"""Pin the two rejection paths that survived the first independent mutation pass."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evidence_fixtures as fx

EVALUATOR = Path(__file__).resolve().parents[1] / "demo_measure.py"


def evaluate(archive, tmp_path):
    output = tmp_path / "verdict.json"
    result = subprocess.run([sys.executable, str(EVALUATOR), *fx.evaluator_args(archive, output)], text=True, capture_output=True, timeout=20)
    return result, json.loads(output.read_text())


@pytest.mark.parametrize("bus,frame", [("rl", 0x180), ("gwr", 0x180), ("fl", 0x280), ("gwf", 0x280)])
def test_a_forbidden_command_on_either_destination_bus_fails(tmp_path, bus, frame):
    archive = fx.write_archive(tmp_path / "archive")
    interfaces = {"rl": "vcan0", "gwr": "vcan-rear", "fl": "vcan0", "gwf": "vcan-front"}
    path = archive / fx.CAPTURE_FILES[bus]
    with path.open("a") as stream:
        stream.write(fx.line(1794704100.0, interfaces[bus], frame, "01 00 00 00 00 00 00 00") + "\n")
    result, summary = evaluate(archive, tmp_path)
    assert result.returncode != 0, f"forbidden {frame:#x} on {bus} was accepted"
    assert "a frame crossed a boundary the policy denies" in result.stderr
    assert summary["verdict"]["pass"] is False


@pytest.mark.parametrize("frame,path_name", [(0x7E0, "uds_request_front_to_rear"), (0x7E8, "uds_response_rear_to_front")])
def test_each_uds_direction_needs_a_routed_pair(tmp_path, frame, path_name):
    archive = fx.write_archive(tmp_path / "archive")
    # Keep the tester's positive text and frame intact. Missing rear-side
    # request/response evidence must fail independently of the tool's success.
    path = archive / fx.CAPTURE_FILES["rl"]
    lines = [line for line in path.read_text().splitlines() if line.split()[2] != f"{frame:03X}"]
    path.write_text("\n".join(lines) + "\n")
    result, summary = evaluate(archive, tmp_path)
    assert result.returncode != 0, f"missing routed {frame:#x} evidence was accepted"
    assert path_name + ": no routed samples" in result.stderr
    assert summary["verdict"]["pass"] is False
