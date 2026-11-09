"""Warm-up of the checkpoint's camera history cache while the agent primes (warmup.py).

The upstream StatefulCameraFPNCache has one stream per 100 ms phase. A call is warm (about 91 ms on the
G4) only when its stream holds 7 frames and its last commit was exactly 0.5 s earlier; otherwise the
model re-encodes the 7 history frames (about 119 ms). FEO runs conditionInputs -> inferPlan -> ... as
one chain per frame event on worker 40, and the bench's event trigger merges a backlog into one chain
for the newest frame; a merged frame is never conditioned, so the 66-pose ego history breaks.

The discrete-event model below is that loop. Without warm-up it reproduces the G4 attempt-2 failure
(bursts of 5 cold plans, a merged frame, a 67-frame gap); with the WarmupScheduler every first plan
is warm and no frame is merged.

Run: python3 -m pytest -q agent/python/tests   (numpy only; no torch, no GPU)
"""
import random
import sys
import time
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from de4sdv_planner import history as H  # noqa: E402
from de4sdv_planner.warmup import WarmupScheduler  # noqa: E402

PERIOD_MS = 100.0
CHAIN_MS = 3.0                                # the chain without an engine call (G4: condition_ms p50 2.6)
G4_COST_MS = {"cold": 119.0, "warm": 91.3}    # G4 attempt 2: compute_ms p50 119.1 cold; bind 91.28 warm


def t_us_of(k):
    return 10_000_000 + 100_000 * k           # checkpoint.py's capture timestamps


class FakeCache:
    """The upstream cache rule: full, or cleared and re-primed from the raw history tiles."""

    def __init__(self):
        self.full, self.last = False, None
        self.resets = 0

    def reset(self):
        self.full, self.last = False, None
        self.resets += 1

    def __len__(self):
        return 7 if self.full else 0

    @property
    def last_committed_timestamps_us(self):
        return None if self.last is None else (self.last,)

    def warm_for(self, t_us):
        return self.full and self.last == t_us - 500_000

    def call(self, t_us):
        assert self.last is None or t_us > self.last, "the cache requires strictly newer timestamps"
        kind = "warm" if self.warm_for(t_us) else "cold"
        self.full, self.last = True, t_us
        return kind


def simulate(n_frames, warmup, cost=G4_COST_MS, jitter_ms=0.0, seed=1):
    """One chain per frame event; a chain that ends after newer frames arrived processes the newest."""
    rng = random.Random(seed)
    caches = [FakeCache() for _ in range(5)]
    sched = WarmupScheduler(cold_ms=cost["cold"] + 2.0, warm_ms=cost["warm"]) if warmup else None
    conditioned, merged, plans, warm_calls = set(), [], [], []
    t, k, lag_max = 0.0, 0, 0.0
    while k < n_frames:
        t = max(t, k * PERIOD_MS)                       # wait for the frame event
        newest = int(t // PERIOD_MS)
        if newest > k:                                  # the backlog merges into the newest frame
            merged.extend(range(k, newest))
            k = newest
            if k >= n_frames:
                break
        lag_max = max(lag_max, t - k * PERIOD_MS)
        if sched:
            sched.observe_step_start(k, t / 1000.0)
        conditioned.add(k)
        t += CHAIN_MS
        s, tu = k % 5, t_us_of(k)
        cam = all(j in conditioned for j in H.camera_history_frames(k))
        primed = cam and all(j in conditioned for j in H.pose_frames(k))
        if primed:                                      # inferPlan plans
            kind = caches[s].call(tu)
            t += cost[kind] + rng.uniform(-jitter_ms, jitter_ms)
            plans.append((k, kind))
        elif sched and cam:                             # inferPlan warms while priming
            decision, _ = sched.decide(k, caches[s].warm_for(tu))
            if decision != "skip":
                kind = caches[s].call(tu)
                assert kind == decision
                ms = cost[kind] + rng.uniform(-jitter_ms, jitter_ms)
                t += ms
                sched.record(decision, ms)
                warm_calls.append((k, s, decision))
        k += 1
    return {"merged": merged, "plans": plans, "warm_calls": warm_calls, "lag_max": lag_max}


def test_the_model_reproduces_the_g4_failure_without_warmup():
    r = simulate(400, warmup=False)
    first = [kind for _, kind in r["plans"][:5]]
    assert first == ["cold"] * 5
    assert r["merged"], "the cold burst must overrun into a merged frame"
    frames = [f for f, _ in r["plans"]]
    gaps = [b - a for a, b in zip(frames, frames[1:]) if b - a > 1]
    assert gaps and gaps[0] == 67, gaps                # G4 attempt 2: {1: 100, 67: 24}
    assert all(kind == "cold" for _, kind in r["plans"])


def test_with_warmup_every_plan_is_warm_and_no_frame_is_merged():
    r = simulate(600, warmup=True)
    assert r["merged"] == []
    assert r["plans"], "the agent never planned"
    assert all(kind == "warm" for _, kind in r["plans"]), r["plans"][:8]
    frames = [f for f, _ in r["plans"]]
    assert frames == list(range(frames[0], frames[0] + len(frames)))   # a plan on every frame
    assert frames[0] == H.POSE_WINDOW - 1                               # as early as without warm-up
    assert r["lag_max"] < PERIOD_MS


def test_every_stream_is_warmed_before_its_first_plan():
    r = simulate(80, warmup=True)
    first_plan = {k % 5: k for k, _ in reversed(r["plans"])}
    for s, k in first_plan.items():
        assert (k - 5, s) in {(f, st) for f, st, _ in r["warm_calls"]}, (s, k)


@pytest.mark.parametrize("seed", range(5))
def test_warmup_keeps_the_lag_below_a_frame_under_jitter(seed):
    r = simulate(600, warmup=True, jitter_ms=4.0, seed=seed)
    assert r["merged"] == []
    assert r["lag_max"] < PERIOD_MS


def test_the_scheduler_defers_a_cold_call_that_would_lag_too_far():
    s = WarmupScheduler(cold_ms=121.0, warm_ms=91.3)
    s.observe_step_start(100, 10.0)
    assert s.decide(100, stream_warm=False)[0] == "cold"
    s.record("cold", 121.0)
    s.observe_step_start(101, 10.124)                  # the chain ran 124 ms: 24 ms behind
    s.record("cold", 121.0)
    s.observe_step_start(102, 10.248)                  # 48 ms behind
    assert s.lag_ms == pytest.approx(48.0, abs=0.01)
    decision, reason = s.decide(102, stream_warm=False)
    assert decision == "skip" and "lag" in reason
    assert s.decide(102, stream_warm=True)[0] == "warm"   # a warm call lowers the lag


def test_the_scheduler_learns_the_measured_cost():
    """The cost estimates follow the measured calls: on a host slower than the setup's calls, the
    scheduler stops priming cold streams once the measured cost would leave the lag over the limit."""
    s = WarmupScheduler(cold_ms=121.0, warm_ms=91.3)
    s.observe_step_start(100, 10.0)
    assert s.decide(100, stream_warm=False)[0] == "cold"        # 5 + 121 - 100 = 26 ms predicted
    for _ in range(10):
        s.record("cold", 170.0)                                  # the calls take 170 ms on this host
    assert s.cost_ms["cold"] == pytest.approx(170.0, abs=6.0)
    assert s.decide(100, stream_warm=False)[0] == "skip"         # 5 + ~165 - 100 > 50 ms


def test_the_predicted_lag_includes_the_chain():
    """The lag after a call counts the chain's own time (conditionInputs, supervision, command), not
    only the engine call."""
    s = WarmupScheduler(chain_ms=10.0, cold_ms=145.0)
    assert s.predicted_lag_ms("cold") == pytest.approx(55.0)    # 0 + 10 + 145 - 100
    assert s.decide(0, stream_warm=False)[0] == "skip"           # over the 50 ms limit
    assert WarmupScheduler(chain_ms=0.0, cold_ms=145.0).decide(0, stream_warm=False)[0] == "cold"


def test_the_scheduler_counts_merged_frames_in_the_lag():
    s = WarmupScheduler()
    s.observe_step_start(10, 1.0)
    s.observe_step_start(12, 1.2)                      # frame 11 merged, on schedule otherwise
    assert s.lag_ms == pytest.approx(0.0, abs=1e-9)
    s.observe_step_start(14, 1.45)                     # frame 13 merged, the chain 50 ms late
    assert s.lag_ms == pytest.approx(50.0, abs=1e-6)
    s.observe_step_start(15, 1.50)                     # a short chain catches up
    assert s.lag_ms == pytest.approx(0.0, abs=1e-6)


# ------------------------------------------------------------ the engine glue (CheckpointEngine.warm)

def _engine_with_history(first, last):
    from de4sdv_planner.checkpoint import CheckpointEngine
    eng = object.__new__(CheckpointEngine)             # no torch: the engine's state set by hand
    eng.caches = [FakeCache() for _ in range(5)]
    eng.tiles = {j: object() for j in range(first, last + 1)}
    eng.fronts = {j: (object(), object()) for j in range(first, last + 1)}
    eng.poses = H.PoseRing()
    for j in range(first, last + 1):
        eng.poses.add(j, np.eye(4))
    eng.counts = {"gap_reset": 0, "reprime": 0, "warm_cold": 0, "warm_warm": 0, "warm_skip": 0}
    eng.sched = WarmupScheduler(cold_ms=121.0, warm_ms=91.3)
    eng.calls = []

    def fake_call(k, s, t_us):
        eng.calls.append((k, s, t_us))
        eng.caches[s].call(t_us)
    eng._warm_call = fake_call
    return eng


def test_engine_warm_waits_for_the_camera_history():
    eng = _engine_with_history(0, 34)
    rec = eng.warm(34)                                 # frame -1 (34 - 35) was never conditioned
    assert rec["warm"] == "wait" and eng.calls == []


def test_engine_warm_primes_the_frames_stream_at_its_timestamp():
    eng = _engine_with_history(0, 35)
    eng.sched.observe_step_start(35, time.monotonic())
    rec = eng.warm(35)
    assert rec["warm"] == "cold" and rec["stream"] == 0
    assert eng.calls == [(35, 0, t_us_of(35))]
    assert eng.counts["warm_cold"] == 1 and "ms" in rec


def test_engine_warm_treats_a_stream_with_a_stale_commit_as_cold():
    """A full stream whose last commit is not exactly 0.5 s before the frame (a frame of its phase was
    not committed) re-encodes its history: the call is cold, and the cache is reset first, as infer()
    does on a gap."""
    eng = _engine_with_history(0, 45)
    eng.caches[0].call(t_us_of(35))                    # stream 0 full, committed 1.0 s before frame 45
    eng.sched.observe_step_start(45, time.monotonic())
    rec = eng.warm(45)
    assert rec["warm"] == "cold" and eng.counts["warm_cold"] == 1
    assert eng.caches[0].resets == 1
    assert eng.calls == [(45, 0, t_us_of(45))]


def test_engine_warm_reports_a_warm_stream_as_warm():
    eng = _engine_with_history(0, 40)
    eng.caches[0].call(t_us_of(35))                    # stream 0 committed 0.5 s before frame 40
    eng.sched.observe_step_start(40, time.monotonic())
    assert eng.warm(40)["warm"] == "warm"
    assert eng.counts["warm_warm"] == 1
