#!/usr/bin/env python3
"""Generate (or check) the O2+ native/library grounding projection layer.

Canonical artifacts:

- ``docs/method-conformance/o2plus/semantic-projection-o2plus.json``
- ``docs/method-conformance/o2plus/api-representation-profile-o2plus.json``

The layer records exact-fit standard-construct grounding for the reviewed
safe subset of already-native/library constructs (W3) and emits
vocabulary-only projection rows / API-representation profile entries over
them. Generation is not authority activation; support stays vocabulary-only;
no traversal is implemented or claimed.

Usage:

    python scripts/generate_semantic_projection_o2p.py              # write
    python scripts/generate_semantic_projection_o2p.py --check      # verify
    python scripts/generate_semantic_projection_o2p.py \\
        --source-revision <40-hex commit id>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic.projection_o2p import (  # noqa: E402
    PROFILE_O2P_PATH,
    PROJECTION_O2P_PATH,
    ProjectionO2PError,
    build_pair_o2p,
    canonical_json,
    resolve_source_revision,
    run_check_errors_o2p,
)


def generate(root: Path, *, source_revision: str | None = None) -> dict:
    """Build both O2+ artifacts bound to a source revision."""
    if source_revision is None:
        source_revision = resolve_source_revision(root)
    return build_pair_o2p(root, source_revision=source_revision)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed artifacts equal regeneration (no writes)",
    )
    parser.add_argument(
        "--source-revision",
        default=None,
        help=(
            "explicit Git commit id that contains every bound input "
            "byte-for-byte (default: HEAD)"
        ),
    )
    args = parser.parse_args(argv)

    if args.check:
        errors = run_check_errors_o2p(ROOT)
        if errors:
            print("O2+ projection check FAILED.")
            for error in errors:
                print(f"  - {error}")
            return 1
        print("O2+ projection check passed.")
        return 0

    try:
        artifacts = generate(ROOT, source_revision=args.source_revision)
    except ProjectionO2PError as exc:
        print("O2+ projection generation FAILED.")
        print(f"  - {exc}")
        return 1
    (ROOT / PROJECTION_O2P_PATH).write_text(
        canonical_json(artifacts["projection"]), encoding="utf-8"
    )
    (ROOT / PROFILE_O2P_PATH).write_text(
        canonical_json(artifacts["profile"]), encoding="utf-8"
    )
    print(f"wrote {PROJECTION_O2P_PATH}")
    print(f"wrote {PROFILE_O2P_PATH}")
    print(
        "source revision: "
        f"{artifacts['projection']['binding']['source_revision']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
