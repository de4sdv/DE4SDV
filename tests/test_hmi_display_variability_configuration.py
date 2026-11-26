"""INC-HMI-001 phase 9: the configured product of the HMI display in the VisionPilot configuration.

Lexical pins on the phase 9 package and on what it reuses, not semantic validation:

- reuse, as the framing records the owner decision of 2026-11-17 on the display of the VisionPilot configuration:
  the configured product types its platform stack by the projection of driverAssistanceVisionPilotSCOREReference,
  the configuration of the driver-assistance increment; no feature, configuration, shared asset, receipt or
  projection changes, and no member type is specialized;
- the composition: the phase 8 realization as one part, two bindings of the central computer's referenced layers
  to the stack's, the SDV Media VM's operating system unbound, and the guests' owned layers typed by the definitions
  of the variants that the projection selects;
- HMI-CONFIG-001 bound to the exact receipt, and its dependencies on the realization and on the three gaps of phase 8
  that the product inherits;
- the links of rule 5 in its dependency form, declared with their clients and opened by a comment of record, none
  that repeats its subject's link, none in a feature-model or configuration document;
- two trees framed by the two DE4SDV concerns, no expose of an inherited feature by qualified name;
- the charter, the guide, and the words the increment keeps out of its texts.

The licensed Syside run validates the model; the receipt-bound pins read the committed receipt, which this phase
does not change.
"""

from __future__ import annotations

import hashlib
import json
import re
from itertools import zip_longest
from pathlib import Path

from sysml_shapes import strip_comments
from test_hmi_display_framing import APPROVAL, PAST_BEHAVIOR
from test_hmi_display_functional_architecture import EXCLUDED_WORD_SHA256
from test_hmi_display_physical_software_realization import BANNED_WORD_SHA256, LAUNCH_PHRASE

ROOT = Path(__file__).resolve().parents[1]
HMI = ROOT / "textual-notation-of-model" / "packages" / "features" / "hmi"
SLICE = HMI / "hmi_display_variability_configuration.sysml"
PHYSICAL = HMI / "hmi_display_physical_software_realization.sysml"
FRAMING = HMI / "hmi_display_framing.sysml"
NEEDS = HMI / "hmi_display_needs_requirements.sysml"
VIEWS_INDEX = HMI / "VIEWS.md"
GUIDE = ROOT / "docs" / "guides" / "hmi-display-increment.md"
NAMING_DOC = ROOT / "docs" / "naming" / "naming-conventions.md"
PLATFORM_STACK = ROOT / "textual-notation-of-model" / "packages" / "architecture" / "sdv_platform_stack.sysml"
DRIVING_SLICE = ROOT / "textual-notation-of-model" / "packages" / "features" / "driving" / (
    "driver_assistance_variability_configuration.sysml")
PLE = ROOT / "model-based-product-line-engineering"
CONFIGURATION = PLE / "feature-configurations" / "driver_assistance_visionpilot_score_reference.sysml"
PRODUCT_MODEL = PLE / "product-models" / "driver_assistance_visionpilot_score_reference.sysml"
RECEIPT = PLE / "feature-models" / "receipts" / "sdv_product_line.receipt.json"
MODEL_ROOTS = (ROOT / "textual-notation-of-model", PLE)

PACKAGE = "DE4SDV_HmiDisplayVariabilityConfiguration"
PHYSICAL_PACKAGE = "DE4SDV_HmiDisplayPhysicalSoftwareRealization"
PRODUCT_DEF = "HmiDisplayVisionPilotSCOREConfiguredProduct"
IDENTITY = "HMI-CONFIG-001"
CONFIGURATION_NAME = "driverAssistanceVisionPilotSCOREReference"
PROJECTION = "DriverAssistanceVisionPilotSCOREReference"
DIGEST = "0447e4a561240dcdc0cc1860eb9a707e0cc5ca965af40c9a6c26b9534458c4db"
FEATURE = "DE4SDV_SDVProductLineFeatureModel::SDVProductLineFeatureTree::platformStack::"

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
#: binding name -> (the referenced layer of the realization, the projection selection it is bound to)
BINDINGS = {
    "centralComputerOSBoundToSelectedOperatingSystem": ("displayRealization.centralComputer.os",
                                                        "platformStack.osPlatform"),
    "centralComputerHypervisorBoundToSelectedHypervisor": ("displayRealization.centralComputer.hypervisor",
                                                           "platformStack.hypervisor"),
}
#: phase 8 guest definition -> its owned layer parts -> the projection selection whose variant types them
GUEST_LAYERS = {
    "HmiDisplaySDVCoreGuest": {"os": "guestOSPlatform", "sdvMiddleware": "guestMiddleware"},
    "HmiDisplayIVIGuest": {"os": "guestOSPlatform"},
}
#: phase 8 definition -> its referenced layers (bound here or, for the SDV Media VM, left unbound)
REFERENCED_LAYERS = {
    "HmiDisplayCentralComputer": {"os": "OSPlatformLayer", "hypervisor": "HypervisorLayer"},
    "HmiDisplaySDVMediaGuest": {"os": "OSPlatformLayer"},
}
#: dependency name -> (client, supplier): the trace and the three gaps of phase 8 that the product inherits
DEPENDENCIES = {
    "configuredDisplayRealizationTrace": ("configuredProduct::displayRealization",
                                          f"{PHYSICAL_PACKAGE}::hmiDisplayPhysicalSystem"),
    "configuredProductSceneCurrencyGap": ("configuredProduct",
                                          f"{PHYSICAL_PACKAGE}::gapHmiRendererJudgesSceneCurrency"),
    "configuredProductDrawingToleranceGap": ("configuredProduct", f"{PHYSICAL_PACKAGE}::gapHmiDrawingToleranceUnset"),
}
#: the gaps of phase 8 by short name: the two above, and the bench's, which the product does not inherit
PRODUCT_GAPS = {"GAP-HMI-001": "gapHmiRendererJudgesSceneCurrency", "GAP-HMI-003": "gapHmiDrawingToleranceUnset"}
BENCH_GAP = ("GAP-HMI-002", "gapHmiBenchSpeedFeed")

#: Rule 5, dependency form, owned with their clients (link name -> (client, feature)). A requirement links only what
#: its subject does not bring.
SUBJECT_LINKS: dict[str, tuple[str, str]] = {}
# ---- unit: the links of the system of interest ------------------------------------------------------------------
#: The system of interest brings VisionPilot and the AAOS SDV guest, so no requirement links a feature of its own.
SUBJECT_LINKS["hmiDisplaySystemOnVisionPilotFeature"] = ("hmiDisplaySystem", "visionPilot")
SUBJECT_LINKS["hmiDisplaySystemOnGuestAndroidSDVFeature"] = ("hmiDisplaySystem", "guestAndroidSDV")
# ---- end of the unit --------------------------------------------------------------------------------------------
REQUIREMENT_LINKS: dict[str, tuple[str, str]] = {}
LINKS = REQUIREMENT_LINKS

ALIASES = ["selectedVehicleApplication", "selectedMiddleware", "selectedOperatingSystem", "selectedHypervisor",
           "selectedGuestOperatingSystem", "selectedGuestMiddleware", "selectedApplicationMiddlewareAdapter"]
VIEWS = [("hmiDisplayProductLineConfigurationView", "ProductLineConfigurationViewpoint",
          "hmiDisplayProductLineConfigurationConcern"),
         ("hmiDisplayProductModelAssemblyView", "ProductModelAssemblyViewpoint",
          "hmiDisplayProductModelAssemblyConcern")]
ASSEMBLY_EXPOSES = [PRODUCT_DEF, f"{PRODUCT_DEF}::platformStack", f"{PRODUCT_DEF}::displayRealization",
                    *(f"{PRODUCT_DEF}::{name}" for name in BINDINGS), "configuredProduct"]

GUIDE_HEADING = "## Variability and configuration (Phase 9)"
GUIDE_STATUS = (
    "**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context, Phase 3 capability classification, "
    "Phase 4 stakeholder needs, Phase 5 requirements, Phase 6 functional architecture, Phase 7 logical architecture, "
    "Phase 8 physical and software realization and Phase 9 variability and configuration, proposal.**")
GUIDE_NEXT = (
    "The next model obligation is **Phase 10**: the verification cases, one or more for each requirement of the "
    "increment; its first gate is `verificationCaseVerifiesRequirement`.")
GUIDE_LINK = "../../textual-notation-of-model/packages/features/hmi/hmi_display_variability_configuration.sysml"
GUIDE_FRAME_LINE = (f"- [SysML variability and configuration]({GUIDE_LINK}): the Phase 9 configured product of the "
                    "HMI display.")
GUIDE_CHECK = (
    "`python -m pytest tests/test_hmi_display_framing.py tests/test_hmi_display_functional_architecture.py "
    "tests/test_hmi_display_logical_architecture.py tests/test_hmi_display_physical_software_realization.py "
    "tests/test_hmi_display_variability_configuration.py -q`")

_NOT_CODE = re.compile(r"/\*.*?\*/|//[^\n]*|\"(?:[^\"\\]|\\.)*\"", re.S)
_TYPED_BY = r"\b(?:ref\s+)?part\s+\w+\s*(?:\[[^\]]*\]\s*)?:(?![:>])[^;{{]*\b{definition}\b"


def _code(path: Path) -> str:
    """The text of ``path`` with comments and string literals blanked."""
    return _NOT_CODE.sub(lambda match: '""' if match.group().startswith('"') else " ", path.read_text(encoding="utf-8"))


def _body(code: str, header: str) -> str:
    """The braced body after the one match of ``header``, which ends with its opening brace."""
    matches = list(re.finditer(header, code))
    assert len(matches) == 1, f"expected one {header!r}, found {len(matches)}"
    start, depth = matches[0].end() - 1, 0
    assert code[start] == "{", f"{header!r} does not end with an opening brace"
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


def _doc_texts(path: Path) -> list[str]:
    """Every comment and doc of ``path``, asterisks dropped, whitespace collapsed."""
    return [" ".join(re.sub(r"^\s*\*\s?", "", text, flags=re.M).split())
            for text in re.findall(r"/\*(.*?)\*/", path.read_text(encoding="utf-8"), re.S)]


def _product_body() -> str:
    return _body(_code(SLICE), rf"\bpart\s+def\s+{PRODUCT_DEF}\s*:>\s*ProductLineConfiguredProduct\s*\{{")


def _guide_section() -> str:
    return GUIDE.read_text(encoding="utf-8").split(GUIDE_HEADING, 1)[1].split("\n## ", 1)[0]


def _feature_links(path: Path) -> dict[str, tuple[str, str]]:
    code = _code(path)
    links = {name: (client, feature) for name, client, feature in re.findall(
        rf"\bdependency\s+(\w+)\s+from\s+(\w+)\s+to\s+{re.escape(FEATURE)}(\w+)\s*;", code)}
    assert len(links) == code.count("DE4SDV_SDVProductLineFeatureModel"), \
        f"a feature reference of another form in {path.name}"
    return links


def _projections() -> set[str]:
    return {name for path in (PLE / "product-models").glob("*.sysml")
            for name in re.findall(r"(?m)^part def (\w+) :> SDVPlatformStack\b", _code(path))}


# -- the configured product ---------------------------------------------------------------------------------------


def test_the_configured_product_pairs_the_projection_with_the_display_realization() -> None:
    """Reuse by typing: the projection of the VisionPilot configuration and the phase 8 realization, no variant
    chosen here, no specialization of the driver-assistance increment's configured product."""
    own = _own(_product_body())
    assert re.findall(r"\b(?:ref\s+)?part\s+(\w+)\s*:", own) == ["platformStack", "displayRealization"]
    assert f"part platformStack : {PROJECTION};" in own
    assert "part displayRealization : HmiDisplayPhysicalSystem;" in own
    assert ":>>" not in _product_body(), "the product redefines no feature of its parts"
    assert "ref part" not in own, "the product composes both of its parts"
    code = _code(SLICE)
    assert re.search(rf"\bprivate import {PHYSICAL_PACKAGE}::HmiDisplayPhysicalSystem;", code)
    assert "DriverAssistanceVisionPilotSCOREConfiguredProduct" not in code, "no specialization of DRIVING-CONFIG-002"
    projections = _projections()
    assert PROJECTION in projections and len(projections) >= 6, "the scan must see the committed projections"
    typed = [(usage, projection) for usage, types in re.findall(r"\bpart\s+(\w+)\s*:\s*([\w:, ]+);", code)
             for projection in projections if re.search(rf"\b{projection}\b", types)]
    assert typed == [("platformStack", PROJECTION)], "one projection-typed part, the platform stack"


def test_the_configured_product_binds_the_central_computer_layers_and_nothing_else() -> None:
    """The stack owns the main-side operating system and the hypervisor; the central computer of phase 8 refers to
    them. The SDV Media VM's operating system has no layer of its own in the stack and stays unbound."""
    found = re.findall(r"\bbinding\s+(\w+)\s+bind\s+([\w.]+)\s*=\s*([\w.]+)\s*;", _own(_product_body()))
    assert {name: (left, right) for name, left, right in found} == BINDINGS
    assert len(found) == len(BINDINGS) == len(re.findall(r"\bbind\b", _code(SLICE))), "no other binding"
    assert "hmiSDVMediaGuest" not in _code(SLICE), "the SDV Media VM's operating system stays unbound"
    docs = _docs(SLICE)
    for phrase in ("KVM runs in the kernel of the main-side operating system, so the platform of the central "
                   "computer is the main side.",
                   "The SDV Media VM refers to an operating system that no source that DE4SDV keeps names, and the "
                   "platform stack has no layer for a VM of the guest (ADR 0025), so this product leaves that "
                   "reference unbound."):
        assert phrase in docs, phrase


def test_the_phase_8_layers_are_referenced_or_owned_as_the_product_binds_them() -> None:
    """The central computer and the SDV Media VM refer to their layers; the SDV Core and IVI VMs own theirs, typed by
    the definitions of the variants that the projection selects (as INC-DRIVING-002 guards its context)."""
    physical, stack = _code(PHYSICAL), _code(PLATFORM_STACK)
    for definition, layers in REFERENCED_LAYERS.items():
        body = _own(_body(physical, rf"\bpart def {definition}\s*\{{"))
        for layer, generic in layers.items():
            assert f"ref part {layer} : {generic};" in body, f"{definition}.{layer} is not referenced"
    for _selection, (variation, variant, definition) in LAYERS.items():
        variants = _body(stack, rf"\bvariation part {variation} : \w+\s*\{{")
        assert re.search(rf"\bvariant (?:ref )?part {variant} : {definition}\b", variants), variant
    for definition, layers in GUEST_LAYERS.items():
        body = _own(_body(physical, rf"\bpart def {definition}\s*\{{"))
        for layer, selection in layers.items():
            typed = LAYERS[selection][2]
            assert re.search(rf"(?<!ref )\bpart {layer} : {typed};", body), f"{definition}.{layer} is not a {typed}"
    docs = _docs(SLICE)
    assert "The guest side departs from one instance and one owner per layer." in docs
    assert ("Those parts stay owned and unbound, so the platform stack is not the only owner of the guest operating "
            "system and the guest middleware in this product.") in docs


def test_the_slice_types_no_part_by_a_platform_layer_definition() -> None:
    """The projection and the realization carry the layer types; the slice restates none of them."""
    code = _code(SLICE)
    for definition in [*(definition for _variation, _variant, definition in LAYERS.values()), "SDVPlatformStack",
                       "OSPlatformLayer", "HypervisorLayer"]:
        assert not re.search(_TYPED_BY.format(definition=definition), code), f"the slice types a part by {definition}"


def test_the_configured_product_is_no_member_product() -> None:
    """Valid, and the governed scope does not admit it: the kernel's configured product and nothing else."""
    code = _code(SLICE)
    assert re.findall(r":>(?!>)\s*([\w:]+)", code) == ["ProductLineConfiguredProduct"]
    assert not re.search(r"\bspecializes\b", code)
    assert "ProductLineMemberProduct" not in code and "DE4SDV_AEBSProductLineScope" not in code
    assert re.findall(r"\bpart <'([A-Z-]+\d+)'> (\w+) : (\w+)\s*\{", code) == [
        (IDENTITY, "configuredProduct", PRODUCT_DEF)]


def test_the_configured_product_traces_the_realization_and_the_two_gaps_it_inherits() -> None:
    """GAP-HMI-001 and -003 are product content (GAP-HMI-004 is retired in phase 10); GAP-HMI-002 is the bench's
    speed feed, which the car's design does not have."""
    code = " ".join(_code(SLICE).split())
    found = re.findall(r"\bdependency\s+(\w+)\s+from\s+([\w:]+)\s+to\s+([\w:]+)\s*;", code)
    assert {name: (client, supplier) for name, client, supplier in found} == DEPENDENCIES
    assert len(re.findall(r"\bdependency\b", code)) == len(DEPENDENCIES), "the slice declares no rule-5 link"
    physical = PHYSICAL.read_text(encoding="utf-8")
    for short, name in [*PRODUCT_GAPS.items(), BENCH_GAP]:
        assert re.search(rf"\bpart <'{short}'> {name} : IncrementGap\s*\{{", physical), short
    assert BENCH_GAP[1] not in code
    assert re.search(r"(?m)^  part hmiDisplayPhysicalSystem : HmiDisplayPhysicalSystem\s*\{", physical)


# -- the receipt -----------------------------------------------------------------------------------------------------


def _receipt_record() -> dict:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    (model,) = [m for m in receipt["evaluation"]["feature_models"]
                if m["feature_model"] == "SDVProductLineFeatureModel"]
    (record,) = [c for c in model["configurations"] if c["configuration"] == CONFIGURATION_NAME]
    return record


def test_hmi_config_001_is_bound_to_the_exact_receipt_that_driving_config_002_binds() -> None:
    """Reuse: the receipt is not re-cut, so the digest equals the committed receipt's and DRIVING-CONFIG-002's."""
    digest = hashlib.sha256(RECEIPT.read_bytes()).hexdigest()
    pattern = r'attribute receiptSha256 : ScalarValues::String = "([0-9a-f]{64})";'
    assert re.findall(pattern, SLICE.read_text(encoding="utf-8")) == [digest] == [DIGEST]
    assert re.findall(pattern, DRIVING_SLICE.read_text(encoding="utf-8")) == [digest], "one receipt, both identities"
    (header,) = re.findall(r"\* Receipt SHA-256: ([0-9a-f]{64})", PRODUCT_MODEL.read_text(encoding="utf-8"))
    assert header == digest, "the committed projection was generated from another receipt"
    assert ("The pull request that rebinds it states whether the configuration's own receipt record changed."
            ) in _docs(SLICE)


def test_the_reuse_changes_no_document_the_receipt_reads() -> None:
    """No feature model, configuration, shared asset or projection changes: each source of the receipt still has
    the SHA-256 the receipt records for it, and no configuration names the HMI display's increment."""
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    sources = [source for source in receipt["sources"] if not source["path"].startswith(".sysand/")]
    assert len(sources) >= 30, "the population of the check must not be vacuous"
    for source in sources:
        path = ROOT / source["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"], source["path"]
    assert str(CONFIGURATION.relative_to(ROOT)) in {source["path"] for source in sources}


def test_the_receipt_records_what_the_slice_states() -> None:
    """Valid, the VisionPilot-to-S-CORE adapter derived, the governed scope does not admit it; adaptive cruise control
    and lane-keep assist come with the configuration."""
    record = _receipt_record()
    assert record["projection_name"] == PROJECTION
    assert record["valid"] is True and record["admission"]["admitted"] is False
    assert {d["variation"]: d["variant"] for d in record["derived_variants"]} == {
        selection: variant for selection, (_variation, variant, _definition) in LAYERS.items()}
    assert {"capabilities.hmiDisplay", "capabilities.adaptiveCruiseControl", "capabilities.laneKeepAssist",
            "platformStack.linux", "platformStack.kvm", "platformStack.guestAndroid",
            "platformStack.guestAndroidSDV"} <= set(record["selected"])
    docs = _docs(SLICE)
    for phrase in ("The receipt records the configuration as valid, and the governed scope does not admit it",
                   "The configuration also selects adaptive cruise control and lane-keep assist, which this "
                   "increment does not judge (phase 3)", "selected operating system, Linux", "selected hypervisor, KVM",
                   "The main side selects VisionPilot, Eclipse S-CORE and Linux. The hypervisor is KVM. The guest side "
                   "selects Android with the AAOS SDV middleware."):
        assert phrase in docs, phrase


# -- the links of rule 5 -------------------------------------------------------------------------------------------


def test_the_links_are_declared_with_their_clients() -> None:
    """In rule 5's dependency form: a requirement links a feature of its own only for what its subject does not bring,
    and none repeats its subject's link (rule 11); the system of interest's links are declared in the framing, and no
    other model file declares a dependency of it."""
    assert _feature_links(NEEDS) == REQUIREMENT_LINKS
    raw = NEEDS.read_text(encoding="utf-8")
    for client in {client for client, _feature in REQUIREMENT_LINKS.values()}:
        assert re.search(rf"\brequirement <'REQ-HMI-0\d\d'> {client} :", raw), client
    assert not {f for _c, f in REQUIREMENT_LINKS.values()} & {f for _c, f in SUBJECT_LINKS.values()}, \
        "a requirement link that repeats its subject's does not earn its place"
    assert _feature_links(FRAMING) == SUBJECT_LINKS
    subject = re.compile(r"(?<![\w:])(?:DE4SDV_HmiDisplayFraming::)?'?hmiDisplaySystem'?(?![\w'])")
    for path in sorted(p for root in MODEL_ROOTS for p in root.rglob("*.sysml")):
        if path == FRAMING:
            continue
        for dependency in re.findall(r"\bdependency\b[^;{]*", strip_comments(path.read_text(encoding="utf-8"))):
            clients_of = re.search(r"\bfrom\b(.*?)\bto\b", dependency, re.S)
            assert not (clients_of and subject.search(clients_of.group(1))), (path.name, dependency)


def test_no_link_sits_in_a_feature_model_document_or_another_hmi_package() -> None:
    """The evaluator reads every dependency of a feature-model or configuration document; the links stay outside."""
    documents = [*sorted((PLE / "feature-models").rglob("*.sysml")),
                 *sorted((PLE / "feature-configurations").rglob("*.sysml")),
                 *sorted((PLE / "product-models").glob("*.sysml")), PLATFORM_STACK]
    assert len(documents) >= 30, "the population of the check must not be vacuous"
    for path in documents:
        text = path.read_text(encoding="utf-8")
        for name in ("DE4SDV_HmiDisplay", "hmiDisplaySystem", "HmiDisplayPhysicalSystem", IDENTITY):
            assert name not in text, (path.name, name)
        assert not re.search(r"\bREQ-HMI-0\d\d\b", text), path.name
    for path in sorted(HMI.glob("hmi_display_*.sysml")):
        if path not in (NEEDS, FRAMING):
            assert "DE4SDV_SDVProductLineFeatureModel" not in _code(path), path.name


# ---- unit: the links of the system of interest ------------------------------------------------------------------
def test_the_system_of_interest_depends_on_visionpilot_and_on_guest_android_sdv() -> None:
    """The display of this increment is the display of the VisionPilot configuration inside the AAOS SDV guest: two
    dependencies of the system of interest in the framing name both features, and its requirements follow it."""
    assert _feature_links(FRAMING) == SUBJECT_LINKS == {
        "hmiDisplaySystemOnVisionPilotFeature": ("hmiDisplaySystem", "visionPilot"),
        "hmiDisplaySystemOnGuestAndroidSDVFeature": ("hmiDisplaySystem", "guestAndroidSDV")}
    code = " ".join(_code(FRAMING).split())
    assert "ref part :>> systemOfInterest = hmiDisplaySystem;" in code
    usage = "part hmiDisplaySystem : HmiDisplaySystem;"
    assert code.count(usage) == 1
    assert REQUIREMENT_LINKS == {}
    assert ("In the framing, phase 9 makes the system of interest depend on the features visionPilot and "
            "guestAndroidSDV. Every requirement follows it, and none carries a link of its own.") in _docs(NEEDS)


def test_no_requirement_of_the_increment_depends_on_a_feature() -> None:
    """Every requirement follows the system of interest, which brings both features: no requirement of the increment
    is a client of any dependency in any model file, in any form (named or not, qualified or by its short name, with
    metadata, inside a body), and the requirements package names no feature and no platform-stack variant."""
    requirements = re.findall(r"\brequirement <'(REQ-HMI-0\d\d)'> (\w+) :", NEEDS.read_text(encoding="utf-8"))
    assert len(requirements) == 10, "the population of the check must not be vacuous"
    names = "|".join(name for _short, name in requirements)
    shorts = "|".join(short for short, _name in requirements)
    client = re.compile(rf"(?<![\w:])(?:DE4SDV_HmiDisplayNeedsRequirements::)?(?:'?(?:{names})'?|'(?:{shorts})')"
                        r"(?![\w'])")
    for path in sorted(p for root in MODEL_ROOTS for p in root.rglob("*.sysml")):
        for dependency in re.findall(r"\bdependency\b[^;{]*", strip_comments(path.read_text(encoding="utf-8"))):
            clients = re.search(r"\bfrom\b(.*?)\bto\b", dependency, re.S)
            assert not (clients and client.search(clients.group(1))), (path.name, dependency)
    code = _code(NEEDS)
    assert "DE4SDV_SDVProductLineFeatureModel" not in code and "DE4SDV_SDVPlatformStack" not in code
    assert "#FeatureBinding" not in code


def test_the_owner_direction_is_one_comment_about_the_product_line_gap() -> None:
    """The direction on what the display of every member is to show is the one comment of the framing, about the gap
    that phase 3 hangs its scope decisions on, and changes no member."""
    code = " ".join(_code(FRAMING).split())
    assert len(re.findall(r"\bcomment\b", code)) == 1
    assert re.search(r"\bcomment about gapHmiDisplayInProductLine (?:part|requirement|concern|view|dependency)\b", code)
    raw = FRAMING.read_text(encoding="utf-8")
    match = re.search(r"\bcomment\s+about\s+gapHmiDisplayInProductLine\s*/\*(.*?)\*/", raw, re.S)
    assert match and " ".join(re.sub(r"^\s*\*\s?", "", match.group(1), flags=re.M).split()) == OWNER_DIRECTION
    assert sum(_doc_texts(path).count(OWNER_DIRECTION) for path in HMI.glob("*.sysml")) == 1
# ---- end of the unit --------------------------------------------------------------------------------------------


# -- the views, the charter and the guide ----------------------------------------------------------------------------


def test_the_two_phase_9_views_frame_the_two_concerns_and_publish_the_configured_product() -> None:
    code = _code(SLICE)
    for view, viewpoint, concern in VIEWS:
        body = _body(code, rf"\bview {view}\s*\{{")
        assert re.search(rf"\bviewpoint \w+ : {viewpoint}\s*\{{\s*frame {concern};", " ".join(body.split()))
        assert "render asTreeDiagram;" in body and "attribute maxCompartmentEntries = 0;" in body
        assert "attribute showAnnotationRows = false;" in body
        assert re.search(rf"\bconcern {concern} : {viewpoint.replace('Viewpoint', 'Concern')}\s*\{{", code)
    configuration = _own(_body(code, rf"\bview {VIEWS[0][0]}\s*\{{"))
    assert re.findall(r"\bexpose (\w+);", configuration) == [PROJECTION, *ALIASES]
    declared = dict(re.findall(rf"\balias (\w+)\s+for {PROJECTION}::(\w+);", " ".join(code.split())))
    assert declared == dict(zip(ALIASES, LAYERS)), declared
    assembly = _own(_body(code, rf"\bview {VIEWS[1][0]}\s*\{{"))
    assert re.findall(r"\bexpose ([\w:]+);", assembly) == ASSEMBLY_EXPOSES, (
        "phase 11's applicablePhaseContentPublished reads the configured-product usage")
    assert "filter not (@ SysML::AllocationUsage);" in assembly


def test_no_view_exposes_an_inherited_feature_by_qualified_name() -> None:
    """An inherited feature exposed by name re-renders every tree that draws a usage of its definition, in any
    increment. Every expose names a member of this package or an owned member of the product definition."""
    code = _code(SLICE)
    own = _own(_product_body())
    members = set(re.findall(r"\b(?:part|binding)\s+(\w+)\b", own))
    for exposed in re.findall(r"\bexpose\s+([\w:]+)\s*;", code):
        parts = exposed.split("::")
        assert len(parts) <= 2, exposed
        if len(parts) == 2:
            assert parts[0] == PRODUCT_DEF and parts[1] in members, exposed


def test_the_views_index_lists_the_two_phase_9_views() -> None:
    """VIEWS.md comes from scripts/generate_view_index.py; the renders come from the licensed Syside run."""
    index = VIEWS_INDEX.read_text(encoding="utf-8")
    section = index.split("## `hmi_display_variability_configuration.sysml`", 1)[1].split("\n## ", 1)[0]
    assert re.findall(r"^### `(\w+)`", section, re.M) == [view for view, _viewpoint, _concern in VIEWS]


def test_the_charter_names_the_phase_9_package_last() -> None:
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", FRAMING.read_text(encoding="utf-8"), re.S)
    assert artifacts and re.findall(r'"([^"]+)"', artifacts.group(1))[-2:] == [PHYSICAL_PACKAGE, PACKAGE]
    assert re.findall(r"(?m)^package\s+(\w+)\s*\{", _code(SLICE)) == [PACKAGE], "one global package per file"


def test_the_naming_conventions_name_hmi_config_001_once() -> None:
    """The configuration paragraph of the naming conventions names the identity; tests/test_check_naming.py holds
    that the checker accepts it and still refuses an unregistered subject."""
    flat = " ".join(NAMING_DOC.read_text(encoding="utf-8").split())
    assert flat.count("`HMI-CONFIG-001` is the configured product of the HMI display (INC-HMI-001 phase 9)") == 1


def test_the_guide_describes_phase_9_and_names_phase_10_next() -> None:
    guide = GUIDE.read_text(encoding="utf-8")
    order = [guide.index(heading) for heading in ("## Physical and software realization (Phase 8)", GUIDE_HEADING,
                                                  "## What the framing already records as open")]
    assert order == sorted(order) and guide.count(GUIDE_HEADING + "\n") == 1
    raw_section = _guide_section()
    assert all(len(line) <= 79 or "](" in line for line in raw_section.splitlines()), "the guide wraps at 79"
    section = " ".join(raw_section.split())
    for text in (IDENTITY, f"`{CONFIGURATION_NAME}`", f"`{PROJECTION}`", "`HmiDisplayPhysicalSystem`",
                 "valid, and the governed scope does not admit it", "the privileged PLE authority run does not start",
                 "Two bindings", "The operating system of the SDV Media VM stays unbound",
                 "So the stack is not their only owner", "GAP-HMI-001 and GAP-HMI-003. GAP-HMI-002",
                 "GAP-HMI-002 is not among them", "2026-11-17", f"({GUIDE_LINK})"):
        assert text in section, text
    flat = " ".join(guide.split())
    assert flat.count(GUIDE_STATUS) == 1
    frame = " ".join(guide.split("## Authoritative frame", 1)[1].split("\n## ", 1)[0].split())
    assert frame.count(GUIDE_FRAME_LINE) == 1
    nxt = " ".join(guide.split("## Next obligation and execution limits", 1)[1].split("\n## ", 1)[0].split())
    assert nxt.count(GUIDE_NEXT) == 1 and flat.count("The next model obligation is") == 1
    assert "The next model obligation is **Phase 9**" not in flat
    check = " ".join(guide.split("## Check the framing change", 1)[1].split())
    assert GUIDE_CHECK in check


#: The guide's Phase 9 section, block by block (each paragraph and each bullet), whole and in order: generated from
#: the guide, never written by hand.
GUIDE_BLOCKS: list[str] = [
    ("[`hmi_display_variability_configuration.sysml`](../../textual-notation-of-model/packages/features/hmi/hmi_disp"
     "lay_variability_configuration.sysml) answers which configured product the HMI display belongs to, and with "
     "which selections. Phase 3 recorded no feature-model delta and placed the display in the VisionPilot "
     "configuration, so Phase 9 adds no feature, constraint, shared asset, configuration, receipt or projection."),
    ("- **The configuration.** The framing names the display of the VisionPilot configuration of the "
     "driver-assistance increment (owner decision of 2026-11-17), so the configured product reuses that "
     "configuration, `driverAssistanceVisionPilotSCOREReference`: VisionPilot, Eclipse S-CORE, Linux and KVM on the "
     "main side, Android with the AAOS SDV middleware in the guest, the camera and the HMI display. It also selects "
     "adaptive cruise control and lane-keep assist, which this increment does not judge (Phase 3); they come with "
     "the configuration, and this increment claims nothing of them. The receipt records the configuration as "
     "**valid, and the governed scope does not admit it**, for the reasons that the driver-assistance increment "
     "states. The same configuration configures DRIVING-CONFIG-002: a configuration can configure more than one "
     "configured product. No feature model, configuration, receipt or projection changes, so the privileged PLE "
     "authority run does not start."),
    ("- **The configured product.** `HMI-CONFIG-001` types its platform stack by the projection "
     "`DriverAssistanceVisionPilotSCOREReference` and composes the Phase 8 realization `HmiDisplayPhysicalSystem`. "
     "Two bindings make the platform and the hypervisor of the central computer, which Phase 8 references, the "
     "selected Linux and KVM: KVM runs in the kernel of the main-side operating system. The operating system of the "
     "SDV Media VM stays unbound: no source that DE4SDV keeps names it, and the stack has no layer for a VM of the "
     "guest. The guest layers of the realization stay owned: Android in the SDV Core VM and in the IVI VM, and the "
     "AAOS SDV middleware in the SDV Core VM, beside the guest operating system and the guest middleware of the "
     "stack. So the stack is not their only owner, and a test keeps them typed by the definitions of the selected "
     "variants. The identity binds the SHA-256 of the receipt, and Phase 10 evidence binds the identity. Dependencies "
     "record the trace to the Phase 8 usage and the two open gaps of Phase 8 that the product inherits, GAP-HMI-001 "
     "and GAP-HMI-003. GAP-HMI-002 is not among them: on the bench the simulator stands in for the ECU that measures "
     "the vehicle speed, and the gap is the feed of that stand-in. The definition specializes no member-product type."),
# ---- unit: the links of the system of interest ------------------------------------------------------------------
    ("- **The links of rule 5.** Until the configuration evaluator reads links of increment elements and the "
     "existing links have moved, rule 5 takes its dependency form (ADR 0027 decision 8). The links are declared with"
     " their clients, in the framing. No check reads them: `tests/test_hmi_display_variability_configuration.py` "
     "pins each link, and that no feature-model or configuration document names an element of the increment."),
    ("- **The system of interest.** `hmiDisplaySystemOnVisionPilotFeature` and "
     "`hmiDisplaySystemOnGuestAndroidSDVFeature` make it depend on `visionPilot` and `guestAndroidSDV`. By ADR 0026 "
     "every member product is to have an HMI display, and what it shows in each is open; this system of interest is "
     "the display of the VisionPilot configuration, inside the AAOS SDV guest, so it enters a member product only "
     "with both features. The binding form gives an element one link and derives no variant for this pair, so the "
     "move of the links takes this combination to the owner. By the owner decision of 2026-11-26 the requirements "
     "follow the system of interest. A comment about `gapHmiDisplayInProductLine` records the owner direction of "
     "the same day: the display of every member is to show the vehicle speed, the collision warning, the outdated "
     "marks and the scene, and to stay independent of the driving application that feeds it. It is a direction for "
     "the open scope decisions and changes no member."),
    ("- **The requirements.** Every requirement follows the system of interest, and none carries a link of its own. "
     "`REQ-HMI-004`, `REQ-HMI-005` and `REQ-HMI-007` name the warning request, which the driver-assistance increment"
     " gives only with both features."),
# ---- end of the unit --------------------------------------------------------------------------------------------
    ("Two views answer the phase's questions, both trees: the selections of the projection (Product Line "
     "Configuration viewpoint) and the assembly of the product with its two parts, its two bindings and the "
     "configured-product usage (Product Model Assembly viewpoint). Their diagrams come from the licensed Syside run;"
     " [`VIEWS.md`](../../textual-notation-of-model/packages/features/hmi/VIEWS.md) lists the views."),
]


def _guide_blocks() -> list[str]:
    """The Phase 9 section of the guide as its blocks: paragraphs split at blank lines, bullet runs at each bullet."""
    blocks = []
    for block in re.split(r"\n\s*\n", _guide_section().strip()):
        blocks += [" ".join(part.split()) for part in re.split(r"\n(?=- )", block)]
    return blocks


def test_the_guide_section_is_every_block_of_record() -> None:
    """Every block of the section, whole and in order: a changed, dropped, added or moved sentence fails it."""
    blocks = _guide_blocks()
    assert len(blocks) == len(GUIDE_BLOCKS) >= 4, "the population of the check must not be vacuous"
    for number, (block, pinned) in enumerate(zip(blocks, GUIDE_BLOCKS), 1):
        assert block == pinned, f"block {number}: {block[:80]!r}"

def test_no_text_of_phase_9_quotes_the_owner_carries_a_banned_word_or_types_by_the_bench() -> None:
    """System 1: the bench appears only as stand-in sentences in the identity's doc, never in the product's."""
    section = _guide_section()
    texts = {"model": SLICE.read_text(encoding="utf-8"), "guide section": section,
             "this test": Path(__file__).read_text(encoding="utf-8")}
    for label, text in texts.items():
        digests = {hashlib.sha256(word.encode()).hexdigest() for word in re.findall(r"[a-z0-9]+", text.lower())}
        assert EXCLUDED_WORD_SHA256 not in digests and not digests & BANNED_WORD_SHA256, label
        assert LAUNCH_PHRASE not in " ".join(text.split()), label
    for label in ("model", "guide section"):
        flat = " ".join(texts[label].split())
        assert not re.search(r"(?i)\b(?:the owner said|owner's words|in his words|he said)\b", flat), label
        assert not re.search(r"(?i)\b(?:issue|pull request|PR)\s*#?\d+|#\d{2,}", flat), label
    for text in [*_doc_texts(SLICE), " ".join(section.split())]:
        assert not PAST_BEHAVIOR.search(text) and not APPROVAL.search(text), text[:80]
    product = _body(SLICE.read_text(encoding="utf-8"), rf"\bpart\s+def\s+{PRODUCT_DEF}\b[^{{]*\{{")
    product_doc = " ".join(re.findall(r"/\*(.*?)\*/", product, re.S)[0].split())
    assert not re.search(r"(?i)\b(?:bench|simulator|guest host|CARLA|stands? in)\b", product_doc)
    bench = [s for s in re.split(r"(?<=\.)\s+", _docs(SLICE))
             if re.search(r"(?i)\b(?:bench|simulator|guest host)\b", s)]
    assert bench and all("stands in" in s or "gap of the bench" in s for s in bench), bench
    assert not re.search(r"\b(?:AAOSGuestHost|GuestHost|Simulator\w*)\b", _code(SLICE)), "nothing typed by the bench"


# -- the package whole -----------------------------------------------------------------------------------------------

#: Every comment and doc of the package, in file order, as `_doc_texts` reads them: the texts of record of the
#: design, generated from the model, never written by hand.
TEXTS_OF_RECORD: list[str] = [
    ("DE4SDV HMI display variability and configuration model slice. INC-HMI-001, phase 9: the configured product of "
     "the HMI display, with the configuration identity HMI-CONFIG-001. It pairs two parts. The first is the "
     "platform-stack projection that the configurator generates from the receipt of the feature configuration "
     "driver_assistance_visionpilot_score_reference.sysml. The second is the physical realization of the HMI display"
     " from phase 8, the system of interest of the increment. Phase 3 records that the display belongs to the "
     "VisionPilot configuration, so this phase adds no feature configuration and changes no feature, no shared "
     "asset, no receipt and no projection: the configured product types its platform stack by the projection of that"
     " configuration, DriverAssistanceVisionPilotSCOREReference. The same configuration configures the configured "
     "product of the driver-assistance increment, DRIVING-CONFIG-002; by the kernel, a configuration can configure "
     "more than one configured product. The feature configuration and the generated projection own the variant "
     "selections. No element of this package restates them. Its docs name some of them, and a guard test keeps those"
     " names equal to the receipt. The links of rule 5 are declared with their clients, in the rule's dependency "
     "form. This package holds none of them. The receipt records the configuration as valid, and the governed scope "
     "does not admit it; the phase 9 package of the driver-assistance increment states why. So the configured "
     "product specializes no member-product type. This slice is configuration evidence only: it proves no runtime "
     "behavior and satisfies no requirement."),
    ("The configured product of the HMI display in the VisionPilot configuration. It holds the generated "
     "platform-stack projection and the physical realization of the HMI display, the system of interest of "
     "INC-HMI-001: the central computer with the SDV Core, IVI and SDV Media VMs. The local parts compose the "
     "projection and the phase-8 realization. They choose no variant. Two bindings. The central computer of phase 8 "
     "refers to its own platform and to its hypervisor, and the platform stack owns them: one binding makes the "
     "platform the same thing as the selected operating system, Linux, and one makes the hypervisor the same thing "
     "as the selected hypervisor, KVM. KVM runs in the kernel of the main-side operating system, so the platform of "
     "the central computer is the main side. The SDV Media VM refers to an operating system that no source that "
     "DE4SDV keeps names, and the platform stack has no layer for a VM of the guest (ADR 0025), so this product "
     "leaves that reference unbound. The guest side departs from one instance and one owner per layer. The platform "
     "stack models the guest side as one guest operating system and one guest middleware for one or more VMs, while "
     "the realization owns Android in the SDV Core VM and in the IVI VM, and the AAOS SDV middleware in the SDV Core"
     " VM. Those parts stay owned and unbound, so the platform stack is not the only owner of the guest operating "
     "system and the guest middleware in this product. A test keeps them typed by the definitions of the variants "
     "that the projection selects: Android and the AAOS SDV middleware. No shared asset implements the HMI display, "
     "so no feature binding resolves the hmiDisplay selection. The projection lists it among the selections that "
     "SysML does not resolve. The configuration also selects adaptive cruise control and lane-keep assist, which "
     "this increment does not judge (phase 3): they come with the configuration, the projection lists them too, and "
     "this increment claims nothing of them. The definition specializes no member-product type, because the governed"
     " scope does not admit the configuration. It specializes the kernel's ProductLineConfiguredProduct, the "
     "configured product of phase 9."),
    ("HMI-CONFIG-001: the configuration identity that the phase-10 evidence binds, as the evidence of the "
     "driver-assistance increment binds DRIVING-CONFIG-002. The identity is bound to the exact receipt that the "
     "configurator generated the platform-stack projection from. receiptSha256 is the SHA-256 of "
     "model-based-product-line-engineering/feature-models/receipts/sdv_product_line.receipt.json, the receipt that "
     "records the evaluation of the feature configuration driverAssistanceVisionPilotSCOREReference. A receipt re-cut "
     "keeps this identity and rebinds receiptSha256 here. The pull request that rebinds it states whether the "
     "configuration's own receipt record changed. By the decision of 2026-11-17 that the identity of "
     "DRIVING-CONFIG-001 records, the record has not changed when its only difference is added states omitted for "
     "features that it does not select, and every other entry is the same: validity, reasons, derived variants with "
     "their variant ids, admission, the selected features, projection name, source, description and element id. "
     "Evidence that binds HMI-CONFIG-001 also records the receipt SHA-256 it ran against. The product inherits two "
     "open gaps of phase 8: the renderer's judging of the scene by the term current (GAP-HMI-001) and the tolerance "
     "of a drawn position (GAP-HMI-003). On the bench, the guest host of INC-DRIVING-001 stands in for the central "
     "computer, with the SDV Media VM as a third guest, and the simulator stands in for the ECU that measures the "
     "vehicle speed and for the vehicle network; the feed of that speed (GAP-HMI-002) is a gap of the bench, not of "
     "this product. Configuration evidence only. This usage proves no renderer, app, composition or platform behavior "
     "and no requirement satisfaction."),
    ("Product-line engineers, system architects and open-source reviewers need the variant selections of "
     "HMI-CONFIG-001 in the platform-stack projection that the configurator generates from its receipt, the "
     "projection of the VisionPilot configuration. The main side selects VisionPilot, Eclipse S-CORE and Linux. The "
     "hypervisor is KVM. The guest side selects Android with the AAOS SDV middleware. The adapter is the derived "
     "VisionPilot-to-S-CORE adapter. This concern is about choices, not assembly."),
    ("System architects, verification engineers and open-source reviewers need the assembly of HMI-CONFIG-001: the "
     "platform-stack projection and the realization of the HMI display, with the two bindings that make the platform"
     " and the hypervisor of the central computer the selected operating system and the selected hypervisor, and the"
     " guest layers that the VMs of the realization own. Phase 10 then verifies one product. This concern is about "
     "assembled assets, not the variation space."),
    ("The generated projection of the VisionPilot configuration and its seven selected layers: six that the "
     "configuration selects, and the derived adapter."),
    ("The configured product: its definition with the two parts and the two bindings, and the usage HMI-CONFIG-001 "
     "that the phase-10 evidence binds. The view filters out the phase-8 allocations, which target the usage of the "
     "realization in phase 8, not this product."),
]

#: The package's code, every declaration at its own depth (two spaces a level), as `_skeleton` reads it: generated
#: from the model, never written by hand. A line ending in a backslash continues on the next.
SKELETON = """\
/*…*/
package DE4SDV_HmiDisplayVariabilityConfiguration {
  private import DE4SDV_MethodViewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_HmiDisplayPhysicalSoftwareRealization::HmiDisplayPhysicalSystem;
  private import DE4SDV_ProductLine::ProductLineConfiguredProduct;
  private import Views::*;
  part def HmiDisplayVisionPilotSCOREConfiguredProduct :> ProductLineConfiguredProduct {
    doc /*…*/
    part platformStack : DriverAssistanceVisionPilotSCOREReference;
    part displayRealization : HmiDisplayPhysicalSystem;
    binding centralComputerOSBoundToSelectedOperatingSystem bind displayRealization.centralComputer.os =\
 platformStack.osPlatform;
    binding centralComputerHypervisorBoundToSelectedHypervisor bind displayRealization.centralComputer.hypervisor =\
 platformStack.hypervisor;
  part <'HMI-CONFIG-001'> configuredProduct : HmiDisplayVisionPilotSCOREConfiguredProduct {
    doc /*…*/
    attribute receiptSha256 : ScalarValues::String =\
 "0447e4a561240dcdc0cc1860eb9a707e0cc5ca965af40c9a6c26b9534458c4db";
  dependency configuredDisplayRealizationTrace from configuredProduct::displayRealization to\
 DE4SDV_HmiDisplayPhysicalSoftwareRealization::hmiDisplayPhysicalSystem;
  dependency configuredProductSceneCurrencyGap from configuredProduct to\
 DE4SDV_HmiDisplayPhysicalSoftwareRealization::gapHmiRendererJudgesSceneCurrency;
  dependency configuredProductDrawingToleranceGap from configuredProduct to\
 DE4SDV_HmiDisplayPhysicalSoftwareRealization::gapHmiDrawingToleranceUnset;
  concern hmiDisplayProductLineConfigurationConcern : ProductLineConfigurationConcern {
    doc /*…*/
    subject;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder reviewer : OpenSourceReviewer;
  concern hmiDisplayProductModelAssemblyConcern : ProductModelAssemblyConcern {
    doc /*…*/
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  alias selectedVehicleApplication for DriverAssistanceVisionPilotSCOREReference::vehicleApplication;
  alias selectedMiddleware for DriverAssistanceVisionPilotSCOREReference::middleware;
  alias selectedOperatingSystem for DriverAssistanceVisionPilotSCOREReference::osPlatform;
  alias selectedHypervisor for DriverAssistanceVisionPilotSCOREReference::hypervisor;
  alias selectedGuestOperatingSystem for DriverAssistanceVisionPilotSCOREReference::guestOSPlatform;
  alias selectedGuestMiddleware for DriverAssistanceVisionPilotSCOREReference::guestMiddleware;
  alias selectedApplicationMiddlewareAdapter for\
 DriverAssistanceVisionPilotSCOREReference::applicationMiddlewareAdapter;
  view hmiDisplayProductLineConfigurationView {
    viewpoint selectedProductLineConfigurationViewpoint : ProductLineConfigurationViewpoint {
      frame hmiDisplayProductLineConfigurationConcern;
    doc /*…*/
    expose DriverAssistanceVisionPilotSCOREReference;
    expose selectedVehicleApplication;
    expose selectedMiddleware;
    expose selectedOperatingSystem;
    expose selectedHypervisor;
    expose selectedGuestOperatingSystem;
    expose selectedGuestMiddleware;
    expose selectedApplicationMiddlewareAdapter;
    attribute showAnnotationRows = false;
    attribute maxCompartmentEntries = 0;
    render asTreeDiagram;
  view hmiDisplayProductModelAssemblyView {
    viewpoint selectedProductModelAssemblyViewpoint : ProductModelAssemblyViewpoint {
      frame hmiDisplayProductModelAssemblyConcern;
    doc /*…*/
    expose HmiDisplayVisionPilotSCOREConfiguredProduct;
    expose HmiDisplayVisionPilotSCOREConfiguredProduct::platformStack;
    expose HmiDisplayVisionPilotSCOREConfiguredProduct::displayRealization;
    expose HmiDisplayVisionPilotSCOREConfiguredProduct::centralComputerOSBoundToSelectedOperatingSystem;
    expose HmiDisplayVisionPilotSCOREConfiguredProduct::centralComputerHypervisorBoundToSelectedHypervisor;
    expose configuredProduct;
    filter not (@ SysML::AllocationUsage);
    attribute showAnnotationRows = false;
    attribute maxCompartmentEntries = 0;
    render asTreeDiagram;
"""

#: Exchange and relation keywords -> how often the stripped file holds each: the two bindings, the four dependencies
#: and the five imports, and none of any other form.
KEYWORD_COUNTS = {"bind": 2, "binding": 2, "dependency": 3, "import": 5, "flow": 0, "interface": 0, "message": 0,
                  "succession": 0, "first": 0, "then": 0, "connection": 0, "connect": 0, "end": 0, "allocation": 0,
                  "allocate": 0, "satisfy": 0, "verify": 0, "perform": 0, "exhibit": 0, "include": 0, "ref": 0,
                  "redefines": 0, "subsets": 0, "references": 0, "specializes": 0, "variant": 0, "variation": 0}


def _skeleton() -> list[str]:
    """The raw model as one line per declaration, the whole declaration up to its own `{` or `;` (whitespace
    collapsed), indented two spaces per brace depth, each body's members after it one level deeper. The header, each
    `doc` and each `comment` keep only `/*…*/` (the texts of record pin their words); every other `/* */` comment, a
    section comment, keeps its text, and so does every `//` note, so a note fails the skeleton too."""
    raw = SLICE.read_text(encoding="utf-8")
    lines: list[str] = []
    pending, depth, at = "", 0, 0

    def emit(text: str) -> None:
        lines.append("  " * depth + " ".join(text.split()))

    while at < len(raw):
        if raw.startswith("//*", at):
            end = raw.index("*/", at + 3) + 2
            emit("//* " + " ".join(raw[at + 3:end - 2].split()) + " */")
            at = end
        elif raw.startswith("//", at):
            end = raw.find("\n", at)
            end = len(raw) if end < 0 else end
            emit("// " + " ".join(raw[at + 2:end].split()))
            at = end
        elif raw.startswith("/*", at):
            end = raw.index("*/", at + 2) + 2
            if re.fullmatch(r"\s*(?:doc|comment)\b[\w\s:,]*", pending) or not (lines or pending.strip()):
                emit(pending + " /*…*/")
                pending = ""
            elif pending.strip():
                pending += " /* " + " ".join(raw[at + 2:end - 2].split()) + " */ "
            else:
                emit("/* " + " ".join(raw[at + 2:end - 2].split()) + " */")
            at = end
        elif raw[at] in "\"'":
            end = raw.index(raw[at], at + 1) + 1
            pending += raw[at:end]
            at = end
        elif raw[at] == "{":
            emit(pending + " {")
            pending, depth, at = "", depth + 1, at + 1
        elif raw[at] == ";":
            emit(pending + ";")
            pending, at = "", at + 1
        elif raw[at] == "}":
            if pending.strip():
                emit(pending)
            assert depth > 0, "a } that closes no body"
            pending, depth, at = "", depth - 1, at + 1
        else:
            pending += raw[at]
            at += 1
    if pending.strip():
        emit(pending)
    assert depth == 0, "a body that is never closed"
    return lines


def test_the_package_is_exactly_its_skeleton() -> None:
    """The whole code of the package, pinned line by line: every declaration at its own depth, whole, in order. A
    change to any declaration fails it: a member added, removed, moved or reordered at any depth, a changed keyword,
    name, type, value, binding end, expose, filter or attribute, a note or a section comment added, a brace that
    closes no body or a body never closed. Its limit: the header, the docs and the named comments are pinned by
    TEXTS_OF_RECORD, not here."""
    expected = SKELETON.splitlines()
    actual = _skeleton()
    assert len(expected) >= 60, "the skeleton must not be vacuous"
    assert not re.search(r"[^\x00-\x7f]", _code(SLICE)), \
        "the code is ASCII: only docs and comments hold other characters"
    for number, (line, pinned) in enumerate(zip_longest(actual, expected), 1):
        assert line == pinned, f"skeleton line {number}: {line!r}, pinned {pinned!r}"


def test_every_doc_and_comment_of_the_package_is_its_text_of_record() -> None:
    """Each text whole and in order, so a changed word, a dropped sentence, an added sentence or a copy of a text in a
    second comment fails, whichever phrase the other tests pin."""
    texts = _doc_texts(SLICE)
    assert len(texts) == len(TEXTS_OF_RECORD) >= 7, "the population of the check must not be vacuous"
    for number, (text, pinned) in enumerate(zip(texts, TEXTS_OF_RECORD), 1):
        assert text == pinned, f"text {number}: {text[:80]!r}"


def test_the_slice_declares_no_exchange_and_no_relation_beyond_its_bindings_and_dependencies() -> None:
    """The whole comment-stripped file, every exchange and relation form at every level: the package, the product
    definition, the usage and the views."""
    code = _code(SLICE)
    found = {keyword: len(re.findall(rf"\b{keyword}\b", code)) for keyword in KEYWORD_COUNTS}
    assert found == KEYWORD_COUNTS
    assert code.count(":>>") == code.count("::>") == 0 and len(re.findall(r":>(?!>)", code)) == 1
    assert len(re.findall(r"=", code)) == len(BINDINGS) + 1 + 2 + 2, "two bindings, one value, four view attributes"


# -- the comments of the links ----------------------------------------------------------------------------------------

#: The plain comment of record that opens the links of rule 5 in a file that declares some (file name -> text).
LINK_COMMENTS: dict[str, str] = {}
# ---- unit: the links of the system of interest ------------------------------------------------------------------
LINK_COMMENTS[FRAMING.name] = (
    "Rule 5 of the increment workflow, in its dependency form, declared with the system of interest (phase 9). The "
    "display of this increment is the display of the VisionPilot configuration (owner decision of 2026-11-17), "
    "inside the AAOS SDV guest: the app in the IVI VM, the high availability renderer in an SDV Media VM, and the "
    "paths from the SDV Core VM to both. So it enters a member product only with the features visionPilot and "
    "guestAndroidSDV, and two dependencies name both. By the owner decision of 2026-11-26, its requirements follow "
    "it, and none links a feature of its own (rule 11). The warning request that REQ-HMI-004, REQ-HMI-005 and "
    "REQ-HMI-007 name comes with both: the requirements of the driver-assistance increment that name it follow a "
    "system of interest that brings visionPilot and apply only where the AAOS SDV guest middleware is selected. By "
    "ADR 0026 every member product is to have an HMI display, and what it shows in each is open "
    "(hmiDisplayContentScopeDecisions). The binding form gives an element one link and derives no variant for this "
    "pair, so the move of the links takes this combination to the owner (rule 5).")
#: The owner's direction on the display of every member: a comment about the product-line gap.
OWNER_DIRECTION = (
    "Owner direction of 2026-11-26: the display of every member is to show the vehicle speed, the collision warning, "
    "the outdated marks and the scene, and the HMI display is to stay independent of the driving application that "
    "feeds it. It is to take each input in a form that does not depend on that application, and each application that "
    "feeds it is to give its inputs in that form through a translation of its own. The vehicle speed has such a form, "
    "as COVESA VSS types it, and the warning request has the form that the driver-assistance increment gives it. The "
    "scene has the form of the scene of the panel of VisionPilot (termsHmiDisplayRequirements), and the scene-form "
    "amendment of phase 10 types its message in a form of the display's own (DisplaySceneMessage). In this increment "
    "VisionPilot is the source of the scene, which it does not give at its boundary yet (gapHmiSceneOutput), and of "
    "the warning request. It is a direction for the scope decisions that hmiDisplayContentScopeDecisions lists, for "
    "the AEBS requirements on the warning and for the message type of the scene; it changes no member here.")
# ---- end of the unit --------------------------------------------------------------------------------------------
#: The opening of a plain comment on the links of rule 5.
LINK_COMMENT_OPENING = "Rule 5 of the increment workflow, in its dependency form"
_LINK = re.compile(r"\s*dependency\s+(\w+)\s+from\s+(\w+)\s+to\s+([\w:]+)\s*;")


def _links_after_the_comment(path: Path, text: str) -> dict[str, tuple[str, str]]:
    """The dependencies right after the one plain comment of ``path`` whose words are ``text``, up to the first other
    statement."""
    raw = path.read_text(encoding="utf-8")
    ends = [match.end() for match in re.finditer(r"/\*(.*?)\*/", raw, re.S)
            if " ".join(re.sub(r"^\s*\*\s?", "", match.group(1), flags=re.M).split()) == text]
    assert len(ends) == 1, f"{path.name} holds the comment of record {len(ends)} times"
    found, at = {}, ends[0]
    while match := _LINK.match(raw, at):
        found[match.group(1)] = (match.group(2), match.group(3))
        at = match.end()
    return found


def test_the_links_of_each_file_follow_their_comment_of_record() -> None:
    """In a file that declares links of rule 5, one plain comment of record opens them, whole and once, and every link
    of the file follows it, in any order. A file without links holds no plain comment that opens on rule 5's
    dependency form."""
    for path, links in ((NEEDS, REQUIREMENT_LINKS), (FRAMING, SUBJECT_LINKS)):
        assert _feature_links(path) == links, path.name
        opening = [text for text in _doc_texts(path) if text.startswith(LINK_COMMENT_OPENING)]
        if not links:
            assert path.name not in LINK_COMMENTS and opening == [], path.name
            continue
        assert opening == [LINK_COMMENTS[path.name]], path.name
        assert _links_after_the_comment(path, LINK_COMMENTS[path.name]) == {
            name: (client, FEATURE + feature) for name, (client, feature) in links.items()}, path.name
    assert set(LINK_COMMENTS) <= {NEEDS.name, FRAMING.name}
