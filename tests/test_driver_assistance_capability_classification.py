"""Content pins for the driver-assistance capability classification (phase 3), not semantic validation."""

from pathlib import Path
import re

from sysml_shapes import braced_body, strip_comments

ROOT = Path(__file__).resolve().parents[1]
DRIVING = ROOT / "textual-notation-of-model/packages/features/driving"
FRAMING = DRIVING / "driver_assistance_framing.sysml"
MODEL = DRIVING / "driver_assistance_capability_classification.sysml"
SCOPE = ROOT / "model-based-product-line-engineering/scoping/de4sdv_aebs_product_line_scope.sysml"
PACKAGE = "DE4SDV_DriverAssistanceCapabilityClassification"
CANDIDATE = "visionPilotDrivingStack"
ADMISSION_GAP = "DE4SDV_DriverAssistanceFraming::gapCandidateAdmission"
HMI_GAP = "DE4SDV_DriverAssistanceFraming::gapDriverHmiInProductLine"
DEFERRED_DRIVING_STACK = "DE4SDV_AEBSProductLineScope::deferredVariabilitySet::drivingStackVariability"
TAKES_EFFECT = "once its scope pull request takes effect"

#: The product-line characteristic kinds of the method kernel. Phase 3 records the feature-model delta
#: only (increment-workflow rule 10): a common capability is never a record, and this increment adds
#: exactly one feature candidate, VisionPilot as the vehicle application of a further member.
CHARACTERISTIC_KINDS = (
    "ProductLineCharacteristic", "ProductLineFeatureCandidate", "DeferredProductLineScope",
    "CommonProductLineCapability",
)


def _raw() -> str:
    assert MODEL.is_file(), "phase 3 of INC-DRIVING-002 needs a capability classification model"
    return MODEL.read_text(encoding="utf-8")


def _code() -> str:
    return strip_comments(_raw())


def _flat(text: str) -> str:
    return " ".join(re.sub(r"(?m)^\s*\*\s?", "", text).split())


def _doc(raw: str, declaration: str) -> str:
    return _flat(braced_body(raw, declaration))


def _comment(about: str) -> str:
    match = re.search(rf"\bcomment\s+\w+\s+about\s+{re.escape(about)}\s*/\*(.*?)\*/", _raw(), re.S)
    assert match, f"a comment about {about} must record what phase 3 identified"
    return _flat(match.group(1))


def _item(text: str, marker: str) -> str:
    items = [item for item in text.split(" - ") if marker in item]
    assert len(items) == 1, f"one item of the comment names {marker}"
    return items[0].strip()


def _dependencies(code: str) -> list[tuple[str, str, str]]:
    return re.findall(r"\bdependency\s+(\w+)\s+from\s+(\S+)\s+to\s+([^;]+?)\s*;", code)


def test_the_classification_records_exactly_the_visionpilot_feature_candidate():
    code = _code()
    assert re.search(rf"\bpackage\s+{PACKAGE}\s*\{{", code)
    kinds = "|".join(CHARACTERISTIC_KINDS)
    characteristics = re.findall(rf"\bpart\s+(\w+)\s*:\s*({kinds})\b", code)
    assert characteristics == [(CANDIDATE, "ProductLineFeatureCandidate")]
    assert "CommonProductLineCapability" not in code, "core elements are common by default and get no record"
    assert "DeferredProductLineScope" not in code, "this increment defers no scope of its own"
    assert len(re.findall(r"\bpart\s+\w+\s*:", code)) == 1, "the candidate is the only part of the slice"


def test_the_candidate_states_what_it_distinguishes_reads_and_writes():
    doc = _doc(_raw(), f"part {CANDIDATE} : ProductLineFeatureCandidate")
    assert "VisionPilot" in doc
    assert "distinguishes a camera-only driver-assistance member from the Autoware members and from the " \
           "AutoE2E candidate" in doc
    assert "one front-camera image and the vehicle speed" in doc
    assert "writes steering and acceleration" in doc


def test_the_candidate_needs_the_camera_and_linux_and_leaves_lidar_selectable():
    doc = _doc(_raw(), f"part {CANDIDATE} : ProductLineFeatureCandidate")
    assert "It requires the camera, so phase 9 adds a requiresFeatures constraint and leaves LiDAR and radar " \
           "selectable." in doc
    assert "requires Linux on the main side" in doc
    assert "its camera source uses V4L2, a Linux interface." in doc
    assert "ROS 2 is a build option, which its upstream simulator path uses." in doc
    assert "Phase 9 adds the Linux constraint as well." in doc
    for wrong in ("requires LiDAR", "requires the LiDAR", "LiDAR is required", "requires ROS 2", "needs neither ROS 2",
                  "build option only"):
        assert wrong not in doc, wrong


def test_the_candidate_defers_the_adapter_and_its_other_functions_and_waits_for_the_member_decision():
    doc = _doc(_raw(), f"part {CANDIDATE} : ProductLineFeatureCandidate")
    assert "middleware adapter to Eclipse S-CORE, which phase 8 realizes first and phase 9 derives" in doc
    assert "speed-following and a lane-keeping function, which no case of this increment judges" in doc
    assert "Phase 9 decides whether the configuration selects them." in doc
    assert "Acceptance waits for the member decision." in doc


def test_the_candidate_traces_to_the_deferred_driving_stack_variability_and_the_admission_gap():
    dependencies = _dependencies(_code())
    assert sorted(dependencies) == sorted([
        ("visionPilotCandidateOfDeferredDrivingStackVariability", CANDIDATE, DEFERRED_DRIVING_STACK),
        ("visionPilotCandidateAnswersCandidateAdmissionGap", CANDIDATE, ADMISSION_GAP),
    ]), "two dependencies, each from the candidate, each to an element that the model holds"
    scope = strip_comments(SCOPE.read_text(encoding="utf-8"))
    assert re.search(r"\bpackage\s+DE4SDV_AEBSProductLineScope\s*\{", scope)
    assert re.search(r"\bpart\s+deferredVariabilitySet\s*:\s*DeferredVariabilitySet\s*;", scope)
    deferred = braced_body(scope, "part def DeferredVariabilitySet")
    assert re.search(r"\bpart\s+drivingStackVariability\s*:\s*DeferredCurrentScopeVariability\s*;", deferred)
    framing = strip_comments(FRAMING.read_text(encoding="utf-8"))
    assert re.search(r"\bpackage\s+DE4SDV_DriverAssistanceFraming\s*\{", framing)
    for gap in ("gapCandidateAdmission", "gapDriverHmiInProductLine", "gapNoSeparateEmergencyFunction"):
        assert re.search(rf"\bpart\s+{gap}\s*:\s*IncrementGap\b", framing), gap


def test_no_dependency_points_to_an_element_the_model_does_not_hold():
    # ADR 0023 and ADR 0026 change the scope only once their scope pull requests take effect. Until then
    # the S-CORE-integrated alternative and a display in the common content are no model elements, so
    # the slice names them in comments and never as a dependency target.
    for _name, _source, target in _dependencies(_code()):
        assert target in (DEFERRED_DRIVING_STACK, ADMISSION_GAP), target
        assert not re.search(r"(?i)score|integrated|display|hmi|commonCore", target), target


def test_the_scope_decisions_the_admission_gap_asks_for_are_named_against_it():
    text = _comment(ADMISSION_GAP)
    for phrase in ("this increment admits nothing", "ADR 0014", "a new planned member",
                   "Autoware and LiDAR stop being common", "driving-stack and sensing variability leave deferral",
                   "INC-DRIVING-001", "Vehicle-Target AEBS", "protected emergency command path",
                   "ADR 0023 decision 5", "gapNoSeparateEmergencyFunction"):
        assert phrase in text, phrase
    runtime = _item(text, "Linux and ROS 2 runtime of Autoware")
    assert "the candidate runs on Linux and does not use the Autoware runtime" in runtime
    assert "ROS 2 is a build option of the candidate, which its upstream simulator path uses" in runtime, \
        "the upstream simulator path runs over ROS 2, so the slice does not say the candidate needs none"
    assert "needs neither ROS 2" not in text
    assert re.search(r"\bis open\.$", runtime), \
        "whether the runtime content narrows to Linux or stops being common is stated as open"
    assert "Eclipse S-CORE is reference-only" in text and "valid and not admitted" in text
    assert "ADR 0023, accepted, takes Eclipse S-CORE out of the reference-only set into the S-CORE-integrated " \
        f"alternative {TAKES_EFFECT} in the model" in text
    assert "then realizes that alternative and needs no new one" in text


def test_the_display_and_the_sound_are_classified_against_the_hmi_gap():
    text = _comment(HMI_GAP)
    assert "optional feature that requires the AAOS SDV guest" in text
    assert f"ADR 0026, accepted, makes a display common content of every member {TAKES_EFFECT}" in text
    assert "Under neither reading is it a feature candidate of this member." in text
    assert "The application's own visualization is not the member's display." in text
    assert "no member differs by one, so the sound is no feature candidate" in text
    sound = _item(text, "The sound:")
    assert re.search(r"Whether the acoustic warning becomes common content of the driver warning is open\b",
                     sound), "the sound's place in the common content is stated as open"


def test_the_header_gives_each_unrecorded_item_its_reason():
    header = _flat(_raw().split("package ", 1)[0])
    for phrase in ("INC-DRIVING-002, phase 3", "VisionPilot", "common by default and get no record",
                   "the feature model already makes LiDAR optional", "display", "sound",
                   "Eclipse S-CORE gets none: the feature model already holds it as a middleware alternative",
                   "The middleware adapter gets none: it is a derived realization"):
        assert phrase in header, phrase


def test_a_view_frames_the_classification_concern_and_exposes_only_the_candidate():
    code = _code()
    concerns = re.findall(r"\bconcern\s+(\w+)\s*:\s*ProductLineCapabilityClassificationConcern\b", code)
    assert concerns == ["driverAssistanceClassificationConcern"]
    concern = braced_body(code, f"concern {concerns[0]} : ProductLineCapabilityClassificationConcern")
    assert re.search(r"\bsubject\s*;", concern)
    assert set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", concern)) == {"ProductLineEngineer", "SystemsEngineer"}
    views = re.findall(r"\bview\s+(\w+)\s*:\s*TVD::TableView\b", code)
    assert views == ["driverAssistanceClassificationView"]
    view = braced_body(code, f"view {views[0]} : TVD::TableView")
    assert re.search(rf"\bviewpoint\s+\w+\s*:\s*ProductLineClassificationViewpoint\s*\{{\s*frame\s+{concerns[0]}\s*;",
                     view)
    assert re.findall(r"\bexpose\s+([^;]+);", code) == [CANDIDATE]
    assert re.search(r"\bfilter\s+@\s*SysML::PartUsage\s*;", view)
    assert re.findall(r"\bview\s+(\w+)\s*:>\s*columnViews\b", view) == ["ID", "Classification", "Rationale"]


def test_the_charter_names_the_classification_package():
    charter = braced_body(strip_comments(FRAMING.read_text(encoding="utf-8")),
                          "part driverAssistanceCharter : IncrementCharter")
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", charter, re.S)
    assert artifacts and re.findall(r'"([^"]+)"', artifacts.group(1))[-1] == PACKAGE, \
        "the charter's expected artifacts must name the package that now holds phase 3 content"


def test_the_slice_carries_no_external_clause_or_claim_wording():
    flat = _flat(_raw())
    for word in ("compliance", "complian", "approv", "certif", "type approval", "owner decided",
                 "owner direction"):
        assert word not in flat, word
    assert not re.search(r"(?i)\b(?:paragraph|clause|annex)\s+\d", flat)
