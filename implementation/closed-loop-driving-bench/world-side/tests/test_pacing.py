"""R3: real-time pacing on an injected clock (no sleeping in the tests)."""

from __future__ import annotations

import carla
import pytest

import world_side as W
from conftest import FakeClock, read_json, read_jsonl, run_tool


def records(run_dir):
    return [r for r in read_jsonl(run_dir / "simulator/world.jsonl") if r["event"] == "tick"]


def test_one_tick_per_hundred_ms_of_wall_time(tmp_path, route, profile):
    clock = FakeClock()
    client = carla.Client("127.0.0.1", 2000, clock=clock)
    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock,
                             warmup=1.0, run_s=1.0)
    assert code == 0
    summary = read_json(run_dir / "simulator/summary.json")
    ticks = summary["ticks"]
    assert ticks == 20                       # 10 warm-up + 10 run ticks
    assert summary["lateTicks"] == 0
    assert summary["scheduleSlips"] == 0
    # sleeps are all one period and the wall time is (ticks - 1) periods; the last sleep is
    # teardown's wait for the last tick's images, after the wall time ends
    assert clock.sleeps[-1] == W.LAST_FRAME_DRAIN_S
    assert all(abs(s - 0.1) < 1e-9 for s in clock.sleeps[1:-1])
    assert abs(summary["wallSeconds"] - (ticks - 1) * 0.1) < 1e-6
    assert 0.99 < summary["realTimeFactor"] < 1.06
    assert all(r["data"]["latenessMonoNs"] == 0 for r in records(run_dir))


def test_a_slow_tick_moves_the_schedule_and_is_counted(tmp_path, route, profile):
    """A tick that overruns must not be followed by a burst of catch-up ticks."""
    clock = FakeClock()
    client = carla.Client("127.0.0.1", 2000, clock=clock)
    client.world.tick_cost_s = 0.13
    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock,
                             warmup=0.5, run_s=1.0)
    assert code == 0
    summary = read_json(run_dir / "simulator/summary.json")
    ticks = summary["ticks"]
    assert ticks == 15
    assert summary["scheduleSlips"] == ticks      # every tick overran its next slot
    assert summary["maxSlipMonoNs"] >= 30_000_000
    assert summary["realTimeFactor"] < 0.8
    # wall time is the sum of the overruns, not one period per tick
    assert abs(summary["wallSeconds"] - ticks * 0.13) < 1e-6
    assert clock.sleeps[-1] == W.LAST_FRAME_DRAIN_S   # teardown's wait, after the run
    assert all(s < 1e-9 for s in clock.sleeps[:-1]), "a late tick must not burst"

    recs = [r["data"] for r in records(run_dir)]
    assert len(recs) == ticks
    assert all(r["tickDurationMonoNs"] == 130_000_000 for r in recs)
    # the tick count proves the schedule followed the wall clock, not the frame count
    assert recs[-1]["frame"] - recs[0]["frame"] + 1 == ticks


def test_a_late_wake_is_counted_and_logged(tmp_path, route, profile):
    clock = FakeClock(overshoot_s=0.005)
    client = carla.Client("127.0.0.1", 2000, clock=clock)
    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock,
                             warmup=0.5, run_s=0.5)
    assert code == 0
    summary = read_json(run_dir / "simulator/summary.json")
    assert summary["lateTicks"] == summary["ticks"] - 1     # every tick after the first
    assert summary["scheduleSlips"] == 0
    assert abs(summary["maxLatenessMonoNs"] - 5_000_000) < 1000
    recs = [r["data"] for r in records(run_dir)]
    assert recs[0]["latenessMonoNs"] == 0
    assert all(abs(r["latenessMonoNs"] - 5_000_000) < 1000 for r in recs[1:])


def test_the_pacer_never_runs_a_tick_before_its_deadline():
    clock = FakeClock()
    pacer = W.Pacer(clock=clock, sleep=clock.sleep)
    pacer.start()
    starts = []
    for _ in range(5):
        start, lateness = pacer.wait_turn()
        starts.append(start)
        clock.advance(0.02)                 # the tick itself
        pacer.finish_turn(clock())
    assert starts == pytest.approx([1000.0, 1000.1, 1000.2, 1000.3, 1000.4], abs=1e-9)
    assert pacer.ticks == 5 and pacer.schedule_slips == 0 and pacer.late_ticks == 0
