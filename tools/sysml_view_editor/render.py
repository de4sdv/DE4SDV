"""SVG renderer for the DE4SDV semantic view graph.

Draws exactly the semantic graph supplied: role boxes, ports on roles, and
directed typed flow arrows with payload labels. No semantic content is
invented here — only what the graph contains is drawn.

Layout strategy:
- If a layout sidecar provides node positions, they are honored.
- Unplaced roles get deterministic default positions (left-to-right chain).
- Ports are placed on the right (out) or left (in) edge of their role box
  based on the flows that use them.
- Edges route from source port to target port; a straight line with an
  arrowhead, labeled with the payload type.
"""

from __future__ import annotations

import html
from pathlib import Path

from .graph import SemanticGraph
from .layout import reconcile

# Geometry
ROLE_W = 200
ROLE_H = 120
PORT_R = 8
GAP_X = 220  # wide enough that out-port labels (~90px) never reach the midpoint
GAP_Y = 80
PAD = 40

# Doc compartment (inside role boxes when the source carries a doc comment).
DOC_LINE_H = 13
DOC_TOP = 52       # first doc line baseline, below the host label
DOC_MAX_LINES = 4  # cap; longer docs are ellipsized (full text in tooltip/panel)
DOC_CAP_CHAR = 5.5  # ~avg glyph width at font-size 9


def _wrap_doc(doc: str, box_width: int) -> list[str]:
    """Greedy word-wrap a doc string to a role box's inner width.

    Deterministic so the Python renderer and the JS editor produce the same
    compartments. Truncated lines are ellipsized; the full text stays
    available in the tooltip and details panel.
    """
    cap = max(10, int((box_width - 20) / DOC_CAP_CHAR))
    lines: list[str] = []
    for word in doc.split():
        if lines and len(lines[-1]) + 1 + len(word) <= cap:
            lines[-1] += " " + word
        else:
            lines.append(word)
    if len(lines) > DOC_MAX_LINES:
        lines = lines[:DOC_MAX_LINES]
        lines[-1] = lines[-1][: cap - 1] + "…"
    return lines


def _esc(s: str) -> str:
    return html.escape(s, quote=True)


def _chain_order(graph: SemanticGraph) -> list[str]:
    """Topological order of roles following flow direction.

    The DE4SDV campaign is a linear chain
    cuttlefishGuest -> hostForwarder -> boundary -> ros2Ingress -> observer,
    and the flow graph defines exactly that order. Roles not participating in
    any flow are appended in sorted order.
    """
    from collections import defaultdict

    outgoing: dict[str, list[str]] = defaultdict(list)
    indegree: dict[str, int] = {rid: 0 for rid in graph.role_ids}
    for flow in graph.flows:
        if flow.source_role == flow.target_role:
            continue  # self-loop, ignore for ordering
        outgoing[flow.source_role].append(flow.target_role)
        indegree[flow.target_role] += 1

    # Kahn's algorithm on the role graph.
    ready = sorted(rid for rid, deg in indegree.items() if deg == 0)
    ordered: list[str] = []
    while ready:
        rid = ready.pop(0)
        ordered.append(rid)
        for nxt in sorted(outgoing[rid]):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                ready.append(nxt)

    # Any role not reached (cycle or isolated) goes to the end in sorted order.
    remaining = sorted(set(graph.role_ids) - set(ordered))
    return ordered + remaining


def _default_positions(graph: SemanticGraph, layout: dict) -> dict[str, dict]:
    """Return {id: {x, y, width, height}} for all roles and ports.

    Roles are placed left-to-right in the flow-derived chain order, one role
    per column, single row. Ports anchor on the right (out) or left (in) edge
    of their role box. Explicit layout-sidecar role positions override the
    defaults; ports derive from their role.
    """
    nodes: dict[str, dict] = {}

    ordered = _chain_order(graph)
    role_index = {rid: col for col, rid in enumerate(ordered)}

    # Compute role boxes.
    doc_lines = {rid: [] for rid in ordered}
    for role in graph.roles:
        if role.doc:
            doc_lines[role.id] = _wrap_doc(role.doc, ROLE_W)
    for rid in ordered:
        lines = doc_lines.get(rid, [])
        height = ROLE_H + (len(lines) * DOC_LINE_H + 6) if lines else ROLE_H
        x = PAD + role_index[rid] * (ROLE_W + GAP_X)
        y = PAD
        nodes[rid] = {"x": x, "y": y, "width": ROLE_W, "height": height}

    # Ports: place on right edge for out-flows, left edge for in-flows.
    port_index: dict[str, int] = {}
    for flow in graph.flows:
        for port_id, role_id, kind in (
            (flow.source_port, flow.source_role, "out"),
            (flow.target_port, flow.target_role, "in"),
        ):
            port_index.setdefault(port_id, 0)
            n = port_index[port_id]
            port_index[port_id] = n + 1
            base = nodes[role_id]
            if kind == "out":
                x = base["x"] + base["width"]
            else:
                x = base["x"]
            y = base["y"] + 20 + n * 28
            nodes[port_id] = {"x": x, "y": y}

    # Honor explicit layout overrides for roles only (ports derive from roles).
    for rid, entry in layout["nodes"].items():
        if rid in nodes and "x" in entry and "y" in entry:
            nodes[rid]["x"] = entry["x"]
            nodes[rid]["y"] = entry["y"]
            nodes[rid]["width"] = entry.get("width", ROLE_W)
            nodes[rid]["height"] = entry.get("height", ROLE_H)

    return nodes


def _port_anchor(node: dict, side: str) -> tuple[float, float]:
    if side == "out":
        return (node["x"] + node["width"], node["y"] + node.get("port_dy", 40))
    return (node["x"], node["y"] + node.get("port_dy", 40))


def _content_bounds(nodes: dict[str, dict], graph: SemanticGraph, title: bool) -> tuple[int, int, int, int]:
    """Compute the SVG viewBox from actual node extents (roles + ports + labels)."""
    # Margin for port labels: out-port labels extend right and above, in-port
    # labels extend left and below. The longest DE4SDV port name
    # (structuredLogcatOut) needs ~110px at font-size 10.
    LABEL_MARGIN_X = 140
    LABEL_MARGIN_TOP = 40
    LABEL_MARGIN_BOTTOM = 30
    x_min = min(n["x"] for n in nodes.values()) - LABEL_MARGIN_X
    y_min = min(n["y"] for n in nodes.values()) - (
        LABEL_MARGIN_TOP + (40 if title else 0)
    )
    x_max = max(
        n.get("x", 0) + n.get("width", 2 * PORT_R + 40) for n in nodes.values()
    ) + LABEL_MARGIN_X
    y_max = max(
        n.get("y", 0) + n.get("height", 2 * PORT_R + 40) for n in nodes.values()
    ) + LABEL_MARGIN_BOTTOM
    return x_min, y_min, x_max - x_min, y_max - y_min


def render_svg(
    graph: SemanticGraph,
    layout: dict,
    *,
    title: str | None = None,
) -> str:
    """Render the semantic graph to an SVG string."""
    warnings = reconcile(layout, graph)
    nodes = _default_positions(graph, layout)

    # Annotate ports with their vertical offset relative to the role box.
    role_nodes = {rid: nodes[rid] for rid in graph.role_ids}
    for port in graph.ports:
        role = role_nodes[port.role_id]
        port_node = nodes[port.id]
        nodes[port.id]["port_dy"] = port_node["y"] - role["y"]

    vx, vy, vw, vh = _content_bounds(nodes, graph, title is not None)

    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="{vx} {vy} {vw} {vh}" '
        f'font-family="sans-serif">'
    )

    if title:
        parts.append(f'<text x="{PAD}" y="{PAD - 12}" font-size="16" font-weight="bold">{_esc(title)}</text>')

    # Edges first (under nodes).
    for flow in graph.flows:
        src = nodes[flow.source_port]
        tgt = nodes[flow.target_port]
        x1 = src["x"] + (src.get("width", 0) if flow.source_host != flow.target_host else 0)
        y1 = src["y"]
        # Route from port anchor to port anchor with a midpoint.
        x2 = tgt["x"]
        y2 = tgt["y"]
        mx = (x1 + x2) / 2
        path = f"M {x1} {y1} L {mx} {y1} L {mx} {y2} L {x2} {y2}"
        flow_title = flow.doc or f"{flow.payload} from {flow.source} to {flow.target}"
        parts.append(
            f'<path d="{path}" fill="none" stroke="#d97706" stroke-width="2" '
            f'marker-end="url(#arrow)"><title>{_esc(flow_title)}</title></path>'
        )
        # Payload label centered on the arrow midpoint with a solid background
        # rect so it reads over any line crossing.
        label_x = mx
        label_y = min(y1, y2)
        text_w = 7 * len(flow.payload) + 8
        parts.append(
            f'<rect x="{label_x - text_w / 2}" y="{label_y - 11}" width="{text_w}" '
            f'height="16" rx="3" fill="#0f172a" stroke="#fbbf24" stroke-width="1" />'
        )
        parts.append(
            f'<text x="{label_x}" y="{label_y}" font-size="11" fill="#fbbf24" '
            f'text-anchor="middle">{_esc(flow.payload)}</text>'
        )

    # Role boxes + labels.
    for role in graph.roles:
        node = role_nodes[role.id]
        role_title = role.doc or f"{role.name} ({role.type_name})"
        parts.append(
            f'<rect x="{node["x"]}" y="{node["y"]}" width="{node["width"]}" '
            f'height="{node["height"]}" rx="8" fill="#1e293b" stroke="#475569" '
            f'stroke-width="1.5"><title>{_esc(role_title)}</title></rect>'
        )
        parts.append(
            f'<text x="{node["x"] + 12}" y="{node["y"] + 24}" font-size="13" '
            f'font-weight="bold" fill="#e2e8f0">{_esc(role.name)}</text>'
        )
        parts.append(
            f'<text x="{node["x"] + 12}" y="{node["y"] + 42}" font-size="10" fill="#94a3b8">'
            f'{_esc(role.host)}</text>'
        )
        # Doc compartment: separator + wrapped doc text inside the box.
        if role.doc:
            lines = _wrap_doc(role.doc, node["width"])
            sep_y = node["y"] + 47
            parts.append(
                f'<line x1="{node["x"] + 8}" y1="{sep_y}" x2="{node["x"] + node["width"] - 8}" '
                f'y2="{sep_y}" stroke="#475569" stroke-width="1" />'
            )
            for i, line in enumerate(lines):
                parts.append(
                    f'<text x="{node["x"] + 12}" y="{node["y"] + DOC_TOP + i * DOC_LINE_H}" '
                    f'font-size="9" fill="#cbd5e1">{_esc(line)}</text>'
                )

    # Ports.
    for port in graph.ports:
        node = nodes[port.id]
        side = "out" if any(f.source_port == port.id for f in graph.flows) else "in"
        cx = node["x"] + (node.get("width", 0) if side == "out" else 0)
        cy = node["y"]
        port_title = port.doc or f"{port.name}: {port.payload}"
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{PORT_R}" fill="#38bdf8" '
            f'stroke="#0ea5e9"><title>{_esc(port_title)}</title></circle>'
        )
        label_x = cx + (PORT_R + 6 if side == "out" else -(PORT_R + 6))
        anchor = "start" if side == "out" else "end"
        # Out-port labels go ABOVE the port, in-port labels go BELOW the port.
        # Opposite labels in the same gap therefore never occupy the same band.
        label_y = cy - (PORT_R + 6) if side == "out" else cy + PORT_R + 14
        parts.append(
            f'<text x="{label_x}" y="{label_y}" font-size="10" fill="#cbd5e1" '
            f'text-anchor="{anchor}">{_esc(port.name)}</text>'
        )

    parts.append(
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#d97706" /></marker></defs>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def render_to_file(
    graph: SemanticGraph,
    layout: dict,
    path: str | Path,
    *,
    title: str | None = None,
) -> list[str]:
    """Render the graph to an SVG file and return the reconcile warnings."""
    warnings = reconcile(layout, graph)
    svg = render_svg(graph, layout, title=title)
    Path(path).write_text(svg, encoding="utf-8")
    return warnings
