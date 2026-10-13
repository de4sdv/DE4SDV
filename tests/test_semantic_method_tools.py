"""Method tools of the semantic service and MCP surface, per increment.

Method evaluation is part of every revision-bound semantic service: the
method is the workflow the increment's charter declares in the bound model, so
the runtime needs no separate method wiring ("not configured" no longer
applies). The four tools take the increment identifier; phase is an optional
filter. A model without a workflow answers with an explicit
CONTRACT_UNAVAILABLE result.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from de4sdv.semantic import method_evaluator as me
from de4sdv.semantic.mcp_server import create_mcp_server
from de4sdv.sysml_api.errors import RevisionMismatchError
from de4sdv.sysml_api.repository import SysMLRepository
from increment_model_fixtures import increment_scenario, cut_method_builder, cut_workflow
from model_contract_fixtures import binding, model_service

P4 = "phase4_needs"

INCREMENT = "INC-FIXTURE-001"


class _Repository(SysMLRepository):
    def __init__(self, elements):
        super().__init__(client=None)  # type: ignore[arg-type]
        self.elements = elements
        self.listings = 0

    def list_elements(self, project_id, commit_id):
        self.listings += 1
        return self.elements


def _service(with_workflow: bool = True, git_commit: str = "a" * 40):
    scenario = increment_scenario(cut_method_builder())
    if with_workflow:
        cut_workflow(scenario)
    revision_binding = binding(git_commit=git_commit, kernel_bindings=scenario.builder.bindings)
    repository = _Repository(scenario.builder.elements)
    return model_service(revision_binding, repository), scenario, repository


def _call(server, tool, arguments):
    result = asyncio.run(server._tool_manager.call_tool(tool, arguments))
    return json.loads(json.dumps(result))


def test_method_tools_need_no_separate_wiring() -> None:
    service, _scenario, _repository = _service()
    status = service.increment_status(increment=INCREMENT)
    assert status["query"] == "increment_status"
    assert status["executable_contract_available"] is True
    assert status["increment"]["resolved"] is True


def test_projections_reuse_one_evaluation_per_increment() -> None:
    service, _scenario, _repository = _service()
    keys = {
        service.increment_status(increment=INCREMENT)["evaluation_key"],
        service.method_gaps(increment=INCREMENT)["evaluation_key"],
        service.next_obligation(increment=INCREMENT)["evaluation_key"],
        service.increment_status(P4, increment=INCREMENT)["evaluation_key"],
    }
    assert len(keys) == 1
    assert service.method_evaluation_count == 1


def test_mcp_tools_take_the_increment_and_an_optional_phase() -> None:
    service, _scenario, _repository = _service()
    server = create_mcp_server(service)
    tools = {tool.name: tool for tool in server._tool_manager.list_tools()}
    for name in ("increment_status", "method_gaps", "next_obligation"):
        schema = tools[name].parameters
        assert schema["required"] == ["increment"], name
        assert set(schema["properties"]) == {"increment", "phase"}, name
    assert "required" not in tools["phase_contract"].parameters or not tools["phase_contract"].parameters["required"]
    status = _call(server, "increment_status", {"increment": INCREMENT, "phase": P4})
    assert [block["phase"] for block in status["phases"]] == [P4]
    nxt = _call(server, "next_obligation", {"increment": INCREMENT})
    assert nxt["next"] is None
    contract = _call(server, "phase_contract", {"phase": P4, "increment": INCREMENT})
    assert {gate["obligation_id"] for gate in contract["gates"]} >= {"needHasStakeholder", "needHasValidationScenario"}
    gaps = _call(server, "method_gaps", {"increment": INCREMENT})
    assert gaps["blocking"] == []


def test_a_model_without_a_workflow_answers_contract_unavailable() -> None:
    service, _scenario, _repository = _service(with_workflow=False)
    server = create_mcp_server(service)
    status = _call(server, "increment_status", {"increment": INCREMENT})
    assert status["executable_contract_available"] is False
    assert status["reason_codes"] == [me.CONTRACT_UNAVAILABLE]
    contract = _call(server, "phase_contract", {})
    assert contract["executable_contract_available"] is False


def test_an_increment_the_bound_revision_does_not_declare_is_answered_as_such() -> None:
    """The served answers evaluate the bound revision only: work on a branch answers
    `increment.resolution` not-declared, naming that revision, never an empty reason."""
    service, _scenario, _repository = _service()
    server = create_mcp_server(service)
    answer = _call(server, "next_obligation", {"increment": "INC-EXAMPLE-001"})
    assert answer["increment"]["resolution"] == "not-declared"
    assert answer["reason"].startswith(f"INC-EXAMPLE-001 isn't declared at revision {'a' * 40} (full-model)")
    status = _call(server, "increment_status", {"increment": "INC-EXAMPLE-001"})
    assert status["increment"]["resolution"] == "not-declared"
    assert status["increment"]["message"] == answer["reason"]


def test_the_served_contract_lists_every_step_and_the_phases_no_check_judges() -> None:
    service, _scenario, _repository = _service()
    contract = _call(create_mcp_server(service), "phase_contract", {})
    assert len(contract["steps"]) == 13
    assert [step["phase"] for step in contract["steps"] if step["executable_checks"]] == contract["phases"]
    assert contract["phases_without_executable_checks"] == [
        step["phase"] for step in contract["steps"] if step["coverage"] == "no executable checks at this revision"]


def test_the_tool_descriptions_say_what_each_answer_covers() -> None:
    service, _scenario, _repository = _service()
    tools = {tool.name: tool.description for tool in create_mcp_server(service)._tool_manager.list_tools()}
    for name in ("phase_contract", "increment_status", "method_gaps", "next_obligation"):
        assert "bound revision" in tools[name], name
    assert "no executable checks at this revision" in tools["phase_contract"]
    assert "`population`" in tools["phase_contract"] and "`cardinality`" in tools["phase_contract"]
    for name in ("increment_status", "method_gaps"):
        assert "`coverage`" in tools[name], name
    for name in ("increment_status", "next_obligation"):
        assert "`increment.resolution` is `not-declared`" in " ".join(tools[name].split()), name


def test_the_status_description_says_an_unchecked_exit_is_never_a_gap() -> None:
    service, _scenario, _repository = _service()
    tools = {tool.name: " ".join(tool.description.split())  # docstrings wrap their lines
             for tool in create_mcp_server(service)._tool_manager.list_tools()}
    assert "BLOCKED by the method (CONTRACT_UNAVAILABLE), never by a gap" in tools["increment_status"]
    assert "declared outputs" in tools["increment_status"]


def test_malformed_increment_identifier_is_refused() -> None:
    service, _scenario, _repository = _service()
    with pytest.raises(ValueError, match="INC-<SUBJECT>-<SEQ>"):
        service.increment_status(increment="AEBS-010")


def test_method_tools_fail_closed_on_a_stale_revision() -> None:
    service, _scenario, _repository = _service()
    service.expected_git_revision = "b" * 40
    with pytest.raises(RevisionMismatchError):
        service.next_obligation(increment=INCREMENT)
