"""The probe script renders the guest command with the namespace on the sender.

Review R42: the old code put `ip netns exec $ns` on the `echo` only, so the
sender ran in the root namespace while the route check judged another table.
The script now renders the whole sender inside the namespace; these tests check
that rendering (they do not run adb or touch a VM).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
SCRIPT = BENCH / "scripts" / "host_isolation_probe.sh"
sys.path.insert(0, str(BENCH / "src"))

from de4sdv_broker_path_bench import probe  # noqa: E402

GUEST_SENDER = "/data/local/tmp/de4sdv_probe_send"


def render(subcommand: str, ns: str, iface="g-ivi", src="192.168.98.118", addr="192.168.98.1",
           port="30160", marker="MARK:probe", *extra) -> str:
    env = {k: v for k, v in os.environ.items() if k not in ("PROBE_SENDER", "PROBE_SENDER_GUEST")}
    result = subprocess.run(["bash", str(SCRIPT), subcommand, ns, iface, src, addr, port, marker, *extra],
                            capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_a_namespaced_udp_probe_runs_the_sender_in_the_namespace():
    line = render("render-probe", "sdv_dt_ns")
    # The namespace prefix wraps the sender, not only the echo (review R42).
    assert f"ip netns exec sdv_dt_ns {GUEST_SENDER}" in line
    assert "--device g-ivi" in line and "--source 192.168.98.118" in line


def test_a_root_namespace_udp_probe_has_no_netns_prefix():
    line = render("render-probe", "-")
    assert "ip netns exec" not in line
    assert line.startswith("echo -n 'MARK:probe' | ")
    assert f"{GUEST_SENDER} --device g-ivi" in line


def test_a_namespaced_tcp_probe_runs_the_sender_in_the_namespace():
    line = render("render-tcp", "sd_mesh_ns", port="4721")
    assert f"ip netns exec sd_mesh_ns {GUEST_SENDER} --tcp" in line
    assert "--timeout-ms" in line


def test_the_udp_probe_pins_an_ephemeral_source_port_and_feeds_the_marker():
    line = render("render-probe", "-")
    # UDP probes bind the device and source; the source port is the kernel's
    # choice (0), and the marker is the payload on stdin.
    assert "--sport 0" in line
    assert line.startswith("echo -n 'MARK:probe'")


def test_the_guest_sender_is_the_pushed_path_from_bench_env():
    # The provisioning step pushes the sender to this path on both guests; the
    # probe and the SD offer run it from there (not from PATH).
    line = render("render-probe", "-")
    assert f"| timeout 2 {GUEST_SENDER} --device g-ivi" in line


def test_r41_the_tcp_probe_pins_its_own_source_port():
    """The :4721 probe has no payload marker; its pinned source port identifies
    it in the capture, so two guests' connects to one host are told apart (R41)."""
    line = render("render-tcp", "-", "eth1", "192.168.98.3", "192.168.98.1", "4721", "MARK:x", "28007")
    assert "--sport 28007" in line and "--tcp" in line


def _dds_range(tmp_path, **env):
    out = tmp_path / "dds_range.json"
    full_env = {**os.environ, **env}
    result = subprocess.run(["bash", str(SCRIPT), "dds-range", str(out)], capture_output=True, text=True,
                            env=full_env)
    assert result.returncode == 0, result.stderr
    return json.loads(out.read_text())


def test_r45_the_script_records_the_range_it_probes_and_the_evaluator_accepts_it(tmp_path):
    record = _dds_range(tmp_path, ROS_DOMAIN_ID="91", DDS_MAX_PARTICIPANT_INDEX="120")
    assert record["domain"] == 91 and record["max_participant_index"] == 120
    assert record["ports"] == probe.dds_udp_ports()
    summary, gap = probe._check_dds_range(record)
    assert gap is None and summary["ports"] == 244


def test_r45_a_reduced_index_is_recorded_as_such_and_the_evaluator_reports_it(tmp_path):
    record = _dds_range(tmp_path, ROS_DOMAIN_ID="91", DDS_MAX_PARTICIPANT_INDEX="2")
    assert record["max_participant_index"] == 2 and len(record["ports"]) == 8
    _summary, gap = probe._check_dds_range(record)
    assert gap and "participant index 2" in gap
