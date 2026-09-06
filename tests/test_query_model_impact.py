"""Tests for the AEBS model impact-analysis tool.

These tests exercise :mod:`scripts.query_model_impact` against the real
AEBS model slices shipped with the repository. They assert that the
reverse-impact graph correctly traces requirement -> evidence contract ->
verification case across the INC-AEBS-009B/009C/009D/009G/009I slices.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import query_model_impact as qmi

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "query_model_impact.py"


# --- Requirement listing ---------------------------------------------------


def test_list_requirements_returns_all_25_names():
    names = qmi.list_requirements()
    assert len(names) == 25, f"expected 25 requirement/need names, got {len(names)}"


def test_list_requirements_contains_expected_names():
    names = set(qmi.list_requirements())
    # Representative subset covering System 1 req/ and System 2 req/need names.
    expected = {
        "reqCommandEmergencyBraking",
        "reqProvideCollisionWarning",
        "reqAllowDriverOverride",
        "reqDetectAEBSFailureCondition",
        "reqPedestrianTargetResponse",
        "reqBicycleTargetResponse",
        "reqResistFalseBrakingCommand",
        "reqHandleDegradedUnavailableInputs",
        "needCommonAEBSCapability",
        "needBoundedDegradationAndAvailability",
        "needVisibleRegulatoryAssumptions",
    }
    missing = expected - names
    assert not missing, f"missing expected requirements: {missing}"


# --- Evidence contract listing ---------------------------------------------


def test_list_evidence_contracts_nonempty_and_covering_increments():
    contracts = set(qmi.list_evidence_contracts())
    assert contracts, "expected at least one evidence contract"
    # Each increment's slice declares its (de-numbered, semantic) evidence
    # contract type (model-organization-audit.md M3).
    expected_contract_stems = (
        "evidenceContractWarningLead",  # nominal (009B provenance)
        "evidenceContractMRMGateChain",  # partial intervention (009C)
        "evidenceContractOverrideFreshnessReplay",  # override (009D)
        "evidenceContractWarningSilenceWindow",  # non-activation (009E)
        "evidenceContractStateOwnership",  # degraded input (009F)
        "evidenceContractConfiguredPedestrianTarget",  # pedestrian (009G)
        "evidenceContractConfiguredBicycleTarget",  # bicycle (009H)
        "evidenceContractSourceIdentity",  # regulatory criterion (009I)
    )
    for stem in expected_contract_stems:
        assert any(stem in c for c in contracts), f"no evidence contract {stem}"


# --- reqCommandEmergencyBraking -------------------------------------------


def test_query_reqCommandEmergencyBraking_returns_009B_009C_009D():
    report = qmi.query_impact("reqCommandEmergencyBraking")
    files = {edge.file for edge in report.edges}
    # 009B (nominal), 009C (partial intervention) both trace to braking.
    assert "aebs_evidence.sysml" in files, files
    assert "aebs_partial_intervention_verification.sysml" in files, files


def test_query_reqCommandEmergencyBraking_sources_include_expected_contracts():
    report = qmi.query_impact("reqCommandEmergencyBraking")
    sources = {edge.source for edge in report.edges}
    assert "evidenceContractFreshOverrideClear" in sources, sources
    assert "evidenceContractNominalBrakingPath" in sources, sources
    assert "evidenceContractMRMGateChain" in sources, sources


def test_query_reqCommandEmergencyBraking_edges_carry_verification_def():
    report = qmi.query_impact("reqCommandEmergencyBraking")
    for edge in report.edges:
        if edge.file == "aebs_evidence.sysml":
            assert edge.verification_def == "NominalMovingVehicleTargetVerification"
        elif edge.file == "aebs_partial_intervention_verification.sysml":
            assert edge.verification_def == "NativeInterventionToMRMVerification"


# --- reqPedestrianTargetResponse ------------------------------------------


def test_query_reqPedestrianTargetResponse_returns_009G_and_009I():
    report = qmi.query_impact("reqPedestrianTargetResponse")
    files = {edge.file for edge in report.edges}
    assert "aebs_pedestrian_verification.sysml" in files, files
    assert "aebs_regulatory_criterion_verification.sysml" in files, files


def test_query_reqPedestrianTargetResponse_sources_include_expected_contracts():
    report = qmi.query_impact("reqPedestrianTargetResponse")
    sources = {edge.source for edge in report.edges}
    assert "evidenceContractConfiguredPedestrianTarget" in sources, sources
    assert "evidenceContractPedestrianApplicableCriterion" in sources, sources


# --- Nonexistent target ----------------------------------------------------


def test_query_nonexistent_requirement_returns_empty_results():
    report = qmi.query_impact("reqDoesNotExist")
    assert report.edges == []
    data = report.to_dict()
    assert data["count"] == 0
    assert data["files"] == {}


# --- JSON output -----------------------------------------------------------


def test_json_output_is_valid_json_and_has_expected_shape():
    report = qmi.query_impact("reqCommandEmergencyBraking")
    data = report.to_dict()
    serialized = json.dumps(data)
    parsed = json.loads(serialized)
    assert parsed["target"] == "reqCommandEmergencyBraking"
    assert parsed["count"] == len(report.edges)
    assert "files" in parsed
    for fname, payload in parsed["files"].items():
        assert "count" in payload
        assert "edges" in payload
        assert isinstance(payload["edges"], list)


def test_cli_json_flag_produces_valid_json():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--json", "reqCommandEmergencyBraking"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["target"] == "reqCommandEmergencyBraking"
    assert data["count"] >= 3  # at least 009B(2) + 009C(1)


# --- CLI smoke tests -------------------------------------------------------


def test_cli_list_requirements():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--list-requirements"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    assert "reqCommandEmergencyBraking" in proc.stdout
    assert "needCommonAEBSCapability" in proc.stdout


def test_cli_list_evidence_contracts():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--list-evidence-contracts"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    assert "evidenceContractWarningLead" in proc.stdout


def test_cli_text_query_includes_file_grouping():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "reqCommandEmergencyBraking"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    assert "aebs_evidence.sysml" in proc.stdout
    assert "aebs_partial_intervention_verification.sysml" in proc.stdout
    assert "evidenceContractFreshOverrideClear" in proc.stdout


def test_cli_text_query_nonexistent_reports_no_results():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "reqDoesNotExist"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    assert "No evidence contracts" in proc.stdout or "none" in proc.stdout.lower()


# --- Graph integrity -------------------------------------------------------


def test_reverse_graph_is_consistent():
    """Every edge target appears as a key in the reverse graph."""
    graph = qmi.build_reverse_impact_graph()
    for target, edges in graph.items():
        for edge in edges:
            assert edge.target == target


def test_every_edge_has_a_file_and_source():
    graph = qmi.build_reverse_impact_graph()
    for target, edges in graph.items():
        assert edges, f"empty edge list for {target}"
        for edge in edges:
            assert edge.source, f"empty source on {edge}"
            assert edge.file.endswith(".sysml"), f"bad file name {edge.file}"
