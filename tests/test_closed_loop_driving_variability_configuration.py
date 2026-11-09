"""INC-DRIVING-001 phase 9: the configured product of the closed-loop driving reference configuration.

Lexical pins on ``closed_loop_driving_variability_configuration.sysml`` and on what it pairs: the generated
platform-stack projection, the phase-8 realization, the receipt the identity DRIVING-CONFIG-001 binds, the
feature the system of interest links to, and the context layers the projection's selections type. The pins
read text; the licensed Syside run validates the model, and the privileged PLE authority run cuts the receipt.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DRIVING = ROOT / "textual-notation-of-model" / "packages" / "features" / "driving"
SLICE = DRIVING / "closed_loop_driving_variability_configuration.sysml"
PHYSICAL = DRIVING / "closed_loop_driving_physical_software_realization.sysml"
FRAMING = DRIVING / "closed_loop_driving_framing.sysml"
REQUIREMENTS = DRIVING / "closed_loop_driving_needs_requirements.sysml"
MW_SLICE = ROOT / "textual-notation-of-model" / "packages" / "features" / "middleware" / (
    "middleware_score_variability_configuration.sysml")
PLATFORM_STACK = ROOT / "textual-notation-of-model" / "packages" / "architecture" / "sdv_platform_stack.sysml"
PLE = ROOT / "model-based-product-line-engineering"
FEATURE_MODEL = PLE / "feature-models" / "sdv_product_line.sysml"
RECEIPT = PLE / "feature-models" / "receipts" / "sdv_product_line.receipt.json"
CONFIGURATION = PLE / "feature-configurations" / "closed_loop_driving_autoe2e_score_reference.sysml"
EVIDENCE = PLE / "feature-configurations" / "evidence" / "closed-loop-driving-autoe2e-score-reference.yaml"
PRODUCT_MODEL = PLE / "product-models" / "closed_loop_driving_autoe2e_score_reference.sysml"
GUIDE = ROOT / "docs" / "guides" / "closed-loop-driving-increment.md"

PACKAGE = "DE4SDV_ClosedLoopDrivingVariabilityConfiguration"
PRODUCT_DEF = "ClosedLoopDrivingAutoE2ESCOREConfiguredProduct"
PROJECTION = "ClosedLoopDrivingAutoE2ESCOREReference"
CONFIGURATION_NAME = "closedLoopDrivingAutoE2ESCOREReference"
IDENTITY = "DRIVING-CONFIG-001"

#: projection selection -> (variation, variant, the definition the variant is typed by)
SELECTIONS = {
    "vehicleApplication": ("vehicleApplication", "autoE2E", "AutoE2EStack"),
    "middleware": ("middleware", "eclipseSCORE", "EclipseSCORE"),
    "osPlatform": ("osPlatform", "linux", "LinuxPlatform"),
    "hypervisor": ("hypervisor", "kvm", "KVMHypervisor"),
    "guestOSPlatform": ("guestOSPlatform", "android", "AndroidHLOS"),
    "guestMiddleware": ("guestMiddleware", "androidSDV", "AndroidSDVMiddleware"),
    "applicationMiddlewareAdapter": ("applicationMiddlewareAdapter", "autoE2EToSCORE", "AutoE2EToSCOREAdapter"),
}

#: phase-8 context part -> (its definition, the composed layer part, the projection selection that types it)
#: three hosts since the amendment of 2026-11-09: the hypervisor is the guest host's, each host has its Linux
CONTEXT_LAYERS = [
    ("ClosedLoopDrivingLinuxHost", "os", "osPlatform"),
    ("ClosedLoopDrivingSimulatorHost", "os", "osPlatform"),
    ("AAOSGuestHost", "os", "osPlatform"),
    ("AAOSGuestHost", "hypervisor", "hypervisor"),
    ("AAOSSDVCoreGuest", "os", "guestOSPlatform"),
    ("AAOSSDVCoreGuest", "sdvMiddleware", "guestMiddleware"),
    ("AAOSIVIGuest", "os", "guestOSPlatform"),
]

_NOT_CODE = re.compile(r"/\*.*?\*/|//[^\n]*|\"(?:[^\"\\]|\\.)*\"", re.S)
_TYPED_BY = r"\b(?:ref\s+)?part\s+\w+\s*(?:\[[^\]]*\]\s*)?:(?![:>])[^;{{]*\b{definition}\b"


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


def _product_body() -> str:
    return _body(_code(SLICE), rf"\bpart\s+def\s+{PRODUCT_DEF}\s*:>\s*ProductLineConfiguredProduct\s*\{{")


def _docs(path: Path) -> str:
    """The text of ``path`` with the leading asterisks of comment lines dropped and whitespace collapsed."""
    return " ".join(re.sub(r"^\s*\*\s?", "", path.read_text(encoding="utf-8"), flags=re.M).split())


def _receipt_record() -> dict:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    (model,) = [m for m in receipt["evaluation"]["feature_models"] if m["feature_model"] == "SDVProductLineFeatureModel"]
    (record,) = [c for c in model["configurations"] if c["configuration"] == CONFIGURATION_NAME]
    return record


# -- the configured product -------------------------------------------------------------------


def test_the_configured_product_pairs_the_projection_with_the_driving_realization() -> None:
    """The same shape as INC-MW-011: the projection and the phase-8 system of interest, no variant chosen here."""
    own = _own(_product_body())
    assert re.findall(r"\b(?:ref\s+)?part\s+(\w+)\s*:", own) == ["platformStack", "drivingSoftware"]
    assert f"part platformStack : {PROJECTION};" in own
    assert "part drivingSoftware : ClosedLoopDrivingSoftwareRealization;" in own
    assert ":>>" not in _product_body(), "the product redefines no feature of its parts"
    assert "ref part" not in own, "the product composes both of its parts"


def test_one_binding_makes_the_composed_s_core_services_the_selected_middleware() -> None:
    """Phase 8 composes the S-CORE services in the realization (the gateway processes sit on the observation path),
    so the product binds a composed part, not a reference, and says so: two composers of one instance, unlike
    INC-MW-011. No second binding: the adapter is the programs' binding code, a dependency."""
    realization = _body(_code(PHYSICAL), r"\bpart\s+def\s+ClosedLoopDrivingSoftwareRealization\s*:>\s*ClosedLoopDrivingSystem\s*\{")
    assert re.search(r"(?<!ref )\bpart scoreServices : EclipseSCORE\b", _own(realization)), "phase 8 composes scoreServices"
    own = _own(_product_body())
    assert re.findall(r"\bbinding\s+(\w+)\s+bind\b", own) == ["scoreServicesBoundToSelectedMiddleware"]
    assert "binding scoreServicesBoundToSelectedMiddleware bind drivingSoftware.scoreServices = platformStack.middleware;" in own
    assert len(re.findall(r"\bbind\b", own)) == 1, "a further binding in the product body"
    docs = _docs(SLICE)
    assert "two composers of one middleware instance" in docs
    assert "no part of the realization is the adapter" in docs


def test_the_slice_types_no_part_by_a_platform_layer_definition() -> None:
    """The projection and the realization carry the layer types; the slice restates none of them."""
    code = _code(SLICE)
    for definition in ["EclipseSCORE", "AutoE2EStack", "AutoE2EToSCOREAdapter", "LinuxPlatform", "KVMHypervisor",
                       "AndroidHLOS", "AndroidSDVMiddleware", "SDVPlatformStack"]:
        assert not re.search(_TYPED_BY.format(definition=definition), code), f"the slice types a part by {definition}"


def test_the_configured_product_is_no_member_product() -> None:
    """Valid, not admitted: the definition specializes the kernel's configured product and nothing else."""
    code = _code(SLICE)
    assert re.search(rf"\bpart\s+def\s+{PRODUCT_DEF}\s*:>\s*ProductLineConfiguredProduct\s*\{{", code)
    assert re.findall(r":>(?!>)\s*([\w:]+)", code) == ["ProductLineConfiguredProduct"]
    assert not re.search(r"\bspecializes\b", code)
    assert "ProductLineMemberProduct" not in code
    assert re.search(rf"\bpart <'{IDENTITY}'> configuredProduct : {PRODUCT_DEF}\s*\{{", code)


# -- the receipt --------------------------------------------------------------------------------


def test_driving_config_001_is_bound_to_the_exact_receipt() -> None:
    """One receipt, three holders of its digest: DRIVING-CONFIG-001, MW-CONFIG-002 and the projection header."""
    digest = hashlib.sha256(RECEIPT.read_bytes()).hexdigest()
    bound = re.findall(r'attribute receiptSha256 : ScalarValues::String = "([0-9a-f]{64})";', SLICE.read_text(encoding="utf-8"))
    assert bound == [digest], "DRIVING-CONFIG-001 binds another receipt than the committed one"
    (mw_bound,) = re.findall(r'attribute receiptSha256 : ScalarValues::String = "([0-9a-f]{64})";',
                             MW_SLICE.read_text(encoding="utf-8"))
    assert mw_bound == digest, "MW-CONFIG-002 binds another receipt than DRIVING-CONFIG-001"
    (header,) = re.findall(r"\* Receipt SHA-256: ([0-9a-f]{64})", PRODUCT_MODEL.read_text(encoding="utf-8"))
    assert header == digest, "the committed projection was generated from another receipt"


def test_the_receipt_records_what_the_configured_product_states() -> None:
    """Valid, the adapter derived for the pair with Eclipse S-CORE, not admitted for the three documented reasons."""
    record = _receipt_record()
    assert record["projection_name"] == PROJECTION
    assert record["valid"] is True
    assert record["admission"]["admitted"] is False
    derived = {d["variation"]: d["variant"] for d in record["derived_variants"]}
    assert derived == {selection: variant for selection, (_, variant, _) in SELECTIONS.items()}
    (rule,) = [d for d in record["derived_variants"] if "rule" in d]
    assert (rule["variation"], rule["variant"], rule["rule"]) == ("applicationMiddlewareAdapter", "autoE2EToSCORE",
                                                                 "autoE2EEclipseSCORERule")
    selected = set(record["selected"])
    assert {"platformStack.autoE2E", "platformStack.eclipseSCORE", "platformStack.linux", "platformStack.kvm",
            "platformStack.guestAndroid", "platformStack.guestAndroidSDV", "sensingBoundary.camera",
            "capabilities.hmiDisplay"} <= selected
    assert not {"sensingBoundary.lidar", "sensingBoundary.radar", "platformStack.autoware", "platformStack.androidSDV"} & selected
    reasons = " ".join(record["admission"]["reasons"])
    for reason in ["platformStack.autoE2E: deferred drivingStackVariability", "reference-only eclipseSCORE",
                   "capabilities.hmiDisplay: not in the governed scope", "misses derived realizations of aaosIntegrated",
                   "does not represent the common content"]:
        assert reason in reasons, reason
    docs = _docs(SLICE)
    for statement in ["the driving stack is deferred variability", "Eclipse S-CORE is reference-only",
                      "the HMI display has no element in the governed scope",
                      "realizes the AAOS-integrated alternative without its middleware androidSDV",
                      "does not represent the common content: no Autoware, no LiDAR"]:
        assert statement in docs, statement


def test_the_configuration_has_no_evidence_record() -> None:
    """The evidence records under ``feature-configurations/evidence/`` are the retired Bills-of-Features'
    evidence blocks (ADR 0022, S7): nothing evaluates them, no receipt reads them, and the precedent
    MW-CONFIG-002 has none. The evidence of this configured product is phase 10 model content bound to
    DRIVING-CONFIG-001 (owner question of 2026-11-06)."""
    assert not EVIDENCE.exists(), "an evidence record carries nothing the model does not"
    assert "closed_loop_driving_autoe2e_score_reference" not in " ".join(
        p.name for p in EVIDENCE.parent.glob("*.yaml"))


# -- the feature model and the links of the system of interest -----------------------------------


def test_the_feature_model_states_the_three_owner_decisions() -> None:
    """Exclusions of the three unpaired middlewares plus one derivation rule; Linux required; the camera required."""
    code = _code(FEATURE_MODEL)
    feature = _body(code, r"#feature occurrence <'F-PLATFORM-VEHICLE-APPLICATION-AUTOE2E'> autoE2E\[0\.\.1\] :> vehicleApplication default null \{")
    exclusion = _own(_body(feature, r"\bassert constraint autoE2EExcludesUnsupportedMiddleware :> xorFeatures \{"))
    assert "new FeatureOperand(that, (androidSDV, autosarAdaptive, noMiddleware))" in exclusion
    assert "new FeatureOperand(that, linux)" in _own(_body(feature, r"\bassert constraint <'C013'> autoE2ERequiresLinux :> requiresFeatures \{"))
    assert "new FeatureOperand(that, sensingBoundary::camera)" in _own(_body(feature, r"\bassert constraint <'C012'> autoE2ERequiresCamera :> requiresFeatures \{"))
    assert not re.search(r"\bautoE2ERequires\w*(SCORE|Middleware)\b", code), "the pairing is exclusions, not a requires constraint"
    rules = re.findall(r"#DerivationRule dependency (\w+)\s+from [\w:]+::applicationMiddlewareAdapter::autoE2EToSCORE\s+to\s+([^;]+);", code)
    assert len(rules) == 1 and rules[0][0] == "autoE2EEclipseSCORERule"
    assert re.findall(r"platformStack::(\w+)", rules[0][1]) == ["autoE2E", "eclipseSCORE"]
    assert re.search(r"dependency autoE2ECorrespondsToDrivingStackVariability\s+from [\w:]+::platformStack::autoE2E\s+to [\w:]+::DeferredVariabilitySet::drivingStackVariability;", code)
    docs = _docs(FEATURE_MODEL)
    assert "No derivation rule exists for AutoE2E with Android SDV, AUTOSAR Adaptive or no middleware" in docs


def test_the_shared_asset_carries_the_two_variants_the_rule_targets() -> None:
    code = _code(PLATFORM_STACK)
    assert "variant part autoE2E : AutoE2EStack;" in " ".join(code.split())
    assert "variant part autoE2EToSCORE : AutoE2EToSCOREAdapter;" in " ".join(code.split())
    assert re.search(r"\bpart def AutoE2EStack :> VehicleApplicationLayer\b", code)
    assert re.search(r"\bpart def AutoE2EToSCOREAdapter :> ApplicationMiddlewareAdapterLayer\b", code)
    assert "no program of its own" in _docs(PLATFORM_STACK)


def test_the_system_of_interest_links_to_the_feature_and_the_two_variants() -> None:
    """What phase 5 promised: phase 9 links the system of interest to the feature it enters a member product with."""
    code = " ".join(_code(SLICE).split())
    targets = dict(re.findall(r"dependency (drivingSystemOn\w+) from ClosedLoopDrivingSoftwareRealization to ([\w:]+);", code))
    assert targets == {
        "drivingSystemOnAutoE2EFeature": "DE4SDV_SDVProductLineFeatureModel::SDVProductLineFeatureTree::platformStack::autoE2E",
        "drivingSystemOnAutoE2EStackVariant": "DE4SDV_SDVPlatformStack::AutoE2EStack",
        "drivingSystemOnAutoE2EToSCOREAdapter": "DE4SDV_SDVPlatformStack::AutoE2EToSCOREAdapter",
    }
    assert ("dependency derivedAdapterIsTheProgramsBindingCode from configuredProduct::drivingSoftware::drivingAgent, "
            "configuredProduct::drivingSoftware::actuationAdapter, configuredProduct::drivingSoftware::statePublisherApplication "
            "to configuredProduct::platformStack::applicationMiddlewareAdapter;") in code
    assert ("dependency drivingAgentRunsTheSelectedApplication from configuredProduct::drivingSoftware::drivingAgent "
            "to configuredProduct::platformStack::vehicleApplication;") in code
    assert "dependency configuredProductAdmissionGap from configuredProduct to DE4SDV_ClosedLoopDrivingFraming::gapProductLineAdmission;" in code
    assert ("dependency configuredDrivingSoftwareTrace from configuredProduct::drivingSoftware to "
            "DE4SDV_ClosedLoopDrivingPhysicalSoftwareRealization::closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware;") in code


def test_the_context_layers_of_phase_8_are_typed_by_the_selected_variants() -> None:
    """The product does not compose the physical context; this pin keeps its host and guest layers the
    definitions of the variants the projection selects, so the bench of phase 8 is the configured product's."""
    projection = _code(PRODUCT_MODEL)
    stack = _code(PLATFORM_STACK)
    physical = _code(PHYSICAL)
    for selection, (variation, variant, definition) in SELECTIONS.items():
        assert re.search(rf"\bpart :>> {selection} = {variation}::{variant};", projection), selection
        assert re.search(rf"\bvariant part {variant} : {definition};", _body(stack, rf"\bvariation part {variation} : \w+\s*\{{")), variant
    for context_def, layer, selection in CONTEXT_LAYERS:
        definition = SELECTIONS[selection][2]
        body = _own(_body(physical, rf"\bpart def {context_def}\b[^{{;]*\{{"))
        assert re.search(rf"(?<!ref )\bpart {layer} : {definition}\b", body), f"{context_def}.{layer} is not a {definition}"
    host = _own(_body(physical, r"\bpart def ClosedLoopDrivingLinuxHost\b[^{;]*\{"))
    assert "KVMHypervisor" not in host, "the S-CORE host nests no VM (amendment of 2026-11-09)"


def test_no_feature_model_or_configuration_document_names_an_increment_requirement() -> None:
    for path in [FEATURE_MODEL, CONFIGURATION, PRODUCT_MODEL, PLATFORM_STACK]:
        assert "DE4SDV_ClosedLoopDrivingNeedsRequirements" not in path.read_text(encoding="utf-8"), path
        assert "REQ-DRIVING" not in path.read_text(encoding="utf-8"), path


def test_no_driving_requirement_depends_on_the_hmi_display() -> None:
    """No requirement statement names a display, so no OnHMIDisplay dependency exists, and the slice says why.
    One need, NEED-DRIVING-004, names the display to state the driving system's independence from it."""
    requirements = REQUIREMENTS.read_text(encoding="utf-8")
    assert "hmiDisplay" not in requirements
    statements = {}
    for match in re.finditer(r"requirement <'((?:REQ|NEED)-DRIVING-\d+)'> \w+ : \w+ \{", requirements):
        body = _body(requirements[match.start():], re.escape(match[0]))
        (statements[match[1]],) = re.findall(r'language "English" /\*(.*?)\*/', body, re.S)
    assert len([i for i in statements if i.startswith("REQ-")]) >= 30, "the requirement statements"
    naming = sorted(i for i, s in statements.items() if re.search(r"\b(display|screen)\b", s, re.I))
    assert naming == ["NEED-DRIVING-004"], naming
    assert "adds no requirement dependency on hmiDisplay" in _docs(SLICE)


# -- the views, the charter and the guide --------------------------------------------------------


def test_the_two_phase_9_views_frame_the_two_concerns() -> None:
    code = _code(SLICE)
    for view, viewpoint, concern in [
        ("closedLoopDrivingProductLineConfigurationView", "ProductLineConfigurationViewpoint", "drivingProductLineConfigurationConcern"),
        ("closedLoopDrivingProductModelAssemblyView", "ProductModelAssemblyViewpoint", "drivingProductModelAssemblyConcern"),
    ]:
        body = _body(code, rf"\bview {view}\s*\{{")
        assert re.search(rf"\bviewpoint \w+ : {viewpoint}\s*\{{\s*frame {concern};", " ".join(body.split()))
        assert "render asTreeDiagram;" in body
        assert "attribute maxCompartmentEntries = 0;" in body
        assert re.search(rf"\bconcern {concern} : {viewpoint.replace('Viewpoint', 'Concern')}\s*\{{", code)
    configuration = _own(_body(code, r"\bview closedLoopDrivingProductLineConfigurationView\s*\{"))
    assert re.findall(r"\bexpose (\w+);", configuration) == [PROJECTION] + [f"selected{s[0].upper()}{s[1:]}".replace(
        "selectedOsPlatform", "selectedOperatingSystem").replace("selectedGuestOSPlatform", "selectedGuestOperatingSystem")
        for s in SELECTIONS]
    assembly = _own(_body(code, r"\bview closedLoopDrivingProductModelAssemblyView\s*\{"))
    assert re.findall(r"\bexpose ([\w:]+);", assembly) == [PRODUCT_DEF, f"{PRODUCT_DEF}::platformStack",
                                                           f"{PRODUCT_DEF}::drivingSoftware",
                                                           f"{PRODUCT_DEF}::scoreServicesBoundToSelectedMiddleware"]
    assert "filter not (@ SysML::AllocationUsage);" in assembly


def test_the_charter_names_the_phase_9_package_after_phase_8() -> None:
    charter = _body(_code(FRAMING), r"\bpart closedLoopDrivingCharter : IncrementCharter\s*\{")
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", FRAMING.read_text(encoding="utf-8"), re.S)
    assert artifacts and re.findall(r'"([^"]+)"', artifacts.group(1))[-3:-1] == [
        "DE4SDV_ClosedLoopDrivingPhysicalSoftwareRealization", PACKAGE]
    assert charter
    assert re.search(rf"\bpackage {PACKAGE}\s*\{{", _code(SLICE))


def test_the_guide_describes_phase_9_and_its_decisions() -> None:
    guide = GUIDE.read_text(encoding="utf-8")
    assert "## Variability and configuration (Phase 9)" in guide
    section = guide.split("## Variability and configuration (Phase 9)")[1].split("\n## ")[0]
    for text in [IDENTITY, "`autoE2E`", "C012", "C013", "androidSDV", "autosarAdaptive", "noMiddleware",
                 "autoE2EToSCORE", "valid and not admitted", "hmiDisplay", "receipt", "2026-11-06"]:
        assert text in section, text
    assert "tests/test_closed_loop_driving_variability_configuration.py" in guide
    assert "closed_loop_driving_variability_configuration.sysml" in guide
