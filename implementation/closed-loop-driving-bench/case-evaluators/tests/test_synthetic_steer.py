"""The synthetic runs write CARLA's steer as the adapter applies it (ICD A30).

The adapter's steer is the commanded road-wheel angle over the vehicle's maximum steering angle,
the front wheels' max_steer_angle CARLA reports (70 degrees for vehicle.lincoln.mkz_2020), not over
the configured command limit (35 degrees). No case reads the steer, so these tests pin the fixture
alone: a synthetic record must not teach a later case the old scale, and the world's view of the
control must be the control the adapter applied.
"""

from __future__ import annotations

import json
from pathlib import Path

MKZ_MAX_STEER_ANGLE_DEG = 70.0


def records(path: Path, event: str) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    return [row for row in rows if row["event"] == event]


def test_the_adapters_steer_is_the_angle_over_the_vehicles_maximum(fixture_root):
    path = fixture_root / "nominal" / "score" / "actuationAdapter.jsonl"
    with path.open(encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    angle, pairs = None, []
    for row in rows:
        if row["event"] == "out.actuation_state":
            angle = row["data"]["steeringAngle"]
        elif row["event"] == "out.vehicle_control" and row["data"]["trigger"] == "command":
            pairs.append((angle, row["data"]["steer"]))
    turning = [pair for pair in pairs if pair[0] is not None and abs(pair[0]) > 0.1]
    assert len(pairs) > 100 and len(turning) > 10, (len(pairs), len(turning))
    wrong = [(a, s) for a, s in pairs if a is None or abs(s + a / MKZ_MAX_STEER_ANGLE_DEG) > 1e-6]
    assert not wrong, wrong[:5]


def test_the_worlds_steer_is_a_steer_the_adapter_applied(fixture_root):
    run = fixture_root / "nominal"
    applied = {row["data"]["steer"]
               for row in records(run / "score" / "actuationAdapter.jsonl", "out.vehicle_control")}
    world = [row["data"]["control"]["steer"] for row in records(run / "simulator" / "world.jsonl", "tick")]
    turning = [steer for steer in world if steer != 0.0]
    assert len(turning) > 10, len(turning)
    foreign = sorted({steer for steer in turning if steer not in applied})
    assert not foreign, foreign[:5]
