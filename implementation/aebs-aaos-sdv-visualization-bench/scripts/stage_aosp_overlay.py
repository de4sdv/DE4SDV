#!/usr/bin/env python3
"""Stage the INC-AEBS-010 AOSP overlay into an AOSP checkout.

Copies vendor/de4sdv/aebs_visualization/** into <aosp>/vendor/de4sdv/
aebs_visualization/ and the protobuf contract into the overlay's interface/
dir so the soong proto_library target can compile it. Idempotent: re-running
refreshes files but never deletes unrelated AOSP content.

Usage:
    python scripts/stage_aosp_overlay.py --aosp /path/to/aosp
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OVERLAY_SRC = REPO_ROOT / "aosp" / "vendor" / "de4sdv" / "aebs_visualization"
PROTO_SRC = REPO_ROOT / "interface" / "aebs_visualization.proto"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aosp", required=True, type=Path, help="AOSP checkout root")
    args = parser.parse_args()

    aosp = args.aosp.resolve()
    if not (aosp / "build" / "envsetup.sh").exists():
        print(f"error: {aosp} does not look like an AOSP checkout", file=sys.stderr)
        return 1

    destination = aosp / "vendor" / "de4sdv" / "aebs_visualization"
    copied = 0
    for source in sorted(OVERLAY_SRC.rglob("*")):
        if not source.is_file() or "__pycache__" in source.parts:
            continue
        relative = source.relative_to(OVERLAY_SRC)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and sha256(target) == sha256(source):
            continue
        shutil.copy2(source, target)
        copied += 1
        print(f"staged {relative}")

    proto_target = destination / "interface" / "aebs_visualization.proto"
    proto_target.parent.mkdir(parents=True, exist_ok=True)
    if not proto_target.exists() or sha256(proto_target) != sha256(PROTO_SRC):
        shutil.copy2(PROTO_SRC, proto_target)
        copied += 1
        print("staged interface/aebs_visualization.proto")

    print(f"overlay staged at {destination} ({copied} file(s) updated)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
