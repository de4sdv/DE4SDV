"""IncrementBoundaryConcern: one model-projected canonical concern identity.

The owner-approved phase 1 concern contract needs the canonical identity of the
increment-boundary concern, so that a check can exclude by the validated type
rather than by a name. The concern definition was therefore promoted out of the
kernel-internal declarations manifest into the kernel-vocabulary admission: the
model home is the existing ``concern def IncrementBoundaryConcern`` with a
directly owned documentation, and the projection row stays vocabulary-only (no
traversal claim, no second definition, no new ontology authority).

These tests pin the positive routing and classification only; the negative
generator guards live in ``tests/test_kernel_vocabulary_projection.py``.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA = "de4sdv/semantic/contract-data/"
CONCERNS_FILE = ("textual-notation-of-model/packages/methods/de4sdv/"
                 "de4sdv_method_concerns_and_viewpoints.sysml")
DECLARATION = "concern def IncrementBoundaryConcern"
IDENTITY = "IncrementBoundaryConcern"


def _json(relative: str):
    return json.loads((REPO_ROOT / relative).read_text(encoding="utf-8"))


def _row(document: dict, identity: str) -> dict:
    for row in document["rows"]:
        if row["identity"] == identity:
            return row
    raise AssertionError(f"{identity} is not projected by {document['schema']}")


def _entry(document: dict, identity: str) -> dict:
    for entry in document["entries"]:
        if entry["for_concept"] == identity:
            return entry
    raise AssertionError(f"{identity} has no profile entry in {document['schema']}")


def test_the_checker_resolves_the_canonical_identity_as_a_file_mapped_concern():
    """The served kernel contract answers IncrementBoundaryConcern with the
    validated file + declaration binding, so a check resolves the canonical
    element identity (UUID) of the bound concern definition, not a name."""
    from de4sdv.semantic.kernel_contract import KernelContract, KernelFileMapping

    contract = KernelContract.from_layers(REPO_ROOT)
    mapping = contract.class_mapping(IDENTITY)
    assert isinstance(mapping, KernelFileMapping)
    assert (mapping.file, mapping.declaration) == (CONCERNS_FILE, DECLARATION)
    assert contract.governed_directory == "textual-notation-of-model/packages/methods/de4sdv"
    # The binding names the declaration that the model file really owns.
    assert DECLARATION in (REPO_ROOT / CONCERNS_FILE).read_text(encoding="utf-8")
    # Vocabulary-only: the identity is no traversal provider and no API claim.
    assert IDENTITY in contract.classes
    assert IDENTITY not in (contract.refused or {})


def test_the_projection_row_carries_the_model_owned_definition_only():
    """The row's text is the documentation the concern definition owns; the
    require constraint and its documentation stay as they were."""
    document = _json(DATA + "kernel-vocabulary-projection.json")
    row = _row(document, IDENTITY)
    assert row["semantic_kind"] == "class"
    assert row["admission_class"] == "definition"
    assert row["accounting"] == "method-admitted"
    assert row["boundary"] == "none"
    source = (REPO_ROOT / CONCERNS_FILE).read_text(encoding="utf-8")
    # Strip the comment-continuation stars, then compare the documentation text.
    plain = " ".join(re.sub(r"(?m)^[ \t]*\*[ \t]?", "", source).split())
    text = " ".join(row["definition"]["documentation"].split())
    assert text in plain
    witness = row["definition"]["documentation_witness"]
    assert witness == {"source_file": CONCERNS_FILE, "owner": DECLARATION,
                       "form": "owned-doc", "documentation_name": None,
                       "documentation_index": 0}
    assert row["definition"]["documentation_observation"] == "model-owned-documentation"
    assert row["grounding"]["kernel_binding_contract"] == {
        "source_file": CONCERNS_FILE, "declaration": DECLARATION}
    assert row["grounding"]["ontology_relations"] == {"sub_class_of": None, "disjoint_with": []}
    assert "no authored-ontology comparison exists" in row["grounding"]["contract_source"]
    assert row["support"] == "vocabulary-only"
    assert row["traversal"] is False
    assert row["api_identity"] == "unclaimed"


def test_the_profile_names_the_native_concern_representation():
    entry = _entry(_json(DATA + "kernel-vocabulary-profile.json"), IDENTITY)
    assert entry["representation_class"] == "concern-definition"
    assert entry["binding_contract_echo"] == {"source_file": CONCERNS_FILE,
                                              "owner": DECLARATION,
                                              "api_metaclass": "ConcernDefinition"}
    assert entry["witness_forms"] == [
        "ownedRelationship -> OwningMembership -> Documentation (anonymous, owner-selected index)"]


def test_the_generator_classifies_the_concern_declaration_form():
    """The admission is generated from the declaration kind, not by a special
    case for this identity: ``concern`` maps to the native concern definition."""
    from de4sdv.semantic.kernel_vocabulary_projection import API_METACLASSES, REPRESENTATION_CLASSES

    assert REPRESENTATION_CLASSES["concern"] == "concern-definition"
    assert API_METACLASSES["concern"] == "ConcernDefinition"


def test_the_admission_replaces_the_kernel_internal_listing():
    """Projected or listed, never both: the concern is no longer accounted as a
    kernel-internal declaration, and the coverage gate has no residual."""
    from de4sdv.semantic import model_projection_coverage as coverage

    internal = yaml.safe_load((REPO_ROOT / coverage.KERNEL_INTERNAL_PATH).read_text(encoding="utf-8"))
    listed = internal["declarations"].get(CONCERNS_FILE) or {}
    assert DECLARATION not in listed
    assert listed, "the other method concerns stay kernel-internal"

    report = coverage.build_report(REPO_ROOT)
    assert report["summary"]["residual_empty"] is True
    assert report["kernel_accounting_errors"] == []
    declaration = report["kernel_declarations"][f"{CONCERNS_FILE}::{DECLARATION}"]
    assert declaration["status"] == "projected"
    assert declaration["layer"] == "definition-batch2"
    assert report["identities"][IDENTITY]["status"] == "projected"
    assert report["identities"][IDENTITY]["layer"] == "definition-batch2"
    assert coverage.run_check_errors(REPO_ROOT) == []
