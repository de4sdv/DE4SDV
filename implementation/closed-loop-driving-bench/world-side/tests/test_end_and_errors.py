"""R9 run end reasons, R10 loud errors, and the CLI entry point."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading

import carla
import pytest

import world_side as W
from conftest import (BENCH, FakeClock, RIG_PATH, make_tool, read_json, read_jsonl,
                      run_tool, write_route, write_profile)

WORLD_SIDE = BENCH / "world-side" / "world_side.py"


def records(run_dir):
    return [r for r in read_jsonl(run_dir / "simulator/world.jsonl") if r["event"] == "tick"]


# --------------------------------------------------------------------- R9: end


def test_stop_after_the_run_duration(tmp_path, route, profile):
    clock = FakeClock()
    client = carla.Client("127.0.0.1", 2000, clock=clock)
    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock,
                             warmup=1.0, run_s=0.5)
    assert code == 0
    summary = read_json(run_dir / "simulator/summary.json")
    assert summary["stopReason"] == "runDuration"
    assert summary["handoverFrame"] == summary["firstFrame"] + 10
    assert summary["lastFrame"] == summary["handoverFrame"] + 5 - 1
    assert summary["ticks"] == 15
    first = summary["firstFrame"]
    assert first == W.SETTLE_MIN_TICKS + 1          # after the setup ticks
    assert [r["data"]["frame"] for r in records(run_dir)] == list(range(first, first + 15))
    stop = [r for r in read_jsonl(run_dir / "simulator/worldSide.jsonl")
            if r["event"] == "stop"]
    assert stop and stop[-1]["data"]["stopReason"] == "runDuration"


def test_stop_at_the_route_destination(tmp_path, profile):
    # destination at the spawn point: the first tick after the handover is inside 5 m
    route = write_route(tmp_path / "route.json", destination=(0.0, 0.0))
    clock = FakeClock()
    client = carla.Client("127.0.0.1", 2000, clock=clock)
    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock,
                             warmup=0.3, run_s=10.0)
    assert code == 0
    summary = read_json(run_dir / "simulator/summary.json")
    assert summary["stopReason"] == "routeEnd"
    assert summary["lastFrame"] == summary["firstFrame"] + 1
    assert summary["ticks"] == 2


def test_stop_on_a_stop_request(tmp_path, route, profile):
    clock = FakeClock()
    client = carla.Client("127.0.0.1", 2000, clock=clock)
    stop = threading.Event()

    first = W.SETTLE_MIN_TICKS + 1                  # the run's first frame, after setup

    def hook(world, frame):
        if frame == first + 4:
            stop.set()

    client.world.motion_hook = hook
    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock,
                             warmup=0.2, run_s=10.0, stop_requested=stop)
    assert code == 0
    summary = read_json(run_dir / "simulator/summary.json")
    assert summary["stopReason"] == "interrupt"
    assert summary["lastFrame"] == first + 4
    assert summary["ticks"] == 5


def test_stop_on_ctrl_c(tmp_path, route, profile):
    clock = FakeClock()
    client = carla.Client("127.0.0.1", 2000, clock=clock)

    def hook(world, frame):
        if frame == 4:
            raise KeyboardInterrupt

    client.world.motion_hook = hook
    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock,
                             warmup=0.2, run_s=10.0)
    assert code == 0
    summary = read_json(run_dir / "simulator/summary.json")
    assert summary["stopReason"] == "interrupt"
    assert summary["done"] is True
    assert client.world.get_settings().synchronous_mode is False
    assert list(client.world.get_actors()) == []


def test_sigint_handler_requests_a_stop():
    stop = threading.Event()
    previous = signal.getsignal(signal.SIGINT)
    try:
        W.install_stop_handlers(stop)
        handler = signal.getsignal(signal.SIGINT)
        assert callable(handler)
        assert not stop.is_set()
        handler(signal.SIGINT, None)
        assert stop.is_set()
    finally:
        signal.signal(signal.SIGINT, previous)


# -------------------------------------------------------------------- R10: errors


def test_missing_route_is_loud(tmp_path, profile):
    clock = FakeClock()
    code, run_dir = run_tool(tmp_path / "nope.json", profile, tmp_path / "run",
                             carla.Client("127.0.0.1", 2000, clock=clock), clock)
    assert code == 1
    errors = [r for r in read_jsonl(run_dir / "simulator/worldSide.jsonl")
              if r["event"] == "error"]
    assert "route file" in errors[0]["data"]["reason"]


def test_missing_profile_is_loud(tmp_path, route):
    clock = FakeClock()
    client = carla.Client("127.0.0.1", 2000, clock=clock)
    code, run_dir = run_tool(route, tmp_path / "nope.json", tmp_path / "run", client, clock)
    assert code == 1
    errors = [r for r in read_jsonl(run_dir / "simulator/worldSide.jsonl")
              if r["event"] == "error"]
    assert "camera profile not found" in errors[0]["data"]["reason"]
    assert client.world.spawned == []           # nothing was spawned


def test_hero_spawn_failure_is_loud_and_tears_down(tmp_path, route, profile):
    clock = FakeClock()
    client = carla.Client("127.0.0.1", 2000, clock=clock)
    client.world.spawn_failures = {"vehicle.lincoln.mkz_2020"}
    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock)
    assert code == 1
    errors = [r for r in read_jsonl(run_dir / "simulator/worldSide.jsonl")
              if r["event"] == "error"]
    assert "cannot spawn the hero" in errors[0]["data"]["reason"]
    assert client.world.get_settings().synchronous_mode is False
    assert client.traffic_managers[8000].synchronous is False
    assert list(client.world.get_actors()) == []
    assert read_json(run_dir / "simulator/summary.json")["stopReason"] == "error"


def test_map_load_failure_is_loud(tmp_path, route, profile):
    clock = FakeClock()
    client = carla.Client("127.0.0.1", 2000, clock=clock, map_name="Carla/Maps/Town01")
    client.load_failure = "server refused"
    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock)
    assert code == 1
    errors = [r for r in read_jsonl(run_dir / "simulator/worldSide.jsonl")
              if r["event"] == "error"]
    assert "cannot load map" in errors[0]["data"]["reason"]
    assert client.world.get_settings().synchronous_mode is False


def test_vehicle_configuration_names_the_blueprint(tmp_path, route, profile):
    config = tmp_path / "vehicle.json"
    config.write_text(json.dumps({"vehicle_blueprint": "vehicle.tesla.model3",
                                  "max_acceleration_mps2": 3.0}))
    clock = FakeClock()
    client = carla.Client("127.0.0.1", 2000, clock=clock)
    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock,
                             warmup=0.2, run_s=0.2,
                             extra=("--vehicle-config", str(config)))
    assert code == 0
    heroes = [s for s in client.world.spawned if s["type_id"] == "vehicle.tesla.model3"]
    assert heroes and heroes[0]["attributes"]["role_name"] == "hero"


# ------------------------------------------------------------------------- CLI


def test_cli_dry_run_as_a_subprocess(tmp_path, route, profile):
    result = subprocess.run(
        [sys.executable, str(WORLD_SIDE), "--dry-run", "--route", str(route),
         "--profile", str(profile), "--rig-path", str(RIG_PATH),
         "--run-dir", str(tmp_path / "run")],
        capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    assert "world side plan" in result.stdout
    assert "first tick frame + 0" in result.stdout   # default: no warm-up
    assert not (tmp_path / "run").exists()


def test_cli_error_exits_non_zero_as_a_subprocess(tmp_path, profile):
    result = subprocess.run(
        [sys.executable, str(WORLD_SIDE), "--route", str(tmp_path / "missing.json"),
         "--profile", str(profile), "--rig-path", str(RIG_PATH),
         "--run-dir", str(tmp_path / "run")],
        capture_output=True, text=True, timeout=120)
    assert result.returncode == 1
    assert "route file" in result.stderr
    errors = [r for r in read_jsonl(tmp_path / "run/simulator/worldSide.jsonl")
              if r["event"] == "error"]
    assert errors and "route file" in errors[0]["data"]["reason"]


def test_python_3_10_syntax(tmp_path):
    """The simulator host runs Python 3.10; compile with it when it is installed."""
    import shutil

    python310 = shutil.which("python3.10")
    if python310 is None:
        pytest.skip("python3.10 is not installed on this host")
    result = subprocess.run(
        [python310, "-c",
         "import sys; compile(open(sys.argv[1]).read(), sys.argv[1], 'exec')",
         str(WORLD_SIDE)],
        capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
