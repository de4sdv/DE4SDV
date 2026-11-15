#!/usr/bin/env python3
"""Scan and check the two baseline images; inventory is not licence clearance."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLES = {"zone-ecu", "can-gw"}
DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
SCHEMA = "de4sdv-ee-sbom/1"


def require_digest(value):
    if not isinstance(value, str) or not DIGEST.fullmatch(value):
        raise ValueError(f"invalid image digest: {value!r}")
    return value


def repository(ref):
    if not isinstance(ref, str) or not ref or "@" in ref:
        raise ValueError("baseline ref must be a repository or tag beside its digest")
    return ref[:ref.rfind(":")] if ref.rfind(":") > ref.rfind("/") else ref


def baseline_images(root):
    parts = yaml.safe_load((root / "vehicle/parts.yaml").read_text())["parts"]
    locked = yaml.safe_load((root / "vehicle/vxp.lock").read_text())["images"]
    lock = {(entry["ref"], require_digest(entry["digest"])) for entry in locked}
    images = {}
    for entry in parts:
        repo = repository(entry["ref"])
        role = repo.rsplit("/", 1)[-1]
        if role not in ROLES:
            continue
        digest = require_digest(entry.get("digest"))
        if (entry["ref"], digest) not in lock:
            raise ValueError(f"{role}: parts and lock disagree")
        ref = repo + "@" + digest
        if role in images and images[role] != ref:
            raise ValueError(f"{role}: conflicting baseline images")
        images[role] = ref
    if set(images) != ROLES:
        raise ValueError("baseline must identify both zone-ecu and can-gw images")
    return dict(sorted(images.items()))


def checked_source(document, ref):
    source = document.get("source", {})
    meta = source.get("metadata", {})
    digest = ref.rsplit("@", 1)[1]
    if source.get("type") != "image" or meta.get("userInput") != ref:
        raise ValueError("scanner source does not identify the requested image")
    if require_digest(meta.get("manifestDigest")) != digest:
        raise ValueError("scanner manifest digest differs from the baseline")
    require_digest(meta.get("imageID"))
    # Retain source identity, not raw image config, environment or registry auth.
    return {key: meta[key] for key in ("userInput", "manifestDigest", "imageID", "architecture", "os")}


def check_inventory(root, out):
    images = baseline_images(root)
    receipt = json.loads((out / "inventory.json").read_text())
    if receipt.get("schema") != SCHEMA or receipt.get("baseline_images") != images:
        raise ValueError("SBOM inventory does not match the current baseline")
    records = receipt.get("images", [])
    if len(records) != len(ROLES) or {record.get("role") for record in records} != ROLES:
        raise ValueError("SBOM inventory must contain each image exactly once")
    for record in records:
        role = record["role"]
        if record.get("file") != role + ".cdx.json.gz":
            raise ValueError("unexpected SBOM path")
        data = (out / record["file"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != record.get("sha256"):
            raise ValueError(f"{role}: SBOM hash mismatch")
        doc = json.loads(gzip.decompress(data))
        if doc.get("bomFormat") != "CycloneDX" or not doc.get("components"):
            raise ValueError(f"{role}: empty or invalid CycloneDX inventory")
        if len(doc["components"]) != record.get("components"):
            raise ValueError(f"{role}: component count mismatch")
        checked_source({"source": {"type": "image", "metadata": record.get("source", {})}}, images[role])
    return receipt


def generate(root, out):
    images = baseline_images(root)  # Validate before invoking a scanner or writing.
    out.mkdir(parents=True, exist_ok=True)
    receipt = {"schema": SCHEMA, "baseline_images": images, "images": []}
    blobs = {}
    with tempfile.TemporaryDirectory(prefix=".scan-", dir=out) as directory:
        temp = Path(directory)
        for role, ref in images.items():
            cdx = temp / (role + ".cdx.json")
            native = temp / (role + ".syft.json")
            subprocess.run(["syft", ref, "-o", f"cyclonedx-json={cdx}", "-o", f"syft-json={native}"], check=True)
            raw = cdx.read_bytes()
            doc = json.loads(raw)
            native_doc = json.loads(native.read_text())
            source = checked_source(native_doc, ref)
            if doc.get("bomFormat") != "CycloneDX" or not doc.get("components"):
                raise ValueError(f"{role}: scanner returned an empty or invalid SBOM")
            descriptor = native_doc.get("descriptor", {})
            if descriptor.get("name") != "syft" or not descriptor.get("version"):
                raise ValueError("scanner identity is missing")
            data = gzip.compress(raw, mtime=0)
            filename = role + ".cdx.json.gz"
            blobs[filename] = data
            receipt["images"].append({"role": role, "file": filename, "sha256": hashlib.sha256(data).hexdigest(), "components": len(doc["components"]), "source": source, "scanner": {"name": descriptor["name"], "version": descriptor["version"]}})
    # Neither old inventory is replaced until both scans and identities passed.
    for filename, data in blobs.items():
        (out / filename).write_bytes(data)
    (out / "inventory.json").write_text(json.dumps(receipt, indent=2) + "\n")
    check_inventory(root, out)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("generate", "check"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    out = args.out or args.root / "sbom"
    try:
        receipt = generate(args.root, out) if args.action == "generate" else check_inventory(args.root, out)
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        print(f"SBOM inventory failed: {exc}")
        return 1
    print(json.dumps({record["role"]: {"components": record["components"], "manifest_digest": record["source"]["manifestDigest"]} for record in receipt["images"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
