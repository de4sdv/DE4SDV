"""The phase-8 signal-mapping checks, over a synthetic increment built in the builder's export shapes.

``signalMappingRecorded`` reads the crossings: a physical element of the
increment that realizes a logical element (``allocatedTo``) and has an
information port, a port with a directed feature of its own, of its
definition (a conjugated definition's original included), of a feature it
narrows, or of a port a connector connects it to. Each logical element it
realizes needs an allocation typed by the kernel's
``SystemToSoftwareSignalMappingCandidate`` that a package of the increment
owns, from it to a physical element of the increment that realizes it (or to a
port of one, directly or as a chain through the element), whose
``LogicalToSoftwareSignalMappingRecord`` records each state a disposition, an
owner and a next action, and when ``notApplicable`` why. ``semanticSourceNamed``
reads each signal mapping: its records state the semantic source, or the item
at its port is VSS-typed, read through metadata typed by COVESA_VSS's
``VssSignalMetadata``, which the loader binds by ADR 0011's file-mapped rule.
The VSS signal here has the serializer's shape: a package-level metadata usage
that owns an Annotation of the signal definition. The scenario declares a
synthetic workflow with these checks; the genuine shapes are evaluated in
``test_genuine_export_evaluation.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import de4sdv.semantic.increment_workflow as workflow_reader
from de4sdv.semantic import method_evaluator as me
from de4sdv.semantic.increment_evaluation import evaluate_increment
from de4sdv.semantic.increment_scope import ModelView
from de4sdv.semantic.relation_checks import (
    LIBRARY_PINS,
    VSS_SIGNAL_METADATA,
    carried_vss_paths,
    information_ports,
)
from de4sdv.semantic.remedies import check_remedy
from de4sdv.semantic.validation import resolve_library_pins
from de4sdv.sysml_api.qualified_names import QualifiedNameIndex
from increment_model_fixtures import (
    INFINITY,
    ModelBuilder,
    WorkflowCheck,
    WorkflowParameter,
    WorkflowStep,
    increment_scenario,
    increment_workflow,
    ref,
)
from test_remedies import _problems, _remedied
from test_revision_index import _traversal

REVISION = me.RevisionIdentity("a" * 40, "", "", workflow_reader.EXPORT_SNAPSHOT_SCOPE)
API_BINDING = me.RevisionIdentity("a" * 40, "project", "commit", "full-model")
P0, P8 = "phase0_incrementFraming", "phase8_physicalRealization"
CROSSING, SOURCE = "crossingHasSignalMapping", "signalMappingNamesSemanticSource"
RECORDED, NAMED = "signalMappingRecorded", "semanticSourceNamed"
P, C = WorkflowParameter, WorkflowCheck
DISPOSITIONS = ("mapped", "candidate", "deferred", "notApplicable")
VSS_FILE = LIBRARY_PINS[VSS_SIGNAL_METADATA].file
#: The verdict of an indeterminate result (input unavailable).
INDETERMINATE = None


@dataclass
class Realization:
    """Handles to a synthetic phase-8 realization with three crossings and their mappings."""

    scenario: Any
    package: dict[str, Any]
    roots: dict[str, dict[str, Any]]
    literals: dict[str, dict[str, Any]]
    vss_metadata: dict[str, Any]
    frame_def: dict[str, Any]
    frame_out: dict[str, Any]
    process_def: dict[str, Any]
    logical_def: dict[str, Any]
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

    def port(self, element: dict[str, Any], name: str) -> dict[str, Any]:
        return self.builder.feature_of(element, name)


def _port_definition(b, package, name: str, direction: str, item_type: dict[str, Any]) -> dict[str, Any]:
    """``port def <name> { <direction> item payload : <item_type>; }``."""
    port_def = b.definition("PortDefinition", name, package)
    b.usage("ItemUsage", "payload", port_def, [item_type], membership="FeatureMembership", direction=direction)
    return port_def


def _record(b, mapping: dict[str, Any], record_def: dict[str, Any], literal: dict[str, Any] | None, short: str,
            **texts: str) -> dict[str, Any]:
    """``item <'MAP-…'> <name> : LogicalToSoftwareSignalMappingRecord { disposition, owner, nextAction, … }``."""
    record = b.usage("ItemUsage", short.lower().replace("-", ""), mapping, [record_def], short=short,
                     membership="FeatureMembership", isComposite=True)
    if literal is not None:
        b.attribute(record, "disposition", literal)
    for member, text in {"owner": "DE4SDV maintainers", "nextAction": "phase 10: test it", **texts}.items():
        if text:
            b.attribute(record, member, text)
    return record


def _vss_signal(b, signals: dict[str, Any], metadata_def: dict[str, Any], name: str, path: str) -> dict[str, Any]:
    """A VSS signal as the serializer gives COVESA_VSS's: an attribute definition, and a package-level
    ``@VssSignalMetadata about <name> { path = "<path>"; }`` typed by the metadata definition, which owns
    an Annotation of the signal."""
    signal = b.definition("AttributeDefinition", name, signals)
    metadata = b.usage("MetadataUsage", None, signals, [metadata_def])
    b.relationship("Annotation", metadata, annotatedElement=ref(signal))
    b.attribute(metadata, "path", path)
    return signal


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
    covesa = b.package("COVESA_VSS", source=VSS_FILE)
    vss_metadata = b.definition("MetadataDefinition", "VssSignalMetadata",
                                b.package("MetadataDefinitions", covesa, source=VSS_FILE))
    vehicle_speed = _vss_signal(b, b.package("SignalDefinitions", covesa, source=VSS_FILE), vss_metadata,
                                "Vehicle_Speed", "Vehicle.Speed")
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
    realization = Realization(scenario, package, roots, literals, vss_metadata, frame_def, frame_out, process_def,
                              logical_def, relay, translator, lifecycle, host, guest, speed, launcher, frame_mapping,
                              frame_record, speed_mapping, speed_record)
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
            C(CROSSING, RECORDED, "physicalElements", advisory=True),
            C(SOURCE, NAMED, "signalMappings", advisory=True))),
    ], charter=r.scenario.charter)


def _view(r: Realization, *, library: bool = True) -> ModelView:
    """The view an export's loader gives: the kernel bindings, and the library pins bound by the file-mapped
    rule (none, as over the API, when ``library`` is false)."""
    b = r.builder
    bound, unbound = resolve_library_pins(LIBRARY_PINS, b.elements, b.sources) if library else ({}, {})
    return ModelView(b.elements, _traversal(b), sources=b.sources, library_bindings=bound, library_problems=unbound)


def _evaluate(r: Realization, revision: me.RevisionIdentity = REVISION, *, library: bool = True):
    return evaluate_increment(_view(r, library=library), r.scenario.increment_id, revision=revision)


def _results(evaluation, gate: str) -> dict[str, me.EvaluationResult]:
    return {r.subject_id: r for r in evaluation.canonical.results if r.unit_id == gate and r.subject_id}


def _verdicts(evaluation, gate: str) -> dict[str, str]:
    return {subject: result.verdict for subject, result in _results(evaluation, gate).items()}


def _note(evaluation, gate: str) -> dict[str, Any] | None:
    return next((note for note in evaluation.gaps()["advisory"] if note["gate"] == gate), None)


def _remedy(evaluation, check: str, subject: str) -> dict[str, Any]:
    """The remedy of one failing subject, as an answer record (the gate's own is its first subject's)."""
    remedy = check_remedy(evaluation.view, check, subject=subject, scope=evaluation.scope)
    return {"what_to_author": remedy.text, "authoring": remedy.authoring(), "subjects": [{"element_id": subject}]}


def _map(r: Realization, name: str, source, target, owner=None) -> dict[str, Any]:
    return r.builder.allocation(name, owner or r.package, source, target,
                                typed_by=r.roots["SystemToSoftwareSignalMappingCandidate"])


def _complete_record(r: Realization, mapping: dict[str, Any], short: str, literal: str = "candidate",
                     **texts: str) -> dict[str, Any]:
    return _record(r.builder, mapping, r.roots["LogicalToSoftwareSignalMappingRecord"], r.literals[literal], short,
                   **texts)


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
    assert _results(evaluation, CROSSING)[r.launcher["@id"]].diagnostics[-1] == (
        f"{_view(r).label(r.launcher['@id'])} declares no port with a directed feature: no crossing")
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
        f"through 1 port(s), but the increment owns no SystemToSoftwareSignalMappingCandidate from "
        f"{view.label(r.translator['@id'])} to a physical element of the increment that realizes it whose mapping "
        "records each state a disposition, an owner and a next action")
    (line,) = note["authoring"]["declarations"]
    assert line.startswith("allocation <name> : ")
    # The speed process owns its port: the target is the port's qualified name.
    assert f" allocate {view.label(r.translator['@id'])} to {view.label(r.speed['@id'])}::speedIn {{ item <'MAP-<ID>'> " \
           "<record> : " in line
    assert "attribute :>> disposition = " in line and line.endswith(
        'attribute :>> owner = "<owner>"; attribute :>> nextAction = "<next action>"; } }')
    assert _exits(evaluation)[P8] == "READY"  # advisory: never blocks


def test_a_record_without_owner_or_next_action_does_not_cover_its_crossing_and_gets_them_to_author() -> None:
    r = _realization()
    b = r.builder
    b.remove(b.feature_of(r.speed_record, "owner"), b.feature_of(r.speed_record, "nextAction"))
    evaluation = _evaluate(r)
    result = _results(evaluation, CROSSING)[r.speed["@id"]]
    view = _view(r)
    assert result.verdict == me.VERDICT_FAIL
    assert result.diagnostics[1] == f"{view.label(r.speed_record['@id'])} states no owner, nextAction"
    note = _note(evaluation, CROSSING)
    # The remedy completes the existing record instead of declaring a second mapping.
    assert note["authoring"]["declarations"] == [
        'attribute :>> owner = "<owner>";', 'attribute :>> nextAction = "<next action>";']
    assert f"in the existing {view.label(r.speed_record['@id'])}: attribute :>> owner" in note["what_to_author"]


def test_a_record_without_a_disposition_does_not_cover_its_crossing() -> None:
    """R14 (M3): the disposition is required."""
    r = _realization()
    b = r.builder
    b.remove(b.feature_of(r.speed_record, "disposition"))
    result = _results(_evaluate(r), CROSSING)[r.speed["@id"]]
    assert result.verdict == me.VERDICT_FAIL
    assert result.diagnostics[1] == f"{_view(r).label(r.speed_record['@id'])} states no disposition"


def test_a_disposition_literal_of_another_enumeration_is_no_disposition() -> None:
    """R14 (M7): only a literal of the kernel's SignalMappingDisposition counts, whatever its name."""
    r = _realization()
    b = r.builder
    foreign = b.definition("EnumerationDefinition", "FixtureOtherDisposition", r.package)
    candidate = b.new("EnumerationUsage", name="candidate", source=b.sources[foreign["@id"]])
    b.own(foreign, candidate, kind="VariantMembership", member_name="candidate")
    b.remove(b.feature_of(r.speed_record, "disposition"))
    b.attribute(r.speed_record, "disposition", candidate)
    result = _results(_evaluate(r), CROSSING)[r.speed["@id"]]
    assert result.verdict == me.VERDICT_FAIL
    assert result.diagnostics[1] == f"{_view(r).label(r.speed_record['@id'])} states no disposition"


def test_unfilled_placeholders_and_to_be_determined_markers_state_nothing() -> None:
    """R7: a value still holding the remedy's placeholder, or only TBD, does not state the member; any other
    text is stated and not judged."""
    r = _realization()
    b = r.builder
    b.remove(b.feature_of(r.speed_record, "owner"), b.feature_of(r.speed_record, "nextAction"))
    b.attribute(r.speed_record, "owner", "<owner>")
    b.attribute(r.speed_record, "nextAction", "TBD")
    result = _results(_evaluate(r), CROSSING)[r.speed["@id"]]
    assert result.verdict == me.VERDICT_FAIL
    assert result.diagnostics[1] == f"{_view(r).label(r.speed_record['@id'])} states no owner, nextAction"
    b.remove(b.feature_of(r.speed_record, "owner"), b.feature_of(r.speed_record, "nextAction"))
    b.attribute(r.speed_record, "owner", "the platform team")
    b.attribute(r.speed_record, "nextAction", "n/a")  # stated, not judged
    assert _verdicts(_evaluate(r), CROSSING)[r.speed["@id"]] == me.VERDICT_PASS


def test_every_record_of_a_mapping_must_be_complete_whatever_its_order() -> None:
    """R8: a mapping owning a complete and an incomplete record covers nothing, in either order."""
    for incomplete_first in (True, False):
        r = _realization()
        b = r.builder
        if incomplete_first:
            b.remove(b.feature_of(r.speed_record, "owner"))
            _complete_record(r, r.speed_mapping, "MAP-FIXTURE-SPEED-2")
            incomplete = r.speed_record
        else:
            incomplete = _complete_record(r, r.speed_mapping, "MAP-FIXTURE-SPEED-2", owner="")
        result = _results(_evaluate(r), CROSSING)[r.speed["@id"]]
        assert result.verdict == me.VERDICT_FAIL, incomplete_first
        assert result.diagnostics[1:] == (f"{_view(r).label(incomplete['@id'])} states no owner",), incomplete_first


def test_a_mapping_to_an_element_that_does_not_realize_the_logical_element_does_not_count() -> None:
    r = _realization()
    b = r.builder
    b.remove(r.frame_mapping)
    elsewhere = b.usage("PartUsage", "elsewhere", r.package)
    wrong = _map(r, "frameToElsewhere", r.relay, elsewhere)
    _complete_record(r, wrong, "MAP-FIXTURE-WRONG")
    evaluation = _evaluate(r)
    result = _results(evaluation, CROSSING)[r.host["@id"]]
    assert result.verdict == me.VERDICT_FAIL
    view = _view(r)
    assert result.diagnostics[1] == (
        f"{view.label(wrong['@id'])} is allocated to {view.label(elsewhere['@id'])}, in no physical element of the "
        f"increment that realizes {view.label(r.relay['@id'])}")


def test_a_mapping_from_another_logical_element_does_not_cover_the_crossing() -> None:
    """R14 (M6): the mapping's source end is the logical element the crossing realizes."""
    r = _realization()
    b = r.builder
    b.remove(r.frame_mapping)
    other = _map(r, "translatorToHostPort", r.translator, r.port(r.host, "frameOut"))
    _complete_record(r, other, "MAP-FIXTURE-OTHER")
    verdicts = _verdicts(_evaluate(r), CROSSING)
    assert (verdicts[r.host["@id"]], verdicts[r.guest["@id"]]) == (me.VERDICT_FAIL, me.VERDICT_FAIL)


def test_an_untyped_allocation_to_a_port_is_no_signal_mapping() -> None:
    r = _realization()
    b = r.builder
    b.remove(r.speed_mapping)
    b.allocation("untypedSpeedMapping", r.package, r.translator, r.port(r.speed, "speedIn"))
    assert _verdicts(_evaluate(r), CROSSING)[r.speed["@id"]] == me.VERDICT_FAIL


def test_only_a_mapping_the_increment_owns_covers_its_crossing() -> None:
    """R11: coverage reads the mappings the signalMappings parameter counts, those a package of the
    increment owns. One in another package, or nested in a definition, is noted and does not count."""
    r = _realization()
    b = r.builder
    b.remove(r.speed_mapping)
    elsewhere = b.package("FixtureOtherIncrementPackage")
    holder = b.definition("PartDefinition", "FixtureMappingHolder", r.package)
    for name, owner in (("foreignSpeedMapping", elsewhere), ("nestedSpeedMapping", holder)):
        _complete_record(r, _map(r, name, r.translator, r.port(r.speed, "speedIn"), owner), f"MAP-{name.upper()}")
    evaluation = _evaluate(r)
    result = _results(evaluation, CROSSING)[r.speed["@id"]]
    view = _view(r)
    assert result.verdict == me.VERDICT_FAIL
    assert sorted(result.diagnostics[1:]) == sorted(
        f"{view.label(m)} is owned by no package of the increment (or is nested in a definition), so it does "
        "not count for this increment" for m in (view.index.feature(elsewhere["@id"], "foreignSpeedMapping"),
                                                 view.index.feature(holder["@id"], "nestedSpeedMapping")))
    assert set(_results(evaluation, SOURCE)) == {r.frame_mapping["@id"]}  # the same population


def test_a_not_applicable_record_states_why() -> None:
    """R6: a notApplicable record covers its crossing only with a stated reason (evidenceOrGap)."""
    r = _realization()
    b = r.builder
    b.remove(b.feature_of(r.frame_record, "semanticSource"), b.feature_of(r.frame_record, "disposition"))
    b.attribute(r.frame_record, "disposition", r.literals["notApplicable"])
    evaluation = _evaluate(r)
    result = _results(evaluation, CROSSING)[r.host["@id"]]
    assert result.verdict == me.VERDICT_FAIL
    assert result.diagnostics[1] == f"{_view(r).label(r.frame_record['@id'])} states no evidenceOrGap"
    assert _note(evaluation, CROSSING)["authoring"]["declarations"] == [
        'attribute :>> evidenceOrGap = "<why no information item crosses a software contract>";']
    b.attribute(r.frame_record, "evidenceOrGap", "<why no information item crosses a software contract>")
    assert _verdicts(_evaluate(r), CROSSING)[r.host["@id"]] == me.VERDICT_FAIL  # the placeholder states nothing
    b.remove(b.feature_of(r.frame_record, "evidenceOrGap"))
    b.attribute(r.frame_record, "evidenceOrGap", "process control only; no information item crosses")
    evaluation = _evaluate(r)
    assert _verdicts(evaluation, CROSSING)[r.host["@id"]] == me.VERDICT_PASS
    assert _verdicts(evaluation, SOURCE)[r.frame_mapping["@id"]] == me.VERDICT_NOT_APPLICABLE


# -- which ports are information ports (R2) -------------------------------------


def _coordinator(r: Realization) -> tuple[dict[str, Any], dict[str, Any]]:
    """A coordinator process whose untyped port is a connector end of the speed process's typed input port
    (``connect coordinatorProcess.requestOut to speedProcess.speedIn;``, chained ends as the export writes
    them), realizing a request source."""
    b = r.builder
    source = b.usage("PartUsage", "requestSource", r.package, [r.logical_def])
    coordinator = b.usage("PartUsage", "coordinatorProcess", r.package, [r.process_def])
    request_out = b.usage("PortUsage", "requestOut", coordinator, [], membership="FeatureMembership")
    b.allocation("sourceToCoordinator", r.package, source, coordinator)
    connection = b.usage("ConnectionUsage", "requestFlow", r.package)
    for end_name, chain in (("source", [coordinator, request_out]), ("target", [r.speed, r.port(r.speed, "speedIn")])):
        end = b.new("Feature", name=end_name, declared=False, source=b.sources[r.package["@id"]])
        b.own(connection, end, kind="EndFeatureMembership", member_name=end_name)
        b.chain_end(end, chain)
    return source, coordinator


def test_an_untyped_port_connected_to_a_port_with_a_directed_feature_is_an_information_port() -> None:
    """R2 (a): the genuine coordinator shape, an untyped port whose connector peer has the directed item."""
    r = _realization()
    _source, coordinator = _coordinator(r)
    view = _view(r)
    assert [view.index.name_of(p) for p in information_ports(view, coordinator["@id"])] == ["requestOut"]
    assert _verdicts(_evaluate(r), CROSSING)[coordinator["@id"]] == me.VERDICT_FAIL


def test_a_conjugated_port_reads_its_original_definition() -> None:
    """R2 (b): ``port frameIn : ~FrameOut;`` receives the original's ``out item``, through the conjugated port
    definition the port definition owns (its PortConjugation, as the export holds every ``~P``)."""
    r = _realization()
    b = r.builder
    conjugated = b.new("ConjugatedPortDefinition", name="~FrameOut", declared=False,
                       source=b.sources[r.frame_out["@id"]])
    b.own(r.frame_out, conjugated, kind="OwningMembership")
    b.relationship("PortConjugation", conjugated, originalPortDefinition=ref(r.frame_out),
                   originalType=ref(r.frame_out), conjugatedType=ref(conjugated))
    b.remove(r.port(r.guest, "frameIn"))
    port = b.usage("PortUsage", "frameIn", r.guest, [], membership="FeatureMembership")
    b.relationship("ConjugatedPortTyping", port, type=ref(conjugated), conjugatedPortDefinition=ref(conjugated),
                   typedFeature=ref(port))
    view = _view(r)
    assert information_ports(view, r.guest["@id"]) == [port["@id"]]
    b.remove(r.frame_mapping)
    assert _verdicts(_evaluate(r), CROSSING)[r.guest["@id"]] == me.VERDICT_FAIL


def test_a_usage_that_only_redefines_another_reads_its_ports() -> None:
    """R2 (c): an untyped usage redefining a baseline usage has the baseline's ports."""
    r = _realization(workflow=False)
    b = r.builder
    baseline = b.definition("PartDefinition", "FixtureBaseline", r.package)
    baseline_host = b.usage("PartUsage", "baselineHost", baseline, [r.process_def], membership="FeatureMembership")
    baseline_port = b.usage("PortUsage", "frameOut", baseline_host, [r.frame_out], membership="FeatureMembership")
    reused = b.usage("PartUsage", "reusedHost", r.package)
    b.relationship("Redefinition", reused, redefinedFeature=ref(baseline_host), redefiningFeature=ref(reused))
    assert information_ports(_view(r), reused["@id"]) == [baseline_port["@id"]]


def test_a_port_that_cannot_be_read_leaves_the_crossing_indeterminate() -> None:
    """R2: a port with no type, no feature and no connected port is unreadable, not 'no crossing'; a
    definition outside the bound revision likewise."""
    r = _realization()
    b = r.builder
    b.usage("PortUsage", "controlPort", r.launcher, [], membership="FeatureMembership")
    result = _results(_evaluate(r), CROSSING)[r.launcher["@id"]]
    assert (result.verdict, result.missing) == (INDETERMINATE, ("model-witness:port",))
    assert "controlPort has no type, no feature and no connected port" in result.diagnostics[0]
    b.remove(b.feature_of(r.launcher, "controlPort"))
    dangling = b.usage("PortUsage", "remotePort", r.launcher, [], membership="FeatureMembership")
    b.relationship("FeatureTyping", dangling, type={"@id": "ffffffff-0000-5000-8000-000000000000"},
                   typedFeature=ref(dangling))
    result = _results(_evaluate(r), CROSSING)[r.launcher["@id"]]
    assert result.verdict == INDETERMINATE
    assert "remotePort is typed by an element that is not in the bound revision" in result.diagnostics[0]


def test_any_directed_feature_counts_and_a_non_information_flow_is_recorded_not_applicable() -> None:
    """R12: the check reads structure, never names, so a power port with a directed attribute is a crossing
    like any other; its record says notApplicable, and why."""
    r = _realization()
    b = r.builder
    power = b.definition("PortDefinition", "PowerIn", r.package)
    b.usage("AttributeUsage", "supplyVoltage", power, [], membership="FeatureMembership", direction="in")
    b.usage("PortUsage", "powerIn", r.launcher, [power], membership="FeatureMembership")
    assert _verdicts(_evaluate(r), CROSSING)[r.launcher["@id"]] == me.VERDICT_FAIL
    mapping = _map(r, "lifecycleSignalMapping", r.lifecycle, r.launcher)
    _complete_record(r, mapping, "MAP-FIXTURE-POWER", "notApplicable",
                     evidenceOrGap="supply power, no information item: it crosses no software contract")
    evaluation = _evaluate(r)
    assert _verdicts(evaluation, CROSSING)[r.launcher["@id"]] == me.VERDICT_PASS
    assert _verdicts(evaluation, SOURCE)[mapping["@id"]] == me.VERDICT_NOT_APPLICABLE


# -- a port the element inherits from its definition (R1) -------------------------


def _service(r: Realization) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """A telemetry service whose information port is its definition's (``part def FixtureServiceDef { port
    frameOut : FrameOut; }``), realizing a telemetry role."""
    b = r.builder
    role = b.usage("PartUsage", "telemetryRole", r.package, [r.logical_def])
    service_def = b.definition("PartDefinition", "FixtureServiceDef", r.package, [r.roots["PhysicalElement"]])
    port = b.usage("PortUsage", "frameOut", service_def, [r.frame_out], membership="FeatureMembership")
    service = b.usage("PartUsage", "telemetryService", r.package, [service_def])
    b.allocation("roleToService", r.package, role, service)
    return role, service, port


def test_the_remedy_names_an_inherited_port_through_the_element_and_following_it_clears_the_advisory() -> None:
    r = _realization()
    role, service, port = _service(r)
    evaluation = _evaluate(r)
    view = _view(r)
    assert _verdicts(evaluation, CROSSING)[service["@id"]] == me.VERDICT_FAIL
    (line,) = _remedy(evaluation, RECORDED, service["@id"])["authoring"]["declarations"]
    assert f" allocate {view.label(role['@id'])} to {view.label(service['@id'])}.frameOut {{ " in line
    # Authored as the remedy says, a chain through the element: covered.
    chained = _map(r, "telemetrySignalMapping", role, [service, port])
    _complete_record(r, chained, "MAP-FIXTURE-TELEMETRY", semanticSource="an opaque frame")
    assert _verdicts(_evaluate(r), CROSSING)[service["@id"]] == me.VERDICT_PASS
    # The definition's own port is every usage's: no coverage, and the note says where it points.
    r.builder.remove(chained)
    to_definition = _map(r, "telemetryToDefinitionPort", role, port)
    _complete_record(r, to_definition, "MAP-FIXTURE-DEFINITION")
    view = _view(r)
    result = _results(_evaluate(r), CROSSING)[service["@id"]]
    assert result.verdict == me.VERDICT_FAIL
    assert result.diagnostics[1] == (
        f"{view.label(to_definition['@id'])} is allocated to {view.label(port['@id'])}, in no physical element of "
        f"the increment that realizes {view.label(role['@id'])}")


# -- the semantic source -------------------------------------------------------


def test_a_vss_typed_item_names_its_semantic_source() -> None:
    r = _realization()
    view = _view(r)
    assert carried_vss_paths(view, view.index.feature(r.speed["@id"], "speedIn")) == ["Vehicle.Speed"]
    result = _results(_evaluate(r), SOURCE)[r.speed_mapping["@id"]]
    assert (result.verdict, result.diagnostics) == (me.VERDICT_PASS, ("VSS-typed: Vehicle.Speed",))


def test_vss_metadata_written_in_the_signal_s_body_annotates_its_owner() -> None:
    """R5: the serializer gives a metadata usage without ``about`` no Annotation (its annotated element is its
    owner), as it does for the model's other body metadata."""
    r = _realization()
    b = r.builder
    signal = b.definition("AttributeDefinition", "Vehicle_ADAS_Flag", b.package("FixtureExtensions", source=VSS_FILE))
    metadata = b.usage("MetadataUsage", None, signal, [r.vss_metadata])
    b.attribute(metadata, "path", "Vehicle.ADAS.Flag")
    b.usage("AttributeUsage", "flag", r.frame_def, [signal], membership="FeatureMembership")
    view = _view(r)
    assert view.index.owner_of(metadata["@id"]) == signal["@id"]
    assert not view.index.owned_relationships(metadata["@id"], "Annotation")
    assert carried_vss_paths(view, r.port(r.host, "frameOut")["@id"]) == ["Vehicle.ADAS.Flag"]


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
    # Pasted unchanged, or replaced by TBD, the line states nothing (R7).
    for value in ("<what the item is, and why it is no VSS signal>", "TBD"):
        b.attribute(r.frame_record, "semanticSource", value)
        assert _verdicts(_evaluate(r), SOURCE)[r.frame_mapping["@id"]] == me.VERDICT_FAIL, value
        b.remove(b.feature_of(r.frame_record, "semanticSource"))


def test_every_record_of_a_mapping_states_its_semantic_source() -> None:
    """R8: a second record without a source is reported, whatever the first states."""
    r = _realization()
    second = _complete_record(r, r.frame_mapping, "MAP-FIXTURE-FRAME-2")
    result = _results(_evaluate(r), SOURCE)[r.frame_mapping["@id"]]
    assert result.verdict == me.VERDICT_FAIL
    assert result.diagnostics[0].endswith(f"and {_view(r).label(second['@id'])} states no semantic source")


def test_a_vss_path_in_a_string_is_no_vss_typing() -> None:
    """A record whose contract fields name the VSS path in text, over an untyped payload, names no source."""
    r = _realization()
    b = r.builder
    b.remove(b.feature_of(r.frame_record, "semanticSource"))
    b.attribute(r.frame_record, "dataTypeAndUnit", "VSS Vehicle.Speed, km/h")
    assert _verdicts(_evaluate(r), SOURCE)[r.frame_mapping["@id"]] == me.VERDICT_FAIL


def test_only_the_bound_vss_signal_metadata_types_a_signal() -> None:
    """R3: other metadata with a ``path`` feature is no VSS typing."""
    r = _realization()
    b = r.builder
    b.remove(b.feature_of(r.frame_record, "semanticSource"))
    other = b.definition("MetadataDefinition", "SourceFileReference", r.package)
    metadata = b.usage("MetadataUsage", None, r.package, [other])
    b.relationship("Annotation", metadata, annotatedElement=ref(r.frame_def))
    b.attribute(metadata, "path", "contracts/frame.proto")
    assert carried_vss_paths(_view(r), r.port(r.host, "frameOut")["@id"]) == []
    assert _verdicts(_evaluate(r), SOURCE)[r.frame_mapping["@id"]] == me.VERDICT_FAIL


def test_vss_typing_is_read_at_a_port_never_at_an_element() -> None:
    """R3: a mapping to the speed process element does not take the VSS typing of the speed port the element
    has; its record states the source instead."""
    r = _realization()
    b = r.builder
    b.remove(r.speed_mapping)
    to_element = _map(r, "speedToElement", r.translator, r.speed)
    record = _complete_record(r, to_element, "MAP-FIXTURE-ELEMENT")
    evaluation = _evaluate(r)
    view = _view(r)
    result = _results(evaluation, SOURCE)[to_element["@id"]]
    assert result.verdict == me.VERDICT_FAIL
    assert result.diagnostics[0] == (
        f"{view.label(to_element['@id'])} is allocated to the element {view.label(r.speed['@id'])}: VSS typing is "
        f"read only at a port, or an item or attribute in one, and {view.label(record['@id'])} states no semantic "
        "source")
    assert "VSS typing is read only at a port" in _note(evaluation, SOURCE)["what_to_author"]
    assert _verdicts(evaluation, CROSSING)[r.speed["@id"]] == me.VERDICT_PASS  # an element target covers it


def test_the_vss_signal_metadata_is_bound_by_the_file_mapped_rule() -> None:
    """R3: the pin resolves by metatype, declared name and source document (ADR 0011). Unbound, as over the
    API, a mapping that needs VSS typing is method side, and a stated source still names its item; with the
    name in another document the pin does not bind."""
    r = _realization()
    evaluation = _evaluate(r, library=False)
    result = _results(evaluation, SOURCE)[r.speed_mapping["@id"]]
    assert (result.verdict, result.missing) == (INDETERMINATE, (f"library-binding:{VSS_SIGNAL_METADATA}",))
    assert _verdicts(evaluation, SOURCE)[r.frame_mapping["@id"]] == me.VERDICT_PASS
    r.builder.sources[r.vss_metadata["@id"]] = "textual-notation-of-model/libraries/elsewhere.sysml"
    bound, unbound = resolve_library_pins(LIBRARY_PINS, r.builder.elements, r.builder.sources)
    assert bound == {} and "1 name/type matches had different provenance" in unbound[VSS_SIGNAL_METADATA]
    result = _results(_evaluate(r), SOURCE)[r.speed_mapping["@id"]]
    assert result.verdict == INDETERMINATE
    assert "had different provenance" in result.diagnostics[0]


def test_an_ambiguous_vss_signal_metadata_pin_binds_nothing() -> None:
    """R3: two declarations the rule matches leave the pin unbound, as an ambiguous kernel binding blocks."""
    r = _realization()
    b = r.builder
    b.definition("MetadataDefinition", "VssSignalMetadata", b.package("FixtureVssCopy", source=VSS_FILE))
    bound, unbound = resolve_library_pins(LIBRARY_PINS, b.elements, b.sources)
    assert bound == {} and "resolved to 2 MetadataDefinition elements" in unbound[VSS_SIGNAL_METADATA]
    assert _verdicts(_evaluate(r), SOURCE)[r.speed_mapping["@id"]] is INDETERMINATE


def test_a_mapping_without_a_record_gets_its_record_to_author() -> None:
    r = _realization()
    b = r.builder
    b.remove(r.frame_record)
    evaluation = _evaluate(r)
    assert _verdicts(evaluation, CROSSING)[r.host["@id"]] == me.VERDICT_FAIL
    view = _view(r)
    for gate in (SOURCE, CROSSING):
        note = _note(evaluation, gate)
        (line,) = note["authoring"]["declarations"]
        assert line.startswith("item <'MAP-<ID>'> <record> : "), gate
        assert f"in the existing {view.label(r.frame_mapping['@id'])}: {line}" in note["what_to_author"], gate


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
    for check, member in ((RECORDED, 'attribute :>> owner = "<owner>";'),
                          (NAMED, 'attribute :>> semanticSource = "<what the item is, and why it is '
                                  'no VSS signal>";')):
        (line,) = check_remedy(view, check).declarations
        assert line.startswith("allocation <name> : ") and " allocate <logical element> to <port> " in line, check
        assert member in line, check


def test_every_signal_mapping_remedy_is_authorable_sysml() -> None:
    """The remedies of both checks, for a crossing without a mapping (with its own port, and with an inherited
    one, a chain), a record without its owner or its reason, a mapping without a record, a record without its
    semantic source, a mapping to an element, and without a subject (the phase contract): accepted forms
    only, with the qualified names and chains they name resolving and the types imported (the oracle of
    test_remedies)."""
    r = _realization()
    b = r.builder
    b.remove(b.feature_of(r.frame_record, "semanticSource"), b.feature_of(r.speed_record, "owner"))
    _role, service, _port = _service(r)
    unrecorded = b.allocation("unrecordedMapping", r.package, r.lifecycle, r.launcher,
                              typed_by=r.roots["SystemToSoftwareSignalMappingCandidate"])
    evaluation = _evaluate(r)
    names = QualifiedNameIndex(b.elements)
    records = [record for answer in (evaluation.gaps(), evaluation.phase_contract()) for record in _remedied(answer)
               if (record.get("gate") or record.get("obligation_id")) in (CROSSING, SOURCE)]
    assert {record.get("gate") or record.get("obligation_id") for record in records} == {CROSSING, SOURCE}
    records += [_remedy(evaluation, RECORDED, subject) for subject in (service["@id"], r.speed["@id"])]
    records += [_remedy(evaluation, NAMED, subject) for subject in (r.frame_mapping["@id"], unrecorded["@id"])]
    lines = [line for record in records for line in record["authoring"]["declarations"]]
    assert any(".frameOut { item <'MAP-<ID>'>" in line for line in lines)  # the chain through the element
    assert 'attribute :>> owner = "<owner>";' in lines  # the existing record completed
    assert [_problems(record, names) for record in records] == [[] for _record in records]
