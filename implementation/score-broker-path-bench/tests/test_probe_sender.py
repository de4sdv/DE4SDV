"""Build-and-run contract for the probe sender (de4sdv_probe_send).

The off-VM harness used toybox nc or OpenBSD nc as a stand-in, and that hid
real defects: toybox nc never binds the source port or device and loops after
EOF on a UDP socket (reviews R39, R40, R41, R43). The bench replaces nc on the
probe path with one small POSIX C sender that binds the egress device
(SO_BINDTODEVICE), the source address and the source port, sends one datagram
or does one timed TCP connect, and exits with the errno. This test compiles it
with the host C compiler and exercises it in an unprivileged user and network
namespace, so CI proves the properties the real guest needs:

- the datagram leaves on the bound device, whatever the route says (R41);
- the source port on the wire is the one asked for (R43);
- a refused or unreachable target gives the errno as the exit code, and the
  tool never hangs (R39, R40);
- a bad source address fails closed with its errno.

It never runs on the VM and never opens a privileged socket on the host: the
whole exercise is inside the namespace. It skips only when the C compiler or
unprivileged user namespaces are unavailable (an environment gap, not a tool
defect); on CI (ubuntu-latest) and the bench host both are present.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parents[1]
SOURCE = BENCH / "aosp-overlay" / "probe-sender" / "de4sdv_probe_send.c"

INNER = r'''
import json, socket, struct, subprocess, sys, time

SENDER = sys.argv[1]

def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

def setup():
    sh("ip link set lo up")
    for dev, addr in (("d0", "192.168.98.118"), ("d1", "192.168.97.118")):
        sh(f"ip link add {dev} type dummy")
        sh(f"ip addr add {addr}/24 dev {dev}")
        sh(f"ip link set {dev} up")
    # A blackhole route so a connect out d0 to this net gets no reply (timeout path).
    sh("ip route add 10.9.9.0/24 dev d0")

def tap(dev):
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))
    s.bind((dev, 0)); s.setblocking(False)
    return s

def drain(s):
    """UDP (sport, payload) pairs seen on a tap."""
    out = []
    while True:
        try:
            data = s.recv(65535)
        except BlockingIOError:
            break
        if len(data) >= 14 + 20 + 8 and data[12:14] == b"\x08\x00" and data[14 + 9] == 17:
            ihl = (data[14] & 0x0f) * 4
            sport = struct.unpack(">H", data[14 + ihl:14 + ihl + 2])[0]
            out.append([sport, data[14 + ihl + 8:].rstrip(b"\x00").decode("latin1")])
    return out

def send(args, stdin=b""):
    t0 = time.monotonic()
    p = subprocess.run([SENDER, *args], input=stdin, capture_output=True, timeout=10)
    return {"rc": p.returncode, "elapsed": time.monotonic() - t0, "stderr": p.stderr.decode("latin1")}

def main():
    setup()
    t0, t1 = tap("d0"), tap("d1")
    results = {}

    # a) UDP on the bound device, with the asked source port and payload.
    results["udp_on_device"] = send(
        ["--device", "d0", "--source", "192.168.98.118", "--sport", "41001",
         "--host", "192.168.98.1", "--port", "30160"], stdin=b"MARK:a")
    time.sleep(0.15)
    results["udp_on_device"]["d0"] = drain(t0)
    results["udp_on_device"]["d1"] = drain(t1)

    # b) The device overrides the route: dest 192.168.97.1 routes via d1, but
    #    bound to d0 it must leave on d0 (review R41).
    results["udp_egress_override"] = send(
        ["--device", "d0", "--source", "192.168.98.118", "--sport", "41002",
         "--host", "192.168.97.1", "--port", "30160"], stdin=b"MARK:b")
    time.sleep(0.15)
    results["udp_egress_override"]["d0"] = drain(t0)
    results["udp_egress_override"]["d1"] = drain(t1)

    # c) A bad source address fails closed with EADDRNOTAVAIL (99).
    results["udp_bad_source"] = send(
        ["--device", "d0", "--source", "10.0.0.9", "--sport", "41003",
         "--host", "192.168.98.1", "--port", "30160"], stdin=b"x")

    # d) TCP connect to a real listener on lo gives exit 0.
    lis = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lis.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    lis.bind(("127.0.0.1", 0)); lis.listen(1)
    port = lis.getsockname()[1]
    results["tcp_connect_ok"] = send(
        ["--tcp", "--device", "lo", "--source", "127.0.0.1", "--sport", "0",
         "--host", "127.0.0.1", "--port", str(port), "--timeout-ms", "1000"])

    # e) TCP to a closed port gives ECONNREFUSED (111).
    results["tcp_refused"] = send(
        ["--tcp", "--device", "lo", "--source", "127.0.0.1", "--sport", "0",
         "--host", "127.0.0.1", "--port", "65533", "--timeout-ms", "1000"])

    # f) TCP to a blackholed address times out and returns promptly (never hangs).
    results["tcp_timeout"] = send(
        ["--tcp", "--device", "d0", "--source", "192.168.98.118", "--sport", "0",
         "--host", "10.9.9.9", "--port", "4721", "--timeout-ms", "400"])

    print(json.dumps(results))

main()
'''


def _userns_ok() -> bool:
    try:
        return subprocess.run(["unshare", "-rn", "true"], capture_output=True, timeout=10).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _compile(tmp_path: Path) -> Path:
    cc = shutil.which("cc") or shutil.which("gcc")
    if cc is None:
        pytest.skip("no C compiler (cc/gcc) to build the probe sender")
    binary = tmp_path / "de4sdv_probe_send"
    result = subprocess.run([cc, "-O2", "-Wall", "-Wextra", "-Werror", "-std=c11",
                             str(SOURCE), "-o", str(binary)], capture_output=True, text=True)
    assert result.returncode == 0, f"the sender did not compile:\n{result.stderr}"
    return binary


@pytest.fixture(scope="module")
def ns_results(tmp_path_factory) -> dict:
    tmp_path = tmp_path_factory.mktemp("probe-sender")
    binary = _compile(tmp_path)
    if not _userns_ok():
        pytest.skip("unprivileged user+net namespaces are not available here")
    inner = tmp_path / "inner.py"
    inner.write_text(INNER)
    result = subprocess.run(["unshare", "-rn", sys.executable, str(inner), str(binary)],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, f"the namespace exercise failed:\n{result.stderr}"
    return json.loads(result.stdout)


def test_the_sender_compiles():
    # A standalone compile check, so a syntax error is a clear failure even
    # where the namespace is unavailable.
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        _compile(Path(d))


def test_udp_leaves_on_the_bound_device_with_the_asked_source_port(ns_results):
    case = ns_results["udp_on_device"]
    assert case["rc"] == 0, case["stderr"]
    assert case["d0"] == [[41001, "MARK:a"]]
    assert case["d1"] == []


def test_the_bound_device_overrides_the_route(ns_results):
    # Review R41: a datagram to an address the route would send out d1 leaves
    # on d0 because the device is bound; coverage can trust the named interface.
    case = ns_results["udp_egress_override"]
    assert case["rc"] == 0, case["stderr"]
    assert case["d0"] == [[41002, "MARK:b"]]
    assert case["d1"] == []


def test_a_bad_source_address_fails_closed_with_its_errno(ns_results):
    assert ns_results["udp_bad_source"]["rc"] == 99  # EADDRNOTAVAIL


def test_tcp_connect_to_a_listener_succeeds(ns_results):
    case = ns_results["tcp_connect_ok"]
    assert case["rc"] == 0, case["stderr"]
    assert case["elapsed"] < 3


def test_tcp_connect_refused_reports_the_errno(ns_results):
    case = ns_results["tcp_refused"]
    assert case["rc"] == 111  # ECONNREFUSED
    assert case["elapsed"] < 3


def test_tcp_connect_times_out_and_never_hangs(ns_results):
    # Review R39/R40: a send to an unanswered target returns at the timeout,
    # with the errno, and never loops.
    case = ns_results["tcp_timeout"]
    assert case["rc"] == 110  # ETIMEDOUT
    assert 0.3 <= case["elapsed"] < 3
