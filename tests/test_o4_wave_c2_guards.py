"""O4 Wave C2 guards without a dedicated test elsewhere.

- the successor-identity overlap guard of ``assemble_model_services``
  (restored in C2: two profile pins can never share, or lack, one element
  identity);
- the CLOSED consumer-ledger rule (owner decision D7): once the ledger is
  CLOSED, a live reference may only carry a non-executable role with status
  ``not-applicable``.
"""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

from model_contract_fixtures import binding, model_facade, model_service

ROOT = Path(__file__).resolve().parents[1]


def _pin_bindings(element_ids):
    pins = {**model_facade().profile["classes"], **model_facade().profile["carriers"]}
    items = list(pins.items())[:len(element_ids)]
    return [{"ontology_class": name, "element_id": element_id, "source_file": pin["file"],
             "declaration": pin["declaration"]}
            for (name, pin), element_id in zip(items, element_ids)]


def test_two_successor_pins_sharing_one_element_identity_are_refused():
    revision_binding = binding(kernel_bindings=_pin_bindings(["same-uuid", "same-uuid"]))
    with pytest.raises(ValueError, match="overlapping or blank successor kernel identities"):
        model_service(revision_binding, object())


def test_distinct_successor_pin_identities_assemble():
    revision_binding = binding(kernel_bindings=_pin_bindings(["uuid-a", "uuid-b"]))
    assert model_service(revision_binding, object()) is not None


def _ledger_and_scan():
    from de4sdv.semantic import o4_consumers as oc

    return oc, oc.load_ledger(ROOT / oc.LEDGER_PATH), oc.scan_tracked_files(ROOT)


def test_committed_ledger_is_closed_and_passes():
    oc, ledger, scan = _ledger_and_scan()
    assert str(ledger["status"]).startswith("CLOSED")
    assert oc.check_ledger(ROOT, ledger, scan) == []
    live = [row for rel, row in ledger["entries"].items() if rel in scan]
    assert live and all(row["role"] in oc.CLOSED_LIVE_ROLES for row in live)
    assert all(row["retirement_status"] == "not-applicable" for row in live)


@pytest.mark.parametrize("field, value", [("role", "runtime-consumer"), ("role", "gate"),
                                          ("retirement_status", "active"),
                                          ("retirement_status", "pending")])
def test_closed_ledger_refuses_an_executable_or_open_live_row(field, value):
    oc, ledger, scan = _ledger_and_scan()
    mutated = copy.deepcopy(ledger)
    rel = next(rel for rel in sorted(scan) if rel in mutated["entries"])
    mutated["entries"][rel][field] = value
    errors = oc.check_ledger(ROOT, mutated, scan)
    assert any("the ledger is CLOSED" in e and rel in e for e in errors), errors


def test_an_open_ledger_still_accepts_executable_roles():
    oc, ledger, scan = _ledger_and_scan()
    mutated = copy.deepcopy(ledger)
    mutated["status"] = "PREPARED"
    rel = next(rel for rel in sorted(scan) if rel in mutated["entries"])
    mutated["entries"][rel]["role"] = "runtime-consumer"
    assert not any("CLOSED" in e for e in oc.check_ledger(ROOT, mutated, scan))
