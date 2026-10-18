"""The frozen genuine-export cut: evaluated end to end, and checked against its own records.

``fixtures/genuine_export/inc-aebs-010.json.gz`` is a frozen sample of real
serializer shapes (see the README beside it): a cut of the licensed export of
one revision, kept unchanged. These tests assert outcomes of that frozen cut,
never of the current model. It is evaluated exactly as
``scripts/evaluate_increment.py`` evaluates an export: kernel identity
validated from the export, every serializer shape the real one.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
from pathlib import Path
from types import SimpleNamespace

from de4sdv.semantic import method_evaluator as me
from de4sdv.semantic.export_evaluation import evaluate_export
from de4sdv.semantic.increment_scope import scope_closure
from de4sdv.sysml_api.repository import reference_ids
from increment_model_fixtures import GENUINE_EXPORT

#: The 20 requirements of INC-AEBS-010, all in the needs-and-requirements package the cut keeps in full.
REQUIREMENTS = [
    "reqAaosEnvironmentObservation", "reqAvailabilityDisposition", "reqDe4sdvParticipation",
    "reqDecisionDistanceExclusionStatement", "reqEvidenceCorrelation", "reqFailClosedFreshness",
    "reqInvalidRejection", "reqNativeParticipation", "reqNoDisplayDerivedDecisionMetric",
    "reqNoFreshDataSubstitution", "reqNoHostBrowserSurface", "reqNoNativeImpersonation", "reqNonColorStateCue",
    "reqNonInterference", "reqObstacleGeometryExpiry", "reqObstacleGeometryFromFilteredCloud",
    "reqReadOnlyBoundaryStatement", "reqRealAAOSRendering", "reqRestorationBehavior", "reqSourceFidelity",
]


#: Of the 20, the ones no function and no architecture element carry. The cut holds no verification case,
#: so none of them has one yet (the full export of the same revision covers them by verification only).
UNCARRIED = [
    "reqAaosEnvironmentObservation", "reqDecisionDistanceExclusionStatement", "reqNoDisplayDerivedDecisionMetric",
    "reqNoFreshDataSubstitution", "reqNoHostBrowserSurface", "reqNoNativeImpersonation", "reqNonColorStateCue",
    "reqObstacleGeometryExpiry", "reqObstacleGeometryFromFilteredCloud", "reqReadOnlyBoundaryStatement",
]


def _evaluated(tmp_path: Path):
    export = tmp_path / "export.json"
    export.write_bytes(gzip.decompress(GENUINE_EXPORT.read_bytes()))
    return evaluate_export(export, "INC-AEBS-010")


def test_the_frozen_cut_passes_framing_needs_and_requirements_and_next_asks_for_verification_cases(
        tmp_path: Path) -> None:
    """The cut keeps the framing, needs-and-requirements, functional, logical and
    physical packages in full and the other declared packages as package elements
    only. Its verification cases are therefore outside the cut: phase 10 finds
    none, so next asks for them and no requirement is verified. The full export of
    the same revision answers next none (Method Check run 39149278617); this is the
    cut boundary, not the model."""
    snapshot, evaluation = _evaluated(tmp_path)
    assert snapshot.identity_mode == "export-validated-kernel-bindings"
    phases = {phase["phase"]: phase for phase in evaluation.status()["phases"]}
    assert {name: (phase["conformance_verdict"], len(phase["gates"])) for name, phase in phases.items()
            if phase["gates"]} == {
        "phase0_incrementFraming": (me.VERDICT_PASS, 15),
        "phase4_needs": (me.VERDICT_PASS, 6),
        "phase5_requirements": (me.VERDICT_PASS, 6),
        "phase6_functionalArchitecture": (me.VERDICT_NOT_APPLICABLE, 3),
        "phase7_logicalArchitecture": (me.VERDICT_PASS, 2),
        "phase8_physicalRealization": (me.VERDICT_PASS, 2),
        "phase10_vvEvidence": (me.VERDICT_FAIL, 3),
    }
    assert phases["phase4_needs"]["applicability"] == "declared"  # an optional [0..1] step
    step = evaluation.next_obligation()["next"]
    assert (step["stage"], step["gate"], step["kind"]) == (
        "phase10_vvEvidence", "verificationCaseVerifiesRequirement", "violation")
    assert [subject["reason_codes"] for subject in step["subjects"]] == [[me.POPULATION_POLICY_VIOLATION]]
    # An untyped parameter is named by its keyword (its metaclass is no model element), and the remedy
    # says how one verification case is declared.
    assert step["what_to_author"].startswith(
        "keep at least 1 verification usage in the increment's packages named in the charter's expectedArtifacts")
    assert step["authoring"]["declarations"] == [
        "verification <name> { objective { verify <requirement of the increment>; } }"]
    blocking = {gap["gate"]: gap for gap in evaluation.gaps()["blocking"]}
    assert set(blocking) == {"verificationCaseVerifiesRequirement", "requirementVerifiedByVerificationCase"}
    assert all(gap["phase"] == "phase10_vvEvidence" for gap in blocking.values())
    assert sorted(s["name"] for s in blocking["requirementVerifiedByVerificationCase"]["subjects"]) == REQUIREMENTS


def test_the_frozen_cut_traces_its_allocation_chain_through_chained_ends_and_definition_features(
        tmp_path: Path) -> None:
    """Genuine shapes of phases 6 to 8: the functions and logical roles are features of the flow and
    system definitions (counted at any depth), and the function-to-logical and logical-to-physical
    allocations are written with feature chains (read as their last feature). No requirement is a
    FunctionalRequirementCandidate, so the blocking phase-6 check does not apply; ten of the twenty
    requirements are carried by no architecture element (advisory)."""
    _snapshot, evaluation = _evaluated(tmp_path)
    results = {}
    for result in evaluation.canonical.results:
        if result.subject_id:
            results.setdefault(result.unit_id, {})[result.subject_id] = result.verdict
    assert {gate: (len(found), sum(v == me.VERDICT_PASS for v in found.values()))
            for gate, found in results.items() if gate in (
                "functionAllocatedToLogicalElement", "logicalElementAllocatedToPhysicalElement",
                "physicalElementCarriesLogicalElement", "functionCarriesRequirement",
                "logicalElementCarriesFunction", "requirementCarriedByArchitecture")} == {
        "functionAllocatedToLogicalElement": (8, 8),
        "logicalElementAllocatedToPhysicalElement": (9, 9),
        "physicalElementCarriesLogicalElement": (8, 8),
        "functionCarriesRequirement": (8, 6),
        "logicalElementCarriesFunction": (9, 6),
        "requirementCarriedByArchitecture": (20, 10),
    }
    advisory = {note["gate"]: sorted(s["name"] for s in note["subjects"]) for note in evaluation.gaps()["advisory"]}
    assert advisory["requirementCarriedByArchitecture"] == UNCARRIED
    (note,) = [note for note in evaluation.gaps()["advisory"] if note["gate"] == "requirementCarriedByArchitecture"]
    assert {s["name"]: s["diagnostics"] for s in note["subjects"]} == {
        name: [f"DE4SDV_AEBSVisualizationNeedsRequirements::VisualizationRequirements::{name} is carried by no "
               "architecture element and has no verification case yet"] for name in UNCARRIED}
    assert advisory["functionCarriesRequirement"] == ["publish", "transport"]
    assert advisory["logicalElementCarriesFunction"] == ["coordinatorSource", "displayService", "nativeAebSource"]
    assert "functionalRequirementAllocatedToFunction" not in results


def test_the_scope_closure_counts_no_parameter_and_no_definition_end_of_the_genuine_shapes(tmp_path: Path) -> None:
    """The export owns a definition's parameters and the ends of a connection or allocation definition
    through FeatureMembership, with ``direction`` set or ``isEnd`` true, not through ParameterMembership or
    EndFeatureMembership. The closure reads those native feature fields: no step parameter of the workflow
    and no end of a trace-vocabulary connection definition is an element of a scope naming their packages."""
    _snapshot, evaluation = _evaluated(tmp_path)
    view = evaluation.view
    packages = {view.label(p): p for p in view.index.elements_of_type("Package")}
    scope = SimpleNamespace(scope_packages=(packages["DE4SDV_IncrementWorkflow"], packages["DE4SDV_TraceVocabulary"]))
    closure = set(scope_closure(view, scope))
    labelled = {view.label(e): e for e in view.index.by_id if view.label(e)}
    parameter = labelled["DE4SDV_IncrementWorkflow::DefineFunctionalArchitecture::functions"]
    end = labelled["DE4SDV_TraceVocabulary::DerivesFromNeed::need"]
    owning = {member: str(relationship.get("@type")) for owner in view.index.by_id
              for relationship in view.index.owned_relationships(owner)
              for member in reference_ids(relationship.get("ownedRelatedElement"))}
    assert (owning[parameter], view.index.element(parameter).get("direction")) == ("FeatureMembership", "out")
    assert (owning[end], view.index.element(end).get("isEnd")) == ("FeatureMembership", True)
    assert parameter not in closure and end not in closure
    assert not [view.label(e) for e in closure
                if view.index.element(e).get("direction") or view.index.element(e).get("isEnd") is True]
    assert labelled["DE4SDV_IncrementWorkflow::DefineFunctionalArchitecture"] in closure
    assert labelled["DE4SDV_TraceVocabulary::DerivesFromNeed"] in closure


def _canonical(value) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode()


def _inconsistencies(text: bytes) -> list[str]:
    """How the cut's JSON departs from its own records (empty when self-consistent)."""
    cut = json.loads(text)
    found = [] if _canonical(cut) == text else ["the file is not the cut script's canonical serialization"]
    recorded = cut["cut_from"]["content_sha256"]
    found += [f"{part} differ from their recorded sha256" for part in ("elements", "element_sources")
              if hashlib.sha256(_canonical(cut[part])).hexdigest() != recorded[part]]
    if set(cut["element_sources"]) != {element["@id"] for element in cut["elements"]}:
        found.append("the element sources do not cover exactly the elements")
    files = {path for path in cut["element_sources"].values() if not path.startswith("@library/")}
    manifest = {entry["path"]: entry["sha256"] for entry in cut["source_manifest"]}
    if files != set(manifest) or not all(re.fullmatch(r"[0-9a-f]{64}", sha) for sha in manifest.values()):
        found.append(f"the source manifest does not list the source files: {sorted(files ^ set(manifest))}")
    if not re.fullmatch(r"[0-9a-f]{40}", str(cut.get("git_commit"))):
        found.append("no source revision is recorded")
    return found


def test_the_frozen_cut_is_self_consistent() -> None:
    """The cut matches its own records; it is never compared with the model at HEAD."""
    assert _inconsistencies(gzip.decompress(GENUINE_EXPORT.read_bytes())) == []
