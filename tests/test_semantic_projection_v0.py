"""Tests for the DE4SDV Semantic Projection v0 / API Representation Profile v0
(K slice: derivesRequirementFromNeed)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from de4sdv.sysml_api.errors import IdentityNotFoundError
from de4sdv.sysml_api.revisions import KernelElementBinding
from de4sdv.semantic.projection import (
    PROFILE_SCHEMA,
    PROJECTION_SCHEMA,
    RevisionIdentity,
    build_projection,
    build_representation_profile,
)
from de4sdv.semantic.kernel_binding_index import KernelBindingIndex

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_derivation_predicate_traversal import (  # noqa: E402
    MARKER_DEF_ID,
    _binding_index,
    _contract,
    _elements,
    _default_binding_entries,
)

ROOT = Path(__file__).resolve().parents[1]
REVISION = RevisionIdentity(
    git_commit="0" * 40,
    sysml_project_id="proj-0001",
    sysml_commit_id="commit-0001",
)

REQ_DEF_ID = "reqdef-uuid-0021"
NEED_DEF_ID = "needdef-uuid-0022"


def _definition_elements() -> list[dict]:
    return [
        {
            "@id": REQ_DEF_ID,
            "@type": "RequirementDefinition",
            "declaredName": "RequirementCandidate",
        },
        {
            "@id": NEED_DEF_ID,
            "@type": "RequirementDefinition",
            "declaredName": "StakeholderNeedCandidate",
        },
    ]


def _projection_binding_index() -> KernelBindingIndex:
    return _binding_index(
        [
            *_default_binding_entries(),
            KernelElementBinding(
                ontology_class="Requirement",
                element_id=REQ_DEF_ID,
                source_file=(
                    "textual-notation-of-model/packages/methods/de4sdv/"
                    "de4sdv_method_context.sysml"
                ),
                declaration="requirement def RequirementCandidate",
            ),
            KernelElementBinding(
                ontology_class="Need",
                element_id=NEED_DEF_ID,
                source_file=(
                    "textual-notation-of-model/packages/methods/de4sdv/"
                    "de4sdv_method_context.sysml"
                ),
                declaration="requirement def StakeholderNeedCandidate",
            ),
        ]
    )


def _by_id() -> dict[str, dict]:
    return {
        item["@id"]: item
        for item in [*_elements(), *_definition_elements()]
    }


def test_projection_row_binds_revision_and_validated_groundings() -> None:
    projection = build_projection(
        _contract(), _projection_binding_index(), REVISION, _by_id()
    )
    assert projection["schema"] == PROJECTION_SCHEMA
    assert projection["revision_binding"]["git_commit"] == REVISION.git_commit
    predicate = projection["predicate"]
    assert predicate["identity"] == "derivesRequirementFromNeed"
    assert predicate["domain"] == "Requirement"
    assert predicate["range"] == "Need"
    assert predicate["semantic_strength"] == "derivation"
    assert predicate["support_state"] == "supported"
    generated_from = projection["revision_binding"]["generated_from"]
    assert set(generated_from["model_definitions"]) == {
        REQ_DEF_ID,
        NEED_DEF_ID,
        MARKER_DEF_ID,
    }


def test_projection_forbids_representation_mechanics() -> None:
    projection = build_projection(
        _contract(), _projection_binding_index(), REVISION, _by_id()
    )
    text = json.dumps(projection)
    for forbidden in ("property_path", "serializer", "dispatch", "transport"):
        assert forbidden not in text.lower()


def test_projection_deterministic_for_identical_inputs() -> None:
    """UG-23: same semantic inputs produce the same canonical payload."""
    first = build_projection(_contract(), _projection_binding_index(), REVISION, _by_id())
    second = build_projection(_contract(), _projection_binding_index(), REVISION, _by_id())
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_projection_fails_closed_without_marker_binding() -> None:
    """UG-24: missing validated grounding blocks generation."""
    with pytest.raises(IdentityNotFoundError):
        build_projection(
            _contract(), _binding_index([]), REVISION, _by_id()
        )


def test_profile_carries_mechanics_and_echoes_projection_meaning() -> None:
    profile = build_representation_profile(
        _contract(), _projection_binding_index(), REVISION, _by_id()
    )
    assert profile["schema"] == PROFILE_SCHEMA
    assert profile["for_predicate"] == "derivesRequirementFromNeed"
    witness = profile["witness"]
    assert witness["api_metaclass"] == "Dependency"
    assert witness["property_paths"]["source"] == "source"
    # The profile may not redefine meaning: its domain/range/strength fields
    # are echoes of the projection row, not independent definitions.
    assert profile["domain_from_projection"] == "Requirement"
    assert profile["range_from_projection"] == "Need"
    assert profile["semantic_strength_from_projection"] == "derivation"


def test_profile_without_projection_inputs_fails_closed() -> None:
    with pytest.raises(IdentityNotFoundError):
        build_representation_profile(
            _contract(), _binding_index([]), REVISION, _by_id()
        )
