"""INC-MW-011 phase 9: the configured product MW-CONFIG-002 of the Eclipse S-CORE configuration.

The configured product pairs the platform-stack projection that the configurator
generates from the receipt with the realization of the middleware integration
layer. It holds one instance per platform layer by identity (two bindings), it is
no member product before the phase-12 decision, and MW-CONFIG-002 is bound to the
exact receipt. Under
rule 5 of the increment workflow, the four HMI-path requirements depend on the
HMI display, declared with the requirements and outside the feature-model and
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


def _product_body() -> str:
    return _body(_code(SLICE), r"\bpart\s+def\s+MiddlewareAutowareSCOREConfiguredProduct\s*\{")


def test_the_configured_product_pairs_the_projection_with_the_layer_realization() -> None:
    body = _product_body()
    own = _own(body)
    assert "part platformStack : MiddlewareAutowareSCOREReference;" in own
    assert "part integrationLayer : SCOREMiddlewareIntegrationLayerRealization " in own
    layer = _body(body, r"\bpart\s+integrationLayer\s*:\s*SCOREMiddlewareIntegrationLayerRealization\s*\{")
    assert " ".join(layer.split()) == "{ ref part :>> scoreServices; ref part :>> adapter; }"


def test_the_configured_product_holds_one_instance_per_platform_layer() -> None:
    """Two bindings make the S-CORE services and the adapter of the layer the same things as the
    selected middleware and the derived adapter of the platform stack (identity). The product body
    declares exactly two parts and exactly these two bindings."""
    own = _own(_product_body())
    assert re.findall(r"\b(?:ref\s+)?part\s+(\w+)\s*:", own) == ["platformStack", "integrationLayer"]
    assert re.findall(r"\bbinding\s+(\w+)\s+bind\b", own) == [
        "scoreServicesBoundToSelectedMiddleware", "adapterBoundToDerivedAdapter"]
    assert len(re.findall(r"\bbind\b", own)) == 2, "a further binding in the product body"
    assert ("binding scoreServicesBoundToSelectedMiddleware bind "
            "integrationLayer.scoreServices = platformStack.middleware;") in own
    assert ("binding adapterBoundToDerivedAdapter bind "
            "integrationLayer.adapter = platformStack.applicationMiddlewareAdapter;") in own
    code = _code(SLICE)
    for definition in LAYER_DEFINITIONS:
        assert not re.search(_TYPED_BY.format(definition=definition), code), f"the slice types a part by {definition}"


def test_the_configured_product_is_no_member_product_before_phase_12() -> None:
    """Until the phase-12 decision it specializes no member-product type (tests/test_member_product_projections.py)."""
    code = _code(SLICE)
    assert re.search(r"\bpart\s+def\s+MiddlewareAutowareSCOREConfiguredProduct\s*\{", code)
    assert not re.search(r"(?::>(?!>)|\bspecializes\b)", code)
    assert "ProductLineMemberProduct" not in code


def test_mw_config_002_is_bound_to_the_exact_receipt() -> None:
    """The phase-10 evidence binds MW-CONFIG-002, so a receipt re-cut keeps the identity and rebinds
    receiptSha256 in the slice."""
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
    """REQ-MW-018 traces to the derived variant through the adapter process."""
    realization = _body(_code(PHYSICAL), r"\bpart\s+def\s+SCOREMiddlewareIntegrationLayerRealization\b[^{;]*\{")
    assert re.search(r"\bpart adapter : PhysicalAllocationElement, AutowareToSCOREAdapter\s*\{", realization)


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
