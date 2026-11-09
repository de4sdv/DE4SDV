"""Targeted mutations: a record that breaks one criterion must be judged failing.

Each test copies one fixture, changes the one thing the requirement bounds, and
asserts failObservedBehavior - not merely "not pass". These are the checks that
say the evaluators measure something rather than re-reading the fixture.
"""

from __future__ import annotations

import json

import cases
import strip
from conftest import CASE_RUN, edit_jsonl, verdict


def copied(run_for, tmp_path, name, tag):
    return strip.copy_run(run_for(name).root, tmp_path / f"{name}-{tag}")


def _jsonl(path, event, fn):
    return edit_jsonl(path, event, fn)


# ------------------------------------------- REQ-DRIVING-008 as amended on 2026-11-09
def _history_edit(run_for, tmp_path, tag, column, value):
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-008"], tag)
    state = {"done": False}

    def fn(data):
        hist = data.get("ego_motion_history")
        if not state["done"] and isinstance(hist, list) and len(hist) == 64:
            hist[-1][column] = value
            state["done"] = True
        return data
    assert edit_jsonl(d / "score/checkpointInputs.jsonl", "out.checkpoint_inputs", fn) == 1
    from runio import Run
    return verdict(Run(d), "VC-DRIVING-008")


def test_history_carrying_the_measured_yaw_rate_fails_vc008(run_for, tmp_path):
    # the old contract: the simulator's yaw rate in the history; the amended one gives it as zero
    assert _history_edit(run_for, tmp_path, "yaw", 2, 0.05).outcome == cases.FAIL


def test_history_carrying_a_curvature_fails_vc008(run_for, tmp_path):
    assert _history_edit(run_for, tmp_path, "curv", 3, 0.002).outcome == cases.FAIL


def test_history_with_zero_yaw_and_curvature_passes_vc008(run_for):
    from runio import Run
    res = verdict(Run(run_for(CASE_RUN["VC-DRIVING-008"]).root), "VC-DRIVING-008")
    assert res.outcome == cases.PASS, res
    assert res.thresholds.get("yaw_rate_given_radps") == 0.0 and res.thresholds.get("curvature_given_1pm") == 0.0


# ---------------------------------------------------------------- the five of the brief
def test_plan_published_101_ms_late_fails_vc015(run_for, tmp_path):
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-015"], "late-publish")

    def fn(data):
        if data.get("plan_frame_index") == 300:
            data["publish_mono_s"] = data["plan_production_mono_s"] + 1
        return data
    assert edit_jsonl(d / "guest/observer.jsonl", "rx.plan", fn) == 1
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-015")
    assert res.outcome == cases.FAIL
    assert res.measured["worst_latency_s"] > 0.1


def test_health_gap_of_201_ms_fails_vc017(run_for, tmp_path):
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-017"], "health-gap")
    # shift the record's own envelope stamp, not only its data
    path = d / "guest/observer.jsonl"
    out, seen = [], 0
    for line in path.read_text().splitlines():
        rec = json.loads(line)
        if rec["event"] == "rx.health" and seen == 99:
            rec["t_real_ns"] += 101_000_000
            seen += 1
        elif rec["event"] == "rx.health":
            seen += 1
        out.append(json.dumps(rec, separators=(",", ":")))
    strip._replace(path, "\n".join(out) + "\n")
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-017")
    assert res.outcome == cases.FAIL
    gap = res.measured["gaps_over_200ms"][0]["gap_s"]
    assert 0.200 < gap < 0.210


def test_stop_101_ms_after_stale_camera_fails_vc023(run_for, tmp_path):
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-023"], "late-stop")

    def fn(data):
        data["capture_sim_ms"] += 101
        return data
    assert edit_jsonl(d / "score/drivingAgent.jsonl", "stop_response.begin", fn) == 1
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-023")
    assert res.outcome == cases.FAIL, (res.outcome, res.measured)
    assert res.measured["delay_s"] > 0.1


def test_command_after_standstill_pulling_fails_vc022(run_for, tmp_path):
    base = run_for(CASE_RUN["VC-DRIVING-022"])
    T1 = base.standstill()["t_sim"]
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-022"], "pull")

    def fn(data):
        if (data.get("actuationTime") or 0) >= T1 - 1e-9:
            data["acceleration"] = 1.0
        return data
    _jsonl(d / "score/actuationAdapter.jsonl", "out.actuation_state", fn)
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-022")
    assert res.outcome == cases.FAIL, (res.outcome, res.measured)
    assert res.measured["pulling_commands_after_standstill"]


def test_replay_plans_beyond_the_on_time_spread_fail_vc018(run_for, tmp_path):
    import evaluate_campaign
    root = tmp_path / "campaign"
    root.mkdir()
    for name in ("aaos-ref1", "aaos-ref2", "aaos-late", "aaos-stopped"):
        strip.copy_run(run_for(name).root, root / name)

    def fn(data):
        if data.get("frameIndex") == 200:
            for smp in data["samples"]:
                smp["curvature"] = round(smp["curvature"] + 0.02, 6)
        return data
    assert edit_jsonl(root / "aaos-late/score/drivingAgent.jsonl", "out.plan", fn) == 1
    report = evaluate_campaign.evaluate_campaign(root)
    v = report["cases"]["VC-DRIVING-018"]
    assert v["outcome"] == cases.FAIL, v
    assert v["measured"]["late_vs_reference"]["plan_curvature"] > 0


# ---------------------------------------------------------------- more of the same kind
def test_missing_plan_step_fails_vc001(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "drop-plan")

    def fn(data):
        return None if data.get("frameIndex") == 300 else data
    assert edit_jsonl(d / "score/drivingAgent.jsonl", "out.plan", fn) == 1
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-001")
    assert res.outcome == cases.FAIL
    assert res.measured["missing_steps"] == 1


def test_doubled_plan_step_fails_vc001(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "dup-plan")
    path = d / "score/drivingAgent.jsonl"
    out, seen = [], False
    for line in path.read_text().splitlines():
        rec = json.loads(line)
        out.append(line)
        if rec["event"] == "out.plan" and rec["data"].get("frameIndex") == 300 and not seen:
            seen = True
            dup = json.loads(line)
            dup["seq"] = 999999
            out.append(json.dumps(dup, separators=(",", ":")))
    strip._replace(path, "\n".join(out) + "\n")
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-001")
    assert res.outcome == cases.FAIL
    assert res.measured["doubled_steps"] == [300]


def test_plan_age_350_ms_at_a_command_fails_vc026(run_for, tmp_path):
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-026"], "late-plan-stop")

    def fn(data):
        data["capture_sim_ms"] += 200
        return data
    edit_jsonl(d / "score/drivingAgent.jsonl", "stop_response.begin", fn)
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-026")
    assert res.outcome == cases.FAIL, (res.outcome, res.measured)
    assert res.measured["delay_s"] > 0.1


def test_adapter_stop_400_ms_after_last_command_fails_vc028(run_for, tmp_path):
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-028"], "late-adapter-stop")

    def fn(data):
        if data.get("stopInForce") == 1:
            data["actuationTime"] = round(data["actuationTime"] + 0.4, 4)
        return data
    edit_jsonl(d / "score/actuationAdapter.jsonl", "out.actuation_state", fn)
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-028")
    assert res.outcome == cases.FAIL, (res.outcome, res.measured)
    assert res.measured["delay_s"] > 0.3


def test_sample_published_150_ms_late_fails_vc016(run_for, tmp_path):
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-016"], "late-sample")

    def fn(data):
        if data.get("sample_capture_ms") == 3000:
            t = (data["sample_receipt_mono_s"] + data["sample_receipt_mono_ns"] / 1e9
                 + 0.15)
            data["publish_mono_s"] = int(t)
            data["publish_mono_ns"] = int(round((t - int(t)) * 1e9))
        return data
    assert edit_jsonl(d / "guest/observer.jsonl", "rx.vehicle_state", fn) == 1
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-016")
    assert res.outcome == cases.FAIL


def test_command_over_the_acceleration_limit_fails_vc012(run_for, tmp_path):
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-012"], "over-limit")

    def fn(data):
        if data.get("applied") == 1:
            data["acceleration"] = 4.0          # max_acceleration is 3.0
        return data
    edit_jsonl(d / "score/actuationAdapter.jsonl", "out.actuation_state", fn)
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-012")
    assert res.outcome == cases.FAIL
    assert res.measured["violation_count"] > 0


def test_deceleration_3_mps2_fails_vc020(run_for, tmp_path):
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-020"], "wrong-decel")

    def fn(data):
        if data.get("actuationTime", 0) >= 25.0:
            data["acceleration"] = -3.0
        return data
    _jsonl(d / "score/actuationAdapter.jsonl", "out.actuation_state", fn)
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-020")
    assert res.outcome == cases.FAIL
    assert res.measured["worst_deviation_mps2"] > 0.2


def test_reference_inference_off_by_half_an_mps2_fails_vc002(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "bad-reference")

    def fn(data):
        if data.get("frameIndex") == 300:
            data["acceleration"] = [a + 0.5 for a in data["acceleration"]]
        return data
    assert edit_jsonl(d / "score/referenceInference.jsonl", "reference_inference", fn) == 1
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-002")
    assert res.outcome == cases.FAIL


def test_plan_naming_another_run_record_fails_vc034(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "wrong-record")

    def fn(data):
        if data.get("frameIndex") == 300:
            data["runRecord"] = "deadbeefdeadbeef"
        return data
    assert edit_jsonl(d / "score/drivingAgent.jsonl", "out.plan", fn) == 1
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-034")
    assert res.outcome == cases.FAIL


def test_one_byte_changed_in_the_checkpoint_fails_vc033(run_for, tmp_path):
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-033"], "byte")
    p = d / "artifacts/checkpoint.bin"
    b = bytearray(p.read_bytes())
    b[3] ^= 0x01
    strip.replace_bytes(p, bytes(b))
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-033")
    assert res.outcome == cases.FAIL
    assert res.measured["problems"]


def test_checkpoint_retained_once_per_campaign_passes_vc033(run_for, tmp_path):
    """C7: the checkpoint copy is retained once per campaign, next to the run directories.
    The evaluator resolves it there when the run directory has none."""
    import shutil
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-033"], "campaign")
    shutil.move(str(d / "artifacts/checkpoint.bin"), str(d.parent / "checkpoint.bin"))
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-033")
    assert res.outcome == cases.PASS, (res.outcome, res.measured)


def test_checkpoint_retained_nowhere_makes_vc033_inconclusive(run_for, tmp_path):
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-033"], "nowhere")
    (d / "artifacts/checkpoint.bin").unlink()
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-033")
    assert res.outcome == cases.INCONCL, (res.outcome, res.measured)
    assert any("checkpointSha256" in m for m in res.missing)


# ---------------------------------------------------------------- v2-specific mutations
def test_missing_bundle_makes_only_vc002_inconclusive(run_for, tmp_path):
    """C2 sampling: a sampled plan step without its npz is missing evidence for
    VC-002; an ordinary per-step metadata case (VC-004) is unaffected."""
    d = copied(run_for, tmp_path, "nominal", "no-bundle-300")
    (d / "score/bundles/300.npz").unlink()
    from runio import Run
    run = Run(d)
    res = verdict(run, "VC-DRIVING-002")
    assert res.outcome == cases.INCONCL
    assert "300" in res.missing[0] and "bundles" in res.missing[0]
    assert "C2" in res.icd_changes
    assert verdict(run, "VC-DRIVING-004").outcome == cases.PASS


def test_vc002_reports_the_sampled_coverage(run_for):
    res = verdict(run_for("nominal"), "VC-DRIVING-002")
    assert res.outcome == cases.PASS
    assert res.measured["sampled_plan_steps"] == 12     # frames 100..650 every 50
    assert res.measured["bundles_present"] == 14        # 0..650 every 50, no fault


def test_vc029_uses_monotonic_not_real_time(run_for, tmp_path):
    """A 5 s real-time skew at the stop begin must not move the verdict: both
    ends are on the S-CORE host's monotonic clock."""
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-029"], "vc029-clock")
    path = d / "score/drivingAgent.jsonl"
    out = []
    for line in path.read_text().splitlines():
        rec = json.loads(line)
        if rec["event"] == "stop_response.begin":
            rec["t_real_ns"] -= 5_000_000_000       # real time only; t_mono stays
        out.append(json.dumps(rec, separators=(",", ":")))
    strip._replace(path, "\n".join(out) + "\n")
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-029")
    assert res.outcome == cases.PASS, (res.outcome, res.measured)
    assert res.measured["clock"].startswith("monotonic")
    assert res.measured["latency_s"] < 0.1


def test_vc029_publish_mono_1s_late_fails(run_for, tmp_path):
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-029"], "vc029-late")

    def fn(data):
        data["publish_mono_s"] += 1
        return data
    edit_jsonl(d / "score/statePublisher.jsonl", "out.health", fn)
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-029")
    assert res.outcome == cases.FAIL, (res.outcome, res.measured)
    assert res.measured["latency_s"] > 0.1


def test_vc026_uses_the_c3_log_fields(run_for, tmp_path):
    """Remove C3's two columns from out.command: 026 must be inconclusive, and
    must name C3 - it cannot fall back to the actuation, one frame late."""
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-026"], "no-c3")

    def fn(data):
        data.pop("step_capture_sim_ms", None)
        data.pop("plan_capture_sim_ms", None)
        return data
    assert edit_jsonl(d / "score/drivingAgent.jsonl", "out.command", fn) > 0
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-026")
    assert res.outcome == cases.INCONCL
    assert "C3" in res.icd_changes
    assert "step_capture_sim_ms" in res.missing[0]


# ---------------------------------------------------------------- error and missing
def test_malformed_record_gives_error_evidence(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "malformed")
    p = d / "score/drivingAgent.jsonl"
    strip.replace_bytes(p, p.read_bytes() + b'{"t_mono_ns": 1, "data": {}}\n')
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-001")
    assert res.outcome == cases.ERROR


def test_removed_file_gives_missing_evidence_not_error(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "no-agent-log")
    (d / "score/drivingAgent.jsonl").unlink()
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-001")
    assert res.outcome == cases.INCONCL
    assert res.missing


def test_unknown_scenario_selects_no_case(run_for, tmp_path):
    import evaluate_run
    d = copied(run_for, tmp_path, "nominal", "unknown-scenario")
    rec = json.loads((d / "run_record.json").read_text())
    rec["scenario"] = "noSuchScenario"
    strip._replace(d / "run_record.json",
                   json.dumps(rec, indent=1, sort_keys=True) + "\n")
    report = evaluate_run.evaluate(d)
    assert report["cases"] == {}
