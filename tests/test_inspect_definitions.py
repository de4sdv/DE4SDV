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
import re
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
        "ab992b7f7a8200c6186845a6c402564b66533f5b0a7ad4f6625fa908738911a4",
    METHODS + "de4sdv_trace_vocabulary.sysml":
        "58ba8ea33ef950e1abcdda19efaa6757e33cad06902e70605ffdc3eaf1a6fbea",
    METHODS + "de4sdv_method_process.sysml":
        "7e94fd449a901e3e9ae6862182e34b653f72aa38457e6142c7cf9b65be9ac257",
    METHODS + "de4sdv_method_context.sysml":
        "481e9a21378f60489e65dc2f8d8274ea61a9f4d4b9f0c085947af6693012e162",
    "textual-notation-of-model/packages/features/aebs/aebs_visualization_needs_requirements.sysml":
        "edce3bf5b30a042083138712bd8084902d4488be1b308730246b26a50af576bb",
    "textual-notation-of-model/packages/features/aebs/aebs_visualization_framing.sysml":
        "04c7c778ff18023a0ea5dde3d8dd10ce9b8fecebdc76c17496535cdbd039f91d",
    ".sysand/lib/ode4hera-requirements-management_2.0.1/RequirementsManagement.sysml":
        "f7a480d6baed5b06eefb3be222608a616241eca5cf6dbde738f22ec00a9d3073",
    ".sysand/lib/mbse4u-sysmod_5.1.1/SYSMOD.sysml":
        "c3340408dc95f07bc8f4b91727b60a72f194cf1353528aae8c895ebdedd7bf9e",
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
        "DE4SDV_IncrementWorkflow::IncrementTraceObligations"]
    owned = _features(definition["owned_features"])
    assert list(owned) == ["owner", "expectedArtifacts", "expectedReviewEvidence", "systemOfInterest", "workflow"]
    # attribute owner : String; (ScalarValues is not part of the export)
    assert (owned["owner"]["keyword"], owned["owner"]["type"], owned["owner"]["multiplicity"]) == (
        "attribute", None, None)
    assert owned["owner"]["type_outside_export"].startswith(OUTSIDE)
    # The export removed the reference to String and recorded it among its external
    # references; the API revision keeps only the typing relationship.
    assert ("the export's external references record its target, and this API revision keeps only the "
            "typing relationship ") in owned["owner"]["type_outside_export"]
    # attribute expectedArtifacts : String[1..*];
    assert owned["expectedArtifacts"]["multiplicity"] == [1, "*"]
    assert owned["expectedArtifacts"]["type_outside_export"].startswith(OUTSIDE)
    # ref part systemOfInterest[0..1]; (untyped: an increment sets it by redefinition)
    assert (owned["systemOfInterest"]["keyword"], owned["systemOfInterest"]["type"],
            owned["systemOfInterest"]["multiplicity"]) == ("ref part", None, [0, 1])
    assert "type_outside_export" not in owned["systemOfInterest"]
    # action workflow : IncrementWorkflow;
    assert (owned["workflow"]["keyword"], owned["workflow"]["type"]) == (
        "action", "DE4SDV_IncrementWorkflow::IncrementWorkflow")
    assert "type_outside_export" not in owned["workflow"]
    inherited = _features(definition["inherited_features"])
    # ref part increment : EngineeringIncrement; attribute applicablePhases[*] : MethodPhase;
    assert (inherited["increment"]["keyword"], inherited["increment"]["type"]) == (
        "ref part", "DE4SDV_MethodContext::EngineeringIncrement")
    assert inherited["applicablePhases"]["type"] == "DE4SDV_MethodProcess::MethodPhase"
    # The cut keeps the increment workflow, which declares IncrementTraceObligations, with
    # its owned members: the inherited feature has its declared multiplicity and no owned
    # relationship is missing.
    assert inherited["applicablePhases"]["multiplicity"] == [0, "*"]
    assert not [gap for gap in answer["gaps"] if gap["category"] == "definition-incomplete"]
    for entry in (inherited["increment"], inherited["applicablePhases"]):
        assert entry["inherited_from"] == "DE4SDV_IncrementWorkflow::IncrementTraceObligations"
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
    answer, definition = _definition(service, "DE4SDV_TraceVocabulary::DerivesFromNeed")
    assert answer["element"]["keyword"] == "connection def"
    # end need : StakeholderNeedCandidate; end derivedRequirement : RequirementCandidate;
    declared = {"need": "DE4SDV_MethodContext::StakeholderNeedCandidate",
                "derivedRequirement": "DE4SDV_MethodContext::RequirementCandidate"}
    ends = _features(definition["owned_features"])
    assert set(ends) == set(declared)
    for name, entry in ends.items():
        assert (entry["end"], entry["keyword"], entry["type"]) == (True, "ref", declared[name])
    # The cut keeps both ends but neither doc comment (``private doc ontologyDefinition``
    # and ``doc``): the answer has no documentation, and the definition-incomplete gap
    # names the two owned relationships the cut lacks.
    assert answer["element"]["documentation"] == []
    named = [re.search(r"DE4SDV_TraceVocabulary::DerivesFromNeed \(([^)]*)\)", gap["reason"])
             for gap in answer["gaps"] if gap["category"] == "definition-incomplete"]
    missing = [identifier for found in named if found for identifier in found.group(1).split(", ")]
    assert len(missing) == 2, missing


def test_a_referential_usage_is_described_with_ref(service) -> None:
    """``ref part increment : EngineeringIncrement;`` (IncrementTraceObligations in
    DE4SDV_IncrementWorkflow): an undirected, non-end part usage that isn't composite is
    declared with ``ref part``. Composite, directed and end features keep their own keyword."""
    element = service.inspect_element("DE4SDV_IncrementWorkflow::IncrementTraceObligations::increment")["element"]
    assert (element["keyword"], element["sysml_type"]) == ("ref part", "PartUsage")
    _answer, obligations = _definition(service, "DE4SDV_IncrementWorkflow::IncrementTraceObligations")
    assert _features(obligations["owned_features"])["increment"]["keyword"] == "ref part"
    _answer, frame = _definition(service, "DE4SDV_IncrementWorkflow::FrameIncrement")
    # out part increment : EngineeringIncrement; (directed: referential without ref)
    assert _features(frame["owned_features"])["increment"]["keyword"] == "part"


def test_a_library_supertype_has_the_same_entry_keys_as_any_supertype(service) -> None:
    """``enum def LevelKind :> ScalarValues::Real`` (SYSMOD, a pinned dependency):
    ScalarValues is not part of the export, so the entry has no element, but it has
    the keys of every supertype entry."""
    keys = {"element_id", "qualified_name", "sysml_type", "relationship_id", "direct", "outside_export"}
    answer, definition = _definition(service, "SYSMOD::LevelKind")
    [library] = definition["supertypes"]
    assert set(library) == keys
    assert (library["element_id"], library["qualified_name"], library["sysml_type"]) == (None, None, None)
    assert (library["direct"], library["outside_export"]) == (True, True)
    [outside] = [gap["reason"] for gap in answer["gaps"] if gap["category"] == "definition-outside-export"]
    assert outside.startswith("SYSMOD::LevelKind specializes an element outside this export")
    assert (f"the export's external references record its target, and this API revision keeps only the "
            f"specialization {library['relationship_id']}") in outside
    _answer, charter = _definition(service, "DE4SDV_IncrementWorkflow::IncrementCharter")
    [direct] = charter["supertypes"]
    assert set(direct) == keys
    assert (direct["qualified_name"], direct["sysml_type"], direct["direct"], direct["outside_export"]) == (
        "DE4SDV_IncrementWorkflow::IncrementTraceObligations", "PartDefinition", True, False)
    assert direct["relationship_id"] and direct["element_id"]


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
    #   subject visualizationTestSystem :> ...; stakeholder verificationEngineer : ...;
    #   require constraint statement {...}
    need = "DE4SDV_AEBSVisualizationNeedsRequirements::VisualizationNeeds::needNonInterference"
    for name, keyword in (("", "requirement"), ("::visualizationTestSystem", "subject"),
                          ("::verificationEngineer", "stakeholder"), ("::statement", "require")):
        element = service.inspect_element(need + name)["element"]
        assert (element["qualified_name"], element["keyword"]) == (need + name, keyword)
        assert element["owning_package"]["qualified_name"] == (
            "DE4SDV_AEBSVisualizationNeedsRequirements::VisualizationNeeds")
        assert "definition" not in element


def test_the_api_listing_gives_the_answers_the_export_gives(cut, service) -> None:
    padded = _service(cut[0], _api_form(cut[0].elements))
    for identifier in ("DE4SDV_IncrementWorkflow::IncrementCharter", "DE4SDV_MethodProcess::MethodPhase",
                       "DE4SDV_TraceVocabulary::DerivesFromNeed", "DE4SDV_IncrementWorkflow::FrameIncrement",
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
    neighbors = service.semantic_neighbors("DE4SDV_TraceVocabulary::DerivesFromNeed")
    assert neighbors["root"]["qualified_name"] == "DE4SDV_TraceVocabulary::DerivesFromNeed"
    usage = service.resolve_element("INC-AEBS-010")["element"]
    assert usage["qualified_name"] == "DE4SDV_AEBSVisualizationFraming::incAEBS010"


def test_a_name_that_resolves_nowhere_says_which_revision_was_searched(cut, service) -> None:
    with pytest.raises(IdentityNotFoundError) as raised:
        service.inspect_element("DE4SDV_MethodContext::EngineeringIncrementt")
    message = str(raised.value)
    assert "no owned member named 'EngineeringIncrementt'" in message
    assert cut[0].revision.git_commit in message


def test_a_refusal_points_from_a_short_name_an_inherited_feature_or_an_import_to_the_canonical_name(
        service) -> None:
    """Only ownership-qualified element names resolve; the refusal says how SysML reaches the
    segment and gives the canonical qualified name, which resolves. Read from the sources:

    - ``part <'INC-AEBS-010'> incAEBS010 : VisualizationIncrement`` in DE4SDV_AEBSVisualizationFraming;
    - ``part def IncrementCharter :> IncrementTraceObligations``, whose ``ref part increment``
      IncrementTraceObligations declares, both in DE4SDV_IncrementWorkflow;
    - ``public import ReqStatus;`` in DE4SDV_MethodContext, for ``enum def ReqStatus`` of
      ``library package RequirementsManagement``.
    """
    cases = {
        "DE4SDV_AEBSVisualizationFraming::'INC-AEBS-010'": (
            "'INC-AEBS-010' is the short name of an owned member of DE4SDV_AEBSVisualizationFraming; "
            "its qualified name is", "DE4SDV_AEBSVisualizationFraming::incAEBS010"),
        "DE4SDV_IncrementWorkflow::IncrementCharter::increment": (
            "'increment' is inherited by DE4SDV_IncrementWorkflow::IncrementCharter from "
            "DE4SDV_IncrementWorkflow::IncrementTraceObligations; its qualified name is",
            "DE4SDV_IncrementWorkflow::IncrementTraceObligations::increment"),
        "DE4SDV_MethodContext::ReqStatus": (
            "'ReqStatus' is imported into DE4SDV_MethodContext (public import); its qualified name is",
            "RequirementsManagement::ReqStatus"),
    }
    for identifier, (reason, canonical) in cases.items():
        with pytest.raises(IdentityNotFoundError) as raised:
            service.inspect_element(identifier)
        assert f"{reason} {canonical}" in str(raised.value), identifier
        resolved = service.resolve_element(canonical)
        assert (resolved["resolution_level"], resolved["element"]["qualified_name"]) == (
            "qualified-name-match", canonical)


def test_the_mcp_tools_take_qualified_names_and_say_so(service) -> None:
    server = create_mcp_server(service)
    tools = {tool.name: tool for tool in server._tool_manager.list_tools()}
    for name in ("resolve_element", "inspect_element"):
        description = tools[name].description
        assert "qualified name" in description, name
        # Only ownership-qualified element names resolve; the description says so, and
        # how far the refusal's explanation reaches.
        for boundary in ("short name", "alias", "inherited", "imported", "ambiguous",
                         "one import level", "authored specializations"):
            assert boundary in description, (name, boundary)
    contract = tools["phase_contract"].description
    assert "`subject_type` containing `::`" in contract and "metaclass" in contract
    result = asyncio.run(server._tool_manager.call_tool(
        "inspect_element", {"identifier": "DE4SDV_MethodProcess::MethodPhase"}))
    assert result["element"]["definition"]["enumerated_values"][0]["name"] == "phase0_incrementFraming"
    assert result["revision"]["git_commit"] == service.binding.git_commit
