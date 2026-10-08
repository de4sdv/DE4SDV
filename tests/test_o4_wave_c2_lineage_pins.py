"""O4 Wave C2: ingestion binds each kernel pin under its owning class only.

The model-built kernel contract maps the natively represented successor
endpoint classes (``Function``, ``LogicalElement``, ``PhysicalElement``,
``ValidationScenario``) to the file pin of their unique specializing
extension class (``action def AllocatableFunction`` and so on): the lineage
pin the Wave B runtime already served. Ingestion must not emit a second
kernel binding for such a borrowed pin, because the successor routing refuses
two ingestion classes on one pin even when they name the same element
(``test_exact_pin_ambiguity_refuses_even_same_uuid``). The real-data
rehearsal against the ff0311b full-model export found exactly this double
binding before the fix. The binder still resolves the profile class through
the routed extension pin.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from de4sdv.semantic.kernel_contract import KernelContract, KernelFileMapping, declaration_identity
from de4sdv.semantic.validation import validate_ontology_bindings

ROOT = Path(__file__).resolve().parents[1]
LINEAGE_PINNED = {
    "Function": "AllocatableFunction",
    "LogicalElement": "LogicalAllocationElement",
    "PhysicalElement": "PhysicalAllocationElement",
    "ValidationScenario": "ValidationPlanningScenario",
}


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
