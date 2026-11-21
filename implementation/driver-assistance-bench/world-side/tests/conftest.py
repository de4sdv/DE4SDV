"""Shared fixtures: the fake CARLA module on the path, a fake clock, a fake server.

Helpers that tests import by name (AdapterStandIn, run_main) live in world_side_testkit.py, never here: pytest
imports every test directory's conftest.py under the one module name `conftest`
(session/tests/test_bench_collection.py).
"""

from __future__ import annotations

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


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def server(clock):
    srv = carla._Server("Carla/Maps/Town06_Opt")
    srv.clock = clock
    return srv


@pytest.fixture
def factory(server):
    def make(host, port):
        return carla.Client(host, port, _server=server, name="world_side")
    return make
