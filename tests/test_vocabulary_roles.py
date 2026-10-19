"""Vocabulary roles, native grounding records, validation-rule homes and the
pilot-query fixture.

These are lexical source checks, not licensed Syside evidence.
"""
import json
from pathlib import Path
import re

import pytest
import yaml

from de4sdv.semantic.authority_inventory import normalize_text
from model_contract_fixtures import model_contract
from sysml_shapes import braced_body

ROOT = Path(__file__).resolve().parents[1]
KERNEL = "textual-notation-of-model/packages/methods/de4sdv/"
PRODUCT_LINE = KERNEL + "de4sdv_product_line.sysml"
CONTEXT = KERNEL + "de4sdv_method_context.sysml"
VIEWPOINTS = KERNEL + "de4sdv_method_concerns_and_viewpoints.sysml"
RULES = KERNEL + "de4sdv_ontology_validation_rules.sysml"
PILOT_FIXTURE = "tests/fixtures/ontology/pilot_queries.yaml"

#: The boundary every PLE configuration role states. It holds before and after the
#: switch of ADR 0022: the YAML catalogue is the configuration authority until the
#: switch, and the PLEML feature models are from it.
ADR_0022_BOUNDARY = "No configurator authority; configuration authority follows ADR 0022"

# identity -> (file, annotated element, kernel names of domain and range)
VOCABULARY_ROLES = {
    "specifiesFeature": (PRODUCT_LINE, "ProductLineFeatureCandidate", ("RequirementCandidate", "ProductLineFeatureCandidate")),
    "specifiesCommonCapability": (PRODUCT_LINE, "CommonProductLineCapability", ("RequirementCandidate", "CommonProductLineCapability")),
    "variesAt": (PRODUCT_LINE, "ProductLineFeatureCandidate", ("ProductLineFeatureCandidate", "VariationPointOntologyDefinition")),
    "appliesToMemberProduct": (PRODUCT_LINE, "FeatureConfigurationOntologyDefinition", ("FeatureConfiguration", "ProductLineMemberProduct")),
    "selectsFeature": (PRODUCT_LINE, "FeatureConfigurationOntologyDefinition", ("FeatureConfiguration", "ProductLineFeatureCandidate")),
    "selectsVariant": (PRODUCT_LINE, "FeatureConfigurationOntologyDefinition", ("FeatureConfiguration", "VariantOntologyDefinition")),
    "usesVerificationMethod": (CONTEXT, "VerificationMethodOntologyDefinition", ("VerificationCase", "VerificationMethod")),
}
PLE_CONFIGURATION_ROLES = {"appliesToMemberProduct", "selectsFeature", "selectsVariant"}
#: Removed at the switch of ADR 0022 (register interp-10): no gate, check, traversal or
#: consumer read it, and the governed-scope admission check derives the fact it names.
REMOVED_PLE_ROLES = {"includesCommonCapability"}
#: The PLEML declaration that FeatureConfiguration grounds on from the switch.
PLEML_FEATURE_CONFIGURATION = "occurrence def FeatureConfiguration"
#: Reviewed domain/range of the native-grounding row whose relation ends are not
#: projected, as recorded before the authored ontology was deleted.
UNPROJECTED_DOMAIN_RANGE = {"usesVerificationMethod": ("VerificationCase", "VerificationMethod")}
#: The ten validation rules, one model home each.
RULE_HOMES = {f"ontologyRuleR{number:03d}" for number in range(1, 11)}


def _text(path):
    return (ROOT / path).read_text()


def _domain_range(identity):
    """Reviewed domain/range: the model contract's projection spec, or the
    reviewed values for a row whose domain/range is not projected."""
    spec = model_contract().relationships[identity]
    if spec.get("domain") and spec.get("range"):
        return spec["domain"], spec["range"]
    return UNPROJECTED_DOMAIN_RANGE[identity]


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


def test_ple_configuration_rows_carry_no_configurator_authority_under_adr_0022():
    """S5o (ADR 0022 decision 8): the PLE configuration roles state the boundary that
    holds before and after the switch, name the PLEML construct that carries each
    fact from the switch, and keep no catalogue authority of ADR 0006."""
    text = _text(PRODUCT_LINE)
    comments = _named_comments(text)
    for identity in PLE_CONFIGURATION_ROLES | {"FeatureConfiguration"}:
        targets, body = comments[identity + "VocabularyRole"]
        assert targets.strip() == "FeatureConfigurationOntologyDefinition", identity
        body = _flat(body)
        assert ADR_0022_BOUNDARY in body and "Vocabulary only" in body, identity
        # True in both states: each role names the YAML side until the switch and
        # the PLEML side from it.
        assert "until the switch" in body.lower() and "from the switch" in body.lower(), identity
        assert "Bill-of-Features" in body and "PLEML" in body, identity
        assert "selection authority stays with the external catalogue" not in body, identity
    carriers = {
        "FeatureConfiguration": "pinned PLEML library definition FeatureConfiguration",
        "appliesToMemberProduct": "owned ProductModelProjectionName annotation names it",
        "selectsFeature": "redefining each with multiplicity 1",
        "selectsVariant": "DE4SDV derivation rules",
    }
    for identity, carrier in carriers.items():
        assert carrier in _flat(comments[identity + "VocabularyRole"][1]), identity
    # Like selectsVariant, these two are DE4SDV derived facts that no PLEML construct carries.
    for identity in ("appliesToMemberProduct", "selectsFeature"):
        body = _flat(comments[identity + "VocabularyRole"][1])
        assert "The relationship is a DE4SDV derived fact" in body and "FeatureConfigurationBinding" not in body, identity
    assert "applies to no member product" in _flat(comments["appliesToMemberProductVocabularyRole"][1])
    definition = _flat(re.search(r"\bdoc\s+FeatureConfigurationOntologyDefinition\s*/\*(.*?)\*/", text, re.S)[1])
    assert definition.startswith("A selection of features that describes a member product or scenario."), definition
    # True in both states: a bill of features may list a common capability, which the
    # catalogue marks mandatory, and from the switch common content has no feature.
    assert "Common capabilities are not configuration choices" in definition
    assert "does not select common capabilities" not in definition and "every member product" not in definition
    # Feature stays the kernel candidate (S5o): a PLEML feature is a distinct element.
    candidate = braced_body(text, "part def ProductLineFeatureCandidate")
    notes = [_flat(body) for body in re.findall(r"\bcomment\s*/\*(.*?)\*/", candidate, re.S)]
    assert len(notes) == 1, notes
    for phrase in ("The ontology Feature stays this kernel definition before and after the switch of ADR 0022",
                   "R001 governs it", "A feature of a PLEML feature model is a distinct element",
                   "never itself a Feature and never typed by a product-line characteristic",
                   "only through a correspondence to a governed feature candidate",
                   "Options that correspond only to common content, reference-only alternatives or deferred "
                   "variability, grouping options and options without a governed element are PLEML features that "
                   "relate to no Feature",
                   "The derived adapter is no PLEML feature"):
        assert phrase in notes[0], phrase
    assert model_contract().classes["Feature"]["kernel"] == {
        "file": PRODUCT_LINE, "declaration": "part def ProductLineFeatureCandidate"}
    # No model-side configuration authority: no FeatureConfiguration, variation-point
    # or variant definition anywhere in the governed kernel directory.
    for path in sorted((ROOT / KERNEL).glob("*.sysml")):
        active = _active(path.read_text())
        assert not re.search(r"\bdef\s+(FeatureConfiguration|VariationPoint|Variant)\b", active), path.name
    # The served mapping follows the switch state: test_feature_configuration_mapping_follows_the_switch.


def _pleml_switch_state(pinned, reviewed_roots, production_usage):
    """The PLEML pins of the API baseline, and every production surface that takes PLEML in."""
    from de4sdv.semantic import pleml_package

    pins = [Path(path) for path in pinned if "pleml" in Path(path).as_posix().lower()]
    signals = [f"pinned dependency {path.as_posix()}" for path in pins]
    if pleml_package.PACKAGE in production_usage:
        signals.append(f"the production Sysand project uses {pleml_package.PACKAGE}")
    for root in map(Path, reviewed_roots):
        for fenced in (pleml_package.PROJECT, *pleml_package.IMPORT_ROOTS):
            if fenced.is_relative_to(root) or root.is_relative_to(fenced):
                signals.append(f"reviewed root {root.as_posix()} takes in {fenced.as_posix()}")
    return pins, signals


def feature_configuration_switch_violations(mapping, pinned, reviewed_roots, production_usage):
    """FeatureConfiguration's served kernel mapping follows the switch of ADR 0022 in both
    directions (review of #407, R3): external exactly while PLEML is outside the API
    baseline and every production surface (ADR 0011), and from the switch the file
    mapping of the pinned PLEML declaration, at the path the export records."""
    pins, signals = _pleml_switch_state(pinned, reviewed_roots, production_usage)
    if not signals:
        if set(mapping) == {"external"}:
            return []
        return [f"FeatureConfiguration maps to {mapping}, but PLEML is outside the API baseline (ADR 0011)"]
    if len(pins) != 1:
        return [f"PLEML enters production ({'; '.join(signals)}), so the API baseline must pin exactly one "
                f"PLEML library, not {len(pins)}"]
    expected = {"file": pins[0].as_posix(), "declaration": PLEML_FEATURE_CONFIGURATION}
    if mapping != expected:
        return [f"PLEML enters production ({'; '.join(signals)}), so FeatureConfiguration must map to "
                f"{expected}, not {mapping}: the switch (S6) flips it"]
    return []


def test_feature_configuration_mapping_follows_the_switch():
    from de4sdv.sysml_api.baseline import PINNED_DEPENDENCIES, REVIEWED_ROOTS

    production = json.loads((ROOT / ".project.json").read_text(encoding="utf-8"))
    usage = {item["resource"] for item in production["usage"]}
    mapping = model_contract().classes["FeatureConfiguration"]["kernel"]
    assert feature_configuration_switch_violations(mapping, PINNED_DEPENDENCIES, REVIEWED_ROOTS, usage) == []


_EXTERNAL = {"external": "Bill-of-Features records"}
_PLEML = ".sysand/lib/mbse4u-pleml_1.1.1/PLEML.sysml"
_FLIPPED = {"file": _PLEML, "declaration": PLEML_FEATURE_CONFIGURATION}
_LIBRARIES = (".sysand/lib/mbse4u-sysmod_5.1.1/SYSMOD.sysml",)
_ROOTS = ("textual-notation-of-model", "model-based-product-line-engineering/product-models")


@pytest.mark.parametrize("mapping, pinned, roots, usage, refused", [
    pytest.param(_EXTERNAL, _LIBRARIES, _ROOTS, set(), False, id="before-the-switch"),
    pytest.param(_FLIPPED, (*_LIBRARIES, _PLEML), _ROOTS, {"pkg:sysand/mbse4u/pleml"}, False, id="the-switch"),
    pytest.param(_EXTERNAL, (*_LIBRARIES, _PLEML), _ROOTS, set(), True, id="the-switch-without-the-flip"),
    pytest.param(_EXTERNAL, _LIBRARIES, _ROOTS, {"pkg:sysand/mbse4u/pleml"}, True, id="the-lock-without-the-flip"),
    pytest.param(_EXTERNAL, _LIBRARIES, (*_ROOTS, "model-based-product-line-engineering/feature-models"), set(),
                 True, id="the-feature-models-without-the-flip"),
    pytest.param(_FLIPPED, _LIBRARIES, _ROOTS, set(), True, id="the-flip-without-the-switch"),
    pytest.param(_FLIPPED, (*_LIBRARIES, _PLEML, "pleml/PLEML-1.1.0.sysml"), _ROOTS, set(), True, id="two-pins"),
    pytest.param({"file": _PLEML, "declaration": "part def FeatureConfiguration"}, (*_LIBRARIES, _PLEML), _ROOTS,
                 set(), True, id="another-declaration"),
    pytest.param({"file": "elsewhere/PLEML.sysml", "declaration": PLEML_FEATURE_CONFIGURATION},
                 (*_LIBRARIES, _PLEML), _ROOTS, set(), True, id="another-path-than-the-export-records"),
])
def test_the_switch_interlock_refuses_either_side_without_the_other(mapping, pinned, roots, usage, refused):
    assert bool(feature_configuration_switch_violations(mapping, pinned, roots, usage)) is refused


def test_the_governed_scope_meets_the_varies_at_evidence_gate():
    """The variesAt role says the governed scope meets its evidence gate (review of #407,
    R12): a variation there owns variants typed by feature-candidate specializations."""
    _, body = _named_comments(_text(PRODUCT_LINE))["variesAtVocabularyRole"]
    assert "The governed product-line scope meets that gate" in _flat(body)
    scope = _active(_text("model-based-product-line-engineering/scoping/de4sdv_aebs_product_line_scope.sysml"))
    supertype = dict(re.findall(r"\bpart\s+def\s+(\w+)\s*:>\s*(\w+)", scope))

    def is_candidate(name):
        while name in supertype:
            name = supertype[name]
            if name == "ProductLineFeatureCandidate":
                return True
        return False

    variations = re.findall(r"\bvariation\s+part\s+\w+\s*\{(.*?)\n\s*\}", scope, re.S)
    typed = [kind for block in variations for kind in re.findall(r"\bvariant\s+part\s+\w+\s*:\s*(\w+)", block)]
    assert len(typed) >= 2 and all(is_candidate(kind) for kind in typed), typed


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
    for phrase in ("metadata def VerificationMethod", "VerificationMethodKind", "verificationMethod",
                   "Two distinct representations"):
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
    text = _text(RULES)
    blocks = _rule_blocks(text)
    assert set(blocks) == RULE_HOMES
    for name, block in blocks.items():
        docs = re.findall(r"\bdoc\s*/\*(.*?)\*/", block, re.S)
        assert normalize_text(docs[0]), name
        rule_id = "DE4SDV-ONT-" + name.removeprefix("ontologyRule")
        assert _flat(docs[1]).startswith(f"Rule {rule_id}. Enforced by: "), name
        # A rule home is a declaration only: no expression, no assertion.
        assert not _active(block).strip(" \n;").replace("doc", "").replace("comment", "").strip(), name
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
    assert len(homes) >= 21, "the scan must see the kernel's vocabulary roles"
    duplicated = {name: files for name, files in homes.items() if len(files) != 1}
    assert not duplicated, duplicated
    assert all(files[0].startswith(KERNEL) for files in homes.values()), homes


def test_removed_ple_configuration_relation_is_refused_and_unused():
    """includesCommonCapability is removed (register interp-10): no gate, check,
    traversal or consumer read it, and the governed-scope admission check derives
    the fact it names from the selections and their correspondences. Its vocabulary
    role is gone from every model file, no model code names it, and the contract
    refuses the name with its register disposition and the true reason."""
    from de4sdv.semantic.kernel_contract import RetiredIdentityError

    contract = model_contract()
    for identity in REMOVED_PLE_ROLES:
        assert identity not in contract.relationships, identity
        assert "register disposition REMOVE" in contract.refused[identity], identity
        assert "admission check derives" in contract.refused[identity], identity
        assert "every member product" not in contract.refused[identity], identity
        with pytest.raises(RetiredIdentityError, match="register disposition REMOVE"):
            contract.relationship_mapping(identity)
    files = list(_model_files())
    assert len(files) > 50, "the scan must see the model files"
    for path in files:
        code = _blank_comment_bodies(path.read_text())
        for identity in REMOVED_PLE_ROLES:
            assert not re.search(r"\b" + identity + r"(?:VocabularyRole)?\b", code, re.IGNORECASE), path


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
#: The one kernel feature a selectable product-line class may type: the output
#: parameter of the phase-3 workflow step ClassifyCapabilities, which says what
#: kind of element the step records (feature candidates, the feature-model
#: delta) and selects nothing. The exemption holds only inside that step's body.
STEP_OUTPUT_EXEMPTION = ("de4sdv_increment_workflow.sysml", "action def ClassifyCapabilities",
                         "out part characteristics[0..*] : ProductLineFeatureCandidate;")


def test_kernel_holds_no_configuration_selection_under_any_name():
    """The kernel holds no configuration selection: the configuration authority
    follows ADR 0022 (the YAML catalogue until the switch, the PLEML feature models
    from it), never the kernel. The kernel product-line
    definitions are pinned, and no kernel feature is typed by a selectable
    product-line class (a selection record under another name): not with ``:``,
    ``defined by`` or ``typed by``, and not through an alias. The one exception
    is the phase-3 step's output parameter (STEP_OUTPUT_EXEMPTION), and only
    inside that step's body. Import statements type nothing and are not
    scanned."""
    active = _active(_text(PRODUCT_LINE))
    assert set(re.findall(r"\bdef\s+(\w+)", active)) == PRODUCT_LINE_DEFINITIONS
    # No reference feature at all in the product-line kernel: selections live outside it.
    assert not re.search(r"\bref\b", active), "reference feature in the product-line kernel"
    imports = re.compile(r"^\s*(?:(?:private|public)\s+)?import\s+[^;]*;", re.MULTILINE)
    texts = {path: imports.sub(" ", _active(path.read_text()))
             for path in sorted((ROOT / KERNEL).glob("*.sysml"))}
    selectable = r"(?:[\w:]*::)?(?:" + "|".join(PLE_SELECTABLES) + r")\b"
    aliases = sorted({name for text in texts.values()
                      for name in re.findall(r"\balias\s+(\w+)\s+for\s+" + selectable, text)})
    typed = re.compile(r"(?::|\b(?:defined|typed)\s+by)\s*(?:[\w:]*::)?("
                       + "|".join((*PLE_SELECTABLES, *aliases)) + r")\b")
    file, step, parameter = STEP_OUTPUT_EXEMPTION
    exempted = 0
    for path, text in texts.items():
        if path.name == file:
            body = braced_body(text, step)
            start = text.index(body, text.index(step))
            exempted = body.count(parameter)
            text = text[:start] + body.replace(parameter, " ", 1) + text[start + len(body):]
        hit = typed.search(text)
        assert not hit, (path.name, hit and hit[0])
    assert exempted == 1, "the exempted output parameter must appear exactly once, in the ClassifyCapabilities body"
