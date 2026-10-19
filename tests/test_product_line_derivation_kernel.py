"""Product-line derivation kernel (ADR 0022, step S2k): the shapes that the
feature models and the evaluator rely on.

Lexical source checks and the model-built contract. The licensed validation
of the definitions runs in CI; the binding test below is synthetic and proves
the ingestion rule (ADR 0011), not a licensed export.
"""
from pathlib import Path
import re

import pytest

from de4sdv.semantic.validation import validate_ontology_bindings
from model_contract_fixtures import model_contract
from sysml_shapes import braced_body, strip_comments

ROOT = Path(__file__).resolve().parents[1]
DERIVATION = "textual-notation-of-model/packages/methods/de4sdv/de4sdv_product_line_derivation.sysml"
PROJECTION = "de4sdv/semantic/contract-data/kernel-vocabulary-projection.json"
OCCURRENCES = ("SysML::OccurrenceDefinition", "SysML::OccurrenceUsage")
#: Definition -> (metaclasses it may annotate, attributes and their types).
SHAPES = {
    "DerivedVariation": (("SysML::Dependency",), {}),
    "DerivationRule": (("SysML::Dependency",), {}),
    "ProductModelProjection": (OCCURRENCES, {"packageName": "String", "ownerName": "String", "label": "String"}),
    "ProductModelProjectionName": (OCCURRENCES, {"partDefinitionName": "String"}),
    "UnassignedBindingTime": (OCCURRENCES, {}),
}
#: The selectable product-line classes of the ADR 0006 kernel guard.
SELECTABLES = ("ProductLineFeatureCandidate", "CommonProductLineCapability", "ProductLineMemberProduct",
               "ProductLineVariantChoice", "DeferredVariantChoice", "ProductLineCharacteristic")


def _source() -> str:
    return (ROOT / DERIVATION).read_text(encoding="utf-8")


def _active() -> str:
    return strip_comments(_source())


def _first_doc(name: str) -> str:
    body = braced_body(_source(), f"metadata def {name}")
    match = re.search(r"\bdoc\s*/\*(.*?)\*/", body, re.S)
    assert match, name
    return " ".join(match.group(1).replace("*", " ").split())


def test_the_package_declares_exactly_the_five_metadata_definitions():
    active = _active()
    assert re.findall(r"\bpackage\s+(\w+)", active) == ["DE4SDV_ProductLineDerivation"]
    assert sorted(re.findall(r"\bdef\s+(\w+)", active)) == sorted(SHAPES)
    assert sorted(re.findall(r"\bmetadata\s+def\s+(\w+)", active)) == sorted(SHAPES)


@pytest.mark.parametrize("name", sorted(SHAPES))
def test_each_definition_keeps_its_pinned_shape(name):
    metaclasses, attributes = SHAPES[name]
    active = _active()
    # Plain metadata: no specialization, so applying it never adds a typing
    # (a feature configuration keeps owning only features).
    assert re.search(r"\bmetadata\s+def\s+" + name + r"\s*\{", active), name
    body = braced_body(active, f"metadata def {name}")
    assert re.findall(r":>\s*annotatedElement\s*:\s*([\w:]+)\s*;", body) == list(metaclasses), name
    assert dict(re.findall(r"\battribute\s+(\w+)\s*:\s*([\w:]+)", body)) == attributes, name
    for keyword in ("ref", "part", "item", "occurrence", "variation", "variant", "constraint", ":>>"):
        assert not re.search(r"(?<![\w:])" + re.escape(keyword) + r"(?![\w>])", body), (name, keyword)


def test_the_package_imports_no_pleml_and_holds_no_selection_record():
    """ADR 0022 confines PLEML imports to the feature models; the ADR 0006
    guard on the product-line kernel holds here as well: no reference feature,
    no feature typed by a selectable product-line class, no configuration,
    variation-point or variant definition and no semantic metadata."""
    active = _active()
    assert re.findall(r"\bimport\s+([\w:*]+)\s*;", active) == ["ScalarValues::String"]
    assert "PLEML" not in active
    assert not re.search(r"\bref\b", active)
    assert not re.search(r"(?::|\b(?:defined|typed)\s+by)\s*(?:[\w:]*::)?(?:" + "|".join(SELECTABLES) + r")\b", active)
    assert not re.search(r"\bdef\s+(FeatureConfiguration|VariationPoint|Variant)\b", active)
    assert "SemanticMetadata" not in active and "baseType" not in active


def test_no_kernel_evidence_status_type():
    """OQ3: configuration evidence status stays an external typed reference
    until the ontology review's decision-4 is decided."""
    active = _active()
    assert not re.search(r"\benum\s+def\b", active)
    assert not [name for name in re.findall(r"\bdef\s+(\w+)", active) if re.search("status|evidence", name, re.I)]


def test_the_definitions_state_the_closed_world_the_evaluator_implements():
    derived = _first_doc("DerivedVariation")
    for clause in ("whose client is the variation and whose suppliers are its source features",
                   "exactly one of its rules must match",
                   "a configuration that matches no rule or several is rejected",
                   "never a feature and never a manual product choice",
                   "a feature binding or configuration entry that targets one is refused",
                   "The short name of the dependency is the stable identity of the derivation"):
        assert clause in derived, clause
    rule = _first_doc("DerivationRule")
    for clause in ("whose client is that variant and whose suppliers are the premises",
                   "one alternative of each source feature of the variation",
                   "matches a configuration that selects every premise",
                   "Derivation applies to valid configurations only"):
        assert clause in rule, clause
    assert "The names identify nothing" in _first_doc("ProductModelProjection")
    assert "is not one of its features" in _first_doc("ProductModelProjectionName")
    unassigned = _first_doc("UnassignedBindingTime")
    assert "no configuration verdict depends on the annotation" in unassigned
    assert "never carries this annotation" in unassigned


def test_the_header_keeps_the_pre_switch_authority_fence():
    header = " ".join(_source().split("package DE4SDV_ProductLineDerivation", 1)[0].replace("*", " ").split())
    assert "until the switch of ADR 0022, the YAML catalogue and the configurator remain the derivation authority" in header
    assert "(ADR 0006 decision 6)" in header and "only the fenced feature models apply these definitions" in header


@pytest.mark.parametrize("name", sorted(SHAPES))
def test_every_definition_is_an_ontology_class_bound_like_the_kernel(name):
    import json

    contract = model_contract()
    assert contract.classes[name]["kernel"] == {"file": DERIVATION, "declaration": f"metadata def {name}"}
    row = {r["identity"]: r for r in json.loads((ROOT / PROJECTION).read_text())["rows"]}[name]
    assert (row["accounting"], row["admission_class"], row["boundary"]) == ("method-admitted", "definition", "none")
    assert (row["support"], row["traversal"], row["api_identity"]) == ("vocabulary-only", False, "unclaimed")
    assert row["definition"]["documentation"] == _first_doc(name)


def test_ingestion_binds_each_definition_by_metatype_name_and_this_file():
    """ADR 0011: a validated binding needs the metatype, the declared name and
    this source file; a same-named element of another file or type is never
    bound, so a name alone identifies nothing."""
    contract = model_contract()
    elements, sources = [], {}

    def add(identifier, kind, name, source):
        elements.append({"@id": identifier, "@type": kind, "declaredName": name})
        sources[identifier] = source

    for name in SHAPES:
        add(f"kernel-{name}", "MetadataDefinition", name, DERIVATION)
        add(f"elsewhere-{name}", "MetadataDefinition", name, "model-based-product-line-engineering/feature-models/x.sysml")
        add(f"wrong-kind-{name}", "PartDefinition", name, DERIVATION)
    entries = {e.ontology_class: e for e in validate_ontology_bindings(contract, elements, sources).entries}
    for name in SHAPES:
        assert (entries[name].status, entries[name].element_ids) == ("mapped", (f"kernel-{name}",)), name
        assert entries[name].api_type == "MetadataDefinition"
    decoys = [e for e in elements if not e["@id"].startswith("kernel-")]
    entries = {e.ontology_class: e for e in validate_ontology_bindings(
        contract, decoys, {e["@id"]: sources[e["@id"]] for e in decoys}).entries}
    for name in SHAPES:
        assert entries[name].status == "unresolved", name
