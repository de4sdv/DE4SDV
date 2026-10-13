#!/usr/bin/env python3
"""Generate (or check) the native-grounding projection and profile.

Canonical artifacts:

- ``de4sdv/semantic/contract-data/native-grounding-projection.json``
- ``de4sdv/semantic/contract-data/native-grounding-profile.json``

The layer records exact-fit standard-construct grounding for the reviewed
safe subset of already-native/library constructs and emits
vocabulary-only projection rows / API-representation profile entries over
them. Generation is not authority activation; support stays vocabulary-only;
no traversal is implemented or claimed.

Usage:

    python scripts/generate_native_grounding_projection.py              # write
    python scripts/generate_native_grounding_projection.py --check      # verify
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic.native_grounding_projection import (  # noqa: E402
    PROFILE_PATH,
    PROJECTION_PATH,
    NativeGroundingError,
    build_artifact_pair,
    canonical_json,
    run_check_errors,
)


def generate(root: Path) -> dict:
    """Build both artifacts from current inputs."""
    return build_artifact_pair(root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed artifacts equal regeneration (no writes)",
    )
    args = parser.parse_args(argv)

    if args.check:
        errors = run_check_errors(ROOT)
        if errors:
            print("Native-grounding projection check FAILED.")
            for error in errors:
                print(f"  - {error}")
            return 1
        print("Native-grounding projection check passed.")
        return 0

    try:
        artifacts = generate(ROOT)
    except NativeGroundingError as exc:
        print("Native-grounding projection generation FAILED.")
        print(f"  - {exc}")
        return 1
    (ROOT / PROJECTION_PATH).write_text(
        canonical_json(artifacts["projection"]), encoding="utf-8"
    )
    (ROOT / PROFILE_PATH).write_text(
        canonical_json(artifacts["profile"]), encoding="utf-8"
    )
    print(f"wrote {PROJECTION_PATH}")
    print(f"wrote {PROFILE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
