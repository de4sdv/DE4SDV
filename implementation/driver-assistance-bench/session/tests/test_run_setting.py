"""run_setting.py against the world side's settings: every run of the committed s1 list resolves.

The stop run is no run of a setting (the model's terms, needs_requirements.sysml:205-211). The world side holds it
as the setting `stop` (world-side/scenarios.py STOP_RUN), so the session must ask for `stop`, never for
`SC-DRIVING-012@stop`.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SESSION = Path(__file__).resolve().parents[1]
RUN_SETTING = SESSION / "run_setting.py"
S1_RUNS = SESSION / "s1_runs.tsv"
STOP_SCENARIO = "SC-DRIVING-012"  # entrypoints.env S1_STOP_SCENARIO
STOP_SETTING = "stop"  # entrypoints.env S1_STOP_SETTING


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(RUN_SETTING), *args], capture_output=True, text=True, timeout=60)


def test_the_stop_run_resolves_to_the_world_sides_setting_stop() -> None:
    r = _run(STOP_SCENARIO, STOP_SETTING)
    assert r.returncode == 0, r.stderr
    assert r.stdout.split()[0] == "stop", r.stdout


def test_a_setting_of_a_scenario_keeps_its_scenario_prefix() -> None:
    r = _run("SC-DRIVING-012", "20kmh")
    assert r.returncode == 0, r.stderr
    assert r.stdout.split()[0] == "SC-DRIVING-012@20", r.stdout


def test_every_run_of_the_committed_s1_list_resolves() -> None:
    lines = [line.split("\t") for line in S1_RUNS.read_text(encoding="utf-8").splitlines()
             if line.strip() and not line.startswith("#")]
    assert lines, "s1_runs.tsv is empty"
    for fields in lines:
        run = fields[1] if len(fields) > 1 else fields[0]
        setting = fields[0]
        if setting == STOP_SETTING or run == "further":
            r = _run(STOP_SCENARIO, STOP_SETTING)
        else:
            scenario = setting.split("@")[0]
            r = _run(scenario, setting)
        assert r.returncode == 0, (fields, r.stderr)
