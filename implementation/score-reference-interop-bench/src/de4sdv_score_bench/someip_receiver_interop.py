"""Evaluators of the DE4SDV SOME/IP receiver against the real someipd.

A run puts someipd, gatewayd, the AutowareToSCORE adapter and the bench's
frame source in a "host" network namespace, and the receiver and a loopback
client in a "guest" namespace; a veth pair joins the two. The runner
(scripts/run_someip_receiver_interop.py) writes raw records per case; the
functions here read only those records and return an outcome:

- identity: every frame that the source produced reaches the loopback
  client byte for byte, in order (the gate asks for 200 of 200);
- resubscribe: after a receiver restart (SIGTERM and SIGKILL), a restart of
  the gateway pair and a link outage longer than the subscription TTL, the
  receiver subscribes again, delivery resumes, and every drop has a reason;
- no_client: frames that arrive while no client is connected are dropped,
  nothing is queued, and the client receives no frame produced before the
  margin of its phase start;
- stored_samples: the frames that the layer stored and sends after a new
  subscription in the host half (a late gatewayd, a gatewayd restart in a
  phase, a restart of the gateway pair) are counted, and the rule drops the
  copies and the frames older than the phase;
- ttl_renewal: without multicast offers, the receiver renews its
  subscription over several TTLs without a lapse or a gap.

The receiver's rule is receiverSubscriptionPhaseDiscardRule of the phase-8
model: a phase holds while the receiver is subscribed and its one client is
connected; in a phase it serves a frame only if the frame is not older than
the phase start less 20 ms (ASM-MW-030) and is no copy of a frame served in
the phase. Every case also needs: no "Failed to subscribe" line of
gatewayd, LoLa shared memory mapped by the processes that must share it, a
balanced account of every frame in every receiver run, only frames
byte-identical to source frames at the client, every delivered frame in a
phase and not older than its margin, and no copy served in a phase. A frame
that the AEBS stack produced in the 20 ms margin of a phase start (the band
of GAP-MW-045) is reported, not failed.

These are CI regression and design data, not evidence of record. Outcomes
use the evidence outcome names of the middleware verification model.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any

from de4sdv_score_bench.abort_matrix import ERROR, FAIL, MISSING, PASS, parse_adapter_log
from de4sdv_score_bench.someip_capture import CaptureAnalysis, analyse_capture
from de4sdv_score_bench.visualization_frame import read_payload

SECOND_NS = 1_000_000_000
RECOVERY_LIMIT_NS = 15 * SECOND_NS
PHASE_START_MARGIN_NS = 20_000_000  # ASM-MW-030
GATEWAYD_SUBSCRIBE_FAILURE = "Failed to subscribe"
DROP_REASONS = (
    "malformed_notification",
    "payload_too_large",
    "length_prefix_mismatch",
    "frame_unreadable",
    "not_subscribed",
    "no_client",
    "field_not_positive",
    "older_than_phase",
    "copy_in_phase",
    "client_write_failed",
)
STORED_FRAME_VERDICTS = ("older_than_phase", "copy_in_phase")
LARGEST_FRAME_BYTES = 2044


@dataclass
class SourceFrame:
    sequence: int
    frame_timestamp_ns: int
    size: int
    sha256: str  # of prefix and frame, the payload of the frame event
    connection: int


@dataclass
class RecordedFrame:
    connection: int
    receipt_realtime_ns: int
    payload_bytes: int
    prefix_ok: bool
    sequence: int | None
    frame_timestamp_ns: int | None
    sha256: str


@dataclass
class RecorderConnection:
    index: int
    connect_realtime_ns: int
    close_realtime_ns: int | None


@dataclass
class Phase:
    run: str
    number: int
    cause: str
    start_monotonic_ns: int
    start_realtime_ns: int
    end_monotonic_ns: int | None = None
    end_cause: str | None = None

    def holds_at(self, monotonic_ns: int) -> bool:
        return self.start_monotonic_ns <= monotonic_ns and (
            self.end_monotonic_ns is None or monotonic_ns < self.end_monotonic_ns)


@dataclass
class ReceiverRun:
    name: str
    events: list[dict[str, Any]]

    def of(self, event: str) -> list[dict[str, Any]]:
        return [record for record in self.events if record.get("event") == event]

    @property
    def start(self) -> dict[str, Any] | None:
        starts = self.of("start")
        return starts[0] if starts else None

    @property
    def frames(self) -> list[dict[str, Any]]:
        return self.of("frame")

    @property
    def final_status(self) -> dict[str, Any] | None:
        finals = self.of("final_status")
        return finals[-1] if finals else None

    @property
    def margin_ns(self) -> int:
        start = self.start or {}
        return int(start.get("phase_start_margin_ns", PHASE_START_MARGIN_NS))

    def phases(self) -> list[Phase]:
        phases: list[Phase] = []
        for event in self.events:
            if event.get("event") == "phase_start":
                phases.append(Phase(self.name, len(phases) + 1, event.get("cause", ""), event["monotonic_ns"],
                                    event["phase_start_realtime_ns"]))
            elif event.get("event") == "phase_end" and phases and phases[-1].end_monotonic_ns is None:
                phases[-1].end_monotonic_ns = event["monotonic_ns"]
                phases[-1].end_cause = event.get("cause")
        return phases

    def phase_at(self, monotonic_ns: int) -> Phase | None:
        for phase in self.phases():
            if phase.holds_at(monotonic_ns):
                return phase
        return None


@dataclass
class CaseRecords:
    case: str
    timeline: dict[str, Any]
    source_frames: list[SourceFrame]
    recorder_frames: list[RecordedFrame]
    recorder_connections: list[RecorderConnection]
    receivers: list[ReceiverRun]
    capture: CaptureAnalysis | None
    gatewayd_logs: dict[str, str] = field(default_factory=dict)
    shared_memory: dict[str, Any] | None = None
    source_stream: bytes | None = None
    recorder_stream: bytes | None = None
    host_address: str = "10.250.0.1"
    guest_address: str = "10.250.0.2"


# --------------------------------------------------------------------------- loading


def _json_lines(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                records.append(value)
    return records


def load_case(case_dir: Path) -> CaseRecords:
    """Reads the raw records of one case directory of the runner."""
    timeline = json.loads((case_dir / "timeline.json").read_text(encoding="utf-8"))
    sources = [SourceFrame(r["seq"], r["frame_timestamp_ns"], r["size"], r["payload_sha256"], r["connection"])
               for r in _json_lines(case_dir / "source.jsonl") if r.get("event") == "sent"]
    recorder = _json_lines(case_dir / "recorder.jsonl")
    frames = [RecordedFrame(r["connection"], r["receipt_realtime_ns"], r["payload_bytes"], r["prefix_ok"],
                            r.get("sequence"), r.get("frame_timestamp_ns"), r["payload_sha256"])
              for r in recorder if r.get("event") == "frame"]
    connections = {}
    for record in recorder:
        if record.get("event") == "connected":
            connections[record["connection"]] = RecorderConnection(record["connection"], record["realtime_ns"], None)
        elif record.get("event") == "disconnected" and record.get("connection") in connections:
            connections[record["connection"]].close_realtime_ns = record["realtime_ns"]
    receivers = []
    for name in timeline.get("receiver_logs", []):
        path = case_dir / name
        receivers.append(ReceiverRun(name, parse_adapter_log(path.read_text(encoding="utf-8", errors="replace"))
                                     if path.exists() else []))
    capture_path = case_dir / "link.pcap"
    capture = analyse_capture(capture_path) if capture_path.exists() and capture_path.stat().st_size > 24 else None
    gatewayd = {name: (case_dir / name).read_text(encoding="utf-8", errors="replace")
                for name in timeline.get("gatewayd_logs", []) if (case_dir / name).exists()}
    shm_path = case_dir / "shared-memory.json"
    shm = json.loads(shm_path.read_text(encoding="utf-8")) if shm_path.exists() else None

    def concat(pattern: str) -> bytes | None:
        files = sorted(case_dir.glob(pattern))
        return b"".join(path.read_bytes() for path in files) if files else None

    return CaseRecords(
        case=timeline.get("case", case_dir.name), timeline=timeline, source_frames=sources, recorder_frames=frames,
        recorder_connections=sorted(connections.values(), key=lambda c: c.index), receivers=receivers,
        capture=capture, gatewayd_logs=gatewayd, shared_memory=shm,
        source_stream=concat("source-stream-*.bin"), recorder_stream=concat("recorder-stream-*.bin"))


# --------------------------------------------------------------------------- shared checks


class Verdict:
    def __init__(self) -> None:
        self.outcome = PASS
        self.reasons: list[str] = []
        self.checks: dict[str, bool] = {}
        self.metrics: dict[str, Any] = {}

    def check(self, name: str, ok: bool, reason: str, outcome: str = FAIL) -> bool:
        self.checks[name] = bool(ok)
        if not ok:
            if self.outcome == PASS:
                self.outcome = outcome
            self.reasons.append(reason)
        return bool(ok)

    def result(self) -> dict[str, Any]:
        return {"outcome": self.outcome, "reasons": self.reasons, "checks": self.checks, "metrics": self.metrics}


def _link_notifications(records: CaseRecords) -> list[tuple[int, bytes]]:
    if records.capture is None:
        return []
    return [(m.ts_ns, m.payload) for m in records.capture.notifications(records.host_address, 30509)
            if m.method == 0x8001 and m.message_type == 0x02]


def _drop_counts(run: ReceiverRun) -> Counter:
    return Counter(frame.get("verdict") for frame in run.frames if frame.get("verdict") != "delivered")


def _case_start_ns(records: CaseRecords) -> int:
    starts = [run.start["realtime_ns"] for run in records.receivers if run.start]
    return min(starts) if starts else 0


def check_common(records: CaseRecords, verdict: Verdict, *, shared_memory_expected: bool = True) -> None:
    for name, text in records.gatewayd_logs.items():
        verdict.check(f"gatewayd_subscribed:{name}", GATEWAYD_SUBSCRIBE_FAILURE not in text,
                      f"{name} logged '{GATEWAYD_SUBSCRIBE_FAILURE}'")
    if shared_memory_expected:
        shm = records.shared_memory or {}
        pairs = shm.get("shared_pairs", {})
        verdict.check("lola_shared_memory_adapter_gatewayd", bool(pairs.get("adapter-gatewayd")),
                      "the adapter and gatewayd map no common LoLa shared memory file")
        verdict.check("lola_shared_memory_gatewayd_someipd", bool(pairs.get("gatewayd-someipd")),
                      "gatewayd and someipd map no common LoLa shared memory file")
        verdict.check("lola_files_owned_by_bench_user", shm.get("foreign_owned_files") == [],
                      f"LoLa files not owned by the bench user: {shm.get('foreign_owned_files')}")
    verdict.check("receiver_started", bool(records.receivers) and all(r.start for r in records.receivers),
                  "a receiver run has no start line", ERROR)

    drops: Counter = Counter()
    delivered = []  # (run, frame line, phase)
    band_frames = 0
    case_start = _case_start_ns(records)
    phase_report = []
    for run in records.receivers:
        counts = _drop_counts(run)
        drops.update(counts)
        unknown = set(counts) - set(DROP_REASONS)
        verdict.check(f"drop_reasons_known:{run.name}", not unknown, f"{run.name}: unknown drop reasons {unknown}")
        final = run.final_status
        frames = run.frames
        if final is not None:
            balanced = final["frames_received"] == final["frames_delivered"] + sum(
                final.get(f"drop_{reason}", 0) for reason in DROP_REASONS)
            verdict.check(f"receiver_balanced:{run.name}", balanced,
                          f"{run.name}: frames_received is not delivered plus the drops")
            verdict.check(f"frame_lines_complete:{run.name}", len(frames) == final["frames_received"],
                          f"{run.name}: {len(frames)} frame lines for {final['frames_received']} frames")
            for reason in DROP_REASONS:
                verdict.check(f"drop_count:{run.name}:{reason}", counts.get(reason, 0) == final.get(f"drop_{reason}"),
                              f"{run.name}: the frame lines and the final status disagree on {reason}")
        phases = run.phases()
        for phase in phases:
            phase_report.append({"run": run.name, "phase": phase.number, "cause": phase.cause,
                                 "start_s": round((phase.start_realtime_ns - case_start) / SECOND_NS, 3),
                                 "end_cause": phase.end_cause})
        outside = 0
        older = 0
        copies = 0
        served: dict[int, set[tuple[int, int]]] = {}
        for frame in frames:
            if frame.get("verdict") != "delivered":
                continue
            phase = next((p for p in phases if p.holds_at(frame["monotonic_ns"])), None)
            if phase is None:
                outside += 1
                continue
            stamp = frame["frame_timestamp_ns"]
            if stamp < phase.start_realtime_ns - run.margin_ns:
                older += 1
            elif stamp < phase.start_realtime_ns:
                band_frames += 1
            key = (frame["sequence"], stamp)
            if key in served.setdefault(phase.number, set()):
                copies += 1
            served[phase.number].add(key)
            delivered.append((run, frame, phase))
        verdict.check(f"delivered_in_a_phase:{run.name}", outside == 0,
                      f"{run.name}: {outside} frames delivered outside a phase")
        verdict.check(f"delivered_not_older_than_phase:{run.name}", older == 0,
                      f"{run.name}: {older} delivered frames are older than their phase start less the margin")
        verdict.check(f"no_copy_served_in_phase:{run.name}", copies == 0,
                      f"{run.name}: {copies} copies served in one phase")
    verdict.metrics["drops_by_reason"] = {reason: drops.get(reason, 0) for reason in DROP_REASONS}
    verdict.metrics["frames_delivered_by_receiver"] = len(delivered)
    verdict.metrics["phases"] = phase_report
    verdict.metrics["band_frames"] = band_frames

    source_by_sha = {frame.sha256: frame for frame in records.source_frames}
    recorded = records.recorder_frames
    verdict.metrics["frames_at_client"] = len(recorded)
    mismatches = _client_session_mismatches(records)
    verdict.check("client_frames_equal_deliveries", not mismatches,
                  f"the client and the receiver disagree on the delivered frames: {mismatches[:3]}")
    foreign = [frame for frame in recorded if frame.sha256 not in source_by_sha or not frame.prefix_ok]
    verdict.check("client_frames_byte_identical_to_source", not foreign,
                  f"{len(foreign)} frames at the client equal no frame of the source")
    # A frame reaches the client twice only from two phases, and only in the
    # margin of the later phase start (GAP-MW-045): reported, not failed.
    seen: dict[tuple[int, int], int] = {}
    band_duplicates = 0
    other_duplicates = 0
    for run, frame, phase in delivered:
        key = (frame["sequence"], frame["frame_timestamp_ns"])
        if key in seen:
            if frame["frame_timestamp_ns"] < phase.start_realtime_ns:
                band_duplicates += 1
            else:
                other_duplicates += 1
        seen[key] = seen.get(key, 0) + 1
    verdict.metrics["duplicates_at_client"] = band_duplicates + other_duplicates
    verdict.metrics["band_duplicates"] = band_duplicates
    verdict.check("no_duplicate_outside_the_band", other_duplicates == 0,
                  f"{other_duplicates} frames reached the client twice outside the band of a phase start")
    link = _link_notifications(records)
    if records.capture is not None:
        link_sha = {hashlib.sha256(payload).hexdigest() for _, payload in link}
        verdict.check("client_frames_crossed_the_link", all(frame.sha256 in link_sha for frame in recorded),
                      "a frame at the client is missing in the link capture")
        unexplained = [payload for _, payload in link if hashlib.sha256(payload).hexdigest() not in source_by_sha]
        verdict.metrics["link_notifications"] = len(link)
        verdict.check("link_payloads_from_source", not unexplained,
                      f"{len(unexplained)} notifications on the link equal no source frame")
        repeats = len(link) - len({hashlib.sha256(payload).hexdigest() for _, payload in link})
        verdict.metrics["repeats_on_link"] = repeats
    else:
        verdict.check("link_capture_present", False, "no link capture", MISSING)


def _client_session_mismatches(records: CaseRecords) -> list[str]:
    """Compares, per loopback connection, the frames the client received with the frames the receiver delivered.

    The k-th client connection that a receiver run accepted is the k-th
    connection of the client. A receiver run that was killed may have written
    one more frame than it logged, so its last connection may hold one extra
    frame at the end.
    """
    sessions = []
    problems = []
    for run in records.receivers:
        killed = run.final_status is None
        current = None
        for event in run.events:
            if event.get("event") == "client_connected":
                current = {"run": run.name, "realtime_ns": event["realtime_ns"], "sequences": [], "killed": killed}
                sessions.append(current)
            elif event.get("event") == "frame" and event.get("verdict") == "delivered":
                if current is None:
                    problems.append(f"{run.name} delivered a frame without a client")
                else:
                    current["sequences"].append(event.get("sequence"))
    sessions.sort(key=lambda session: session["realtime_ns"])
    connections = [c.index for c in records.recorder_connections]
    if len(sessions) != len(connections):
        problems.append(f"{len(sessions)} accepted client connections, {len(connections)} client connections")
        return problems
    for session, connection in zip(sessions, connections):
        received = [f.sequence for f in records.recorder_frames if f.connection == connection]
        delivered = session["sequences"]
        if received == delivered:
            continue
        if session["killed"] and len(received) == len(delivered) + 1 and received[:-1] == delivered:
            continue
        problems.append(f"connection {connection} ({session['run']}): {len(received)} received, "
                        f"{len(delivered)} delivered")
    return problems


def _gaps(sequences: list[int]) -> list[tuple[int, int]]:
    return [(a, b) for a, b in zip(sequences, sequences[1:]) if b != a + 1]


def _first_after(events: list[dict[str, Any]], event: str, after_realtime_ns: int) -> dict[str, Any] | None:
    found = [e for e in events if e.get("event") == event and e["realtime_ns"] >= after_realtime_ns]
    return min(found, key=lambda e: e["realtime_ns"]) if found else None


def _window_end(records: CaseRecords, disturbances: list[dict[str, Any]], index: int) -> int:
    if index + 1 < len(disturbances):
        return disturbances[index + 1]["start_realtime_ns"]
    return records.timeline.get("stop_realtime_ns", disturbances[index]["end_realtime_ns"] + 60 * SECOND_NS)


def _window_drops(records: CaseRecords, start: int, end: int) -> dict[str, int]:
    return dict(Counter(e.get("verdict") for run in records.receivers for e in run.frames
                        if e.get("verdict") != "delivered" and start <= e["realtime_ns"] < end))


# --------------------------------------------------------------------------- cases


def evaluate_identity(records: CaseRecords, expected_frames: int = 200) -> dict[str, Any]:
    verdict = Verdict()
    check_common(records, verdict)
    sources = records.source_frames
    verdict.metrics["frames_produced"] = len(sources)
    verdict.check("source_produced_all", len(sources) == expected_frames,
                  f"the source produced {len(sources)} of {expected_frames} frames", MISSING)
    recorded = records.recorder_frames
    identical = [frame.sha256 for frame in recorded] == [frame.sha256 for frame in sources]
    verdict.metrics["frames_byte_identical"] = sum(
        1 for a, b in zip(recorded, sources) if a.sha256 == b.sha256)
    verdict.check("all_frames_byte_identical_in_order", identical and len(recorded) == expected_frames,
                  f"{verdict.metrics['frames_byte_identical']} of {expected_frames} frames byte-identical in order")
    verdict.check("streams_equal", records.source_stream is not None
                  and records.source_stream == records.recorder_stream,
                  "the byte stream at the client differs from the byte stream of the source")
    link = _link_notifications(records)
    verdict.check("link_carries_every_frame_in_order",
                  [hashlib.sha256(payload).hexdigest() for _, payload in link] == [f.sha256 for f in sources],
                  "the link capture does not carry every source frame once, in order")
    largest = [f for f in sources if f.size == LARGEST_FRAME_BYTES]
    verdict.check("largest_frame_crossed", bool(largest) and all(
        any(r.sha256 == f.sha256 for r in recorded) for f in largest),
        f"no frame of {LARGEST_FRAME_BYTES} bytes reached the client")
    verdict.metrics["largest_frames"] = len(largest)
    total_drops = sum(verdict.metrics["drops_by_reason"].values())
    verdict.check("no_drop", total_drops == 0, f"the receiver dropped {total_drops} frames")
    return verdict.result()


def _check_disturbances(records: CaseRecords, verdict: Verdict, planned: int) -> list[dict[str, Any]]:
    """Per disturbance: a new subscription when one is expected, delivery after it, drops, no gap."""
    disturbances = records.timeline.get("disturbances", [])
    verdict.check("disturbances_recorded", len(disturbances) >= planned,
                  f"{len(disturbances)} disturbances recorded, {planned} planned", MISSING)
    all_events = [event for run in records.receivers for event in run.events]
    recorded = records.recorder_frames
    windows = []
    for index, disturbance in enumerate(disturbances):
        kind = disturbance["kind"]
        start, end = disturbance["start_realtime_ns"], disturbance["end_realtime_ns"]
        window_end = _window_end(records, disturbances, index)
        expects = disturbance.get("expects_resubscription", True)
        window: dict[str, Any] = {"kind": kind, "expects_resubscription": expects, "resubscribed_after_s": None,
                                  "first_frame_after_s": None, "frames_after": 0, "gaps_after": [],
                                  "drops_in_window": _window_drops(records, start, window_end)}
        if expects:
            # The disturbance ends the old subscription, so the first subscription
            # after its start is the new one; it can come before the runner noted
            # the end (a restarted someipd offers before the runner sees gatewayd).
            subscribed = _first_after(all_events, "subscribed", start)
            resumed_at = subscribed["realtime_ns"] if subscribed is not None else None
        else:
            subscribed = None
            resumed_at = end
        after = [f for f in recorded if resumed_at is not None and resumed_at <= f.receipt_realtime_ns < window_end]
        window["frames_after"] = len(after)
        if subscribed is not None:
            window["resubscribed_after_s"] = round((subscribed["realtime_ns"] - end) / SECOND_NS, 3)
        if after:
            window["first_frame_after_s"] = round((after[0].receipt_realtime_ns - end) / SECOND_NS, 3)
            settled = [f.sequence for f in after if f.receipt_realtime_ns >= after[0].receipt_realtime_ns + SECOND_NS]
            window["gaps_after"] = _gaps(settled)
        recovered = bool(after) and after[0].receipt_realtime_ns - end <= RECOVERY_LIMIT_NS
        if expects:
            recovered = recovered and subscribed is not None and subscribed["realtime_ns"] - end <= RECOVERY_LIMIT_NS
        verdict.check(f"recovered:{kind}", recovered,
                      f"{kind}: no {'new subscription with ' if expects else ''}delivery within "
                      f"{RECOVERY_LIMIT_NS // SECOND_NS} s")
        verdict.check(f"no_gap_after_recovery:{kind}", not window["gaps_after"],
                      f"{kind}: sequence gaps after recovery {window['gaps_after'][:5]}")
        windows.append(window)
    verdict.metrics["windows"] = windows
    return windows


def evaluate_resubscribe(records: CaseRecords) -> dict[str, Any]:
    verdict = Verdict()
    check_common(records, verdict)
    _check_disturbances(records, verdict, planned=4)
    return verdict.result()


def evaluate_no_client(records: CaseRecords) -> dict[str, Any]:
    verdict = Verdict()
    check_common(records, verdict)
    verdict.check("one_receiver_run", len(records.receivers) == 1, "the case needs one receiver run", ERROR)
    verdict.check("one_client_connection", len(records.recorder_connections) == 1,
                  f"{len(records.recorder_connections)} client connections, 1 planned", ERROR)
    if verdict.outcome == ERROR:
        return verdict.result()
    run = records.receivers[0]
    phases = run.phases()
    verdict.check("one_phase_started_by_the_client", len(phases) == 1 and phases[0].cause == "client_connected",
                  f"phases {[p.cause for p in phases]}: one phase, started by the client, planned")
    if not phases:
        return verdict.result()
    phase_start_ns = phases[0].start_realtime_ns
    margin = run.margin_ns
    connect = records.recorder_connections[0].connect_realtime_ns
    before = [f for f in run.frames if f["monotonic_ns"] < phases[0].start_monotonic_ns]
    no_client = [f for f in before if f.get("verdict") == "no_client"]
    verdict.metrics["frames_before_client"] = len(before)
    verdict.metrics["dropped_no_client"] = len(no_client)
    verdict.check("frames_dropped_without_client", len(no_client) >= 10 and len(no_client) == len(before),
                  f"{len(no_client)} of {len(before)} frames before the client were dropped as no_client")
    recorded = records.recorder_frames
    cutoff = min(connect, phase_start_ns) - margin
    produced_before = [f for f in recorded if f.frame_timestamp_ns is not None and f.frame_timestamp_ns < cutoff]
    in_band = [f for f in recorded if f.frame_timestamp_ns is not None
               and cutoff <= f.frame_timestamp_ns < min(connect, phase_start_ns)]
    verdict.metrics["client_frames_produced_before_the_margin"] = len(produced_before)
    verdict.metrics["client_frames_in_the_band"] = len(in_band)
    verdict.check("nothing_produced_before_the_margin_delivered", not produced_before,
                  f"{len(produced_before)} frames produced before the margin of the client phase reached it")
    verdict.check("frames_after_connect", len(recorded) >= 10, f"the client received {len(recorded)} frames")
    if recorded:
        first = recorded[0]
        verdict.metrics["first_frame_age_at_connect_ms"] = round((first.frame_timestamp_ns - connect) / 1e6, 3)
        verdict.check("no_queue", first.frame_timestamp_ns >= phase_start_ns - margin,
                      "the first frame at the client was produced before the margin of its phase: a queue")
        verdict.metrics["gaps_after_connect"] = _gaps([f.sequence for f in recorded])
        verdict.check("no_gap_after_connect", not verdict.metrics["gaps_after_connect"],
                      f"sequence gaps after the connection {verdict.metrics['gaps_after_connect'][:5]}")
    return verdict.result()


def evaluate_stored_samples(records: CaseRecords) -> dict[str, Any]:
    """Stored frames after new subscriptions in the host half: counted per step and dropped.

    The steps: the first subscription with a late gatewayd, a gatewayd restart
    beside a running someipd in a phase (stored frames that repeat served
    frames are copies), and a restart of the gateway pair (stored frames are
    older than the new phase).
    """
    verdict = Verdict()
    check_common(records, verdict)
    verdict.check("one_receiver_run", len(records.receivers) == 1, "the case needs one receiver run", ERROR)
    if verdict.outcome == ERROR:
        return verdict.result()
    run = records.receivers[0]
    phases = run.phases()
    verdict.check("subscribed", bool(phases), "the receiver never started a phase", MISSING)
    if not phases:
        return verdict.result()
    disturbances = records.timeline.get("disturbances", [])
    steps = [{"kind": "late_gatewayd_first_subscription", "start_realtime_ns": 0,
              "end_realtime_ns": phases[0].start_realtime_ns}] + list(disturbances)
    total_stored = 0
    report = []
    for index, step in enumerate(steps):
        start = step["start_realtime_ns"]
        end = (steps[index + 1]["start_realtime_ns"] if index + 1 < len(steps)
               else records.timeline.get("stop_realtime_ns", 2 ** 63))
        lines = [f for f in run.frames if start <= f["realtime_ns"] < end]
        stored = [f for f in lines if f.get("verdict") in STORED_FRAME_VERDICTS]
        total_stored += len(stored)
        report.append({"step": step["kind"], "stored_dropped": dict(Counter(f["verdict"] for f in stored)),
                       "served": sum(1 for f in lines if f.get("verdict") == "delivered")})
    verdict.metrics["steps"] = report
    verdict.metrics["stored_frames_dropped"] = total_stored
    _check_disturbances(records, verdict, planned=2)
    # Independent count from the link: a stored frame of a restart repeats an
    # earlier notification byte for byte.
    link = _link_notifications(records)
    seen: set[str] = set()
    repeats = 0
    for _ts_ns, payload in link:
        digest = hashlib.sha256(payload).hexdigest()
        if digest in seen:
            repeats += 1
        seen.add(digest)
    verdict.metrics["repeats_on_link"] = repeats  # the duplicate check shows that none reached the client twice
    verdict.check("stored_frames_arrived", total_stored > 0 or repeats > 0,
                  "no stored frame arrived after a new subscription: the rule was not exercised", MISSING)
    return verdict.result()


def evaluate_ttl_renewal(records: CaseRecords, *, minimum_ttls: int = 3) -> dict[str, Any]:
    verdict = Verdict()
    check_common(records, verdict)
    verdict.check("one_receiver_run", len(records.receivers) == 1, "the case needs one receiver run", ERROR)
    if verdict.outcome == ERROR or records.capture is None:
        verdict.check("link_capture_present", records.capture is not None, "no link capture", MISSING)
        return verdict.result()
    run = records.receivers[0]
    start = run.start or {}
    ttl_s = int(start.get("subscription_ttl_s", 0))
    verdict.check("unicast_fallback_only", start.get("join_multicast") is False,
                  "the receiver joined the multicast group")
    final = run.final_status or {}
    verdict.check("no_offer_seen", final.get("offers") == 0, f"the receiver saw {final.get('offers')} offers")
    acks = [m.ts_ns for m in records.capture.sd_messages
            if m.src == records.host_address and m.dst == records.guest_address
            for e in m.entries if e.type_name == "SubscribeEventgroupAck" and e.ttl > 0]
    nacks = [m.ts_ns for m in records.capture.sd_messages
             if m.src == records.host_address and m.dst == records.guest_address
             for e in m.entries if e.type_name == "SubscribeEventgroupAck" and e.ttl == 0]
    renewals = [m.ts_ns for m in records.capture.sd_messages
                if m.src == records.guest_address for e in m.entries
                if e.type_name == "SubscribeEventgroup" and e.ttl > 0]
    verdict.metrics["subscribes_on_link"] = len(renewals)
    verdict.metrics["acks_on_link"] = len(acks)
    # someipd answers a subscription that comes before its first offer with a
    # Nack; the fallback then subscribes again. Only a Nack after the first
    # Ack is a lapse of the renewal.
    first_ack = acks[0] if acks else None
    verdict.metrics["nacks_before_first_ack"] = sum(1 for t in nacks if first_ack is None or t < first_ack)
    late_nacks = [t for t in nacks if first_ack is not None and t > first_ack]
    verdict.check("no_nack_after_the_first_ack", not late_nacks, f"{len(late_nacks)} Nacks after the first Ack")
    if len(acks) >= 2:
        window_s = (acks[-1] - acks[0]) / SECOND_NS
        largest_gap_s = max(b - a for a, b in zip(acks, acks[1:])) / SECOND_NS
    else:
        window_s, largest_gap_s = 0.0, None
    verdict.metrics["acked_window_s"] = round(window_s, 3)
    verdict.metrics["largest_ack_gap_s"] = None if largest_gap_s is None else round(largest_gap_s, 3)
    verdict.check("window_longer_than_ttls", ttl_s > 0 and window_s >= minimum_ttls * ttl_s,
                  f"the acknowledged window is {window_s:.1f} s, less than {minimum_ttls} TTLs of {ttl_s} s",
                  MISSING)
    verdict.check("renewed_before_each_ttl", largest_gap_s is not None and largest_gap_s < ttl_s,
                  f"the largest gap between two Acks is {largest_gap_s} s, not less than the TTL {ttl_s} s")
    first_subscribed = next((e["realtime_ns"] for e in run.events if e.get("event") == "subscribed"), None)
    stop_ns = records.timeline.get("stop_realtime_ns") or 2**63
    lapses = [e["event"] for e in run.events if e.get("event") in (
        "subscription_expired", "subscription_lost", "nack", "subscribe_timeout", "connection_ended")
        and first_subscribed is not None and first_subscribed <= e["realtime_ns"] < stop_ns]
    verdict.check("subscribed", first_subscribed is not None, "the receiver never subscribed", MISSING)
    verdict.check("no_lapse", not lapses, f"the subscription lapsed: {lapses}")
    phases = run.phases()
    verdict.check("one_phase", len(phases) == 1, f"{len(phases)} phases")
    sequences = [f.sequence for f in records.recorder_frames]
    verdict.metrics["frames_at_client"] = len(sequences)
    verdict.metrics["gaps"] = _gaps(sequences)
    verdict.check("no_gap", bool(sequences) and not verdict.metrics["gaps"],
                  f"sequence gaps {verdict.metrics['gaps'][:5]}")
    return verdict.result()


EVALUATORS = {
    "identity": evaluate_identity,
    "resubscribe": evaluate_resubscribe,
    "no_client": evaluate_no_client,
    "stored_samples": evaluate_stored_samples,
    "ttl_renewal": evaluate_ttl_renewal,
}
