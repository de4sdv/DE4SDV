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
the same roots `scripts/validate_sysml.py` validates — the whole
`textual-notation-of-model` tree (packages, imported libraries such as
`libraries/covesa-vss-sysmlv2`, snapshots) plus
`model-based-product-line-engineering/product-models` (stdlib only,
deterministic output). The generated site is self-contained except that it
*references* the committed diagram SVGs in the model tree — no SVG copies,
so it can never drift from the rendered artifacts.

Every build also emits `help.html` at the site root, rendered from
[`docs/guides/model-viewer.md`](../../docs/guides/model-viewer.md) (the same
guide is linked as **Help** in the page header and published on
viewer.de4sdv.org). It also emits `elements.html` from
[`docs/guides/sysml-elements.md`](../../docs/guides/sysml-elements.md)
(linked as **Elements** in the page header): the high-level guide to the
SysML v2 element kinds used across the model and why DE4SDV uses them.

### Multiple revisions (branch / PR selector)

By default the working tree is built, plus `main` (or `origin/main`) when
the repository has it. Build extra revisions with `--refs`:

```bash
# a few refs (branches, tags, refs/pull/N/head)
python -m tools.sysml_html_viewer.generate --repo . --out build/model-viewer \
    --refs main,feat/model-html-viewer

# every local branch
python -m tools.sysml_html_viewer.generate --repo . --out build/model-viewer \
    --refs auto
```

Each ref is materialized from git (`git archive`, nothing is checked out or
modified) and becomes a complete site under `refs/<name>/`. Every page's
header then carries a **Revision** picker to switch between the working
tree and the built refs — pure relative links, so it works from `file://`.
Refs that exist only on the remote (`origin/<name>`) resolve automatically,
which covers PR branches that were never checked out. When the `gh` CLI can
map a branch to an open pull request, the picker labels it
(`PR #99: feat(...)`); use `--no-prs` to disable.

Revisions that are **not built** are still listed in the picker, disabled,
with a hint in their tooltip: `regenerate with: --refs <name> (or --refs
auto)` — the picker never silently hides a branch or PR. Refs without any
`.sysml` under the model roots are skipped at generation with a warning
(e.g. PRs that only touch docs or tooling), and the same disabled-entry
mechanism makes that visible in the UI.

`gh pr checkout <number>` is the easiest way to add a PR to the picker: the
branch becomes a local branch, and the next generation labels it with its
PR number and title.

## View

Serve from the repository root (any static server works, including
`file://`):

```bash
python -m http.server 8000   # then open http://localhost:8000/build/model-viewer/
```

Or open `build/model-viewer/index.html` directly in a browser.

### Server mode: every branch and PR clickable

```bash
python -m tools.sysml_html_viewer.serve --repo . --port 8787
# then open http://127.0.0.1:8787/
```

The server serves the generated site and upgrades the Revision picker to
the **full** list of revisions — every local branch and every open PR
(labeled `PR #N: title`). Clicking a ref that was not built at generation
time materializes it from git and generates its site **on demand** (a few
seconds on the first click), then caches it in the same `refs/<name>/`
layout. Refs without `.sysml` under the validated model roots stay disabled
with a hint. Static builds (`file://` or a plain static host) keep the
static picker — the dynamic upgrade only activates when the page is served
by this server.

The server also watches the model: if any `.sysml` under the validated
roots is newer than the generated working-tree site, the next page request
regenerates it first. Editing the model and refreshing the browser is the
whole loop — no manual regeneration needed.

Switching to a revision that is not built yet shows a progress overlay
("Building revision …") while the server generates it; already-built
revisions switch instantly.

## Publishing for collaborators

The published site shows **committed content only** — no local working
tree. The recommended setup is GitHub Pages + a deploy workflow, behind a
custom domain:

1. **Deploy workflow** (`.github/workflows/deploy-viewer.yml`, included):
   on every push to `main`, weekly, and manually (`workflow_dispatch`), it
   checks out all branches and PR heads, runs the generator with
   `--public --refs auto` (root site labeled with the plain branch name,
   one sub-site per branch/PR head, PR labels from `gh`), runs the
   repository gates, and deploys to Pages.
2. **Domain** (optional but recommended): add a `CNAME` in the DNS zone
   (e.g. `viewer` → `de4sdv.github.io`), then set the custom domain in the
   repository's Pages settings. Cloudflare DNS works fine (DNS-only, or
   proxy with SSL mode Full).
3. **What collaborators get**: the full viewer — tree, diagrams, hover
   tooltips, source go-to-definition — plus a Revision picker listing
   every branch and every open PR, all prebuilt and instantly clickable.
   No server, no clone needed.

Local use is unchanged: `python -m tools.sysml_html_viewer.serve` keeps
the on-demand experience including your uncommitted working tree — the
one thing a published snapshot intentionally never shows.

## What is on a page

- **Index** — model stats and the full navigation tree.
- **Search & filters (in the tree)** — a search box at the top of the
  model tree on every page. Results appear live as you type (no Enter):
  the tree itself filters in place — matching elements stay in their
  place with the matched text highlighted, their ancestors remain
  visible, and everything else collapses away. Below the box, four
  dropdowns filter the tree by **SysML v2 keyword** (every declaration
  keyword used in the model: view, viewpoint, part def, requirement,
  verification, use case, …), **SAF domain** and **SAF aspect** (parsed
  from the viewpoint definitions' doc comments in the model), and
  **viewpoint**. Filters combine with the name search and with each
  other. Click a match (or press Enter to jump to the first one) to open
  it; **Esc** clears the name search, the **✕** button clears
  everything. No view switch, no separate results page.
- **Directory pages** (`pages/<model-dir>/index.html`) — contents of each
  model folder.
- **Tree nodes for files** — expanding a `.sysml` file lists its views and
  **every declared member** (ports and attributes nested in part
  definitions included), each jumping to its declaration line. Packages
  are structural containers and are not listed as members.
- **File pages** (`pages/<model-file>.html`) — one per `.sysml` file:
  - *view sections*: view name, viewpoint, concern, expose targets,
    depth, render kind, source line — and the SysIDE diagram (or an
    explicit "no committed diagram" note when the artifact is missing).
    Each diagram has a **fullscreen button** (`⛶`) in its toolbar:
    the diagram fills the screen, Esc or `✕ Close` returns;
  - *source*: the full `.sysml` file below the diagrams, syntax
    highlighted with numbered lines. Identifiers that resolve to model
    elements are **source references** (dotted underline): hover shows
    the element's kind, doc, and declaration location; click jumps to
    the definition — same file (`#src-N`) or the defining file
    (`pages/<file>.html#src-N`) for members imported from other
    packages. Textual-notation **symbols** (`:`, `:>`, `:>>`, `::`)
    also carry hover tooltips explaining the construct (typing,
    specialization, feature specialization, qualified names). Tree
    entries for elements jump to the element's
    declaration line (`#src-N`);
  - *source link*: the exact `.sysml` file on GitHub (at the current
    branch, or at the ref for ref builds).

## Diagram hover enrichment

Diagrams are inlined into the page (not `<img>`), and every element label
the diagram shows is resolved back to the model:

- **Hover** an element label — a tooltip shows its kind, its `doc`
  comment, and its exact source location (file:line). A usage label
  (`name : Type`) whose own declaration has no `doc` shows the `doc`
  of its **type definition** instead — the documentation a reader
  wants when hovering a part/port usage. A doc comment placed right
  after a declaration's opening brace belongs to that declaration
  only; it never leaks onto the member that follows it.
- **Click** a label — the viewer jumps to the element's declaration
  line (`#src-N`) in its defining file.
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

## Design package

A deliberately minimal visual design; everything lives in `viewer.css`
as tokens under `:root`.

- **Layout** — the project browser (model tree) is a full-height sidebar
  pinned to the outermost left edge of every screen, below a sticky
  header; content is centered at a comfortable reading width
  (max 1080 px). Below 900 px the tree collapses above the content.
- **Color** — four neutrals plus one accent, all in `:root`:
  `--bg #f4f6f9`, `--panel #ffffff`, `--ink #1f2933`,
  `--muted #6b7a8a`, `--line #e2e8f0`, `--accent #1a56db`
  (with `--accent-soft #eaf1fe` for hovers/focus).
- **Type** — **IBM Plex Sans** for documentation and UI (header brand,
  body, tree, filters, tables), **IBM Plex Mono** for code, identifiers,
  commands, and SysML snippets (the source view, inline `code`, kind
  badges). Both load from Google Fonts (OFL) with system-stack
  fallbacks; the header height is measured at runtime, so the sidebar
  geometry stays exact.
- **Shape** — flat surfaces, hairline borders (`--line`), small radii
  (8 px cards), no shadows.

### Carbon theme layer (`carbon.css` + `theme.js`)

On top of the base design, the viewer ships a **Carbon Design System theme
layer** (loaded after `viewer.css` on every page):

- **Light theme** (default) follows Carbon white/gray tokens: gray-100
  `#161616` text on white/gray-10 `#f4f4f4` surfaces, blue-60 `#0f62fe`
  interactive accent, gray-20 `#e0e0e0` borders, 0 px corner radius
  everywhere, and Carbon component idioms (tags for kind badges and
  requirement kinds, underline-style selects, square filter chips, 2 px
  focus rings).
- **Dark theme** (Carbon g100) activates via `<html data-theme="dark">`:
  gray-100 background, gray-90 panels, light text, blue-40 `#4589ff`
  interactive accent, dark-tuned syntax and tag colors.
- **Theme toggle**: the header sun/moon button switches themes; the choice
  persists in `localStorage`. A small inline `<head>` script re-applies the
  saved theme before first paint (no flash), and `?theme=dark|light` acts as
  a per-view URL override that does not overwrite the saved choice.
- Both theme token sets live in `carbon.css`; `theme.js` only wires the
  toggle button and the body-level theme class.

## Tests

```bash
python -m pytest tests/test_sysml_html_viewer.py -q
```

Tests run against the synthetic fixture in
`tests/fixtures/sysml_viewer_model` (original test data — not a copy of
any real model file).
