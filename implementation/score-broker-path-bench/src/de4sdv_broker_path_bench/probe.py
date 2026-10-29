"""Read side of the REQ-MW-016 reachability check: confirm the host ports are isolated.

The check is a property: no DDS port of a host ROS 2 process, and no port 4721
of the frame assembler, is reachable from any guest domain. The bench proves
isolation, so a pass means the probes did NOT get through. The probing itself
runs in scripts/host_isolation_probe.sh with standard tools (ss, nc, tcpdump,
nft); this module only reads what those tools recorded and decides the outcome.

Run artifacts this module reads (JSON, one object or a list per file):

- host_listeners.json: the sockets the host ROS 2 processes and the frame
  assembler have bound (from ``ss -ulnp`` / ``ss -tlnp`` on the host), each
  with address, port, protocol and the owning element.
- probe_attempts.json: one record per (guest, interface, host address, port)
  the guest probed, with a unique marker string and the guest's own result
  (``sent`` for a datagram, ``connected`` / ``refused`` / ``timeout`` /
  ``no_route`` for a TCP connect).
- host_capture_markers.json: the markers that arrived at the host, read from
  the tcpdump capture on each guest-facing interface, and the TCP connects the
  host accepted. A marker here means a datagram reached the host.
- nft_counters.json: the before/after packet counts of the isolation rule.
- control.json: the positive control, the same method against a host socket
  left reachable (or with the isolation off for a control window); it must
  show the method works.

The evaluators call ``evaluate_isolation``; it never opens a socket.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: The DDS ports of ROS_DOMAIN_ID 91 with MaxAutoParticipantIndex 120
#: (GAP-MW-046). SPDP/user multicast 30150-30151; unicast 30160 + 2i and
#: 30161 + 2i for i in 0..120, so 30160-30401. The nft rule and this set are
#: derived from the same two parameters.
DDS_DOMAIN = 91
DDS_MAX_PARTICIPANT_INDEX = 120


def dds_udp_ports(domain: int = DDS_DOMAIN, max_index: int = DDS_MAX_PARTICIPANT_INDEX) -> list[int]:
    port_base = 7400
    domain_gain, participant_gain = 250, 2
    d0, d1, d2, d3 = 0, 10, 1, 11
    spdp_multicast = port_base + domain_gain * domain + d0
    user_multicast = port_base + domain_gain * domain + d2
    first_unicast = port_base + domain_gain * domain + d1
    last_unicast = port_base + domain_gain * domain + d3 + participant_gain * max_index
    ports = {spdp_multicast, user_multicast}
    ports.update(range(first_unicast, last_unicast + 1))
    return sorted(ports)


#: Port 4721, the frame assembler of INC-AEBS-010 (ASM-MW-029). The host must
#: keep the guest network off it too, so the probe covers it.
FRAME_ASSEMBLER_PORT = 4721


def _load(run_dir: Path, name: str, default: Any) -> Any:
    path = run_dir / name
    if not path.exists():
        return default
    return json.loads(path.read_text())


@dataclass
class IsolationVerdict:
    reachable: list[dict]  # probes that reached a host port that must be isolated
    control_ok: bool
    control_detail: str
    attempts: int
    layer_dds_ports: list[int]
    problems: list[str]


def _reached(attempt: dict, host_markers: dict) -> bool:
    """Did this probe reach the host, by the host's own record (not the guest's)?"""
    marker = attempt.get("marker")
    if attempt.get("protocol") == "udp":
        return marker in set(host_markers.get("udp_markers", []))
    accepted = host_markers.get("tcp_accepted", [])
    return any(entry.get("port") == attempt.get("port") and entry.get("from") == attempt.get("guest")
               for entry in accepted)


def evaluate_isolation(run_dir: str | Path) -> IsolationVerdict:
    """Decide whether every isolated host port stayed unreachable from the guests."""
    run_dir = Path(run_dir)
    problems: list[str] = []
    listeners = _load(run_dir, "host_listeners.json", [])
    attempts = _load(run_dir, "probe_attempts.json", [])
    host_markers = _load(run_dir, "host_capture_markers.json", {})
    control = _load(run_dir, "control.json", {})

    layer_dds = sorted({int(item["port"]) for item in listeners
                        if item.get("element_in_layer") and int(item.get("port", 0)) in set(dds_udp_ports())})

    # The positive control must show the method can observe a reachable port.
    control_ok = bool(control.get("reached"))
    control_detail = str(control.get("detail", "no control record"))
    if not control_ok:
        problems.append("positive control did not reach its reachable host port; an unreachable result shows nothing")

    must_isolate = set(dds_udp_ports()) | {FRAME_ASSEMBLER_PORT}
    reachable: list[dict] = []
    for attempt in attempts:
        port = int(attempt.get("port", 0))
        if port not in must_isolate:
            continue
        if _reached(attempt, host_markers):
            reachable.append(attempt)

    if not attempts:
        problems.append("no probe attempts recorded")
    return IsolationVerdict(reachable, control_ok, control_detail, len(attempts), layer_dds, problems)
