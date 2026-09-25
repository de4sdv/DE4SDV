#!/usr/bin/env python3
"""Generate (or check) the O4 definition-admission projection + profile artifacts.

Canonical artifacts:

- ``docs/method-conformance/o4/definition-projection.json``
- ``docs/method-conformance/o4/definition-profile.json``

The artifacts carry the 21 admitted definition identities of the pinned
``docs/method-conformance/o4/definition-admission.yaml`` batch: the generated
Semantic Projection rows (recomputed documentation observation against the
reviewed definitions, kernel-binding-contract grounding) and the API
Representation Profile entries (declaration-form representation mechanics and
metaclass echo only). Support stays ``vocabulary-only``; no traversal is
implemented or claimed and no API element identity is claimed.

Two-commit source binding (the O2+/O1 pattern): the admission inputs must be
committed first, then this generator binds the artifacts to that commit.

Usage:

    python scripts/generate_definition_projection.py              # write
    python scripts/generate_definition_projection.py --check      # verify
    python scripts/generate_definition_projection.py \\
        --source-revision <40-hex commit id>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic.projection_o2p import canonical_json, resolve_source_revision  # noqa: E402
from de4sdv.semantic.definition_projection import (  # noqa: E402
    PROFILE_PATH,
    PROJECTION_PATH,
    DefinitionAdmissionError,
    build_artifact_pair,
    run_check_errors,
)


def generate(root: Path, *, source_revision: str | None = None) -> dict:
    """Build both definition artifacts bound to a source revision."""
    if source_revision is None:
        source_revision = resolve_source_revision(root)
    return build_artifact_pair(root, source_revision=source_revision)


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
        help="commit id containing every bound input byte-for-byte (default: HEAD)",
    )
    args = parser.parse_args(argv)

    if args.check:
        errors = run_check_errors(ROOT)
        if errors:
            print("Definition-admission artifact check failed:")
            for error in errors:
                print(f"  - {error}")
            return 1
        print("Definition-admission artifacts match regeneration from current inputs.")
        return 0

    try:
        artifacts = generate(ROOT, source_revision=args.source_revision)
    except DefinitionAdmissionError as exc:
        print(f"Definition-admission generation refused: {exc}")
        return 1
    projection_path = ROOT / PROJECTION_PATH
    profile_path = ROOT / PROFILE_PATH
    projection_path.write_text(
        canonical_json(artifacts["projection"]), encoding="utf-8"
    )
    profile_path.write_text(canonical_json(artifacts["profile"]), encoding="utf-8")
    projection = artifacts["projection"]
    print(
        f"Wrote {PROJECTION_PATH} "
        f"({len(projection['rows'])} rows) and {PROFILE_PATH} "
        f"({len(artifacts['profile']['entries'])} entries) bound to "
        f"{projection['binding']['source_revision']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())