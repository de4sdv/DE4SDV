#!/usr/bin/env python3
"""Generate (or check) the O3 semantic-authority equivalence scope document.

Canonical artifact (single):

- ``docs/method-conformance/o3/o3-equivalence-scope.json``
  (``de4sdv.o3-equivalence-scope/v1``): the machine-readable O3 readiness
  scope — the 13-identity migration boundary, the old authority bundle
  (authored ontology YAML + kernel contract + validated kernel bindings +
  runtime strategy implementations), the proposed new bundle (authoritative
  model revision + the Semantic Projection chain through v1.2 + the API
  Representation Profile chain through v1.2), the per-identity declared-
  semantics comparison, the reviewed contract checks, the support-state
  preservation matrix, and the same-revision comparison requirement for the
  future cutover.

Read-only planning evidence — NOT activation authority:

- the tooling writes exactly ONE repository path (the scope document above);
  the write guard refuses anything else;
- it never switches runtime authority, never edits the ontology YAML, the
  O2 chain artifacts, the model, or any runtime module;
- it is never imported by the runtime/query path (test-locked);
- every comparison fails closed: any declared-semantics mismatch, contract-
  check failure, digest drift, or unrecorded change requires regeneration
  and independent review.

Determinism: identical inputs produce byte-identical output. The comparison
base revision is recorded from ``origin/main`` (falling back to ``HEAD``) and
is validated on ``--check`` as an existing ancestor of the checked-out
revision — it is deliberately never byte-compared, because regeneration
legitimately resolves the then-current permanent main revision.

Usage:

    python scripts/generate_o3_equivalence_scope.py            # write
    python scripts/generate_o3_equivalence_scope.py --check    # verify
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic import o3_equivalence  # noqa: E402


def run_check_errors(root: Path) -> list[str]:
    """Validate the committed scope document fail-closed."""
    path = root / o3_equivalence.O3_SCOPE_PATH
    if not path.exists():
        return [f"O3 scope document missing: {o3_equivalence.O3_SCOPE_PATH}"]
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"O3 scope document is not valid JSON: {exc}"]
    if not isinstance(document, dict):
        return ["O3 scope document must be a JSON object"]
    return o3_equivalence.check_scope_document(root, document)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the committed scope document instead of writing",
    )
    args = parser.parse_args(argv)

    if args.check:
        errors = run_check_errors(ROOT)
        if errors:
            print("O3 equivalence scope check FAILED.")
            for error in errors:
                print(f"  - {error}")
            return 1
        print("O3 equivalence scope check passed.")
        return 0

    document = o3_equivalence.build_scope_document(ROOT)
    path = ROOT / o3_equivalence.O3_SCOPE_PATH
    o3_equivalence.assert_writable(path, ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(o3_equivalence.canonical_json(document), encoding="utf-8")
    summary = document["summary"]
    static = summary["static_parity"]
    print(f"wrote {o3_equivalence.O3_SCOPE_PATH}")
    print(f"scope identities: {len(document['identities'])}")
    print(
        "static parity: "
        f"{len(static['identities_fully_equivalent'])} fully equivalent; "
        f"{len(static['identities_with_pending_dimension'])} with a pending "
        f"dimension; {len(static['identities_with_mismatch'])} with mismatch"
    )
    print(
        "runtime equivalence: "
        f"{len(summary['runtime']['completed'])} completed; "
        f"{len(summary['runtime']['not_yet_comparable'])} not yet comparable"
    )
    print(f"contract checks failing: {len(summary['contract_check_failures'])}")
    print(
        "comparison base revision: "
        f"{document['basis']['comparison_base_revision']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
