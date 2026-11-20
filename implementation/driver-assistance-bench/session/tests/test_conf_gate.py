"""J4 of the closure review of 44a4be29: the S-CORE start's staged vision_pilot.conf must carry every value the model
fixes, not only speed_limit. The candidate's configuration sentence (driver_assistance_physical_software_realization
.sysml:541-544, VisionPilotSCOREApplication): engine.provider = cuda, model.precision = fp32, visualization_on = false,
rrd_on = true; source.mode = score is the value the kit stages for the bench (score-path/scripts/stage_score_side.py:67,
score-interface/README.md:27: the module is chosen by source.mode = score). The values are written out here from those
lines, not taken from the script. A start whose SCORE_CONFIG line names another value, or none, ends the session at
that start (exit 5, failed_step score_start_<run>), before the go, as a wrong speed_limit does.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from test_session_dryrun import G4, _vp_env, assert_invariants, vp_clone  # noqa: F401 (the dry runs' fixtures)
from test_session_s1 import record, s1_run

FIXED = {"source.mode": "score", "engine.provider": "cuda", "model.precision": "fp32", "visualization_on": "false",
         "rrd_on": "true"}
FACTS_PIN = "0001-de4sdv-visualization-recorder.diff+0002-de4sdv-score-interface.diff+0003-de4sdv-headless-display" \
    ".diff+0005-de4sdv-warm-start.diff"


def staged(**over: str) -> str:
    """A SCORE_CONFIG line in score_config_record.py's word order, the model's values unless overridden."""
    v = {**FIXED, **over}
    words = ["speed_limit=5.833", "speed_limit_requested=5.833", "hero_wait_s=400.0"] + \
        [f"{k}={v[k]}" for k in FIXED if v[k] is not None] + ["conf_sha256=" + "a" * 64, "conf_recorded=1",
                                                              "facts_diffs=" + FACTS_PIN]
    return "SCORE_CONFIG " + " ".join(words)


def _run(tmp: Path, line: str):
    return s1_run(tmp, "--without-guest-host", "--camcal", "settings", runs="SC-DRIVING-012@20\tr1\n",
                  FAKE_TAIL_ADD="score_start_012_20_r1:" + line)


def test_a_start_that_stages_every_fixed_value_goes_on(tmp_path: Path) -> None:
    r = _run(tmp_path, staged())
    assert r.rc == 0, r.log[-3000:]
    assert record(r)["score_runs"]["012_20_r1"]["staged"]["engine.provider"] == "cuda"


@pytest.mark.parametrize("key, wrong", [("source.mode", "file"), ("engine.provider", "cpu"),
                                        ("model.precision", "fp16"), ("visualization_on", "true"),
                                        ("rrd_on", "false"), ("rrd_on", None)])
def test_a_start_that_stages_another_value_ends_the_session_before_the_go(tmp_path: Path, key: str, wrong) -> None:
    r = _run(tmp_path, staged(**{key: wrong}))
    assert r.rc == 5, r.log[-3000:]
    rec = record(r)
    assert rec["failed_step"] == "score_start_012_20_r1", rec["failed_step"]
    shown = wrong if wrong is not None else "none"
    assert f"{key} {shown}, the model fixes {FIXED[key]}" in r.log, r.log[-2000:]
    assert not r.ssh(G4, "world_012_20_r1/go")
    assert_invariants(r)
