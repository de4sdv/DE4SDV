# ADR 0013: Diagram layout sidecars for the model viewer

## Status

Proposed

## Context

The committed SysIDE diagram SVGs are the model viewer's rendering
authority: what reviewers see is exactly what the privileged validation
workflow rendered, never a re-render. That contract keeps diagrams
trustworthy, but it also fixes the layout of every diagram. When a committed
render is correct semantically but hard to read — an overlapping label, a
box that should sit beside another, a connector crossing a compartment —
the only remedy today is another privileged render cycle.

Contributors and maintainers occasionally need a per-diagram arrangement
that is presentation-only: no model change, no re-render, reviewable, and
reversible.

## Decision

The local model viewer gains an opt-in **diagram layout editor**
(`--edit-layout` on the viewer server). It lets a maintainer move labels,
move and resize element boxes (their compartment separators, inner labels,
and port symbols follow proportionally), and move connection lines, then
save the result as a **layout sidecar**:

- Path: `<…>/diagrams/.de4sdv-diagrams/<diagram>.svg.layout.json` (beside
  the committed diagram's `diagrams/` directory, untracked by default).
- Content: an ordered list of layout-only ops (`text` move, `boxes`
  move/resize, `connectors` re-route, `lines`, `paths` restricted to
  parseable M/H/V(/A/Z) geometry, `svg` canvas size). Each op's find key is
  the raw committed geometry (same identity scheme as the viewer's hover
  JSON) plus the SHA-256 of the committed diagram it was created against.
- Rendering: the viewer applies the sidecar to the inlined SVG at
  generation/serve time. Committed SVGs are never modified.

Boundaries kept intact:

- The committed SysIDE artifacts remain the single rendering authority;
  `viewer.de4sdv.org` and every ref sub-site render committed content only.
- Sidecars cannot carry model content — validation is structural, and ops
  whose geometry no longer exists are skipped, never invented.
- Freshness fails closed: a sidecar whose base hash does not match the
  current diagram is reported stale and not applied.
- Ref sites and static builds stay read-only; the editor activates only on
  pages served by the local editor server.

## Consequences

Positive:

- Presentation fixes no longer require a privileged render cycle or a model
  edit; the semantic contract of the viewer is unchanged.
- Layouts are plain JSON, diffable and reviewable in pull requests like any
  other change, and reversible by deleting the file.

Negative / follow-up:

- The sidecar is a new artifact class contributors must understand; the user
  guide (`docs/guides/diagram-layout-editor.md`) and the editor's own status
  line carry that explanation.
- Ops are geometry-keyed, so a re-render that moves an element invalidates
  the matching ops (fail-closed notice instead of silent drift). Re-saving
  after a re-render is manual work.
- Proportional companion moving keeps compositions recognizable but is a
  heuristic; precisely re-placing a resized box's interior may need a
  follow-up drag.

## Non-decisions

- Whether the committed diagram workflow itself should change (it should
  not).
- Whether layout becomes part of the SysML model or the API baseline (it
  stays viewer-side presentation state).
- Any public/published editing surface (explicitly excluded).

## Links

- User guide: `docs/guides/diagram-layout-editor.md`
- Viewer tool: `tools/sysml_html_viewer/` (`layout_sidecar.py`,
  `layout_apply.py`, `editor_layout.js`, `serve.py --edit-layout`)
- Tests: `tests/test_diagram_layout_editor.py`
- ADR 0005 (SysML v2 API repository as live model store) and ADR 0012
  (revision-bound semantic reads) define the semantic authority this editor
  deliberately does not touch.
