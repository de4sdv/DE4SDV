"""O4 Wave A (A3): vocabulary roles, native grounding records, validation-rule
homes and the pilot-query fixture.

These are lexical source checks, not licensed Syside evidence.
"""
from pathlib import Path
import re

import yaml

from de4sdv.semantic.authority_inventory import normalize_text
from model_contract_fixtures import contract_equivalence_evidence, model_contract

ROOT = Path(__file__).resolve().parents[1]
KERNEL = "textual-notation-of-model/packages/methods/de4sdv/"
PRODUCT_LINE = KERNEL + "de4sdv_product_line.sysml"
CONTEXT = KERNEL + "de4sdv_method_context.sysml"
VIEWPOINTS = KERNEL + "de4sdv_method_concerns_and_viewpoints.sysml"
RULES = KERNEL + "de4sdv_ontology_validation_rules.sysml"
PILOT_FIXTURE = "tests/fixtures/ontology/pilot_queries.yaml"

ADR_0006_BOUNDARY = "No configurator authority; selection authority stays with the external catalogue (ADR 0006)"

# identity -> (file, annotated element, kernel names of domain and range)
VOCABULARY_ROLES = {
    "specifiesFeature": (PRODUCT_LINE, "ProductLineFeatureCandidate", ("RequirementCandidate", "ProductLineFeatureCandidate")),
    "specifiesCommonCapability": (PRODUCT_LINE, "CommonProductLineCapability", ("RequirementCandidate", "CommonProductLineCapability")),
    "variesAt": (PRODUCT_LINE, "ProductLineFeatureCandidate", ("ProductLineFeatureCandidate", "VariationPointOntologyDefinition")),
    "appliesToMemberProduct": (PRODUCT_LINE, "FeatureConfigurationOntologyDefinition", ("FeatureConfiguration", "ProductLineMemberProduct")),
    "selectsFeature": (PRODUCT_LINE, "FeatureConfigurationOntologyDefinition", ("FeatureConfiguration", "ProductLineFeatureCandidate")),
    "includesCommonCapability": (PRODUCT_LINE, "FeatureConfigurationOntologyDefinition", ("FeatureConfiguration", "CommonProductLineCapability")),
    "selectsVariant": (PRODUCT_LINE, "FeatureConfigurationOntologyDefinition", ("FeatureConfiguration", "VariantOntologyDefinition")),
    "usesVerificationMethod": (CONTEXT, "VerificationMethodOntologyDefinition", ("VerificationCase", "VerificationMethod")),
}
PLE_CONFIGURATION_ROLES = {"appliesToMemberProduct", "selectsFeature", "includesCommonCapability", "selectsVariant"}


def _text(path):
    return (ROOT / path).read_text()


def _domain_range(identity):
    """Reviewed domain/range: the model contract's projection spec, or (for the
    O2+ row usesVerificationMethod, whose domain/range text is not projected)
    the authored values recorded by the pre-deletion evidence."""
    spec = model_contract().relationships[identity]
    if spec.get("domain") and spec.get("range"):
        return spec["domain"], spec["range"]
    authored = contract_equivalence_evidence()["authored_contract"]["differences"][identity]["authored"]
    return authored["domain_range"]["domain"], authored["domain_range"]["range"]


def _flat(text):
    return " ".join(text.replace("*", " ").split())


def _named_comments(text):
    return {
        name: (targets, body)
        for name, targets, body in re.findall(r"\bcomment\s+(\w+)\s+about\s+([\w\s,:]+?)\s*/\*(.*?)\*/", text, re.S)
    }


def _anonymous_comments_about(text, target):
    return [_flat(body) for body in re.findall(r"\bcomment\s+about\s+" + re.escape(target) + r"\s*/\*(.*?)\*/", text, re.S)]


def _active(text):
    return re.sub(r"/\*.*?\*/|//[^\n]*", " ", text, flags=re.S)


def test_relationship_vocabulary_roles_are_anchored_and_claim_no_traversal():
    for identity, (path, target, (domain, range_)) in VOCABULARY_ROLES.items():
        comments = _named_comments(_text(path))
        name = identity + "VocabularyRole"
        assert name in comments, identity
        targets, body = comments[name]
        assert [t.strip() for t in targets.split(",")] == [target], identity
        body = _flat(body)
        reviewed_domain, reviewed_range = _domain_range(identity)
        # The comment restates the reviewed domain/range identities and their
        # kernel names; it must not invent a different signature.
        assert f"relationship {identity}" in body, identity
        assert f"domain {reviewed_domain}" in body and f"range {reviewed_range}" in body, identity
        for kernel_name in (domain, range_):
            assert kernel_name in body, (identity, kernel_name)
        assert "no sysml_mapping" in body and "no runtime traversal" in body, identity
        # Vocabulary only: the model contract declares no executable mapping either.
        assert "sysml_mapping" not in model_contract().relationships[identity], identity


def test_ple_configuration_rows_keep_adr_0006_external_selection_authority():
    text = _text(PRODUCT_LINE)
    comments = _named_comments(text)
    for identity in PLE_CONFIGURATION_ROLES | {"FeatureConfiguration"}:
        targets, body = comments[identity + "VocabularyRole"]
        assert targets.strip() == "FeatureConfigurationOntologyDefinition", identity
        body = _flat(body)
        assert ADR_0006_BOUNDARY in body and "Vocabulary only" in body, identity
        assert "PLEML" in body, identity
    assert "decision-9" in _flat(comments["FeatureConfigurationVocabularyRole"][1])
    # No model-side configuration authority: no FeatureConfiguration, variation-point
    # or variant definition anywhere in the governed kernel directory.
    for path in sorted((ROOT / KERNEL).glob("*.sysml")):
        active = _active(path.read_text())
        assert not re.search(r"\bdef\s+(FeatureConfiguration|VariationPoint|Variant)\b", active), path.name
    assert "external" in model_contract().classes["FeatureConfiguration"]["kernel"]


def test_native_rows_record_library_grounding_without_copying_library_types():
    viewpoints = _text(VIEWPOINTS)
    grounding = {
        "ConcernOntologyDefinition": "concern def ConcernCheck",
        "ViewpointOntologyDefinition": "viewpoint def ViewpointCheck",
        "ViewOntologyDefinition": "abstract view def View",
    }
    for doc_name, library_element in grounding.items():
        bodies = _anonymous_comments_about(viewpoints, doc_name)
        assert any(body.startswith("Grounding: Systems Library") and library_element in body for body in bodies), doc_name
    context = _text(CONTEXT)
    method_bodies = _anonymous_comments_about(context, "VerificationMethodOntologyDefinition")
    record = [body for body in method_bodies if body.startswith("Grounding record")]
    assert len(record) == 1
    for phrase in ("metadata def VerificationMethod", "VerificationMethodKind", "verificationMethod", "Two distinct carriers"):
        assert phrase in record[0], phrase
    # Library types are referenced, never redeclared in the kernel.
    for path in sorted((ROOT / KERNEL).glob("*.sysml")):
        active = _active(path.read_text())
        assert not re.search(r"\bdef\s+(ConcernCheck|ViewpointCheck|View|VerificationMethod|VerificationMethodKind|Concern|Viewpoint)\b", active), path.name


def test_increment_size_stays_vocabulary_only_guidance():
    text = _text(RULES)
    targets, body = _named_comments(text)["IncrementSizeVocabularyRole"]
    assert targets.strip() == "IncrementSize"
    assert "private import DE4SDV_MethodProcess::*;" in text
    body = _flat(body)
    assert "Vocabulary only" in body and "never promoted to semantic authority" in body


def _rule_blocks(text):
    blocks = {}
    for match in re.finditer(r"\bconstraint\s+(ontologyRule\w+)\s*\{", text):
        depth, start = 0, match.end() - 1
        for token in re.finditer(r"/\*.*?\*/|[{}]", text[start:], re.S):
            if token[0] == "{":
                depth += 1
            elif token[0] == "}":
                depth -= 1
                if depth == 0:
                    blocks[match[1]] = text[start + 1:start + token.start()]
                    break
    return blocks


def test_every_validation_rule_has_one_faithful_model_home():
    # The authored rules as recorded by the pre-deletion evidence (O4 Wave C2).
    rules = contract_equivalence_evidence()["authored_validation_rules"]["rules"]
    text = _text(RULES)
    blocks = _rule_blocks(text)
    expected = {"ontologyRule" + rule["id"].split("-")[-1]: rule for rule in rules}
    assert len(rules) == 10 and set(blocks) == set(expected)
    for name, rule in expected.items():
        block = blocks[name]
        docs = re.findall(r"\bdoc\s*/\*(.*?)\*/", block, re.S)
        assert normalize_text(docs[0]) == normalize_text(rule["statement"]), name
        assert normalize_text(docs[1]) == normalize_text(f"Rule {rule['id']}. Enforced by: {rule['enforced_by']}"), name
        # A rule home is a declaration only: no expression, no assertion.
        assert not _active(block).strip(" \n;").replace("doc", "").replace("comment", "").strip(), name
    r003 = _flat(re.findall(r"\bdoc\s*/\*(.*?)\*/", blocks["ontologyRuleR003"], re.S)[2])
    rule = expected["ontologyRuleR003"]
    for kind in ("origin_groundings", "exclusion_groundings"):
        for concept, grounding in rule[kind].items():
            assert f"{concept}: {grounding['declaration']} in {grounding['file']}" in r003, concept
    # The rule homes are never asserted or specialized elsewhere.
    for root in ("textual-notation-of-model", "model-based-product-line-engineering"):
        for path in (ROOT / root).rglob("*.sysml"):
            if path != ROOT / RULES:
                assert "ontologyRule" not in path.read_text(), path


def test_rule_homes_add_no_kernel_declarations():
    active = _active(_text(RULES))
    assert not re.search(r"\bdef\b", active)


def test_pilot_query_fixture_is_the_pilot_query_home():
    """Replaces ``test_pilot_query_fixture_equals_the_ontology_block``: the
    authored YAML block was deleted in O4 Wave C2; the fixture is the home."""
    fixture = yaml.safe_load(_text(PILOT_FIXTURE))
    assert list(fixture) == ["pilot_queries"]
    assert len(fixture["pilot_queries"]) == 8 and all(isinstance(q, str) and q for q in fixture["pilot_queries"])


MODEL_ROOTS = ("textual-notation-of-model", "model-based-product-line-engineering")


def _model_files():
    for root in MODEL_ROOTS:
        yield from sorted((ROOT / root).rglob("*.sysml"))


def _blank_comment_bodies(text):
    """Keep comment delimiters, drop comment interiors and line comments."""
    return re.sub(r"/\*.*?\*/", "/**/", re.sub(r"//[^\n]*", "", text), flags=re.S)


def test_vocabulary_role_names_are_unique_and_kernel_resident():
    """A homonym role (same name in a second file or twice in one file) would
    let a dict-based reader silently pick either body."""
    homes = {}
    for path in _model_files():
        for name in re.findall(r"\bcomment\s+(?!about\b)(\w+VocabularyRole)\b", _blank_comment_bodies(path.read_text())):
            homes.setdefault(name, []).append(path.relative_to(ROOT).as_posix())
    assert len(homes) >= 23, "the scan must see the kernel's vocabulary roles"
    duplicated = {name: files for name, files in homes.items() if len(files) != 1}
    assert not duplicated, duplicated
    assert all(files[0].startswith(KERNEL) for files in homes.values()), homes


def test_rule_homes_are_declared_once_and_never_asserted_anywhere():
    """Every ``ontologyRule*`` token in every model file, the rules file
    included, is exactly its one bare constraint declaration."""
    occurrences = []
    for path in _model_files():
        active = _active(path.read_text())
        for match in re.finditer(r"ontologyRule\w*", active):
            line_start = active.rfind("\n", 0, match.start()) + 1
            occurrences.append((path, active[line_start:match.end() + 2].strip(), match[0]))
    declarations = [(path, name) for path, line, name in occurrences
                    if re.fullmatch(r"constraint\s+" + name + r"\s*\{", line)]
    assert len(declarations) == len(occurrences) == 10, [o[1] for o in occurrences]
    assert {path for path, _ in declarations} == {ROOT / RULES}
    assert len({name for _, name in declarations}) == 10
    active = _active(_text(RULES))
    for keyword in ("assert", "satisfy", "require", "assume", "part", "ref", ":>", "subsets", "redefines"):
        assert not re.search(r"(?<![\w:])" + re.escape(keyword) + r"(?![\w>])", active), keyword


PRODUCT_LINE_DEFINITIONS = {
    "ProductLine", "SDVProductLine", "ProductLineMemberProduct", "ProductLineCharacteristic",
    "CommonProductLineCapability", "ProductLineFeatureCandidate", "DeferredProductLineScope",
    "ProductLineVariantChoice", "DeferredVariantChoice", "DeferredProductLineVariation",
}
PLE_SELECTABLES = ("ProductLineFeatureCandidate", "CommonProductLineCapability", "ProductLineMemberProduct",
                   "ProductLineVariantChoice", "DeferredVariantChoice", "ProductLineCharacteristic")


def test_kernel_holds_no_configuration_selection_under_any_name():
    """ADR 0006: selection authority is external. The kernel product-line
    definitions are pinned, and no kernel feature is typed by a selectable
    product-line class (a selection record under another name)."""
    active = _active(_text(PRODUCT_LINE))
    assert set(re.findall(r"\bdef\s+(\w+)", active)) == PRODUCT_LINE_DEFINITIONS
    # No reference feature at all in the product-line kernel: selections are external.
    assert not re.search(r"\bref\b", active), "reference feature in the product-line kernel"
    typed = re.compile(r":\s*(?:[\w:]*::)?(" + "|".join(PLE_SELECTABLES) + r")\b")
    for path in sorted((ROOT / KERNEL).glob("*.sysml")):
        active = _active(path.read_text())
        hit = typed.search(active)
        assert not hit, (path.name, hit and hit[0])
