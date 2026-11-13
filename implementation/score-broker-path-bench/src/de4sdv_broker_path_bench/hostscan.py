"""Host-side readers of the bench scripts: ss, nft, ip, /proc, and a control listener.

The VM scripts run standard tools and hand their raw output to these
functions, so the code that turns tool output into records is the code the
tests run (review R28: an inline parser in a script went untested and read
the wrong column). Each reader takes the text a tool prints and returns
plain data. The command line (``python3 -m de4sdv_broker_path_bench.hostscan``)
is what the scripts call. Nothing here sends a packet; the control listener
only receives.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import signal
import socket
import sys
import time
from pathlib import Path

from . import sd
from .pcap import PcapError, datagrams, read_pcap

TCP_SYN = 0x02
TCP_ACK = 0x10

#: The layer's two ROS 2 processes (the Launch Manager's binary names of the
#: reference interop bench). ss and the kernel give a process name of at most
#: 15 characters, so a name matches on that prefix, exactly.
LAYER_PROCESSES = ("de4sdv_score_adapter", "de4sdv_health_proxy")
#: The adapter, the one client the frame assembler may have (ASM-MW-029).
ADAPTER_PROCESS = "de4sdv_score_adapter"
COMM_LENGTH = 15

_ADDRESS = re.compile(r"^(?P<addr>\[[^\]]*\]|[^\s\[\]]*?)(?:%(?P<dev>[^\s:]+))?:(?P<port>\d+|\*)$")
_USER = re.compile(r'\("(?P<name>[^"]*)",pid=(?P<pid>\d+)')
_NETIDS = {"udp", "tcp", "raw", "u_dgr", "u_str", "u_seq", "nl", "p_raw", "p_dgr", "sctp", "mptcp"}


def _address(token: str) -> tuple[str, str | None, int | None] | None:
    match = _ADDRESS.match(token)
    if match is None:
        return None
    port = match["port"]
    return match["addr"], match["dev"], None if port == "*" else int(port)


def _processes(line: str) -> list[dict]:
    return [{"name": match["name"], "pid": int(match["pid"])} for match in _USER.finditer(line)]


def parse_ss(text: str, protocol: str | None) -> list[dict]:
    """The sockets of an ``ss -H -l -n -p`` listing, with or without its Netid column.

    The local address is the first address column, the peer the second. With
    one protocol selected, ss prints no Netid column, so the columns shift by
    one; the parser finds the address columns instead of counting them.
    ``protocol`` names the protocol when the listing has no Netid column.
    """
    rows = []
    for line in text.splitlines():
        tokens = line.split()
        if not tokens:
            continue
        netid = tokens[0].lower() if tokens[0].lower() in _NETIDS else None
        addresses = [(index, parsed) for index, token in enumerate(tokens)
                     if ":" in token and not token.startswith("users:") and (parsed := _address(token))]
        if len(addresses) < 2:
            continue
        (_index, (addr, dev, port)) = addresses[0]
        if port is None:
            continue
        rows.append({"protocol": netid or protocol or "", "address": addr, "device": dev, "port": port,
                     "processes": _processes(line)})
    return rows


def _comm_matches(name: str, wanted: tuple[str, ...]) -> bool:
    return any(name == candidate[:COMM_LENGTH] for candidate in wanted)


def listeners(udp_text: str, tcp_text: str, layer_names: tuple[str, ...] = LAYER_PROCESSES) -> list[dict]:
    """The host listeners of the probe (host_listeners.json): UDP and TCP sockets with their owner.

    ``element_in_layer`` is True when a process of the socket is a layer
    process, False when its processes are all others, and None when ss shows
    no process (the owner is unknown, for example without root).
    """
    rows = []
    for protocol, text in (("udp", udp_text), ("tcp", tcp_text)):
        for socket_row in parse_ss(text, protocol):
            processes = socket_row["processes"]
            if not processes:
                membership = None
            else:
                membership = any(_comm_matches(item["name"], layer_names) for item in processes)
            rows.append({"address": socket_row["address"], "port": socket_row["port"],
                         "protocol": socket_row["protocol"],
                         "element": processes[0]["name"] if processes else "",
                         "pid": processes[0]["pid"] if processes else None,
                         "element_in_layer": membership})
    return rows


# ---------------------------------------------------------------- ASM-MW-029

def parse_ss_established(text: str) -> list[dict]:
    """The connections of ``ss -H -t -n -p state established ...``: local, peer and processes."""
    rows = []
    for line in text.splitlines():
        tokens = line.split()
        addresses = [parsed for token in tokens
                     if ":" in token and not token.startswith("users:") and (parsed := _address(token))]
        if len(addresses) < 2:
            continue
        (laddr, _ldev, lport), (paddr, _pdev, pport) = addresses[0], addresses[1]
        rows.append({"local": f"{laddr}:{lport}", "peer": f"{paddr}:{pport}", "processes": _processes(line)})
    return rows


def _is_loopback(address: str) -> bool:
    host = address.rsplit(":", 1)[0].strip("[]")
    return host.startswith("127.") or host in ("::1", "::ffff:127.0.0.1")


def client_check(sport_text: str, dport_text: str, phase: str, adapter: str = ADAPTER_PROCESS) -> dict:
    """The two steps of the ASM-MW-029 client check (VC-MW-015).

    Step 1 (``sport = :4721``): the frame assembler holds exactly one
    connection, from a loopback peer. Step 2 (``dport = :4721``): the client
    socket of that peer belongs to the adapter process. Both must hold.
    """
    accepted = parse_ss_established(sport_text)
    clients = parse_ss_established(dport_text)
    peers = sorted(row["peer"] for row in accepted)
    check = {"phase": phase, "peers": peers, "adapter_peer": None, "holds": False,
             "sport_rows": accepted, "dport_rows": clients}
    if len(accepted) != 1:
        check["detail"] = f"the frame assembler holds {len(accepted)} connections, not exactly one"
        return check
    peer = accepted[0]["peer"]
    if not _is_loopback(peer):
        check["detail"] = f"its client {peer} is not on a loopback address"
        return check
    owners = [row for row in clients if row["local"] == peer]
    names = sorted({item["name"] for row in owners for item in row["processes"]})
    if not owners or not names:
        check["detail"] = f"no process is shown for the client socket {peer} (step 2)"
        return check
    if not all(_comm_matches(name, (adapter,)) for name in names):
        check["detail"] = f"the client {peer} is {names}, not the adapter"
        return check
    check.update(holds=True, adapter_peer=peer, detail=f"one loopback client {peer}, the adapter")
    return check


def record_client_check(path: Path, check: dict) -> dict:
    """Add one check to frame_assembler_clients.json; adapter_only holds only if every check holds."""
    record = {"checks": []}
    if path.exists():
        try:
            loaded = json.loads(path.read_text())
            if isinstance(loaded, dict) and isinstance(loaded.get("checks"), list):
                record = loaded
        except (OSError, json.JSONDecodeError):
            pass
    record["checks"] = [item for item in record["checks"] if item.get("phase") != check["phase"]] + [check]
    phases = {item.get("phase") for item in record["checks"]}
    record["adapter_only"] = bool(record["checks"]) and all(item.get("holds") is True for item in record["checks"])
    record["complete"] = {"before", "after"} <= phases
    path.write_text(json.dumps(record, indent=1) + "\n")
    return record


# ---------------------------------------------------------------- nft

_COUNTER = re.compile(r"\bcounter packets (\d+) bytes (\d+)\b")


def nft_counters(text: str) -> dict:
    """The packet counters of the isolation rules in ``nft -a list table inet de4sdv_bench``.

    Every DDS drop rule (``udp dport @dds_...`` with ``drop``) adds to
    ``dds_packets``, so a duplicated rule cannot hide a count. A table without
    readable counters gives None: the probe then cannot judge a datagram.
    """
    present = bool(re.search(r"^table inet \S+", text, re.MULTILINE))
    dds = [int(m.group(1)) for line in text.splitlines()
           if re.search(r"udp dport @dds\S*", line) and " drop" in line and (m := _COUNTER.search(line))]
    dds_rules = sum(1 for line in text.splitlines() if re.search(r"udp dport @dds\S*", line) and " drop" in line)
    tcp = [int(m.group(1)) for line in text.splitlines()
           if re.search(r"tcp dport 4721\b", line) and " drop" in line and (m := _COUNTER.search(line))]
    tcp_rules = sum(1 for line in text.splitlines() if re.search(r"tcp dport 4721\b", line) and " drop" in line)
    return {"table": present, "dds_rules": dds_rules,
            "dds_packets": sum(dds) if present and dds and len(dds) == dds_rules else None,
            "tcp_rules": tcp_rules,
            "tcp_packets": sum(tcp) if present and tcp and len(tcp) == tcp_rules else None}


# ---------------------------------------------------------------- the capture witness

_MARKER = re.compile(rb"MARK:[0-9A-Za-z._-]+")


def _capture_sources(sources) -> list[tuple[str | None, Path]]:
    """(host interface, path) of each capture: a (name, path) pair, an ``IFACE=PATH`` token, or a bare path.

    A bare path ``capture-<iface>.pcap`` names its interface; any other bare
    path has no known interface (its markers then carry ``capture_interface``
    None, which the evaluator cannot attribute).
    """
    found = []
    for source in sources:
        if isinstance(source, tuple):
            found.append((source[0], Path(source[1])))
            continue
        text = str(source)
        if "=" in text and not Path(text).exists():
            name, _, path = text.partition("=")
            found.append((name or None, Path(path)))
            continue
        match = re.match(r"^capture-(.+)\.pcap$", Path(text).name)
        found.append((match.group(1) if match else None, Path(text)))
    return found


def capture_markers(sources, assembler_port: int = 4721) -> dict:
    """What the guest-facing captures saw, and where: the UDP markers and the TCP SYNs to the frame assembler.

    The captures are taken on the host, before netfilter, so a datagram the
    isolation rule then drops still appears here. The probe pairs this with
    the drop counter: captured and not dropped is a reach. A UDP marker is the
    ``MARK:...`` string in a datagram's payload; a captured 4721 connection is
    a SYN (no ACK) to the host's 4721.

    For each captured marker and SYN it records the host capture interface,
    and the source address and source MAC of the frame (review R41), so the
    evaluator can check that a probe left on the guest interface it names,
    from the source it names. A frame seen on two host interfaces (a bridge
    member and its bridge) is kept once per interface. ``sources`` is a list
    of (interface, path) pairs, ``IFACE=PATH`` tokens or bare paths.
    """
    udp_markers: set[str] = set()
    udp_captures: list[dict] = []
    tcp_syns: list[dict] = []
    seen_udp: set[tuple] = set()
    seen_syn: set[tuple] = set()
    problems: list[str] = []
    for interface, path in _capture_sources(sources):
        if not path.exists():
            continue
        try:
            capture = read_pcap(path)
        except PcapError as error:
            problems.append(f"{path}: {error}")
            continue
        for item in datagrams(capture):
            if item.protocol == "udp":
                for match in _MARKER.findall(item.payload):
                    marker = match.decode("ascii")
                    udp_markers.add(marker)
                    key = (marker, interface, item.src, item.src_mac, item.dst, item.sport, item.dport, item.vlans)
                    if key not in seen_udp:
                        seen_udp.add(key)
                        udp_captures.append({"marker": marker, "capture_interface": interface, "src": item.src,
                                             "src_mac": item.src_mac, "dst": item.dst, "sport": item.sport,
                                             "dport": item.dport, "vlans": list(item.vlans)})
            elif item.protocol == "tcp" and item.dport == assembler_port \
                    and item.tcp_flags & TCP_SYN and not item.tcp_flags & TCP_ACK:
                key = (item.dst, item.dport, item.src, item.sport, item.src_mac, interface)
                if key not in seen_syn:
                    seen_syn.add(key)
                    tcp_syns.append({"host": item.dst, "port": item.dport, "src": item.src, "sport": item.sport,
                                     "src_mac": item.src_mac, "capture_interface": interface})
    return {"udp_markers": sorted(udp_markers), "udp_captures": udp_captures, "tcp_syns": tcp_syns,
            "problems": problems}


# ---------------------------------------------------------------- ip

_IP_LINE = re.compile(r"^\d+:\s+(?P<name>[^\s:@]+)(?:@\S+)?:?\s")
_IPV4 = re.compile(r"\binet (\d+\.\d+\.\d+\.\d+)/\d+")


def parse_ip_addr(text: str) -> dict[str, list[str]]:
    """Interface to IPv4 addresses, from ``ip -o link show`` and ``ip -o -4 addr show`` lines."""
    found: dict[str, list[str]] = {}
    for line in text.splitlines():
        match = _IP_LINE.match(line)
        if match is None:
            continue
        name = match["name"]
        addresses = found.setdefault(name, [])
        for address in _IPV4.findall(line):
            if address not in addresses:
                addresses.append(address)
    return found


def parse_guest_inventory(text: str) -> dict[str, dict[str, list[str]]]:
    """Namespace to interface to IPv4 addresses, from the probe's sectioned guest listing.

    The probe writes ``# netns: <name>`` (empty for the root namespace) and
    then that namespace's ``ip -o link show`` and ``ip -o -4 addr show``.
    """
    sections: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        if line.startswith("# netns:"):
            current = line[len("# netns:"):].strip()
            sections.setdefault(current, [])
        elif current is not None:
            sections[current].append(line)
    return {name: parse_ip_addr("\n".join(lines)) for name, lines in sections.items()}


_MAC = re.compile(r"\blink/ether ([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})\b")


def parse_guest_macs(text: str) -> dict[str, dict[str, str | None]]:
    """Namespace to interface to MAC address (``link/ether``), from the probe's sectioned guest listing.

    The probe names each guest interface by name; the host sees the frame's
    source MAC, so the MAC ties a captured probe to the guest interface it left
    on (review R41). An interface with no Ethernet address (lo) gives None.
    """
    sections: dict[str, dict[str, str | None]] = {}
    current = None
    for line in text.splitlines():
        if line.startswith("# netns:"):
            current = line[len("# netns:"):].strip()
            sections.setdefault(current, {})
            continue
        if current is None:
            continue
        match = _IP_LINE.match(line)
        if match is None:
            continue
        mac = _MAC.search(line)
        known = sections[current].get(match["name"])
        sections[current][match["name"]] = known or (mac.group(1).lower() if mac else None)
    return sections


def host_addresses(text: str, pattern: str = "cvd-*") -> list[str]:
    """Every IPv4 address of a host interface whose name matches ``pattern`` (VC-MW-017: cvd-* addresses)."""
    addresses = []
    for name, found in parse_ip_addr(text).items():
        if fnmatch.fnmatch(name, pattern):
            addresses.extend(found)
    return sorted(set(addresses), key=lambda a: tuple(int(p) for p in a.split(".")))


def route_device(text: str) -> tuple[str, str | None] | None:
    """(device, source) of an ``ip route get`` answer, or None when there is no route."""
    first = text.strip().splitlines()[0] if text.strip() else ""
    if not first or "unreachable" in first.lower() or first.startswith(("RTNETLINK", "Error")):
        return None
    dev = re.search(r"\bdev (\S+)", first)
    src = re.search(r"\bsrc (\S+)", first)
    if dev is None:
        return None
    return dev.group(1), src.group(1) if src else None


def neigh_state(text: str) -> str | None:
    """The state of an ``ip neigh show <addr> dev <if>`` entry (REACHABLE, FAILED, ...), or None."""
    for line in text.splitlines():
        states = re.findall(r"\b(REACHABLE|STALE|DELAY|PROBE|FAILED|INCOMPLETE|PERMANENT|NOARP|NONE)\b", line)
        if states:
            return states[-1]
    return None


# ---------------------------------------------------------------- ASM-MW-031

#: The one ROS 2 environment of the host (adapterAbortConditions, ASM-MW-031).
EXPECTED_ENVIRONMENT = {"distro": "humble", "rmw": "rmw_cyclonedds_cpp", "domain": "91", "max_participant_index": 120}
_ROS_LIBRARIES = ("librcl.so", "librmw.so", "librmw_implementation", "librclpy", "librcutils.so", "libddsc.so")
_ROS_VARIABLES = ("RMW_IMPLEMENTATION", "ROS_DISTRO", "ROS_DOMAIN_ID", "AMENT_PREFIX_PATH", "ROS_VERSION")


def _max_participant_index(uri: str | None, root: Path) -> tuple[int | None, str]:
    """MaxAutoParticipantIndex of a CYCLONEDDS_URI, and how it was read."""
    if not uri:
        return None, "CYCLONEDDS_URI unset (CycloneDDS default range)"
    texts = []
    for part in re.split(r"[,\s]+", uri.strip()):
        if not part:
            continue
        if part.startswith("<"):
            texts.append(part)
            continue
        path = part[len("file://"):] if part.startswith("file://") else part
        try:
            texts.append(Path(path).read_text())
        except OSError as error:
            return None, f"{path} unreadable ({error.__class__.__name__})"
    if not texts and uri.strip().startswith("<"):
        texts.append(uri)
    for text in texts:
        match = re.search(r"<MaxAutoParticipantIndex>\s*(\d+)\s*</MaxAutoParticipantIndex>", text)
        if match:
            return int(match.group(1)), "from CYCLONEDDS_URI"
    return None, "CYCLONEDDS_URI names no MaxAutoParticipantIndex (CycloneDDS default range)"


def asm_mw_031(proc_root: str | Path = "/proc", expected: dict | None = None) -> dict:
    """The ROS 2 environment of every ROS 2 process on the host (VC-MW-017, ASM-MW-031).

    A process is a ROS 2 process when its environment names ROS 2 or its maps
    load a ROS 2 or CycloneDDS library. Each one must run the one environment:
    distribution, middleware, domain and participant range. ``holds`` is True
    only when every ROS 2 process shows all four, False when one shows another
    value, and None (unknown) when a process could not be read: then the case
    shows nothing about the other processes. Run it as root.
    """
    expected = dict(EXPECTED_ENVIRONMENT if expected is None else expected)
    root = Path(proc_root)
    processes, unreadable, problems = [], [], []
    for entry in sorted(root.iterdir(), key=lambda p: (len(p.name), p.name)):
        if not entry.name.isdigit():
            continue
        try:
            cmdline = [part.decode("utf-8", "replace") for part in (entry / "cmdline").read_bytes().split(b"\0") if part]
        except OSError:
            continue  # the process is gone
        if not cmdline:
            continue  # a kernel thread
        try:
            raw_environ = (entry / "environ").read_bytes()
            maps = (entry / "maps").read_text(errors="replace")
        except PermissionError:
            unreadable.append({"pid": int(entry.name), "cmdline": cmdline[:4]})
            continue
        except OSError:
            continue
        environ = dict(part.decode("utf-8", "replace").split("=", 1) for part in raw_environ.split(b"\0") if b"=" in part)
        by_env = any(name in environ for name in _ROS_VARIABLES)
        by_maps = any(library in maps for library in _ROS_LIBRARIES)
        if not (by_env or by_maps):
            continue
        distro = environ.get("ROS_DISTRO")
        if distro is None:
            found = sorted(set(re.findall(r"/opt/ros/([a-z]+)/", maps)))
            distro = found[0] if len(found) == 1 else None
        index, index_source = _max_participant_index(environ.get("CYCLONEDDS_URI"), root)
        record = {"pid": int(entry.name), "cmdline": cmdline[:4], "found_by": "environment" if by_env else "libraries",
                  "distro": distro, "rmw": environ.get("RMW_IMPLEMENTATION"), "domain": environ.get("ROS_DOMAIN_ID"),
                  "max_participant_index": index, "index_source": index_source}
        processes.append(record)
        for key in ("distro", "rmw", "domain", "max_participant_index"):
            if record[key] != expected[key]:
                problems.append(f"pid {record['pid']} ({cmdline[0]}): {key} {record[key]!r}, not {expected[key]!r}")
    if not processes:
        holds = None
        problems.append("no ROS 2 process found on the host")
    elif problems:
        holds = False
    elif unreadable:
        holds = None
    else:
        holds = True
    if unreadable and holds is not False:
        problems.append(f"{len(unreadable)} processes could not be read (run the scan as root)")
    return {"holds": holds, "expected": expected, "processes": processes, "unreadable": unreadable,
            "problems": problems}


# ---------------------------------------------------------------- the MONITORING gate

_APP_EPOCH = re.compile(r"^\s*(\d+(?:\.\d+)?)\s")
_NOT_MONITORING = ("intervention=true", "warning=true", "braking=true", "lifecycle=released_verified_stop")


def monitoring_gate(logcat_text: str, *, now_epoch_s: float, max_age_s: float) -> dict:
    """Whether the HMI shows MONITORING now: the app's latest frame line, if fresh (review R26).

    The app logs one ``onGatewayFrame`` line per frame (INC-AEBS-010
    MainActivity.java). MONITORING is not intervention, not warning, not
    braking, and lifecycle not released. The latest line decides, and only if
    it is at most ``max_age_s`` older than the guest clock ``now_epoch_s`` (the
    guest clock is read to the second, so a line up to one second "ahead" is
    accepted); an old MONITORING line in the buffer does not open the gate.
    """
    latest = None
    for line in logcat_text.splitlines():
        if "onGatewayFrame" not in line:
            continue
        match = _APP_EPOCH.match(line)
        if match is None:
            continue
        stamp = float(match.group(1))
        if latest is None or stamp >= latest[0]:
            latest = (stamp, line.strip())
    if latest is None:
        return {"monitoring": False, "line": None, "age_s": None, "max_age_s": max_age_s,
                "reason": "no timestamped onGatewayFrame line"}
    stamp, line = latest
    age = round(now_epoch_s - stamp, 6)
    record = {"monitoring": False, "line": line, "age_s": age, "max_age_s": max_age_s}
    if age > max_age_s:
        record["reason"] = f"the latest frame line is {age} s old, more than {max_age_s} s"
    elif age < -1.0:
        record["reason"] = f"the latest frame line is {-age} s ahead of the guest clock"
    elif any(flag in line for flag in _NOT_MONITORING):
        record["reason"] = "the latest frame is not MONITORING"
    else:
        record.update(monitoring=True, reason="the latest frame is MONITORING and fresh")
    return record


# ---------------------------------------------------------------- control listener

def control_listen(port: int, out: Path, seconds: float) -> int:
    """Receive datagrams on 0.0.0.0:port and record each one (the bench's own control socket)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port))
    sock.settimeout(0.5)
    stop = [False]

    def _stop(*_args):
        stop[0] = True

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    end = time.monotonic() + seconds
    with open(out, "a") as handle:
        while not stop[0] and time.monotonic() < end:
            try:
                data, peer = sock.recvfrom(4096)
            except socket.timeout:
                continue
            handle.write(json.dumps({"realtime_ns": time.time_ns(), "src": peer[0], "sport": peer[1], "port": port,
                                     "payload": data.decode("utf-8", "replace")}) + "\n")
            handle.flush()
    return 0


# ---------------------------------------------------------------- command line

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python3 -m de4sdv_broker_path_bench.hostscan", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("listeners", help="host_listeners.json from ss -H -u/-t -l -n -p listings")
    p.add_argument("--udp", action="append", default=[])
    p.add_argument("--tcp", action="append", default=[])
    p = sub.add_parser("counters", help="the isolation counters of an nft -a list table listing")
    p.add_argument("file")
    p = sub.add_parser("captured", help="captured_markers.json from the guest-facing capture pcaps (IFACE=PATH)")
    p.add_argument("pcap", nargs="+", help="IFACE=PATH per capture (a bare capture-<iface>.pcap names its interface)")
    p = sub.add_parser("clients", help="one ASM-MW-029 check from the two ss steps, added to the record")
    p.add_argument("--sport", required=True)
    p.add_argument("--dport", required=True)
    p.add_argument("--phase", required=True, choices=("before", "after"))
    p.add_argument("--record", required=True)
    p = sub.add_parser("asm031", help="the ASM-MW-031 record of every ROS 2 process (run as root)")
    p.add_argument("--proc", default="/proc")
    p = sub.add_parser("host-addresses", help="the cvd-* host addresses of an ip -o -4 addr show listing")
    p.add_argument("file")
    p = sub.add_parser("guest-ifaces", help="namespace, interface, first IPv4 and MAC of a guest inventory, one per line")
    p.add_argument("file")
    p = sub.add_parser("route", help="device and source of an ip route get answer")
    p.add_argument("file")
    p = sub.add_parser("sd-processed", help="sd_core_processed.json from the SDV Core VM logcat around the offer")
    p.add_argument("--logcat", required=True)
    p.add_argument("--since", type=float, required=True, help="the core clock (epoch s) just before the send")
    p.add_argument("--provider", help="the spoofed offer's provider address")
    p.add_argument("--processed-pattern", action="append", default=None, metavar="NAME=REGEX")
    p.add_argument("--ignored-pattern", action="append", default=None, metavar="NAME=REGEX")
    p.add_argument("--out", required=True)
    p = sub.add_parser("monitoring", help="the time-bounded MONITORING gate over the app's logcat (exit 1 if shut)")
    p.add_argument("--logcat", required=True)
    p.add_argument("--now", type=float, required=True, help="the guest clock (epoch s) when the logcat was read")
    p.add_argument("--max-age", type=float, default=2.0)
    p = sub.add_parser("control-listen", help="record what the bench's control socket receives")
    p.add_argument("--port", type=int, required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--seconds", type=float, default=3600)
    args = parser.parse_args(argv)

    def read(path: str) -> str:
        return Path(path).read_text(errors="replace") if path and Path(path).exists() else ""

    if args.command == "listeners":
        rows = listeners("".join(read(p) for p in args.udp), "".join(read(p) for p in args.tcp))
        # Two listings (before and after the probe) list the same socket twice; keep one row each.
        unique = {(r["protocol"], r["address"], r["port"], r["pid"]): r for r in rows}
        print(json.dumps(list(unique.values()), indent=1))
    elif args.command == "counters":
        print(json.dumps(nft_counters(read(args.file))))
    elif args.command == "captured":
        found = capture_markers(args.pcap)
        print(json.dumps({"udp_markers": found["udp_markers"], "udp_captures": found["udp_captures"],
                          "tcp_syns": found["tcp_syns"], "problems": found["problems"]}, indent=1))
    elif args.command == "clients":
        check = client_check(read(args.sport), read(args.dport), args.phase)
        record = record_client_check(Path(args.record), check)
        print(json.dumps({"phase": args.phase, "holds": check["holds"], "detail": check["detail"],
                          "adapter_only": record["adapter_only"]}))
    elif args.command == "asm031":
        print(json.dumps(asm_mw_031(args.proc), indent=1))
    elif args.command == "host-addresses":
        print("\n".join(host_addresses(read(args.file))))
    elif args.command == "guest-ifaces":
        text = read(args.file)
        macs = parse_guest_macs(text)
        for netns, interfaces in parse_guest_inventory(text).items():
            for name, addresses in interfaces.items():
                if name != "lo":
                    mac = macs.get(netns, {}).get(name)
                    print(f"{netns or '-'} {name} {addresses[0] if addresses else '-'} {mac or '-'}")
    elif args.command == "route":
        found = route_device(read(args.file))
        print(f"{found[0]} {found[1] or '-'}" if found else "none")
    elif args.command == "sd-processed":
        def patterns(items):
            return None if items is None else [tuple(item.split("=", 1)) for item in items if "=" in item]
        record = sd.core_offer_record(read(args.logcat), since_epoch_s=args.since, provider=args.provider,
                                      processed_patterns=patterns(args.processed_pattern),
                                      ignored_patterns=patterns(args.ignored_pattern))
        Path(args.out).write_text(json.dumps(record, indent=1) + "\n")
        print(json.dumps({"status": record["status"], "result": record["result"], "line": record["matched_line"]}))
    elif args.command == "monitoring":
        record = monitoring_gate(read(args.logcat), now_epoch_s=args.now, max_age_s=args.max_age)
        print(json.dumps(record))
        return 0 if record["monitoring"] else 1
    elif args.command == "control-listen":
        return control_listen(args.port, Path(args.out), args.seconds)
    return 0


if __name__ == "__main__":
    sys.exit(main())
