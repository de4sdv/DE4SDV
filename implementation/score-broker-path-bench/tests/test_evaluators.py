"""Regression tests of the evaluators over synthetic run directories.

Each test builds a run directory of raw artifacts and asserts the outcome the
verification case of #448 (5d14317c) asks for. The cases marked [R...]/[E...]
reproduce the false-pass and fail/inconclusive-swap findings of the two
independent reviews of PR #450 at 1392e969; each must now give the right
outcome. The artifacts are the same kinds the bench captures.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import builders as b  # noqa: E402
from de4sdv_broker_path_bench import evaluators, outcome  # noqa: E402

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

def _vc016(tmp_path, produced, received, sd_offer=None, residual=None):
    files = dict(
        produced__pcap=b.pcap(b.stream_records(4721, produced, t0=P0)),
        received__pcap=b.pcap(b.stream_records(4731, received, t0=P0 + 5_000_000)),
        settings__json=settings(),
    )
    if sd_offer is not None:
        files["sd_offer__json"] = sd_offer
    if residual is not None:
        files["residual__json"] = residual
    return evaluators.load_run(write(tmp_path, **files))


def test_vc016_passes_on_identical_bytes_with_a_good_offer(tmp_path):
    payloads = frames_seq()
    run = _vc016(tmp_path, payloads, payloads, sd_offer={"provider_after_offer": "192.168.98.1"})
    assert evaluators.evaluate_provenance(run).outcome == outcome.PASS, evaluators.evaluate_provenance(run).as_dict()


def test_vc016_byte_difference_fails(tmp_path):
    payloads = frames_seq()
    tampered = list(payloads)
    tampered[1] = b.frame(2, 2_100_000_000, stage="INTERVENTION")
    run = _vc016(tmp_path, payloads, tampered, sd_offer={"provider_after_offer": "192.168.98.1"})
    assert evaluators.evaluate_provenance(run).outcome == outcome.FAIL


def test_vc016_no_sd_record_is_inconclusive(tmp_path):
    payloads = frames_seq()
    run = _vc016(tmp_path, payloads, payloads)
    assert evaluators.evaluate_provenance(run).outcome == outcome.INCONCLUSIVE


def test_vc016_sd_redirect_fails(tmp_path):
    payloads = frames_seq()
    run = _vc016(tmp_path, payloads, payloads, sd_offer={"provider_after_offer": "192.168.98.118"})
    assert evaluators.evaluate_provenance(run).outcome == outcome.FAIL


def test_vc016_rg_unproduced_received_frame_fails(tmp_path):
    payloads = frames_seq()
    injected = payloads[:3] + [b.frame(999, 9_000_000_000)] + payloads[3:]
    run = _vc016(tmp_path, payloads, injected, sd_offer={"provider_after_offer": "192.168.98.1"})
    assert evaluators.evaluate_provenance(run).outcome == outcome.FAIL


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


def _udp_probe(port, *, counter=True, sent="sent", guest="ivi", iface="eth1", host="192.168.98.1"):
    return {"guest": guest, "interface": iface, "src_addr": "192.168.98.118", "host": host, "port": port,
            "protocol": "udp", "marker": _marker(port, guest, iface, host), "send_status": sent,
            "counter_moved": counter, "guest_connected": None}


def _vc017(tmp_path, **files):
    base = dict(
        firewall__json={"inet_table_present": True, "dds_counters_readable": True, "tcp_counters_readable": True},
        host_listeners__json=[{"address": "0.0.0.0", "port": 30160, "protocol": "udp", "element": "de4sdv_score_ad",
                               "pid": 11, "element_in_layer": True}],
        probe_attempts__json=[_udp_probe(30160, counter=True)],
        captured_markers__json={"udp_markers": [_marker(30160)], "tcp_syns": []},
        control__json={"captured": True, "counter_moved": False, "delivered": True, "detail": "control arrived"},
        coverage__json={"per_guest": {"ivi": {"expected_interfaces": ["eth1"], "probed_interfaces": ["eth1"],
                                              "expected_host_addresses": ["192.168.98.1"],
                                              "probed_host_addresses": ["192.168.98.1"]}}},
        asm_mw_031__json={"holds": True},
        inspection__json={"no_host_endpoint": True, "inspector": "bench"},
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
    run = _vc017(tmp_path,
                 probe_attempts__json=[_udp_probe(30160, counter=False)],  # captured, not dropped: reached
                 control__json={"captured": False, "counter_moved": None, "delivered": False, "detail": "control lost"})
    assert evaluators.evaluate_isolation(run).outcome == outcome.FAIL


def test_vc017_e13_only_4721_reached_is_not_a_requirement_failure(tmp_path):
    run = _vc017(
        tmp_path,
        host_listeners__json=[{"address": "0.0.0.0", "port": 4721, "protocol": "tcp", "element": "python3",
                               "pid": 12, "element_in_layer": False}],
        probe_attempts__json=[{"guest": "ivi", "interface": "eth1", "src_addr": "192.168.98.118",
                               "host": "192.168.98.1", "port": 4721, "protocol": "tcp", "marker": _marker(4721),
                               "send_status": "sent", "counter_moved": False, "guest_connected": True}],
        captured_markers__json={"udp_markers": [], "tcp_syns": [{"host": "192.168.98.1", "port": 4721}]},
    )
    res = evaluators.evaluate_isolation(run)
    assert res.outcome == outcome.PASS
    assert res.measurements.get("asm_mw_029_findings")


def test_vc017_other_process_reachable_fails_only_when_asm031_holds(tmp_path):
    base = dict(
        host_listeners__json=[{"address": "0.0.0.0", "port": 30161, "protocol": "udp", "element": "component_conta",
                               "pid": 13, "element_in_layer": False}],
        probe_attempts__json=[_udp_probe(30161, counter=False)],  # captured, not dropped: reached
        captured_markers__json={"udp_markers": [_marker(30161)], "tcp_syns": []},
    )
    holds = _vc017(tmp_path / "a", asm_mw_031__json={"holds": True}, **base)
    assert evaluators.evaluate_isolation(holds).outcome == outcome.FAIL
    not_shown = _vc017(tmp_path / "b", asm_mw_031__json={"holds": False}, **base)
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


def _vc020(tmp_path, received_records, logcat, condition="hmi_down", offset_ns=2_000_000, with_clock=True):
    run = write(tmp_path, received__pcap=b.pcap(received_records),
                settings__json=settings(condition=condition),
                **{"relay-logcat.txt": logcat})
    if with_clock:
        (run / "clock-start.pcap").write_bytes(b.clock_pcap(offset_ns, T_SUB - 60_000_000_000, 0x1111))
        (run / "clock-end.pcap").write_bytes(b.clock_pcap(offset_ns, T_SUB + 60_000_000_000, 0x2222))
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
    # the offset and passed; the rule and #448 compare raw.
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
# Each is a false pass or false fail the two delta reviews of #450 cited; it is
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
    run = _vc016(tmp_path, payloads, payloads[:3], sd_offer={"provider_after_offer": "192.168.98.1"})
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
    # #448: a pass covers the four conditions.
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
