"""Merged frames (DESIGN.md "Merged frames"). When the bench's FEO event trigger merges a backlog into one
chain, conditionInputs takes the newest ready frame and the older ready frames together and conditions
every one of them into the planner's histories; only the newest frame is planned. A frame left out of
the histories breaks the 66-pose ego-motion window, and every later frame then re-primes for 6.6 s:
that is how the G4 run lost its plans (kPlanStale).

The stub engine keeps the same histories as the checkpoint engine, so these tests need no GPU. The
stall option exists for the agent's integration run: it delays chosen plans so that FEO merges frames.
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import de4sdv_planner as P  # noqa: E402
from de4sdv_planner import history as H  # noqa: E402
from de4sdv_planner.warmup import WarmupScheduler  # noqa: E402

FIRST = 2000
IMG = memoryview(bytes(4 * 4 * 4))
RIG = {"vehicle": {"world_matrix": np.eye(4).reshape(-1).tolist(), "location": [0.0, 0.0, 0.0],
                   "wheel_positions": [[1.4, -0.8, 0.35], [1.4, 0.8, 0.35], [-1.45, -0.8, 0.35], [-1.45, 0.8, 0.35]],
                   "wheel_radii": [0.35] * 4}, "cameras": []}


def _start(tmp_path, **extra):
    ck = tmp_path / "ckpt.bin"
    ck.write_bytes(b"stand-in checkpoint")
    cfg = {"engine": "stub", "checkpoint_path": str(ck), "checkpoint_sha256": P.sha256_file(str(ck)), **extra}
    out = json.loads(P.setup(json.dumps(cfg)))
    assert not out["identity"]["refused"]
    json.loads(P.set_rig(json.dumps(RIG)))
    return out


def _condition(k):
    M = np.eye(4)
    M[0, 3] = 0.5 * (k - FIRST)                              # 5 m/s along x
    primed, measured, ck, rec = P.condition(k, [IMG] * 6, [(4, 4)] * 6, M.tobytes(), None, None)
    return primed


def test_a_frame_left_out_of_the_histories_re_primes_for_the_whole_pose_window(tmp_path):
    """Before merged frames: the skipped frame 2100 un-primes frames 2100 .. 2165 (66 frames, 6.6 s)."""
    _start(tmp_path)
    unprimed = [k for k in range(FIRST, FIRST + 200) if k != 2100 and not _condition(k)]
    after_gap = [k for k in unprimed if k > 2100]
    assert after_gap[0] == 2101 and after_gap[-1] == 2100 + H.POSE_WINDOW - 1
    assert len(after_gap) == H.POSE_WINDOW - 1               # 2101 .. 2165 (2100 itself never arrived)
    assert P.infer(2130) is None


def test_a_merged_frame_conditioned_without_a_plan_keeps_the_histories(tmp_path):
    """With merged frames: frames 2099 and 2100 are conditioned in 2101's chain, never planned, and every
    frame from the first primed one on stays primed and plannable."""
    _start(tmp_path)
    primed = {}
    planned = {}
    for k in range(FIRST, FIRST + 200):
        primed[k] = _condition(k)
        if k in (2099, 2100):
            continue                                         # merged: conditioned, not planned
        planned[k] = P.infer(k) is not None
        assert planned[k] == primed[k], k
    assert [k for k, p in primed.items() if not p] == list(range(FIRST, FIRST + H.POSE_WINDOW - 1))
    assert planned[2098] and planned[2101] and planned[2102]


def test_conditioning_merged_frames_one_by_one_leaves_the_lag_of_one_observation():
    """checkpoint.condition() reports every conditioned frame to the warm-up scheduler. Merged frames are
    conditioned in the newest frame's chain, oldest first, a few ms apart; the lag must be the one a
    single observation of the newest frame gives."""
    for late_ms in (0.0, 40.0, 130.0, 260.0):
        one, each = WarmupScheduler(), WarmupScheduler()
        for s in (one, each):
            s.observe_step_start(10, 0.0)
        t = 0.1 * 3 + late_ms / 1000.0                       # frames 11 and 12 merged into 13's chain
        one.observe_step_start(13, t + 0.006)
        for i, k in enumerate((11, 12, 13)):
            each.observe_step_start(k, t + 0.003 * i)
        assert each.lag_ms == pytest.approx(one.lag_ms, abs=1e-9), late_ms


def _plan_times(frames):
    """Condition frames 2000 .. 2100 and plan the given ones right after their own condition call (the
    stub keeps 8 frames of ego rows, as the checkpoint engine does)."""
    seen = {}
    for k in range(FIRST, FIRST + 101):
        _condition(k)
        if k in frames:
            t0 = time.monotonic()
            r = P.infer(k)
            assert r is not None, k
            seen[k] = (time.monotonic() - t0, json.loads(r[2]))
    return seen


def test_the_stub_stall_delays_the_chosen_plans_and_records_it(tmp_path):
    out = _start(tmp_path, stub_stall_ms=120, stub_stall_every=50)
    assert out["engineRecord"]["stall"] == {"ms": 120.0, "every": 50}
    seen = _plan_times((2099, 2100))
    dt, rec = seen[2099]                                     # not a multiple of 50: no stall
    assert dt < 0.05 and "stall_ms" not in rec
    dt, rec = seen[2100]
    assert dt >= 0.12 and rec["stall_ms"] == 120.0


def test_the_stub_without_the_stall_options_never_stalls(tmp_path):
    out = _start(tmp_path)
    assert out["engineRecord"]["stall"] is None
    dt, rec = _plan_times((2100,))[2100]
    assert dt < 0.05 and "stall_ms" not in rec


def test_the_stub_stall_reaches_the_pure_pursuit_plan_record(tmp_path):
    """The L4 integration runs plan by pure pursuit along the route (stub_route): the stalled plan's record
    must carry the stall there too."""
    route = tmp_path / "route.json"
    route.write_text(json.dumps({"waypoints": [[0.5 * i, 0.0, 0.0] for i in range(400)]}))
    _start(tmp_path, stub_stall_ms=120, stub_stall_every=50, stub_route=str(route), stub_target_speed_mps=5.0)
    seen = _plan_times((2099, 2100))
    assert seen[2099][1]["mode"] == "stub-pure-pursuit" and "stall_ms" not in seen[2099][1]
    dt, rec = seen[2100]
    assert rec["mode"] == "stub-pure-pursuit" and dt >= 0.12 and rec["stall_ms"] == 120.0


@pytest.mark.parametrize("bad", [{"stub_stall_ms": 120}, {"stub_stall_every": 50},
                                 {"stub_stall_ms": -1, "stub_stall_every": 50},
                                 {"stub_stall_ms": 120, "stub_stall_every": 0}])
def test_the_stub_refuses_a_half_or_invalid_stall(tmp_path, bad):
    with pytest.raises(ValueError):
        _start(tmp_path, **bad)
