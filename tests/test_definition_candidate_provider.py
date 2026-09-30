"""O4 definition-candidate provider — explicit candidate class resolution.

TDD suite: parity for every admitted identity, adversarial independence from
the legacy contract (a mutated legacy must not change admitted answers, and
unadmitted identities must still delegate), fail-closed refusal of incomplete
candidate contracts, and runtime independence.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

from de4sdv.semantic.definition_candidate import (
    DefinitionCandidate,
    load_definition_candidate,
)
from de4sdv.semantic.definition_candidate_provider import DefinitionCandidateProvider
from de4sdv.semantic.kernel_contract import KernelContract, KernelFileMapping

ONTOLOGY = REPO_ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"


def _legacy() -> KernelContract:
    return KernelContract.load(ONTOLOGY)


def _candidate() -> DefinitionCandidate:
    return load_definition_candidate(REPO_ROOT)


def _provider(
    legacy: KernelContract | None = None, candidate: DefinitionCandidate | None = None
) -> DefinitionCandidateProvider:
    return DefinitionCandidateProvider(
        legacy=legacy if legacy is not None else _legacy(),
        candidate=candidate if candidate is not None else _candidate(),
    )


def _mutated_legacy(
    *, classes: tuple[str, ...] = (), relationships: tuple[str, ...] = ()
) -> KernelContract:
    """A structurally valid legacy contract with deliberate content mutations."""
    legacy = _legacy()
    mutated_classes = {name: dict(spec) for name, spec in legacy.classes.items()}
    for name in classes:
        entry = dict(mutated_classes[name])
        kernel = dict(entry["kernel"])
        kernel["file"] = "mutated/path.sysml"
        kernel["declaration"] = "part def Mutated"
        entry["kernel"] = kernel
        mutated_classes[name] = entry
    mutated_relationships = {
        name: dict(spec) for name, spec in legacy.relationships.items()
    }
    for name in relationships:
        spec = dict(mutated_relationships[name])
        mapping = dict(spec["sysml_mapping"])
        mapping["strategy"] = "mutated-strategy"
        spec["sysml_mapping"] = mapping
        mutated_relationships[name] = spec
    return KernelContract(
        source=legacy.source,
        identity=legacy.identity,
        governed_directory=legacy.governed_directory,
        exclusions=legacy.exclusions,
        classes=mutated_classes,
        relationships=mutated_relationships,
    )


def test_provider_parity_for_every_admitted_identity():
    legacy = _legacy()
    candidate = _candidate()
    provider = _provider(legacy=legacy, candidate=candidate)
    assert len(candidate.identities) == 22
    for name in candidate.identities:
        resolved = provider.class_mapping(name)
        assert isinstance(resolved, KernelFileMapping)
        assert resolved == legacy.class_mapping(name), name
        assert provider.mapping(name) == legacy.mapping(name), name


def test_provider_resolves_admitted_from_candidate_under_legacy_mutation():
    original = _legacy().class_mapping("Requirement")
    mutated = _mutated_legacy(classes=("Requirement",))
    provider = _provider(legacy=mutated)
    resolved = provider.class_mapping("Requirement")
    assert resolved == original
    assert resolved != mutated.class_mapping("Requirement")
    assert provider.mapping("Requirement") == original


def test_provider_delegates_unadmitted_identities():
    legacy = _legacy()
    candidate = _candidate()
    unadmitted = sorted(set(legacy.classes) - set(candidate.identities))
    assert unadmitted
    target = unadmitted[0]
    mutated = _mutated_legacy(classes=(target,))
    provider = _provider(legacy=mutated, candidate=candidate)
    assert provider.class_mapping(target) == mutated.class_mapping(target)
    assert provider.mapping(target) == mutated.mapping(target)


def test_provider_relationships_delegate():
    legacy = _legacy()
    relationship = next(
        name
        for name in sorted(legacy.relationships)
        if "sysml_mapping" in legacy.relationships[name]
    )
    mutated = _mutated_legacy(relationships=(relationship,))
    provider = _provider(legacy=mutated)
    assert provider.relationship_mapping(relationship) == mutated.relationship_mapping(
        relationship
    )
    assert provider.relationship_mapping(relationship).strategy == "mutated-strategy"


def test_provider_surface_matches_facade_contract():
    legacy = _legacy()
    candidate = _candidate()
    provider = _provider(legacy=legacy, candidate=candidate)
    assert provider.identity == legacy.identity
    assert provider.relationships == legacy.relationships
    for name in candidate.identities:
        contract = candidate.row_for(name)["grounding"]["kernel_binding_contract"]
        assert provider.classes[name] == {
            "kernel": {
                "file": contract["source_file"],
                "declaration": contract["declaration"],
            }
        }
    unadmitted = sorted(set(legacy.classes) - set(candidate.identities))[0]
    assert provider.classes[unadmitted] == legacy.classes[unadmitted]


def test_provider_refuses_candidate_without_complete_file_contract():
    broken = DefinitionCandidate(
        source_revision="a" * 40,
        bound_inputs={},
        identities=("Broken",),
        rows=({"identity": "Broken", "grounding": {}},),
        entries=(),
    )
    with pytest.raises(ValueError, match="Broken"):
        DefinitionCandidateProvider(legacy=_legacy(), candidate=broken)


def test_provider_is_never_referenced_by_runtime_modules():
    runtime_modules = (
        "de4sdv/semantic/query.py",
        "de4sdv/semantic/runtime.py",
        "de4sdv/semantic/traversal.py",
        "de4sdv/semantic/impact.py",
        "de4sdv/semantic/mcp_server.py",
        "de4sdv/semantic/api_binding.py",
        "de4sdv/semantic/kernel_binding_index.py",
    )
    for relative in runtime_modules:
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert "definition_candidate_provider" not in text, relative
