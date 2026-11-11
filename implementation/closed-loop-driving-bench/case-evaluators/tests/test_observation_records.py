"""The observation records as the state publisher and the IVI observer app write them (ICD A34).

The state publisher (S-CORE host) writes one `out.operational_state` record
per message it sent, in score/statePublisher.jsonl. `data.kind` names the
kind; the stamps it takes itself are whole nanosecond counts and simulation
milliseconds with the clock in the name; `mode` and `cause` are names
(state-publisher/publisher_core.cpp:574-600, 708-729, 812-827;
state_publisher_main.cpp:452, `seq` is the kind's sequence).

The observer app (IVI guest) writes one `in.operational_state` record per
message it received, in guest/observer.jsonl: the 43 fields of ICD section 3
in its order for every kind, the fields of the other kinds zero, "" or [];
`kind`, `mode` and `cause` as their u32 values with `kind_name`, `mode_name`
and `cause_name` beside them; then `clocks`
(ivi-observer/app/src/org/de4sdv/drivingstate/StateRecord.java:32, 90-100,
105-158). Its envelope's `t_real_ns` is the IVI's receipt time in whole
milliseconds (TypedStateSubscriber.java:392-393).

The case evaluators read only these records. A run that carries only the names
the evaluators' own synthetic runs used to write (`rx.plan`,
`rx.vehicle_state`, `rx.health`, `out.plan`, `out.vehicle_state`,
`out.health`) is missing evidence.

The key lists here are taken from the producers' source, not from the
generator, so the generator is checked against them. The records of the
reader tests are written here, with values of their own.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections import Counter
from pathlib import Path

import pytest

import cases
import strip
from conftest import add_arrivals, verdict
from runio import MissingEvidence, Run

OBSERVER = "guest/observer.jsonl"
OBSERVER_EVENT = "in.operational_state"
PUBLISHER = "score/statePublisher.jsonl"
PUBLISHER_EVENT = "out.operational_state"

# ICD section 3, field 3; StateRecord.java:183-194; publisher_core.cpp:245-253
KIND_NAME = {1: "PLAN", 2: "VEHICLE_STATE", 3: "HEALTH"}
KIND_VALUE = {v: k for k, v in KIND_NAME.items()}
# StateRecord.java:198-246; publisher_core.cpp:255-283
MODE_NAMES = ["kStarting", "kDriving", "kStopResponse", "kStandstill", "kRefused"]
CAUSE_NAMES = ["kNone", "kCameraMissing", "kCameraInvalid", "kCameraStale", "kMotionInvalid",
               "kMotionStale", "kRouteStale", "kRouteEmpty", "kPlanStale", "kPlanInvalid",
               "kCommandTimeout", "kCheckpointRefused", "kRunEnd"]

# The 43 fields of ICD section 3 in its order, with the value the observer
# records for a field of another kind (StateRecord.java:39-87, 105-158).
OBSERVER_FIELDS = [
    ("schema_major", 0), ("schema_minor", 0), ("kind", 0), ("sequence", 0), ("producer", ""),
    ("publish_real_s", 0), ("publish_real_ns", 0), ("publish_mono_s", 0), ("publish_mono_ns", 0),
    ("plan_frame_index", 0), ("plan_capture_ms", 0), ("plan_production_mono_s", 0),
    ("plan_production_mono_ns", 0), ("plan_reference", ""), ("run_record", ""),
    ("plan_producer", ""), ("plan_sample_count", 0), ("plan_horizon_s", 0.0),
    ("plan_acceleration", []), ("plan_curvature", []), ("plan_x", []), ("plan_y", []),
    ("speed_kmh", 0.0), ("longitudinal_acceleration", 0.0), ("lateral_acceleration", 0.0),
    ("yaw_rate_dps", 0.0), ("sample_capture_ms", 0), ("sample_receipt_mono_s", 0),
    ("sample_receipt_mono_ns", 0),
    ("mode", 0), ("cause", 0), ("mode_source", ""), ("cause_since_mono_s", 0),
    ("cause_since_mono_ns", 0), ("last_plan_frame_index", 0), ("last_plan_capture_ms", 0),
    ("step_capture_ms", 0), ("last_plan_production_mono_s", 0),
    ("last_plan_production_mono_ns", 0), ("dropped_samples", 0),
    ("checkpoint_expected_sha256", ""), ("checkpoint_actual_sha256", ""), ("refusal_reason", ""),
]
assert len(OBSERVER_FIELDS) == 43
# the record's keys in order: a name after kind, mode and cause, clocks last
OBSERVER_KEYS = []
for _name, _ in OBSERVER_FIELDS:
    OBSERVER_KEYS.append(_name)
    if _name in ("kind", "mode", "cause"):
        OBSERVER_KEYS.append(f"{_name}_name")
OBSERVER_KEYS.append("clocks")
# StateRecord.java:90-100
OBSERVER_CLOCKS = {
    "publish_real_s": "real", "publish_real_ns": "real",
    "publish_mono_s": "monotonic", "publish_mono_ns": "monotonic",
    "plan_capture_ms": "simulation",
    "plan_production_mono_s": "monotonic", "plan_production_mono_ns": "monotonic",
    "sample_capture_ms": "simulation",
    "sample_receipt_mono_s": "monotonic", "sample_receipt_mono_ns": "monotonic",
    "cause_since_mono_s": "monotonic", "cause_since_mono_ns": "monotonic",
    "last_plan_capture_ms": "simulation", "step_capture_ms": "simulation",
    "last_plan_production_mono_s": "monotonic", "last_plan_production_mono_ns": "monotonic",
}

# The publisher's `data` per kind, in its order (publisher_core.cpp:574-600,
# 708-729, 812-827); the three refusal fields only once a refusal is set
# (publisher_core.cpp:590-594).
PUBLISHER_KEYS = {
    "PLAN": ["kind", "sequence", "producer", "publish_mono_ns", "publish_real_ns",
             "plan_frame_index", "plan_capture_sim_ms", "plan_production_mono_ns",
             "plan_reference", "run_record", "plan_producer", "plan_sample_count",
             "plan_horizon_s", "plan_acceleration", "plan_curvature", "plan_x", "plan_y",
             "clocks"],
    "VEHICLE_STATE": ["kind", "sequence", "producer", "publish_mono_ns", "publish_real_ns",
                      "speed_kmh", "longitudinal_acceleration", "lateral_acceleration",
                      "yaw_rate_dps", "sample_capture_sim_ms", "sample_receipt_mono_ns",
                      "clocks"],
    "HEALTH": ["kind", "sequence", "producer", "publish_mono_ns", "publish_real_ns", "mode",
               "cause", "mode_source", "cause_since_mono_ns", "last_plan_frame_index",
               "last_plan_capture_sim_ms", "step_capture_sim_ms",
               "last_plan_production_mono_ns", "dropped_samples", "clocks"],
}
PUBLISHER_REFUSAL_KEYS = ["checkpoint_expected_sha256", "checkpoint_actual_sha256",
                          "refusal_reason"]
PUBLISHER_CLOCKS = {
    "PLAN": {"publish_mono_ns": "monotonic", "publish_real_ns": "real",
             "plan_capture_sim_ms": "simulation", "plan_production_mono_ns": "monotonic"},
    "VEHICLE_STATE": {"publish_mono_ns": "monotonic", "publish_real_ns": "real",
                      "sample_capture_sim_ms": "simulation",
                      "sample_receipt_mono_ns": "monotonic"},
    "HEALTH": {"publish_mono_ns": "monotonic", "publish_real_ns": "real",
               "cause_since_mono_ns": "monotonic", "last_plan_capture_sim_ms": "simulation",
               "step_capture_sim_ms": "simulation", "last_plan_production_mono_ns": "monotonic"},
}

# The names the evaluators' synthetic runs used before ICD A34, and the section 3
# fields each kind carried under them.
OLD_OBSERVER_EVENT = {1: "rx.plan", 2: "rx.vehicle_state", 3: "rx.health"}
OLD_PUBLISHER_EVENT = {"PLAN": "out.plan", "VEHICLE_STATE": "out.vehicle_state",
                       "HEALTH": "out.health"}
_HEADER = ["schema_major", "schema_minor", "kind", "sequence", "producer", "publish_real_s",
           "publish_real_ns", "publish_mono_s", "publish_mono_ns"]
OLD_KEYS = {
    1: _HEADER + ["plan_frame_index", "plan_capture_ms", "plan_production_mono_s",
                  "plan_production_mono_ns", "plan_reference", "run_record", "plan_producer",
                  "plan_sample_count", "plan_horizon_s", "plan_acceleration",
                  "plan_curvature", "plan_x", "plan_y"],
    2: _HEADER + ["speed_kmh", "longitudinal_acceleration", "lateral_acceleration",
                  "yaw_rate_dps", "sample_capture_ms", "sample_receipt_mono_s",
                  "sample_receipt_mono_ns"],
    3: _HEADER + ["mode", "cause", "mode_source", "cause_since_mono_s", "cause_since_mono_ns",
                  "last_plan_frame_index", "last_plan_capture_ms", "step_capture_ms",
                  "last_plan_production_mono_s", "last_plan_production_mono_ns",
                  "dropped_samples", "checkpoint_expected_sha256",
                  "checkpoint_actual_sha256", "refusal_reason"],
}

NS = 1_000_000_000


# ------------------------------------------------------------------ builders
def observer_data(fields: dict) -> dict:
    """An observer record's `data` from the section 3 fields of one message."""
    unknown = set(fields) - {name for name, _ in OBSERVER_FIELDS}
    assert not unknown, unknown
    out: dict = {}
    for name, default in OBSERVER_FIELDS:
        out[name] = fields.get(name, default)
        if name == "kind":
            out["kind_name"] = KIND_NAME.get(out["kind"], "KIND_UNSPECIFIED")
        elif name == "mode":
            out["mode_name"] = MODE_NAMES[out["mode"]]
        elif name == "cause":
            out["cause_name"] = CAUSE_NAMES[out["cause"]]
    out["clocks"] = dict(OBSERVER_CLOCKS)
    return out


def publisher_data(kind: str, fields: dict) -> dict:
    """A publisher record's `data` for one message, in the publisher's order."""
    keys = list(PUBLISHER_KEYS[kind])
    if kind == "HEALTH" and any(k in fields for k in PUBLISHER_REFUSAL_KEYS):
        keys[-1:-1] = PUBLISHER_REFUSAL_KEYS
    out: dict = {}
    for k in keys:
        out[k] = kind if k == "kind" else (dict(PUBLISHER_CLOCKS[kind]) if k == "clocks"
                                           else fields[k])
    return out


def observer_line(seq: int, t_mono_ns: int, t_real_ns: int, **fields) -> dict:
    return {"t_mono_ns": t_mono_ns, "t_real_ns": t_real_ns, "host": "guest",
            "component": "observer", "event": OBSERVER_EVENT, "seq": seq,
            "data": observer_data(fields)}


def publisher_line(t_mono_ns: int, t_real_ns: int, kind: str, **fields) -> dict:
    return {"t_mono_ns": t_mono_ns, "t_real_ns": t_real_ns, "host": "score",
            "component": "statePublisher", "event": PUBLISHER_EVENT,
            "seq": fields["sequence"], "data": publisher_data(kind, fields)}


def mini_run(tmp_path: Path, rel: str, records: list[dict]) -> Run:
    """A run directory holding one record file, written here."""
    d = tmp_path / "run"
    (d / rel).parent.mkdir(parents=True)
    (d / "run_record.json").write_text(json.dumps(
        {"contractIdentity": "de4sdv.driving.icd.v2", "scenario": "closedLoopRoute"}) + "\n")
    with (d / rel).open("w") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")
    return Run(d)


# ------------------------------------------------------------------ converters
def rewrite_jsonl(path: Path, fn) -> int:
    """Stream a JSONL file through fn(record) -> record into a new file that
    replaces it (the copy's file is a hard link to the fixture). Returns the
    number of records changed."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    changed = 0
    with os.fdopen(fd, "w") as out, path.open() as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = json.loads(line)
            new = fn(rec)
            if new != rec:
                changed += 1
            out.write(json.dumps(new, separators=(",", ":")) + "\n")
    os.replace(tmp, path)
    return changed


def _total(d: dict, base: str) -> int:
    """A section 3 `_s`/`_ns` pair as a whole nanosecond count."""
    return int(d[base + "_s"]) * NS + int(d[base + "_ns"])


def _pair(total: int) -> tuple[int, int]:
    return divmod(int(total), NS)


def as_written_observer(rec: dict) -> dict:
    """An old observer record as the observer writes it; others unchanged."""
    if rec["event"] not in OLD_OBSERVER_EVENT.values():
        return rec
    return dict(rec, event=OBSERVER_EVENT, data=observer_data(rec["data"]))


def as_written_publisher(rec: dict) -> dict:
    """An old publisher record as the publisher writes it; others unchanged."""
    kind = {v: k for k, v in OLD_PUBLISHER_EVENT.items()}.get(rec["event"])
    if kind is None:
        return rec
    d = rec["data"]
    f = {"sequence": d["sequence"], "producer": d["producer"],
         "publish_mono_ns": _total(d, "publish_mono"),
         "publish_real_ns": _total(d, "publish_real")}
    if kind == "PLAN":
        f.update(plan_frame_index=d["plan_frame_index"], plan_capture_sim_ms=d["plan_capture_ms"],
                 plan_production_mono_ns=_total(d, "plan_production_mono"),
                 plan_reference=d["plan_reference"], run_record=d["run_record"],
                 plan_producer=d["plan_producer"], plan_sample_count=d["plan_sample_count"],
                 plan_horizon_s=d["plan_horizon_s"], plan_acceleration=d["plan_acceleration"],
                 plan_curvature=d["plan_curvature"], plan_x=d["plan_x"], plan_y=d["plan_y"])
    elif kind == "VEHICLE_STATE":
        f.update(speed_kmh=d["speed_kmh"],
                 longitudinal_acceleration=d["longitudinal_acceleration"],
                 lateral_acceleration=d["lateral_acceleration"], yaw_rate_dps=d["yaw_rate_dps"],
                 sample_capture_sim_ms=d["sample_capture_ms"],
                 sample_receipt_mono_ns=_total(d, "sample_receipt_mono"))
    else:
        f.update(mode=MODE_NAMES[d["mode"]], cause=CAUSE_NAMES[d["cause"]],
                 mode_source=d["mode_source"],
                 cause_since_mono_ns=_total(d, "cause_since_mono"),
                 last_plan_frame_index=d["last_plan_frame_index"],
                 last_plan_capture_sim_ms=d["last_plan_capture_ms"],
                 step_capture_sim_ms=d["step_capture_ms"],
                 last_plan_production_mono_ns=_total(d, "last_plan_production_mono"),
                 dropped_samples=d["dropped_samples"])
        if d.get("refusal_reason") or d.get("checkpoint_expected_sha256"):
            f.update({k: d[k] for k in PUBLISHER_REFUSAL_KEYS})
    return dict(rec, event=PUBLISHER_EVENT, seq=d["sequence"], data=publisher_data(kind, f))


def as_before_observer(rec: dict) -> dict:
    """An observer record under the name and with the fields used before A34."""
    k = rec["data"].get("kind")
    if rec["event"] != OBSERVER_EVENT or k not in OLD_OBSERVER_EVENT:
        return rec
    return dict(rec, event=OLD_OBSERVER_EVENT[k], data={key: rec["data"][key] for key in OLD_KEYS[k]})


def as_before_publisher(rec: dict) -> dict:
    """A publisher record under the name and with the fields used before A34."""
    kind = rec["data"].get("kind")
    if rec["event"] != PUBLISHER_EVENT or kind not in OLD_PUBLISHER_EVENT:
        return rec
    d = rec["data"]
    body = {"schema_major": 2, "schema_minor": 0, "kind": KIND_VALUE[kind],
            "sequence": d["sequence"], "producer": d["producer"]}
    body["publish_real_s"], body["publish_real_ns"] = _pair(d["publish_real_ns"])
    body["publish_mono_s"], body["publish_mono_ns"] = _pair(d["publish_mono_ns"])
    if kind == "PLAN":
        body.update(plan_frame_index=d["plan_frame_index"], plan_capture_ms=d["plan_capture_sim_ms"])
        body["plan_production_mono_s"], body["plan_production_mono_ns"] = \
            _pair(d["plan_production_mono_ns"])
        body.update({k: d[k] for k in ("plan_reference", "run_record", "plan_producer",
                                       "plan_sample_count", "plan_horizon_s",
                                       "plan_acceleration", "plan_curvature", "plan_x",
                                       "plan_y")})
    elif kind == "VEHICLE_STATE":
        body.update({k: d[k] for k in ("speed_kmh", "longitudinal_acceleration",
                                       "lateral_acceleration", "yaw_rate_dps")})
        body["sample_capture_ms"] = d["sample_capture_sim_ms"]
        body["sample_receipt_mono_s"], body["sample_receipt_mono_ns"] = \
            _pair(d["sample_receipt_mono_ns"])
    else:
        body.update(mode=MODE_NAMES.index(d["mode"]), cause=CAUSE_NAMES.index(d["cause"]),
                    mode_source=d["mode_source"])
        body["cause_since_mono_s"], body["cause_since_mono_ns"] = _pair(d["cause_since_mono_ns"])
        body.update(last_plan_frame_index=d["last_plan_frame_index"],
                    last_plan_capture_ms=d["last_plan_capture_sim_ms"],
                    step_capture_ms=d["step_capture_sim_ms"])
        body["last_plan_production_mono_s"], body["last_plan_production_mono_ns"] = \
            _pair(d["last_plan_production_mono_ns"])
        body["dropped_samples"] = d["dropped_samples"]
        body.update({k: d.get(k, "") for k in PUBLISHER_REFUSAL_KEYS})
    return dict(rec, event=OLD_PUBLISHER_EVENT[kind], data=body)


def converted(run_for, tmp_path: Path, name: str, shape: str) -> Path:
    """A hard-linked copy of a generator run with both observation files in
    `shape`: "written" (as the producers write them) or "before" (the names
    used before A34). Records already in that shape are left as they are."""
    d = strip.copy_run(run_for(name).root, tmp_path / f"{name}-{shape}")
    obs, pub = ((as_written_observer, as_written_publisher) if shape == "written"
                else (as_before_observer, as_before_publisher))
    rewrite_jsonl(d / OBSERVER, obs)
    rewrite_jsonl(d / PUBLISHER, pub)
    return d


def events_of(path: Path) -> Counter:
    c: Counter = Counter()
    with path.open() as fh:
        for line in fh:
            if line.strip():
                c[json.loads(line)["event"]] += 1
    return c


# ------------------------------------------------------------------ the cases
# Every case that reads one of the two files, on the run conftest.CASE_RUN
# names for it, and the second start of REQ-DRIVING-035.
AFFECTED = [("VC-DRIVING-015", "nominal"), ("VC-DRIVING-016", "nominal"),
            ("VC-DRIVING-017", "comm-stop"), ("VC-DRIVING-029", "fault-camera_missing"),
            ("VC-DRIVING-035", "refusal-mismatch"), ("VC-DRIVING-035", "refusal-unpinned")]
# the file and the record (event, kind) each case reads
READS = {"VC-DRIVING-015": (OBSERVER, OBSERVER_EVENT, "PLAN"),
         "VC-DRIVING-016": (OBSERVER, OBSERVER_EVENT, "VEHICLE_STATE"),
         "VC-DRIVING-017": (OBSERVER, OBSERVER_EVENT, "HEALTH"),
         "VC-DRIVING-029": (PUBLISHER, PUBLISHER_EVENT, "HEALTH"),
         "VC-DRIVING-035": (OBSERVER, OBSERVER_EVENT, "HEALTH")}


@pytest.mark.parametrize("vc, name", AFFECTED)
def test_a_case_judges_a_run_whose_records_are_as_the_producers_write_them(vc, name, run_for,
                                                                          tmp_path):
    d = converted(run_for, tmp_path, name, "written")
    assert not set(events_of(d / OBSERVER)) & set(OLD_OBSERVER_EVENT.values())
    assert not set(events_of(d / PUBLISHER)) & set(OLD_PUBLISHER_EVENT.values())
    if vc == "VC-DRIVING-016":
        # it also needs the sample's arrival, which no producer writes yet
        # (gaps.V2_GAPS): the copy gets it
        assert add_arrivals(d) == 700
    res = verdict(Run(d), vc)
    assert res.outcome == cases.PASS, (vc, res.outcome, res.missing, res.notes)
    rel = READS[vc][0]
    assert any(e["file"] == rel for e in res.evidence), res.evidence


@pytest.mark.parametrize("vc, name", AFFECTED)
def test_a_run_with_only_the_names_used_before_is_missing_evidence(vc, name, run_for, tmp_path):
    d = converted(run_for, tmp_path, name, "before")
    assert OBSERVER_EVENT not in events_of(d / OBSERVER)
    assert PUBLISHER_EVENT not in events_of(d / PUBLISHER)
    res = verdict(Run(d), vc)
    assert res.outcome == cases.INCONCL, (vc, res.outcome, res.measured)
    rel, event, kind = READS[vc]
    assert len(res.missing) == 1, res.missing
    assert rel in res.missing[0] and event in res.missing[0] and kind in res.missing[0], \
        res.missing


@pytest.mark.parametrize("vc", sorted(READS))
def test_a_case_that_reads_the_observation_records_names_amendment_a34(vc):
    import gaps
    assert "A34" in gaps.amendments_for(vc), gaps.amendments_for(vc)
    assert sorted(gaps.AMENDMENT_CHANGES["A34"]["unblocks"]) == sorted(READS)


# ------------------------------------------------------------------ the generator
@pytest.mark.parametrize("name", ["nominal", "fault-camera_missing", "fault-plan_invalid_nan",
                                  "comm-stop", "refusal-mismatch", "refusal-unpinned",
                                  "aaos-ref1"])
def test_the_generator_writes_the_observation_records_as_the_producers_do(name, run_for):
    root = run_for(name).root
    published: dict[tuple[str, int], dict] = {}
    kinds_published: Counter = Counter()
    with (root / PUBLISHER).open() as fh:
        for line in fh:
            rec = json.loads(line)
            assert rec["event"] not in OLD_PUBLISHER_EVENT.values(), rec["event"]
            if rec["event"] != PUBLISHER_EVENT:
                continue
            d = rec["data"]
            kind = d["kind"]
            keys = list(PUBLISHER_KEYS[kind])
            if kind == "HEALTH" and "refusal_reason" in d:
                keys[-1:-1] = PUBLISHER_REFUSAL_KEYS
            assert list(d) == keys, (kind, list(d))
            assert d["clocks"] == PUBLISHER_CLOCKS[kind], d["clocks"]
            assert rec["seq"] == d["sequence"], (rec["seq"], d["sequence"])
            assert (rec["host"], rec["component"]) == ("score", "statePublisher")
            if kind == "HEALTH":
                assert d["mode"] in MODE_NAMES and d["cause"] in CAUSE_NAMES, d
            kinds_published[kind] += 1
            published[(kind, d["sequence"])] = d
    receipts = 0
    with (root / OBSERVER).open() as fh:
        for line in fh:
            rec = json.loads(line)
            assert rec["event"] not in OLD_OBSERVER_EVENT.values(), rec["event"]
            if rec["event"] != OBSERVER_EVENT:
                continue
            receipts += 1
            d = rec["data"]
            assert list(d) == OBSERVER_KEYS, list(d)
            assert d["clocks"] == OBSERVER_CLOCKS
            assert d["kind_name"] == KIND_NAME[d["kind"]]
            assert d["mode_name"] == MODE_NAMES[d["mode"]]
            assert d["cause_name"] == CAUSE_NAMES[d["cause"]]
            assert (rec["host"], rec["component"]) == ("guest", "observer")
            # the same message as the publisher's record of its kind and sequence
            p = published[(d["kind_name"], d["sequence"])]
            assert _total(d, "publish_mono") == p["publish_mono_ns"]
            assert _total(d, "publish_real") == p["publish_real_ns"]
            if d["kind"] == 1:
                assert d["plan_capture_ms"] == p["plan_capture_sim_ms"]
                assert _total(d, "plan_production_mono") == p["plan_production_mono_ns"]
                assert d["plan_acceleration"] == p["plan_acceleration"]
            elif d["kind"] == 2:
                assert d["sample_capture_ms"] == p["sample_capture_sim_ms"]
                assert _total(d, "sample_receipt_mono") == p["sample_receipt_mono_ns"]
            else:
                assert (MODE_NAMES[d["mode"]], CAUSE_NAMES[d["cause"]]) == (p["mode"], p["cause"])
                assert d["last_plan_capture_ms"] == p["last_plan_capture_sim_ms"]
                assert d["step_capture_ms"] == p["step_capture_sim_ms"]
                assert _total(d, "last_plan_production_mono") == p["last_plan_production_mono_ns"]
                assert _total(d, "cause_since_mono") == p["cause_since_mono_ns"]
                assert d["refusal_reason"] == p.get("refusal_reason", "")
    assert receipts == sum(kinds_published.values()), (receipts, kinds_published)
    want = {"HEALTH"} if name.startswith("refusal-") else {"PLAN", "VEHICLE_STATE", "HEALTH"}
    assert set(kinds_published) == want, kinds_published


# ------------------------------------------------------------------ the readers
# Each reader on records written here in the shape the producer writes them,
# with values of this test's own.
T_REAL0 = 1_794_000_000_000_000_000


def test_plan_pubs_reads_the_observers_plan_receipts(tmp_path):
    lines = [
        {"t_mono_ns": 10, "t_real_ns": T_REAL0, "host": "guest", "component": "observer",
         "event": "ready", "seq": 0, "data": {"link": "3 of 3 units subscribed"}},
        observer_line(1, 5_000_000_000, T_REAL0 + 7_000_000, kind=3, sequence=9,
                      producer="statePublisher", publish_mono_s=600, publish_mono_ns=1,
                      mode=1, last_plan_capture_ms=320_900),
        observer_line(2, 5_100_000_000, T_REAL0 + 41_000_000, schema_major=2, kind=1,
                      sequence=17, producer="statePublisher",
                      publish_real_s=1_794_000_000, publish_real_ns=40_000_123,
                      publish_mono_s=600, publish_mono_ns=40_000_001,
                      plan_frame_index=3210, plan_capture_ms=321_000,
                      plan_production_mono_s=600, plan_production_mono_ns=12_345_678,
                      plan_reference="0123456789abcdef/3210", run_record="0123456789abcdef",
                      plan_producer="drivingAgent/inferPlan", plan_sample_count=64,
                      plan_horizon_s=6.4, plan_acceleration=[0.5, 0.25, -0.125],
                      plan_curvature=[0.01, 0.02, 0.03], plan_x=[0.1, 0.4, 0.9],
                      plan_y=[0.0, 0.001, 0.004]),
        observer_line(3, 5_200_000_000, T_REAL0 + 45_000_000, kind=2, sequence=20,
                      producer="statePublisher", publish_mono_s=600, publish_mono_ns=44_000_000,
                      sample_capture_ms=321_000, speed_kmh=12.5),
    ]
    ps = mini_run(tmp_path, OBSERVER, lines).plan_pubs()
    assert len(ps) == 1, ps
    p = ps[0]
    assert p["t_real"] == pytest.approx(1_794_000_000.041, abs=1e-6)
    assert p["publish_mono"] == pytest.approx(600.040000001, abs=1e-9)
    assert p["publish_real"] == pytest.approx(1_794_000_000.040000123, abs=1e-6)
    assert p["frame"] == 3210
    assert p["capture_ms"] == 321_000 and p["capture_s"] == pytest.approx(321.0)
    assert p["production_mono"] == pytest.approx(600.012345678, abs=1e-9)
    assert p["reference"] == "0123456789abcdef/3210"
    assert p["run_record"] == "0123456789abcdef"
    assert p["producer"] == "statePublisher"
    assert p["plan_producer"] == "drivingAgent/inferPlan"
    assert p["sample_count"] == 64 and p["horizon"] == pytest.approx(6.4)
    assert (p["accel"], p["curv"]) == ([0.5, 0.25, -0.125], [0.01, 0.02, 0.03])
    assert (p["x"], p["y"]) == ([0.1, 0.4, 0.9], [0.0, 0.001, 0.004])
    assert p["file"] == OBSERVER and p["rec"]["seq"] == 2


def test_vs_pubs_reads_the_observers_vehicle_state_receipts(tmp_path):
    # The publisher stamps a vehicle state's publish time with the sample's
    # receipt (publisher_core.cpp:749, 755), so on a real run the two are equal;
    # they differ here to pin which field is which.
    lines = [
        observer_line(1, 6_000_000_000, T_REAL0 + 52_000_000, kind=2, sequence=88,
                      producer="statePublisher",
                      publish_real_s=1_794_000_000, publish_real_ns=51_500_000,
                      publish_mono_s=700, publish_mono_ns=50_000_000,
                      speed_kmh=36.5, longitudinal_acceleration=0.5,
                      lateral_acceleration=-0.25, yaw_rate_dps=1.5, sample_capture_ms=330_100,
                      sample_receipt_mono_s=700, sample_receipt_mono_ns=48_500_000),
        observer_line(2, 6_100_000_000, T_REAL0 + 53_000_000, kind=1, sequence=30,
                      producer="statePublisher", publish_mono_s=700, publish_mono_ns=52_000_000,
                      plan_frame_index=3301, plan_capture_ms=330_100),
        observer_line(3, 6_200_000_000, T_REAL0 + 54_000_000, kind=3, sequence=31,
                      producer="statePublisher", publish_mono_s=700, publish_mono_ns=53_000_000,
                      step_capture_ms=330_100),
    ]
    vs = mini_run(tmp_path, OBSERVER, lines).vs_pubs()
    assert len(vs) == 1, vs
    v = vs[0]
    assert v["t_real"] == pytest.approx(1_794_000_000.052, abs=1e-6)
    assert v["publish_mono"] == pytest.approx(700.05, abs=1e-9)
    assert v["publish_real"] == pytest.approx(1_794_000_000.0515, abs=1e-6)
    assert v["receipt_mono"] == pytest.approx(700.0485, abs=1e-9)
    assert v["sample_capture_ms"] == 330_100
    assert v["speed_kmh"] == pytest.approx(36.5)
    assert v["file"] == OBSERVER and v["rec"]["seq"] == 1


def test_health_pubs_reads_the_observers_health_receipts(tmp_path):
    lines = [
        observer_line(1, 7_000_000_000, T_REAL0 + 250_000_000, schema_major=2, kind=3,
                      sequence=41, producer="statePublisher",
                      publish_real_s=1_794_000_000, publish_real_ns=245_000_123,
                      publish_mono_s=512, publish_mono_ns=7_000_456,
                      mode=2, cause=3, mode_source="superviseLoop",
                      cause_since_mono_s=511, cause_since_mono_ns=987_654_321,
                      last_plan_frame_index=2467, last_plan_capture_ms=246_700,
                      step_capture_ms=246_800, last_plan_production_mono_s=511,
                      last_plan_production_mono_ns=901_234_567, dropped_samples=1),
        observer_line(2, 7_050_000_000, T_REAL0 + 260_000_000, kind=1, sequence=12,
                      producer="statePublisher", publish_mono_s=512, publish_mono_ns=17_000_000,
                      plan_frame_index=2469, plan_capture_ms=246_900),
        observer_line(3, 7_060_000_000, T_REAL0 + 270_000_000, kind=2, sequence=13,
                      producer="statePublisher", publish_mono_s=512, publish_mono_ns=27_000_000,
                      sample_capture_ms=246_900),
        observer_line(4, 6_900_000_000, T_REAL0 + 150_000_000, kind=3, sequence=40,
                      producer="statePublisher", publish_mono_s=511, publish_mono_ns=900_000_000,
                      mode=4, cause=11, mode_source="superviseLoop",
                      checkpoint_expected_sha256="ab" * 32, checkpoint_actual_sha256="cd" * 32,
                      refusal_reason="mismatch"),
    ]
    hs = mini_run(tmp_path, OBSERVER, lines).health_pubs()
    assert [h["rec"]["seq"] for h in hs] == [4, 1], hs        # by receipt time, kind 3 only
    refused, h = hs
    assert h["t_real"] == pytest.approx(1_794_000_000.25, abs=1e-6)
    assert h["publish_mono"] == pytest.approx(512.007000456, abs=1e-9)
    assert h["publish_real"] == pytest.approx(1_794_000_000.245000123, abs=1e-6)
    assert (h["mode"], h["cause"]) == (2, 3)
    assert h["mode_source"] == "superviseLoop" and h["producer"] == "statePublisher"
    assert h["cause_since_mono"] == pytest.approx(511.987654321, abs=1e-9)
    assert h["last_plan_frame"] == 2467
    assert (h["last_plan_capture_ms"], h["step_capture_ms"]) == (246_700, 246_800)
    assert h["last_plan_production_mono"] == pytest.approx(511.901234567, abs=1e-9)
    assert h["dropped_samples"] == 1
    assert (h["expected_sha"], h["actual_sha"], h["refusal_reason"]) == ("", "", "")
    assert h["file"] == OBSERVER
    assert (refused["mode"], refused["cause"]) == (4, 11)
    assert (refused["expected_sha"], refused["actual_sha"], refused["refusal_reason"]) == \
        ("ab" * 32, "cd" * 32, "mismatch")


def test_health_side_reads_the_publishers_health_records(tmp_path):
    other = {"t_mono_ns": 812_300_000_000, "t_real_ns": T_REAL0 + 300_000_000_000,
             "host": "score", "component": "statePublisher", "seq": 0}
    lines = [
        dict(other, event="in.mode", data={"mode": "kStopResponse", "cause": "kCameraStale",
                                           "frame_index": 3300, "capture_time": 330.0}),
        dict(other, event="stop_response.begin",
             data={"source": "superviseLoop", "mode": "kStopResponse", "cause": "kCameraStale",
                   "capture_time": 330.0, "clocks": {"capture_time": "simulation"}}),
        publisher_line(812_345_000_000, T_REAL0 + 300_045_000_000, "PLAN", sequence=3,
                       producer="statePublisher", publish_mono_ns=812_344_000_000,
                       publish_real_ns=T_REAL0 + 300_044_000_000, plan_frame_index=3299,
                       plan_capture_sim_ms=329_900, plan_production_mono_ns=812_340_000_000,
                       plan_reference="0123456789abcdef/3299", run_record="0123456789abcdef",
                       plan_producer="drivingAgent/inferPlan", plan_sample_count=64,
                       plan_horizon_s=6.4, plan_acceleration=[0.0], plan_curvature=[0.0],
                       plan_x=[0.0], plan_y=[0.0]),
        publisher_line(812_345_500_000, T_REAL0 + 300_045_500_000, "VEHICLE_STATE", sequence=4,
                       producer="statePublisher", publish_mono_ns=812_345_400_000,
                       publish_real_ns=T_REAL0 + 300_045_400_000, speed_kmh=10.0,
                       longitudinal_acceleration=0.0, lateral_acceleration=0.0,
                       yaw_rate_dps=0.0, sample_capture_sim_ms=330_000,
                       sample_receipt_mono_ns=812_345_400_000),
        publisher_line(812_345_701_234, T_REAL0 + 300_045_701_234, "HEALTH", sequence=2468,
                       producer="statePublisher", publish_mono_ns=812_345_678_901,
                       publish_real_ns=1_794_000_300_045_678_789, mode="kStopResponse",
                       cause="kCameraStale", mode_source="superviseLoop",
                       cause_since_mono_ns=812_300_000_123, last_plan_frame_index=3299,
                       last_plan_capture_sim_ms=329_900, step_capture_sim_ms=330_000,
                       last_plan_production_mono_ns=812_340_000_000, dropped_samples=0),
        publisher_line(812_245_701_234, T_REAL0 + 299_945_701_234, "HEALTH", sequence=2467,
                       producer="statePublisher", publish_mono_ns=812_245_600_000,
                       publish_real_ns=T_REAL0 + 299_945_600_000, mode="kDriving",
                       cause="kNone", mode_source="superviseLoop", cause_since_mono_ns=0,
                       last_plan_frame_index=3298, last_plan_capture_sim_ms=329_800,
                       step_capture_sim_ms=329_900, last_plan_production_mono_ns=812_240_000_000,
                       dropped_samples=0),
    ]
    hs = mini_run(tmp_path, PUBLISHER, lines).health_side()
    assert [h["seq"] for h in hs] == [2467, 2468], hs       # by monotonic time, HEALTH only
    before, h = hs
    assert h["t_mono"] == pytest.approx(812.345701234, abs=1e-9)
    assert h["t_real"] == pytest.approx(1_794_000_300.045701234, abs=1e-6)
    assert h["publish_mono"] == pytest.approx(812.345678901, abs=1e-9)
    assert h["publish_real"] == pytest.approx(1_794_000_300.045678789, abs=1e-6)
    assert (h["mode"], h["cause"]) == ("kStopResponse", "kCameraStale")
    assert h["mode_source"] == "superviseLoop"
    assert h["cause_since_mono"] == pytest.approx(812.300000123, abs=1e-9)
    assert h["file"] == PUBLISHER
    assert before["cause_since_mono"] == 0.0 and before["mode"] == "kDriving"


# The readers on files that hold only the names used before A34.
OLD_ONLY = {
    "plan_pubs": (OBSERVER, "rx.plan", 1),
    "vs_pubs": (OBSERVER, "rx.vehicle_state", 2),
    "health_pubs": (OBSERVER, "rx.health", 3),
    "health_side": (PUBLISHER, "out.health", 3),
}


@pytest.mark.parametrize("reader", sorted(OLD_ONLY))
def test_a_reader_reads_nothing_under_the_names_used_before(reader, tmp_path):
    rel, event, k = OLD_ONLY[reader]
    full = observer_data({"kind": k, "sequence": 1, "producer": "statePublisher",
                          "publish_mono_s": 100, "publish_mono_ns": 5, "plan_frame_index": 1,
                          "plan_capture_ms": 100, "plan_producer": "drivingAgent/inferPlan",
                          "sample_capture_ms": 100, "mode": 1, "step_capture_ms": 100})
    rec = {"t_mono_ns": 100_000_000_000, "t_real_ns": T_REAL0, "host": "x", "component": "x",
           "event": event, "seq": 1, "data": {key: full[key] for key in OLD_KEYS[k]}}
    run = mini_run(tmp_path, rel, [rec])
    if reader == "health_side":
        assert run.health_side() == []
        return
    with pytest.raises(MissingEvidence) as exc:
        getattr(run, reader)()
    assert OBSERVER_EVENT in exc.value.what and KIND_NAME[k] in exc.value.what, exc.value.what
