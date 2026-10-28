"""Tests of the evaluators of the SOME/IP receiver against someipd (P0.3).

Each test builds the raw records of one case in memory, as the runner
writes them: frame source, loopback client, receiver log lines, the link
capture, gatewayd logs and the LoLa shared memory snapshot. A passing
record set is then changed in one place to show that the evaluator fails
for that reason (mutation tests).
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
    DROP_REASONS,
    CaseRecords,
    ReceiverRun,
    RecordedFrame,
    RecorderConnection,
    SourceFrame,
    evaluate_identity,
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

    def receiver(self, bound_ns: int = 0, multicast: bool = True) -> list[dict]:
        events = [{"event": "start", "monotonic_ns": 0, "realtime_ns": T0, "clock_offset_bound_ns": bound_ns,
                   "join_multicast": multicast, "subscription_ttl_s": 3}]
        self.receivers.append(events)
        return events

    @staticmethod
    def event(events: list[dict], name: str, realtime_ns: int, **fields) -> None:
        events.append({"event": name, "monotonic_ns": realtime_ns - T0, "realtime_ns": realtime_ns, **fields})

    def phase(self, events: list[dict], cause: str, realtime_ns: int) -> None:
        if cause == "subscription_acknowledged":
            self.event(events, "subscribed", realtime_ns)
        else:
            self.event(events, "client_connected", realtime_ns)
        self.event(events, "phase_start", realtime_ns, cause=cause, phase_start_realtime_ns=realtime_ns)

    def connect_client(self, realtime_ns: int) -> int:
        index = len(self.connections) + 1
        self.connections.append(RecorderConnection(index, realtime_ns, None))
        return index

    def arrive(self, events: list[dict], seq: int, verdict: str, *, at: int | None = None,
               connection: int | None = None, on_link: bool = True) -> None:
        data = self.payloads[seq]
        receipt = at if at is not None else self.produced(seq) + 2 * MS
        self.event(events, "frame", receipt, verdict=verdict, sequence=seq, frame_timestamp_ns=self.produced(seq),
                   payload_bytes=len(data))
        if on_link:
            self.link.append(SomeipMessage(receipt - MS, HOST, 30509, GUEST, 40000, 0x4DEE, 0x8001, 0, seq & 0xFFFF,
                                           1, 1, 0x02, 0, data))
        if verdict == "delivered":
            self.recorded.append(RecordedFrame(connection or len(self.connections), receipt + MS, len(data), True,
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
    builder.phase(events, "client_connected", T0 + 500 * MS)
    builder.connect_client(T0 + 500 * MS)
    builder.ack(T0 + 700 * MS)
    builder.phase(events, "subscription_acknowledged", T0 + 700 * MS)
    for seq in range(1, 201):
        builder.arrive(events, seq, "delivered")
    builder.final(events, T0 + 30 * S)
    return builder


def test_identity_passes_with_200_identical_frames():
    result = evaluate_identity(identity_builder().records())
    assert result["outcome"] == PASS, result["reasons"]
    assert result["metrics"]["frames_byte_identical"] == 200
    assert result["metrics"]["largest_frames"] > 0


def test_identity_fails_when_one_byte_differs_at_the_client():
    records = identity_builder().records()
    records.recorder_frames[50].sha256 = "0" * 64
    result = evaluate_identity(records)
    assert result["outcome"] == FAIL
    assert not result["checks"]["all_frames_byte_identical_in_order"]


def test_identity_fails_when_a_frame_is_missing():
    builder = Builder(200)
    events = builder.receiver()
    builder.phase(events, "client_connected", T0 + 500 * MS)
    builder.connect_client(T0 + 500 * MS)
    builder.phase(events, "subscription_acknowledged", T0 + 700 * MS)
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
    builder = identity_builder()
    records = builder.records()
    for frame in records.source_frames:
        if frame.size == 2044:
            frame.size = 2043  # as if the source never produced a frame of 2044 bytes
    assert not evaluate_identity(records)["checks"]["largest_frame_crossed"]


def test_identity_fails_when_a_delivered_frame_is_older_than_its_phase():
    builder = identity_builder()
    records = builder.records()
    phase = [e for e in records.receivers[0].events if e["event"] == "phase_start"][-1]
    phase["phase_start_realtime_ns"] = Builder.produced(150)
    result = evaluate_identity(records)
    assert not result["checks"]["delivered_not_older_than_phase:receiver-1.log"]


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
    assert records.receivers[0].start["clock_offset_bound_ns"] == 0
    assert "Failed to subscribe" in records.gatewayd_logs["gatewayd.log"]
    assert records.capture is None and records.source_stream == b"\x01\x02"


# --------------------------------------------------------------------------- resubscribe


def resubscribe_builder(*, duplicate: bool = False, gap: bool = False, missing_resubscribe: bool = False,
                        killed_extra_frame: bool = False) -> Builder:
    builder = Builder(400)
    kinds = ["receiver_sigterm_restart", "receiver_sigkill_restart", "gateway_pair_restart", "link_outage"]
    # Windows of 8 s: disturbance at 3 s, recovery at 4 s, frames continue.
    seq = 1
    events = builder.receiver()
    builder.phase(events, "client_connected", T0 + 500 * MS)
    builder.connect_client(T0 + 500 * MS)
    builder.phase(events, "subscription_acknowledged", T0 + 600 * MS)
    window_start = T0
    for index, kind in enumerate(kinds):
        disturbance_start = window_start + 3 * S
        recovery = window_start + 4 * S
        builder.timeline["disturbances"].append({"kind": kind, "start_realtime_ns": disturbance_start,
                                                 "end_realtime_ns": disturbance_start + 200 * MS})
        while builder.produced(seq) < disturbance_start:
            builder.arrive(events, seq, "delivered")
            seq += 1
        if kind.startswith("receiver_"):
            if kind == "receiver_sigterm_restart":
                builder.final(events, disturbance_start)
            elif killed_extra_frame:
                builder.recorded.append(RecordedFrame(len(builder.connections), disturbance_start, 10, True, seq,
                                                      builder.produced(seq),
                                                      hashlib.sha256(builder.payloads[seq]).hexdigest()))
                seq += 1
            events = builder.receiver()
            builder.phase(events, "client_connected", recovery - 300 * MS)
            builder.connect_client(recovery - 300 * MS)
        while builder.produced(seq) < recovery:
            builder.arrive(events, seq, "not_subscribed" if kind.startswith("receiver_") else "older_than_phase",
                           at=recovery + 1 * MS if not kind.startswith("receiver_") else None)
            seq += 1
        if not (missing_resubscribe and kind == "link_outage"):
            builder.ack(recovery)
            builder.phase(events, "subscription_acknowledged", recovery)
        if duplicate and kind == "gateway_pair_restart":
            builder.arrive(events, seq - 20, "sequence_not_increasing", at=recovery + 2 * MS)
        window_start += 8 * S
        while builder.produced(seq) < window_start:
            if gap and kind == "link_outage" and seq == builder_gap_sequence(builder, recovery):
                seq += 1
                continue
            if missing_resubscribe and kind == "link_outage":
                builder.arrive(events, seq, "not_subscribed")
            else:
                builder.arrive(events, seq, "delivered")
            seq += 1
    builder.final(events, window_start)
    builder.timeline["stop_realtime_ns"] = window_start
    return builder


def builder_gap_sequence(builder: Builder, recovery: int) -> int:
    return next(seq for seq in builder.payloads if builder.produced(seq) >= recovery + 2 * S)


def test_resubscribe_passes_and_reports_each_window():
    result = evaluate_resubscribe(resubscribe_builder().records())
    assert result["outcome"] == PASS, result["reasons"]
    windows = {w["kind"]: w for w in result["metrics"]["windows"]}
    assert set(windows) == {"receiver_sigterm_restart", "receiver_sigkill_restart", "gateway_pair_restart",
                            "link_outage"}
    assert all(w["resubscribed_after_s"] is not None for w in windows.values())


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
    assert not result["checks"]["resubscribed:link_outage"]


def test_resubscribe_fails_on_a_duplicate_at_the_client():
    builder = resubscribe_builder()
    records = builder.records()
    records.recorder_frames.append(copy.deepcopy(records.recorder_frames[10]))
    result = evaluate_resubscribe(records)
    assert result["outcome"] == FAIL
    assert not result["checks"]["no_duplicate_at_client"]


def test_resubscribe_counts_dropped_duplicates_by_reason():
    result = evaluate_resubscribe(resubscribe_builder(duplicate=True).records())
    assert result["outcome"] == PASS, result["reasons"]
    assert result["metrics"]["drops_by_reason"]["sequence_not_increasing"] == 1


def test_resubscribe_fails_on_a_gap_after_recovery():
    result = evaluate_resubscribe(resubscribe_builder(gap=True).records())
    assert not result["checks"]["no_gap_after_recovery:link_outage"]


def test_unknown_drop_reason_fails():
    builder = resubscribe_builder()
    records = builder.records()
    frame = next(e for e in records.receivers[0].events if e["event"] == "frame")
    frame["verdict"] = "lost_somewhere"
    assert evaluate_resubscribe(records)["outcome"] == FAIL


# --------------------------------------------------------------------------- no client


def no_client_builder(*, deliver_old: bool = False, queue: bool = False) -> Builder:
    builder = Builder(120)
    events = builder.receiver()
    builder.ack(T0 + 500 * MS)
    builder.phase(events, "subscription_acknowledged", T0 + 500 * MS)
    connect = builder.produced(50) + 50 * MS
    for seq in range(1, 51):
        builder.arrive(events, seq, "no_client")
    builder.phase(events, "client_connected", connect)
    builder.connect_client(connect)
    if queue:
        builder.arrive(events, 50, "delivered", at=connect + 1 * MS)
    for seq in range(51, 121):
        builder.arrive(events, seq, "delivered")
    builder.final(events, T0 + 20 * S)
    if deliver_old:
        records_frame = builder.recorded[0]
        records_frame.frame_timestamp_ns = connect - 10 * MS
    return builder


def test_no_client_passes():
    result = evaluate_no_client(no_client_builder().records())
    assert result["outcome"] == PASS, result["reasons"]
    assert result["metrics"]["dropped_no_client"] == 50


def test_no_client_fails_when_a_frame_produced_before_the_connection_arrives():
    result = evaluate_no_client(no_client_builder(deliver_old=True).records())
    assert result["outcome"] == FAIL
    assert not result["checks"]["nothing_produced_before_delivered"]


def test_no_client_fails_on_a_queued_frame():
    result = evaluate_no_client(no_client_builder(queue=True).records())
    assert result["outcome"] == FAIL
    assert not result["checks"]["no_queue"]


# --------------------------------------------------------------------------- stored samples


def stored_builder(*, stored: int = 10, deliver_one: bool = False, uncounted: bool = False) -> Builder:
    builder = Builder(150)
    events = builder.receiver()
    builder.phase(events, "client_connected", T0 + 300 * MS)
    builder.connect_client(T0 + 300 * MS)
    acked = builder.produced(60) + 50 * MS
    builder.ack(acked)
    builder.phase(events, "subscription_acknowledged", acked)
    for index, seq in enumerate(range(61 - stored, 61)):
        verdict = "delivered" if deliver_one and index == 0 else "older_than_phase"
        if uncounted and index == 0:
            builder.link.append(SomeipMessage(acked, HOST, 30509, GUEST, 40000, 0x4DEE, 0x8001, 0, seq, 1, 1, 2, 0,
                                              builder.payloads[seq]))
            continue
        builder.arrive(events, seq, verdict, at=acked + (index + 1) * MS)
    for seq in range(61, 151):
        builder.arrive(events, seq, "delivered")
    builder.final(events, T0 + 20 * S)
    return builder


def test_stored_samples_pass_reports_the_count_seen():
    result = evaluate_stored_samples(stored_builder(stored=10).records())
    assert result["outcome"] == PASS, result["reasons"]
    assert result["metrics"]["stored_frames_on_link"] == 10
    assert result["metrics"]["stored_frames_by_verdict"] == {"older_than_phase": 10}


def test_stored_samples_are_inconclusive_when_none_arrive():
    result = evaluate_stored_samples(stored_builder(stored=0).records())
    assert result["outcome"] == MISSING


def test_stored_sample_delivered_fails():
    result = evaluate_stored_samples(stored_builder(deliver_one=True).records())
    assert result["outcome"] == FAIL
    assert not result["checks"]["stored_frames_dropped"]
    assert not result["checks"]["no_stored_frame_at_client"]


def test_stored_sample_missing_in_the_receiver_lines_fails():
    result = evaluate_stored_samples(stored_builder(uncounted=True).records())
    assert not result["checks"]["stored_frames_counted_at_receiver"]


# --------------------------------------------------------------------------- TTL renewal


def ttl_builder(*, ack_gap_s: float = 1.0, multicast: bool = False, lapse: bool = False, seconds: int = 15) -> Builder:
    builder = Builder(seconds * 10 + 20)
    events = builder.receiver(multicast=multicast)
    builder.phase(events, "client_connected", T0 + 300 * MS)
    builder.connect_client(T0 + 300 * MS)
    builder.phase(events, "subscription_acknowledged", T0 + 500 * MS)
    at = T0 + 500 * MS
    while at <= T0 + 500 * MS + seconds * S:
        builder.ack(at)
        at += int(ack_gap_s * S)
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


def test_ttl_renewal_fails_when_acks_are_a_ttl_apart():
    assert not evaluate_ttl_renewal(ttl_builder(ack_gap_s=3.0).records())["checks"]["renewed_before_each_ttl"]


def test_ttl_renewal_needs_the_unicast_fallback_only():
    assert not evaluate_ttl_renewal(ttl_builder(multicast=True).records())["checks"]["unicast_fallback_only"]


def test_ttl_renewal_ignores_a_nack_before_the_first_subscription():
    builder = ttl_builder()
    events = builder.receivers[0]
    events.insert(1, {"event": "nack", "monotonic_ns": 1, "realtime_ns": T0 + 100 * MS})
    events.insert(2, {"event": "connection_ended", "monotonic_ns": 2, "realtime_ns": T0 + 100 * MS})
    assert evaluate_ttl_renewal(builder.records())["outcome"] == PASS


def test_ttl_renewal_fails_on_a_lapse():
    assert not evaluate_ttl_renewal(ttl_builder(lapse=True).records())["checks"]["no_lapse"]


def test_ttl_renewal_is_inconclusive_for_a_short_window():
    assert evaluate_ttl_renewal(ttl_builder(seconds=4).records())["outcome"] == MISSING
