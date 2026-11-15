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
    "adaptiveCruiseControl": ("0", ()),
    "laneKeepAssist": ("0", ()),
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
    """The counts that INC-DRIVING-001 left stale, restated with VisionPilot."""
    docs = _docs(FEATURE_MODEL)
    assert ("The ten rules and the exclusions of Openpilot, Apollo, AutoE2E and VisionPilot cover all twenty "
            "application-middleware pairs, each exactly once.") in docs
    assert "the eight rules" not in docs and "twelve application-middleware pairs" not in docs
    assert ("the configurations that select it, the Eclipse S-CORE configurations of INC-MW-011, INC-DRIVING-001 "
            "and INC-DRIVING-002, are not admitted") in docs
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
                   "no other pairing of VisionPilot has an adapter"):
        assert phrase in adapter_doc, phrase


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
