"""Lane B: method-contract binding and candidate production tests.

Tests are written against the A specification (docs/method-conformance/)
and the frozen baseline (Increment B, Section 12). They fail before the
binder/traversal/candidate-path implementation exists — that is the point
(test-first per Increment B task list).

In-memory synthetic fixtures only; no copies of real model files.

B-owned acceptance cases covered here:
- MC-10: method-contract objects leak into engineering populations -> rejected;
         shared type references remain legal.
- MC-14: reimport with different UUIDs preserves explicit-identity
         correspondence and semantic relationships (no name merging).
- MC-36: selected-commit export excludes uncommitted content and declares
         its commit identity; dirty-tree evaluation requests are refused.
- MC-37: concurrent candidates stay isolated; published accepted-baseline
         selection unchanged; candidate validation does not imply approval.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------
# Synthetic pilot graph (in-memory, mimics the serialized API shapes the real
# pilot produces — shapes validated against tests/test_native_semantic_traversal.py
# and the merged pilot model; no real model content copied).
# --------------------------------------------------------------------------

def _base_element(element_id: str, element_type: str, name: str, **extra: object) -> dict:
    element = {
        "@id": element_id,
        "@type": element_type,
        "declaredName": name,
    }
    element.update(extra)
    return element


def _pilot_graph(
    *,
    usage_uuids: tuple[str, ...] = tuple(
        f"00000000-0000-4000-8000-{i:012d}" for i in range(1, 7)
    ),
    short_names: tuple[str, ...] = (
        "VC-AEBS-009D-01",
        "VC-AEBS-009D-02",
        "VC-AEBS-009D-03",
        "VC-AEBS-009D-04",
        "VC-AEBS-009D-05",
        "VC-AEBS-009D-06",
    ),
) -> list[dict]:
    """Synthetic pilot graph: definition, six usages (with declaredShortName),
    objective + verify memberships (inherited witnesses), subject
    memberships to per-scenario benches, method metadata owners."""
    elements: list[dict] = []
    definition = _base_element(
        "00000000-0000-4000-8000-0000000000d0",
        "VerificationCaseDefinition",
        "ConsciousOverrideVerification",
        declaredShortName="VC-AEBS-009D-DE",
    )
    elements.append(definition)
    scenario_names = (
        "fresh_false_control",
        "fresh_true_conscious_override",
        "stale",
        "missing",
        "malformed",
        "future_stamped",
    )
    for uuid, short, scenario in zip(usage_uuids, short_names, scenario_names):
        usage = _base_element(
            uuid,
            "VerificationCaseUsage",
            f"override{scenario.replace('_', ' ').title().replace(' ', '')}Verification",
            declaredShortName=short,
        )
        elements.append(usage)
        # Usage-level verification-method metadata: the @VerificationMethod
        # annotation serializes as a MetadataUsage owned via an
        # OwningMembership whose memberElement is the metadata usage (real
        # licensed-export shape).
        elements.append(
            {
                "@id": uuid[:-2] + "mm1",
                "@type": "OwningMembership",
                "owningRelatedElement": {"@id": uuid},
                "memberElement": {"@id": uuid[:-2] + "mu1"},
                "ownedRelatedElement": [{"@id": uuid[:-2] + "mu1"}],
            }
        )
        usage: dict = elements[-2]
        usage.setdefault("ownedRelationship", []).append(
            {"@id": uuid[:-2] + "mm1"}
        )
        elements.append(
            {
                "@id": uuid[:-2] + "mu1",
                "@type": "MetadataUsage",
                "owningRelationship": {"@id": uuid[:-2] + "mm1"},
            }
        )
        # Specialization witness in the serializer's real shape: a
        # FeatureTyping whose specific end is the usage and whose general/type
        # end is the shared definition (verified against a real export).
        elements.append(
            {
                "@id": uuid[:-2] + "g1",
                "@type": "FeatureTyping",
                "owningRelatedElement": {"@id": uuid},
                "specific": {"@id": uuid},
                "typedFeature": {"@id": uuid},
                "general": {"@id": "00000000-0000-4000-8000-0000000000d0"},
                "type": {"@id": "00000000-0000-4000-8000-0000000000d0"},
            }
        )
        # SubjectMembership: usage owns a bench member
        bench_id = uuid[:-2] + "b1"
        elements.append(
            _base_element(
                bench_id,
                "PartUsage",
                f"{scenario.replace('_', '')}Bench",
            )
        )
        elements.append(
            {
                "@id": uuid[:-2] + "m1",
                "@type": "SubjectMembership",
                "owningRelatedElement": {"@id": uuid},
                "memberElement": {"@id": bench_id},
            }
        )
    # Objective + verify memberships on the definition (inherited witnesses)
    elements.append(
        _base_element(
            "00000000-0000-4000-8000-0000000000e0",
            "RequirementUsage",
            "evidenceObjective",
        )
    )
    elements.append(
        {
            "@id": "00000000-0000-4000-8000-0000000000e1",
            "@type": "ObjectiveMembership",
            "owningRelatedElement": {"@id": "00000000-0000-4000-8000-0000000000d0"},
            "memberElement": {"@id": "00000000-0000-4000-8000-0000000000e0"},
        }
    )
    for index, req_name in enumerate(
        (
            "evidenceContractClosedOverrideScenario",
            "evidenceContractOverrideFreshnessReplay",
            "evidenceContractIndependentVerdict",
        )
    ):
        req_id = f"00000000-0000-4000-8000-0000000000e{index + 2}"
        elements.append(
            _base_element(
                req_id,
                "RequirementUsage",
                req_name,
                declaredShortName=f"EC-009D-{index + 1:02d}",
            )
        )
        elements.append(
            {
                "@id": f"00000000-0000-4000-8000-0000000000f{index}",
                "@type": "RequirementVerificationMembership",
                "owningRelatedElement": {"@id": "00000000-0000-4000-8000-0000000000e0"},
                "memberElement": {"@id": req_id},
            }
        )
    # Definition-action metadata: MetadataUsage owned by each action usage.
    for action_id in ("00000000-0000-4000-8000-0000000000a1",
                      "00000000-0000-4000-8000-0000000000a2",
                      "00000000-0000-4000-8000-0000000000a3"):
        elements.append(
            {
                "@id": action_id,
                "@type": "ActionUsage",
                "owner": {"@id": "00000000-0000-4000-8000-0000000000d0"},
            }
        )
        elements.append(
            {
                "@id": action_id[:-2] + "mu",
                "@type": "MetadataUsage",
                "owner": {"@id": action_id},
                "declaredName": "VerificationMethod",
            }
        )
    return elements


def _kernel_binding_for(short_name: str, element_id: str) -> dict:
    return {
        "ontology_class": f"pilot:{short_name}",
        "element_id": element_id,
        "source_file": "synthetic",
        "declaration": "verification def synthetic",
    }


# --------------------------------------------------------------------------
# Explicit contribution set vs evaluation scope (frozen baseline Section 6)
# --------------------------------------------------------------------------

def test_contribution_and_evaluation_scope_are_distinct_sets() -> None:
    from de4sdv.semantic.method_contract import MethodEvaluationScope

    # The six usages are pre-existing (reused) verification cases: they are in
    # evaluation scope but NOT in the contribution set of the binding increment.
    contribution = {"pre-existing"}
    scope = MethodEvaluationScope(
        increment_id="INC-AEBS-009D",
        contribution_set=contribution,
        evaluation_scope_subjects={
            "VC-AEBS-009D-01",
            "VC-AEBS-009D-02",
            "VC-AEBS-009D-03",
            "VC-AEBS-009D-04",
            "VC-AEBS-009D-05",
            "VC-AEBS-009D-06",
        },
        subject_types={"VerificationCaseUsage"},
        population_policy={"VC-AEBS-009D-01": (1, 1)},
        exclusions={},
    )
    assert scope.evaluation_scope_subjects - scope.contribution_set == set(
        scope.evaluation_scope_subjects
    ), "reused verification cases are evaluation scope, not contributions"
    assert scope.contribution_set != scope.evaluation_scope_subjects


# --------------------------------------------------------------------------
# MC-10: method-contract leakage into engineering populations
# --------------------------------------------------------------------------

def test_mc10_method_contract_objects_rejected_from_engineering_populations() -> None:
    from de4sdv.semantic.method_contract import engineering_subjects_only

    method_object = _base_element(
        "00000000-0000-4000-8000-000000000c01",
        "PartUsage",
        "phase10MethodContractObligationCarrier",
        declaredShortName="PC-009D-01",
    )
    engineering_element = _base_element(
        "00000000-0000-4000-8000-000000000c02",
        "VerificationCaseUsage",
        "overrideTrueVerification",
    )
    # An engineering population built from these elements must not include
    # the method-contract carrier.
    population = engineering_subjects_only(
        [method_object, engineering_element],
        eligible_types={"VerificationCaseUsage"},
        method_id_prefixes={"PC-"},
    )
    assert [element_id for element_id, _ in population] == [
        "00000000-0000-4000-8000-000000000c02"
    ]


def test_mc10_scope_validation_failure_on_empty_registry() -> None:
    """The defined scope-validation failure: MC-10 rejection requires a
    non-empty governed prefix registry; an empty registry is a refused
    evaluation, not a silently unfiltered population."""
    from de4sdv.semantic.method_contract import engineering_subjects_only

    method_object = _base_element(
        "00000000-0000-4000-8000-000000000c01",
        "PartUsage",
        "phase10MethodContractObligationCarrier",
        declaredShortName="PC-009D-01",
    )
    engineering_element = _base_element(
        "00000000-0000-4000-8000-000000000c02",
        "VerificationCaseUsage",
        "overrideTrueVerification",
    )
    with pytest.raises(ValueError, match="method_id_prefixes"):
        engineering_subjects_only(
            [method_object, engineering_element],
            eligible_types={"VerificationCaseUsage"},
            method_id_prefixes=set(),
        )


def test_mc10_shared_type_references_remain_legal() -> None:
    from de4sdv.semantic.method_contract import engineering_subjects_only

    # A method-contract object legitimately referencing a shared engineering
    # TYPE (e.g. its subject_selector type names VerificationCaseUsage) does
    # not leak: the type reference is not membership.
    method_object = _base_element(
        "00000000-0000-4000-8000-000000000d01",
        "PartUsage",
        "pilotScopeCarrier",
        declaredShortName="PC-009D-SCOPE",
    )
    engineering_element = _base_element(
        "00000000-0000-4000-8000-000000000d02",
        "VerificationCaseUsage",
        "overrideTrueVerification",
    )
    population = engineering_subjects_only(
        [method_object, engineering_element],
        eligible_types={"VerificationCaseUsage"},
        method_id_prefixes={"PC-"},
    )
    assert ("00000000-0000-4000-8000-000000000d02", engineering_element) in population


# --------------------------------------------------------------------------
# MC-14: reimport identity correspondence
# --------------------------------------------------------------------------

def test_mc14_reimport_preserves_explicit_identity_correspondence() -> None:
    from de4sdv.sysml_api.identity import resolve_identity
    from de4sdv.sysml_api.errors import IdentityNotFoundError

    original = _pilot_graph()
    # Reimport assigned different UUIDs; explicit identifiers survive.
    remapped = _pilot_graph(
        usage_uuids=tuple(f"11111111-0000-4000-8000-{i:012d}" for i in range(1, 7))
    )
    for original_element, reimported in zip(original, remapped):
        if "declaredShortName" in original_element:
            explicit = original_element["declaredShortName"]
            resolution = resolve_identity(explicit, remapped)
            assert resolution.level == "stable-explicit-id"
            # Semantic relationships preserved: the usage keeps its name.
            assert resolution.element["declaredName"] == original_element["declaredName"]
    # UUID equality is NOT required and name-based merging is NOT used:
    with pytest.raises(IdentityNotFoundError):
        resolve_identity("00000000-0000-4000-8000-000000000001", remapped)


def test_mc14_missing_explicit_identifier_fails_closed() -> None:
    from de4sdv.sysml_api.identity import resolve_identity
    from de4sdv.sysml_api.errors import IdentityNotFoundError

    graph = _pilot_graph()
    # Drop the short name from the '-02' usage: identity by explicit id now
    # fails closed (no name-based fallback).
    for element in graph:
        if element.get("declaredShortName") == "VC-AEBS-009D-02":
            del element["declaredShortName"]
            break
    with pytest.raises(IdentityNotFoundError):
        resolve_identity("VC-AEBS-009D-02", graph)


def test_mc14_duplicate_explicit_identifier_fails_closed() -> None:
    from de4sdv.sysml_api.identity import resolve_identity
    from de4sdv.sysml_api.errors import AmbiguousIdentityError

    graph = _pilot_graph()
    # A second usage claims the same short name: duplicate bindings error.
    graph.append(
        _base_element(
            "00000000-0000-4000-8000-000000000999",
            "VerificationCaseUsage",
            "aDifferentUsage",
            declaredShortName="VC-AEBS-009D-02",
        )
    )
    with pytest.raises(AmbiguousIdentityError):
        resolve_identity("VC-AEBS-009D-02", graph)


def test_mc14_independent_transactions_correspond_by_explicit_id() -> None:
    """MC-14 two-transaction design: two INDEPENDENT export transactions of
    the same source carry different serializer UUIDs but the same persistent
    explicit identities. Correspondence is established by persistent identity
    alone; declared names are compared only as attributes after identity is
    established, never as keys, and never by UUID equality.
    (The privileged two-import run provides the real-serializer version of
    this evidence.)"""
    from de4sdv.semantic.method_contract import CorrespondenceMap

    first = _pilot_graph()
    second = _pilot_graph(
        usage_uuids=tuple(f"22222222-0000-4000-8000-{i:012d}" for i in range(1, 7))
    )
    first_by_short = {
        e["declaredShortName"]: e
        for e in first
        if "declaredShortName" in e and e["declaredShortName"].startswith("VC-AEBS-009D-0")
    }
    second_by_short = {
        e["declaredShortName"]: e
        for e in second
        if "declaredShortName" in e and e["declaredShortName"].startswith("VC-AEBS-009D-0")
    }
    mapping = CorrespondenceMap(
        {
            short: second_by_short[short]["@id"]
            for short in first_by_short
        }
    )
    for short, original in first_by_short.items():
        reimported_id = mapping.uuid_for(short)
        assert reimported_id != original["@id"], (
            "independent transactions must NOT reuse serializer UUIDs"
        )
        assert second_by_short[short]["declaredName"] == original["declaredName"]
    # Correspondence covers every explicit identity exactly once.
    assert len(mapping.mapping) == 6


def test_mc14_wrong_target_type_fails_closed() -> None:
    from de4sdv.sysml_api.identity import resolve_identity
    from de4sdv.sysml_api.errors import IdentityNotFoundError

    graph = _pilot_graph()
    with pytest.raises(IdentityNotFoundError):
        resolve_identity(
            "VC-AEBS-009D-02",
            graph,
            expected_type="PartUsage",
        )


def test_mc14_contradictory_correspondence_rejected() -> None:
    from de4sdv.semantic.method_contract import CorrespondenceMap

    mapping = CorrespondenceMap(
        {
            "VC-AEBS-009D-01": "00000000-0000-4000-8000-000000000001",
            "VC-AEBS-009D-02": "00000000-0000-4000-8000-000000000002",
        }
    )
    # Two explicit identities claimed to correspond to the same reimport UUID
    # is contradictory provenance and must be rejected.
    with pytest.raises(ValueError, match="contradictory"):
        CorrespondenceMap(
            {
                "VC-AEBS-009D-01": "00000000-0000-4000-8000-000000000001",
                "VC-AEBS-009D-02": "00000000-0000-4000-8000-000000000001",
            }
        )
    with pytest.raises(ValueError, match="duplicate"):
        CorrespondenceMap(
            [
                ("VC-AEBS-009D-01", "00000000-0000-4000-8000-000000000001"),
                ("VC-AEBS-009D-01", "00000000-0000-4000-8000-000000000002"),
            ]
        )


# --------------------------------------------------------------------------
# MC-36: committed-source isolation + dirty-tree refusal
# --------------------------------------------------------------------------

def _commit_all(repo: Path) -> str:
    repo_git = ["git", "-C", str(repo)]
    subprocess.run(repo_git + ["add", "-A"], check=True)
    subprocess.run(
        repo_git + ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "c"],
        check=True,
        capture_output=True,
    )
    return subprocess.check_output(repo_git + ["rev-parse", "HEAD"], text=True).strip()


def _synthetic_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "synthetic-repo"
    repo.mkdir()
    git = ["git", "-C", str(repo)]
    subprocess.run(git + ["init", "-q"], check=True)
    (repo / "textual-notation-of-model").mkdir()
    (repo / "textual-notation-of-model" / "a.sysml").write_text("package P { }\n")
    _commit_all(repo)
    return repo, subprocess.check_output(git + ["rev-parse", "HEAD"], text=True).strip()


def test_mc36_selected_commit_export_excludes_uncommitted_work(tmp_path: Path) -> None:
    from de4sdv.sysml_api.candidate import export_selected_commit

    repo, committed = _synthetic_repo(tmp_path)
    # Uncommitted work in the tree: a NEW file and an EDIT to a tracked file.
    (repo / "textual-notation-of-model" / "b.sysml").write_text("package Q { }\n")
    tracked = repo / "textual-notation-of-model" / "a.sysml"
    original = tracked.read_text()
    tracked.write_text(original + "// dirty edit\n")

    source_docs, identity = export_selected_commit(repo, committed)
    # Export contains ONLY committed content: no b.sysml, no dirty edit.
    assert set(source_docs) == {"textual-notation-of-model/a.sysml"}
    assert "dirty edit" not in "".join(str(x) for x in source_docs.values())
    # The export declares its commit identity.
    assert identity["git_commit"] == committed
    assert identity["tree_was_dirty"] is True


def test_mc36_isolated_checkout_at_exact_commit(tmp_path: Path) -> None:
    from de4sdv.sysml_api.candidate import prepare_isolated_checkout

    repo, committed = _synthetic_repo(tmp_path)
    # An isolated worktree is created at the exact SHA, detached and clean.
    worktree = tmp_path / "isolated"
    prepare_isolated_checkout(repo, committed, worktree)
    head = subprocess.check_output(
        ["git", "-C", str(worktree), "rev-parse", "HEAD"], text=True
    ).strip()
    assert head == committed
    # Uncommitted work in the ORIGIN repo does not appear in the worktree.
    (repo / "textual-notation-of-model" / "b.sysml").write_text("package Q { }\n")
    worktree_files = {
        p.name for p in (worktree / "textual-notation-of-model").iterdir()
    }
    assert worktree_files == {"a.sysml"}


def test_mc36_isolated_checkout_rejects_wrong_sha(tmp_path: Path) -> None:
    from de4sdv.sysml_api.candidate import prepare_isolated_checkout

    repo, committed = _synthetic_repo(tmp_path)
    with pytest.raises(ValueError, match="40-character"):
        prepare_isolated_checkout(repo, "short-sha", tmp_path / "w")
    with pytest.raises(ValueError, match="does not resolve"):
        prepare_isolated_checkout(repo, "f" * 40, tmp_path / "w2")


def test_mc36_dirty_tree_evaluation_request_refused(tmp_path: Path) -> None:
    from de4sdv.sysml_api.candidate import export_selected_commit

    repo, committed = _synthetic_repo(tmp_path)
    (repo / "textual-notation-of-model" / "b.sysml").write_text("package Q { }\n")
    with pytest.raises(RuntimeError, match="dirty working tree"):
        export_selected_commit(repo, committed, allow_dirty=True)


# --------------------------------------------------------------------------
# MC-37: candidate isolation + published baseline preservation
# --------------------------------------------------------------------------

def test_mc37_concurrent_candidates_do_not_overwrite() -> None:
    from de4sdv.sysml_api.candidate import CandidateRegistry

    registry = CandidateRegistry()
    first = registry.register_candidate(
        git_commit="a" * 40, project_id="proj-a", commit_id="ca-1"
    )
    second = registry.register_candidate(
        git_commit="b" * 40, project_id="proj-b", commit_id="cb-1"
    )
    # Distinct identities; neither overwrote the other.
    assert first.sysml_project_id != second.sysml_project_id
    assert registry.get_candidate("a" * 40).sysml_commit_id == "ca-1"
    assert registry.get_candidate("b" * 40).sysml_commit_id == "cb-1"


def test_mc37_candidate_production_preserves_published_baseline() -> None:
    from de4sdv.sysml_api.candidate import CandidateRegistry

    registry = CandidateRegistry()
    registry.set_published_accepted_baseline(
        git_commit="c" * 40, project_id="proj-published", commit_id="cp-1"
    )
    before = registry.published_accepted_baseline()
    registry.register_candidate(
        git_commit="d" * 40, project_id="proj-candidate", commit_id="cd-1"
    )
    # Candidate production must not touch the published pointer.
    assert registry.published_accepted_baseline() == before


def test_mc37_candidate_binding_requires_validation() -> None:
    from de4sdv.sysml_api.candidate import CandidateRegistry

    registry = CandidateRegistry()
    # Binding emission without passing validation is refused (provenance is
    # complete here so the refusal is attributable to validation alone).
    with pytest.raises(RuntimeError, match="validation"):
        registry.emit_binding(
            git_commit="e" * 40,
            project_id="proj-x",
            commit_id="cx-1",
            semantic_validation="failed",
            git_repository="de4sdv/DE4SDV",
            import_timestamp="2026-09-10T00:00:00+00:00",
            import_tool_version="de4sdv-full-model-import/1+official-syside-json",
            ontology_path="approach/framework/ontology/de4sdv-basic-ontology.yaml",
            ontology_sha256="a" * 64,
        )
    binding = registry.emit_binding(
        git_commit="e" * 40,
        project_id="proj-x",
        commit_id="cx-1",
        semantic_validation="passed",
        git_repository="de4sdv/DE4SDV",
        import_timestamp="2026-09-10T00:00:00+00:00",
        import_tool_version="de4sdv-full-model-import/1+official-syside-json",
        ontology_path="approach/framework/ontology/de4sdv-basic-ontology.yaml",
        ontology_sha256="a" * 64,
    )
    assert binding.semantic_validation == "passed"
    assert binding.scope == "candidate"
    # The binding must round-trip through the strict loader (authority tuple
    # complete even for candidate scope).
    loaded = type(binding).from_dict(binding.to_dict())
    assert loaded.ontology.path == binding.ontology.path
    assert loaded.scope == "candidate"


# --------------------------------------------------------------------------
# Binding boundary: status vocabulary + pilot graph read-back
# --------------------------------------------------------------------------

def test_binding_rejects_unknown_status_vocabulary() -> None:
    from de4sdv.semantic.method_contract import bind_pilot_usages

    graph = _pilot_graph()
    # A declared pilot scope referencing an unknown status vocabulary value
    # fails at the binding boundary.
    declared = {
        "scope_usages": [
            "VC-AEBS-009D-01",
            "VC-AEBS-009D-02",
            "VC-AEBS-009D-03",
            "VC-AEBS-009D-04",
            "VC-AEBS-009D-05",
            "VC-AEBS-009D-06",
        ],
        "status_vocabulary": "de4sdv.acceptance.maintainer-decision.v1",
        "status_value": "approved",
    }
    with pytest.raises((ValueError, RuntimeError), match="status"):
        bind_pilot_usages(graph, declared)


def test_binding_resolves_all_six_pilot_usages_with_subjects_and_metadata() -> None:
    from de4sdv.semantic.method_contract import bind_pilot_usages

    graph = _pilot_graph()
    declared = {
        "scope_usages": [
            "VC-AEBS-009D-01",
            "VC-AEBS-009D-02",
            "VC-AEBS-009D-03",
            "VC-AEBS-009D-04",
            "VC-AEBS-009D-05",
            "VC-AEBS-009D-06",
        ],
        "definition_short_name": "VC-AEBS-009D-DE",
    }
    bound = bind_pilot_usages(graph, declared)
    assert len(bound.usages) == 6
    for usage in bound.usages:
        # Each usage resolves by explicit id, has exactly one subject member,
        # and inherits the objective's verify witnesses.
        assert usage.resolution_level == "stable-explicit-id"
        assert len(usage.subject_members) == 1
        assert len(usage.verify_witnesses) == 3
    # Completeness is explicit, not implied by emptiness.
    assert bound.completeness == "complete"
    assert bound.diagnostics == []


def test_binding_reports_incomplete_pagination_or_missing_reference() -> None:
    from de4sdv.semantic.method_contract import bind_pilot_usages

    graph = _pilot_graph()
    # Remove one usage's SubjectMembership: the binding must report the gap,
    # never silently return an empty/complete result.
    graph = [
        element
        for element in graph
        if not (
            element.get("@type") == "SubjectMembership"
            and element["owningRelatedElement"]["@id"]
            == "00000000-0000-4000-8000-000000000002"
        )
    ]
    declared = {
        "scope_usages": [
            "VC-AEBS-009D-01",
            "VC-AEBS-009D-02",
            "VC-AEBS-009D-03",
            "VC-AEBS-009D-04",
            "VC-AEBS-009D-05",
            "VC-AEBS-009D-06",
        ],
    }
    bound = bind_pilot_usages(graph, declared)
    assert bound.completeness == "incomplete"
    assert bound.diagnostics, "a missing required reference must surface as a diagnostic"


def test_binding_missing_usage_is_incomplete_not_empty() -> None:
    from de4sdv.semantic.method_contract import bind_pilot_usages

    # Drop one usage entirely: result is incomplete with diagnostics.
    graph = [
        element
        for element in _pilot_graph()
        if element.get("declaredShortName") != "VC-AEBS-009D-04"
    ]
    declared = {
        "scope_usages": [
            "VC-AEBS-009D-01",
            "VC-AEBS-009D-02",
            "VC-AEBS-009D-03",
            "VC-AEBS-009D-04",
            "VC-AEBS-009D-05",
            "VC-AEBS-009D-06",
        ],
    }
    bound = bind_pilot_usages(graph, declared)
    assert len(bound.usages) == 5
    assert bound.completeness == "incomplete"
    assert any("VC-AEBS-009D-04" in d for d in bound.diagnostics)
