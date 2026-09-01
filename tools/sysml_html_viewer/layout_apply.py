"""Deterministic layout application over committed SysIDE diagram SVGs.

Takes the user's layout ops (from ``layout_sidecar``) and rewrites the
inlined SVG markup on the fly at page-generation / serve time. The committed
SVGs are never modified — the transformed markup is used only for the served
page.

Supported ops (layout-only; nothing else is ever changed):

- ``text``: move labels (``x``/``y``), rescale (``font-size``).
- ``boxes``: move/resize the white element boxes (``x1,y1,x2,y2``), with the
  classic SysIDE rounded-box shape and the tiny port-glyph squares
  regenerated from the new geometry.
- ``connectors``: full re-route (polyline ``points``), ``lines``: re-route,
  ``paths``: re-route of open M/H/V paths.
- ``svg``: canvas width/height/viewBox.

Sizing ops also move the box's own separator polylines, its compartment
labels, and its port glyphs+labels along — proportionally, so a resized box
keeps its internal composition (the labels a viewer of the committed diagram
already associates with the box).
"""
from __future__ import annotations

import math
import re
from typing import Any

# ---------------------------------------------------------------- primitives


def fmt(v: float) -> str:
    """Format a coordinate the way SysIDE writes them (integers stay
    integers, never '34.0')."""
    if v == int(v):
        return str(int(v))
    return f"{v:.2f}".rstrip("0").rstrip(".")


class Box:
    def __init__(self, x1: float, y1: float, x2: float, y2: float):
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2

    @property
    def w(self) -> float:
        return self.x2 - self.x1

    @property
    def h(self) -> float:
        return self.y2 - self.y1


# ---------------------------------------------------------------- path model

# SysIDE element-box paths: `M x,y H x2 A 6,6 0 0 1 x,y V ... Z` with
# uppercase commands only. The parser keeps command identity so the exact
# same shape can be regenerated at a new geometry.
_PATH_TOKEN_RE = re.compile(r"([A-Z])\s*((?:-?[\d.]+[\s,]*)*)")

# Rounded-box path with the standard SysIDE structure:
# M tl H tr A(4) V br A(4) H bl A(4) V tl' A(4) Z  — corner radius 6.
# Only used to decide rounded vs plain regeneration; geometry always comes
# from parse_path_points.
_ROUNDED_BOX_RE = re.compile(
    r"^M\s+(-?[\d.]+)[,\s]+(-?[\d.]+)\s+H\s+(-?[\d.]+)"
    r"(?:\s+A\s+6,6\s+0\s+0\s+1\s+(-?[\d.]+)[,\s]+(-?[\d.]+))?"
    r"\s+V\s+(-?[\d.]+)"
    r"(?:\s+A\s+6,6\s+0\s+0\s+1\s+(-?[\d.]+)[,\s]+(-?[\d.]+))?"
    r"\s+H\s+(-?[\d.]+)"
    r"(?:\s+A\s+6,6\s+0\s+0\s+1\s+(-?[\d.]+)[,\s]+(-?[\d.]+))?"
    r"\s+V\s+(-?[\d.]+)"
    r"(?:\s+A\s+6,6\s+0\s+0\s+1\s+(-?[\d.]+)[,\s]+(-?[\d.]+))?"
    r"\s+Z\s*$"
)


def build_box_path(box: Box, radius: float = 6.0) -> str:
    """Exact SysIDE rounded-box path (`A 6,6 0 0 1` corners) for a box."""
    f = fmt
    r = radius
    return (
        f"M {f(box.x1 + r)},{f(box.y1)} H {f(box.x2 - r)} "
        f"A {f(r)},{f(r)} 0 0 1 {f(box.x2)},{f(box.y1 + r)} "
        f"V {f(box.y2 - r)} "
        f"A {f(r)},{f(r)} 0 0 1 {f(box.x2 - r)},{f(box.y2)} "
        f"H {f(box.x1 + r)} "
        f"A {f(r)},{f(r)} 0 0 1 {f(box.x1)},{f(box.y2 - r)} "
        f"V {f(box.y1 + r)} "
        f"A {f(r)},{f(r)} 0 0 1 {f(box.x1 + r)},{f(box.y1)} Z"
    )


def build_rect_path(box: Box) -> str:
    f = fmt
    return (
        f"M {f(box.x1)},{f(box.y1)} H {f(box.x2)} V {f(box.y2)} "
        f"H {f(box.x1)} V {f(box.y1)} Z"
    )


def parse_path_points(d: str) -> list[tuple[float, float]] | None:
    """All points referenced by an M/H/V(/A) path (for bbox + transform).
    Returns None for paths with unsupported commands (C/S/Q/T and lowercase
    relatives) — those are never rewritten."""
    pts: list[tuple[float, float]] = []
    cur = (0.0, 0.0)
    for m in _PATH_TOKEN_RE.finditer(d):
        cmd = m.group(1)
        if cmd not in "MHVAZ":
            return None
        if cmd == "Z":
            continue
        nums = [float(v) for v in re.findall(r"-?[\d.]+", m.group(2))]
        if cmd == "M" and len(nums) >= 2:
            cur = (nums[0], nums[1])
            pts.append(cur)
        elif cmd == "H" and nums:
            cur = (nums[0], cur[1])
            pts.append(cur)
        elif cmd == "V" and nums:
            cur = (cur[0], nums[0])
            pts.append(cur)
        elif cmd == "A":
            if len(nums) % 7:
                return None
            for i in range(0, len(nums), 7):
                pts.append((nums[i + 5], nums[i + 6]))
    return pts


def rebuild_path(d: str, tx: Any) -> str | None:
    """Rewrite an M/H/V(/A) path, mapping every point through ``tx(x, y)``.
    Arc flags/rotations are preserved; arc endpoints are transformed.
    Returns None when the path uses unsupported commands."""
    out: list[str] = []
    cur = (0.0, 0.0)
    for m in _PATH_TOKEN_RE.finditer(d):
        cmd = m.group(1)
        if cmd not in "MHVAZ":
            return None
        if cmd == "Z":
            out.append("Z")
            continue
        nums = [float(v) for v in re.findall(r"-?[\d.]+", m.group(2))]
        f = fmt
        if cmd == "M" and len(nums) >= 2:
            x, y = tx(nums[0], nums[1])
            cur = (x, y)
            out.append(f"M {f(x)},{f(y)}")
        elif cmd == "H" and nums:
            x, y = tx(nums[0], cur[1])
            cur = (x, y)
            out.append(f"H {f(x)}")
        elif cmd == "V" and nums:
            x, y = tx(cur[0], nums[0])
            cur = (x, y)
            out.append(f"V {f(y)}")
        elif cmd == "A":
            if len(nums) % 7:
                return None
            segs = []
            for i in range(0, len(nums), 7):
                rx, ry, rot, laf, sf = nums[i:i + 5]
                x, y = tx(nums[i + 5], nums[i + 6])
                cur = (x, y)
                segs.append(
                    f"A {f(rx)},{f(ry)} 0 {int(laf)} {int(sf)} {f(x)},{f(y)}"
                )
            out.append(" ".join(segs))
        else:
            return None
    return " ".join(out) if out else None


def polyline_str(points: list[tuple[float, float]]) -> str:
    return " ".join(f"{fmt(x)},{fmt(y)}" for x, y in points)


# ---------------------------------------------------------------- svg parsing

_SVG_TAG_RE = re.compile(r"<svg\b[^>]*>", re.S)
_SVG_END_RE = re.compile(r"</svg\s*>\s*$", re.S)

_NUM_ATTR = r"(-?[\d.]+)"
_TEXT_TAG_RE = re.compile(
    r"(<text\b[^>]*?)"                      # 1: attrs up to x=
    r"\sx=\"" + _NUM_ATTR + r"\"\s+y=\"" + _NUM_ATTR + r"\""  # 2,3: x, y
    r"([^>]*>)"                             # 4: rest of attrs + '>'
    r"(.*?)"                                # 5: content
    r"(</text\s*>)",                        # 6: close
    re.S,
)


def _get_attr(tag: str, name: str) -> str | None:
    m = re.search(rf'\b{name}="([^"]*)"', tag)
    return m.group(1) if m else None


def _set_attr(tag: str, name: str, value: str) -> str:
    if re.search(rf'\b{name}="[^"]*"', tag):
        return re.sub(rf'\b{name}="[^"]*"', f'{name}="{value}"', tag)
    return tag[:-1].rstrip() + f' {name}="{value}">' if tag.endswith(">") else tag


# ---------------------------------------------------------------- applicator


class _Ctx:
    """Working state of one apply_layout pass."""

    def __init__(self, svg_text: str):
        self.svg_text = svg_text
        self.errors: list[str] = []

    def replace_once(self, old: str, new: str) -> bool:
        """Replace the first occurrence of old with new. False when absent
        (geometry key gone from the diagram — op skipped)."""
        idx = self.svg_text.find(old)
        if idx == -1 or new == old:
            return old in self.svg_text and new == old
        self.svg_text = self.svg_text[:idx] + new + self.svg_text[idx + len(old):]
        return True


def apply_layout(svg_text: str, layout: dict) -> tuple[str, list[str]]:
    """Apply layout edit steps to inlined SVG markup. Returns (new_markup,
    notes).

    ``layout['ops']`` is a list of ``{kind, find, op}`` steps applied in
    order — each step's ``find`` names the geometry as it existed when the
    step was created (after all earlier steps). Notes report skipped ops
    (for the toolbar status + tests). The original ``svg_text`` is never
    modified.
    """
    ctx = _Ctx(svg_text)
    ops = (layout or {}).get("ops", [])
    if isinstance(ops, dict):  # legacy dict form: apply as final state
        ops = _legacy_ops(ops)
    for step in ops:
        if not isinstance(step, dict):
            continue
        kind = step.get("kind") or ""
        key = step.get("find", "")
        op = step.get("op", {})
        try:
            if kind == "svg":
                _apply_svg(ctx, op)
            elif kind == "text":
                _apply_text(ctx, key, op)
            elif kind == "boxes":
                _apply_box(ctx, key, op)
            elif kind == "connectors":
                _apply_connector(ctx, key, op)
            elif kind == "lines":
                _apply_line(ctx, key, op)
            elif kind == "paths":
                _apply_path(ctx, key, op)
            elif kind == "arrows":
                _apply_arrow(ctx, key, op)
        except Exception as exc:  # never break the page over an op
            ctx.errors.append(f"{kind}[{key[:24]}…]: {exc}")
    return ctx.svg_text, ctx.errors


def _legacy_ops(ops: dict) -> list[dict]:
    """Convert the dict-of-maps form into ordered steps (final-state wins:
    later entries override earlier ones per kind+key)."""
    steps: list[dict] = []
    for kind in ("svg", "text", "boxes", "connectors", "lines", "paths"):
        entries = ops.get(kind)
        if isinstance(entries, dict):
            for key, op in entries.items():
                steps.append({"kind": kind, "find": key, "op": op})
    return steps


# -- svg canvas ---------------------------------------------------------------


def _apply_svg(ctx: _Ctx, op: dict) -> None:
    m = _SVG_TAG_RE.search(ctx.svg_text)
    if not m:
        ctx.errors.append("svg: no <svg> tag found")
        return
    tag = m.group(0)
    new = tag
    for attr in ("width", "height"):
        if attr in op:
            new = _set_attr(new, attr, fmt(float(op[attr])))
    if "viewBox" in op:
        vb = " ".join(fmt(float(v)) for v in str(op["viewBox"]).split()[:4])
        new = _set_attr(new, "viewBox", vb)
    if new != tag:
        ctx.replace_once(tag, new)


# -- text ---------------------------------------------------------------------


def _apply_text(ctx: _Ctx, key: str, op: dict) -> None:
    def iter_texts():
        return _TEXT_TAG_RE.finditer(ctx.svg_text)

    target = None
    for tm in iter_texts():
        x, y = float(tm.group(2)), float(tm.group(3))
        if f"{x:g},{y:g}" == key:
            target = tm
            break
    if target is None:
        ctx.errors.append(f"text {key}: label not found (stale?)")
        return
    old = target.group(0)
    attrs, x_attr, y_attr, rest, content, close = (
        target.group(1), target.group(2), target.group(3),
        target.group(4), target.group(5), target.group(6),
    )
    nx = float(op.get("x", x_attr))
    ny = float(op.get("y", y_attr))
    attrs = _set_attr(attrs, "x", fmt(nx))
    attrs = _set_attr(attrs, "y", fmt(ny))
    fs = op.get("font-size")
    if fs is not None:
        attrs = _set_attr(attrs, "font-size", fmt(float(fs)))
    # tspans may carry absolute x/y too; shift them by the same delta
    dx, dy = nx - float(x_attr), ny - float(y_attr)
    new_content = content
    if (abs(dx) > 1e-9 or abs(dy) > 1e-9) and "<tspan" in content:

        def shift_tspan(mm: re.Match) -> str:
            t = mm.group(0)
            tx = _get_attr(t, "x")
            ty = _get_attr(t, "y")
            if tx is not None:
                t = _set_attr(t, "x", fmt(float(tx) + dx))
            if ty is not None:
                t = _set_attr(t, "y", fmt(float(ty) + dy))
            return t

        new_content = re.sub(r"<tspan\b[^>]*>", shift_tspan, content)
    new = f"{attrs} x=\"{fmt(nx)}\" y=\"{fmt(ny)}\"{rest}{new_content}{close}"
    if fs is not None:
        # font-size lives in `rest` (after the x/y pair) — rewrite it there
        new = re.sub(
            r'\bfont-size="[^"]*"', f'font-size="{fmt(float(fs))}"', new, count=1
        )
    ctx.replace_once(old, new)


# -- element boxes ------------------------------------------------------------


def _find_box(ctx: _Ctx, key: str) -> tuple[str, Box] | None:
    """Find a committed box path by its raw d attribute (or by `x1,y1,x2,y2`
    shorthand). Returns (raw_d, Box). The shape (rounded vs plain) is decided
    by the path grammar; the geometry comes from parse_path_points so x/y can
    never mix up."""
    for m in re.finditer(
        r'<path\b[^>]*\bd="([^"]+)"[^>]*\bfill="#FFFFFF"[^>]*/?>',
        ctx.svg_text,
    ):
        d = m.group(1)
        pts = parse_path_points(d)
        if not pts or len(pts) < 4:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        box = Box(min(xs), min(ys), max(xs), max(ys))
        if d == key or f"{box.x1:g},{box.y1:g},{box.x2:g},{box.y2:g}" == key:
            return d, box
    return None


def _apply_box(ctx: _Ctx, key: str, op: dict) -> None:
    """Rewrite one element box to its new geometry. Companions (labels,
    separators, port glyphs, attached connector ends, arrowheads) are moved
    by their OWN explicit ops — the client records them, this applier never
    infers them (single source of truth, exactly reproducible)."""
    found = _find_box(ctx, key)
    if found is None:
        ctx.errors.append(f"box {key[:24]}…: not found (stale?)")
        return
    old_d, old = found
    x1 = float(op.get("x1", old.x1))
    y1 = float(op.get("y1", old.y1))
    x2 = float(op.get("x2", old.x2))
    y2 = float(op.get("y2", old.y2))
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1
    new = Box(x1, y1, x2, y2)
    rounded = bool(_ROUNDED_BOX_RE.match(old_d))
    new_d = build_box_path(new) if rounded else build_rect_path(new)
    if not ctx.replace_once(f'd="{old_d}"', f'd="{new_d}"'):
        ctx.errors.append(f"box {key[:24]}…: path text vanished mid-apply")


def _parse_points(raw: str) -> list[tuple[float, float]]:
    coords = [float(v) for v in re.split(r"[,\s]+", raw.strip()) if v]
    return list(zip(coords[0::2], coords[1::2]))


# -- connectors ----------------------------------------------------------------


def _apply_connector(ctx: _Ctx, key: str, op: dict) -> None:
    pts = op.get("points") or []
    flat = " ".join(f"{fmt(p[0])},{fmt(p[1])}" for p in pts)
    if not ctx.replace_once(f'points="{key}"', f'points="{flat}"'):
        ctx.errors.append(f"connector {key[:24]}…: not found (stale?)")


# SysIDE arrowheads: `<g transform="translate(x,y) rotate(a) scale(s) …"
# fill="#1A1A1A">` groups placed at the line end. Layout ops move them by
# rewriting the translate(x,y) prefix.
_ARROW_G_RE = re.compile(
    r'<g\b[^>]*?\btransform="translate\((-?[\d.]+),(-?[\d.]+)\)[^"]*"\s*'
    r'fill="#1A1A1A"'
)


def _apply_arrow(ctx: _Ctx, key: str, op: dict) -> None:
    kx, ky = (float(v) for v in key.split(","))
    nx = float(op.get("x", kx))
    ny = float(op.get("y", ky))
    found = None
    for m in _ARROW_G_RE.finditer(ctx.svg_text):
        if f"{float(m.group(1)):g},{float(m.group(2)):g}" == f"{kx:g},{ky:g}":
            found = m
            break
    if found is None:
        ctx.errors.append(f"arrow {key}: not found (stale?)")
        return
    old = found.group(0)
    old_tr = f"translate({fmt(float(found.group(1)))},{fmt(float(found.group(2)))})"
    new_tr = f"translate({fmt(nx)},{fmt(ny)})"
    ctx.replace_once(old, old.replace(old_tr, new_tr, 1))


def _apply_line(ctx: _Ctx, key: str, op: dict) -> None:
    # find the specific line element by its current coords
    x1, y1, x2, y2 = (float(v) for v in key.split(","))
    pat = re.compile(
        r'<line\b[^>]*\bx1="' + re.escape(fmt(x1)) + r'"[^>]*\by1="'
        + re.escape(fmt(y1)) + r'"[^>]*\bx2="' + re.escape(fmt(x2))
        + r'"[^>]*\by2="' + re.escape(fmt(y2)) + r'"[^>]*/?>'
    )
    mm = pat.search(ctx.svg_text)
    if mm is None:
        ctx.errors.append(f"line {key}: not found (stale?)")
        return
    raw = mm.group(0)
    n = _set_attr(raw, "x1", fmt(float(op.get("x1", x1))))
    n = _set_attr(n, "y1", fmt(float(op.get("y1", y1))))
    n = _set_attr(n, "x2", fmt(float(op.get("x2", x2))))
    n = _set_attr(n, "y2", fmt(float(op.get("y2", y2))))
    ctx.replace_once(raw, n)


def _apply_path(ctx: _Ctx, key: str, op: dict) -> None:
    new_d = op.get("d", "")
    # only geometry the engine can parse is layout-editable; a curved or
    # otherwise unsupported path key is never rewritten
    if not parse_path_points(key):
        ctx.errors.append(f"path {key[:24]}…: unsupported path grammar")
        return
    if not ctx.replace_once(f'd="{key}"', f'd="{new_d}"'):
        ctx.errors.append(f"path {key[:24]}…: not found (stale?)")
