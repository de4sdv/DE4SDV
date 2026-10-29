"""Tests of the clock-offset reader, the outcome vocabulary and the DDS-port derivation."""

from __future__ import annotations

import struct
import sys
import tempfile
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import builders as b  # noqa: E402
from de4sdv_broker_path_bench import clock, outcome, probe  # noqa: E402
from de4sdv_broker_path_bench.pcap import read_pcap  # noqa: E402

_NTP_TO_UNIX_S = 2_208_988_800


def _ntp_ts(unix_ns: int) -> bytes:
    seconds = unix_ns // 1_000_000_000 + _NTP_TO_UNIX_S
    fraction = (unix_ns % 1_000_000_000) * (1 << 32) // 1_000_000_000
    return struct.pack(">II", seconds, fraction)


def _request(marker: int) -> bytes:
    return bytes([0x23]) + bytes(39) + struct.pack(">Q", marker)


def _response(marker: int, t2_ns: int, t3_ns: int) -> bytes:
    # Marker (the client's transmit stamp) echoed in the originate field at offset 24.
    return bytes([0x24]) + bytes(23) + struct.pack(">Q", marker) + _ntp_ts(t2_ns) + _ntp_ts(t3_ns)


def _clock_capture(offset_ns: int, one_way_ns: int, marker: int = 0xABCD) -> str:
    """A guest capture of one exchange with a known offset and symmetric delay."""
    t1 = 1_000_000_000_000
    t2_host = t1 - offset_ns + one_way_ns
    t3_host = t2_host
    t4 = t1 + 2 * one_way_ns
    records = [
        (t1, b.udp_datagram("192.168.98.118", "192.168.98.1", 40000, 123, _request(marker))),
        (t4, b.udp_datagram("192.168.98.1", "192.168.98.118", 123, 40000, _response(marker, t2_host, t3_host))),
    ]
    handle = tempfile.NamedTemporaryFile(suffix=".pcap", delete=False)
    handle.write(b.pcap(records))
    handle.close()
    return handle.name


def test_offset_and_uncertainty_from_a_symmetric_exchange() -> None:
    path = _clock_capture(offset_ns=5_000_000, one_way_ns=1_000_000)
    found, problems = clock.exchanges(read_pcap(path))
    assert problems == []
    measurement = clock.best(found)
    assert measurement is not None
    assert abs(measurement.offset_ns - 5_000_000) < 1_000
    assert abs(measurement.uncertainty_ns - 1_000_000) < 1_000
    assert measurement.holds()  # 5 ms + 1 ms < 20 ms


def test_a_large_offset_fails_the_bound() -> None:
    path = _clock_capture(offset_ns=50_000_000, one_way_ns=1_000_000)
    measurement = clock.best(clock.exchanges(read_pcap(path))[0])
    assert measurement is not None and not measurement.holds()


def test_a_response_without_its_request_is_a_problem() -> None:
    t2 = 1_000_000_000_000
    records = [(t2 + 1000, b.udp_datagram("192.168.98.1", "192.168.98.118", 123, 40000,
                                          _response(0x11, t2, t2)))]
    handle = tempfile.NamedTemporaryFile(suffix=".pcap", delete=False)
    handle.write(b.pcap(records))
    handle.close()
    _found, problems = clock.exchanges(read_pcap(handle.name))
    assert any("without its request" in problem for problem in problems)


def test_drift_and_session_length() -> None:
    # The spike saw the offset move about 50 ms in 14 minutes (about 60 ppm).
    start = clock.OffsetMeasurement(offset_ns=0.0, uncertainty_ns=1_000_000.0, exchanges=1, measured_at_ns=0)
    end = clock.OffsetMeasurement(offset_ns=50_000_000.0, uncertainty_ns=1_000_000.0, exchanges=1,
                                  measured_at_ns=14 * 60 * 1_000_000_000)
    rate = clock.drift_ppm(start, end)
    assert 50 < rate < 70
    # At that rate the 20 ms budget lasts a few minutes after a setting.
    fresh = clock.OffsetMeasurement(0.0, 1_000_000.0, 1, 0)
    seconds = clock.session_seconds(fresh, rate)
    assert 100 < seconds < 600


def test_outcome_precedence_and_verdict() -> None:
    assert outcome.verdict(outcome.PASS) == "pass"
    assert outcome.verdict(outcome.FAIL) == "fail"
    assert outcome.verdict(outcome.ERROR) == "error"
    assert outcome.verdict(outcome.INCONCLUSIVE) == "inconclusive"
    assert outcome.verdict(outcome.BLOCKED) == "inconclusive"
    result = outcome.CaseResult("VC-MW-015", "run1")
    result.add("a", outcome.PASS, "ok")
    assert result.outcome == outcome.PASS
    result.add("b", outcome.INCONCLUSIVE, "missing")
    assert result.outcome == outcome.INCONCLUSIVE  # missing evidence beats a pass
    result.add("c", outcome.FAIL, "observed")
    assert result.outcome == outcome.FAIL  # an independent failure beats missing evidence
    result.add("d", outcome.ERROR, "bad evidence")
    assert result.outcome == outcome.ERROR
    empty = outcome.CaseResult("VC-MW-016", "run1")
    assert empty.outcome == outcome.INCONCLUSIVE  # no finding is no pass


def test_outcome_dependent_failure_is_downgraded() -> None:
    # A FAIL that depends on an inconclusive condition (a capture gap, a bad
    # clock) does not dominate; it becomes missing evidence (#448 precedence).
    result = outcome.CaseResult("VC-MW-015", "run")
    result.add("delivery_evidence", outcome.INCONCLUSIVE, "the guest capture has a gap")
    result.add("completeness", outcome.FAIL, "2 frames missing", depends_on="delivery_evidence")
    assert result.outcome == outcome.INCONCLUSIVE
    independent = outcome.CaseResult("VC-MW-015", "run")
    independent.add("completeness", outcome.FAIL, "2 frames missing", depends_on="delivery_evidence")
    assert independent.outcome == outcome.FAIL
    mixed = outcome.CaseResult("VC-MW-015", "run")
    mixed.add("delivery_evidence", outcome.INCONCLUSIVE, "bad clock")
    mixed.add("phase-end", outcome.FAIL, "layer-caused phase end in the event")
    assert mixed.outcome == outcome.FAIL


def test_dds_ports_follow_the_domain_and_the_participant_index() -> None:
    ports = probe.dds_udp_ports(domain=91, max_index=120)
    assert ports[0] == 30150  # SPDP multicast
    assert 30151 in ports  # user multicast
    assert 30160 in ports and 30401 in ports  # unicast range for indices 0..120
    assert max(ports) == 30401
    assert 30402 not in ports
