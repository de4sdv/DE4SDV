"""The actuation adapter's shell against a fake simulator client, with independent expectations.

tests/shell_driver.cpp runs the real shell, core and records with the fake client of
tests/fake_simulator_client.cpp. This test builds every command's 24 bytes with Python's struct and
its check value with zlib.crc32 (the ICD's CRC-32 over the first 20 bytes), and computes every
expected Ackermann control with Python's math from MAP-DRIVING-DA-COMMAND's rule, rounded to the
float32 that CARLA's VehicleAckermannControl holds. Nothing here is taken from the C++ sources.
The bytes are little-endian, as on the hosts that run this test (x86_64, aarch64).
"""

from __future__ import annotations

import json
import math
import shutil
import struct
import subprocess
import zlib
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ADAPTER = HERE.parent
INCLUDE = ADAPTER.parent / "interfaces" / "include"
SOURCES = [
    HERE / "shell_driver.cpp",
    HERE / "fake_simulator_client.cpp",
    ADAPTER / "adapter_shell.cpp",
    ADAPTER / "actuation_core.cpp",
]


def f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def command(seq: int, issue: float, acceleration: float = 0.0, steering: float = 0.0,
            corrupt: bool = False) -> str:
    body = struct.pack("<ffdI", acceleration, steering, issue, seq)
    crc = zlib.crc32(body) & 0xFFFFFFFF
    if corrupt:
        crc ^= 0x00000100
    return "cmd " + (body + struct.pack("<I", crc)).hex()


def expected_control(acceleration: float, steering: float, v: float) -> dict[str, float]:
    a = f32(acceleration)  # the payload's float
    s = f32(steering)
    return {
        "steer": f32(-s * math.pi / 180.0),
        "steerSpeed": 0.0,
        "speed": f32(max(0.0, v + 2.0 * a)),
        "acceleration": f32(a),
        "jerk": 10.0,
    }


@pytest.fixture(scope="module")
def driver(tmp_path_factory: pytest.TempPathFactory) -> Path:
    compiler = shutil.which("g++")
    if compiler is None:
        pytest.skip("g++ is not installed")
    binary = tmp_path_factory.mktemp("shell") / "shell_driver"
    subprocess.run(
        [str(compiler), "-std=c++17", "-Wall", "-Wextra", "-Werror", "-pedantic", f"-I{ADAPTER}",
         f"-I{HERE}", f"-I{INCLUDE}", *map(str, SOURCES), "-o", str(binary)],
        check=True,
    )
    return binary


def run(driver: Path, tmp_path: Path, script: list[str]) -> tuple[list[dict], list[dict]]:
    log = tmp_path / "actuationAdapter.jsonl"
    result = subprocess.run([str(driver), str(log)], input="\n".join(script) + "\n",
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    applied = [json.loads(line) for line in result.stdout.splitlines()]
    records = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    for record in records:
        assert set(record) == {"t_mono_ns", "t_real_ns", "host", "component", "event", "seq", "data"}
        assert record["component"] == "actuationAdapter"
    assert [r["seq"] for r in records] == list(range(1, len(records) + 1))
    return applied, records


def events(records: list[dict], name: str) -> list[dict]:
    return [r["data"] for r in records if r["event"] == name]


SPEED_VECTORS = [  # (v, acceleration): includes the clamp at 0
    (0.0, 0.0), (5.56, 0.0), (5.56, 1.2), (5.56, -2.78), (5.56, -2.79), (5.56, -5.0),
    (16.67, -5.0), (16.67, -8.335), (16.67, -9.0), (0.0, -0.3), (11.1, 0.75), (2.0, -0.999),
]
STEERING_VECTORS = [0.0, 0.5, -0.5, 3.75, -3.75, 12.0, -12.0, 35.0, -35.0, 89.9]


def test_speed_rule_vectors(driver: Path, tmp_path: Path) -> None:
    script = []
    for index, (v, a) in enumerate(SPEED_VECTORS):
        t = round(0.05 * (index + 1), 2)
        script += [f"world {index + 1} {t!r} {v!r}", command(index + 1, t, a, 0.0)]
    applied, records = run(driver, tmp_path, script)
    assert len(applied) == len(SPEED_VECTORS)
    for (v, a), got in zip(SPEED_VECTORS, applied):
        want = expected_control(a, 0.0, v)
        assert got == want, (v, a, got, want)
        assert got["speed"] >= 0.0
    clamped = [got for (v, a), got in zip(SPEED_VECTORS, applied) if v + 2 * a < 0]
    assert len(clamped) == 4 and all(got["speed"] == 0.0 for got in clamped)
    assert events(records, "out.ackermann_control") == [
        {**{k: g[k] for k in g}, "frame": i + 1, "t_sim_s": round(0.05 * (i + 1), 2), "seq": i + 1,
         "controlSource": "actuationAdapter"}
        for i, g in enumerate(applied)
    ]


def test_steering_sign_vectors(driver: Path, tmp_path: Path) -> None:
    script = ["world 1 0.05 8.0"]
    for index, steering in enumerate(STEERING_VECTORS):
        script.append(command(index + 1, 0.05, 0.0, steering))
    applied, _ = run(driver, tmp_path, script)
    assert len(applied) == len(STEERING_VECTORS)
    for steering, got in zip(STEERING_VECTORS, applied):
        assert got == expected_control(0.0, steering, 8.0)
        # The command is positive to the left; CARLA's steer is positive to the right.
        if steering > 0:
            assert got["steer"] < 0
        elif steering < 0:
            assert got["steer"] > 0


def test_each_rejection_reason_and_nothing_applied(driver: Path, tmp_path: Path) -> None:
    script = [
        "world 249 12.45 5.0",
        command(1, 12.35, -1.0, 2.0),           # accepted
        command(1, 12.35, -1.0, 2.0),           # repetition
        command(2, 12.35, -6.0, 20.0, True),    # corruption
        command(2, 12.30, -6.0, 20.0),          # delay: 150 ms
        command(4, 12.45, -6.0, 20.0),          # loss
        command(5, 12.45, -6.0, 20.0),          # loss: the last accepted is still 1
    ]
    applied, records = run(driver, tmp_path, script)
    assert applied == [expected_control(-1.0, 2.0, 5.0)]
    assert [d["reason"] for d in events(records, "drop")] == [
        "repetition", "corruption", "delay", "loss", "loss"]
    verdicts = [(d["seq"], d["crc_ok"], d["verdict"]) for d in events(records, "in.driving_command")]
    assert verdicts == [(1, True, "accepted"), (1, True, "rejected"), (2, False, "rejected"),
                        (2, True, "rejected"), (4, True, "rejected"), (5, True, "rejected")]
    assert len(events(records, "out.ackermann_control")) == 1


def test_a_gap_against_a_repeat(driver: Path, tmp_path: Path) -> None:
    script = ["world 10 0.5 3.0", command(1, 0.5), command(2, 0.5), command(2, 0.5), command(3, 0.5),
              command(5, 0.5), command(4, 0.5)]
    applied, records = run(driver, tmp_path, script)
    assert len(applied) == 4  # 1, 2, 3 and the late 4
    drops = events(records, "drop")
    assert [(d["seq"], d["reason"], d["lastAcceptedSeq"]) for d in drops] == [
        (2, "repetition", 2), (5, "loss", 3)]


def boundary_pairs() -> list[tuple[float, float]]:
    """Two 0.05 s steps apart, yet more than 0.1 apart as doubles."""
    literal = [(12.55, 12.45), (12.05, 11.95), (0.4, 0.3), (1.05, 0.95)]
    steps = [0.0]
    for _ in range(300):
        steps.append(steps[-1] + 0.05)
    accumulated = [(steps[k], steps[k - 2]) for k in (3, 13, 241, 300)]
    pairs = literal + accumulated
    assert all(newest - issue > 0.1 for newest, issue in pairs)
    return pairs


def test_delay_boundary_misses_exactly_one_tenth(driver: Path, tmp_path: Path) -> None:
    script = []
    for index, (newest, issue) in enumerate(boundary_pairs()):
        script += [f"world {index + 1} {newest!r} 2.0", command(index + 1, issue, 0.5)]
    applied, records = run(driver, tmp_path, script)
    assert len(applied) == len(boundary_pairs())
    assert events(records, "drop") == []
    issue_times = [d["issueTime_sim_s"] for d in events(records, "in.driving_command")]
    assert issue_times == [issue for _, issue in boundary_pairs()]


def test_delay_just_above_one_tenth(driver: Path, tmp_path: Path) -> None:
    script = ["world 1 12.45 2.0", command(1, 12.349), "world 2 12.5 2.0", command(1, 12.35)]
    applied, records = run(driver, tmp_path, script)
    assert applied == []
    assert [d["reason"] for d in events(records, "drop")] == ["delay", "delay"]


def test_first_command_of_a_run(driver: Path, tmp_path: Path) -> None:
    script = [command(1, 0.0), "world 1 0.05 0.0", command(2, 0.05), command(1, 0.05, 1.0)]
    applied, records = run(driver, tmp_path, script)
    # Before any snapshot the age cannot be shown: a delay; then 2 is a loss; then 1 is accepted.
    assert [d["reason"] for d in events(records, "drop")] == ["delay", "loss"]
    first = events(records, "in.driving_command")[0]
    assert first["newestWorldTime_sim_s"] is None and first["newestWorldFrame"] is None
    assert applied == [expected_control(1.0, 0.0, 0.0)]


def test_no_ego_vehicle_in_the_snapshot(driver: Path, tmp_path: Path) -> None:
    applied, records = run(driver, tmp_path, ["noego 1 0.05", command(1, 0.05)])
    assert applied == []
    assert [r["event"] for r in records] == ["in.world_snapshot", "error", "in.driving_command", "drop"]
