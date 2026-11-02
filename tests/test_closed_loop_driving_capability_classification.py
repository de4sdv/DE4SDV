"""Content pins for the closed-loop driving capability classification (phase 3), not semantic validation."""

from pathlib import Path
import re

from sysml_shapes import braced_body, strip_comments

ROOT = Path(__file__).resolve().parents[1]
DRIVING = ROOT / "textual-notation-of-model/packages/features/driving"
FRAMING = DRIVING / "closed_loop_driving_framing.sysml"
MODEL = DRIVING / "closed_loop_driving_capability_classification.sysml"
SCOPE = ROOT / "model-based-product-line-engineering/scoping/de4sdv_aebs_product_line_scope.sysml"
PACKAGE = "DE4SDV_ClosedLoopDrivingCapabilityClassification"
CANDIDATE = "autoE2EDrivingStack"
GAP = "DE4SDV_ClosedLoopDrivingFraming::gapProductLineAdmission"
DEFERRED_DRIVING_STACK = "DE4SDV_AEBSProductLineScope::deferredVariabilitySet::drivingStackVariability"

#: The product-line characteristic kinds of the method kernel. Phase 3 records the feature-model delta
#: only: a common capability is never a record, and this increment adds exactly one feature candidate
#: (owner decisions of 2026-11-02: AutoE2E is the driving stack of a new planned member).
CHARACTERISTIC_KINDS = (
    "ProductLineCharacteristic", "ProductLineFeatureCandidate", "DeferredProductLineScope",
    "CommonProductLineCapability",
)


def _raw() -> str:
    assert MODEL.is_file(), "phase 3 of INC-DRIVING-001 needs a capability classification model"
    return MODEL.read_text(encoding="utf-8")


def _code() -> str:
    return strip_comments(_raw())


def _doc(raw: str, declaration: str) -> str:
    return " ".join(re.sub(r"(?m)^\s*\*\s?", "", braced_body(raw, declaration)).split())


def test_the_classification_records_exactly_the_autoe2e_feature_candidate():
    code = _code()
    assert re.search(rf"\bpackage\s+{PACKAGE}\s*\{{", code)
    kinds = "|".join(CHARACTERISTIC_KINDS)
    characteristics = re.findall(rf"\bpart\s+(\w+)\s*:\s*({kinds})\b", code)
    assert characteristics == [(CANDIDATE, "ProductLineFeatureCandidate")]
    assert "CommonProductLineCapability" not in code, "core elements are common by default and get no record"


def test_the_candidate_needs_cameras_and_leaves_lidar_open():
    doc = _doc(_raw(), f"part {CANDIDATE} : ProductLineFeatureCandidate")
    # Owner decision of 2026-11-02: AutoE2E plans from cameras and takes no LiDAR input, so the
    # feature model will state that it requires the camera feature and leave LiDAR selectable. Each
    # statement is pinned on its own; the PLEML edit lands in phase 9 with the adapter derivation.
    assert "AutoE2E" in doc and "phase 9" in doc
    assert "takes no LiDAR input" in doc
    assert "requires the camera feature" in doc
    assert "leaves LiDAR selectable" in doc


def test_the_candidate_traces_to_the_deferred_driving_stack_variability_and_the_admission_gap():
    code = _code()
    targets = {
        target for source, target in re.findall(r"\bdependency\s+\w+\s+from\s+(\S+)\s+to\s+([^;]+);", code)
        if source == CANDIDATE
    }
    assert targets == {DEFERRED_DRIVING_STACK, GAP}
    scope = strip_comments(SCOPE.read_text(encoding="utf-8"))
    assert re.search(r"\bpart\s+deferredVariabilitySet\s*:\s*DeferredVariabilitySet\s*;", scope)
    deferred = braced_body(scope, "part def DeferredVariabilitySet")
    assert re.search(r"\bpart\s+drivingStackVariability\s*:\s*DeferredCurrentScopeVariability\s*;", deferred)
    assert re.search(r"\bpart\s+gapProductLineAdmission\s*:\s*IncrementGap\b",
                     strip_comments(FRAMING.read_text(encoding="utf-8")))


def test_the_owner_scope_decisions_the_gap_asks_for_are_recorded_against_it():
    # gapProductLineAdmission asks phase 3 to identify the owner scope decisions; a comment about the
    # gap records them for the member decision without rewriting the accepted phase 0 text.
    match = re.search(rf"\bcomment\s+\w+\s+about\s+{re.escape(GAP)}\s*/\*(.*?)\*/", _raw(), re.S)
    assert match, "a comment about the admission gap must state the identified owner scope decisions"
    text = " ".join(re.sub(r"(?m)^\s*\*\s?", "", match.group(1)).split())
    for decision in ("Autoware", "LiDAR", "Vehicle-Target AEBS", "Eclipse S-CORE", "ADR 0014"):
        assert decision in text, decision


def test_a_view_frames_the_classification_concern_and_exposes_the_candidate():
    code = _code()
    concerns = re.findall(r"\bconcern\s+(\w+)\s*:\s*ProductLineCapabilityClassificationConcern\b", code)
    assert len(concerns) == 1
    concern = braced_body(code, f"concern {concerns[0]} : ProductLineCapabilityClassificationConcern")
    assert re.search(r"\bsubject\s*;", concern)
    assert set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", concern)) == {"ProductLineEngineer", "SystemsEngineer"}
    views = re.findall(r"\bview\s+(\w+)\s*:\s*TVD::TableView\b", code)
    assert len(views) == 1
    view = braced_body(code, f"view {views[0]} : TVD::TableView")
    assert re.search(rf"\bviewpoint\s+\w+\s*:\s*ProductLineClassificationViewpoint\s*\{{\s*frame\s+{concerns[0]}\s*;", view)
    assert re.findall(r"\bexpose\s+([^;]+);", view) == [CANDIDATE]


def test_the_charter_names_the_classification_package():
    charter = braced_body(strip_comments(FRAMING.read_text(encoding="utf-8")),
                          "part closedLoopDrivingCharter : IncrementCharter")
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", charter, re.S)
    assert artifacts and PACKAGE in re.findall(r'"([^"]+)"', artifacts.group(1)), \
        "the charter's expected artifacts must name the package that now holds phase 3 content"
