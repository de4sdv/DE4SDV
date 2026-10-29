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
            counter did not take it (it arrived and was not dropped);
- isolated  when the isolation counter took it (dropped);
- unknown   when the guest send failed, or the marker never arrived at the
            host (no counter movement and no capture): the datagram was not
            sent or did not reach the host, so nothing is shown.

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


def _classify(attempt: dict, captured: dict) -> str:
    """reached | isolated | unknown for one probe, from its observation."""
    if attempt.get("send_status") != SENT:
        return "unknown"
    counter_moved = attempt.get("counter_moved")
    if counter_moved is True:
        return "isolated"
    if not _captured(attempt, captured):
        return "unknown"  # it never arrived at the host (silent send failure, no route)
    if counter_moved is False:
        return "reached"  # arrived and the isolation rule did not take it
    return "unknown"      # counter unreadable for this probe


def evaluate_isolation(run_dir: str | Path) -> IsolationVerdict:
    run_dir = Path(run_dir)
    verdict = IsolationVerdict()
    firewall = _load(run_dir, "firewall.json", {})
    listeners = _load(run_dir, "host_listeners.json", [])
    attempts = _load(run_dir, "probe_attempts.json", [])
    captured = _load(run_dir, "captured_markers.json", {})
    control = _load(run_dir, "control.json", {})
    coverage = _load(run_dir, "coverage.json", {})
    asm = _load(run_dir, "asm_mw_031.json", None)
    inspection = _load(run_dir, "inspection.json", None)

    for name, value in (("firewall", firewall), ("host_listeners", listeners), ("probe_attempts", attempts),
                        ("captured_markers", captured), ("control", control)):
        if value == "ERROR":
            verdict.errors.append(f"{name}.json is not valid JSON")
    if verdict.errors:
        return verdict
    firewall = firewall or {}
    listeners = listeners or []
    attempts = attempts or []
    captured = captured or {}
    control = control or {}

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

    # Classify each probe. Only when the table is readable can a reached probe
    # be told from a dropped one.
    for attempt in attempts:
        if not isinstance(attempt, dict):
            continue
        port = _as_int(attempt.get("port"))
        if port is None:
            continue  # a malformed probe record shows nothing (hostile input, review R38)
        state = _classify(attempt, captured)
        if state == "isolated":
            verdict.isolated_probes += 1
            continue
        if state == "unknown":
            if attempt.get("send_status") == SENT:
                verdict.unknown_probes.append(attempt)
            continue
        # reached
        if not verdict.table_readable:
            verdict.unknown_probes.append(attempt)
            continue
        if port == FRAME_ASSEMBLER_PORT:
            verdict.reached_frame_assembler.append(attempt)
        elif port in layer_dds_ports:
            verdict.reached_layer.append(attempt)
        elif port in dds_set:
            verdict.reached_other.append(attempt)

    if verdict.unknown_probes:
        ports = sorted({p for a in verdict.unknown_probes if (p := _as_int(a.get("port"))) is not None})
        verdict.coverage_gaps.append(f"{len(verdict.unknown_probes)} probes did not arrive at the host or were not "
                                     f"sent (ports {ports[:8]}); they show nothing")

    # Coverage: every listed socket, host address and interface must be probed.
    if isinstance(coverage, dict) and coverage:
        for guest, expect in (coverage.get("per_guest") or {}).items():
            missing_if = set(expect.get("expected_interfaces", [])) - set(expect.get("probed_interfaces", []))
            missing_addr = set(expect.get("expected_host_addresses", [])) - set(expect.get("probed_host_addresses", []))
            if missing_if:
                verdict.coverage_gaps.append(f"{guest}: interfaces not probed: {sorted(missing_if)}")
            if missing_addr:
                verdict.coverage_gaps.append(f"{guest}: host addresses not probed: {sorted(missing_addr)}")
        probed_ports = {_as_int(a.get("port")) for a in attempts if isinstance(a, dict)}
        for item in listeners:
            if not isinstance(item, dict):
                continue
            port = _as_int(item.get("port"))
            if port is not None and (port in dds_set or port == FRAME_ASSEMBLER_PORT) and port not in probed_ports:
                verdict.coverage_gaps.append(f"listed socket on port {port} was not probed")
    else:
        verdict.coverage_gaps.append("no coverage record; the probed interfaces and addresses are unknown")

    if isinstance(inspection, dict):
        verdict.inspection_present = True
        verdict.inspection_no_host_endpoint = inspection.get("no_host_endpoint") is True
    return verdict
