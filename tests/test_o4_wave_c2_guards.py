"""Successor profile pins must resolve to distinct, nonblank element identities."""
from __future__ import annotations

import pytest

from model_contract_fixtures import binding, model_facade, model_service


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
