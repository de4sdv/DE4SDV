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


def _sd(ts, src, dst, entries, options=(), src_port=None):
    return ts, b.udp_datagram(src, dst, src_port if src_port is not None else b.SD_PORT, b.SD_PORT,
                              b.sd_message(entries, list(options)))


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


def test_the_offer_source_port_is_read(tmp_path):
    # Review R43: the reader keeps the SD datagram's source port, so the
    # evaluator can tell a valid offer (from 30490) from an ignored one.
    from_sd_port = _sd(T, IVI, CORE, [b.sd_entry(b.SD_OFFER, 0x4DEE, 1, options=1)],
                       [b.sd_ipv4_endpoint(IVI, 30509)])
    from_ephemeral = _sd(T + 1, IVI, CORE, [b.sd_entry(b.SD_OFFER, 0x4DEE, 1, options=1)],
                         [b.sd_ipv4_endpoint(IVI, 30509)], src_port=45678)
    entries = sd.sd_entries(_capture(tmp_path, [from_sd_port, from_ephemeral]))
    assert [e.src_port for e in entries] == [b.SD_PORT, 45678]
    assert sd.offer_and_provider([entries[0]])["offer_src_port"] == b.SD_PORT
    assert sd.offer_and_provider([entries[1]])["offer_src_port"] == 45678


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


# ------------------------------------------------------------ R43: did the core stack process the offer?
#
# The lines are vsomeip 3.1.37.1's own (service_discovery_impl.cpp and
# routing_manager_impl.cpp at the COVESA 3.1.37.1 tag). The image's copy may
# differ; S1 confirms the lines on the live SDV Core VM, and a missing line
# gives "unknown", which keeps VC-MW-016 inconclusive.

SINCE = 1793000000.0


def _line(epoch: float, message: str, level: str = "W", tag: str = "vsomeip") -> str:
    return f"{epoch:.6f}   812   830 {level} {tag}  : {message}"


def test_r43_a_secure_service_rejection_shows_the_stack_processed_the_offer():
    text = "\n".join([_line(SINCE - 5, "process_offerservice_serviceentry: Ignoring offer of [4dee.0001]"),
                      _line(SINCE + 0.4, "process_offerservice_serviceentry: Ignoring offer of [4dee.0001]")])
    record = sd.core_offer_record(text, since_epoch_s=SINCE, provider="192.168.98.118")
    assert record["status"] == "processed" and record["processed"] is True
    assert record["result"] == "secure_service_rejected"
    assert "Ignoring offer of [4dee.0001]" in record["matched_line"]
    assert record["matched_line"].startswith(f"{SINCE + 0.4:.6f}")


def test_r43_an_acceptance_rejection_of_the_spoofed_provider_shows_processing():
    text = _line(SINCE + 1, "service_discovery_impl::process_offerservice_serviceentry: Do not accept offer from "
                            "192.168.98.118:30509 reliable=1")
    record = sd.core_offer_record(text, since_epoch_s=SINCE, provider="192.168.98.118")
    assert record["status"] == "processed" and record["result"] == "acceptance_rejected"


def test_r43_an_sd_message_from_an_unknown_port_was_ignored_before_sd():
    text = _line(SINCE + 0.2, "Ignored SD message from unknown port (45678)", level="E")
    record = sd.core_offer_record(text, since_epoch_s=SINCE, provider="192.168.98.118")
    assert record["status"] == "ignored" and record["processed"] is False
    assert record["result"] == "unknown_port"


def test_r43_no_line_in_the_window_is_unknown():
    text = "\n".join([_line(SINCE - 30, "process_offerservice_serviceentry: Ignoring offer of [4dee.0001]"),
                      _line(SINCE + 1, "process_offerservice_serviceentry: Ignoring offer of [1234.0001]"),
                      "no timestamp: Ignoring offer of [4dee.0001]"])
    record = sd.core_offer_record(text, since_epoch_s=SINCE, provider="192.168.98.118")
    assert record["status"] == "unknown" and record["processed"] is None and record["matched_line"] is None


def test_r43_a_service_line_takes_precedence_over_an_unrelated_ignored_message():
    # "Ignored SD message ..." names no service; another sender can cause it. A
    # line that names the frame service is specific to the spoofed offer.
    text = "\n".join([_line(SINCE + 0.1, "Ignored SD message from unknown port (5353)", level="E"),
                      _line(SINCE + 0.2, "process_offerservice_serviceentry: Ignoring offer of [4dee.0001]")])
    record = sd.core_offer_record(text, since_epoch_s=SINCE, provider="192.168.98.118")
    assert record["status"] == "processed"
    assert any("unknown port" in line for line in record["also_seen"])


def test_r43_the_matcher_is_a_setting():
    text = _line(SINCE + 0.2, "SD: offer 4dee.0001 discarded by policy")
    record = sd.core_offer_record(text, since_epoch_s=SINCE, provider="192.168.98.118",
                                  processed_patterns=[("image_policy", r"offer {service}\.{instance} discarded")])
    assert record["status"] == "processed" and record["result"] == "image_policy"
    assert record["patterns"]["processed"] == [["image_policy", r"offer {service}\.{instance} discarded"]]


def test_r43_the_sd_processed_command_writes_the_record(tmp_path, capsys):
    from de4sdv_broker_path_bench import hostscan
    logcat = tmp_path / "core-logcat-sd-offer.txt"
    logcat.write_text(_line(SINCE + 0.3, "process_offerservice_serviceentry: Ignoring offer of [4dee.0001]") + "\n")
    out = tmp_path / "sd_core_processed.json"
    assert hostscan.main(["sd-processed", "--logcat", str(logcat), "--since", str(SINCE),
                          "--provider", "192.168.98.118", "--out", str(out)]) == 0
    import json
    record = json.loads(out.read_text())
    assert record["status"] == "processed" and record["pattern_source"].startswith("vsomeip 3.1.37.1")
