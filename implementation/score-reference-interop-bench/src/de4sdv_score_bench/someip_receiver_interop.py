"""Evaluators of the DE4SDV SOME/IP receiver against the real someipd (P0.3 of the bench).

A run puts someipd, gatewayd, the AutowareToSCORE adapter and the bench's
frame source in a "host" network namespace, and the receiver and a loopback
client in a "guest" namespace; a veth pair joins the two. The runner
(scripts/run_someip_receiver_interop.py) writes raw records per case; the
functions here read only those records and return an outcome:

- identity: every frame that the source produced reaches the loopback
  client byte for byte, in order (the gate asks for 200 of 200);
- resubscribe: after a receiver restart (SIGTERM and SIGKILL), a restart of
  the gateway pair and a link outage longer than the subscription TTL, the
  receiver subscribes again, delivery resumes, no frame comes twice, and
  every drop has a reason;
- no_client: frames that arrive while no client is connected are dropped,
  nothing is queued, and the client receives no frame produced before it
  connected;
- stored_samples: frames that the S-CORE layer stored before a new
  subscription and sends after it are counted and dropped;
- ttl_renewal: without multicast offers, the receiver renews its
  subscription over several TTLs without a lapse or a gap.

Every case also needs: no "Failed to subscribe" line of gatewayd, LoLa
shared memory mapped by the processes that must share it, a balanced
account of every frame in every receiver run, only frames byte-identical to
source frames at the client, and no delivered frame older than its phase.

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
GATEWAYD_SUBSCRIBE_FAILURE = "Failed to subscribe"
DROP_REASONS = (
    "malformed_notification",
    "payload_too_large",
    "length_prefix_mismatch",
    "frame_unreadable",
    "not_subscribed",
    "no_client",
    "sequence_not_increasing",
    "older_than_phase",
    "client_write_failed",
)
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
    def bound_ns(self) -> int:
        start = self.start or {}
        return int(start.get("clock_offset_bound_ns", 0))


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


def _phase_starts(run: ReceiverRun) -> list[tuple[int, int, str]]:
    """(monotonic_ns, phase start realtime_ns, cause) of every phase start of one receiver run."""
    return [(p["monotonic_ns"], p["phase_start_realtime_ns"], p["cause"]) for p in run.of("phase_start")]


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
    delivered_lines = []
    for run in records.receivers:
        counts = _drop_counts(run)
        drops.update(counts)
        unknown = set(counts) - set(DROP_REASONS)
        verdict.check(f"drop_reasons_known:{run.name}", not unknown, f"{run.name}: unknown drop reasons {unknown}")
        final = run.final_status
        frames = run.frames
        if final is not None:
            balanced = final["frames_received"] == final["frames_delivered"] + sum(
                final[f"drop_{reason}"] for reason in DROP_REASONS)
            verdict.check(f"receiver_balanced:{run.name}", balanced,
                          f"{run.name}: frames_received is not delivered plus the drops")
            verdict.check(f"frame_lines_complete:{run.name}", len(frames) == final["frames_received"],
                          f"{run.name}: {len(frames)} frame lines for {final['frames_received']} frames")
            for reason in DROP_REASONS:
                verdict.check(f"drop_count:{run.name}:{reason}", counts.get(reason, 0) == final[f"drop_{reason}"],
                              f"{run.name}: the frame lines and the final status disagree on {reason}")
        phases = _phase_starts(run)
        older = 0
        for frame in frames:
            if frame.get("verdict") != "delivered":
                continue
            delivered_lines.append(frame)
            in_force = [p for p in phases if p[0] <= frame["monotonic_ns"]]
            if not in_force or frame["frame_timestamp_ns"] < max(p[1] for p in in_force) - run.bound_ns:
                older += 1
        verdict.check(f"delivered_not_older_than_phase:{run.name}", older == 0,
                      f"{run.name}: {older} delivered frames are older than their phase start")
    verdict.metrics["drops_by_reason"] = {reason: drops.get(reason, 0) for reason in DROP_REASONS}
    verdict.metrics["frames_delivered_by_receiver"] = len(delivered_lines)

    source_by_sha = {frame.sha256: frame for frame in records.source_frames}
    recorded = records.recorder_frames
    verdict.metrics["frames_at_client"] = len(recorded)
    mismatches = _client_session_mismatches(records)
    verdict.check("client_frames_equal_deliveries", not mismatches,
                  f"the client and the receiver disagree on the delivered frames: {mismatches[:3]}")
    foreign = [frame for frame in recorded if frame.sha256 not in source_by_sha or not frame.prefix_ok]
    verdict.check("client_frames_byte_identical_to_source", not foreign,
                  f"{len(foreign)} frames at the client equal no frame of the source")
    sequences = [frame.sequence for frame in recorded]
    duplicates = [sequence for sequence, count in Counter(sequences).items() if count > 1]
    verdict.metrics["duplicates_at_client"] = len(duplicates)
    verdict.check("no_duplicate_at_client", not duplicates, f"frames delivered twice: {duplicates[:10]}")
    link = _link_notifications(records)
    if records.capture is not None:
        link_sha = {hashlib.sha256(payload).hexdigest() for _, payload in link}
        verdict.check("client_frames_crossed_the_link", all(frame.sha256 in link_sha for frame in recorded),
                      "a frame at the client is missing in the link capture")
        unexplained = [payload for _, payload in link if hashlib.sha256(payload).hexdigest() not in source_by_sha]
        verdict.metrics["link_notifications"] = len(link)
        verdict.check("link_payloads_from_source", not unexplained,
                      f"{len(unexplained)} notifications on the link equal no source frame")
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


def _first_after(events: list[dict[str, Any]], event: str, after_realtime_ns: int) -> dict[str, Any] | None:
    found = [e for e in events if e.get("event") == event and e["realtime_ns"] >= after_realtime_ns]
    return min(found, key=lambda e: e["realtime_ns"]) if found else None


def evaluate_resubscribe(records: CaseRecords) -> dict[str, Any]:
    verdict = Verdict()
    check_common(records, verdict)
    disturbances = records.timeline.get("disturbances", [])
    verdict.check("disturbances_recorded", len(disturbances) >= 4,
                  f"{len(disturbances)} disturbances recorded, 4 planned", MISSING)
    all_events = [event for run in records.receivers for event in run.events]
    recorded = records.recorder_frames
    windows = []
    for index, disturbance in enumerate(disturbances):
        start, end = disturbance["start_realtime_ns"], disturbance["end_realtime_ns"]
        next_start = disturbances[index + 1]["start_realtime_ns"] if index + 1 < len(disturbances) else \
            records.timeline.get("stop_realtime_ns", end + 60 * SECOND_NS)
        # The disturbance ends the old subscription, so the first subscription
        # after its start is the new one; it can come before the runner noted
        # the end (a restarted someipd offers before the runner sees gatewayd).
        subscribed = _first_after(all_events, "subscribed", start)
        resubscribed_at = subscribed["realtime_ns"] if subscribed is not None else None
        delivered_after = [f for f in recorded if resubscribed_at is not None
                           and resubscribed_at <= f.receipt_realtime_ns < next_start]
        window: dict[str, Any] = {"kind": disturbance["kind"],
                                  "resubscribed_after_s": None, "first_frame_after_s": None,
                                  "frames_after": len(delivered_after), "gaps_after": []}
        if subscribed is not None:
            window["resubscribed_after_s"] = round((resubscribed_at - end) / SECOND_NS, 3)
        if delivered_after:
            window["first_frame_after_s"] = round((delivered_after[0].receipt_realtime_ns - end) / SECOND_NS, 3)
            settled = [f.sequence for f in delivered_after
                       if f.receipt_realtime_ns >= delivered_after[0].receipt_realtime_ns + SECOND_NS]
            window["gaps_after"] = _gaps(settled)
        window["drops_in_window"] = dict(Counter(
            e.get("verdict") for e in all_events if e.get("event") == "frame" and e.get("verdict") != "delivered"
            and disturbance["start_realtime_ns"] <= e["realtime_ns"] < next_start))
        ok = (subscribed is not None and subscribed["realtime_ns"] - end <= RECOVERY_LIMIT_NS
              and bool(delivered_after) and delivered_after[0].receipt_realtime_ns - end <= RECOVERY_LIMIT_NS)
        verdict.check(f"resubscribed:{disturbance['kind']}", ok,
                      f"{disturbance['kind']}: no new subscription with delivery within "
                      f"{RECOVERY_LIMIT_NS // SECOND_NS} s")
        verdict.check(f"no_gap_after_recovery:{disturbance['kind']}", not window["gaps_after"],
                      f"{disturbance['kind']}: sequence gaps after recovery {window['gaps_after'][:5]}")
        windows.append(window)
    verdict.metrics["windows"] = windows
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
    client_phases = [p for p in _phase_starts(run) if p[2] == "client_connected"]
    connect = records.recorder_connections[0].connect_realtime_ns
    verdict.check("client_phase_started", len(client_phases) == 1, "no single phase start at the client connection")
    if not client_phases:
        return verdict.result()
    phase_start_ns = client_phases[0][1]
    bound = run.bound_ns
    before = [f for f in run.frames if f["realtime_ns"] < phase_start_ns]
    no_client = [f for f in before if f.get("verdict") == "no_client"]
    verdict.metrics["frames_before_client"] = len(before)
    verdict.metrics["dropped_no_client"] = len(no_client)
    verdict.check("frames_dropped_without_client", len(no_client) >= 10 and len(no_client) == len(before),
                  f"{len(no_client)} of {len(before)} frames before the client were dropped as no_client")
    recorded = records.recorder_frames
    produced_before = [f for f in recorded if f.frame_timestamp_ns is not None
                       and f.frame_timestamp_ns < min(connect, phase_start_ns) - bound]
    verdict.metrics["client_frames_produced_before_connect"] = len(produced_before)
    verdict.check("nothing_produced_before_delivered", not produced_before,
                  f"{len(produced_before)} frames produced before the client connected reached it")
    verdict.check("frames_after_connect", len(recorded) >= 10, f"the client received {len(recorded)} frames")
    if recorded:
        first = recorded[0]
        verdict.metrics["first_frame_age_at_connect_ms"] = round((first.frame_timestamp_ns - connect) / 1e6, 3)
        verdict.check("no_queue", first.frame_timestamp_ns >= phase_start_ns - bound,
                      "the first frame at the client was produced before the client phase: a queue")
        verdict.metrics["gaps_after_connect"] = _gaps([f.sequence for f in recorded])
        verdict.check("no_gap_after_connect", not verdict.metrics["gaps_after_connect"],
                      f"sequence gaps after the connection {verdict.metrics['gaps_after_connect'][:5]}")
    return verdict.result()


def evaluate_stored_samples(records: CaseRecords) -> dict[str, Any]:
    verdict = Verdict()
    check_common(records, verdict)
    verdict.check("one_receiver_run", len(records.receivers) == 1, "the case needs one receiver run", ERROR)
    if verdict.outcome == ERROR:
        return verdict.result()
    run = records.receivers[0]
    phases = [p for p in _phase_starts(run) if p[2] == "subscription_acknowledged"]
    verdict.check("subscribed", bool(phases), "the receiver never subscribed", MISSING)
    if not phases:
        return verdict.result()
    phase_start_ns = phases[0][1]
    bound = run.bound_ns
    cutoff = phase_start_ns - bound
    # someipd sends events only to an acknowledged subscriber, so every frame
    # on the link or at the receiver that is older than the phase start was
    # stored by the layer before the subscription.
    stored_lines = [f for f in run.frames
                    if f.get("frame_timestamp_ns") is not None and f["frame_timestamp_ns"] < cutoff]
    stored_delivered = [f for f in stored_lines if f.get("verdict") == "delivered"]
    link_stored = []
    for _ts_ns, payload in _link_notifications(records):
        ok, fields = read_payload(payload)
        if ok and fields is not None and fields.frame_timestamp_ns < cutoff:
            link_stored.append(fields)
    verdict.metrics["stored_frames_on_link"] = len(link_stored)
    verdict.metrics["stored_frames_at_receiver"] = len(stored_lines)
    verdict.metrics["stored_frames_by_verdict"] = dict(Counter(f.get("verdict") for f in stored_lines))
    if link_stored:
        ages = [(phase_start_ns - f.frame_timestamp_ns) / SECOND_NS for f in link_stored]
        verdict.metrics["stored_age_s"] = {"min": round(min(ages), 3), "max": round(max(ages), 3)}
        verdict.metrics["stored_sequences"] = [min(f.sequence for f in link_stored),
                                               max(f.sequence for f in link_stored)]
    verdict.check("stored_frames_counted_at_receiver", len(stored_lines) == len(link_stored),
                  f"{len(stored_lines)} stored frames in the receiver lines, {len(link_stored)} on the link")
    verdict.check("stored_frames_dropped", not stored_delivered, f"{len(stored_delivered)} stored frames delivered")
    at_client = [f for f in records.recorder_frames
                 if f.frame_timestamp_ns is not None and f.frame_timestamp_ns < cutoff]
    verdict.check("no_stored_frame_at_client", not at_client, f"{len(at_client)} stored frames at the client")
    verdict.check("stored_frames_arrived", bool(link_stored),
                  "no frame older than the subscription arrived: the rule was not exercised", MISSING)
    verdict.check("delivery_after_subscription", len(records.recorder_frames) >= 10,
                  f"the client received {len(records.recorder_frames)} new frames")
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
    nacks = [m for m in records.capture.sd_messages
             for e in m.entries if e.type_name == "SubscribeEventgroupAck" and e.ttl == 0]
    renewals = [m.ts_ns for m in records.capture.sd_messages
                if m.src == records.guest_address for e in m.entries
                if e.type_name == "SubscribeEventgroup" and e.ttl > 0]
    verdict.metrics["subscribes_on_link"] = len(renewals)
    verdict.metrics["acks_on_link"] = len(acks)
    verdict.check("no_nack", not nacks, f"{len(nacks)} Nacks on the link")
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
    phases = [p for p in _phase_starts(run) if p[2] == "subscription_acknowledged"]
    verdict.check("one_subscription_phase", len(phases) == 1, f"{len(phases)} subscription phases")
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
