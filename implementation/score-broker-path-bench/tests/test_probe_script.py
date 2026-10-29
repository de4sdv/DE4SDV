"""The probe script renders the guest command with the namespace on the sender.

Review R42: the old code put `ip netns exec $ns` on the `echo` only, so the
sender ran in the root namespace while the route check judged another table.
The script now renders the whole sender inside the namespace; these tests check
that rendering (they do not run adb or touch a VM).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "host_isolation_probe.sh"


def render(subcommand: str, ns: str, iface="g-ivi", src="192.168.98.118", addr="192.168.98.1",
           port="30160", marker="MARK:probe") -> str:
    result = subprocess.run(["bash", str(SCRIPT), subcommand, ns, iface, src, addr, port, marker],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_a_namespaced_udp_probe_runs_the_sender_in_the_namespace():
    line = render("render-probe", "sdv_dt_ns")
    # The namespace prefix wraps the sender, not only the echo (review R42).
    assert "ip netns exec sdv_dt_ns de4sdv_probe_send" in line
    assert "--device g-ivi" in line and "--source 192.168.98.118" in line


def test_a_root_namespace_udp_probe_has_no_netns_prefix():
    line = render("render-probe", "-")
    assert "ip netns exec" not in line
    assert line.startswith("echo -n 'MARK:probe' | ")
    assert "de4sdv_probe_send --device g-ivi" in line


def test_a_namespaced_tcp_probe_runs_the_sender_in_the_namespace():
    line = render("render-tcp", "sd_mesh_ns", port="4721")
    assert "ip netns exec sd_mesh_ns de4sdv_probe_send --tcp" in line
    assert "--timeout-ms" in line


def test_the_udp_probe_pins_an_ephemeral_source_port_and_feeds_the_marker():
    line = render("render-probe", "-")
    # UDP probes bind the device and source; the source port is the kernel's
    # choice (0), and the marker is the payload on stdin.
    assert "--sport 0" in line
    assert line.startswith("echo -n 'MARK:probe'")
