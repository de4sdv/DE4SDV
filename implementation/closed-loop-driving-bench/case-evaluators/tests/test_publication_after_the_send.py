"""VC-DRIVING-015, -016 and -029 take the publication time from the publisher's
record written after the send, and VC-DRIVING-016 counts from the sample's
arrival at the agent.

The success criteria, from the model (closed_loop_driving_needs_requirements.sysml):

REQ-DRIVING-015: "Met when, over a 60 s window of a run of SC-DRIVING-001, every
plan in the records of the run is published once, equal to its record, with its
producer and its production time, within 100 ms of wall-clock time after that
production time."

REQ-DRIVING-016: "Met when, over a 60 s window of a run of SC-DRIVING-001, the
motion sample of every step in the records of the run is published once, equal
to its record, with its producer and its sample time, within 100 ms of
wall-clock time after the driving system received it."

REQ-DRIVING-029: "Met when, in each run of the criteria of REQ-DRIVING-023 to
REQ-DRIVING-028, a publication that the driving system is stopped, with the
cause of that run, follows within 100 ms of wall-clock time after the stop
response begins, and every later health publication of the run shows the mode
stopped."

What the producers write, and the tests rest on:

* the state publisher writes its `out.operational_state` record of a message
  after `event.Send()` returned (state-publisher/state_publisher_main.cpp,
  `sendFrames`); run_log.h stamps the envelope `t_mono_ns` at the write, so it is
  a time after the send on the S-CORE host's monotonic clock;
* the stamp in a PLAN or VEHICLE_STATE message, `publish_mono`, is the
  publisher's receipt of the plan or the sample (state-publisher/
  publisher_core.cpp, `OnPlan`, `OnEgoMotionSample`: `receiptMono`), so a
  VEHICLE_STATE's `publish_mono` equals its `sample_receipt_mono`; a HEALTH
  message carries the time it was made;
* the agent publishes the motion sample and then writes `out.ego_motion_sample`
  {stage, speed, longitudinalAcceleration, lateralAcceleration, yawRate,
  captureTime, frame, clocks} (agent/cc/agent_ffi.cpp): no arrival time. The
  frame store keeps the world snapshot the sample comes from until the six
  images of the frame are there, or 95 ms after it arrived (agent/cc/
  frame_store.h, `kDefaultDeadlineNs`). The tests add the arrival,
  `arrival_mono_ns` with `clocks.arrival_mono_ns = "monotonic"`, to the records
  they build; no producer writes it yet.

Each test edits a hard-linked copy of a synthetic run, or writes its own records.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections import Counter
from pathlib import Path

import pytest

import cases
import gaps
import strip
from conftest import CASE_RUN, add_arrivals, verdict
from runio import MissingEvidence, Run

AGENT = "score/drivingAgent.jsonl"
PUBLISHER = "score/statePublisher.jsonl"
OBSERVER = "guest/observer.jsonl"
NS = 1_000_000_000
VC015, VC016, VC029 = "VC-DRIVING-015", "VC-DRIVING-016", "VC-DRIVING-029"
ARRIVAL_FIELD = "score/drivingAgent.jsonl:out.ego_motion_sample.arrival_mono_ns"
VALUES = [("speed", "speed_kmh"), ("longitudinalAcceleration", "longitudinal_acceleration"),
          ("lateralAcceleration", "lateral_acceleration"), ("yawRate", "yaw_rate_dps")]


# ------------------------------------------------------------------ helpers
def copied(run_for, tmp_path: Path, name: str, tag: str) -> Path:
    return strip.copy_run(run_for(name).root, tmp_path / f"{name}-{tag}")


def rewrite(path: Path, fn) -> int:
    """Stream a JSONL file through fn(record) -> record, a list of records, or
    None to drop it, into a new file that replaces it (the copy's file is a hard
    link to the fixture). Returns the number of records fn changed or dropped."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    changed = 0
    with os.fdopen(fd, "w") as out, path.open() as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = json.loads(line)
            before = json.dumps(rec, sort_keys=True)
            new = fn(rec)
            new = [] if new is None else (new if isinstance(new, list) else [new])
            if len(new) != 1 or json.dumps(new[0], sort_keys=True) != before:
                changed += 1
            for r in new:
                out.write(json.dumps(r, separators=(",", ":")) + "\n")
    os.replace(tmp, path)
    return changed


def records(path: Path, pred) -> list[dict]:
    out = []
    with path.open() as fh:
        for line in fh:
            if line.strip():
                rec = json.loads(line)
                if pred(rec):
                    out.append(rec)
    return out


def is_pub(rec: dict, kind: str) -> bool:
    return rec["event"] == "out.operational_state" and rec["data"].get("kind") == kind


def is_obs(rec: dict, kind: int) -> bool:
    return rec["event"] == "in.operational_state" and rec["data"].get("kind") == kind


def is_sample(rec: dict) -> bool:
    return rec["event"] == "out.ego_motion_sample"


def pair(total: int) -> tuple[int, int]:
    return divmod(int(total), NS)


def window_samples(d: Path) -> list[dict]:
    """The agent's samples in VC-DRIVING-016's window: the first 60 s of their
    simulation time."""
    samples = records(d / AGENT, is_sample)
    t0 = min(s["data"]["captureTime"] for s in samples)
    return [s for s in samples if s["data"]["captureTime"] - t0 <= 60.0 + 1e-9]


def capture_ms(sample: dict) -> int:
    return int(round(sample["data"]["captureTime"] * 1000))


# ------------------------------------------------------------------ VC-DRIVING-015
PLAN_FRAME = 300


def plan_production_ns(d: Path, frame: int) -> int:
    [plan] = records(d / AGENT, lambda r: r["event"] == "out.plan"
                     and r["data"]["frameIndex"] == frame)
    return int(round(plan["data"]["productionTime"] * NS))


def test_vc015_a_plan_whose_publisher_record_is_written_120_ms_after_production_fails_although_the_stamp_is_2_ms_after_it(
        run_for, tmp_path):
    d = copied(run_for, tmp_path, CASE_RUN[VC015], "record-120ms")
    production = plan_production_ns(d, PLAN_FRAME)
    stamp = production + 2_000_000

    def pub(rec):
        if is_pub(rec, "PLAN") and rec["data"]["plan_frame_index"] == PLAN_FRAME:
            rec["t_mono_ns"] = production + 120_000_000
            rec["data"]["publish_mono_ns"] = stamp
        return rec

    def obs(rec):
        if is_obs(rec, 1) and rec["data"]["plan_frame_index"] == PLAN_FRAME:
            rec["data"]["publish_mono_s"], rec["data"]["publish_mono_ns"] = pair(stamp)
        return rec
    assert rewrite(d / PUBLISHER, pub) == 1
    assert rewrite(d / OBSERVER, obs) <= 1          # the generator's stamp may be it already
    [o] = records(d / OBSERVER, lambda r: is_obs(r, 1) and r["data"]["plan_frame_index"] == PLAN_FRAME)
    assert (o["data"]["publish_mono_s"], o["data"]["publish_mono_ns"]) == pair(stamp)
    res = verdict(Run(d), VC015)
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    assert res.measured["worst_latency_s"] == pytest.approx(0.120, abs=1e-6), res.measured
    assert res.measured["problem_count"] == 1, res.measured
    [p] = res.measured["problems"]
    assert p["frame"] == PLAN_FRAME and p["latency_s"] == pytest.approx(0.120, abs=1e-6), p


@pytest.mark.parametrize("offset_ns, outcome", [
    pytest.param(5_000, cases.FAIL, id="5-us-off-fails"),
    pytest.param(500, cases.PASS, id="0.5-us-off-passes"),
])
def test_vc015_a_published_production_time_that_differs_from_the_record_fails(run_for, tmp_path,
                                                                              offset_ns, outcome):
    d = copied(run_for, tmp_path, CASE_RUN[VC015], f"production-{offset_ns}")

    def obs(rec):
        if is_obs(rec, 1) and rec["data"]["plan_frame_index"] == PLAN_FRAME:
            dd = rec["data"]
            total = dd["plan_production_mono_s"] * NS + dd["plan_production_mono_ns"] + offset_ns
            dd["plan_production_mono_s"], dd["plan_production_mono_ns"] = pair(total)
        return rec
    assert rewrite(d / OBSERVER, obs) == 1
    res = verdict(Run(d), VC015)
    assert res.outcome == outcome, (res.outcome, res.measured, res.notes)
    assert res.measured["largest_production_time_difference_s"] == \
        pytest.approx(offset_ns / NS, abs=1e-9), res.measured
    if outcome == cases.FAIL:
        [p] = res.measured["problems"]
        assert p["frame"] == PLAN_FRAME and "production time" in p["problem"], p


def test_vc015_a_run_without_the_publishers_plan_records_is_missing_evidence(run_for, tmp_path):
    d = copied(run_for, tmp_path, CASE_RUN[VC015], "no-plan-records")
    assert rewrite(d / PUBLISHER, lambda r: None if is_pub(r, "PLAN") else r) > 600
    res = verdict(Run(d), VC015)
    assert res.outcome == cases.INCONCL, (res.outcome, res.measured, res.notes)
    assert res.missing == ["score/statePublisher.jsonl:out.operational_state kind=PLAN"], \
        res.missing


@pytest.mark.parametrize("count", [0, 2])
def test_vc015_a_plan_with_no_or_two_publisher_records_fails(run_for, tmp_path, count):
    d = copied(run_for, tmp_path, CASE_RUN[VC015], f"plan-records-{count}")

    def pub(rec):
        if is_pub(rec, "PLAN") and rec["data"]["plan_frame_index"] == PLAN_FRAME:
            return [rec] * count
        return rec
    assert rewrite(d / PUBLISHER, pub) == 1
    res = verdict(Run(d), VC015)
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    assert res.measured["problems"] == [{"frame": PLAN_FRAME, "publisher_records": count}], \
        res.measured


# ------------------------------------------------------------------ VC-DRIVING-016
def test_vc016_a_run_as_the_producers_write_it_is_inconclusive_and_names_the_arrival_and_its_change(
        run_for):
    run = run_for(CASE_RUN[VC016])
    assert not records(run.root / AGENT, lambda r: is_sample(r) and "arrival_mono_ns" in r["data"])
    res = verdict(run, VC016)
    assert res.outcome == cases.INCONCL, (res.outcome, res.measured, res.notes)
    assert res.missing == [ARRIVAL_FIELD], res.missing
    assert res.icd_changes == ["C13"] == [gaps.V2_GAPS[VC016]["change"]], res.icd_changes
    assert "95 ms" in res.notes[0] and "frame store" in res.notes[0], res.notes
    # what the records do show
    win = window_samples(run.root)
    sent = {r["data"]["sample_capture_sim_ms"]: r["t_mono_ns"]
            for r in records(run.root / PUBLISHER, lambda r: is_pub(r, "VEHICLE_STATE"))}
    worst = max(sent[capture_ms(s)] - s["t_mono_ns"] for s in win) / NS
    m = res.measured
    assert m["samples_in_window"] == len(win) == 601, m
    assert m["receipts_per_sample"] == {"1": len(win)}, m
    assert m["worst_record_to_publication_s"] == pytest.approx(worst, abs=1e-9), m
    assert m["samples_with_arrival"] == 0 and m["worst_latency_s"] is None, m


def test_vc016_the_same_run_with_arrivals_passes_and_counts_from_the_arrival(run_for, tmp_path):
    d = copied(run_for, tmp_path, CASE_RUN[VC016], "arrivals")
    assert add_arrivals(d, before_record_ns=40_000_000) == 700
    res = verdict(Run(d), VC016)
    assert res.outcome == cases.PASS, (res.outcome, res.missing, res.notes, res.measured)
    sent = {r["data"]["sample_capture_sim_ms"]: r["t_mono_ns"]
            for r in records(d / PUBLISHER, lambda r: is_pub(r, "VEHICLE_STATE"))}
    win = window_samples(d)
    worst = max(sent[capture_ms(s)] - s["data"]["arrival_mono_ns"] for s in win) / NS
    assert res.measured["samples_with_arrival"] == len(win), res.measured
    assert res.measured["worst_latency_s"] == pytest.approx(worst, abs=1e-9), res.measured


def test_vc016_a_publication_more_than_100_ms_after_its_arrival_fails_although_publish_mono_equals_the_receipt(
        run_for, tmp_path):
    d = copied(run_for, tmp_path, CASE_RUN[VC016], "late-after-arrival")
    assert add_arrivals(d, before_record_ns=40_000_000) == 700
    [s] = [s for s in window_samples(d) if capture_ms(s) == 30_000]
    arrival = s["data"]["arrival_mono_ns"]

    def pub(rec):
        if is_pub(rec, "VEHICLE_STATE") and rec["data"]["sample_capture_sim_ms"] == 30_000:
            rec["t_mono_ns"] = arrival + 120_000_000
            rec["data"]["publish_mono_ns"] = rec["data"]["sample_receipt_mono_ns"]
        return rec

    def obs(rec):
        if is_obs(rec, 2) and rec["data"]["sample_capture_ms"] == 30_000:
            dd = rec["data"]
            dd["publish_mono_s"], dd["publish_mono_ns"] = (dd["sample_receipt_mono_s"],
                                                           dd["sample_receipt_mono_ns"])
        return rec
    assert rewrite(d / PUBLISHER, pub) == 1
    assert rewrite(d / OBSERVER, obs) <= 1
    [o] = records(d / OBSERVER, lambda r: is_obs(r, 2) and r["data"]["sample_capture_ms"] == 30_000)
    assert (o["data"]["publish_mono_s"], o["data"]["publish_mono_ns"]) == \
        (o["data"]["sample_receipt_mono_s"], o["data"]["sample_receipt_mono_ns"])
    res = verdict(Run(d), VC016)
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    assert res.measured["worst_latency_s"] == pytest.approx(0.120, abs=1e-6), res.measured
    [p] = res.measured["problems"]
    assert p["capture_ms"] == pytest.approx(30_000) and \
        p["latency_s"] == pytest.approx(0.120, abs=1e-6), p


@pytest.mark.parametrize("arrivals", [False, True], ids=["without-arrivals", "with-arrivals"])
@pytest.mark.parametrize("agent_key, field", VALUES, ids=[f for _, f in VALUES])
def test_vc016_one_of_the_four_values_changed_in_one_receipt_fails(run_for, tmp_path, agent_key,
                                                                  field, arrivals):
    d = copied(run_for, tmp_path, CASE_RUN[VC016], f"value-{field}-{arrivals}")
    if arrivals:
        assert add_arrivals(d) == 700

    def obs(rec):
        if is_obs(rec, 2) and rec["data"]["sample_capture_ms"] == 30_000:
            rec["data"][field] += 0.01
        return rec
    assert rewrite(d / OBSERVER, obs) == 1
    res = verdict(Run(d), VC016)
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    [p] = res.measured["problems"]
    assert p["capture_ms"] == pytest.approx(30_000) and field in p["problem"], p
    assert res.measured["largest_value_difference"][field] == pytest.approx(0.01, abs=1e-6)


@pytest.mark.parametrize("count", [0, 2])
def test_vc016_a_sample_with_no_or_two_publisher_records_fails(run_for, tmp_path, count):
    d = copied(run_for, tmp_path, CASE_RUN[VC016], f"sample-records-{count}")
    assert add_arrivals(d) == 700

    def pub(rec):
        if is_pub(rec, "VEHICLE_STATE") and rec["data"]["sample_capture_sim_ms"] == 30_000:
            return [rec] * count
        return rec
    assert rewrite(d / PUBLISHER, pub) == 1
    res = verdict(Run(d), VC016)
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    assert res.measured["problems"] == [{"capture_ms": 30_000.0, "publisher_records": count}], \
        res.measured


def test_vc016_a_run_without_the_publishers_vehicle_state_records_is_missing_evidence(run_for,
                                                                                    tmp_path):
    d = copied(run_for, tmp_path, CASE_RUN[VC016], "no-vehicle-state-records")
    assert add_arrivals(d) == 700
    assert rewrite(d / PUBLISHER, lambda r: None if is_pub(r, "VEHICLE_STATE") else r) == 700
    res = verdict(Run(d), VC016)
    assert res.outcome == cases.INCONCL, (res.outcome, res.measured, res.notes)
    assert res.missing == ["score/statePublisher.jsonl:out.operational_state kind=VEHICLE_STATE"], \
        res.missing


def test_vc016_is_a_case_with_a_known_gap():
    gap = gaps.V2_GAPS[VC016]
    assert gap["change"] == "C13" and "arrival_mono_ns" in gap["missing"], gap
    assert "C13" not in gaps.ICD_CHANGES          # proposed, not a change ICD v2 adopted


# ------------------------------------------------------------------ VC-DRIVING-029
def test_vc029_the_stop_publications_record_written_120_ms_after_the_stop_begin_fails_although_the_stamp_is_in_time(
        run_for, tmp_path):
    d = copied(run_for, tmp_path, CASE_RUN[VC029], "stop-record-120ms")
    [begin] = records(d / AGENT, lambda r: r["event"] == "stop_response.begin")
    b = begin["t_mono_ns"]
    stopped = [r for r in records(d / PUBLISHER, lambda r: is_pub(r, "HEALTH"))
               if r["data"]["mode"] in ("kStopResponse", "kStandstill")]
    first = min(stopped, key=lambda r: r["t_mono_ns"])
    assert first["data"]["cause"] == begin["data"]["cause"]
    assert 0 < first["data"]["publish_mono_ns"] - b < 100_000_000       # the stamp is in time
    shift = b + 120_000_000 - first["t_mono_ns"]
    later = [r for r in records(d / PUBLISHER, lambda r: is_pub(r, "HEALTH"))
             if r["t_mono_ns"] >= first["t_mono_ns"]]

    def pub(rec):
        if is_pub(rec, "HEALTH") and rec["t_mono_ns"] >= first["t_mono_ns"]:
            rec["t_mono_ns"] += shift                                   # the records, not the stamps
        return rec
    assert rewrite(d / PUBLISHER, pub) == len(later)
    res = verdict(Run(d), VC029)
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    assert res.measured["latency_s"] == pytest.approx(0.120, abs=1e-6), res.measured
    assert res.measured["stop_publication_mono"] == pytest.approx((b + 120_000_000) / NS,
                                                                  abs=1e-9), res.measured


# ------------------------------------------------------------------ the readers
T_REAL0 = 1_794_000_000_000_000_000


def mini_run(tmp_path: Path, files: dict[str, list[dict]]) -> Run:
    d = tmp_path / "run"
    d.mkdir()
    (d / "run_record.json").write_text(json.dumps(
        {"contractIdentity": "de4sdv.driving.icd.v2", "scenario": "closedLoopRoute"}) + "\n")
    for rel, recs in files.items():
        (d / rel).parent.mkdir(parents=True, exist_ok=True)
        with (d / rel).open("w") as fh:
            for rec in recs:
                fh.write(json.dumps(rec) + "\n")
    return Run(d)


def envelope(t_mono_ns: int, host: str, component: str, event: str, seq: int, data: dict) -> dict:
    return {"t_mono_ns": t_mono_ns, "t_real_ns": T_REAL0 + t_mono_ns, "host": host,
            "component": component, "event": event, "seq": seq, "data": data}


def test_plan_side_reads_the_publishers_plan_records_and_their_time_after_the_send(tmp_path):
    plan = {"kind": "PLAN", "sequence": 7, "producer": "statePublisher",
            "publish_mono_ns": 812_344_000_000, "publish_real_ns": T_REAL0 + 812_344_000_000,
            "plan_frame_index": 3299, "plan_capture_sim_ms": 329_900,
            "plan_production_mono_ns": 812_340_000_001}
    lines = [
        envelope(812_344_150_000, "score", "statePublisher", "out.operational_state", 7, plan),
        envelope(812_344_160_000, "score", "statePublisher", "out.operational_state", 8,
                 dict(plan, kind=1, sequence=8, plan_frame_index=3300)),   # the kind as a number
        envelope(812_344_170_000, "score", "statePublisher", "in.plan", 0,
                 {"plan_frame_index": 3301}),
    ]
    run = mini_run(tmp_path, {PUBLISHER: lines})
    [p] = run.plan_side()
    assert p["t_mono"] == pytest.approx(812.34415, abs=1e-9)          # the record, after the send
    assert p["publish_mono"] == pytest.approx(812.344, abs=1e-9)      # the stamp in the message
    assert p["production_mono"] == pytest.approx(812.340000001, abs=1e-9)
    assert p["frame"] == 3299 and p["file"] == PUBLISHER and p["rec"]["seq"] == 7


def test_vs_side_reads_the_publishers_vehicle_state_records_and_their_time_after_the_send(tmp_path):
    vs = {"kind": "VEHICLE_STATE", "sequence": 4, "producer": "statePublisher",
          "publish_mono_ns": 437_774_779_299, "publish_real_ns": T_REAL0 + 437_774_779_299,
          "speed_kmh": 10.0, "longitudinal_acceleration": 0.5, "lateral_acceleration": 0.0,
          "yaw_rate_dps": 0.0, "sample_capture_sim_ms": 1_026_000,
          "sample_receipt_mono_ns": 437_774_779_299}
    lines = [
        envelope(437_774_828_599, "score", "statePublisher", "out.operational_state", 4, vs),
        envelope(437_774_900_000, "score", "statePublisher", "out.operational_state", 5,
                 dict(vs, kind=2, sequence=5, sample_capture_sim_ms=1_026_100)),
    ]
    run = mini_run(tmp_path, {PUBLISHER: lines})
    [v] = run.vs_side()
    assert v["t_mono"] == pytest.approx(437.774828599, abs=1e-9)
    assert v["publish_mono"] == v["receipt_mono"] == pytest.approx(437.774779299, abs=1e-9)
    assert v["capture_ms"] == 1_026_000 and v["file"] == PUBLISHER


@pytest.mark.parametrize("kind", [True, 1.0], ids=["json-true", "float-1.0"])
def test_a_kind_of_another_type_is_not_read(tmp_path, kind):
    """The observer's kind is the u32 value: a JSON true or 1.0 is not kind 1,
    though Python counts both equal to 1 (runio._is). The publisher's kind is
    the name: a record whose kind is the number is not read."""
    obs = {"kind": kind, "sequence": 1, "producer": "statePublisher", "publish_mono_s": 100,
           "publish_mono_ns": 5, "plan_frame_index": 1, "plan_capture_ms": 100,
           "plan_producer": "drivingAgent/inferPlan"}
    pub = {"kind": 3, "sequence": 1, "producer": "statePublisher", "publish_mono_ns": 100_000_000_005,
           "mode": "kStopResponse", "cause": "kCameraStale"}
    run = mini_run(tmp_path, {
        OBSERVER: [envelope(100_000_000_000, "guest", "observer", "in.operational_state", 1, obs)],
        PUBLISHER: [envelope(100_000_000_010, "score", "statePublisher", "out.operational_state", 1,
                             pub)]})
    with pytest.raises(MissingEvidence) as exc:
        run.plan_pubs()
    assert "kind=1 (PLAN)" in exc.value.what, exc.value.what
    assert run.health_side() == []


def test_ego_samples_read_the_arrival_only_as_whole_monotonic_nanoseconds(tmp_path):
    def sample(frame: int, **extra) -> dict:
        d = {"stage": "s", "speed": 1.0, "longitudinalAcceleration": 0.0,
             "lateralAcceleration": 0.0, "yawRate": 0.0, "captureTime": frame / 10,
             "frame": frame, "clocks": {"captureTime": "simulation"}}
        for k, v in extra.items():
            if k == "clocks":
                d["clocks"] = dict(d["clocks"], **v)
            else:
                d[k] = v
        return envelope(500_000_000_000 + frame, "score", "drivingAgent",
                        "out.ego_motion_sample", frame, d)
    mono = {"arrival_mono_ns": "monotonic"}
    lines = [sample(1, arrival_mono_ns=499_960_000_001, clocks=mono),
             sample(2, arrival_mono_ns=499_960_000_002),                       # no clock
             sample(3, arrival_mono_ns=499.96, clocks=mono),                   # not whole ns
             sample(4, arrival_mono_ns=True, clocks=mono),
             sample(5, arrival_mono_ns=499_960_000_005, clocks={"arrival_mono_ns": "real"}),
             sample(6)]
    got = {s["step"]: s["arrival_mono"] for s in mini_run(tmp_path, {AGENT: lines}).ego_samples()}
    assert got[1] == pytest.approx(499.960000001, abs=1e-12)
    assert [got[f] for f in (2, 3, 4, 5, 6)] == [None] * 5, got


def test_vs_pubs_read_the_four_values_and_the_producer(tmp_path):
    obs = {"kind": 2, "sequence": 3, "producer": "statePublisher", "publish_mono_s": 700,
           "publish_mono_ns": 50_000_000, "speed_kmh": 36.5, "longitudinal_acceleration": 0.5,
           "lateral_acceleration": -0.25, "yaw_rate_dps": 1.5, "sample_capture_ms": 330_100,
           "sample_receipt_mono_s": 700, "sample_receipt_mono_ns": 50_000_000}
    run = mini_run(tmp_path, {OBSERVER: [envelope(6_000_000_000, "guest", "observer",
                                                  "in.operational_state", 1, obs)]})
    [v] = run.vs_pubs()
    assert (v["speed_kmh"], v["accel"], v["lateral"], v["yaw_dps"]) == (36.5, 0.5, -0.25, 1.5)
    assert v["producer"] == "statePublisher"


# ------------------------------------------------------------------ the generator
def test_the_generator_writes_publish_mono_as_the_publisher_does(fixture_root):
    """For PLAN and VEHICLE_STATE the stamp is the publisher's receipt; for
    VEHICLE_STATE equal to sample_receipt_mono; the publisher's record is
    written after the send, later than the stamp."""
    kinds: Counter = Counter()
    for run_dir in sorted(p for p in fixture_root.iterdir() if (p / PUBLISHER).exists()):
        for rec in records(run_dir / PUBLISHER, lambda r: r["event"] == "out.operational_state"):
            d = rec["data"]
            kinds[d["kind"]] += 1
            assert rec["t_mono_ns"] > d["publish_mono_ns"], (run_dir.name, rec)
            if d["kind"] == "VEHICLE_STATE":
                assert d["publish_mono_ns"] == d["sample_receipt_mono_ns"], (run_dir.name, d)
            if d["kind"] == "PLAN":
                assert d["publish_mono_ns"] > d["plan_production_mono_ns"], (run_dir.name, d)
        for rec in records(run_dir / OBSERVER, lambda r: is_obs(r, 2)):
            d = rec["data"]
            assert (d["publish_mono_s"], d["publish_mono_ns"]) == \
                (d["sample_receipt_mono_s"], d["sample_receipt_mono_ns"]), (run_dir.name, d)
    assert kinds["VEHICLE_STATE"] > 0 and kinds["PLAN"] > 0 and kinds["HEALTH"] > 0, kinds
