"""Kernel pins and element identities bind one to one.

Successor profile pins must resolve to distinct, nonblank element identities.

Ingestion binds each kernel pin under its owning class only. The model-built
kernel contract maps the natively represented successor endpoint classes
(``Function``, ``LogicalElement``, ``PhysicalElement``,
``ValidationScenario``) to the file pin of their unique specializing extension
class (``action def AllocatableFunction`` and so on): the lineage pin the
runtime already served. Ingestion must not emit a second kernel binding for
such a borrowed pin, because the successor routing refuses two ingestion
classes on one pin even when they name the same element
(``test_exact_pin_ambiguity_refuses_even_same_uuid``). The real-data rehearsal
against the ff0311b full-model export found exactly this double binding before
the fix. The binder still resolves the profile class through the routed
extension pin.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from de4sdv.semantic.kernel_contract import KernelContract, KernelFileMapping, declaration_identity
from de4sdv.semantic.validation import validate_ontology_bindings
from model_contract_fixtures import binding, model_facade, model_service

ROOT = Path(__file__).resolve().parents[1]
LINEAGE_PINNED = {
    "Function": "AllocatableFunction",
    "LogicalElement": "LogicalAllocationElement",
    "PhysicalElement": "PhysicalAllocationElement",
    "ValidationScenario": "ValidationPlanningScenario",
}


# ---------------------------------------------------------------------------
# Successor profile pins: distinct, nonblank element identities
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Borrowed lineage pins: one kernel binding per pin
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def contract():
    return KernelContract.from_layers(ROOT)


def test_the_contract_names_its_borrowed_lineage_pins(contract):
    assert dict(contract.lineage_pinned) == LINEAGE_PINNED
    for name, owner in LINEAGE_PINNED.items():
        assert isinstance(contract.mapping(name), KernelFileMapping)
        assert contract.mapping(name) == contract.mapping(owner)


def test_ingestion_validation_binds_each_pin_under_its_owner_only(contract):
    elements, sources = [], {}
    for name in sorted(contract.classes):
        mapping = contract.mapping(name)
        if not isinstance(mapping, KernelFileMapping) or name in contract.lineage_pinned:
            continue
        declared, metaclass = declaration_identity(mapping.declaration)
        element = {"@id": f"id-{name}", "@type": metaclass, "declaredName": declared}
        elements.append(element)
        sources[element["@id"]] = mapping.file
    report = validate_ontology_bindings(contract, elements, sources)
    assert report.passed, report.summary
    statuses = {entry.ontology_class: entry.status for entry in report.entries}
    for name, owner in LINEAGE_PINNED.items():
        assert statuses[name] == "lineage-pinned"
        assert statuses[owner] == "mapped"
    mapped_pins = [(e.mapping["file"], e.mapping["declaration"]) for e in report.entries
                   if e.status == "mapped"]
    assert len(mapped_pins) == len(set(mapped_pins)), "one kernel binding per pin"
    assert report.summary["lineage-pinned"] == len(LINEAGE_PINNED)
