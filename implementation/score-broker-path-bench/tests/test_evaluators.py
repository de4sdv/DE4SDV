"""End-to-end tests of the evaluators over synthetic run directories.

Each test builds a run directory of raw artifacts and asserts the outcome.
The artifacts are the same kinds the bench captures: a host pcap of the frame
assembler stream, a guest pcap of the relay stream, NTP captures and probe
JSON.
"""

from __future__ import annotations

import json
import struct
import sys
import tempfile
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import builders as b  # noqa: E402
from de4sdv_broker_path_bench import evaluators, outcome  # noqa: E402

STAGES = ["MONITORING", "WARNING", "INTERVENTION", "RELEASED", "MONITORING", "MONITORING"]


def _stream_pcap(port: int, frames_payloads: list[bytes], step_ns: int = 10_000_000, t0_ns: int = 1_000_000_000):
    sender = b.TcpSender("10.0.0.2", "10.0.0.1", port + 1000, port, t0_ns).handshake()
    for payload in frames_payloads:
        sender.send(b.delimited(payload), step_ns=step_ns)
    sender.fin()
    return b.pcap(sender.records)


def _frames(stages=STAGES, base_ns=2_000_000_000):
    return [b.frame(index + 1, base_ns + index * 100_000_000, stage=stage) for index, stage in enumerate(stages)]


def _run(tmp: Path, **files: bytes) -> Path:
    run = tmp
    for name, data in files.items():
        (run / name.replace("__", ".")).write_bytes(data)
    return run


def _settings(run: Path, **values) -> None:
    (run / "settings.json").write_text(json.dumps(values))


def test_source_order_passes_when_every_frame_arrives_in_order(tmp_path) -> None:
    payloads = _frames()
    _run(tmp_path, produced__pcap=_stream_pcap(4721, payloads), received__pcap=_stream_pcap(4731, payloads))
    _settings(tmp_path)
    result = evaluators.evaluate_source_order(evaluators.load_run(tmp_path))
    assert result.outcome == outcome.PASS, result.as_dict()


def test_source_order_fails_on_a_missing_frame(tmp_path) -> None:
    payloads = _frames()
    received = payloads[:2] + payloads[3:]  # the INTERVENTION frame never arrives
    _run(tmp_path, produced__pcap=_stream_pcap(4721, payloads), received__pcap=_stream_pcap(4731, received))
    _settings(tmp_path)
    result = evaluators.evaluate_source_order(evaluators.load_run(tmp_path))
    assert result.outcome == outcome.FAIL
    assert any(finding.code == "completeness" for finding in result.findings)


def test_source_order_inconclusive_when_a_stage_is_absent(tmp_path) -> None:
    payloads = _frames(stages=["MONITORING", "WARNING", "MONITORING"])  # no INTERVENTION, no RELEASED
    _run(tmp_path, produced__pcap=_stream_pcap(4721, payloads), received__pcap=_stream_pcap(4731, payloads))
    _settings(tmp_path)
    result = evaluators.evaluate_source_order(evaluators.load_run(tmp_path))
    assert result.outcome == outcome.INCONCLUSIVE


def test_source_order_fails_on_a_large_inter_arrival_gap(tmp_path) -> None:
    payloads = _frames()
    sender = b.TcpSender("10.0.0.2", "10.0.0.1", 5731, 4731).handshake()
    for index, payload in enumerate(payloads):
        sender.send(b.delimited(payload), step_ns=600_000_000 if index == 3 else 10_000_000)
    sender.fin()
    _run(tmp_path, produced__pcap=_stream_pcap(4721, payloads), received__pcap=b.pcap(sender.records))
    _settings(tmp_path)
    result = evaluators.evaluate_source_order(evaluators.load_run(tmp_path))
    assert result.outcome == outcome.FAIL
    assert any(finding.code == "gap" for finding in result.findings)


def test_provenance_passes_on_identical_bytes(tmp_path) -> None:
    payloads = _frames()
    _run(tmp_path, produced__pcap=_stream_pcap(4721, payloads), received__pcap=_stream_pcap(4731, payloads))
    _settings(tmp_path)
    result = evaluators.evaluate_provenance(evaluators.load_run(tmp_path))
    assert result.outcome == outcome.PASS, result.as_dict()


def test_provenance_fails_when_a_received_frame_differs(tmp_path) -> None:
    payloads = _frames()
    tampered = list(payloads)
    tampered[1] = b.frame(2, 2_100_000_000, stage="INTERVENTION")  # same sequence, other content
    _run(tmp_path, produced__pcap=_stream_pcap(4721, payloads), received__pcap=_stream_pcap(4731, tampered))
    _settings(tmp_path)
    result = evaluators.evaluate_provenance(evaluators.load_run(tmp_path))
    assert result.outcome == outcome.FAIL


def test_isolation_passes_when_no_port_is_reachable(tmp_path) -> None:
    (tmp_path / "host_listeners.json").write_text(json.dumps([
        {"port": 30160, "protocol": "udp", "element_in_layer": True, "element": "adapter"},
        {"port": 4721, "protocol": "tcp", "element_in_layer": False, "element": "frame_assembler"},
    ]))
    (tmp_path / "probe_attempts.json").write_text(json.dumps([
        {"guest": "ivi", "interface": "eth1", "host": "192.168.98.1", "port": 30160, "protocol": "udp",
         "marker": "m1", "result": "sent"},
        {"guest": "ivi", "interface": "buried_eth0", "host": "192.168.97.1", "port": 4721, "protocol": "tcp",
         "marker": "m2", "result": "timeout"},
    ]))
    (tmp_path / "host_capture_markers.json").write_text(json.dumps({"udp_markers": [], "tcp_accepted": []}))
    (tmp_path / "control.json").write_text(json.dumps({"reached": True, "detail": "control datagram arrived"}))
    _settings(tmp_path)
    result = evaluators.evaluate_isolation(evaluators.load_run(tmp_path))
    assert result.outcome == outcome.PASS, result.as_dict()


def test_isolation_fails_when_a_dds_port_is_reachable(tmp_path) -> None:
    (tmp_path / "host_listeners.json").write_text(json.dumps([
        {"port": 30160, "protocol": "udp", "element_in_layer": True, "element": "adapter"}]))
    (tmp_path / "probe_attempts.json").write_text(json.dumps([
        {"guest": "ivi", "interface": "buried_eth0", "host": "192.168.97.1", "port": 30160, "protocol": "udp",
         "marker": "m1", "result": "sent"}]))
    (tmp_path / "host_capture_markers.json").write_text(json.dumps({"udp_markers": ["m1"], "tcp_accepted": []}))
    (tmp_path / "control.json").write_text(json.dumps({"reached": True, "detail": "ok"}))
    _settings(tmp_path)
    result = evaluators.evaluate_isolation(evaluators.load_run(tmp_path))
    assert result.outcome == outcome.FAIL


def test_isolation_inconclusive_without_a_working_control(tmp_path) -> None:
    (tmp_path / "host_listeners.json").write_text(json.dumps([]))
    (tmp_path / "probe_attempts.json").write_text(json.dumps([
        {"guest": "ivi", "interface": "eth1", "host": "192.168.98.1", "port": 30160, "protocol": "udp",
         "marker": "m1", "result": "sent"}]))
    (tmp_path / "host_capture_markers.json").write_text(json.dumps({"udp_markers": [], "tcp_accepted": []}))
    (tmp_path / "control.json").write_text(json.dumps({"reached": False, "detail": "control never arrived"}))
    _settings(tmp_path)
    result = evaluators.evaluate_isolation(evaluators.load_run(tmp_path))
    assert result.outcome == outcome.INCONCLUSIVE


_NTP_TO_UNIX_S = 2_208_988_800


def _ntp_ts(unix_ns: int) -> bytes:
    seconds = unix_ns // 1_000_000_000 + _NTP_TO_UNIX_S
    fraction = (unix_ns % 1_000_000_000) * (1 << 32) // 1_000_000_000
    return struct.pack(">II", seconds, fraction)


def _clock_pcap(offset_ns: int, at_ns: int, marker: int = 0x1234) -> bytes:
    one_way = 500_000
    t1 = at_ns
    t2 = t1 - offset_ns + one_way
    t4 = t1 + 2 * one_way
    request = bytes([0x23]) + bytes(39) + struct.pack(">Q", marker)
    response = bytes([0x24]) + bytes(23) + struct.pack(">Q", marker) + _ntp_ts(t2) + _ntp_ts(t2)
    return b.pcap([
        (t1, b.udp_datagram("192.168.98.118", "192.168.98.1", 40000, 123, request)),
        (t4, b.udp_datagram("192.168.98.1", "192.168.98.118", 123, 40000, response)),
    ])


def test_unsubscribed_discard_passes_when_frames_follow_the_subscription(tmp_path) -> None:
    # Offset 2 ms (guest ahead of host). New subscription at guest time 3_000_000_000.
    start_guest = 3_000_000_000
    offset = 2_000_000
    payloads = _frames(base_ns=start_guest - offset + 50_000_000)  # produced just after the subscription on the host
    _run(tmp_path, received__pcap=_stream_pcap(4731, payloads, t0_ns=start_guest))
    (tmp_path / "clock-start.pcap").write_bytes(_clock_pcap(offset, start_guest - 1_000_000_000))
    (tmp_path / "clock-end.pcap").write_bytes(_clock_pcap(offset, start_guest + 2_000_000_000, marker=0x5678))
    _settings(tmp_path, new_subscription_realtime_ns=[start_guest])
    result = evaluators.evaluate_unsubscribed_discard(evaluators.load_run(tmp_path))
    assert result.outcome == outcome.PASS, result.as_dict()


def test_unsubscribed_discard_fails_on_an_old_frame(tmp_path) -> None:
    start_guest = 3_000_000_000
    offset = 2_000_000
    old = b.frame(1, start_guest - offset - 5_000_000_000, stage="MONITORING")  # produced 5 s before the subscription
    _run(tmp_path, received__pcap=_stream_pcap(4731, [old], t0_ns=start_guest))
    (tmp_path / "clock-start.pcap").write_bytes(_clock_pcap(offset, start_guest - 1_000_000_000))
    (tmp_path / "clock-end.pcap").write_bytes(_clock_pcap(offset, start_guest + 2_000_000_000, marker=0x5678))
    _settings(tmp_path, new_subscription_realtime_ns=[start_guest])
    result = evaluators.evaluate_unsubscribed_discard(evaluators.load_run(tmp_path))
    assert result.outcome == outcome.FAIL


def test_unsubscribed_discard_inconclusive_when_the_clock_bound_fails(tmp_path) -> None:
    start_guest = 3_000_000_000
    payloads = _frames(base_ns=start_guest)
    _run(tmp_path, received__pcap=_stream_pcap(4731, payloads, t0_ns=start_guest))
    (tmp_path / "clock-start.pcap").write_bytes(_clock_pcap(50_000_000, start_guest - 1_000_000_000))  # 50 ms offset
    (tmp_path / "clock-end.pcap").write_bytes(_clock_pcap(50_000_000, start_guest + 2_000_000_000, marker=0x5678))
    _settings(tmp_path, new_subscription_realtime_ns=[start_guest])
    result = evaluators.evaluate_unsubscribed_discard(evaluators.load_run(tmp_path))
    assert result.outcome == outcome.INCONCLUSIVE


def test_run_cli_reports_each_case(tmp_path) -> None:
    from de4sdv_broker_path_bench import run
    payloads = _frames()
    _run(tmp_path, produced__pcap=_stream_pcap(4721, payloads), received__pcap=_stream_pcap(4731, payloads))
    _settings(tmp_path)
    code = run.main([str(tmp_path), "--case", "VC-MW-015", "--case", "VC-MW-016"])
    assert code == 0
