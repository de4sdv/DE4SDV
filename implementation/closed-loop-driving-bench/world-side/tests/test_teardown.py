"""Teardown order (R2): the last tick's images get time to reach the agent, every actor goes while
the world is still synchronous, and the summary is on disk before teardown starts.

On the simulator host the old order (asynchronous mode restored first, actors destroyed after) let
the server run free with the cameras and the hero still in place: drivingAgent took a frame after
the run's last tick, and its images were missing."""

from __future__ import annotations

import carla
import pytest

import world_side as W
from conftest import FakeClock, RIG_PATH, read_json, run_tool


def a_client(clock):
    return carla.Client("127.0.0.1", 2000, clock=clock, map_name="Carla/Maps/Town10HD_Opt")


def run_logging_sleeps(route, profile, run_dir, client, clock, *, warmup=1.0, run_s=0.5):
    """main() with a sleep that also lands in the world's log, so it can be ordered with the ticks."""
    def sleep(seconds: float) -> None:
        client.world.log.append(("sleep", float(seconds)))
        clock.sleep(seconds)

    code = W.main(
        ["--route", str(route), "--profile", str(profile), "--rig-path", str(RIG_PATH),
         "--run-dir", str(run_dir), "--warmup-s", str(warmup), "--run-s", str(run_s),
         "--width", "640", "--front-width", "1024"],
        client_factory=lambda host, port: client, clock=clock, sleep=sleep,
        install_signals=False)
    return code


def test_every_actor_goes_while_the_world_is_still_synchronous(tmp_path, route, profile):
    clock = FakeClock()
    client = a_client(clock)
    code, _ = run_tool(route, profile, tmp_path / "run", client, clock, warmup=1.0, run_s=0.5)
    assert code == 0

    log = client.world.log
    destroys = [i for i, e in enumerate(log) if e[0] == "destroy"]
    restores = [i for i, e in enumerate(log) if e == ("settings", False)]
    assert destroys and restores
    # every destroy before the settings go back to asynchronous mode
    assert max(destroys) < min(restores)
    # and nothing ticked between the last tick and the restore: no frame after the run
    last_tick = max(i for i, e in enumerate(log) if e[0] == "tick")
    assert last_tick < min(destroys)
    assert list(client.world.get_actors()) == []
    assert client.world.get_settings().synchronous_mode is False


def test_the_last_tick_gets_time_to_arrive_before_teardown(tmp_path, route, profile):
    clock = FakeClock()
    client = a_client(clock)
    assert run_logging_sleeps(route, profile, tmp_path / "run", client, clock) == 0

    log = client.world.log
    last_tick = max(i for i, e in enumerate(log) if e[0] == "tick")
    first_teardown = min(i for i, e in enumerate(log) if e[0] in ("stop", "destroy")
                         and i > last_tick)
    waited = sum(e[1] for e in log[last_tick:first_teardown] if e[0] == "sleep")
    assert waited >= W.LAST_FRAME_DRAIN_S
    # longer than drivingAgent's 95 ms frame deadline, with margin
    assert W.LAST_FRAME_DRAIN_S >= 0.2


def test_no_wait_when_no_tick_was_made(tmp_path, route, profile):
    clock = FakeClock()
    client = a_client(clock)
    client.world.spawn_failures = {"sensor.camera.rgb"}
    assert run_logging_sleeps(route, profile, tmp_path / "run", client, clock) == 1
    assert ("sleep", W.LAST_FRAME_DRAIN_S) not in client.world.log


def test_the_summary_is_on_disk_when_teardown_dies(tmp_path, route, profile, monkeypatch):
    """A server that dies during teardown makes the client library abort the process (std::terminate
    on its timeout); in process, an exception that teardown does not catch stands in for it."""
    clock = FakeClock()
    client = a_client(clock)

    def destroy_dies(self):
        raise KeyboardInterrupt("teardown died")

    monkeypatch.setattr(carla.Actor, "destroy", destroy_dies)
    run_dir = tmp_path / "run"
    with pytest.raises(KeyboardInterrupt):
        run_tool(route, profile, run_dir, client, clock, warmup=1.0, run_s=0.5)

    summary = read_json(run_dir / "simulator" / "summary.json")
    assert summary["stopReason"] == "runDuration"
    assert summary["ticks"] > 0
