"""O4 definition-candidate provider — the verified pair's class mappings only.

Since O4 Wave C2 the provider has no legacy fallback: admitted identities
resolve from the verified candidate pair, every other identity is refused
(``KeyError``). Parity is against the model-built kernel contract, whose
definition layer must route each admitted identity to exactly the same
mapping. Incomplete candidate contracts are refused.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from model_contract_fixtures import model_contract

REPO_ROOT = Path(__file__).resolve().parents[1]

from de4sdv.semantic.definition_candidate import (
    DefinitionCandidate,
    load_definition_candidate,
)
from de4sdv.semantic.definition_candidate_provider import DefinitionCandidateProvider
from de4sdv.semantic.kernel_contract import KernelFileMapping


def _candidate() -> DefinitionCandidate:
    return load_definition_candidate(REPO_ROOT)


def _provider(candidate: DefinitionCandidate | None = None) -> DefinitionCandidateProvider:
    return DefinitionCandidateProvider(candidate=candidate if candidate is not None else _candidate())


def test_provider_parity_for_every_admitted_identity():
    contract = model_contract()
    candidate = _candidate()
    provider = _provider(candidate=candidate)
    assert len(candidate.identities) == 22
    for name in candidate.identities:
        resolved = provider.class_mapping(name)
        assert isinstance(resolved, KernelFileMapping)
        assert resolved == contract.class_mapping(name), name
        assert provider.mapping(name) == contract.mapping(name), name


def test_provider_refuses_unadmitted_identities():
    contract = model_contract()
    candidate = _candidate()
    unadmitted = sorted(set(contract.classes) - set(candidate.identities))
    assert unadmitted
    provider = _provider(candidate=candidate)
    for name in unadmitted[:5]:
        with pytest.raises(KeyError, match="not an admitted definition identity"):
            provider.mapping(name)
        with pytest.raises(KeyError):
            provider.class_mapping(name)


def test_provider_has_no_legacy_fallback_surface():
    provider = _provider()
    assert not hasattr(provider, "_legacy")
    assert not hasattr(provider, "relationship_mapping")
    with pytest.raises(TypeError):
        DefinitionCandidateProvider(legacy=object(), candidate=_candidate())  # type: ignore[call-arg]


def test_provider_classes_echo_the_candidate_contract():
    candidate = _candidate()
    provider = _provider(candidate=candidate)
    assert set(provider.classes) == set(candidate.identities)
    for name in candidate.identities:
        contract = candidate.row_for(name)["grounding"]["kernel_binding_contract"]
        assert provider.classes[name] == {
            "kernel": {
                "file": contract["source_file"],
                "declaration": contract["declaration"],
            }
        }


def test_provider_refuses_candidate_without_complete_file_contract():
    broken = DefinitionCandidate(
        source_revision="a" * 40,
        bound_inputs={},
        identities=("Broken",),
        rows=({"identity": "Broken", "grounding": {}},),
        entries=(),
    )
    with pytest.raises(ValueError, match="Broken"):
        DefinitionCandidateProvider(candidate=broken)


def test_provider_is_never_referenced_by_query_surfaces():
    runtime_modules = (
        "de4sdv/semantic/query.py",
        "de4sdv/semantic/traversal.py",
        "de4sdv/semantic/impact.py",
        "de4sdv/semantic/mcp_server.py",
        "de4sdv/semantic/api_binding.py",
        "de4sdv/semantic/kernel_binding_index.py",
    )
    for relative in runtime_modules:
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert "definition_candidate_provider" not in text, relative
