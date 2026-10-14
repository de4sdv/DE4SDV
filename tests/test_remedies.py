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
    """A workflow whose needs step checks the statement of each need."""
    increment_workflow(scenario.builder, [
        WorkflowStep("frameIncrement", P0, (P("increment", "EngineeringIncrement"),)),
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


def test_a_new_increment_is_told_to_declare_its_usage_typed_by_the_qualified_kernel_definition() -> None:
    """``out part increment : EngineeringIncrement``: the keyword, the qualified type and its import."""
    scenario, _steps, _types = _kernel_scenario()
    step = _evaluate(scenario, NEW).next_obligation()["next"]
    assert step["gate"] == "incrementHasIdentifier"
    qualified, package = _kernel_qualified(scenario, "EngineeringIncrement")
    line = f"part <'{NEW}'> <usageName> : {qualified};"
    assert step["authoring"]["declarations"] == [line]
    assert step["authoring"]["imports"] == [f"private import {package}::*;"]
    assert step["what_to_author"].startswith("declare the increment usage with its identifier")
    assert line in step["what_to_author"] and f"private import {package}::*;" in step["what_to_author"]
    (named,) = step["authoring"]["types"]
    assert (named["qualified_name"], named["element_id"]) == (
        qualified, scenario.vocabulary["EngineeringIncrement"]["@id"])
    assert "or a definition specializing it" in named["admits"]


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
_MEMBERS = [
    _DOC,
    r"subject;",  # INC-AEBS-010's concerns
    rf"subject {_NAME} (?::|:>) {_REF};",
    rf"stakeholder {_NAME} : {_REF};",
    rf"(?:ref part|attribute) :>> (?:[A-Za-z_]\w*|{_QN}) = {_VALUE};",  # the charters
    r'require constraint statement \{ language "English" /\* [^*]* \*/ \}',
    rf"objective \{{ verify {_REF}; \}}",
    rf"verify {_REF};",
    rf"frame {_REF};",
    rf"viewpoint {_NAME} : {_REF} \{{ frame {_REF}; \}}",  # INC-TEST-001's view
]
_MEMBER = "(?:" + "|".join(_MEMBERS) + ")"
_BODY = rf"(?:;| \{{(?: {_MEMBER})+ \}})"
ACCEPTED_FORMS = [
    rf"private import {_PACKAGE}::\*;",  # the rule: a direct import of the owning package
    rf"(?:part|requirement|concern|verification|view) (?:<'[^']*'> )?{_NAME}(?: : {_REF})?{_BODY}",
    rf"(?:part|viewpoint) def {_NAME}(?: :> {_REF})?(?:;| \{{ {_DOC} \}})",
    rf"connection {_NAME} : {_REF} connect {_REF} to {_REF};",  # DerivesFromNeed, ValidationPlanningAssociation
    rf"allocation {_NAME} allocate {_REF} to {_REF};",  # the AEBS requirement allocations
    rf"dependency {_NAME} from {_REF} to {_REF};",  # the AEBS evidence dependencies
    *_MEMBERS,  # a member added to an existing subject
]
#: Constructs that are not SysML: the old fallback for a relation check without a remedy.
NOT_SYSML = (re.compile(r"\badd an? \w+ relation\b"), re.compile(r"\brelation from\b"), re.compile(r"verifiedBy"))
#: A type position: after ':' (typing), or after ':>' following a definition's name (specialization).
#: After a usage's name, ':>' subsets another usage, which a placeholder may name.
_TYPE_POSITION = re.compile(r"(?<![:>]):\s+(<[^<>]+>)|\bdef\s+\S+\s+:>\s+(<[^<>]+>)")


def _accepted(line: str) -> bool:
    return any(re.fullmatch(form, line) for form in ACCEPTED_FORMS)


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
    for line in [*lines, *imports]:
        if not _accepted(line):
            found.append(f"not an accepted form: {line}")
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
