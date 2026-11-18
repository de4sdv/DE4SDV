"""INC-DRIVING-002 phase 10, first slice: the verification cases of the driver-assistance requirements.

Lexical pins on ``driver_assistance_verification_evidence.sysml``: one case per requirement, each bound to the
realization of the driver-assistance system in DRIVING-CONFIG-002, not started, each naming the scenarios, settings
and runs its requirement's criteria read; the run-level evidence record and the record of the one analysis; the
environment gap that continues the readiness items of phase 8; the claims, arguments and counter-claims the
assurance view links; and the evidence decisions of 2026-11-18 by their exact phrases. The invariants of every
verification model are in ``test_verification_model_invariants.py``; the licensed Syside run validates the model.
"""

from __future__ import annotations

import re
from pathlib import Path

from sysml_shapes import charter_package_files, strip_comments

ROOT = Path(__file__).resolve().parents[1]
DRIVING = ROOT / "textual-notation-of-model" / "packages" / "features" / "driving"
SLICE = DRIVING / "driver_assistance_verification_evidence.sysml"
REQUIREMENTS = DRIVING / "driver_assistance_needs_requirements.sysml"
FRAMING = DRIVING / "driver_assistance_framing.sysml"
PHYSICAL = DRIVING / "driver_assistance_physical_software_realization.sysml"
VARIABILITY = DRIVING / "driver_assistance_variability_configuration.sysml"
DRIVING_001_FRAMING = DRIVING / "closed_loop_driving_framing.sysml"
GUIDE = ROOT / "docs" / "guides" / "driver-assistance-increment.md"
WORKFLOW = ROOT / "methodologies" / "sysmod-sysmlv2" / "increment-workflow.md"
MODEL_ROOTS = [ROOT / "textual-notation-of-model", ROOT / "model-based-product-line-engineering"]

PACKAGE = "DE4SDV_DriverAssistanceVerificationEvidence"
BENCH_DEF = "DriverAssistanceVerificationBench"
RUN_RECORD = "RetainedAssistanceRunEvidence"
ANALYSIS_RECORD = "RetainedCommandFormAnalysis"
GAP = "GAP-DRIVING-014"
GAP_NAME = "gapAssistanceVerificationEnvironmentOpen"
DECISIONS = "the evidence decisions of 2026-11-18"
NUMBERS = list(range(36, 45))

SC_IDS = {"stationaryTarget": "SC-DRIVING-012", "slowerTarget": "SC-DRIVING-013",
          "curveWithGuardPipes": "SC-DRIVING-014", "vehicleTurningOff": "SC-DRIVING-015"}
SETTINGS = {"stationaryAt20": "stationaryTarget", "stationaryAt42": "stationaryTarget",
            "stationaryAt60": "stationaryTarget", "slowerAt30": "slowerTarget", "slowerAt60": "slowerTarget",
            "curveAt30": "curveWithGuardPipes", "turningOffAt40": "vehicleTurningOff"}
TARGET_SETTINGS = [s for s, scenario in SETTINGS.items() if scenario in ("stationaryTarget", "slowerTarget")]
STOP_RUN = ("the further run of SC-DRIVING-012 in which the Eclipse S-CORE path of the driver-assistance system "
            "is stopped")
APART = ("The runs of SC-DRIVING-014 and SC-DRIVING-015 are reported apart from the runs inside the declared "
         "operating conditions (gapDeclaredOperatingConditions).")

#: requirement number -> (the settings the case reads, the count phrase of its runs, whether it reads the stop run,
#: the requirement's verification method); the criteria of each requirement name them
CASE_RUNS = {
    36: (TARGET_SETTINGS, "ten runs", False, "test"),
    37: (TARGET_SETTINGS, "ten runs", False, "test"),
    38: (list(SETTINGS), "fourteen runs", True, "test"),
    39: ([], None, False, "analyze"),
    40: (list(SETTINGS), "fourteen runs", True, "test"),
    41: (list(SETTINGS), "fourteen runs", True, "test"),
    42: (TARGET_SETTINGS, "ten runs", False, "test"),
    43: (TARGET_SETTINGS, "ten runs", True, "test"),
    44: (list(SETTINGS), "fourteen runs", True, "test"),
}

#: claim -> (the phase 1 concern it answers, the requirement numbers its argument cites)
CLAIMS = {
    "vehicleTargetResponse": ("vehicleTargetResponseConcern", [36, 37, 40, 41]),
    "emergencyBrakingIndependence": ("emergencyBrakingIndependenceConcern", [38, 39]),
    "driverWarningSequence": ("driverWarningSequenceConcern", [40, 42]),
    "scoreCommandAndWarningPath": ("scoreCommandAndWarningPathConcern", [38, 43]),
    "candidateVerdict": ("candidateVerdictConcern", [44]),
}
#: the phase 1 concern whose question no run answers, and so no claim
UNCLAIMED_CONCERN = "vehicleTargetCriteriaConcern"
#: counter-claim -> (the record that keeps it open, its file)
COUNTER_CLAIMS = {
    "SimulatedConfigurationOnly": ("asmSimulatedConfigurationStandsIn", FRAMING),
    "RenderedCameraImages": ("gapCameraImageAndGeometry", FRAMING),
    "NoComplianceOrApproval": ("onRoadOperationOutOfScope", FRAMING),
    "OutsideDeclaredConditions": ("gapDeclaredOperatingConditions", FRAMING),
    "NoIndependentEmergencyPath": ("gapNoSeparateEmergencyFunction", FRAMING),
    "BuildWithUnmergedChanges": ("gapCandidateBehaviorUnverified", FRAMING),
    "WarningModesNotJudgedHere": ("furtherWarningProvisionsOutOfScope", FRAMING),
    "NoMemberProduct": ("gapCandidateAdmission", FRAMING),
    "NoUpstreamEndorsementOrRights": ("gapUpstreamContactAndRights", FRAMING),
    "BenchOpenNoVerdict": (GAP_NAME, SLICE),
}
RUN_ATTRIBUTES = [
    "configurationIdentity", "receiptSha256", "modelRevision", "candidateRecordIdentity", "upstreamRevision",
    "sourceDifference", "networkFileSha256", "configurationFileSha256", "launchSettings", "candidateBuild",
    "visualizationRecorderDelay", "scoreLifecycleVersion", "scoreCommunicationVersion", "scoreSOMEIPGatewayCommit",
    "guestImageBuilds", "simulatorBuild", "scenario", "setting", "runIdentity", "simulationClockSpan",
    "wallClockSpan", "rawObservationArtifact", "benchRecordingArtifact", "independentEngineerIdentity",
    "claimBoundary"]
ANALYSIS_ATTRIBUTES = ["configurationIdentity", "receiptSha256", "modelRevision", "analyzedRealization",
                       "analystIdentity", "claimBoundary"]
OUTCOMES = ["passBoundedVerification", "passBoundedValidation", "failObservedBehavior",
            "inconclusiveMissingEvidence", "blockedTargetRuntime", "errorEvidence"]

_NOT_CODE = re.compile(r"/\*.*?\*/|//[^\n]*|\"(?:[^\"\\]|\\.)*\"", re.S)


def _code(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return _NOT_CODE.sub(lambda match: '""' if match.group().startswith('"') else " ", text)


def _body(text: str, header: str) -> str:
    matches = list(re.finditer(header, text))
    assert len(matches) == 1, f"expected one {header!r}, found {len(matches)}"
    start = matches[0].end() - 1
    assert text[start] == "{", f"{header!r} does not end with an opening brace"
    depth = 0
    for end in range(start, len(text)):
        depth += {"{": 1, "}": -1}.get(text[end], 0)
        if depth == 0:
            return text[start : end + 1]
    raise AssertionError(f"{header!r} has an unbalanced body")


def _flat(text: str) -> str:
    return " ".join(re.sub(r"^\s*\*\s?", "", text, flags=re.M).split())


def _docs(path: Path) -> str:
    return _flat(path.read_text(encoding="utf-8"))


def _requirements() -> dict[int, tuple[str, str]]:
    """Requirement number -> (usage name, verification method), from the phase 5 package."""
    raw = REQUIREMENTS.read_text(encoding="utf-8")
    found = {}
    for match in re.finditer(r"requirement <'REQ-DRIVING-(\d{3})'> (\w+) : \w*RequirementCandidate \{", raw):
        body = _body(raw[match.start():], re.escape(match[0]))
        (method,) = re.findall(r'attribute :>> verificationMethod = "(\w+)";', body)
        found[int(match[1])] = (match[2], method)
    assert sorted(found) == NUMBERS
    return found


def _usages() -> dict[int, tuple[str, str, str]]:
    """Case number -> (usage name, definition name, raw usage body with its doc)."""
    raw = SLICE.read_text(encoding="utf-8")
    out = {}
    for match in re.finditer(r"verification <'VC-DRIVING-(\d{3})'> (\w+) : (\w+) \{", raw):
        out[int(match[1])] = (match[2], match[3], _body(raw[match.start():], re.escape(match[0])))
    return out


def _definitions() -> dict[str, str]:
    code = _code(SLICE)
    return {m[1]: _body(code[m.start():], re.escape(m[0])) for m in re.finditer(r"\bverification def (\w+) \{", code)}


def _definition_docs() -> dict[str, str]:
    raw = SLICE.read_text(encoding="utf-8")
    return {m[1]: _flat(_body(raw[m.start():], re.escape(m[0]))) for m in re.finditer(r"\bverification def (\w+) \{", raw)}


# -- the cases ------------------------------------------------------------------------------------


def test_each_requirement_of_the_increment_is_verified_by_exactly_one_case() -> None:
    """Nine requirements, nine cases VC-DRIVING-036 to -044, each objective verifying the requirement of its own
    number with its subject bound to the realization on the bench (decision 1 of 2026-11-18: one case per
    requirement)."""
    requirements = _requirements()
    usages = _usages()
    definitions = _definitions()
    assert sorted(usages) == NUMBERS
    verified = {}
    for number, (usage, definition, _) in usages.items():
        body = definitions[definition]
        assert len(re.findall(r"\bobjective \w+ \{", body)) == 1, usage
        objective = _body(body, r"\bobjective \w+ \{")
        (target,) = re.findall(
            r"\bverify (\w+) \{ subject driverAssistanceSystem = verifiedBench\.assistanceSoftware; \}", objective)
        assert len(re.findall(r"\bverify\b", objective)) == 1, usage
        verified[number] = target
    assert verified == {n: name for n, (name, _) in requirements.items()}, "each case verifies its own requirement"
    assert len(definitions) == len(set(definitions)) == len(NUMBERS)


def test_the_case_ids_continue_the_series_and_are_unique_in_the_model() -> None:
    ids = []
    for path in sorted((ROOT / "textual-notation-of-model").rglob("*.sysml")):
        ids += re.findall(r"<'(VC-[A-Z0-9-]+)'>", path.read_text(encoding="utf-8"))
    assert len(set(ids)) == len(ids), "a verification-case id is declared once in the model"
    own = re.findall(r"<'(VC-DRIVING-\d{3})'>", SLICE.read_text(encoding="utf-8"))
    assert own == [f"VC-DRIVING-0{n}" for n in NUMBERS]
    increment_files = charter_package_files(FRAMING, "driverAssistanceCharter")
    assert SLICE in increment_files
    elsewhere = [i for path in increment_files if path != SLICE
                 for i in re.findall(r"<'(VC-DRIVING-\d{3})'>", path.read_text(encoding="utf-8"))]
    assert not elsewhere, "a case id belongs to the verification-evidence slice and nowhere else"
    earlier = [int(i[-3:]) for i in ids if i.startswith("VC-DRIVING-") and i not in own]
    assert earlier and max(earlier) + 1 == NUMBERS[0], "the numbers continue the VC-DRIVING series"


def test_no_case_has_started_and_each_states_its_scenarios_settings_runs_and_bench() -> None:
    """Each usage doc opens with Not started and names the scenarios by SC identity and enum literal, the
    settings, the runs and the bench that its requirement's criteria read; every requirement keeps NotStarted."""
    for number, (usage, _, body) in _usages().items():
        doc = _flat(body)
        settings, count, stop, method = CASE_RUNS[number]
        assert "doc /* Not started. Scenarios: " in doc, usage
        scenarios = sorted({SETTINGS[s] for s in settings})
        assert sorted(re.findall(r"AssistanceScenarioIdentity::(\w+)", doc)) == scenarios, usage
        for scenario in scenarios:
            assert f"{SC_IDS[scenario]} (AssistanceScenarioIdentity::{scenario})" in doc, (usage, scenario)
        named = re.search(r"Settings: (.*?)\. Runs:", doc)
        assert (re.findall(r"\b(\w+At\d\d)\b", named[1]) if named else []) == settings, usage
        if count:
            assert f"Runs: the two runs of each setting, {count}" in doc, usage
        assert (STOP_RUN in doc) is stop, usage
        assert (APART in doc) is ("curveAt30" in settings), usage
        kinds = "(test, analyze)" if method == "test" else "analyze"
        assert f"@VerificationMethod{{ kind = {kinds}; }}" in body, usage
        assert "subject verifiedBench :> driverAssistanceVerificationBench;" in body, usage
    assert "Scenarios: none; the case reads the realization of phase 8 and no run." in _flat(_usages()[39][2])
    raw = REQUIREMENTS.read_text(encoding="utf-8")
    assert raw.count("verificationStatus = VVStatus::NotStarted") == len(NUMBERS)
    assert "VVStatus::" not in SLICE.read_text(encoding="utf-8"), "this slice sets no status"


def test_each_case_collects_by_its_requirements_method_and_analyzes_against_the_requirement() -> None:
    """Eight requirements state the method test and REQ-DRIVING-039 the method analyze: the eight cases collect
    the run record by test, the case of 039 collects the analysis record by analysis; all process and evaluate by
    analysis, to the increment's own outcome and the standard verdict."""
    requirements = _requirements()
    definitions = _definitions()
    for number, (usage, definition, _) in _usages().items():
        body = definitions[definition]
        method = requirements[number][1]
        assert method == CASE_RUNS[number][3], number
        record = ANALYSIS_RECORD if method == "analyze" else RUN_RECORD
        assert re.search(rf"action collectData \{{\s*@VerificationMethod\{{ kind = {method}; \}}\s*out item "
                         rf"retainedEvidence : {record};", body), usage
        assert re.search(r"action processData \{\s*@VerificationMethod\{ kind = analyze; \}\s*in item retainedEvidence : "
                         rf"{record} = collectData\.retainedEvidence;\s*out evaluatedOutcome : AssistanceEvidenceOutcome;",
                         body), usage
        assert re.search(r"action evaluateData \{\s*@VerificationMethod\{ kind = analyze; \}\s*in evaluatedOutcome : "
                         r"AssistanceEvidenceOutcome = processData\.evaluatedOutcome;", body), usage
        assert "out verdict : VerdictKind = MapAssistanceEvidenceOutcomeToVerdict(evaluatedOutcome);" in body, usage
        assert "return verdict : VerdictKind = evaluateData.verdict;" in body, usage
        assert re.search(rf"\bsubject verifiedBench : {BENCH_DEF};", body), usage
    docs = _definition_docs()
    for number, (_, definition, _) in _usages().items():
        lead = "Analysis" if CASE_RUNS[number][3] == "analyze" else "Test"
        assert f"doc /* {lead} of REQ-DRIVING-0{number}. collectData retains" in docs[definition], definition


def test_every_case_is_performed_by_the_verification_system_once() -> None:
    system = _body(_code(SLICE), r"\bpart driverAssistanceVerificationSystem \{")
    performed = re.findall(r"\bperform (\w+);", system)
    assert performed == [usage for _, (usage, _, _) in sorted(_usages().items())]
    code = " ".join(_code(SLICE).split())
    assert ("dependency verificationSystemIsTheDriverAssistanceVerificationEnvironment from "
            "driverAssistanceVerificationSystem to driverAssistanceVerificationEnvironment;") in code
    assert (f"dependency assistanceEnvironmentGapOnVerificationSystem from {GAP_NAME} "
            "to driverAssistanceVerificationSystem;") in code
    assert re.search(r"\bpart driverAssistanceVerificationEnvironment : System2EngineeringAndAssuranceSystem \{",
                     _code(FRAMING))


def test_no_validation_case_is_added_and_the_phase_4_reviews_stay_planned() -> None:
    code = _code(SLICE)
    assert "ValidationPlanningScenario" not in code and "passBoundedValidation?" in " ".join(code.split())
    assert "validation" not in " ".join(re.findall(r"\bverification <'[^']+'> (\w+)", code)).lower()
    docs = _docs(SLICE)
    assert ("The validation of the needs stays planned in phase 4 (SC-DRIVING-016 to SC-DRIVING-019). This slice "
            "adds no validation case.") in docs
    for plan in ("SC-DRIVING-016", "SC-DRIVING-017", "SC-DRIVING-018", "SC-DRIVING-019"):
        assert re.search(rf"part <'{plan}'> \w+ : ValidationPlanningScenario \{{", REQUIREMENTS.read_text(encoding="utf-8"))


# -- the vocabulary, the records and the bench ------------------------------------------------------------------


def test_the_outcome_vocabulary_is_the_increments_own_with_the_six_shared_literals() -> None:
    """Decision 2 of 2026-11-18: an own enum and verdict map with the precedent's six literals; the mapping is
    total, only the two pass literals give pass, error gives error and every other outcome inconclusive."""
    code = _code(SLICE)
    assert re.findall(r"(\w+);", _body(code, r"\benum def AssistanceEvidenceOutcome \{")) == OUTCOMES
    calc = " ".join(_body(code, r"\bcalc def MapAssistanceEvidenceOutcomeToVerdict \{").split())
    assert "in outcome : AssistanceEvidenceOutcome;" in calc
    branches = re.findall(r"outcome == AssistanceEvidenceOutcome::(\w+)\? VerdictKind::(\w+)", calc)
    assert branches == [("passBoundedVerification", "pass"), ("passBoundedValidation", "pass"),
                        ("failObservedBehavior", "fail"), ("errorEvidence", "error")]
    assert calc.rstrip("} ").endswith("else VerdictKind::inconclusive;")
    for foreign in ("DrivingEvidenceOutcome", "MiddlewareEvidenceOutcome", "DE4SDV_ClosedLoopDrivingVerificationEvidence",
                    "DE4SDV_MiddlewareVerificationEvidence"):
        assert foreign not in code, foreign
    assert re.findall(r"(\w+);", _body(code, r"\benum def AssistanceScenarioIdentity \{")) == list(SC_IDS)
    assert re.findall(r"(\w+);", _body(code, r"\benum def AssistanceSettingIdentity \{")) == list(SETTINGS)
    raw = SLICE.read_text(encoding="utf-8")
    assert set(re.findall(r"AssistanceScenarioIdentity::(\w+)", raw)) == set(SC_IDS)
    docs = _docs(SLICE)
    assert "Each setting runs twice and both runs count: fourteen runs." in docs
    assert ("is a fifteenth run at one of the three settings of SC-DRIVING-012; the next slice chooses which."
            in docs)
    assert "A missing or partial record gives inconclusive, never pass." in docs


def test_the_run_record_binds_the_identities_the_decision_names() -> None:
    """Decision 4 of 2026-11-18: one retained record per run, read by every case of that run, with the candidate
    identity of REQ-DRIVING-044, the configured product and its receipt digest, the model revision, the build and
    the recorder's delay, the platform, gateway and simulator pins, the scenario and setting, and both clocks."""
    code = _code(SLICE)
    record = _body(code, rf"\bitem def {RUN_RECORD} \{{")
    assert re.findall(r"\battribute (\w+) : ", record) == RUN_ATTRIBUTES
    assert "attribute scenario : AssistanceScenarioIdentity;" in record
    assert "attribute setting : AssistanceSettingIdentity;" in record
    docs = _docs(SLICE)
    for phrase in (f"every case that reads the run reads this record ({DECISIONS})",
                   "It binds DRIVING-CONFIG-002 as its configurationIdentity.",
                   "candidateRecordIdentity names the candidate identity record of REQ-DRIVING-044 of the run",
                   "VisionPilot at 014e0e7a with the DE4SDV S-CORE interface and the DE4SDV visualization recorder",
                   "the readiness probe of the recorder on 2026-11-17 measured 2.0 ms more at the median and 5.8 ms "
                   "more at the 99th percentile from an image to its command",
                   "simulationClockSpan and wallClockSpan are the two clocks of the run, kept apart.",
                   "phase 10 judges no run whose judged window holds a dropped image (MAP-DRIVING-DA-CAMERA-IMAGE)",
                   "A missing or partial record gives inconclusive, never pass. No record exists yet."):
        assert phrase in docs, phrase
    analysis = _body(code, rf"\bitem def {ANALYSIS_RECORD} \{{")
    assert re.findall(r"\battribute (\w+) : ", analysis) == ANALYSIS_ATTRIBUTES
    assert "The evidence record of the analysis of REQ-DRIVING-039, which reads the realization and no run." in docs
    for name in ("DrivingCommandEventPayload", "MAP-DRIVING-DA-COMMAND", "reqDetectableDrivingCommandRejection"):
        assert name in _flat(_body(SLICE.read_text(encoding="utf-8"), rf"\bitem def {ANALYSIS_RECORD} \{{")), name
        assert name in PHYSICAL.read_text(encoding="utf-8"), name
    # each record is read by a case: the analysis record by the one analysis, the run record by the eight tests
    typed = re.findall(r"out item retainedEvidence : (\w+);", code)
    assert typed.count(ANALYSIS_RECORD) == 1 and typed.count(RUN_RECORD) == len(NUMBERS) - 1


def test_the_bench_refers_to_the_realization_in_driving_config_002() -> None:
    code = " ".join(_code(SLICE).split())
    bench = _body(code, rf"\bpart def {BENCH_DEF} \{{")
    assert ("ref part system1ConfiguredProduct :> DE4SDV_DriverAssistanceVariabilityConfiguration::configuredProduct;"
            in bench)
    assert ("ref part assistanceSoftware :> DE4SDV_DriverAssistanceFraming::candidateDriverAssistanceSystem = "
            "system1ConfiguredProduct.assistanceSoftware;") in bench
    assert len(re.findall(r"\bpart \w+ :", bench)) == 2 and not re.search(r"(?<!ref )\bpart \w+ :", bench), \
        "the bench owns no System 1 part"
    assert f"part driverAssistanceVerificationBench : {BENCH_DEF};" in code
    variability = _code(VARIABILITY)
    assert re.search(r"\bpart <'DRIVING-CONFIG-002'> configuredProduct : ", variability)
    assert "part assistanceSoftware : DriverAssistanceSoftwareRealization;" in variability
    assert "The bench is not a product selection." in _docs(SLICE)


def test_the_environment_gap_is_deferred_and_continues_the_readiness_items_of_phase_8() -> None:
    """Decision 5 of 2026-11-18: the test environment stays a gap that continues the phase 8 readiness items until
    the probes run."""
    raw = SLICE.read_text(encoding="utf-8")
    gap = _body(raw, rf"\bpart <'{GAP}'> {GAP_NAME} : IncrementGap \{{")
    assert "attribute :>> disposition = LifecycleDisposition::deferred;" in gap
    doc = _flat(gap)
    for phrase in (f"continue here until the probes run ({DECISIONS})",
                   "the link of the S-CORE process with the build of ONNX Runtime for CUDA",
                   "whether that process may hold a second C++ standard library",
                   "that the candidate record reaches the vehicle interface, which subscribes after the record was "
                   "published",
                   "the candidate driving on CARLA 1.0, which it has not done yet",
                   "whether the S-CORE host's own GPU keeps the candidate's cycle with the S-CORE build",
                   "the capture of the start of the sound on the IVI guest, which is unmeasured",
                   "The calibration runs of ASM-DRIVING-005 and ASM-DRIVING-006 come before the first judged run.",
                   "nothing of phase 10 is built before the probes are read",
                   "Deferred to that slice."):
        assert phrase in doc, phrase
    physical = _docs(PHYSICAL)
    for source in ("Open before phase 10: the link with the build of ONNX Runtime for CUDA",
                   "The candidate itself has not yet driven on CARLA 1.0",
                   "Whether the S-CORE host's own GPU keeps the cycle with the S-CORE build is not shown yet",
                   "the start of the sound on the guest is unmeasured"):
        assert source in physical, source
    ids = sorted(set(re.findall(r"GAP-DRIVING-\d{3}", "".join(
        p.read_text(encoding="utf-8") for p in DRIVING.glob("*.sysml")))))
    assert max(ids) == GAP and raw.count(f"<'{GAP}'>") == 1, "the next free gap number of the driving series"
    assert sum(p.read_text(encoding="utf-8").count(f"<'{GAP}'>") for p in DRIVING.glob("*.sysml")) == 1


# -- the assurance structure ----------------------------------------------------------------------


def test_each_claim_answers_one_phase_1_concern_and_its_argument_cites_the_right_cases() -> None:
    """Decision 3 of 2026-11-18: claims now, one per answered phase 1 concern, each argument citing the planned
    cases; vehicleTargetCriteriaConcern, answered by the phase 5 table, has none."""
    code = _code(SLICE)
    raw = SLICE.read_text(encoding="utf-8")
    usages = {n: u for n, (u, _, _) in _usages().items()}
    framing = _code(FRAMING)
    phase1 = re.findall(r"\bconcern (\w+) : (\w+Concern) \{", framing)
    assert sorted(c for c, _ in phase1 if c != "driverAssistanceBoundary") == sorted(
        [concern for concern, _ in CLAIMS.values()] + [UNCLAIMED_CONCERN])
    for stem, (concern, numbers) in CLAIMS.items():
        claim = _flat(_body(raw, rf"\brequirement {stem}Claim : DriverAssistanceClaim \{{"))
        assert f"doc /* Answers {concern}. " in claim, stem
        head, tail = claim.split(f"subject claimSubject : {BENCH_DEF}; require constraint {{", 1)
        assert head.rstrip(" /").endswith("A claim to be proven: no case has started."), stem
        assert tail.startswith(" doc /* The claim requires "), stem
        assert "; it excludes " in tail, stem
        cites = re.search(rf"dependency {stem}ArgumentCitesCases\s+from {stem}Argument\s+to ([^;]+);", code)
        assert cites, stem
        assert re.findall(r"\w+", cites[1]) == [usages[n] for n in numbers], stem
        argument = _flat(_body(raw, rf"\brequirement {stem}Argument : DriverAssistanceArgument \{{"))
        assert re.findall(r"VC-DRIVING-0(\d\d)", argument) == [str(n) for n in numbers], stem
        assert "the argument holds once every cited case has a pass verdict and fails with any fail" in argument
        assert re.search(rf"dependency claimSupportedBy{stem[0].upper() + stem[1:]}Argument\s+from {stem}Argument "
                         rf"to {stem}Claim;", code)
    assert re.findall(r"\brequirement (\w+)Claim : DriverAssistanceClaim \{", code) == list(CLAIMS)
    assert UNCLAIMED_CONCERN not in " ".join(re.findall(r"Answers (\w+)\.", raw))
    assert ("vehicleTargetCriteriaConcern is answered by the requirement definition table of phase 5, and no run "
            "answers it.") in _docs(SLICE)
    assert {n for _, numbers in CLAIMS.values() for n in numbers} == set(NUMBERS), "every case is cited"
    for definition, kind in [("DriverAssistanceClaim", "AssuranceClaim"),
                             ("DriverAssistanceArgument", "AssuranceArgument"),
                             ("DriverAssistanceCounterClaim", "AssuranceCounterClaim")]:
        assert f"requirement def {definition} :> {kind};" in code
    assert "RequirementCandidate" not in code, "the assurance elements specialize the kernel's assurance kinds"
    assert not re.search(r"\bsatisfy\b", code)


def test_each_counter_claim_restates_a_non_claim_of_the_framing_and_is_tied_to_its_record() -> None:
    code = _code(SLICE)
    raw = SLICE.read_text(encoding="utf-8")
    for stem, (target, home) in COUNTER_CLAIMS.items():
        doc = _flat(_body(raw, rf"\brequirement counterClaim{stem} : DriverAssistanceCounterClaim \{{"))
        assert re.search(rf"dependency counterClaim{stem}BoundTo\s+from counterClaim{stem} to {target};", code), stem
        assert re.search(rf"\bpart (<'[A-Z0-9-]+'> )?{target} : \w+ \{{", _code(home)), (stem, target)
        named = target if home is not SLICE else GAP
        assert f"{named})." in doc or f"{named}, " in doc or f", {named})" in doc or f"names {named}" in doc, stem
        if home is not SLICE:
            assert f"private import DE4SDV_DriverAssistanceFraming::{target};" in code, target
    assert re.findall(r"\brequirement counterClaim(\w+) : DriverAssistanceCounterClaim \{", code) == list(COUNTER_CLAIMS)
    docs = _docs(SLICE)
    assert ("No on-road, production-readiness, safety-approval, compliance, type-approval or certification claim, and "
            "none about UNECE R152") in docs
    assert "whether and when the display and the sound give the warning is the planned review SC-DRIVING-018" in docs


def test_the_slice_makes_no_result_compliance_or_regulation_claim() -> None:
    """Every case is Not started: no text reports behavior in a run or an approval, and every sentence that names
    UNECE R152 states what is not claimed."""
    raw = SLICE.read_text(encoding="utf-8")
    assert not re.search(r"(?i)\b(?:braked|warned|collided|avoided|detected|passed|failed)\b", raw)
    assert not re.search(r"(?i)\b(?:compliant|complies|certified|homologated|type-approved|admitted)\b", raw)
    sentences = [s for s in re.split(r"(?<=\.)\s+", _docs(SLICE)) if "R152" in s]
    assert len(sentences) >= 3
    for sentence in sentences:
        assert re.search(r"\b(?:no|none|excludes)\b", sentence), sentence
    assert not re.search(r"(?i)\bthe owner (?:said|wrote|asked|told)\b|[\u201c\u201d]", raw), \
        "the decisions are stated neutrally and dated, never quoted"
    assert raw.count(DECISIONS) >= 3


def test_the_assurance_view_frames_the_phase_1_assurance_concern_and_links_everything() -> None:
    code = _code(SLICE)
    view = _body(code, r"\bview driverAssistanceAssuranceView \{")
    viewpoint = " ".join(_body(view, r"\bviewpoint selectedAssuranceViewpoint : ArgumentationAssuranceViewpoint \{").split())
    assert viewpoint == "{ frame driverAssistanceArgumentationAssuranceConcern; frame candidateVerdictConcern; }"
    assert re.findall(r"\bconcern (\w+) : ArgumentationAssuranceConcern \{", _code(FRAMING)) == ["candidateVerdictConcern"]
    exposed = re.findall(r"\bexpose ([\w:]+);", view)
    usages = [u for _, (u, _, _) in sorted(_usages().items())]
    expected = ([f"{s}Claim" for s in CLAIMS] + [f"{s}Argument" for s in CLAIMS]
                + [f"counterClaim{s}" for s in COUNTER_CLAIMS] + usages
                + [RUN_RECORD, ANALYSIS_RECORD, BENCH_DEF, GAP_NAME]
                + [target for target, home in COUNTER_CLAIMS.values() if home is not SLICE]
                + [f"claimSupportedBy{s[0].upper() + s[1:]}Argument" for s in CLAIMS]
                + [f"{s}ArgumentCitesCases" for s in CLAIMS] + [f"counterClaim{s}BoundTo" for s in COUNTER_CLAIMS])
    assert exposed == expected
    assert "render asTreeDiagram;" in view and "attribute maxCompartmentEntries = 0;" in view
    assert len(re.findall(r"\bview \w+", code)) == 1, "one view in the phase"
    concern = _body(code, r"\bconcern driverAssistanceArgumentationAssuranceConcern : ArgumentationAssuranceConcern \{")
    assert re.findall(r"\bstakeholder \w+ : (\w+);", concern) == [
        "ProductLineEngineer", "VerificationEngineer", "OpenSourceReviewer"]
    assert "Product-line engineers, verification engineers and open-source reviewers need" in _docs(SLICE)


def test_the_views_per_phase_list_names_the_assurance_viewpoint_for_phase_10() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert re.search(r"- \*\*Phase 10\*\* — one tree: `ArgumentationAssuranceViewpoint`", text)


def test_the_package_declares_no_name_that_another_model_package_declares() -> None:
    kinds = (r"(?:part def|part|item def|enum def|calc def|verification def|verification|requirement def|requirement|"
             r"concern|view|dependency)")
    declared = set(re.findall(rf"(?m)^  {kinds}\s+(?:<'[^']*'>\s*)?(\w+)", _code(SLICE)))
    assert len(declared) >= 70, "the population of the check must not be vacuous"
    anywhere = re.compile(rf"\b{kinds}\s+(?:<'[^']*'>\s*)?(\w+)")
    taken: dict[str, list[str]] = {}
    for root in MODEL_ROOTS:
        for path in sorted(root.rglob("*.sysml")):
            if path == SLICE:
                continue
            for name in anywhere.findall(strip_comments(path.read_text(encoding="utf-8"))):
                if name in declared:
                    taken.setdefault(name, []).append(path.name)
    assert not taken, f"declared in another package too: {taken}"


# -- the charter and the guide --------------------------------------------------------------------


def test_the_charter_names_the_phase_10_package_last() -> None:
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", FRAMING.read_text(encoding="utf-8"), re.S)
    assert artifacts and re.findall(r'"([^"]+)"', artifacts.group(1))[-2:] == [
        "DE4SDV_DriverAssistanceVariabilityConfiguration", PACKAGE]
    assert re.findall(r"(?m)^package\s+(\w+)\s*\{", _code(SLICE)) == [PACKAGE], "one global package per file"


def test_the_guide_describes_the_first_phase_10_slice() -> None:
    guide = GUIDE.read_text(encoding="utf-8")
    order = [guide.index(heading) for heading in ("## Variability and configuration (Phase 9)",
                                                  "## Verification and evidence (Phase 10)",
                                                  "## What the framing already records as open")]
    assert order == sorted(order)
    raw_section = guide.split("## Verification and evidence (Phase 10)", 1)[1].split("\n## ", 1)[0]
    section = " ".join(raw_section.split())
    for text in ("VC-DRIVING-036", "VC-DRIVING-044", "DRIVING-CONFIG-002", "**One case per requirement.**",
                 "`NotStarted`", "2026-11-18", GAP, "the stop run", "simulation-clock and wall-clock spans",
                 "Ten counter-claims", "Five claims", "Argumentation Assurance", "**No validation case.**",
                 "`candidateVerdictConcern`", "`vehicleTargetCriteriaConcern` has no claim",
                 "Missing or partial evidence, and a setting whose runs are not judged, is inconclusive, never pass.",
                 "(../../textual-notation-of-model/packages/features/driving/driver_assistance_verification_evidence.sysml)"):
        assert text in section, text
    rows = re.findall(r"^\| (VC-DRIVING-\d{3}) \| (REQ-DRIVING-\d{3}), [^|]+ \| ([^|]+) \| (\w+) \|$", raw_section, re.M)
    assert [(case, requirement) for case, requirement, _, _ in rows] == [
        (f"VC-DRIVING-0{n}", f"REQ-DRIVING-0{n}") for n in NUMBERS]
    for (_, _, runs, method), number in zip(rows, NUMBERS):
        settings, count, stop, model_method = CASE_RUNS[number]
        assert method == {"test": "test", "analyze": "analysis"}[model_method], number
        assert (count or "no run") in runs and ("the stop run" in runs) is stop, number
    assert "instrument" not in section
    check = " ".join(guide.split("## Check the framing change", 1)[1].split())
    assert "tests/test_driver_assistance_verification_evidence.py" in check
    flat = " ".join(guide.split())
    assert "The next model obligation is **Phase 10**" in flat and "its second slice follows the readiness probes" in flat
