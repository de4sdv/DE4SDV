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


#: A feature in these texts is a feature of a PLEML feature model (review R2).
PLEML_FEATURE = "Feature here means a feature of a PLEML feature model, not the ontology class Feature"


def test_the_definitions_state_the_closed_world_the_evaluator_implements():
    """The shape the evaluator (S2) implements and the feature models (S3)
    author: one client, how each premise maps to its source feature, no
    supplier order, no rule outside a derived variation (review R1 to R3)."""
    derived = _first_doc("DerivedVariation")
    for clause in ("Declares that a shared-asset variation is derived",
                   "Applied to a dependency with exactly one client, the variation, whose suppliers are its "
                   "source features",
                   "Supplier order carries no meaning",
                   "exactly one of its rules must match",
                   "a configuration that matches no rule or several is rejected",
                   "never a feature and never a manual product choice",
                   "a feature binding or configuration entry that targets one is refused",
                   "The short name of the dependency is the stable identity of the derivation",
                   PLEML_FEATURE):
        assert clause in derived, clause
    rule = _first_doc("DerivationRule")
    for clause in ("Applied to a dependency with exactly one client, that variant, whose suppliers are the premises",
                   "one premise per source feature of the variation, each a direct sub-feature of a distinct "
                   "source feature, that is, a feature of the feature model with an authored subsetting of it",
                   "Supplier order carries no meaning",
                   "The client is a variant of a variation that exactly one derived variation names; a rule "
                   "without one is invalid",
                   "The rule matches a valid configuration that selects every premise",
                   "derivation applies to valid configurations only"):
        assert clause in rule, clause
    assert "The names identify nothing" in _first_doc("ProductModelProjection")
    assert "is not one of its features" in _first_doc("ProductModelProjectionName")
    unassigned = _first_doc("UnassignedBindingTime")
    for clause in ("the binding time of the annotated feature of the feature model is not yet decided",
                   "no configuration verdict depends on the annotation",
                   "An annotated feature does not redefine bindingTime; a feature that does both is refused",
                   "never carries this annotation",
                   PLEML_FEATURE):
        assert clause in unassigned, clause


def test_the_header_keeps_the_pre_switch_authority_fence():
    header = " ".join(_source().split("package DE4SDV_ProductLineDerivation", 1)[0].replace("*", " ").split())
    assert "until the switch of ADR 0022, the YAML catalogue and the configurator remain the derivation authority" in header
    assert "(ADR 0006 decision 6)" in header and "only the fenced feature models apply these definitions" in header
    assert "a repository test refuses any file of the model roots that imports this package or applies them" in header
    assert ("In these definitions a feature is a feature of a PLEML feature model, not the ontology class Feature "
            "(kernel ProductLineFeatureCandidate); the ontology pull request before the switch (S5o) decides "
            "that boundary") in header


#: The model roots that ingestion exports and serves (the production selectors).
MODEL_ROOTS = ("textual-notation-of-model", "model-based-product-line-engineering/product-models",
               "model-based-product-line-engineering/scoping")
#: An import or qualified use of the package, or an application of one of its
#: definitions: prefix or body metadata (#Name, @Name) or a named metadata usage.
_APPLIES = re.compile(
    r"\bDE4SDV_ProductLineDerivation\b"
    r"|[#@]\s*(?:" + "|".join(SHAPES) + r")\b"
    r"|\bmetadata\s+\w+\s*:\s*(?:[\w:]*::)?(?:" + "|".join(SHAPES) + r")\b")


def _model_root_files_applying_the_kernel(root: Path) -> list[str]:
    found = []
    for model_root in MODEL_ROOTS:
        for path in sorted((root / model_root).rglob("*.sysml")):
            relative = path.relative_to(root).as_posix()
            if relative != DERIVATION and _APPLIES.search(strip_comments(path.read_text(encoding="utf-8"))):
                found.append(relative)
    return found


def test_until_the_switch_no_model_root_file_applies_the_derivation_kernel():
    """ADR 0022 fence (review R4): until the switch, only the fenced feature
    models outside the model roots, and synthetic test fixtures, import this
    package or apply its definitions. A file of the model roots that does is
    refused, so the served model cannot apply the derivation kernel before
    the switch. The switch rewrites this guard together with the header."""
    assert _model_root_files_applying_the_kernel(ROOT) == []


@pytest.mark.parametrize("text", [
    "package P { private import DE4SDV_ProductLineDerivation::*; }",
    "package P { #DerivedVariation dependency d from a to b, c; }",
    "package P { #DE4SDV_ProductLineDerivation::DerivationRule dependency r from a to b; }",
    "package P { occurrence def M { @ProductModelProjection { packageName = \"P\"; } } }",
    "package P { occurrence c { metadata name : ProductModelProjectionName; } }",
    "package P { #UnassignedBindingTime occurrence f; }",
])
def test_the_fence_guard_refuses_a_planted_model_root_file(tmp_path, text):
    planted = tmp_path / "textual-notation-of-model/packages/features/probe/probe.sysml"
    planted.parent.mkdir(parents=True)
    planted.write_text(text + "\n", encoding="utf-8")
    fenced = tmp_path / "model-based-product-line-engineering/feature-models/probe.sysml"
    fenced.parent.mkdir(parents=True)
    fenced.write_text(text + "\n", encoding="utf-8")
    assert _model_root_files_applying_the_kernel(tmp_path) == [
        "textual-notation-of-model/packages/features/probe/probe.sysml"]


@pytest.mark.parametrize("name", sorted(SHAPES))
def test_every_definition_is_an_ontology_class_bound_like_the_kernel(name):
    import json

    contract = model_contract()
    assert contract.classes[name]["kernel"] == {"file": DERIVATION, "declaration": f"metadata def {name}"}
    row = {r["identity"]: r for r in json.loads((ROOT / PROJECTION).read_text())["rows"]}[name]
    # S5o: these rows share the PLE boundary; none of them carries configurator authority.
    assert (row["accounting"], row["admission_class"], row["boundary"]) == (
        "method-admitted", "definition", "ple-no-configurator-authority")
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
