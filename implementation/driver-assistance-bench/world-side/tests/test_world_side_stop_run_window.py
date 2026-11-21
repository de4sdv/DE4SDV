"""The stop run's length against its stop instant (J7 of the closure check of 44a4be29).

VC-DRIVING-038 reads the stop run's world ticks after the last control applied before the stop
(case-evaluators/cases_da.py stop_038); with none it is inconclusive. The model leaves the stop run's length free
(needs_requirements.sysml:205-211 and :298; verification_evidence.sysml:395-411 and :683-706), so the bench sizes it:
the run's cap, counted in simulation time from the go, covers the stop instant at its bound plus 10 s of simulation time
after it, and the stationary target stands where the hero cannot reach it within the cap.

The stop instant's bound after the go: the session's path stop at the go + PATH_STOP_AFTER_S (12 s,
session/da_session.sh), then the step's start call and path_stop.sh (about 2 s), the LmControl client's connect
(lm_control_client.h connect_timeout_ms 5000) and drain (drain_ms 200), and the end of the components outside the run
target path_stopped (actuation adapter, gatewayd, someipd: launch_manager_config.json shutdown_timeout_ms 3000, then
SIGKILL): 12 + 2 + 5 + 0.2 + 3 = 22.2 s. The world paces on the wall clock, so its simulation time never runs ahead of
the wall time since the go.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from world_side_testkit import AdapterStandIn, run_main

import scenarios

BENCH = Path(__file__).resolve().parents[2]
SESSION_SH = BENCH / "session" / "da_session.sh"
WARMUP_SH = BENCH / "world-side" / "scripts" / "warmup.sh"

# the stop instant's bound after the call (see the module's doc): the step and path_stop.sh, connect, drain, shutdown
PATH_STOP_SETTLE_BOUND_S = 2.0 + 5.0 + 0.2 + 3.0
# PROPOSAL (S1 plan section 3): the stop run goes on 10 s of simulation time after the stop
WINDOW_AFTER_STOP_S = 10.0
# half lengths of the hero (vehicle.lincoln.mkz) and the target (vehicle.tesla.model3), about: their centres at contact
CONTACT_CENTRES_M = 2.45 + 2.40


def _session_path_stop_after_s() -> float:
    m = re.search(r"^PATH_STOP_AFTER_S=([0-9.]+)\s*$", SESSION_SH.read_text(encoding="utf-8"), re.M)
    assert m, f"precondition: {SESSION_SH} sets PATH_STOP_AFTER_S"
    return float(m.group(1))


def test_the_session_stops_the_path_at_the_go_plus_12_s():
    assert _session_path_stop_after_s() == 12.0


def test_the_stop_runs_cap_covers_the_stop_bound_and_the_window_after_it():
    st = scenarios.setting(scenarios.STOP_RUN)
    bound = _session_path_stop_after_s() + PATH_STOP_SETTLE_BOUND_S          # 22.2 s after the go
    assert st.run_cap_s - bound >= WINDOW_AFTER_STOP_S, (
        f"the stop run ends {st.run_cap_s} s after the go: {st.run_cap_s - bound:.1f} s after the stop's bound "
        f"({bound} s), less than the {WINDOW_AFTER_STOP_S} s window")


def test_the_hero_cannot_reach_the_stop_runs_target_within_the_cap():
    # after the stop the simulator keeps the last valid control (the adapter has no stop response), so the hero drives
    # on; at the band's top speed held from the go it must stay short of the target until the cap, or the run ends
    # at the contact and cuts the window
    st = scenarios.setting(scenarios.STOP_RUN)
    reach = st.high_kmh * scenarios.KMH * st.run_cap_s
    assert reach < st.target_ahead_m - CONTACT_CENTRES_M, (reach, st.target_ahead_m)


def test_the_stop_runs_road_is_within_the_sessions_survey_road():
    # every run starts on the session's road, which the warm-up's survey sizes for SURVEY_SETTING (SC-DRIVING-012@60)
    assert 'SURVEY_SETTING=${SURVEY_SETTING:-SC-DRIVING-012@60}' in WARMUP_SH.read_text(encoding="utf-8")
    stop = scenarios.setting(scenarios.STOP_RUN)
    survey = scenarios.setting("SC-DRIVING-012@60")
    assert scenarios.road_needed_m(stop, stop.target_ahead_m) <= scenarios.road_needed_m(survey,
                                                                                         survey.target_ahead_m)


def test_on_the_fake_the_stop_run_ends_at_its_cap_with_the_window_after_the_stop_bound(tmp_path, server, factory,
                                                                                    clock):
    AdapterStandIn(server, 22.0)            # the band's top, held to the end (the last control kept after the stop)
    run_dir = tmp_path / "stop"
    rc, lines = run_main(["run", "--run-dir", str(run_dir), "--setting", scenarios.STOP_RUN], factory, clock)
    assert rc == 0, lines
    sim = run_dir / "simulator"
    summary = json.loads((sim / "summary.json").read_text())
    ticks = [json.loads(x)["data"] for x in (sim / "world.jsonl").read_text().splitlines()]
    ticks = [t for t in ticks if t.get("scenarioTimeS") is not None]
    assert ticks, "precondition: the run ticked"
    assert not any(t["targetContact"] for t in ticks)
    assert summary["endReason"] == "run cap"
    bound = _session_path_stop_after_s() + PATH_STOP_SETTLE_BOUND_S
    assert ticks[-1]["scenarioTimeS"] - bound >= WINDOW_AFTER_STOP_S - 1e-6
