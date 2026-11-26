"""Content pins for the E/E architecture operational context (INC-EE-001 phase 2), not semantic validation."""

from pathlib import Path
import re

from sysml_shapes import braced_body, strip_comments

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs/guides/ee-architecture-increment.md"
EE = ROOT / "textual-notation-of-model/packages/features/ee"
FRAMING = EE / "ee_architecture_framing.sysml"
MODEL = EE / "ee_architecture_operational_context.sysml"
PACKAGE = "DE4SDV_EEArchitectureOperationalContext"
FRAMING_PACKAGE = "DE4SDV_EEArchitectureFraming"
DA_PACKAGE = "DE4SDV_DriverAssistanceOperationalContext"
CONTEXT = "eeArchitectureOperationalContext"
SOI = "vehicleNetwork"
SOI_TYPE = "EEVehicleNetworkSystem"

#: Context parts around the system of interest and their kernel, reused or new operational types. Phase 0 draws
#: the boundary: the command source and the Eclipse S-CORE path are System 1 parts outside the vehicle network,
#: and the vehicle only takes the applied command.
CONTEXT_PARTS = {
    "commandSource": "DrivingCommandSource",
    "scorePath": "SCORECommandAndWarningPath",
    "vehicle": "SubjectVehicle",
}

#: The story: one use case per scenario, with its identity and the phrase that names its route or fault.
STORY = "vehicleNetworkStory"
USE_CASE_DEF = "CarryDrivingCommandToActuation"
SCENARIOS = {
    "carryCommandThroughZoneController": ("SC-EE-001", "crosses the Ethernet backbone and a zone controller"),
    "carryCommandOverDirectLink": ("SC-EE-002", "over the direct link from the central computer"),
    "rejectFaultyCommandOnTheRoute": ("SC-EE-003", "is lost, delayed, repeated or corrupted on its way"),
    "respondToLinkDownOnTheRoute": ("SC-EE-004", "one link of the route goes down"),
}

#: The operation: every action with its parameters, in order, and every flow between them.
OPERATION = "VehicleNetworkCommandOperation"
ACTIONS = {
    "giveDrivingCommand": [("out", "drivingCommand", "DrivingCommand")],
    "carryCommandOverSCORE": [("in", "drivingCommand", "DrivingCommand"), ("out", "carriedCommand", "DrivingCommand")],
    "carryAndApplyCommand": [("in", "drivingCommand", "DrivingCommand"), ("out", "appliedCommand", "DrivingCommand")],
    "moveVehicle": [("in", "appliedCommand", "DrivingCommand")],
}
FLOWS = [
    ("giveDrivingCommand", "drivingCommand", "carryCommandOverSCORE", "drivingCommand"),
    ("carryCommandOverSCORE", "carriedCommand", "carryAndApplyCommand", "drivingCommand"),
    ("carryAndApplyCommand", "appliedCommand", "moveVehicle", "appliedCommand"),
]

#: A field, a rate or a number of the driving command: phase 5 and phase 8 material, not phase 2's.
FORM = re.compile(r"(?i)\b(?:issue[ -]?times?|sequence[ -]?counts?|sequence[ -]?numbers?|check[ -]?values?|"
                  r"checksums?|counters?|counting|cadences?|periods?|periodic|rates?|hz|cycle times?|"
                  r"steps? sizes?|delay limits?)\b|\d")
#: identities, phase and system numbers and view depths, which are no number of the command
IDENTITY = re.compile(r"\b(?:SC|INC|REQ)-[A-Z]+-\d{3}\b|\b[Pp]hases? \d+(?: (?:to|and) \d+)?\b|\bSystem [12]\b|\battribute depth = [12];|DE4SDV")
#: The phase-0 sentence whose word "form" the model may cite, by its record's name.
BASELINE_RECORD = "asmEECommandFromDrivingBaseline"
#: the non-claim that may follow the cited sentence: the baseline states no cadence
NO_CADENCE = "that baseline states no cadence of the command as such."


def _raw() -> str:
    assert MODEL.is_file(), "phase 2 of INC-EE-001 needs an operational context model"
    return MODEL.read_text(encoding="utf-8")


def _code() -> str:
    return strip_comments(_raw())


def _top(body: str) -> str:
    """The text of a body at its own depth: the contents of nested blocks are dropped, whatever the indentation."""
    kept, depth = [], 0
    for char in body:
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        elif depth == 0:
            kept.append(char)
    return "".join(kept)


def _package() -> str:
    return _top(braced_body(_code(), f"package {PACKAGE}"))


def _flat(text: str) -> str:
    return " ".join(text.split())


def _doc(raw: str, declaration: str) -> str:
    body = braced_body(raw, declaration)
    match = re.search(r"\bdoc\s*/\*(.*?)\*/", body, re.S)
    assert match, f"{declaration} has a doc"
    return _flat(re.sub(r"(?m)^\s*\*\s?", "", match.group(1)))


def _guide_section() -> str:
    section = re.search(r"(?ms)^## Operational context and story \(Phase 2\)\n(.*?)(?=^## )",
                        GUIDE.read_text(encoding="utf-8"))
    assert section, "the guide has a Phase 2 section"
    return _flat(section.group(1))


def test_the_increment_has_exactly_one_operational_context_named_in_the_charter():
    code = _code()
    framing = strip_comments(FRAMING.read_text(encoding="utf-8"))
    assert re.search(rf"\bpackage\s+{PACKAGE}\s*\{{", code)
    contexts = re.findall(r"\bpart\s+(\w+)\s*:\s*SystemContext\b", code)
    contexts += re.findall(r"\bpart\s+(\w+)\s*:\s*SystemContext\b", framing)
    assert contexts == [CONTEXT]
    charter = braced_body(framing, "part eeArchitectureCharter : IncrementCharter")
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", charter, re.S)
    # the framing test pins the whole list; later phases append their packages after this one
    assert artifacts and re.findall(r'"([^"]+)"', artifacts.group(1))[:2] == [FRAMING_PACKAGE, PACKAGE]


def test_the_system_of_interest_is_the_charter_network_as_a_black_box():
    code = _code()
    framing = strip_comments(FRAMING.read_text(encoding="utf-8"))
    charter = braced_body(framing, "part eeArchitectureCharter : IncrementCharter")
    soi_usage = re.search(r"systemOfInterest\s*=\s*(\w+)\s*;", charter).group(1)
    assert re.search(rf"\bpart\s+{soi_usage}\s*:\s*{SOI_TYPE}\s*;", framing), "the charter's system is the network"
    context = braced_body(code, f"part {CONTEXT} : SystemContext")
    assert re.search(rf"\bpart\s+{SOI}\s*:\s*{SOI_TYPE}\s*:>>\s*systemOfInterest\s*;", context)
    assert not re.search(rf"\bpart\s+{SOI}\s*:[^;{{]*\{{", context), "the system of interest declares no parts here"
    parts = dict(re.findall(r"\bpart\s+(\w+)\s*:\s*(\w+)", _top(context)))
    assert parts == {SOI: SOI_TYPE, **CONTEXT_PARTS}


def test_the_boundary_drawn_in_phase_zero_holds():
    raw = _raw()
    code = _code()
    context = braced_body(code, f"part {CONTEXT} : SystemContext")
    assert dict(re.findall(r"\bpart\s+(\w+)\s*:\s*(\w+)", _top(context))).items() >= CONTEXT_PARTS.items(), \
        "the parts around the system of interest stand at the context's top level with their types"
    for name, type_name in re.findall(r"\bpart\s+(\w+)\s*:\s*(\w+)", context):
        if name == SOI:
            continue
        assert not re.search(r"(?i)ecu|zone|backbone|\bcan\b|directlink|centralcomputer|gateway|actuat",
                             f"{name} {type_name}"), f"{name}: an element of the network is drawn in the context"
    doc = _doc(raw, f"part {CONTEXT} : SystemContext")
    for phrase in ("Inside the system of interest, as phase 0 draws it: the network side of the central computer",
                   "and the actuation ECU on CAN that receives the command and acts on it",
                   "The source of the driving command on the central computer and the Eclipse S-CORE path are "
                   "System 1 parts outside the vehicle network",
                   "the vehicle only takes the command that the actuation ECU applies"):
        assert phrase in doc, phrase
    for name in ("SCORECommandAndWarningPath", "DrivingCommand"):
        assert f"private import {DA_PACKAGE}::{name};" in code, f"{name} is imported singly"
        assert not re.search(rf"\b(?:part|item)\s+def\s+{name}\b", code), f"reuse {name}, never redeclare it"
    assert not re.search(rf"\bprivate\s+import\s+{DA_PACKAGE}::\*", code), "only the two names of DA phase 2"
    assert re.findall(r"\b(?:part|item|action|use case)\s+def\s+(\w+)", code) == [
        "DrivingCommandSource", OPERATION, USE_CASE_DEF], "one new role, the operation and the use case definition"
    assert re.search(r"\bpart\s+def\s+DrivingCommandSource\s*:>\s*OperationalEntity\s*\{", code)
    assert not re.search(r"\bconcern def\b", code)


def test_the_command_source_names_its_increment_and_the_score_path_is_narrowed():
    raw = _raw()
    source = _doc(raw, "part def DrivingCommandSource :> OperationalEntity")
    for phrase in ("the driver-assistance candidate of INC-DRIVING-002 gives the driving command",
                   f"({BASELINE_RECORD})", "eeVerificationEnvironment"):
        assert phrase in source, phrase
    score = _doc(raw, "part scorePath : SCORECommandAndWarningPath")
    for phrase in ("hands the driving command to the network side of the central computer (asmEEScoreCommandSource)",
                   "the scope holds one flow, so it carries no warning request in this increment"):
        assert phrase in score, phrase
    assert "takes the command that the actuation ECU applies and sends nothing back" in \
        _doc(raw, "part vehicle : SubjectVehicle")


def test_context_and_story_hold_system_one_roles_only():
    raw = _raw()
    code = _code()
    context = braced_body(code, f"part {CONTEXT} : SystemContext")
    forbidden = (r"\b(?:System2\w*|DE4SDVEvidenceBaseline|OpenSourceReviewer|VerificationEngineer|\w*Testbed\w*"
                 r"|\w*Replay\w*|\w*Injection\w*|\w*Injector\w*|\w*VehicleModel\w*|\w*Recorder\w*|\w*Recording\w*"
                 r"|\w*Evaluator\w*|\w*Host\w*|eeVerificationEnvironment)\b")
    assert not re.search(forbidden, context), "testbed, replay, injection and evaluator roles belong to System 2"
    for name in (STORY, *SCENARIOS):
        assert not re.search(forbidden, braced_body(code, f"use case {name}")), name
        assert not re.search(r"(?i)\b(?:replay|testbed|recording|recorded|injection|injected)\b",
                             braced_body(raw, f"use case {name}")), f"{name}: no System 2 term in the scenario"
    assert not re.search(
        r"\b(?:part|item|concern|use case) def (?:SubjectVehicle|SystemContext|OperationalEntity|EEVehicleNetworkSystem"
        r"|DriverAssistanceSystem)\b", code), "kernel and framing names are used, never shadowed"
    assert "eeVerificationEnvironment" in _doc(raw, f"part {CONTEXT} : SystemContext"), \
        "the context doc says where System 2 stays"


def test_every_use_case_binds_its_subject_and_actors_to_the_context():
    code = _code()
    #: the context's top-level parts, name -> type, read from the model: a bound part must exist there with its type
    context_parts = dict(re.findall(r"\bpart\s+(\w+)\s*:\s*(\w+)",
                                    _top(braced_body(code, f"part {CONTEXT} : SystemContext"))))
    usages = re.findall(r"\buse case\s+(?!def\b)(\w+)", _package())
    assert sorted(usages) == sorted([STORY, *SCENARIOS])
    for name in usages:
        body = braced_body(code, f"use case {name}")
        assert re.search(rf"\bsubject\s+{SOI}\s*:\s*{SOI_TYPE}\s*=\s*{CONTEXT}::{SOI}\s*;", body), \
            f"{name}: the subject is the context's system of interest"
        declared = re.findall(r"\bactor\s+(\w+)\s*:", body)
        actors = re.findall(rf"\bactor\s+(\w+)\s*:\s*(\w+)\s*=\s*{CONTEXT}::(\w+)\s*;", body)
        assert len(actors) == len(declared), f"{name}: every actor is bound to a context part"
        assert {(a, t, p) for a, t, p in actors} == {(p, t, p) for p, t in CONTEXT_PARTS.items()}, \
            f"{name}: the command source, the S-CORE path and the vehicle, each bound to its context part"
        assert context_parts.get(SOI) == SOI_TYPE, f"{name}: the subject is bound to a top-level context part"
        for actor, type_name, part in actors:
            assert context_parts.get(part) == type_name, \
                f"{name}: actor {actor} is bound to a top-level context part of its own type"
    assert f"use case def {USE_CASE_DEF} :> SYSMODSystemUseCaseBase" in code
    use_case_def = braced_body(code, f"use case def {USE_CASE_DEF} :> SYSMODSystemUseCaseBase")
    for slot in ("ucMotivation", "ucTrigger", "ucResult"):
        assert re.search(rf"\battribute\s+redefines\s+{slot}\s*=\s*\"[^\"]+\"\s*;", use_case_def), slot
    assert re.search(rf"\buse case\s+{STORY}\s*:\s*{USE_CASE_DEF}\s*\{{", code)


def test_the_story_holds_the_four_scenarios():
    raw = _raw()
    code = _code()
    story = braced_body(code, f"use case {STORY} : {USE_CASE_DEF}")
    assert re.findall(r"\binclude\s+(\w+)\s*;", story) == list(SCENARIOS)
    assert re.search(r"\bfirst\s+start\s*;", story) and re.search(r"\bthen\s+done\s*;", story)
    for name, (scenario_id, phrase) in SCENARIOS.items():
        doc = _doc(raw, f"use case {name}")
        assert doc.startswith(scenario_id + " "), f"{name} carries {scenario_id}"
        assert phrase in doc, f"{name}: its route or fault"
        assert doc.endswith("No timing claim for a vehicle network is made."), f"{name}: the nonclaim"
    objective = _flat(re.sub(r"(?m)^\s*\*\s?", "", braced_body(
        raw, f"use case def {USE_CASE_DEF} :> SYSMODSystemUseCaseBase").split("objective", 1)[1]))
    assert ("a time limit counts on the clock of the virtual vehicle and makes no timing claim for a vehicle "
            "network.") in objective, "the use case definition's objective keeps its nonclaim"
    direct = _doc(raw, "use case carryCommandOverDirectLink")
    assert "which passes no zone controller" in direct
    assert not re.search(r"(?i)\b(?:ethernet|can)\s+link\b|\bmedium\b", direct), "the medium of the link is open"
    fault = _doc(raw, "use case rejectFaultyCommandOnTheRoute")
    assert "on either route" in fault and "applies no command that it rejects" in fault
    stop = _doc(raw, "use case respondToLinkDownOnTheRoute")
    for phrase in ("on either route", "the vehicle gets the stop response that the engineering question names",
                   "REQ-DRIVING-028 of INC-DRIVING-001, not from the driver-assistance increment, whose adapter "
                   "has no stop response (gapEEActuationEnd).",
                   "the response and its time limit are fixed with the requirements (phase 5)"):
        assert phrase in stop, phrase
    ids = re.findall(r"SC-[A-Z]+-\d{3}", raw)
    assert sorted(set(ids)) == sorted(s[0] for s in SCENARIOS.values()), "only the four new scenario identities"


def test_the_boundary_flows_cross_in_the_drawn_directions():
    raw = _raw()
    code = _code()
    operation = braced_body(code, f"action def {OPERATION}")
    flows = re.findall(r"\bflow\s+from\s+(\w+)\.(\w+)\s+to\s+(\w+)\.(\w+)\s*;", operation)
    assert {(s, i) for s, i, t, _ in flows if t == "carryAndApplyCommand"} == {("carryCommandOverSCORE",
                                                                              "carriedCommand")}
    assert {(i, t) for s, i, t, _ in flows if s == "carryAndApplyCommand"} == {("appliedCommand", "moveVehicle")}
    assert not [f for f in flows if f[0] == "moveVehicle"], "the vehicle only receives"
    assert sorted(flows) == sorted(FLOWS), "exactly the flows of the drawn boundary"
    assert re.findall(r"\baction\s+(\w+)\s*\{", operation) == list(ACTIONS)
    for action, parameters in ACTIONS.items():
        assert re.findall(r"\b(in|out)\s+(\w+)\s*:\s*(\w+)\s*;", braced_body(operation, f"action {action}")) == \
            parameters, action
    assert re.search(rf"\baction\s+vehicleNetworkCommandOperation\s*:\s*{OPERATION}\s*;", code)
    assert "the stop response reaches the vehicle on the same flow" in \
        _doc(braced_body(raw, f"action def {OPERATION}"), "action carryAndApplyCommand")


def test_phase_two_names_no_form_or_cadence_of_the_driving_command():
    raw = _raw()
    code = _code()
    texts = {MODEL.name: raw, "the guide's Phase 2 section": _guide_section()}
    for name, text in texts.items():
        sentences = re.split(r"(?<=[.;:])\s+", _flat(text.replace("*", " ")))
        for index, sentence in enumerate(sentences):
            bare = re.sub(IDENTITY, "", sentence)
            if sentence == NO_CADENCE and index and BASELINE_RECORD in sentences[index - 1]:
                # the non-claim right after the cited sentence names no cadence of its own
                continue
            if BASELINE_RECORD in sentence:
                # the cited sentence may use the word "form" of the record; strip only that word
                cited = re.sub(r"(?i)\bform\b", "", bare)
                assert not FORM.search(cited), f"{name}: the cited baseline sentence names no field or number: {sentence}"
                continue
            assert not FORM.search(bare), f"{name} names a form, a rate or a number of the command: {sentence}"
    assert not re.search(r"\bDE4SDV_DriverAssistance(?:NeedsRequirements|FunctionalArchitecture|LogicalArchitecture"
                         r"|PhysicalSoftwareRealization|VerificationEvidence)\b", code), \
        "phase 2 reads no later phase of INC-DRIVING-002"
    flat = texts["the guide's Phase 2 section"]
    assert ("It imports two names of the operational context of the driver-assistance increment, "
            "`DrivingCommand` and `SCORECommandAndWarningPath`: names, not the form of the command.") in flat


def test_operational_views_frame_operational_concerns_and_expose_phase_two():
    raw = _raw()
    code = _code()
    framing = strip_comments(FRAMING.read_text(encoding="utf-8"))
    expected = {
        "eeArchitectureOperationalContextView": (
            "OperationalContextDefinitionViewpoint", ["eeArchitectureContextConcern"],
            "OperationalContextConcern", {CONTEXT, f"{CONTEXT}::*", "vehicleNetworkCommandOperation"}, "2"),
        "eeArchitectureOperationalStoryView": (
            "OperationalStoryViewpoint", ["eeArchitectureStoryConcern", "eeVehicleCommandConcern"],
            "OperationalStoryConcern", {STORY, f"{STORY}::*"}, "1"),
    }
    assert re.findall(r"\bview\s+(\w+)", _package()) == list(expected)
    assert re.search(r"\bconcern\s+eeVehicleCommandConcern\s*:\s*OperationalCapabilityConcern\b", framing), \
        "the story view's second frame is phase 1's operational concern"
    assert "Answered by the operational story of phase 2." in _doc(
        FRAMING.read_text(encoding="utf-8"), "concern eeVehicleCommandConcern : OperationalCapabilityConcern")
    for view_name, (viewpoint, frames, concern_type, exposed, depth) in expected.items():
        view = braced_body(code, f"view {view_name}")
        assert re.search(rf"\bviewpoint\s+\w+\s*:\s*{viewpoint}\s*\{{", view), view_name
        assert re.findall(r"\bframe\s+([\w:]+)\s*;", view) == frames, view_name
        assert set(re.findall(r"\bexpose\s+([\w:*]+)\s*;", view)) == exposed, view_name
        assert re.search(rf"\battribute\s+depth\s*=\s*{depth}\s*;", view), view_name
        assert re.search(r"\battribute\s+showAnnotationRows\s*=\s*false\s*;", view), view_name
        assert re.search(r"\brender\s+asTreeDiagram\s*;", view), view_name
        concern_body = braced_body(code, f"concern {frames[0]} : {concern_type}")
        lines = [line.strip() for line in concern_body.splitlines() if line.strip() and line.strip() != "doc"]
        assert lines[0] == "subject;", frames[0]
    holders = {
        "eeArchitectureContextConcern": [("systemArchitect", "SystemArchitect"), ("systemsEngineer", "SystemsEngineer"),
                                         ("reviewer", "OpenSourceReviewer")],
        "eeArchitectureStoryConcern": [("systemsEngineer", "SystemsEngineer"),
                                       ("verificationEngineer", "VerificationEngineer"),
                                       ("reviewer", "OpenSourceReviewer")],
    }
    concern_types = {"eeArchitectureContextConcern": "OperationalContextConcern",
                     "eeArchitectureStoryConcern": "OperationalStoryConcern"}
    for concern, stakeholders in holders.items():
        body = braced_body(code, f"concern {concern} : {concern_types[concern]}")
        assert re.findall(r"\bstakeholder\s+(\w+)\s*:\s*(\w+)\s*;", body) == stakeholders, concern
    # each concern doc holds only its pinned sentences
    assert _doc(raw, "concern eeArchitectureContextConcern : OperationalContextConcern") == (
        "System architects, systems engineers and open-source reviewers need to see what is inside the vehicle "
        "network and what is around it: the source of the driving command, the Eclipse S-CORE path and the "
        "vehicle, and which item crosses the boundary in which direction. The actuation ECU is inside; the "
        "source and the S-CORE path are outside; the vehicle only receives.")
    assert _doc(raw, "concern eeArchitectureStoryConcern : OperationalStoryConcern") == (
        "Systems engineers, verification engineers and open-source reviewers need the vehicle network told in "
        "stakeholder language: the driving command on each of its two routes, a command that a fault makes "
        "invalid, and a link of the route that goes down.")


def test_dependencies_trace_the_story_and_the_context_to_phase_zero():
    raw = _raw()
    code = _code()
    deps = re.findall(r"\bdependency\s+(\w+)\s+from\s+([\w:]+)\s+to\s+([\w:]+)\s*;", code)
    assert {(name, client, supplier) for name, client, supplier in deps} == {
        ("vehicleNetworkStoryAnswersProblem", STORY, f"{FRAMING_PACKAGE}::eeArchitectureProblem"),
        ("commandSourceOnDrivingBaseline", "DrivingCommandSource", f"{FRAMING_PACKAGE}::{BASELINE_RECORD}"),
        ("scorePathOnScoreCommandSource", f"{CONTEXT}::scorePath", f"{FRAMING_PACKAGE}::asmEEScoreCommandSource"),
        ("routeScenariosOnZoneRouteGap", STORY, f"{FRAMING_PACKAGE}::gapEEZoneRouteInVehicles"),
    }
    assert len(deps) == 4
    framing = strip_comments(FRAMING.read_text(encoding="utf-8"))
    for _, _, supplier in deps:
        name = supplier.split("::")[-1]
        assert re.search(rf"\b(?:requirement|part)\s+{name}\s*:", framing), f"{name} is a phase 0 record"
    abouts = re.findall(r"\bcomment\s+(\w+)\s+about\s+([\w:]+)", raw)
    assert abouts == [("actuationEndComment", f"{FRAMING_PACKAGE}::gapEEActuationEnd"),
                      ("stackAndNetworkBoundaryComment", f"{FRAMING_PACKAGE}::gapEEStackAndNetworkBoundary")]
    actuation = _flat(re.sub(r"(?m)^\s*\*\s?", "", re.search(
        r"comment actuationEndComment about [\w:]+\s*/\*(.*?)\*/", raw, re.S).group(1)))
    for phrase in ("Phase 2 draws no input from the vehicle to the actuation ECU",
                   "phases 6 to 8 decide inside the black box",
                   "this context changes neither the driver-assistance nor the closed-loop adapter."):
        assert phrase in actuation, phrase
    stack = _flat(re.sub(r"(?m)^\s*\*\s?", "", re.search(
        r"comment stackAndNetworkBoundaryComment about [\w:]+\s*/\*(.*?)\*/", raw, re.S).group(1)))
    for phrase in ("The central computer lies across the boundary", "VehicleNetworkBoundary", "phase 3"):
        assert phrase in stack, phrase


#: An affirmative timing, safety or approval claim in words; the framing test's approval words are read from it.
CLAIM = re.compile(r"(?i)\b(?:deadline|latency|real-time|meets|guarantee[sd]?|ASIL|safe|freedom from interference)\b")


def test_phase_two_makes_no_timing_safety_or_approval_claim():
    from test_ee_architecture_framing import APPROVAL
    texts = {MODEL.name: _raw(), "the guide's Phase 2 section": _guide_section()}
    for name, text in texts.items():
        for sentence in re.split(r"(?<=[.;:])\s+", _flat(re.sub(r"(?m)^\s*\*\s?", " ", text))):
            # only the nonclaims are skipped: a sentence that begins "No timing" or says "without any timing"
            if sentence.startswith("No timing") or "without any timing" in sentence:
                continue
            assert not APPROVAL.search(sentence), f"{name} makes an approval claim: {sentence}"
            assert not CLAIM.search(sentence), f"{name} makes a timing or safety claim: {sentence}"


def test_the_guide_has_a_phase_two_section():
    guide = GUIDE.read_text(encoding="utf-8")
    assert ("**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context, Phase 3 capability "
            "classification, Phase 4 stakeholder needs, Phase 5 requirements, Phase 6 functional architecture and "
            "Phase 7 logical architecture, proposal.**") in _flat(guide)
    assert "Phase 4 stakeholder needs and Phase 5 requirements, proposal.**" not in _flat(guide)
    assert guide.index("## Concerns (Phase 1)") < guide.index("## Operational context and story (Phase 2)") \
        < guide.index("## What the framing already records as open")
    flat = _guide_section()
    for phrase in (
            "Phase 2 draws the boundary that Phase 0 states and does not move it.",
            "Inside the vehicle network: the network side of the central computer, the Ethernet backbone, the two "
            "zone controllers, a CAN bus in each zone, the direct link and the actuation ECU.",
            "Around it: the source of the driving command (`DrivingCommandSource`), the Eclipse S-CORE path and "
            "the vehicle, which takes the applied command and sends nothing back.",
            "`SC-EE-001` carries the command through a zone controller, `SC-EE-002` over the direct link, "
            "`SC-EE-003` covers a command that is lost, delayed, repeated or corrupted on either route, and "
            "`SC-EE-004` a link of the route that goes down, after which the vehicle gets the stop response.",
            "The stop response comes from the engineering question and REQ-DRIVING-028 of the closed-loop driving "
            "increment, not from the driver-assistance increment, whose adapter has no stop response "
            "(`gapEEActuationEnd`).",
            "The criteria and their limits are fixed with the requirements in Phase 5, and the verdict for each "
            "route comes from Phase 10.",
            "The context view frames `eeArchitectureContextConcern`.",
            "The story view frames `eeArchitectureStoryConcern` and the Phase 1 concern `eeVehicleCommandConcern`, "
            "which the story answers.",
            "No timing, safety or compliance claim for a vehicle network is made.",
            "The testbed, the replay, the fault injection, the vehicle model, the records and the evaluators stay "
            "in `eeVerificationEnvironment`."):
        assert phrase in flat, phrase
    assert not re.search(r"(?i)\breplay(?:s|ed)? (?:stands|gives)\b", flat)


def test_the_guide_names_the_next_obligation_after_phase_two():
    flat = _flat(GUIDE.read_text(encoding="utf-8").split("## Next obligation and execution limits", 1)[1]
                 .split("\n## ", 1)[0])
    # phase 3 records no feature-model delta, and phase 7 has started, so the next obligation is phase 8
    for phrase in ("Phase 3, the capability classification, records no feature-model delta, and review judges it: "
                   "its one blocking check has nothing to evaluate, so the Method Check lists Phase 3 as vacuous, "
                   "with a prompt for review.",
                   "After that baseline, the owner decided on 2026-11-21 to start Phase 4, on 2026-11-22 to go "
                   "on with Phase 5, on 2026-11-24 to go on with Phase 6 and on 2026-11-25 to go on with Phase 7.",
                   "The next model obligation is **Phase 8**: the E/E and software realization, which allocates "
                   "each logical element to a physical element; its first gate is "
                   "`logicalElementAllocatedToPhysicalElement`.",
                   "The testbed with its readiness probe waits for a further decision of the owner."):
        assert phrase in flat, phrase
    assert "The next model obligation is **Phase 4**" not in flat
    assert "The next model obligation is **Phase 2**" not in flat
    assert "The next model obligation is **Phase 3**" not in flat
    assert "The next model obligation is **Phase 6**" not in flat
    assert "The next model obligation is **Phase 7**" not in flat
