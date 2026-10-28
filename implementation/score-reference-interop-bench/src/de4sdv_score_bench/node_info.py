"""Reader of ``ros2 node info`` for the ROS 2 endpoints of the adapter node.

The model (adapterAbortConditions) names the endpoints of the adapter node in
a member run: its VelocityReport publication, and the /parameter_events
subscription of rclcpp's time source. The node has no parameter services, no
parameter event publisher and no /rosout. The check reads the sections of
``ros2 node info`` and passes only for exactly these endpoints.
"""

from __future__ import annotations

import re
from typing import Any

SECTIONS = ("Subscribers", "Publishers", "Service Servers", "Service Clients", "Action Servers", "Action Clients")
_ENTRY = re.compile(r"^\s+(?P<name>/\S+): (?P<type>\S+)\s*$")

EXPECTED = {
    "Subscribers": {"/parameter_events": "rcl_interfaces/msg/ParameterEvent"},
    "Publishers": {"/de4sdv/middleware/velocity_status": "autoware_vehicle_msgs/msg/VelocityReport"},
    "Service Servers": {},
    "Service Clients": {},
    "Action Servers": {},
    "Action Clients": {},
}


def parse_node_info(text: str) -> dict[str, dict[str, str]] | None:
    """The endpoints per section, or None when the output holds no section."""
    sections: dict[str, dict[str, str]] = {}
    current = None
    for line in text.splitlines():
        header = line.strip().rstrip(":")
        if line.strip().endswith(":") and header in SECTIONS:
            current = header
            sections[current] = {}
            continue
        match = _ENTRY.match(line)
        if match is not None and current is not None:
            sections[current][match.group("name")] = match.group("type")
    return sections if sections else None


def check_member_endpoints(text: str) -> dict[str, Any]:
    """Passes only for the endpoints that the model names for a member run."""
    sections = parse_node_info(text)
    if sections is None:
        return {"passed": False, "reasons": ["ros2 node info gave no endpoint section"], "endpoints": None}
    reasons = []
    for section in SECTIONS:
        if section not in sections:
            reasons.append(f"ros2 node info has no section {section}")
            continue
        unexpected = sorted(set(sections[section]) - set(EXPECTED[section]))
        missing = sorted(set(EXPECTED[section]) - set(sections[section]))
        if unexpected:
            reasons.append(f"{section}: unexpected {', '.join(unexpected)}")
        if missing:
            reasons.append(f"{section}: missing {', '.join(missing)}")
    for section, entries in sections.items():
        if "/rosout" in entries:
            reasons.append(f"{section}: /rosout")
    return {"passed": not reasons, "reasons": reasons, "endpoints": sections}
