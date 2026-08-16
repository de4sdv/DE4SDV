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
import re
from pathlib import Path

from .model_parse import ModelFile, TreeNode, ViewInfo, artifact_filename

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def slugify(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-")
    return slug or "item"


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


def _kind_label(kind: str) -> str:
    label = kind.replace("def", "def")
    return label


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


# ---------------------------------------------------------------------------
# Page shell
# ---------------------------------------------------------------------------


def _page_shell(
    title: str,
    tree_html: str,
    breadcrumbs: list[tuple[str, str]],
    content: str,
    css_rel: str,
) -> str:
    crumbs = " / ".join(
        f'<a href="{esc(href)}">{esc(label)}</a>' for label, href in breadcrumbs
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} — DE4SDV Model Viewer</title>
<link rel="stylesheet" href="{esc(css_rel)}">
</head>
<body>
<header class="site-header">
  <span class="site-title">DE4SDV <em>Model Viewer</em></span>
  <span class="site-sub">read-only browser over the SysML v2 textual model</span>
</header>
<div class="layout">
  <nav class="tree-pane" aria-label="Model navigation">
    <div class="tree-title">Project</div>
    {tree_html}
  </nav>
  <main class="content-pane">
    <div class="breadcrumb">{crumbs}</div>
    {content}
  </main>
</div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Index / TOC pages
# ---------------------------------------------------------------------------


def render_index(tree: TreeNode, stats: dict[str, int], file_count_with_diagrams: int) -> str:
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
    <li>Element pages live inside the file page of the model file that declares them.</li>
  </ul>
</div>
"""
    return _page_shell(
        "Model", tree_html, [("Model", "index.html")], content, css_rel="assets/viewer.css"
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
        dir_label, tree_html, breadcrumbs, content, css_rel=prefix + "assets/viewer.css"
    )


# ---------------------------------------------------------------------------
# File pages
# ---------------------------------------------------------------------------


def _render_view_block(
    v: ViewInfo,
    mf: ModelFile,
    repo_prefix: str,
    anchor_counter: dict[str, int],
) -> str:
    anchor = make_anchor(anchor_counter, v.name)
    artifact = artifact_filename(v.name, v.view_type)
    svg_abs = mf.path.parent / "diagrams" / artifact
    svg_rel = ""
    if svg_abs.exists():
        svg_rel = repo_prefix + (Path(mf.rel_path).parent / "diagrams" / artifact).as_posix()
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
    if svg_rel:
        diagram_html = (
            f'<div class="diagram-frame">'
            f'<a href="{esc(svg_rel)}" target="_blank" rel="noopener">'
            f'<img class="diagram-image" src="{esc(svg_rel)}" alt="Diagram of view {esc(v.name)}">'
            f"</a></div>"
        )
    else:
        diagram_html = (
            '<div class="diagram-missing"><strong>No committed diagram.</strong> '
            "Regenerate via the Privileged Syside Validation workflow "
            f"(expected artifact <code>diagrams/{esc(artifact)}</code>).</div>"
        )
    return f"""
<section class="view-section" id="view-{anchor}">
  <h2><span class="kind-badge view-badge">view</span> {esc(v.name)}</h2>
  <table class="meta-table">{meta_html}</table>
  {doc_html}
  {diagram_html}
</section>
"""


def _render_member_tree(members: list, anchor_counter: dict[str, int], depth: int = 0) -> str:
    out = []
    for m in members:
        anchor = make_anchor(anchor_counter, m.name)
        kids = _render_member_tree(m.children, anchor_counter, depth + 1) if m.children else ""
        doc = f'<p class="member-doc">{esc(m.doc)}</p>' if m.doc else ""
        body = (
            f'<div class="member-head">'
            f'<span class="tree-icon">{_icon(m.kind)}</span>'
            f'<span class="kind-badge">{esc(_kind_label(m.kind))}</span>'
            f'<span class="member-name"><code>{esc(m.name)}</code></span>'
            f"<span class='tree-meta'>line {m.line}</span></div>{doc}"
        )
        if kids:
            out.append(
                f'<details class="member-node" id="member-{anchor}"><summary>{body}</summary>'
                f'<div class="member-children">{kids}</div></details>'
            )
        else:
            out.append(
                f'<div class="member-node" id="member-{anchor}">{body}</div>'
            )
    return "".join(out)


def render_file_page(
    mf: ModelFile,
    tree_html: str,
    prefix: str,
    repo_prefix: str,
    breadcrumbs: list[tuple[str, str]],
    source_url: str,
) -> str:
    anchor_counter: dict[str, int] = {}
    views_html = "".join(
        _render_view_block(v, mf, repo_prefix, anchor_counter) for v in mf.views
    )
    members_html = _render_member_tree(mf.members, anchor_counter)
    doc_html = f'<div class="doc-block"><p>{esc(mf.file_doc)}</p></div>' if mf.file_doc else ""
    view_count = len(mf.views)
    source_link = (
        f'<a class="source-link" href="{esc(source_url)}" target="_blank" rel="noopener">'
        "view source on GitHub</a>"
        if source_url
        else ""
    )
    content = f"""
<div class="card file-header">
  <h1>{esc(mf.rel_path)}</h1>
  <p class="muted">{view_count} view(s) · {len(mf.members)} declared member(s) {source_link}</p>
  {doc_html}
</div>
{views_html}
<div class="card">
  <h2>Members</h2>
  <p class="muted">Declared in this file; nested members expand inline.</p>
  <div class="member-list">{members_html}</div>
</div>
"""
    return _page_shell(
        f"{mf.rel_path}", tree_html, breadcrumbs, content, css_rel=prefix + "assets/viewer.css"
    )
