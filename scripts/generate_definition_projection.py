#!/usr/bin/env python3
"""Generate (or check) the class-definition and kernel-vocabulary artifact pairs.

Canonical artifacts:

- ``de4sdv/semantic/contract-data/class-definition-projection.json``
- ``de4sdv/semantic/contract-data/class-definition-profile.json``
- ``de4sdv/semantic/contract-data/kernel-vocabulary-projection.json``
- ``de4sdv/semantic/contract-data/kernel-vocabulary-profile.json``

The kernel-vocabulary pair (``kernel-vocabulary-admission.yaml``, module
``de4sdv/semantic/kernel_vocabulary_projection.py``) is a separate pair for
the remaining retained identities, the unregistered ontology classes and the
successor predicates. ``--batch 1`` selects the class-definition pair,
``--batch 2`` the kernel-vocabulary pair (default: both).

The class-definition artifacts carry the 22 admitted definition identities of the governed
``de4sdv/semantic/contract-data/class-definition-admission.yaml``: the generated
Semantic Projection rows (model-owned documentation and ownership witnesses,
kernel-binding-contract grounding) and the API
Representation Profile entries (declaration-form representation mechanics and
metaclass echo only). Support stays ``vocabulary-only``; no traversal is
implemented or claimed and no API element identity is claimed.

Both live pairs are constructed deterministically from current sources,
including uncommitted model edits, without Git source-revision bindings.
Commit the model edit and regenerated live artifacts together. Frozen historical
records keep their separate revision-bound contract unchanged.

Usage:

    python scripts/generate_definition_projection.py              # write
    python scripts/generate_definition_projection.py --check      # verify
    python scripts/generate_definition_projection.py --batch 2
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic.native_grounding_projection import canonical_json  # noqa: E402
from de4sdv.semantic.definition_projection import (  # noqa: E402
    PROFILE_PATH,
    PROJECTION_PATH,
    DefinitionAdmissionError,
    build_artifact_pair,
    run_check_errors,
)
from de4sdv.semantic import kernel_vocabulary_projection as kernel_vocabulary  # noqa: E402


def generate(root: Path) -> dict:
    """Build the first definition pair from current model sources."""
    return build_artifact_pair(root)


def generate_kernel_vocabulary(root: Path) -> dict:
    """Build the remaining definition pair from current model sources."""
    return kernel_vocabulary.build_artifact_pair(root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed artifacts equal regeneration (no writes)",
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
            errors = run_check_errors(ROOT) if batch == "1" else kernel_vocabulary.run_check_errors(ROOT)
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
                artifacts = generate(ROOT)
                projection_rel, profile_rel = PROJECTION_PATH, PROFILE_PATH
            else:
                artifacts = generate_kernel_vocabulary(ROOT)
                projection_rel, profile_rel = kernel_vocabulary.PROJECTION_PATH, kernel_vocabulary.PROFILE_PATH
        except (DefinitionAdmissionError, kernel_vocabulary.KernelVocabularyError) as exc:
            print(f"Definition-admission batch {batch} generation refused: {exc}")
            return 1
        (ROOT / projection_rel).write_text(canonical_json(artifacts["projection"]), encoding="utf-8")
        (ROOT / profile_rel).write_text(canonical_json(artifacts["profile"]), encoding="utf-8")
        projection = artifacts["projection"]
        print(
            f"Wrote {projection_rel} ({len(projection['rows'])} rows) and {profile_rel} "
            f"({len(artifacts['profile']['entries'])} entries) from current model sources."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
