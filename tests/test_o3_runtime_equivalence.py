"""O3 Stage A — runtime equivalence machinery: sweeps, comparison, K,
grounding proof, support separation.

All fixtures are synthetic (no network, no privileged ingestion). The
comparison contract itself is the accepted #257 schema: any basis or
semantic difference blocks; set ordering canonicalizes; the K pair must
stay one fact / two navigations; VerificationCase grounding is proven by
structure, never by name text alone.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from de4sdv.semantic import o3_bundle as ob
from de4sdv.semantic import o3_equivalence as oe
from de4sdv.sysml_api.revisions import OntologyIdentity

REPO_ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "run_o3_equivalence", REPO_ROOT / "scripts" / "run_o3_equivalence.py"
)
assert _spec is not None and _spec.loader is not None
runner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(runner)

_BINDING_DIGEST = "sha256:" + "b" * 64


def _attested_binding(
    root: Path, revision: str, *, project: str = "pid", commit: str = "cid"
):
    ontology_sha = hashlib.sha256((root / ob.ONTOLOGY_PATH).read_bytes()).hexdigest()
    return SimpleNamespace(
        git_commit=revision,
        semantic_validation="passed",
        sysml_project_id=project,
        sysml_commit_id=commit,
        ontology=OntologyIdentity(ob.ONTOLOGY_PATH, ontology_sha),
        kernel_bindings=(),
        scope="full-model",
    )


def _evidence_records(evidence_dir: Path):
    """Structured validation evidence records bound to REAL produced files."""
    records = {}
    for name in ob.REQUIRED_VALIDATIONS:
        path = evidence_dir / f"{name}.json"
        path.write_text(json.dumps({"result": "passed"}), encoding="utf-8")
        records[name] = {
            "status": "passed",
            "artifact": name,
            "path": str(path),
            "sha256": ob.sha256_file(path),
        }
    return records


def _closed_bundle(*, grounding="EQUIVALENT", export=None):
    revision = "a" * 40
    binding = _attested_binding(REPO_ROOT, revision)
    bundle = ob.build_candidate_bundle(REPO_ROOT, git_revision=revision)
    evidence_dir = Path(tempfile.mkdtemp(prefix="o3-evidence-"))
    attestation = ob.build_closure_attestation(
        bundle,
        binding=binding,
        binding_sha256=_BINDING_DIGEST,
        element_count=1,
        export_identity_sha256=export,
        validations=_evidence_records(evidence_dir),
        verification_case_grounding={"result": grounding},
        generated_at="1970-01-01T00:00:00+00:00",
    )
    return ob.close_bundle(bundle, attestation), binding


class _Mapping:
    def __init__(self, *, domain, range_, strength, strategy="s", configuration=None):
        self.domain = domain
        self.range = range_
        self.semantic_strength = strength
        self.strategy = strategy
        self.configuration = configuration or {}


class _Traversal:
    def __init__(self, hops, blocked=()):
        self._hops = hops
        self._blocked = frozenset(blocked)

    def traverse(self, predicate, source, elements):
        return list(self._hops.get((predicate, source["@id"]), []))

    def blocked_predicates(self):
        return self._blocked


class _Binder:
    def __init__(self, class_ids):
        self._class_ids = class_ids
        self.calls: list[str] = []

    def bind_class(self, name):
        self.calls.append(name)
        if name == "VerificationCase":
            # Mirrors the REAL OntologyApiBinder/KernelContract contract: the
            # file-mapped binder rejects native mappings. Any O3 code path
            # that calls this for VerificationCase must fail, not silently
            # receive a manufactured identity.
            raise ValueError("ontology class VerificationCase is not file-mapped")
        element_id_value, sysml_type = self._class_ids[name]
        return SimpleNamespace(
            sysml=SimpleNamespace(
                element_id=element_id_value, type=sysml_type
            )
        )


class _Contract:
    def __init__(self, mappings, class_mappings=None):
        self._mappings = mappings
        self._class_mappings = class_mappings or {}

    def relationship_mapping(self, name):
        return self._mappings[name]

    def mapping(self, name):
        return self._class_mappings[name]


def _binding(*, commit="a" * 40, project="pid", sysml="cid"):
    return SimpleNamespace(
        git_commit=commit, sysml_project_id=project, sysml_commit_id=sysml,
        scope="full-model",
    )


def _hop(target, witness, strategy="s"):
    return SimpleNamespace(
        target={"@id": target}, api_object={"@id": witness}, strategy=strategy
    )


def _membership_elements():
    return [
        {
            "@id": "m1",
            "@type": "SubjectMembership",
            "memberElement": {"@id": "t-1"},
            "owningRelatedElement": {"@id": "r-1"},
        },
        {"@id": "t-1", "@type": "PartUsage", "declaredName": "part"},
        {"@id": "r-1", "@type": "RequirementUsage", "declaredName": "req"},
    ]


def _subject_service(*, authority, hops, blocked=(), commit="a" * 40, strength="native-reference"):
    mapping = _Mapping(
        domain="Requirement", range_="MemberProduct", strength=strength
    )
    mappings = {"hasSubject": mapping}
    return SimpleNamespace(
        binding=_binding(commit=commit),
        semantic_authority_id=authority,
        traversal=_Traversal(hops, blocked=blocked),
        contract=_Contract(mappings),
    )


def _fake_service(
    *,
    authority,
    hops=None,
    blocked=(),
    commit="a" * 40,
    project="pid",
    sysml="cid",
    strength="native-reference",
    class_ids=None,
    elements=None,
):
    hops = hops if hops is not None else {}
    mapping = _Mapping(domain="Requirement", range_="MemberProduct", strength=strength)
    mappings = {
        "hasSubject": mapping,
        "verifiedBy": mapping,
        "derivesRequirementFromNeed": mapping,
        "derivedRequirementsOfNeed": mapping,
        "hasRelevantArchitecture": mapping,
    }
    class_ids = class_ids or {
        name: (f"uuid-{name}", "EnumerationDefinition")
        for name in runner.CLASS_IDENTITIES
    }
    class_mappings = {
        name: SimpleNamespace(file=f"{name}.sysml", declaration=f"item def {name}")
        for name in runner.CLASS_IDENTITIES
        if name != "VerificationCase"
    }
    class_mappings["VerificationCase"] = SimpleNamespace(
        file=None, declaration=None
    )
    service = SimpleNamespace(
        binding=SimpleNamespace(
            git_commit=commit,
            sysml_project_id=project,
            sysml_commit_id=sysml,
            scope="full-model",
        ),
        semantic_authority_id=authority,
        traversal=_Traversal(hops, blocked=blocked),
        contract=_Contract(mappings, class_mappings),
        binder=_Binder(class_ids),
    )
    service._elements = lambda: (
        elements if elements is not None else _membership_elements()
    )
    return service


def _k_elements():
    return [
        {
            "@id": "c-1",
            "@type": "ConnectionUsage",
            "ownedRelationship": [
                {
                    "memberElement": {"@id": "r-1"},
                    "referencedFeature": {"@id": "n-1"},
                }
            ],
        },
        {"@id": "r-1", "@type": "RequirementUsage", "declaredName": "req"},
        {"@id": "n-1", "@type": "RequirementUsage", "declaredName": "need"},
    ]


class TestSubjectPopulation:
    def test_population_is_witness_derived_and_complete(self) -> None:
        population = runner.subject_population(_membership_elements(), "hasSubject")
        assert population == ["r-1", "t-1"]

    def test_population_is_deterministic(self) -> None:
        first = runner.subject_population(_membership_elements(), "hasSubject")
        second = runner.subject_population(
            list(reversed(_membership_elements())), "hasSubject"
        )
        assert first == second


class TestComparisonBlocks:
    def _compare(self, old_hops, new_hops, **kwargs):
        elements = _membership_elements()
        old = runner.collect_predicate(
            _fake_service(authority="de4sdv.o0-o1-authored-v1", hops=old_hops, **kwargs),
            "hasSubject",
            elements,
        )
        new = runner.collect_predicate(
            _fake_service(authority="o3-candidate:x", hops=new_hops, **kwargs),
            "hasSubject",
            elements,
        )
        return runner.compare_collected(old, new)

    def test_same_hops_compare_equivalent(self) -> None:
        hops = {("hasSubject", "r-1"): [_hop("t-1", "w-1")]}
        report = self._compare(hops, hops)
        assert report["classification"] == "EQUIVALENT"

    def test_revision_difference_blocks(self) -> None:
        hops = {("hasSubject", "r-1"): [_hop("t-1", "w-1")]}
        elements = _membership_elements()
        old = runner.collect_predicate(
            _fake_service(authority="old", hops=hops, commit="a" * 40),
            "hasSubject",
            elements,
        )
        new = runner.collect_predicate(
            _fake_service(authority="new", hops=hops, commit="b" * 40),
            "hasSubject",
            elements,
        )
        report = runner.compare_collected(old, new)
        assert report["classification"] == "BLOCKING_MISMATCH"
        assert any(
            "basis-mismatch:revision" in entry["mismatches"]
            for entry in report["subjects"].values()
        )

    def test_sysml_project_difference_blocks(self) -> None:
        hops = {("hasSubject", "r-1"): [_hop("t-1", "w-1")]}
        elements = _membership_elements()
        old = runner.collect_predicate(
            _fake_service(authority="old", hops=hops, project="pid-1"),
            "hasSubject",
            elements,
        )
        new = runner.collect_predicate(
            _fake_service(authority="new", hops=hops, project="pid-2"),
            "hasSubject",
            elements,
        )
        assert runner.compare_collected(old, new)["classification"] == (
            "BLOCKING_MISMATCH"
        )

    def test_sysml_commit_difference_blocks(self) -> None:
        hops = {("hasSubject", "r-1"): [_hop("t-1", "w-1")]}
        elements = _membership_elements()
        old = runner.collect_predicate(
            _fake_service(authority="old", hops=hops, sysml="cid-1"),
            "hasSubject",
            elements,
        )
        new = runner.collect_predicate(
            _fake_service(authority="new", hops=hops, sysml="cid-2"),
            "hasSubject",
            elements,
        )
        assert runner.compare_collected(old, new)["classification"] == (
            "BLOCKING_MISMATCH"
        )

    def test_subject_population_mismatch_blocks(self) -> None:
        report = runner.compare_collected(
            {"subjects": ["r-1"], "records": {"r-1": {"witnesses": [], "targets": []}}},
            {"subjects": ["r-2"], "records": {"r-2": {"witnesses": [], "targets": []}}},
        )
        assert report["classification"] == "BLOCKING_MISMATCH"
        assert report["mismatches"][0]["mismatches"] == [
            "subject-population-mismatch"
        ]

    def test_target_set_difference_blocks(self) -> None:
        report = self._compare(
            {("hasSubject", "r-1"): [_hop("t-1", "w-1")]},
            {("hasSubject", "r-1"): [_hop("t-2", "w-1")]},
        )
        assert report["classification"] == "BLOCKING_MISMATCH"
        assert any(
            "targets-mismatch" in entry["mismatches"]
            for entry in report["subjects"].values()
            if entry["mismatches"]
        )

    def test_witness_set_difference_blocks(self) -> None:
        report = self._compare(
            {("hasSubject", "r-1"): [_hop("t-1", "w-1")]},
            {("hasSubject", "r-1"): [_hop("t-1", "w-2")]},
        )
        assert report["classification"] == "BLOCKING_MISMATCH"

    def test_semantic_strength_difference_blocks(self) -> None:
        hops = {("hasSubject", "r-1"): [_hop("t-1", "w-1")]}
        elements = _membership_elements()
        old = runner.collect_predicate(
            _fake_service(authority="old", hops=hops, strength="native-reference"),
            "hasSubject",
            elements,
        )
        new = runner.collect_predicate(
            _fake_service(authority="new", hops=hops, strength="relevance"),
            "hasSubject",
            elements,
        )
        report = runner.compare_collected(old, new)
        assert report["classification"] == "BLOCKING_MISMATCH"
        assert any(
            "semantic-strength-mismatch" in entry["mismatches"]
            for entry in report["subjects"].values()
            if entry["mismatches"]
        )

    def test_runtime_support_difference_blocks(self) -> None:
        hops = {("hasSubject", "r-1"): [_hop("t-1", "w-1")]}
        elements = _membership_elements()
        old = runner.collect_predicate(
            _fake_service(authority="old", hops=hops),
            "hasSubject",
            elements,
        )
        new = runner.collect_predicate(
            _fake_service(authority="new", hops=hops, blocked=("hasSubject",)),
            "hasSubject",
            elements,
        )
        report = runner.compare_collected(old, new)
        assert report["classification"] == "BLOCKING_MISMATCH"
        assert any(
            "support-state-mismatch" in entry["mismatches"]
            for entry in report["subjects"].values()
            if entry["mismatches"]
        )

    def test_irrelevant_hop_order_does_not_block(self) -> None:
        report = self._compare(
            {("hasSubject", "r-1"): [_hop("t-1", "w-1"), _hop("t-2", "w-2")]},
            {("hasSubject", "r-1"): [_hop("t-2", "w-2"), _hop("t-1", "w-1")]},
        )
        assert report["classification"] == "EQUIVALENT"


class TestKPairEvidence:
    def _collected(self, service, predicate):
        return runner.collect_predicate(service, predicate, _k_elements())

    def _k_services(self, *, old_witnesses, new_witnesses_forward, new_witnesses_inverse=None):
        new_witnesses_inverse = (
            new_witnesses_inverse
            if new_witnesses_inverse is not None
            else new_witnesses_forward
        )
        elements = _k_elements()

        def hops(witnesses):
            return {
                ("derivesRequirementFromNeed", "r-1"): [
                    _hop(f"t-{i}", w) for i, w in enumerate(witnesses)
                ],
                ("derivedRequirementsOfNeed", "r-1"): [
                    _hop(f"t-{i}", w) for i, w in enumerate(witnesses)
                ],
            }

        old = _fake_service(authority="old", hops=hops(old_witnesses), elements=elements)
        new = _fake_service(authority="new", hops={
            ("derivesRequirementFromNeed", "r-1"): [
                _hop(f"t-{i}", w) for i, w in enumerate(new_witnesses_inverse)
            ],
            ("derivedRequirementsOfNeed", "r-1"): [
                _hop(f"t-{i}", w) for i, w in enumerate(new_witnesses_forward)
            ],
        }, elements=elements)
        old_collected = {
            name: self._collected(old, name) for name in oe.K_PAIR
        }
        new_collected = {
            name: self._collected(new, name) for name in oe.K_PAIR
        }
        return old_collected, new_collected

    def test_shared_witnesses_pass(self) -> None:
        old, new = self._k_services(
            old_witnesses=["w-1", "w-2"], new_witnesses_forward=["w-1", "w-2"]
        )
        evidence = runner.k_pair_evidence(old, new)
        assert evidence["classification"] == "EQUIVALENT"
        assert evidence["drift_from_readiness_baseline"] is True  # 2 != 5

    def test_two_independent_new_facts_block(self) -> None:
        old, new = self._k_services(
            old_witnesses=["w-1"],
            new_witnesses_forward=["w-1"],
            new_witnesses_inverse=["w-9"],
        )
        evidence = runner.k_pair_evidence(old, new)
        assert evidence["classification"] == "BLOCKING_MISMATCH"
        assert any("duplication" in error for error in evidence["errors"])

    def test_witness_population_change_blocks(self) -> None:
        old, new = self._k_services(
            old_witnesses=["w-1"], new_witnesses_forward=["w-1", "w-2"]
        )
        evidence = runner.k_pair_evidence(old, new)
        assert evidence["classification"] == "BLOCKING_MISMATCH"


class TestVerificationCaseGrounding:
    @staticmethod
    def _elements(*, def_implied=True, usage_implied=True, uri=True, def_anchor="VerificationCase", usage_anchor="verificationCases"):
        uri_suffix = "#uuid" if uri else ""
        uri_prefix = "file:///lib/Systems Library/VerificationCases.sysml" if uri else ""
        return [
            {"@id": "def1", "@type": "VerificationCaseDefinition"},
            {"@id": "use1", "@type": "VerificationCaseUsage"},
            {"@id": "anchor-def", "declaredName": def_anchor},
            {"@id": "anchor-use", "declaredName": usage_anchor},
            {
                "@id": "sub1",
                "@type": "Subclassification",
                "isImplied": def_implied,
                "subclassifier": {"@id": "def1"},
                "superclassifier": {
                    "@id": "anchor-def",
                    **({"@uri": uri_prefix + uri_suffix} if uri else {}),
                },
            },
            {
                "@id": "sub2",
                "@type": "Subsetting",
                "isImplied": usage_implied,
                "subsettingFeature": {"@id": "use1"},
                "subsettedFeature": {
                    "@id": "anchor-use",
                    **({"@uri": uri_prefix + uri_suffix} if uri else {}),
                },
            },
        ]

    def test_fully_proven_grounding_is_equivalent(self) -> None:
        result = runner.prove_verification_case_grounding(self._elements())
        assert result["result"] == "EQUIVALENT"
        assert result["governed_population"] == {"definitions": 1, "usages": 1}

    def test_wrong_definition_anchor_name_blocks(self) -> None:
        result = runner.prove_verification_case_grounding(
            self._elements(def_anchor="SomethingElse")
        )
        assert result["result"] == "BLOCKING_MISMATCH"
        assert result["conflicts"]

    def test_wrong_usage_anchor_name_blocks(self) -> None:
        result = runner.prove_verification_case_grounding(
            self._elements(usage_anchor="somethingElse")
        )
        assert result["result"] == "BLOCKING_MISMATCH"

    def test_missing_implied_edge_is_not_yet_comparable(self) -> None:
        result = runner.prove_verification_case_grounding(
            self._elements(def_implied=False)
        )
        assert result["result"] == "NOT_YET_COMPARABLE"

    def test_missing_library_evidence_is_not_yet_comparable(self) -> None:
        """Names alone cannot finish the proof."""
        result = runner.prove_verification_case_grounding(
            self._elements(uri=False)
        )
        assert result["result"] == "NOT_YET_COMPARABLE"

    def test_source_document_evidence_also_proves(self) -> None:
        result = runner.prove_verification_case_grounding(
            self._elements(uri=False),
            element_sources={
                "anchor-def": "Systems Library/VerificationCases.sysml",
                "anchor-use": "Systems Library/VerificationCases.sysml",
            },
        )
        assert result["result"] == "EQUIVALENT"

    def test_wrong_role_mechanism_blocks(self) -> None:
        elements = self._elements()
        # Convert the usage-role proof edge into a Subclassification: the
        # usage role requires implied Subsetting, so the proof cannot hold.
        for element in elements:
            if element.get("@id") == "sub2":
                element["@type"] = "Subclassification"
        result = runner.prove_verification_case_grounding(elements)
        assert result["result"] != "EQUIVALENT"

    def test_conflicting_anchor_identities_block(self) -> None:
        elements = self._elements()
        elements.append(
            {
                "@id": "sub1b",
                "@type": "Subclassification",
                "isImplied": True,
                "subclassifier": {"@id": "def1"},
                "superclassifier": {
                    "@id": "anchor-def-2",
                    "@uri": "file:///lib/Systems Library/VerificationCases.sysml#x",
                },
            }
        )
        elements.append({"@id": "anchor-def-2", "declaredName": "VerificationCase"})
        result = runner.prove_verification_case_grounding(elements)
        assert result["result"] == "BLOCKING_MISMATCH"
        assert any("multiple distinct anchor" in conflict for conflict in result["conflicts"])

    def test_empty_governed_population_is_not_yet_comparable(self) -> None:
        result = runner.prove_verification_case_grounding([])
        assert result["result"] == "NOT_YET_COMPARABLE"


class TestSupportSeparation:
    def test_artifact_and_runtime_dimensions_are_separate(self) -> None:
        elements = _membership_elements()
        hops = {("hasSubject", "r-1"): [_hop("t-1", "w-1")]}
        old = {
            predicate: runner.collect_predicate(
                _fake_service(authority="old", hops=hops), predicate, elements
            )
            for predicate in runner.RELATIONSHIP_PREDICATES
        }
        new = {
            predicate: runner.collect_predicate(
                _fake_service(
                    authority="new",
                    hops=hops,
                    blocked=("hasSubject",) if predicate == "hasSubject" else (),
                ),
                predicate,
                elements,
            )
            for predicate in runner.RELATIONSHIP_PREDICATES
        }
        projection_documents = [
            {
                "concepts": [
                    {"identity": name, "support_state": "vocabulary-only"}
                    for name in runner.CLASS_IDENTITIES
                ],
                "predicates": [
                    {"identity": name, "support_state": "vocabulary-only"}
                    for name in runner.RELATIONSHIP_PREDICATES
                ],
            }
        ]
        evidence = runner.support_preservation_evidence(
            old, new, projection_documents
        )
        # Publication never promotes support ...
        assert evidence["artifact_support_preservation"]["classification"] == (
            "EQUIVALENT"
        )
        # ... while the runtime behavior dimension independently blocks.
        assert evidence["runtime_behavior"]["classification"] == (
            "BLOCKING_MISMATCH"
        )
        assert evidence["runtime_behavior"]["predicates"]["hasSubject"][
            "old_states"
        ] == ["runtime-queryable"]
        assert evidence["runtime_behavior"]["predicates"]["hasSubject"][
            "new_states"
        ] == ["runtime-blocked"]

    def test_artifact_promotion_would_block(self) -> None:
        elements = _membership_elements()
        hops = {("hasSubject", "r-1"): [_hop("t-1", "w-1")]}
        old = {
            predicate: runner.collect_predicate(
                _fake_service(authority="old", hops=hops), predicate, elements
            )
            for predicate in runner.RELATIONSHIP_PREDICATES
        }
        new = {
            predicate: runner.collect_predicate(
                _fake_service(authority="new", hops=hops), predicate, elements
            )
            for predicate in runner.RELATIONSHIP_PREDICATES
        }
        projection_documents = [
            {
                "predicates": [
                    {"identity": name, "support_state": "supported"}
                    for name in runner.RELATIONSHIP_PREDICATES
                ]
            }
        ]
        evidence = runner.support_preservation_evidence(
            old, new, projection_documents
        )
        assert evidence["artifact_support_preservation"]["classification"] == (
            "BLOCKING_MISMATCH"
        )


class TestClassIdentityComparison:
    """BLOCKER A: seven file-mapped classes go through the file-mapped
    binder; VerificationCase consumes the grounding proof and NEVER touches
    the file binder (the fake binder raises if it is ever called)."""

    def _services(self):
        return (
            _fake_service(authority="de4sdv.o0-o1-authored-v1"),
            _fake_service(authority="o3-candidate:o3b-test"),
        )

    def test_seven_file_classes_compare_and_vc_never_uses_the_binder(self):
        old, new = self._services()
        result = runner.compare_class_identities(
            old, new, verification_case_grounding={"result": "EQUIVALENT"}
        )
        assert result["classification"] == "EQUIVALENT"
        assert result["identities"]["VerificationCase"]["classification"] == "EQUIVALENT"
        assert "VerificationCase" not in old.binder.calls
        assert "VerificationCase" not in new.binder.calls
        assert sorted(old.binder.calls) == sorted(runner.FILE_MAPPED_CLASSES)

    def test_vc_grounding_classification_passthrough(self):
        old, new = self._services()
        for grounding, expected in (
            ("NOT_YET_COMPARABLE", "NOT_YET_COMPARABLE"),
            ("BLOCKING_MISMATCH", "BLOCKING_MISMATCH"),
            ("EQUIVALENT", "EQUIVALENT"),
        ):
            result = runner.compare_class_identities(
                old, new, verification_case_grounding={"result": grounding}
            )
            assert result["identities"]["VerificationCase"]["classification"] == expected

    def test_absent_or_unknown_grounding_is_not_yet_comparable(self):
        old, new = self._services()
        result = runner.compare_class_identities(
            old, new, verification_case_grounding=None
        )
        assert (
            result["identities"]["VerificationCase"]["classification"]
            == "NOT_YET_COMPARABLE"
        )
        assert result["classification"] == "NOT_YET_COMPARABLE"

    def test_file_class_mismatch_is_never_downgraded_by_vc(self):
        old = _fake_service(authority="old")
        class_ids = dict(old.binder._class_ids)
        class_ids["MethodPhase"] = ("uuid-other", "EnumerationDefinition")
        new = _fake_service(authority="new", class_ids=class_ids)
        result = runner.compare_class_identities(
            old, new, verification_case_grounding={"result": "NOT_YET_COMPARABLE"}
        )
        assert result["classification"] == "BLOCKING_MISMATCH"

    def test_real_file_binder_rejects_verification_case(self):
        from de4sdv.semantic.api_binding import OntologyApiBinder
        from de4sdv.semantic.kernel_contract import KernelContract

        contract = KernelContract.load(REPO_ROOT / ob.ONTOLOGY_PATH)
        binder = OntologyApiBinder(
            contract,
            SimpleNamespace(),
            project_id="pid",
            commit_id="cid",
            kernel_bindings=None,
        )
        with pytest.raises(ValueError, match="not file-mapped"):
            binder.bind_class("VerificationCase")

    def test_scope_partition_is_exact(self):
        assert "VerificationCase" in runner.CLASS_IDENTITIES
        assert "VerificationCase" not in runner.FILE_MAPPED_CLASSES
        assert len(runner.FILE_MAPPED_CLASSES) == 7


class TestSingleClosureIdentity:
    """BLOCKER C/D: exactly ONE import/export closure identity across
    bundle, report and manifests; unresolved comparisons exit non-zero."""

    def test_resolves_the_bundle_attested_closure(self):
        closed, binding = _closed_bundle()
        digest = runner.resolve_attested_closure(
            closed,
            binding=binding,
            binding_sha256=_BINDING_DIGEST,
            element_count=1,
        )
        assert digest == closed["api_closure"]["import_closure_digest"]

    def test_element_count_mismatch_blocks(self):
        closed, binding = _closed_bundle()
        with pytest.raises(ob.O3BundleError, match="element count"):
            runner.resolve_attested_closure(
                closed,
                binding=binding,
                binding_sha256=_BINDING_DIGEST,
                element_count=2,
            )

    def test_binding_digest_mismatch_blocks(self):
        closed, binding = _closed_bundle()
        with pytest.raises(ob.O3BundleError, match="binding digest"):
            runner.resolve_attested_closure(
                closed,
                binding=binding,
                binding_sha256="sha256:" + "9" * 64,
                element_count=1,
            )

    def test_tampered_closure_digest_blocks(self):
        closed, binding = _closed_bundle()
        closed["api_closure"]["import_closure_digest"] = "sha256:" + "d" * 64
        with pytest.raises(ob.O3BundleError, match="failed verification"):
            runner.resolve_attested_closure(
                closed,
                binding=binding,
                binding_sha256=_BINDING_DIGEST,
                element_count=1,
            )

    def test_different_export_identity_changes_and_protects_the_closure(self):
        first, _ = _closed_bundle(export="sha256:" + "1" * 64)
        second, _ = _closed_bundle(export="sha256:" + "2" * 64)
        assert (
            first["api_closure"]["import_closure_digest"]
            != second["api_closure"]["import_closure_digest"]
        )
        first["api_closure"]["export_identity_sha256"] = "sha256:" + "2" * 64
        with pytest.raises(ob.O3BundleError, match="failed verification"):
            runner.resolve_attested_closure(
                first,
                binding=_attested_binding(REPO_ROOT, "a" * 40),
                binding_sha256=_BINDING_DIGEST,
                element_count=1,
            )

    def test_report_requires_the_single_attested_closure(self):
        closed, binding = _closed_bundle()
        old = _fake_service(authority="de4sdv.o0-o1-authored-v1")
        new = _fake_service(authority="o3-candidate:o3b-test")
        with pytest.raises(ob.O3BundleError, match="ONE closure identity"):
            runner.build_runtime_equivalence_report(
                old,
                new,
                root=REPO_ROOT,
                bundle=closed,
                binding=binding,
                binding_sha256=_BINDING_DIGEST,
                import_closure_digest="sha256:" + "e" * 64,
                git_revision="a" * 40,
                verification_case_grounding={"result": "EQUIVALENT"},
                generated_at="t",
            )

    def _full_report(self, *, grounding):
        closed, binding = _closed_bundle()
        digest = closed["api_closure"]["import_closure_digest"]
        old = _fake_service(authority="de4sdv.o0-o1-authored-v1")
        new = _fake_service(authority="o3-candidate:o3b-test")
        return runner.build_runtime_equivalence_report(
            old,
            new,
            root=REPO_ROOT,
            bundle=closed,
            binding=binding,
            binding_sha256=_BINDING_DIGEST,
            import_closure_digest=digest,
            git_revision="a" * 40,
            verification_case_grounding={"result": grounding},
            generated_at="t",
        )

    def test_one_closure_digest_everywhere_and_equivalent_is_green(self):
        report = self._full_report(grounding="EQUIVALENT")
        assert report["overall"] == "EQUIVALENT"
        assert report["import_closure_digest"] == report["manifests"]["old"][
            "import_closure_digest"
        ]
        assert report["import_closure_digest"] == report["manifests"]["new"][
            "import_closure_digest"
        ]
        assert runner.compare_exit_code(report) == 0

    def test_not_yet_comparable_report_exits_non_zero(self):
        report = self._full_report(grounding="NOT_YET_COMPARABLE")
        assert report["overall"] == "NOT_YET_COMPARABLE"
        assert runner.compare_exit_code(report) != 0

    def test_blocking_report_exits_non_zero(self):
        report = self._full_report(grounding="BLOCKING_MISMATCH")
        assert report["overall"] == "BLOCKING_MISMATCH"
        assert runner.compare_exit_code(report) != 0


class TestExitRules:
    def test_compare_exit_codes(self):
        assert runner.compare_exit_code({"overall": "EQUIVALENT"}) == 0
        for classification in (
            "BLOCKING_MISMATCH",
            "NOT_YET_COMPARABLE",
            "INTENTIONAL_MIGRATION_REVIEW_REQUIRED",
            "UNSUPPORTED_BOTH",
            "unknown",
        ):
            assert runner.compare_exit_code({"overall": classification}) != 0

    def test_bundle_exit_codes(self):
        assert (
            runner.bundle_exit_code(
                closure_errors=[], grounding_result="EQUIVALENT"
            )
            == 0
        )
        # comparison-capable: NOT_YET_COMPARABLE may close for the compare
        # step (activation_eligible stays false); compare owns final success
        assert (
            runner.bundle_exit_code(
                closure_errors=[], grounding_result="NOT_YET_COMPARABLE"
            )
            == 0
        )
        assert (
            runner.bundle_exit_code(
                closure_errors=[], grounding_result="BLOCKING_MISMATCH"
            )
            != 0
        )
        assert (
            runner.bundle_exit_code(
                closure_errors=["closure mismatch"], grounding_result="EQUIVALENT"
            )
            != 0
        )


class TestValidationEvidenceRecords:
    def _args(self, *, status="passed", artifacts=True, tmp_path):
        validation = []
        validation_artifact = []
        for name in ob.REQUIRED_VALIDATIONS:
            validation.append(f"{name}={status}")
            if artifacts:
                path = tmp_path / f"{name}.json"
                path.write_text(json.dumps({"result": status}), encoding="utf-8")
                validation_artifact.append(f"{name}={path}")
        return argparse.Namespace(
            validation=validation, validation_artifact=validation_artifact
        )

    def test_records_bind_status_artifact_and_digest(self, tmp_path) -> None:
        records = runner.bundle_validation_records(self._args(tmp_path=tmp_path))
        for name in ob.REQUIRED_VALIDATIONS:
            record = records[name]
            assert record["status"] == "passed"
            assert record["artifact"] == name
            assert record["sha256"] == ob.sha256_file(
                tmp_path / f"{name}.json"
            )

    def test_failed_status_is_refused(self, tmp_path) -> None:
        with pytest.raises(SystemExit):
            runner.bundle_validation_records(
                self._args(status="failed", tmp_path=tmp_path)
            )

    def test_missing_artifact_binding_is_refused(self, tmp_path) -> None:
        with pytest.raises(SystemExit):
            runner.bundle_validation_records(
                self._args(artifacts=False, tmp_path=tmp_path)
            )

    def test_missing_artifact_file_is_refused(self, tmp_path) -> None:
        args = self._args(tmp_path=tmp_path)
        for name in ob.REQUIRED_VALIDATIONS:
            (tmp_path / f"{name}.json").unlink()
        with pytest.raises(SystemExit):
            runner.bundle_validation_records(args)
