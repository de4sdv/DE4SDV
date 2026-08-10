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
```

## Tests

```bash
python -m pytest tools/sysml_view_editor/tests/test_sysml_view_editor.py -v
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
