"""INC-DRIVING-001 phase 10, first slice: the verification cases of the closed-loop driving requirements.

Lexical pins on ``closed_loop_driving_verification_evidence.sysml``: one case per requirement, each bound to
the driving software of DRIVING-CONFIG-001, not started; the run-level evidence record with the bench
recording rule; the environment gap; the claims, arguments and counter-claims the assurance view links; and
the owner decisions of 2026-11-06 by their exact phrases. The invariants of every verification model are in
``test_verification_model_invariants.py``; the licensed Syside run validates the model.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DRIVING = ROOT / "textual-notation-of-model" / "packages" / "features" / "driving"
SLICE = DRIVING / "closed_loop_driving_verification_evidence.sysml"
REQUIREMENTS = DRIVING / "closed_loop_driving_needs_requirements.sysml"
FRAMING = DRIVING / "closed_loop_driving_framing.sysml"
PHYSICAL = DRIVING / "closed_loop_driving_physical_software_realization.sysml"
VARIABILITY = DRIVING / "closed_loop_driving_variability_configuration.sysml"
GUIDE = ROOT / "docs" / "guides" / "closed-loop-driving-increment.md"
WORKFLOW = ROOT / "methodologies" / "sysmod-sysmlv2" / "increment-workflow.md"

PACKAGE = "DE4SDV_ClosedLoopDrivingVerificationEvidence"
BENCH_DEF = "ClosedLoopDrivingVerificationBench"
RECORD = "RetainedDrivingRunEvidence"
GAP = "GAP-DRIVING-009"
CASE_COUNT = 35

#: requirement number -> (scenario literal, bench phrase the case usage must state)
CASE_SCENARIOS = {
    **{n: ("closedLoopRoute", "no guest") for n in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 13, 15, 16, 17, 30, 31, 32, 33, 34)},
    11: ("closedLoopRoute", "plan injection"), 12: ("closedLoopRoute", "plan injection"),
    14: ("closedLoopRoute", "stop of the S-CORE communication"), 28: ("closedLoopRoute", "stop of the S-CORE communication"),
    18: ("aaosUnavailable", "replayed"), 19: ("aaosUnavailable", "replayed"),
    **{n: ("degradedInputOrPlan", "input faults") for n in (20, 21, 22, 23, 24, 25, 26, 27, 29)},
    35: ("checkpointRefusal", "single byte"),
}
SCENARIO_IDS = {"closedLoopRoute": "SC-DRIVING-001", "degradedInputOrPlan": "SC-DRIVING-003",
                "aaosUnavailable": "SC-DRIVING-004", "checkpointRefusal": "none"}

#: claim -> (the phase 1 concern it answers, the requirement numbers its argument cites)
CLAIMS = {
    "drivenAlongTheRoute": ("drivenAlongTheRouteConcern", {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 33, 34}),
    "checkpointCommandAuthority": ("checkpointCommandAuthorityConcern", {2, 11, 12, 33, 34, 35}),
    "scoreCommandPath": ("scoreCommandPathConcern", {14, 28}),
    "observationFidelity": ("aaosObservationFidelityConcern", {15, 16, 17, 18, 19, 29}),
    "degradedInputBehavior": ("degradedInputBehaviorConcern", {9, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29}),
    "timeDomainHonesty": ("timeDomainHonestyConcern", {1, 13, 30, 31, 32}),
    "reproducibleClosedLoopEvidence": ("reproducibleClosedLoopEvidenceConcern", {2, 33, 34}),
}
#: counter-claim -> the record that keeps it open
COUNTER_CLAIMS = {
    "SimulatedSensorsAndDynamics": ("asmSimulatedSensorsStandForTheVehicles", PHYSICAL),
    "NoRealTimeOnTarget": ("gapClosedLoopPerformance", FRAMING),
    "NoSafetyOrCertification": ("roadDeploymentOutOfScope", FRAMING),
    "NoMembership": ("gapProductLineAdmission", FRAMING),
    "CheckpointRightsAndTransfer": ("gapAdoptionAndRights", FRAMING),
    "BoundedFaults": ("gapModelInputAndFeedback", FRAMING),
    "EnvironmentOpenNoVerdict": ("gapDrivingVerificationEnvironmentOpen", SLICE),
}
RECORD_ATTRIBUTES = [
    "configurationIdentity", "receiptSha256", "modelRevision", "checkpointSha256", "autoE2ESourceRevision",
    "configurationSha256", "runRecordIdentity", "scoreFEORevision", "scoreCommunicationVersion",
    "scoreLifecycleVersion", "scoreSOMEIPGatewayCommit", "simulatorBuild", "scenario", "simulationClockSpan",
    "wallClockSpan", "executionEnvironmentIdentity", "contractIdentity", "rawObservationArtifact",
    "benchRecordingArtifact", "independentObserverIdentity", "claimBoundary"]

_NOT_CODE = re.compile(r"/\*.*?\*/|//[^\n]*|\"(?:[^\"\\]|\\.)*\"", re.S)


def test_the_ego_motion_history_case_checks_yaw_rate_and_curvature_as_zero():
    # REQ-DRIVING-008 as amended on 2026-11-09: the case compares speed and acceleration with the simulator and
    # checks that yaw rate and curvature were given as zero.
    text = _docs(SLICE)
    assert "compares speed and acceleration with the simulator's values within 0.05 m/s and 0.1 m/s², and checks that yaw rate and curvature are 0" in text
    assert "0.01 rad/s" not in text and "0.001 1/m" not in text


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


def _docs(path: Path) -> str:
    return " ".join(re.sub(r"^\s*\*\s?", "", path.read_text(encoding="utf-8"), flags=re.M).split())


def _requirements() -> dict[int, str]:
    """Requirement number -> usage name, from the phase 5 package."""
    found = re.findall(r"requirement <'REQ-DRIVING-(\d{3})'> (\w+) : \w*RequirementCandidate \{", _code(REQUIREMENTS))
    assert len(found) == CASE_COUNT
    return {int(number): name for number, name in found}


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


# -- the cases ------------------------------------------------------------------------------------


def test_each_requirement_of_the_increment_is_verified_by_exactly_one_case() -> None:
    """Thirty-five requirements, thirty-five cases, each objective verifying one requirement with its subject
    bound to the driving software of the bench (owner decision 1 of 2026-11-06: one case per requirement)."""
    requirements = _requirements()
    usages = _usages()
    definitions = _definitions()
    assert sorted(usages) == list(range(1, CASE_COUNT + 1))
    verified = {}
    for number, (usage, definition, _) in usages.items():
        body = definitions[definition]
        assert len(re.findall(r"\bobjective \w+ \{", body)) == 1, usage
        objective = _body(body, r"\bobjective \w+ \{")
        (target,) = re.findall(r"\bverify (\w+) \{ subject drivingSystem = verifiedBench\.drivingSoftware; \}", objective)
        assert len(re.findall(r"\bverify\b", objective)) == 1, usage
        verified[number] = target
    assert verified == requirements, "every case verifies the requirement of its number and nothing else"
    assert len(set(verified.values())) == CASE_COUNT


def test_the_case_ids_are_unique_in_the_model() -> None:
    ids = []
    for path in sorted((ROOT / "textual-notation-of-model").rglob("*.sysml")):
        ids += re.findall(r"<'(VC-[A-Z0-9-]+)'>", path.read_text(encoding="utf-8"))
    driving = [i for i in ids if i.startswith("VC-DRIVING-")]
    assert len(driving) == CASE_COUNT and len(set(ids)) == len(ids)


def test_no_case_has_started_and_each_states_its_scenario_and_bench() -> None:
    """Each usage doc opens with Not started, names its scenario by SC identity and enum literal, and names the
    bench feature that distinguishes its run; every requirement keeps NotStarted."""
    for number, (usage, _, body) in _usages().items():
        doc = " ".join(re.sub(r"^\s*\*\s?", "", body, flags=re.M).split())
        literal, bench = CASE_SCENARIOS[number]
        assert "doc /* Not started. Scenario: " in doc, usage
        assert f"DrivingScenarioIdentity::{literal}" in doc, usage
        assert SCENARIO_IDS[literal] in doc, usage
        assert bench in doc, (usage, bench)
        assert "@VerificationMethod{ kind = (test, analyze); }" in body, usage
        assert "subject verifiedBench :> closedLoopDrivingVerificationBench;" in body, usage
    assert REQUIREMENTS.read_text(encoding="utf-8").count("verificationStatus = VVStatus::NotStarted") == CASE_COUNT


def test_each_case_collects_by_test_and_analyzes_against_the_requirement() -> None:
    """All thirty-five requirements state the method test; each case collects by test and processes and
    evaluates by analysis, from the run record to the increment's own outcome and the standard verdict."""
    assert _code(REQUIREMENTS).count('verificationMethod = ""') == CASE_COUNT
    assert REQUIREMENTS.read_text(encoding="utf-8").count('verificationMethod = "test"') == CASE_COUNT
    for name, body in _definitions().items():
        assert re.search(r"action collectData \{\s*@VerificationMethod\{ kind = test; \}\s*out item retainedEvidence : "
                         rf"{RECORD};", body), name
        assert re.search(r"action processData \{\s*@VerificationMethod\{ kind = analyze; \}\s*in item retainedEvidence : "
                         rf"{RECORD} = collectData\.retainedEvidence;\s*out evaluatedOutcome : DrivingEvidenceOutcome;", body), name
        assert "out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);" in body, name
        assert "return verdict : VerdictKind = evaluateData.verdict;" in body, name
        assert re.search(r"\bsubject verifiedBench : ClosedLoopDrivingVerificationBench;", body), name


def test_every_case_is_performed_by_the_verification_system_once() -> None:
    system = _body(_code(SLICE), r"\bpart closedLoopDrivingVerificationSystem \{")
    performed = re.findall(r"\bperform (\w+);", system)
    assert sorted(performed) == sorted(usage for usage, _, _ in _usages().values())
    assert len(performed) == len(set(performed)) == CASE_COUNT
    code = " ".join(_code(SLICE).split())
    assert ("dependency verificationSystemIsTheClosedLoopVerificationEnvironment from closedLoopDrivingVerificationSystem "
            "to closedLoopVerificationEnvironment;") in code
    assert ("dependency environmentGapOnVerificationSystem from gapDrivingVerificationEnvironmentOpen "
            "to closedLoopDrivingVerificationSystem;") in code


# -- the vocabulary, the record and the bench -------------------------------------------------------


def test_the_outcome_vocabulary_is_the_increments_own_with_the_six_shared_literals() -> None:
    """Owner decision 2 of 2026-11-06: an own enum and verdict map, the literals of INC-MW-010's, total mapping."""
    code = _code(SLICE)
    literals = re.findall(r"(\w+);", _body(code, r"\benum def DrivingEvidenceOutcome \{"))
    assert literals == ["passBoundedVerification", "passBoundedValidation", "failObservedBehavior",
                        "inconclusiveMissingEvidence", "blockedTargetRuntime", "errorEvidence"]
    calc = " ".join(_body(code, r"\bcalc def MapDrivingEvidenceOutcomeToVerdict \{").split())
    assert "in outcome : DrivingEvidenceOutcome;" in calc
    for literal, verdict in [("passBoundedVerification", "pass"), ("passBoundedValidation", "pass"),
                             ("failObservedBehavior", "fail"), ("errorEvidence", "error")]:
        assert f"outcome == DrivingEvidenceOutcome::{literal}? VerdictKind::{verdict}" in calc, literal
    assert calc.rstrip("} ").endswith("else VerdictKind::inconclusive;")
    assert "MiddlewareEvidenceOutcome" not in code and "DE4SDV_MiddlewareVerificationEvidence" not in code
    scenarios = re.findall(r"(\w+);", _body(code, r"\benum def DrivingScenarioIdentity \{"))
    assert scenarios == ["closedLoopRoute", "degradedInputOrPlan", "aaosUnavailable", "checkpointRefusal"]
    assert set(re.findall(r"DrivingScenarioIdentity::(\w+)", SLICE.read_text(encoding="utf-8"))) == set(scenarios)


def test_the_run_record_binds_the_identities_and_the_bench_recording() -> None:
    """Owner decision 4: one record per run. The recording rule of 2026-11-09, which supersedes the single capture
    of 2026-11-06: separate real-time recordings per host, each showing its clocks, never retimed."""
    code = _code(SLICE)
    attributes = re.findall(r"\battribute (\w+) : ", _body(code, rf"\bitem def {RECORD} \{{"))
    assert attributes == RECORD_ATTRIBUTES
    assert "attribute scenario : DrivingScenarioIdentity;" in code
    docs = _docs(SLICE)
    for phrase in ["separate real-time recordings, one per host, taken while the run runs",
                   "the simulator's chase view of the vehicle, rendered and encoded by the simulator host's hardware "
                   "video encoder (NVENC) after one warm-up lap",
                   "the display of the IVI VM with the observer application, recorded on the guest",
                   "the terminal sessions of the bench, recorded as terminal sessions",
                   "Each recording shows its clocks",
                   "A public cut may place them side by side, aligned by the clocks the run record names; nothing is "
                   "retimed and nothing is rendered after the run (owner decision of 2026-11-09, which supersedes the "
                   "single capture of 2026-11-06)",
                   "the public cut of the increment comes from these recordings and from nothing else",
                   "A missing or partial record gives inconclusive, never pass. No record exists yet."]:
        assert phrase in docs, phrase
    assert "It is not composed from separate recordings" not in docs, "superseded on 2026-11-09"


def test_the_bench_refers_to_the_driving_software_of_driving_config_001() -> None:
    code = " ".join(_code(SLICE).split())
    bench = _body(code, rf"\bpart def {BENCH_DEF} \{{")
    assert "ref part system1ConfiguredProduct :> DE4SDV_ClosedLoopDrivingVariabilityConfiguration::configuredProduct;" in bench
    assert ("ref part drivingSoftware :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem = "
            "system1ConfiguredProduct.drivingSoftware;") in bench
    assert "ref part" in bench and not re.search(r"(?<!ref )\bpart \w+ :", bench[1:]), "the bench owns no System 1 part"
    assert f"part closedLoopDrivingVerificationBench : {BENCH_DEF};" in code
    assert re.search(r"\bpart <'DRIVING-CONFIG-001'> configuredProduct : ", _code(VARIABILITY))


def test_the_environment_gap_is_deferred_and_names_the_probes_and_the_capture() -> None:
    raw = SLICE.read_text(encoding="utf-8")
    gap = _body(raw, rf"\bpart <'{GAP}'> gapDrivingVerificationEnvironmentOpen : IncrementGap \{{")
    assert "attribute :>> disposition = LifecycleDisposition::deferred;" in gap
    doc = " ".join(re.sub(r"^\s*\*\s?", "", gap, flags=re.M).split())
    for phrase in ["the probes the owner authorized on 2026-11-06", "were read from 2026-11-07 to 2026-11-09",
                   "three hosts", "the bench network", "the VXLAN segment", "GAP-DRIVING-007",
                   "separate real-time recordings per host", "the environment's identity",
                   "the three hosts have not yet run together"]:
        assert phrase in doc, phrase
    assert "side by side and both clocks visible" not in doc and "nothing of phase 10 is built before they are read" not in doc
    head = " ".join(raw[:raw.index("package ")].split())
    assert "stay open until then" not in head and "fixed by the readiness probes" in head
    ids = sorted(set(re.findall(r"GAP-DRIVING-\d{3}", "".join(p.read_text(encoding="utf-8") for p in DRIVING.glob("*.sysml")))))
    # GAP-DRIVING-009 took the next free number; GAP-DRIVING-010 (the history-mask decision of 2026-11-09) is the
    # newest since. Numbers are taken in order and never reused.
    assert GAP in ids and max(ids) == "GAP-DRIVING-010", "the next free gap number"


# -- the assurance structure ----------------------------------------------------------------------


def test_each_claim_answers_one_phase_1_concern_and_its_argument_cites_the_right_cases() -> None:
    """Owner decision 3: claims now, one per answered concern; counter-claims are the framing's non-claims."""
    code = _code(SLICE)
    raw = SLICE.read_text(encoding="utf-8")
    usages = {n: u for n, (u, _, _) in _usages().items()}
    framing = _code(FRAMING)
    for stem, (concern, numbers) in CLAIMS.items():
        claim = _body(raw, rf"\brequirement {stem}Claim : ClosedLoopDrivingClaim \{{")
        assert f"Answers {concern}." in " ".join(re.sub(r"^\s*\*\s?", "", claim, flags=re.M).split()), stem
        assert re.search(rf"\bconcern {concern} : \w+Concern \{{", framing), concern
        assert "subject claimSubject : ClosedLoopDrivingVerificationBench;" in claim and "require constraint {" in claim
        assert "A claim to be proven: no case has started." in " ".join(re.sub(r"^\s*\*\s?", "", claim, flags=re.M).split())
        cites = re.search(rf"dependency {stem}ArgumentCitesCases\s+from {stem}Argument\s+to ([^;]+);", code)
        assert cites, stem
        assert set(re.findall(r"\w+", cites[1])) == {usages[n] for n in numbers}, stem
        assert re.search(rf"dependency claimSupportedBy{stem[0].upper() + stem[1:]}Argument\s+from {stem}Argument to {stem}Claim;", code)
        assert re.search(rf"\brequirement {stem}Argument : ClosedLoopDrivingArgument \{{", code)
    assert set(re.findall(r"\brequirement (\w+)Claim : ClosedLoopDrivingClaim \{", code)) == set(CLAIMS)
    assert {n for _, numbers in CLAIMS.values() for n in numbers} == set(range(1, CASE_COUNT + 1)), "every case is cited"
    for stem, (target, home) in COUNTER_CLAIMS.items():
        assert re.search(rf"\brequirement counterClaim{stem} : ClosedLoopDrivingCounterClaim \{{", code), stem
        assert re.search(rf"dependency counterClaim{stem}BoundTo\s+from counterClaim{stem} to {target};", code), stem
        assert re.search(rf"\bpart (<'[A-Z0-9-]+'> )?{target} : \w+ \{{", _code(home)), (stem, target)
        if home is not SLICE:
            assert re.search(rf"\bprivate import \w+::{target};", code), target
    assert set(re.findall(r"\brequirement counterClaim(\w+) : ClosedLoopDrivingCounterClaim \{", code)) == set(COUNTER_CLAIMS)
    for definition, kind in [("ClosedLoopDrivingClaim", "AssuranceClaim"), ("ClosedLoopDrivingArgument", "AssuranceArgument"),
                             ("ClosedLoopDrivingCounterClaim", "AssuranceCounterClaim")]:
        assert f"requirement def {definition} :> {kind};" in code
    assert not re.search(r"\bsatisfy\b", code)


def test_the_assurance_view_frames_the_two_phase_1_assurance_concerns_and_links_everything() -> None:
    code = _code(SLICE)
    view = _body(code, r"\bview closedLoopDrivingAssuranceView \{")
    viewpoint = " ".join(_body(view, r"\bviewpoint selectedAssuranceViewpoint : ArgumentationAssuranceViewpoint \{").split())
    assert viewpoint == ("{ frame drivingArgumentationAssuranceConcern; frame timeDomainHonestyConcern; "
                         "frame reproducibleClosedLoopEvidenceConcern; }")
    assert re.search(r"\bconcern (timeDomainHonestyConcern|reproducibleClosedLoopEvidenceConcern) : ArgumentationAssuranceConcern \{",
                     _code(FRAMING))
    exposed = re.findall(r"\bexpose ([\w:]+);", view)
    usages = [u for u, _, _ in _usages().values()]
    for name in ([f"{s}Claim" for s in CLAIMS] + [f"{s}Argument" for s in CLAIMS] + [f"counterClaim{s}" for s in COUNTER_CLAIMS]
                 + usages + [RECORD, BENCH_DEF, "gapDrivingVerificationEnvironmentOpen"]
                 + [f"claimSupportedBy{s[0].upper() + s[1:]}Argument" for s in CLAIMS] + [f"{s}ArgumentCitesCases" for s in CLAIMS]
                 + [f"counterClaim{s}BoundTo" for s in COUNTER_CLAIMS]
                 + [target for target, _ in COUNTER_CLAIMS.values()]):
        assert name in exposed, name
    assert len(exposed) == len(set(exposed))
    assert "render asTreeDiagram;" in view and "attribute maxCompartmentEntries = 0;" in view
    concern = _body(code, r"\bconcern drivingArgumentationAssuranceConcern : ArgumentationAssuranceConcern \{")
    assert re.findall(r"\bstakeholder \w+ : (\w+);", concern) == ["SystemsEngineer", "VerificationEngineer", "OpenSourceReviewer"]
    assert "Systems engineers, verification engineers and open-source reviewers need" in _docs(SLICE)


def test_the_views_per_phase_list_names_the_assurance_viewpoint_for_phase_10() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert re.search(r"- \*\*Phase 10\*\* — one tree: `ArgumentationAssuranceViewpoint`", text)


# -- the charter and the guide --------------------------------------------------------------------


def test_the_charter_names_the_phase_10_package_last() -> None:
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", FRAMING.read_text(encoding="utf-8"), re.S)
    assert artifacts and re.findall(r'"([^"]+)"', artifacts.group(1))[-2:] == [
        "DE4SDV_ClosedLoopDrivingVariabilityConfiguration", PACKAGE]
    assert re.search(rf"\bpackage {PACKAGE}\s*\{{", _code(SLICE))


def test_the_guide_describes_the_first_phase_10_slice() -> None:
    guide = GUIDE.read_text(encoding="utf-8")
    assert "## Verification and evidence (Phase 10)" in guide
    section = guide.split("## Verification and evidence (Phase 10)")[1].split("\n## ")[0]
    for text in ["VC-DRIVING-001", "VC-DRIVING-035", "DRIVING-CONFIG-001", "One case per requirement", "Not started",
                 GAP, "bench recording", "both clocks", "2026-11-06", "counter-claims", "ArgumentationAssuranceViewpoint",
                 "probes"]:
        assert text in section, text
    assert "tests/test_closed_loop_driving_verification_evidence.py" in guide
    assert "closed_loop_driving_verification_evidence.sysml" in guide
    assert "The next work is **Phase 10**" not in guide
