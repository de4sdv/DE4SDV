"""Targeted mutations: a record that breaks one criterion must be judged failing.

Each test copies one fixture, changes the one thing the requirement bounds, and
asserts failObservedBehavior - not merely "not pass". These are the checks that
say the evaluators measure something rather than re-reading the fixture.
"""

from __future__ import annotations

import json
import math

import pytest

import cases
import make_synthetic_run as synth
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


# ------------------------------------------- REQ-DRIVING-008 as amended on 2026-11-10
# The rows are compared with the speed and acceleration worked out the source's
# way (numpy.gradient at 0.1 s, rows [1:-1]) from the C1 poses of the frames
# k-65 .. k, moved to the origin of the camera rig of drivingAgent's `rig`
# record; never with the speed and acceleration the simulator reports.
AGENT = "score/drivingAgent.jsonl"
C2 = "score/checkpointInputs.jsonl"
WORLD = "simulator/world.jsonl"
LATERAL_ORIGIN = [synth.RIG_ORIGIN[0], 0.4, synth.RIG_ORIGIN[2]]   # 0.4 m to the right


def _vc008(d):
    from runio import Run
    return verdict(Run(d), "VC-DRIVING-008")


def _poses(d) -> dict:
    """{frame: egoPose} of a run directory's C1 record."""
    out = {}
    for line in (d / WORLD).read_text().splitlines():
        if line.strip():
            rec = json.loads(line)
            out[rec["data"]["frame"]] = rec["data"]["egoPose"]
    return out


def _source_rows(poses: dict, k: int, origin) -> list:
    """The rows of step k from the poses of frames k-65 .. k (the generator's own)."""
    return synth.ego_motion_rows([poses[g] for g in range(k - 65, k + 1)], origin)


def _set_rows(d, rows_for) -> int:
    """Every step with rows gets rows_for(step frame)."""
    def fn(data):
        if data["ego_motion_history"]:
            data["ego_motion_history"] = rows_for(data["frame"])
        return data
    return edit_jsonl(d / C2, "out.checkpoint_inputs", fn)


def _set_rig_origin(d, origin) -> None:
    def fn(data):
        data["result"]["origin"] = list(origin)
        return data
    edit_jsonl(d / AGENT, "rig", fn)


def _slow_turn(run_for, tmp_path, tag, rig_origin, rows_origin):
    """The nominal run with every pose on a 4 m circle at 2 m/s, turning at
    0.5 rad/s, the rig at `rig_origin` and every step's rows worked out at
    `rows_origin`."""
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-008"], tag)
    radius, speed = 4.0, 2.0

    def tick(data):
        th = speed / radius * data["frame"] * synth.STEP_S
        data["egoPose"] = {"x": round(radius * math.sin(th), 4),
                           "y": round(radius * (1.0 - math.cos(th)), 4), "yaw": round(th, 6)}
        return data
    assert edit_jsonl(d / WORLD, "tick", tick) > 0
    _set_rig_origin(d, rig_origin)
    poses = _poses(d)
    assert _set_rows(d, lambda k: _source_rows(poses, k, rows_origin)) > 0
    return _vc008(d)


def test_vc008_reports_the_rig_origin_it_moved_the_poses_to(run_for):
    run = run_for(CASE_RUN["VC-DRIVING-008"])
    res = _vc008(run.root)
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert res.measured["rig_origin_m"] == synth.RIG_ORIGIN
    assert res.measured["worst_abs_error"]["speed"] < 1e-5, res.measured
    assert res.measured["worst_abs_error"]["accel"] < 1e-5, res.measured
    rig = run.events(AGENT, "rig")[0]
    assert {"file": AGENT, "seq": rig["seq"]} in res.evidence, res.evidence


def test_vc008_passes_where_the_reported_speed_jumps_at_the_start(run_for, tmp_path):
    # At a start from standstill CARLA's reported speed and acceleration are not
    # what the poses show; the case does not compare with them.
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-008"], "startup-jump")

    def fn(data):
        if 60 <= data["frame"] <= 80:
            data["velocity"]["speed_mps"] = round(data["velocity"]["speed_mps"] + 0.5, 6)
            data["acceleration"]["longitudinal_mps2"] = 4.0
        return data
    assert edit_jsonl(d / WORLD, "tick", fn) == 21
    res = _vc008(d)
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)


def test_vc008_needs_no_reported_speed_or_acceleration(run_for, tmp_path):
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-008"], "no-reported-kinematics")

    def fn(data):
        data.pop("velocity")
        data.pop("acceleration")
        return data
    assert edit_jsonl(d / WORLD, "tick", fn) > 0
    res = _vc008(d)
    assert res.outcome == cases.PASS, (res.outcome, res.missing, res.measured)


def test_vc008_rows_at_the_rig_origin_pass_on_a_slow_turn(run_for, tmp_path):
    res = _slow_turn(run_for, tmp_path, "turn-rig", synth.RIG_ORIGIN, synth.RIG_ORIGIN)
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)


def test_vc008_rows_at_the_vehicle_origin_fail_on_a_slow_turn(run_for, tmp_path):
    # 1.39 m behind the vehicle origin, the rig origin moves at about 2.12 m/s
    res = _slow_turn(run_for, tmp_path, "turn-vehicle", synth.RIG_ORIGIN, [0.0, 0.0, 0.0])
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    assert 0.11 < res.measured["worst_abs_error"]["speed"] < 0.125, res.measured
    assert res.measured["records_with_a_problem"] == res.measured["records"]


def test_vc008_a_lateral_rig_origin_passes_with_its_sign(run_for, tmp_path):
    res = _slow_turn(run_for, tmp_path, "lateral", LATERAL_ORIGIN, LATERAL_ORIGIN)
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert res.measured["rig_origin_m"] == LATERAL_ORIGIN


def test_vc008_a_lateral_rig_origin_with_the_wrong_sign_fails(run_for, tmp_path):
    # the rig origin's y is to the right (vehicle axes); taken to the left it is
    # 0.8 m off, and on this turn about 0.38 m/s slower
    flipped = [LATERAL_ORIGIN[0], -LATERAL_ORIGIN[1], LATERAL_ORIGIN[2]]
    res = _slow_turn(run_for, tmp_path, "lateral-flipped", LATERAL_ORIGIN, flipped)
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    assert 0.37 < res.measured["worst_abs_error"]["speed"] < 0.39, res.measured


def test_vc008_source_rows_one_frame_late_fail(run_for, tmp_path):
    # The source's rows of frames k-63 .. k: the newest at the step, not 100 ms
    # before it. While the vehicle speeds up by 0.15 m/s a frame they are off by that.
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-008"], "rows-late")
    poses = _poses(d)
    last = max(poses)
    assert _set_rows(d, lambda k: _source_rows(poses, min(k + 1, last), synth.RIG_ORIGIN)) > 0
    res = _vc008(d)
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    assert 0.14 < res.measured["worst_abs_error"]["speed"] < 0.16, res.measured
    assert all(p["problems"][0].startswith("sample frame") for p in res.measured["problems"])


@pytest.mark.parametrize("column, offset, outcome", [
    (0, 0.04, cases.PASS), (0, 0.06, cases.FAIL),
    (1, 0.09, cases.PASS), (1, 0.11, cases.FAIL)])
def test_vc008_tolerance_edges(run_for, tmp_path, column, offset, outcome):
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-008"], f"tolerance-{column}-{offset}")

    def fn(data):
        for row in data["ego_motion_history"]:
            row[column] = round(row[column] + offset, 6)
        return data
    assert edit_jsonl(d / C2, "out.checkpoint_inputs", fn) > 0
    res = _vc008(d)
    assert res.outcome == outcome, (res.outcome, res.measured, res.notes)
    worst = res.measured["worst_abs_error"]["speed" if column == 0 else "accel"]
    assert abs(worst - offset) < 1e-5, res.measured      # the offset, nothing else


def test_vc008_a_null_speed_in_a_row_fails(run_for, tmp_path):
    # ICD section 6: JSON null is a non-finite value, never within 0.05 m/s
    res = _history_edit(run_for, tmp_path, "null-speed", 0, None)
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)


def test_vc008_without_the_rig_record_is_inconclusive(run_for, tmp_path):
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-008"], "no-rig")
    assert edit_jsonl(d / AGENT, "rig", lambda data: None) == 1
    res = _vc008(d)
    assert res.outcome == cases.INCONCL, (res.outcome, res.measured, res.notes)
    assert any(AGENT in m and "rig" in m and "result.origin" in m for m in res.missing), res.missing


def test_vc008_reads_a_rig_result_logged_as_a_json_string(run_for, tmp_path):
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-008"], "rig-string")

    def fn(data):
        data["result"] = json.dumps(data["result"])
        return data
    assert edit_jsonl(d / AGENT, "rig", fn) == 1
    res = _vc008(d)
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert res.measured["rig_origin_m"] == synth.RIG_ORIGIN


@pytest.mark.parametrize("frame, records", [(0, 1), (300, 66)])
def test_vc008_a_missing_tick_in_a_window_fails_naming_its_frame(run_for, tmp_path,
                                                                   frame, records):
    # frame 0 is only the oldest pose of the first plan's window (step 65), no row's
    # frame; frame 300 is in the windows of steps 300 .. 365
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-008"], f"no-tick-{frame}")
    assert edit_jsonl(d / WORLD, "tick",
                      lambda data: None if data["frame"] == frame else data) == 1
    res = _vc008(d)
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    assert res.measured["records_with_a_problem"] == records, res.measured
    first = res.measured["problems"][0]
    assert first["frame"] == max(frame, 65), first
    assert first["problems"] == [f"no world tick for frame {frame}"], first


def test_vc008_names_its_amendment():
    import gaps
    assert "A29" in gaps.amendments_for("VC-DRIVING-008")


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
def test_two_consecutive_steps_without_a_plan_fail_vc001(run_for, tmp_path):
    # REQ-DRIVING-001 as amended: one step without its own plan is allowed, two are not
    d = copied(run_for, tmp_path, "nominal", "drop-plans")

    def fn(data):
        return None if data.get("frameIndex") in (300, 301) else data
    assert edit_jsonl(d / "score/drivingAgent.jsonl", "out.plan", fn) == 2
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-001")
    assert res.outcome == cases.FAIL
    assert res.measured.get("failing_pairs") == [[300, 301]], res.measured
    assert res.measured["longest_run_without_a_new_plan"] == 2


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
