"""Read side of the REQ-MW-016 reachability check (VC-MW-017, second finding).

The check is a property: no DDS port of a host ROS 2 process is reachable
from any guest domain, and port 4721 of the frame assembler is not either
(ASM-MW-029). The bench proves isolation, so a pass means the probes did
NOT reach a host port. The probing runs in scripts/host_isolation_probe.sh
with standard tools; this module reads what those tools recorded and
classifies each probe. It never opens a socket.

Reachability is judged as #448 asks: a capture on the guest-facing
interface and the counters of the isolation rule (both). A probe is:

- reached   when its marker was captured on the host AND the isolation
            counter did not take it (it arrived and was not dropped), or when
            a host socket received it, or the guest's own TCP connect
            completed (direct evidence, which needs no counter);
- isolated  when the isolation counter took it (dropped);
- unknown   when the guest send failed, the record is incomplete or
            malformed, the probe came from the guest's loopback, or the
            marker never arrived at the host: nothing is shown, and each such
            probe is a coverage gap, never silently skipped.

A pre-netfilter capture alone over-counts: it also sees datagrams the rule
then drops. So the counter decides reached vs dropped. If the isolation
table is absent, or its counters cannot be read, the probe cannot tell a
drop from a delivery, so the whole run is inconclusive (it never passes
without a working, readable firewall).

The positive control uses the same capture observation and, because its
target is the bench's own socket, must also have been delivered there. A
control that was captured and not dropped by the bench rule yet not
delivered shows the capture-plus-counter method did not observe a reachable
datagram as reached, so the run is inconclusive.

Run artifacts this module reads (JSON), all written by the probe script:
- firewall.json: {inet_table_present, dds_counters_readable,
  tcp_counters_readable}, the validity gate.
- host_listeners.json: the host sockets, each {address, port, protocol,
  element, pid, element_in_layer} (hostscan.listeners of a real ss listing).
- probe_attempts.json: one record per (guest, interface, src_addr, host,
  port, protocol) with a unique marker, the send status, the per-probe
  counter movement and, for TCP, the guest connect result.
- captured_markers.json: {udp_markers: [...], tcp_syns: [{host, port}]},
  what the guest-facing capture saw (pre-netfilter).
- control.json: {captured, counter_moved, delivered, detail}.
- coverage.json: {per_guest: {guest: {expected_interfaces,
  expected_host_addresses, probed_interfaces, probed_host_addresses}}}, with
  the expected sets derived independently of the probed ones.
- asm_mw_031.json: {holds: bool|null, ...} for the ROS 2 processes.
- inspection.json (first finding): {no_host_endpoint: bool, ...}.
- host_socket_receipts.json (optional): {udp_markers, tcp_connects}, what a
  host socket received where a run records it; the probe script does not
  write it, so it can only add a reach, never a pass.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: The DDS ports of ROS_DOMAIN_ID 91 with MaxAutoParticipantIndex 120
#: (GAP-MW-046): SPDP/user multicast 30150-30151 and unicast 30160-30401.
DDS_DOMAIN = 91
DDS_MAX_PARTICIPANT_INDEX = 120
#: Port 4721, the frame assembler of INC-AEBS-010 (ASM-MW-029). A reachable
#: 4721 is a finding against ASM-MW-029, not against REQ-MW-016 (#448).
FRAME_ASSEMBLER_PORT = 4721

SENT = "sent"


def _as_int(value: object) -> int | None:
    """A port as an int, or None for a missing or malformed value (hostile input, review R38)."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def dds_udp_ports(domain: int = DDS_DOMAIN, max_index: int = DDS_MAX_PARTICIPANT_INDEX) -> list[int]:
    port_base, domain_gain, participant_gain = 7400, 250, 2
    d0, d1, d2, d3 = 0, 10, 1, 11
    spdp_multicast = port_base + domain_gain * domain + d0
    user_multicast = port_base + domain_gain * domain + d2
    first_unicast = port_base + domain_gain * domain + d1
    last_unicast = port_base + domain_gain * domain + d3 + participant_gain * max_index
    ports = {spdp_multicast, user_multicast}
    ports.update(range(first_unicast, last_unicast + 1))
    return sorted(ports)


def _load(run_dir: Path, name: str, default: Any) -> Any:
    path = run_dir / name
    if not path.exists():
        return None if default is None else default
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return "ERROR"


@dataclass
class IsolationVerdict:
    reached_layer: list[dict] = field(default_factory=list)            # reached DDS port of a layer element
    reached_other: list[dict] = field(default_factory=list)            # reached DDS port of a non-layer process
    reached_frame_assembler: list[dict] = field(default_factory=list)  # reached 4721 (ASM-MW-029)
    unknown_probes: list[dict] = field(default_factory=list)           # sent but neither reached nor dropped
    isolated_probes: int = 0
    table_readable: bool = False
    control_ok: bool = False
    control_detail: str = ""
    asm_mw_031_holds: bool | None = None
    attempts: int = 0
    required_dds_ports: int = 0                                         # the DDS set size required per pair (R45)
    probed_interfaces: dict = field(default_factory=dict)              # guest -> {interface}, from captured attempts
    probed_host_addresses: dict = field(default_factory=dict)         # guest -> {host address}, from captured attempts
    coverage_gaps: list[str] = field(default_factory=list)
    inspection_present: bool = False
    inspection_no_host_endpoint: bool | None = None
    problems: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    # Compatibility aliases for callers that used the earlier names.
    @property
    def layer_reachable(self) -> list[dict]:
        return self.reached_layer

    @property
    def other_reachable(self) -> list[dict]:
        return self.reached_other

    @property
    def frame_assembler_reachable(self) -> list[dict]:
        return self.reached_frame_assembler


def _captured(attempt: dict, captured: dict) -> bool:
    if attempt.get("protocol") == "udp":
        return attempt.get("marker") in set(captured.get("udp_markers", []))
    port = _as_int(attempt.get("port"))
    for syn in captured.get("tcp_syns", []):
        if syn.get("host") == attempt.get("host") and _as_int(syn.get("port")) == port and port is not None:
            return True
    return False


def _loopback_probe(attempt: dict) -> bool:
    """A probe from the guest's loopback: it cannot leave the guest (review R15/R27, N-3)."""
    source = str(attempt.get("src_addr") or "")
    return attempt.get("interface") == "lo" or source.startswith("127.") or source == "::1"


def _classify(attempt: dict, captured: dict, udp_receipts: set, tcp_receipts: set) -> str:
    """received | reached | isolated | unknown | invalid for one probe, from its observation.

    received: direct reach evidence (a host socket received the marker, or the
              guest's own TCP connect completed); it needs no drop counter.
    reached:  the capture saw the marker and the drop counter did not take it.
    isolated: the capture saw the marker and the drop counter took it. The
              capture is required (review R25): a counter that moved without a
              captured marker is not shown to be this probe's datagram.
    unknown:  the send failed, the record is incomplete, or nothing arrived;
              it shows nothing and is a coverage gap, never silently skipped.
    invalid:  a probe from the guest's loopback, which cannot reach the host.
    """
    if _loopback_probe(attempt):
        return "invalid"
    if attempt.get("protocol") == "udp" and attempt.get("marker") in udp_receipts:
        return "received"
    if attempt.get("protocol") == "tcp" and (
            (attempt.get("guest"), _as_int(attempt.get("port"))) in tcp_receipts
            or attempt.get("guest_connected") is True):
        return "received"
    if attempt.get("send_status") != SENT:
        return "unknown"
    if not _captured(attempt, captured):
        return "unknown"  # it never arrived at the host (silent send failure, no route)
    counter_moved = attempt.get("counter_moved")
    if counter_moved is True:
        return "isolated"  # captured and the isolation rule took it (R25)
    if counter_moved is False:
        return "reached"   # captured and the isolation rule did not take it
    return "unknown"       # captured but the counter is unreadable for this probe


def evaluate_isolation(run_dir: str | Path, *, required_dds_ports: set[int] | None = None) -> IsolationVerdict:
    run_dir = Path(run_dir)
    verdict = IsolationVerdict()
    # The DDS set that each probed pair must cover (review R45). The default is
    # the full set of the domain and participant range; a reduced dry run leaves
    # ports unprobed, which the coverage check below reports as a gap.
    required_ports = set(required_dds_ports) if required_dds_ports is not None else set(dds_udp_ports())
    verdict.required_dds_ports = len(required_ports)
    firewall = _load(run_dir, "firewall.json", {})
    listeners = _load(run_dir, "host_listeners.json", [])
    attempts = _load(run_dir, "probe_attempts.json", [])
    captured = _load(run_dir, "captured_markers.json", {})
    control = _load(run_dir, "control.json", {})
    coverage = _load(run_dir, "coverage.json", {})
    asm = _load(run_dir, "asm_mw_031.json", None)
    inspection = _load(run_dir, "inspection.json", None)
    receipts = _load(run_dir, "host_socket_receipts.json", {})

    for name, value in (("firewall", firewall), ("host_listeners", listeners), ("probe_attempts", attempts),
                        ("captured_markers", captured), ("control", control), ("host_socket_receipts", receipts)):
        if value == "ERROR":
            verdict.errors.append(f"{name}.json is not valid JSON")
    if verdict.errors:
        return verdict
    firewall = firewall if isinstance(firewall, dict) else {}
    listeners = listeners if isinstance(listeners, list) else []
    attempts = attempts if isinstance(attempts, list) else []
    captured = captured if isinstance(captured, dict) else {}
    control = control if isinstance(control, dict) else {}
    receipts = receipts if isinstance(receipts, dict) else {}
    # A receipt at a host socket, where a run records one, is direct reach
    # evidence; the probe script does not write one, so this only ever adds a
    # reach (a fail), never a pass.
    udp_receipts = {m for m in receipts.get("udp_markers", []) if isinstance(m, str)} \
        if isinstance(receipts.get("udp_markers"), list) else set()
    tcp_receipts = {(c.get("guest"), _as_int(c.get("port"))) for c in receipts.get("tcp_connects", [])
                    if isinstance(c, dict)} if isinstance(receipts.get("tcp_connects"), list) else set()

    dds_set = set(dds_udp_ports())
    layer_dds_ports = {_as_int(item.get("port")) for item in listeners
                       if isinstance(item, dict) and item.get("element_in_layer") and _as_int(item.get("port")) in dds_set}
    layer_dds_ports.discard(None)
    verdict.attempts = len(attempts)

    # Validity gate: without a readable isolation table the probe cannot tell a
    # drop from a delivery, so it cannot judge reachability (#448, R26).
    verdict.table_readable = bool(firewall.get("inet_table_present")) and \
        bool(firewall.get("dds_counters_readable")) and bool(firewall.get("tcp_counters_readable"))
    if not verdict.table_readable:
        verdict.coverage_gaps.append("the isolation table or its counters were not readable; the probe cannot judge "
                                     "reachability (install the firewall before probing)")

    # The positive control: captured, not dropped by the bench rule, and
    # delivered to the bench's own socket (the same capture observation, with
    # delivery to prove the method sees a reachable datagram as reached).
    control_captured = control.get("captured") is True
    control_dropped = control.get("counter_moved") is True
    control_delivered = control.get("delivered") is True
    verdict.control_ok = control_captured and not control_dropped and control_delivered
    verdict.control_detail = str(control.get("detail", "no control record"))
    if not verdict.control_ok:
        if control_captured and not control_dropped and not control_delivered:
            verdict.problems.append("the control datagram was captured and not dropped by the bench rule, yet it was "
                                    "not delivered; the capture-and-counter method is not shown to observe a reachable "
                                    "datagram, so the run shows nothing")
        else:
            verdict.problems.append("the positive control did not reach its host socket; an unreachable probe shows "
                                    "nothing")

    if isinstance(asm, dict):
        verdict.asm_mw_031_holds = asm.get("holds") if isinstance(asm.get("holds"), bool) else None
    else:
        verdict.asm_mw_031_holds = None

    # Classify each probe. Every probe that is neither isolated nor reached is
    # unknown and a coverage gap: a failed send, an incomplete or malformed
    # record, or a probe from the guest's loopback shows nothing, and is never
    # silently skipped (review R15/R27/R38). Only when the table is readable
    # can a captured probe be told from a dropped one; a direct receipt needs
    # no counter.
    loopback_seen = False
    # Coverage is derived from the attempts whose datagram actually reached the
    # host, not from any probed list the script wrote (reviews R41/B3): a pair
    # or a port counts as probed only when the capture (or a direct receipt)
    # shows its datagram arrived. A send that failed or never arrived is a gap.
    arrived_if: dict[str, set] = {}
    arrived_addr: dict[str, set] = {}
    arrived_ports: dict[tuple, set] = {}
    for attempt in attempts:
        if not isinstance(attempt, dict):
            verdict.unknown_probes.append({"port": None, "malformed": True})
            continue
        port = _as_int(attempt.get("port"))
        if port is None:
            verdict.unknown_probes.append(attempt)  # a malformed probe record shows nothing (review R38)
            continue
        state = _classify(attempt, captured, udp_receipts, tcp_receipts)
        if _captured(attempt, captured) or state == "received":
            guest = attempt.get("guest")
            arrived_if.setdefault(guest, set()).add(attempt.get("interface"))
            arrived_addr.setdefault(guest, set()).add(attempt.get("host"))
            arrived_ports.setdefault((guest, attempt.get("host")), set()).add(port)
        if state == "isolated":
            verdict.isolated_probes += 1
            continue
        if state in ("unknown", "invalid"):
            loopback_seen = loopback_seen or state == "invalid"
            verdict.unknown_probes.append(attempt)
            continue
        if state == "reached" and not verdict.table_readable:
            verdict.unknown_probes.append(attempt)
            continue
        # reached (capture and counter) or received (direct evidence)
        if port == FRAME_ASSEMBLER_PORT:
            verdict.reached_frame_assembler.append(attempt)
        elif port in layer_dds_ports:
            verdict.reached_layer.append(attempt)
        elif port in dds_set:
            verdict.reached_other.append(attempt)
    verdict.probed_interfaces = {guest: set(ifaces) for guest, ifaces in arrived_if.items()}
    verdict.probed_host_addresses = {guest: set(hosts) for guest, hosts in arrived_addr.items()}

    if loopback_seen:
        verdict.problems.append("a probe record names the guest's loopback as its source; such a datagram cannot "
                                "leave the guest, so it shows nothing")
    if verdict.unknown_probes:
        ports = sorted({p for a in verdict.unknown_probes if (p := _as_int(a.get("port"))) is not None})
        verdict.coverage_gaps.append(f"{len(verdict.unknown_probes)} probes did not arrive at the host, were not "
                                     f"sent, or are malformed (ports {ports[:8]}); they show nothing")

    # Coverage: every expected interface and host address of each guest must
    # have a captured attempt, and each probed (guest, host) pair must cover the
    # full DDS set plus 4721 (reviews R41/B3/R45). A reduced-range dry run leaves
    # ports unprobed, which is a gap, so it cannot pass.
    required_full = required_ports | {FRAME_ASSEMBLER_PORT}
    if isinstance(coverage, dict) and coverage:
        for guest, expect in (coverage.get("per_guest") or {}).items():
            missing_if = set(expect.get("expected_interfaces", [])) - arrived_if.get(guest, set())
            missing_addr = set(expect.get("expected_host_addresses", [])) - arrived_addr.get(guest, set())
            if missing_if:
                verdict.coverage_gaps.append(f"{guest}: interfaces with no captured probe: {sorted(missing_if)}")
            if missing_addr:
                verdict.coverage_gaps.append(f"{guest}: host addresses with no captured probe: {sorted(missing_addr)}")
    else:
        verdict.coverage_gaps.append("no coverage record; the probed interfaces and addresses are unknown")
    for (guest, host), ports in sorted(arrived_ports.items(), key=lambda item: (str(item[0][0]), str(item[0][1]))):
        missing_ports = required_full - ports
        if missing_ports:
            sample = sorted(p for p in missing_ports if isinstance(p, int))[:8]
            verdict.coverage_gaps.append(f"{guest} {host}: {len(missing_ports)} of {len(required_full)} required "
                                         f"ports not probed (e.g. {sample})")
    probed_ports_all = {port for ports in arrived_ports.values() for port in ports}
    for item in listeners:
        if not isinstance(item, dict):
            verdict.coverage_gaps.append("a host listener entry is malformed; it cannot be checked for coverage")
            continue
        port = _as_int(item.get("port"))
        if port is None:
            verdict.coverage_gaps.append("a host listener entry has no valid port (a malformed listener is a gap)")
            continue
        if (port in dds_set or port == FRAME_ASSEMBLER_PORT) and port not in probed_ports_all:
            verdict.coverage_gaps.append(f"listed socket on port {port} was not probed")

    if isinstance(inspection, dict):
        verdict.inspection_present = True
        verdict.inspection_no_host_endpoint = inspection.get("no_host_endpoint") is True
    return verdict
