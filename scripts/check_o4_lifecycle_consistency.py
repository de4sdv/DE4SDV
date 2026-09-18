#!/usr/bin/env python3
"""Fail-closed O4 lifecycle invariant: O3 stays frozen throughout O4.

The frozen O3 authority transition is complete for exactly the thirteen
identities in ``MIGRATED_IDENTITIES`` (``de4sdv.semantic.o3_bundle``). No
other O4-target identity may require a future O3 authority-transition or
O3-admission obligation anywhere in its governed lifecycle records; O4
targets reuse the O2 admission / generated-projection machinery and never
join or reopen O3.

Scanned structured lifecycle-obligation fields (never prose):

* O1 reviewed decisions : ``required_evidence``
* accepted O4 review    : ``target.evidence_needed`` and ``dependencies``
* O4 execution register : ``validation_evidence_requirement`` and
  ``dependencies``

An item is an O3 lifecycle obligation when it mentions ``O3`` together with
``transition`` or ``admission`` (case-insensitive). Historical/contextual
mentions of O3 in notes, rationales, or open-decision prose are deliberately
not scanned — the bare token ``O3`` is never a violation, and the thirteen
frozen identities may legitimately retain their O3 transition evidence.

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


def is_o3_lifecycle_obligation(item: object) -> bool:
    """True when an obligation item requires a future O3 transition/admission.

    The detector is item-scoped and requires both the O3 token and a
    transition/admission action word, so historical or contextual prose that
    merely mentions O3 (or the thirteen frozen identities' legitimate O3
    transition evidence, which is exempted by identity membership) never
    counts as a violation.
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


def _scan_items(errors: list[str], identity: str, frozen: set, source: str, field: str, items) -> None:
    if identity in frozen:
        return
    for item in items or []:
        if is_o3_lifecycle_obligation(item):
            errors.append(
                f"{source}: {identity} (not an O3 identity) carries a future "
                f"O3 lifecycle obligation in {field}: {item!r}"
            )


def run_all_checks(root: Path) -> list[str]:
    errors: list[str] = []
    migrated = _migrated_identities()
    if len(migrated) != FROZEN_COUNT:
        errors.append(
            f"MIGRATED_IDENTITIES must be exactly {FROZEN_COUNT}; found {len(migrated)}"
        )
    frozen = set(migrated)

    import yaml

    decisions = yaml.safe_load((root / O1_DECISIONS_PATH).read_text(encoding="utf-8"))
    for identity, entry in (decisions.get("entries") or {}).items():
        _scan_items(
            errors, identity, frozen, O1_DECISIONS_PATH, "required_evidence",
            entry.get("required_evidence"),
        )

    review = json.loads((root / REVIEW_PATH).read_text(encoding="utf-8"))
    for row in review.get("rows", []):
        identity = str(row.get("identity"))
        _scan_items(
            errors, identity, frozen, REVIEW_PATH, "target.evidence_needed",
            (row.get("target") or {}).get("evidence_needed"),
        )
        _scan_items(
            errors, identity, frozen, REVIEW_PATH, "dependencies",
            row.get("dependencies"),
        )

    register = json.loads((root / REGISTER_PATH).read_text(encoding="utf-8"))
    for row in register.get("rows", []):
        identity = str(row.get("identity"))
        _scan_items(
            errors, identity, frozen, REGISTER_PATH,
            "validation_evidence_requirement",
            row.get("validation_evidence_requirement"),
        )
        _scan_items(
            errors, identity, frozen, REGISTER_PATH, "dependencies",
            row.get("dependencies"),
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
        "O4 lifecycle consistency check passed: no non-O3 O4 target carries a "
        "future O3 transition/admission obligation."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
