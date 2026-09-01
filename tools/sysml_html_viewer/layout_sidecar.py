"""Layout sidecar: user-arranged diagram layout stored beside the model.

The committed SysIDE diagram SVGs stay the single rendering authority. This
module stores ONLY user layout adjustments (positions and sizes of elements,
routes of connectors, canvas size) as a JSON sidecar next to the diagram's
own ``diagrams/`` directory::

    <package>/diagrams/.de4sdv-diagrams/<diagram>.svg.layout.json

Design rules (deliberate, and enforced here):

- **Layout-only.** An op may move/resize existing rendered geometry. It may
  never change a label, add or remove an element, or carry any model
  content. The validation here is structural; a sidecar that references
  geometry the diagram no longer has is simply skipped at apply time.
- **Identity = raw geometry keys.** The same raw-attribute keys the viewer's
  hover JSON uses (``points`` strings, ``d`` strings, ``x,y`` text
  positions). A sidecar therefore survives model re-renders unchanged while
  the geometry is unchanged, and its ``base_sha256`` pins the exact SVG it
  was created against — a mismatch is reported as stale and the site renders
  the committed diagram unmodified (fail closed).
- **Atomic writes.** ``save_layout`` writes via a temp file + ``os.replace``
  so a crash can never leave a half-written sidecar.

The sidecar is untracked working-tree state (`.de4sdv-diagrams/` is
gitignored). It is meant to be committed to a branch by its author when a
layout is worth sharing — `git add -f` — and reviewed like any other change.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path

from .layout_apply import apply_layout, parse_path_points

LAYOUT_DIRNAME = ".de4sdv-diagrams"
LAYOUT_VERSION = 1


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sidecar_for(svg_path: Path) -> Path:
    """Sidecar file for one committed diagram SVG (beside its diagrams/ dir)."""
    svg_path = Path(svg_path)
    return svg_path.parent / LAYOUT_DIRNAME / f"{svg_path.name}.layout.json"


def _norm_num(v: object) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    f = float(v)
    if f != f or f in (float("inf"), float("-inf")):  # NaN / inf
        return None
    return f


def _norm_point(v: object) -> list[float] | None:
    if not isinstance(v, (list, tuple)) or len(v) != 2:
        return None
    x, y = _norm_num(v[0]), _norm_num(v[1])
    if x is None or y is None:
        return None
    return [x, y]


def _validate_bbox(v: object) -> list[float] | None:
    if not isinstance(v, dict):
        return None
    box = [_norm_num(v.get(k)) for k in ("x1", "y1", "x2", "y2")]
    if any(b is None for b in box):
        return None
    return [float(b) for b in box]  # type: ignore[return-value]


def validate_layout(layout: object) -> list[str]:
    """Structural validation of a layout ops record. Returns a list of errors
    (empty = valid).

    ``layout.ops`` is a LIST of edit steps applied in order; each step's
    ``find`` key names the geometry as it existed when the step was created
    (i.e. after all earlier steps), so sequential re-application on the
    committed SVG reproduces the author's final state exactly. Only
    structure and numeric sanity are checked here; unknown geometry keys are
    a normal, skippable condition at apply time."""
    errors: list[str] = []
    if not isinstance(layout, dict):
        return ["layout must be an object"]
    ops = layout.get("ops")
    if not isinstance(ops, list):
        return ["layout.ops must be a list"]
    allowed_kinds = {"text", "boxes", "connectors", "lines", "paths", "svg"}
    for i, step in enumerate(ops):
        if not isinstance(step, dict):
            errors.append(f"ops[{i}] must be an object")
            continue
        kind = step.get("kind")
        if kind not in allowed_kinds:
            errors.append(f"ops[{i}]: unknown kind {kind!r}")
            continue
        find = step.get("find")
        op = step.get("op")
        if kind == "svg":
            if not isinstance(op, dict):
                errors.append(f"ops[{i}].op must be an object")
            else:
                for k in ("width", "height"):
                    if _norm_num(op.get(k)) is None:
                        errors.append(f"ops[{i}].op.{k} must be a number")
                vb = op.get("viewBox")
                if not isinstance(vb, str) or not re.fullmatch(
                    r"-?[\d.]+(\s+-?[\d.]+){3}", vb.strip()
                ):
                    errors.append(f"ops[{i}].op.viewBox must be 'minX minY w h'")
            continue
        if not isinstance(find, str) or not find.strip():
            errors.append(f"ops[{i}].find must be a non-empty string")
            continue
        if kind == "text":
            if not isinstance(op, dict):
                errors.append(f"ops[{i}].op must be an object")
                continue
            if _norm_num(op.get("x")) is None or _norm_num(op.get("y")) is None:
                errors.append(f"ops[{i}].op needs numeric x and y")
            fs = _norm_num(op.get("font-size"))
            if fs is not None and fs <= 0:
                errors.append(f"ops[{i}].op.font-size must be > 0")
        elif kind == "boxes":
            if _validate_bbox(op) is None:
                errors.append(f"ops[{i}].op needs numeric x1,y1,x2,y2")
        elif kind == "connectors":
            if not isinstance(op, dict) or not isinstance(op.get("points"), list):
                errors.append(f"ops[{i}].op needs a points array")
                continue
            pts = [_norm_point(p) for p in op["points"]]
            if not op["points"] or any(p is None for p in pts):
                errors.append(f"ops[{i}].op.points must be [x, y] pairs")
        elif kind == "lines":
            if not isinstance(op, dict) or any(
                _norm_num(op.get(k)) is None for k in ("x1", "y1", "x2", "y2")
            ):
                errors.append(f"ops[{i}].op needs numeric x1,y1,x2,y2")
        elif kind == "paths":
            if not isinstance(op, dict) or not isinstance(op.get("d"), str):
                errors.append(f"ops[{i}].op needs a path 'd' string")
    return errors


def load_layout(svg_path: Path) -> dict | None:
    """Load and structurally validate the sidecar for one diagram.
    Returns None when absent or invalid (invalid sidecars never break the
    site; they are ignored)."""
    p = sidecar_for(svg_path)
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict) or raw.get("version") != LAYOUT_VERSION:
        return None
    if validate_layout(raw.get("layout", {})):
        return None
    return raw


def is_stale(layout: dict, svg_text: str) -> bool:
    """True when the sidecar was created against a different diagram than
    the one on disk now (fail closed: do not apply)."""
    base = layout.get("base_sha256")
    if not isinstance(base, str) or not base:
        return True
    return base != sha256_text(svg_text)


def save_layout(
    svg_path: Path,
    base_sha256: str,
    layout: dict,
    original: dict | None = None,
) -> dict:
    """Validate + write the sidecar atomically. Returns the stored record.
    Raises ValueError on invalid layout, FileNotFoundError when the SVG is
    gone."""
    svg_path = Path(svg_path)
    if not svg_path.is_file():
        raise FileNotFoundError(str(svg_path))
    if validate_layout(layout):
        raise ValueError("invalid layout: " + "; ".join(validate_layout(layout)))
    record = {
        "version": LAYOUT_VERSION,
        "base_sha256": base_sha256,
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "original": original or {},
        "layout": layout,
    }
    p = sidecar_for(svg_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, p)
    return record


def delete_layout(svg_path: Path) -> bool:
    """Remove the sidecar (Reset). True when a file was removed."""
    try:
        sidecar_for(svg_path).unlink()
        return True
    except OSError:
        return False


def layout_stats(layout: dict) -> dict:
    """Op counts by kind, for the toolbar status line."""
    ops = layout.get("ops", []) if isinstance(layout, dict) else []
    if isinstance(ops, dict):
        ops = [
            {"kind": k} for k, v in ops.items() if isinstance(v, dict) and v
        ]
    counts: dict[str, int] = {}
    for step in ops:
        if isinstance(step, dict) and step.get("kind"):
            counts[step["kind"]] = counts.get(step["kind"], 0) + 1
    return counts


def ops_total(layout: dict) -> int:
    return sum(layout_stats(layout).values())


# ---------------------------------------------------------------- loader
#
# The diagram layout context is what the page renderer and the client-side
# editor both work from: it applies the saved sidecar to the inlined SVG
# markup and emits the per-diagram payload (original + current geometry
# maps, current ops) the editor needs to compute new ops in the committed
# diagram's coordinate space.

import re  # noqa: E402  (kept late so the storage API above stays import-light)

from .layout_apply import parse_path_points  # noqa: E402

_TEXT_RE = re.compile(
    r"<text\b[^>]*?x=\"(-?[\d.]+)\"[^>]*?y=\"(-?[\d.]+)\"[^>]*>(.*?)</text>",
    re.S,
)
_WHITE_PATH_RE = re.compile(
    r"<path\b[^>]*\bd=\"([^\"]+)\"[^>]*\bfill=\"#FFFFFF\"[^>]*/?>"
)
_POLYLINE_RE = re.compile(r"<polyline\b[^>]*\bpoints=\"([^\"]+)\"[^>]*>")
_OPEN_PATH_RE = re.compile(r"<path\b[^>]*\bd=\"([^\"]+)\"[^>]*\bfill=\"none\"[^>]*/?>")
_SVG_TAG_RE = re.compile(r"<svg\b[^>]*>")


def _geom_maps(svg_text: str) -> dict:
    """Extract the editable-geometry maps of one SVG markup in the same key
    scheme the sidecar and the hover JSON use."""
    texts: dict[str, list[float]] = {}
    for m in _TEXT_RE.finditer(svg_text):
        x, y = float(m.group(1)), float(m.group(2))
        texts[f"{x:g},{y:g}"] = [x, y]
    boxes: dict[str, list[float]] = {}
    for m in _WHITE_PATH_RE.finditer(svg_text):
        pts = parse_path_points(m.group(1))
        if not pts or len(pts) < 4:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        key = f"{min(xs):g},{min(ys):g},{max(xs):g},{max(ys):g}"
        boxes.setdefault(key, [min(xs), min(ys), max(xs), max(ys)])
    connectors: dict[str, list[list[float]]] = {}
    for m in _POLYLINE_RE.finditer(svg_text):
        raw = m.group(1)
        coords = [float(v) for v in re.split(r"[,\s]+", raw.strip()) if v]
        pts = [list(p) for p in zip(coords[0::2], coords[1::2])]
        if len(pts) >= 2:
            connectors.setdefault(raw, pts)
    paths: dict[str, str] = {}
    for m in _OPEN_PATH_RE.finditer(svg_text):
        d = m.group(1)
        pts = parse_path_points(d)
        if pts and len(pts) >= 2:
            paths.setdefault(d, d)
    return {"text": texts, "boxes": boxes, "connectors": connectors, "paths": paths}


def _canvas(svg_text: str) -> list[float]:
    m = _SVG_TAG_RE.search(svg_text)
    if not m:
        return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    tag = m.group(0)

    def attr(name: str) -> float:
        mm = re.search(rf'\b{name}="([^"]*)"', tag)
        try:
            return float(mm.group(1)) if mm else 0.0
        except ValueError:
            return 0.0

    vb = [0.0, 0.0, 0.0, 0.0]
    mv = re.search(r'\bviewBox="([^"]*)"', tag)
    if mv:
        try:
            vb = [float(v) for v in mv.group(1).split()[:4]]
        except ValueError:
            pass
    return [attr("width"), attr("height"), *vb]


def diagram_layout_context(repo_root: Path) -> dict:
    """Build the layout context passed to the page renderer: ``ctx['loader'](
    svg_abs, svg_markup) -> (markup, status, meta)``.

    ``status`` carries ``stale`` / ``skipped`` for the rendered notices;
    ``meta`` is the per-diagram payload embedded as ``diagram-layout`` JSON
    (svg key, base hash, original + current geometry, current ops). Diagrams
    without a usable sidecar render unchanged and get meta with empty ops.
    """
    repo_root = Path(repo_root).resolve()

    def loader(svg_abs: Path, svg_markup: str) -> tuple[str, dict, dict]:
        svg_abs = Path(svg_abs)
        committed = svg_markup  # markup exactly as committed (prologues stripped)
        base = sha256_text(committed)
        status = {"stale": False, "skipped": [], "applied": 0}
        record = load_layout(svg_abs)
        ops: dict = {}
        if record is not None:
            ops = record["layout"].get("ops", {})
            if is_stale(record, committed):
                status["stale"] = True
            else:
                _, skipped = apply_layout(committed, record["layout"])
                status["skipped"] = skipped
                status["applied"] = ops_total(record["layout"]) - len(skipped)
                if status["applied"] > 0:
                    svg_markup = apply_layout(committed, record["layout"])[0]
        try:
            svg_key = svg_abs.resolve().relative_to(repo_root).as_posix()
        except ValueError:
            svg_key = svg_abs.name
        meta = {
            "svg": svg_key,
            "base": base,
            "orig": _geom_maps(committed),
            "cur": _geom_maps(svg_markup),
            "ops": ops,
            "canvas": {
                "orig": _canvas(committed),
                "cur": _canvas(svg_markup),
            },
        }
        return svg_markup, status, meta

    return {"loader": loader}

