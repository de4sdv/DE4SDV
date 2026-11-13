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
`model-based-product-line-engineering/product-models`, the governed
product-line scope in `model-based-product-line-engineering/scoping`, and the
PLEML feature models and configurations in
`model-based-product-line-engineering/feature-models` and
`model-based-product-line-engineering/feature-configurations` (ADR 0022)
(stdlib only, deterministic output). Like the validation and the export, it
skips every `fixtures` directory of a root: the invalid configuration and the
parity probes under `feature-configurations/fixtures/` are not model files of
the viewer. The generated site is self-contained except that it
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

### Two assistant capabilities in one Ask window

In server mode the viewer offers **two separate** assistant capabilities.
They never fall back to each other and have separate endpoints, prompts,
and rate-limit budgets:

**DE4SDV Guide** (`POST /api/repo-chat`, `repo_guide.py`)

- Answers questions about the Git repository: docs, ADRs, tooling, the
  contribution workflow, product-line material.
- Grounded in the exact deployed Git checkout: a deterministic SQLite
  FTS5 index over README, `docs/`, ADRs, CONTRIBUTING, relevant
  `.sysml`/`.py`/YAML. Secrets, env files, VCS internals, build output,
  and generated assets are excluded.
- Not an engineering or model authority: generated answers that state
  what the repository does not cover, and a refusal when no trustworthy
  repository context matches. Never queries the Systems Modeling API.

**Ask the model** (`POST /ask`, `ask_model.py`)

- Answers questions about one specific model element the user
  right-clicked.
- Grounded in the element's declaration source, doc comment, children,
  and method-layer relations (semantic layer, server-side only).
- The element-grounded model capability; unchanged by DE4SDV Guide.

Both live in one chat window, **Ask**, at the bottom-right of every
viewer page. It is minimized by default. A switch in its header picks the
capability: **Model** (Ask the model) or **Repository** (DE4SDV Guide).
Each mode keeps its own conversation and sends only to its own endpoint;
a failed answer is reported in that mode and never retried in the other.
The window, the mode, the selected element and both conversations persist
while navigating the generated viewer (browser `localStorage` only — no
server-side user memory); "New chat" clears the conversation of the
current mode.

- **Model** answers about one element. Right-click a model element and
  choose **Ask the model… (element-grounded query)**: the window opens in
  Model mode with that element selected. Each answer names the element it
  was grounded on.
- **Repository** answers carry source references rendered as GitHub links
  pinned to the deployed application Git SHA, and the LLM receives only
  the question plus the retrieved repository context. **Ask the
  repository…** in the context menu opens this mode with a question about
  the element prefilled.

The API key stays server-side for both.

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
  other. The name search reads the text of each tree entry, so it also
  finds a short name (`REQ-MW-010`). Click a match (or press Enter to
  jump to the first one) to open it; **Esc** clears the name search, the
  **✕** button clears everything. No view switch, no separate results
  page.
- **Directory pages** (`pages/<model-dir>/index.html`) — contents of each
  model folder.
- **Tree nodes for files** — expanding a `.sysml` file lists its views and
  **every declared member** (ports and attributes nested in part
  definitions included), each jumping to its declaration line. Packages
  are structural containers and are not listed as members. A member with
  a short name shows it before its name, as the SysIDE diagrams do:
  `<REQ-MW-010> reqDeliverReferenceVehicleSpeed`. See "Declarations and
  their owners" below for what the scanner reads.
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
    packages. A name links to a declaration with the same name: in the
    same file first, then in the same folder or below it, else the first
    one found. In a qualified name `Q::name`, the declarations of name in
    the body of the declaration that `Q` links to come first. A
    declaration in a library package (`library package L`) is a target
    only in its own file and in a file that names `L` as a qualifier
    (`import L::*`, `L::x`); thus a common name such as `kind` in another
    file does not link to the library. A string (`"..."`) is text: a word
    in it is never a source reference. The tooltip of a source reference
    to an element with a short name shows the short name too. This is a
    navigation heuristic over the scanned declarations, not SysML v2 name
    resolution. Textual-notation **symbols** (`:`, `:>`, `:>>`, `::`)
    also carry hover tooltips explaining the construct (typing,
    specialization, feature specialization, qualified names). Tree
    entries for elements jump to the element's
    declaration line (`#src-N`);
  - *source link*: the exact `.sysml` file on GitHub (at the current
    branch, or at the ref for ref builds).

## Declarations and their owners

The scanner (`model_parse.py`) reads the `.sysml` text line by line. It is
a navigation heuristic, not a SysML v2 parser. A line declares a member
when it starts a statement with a declaration: prefix keywords (`abstract`,
`variant`, `in`, `ref`, ...), a kind (`part def`, `requirement`,
`connection def`, `assert constraint`, `binding`, ...), an optional short
name (`<'REQ-MW-010'>`) and a name. `library package` and
`standard library package` declare packages. A keyword is never a name:
`attribute redefines x = ...;` is an unnamed attribute, like
`attribute :>> x = ...;`. `flow of T from a to b;` is an unnamed flow:
the index lists it under its keyword, `flow`, as it lists `objective` and
`subject`. A line that continues a statement declares nothing: when
`binding b` has its `bind x = y;` on the next line, that line is part of
the binding b.

The owner of a member is the nearest member that owns one of the braces
open at its line. A brace in a comment, a string or a quoted name does not
count. A brace that belongs to a statement the scanner does not index
(`perform ... {`, `attribute :>> x = ... {`, `#feature occurrence ... {`)
is no owner: the members inside it get the nearest member around it, never
a member that comes before it. The index, the diagram hover data and the
Ask evidence (owner and children) use this owner. The index also has the
short name as a name of the element, so `REQ-MW-010` finds the
requirement.

The declaration forms that the scanner does not read yet: kindless
features (`in x : T;`, `out x : T;`, `end x : T;`), `#metadata`-prefixed
declarations (the feature models), `occurrence` and `occurrence def`, a
multiplicity right after the name (`part x[0..1]`), named constraints of
requirements (`require constraint statement { ... }`), and a declaration
that is not the first statement of its line.

## Diagram hover enrichment

Diagrams are inlined into the page (not `<img>`), and every element label
the diagram shows is resolved back to the model:

- **Hover** an element label — a tooltip shows its kind, its short name
  (if it has one), its `doc` comment, and its exact source location
  (file:line). A usage label (`name : Type`) whose own declaration has no
  `doc` shows the `doc` of its **type definition** instead — the
  documentation a reader wants when hovering a part/port usage. A
  qualified type (`Q::T`) finds the T that Q declares first. In a typing
  list (`: A, B`), the first type with a doc gives the doc. A doc comment
  placed right after a declaration's opening brace belongs to that
  declaration only; it never leaks onto the member that follows it.
- **Compartment rows** (`doc …`, `attributes`, `subject`, `actors`,
  `include use cases`) belong to the element whose box contains them: the
  title of the smallest box around the row (its topmost text that is not
  a stereotype line). A row in no box belongs to the title above it in the
  same column. A row whose title does not resolve shows nothing. Many rows
  have the same text, so the hover data has a row only under its position.
- **Click** a label — the viewer jumps to the element's declaration
  line (`#src-N`) in its defining file.
- Labels that are pure layout text (headers, "parts", stereotype labels)
  stay inert; a diagram element with no committed model match simply
  shows nothing.

The label → element mapping is generated from the authoritative `.sysml`
files, so the tooltip content can never say something the model does not
declare. Labels resolve across all the model roots the generator reads,
including
specializer (`:>`, `:>>`), typing (` : `), qualified (`A::b`), dotted
deployment (`host.role.port.item`), redefines (`^name`), short name
(`<REQ-MW-010> name`) and package-expose shapes. The library rule of the
source references applies to the labels too. Pure layout text and
stereotype markers stay inert. Run
`python scripts/audit_diagram_labels.py` to audit every diagram's
unresolved labels.

The navigation tree is **resizable**: drag the divider between tree and
content pane; the width is remembered per browser (localStorage, guarded
for `file://`). The divider sets the CSS variable `--tree-w`, and only the
two-column layout uses it. At 900 px and below the layout has one column,
so a remembered width cannot make a page wider than the screen.

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
  (max 1080 px). At 900 px and below the tree collapses above the content.
- **Fit** — no page and no box scrolls sideways, at all screen widths
  down to 320 px. A long source line wraps, and its wrapped part starts
  under its code, not under its line number. A long name wraps in the
  tree, in a heading and in a table cell: at a `<wbr>` word boundary where
  the page has one (the file path, the view name, the view metadata), else
  between two characters. The view metadata table has fixed columns. A
  code block in a guide page or in an Ask answer wraps too. A guide table
  breaks a word only at 900 px and below. On a phone (640 px and below)
  its rows stack, and each cell shows the name of its column
  (`data-label`) above its text. The one exception is the full-screen
  diagram: it shows the diagram at its native size, and you pan it in its
  box. A narrow-screen rule comes after its base rule (a test checks
  this): in the cascade, a narrow-screen rule before its base rule has no
  effect.
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
