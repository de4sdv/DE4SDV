"""INC-MW-011 phase 9: the configured product MW-CONFIG-002 of the Eclipse S-CORE configuration.

The configured product pairs the platform-stack projection that the configurator
generates from the receipt with the realization of the middleware integration
layer. It holds one instance and one owner per platform layer: the layer declares
its S-CORE services, its adapter and the SDV Core of the guest as references, and
four bindings make them, and the platform software of the SDV Core, the platform
stack's parts (owner decisions of 2026-10-23 and 2026-10-28, ADR 0025). The
platform stack has no feature for the SDV Gateway on IVI, so the product leaves
that reference unbound. Since the scope revision of ADR 0023 and ADR 0026 it
specializes the S-CORE-integrated member definition (ADR 0023, decision 8), and
MW-CONFIG-002 is bound to the exact receipt. CLS-MW-004 has both integrated
alternatives as its counterpart (owner decision of 2026-11-21).
Under rule 5 of the increment workflow, the four HMI-path requirements depend on
the HMI display, declared with the requirements and outside the feature-model and
configuration documents.

These are lexical source guards; licensed Syside validates the model in CI.
Comments and string literals are blanked before code is matched.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLE = ROOT / "model-based-product-line-engineering"
RECEIPT = PLE / "feature-models" / "receipts" / "sdv_product_line.receipt.json"
PROJECTION = PLE / "product-models" / "middleware_autoware_score_reference.sysml"
CONFIGURATION = "model-based-product-line-engineering/feature-configurations/middleware_autoware_score_reference.sysml"
MIDDLEWARE = ROOT / "textual-notation-of-model" / "packages" / "features" / "middleware"
SLICE = MIDDLEWARE / "middleware_score_variability_configuration.sysml"
PHYSICAL = MIDDLEWARE / "middleware_score_physical_software_realization.sysml"
NEEDS = MIDDLEWARE / "middleware_score_needs_requirements.sysml"
FRAMING = MIDDLEWARE / "middleware_score_framing.sysml"
CLASSIFICATION = MIDDLEWARE / "middleware_score_feature_classification.sysml"
SCOPE = PLE / "scoping" / "de4sdv_aebs_product_line_scope.sysml"
#: The member definition of the S-CORE-integrated member in the governed scope (ADR 0023, decision 1).
MEMBER = "DE4SDV_AEBSProductLineScope::SCOREIntegratedAutowareAEBSReferenceMember"
#: CLS-MW-004's counterpart: both integrated alternatives (owner decision of 2026-11-21, replacing 2026-10-21's).
COUNTERPARTS = {
    "hmiGuestCandidateCounterpartOfAAOSIntegratedMode": "aaosIntegrated",
    "hmiGuestCandidateCounterpartOfSCOREIntegratedMode": "scoreIntegrated",
}
#: The validated model roots (AGENTS.md).
MODEL_ROOTS = (ROOT / "textual-notation-of-model", PLE)
HMI_DISPLAY = "DE4SDV_SDVProductLineFeatureModel::SDVProductLineFeatureTree::capabilities::hmiDisplay"
#: The HMI-path requirements and their IDs (owner decision of 2026-10-22).
HMI_PATH_REQUIREMENTS = {
    "reqDeliverAEBSSignalsInSourceOrder": "REQ-MW-014",
    "reqPreserveAEBSSignalProvenance": "REQ-MW-015",
    "reqNoApplicationDataFromHMIGuest": "REQ-MW-016",
    "reqDiscardFramesWhileHMIUnsubscribed": "REQ-MW-019",
}
#: Definitions of platform layers and of the phase-8 physical context: the slice types no part by one of them.
LAYER_DEFINITIONS = (
    "VehicleApplicationLayer", "AutowareStack", "MiddlewareLayer", "EclipseSCORE", "AndroidSDVMiddleware",
    "ApplicationMiddlewareAdapterLayer", "AutowareToSCOREAdapter", "OSPlatformLayer", "LinuxPlatform",
    "AndroidHLOS", "HypervisorLayer", "KVMHypervisor", "HardwareLayer", "SCORETwoDomainPhysicalSystem",
)

_NOT_CODE = re.compile(r'/\*.*?\*/|//[^\n]*|"(?:[^"\\\n]|\\.)*"', re.DOTALL)
#: Typing: ``name : T``, ``name : Pkg::T`` or ``T`` anywhere in a typing list ``name : A, P::B, T``
#: (never ``:>``, ``:>>`` or ``::``).
_TYPED_BY = (r"(?<![:\w])\w+\s*(?:\[[^\]]*\]\s*)?(?<!:):(?![:>])\s*(?:(?:\w+\s*::\s*)*\w+\s*,\s*)*"
             r"(?:\w+\s*::\s*)*{definition}\b")


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


def _heads(body: str) -> str:
    """Like :func:`_own`, but each nested body stays as ``{}``, so a declaration head ends at ``;`` or ``{``."""
    kept, depth = [], 0
    for character in body[1:-1]:
        if character == "{":
            depth += 1
            if depth == 1:
                kept.append("{")
        elif character == "}":
            depth -= 1
            if depth == 0:
                kept.append("}")
        elif depth == 0:
            kept.append(character)
    return " ".join("".join(kept).split())


def _product_body() -> str:
    return _body(_code(SLICE), r"\bpart\s+def\s+MiddlewareAutowareSCOREConfiguredProduct\s*:>\s*"
                               rf"{re.escape(MEMBER)}\s*,\s*ProductLineConfiguredProduct\s*\{{")


def _docs(path: Path) -> str:
    """Every comment of ``path``, comment leaders dropped, whitespace collapsed."""
    text = path.read_text(encoding="utf-8")
    return " ".join(" ".join(re.sub(r"^\s*\*\s?", "", comment, flags=re.M)
                             for comment in re.findall(r"/\*(.*?)\*/", text, re.S)).split())


def _composite_parts_typed_by(body: str, definition: str) -> list[str]:
    """The names of the composite (not ``ref``) part usages at any depth of ``body`` whose typing list has
    ``definition``, as in ``part adapter : PhysicalAllocationElement, AutowareToSCOREAdapter``."""
    names = []
    for match in re.finditer(r"\b(ref\s+)?part\s+(\w+)\s*(?:\[[^\]]*\]\s*)?:(?![:>])([^;{]*)", body):
        if not match[1] and definition in re.findall(r"(?:\w+\s*::\s*)*(\w+)", match[3]):
            names.append(match[2])
    return names


def test_the_configured_product_pairs_the_projection_with_the_layer_realization() -> None:
    body = _product_body()
    own = _own(body)
    assert "part platformStack : MiddlewareAutowareSCOREReference;" in own
    assert "part integrationLayer : SCOREMiddlewareIntegrationLayerRealization;" in own
    assert ":>>" not in body, "the product redefines no feature of its parts"


def test_the_layer_refers_to_its_s_core_services_and_its_adapter() -> None:
    """The realization owns no platform layer: its S-CORE services and its adapter are references
    (owner decision of 2026-10-23). The phase-8 physical context composes each of them exactly once, in
    the Linux host, and binds the layer's references to them."""
    realization = _heads(_body(_code(PHYSICAL), r"\bpart\s+def\s+SCOREMiddlewareIntegrationLayerRealization\b[^{;]*\{"))
    layered = [(match[1], match[2]) for match in re.finditer(r"\b(ref\s+)?part\s+(\w+)\s*:\s*([^{;]*)", realization)
               if {name.strip().rsplit("::", 1)[-1] for name in match[3].split(",")} & set(LAYER_DEFINITIONS)]
    assert layered == [("ref ", "adapter"), ("ref ", "scoreServices")]
    context = _body(_code(PHYSICAL), r"\bpart\s+def\s+SCORETwoDomainPhysicalSystem\s*\{")
    host = _own(_body(context, r"\bpart\s+linuxHost\s*\{"))
    assert re.search(r"(?<!ref )\bpart scoreServices : EclipseSCORE\b", host), "the Linux host composes scoreServices"
    assert re.search(r"(?<!ref )\bpart adapter : AutowareToSCOREAdapter\b", host), "the Linux host composes adapter"
    for definition, name in (("EclipseSCORE", "scoreServices"), ("AutowareToSCOREAdapter", "adapter")):
        assert _composite_parts_typed_by(context, definition) == [name], (
            f"the phase-8 context composes exactly one part typed by {definition}: linuxHost.{name}")
    own = _own(context)
    assert "binding scoreServicesBoundToLinuxHost bind integrationLayer.scoreServices = linuxHost.scoreServices;" in own
    assert "binding adapterBoundToLinuxHost bind integrationLayer.adapter = linuxHost.adapter;" in own


def test_the_configured_product_holds_one_instance_and_one_owner_per_platform_layer() -> None:
    """Four bindings make the layer's references the same things as the parts that the platform stack composes,
    their only owner: the S-CORE services, the adapter, the SDV Core as the guest middleware, and its platform
    software as the guest operating system, as in the AAOS-integrated configured member. The product body declares
    exactly two parts and exactly these four bindings. The SDV Gateway on IVI has no feature in the platform stack,
    so its reference stays unbound here, and the doc says so (ADR 0025)."""
    own = _own(_product_body())
    assert re.findall(r"\b(?:ref\s+)?part\s+(\w+)\s*:", own) == ["platformStack", "integrationLayer"]
    assert re.findall(r"\bbinding\s+(\w+)\s+bind\b", own) == [
        "scoreServicesBoundToSelectedMiddleware", "adapterBoundToDerivedAdapter",
        "sdvCoreBoundToGuestMiddleware", "platformSoftwareBoundToGuestOperatingSystem"]
    assert len(re.findall(r"\bbind\b", own)) == 4, "a further binding in the product body"
    for binding in ("binding scoreServicesBoundToSelectedMiddleware bind "
                    "integrationLayer.scoreServices = platformStack.middleware;",
                    "binding adapterBoundToDerivedAdapter bind "
                    "integrationLayer.adapter = platformStack.applicationMiddlewareAdapter;",
                    "binding sdvCoreBoundToGuestMiddleware bind "
                    "integrationLayer.sdvCore = platformStack.guestMiddleware;",
                    "binding platformSoftwareBoundToGuestOperatingSystem bind "
                    "integrationLayer.sdvCore.platformSoftware = platformStack.guestOSPlatform;"):
        assert binding in own, binding
    assert "integrationLayer.sdvGateway" not in own, "the platform stack has no feature for the SDV Gateway on IVI"
    doc = " ".join(re.sub(r"^\s*\*\s?", "", line) for line in SLICE.read_text(encoding="utf-8").splitlines())
    assert ("So this product leaves the layer's reference to the SDV Gateway on IVI unbound, and phase 8 binds it "
            "to the gateway of the IVI VM.") in " ".join(doc.split())
    code = _code(SLICE)
    for definition in LAYER_DEFINITIONS:
        assert not re.search(_TYPED_BY.format(definition=definition), code), f"the slice types a part by {definition}"


def test_the_configured_product_specializes_the_s_core_integrated_member() -> None:
    """ADR 0023, decision 8: once the scope admits the member, the configured product that phase 9 added for
    MW-CONFIG-002 specializes the new member definition, as the AAOS-integrated configured member does
    (tests/test_member_product_projections.py). It also specializes the kernel's ProductLineConfiguredProduct, the
    configured product of phase 9 (owner decision of 2026-10-29). The member definition is the scope's."""
    code = _code(SLICE)
    found = [", ".join(re.split(r"\s*,\s*", generals))
             for generals in re.findall(r":>(?!>)\s*([\w:]+(?:\s*,\s*[\w:]+)*)", code)]
    assert found == [f"{MEMBER}, ProductLineConfiguredProduct"]
    assert not re.search(r"\bspecializes\b", code)
    assert "ProductLineMemberProduct" not in code, "the member definition carries the member lineage"
    assert re.search(r"\bpart\s+def\s+SCOREIntegratedAutowareAEBSReferenceMember\s*:>\s*ProductLineMemberProduct\b",
                     _code(SCOPE))
    docs = _docs(SLICE)
    for phrase in ("The governed scope admits the configuration since the scope revision of ADR 0023 and ADR 0026: "
                   "it realizes the alternative S-CORE Integrated, and its configured product specializes the member "
                   "definition SCOREIntegratedAutowareAEBSReferenceMember.",
                   "The owner accepted the member on 2026-11-13 (ADR 0023), before the runnable proof of phase 10. "
                   "That proof stays an obligation of phase 10: it is evidence about the member, not a condition of "
                   "its membership.",
                   "The definition specializes the member definition SCOREIntegratedAutowareAEBSReferenceMember of "
                   "the governed scope (ADR 0023, decision 8), as the AAOS-integrated configured member specializes "
                   "its member definition."):
        assert phrase in docs, phrase
    for stale in ("specializes no member-product type", "The member decision is phase-12 work",
                  "If the owner admits the member in phase 12", "It stays a phase-12 decision", "C007 to C010"):
        assert stale not in docs, stale


def test_cls_mw_004_has_both_integrated_alternatives_as_its_counterpart() -> None:
    """Owner decision of 2026-11-21 (ADR 0023, decision 3): since ADR 0026 the AAOS-integrated member also holds the
    HMI display in its AAOS SDV guest, so the counterpart of CLS-MW-004 is both integrated alternatives, one
    dependency each, in the form of the feature model's correspondences. It replaces the choice of 2026-10-21."""
    code = _code(CLASSIFICATION)
    found = re.findall(r"\bdependency\s+(\w+)\s+from\s+hmiGuestExecutionDomain\s+to\s+([\w:]+)\s*;", code)
    assert found == [(name, f"DE4SDV_AEBSProductLineScope::vehiclePlatformIntegrationMode::{alternative}")
                     for name, alternative in COUNTERPARTS.items()]
    assert len(re.findall(r"\bfrom\s+hmiGuestExecutionDomain\b", code)) == len(COUNTERPARTS)
    for alternative in COUNTERPARTS.values():
        assert re.search(rf"\bvariant\s+part\s+{alternative}\s*:", _code(SCOPE)), alternative
    candidate = _docs(CLASSIFICATION)
    for phrase in ("CLS-MW-004: an AAOS SDV HMI guest next to the Linux host distinguishes the two integrated members "
                   "from the standalone member.",
                   "Its counterpart is both integrated alternatives, AAOS Integrated and S-CORE Integrated (owner "
                   "decision of 2026-11-21)."):
        assert phrase in candidate, phrase
    assert "the AAOS-integrated mode is only a candidate counterpart, and the ADR decides" not in candidate
    comment = _docs(SLICE)
    for phrase in ("The owner decided on 2026-11-21 that the counterpart of CLS-MW-004 is both integrated "
                   "alternatives, AAOS Integrated and S-CORE Integrated.",
                   "This replaces the decision of 2026-10-21, made before ADR 0026, to re-point it to S-CORE "
                   "Integrated alone.",
                   "eclipseSCORE, not hmiDisplay, tells the S-CORE member apart from the AAOS-integrated member."):
        assert phrase in comment, phrase
    assert "only hmiDisplay distinguishes the S-CORE product" not in comment
    text = SLICE.read_text(encoding="utf-8")
    (about,) = re.findall(r"\bcomment hmiGuestCandidateCounterpartAtBaseline\s+about\s+([^/]*)/\*", text)
    assert [name.strip() for name in about.split(",")] == [
        "DE4SDV_MiddlewareSCOREFeatureClassification::hmiGuestExecutionDomain",
        *(f"DE4SDV_MiddlewareSCOREFeatureClassification::{name}" for name in COUNTERPARTS)]


def test_mw_config_002_is_bound_to_the_exact_receipt() -> None:
    """The phase-10 evidence binds MW-CONFIG-002, so a receipt re-cut keeps the identity and rebinds
    receiptSha256 in the slice. The slice states what counts as a change of the configuration's own receipt record
    (decision of 2026-11-17)."""
    text = SLICE.read_text(encoding="utf-8")
    holders = sorted(path.relative_to(ROOT).as_posix() for root in MODEL_ROOTS for path in root.rglob("*.sysml")
                     if "<'MW-CONFIG-002'>" in path.read_text(encoding="utf-8"))
    assert holders == [SLICE.relative_to(ROOT).as_posix()]
    assert re.search(r"\bpart <'MW-CONFIG-002'> configuredProduct : MiddlewareAutowareSCOREConfiguredProduct\s*\{",
                     text)
    (bound,) = re.findall(r'\battribute receiptSha256 : ScalarValues::String = "([0-9a-f]{64})";', text)
    (header,) = re.findall(r"^ \* Receipt SHA-256: ([0-9a-f]{64})$", PROJECTION.read_text(encoding="utf-8"), re.M)
    committed = hashlib.sha256(RECEIPT.read_bytes()).hexdigest()
    assert bound == header == committed, (
        f"MW-CONFIG-002 binds the receipt {bound}, the projection names {header}, and the committed receipt "
        f"is {committed}: rebind receiptSha256 of MW-CONFIG-002 to the new receipt, and state in the pull "
        f"request whether the configuration's own receipt record changed")
    docs = " ".join(re.sub(r"^\s*\*\s?", "", text, flags=re.M).split())
    assert ("The pull request that rebinds it states whether the configuration's own receipt record changed. By "
            "the decision of 2026-11-17, the record has not changed when its only difference is added states omitted "
            "for features that it does not select, and every other entry is the same: validity, reasons, derived "
            "variants with their variant ids, admission, the selected features, projection name, source, description "
            "and element id."
            ) in docs, "MW-CONFIG-002 no longer states what counts as a change of its own receipt record"


def test_the_receipt_records_what_the_configured_product_states() -> None:
    """Valid, the derived adapter autowareToSCORE, not admitted, the guest side and the HMI display."""
    [model] = json.loads(RECEIPT.read_text(encoding="utf-8"))["evaluation"]["feature_models"]
    [configuration] = [item for item in model["configurations"] if item["source"] == CONFIGURATION]
    assert configuration["configuration"] == "middlewareAutowareSCOREReference"
    assert configuration["projection_name"] == "MiddlewareAutowareSCOREReference"
    assert configuration["valid"] is True
    assert configuration["admission"]["admitted"] is False
    derived = {item["variation"]: item["variant"] for item in configuration["derived_variants"]}
    assert derived["applicationMiddlewareAdapter"] == "autowareToSCORE"
    assert {"platformStack.autoware", "platformStack.eclipseSCORE", "platformStack.linux", "platformStack.kvm",
            "platformStack.guestAndroid", "platformStack.guestAndroidSDV",
            "capabilities.hmiDisplay"} <= set(configuration["selected"])


def test_the_layer_adapter_is_typed_by_the_derived_adapter_variant() -> None:
    """The process that REQ-MW-018 names is typed by the definition of the derived variant."""
    realization = _body(_code(PHYSICAL), r"\bpart\s+def\s+SCOREMiddlewareIntegrationLayerRealization\b[^{;]*\{")
    assert re.search(r"\bref part adapter : PhysicalAllocationElement, AutowareToSCOREAdapter\s*\{", realization)


def test_the_hmi_path_requirements_depend_on_the_hmi_display() -> None:
    """Rule 5: one dependency for each HMI-path requirement, declared with the requirements."""
    code = _code(NEEDS)
    found = re.findall(rf"\bdependency (\w+)\s+from (\w+)\s+to {re.escape(HMI_DISPLAY)};", code)
    assert sorted(found) == sorted((f"{requirement}OnHMIDisplay", requirement) for requirement in HMI_PATH_REQUIREMENTS)
    assert code.count("hmiDisplay") == len(HMI_PATH_REQUIREMENTS)
    text = NEEDS.read_text(encoding="utf-8")
    for requirement, identifier in HMI_PATH_REQUIREMENTS.items():
        assert re.search(rf"\brequirement <'{identifier}'> {requirement} :", text)


def test_no_feature_model_or_configuration_document_names_an_increment_requirement() -> None:
    """A requirement-to-feature dependency inside a feature-model document makes the evaluator refuse."""
    for folder in ("feature-models", "feature-configurations"):
        for path in sorted((PLE / folder).rglob("*.sysml")):
            assert "DE4SDV_MiddlewareSCORENeedsRequirements" not in path.read_text(encoding="utf-8"), path


def test_the_charter_names_the_phase_9_package() -> None:
    (artifacts,) = re.findall(r"attribute :>> expectedArtifacts = \(([^)]*)\);", FRAMING.read_text(encoding="utf-8"))
    assert '"DE4SDV_MiddlewareSCOREVariabilityConfiguration"' in artifacts
    assert re.search(r"\bpackage DE4SDV_MiddlewareSCOREVariabilityConfiguration\s*\{", _code(SLICE))
