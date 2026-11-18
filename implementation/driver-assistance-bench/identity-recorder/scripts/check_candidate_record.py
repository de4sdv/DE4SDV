#!/usr/bin/env python3
"""Re-derives a candidate record of MAP-DRIVING-DA-CANDIDATE-RECORD, as REQ-DRIVING-044's verification asks.

The engineer who checks a record takes the named revision, applies the recorded difference and hashes the named
files again. This script does the parts a machine can do:

  1. the record's own consistency: each difference file's SHA-256 and size, the total size and the digest of all of
     them, and (with --event-sha256) that the record file is the one the event named;
  2. with --vp-clone: a fresh `git clone --shared` of the clone at the recorded revision, `git apply --check` and
     `git apply` of every recorded difference in order, and the difference of the result against the revision is
     not empty (the source difference is never empty);
  3. with --rehash: the SHA-256 of every listed file that still exists on this host, against the recorded one.

It prints one JSON report and exits 0 when every check that ran holds, 1 otherwise, 2 on a usage error.

Usage:
  check_candidate_record.py <candidate_record.json> [--event-sha256 HEX] [--vp-clone DIR] [--scratch DIR] [--rehash]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

LISTS = ("configuration_files", "network_files", "binaries", "runtime_libraries")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check_consistency(record: dict, raw: bytes, event_sha: str | None) -> list[str]:
    problems = []
    difference = record["source_difference"]
    total = b""
    for item in difference["files"]:
        text = item["text"].encode("utf-8")
        if hashlib.sha256(text).hexdigest() != item["sha256"]:
            problems.append(f"difference {item['name']}: sha256 differs from its text")
        if len(text) != item["bytes"]:
            problems.append(f"difference {item['name']}: size differs from its text")
        total += text
    if not difference["files"] or len(total) == 0:
        problems.append("the source difference is empty")
    if len(total) != difference["bytes"]:
        problems.append("the total size of the difference differs")
    if hashlib.sha256(total).hexdigest() != difference["sha256"]:
        problems.append("the digest of the difference differs")
    if event_sha is not None and hashlib.sha256(raw).hexdigest() != event_sha:
        problems.append("the record file is not the one the event named")
    revision = record.get("upstream_revision", "")
    if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
        problems.append("the upstream revision is not 40 lowercase hex digits")
    return problems


def check_apply(record: dict, vp_clone: Path, scratch: Path) -> list[str]:
    problems = []
    work = Path(tempfile.mkdtemp(prefix="rederive-", dir=scratch))
    tree = work / "vp"
    run = lambda *args, **kw: subprocess.run(args, capture_output=True, text=True, **kw)  # noqa: E731
    clone = run("git", "clone", "--quiet", "--shared", "--no-checkout", str(vp_clone), str(tree))
    if clone.returncode != 0:
        return [f"git clone failed: {clone.stderr.strip()}"]
    checkout = run("git", "-C", str(tree), "checkout", "--quiet", "--detach", record["upstream_revision"])
    if checkout.returncode != 0:
        return [f"the clone has no revision {record['upstream_revision']}: {checkout.stderr.strip()}"]
    for item in record["source_difference"]["files"]:
        patch = work / item["name"]
        patch.write_bytes(item["text"].encode("utf-8"))
        applied = run("git", "-C", str(tree), "apply", "--check", str(patch))
        if applied.returncode != 0:
            problems.append(f"{item['name']} does not apply: {applied.stderr.strip()}")
            return problems
        run("git", "-C", str(tree), "apply", str(patch), check=True)
    run("git", "-C", str(tree), "add", "-A", check=True)
    diff = run("git", "-C", str(tree), "diff", "--cached", "--stat", record["upstream_revision"])
    if diff.returncode != 0 or not diff.stdout.strip():
        problems.append("the applied difference leaves the source equal to the revision")
    return problems


def check_rehash(record: dict) -> tuple[list[str], int, int]:
    problems, checked, absent = [], 0, 0
    for name in LISTS:
        for item in record.get(name, []):
            path = Path(item["path"])
            if not path.is_file():
                absent += 1
                continue
            checked += 1
            if sha256_file(path) != item["sha256"]:
                problems.append(f"{name}: {item['path']} differs from the record")
    return problems, checked, absent


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("record", type=Path)
    parser.add_argument("--event-sha256")
    parser.add_argument("--vp-clone", type=Path)
    parser.add_argument("--scratch", type=Path, default=None)
    parser.add_argument("--rehash", action="store_true")
    args = parser.parse_args(argv)
    raw = args.record.read_bytes()
    record = json.loads(raw)
    report: dict = {"record": str(args.record), "record_sha256": hashlib.sha256(raw).hexdigest(), "checks": {}}
    problems = check_consistency(record, raw, args.event_sha256)
    report["checks"]["consistency"] = problems or "ok"
    if args.vp_clone is not None:
        scratch = args.scratch or Path(tempfile.gettempdir())
        scratch.mkdir(parents=True, exist_ok=True)
        applied = check_apply(record, args.vp_clone, scratch)
        report["checks"]["apply_at_revision"] = applied or "ok"
        problems += applied
    if args.rehash:
        rehashed, checked, absent = check_rehash(record)
        report["checks"]["rehash"] = rehashed or "ok"
        report["rehash_counts"] = {"checked": checked, "absent_here": absent}
        problems += rehashed
    report["ok"] = not problems
    print(json.dumps(report, indent=1))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
