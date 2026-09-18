#!/usr/bin/env python3
"""Fail-closed O4 lifecycle invariant: O3 stays frozen throughout O4.

The frozen O3 authority transition is complete for exactly the thirteen
identities in ``MIGRATED_IDENTITIES`` (``de4sdv.semantic.o3_bundle``), and no
**retained O4-target identity** may require a future O3
authority-transition/admission obligation anywhere in its governed lifecycle
records. O4 targets reuse the O2 admission / generated-projection machinery
and never join or reopen O3.

Membership is derived from the generated O4 execution register (the
authoritative membership/accounting source):

* ``o4_targets = {row.identity | row.membership == "o4-target"}``
* ``o3_complete = {row.identity | row.o3_complete is true}``

The checker fails closed unless ``len(o4_targets) == 77``,
``len(o3_complete) == 13``, ``MIGRATED_IDENTITIES == o3_complete``, and the
two sets are disjoint; it also fails closed if any O4 target is missing from
the accepted integrated review or from the O1 reviewed-decision entries.

Scanned structured lifecycle-obligation fields, **only for identities in
``o4_targets``** (never prose):

* O1 reviewed decisions : ``required_evidence``
* accepted O4 review    : ``target.evidence_needed`` and ``dependencies``
* O4 execution register : ``validation_evidence_requirement`` and
  ``dependencies``

Non-target records — merged rows, removed rows, runtime-strategy metadata,
and the frozen-thirteen rows — are deliberately outside the target scan; the
frozen thirteen are independently pinned through exact equality with
``MIGRATED_IDENTITIES``. An item is an O3 lifecycle obligation when it
mentions ``O3`` together with ``transition`` or ``admission``
(case-insensitive); historical/contextual mentions of O3 in notes,
rationales, or open-decision prose are never scanned.

Usage:
    python scripts/check_o4_lifecycle_consistency.py
"""

from __future__ import annotations

from pathlib import Path
import json
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]

O1_DECISIONS_PATH = "docs/method-conformance/o1/authority-review-decisions.yaml"
REVIEW_PATH = "docs/method-conformance/o4/ontology-review/integrated-review.json"
REGISTER_PATH = "docs/method-conformance/o4/o4-execution-register.json"

FROZEN_COUNT = 13
O4_TARGET_COUNT = 77


def is_o3_lifecycle_obligation(item: object) -> bool:
    """True when an obligation item requires a future O3 transition/admission.

    The detector is item-scoped and requires both the O3 token and a
    transition/admission action word, so historical or contextual prose that
    merely mentions O3 never counts as a violation.
    """
    text = str(item).lower()
    return "o3" in text and ("transition" in text or "admission" in text)


def _migrated_identities() -> tuple:
    try:
        from de4sdv.semantic.o3_bundle import MIGRATED_IDENTITIES
    except ImportError:  # Direct execution sets scripts/ as sys.path[0].
        sys.path.insert(0, str(REPO_ROOT))
        from de4sdv.semantic.o3_bundle import MIGRATED_IDENTITIES
    return tuple(MIGRATED_IDENTITIES)


def _scan_items(errors: list[str], identity: str, source: str, field: str, items) -> None:
    for item in items or []:
        if is_o3_lifecycle_obligation(item):
            errors.append(
                f"{source}: {identity} (O4 target, not an O3 identity) carries a "
                f"future O3 lifecycle obligation in {field}: {item!r}"
            )


def run_all_checks(root: Path) -> list[str]:
    errors: list[str] = []
    migrated = set(_migrated_identities())

    # --- authoritative membership from the generated execution register ---
    register = json.loads((root / REGISTER_PATH).read_text(encoding="utf-8"))
    register_rows = [row for row in register.get("rows", []) if isinstance(row, dict)]
    register_index = {str(row.get("identity")): row for row in register_rows}
    o4_targets = {
        str(row.get("identity"))
        for row in register_rows
        if row.get("membership") == "o4-target"
    }
    o3_complete = {
        str(row.get("identity"))
        for row in register_rows
        if row.get("o3_complete") is True
    }

    if len(o4_targets) != O4_TARGET_COUNT:
        errors.append(
            f"{REGISTER_PATH}: o4_targets must be exactly {O4_TARGET_COUNT}; "
            f"found {len(o4_targets)}"
        )
    if len(o3_complete) != FROZEN_COUNT:
        errors.append(
            f"{REGISTER_PATH}: o3_complete must be exactly {FROZEN_COUNT}; "
            f"found {len(o3_complete)}"
        )
    if migrated != o3_complete:
        errors.append(
            "MIGRATED_IDENTITIES must equal the register's o3_complete set "
            f"(missing: {sorted(migrated - o3_complete)}; extra: {sorted(o3_complete - migrated)})"
        )
    if not o4_targets.isdisjoint(o3_complete):
        errors.append(
            "o4_targets and o3_complete must be disjoint; overlap: "
            f"{sorted(o4_targets & o3_complete)}"
        )

    # --- coverage: every O4 target must be present in both sources ---
    review = json.loads((root / REVIEW_PATH).read_text(encoding="utf-8"))
    review_index = {
        str(row.get("identity")): row
        for row in review.get("rows", [])
        if isinstance(row, dict)
    }
    import yaml

    decisions = yaml.safe_load((root / O1_DECISIONS_PATH).read_text(encoding="utf-8"))
    decision_entries = decisions.get("entries") or {}

    for identity in sorted(o4_targets - set(review_index)):
        errors.append(
            f"{REVIEW_PATH}: O4 target {identity} is missing from the accepted "
            "integrated review"
        )
    for identity in sorted(o4_targets - set(decision_entries)):
        errors.append(
            f"{O1_DECISIONS_PATH}: O4 target {identity} is missing from the O1 "
            "reviewed-decision entries"
        )

    # --- target-scoped lifecycle scans ---
    for identity in sorted(o4_targets):
        entry = decision_entries.get(identity)
        if isinstance(entry, dict):
            _scan_items(
                errors, identity, O1_DECISIONS_PATH, "required_evidence",
                entry.get("required_evidence"),
            )
        review_row = review_index.get(identity)
        if review_row is not None:
            _scan_items(
                errors, identity, REVIEW_PATH, "target.evidence_needed",
                (review_row.get("target") or {}).get("evidence_needed"),
            )
            _scan_items(
                errors, identity, REVIEW_PATH, "dependencies",
                review_row.get("dependencies"),
            )
        register_row = register_index.get(identity)
        if register_row is not None:
            _scan_items(
                errors, identity, REGISTER_PATH,
                "validation_evidence_requirement",
                register_row.get("validation_evidence_requirement"),
            )
            _scan_items(
                errors, identity, REGISTER_PATH, "dependencies",
                register_row.get("dependencies"),
            )

    return errors


def main() -> int:
    errors = run_all_checks(REPO_ROOT)
    if errors:
        print("O4 lifecycle consistency check FAILED (O3 stays frozen throughout O4):")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "O4 lifecycle consistency check passed: no retained O4 target carries a "
        "future O3 transition/admission obligation."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
