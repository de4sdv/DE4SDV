#!/usr/bin/env python3
"""Generate (or check) the O4 definition-admission projection + profile artifacts.

Canonical artifacts:

- ``docs/method-conformance/o4/definition-projection.json``
- ``docs/method-conformance/o4/definition-profile.json``
- ``docs/method-conformance/o4/definition-batch2-projection.json`` (batch 2)
- ``docs/method-conformance/o4/definition-batch2-profile.json`` (batch 2)

Batch 2 (``definition-admission-batch2.yaml``, module
``de4sdv/semantic/definition_projection_batch2.py``) is a separate pair for
the remaining retained identities, the unregistered ontology classes and the
W6 successor predicates; ``--batch`` selects one pair (default: both).

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
    python scripts/generate_definition_projection.py --batch 2
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
from de4sdv.semantic import definition_projection_batch2 as batch2  # noqa: E402


def generate(root: Path, *, source_revision: str | None = None) -> dict:
    """Build both definition artifacts bound to a source revision."""
    if source_revision is None:
        source_revision = resolve_source_revision(root)
    return build_artifact_pair(root, source_revision=source_revision)


def generate_batch2(root: Path, *, source_revision: str | None = None) -> dict:
    """Build both batch-2 definition artifacts bound to a source revision."""
    if source_revision is None:
        source_revision = resolve_source_revision(root)
    return batch2.build_artifact_pair(root, source_revision=source_revision)


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
    parser.add_argument(
        "--batch",
        choices=("1", "2", "all"),
        default="all",
        help="which definition pair to generate or check (default: both)",
    )
    args = parser.parse_args(argv)
    batches = ("1", "2") if args.batch == "all" else (args.batch,)

    if args.check:
        failed = False
        for batch in batches:
            errors = run_check_errors(ROOT) if batch == "1" else batch2.run_check_errors(ROOT)
            if errors:
                failed = True
                print(f"Definition-admission batch {batch} artifact check failed:")
                for error in errors:
                    print(f"  - {error}")
            else:
                print(f"Definition-admission batch {batch} artifacts match regeneration from current inputs.")
        return 1 if failed else 0

    for batch in batches:
        try:
            if batch == "1":
                artifacts = generate(ROOT, source_revision=args.source_revision)
                projection_rel, profile_rel = PROJECTION_PATH, PROFILE_PATH
            else:
                artifacts = generate_batch2(ROOT, source_revision=args.source_revision)
                projection_rel, profile_rel = batch2.PROJECTION_PATH, batch2.PROFILE_PATH
        except (DefinitionAdmissionError, batch2.DefinitionBatch2Error) as exc:
            print(f"Definition-admission batch {batch} generation refused: {exc}")
            return 1
        (ROOT / projection_rel).write_text(canonical_json(artifacts["projection"]), encoding="utf-8")
        (ROOT / profile_rel).write_text(canonical_json(artifacts["profile"]), encoding="utf-8")
        projection = artifacts["projection"]
        print(
            f"Wrote {projection_rel} ({len(projection['rows'])} rows) and {profile_rel} "
            f"({len(artifacts['profile']['entries'])} entries) bound to "
            f"{projection['binding']['source_revision']}."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
