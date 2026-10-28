"""Tests of the evaluators of the SOME/IP receiver against someipd.

Each test builds the raw records of one case in memory, as the runner
writes them: frame source, loopback client, receiver log lines, the link
capture, gatewayd logs and the LoLa shared memory snapshot. A passing
record set is then changed in one place to show that the evaluator fails
for that reason (mutation tests). The receiver's rule is the subscription
phase discard rule of the phase-8 model: a phase holds while the receiver
is subscribed and its one client is connected, with a margin of 20 ms
before the phase start and no copy served twice in a phase.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))

from de4sdv_score_bench.someip_capture import (  # noqa: E402
    CaptureAnalysis,
    SdEntry,
    SdMessage,
    SomeipMessage,
    TcpStream,
)
from de4sdv_score_bench.someip_receiver_interop import (  # noqa: E402
    ANNOUNCED_PROPERTIES,
    DROP_REASONS,
    INGRESS_START_PROPERTY,
    INGRESS_TRIGGER,
    CaseRecords,
    ReceiverRun,
    RecordedFrame,
    RecorderConnection,
    SourceFrame,
    evaluate_identity,
    evaluate_ingress_start,
    evaluate_no_client,
    evaluate_resubscribe,
    evaluate_stored_samples,
    evaluate_ttl_renewal,
    load_case,
)
from de4sdv_score_bench.visualization_frame import encode_frame, length_prefixed  # noqa: E402

S = 1_000_000_000
MS = 1_000_000
T0 = 1_793_116_440_000_000_000
MARGIN = 20 * MS
HOST, GUEST = "10.250.0.1", "10.250.0.2"
PASS, FAIL, MISSING = "passBoundedVerification", "failObservedBehavior", "inconclusiveMissingEvidence"
ERROR = "errorEvidence"
SIZES = (64, 200, 800, 1100, 2044, 96, 512)


def payload(sequence: int, timestamp: int) -> bytes:
    return length_prefixed(encode_frame(sequence, timestamp, bridge_receipt_timestamp_ns=timestamp,
                                        source_identity="de4sdv-ci-frame-source",
                                        size=SIZES[sequence % len(SIZES)]))


class Builder:
    """Raw records of one case: frames produced every 100 ms from T0 + 1 s."""

    def __init__(self, frames: int = 200) -> None:
        self.frames = frames
        self.payloads = {seq: payload(seq, self.produced(seq)) for seq in range(1, frames + 1)}
        self.receivers: list[list[dict]] = []
        self.recorded: list[RecordedFrame] = []
        self.connections: list[RecorderConnection] = []
        self.link: list[SomeipMessage] = []
        self.sd: list[SdMessage] = []
        self.tcp_ends: list[int] = []  # FIN times of TCP connections that someipd closed
        self.auto_renewals = True  # a correct run renews its subscription every second
        self.log_tcp_connected = True  # a correct receiver logs each TCP connection
        self.timeline: dict = {"case": "test", "disturbances": [], "stop_realtime_ns": T0 + 600 * S}
        self.gatewayd = {"gatewayd.log": "[gatewayd] Connected to someipd over the mw::com IPC binding\n"}
        self.shm = {"shared_pairs": {"adapter-gatewayd": ["/dev/shm/lola-data-1"],
                                     "gatewayd-someipd": ["/dev/shm/lola-data-2"]},
                    "foreign_owned_files": []}

    @staticmethod
    def produced(seq: int) -> int:
        return T0 + S + seq * 100 * MS

    def receiver(self, multicast: bool = True, at: int = T0) -> list[dict]:
        """A receiver run that starts at at: its start record, the host property and the trigger at listen."""
        events = [{"event": "start", "monotonic_ns": at - T0, "realtime_ns": at, "phase_start_margin_ns": MARGIN,
                   "copy_memory_frames": 40, "join_multicast": multicast, "subscription_ttl_s": 3}]
        events += [{"event": "property_not_announced", "monotonic_ns": at - T0 + 1000, "realtime_ns": at + 1000,
                    "name": name, "value": value, "reason": "not Android"} for name, value in ANNOUNCED_PROPERTIES]
        self.receivers.append(events)
        self.trigger(events, at + 2000, "listening")
        return events

    def trigger(self, events: list[dict], realtime_ns: int, reason: str, ok: bool = True) -> None:
        """An ingress trigger of the receiver: the start property to 0 and 1, then its record."""
        for name, value in INGRESS_TRIGGER:
            events.append({"event": "property_not_announced", "monotonic_ns": realtime_ns - T0,
                           "realtime_ns": realtime_ns, "name": name, "value": value, "reason": "not Android"})
        self.event(events, "ingress_trigger", realtime_ns, reason=reason, property=INGRESS_START_PROPERTY, ok=ok)

    @staticmethod
    def event(events: list[dict], name: str, realtime_ns: int, **fields) -> None:
        events.append({"event": name, "monotonic_ns": realtime_ns - T0, "realtime_ns": realtime_ns, **fields})

    def phase_start(self, events: list[dict], cause: str, realtime_ns: int) -> None:
        """A phase start and the link record that a correct run has for it: an Ack inside its TTL."""
        acks = [m.ts_ns for m in self.sd if m.src == HOST for e in m.entries
                if e.type_name == "SubscribeEventgroupAck" and e.ttl > 0 and m.ts_ns <= realtime_ns]
        if not acks or realtime_ns - max(acks) > 3 * S:
            self.sd.append(SdMessage(realtime_ns - 10_000 if cause == "subscription_acknowledged" else realtime_ns - 400 * MS,
                                     HOST, 30490, GUEST, 30490, len(self.sd) + 1, True, True,
                                     [SdEntry(7, "SubscribeEventgroupAck", 0x4DEE, 1, 1, 3, 1, None, [])]))
        self.event(events, "subscribed" if cause == "subscription_acknowledged" else "client_connected", realtime_ns)
        self.event(events, "phase_start", realtime_ns, cause=cause, phase_start_realtime_ns=realtime_ns)

    def phase_end(self, events: list[dict], cause: str, realtime_ns: int) -> None:
        """A phase end and the independent record that a correct run has for its cause."""
        before = realtime_ns - 10_000
        if cause == "subscription_lost:stopped":
            self.sd.append(SdMessage(realtime_ns, GUEST, 30490, HOST, 30490, len(self.sd) + 1, True, True,
                                     [SdEntry(6, "SubscribeEventgroup", 0x4DEE, 1, 1, 0, 1, None, [])]))
        elif cause == "subscription_lost:stop_offer":
            self.sd.append(SdMessage(before, HOST, 30490, "224.244.224.245", 30490, len(self.sd) + 1, True, False,
                                     [SdEntry(1, "OfferService", 0x4DEE, 1, 1, 0, None, 0, [])]))
        elif cause == "subscription_lost:nack":
            self.sd.append(SdMessage(before, HOST, 30490, GUEST, 30490, len(self.sd) + 1, True, True,
                                     [SdEntry(7, "SubscribeEventgroupAck", 0x4DEE, 1, 1, 0, 1, None, [])]))
        elif cause == "subscription_lost:tcp_closed":
            self.tcp_ends.append(before)
        elif cause == "client_lost" and self.connections and self.connections[-1].close_realtime_ns is None:
            self.connections[-1].close_realtime_ns = before
        self.event(events, "phase_end", realtime_ns, cause=cause)

    def connect_client(self, events: list[dict], realtime_ns: int, *, starts_phase: bool) -> int:
        """The client stamps 100 us before connect() and at its return; the receiver accepts at the return."""
        index = len(self.connections) + 1
        self.connections.append(RecorderConnection(index, realtime_ns, None,
                                                   pre_connect_realtime_ns=realtime_ns - 100_000))
        if starts_phase:
            self.phase_start(events, "client_connected", realtime_ns)
        else:
            self.event(events, "client_connected", realtime_ns)
        return index

    def arrive(self, events: list[dict], seq: int, verdict: str, *, at: int | None = None,
               on_link: bool = True) -> None:
        data = self.payloads[seq]
        receipt = at if at is not None else self.produced(seq) + 2 * MS
        self.event(events, "frame", receipt, verdict=verdict, sequence=seq, frame_timestamp_ns=self.produced(seq),
                   payload_bytes=len(data), someip_session=seq & 0xFFFF)
        if on_link:
            self.link.append(SomeipMessage(receipt - MS, HOST, 30509, GUEST, 40000, 0x4DEE, 0x8001, 0, seq & 0xFFFF,
                                           1, 1, 0x02, 0, data))
        if verdict == "delivered":
            self.recorded.append(RecordedFrame(len(self.connections), receipt + MS, len(data), True,
                                               seq, self.produced(seq), hashlib.sha256(data).hexdigest()))

    def final(self, events: list[dict], realtime_ns: int) -> None:
        frames = [e for e in events if e["event"] == "frame"]
        counts = {reason: sum(1 for e in frames if e["verdict"] == reason) for reason in DROP_REASONS}
        status = {f"drop_{reason}": count for reason, count in counts.items()}
        status.update(frames_received=len(frames),
                      frames_delivered=sum(1 for e in frames if e["verdict"] == "delivered"),
                      offers=0 if not events[0]["join_multicast"] else 5)
        self.event(events, "final_status", realtime_ns, **status)

    def ack(self, realtime_ns: int, ttl: int = 3) -> None:
        self.sd.append(SdMessage(realtime_ns - MS, GUEST, 30490, HOST, 30490, len(self.sd) + 1, True, True,
                                 [SdEntry(6, "SubscribeEventgroup", 0x4DEE, 1, 1, 3, 1, None, [(GUEST, 40000, "tcp")])]))
        self.sd.append(SdMessage(realtime_ns, HOST, 30490, GUEST, 30490, len(self.sd) + 1, True, True,
                                 [SdEntry(7, "SubscribeEventgroupAck", 0x4DEE, 1, 1, ttl, 1, None, [])]))

    def connections_of(self, receivers: list[list[dict]]) -> list[TcpStream]:
        """The TCP connections of a correct run: each receiver run connects at its start and again after each
        phase end that ends its connection; someipd's FIN of a tcp_closed end belongs to the connection it ends.
        Each connection gets the tcp_connected record of the receiver; a run that has its own keeps them."""
        streams: list[TcpStream] = []
        assigned: set[int] = set()
        port = 41000
        for events in receivers:
            if any(e.get("event") == "tcp_connected" for e in events):
                continue
            ending = ("subscription_lost:tcp_closed", "subscription_lost:nack", "subscription_lost:stop_offer",
                      "subscription_lost:server_reboot", "subscription_lost:stream_framing_lost")
            times = [events[0]["realtime_ns"] + 1000] + [e["realtime_ns"] + 1000 for e in events
                                                          if e.get("event") == "phase_end" and e.get("cause") in ending]
            for k, connect in enumerate(times):
                limit = times[k + 1] if k + 1 < len(times) else 2 ** 63
                fins = [stamp for stamp in self.tcp_ends if connect < stamp < limit]
                assigned.update(fins)
                streams.append(TcpStream(len(streams) + 1, HOST, 30509, GUEST, port, syn=True, first_ts_ns=connect,
                                         fin=bool(fins), fin_ts_ns=fins[0] if fins else None))
                if self.log_tcp_connected:
                    at = next((i for i, e in enumerate(events) if e.get("realtime_ns", 0) > connect), len(events))
                    events.insert(at, {"event": "tcp_connected", "monotonic_ns": connect - T0, "realtime_ns": connect,
                                       "local": f"{GUEST}:{port}", "server": f"{HOST}:30509"})
                port += 1
        for index, stamp in enumerate(self.tcp_ends):
            if stamp not in assigned:
                streams.append(TcpStream(100 + index, HOST, 30509, GUEST, 40001 + index, fin=True, fin_ts_ns=stamp))
        return streams

    def records(self) -> CaseRecords:
        stream = TcpStream(0, HOST, 30509, GUEST, 40000, messages=list(self.link))
        receivers = [copy.deepcopy(e) for e in self.receivers]
        closed = self.connections_of(receivers)
        # The runner's records of each receiver process: a run with a final
        # status was stopped by SIGTERM and ended with 0, a run without one
        # was killed by a planned SIGKILL; no core.
        timeline = copy.deepcopy(self.timeline)
        timeline.setdefault("events", [])
        timeline.setdefault("processes", {})
        timeline.setdefault("cores", [])
        timeline.setdefault("parameters", {"one_clock": True})
        timeline.setdefault("core_scan", {"core_pattern": "/runner/cores/core.%e.%p", "core_dir": "/runner/cores",
                                          "pattern_in_core_dir": True, "child_rlimit_core": "unlimited"})
        sd = list(self.sd)
        if self.auto_renewals:
            # The Ack of each renewal, every second through each phase.
            for events in self.receivers:
                for phase in ReceiverRun("renewals", events).phases():
                    end = phase.end_realtime_ns or max(e["realtime_ns"] for e in events)
                    at = phase.start_realtime_ns + S
                    while at < end:
                        sd.append(SdMessage(at, HOST, 30490, GUEST, 30490, 50_000 + len(sd), True, True,
                                            [SdEntry(7, "SubscribeEventgroupAck", 0x4DEE, 1, 1, 3, 1, None, [])]))
                        at += S
            sd.sort(key=lambda message: message.ts_ns)
        capture = CaptureAnalysis(len(self.link), sd, 0, [stream] + closed)
        for index, events in enumerate(self.receivers):
            name = f"receiver-{index + 1}"
            if name in timeline["processes"]:
                continue
            killed = not any(e.get("event") == "final_status" for e in events)
            timeline["processes"][name] = {"returncode": -9 if killed else 0}
            timeline["events"].append({"what": f"stop {name}", "signal": "SIGKILL" if killed else "SIGTERM",
                                       "realtime_ns": events[-1]["realtime_ns"]})
        sources = [SourceFrame(seq, self.produced(seq), len(data) - 4, hashlib.sha256(data).hexdigest(), 1)
                   for seq, data in self.payloads.items()]
        source_stream = b"".join(self.payloads[seq] for seq in sorted(self.payloads))
        recorder_stream = b"".join(self.payloads[f.sequence] for f in self.recorded)
        return CaseRecords(
            case="test", timeline=timeline, source_frames=sources,
            recorder_frames=list(self.recorded), recorder_connections=list(self.connections),
            receivers=[ReceiverRun(f"receiver-{i + 1}.log", e) for i, e in enumerate(receivers)],
            capture=capture, gatewayd_logs=dict(self.gatewayd), shared_memory=copy.deepcopy(self.shm),
            source_stream=source_stream, recorder_stream=recorder_stream)


# --------------------------------------------------------------------------- identity


def identity_builder() -> Builder:
    builder = Builder(200)
    events = builder.receiver()
    builder.connect_client(events, T0 + 500 * MS, starts_phase=False)
    builder.ack(T0 + 700 * MS)
    builder.phase_start(events, "subscription_acknowledged", T0 + 700 * MS)
    for seq in range(1, 201):
        builder.arrive(events, seq, "delivered")
    builder.final(events, T0 + 30 * S)
    return builder


def test_identity_passes_with_200_identical_frames():
    result = evaluate_identity(identity_builder().records())
    assert result["outcome"] == PASS, result["reasons"]
    assert result["metrics"]["frames_byte_identical"] == 200
    assert result["metrics"]["largest_frames"] > 0
    assert result["metrics"]["phases"] == [{"run": "receiver-1.log", "phase": 1, "cause": "subscription_acknowledged",
                                            "start_s": 0.7, "end_cause": None}]


def test_identity_fails_when_one_byte_differs_at_the_client():
    records = identity_builder().records()
    records.recorder_frames[50].sha256 = "0" * 64
    result = evaluate_identity(records)
    assert result["outcome"] == FAIL
    assert not result["checks"]["all_frames_byte_identical_in_order"]


def test_identity_fails_when_a_frame_is_missing():
    builder = Builder(200)
    events = builder.receiver()
    builder.connect_client(events, T0 + 500 * MS, starts_phase=False)
    builder.phase_start(events, "subscription_acknowledged", T0 + 700 * MS)
    for seq in range(1, 201):
        if seq != 77:
            builder.arrive(events, seq, "delivered")
    builder.final(events, T0 + 30 * S)
    result = evaluate_identity(builder.records())
    assert result["outcome"] == FAIL
    assert not result["checks"]["link_carries_every_frame_in_order"]


def test_identity_fails_on_a_gatewayd_subscribe_failure():
    builder = identity_builder()
    builder.gatewayd["gatewayd.log"] += "[gatewayd] Failed to subscribe to de4sdv/aebs_signal_frame\n"
    result = evaluate_identity(builder.records())
    assert result["outcome"] == FAIL
    assert not result["checks"]["gatewayd_subscribed:gatewayd.log"]


@pytest.mark.parametrize("pair", ["adapter-gatewayd", "gatewayd-someipd"])
def test_identity_fails_without_shared_lola_memory(pair):
    builder = identity_builder()
    builder.shm["shared_pairs"][pair] = []
    assert evaluate_identity(builder.records())["outcome"] == FAIL


def test_identity_fails_when_lola_files_belong_to_another_user():
    builder = identity_builder()
    builder.shm["foreign_owned_files"] = ["/dev/shm/lola-ctl-7310-1"]
    assert evaluate_identity(builder.records())["outcome"] == FAIL


def test_identity_fails_when_the_final_status_does_not_balance():
    records = identity_builder().records()
    records.receivers[0].events[-1]["frames_received"] = 201
    result = evaluate_identity(records)
    assert result["outcome"] == FAIL
    assert not result["checks"]["receiver_balanced:receiver-1.log"]


def test_identity_fails_when_a_link_payload_is_not_from_the_source():
    records = identity_builder().records()
    records.capture.streams[0].messages[3].payload = b"\x05\x00\x00\x00\x08\x01\x18\x09\x00"
    result = evaluate_identity(records)
    assert result["outcome"] == FAIL
    assert not result["checks"]["link_payloads_from_source"]


def test_identity_needs_the_largest_frame():
    records = identity_builder().records()
    for frame in records.source_frames:
        if frame.size == 2044:
            frame.size = 2043  # as if the source never produced a frame of 2044 bytes
    assert not evaluate_identity(records)["checks"]["largest_frame_crossed"]


def test_a_delivered_frame_older_than_its_margin_fails():
    records = identity_builder().records()
    phase = next(e for e in records.receivers[0].events if e["event"] == "phase_start")
    phase["phase_start_realtime_ns"] = Builder.produced(150)
    result = evaluate_identity(records)
    assert not result["checks"]["delivered_not_older_than_phase:receiver-1.log"]


def test_a_frame_in_the_margin_is_reported_as_band():
    records = identity_builder().records()
    phase = next(e for e in records.receivers[0].events if e["event"] == "phase_start")
    phase["phase_start_realtime_ns"] = Builder.produced(1) + 15 * MS  # frame 1 lies 15 ms before the start
    result = evaluate_identity(records)
    assert result["checks"]["delivered_not_older_than_phase:receiver-1.log"]
    assert result["metrics"]["band_frames"] == 1


def test_a_frame_delivered_outside_a_phase_fails():
    records = identity_builder().records()
    events = records.receivers[0].events
    events.insert(-1, {"event": "phase_end", "monotonic_ns": Builder.produced(100) - T0,
                       "realtime_ns": Builder.produced(100), "cause": "client_lost"})
    result = evaluate_identity(records)
    assert not result["checks"]["delivered_in_a_phase:receiver-1.log"]


def test_a_copy_served_twice_in_one_phase_fails():
    builder = identity_builder()
    events = builder.receivers[0]
    del events[-1]  # the final status is written again below
    builder.arrive(events, 150, "delivered", at=Builder.produced(200) + 50 * MS)
    builder.final(events, T0 + 31 * S)
    result = evaluate_identity(builder.records())
    assert not result["checks"]["no_copy_served_in_phase:receiver-1.log"]
    assert not result["checks"]["no_duplicate_outside_the_band"]


def test_load_case_reads_the_files_of_the_runner(tmp_path):
    builder = identity_builder()
    case = tmp_path / "identity"
    case.mkdir()
    (case / "timeline.json").write_text(json.dumps({"case": "identity", "receiver_logs": ["receiver-1.log"],
                                                    "gatewayd_logs": ["gatewayd.log"], "disturbances": []}))
    with open(case / "source.jsonl", "w") as handle:
        for seq, data in builder.payloads.items():
            handle.write(json.dumps({"event": "sent", "seq": seq, "frame_timestamp_ns": builder.produced(seq),
                                     "size": len(data) - 4, "payload_sha256": hashlib.sha256(data).hexdigest(),
                                     "connection": 1}) + "\n")
    with open(case / "recorder.jsonl", "w") as handle:
        handle.write(json.dumps({"event": "connected", "connection": 1, "realtime_ns": T0}) + "\n")
        for frame in builder.recorded:
            handle.write(json.dumps({"event": "frame", "connection": 1, "receipt_realtime_ns": frame.receipt_realtime_ns,
                                     "payload_bytes": frame.payload_bytes, "prefix_ok": True,
                                     "sequence": frame.sequence, "frame_timestamp_ns": frame.frame_timestamp_ns,
                                     "payload_sha256": frame.sha256}) + "\n")
    (case / "receiver-1.log").write_text("\n".join(json.dumps(e) for e in builder.receivers[0]) + "\nnot json\n")
    (case / "gatewayd.log").write_text("[gatewayd] Failed to subscribe\n")
    (case / "source-stream-1.bin").write_bytes(b"\x01\x02")
    records = load_case(case)
    assert len(records.source_frames) == 200 and len(records.recorder_frames) == 200
    assert records.recorder_connections[0].connect_realtime_ns == T0
    assert records.receivers[0].start["phase_start_margin_ns"] == MARGIN
    assert len(records.receivers[0].phases()) == 1
    assert "Failed to subscribe" in records.gatewayd_logs["gatewayd.log"]
    assert records.capture is None and records.source_stream == b"\x01\x02"


def test_identity_reports_the_receipt_time_less_the_frame_stamp():
    result = evaluate_identity(identity_builder().records())
    assert result["metrics"]["receipt_minus_frame_ms"] == {"min": 2.0, "max": 2.0}
    assert result["metrics"]["clock_steps"] == 0


def test_a_clock_step_voids_the_case():
    builder = identity_builder()
    events = builder.receivers[0]
    events.insert(len(events) - 1, {"event": "clock_step", "monotonic_ns": 9 * S, "realtime_ns": T0 + 9 * S,
                                    "step_ns": 5 * MS, "in_phase": True})
    result = evaluate_identity(builder.records())
    assert result["outcome"] == MISSING
    assert not result["checks"]["no_clock_step:receiver-1.log"]


def test_a_receiver_run_must_trigger_the_ingress_after_it_listens():
    builder = identity_builder()
    events = builder.receivers[0]
    builder.receivers[0] = [e for e in events if e["event"] not in ("property_not_announced", "ingress_trigger")]
    result = evaluate_identity(builder.records())
    assert result["outcome"] == FAIL
    assert not result["checks"]["ingress_triggers_after_listen:receiver-1.log"]


def test_the_ingress_trigger_comes_after_the_start_record_and_in_order():
    builder = identity_builder()
    events = builder.receivers[0]
    properties = [e for e in events if e["event"] == "property_not_announced"]
    rest = [e for e in events if e["event"] != "property_not_announced"]
    builder.receivers[0] = properties[:1] + rest[:1] + properties[1:] + rest[1:]
    assert evaluate_identity(builder.records())["outcome"] == FAIL
    builder.receivers[0] = rest[:1] + [properties[0], properties[2], properties[1]] + rest[1:]
    assert evaluate_identity(builder.records())["outcome"] == FAIL


def test_a_failed_property_set_does_not_count():
    builder = identity_builder()
    for event in builder.receivers[0]:
        if event["event"] == "property_not_announced":
            event.update(event="property_announced", ok=event["value"] != "1")
    assert evaluate_identity(builder.records())["outcome"] == FAIL


def test_a_failed_ingress_trigger_fails():
    builder = identity_builder()
    next(e for e in builder.receivers[0] if e["event"] == "ingress_trigger")["ok"] = False
    assert evaluate_identity(builder.records())["outcome"] == FAIL


def trigger_builder(*, repeats: int = 2, gap_s: float = 1.0, after_client: bool = False,
                    gave_up_after: int | None = None) -> Builder:
    """A receiver run that repeats the ingress trigger until its first client connects."""
    builder = Builder(200)
    events = builder.receiver()
    at = T0 + 2000
    for _ in range(repeats):
        at += int(gap_s * S)
        builder.trigger(events, at, "no_first_client")
    if gave_up_after is not None:
        builder.event(events, "ingress_trigger_gave_up", at + S, tries=1 + gave_up_after)
    builder.ack(at + 100 * MS)
    builder.event(events, "subscribed", at + 100 * MS)
    builder.connect_client(events, at + 300 * MS, starts_phase=True)
    builder.phase_end(events, "client_lost", at + 5 * S)
    builder.event(events, "client_lost", at + 5 * S)
    if after_client:
        builder.trigger(events, at + 6 * S, "no_first_client")
    builder.final(events, at + 20 * S)
    builder.timeline["stop_realtime_ns"] = at + 21 * S
    return builder


def test_repeats_until_the_first_client_pass():
    result = evaluate_identity(trigger_builder().records())
    assert result["checks"]["ingress_trigger_rule:receiver-1.log"]
    assert result["checks"]["ingress_triggers_after_listen:receiver-1.log"]


def test_no_trigger_after_the_first_client():
    result = evaluate_identity(trigger_builder(after_client=True).records())
    assert not result["checks"]["ingress_trigger_rule:receiver-1.log"]


@pytest.mark.parametrize("gap_s", [0.5, 1.6])
def test_repeats_are_one_second_apart(gap_s):
    result = evaluate_identity(trigger_builder(gap_s=gap_s).records())
    assert not result["checks"]["ingress_trigger_rule:receiver-1.log"]


def test_at_most_ten_repeats():
    assert evaluate_identity(trigger_builder(repeats=10).records())["checks"]["ingress_trigger_rule:receiver-1.log"]
    assert not evaluate_identity(trigger_builder(repeats=11).records())["checks"]["ingress_trigger_rule:receiver-1.log"]


def test_the_give_up_comes_after_ten_repeats_only():
    builder = trigger_builder(repeats=5, gave_up_after=5)
    assert not evaluate_identity(builder.records())["checks"]["ingress_trigger_rule:receiver-1.log"]


# ------------------------------------------------- rule constants, receiver end, cores, phases (mutations)


def test_the_evaluator_uses_its_own_margin():
    """A start record that claims a margin of 20 s does not let a frame 14.9 s old pass."""
    builder = identity_builder()
    builder.receivers[0][0]["phase_start_margin_ns"] = 20 * S
    phase_start = next(e for e in builder.receivers[0] if e["event"] == "phase_start")["phase_start_realtime_ns"]
    first = next(e for e in builder.receivers[0] if e["event"] == "frame")
    first["frame_timestamp_ns"] = phase_start - int(14.9 * S)
    result = evaluate_identity(builder.records())
    assert result["outcome"] == FAIL
    assert not result["checks"]["rule_constants:receiver-1.log"]
    assert not result["checks"]["delivered_not_older_than_phase:receiver-1.log"]


def test_the_start_record_must_give_the_copy_memory_of_the_rule():
    builder = identity_builder()
    builder.receivers[0][0]["copy_memory_frames"] = 10
    assert not evaluate_identity(builder.records())["checks"]["rule_constants:receiver-1.log"]


def test_a_receiver_that_crashed_fails():
    """No final status and returncode -11 after a planned SIGTERM: the receiver crashed."""
    builder = identity_builder()
    builder.receivers[0] = [e for e in builder.receivers[0] if e["event"] != "final_status"]
    builder.timeline["processes"] = {"receiver-1": {"returncode": -11}}
    builder.timeline["events"] = [{"what": "stop receiver-1", "signal": "SIGTERM", "realtime_ns": T0 + 30 * S}]
    result = evaluate_identity(builder.records())
    assert result["outcome"] == FAIL
    assert not result["checks"]["receiver_end:receiver-1.log"]


@pytest.mark.parametrize("returncode, final", [(1, True), (0, False)])
def test_a_sigterm_stop_needs_exit_zero_and_a_final_status(returncode, final):
    builder = identity_builder()
    if not final:
        builder.receivers[0] = [e for e in builder.receivers[0] if e["event"] != "final_status"]
    builder.timeline["processes"] = {"receiver-1": {"returncode": returncode}}
    builder.timeline["events"] = [{"what": "stop receiver-1", "signal": "SIGTERM", "realtime_ns": T0 + 30 * S}]
    assert not evaluate_identity(builder.records())["checks"]["receiver_end:receiver-1.log"]


def test_a_receiver_without_a_planned_stop_fails():
    builder = identity_builder()
    builder.timeline["processes"] = {"receiver-1": {"returncode": 0}}
    builder.timeline["events"] = []
    assert not evaluate_identity(builder.records())["checks"]["receiver_end:receiver-1.log"]


def test_a_missing_final_status_is_accepted_after_a_planned_sigkill():
    result = evaluate_resubscribe(resubscribe_builder().records())
    assert result["checks"]["receiver_end:receiver-2.log"]
    builder = resubscribe_builder()
    builder.timeline["processes"] = {"receiver-2": {"returncode": -11}}
    builder.timeline["events"] = [{"what": "stop receiver-2", "signal": "SIGKILL", "realtime_ns": T0}]
    assert not evaluate_resubscribe(builder.records())["checks"]["receiver_end:receiver-2.log"]


def test_a_receiver_core_fails_the_case():
    builder = identity_builder()
    builder.timeline["cores"] = [{"process": "receiver-1", "core": "core.de4sdv_someip_r.4242", "returncode": 0}]
    result = evaluate_identity(builder.records())
    assert result["outcome"] == FAIL
    assert not result["checks"]["no_receiver_core"]


GAP_MW_041_FRAMES = [  # the crashing thread of gatewayd's abort at its stop, as the CI cores give it
    "pthread_kill in libc.so.6", "raise in libc.so.6", "abort in libc.so.6",
    "score::cpp::detail::assertion_failed in gatewayd",
    "score::mw::com::impl::lola::TransactionLogSet::TransactionLogNode::Reset in gatewayd",
    "score::cpp::move_only_function<void (), 32ul, 16ul>::wrapper<...>::invoke in gatewayd",
    "score::mw::com::impl::lola::SubscriptionStateMachine::~SubscriptionStateMachine in gatewayd",
    "score::mw::com::impl::lola::ProxyEvent::~ProxyEvent in gatewayd",
    "score::mw::com::impl::ProxyEventBase::~ProxyEventBase in gatewayd",
    "score::someip_gateway::gatewayd::LocalServiceInstance::~LocalServiceInstance in gatewayd",
    "main in gatewayd"]


def gatewayd_core(builder: Builder, frames: list[str], signal_name: str = "SIGTERM", returncode: int = -6,
                  exit_s: float = 29.05) -> None:
    """A core of gatewayd and the runner's records of its planned stop at 29 s and its exit."""
    builder.timeline["cores"] = [{"process": "gatewayd", "core": "core.gatewayd.5914", "returncode": returncode,
                                  "named_top_frames": frames[:12], "named_frames": frames}]
    builder.timeline["events"] = [{"what": "stop gatewayd", "signal": signal_name, "monotonic_ns": 29 * S,
                                   "realtime_ns": T0 + 29 * S}]
    builder.timeline["processes"] = {"gatewayd": {"returncode": returncode, "exit_monotonic_ns": int(exit_s * S)}}


def test_the_gatewayd_abort_is_recorded_with_its_frames():
    builder = identity_builder()
    gatewayd_core(builder, GAP_MW_041_FRAMES)
    result = evaluate_identity(builder.records())
    assert result["outcome"] == PASS, result["reasons"]
    assert result["metrics"]["process_cores"] == [{"process": "gatewayd", "returncode": -6,
                                                   "core": "core.gatewayd.5914", "top_frames": GAP_MW_041_FRAMES[:6],
                                                   "known": "GAP-MW-041"}]


@pytest.mark.parametrize("frames, signal_name, returncode", [
    (["abort in libc.so.6", "score::cpp::detail::assertion_failed in gatewayd",
      "score::someip_gateway::gatewayd::SomethingElse::OnSample in gatewayd"], "SIGTERM", -6),  # other frames
    (GAP_MW_041_FRAMES[:5], "SIGTERM", -6),  # Reset, but not under ~ProxyEvent or ~LocalServiceInstance
    (GAP_MW_041_FRAMES, "SIGKILL", -6),  # the signature, but not at the end that follows a planned SIGTERM
    (GAP_MW_041_FRAMES, "SIGTERM", -11),  # the signature with another signal
])
def test_a_core_that_is_not_the_known_gatewayd_abort_fails(frames, signal_name, returncode):
    builder = identity_builder()
    gatewayd_core(builder, frames, signal_name, returncode)
    result = evaluate_identity(builder.records())
    assert result["outcome"] == FAIL
    assert not result["checks"]["only_known_cores"]
    assert result["metrics"]["process_cores"][0]["known"] is None


def test_the_known_abort_must_follow_the_planned_stop():
    """The reviewer's D7c case: the signature, but the abort 15 s before the planned SIGTERM."""
    builder = identity_builder()
    gatewayd_core(builder, GAP_MW_041_FRAMES, exit_s=15.0)
    result = evaluate_identity(builder.records())
    assert result["outcome"] == FAIL
    assert not result["checks"]["only_known_cores"]
    assert result["metrics"]["process_cores"][0]["known"] is None


def test_a_case_needs_the_core_scan():
    builder = identity_builder()
    records = builder.records()
    del records.timeline["cores"]
    assert evaluate_identity(records)["outcome"] == ERROR


def test_a_phase_start_400_ms_before_its_ack_fails():
    builder = identity_builder()
    start = next(e for e in builder.receivers[0] if e["event"] == "phase_start")
    start["phase_start_realtime_ns"] -= 400 * MS
    start["realtime_ns"] -= 400 * MS
    result = evaluate_identity(builder.records())
    assert result["outcome"] == FAIL
    assert not result["checks"]["phase_starts_independent:receiver-1.log"]


def test_a_phase_start_long_after_its_cause_fails():
    builder = identity_builder()
    ack = next(m for m in builder.sd if m.src == HOST and m.entries[0].type_name == "SubscribeEventgroupAck")
    ack.ts_ns -= 150 * MS  # the Ack came 150 ms before the phase start
    assert not evaluate_identity(builder.records())["checks"]["phase_starts_independent:receiver-1.log"]


def test_a_phase_start_must_name_its_cause():
    builder = identity_builder()  # client at 500 ms, Ack at 700 ms
    next(e for e in builder.receivers[0] if e["event"] == "phase_start")["cause"] = "client_connected"
    assert not evaluate_identity(builder.records())["checks"]["phase_starts_independent:receiver-1.log"]


def test_a_phase_start_needs_an_ack_inside_its_ttl():
    builder = trigger_builder()
    for message in builder.sd:
        if message.src == HOST:
            message.ts_ns -= 4 * S
    assert not evaluate_identity(builder.records())["checks"]["phase_starts_independent:receiver-1.log"]


@pytest.mark.parametrize("cause", ["subscription_lost:stopped", "subscription_lost:tcp_closed", "client_lost"])
def test_a_phase_end_needs_its_independent_event(cause):
    builder = resubscribe_builder() if cause != "client_lost" else trigger_builder()
    if cause == "subscription_lost:stopped":
        builder.sd = [m for m in builder.sd if not (m.src == GUEST and m.entries[0].ttl == 0)]
    elif cause == "subscription_lost:tcp_closed":
        builder.tcp_ends = []
    else:
        builder.connections[-1].close_realtime_ns = None
    result = (evaluate_resubscribe if cause != "client_lost" else evaluate_identity)(builder.records())
    assert not all(v for k, v in result["checks"].items() if k.startswith("phase_ends_independent"))


def test_a_ttl_end_comes_one_ttl_after_the_last_ack():
    builder = ttl_builder(seconds=6)
    events = builder.receivers[0]
    last_ack = max(m.ts_ns for m in builder.sd if m.src == HOST and m.entries[0].ttl > 0)
    final = events.pop()
    builder.phase_end(events, "subscription_lost:ttl_expired", last_ack + 3 * S + MS)
    events.append(final)
    assert evaluate_ttl_renewal(builder.records())["checks"]["phase_ends_independent:receiver-1.log"]
    builder = ttl_builder(seconds=6)
    events = builder.receivers[0]
    final = events.pop()
    builder.phase_end(events, "subscription_lost:ttl_expired", last_ack + 1 * S)
    events.append(final)
    assert not evaluate_ttl_renewal(builder.records())["checks"]["phase_ends_independent:receiver-1.log"]


# ------------------------------------------------ delta review: D1, D2, D3, D5, D6, D8 (mutations)


def late_start_no_client(late_ms: int = 0, early_ms: int = 0) -> Builder:
    """no_client with the receiver's phase start late_ms after the client's connect, or early_ms before its
    pre-connect stamp; frames received before the logged start are dropped as no_client."""
    builder = Builder(120)
    events = builder.receiver()
    for k in range(7):  # subscribed at 500 ms, renewed every second
        builder.ack(T0 + 500 * MS + k * S)
    builder.event(events, "subscribed", T0 + 500 * MS)
    connect = builder.produced(50) + 50 * MS
    builder.connections.append(RecorderConnection(1, connect, None, pre_connect_realtime_ns=connect - 100_000))
    start = connect + late_ms * MS - early_ms * MS
    for seq in range(1, 121):
        if builder.produced(seq) + 2 * MS < start:
            builder.arrive(events, seq, "no_client")
    builder.event(events, "client_connected", start)
    builder.event(events, "phase_start", start, cause="client_connected", phase_start_realtime_ns=start)
    for seq in range(1, 121):
        if builder.produced(seq) + 2 * MS >= start:
            builder.arrive(events, seq, "delivered")
    builder.final(events, T0 + 20 * S)
    return builder


def test_a_frame_dropped_outside_a_phase_after_the_independent_start_fails():
    result = evaluate_no_client(late_start_no_client(late_ms=90).records())
    assert result["outcome"] == FAIL
    assert not result["checks"]["drops_against_independent_starts:receiver-1.log"]
    assert not result["checks"]["phase_starts_independent:receiver-1.log"]  # 90 ms after I: above 10 ms


def test_a_phase_start_more_than_10_ms_after_its_cause_fails():
    result = evaluate_no_client(late_start_no_client(late_ms=11).records())
    assert not result["checks"]["phase_starts_independent:receiver-1.log"]
    assert evaluate_no_client(late_start_no_client(late_ms=5).records())["outcome"] == PASS


def test_a_frame_dropped_as_older_although_it_is_not_older_than_the_independent_start_fails():
    builder = identity_builder()  # Ack at 700 ms: I = 700 ms
    events = builder.receivers[0]
    frame = next(e for e in events if e["event"] == "frame" and e["frame_timestamp_ns"] > T0 + 700 * MS)
    frame["verdict"] = "older_than_phase"
    builder.recorded = [f for f in builder.recorded if f.sequence != frame["sequence"]]
    final = next(e for e in events if e["event"] == "final_status")
    final["frames_delivered"] -= 1
    final["drop_older_than_phase"] += 1
    result = evaluate_identity(builder.records())
    assert not result["checks"]["drops_against_independent_starts:receiver-1.log"]


def test_a_phase_start_before_the_pre_connect_stamp_fails():
    """The reviewer's D2 case: the receiver logs its start 45 ms before the client's stamp."""
    result = evaluate_no_client(late_start_no_client(early_ms=45).records())
    assert result["outcome"] == FAIL
    assert not result["checks"]["phase_starts_independent:receiver-1.log"]


def test_the_cause_tie_is_the_stamp_interval_and_1_ms():
    builder = identity_builder()  # client connect at 500 ms (pre 499.9 ms), Ack at 700 ms
    ack = next(m for m in builder.sd if m.src == HOST and m.entries[0].type_name == "SubscribeEventgroupAck")
    start = next(e for e in builder.receivers[0] if e["event"] == "phase_start")
    for event in (start,):
        event["cause"] = "client_connected"
    ack.ts_ns = T0 + 500 * MS + 900_000  # inside the stamp interval plus 1 ms: either cause
    start["phase_start_realtime_ns"] = start["realtime_ns"] = T0 + 500 * MS + 950_000
    assert evaluate_identity(builder.records())["checks"]["phase_starts_independent:receiver-1.log"]
    ack.ts_ns = T0 + 500 * MS + 5 * MS  # 5 ms after the connect: the Ack is the cause
    start["phase_start_realtime_ns"] = start["realtime_ns"] = T0 + 500 * MS + 5 * MS + 50_000
    assert not evaluate_identity(builder.records())["checks"]["phase_starts_independent:receiver-1.log"]


def test_a_tcp_end_needs_a_fin_or_rst_of_someipd():
    """The reviewer's D3 case: only the receiver's own FIN, 50 us after its tcp_closed end."""
    builder = resubscribe_builder()
    records = builder.records()
    ends = [e["realtime_ns"] for e in records.receivers[-1].events
            if e.get("event") == "phase_end" and e.get("cause") == "subscription_lost:tcp_closed"]
    assert evaluate_resubscribe(records)["outcome"] == PASS
    records.capture.streams = [s for s in records.capture.streams if not s.fin] + [
        TcpStream(90 + i, GUEST, 40000, HOST, 30509, fin=True, fin_ts_ns=end + 50_000) for i, end in enumerate(ends)]
    assert not all(v for k, v in evaluate_resubscribe(records)["checks"].items()
                   if k.startswith("phase_ends_independent"))
    builder = resubscribe_builder()
    builder.tcp_ends = [stamp + 2 * MS + 10_000 for stamp in builder.tcp_ends]  # someipd's FIN 2 ms after the end
    assert not all(v for k, v in evaluate_resubscribe(builder.records())["checks"].items()
                   if k.startswith("phase_ends_independent"))


def phase_across_the_fin() -> Builder:
    """The reviewer's D5 case: receiver-3 goes on across someipd's FIN at the gateway pair restart."""
    builder = resubscribe_builder()
    events = builder.receivers[-1]
    end = next(i for i, e in enumerate(events) if e.get("event") == "phase_end"
               and e.get("cause") == "subscription_lost:tcp_closed")
    next_start = next(i for i, e in enumerate(events) if i > end and e.get("event") == "phase_start")
    del events[next_start]
    del events[end]
    return builder


def test_a_phase_that_goes_on_after_someipds_fin_fails():
    result = evaluate_resubscribe(phase_across_the_fin().records())
    assert result["outcome"] == FAIL
    assert not result["checks"]["leave_records_end_their_phase:receiver-3.log"]


def test_a_receiver_without_its_tcp_connected_record_gives_an_error():
    """The reviewer's D5b case: no tcp_connected record names the current connection."""
    builder = phase_across_the_fin()
    builder.log_tcp_connected = False
    result = evaluate_resubscribe(builder.records())
    assert result["outcome"] == ERROR
    assert not result["checks"]["receiver_logs_its_connection:receiver-3.log"]


def test_a_receiver_that_names_another_connection_fails():
    """The reviewer's D5c case: the receiver's tcp_connected names a port the capture does not set up."""
    builder = resubscribe_builder()
    records = builder.records()
    connected = [e for e in records.receivers[-1].events if e.get("event") == "tcp_connected"]
    connected[0]["local"] = f"{GUEST}:49999"
    result = evaluate_resubscribe(records)
    assert result["outcome"] == FAIL
    assert not result["checks"]["phase_starts_independent:receiver-3.log"]


def test_a_phase_start_on_a_renewal_ack_fails():
    """The reviewer's D10 case: the receiver ignores the first Ack and starts on the third, 2 s later."""
    builder = ttl_builder()
    events = builder.receivers[0]
    late = T0 + 2500 * MS
    for event in events:
        if event.get("event") in ("subscribed", "phase_start"):
            event["realtime_ns"], event["monotonic_ns"] = late, late - T0
            if event.get("event") == "phase_start":
                event["phase_start_realtime_ns"] = late
    lost = [e for e in events if e.get("event") == "frame" and e["realtime_ns"] < late]
    for event in lost:
        event["verdict"] = "not_subscribed"
    builder.recorded = [f for f in builder.recorded if f.sequence not in {e["sequence"] for e in lost}]
    final = next(e for e in events if e.get("event") == "final_status")
    final["frames_delivered"] -= len(lost)
    final["drop_not_subscribed"] = final.get("drop_not_subscribed", 0) + len(lost)
    events.sort(key=lambda e: e["realtime_ns"])
    result = evaluate_ttl_renewal(builder.records())
    assert result["outcome"] == FAIL
    assert not result["checks"]["phase_starts_independent:receiver-1.log"]
    assert not result["checks"]["drops_against_independent_starts:receiver-1.log"]


@pytest.mark.parametrize("reason", ["length_prefix_mismatch", "malformed_notification", "field_not_positive",
                                    "copy_in_phase"])
def test_a_valid_frame_dropped_for_its_content_or_as_a_copy_fails(reason):
    """The reviewer's D11 cases: a well-formed frame on the link, dropped 200 ms into a phase."""
    builder = resubscribe_builder()
    events = builder.receivers[-1]
    start = next(e for e in events if e.get("event") == "phase_start")
    frame = next(e for e in events if e.get("event") == "frame" and e.get("verdict") == "delivered"
                 and e["realtime_ns"] > start["realtime_ns"] + 200 * MS)
    frame["verdict"] = reason
    builder.recorded = [f for f in builder.recorded if f.sequence != frame["sequence"]]
    final = next(e for e in events if e.get("event") == "final_status")
    final["frames_delivered"] -= 1
    final[f"drop_{reason}"] = final.get(f"drop_{reason}", 0) + 1
    result = evaluate_resubscribe(builder.records())
    assert result["outcome"] == FAIL
    name = "copies_repeat_a_served_frame" if reason == "copy_in_phase" else "content_drops_malformed_on_link"
    assert not result["checks"][f"{name}:receiver-3.log"]


def test_a_malformed_frame_on_the_link_may_be_dropped_for_its_content():
    builder = resubscribe_builder()
    events = builder.receivers[-1]
    start = next(e for e in events if e.get("event") == "phase_start")
    frame = next(e for e in events if e.get("event") == "frame" and e.get("verdict") == "delivered"
                 and e["realtime_ns"] > start["realtime_ns"] + 200 * MS)
    frame["verdict"] = "length_prefix_mismatch"
    builder.recorded = [f for f in builder.recorded if f.sequence != frame["sequence"]]
    message = next(m for m in builder.link if m.session == frame["sequence"] & 0xFFFF)
    message.payload = b"\xff\x00\x00\x00" + message.payload[4:]  # the prefix no longer counts the frame
    final = next(e for e in events if e.get("event") == "final_status")
    final["frames_delivered"] -= 1
    final["drop_length_prefix_mismatch"] += 1
    assert evaluate_resubscribe(builder.records())["checks"]["content_drops_malformed_on_link:receiver-3.log"]


@pytest.mark.parametrize("connect_ms", [1.2, 5.0])
def test_a_frame_during_the_clients_connect_may_be_dropped(connect_ms):
    """The reviewer's D12 case: frame 51 arrives 2 ms before the accept, while connect() is under way."""
    builder = Builder(120)
    events = builder.receiver()
    builder.auto_renewals = False
    for k in range(20):
        builder.ack(T0 + 500 * MS + k * S + 300_000)
    builder.event(events, "subscribed", T0 + 500 * MS)
    accept = builder.produced(51) + 4 * MS
    for seq in range(1, 52):
        builder.arrive(events, seq, "no_client")
    builder.connections.append(RecorderConnection(1, accept + 20_000, None,
                                                  pre_connect_realtime_ns=accept - int(connect_ms * MS)))
    builder.event(events, "client_connected", accept)
    builder.event(events, "phase_start", accept, cause="client_connected", phase_start_realtime_ns=accept)
    for seq in range(52, 121):
        builder.arrive(events, seq, "delivered")
    builder.final(events, T0 + 20 * S)
    result = evaluate_no_client(builder.records())
    assert result["outcome"] == PASS, result["reasons"]


@pytest.mark.parametrize("shift_ms", [0, 5, 15, 19, -5, -9, -11, -15, -19])
def test_two_clocks_accept_an_offset_inside_their_bound(shift_ms):
    """The reviewer's D4 case on the builder: the capture moved by an offset, a bound of 19 ms and 1 ms transit."""
    for builder, evaluate in ((identity_builder(), evaluate_identity), (resubscribe_builder(), evaluate_resubscribe),
                              (ingress_builder(), evaluate_ingress_start)):
        builder.timeline["parameters"] = {"one_clock": False, "clock_offset_bound_ns": 19 * MS,
                                          "transit_bound_ns": MS}
        records = ingress_records(builder) if evaluate is evaluate_ingress_start else builder.records()
        shift = shift_ms * MS
        for message in records.capture.sd_messages:
            message.ts_ns += shift
        for stream in records.capture.streams:
            stream.fin_ts_ns = None if stream.fin_ts_ns is None else stream.fin_ts_ns + shift
            stream.first_ts_ns = None if stream.first_ts_ns is None else stream.first_ts_ns + shift
            for message in stream.messages:
                message.ts_ns += shift
        result = evaluate(records)
        assert result["outcome"] == PASS, (evaluate.__name__, result["reasons"][:3])


@pytest.mark.parametrize("what", ["nack", "stop_offer", "client_end", "ack_gap"])
def test_a_leave_record_inside_a_phase_needs_its_end(what):
    builder = identity_builder()  # one phase from 700 ms to the end of the run at 30 s
    at = T0 + 10 * S
    if what == "nack":
        builder.sd.append(SdMessage(at, HOST, 30490, GUEST, 30490, 9000, True, True,
                                    [SdEntry(7, "SubscribeEventgroupAck", 0x4DEE, 1, 1, 0, 1, None, [])]))
    elif what == "stop_offer":
        builder.sd.append(SdMessage(at, HOST, 30490, "224.244.224.245", 30490, 9000, True, False,
                                    [SdEntry(1, "OfferService", 0x4DEE, 1, 1, 0, None, 0, [])]))
    elif what == "client_end":
        builder.connections[0].close_realtime_ns = at
    else:
        builder.auto_renewals = False  # one Ack at 700 ms, then none for 29 s
    result = evaluate_identity(builder.records())
    assert result["outcome"] == FAIL
    assert not result["checks"]["leave_records_end_their_phase:receiver-1.log"]


def test_the_core_scan_must_cover_the_kernel_core_pattern():
    builder = identity_builder()
    builder.timeline["core_scan"] = {"core_pattern": "|/usr/share/apport/apport %p", "core_dir": "/runner/cores",
                                     "pattern_in_core_dir": False, "child_rlimit_core": "unlimited"}
    result = evaluate_identity(builder.records())
    assert result["outcome"] == ERROR
    assert not result["checks"]["core_pattern_in_core_dir"]
    builder.timeline["core_scan"] = {"core_pattern": "/runner/cores/core.%e.%p", "core_dir": "/runner/cores",
                                     "pattern_in_core_dir": True, "child_rlimit_core": "0"}
    assert not evaluate_identity(builder.records())["checks"]["child_core_limit"]


def test_a_run_on_two_clocks_needs_its_measured_bound():
    builder = identity_builder()
    builder.timeline["parameters"] = {"one_clock": False}
    result = evaluate_identity(builder.records())
    assert result["outcome"] == ERROR
    assert not result["checks"]["capture_clock_known"]
    builder.timeline["parameters"] = {"one_clock": False, "clock_offset_bound_ns": 3 * MS, "transit_bound_ns": MS}
    assert evaluate_identity(builder.records())["checks"]["capture_clock_known"]


def test_a_framing_loss_in_a_phase_fails_with_its_own_check():
    builder = trigger_builder()
    end = next(e for e in builder.receivers[0] if e["event"] == "phase_end")
    end["cause"] = "subscription_lost:stream_framing_lost"
    result = evaluate_identity(builder.records())
    assert not result["checks"]["no_framing_loss_in_a_phase:receiver-1.log"]
    assert any("loss of the SOME/IP framing" in reason for reason in result["reasons"])
    assert result["checks"]["phase_ends_independent:receiver-1.log"]


# --------------------------------------------------------------------------- resubscribe


def resubscribe_builder(*, missing_resubscribe: bool = False, killed_extra_frame: bool = False,
                        gap: bool = False) -> Builder:
    """Four disturbances, each window 8 s: disturbance at 3 s, phase again at 4 s."""
    builder = Builder(400)
    kinds = ["receiver_sigterm_restart", "receiver_sigkill_restart", "gateway_pair_restart", "link_outage"]
    seq = 1
    events = builder.receiver()
    builder.connect_client(events, T0 + 500 * MS, starts_phase=False)
    builder.ack(T0 + 600 * MS)
    builder.phase_start(events, "subscription_acknowledged", T0 + 600 * MS)
    window_start = T0
    for kind in kinds:
        disturbance_start = window_start + 3 * S
        recovery = window_start + 4 * S
        builder.timeline["disturbances"].append({"kind": kind, "start_realtime_ns": disturbance_start,
                                                 "end_realtime_ns": disturbance_start + 200 * MS,
                                                 "expects_resubscription": True})
        while builder.produced(seq) < disturbance_start:
            builder.arrive(events, seq, "delivered")
            seq += 1
        if kind.startswith("receiver_"):
            if kind == "receiver_sigterm_restart":
                builder.phase_end(events, "subscription_lost:stopped", disturbance_start)
                builder.final(events, disturbance_start)
            elif killed_extra_frame:
                builder.recorded.append(RecordedFrame(len(builder.connections), disturbance_start, 10, True, seq,
                                                      builder.produced(seq),
                                                      hashlib.sha256(builder.payloads[seq]).hexdigest()))
                seq += 1
            events = builder.receiver(at=disturbance_start + 100 * MS)
            builder.connect_client(events, recovery - 300 * MS, starts_phase=False)
        else:
            builder.phase_end(events, "subscription_lost:tcp_closed", disturbance_start)
        while builder.produced(seq) < recovery:
            verdict = "not_subscribed" if kind.startswith("receiver_") else "older_than_phase"
            builder.arrive(events, seq, verdict, at=None if kind.startswith("receiver_") else recovery + 1 * MS)
            seq += 1
        if not (missing_resubscribe and kind == "link_outage"):
            builder.ack(recovery)
            builder.phase_start(events, "subscription_acknowledged", recovery)
        window_start += 8 * S
        while builder.produced(seq) < window_start:
            if gap and kind == "link_outage" and recovery + 2 * S <= builder.produced(seq) < recovery + 2 * S + 100 * MS:
                seq += 1
                continue
            builder.arrive(events, seq, "not_subscribed" if missing_resubscribe and kind == "link_outage"
                           else "delivered")
            seq += 1
    builder.final(events, window_start)
    builder.timeline["stop_realtime_ns"] = window_start
    return builder


def test_resubscribe_passes_and_reports_each_window():
    result = evaluate_resubscribe(resubscribe_builder().records())
    assert result["outcome"] == PASS, result["reasons"]
    windows = {w["kind"]: w for w in result["metrics"]["windows"]}
    assert set(windows) == {"receiver_sigterm_restart", "receiver_sigkill_restart", "gateway_pair_restart",
                            "link_outage"}
    assert all(w["resubscribed_after_s"] is not None for w in windows.values())
    assert windows["gateway_pair_restart"]["drops_in_window"] == {"older_than_phase": 10}
    causes = [p["cause"] for p in result["metrics"]["phases"]]
    assert causes.count("subscription_acknowledged") == 5


def test_resubscribe_counts_a_subscription_that_comes_before_the_noted_end():
    builder = resubscribe_builder()
    for disturbance in builder.timeline["disturbances"]:
        disturbance["end_realtime_ns"] += 2 * S  # the runner noted the end after the new Ack
    result = evaluate_resubscribe(builder.records())
    assert result["outcome"] == PASS, result["reasons"]
    assert all(w["resubscribed_after_s"] < 0 for w in result["metrics"]["windows"])


def test_resubscribe_accepts_one_extra_frame_of_a_killed_receiver():
    result = evaluate_resubscribe(resubscribe_builder(killed_extra_frame=True).records())
    assert result["checks"]["client_frames_equal_deliveries"], result["reasons"]


def test_resubscribe_fails_without_a_new_subscription():
    result = evaluate_resubscribe(resubscribe_builder(missing_resubscribe=True).records())
    assert result["outcome"] == FAIL
    assert not result["checks"]["recovered:link_outage"]


def test_resubscribe_fails_on_a_gap_after_recovery():
    result = evaluate_resubscribe(resubscribe_builder(gap=True).records())
    assert not result["checks"]["no_gap_after_recovery:link_outage"]


def test_unknown_drop_reason_fails():
    records = resubscribe_builder().records()
    frame = next(e for e in records.receivers[0].events if e["event"] == "frame")
    frame["verdict"] = "lost_somewhere"
    assert evaluate_resubscribe(records)["outcome"] == FAIL


# --------------------------------------------------------------------------- no client


def no_client_builder(*, deliver_old: bool = False, queue: bool = False) -> Builder:
    builder = Builder(120)
    events = builder.receiver()
    builder.ack(T0 + 500 * MS)
    builder.event(events, "subscribed", T0 + 500 * MS)
    connect = builder.produced(50) + 50 * MS
    for seq in range(1, 51):
        builder.arrive(events, seq, "no_client")
    builder.connect_client(events, connect, starts_phase=True)
    if queue:
        builder.arrive(events, 50, "delivered", at=connect + 1 * MS)
    for seq in range(51, 121):
        builder.arrive(events, seq, "delivered")
    builder.final(events, T0 + 20 * S)
    if deliver_old:
        builder.recorded[0].frame_timestamp_ns = connect - 30 * MS
    return builder


def test_no_client_passes():
    result = evaluate_no_client(no_client_builder().records())
    assert result["outcome"] == PASS, result["reasons"]
    assert result["metrics"]["dropped_no_client"] == 50


def test_no_client_fails_when_a_frame_produced_before_the_margin_arrives():
    result = evaluate_no_client(no_client_builder(deliver_old=True).records())
    assert result["outcome"] == FAIL
    assert not result["checks"]["nothing_produced_before_the_margin_delivered"]


def test_no_client_fails_on_a_queued_frame():
    result = evaluate_no_client(no_client_builder(queue=True).records())
    assert result["outcome"] == FAIL
    assert not result["checks"]["no_queue"]


def test_no_client_needs_the_phase_to_start_with_the_client():
    records = no_client_builder().records()
    phase = next(e for e in records.receivers[0].events if e["event"] == "phase_start")
    phase["cause"] = "subscription_acknowledged"
    assert not evaluate_no_client(records)["checks"]["one_phase_started_by_the_client"]


# --------------------------------------------------------------------------- stored samples


def stored_builder(*, copies: int = 8, older: int = 9, deliver_copy: bool = False, none: bool = False) -> Builder:
    """A late gatewayd, then a gatewayd restart in the phase (copies), then a pair restart (older frames)."""
    builder = Builder(150)
    events = builder.receiver()
    builder.connect_client(events, T0 + 300 * MS, starts_phase=False)
    acked = builder.produced(5) + 50 * MS
    builder.ack(acked)
    builder.phase_start(events, "subscription_acknowledged", acked)
    restart = builder.produced(40) + 50 * MS
    builder.timeline["disturbances"] = [
        {"kind": "gatewayd_restart", "start_realtime_ns": restart, "end_realtime_ns": restart + 100 * MS,
         "expects_resubscription": False},
    ]
    for seq in range(6, 41):
        builder.arrive(events, seq, "delivered")
    for index, seq in enumerate(range(41 - copies, 41)):
        verdict = "delivered" if deliver_copy and index == 0 else "copy_in_phase"
        if not none:
            builder.arrive(events, seq, verdict, at=restart + 300 * MS + index * MS)
    for seq in range(41, 80):
        builder.arrive(events, seq, "delivered", at=max(builder.produced(seq), restart + 400 * MS) + 2 * MS)
    pair = builder.produced(80) + 50 * MS
    builder.timeline["disturbances"].append({"kind": "gateway_pair_restart", "start_realtime_ns": pair,
                                             "end_realtime_ns": pair + 500 * MS, "expects_resubscription": True})
    builder.phase_end(events, "subscription_lost:tcp_closed", pair)
    acked_again = pair + 1 * S
    builder.ack(acked_again)
    builder.phase_start(events, "subscription_acknowledged", acked_again)
    for index, seq in enumerate(range(81 - older, 81)):
        if not none:
            builder.arrive(events, seq, "older_than_phase", at=acked_again + (index + 1) * MS)
    for seq in range(91, 151):
        builder.arrive(events, seq, "delivered")
    builder.final(events, T0 + 20 * S)
    return builder


def test_stored_samples_pass_and_report_each_step():
    result = evaluate_stored_samples(stored_builder().records())
    assert result["outcome"] == PASS, result["reasons"]
    steps = {s["step"]: s for s in result["metrics"]["steps"]}
    assert steps["gatewayd_restart"]["stored_dropped"] == {"copy_in_phase": 8}
    assert steps["gateway_pair_restart"]["stored_dropped"] == {"older_than_phase": 9}
    assert result["metrics"]["stored_frames_dropped"] == 17
    # Frames 33 to 40 and 72 to 79 come twice on the link; frame 80 comes once, late.
    assert result["metrics"]["repeats_on_link"] == 8 + 8


def test_stored_samples_are_inconclusive_when_none_arrive():
    assert evaluate_stored_samples(stored_builder(none=True).records())["outcome"] == MISSING


def test_stored_samples_need_a_frame_from_before_the_phase():
    result = evaluate_stored_samples(stored_builder(older=0).records())
    assert result["outcome"] == MISSING
    assert not result["checks"]["frames_from_before_the_phase_dropped_in_a_phase"]
    assert result["checks"]["copies_dropped_in_a_phase"]


def test_stored_samples_need_a_copy():
    result = evaluate_stored_samples(stored_builder(copies=0).records())
    assert result["outcome"] == MISSING
    assert not result["checks"]["copies_dropped_in_a_phase"]
    assert result["checks"]["frames_from_before_the_phase_dropped_in_a_phase"]


def test_stored_samples_report_the_link_view_per_step():
    steps = {s["step"]: s for s in evaluate_stored_samples(stored_builder().records())["metrics"]["steps"]}
    assert steps["gatewayd_restart"]["repeats_on_link"] == 8
    assert steps["gateway_pair_restart"]["older_on_link"] == 9


def test_a_copy_served_after_a_gatewayd_restart_fails():
    result = evaluate_stored_samples(stored_builder(deliver_copy=True).records())
    assert result["outcome"] == FAIL
    assert not result["checks"]["no_copy_served_in_phase:receiver-1.log"]


# --------------------------------------------------------------------------- TTL renewal


def ttl_builder(*, ack_gap_s: float = 1.0, multicast: bool = False, lapse: bool = False, seconds: int = 15,
                early_nack: bool = False, late_nack: bool = False) -> Builder:
    builder = Builder(seconds * 10 + 20)
    builder.auto_renewals = False  # the Acks of this case are its subject
    events = builder.receiver(multicast=multicast)
    builder.connect_client(events, T0 + 300 * MS, starts_phase=False)
    if early_nack:  # a subscription before someipd's first offer
        builder.sd.append(SdMessage(T0 + 100 * MS, HOST, 30490, GUEST, 30490, 1, True, True,
                                    [SdEntry(7, "SubscribeEventgroupAck", 0x4DEE, 1, 1, 0, 1, None, [])]))
        Builder.event(events, "nack", T0 + 100 * MS)
        Builder.event(events, "connection_ended", T0 + 100 * MS)
    builder.phase_start(events, "subscription_acknowledged", T0 + 500 * MS)
    at = T0 + 500 * MS
    while at <= T0 + 500 * MS + seconds * S:
        builder.ack(at)
        at += int(ack_gap_s * S)
    if late_nack:
        builder.sd.append(SdMessage(T0 + 6 * S, HOST, 30490, GUEST, 30490, 99, True, True,
                                    [SdEntry(7, "SubscribeEventgroupAck", 0x4DEE, 1, 1, 0, 1, None, [])]))
    if lapse:
        Builder.event(events, "subscription_expired", T0 + 5 * S)
    for seq in range(1, seconds * 10):
        builder.arrive(events, seq, "delivered")
    builder.final(events, T0 + (seconds + 2) * S)
    return builder


def test_ttl_renewal_passes_over_five_ttls():
    result = evaluate_ttl_renewal(ttl_builder().records())
    assert result["outcome"] == PASS, result["reasons"]
    assert result["metrics"]["acked_window_s"] >= 9


def test_ttl_renewal_accepts_a_nack_before_the_first_ack():
    result = evaluate_ttl_renewal(ttl_builder(early_nack=True).records())
    assert result["outcome"] == PASS, result["reasons"]
    assert result["metrics"]["nacks_before_first_ack"] == 1


def test_ttl_renewal_fails_on_a_nack_after_the_first_ack():
    assert not evaluate_ttl_renewal(ttl_builder(late_nack=True).records())["checks"]["no_nack_after_the_first_ack"]


def test_ttl_renewal_fails_when_acks_are_a_ttl_apart():
    assert not evaluate_ttl_renewal(ttl_builder(ack_gap_s=3.0).records())["checks"]["renewed_before_each_ttl"]


def test_ttl_renewal_needs_the_unicast_fallback_only():
    assert not evaluate_ttl_renewal(ttl_builder(multicast=True).records())["checks"]["unicast_fallback_only"]


def test_ttl_renewal_fails_on_a_lapse():
    assert not evaluate_ttl_renewal(ttl_builder(lapse=True).records())["checks"]["no_lapse"]


def test_ttl_renewal_is_inconclusive_for_a_short_window():
    assert evaluate_ttl_renewal(ttl_builder(seconds=4).records())["outcome"] == MISSING


# --------------------------------------------------------------------------- init file


def test_the_init_file_lets_the_receiver_start_the_ingress():
    """The .rc passes the announce sequence of the bench and sets no ingress trigger itself."""
    rc = (BENCH / "someip-receiver" / "de4sdv_someip_receiver.rc").read_text()
    lines = [line.strip() for line in rc.splitlines() if line.strip() and not line.strip().startswith("#")]
    service = next(line.split() for line in lines if line.startswith("service de4sdv_someip_receiver "))
    announced = [tuple(service[i + 1].split("=", 1)) for i, word in enumerate(service) if word == "--announce-property"]
    assert announced == list(ANNOUNCED_PROPERTIES)
    assert [service[i + 1] for i, word in enumerate(service) if word == "--ingress-start-property"] == \
        [INGRESS_START_PROPERTY]
    commands = [line for line in lines if not line.startswith("service ")]
    assert not [line for line in commands if line.startswith("setprop de4sdv.aebs.frame_server.host")]
    assert not [line for line in commands if line.startswith("setprop de4sdv.aebs.ingress.start")]
    assert not [line for line in lines if "init.svc.de4sdv_someip_receiver" in line]
    assert "setprop de4sdv.aebs.frame_server.port 4731" in commands
    # The margin of the discard rule is fixed: the service passes no margin option.
    assert not [word for word in service if "margin" in word or "clock-offset" in word]
    assert "oneshot" not in lines
    # Records that the evaluators can read: a line per served frame too.
    assert "--log-frames" in service
    # init's stop sends SIGTERM first, so the receiver sends StopSubscribe and logs final_status.
    assert "gentle_kill" in lines


# --------------------------------------------------------------------------- ingress_start


def ingress_builder(*, race: bool = True, trigger_after_stop: bool = False, request_after_stop: bool = False,
                    tries_at_end: int = 11, unread_at_stop: int = 0) -> Builder:
    """First ingress; receiver killed at 5 s while the old ingress lingers; ingress stopped at 12 s;
    receiver killed at 18 s and started while no ingress can start."""
    builder = Builder(300)
    standin: list[dict] = []

    def stand_in(event: str, realtime_ns: int, receiver: str, prop: str, monotonic: int, **fields) -> None:
        standin.append({"event": event, "realtime_ns": realtime_ns, "monotonic_ns": realtime_ns - T0,
                        "property": prop, "value": "1" if prop == INGRESS_START_PROPERTY else "127.0.0.1",
                        "receiver_log": receiver, "receiver_monotonic_ns": monotonic, **fields})

    seq = 1

    def frames_until(events: list[dict], until: int, verdict: str) -> None:
        nonlocal seq
        while builder.produced(seq) < until:
            builder.arrive(events, seq, verdict)
            seq += 1

    def restart(at: int) -> list[dict]:
        events = builder.receiver()
        for record in events:
            record["realtime_ns"] += at - T0
            record["monotonic_ns"] += at - T0
        return events

    events = builder.receiver()
    builder.ack(T0 + 100 * MS)
    builder.event(events, "subscribed", T0 + 100 * MS)
    stand_in("started", T0 + 50 * MS, "receiver-1.log", "de4sdv.aebs.frame_server.host", 1000, ingress="ingress-1")
    builder.connect_client(events, T0 + 300 * MS, starts_phase=True)
    frames_until(events, T0 + 5 * S, "delivered")
    # 1. receiver killed; its old ingress runs on for 2.5 s
    builder.timeline["disturbances"].append({"kind": "receiver_restart_old_ingress_alive",
                                             "start_realtime_ns": T0 + 5 * S})
    builder.connections[-1].close_realtime_ns = T0 + 5 * S + 10 * MS
    builder.connections[-1].end_reason = "closed"
    listen_at = T0 + 5 * S + 300 * MS
    events = restart(listen_at)
    host = next(e for e in events if e["event"] == "property_not_announced")
    listen = next(e for e in events if e["event"] == "ingress_trigger")
    builder.ack(listen_at + 200 * MS)
    builder.event(events, "subscribed", listen_at + 200 * MS)
    frames_until(events, listen_at + 200 * MS, "not_subscribed")
    if race:
        stand_in("start_ignored", listen_at + 20 * MS, "receiver-2.log", "de4sdv.aebs.frame_server.host",
                 host["monotonic_ns"], state="running")
        stand_in("start_ignored", listen_at + 20 * MS, "receiver-2.log", INGRESS_START_PROPERTY,
                 listen["monotonic_ns"], state="running")
        for k in (1, 2):
            builder.trigger(events, listen["realtime_ns"] + k * S, "no_first_client")
            stand_in("start_ignored", listen["realtime_ns"] + k * S + 20 * MS, "receiver-2.log", INGRESS_START_PROPERTY,
                     listen["monotonic_ns"] + k * S, state="running")
        start_at = listen["realtime_ns"] + 3 * S
        builder.trigger(events, start_at, "no_first_client")
        frames_until(events, start_at + 300 * MS, "no_client")
        stand_in("started", start_at + 20 * MS, "receiver-2.log", INGRESS_START_PROPERTY, start_at - T0,
                 ingress="ingress-2")
    else:
        start_at = listen["realtime_ns"]
        stand_in("started", start_at + 20 * MS, "receiver-2.log", "de4sdv.aebs.frame_server.host",
                 host["monotonic_ns"], ingress="ingress-2")
        frames_until(events, start_at + 300 * MS, "no_client")
    builder.connect_client(events, start_at + 300 * MS, starts_phase=True)
    frames_until(events, T0 + 12 * S, "delivered")
    # 2. the bench stops the ingress
    builder.timeline["disturbances"].append({"kind": "ingress_stopped", "start_realtime_ns": T0 + 12 * S})
    if unread_at_stop:
        del builder.recorded[-unread_at_stop:]
    builder.connections[-1].close_realtime_ns = T0 + 12 * S + 10 * MS
    builder.connections[-1].end_reason = "stopped"
    builder.event(events, "client_lost", T0 + 12 * S + 20 * MS)
    builder.phase_end(events, "client_lost", T0 + 12 * S + 20 * MS)
    if trigger_after_stop:
        builder.trigger(events, T0 + 14 * S, "no_first_client")
    if request_after_stop:
        stand_in("start_ignored", T0 + 14 * S, "receiver-2.log", INGRESS_START_PROPERTY, 14 * S, state="running")
    frames_until(events, T0 + 18 * S, "no_client")
    # 3. receiver killed and started while no ingress can start
    builder.timeline["disturbances"].append({"kind": "receiver_start_no_ingress", "start_realtime_ns": T0 + 18 * S})
    listen_at = T0 + 18 * S + 300 * MS
    events = restart(listen_at)
    listen = next(e for e in events if e["event"] == "ingress_trigger")
    for k in range(1, tries_at_end):
        builder.trigger(events, listen["realtime_ns"] + k * S, "no_first_client")
    if tries_at_end == 11:
        builder.event(events, "ingress_trigger_gave_up", listen["realtime_ns"] + 11 * S, tries=11)
    builder.final(events, T0 + 31 * S)
    builder.timeline["stop_realtime_ns"] = T0 + 31 * S
    builder.standin = standin
    return builder


def ingress_records(builder: Builder) -> CaseRecords:
    records = builder.records()
    records.init_stand_in = list(builder.standin)
    return records


def test_ingress_start_passes_and_reports_each_step():
    result = evaluate_ingress_start(ingress_records(ingress_builder()))
    assert result["outcome"] == PASS, result["reasons"]
    steps = {s["step"]: s for s in result["metrics"]["steps"]}
    race = steps["receiver_restart_old_ingress_alive"]
    assert race["started_by"] == "no_first_client"
    assert race["start_triggers_ignored"] == 3
    assert race["client_back_s"] == pytest.approx(3.6, abs=0.01)
    assert steps["ingress_stopped"]["start_requests"] == 0
    assert steps["receiver_start_no_ingress"]["tries"] == 11
    assert steps["receiver_start_no_ingress"]["gave_up_after_s"] == pytest.approx(11.0)


def test_ingress_start_is_inconclusive_without_the_race():
    result = evaluate_ingress_start(ingress_records(ingress_builder(race=False)))
    assert result["outcome"] == MISSING
    assert not result["checks"]["start_request_while_the_old_ingress_ran:receiver_restart_old_ingress_alive"]
    assert not result["checks"]["started_by_a_repeat:receiver_restart_old_ingress_alive"]


def test_a_stopped_ingress_must_stay_down():
    result = evaluate_ingress_start(ingress_records(ingress_builder(trigger_after_stop=True)))
    assert result["outcome"] == FAIL
    assert not result["checks"]["no_trigger_after_the_first_client:ingress_stopped"]
    assert not result["checks"]["ingress_trigger_rule:receiver-2.log"]
    result = evaluate_ingress_start(ingress_records(ingress_builder(request_after_stop=True)))
    assert not result["checks"]["stays_down:ingress_stopped"]


def test_the_receiver_gives_up_after_eleven_tries():
    result = evaluate_ingress_start(ingress_records(ingress_builder(tries_at_end=5)))
    assert result["outcome"] == FAIL
    assert not result["checks"]["tries_then_gave_up:receiver_start_no_ingress"]


@pytest.mark.parametrize("unread, outcome", [(3, PASS), (4, FAIL)])
def test_a_stopped_client_may_miss_its_last_frames(unread, outcome):
    result = evaluate_ingress_start(ingress_records(ingress_builder(unread_at_stop=unread)))
    assert result["outcome"] == outcome, result["reasons"]


def test_a_client_that_the_receiver_closed_may_not_miss_frames():
    builder = ingress_builder()
    builder.connections[1].end_reason = "closed"
    del builder.recorded[-1]
    assert evaluate_ingress_start(ingress_records(builder))["outcome"] == FAIL


def test_every_receiver_case_is_a_gate():
    """An inconclusive case fails the job too: no case is measured only."""
    sys.path.insert(0, str(BENCH / "scripts"))
    import run_someip_receiver_interop as runner  # noqa: PLC0415

    assert set(runner.GATE_CASES) == set(runner.CASES)
    assert not hasattr(runner, "MEASUREMENT_CASES")
