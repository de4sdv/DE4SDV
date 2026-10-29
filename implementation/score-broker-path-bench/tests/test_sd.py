"""Tests of the SOME/IP-SD reader (VC-MW-016: the spoofed offer and the provider after it).

The SD packets follow the SOME/IP-SD layout byte for byte (header, entries,
IPv4 endpoint options) and sit in an Ethernet capture as tcpdump writes it on
the host bridge. The bench's own offer sender (scripts/send_sd_offer.sh)
builds its packet with printf; one test parses exactly those bytes.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import builders as b  # noqa: E402
from de4sdv_broker_path_bench import sd  # noqa: E402
from de4sdv_broker_path_bench.pcap import read_pcap  # noqa: E402

HOST, CORE, IVI = "192.168.98.1", "192.168.98.3", "192.168.98.118"
T = 1_793_000_000_000_000_000


def _sd(ts, src, dst, entries, options=()):
    return ts, b.udp_datagram(src, dst, b.SD_PORT, b.SD_PORT, b.sd_message(entries, list(options)))


def _capture(tmp_path, records):
    path = tmp_path / "host-cvd-ebr.pcap"
    path.write_bytes(b.pcap(records))
    return read_pcap(path)


def _host_offer(ts):
    return _sd(ts, HOST, "224.0.0.0", [b.sd_entry(b.SD_OFFER, 0x4DEE, 1, options=1)], [b.sd_ipv4_endpoint(HOST, 30509)])


def _core_subscribe(ts, dst):
    return _sd(ts, CORE, dst, [b.sd_entry(b.SD_SUBSCRIBE, 0x4DEE, 1, eventgroup=1, options=1)],
               [b.sd_ipv4_endpoint(CORE, 40001)])


def test_entries_are_read_with_their_options(tmp_path):
    entries = sd.sd_entries(_capture(tmp_path, [_host_offer(T)]))
    assert len(entries) == 1
    entry = entries[0]
    assert (entry.kind, entry.service, entry.instance, entry.ttl, entry.src) == ("offer", 0x4DEE, 1, 3, HOST)
    assert entry.endpoints == [(HOST, "tcp", 30509)]


def test_the_provider_after_a_spoofed_offer_stays_the_host(tmp_path):
    records = [_host_offer(T), _core_subscribe(T + 10, HOST),
               _sd(T + 1_000, IVI, CORE, [b.sd_entry(b.SD_OFFER, 0x4DEE, 1, options=1)], [b.sd_ipv4_endpoint(IVI, 30509)]),
               _core_subscribe(T + 2_000, HOST)]
    found = sd.offer_and_provider(sd.sd_entries(_capture(tmp_path, records)))
    assert found["offer_time_ns"] == T + 1_000 and found["offer_src"] == IVI
    assert found["providers_after"] == [HOST]


def test_a_redirected_subscription_names_the_ivi(tmp_path):
    records = [_host_offer(T),
               _sd(T + 1_000, IVI, CORE, [b.sd_entry(b.SD_OFFER, 0x4DEE, 1, options=1)], [b.sd_ipv4_endpoint(IVI, 30509)]),
               _core_subscribe(T + 2_000, IVI)]
    found = sd.offer_and_provider(sd.sd_entries(_capture(tmp_path, records)))
    assert found["providers_after"] == [IVI]


def test_no_spoofed_offer_gives_no_offer_time(tmp_path):
    found = sd.offer_and_provider(sd.sd_entries(_capture(tmp_path, [_host_offer(T), _core_subscribe(T + 10, HOST)])))
    assert found["offer_time_ns"] is None


def test_malformed_sd_payloads_are_skipped_not_raised(tmp_path):
    good = b.sd_message([b.sd_entry(b.SD_OFFER, 0x4DEE, 1)])
    records = [(T + i, b.udp_datagram(IVI, CORE, b.SD_PORT, b.SD_PORT, good[:i])) for i in range(len(good))]
    entries = sd.sd_entries(_capture(tmp_path, records))
    assert entries == []


def test_the_bench_offer_sender_bytes_parse_as_an_offer(tmp_path):
    script = BENCH / "scripts" / "send_sd_offer.sh"
    raw = subprocess.run(["bash", str(script), "bytes", IVI, "30509"], capture_output=True, check=True).stdout
    records = [(T, b.udp_datagram(IVI, CORE, b.SD_PORT, b.SD_PORT, raw))]
    entries = sd.sd_entries(_capture(tmp_path, records))
    assert [(e.kind, e.service, e.instance, e.major, e.ttl > 0) for e in entries] == [("offer", 0x4DEE, 1, 1, True)]
    assert entries[0].endpoints == [(IVI, "tcp", 30509)]
