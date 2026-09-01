"""INC-AEBS-010 Phase 10 verification-and-evidence guard tests.

Guards for the visualization V&V slice: model/pilot existence, requirement
coverage, evidence-ladder honesty (fixture path never upgrades to live-chain),
status-only YAML criteria, claim-boundary vocabulary, and parse-gate coverage
of the retained evidence artifacts referenced by the pilot.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

MODEL = Path(
    "textual-notation-of-model/packages/features/aebs/"
    "aebs_010_visualization_verification_evidence.sysml"
)
PILOT = Path(
    "methodologies/sysmod-sysmlv2/pilots/aebs-010-visualization-evidence.yaml"
)
EVIDENCE_INDEX = Path(
    "implementation/aebs-aaos-sdv-visualization-bench/evidence/"
    "010/VIDEO-EVIDENCE-DISPOSITION.md"
)

ALLOWED_CRITERION_KEYS = {"id", "status", "sysml_element", "evidence"}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _model() -> str:
    return _read(MODEL)


def _pilot() -> dict:
    return yaml.safe_load(_read(PILOT))


def test_phase10_artifacts_exist_and_are_indexed() -> None:
    assert MODEL.is_file()
    assert PILOT.is_file()
    pilot = _pilot()
    assert pilot["model_artifacts"]["sysml"] == str(MODEL)
    assert pilot["id"] == "INC-AEBS-010"


def test_id_namespaces_are_collision_free() -> None:
    model = _model()
    for prefix in ("AC-AEBS-S2-", "VC-AEBS-S2-", "E-AEBS-S2-"):
        assert prefix in model, f"{prefix} series must be used by this slice"
    # The System 1 series and the chain needs/requirements series must not be
    # re-allocated by this slice.
    assert "REQ-AEBS-010-" not in _read(PILOT)
    assert "NEED-AEBS-" not in _read(PILOT)


def test_yaml_vc_ids_match_model_verification_usage_anchors() -> None:
    model = _model()
    pilot = _pilot()
    for case in pilot["verification_cases"]:
        assert re.search(
            rf"doc /\* {case['id']} verification case usage\. \*/",
            model,
        ), f"{case['id']} anchor doc missing from the model"


def test_every_acceptance_criterion_is_status_only_in_yaml_and_modeled() -> None:
    pilot = _pilot()
    model = _model()
    for criterion in pilot["acceptance_criteria"]:
        assert set(criterion) == ALLOWED_CRITERION_KEYS, criterion["id"]
        element = criterion["sysml_element"]
        assert re.search(
            rf"requirement\s+{element}\s*:\s*VisualizationAcceptanceCriterionS2\s*\{{",
            model,
        ), f"{element} must be a modeled requirement usage"
        assert f"{criterion['id']};" in model or f"{criterion['id']} " in model, (
            f"{criterion['id']} must be anchored in the model doc"
        )


def test_verification_cases_cover_all_criteria() -> None:
    pilot = _pilot()
    model = _model()
    criteria = {c["id"] for c in pilot["acceptance_criteria"]}
    covered = {c["acceptance_criterion"] for c in pilot["verification_cases"]}
    # AC-AEBS-S2-008 (evidence integrity) is verified inside every case
    # objective in the model rather than by its own YAML case.
    integrity_id = "AC-AEBS-S2-008"
    covered |= {integrity_id}
    assert covered == criteria
    integrity_element = next(
        c["sysml_element"]
        for c in pilot["acceptance_criteria"]
        if c["id"] == integrity_id
    )
    # The model must verify the integrity criterion from at least one objective.
    objectives = re.findall(r"objective \w+ \{(.*?)\n    \}", model, re.S)
    assert any(f"verify {integrity_element};" in o for o in objectives)


def test_fixture_path_evidence_never_claims_live_chain() -> None:
    pilot = _pilot()
    degraded = next(
        c for c in pilot["verification_cases"] if c["id"] == "VC-AEBS-S2-006"
    )
    assert degraded["status"] == "pass_bounded_verification_fixture_path"
    for artifact in degraded["current_evidence"]:
        assert "state-campaign" in artifact
    ladder = {l["layer"]: l["status"] for l in pilot["evidence_ladder"]}
    assert ladder["degraded_state_validation"] == "observed_bounded_fixture_path"


def test_restoration_is_deferred_not_proven() -> None:
    pilot = _pilot()
    restoration = next(
        c for c in pilot["verification_cases"] if c["id"] == "VC-AEBS-S2-007"
    )
    assert restoration["status"] == "deferred_not_proven"
    assert "current_evidence" not in restoration
    deferred = {d["id"] for d in pilot["phase10_claim"]["deferred_items"]}
    assert "AC-AEBS-S2-007" in deferred


def test_scenario_safety_outcome_stays_deferred() -> None:
    model = _model()
    pilot = _pilot()
    assert pilot["phase10_claim"]["scenario_safety_outcome"] == "deferred_not_proven"
    assert "scenarioSafetyDeferredS2" in model
    assert "deferred_not_proven" in model


def test_claim_boundary_forbids_safety_and_certification_reading() -> None:
    model = _model()
    claim_block = re.search(
        r"requirement s2VisualizationInstrumentationClaim : VisualizationClaimS2 \{.*?\n  \}",
        model,
        re.S,
    )
    assert claim_block is not None
    text = claim_block.group(0)
    for excluded in (
        "safety",
        "certification",
        "homologation",
        "production-readiness",
    ):
        assert excluded in text, f"claim boundary must explicitly exclude { excluded }"


def test_read_only_boundary_is_claimed_in_model() -> None:
    model = _model()
    assert "acceptanceCriterionS2ReadOnlyBoundary" in model
    assert "issues no vehicle command" in _read(PILOT).lower() or (
        "no vehicle command" in _read(PILOT)
    )


def test_retained_evidence_artifacts_exist() -> None:
    pilot = _pilot()
    repo = Path(".")
    paths: set[str] = set()

    def collect(node) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "artifact" and isinstance(value, str):
                    paths.add(value)
                elif key == "current_evidence" and isinstance(value, list):
                    paths.update(v for v in value if isinstance(v, str))
                else:
                    collect(value)
        elif isinstance(node, list):
            for item in node:
                collect(item)

    collect(pilot)
    assert paths, "pilot must reference retained evidence artifacts"
    for rel in sorted(paths):
        target = repo / rel
        assert target.is_file() or target.is_dir(), f"missing evidence artifact: {rel}"


def test_evidence_index_classifies_publication_and_forensic_sets() -> None:
    index = _read(EVIDENCE_INDEX)
    assert "final-cut-v2.mp4" in index
    assert "raw-continuous.mp4" in index
    assert "forensic_only" in index
    # The obsolete pre-correction generations must stay classified non-publication.
    for obsolete in (
        "raw-recording-full.mp4",
        "live-v17-pro-ui.mp4",
        "live-v20-final-hmi-continuous.mp4",
    ):
        row = [line for line in index.splitlines() if obsolete in line]
        assert row and "forensic_only" in row[0], obsolete


def test_gap_records_are_modeled_with_owner() -> None:
    model = _model()
    for gap in (
        "gap010RestorationUnexercisedS2",
        "gap010LiveDegradationUnprovenS2",
        "gap010InterVmRouteDeferredS2",
    ):
        assert gap in model
    pilot = _pilot()
    for gap in pilot["runtime_evidence_gaps"]:
        assert gap["owner"] == "successor_increment"


def test_cross_increment_traces_use_accepted_chain_elements() -> None:
    model = _model()
    for target in (
        "to testArticle;",
        "to physicalSystem;",
        "to coordinatorStateProvenance;",
    ):
        assert target in model
    # MW-010 predecessor decision must be referenced, never restated.
    framing = _read(
        Path(
            "textual-notation-of-model/packages/features/aebs/"
            "aebs_010_visualization_framing.sysml"
        )
    )
    assert "successorIncrementDecision010" in framing


def test_views_use_argumentation_assurance_viewpoint() -> None:
    model = _model()
    assert model.count("view aebs010") >= 2
    assert "ArgumentationAssuranceViewpoint" in model
    assert "frame argumentationAssuranceConcernS2" in model
