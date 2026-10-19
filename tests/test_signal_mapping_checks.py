"""The phase-8 signal-mapping checks, over a synthetic increment in the export's shapes.

``signalMappingRecorded`` reads the crossings: a physical element of the
increment that realizes a logical element (``allocatedTo``) and has a port
with a directed feature. Each logical element it realizes needs an allocation
typed by the kernel's ``SystemToSoftwareSignalMappingCandidate`` from it to a
physical element of the increment that realizes it (or to a port of one),
owning a ``LogicalToSoftwareSignalMappingRecord`` with a disposition, an owner
and a next action. ``semanticSourceNamed`` reads each signal mapping: the item
at its target is VSS-typed (a definition that VSS signal metadata annotates,
read by its ``path``), or its record states the semantic source. The scenario
declares a synthetic workflow with these checks; the genuine-shape evaluation
is in ``test_genuine_export_evaluation.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import de4sdv.semantic.increment_workflow as workflow_reader
from de4sdv.semantic import method_evaluator as me
from de4sdv.semantic.increment_evaluation import evaluate_increment
from de4sdv.semantic.increment_scope import ModelView
from de4sdv.semantic.relation_checks import carried_vss_paths, information_ports
from de4sdv.semantic.remedies import check_remedy
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
from test_remedies import _problems, _remedied
from test_revision_index import _traversal

REVISION = me.RevisionIdentity("a" * 40, "", "", workflow_reader.EXPORT_SNAPSHOT_SCOPE)
API_BINDING = me.RevisionIdentity("a" * 40, "project", "commit", "full-model")
P0, P8 = "phase0_incrementFraming", "phase8_physicalRealization"
CROSSING, SOURCE = "crossingHasSignalMapping", "signalMappingNamesSemanticSource"
P, C = WorkflowParameter, WorkflowCheck
DISPOSITIONS = ("mapped", "candidate", "deferred", "notApplicable")


@dataclass
class Realization:
    """Handles to a synthetic phase-8 realization with two crossings and their mappings."""

    scenario: Any
    package: dict[str, Any]
    roots: dict[str, dict[str, Any]]
    literals: dict[str, dict[str, Any]]
    relay: dict[str, Any]
    translator: dict[str, Any]
    lifecycle: dict[str, Any]
    host: dict[str, Any]
    guest: dict[str, Any]
    speed: dict[str, Any]
    launcher: dict[str, Any]
    frame_mapping: dict[str, Any]
    frame_record: dict[str, Any]
    speed_mapping: dict[str, Any]
    speed_record: dict[str, Any]

    @property
    def builder(self):
        return self.scenario.builder


def _port_definition(b, package, name: str, direction: str, item_type: dict[str, Any]) -> dict[str, Any]:
    """``port def <name> { <direction> item payload : <item_type>; }``."""
    port_def = b.definition("PortDefinition", name, package)
    b.usage("ItemUsage", "payload", port_def, [item_type], membership="FeatureMembership", direction=direction)
    return port_def


def _record(b, mapping: dict[str, Any], record_def: dict[str, Any], literal: dict[str, Any], short: str,
            **texts: str) -> dict[str, Any]:
    """``item <'MAP-…'> <name> : LogicalToSoftwareSignalMappingRecord { disposition, owner, nextAction, … }``."""
    record = b.usage("ItemUsage", short.lower().replace("-", ""), mapping, [record_def], short=short,
                     membership="FeatureMembership", isComposite=True)
    b.attribute(record, "disposition", literal)
    for member, text in {"owner": "DE4SDV maintainers", "nextAction": "phase 10: test it", **texts}.items():
        if text:
            b.attribute(record, member, text)
    return record


def _realization(*, workflow: bool = True) -> Realization:
    """A frame relay realized by a host and a guest process (one mapping, from the relay to the host's port,
    whose record states the frame's semantic source), a speed translator realized by a speed process (a
    mapping to its port, whose payload's speed_kmh is typed by a VSS signal), and a lifecycle bridge realized
    by a launcher without ports (no crossing). The charter declares phases 0 and 8."""
    scenario = increment_scenario(ModelBuilder(label="signal-mapping", kernel_packages=True),
                                  applicable_phases=(P0, P8))
    b = scenario.builder
    package = scenario.needs_package
    roots = {cls: b.kernel_definition(cls) for cls in (
        "Function", "LogicalElement", "PhysicalElement", "SystemToSoftwareSignalMappingCandidate",
        "LogicalToSoftwareSignalMappingRecord")}
    literals = b.enumeration("SignalMappingDisposition", DISPOSITIONS)
    # A VSS signal as COVESA_VSS declares one: an attribute definition its signal metadata annotates.
    vss = b.package("FixtureVSS")
    vehicle_speed = b.definition("AttributeDefinition", "Vehicle_Speed", vss)
    metadata = b.usage("MetadataUsage", None, vss, annotatedElement=[{"@id": vehicle_speed["@id"]}])
    b.attribute(metadata, "path", "Vehicle.Speed")
    frame_def = b.definition("ItemDefinition", "FixtureFrame", package)
    payload = b.definition("ItemDefinition", "FixtureSpeedPayload", package)
    b.usage("AttributeUsage", "speed_kmh", payload, [vehicle_speed], membership="FeatureMembership")
    frame_out = _port_definition(b, package, "FrameOut", "out", frame_def)
    frame_in = _port_definition(b, package, "FrameIn", "in", frame_def)
    speed_in = _port_definition(b, package, "SpeedIn", "in", payload)
    logical_def = b.definition("PartDefinition", "FixtureLogicalRole", package, [roots["LogicalElement"]])
    relay = b.usage("PartUsage", "frameRelay", package, [logical_def])
    translator = b.usage("PartUsage", "speedTranslator", package, [logical_def])
    lifecycle = b.usage("PartUsage", "lifecycleBridge", package, [logical_def])
    process_def = b.definition("PartDefinition", "FixtureProcess", package, [roots["PhysicalElement"]])
    host = b.usage("PartUsage", "hostProcess", package, [process_def])
    host_port = b.usage("PortUsage", "frameOut", host, [frame_out], membership="FeatureMembership")
    guest = b.usage("PartUsage", "guestProcess", package, [process_def])
    b.usage("PortUsage", "frameIn", guest, [frame_in], membership="FeatureMembership")
    speed = b.usage("PartUsage", "speedProcess", package, [process_def])
    speed_port = b.usage("PortUsage", "speedIn", speed, [speed_in], membership="FeatureMembership")
    launcher = b.usage("PartUsage", "launcher", package, [process_def])
    for name, logical, physical in (("relayToHost", relay, host), ("relayToGuest", relay, guest),
                                    ("translatorToSpeed", translator, speed), ("lifecycleToLauncher", lifecycle,
                                                                                launcher)):
        b.allocation(name, package, logical, physical)
    mapping_def, record_def = roots["SystemToSoftwareSignalMappingCandidate"], roots["LogicalToSoftwareSignalMappingRecord"]
    frame_mapping = b.allocation("frameSignalMapping", package, relay, host_port, typed_by=mapping_def)
    frame_record = _record(b, frame_mapping, record_def, literals["candidate"], "MAP-FIXTURE-FRAME",
                           semanticSource="an opaque display frame, no vehicle signal by owner decision")
    speed_mapping = b.allocation("speedSignalMapping", package, translator, speed_port, typed_by=mapping_def)
    speed_record = _record(b, speed_mapping, record_def, literals["candidate"], "MAP-FIXTURE-SPEED")
    realization = Realization(scenario, package, roots, literals, relay, translator, lifecycle, host, guest, speed,
                              launcher, frame_mapping, frame_record, speed_mapping, speed_record)
    if workflow:
        _workflow(realization)
    return realization


def _workflow(r: Realization) -> None:
    increment_workflow(r.builder, [
        WorkflowStep("frameIncrement", P0, (P("increment", "EngineeringIncrement"),)),
        WorkflowStep("definePhysicalRealization", P8, (
            P("logicalElements", "LogicalElement", "PartUsage", "in", (1, INFINITY)),
            P("physicalElements", "PhysicalElement", "PartUsage", "out", (1, INFINITY)),
            P("signalMappings", "SystemToSoftwareSignalMappingCandidate", "AllocationUsage", "out", (0, INFINITY))), (
            C("logicalElementAllocatedToPhysicalElement", "allocatedTo", "logicalElements"),
            C(CROSSING, "signalMappingRecorded", "physicalElements", advisory=True),
            C(SOURCE, "semanticSourceNamed", "signalMappings", advisory=True))),
    ], charter=r.scenario.charter)


def _view(r: Realization) -> ModelView:
    b = r.builder
    return ModelView(b.elements, _traversal(b), sources=b.sources)


def _evaluate(r: Realization, revision: me.RevisionIdentity = REVISION):
    return evaluate_increment(_view(r), r.scenario.increment_id, revision=revision)


def _results(evaluation, gate: str) -> dict[str, me.EvaluationResult]:
    return {r.subject_id: r for r in evaluation.canonical.results if r.unit_id == gate and r.subject_id}


def _verdicts(evaluation, gate: str) -> dict[str, str]:
    return {subject: result.verdict for subject, result in _results(evaluation, gate).items()}


def _note(evaluation, gate: str) -> dict[str, Any] | None:
    return next((note for note in evaluation.gaps()["advisory"] if note["gate"] == gate), None)


# -- the crossings ----------------------------------------------------------


def test_information_ports_are_read_from_the_port_definition() -> None:
    r = _realization(workflow=False)
    view = _view(r)
    assert [view.index.name_of(p) for p in information_ports(view, r.host["@id"])] == ["frameOut"]
    assert information_ports(view, r.launcher["@id"]) == []


def test_each_crossing_is_covered_by_a_mapping_of_the_logical_element_it_realizes() -> None:
    """The guest process is covered by the relay's one mapping to the host's port: one mapping per logical
    element covers the processes of its chain. The launcher has no port with a directed feature: no crossing."""
    r = _realization()
    evaluation = _evaluate(r)
    assert _verdicts(evaluation, CROSSING) == {
        r.host["@id"]: me.VERDICT_PASS, r.guest["@id"]: me.VERDICT_PASS, r.speed["@id"]: me.VERDICT_PASS,
        r.launcher["@id"]: me.VERDICT_NOT_APPLICABLE}
    assert _results(evaluation, CROSSING)[r.guest["@id"]].targets == (r.frame_record["@id"],)
    assert _note(evaluation, CROSSING) is None


def test_a_crossing_without_a_mapping_is_an_advisory_note_with_the_mapping_to_author() -> None:
    r = _realization()
    r.builder.remove(r.speed_mapping)
    evaluation = _evaluate(r)
    assert _verdicts(evaluation, CROSSING)[r.speed["@id"]] == me.VERDICT_FAIL
    note = _note(evaluation, CROSSING)
    (subject,) = note["subjects"]
    view = _view(r)
    assert subject["diagnostics"][0] == (
        f"{view.label(r.speed['@id'])} realizes {view.label(r.translator['@id'])} and exchanges information items "
        f"through 1 port(s), but no SystemToSoftwareSignalMappingCandidate from {view.label(r.translator['@id'])} "
        "to a physical element of the increment that realizes it owns a mapping record with a disposition, an "
        "owner and a next action")
    (line,) = note["authoring"]["declarations"]
    assert line.startswith("allocation <name> : ")
    assert f" allocate {view.label(r.translator['@id'])} to {view.label(r.speed['@id'])}::speedIn {{ item <'MAP-<ID>'> " \
           "<record> : " in line
    assert "attribute :>> disposition = " in line and line.endswith(
        'attribute :>> owner = "<owner>"; attribute :>> nextAction = "<next action>"; } }')
    assert _exits(evaluation)[P8] == "READY"  # advisory: never blocks


def test_a_record_without_owner_or_next_action_does_not_cover_its_crossing() -> None:
    r = _realization()
    b = r.builder
    b.remove(b.feature_of(r.speed_record, "owner"), b.feature_of(r.speed_record, "nextAction"))
    evaluation = _evaluate(r)
    result = _results(evaluation, CROSSING)[r.speed["@id"]]
    assert result.verdict == me.VERDICT_FAIL
    assert result.diagnostics[1] == f"{_view(r).label(r.speed_record['@id'])} states no owner, nextAction"


def test_a_mapping_to_an_element_that_does_not_realize_the_logical_element_does_not_count() -> None:
    r = _realization()
    b = r.builder
    b.remove(r.frame_mapping)
    elsewhere = b.usage("PartUsage", "elsewhere", r.package)
    wrong = b.allocation("frameToElsewhere", r.package, r.relay, elsewhere,
                         typed_by=r.roots["SystemToSoftwareSignalMappingCandidate"])
    _record(b, wrong, r.roots["LogicalToSoftwareSignalMappingRecord"], r.literals["candidate"], "MAP-FIXTURE-WRONG")
    evaluation = _evaluate(r)
    result = _results(evaluation, CROSSING)[r.host["@id"]]
    assert result.verdict == me.VERDICT_FAIL
    view = _view(r)
    assert result.diagnostics[1] == (
        f"{view.label(wrong['@id'])} is allocated to {view.label(elsewhere['@id'])}, in no physical element of the "
        f"increment that realizes {view.label(r.relay['@id'])}")


def test_an_untyped_allocation_to_a_port_is_no_signal_mapping() -> None:
    r = _realization()
    b = r.builder
    b.remove(r.speed_mapping)
    port = b.feature_of(r.speed, "speedIn")
    b.allocation("untypedSpeedMapping", r.package, r.translator, port)
    assert _verdicts(_evaluate(r), CROSSING)[r.speed["@id"]] == me.VERDICT_FAIL


# -- the semantic source -------------------------------------------------------


def test_a_vss_typed_item_names_its_semantic_source() -> None:
    r = _realization()
    view = _view(r)
    assert carried_vss_paths(view, view.index.feature(r.speed["@id"], "speedIn")) == ["Vehicle.Speed"]
    result = _results(_evaluate(r), SOURCE)[r.speed_mapping["@id"]]
    assert (result.verdict, result.diagnostics) == (me.VERDICT_PASS, ("VSS-typed: Vehicle.Speed",))


def test_a_record_that_states_its_semantic_source_names_it() -> None:
    r = _realization()
    result = _results(_evaluate(r), SOURCE)[r.frame_mapping["@id"]]
    assert (result.verdict, result.diagnostics) == (
        me.VERDICT_PASS, ("semantic source stated: an opaque display frame, no vehicle signal by owner decision",))


def test_an_item_neither_vss_typed_nor_stated_gets_the_line_to_author_in_its_record() -> None:
    r = _realization()
    b = r.builder
    b.remove(b.feature_of(r.frame_record, "semanticSource"))
    evaluation = _evaluate(r)
    view = _view(r)
    assert _verdicts(evaluation, SOURCE)[r.frame_mapping["@id"]] == me.VERDICT_FAIL
    note = _note(evaluation, SOURCE)
    (subject,) = note["subjects"]
    assert subject["diagnostics"] == [
        f"{view.label(r.frame_mapping['@id'])} carries no VSS-typed item at "
        f"{view.label(view.index.feature(r.host['@id'], 'frameOut'))}, and {view.label(r.frame_record['@id'])} "
        "states no semantic source"]
    statement = 'attribute :>> semanticSource = "<what the item is, and why it is no VSS signal>";'
    assert note["authoring"]["declarations"] == [statement]
    assert f"in the existing {view.label(r.frame_record['@id'])}: {statement}" in note["what_to_author"]
    assert "type it with COVESA VSS instead of stating it" in note["what_to_author"]


def test_a_vss_path_in_a_string_is_no_vss_typing() -> None:
    """A record whose contract fields name the VSS path in text, over an untyped payload, names no source."""
    r = _realization()
    b = r.builder
    b.remove(b.feature_of(r.frame_record, "semanticSource"))
    b.attribute(r.frame_record, "dataTypeAndUnit", "VSS Vehicle.Speed, km/h")
    assert _verdicts(_evaluate(r), SOURCE)[r.frame_mapping["@id"]] == me.VERDICT_FAIL


def test_a_not_applicable_record_maps_no_item() -> None:
    r = _realization()
    b = r.builder
    b.remove(b.feature_of(r.frame_record, "semanticSource"), b.feature_of(r.frame_record, "disposition"))
    b.attribute(r.frame_record, "disposition", r.literals["notApplicable"])
    b.attribute(r.frame_record, "evidenceOrGap", "process control only; no information item crosses")
    evaluation = _evaluate(r)
    assert _verdicts(evaluation, SOURCE)[r.frame_mapping["@id"]] == me.VERDICT_NOT_APPLICABLE
    assert _verdicts(evaluation, CROSSING)[r.host["@id"]] == me.VERDICT_PASS  # a notApplicable record covers it


def test_a_mapping_without_a_record_gets_its_record_to_author() -> None:
    r = _realization()
    b = r.builder
    b.remove(r.frame_record)
    evaluation = _evaluate(r)
    assert _verdicts(evaluation, CROSSING)[r.host["@id"]] == me.VERDICT_FAIL
    note = _note(evaluation, SOURCE)
    view = _view(r)
    (line,) = note["authoring"]["declarations"]
    assert line.startswith("item <'MAP-<ID>'> <record> : ")
    assert f"in the existing {view.label(r.frame_mapping['@id'])}: {line}" in note["what_to_author"]


# -- the method around them -------------------------------------------------------


def _exits(evaluation) -> dict[str, str]:
    return {phase["phase"]: phase["phase_exit"]["status"] if isinstance(phase["phase_exit"], dict)
            else phase["phase_exit"] for phase in evaluation.status()["phases"] if phase.get("gates")}


def test_the_signal_mapping_checks_are_withheld_on_an_api_revision_binding() -> None:
    """They read native allocations: while allocatedTo has open forward obligations an API revision binding
    reports them as method side, as it does the allocation checks of phases 6 to 8."""
    api = _evaluate(_realization(), API_BINDING)
    for gate in (CROSSING, SOURCE):
        unit = next(u for u in api.canonical.units if u.unit_id == gate)
        assert (unit.verdict, unit.missing) == (None, ("governed-relation:allocatedTo",)), gate


def test_the_remedies_without_a_subject_declare_the_whole_mapping() -> None:
    r = _realization(workflow=False)
    view = _view(r)
    for check, member in (("signalMappingRecorded", 'attribute :>> owner = "<owner>";'),
                          ("semanticSourceNamed", 'attribute :>> semanticSource = "<what the item is, and why it is '
                                                  'no VSS signal>";')):
        (line,) = check_remedy(view, check).declarations
        assert line.startswith("allocation <name> : ") and " allocate <logical element> to <port> " in line, check
        assert member in line, check


def test_every_signal_mapping_remedy_is_authorable_sysml() -> None:
    """The remedies of both checks, for a crossing without a mapping, a record without its semantic source,
    a mapping without a record, and without a subject (the phase contract): accepted forms only, with the
    qualified types they name resolving and imported (the oracle of test_remedies)."""
    r = _realization()
    b = r.builder
    b.remove(r.speed_mapping, b.feature_of(r.frame_record, "semanticSource"))
    b.allocation("unrecordedMapping", r.package, r.lifecycle, r.launcher,
                 typed_by=r.roots["SystemToSoftwareSignalMappingCandidate"])
    evaluation = _evaluate(r)
    names = QualifiedNameIndex(b.elements)
    records = [record for answer in (evaluation.gaps(), evaluation.phase_contract()) for record in _remedied(answer)
               if (record.get("gate") or record.get("obligation_id")) in (CROSSING, SOURCE)]
    assert {record.get("gate") or record.get("obligation_id") for record in records} == {CROSSING, SOURCE}
    assert {(record.get("gate") or record.get("obligation_id")): _problems(record, names) for record in records} == {
        CROSSING: [], SOURCE: []}
