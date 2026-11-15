"""summarize_gate2.py: the report's verdict follows the records' expectations (R9).

Inputs are JSONL in the shape gate2.py writes: command records, plus one
`"kind": "isolation"` record per arm and run that counts one capture of the
other zone's bus once.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

CHECKS = Path(__file__).resolve().parents[1]


def cmd(label, arm="headlamp", ok=True, t0=100.0, idx=0, **extra):
    return {"label": label, "arm": arm, "idx": idx, "rep": 1, "ok": ok, "t0": t0,
            "t5": (t0 + 0.07) if ok and t0 is not None else None,
            "s1": 0.01, "s2": 0.02, "s3": 0.03, "total": 0.07, **extra}


def iso(label, arm, routed, denied):
    return {"kind": "isolation", "label": label, "rep": 1, "arm": arm,
            "routed_status_frames": routed, "denied_command_frames": denied}


def summarize(tmp_path, records):
    f = tmp_path / "gate2.jsonl"
    f.write_text("".join(json.dumps(r) + "\n" for r in records))
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run([sys.executable, str(CHECKS / "summarize_gate2.py"), str(f)],
                          capture_output=True, text=True, env=env, timeout=60)


GOOD = [
    cmd("baseline", "headlamp", idx=0), cmd("baseline", "headlamp", idx=1),
    cmd("baseline", "wiper", idx=0), cmd("baseline", "wiper", idx=1),
    iso("baseline", "headlamp", 798, 0), iso("baseline", "wiper", 799, 0),
]


def test_complete_matrix_passes_and_counts_each_capture_once(tmp_path):
    res = summarize(tmp_path, GOOD)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "forbidden command frames on the other bus: 0" in res.stdout
    assert "routed status frames on the other bus: 1597 (required, present in 2/2 captures)" in res.stdout


def test_forbidden_frames_are_summed_per_capture_not_per_record(tmp_path):
    res = summarize(tmp_path, GOOD[:4] + [iso("baseline", "headlamp", 798, 2), iso("baseline", "wiper", 799, 0)])
    assert "forbidden command frames on the other bus: 2" in res.stdout, res.stdout
    assert res.returncode == 1


def test_expected_down_that_converged_fails(tmp_path):
    res = summarize(tmp_path, GOOD + [cmd("restart-down", ok=True)])
    assert res.returncode == 1, res.stdout + res.stderr


def test_expected_down_that_did_not_converge_passes(tmp_path):
    res = summarize(tmp_path, GOOD + [cmd("restart-down", ok=False)])
    assert res.returncode == 0, res.stdout + res.stderr


def test_expected_down_without_a_write_fails(tmp_path):
    res = summarize(tmp_path, GOOD + [cmd("linkloss-down", ok=False, t0=None)])
    assert res.returncode == 1, res.stdout + res.stderr


def test_up_record_that_did_not_converge_fails(tmp_path):
    res = summarize(tmp_path, GOOD + [cmd("restart-up", ok=False)])
    assert res.returncode == 1, res.stdout + res.stderr


def test_missing_isolation_evidence_fails(tmp_path):
    # the pre-fix record shape: a per-record leak count and no isolation record
    legacy = [dict(r, leaks={"other_bus_frames_of_this_ecu": 0}) for r in GOOD[:4]]
    res = summarize(tmp_path, legacy)
    assert res.returncode == 1, res.stdout + res.stderr


def test_capture_without_routed_status_fails(tmp_path):
    res = summarize(tmp_path, GOOD[:4] + [iso("baseline", "headlamp", 0, 0), iso("baseline", "wiper", 799, 0)])
    assert res.returncode == 1, res.stdout + res.stderr


def test_empty_input_fails(tmp_path):
    res = summarize(tmp_path, [])
    assert res.returncode == 1, res.stdout + res.stderr
