#!/usr/bin/env python3
"""Stage the INC-AEBS-010 AOSP overlay into an AOSP checkout.

Copies aosp/vendor/de4sdv/aebs_visualization/** into
<aosp>/system/software_defined_vehicle/samples/de4sdv_aebs_visualization/
(the location where soong demonstrably instantiates DE4SDV modules in this
tree, matching the INC-MW-010 modules) and the protobuf contract into the
overlay's interface/ dir so the genrule can compile it. Also appends the
PRODUCT_PACKAGES block to device/google/sdv/sdv_ivi_cf/sdv_ivi_cf.mk when
not already present.

Idempotent: re-running refreshes files but never deletes unrelated AOSP
content.

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
DEST_REL = Path("system/software_defined_vehicle/samples/de4sdv_aebs_visualization")
DEVICE_MK = Path("device/google/sdv/sdv_ivi_cf/sdv_ivi_cf.mk")

PRODUCT_PACKAGES_BLOCK = """
# DE4SDV INC-AEBS-010 visualization instrumentation (System 2 test article)
PRODUCT_PACKAGES += \\
    de4sdv_aebs_ingress \\
    De4sdvAebsVisualizationApp
"""


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

    destination = aosp / DEST_REL
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

    device_mk = aosp / DEVICE_MK
    if device_mk.exists() and "de4sdv_aebs_ingress" not in device_mk.read_text(encoding="utf-8"):
        with device_mk.open("a", encoding="utf-8") as handle:
            handle.write(PRODUCT_PACKAGES_BLOCK)
        copied += 1
        print(f"appended PRODUCT_PACKAGES to {DEVICE_MK}")

    print(f"overlay staged at {destination} ({copied} change(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
