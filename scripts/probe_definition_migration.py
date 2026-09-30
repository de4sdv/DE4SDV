#!/usr/bin/env python3
"""Offline O4 definition-migration probe (read-only; no network, no writes).

Runs :func:`de4sdv.semantic.definition_migration.probe_definition_migration`
over the checked-out candidate artifacts and prints the JSON report:
per-identity candidate-vs-authored mappings, the fresh exact-revision API
closure state and its exact prerequisite, the remaining legacy-only class
count, and — when ``--export`` supplies a retained export — declaration-form
matches as representation evidence (never an identity claim).

Exit codes: 0 report produced; 2 refused (fail closed); 1 unexpected error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic.definition_migration import (  # noqa: E402
    DefinitionMigrationError,
    probe_definition_migration,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT), help="repository checkout")
    parser.add_argument(
        "--binding",
        default=None,
        help="optional validated revision binding JSON for the closure state",
    )
    parser.add_argument(
        "--export",
        default=None,
        help="optional retained export JSON for the declaration-form probe",
    )
    parser.add_argument(
        "--expected-git-revision",
        help="explicit revision for closure checking; omission cannot prove closure",
    )
    args = parser.parse_args(argv)

    try:
        binding = None
        if args.binding:
            from de4sdv.sysml_api.revisions import RevisionBinding

            binding = RevisionBinding.load(Path(args.binding))
        report = probe_definition_migration(
            Path(args.root), binding=binding, export=args.export,
            expected_git_revision=args.expected_git_revision,
        )
    except (DefinitionMigrationError, ValueError, OSError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())