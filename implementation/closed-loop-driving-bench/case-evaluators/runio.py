"""Reading an ICD v2 bench run directory (ICD sections 6, 7, 8) into views.

Rules enforced here, because every case depends on them:

* a record is a JSON object with the envelope of ICD section 6
  (t_mono_ns, t_real_ns, host, component, event, seq, data) and a dict data;
  a file that breaks the envelope, or a line that is not JSON, raises
  RunFormatError - the caller turns that into errorEvidence, never into a pass;
* a file, event or field that is absent raises MissingEvidence carrying the
  record that would supply it - the caller turns that into
  inconclusiveMissingEvidence;
* a JSON null in a numeric slot is a non-finite value (run_log.h writes null
  for NaN and infinities), not an absent field. `num()` returns NaN for it,
  `has()` distinguishes absence;
* ICD v2 section 6 names the clock in every time field: `_sim_ms` / `_sim_s`
  for simulation time, `_mono_ns` / `_mono_s` for the S-CORE host's monotonic
  clock, `_real_ns` for real time. Payload crossings keep the model's field
  names and carry a sibling `clocks` object mapping each payload time field to
  its clock. Both forms are read here; a stamp with neither is not a stamped
  record and is reported missing.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

STEP_S = 0.1          # one step = 100 ms of simulation time (payloads.h)
STEP_MS = 100
SIM_EPS = 1e-9
CONTRACT = "de4sdv.driving.icd.v2"

ENVELOPE = ("t_mono_ns", "t_real_ns", "host", "component", "event", "seq", "data")


class RunFormatError(Exception):
    """The run directory cannot be read as an ICD v2 record."""


class MissingEvidence(Exception):
    """A record the case needs is not in the run directory."""

    def __init__(self, what: str, icd_change: str | None = None, detail: str = ""):
        self.what = what
        self.icd_change = icd_change
        self.detail = detail
        super().__init__(f"{what}" + (f" ({icd_change})" if icd_change else ""))


def num(d: dict, key: str, where: str = "", change: str | None = None) -> float:
    """A required float. Absent -> MissingEvidence; null -> NaN."""
    if key not in d:
        raise MissingEvidence(f"{where}.{key}" if where else key, change)
    v = d[key]
    if v is None:
        return float("nan")
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise RunFormatError(f"{where}.{key} is not a number: {v!r}")
    return float(v)


def maybe_num(d: dict, key: str) -> float | None:
    v = d.get(key)
    if v is None or isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v)


def finite(*xs: float) -> bool:
    return all(isinstance(x, float) and math.isfinite(x) for x in xs)


def close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def frames_between(t0: float, t1: float) -> float:
    return (t1 - t0) / STEP_S


def sim_s(ms: float | int | None) -> float | None:
    return None if ms is None else float(ms) / 1000.0


def sim_ms(sec: float | None) -> float | None:
    return None if sec is None else float(sec) * 1000.0


def _pair_s(d: dict, base: str) -> float | None:
    """A `_s`/`_ns` u32 pair (ICD v2 section 3), seconds, or None."""
    s = maybe_num(d, base + "_s")
    if s is None:
        return None
    ns = maybe_num(d, base + "_ns") or 0.0
    return s + ns / 1e9


def _clock(d: dict, field: str) -> str | None:
    clocks = d.get("clocks")
    if isinstance(clocks, dict):
        c = clocks.get(field)
        return c if isinstance(c, str) else None
    return None


def _sim_stamp(d: dict, field: str, ms_field: str | None = None) -> float | None:
    """A simulation stamp in seconds from a suffixed field or a payload+clocks."""
    if ms_field is not None and maybe_num(d, ms_field) is not None:
        return float(d[ms_field]) / 1000.0
    v = maybe_num(d, field + "_sim_s")
    if v is not None:
        return v
    ms = maybe_num(d, field + "_sim_ms")
    if ms is not None:
        return ms / 1000.0
    v = maybe_num(d, field)
    if v is not None and _clock(d, field) == "simulation":
        return v
    return None


def _any_sim_ms(d: dict) -> float | None:
    """The record's simulation time in ms, from any field ICD section 6 marks
    as simulation time: a `_sim_ms`/`_sim_s` suffix, or a payload field the
    sibling `clocks` object maps to `simulation` (seconds, A7). The agent's
    stop records use capture_sim_ms (agent/cc/agent_logic.cpp:623-647); the
    adapter's use actuationTime with clocks and t_sim_ms
    (actuation-adapter/log_records.h:117-142)."""
    for key in ("capture_sim_ms", "t_sim_ms"):
        if maybe_num(d, key) is not None:
            return float(d[key])
    for key in sorted(d):
        if key.endswith("_sim_ms") and maybe_num(d, key) is not None:
            return float(d[key])
        if key.endswith("_sim_s") and maybe_num(d, key) is not None:
            return float(d[key]) * 1000.0
    clocks = d.get("clocks")
    if isinstance(clocks, dict):
        for key in sorted(clocks):
            if clocks[key] == "simulation" and maybe_num(d, key) is not None:
                v = float(d[key])
                return v if key.endswith("_ms") else v * 1000.0
    return None


class Run:
    """One run directory."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        if not self.root.is_dir():
            raise RunFormatError(f"not a run directory: {self.root}")
        rec_path = self.root / "run_record.json"
        if not rec_path.exists():
            raise MissingEvidence("run_record.json", "C7",
                                  "the run record is the identity of every run (ICD 8)")
        try:
            self.record = json.loads(rec_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise RunFormatError(f"run_record.json: {exc}") from exc
        if not isinstance(self.record, dict):
            raise RunFormatError("run_record.json: not an object")
        contract = self.record.get("contractIdentity")
        if contract != CONTRACT:
            raise RunFormatError(
                f"run_record.json: contractIdentity is {contract!r}, not {CONTRACT!r}: "
                "this evaluator reads ICD v2 records only")
        self.scenario = self.record.get("scenario")
        if not isinstance(self.scenario, str):
            raise RunFormatError("run_record.json: 'scenario' missing or not a string")
        self.variant = self.record.get("scenarioVariant") or {}
        if not isinstance(self.variant, dict):
            self.variant = {}
        self._cache: dict[str, list[dict] | None] = {}
        self._identity: str | None = None
        self._input_steps: list[dict] | None = None

    # ---------------------------------------------------------------- identity
    def identity(self) -> str:
        """First 16 hex digits of the SHA-256 of run_record.json (ICD 8)."""
        if self._identity is None:
            self._identity = hashlib.sha256(
                (self.root / "run_record.json").read_bytes()).hexdigest()[:16]
        return self._identity

    def role(self) -> str | None:
        r = self.record.get("runRole")
        return r if isinstance(r, str) else None

    def campaign(self) -> str | None:
        c = self.record.get("campaignId")
        return c if isinstance(c, str) else None

    def fault(self) -> str:
        f = self.variant.get("fault")
        if isinstance(f, str) and f:
            return f
        return "none"

    # ---------------------------------------------------------------- records
    def path(self, rel: str) -> Path:
        return self.root / rel

    def exists(self, rel: str) -> bool:
        return self.path(rel).exists()

    def read(self, rel: str, required: bool = False) -> list[dict] | None:
        if rel in self._cache:
            got = self._cache[rel]
        else:
            p = self.path(rel)
            got = None if not p.exists() else self._parse_jsonl(p, rel)
            self._cache[rel] = got
        if got is None and required:
            raise MissingEvidence(rel, None, "file absent from the run directory")
        return got

    def _parse_jsonl(self, path: Path, rel: str) -> list[dict]:
        out: list[dict] = []
        try:
            text = path.read_text()
        except OSError as exc:
            raise RunFormatError(f"{rel}: {exc}") from exc
        for lineno, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RunFormatError(f"{rel}:{lineno}: {exc}") from exc
            if not isinstance(rec, dict):
                raise RunFormatError(f"{rel}:{lineno}: record is not an object")
            lacking = [k for k in ENVELOPE if k not in rec]
            if lacking:
                raise RunFormatError(f"{rel}:{lineno}: missing {','.join(lacking)}")
            if not isinstance(rec["data"], dict):
                raise RunFormatError(f"{rel}:{lineno}: data is not an object")
            if not isinstance(rec["seq"], int):
                raise RunFormatError(f"{rel}:{lineno}: seq is not an integer")
            if not isinstance(rec["event"], str):
                raise RunFormatError(f"{rel}:{lineno}: event is not a string")
            out.append(rec)
        return out

    def score_files(self) -> list[str]:
        d = self.path("score")
        if not d.is_dir():
            return []
        return sorted(f"score/{p.name}" for p in d.glob("*.jsonl"))

    def events(self, rel: str, event: str | None = None,
               required: bool = True) -> list[dict]:
        recs = self.read(rel, required=required) or []
        if event is None:
            return recs
        sel = [r for r in recs if r["event"] == event]
        if not sel and required:
            raise MissingEvidence(f"{rel}:{event}", None,
                                  "no record of this event in the file")
        return sel

    def score_events(self, event: str) -> list[tuple[str, dict]]:
        out = []
        for rel in self.score_files():
            for r in (self.read(rel) or []):
                if r["event"] == event:
                    out.append((rel, r))
        return out

    # ---------------------------------------------------------------- world
    def world(self) -> list[dict]:
        """The world-side record of the ticks (ICD section 10, C1)."""
        recs = self.read("simulator/world.jsonl", required=False)
        if recs is None:
            raise MissingEvidence("simulator/world.jsonl", "C1",
                                  "the world-side record of the ticks is absent")
        return sorted(recs, key=lambda r: r["seq"])

    def world_by_frame(self) -> dict[int, dict]:
        out = {}
        for r in self.world():
            f = r["data"].get("frame")
            if not isinstance(f, int):
                raise RunFormatError("simulator/world.jsonl: tick without integer frame")
            out[f] = r
        return out

    def world_frame(self, frame: int) -> dict:
        wb = self.world_by_frame()
        if frame not in wb:
            raise MissingEvidence(f"simulator/world.jsonl:frame {frame}", None,
                                  "the tick of this frame is not recorded")
        return wb[frame]

    def world_last_frame(self) -> int:
        return max(self.world_by_frame())

    # ---------------------------------------------------------------- plans
    def _plan_payload(self, d: dict, rel: str, rec: dict) -> dict:
        if "samples" not in d:
            raise RunFormatError(f"{rel}:{rec['seq']}: plan without samples")
        samples = d["samples"]
        if not isinstance(samples, list):
            raise RunFormatError(f"{rel}:{rec['seq']}: samples not a list")
        parsed = []
        for s in samples:
            if not isinstance(s, dict):
                raise RunFormatError(f"{rel}:{rec['seq']}: sample not an object")

            def fld(key: str) -> float:
                v = s.get(key)
                if v is None:
                    return float("nan")          # null is run_log.h's non-finite
                if isinstance(v, bool) or not isinstance(v, (int, float)):
                    raise RunFormatError(f"{rel}:{rec['seq']}: sample.{key} not a number")
                return float(v)

            parsed.append({"acceleration": fld("acceleration"),
                           "curvature": fld("curvature"),
                           "x": fld("x"), "y": fld("y"), "heading": fld("heading")})
        cap_s = _sim_stamp(d, "captureTime", "capture_sim_ms")
        return {
            "frame": d.get("frameIndex"),
            "capture_s": cap_s,
            "capture_ms": sim_ms(cap_s),
            "production_mono": _pair_s(d, "production_mono")
                                if "production_mono_s" in d else maybe_num(d, "productionTime"),
            "sample_count": d.get("sampleCount"),
            "horizon": maybe_num(d, "horizon"),
            "samples": parsed,
            "producer": d.get("producer"),
            "run_record": d.get("runRecord") or d.get("run_record"),
            "reference": d.get("planReference") or d.get("plan_reference"),
            "capture_clock": _clock(d, "captureTime") or d.get("captureTimeClock"),
            "production_clock": _clock(d, "productionTime") or d.get("productionTimeClock"),
            "rec": rec,
            "file": rel,
        }

    def plans(self, rel: str = "score/drivingAgent.jsonl", event: str = "out.plan",
              required: bool = True) -> list[dict]:
        out = [self._plan_payload(r["data"], rel, r) for r in self.events(rel, event, required)]
        return sorted(out, key=lambda p: (p["frame"] if isinstance(p["frame"], int) else -1,
                                          p["rec"]["seq"]))

    def plans_in(self, rel: str, event: str) -> list[dict]:
        """Plans at the commander's view (in.plan) when present, else the producer's."""
        if self.exists(rel):
            recs = self.events(rel, event, required=False)
            if recs:
                return sorted((self._plan_payload(r["data"], rel, r) for r in recs),
                              key=lambda p: (p["frame"] if isinstance(p["frame"], int) else -1,
                                             p["rec"]["seq"]))
        return []

    def _command(self, d: dict, rec: dict, rel: str) -> dict:
        cap_s = _sim_stamp(d, "captureTime", "capture_sim_ms")
        step_ms = maybe_num(d, "step_capture_sim_ms")
        plan_cap_ms = maybe_num(d, "plan_capture_sim_ms")
        return {
            "accel": maybe_num(d, "acceleration"),
            "steer": maybe_num(d, "steeringAngle"),
            "production_mono": _pair_s(d, "production_mono")
                               if "production_mono_s" in d else maybe_num(d, "productionTime"),
            "reference": d.get("planReference") or d.get("plan_reference") or "",
            "capture_s": cap_s,
            # ICD v2 C3: the commander's log record carries both simulation
            # stamps; the command payload stays exact (no simulation field).
            "step_capture_ms": step_ms,
            "plan_capture_ms": plan_cap_ms,
            "step_frame": int(round(step_ms / STEP_MS)) if step_ms is not None else None,
            "t_mono": rec["t_mono_ns"] / 1e9,
            "rec": rec,
            "file": rel,
        }

    def commands(self) -> list[dict]:
        rel = "score/drivingAgent.jsonl"
        return [self._command(rec["data"], rec, rel)
                for rec in self.events(rel, "out.command")]

    def adapter_commands(self) -> list[dict]:
        """The adapter's in.command records (actuation-adapter/log_records.h:46-63),
        each with its arrival on the monotonic clock and the out.actuation_state
        the adapter logged right after it, before the next in.command
        (actuation_adapter_main.cpp:244-256); None when it applied nothing."""
        rel = "score/actuationAdapter.jsonl"
        recs = sorted(self.events(rel, None, required=False) or [], key=lambda r: r["seq"])
        out: list[dict] = []
        for rec in recs:
            if rec["event"] == "in.command":
                c = self._command(rec["data"], rec, rel)
                c["arrival_mono"] = maybe_num(rec["data"], "arrival_mono_s")
                c["valid"] = rec["data"].get("valid")
                c["actuation"] = None
                out.append(c)
            elif rec["event"] == "out.actuation_state" and out and out[-1]["actuation"] is None:
                d = rec["data"]
                if int(d.get("applied") or 0) == 1:
                    out[-1]["actuation"] = {"actuation_s": _sim_stamp(d, "actuationTime",
                                                                       "actuation_sim_ms"),
                                            "rec": rec}
        return out

    def actuations(self) -> list[dict]:
        rel = "score/actuationAdapter.jsonl"
        out = []
        for rec in self.events(rel, "out.actuation_state"):
            d = rec["data"]
            act_s = _sim_stamp(d, "actuationTime", "actuation_sim_ms")
            stop_s = _sim_stamp(d, "stopSince", "stop_since_sim_ms")
            out.append({
                "applied": int(d.get("applied") or 0),
                "stop": int(d.get("stopInForce") or 0),
                "cause": d.get("cause"),
                "accel": maybe_num(d, "acceleration"),
                "steer": maybe_num(d, "steeringAngle"),
                "actuation_s": act_s,
                "stop_since_s": stop_s,
                "stop_since_mono": _pair_s(d, "stopSinceMono")
                                   if "stopSinceMono_s" in d else maybe_num(d, "stopSinceMono"),
                "reference": d.get("planReference") or d.get("plan_reference") or "",
                "t_mono": rec["t_mono_ns"] / 1e9,
                "rec": rec,
                "file": rel,
            })
        return sorted(out, key=lambda a: (a["actuation_s"] if a["actuation_s"] is not None else -1.0,
                                          a["rec"]["seq"]))

    def vehicle_controls(self) -> list[dict]:
        """The controls the adapter applied, out.vehicle_control
        (actuation-adapter/log_records.h:84-97): frame, t_sim_ms and the
        trigger (command, tick, hold, stop; actuation_adapter_main.cpp:185, 210)."""
        rel = "score/actuationAdapter.jsonl"
        out = []
        for rec in self.events(rel, "out.vehicle_control", required=False):
            d = rec["data"]
            t_ms = _any_sim_ms(d)
            frame = d.get("frame")
            if not isinstance(frame, int) or isinstance(frame, bool):
                frame = int(round(t_ms / STEP_MS)) if t_ms is not None else None
            out.append({"frame": frame, "t_sim": None if t_ms is None else t_ms / 1000.0,
                        "trigger": d.get("trigger"), "throttle": maybe_num(d, "throttle"),
                        "brake": maybe_num(d, "brake"), "steer": maybe_num(d, "steer"),
                        "rec": rec, "file": rel})
        return sorted(out, key=lambda v: (v["frame"] if v["frame"] is not None else -1,
                                          v["rec"]["seq"]))

    def modes(self) -> list[dict]:
        out = []
        for rec in self.events("score/drivingAgent.jsonl", "out.mode"):
            d = rec["data"]
            cap_s = _sim_stamp(d, "captureTime", "capture_sim_ms")
            dec_mono = _pair_s(d, "decision_mono") if "decision_mono_s" in d \
                else maybe_num(d, "decisionTime")
            out.append({"mode": d.get("mode"), "cause": d.get("cause"),
                        "frame": d.get("frameIndex"),
                        "capture_s": cap_s,
                        "capture_ms": sim_ms(cap_s),
                        "decision_mono": dec_mono,
                        "rec": rec, "file": "score/drivingAgent.jsonl"})
        return out

    # ---------------------------------------------------------------- stops
    def stops(self, event: str = "stop_response.begin") -> list[dict]:
        """Every stop_response.begin / standstill in the score logs, by simulation time."""
        out = []
        for rel, rec in self.score_events(event):
            d = rec["data"]
            t_ms = _any_sim_ms(d)
            if t_ms is None:
                raise MissingEvidence(f"{rel}:{event} simulation time", "C9",
                                      f"record {rec['seq']} names no field of the "
                                      "simulation clock (ICD section 6)")
            frame = d.get("frame")
            if not isinstance(frame, int) or isinstance(frame, bool):
                frame = int(round(t_ms / STEP_MS))
            out.append({"t_sim": t_ms / 1000.0, "cause": d.get("cause"),
                        "source": d.get("source") or rec.get("component"), "frame": frame,
                        "t_mono": rec["t_mono_ns"] / 1e9,
                        "t_real": rec["t_real_ns"] / 1e9, "rec": rec, "file": rel})
        return sorted(out, key=lambda s: s["t_sim"])

    def stop_begin(self) -> dict | None:
        s = self.stops("stop_response.begin")
        return s[0] if s else None

    def standstill(self) -> dict | None:
        s = self.stops("stop_response.standstill")
        return s[0] if s else None

    # ---------------------------------------------------------------- publications
    def health_pubs(self) -> list[dict]:
        """The observer's decoded HEALTH message (ICD v2 section 3, fields 30-43)."""
        rel = "guest/observer.jsonl"
        out = []
        for rec in self.events(rel, "rx.health"):
            d = rec["data"]
            out.append({
                "t_real": rec["t_real_ns"] / 1e9,
                "t_mono_guest": rec["t_mono_ns"] / 1e9,
                "publish_real": _pair_s(d, "publish_real"),
                "publish_mono": _pair_s(d, "publish_mono"),
                "mode": d.get("mode"),
                "cause": d.get("cause"),
                "mode_source": d.get("mode_source"),
                "producer": d.get("producer"),
                "cause_since_mono": _pair_s(d, "cause_since_mono"),
                "last_plan_frame": d.get("last_plan_frame_index"),
                "last_plan_capture_ms": maybe_num(d, "last_plan_capture_ms"),
                "step_capture_ms": maybe_num(d, "step_capture_ms"),
                "last_plan_production_mono": _pair_s(d, "last_plan_production_mono"),
                "dropped_samples": d.get("dropped_samples"),
                "expected_sha": d.get("checkpoint_expected_sha256"),
                "actual_sha": d.get("checkpoint_actual_sha256"),
                "refusal_reason": d.get("refusal_reason"),
                "rec": rec, "file": rel,
            })
        return sorted(out, key=lambda h: h["t_real"])

    def plan_pubs(self) -> list[dict]:
        """The observer's decoded PLAN message (fields 10-22)."""
        rel = "guest/observer.jsonl"
        out = []
        for rec in self.events(rel, "rx.plan"):
            d = rec["data"]
            out.append({
                "t_real": rec["t_real_ns"] / 1e9,
                "publish_real": _pair_s(d, "publish_real"),
                "publish_mono": _pair_s(d, "publish_mono"),
                "frame": d.get("plan_frame_index"),
                "capture_ms": maybe_num(d, "plan_capture_ms"),
                "capture_s": sim_s(d.get("plan_capture_ms")),
                "production_mono": _pair_s(d, "plan_production_mono"),
                "reference": d.get("plan_reference"),
                "run_record": d.get("run_record"),
                "producer": d.get("producer"),
                "plan_producer": d.get("plan_producer"),
                "accel": d.get("plan_acceleration") or [],
                "curv": d.get("plan_curvature") or [],
                "x": d.get("plan_x") or [],
                "y": d.get("plan_y") or [],
                "sample_count": d.get("plan_sample_count"),
                "horizon": maybe_num(d, "plan_horizon_s"),
                "rec": rec, "file": rel,
            })
        return sorted(out, key=lambda p: p["t_real"])

    def vs_pubs(self) -> list[dict]:
        rel = "guest/observer.jsonl"
        out = []
        for rec in self.events(rel, "rx.vehicle_state"):
            d = rec["data"]
            out.append({
                "t_real": rec["t_real_ns"] / 1e9,
                "publish_mono": _pair_s(d, "publish_mono"),
                "publish_real": _pair_s(d, "publish_real"),
                "speed_kmh": maybe_num(d, "speed_kmh"),
                "sample_capture_ms": maybe_num(d, "sample_capture_ms"),
                "receipt_mono": _pair_s(d, "sample_receipt_mono"),
                "rec": rec, "file": rel,
            })
        return sorted(out, key=lambda p: p["t_real"])

    def health_side(self) -> list[dict]:
        """The publisher's own HEALTH record on the S-CORE host (ICD v2 C5).

        VC-029 compares the stop begin with the publisher's monotonic stamp,
        not with the guest's receipt, so both ends are on the S-CORE host.
        """
        rel = "score/statePublisher.jsonl"
        out = []
        for rec in self.events(rel, "out.health", required=False):
            d = rec["data"]
            out.append({"t_mono": rec["t_mono_ns"] / 1e9,
                        "t_real": rec["t_real_ns"] / 1e9,
                        "publish_mono": _pair_s(d, "publish_mono"),
                        "publish_real": _pair_s(d, "publish_real"),
                        "mode": d.get("mode"), "cause": d.get("cause"),
                        "mode_source": d.get("mode_source"),
                        "cause_since_mono": _pair_s(d, "cause_since_mono"),
                        "seq": rec["seq"], "rec": rec, "file": rel})
        return sorted(out, key=lambda h: h["t_mono"])

    # ---------------------------------------------------------------- agent inputs
    def ego_samples(self) -> list[dict]:
        """The motion sample of each step, as the agent logs it:
        out.ego_motion_sample (agent/cc/agent_ffi.cpp:1088-1095). No producer
        writes in.ego_motion."""
        rel = "score/drivingAgent.jsonl"
        out = []
        for rec in self.events(rel, "out.ego_motion_sample", required=False):
            d = rec["data"]
            cap_s = _sim_stamp(d, "captureTime", "capture_sim_ms")
            frame = d.get("frame")
            step = frame if isinstance(frame, int) and not isinstance(frame, bool) else None
            out.append({
                "speed_kmh": maybe_num(d, "speed"),
                "accel": maybe_num(d, "longitudinalAcceleration"),
                "lateral": maybe_num(d, "lateralAcceleration"),
                "yaw_dps": maybe_num(d, "yawRate"),
                "capture_s": cap_s,
                "capture_ms": sim_ms(cap_s),
                "capture_clock": _clock(d, "captureTime") or d.get("captureTimeClock"),
                "step": step,
                "valid": d.get("valid"),
                "t_mono": rec["t_mono_ns"] / 1e9,
                "rec": rec, "file": rel,
            })
        # the step is the sample's own frame, never its record index: real runs
        # start at frame 48 or 5000
        return sorted(out, key=lambda s: (s["step"] if s["step"] is not None else -1,
                                          s["rec"]["seq"]))

    def camera_inputs(self) -> list[dict]:
        """The per-step camera metadata of ICD v2 C2, one entry per step."""
        return self.input_steps()

    def input_steps(self) -> list[dict]:
        """ICD v2 C2: the per-step checkpoint input metadata.

        Projection operators are written once per run (and on change), so they
        are carried forward into every following step here. The A11 fields
        (cameras[].front_hi_res, mapContext, routeMask), the A16 fields
        (routeMask.waypointsInWindow / waypointsOnCorridor, rasterPose) and the
        A17 camera sizes are carried as they are recorded, None when absent.
        """
        if self._input_steps is not None:
            return self._input_steps
        rel = "score/checkpointInputs.jsonl"
        recs = self.events(rel, "out.checkpoint_inputs", required=False)
        if not recs:
            raise MissingEvidence(rel, "C2",
                                  "the metadata of the inputs handed to the checkpoint "
                                  "is not recorded")
        out: list[dict] = []
        projections: dict[str, dict] = {}
        for rec in sorted(recs, key=lambda r: (r["data"].get("frame", -1), r["seq"])):
            d = rec["data"]
            f = d.get("frame")
            if not isinstance(f, int):
                raise RunFormatError(f"{rel}:{rec['seq']}: step without integer frame")
            ms = d.get("sim_ms")
            if not isinstance(ms, int):
                raise RunFormatError(f"{rel}:{rec['seq']}: step without integer sim_ms")
            for p in d.get("projections") or []:
                if isinstance(p, dict) and p.get("camera"):
                    projections[p["camera"]] = p
            cams = []
            for c in d.get("cameras") or []:
                if not isinstance(c, dict):
                    raise RunFormatError(f"{rel}:{rec['seq']}: camera not an object")
                cname = c.get("name")
                cams.append({
                    "name": cname,
                    "image_frame": c.get("image_frame"),
                    "capture_sim_ms": maybe_num(c, "capture_sim_ms"),
                    "arrival_mono_ns": maybe_num(c, "arrival_mono_ns"),
                    "width": c.get("width"), "height": c.get("height"),
                    "source_width": c.get("source_width"),
                    "source_height": c.get("source_height"),
                    "front_hi_res": c.get("front_hi_res"),
                    "valid": c.get("valid"), "status": c.get("status"),
                    "history": c.get("history") or [],
                    "projection": projections.get(str(cname)) if cname is not None else None,
                })
            out.append({
                "frame": f, "sim_ms": ms,
                "cameras": cams,
                "projections": dict(projections),
                "ego_motion_history": d.get("ego_motion_history") or [],
                "map_context_render_sim_ms": maybe_num(d, "map_context_render_sim_ms"),
                "map_context": (d.get("mapContext")
                                if isinstance(d.get("mapContext"), dict) else None),
                "route_mask": (d.get("routeMask")
                               if isinstance(d.get("routeMask"), dict) else None),
                "raster_pose": (d.get("rasterPose")
                                if isinstance(d.get("rasterPose"), dict) else None),
                "corridor_cell_count": d.get("corridor_cell_count"),
                "destination_cell_count": d.get("destination_cell_count"),
                "input_conditions": d.get("input_conditions") or {},
                # A26: the engine's answer (agent/cc/agent_ffi.cpp:1018, 1072-1073)
                "primed": d.get("primed"),
                "conditioned": d.get("conditioned"),
                "merged_frames": d.get("mergedFrames") or [],
                "rec": rec, "file": rel,
            })
        self._input_steps = out
        return out

    def route_announcements(self) -> list[dict]:
        rel = "score/route_provider.jsonl"
        out = []
        for rec in self.events(rel, "out.route_announcement", required=False):
            d = rec["data"]
            out.append({"issue_s": _sim_stamp(d, "issueTime", "issue_sim_ms"),
                        "corridor": d.get("corridorPoints"),
                        "sha": d.get("routeSha256"),
                        "route_file": d.get("routeFile"),
                        "t_mono": rec["t_mono_ns"] / 1e9,
                        "rec": rec, "file": rel})
        return out

    # ---------------------------------------------------------------- artifacts
    def reference_inference(self) -> dict[int, dict]:
        rel = "score/referenceInference.jsonl"
        recs = self.events(rel, "reference_inference", required=False)
        if not recs:
            raise MissingEvidence(rel, "C11",
                                  "no offline reference inference for the recorded inputs")
        return {r["data"].get("frameIndex"): r["data"] for r in recs}

    def injections(self) -> list[dict]:
        rel = "bench/injection.jsonl"
        recs = self.events(rel, "injection", required=False)
        if not recs:
            raise MissingEvidence(rel, "C8",
                                  "the bench's injections and control acts are not recorded")
        out = []
        for r in recs:
            d = r["data"]
            t_ms = maybe_num(d, "t_sim_ms")
            mono_ns = maybe_num(d, "t_mono_ns")
            real_ns = maybe_num(d, "t_real_ns")
            out.append({"action": d.get("action"),
                        "t_sim": sim_s(t_ms),
                        "t_sim_ms": t_ms,
                        "t_mono": mono_ns / 1e9 if mono_ns is not None else None,
                        "t_real": real_ns / 1e9 if real_ns is not None else None,
                        "detail": d.get("detail") or {},
                        "rec": r, "file": rel})
        return sorted(out, key=lambda x: (x["t_sim"] if x["t_sim"] is not None else -1.0,
                                          x["rec"]["seq"]))

    # ---------------------------------------------------------------- bundles
    def bundle_frames(self) -> set[int]:
        """Frames with a sampled full input bundle (ICD v2 C2)."""
        d = self.path("score/bundles")
        if not d.is_dir():
            return set()
        out = set()
        for p in d.glob("*.npz"):
            try:
                out.add(int(p.stem))
            except ValueError:
                continue
        return out

    def bundle_schedule(self) -> set[int]:
        """Every 50th step, plus every step within +/-0.5 s of a fault.

        This is the sampling rule of ICD v2 C2; the evaluator derives it so a
        missing bundle is noticed rather than excused.
        """
        last = self.world_last_frame() if self.exists("simulator/world.jsonl") else \
            max((p["frame"] for p in self.plans(required=False)
                 if isinstance(p["frame"], int)), default=-1)
        sched = {f for f in range(0, last + 1, 50)}
        fault_frame = None
        try:
            for i in self.injections():
                if i["action"] == "fault_begin" and i["t_sim"] is not None:
                    fault_frame = int(round(i["t_sim"] / STEP_S))
                    break
        except MissingEvidence:
            pass
        if fault_frame is not None:
            sched |= {f for f in range(fault_frame - 5, fault_frame + 6) if 0 <= f <= last}
        return sched

    def named_file(self, path: str, sha: str | None) -> tuple[Path | None, str | None]:
        """The file a run record names with its SHA-256 (C7).

        A relative path is in the run directory, or by its name in the campaign
        directory. An absolute path names a file on the host that ran the bench:
        a copy retained by its name in the run directory (top or bench/) or in
        the campaign directory is used first; the file at that path on the
        evaluating host only when its SHA-256 is the recorded one. Returns
        (path, None) or (None, why).
        """
        import hashlib
        named = Path(path)
        if not named.is_absolute():
            for p in (self.root / named, self.root.parent / named.name):
                if p.exists():
                    return p, None
            return None, f"{path} is not retained in the run or campaign directory"
        for p in (self.root / named.name, self.root / "bench" / named.name,
                  self.root.parent / named.name):
            if p.exists():
                return p, None
        if named.exists():
            if isinstance(sha, str) and sha \
                    and hashlib.sha256(named.read_bytes()).hexdigest() == sha:
                return named, None
            return None, (f"{path} is a path on the bench host; the file at that path on the "
                          "evaluating host is not the one the run recorded")
        return None, (f"{path} is a path on the bench host and no copy is retained in the "
                      "run or campaign directory")

    def limits(self) -> dict:
        """The vehicle configuration of ICD section 5, named by the run record (C7).

        Its limits are used only from a file whose SHA-256 is the recorded one.
        """
        import hashlib
        veh = self.record.get("vehicleConfiguration")
        if not (isinstance(veh, dict) and isinstance(veh.get("path"), str)):
            raise MissingEvidence("run_record.vehicleConfiguration.path", "C7",
                                  "the run record does not name the vehicle configuration")
        p, why = self.named_file(veh["path"], veh.get("sha256"))
        if p is None:
            raise MissingEvidence(f"run_record.vehicleConfiguration.path -> {veh['path']}", "C7",
                                  why or "the vehicle configuration is not retained")
        sha = veh.get("sha256")
        if not (isinstance(sha, str) and sha):
            raise MissingEvidence("run_record.vehicleConfiguration.sha256", "C7",
                                  "no SHA-256 to verify the vehicle configuration against")
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        if got != sha:
            raise MissingEvidence(f"run_record.vehicleConfiguration -> {p.name}", "C7",
                                  f"the file's SHA-256 {got[:12]}... is not the recorded "
                                  f"{sha[:12]}...: its limits are not the run's")
        try:
            return json.loads(p.read_text())
        except json.JSONDecodeError as exc:
            raise RunFormatError(f"{veh['path']}: {exc}") from exc

    def engine(self) -> str | None:
        """The planner engine the agent built: `checkpoint` or `stub`, from its
        `engine` record (agent/cc/agent_ffi.cpp:656-657); None when absent."""
        for rec in self.events("score/drivingAgent.jsonl", "engine", required=False):
            setup = rec["data"].get("setup")
            name = setup.get("engine") if isinstance(setup, dict) else rec["data"].get("engine")
            if isinstance(name, str) and name:
                return name
        return None

    def first_plan_production(self) -> float | None:
        ps = self.plans(required=False)
        return ps[0]["production_mono"] if ps else None

    def priming_frame(self) -> int:
        recs = self.events("score/drivingAgent.jsonl", "priming.complete", required=False)
        if not recs:
            raise MissingEvidence("score/drivingAgent.jsonl:priming.complete", "C10",
                                  "no record marks the end of priming")
        d = recs[0]["data"]
        f = d.get("frame")
        if not isinstance(f, int):
            raise RunFormatError("priming.complete without integer frame")
        return f
