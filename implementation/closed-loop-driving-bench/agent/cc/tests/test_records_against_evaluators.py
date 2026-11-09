#!/usr/bin/env python3
"""The agent's log records, read by the bench's own case evaluators.

The C++ test binary emits a scripted run (priming -> driving -> fault -> stop ->
standstill) as score/drivingAgent.jsonl. This test loads that file with the
evaluators' own reader (case-evaluators/runio.py) and runs the evaluators that
can decide on the agent's records alone (VC-DRIVING-026 and -027), plus
field-level checks for the cases that also need the world, the adapter or the
publisher (011, 020, 021, 022, 024, 029, 032).

Read-only against the bench: the bench tree is never written. Run dirs are
created under .build/runs/.

    python3 tests/test_records_against_evaluators.py [-v]

Exit status 0 when every check passes.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIB = HERE.parent
BENCH = Path(os.environ.get("DE4SDV_BENCH", str(Path(__file__).resolve().parents[3])))
EVAL = BENCH / "case-evaluators"
INCLUDE = BENCH / "interfaces" / "include"
BINARY = Path(os.environ.get("AGENT_LOGIC_TEST_BIN", LIB / ".build" / "agent_logic_test"))

sys.path.insert(0, str(EVAL))
import runio  # noqa: E402  (the evaluators' reader, read-only)
import cases  # noqa: E402  (the evaluators themselves)

FAILURES: list[str] = []
CHECKS = 0
VERBOSE = "-v" in sys.argv


def check(condition: bool, what: str) -> None:
    global CHECKS
    CHECKS += 1
    if not condition:
        FAILURES.append(what)
        print(f"FAIL {what}")
    elif VERBOSE:
        print(f"ok   {what}")


def check_close(actual, expected, tolerance: float, what: str) -> None:
    global CHECKS
    CHECKS += 1
    if actual is None or abs(float(actual) - float(expected)) > tolerance:
        FAILURES.append(f"{what} (actual {actual!r}, expected {expected!r})")
        print(f"FAIL {what} (actual {actual!r}, expected {expected!r})")
    elif VERBOSE:
        print(f"ok   {what}")


def ensure_binary() -> None:
    if BINARY.exists():
        return
    BINARY.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
        "-I", str(LIB), "-I", str(INCLUDE),
        str(LIB / "tests" / "agent_logic_test.cpp"),
        str(LIB / "agent_logic.cpp"), str(LIB / "json_lite.cpp"),
        "-o", str(BINARY),
    ]
    print("building:", " ".join(command))
    subprocess.run(command, check=True)


def envelope(event: str, seq: int, data: dict, component: str = "bench") -> dict:
    return {
        "t_mono_ns": 900_000_000_000 + seq * 1_000_000,
        "t_real_ns": 1_794_000_000_000_000_000 + seq * 1_000_000,
        "host": "bench",
        "component": component,
        "event": event,
        "seq": seq,
        "data": data,
    }


def make_run(name: str, scenario: str, fault: str) -> tuple[runio.Run, Path, str]:
    """Writes run_record.json, emits the agent log, returns the loaded run."""
    root = LIB / ".build" / "runs" / name
    if root.exists():
        shutil.rmtree(root)
    (root / "score").mkdir(parents=True)
    (root / "bench").mkdir(parents=True)

    record = {
        "contractIdentity": "de4sdv.driving.icd.v2",
        "scenario": "degradedInputOrPlan",
        "scenarioVariant": {
            "fault": fault,
            "entrySpeedMps": 10.0,
            "aaosMode": "absent",
            "checkpointCase": "pinned",
        },
        "campaignId": "wp2-agent-logic",
        "runRole": f"fault-{fault}",
        "checkpointSha256": "0" * 64,
        "configurationSha256": "1" * 64,
        "vehicleConfiguration": {"path": "config/vehicle_limits.json", "sha256": "2" * 64},
    }
    (root / "run_record.json").write_text(json.dumps(record, indent=1) + "\n")
    identity = hashlib.sha256((root / "run_record.json").read_bytes()).hexdigest()[:16]

    subprocess.run(
        [str(BINARY), "--emit-scenario", scenario, str(root), identity],
        check=True,
        stdout=subprocess.DEVNULL,
    )

    if scenario == "plan_invalid":
        injection = envelope(
            "injection",
            0,
            {
                "action": "plan_inject",
                "t_sim_ms": 6000,
                "t_mono_ns": 900_000_000_000,
                "t_real_ns": 1_794_000_000_000_000_000,
                "detail": {"planReference": f"{identity}/60", "invalid": "63"},
            },
        )
        (root / "bench" / "injection.jsonl").write_text(json.dumps(injection) + "\n")

    return runio.Run(str(root)), root, identity


# --------------------------------------------------------------------- checks
def check_plan_stale_run(run: runio.Run, identity: str) -> None:
    plans = run.plans_in("score/drivingAgent.jsonl", "in.plan")
    check(len(plans) == 80, f"in.plan records: 80 (one per step from 20 to 99), got {len(plans)}")
    check(all(p["capture_ms"] is not None for p in plans), "every in.plan carries a capture stamp")
    check(all(p["sample_count"] == 64 for p in plans), "every in.plan holds 64 pairs")
    check(
        all(cases.finite(s["acceleration"]) and cases.finite(s["curvature"])
            for p in plans for s in p["samples"]),
        "every in.plan sample is finite over acceleration and curvature",
    )
    check({p["frame"] for p in plans} == set(range(20, 60)),
          "the commander view holds the plans of frames 20..59 (the plan's own frameIndex)")
    check(max(p["frame"] for p in plans) == 59,
          "the newest plan the commander saw is frame 59 (planning stalled at 60)")
    check(all(p["reference"] == f"{identity}/{p['frame']}" for p in plans),
          "every plan reference is <runIdentity>/<frameIndex>")
    check(all(p["run_record"] == identity for p in plans),
          "every in.plan names this run's record (REQ-DRIVING-034)")
    check(all(p["producer"] == "drivingAgent/inferPlan" for p in plans),
          "every in.plan names its producer (REQ-DRIVING-015)")

    commands = run.commands()
    check(len(commands) == 80, f"out.command records: 80 (no command while kStarting), got {len(commands)}")
    check(all(c["step_capture_ms"] is not None and c["plan_capture_ms"] is not None
              for c in commands),
          "every command carries step_capture_sim_ms and plan_capture_sim_ms (C3/VC-026)")
    refs = {p["reference"] for p in plans}
    check(all(c["reference"] in refs for c in commands),
          "every command names an in.plan reference (VC-011 chain)")
    check(all(c["production_mono"] is not None for c in commands),
          "every command carries its monotonic issue time (REQ-DRIVING-032)")

    begin = run.stop_begin()
    check(begin is not None, "stop_response.begin present")
    if begin:
        check_close(begin["t_sim"], 6.3, 1e-9, "stop begins at frame 63 (plan age 400 ms)")
        check(cases.enum_name(begin["cause"], cases.CAUSES) == "kPlanStale",
              "stop cause is kPlanStale")
        check(begin["source"] == "superviseLoop", "stop source is superviseLoop")
        check(begin["t_mono"] > 0.0, "stop_response.begin has a monotonic envelope stamp (VC-029)")

    stand = run.standstill()
    check(stand is not None, "stop_response.standstill present")
    if stand:
        check(stand["t_sim"] > begin["t_sim"], "standstill follows the stop begin")

    by_frame = {m["frame"]: m for m in run.modes()}
    check(len(by_frame) == 100, f"out.mode records: 100, got {len(by_frame)}")
    names = {f: cases.enum_name(m["mode"], cases.MODES) for f, m in by_frame.items()}
    check(names[19] == "kStarting", "frame 19 is kStarting")
    check(names[20] == "kDriving", "frame 20 is the first kDriving step")
    check(names[62] == "kDriving", "frame 62 is still kDriving (plan age 300 ms)")
    check(names[63] == "kStopResponse", "frame 63 is kStopResponse")
    check(names[87] == "kStandstill" or names[88] == "kStandstill",
          "the stop reaches kStandstill")
    check(names[99] == "kStandstill", "the last step is kStandstill")
    check(cases.enum_name(by_frame[63]["cause"], cases.CAUSES) == "kPlanStale",
          "the latched cause appears on the mode record")
    check(by_frame[99]["capture_ms"] is not None and by_frame[99]["decision_mono"] is not None,
          "out.mode carries both clock marks (C9)")

    stop_commands = [c for c in commands if c["step_capture_ms"] >= 6300]
    check(len(stop_commands) == 37, f"37 stop commands (63..99), got {len(stop_commands)}")
    check(all(abs(c["accel"] - (-4.0)) <= 1e-6 for c in stop_commands),
          "every stop command is -4 m/s^2 (VC-020)")
    check(all(c["accel"] <= 0.05 for c in stop_commands),
          "no stop command pulls the vehicle (VC-022)")
    held = {round(c["steer"], 6) for c in stop_commands}
    check(len(held) == 1, f"the stop steering is held at one value, got {sorted(held)}")
    before = [c for c in commands if c["step_capture_ms"] < 6300]
    if before and stop_commands:
        check_close(stop_commands[0]["steer"], before[-1]["steer"], 1e-6,
                    "the held steering equals the last valid-plan command (VC-021)")

    # The evaluator itself, on these records.
    result = cases.vc026(run)
    if result.outcome != cases.PASS:
        print(json.dumps(result.as_dict() if hasattr(result, "as_dict") else str(result),
                         indent=1)[:2000])
    check(result.outcome == cases.PASS,
          f"cases.vc026 decides passBoundedVerification, got {result.outcome}")
    check(result.measured.get("baseline_frame") == 63,
          f"vc026 baseline frame 63, got {result.measured.get('baseline_frame')}")
    check(result.measured.get("cause") == "kPlanStale",
          f"vc026 cause kPlanStale, got {result.measured.get('cause')}")
    check_close(result.measured.get("plan_age_at_baseline_s"), 0.4, 1e-9,
                "vc026 plan age at the baseline is 400 ms")
    check_close(result.measured.get("delay_s"), 0.0, 1e-9, "vc026 stop delay is 0 ms")


def check_plan_invalid_run(run: runio.Run, identity: str) -> None:
    produced = run.plans()  # out.plan, inferPlan's view
    check(len(produced) == 80, f"out.plan records: 80 (20..99, planning continues), got {len(produced)}")
    invalid = [p for p in produced if p["frame"] == 60]
    check(len(invalid) == 1 and invalid[0]["sample_count"] == 63,
          "the invalid plan is recorded by its producer with 63 pairs")
    check(len(invalid[0]["samples"]) == 63, "the invalid plan carries 63 samples")

    commander_view = run.plans_in("score/drivingAgent.jsonl", "in.plan")
    check(all(p["sample_count"] == 64 for p in commander_view),
          "the commander view never holds the invalid plan (REQ-DRIVING-027)")
    check(all(p["reference"] != f"{identity}/60" for p in commander_view),
          "the invalid plan is not passed on to the commander")

    begin = run.stop_begin()
    check(begin is not None, "stop_response.begin present")
    if begin:
        check_close(begin["t_sim"], 6.0, 1e-9, "the stop begins at the invalid plan's step")
        check(cases.enum_name(begin["cause"], cases.CAUSES) == "kPlanInvalid",
              "the stop cause is kPlanInvalid")

    commands = run.commands()
    check(all(c["reference"] != f"{identity}/60" for c in commands),
          "no command is computed from the invalid plan")

    result = cases.vc027(run)
    if result.outcome != cases.PASS:
        print(json.dumps(result.as_dict() if hasattr(result, "as_dict") else str(result),
                         indent=1)[:2000])
    check(result.outcome == cases.PASS,
          f"cases.vc027 decides passBoundedVerification, got {result.outcome}")
    check(result.measured.get("commands_from_it") == 0,
          f"vc027 commands from the invalid plan: 0, got {result.measured.get('commands_from_it')}")
    check(result.measured.get("cause") == "kPlanInvalid",
          f"vc027 cause kPlanInvalid, got {result.measured.get('cause')}")


def check_camera_run(run: runio.Run, identity: str) -> None:
    """The brief's scenario: images of one camera withheld from step 60."""
    begin = run.stop_begin()
    check(begin is not None, "camera run: stop_response.begin present")
    if begin:
        check_close(begin["t_sim"], 6.0, 1e-9, "camera run: the stop begins at the fault step")
        check(cases.enum_name(begin["cause"], cases.CAUSES) == "kCameraMissing",
              "camera run: the stop cause is kCameraMissing")

    by_frame = {m["frame"]: cases.enum_name(m["mode"], cases.MODES) for m in run.modes()}
    check(by_frame.get(59) == "kDriving", "camera run: frame 59 is kDriving")
    check(by_frame.get(60) == "kStopResponse", "camera run: frame 60 is kStopResponse")
    check(by_frame.get(99) == "kStandstill", "camera run: the last step is kStandstill")

    commands = run.commands()
    stop_commands = [c for c in commands if c["step_capture_ms"] >= 6000]
    check(len(stop_commands) == 40, f"camera run: 40 stop commands, got {len(stop_commands)}")
    check(all(abs(c["accel"] + 4.0) <= 1e-6 for c in stop_commands),
          "camera run: every stop command is -4 m/s^2 from the fault step on")
    check(all(c["step_capture_ms"] is not None and c["plan_capture_ms"] is not None
              for c in commands),
          "camera run: every command still carries both sim stamps (C3)")

    # Orchestrator review (C2 resolved): VC-DRIVING-022's predicate, "no command
    # after T0 comes from a plan captured after T0", over the evaluators' reader.
    # Non-vacuous only if inferPlan kept planning after the stop began.
    t0_ms = 6000
    late_plans = [p for p in run.plans() if (p["capture_ms"] or 0) > t0_ms]
    check(bool(late_plans), f"camera run: plans captured after T0 exist ({len(late_plans)})")
    late_refs = {p["reference"] for p in late_plans}
    after = [c for c in commands if c["step_capture_ms"] > t0_ms]
    check(all(c["plan_capture_ms"] <= t0_ms for c in after),
          "camera run: VC-022 predicate, every command after T0 names a plan captured by T0")
    check(not any(c["reference"] in late_refs for c in after),
          "camera run: no command after T0 names a plan captured after T0")
    check(len({c["reference"] for c in after}) == 1,
          "camera run: the stop commands name one frozen plan reference")

    # The condition word itself is mine; the C2 per-camera record VC-023 reads is
    # conditionInputs', which this library does not write.
    conditions = run.events("score/drivingAgent.jsonl", "out.condition", required=False)
    first_bad = [r for r in conditions if r["data"]["bits"] != 0]
    check(bool(first_bad), "camera run: out.condition reports a non-zero bit word")
    if first_bad:
        check(first_bad[0]["data"]["frame"] == 60,
              f"camera run: the first non-zero condition word is frame 60, got "
              f"{first_bad[0]['data']['frame']}")
        check("kCameraMissing" in first_bad[0]["data"]["causes"],
              "camera run: the condition word names kCameraMissing")
    result = evaluate(run, cases.vc023)
    check(result["outcome"] == cases.INCONCL,
          f"camera run: vc023 stays inconclusive without C2 metadata, got {result['outcome']}")
    check("checkpointInputs" in str(result.get("missing", "")),
          f"camera run: vc023 names the missing C2 record, got {result.get('missing')!r}")


def evaluate(run: runio.Run, fn):
    """Runs one evaluator, as evaluate_run.py does: missing evidence is an outcome."""
    try:
        return fn(run)
    except runio.MissingEvidence as exc:
        return {"outcome": cases.INCONCL, "missing": exc.what}


def check_cases_that_need_other_components(run: runio.Run) -> None:
    """Cases whose evidence my records cannot supply must stay inconclusive."""
    modes = {m["frame"]: cases.enum_name(m["mode"], cases.MODES) for m in run.modes()}
    # VC-023: this run's fault is not a camera fault, so the case is not applicable.
    r023 = cases.vc023(run)
    check(r023.outcome == cases.NOT_APPLICABLE,
          f"vc023 is notApplicable on a plan_stale run, got {r023.outcome}")
    # VC-024: this run's fault is not a motion fault.
    r024 = cases.vc024(run)
    check(r024.outcome == cases.NOT_APPLICABLE,
          f"vc024 is notApplicable on a plan_stale run, got {r024.outcome}")
    # VC-020/021/022 need the adapter's actuation records.
    for name, fn in (("vc020", cases.vc020), ("vc021", cases.vc021), ("vc022", cases.vc022)):
        result = evaluate(run, fn)
        check(result["outcome"] == cases.INCONCL,
              f"{name} is inconclusive without the adapter records, got {result['outcome']}")
    # VC-032 needs C2's camera arrival stamps and the adapter hop.
    result = evaluate(run, cases.vc032)
    check(result["outcome"] == cases.INCONCL,
          f"vc032 is inconclusive without C2/adapter records, got {result['outcome']}")
    check("actuationAdapter" in str(result.get("missing", "")),
          f"vc032 names the missing adapter record, got {result.get('missing')!r}")
    check(modes.get(99) == "kStandstill", "the mode sequence is complete for the lo/hi frames")


# ------------------------------------------------------- field cross-check
# Every field name the record builders emit, with who reads it. "read" fields
# must appear in runio.py/cases.py; "ignored" fields must not (they are for
# humans or for another component), so a drift in either direction fails.
EMITTED = {
    "frameIndex": "read",
    "captureTime": "read",
    "productionTime": "read",
    "horizon": "read",
    "sampleCount": "read",
    "samples": "read",
    "acceleration": "read",
    "curvature": "read",
    "x": "read",
    "y": "read",
    "heading": "read",
    "producer": "read",
    "runRecord": "read",
    "planReference": "read",
    "clocks": "read",
    "mode": "read",
    "cause": "read",
    "decisionTime": "read",
    "frame": "read",
    "capture_sim_ms": "read",
    "source": "read",
    "step_capture_sim_ms": "read",
    "plan_capture_sim_ms": "read",
    "input_conditions": "read",
    "sim_ms": "read",
    "reason": "read",
    "checkpointExpectedSha256": "component",   # statePublisher -> HEALTH 41 (A5)
    "checkpointActualSha256": "component",     # statePublisher -> HEALTH 42 (A5)
    "refusalReason": "component",              # statePublisher -> HEALTH 43 (A5)
    "modeName": "human",
    "causeName": "human",
    "causeValue": "human",
    "decision_mono_s": "read",                 # runio's alternative out.mode stamp
                                               # (_pair_s base "decision_mono"); my
                                               # out.mode uses decisionTime instead
    "speedKmh": "human",
    "speedMps": "human",
    "commandLaw": "human",
    "sampleIndex": "human",
    "bits": "human",
    "causes": "human",
    "causeValues": "human",
    "code": "human",
    "expectedSha256": "human",
    "actualSha256": "human",
}


def check_field_table() -> None:
    source = (EVAL / "runio.py").read_text() + (EVAL / "cases.py").read_text()
    for key, who in EMITTED.items():
        present = f'"{key}"' in source
        if who == "read":
            check(present, f"field {key} is read by runio.py/cases.py")
        else:
            check(not present, f"field {key} is {who}-only, not read by the evaluators")
    print(f"field table: {len(EMITTED)} emitted names, "
          f"{sum(1 for w in EMITTED.values() if w == 'read')} read by the evaluators, "
          f"{sum(1 for w in EMITTED.values() if w == 'component')} consumed by statePublisher, "
          f"{sum(1 for w in EMITTED.values() if w == 'human')} for humans/log inspection")


def main() -> int:
    ensure_binary()
    stale_run, stale_root, stale_identity = make_run("plan_stale", "plan_stale", "plan_stale")
    invalid_run, invalid_root, invalid_identity = make_run(
        "plan_invalid", "plan_invalid", "plan_invalid_63")

    print(f"run (plan_stale):   {stale_root}")
    check_plan_stale_run(stale_run, stale_identity)
    print(f"run (plan_invalid): {invalid_root}")
    check_plan_invalid_run(invalid_run, invalid_identity)
    camera_run, camera_root, camera_identity = make_run(
        "camera_missing", "camera_missing", "camera_missing")
    print(f"run (camera_missing): {camera_root}")
    check_camera_run(camera_run, camera_identity)
    check_cases_that_need_other_components(stale_run)
    check_field_table()

    print(f"{CHECKS} checks, {len(FAILURES)} failures")
    for failure in FAILURES:
        print(f"  - {failure}")
    return 0 if not FAILURES else 1


if __name__ == "__main__":
    sys.exit(main())
