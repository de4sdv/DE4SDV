"""The API describes definitions: qualified names resolve, and inspect_element says
what a definition declares, over the frozen genuine-export cut.

The service is the production assembly (model facade plus service assembly) over
the cut, with kernel identity validated from the export as the export evaluation
validates it. Answers are checked against oracles that are not the code under
test:

- the method layer: each ``phase_contract`` gate names its subject type and the
  element it selects (``subject_selector``) from validated kernel lineage;
- the ingestion-validated kernel bindings (file and declaration to element);
- the cut's own source files, read at the cut's source revision: the expected
  values below were read from those files, whose sha256 the cut records in its
  source manifest (asserted here). They are never compared with the model at
  HEAD; a re-cut must re-read them.
"""

from __future__ import annotations

import asyncio
import copy
import gzip
import json
from typing import Any

import pytest

from de4sdv.semantic.export_evaluation import load_export_snapshot
from de4sdv.semantic.mcp_server import create_mcp_server
from de4sdv.semantic.revision_index import RevisionIndex
from de4sdv.sysml_api.errors import IdentityNotFoundError
from de4sdv.sysml_api.repository import SysMLRepository, reference_ids
from increment_model_fixtures import GENUINE_EXPORT
from model_contract_fixtures import binding, model_service

METHODS = "textual-notation-of-model/packages/methods/de4sdv/"
#: The cut's source files the expected values were read from, with the sha256
#: the cut records for them.
SOURCES = {
    METHODS + "de4sdv_increment_workflow.sysml":
        "6098659cad8f9fe63238a74f197df94f9d1a3924871b202e256d96a7fcabe3d9",
    METHODS + "de4sdv_method_traces.sysml":
        "a4b2cba28cc6f29534db455ef47f1e0aed3ded7ccdc690bebf475cf3e732efd7",
    METHODS + "de4sdv_method_process.sysml":
        "0db2f91dcda080d6bfedf0a5795b84261388326ff73faa411b49fdd91cec2108",
    METHODS + "de4sdv_method_context.sysml":
        "63c1a3efc36f77027fff2e22aa071ebc3ecdaddf4d23976e8662bcb45fc02654",
    "textual-notation-of-model/packages/features/aebs/aebs_visualization_needs_requirements.sysml":
        "765324cbefbbd5ccee25b621cda1e6a7a42344aec69a2dce48cf697dd7e72f91",
}
OUTSIDE = "typed by an element outside this export"


class _Repository(SysMLRepository):
    def __init__(self, elements: list[dict[str, Any]]) -> None:
        super().__init__(client=None)  # type: ignore[arg-type]
        self.elements = elements

    def list_elements(self, project_id: str, commit_id: str) -> list[dict[str, Any]]:
        return self.elements


@pytest.fixture(scope="module")
def cut(tmp_path_factory: pytest.TempPathFactory):
    path = tmp_path_factory.mktemp("genuine-export") / "export.json"
    raw = gzip.decompress(GENUINE_EXPORT.read_bytes())
    path.write_bytes(raw)
    return load_export_snapshot(path), json.loads(raw)


def _service(snapshot, elements: list[dict[str, Any]] | None = None):
    kernel = [{"ontology_class": b.ontology_class, "element_id": b.element_id,
               "source_file": b.source_file, "declaration": b.declaration}
              for b in snapshot.kernel_bindings]
    return model_service(binding(git_commit=snapshot.revision.git_commit, kernel_bindings=kernel),
                         _Repository(snapshot.elements if elements is None else elements))


@pytest.fixture(scope="module")
def service(cut):
    return _service(cut[0])


def _api_form(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The listing the pinned API serves: every exported field unchanged, padded with
    valueless schema fields (the keys below occur padded in the production listing)."""
    empty = ("documentation", "ownedFeature", "feature", "inheritedFeature", "ownedMember", "member",
             "membership", "ownedElement", "ownedSpecialization", "ownedSubclassification", "aliasIds",
             "textualRepresentation", "ownedAnnotation", "relatedElement", "source", "target")
    null = ("qualifiedName", "name", "declaredName", "shortName", "declaredShortName", "owner",
            "owningNamespace", "owningMembership", "owningType", "owningFeature", "multiplicity", "type",
            "general", "superclassifier", "direction", "isEnd", "memberName", "owningRelationship")
    padded = []
    for element in elements:
        item = copy.deepcopy(element)
        for key in empty:
            item.setdefault(key, [])
        for key in null:
            item.setdefault(key, None)
        item.setdefault("ownedRelationship", [])
        padded.append(item)
    return padded


def _definition(service, identifier: str) -> tuple[dict[str, Any], dict[str, Any]]:
    answer = service.inspect_element(identifier)
    return answer, answer["element"]["definition"]


def _features(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {entry["name"]: entry for entry in entries}


def test_the_expected_values_come_from_the_cut_s_own_source_files(cut) -> None:
    manifest = {entry["path"]: entry["sha256"] for entry in cut[1]["source_manifest"]}
    assert {path: manifest.get(path) for path in SOURCES} == SOURCES


def test_every_subject_type_phase_contract_names_resolves_to_the_element_it_selects(service) -> None:
    gates = service.phase_contract()["gates"]
    qualified = [gate for gate in gates if "::" in gate["subject_type"]]
    assert len(qualified) >= 10
    for gate in qualified:
        answer = service.inspect_element(gate["subject_type"])
        assert answer["resolution_level"] == "qualified-name-match", gate["subject_type"]
        assert answer["element"]["element_id"] == gate["subject_selector"], gate["subject_type"]
        assert answer["element"]["qualified_name"] == gate["subject_type"]
    # An untyped parameter's subject type is a SysML metaclass, not a model element.
    for gate in gates:
        if "::" not in gate["subject_type"]:
            assert gate["subject_type"].endswith("Usage")
            with pytest.raises(IdentityNotFoundError):
                service.inspect_element(gate["subject_type"])


def test_every_qualified_name_in_phase_contract_resolves_to_the_element_the_method_names(cut, service) -> None:
    contract = service.phase_contract()
    names = {gate["check_definition"] for gate in contract["gates"]}
    names |= {step["definition"] for step in contract["steps"]}
    names |= {name.strip() for step in contract["steps"] for parameter in step["inputs"] + step["outputs"]
              for name in (parameter["type"] or "").split(",") if "::" in name}
    assert len(names) >= 20
    index = RevisionIndex(cut[0].elements)
    for name in sorted(names):
        resolved = service.resolve_element(name)
        assert resolved["resolution_level"] == "qualified-name-match", name
        assert resolved["element"]["qualified_name"] == name
        assert index.qualified_name(resolved["element"]["element_id"]) == name


def test_every_kernel_declaration_resolves_by_its_qualified_name(cut, service) -> None:
    snapshot, export = cut
    sources = export["element_sources"]
    assert len(snapshot.kernel_bindings) >= 40
    for kernel in snapshot.kernel_bindings:
        named = service.resolve_element(kernel.element_id)["element"]["qualified_name"]
        assert named and named.split("::")[-1] == kernel.declaration.split()[-1], kernel
        resolved = service.resolve_element(named)
        assert (resolved["resolution_level"], resolved["element"]["element_id"]) == (
            "qualified-name-match", kernel.element_id)
        assert sources[kernel.element_id] == kernel.source_file


def test_a_charter_definition_is_described_as_its_source_declares(service) -> None:
    answer, definition = _definition(service, "DE4SDV_IncrementWorkflow::IncrementCharter")
    element = answer["element"]
    assert (element["keyword"], element["qualified_name"]) == (
        "part def", "DE4SDV_IncrementWorkflow::IncrementCharter")
    assert element["owning_package"]["qualified_name"] == "DE4SDV_IncrementWorkflow"
    assert element["documentation"][0].startswith("Charter declaration of one increment")
    assert [s["qualified_name"] for s in definition["supertypes"] if s["direct"]] == [
        "DE4SDV_MethodTraces::IncrementTraceObligations"]
    owned = _features(definition["owned_features"])
    assert list(owned) == ["owner", "expectedArtifacts", "expectedReviewEvidence", "workflow"]
    # attribute owner : String; (ScalarValues is not part of the export)
    assert (owned["owner"]["keyword"], owned["owner"]["type"], owned["owner"]["multiplicity"]) == (
        "attribute", None, None)
    assert owned["owner"]["type_outside_export"].startswith(OUTSIDE)
    # attribute expectedArtifacts : String[1..*];
    assert owned["expectedArtifacts"]["multiplicity"] == [1, "*"]
    assert owned["expectedArtifacts"]["type_outside_export"].startswith(OUTSIDE)
    # action workflow : IncrementWorkflow;
    assert (owned["workflow"]["keyword"], owned["workflow"]["type"]) == (
        "action", "DE4SDV_IncrementWorkflow::IncrementWorkflow")
    assert "type_outside_export" not in owned["workflow"]
    inherited = _features(definition["inherited_features"])
    # ref part increment : EngineeringIncrement; attribute applicablePhases[*] : MethodPhase;
    assert (inherited["increment"]["keyword"], inherited["increment"]["type"]) == (
        "part", "DE4SDV_MethodContext::EngineeringIncrement")
    assert inherited["applicablePhases"]["type"] == "DE4SDV_MethodProcess::MethodPhase"
    # The cut keeps this inherited feature but not its multiplicity range (it keeps
    # no owned member of a referenced element): the answer says so, never "none declared".
    incomplete = [gap["reason"] for gap in answer["gaps"] if gap["category"] == "definition-incomplete"]
    assert inherited["applicablePhases"]["multiplicity"] == [0, "*"] or any(
        "IncrementTraceObligations::applicablePhases (" in reason for reason in incomplete)
    for entry in (inherited["increment"], inherited["applicablePhases"]):
        assert entry["inherited_from"] == "DE4SDV_MethodTraces::IncrementTraceObligations"
    assert not set(owned) & set(inherited)


def test_an_enumeration_definition_lists_its_enumerated_values_in_order(service) -> None:
    answer, definition = _definition(service, "DE4SDV_MethodProcess::MethodPhase")
    assert answer["element"]["keyword"] == "enum def"
    assert answer["element"]["owning_package"]["qualified_name"] == "DE4SDV_MethodProcess"
    values = definition["enumerated_values"]
    assert [value["name"] for value in values] == [
        "phase0_incrementFraming", "phase1_concernFraming", "phase2_operationalContext",
        "phase3_capabilityClassification", "phase4_needs", "phase5_requirements",
        "phase6_functionalArchitecture", "phase7_logicalArchitecture", "phase8_physicalRealization",
        "phase9_variabilityConfiguration", "phase10_vvEvidence", "phase11_publication",
        "phase12_baselineNextSlice"]
    assert values[4]["qualified_name"] == "DE4SDV_MethodProcess::MethodPhase::phase4_needs"
    assert definition["owned_features"] == []


def test_a_connection_definition_lists_its_ends(service) -> None:
    answer, definition = _definition(service, "DE4SDV_MethodContext::DerivesFromNeed")
    assert answer["element"]["keyword"] == "connection def"
    # end need : StakeholderNeedCandidate; end derivedRequirement : RequirementCandidate;
    declared = {"need": "DE4SDV_MethodContext::StakeholderNeedCandidate",
                "derivedRequirement": "DE4SDV_MethodContext::RequirementCandidate"}
    ends = _features(definition["owned_features"])
    assert "derivedRequirement" in ends and set(ends) <= set(declared)
    for name, entry in ends.items():
        assert (entry["end"], entry["keyword"], entry["type"]) == (True, "ref", declared[name])


def test_a_redefinition_hides_what_it_redefines_and_values_are_described(service) -> None:
    _answer, definition = _definition(service, "DE4SDV_IncrementWorkflow::FrameIncrement")
    assert [s["qualified_name"] for s in definition["supertypes"]] == ["DE4SDV_IncrementWorkflow::IncrementStep"]
    owned = _features(definition["owned_features"])
    # attribute :>> phase = MethodPhase::phase0_incrementFraming;
    assert owned["phase"]["redefines"] == ["DE4SDV_IncrementWorkflow::IncrementStep::phase"]
    assert owned["phase"]["value"] == {"default": False, "values": [{
        "reference": "DE4SDV_MethodProcess::MethodPhase::phase0_incrementFraming",
        "element_id": owned["phase"]["value"]["values"][0]["element_id"]}]}
    # out part increment : EngineeringIncrement; out part assumptions[1..*] : IncrementAssumption;
    assert (owned["increment"]["direction"], owned["increment"]["keyword"]) == ("out", "part")
    assert owned["assumptions"]["multiplicity"] == [1, "*"]
    # out requirement problemStatement : ProblemStatement; out concern framedConcerns[1..*];
    assert owned["problemStatement"]["keyword"] == "requirement"
    assert (owned["framedConcerns"]["keyword"], owned["framedConcerns"]["type"]) == ("concern", None)
    assert "type_outside_export" not in owned["framedConcerns"]
    # IncrementStep declares only phase, which FrameIncrement redefines.
    assert definition["inherited_features"] == []
    _answer, check = _definition(service, "DE4SDV_IncrementWorkflow::MethodCheck")
    checks = _features(check["owned_features"])
    # attribute minimum : Natural default 1; attribute advisory : Boolean default false;
    assert checks["minimum"]["value"] == {"default": True, "values": [{"literal": 1}]}
    assert checks["advisory"]["value"] == {"default": True, "values": [{"literal": False}]}


def test_a_usage_gets_the_keyword_that_declares_it_and_its_nearest_package(service) -> None:
    # package VisualizationNeeds { requirement needNonInterference : VisualizationEngineeringNeed {
    #   subject increment : ...; stakeholder verificationEngineer : ...; require constraint statement {...}
    need = "DE4SDV_AEBSVisualizationNeedsRequirements::VisualizationNeeds::needNonInterference"
    for name, keyword in (("", "requirement"), ("::increment", "subject"),
                          ("::verificationEngineer", "stakeholder"), ("::statement", "require")):
        element = service.inspect_element(need + name)["element"]
        assert (element["qualified_name"], element["keyword"]) == (need + name, keyword)
        assert element["owning_package"]["qualified_name"] == (
            "DE4SDV_AEBSVisualizationNeedsRequirements::VisualizationNeeds")
        assert "definition" not in element


def test_the_api_listing_gives_the_answers_the_export_gives(cut, service) -> None:
    padded = _service(cut[0], _api_form(cut[0].elements))
    for identifier in ("DE4SDV_IncrementWorkflow::IncrementCharter", "DE4SDV_MethodProcess::MethodPhase",
                       "DE4SDV_MethodContext::DerivesFromNeed", "DE4SDV_IncrementWorkflow::FrameIncrement",
                       "IncrementCharter"):
        assert padded.inspect_element(identifier) == service.inspect_element(identifier), identifier


def test_owned_relationships_missing_from_the_corpus_are_a_gap(cut, service) -> None:
    resolved = service.resolve_element("DE4SDV_IncrementWorkflow::IncrementCharter")["element"]
    by_id = {element["@id"]: element for element in cut[0].elements}
    owner = by_id[resolved["element_id"]]
    membership = next(by_id[r] for r in reference_ids(owner["ownedRelationship"])
                      if by_id[r].get("memberName") == "owner")
    partial = _service(cut[0], [element for element in cut[0].elements if element["@id"] != membership["@id"]])
    answer, definition = _definition(partial, "DE4SDV_IncrementWorkflow::IncrementCharter")
    assert "owner" not in _features(definition["owned_features"])

    def incomplete(gaps: list[dict[str, str]]) -> str:
        return " ".join(gap["reason"] for gap in gaps if gap["category"] == "definition-incomplete")

    assert f"DE4SDV_IncrementWorkflow::IncrementCharter ({membership['@id']})" in incomplete(answer["gaps"])
    assert membership["@id"] not in incomplete(service.inspect_element(resolved["element_id"])["gaps"])


def test_bare_names_keep_their_resolution_and_every_answer_names_its_elements(service) -> None:
    bare = service.inspect_element("IncrementCharter")
    assert bare["resolution_level"] == "structural-match"
    assert bare["element"] == service.inspect_element("DE4SDV_IncrementWorkflow::IncrementCharter")["element"]
    neighbors = service.semantic_neighbors("DE4SDV_MethodContext::DerivesFromNeed")
    assert neighbors["root"]["qualified_name"] == "DE4SDV_MethodContext::DerivesFromNeed"
    usage = service.resolve_element("INC-AEBS-010")["element"]
    assert usage["qualified_name"] == "DE4SDV_AEBSVisualizationFraming::incAEBS010"


def test_a_name_that_resolves_nowhere_says_which_revision_was_searched(cut, service) -> None:
    with pytest.raises(IdentityNotFoundError) as raised:
        service.inspect_element("DE4SDV_MethodContext::EngineeringIncrementt")
    message = str(raised.value)
    assert "no owned member named 'EngineeringIncrementt'" in message
    assert cut[0].revision.git_commit in message


def test_the_mcp_tools_take_qualified_names_and_say_so(service) -> None:
    server = create_mcp_server(service)
    tools = {tool.name: tool for tool in server._tool_manager.list_tools()}
    for name in ("resolve_element", "inspect_element"):
        assert "qualified name" in tools[name].description, name
    result = asyncio.run(server._tool_manager.call_tool(
        "inspect_element", {"identifier": "DE4SDV_MethodProcess::MethodPhase"}))
    assert result["element"]["definition"]["enumerated_values"][0]["name"] == "phase0_incrementFraming"
    assert result["revision"]["git_commit"] == service.binding.git_commit
