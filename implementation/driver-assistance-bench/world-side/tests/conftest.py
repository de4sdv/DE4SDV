"""Shared fixtures: the fake CARLA module on the path, a fake clock, a fake server and an adapter stand-in."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "fake_carla"))
sys.path.insert(0, str(HERE.parent))

import carla  # noqa: E402  (the fake)


class FakeClock:
    def __init__(self):
        self.now = 1000.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += max(0.0, seconds)

    def advance(self, seconds: float) -> None:
        self.now += seconds


class AdapterStandIn:
    """Plays the actuation adapter: a second client that finds the hero by role and applies one Ackermann
    control per 0.1 s (every second tick), by the adapter's rule speed = max(0, v + 2 a). The test sets the
    acceleration and the steering it 'receives'."""

    def __init__(self, server, target_kmh: float, steer_rad: float = 0.0, accel: float = 2.0,
                 steer_fn=None):
        self.client = carla.Client("127.0.0.1", 2000, _server=server, name="adapter")
        self.world = self.client.get_world()
        self.target = target_kmh / 3.6
        self.steer = steer_rad
        self.accel = accel
        self.steer_fn = steer_fn
        self.hero = None
        self.applied = 0
        server.pre_tick_hooks.append(self)

    def __call__(self, server) -> None:
        if self.hero is None or not self.hero.is_alive:
            heroes = [a for a in self.world.get_actors().filter("vehicle.*")
                      if a.attributes.get("role_name") == "hero"]
            self.hero = heroes[0] if heroes else None
            if self.hero is None:
                return
        if server.frame % 2:
            return
        v = math.hypot(self.hero.get_velocity().x, self.hero.get_velocity().y)
        a = self.accel if v < self.target - 0.05 else 0.0
        steer = self.steer_fn(self.hero) if self.steer_fn else self.steer
        self.hero.apply_ackermann_control(carla.VehicleAckermannControl(
            steer=steer, steer_speed=0.0, speed=max(0.0, v + 2.0 * a) if a else self.target, acceleration=a,
            jerk=10.0))
        self.applied += 1


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def server(clock):
    srv = carla._Server("Carla/Maps/Town04")
    srv.clock = clock
    return srv


@pytest.fixture
def factory(server):
    def make(host, port):
        return carla.Client(host, port, _server=server, name="world_side")
    return make


def run_main(argv, factory, clock, out=None):
    import da_world_side
    lines: list[str] = []
    rc = da_world_side.main(argv, client_factory=factory, clock=clock, sleep=clock.sleep,
                            out=out or lines.append)
    return rc, lines
