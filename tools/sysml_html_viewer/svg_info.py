"""Diagram hover enrichment: extract SVG text labels and resolve them to
model elements.

SysIDE renders each diagram as a flat SVG: element names, stereotype
labels (``«part def»``), and usage labels (``signalTranslator :
SignalTranslator``) are plain ``<text>`` elements. This module turns those
labels back into model knowledge (kind, doc, source location, viewer
anchor) so the generated viewer can show a tooltip on hover.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass

from .model_parse import ElementRef

_TEXT_RE = re.compile(r"<text\b[^>]*>(.*?)</text>", flags=re.S)
_TAG_RE = re.compile(r"<[^>]+>")

# Label shapes SysIDE emits: stereotype prefix «view» name, `expose name`,
# `name : Type`, plain name. Anything else is layout text (headers, notes).
_STEREOTYPE_RE = re.compile(r"^«[^»]*»\s*")
_EXPOSE_RE = re.compile(r"^expose\s+")
_EXHIBIT_RE = re.compile(r"^exhibit\s+")
# `states lifecycleStates` renders the exhibited usage; resolve by its name
_PLURAL_USAGE_RE = re.compile(
    r"^(?:states|parts|ports|actions|items|flows|interfaces|attributes)\s+"
)

# SysIDE compartment headings (exact) and doc rows (prefix) that carry no
# declaration of their own; they resolve to the element whose compartment
# they render.
_HEADING_RE = re.compile(
    r"^(?:subject|actors|include use cases|attributes)\s*$|^doc\b"
)


def _unescape(s: str) -> str:
    """SysIDE SVG text may carry HTML entities (&gt; for the :> specializer)."""
    s = s.replace("&lt;", "<")
    s = s.replace("&gt;", ">")
    s = s.replace("&quot;", '"')
    s = s.replace("&#39;", "'")
    s = s.replace("&apos;", "'")
    s = s.replace("&amp;", "&")  # last, so &amp;gt; resolves to >
    return s


def extract_text_labels(svg_text: str) -> list[str]:
    """All text-element contents, normalized (whitespace collapsed, entities
    unescaped)."""
    labels = []
    for m in _TEXT_RE.finditer(svg_text):
        plain = _TAG_RE.sub("", m.group(1))
        plain = _unescape(plain)
        plain = re.sub(r"\s+", " ", plain).strip()
        if plain:
            labels.append(plain)
    return labels


# SysIDE's committed relationship connectors use dark, unfilled geometry;
# #336680 polylines are compartment/table separators. Keep that discriminator
# for native polyline connectors so nearby port labels cannot turn separators
# into relationship hit targets. Line/path support remains permissive because
# those primitives are not present in the current committed SysIDE artifacts;
# semantic label pairing still gates whether they become hover targets.
_POLYLINE_RE = re.compile(
    r'<polyline\b(?=[^>]*points="([^"]+)")'
    r'(?=[^>]*\bfill="none")(?=[^>]*\bstroke="(?:#1A1A1A|black)")[^>]*>'
)
_LINE_RE = re.compile(
    r'<line\b(?=[^>]*\bx1="([\d.-]+)")(?=[^>]*\by1="([\d.-]+)")'
    r'(?=[^>]*\bx2="([\d.-]+)")(?=[^>]*\by2="([\d.-]+)")[^>]*>'
)
_PATH_RE = re.compile(
    r'<path\b(?=[^>]*\bd="([^"]+)")(?=[^>]*\bfill="none")([^>]*)>'
)

_TEXT_POS_RE = re.compile(
    r'<text\b[^>]*x="([\d.]+)"[^>]*y="([\d.]+)"[^>]*>(.*?)</text>', flags=re.S
)


def _connector_polylines(svg_text: str) -> list[tuple[str, list[tuple[float, float]]]]:
    """Return stable keys and points for all line-like SVG geometry.

    The historical function name is retained for callers, but the returned
    inventory includes polyline, line, and simple SysIDE path geometry. Paths
    used for arrows and element borders are filtered by their SVG fill/stroke
    attributes and by relationship-label resolution.
    """
    out = []
    for m in _POLYLINE_RE.finditer(svg_text):
        pts = m.group(1)
        coords = [float(v) for v in re.split(r"[,\s]+", pts.strip()) if v]
        points = list(zip(coords[0::2], coords[1::2]))
        if len(points) >= 2:
            out.append((pts, points))
    for m in _LINE_RE.finditer(svg_text):
        points = [(float(m.group(1)), float(m.group(2))), (float(m.group(3)), float(m.group(4)))]
        key = f"line:{m.group(1)},{m.group(2)},{m.group(3)},{m.group(4)}"
        out.append((key, points))
    for m in _PATH_RE.finditer(svg_text):
        d = m.group(1)
        if re.search(r"\bZ\b", d, re.I):
            continue  # closed rounded/outline boxes, not open connectors
        points = _orthogonal_path_points(d)
        if len(points) >= 2:
            out.append((f"path:{d}", points))
    return out


def _orthogonal_path_points(d: str) -> list[tuple[float, float]]:
    """Parse the M/H/V subset used by SysIDE's routed relationship paths."""
    points: list[tuple[float, float]] = []
    cur = (0.0, 0.0)
    for command, args in re.findall(r"([MHV])\s*([\d.,\s-]*)", d, re.I):
        nums = [float(v) for v in re.findall(r"-?[\d.]+", args)]
        cmd = command.upper()
        if cmd == "M" and len(nums) >= 2:
            cur = (nums[0], nums[1])
            points.append(cur)
        elif cmd == "H" and nums:
            cur = (nums[0], cur[1])
            points.append(cur)
        elif cmd == "V" and nums:
            cur = (cur[0], nums[0])
            points.append(cur)
    return points


def _dist_point_segment(
    px: float, py: float, x1: float, y1: float, x2: float, y2: float
) -> float:
    dx, dy = x2 - x1, y2 - y1
    if dx == dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


_CONNECTION_KINDS = frozenset({"connection", "flow", "bind", "dependency"})

# kinds that own an element box (the white rounded rects SysIDE draws for
# part defs, parts, item defs, ...)
_BOX_OWNER_KINDS = frozenset({
    "part", "part def", "item", "item def", "port def", "attribute",
    "attribute def", "requirement", "requirement def", "use case",
    "use case def", "verification case", "verification case def",
    "state", "state def", "viewpoint def", "viewpoint",
})

# SysIDE element boxes: white-filled paths made only of M/H/V(/A) commands —
# rounded-rect boxes in interconnection views (`A 6,6` corner arcs) and
# plain rectangles in tree views. Curved paths (C/S/Q/T) are never boxes,
# and the tiny square port glyphs are filtered out by the label-inside rule.
_BOX_PATH_RE = re.compile(
    r'<path\b(?=[^>]*d="([^"]+)")(?=[^>]*fill="#FFFFFF")'
    r'(?![^>]*\b[CSQT]\s)[^>]*>'
)


def _path_bbox(d: str) -> tuple[float, float, float, float] | None:
    """Bounding box of a SysIDE element-box path (`M x,y H x2 V y2 A ... Z`)."""
    pts: list[tuple[float, float]] = []
    cur = (0.0, 0.0)
    for cmd, args in re.findall(r"([MHVZ])\s*([\d.,\s-]*)", d, re.I):
        nums = [float(v) for v in re.findall(r"-?[\d.]+", args)]
        c = cmd.upper()
        if c == "M" and len(nums) >= 2:
            cur = (nums[0], nums[1])
            pts.append(cur)
        elif c == "H" and nums:
            cur = (nums[0], cur[1])
            pts.append(cur)
        elif c == "V" and nums:
            cur = (cur[0], nums[0])
            pts.append(cur)
        elif c == "A":
            # rx ry rotation large-arc sweep x y — endpoint is the last pair
            for i in range(0, len(nums) - 5, 7):
                pts.append((nums[i + 5], nums[i + 6]))
    if not pts:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _text_positions(svg_text: str) -> list[tuple[float, float, str]]:
    """(x, y, normalized text) for every text element."""
    return [
        (
            float(m.group(1)),
            float(m.group(2)),
            re.sub(r"\s+", " ", _unescape(_TAG_RE.sub("", m.group(3)))).strip(),
        )
        for m in _TEXT_POS_RE.finditer(svg_text)
        if re.sub(r"\s+", " ", _unescape(_TAG_RE.sub("", m.group(3)))).strip()
    ]


def _connector_label(
    plain: str,
    li: LabelInfo,
    index: dict[str, list[ElementRef]],
    view_file: str,
    view_folder: str,
) -> LabelInfo:
    """Connector pairing may find a label that resolved to a port while the
    SAME name also declares the connection (bind/connection/flow usage).
    Prefer the connection-kind declaration so the tooltip names the
    connection, not its end point."""
    if li.kind in _CONNECTION_KINDS:
        return li
    for key in _normalize(li.label):
        refs = index.get(key)
        if not refs:
            continue
        conn_refs = [r for r in refs if r.kind in _CONNECTION_KINDS]
        if conn_refs:
            ref = _prefer(conn_refs, view_file, view_folder)
            if ref is not None:
                return LabelInfo(
                label=li.label,
                name=ref.name,
                kind=ref.kind,
                doc=ref.doc,
                rel_path=ref.rel_path,
                line=ref.line,
                anchor=ref.anchor,
            )
    return li


def resolve_connectors(
    svg_text: str,
    resolved: dict[str, LabelInfo],
    member_index: dict[str, list[ElementRef]],
    view_file: str,
    view_folder: str,
    radius: float = 260.0,
    resolved_pos: dict[str, LabelInfo] | None = None,
) -> dict[str, LabelInfo]:
    """Pair visible relationship geometry with its model declaration.

    ``resolved_pos`` is the identity-preserving map built from each SVG
    text element's coordinates. It is preferred over ``resolved`` so two
    same-text labels in one diagram cannot collapse to one tooltip. The
    geometry inventory includes polyline/line/path primitives; only a nearby
    relationship declaration is accepted, so frame/separator geometry does
    not become a fabricated relationship.
    """
    positions = _text_positions(svg_text)
    shapes = _connector_polylines(svg_text)
    # A declaration can be printed more than once (for example in an expose
    # compartment and beside its relationship). Group those occurrences by
    # declaration first; otherwise duplicate labels compete with distinct
    # relationships and one real connector is silently lost.
    relationships: dict[tuple[str, str, int], list[tuple[float, float, LabelInfo]]] = {}
    for x, y, plain in positions:
        li = (
            resolved_pos.get(_position_key(x, y), resolved.get(plain))
            if resolved_pos is not None
            else resolved.get(plain)
        )
        if li is None:
            continue
        li = _connector_label(plain, li, member_index, view_file, view_folder)
        if li.kind in _CONNECTION_KINDS and not plain.startswith("expose "):
            identity = (li.rel_path, li.kind, li.line)
            relationships.setdefault(identity, []).append((x, y, li))

    # Resolve declarations and shapes as a one-to-one assignment. For each
    # declaration, retain all printed label positions as candidates and let the
    # globally closest unused declaration/shape pair win. This handles both
    # duplicate labels and nearby routed lines without dropping a declaration.
    pairs: list[tuple[float, tuple[str, str, int], str, LabelInfo]] = []
    for identity, occurrences in relationships.items():
        for x, y, li in occurrences:
            for shape_key, segs in shapes:
                d = min(
                    _dist_point_segment(x, y, *a, *b)
                    for a, b in zip(segs[:-1], segs[1:])
                )
                if d <= radius:
                    pairs.append((d, identity, shape_key, li))
    assignments: list[tuple[float, str, LabelInfo]] = []
    used_relationships: set[tuple[str, str, int]] = set()
    used_shapes: set[str] = set()
    for distance, identity, shape_key, li in sorted(pairs, key=lambda p: p[0]):
        if identity in used_relationships or shape_key in used_shapes:
            continue
        used_relationships.add(identity)
        used_shapes.add(shape_key)
        assignments.append((distance, shape_key, li))

    return {shape_key: li for _, shape_key, li in assignments}


def resolve_boxes(
    svg_text: str,
    resolved: dict[str, LabelInfo],
    resolved_pos: dict[str, LabelInfo] | None = None,
) -> dict[str, LabelInfo]:
    """Pair element-box paths (white rounded rects) with the element label
    inside them — the box owner — and port glyphs (small white squares on
    box edges) with their port label — so hovering the box body or the
    port symbol shows the element's tooltip. Keyed by the raw d attribute;
    labels with connection-ish kinds (flows, connections) never own a box."""
    out: dict[str, LabelInfo] = {}
    boxes = []
    for m in _BOX_PATH_RE.finditer(svg_text):
        bbox = _path_bbox(m.group(1))
        if bbox is not None:
            boxes.append((m.group(1), bbox))
    if not boxes:
        return out
    positions = _text_positions(svg_text)

    def _label_at(x: float, y: float, plain: str) -> LabelInfo | None:
        if resolved_pos is not None:
            li = resolved_pos.get(_position_key(x, y))
            if li is not None:
                return li
        return resolved.get(plain)

    for d, (x1, y1, x2, y2) in boxes:
        inside = [
            (x, y, li)
            for (x, y, plain) in positions
            if (li := _label_at(x, y, plain)) is not None
            and li.kind in _BOX_OWNER_KINDS
            and x1 < x < x2
            and y1 < y < y2
        ]
        if inside:
            # the box header label (topmost inside) names the box owner
            inside.sort(key=lambda t: t[1])
            out[d] = inside[0][2]
            continue
        # small white rects are port glyphs: pair with the nearest port
        # label (falling back to item labels) so the port symbol is
        # hoverable like the port text
        if max(x2 - x1, y2 - y1) <= 60:
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            best_port: tuple[float, LabelInfo] | None = None
            best_item: tuple[float, LabelInfo] | None = None
            for x, y, plain in positions:
                li = _label_at(x, y, plain)
                if li is None or li.kind not in ("port", "item"):
                    continue
                # measure to the label's approximated box (10px font,
                # ~5.5px per char) — SysIDE left-anchors port labels, so
                # the start point alone under-measures wide labels
                lx2 = x + len(plain) * 5.5
                dist = _dist_point_rect(cx, cy, x, y, lx2, y + 10)
                if dist > 60:
                    continue
                if li.kind == "port":
                    if best_port is None or dist < best_port[0]:
                        best_port = (dist, li)
                elif best_item is None or dist < best_item[0]:
                    best_item = (dist, li)
            if best_port is not None:
                out[d] = best_port[1]
            elif best_item is not None:
                out[d] = best_item[1]
    return out


def _dist_point_rect(
    px: float, py: float, x1: float, y1: float, x2: float, y2: float
) -> float:
    """Distance from a point to a rectangle (0 when inside)."""
    dx = max(x1 - px, 0.0, px - x2)
    dy = max(y1 - py, 0.0, py - y2)
    return math.hypot(dx, dy)


def _normalize(label: str) -> list[str]:
    """Candidate lookup keys for a raw SVG label, most specific first."""
    candidates = []
    s = _STEREOTYPE_RE.sub("", label).strip()
    s = _EXPOSE_RE.sub("", s).strip()
    s = _EXHIBIT_RE.sub("", s).strip()
    s = s.lstrip("^")  # `^name` = redefines marker
    if not s:
        return []
    candidates.append(s)
    # plural usage labels (`states lifecycleStates`) resolve by their name
    s2 = _PLURAL_USAGE_RE.sub("", s)
    if s2 and s2 != s:
        candidates.append(s2)
    # strip a specializer/typing suffix: ` :> Super`, ` :>> Super`, ` : Type`
    for sep in (" :>> ", " :> ", " : "):
        if sep in s:
            candidates.append(s.split(sep, 1)[0].strip())
            break
    # qualified paths (`Root::member`) resolve by their member first (most
    # specific), then by their root name; `A::B::*` skips the wildcard
    for c in list(candidates):
        if "::" in c:
            parts = [p.strip() for p in c.split("::") if p.strip()]
            if len(parts) > 1:
                for p in reversed(parts[1:]):
                    candidates.append(p)
                candidates.append(parts[0])
    # dotted deployment paths (`host.role.port.item`) resolve by their
    # first and last segments (host part / item name)
    for c in list(candidates):
        if "." in c and "::" not in c:
            segs = [s for s in c.split(".") if s]
            if len(segs) > 1:
                candidates.append(segs[0])
                candidates.append(segs[-1])
    # flow labels (`providerToObserverPayload of VehicleSpeedProviderMessage`)
    # resolve by the flow/feature name before " of "
    for c in list(candidates):
        if " of " in c:
            candidates.append(c.split(" of ", 1)[0].strip())
    # quoted-name form ('exchange vehicle signals' vs exchange vehicle signals)
    for c in list(candidates):
        if c.startswith("'") and c.endswith("'"):
            candidates.append(c[1:-1])
    return [c for c in candidates if c]


def _prefer(refs: list[ElementRef], view_file: str, view_folder: str) -> ElementRef | None:
    """Pick the best match: same file, then same folder, then first."""
    if not refs:
        return None
    for ref in refs:
        if ref.rel_path == view_file:
            return ref
    for ref in refs:
        if ref.rel_path.startswith(view_folder):
            return ref
    return refs[0]


@dataclass
class LabelInfo:
    """Resolved hover info for one diagram label."""

    label: str
    name: str
    kind: str
    doc: str = ""
    rel_path: str = ""
    line: int = 0
    anchor: str = ""
    x: float = 0.0
    y: float = 0.0

    def to_dict(self) -> dict[str, object]:
        d: dict[str, object] = {"name": self.name, "kind": self.kind}
        if self.doc:
            d["doc"] = self.doc
        if self.rel_path:
            d["file"] = self.rel_path
            d["line"] = self.line
            d["anchor"] = self.anchor
        return d


def _position_key(x: float, y: float) -> str:
    """Stable position key matching the SVG x/y attributes (`962` vs `244.4`)."""
    return f"{x:g},{y:g}"


def _port_contexts(
    svg_text: str, resolved: dict[str, LabelInfo]
) -> dict[str, list[tuple[float, float, float, float]]]:
    """Map a definition name (from an element box's owner label type) to the
    port glyphs on that box's edge, so an ambiguous port label can be
    assigned to the ref whose parent's box is nearest.

    Example: the observer box (owner `^observer : AAOSVehicleSpeedObserver`)
    yields ``AAOSVehicleSpeedObserver -> [observer-port-glyphs]``; the
    bundle frame yields ``AAOSVehicleSpeedServiceBundle -> [bundle glyphs]``.
    """
    positions = _text_positions(svg_text)
    boxes: list[tuple[float, float, float, float, str]] = []
    for m in _BOX_PATH_RE.finditer(svg_text):
        bbox = _path_bbox(m.group(1))
        if bbox is None:
            continue
        x1, y1, x2, y2 = bbox
        inside = [
            (x, y, plain)
            for (x, y, plain) in positions
            if (li := resolved.get(plain)) is not None
            and li.kind in _BOX_OWNER_KINDS
            and x1 < x < x2
            and y1 < y < y2
        ]
        if not inside:
            continue
        inside.sort(key=lambda t: t[1])
        plain = inside[0][2]
        def_name = plain.split(" : ", 1)[-1].strip() if " : " in plain else plain
        boxes.append((x1, y1, x2, y2, def_name))
    glyphs: dict[str, list[tuple[float, float, float, float]]] = {}
    for m in _BOX_PATH_RE.finditer(svg_text):
        bbox = _path_bbox(m.group(1))
        if bbox is None:
            continue
        x1, y1, x2, y2 = bbox
        if max(x2 - x1, y2 - y1) > 60:
            continue  # element boxes, not port glyphs
        # the SMALLEST box this glyph overlaps (glyphs straddle box edges,
        # often a few px OUTSIDE them; nearest-box wrongly picks the outer
        # frame, which contains everything)
        overlaps = [
            b
            for b in boxes
            if b[0] < x2 + 20 and b[2] > x1 - 20 and b[1] < y2 + 20 and b[3] > y1 - 20
        ]
        if not overlaps:
            continue  # glyph not on any known box edge
        owner = min(overlaps, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
        glyphs.setdefault(owner[4], []).append((x1, y1, x2, y2))
    return glyphs


def _pick_by_position(
    x: float,
    y: float,
    refs: list[ElementRef],
    glyphs: dict[str, list[tuple[float, float, float, float]]],
) -> ElementRef | None:
    """Among same-name refs with DIFFERENT parents, pick the one whose
    parent's port glyphs sit nearest the label position."""
    best: tuple[float, ElementRef] | None = None
    for ref in refs:
        gs = glyphs.get(ref.parent_name)
        if not gs:
            continue
        dist = min(_dist_point_rect(x, y, *g) for g in gs)
        if best is None or dist < best[0]:
            best = (dist, ref)
    return best[1] if best is not None else None


def _typed_doc_fallback(
    label: str,
    index: dict[str, list[ElementRef]],
    view_file: str,
    view_folder: str,
) -> str:
    """Doc of the TYPE named in a usage label (`aaosSdvBoundary :
    SDVCoreBoundary` -> the doc of `part def SDVCoreBoundary`).

    A part/port/item usage rarely carries its own `doc`; the documentation a
    reader wants when hovering the usage is the documentation of its
    definition. Returns '' when the label carries no typing or the type is
    unknown/undocumented (honest: no invented text)."""
    for key in _normalize(label):
        if " : " not in key:
            continue
        type_name = key.rsplit(" : ", 1)[-1].strip()
        if not type_name:
            return ""
        refs = index.get(type_name) or index.get(f"'{type_name}'")
        if not refs:
            return ""
        ref = _prefer(refs, view_file, view_folder)
        if ref is not None and ref.doc:
            return ref.doc
    return ""


def resolve_labels(
    labels: list[str],
    index: dict[str, list[ElementRef]],
    view_file: str,
    view_folder: str,
    svg_text: str = "",
) -> list[LabelInfo]:
    """Resolve diagram labels against the model index, most specific first.

    Compartment labels (``objective``, ``subject``, ``actors``, ``include
    use cases``, ``attributes``, ``doc ...``) have no declaration of their
    own or repeat a keyword; they resolve to the element whose compartment
    they render (the last resolved label that owns children), so hovering
    them shows that element's tooltip. Anonymous usages (``objective {``)
    are indexed under their keyword; when several exist, the one nested in
    the current context element wins.
    """
    out: list[LabelInfo] = []
    context: ElementRef | None = None
    resolved_key: dict[str, str] = {}
    if svg_text:
        items = [(x, y, plain) for (x, y, plain) in _text_positions(svg_text) if plain]
    else:
        items = [(0.0, 0.0, label) for label in labels]
    for x, y, label in items:
        ref = None
        key_hit = ""
        if context is not None and _HEADING_RE.match(label):
            # compartment headings/doc rows show their containing element
            ref = context
        else:
            for key in _normalize(label):
                refs = index.get(key)
                if not refs:
                    continue
                key_hit = key
                ref = _prefer(refs, view_file, view_folder)
                if context is not None:
                    inside = [
                        r
                        for r in refs
                        if r.parent_name == context.name
                        and r.parent_line == context.line
                    ]
                    if inside:
                        ref = inside[0]
                break  # first resolvable key wins (exact > stripped > name part)
        if ref is None:
            continue
        out.append(
            LabelInfo(
                label=label,
                name=ref.name,
                kind=ref.kind,
                doc=ref.doc,
                rel_path=ref.rel_path,
                line=ref.line,
                anchor=ref.anchor,
                x=x,
                y=y,
            )
        )
        if key_hit:
            resolved_key[label] = key_hit
        if ref.has_children and ref.kind != "package":
            context = ref
    # positional disambiguation: the SAME name can be declared several
    # times (e.g. `port structuredLogcatOut` on the observer AND on the
    # bundle). When a label's name has multiple same-file refs with
    # different parents, pick the ref whose parent's port glyphs sit
    # nearest the label position — the observer-side label resolves to
    # the observer port, the bundle-edge label to the bundle port.
    if svg_text and out:
        by_label = {li.label: li for li in out}
        glyphs = _port_contexts(svg_text, by_label)
        for i, li in enumerate(out):
            key = resolved_key.get(li.label)
            if not key:
                continue
            refs = index.get(key) or []
            same = [r for r in refs if r.rel_path == view_file]
            if len(same) < 2 or len({r.parent_name for r in same if r.parent_name}) < 2:
                continue
            alt = _pick_by_position(li.x, li.y, same, glyphs)
            if alt is not None:
                out[i] = LabelInfo(
                    label=li.label,
                    name=alt.name,
                    kind=alt.kind,
                    doc=alt.doc,
                    rel_path=alt.rel_path,
                    line=alt.line,
                    anchor=alt.anchor,
                    x=li.x,
                    y=li.y,
                )
    # typed-usage doc fallback: a usage label (`name : Type`) whose resolved
    # declaration carries no doc shows the doc of its TYPE definition instead.
    # The usage still links to its own declaration; only the doc text falls
    # back to the definition the reader actually wants.
    for i, li in enumerate(out):
        if li.doc:
            continue
        typed_doc = _typed_doc_fallback(li.label, index, view_file, view_folder)
        if typed_doc:
            out[i] = LabelInfo(
                label=li.label,
                name=li.name,
                kind=li.kind,
                doc=typed_doc,
                rel_path=li.rel_path,
                line=li.line,
                anchor=li.anchor,
                x=li.x,
                y=li.y,
            )
    return out


def labels_to_json(
    resolved: list[LabelInfo],
    page_dir: str,  # repo-relative dir of the generated page (for hrefs)
    connectors: dict[str, LabelInfo] | None = None,
) -> str:
    """Stable JSON for embedding: label -> {info, href}; plus the
    connector map (polyline points -> {info, href}) when present."""
    payload: dict[str, object] = {}
    for li in resolved:
        href = ""
        if li.anchor:
            href = f"pages/{li.rel_path}.html#{li.anchor}"
        entry = li.to_dict()
        if href:
            entry["href"] = href
        payload[li.label] = entry
    if connectors:
        conn_payload: dict[str, dict] = {}
        for pts, li in connectors.items():
            href = ""
            if li.anchor:
                href = f"pages/{li.rel_path}.html#{li.anchor}"
            entry = li.to_dict()
            if href:
                entry["href"] = href
            conn_payload[pts] = entry
        payload["connectors"] = conn_payload
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)
