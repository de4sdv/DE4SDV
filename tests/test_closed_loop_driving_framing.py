"""Content pins for the closed-loop driving increment, not semantic validation."""

from pathlib import Path
import re

import yaml

from sysml_shapes import braced_body, strip_comments

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "textual-notation-of-model/packages/features/driving/closed_loop_driving_framing.sysml"
PACKAGE = "DE4SDV_ClosedLoopDrivingFraming"


def test_increment_has_its_own_phase_zero_contract():
    assert MODEL.is_file(), "the owner's closed-loop question needs a framing model"
    code = strip_comments(MODEL.read_text(encoding="utf-8"))
    assert "part def ClosedLoopDrivingIncrement :> EngineeringIncrement" in code
    assert re.search(
        r"part\s+<'INC-DRIVING-001'>\s+closedLoopDrivingIncrement\s*:\s*ClosedLoopDrivingIncrement",
        code,
    )
    problem = braced_body(code, "requirement closedLoopDrivingProblem : ProblemStatement")
    assert "subject closedLoopDrivingSubject : ClosedLoopDrivingIncrement;" in problem
    charter = braced_body(code, "part closedLoopDrivingCharter : IncrementCharter")
    assert "ref part :>> increment = closedLoopDrivingIncrement;" in charter
    assert "ref part :>> systemOfInterest = candidateDrivingSystem;" in charter
    assert 'attribute :>> owner = "Orkun Yilmaz";' in charter
    assert "part closedLoopDrivingScope : IncrementScope" in code
    assert re.search(
        r"dependency\s+scopeToDrivingQuestion\s+from\s+closedLoopDrivingScope\s+to\s+closedLoopDrivingQuestion\s*;",
        code,
    )
    assert re.findall(r'MethodPhase::(\w+)', charter) == [
        "phase0_incrementFraming", "phase1_concernFraming", "phase2_operationalContext",
        "phase3_capabilityClassification", "phase4_needs", "phase5_requirements",
        "phase6_functionalArchitecture", "phase7_logicalArchitecture",
        "phase8_physicalRealization", "phase9_variabilityConfiguration",
        "phase10_vvEvidence", "phase11_publication", "phase12_baselineNextSlice",
    ]
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", charter, re.S)
    assert artifacts and re.findall(r'"([^"]+)"', artifacts.group(1)) == [PACKAGE]
    assert "frame closedLoopDrivingBoundary;" in code
    assert "viewpoint closedLoopDrivingFramingViewpoint : IncrementFramingViewpoint" in code
    assert "expose closedLoopDrivingCharter;" in code


def test_phase_zero_keeps_risks_and_nonclaims_visible():
    raw = MODEL.read_text(encoding="utf-8")
    code = strip_comments(raw)
    expected = {
        "asmEngineeringUse": ("IncrementAssumption", ("System 1", "System 2", "not production-ready")),
        "asmSourceAuthenticity": ("IncrementAssumption", ("pinned checkpoint", "synthetic-input", "not substitutes")),
        "asmCandidateReuse": ("IncrementAssumption", ("reuse candidate", "not trajectory", "not safety")),
        "gapClosedLoopPerformance": ("IncrementGap", ("20 fresh", "24 fps", "inference cadence", "real-time factor", "input-to-actuation age", "unmeasured")),
        "gapModelInputAndFeedback": ("IncrementGap", ("calibration", "history", "acceleration/curvature", "domain shift")),
        "gapTransportAndControl": ("IncrementGap", ("S-CORE", "AAOS", "existing AEBS", "control")),
        "gapProductLineAdmission": ("IncrementGap", ("ADR 0014", "Phase 3", "Phase 9")),
        "gapAdoptionAndRights": ("IncrementGap", ("maintainers", "checkpoint", "before deep adoption")),
        "gapBoundedCloudCampaign": ("IncrementGap", ("authorization", "shutdown", "credit")),
    }
    for name, (kind, phrases) in expected.items():
        declaration = f"part {name} : {kind}"
        assert declaration in code, f"missing framing record: {name}"
        documentation = braced_body(raw, declaration)
        normalized = " ".join(re.sub(r"(?m)^\s*\*\s?", "", documentation).split())
        for phrase in phrases:
            assert phrase in normalized, (name, phrase)
    assert "part closedLoopVerificationEnvironment : System2EngineeringAndAssuranceSystem" in code
    assert "OutOfScopeItem" not in braced_body(code, "part closedLoopDrivingScope : IncrementScope")
    assert not re.search(r"\b(?:verify|satisfy)\s+\w+", code)


def test_pilot_is_an_index_of_existing_artifacts_only():
    pilot = ROOT / "methodologies/sysmod-sysmlv2/pilots/driving-001-closed-loop.yaml"
    assert pilot.is_file(), "the new framing needs a discoverable pilot index"
    index = yaml.safe_load(pilot.read_text(encoding="utf-8"))
    assert set(index) == {"increment_id", "model_files", "documentation", "provenance"}
    assert index["increment_id"] == "INC-DRIVING-001"
    assert index["model_files"] == [{
        "package": PACKAGE,
        "file": str(MODEL.relative_to(ROOT)),
        "increment": f"{PACKAGE}::closedLoopDrivingIncrement",
        "charter": f"{PACKAGE}::closedLoopDrivingCharter",
        "view": f"{PACKAGE}::closedLoopDrivingFramingView",
    }]
    assert (ROOT / index["documentation"]).is_file()
    assert (ROOT / index["provenance"]).is_file()


def test_framing_view_exposes_scope_and_deferred_scope():
    code = strip_comments(MODEL.read_text(encoding="utf-8"))
    scope_items = set(re.findall(
        r"\bpart\s+(\w+)\s*:\s*(?:InScopeItem|OutOfScopeItem)\b", code
    ))
    assert scope_items, "the scope-coverage assertion must not be vacuous"
    view = braced_body(code, "view closedLoopDrivingFramingView")
    exposed = set(re.findall(r"\bexpose\s+(\w+)\s*;", view))
    required = scope_items | {"closedLoopDrivingBoundary"}
    assert required <= exposed, f"framing view omits boundary content: {sorted(required - exposed)}"
