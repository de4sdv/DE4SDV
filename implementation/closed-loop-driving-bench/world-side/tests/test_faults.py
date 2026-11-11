"""R7: world-side faults (C8 camera_stop) and their C1 consequences."""

from __future__ import annotations

import carla
import pytest

import runio
import world_side as W
from conftest import (FakeClock, make_tool, read_json, read_jsonl, run_tool,
                      write_run_record)


def records(run_dir):
    return [r for r in read_jsonl(run_dir / "simulator/world.jsonl") if r["event"] == "tick"]


def camera_state(rec, name):
    return next(s for s in rec["data"]["sensors"] if s["name"] == name)


def test_camera_stop_timing_record_and_sensor_state(tmp_path, route, profile):
    clock = FakeClock()
    client = carla.Client("127.0.0.1", 2000, clock=clock)
    tool = make_tool(route, profile, tmp_path / "run", client, clock, warmup=1.0, run_s=1.0,
                     faults=("camera_stop:rear_left@0.3",))
    tool.start()
    try:
        camera = next(c for c in tool.cameras if c.slot == "rear_left")
        camera_id = camera.actor_id()
        tool.run()
        tool.write_summary()
        fh = tool.handover_frame
        fault_frame = fh + 3                      # 0.3 s after the handover frame
        summary = read_json(tmp_path / "run/simulator/summary.json")
        assert summary["faults"] == [{"fault": "camera_stop", "argument":
                                      "camera_stop:rear_left@0.3", "camera": "rear_left",
                                      "afterHandoverS": 0.3, "frame": fault_frame,
                                      "fired": True}]

        # the camera was destroyed before the tick of its frame
        log = client.world.log
        destroy_at = log.index(("destroy", camera_id, fault_frame - 1))
        tick_at = log.index(("tick", fault_frame))
        assert destroy_at < tick_at

        # C8 record
        inj = [r for r in read_jsonl(tmp_path / "run/bench/injection.jsonl")
               if r["event"] == "injection"]
        assert len(inj) == 1
        rec = inj[0]
        assert set(rec) == set(runio.ENVELOPE)
        assert (rec["host"], rec["component"], rec["event"]) == ("simulator", "worldSide",
                                                                "injection")
        data = rec["data"]
        assert data["action"] == "camera_stop"
        assert data["t_sim_ms"] == fault_frame * 100
        assert isinstance(data["t_mono_ns"], int) and isinstance(data["t_real_ns"], int)
        assert data["detail"]["camera"] == "cam_rear_left"
        assert data["detail"]["actor_id"] == camera_id
        assert data["detail"]["fault"] == "camera_missing"

        # C1 says alive=False / attached=False from that tick on, and only there
        for r in records(tmp_path / "run"):
            state = camera_state(r, "cam_rear_left")
            assert state["actor_id"] == camera_id
            if r["data"]["frame"] < fault_frame:
                assert state["alive"] is True and state["attached"] is True
            else:
                assert state["alive"] is False and state["attached"] is False
            others = [s for s in r["data"]["sensors"] if s["name"] != "cam_rear_left"]
            assert len(others) == 5
            assert all(s["alive"] and s["attached"] for s in others)

        # the evaluator's own reader
        write_run_record(tmp_path / "run", scenario="degradedInputOrPlan",
                         fault="camera_missing")
        injected = runio.Run(tmp_path / "run").injections()
        assert len(injected) == 1
        assert injected[0]["action"] == "camera_stop"
        assert injected[0]["t_sim_ms"] == fault_frame * 100
        assert injected[0]["detail"]["camera"] == "cam_rear_left"
    finally:
        tool.teardown()


def test_camera_stop_at_the_handover_frame(tmp_path, route, profile):
    clock = FakeClock()
    client = carla.Client("127.0.0.1", 2000, clock=clock)
    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock,
                             warmup=0.5, run_s=0.5,
                             faults=("camera_stop:front_right@0",))
    assert code == 0
    summary = read_json(run_dir / "simulator/summary.json")
    fh = summary["handoverFrame"]
    assert summary["faults"][0]["frame"] == fh
    at_fh = next(r for r in records(run_dir) if r["data"]["frame"] == fh)
    assert camera_state(at_fh, "cam_front_right")["alive"] is False
    before = [r for r in records(run_dir) if r["data"]["frame"] < fh]
    assert all(camera_state(r, "cam_front_right")["alive"] for r in before)


def test_a_fault_after_the_run_never_fires(tmp_path, route, profile):
    clock = FakeClock()
    client = carla.Client("127.0.0.1", 2000, clock=clock)
    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock,
                             warmup=0.2, run_s=0.3,
                             faults=("camera_stop:front@99",))
    assert code == 0
    summary = read_json(run_dir / "simulator/summary.json")
    assert summary["faults"][0]["fired"] is False
    assert summary["faults"][0]["frame"] == summary["handoverFrame"] + 990
    assert all(camera_state(r, "cam_front")["alive"] for r in records(run_dir))
    assert [r for r in read_jsonl(run_dir / "bench/injection.jsonl")
            if r["event"] == "injection"] == []


def test_fault_parser_is_extensible_and_strict():
    fault = W.parse_fault("camera_stop:cam_front_left@1.5")
    assert (fault.kind, fault.slot, fault.after_s) == ("camera_stop", "front_left", 1.5)
    assert W.parse_fault("run_end_brake").kind == "run_end_brake"
    for bad in ("camera_stop:trunk@1", "camera_stop:rear@", "camera_stop:rear@-1",
                "camera_stop:rear", "steer:1"):
        with pytest.raises(W.BenchError):
            W.parse_fault(bad)
    # a new kind is one registry entry
    W.FAULT_PARSERS["noop"] = lambda text: W.Fault("noop", text)
    try:
        assert W.parse_fault("noop").kind == "noop"
    finally:
        del W.FAULT_PARSERS["noop"]
