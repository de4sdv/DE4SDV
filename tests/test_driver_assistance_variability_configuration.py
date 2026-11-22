"""INC-DRIVING-002 phase 9: VisionPilot in the product line and the configured product of its configuration.

Lexical pins on the product-line side of the phase: the feature visionPilot of the SDV feature model with its
constraints, its pairing with the middlewares and its correspondence; the two shared-asset variants the binding
and the derivation rule target; the feature configuration driverAssistanceVisionPilotSCOREReference; and no
increment element named in a feature-model, configuration or product-model document. The pins read text; the
licensed Syside run validates the model, and the privileged PLE authority run cuts the receipt that decides the
configuration's validity and admission.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORM_STACK = ROOT / "textual-notation-of-model" / "packages" / "architecture" / "sdv_platform_stack.sysml"
PLE = ROOT / "model-based-product-line-engineering"
FEATURE_MODEL = PLE / "feature-models" / "sdv_product_line.sysml"
CONFIGURATION = PLE / "feature-configurations" / "driver_assistance_visionpilot_score_reference.sysml"
EVIDENCE_DIR = PLE / "feature-configurations" / "evidence"
RUNNER = ROOT / "scripts" / "run_ple_authority.py"

CONFIGURATION_NAME = "driverAssistanceVisionPilotSCOREReference"
CONFIGURATION_PACKAGE = "DE4SDV_DriverAssistanceVisionPilotSCOREReferenceConfiguration"
PROJECTION = "DriverAssistanceVisionPilotSCOREReference"
TREE = "DE4SDV_SDVProductLineFeatureModel::SDVProductLineFeatureTree"
STACK = "DE4SDV_SDVPlatformStack::SDVPlatformStack"

#: The selections of the configuration, in its order: feature -> (multiplicity, the members a group redefinition
#: lists). LiDAR and radar are unset, as in DRIVING-CONFIG-001: VisionPilot reads one front camera.
SELECTIONS = {
    "platformStack": ("1", ()),
    "vehicleApplication": ("1", ("visionPilot",)),
    "visionPilot": ("1", ()),
    "middleware": ("1", ("eclipseSCORE",)),
    "eclipseSCORE": ("1", ()),
    "operatingSystem": ("1", ("linux",)),
    "linux": ("1", ()),
    "hypervisor": ("1", ("kvm",)),
    "kvm": ("1", ()),
    "guestOperatingSystem": ("1", ("guestAndroid",)),
    "guestAndroid": ("1", ()),
    "guestMiddleware": ("1", ("guestAndroidSDV",)),
    "guestAndroidSDV": ("1", ()),
    "sensingBoundary": ("1", ()),
    "perceptionSensors": ("1..*", ("camera",)),
    "camera": ("1", ()),
    "capabilities": ("1", ()),
    "pedestrianDetection": ("0", ()),
    "bicycleDetection": ("0", ()),
    "adaptiveCruiseControl": ("1", ()),
    "laneKeepAssist": ("1", ()),
    "hmiDisplay": ("1", ()),
}

_NOT_CODE = re.compile(r"/\*.*?\*/|//[^\n]*|\"(?:[^\"\\]|\\.)*\"", re.S)


def _code(path: Path) -> str:
    """The text of ``path`` with comments and string literals blanked."""
    text = path.read_text(encoding="utf-8")
    return _NOT_CODE.sub(lambda match: '""' if match.group().startswith('"') else " ", text)


def _body(code: str, header: str) -> str:
    """The braced body after the one match of ``header``, which ends with its opening brace."""
    matches = list(re.finditer(header, code))
    assert len(matches) == 1, f"expected one {header!r}, found {len(matches)}"
    start = matches[0].end() - 1
    assert code[start] == "{", f"{header!r} does not end with an opening brace"
    depth = 0
    for end in range(start, len(code)):
        depth += {"{": 1, "}": -1}.get(code[end], 0)
        if depth == 0:
            return code[start : end + 1]
    raise AssertionError(f"{header!r} has an unbalanced body")


def _own(body: str) -> str:
    """A braced body at its own depth, nested bodies left out, whitespace collapsed."""
    kept, depth = [], 0
    for character in body[1:-1]:
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
        elif depth == 0:
            kept.append(character)
    return " ".join("".join(kept).split())


def _docs(path: Path) -> str:
    """The text of ``path`` with the leading asterisks of comment lines dropped and whitespace collapsed."""
    return " ".join(re.sub(r"^\s*\*\s?", "", path.read_text(encoding="utf-8"), flags=re.M).split())


def _feature() -> str:
    return _body(_code(FEATURE_MODEL), r"#feature occurrence <'F-PLATFORM-VEHICLE-APPLICATION-VISIONPILOT'> "
                                       r"visionPilot\[0\.\.1\] :> vehicleApplication default null \{")


# -- the feature model ------------------------------------------------------------------------------------------


def test_the_feature_model_adds_visionpilot_with_the_camera_and_linux_required() -> None:
    """C014 and C015, the next free constraint IDs: the camera required with LiDAR and radar left selectable,
    and Linux on the main side, the camera source's V4L2 interface (the phase 3 record of 2026-11-14)."""
    feature = _feature()
    camera = _own(_body(feature, r"\bassert constraint <'C014'> visionPilotRequiresCamera :> requiresFeatures \{"))
    assert "new FeatureOperand(that, sensingBoundary::camera)" in camera
    linux = _own(_body(feature, r"\bassert constraint <'C015'> visionPilotRequiresLinux :> requiresFeatures \{"))
    assert "new FeatureOperand(that, linux)" in linux
    assert re.findall(r"\bassert constraint (?:<'(C\d+)'> )?(\w+) :> (\w+)", feature) == [
        ("C014", "visionPilotRequiresCamera", "requiresFeatures"),
        ("C015", "visionPilotRequiresLinux", "requiresFeatures"),
        ("", "visionPilotExcludesUnsupportedMiddleware", "xorFeatures"),
    ]
    docs = _docs(FEATURE_MODEL)
    assert "so it requires the camera feature and leaves LiDAR and radar selectable" in docs
    assert "its live camera source uses V4L2, a Linux interface" in docs


def test_the_middleware_pairing_is_one_rule_and_an_exclusion_not_a_requires_constraint() -> None:
    """The AutoE2E form of 2026-11-06 carried over: one derivation rule for the pair with Eclipse S-CORE, which
    phase 8 realized, and an exclusion of the three pairs no rule exists for. A requires constraint on Eclipse
    S-CORE would bind the product line to this increment's bench."""
    code = _code(FEATURE_MODEL)
    exclusion = _own(_body(_feature(), r"\bassert constraint visionPilotExcludesUnsupportedMiddleware :> xorFeatures \{"))
    assert "new FeatureOperand(that, (androidSDV, autosarAdaptive, noMiddleware))" in exclusion
    assert not re.search(r"\bvisionPilotRequires\w*(SCORE|Middleware)\b", code), "the pairing is no requires"
    assert "eclipseSCORE" not in _feature()
    rules = re.findall(r"#DerivationRule dependency (\w+)\s+from ([\w:]+)\s+to\s+([^;]+);", code)
    vision = [(name, client, suppliers) for name, client, suppliers in rules if "visionPilot" in client + suppliers]
    assert len(vision) == 1, vision
    name, client, suppliers = vision[0]
    assert (name, client) == ("visionPilotEclipseSCORERule", f"{STACK}::applicationMiddlewareAdapter::visionPilotToSCORE")
    assert re.findall(r"platformStack::(\w+)", suppliers) == ["visionPilot", "eclipseSCORE"]
    assert "No derivation rule exists for VisionPilot with Android SDV, AUTOSAR Adaptive or no middleware" in _docs(
        FEATURE_MODEL)


def test_the_feature_is_bound_once_and_corresponds_to_the_deferred_driving_stack_variability() -> None:
    code = " ".join(_code(FEATURE_MODEL).split())
    assert (f"#FeatureBinding dependency vehicleApplicationVisionPilotBinding from {STACK}::vehicleApplication::"
            f"visionPilot to SDVProductLineFeatureTree::platformStack::visionPilot;") in code
    assert ("dependency visionPilotCorrespondsToDrivingStackVariability from SDVProductLineFeatureTree::platformStack::"
            "visionPilot to DE4SDV_AEBSProductLineScope::DeferredVariabilitySet::drivingStackVariability;") in code
    bindings = re.findall(r"#FeatureBinding dependency (\w+) from ([\w:]+) to SDVProductLineFeatureTree::platformStack::"
                          r"visionPilot;", code)
    assert bindings == [("vehicleApplicationVisionPilotBinding", f"{STACK}::vehicleApplication::visionPilot")]
    assert len(re.findall(r"\bfrom SDVProductLineFeatureTree::platformStack::visionPilot\b", code)) == 1


def test_the_feature_model_comments_count_the_rules_and_the_display_configurations() -> None:
    """The counts that INC-DRIVING-001 left stale, restated with VisionPilot. Since the scope revision of ADR 0023
    and ADR 0026 the display comment no longer counts the configurations that select the display: every member
    selects it."""
    docs = _docs(FEATURE_MODEL)
    assert ("The ten rules and the exclusions of Openpilot, Apollo, AutoE2E and VisionPilot cover all twenty "
            "application-middleware pairs, each exactly once.") in docs
    assert "the eight rules" not in docs and "twelve application-middleware pairs" not in docs
    assert "Every member configuration selects it" in docs
    assert ("the configurations that select it, the Eclipse S-CORE configurations of INC-MW-011, INC-DRIVING-001 "
            "and INC-DRIVING-002, are not admitted") not in docs
    assert "only the Eclipse S-CORE configuration selects it" not in docs


# -- the shared asset -------------------------------------------------------------------------------------------


def test_the_shared_asset_carries_the_two_variants_the_binding_and_the_rule_target() -> None:
    code = _code(PLATFORM_STACK)
    application = _own(_body(code, r"\bvariation part vehicleApplication : VehicleApplicationLayer\s*\{"))
    assert re.findall(r"\bvariant part (\w+) : (\w+);", application)[-1] == ("visionPilot", "VisionPilotStack")
    adapter = _own(_body(code, r"\bvariation part applicationMiddlewareAdapter : ApplicationMiddlewareAdapterLayer\s*\{"))
    assert "variant part visionPilotToSCORE : VisionPilotToSCOREAdapter;" in adapter
    assert re.search(r"\bpart def VisionPilotStack :> VehicleApplicationLayer\s*\{", code)
    assert re.search(r"\bpart def VisionPilotToSCOREAdapter :> ApplicationMiddlewareAdapterLayer\s*\{", code)
    raw = PLATFORM_STACK.read_text(encoding="utf-8")
    adapter_doc = " ".join(re.sub(r"^\s*\*\s?", "", _body(raw, r"\bpart def VisionPilotToSCOREAdapter :> "
                                                          r"ApplicationMiddlewareAdapterLayer\s*\{"), flags=re.M).split())
    for phrase in ("The DE4SDV S-CORE interface module of the VisionPilot process", "no program of its own",
                   "no other pairing of VisionPilot has an adapter",
                   "On S-CORE Communication (mw::com), the vehicle interface publishes the driving command and "
                   "subscribes to the candidate record, and the warning request publisher publishes the warning "
                   "request.",
                   "The camera images and the speed of the ego vehicle come from the simulator's client library, not "
                   "from mw::com."):
        assert phrase in adapter_doc, phrase
    # Phase 8's camera interface takes its images from the simulator's client (SCORECameraInterface): the adapter
    # names the camera once, in the sentence that says so.
    assert adapter_doc.count("camera") == 1, adapter_doc


# -- the non-claims of the phase ----------------------------------------------------------------------------------

#: Affirmative forms of a claim the phase does not make: an approval, or a configuration, product or member admitted.
CLAIM_PATTERNS = (
    r"\bapprov",
    r"\b(?:is|are|was|were|be|been|and)\s+admitted\b(?!\s+to\s+no\b)",
    r"\badmitted\s+(?:member|configuration|product)\b",
)


def _shared_asset_docs() -> str:
    """The two VisionPilot shared assets of the platform stack, VisionPilotStack and VisionPilotToSCOREAdapter, with
    the leading asterisks of their comment lines dropped and whitespace collapsed."""
    raw = PLATFORM_STACK.read_text(encoding="utf-8")
    bodies = (_body(raw, r"\bpart def VisionPilotStack :> VehicleApplicationLayer\s*\{"),
              _body(raw, r"\bpart def VisionPilotToSCOREAdapter :> ApplicationMiddlewareAdapterLayer\s*\{"))
    return " ".join(re.sub(r"^\s*\*\s?", "", "\n".join(bodies), flags=re.M).split())


def _guide_phase_9() -> str:
    """The phase 9 section of the guide, whitespace collapsed."""
    text = GUIDE.read_text(encoding="utf-8")
    start = text.index("## Variability and configuration (Phase 9)")
    return " ".join(text[start : text.index("\n## ", start)].split())


def test_the_phase_9_texts_state_their_non_claims() -> None:
    """The configuration is valid and admitted to no member, the configured product is configuration evidence only,
    and the VisionPilot stack is a candidate realization that assumes no conformance. An edit that drops or turns
    one of these statements fails here."""
    slice_docs, assets = _docs(SLICE), _shared_asset_docs()
    assert "The configuration is valid and not admitted." in slice_docs
    assert ("Configuration evidence only. This usage proves no candidate, adapter, gateway or presentation behavior "
            "and no requirement satisfaction.") in slice_docs
    assert "Valid and not admitted: VisionPilot" in _docs(CONFIGURATION)
    assert ("Status: candidate realization, admitted to no member; the driver-assistance increment's phase 8 places "
            "it, phase 10 judges it.") in assets
    assert "No conformance to DE4SDV boundary contracts is assumed without evidence." in assets


def test_no_phase_9_text_claims_an_approval_or_an_admission() -> None:
    """The texts are read with their comments, so a claim placed in a comment fails too."""
    texts = {"phase 9 package": _docs(SLICE), "configuration": _docs(CONFIGURATION),
             "VisionPilot shared assets": _shared_asset_docs(), "guide, phase 9 section": _guide_phase_9()}
    for name, prose in texts.items():
        for pattern in CLAIM_PATTERNS:
            match = re.search(pattern, prose, re.IGNORECASE)
            assert match is None, (name, match.group(0) if match else None)

# -- the feature configuration ------------------------------------------------------------------------------------


def _selections() -> dict[str, tuple[str, tuple[str, ...]]]:
    body = _body(_code(CONFIGURATION), rf"#featureConfiguration occurrence {CONFIGURATION_NAME} : "
                                       r"SDVProductLineFeatureTree :> featureConfigurations\s*\{")
    found = {}
    for name, multiplicity, operands in re.findall(
            r"#feature occurrence :>> (\w+)\[([^\]]+)\](?: = \(([^)]*)\))?\s*[;{]", body):
        assert name not in found, name
        found[name] = (multiplicity, tuple(o.strip() for o in operands.split(",")) if operands else ())
    return found


def test_the_configuration_selects_visionpilot_on_eclipse_score_with_an_aaos_sdv_guest_and_the_camera_alone() -> None:
    assert _selections() == SELECTIONS
    raw = CONFIGURATION.read_text(encoding="utf-8")
    assert re.search(rf"^package {CONFIGURATION_PACKAGE}\s*\{{", raw, re.M)
    assert re.findall(r'partDefinitionName = "(\w+)";', raw) == [PROJECTION]
    assert f"private import {TREE};" in raw
    docs = _docs(CONFIGURATION)
    assert "C014 requires the camera and leaves the others selectable" in docs
    assert "Vehicle-target AEBS only (no pedestrian or bicycle detection)." in docs
    assert ("It selects adaptive cruise control and lane-keep assist: VisionPilot runs a speed-following and a "
            "lane-keeping function, which no case of INC-DRIVING-002 judges.") in docs


def test_the_authority_runner_lists_the_configuration_beside_the_driving_one() -> None:
    from scripts import run_ple_authority as runner

    path = CONFIGURATION.relative_to(ROOT).as_posix()
    assert path in runner.CONFIGURATIONS
    previous = "model-based-product-line-engineering/feature-configurations/closed_loop_driving_autoe2e_score_reference.sysml"
    assert runner.CONFIGURATIONS.index(path) == runner.CONFIGURATIONS.index(previous) + 1


def test_the_configuration_has_no_evidence_record() -> None:
    """The evidence records are the retired Bills-of-Features' evidence blocks (ADR 0022, S7), as the test of
    DRIVING-CONFIG-001 says: the evidence of this configured product is phase 10 model content."""
    assert not [path.name for path in EVIDENCE_DIR.glob("*.yaml") if "visionpilot" in path.name.lower()]


def test_no_feature_model_configuration_or_product_model_document_names_an_increment_element() -> None:
    """Rule 5's dependency form: the links of the requirements and of the system of interest are declared with
    them, outside the feature-model and configuration documents, whose every dependency the evaluator reads."""
    documents = [*sorted((PLE / "feature-models").rglob("*.sysml")),
                 *sorted((PLE / "feature-configurations").rglob("*.sysml")),
                 *sorted((PLE / "product-models").glob("*.sysml")), PLATFORM_STACK]
    assert len(documents) >= 30, "the population of the check must not be vacuous"
    for path in documents:
        text = path.read_text(encoding="utf-8")
        for name in ("DE4SDV_DriverAssistanceNeedsRequirements", "DE4SDV_DriverAssistanceFraming",
                     "candidateDriverAssistanceSystem", "DE4SDV_DriverAssistanceVariabilityConfiguration"):
            assert name not in text, (path.name, name)
        assert not re.search(r"\bREQ-DRIVING-0(?:3[6-9]|4[0-4])\b", text), path.name


# == the phase 9 package: the configured product DRIVING-CONFIG-002 ==============================================

import hashlib  # noqa: E402
import json  # noqa: E402

DRIVING = ROOT / "textual-notation-of-model" / "packages" / "features" / "driving"
SLICE = DRIVING / "driver_assistance_variability_configuration.sysml"
PHYSICAL = DRIVING / "driver_assistance_physical_software_realization.sysml"
DRIVING_001_PHYSICAL = DRIVING / "closed_loop_driving_physical_software_realization.sysml"
FRAMING = DRIVING / "driver_assistance_framing.sysml"
NEEDS = DRIVING / "driver_assistance_needs_requirements.sysml"
VIEWS_INDEX = DRIVING / "VIEWS.md"
DRIVING_001_SLICE = DRIVING / "closed_loop_driving_variability_configuration.sysml"
MW_SLICE = ROOT / "textual-notation-of-model" / "packages" / "features" / "middleware" / (
    "middleware_score_variability_configuration.sysml")
RECEIPT = PLE / "feature-models" / "receipts" / "sdv_product_line.receipt.json"
PRODUCT_MODEL = PLE / "product-models" / "driver_assistance_visionpilot_score_reference.sysml"
GUIDE = ROOT / "docs" / "guides" / "driver-assistance-increment.md"

PACKAGE = "DE4SDV_DriverAssistanceVariabilityConfiguration"
PRODUCT_DEF = "DriverAssistanceVisionPilotSCOREConfiguredProduct"
IDENTITY = "DRIVING-CONFIG-002"
FEATURE = "DE4SDV_SDVProductLineFeatureModel::SDVProductLineFeatureTree::platformStack::"
#: Rule 5, dependency form, owned with their clients: the system of interest brings VisionPilot; each requirement
#: whose statement or terms name the Eclipse S-CORE path adds the middleware (link name -> (client, feature)).
SUBJECT_LINKS = {"assistanceSystemOnVisionPilotFeature": ("candidateDriverAssistanceSystem", "visionPilot")}
REQUIREMENT_LINKS = {
    "reqDrivingCommandOverSCOREOnEclipseSCORE": ("reqDrivingCommandOverSCORE", "eclipseSCORE"),
    "reqDetectableDrivingCommandOnEclipseSCORE": ("reqDetectableDrivingCommand", "eclipseSCORE"),
    "reqWarningRequestBeforeEmergencyBrakingOnEclipseSCORE": ("reqWarningRequestBeforeEmergencyBraking", "eclipseSCORE"),
    "reqWarningRequestOverSCOREOnEclipseSCORE": ("reqWarningRequestOverSCORE", "eclipseSCORE"),
}
#: The requirements whose term warning request names the AAOS SDV, which the guest-middleware group can leave out.
GUEST_LINKS = {
    "reqWithholdWarningRequestOnGuestAndroidSDV": ("reqWithholdWarningRequest", "guestAndroidSDV"),
    "reqWarningRequestBeforeEmergencyBrakingOnGuestAndroidSDV": ("reqWarningRequestBeforeEmergencyBraking",
                                                                "guestAndroidSDV"),
    "reqWarningRequestOverSCOREOnGuestAndroidSDV": ("reqWarningRequestOverSCORE", "guestAndroidSDV"),
}

#: projection selection -> (variation, variant, the definition the variant is typed by)
LAYERS = {
    "vehicleApplication": ("vehicleApplication", "visionPilot", "VisionPilotStack"),
    "middleware": ("middleware", "eclipseSCORE", "EclipseSCORE"),
    "osPlatform": ("osPlatform", "linux", "LinuxPlatform"),
    "hypervisor": ("hypervisor", "kvm", "KVMHypervisor"),
    "guestOSPlatform": ("guestOSPlatform", "android", "AndroidHLOS"),
    "guestMiddleware": ("guestMiddleware", "androidSDV", "AndroidSDVMiddleware"),
    "applicationMiddlewareAdapter": ("applicationMiddlewareAdapter", "visionPilotToSCORE", "VisionPilotToSCOREAdapter"),
}
#: phase-8 context part -> (the file that defines it, the composed layer part, the projection selection that types it)
CONTEXT_LAYERS = [
    ("DriverAssistanceSCOREHost", PHYSICAL, "os", "osPlatform"),
    ("DriverAssistanceSCOREHost", PHYSICAL, "scoreServices", "middleware"),
    ("DriverAssistanceSimulatorHost", PHYSICAL, "os", "osPlatform"),
    ("AAOSGuestHost", DRIVING_001_PHYSICAL, "os", "osPlatform"),
    ("AAOSGuestHost", DRIVING_001_PHYSICAL, "hypervisor", "hypervisor"),
    ("DriverAssistanceSDVCoreGuest", PHYSICAL, "os", "guestOSPlatform"),
    ("DriverAssistanceSDVCoreGuest", PHYSICAL, "sdvMiddleware", "guestMiddleware"),
    ("DriverAssistanceIVIGuest", PHYSICAL, "os", "guestOSPlatform"),
]
_TYPED_BY = r"\b(?:ref\s+)?part\s+\w+\s*(?:\[[^\]]*\]\s*)?:(?![:>])[^;{{]*\b{definition}\b"


def _product_body() -> str:
    return _body(_code(SLICE), rf"\bpart\s+def\s+{PRODUCT_DEF}\s*:>\s*ProductLineConfiguredProduct\s*\{{")


def _receipt_record() -> dict:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    (model,) = [m for m in receipt["evaluation"]["feature_models"] if m["feature_model"] == "SDVProductLineFeatureModel"]
    (record,) = [c for c in model["configurations"] if c["configuration"] == CONFIGURATION_NAME]
    return record


def test_the_configured_product_pairs_the_projection_with_the_assistance_realization() -> None:
    """The shape of INC-DRIVING-001 and INC-MW-011: the projection and the phase-8 system of interest, no variant
    chosen here."""
    own = _own(_product_body())
    assert re.findall(r"\b(?:ref\s+)?part\s+(\w+)\s*:", own) == ["platformStack", "assistanceSoftware"]
    assert f"part platformStack : {PROJECTION};" in own
    assert "part assistanceSoftware : DriverAssistanceSoftwareRealization;" in own
    assert ":>>" not in _product_body(), "the product redefines no feature of its parts"
    assert "ref part" not in own, "the product composes both of its parts"
    assert re.search(r"\bprivate import DE4SDV_DriverAssistancePhysicalSoftwareRealization::"
                     r"DriverAssistanceSoftwareRealization;", _code(SLICE))


def test_the_configured_product_binds_nothing_because_the_realization_composes_no_platform_layer() -> None:
    """Phase 8 kept the S-CORE path outside the boundary of phase 0: the services sit on the S-CORE host beside the
    realization, so no part of the realization is the selected middleware, unlike INC-DRIVING-001. The adapter is
    three modules of the candidate's process, no program of its own: a dependency, not a binding."""
    code = _code(PHYSICAL)
    realization = _own(_body(code, r"\bpart\s+def\s+DriverAssistanceSoftwareRealization\s*:>\s*DriverAssistanceSystem\s*\{"))
    assert re.findall(r"\bpart\s+(\w+)\s*:\s*(\w+);", realization) == [
        ("identityRecording", "CandidateIdentityRecordingApplication"), ("visionPilotApplication", "VisionPilotSCOREApplication")]
    host = _own(_body(code, r"\bpart\s+def\s+DriverAssistanceSCOREHost\b[^{;]*\{"))
    assert re.search(r"(?<!ref )\bpart scoreServices : EclipseSCORE\b", host), "the host composes the S-CORE services"
    assert not re.search(r"\bbind(?:ing)?\b", _product_body()), "no binding in the configured product"
    docs = _docs(SLICE)
    for phrase in ("No binding.", "the platform stack is the only composer of it in this product",
                   "no part of the realization is the adapter either"):
        assert phrase in docs, phrase


def test_the_slice_types_no_part_by_a_platform_layer_definition() -> None:
    """The projection and the realization carry the layer types; the slice restates none of them."""
    code = _code(SLICE)
    for definition in [*(definition for _variation, _variant, definition in LAYERS.values()), "SDVPlatformStack"]:
        assert not re.search(_TYPED_BY.format(definition=definition), code), f"the slice types a part by {definition}"


def test_the_configured_product_is_no_member_product() -> None:
    """Valid, not admitted: the definition specializes the kernel's configured product and nothing else."""
    code = _code(SLICE)
    assert re.findall(r":>(?!>)\s*([\w:]+)", code) == ["ProductLineConfiguredProduct"]
    assert not re.search(r"\bspecializes\b", code)
    assert "ProductLineMemberProduct" not in code
    assert re.findall(r"\bpart <'([A-Z-]+\d+)'> (\w+) : (\w+)\s*\{", code) == [(IDENTITY, "configuredProduct", PRODUCT_DEF)]


def test_the_configured_product_traces_the_realization_the_adapter_the_application_and_the_admission_gap() -> None:
    code = " ".join(_code(SLICE).split())
    application = "configuredProduct::assistanceSoftware::visionPilotApplication"
    for statement in (
            "dependency configuredAssistanceSoftwareTrace from configuredProduct::assistanceSoftware to "
            "DE4SDV_DriverAssistancePhysicalSoftwareRealization::driverAssistancePhysicalSystem::scoreHost::"
            "assistanceSoftware;",
            f"dependency derivedAdapterIsTheInterfaceModule from {application}::cameraInterface, "
            f"{application}::vehicleInterface, {application}::warningRequestPublisher to "
            "configuredProduct::platformStack::applicationMiddlewareAdapter;",
            f"dependency candidateProcessRunsTheSelectedApplication from {application}::perceptionAndFusion, "
            f"{application}::safetyGuardianPlanner to configuredProduct::platformStack::vehicleApplication;",
            "dependency configuredProductAdmissionGap from configuredProduct to "
            "DE4SDV_DriverAssistanceFraming::gapCandidateAdmission;"):
        assert statement in code, statement
    assert len(re.findall(r"\bdependency\b", code)) == 4, "the slice declares no rule-5 link: they live with their clients"
    modules = _own(_body(_code(PHYSICAL), r"\bpart\s+def\s+VisionPilotSCOREApplication\s*\{"))
    assert re.findall(r"\bpart\s+(\w+)\s*:", modules) == ["cameraInterface", "perceptionAndFusion", "safetyGuardianPlanner",
                                                         "vehicleInterface", "warningRequestPublisher"]


# -- the receipt and the model's reading of admission ------------------------------------------------------------


def test_driving_config_002_is_bound_to_the_exact_receipt() -> None:
    """One receipt, four holders of its digest: DRIVING-CONFIG-002, DRIVING-CONFIG-001, MW-CONFIG-002 and the
    projection header. Receipt-bound: the licensed PLE authority run cuts the receipt and the configurator writes
    the projection, and each digest is rebound to it. The slice states what counts as a change of the
    configuration's own receipt record (decision of 2026-11-17)."""
    digest = hashlib.sha256(RECEIPT.read_bytes()).hexdigest()
    pattern = r'attribute receiptSha256 : ScalarValues::String = "([0-9a-f]{64})";'
    assert re.findall(pattern, SLICE.read_text(encoding="utf-8")) == [digest], "DRIVING-CONFIG-002 binds another receipt"
    for holder in (DRIVING_001_SLICE, MW_SLICE):
        assert re.findall(pattern, holder.read_text(encoding="utf-8")) == [digest], holder.name
    (header,) = re.findall(r"\* Receipt SHA-256: ([0-9a-f]{64})", PRODUCT_MODEL.read_text(encoding="utf-8"))
    assert header == digest, "the committed projection was generated from another receipt"
    assert ("The pull request that rebinds it states whether the configuration's own receipt record changed. By "
            "the decision of 2026-11-17, the record has not changed when its only difference is added states omitted "
            "for features that it does not select, and every other entry is the same: validity, reasons, derived "
            "variants with their variant ids, admission, the selected features, projection name, source, description "
            "and element id."
            ) in _docs(SLICE), "DRIVING-CONFIG-002 no longer states what counts as a change of its own receipt record"


def test_the_receipt_records_what_the_configured_product_states() -> None:
    """Valid, the adapter derived for the pair with Eclipse S-CORE, the alternative S-CORE Integrated realized, not
    admitted for the documented reasons. Receipt-bound: the record exists once the licensed PLE authority run has
    cut the receipt."""
    record = _receipt_record()
    assert record["projection_name"] == PROJECTION
    assert record["valid"] is True and record["admission"]["admitted"] is False
    assert {d["variation"]: d["variant"] for d in record["derived_variants"]} == {
        selection: variant for selection, (_variation, variant, _definition) in LAYERS.items()}
    (rule,) = [d for d in record["derived_variants"] if "rule" in d]
    assert (rule["variation"], rule["variant"], rule["rule"]) == (
        "applicationMiddlewareAdapter", "visionPilotToSCORE", "visionPilotEclipseSCORERule")
    selected = set(record["selected"])
    assert {"platformStack.visionPilot", "platformStack.eclipseSCORE", "platformStack.linux", "platformStack.kvm",
            "platformStack.guestAndroid", "platformStack.guestAndroidSDV", "sensingBoundary.camera",
            "capabilities.hmiDisplay", "capabilities.adaptiveCruiseControl", "capabilities.laneKeepAssist"} <= selected
    assert not {"sensingBoundary.lidar", "sensingBoundary.radar", "platformStack.autoware",
                "platformStack.androidSDV"} & selected
    assert record["admission"]["alternative"] == "scoreIntegrated"
    assert record["admission"]["reasons"] == [
        "selects content the governed scope does not admit: platformStack.visionPilot: deferred drivingStackVariability"
        " | capabilities.adaptiveCruiseControl: not in the governed scope"
        " | capabilities.laneKeepAssist: not in the governed scope",
        "does not represent the common content: autowareApplication (missing platformStack.autoware); "
        "currentSensingBaseline (missing sensingBoundary.lidar)"]


def test_the_model_reading_of_admission_gives_the_reasons_the_slice_states() -> None:
    """Before the receipt: the stated reading of the correspondences (test_ple_authority_model.admission) blocks the
    configuration for the reasons the package doc names, and realizes the S-CORE-integrated alternative."""
    from tests import test_ple_authority_model as ple

    family, selected = ple._configuration_selection(CONFIGURATION.relative_to(ROOT).as_posix())
    correspondences, family_elements = ple._correspondences(family)
    alternative, blocking = ple.admission(ple._tree(family)[1], correspondences, family_elements, selected)
    assert alternative == "vehiclePlatformIntegrationMode::scoreIntegrated"
    assert sorted(blocking) == sorted((
        "visionPilot: deferred", "adaptiveCruiseControl: not in the governed scope",
        "laneKeepAssist: not in the governed scope",
        "InitialCommonCoreEngineeringContent::autowareApplication is not represented: autoware is not selected",
        "InitialCommonCoreEngineeringContent::currentSensingBaseline is not represented: lidar is not selected"))
    docs = _docs(SLICE)
    for statement in ("It realizes the alternative S-CORE Integrated with its derived realizations.",
                      "the correspondences gives two reasons", "the driving stack is deferred variability",
                      "adaptive cruise control and lane-keep assist have no element in the governed scope",
                      "Adaptive cruise control and lane-keep assist have no shared asset either",
                      "does not represent the common content: no Autoware, no LiDAR"):
        assert statement in docs, statement
    for stale in ("Eclipse S-CORE is reference-only", "the HMI display, adaptive cruise control",
                  "realizes the AAOS-integrated alternative without its middleware androidSDV"):
        assert stale not in docs, stale


# -- the links of rule 5 -------------------------------------------------------------------------------------------


def _feature_links(path: Path) -> dict[str, tuple[str, str]]:
    code = _code(path)
    links = {name: (client, feature) for name, client, feature in re.findall(
        rf"\bdependency\s+(\w+)\s+from\s+(\w+)\s+to\s+{re.escape(FEATURE)}(\w+)\s*;", code)}
    assert len(links) == code.count("DE4SDV_SDVProductLineFeatureModel"), f"a feature reference of another form in {path.name}"
    return links


def test_the_system_of_interest_links_to_the_feature_visionpilot_in_the_framing() -> None:
    """What phase 5 promised: phase 9 links the system of interest to the feature it enters a member product with,
    in rule 5's dependency form, next to the system of interest."""
    assert _feature_links(FRAMING) == SUBJECT_LINKS
    assert "systemOfInterest = candidateDriverAssistanceSystem;" in " ".join(_code(FRAMING).split())


def test_each_requirement_that_names_the_score_path_links_to_eclipse_score() -> None:
    """Through the subject first: the subject brings VisionPilot, so a requirement links only what it adds. 038 and
    043 name the Eclipse S-CORE path, 039 the path on which the actuation detects a failure, and 042 its boundary,
    the hand-over to the S-CORE path. No requirement repeats its subject's link."""
    links = _feature_links(NEEDS)
    assert {name: link for name, link in links.items() if link[1] == "eclipseSCORE"} == REQUIREMENT_LINKS
    assert links == {**REQUIREMENT_LINKS, **GUEST_LINKS}
    raw = NEEDS.read_text(encoding="utf-8")
    for client, identifier in (("reqDrivingCommandOverSCORE", "038"), ("reqDetectableDrivingCommand", "039"),
                               ("reqWarningRequestBeforeEmergencyBraking", "042"), ("reqWarningRequestOverSCORE", "043")):
        assert re.search(rf"\brequirement <'REQ-DRIVING-{identifier}'> {client} :", raw), client
    statements = dict(re.findall(r"requirement <'(REQ-DRIVING-\d+)'> \w+ : \w+ \{\s*subject [^;]+;\s*require constraint "
                                 r"statement \{ language \"English\" /\* (.*?) \*/ \}", raw, re.S))
    assert len(statements) == 9
    assert sorted(i for i, s in statements.items() if "Eclipse S-CORE path" in s) == [
        "REQ-DRIVING-038", "REQ-DRIVING-039", "REQ-DRIVING-043"]
    assert "at its boundary" in statements["REQ-DRIVING-042"]
    assert ("Boundary: the interface at which the outputs of the driver-assistance system leave it for the Eclipse "
            "S-CORE path.") in _docs(NEEDS)


def test_no_link_starts_from_the_realization_or_sits_in_a_feature_model_document() -> None:
    """A link from the phase-8 realization is no counted kind (it left INC-DRIVING-001's requirements reading as core);
    the links live with the requirements and the system of interest, never in the phase 9 package."""
    for path in sorted(DRIVING.glob("driver_assistance_*.sysml")):
        if path in (FRAMING, NEEDS):
            continue
        assert "DE4SDV_SDVProductLineFeatureModel" not in _code(path), path.name
    assert not re.search(r"\bdependency\s+\w+\s+from\s+DriverAssistanceSoftwareRealization\b", _code(SLICE))


def test_no_driver_assistance_requirement_depends_on_the_hmi_display() -> None:
    """No requirement statement names a display, so no OnHMIDisplay dependency exists, and the slice says why."""
    raw = NEEDS.read_text(encoding="utf-8")
    assert "hmiDisplay" not in _code(NEEDS)
    statements = re.findall(r"requirement <'REQ-DRIVING-\d+'> \w+ : \w+ \{\s*subject [^;]+;\s*require constraint "
                            r"statement \{ language \"English\" /\* (.*?) \*/ \}", raw, re.S)
    assert len(statements) == 9 and not [s for s in statements if re.search(r"\b(display|screen)\b", s, re.I)]
    assert "this package adds no requirement dependency on hmiDisplay" in _docs(SLICE)


# -- the physical context, the views, the charter and the guide ----------------------------------------------------


def test_the_context_layers_of_phase_8_are_typed_by_the_selected_variants() -> None:
    """The product does not compose the physical context; this pin keeps its host and guest layers the definitions
    of the variants the configuration selects, so the bench of phase 8 is the configured product's."""
    stack = _code(PLATFORM_STACK)
    for _selection, (variation, variant, definition) in LAYERS.items():
        variants = _body(stack, rf"\bvariation part {variation} : \w+\s*\{{")
        assert re.search(rf"\bvariant (?:ref )?part {variant} : {definition}\b", variants), variant
    for context_def, path, layer, selection in CONTEXT_LAYERS:
        definition = LAYERS[selection][2]
        body = _own(_body(_code(path), rf"\bpart def {context_def}\b[^{{;]*\{{"))
        assert re.search(rf"(?<!ref )\bpart {layer} : {definition}\b", body), f"{context_def}.{layer} is not a {definition}"
    system = _own(_body(_code(PHYSICAL), r"\bpart def DriverAssistancePhysicalSystem\b[^{;]*\{"))
    assert "part guestHost : AAOSGuestHost;" in system


def test_the_projection_redefines_the_selected_layers() -> None:
    """Receipt-bound: the configurator writes the projection from the receipt of the licensed run."""
    projection = _code(PRODUCT_MODEL)
    assert re.search(rf"\bpart def {PROJECTION} :> SDVPlatformStack\s*\{{", projection)
    for selection, (variation, variant, _definition) in LAYERS.items():
        assert re.search(rf"\bpart :>> {selection} = {variation}::{variant};", projection), selection


def test_the_two_phase_9_views_frame_the_two_concerns_and_publish_the_configured_product() -> None:
    code = _code(SLICE)
    for view, viewpoint, concern in [
        ("driverAssistanceProductLineConfigurationView", "ProductLineConfigurationViewpoint",
         "assistanceProductLineConfigurationConcern"),
        ("driverAssistanceProductModelAssemblyView", "ProductModelAssemblyViewpoint", "assistanceProductModelAssemblyConcern"),
    ]:
        body = _body(code, rf"\bview {view}\s*\{{")
        assert re.search(rf"\bviewpoint \w+ : {viewpoint}\s*\{{\s*frame {concern};", " ".join(body.split()))
        assert "render asTreeDiagram;" in body and "attribute maxCompartmentEntries = 0;" in body
        assert "attribute showAnnotationRows = false;" in body
        assert re.search(rf"\bconcern {concern} : {viewpoint.replace('Viewpoint', 'Concern')}\s*\{{", code)
    configuration = _own(_body(code, r"\bview driverAssistanceProductLineConfigurationView\s*\{"))
    aliases = ["selectedVehicleApplication", "selectedMiddleware", "selectedOperatingSystem", "selectedHypervisor",
               "selectedGuestOperatingSystem", "selectedGuestMiddleware", "selectedApplicationMiddlewareAdapter"]
    assert re.findall(r"\bexpose (\w+);", configuration) == [PROJECTION, *aliases]
    declared = dict(re.findall(rf"\balias (\w+)\s+for {PROJECTION}::(\w+);", " ".join(code.split())))
    assert declared == dict(zip(aliases, LAYERS)), declared
    assembly = _own(_body(code, r"\bview driverAssistanceProductModelAssemblyView\s*\{"))
    assert re.findall(r"\bexpose ([\w:]+);", assembly) == [
        PRODUCT_DEF, f"{PRODUCT_DEF}::platformStack", f"{PRODUCT_DEF}::assistanceSoftware", "configuredProduct"], (
        "phase 11's applicablePhaseContentPublished reads the configured-product usage")
    assert "filter not (@ SysML::AllocationUsage);" in assembly


def test_the_views_index_lists_the_two_phase_9_views() -> None:
    """VIEWS.md comes from scripts/generate_view_index.py; the renders come from the licensed Syside run."""
    index = VIEWS_INDEX.read_text(encoding="utf-8")
    section = index.split("## `driver_assistance_variability_configuration.sysml`", 1)[1].split("\n## ", 1)[0]
    assert re.findall(r"^### `(\w+)`", section, re.M) == ["driverAssistanceProductLineConfigurationView",
                                                         "driverAssistanceProductModelAssemblyView"]


def test_the_charter_names_the_phase_9_package_after_phase_8() -> None:
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", FRAMING.read_text(encoding="utf-8"), re.S)
    assert artifacts and re.findall(r'"([^"]+)"', artifacts.group(1))[-3:] == [
        "DE4SDV_DriverAssistancePhysicalSoftwareRealization", PACKAGE,
        "DE4SDV_DriverAssistanceVerificationEvidence"], "phase 10 follows phase 9 in the charter"
    assert re.findall(r"(?m)^package\s+(\w+)\s*\{", _code(SLICE)) == [PACKAGE], "one global package per file"


def test_the_guide_describes_phase_9_and_its_decisions() -> None:
    guide = GUIDE.read_text(encoding="utf-8")
    order = [guide.index(heading) for heading in ("## Physical and software realization (Phase 8)",
                                                  "## Variability and configuration (Phase 9)",
                                                  "## What the framing already records as open")]
    assert order == sorted(order)
    section = " ".join(guide.split("## Variability and configuration (Phase 9)", 1)[1].split("\n## ", 1)[0].split())
    for text in (IDENTITY, "`visionPilot`", "C014", "C015", "`androidSDV`", "`autosarAdaptive`", "`noMiddleware`",
                 "`visionPilotToSCORE`", "valid, and the governed scope does not admit it", "`hmiDisplay`",
                 "receipt", "2026-11-06", "It selects adaptive cruise control and lane-keep assist",
                 "it realizes the S-CORE-integrated alternative, but the driving stack is deferred variability",
                 "adaptive cruise control and lane-keep assist are outside the governed scope",
                 "2026-11-14", "`assistanceSystemOnVisionPilotFeature`", "`eclipseSCORE`", "No check reads them",
                 "(../../textual-notation-of-model/packages/features/driving/"
                 "driver_assistance_variability_configuration.sysml)",
                 "tests/test_driver_assistance_variability_configuration.py"):
        assert text in section, text
    for count in ("215,040", "17,680", "832"):
        assert count not in section, "the guide quotes no count the receipt has not produced"
    for stale in ("Eclipse S-CORE is reference-only", "the display, adaptive cruise control",
                  "the AAOS-integrated alternative without its middleware"):
        assert stale not in " ".join(section.split()), stale
    check = " ".join(guide.split("## Check the framing change", 1)[1].split())
    assert "tests/test_driver_assistance_variability_configuration.py" in check


def test_each_requirement_that_names_the_warning_request_links_to_the_aaos_sdv_guest_middleware() -> None:
    """The term warning request is the output by which the system asks the AAOS SDV for the collision warning, and
    the guest-middleware group has a none alternative: REQ-DRIVING-040, -042 and -043 apply only where the AAOS SDV
    guest middleware is selected. 042 and 043 then carry two links of their own, which the dependency form reads as
    both."""
    links = _feature_links(NEEDS)
    assert {name: link for name, link in links.items() if link[1] == "guestAndroidSDV"} == GUEST_LINKS
    raw = NEEDS.read_text(encoding="utf-8")
    statements = dict(re.findall(r"requirement <'(REQ-DRIVING-\d+)'> \w+ : \w+ \{\s*subject [^;]+;\s*require constraint "
                                 r"statement \{ language \"English\" /\* (.*?) \*/ \}", raw, re.S))
    assert sorted(i for i, s in statements.items() if "warning request" in s) == [
        "REQ-DRIVING-040", "REQ-DRIVING-042", "REQ-DRIVING-043"]
    assert ("Warning request: the output by which the driver-assistance system asks the AAOS SDV to give the driver "
            "the collision warning.") in _docs(NEEDS)
    section = " ".join(GUIDE.read_text(encoding="utf-8").split("## Variability and configuration (Phase 9)", 1)[1]
                       .split("\n## ", 1)[0].split())
    assert "`guestAndroidSDV`" in section
