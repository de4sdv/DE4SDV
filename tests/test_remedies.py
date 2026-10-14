"""What to author: remedies built from the typed parameter a check is about.

A workflow step declares typed parameters, and each method check is about one
of them. These tests check, over synthetic export-shaped models, that what an
answer tells an agent to author is built from that parameter in the bound
view: its SysML keyword, its type's qualified name computed from ownership,
the ``private import`` of the type's package, the types the check's own type
test admits, the order in which elements must be declared, and only SysML an
author can write. The oracles are the builders' own construction (which
package each definition was put in, which name it got) and the KerML
qualified-name resolution of :mod:`de4sdv.sysml_api.qualified_names`, never
the remedy code. The genuine-export cut is covered in
``test_remedies_on_the_genuine_export.py``.
"""

from __future__ import annotations

from typing import Any

from de4sdv.semantic import method_evaluator as me
from de4sdv.semantic.increment_evaluation import evaluate_increment
from de4sdv.semantic.increment_scope import ModelView
from de4sdv.semantic.kernel_contract import KernelFileMapping, declaration_identity
from de4sdv.semantic.remedies import SUBJECT_FIRST
from de4sdv.sysml_api.qualified_names import QualifiedNameIndex
from increment_model_fixtures import (
    INFINITY,
    ModelBuilder,
    WorkflowCheck,
    WorkflowParameter,
    WorkflowStep,
    increment_scenario,
    increment_workflow,
)
from model_contract_fixtures import model_contract
from sysml_shapes import REPO_ROOT
from test_method_answer_coverage import _metaclass, _workflow_steps
from test_revision_index import _traversal

REVISION = me.RevisionIdentity("b" * 40, "project", "commit", "full-model")
P0, P4, P5, P10 = ("phase0_incrementFraming", "phase4_needs", "phase5_requirements", "phase10_vvEvidence")
P, C = WorkflowParameter, WorkflowCheck
NEW = "INC-EXAMPLE-001"  # an increment the synthetic revisions do not declare (a new increment)


def _view(scenario) -> ModelView:
    builder = scenario.builder
    return ModelView(builder.elements, _traversal(builder), sources=builder.sources)


def _evaluate(scenario, increment_id: str | None = None):
    return evaluate_increment(_view(scenario), increment_id or scenario.increment_id, revision=REVISION)


def _feature(builder: ModelBuilder, owner: dict, kind: str, name: str, *bounds: Any,
             typed_by: dict | None = None, **extra: Any) -> dict:
    """A feature ``owner`` declares (``kind`` usage through a feature membership), optionally typed."""
    feature = builder.new(kind, name=name, source=builder.sources[owner["@id"]], **extra)
    builder.own(owner, feature, kind="FeatureMembership", member_name=name)
    if typed_by is not None:
        builder.typed(feature, typed_by)
    if bounds:
        builder.multiplicity(feature, *bounds)
    return feature


def _kernel_scenario(applicable_phases=(P0, P4, P5, P10)):
    """A complete increment whose charter declares the live workflow file's workflow (read lexically),
    over a synthetic kernel shaped like the method's.

    Kernel definitions sit in one synthetic package per kernel file. A step parameter is typed by the
    kernel definition the contract pins under the parameter's type name, else by a synthetic definition
    of that name in ``FixtureMethodTypes``. The kernel declares the features the checks read:
    ``increment`` (a reference part) and ``applicablePhases`` on the charter class, the charter
    definition's ``owner``, ``expectedArtifacts``, ``expectedReviewEvidence`` and ``systemOfInterest``,
    and the library attributes needs and requirements redefine.
    """
    builder = ModelBuilder(label="remedies", kernel_packages=True)
    scenario = increment_scenario(builder, applicable_phases=applicable_phases)
    roots = scenario.vocabulary
    types = builder.package("FixtureMethodTypes")
    # The charter class declares increment, applicablePhases, owner, expectedArtifacts,
    # expectedReviewEvidence and systemOfInterest (increment_scenario's synthetic kernel).
    charter = builder.definition("PartDefinition", "IncrementCharter", types, [roots["IncrementTraceObligations"]])
    holder = builder.library["__holder__"]
    for need_or_requirement in (roots["Need"], roots["Requirement"]):
        builder.specializes(need_or_requirement, holder)
    _feature(builder, roots["Requirement"], "AttributeUsage", "successCriteria", 0, 1)
    by_name: dict[str, dict] = {}
    for ontology_class in model_contract().classes:
        mapping = model_contract().mapping(ontology_class)
        if isinstance(mapping, KernelFileMapping):
            by_name.setdefault(declaration_identity(mapping.declaration)[0], {"class": ontology_class})
    definitions = {"IncrementCharter": charter}

    def typed(name: str | None, keyword: str):
        if name is None:
            return None
        if name not in definitions:
            known = by_name.get(name)
            definitions[name] = (builder.kernel_definition(known["class"]) if known else builder.definition(
                "RequirementDefinition" if keyword == "requirement" else "PartDefinition", name, types))
        return definitions[name]

    steps = _workflow_steps()
    scenario.workflow = increment_workflow(builder, [
        WorkflowStep(step.usage, step.phase, tuple(
            P(p.name, typed(p.type, p.keyword), kind=_metaclass(p.keyword), direction=p.direction,
              bounds=(p.multiplicity[0], INFINITY if p.multiplicity[1] == "*" else p.multiplicity[1]))
            for p in step.parameters), tuple(
            C(c.name, c.check, c.about, advisory=True if c.advisory else None, doc=c.claim) for c in step.checks))
        for step in steps], charter=scenario.charter)
    builder.specializes(next(e for e in builder.elements if e.get("declaredName") == "FixtureCharter"), charter)
    for name, usage in (("IncrementScope", "fixtureScope"), ("OutOfScopeItem", "fixtureOutOfScopeItem")):
        builder.usage("PartUsage", usage, scenario.framing, [typed(name, "part")])
    return scenario, steps, definitions


def _needs_workflow(scenario) -> None:
    """A workflow that checks the increment's identifier and the statement of each need."""
    increment_workflow(scenario.builder, [
        WorkflowStep("frameIncrement", P0, (P("increment", "EngineeringIncrement"),), (
            C("incrementHasIdentifier", "incrementShortName", "increment"),)),
        WorkflowStep("elaborateNeeds", P4, (P("needs", "Need", "RequirementUsage", bounds=(1, INFINITY)),), (
            C("needHasStatement", "requireConstraint", "needs"),)),
    ], charter=scenario.charter)


def _printed(value: Any) -> list[tuple[str, str]]:
    """Every (element_id, qualified_name) pair an answer prints."""
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        if value.get("element_id") and value.get("qualified_name"):
            found.append((value["element_id"], value["qualified_name"]))
        for item in value.values():
            found.extend(_printed(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_printed(item))
    return found


# -- one name printer ------------------------------------------------------------


def test_every_name_the_method_answers_print_resolves_to_the_element_it_names() -> None:
    """The answers print KerML qualified names computed from ownership: a name that is not a basic
    name is quoted, and every printed name resolves, exactly, to the element it is printed for."""
    scenario = increment_scenario()
    _needs_workflow(scenario)
    builder = scenario.builder
    builder.remove(builder.feature_of(scenario.needs[1], "statement"))
    scenario.needs[1]["declaredName"] = "need one"  # not a basic name
    evaluation = _evaluate(scenario)
    answers = [evaluation.status(), evaluation.gaps(), evaluation.next_obligation(), evaluation.phase_contract()]
    (gap,) = evaluation.gaps()["blocking"]
    assert [s["qualified_name"] for s in gap["subjects"]] == ["DE4SDV_FixtureNeedsRequirements::'need one'"]
    names = QualifiedNameIndex(builder.elements)
    printed = [pair for answer in answers for pair in _printed(answer)]
    assert len(printed) >= 5
    for element_id, name in printed:
        assert [e["@id"] for e in names.resolve(name)] == [element_id], name


# -- the synthetic kernel scenario ---------------------------------------------------


def _kernel_qualified(scenario, ontology_class: str) -> tuple[str, str]:
    """The (qualified name, package name) the builder gave a kernel definition: the oracle."""
    builder = scenario.builder
    kernel = builder.kernel_definition(ontology_class)
    package = builder.kernel_package(builder.sources[kernel["@id"]])["declaredName"]
    return f"{package}::{kernel['declaredName']}", package


def test_the_kernel_scenario_declares_the_live_workflow_and_passes_its_blocking_checks() -> None:
    scenario, steps, _types = _kernel_scenario()
    evaluation = _evaluate(scenario)
    assert evaluation.increment_method.available, evaluation.increment_method.reason
    assert [s["step"] for s in evaluation.phase_contract()["steps"]] == [step.usage for step in steps]
    assert evaluation.gaps()["blocking"] == []


# -- what to author, from the typed parameter ------------------------------------------


def test_a_new_increment_is_told_to_declare_its_definition_then_its_usage() -> None:
    """``out part increment : EngineeringIncrement``: the method's form. The increment's own definition
    specializes the qualified kernel definition (its keyword and import), and the usage is typed by it."""
    scenario, _steps, _types = _kernel_scenario()
    step = _evaluate(scenario, NEW).next_obligation()["next"]
    assert step["gate"] == "incrementHasIdentifier"
    qualified, package = _kernel_qualified(scenario, "EngineeringIncrement")
    lines = [f"part def <IncrementDefinitionName> :> {qualified};",
             f"part <'{NEW}'> <usageName> : <IncrementDefinitionName>;"]
    assert step["authoring"]["declarations"] == lines
    assert step["authoring"]["imports"] == [f"private import {package}::*;"]
    assert step["what_to_author"].startswith("declare the increment usage with its identifier")
    assert " ".join(lines) in step["what_to_author"] and f"private import {package}::*;" in step["what_to_author"]
    (named,) = step["authoring"]["types"]
    assert (named["qualified_name"], named["element_id"]) == (
        qualified, scenario.vocabulary["EngineeringIncrement"]["@id"])
    assert named["admits"] == "the increment's own definition specializes it"
    # The method's form only: the remedy never offers to type the usage by the kernel definition itself.
    assert f": {qualified};" not in step["what_to_author"]


def test_a_new_increment_s_problem_statement_takes_the_increment_definition_as_subject() -> None:
    """The problem statement's subject is typed by the increment's own definition, declared first in the
    same remedy; once the increment resolves, by the definition that types its usage."""
    scenario, _steps, _types = _kernel_scenario()
    qualified, _package = _kernel_qualified(scenario, "EngineeringIncrement")
    problem, _types = _kernel_qualified(scenario, "ProblemStatement")
    for gate in ("incrementHasProblemStatement", "incrementHasStakeholder"):
        declarations = _gap(_evaluate(scenario, NEW).gaps(), gate)["authoring"]["declarations"]
        assert declarations[0] == f"part def <IncrementDefinitionName> :> {qualified};", gate
        assert declarations[1].startswith(
            f"requirement <problemStatementName> : {problem} {{ subject increment : <IncrementDefinitionName>; "), gate
    resolved = [g for g in _evaluate(scenario).phase_contract()["gates"]
                if g["obligation_id"] == "incrementHasProblemStatement"][0]
    assert resolved["authoring"]["declarations"] == [
        f"requirement <problemStatementName> : {problem} {{ subject increment : DE4SDV_FixtureFraming::FixtureIncrement; }}"]


# -- the accepted forms (oracle) ---------------------------------------------------------
#
# The SysML a remedy may suggest, written here from the accepted-forms rules
# (~/.claude/skills/de4sdv-sysml-accepted-forms) and from forms licensed Syside accepted in
# the model (INC-AEBS-010's framing, the AEBS needs and evidence slices) and in the method-loop
# test increment INC-TEST-001 (PR #353). A placeholder <...> stands for a name or text.

import re  # noqa: E402

_NAME = r"(?:<[^<>]+>|[A-Za-z_]\w*)"
_SEGMENT = r"(?:[A-Za-z_]\w*|'[^'\\]*(?:\\.[^'\\]*)*')"
_QN = rf"{_SEGMENT}(?:::{_SEGMENT})+"
_PACKAGE = rf"{_SEGMENT}(?:::{_SEGMENT})*"
_REF = rf"(?:{_QN}|<[^<>]+>)"
_TEXT = r'"[^"]*"'
_ITEM = rf"(?:{_REF}|{_TEXT})"
_VALUE = rf"(?:{_ITEM}|\({_ITEM}(?:, {_ITEM})*\))"
_DOC = r"doc /\* [^*]* \*/"
#: The members a remedy may suggest, by kind.
_MEMBER_FORMS = {
    "doc": _DOC,
    "subject": rf"subject(?: {_NAME} (?::|:>) {_REF})?;",  # 'subject;': INC-AEBS-010's concerns
    "stakeholder": rf"stakeholder {_NAME} : {_REF};",
    "redefinition": rf"(?:ref part|attribute) :>> (?:[A-Za-z_]\w*|{_QN}) = {_VALUE};",  # charters, library attributes
    "statement": r'require constraint statement \{ language "English" /\* [^*]* \*/ \}',
    "objective": rf"objective \{{ verify {_REF}; \}}",
    "verify": rf"verify {_REF};",
    "frame": rf"frame {_REF};",
    "viewpoint": rf"viewpoint {_NAME} : {_REF} \{{ frame {_REF}; \}}",  # INC-TEST-001's view
}
#: The members each container's body may hold. A subject, stakeholder, statement or framed concern is a
#: member of a requirement (a concern is one; a case has a subject); a verify sits in a case's objective;
#: a viewpoint in a view; a redefinition in the part or requirement that inherits the feature.
_CONTAINS = {
    "part": ("doc", "redefinition"),
    "action": ("doc",),  # the AEBS flows
    "requirement": ("doc", "subject", "stakeholder", "redefinition", "statement", "frame"),
    "concern": ("doc", "subject", "stakeholder"),
    "verification": ("doc", "subject", "objective"),
    "view": ("doc", "viewpoint"),
}


def _container(keyword: str) -> str:
    members = "|".join(_MEMBER_FORMS[kind] for kind in _CONTAINS[keyword])
    return rf"{keyword} (?:<'[^']*'> )?{_NAME}(?: : {_REF})?(?:;| \{{(?: (?:{members}))+ \}})"


#: Lines that stand on their own in a package.
TOP_LEVEL_FORMS = [
    rf"private import {_PACKAGE}::\*;",  # the rule: a direct import of the owning package
    # part/requirement/concern/verification/view: the framings and slices above; action: the AEBS flows
    *(_container(keyword) for keyword in _CONTAINS),
    rf"(?:part|viewpoint) def {_NAME}(?: :> {_REF})?(?:;| \{{ {_DOC} \}})",
    rf"connection {_NAME} : {_REF} connect {_REF} to {_REF};",  # DerivesFromNeed, ValidationPlanningAssociation
    rf"allocation {_NAME} allocate {_REF} to {_REF};",  # the AEBS requirement allocations
    rf"dependency {_NAME} from {_REF} to {_REF};",  # the AEBS evidence dependencies
]
#: A member on its own line: only in a remedy for an existing element, the container its instruction names.
MEMBER_FORMS = list(_MEMBER_FORMS.values())
ACCEPTED_FORMS = [*TOP_LEVEL_FORMS, *MEMBER_FORMS]
#: Constructs that are not SysML: the old fallback for a relation check without a remedy.
NOT_SYSML = (re.compile(r"\badd an? \w+ relation\b"), re.compile(r"\brelation from\b"), re.compile(r"verifiedBy"))
#: A type position: after ':' (typing), or after ':>' following a definition's name (specialization).
#: After a usage's name, ':>' subsets another usage, which a placeholder may name.
_TYPE_POSITION = re.compile(r"(?<![:>]):\s+(<[^<>]+>)|\bdef\s+\S+\s+:>\s+(<[^<>]+>)")


def _accepted(line: str, forms: list[str]) -> bool:
    return any(re.fullmatch(form, line) for form in forms)


def _for_an_existing_element(record: dict) -> bool:
    """Whether a record's remedy is built for an existing element (its first subject), the container
    its instruction names: a subject with an element, and no population or identity violation (whose
    remedy declares a subject instead)."""
    subjects = record.get("subjects") or []
    violations = {"POPULATION_POLICY_VIOLATION", "SCOPE_RESOLUTION_ERROR"}
    return any(subject.get("element_id") for subject in subjects) and not violations & set(
        record.get("reason_codes") or [])


def _declared_placeholders(lines: list[str]) -> set[str]:
    """Placeholders a remedy itself declares, as a definition or a usage name."""
    found = set()
    for line in lines:
        found |= set(re.findall(r"\bdef (<[^<>]+>)", line))
        found |= set(re.findall(r"\b(?:part|concern|requirement|view|verification) (<[^<>]+>)", line))
    return found


def _problems(record: dict, names: QualifiedNameIndex, own_package: str | None = None) -> list[str]:
    """Why one answer record's remedy is not authorable SysML (empty: it is)."""
    text = record.get("what_to_author") or record.get("what_satisfies") or ""
    authoring = record.get("authoring") or {}
    lines = list(authoring.get("declarations") or [])
    imports = list(authoring.get("imports") or [])
    found = []
    members_allowed = _for_an_existing_element(record)
    for line in [*lines, *imports]:
        if not _accepted(line, TOP_LEVEL_FORMS):
            if not _accepted(line, MEMBER_FORMS):
                found.append(f"not an accepted form: {line}")
            elif not members_allowed:
                found.append(f"a member outside its container: {line}")
        if line not in text:
            found.append(f"not in the text: {line}")
    for pattern in NOT_SYSML:
        if pattern.search(text):
            found.append(f"names a construct that is not SysML: {pattern.pattern}")
    declared = _declared_placeholders(lines)
    for line in lines:
        for placeholder in (typed or specialized for typed, specialized in _TYPE_POSITION.findall(line)):
            if placeholder not in declared:
                found.append(f"a type placeholder {placeholder} in: {line}")
        for name in re.findall(_QN, line):
            if len(names.resolve(name)) != 1:
                found.append(f"{name} does not resolve to one element")
    for named in authoring.get("types") or []:
        package = (named.get("qualified_name") or "").rpartition("::")[0]
        if named.get("qualified_name") and package != own_package:
            wanted = [i for i in imports if re.fullmatch(rf"private import ({_PACKAGE})::\*;", i)
                      and named["qualified_name"].startswith(i[len("private import "):-len("::*;")] + "::")]
            if not wanted:
                found.append(f"no import names the package of {named['qualified_name']}")
    return found


def _remedied(answer: dict) -> list[dict]:
    """The records of an answer that say what to author or what satisfies a gate."""
    records = [*(answer.get("blocking") or []), *(answer.get("advisory") or []), *(answer.get("gates") or [])]
    if answer.get("next"):
        records.append(answer["next"])
    return [r for r in records if r.get("what_to_author") or r.get("what_satisfies")]


def test_every_remedy_the_live_workflow_declares_is_authorable_sysml() -> None:
    """Walk every check of the live workflow file, for a new increment (nothing declared, as in the
    throwaway-increment test's first call), for a declared one (``phase_contract``) and for failing
    subjects: every line is an accepted form, names only qualified types that resolve, carries their
    imports, and leaves no type placeholder; nothing names a construct that is not SysML."""
    scenario, steps, _types = _kernel_scenario()
    builder = scenario.builder
    for need in scenario.needs:
        builder.remove(builder.feature_of(need, "statement"))
    builder.remove(builder.feature_of(scenario.charter, "owner"))
    names = QualifiedNameIndex(builder.elements)
    declared = [check.name for step in steps for check in step.checks]
    new = _evaluate(scenario, NEW)
    walked: dict[str, list[str]] = {}
    for answer in (new.gaps(), _evaluate(scenario).phase_contract(), _evaluate(scenario).gaps()):
        for record in _remedied(answer):
            gate = record.get("gate") or record.get("obligation_id")
            walked.setdefault(gate, []).extend(_problems(record, names, "DE4SDV_FixtureFraming"))
    assert set(declared) <= set(walked), set(declared) - set(walked)
    assert {gate: problems for gate, problems in walked.items() if problems} == {}


def test_a_new_increment_s_remedies_name_no_type_placeholder() -> None:
    """The placeholders the throwaway-increment test counted (<IncrementDefinition>, <role>, <Viewpoint>,
    <Definition>, MethodPhase::...) are gone: only names and text the author chooses remain."""
    scenario, _steps, _types = _kernel_scenario()
    texts = [record["what_to_author"] for record in _remedied(_evaluate(scenario, NEW).gaps())]
    assert len(texts) >= 24
    for placeholder in ("<IncrementDefinition>", "<role>", "<Viewpoint>", "<Definition>", "MethodPhase::...",
                        "<incrementUsage>", "<scenario>"):
        assert not [text for text in texts if placeholder in text], placeholder


# -- the Method Check report -------------------------------------------------------------


def test_the_method_check_summary_shows_the_lines_to_author_as_a_sysml_block() -> None:
    """Under "What to author", the report adds the imports and declarations as a SysML block to copy."""
    from scripts import method_check

    scenario, _steps, _types = _kernel_scenario()
    step = _evaluate(scenario, NEW).next_obligation()["next"]
    entry = {"id": NEW, "outcome": "evaluated", "usage": {}, "charters": [], "next": step, "next_reason": "",
             "counts": {"blocking": 1, "blocking_by_kind": {}, "advisory": 0}, "phase_exits": {},
             "diagnostics": [], "evaluation": {"gaps": {"blocking": [], "advisory": []}, "next": {}}}
    text = method_check.render_summary({"revision": "a" * 40, "export": {}, "increments": [entry], "notes": [],
                                        "errors": []})
    lines = text.splitlines()
    at = lines.index(f"- What to author: `{step['what_to_author']}`")
    block = [*step["authoring"]["imports"], *step["authoring"]["declarations"]]
    assert lines[at + 1:at + 4 + len(block)] == ["", "  ```sysml", *(f"  {line}" for line in block), "  ```"]


# -- the rules, one by one -------------------------------------------------------------------


def _gap(answer: dict, gate: str) -> dict:
    (entry,) = [e for e in [*answer["blocking"], *answer["advisory"]] if e["gate"] == gate]
    return entry


def _types_by_id(record: dict) -> dict[str, dict]:
    return {named["element_id"]: named for named in record["authoring"]["types"]}


def test_the_types_a_remedy_names_are_the_ones_its_check_admits() -> None:
    """From the check's own type test: the parameter's type lineage; a relation's carrier and end class
    (validated kernel bindings); a check that tests no type says so."""
    scenario, _steps, _types = _kernel_scenario()
    vocabulary, kernel = scenario.vocabulary, scenario.builder.kernel_definition
    gaps = _evaluate(scenario, NEW).gaps()
    planned = _types_by_id(_gap(gaps, "needHasValidationScenario"))
    assert set(planned) == {vocabulary["ValidationPlanningAssociation"]["@id"], kernel("ValidationScenario")["@id"]}
    derived = _types_by_id(_gap(gaps, "requirementDerivesFromNeed"))
    assert set(derived) == {vocabulary["DerivesFromNeed"]["@id"], vocabulary["Need"]["@id"]}
    stakeholder = _types_by_id(_gap(gaps, "incrementHasStakeholder"))[vocabulary["Stakeholder"]["@id"]]
    assert "the check tests no stakeholder type" in stakeholder["admits"]
    framed = _gap(gaps, "incrementHasFramedConcern")
    assert any("tests no viewpoint or concern type" in note for note in framed["authoring"]["notes"])


def test_a_member_is_declared_with_the_keyword_of_the_feature_it_redefines() -> None:
    """``ref part :>> increment`` because the charter class's increment feature is a referential part
    usage; the same remedy over a composite feature says ``part``."""
    scenario, _steps, _types = _kernel_scenario()
    builder = scenario.builder
    builder.remove(builder.feature_of(scenario.charter, "increment"))
    step = _evaluate(scenario).next_obligation()["next"]
    assert step["gate"] == "incrementHasCharter"
    assert step["authoring"]["declarations"] == ["ref part :>> increment = DE4SDV_FixtureFraming::incFixture;"]
    assert step["what_to_author"].startswith("reference the increment from DE4SDV_FixtureFraming::fixtureCharter: ")
    builder.feature_of(scenario.vocabulary["IncrementTraceObligations"], "increment")["isComposite"] = True
    step = _evaluate(scenario).next_obligation()["next"]
    assert step["authoring"]["declarations"] == ["part :>> increment = DE4SDV_FixtureFraming::incFixture;"]
    owner = _gap(_evaluate(scenario, NEW).gaps(), "incrementHasOwner")
    assert 'attribute :>> owner = "<owner>";' in owner["authoring"]["declarations"][0]


def test_the_charter_is_declared_holding_its_reference_to_the_increment_usage() -> None:
    scenario, _steps, _types = _kernel_scenario()
    charter = _gap(_evaluate(scenario, NEW).gaps(), "incrementHasCharter")
    (line,) = charter["authoring"]["declarations"]
    assert line == "part <charterName> : FixtureMethodTypes::IncrementCharter { ref part :>> increment = <usageName>; }"
    assert "after the increment usage" in charter["what_to_author"]
    # The same name the increment's own remedy declares.
    identifier = _gap(_evaluate(scenario, NEW).gaps(), "incrementHasIdentifier")
    assert identifier["authoring"]["declarations"][1] == f"part <'{NEW}'> <usageName> : <IncrementDefinitionName>;"


def test_applicable_phases_lists_the_literals_of_the_enumeration_and_marks_the_checked_phases() -> None:
    """All MethodPhase literals, qualified, in the enumeration's order, read from the view (a literal
    added to the enumeration is listed too), with the phases whose steps have executable checks marked."""
    scenario, steps, _types = _kernel_scenario()
    builder = scenario.builder
    enumeration = scenario.vocabulary.get("MethodPhase") or builder.kernel_definition("MethodPhase")
    package = builder.kernel_package(builder.sources[enumeration["@id"]])["declaredName"]
    extra = builder.new("EnumerationUsage", name="phase13_retrospective", source=builder.sources[enumeration["@id"]])
    builder.own(enumeration, extra, kind="VariantMembership", member_name="phase13_retrospective")
    checked = {step.phase for step in steps if step.checks}
    entry = _gap(_evaluate(scenario, NEW).gaps(), "incrementDeclaresApplicablePhases")
    names = [*scenario.phases, "phase13_retrospective"]
    assert entry["authoring"]["phases"] == [
        {"literal": f"{package}::MethodPhase::{name}", "name": name, "executable_checks": name in checked}
        for name in names]
    assert f"private import {package}::*;" in entry["authoring"]["imports"]
    assert "MethodPhase::..." not in entry["what_to_author"]
    for name in names:
        assert f"{package}::MethodPhase::{name}" in entry["what_to_author"]


def test_an_untyped_parameter_is_declared_by_its_keyword_and_marked_as_a_metaclass() -> None:
    scenario, _steps, _types = _kernel_scenario()
    gates = {gate["obligation_id"]: gate for gate in _evaluate(scenario).phase_contract()["gates"]}
    concern, case = gates["incrementHasFramedConcern"], gates["verificationCaseVerifiesRequirement"]
    for gate, metaclass, keyword in ((concern, "ConcernUsage", "concern"), (case, "VerificationCaseUsage",
                                                                             "verification")):
        assert (gate["subject_type"], gate["subject_type_kind"], gate["subject_keyword"]) == (
            metaclass, "metaclass", keyword)
        assert "not a model element" in gate["subject_type_note"]
        assert gate["authoring"]["declarations"][0].startswith(f"{keyword} <")
    typed = gates["incrementHasIdentifier"]
    assert (typed["subject_type_kind"], typed["subject_keyword"]) == ("definition", "part")
    assert "subject_type_note" not in typed


def test_a_remedy_that_adds_stakeholders_declares_the_subject_first() -> None:
    scenario, _steps, _types = _kernel_scenario()
    gaps = _evaluate(scenario, NEW).gaps()
    for gate in ("incrementHasStakeholder", "needHasStakeholder", "incrementHasFramedConcern"):
        entry = _gap(gaps, gate)
        (line,) = [d for d in entry["authoring"]["declarations"] if "stakeholder " in d]
        assert re.search(r"\{ (?:doc /\* [^*]* \*/ )?subject\b[^;]*; stakeholder ", line), (gate, line)
        assert SUBJECT_FIRST in entry["authoring"]["notes"], gate
    builder = scenario.builder
    need = scenario.needs[1]
    builder.remove(*[e for e in builder.elements if e.get("@type") in ("StakeholderMembership", "SubjectMembership")
                     and e.get("owningRelatedElement", {}).get("@id") == need["@id"]])
    entry = _gap(_evaluate(scenario).gaps(), "needHasStakeholder")
    assert entry["authoring"]["declarations"][0].startswith("subject ")
    assert entry["authoring"]["declarations"][1].startswith("stakeholder ")


def test_the_system_of_interest_lines_are_declared_inside_the_charter_and_the_need() -> None:
    """The charter's systemOfInterest line is a member of the charter, the subject line a member of the
    need: each sits in its container's block. A new increment's charter is typed like the workflow's
    charter parameter; an increment's own charter is restated as declared. A bare subject line comes
    only in the remedy for an existing need, which its instruction names. With a system of interest
    declared, the subject alone."""
    scenario, _steps, types = _kernel_scenario()
    builder = scenario.builder
    need = _owner_qualified(builder, types["StakeholderNeedCandidate"])
    charter = _owner_qualified(builder, types["IncrementCharter"])
    system = ["part def <SystemName> { doc /* <the system of interest> */ }", "part <systemUsage> : <SystemName>;"]
    new = _gap(_evaluate(scenario, NEW).gaps(), "needSubjectIsSystemOfInterest")
    assert new["authoring"]["declarations"] == [
        *system, f"part <charterName> : {charter} {{ ref part :>> systemOfInterest = <systemUsage>; }}",
        f"requirement <name> : {need} {{ subject <subjectName> :> <systemUsage>; }}"]
    existing = _gap(_evaluate(scenario).gaps(), "needSubjectIsSystemOfInterest")  # the needs take the increment
    assert existing["authoring"]["declarations"] == [
        *system, "part fixtureCharter : DE4SDV_FixtureFraming::FixtureCharter "
                 "{ ref part :>> systemOfInterest = <systemUsage>; }", "subject <subjectName> :> <systemUsage>;"]
    assert existing["what_to_author"].startswith(
        "declare the system of interest in the increment's package, reference it from the charter and take it as "
        f"the subject of {existing['subjects'][0]['qualified_name']}, never the increment: ")
    system_definition = builder.definition("PartDefinition", "FixtureSystem", scenario.framing)
    builder.attribute(scenario.charter, "systemOfInterest",
                      builder.usage("PartUsage", "fixtureSystem", scenario.framing, [system_definition]), kind="PartUsage")
    evaluation = _evaluate(scenario)
    (gate,) = [g for g in evaluation.phase_contract()["gates"] if g["obligation_id"] == "needSubjectIsSystemOfInterest"]
    assert gate["authoring"]["declarations"] == [
        f"requirement <name> : {need} {{ subject <subjectName> :> DE4SDV_FixtureFraming::fixtureSystem; }}"]
    assert _gap(evaluation.gaps(), "needSubjectIsSystemOfInterest")["authoring"]["declarations"] == [
        "subject <subjectName> :> DE4SDV_FixtureFraming::fixtureSystem;"]


def test_a_new_charter_s_features_are_the_ones_its_type_inherits() -> None:
    """A new increment's charter is typed like the workflow's charter parameter, so its systemOfInterest
    line redefines the feature that type inherits, by its bare name: never a feature that other charter
    definitions of the model declare (two of them redefine systemOfInterest here)."""
    scenario, _steps, types = _kernel_scenario()
    builder = scenario.builder
    inherited = builder.feature_of(scenario.vocabulary["IncrementTraceObligations"], "systemOfInterest")
    for name in ("ProjectACharter", "ProjectBCharter"):
        definition = builder.definition("PartDefinition", name, builder.package(f"{name}Package"),
                                        [types["IncrementCharter"]])
        feature = _feature(builder, definition, "PartUsage", "systemOfInterest")
        builder.relationship("Redefinition", feature, general={"@id": inherited["@id"]}, specific={"@id": feature["@id"]},
                             redefinedFeature={"@id": inherited["@id"]}, redefiningFeature={"@id": feature["@id"]})
    entry = _gap(_evaluate(scenario, NEW).gaps(), "needSubjectIsSystemOfInterest")
    declarations = entry["authoring"]["declarations"]
    assert [line for line in declarations if "ProjectACharter" in line or "ProjectBCharter" in line] == []
    assert (f"part <charterName> : {_owner_qualified(builder, types['IncrementCharter'])} "
            "{ ref part :>> systemOfInterest = <systemUsage>; }") in declarations
    assert [note for note in entry["authoring"]["notes"] if "inherited features" in note or "ambiguous" in note] == []


def test_a_population_remedy_says_how_many_to_keep_and_how_one_is_declared() -> None:
    scenario, _steps, types = _kernel_scenario()
    builder = scenario.builder
    builder.remove(*[e for e in builder.elements if e.get("declaredName") == "fixtureAssumption"])
    entry = _gap(_evaluate(scenario).gaps(), "incrementHasAssumption")
    qualified, _package = _kernel_qualified(scenario, "Assumption")
    line = f"part <name> : {qualified} {{ doc /* <text> */ }}"
    assert entry["what_to_author"].startswith("keep at least 1 IncrementAssumption in the increment's package (")
    assert f"one is declared as: {line}" in entry["what_to_author"]
    assert entry["authoring"]["declarations"] == [line]


def _owner_qualified(builder: ModelBuilder, definition: dict) -> str:
    """``<package>::<name>`` of a definition a package owns: the builder's construction (the oracle)."""
    by_id = {e["@id"]: e for e in builder.elements}
    package = by_id[by_id[definition["owningRelationship"]["@id"]]["owningRelatedElement"]["@id"]]
    assert package["@type"] in ("Package", "LibraryPackage"), package["@type"]
    return f"{package['declaredName']}::{definition['declaredName']}"


def test_a_population_remedy_declares_the_element_it_counts_first_and_complete() -> None:
    """No need and no requirement at all, while phases 4, 5 and 10 apply. Each population remedy about
    the needs or the requirements declares one of them first, by the parameter's keyword and type (the
    live workflow file, read lexically), with what its check asks of it inside it. The lines the check
    needs besides it (a scenario and its connection, a DerivesFromNeed connection, the system of interest)
    follow it after "then:", and a connection or case among them refers to it by the name it is declared
    with: never "one is declared as" followed by another element."""
    scenario, steps, types = _kernel_scenario()
    builder = scenario.builder
    builder.remove(*scenario.needs, *scenario.requirements)
    about = {check.name: parameter for step in steps for check in step.checks
             for parameter in step.parameters if parameter.name == check.about}
    gaps = _evaluate(scenario).gaps()
    population = [entry for entry in [*gaps["blocking"], *gaps["advisory"]]
                  if "POPULATION_POLICY_VIOLATION" in entry["reason_codes"]
                  and about[entry["gate"]].name in ("needs", "requirements")]
    assert {"needHasStatement", "needHasValidationScenario", "needSubjectIsSystemOfInterest",
            "requirementDerivesFromNeed", "requirementSubjectIsSystemOfInterest"} <= {entry["gate"] for entry in population}
    for entry in population:
        parameter = about[entry["gate"]]
        declarations, text = entry["authoring"]["declarations"], entry["what_to_author"]
        first, rest = declarations[0], declarations[1:]
        declared = re.fullmatch(rf"{parameter.keyword} (<[^<>]+>) : {re.escape(_owner_qualified(builder, types[parameter.type]))}"
                                r"(?:;| \{ .+ \})", first)
        assert declared, (entry["gate"], first)
        assert f"one is declared as: {first}" in text, entry["gate"]
        if rest:
            assert f"{first} then: {' '.join(rest)}" in text, entry["gate"]
        for line in rest:
            if line.startswith(("connection ", "verification ")):
                assert re.search(rf"(?:connect|to|verify) {re.escape(declared.group(1))}(?=[; ])", line), (
                    entry["gate"], line)


def test_a_type_outside_any_package_is_named_without_an_import() -> None:
    """A definition without an owning package has no qualified name: it is named, never qualified or
    imported by guess, and the remedy says so."""
    scenario = increment_scenario()
    _needs_workflow(scenario)
    step = _evaluate(scenario, NEW).next_obligation()["next"]
    assert step["authoring"]["declarations"] == [f"part def <IncrementDefinitionName> :> EngineeringIncrement;",
                                                 f"part <'{NEW}'> <usageName> : <IncrementDefinitionName>;"]
    assert step["authoring"]["imports"] == []
    assert any("has no qualified name" in note for note in step["authoring"]["notes"])


def test_the_increment_s_own_package_is_never_imported() -> None:
    scenario, _steps, _types = _kernel_scenario()
    builder = scenario.builder
    problem = next(e for e in builder.elements if e.get("declaredName") == "fixtureProblemStatement")
    builder.remove(builder.feature_of(problem, "increment"))
    entry = _gap(_evaluate(scenario).gaps(), "incrementHasProblemStatement")
    assert entry["authoring"]["declarations"] == ["subject increment : DE4SDV_FixtureFraming::FixtureIncrement;"]
    assert entry["authoring"]["imports"] == []


def test_a_member_named_twice_in_the_lineage_is_never_picked_and_each_candidate_is_listed() -> None:
    """Two inherited features named alike (as SYSMOD's and the NRM's stability are): SysML's bare name is
    ambiguous there and no rule here picks one (an element-id order is none), so no line redefines it;
    a note says so and lists each candidate's qualified name, as an ambiguous name's refusal does."""
    scenario, _steps, _types = _kernel_scenario()
    builder = scenario.builder
    holder = builder.library["__holder__"]  # the library attribute base the fixture's needs specialize
    builder.own(builder.package("FixtureLibrary"), holder, member_name=holder["declaredName"])
    other = builder.definition("RequirementDefinition", "OtherAttributes", builder.package("FixtureOtherLibrary"))
    _feature(builder, other, "AttributeUsage", "source")
    need_definition = next(e for e in builder.elements if e.get("declaredName") == "FixtureNeed")
    builder.specializes(need_definition, other)
    builder.remove(builder.feature_of(scenario.needs[1], "source"))
    entry = _gap(_evaluate(scenario).gaps(), "needHasSource")
    assert entry["authoring"]["declarations"] == []
    (note,) = [note for note in entry["authoring"]["notes"] if "ambiguous" in note]
    for candidate in (f"FixtureLibrary::{holder['declaredName']}::source", "FixtureOtherLibrary::OtherAttributes::source"):
        assert candidate in note, note
    assert note in entry["what_to_author"]


def test_a_remedy_says_what_to_author_never_that_authoring_it_proves_anything() -> None:
    scenario, _steps, _types = _kernel_scenario()
    texts = [r.get("what_to_author") or r.get("what_satisfies") for answer in (
        _evaluate(scenario, NEW).gaps(), _evaluate(scenario).phase_contract()) for r in _remedied(answer)]
    claims = re.compile(r"\b(?:prove|proves|proof|complian\w*|certif\w*|homolog\w*|satisf\w*|accept\w*|pass\w*)\b",
                        re.IGNORECASE)
    assert [text for text in texts if claims.search(text)] == []


def test_every_relation_check_names_sysml_or_says_nothing_is_authored_in_the_model() -> None:
    """Every relation a workflow may check (the contract's relations and the native ones), with and
    without a subject: SysML in accepted forms, or, for a relation without a SysML mapping or with
    external content, that nothing is authored in the model (method side). ``verifiedBy`` is a
    ``verify`` in a verification case's objective."""
    from de4sdv.semantic.relation_checks import relation_checks
    from de4sdv.semantic.remedies import check_remedy

    scenario, _steps, _types = _kernel_scenario()
    view = _view(scenario)
    names = QualifiedNameIndex(scenario.builder.elements)
    requirement = scenario.requirements[0]["@id"]
    relations = sorted(relation_checks(view))
    assert {"verifiedBy", "derivesRequirementFromNeed", "hasValidationScenario", "frame", "verify"} <= set(relations)
    for relation in relations:
        for subject in (None, requirement):
            remedy = check_remedy(view, relation, subject=subject)
            record = {"what_to_author": remedy.text, "authoring": remedy.authoring(),
                      "subjects": [{"element_id": subject}] if subject else []}
            assert _problems(record, names) == [], (relation, subject)
            assert remedy.declarations or "nothing to author in the model" in remedy.text, (relation, remedy.text)
    verified = check_remedy(view, "verifiedBy", subject=requirement)
    assert verified.declarations == (
        "verification <name> { objective { verify DE4SDV_FixtureNeedsRequirements::requirement0; } }",)


def test_the_derivation_line_connects_the_ends_in_the_order_the_carrier_declares() -> None:
    """``connect a to b`` binds the carrier's first end to ``a``. The line follows the order in which the
    carrier declares its ends, in both serialized shapes (the export's FeatureMembership of an isEnd usage,
    and EndFeatureMembership), never the order the roles happen to be passed in."""
    config = model_contract().relationship_mapping("derivesRequirementFromNeed").configuration
    placeholder = {config["need_role"]: "<need>", config["requirement_role"]: "<requirement>"}
    for membership in ("FeatureMembership", "EndFeatureMembership"):
        for order in (list(placeholder), list(placeholder)[::-1]):
            scenario, _steps, _types = _kernel_scenario()
            builder = scenario.builder
            carrier = scenario.vocabulary["DerivesFromNeed"]
            for role in order:
                end = builder.new("ReferenceUsage", name=role, source=builder.sources[carrier["@id"]], isEnd=True)
                builder.own(carrier, end, kind=membership, member_name=role)
            entry = _gap(_evaluate(scenario, NEW).gaps(), "requirementDerivesFromNeed")
            (line,) = [d for d in entry["authoring"]["declarations"] if d.startswith("connection ")]
            assert line.endswith(f" connect {placeholder[order[0]]} to {placeholder[order[1]]};"), (
                membership, order, line)


# -- the service and its tool descriptions ---------------------------------------------------


def test_the_method_tools_answer_with_authoring_and_their_descriptions_say_so() -> None:
    from de4sdv.semantic.mcp_server import create_mcp_server
    from de4sdv.sysml_api.repository import SysMLRepository
    from model_contract_fixtures import binding, model_service

    class _Repository(SysMLRepository):
        def __init__(self, elements):
            super().__init__(client=None)  # type: ignore[arg-type]
            self.elements = elements

        def list_elements(self, project_id, commit_id):
            return self.elements

    scenario, _steps, _types = _kernel_scenario()
    builder = scenario.builder
    service = model_service(binding(git_commit="a" * 40, kernel_bindings=builder.bindings),
                            _Repository(builder.elements))
    step = service.next_obligation(increment=NEW)["next"]
    qualified, package = _kernel_qualified(scenario, "EngineeringIncrement")
    assert step["authoring"]["imports"] == [f"private import {package}::*;"]
    assert qualified in step["authoring"]["declarations"][0]
    gates = service.phase_contract(increment=NEW)["gates"]
    assert all(gate["authoring"]["declarations"] or "nothing to author" in gate["what_satisfies"] for gate in gates)
    tools = {tool.name: " ".join(tool.description.split())
             for tool in create_mcp_server(service)._tool_manager.list_tools()}
    for name in ("method_gaps", "next_obligation", "phase_contract"):
        assert "`authoring`" in tools[name] and "`private import`" in tools[name], name
        assert "`phases`" in tools[name], name  # authoring.phases: the MethodPhase literals
    assert "`subject_type_kind`" in tools["phase_contract"]
    assert "`parameter_element_id`" in tools["phase_contract"]
    guide = (REPO_ROOT / "docs/guides/drive-an-increment-with-the-method-tools.md").read_text(encoding="utf-8")
    assert "`parameter_element_id`" in guide and "`phases`" in guide


def test_a_population_remedy_names_an_untyped_parameter_by_its_keyword() -> None:
    """No verification case at all: each check about the untyped ``verification`` parameter says how many
    verification usages to keep and how one is declared, also when the check's own remedy is method side."""
    scenario, _steps, _types = _kernel_scenario()
    builder = scenario.builder
    builder.remove(*scenario.cases)
    gaps = _evaluate(scenario).gaps()
    verifies = _gap(gaps, "verificationCaseVerifiesRequirement")
    evidence = _gap(gaps, "verificationCaseHasEvidenceRecordOrStatus")
    for entry in (verifies, evidence):
        assert entry["what_to_author"].startswith(
            "keep at least 1 verification usage in the increment's packages named in the charter's expectedArtifacts")
    assert verifies["authoring"]["declarations"] == [
        "verification <name> { objective { verify <requirement of the increment>; } }"]
    assert evidence["authoring"]["declarations"] == ["verification <name>;"]


def test_known_looseness_the_checks_accept_an_increment_typed_by_the_kernel_definition_itself() -> None:
    """A known looseness, not the method's form: incrementShortName and problemStatementSubject test the
    type lineage and the usage's own typing, so a usage typed directly by EngineeringIncrement (and a problem
    statement subject typed the same way) passes them. The remedies teach the method's form instead, a
    definition specializing EngineeringIncrement (what every scenario here declares). Tightening the checks
    is a later method decision; this test records the looseness until then."""
    scenario, _steps, _types = _kernel_scenario()
    kernel = scenario.vocabulary["EngineeringIncrement"]
    _typed_by_the_kernel_definition_itself(scenario)
    evaluation = _evaluate(scenario)
    verdicts = {u.unit_id: u.verdict for u in evaluation.canonical.units}
    assert verdicts["incrementHasIdentifier"] == me.VERDICT_PASS
    assert verdicts["incrementHasProblemStatement"] == me.VERDICT_PASS
    assert evaluation.scope.definition_ids == (kernel["@id"],)


def _typed_by_the_kernel_definition_itself(scenario) -> dict:
    """Retype the increment usage and the problem statement's subject by the kernel EngineeringIncrement
    itself (the known looseness); returns the problem statement."""
    builder = scenario.builder
    kernel = scenario.vocabulary["EngineeringIncrement"]
    problem = next(e for e in builder.elements if e.get("declaredName") == "fixtureProblemStatement")
    for typed in (scenario.usage, builder.feature_of(problem, "increment")):
        for typing in [e for e in builder.elements if e.get("@type") == "FeatureTyping"
                       and e.get("typedFeature", {}).get("@id") == typed["@id"]]:
            typing["type"] = typing["general"] = {"@id": kernel["@id"]}
    return problem


def test_an_increment_typed_by_the_kernel_definition_itself_is_taught_the_method_form() -> None:
    """The looseness above is never echoed. For an increment usage typed by the kernel EngineeringIncrement
    itself, the remedies declare the increment's own definition specializing it, retype the usage by it
    and type the problem statement's subject by it, with one note naming the looseness. (A usage typed
    by a definition of its own keeps naming it: the problem-statement test above.)"""
    scenario, _steps, _types = _kernel_scenario()
    problem = _typed_by_the_kernel_definition_itself(scenario)
    qualified, _package = _kernel_qualified(scenario, "EngineeringIncrement")
    statement, _package = _kernel_qualified(scenario, "ProblemStatement")
    define = f"part def <IncrementDefinitionName> :> {qualified};"
    retyped = f"part <'{scenario.increment_id}'> incFixture : <IncrementDefinitionName>;"
    subject = "subject increment : <IncrementDefinitionName>;"
    gates = {gate["obligation_id"]: gate for gate in _evaluate(scenario).phase_contract()["gates"]}
    assert gates["incrementHasIdentifier"]["authoring"]["declarations"] == [
        define, f"part <'{scenario.increment_id}'> <usageName> : <IncrementDefinitionName>;"]
    assert gates["incrementHasProblemStatement"]["authoring"]["declarations"] == [
        define, retyped, f"requirement <problemStatementName> : {statement} {{ {subject} }}"]
    assert gates["incrementHasStakeholder"]["authoring"]["declarations"][:2] == [define, retyped]
    scenario.builder.remove(scenario.builder.feature_of(problem, "increment"))
    gap = _gap(_evaluate(scenario).gaps(), "incrementHasProblemStatement")
    assert gap["authoring"]["declarations"] == [define, retyped, subject]
    for record in (gates["incrementHasIdentifier"], gates["incrementHasProblemStatement"], gap):
        named = [note for note in record["authoring"]["notes"]
                 if "DE4SDV_FixtureFraming::incFixture" in note and qualified in note]
        assert len(named) == 1, record["authoring"]["notes"]
    texts = [record.get("what_to_author") or record.get("what_satisfies") for record in (*gates.values(), gap)]
    assert [text for text in texts if f": {qualified};" in text or f"subject increment : {qualified};" in text] == []
