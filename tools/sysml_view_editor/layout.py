"""Layout sidecar: presentation-only state for the DE4SDV view editor.

The sidecar stores positions, sizes, and edge routing ONLY. It never stores
roles, ports, flows, payload types, or any semantic fact. Semantics come from
the authoritative SysML model (see graph.py). The sidecar is keyed by stable
qualified IDs derived from the model, so renames/orphans can be detected.

Schema versioning is explicit; unknown versions must be rejected, never
silently migrated.
"""

from __future__ import annotations

import json
from pathlib import Path

SCHEMA_VERSION = 1


class LayoutError(ValueError):
    """Raised when a layout sidecar is invalid, stale, or unsupported."""


def empty_layout(view_name: str, semantic_hash: str) -> dict:
    """A layout with no placements — every element is unplaced."""
    return {
        "schema_version": SCHEMA_VERSION,
        "view": view_name,
        "semantic_hash": semantic_hash,
        "nodes": {},
        "edges": {},
    }


def load_layout(path: str | Path) -> dict:
    """Load and validate a layout sidecar."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA_VERSION:
        raise LayoutError(
            f"Unsupported layout schema version {data.get('schema_version')!r}; "
            f"expected {SCHEMA_VERSION}"
        )
    if not isinstance(data.get("nodes"), dict):
        raise LayoutError("Layout sidecar must contain a 'nodes' object")
    if not isinstance(data.get("edges"), dict):
        raise LayoutError("Layout sidecar must contain an 'edges' object")
    return data


def save_layout(layout: dict, path: str | Path) -> None:
    """Write a layout sidecar atomically."""
    layout = dict(layout)
    layout["schema_version"] = SCHEMA_VERSION
    tmp = Path(path).with_suffix(Path(path).suffix + ".tmp")
    tmp.write_text(json.dumps(layout, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(Path(path))


def reconcile(layout: dict, graph, *, allow_orphans: bool = False) -> list[str]:
    """Return a list of warnings reconciling a layout against a semantic graph.

    - Unplaced semantic elements (roles/ports/flows with no layout entry) are
      reported so the renderer can place them deterministically.
    - Layout entries whose stable ID no longer exists in the graph are orphan
      warnings. They are never silently dropped.
    """
    warnings: list[str] = []
    node_ids = {r.id for r in graph.roles} | {p.id for p in graph.ports}
    edge_ids = {f.stable_id for f in graph.flows}

    for nid in sorted(node_ids):
        if nid not in layout["nodes"]:
            warnings.append(f"unplaced: {nid}")

    for eid in sorted(edge_ids):
        if eid not in layout["edges"]:
            warnings.append(f"unplaced: {eid}")

    for lid in sorted(layout["nodes"]):
        if lid not in node_ids:
            warnings.append(f"orphan: {lid}")

    for lid in sorted(layout["edges"]):
        if lid not in edge_ids:
            warnings.append(f"orphan: {lid}")

    return warnings
