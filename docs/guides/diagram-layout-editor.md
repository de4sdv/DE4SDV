# DE4SDV Diagram Layout Editor — how to use it

The layout editor lets you **arrange the diagrams you publish**: move labels,
move and resize element boxes (their compartments follow), and move
connection lines. It is built into the local model viewer and activated with
one flag.

## What it is — and what it is not

- The committed SysIDE diagram SVGs stay the **single rendering authority**.
  The editor never touches the model, the committed SVGs, or anything the
  `syside viz` workflow produced.
- Your arrangement is saved as a **layout sidecar** — a small JSON file next
  to the diagram under `<…>/diagrams/.de4sdv-diagrams/<diagram>.svg.layout.json`.
  At render time the viewer applies the sidecar to the committed diagram on
  the fly. Delete the file (or press *Reset saved*) and the committed
  diagram renders unchanged.
- The sidecar stores only geometry: which element moved where, which box got
  which size. It cannot change text, add or remove elements, or carry any
  model content. A layout sidecar is reviewable in a pull request like any
  other change.

## Run it

```bash
python -m tools.sysml_html_viewer.serve --repo . --port 8787 --edit-layout
```

Open <http://127.0.0.1:8787> and navigate to any view with a committed
diagram. The diagram toolbar gains an **Edit layout** button. (Without
`--edit-layout` nothing changes — the viewer stays exactly as before.)

The editor is **local-server only**: it edits the working tree's layouts.
Ref sub-sites (branches, PRs) and the published viewer.de4sdv.org stay
read-only.

## Edit

Press **Edit layout** on a diagram:

- **Drag a label** to move it.
- **Drag a box body** to move it; **drag an edge** to resize. Its
  compartment separators, inner labels, and port symbols move along,
  proportionally, so a resized box keeps its composition.
- **Drag a line** (separator or connector) to move the whole route.
- Drag empty canvas to pan; **Ctrl+wheel** zooms; the **snap** checkbox
  rounds to a 2px grid; **Ctrl/Cmd+Z** undoes.
- **Save layout** writes the sidecar and reloads the page with the layout
  applied. **Reset saved** deletes the sidecar (the committed diagram
  returns). **Close** discards unsaved changes.

## Reviewing and sharing

The sidecar is an untracked file under your working tree. To propose a
layout:

1. Edit and save.
2. `git add -f <diagrams>/.de4sdv-diagrams/<diagram>.svg.layout.json`
   (the directory is gitignored — layout is local state by default)
3. Commit on a branch and open a PR as usual.

Reviewers see the sidecar diff itself: each entry names the element (by its
committed geometry) and the new geometry. After merge, everyone who runs
the local viewer with `--edit-layout` gets the arrangement from the
committed sidecar.

## Freshness rules (fail closed)

Every sidecar records the hash of the committed diagram it was made against.

- If the diagram is re-rendered by `syside viz` (new geometry), the sidecar
  is **stale**: the page shows a notice and renders the committed diagram
  unchanged. Nothing half-applies.
- If only some saved moves reference geometry that still exists (same
  diagram, different elements moved), the appliable subset is applied and a
  notice says how many ops were skipped.

The status line in the editor counts unsaved changes; the page shows a note
when saved ops could not be applied.
