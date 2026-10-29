"""Tests of the VC-MW-017 reachability judgement (probe.py), from real artifact shapes.

Each case builds the probe artifacts the VM script records: the firewall
validity record, the per-probe observations (send status, the capture
witness, the drop-counter delta), the host listeners from a real ss parse,
and the control. probe.evaluate_isolation reads them and classifies each
probe as reached, isolated or unknown; the case evaluator maps that to an
outcome. These are the shapes the harness feeds, not synthesized verdicts,
so a false pass or false fail of the judgement fails here (review R26-R29,
R15, R2b/R2d, R1d).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from de4sdv_broker_path_bench import probe  # noqa: E402

LAYER_PORT, OTHER_PORT, ASSEMBLER_PORT = 30160, 30162, 4721
HOST = "192.168.98.1"


def write(run: Path, **files) -> Path:
    run.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        path = run / name.replace("__", ".")
        path.write_text(json.dumps(data) if isinstance(data, (dict, list)) else data)
    return run


def firewall(table=True, dds=True, tcp=True):
    return {"inet_table_present": table, "dds_counters_readable": dds, "tcp_counters_readable": tcp}


def udp_attempt(port, *, guest="ivi", iface="eth1", src="192.168.98.118", host=HOST, sent="sent", counter=True):
    marker = f"MARK:{guest}-{iface}-{host}-{port}"
    return {"guest": guest, "interface": iface, "src_addr": src, "host": host, "port": port, "protocol": "udp",
            "marker": marker, "send_status": sent, "counter_moved": counter, "guest_connected": None}


def tcp_attempt(*, guest="ivi", iface="eth1", src="192.168.98.118", host=HOST, sent="sent", counter=True,
                connected=True):
    marker = f"MARK:{guest}-{iface}-{host}-{ASSEMBLER_PORT}"
    return {"guest": guest, "interface": iface, "src_addr": src, "host": host, "port": ASSEMBLER_PORT,
            "protocol": "tcp", "marker": marker, "send_status": sent, "counter_moved": counter,
            "guest_connected": connected}


def listeners(*rows):
    out = []
    for port, element, in_layer in rows:
        out.append({"address": "0.0.0.0", "port": port, "protocol": "tcp" if port == ASSEMBLER_PORT else "udp",
                    "element": element, "pid": 10, "element_in_layer": in_layer})
    return out


def coverage(probed_if=("eth1",), expected_if=("eth1",), probed_addr=(HOST,), expected_addr=(HOST,)):
    return {"per_guest": {"ivi": {"expected_interfaces": list(expected_if), "probed_interfaces": list(probed_if),
                                  "expected_host_addresses": list(expected_addr),
                                  "probed_host_addresses": list(probed_addr)}}}


def base(run: Path, *, attempts, captured_udp=(), captured_syns=(), listeners_rows=((LAYER_PORT, "de4sdv_score_ad", True),),
         fw=None, control=None, cov=None, asm=True, inspection=True, **extra):
    files = {
        "firewall__json": fw if fw is not None else firewall(),
        "probe_attempts__json": attempts,
        "captured_markers__json": {"udp_markers": list(captured_udp), "tcp_syns": list(captured_syns)},
        "host_listeners__json": listeners(*listeners_rows),
        "control__json": control if control is not None else {"captured": True, "counter_moved": False,
                                                              "delivered": True, "detail": "ok"},
        "coverage__json": cov if cov is not None else coverage(),
        "asm_mw_031__json": {"holds": asm} if asm is not None else {"holds": None},
    }
    if inspection:
        files["inspection__json"] = {"no_host_endpoint": True, "inspector": "bench", "artifacts": []}
    files.update(extra)
    return write(run, **files)


def verdict(run: Path):
    return probe.evaluate_isolation(run)


# -------------------------------------------------- the four harness scenarios

def test_nofw_without_the_table_is_not_a_pass(tmp_path):
    """nofw (R26): no firewall table, so the probe cannot judge; it must not pass."""
    attempt = udp_attempt(LAYER_PORT, counter=None)
    run = base(tmp_path, attempts=[attempt], captured_udp=[attempt["marker"]],
               fw=firewall(table=False, dds=False, tcp=False),
               control={"captured": True, "counter_moved": None, "delivered": True, "detail": "no table"})
    result = verdict(run)
    assert not result.table_readable
    assert result.reached_layer == [] and result.reached_other == []


def test_fw_real_failed_add_leaves_no_table_is_inconclusive(tmp_path):
    """fw_real (R26): nft add failed closed, so no readable counters; cannot judge."""
    run = base(tmp_path, attempts=[udp_attempt(LAYER_PORT, counter=None)],
               fw=firewall(table=False, dds=False, tcp=False))
    assert not verdict(run).table_readable


def test_fw_emul_working_firewall_drops_every_probe(tmp_path):
    """fw_emul (R27): the firewall drops each probe (counter moved), so nothing is reachable."""
    attempts = [udp_attempt(p, counter=True) for p in (30150, 30151, 30160, 30161, 30162)]
    attempts.append(tcp_attempt(counter=True, connected=False))
    captured = [a["marker"] for a in attempts]  # pre-netfilter capture sees them all
    run = base(tmp_path, attempts=attempts, captured_udp=captured,
               captured_syns=[{"host": HOST, "port": ASSEMBLER_PORT}])
    result = verdict(run)
    assert result.table_readable
    assert result.reached_layer == [] and result.reached_other == [] and result.reached_frame_assembler == []
    assert result.control_ok is True


def test_fw_emul_ctrl_blocked_is_inconclusive(tmp_path):
    """fw_emul_ctrl_blocked (R1d): the control was captured and not dropped by the bench rule, but not
    delivered, so the method is not shown to observe a reachable datagram; the run cannot pass."""
    attempts = [udp_attempt(p, counter=True) for p in (30150, 30160)]
    run = base(tmp_path, attempts=attempts, captured_udp=[a["marker"] for a in attempts],
               control={"captured": True, "counter_moved": False, "delivered": False,
                        "detail": "control datagram not delivered"})
    assert verdict(run).control_ok is False


# -------------------------------------------------- the judgement

def test_a_layer_port_reached_past_the_firewall_is_a_layer_finding(tmp_path):
    """A DDS port of the layer captured and NOT dropped (the rule has a gap) is reachable (R26/R27)."""
    attempt = udp_attempt(LAYER_PORT, counter=False)  # arrived, counter did not take it
    run = base(tmp_path, attempts=[attempt], captured_udp=[attempt["marker"]])
    result = verdict(run)
    assert [a["port"] for a in result.reached_layer] == [LAYER_PORT]


def test_a_probe_that_never_arrived_is_unknown_not_reached(tmp_path):
    """N-3: a probe whose marker is not in the capture never arrived; it is unknown, not reached."""
    attempt = udp_attempt(LAYER_PORT, counter=False)  # the counter did not move, but...
    run = base(tmp_path, attempts=[attempt], captured_udp=[])  # ...nothing was captured
    result = verdict(run)
    assert result.reached_layer == []
    assert any("did not arrive" in gap or "unknown" in gap for gap in result.coverage_gaps) or result.unknown_probes


def test_a_failed_send_is_unknown(tmp_path):
    """R27/R15: a probe whose guest send failed (e.g. from lo, EINVAL) is unknown, never reached."""
    attempt = udp_attempt(LAYER_PORT, sent="send_failed", counter=False)
    run = base(tmp_path, attempts=[attempt], captured_udp=[])
    assert verdict(run).reached_layer == []


def test_a_dropped_layer_probe_is_isolated(tmp_path):
    attempt = udp_attempt(LAYER_PORT, counter=True)
    run = base(tmp_path, attempts=[attempt], captured_udp=[attempt["marker"]])
    assert verdict(run).reached_layer == []


def test_a_reachable_other_process_port_fails_only_when_asm031_holds(tmp_path):
    attempt = udp_attempt(OTHER_PORT, counter=False)
    rows = ((OTHER_PORT, "component_conta", False),)
    holds = base(tmp_path / "a", attempts=[attempt], captured_udp=[attempt["marker"]], listeners_rows=rows, asm=True)
    assert [a["port"] for a in verdict(holds).reached_other] == [OTHER_PORT]
    assert verdict(holds).asm_mw_031_holds is True
    not_shown = base(tmp_path / "b", attempts=[attempt], captured_udp=[attempt["marker"]], listeners_rows=rows,
                     asm=None)
    assert verdict(not_shown).asm_mw_031_holds is None


def test_a_reachable_4721_is_a_frame_assembler_finding_not_a_layer_finding(tmp_path):
    attempt = tcp_attempt(counter=False, connected=True)
    run = base(tmp_path, attempts=[attempt], captured_syns=[{"host": HOST, "port": ASSEMBLER_PORT}],
               listeners_rows=((ASSEMBLER_PORT, "python3", False),))
    result = verdict(run)
    assert result.reached_layer == [] and result.reached_other == []
    assert [a["port"] for a in result.reached_frame_assembler] == [ASSEMBLER_PORT]


def test_r29_coverage_gap_when_the_host_has_an_unprobed_address(tmp_path):
    """R29/R2d: expected addresses derived from the host side; an unprobed one is a gap."""
    attempt = udp_attempt(LAYER_PORT, counter=True)
    cov = coverage(probed_addr=(HOST,), expected_addr=(HOST, "192.168.97.1"))
    run = base(tmp_path, attempts=[attempt], captured_udp=[attempt["marker"]], cov=cov)
    assert any("192.168.97.1" in gap for gap in verdict(run).coverage_gaps)


def test_r2b_a_listed_layer_socket_that_was_not_probed_is_a_gap(tmp_path):
    attempt = udp_attempt(30150, counter=True)
    run = base(tmp_path, attempts=[attempt], captured_udp=[attempt["marker"]],
               listeners_rows=((30150, "de4sdv_score_ad", True), (LAYER_PORT, "de4sdv_score_ad", True)))
    assert any(str(LAYER_PORT) in gap for gap in verdict(run).coverage_gaps)


def test_asm031_unknown_with_no_reachable_layer_port_is_still_noted(tmp_path):
    run = base(tmp_path, attempts=[udp_attempt(LAYER_PORT, counter=True)],
               captured_udp=[f"MARK:ivi-eth1-{HOST}-{LAYER_PORT}"], asm=None)
    assert verdict(run).asm_mw_031_holds is None
