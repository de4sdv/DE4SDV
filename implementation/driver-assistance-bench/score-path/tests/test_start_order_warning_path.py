"""Score-side's start order (lane I-S of the S1 integration, 2026-11-20): the candidate's process no longer depends on
gatewayd (score-side lane, a9384a0c: an edge to gatewayd would keep the warning path running in the stop run's target
path_stopped), so Lifecycle may start the candidate before gatewayd or someipd. The session writes the go only after
the S-CORE start step returned 0 (session/da_session.sh world_run: score_start_<run> before touch-go), so the start must
not return before both run. Guard test: the start already waits for every component of COMPONENTS_FULL.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from test_score_side_scripts import START, bench, record_driver, run, state  # noqa: F401
import fake_bundle


@pytest.mark.parametrize("late", ["gatewayd", "someipd"])
def test_the_start_returns_only_once_the_warning_path_runs_even_when_it_starts_after_the_candidate(
        bench: dict, tmp_path: Path, late: str) -> None:
    out = tmp_path / "out"
    t0 = time.monotonic()
    started = run(START, str(out), "10.164.0.2", env={**bench["env"], "FAKE_LM_LATE": f"{late}:4"})
    took = time.monotonic() - t0
    assert started.returncode == 0, started.stdout + started.stderr
    lm_log = (bench["stage"] / "state" / "launch_manager.log").read_text()
    # the order the knob models: the candidate and the adapter first, the warning path's component 4 s later
    assert lm_log.index("started vision_pilot") < lm_log.index(f"started {late}"), lm_log
    # the start returned only after that component ran
    assert took >= 4, took
    s = state(out / "score_side_state.env")
    assert s["STATE"] == "up" and s[f"PID_{late}"], s
    assert any(f"/bin/{late}" in p for p in fake_bundle.staged_processes(bench["stage"]))
