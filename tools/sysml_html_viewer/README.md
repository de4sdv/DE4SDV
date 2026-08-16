# DE4SDV static HTML model viewer

A read-only HTML viewer for the DE4SDV SysML v2 systems model — the
"project browser" pattern used by desktop modeling tools, made static:
click through the model tree on the left; the right pane shows packages,
declared members with their documentation, and every declared `view` with
the diagram SysIDE renders from it.

This is a **viewer, not a modeler**: nothing on these pages edits the
model, changes a view, or writes a layout sidecar. Diagrams are the
committed SysIDE artifacts (`diagram-*.svg` beside the model files), so
what reviewers see is exactly what the privileged validation workflow
rendered — never a re-render.

## Generate

```bash
python -m tools.sysml_html_viewer.generate --repo . --out build/model-viewer
```

The generator parses the authoritative `.sysml` textual notation under
`textual-notation-of-model/packages` (stdlib only, deterministic output).
The generated site is self-contained except that it *references* the
committed diagram SVGs in the model tree — no SVG copies, so it can never
drift from the rendered artifacts.

## View

Serve from the repository root (any static server works, including
`file://`):

```bash
python -m http.server 8000   # then open http://localhost:8000/build/model-viewer/
```

Or open `build/model-viewer/index.html` directly in a browser.

## What is on a page

- **Index** — model stats and the full navigation tree.
- **Directory pages** (`pages/<model-dir>/index.html`) — contents of each
  model folder.
- **File pages** (`pages/<model-file>.html`) — one per `.sysml` file:
  - *view sections*: view name, viewpoint, concern, expose targets,
    depth, render kind, source line — and the SysIDE diagram (or an
    explicit "no committed diagram" note when the artifact is missing);
  - *source*: the full `.sysml` file below the diagrams, syntax
    highlighted with numbered lines. Tree entries for elements and
    tooltip "open in viewer" links jump to the element's declaration
    line (`#src-N`);
  - *source link*: the exact `.sysml` file on GitHub.

## Diagram hover enrichment

Diagrams are inlined into the page (not `<img>`), and every element label
the diagram shows is resolved back to the model:

- **Hover** an element label — a tooltip shows its kind, its `doc`
  comment, and its exact source location (file:line).
- **Click** a label — the viewer jumps to that member's section.
- Labels that are pure layout text (headers, "parts", stereotype labels)
  stay inert; a diagram element with no committed model match simply
  shows nothing.

The label → element mapping is generated from the authoritative `.sysml`
files, so the tooltip content can never say something the model does not
declare. Labels resolve across both model roots (`textual-notation-of-model/packages`
and `model-based-product-line-engineering/product-models`), including
specializer (`:>`, `:>>`), typing (` : `), qualified (`A::b`), dotted
deployment (`host.role.port.item`), redefines (`^name`) and package-expose
shapes. Pure layout text and stereotype markers stay inert. Run
`python scripts/audit_diagram_labels.py` to audit every diagram's
unresolved labels.

The navigation tree is **resizable**: drag the divider between tree and
content pane; the width is remembered per browser (localStorage, guarded
for `file://`).

## Design rules

1. Semantics come only from `.sysml` — the viewer never invents elements,
   ports, flows, or diagrams.
2. Diagrams are linked, not copied or re-rendered.
3. Output is deterministic: regenerating at the same model head produces
   byte-identical pages.
4. View parsing mirrors `scripts/generate_view_index.py`; a parity test
   (`tests/test_sysml_html_viewer.py`) keeps the two inventories in
   agreement, including typed views (`view X : MVD::MatrixView`).

## Tests

```bash
python -m pytest tests/test_sysml_html_viewer.py -q
```

Tests run against the synthetic fixture in
`tests/fixtures/sysml_viewer_model` (original test data — not a copy of
any real model file).
