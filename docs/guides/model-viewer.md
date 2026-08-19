# DE4SDV Model Viewer — how to use it

The DE4SDV model viewer is a read-only HTML viewer for the DE4SDV SysML v2
systems model. It follows the project-browser pattern of desktop modeling
tools: the model tree on the left, packages and their members with
documentation on the right, and every declared `view` with the diagram that
SysIDE renders from it.

It is a **viewer, not a modeler**. Nothing on these pages edits the model.
Diagrams are the committed `syside viz` artifacts (`diagram-*.svg` beside the
model files), so what you see is exactly what the privileged validation
workflow rendered — never a re-render.

## Run it

Local server mode (recommended for day-to-day use — includes auto-refresh and
on-demand branch builds):

```bash
python -m tools.sysml_html_viewer.serve --repo . --port 8787
# open http://127.0.0.1:8787/
```

Static build (no server, works from `file://`):

```bash
python -m tools.sysml_html_viewer.generate --repo . --out build/model-viewer
```

Published site: <https://viewer.de4sdv.org> (rebuilt from `main` and open pull
requests by the deploy workflow).

## Features

### Hover tooltips on elements

Rest the pointer on any model label — tree entry or diagram element. A tooltip
shows the element kind, its documentation, the source file and line, and a
link that jumps to the declaration in the highlighted source. Hovering a
compartment row (for example `attributes` or `doc …`) shows the tooltip of the
element whose compartment it renders.

### Hover tooltips on connections

In a diagram, hover the **connection line itself** (the polyline between two
ports). The tooltip names the connection or flow that the line renders, with
its kind, source location, and a link to the declaration. The label lying on
the connection wins over the endpoint labels, so you always learn what the
wire is, not just where it ends. This works for `connection`, `flow`, and
`bind` relationships.

### Go to definition

Click any tooltip link to jump to the declaration line in the highlighted
source view of the model file. In the source view, identifiers that resolve to
model elements are clickable links — hover them for a tooltip, click to jump.
Self-links on the declaration itself are omitted so the source stays quiet.

### Tree search and filters

The search box filters the model tree live by **names, kinds, and
documentation text** — type and the tree narrows to matching members, with
matches highlighted. The filter row beside the search narrows by **kind**
(part, port, requirement, view, … — only kinds actually used in the model are
listed), **SAF domain**, and **SAF aspect**. The ✕ button clears search and
filters.

### Revision picker (branches and pull requests)

Every page header has a **Revision** picker. It lists the working tree, `main`,
and any branches or open pull requests that were built. In server mode,
unbuilt revisions are built on demand when you select them (a progress overlay
shows while building). The picker is disabled (with the reason shown) for
revisions that were not built; published sites list all open PR heads.

### Fullscreen diagrams

Every diagram frame has a ⛶ button that expands the diagram to fill the
window. Press Esc or click ⛶ again to exit. Tooltips keep working in
fullscreen.

### Auto-refresh (server mode)

In server mode, editing a `.sysml` file (or the viewer's own code) and
refreshing the page shows the change immediately — the server rebuilds when it
detects newer files.

### Community chat

The **Chat** link in the header points to the DE4SDV Mattermost community
(<https://chat.de4sdv.org>).

## Static vs. server mode

A page served from a static build (including the published site) shows a note
when a revision is listed but not built: "served statically — run
`python -m tools.sysml_html_viewer.serve …`". Server mode is the only mode
that builds revisions on demand and watches for model changes.
