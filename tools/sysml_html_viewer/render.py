"""HTML rendering for the DE4SDV static model viewer.

Layout follows the read-only "project browser" pattern: a persistent left
navigation tree and a right content pane showing the selected package,
file, element, or view. All links are relative so the site works from
``file://`` and from any static host rooted at the repository.

The viewer is deliberately non-editing: it links the committed SysIDE
diagram artifacts (``diagrams/diagram-<view>.svg`` beside the model files)
instead of re-rendering or re-laying-out anything.
"""
from __future__ import annotations

import html
import json
import posixpath
import re
from pathlib import Path

from .model_parse import (
    ModelFile,
    TreeNode,
    ViewInfo,
    artifact_filename,
    slugify,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def make_anchor(counter: dict[str, int], name: str) -> str:
    base = slugify(name)
    counter[base] = counter.get(base, 0) + 1
    return base if counter[base] == 1 else f"{base}-{counter[base]}"


# ---------------------------------------------------------------------------
# Icons (inline SVG, one per element kind family)
# ---------------------------------------------------------------------------

_ICONS = {
    "package": '<svg viewBox="0 0 16 16"><path d="M2 3h12v10H2z" fill="none" stroke="#8a63d2" stroke-width="1.3"/><path d="M2 3h12v2H2z" fill="#8a63d2"/></svg>',
    "view": '<svg viewBox="0 0 16 16"><rect x="1.5" y="2" width="13" height="12" rx="1.5" fill="none" stroke="#2e7d32" stroke-width="1.3"/><path d="M4 7.5l2.5 2.5L12 5" fill="none" stroke="#2e7d32" stroke-width="1.5"/></svg>',
    "viewpoint": '<svg viewBox="0 0 16 16"><path d="M8 2l5 3v6l-5 3-5-3V5z" fill="none" stroke="#00695c" stroke-width="1.3"/><circle cx="8" cy="8" r="1.6" fill="#00695c"/></svg>',
    "concern": '<svg viewBox="0 0 16 16"><path d="M8 1.5L14.5 4v5.5L8 14.5 1.5 9.5V4z" fill="none" stroke="#b26a00" stroke-width="1.3"/><path d="M8 5.5v3.5" stroke="#b26a00" stroke-width="1.5"/><circle cx="8" cy="11" r="0.9" fill="#b26a00"/></svg>',
    "requirement": '<svg viewBox="0 0 16 16"><rect x="2" y="2.5" width="12" height="11" rx="1" fill="none" stroke="#1565c0" stroke-width="1.3"/><path d="M5 6h6M5 8.5h6M5 11h3.5" stroke="#1565c0" stroke-width="1.3" stroke-linecap="round"/></svg>',
    "part": '<svg viewBox="0 0 16 16"><rect x="2" y="3" width="12" height="10" rx="1.2" fill="none" stroke="#37474f" stroke-width="1.3"/><path d="M2 6h12" stroke="#37474f" stroke-width="1.3"/></svg>',
    "item": '<svg viewBox="0 0 16 16"><ellipse cx="8" cy="8" rx="5.5" ry="3.2" fill="none" stroke="#6d4c41" stroke-width="1.3"/><path d="M2.5 8v3.5c0 1.8 2.5 3.2 5.5 3.2s5.5-1.4 5.5-3.2V8" fill="none" stroke="#6d4c41" stroke-width="1.3"/></svg>',
    "port": '<svg viewBox="0 0 16 16"><rect x="2.5" y="5.5" width="6" height="5" fill="none" stroke="#455a64" stroke-width="1.3"/><path d="M8.5 8h5M11 6.5v3" stroke="#455a64" stroke-width="1.3"/></svg>',
    "flow": '<svg viewBox="0 0 16 16"><path d="M2 11h8" stroke="#00838f" stroke-width="1.5"/><path d="M7.5 8.5L10 11l-2.5 2.5" fill="none" stroke="#00838f" stroke-width="1.5"/></svg>',
    "interface": '<svg viewBox="0 0 16 16"><path d="M3 4h6v4H3z" fill="none" stroke="#5e35b1" stroke-width="1.3"/><path d="M9 6h4l-1.5 2" stroke="#5e35b1" stroke-width="1.3"/></svg>',
    "action": '<svg viewBox="0 0 16 16"><rect x="3" y="2.5" width="10" height="4" rx="1" fill="none" stroke="#c62828" stroke-width="1.3"/><rect x="3" y="9.5" width="10" height="4" rx="1" fill="none" stroke="#c62828" stroke-width="1.3"/></svg>',
    "state": '<svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="5.5" fill="none" stroke="#2e7d32" stroke-width="1.3"/><circle cx="8" cy="8" r="1.3" fill="#2e7d32"/></svg>',
    "attribute": '<svg viewBox="0 0 16 16"><path d="M3 4h10M3 8h10M3 12h6" stroke="#607d8b" stroke-width="1.3" stroke-linecap="round"/></svg>',
    "metadata": '<svg viewBox="0 0 16 16"><path d="M2 3.5h12v9H2z" fill="none" stroke="#546e7a" stroke-width="1.3"/><path d="M2 6.5h12" stroke="#546e7a" stroke-width="1.3"/></svg>',
    "file": '<svg viewBox="0 0 16 16"><path d="M3 1.5h6l4 4v9H3z" fill="none" stroke="#78909c" stroke-width="1.3"/><path d="M9 1.5v4h4" fill="none" stroke="#78909c" stroke-width="1.3"/></svg>',
    "dir": '<svg viewBox="0 0 16 16"><path d="M1.5 3.5h5l1.5 2h6.5v7h-13z" fill="none" stroke="#8a63d2" stroke-width="1.3"/></svg>',
    "root": '<svg viewBox="0 0 16 16"><path d="M8 1.5L15 6.5v8H9.5v-4.5h-3V14.5H1v-8z" fill="none" stroke="#37474f" stroke-width="1.3"/></svg>',
    "other": '<svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="5" fill="none" stroke="#90a4ae" stroke-width="1.3"/></svg>',
}


def _icon(kind: str) -> str:
    base = kind.split()[0]
    for key in (kind, base):
        if key in _ICONS:
            return _ICONS[key]
    if base.endswith("def"):
        return _ICONS.get(base[:-4], _ICONS["other"])
    return _ICONS["other"]


# ---------------------------------------------------------------------------
# Navigation tree
# ---------------------------------------------------------------------------


def render_tree(node: TreeNode, active_href: str = "", depth: int = 0) -> str:
    """Recursive nav tree. Expandable nodes use <details> (no JS required)."""
    cls = f"tree-node tree-{node.kind}"
    if node.href and node.href == active_href:
        cls += " active"
    kids = "".join(render_tree(c, active_href, depth + 1) for c in node.children)
    inner = f'<span class="tree-icon">{_icon(node.kind)}</span>'
    if node.href:
        label = f'<a href="{esc(node.href)}">{esc(node.label)}</a>'
    else:
        label = f"<span class='tree-label'>{esc(node.label)}</span>"
    meta = f"<span class='tree-meta'>{esc(node.meta)}</span>" if node.meta else ""
    if kids:
        open_attr = " open" if depth <= 1 or node.href == active_href else ""
        return (
            f'<details class="{cls}"{open_attr}><summary>{inner} {label} {meta}</summary>'
            f"<ul>{kids}</ul></details>"
        )
    return f'<li class="{cls}">{inner} {label} {meta}</li>'


def render_ref_picker(
    refs: list[tuple[str, str, bool, str, bool]], current: str, site: str
) -> str:
    """Header revision picker: one <option> per known revision, with relative
    hrefs computed from this page's site path so the site keeps working from
    file:// (no fetch, no absolute paths).

    Each entry is (site-root target, label, enabled, title, buildable).
    Revisions that exist in the repository but were not built at generation
    time appear as disabled options whose title explains why. The
    "served statically" hint is shown only when a *buildable* revision is
    missing — on published snapshots (all buildable refs built) disabled
    entries are genuinely unbuildable and the hint would be noise.
    """
    if not refs:
        return ""
    opts = []
    has_disabled_buildable = False
    for target, label, enabled, title, buildable in refs:
        # browsers resolve relative URLs from the page's directory, not the
        # page file itself
        base = posixpath.dirname(site)
        rel = posixpath.relpath(target, base) if target else ""
        sel = " selected" if target and target == current else ""
        dis = "" if enabled else " disabled"
        if not enabled and buildable:
            has_disabled_buildable = True
        tip = f' title="{esc(title)}"' if title else ""
        opts.append(f'<option value="{esc(rel)}"{sel}{dis}{tip}>{esc(label)}</option>')
    note = ""
    if has_disabled_buildable:
        note = (
            '<span class="ref-picker-note">served statically — run '
            "<code>python -m tools.sysml_html_viewer.serve</code> "
            "to make every branch selectable</span>"
        )
    return (
        '<span class="ref-picker-wrap" title="Show the viewer for another '
        'branch or pull request">'
        '<span class="ref-picker-label">Revision</span>'
        f'<select class="ref-picker" id="refPicker">'
        f'{"".join(opts)}'
        f"</select>{note}</span>"
    )


# ---------------------------------------------------------------------------
# Page shell
# ---------------------------------------------------------------------------


def _page_shell(
    title: str,
    tree_html: str,
    breadcrumbs: list[tuple[str, str]],
    content: str,
    css_rel: str,
    js_rel: str,
    picker: str = "",
    body_class: str = "",
    search_prefix: str = "",
    asset_stamp: str = "",
) -> str:
    crumbs = " / ".join(
        f'<a href="{esc(href)}">{esc(label)}</a>' for label, href in breadcrumbs
    )
    body_attr = f' class="{esc(body_class)}"' if body_class else ""
    body_attr += f' data-search-prefix="{esc(search_prefix)}"'
    if asset_stamp:
        css_rel += f"?v={asset_stamp}"
        js_rel += f"?v={asset_stamp}"
    search_index_rel = search_prefix + "assets/search-index.js"
    if asset_stamp:
        search_index_rel += f"?v={asset_stamp}"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} — DE4SDV Model Viewer</title>
<link rel="stylesheet" href="{esc(css_rel)}">
</head>
<body{body_attr}>
<header class="site-header">
  <a class="site-title" href="{esc(search_prefix + 'index.html')}">DE4SDV <em>Model Viewer</em></a>
  <span class="site-sub">read-only browser over the SysML v2 textual model</span>
  {picker}
</header>
<div class="layout">
  <nav class="tree-pane" aria-label="Model navigation">
    <div class="tree-title">Project</div>
    <div class="tree-search-wrap">
      <input type="search" id="treeSearch" class="tree-search"
             placeholder="Search model (names, kinds, docs)…"
             autocomplete="off" aria-label="Search the model">
    </div>
    <div id="treeSearchResults" class="tree-search-results" hidden></div>
    <div id="treeNav">
      {tree_html}
    </div>
  </nav>
  <div class="tree-resizer" id="treeResizer" title="Drag to resize the model tree" aria-hidden="true"></div>
  <main class="content-pane">
    <div class="breadcrumb">{crumbs}</div>
    {content}
  </main>
</div>
<script src="{esc(search_index_rel)}"></script>
<script src="{esc(js_rel)}"></script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Index / TOC pages
# ---------------------------------------------------------------------------


def render_index(
    tree: TreeNode,
    stats: dict[str, int],
    file_count_with_diagrams: int,
    picker: str = "",
    search_prefix: str = "",
    asset_stamp: str = "",
) -> str:
    tree_html = render_tree(tree, "")
    stats_html = "".join(
        f"<div class='stat'><span class='stat-n'>{v}</span><span class='stat-k'>{k}</span></div>"
        for k, v in [
            ("files", stats["files"]),
            ("views", stats["views"]),
            ("diagrams", file_count_with_diagrams),
            ("members", stats["members"]),
        ]
    )
    # getting-started links derive from the actual tree, never hardcode
    files = _collect_files(tree)
    start_links = []
    for f in files[:2]:
        start_links.append(
            f'<li>Start with <a href="{esc(f.href)}">{esc(f.label)}</a>.</li>'
        )
    if not start_links:
        start_links = ["<li>No model files were found.</li>"]
    content = f"""
<div class="card welcome">
  <h1>DE4SDV systems model</h1>
  <p>Browse the software-defined vehicle (SDV) systems model: packages,
  declared members, and every SysML v2 <strong>view</strong> with the diagram
  SysIDE renders from it. Click through the tree on the left — views open with
  their full diagram and view definition metadata.</p>
  <p>This viewer is generated from the authoritative <code>.sysml</code>
  textual notation. It only links artifacts that exist in the repository;
  it never invents elements or re-renders diagrams.</p>
  <div class="stats">{stats_html}</div>
</div>
<div class="card">
  <h2>Getting started</h2>
  <ul>
    {''.join(start_links)}
    <li>Open any <span class="kind-badge view-badge">view</span> in a file page to see its diagram and definition.</li>
    <li>Elements in the tree jump to their declaration line in the highlighted source below the diagrams.</li>
  </ul>
</div>
"""
    return _page_shell(
        "Model", tree_html, [("Model", "index.html")], content,
        css_rel="assets/viewer.css", js_rel="assets/viewer.js",
        picker=picker, search_prefix=search_prefix, asset_stamp=asset_stamp,
    )


def _collect_files(node: TreeNode) -> list[TreeNode]:
    out = []
    if node.kind == "file":
        out.append(node)
    for c in node.children:
        out.extend(_collect_files(c))
    return out


def render_dir_page(
    dir_label: str,
    breadcrumbs: list[tuple[str, str]],
    tree_html: str,
    children: list[TreeNode],
    prefix: str,
    picker: str = "",
    search_prefix: str = "",
    asset_stamp: str = "",
) -> str:
    items = []
    for c in children:
        if c.kind == "dir":
            items.append(
                f"<li class='dir-item'>{_icon('dir')} <a href='{esc(c.href)}'>{esc(c.label)}</a></li>"
            )
        elif c.kind == "file":
            items.append(
                f"<li class='file-item'>{_icon('file')} <a href='{esc(c.href)}'>{esc(c.label)}</a>"
                f"<span class='tree-meta'>{len(c.children)} items</span></li>"
            )
        else:
            items.append(
                f"<li class='child-item'>{_icon(c.kind)} <a href='{esc(c.href)}'>{esc(c.label)}</a></li>"
            )
    content = (
        f"<div class='card'><h1>{esc(dir_label)}</h1>"
        f"<ul class='toc-list'>{''.join(items)}</ul></div>"
    )
    return _page_shell(
        dir_label, tree_html, breadcrumbs, content,
        css_rel=prefix + "assets/viewer.css", js_rel=prefix + "assets/viewer.js",
        picker=picker, search_prefix=search_prefix, asset_stamp=asset_stamp,
    )


# ---------------------------------------------------------------------------
# Source view
# ---------------------------------------------------------------------------

_SRC_KEYWORDS = frozenset(
    """
    package import part def requirement view viewpoint concern expose frame
    render attribute abstract doc flow port item interface state action usage
    exhibit in out then first last all only require constraint ref assert and
    or not true false
    """.split()
)

_SRC_TOKEN_RE = re.compile(
    r"'[^']*'|:>>|:>|::|->|=>|"
    r"\b\d+(?:\.\d+)?\b|"
    r"\b[A-Za-z_][A-Za-z0-9_]*\b|.",
)

# per-line scan: quoted names first, then comment openers
_LINE_SCAN_RE = re.compile(r"'[^']*'|/\*|//")

_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _resolve_source_ref(
    token: str, line_no: int, mf: ModelFile, member_index: dict
):
    """Resolve an identifier in the source to its declaration, or None.

    The declaration itself is never annotated; usages in the same file
    resolve to the same file, everything else to the defining file.
    """
    refs = member_index.get(token)
    if not refs:
        return None
    if any(r.rel_path == mf.rel_path and r.line == line_no for r in refs):
        return None
    from .svg_info import _prefer

    folder = str(Path(mf.rel_path).parent)
    return _prefer(refs, mf.rel_path, folder)


def _token_class(tok: str) -> str:
    if tok in _SRC_KEYWORDS:
        return "kw"
    if tok in (":>>", ":>", "::", "->", "=>"):
        return "op"
    if tok.replace(".", "").isdigit():
        return "num"
    return ""


def _highlight_code(
    seg: str,
    line_no: int,
    mf: ModelFile | None,
    member_index: dict | None,
    prefix: str,
) -> str:
    """Highlight keywords/numbers/operators in a comment-free segment and
    wrap identifiers that resolve to model elements as source references."""
    out = []
    pos = 0
    for m in _SRC_TOKEN_RE.finditer(seg):
        out.append(esc(seg[pos : m.start()]))
        tok = m.group(0)
        cls = _token_class(tok)
        if cls:
            out.append(f'<span class="src-{cls}">{esc(tok)}</span>')
        else:
            ref = None
            if mf is not None and member_index is not None and _IDENT_RE.fullmatch(tok):
                ref = _resolve_source_ref(tok, line_no, mf, member_index)
            if ref is not None:
                same = ref.rel_path == mf.rel_path
                href = (
                    f"#src-{ref.line}"
                    if same
                    else prefix + f"pages/{ref.rel_path}.html#src-{ref.line}"
                )
                tip = (
                    f' data-tip-kind="{esc(ref.kind)}"'
                    f' data-tip-name="{esc(ref.name)}"'
                )
                if ref.doc:
                    tip += f' data-tip-doc="{esc(ref.doc)}"'
                tip += f' data-tip-file="{esc(ref.rel_path)}" data-tip-line="{ref.line}"'
                tip += (
                    ' data-tip-hint="click to jump to declaration"'
                    if same
                    else ' data-tip-hint="click to jump to definition"'
                )
                out.append(
                    f'<a class="src-ref" href="{esc(href)}"{tip}>{esc(tok)}</a>'
                )
            else:
                out.append(esc(tok))
        pos = m.end()
    out.append(esc(seg[pos:]))
    return "".join(out)


def _highlight_line(
    line: str,
    in_block: bool,
    line_no: int,
    mf: ModelFile | None,
    member_index: dict | None,
    prefix: str,
) -> tuple[str, bool]:
    """Highlight one source line; returns (html, still_in_block_comment).

    Multi-line /* ... */ comments are split per line so every .src-line
    block is self-contained — a comment spanning lines must never nest
    later lines inside the first line's block.
    """
    out = []
    pos = 0
    if in_block:
        end = line.find("*/")
        if end == -1:
            return f'<span class="src-cmt">{esc(line)}</span>', True
        out.append(f'<span class="src-cmt">{esc(line[: end + 2])}</span>')
        pos = end + 2
        in_block = False
    while pos < len(line):
        m = _LINE_SCAN_RE.search(line, pos)
        if not m:
            out.append(_highlight_code(line[pos:], line_no, mf, member_index, prefix))
            break
        out.append(_highlight_code(line[pos : m.start()], line_no, mf, member_index, prefix))
        tok = m.group(0)
        if tok.startswith("'"):
            out.append(f'<span class="src-str">{esc(tok)}</span>')
            pos = m.end()
        elif tok == "/*":
            end = line.find("*/", m.end())
            if end == -1:
                out.append(f'<span class="src-cmt">{esc(line[m.start() :])}</span>')
                pos = len(line)
                in_block = True
            else:
                out.append(f'<span class="src-cmt">{esc(line[m.start() : end + 2])}</span>')
                pos = end + 2
        else:  # "//" line comment to end of line
            out.append(f'<span class="src-cmt">{esc(line[m.start() :])}</span>')
            pos = len(line)
    return "".join(out), in_block


def _highlight_source(
    text: str,
    mf: ModelFile | None = None,
    member_index: dict | None = None,
    prefix: str = "",
) -> str:
    """Syntax-highlight the .sysml source and wrap resolvable identifiers
    as source references (hover tooltip + jump to the definition).

    Line blocks are joined WITHOUT newlines: inside a <pre> with
    white-space: pre, a newline between two block elements renders as an
    extra line box, doubling the perceived line spacing.
    """
    in_block = False
    body = []
    for i, raw in enumerate(text.split("\n"), 1):
        html, in_block = _highlight_line(raw, in_block, i, mf, member_index, prefix)
        body.append(
            f'<span class="src-line" id="src-{i}">'
            f'<span class="src-ln">{i}</span>{html}</span>'
        )
    return "".join(body)


# ---------------------------------------------------------------------------
# File pages
# ---------------------------------------------------------------------------


def _inline_svg(svg_abs: Path) -> str:
    """Read a committed diagram SVG and strip XML/DOCTYPE prologues so it can
    be inlined into the page (hover enrichment needs the DOM, not <img>)."""
    try:
        text = svg_abs.read_text(encoding="utf-8")
    except OSError:
        return ""
    text = re.sub(r"^<\?xml[^>]*\?>", "", text).lstrip()
    text = re.sub(r"^<!DOCTYPE[^>]*>", "", text).lstrip()
    if not text.startswith("<svg"):
        return ""
    return text


def _svg_hover_json(
    svg_markup: str,
    v: ViewInfo,
    mf: ModelFile,
    member_index: dict,
    prefix: str,
) -> str:
    """Build the label -> element-info JSON embedded next to the diagram."""
    from . import svg_info

    labels = svg_info.extract_text_labels(svg_markup)
    folder = str(Path(mf.rel_path).parent)
    resolved = svg_info.resolve_labels(labels, member_index, mf.rel_path, folder)
    payload: dict[str, dict] = {}
    for li in resolved:
        entry = li.to_dict()
        if li.anchor:
            entry["href"] = prefix + f"pages/{li.rel_path}.html#{li.anchor}"
        payload[li.label] = entry
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return raw.replace("</", "<\\/")


def _diagram_missing(artifact: str, svg_rel: str) -> str:
    if svg_rel:
        return (
            '<div class="diagram-missing"><strong>Diagram not inlined.</strong> '
            f'<a href="{esc(svg_rel)}" target="_blank" rel="noopener">open raw SVG</a>.</div>'
        )
    return (
        '<div class="diagram-missing"><strong>No committed diagram.</strong> '
        "Regenerate via the Privileged Syside Validation workflow "
        f"(expected artifact <code>diagrams/{esc(artifact)}</code>).</div>"
    )


def _render_view_block(
    v: ViewInfo,
    mf: ModelFile,
    repo_prefix: str,
    prefix: str,
    member_index: dict,
    anchor_counter: dict[str, int],
    blob_base: str = "",
    external_ref: bool = False,
) -> str:
    anchor = make_anchor(anchor_counter, v.name)
    artifact = artifact_filename(v.name, v.view_type)
    svg_abs = mf.path.parent / "diagrams" / artifact
    if svg_abs.exists():
        if blob_base:
            # ref builds materialize from git; point the raw artifact at GitHub
            svg_rel = blob_base + "/" + (
                Path(mf.rel_path).parent / "diagrams" / artifact
            ).as_posix()
        elif external_ref:
            # ref build without a GitHub remote: no raw-artifact link at all
            svg_rel = ""
        else:
            svg_rel = repo_prefix + (Path(mf.rel_path).parent / "diagrams" / artifact).as_posix()
        svg_markup = _inline_svg(svg_abs)
        if svg_markup:
            svg_info_json = _svg_hover_json(svg_markup, v, mf, member_index, prefix)
            raw_link = (
                f' <a href="{esc(svg_rel)}" target="_blank" rel="noopener">open raw SVG</a>.'
                if svg_rel
                else "."
            )
            diagram_html = (
                f'<div class="diagram-frame interactive" data-view="{esc(anchor)}">'
                f'<div class="diagram-toolbar">'
                f'<span class="diagram-toolbar-file">{esc(artifact)}</span>'
                f'<button type="button" class="diagram-fs-btn" '
                f'title="Fullscreen (Esc to close)">&#x26F6; Fullscreen</button>'
                f"</div>"
                f'<div class="diagram-scroll">{svg_markup}</div>'
                f"</div>"
                f'<p class="muted">Hover a model element for details{raw_link}</p>'
                f'<script type="application/json" class="diagram-info" '
                f'data-for="{esc(anchor)}">{svg_info_json}</script>'
            )
        else:
            diagram_html = _diagram_missing(artifact, svg_rel)
    else:
        diagram_html = _diagram_missing(artifact, "")
    rows = []
    if v.viewpoint:
        rows.append(
            ("Viewpoint", f"<code>{esc(v.viewpoint)}</code>"
             f"<span class='muted'> ({esc(v.viewpoint_type)})</span>")
        )
    if v.view_type:
        rows.append(("View type", f"<code>{esc(v.view_type)}</code>"))
    if v.concern:
        rows.append(("Concern", f"<code>{esc(v.concern)}</code>"))
    if v.render:
        rows.append(("Render", f"<code>{esc(v.render)}</code>"))
    if v.depth:
        rows.append(("Depth", f"<code>{esc(v.depth)}</code>"))
    if v.exposes:
        rows.append(
            ("Exposes", "<br>".join(f"<code>{esc(e)}</code>" for e in v.exposes))
        )
    rows.append(("Source", f"<code>{esc(mf.rel_path)}:{v.line}</code>"))
    meta_html = "".join(
        f"<tr><th>{esc(k)}</th><td>{val}</td></tr>" for k, val in rows
    )
    doc_html = (
        f'<div class="doc-block"><h4>Notes</h4><p>{esc(v.doc)}</p></div>'
        if v.doc
        else ""
    )
    return f"""
<section class="view-section" id="view-{anchor}">
  <h2><span class="kind-badge view-badge">view</span> {esc(v.name)}</h2>
  <table class="meta-table">{meta_html}</table>
  {doc_html}
  {diagram_html}
</section>
"""


def render_file_page(
    mf: ModelFile,
    tree_html: str,
    prefix: str,
    repo_prefix: str,
    breadcrumbs: list[tuple[str, str]],
    source_url: str,
    member_index: dict,
    picker: str = "",
    blob_base: str = "",
    external_ref: bool = False,
    search_prefix: str = "",
    asset_stamp: str = "",
) -> str:
    anchor_counter: dict[str, int] = {}
    views_html = "".join(
        _render_view_block(
            v, mf, repo_prefix, prefix, member_index, anchor_counter,
            blob_base, external_ref,
        )
        for v in mf.views
    )
    doc_html = f'<div class="doc-block"><p>{esc(mf.file_doc)}</p></div>' if mf.file_doc else ""
    view_count = len(mf.views)
    source_link = (
        f'<a class="source-link" href="{esc(source_url)}" target="_blank" rel="noopener">'
        "view source on GitHub</a>"
        if source_url
        else ""
    )
    try:
        source_html = _highlight_source(
            mf.path.read_text(encoding="utf-8"), mf, member_index, prefix
        )
    except OSError:
        source_html = "<p class='muted'>Source file not readable.</p>"
    content = f"""
<div class="card file-header">
  <h1>{esc(mf.rel_path)}</h1>
  <p class="muted">{view_count} view(s) · {len(mf.members)} declared member(s) {source_link}</p>
  {doc_html}
</div>
{views_html}
<div class="card">
  <h2>Source</h2>
  <pre class="source-view">{source_html}</pre>
</div>
"""
    return _page_shell(
        f"{mf.rel_path}", tree_html, breadcrumbs, content,
        css_rel=prefix + "assets/viewer.css", js_rel=prefix + "assets/viewer.js",
        picker=picker, search_prefix=search_prefix, asset_stamp=asset_stamp,
    )
