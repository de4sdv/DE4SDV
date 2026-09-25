"""W6 rename-transition scaffolding: fail-closed preparation, no activation."""
import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

COMMITTED = {
    "realizedBy": "allocatedToArchitecture",
    "specifiesFunction": "hasRelevantFunction",
    "validatedBy": "hasValidationScenario",
    "constrainedBy": "hasRegulatorySource",
    "deployedTo": "logicalAllocatedToPhysical",
    "IncrementTraceabilityShell": "RequiredTraceChain",
}


def _entry(identity, successor, authorization=None) -> dict:
    return {"identity": identity, "proposed_successor": successor,
            "authorization": authorization}


def _doc(**overrides) -> dict:
    document = {
        "schema": "de4sdv.o4-w6-transition-plan/v1",
        "status": "preparation",
        "note": "fixture",
        "entries": [_entry("realizedBy", "allocatedToArchitecture")],
    }
    document.update(overrides)
    return document


def test_committed_skeleton_loads_and_every_state_is_pending():
    from de4sdv.semantic.rename_transition import load_plan, transition_state

    plan = load_plan(REPO_ROOT)
    assert plan["status"] == "preparation"
    assert {e["identity"]: e["proposed_successor"] for e in plan["entries"]} == COMMITTED
    assert all(e["authorization"] is None for e in plan["entries"])
    for identity in COMMITTED:
        assert transition_state(identity, plan) == "pending"
        assert transition_state(identity) == "pending"  # committed plan by default


def test_committed_plan_has_no_authorized_entries():
    from de4sdv.semantic.rename_transition import authorized_entries, load_plan

    assert authorized_entries(load_plan(REPO_ROOT)) == []


def test_unknown_top_level_key_is_refused():
    from de4sdv.semantic.rename_transition import RenameTransitionError, validate_plan

    with pytest.raises(RenameTransitionError, match="unknown top-level"):
        validate_plan(_doc(activated=True))
    with pytest.raises(RenameTransitionError, match="status"):
        validate_plan(_doc(status="active"))
    with pytest.raises(RenameTransitionError, match="schema"):
        validate_plan(_doc(schema="de4sdv.o4-w6-transition-plan/v2"))


def test_unknown_entry_keys_are_refused():
    from de4sdv.semantic.rename_transition import RenameTransitionError, validate_plan

    for key in ("activation", "wire", "migrated"):
        entry = _entry("realizedBy", "allocatedToArchitecture")
        entry[key] = True
        with pytest.raises(RenameTransitionError, match="unknown entry keys"):
            validate_plan(_doc(entries=[entry]))
    with pytest.raises(RenameTransitionError, match="missing entry keys"):
        validate_plan(_doc(entries=[{"identity": "realizedBy"}]))


def test_invalid_successor_is_refused():
    from de4sdv.semantic.rename_transition import RenameTransitionError, validate_plan

    for successor in ("", "AllocatedToArchitecture", "allocated-to-architecture",
                      "hasRegulatorySource (proposed)", None):
        with pytest.raises(RenameTransitionError, match="proposed_successor"):
            validate_plan(_doc(entries=[_entry("realizedBy", successor)]))
    # decision-15 rows validate the successor as an identifier only: the
    # existing register identity RequiredTraceChain is accepted, a malformed
    # name is still refused.
    plan = validate_plan(_doc(entries=[_entry("IncrementTraceabilityShell", "RequiredTraceChain")]))
    assert plan["entries"][0]["proposed_successor"] == "RequiredTraceChain"
    with pytest.raises(RenameTransitionError, match="proposed_successor"):
        validate_plan(_doc(entries=[_entry("IncrementTraceabilityShell", "required trace chain")]))


def test_invalid_identity_is_refused():
    from de4sdv.semantic.rename_transition import RenameTransitionError, validate_plan

    for identity in ("", "realized by", "1realizedBy", None):
        with pytest.raises(RenameTransitionError, match="identity"):
            validate_plan(_doc(entries=[_entry(identity, "allocatedToArchitecture")]))


def test_duplicate_identity_is_refused():
    from de4sdv.semantic.rename_transition import RenameTransitionError, validate_plan

    entries = [_entry("realizedBy", "allocatedToArchitecture"),
               _entry("realizedBy", "hasRelevantFunction")]
    with pytest.raises(RenameTransitionError, match="duplicate identity"):
        validate_plan(_doc(entries=entries))


def test_any_non_null_authorization_is_refused_naming_the_decision():
    from de4sdv.semantic.rename_transition import RenameTransitionError, validate_plan

    record = {"decision": "decision-1", "record": "docs/method-conformance/o4/w6-transition-preparation.md#decision-1"}
    for authorization in (record, ["decision-1"], "decision-1"):
        with pytest.raises(RenameTransitionError, match="decision-1"):
            validate_plan(_doc(entries=[_entry("realizedBy", "allocatedToArchitecture",
                                               authorization)]))
    with pytest.raises(RenameTransitionError, match="decision-15"):
        validate_plan(_doc(entries=[_entry("RequiredTraceChain", "traceExpectation",
                                           record)]))


def test_synthetic_authorized_plan_yields_decided_in_memory_only():
    from de4sdv.semantic.rename_transition import (authorized_entries,
                                                   transition_state, validate_plan)

    document = _doc(entries=[_entry(
        "realizedBy", "allocatedToArchitecture",
        {"decision": "decision-1",
         "record": "docs/method-conformance/o4/o4-execution-register.json#realizedBy"})])
    plan = validate_plan(document, allow_authorized=True)
    assert transition_state("realizedBy", plan) == "decided"
    assert [e["identity"] for e in authorized_entries(plan)] == ["realizedBy"]
    with pytest.raises(ValueError, match="decision"):
        validate_plan(_doc(entries=[_entry(
            "realizedBy", "allocatedToArchitecture",
            {"decision": "decision-99", "record": "docs/note.md#x"})]),
            allow_authorized=True)


def test_module_is_absent_from_the_runtime_import_graph():
    """No other de4sdv module imports or references the scaffolding."""
    offenders = []
    for path in sorted((REPO_ROOT / "de4sdv").rglob("*.py")):
        if path.name == "rename_transition.py":
            continue
        if "rename_transition" in path.read_text(encoding="utf-8"):
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == []


def test_module_imports_are_build_time_only():
    from de4sdv.semantic import rename_transition

    tree = ast.parse(Path(rename_transition.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
    assert imported <= {"__future__", "re", "pathlib", "yaml"}