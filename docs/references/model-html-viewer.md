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
source location; clicking jumps to the element's declaration line in the
source view. The navigation
tree on the left is resizable (drag the divider; the width is remembered).
Below the diagrams, each file page shows the highlighted `.sysml` source
with numbered lines — reviewers check the ground truth directly next to
the rendered views, and tree entries for elements jump to their
declaration lines. Identifiers in the source that resolve to model
elements are references themselves: hovering an imported type shows its
kind, doc, and defining file, and clicking jumps to the definition — in
the same file or in the package that declares it. Diagrams can be expanded
full screen with the button in their toolbar (Esc returns).

## Comparing branches and pull requests

The viewer is not tied to one checkout. The generator can build several
revisions of the repository at once, and every page then carries a
**Revision** picker in the header to switch between them:

```bash
# working tree + main + the branches behind two open PRs
python -m tools.sysml_html_viewer.generate --repo . --out build/model-viewer \
    --refs main,feat/sysml-api-challenge-harness,spike/syside-modeler-view-automation

# or simply: every local branch
python -m tools.sysml_html_viewer.generate --repo . --out build/model-viewer \
    --refs auto
```

Each revision becomes a complete site under `refs/<name>/` (materialized
from git — nothing is checked out or modified), so the tree, diagrams,
tooltips, and source references all reflect that branch or PR. PR branches
that only exist on the remote resolve via `origin/<name>`, and when `gh`
can map a branch to an open pull request the picker labels it
(`PR #99: feat(...)`). Branches and PRs that were **not** built appear in
the picker as disabled entries whose tooltip shows the exact regenerate
command (`--refs <name>`), so the picker never silently hides a revision.
Reviewing a PR therefore needs no local checkout:
`gh pr checkout <number>` once, regenerate with `--refs`, and switch
between the working tree and the PR in the header.

## When to use

- Reviewing a feature or increment (middleware, AEBS): start at the
  feature's increment-framing file and click through its views.
- Orienting new contributors: the tree shows the whole validated model —
  `textual-notation-of-model` (packages, imported libraries such as
  `libraries/covesa-vss-sysmlv2`, snapshots) and the PLE product models.
- Linking to a specific element or view: every page and section has a
  stable URL (`.../mw_logical_architecture.sysml.html#view-mwSystemStructureView`).

## Regenerate after model changes

The viewer is a derived artifact. After any merged change that touches
`.sysml` files or the committed diagram SVGs, regenerate:

```bash
python -m tools.sysml_html_viewer.generate --repo . --out build/model-viewer
```

The generator is deterministic: regenerating at the same model head
produces byte-identical output. Output lives in `build/model-viewer`
(gitignored). Diagram SVGs are inlined from the model tree (working-tree
builds) or from the ref's git contents (ref builds) — it can never drift
from what the privileged validation workflow rendered.

## Serve

```bash
python -m http.server 8000
# open http://localhost:8000/build/model-viewer/
```

The site also works directly from `file://` (open `build/model-viewer/index.html`).

For review sessions where any branch or PR must be selectable, run the
viewer server instead:

```bash
python -m tools.sysml_html_viewer.serve --repo . --port 8787
# open http://127.0.0.1:8787/
```

The server upgrades the Revision picker to every branch and open PR of the
repository; picking one that is not built yet generates it on demand
(a few seconds, then cached) — no static regeneration needed between
reviews. It also regenerates the working-tree site automatically whenever
a `.sysml` file under the model roots changes, so editing the model and
refreshing the browser is the complete workflow.

## Publishing for collaborators

The published viewer shows committed content only (never a local working
tree). The recommended setup: GitHub Pages + the included deploy workflow
(`.github/workflows/deploy-viewer.yml`) behind a custom domain such as
`viewer.de4sdv.org`. On every push to `main` (plus weekly and manual
runs) the workflow checks out all branches and PR heads, generates the
site with `--public --refs auto` — root labeled with the plain branch
name, one sub-site per branch and open PR, PR labels from `gh` — runs the
repository gates, and deploys. Collaborators open the URL and pick any
revision from the header picker; everything is prebuilt, so no server is
involved. Domain setup: `CNAME viewer → de4sdv.github.io` in the DNS
zone, then set the custom domain in the Pages settings.

## Implementation

- Generator: `tools/sysml_html_viewer/` (stdlib only)
- Tests: `tests/test_sysml_html_viewer.py` (synthetic fixture, view-inventory
  parity with `scripts/generate_view_index.py`, link-resolution and
  determinism checks)
- Tool README: `tools/sysml_html_viewer/README.md`

The viewer parses the authoritative `.sysml` textual notation and links
the committed SysIDE diagram artifacts. It never invents model content and
never re-renders diagrams.
