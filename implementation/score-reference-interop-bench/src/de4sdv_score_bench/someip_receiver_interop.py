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
  subscription over several TTLs without a lapse or a gap;
- ingress_start: the loopback client is a oneshot ingress stand-in that
  only an init stand-in starts, on the receiver's start properties; after a
  receiver restart while the old ingress still runs, a repeat of the start
  trigger brings a client back; an ingress stopped after the first client
  stays down; without any ingress, the receiver gives up after its tries.

The receiver's rule is receiverSubscriptionPhaseDiscardRule of the phase-8
model: a phase holds while the receiver is subscribed and its one client is
connected; in a phase it serves a frame only if the frame is not older than
the phase start less 20 ms (ASM-MW-030) and is no copy of a frame served in
the phase. Every case also needs: no "Failed to subscribe" line of
gatewayd, LoLa shared memory mapped by the processes that must share it, a
balanced account of every frame in every receiver run, only frames
byte-identical to source frames at the client, every delivered frame in a
phase and not older than its margin, and no copy served in a phase. The
evaluators also check the receiver's records against records that it does
not write (the capture, the client's log, the runner's timeline): their own
margin and copy memory, each receiver's end against the planned stop, the
cores of the case, each phase start and end and the drops against the
independent records, in both directions. These checks rest on one clock
(both namespaces share one kernel); a run on two clocks needs a measured
offset bound. A frame
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
PHASE_START_MARGIN_NS = 20_000_000  # ASM-MW-030; the evaluators use this value, not the receiver's record
COPY_MEMORY_FRAMES = 40  # 20 + 20 sample slots
SUBSCRIPTION_TTL_NS = 3 * SECOND_NS
# Independent checks of the phases. Let I be the later of the first Ack of
# someipd (TTL above 0) after the setup of the current TCP connection and
# after the last record that ended a subscription, and the client's connect,
# which the client stamps before connect() and after it. A phase starts at
# most 10 ms after I with the stamp after connect() (the CI starts lie 10 to
# 53 us after it) and not before the stamp before connect(); a phase ends
# within 100 ms of the record of its cause, and each such record inside a
# phase must be followed by its end within 100 ms. The capture slack is the
# clock allowance between the capture and the receiver: 1 ms when the run
# records one clock (both namespaces share one kernel), else the run's
# measured ASM-MW-030 bound plus transit, which also widens the start bound.
START_BOUND_NS = 10 * 1_000_000
PHASE_EVENT_BOUND_NS = 100 * 1_000_000
CAPTURE_SLACK_NS = 1_000_000
CAUSE_TIE_EXTRA_NS = 1_000_000
CLIENT_END_BEFORE_NS = 500 * 1_000_000
RELIABLE_PORT = 30509
MAX_PAYLOAD_BYTES = 2048
CONTENT_DROP_REASONS = ("malformed_notification", "payload_too_large", "length_prefix_mismatch", "frame_unreadable",
                        "field_not_positive")
GAP_MW_041_FRAME = "TransactionLogSet::TransactionLogNode::Reset"
GAP_MW_041_CALLERS = ("ProxyEvent::~ProxyEvent", "LocalServiceInstance::~LocalServiceInstance")
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
# At each of its starts, after its loopback server listens, the receiver sets
# the frame server host of the ingress and then triggers the ingress: its start
# property to 0 and then 1. Until the first client of the receiver process
# connects, it repeats the trigger every 1 s, at most 10 times, then gives up;
# after the first client, it never triggers again (de4sdv_someip_receiver.rc
# passes the same properties). Off Android, the receiver logs the properties
# and does not set them.
FRAME_SERVER_HOST_PROPERTY = "de4sdv.aebs.frame_server.host"
INGRESS_START_PROPERTY = "de4sdv.aebs.ingress.start"
ANNOUNCED_PROPERTIES = ((FRAME_SERVER_HOST_PROPERTY, "127.0.0.1"),)
INGRESS_TRIGGER = ((INGRESS_START_PROPERTY, "0"), (INGRESS_START_PROPERTY, "1"))
INGRESS_RETRIGGER_PERIOD_NS = SECOND_NS
INGRESS_RETRIGGER_LIMIT = 10
RETRIGGER_EARLY_NS = 5_000_000
RETRIGGER_LATE_NS = 500_000_000
PROPERTY_EVENTS = ("property_announced", "property_not_announced")
INGRESS_STEPS = ("receiver_restart_old_ingress_alive", "ingress_stopped", "receiver_start_no_ingress")
FRAMES_AFTER_INGRESS_BACK = 10
KILLED_CLIENT_UNREAD_FRAMES = 3
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
    connect_realtime_ns: int  # stamped after connect() returned
    close_realtime_ns: int | None
    end_reason: str | None = None
    pre_connect_realtime_ns: int | None = None  # stamped before connect()

    @property
    def pre_connect_ns(self) -> int:
        """The pre-connect stamp; records without one give the later stamp, which is the stricter one."""
        return self.pre_connect_realtime_ns if self.pre_connect_realtime_ns is not None else self.connect_realtime_ns


@dataclass
class Phase:
    run: str
    number: int
    cause: str
    start_monotonic_ns: int
    start_realtime_ns: int
    end_monotonic_ns: int | None = None
    end_cause: str | None = None
    end_realtime_ns: int | None = None

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

    def phases(self) -> list[Phase]:
        phases: list[Phase] = []
        for event in self.events:
            if event.get("event") == "phase_start":
                phases.append(Phase(self.name, len(phases) + 1, event.get("cause", ""), event["monotonic_ns"],
                                    event["phase_start_realtime_ns"]))
            elif event.get("event") == "phase_end" and phases and phases[-1].end_monotonic_ns is None:
                phases[-1].end_monotonic_ns = event["monotonic_ns"]
                phases[-1].end_cause = event.get("cause")
                phases[-1].end_realtime_ns = event.get("realtime_ns")
        return phases

    def properties(self) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
        """The properties set or logged before and after the start record (logged after listen())."""
        before: list[tuple[str, str]] = []
        after: list[tuple[str, str]] = []
        started = False
        for record in self.events:
            if record.get("event") == "start":
                started = True
            elif record.get("event") in PROPERTY_EVENTS and record.get("ok", True):
                (after if started else before).append((record.get("name"), record.get("value")))
        return before, after

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
    init_stand_in: list[dict[str, Any]] = field(default_factory=list)


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
            connections[record["connection"]] = RecorderConnection(
                record["connection"], record["realtime_ns"], None,
                pre_connect_realtime_ns=record.get("pre_connect_realtime_ns"))
        elif record.get("event") == "disconnected" and record.get("connection") in connections:
            connections[record["connection"]].close_realtime_ns = record["realtime_ns"]
            connections[record["connection"]].end_reason = record.get("reason")
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
        source_stream=concat("source-stream-*.bin"), recorder_stream=concat("recorder-stream-*.bin"),
        init_stand_in=_json_lines(case_dir / "init-stand-in.jsonl"))


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


def _planned_stop(records: CaseRecords, process: str) -> str | None:
    """The signal of the runner's last planned stop of this process, from the timeline."""
    signal_name = None
    for event in records.timeline.get("events", []):
        if event.get("what") == f"stop {process}":
            signal_name = event.get("signal")
    return signal_name


def _end_problems(records: CaseRecords, run: ReceiverRun) -> list[str]:
    """A receiver stopped by SIGTERM exits with 0 and logs its final status; a missing final status is
    accepted only after a planned SIGKILL, which ends the receiver with -9."""
    process = run.name[:-4] if run.name.endswith(".log") else run.name
    record = records.timeline.get("processes", {}).get(process)
    if record is None:
        return [f"the timeline has no process record of {process}"]
    returncode = record.get("returncode")
    planned = _planned_stop(records, process)
    if planned == "SIGKILL":
        return [] if returncode == -9 else [f"killed by a planned SIGKILL, but ended with {returncode}"]
    if planned in ("SIGTERM", "SIGINT"):
        problems = [] if returncode == 0 else [f"stopped by {planned}, but ended with {returncode}"]
        if run.final_status is None:
            problems.append(f"stopped by {planned}, but logged no final_status")
        return problems
    return [f"ended with {returncode} without a planned stop"]


def capture_slack_ns(records: CaseRecords) -> int | None:
    """The clock allowance between the capture and the receiver; None: a two-clock run without a bound."""
    parameters = records.timeline.get("parameters", {})
    if parameters.get("one_clock"):
        return CAPTURE_SLACK_NS
    bound, transit = parameters.get("clock_offset_bound_ns"), parameters.get("transit_bound_ns")
    if bound is not None and transit is not None:
        return int(bound) + int(transit)
    return None


def _known_core(records: CaseRecords, core: dict[str, Any]) -> bool:
    """GAP-MW-041: gatewayd's abort in TransactionLogNode::Reset under ~ProxyEvent or ~LocalServiceInstance,
    at the end that follows the planned SIGTERM."""
    process = str(core.get("process", ""))
    frames = core.get("named_frames") or core.get("named_top_frames") or []
    at = next((i for i, frame in enumerate(frames) if GAP_MW_041_FRAME in frame), None)
    signature = at is not None and any(caller in frame for frame in frames[at + 1:] for caller in GAP_MW_041_CALLERS)
    stops = [event for event in records.timeline.get("events", [])
             if event.get("what") == f"stop {process}" and event.get("signal") == "SIGTERM"]
    exit_ns = records.timeline.get("processes", {}).get(process, {}).get("exit_monotonic_ns")
    after_stop = bool(stops) and exit_ns is not None and stops[-1].get("monotonic_ns") is not None and \
        exit_ns >= stops[-1]["monotonic_ns"]
    return (process.startswith("gatewayd") and signature and core.get("returncode") == -6
            and _planned_stop(records, process) == "SIGTERM" and after_stop)


def _check_cores(records: CaseRecords, verdict: Verdict) -> None:
    """The core scan must look where the kernel writes cores, for children that may write them. No receiver
    core; every other core must be the known gatewayd abort at its stop (GAP-MW-041), else the case fails."""
    scan = records.timeline.get("core_scan") or {}
    verdict.check("core_pattern_in_core_dir", bool(scan.get("pattern_in_core_dir")),
                  f"kernel.core_pattern {scan.get('core_pattern')!r} is no plain path under {scan.get('core_dir')!r}",
                  ERROR)
    limit = str(scan.get("child_rlimit_core"))
    verdict.check("child_core_limit", limit == "unlimited" or (limit.isdigit() and int(limit) > 0),
                  f"RLIMIT_CORE of a bench child is {scan.get('child_rlimit_core')!r}", ERROR)
    cores = records.timeline.get("cores")
    verdict.check("cores_scanned", cores is not None, "the runner recorded no scan of the core directory", ERROR)
    cores = cores or []
    receiver_cores = [c for c in cores if str(c.get("process", "")).startswith("receiver-")]
    verdict.check("no_receiver_core", not receiver_cores,
                  f"receiver cores: {[(c.get('process'), c.get('core')) for c in receiver_cores]}")
    unknown = [c for c in cores if c not in receiver_cores and not _known_core(records, c)]
    verdict.check("only_known_cores", not unknown,
                  f"cores that are not the known gatewayd abort at its stop (GAP-MW-041): "
                  f"{[(c.get('process'), c.get('returncode'), (c.get('named_top_frames') or [])[:5]) for c in unknown]}")
    verdict.metrics["process_cores"] = [
        {"process": c.get("process"), "returncode": c.get("returncode"), "core": c.get("core"),
         "top_frames": (c.get("named_top_frames") or [])[:6],
         "known": "GAP-MW-041" if _known_core(records, c) else None}
        for c in cores]


def _link_events(records: CaseRecords) -> dict[str, Any]:
    """The independent events of a case: SD messages and TCP ends of the capture, and the client's
    connects and ends, each as a sorted list of CLOCK_REALTIME times."""
    host, guest = records.host_address, records.guest_address
    sd = records.capture.sd_messages if records.capture is not None else []
    streams = records.capture.streams if records.capture is not None else []

    def entries(src: str, name: str, ttl_positive: bool, dst: str | None = None) -> list[int]:
        return sorted(m.ts_ns for m in sd if m.src == src and (dst is None or m.dst == dst)
                      for e in m.entries if e.type_name == name and (e.ttl > 0) == ttl_positive)

    def carries_ack(message) -> bool:
        return any(e.type_name == "SubscribeEventgroupAck" and e.ttl > 0 for e in message.entries)

    reboots = []
    last_session: dict[str, int] = {}
    for message in sorted((m for m in sd if m.src == host), key=lambda m: m.ts_ns):
        previous = last_session.get(message.dst)
        # A reboot message that carries an Ack for the receiver keeps its connection.
        if message.reboot and previous is not None and message.session <= previous and not carries_ack(message):
            reboots.append(message.ts_ns)
        last_session[message.dst] = message.session
    planned_kills = sorted(event["realtime_ns"] for event in records.timeline.get("events", [])
                           if str(event.get("what", "")).startswith(("stop recorder", "stop ingress-"))
                           and event.get("signal") == "SIGKILL")
    client_stops = sorted(event["realtime_ns"] for event in records.timeline.get("events", [])
                          if str(event.get("what", "")).startswith(("stop recorder", "stop ingress-")))
    closes = [c.close_realtime_ns for c in records.recorder_connections if c.close_realtime_ns is not None]
    # someipd's FIN or RST of each TCP connection, by the guest port of the connection.
    server_ends: dict[int, list[int]] = {}
    for s in streams:
        if s.src == host and s.sport == RELIABLE_PORT and s.dst == guest:
            for stamp in (s.fin_ts_ns, s.rst_ts_ns):
                if stamp is not None:
                    server_ends.setdefault(s.dport, []).append(stamp)
    return {
        "acks": entries(host, "SubscribeEventgroupAck", True, guest),
        "nacks": entries(host, "SubscribeEventgroupAck", False, guest),
        "stop_offers": entries(host, "OfferService", False),
        "stop_subscribes": entries(guest, "SubscribeEventgroup", False, host),
        "server_tcp_ends": sorted(stamp for stamps in server_ends.values() for stamp in stamps),
        "server_tcp_ends_by_port": {port: sorted(stamps) for port, stamps in server_ends.items()},
        "reboots": reboots,
        "client_ends": sorted(closes + client_stops),
        "client_ends_reverse": sorted(closes + planned_kills),
    }


def _run_end_ns(records: CaseRecords, run: ReceiverRun) -> int:
    """Where an open phase of the run stops: the planned SIGKILL, else the last record of the run."""
    process = run.name[:-4] if run.name.endswith(".log") else run.name
    kills = [event["realtime_ns"] for event in records.timeline.get("events", [])
             if event.get("what") == f"stop {process}" and event.get("signal") == "SIGKILL"]
    return kills[-1] if kills else max((e.get("realtime_ns", 0) for e in run.events), default=0)


def _phase_problems(records: CaseRecords, run: ReceiverRun, slack: int) -> dict[str, list[str]]:
    """Each phase of the run against the independent records of the case.

    - connection: the current TCP connection is the latest stream of someipd's
      reliable port to the guest that the capture shows set up before the
      start; the receiver's last tcp_connected record must name its port (no
      record: an error).
    - start: I is the later of the first Ack (TTL above 0) after that setup
      and after the last record that ended a subscription (a Nack, a StopOffer,
      a someipd reboot, a TTL lapse), and the post-connect stamp of the open
      client connection. The start lies at or after the client's pre-connect
      stamp and at most 10 ms after I (on two clocks, plus the slack); the last
      Ack must be inside its TTL; the later of the first Ack and the client
      names the cause, unless they lie within the stamp interval plus 1 ms.
    - drops: no frame received between I plus the slack and the start is
      dropped outside a phase, and no frame stamped at or after I less 20 ms
      plus the slack is dropped as older than the phase; a copy repeats one of
      the last 40 frames served in the phase; a frame dropped for its content
      is malformed on the link too.
    - end: the phase ends within 100 ms after the record of its cause: a Nack,
      a StopOffer, someipd's FIN or RST (at or before the end plus the slack),
      a reboot of someipd, the receiver's StopSubscribe at its stop, the end of
      the TTL after the last Ack, or the end of the client.
    - reverse: each such record strictly inside the phase (more than the slack
      after the start and before the end: someipd's FIN or RST of the current
      connection, a Nack, a StopOffer, a reboot, the client's end, an Ack gap
      longer than the TTL) is followed by the end within 100 ms.
    - framing: no phase ends on a loss of the SOME/IP framing.
    """
    events = _link_events(records)
    problems: dict[str, list[str]] = {"starts": [], "drops": [], "ends": [], "reverse": [], "framing": [],
                                      "connection_errors": [], "content": [], "copies": []}
    connections = records.recorder_connections
    run_end = _run_end_ns(records, run)

    def last_before(times: list[int], limit: int) -> int | None:
        found = [stamp for stamp in times if stamp <= limit]
        return found[-1] if found else None

    def near(times: list[int], at: int, before: int, after: int) -> bool:
        return any(at - before <= stamp <= at + after for stamp in times)

    two_clocks = not records.timeline.get("parameters", {}).get("one_clock")
    start_bound = START_BOUND_NS + (slack if two_clocks else 0)
    host, guest = records.host_address, records.guest_address
    setups = sorted((st.first_ts_ns, st.dport) for st in (records.capture.streams if records.capture else [])
                    if st.src == host and st.sport == RELIABLE_PORT and st.dst == guest and st.syn
                    and st.first_ts_ns is not None)
    acks = events["acks"]
    expiries = [current + SUBSCRIPTION_TTL_NS for current, following in zip(acks, acks[1:])
                if following - current > SUBSCRIPTION_TTL_NS]
    subscription_leaves = sorted(events["nacks"] + events["stop_offers"] + events["reboots"] + expiries)
    served_in_phase: dict[int, list[tuple[int, int]]] = {}
    for frame in run.frames:
        if frame.get("verdict") == "delivered":
            phase_now = run.phase_at(frame["monotonic_ns"])
            if phase_now is not None:
                served_in_phase.setdefault(phase_now.number, []).append(
                    (frame["realtime_ns"], frame.get("sequence"), frame.get("frame_timestamp_ns")))

    for phase in run.phases():
        s = phase.start_realtime_ns
        label = f"phase {phase.number}"
        # D9: the current TCP connection, from the capture: the latest stream of
        # someipd's reliable port to the guest set up before the start.
        setup = last_before([at for at, _ in setups], s + slack)
        port = next((dport for at, dport in reversed(setups) if at == setup), None) if setup is not None else None
        logged = [record for record in run.of("tcp_connected") if record["realtime_ns"] <= s]
        logged_port = None
        if logged and ":" in str(logged[-1].get("local", "")):
            logged_port = int(str(logged[-1]["local"]).rsplit(":", 1)[1])
        if not logged:
            problems["connection_errors"].append(f"{label}: the receiver logged no tcp_connected before its start")
        elif setup is None:
            problems["starts"].append(f"{label}: the capture holds no TCP connection of someipd set up before it")
        elif logged_port != port:
            problems["starts"].append(f"{label}: the receiver's connection {logged_port} is not the one in the "
                                      f"capture, {port}")
        last_ack = last_before(acks, s + slack)
        # D10: the first Ack after the setup of the current connection and after
        # the last record that ended a subscription.
        since = max([setup or 0] + [leave for leave in subscription_leaves if leave <= s + slack])
        first_ack = next((a for a in acks if since <= a <= s + slack), None)
        open_connections = [c for c in connections if c.pre_connect_ns <= s
                            and (c.close_realtime_ns is None or c.close_realtime_ns > s)]
        connection = max(open_connections, key=lambda c: c.pre_connect_ns) if open_connections else None
        independent = None
        if first_ack is None or connection is None:
            problems["starts"].append(f"{label}: no Ack after the connection setup ({first_ack}) or no open client "
                                      f"connection with a pre-connect stamp at or before its start")
        else:
            pre, post = connection.pre_connect_ns, connection.connect_realtime_ns
            # D12: the pre-connect stamp is the lower bound; I uses the post stamp.
            independent = max(first_ack, post)
            if last_ack is not None and s - last_ack > SUBSCRIPTION_TTL_NS:
                problems["starts"].append(f"{label}: the last Ack is {(s - last_ack) / SECOND_NS:.3f} s old")
            if s > independent + start_bound:
                problems["starts"].append(f"{label}: starts {(s - independent) / 1e6:.3f} ms after I")
            tie = abs(first_ack - pre) <= (post - pre) + CAUSE_TIE_EXTRA_NS
            causes = ({"subscription_acknowledged", "client_connected"} if tie
                      else {"subscription_acknowledged"} if first_ack > pre else {"client_connected"})
            if phase.cause not in causes:
                problems["starts"].append(f"{label}: cause {phase.cause}, the records give {sorted(causes)}")
        if independent is not None:
            late = [f for f in run.frames if f.get("verdict") in ("no_client", "not_subscribed")
                    and independent + slack < f["realtime_ns"] < s]
            older = [f for f in run.frames if f.get("verdict") == "older_than_phase" and phase.holds_at(f["monotonic_ns"])
                     and f["frame_timestamp_ns"] >= independent - PHASE_START_MARGIN_NS + slack]
            if late:
                problems["drops"].append(f"{label}: {len(late)} frames dropped outside a phase after I, "
                                         f"the first sequence {late[0].get('sequence')}")
            if older:
                problems["drops"].append(f"{label}: {len(older)} frames dropped as older than the phase, "
                                         f"stamped after I less 20 ms, the first sequence {older[0].get('sequence')}")
        # D11: a copy must repeat one of the last 40 frames served in the phase.
        served = served_in_phase.get(phase.number, [])
        for frame in run.frames:
            if frame.get("verdict") != "copy_in_phase" or not phase.holds_at(frame["monotonic_ns"]):
                continue
            earlier = [(seq, stamp) for at, seq, stamp in served if at < frame["realtime_ns"]][-COPY_MEMORY_FRAMES:]
            if (frame.get("sequence"), frame.get("frame_timestamp_ns")) not in earlier:
                problems["copies"].append(f"{label}: sequence {frame.get('sequence')} dropped as a copy, but it is "
                                          f"none of the last {COPY_MEMORY_FRAMES} frames served in the phase")
        e = phase.end_realtime_ns
        cause = phase.end_cause
        if e is not None and cause is not None:
            if "framing" in cause:
                problems["framing"].append(f"{label}: ended on a loss of the SOME/IP framing of the TCP stream")
            else:
                if cause == "client_lost":
                    ok = near(events["client_ends"], e, CLIENT_END_BEFORE_NS, PHASE_EVENT_BOUND_NS)
                elif cause == "subscription_lost:stopped":
                    ok = near(events["stop_subscribes"], e, PHASE_EVENT_BOUND_NS + slack, PHASE_EVENT_BOUND_NS + slack)
                elif cause == "subscription_lost:ttl_expired":
                    last_ack = last_before(events["acks"], e)
                    ok = last_ack is not None and SUBSCRIPTION_TTL_NS - 5 * 1_000_000 - slack <= e - last_ack <= \
                        SUBSCRIPTION_TTL_NS + 2 * PHASE_EVENT_BOUND_NS + slack
                else:
                    key = {"subscription_lost:nack": "nacks", "subscription_lost:stop_offer": "stop_offers",
                           "subscription_lost:tcp_closed": "server_tcp_ends",
                           "subscription_lost:server_reboot": "reboots"}.get(cause)
                    ok = key is not None and near(events[key], e, PHASE_EVENT_BOUND_NS, slack)
                if not ok:
                    problems["ends"].append(f"{label}: end {cause} has no independent record within the bound")
        # Reverse: each leave record inside the phase is followed by its end within the bound.
        stop = e if e is not None else run_end

        def inside_phase(times: list[int]) -> list[int]:
            return [stamp for stamp in times if s + slack < stamp < stop - slack]

        inside = {
            "someipd's FIN or RST": inside_phase(events["server_tcp_ends_by_port"].get(port, [])),
            "a Nack": inside_phase(events["nacks"]),
            "a StopOffer": inside_phase(events["stop_offers"]),
            "a someipd reboot": inside_phase(events["reboots"]),
            "the client's end": inside_phase(events["client_ends_reverse"]),
        }
        for what, times in inside.items():
            for stamp in times:
                if e is None or e - stamp > PHASE_EVENT_BOUND_NS + slack:
                    problems["reverse"].append(f"{label}: {what} at {stamp} inside the phase, "
                                               f"{'no end' if e is None else f'end {(e - stamp) / 1e6:.3f} ms later'}")
        acks_until = [a for a in acks if a <= stop]
        held = [a for a in acks_until if a <= s + slack][-1:] + [a for a in acks_until if a > s + slack]
        for current, following in zip(held, held[1:] + [stop]):
            expiry = current + SUBSCRIPTION_TTL_NS
            if following - current > SUBSCRIPTION_TTL_NS + PHASE_EVENT_BOUND_NS + slack and expiry < stop:
                if e is None or e - expiry > PHASE_EVENT_BOUND_NS + slack:
                    problems["reverse"].append(f"{label}: an Ack gap longer than the TTL after {current}, "
                                               f"the phase goes on")
    # D11: a frame dropped for its content must be malformed on the link too.
    notifications = records.capture.notifications(host, RELIABLE_PORT) if records.capture is not None else []
    for frame in run.frames:
        if frame.get("verdict") not in CONTENT_DROP_REASONS:
            continue
        session = frame.get("someip_session")
        found = [m for m in notifications if m.session == session and m.dst == guest
                 and frame["realtime_ns"] - PHASE_EVENT_BOUND_NS - slack <= m.ts_ns <= frame["realtime_ns"] + slack]
        if found and _well_formed(found[-1]):
            problems["content"].append(f"session {session} dropped as {frame.get('verdict')}, but its notification "
                                       f"on the link is well-formed")
    return problems


def _well_formed(message) -> bool:
    """The checks of the receiver on one notification of the frame event, read from the capture."""
    if (message.service, message.method, message.message_type, message.return_code) != (0x4DEE, 0x8001, 0x02, 0):
        return False
    if message.protocol_version != 1 or len(message.payload) > MAX_PAYLOAD_BYTES:
        return False
    ok, fields = read_payload(message.payload)
    return ok and fields is not None and fields.sequence > 0 and fields.frame_timestamp_ns > 0


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
    slack = capture_slack_ns(records)
    verdict.check("capture_clock_known", slack is not None,
                  "a run on two clocks needs its measured ASM-MW-030 bound and its transit bound", ERROR)

    drops: Counter = Counter()
    delivered = []  # (run, frame line, phase)
    band_frames = 0
    clock_steps = 0
    case_start = _case_start_ns(records)
    phase_report = []
    for run in records.receivers:
        counts = _drop_counts(run)
        drops.update(counts)
        unknown = set(counts) - set(DROP_REASONS)
        verdict.check(f"drop_reasons_known:{run.name}", not unknown, f"{run.name}: unknown drop reasons {unknown}")
        final = run.final_status
        frames = run.frames
        start_record = run.start or {}
        verdict.check(f"rule_constants:{run.name}",
                      start_record.get("phase_start_margin_ns") == PHASE_START_MARGIN_NS
                      and start_record.get("copy_memory_frames") == COPY_MEMORY_FRAMES,
                      f"{run.name}: the start record gives margin {start_record.get('phase_start_margin_ns')} ns "
                      f"and copy memory {start_record.get('copy_memory_frames')}, not {PHASE_START_MARGIN_NS} and "
                      f"{COPY_MEMORY_FRAMES}")
        problems = _end_problems(records, run)
        verdict.check(f"receiver_end:{run.name}", not problems, f"{run.name}: {problems}")
        if slack is not None:
            phase_problems = _phase_problems(records, run, slack)
            for key, name in (("starts", "phase_starts_independent"), ("drops", "drops_against_independent_starts"),
                              ("ends", "phase_ends_independent"), ("reverse", "leave_records_end_their_phase"),
                              ("framing", "no_framing_loss_in_a_phase"), ("content", "content_drops_malformed_on_link"),
                              ("copies", "copies_repeat_a_served_frame")):
                found = phase_problems[key]
                verdict.check(f"{name}:{run.name}", not found, f"{run.name}: {found[:3]}")
            found = phase_problems["connection_errors"]
            verdict.check(f"receiver_logs_its_connection:{run.name}", not found, f"{run.name}: {found[:3]}", ERROR)
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
        # The ingress is oneshot: each start of the receiver must start it
        # again, and only after the loopback server listens; until the first
        # client, the trigger repeats every 1 s, at most 10 times.
        before, after = run.properties()
        triggers = run.of("ingress_trigger")
        if run.final_status is None and after[-1:] == [INGRESS_TRIGGER[0]]:
            after = after[:-1]  # a killed run can stop between 0 and 1
        expected = list(ANNOUNCED_PROPERTIES) + list(INGRESS_TRIGGER) * len(triggers)
        verdict.check(f"ingress_triggers_after_listen:{run.name}",
                      not before and bool(triggers) and after == expected
                      and triggers[0].get("reason") == "listening" and all(t.get("ok", True) for t in triggers),
                      f"{run.name}: properties after the start record {after} (before it: {before}), "
                      f"{len(triggers)} ingress triggers")
        problems = _trigger_problems(run)
        verdict.check(f"ingress_trigger_rule:{run.name}", not problems, f"{run.name}: {problems[:3]}")
        # A clock step voids the run: the phase start and the frame stamps no
        # longer share one time line (ASM-MW-030).
        steps = run.of("clock_step")
        clock_steps += len(steps)
        verdict.check(f"no_clock_step:{run.name}", not steps,
                      f"{run.name}: {len(steps)} clock steps, the first of {steps[0].get('step_ns') if steps else 0} ns",
                      MISSING)
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
            if stamp < phase.start_realtime_ns - PHASE_START_MARGIN_NS:
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
    _check_cores(records, verdict)
    verdict.metrics["drops_by_reason"] = {reason: drops.get(reason, 0) for reason in DROP_REASONS}
    verdict.metrics["frames_delivered_by_receiver"] = len(delivered)
    verdict.metrics["clock_steps"] = clock_steps
    if delivered:
        # Receipt time on the receiver clock less frame_timestamp_ns: the path
        # latency here, on one clock; on the VM also the host-guest offset.
        lags = [frame["realtime_ns"] - frame["frame_timestamp_ns"] for _, frame, _ in delivered]
        verdict.metrics["receipt_minus_frame_ms"] = {"min": round(min(lags) / 1e6, 3), "max": round(max(lags) / 1e6, 3)}
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


def _trigger_problems(run: ReceiverRun) -> list[str]:
    """Ingress triggers of one receiver run against the rule: the first at listen; then, until the first
    client, a repeat every 1 s, at most 10, and a give-up 1 s after the last; none after the first client."""
    problems = []
    first_client = False
    last_ns = None
    repeats = 0
    gave_up = False

    def spaced(record: dict[str, Any], what: str) -> None:
        gap = record["monotonic_ns"] - last_ns if last_ns is not None else None
        if gap is None or not INGRESS_RETRIGGER_PERIOD_NS - RETRIGGER_EARLY_NS <= gap <= \
                INGRESS_RETRIGGER_PERIOD_NS + RETRIGGER_LATE_NS:
            problems.append(f"{what} {gap / SECOND_NS if gap is not None else None} s after the last try")

    for record in run.events:
        event = record.get("event")
        if event == "client_connected":
            first_client = True
        elif event == "ingress_trigger":
            if first_client or gave_up:
                problems.append(f"trigger at {record['monotonic_ns']} after the first client or the give-up")
            if record.get("reason") == "listening":
                if last_ns is not None:
                    problems.append("a second trigger at listen")
            elif record.get("reason") == "no_first_client":
                repeats += 1
                spaced(record, "repeat")
            else:
                problems.append(f"trigger reason {record.get('reason')}")
            last_ns = record["monotonic_ns"]
        elif event == "ingress_trigger_gave_up":
            gave_up = True
            if first_client or repeats != INGRESS_RETRIGGER_LIMIT:
                problems.append(f"gave up after {repeats} repeats, first client {first_client}")
            spaced(record, "give-up")
    if repeats > INGRESS_RETRIGGER_LIMIT:
        problems.append(f"{repeats} repeats, more than {INGRESS_RETRIGGER_LIMIT}")
    return problems


def _client_session_mismatches(records: CaseRecords) -> list[str]:
    """Compares, per loopback connection, the frames the client received with the frames the receiver delivered.

    The k-th client connection that a receiver run accepted is the k-th
    connection of the client. A receiver run that was killed may have written
    one more frame than it logged, so its last connection may hold one extra
    frame at the end. A client that was killed or stopped (its connection has
    no end record, or ends with reason stopped) may not have read the last
    frames that the receiver wrote: its frames are then the first ones of the
    delivered frames, with at most 3 missing at the end.
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
    closed = {c.index: c.close_realtime_ns is not None and c.end_reason != "stopped"
              for c in records.recorder_connections}
    for session, connection in zip(sessions, connections):
        received = [f.sequence for f in records.recorder_frames if f.connection == connection]
        delivered = session["sequences"]
        if received == delivered:
            continue
        if session["killed"] and len(received) == len(delivered) + 1 and received[:-1] == delivered:
            continue
        if not closed[connection] and received == delivered[:len(received)] and \
                len(delivered) - len(received) <= KILLED_CLIENT_UNREAD_FRAMES:
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
    margin = PHASE_START_MARGIN_NS
    connect = records.recorder_connections[0].pre_connect_ns
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

    The steps, each with the source paused so that the newest frames stay in
    the sample slots: the first subscription with a late gatewayd (frames from
    before the phase arrive in it), a gatewayd restart beside a running
    someipd in a phase (stored frames repeat served frames: copies), and a
    restart of the gateway pair (frames from before the new phase). The case
    passes only when both checks of the rule acted on real stored frames: a
    frame older than its phase start less the margin, and a copy.
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
    steps = [{"kind": "late_gatewayd_first_subscription", "start_realtime_ns": 0}] + list(disturbances)
    link = _link_notifications(records)
    report = []
    for index, step in enumerate(steps):
        start = step["start_realtime_ns"]
        end = (steps[index + 1]["start_realtime_ns"] if index + 1 < len(steps)
               else records.timeline.get("stop_realtime_ns", 2 ** 63))
        lines = [f for f in run.frames if start <= f["realtime_ns"] < end]
        stored = [f for f in lines if f.get("verdict") in STORED_FRAME_VERDICTS]
        # Independent view of the link: notifications whose frame is older
        # than the receiver's phase start in force, less the margin, and
        # repeats of an earlier notification.
        seen: set[str] = set()
        older_on_link = 0
        repeats_on_link = 0
        for ts_ns, payload in link:
            digest = hashlib.sha256(payload).hexdigest()
            repeat = digest in seen
            seen.add(digest)
            if not start <= ts_ns < end:
                continue
            repeats_on_link += int(repeat)
            ok, fields = read_payload(payload)
            in_force = [p for p in phases if p.start_realtime_ns <= ts_ns]
            if ok and fields is not None and in_force and \
                    fields.frame_timestamp_ns < in_force[-1].start_realtime_ns - PHASE_START_MARGIN_NS:
                older_on_link += 1
        report.append({"step": step["kind"], "stored_dropped": dict(Counter(f["verdict"] for f in stored)),
                       "older_on_link": older_on_link, "repeats_on_link": repeats_on_link,
                       "served": sum(1 for f in lines if f.get("verdict") == "delivered")})
    verdict.metrics["steps"] = report
    older = [f for f in run.frames if f.get("verdict") == "older_than_phase"]
    copies = [f for f in run.frames if f.get("verdict") == "copy_in_phase"]
    verdict.metrics["stored_frames_dropped"] = len(older) + len(copies)
    verdict.metrics["dropped_older_than_phase"] = len(older)
    verdict.metrics["dropped_copy_in_phase"] = len(copies)
    if older:
        ages = [(run.phase_at(f["monotonic_ns"]).start_realtime_ns - f["frame_timestamp_ns"]) / SECOND_NS
                for f in older if run.phase_at(f["monotonic_ns"]) is not None]
        if ages:
            verdict.metrics["older_frame_age_s"] = {"min": round(min(ages), 3), "max": round(max(ages), 3)}
    _check_disturbances(records, verdict, planned=2)
    verdict.check("frames_from_before_the_phase_dropped_in_a_phase", bool(older),
                  "no frame from before its phase arrived in a phase: check (a) of the rule did not act", MISSING)
    verdict.check("copies_dropped_in_a_phase", bool(copies),
                  "no copy of a served frame arrived in a phase: check (b) of the rule did not act", MISSING)
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


def evaluate_ingress_start(records: CaseRecords) -> dict[str, Any]:
    """The start trigger of the oneshot ingress: bounded to the start of each receiver process.

    The init stand-in of the runner starts the ingress stand-in on each
    receiver record of the frame server host or of the ingress start set to
    1, unless the ingress still runs. The steps:
    - receiver_restart_old_ingress_alive: the receiver is killed and starts
      again while its old ingress still runs (it stays alive 2.5 s after its
      stream ends). At least one start request must come while the old
      ingress runs, else the step did not show the race (inconclusive). A
      repeat of the trigger (reason no_first_client) must start the new
      ingress, which connects within 1 s per ignored start trigger, plus
      1 s, plus 3 s for the receiver restart and the ingress start, and
      receives frames.
    - ingress_stopped: the bench stops the ingress after the first client of
      the receiver: no start request, no start and no client follow.
    - receiver_start_no_ingress: the receiver starts while no ingress can
      start: it tries 11 times, 1 s apart, and gives up.
    The trigger rule of every receiver run is checked in check_common.
    """
    verdict = Verdict()
    check_common(records, verdict)
    standin = records.init_stand_in
    verdict.check("init_stand_in_records", bool(standin), "the case has no records of the init stand-in", ERROR)
    verdict.check("three_receiver_runs", len(records.receivers) == 3, "the case needs three receiver runs", ERROR)
    disturbances = [d for d in records.timeline.get("disturbances", []) if d.get("kind") in INGRESS_STEPS]
    verdict.check("three_steps", [d["kind"] for d in disturbances] == list(INGRESS_STEPS),
                  f"the steps are {[d['kind'] for d in disturbances]}", ERROR)
    if verdict.outcome == ERROR:
        return verdict.result()
    triggers = {(run.name, record["monotonic_ns"]): record.get("reason")
                for run in records.receivers for record in run.of("ingress_trigger")}
    stop_ns = records.timeline.get("stop_realtime_ns", 2 ** 63)
    windows = {}
    for index, step in enumerate(disturbances):
        end = disturbances[index + 1]["start_realtime_ns"] if index + 1 < len(disturbances) else stop_ns
        windows[step["kind"]] = (step["start_realtime_ns"], end)
    first = [c for c in records.recorder_connections if c.connect_realtime_ns < disturbances[0]["start_realtime_ns"]]
    verdict.check("ingress_started_at_listen", len(first) == 1, f"{len(first)} client connections before the steps")
    report = []

    # 1. The start race: the old ingress still runs when the new receiver starts.
    kind = "receiver_restart_old_ingress_alive"
    start, end = windows[kind]
    window = [r for r in standin if start <= r.get("realtime_ns", 0) < end]
    started_at = next((i for i, r in enumerate(window) if r.get("event") == "started"), len(window))
    started = window[started_at] if started_at < len(window) else None
    old_alive = [r for r in window[:started_at] if r.get("event") == "start_ignored" and r.get("state") == "running"]
    ignored_triggers = sum(1 for r in old_alive if r.get("property") == INGRESS_START_PROPERTY)
    cause = None
    if started is not None:
        cause = (triggers.get((started.get("receiver_log"), started.get("receiver_monotonic_ns")))
                 if started.get("property") == INGRESS_START_PROPERTY else "frame_server_host")
    connection = next((c for c in records.recorder_connections if start <= c.connect_realtime_ns < end), None)
    back_ns = connection.connect_realtime_ns - start if connection is not None else None
    bound_ns = INGRESS_RETRIGGER_PERIOD_NS * (ignored_triggers + 1) + 3 * SECOND_NS
    frames = sum(1 for f in records.recorder_frames if connection is not None and f.connection == connection.index)
    report.append({"step": kind, "start_requests_while_old_ingress_ran": len(old_alive),
                   "start_triggers_ignored": ignored_triggers, "started_by": cause,
                   "client_back_s": round(back_ns / SECOND_NS, 3) if back_ns is not None else None,
                   "bound_s": bound_ns / SECOND_NS, "frames_after": frames})
    verdict.check(f"start_request_while_the_old_ingress_ran:{kind}", bool(old_alive),
                  f"{kind}: no start request came while the old ingress ran", MISSING)
    verdict.check(f"ingress_back:{kind}", back_ns is not None and back_ns <= bound_ns,
                  f"{kind}: client back after {back_ns} ns, bound {bound_ns} ns")
    verdict.check(f"started_by_a_repeat:{kind}", cause == "no_first_client",
                  f"{kind}: the ingress came back through {cause}, not through a repeat of the trigger")
    verdict.check(f"frames_after:{kind}", frames >= FRAMES_AFTER_INGRESS_BACK, f"{kind}: {frames} frames at the client")

    # 2. A stopped ingress stays down after the first client.
    kind = "ingress_stopped"
    start, end = windows[kind]
    requests = [r for r in standin if start <= r.get("realtime_ns", 0) < end
                and r.get("event") in ("started", "start_ignored")]
    later = [c for c in records.recorder_connections if start <= c.connect_realtime_ns < end]
    run = records.receivers[1]
    first_client = next((r["realtime_ns"] for r in run.of("client_connected")), None)
    after_first = [r for r in run.of("ingress_trigger") if first_client is not None and r["realtime_ns"] > first_client]
    report.append({"step": kind, "start_requests": len(requests), "client_connections": len(later),
                   "triggers_after_first_client": len(after_first), "window_s": round((end - start) / SECOND_NS, 3)})
    verdict.check(f"long_enough:{kind}", end - start >= 3 * INGRESS_RETRIGGER_PERIOD_NS,
                  f"{kind}: the step lasted {(end - start) / SECOND_NS:.3f} s", ERROR)
    verdict.check(f"no_trigger_after_the_first_client:{kind}", first_client is not None and not after_first,
                  f"{kind}: {len(after_first)} triggers of {run.name} after its first client")
    verdict.check(f"stays_down:{kind}", not requests and not later,
                  f"{kind}: {len(requests)} start requests and {len(later)} client connections after the stop")

    # 3. No ingress at all: the receiver tries 11 times and gives up.
    kind = "receiver_start_no_ingress"
    run = records.receivers[2]
    tries = run.of("ingress_trigger")
    gave_up = run.of("ingress_trigger_gave_up")
    report.append({"step": kind, "tries": len(tries), "gave_up": bool(gave_up),
                   "gave_up_after_s": round((gave_up[0]["monotonic_ns"] - tries[0]["monotonic_ns"]) / SECOND_NS, 3)
                   if gave_up and tries else None})
    verdict.check(f"tries_then_gave_up:{kind}", len(tries) == 1 + INGRESS_RETRIGGER_LIMIT and len(gave_up) == 1,
                  f"{kind}: {len(tries)} tries, {len(gave_up)} give-up records")
    verdict.metrics["steps"] = report
    verdict.metrics["ingress_starts"] = sum(1 for r in standin if r.get("event") == "started")
    verdict.metrics["ingress_triggers"] = dict(Counter(triggers.values()))
    return verdict.result()


EVALUATORS = {
    "identity": evaluate_identity,
    "resubscribe": evaluate_resubscribe,
    "no_client": evaluate_no_client,
    "stored_samples": evaluate_stored_samples,
    "ttl_renewal": evaluate_ttl_renewal,
    "ingress_start": evaluate_ingress_start,
}
