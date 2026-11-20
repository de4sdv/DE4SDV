"""Reading the records of an S1 session for the case evaluators (OBSERVABLES.md, "Records").

`discover(root)` finds every run under a fetched session tree by the file names the session writes:
`world_<run>/simulator/world.jsonl`, `score_<run>/score_side/run/score/*.jsonl`, `capture_<run>/
app_record_warning.jsonl`, `ivi_clock_<run>/clock.jsonl`, and `session.json` at the root. It does not care which
host folder holds them (attempt 3: `sim-lead-fetch/x/out`, `score/fetch-20261120b/x/out`, `guest/out`). Two copies
of one file with different bytes make that file unreadable (errorEvidence); a missing file is missing evidence.

A run is a run of a setting when its setting record says `kind` `run`; the stop run when its kind is `stop`, its id
is `stop`, or its session entry's `runIdentity` names the stop. The two runs of a setting are taken in the order of
their first world tick (sim time is monotonic over a session); `runIdentity` is reported, not needed.
"""

from __future__ import annotations

import bisect
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path


class MissingEvidence(Exception):
    """A run, file, record or field that a case needs is missing: inconclusiveMissingEvidence."""


class EvidenceError(Exception):
    """A record that cannot be read: errorEvidence."""


PATTERNS = {
    "world": ("world_", "simulator/world.jsonl"),
    "setting_record": ("world_", "simulator/setting_record.json"),
    "score": ("score_", "score_side/run/score/score_interface.jsonl"),
    "adapter": ("score_", "score_side/run/score/actuationAdapter.jsonl"),
    "identity": ("score_", "score_side/run/score/identityRecorder.jsonl"),
    "candidate_record": ("score_", "score_side/run/score/candidate_record.json"),
    "receipts": ("capture_", "app_record_warning.jsonl"),
    "clock": ("ivi_clock_", "clock.jsonl"),
}
PRODUCER = {
    "world": "the world side (B/world-side/da_world_side.py)",
    "setting_record": "the world side (B/world-side/da_world_side.py:706-729)",
    "score": "the S-CORE interface (B/score-interface)",
    "adapter": "the actuation adapter (B/actuation-adapter)",
    "identity": "the identity recorder (B/identity-recorder)",
    "candidate_record": "the identity recorder (B/identity-recorder)",
    "receipts": "the IVI warning app (B/ivi-warning-app)",
    "clock": "the session's ivi_clock step",
}


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    out = []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise EvidenceError(f"{path}:{n} is not JSON ({exc.msg})") from None
            if not isinstance(obj, dict):
                raise EvidenceError(f"{path}:{n} is not a JSON object")
            out.append(obj)
    return out


def read_json(path: Path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"{path} is not JSON ({exc.msg})") from None


def find_stop_record(obj) -> dict | None:
    """The first object holding runTarget path_stopped in a JSON value (shared contract 3)."""
    if isinstance(obj, dict):
        if obj.get("runTarget") == "path_stopped":
            return obj
        for v in obj.values():
            hit = find_stop_record(v)
            if hit is not None:
                return hit
    elif isinstance(obj, list):
        for v in obj:
            hit = find_stop_record(v)
            if hit is not None:
                return hit
    return None


@dataclass
class Run:
    run_id: str
    root: Path
    paths: dict
    session_entry: dict = field(default_factory=dict)
    conflicts: dict = field(default_factory=dict)
    setting_id: str | None = None
    kind: str | None = None
    repetition: int | None = None
    _cache: dict = field(default_factory=dict)

    # ---------------------------------------------------------------- files
    def label(self, key: str) -> str:
        p = self.paths.get(key)
        if p is not None:
            try:
                return str(p.relative_to(self.root))
            except ValueError:
                return str(p)
        prefix, rest = PATTERNS[key]
        return f"{prefix}{self.run_id}/{rest}"

    def _path(self, key: str) -> Path:
        if key in self.conflicts:
            raise EvidenceError(f"{self.label(key)}: {self.conflicts[key]}")
        p = self.paths.get(key)
        if p is None:
            raise MissingEvidence(f"{self.label(key)}: no file ({PRODUCER[key]})")
        return p

    def _jsonl(self, key: str) -> list[dict]:
        if key not in self._cache:
            self._cache[key] = read_jsonl(self._path(key))
        return self._cache[key]

    def _json(self, key: str):
        if key not in self._cache:
            self._cache[key] = read_json(self._path(key))
        return self._cache[key]

    # ---------------------------------------------------------------- W
    def ticks(self) -> list[dict]:
        if "ticks" not in self._cache:
            ticks = []
            for line in self._jsonl("world"):
                if line.get("event") != "tick":
                    continue
                d = line.get("data")
                if not isinstance(d, dict) or not isinstance(d.get("simTimeS"), (int, float)):
                    raise EvidenceError(f"{self.label('world')}: a tick line without data.simTimeS")
                ticks.append(d)
            if not ticks:
                raise MissingEvidence(f"{self.label('world')}: no tick line ({PRODUCER['world']})")
            ticks.sort(key=lambda d: d["simTimeS"])
            self._cache["ticks"] = ticks
        return self._cache["ticks"]

    def frame_index(self) -> dict:
        if "frame_index" not in self._cache:
            self._cache["frame_index"] = {t.get("frame"): i for i, t in enumerate(self.ticks())}
        return self._cache["frame_index"]

    def tick_of(self, rec: dict, time_key: str) -> int | None:
        """The index of the W tick of an S record: the same frame, else the last tick at or before its time."""
        fi = self.frame_index()
        if rec.get("frame") in fi:
            return fi[rec["frame"]]
        t = rec.get(time_key)
        if not isinstance(t, (int, float)):
            return None
        times = [x["simTimeS"] for x in self.ticks()]
        i = bisect.bisect_right(times, t + 1e-9) - 1
        return i if i >= 0 else None

    def run_span(self) -> tuple[float, float]:
        ticks = self.ticks()
        return ticks[0]["simTimeS"], ticks[-1]["simTimeS"]

    def setting_record(self) -> dict:
        rec = self._json("setting_record")
        if not isinstance(rec, dict):
            raise EvidenceError(f"{self.label('setting_record')} is not a JSON object")
        return rec

    # ---------------------------------------------------------------- S, A, I
    def score(self, kind: str) -> list[dict]:
        return [r for r in self._jsonl("score") if r.get("kind") == kind]

    def commands(self) -> list[dict]:
        """S out.driving_command, by issue time (then seq)."""
        cmds = self.score("out.driving_command")
        for c in cmds:
            acc = c.get("acceleration")
            if not isinstance(c.get("seq"), int) or not isinstance(c.get("issueTime_sim_s"), (int, float)) \
                    or not isinstance(acc, (int, float)) or isinstance(acc, bool):
                raise EvidenceError(f"{self.label('score')}: an out.driving_command without an integer seq, "
                                    "a numeric issueTime_sim_s and acceleration")
        return sorted(cmds, key=lambda c: (c["issueTime_sim_s"], c["seq"]))

    def warnings(self) -> list[dict]:
        ws = self.score("out.warning_request")
        for w in ws:
            if not isinstance(w.get("requested"), bool) or not isinstance(w.get("issueTime_sim_s"), (int, float)):
                raise EvidenceError(f"{self.label('score')}: an out.warning_request without a boolean requested "
                                    "and a numeric issueTime_sim_s")
        return sorted(ws, key=lambda w: (w["issueTime_sim_s"], w.get("mono_ns") or 0))

    def drops(self) -> list[dict]:
        drops = self.score("drop.camera_image")
        for d in drops:
            if not isinstance(d.get("sim_s"), (int, float)):
                raise EvidenceError(f"{self.label('score')}: a drop.camera_image without sim_s")
        return drops

    def drops_in(self, w0: float, w1: float) -> list[dict]:
        return [d for d in self.drops() if w0 - 1e-6 <= d["sim_s"] <= w1 + 1e-6]

    def adapter(self, event: str) -> list[dict]:
        return [r for r in self._jsonl("adapter") if r.get("event") == event]

    def identity_lines(self) -> list[dict]:
        return self._jsonl("identity")

    # ---------------------------------------------------------------- R, C, P
    def receipts(self) -> list[dict]:
        return [r for r in self._jsonl("receipts") if r.get("event") == "receipt"]

    def clock(self) -> dict:
        lines = self._jsonl("clock")
        if not lines:
            raise MissingEvidence(f"{self.label('clock')}: empty ({PRODUCER['clock']})")
        for line in lines:
            if line.get("label") == "after_second_set":
                return line
        return lines[-1]

    def stop_record(self, session: dict) -> dict:
        rec = find_stop_record(self.session_entry) or find_stop_record(session)
        if rec is None:
            for p in sorted(self.root.rglob(f"path_stop_{self.run_id}*")):
                if not p.is_file():
                    continue
                for line in p.read_text(errors="replace").splitlines():
                    line = line.strip()
                    if line.startswith("{") and "runTarget" in line:
                        try:
                            cand = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if isinstance(cand, dict) and cand.get("runTarget") == "path_stopped":
                            rec = cand
        if rec is None:
            raise MissingEvidence(f"the stop record of run {self.run_id}: no object with runTarget path_stopped in "
                                  f"session.json or path_stop_{self.run_id}.* (shared contract 3, lane C4)")
        return rec


@dataclass
class Session:
    root: Path
    session: dict
    runs: list
    stop_run: Run | None
    problems: list

    def by_setting(self) -> dict:
        out: dict = {}
        for r in self.runs:
            out.setdefault(r.setting_id, []).append(r)
        return out


NOT_A_RUN = ("calib", "warmup", "camcal")


def discover(root) -> Session:
    root = Path(root)
    session: dict = {}
    if (root / "session.json").is_file():
        session = read_json(root / "session.json")
    found: dict = {}
    conflicts: dict = {}
    for key, (prefix, rest) in PATTERNS.items():
        depth = len(rest.split("/"))
        for p in sorted(root.rglob(rest.split("/")[-1])):
            d = p
            for _ in range(depth):
                d = d.parent
            if not d.name.startswith(prefix) or p.relative_to(d).as_posix() != rest:
                continue
            rid = d.name[len(prefix):]
            slot = found.setdefault(rid, {})
            if key in slot and slot[key] != p:
                if _sha(slot[key]) != _sha(p):
                    conflicts.setdefault(rid, {})[key] = f"two copies with different bytes: {slot[key]} and {p}"
                continue
            slot[key] = p
    raw = session.get("score_runs") if isinstance(session, dict) else None
    entries: dict = raw if isinstance(raw, dict) else {}
    ids = set(found) | set(entries)
    runs, stop_run, problems = [], None, []
    for rid in sorted(ids):
        if any(rid.startswith(x) for x in NOT_A_RUN):
            continue
        entry = entries.get(rid) if isinstance(entries.get(rid), dict) else {}
        run = Run(rid, root, found.get(rid, {}), entry, conflicts.get(rid, {}))
        kind, sid = None, None
        try:
            rec = run.setting_record()
            kind = rec.get("kind")
            st = rec.get("setting")
            sid = st.get("setting_id") if isinstance(st, dict) else None
        except (MissingEvidence, EvidenceError):
            pass
        entry_sid = entry.get("setting") if isinstance(entry.get("setting"), str) else None
        if sid and entry_sid and sid != entry_sid:
            problems.append(f"run {rid}: setting_record.json says {sid}, session.json says {entry_sid}")
            run.conflicts["setting_record"] = f"setting {sid} against session.json {entry_sid}"
        sid = sid or entry_sid
        ident = str(entry.get("runIdentity") or "")
        is_stop = kind == "stop" or rid == "stop" or "stop" in ident.lower()
        if kind not in (None, "run", "stop") and not is_stop:
            continue                                   # a calibration or another kind of world run
        run.setting_id, run.kind = sid, ("stop" if is_stop else "run")
        if is_stop:
            if stop_run is not None:
                problems.append(f"two stop runs: {stop_run.run_id} and {rid}")
            stop_run = stop_run or run
            continue
        if sid is None:
            problems.append(f"run {rid}: no setting in setting_record.json or session.json")
            continue
        runs.append(run)

    def first_sim(r: Run):
        try:
            return (0, r.ticks()[0]["simTimeS"], r.run_id)
        except (MissingEvidence, EvidenceError):
            return (1, 0.0, r.run_id)

    runs.sort(key=first_sim)
    counts: dict = {}
    for r in runs:
        counts[r.setting_id] = counts.get(r.setting_id, 0) + 1
        r.repetition = counts[r.setting_id]
    return Session(root, session, runs, stop_run, problems)
