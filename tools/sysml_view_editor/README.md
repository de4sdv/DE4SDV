# DE4SDV SysML v2 View Editor

Deterministic rendering of DE4SDV SysML v2 views from the authoritative
textual model. The tool draws exactly what the Git-tracked SysML declares —
no semantic content is invented by the renderer.

## Architecture

```text
Git-tracked *.sysml  (semantic authority)
        │  parse (regex, comment-stripped)
        ▼
semantic graph  (roles, ports, flows, payloads)
        │  + layout sidecar (presentation only)
        ▼
SVG render  (derived artifact)
```

- **Semantics come only from the `.sysml` source.** The graph contains no
  presentation state.
- **The layout sidecar stores only presentation** (positions, sizes, routing).
  It never stores roles, ports, flows, or payloads. Unknown schema versions
  are rejected, never silently migrated.
- **Stable qualified IDs** (`vmA.cuttlefishGuest.structuredLogcatOut`) key the
  sidecar, so renames and deletions produce explicit orphan warnings instead
  of silently corrupting layout.
- **Source docs surface in the view.** `doc /* ... */` comments in the SysML
  source attach to roles (part defs), ports (port defs), flows (preceding
  comment), and the deployment. Documented roles show a **doc compartment**
  inside the box (wrapped, capped, shown in both the SVG render and the
  interactive editor); every element also carries a `<title>` tooltip, and
  the interactive editor shows the full doc in a details panel on click.
  Docs never enter the layout sidecar and never change the semantic hash —
  they are explanatory model content, not presentation.
- **Parity gate** compares the extracted graph against a hand-authored
  expectation before any render is trusted.

## Commands

```bash
# Extract the deterministic semantic graph as JSON
python -m tools.sysml_view_editor graph --model path/to/model.sysml

# Render the view to SVG (creates an empty layout sidecar on first run)
python -m tools.sysml_view_editor render \
  --model path/to/model.sysml \
  --output out.svg \
  --layout out.layout.json

# Run the parity gate against a hand-authored expectation
python -m tools.sysml_view_editor check \
  --model path/to/model.sysml \
  --expectation tools/sysml_view_editor/tests/fixtures/expectation.json

# Start the presentation-only interactive editor
python -m tools.sysml_view_editor serve \
  --model path/to/model.sysml \
  --layout out.layout.json \
  --port 8123

# Select a different declared view usage (its expose sources the diagram)
python -m tools.sysml_view_editor render \
  --model path/to/model.sysml \
  --view mwVehicleSpeedCampaignStructureView \
  --output out.svg
```

Open `http://127.0.0.1:8123`. Drag a role box to move it; drag its blue
bottom-right handle to resize it. Ports, typed flows, and labels are derived
from the current role rectangles and remain connected throughout the gesture.
`Save layout` writes only presentation state to the sidecar.

## View-driven sourcing

Diagrams are sourced from the **declared view usage**, per the SysML v2 spec
("a diagram is also a view usage"): the view's `expose` targets resolve to the
deployment part def whose parts and flows become the graph. The header shows
the view's viewpoint, framed concern, and render hint, so a reviewer sees what
sourced the diagram. The deployment name is a fallback only:

- `view` — the view's expose resolved to a deployment part usage (preferred).
- `explicit` — a `--deployment`/kwarg override was given.
- `default` — no resolvable view block (legacy model), or the view exposes
  types this flow-graph renderer cannot project (e.g. item/port-only views).
  In the latter case the unresolved exposes are surfaced as a warning rather
  than silently drawing the default content.

## Tests

```bash
python -m pytest tools/sysml_view_editor/tests/test_sysml_view_editor.py -v
```

The browser interaction regression requires a live editor and Chromium with a
DevTools port. It verifies connected drag, connected resize, and save/reload:

```bash
chromium --remote-debugging-port=9223 http://127.0.0.1:8123
node tools/sysml_view_editor/tests/browser_interaction_check.mjs --port 9223
```

## Design notes

- Endpoint paths in the DE4SDV model are mixed-shape:
  - `vmA.cuttlefishGuest.structuredLogcatOut.envelope` — host.role.port.payload
  - `privateTcpBoundary.vmAIn.envelope` — role.port.payload (boundary is itself
    a role)
  The graph resolver handles both forms; do not assume four segments.
- The fixture mirrors the DE4SDV middleware topology: five roles, eight ports,
  four directed typed flows. The parity expectation is hand-authored and is
  the contract for the render.
- Regex parsing extracts structural relationships; it is not a SysML v2
  semantic validator (use licensed SysIDE for validation).
