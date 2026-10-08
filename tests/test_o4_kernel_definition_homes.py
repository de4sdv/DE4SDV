"""O4 definition homes: source/typing checks, not licensed Syside evidence."""
from pathlib import Path
import re

import pytest


from de4sdv.semantic.authority_inventory import declaration_block, normalize_text
from model_contract_fixtures import (authored_definition, contract_equivalence_evidence,
                                     model_contract, reviewed_definition)

ROOT = Path(__file__).resolve().parents[1]
KERNEL = "textual-notation-of-model/packages/methods/de4sdv/"
CONTEXT = KERNEL + "de4sdv_method_context.sysml"
MIDDLEWARE = "textual-notation-of-model/packages/features/middleware/middleware_verification_evidence.sysml"
AEBS = "textual-notation-of-model/packages/features/aebs/"
# D4 population (owner decision 2026-10-06): exactly these eight AEBS definitions.
AEBS_EVIDENCE_CONTRACTS = {
    AEBS + "aebs_override_verification.sysml": "OverrideEvidenceContract",
    AEBS + "aebs_degraded_input_verification.sysml": "DegradedInputEvidenceContract",
    AEBS + "aebs_bicycle_verification.sysml": "BicycleEvidenceContract",
    AEBS + "aebs_evidence.sysml": "NominalEvidenceContractRequirement",
    AEBS + "aebs_regulatory_criterion_verification.sysml": "RegulatoryCriterionEvidenceContract",
    AEBS + "aebs_non_activation_verification.sysml": "NonActivationEvidenceContract",
    AEBS + "aebs_pedestrian_verification.sysml": "PedestrianEvidenceContract",
    AEBS + "aebs_partial_intervention_verification.sysml": "PartialInterventionEvidenceContract",
}


def test_acceptance_criterion_has_kernel_home_and_middleware_specialization():
    text = (ROOT / CONTEXT).read_text()
    block, bodyless = declaration_block(text, "requirement def AcceptanceCriterion")
    assert block and not bodyless, "D2 requires a kernel requirement definition"
    assert model_contract().classes["AcceptanceCriterion"]["kernel"] == {
        "file": CONTEXT, "declaration": "requirement def AcceptanceCriterion"
    }
    assert normalize_text(reviewed_definition("AcceptanceCriterion")) in normalize_text(block)
    assert "de4sdv.acceptance.maintainer-decision.v1" in block
    middleware = re.sub(r"/\*.*?\*/|//[^\n]*", "", (ROOT / MIDDLEWARE).read_text(), flags=re.S)
    header = re.search(r"requirement\s+def\s+MiddlewareAcceptanceCriterion\s*:>\s*([^;{]+)", middleware)
    assert header and "AcceptanceCriterion" in {s.strip() for s in header[1].split(",")}


def test_evidence_contract_is_a_planning_requirement_and_slices_are_typed():
    text = (ROOT / CONTEXT).read_text()
    block, bodyless = declaration_block(text, "requirement def EvidenceContract")
    assert block and not bodyless, "D4 requires a kernel requirement definition"
    assert model_contract().classes["EvidenceContract"]["kernel"] == {
        "file": CONTEXT, "declaration": "requirement def EvidenceContract"
    }
    assert normalize_text(reviewed_definition("EvidenceContract")) in normalize_text(block)
    for path, declaration in AEBS_EVIDENCE_CONTRACTS.items():
        source = re.sub(r"/\*.*?\*/|//[^\n]*", "", (ROOT / path).read_text(), flags=re.S)
        header = re.search(r"requirement\s+def\s+" + declaration + r"\s*:>\s*([^;{]+)", source)
        assert header and "EvidenceContract" in {s.strip() for s in header[1].split(",")}, declaration
        # Direct import of the owning kernel member (accepted form), no name borrowing.
        assert re.search(r"private\s+import\s+DE4SDV_MethodContext::(?:EvidenceContract|\*)\s*;", source), path
    # Owner decision 2026-10-06: the middleware acceptance criterion is an
    # AcceptanceCriterion only, never an evidence contract.
    source = re.sub(r"/\*.*?\*/|//[^\n]*", "", (ROOT / MIDDLEWARE).read_text(), flags=re.S)
    header = re.search(r"requirement\s+def\s+MiddlewareAcceptanceCriterion\s*:>\s*([^;{]+)", source)
    assert header and "EvidenceContract" not in {s.strip() for s in header[1].split(",")}
    assert "AcceptanceCriterion" in {s.strip() for s in header[1].split(",")}
    # Claims/arguments/counterclaims do not become evidence contracts by name.
    for declaration in ("MiddlewareClaim", "MiddlewareAssuranceArgument", "MiddlewareCounterClaim"):
        header = re.search(r"requirement\s+def\s+" + declaration + r"\s*:>\s*([^;{]+)", source)
        assert header and "EvidenceContract" not in {s.strip() for s in header[1].split(",")}


def test_evaluation_scope_structurally_owns_exclusions_with_reference_and_rationale():
    path = KERNEL + "de4sdv_method_conformance.sysml"
    text = (ROOT / path).read_text()
    block, _ = declaration_block(text, "part def MethodEvaluationScope")
    active = re.sub(r"/\*.*?\*/|//[^\n]*", "", block, flags=re.S)
    assert re.search(r"item\s+exclusions\s*:\s*MethodEvaluationExclusion\s*\[\*\]\s*;", active)
    record, _ = declaration_block(text, "item def MethodEvaluationExclusion")
    active = re.sub(r"/\*.*?\*/|//[^\n]*", "", record, flags=re.S)
    assert re.search(r"ref\s+excludedElement\s*:\s*Base::Anything\s*;", active)
    assert re.search(r"attribute\s+rationale\s*:\s*String\s*;", active)
    assert 'rationale != ""' in active
    assert model_contract().exclusions[path]["item def MethodEvaluationExclusion"].strip()
    # Existing Python value representation remains compatible; no consumer rewiring.
    from de4sdv.semantic.method_contract import MethodEvaluationScope
    scope = MethodEvaluationScope("INC-SYNTHETIC", frozenset(), frozenset(), frozenset(), {}, {"excluded-id": "outside this slice"})
    assert scope.exclusions == {"excluded-id": "outside this slice"}


def _disjoint_pairs(active):
    """Checked-constraint disjointness pairs: ``part def A`` asserting
    ``not (that istype B)`` in its own body."""
    pairs = []
    for match in re.finditer(r"\bpart\s+def\s+(\w+)[^;{]*\{", active):
        depth, end = 1, match.end()
        while depth and end < len(active):
            depth += {"{": 1, "}": -1}.get(active[end], 0)
            end += 1
        body = active[match.end():end - 1]
        for other in re.findall(
            r"\bassert\s+constraint\s+\w+\s*\{\s*not\s*\(\s*that\s+istype\s+(\w+)\s*\)\s*\}", body
        ):
            pairs.append((match[1], other))
    return pairs


MODEL_ROOTS = (
    "textual-notation-of-model",
    "model-based-product-line-engineering/product-models",
    "model-based-product-line-engineering/scoping",
)
_TYPING_END = re.compile(r":>>?|::>|\bsubsets\b|\bredefines\b|\breferences\b|\bdefault\b|:=")
_PART_USAGE = re.compile(
    r"\bpart\s+(?!def\b)(?:(?::>>|\bredefines\b)\s*)?(\w+)?\s*(?:\[[^\]]*\]\s*)?"
    r"(?::(?![>:])|\bdefined\s+by\b)\s*([^;{=]+)"
)


def _active(text):
    """Source text without comments; documentation bodies are comments too."""
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)


def _type_names(declared):
    """Short type names from a typing or specialization list.

    Qualified names, multiplicities, ``ordered``/``nonunique`` and anything
    after the typing list (subsetting, redefinition, values) are removed.
    """
    names = set()
    for item in _TYPING_END.split(declared, maxsplit=1)[0].split(","):
        item = re.sub(r"\[[^\]]*\]|\bordered\b|\bnonunique\b", "", item).strip()
        if item:
            names.add(item.split("::")[-1].strip())
    return names


def _part_def_parents(active):
    parents = {}
    for match in re.finditer(r"\bpart\s+def\s+(\w+)\s*(?::>|\bspecializes\b)\s*([^;{]+)", active):
        parents.setdefault(match[1], set()).update(_type_names(match[2]))
    return parents


def _typed_part_usages(active, parents):
    """(usage name, transitive type closure) for each typed part usage."""
    for usage in _PART_USAGE.finditer(active):
        types = _type_names(usage[2])
        pending = list(types)
        while pending:
            for parent in parents.get(pending.pop(), set()) - types:
                types.add(parent)
                pending.append(parent)
        yield usage[1] or "<anonymous>", types


def _disjoint_typing_violations(*texts):
    """Bounded static probe of checked disjointness + part typing/lineage.

    Disjoint pairs and specialization chains are collected across all given
    sources, so a chain declared in one file is resolved for usages in
    another. Typing through subsetting or redefinition of another usage is
    not followed. This is not a SysML compiler or a production query-time
    source parser.
    """
    actives = [_active(text) for text in texts]
    joined = "\n".join(actives)
    pairs = _disjoint_pairs(joined)
    parents = _part_def_parents(joined)
    violations = []
    for active in actives:
        for name, types in _typed_part_usages(active, parents):
            for a, b in pairs:
                entry = (name, *sorted((a, b)))
                if {a, b} <= types and entry not in violations:
                    violations.append(entry)
    return violations


def _usages_typed_by(type_name, *texts):
    joined = "\n".join(_active(text) for text in texts)
    parents = _part_def_parents(joined)
    return [name for name, types in _typed_part_usages(joined, parents) if type_name in types]


def _model_texts():
    """Every .sysml file in the roots that licensed validation checks."""
    texts = []
    for root in MODEL_ROOTS:
        files = sorted((ROOT / root).rglob("*.sysml"))
        assert files, f"no .sysml files under {root}"
        texts.extend(path.read_text(encoding="utf-8") for path in files)
    return texts


def test_common_capability_feature_disjointness_is_checked_on_both_definitions():
    """Owner decision 7 fallback: licensed Syside rejected the standalone KerML
    ``disjoining`` in a SysML package, so the axiom is a checked constraint."""
    source = (ROOT / (KERNEL + "de4sdv_product_line.sysml")).read_text()
    active = re.sub(r"/\*.*?\*/|//[^\n]*", "", source, flags=re.S)
    assert "disjoining" not in active
    assert set(_disjoint_pairs(active)) == {
        ("CommonProductLineCapability", "ProductLineFeatureCandidate"),
        ("ProductLineFeatureCandidate", "CommonProductLineCapability"),
    }, "Decision 7 requires the symmetric checked constraint"
    assert _disjoint_typing_violations(source) == []
    prefix, suffix = source.rsplit("}", 1)
    # Keep the synthetic members in the actual declaring package, so this
    # negative does not depend on unresolved root-level short-name typing.
    def with_members(members):
        return prefix + "\n" + members + "\n}" + suffix

    negative = with_members("part impossible : CommonProductLineCapability, ProductLineFeatureCandidate;")
    expected = [("impossible", "CommonProductLineCapability", "ProductLineFeatureCandidate")]
    assert _disjoint_typing_violations(negative) == expected
    assert _disjoint_typing_violations(with_members("/* part impossible : CommonProductLineCapability, ProductLineFeatureCandidate; */")) == []
    unchecked = negative.replace("assert constraint notAFeatureCandidate", "/* x */ constraint notAFeatureCandidate")
    unchecked = unchecked.replace("assert constraint notACommonCapability", "/* x */ constraint notACommonCapability")
    assert _disjoint_typing_violations(unchecked) == []
    inherited = with_members("part def Common :> CommonProductLineCapability;"
                             "\npart def Feature :> ProductLineFeatureCandidate;"
                             "\npart impossible : Common, Feature;")
    assert _disjoint_typing_violations(inherited) == expected
    assert _disjoint_typing_violations(with_members("part valid : CommonProductLineCapability;")) == []


def test_no_model_usage_is_typed_as_both_common_capability_and_feature_candidate():
    """Decision 7 across every model root the licensed check validates.

    Licensed Syside accepts the checked constraints; whether it evaluates them
    against usages is not established, so this probe guards the whole model.
    """
    kernel = (ROOT / (KERNEL + "de4sdv_product_line.sysml")).read_text()
    texts = _model_texts()
    assert len(texts) >= 50, "model scan unexpectedly small"
    # Non-vacuity: real product-line usages are classified on both sides,
    # through specialization chains declared in other files.
    common = _usages_typed_by("CommonProductLineCapability", *texts)
    features = _usages_typed_by("ProductLineFeatureCandidate", *texts)
    assert len(common) >= 10 and len(features) >= 2, (common, features)
    assert _disjoint_typing_violations(*texts) == []
    # A dual-typed usage in another file, reached through specializations
    # declared in yet another file, is still reported.
    chain = "package Chain { part def Shared :> CommonProductLineCapability; part def Choice :> ProductLineFeatureCandidate; }"
    usage = "package Use { part bad : Chain::Shared, Chain::Choice[1]; }"
    assert _disjoint_typing_violations(kernel, chain, usage) == [
        ("bad", "CommonProductLineCapability", "ProductLineFeatureCandidate")
    ]
    # Redefining and anonymous typed usages are covered as well.
    assert _disjoint_typing_violations(
        kernel, chain, "package Use { part :>> slot : Shared, Choice; part : Shared, Choice; }"
    ) == [
        ("slot", "CommonProductLineCapability", "ProductLineFeatureCandidate"),
        ("<anonymous>", "CommonProductLineCapability", "ProductLineFeatureCandidate"),
    ]
    # Subsetting after the typing list is not mistaken for a second type.
    assert _disjoint_typing_violations(
        kernel, chain, "package Use { part ok : Shared :> Choice; }"
    ) == []


def _direct_documentation(block):
    """Return directly owned named/anonymous Documentation, not nested text."""
    depth = -1
    docs = []
    for token in re.finditer(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|[{}]', block, re.S):
        value = token[0]
        if value == "{":
            depth += 1
        elif value == "}":
            depth -= 1
        elif value.startswith("/*") and depth == 0:
            prefix = re.search(r"\bdoc(?:\s+(\w+))?\s*$", block[:token.start()])
            if prefix:
                docs.append((prefix[1], value[2:-2]))
    return docs


def _braced_block(text, start):
    """Return text[start:] up to the brace that closes text[start] == "{"."""
    assert text[start] == "{"
    depth = 0
    for token in re.finditer(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|[{}]', text[start:], re.S):
        if token[0] == "{":
            depth += 1
        elif token[0] == "}":
            depth -= 1
            if depth == 0:
                return text[start:start + token.end()]
    raise AssertionError("unbalanced braces")


def test_braced_block_stops_at_the_matching_brace():
    text = 'package P { part p { doc /* } */ } } doc late /* after */'
    assert _braced_block(text, text.index("{")) == 'package P { part p { doc /* } */ } }'[10:]
    assert _direct_documentation(_braced_block(text, text.index("{"))) == []


def _home_docs(row):
    text = (ROOT / row["file"]).read_text()
    declaration = row["declaration"]
    if declaration.startswith("package "):
        package = re.search(r"\b" + re.escape(declaration) + r"\s*\{", text)
        assert package, declaration
        block = _braced_block(text, package.end() - 1)
    else:
        block, bodyless = declaration_block(text, declaration)
        assert block and not bodyless, declaration
    return _direct_documentation(block)


def test_all_authored_definitions_have_exact_owned_model_documentation_homes():
    """Replaces ``test_all_yaml_definitions_have_exact_owned_model_documentation_homes``:
    the authored definitions are read from the pre-deletion evidence
    (closure/contract-equivalence.json) since O4 Wave C2 deleted the YAML."""
    import json
    document = json.loads((ROOT / "docs/method-conformance/o4/kernel-definition-homes.json").read_text())
    authored = contract_equivalence_evidence()["authored_definitions"]["entries"]
    required = {tuple(key.split(":", 1)) for key in authored}
    entries = document["definitions"]
    assert len(entries) == len(required) == 76
    assert {(row["kind"], row["identity"]) for row in entries} == required
    for row in entries:
        candidates = [body for name, body in _home_docs(row) if name == row["documentation_name"]]
        assert len(candidates) > row["documentation_index"], row["identity"]
        assert normalize_text(candidates[row["documentation_index"]]) == normalize_text(
            authored_definition(row["kind"], row["identity"])
        ), row["identity"]


def test_definition_home_inventory_covers_all_requested_register_targets():
    import json
    homes = json.loads((ROOT / "docs/method-conformance/o4/kernel-definition-homes.json").read_text())
    register = json.loads((ROOT / "docs/method-conformance/o4/o4-execution-register.json").read_text())
    expected = {row["identity"]: row for row in register["rows"]
                if row["base_wave"] in {"W2", "W4"}
                and row["migration_class"] in {"MODEL_AUTHORITY_PARITY", "NEW_APPLICATION_SEMANTICS"}}
    assert "register_targets" in homes, "List the requested W2/W4 rows without rewriting generated closure state"
    rows = homes["register_targets"]
    assert len(rows) == len(expected) == 40
    assert {row["identity"] for row in rows} == set(expected)
    definitions = {row["identity"]: row for row in homes["definitions"]}
    for row in rows:
        assert row["base_wave"] == expected[row["identity"]]["base_wave"]
        assert row["migration_class"] == expected[row["identity"]]["migration_class"]
        assert row["claim"] == "definition-home-only; no runtime admission or row-lifecycle closure"
        assert (ROOT / row["file"]).is_file()
        if row["identity"] in definitions:
            home = definitions[row["identity"]]
            assert row["file"] == home["file"]
            assert row["declaration"] == home["declaration"]
            assert row["parity"] == "normalized-exact owned model documentation"
        else:
            # These seven YAML rows declare only domain/range, not definition
            # prose; do not fabricate a text-parity claim for them.
            assert row["parity"] == "no authored definition; model vocabulary role documented"
            existing_homes = {
                "addressesConcern": (KERNEL + "de4sdv_method_vocabulary_carriers.sysml", "connection def AddressesConcern"),
                "selectedViewpoint": (KERNEL + "de4sdv_method_vocabulary_carriers.sysml", "connection def SelectedViewpoint"),
                "producesView": (KERNEL + "de4sdv_method_vocabulary_carriers.sysml", "connection def ProducesView"),
                "recordsAssumption": (KERNEL + "de4sdv_method_vocabulary_carriers.sysml", "connection def RecordsAssumption"),
                "recordsGap": (KERNEL + "de4sdv_method_vocabulary_carriers.sysml", "connection def RecordsGap"),
                "hasStakeholder": (CONTEXT, "part def EngineeringIncrement"),
                "hasAcceptanceCriterion": (CONTEXT, "requirement def AcceptanceCriterion"),
            }
            assert (row["file"], row["declaration"]) == existing_homes[row["identity"]]
            if row["identity"] == "hasStakeholder":
                assert "comment hasStakeholderVocabularyRole about EngineeringIncrement, Stakeholder" in (ROOT / CONTEXT).read_text()
            elif row["identity"] != "hasAcceptanceCriterion":
                assert _home_docs(row), row["identity"]


def test_no_documentation_name_shadows_a_model_or_library_name():
    """Licensed Syside run 37411981652: ``doc VerificationMethod`` shadowed the
    library metadata for every importer. Kernel Documentation names must be
    unique ``ontologyDefinition`` or ``<Term>OntologyDefinition`` forms."""
    contract = model_contract()
    vocabulary = set(contract.classes) | set(contract.relationships) | set(contract.refused)
    declared = set()
    for path in sorted((ROOT / KERNEL).glob("*.sysml")):
        active = re.sub(r"/\*.*?\*/|//[^\n]*", " ", path.read_text(), flags=re.S)
        declared |= set(re.findall(r"\bdef\s+(\w+)", active))
    named_docs = named_comments = 0
    for path in sorted((ROOT / KERNEL).glob("*.sysml")):
        text = _blank_comment_bodies(path.read_text())
        for name in re.findall(r"\bdoc\s+(\w+)\s*/\*", text):
            named_docs += 1
            assert name == "ontologyDefinition" or name.endswith("OntologyDefinition"), (path.name, name)
        # Named comments are package members too (re-exported by wildcard
        # imports), with or without an ``about`` clause, so they must not reuse
        # a predicate, class or definition name.
        for name in re.findall(r"\bcomment\s+(?!about\b)(\w+)\b(?=\s*(?:about\b|/\*|;))", text):
            named_comments += 1
            assert name.endswith("VocabularyRole"), (path.name, name)
            assert name not in vocabulary | declared, (path.name, name)
    assert named_docs >= 36 and named_comments >= 2, "the scan must see the kernel's named docs and comments"


def _blank_comment_bodies(text):
    """Keep ``/*``/``*/`` tokens but drop comment interiors and line comments,
    so prose inside comments is never scanned as declarations."""
    return re.sub(r"/\*.*?\*/", "/**/", re.sub(r"//[^\n]*", "", text), flags=re.S)


def test_definition_owned_ontology_docs_are_private_and_package_homes_are_named():
    """Definition-owned exact docs are private so specializations do not
    inherit them; package-owned homes link to their concept only by the
    ``<Term>OntologyDefinition`` name, which must match the inventory row."""
    import json
    rows = json.loads((ROOT / "docs/method-conformance/o4/kernel-definition-homes.json").read_text())["definitions"]
    package_rows = [row for row in rows if row["declaration"].startswith("package ")]
    definition_rows = [row for row in rows if not row["declaration"].startswith("package ")]
    assert (len(package_rows), len(definition_rows)) == (25, 51)
    for row in package_rows:
        assert row["documentation_name"] == row["identity"] + "OntologyDefinition", row["identity"]
    named_definition_rows = [row for row in definition_rows if row["documentation_name"]]
    assert len(named_definition_rows) == 11
    assert {row["documentation_name"] for row in named_definition_rows} == {"ontologyDefinition"}
    public = []
    total = 0
    for path in sorted((ROOT / KERNEL).glob("*.sysml")):
        for match in re.finditer(r"(?m)^[ \t]*((?:\w+\s+)*)doc\s+ontologyDefinition\b", path.read_text()):
            total += 1
            if "private" not in match[1].split():
                public.append(path.name)
    assert total == 11 and public == [], public
    # Model -> inventory: no orphan <Term>OntologyDefinition carrier.
    carriers = set()
    for path in sorted((ROOT / KERNEL).glob("*.sysml")):
        carriers |= set(re.findall(r"\bdoc\s+(\w+OntologyDefinition)\s*/\*", _blank_comment_bodies(path.read_text())))
    assert carriers == {row["documentation_name"] for row in package_rows}, carriers ^ {
        row["documentation_name"] for row in package_rows}


def test_kernel_evidence_contract_specializations_are_exactly_the_claimed_population():
    """D4 (owner decision 2026-10-06): the kernel type is specialized by
    exactly the eight AEBS evidence-contract definitions; the middleware
    acceptance criterion is not an evidence contract. Any other
    specialization must update the D4 wording, ADR 0020 and this pin."""
    supers = {}
    for root in ("textual-notation-of-model", "model-based-product-line-engineering/product-models"):
        for path in sorted((ROOT / root).rglob("*.sysml")):
            source = re.sub(r"/\*.*?\*/|//[^\n]*", " ", path.read_text(), flags=re.S)
            for name, parents in re.findall(
                r"requirement\s+def\s+(\w+)\s*(?::>|\bspecializes\b)\s*([^;{]+)", source
            ):
                supers.setdefault(name, set()).update(
                    s.strip().split("::")[-1] for s in parents.split(",") if s.strip()
                )
    # Transitive specialization closure of the kernel EvidenceContract.
    found, frontier = set(), {"EvidenceContract"}
    while frontier:
        frontier = {name for name, parents in supers.items() if parents & frontier} - found
        found |= frontier
    assert found == set(AEBS_EVIDENCE_CONTRACTS.values()), found
    # Every member is declared exactly once, in its AEBS slice.
    for path, declaration in AEBS_EVIDENCE_CONTRACTS.items():
        owners = [p for p in (ROOT / "textual-notation-of-model").rglob("*.sysml")
                  if re.search(r"requirement\s+def\s+" + declaration + r"\b",
                               re.sub(r"/\*.*?\*/|//[^\n]*", " ", p.read_text(), flags=re.S))]
        assert [p.relative_to(ROOT).as_posix() for p in owners] == [path], declaration


# Usages typed by each closure member, per owning slice. The pin covers the
# usage population, not only the definition closure (R2/K5).
AEBS_EVIDENCE_CONTRACT_USAGES = {
    "OverrideEvidenceContract": 3, "DegradedInputEvidenceContract": 4, "BicycleEvidenceContract": 3,
    "NominalEvidenceContractRequirement": 5, "RegulatoryCriterionEvidenceContract": 6,
    "NonActivationEvidenceContract": 3, "PedestrianEvidenceContract": 3, "PartialInterventionEvidenceContract": 3,
}


def test_evidence_contract_usage_population_is_exactly_the_slice_usages():
    """Every reference to EvidenceContract or a closure member, in every model
    root, is one of: its definition header, the kernel specialization, the
    direct kernel import, the discriminator comment, or a requirement usage
    typed by a closure member inside that member's own slice. A usage typed
    directly by EvidenceContract, a usage elsewhere, or a feature subsetting
    or redefining a contract usage fails."""
    closure = {"EvidenceContract"} | set(AEBS_EVIDENCE_CONTRACTS.values())
    home = {name: path for path, name in AEBS_EVIDENCE_CONTRACTS.items()}
    token = re.compile(r"(?<![\w'])(?:[\w]+::)*(" + "|".join(sorted(closure)) + r")\b")
    usage = re.compile(r"\brequirement\s+(?:<'[^']*'>\s*)?(\w+)\s*:\s*(\w+)\s*\{")
    counts, usage_names = {}, set()
    for root in ("textual-notation-of-model", "model-based-product-line-engineering"):
        for path in sorted((ROOT / root).rglob("*.sysml")):
            rel = path.relative_to(ROOT).as_posix()
            source = re.sub(r"/\*.*?\*/|//[^\n]*", " ", path.read_text(), flags=re.S)
            allowed = set()
            for match in usage.finditer(source):
                if match[2] in closure:
                    assert match[2] != "EvidenceContract", (rel, match[1], "usage typed directly by the kernel type")
                    assert home[match[2]] == rel, (rel, match[1], "closure usage outside its slice")
                    counts[match[2]] = counts.get(match[2], 0) + 1
                    usage_names.add(match[1])
                    allowed.add(match.start(2))
            for match in re.finditer(r"\brequirement\s+def\s+(\w+)(?:\s*:>\s*([\w:]+))?", source):
                if match[1] in closure:
                    allowed.add(match.start(1))
                    if match[2]:
                        allowed.add(match.start(2) + len(match[2]) - len(match[2].split("::")[-1]))
            for match in re.finditer(r"\bprivate\s+import\s+DE4SDV_MethodContext::(EvidenceContract)\s*;", source):
                allowed.add(match.start(1))
            if rel == CONTEXT:
                for match in re.finditer(r"\bcomment\s+hasRelevantEvidenceContractVocabularyRole\s+about\s+(EvidenceContract)\b", source):
                    allowed.add(match.start(1))
            for match in token.finditer(source):
                assert match.start(1) in allowed, (rel, source[max(0, match.start() - 60):match.end() + 10])
    assert counts == AEBS_EVIDENCE_CONTRACT_USAGES, counts
    assert len(usage_names) == 28 and sum(counts.values()) == 30
    # No feature anywhere subsets or redefines a contract usage.
    reuse = re.compile(r"(?::>>?|\bsubsets\b|\bredefines\b|\breferences\b|::>)\s*(?:[\w]+(?:::|\.))*(" +
                       "|".join(sorted(usage_names)) + r")\b")
    for root in ("textual-notation-of-model", "model-based-product-line-engineering"):
        for path in sorted((ROOT / root).rglob("*.sysml")):
            source = re.sub(r"/\*.*?\*/|//[^\n]*", " ", path.read_text(), flags=re.S)
            assert not reuse.search(source), (path.name, reuse.search(source)[0])


def test_has_relevant_evidence_contract_discriminator_is_model_resident_vocabulary():
    """hasRelevantEvidenceContract is discriminated by EvidenceContract type
    lineage, stated in the kernel as vocabulary; the runtime mapping is not
    changed by this documentation."""
    text = (ROOT / CONTEXT).read_text()
    match = re.search(
        r"comment\s+hasRelevantEvidenceContractVocabularyRole\s+about\s+EvidenceContract\s*/\*(.*?)\*/", text, re.S)
    assert match, "discriminator vocabulary role must annotate the kernel EvidenceContract"
    body = normalize_text(match[1].replace("*", " "))
    for phrase in ("specialization closure", "governed kernel mapping", "never by a name",
                   "AcceptanceCriterion typing", "Vocabulary only", "existing dependency mapping"):
        assert normalize_text(phrase) in body, phrase
    assert model_contract().relationship_mapping("hasRelevantEvidenceContract").strategy == "dependency"


def test_named_docs_do_not_borrow_nested_or_comment_only_homes():
    assert _direct_documentation('{ doc D /* exact */ part p { doc D /* wrong */ } }') == [("D", " exact ")]
    assert _direct_documentation('{ /* doc D / * fake * / */ doc D /* exact */ }') == [("D", " exact ")]
    assert _direct_documentation('{ doc /* outer */ part p; doc D /* second */ }') == [(None, " outer "), ("D", " second ")]


def test_architecture_umbrellas_document_native_kinds_without_parallel_taxonomy():
    text = (ROOT / CONTEXT).read_text()
    docs = dict(_direct_documentation(text[text.index("package DE4SDV_MethodContext"):]))
    for name in ("ArchitectureElement", "Function", "LogicalElement", "PhysicalElement"):
        # Documentation names must not equal any model/library name: licensed
        # Syside resolves a same-named Documentation before an imported type.
        doc_name = name + "OntologyDefinition"
        assert doc_name in docs and name not in docs, name
        assert not re.search(r"\bdef\s+" + name + r"\b", re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S))
        annotation = re.search(r"comment\s+about\s+" + doc_name + r"\s*/\*(.*?)\*/", text, re.S)
        assert annotation, name
        expected = ("ActionDefinition", "ActionUsage") if name == "Function" else ("PartDefinition", "PartUsage")
        for native_kind in expected:
            assert native_kind in annotation[1], (name, native_kind)


def test_canonical_architecture_remains_non_queryable_documentation_only():
    text = (ROOT / (KERNEL + "de4sdv_product_line.sysml")).read_text()
    annotation = re.search(r"comment\s+about\s+instantiatesCanonicalArchitectureOntologyDefinition\s*/\*(.*?)\*/", text, re.S)
    assert annotation and "not queryable; no product-to-canonical reachability claimed" in " ".join(annotation[1].split())
    contract = model_contract()
    assert "sysml_mapping" not in contract.relationships["instantiatesCanonicalArchitecture"]
    with pytest.raises(KeyError, match="no SysML mapping"):
        contract.relationship_mapping("instantiatesCanonicalArchitecture")
