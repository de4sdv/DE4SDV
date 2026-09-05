# DE4SDV Model Viewer — how to use it

The DE4SDV model viewer is a read-only HTML viewer for the DE4SDV SysML v2
systems model. It follows the project-browser pattern of desktop modeling
tools: the model tree on the left, packages and their members with
documentation on the right, and every declared `view` with the diagram that
SysIDE renders from it.

It is a **viewer, not a modeler**. Nothing on these pages edits the model.
Diagrams are the committed `syside viz` artifacts gathered in each first-level
model area's `diagrams/` folder, so what you see is exactly what the privileged
validation workflow rendered — never a re-render.

## Diagram provenance

Every diagram in this viewer is a **committed artifact**, not a live render: it
was produced with [SysIDE](https://docs.sensmetry.com/editor/) (`syside viz`) by
the privileged validation workflow and committed to the repository beside the
model sources in each area's `diagrams/` folder. The viewer embeds exactly those
files — it never re-renders or invents a diagram.

To render or refresh diagrams yourself, install the SysIDE Editor extension for
VS Code — setup and the visualization commands are in the
[official SysIDE documentation](https://docs.sensmetry.com/editor/) — open the
package that declares the view, run the visualization command on it, and
contribute the updated SVG through a pull request.

## The live website

The public reader experience is
**[viewer.de4sdv.org](https://viewer.de4sdv.org)**. It serves one reviewed
current revision and its bounded Ask-model capability. Right-click a model
element and choose **Ask the model** to ask a question grounded in the
deployed model. The answer is generated, not model authority: follow its
element/source links and verify important conclusions against the model.

The prebuilt branch and pull-request viewer remains available at the
[native GitHub Pages URL](https://de4sdv.github.io/DE4SDV/) as a browse-only
engineering mirror. It does not execute Ask-model requests.

## Repository diagram collections

Each first-level model area that declares concrete views has a generated
`VIEWS.md` landing page. It lists every view, explains the reviewer question in
one sentence, records the source/viewpoint/concern/exposure metadata, and embeds
the committed SVG when the render passed publication QA:

- [architecture](../../textual-notation-of-model/packages/architecture/VIEWS.md)
- [AEBS](../../textual-notation-of-model/packages/features/aebs/VIEWS.md)
- [middleware](../../textual-notation-of-model/packages/features/middleware/VIEWS.md)
- [DE4SDV method](../../textual-notation-of-model/packages/methods/de4sdv/VIEWS.md)
- [product models](../../model-based-product-line-engineering/product-models/VIEWS.md)

The landing page keeps a visible status entry when a diagram is withheld. Empty
view frames, exposure-only renders, and empty table/matrix frames are not
published as if they were usable diagrams. Dense or degraded-but-informative
renders stay available with a presentation note and should be opened at full
size.

## Run it locally (your own work)

Localhost serves **your own working tree and unmerged branches** — use it for
your own work and direct feedback before anything is published:

```bash
python -m tools.sysml_html_viewer.serve --repo . --port 8787
# open http://127.0.0.1:8787/
```

Server mode includes auto-refresh and on-demand builds of any branch or pull
request you select.

Static build (no server, works from `file://`):

```bash
python -m tools.sysml_html_viewer.generate --repo . --out build/model-viewer
```

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

A page served from a static build (including the native Pages mirror) shows a note
when a revision is listed but not built: "served statically — run
`python -m tools.sysml_html_viewer.serve …`". Server mode is the only mode
that builds revisions on demand and watches for model changes. The public
interactive service is intentionally pinned to one reviewed application
revision and one validated model revision; it does not expose arbitrary branch
or pull-request builds.
