"""Read side of the REQ-MW-016 reachability check: confirm the host ports are isolated.

The check is a property: no DDS port of a host ROS 2 process is reachable from
any guest domain. The bench proves isolation, so a pass means the probes did
NOT reach a host socket. The probing runs in scripts/host_isolation_probe.sh
with standard tools; this module only reads what those tools recorded and
decides the second finding of REQ-MW-016. It never opens a socket.

Reachability is judged by host-socket receipt, the authoritative signal: a
probe reached the host only when its marker arrived at the real host socket
(host_socket_receipts.json), or the host accepted its TCP connect. A capture
on the guest-facing interface is taken before netfilter, so it is not the
test. The isolation-rule counters (nft_counters.json) corroborate. The
positive control uses the same host-socket-receipt observation (#448).

Run artifacts this module reads (JSON):
- host_listeners.json: the host sockets, each {address, port, protocol,
  element, element_in_layer}.
- probe_attempts.json: one record per (guest, interface, src_addr, host,
  port, protocol) with a unique marker and the guest's own result.
- host_socket_receipts.json: {udp_markers: [...], tcp_connects: [{port,
  guest, src_addr}]}, what actually reached a host socket.
- nft_counters.json: per-rule before/after counts (corroboration).
- control.json: {reached: bool, detail}, the positive control by the same
  host-socket-receipt method.
- coverage.json: {expected_interfaces, expected_host_addresses,
  probed_interfaces, probed_host_addresses} of each guest.
- asm_mw_031.json: {holds: bool, detail} for the ROS 2 processes outside the layer.
- inspection.json (first finding): {no_host_endpoint: bool, inspector, artifacts}.
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
    layer_reachable: list[dict] = field(default_factory=list)       # reached DDS port of a layer element
    other_reachable: list[dict] = field(default_factory=list)       # reached DDS port of a non-layer process
    frame_assembler_reachable: list[dict] = field(default_factory=list)  # reached 4721 (ASM-MW-029)
    control_ok: bool = False
    control_detail: str = ""
    asm_mw_031_holds: bool | None = None
    attempts: int = 0
    coverage_gaps: list[str] = field(default_factory=list)
    inspection_present: bool = False
    inspection_no_host_endpoint: bool | None = None
    problems: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _reached(attempt: dict, receipts: dict) -> bool:
    marker = attempt.get("marker")
    if attempt.get("protocol") == "udp":
        return marker is not None and marker in set(receipts.get("udp_markers", []))
    for entry in receipts.get("tcp_connects", []):
        if entry.get("port") == attempt.get("port") and entry.get("guest") == attempt.get("guest"):
            return True
    return False


def evaluate_isolation(run_dir: str | Path) -> IsolationVerdict:
    run_dir = Path(run_dir)
    verdict = IsolationVerdict()
    listeners = _load(run_dir, "host_listeners.json", [])
    attempts = _load(run_dir, "probe_attempts.json", [])
    receipts = _load(run_dir, "host_socket_receipts.json", {})
    control = _load(run_dir, "control.json", {})
    coverage = _load(run_dir, "coverage.json", {})
    asm = _load(run_dir, "asm_mw_031.json", None)
    inspection = _load(run_dir, "inspection.json", None)

    for name, value in (("host_listeners", listeners), ("probe_attempts", attempts),
                        ("host_socket_receipts", receipts), ("control", control)):
        if value == "ERROR":
            verdict.errors.append(f"{name}.json is not valid JSON")
    if verdict.errors:
        return verdict
    listeners = listeners or []
    attempts = attempts or []
    receipts = receipts or {}
    control = control or {}

    dds_set = set(dds_udp_ports())
    layer_dds_ports = {int(item["port"]) for item in listeners
                       if item.get("element_in_layer") and int(item.get("port", 0)) in dds_set}
    verdict.attempts = len(attempts)

    # Control: by the same host-socket-receipt observation.
    verdict.control_ok = control.get("reached") is True
    verdict.control_detail = str(control.get("detail", "no control record"))
    if not verdict.control_ok:
        verdict.problems.append("the positive control did not reach its host socket; an unreachable probe shows nothing")

    # ASM-MW-031 for the processes outside the layer.
    if isinstance(asm, dict):
        verdict.asm_mw_031_holds = asm.get("holds") is True
    else:
        verdict.asm_mw_031_holds = None

    for attempt in attempts:
        port = int(attempt.get("port", 0))
        if not _reached(attempt, receipts):
            continue
        if port == FRAME_ASSEMBLER_PORT:
            verdict.frame_assembler_reachable.append(attempt)
        elif port in layer_dds_ports:
            verdict.layer_reachable.append(attempt)
        elif port in dds_set:
            verdict.other_reachable.append(attempt)

    # Coverage: every listed socket, host address and interface must be probed.
    if isinstance(coverage, dict) and coverage:
        for guest, expect in (coverage.get("per_guest") or {}).items():
            missing_if = set(expect.get("expected_interfaces", [])) - set(expect.get("probed_interfaces", []))
            missing_addr = set(expect.get("expected_host_addresses", [])) - set(expect.get("probed_host_addresses", []))
            if missing_if:
                verdict.coverage_gaps.append(f"{guest}: interfaces not probed: {sorted(missing_if)}")
            if missing_addr:
                verdict.coverage_gaps.append(f"{guest}: host addresses not probed: {sorted(missing_addr)}")
        probed_ports = {int(a.get("port", 0)) for a in attempts}
        for item in listeners:
            port = int(item.get("port", 0))
            if (port in dds_set or port == FRAME_ASSEMBLER_PORT) and port not in probed_ports:
                verdict.coverage_gaps.append(f"listed socket on port {port} was not probed")
    else:
        verdict.coverage_gaps.append("no coverage record; the probed interfaces and addresses are unknown")

    if isinstance(inspection, dict):
        verdict.inspection_present = True
        verdict.inspection_no_host_endpoint = inspection.get("no_host_endpoint") is True
    return verdict
