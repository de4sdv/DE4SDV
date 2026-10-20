"""The frozen genuine-export cut: evaluated end to end, and checked against its own records.

``fixtures/genuine_export/inc-aebs-010.json.gz`` is a frozen sample of real
serializer shapes (see the README beside it): a cut of the licensed export of
one revision, kept unchanged. These tests assert outcomes of that frozen cut,
never of the current model. It is evaluated exactly as
``scripts/evaluate_increment.py`` evaluates an export: kernel identity
validated from the export, every serializer shape the real one.
"""

from __future__ import annotations

import copy
import gzip
import hashlib
import json
import re
import uuid
from pathlib import Path
from types import SimpleNamespace

from de4sdv.semantic import method_evaluator as me
from de4sdv.semantic.export_evaluation import evaluate_export
from de4sdv.semantic.increment_scope import scope_closure
from de4sdv.semantic.method_checks import NAMED_CHECKS
from de4sdv.semantic.relation_checks import VSS_SIGNAL_METADATA, carried_vss_paths, signal_mappings
from de4sdv.semantic.remedies import check_remedy
from de4sdv.sysml_api.qualified_names import QualifiedNameIndex
from de4sdv.sysml_api.repository import reference_ids
from increment_model_fixtures import GENUINE_EXPORT

#: The 20 requirements of INC-AEBS-010, all in the needs-and-requirements package the cut keeps in full.
REQUIREMENTS = [
    "reqAaosEnvironmentObservation", "reqAvailabilityDisposition", "reqDe4sdvParticipation",
    "reqDecisionDistanceExclusionStatement", "reqEvidenceCorrelation", "reqFailClosedFreshness",
    "reqInvalidRejection", "reqNativeParticipation", "reqNoDisplayDerivedDecisionMetric",
    "reqNoFreshDataSubstitution", "reqNoHostBrowserSurface", "reqNoNativeImpersonation", "reqNonColorStateCue",
    "reqNonInterference", "reqObstacleGeometryExpiry", "reqObstacleGeometryFromFilteredCloud",
    "reqReadOnlyBoundaryStatement", "reqRealAAOSRendering", "reqRestorationBehavior", "reqSourceFidelity",
]


#: Of the 20, the ones no function and no architecture element carry. The cut holds no verification case,
#: so none of them has one yet (the full export of the same revision covers them by verification only).
UNCARRIED = [
    "reqAaosEnvironmentObservation", "reqDecisionDistanceExclusionStatement", "reqNoDisplayDerivedDecisionMetric",
    "reqNoFreshDataSubstitution", "reqNoHostBrowserSurface", "reqNoNativeImpersonation", "reqNonColorStateCue",
    "reqObstacleGeometryExpiry", "reqObstacleGeometryFromFilteredCloud", "reqReadOnlyBoundaryStatement",
]


def _evaluated(tmp_path: Path):
    export = tmp_path / "export.json"
    export.write_bytes(gzip.decompress(GENUINE_EXPORT.read_bytes()))
    return evaluate_export(export, "INC-AEBS-010")


def test_the_frozen_cut_passes_framing_needs_and_requirements_and_next_asks_for_verification_cases(
        tmp_path: Path) -> None:
    """The cut keeps the framing, needs-and-requirements, functional, logical and
    physical packages in full and the other declared packages as package elements
    only. Its verification cases are therefore outside the cut: phase 10 finds
    none, so next asks for them and no requirement is verified. The full export of
    the same revision answers next none (Method Check run 39227136691); this is the
    cut boundary, not the model."""
    snapshot, evaluation = _evaluated(tmp_path)
    assert snapshot.identity_mode == "export-validated-kernel-bindings"
    phases = {phase["phase"]: phase for phase in evaluation.status()["phases"]}
    assert {name: (phase["conformance_verdict"], len(phase["gates"])) for name, phase in phases.items()
            if phase["gates"]} == {
        "phase0_incrementFraming": (me.VERDICT_PASS, 15),
        "phase4_needs": (me.VERDICT_PASS, 6),
        "phase5_requirements": (me.VERDICT_PASS, 6),
        "phase6_functionalArchitecture": (me.VERDICT_PASS, 4),
        "phase7_logicalArchitecture": (me.VERDICT_PASS, 2),
        "phase8_physicalRealization": (me.VERDICT_PASS, 4),
        "phase10_vvEvidence": (me.VERDICT_FAIL, 3),
    }
    assert phases["phase4_needs"]["applicability"] == "declared"  # an optional [0..1] step
    step = evaluation.next_obligation()["next"]
    assert (step["stage"], step["gate"], step["kind"]) == (
        "phase10_vvEvidence", "verificationCaseVerifiesRequirement", "violation")
    assert [subject["reason_codes"] for subject in step["subjects"]] == [[me.POPULATION_POLICY_VIOLATION]]
    # An untyped parameter is named by its keyword (its metaclass is no model element), and the remedy
    # says how one verification case is declared.
    assert step["what_to_author"].startswith(
        "keep at least 1 verification usage in the increment's packages named in the charter's expectedArtifacts")
    assert step["authoring"]["declarations"] == [
        "verification <name> { objective { verify <requirement of the increment>; } }"]
    blocking = {gap["gate"]: gap for gap in evaluation.gaps()["blocking"]}
    assert set(blocking) == {"verificationCaseVerifiesRequirement", "requirementVerifiedByVerificationCase"}
    assert all(gap["phase"] == "phase10_vvEvidence" for gap in blocking.values())
    assert sorted(s["name"] for s in blocking["requirementVerifiedByVerificationCase"]["subjects"]) == REQUIREMENTS


def test_the_frozen_cut_traces_its_allocation_chain_through_chained_ends_and_definition_features(
        tmp_path: Path) -> None:
    """Genuine shapes of phases 6 to 8: the functions and logical roles are features of the flow and
    system definitions (counted at any depth), and the function-to-logical and logical-to-physical
    allocations are written with feature chains (read as their last feature). No requirement is a
    FunctionalRequirementCandidate, so the blocking phase-6 trace does not apply, while the phase's
    population check counts its eight functions; ten of the twenty requirements are carried by no
    architecture element (advisory)."""
    _snapshot, evaluation = _evaluated(tmp_path)
    results = {}
    for result in evaluation.canonical.results:
        if result.subject_id:
            results.setdefault(result.unit_id, {})[result.subject_id] = result.verdict
    assert {gate: (len(found), sum(v == me.VERDICT_PASS for v in found.values()))
            for gate, found in results.items() if gate in (
                "incrementHasFunction", "functionAllocatedToLogicalElement", "logicalElementAllocatedToPhysicalElement",
                "physicalElementCarriesLogicalElement", "functionCarriesRequirement",
                "logicalElementCarriesFunction", "requirementCarriedByArchitecture")} == {
        "incrementHasFunction": (8, 8),
        "functionAllocatedToLogicalElement": (8, 8),
        "logicalElementAllocatedToPhysicalElement": (9, 9),
        "physicalElementCarriesLogicalElement": (8, 8),
        "functionCarriesRequirement": (8, 6),
        "logicalElementCarriesFunction": (9, 6),
        "requirementCarriedByArchitecture": (20, 10),
    }
    advisory = {note["gate"]: sorted(s["name"] for s in note["subjects"]) for note in evaluation.gaps()["advisory"]}
    assert advisory["requirementCarriedByArchitecture"] == UNCARRIED
    (note,) = [note for note in evaluation.gaps()["advisory"] if note["gate"] == "requirementCarriedByArchitecture"]
    assert {s["name"]: s["diagnostics"] for s in note["subjects"]} == {
        name: [f"DE4SDV_AEBSVisualizationNeedsRequirements::VisualizationRequirements::{name} is carried by no "
               "architecture element and has no verification case yet"] for name in UNCARRIED}
    assert advisory["functionCarriesRequirement"] == ["publish", "transport"]
    assert advisory["logicalElementCarriesFunction"] == ["coordinatorSource", "displayService", "nativeAebSource"]
    assert "functionalRequirementAllocatedToFunction" not in results


def test_the_frozen_cut_has_crossings_without_a_signal_mapping(tmp_path: Path) -> None:
    """Genuine shapes of the phase-8 signal-mapping control: INC-AEBS-010 declares no signal mapping, so
    each physical element that realizes a logical element through an information port is an advisory
    crossing without a record: ports typed by their port definitions or inherited from the element's
    definition, the coordinator's untyped ports through the connected ports' directed items, and the pinned
    AEB node's ports, whose definitions the cut keeps as references only, through their connected ports."""
    _snapshot, evaluation = _evaluated(tmp_path)
    crossings = {evaluation.view.index.name_of(r.subject_id): r.verdict for r in evaluation.canonical.results
                 if r.unit_id == "crossingHasSignalMapping" and r.subject_id}
    assert crossings == {name: me.VERDICT_FAIL for name in (
        "evidenceRecorder", "dataTunnel", "displayApp", "gatewayIngress", "sourceAdapter", "transport",
        "coordinator", "pinnedAeb")}
    mappings = next(u for u in evaluation.canonical.units if u.unit_id == "signalMappingNamesSemanticSource")
    assert mappings.verdict == me.VERDICT_NOT_APPLICABLE  # no signal mapping in the increment
    phase = next(p for p in evaluation.status()["phases"] if p["phase"] == "phase8_physicalRealization")
    exit_ = phase["phase_exit"]
    assert (exit_["status"] if isinstance(exit_, dict) else exit_) == "READY"  # advisory


# -- signal mappings authored in genuine shapes ------------------------------------------

#: INC-MW-011's mappings, which the cut keeps with what their targets' signals are read through.
SCORE = "DE4SDV_MiddlewareSCOREPhysicalSoftwareRealization"
SPEED_MAPPING, FRAME_MAPPING = f"{SCORE}::vehicleSpeedSignalMapping", f"{SCORE}::aebsSignalFrameSignalMapping"


def _ids(value) -> list[str]:
    if isinstance(value, dict):
        return [value["@id"]] if "@id" in value else []
    return [found for item in value for found in _ids(item)] if isinstance(value, list) else []


def _one(export: dict, qualified: str, kind: str | None = None) -> str:
    found = [e["@id"] for e in QualifiedNameIndex(export["elements"]).resolve(qualified)
             if kind is None or e["@type"] == kind]
    assert len(found) == 1, (qualified, found)
    return found[0]


def _clone_mapping(export: dict, template: str, name: str, package: str, source: str, chain: list[str]) -> str:
    """Author a signal mapping into ``export`` in genuine shapes: the genuine ``template`` mapping's subtree,
    its record included, with fresh identities, its source end re-pointed to ``source`` and its target end to
    ``chain``: one feature, referenced as the template does, or a feature chain, written as the cut's
    chained allocation ends write theirs (a Feature the end's ReferenceSubsetting owns, one FeatureChaining
    per chained feature). Owned by ``package``; returns the new mapping's id."""
    by_id = {e["@id"]: e for e in export["elements"]}
    subtree, frontier = [], [template]
    while frontier:
        current = frontier.pop()
        if current not in subtree and current in by_id:
            subtree.append(current)
            frontier += _ids(by_id[current].get("ownedRelationship")) + _ids(by_id[current].get("ownedRelatedElement"))
    fresh = {old: str(uuid.uuid5(uuid.NAMESPACE_URL, f"{name}/{old}")) for old in subtree}

    def renamed(value):
        if isinstance(value, dict):
            return {k: (fresh.get(v, v) if k == "@id" else renamed(v)) for k, v in value.items()}
        return [renamed(v) for v in value] if isinstance(value, list) else value

    clones = {fresh[old]: dict(renamed(copy.deepcopy(by_id[old])), elementId=fresh[old]) for old in subtree}
    mapping = clones[fresh[template]]
    mapping["declaredName"] = name
    added = []
    for membership in (clones[r["@id"]] for r in mapping["ownedRelationship"] if r["@id"] in clones):
        if membership["@type"] != "EndFeatureMembership":
            continue
        end = clones[_ids(membership["memberElement"])[0]]
        subsetting = next(clones[r["@id"]] for r in end["ownedRelationship"]
                          if clones.get(r["@id"], {}).get("@type") == "ReferenceSubsetting")
        previous = _ids(subsetting["referencedFeature"])[0]
        target = source if membership["memberName"] == "source" else chain[0]
        if membership["memberName"] == "target" and len(chain) > 1:
            chained = next(f for e in export["elements"] if e["@type"] == "ReferenceSubsetting"
                           and e.get("ownedRelatedElement") for f in _ids(e["ownedRelatedElement"])
                           if by_id[f]["@type"] == "Feature" and by_id[f].get("ownedRelationship"))
            target = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{name}/chain"))
            feature = dict(copy.deepcopy(by_id[chained]), **{"@id": target, "elementId": target},
                           owningRelationship={"@id": subsetting["@id"]}, ownedRelationship=[])
            template_chaining = by_id[_ids(by_id[chained]["ownedRelationship"])[0]]
            for position, link in enumerate(chain):
                chaining = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{name}/chaining/{position}"))
                added.append(dict(copy.deepcopy(template_chaining), **{"@id": chaining, "elementId": chaining},
                                  chainingFeature={"@id": link}, owningRelatedElement={"@id": target}))
                feature["ownedRelationship"].append({"@id": chaining})
            added.append(feature)
            subsetting["ownedRelatedElement"] = [{"@id": target}]
        for key, value in list(subsetting.items()):
            if isinstance(value, dict) and value.get("@id") == previous:
                subsetting[key] = {"@id": target}
        if membership["memberName"] == "target":
            mapping["target"] = [{"@id": target}]
    owning = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{name}/membership"))
    mapping["owningRelationship"] = {"@id": owning}
    added.append({"@id": owning, "elementId": owning, "@type": "OwningMembership", "memberName": name,
                  "memberElement": {"@id": mapping["@id"]}, "ownedRelatedElement": [{"@id": mapping["@id"]}],
                  "owningRelatedElement": {"@id": package}})
    by_id[package]["ownedRelationship"].append({"@id": owning})
    export["elements"] += [*clones.values(), *added]
    export["element_sources"].update({e["@id"]: export["element_sources"][package] for e in [*clones.values(), *added]})
    return mapping["@id"]


def _evaluate_cut(tmp_path: Path, export: dict, increment: str = "INC-AEBS-010"):
    path = tmp_path / f"export-{uuid.uuid4().hex[:8]}.json"
    path.write_text(json.dumps(export))
    return evaluate_export(path, increment)


def _cut() -> dict:
    return json.loads(gzip.decompress(GENUINE_EXPORT.read_bytes()))


def test_a_crossing_s_inherited_port_is_named_through_the_element_and_following_the_remedy_clears_it(
        tmp_path: Path) -> None:
    """R1, on genuine shapes: evidenceRecorder's information port, renderedIn, is its definition's. The remedy
    names it as a chain through the element; authored so (the genuine speed mapping's subtree, the cut's
    chained-end shape), the crossing is covered. Allocated to the definition's port itself, it is not: that
    port is every usage's."""
    export = _cut()
    _snapshot, evaluation = _evaluate_cut(tmp_path, export)
    view = evaluation.view
    recorder = next(r.subject_id for r in evaluation.canonical.results if r.unit_id == "crossingHasSignalMapping"
                    and view.index.name_of(r.subject_id) == "evidenceRecorder")
    (line,) = check_remedy(view, "signalMappingRecorded", subject=recorder, scope=evaluation.scope).declarations
    source_text, target_text = re.search(r" allocate (\S+) to (\S+) \{ ", line).groups()
    assert target_text == f"{view.label(recorder)}.renderedIn"
    physical = "DE4SDV_AEBSVisualizationPhysicalSoftwareRealization"
    port = _one(export, f"{physical}::VisualizationEvidenceRecorder::renderedIn", "PortUsage")
    package = _one(export, physical, "Package")
    for name, chain, verdict in (("toTheDefinitionPort", [port], me.VERDICT_FAIL),
                                 ("throughTheElement", [recorder, port], me.VERDICT_PASS)):
        authored = copy.deepcopy(export)
        _clone_mapping(authored, _one(authored, SPEED_MAPPING), name, package, _one(authored, source_text), chain)
        _snapshot, after = _evaluate_cut(tmp_path, authored)
        result = next(r for r in after.canonical.results if r.unit_id == "crossingHasSignalMapping"
                      and r.subject_id == recorder)
        assert result.verdict == verdict, (name, result.diagnostics)


def test_vss_typing_is_read_through_the_genuine_annotation_of_the_bound_signal_metadata(tmp_path: Path) -> None:
    """R3 and R5, on genuine shapes: the cut keeps INC-MW-011's speed mapping, its target port and the
    COVESA_VSS signal it carries, whose package-level @VssSignalMetadata owns an Annotation of the signal
    (the serializer emits no annotatedElement key). The loader binds the metadata definition by the
    file-mapped rule, and the speed mapping's port carries Vehicle.Speed."""
    export = _cut()
    snapshot, evaluation = _evaluate_cut(tmp_path, export)
    view = evaluation.view
    assert snapshot.library_bindings == {VSS_SIGNAL_METADATA: view.library_element(VSS_SIGNAL_METADATA)}
    metadata = [m for m in view.index.elements_of_type("MetadataUsage")
                if view.library_element(VSS_SIGNAL_METADATA) in view.index.typed_by(m)]
    assert metadata and all(view.index.owned_relationships(m, "Annotation") for m in metadata)
    assert not any("annotatedElement" in view.index.element(m) for m in metadata)
    speed = _one(export, SPEED_MAPPING)
    target = signal_mappings(view)[speed][0][1]
    assert carried_vss_paths(view, target) == ["Vehicle.Speed"]
    result = NAMED_CHECKS["semanticSourceNamed"](view, evaluation.scope, speed)
    assert (result.status, result.diagnostics) == ("satisfied", ("VSS-typed: Vehicle.Speed",))


def test_a_mapping_to_an_element_does_not_take_the_vss_typing_of_its_ports(tmp_path: Path) -> None:
    """R3, on genuine shapes: INC-MW-011's frame mapping, authored again without any semanticSource and
    allocated to the adapter element, whose speed port carries Vehicle.Speed, names no semantic source."""
    export = _cut()
    by_id = {e["@id"]: e for e in export["elements"]}
    frame = _one(export, FRAME_MAPPING)
    for record in (by_id[m] for r in by_id[frame]["ownedRelationship"] for m in _ids(by_id[r["@id"]].get("memberElement"))
                   if str(by_id[m].get("declaredShortName", "")).startswith("MAP-")):
        record["ownedRelationship"] = [r for r in record["ownedRelationship"]
                                       if by_id[r["@id"]].get("memberName") != "semanticSource"]
    adapter = _one(export, f"{SCORE}::SCOREMiddlewareIntegrationLayerRealization::adapter", "PartUsage")
    source = _one(export, "DE4SDV_MiddlewareSCORELogicalArchitecture::hmiFrameRelay")
    mapping = _clone_mapping(export, frame, "frameToTheAdapterElement", _one(export, SCORE, "Package"), source,
                             [adapter])
    _snapshot, evaluation = _evaluate_cut(tmp_path, export)
    view = evaluation.view
    assert carried_vss_paths(view, adapter) == ["Vehicle.Speed"]  # what the element's ports carry
    result = NAMED_CHECKS["semanticSourceNamed"](view, evaluation.scope, mapping)
    assert result.status == "violated"
    assert result.diagnostics[0].startswith(f"{view.label(mapping)} is allocated to the element {view.label(adapter)}: "
                                            "VSS typing is read only at a port")


def test_the_scope_closure_counts_no_parameter_and_no_definition_end_of_the_genuine_shapes(tmp_path: Path) -> None:
    """The export owns a definition's parameters and the ends of a connection or allocation definition
    through FeatureMembership, with ``direction`` set or ``isEnd`` true, not through ParameterMembership or
    EndFeatureMembership. The closure reads those native feature fields: no step parameter of the workflow
    and no end of a trace-vocabulary connection definition is an element of a scope naming their packages."""
    _snapshot, evaluation = _evaluated(tmp_path)
    view = evaluation.view
    packages = {view.label(p): p for p in view.index.elements_of_type("Package")}
    scope = SimpleNamespace(scope_packages=(packages["DE4SDV_IncrementWorkflow"], packages["DE4SDV_TraceVocabulary"]))
    closure = set(scope_closure(view, scope))
    labelled = {view.label(e): e for e in view.index.by_id if view.label(e)}
    parameter = labelled["DE4SDV_IncrementWorkflow::DefineFunctionalArchitecture::functions"]
    end = labelled["DE4SDV_TraceVocabulary::DerivesFromNeed::need"]
    owning = {member: str(relationship.get("@type")) for owner in view.index.by_id
              for relationship in view.index.owned_relationships(owner)
              for member in reference_ids(relationship.get("ownedRelatedElement"))}
    assert (owning[parameter], view.index.element(parameter).get("direction")) == ("FeatureMembership", "out")
    assert (owning[end], view.index.element(end).get("isEnd")) == ("FeatureMembership", True)
    assert parameter not in closure and end not in closure
    assert not [view.label(e) for e in closure
                if view.index.element(e).get("direction") or view.index.element(e).get("isEnd") is True]
    assert labelled["DE4SDV_IncrementWorkflow::DefineFunctionalArchitecture"] in closure
    assert labelled["DE4SDV_TraceVocabulary::DerivesFromNeed"] in closure


def _canonical(value) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode()


def _inconsistencies(text: bytes) -> list[str]:
    """How the cut's JSON departs from its own records (empty when self-consistent)."""
    cut = json.loads(text)
    found = [] if _canonical(cut) == text else ["the file is not the cut script's canonical serialization"]
    recorded = cut["cut_from"]["content_sha256"]
    found += [f"{part} differ from their recorded sha256" for part in ("elements", "element_sources")
              if hashlib.sha256(_canonical(cut[part])).hexdigest() != recorded[part]]
    if set(cut["element_sources"]) != {element["@id"] for element in cut["elements"]}:
        found.append("the element sources do not cover exactly the elements")
    files = {path for path in cut["element_sources"].values() if not path.startswith("@library/")}
    manifest = {entry["path"]: entry["sha256"] for entry in cut["source_manifest"]}
    if files != set(manifest) or not all(re.fullmatch(r"[0-9a-f]{64}", sha) for sha in manifest.values()):
        found.append(f"the source manifest does not list the source files: {sorted(files ^ set(manifest))}")
    if not re.fullmatch(r"[0-9a-f]{40}", str(cut.get("git_commit"))):
        found.append("no source revision is recorded")
    return found


def test_the_frozen_cut_is_self_consistent() -> None:
    """The cut matches its own records; it is never compared with the model at HEAD."""
    assert _inconsistencies(gzip.decompress(GENUINE_EXPORT.read_bytes())) == []
