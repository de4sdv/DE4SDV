"""Configured product (phase 9) and baseline decision (phase 12): the kernel
classes, their admission and bindings, and the workflow parameters they type.

The owner decided both on 2026-10-28:

- Q1: the configured product, the main output of phase 9, gets a kernel class.
  The ontology maps it onto the PLEML feature configuration (relationship
  ``configuredBy``), and the kernel imports no PLEML package. ``variationPoints``
  becomes ``[0..*]``.
- Q2: the baseline decision is a kernel specialization of the lifecycle
  decision, with a disposition typed by an ontology enumeration (accepted,
  deferred, invalidated). ``IncrementGap`` gets a disposition too. Its typing
  identifies a baseline decision, never a name, and no check reads the
  baseline register.

Lexical source checks and the model-built contract. The licensed validation of
the definitions runs in CI. The binding test is synthetic: it proves the
ingestion rule (ADR 0011), not a licensed export. No check is about these
parameters yet; the checks of phases 9 and 12 are a later method change.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from de4sdv.semantic.kernel_contract import KernelFileMapping, declaration_identity
from de4sdv.semantic.validation import validate_ontology_bindings
from model_contract_fixtures import model_contract
from sysml_shapes import braced_body, strip_comments

ROOT = Path(__file__).resolve().parents[1]
KERNEL = "textual-notation-of-model/packages/methods/de4sdv/"
PRODUCT_LINE = KERNEL + "de4sdv_product_line.sysml"
METHOD_CONTEXT = KERNEL + "de4sdv_method_context.sysml"
WORKFLOW = KERNEL + "de4sdv_increment_workflow.sysml"
PROJECTION = "de4sdv/semantic/contract-data/kernel-vocabulary-projection.json"
ADMISSION = "de4sdv/semantic/contract-data/kernel-vocabulary-admission.yaml"
#: Ontology class -> (kernel file, kernel declaration, boundary): the three
#: classes of the owner decisions, each a method-admitted class bound like the kernel.
CLASSES = {
    "ConfiguredProduct": (PRODUCT_LINE, "part def ProductLineConfiguredProduct", "ple-no-configurator-authority"),
    "IncrementBaselineDecision": (METHOD_CONTEXT, "part def IncrementBaselineDecision", "none"),
    "LifecycleDisposition": (METHOD_CONTEXT, "enum def LifecycleDisposition", "none"),
}
DISPOSITIONS = ["accepted", "deferred", "invalidated"]


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _first_doc(relative: str, declaration: str) -> str:
    body = braced_body(_text(relative), declaration)
    match = re.search(r"\bdoc\s*/\*(.*?)\*/", body, re.S)
    assert match, declaration
    return " ".join(match.group(1).replace("*", " ").split())


def _members(relative: str, declaration: str) -> list[str]:
    """The statements of a definition body, without documentation, comments and nested bodies."""
    body = re.sub(r"\bdoc\b(?:\s+\w+)?\s*/\*.*?\*/", " ", braced_body(_text(relative), declaration), flags=re.S)
    flat = re.sub(r"\{[^{}]*\}", ";", strip_comments(body))
    return [" ".join(statement.split()) for statement in flat.split(";") if statement.strip()]


def _rows() -> dict[str, dict]:
    return {row["identity"]: row for row in json.loads(_text(PROJECTION))["rows"]}


def _admission_rows() -> dict[str, dict]:
    import yaml

    return {row["identity"]: row for row in yaml.safe_load(_text(ADMISSION))["admitted"]}


# ---------------------------------------------------------------------------
# Q1: the configured product
# ---------------------------------------------------------------------------


def test_the_configured_product_is_a_kernel_class_that_records_no_selection():
    """No specialization, no feature: the selections stay in the feature
    configuration and the generated projection (ADR 0006, ADR 0022)."""
    code = strip_comments(_text(PRODUCT_LINE))
    assert re.search(r"\bpart\s+def\s+ProductLineConfiguredProduct\s*\{", code)
    assert _members(PRODUCT_LINE, "part def ProductLineConfiguredProduct") == []
    doc = _first_doc(PRODUCT_LINE, "part def ProductLineConfiguredProduct")
    for clause in ("A product that a feature configuration configures, the main output of phase 9",
                   "the product-model projection that the configurator generates from the evaluation receipt "
                   "of the configuration",
                   "the configured product records none",
                   "A configured product whose configuration is admitted also specializes the definition of its "
                   "member in the governed scope",
                   "A configured product that is not admitted specializes no member definition",
                   "it proves no runtime behavior and satisfies no requirement"):
        assert clause in doc, clause


def test_the_ontology_maps_the_configured_product_onto_the_pleml_feature_configuration():
    """configuredBy is a vocabulary-only DE4SDV derived fact whose range is the
    FeatureConfiguration class, grounded on the pinned PLEML declaration; no
    kernel file imports PLEML (ADR 0022 decision 1)."""
    contract = model_contract()
    spec = contract.relationships["configuredBy"]
    assert (spec["domain"], spec["range"]) == ("ConfiguredProduct", "FeatureConfiguration")
    assert "sysml_mapping" not in spec
    assert contract.mapping("FeatureConfiguration") == KernelFileMapping(
        ".sysand/lib/mbse4u-pleml_1.1.1/PLEML.sysml", "occurrence def FeatureConfiguration")
    row = _rows()["configuredBy"]
    assert (row["accounting"], row["admission_class"], row["boundary"]) == (
        "method-admitted", "relationship-vocabulary", "ple-no-configurator-authority")
    assert (row["support"], row["traversal"], row["api_identity"]) == ("vocabulary-only", False, "unclaimed")
    assert row["definition"]["documentation_witness"]["about"] == ["ProductLineConfiguredProduct"]
    assert "no authored-ontology comparison exists" in row["relation"]["contract_source"]
    role = row["definition"]["documentation"]
    for clause in ("domain ConfiguredProduct (kernel ProductLineConfiguredProduct), range FeatureConfiguration",
                   "so the kernel imports no PLEML package",
                   "Vocabulary only, with no sysml_mapping and no runtime traversal",
                   "The relationship is a DE4SDV derived fact",
                   # The precisions of the assurance review (R1), pending the owner's confirmation (Q1).
                   "The derivation reads the effective part usages of the configured product: its own usages and "
                   "the inherited usages that it does not redefine",
                   "when one of these usages is typed by the part definition of that configuration's product-model "
                   "projection",
                   "The configuration's owned ProductModelProjectionName annotation names that part definition",
                   "binds the generated part definition by validated identity, never by partDefinitionName alone",
                   "Exactly one feature configuration configures a configured product",
                   "A specialization of a configured product that adds System 2 instrumentation, such as a test "
                   "article, is configured by the same configuration and counts for the phase 9 of its increment",
                   "It never becomes a product-line member, because membership is never inferred from specializing "
                   "a member definition"):
        assert clause in role, clause
    obligations = " ".join(_admission_rows()["configuredBy"]["forward_obligations"])
    for clause in ("the effective part usages of the configured product (its own usages and the inherited usages "
                   "that it does not redefine)",
                   "exactly one feature configuration configures a configured product",
                   "never infers membership from specializing a member definition",
                   "never by the partDefinitionName string alone",
                   "exact-revision traversal evidence"):
        assert clause in obligations, clause
    for path in sorted((ROOT / KERNEL).glob("*.sysml")):
        assert not re.search(r"\bimport\s+PLEML\b", strip_comments(path.read_text(encoding="utf-8"))), path.name


def test_the_member_product_is_a_product_variant_not_a_configured_product():
    """Review R4: only one kernel definition calls itself a configured product."""
    assert _first_doc(PRODUCT_LINE, "part def ProductLineMemberProduct") == (
        "A product variant that belongs to a product line; the configured product of an admitted configuration "
        "specializes its definition.")
    assert "configured product or product variant" not in _text(PRODUCT_LINE)


# ---------------------------------------------------------------------------
# Q2: the baseline decision, its disposition and the gap's disposition
# ---------------------------------------------------------------------------


def test_the_baseline_decision_specializes_the_lifecycle_decision_with_one_disposition():
    code = strip_comments(_text(METHOD_CONTEXT))
    assert re.search(r"\bpart\s+def\s+IncrementBaselineDecision\s*:>\s*IncrementLifecycleDecision\s*\{", code)
    assert _members(METHOD_CONTEXT, "part def IncrementBaselineDecision") == [
        "attribute disposition : LifecycleDisposition"]
    # The framing decision stays doc-only: phase 0 keeps its type.
    assert _members(METHOD_CONTEXT, "part def IncrementLifecycleDecision") == []
    doc = _first_doc(METHOD_CONTEXT, "part def IncrementBaselineDecision")
    for clause in ("The lifecycle decision of phase 12",
                   "It is not the framing decision of phase 0",
                   "Its disposition states the decision",
                   "Its typing identifies it, never a name",
                   "No check reads the baseline register, and the model does not mirror it",
                   "No acceptance under de4sdv.acceptance.maintainer-decision.v1"):
        assert clause in doc, clause


def test_the_disposition_enumeration_has_the_three_literals_of_the_owner_decision():
    body = strip_comments(braced_body(_text(METHOD_CONTEXT), "enum def LifecycleDisposition"))
    assert re.findall(r"^\s{4}(\w+)\s*\{", body, re.M) == DISPOSITIONS
    doc = _first_doc(METHOD_CONTEXT, "enum def LifecycleDisposition")
    assert "(accepted, deferred, or invalidated)" in doc
    assert "It is no evidence status, no verdict and no acceptance record" in doc


def test_the_gap_carries_an_optional_disposition_of_the_same_enumeration():
    """A gap is recorded in any phase; the baseline decision of phase 12 gives it its disposition."""
    assert _members(METHOD_CONTEXT, "part def IncrementGap") == [
        "attribute disposition : LifecycleDisposition[0..1]"]


# ---------------------------------------------------------------------------
# Admission and bindings
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(CLASSES))
def test_every_new_class_is_an_ontology_class_bound_like_the_kernel(name):
    file, declaration, boundary = CLASSES[name]
    contract = model_contract()
    assert contract.classes[name]["kernel"] == {"file": file, "declaration": declaration}
    row = _rows()[name]
    assert (row["accounting"], row["admission_class"], row["boundary"]) == ("method-admitted", "definition", boundary)
    assert (row["support"], row["traversal"], row["api_identity"]) == ("vocabulary-only", False, "unclaimed")
    assert row["definition"]["documentation"] == _first_doc(file, declaration)
    expected_parent = "IncrementLifecycleDecision" if name == "IncrementBaselineDecision" else None
    assert row["grounding"]["ontology_relations"] == {"sub_class_of": expected_parent, "disjoint_with": []}


def test_ingestion_binds_each_new_class_by_file_and_declaration_never_by_name():
    """ADR 0011: the governed declaration binds; a homonym in another document
    never does, and without the governed declaration the class stays unresolved."""
    contract = model_contract()
    governed, homonyms, sources = [], [], {}
    for name, (file, declaration, _boundary) in CLASSES.items():
        declared, metaclass = declaration_identity(declaration)
        element = {"@id": f"governed-{name}", "@type": metaclass, "declaredName": declared}
        homonym = {"@id": f"homonym-{name}", "@type": metaclass, "declaredName": declared}
        governed.append(element)
        homonyms.append(homonym)
        sources[element["@id"]] = file
        sources[homonym["@id"]] = "textual-notation-of-model/packages/features/probe/probe.sysml"
    report = validate_ontology_bindings(contract, governed + homonyms, sources)
    entries = {entry.ontology_class: entry for entry in report.entries}
    for name in CLASSES:
        assert (entries[name].status, entries[name].element_ids) == ("mapped", (f"governed-{name}",)), name
    report = validate_ontology_bindings(contract, homonyms, sources)
    entries = {entry.ontology_class: entry for entry in report.entries}
    for name in CLASSES:
        assert entries[name].status == "unresolved", name
        assert "had different provenance" in entries[name].detail, name


# ---------------------------------------------------------------------------
# The workflow parameters of phases 9 and 12
# ---------------------------------------------------------------------------

#: Step -> its parameters (direction, keyword, name, multiplicity, type).
PARAMETERS = {
    "DefineVariabilityAndConfiguration": [
        ("in", "part", "physicalElements", "[0..*]", ""),
        ("out", "part", "variationPoints", "[0..*]", ""),
        ("out", "part", "configuredProducts", "[1..*]", "ProductLineConfiguredProduct")],
    "DecideBaselineAndNextSlice": [
        ("in", "part", "charter", "", "IncrementCharter"),
        ("out", "part", "baselineDecision", "", "IncrementBaselineDecision"),
        ("out", "part", "openGaps", "[0..*]", "IncrementGap")],
}


@pytest.mark.parametrize("step", sorted(PARAMETERS))
def test_the_steps_of_phases_9_and_12_type_their_outputs_by_the_new_classes(step):
    """The types of the step parameters. The checks of phases 9 and 12 are about the
    typed outputs only (``tests/test_increment_workflow.py`` locks them): never about
    ``variationPoints`` or ``physicalElements``, which stay untyped."""
    body = strip_comments(braced_body(_text(WORKFLOW), f"action def {step}"))
    found = re.findall(r"\b(in|out)\s+(\w+)\s+(\w+)(\[[^\]]*\])?\s*(?::\s*(\w+))?\s*;", body)
    assert found == PARAMETERS[step]
    about = set(re.findall(r"\bMethodCheck\s+about\s+(\w+)", body))
    assert about == {name for _direction, _kind, name, _bounds, typed in found if typed and name != "charter"}
    code = strip_comments(_text(WORKFLOW))
    assert code.count("private import DE4SDV_ProductLine::ProductLineConfiguredProduct;") == 1


def test_no_method_module_reads_the_baseline_register():
    """Q2: the method never reads the baseline register (repository text); the
    baseline decision's typing and disposition are the model's record."""
    for path in sorted((ROOT / "de4sdv").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"baseline[-_]register", text, re.IGNORECASE), path.relative_to(ROOT)


#: The modules that decide a verdict, readiness or an acceptance: the result algebra,
#: the increment evaluation with its phase exits, the delivery gate, the operational
#: exit, the acceptance-policy readers and the Method Check scripts.
VERDICT_AND_ACCEPTANCE_MODULES = (
    "de4sdv/semantic/method_evaluator.py", "de4sdv/semantic/increment_evaluation.py",
    "de4sdv/semantic/delivery_gate.py", "de4sdv/semantic/operational_exit.py",
    "de4sdv/semantic/method_pilot.py", "de4sdv/semantic/method_contract.py",
    "scripts/method_check.py", "scripts/run_delivery_gate.py", "scripts/run_core_operational_exit.py",
)
_DISPOSITION_LITERAL = re.compile(r"""(['"])(?:LifecycleDisposition::)?(?:accepted|deferred|invalidated)\1""")


def _maps_a_disposition_literal(text: str) -> bool:
    """Lexical proxy, not a parser: a module that names the LifecycleDisposition
    enumeration in code and also holds one of its literal names as a string
    constant. A mapping from a disposition value to an acceptance, a verdict or a
    readiness takes this form. A check that a disposition is stated needs neither."""
    code = re.sub(r"#[^\n]*", " ", text)
    return "LifecycleDisposition" in code and _DISPOSITION_LITERAL.search(code) is not None


def test_no_evaluator_or_acceptance_module_maps_a_disposition_literal():
    """Review R5: LifecycleDisposition::accepted is a phase-12 decision, never an
    acceptance under de4sdv.acceptance.maintainer-decision.v1, a verdict or
    readiness. The modules that decide those do not name the enumeration, and no
    other module maps its literals."""
    for relative in VERDICT_AND_ACCEPTANCE_MODULES:
        assert (ROOT / relative).is_file(), relative
        assert "LifecycleDisposition" not in _text(relative), relative
    modules = sorted((ROOT / "de4sdv").rglob("*.py")) + sorted((ROOT / "scripts").glob("*.py"))
    assert len(modules) > 50, "the scan must see the code"
    for path in modules:
        assert not _maps_a_disposition_literal(path.read_text(encoding="utf-8")), path.relative_to(ROOT)


@pytest.mark.parametrize("text, maps", [
    ('DISPOSITION = "LifecycleDisposition"\nOUTCOME = {"accepted": "PASS", "deferred": "BLOCKED"}\n', True),
    ("if value == 'LifecycleDisposition::accepted':\n    readiness = 'READY'\n", True),
    ('DISPOSITION = "LifecycleDisposition"\nstated = value is not None\n', False),
    ('if record["outcome"] == "accepted":\n    accepted.append(record)\n', False),
    ('# LifecycleDisposition is named in a comment only\nOUTCOME = {"accepted": "PASS"}\n', False),
])
def test_the_disposition_guard_sees_a_mapping_and_only_a_mapping(text, maps):
    """Positive and negative controls of the lexical guard above: an acceptance
    policy's own "accepted" outcome and a presence check are no mapping."""
    assert _maps_a_disposition_literal(text) is maps
