# Static HTML model viewer

The DE4SDV systems model is browsable as a static, read-only HTML site —
the same click-through experience as a desktop modeling tool's project
browser, without any modeling tool or license: packages on the left,
elements and rendered views on the right.

Purpose: make the model understandable to humans and reviewers. A reviewer
opens the viewer, expands the feature tree, clicks a view, and sees the
SysIDE-rendered diagram with its viewpoint, concern, expose targets, and
source location — no tool installation, no model checkout required.
Diagram element labels are hover-enriched: resting the pointer on an
element in the diagram shows its kind, its `doc` comment, and its exact
source location; clicking jumps to the member's section.

## When to use

- Reviewing a feature or increment (middleware, AEBS): start at the
  feature's increment-framing file and click through its views.
- Orienting new contributors: the tree shows the whole
  `textual-notation-of-model/packages` structure.
- Linking to a specific element or view: every page and section has a
  stable URL (`.../mw_conceptual_architecture.sysml.html#view-mwSystemStructureView`).

## Regenerate after model changes

The viewer is a derived artifact. After any merged change that touches
`.sysml` files or the committed diagram SVGs, regenerate:

```bash
python -m tools.sysml_html_viewer.generate --repo . --out build/model-viewer
```

The generator is deterministic: regenerating at the same model head
produces byte-identical output. Output lives in `build/model-viewer`
(gitignored) and references the committed SVGs in place — it can never
drift from what the privileged validation workflow rendered.

## Serve

```bash
python -m http.server 8000
# open http://localhost:8000/build/model-viewer/
```

The site also works directly from `file://` (open `build/model-viewer/index.html`).

## Implementation

- Generator: `tools/sysml_html_viewer/` (stdlib only)
- Tests: `tests/test_sysml_html_viewer.py` (synthetic fixture, view-inventory
  parity with `scripts/generate_view_index.py`, link-resolution and
  determinism checks)
- Tool README: `tools/sysml_html_viewer/README.md`

The viewer parses the authoritative `.sysml` textual notation and links
the committed SysIDE diagram artifacts. It never invents model content and
never re-renders diagrams.
