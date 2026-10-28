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
        self.timeline: dict = {"case": "test", "disturbances": [], "stop_realtime_ns": T0 + 600 * S}
        self.gatewayd = {"gatewayd.log": "[gatewayd] Connected to someipd over the mw::com IPC binding\n"}
        self.shm = {"shared_pairs": {"adapter-gatewayd": ["/dev/shm/lola-data-1"],
                                     "gatewayd-someipd": ["/dev/shm/lola-data-2"]},
                    "foreign_owned_files": []}

    @staticmethod
    def produced(seq: int) -> int:
        return T0 + S + seq * 100 * MS

    def receiver(self, multicast: bool = True) -> list[dict]:
        events = [{"event": "start", "monotonic_ns": 0, "realtime_ns": T0, "phase_start_margin_ns": MARGIN,
                   "join_multicast": multicast, "subscription_ttl_s": 3}]
        events += [{"event": "property_not_announced", "monotonic_ns": 1000, "realtime_ns": T0 + 1000, "name": name,
                    "value": value, "reason": "not Android"} for name, value in ANNOUNCED_PROPERTIES]
        self.receivers.append(events)
        self.trigger(events, T0 + 2000, "listening")
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
        self.event(events, "subscribed" if cause == "subscription_acknowledged" else "client_connected", realtime_ns)
        self.event(events, "phase_start", realtime_ns, cause=cause, phase_start_realtime_ns=realtime_ns)

    def phase_end(self, events: list[dict], cause: str, realtime_ns: int) -> None:
        self.event(events, "phase_end", realtime_ns, cause=cause)

    def connect_client(self, events: list[dict], realtime_ns: int, *, starts_phase: bool) -> int:
        index = len(self.connections) + 1
        self.connections.append(RecorderConnection(index, realtime_ns, None))
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
                   payload_bytes=len(data))
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

    def records(self) -> CaseRecords:
        stream = TcpStream(0, HOST, 30509, GUEST, 40000, messages=list(self.link))
        capture = CaptureAnalysis(len(self.link), list(self.sd), 0, [stream])
        sources = [SourceFrame(seq, self.produced(seq), len(data) - 4, hashlib.sha256(data).hexdigest(), 1)
                   for seq, data in self.payloads.items()]
        source_stream = b"".join(self.payloads[seq] for seq in sorted(self.payloads))
        recorder_stream = b"".join(self.payloads[f.sequence] for f in self.recorded)
        return CaseRecords(
            case="test", timeline=copy.deepcopy(self.timeline), source_frames=sources,
            recorder_frames=list(self.recorded), recorder_connections=list(self.connections),
            receivers=[ReceiverRun(f"receiver-{i + 1}.log", copy.deepcopy(e)) for i, e in enumerate(self.receivers)],
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
    assert records.receivers[0].margin_ns == MARGIN
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
            events = builder.receiver()
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
