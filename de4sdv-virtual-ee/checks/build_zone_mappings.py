#!/usr/bin/env python3
"""Generate one VSS mapping per zone from the full mapping tree.

A zone's provider is started with that zone's DBC only, so a mapping that also
names another zone's signals fails at startup:

    VSS datapoint Body.Windshield.Front.Wiping.Mode is mapped to CAN signal
    Wiper_Mode_Req which is not used in any message definition

That error is correct — the zone genuinely cannot see those frames. The fix is
one mapping per zone, generated from the single source tree rather than
maintained by hand, so the three artifacts cannot drift.

Run:  python de4sdv-virtual-ee/checks/build_zone_mappings.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FULL = ROOT / "vss" / "mapping" / "vss_dbc.json"

# zone id -> (VSS subtree the zone owns, output file)
ZONES = {
    "headlamp": ("Vehicle.Body.Lights", ROOT / "vss" / "mapping" / "headlamp.json"),
    "wiper": ("Vehicle.Body.Windshield", ROOT / "vss" / "mapping" / "wiper.json"),
}


def prune(node: dict, prefix: str) -> dict | None:
    """Keep only leaves under ``prefix``; drop branches left empty."""
    if node.get("type") != "branch":
        return node
    children = {}
    for name, child in (node.get("children") or {}).items():
        kept = prune(child, prefix)
        if kept is not None:
            children[name] = kept
    if not children:
        return None
    out = {k: v for k, v in node.items() if k != "children"}
    out["children"] = children
    return out


def count_leaves(node: dict) -> int:
    if node.get("type") != "branch":
        return 1
    return sum(count_leaves(c) for c in (node.get("children") or {}).values())


def main() -> int:
    full = json.loads(FULL.read_text())
    written = []
    for zone, (prefix, dest) in ZONES.items():
        node: dict = full["Vehicle"]
        for part in prefix.split(".")[1:]:
            node = node["children"][part]
        kept = prune(node, prefix)
        if kept is None:
            print(f"FAIL  {zone}: nothing under {prefix}")
            return 1
        tree = {"Vehicle": {"type": "branch", "children": {}}}
        # re-root the kept subtree so the file is a valid VSS document
        cursor = tree["Vehicle"]["children"]
        parts = prefix.split(".")[1:]
        for part in parts[:-1]:
            cursor[part] = {"type": "branch", "children": {}}
            cursor = cursor[part]["children"]
        cursor[parts[-1]] = kept
        dest.write_text(json.dumps(tree, indent=2) + "\n")
        written.append((zone, dest.name, count_leaves(kept)))
    for zone, name, leaves in written:
        print(f"OK    {zone}: {name} ({leaves} leaf/leaves)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
