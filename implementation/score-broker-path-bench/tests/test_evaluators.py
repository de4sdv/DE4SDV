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

def _vc017(tmp_path, **files):
    base = dict(
        host_listeners__json=[{"port": 30160, "protocol": "udp", "element_in_layer": True, "element": "adapter"}],
        probe_attempts__json=[{"guest": "ivi", "interface": "eth1", "host": "192.168.98.1", "port": 30160,
                               "protocol": "udp", "marker": "ivi-eth1-30160", "result": "sent"}],
        host_socket_receipts__json={"udp_markers": [], "tcp_connects": []},
        control__json={"reached": True, "detail": "control arrived"},
        coverage__json={"per_guest": {"ivi": {"expected_interfaces": ["eth1"], "probed_interfaces": ["eth1"],
                                              "expected_host_addresses": ["192.168.98.1"],
                                              "probed_host_addresses": ["192.168.98.1"]}}},
        asm_mw_031__json={"holds": True},
        inspection__json={"no_host_endpoint": True, "inspector": "bench"},
    )
    base.update(files)
    return evaluators.load_run(write(tmp_path, **base))


def test_vc017_passes_when_nothing_is_reachable(tmp_path):
    run = _vc017(tmp_path)
    assert evaluators.evaluate_isolation(run).outcome == outcome.PASS, evaluators.evaluate_isolation(run).as_dict()


def test_vc017_e12_layer_port_reached_fails_even_if_control_fails(tmp_path):
    run = _vc017(tmp_path,
                 host_socket_receipts__json={"udp_markers": ["ivi-eth1-30160"], "tcp_connects": []},
                 control__json={"reached": False, "detail": "control lost"})
    assert evaluators.evaluate_isolation(run).outcome == outcome.FAIL


def test_vc017_e13_only_4721_reached_is_not_a_requirement_failure(tmp_path):
    run = _vc017(
        tmp_path,
        host_listeners__json=[{"port": 4721, "protocol": "tcp", "element_in_layer": False, "element": "assembler"}],
        probe_attempts__json=[{"guest": "ivi", "interface": "eth1", "host": "192.168.98.1", "port": 4721,
                               "protocol": "tcp", "marker": "ivi-eth1-4721", "result": "connected"}],
        host_socket_receipts__json={"udp_markers": [], "tcp_connects": [{"port": 4721, "guest": "ivi"}]},
        coverage__json={"per_guest": {"ivi": {"expected_interfaces": ["eth1"], "probed_interfaces": ["eth1"],
                                              "expected_host_addresses": ["192.168.98.1"],
                                              "probed_host_addresses": ["192.168.98.1"]}}},
    )
    res = evaluators.evaluate_isolation(run)
    assert res.outcome == outcome.PASS
    assert res.measurements.get("asm_mw_029_findings")


def test_vc017_other_process_reachable_fails_only_when_asm031_holds(tmp_path):
    base = dict(
        host_listeners__json=[{"port": 30161, "protocol": "udp", "element_in_layer": False, "element": "ros2cli"}],
        probe_attempts__json=[{"guest": "ivi", "interface": "eth1", "host": "192.168.98.1", "port": 30161,
                               "protocol": "udp", "marker": "m", "result": "sent"}],
        host_socket_receipts__json={"udp_markers": ["m"], "tcp_connects": []},
        coverage__json={"per_guest": {"ivi": {"expected_interfaces": ["eth1"], "probed_interfaces": ["eth1"],
                                              "expected_host_addresses": ["192.168.98.1"],
                                              "probed_host_addresses": ["192.168.98.1"]}}},
    )
    holds = _vc017(tmp_path / "a", asm_mw_031__json={"holds": True}, **base)
    assert evaluators.evaluate_isolation(holds).outcome == outcome.FAIL
    not_shown = _vc017(tmp_path / "b", asm_mw_031__json={"holds": False}, **base)
    assert evaluators.evaluate_isolation(not_shown).outcome == outcome.INCONCLUSIVE


def test_vc017_control_failure_is_inconclusive(tmp_path):
    run = _vc017(tmp_path, control__json={"reached": False, "detail": "no control"})
    assert evaluators.evaluate_isolation(run).outcome == outcome.INCONCLUSIVE


def test_vc017_coverage_gap_is_inconclusive(tmp_path):
    run = _vc017(tmp_path, coverage__json={"per_guest": {"ivi": {
        "expected_interfaces": ["eth1", "buried_eth0"], "probed_interfaces": ["eth1"],
        "expected_host_addresses": ["192.168.98.1"], "probed_host_addresses": ["192.168.98.1"]}}})
    assert evaluators.evaluate_isolation(run).outcome == outcome.INCONCLUSIVE


def test_vc017_missing_inspection_is_inconclusive(tmp_path):
    run = write(tmp_path,
                host_listeners__json=[],
                probe_attempts__json=[{"guest": "ivi", "interface": "eth1", "host": "192.168.98.1", "port": 30160,
                                       "protocol": "udp", "marker": "m", "result": "sent"}],
                host_socket_receipts__json={"udp_markers": [], "tcp_connects": []},
                control__json={"reached": True, "detail": "ok"},
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


def test_vc020_clock_failure_suppresses_the_violation_to_inconclusive(tmp_path):
    frame = b.frame(7, T_SUB - 5_000_000_000)  # clearly old, would be a violation
    records = b.stream_records(4731, [frame], t0=T_SUB + 100_000_000)
    run = _vc020(tmp_path, records, phase_logcat(T_SUB), offset_ns=50_000_000)  # 50 ms offset: ASM-MW-030 fails
    assert evaluators.evaluate_unsubscribed_discard(run).outcome == outcome.INCONCLUSIVE


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
