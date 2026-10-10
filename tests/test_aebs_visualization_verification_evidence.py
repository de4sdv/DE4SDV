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

REQUIRED_SUCCESS_CRITERIA_KEYS = {"requirement", "case", "status", "evidence"}
# formerly: only for criteria that had an AC ID on main (AC-AEBS-S2-001..007).
OPTIONAL_SUCCESS_CRITERIA_KEYS = {"formerly"}
NEEDS = MODEL_DIR / "aebs_visualization_needs_requirements.sysml"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _model() -> str:
    return _read(MODEL)


def _pilot() -> dict:
    return yaml.safe_load(_read(PILOT))


def _requirement_blocks() -> dict[str, tuple[str, str]]:
    """REQ ID -> (usage name, declaration block) for each S2 requirement."""
    blocks = {}
    for match in re.finditer(
        r"    requirement (req\w+) : VisualizationInstrumentRequirementCandidate \{.*?\n    \}",
        _read(NEEDS),
        re.S,
    ):
        req_id = re.search(r"doc /\* (REQ-AEBS-S2-\d{3})", match.group(0)).group(1)
        blocks[req_id] = (match.group(1), match.group(0))
    return blocks


def _success_criteria(block: str) -> str | None:
    found = re.search(r'attribute :>> successCriteria = "([^"]*)";', block)
    return found.group(1) if found else None


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


def test_every_success_criteria_row_is_status_only_and_modeled() -> None:
    """Owner decision 2026-10-10: success criteria are the requirement's own
    successCriteria attribute. The index keeps status and evidence only, per
    requirement, and names the retired criterion ID it replaced."""
    pilot = _pilot()
    model = _model()
    blocks = _requirement_blocks()
    assert "acceptance_criteria" not in pilot
    for row in pilot["requirement_success_criteria"]:
        assert REQUIRED_SUCCESS_CRITERIA_KEYS <= set(row) <= (
            REQUIRED_SUCCESS_CRITERIA_KEYS | OPTIONAL_SUCCESS_CRITERIA_KEYS
        ), row["requirement"]
        usage, block = blocks[row["requirement"]]
        criteria = _success_criteria(block)
        assert criteria and criteria.startswith("Met when"), row["requirement"]
        assert "shall" not in criteria, row["requirement"]
        if "formerly" in row:
            assert row["formerly"] in {f"AC-AEBS-S2-{n:03d}" for n in range(1, 8)}, row["requirement"]
            assert f"success criteria formerly {row['formerly']}" in block, row["requirement"]
        else:
            assert "success criteria formerly" not in block, row["requirement"]
        case_usage = re.search(
            rf"doc /\* {row['case']} verification case usage\. \*/\s*verification (\w+) : (\w+)", model
        )
        assert case_usage, row["case"]
        definition = re.search(rf"verification def {case_usage.group(2)} \{{.*?\n  \}}", model, re.S)
        assert definition and f"verify {usage} {{" in definition.group(0), (row["case"], usage)


def test_success_criteria_index_matches_the_model_and_retires_the_criteria() -> None:
    """Every requirement that states successCriteria is indexed once, the
    acceptance-criterion elements and their verify links are gone, and the
    evidence-integrity obligation lives on the shared evidence record."""
    pilot = _pilot()
    model = _model()
    stated = {req for req, (_usage, block) in _requirement_blocks().items() if _success_criteria(block)}
    rows = [row["requirement"] for row in pilot["requirement_success_criteria"]]
    assert len(rows) == len(set(rows)) and set(rows) == stated
    formerly = [row["formerly"] for row in pilot["requirement_success_criteria"] if "formerly" in row]
    assert len(formerly) == len(set(formerly)) == 7
    code = _strip_sysml_comments(model)
    assert "AcceptanceCriterion" not in code
    assert not re.search(r"\bverify\s+acceptanceCriterion", code)
    for case in pilot["verification_cases"]:
        assert "acceptance_criterion" not in case and "planned_acceptance_criteria" not in case
    record = re.search(r"item def RetainedVisualizationEvidence \{.*?\n  \}", model, re.S)
    assert record
    text = " ".join(re.sub(r"\n\s*\*(?!/)", "\n", record.group(0)).split())
    assert "formerly AC-AEBS-S2-008" in text
    assert "never as an observed runtime pass" in text
    obligation = pilot["evidence_integrity_obligation"]
    assert obligation["formerly"] == "AC-AEBS-S2-008"
    assert obligation["sysml_element"] == "RetainedVisualizationEvidence"


EXPECTED_VERDICT_MAPPING = (
    "if outcome == VisualizationEvidenceDisposition::observedBounded"
    "? VerdictKind::pass\n"
    "      else if outcome == VisualizationEvidenceDisposition::partial"
    "? VerdictKind::inconclusive\n"
    "      else if outcome == VisualizationEvidenceDisposition::blocked"
    "? VerdictKind::inconclusive\n"
    "      else if outcome == VisualizationEvidenceDisposition::notClaimed"
    "? VerdictKind::inconclusive\n"
    "      else VerdictKind::inconclusive;"
)


def test_verdict_mapping_is_exactly_the_reviewed_semantics() -> None:
    """Pin the full verdict mapping, not just the pass direction.

    Direction-only guards let a partial outcome be re-mapped to a definitive
    verdict (e.g. fail) that the retained evidence cannot support either: a
    partial observation supports neither pass nor fail, only inconclusive.
    The exact mapping is therefore pinned verbatim; any semantics change must
    consciously rewrite this guard.
    """
    model = _model()
    mapping = re.search(
        r"calc def MapVisualizationOutcomeToVerdict \{(.*?)\n  \}",
        model,
        re.S,
    )
    assert mapping, "MapVisualizationOutcomeToVerdict must remain defined"
    body = mapping.group(1)
    assert EXPECTED_VERDICT_MAPPING.strip() in body, (
        "MapVisualizationOutcomeToVerdict must map only observedBounded to pass and "
        "everything else (incl. partial) to inconclusive; "
        f"got: {body.strip()}"
    )


def test_missing_evidence_cannot_map_to_pass() -> None:
    """blocked/planned/notClaimed dispositions must stay non-pass."""
    model = _model()
    mapping = re.search(
        r"calc def MapVisualizationOutcomeToVerdict \{(.*?)\n  \}",
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
    assert degraded["status"] == "observed_unidentified_build_fixture_path"
    for artifact in degraded["current_evidence"]:
        assert "state-campaign" in artifact
    ladder = {l["layer"]: l["status"] for l in pilot["evidence_ladder"]}
    assert ladder["degraded_state_validation"] == "observed_unidentified_build_fixture_path"


def test_bench_binds_the_subject_to_the_configured_article_instrument() -> None:
    """Option C (owner decision 2026-10-09): the configuration role and the
    subject role are separate; the subject is the visualization test system
    as realized in AEBS-CONFIG-010-001, linked by typing, never allocation."""
    model = _model()
    bench = re.search(r"part def VisualizationVerificationBench \{(.*?)\n  \}", model, re.S)
    assert bench
    assert "part system2TestArticle :> testArticle;" in bench.group(1)
    assert (
        "ref part system2Instrument :> system2VisualizationInstrument = "
        "system2TestArticle.visualizationChain.instrument;"
    ) in bench.group(1)
    assert not re.search(r"\ballocate\b", _strip_sysml_comments(model))


RETAINED_RECORDS = (
    "liveChainEvidence",
    "lifecycleArcEvidence",
    "readOnlyBoundaryEvidence",
    "provenanceSeparationEvidence",
    "failClosedStalenessEvidence",
    "degradedRenderingEvidence",
)


CONTRADICTED_RECORDS = ("lifecycleArcEvidence",)


def _record_block(model: str, record: str) -> str:
    block = re.search(rf"part {record} : RetainedVisualizationEvidence \{{.*?\n  \}}", model, re.S)
    assert block, record
    return block.group(0)


def test_retained_evidence_is_scoped_to_its_integrity_gap() -> None:
    """GAP-AEBS-010-009: the retained records ran on builds that are not
    exactly identified, and EVID-AEBS-S2-002 rests on a statement its own
    frame log contradicts. Scoped observations, never a pass; by owner
    decision of 2026-10-09 no re-capture is planned."""
    model = _model()
    gap = re.search(r"part gapRetainedEvidenceIntegrity : IncrementGap \{.*?\n  \}", model, re.S)
    assert gap
    for fact in ("GAP-AEBS-010-009", "4d8dc1b", "6.876 m/s", "de4sdv-ros2-autoware"):
        assert fact in gap.group(0), fact
    for record in RETAINED_RECORDS:
        expected = (
            "contradictedByRetainedData" if record in CONTRADICTED_RECORDS else "observedUnidentifiedBuild"
        )
        assert f"VisualizationEvidenceDisposition::{expected};" in _record_block(model, record), record
        assert re.search(rf"\bfrom {record} to gapRetainedEvidenceIntegrity;", model), record
    pilot = _pilot()
    statuses = {case["id"]: case["status"] for case in pilot["verification_cases"]}
    assert statuses["VC-AEBS-S2-002"] == "contradicted_by_retained_data_no_recapture_planned"
    for number in (1, 3, 4, 5):
        assert statuses[f"VC-AEBS-S2-{number:03d}"] == "observed_unidentified_build"
    assert not any(status.startswith("pass") for status in statuses.values())
    gaps = {gap["id"]: gap.get("model_element") for gap in pilot["runtime_evidence_gaps"]}
    assert gaps["GAP-AEBS-010-009"] == "gapRetainedEvidenceIntegrity"


def test_no_recapture_is_pending_and_the_gap_stays_open() -> None:
    """Owner decision 2026-10-09: no re-capture is planned. Nothing may say
    one is pending, and GAP-AEBS-010-009 stays open as an accepted
    limitation."""
    model, pilot_text = _model(), PILOT.read_text(encoding="utf-8")
    for text in (model, pilot_text):
        for stale in ("re-capture pending", "pending re-capture", "until re-capture",
                      "recapture_pending", "planned separately", "re-captured from"):
            assert stale not in text, stale
    gap = re.search(r"part gapRetainedEvidenceIntegrity : IncrementGap \{.*?\n  \}", model, re.S)
    assert gap and "no re-capture is planned" in gap.group(0) and "2026-10-09" in gap.group(0)
    status = {entry["id"]: entry["status"] for entry in _pilot()["runtime_evidence_gaps"]}
    assert status["GAP-AEBS-010-009"] == "open_accepted_limitation_no_recapture_planned"


def test_v21_record_errors_are_not_asserted_as_fact() -> None:
    """The v21 take used one bench host, and its ego re-accelerated after
    release. No evidence record may name the second VM or assert a verified
    stop throughout RELEASED, and the counter-claim must bound the claim."""
    model = _model()
    environments = re.findall(r'executionEnvironmentIdentity = "([^"]*)"', model)
    assert environments
    assert not [env for env in environments if "ros2-autoware" in env]
    lifecycle = _record_block(model, "lifecycleArcEvidence")
    assert "onward (ego speed 0.0 m/s, verified stop)" not in lifecycle
    assert "contradicted by the retained data" in lifecycle
    assert "is not established" in _record_block(model, "failClosedStalenessEvidence")
    assert "requirement counterClaimRetainedRecordContradicted : VisualizationCounterClaim {" in model
    for target in ("visualizationInstrumentationClaim", "gapRetainedEvidenceIntegrity"):
        assert re.search(rf"\bfrom counterClaimRetainedRecordContradicted to {target};", model), target


def test_restoration_is_deferred_not_proven() -> None:
    pilot = _pilot()
    restoration = next(
        c for c in pilot["verification_cases"] if c["id"] == "VC-AEBS-S2-007"
    )
    assert restoration["status"] == "deferred_not_proven"
    assert "current_evidence" not in restoration
    deferred = {d["id"]: d["status"] for d in pilot["phase10_claim"]["deferred_items"]}
    assert deferred.get("REQ-AEBS-S2-009") == "success_criteria_deferred_not_proven"


# Planned cases for the requirements that no retained campaign verifies:
# case id -> (usage, verified requirement usages).
PLANNED_CASES = {
    "VC-AEBS-S2-008": (
        "liveSourceFidelityVerification",
        {"reqSourceFidelity", "reqNativeParticipation", "reqDe4sdvParticipation"},
    ),
    "VC-AEBS-S2-009": (
        "staleAndInvalidFrameVerification",
        {"reqFailClosedFreshness", "reqInvalidRejection"},
    ),
    "VC-AEBS-S2-010": (
        "renderingEnvironmentVerification",
        {"reqAaosEnvironmentObservation", "reqNoHostBrowserSurface"},
    ),
}


def test_planned_cases_are_not_executed_and_bind_no_evidence() -> None:
    """Planning only: no execution, no evidence record, no argument support."""
    pilot = _pilot()
    model = _model()
    cases = {case["id"]: case for case in pilot["verification_cases"]}
    for case_id, (usage, requirements) in PLANNED_CASES.items():
        case = cases[case_id]
        assert case["status"] == "not_executed", case_id
        assert "current_evidence" not in case, case_id
        block = re.search(rf"verification {usage} : (\w+) \{{.*?\n  \}}", model, re.S)
        assert block and "not executed" in block.group(0), case_id
        definition = re.search(
            rf"verification def {block.group(1)} \{{.*?\n  \}}", model, re.S
        )
        assert definition and "not executed" in definition.group(0), case_id
        for requirement in requirements:
            assert f"verify {requirement} {{" in definition.group(0), (case_id, requirement)
        assert not re.search(rf"\bfrom {usage} to ", _strip_sysml_comments(model)), case_id


# Success criteria formalized after the retained take, stated directly in the
# requirement (no AC ID ever reached main): requirement -> verifying case usage.
LATE_SUCCESS_CRITERIA = {
    "REQ-AEBS-S2-015": "readOnlyBoundaryVerification",
    "REQ-AEBS-S2-016": "provenanceSeparationVerification",
    "REQ-AEBS-S2-017": "provenanceSeparationVerification",
    "REQ-AEBS-S2-018": "provenanceSeparationVerification",
    "REQ-AEBS-S2-020": "failClosedStalenessVerification",
    "REQ-AEBS-S2-021": "degradedRenderingVerification",
}


def test_late_success_criteria_are_not_assessed_against_retained_evidence() -> None:
    """The success criteria of REQ-AEBS-S2-015..018, -020 and -021 were
    formalized after the retained take: indexed not_assessed with a pointer to
    the case's retained record, and the case usage says its verdict does not
    cover them (review R1)."""
    model = _model()
    rows = {row["requirement"]: row for row in _pilot()["requirement_success_criteria"]}
    blocks = _requirement_blocks()
    for req, case in LATE_SUCCESS_CRITERIA.items():
        row = rows[req]
        assert "formerly" not in row and row["status"] == "not_assessed", req
        assert re.match(r"EVID-AEBS-S2-\d{3} retained ", row["evidence"]), req
        assert f"not assessed against these success criteria (objective of {row['case']})" in row["evidence"], req
        criteria = _success_criteria(blocks[req][1])
        assert criteria and criteria.startswith("Met when") and "shall" not in criteria, req
        usage_block = re.search(rf"verification {case} : \w+ \{{.*?\n  \}}", model, re.S)
        assert usage_block, case
        usage_text = " ".join(usage_block.group(0).split())
        assert req.replace("REQ-AEBS-S2-", "-") in usage_text, (req, case)
        assert "formalized after the retained take" in usage_text, case
        assert "case verdict does not cover" in usage_text, case


def test_fixture_path_case_states_its_synthetic_scope() -> None:
    """Owner decision 2026-10-09: VC-AEBS-S2-009 stays a planned fixture-path
    case with its fixture scope stated explicitly in its doc (synthetic
    degraded inputs; it does not verify the live chain). Live-chain
    verification can be added if evidence is ever captured."""
    model = _model()
    usage = re.search(
        r"verification staleAndInvalidFrameVerification : (\w+) \{.*?\n  \}", model, re.S
    )
    assert usage
    definition = re.search(rf"verification def {usage.group(1)} \{{.*?\n  \}}", model, re.S)
    assert definition
    for block in (usage.group(0), definition.group(0)):
        # Join wrapped doc lines: drop each continuation line's leading "*".
        text = " ".join(re.sub(r"\n\s*\*(?!/)", "\n", block).split())
        assert "synthetic degraded inputs" in text
        assert "does not verify the live chain" in text


def test_every_requirement_is_verified_by_a_case_objective() -> None:
    model = _model()
    needs = _read(MODEL_DIR / "aebs_visualization_needs_requirements.sysml")
    requirements = set(
        re.findall(r"requirement (req\w+) : VisualizationInstrumentRequirementCandidate", needs)
    )
    assert len(requirements) == 20
    objectives = "\n".join(re.findall(r"objective \w+ \{(.*?)\n    \}", model, re.S))
    verified = set(re.findall(r"\bverify (req\w+)", objectives))
    assert requirements <= verified, sorted(requirements - verified)


def test_scenario_safety_outcome_stays_deferred() -> None:
    model = _model()
    pilot = _pilot()
    assert pilot["phase10_claim"]["scenario_safety_outcome"] == "deferred_not_proven"
    assert "scenarioSafetyDeferred" in model
    assert "deferred_not_proven" in model


def test_claim_boundary_forbids_safety_and_certification_reading() -> None:
    model = _model()
    claim_block = re.search(
        r"requirement visualizationInstrumentationClaim : VisualizationClaim \{.*?\n  \}",
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
    criteria = _success_criteria(_requirement_blocks()["REQ-AEBS-S2-005"][1])
    assert criteria and "issues no vehicle command" in criteria
    definition = re.search(r"verification def VisualizationReadOnlyBoundaryVerification \{.*?\n  \}", model, re.S)
    assert definition and "verify reqNonInterference {" in definition.group(0)
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
        "gap010RestorationUnexercised",
        "gap010LiveDegradationUnproven",
        "gap010InterVmRouteDeferred",
    ):
        assert gap in model
    pilot = _pilot()
    for gap in pilot["runtime_evidence_gaps"]:
        assert gap["owner"] == "successor_increment"


def test_cross_increment_traces_use_accepted_chain_elements() -> None:
    model = _model()
    for target in (
        "to testArticle;",
        "to testArticle::visualizationChain;",
        "to testArticle::visualizationChain::instrument;",
        "to coordinatorStateProvenance;",
    ):
        assert target in model
    # Evidence traces point at the configured article, not the design-level
    # Phase 8 decomposition.
    assert "to physicalSystem" not in model
    # MW-010 predecessor decision must be referenced, never restated.
    framing = _read(FRAMING)
    assert "successorIncrementDecision010" in framing


def test_views_use_argumentation_assurance_viewpoint() -> None:
    model = _model()
    assert model.count("view aebsVisualization") >= 2
    assert "ArgumentationAssuranceViewpoint" in model
    assert "frame visualizationArgumentationAssuranceConcern" in model


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
        r"part def VisualizationVerificationBench \{(.*?)\n  \}",
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
    """No success-criteria row in the pilot carries a partial-into-pass upgrade."""
    pilot = _pilot()
    for row in pilot["requirement_success_criteria"]:
        assert row["status"] != "pass", row["requirement"]
        assert "pass_partial" not in row["status"], row["requirement"]
    assert "pass" not in pilot["evidence_integrity_obligation"]["status"]


def _strip_sysml_comments(text: str) -> str:
    """Blank out /* */ and // comments while preserving line structure."""
    text = re.sub(
        r"/\*.*?\*/",
        lambda match: re.sub(r"[^\n]", " ", match.group(0)),
        text,
        flags=re.DOTALL,
    )
    return re.sub(r"//[^\n]*", "", text)


_DECLARATION_RE = re.compile(
    r"\b(?:part|item|enum|concern|view|requirement|verification|calc|action|"
    r"port|flow|attribute|ref)\s+(?:def\s+)?([A-Za-z_][A-Za-z0-9_]*)"
)

RETIRED_S2_ROLE_SHORTHAND_NAMES = (
    # Approved direct mappings.
    "VisualizationScenarioS2",
    "VisualizationObservationS2",
    "RetainedVisualizationEvidenceS2",
    "ReplayedVisualizationEvaluationS2",
    "VisualizationVandVBenchS2",
    "MapS2OutcomeToVerdict",
    # Defs de-shorthand without further change of meaning.
    "VisualizationAcceptanceCriterionS2",
    "VisualizationClaimS2",
    "VisualizationArgumentS2",
    "VisualizationCounterClaimS2",
    "VisualizationChainCorrelationVerificationS2",
    "VisualizationLifecycleArcVerificationS2",
    "VisualizationReadOnlyBoundaryVerificationS2",
    "VisualizationProvenanceSeparationVerificationS2",
    "VisualizationFailClosedStalenessVerificationS2",
    "VisualizationDegradedRenderingVerificationS2",
    "VisualizationRestorationVerificationS2",
    # Generic names that gain the visualization qualifier.
    "verificationSystemS2",
    "s2VisualizationInstrumentationClaim",
    "argumentationAssuranceConcernS2",
    # Usage records de-shorthand (stems keep their identity role).
    "scenarioSafetyDeferredS2",
    "restorationEvidencePlannedS2",
)


def _has_s1_s2_role_shorthand(name: str) -> bool:
    from scripts.check_naming import has_role_shorthand
    return has_role_shorthand(name)


def test_role_shorthand_detection_preserves_technology_names() -> None:
    for name in ("VisualizationS1", "VisualizationS2", "s1Claim", "s2Claim"):
        assert _has_s1_s2_role_shorthand(name), name
    for name in ("ROS2TopicEndpoint", "System2Instrumentation", "VisualizationScenario"):
        assert not _has_s1_s2_role_shorthand(name), name


def test_target_declarations_carry_no_role_shorthand() -> None:
    """Naming conventions §2/§3: the package (and each owning def) establishes
    the System 2 role, so locally declared names must not embed the redundant
    S1/S2 role shorthand. Stable hyphenated IDs (EVID/AC/VC/...-AEBS-S2-*) are
    identity records and are not declarations — they stay untouched."""
    code = _strip_sysml_comments(_model())
    offenders = sorted(
        {
            name
            for name in _DECLARATION_RE.findall(code)
            if _has_s1_s2_role_shorthand(name)
        }
    )
    assert not offenders, (
        f"declarations still embed S1/S2 role shorthand: {offenders}"
    )


def test_retired_s2_names_absent_from_live_source() -> None:
    """Every retired S2-shorthand declaration name is gone from live sources:
    the target model, the pilot record, the generated view index, and all
    sibling SysML slices. docs/naming/* (migration record) and retained
    evidence prose are historical surfaces and intentionally out of scope."""
    live_sources = "\n".join(
        [
            _model(),
            _read(PILOT),
            _read(MODEL_DIR / "VIEWS.md"),
            *(
                path.read_text(encoding="utf-8")
                for path in sorted(MODEL_DIR.glob("*.sysml"))
            ),
        ]
    )
    residual = [
        name
        for name in RETIRED_S2_ROLE_SHORTHAND_NAMES
        if name in live_sources
    ]
    assert not residual, f"retired names still referenced in live source: {residual}"


def test_success_criteria_gap_names_every_requirement_without_success_criteria() -> None:
    """GAP-AEBS-010-010 names exactly the requirements that state no
    successCriteria."""
    missing = sorted(
        req for req, (_usage, block) in _requirement_blocks().items() if not _success_criteria(block)
    )
    assert missing == [
        "REQ-AEBS-S2-002", "REQ-AEBS-S2-003", "REQ-AEBS-S2-004", "REQ-AEBS-S2-006",
        "REQ-AEBS-S2-008", "REQ-AEBS-S2-012", "REQ-AEBS-S2-013",
    ]
    gap = re.search(r"part gapRequirementSuccessCriteriaMissing : IncrementGap \{.*?\n  \}", _model(), re.S)
    assert gap and "GAP-AEBS-010-010" in gap.group(0)
    assert set(re.findall(r"REQ-AEBS-S2-\d{3}", gap.group(0))) == set(missing)
    deferred = {item["id"] for item in _pilot()["phase10_claim"]["deferred_items"]}
    assert "GAP-AEBS-010-010" in deferred


def test_late_success_criteria_name_deciding_observables_unambiguously() -> None:
    """Each late success criterion names an observable that can decide it,
    with an explicit quantifier; no ambiguous "frames or user-interface dumps"
    list (review R4)."""
    blocks = _requirement_blocks()
    texts = {req: _success_criteria(blocks[req][1]) for req in LATE_SUCCESS_CRITERIA}
    for req, text in texts.items():
        assert text, req
        assert "frames or user-interface dumps" not in text, req
        assert "frame or user-interface dump" not in text, req
        assert re.search(r"\b(each|no|any)\b", text), (req, "quantifier")
    assert "source adapter's subscriptions" in texts["REQ-AEBS-S2-016"]
    assert "retained frame record" in texts["REQ-AEBS-S2-016"]
    assert "retained bridge receipt record" in texts["REQ-AEBS-S2-020"]
    assert "either artifact suffices" in texts["REQ-AEBS-S2-015"]


def test_claim_deferred_items_name_every_planned_item() -> None:
    """Review R8: the claim's deferred list names the planned cases, the
    success criteria not assessed, and the requirements only a planned case
    verifies."""
    deferred = {item["id"]: item["status"] for item in _pilot()["phase10_claim"]["deferred_items"]}
    for case_id in PLANNED_CASES:
        assert deferred.get(case_id) == "not_executed", case_id
    for req in LATE_SUCCESS_CRITERIA:
        assert deferred.get(req) == "success_criteria_not_assessed", req
    assert deferred.get("REQ-AEBS-S2-009") == "success_criteria_deferred_not_proven"
    cases = {c["id"]: c for c in _pilot()["verification_cases"]}
    planned_only = set()
    for case_id in PLANNED_CASES:
        planned_only |= set(cases[case_id]["requirement_ids"])
    executed = set()
    for case_id, case in cases.items():
        if case_id not in PLANNED_CASES:
            executed |= set(case["requirement_ids"])
    for requirement_id in planned_only - executed:
        assert deferred.get(requirement_id) == "planned_verification_only", requirement_id

def test_success_criteria_are_campaign_neutral() -> None:
    """Success criteria belong to the requirement (owner decision
    2026-10-10). Choice made during the walk, for Orkun's review: they state
    what evidence would show the requirement met, so none may name one past
    campaign or its retained take."""
    for req, (_usage, block) in _requirement_blocks().items():
        criteria = _success_criteria(block)
        if not criteria:
            continue
        assert not re.search(r"\bthe retained (take|run|bridge receipt record)\b", criteria), req
        assert not re.search(r"\b(v21|campaign|2026-\d\d-\d\d)\b", criteria, re.I), req
    texts = {req: _success_criteria(block) for req, (_u, block) in _requirement_blocks().items()}
    assert texts["REQ-AEBS-S2-011"].count("the verification take") == 2
    assert texts["REQ-AEBS-S2-019"].startswith("Met when the verification take shows")
