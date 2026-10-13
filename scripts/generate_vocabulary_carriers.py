#!/usr/bin/env python3
"""Generate (or check) the O4 W4 vocabulary-relationship carrier artifacts.

Canonical artifacts:

- ``de4sdv/semantic/contract-data/increment-relationship-projection.json``
- ``de4sdv/semantic/contract-data/increment-relationship-profile.json``

The artifacts carry the five admitted vocabulary-only relationship carriers
(``recordsGap``, ``recordsAssumption``, ``addressesConcern``,
``selectedViewpoint``, ``producesView``): the reviewed definitions with their
model-resident carrier lineage (kernel ``connection def``, typed ends), the
generated Projection rows, and the API-representation profile entries.
Support stays ``vocabulary-only``; no traversal is implemented or claimed.

Deterministic current-input regeneration is the freshness gate. Construction
does not require an input commit or emit Git-revision/input-digest bindings.

Usage:

    python scripts/generate_vocabulary_carriers.py              # write
    python scripts/generate_vocabulary_carriers.py --check      # verify
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic.projection_o2p import canonical_json  # noqa: E402
from de4sdv.semantic.vocabulary_carrier import (  # noqa: E402
    PROFILE_CARRIER_PATH,
    PROJECTION_CARRIER_PATH,
    CarrierError,
    build_artifact_pair,
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
            print("Vocabulary-carrier artifact check failed:")
            for error in errors:
                print(f"  - {error}")
            return 1
        print("Vocabulary-carrier artifacts match regeneration from current inputs.")
        return 0

    try:
        artifacts = generate(ROOT)
    except CarrierError as exc:
        print(f"Vocabulary-carrier generation refused: {exc}")
        return 1
    projection_path = ROOT / PROJECTION_CARRIER_PATH
    profile_path = ROOT / PROFILE_CARRIER_PATH
    projection_path.write_text(
        canonical_json(artifacts["projection"]), encoding="utf-8"
    )
    profile_path.write_text(canonical_json(artifacts["profile"]), encoding="utf-8")
    projection = artifacts["projection"]
    print(
        f"Wrote {PROJECTION_CARRIER_PATH} "
        f"({len(projection['rows'])} rows) and {PROFILE_CARRIER_PATH} "
        f"({len(artifacts['profile']['entries'])} entries) from current inputs."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
