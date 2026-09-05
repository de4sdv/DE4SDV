"""INC-AEBS-010 Phase 10 verification-and-evidence guard tests.

Guards for the visualization V&V slice: model/pilot existence, requirement
coverage, evidence-ladder honesty (fixture path never upgrades to live-chain),
status-only YAML criteria, claim-boundary vocabulary, canonical naming, and
parse-gate coverage of the retained evidence artifacts referenced by the pilot.

Canonical identities (naming-conventions.md / migration-manifest.md M11):
model file `aebs_visualization_verification_evidence.sysml`, package
`DE4SDV_AEBSVisualizationVerificationEvidence`, evidence IDs
`EVID-AEBS-S2-001..007`, views `aebsVisualization*AssuranceView`.
`INC-AEBS-010`, `AEBS-CONFIG-010-001`, AC/VC/REQ/GAP identities stay
lifecycle-owned and unchanged.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

MODEL_DIR = Path("textual-notation-of-model/packages/features/aebs")
MODEL = MODEL_DIR / "aebs_visualization_verification_evidence.sysml"
FRAMING = MODEL_DIR / "aebs_visualization_framing.sysml"
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


def test_canonical_model_identity_is_used() -> None:
    model = _model()
    assert "package DE4SDV_AEBSVisualizationVerificationEvidence {" in model
    assert "DE4SDV_AEBS010VisualizationVerificationEvidence" not in model
    # The pseudo phase-increment must not exist; the framing increment
    # `incAEBS010` is the only INC-AEBS-010 increment identity.
    assert "incAEBS010VerificationEvidence" not in model


def test_no_old_package_imports_remain() -> None:
    model = _model()
    for old_import in (
        "DE4SDV_AEBS010VisualizationFraming",
        "DE4SDV_AEBS010VisualizationNeedsRequirements",
        "DE4SDV_AEBS010VisualizationPhysicalRealization",
        "DE4SDV_AEBS010VisualizationVariabilityConfiguration",
    ):
        assert old_import not in model, f"stale import: {old_import}"
    for canonical_import in (
        "DE4SDV_AEBSVisualizationFraming",
        "DE4SDV_AEBSVisualizationNeedsRequirements",
        "DE4SDV_AEBSVisualizationPhysicalSoftwareRealization",
        "DE4SDV_AEBSVisualizationVariabilityConfiguration",
    ):
        assert canonical_import in model, f"missing import: {canonical_import}"


def test_view_identities_are_canonical_not_lifecycle_numbered() -> None:
    model = _model()
    assert "view aebsVisualizationVerificationAssuranceView {" in model
    assert "view aebsVisualizationOpenCounterclaimAssuranceView {" in model
    assert "view aebs010" not in model


def test_evidence_ids_use_canonical_evid_grammar() -> None:
    model = _model()
    pilot_text = _read(PILOT)
    index = _read(EVIDENCE_INDEX)
    expected = {f"EVID-AEBS-S2-{number:03d}" for number in range(1, 8)}
    for evidence_id in expected:
        assert evidence_id in model, f"{evidence_id} missing from model"
        assert evidence_id in pilot_text, f"{evidence_id} missing from pilot"
    # The retired E- grammar is middleware-only (closed grandfathered set);
    # this slice must not reintroduce it.
    assert "E-AEBS-S2-" not in model
    assert "E-AEBS-S2-" not in pilot_text


def test_evid_ids_are_collision_free_across_slices() -> None:
    """EVID-AEBS-S2-* identities must each be allocated in exactly one model
    file (prose mentions inside the allocating file are fine)."""
    aebs_dir = MODEL_DIR
    holders: dict[str, set[str]] = {}
    for path in sorted(aebs_dir.glob("*.sysml")):
        for evidence_id in re.findall(r"EVID-AEBS-S2-[0-9]{3}", _read(path)):
            holders.setdefault(evidence_id, set()).add(path.name)
    collisions = {k: v for k, v in holders.items() if len(v) > 1}
    assert not collisions, collisions
    assert {f"EVID-AEBS-S2-{n:03d}" for n in range(1, 8)} <= set(holders)


def test_id_namespaces_are_collision_free() -> None:
    model = _model()
    for prefix in ("AC-AEBS-S2-", "VC-AEBS-S2-", "EVID-AEBS-S2-"):
        assert prefix in model, f"{prefix} series must be used by this slice"
    # The System 1 series and the chain needs/requirements series must not be
    # re-allocated by this slice.
    assert "REQ-AEBS-010-" not in _read(PILOT)
    # New-style need IDs are not allocated by this slice (needs live in the
    # framing/needs slices and the N-AEBS-* legacy series).
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


def test_partial_outcome_maps_to_inconclusive_not_pass() -> None:
    """A partial result can never upgrade into a pass verdict (plan Task 6)."""
    model = _model()
    mapping = re.search(
        r"calc def MapS2OutcomeToVerdict \{(.*?)\n  \}",
        model,
        re.S,
    )
    assert mapping, "MapS2OutcomeToVerdict must remain defined"
    body = mapping.group(1)
    assert "VisualizationEvidenceDisposition::observedBounded? VerdictKind::pass" in body
    # partial must not map to pass: it stays inconclusive unless a later,
    # explicitly justified bounded-pass interpretation is added with its own
    # negative guard removed.
    assert "VisualizationEvidenceDisposition::partial? VerdictKind::pass" not in body


def test_missing_evidence_cannot_map_to_pass() -> None:
    """blocked/planned/notClaimed dispositions must stay non-pass."""
    model = _model()
    mapping = re.search(
        r"calc def MapS2OutcomeToVerdict \{(.*?)\n  \}",
        model,
        re.S,
    )
    assert mapping
    body = mapping.group(1)
    pass_lines = [
        line for line in body.splitlines() if re.search(r"VerdictKind::pass\b", line)
    ]
    assert pass_lines, "mapping must retain the observedBounded pass branch"
    offenders = [l for l in pass_lines if "observedBounded" not in l]
    assert not offenders, (
        f"pass verdict reachable from non-observedBounded outcomes: {offenders}"
    )


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


def test_retained_evidence_artifacts_exist_or_are_external_identity() -> None:
    """Every evidence reference resolves to an in-tree artifact or is
    explicitly declared in the external-media manifest (never a pretend
    in-tree file)."""
    pilot = _pilot()
    repo = Path(".")
    media_manifest = yaml.safe_load(
        _read(
            Path(
                "implementation/aebs-aaos-sdv-visualization-bench/evidence/"
                "010/external-media.yaml"
            )
        )
    )
    external_former_paths = {
        a["former_path"]
        for a in media_manifest["artifacts"]
    }
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
        if target.is_file() or target.is_dir():
            continue
        # Missing in-tree: must be an explicit external-media entry whose
        # former_path matches the referenced file's tail path.
        tail = "/".join(rel.split("/")[-3:])
        assert tail in external_former_paths or rel in external_former_paths, (
            f"evidence artifact neither in-tree nor in external-media.yaml: {rel}"
        )


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
    framing = _read(FRAMING)
    assert "successorIncrementDecision010" in framing


def test_views_use_argumentation_assurance_viewpoint() -> None:
    model = _model()
    assert model.count("view aebsVisualization") >= 2
    assert "ArgumentationAssuranceViewpoint" in model
    assert "frame argumentationAssuranceConcernS2" in model


def test_slice_adds_no_product_feature_or_member() -> None:
    """Phase 10 is System 2 evidence only: no BoF, no product feature, no
    duplicated planned member, no runtime-maturity claim from Gate C."""
    model = _model()
    # The only member specialization is the canonical test article type,
    # owned by the variability-configuration slice - not re-declared here.
    assert "part def AEBSAutowareAAOSSDVVisualizationTestArticle" not in model
    # No new Bill-of-Features authority is created by this slice.
    part_defs = re.findall(r"part def (\w+)", model)
    assert all("Feature" not in name for name in part_defs), part_defs


def test_bench_subject_distinction_is_explicit() -> None:
    """System 1 subject is the uninstrumented configured member; the
    instrumented test article belongs to the System 2 side."""
    model = _model()
    bench = re.search(
        r"part def VisualizationVandVBenchS2 \{(.*?)\n  \}",
        model,
        re.S,
    )
    assert bench, "bench definition missing"
    body = bench.group(1)
    assert "System 1" in body and "System 2" in body, (
        "bench must label its System 1 / System 2 subjects"
    )
    # The misleading typing (System 1 member typed as the instrumented test
    # article) must not survive.
    assert (
        "part system1MemberProduct : AEBSAutowareAAOSSDVVisualizationTestArticle"
        not in body
    )


def test_known_limitations_record_geometry_and_repeatability_gaps() -> None:
    """v21 observations must not transfer to corrected geometry or
    deterministic warning timing (re-adjudication, plan Task 6)."""
    pilot = _pilot()
    limitations = {entry["id"] for entry in pilot.get("known_limitations", [])}
    assert {"DEF-AEBS-S2-001", "DEF-AEBS-S2-002", "DEF-AEBS-S2-003"} <= limitations
    text = str(pilot["known_limitations"])
    assert "geometry" in text
    assert "repeatability" in text or "warning-lead" in text


def test_v21_evidence_binds_source_identity_beyond_head_at_capture() -> None:
    """uncommitted_correction: true requires the deployed-source checksum
    provenance (revision-checksums.md) to be retained next to the segment."""
    segment = yaml.safe_load(
        _read(
            Path(
                "implementation/aebs-aaos-sdv-visualization-bench/evidence/"
                "010/forward-ui/final-hmi-v21-corrected/segment.yaml"
            )
        )
    )
    assert segment.get("uncommitted_correction") is True
    checksums = _read(
        Path(
            "implementation/aebs-aaos-sdv-visualization-bench/evidence/"
            "010/forward-ui/final-hmi-v21-corrected/revision-checksums.md"
        )
    )
    assert segment["head_at_capture"] in checksums
    assert "sha256 prefixes of the deployed corrected sources" in checksums


def test_partial_status_never_appears_as_campaign_pass() -> None:
    """No criterion in the pilot carries a partial-into-pass upgrade."""
    pilot = _pilot()
    for criterion in pilot["acceptance_criteria"]:
        assert criterion["status"] != "pass", criterion["id"]
        assert "pass_partial" not in criterion["status"], criterion["id"]
