"""R2: the demo verdict must fail closed.

Every test runs the real evaluator (checks/demo_measure.py) as a subprocess on
an archive that differs from a working one in exactly one property, and
requires a non-zero exit naming that property.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evidence_fixtures as fx  # noqa: E402

CHECKS = Path(__file__).resolve().parents[1]
EVALUATOR = CHECKS / "demo_measure.py"
PY = "/usr/bin/python3"


def run(archive: Path, tmp_path: Path, extra: list[str] | None = None):
    out = tmp_path / "summary.json"
    proc = subprocess.run(
        [PY, str(EVALUATOR), *fx.evaluator_args(archive, out), *(extra or [])],
        capture_output=True, text=True, timeout=120,
    )
    return proc, out


def test_a_working_archive_passes(tmp_path):
    """Guard: the synthetic working archive is accepted."""
    archive = fx.write_archive(tmp_path / "a")
    proc, out = run(archive, tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert out.exists()


@pytest.mark.parametrize("bus", ["fl", "rl", "gwf", "gwr"])
def test_a_missing_capture_fails(tmp_path, bus):
    archive = fx.write_archive(tmp_path / "a")
    (archive / fx.CAPTURE_FILES[bus]).unlink()
    proc, _ = run(archive, tmp_path)
    assert proc.returncode != 0, "missing capture accepted"
    assert "capture" in proc.stderr and fx.CAPTURE_FILES[bus] in proc.stderr


@pytest.mark.parametrize("bus", ["fl", "rl", "gwf", "gwr"])
def test_an_empty_capture_fails(tmp_path, bus):
    archive = fx.write_archive(tmp_path / "a")
    (archive / fx.CAPTURE_FILES[bus]).write_text("")
    proc, _ = run(archive, tmp_path)
    assert proc.returncode != 0, "empty capture accepted"
    assert "empty" in proc.stderr and fx.CAPTURE_FILES[bus] in proc.stderr


def test_a_malformed_capture_line_fails(tmp_path):
    archive = fx.write_archive(tmp_path / "a")
    path = archive / fx.CAPTURE_FILES["rl"]
    # A truncated live candump file leaves NULs; an interface error is text.
    path.write_text(path.read_text() + "\x00\x00\x00\ncandump: interface vcan0 not found\n")
    proc, _ = run(archive, tmp_path)
    assert proc.returncode != 0, "malformed capture accepted"
    assert "malformed" in proc.stderr and fx.CAPTURE_FILES["rl"] in proc.stderr


def test_a_non_finite_capture_timestamp_fails(tmp_path):
    archive = fx.write_archive(tmp_path / "a")
    path = archive / fx.CAPTURE_FILES["fl"]
    path.write_text(path.read_text() + " (1e999)  vcan0  181   [8]  00 00 00 00 00 00 00 00\n")
    proc, _ = run(archive, tmp_path)
    assert proc.returncode != 0, "non-finite timestamp accepted"
    assert fx.CAPTURE_FILES["fl"] in proc.stderr


# --- the command matrix --------------------------------------------------------


def write_commands(archive: Path, commands: list[dict]) -> None:
    (archive / "commands.jsonl").write_text("".join(json.dumps(c) + "\n" for c in commands))


def test_the_scenario_declares_eight_alternating_commands_per_arm():
    """The verdict counts against the committed driver's matrix, not 'any'."""
    sys.path.insert(0, str(CHECKS))
    import demo_measure

    scenario = demo_measure.SCENARIOS["alternating-8"]
    assert [str(v).lower() for v in scenario["headlamp"]] == ["true", "false"] * 4
    assert [str(v).lower() for v in scenario["wiper"]] == ["fast", "off"] * 4


def test_an_incomplete_command_matrix_fails(tmp_path):
    # Six per arm, all converged: the shape of the historical 12-command runs.
    commands = [c for c in fx.default_commands() if c["arm"] == "headlamp"][:6]
    commands += [c for c in fx.default_commands() if c["arm"] == "wiper"][:6]
    archive = fx.write_archive(tmp_path / "a", commands)
    proc, _ = run(archive, tmp_path)
    assert proc.returncode != 0, "6 of 8 commands per arm accepted"
    assert "headlamp: 6 of 8" in proc.stderr and "wiper: 6 of 8" in proc.stderr


def test_an_extra_command_fails(tmp_path):
    commands = fx.default_commands()
    extra = dict(commands[7], value=True, t0=commands[7]["t0"] + 0.7, t5=commands[7]["t0"] + 0.77)
    commands.insert(8, extra)
    archive = fx.write_archive(tmp_path / "a", commands)
    proc, _ = run(archive, tmp_path)
    assert proc.returncode != 0, "a ninth headlamp command accepted"
    assert "headlamp: 9 of 8" in proc.stderr


def test_one_nonconverged_command_fails(tmp_path):
    commands = fx.default_commands()
    commands[10].update(ok=False, t5=None)
    archive = fx.write_archive(tmp_path / "a", commands)
    proc, _ = run(archive, tmp_path)
    assert proc.returncode != 0, "a non-converged command accepted"
    assert "wiper command 3" in proc.stderr and "did not converge" in proc.stderr


@pytest.mark.parametrize("ok", ["false", "true", 1])
def test_converged_must_be_json_true(tmp_path, ok):
    commands = fx.default_commands()
    commands[1]["ok"] = ok
    archive = fx.write_archive(tmp_path / "a", commands)
    proc, _ = run(archive, tmp_path)
    assert proc.returncode != 0, f"ok={ok!r} read as converged"
    assert "headlamp command 2" in proc.stderr and "did not converge" in proc.stderr


@pytest.mark.parametrize("field,value", [("t5", None), ("t5", float("nan")), ("t0", "1794704073.0"),
                                         ("t5", float("inf")), ("t5", True)])
def test_a_command_timestamp_must_be_finite(tmp_path, field, value):
    commands = fx.default_commands()
    archive = fx.write_archive(tmp_path / "a", commands)  # bus frames from the true stamps
    commands[2][field] = value
    write_commands(archive, commands)
    proc, _ = run(archive, tmp_path)
    assert proc.returncode != 0, f"{field}={value!r} accepted"
    assert "headlamp command 3" in proc.stderr and field in proc.stderr


def test_t5_before_t0_fails(tmp_path):
    commands = fx.default_commands()
    archive = fx.write_archive(tmp_path / "a", commands)
    commands[4]["t5"] = commands[4]["t0"] - 0.01
    write_commands(archive, commands)
    proc, _ = run(archive, tmp_path)
    assert proc.returncode != 0, "t5 < t0 accepted"
    assert "headlamp command 5" in proc.stderr and "t5" in proc.stderr


def test_a_repeated_value_is_not_the_declared_transition(tmp_path):
    commands = fx.default_commands()
    commands[9]["value"] = "FAST"  # FAST FAST: a non-transition where OFF was declared
    archive = fx.write_archive(tmp_path / "a", commands)
    proc, _ = run(archive, tmp_path)
    assert proc.returncode != 0, "a repeated value accepted as a transition"
    assert "wiper command 2" in proc.stderr and "expected 'OFF'" in proc.stderr


def test_a_command_without_its_bus_frame_fails(tmp_path):
    archive = fx.write_archive(tmp_path / "a", drop_command_frame_at=3)
    proc, _ = run(archive, tmp_path)
    assert proc.returncode != 0, "a command with no command frame accepted"
    assert "headlamp command 4" in proc.stderr and "no 0x180 command frame" in proc.stderr


def test_a_command_without_its_status_frame_fails(tmp_path):
    # Periodic status still flows: drop both the immediate and every periodic
    # frame carrying the new state by removing all 0x281 frames on the rear bus.
    archive = fx.write_archive(tmp_path / "a")
    for name in (fx.CAPTURE_FILES["rl"],):
        path = archive / name
        path.write_text("\n".join(ln for ln in path.read_text().splitlines() if "  281  " not in ln) + "\n")
    proc, _ = run(archive, tmp_path)
    assert proc.returncode != 0, "commands with no status frame accepted"
    assert "wiper command 1" in proc.stderr and "no 0x281 status frame" in proc.stderr


def test_an_unparseable_command_record_is_named(tmp_path):
    archive = fx.write_archive(tmp_path / "a")
    path = archive / "commands.jsonl"
    lines = path.read_text().splitlines()
    lines[2] = '{"arm": "headlamp", "value": tr'
    path.write_text("\n".join(lines) + "\n")
    proc, _ = run(archive, tmp_path)
    assert proc.returncode != 0
    assert "commands.jsonl line 3" in proc.stderr


def test_an_unknown_scenario_is_refused(tmp_path):
    archive = fx.write_archive(tmp_path / "a")
    proc, _ = run(archive, tmp_path, ["--scenario", "any-one-success"])
    assert proc.returncode != 0
    assert "any-one-success" in proc.stderr


# --- routed paths and the diagnostic -------------------------------------------


def test_no_routed_status_samples_fails(tmp_path):
    archive = fx.write_archive(tmp_path / "a", route_status=False)
    proc, _ = run(archive, tmp_path)
    assert proc.returncode != 0, "a run with no routed status pair accepted"
    assert "headlamp_status_front_to_rear: no routed samples" in proc.stderr
    assert "wiper_status_rear_to_front: no routed samples" in proc.stderr


def test_a_negative_uds_response_with_5003_in_its_address_fails(tmp_path):
    archive = fx.write_archive(tmp_path / "a", uds_text=fx.NEGATIVE_UDS_TEXT)
    proc, out = run(archive, tmp_path)
    assert proc.returncode != 0, "a NegativeResponse at 0x7215003c8320 read as positive"
    assert "negative response" in proc.stderr and "0x22" in proc.stderr
    assert json.loads(out.read_text())["uds"]["positive_response"] is False


def test_missing_uds_output_fails(tmp_path):
    archive = fx.write_archive(tmp_path / "a")
    (archive / "uds.txt").unlink()
    proc, _ = run(archive, tmp_path)
    assert proc.returncode != 0, "a run without the diagnostic accepted"
    assert "uds.txt" in proc.stderr


def test_uds_tool_text_without_a_payload_fails(tmp_path):
    archive = fx.write_archive(tmp_path / "a", uds_text="UdsTool not installed on this host: /opt/x\nPositiveResponse\n")
    proc, _ = run(archive, tmp_path)
    assert proc.returncode != 0, "the word PositiveResponse alone accepted"
    assert "no UDS response payload" in proc.stderr


def test_a_positive_tool_line_needs_the_positive_frame_on_the_tester_bus(tmp_path):
    # The tester printed a positive payload, but the bus carried a negative one.
    archive = fx.write_archive(tmp_path / "a", uds_response="03 7F 10 22 CC CC CC CC")
    proc, _ = run(archive, tmp_path)
    assert proc.returncode != 0, "a positive tool line without its bus frame accepted"
    assert "no positive 0x7E8 response 50 03" in proc.stderr


def test_the_reviewers_fail_open_reproduction_now_fails(tmp_path):
    """The exact shape of probe-evidence/demo_verdict: four empty captures,
    one converged command of twelve, a negative UDS reply containing 5003."""
    archive = tmp_path / "a"
    archive.mkdir()
    for name in fx.CAPTURE_FILES.values():
        (archive / name).write_text("")
    commands = [c for c in fx.default_commands() if c["arm"] == "headlamp"][:6]
    commands += [c for c in fx.default_commands() if c["arm"] == "wiper"][:6]
    for c in commands[1:]:
        c.update(ok=False, t5=None)
    write_commands(archive, commands)
    (archive / "uds.txt").write_text(fx.NEGATIVE_UDS_TEXT)
    proc, out = run(archive, tmp_path)
    assert proc.returncode != 0
    for reason in ("required capture empty", "headlamp: 6 of 8", "did not converge",
                   "no routed samples", "negative response"):
        assert reason in proc.stderr, reason
    summary = json.loads(out.read_text())
    assert summary["verdict"]["pass"] is False


HISTORICAL = CHECKS.parent / "results" / "20261115T005422Z-657d64c6"


def _digest(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def test_the_historical_twelve_command_archive_is_not_current_acceptance(tmp_path):
    """Its numbers stay; replayed today it is a 6-of-8 run, and nothing in the
    archive is rewritten by the replay."""
    before = _digest(HISTORICAL)
    out = tmp_path / "replay.json"
    args = fx.evaluator_args(HISTORICAL, out)
    proc = subprocess.run([PY, str(EVALUATOR), *args], capture_output=True, text=True, timeout=120)
    assert proc.returncode != 0, "a historical 12-command archive passed as current acceptance"
    assert "headlamp: 6 of 8" in proc.stderr and "wiper: 6 of 8" in proc.stderr
    assert _digest(HISTORICAL) == before
