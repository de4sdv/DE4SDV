#!/usr/bin/env python3
"""Requalify frozen PLE inputs with the current serializer and ephemeral API.

No models are copied or vendored. Historical replay is explicitly separate;
observations never authorize adoption or semantic authority activation.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from de4sdv.semantic.ple_qualification import build_case_report
from de4sdv.sysml_api.baseline import BaselineExportBundle, build_export_bundle
from de4sdv.sysml_api.client import ApiClient
from de4sdv.sysml_api.ingestion import import_baseline

FROZEN_REVISION = "6a99626b4af7cd01108f27dac88bf5b55bba207a"
PLEML_PIN = "5f8ab8560219dc24d8ec7ec90d6f0a145896ef8e"
SERIALIZER_VERSION = "0.10.3"
FIXTURE = "docs/spikes/pleml-gate-a/pleml_gate_a_fixture.sysml"
LIBRARY = "external/pleml/PLEML/PLEML.sysml"
EXECUTOR_INPUTS = ("scripts/run_ple_qualification.py", "de4sdv/semantic/ple_qualification.py",
                   "de4sdv/sysml_api/baseline.py", "de4sdv/sysml_api/ingestion.py",
                   "de4sdv/sysml_api/client.py", "de4sdv/sysml_api/repository.py",
                   "de4sdv/sysml_api/errors.py")


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=False)
    if result.returncode:
        raise ValueError(f"Git source verification failed: {args[0]}")
    return result.stdout.decode().strip()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verified_file(root, revision, relative):
    path = root / relative
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"source escapes verified checkout: {relative}")
    expected = subprocess.run(["git", "-C", str(root), "show", f"{revision}:{relative}"], capture_output=True, check=False)
    if expected.returncode or path.read_bytes() != expected.stdout:
        raise ValueError(f"source differs from recorded Git object: {relative}")
    return digest(expected.stdout)


def load_experiment(root) -> tuple[Any, list[dict[str, Any]], dict[str, Any]]:
    root = root.resolve()
    if git(root, "rev-parse", "HEAD") != FROZEN_REVISION:
        raise ValueError("experiment checkout is not the frozen reviewed revision")
    if git(root / "external/pleml", "rev-parse", "HEAD") != PLEML_PIN:
        raise ValueError("PLEML pin mismatch")
    fixture_digest = verified_file(root, FROZEN_REVISION, FIXTURE)
    library_digest = verified_file(root / "external/pleml", PLEML_PIN, "PLEML/PLEML.sysml")
    evaluator_digest = verified_file(root, FROZEN_REVISION, "tools/pleml_gate_a.py")
    name = "_de4sdv_verified_ple_qualification_oracle"
    spec = importlib.util.spec_from_file_location(name, root / "tools/pleml_gate_a.py")
    if spec is None or spec.loader is None:
        raise ValueError("cannot load verified experiment interpreter")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    identity = module.gate_a_source_identity(root, expected_pleml_commit=PLEML_PIN)
    return module, list(identity.source_manifest), {
        "interpreter_revision": FROZEN_REVISION, "interpreter_sha256": evaluator_digest,
        "fixture_sha256": fixture_digest, "library_sha256": library_digest,
        "pleml_pin": PLEML_PIN,
    }


def historical_matrix(path, module, manifest):
    raw = json.loads(path.read_text())
    identity = raw.get("gate_a_identity", {})
    if raw.get("source_manifest") != manifest or identity.get("pleml_commit") != PLEML_PIN or identity.get("git_commit") != raw.get("git_commit"):
        raise ValueError("historical source manifest or identity mismatch")
    bundle = BaselineExportBundle.from_dict(raw)
    return module.build_observability_matrix(list(bundle.elements.values()), bundle.element_sources), raw["git_commit"]


def serialize(root, manifest):
    syside = importlib.import_module("syside")

    version = importlib.metadata.version("syside")
    if version != SERIALIZER_VERSION:
        raise ValueError("installed serializer differs from current reviewed pin")
    paths = [root / source["path"] for source in manifest]
    model, diagnostics = syside.try_load_model(paths)
    if diagnostics.contains_errors(warnings_as_errors=False):
        raise ValueError(f"current serializer rejected frozen qualification inputs: {diagnostics}")
    documents = {}
    for document in model.user_docs:
        with document.lock() as locked:
            parsed = urlparse(str(locked.url))
            source = Path(unquote(parsed.path if parsed.scheme == "file" else str(locked.url))).resolve().relative_to(root).as_posix()
            values = json.loads(syside.json.dumps(locked.root_node, syside.SerializationOptions.minimal()))
        if not isinstance(values, list) or not all(isinstance(item, dict) for item in values):
            raise ValueError("serializer did not produce an element array")
        if source in documents:
            raise ValueError("serializer repeated a source document")
        documents[source] = values
    if set(documents) != {source["path"] for source in manifest}:
        raise ValueError("serializer source coverage mismatch")
    bundle = build_export_bundle(git_commit=FROZEN_REVISION, source_documents=documents)
    raw = bundle.to_dict()
    raw["source_manifest"] = manifest
    return BaselineExportBundle.from_dict(raw), version


def verify_readback(bundle, values):
    if not isinstance(values, list) or not all(isinstance(item, dict) for item in values):
        raise ValueError("API readback must contain element objects")
    indexed = {item.get("@id"): item for item in values}
    if len(indexed) != len(values) or set(indexed) != set(bundle.elements):
        raise ValueError("API readback changed or duplicated UUIDs")
    for uuid, expected in bundle.elements.items():
        if indexed[uuid].get("@type") != expected.get("@type"):
            raise ValueError("API readback changed metatype")
    if reference_edges(indexed) != reference_edges(bundle.elements):
        raise ValueError("API readback changed internal references")
    return values


def reference_edges(elements):
    """Preserve reference property paths, targets and multiplicity, not list order."""
    edges = Counter()

    def collect(value, source, path):
        if isinstance(value, dict):
            if "@id" in value and "@type" not in value:
                if set(value) != {"@id"}:
                    raise ValueError("API readback contains a noncanonical reference object")
                target = value["@id"]
                if not isinstance(target, str) or target not in elements:
                    raise ValueError("API readback contains a dangling internal reference")
                edges[(source, path, target)] += 1
                return
            for key, child in value.items():
                collect(child, source, path + (key,))
        elif isinstance(value, list):
            for child in value:
                collect(child, source, path)

    for source, value in elements.items():
        collect(value, source, ())
    return edges


def observe(module, elements):
    model = module.GateAModel(elements)

    def unique(name):
        matches = [item["@id"] for item in elements if item.get("@type") == "OccurrenceUsage" and (item.get("declaredName") or item.get("name")) == name]
        if len(matches) != 1:
            raise ValueError(f"qualification role missing or ambiguous: {name}")
        return matches[0]

    nominal, ambiguous = unique("nominalAdapterRules"), unique("ambiguousAdapterRules")
    outcomes = {}
    for label, config, rules in (
        ("adapter-required-exactly-one", "validAutowareAndroid", nominal),
        ("valid-no-adapter", "validAutowareNoMiddleware", nominal),
        ("configuration-invalid", "forbiddenApolloAndroid", nominal),
        ("derivation-incomplete", "missingOpenpilotSCORE", nominal),
        ("derivation-ambiguous", "validAutowareAndroid", ambiguous),
    ):
        value = asdict(model.evaluate(unique(config), rule_set_id=rules))
        value["selected_feature_ids"] = sorted(value["selected_feature_ids"])
        outcomes[label] = value
    expected = {"adapter-required-exactly-one": "derivation-complete", "valid-no-adapter": "derivation-complete", "configuration-invalid": "configuration-invalid", "derivation-incomplete": "derivation-incomplete", "derivation-ambiguous": "derivation-ambiguous"}
    if {key: value["status"] for key, value in outcomes.items()} != expected:
        raise ValueError("adapter or incompatibility interpretation changed")
    if outcomes["valid-no-adapter"]["adapter_id"] is not None:
        raise ValueError("no-adapter configuration selected an adapter")
    groups = {"at-least-one": model.group_resolutions(unique("validOneSensor")),
              "multi-select": model.group_resolutions(unique("validBothSensors"))}
    try:
        model.group_resolutions(unique("invalidNoSensor"))
    except module.UnsupportedSemanticShape as exc:
        groups["empty"] = {"status": "configuration-invalid", "reason": str(exc)}
    else:
        raise ValueError("empty at-least-one group unexpectedly passed")
    return {"outcomes": outcomes, "group_resolutions": groups,
            "native_expression_executed": False}


def run(args):
    if args.out.exists():
        raise ValueError("refusing to overwrite an existing receipt")
    module, manifest, source_identity = load_experiment(args.experiment)
    executor_revision = git(ROOT, "rev-parse", "HEAD")
    current_lock = verified_file(ROOT, executor_revision, "sysand-lock.toml")
    source_identity.update(executor_revision=executor_revision, current_lock_sha256=current_lock,
                           executor_source_dirty=bool(git(ROOT, "status", "--porcelain")))
    prior, historical_revision = historical_matrix(args.historical_export, module, manifest)
    source_identity["historical_export_revision"] = historical_revision
    source_identity["historical_export_sha256"] = digest(args.historical_export.read_bytes())
    if args.api_url is None:
        receipt = build_case_report(prior, prior)
        receipt.update(historical=True, fresh_serialization=False, api_readback=False,
                       observations=observe(module, json.loads(args.historical_export.read_text())["elements"]))
    else:
        if re.fullmatch(r"http://127\.0\.0\.1:[0-9]{1,5}", args.api_url) is None or not 1 <= int(args.api_url.rsplit(":", 1)[1]) <= 65535:
            raise ValueError("qualification may write only to an ephemeral loopback API")
        if args.expected_executor != executor_revision or re.fullmatch(r"[0-9a-f]{40}", executor_revision) is None:
            raise ValueError("fresh qualification requires the exact executor revision")
        source_identity["executor_inputs"] = {
            relative: verified_file(ROOT, executor_revision, relative)
            for relative in EXECUTOR_INPUTS
        }
        bundle, version = serialize(args.experiment.resolve(), manifest)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        for filename in ("export.json", "binding.json", "api-readback.json"):
            if (args.out.parent / filename).exists():
                raise ValueError("fresh execution output already exists")
        bundle.write(args.out.parent / "export.json")
        client = ApiClient(args.api_url)
        imported = import_baseline(client, bundle, project_name="DE4SDV isolated PLE qualification")
        values = verify_readback(bundle, client.get_all(f"/projects/{imported.project_id}/commits/{imported.commit_id}/elements"))
        binding = {"schema": "de4sdv.ple-qualification-binding/v1", "model_revision": FROZEN_REVISION,
                   "executor_revision": executor_revision, "pleml_pin": PLEML_PIN,
                   "serializer_version": version, "current_lock_sha256": current_lock,
                   "export_sha256": digest((args.out.parent / "export.json").read_bytes()), **asdict(imported)}
        (args.out.parent / "binding.json").write_text(json.dumps(binding, indent=2) + "\n")
        (args.out.parent / "api-readback.json").write_text(json.dumps(values, indent=2) + "\n")
        matrix = module.build_observability_matrix(values, bundle.element_sources)
        receipt = build_case_report(matrix, prior)
        receipt.update(historical=False, fresh_serialization=True, api_readback=True,
                       binding=binding, observations=observe(module, values),
                       pruning_records=list(bundle.external_references))
    # Check that the read-only experiment and current lock did not move mid-run.
    _, final_manifest, final_identity = load_experiment(args.experiment)
    if final_manifest != manifest or final_identity["interpreter_sha256"] != source_identity["interpreter_sha256"] or verified_file(ROOT, executor_revision, "sysand-lock.toml") != current_lock:
        raise ValueError("qualification sources moved during execution")
    if args.api_url is not None:
        if git(ROOT, "rev-parse", "HEAD") != executor_revision:
            raise ValueError("executor checkout moved during execution")
        for relative, expected in source_identity["executor_inputs"].items():
            if verified_file(ROOT, executor_revision, relative) != expected:
                raise ValueError("executing source moved during qualification")
    receipt["source_identity"] = source_identity
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as output:
        output.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--historical-export", type=Path, required=True)
    parser.add_argument("--api-url")
    parser.add_argument("--expected-executor")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = run(args)
    except (ValueError, RuntimeError, OSError, ImportError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"receipt": str(args.out), "historical": receipt["historical"],
                      "case_count": len(receipt["cases"]), "qualified": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
