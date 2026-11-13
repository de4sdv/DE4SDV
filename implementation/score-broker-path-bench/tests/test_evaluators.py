"""Regression tests of the evaluators over synthetic run directories.

Each test builds a run directory of raw artifacts and asserts the outcome the
verification case (middleware_score_verification_evidence.sysml at main 4bcfe628) asks for. The cases marked [R...]/[E...]
reproduce the false-pass and fail/inconclusive-swap findings of the two
independent reviews of this bench at 1392e969; each must now give the right
outcome. The artifacts are the same kinds the bench captures.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import builders as b  # noqa: E402
from de4sdv_broker_path_bench import evaluators, outcome, probe  # noqa: E402

STAGES = ["MONITORING", "WARNING", "INTERVENTION", "RELEASED", "MONITORING", "MONITORING"]
P0 = 1_793_000_000_000_000_000  # a realistic epoch-ns base (2026-10), so clock captures stay positive
TAG = b.RELAY_TAG


def frames_seq(stages=STAGES, base_ns=P0, first_seq=1, step=100_000_000):
    return [b.frame(first_seq + i, base_ns + i * step, stage=s) for i, s in enumerate(stages)]


def write(run: Path, **files) -> Path:
    run.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        path = run / name.replace("__", ".")
        if isinstance(data, (dict, list)):
            path.write_text(json.dumps(data))
        elif isinstance(data, bytes):
            path.write_bytes(data)
        else:
            path.write_text(data)
    return run


def settings(**values) -> dict:
    values.setdefault("relay_logcat_tag", TAG)
    return dict(values)


def phase_logcat(start_ns, end_ns=None, *, layer_caused=False, client_connected=True, cause="client_connected",
                 phase=1, pid=1234, extra=()):
    lines = [b.phase_start_line(start_ns, phase=phase, pid=pid)]
    if end_ns is not None:
        lines.append(b.phase_end_line(end_ns, start_ns, phase=phase, pid=pid, layer_caused=layer_caused,
                                      client_connected=client_connected, cause=cause))
    lines.extend(extra)
    return "\n".join(lines) + "\n"


def clocks(run, offset_ns=2_000_000):
    (run / "clock-start.pcap").write_bytes(b.clock_pcap(offset_ns, P0 - 60_000_000_000, 0x1111))
    (run / "clock-end.pcap").write_bytes(b.clock_pcap(offset_ns, P0 + 60_000_000_000, 0x2222))


# ------------------------------------------------------------ VC-MW-015

def _vc015_base(tmp_path, produced, received, logcat=None, adapter_only=True, with_clock=True, **extra_settings):
    run = write(
        tmp_path,
        produced__pcap=b.pcap(b.stream_records(4721, produced, t0=P0)),
        received__pcap=b.pcap(b.stream_records(4731, received, t0=P0 + 5_000_000)),
        settings__json=settings(**extra_settings),
        frame_assembler_clients__json={"adapter_only": adapter_only},
    )
    if logcat is not None:
        (run / "relay-logcat.txt").write_text(logcat)
    if with_clock:
        clocks(run)
    return evaluators.load_run(run)


def test_vc015_passes_when_every_required_frame_arrives(tmp_path):
    payloads = frames_seq()
    run = _vc015_base(tmp_path, payloads, payloads, logcat=phase_logcat(P0 - 50_000_000))
    assert evaluators.evaluate_source_order(run).outcome == outcome.PASS, \
        evaluators.evaluate_source_order(run).as_dict()


def _truncate_received(run, received):
    # Rewrite received.pcap as a stream cut mid-connection: no FIN, so the
    # evaluator reads it as a guest capture stopped early (review B1).
    (run.run_dir / "received.pcap").write_bytes(b.pcap(b.stream_records(4731, received, t0=P0 + 5_000_000)[:-1]))


def test_vc015_b1_frames_produced_after_the_guest_capture_ended_are_not_required(tmp_path):
    # B1: the guest capture was cut mid-stream (no FIN) after frame 7, so the
    # stack produced frames 8-12 after the capture ended. They were delivered but
    # not captured; they are beyond the capture's coverage, so they are not
    # required and the run still passes.
    produced = frames_seq(["MONITORING", "WARNING", "INTERVENTION", "RELEASED"] + ["MONITORING"] * 8, base_ns=P0)
    run = _vc015_base(tmp_path, produced, produced[:7], logcat=phase_logcat(P0 - 50_000_000))
    _truncate_received(run, produced[:7])
    assert evaluators.evaluate_source_order(run).outcome == outcome.PASS, \
        evaluators.evaluate_source_order(run).as_dict()


def test_vc015_a_frame_missing_inside_the_capture_coverage_still_fails(tmp_path):
    # The ceiling trims only the tail: a frame produced well inside the covered
    # window that never arrived is still a completeness failure.
    produced = frames_seq(["MONITORING", "WARNING", "INTERVENTION", "RELEASED"] + ["MONITORING"] * 8, base_ns=P0)
    received = [produced[0]] + produced[2:7]  # frame 2 (early, well inside coverage) is missing
    run = _vc015_base(tmp_path, produced, received, logcat=phase_logcat(P0 - 50_000_000))
    _truncate_received(run, received)
    assert evaluators.evaluate_source_order(run).outcome == outcome.FAIL


def test_vc015_e6_layer_caused_phase_end_fails(tmp_path):
    payloads = frames_seq()
    logcat = phase_logcat(P0 - 50_000_000, P0 + 300_000_000, layer_caused=True, cause="timeout")
    run = _vc015_base(tmp_path, payloads, payloads, logcat=logcat)
    assert evaluators.evaluate_source_order(run).outcome == outcome.FAIL


def test_vc015_e5_ingress_disconnect_is_inconclusive(tmp_path):
    payloads = frames_seq()
    logcat = phase_logcat(P0 - 50_000_000, P0 + 300_000_000, layer_caused=False, client_connected=False,
                          cause="client_lost")
    run = _vc015_base(tmp_path, payloads, payloads, logcat=logcat)
    assert evaluators.evaluate_source_order(run).outcome == outcome.INCONCLUSIVE


def test_vc015_e7_frames_produced_before_the_phase_are_not_required(tmp_path):
    produced = frames_seq(["MONITORING"] * 3 + STAGES, base_ns=P0)  # first 3 produced before the phase
    received = produced[3:]
    # The phase starts at the 4th produced frame's timestamp.
    phase_start = P0 + 3 * 100_000_000
    run = _vc015_base(tmp_path, produced, received, logcat=phase_logcat(phase_start))
    assert evaluators.evaluate_source_order(run).outcome == outcome.PASS


def test_vc015_e8_capture_gap_suppresses_the_completeness_fail(tmp_path):
    payloads = frames_seq()
    run = write(
        tmp_path,
        produced__pcap=b.pcap(b.stream_records(4721, payloads, t0=P0)),
        received__pcap=b.pcap(b.stream_records(4731, payloads, t0=P0 + 5_000_000, drop_index=2)),
        settings__json=settings(),
        frame_assembler_clients__json={"adapter_only": True},
        **{"relay-logcat.txt": phase_logcat(P0 - 50_000_000)},
    )
    clocks(run)
    assert evaluators.evaluate_source_order(evaluators.load_run(run)).outcome == outcome.INCONCLUSIVE


def test_vc015_data_loss_in_the_event_fails(tmp_path):
    payloads = frames_seq()
    logcat = phase_logcat(P0 - 50_000_000, extra=[b.data_loss_line(P0 + 100_000_000)])
    run = _vc015_base(tmp_path, payloads, payloads, logcat=logcat)
    assert evaluators.evaluate_source_order(run).outcome == outcome.FAIL


def test_vc015_e9_second_client_is_inconclusive(tmp_path):
    payloads = frames_seq()
    run = _vc015_base(tmp_path, payloads, payloads, logcat=phase_logcat(P0 - 50_000_000), adapter_only=False)
    assert evaluators.evaluate_source_order(run).outcome == outcome.INCONCLUSIVE


def test_vc015_missing_clock_is_inconclusive(tmp_path):
    payloads = frames_seq()
    run = _vc015_base(tmp_path, payloads, payloads, logcat=phase_logcat(P0 - 50_000_000), with_clock=False)
    assert evaluators.evaluate_source_order(run).outcome == outcome.INCONCLUSIVE


def test_vc015_zero_relay_events_is_inconclusive(tmp_path):
    payloads = frames_seq()
    run = _vc015_base(tmp_path, payloads, payloads, logcat="2.0  1000  1234  1250 I other: hello\n")
    assert evaluators.evaluate_source_order(run).outcome == outcome.INCONCLUSIVE


def test_vc015_e10_malformed_received_frame_is_error_not_crash(tmp_path):
    payloads = frames_seq()
    garbage = b"\x08\x01\x18\xff"  # schema_major 1 then a truncated varint
    received = payloads[:2] + [garbage] + payloads[2:]
    run = _vc015_base(tmp_path, payloads, received, logcat=phase_logcat(P0 - 50_000_000))
    assert evaluators.evaluate_source_order(run).outcome == outcome.ERROR


def test_vc015_e11_out_of_order_duplicate_fails(tmp_path):
    payloads = frames_seq()
    received = payloads[:3] + [payloads[2]] + payloads[3:]  # frame 3 delivered twice (not increasing)
    run = _vc015_base(tmp_path, payloads, received, logcat=phase_logcat(P0 - 50_000_000))
    assert evaluators.evaluate_source_order(run).outcome == outcome.FAIL


# ------------------------------------------------------------ VC-MW-016

def _vc016(tmp_path, produced, received, sd_offer=None, residual=None, sd_capture=None, core_processed=None):
    files = dict(
        produced__pcap=b.pcap(b.stream_records(4721, produced, t0=P0)),
        received__pcap=b.pcap(b.stream_records(4731, received, t0=P0 + 5_000_000)),
        settings__json=settings(),
    )
    if sd_offer is not None:
        files["sd_offer__json"] = sd_offer
    if residual is not None:
        files["residual__json"] = residual
    run = evaluators.load_run(write(tmp_path, **files))
    if sd_capture is not None:
        (run.run_dir / "host-cvd-ebr.pcap").write_bytes(b.pcap(sd_capture))
    if core_processed is not None:
        (run.run_dir / "sd_core_processed.json").write_text(json.dumps(core_processed))
    return run


SD_T = P0 + 50_000_000  # the spoofed offer lands inside the produced-frame window

# sd_core_processed.json as send_sd_offer.sh writes it (review R43).
PROCESSED = {"processed": True, "status": "processed", "result": "secure_service_rejected",
             "matched_line": "1793000000.400000 812 830 W vsomeip : process_offerservice_serviceentry: "
                             "Ignoring offer of [4dee.0001]"}
UNKNOWN = {"processed": None, "status": "unknown", "result": "no_matching_line", "matched_line": None}


def _spoofed_offer_capture(offer_src_port=30490, provider="192.168.98.1"):
    """A host offer, then a spoofed IVI offer, then the core's subscribe to `provider`."""
    offer_entry = [b.sd_entry(b.SD_OFFER, 0x4DEE, 1, options=1)]
    subscribe = [b.sd_entry(b.SD_SUBSCRIBE, 0x4DEE, 1, eventgroup=1, options=1)]
    return [
        (P0 - 10_000_000, b.udp_datagram("192.168.98.1", "224.0.0.0", 30490, 30490,
                                         b.sd_message(offer_entry, [b.sd_ipv4_endpoint("192.168.98.1", 30509)]))),
        (SD_T, b.udp_datagram("192.168.98.118", "192.168.98.3", offer_src_port, 30490,
                              b.sd_message(offer_entry, [b.sd_ipv4_endpoint("192.168.98.118", 30509)]))),
        (SD_T + 2_000_000, b.udp_datagram("192.168.98.3", provider, 30490, 30490,
                                          b.sd_message(subscribe, [b.sd_ipv4_endpoint("192.168.98.3", 40001)]))),
    ]


def _good_offer():
    """A valid stimulus: a spoofed offer from the SD port in the SD capture, which the core stack processed."""
    return {"sd_capture": _spoofed_offer_capture(offer_src_port=30490), "core_processed": PROCESSED}


def test_vc016_passes_on_identical_bytes_with_a_good_offer(tmp_path):
    payloads = frames_seq()
    run = _vc016(tmp_path, payloads, payloads, **_good_offer())
    assert evaluators.evaluate_provenance(run).outcome == outcome.PASS, evaluators.evaluate_provenance(run).as_dict()


def test_vc016_byte_difference_fails(tmp_path):
    payloads = frames_seq()
    tampered = list(payloads)
    tampered[1] = b.frame(2, 2_100_000_000, stage="INTERVENTION")
    run = _vc016(tmp_path, payloads, tampered, **_good_offer())
    assert evaluators.evaluate_provenance(run).outcome == outcome.FAIL


def test_vc016_no_sd_record_is_inconclusive(tmp_path):
    payloads = frames_seq()
    run = _vc016(tmp_path, payloads, payloads)
    assert evaluators.evaluate_provenance(run).outcome == outcome.INCONCLUSIVE


def test_vc016_r49_a_written_redirect_record_is_data_only(tmp_path):
    # Review R49: sd_offer.json is data only; a redirect is failed from the SD
    # capture (test_vc016_r43_offer_processed_with_a_redirect_fails), not from a
    # written record.
    payloads = frames_seq()
    run = _vc016(tmp_path, payloads, payloads, sd_offer={"provider_after_offer": "192.168.98.118"})
    result = evaluators.evaluate_provenance(run)
    assert result.outcome == outcome.INCONCLUSIVE
    assert result.measurements["sd_offer_record"]["provider_after_offer"] == "192.168.98.118"


def test_vc016_r49_v2_b016_a_written_good_offer_record_alone_gives_no_pass(tmp_path):
    # v2 B016: no SD capture, an sd_offer.json naming 192.168.98.1. Neither R43
    # condition is shown (source port 30490, a stack-processed record), so the
    # record is data only and the run shows nothing.
    payloads = frames_seq()
    run = _vc016(tmp_path, payloads, payloads, sd_offer={"provider_after_offer": "192.168.98.1",
                                                         "offer_time_ns": P0 + 150_000_000})
    result = evaluators.evaluate_provenance(run)
    assert result.outcome == outcome.INCONCLUSIVE, result.as_dict()
    assert any(f.code == "sd-offer" and "data only" in f.message for f in result.findings)


def test_vc016_rg_unproduced_received_frame_fails(tmp_path):
    payloads = frames_seq()
    injected = payloads[:3] + [b.frame(999, 9_000_000_000)] + payloads[3:]
    run = _vc016(tmp_path, payloads, injected, **_good_offer())
    assert evaluators.evaluate_provenance(run).outcome == outcome.FAIL


def test_vc016_r43_offer_from_the_sd_port_processed_and_no_redirect_passes(tmp_path):
    payloads = frames_seq()
    run = _vc016(tmp_path, payloads, payloads, sd_capture=_spoofed_offer_capture(offer_src_port=30490),
                 core_processed=PROCESSED)
    assert evaluators.evaluate_provenance(run).outcome == outcome.PASS, evaluators.evaluate_provenance(run).as_dict()


def test_vc016_r43_offer_from_an_ephemeral_source_port_is_inconclusive(tmp_path):
    # send_sd_offer sent from an ephemeral port: the stack ignores it, so it is
    # not a valid stimulus (R43).
    payloads = frames_seq()
    run = _vc016(tmp_path, payloads, payloads, sd_capture=_spoofed_offer_capture(offer_src_port=45678),
                 core_processed=PROCESSED)
    result = evaluators.evaluate_provenance(run)
    assert result.outcome == outcome.INCONCLUSIVE
    assert any("source port" in f.message for f in result.findings)


def test_vc016_r43_offer_not_shown_processed_is_inconclusive(tmp_path):
    payloads = frames_seq()
    run = _vc016(tmp_path, payloads, payloads, sd_capture=_spoofed_offer_capture(offer_src_port=30490))
    result = evaluators.evaluate_provenance(run)
    assert result.outcome == outcome.INCONCLUSIVE
    assert any("processed" in f.message for f in result.findings)


def test_vc016_r43_offer_processed_with_a_redirect_fails(tmp_path):
    payloads = frames_seq()
    run = _vc016(tmp_path, payloads, payloads,
                 sd_capture=_spoofed_offer_capture(offer_src_port=30490, provider="192.168.98.118"),
                 core_processed=PROCESSED)
    assert evaluators.evaluate_provenance(run).outcome == outcome.FAIL


def test_vc016_r43_a_redirect_in_the_capture_fails_even_without_a_processed_record(tmp_path):
    # The core subscribing to the spoofed provider shows by itself that the stack
    # took the offer; a missing log line must not hide that failure.
    payloads = frames_seq()
    for name, record in (("none", None), ("unknown", UNKNOWN)):
        run = _vc016(tmp_path / name, payloads, payloads,
                     sd_capture=_spoofed_offer_capture(offer_src_port=30490, provider="192.168.98.118"),
                     core_processed=record)
        assert evaluators.evaluate_provenance(run).outcome == outcome.FAIL, name


def test_vc016_r43_an_ignored_offer_is_inconclusive(tmp_path):
    payloads = frames_seq()
    ignored = {"processed": False, "status": "ignored", "result": "unknown_port",
               "matched_line": "1793000000.2 812 830 E vsomeip : Ignored SD message from unknown port (45678)"}
    run = _vc016(tmp_path, payloads, payloads, sd_capture=_spoofed_offer_capture(offer_src_port=30490),
                 core_processed=ignored)
    result = evaluators.evaluate_provenance(run)
    assert result.outcome == outcome.INCONCLUSIVE
    assert any("ignored the offer" in f.message for f in result.findings)


def test_vc016_r43_an_unknown_record_is_inconclusive(tmp_path):
    payloads = frames_seq()
    run = _vc016(tmp_path, payloads, payloads, sd_capture=_spoofed_offer_capture(offer_src_port=30490),
                 core_processed=UNKNOWN)
    result = evaluators.evaluate_provenance(run)
    assert result.outcome == outcome.INCONCLUSIVE
    assert any("no matching line" in f.message for f in result.findings)


def test_vc016_r43_a_bare_processed_flag_without_its_line_is_inconclusive(tmp_path):
    payloads = frames_seq()
    run = _vc016(tmp_path, payloads, payloads, sd_capture=_spoofed_offer_capture(offer_src_port=30490),
                 core_processed={"processed": True})
    assert evaluators.evaluate_provenance(run).outcome == outcome.INCONCLUSIVE


def test_vc016_b1_frames_produced_after_the_guest_capture_ended_are_not_a_stop(tmp_path):
    # B1: the guest capture was cut mid-stream (no FIN) after frame 7, so the
    # stack produced frames 8-12 after the capture ended. They are beyond the
    # capture's coverage, not a stop after the offer; a clean run passes.
    produced = frames_seq(["MONITORING", "WARNING", "INTERVENTION", "RELEASED"] + ["MONITORING"] * 8, base_ns=P0)
    run = _vc016(tmp_path, produced, produced[:7], **_good_offer())
    (run.run_dir / "received.pcap").write_bytes(b.pcap(b.stream_records(4731, produced[:7], t0=P0 + 5_000_000)[:-1]))
    assert evaluators.evaluate_provenance(run).outcome == outcome.PASS, evaluators.evaluate_provenance(run).as_dict()


# ------------------------------------------------------------ VC-MW-017
#
# These cases feed the probe artifacts of the new contract (probe.py): the
# firewall validity record, the per-probe observation (send status, the
# capture witness in captured_markers.json, the drop-counter delta) and the
# control with its capture, counter and delivery. The detailed judgement is
# in tests/test_probe.py; these cover the outcome mapping of the case.

def _marker(port, guest="ivi", iface="eth1", host="192.168.98.1"):
    # Markers are opaque strings to the evaluator; this keeps the base fixture's
    # marker form of the earlier rounds ("ivi-eth1-30160"), which the reviewers'
    # repros build on. The probe script writes "MARK:<guest>-<if>-<addr>-<port>".
    return f"{guest}-{iface}-{port}"


IVI_MAC = "00:1a:11:e1:cf:02"


def _udp_probe(port, *, counter=True, sent="sent", guest="ivi", iface="eth1", host="192.168.98.1"):
    return {"guest": guest, "netns": "-", "interface": iface, "src_addr": "192.168.98.118", "src_mac": IVI_MAC,
            "host": host, "port": port, "protocol": "udp", "marker": _marker(port, guest, iface, host),
            "send_status": sent, "counter_moved": counter, "guest_connected": None}


def _udp_copy(attempt, capture_interface="cvd-ebr"):
    # What hostscan records for a captured probe: it left on the named guest
    # interface (its MAC) from the named source (review R41).
    return {"marker": attempt["marker"], "capture_interface": capture_interface, "src": attempt["src_addr"],
            "src_mac": attempt["src_mac"], "dst": attempt["host"], "sport": 40000, "dport": attempt["port"],
            "vlans": []}


def _full_isolation_artifacts(reached_udp=(), connected_4721=False, host="192.168.98.1", guest="ivi", iface="eth1"):
    """Attempts and captured copies covering the full DDS set plus 4721 for one
    (guest, interface, host) pair, all isolated unless a port is marked reached
    (review R45: a pass needs the whole set probed), each captured as named (R41)."""
    reached = set(reached_udp)
    attempts = [_udp_probe(port, counter=port not in reached, guest=guest, iface=iface, host=host)
                for port in probe.dds_udp_ports()]
    captured = {"udp_markers": [a["marker"] for a in attempts], "udp_captures": [_udp_copy(a) for a in attempts]}
    attempts.append({"guest": guest, "netns": "-", "interface": iface, "src_addr": "192.168.98.118",
                     "src_mac": IVI_MAC, "host": host, "port": 4721, "sport": 28001, "protocol": "tcp",
                     "marker": _marker(4721, guest, iface, host), "send_status": "sent",
                     "counter_moved": not connected_4721, "guest_connected": connected_4721})
    captured["tcp_syns"] = [{"host": host, "port": 4721, "src": "192.168.98.118", "sport": 28001,
                             "src_mac": IVI_MAC, "capture_interface": "cvd-ebr"}]
    return attempts, captured


def _vc017(tmp_path, *, reached_udp=(), connected_4721=False, **files):
    attempts, captured = _full_isolation_artifacts(reached_udp, connected_4721)
    base = dict(
        firewall__json={"inet_table_present": True, "dds_counters_readable": True, "tcp_counters_readable": True},
        host_listeners__json=[{"address": "0.0.0.0", "port": 30160, "protocol": "udp", "element": "de4sdv_score_ad",
                               "pid": 11, "element_in_layer": True}],
        probe_attempts__json=attempts,
        captured_markers__json=captured,
        control__json={"captured": True, "counter_moved": False, "delivered": True, "detail": "control arrived"},
        coverage__json={"per_guest": {"ivi": {"expected_interfaces": ["eth1"],
                                              "expected_host_addresses": ["192.168.98.1"]}}},
        asm_mw_031__json={"holds": True},
        inspection__json={"no_host_endpoint": True, "inspector": "bench"},
        dds_range__json={"domain": 91, "max_participant_index": 120, "ports": probe.dds_udp_ports()},
    )
    base.update(files)
    return evaluators.load_run(write(tmp_path, **base))


def test_vc017_passes_when_the_firewall_drops_every_probe(tmp_path):
    run = _vc017(tmp_path)
    assert evaluators.evaluate_isolation(run).outcome == outcome.PASS, evaluators.evaluate_isolation(run).as_dict()


def test_vc017_no_firewall_table_is_inconclusive(tmp_path):
    run = _vc017(tmp_path,
                 firewall__json={"inet_table_present": False, "dds_counters_readable": False,
                                 "tcp_counters_readable": False},
                 probe_attempts__json=[_udp_probe(30160, counter=None)],
                 control__json={"captured": True, "counter_moved": None, "delivered": True, "detail": "no table"})
    assert evaluators.evaluate_isolation(run).outcome == outcome.INCONCLUSIVE


def test_vc017_e12_layer_port_reached_fails_even_if_control_fails(tmp_path):
    # The full set is probed; layer port 30160 is reached (captured, not dropped).
    run = _vc017(tmp_path, reached_udp=(30160,),
                 control__json={"captured": False, "counter_moved": None, "delivered": False, "detail": "control lost"})
    assert evaluators.evaluate_isolation(run).outcome == outcome.FAIL


def test_vc017_e13_only_4721_reached_is_not_a_requirement_failure(tmp_path):
    # Every DDS port is isolated; only :4721 connects. An ASM-MW-029 finding, not
    # a REQ-MW-016 failure, and the full set is covered, so the case passes.
    run = _vc017(tmp_path, connected_4721=True,
                 host_listeners__json=[{"address": "0.0.0.0", "port": 4721, "protocol": "tcp", "element": "python3",
                                        "pid": 12, "element_in_layer": False}])
    res = evaluators.evaluate_isolation(run)
    assert res.outcome == outcome.PASS, res.as_dict()
    assert res.measurements.get("asm_mw_029_findings")


def test_vc017_other_process_reachable_fails_only_when_asm031_holds(tmp_path):
    listeners = [{"address": "0.0.0.0", "port": 30161, "protocol": "udp", "element": "component_conta",
                  "pid": 13, "element_in_layer": False}]
    holds = _vc017(tmp_path / "a", reached_udp=(30161,), host_listeners__json=listeners,
                   asm_mw_031__json={"holds": True})
    assert evaluators.evaluate_isolation(holds).outcome == outcome.FAIL
    not_shown = _vc017(tmp_path / "b", reached_udp=(30161,), host_listeners__json=listeners,
                       asm_mw_031__json={"holds": False})
    assert evaluators.evaluate_isolation(not_shown).outcome == outcome.INCONCLUSIVE


def test_vc017_control_failure_is_inconclusive(tmp_path):
    run = _vc017(tmp_path, control__json={"captured": False, "counter_moved": None, "delivered": False,
                                          "detail": "no control"})
    assert evaluators.evaluate_isolation(run).outcome == outcome.INCONCLUSIVE


def test_vc017_control_captured_but_not_delivered_is_inconclusive(tmp_path):
    # fw_emul_ctrl_blocked: the control was captured and not dropped by the bench rule, but not delivered.
    run = _vc017(tmp_path, control__json={"captured": True, "counter_moved": False, "delivered": False,
                                          "detail": "control datagram not delivered"})
    assert evaluators.evaluate_isolation(run).outcome == outcome.INCONCLUSIVE


def test_vc017_coverage_gap_is_inconclusive(tmp_path):
    run = _vc017(tmp_path, coverage__json={"per_guest": {"ivi": {
        "expected_interfaces": ["eth1", "buried_eth0"], "probed_interfaces": ["eth1"],
        "expected_host_addresses": ["192.168.98.1"], "probed_host_addresses": ["192.168.98.1"]}}})
    assert evaluators.evaluate_isolation(run).outcome == outcome.INCONCLUSIVE


def test_vc017_missing_inspection_is_inconclusive(tmp_path):
    run = write(tmp_path,
                firewall__json={"inet_table_present": True, "dds_counters_readable": True,
                                "tcp_counters_readable": True},
                host_listeners__json=[],
                probe_attempts__json=[_udp_probe(30160, counter=True)],
                captured_markers__json={"udp_markers": [_marker(30160)], "tcp_syns": []},
                control__json={"captured": True, "counter_moved": False, "delivered": True, "detail": "ok"},
                coverage__json={"per_guest": {"ivi": {"expected_interfaces": ["eth1"], "probed_interfaces": ["eth1"],
                                                      "expected_host_addresses": ["192.168.98.1"],
                                                      "probed_host_addresses": ["192.168.98.1"]}}},
                asm_mw_031__json={"holds": True})
    assert evaluators.evaluate_isolation(evaluators.load_run(run)).outcome == outcome.INCONCLUSIVE


# ------------------------------------------------------------ VC-MW-020

T_SUB = 1_793_000_000_000_000_000  # IVI VM clock of a new subscription, 2026-10


def _served_frames(received_records) -> list[tuple[int, bytes]]:
    """(capture time, frame bytes) of each frame the relay served in a received stream (builder records)."""
    from de4sdv_broker_path_bench.pcap import Packet, decode
    served = []
    for ts, raw in sorted(received_records):
        item = decode(Packet(ts, 1, raw, len(raw)))
        if item is not None and item.protocol == "tcp" and item.sport == 4731 and len(item.payload) > 4:
            served.append((ts, item.payload[4:]))
    return served


def _dt_stream(served, open_ns) -> bytes:
    """A Data Tunnel capture: the IVI agent opens one stream at ``open_ns``; the core carries each served frame."""
    conn = b.DtConnection(open_ns - 30_000_000).handshake().open_stream(1, open_ns, preface=True).server_settings()
    for ts, payload in served:
        conn.data(1, payload, max(ts - 1_000_000, open_ns + 1_000_000))
    return b.dt_capture([conn])


def _vc020(tmp_path, received_records, logcat, condition="hmi_down", offset_ns=2_000_000, with_clock=True,
           dt="before"):
    """A VC-MW-020 run. ``dt`` gives its Data Tunnel capture (VC-MW-020's second start): "before" opens the
    stream 100 ms before the first phase start, so the second check equals the first; None writes none."""
    run = write(tmp_path, received__pcap=b.pcap(received_records),
                settings__json=settings(condition=condition),
                **{"relay-logcat.txt": logcat})
    if with_clock:
        (run / "clock-start.pcap").write_bytes(b.clock_pcap(offset_ns, T_SUB - 60_000_000_000, 0x1111))
        (run / "clock-end.pcap").write_bytes(b.clock_pcap(offset_ns, T_SUB + 60_000_000_000, 0x2222))
    if dt == "before":
        starts = [int(line.split('"phase_start_realtime_ns":')[1].split(",")[0].rstrip("}"))
                  for line in logcat.splitlines() if '"event":"phase_start"' in line]
        open_ns = (min(starts) if starts else T_SUB) - 100_000_000
        (run / "data-tunnel-vlan2.pcap").write_bytes(_dt_stream(_served_frames(received_records), open_ns))
    return evaluators.load_run(run)


def test_vc020_passes_when_frames_follow_the_subscription(tmp_path):
    payloads = [b.frame(i, T_SUB + 50_000_000 + i * 100_000_000) for i in range(1, 4)]
    records = b.stream_records(4731, payloads, t0=T_SUB + 40_000_000)
    run = _vc020(tmp_path, records, phase_logcat(T_SUB, phase=1))
    assert evaluators.evaluate_unsubscribed_discard(run).outcome == outcome.PASS, \
        evaluators.evaluate_unsubscribed_discard(run).as_dict()


def test_vc020_ra_old_frame_in_second_phase_fails(tmp_path):
    # Two phases; a frame produced 2 s before the second start is served in it.
    s2 = T_SUB + 30_000_000_000
    old = b.frame(500, s2 - 2_000_000_000)
    records = b.stream_records(4731, [old], t0=s2 + 100_000_000)
    logcat = (phase_logcat(T_SUB, T_SUB + 10_000_000_000, phase=1, layer_caused=False, client_connected=False,
                           cause="client_lost")
              + phase_logcat(s2, phase=2))
    run = _vc020(tmp_path, records, logcat)
    assert evaluators.evaluate_unsubscribed_discard(run).outcome == outcome.FAIL


def test_vc020_rv_zero_frames_in_phase_is_inconclusive(tmp_path):
    records = b.stream_records(4731, [b.frame(1, T_SUB - 100_000_000)], t0=T_SUB - 200_000_000)  # before the phase
    run = _vc020(tmp_path, records, phase_logcat(T_SUB))
    assert evaluators.evaluate_unsubscribed_discard(run).outcome == outcome.INCONCLUSIVE


def test_vc020_e4_clock_step_in_phase_is_inconclusive(tmp_path):
    payloads = [b.frame(i, T_SUB + 50_000_000 + i * 100_000_000) for i in range(1, 4)]
    records = b.stream_records(4731, payloads, t0=T_SUB + 40_000_000)
    logcat = phase_logcat(T_SUB, extra=[b.clock_step_line(T_SUB + 500_000_000, in_phase=True)])
    run = _vc020(tmp_path, records, logcat)
    assert evaluators.evaluate_unsubscribed_discard(run).outcome == outcome.INCONCLUSIVE


def test_vc020_rb_raw_comparison_flags_an_offset_hidden_violation(tmp_path):
    # Frame stamped 30 ms (host clock) before the guest phase start, guest clock +15 ms ahead.
    # Raw comparison (no offset correction) sees 30 ms > 20 ms -> violation. The PR corrected by
    # the offset and passed; the rule and VC-MW-020 compare raw.
    frame = b.frame(7, T_SUB - 30_000_000)
    records = b.stream_records(4731, [frame], t0=T_SUB + 100_000_000)
    run = _vc020(tmp_path, records, phase_logcat(T_SUB), offset_ns=15_000_000)
    assert evaluators.evaluate_unsubscribed_discard(run).outcome == outcome.FAIL


def test_vc020_clock_failure_suppresses_a_small_violation_to_inconclusive(tmp_path):
    # A failed ASM-MW-030 (50 ms offset) suppresses a violation that is within the
    # clock offset plus uncertainty plus 20 ms: it may be only the clock (review R19).
    frame = b.frame(7, T_SUB - 40_000_000)  # 40 ms before the start, below 20 + 50 + uncertainty
    # The normal order: the ingress connects (accept at T_SUB - 70 ms), then the
    # relay logs the phase start, so the judged start is the relay's.
    records = b.stream_records(4731, [frame], t0=T_SUB - 100_000_000)
    run = _vc020(tmp_path, records, phase_logcat(T_SUB), offset_ns=50_000_000)  # ASM-MW-030 fails
    assert evaluators.evaluate_unsubscribed_discard(run).outcome == outcome.INCONCLUSIVE


def test_vc020_clock_independent_violation_fails_even_when_asm030_fails(tmp_path):
    # N-5: a frame produced 5 s before the start is far outside the offset plus
    # uncertainty plus 20 ms, so it fails whatever ASM-MW-030 shows (review R19).
    frame = b.frame(7, T_SUB - 5_000_000_000)
    records = b.stream_records(4731, [frame], t0=T_SUB + 100_000_000)
    run = _vc020(tmp_path, records, phase_logcat(T_SUB), offset_ns=30_000_000)  # ASM-MW-030 fails
    assert evaluators.evaluate_unsubscribed_discard(run).outcome == outcome.FAIL


def test_vc020_rw_unnamed_condition_is_inconclusive(tmp_path):
    payloads = [b.frame(i, T_SUB + 50_000_000 + i * 100_000_000) for i in range(1, 4)]
    records = b.stream_records(4731, payloads, t0=T_SUB + 40_000_000)
    run = _vc020(tmp_path, records, phase_logcat(T_SUB), condition=None)
    assert evaluators.evaluate_unsubscribed_discard(run).outcome == outcome.INCONCLUSIVE


def test_run_cli_reports_each_case(tmp_path):
    from de4sdv_broker_path_bench import run
    payloads = frames_seq()
    write(tmp_path,
          produced__pcap=b.pcap(b.stream_records(4721, payloads, t0=P0)),
          received__pcap=b.pcap(b.stream_records(4731, payloads, t0=P0 + 5_000_000)),
          settings__json=settings(),
          frame_assembler_clients__json={"adapter_only": True},
          **{"relay-logcat.txt": phase_logcat(P0 - 50_000_000)})
    clocks(tmp_path)
    assert run.main([str(tmp_path), "--case", "VC-MW-015"]) == 0


# ------------------------------------------- VC-MW-015/016/020 delta regressions
# Each is a false pass or false fail the two delta reviews of this bench cited; it is
# built from real pcap and logcat shapes (builders emit real bytes and lines),
# not synthesized verdicts, so the judgement is exercised end to end.


def test_vc015_r32_layer_caused_phase_end_before_the_event_passes(tmp_path):
    # E6c: a layer-caused phase end 60 s before the AEBS event is outside it (R32).
    payloads = frames_seq()
    early = (b.phase_start_line(P0 - 120_000_000_000, phase=1)
             + "\n" + b.phase_end_line(P0 - 60_000_000_000, P0 - 120_000_000_000, phase=1, layer_caused=True,
                                       client_connected=True, cause="timeout")
             + "\n" + b.phase_start_line(P0 - 50_000_000, phase=2) + "\n")
    run = _vc015_base(tmp_path, payloads, payloads, logcat=early)
    assert evaluators.evaluate_source_order(run).outcome == outcome.PASS


def test_vc015_r32_data_loss_before_the_event_passes(tmp_path):
    # E19: a DATA_LOSS 60 s before the event is outside it (R32).
    payloads = frames_seq()
    logcat = phase_logcat(P0 - 50_000_000, extra=[b.data_loss_line(P0 - 60_000_000_000)])
    run = _vc015_base(tmp_path, payloads, payloads, logcat=logcat)
    assert evaluators.evaluate_source_order(run).outcome == outcome.PASS


def test_vc015_r14_frame_in_the_band_before_the_phase_is_not_required(tmp_path):
    # N-1: frame 3 produced 10 ms before the phase start (in the 20 ms band) and
    # dropped by the relay is not required (R14).
    payloads = frames_seq()
    phase_start = P0 + 210_000_000  # 10 ms after frame 3 (P0 + 200 ms) was produced
    run = _vc015_base(tmp_path, payloads, payloads[3:], logcat=phase_logcat(phase_start))
    assert evaluators.evaluate_source_order(run).outcome == outcome.PASS


def test_vc015_r35_second_client_in_produced_pcap_is_inconclusive(tmp_path):
    # E9a: a second :4721 client is visible in produced.pcap though the ss record
    # says adapter_only; the missing frames are that client's (R35).
    payloads = frames_seq()
    adapter = payloads[:3] + payloads[5:]
    other = payloads[3:5]
    produced_records = (b.stream_records(4721, adapter, t0=P0, cport=50000)
                        + b.stream_records(4721, other, t0=P0 + 300_000_000, cport=50009))
    run = write(
        tmp_path,
        produced__pcap=b.pcap(sorted(produced_records)),
        received__pcap=b.pcap(b.stream_records(4731, adapter, t0=P0 + 5_000_000)),
        settings__json=settings(),
        frame_assembler_clients__json={"adapter_only": True},
        **{"relay-logcat.txt": phase_logcat(P0 - 50_000_000)},
    )
    clocks(run)
    assert evaluators.evaluate_source_order(evaluators.load_run(run)).outcome == outcome.INCONCLUSIVE


def test_vc015_r31_mid_stream_capture_with_all_frames_passes(tmp_path):
    # M1: the guest capture joined the ingress connection mid-stream (the
    # documented window); no frame of the event is missing (R31).
    payloads = frames_seq()
    sender = b.TcpSender("127.0.0.1", "127.0.0.1", 50001, 4731, P0 - 30_000_000)  # no handshake: mid-stream
    sender.sseq = 77_000
    records = []
    for i, payload in enumerate(payloads):
        data = b.delimited(payload)
        records.append((P0 + 5_000_000 + i * 100_000_000,
                        b.tcp_segment("127.0.0.1", "127.0.0.1", 4731, 50001, sender.sseq, 1, b.PSH | b.ACK, data)))
        sender.sseq += len(data)
    run = write(
        tmp_path,
        produced__pcap=b.pcap(b.stream_records(4721, payloads, t0=P0)),
        received__pcap=b.pcap(records),
        settings__json=settings(),
        frame_assembler_clients__json={"adapter_only": True},
        **{"relay-logcat.txt": phase_logcat(P0 - 50_000_000)},
    )
    clocks(run)
    assert evaluators.evaluate_source_order(evaluators.load_run(run)).outcome == outcome.PASS


def test_vc016_r8b_frames_stop_after_the_offer_fails(tmp_path):
    # R-S2: frames 1-3 of 6 arrive, then the stack keeps producing but nothing
    # more arrives; the provider stayed .1 (R8b).
    payloads = frames_seq()
    run = _vc016(tmp_path, payloads, payloads[:3], **_good_offer())
    assert evaluators.evaluate_provenance(run).outcome == outcome.FAIL


def test_vc016_r34_empty_offer_record_is_inconclusive(tmp_path):
    # E17: an sd_offer.json with no provider after the offer is missing evidence (R34).
    payloads = frames_seq()
    run = _vc016(tmp_path, payloads, payloads, sd_offer={})
    assert evaluators.evaluate_provenance(run).outcome == outcome.INCONCLUSIVE


def _records_with_gap(payloads, p0):
    # A received stream of all frames with a 600 ms gap between frame 2 and 3.
    sender = b.TcpSender("127.0.0.1", "127.0.0.1", 50001, 4731, p0).handshake()
    for i, payload in enumerate(payloads):
        step = 600_000_000 if i == 2 else 100_000_000
        sender.send(b.delimited(payload), step_ns=step)
    sender.fin()
    return sender.records


def test_vc016_r34_gap_without_an_offer_time_is_inconclusive(tmp_path):
    # E18: a 600 ms receipt gap with a record that has no offer time: whether it
    # follows the offer is unknown (R34).
    payloads = frames_seq()
    run = write(
        tmp_path,
        produced__pcap=b.pcap(b.stream_records(4721, payloads, t0=P0)),
        received__pcap=b.pcap(_records_with_gap(payloads, P0 + 5_000_000)),
        settings__json=settings(),
        sd_offer__json={"provider_after_offer": "192.168.98.1"},
    )
    assert evaluators.evaluate_provenance(evaluators.load_run(run)).outcome == outcome.INCONCLUSIVE


def test_vc020_r33_capture_accept_later_than_relay_start_fails(tmp_path):
    # E16: the relay log says the phase started at T0, but the loopback accept is
    # 230 ms later, and the frame was produced before that accept (R33).
    frame = b.frame(30, T_SUB + 100_000_000)
    records = b.stream_records(4731, [frame], t0=T_SUB + 200_000_000)  # accept (ACK) at T_SUB + 230 ms
    run = _vc020(tmp_path, records, phase_logcat(T_SUB))
    assert evaluators.evaluate_unsubscribed_discard(run).outcome == outcome.FAIL


def test_vc020_r33_judged_start_is_the_later_of_relay_start_and_accept(tmp_path):
    # Decision on R33: no tolerance. The judged start is the later of the relay's
    # phase start and the ingress's loopback accept; a relay that claims a start
    # 60 ms before the ingress connected is judged against the accept.
    frame = b.frame(31, T_SUB + 20_000_000)  # produced 20 ms after the relay's start, 40 ms before the accept
    records = b.stream_records(4731, [frame], t0=T_SUB + 30_000_000)  # accept (ACK) at T_SUB + 60 ms
    run = _vc020(tmp_path, records, phase_logcat(T_SUB))
    assert evaluators.evaluate_unsubscribed_discard(run).outcome == outcome.FAIL


def test_vc020_r33_records_both_starts_and_their_difference(tmp_path):
    frame = b.frame(30, T_SUB + 100_000_000)
    records = b.stream_records(4731, [frame], t0=T_SUB + 200_000_000)  # accept (ACK) at T_SUB + 230 ms
    run = _vc020(tmp_path, records, phase_logcat(T_SUB))
    starts = evaluators.evaluate_unsubscribed_discard(run).measurements["phase_starts"]
    assert starts == [{"pid": 1234, "phase": 1, "connection": 0, "relay_start_ns": T_SUB,
                       "accept_ns": T_SUB + 230_000_000, "accept_minus_relay_ns": 230_000_000,
                       "judged_start_ns": T_SUB + 230_000_000, "judged_start_known": True}]


def _mid_stream(items, cport=50002):
    """A loopback stream the capture joined mid-stream (no handshake): (delivered_ns, frame) pairs."""
    seq, records = 77_000, []
    for delivered_ns, payload in items:
        data = b.delimited(payload)
        records.append((delivered_ns, b.tcp_segment("127.0.0.1", "127.0.0.1", 4731, cport, seq, 1,
                                                    b.PSH | b.ACK, data)))
        seq += len(data)
    return records


def test_vc020_r33_no_accept_and_first_seen_after_the_relay_start_is_inconclusive(tmp_path):
    # The capture joined the connection after the relay's start: the accept is
    # not in the capture, and the capture may have missed the start of the
    # phase, so a frame that looks fresh is no pass.
    records = _mid_stream([(T_SUB + 100_000_000, b.frame(40, T_SUB + 10_000_000))])
    run = _vc020(tmp_path, records, phase_logcat(T_SUB))
    result = evaluators.evaluate_unsubscribed_discard(run)
    assert result.outcome == outcome.INCONCLUSIVE, result.as_dict()
    assert result.measurements["phase_starts"][0]["judged_start_known"] is False
    assert result.measurements["phase_starts"][0]["accept_ns"] is None


def test_vc020_r33_no_accept_still_fails_a_frame_older_than_the_relay_start(tmp_path):
    # The judged start is never earlier than the relay's start, so a frame far
    # older than the relay's start fails without the accept.
    records = _mid_stream([(T_SUB + 100_000_000, b.frame(41, T_SUB - 300_000_000))])
    run = _vc020(tmp_path, records, phase_logcat(T_SUB))
    assert evaluators.evaluate_unsubscribed_discard(run).outcome == outcome.FAIL


def test_vc020_r33_no_accept_but_seen_before_the_relay_start_keeps_it(tmp_path):
    # A new phase on a connection the capture saw before the relay's start: the
    # accept is earlier than that first packet, so the later time is the relay's.
    records = _mid_stream([(T_SUB - 200_000_000, b.frame(42, T_SUB - 250_000_000)),  # before the phase: not judged
                           (T_SUB + 100_000_000, b.frame(43, T_SUB + 50_000_000))])
    run = _vc020(tmp_path, records, phase_logcat(T_SUB))
    result = evaluators.evaluate_unsubscribed_discard(run)
    assert result.outcome == outcome.PASS, result.as_dict()
    assert result.measurements["phase_starts"] == [
        {"pid": 1234, "phase": 1, "connection": 0, "relay_start_ns": T_SUB, "accept_ns": None,
         "accept_minus_relay_ns": None, "judged_start_ns": T_SUB, "judged_start_known": True}]


def test_vc020_r33_normal_order_keeps_the_relay_start(tmp_path):
    # R-U in the normal order: the ingress connects, then the relay logs the
    # phase start; the max is the relay's own start, so a fresh frame produced
    # after it passes, and an old-phase frame delivered in phase 1 is not
    # judged against phase 2.
    s2 = T_SUB + 30_000_000_000
    old = b.stream_records(4731, [b.frame(1, s2 - 21_000_000_000)], t0=T_SUB - 40_000_000, cport=42001)
    fresh = b.stream_records(4731, [b.frame(2, s2 + 30_000_000)], t0=s2 - 40_000_000, cport=42002)
    logcat = (phase_logcat(T_SUB, T_SUB + 10_000_000_000, phase=1, client_connected=False, cause="client_lost")
              + phase_logcat(s2, phase=2))
    run = _vc020(tmp_path, sorted(old + fresh), logcat)
    result = evaluators.evaluate_unsubscribed_discard(run)
    assert result.outcome == outcome.PASS, result.as_dict()
    assert all(entry["judged_start_ns"] == entry["relay_start_ns"] for entry in result.measurements["phase_starts"])


def test_vc020_e3b_frame_within_the_margin_of_the_relay_start_passes(tmp_path):
    # E3b in the normal order: guest clock -10 ms, a frame stamped 15 ms before the
    # relay's start, compared raw; within the 20 ms margin.
    frame = b.frame(8, T_SUB - 15_000_000)
    records = b.stream_records(4731, [frame], t0=T_SUB - 100_000_000)  # accept at T_SUB - 70 ms
    run = _vc020(tmp_path, records, phase_logcat(T_SUB), offset_ns=-10_000_000)
    assert evaluators.evaluate_unsubscribed_discard(run).outcome == outcome.PASS



def test_vc020_capture_gap_is_no_pass(tmp_path):
    # G1: received.pcap lost a segment; the lost frame may be one produced before
    # the new subscription, so clean captured frames are no pass.
    # Accept at T_SUB - 70 ms; frames produced 10 ms before their delivery at T_SUB + 30, 130, 230 ms.
    payloads = [b.frame(i, T_SUB - 80_000_000 + i * 100_000_000) for i in range(1, 4)]
    records = b.stream_records(4731, payloads, t0=T_SUB - 100_000_000, drop_index=1)
    run = _vc020(tmp_path, records, phase_logcat(T_SUB))
    result = evaluators.evaluate_unsubscribed_discard(run)
    assert result.outcome == outcome.INCONCLUSIVE, result.as_dict()
    assert "capture-gap" in {finding.code for finding in result.findings}


def test_vc020_capture_gap_still_fails_a_captured_old_frame(tmp_path):
    # A captured frame produced long before the subscription fails whatever the capture lost.
    payloads = [b.frame(1, T_SUB - 2_000_000_000)] + [b.frame(i, T_SUB - 80_000_000 + i * 100_000_000)
                                                     for i in range(2, 4)]
    records = b.stream_records(4731, payloads, t0=T_SUB - 100_000_000, drop_index=2)
    run = _vc020(tmp_path, records, phase_logcat(T_SUB))
    assert evaluators.evaluate_unsubscribed_discard(run).outcome == outcome.FAIL

def test_vc020_r18_ivi_vm_down_first_phase_is_data(tmp_path):
    # E15/N-4: condition 2 judges only the phase after the clock setting; a dirty
    # first phase after the reboot is data, outside the judged scope (R18).
    p1, p2 = T_SUB, T_SUB + 20_000_000_000
    bad = [b.frame(1, p1 - 300_000_000)]  # 300 ms older than the first phase start
    clean = [b.frame(10 + i, p2 + 50_000_000 + i * 100_000_000) for i in range(3)]
    logcat = (b.phase_start_line(p1, phase=1) + "\n"
              + b.phase_end_line(p1 + 10_000_000_000, p1, phase=1, layer_caused=False, client_connected=False,
                                 cause="client_lost") + "\n"
              + b.phase_start_line(p2, phase=2) + "\n")
    # The normal order: each connection's accept comes before its phase start.
    records = (b.stream_records(4731, bad, t0=p1 - 40_000_000, cport=43001)
               + b.stream_records(4731, clean, t0=p2 - 40_000_000, cport=43002))
    run = _vc020(tmp_path, sorted(records), logcat, condition="ivi_vm_down")
    assert evaluators.evaluate_unsubscribed_discard(run).outcome == outcome.PASS


def test_vc020_r30_clock_step_in_the_unjudged_first_phase_does_not_void(tmp_path):
    # E15b: the mandated clock setting steps the clock in the first (out-of-scope)
    # phase; the judged phase 2 is clean (R30).
    p1, p2 = T_SUB, T_SUB + 20_000_000_000
    first = [b.frame(1, p1 + 40_000_000)]
    clean = [b.frame(10 + i, p2 + 50_000_000 + i * 100_000_000) for i in range(3)]
    logcat = (b.phase_start_line(p1, phase=1) + "\n"
              + b.clock_step_line(p1 + 5_000_000_000, in_phase=True) + "\n"
              + b.phase_end_line(p1 + 10_000_000_000, p1, phase=1, layer_caused=False, client_connected=False,
                                 cause="client_lost", clock_steps=1) + "\n"
              + b.phase_start_line(p2, phase=2) + "\n")
    # The normal order: each connection's accept comes before its phase start.
    records = (b.stream_records(4731, first, t0=p1 - 40_000_000, cport=44001)
               + b.stream_records(4731, clean, t0=p2 - 40_000_000, cport=44002))
    run = _vc020(tmp_path, sorted(records), logcat, condition="ivi_vm_down")
    assert evaluators.evaluate_unsubscribed_discard(run).outcome == outcome.PASS


# ------------------------------------------------- VC-MW-020 case over its conditions

def _vc020_condition_run(tmp_path, condition, *, stale=False):
    first = T_SUB - 5_000_000_000 if stale else T_SUB + 50_000_000
    payloads = [b.frame(i, first + i * 100_000_000) for i in range(1, 4)]
    records = b.stream_records(4731, payloads, t0=T_SUB + 40_000_000)
    return _vc020(tmp_path, records, phase_logcat(T_SUB, phase=1), condition=condition).run_dir


def test_run_cli_one_vc020_condition_is_not_a_case_pass(tmp_path, capsys):
    # R-W / assurance R4e: one condition (one run) passing is not a case pass;
    # VC-MW-020: a pass covers the four conditions.
    from de4sdv_broker_path_bench import run
    run_dir = _vc020_condition_run(tmp_path, "hmi_down")
    code = run.main([str(run_dir), "--case", "VC-MW-020"])
    report = json.loads(capsys.readouterr().out)
    result = report["results"]["VC-MW-020"]
    assert code == 1
    assert result["outcome"] == outcome.INCONCLUSIVE
    assert result["conditions"]["hmi_down"]["outcome"] == outcome.PASS
    assert set(result["missing_conditions"]) == {"ivi_vm_down", "sdv_core_vm_down", "pair_restart"}


def test_run_cli_vc020_case_passes_only_over_all_four_conditions(tmp_path, capsys):
    from de4sdv_broker_path_bench import run
    dirs = [str(_vc020_condition_run(tmp_path / c, c))
            for c in ("hmi_down", "ivi_vm_down", "sdv_core_vm_down", "pair_restart")]
    code = run.main(["--vc020-runs", *dirs])
    result = json.loads(capsys.readouterr().out)["results"]["VC-MW-020"]
    assert code == 0 and result["outcome"] == outcome.PASS and result["missing_conditions"] == []


def test_run_cli_vc020_case_fails_when_one_condition_fails(tmp_path, capsys):
    from de4sdv_broker_path_bench import run
    dirs = [str(_vc020_condition_run(tmp_path / c, c, stale=(c == "pair_restart")))
            for c in ("hmi_down", "ivi_vm_down", "sdv_core_vm_down", "pair_restart")]
    code = run.main(["--vc020-runs", *dirs])
    result = json.loads(capsys.readouterr().out)["results"]["VC-MW-020"]
    assert code == 1 and result["outcome"] == outcome.FAIL
    assert result["conditions"]["pair_restart"]["outcome"] == outcome.FAIL


# ------------------------------------------------- R37: a new phase after the clock setting

def test_r37_new_phase_start_after_the_ingress_restart_is_found(tmp_path):
    # set_ivi_clock.sh setup restarts the ingress after the clock setting; a new
    # relay phase_start (a (pid, phase) key not in the log before) must follow.
    from de4sdv_broker_path_bench import relay_log
    before = (b.phase_start_line(T_SUB, phase=1) + "\n"
              + b.phase_end_line(T_SUB + 5_000_000_000, T_SUB, phase=1, layer_caused=False, client_connected=False,
                                 cause="client_lost") + "\n")
    after = before + b.phase_start_line(T_SUB + 6_000_000_000, phase=2) + "\n"
    (tmp_path / "before.txt").write_text(before)
    (tmp_path / "after.txt").write_text(after)
    new = relay_log.new_phase_starts(relay_log.relay_events(before.splitlines(), TAG),
                                     relay_log.relay_events(after.splitlines(), TAG))
    assert [(event["pid"], event["phase"]) for event in new] == [(1234, 2)]
    code = relay_log.main(["new-phase-start", "--tag", TAG, "--before", str(tmp_path / "before.txt"),
                           "--after", str(tmp_path / "after.txt")])
    assert code == 0


def test_r37_no_new_phase_start_is_reported(tmp_path):
    from de4sdv_broker_path_bench import relay_log
    log = b.phase_start_line(T_SUB, phase=1) + "\n"
    (tmp_path / "before.txt").write_text(log)
    (tmp_path / "after.txt").write_text(log)  # the same phase only: the ingress did not reconnect
    code = relay_log.main(["new-phase-start", "--tag", TAG, "--before", str(tmp_path / "before.txt"),
                           "--after", str(tmp_path / "after.txt")])
    assert code == 1


def test_vc020_r46_out_of_scope_phase_is_the_first_in_log_order(tmp_path):
    # R46: a clock step in the first phase moved realtime back past the second
    # phase's start, so the earliest-realtime phase is phase 2, but the phase to
    # record as data is phase 1 (the first the relay logged).
    p1_start, p2_start = T_SUB + 5_000_000_000, T_SUB  # phase 1 logged first, later realtime
    logcat = (b.phase_start_line(p1_start, phase=1)
              + "\n" + b.phase_end_line(p1_start + 2_000_000_000, p1_start, phase=1, layer_caused=False,
                                        client_connected=False, cause="client_lost")
              + "\n" + b.phase_start_line(p2_start, phase=2) + "\n")
    clean = [b.frame(10, p1_start + 2_500_000_000)]
    records = b.stream_records(4731, clean, t0=p1_start + 2_400_000_000, cport=46001)
    run = _vc020(tmp_path, sorted(records), logcat, condition="ivi_vm_down")
    result = evaluators.evaluate_unsubscribed_discard(run)
    assert result.measurements["first_phase_recorded_as_data"] == {"pid": 1234, "phase": 1}


# ------------------------------------------- VC-MW-015: an ingress disconnect the relay causes
#
# The merged case text (main 4bcfe628): an ingress disconnect that the relay
# causes is a delivery failure of the layer, not an inconclusive condition.
# The relay causes it by its exit (gateway_client_lost, exit code 4) or by a
# close of the stream from port 4731 in the loopback capture. An ingress that
# closes its own stream stays an inconclusive condition.

EVENT_T0 = P0 - 150_000_000  # a received stream whose frames and close fall inside the produced span


def _received(run, received, *, close, t0=EVENT_T0, extra_records=()):
    records = b.stream_records(4731, received, t0=t0, close=close) + list(extra_records)
    (run.run_dir / "received.pcap").write_bytes(b.pcap(sorted(records)))


def test_vc015_the_relay_closing_the_ingress_stream_in_the_event_fails(tmp_path):
    payloads = frames_seq()
    run = _vc015_base(tmp_path, payloads, payloads, logcat=phase_logcat(P0 - 200_000_000))
    _received(run, payloads, close="server")
    result = evaluators.evaluate_source_order(run)
    assert result.outcome == outcome.FAIL, result.as_dict()
    assert any(f.code == "ingress-disconnect" and "4731" in f.message for f in result.findings)


def test_vc015_the_ingress_closing_its_own_stream_stays_inconclusive(tmp_path):
    payloads = frames_seq()
    logcat = phase_logcat(P0 - 200_000_000, P0 + 290_000_000, layer_caused=False, client_connected=False,
                          cause="client_lost")
    run = _vc015_base(tmp_path, payloads, payloads, logcat=logcat)
    _received(run, payloads, close="client")
    result = evaluators.evaluate_source_order(run)
    assert result.outcome == outcome.INCONCLUSIVE, result.as_dict()
    assert not any(f.code == "ingress-disconnect" for f in result.findings)


def test_vc015_a_relay_close_after_the_event_is_not_a_failure(tmp_path):
    payloads = frames_seq()
    run = _vc015_base(tmp_path, payloads, payloads, logcat=phase_logcat(P0 - 200_000_000))
    _received(run, payloads, close="server", t0=P0 + 5_000_000)  # the FIN lands after the produced span
    result = evaluators.evaluate_source_order(run)
    assert result.outcome == outcome.PASS, result.as_dict()


def test_vc015_the_relay_exit_on_a_lost_gateway_client_in_the_event_fails(tmp_path):
    payloads = frames_seq()
    lost = b.logcat_line(P0 + 150_000_000, {"event": "gateway_client_lost", "stage": "disconnected",
                                            "notification_type": 2, "exit_code": 4})
    run = _vc015_base(tmp_path, payloads, payloads, logcat=phase_logcat(P0 - 200_000_000, extra=[lost]))
    result = evaluators.evaluate_source_order(run)
    assert result.outcome == outcome.FAIL, result.as_dict()
    assert any(f.code == "relay-exit" and "exit code 4" in f.message for f in result.findings)


def test_vc015_a_relay_write_failure_close_in_the_event_fails_not_inconclusive(tmp_path):
    payloads = frames_seq()
    logcat = phase_logcat(P0 - 200_000_000, P0 + 290_000_000, layer_caused=False, client_connected=False,
                          cause="client_write_failed")
    run = _vc015_base(tmp_path, payloads, payloads, logcat=logcat)
    result = evaluators.evaluate_source_order(run)
    assert result.outcome == outcome.FAIL, result.as_dict()
    assert any(f.code == "ingress-disconnect" and "client_write_failed" in f.message for f in result.findings)


def test_vc015_a_refused_second_client_closed_by_the_relay_is_not_an_ingress_disconnect(tmp_path):
    # The relay refuses a second client and closes it from port 4731; that
    # connection carried no frames, so it is not the ingress stream.
    payloads = frames_seq()
    run = _vc015_base(tmp_path, payloads, payloads, logcat=phase_logcat(P0 - 200_000_000))
    refused = b.TcpSender("127.0.0.1", "127.0.0.1", 50999, 4731, P0 + 100_000_000).handshake().fin().records
    _received(run, payloads, close=None, t0=P0 + 5_000_000, extra_records=refused)
    result = evaluators.evaluate_source_order(run)
    assert not any(f.code == "ingress-disconnect" for f in result.findings), result.as_dict()


def test_vc015_a_second_frame_assembler_client_is_recorded_as_a_bench_discrepancy(tmp_path):
    payloads = frames_seq()
    run = _vc015_base(tmp_path, payloads, payloads, logcat=phase_logcat(P0 - 50_000_000), adapter_only=False)
    result = evaluators.evaluate_source_order(run)
    assert result.outcome == outcome.INCONCLUSIVE
    assert "ASM-MW-029" in result.measurements["bench_discrepancy"]


# ------------------------------------------- VC-MW-020: the wide limit needs no clock step between the measurements
#
# The merged case text (main 4bcfe628): processData applies the
# clock-independent wide limit only if the relay logged no clock step between
# the two offset measurements (start and end of the session).

def test_vc020_the_wide_limit_is_not_applied_after_a_clock_step_between_the_measurements(tmp_path):
    frame = b.frame(7, T_SUB - 5_000_000_000)  # far outside the wide limit, as in N-5
    records = b.stream_records(4731, [frame], t0=T_SUB + 100_000_000)
    step = b.clock_step_line(T_SUB - 10_000_000_000, in_phase=False)  # between T_SUB-60 s and T_SUB+60 s
    run = _vc020(tmp_path, records, phase_logcat(T_SUB, extra=[step]), offset_ns=30_000_000)  # ASM-MW-030 fails
    result = evaluators.evaluate_unsubscribed_discard(run)
    assert result.outcome == outcome.INCONCLUSIVE, result.as_dict()
    assert result.measurements["wide_limit_applied"] is False


def test_vc020_a_clock_step_before_the_first_measurement_keeps_the_wide_limit(tmp_path):
    # The clock setting itself is a step; it comes before the start measurement.
    frame = b.frame(7, T_SUB - 5_000_000_000)
    records = b.stream_records(4731, [frame], t0=T_SUB + 100_000_000)
    step = b.clock_step_line(T_SUB - 120_000_000_000, in_phase=False)
    run = _vc020(tmp_path, records, phase_logcat(T_SUB, extra=[step]), offset_ns=30_000_000)
    result = evaluators.evaluate_unsubscribed_discard(run)
    assert result.outcome == outcome.FAIL, result.as_dict()
    assert result.measurements["wide_limit_applied"] is True


def test_vc020_an_unreadable_logcat_line_is_not_a_clock_step(tmp_path):
    frame = b.frame(7, T_SUB - 5_000_000_000)
    records = b.stream_records(4731, [frame], t0=T_SUB + 100_000_000)
    line = b.logcat_line(T_SUB - 10_000_000_000, {"event": "clock_step", "step_ns": 250_000_000, "in_phase": False})
    line = line.replace('"realtime_ns":', '"_realtime_ns":')
    first = line.split()[0]
    line = line.replace(first, "garbled", 1)  # no logcat time either
    run = _vc020(tmp_path, records, phase_logcat(T_SUB, extra=[line]), offset_ns=30_000_000)
    result = evaluators.evaluate_unsubscribed_discard(run)
    # An unreadable line is no relay event at all, so the wide limit still applies.
    assert result.measurements["wide_limit_applied"] is True



# ------------------------------------------- VC-MW-020: the second check, with the Data Tunnel subscription time
#
# The merged case text (main 4bcfe628): processData also runs the same check
# with a second start, the time of the subscription in the Data Tunnel capture.
# If that check fails and the first one passes, the outcome is
# inconclusiveMissingEvidence. Coordinator decision: if the time cannot be read
# the second check cannot run, so the run gives no pass.

def _clean_phase_run(tmp_path, *, dt="before", first_ns=T_SUB + 50_000_000):
    payloads = [b.frame(i, first_ns + i * 100_000_000) for i in range(1, 4)]
    records = b.stream_records(4731, payloads, t0=T_SUB + 40_000_000)
    return _vc020(tmp_path, records, phase_logcat(T_SUB, phase=1), dt=dt), records


def test_vc020_the_data_tunnel_stream_opened_before_the_judged_start_passes(tmp_path):
    run, _records = _clean_phase_run(tmp_path)
    result = evaluators.evaluate_unsubscribed_discard(run)
    assert result.outcome == outcome.PASS, result.as_dict()
    start = result.measurements["dt_starts"][0]
    assert start["dt_start_kind"] == "stream_open" and start["dt_start_ns"] == T_SUB - 100_000_000


def test_vc020_a_later_data_tunnel_subscription_that_fails_the_second_check_is_inconclusive(tmp_path):
    # The relay and the accept say about T_SUB; Data Tunnel says the stream
    # opened at T_SUB + 300 ms. Frames produced at T_SUB + 150 and + 250 ms are
    # delivered after that opening (stored frames): they pass the first check
    # and fail the second, so the run shows nothing (inconclusive, not fail).
    frames = [(T_SUB + 320_000_000, b.frame(1, T_SUB + 150_000_000)), (T_SUB + 330_000_000, b.frame(2, T_SUB + 250_000_000)),
              (T_SUB + 370_000_000, b.frame(3, T_SUB + 350_000_000))]
    records = _loopback(frames, t0=T_SUB + 40_000_000)
    run = _vc020(tmp_path, records, phase_logcat(T_SUB, phase=1), dt=None)
    (run.run_dir / "data-tunnel-vlan2.pcap").write_bytes(_dt_stream(_served_frames(records), T_SUB + 300_000_000))
    result = evaluators.evaluate_unsubscribed_discard(run)
    assert result.outcome == outcome.INCONCLUSIVE, result.as_dict()
    assert any(f.code == "dt-check" for f in result.findings)
    assert not any(f.outcome == outcome.FAIL for f in result.findings)


def test_vc020_without_a_data_tunnel_capture_there_is_no_pass(tmp_path):
    run, _records = _clean_phase_run(tmp_path, dt=None)
    result = evaluators.evaluate_unsubscribed_discard(run)
    assert result.outcome == outcome.INCONCLUSIVE, result.as_dict()
    assert any(f.code == "dt-start" and "data-tunnel-vlan2.pcap" in f.message for f in result.findings)


def test_vc020_a_data_tunnel_capture_without_the_phase_frames_gives_no_pass(tmp_path):
    run, _records = _clean_phase_run(tmp_path, dt=None)
    other = [(T_SUB, b.frame(900, T_SUB))]
    (run.run_dir / "data-tunnel-vlan2.pcap").write_bytes(_dt_stream(other, T_SUB - 100_000_000))
    result = evaluators.evaluate_unsubscribed_discard(run)
    assert result.outcome == outcome.INCONCLUSIVE, result.as_dict()
    assert result.measurements["dt_starts"][0]["dt_start_kind"] == "unknown"


def _flowing_tunnel(produced, *, from_ns, gap_after_ns=None):
    """A Data Tunnel capture joined mid-connection: no SYN, no preface, the frames already flowing."""
    conn = b.DtConnection(from_ns).handshake().open_stream(1, from_ns + 1_000_000, preface=True).server_settings()
    for frame_ts, payload in produced:
        at = frame_ts + 5_000_000
        if gap_after_ns is not None and gap_after_ns[0] <= at < gap_after_ns[1]:
            continue  # the flow stopped (a resubscription)
        conn.data(1, payload, at)
    conn.records = [record for record in conn.records if record[0] > from_ns + 100_000_000]  # joined after the start
    return b.dt_capture([conn])


def _hmi_down_like(tmp_path, *, gap=None):
    # The Data Tunnel stream started before the capture (as in HMI down: the
    # relay stays subscribed while the ingress is gone); the frames before the
    # phase crossed Data Tunnel and were discarded by the relay.
    produced = [(T_SUB - 2_000_000_000 + i * 100_000_000, b.frame(i, T_SUB - 2_000_000_000 + i * 100_000_000))
                for i in range(1, 25)]
    served = [payload for ts, payload in produced if ts >= T_SUB + 50_000_000]
    records = b.stream_records(4731, served, t0=T_SUB + 40_000_000)
    run, _ = _vc020(tmp_path, records, phase_logcat(T_SUB, phase=1), dt=None), None
    (run.run_dir / "produced.pcap").write_bytes(b.pcap(b.stream_records(4721, [p for _t, p in produced],
                                                                       t0=T_SUB - 2_100_000_000)))
    (run.run_dir / "data-tunnel-vlan2.pcap").write_bytes(_flowing_tunnel(produced, from_ns=T_SUB - 2_500_000_000,
                                                                         gap_after_ns=gap))
    return run


def test_vc020_a_mid_connection_capture_with_the_flow_running_through_the_start_passes(tmp_path):
    # The open time is not in the capture, but the frames flowed on the same
    # carrier, with no gap of 500 ms, from before the judged start to the
    # phase's first frame: the subscription started before the judged start,
    # so the second check cannot fail where the first passes.
    result = evaluators.evaluate_unsubscribed_discard(_hmi_down_like(tmp_path))
    assert result.outcome == outcome.PASS, result.as_dict()
    assert result.measurements["dt_starts"][0]["dt_start_kind"] == "before_judged_start"


def test_vc020_a_mid_connection_capture_with_a_flow_gap_before_the_phase_gives_no_pass(tmp_path):
    # A gap of 500 ms or more before the phase may be a new subscription whose
    # open time the capture does not hold.
    result = evaluators.evaluate_unsubscribed_discard(_hmi_down_like(tmp_path, gap=(T_SUB - 600_000_000,
                                                                                 T_SUB + 40_000_000)))
    assert result.outcome == outcome.INCONCLUSIVE, result.as_dict()
    assert result.measurements["dt_starts"][0]["dt_start_kind"] == "unknown"


def test_vc020_a_first_check_failure_still_fails_without_a_data_tunnel_capture(tmp_path):
    s2 = T_SUB + 30_000_000_000
    old = b.frame(500, s2 - 2_000_000_000)
    records = b.stream_records(4731, [old], t0=s2 + 100_000_000)
    logcat = (phase_logcat(T_SUB, T_SUB + 10_000_000_000, phase=1, layer_caused=False, client_connected=False,
                           cause="client_lost")
              + phase_logcat(s2, phase=2))
    run = _vc020(tmp_path, records, logcat, dt=None)
    assert evaluators.evaluate_unsubscribed_discard(run).outcome == outcome.FAIL


# ------------------------------------------- R48: the second check judges every frame after its start
#
# Decision on review R48: the second check judges every received frame
# delivered at or after the Data Tunnel start,
# not only frames inside the relay's logged phases. With the Data Tunnel bound,
# no frame may have been delivered outside a relay phase between the previous
# phase end (or the capture start) and the judged start; such a frame gives
# inconclusive. The bound then holds in all four conditions. Repros A-C of the
# final closure check of d4ab2ac1.

def _loopback(deliveries, *, t0, close="client"):
    """One ingress connection on 4731; ``deliveries`` = [(delivered_ns, frame bytes)], in time order."""
    sender = b.TcpSender("127.0.0.1", "127.0.0.1", 5731, 4731, t0).handshake()
    for at, payload in deliveries:
        sender.send(b.delimited(payload), step_ns=at - sender.t)
    if close == "client":
        sender.client_fin()
    return sender.records


def _dt_readable(open_ns, frames_at, earlier=None):
    """One VLAN 2 connection from its SYN. ``earlier`` = (open_ns, frames_at) of a first stream; the second
    stream (3) opens at ``open_ns``."""
    first_open = earlier[0] if earlier else open_ns
    conn = b.DtConnection(first_open - 30_000_000).handshake().open_stream(1, first_open, preface=True)
    conn.server_settings()
    sid = 1
    if earlier:
        for at, payload in earlier[1]:
            conn.data(1, payload, at)
        conn.open_stream(3, open_ns)
        sid = 3
    for at, payload in frames_at:
        conn.data(sid, payload, at)
    return b.dt_capture([conn])


def _r48_run(tmp_path, condition, records, logcat, dt_bytes):
    run = write(tmp_path, received__pcap=b.pcap(records), settings__json=settings(condition=condition),
                **{"relay-logcat.txt": logcat})
    (run / "clock-start.pcap").write_bytes(b.clock_pcap(2_000_000, T_SUB - 60_000_000_000, 0x1111))
    (run / "clock-end.pcap").write_bytes(b.clock_pcap(2_000_000, T_SUB + 60_000_000_000, 0x2222))
    (run / "data-tunnel-vlan2.pcap").write_bytes(dt_bytes)
    return evaluators.load_run(run)


@pytest.mark.parametrize("condition", ["hmi_down", "ivi_vm_down", "sdv_core_vm_down", "pair_restart"])
def test_r48_a_the_bound_holds_in_every_condition(tmp_path, condition):
    run = _hmi_down_like(tmp_path)
    settings_path = run.run_dir / "settings.json"
    values = json.loads(settings_path.read_text())
    values["condition"] = condition
    settings_path.write_text(json.dumps(values))
    result = evaluators.evaluate_unsubscribed_discard(evaluators.load_run(run.run_dir))
    assert result.outcome == outcome.PASS, result.as_dict()
    assert result.measurements["dt_starts"][0]["dt_start_kind"] == "before_judged_start"


def _pair_restart_runs(tmp_path, *, stored: bool):
    prev_start, prev_end, s2, s1 = T_SUB - 10_000_000_000, T_SUB - 2_000_000_000, T_SUB - 400_000_000, T_SUB
    before = [(prev_start + 100_000_000 + i * 100_000_000, b.frame(i + 1, prev_start + 95_000_000 + i * 100_000_000))
              for i in range(10)]
    old = [(T_SUB - 300_000_000, b.frame(50, s2 - 3_000_000_000))] if stored else []  # between the phases, after S2
    after = [(s1 + 60_000_000 + i * 100_000_000, b.frame(60 + i, s1 + 50_000_000 + i * 100_000_000))
             for i in range(5)]
    records = _loopback(before + old + after, t0=prev_start - 50_000_000)
    logcat = (phase_logcat(prev_start, prev_end, layer_caused=False, client_connected=True,
                           cause="publication_destroyed", phase=1)
              + phase_logcat(s1, phase=2))
    phase1 = (prev_start - 100_000_000, [(at - 2_000_000, payload) for at, payload in before])
    dt_bytes = _dt_readable(s2, [(at - 2_000_000, payload) for at, payload in old + after], earlier=phase1)
    return _r48_run(tmp_path, "pair_restart", records, logcat, dt_bytes)


def test_r48_b_a_stored_frame_between_the_phases_after_the_data_tunnel_start_is_inconclusive(tmp_path):
    # pair_restart, the ingress connected throughout: the Data Tunnel stream
    # opens 400 ms before the relay's phase_start, and a frame produced 3.4 s
    # before that opening is delivered between the relay's phases. The second
    # check judges it and fails; the first passes; so the run shows nothing.
    result = evaluators.evaluate_unsubscribed_discard(_pair_restart_runs(tmp_path, stored=True))
    assert result.outcome == outcome.INCONCLUSIVE, result.as_dict()
    assert any(f.code == "dt-check" for f in result.findings)


def test_r48_b0_the_same_run_without_the_stored_frame_passes(tmp_path):
    result = evaluators.evaluate_unsubscribed_discard(_pair_restart_runs(tmp_path, stored=False))
    assert result.outcome == outcome.PASS, result.as_dict()


@pytest.mark.parametrize("delivery_ns", [T_SUB + 500_000_000, T_SUB + 600_000_000])
def test_r48_a_readable_start_judges_a_stored_frame_at_or_after_the_phase_end(tmp_path, delivery_ns):
    opened = T_SUB - 100_000_000
    deliveries = [(T_SUB + 60_000_000, b.frame(1, T_SUB + 50_000_000)),
                  (delivery_ns, b.frame(2, opened - 3_000_000_000))]
    records = _loopback(deliveries, t0=T_SUB - 60_000_000)
    logcat = phase_logcat(T_SUB, T_SUB + 500_000_000, phase=1, cause="publication_destroyed")
    tunnel = _dt_readable(opened, [(at - 2_000_000, payload) for at, payload in deliveries])
    result = evaluators.evaluate_unsubscribed_discard(_r48_run(tmp_path, "pair_restart", records, logcat, tunnel))
    assert result.outcome == outcome.INCONCLUSIVE, result.as_dict()
    assert any(f.code == "dt-check" for f in result.findings)


def test_r48_c_a_stored_frame_between_the_accept_and_the_relay_start_is_inconclusive(tmp_path):
    # hmi_down in the normal order: the accept at -30 ms, the relay's
    # phase_start at T; a frame produced 3 s earlier is delivered at -20 ms,
    # after the Data Tunnel stream opened (-100 ms). The second check judges it.
    stored = (T_SUB - 20_000_000, b.frame(70, T_SUB - 3_000_000_000))
    after = [(T_SUB + 60_000_000 + i * 100_000_000, b.frame(80 + i, T_SUB + 50_000_000 + i * 100_000_000))
             for i in range(5)]
    records = _loopback([stored] + after, t0=T_SUB - 60_000_000)  # the handshake's ACK at T - 30 ms
    dt_bytes = _dt_readable(T_SUB - 100_000_000, [(at - 2_000_000, p) for at, p in [stored] + after])
    result = evaluators.evaluate_unsubscribed_discard(
        _r48_run(tmp_path, "hmi_down", records, phase_logcat(T_SUB, phase=1), dt_bytes))
    assert result.outcome == outcome.INCONCLUSIVE, result.as_dict()
    assert any(f.code == "dt-check" for f in result.findings)


@pytest.mark.parametrize("condition", ["hmi_down", "ivi_vm_down", "sdv_core_vm_down", "pair_restart"])
def test_r48_with_the_bound_a_frame_delivered_outside_a_phase_before_the_judged_start_is_inconclusive(tmp_path, condition):
    # The bound shows the subscription started before the judged start, but not
    # when; a frame delivered outside the relay's phases before the judged start
    # might follow it, and the bound cannot judge that frame.
    produced = [(T_SUB - 2_000_000_000 + i * 100_000_000, b.frame(i, T_SUB - 2_000_000_000 + i * 100_000_000))
                for i in range(1, 25)]
    stray = (T_SUB - 150_000_000, b.frame(300, T_SUB - 4_000_000_000))  # outside every phase
    served = [(ts + 10_000_000, payload) for ts, payload in produced if ts >= T_SUB + 50_000_000]
    records = _loopback([stray] + served, t0=T_SUB - 400_000_000)
    run = write(tmp_path, received__pcap=b.pcap(records), settings__json=settings(condition=condition),
                **{"relay-logcat.txt": phase_logcat(T_SUB, phase=1)})
    (run / "clock-start.pcap").write_bytes(b.clock_pcap(2_000_000, T_SUB - 60_000_000_000, 0x1111))
    (run / "clock-end.pcap").write_bytes(b.clock_pcap(2_000_000, T_SUB + 60_000_000_000, 0x2222))
    (run / "produced.pcap").write_bytes(b.pcap(b.stream_records(4721, [p for _t, p in produced],
                                                               t0=T_SUB - 2_100_000_000)))
    (run / "data-tunnel-vlan2.pcap").write_bytes(_flowing_tunnel(produced, from_ns=T_SUB - 2_500_000_000))
    result = evaluators.evaluate_unsubscribed_discard(evaluators.load_run(run))
    assert result.outcome == outcome.INCONCLUSIVE, result.as_dict()
    assert any(f.code == "dt-bound" for f in result.findings)


@pytest.mark.parametrize("delivery_ns", [T_SUB + 500_000_000, T_SUB + 600_000_000])
def test_r48_the_bound_cannot_hide_a_stored_frame_at_or_after_the_phase_end(tmp_path, delivery_ns):
    run = _hmi_down_like(tmp_path)
    received = evaluators._read_frames(run, "received.pcap", 4731)
    deliveries = [(frame.delivered_ns, frame.payload) for frame in received.frames]
    deliveries.append((delivery_ns, b.frame(300, T_SUB - 4_000_000_000)))
    (run.run_dir / "received.pcap").write_bytes(b.pcap(_loopback(deliveries, t0=T_SUB - 60_000_000)))
    (run.run_dir / "relay-logcat.txt").write_text(
        phase_logcat(T_SUB, T_SUB + 500_000_000, phase=1, cause="publication_destroyed"))
    result = evaluators.evaluate_unsubscribed_discard(evaluators.load_run(run.run_dir))
    assert result.measurements["dt_starts"][0]["dt_start_kind"] == "before_judged_start"
    assert result.outcome == outcome.INCONCLUSIVE, result.as_dict()
    assert any(f.code == "dt-bound" for f in result.findings)


@pytest.mark.parametrize("readable", [False, True])
def test_r48_the_second_check_needs_a_timestamp_outside_a_relay_phase(tmp_path, readable):
    run = _hmi_down_like(tmp_path)
    received = evaluators._read_frames(run, "received.pcap", 4731)
    deliveries = [(frame.delivered_ns, frame.payload) for frame in received.frames]
    deliveries.append((T_SUB + 600_000_000, b"\x08\x01\x18\x63"))  # sequence 99, no timestamp
    (run.run_dir / "received.pcap").write_bytes(b.pcap(_loopback(deliveries, t0=T_SUB - 60_000_000)))
    (run.run_dir / "relay-logcat.txt").write_text(
        phase_logcat(T_SUB, T_SUB + 500_000_000, phase=1, cause="publication_destroyed"))
    if readable:
        (run.run_dir / "data-tunnel-vlan2.pcap").write_bytes(
            _dt_readable(T_SUB - 100_000_000, [(at - 2_000_000, payload) for at, payload in deliveries]))
    result = evaluators.evaluate_unsubscribed_discard(evaluators.load_run(run.run_dir))
    assert result.outcome == outcome.INCONCLUSIVE, result.as_dict()
    assert any(f.code == "dt-timestamp" for f in result.findings)


def test_r48_a_forward_clock_step_in_the_lookback_can_make_the_bound_unknown(tmp_path):
    run = _hmi_down_like(tmp_path)
    produced = evaluators._read_frames(run, "produced.pcap", 4721)
    conn = b.DtConnection(T_SUB - 4_000_000_000).handshake()
    conn.open_stream(1, T_SUB - 3_900_000_000, preface=True).server_settings()
    for frame in produced.frames:
        ts = evaluators._facts(frame).frame_timestamp_ns
        clock_shift = -500_000_000 if ts < T_SUB - 1_000_000_000 else 0
        conn.data(1, frame.payload, ts + 5_000_000 + clock_shift)
    conn.records = [record for record in conn.records if record[0] > T_SUB - 3_000_000_000]
    (run.run_dir / "data-tunnel-vlan2.pcap").write_bytes(b.dt_capture([conn]))
    result = evaluators.evaluate_unsubscribed_discard(evaluators.load_run(run.run_dir))
    assert result.outcome == outcome.INCONCLUSIVE, result.as_dict()
    assert result.measurements["dt_starts"][0]["dt_start_kind"] == "unknown"
