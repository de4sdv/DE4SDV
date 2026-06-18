# SysIDE Modeler view automation spike

## Purpose

Evaluate whether the two DE4SDV pilot views created manually in SysON can be
rendered automatically from SysML v2 textual view definitions using SysIDE
Modeler CLI.

The target workflow is:

```text
reviewed GitHub .sysml snapshot
  -> SysML v2 textual view definitions
  -> SysIDE Modeler CLI renders SVGs
  -> manifests record source snapshot, view definition, renderer, and outputs
  -> draft GitHub PR updates generated artifacts
```

This is different from the SysON spike. SysON tested human GUI layout and manual
SVG export. SysIDE Modeler should test whether we can avoid manual GUI layout by
making views explicit model artifacts.

## Source files

- Model slice: `textual-notation-of-model/snapshots/de4sdv-context-spike.sysml`
- View definitions:
  `textual-notation-of-model/views/syside-modeler/de4sdv-syside-views.sysml`

## Candidate render commands

Render all SysIDE view definitions:

```bash
syside viz view \
  textual-notation-of-model/snapshots/de4sdv-context-spike.sysml \
  textual-notation-of-model/views/syside-modeler/de4sdv-syside-views.sysml \
  --output-dir textual-notation-of-model/views/syside-modeler/generated
```

Render one named view:

```bash
syside viz view \
  textual-notation-of-model/snapshots/de4sdv-context-spike.sysml \
  textual-notation-of-model/views/syside-modeler/de4sdv-syside-views.sysml \
  --qualified-name "DE4SDV_SysideModelerViews::DE4SDVViewSet::systemContext" \
  --output-dir textual-notation-of-model/views/syside-modeler/generated
```

On this ARM64 host, the installed SysIDE binary is x86_64. A Docker amd64 wrapper
can execute the binary, but validation/rendering still requires a SysIDE license
available to the container:

```bash
docker run --rm --platform linux/amd64 \
  -e SYSIDE_LICENSE_KEY \
  -v /home/mrk/.local:/root/.local \
  -v /home/mrk/DE4SDV:/work \
  -w /work \
  debian:trixie-slim \
  /root/.local/syside viz view \
    textual-notation-of-model/snapshots/de4sdv-context-spike.sysml \
    textual-notation-of-model/views/syside-modeler/de4sdv-syside-views.sysml \
    --output-dir textual-notation-of-model/views/syside-modeler/generated
```

## Current finding

The SysIDE Modeler CLI is installed as `syside 0.10.0`, and its `viz view`
command is available. It supports headless generation of diagrams from textual
SysML v2 views into SVG, PNG, or JPEG.

After providing the SysIDE license through an ignored local `.syside.env` file,
validation and rendering succeeded through the amd64 Docker wrapper:

```text
Wrote /work/textual-notation-of-model/views/syside-modeler/generated/system-context.svg
Wrote /work/textual-notation-of-model/views/syside-modeler/generated/lifecycle-engineering-system.svg
```

The license file is intentionally local-only and must not be committed.

## Engineering workflow implication

SysIDE Modeler is probably a better fit than SysON for fully automated generated
views because the view definition can live in Git as SysML v2 text. The weak
point is not GUI automation; the weak point is connecting the authoritative live
model graph to the renderer.

Practical workflow candidate:

```text
GitHub reviewed .sysml + textual view definitions
  -> SysIDE Modeler CLI renders deterministic SVGs in CI/maintainer workflow
  -> GitHub PR carries generated SVGs and manifests
  -> optional privileged job imports/updates SysML v2 API repository
```

For a future live-API workflow:

```text
SysML v2 API repository commit
  -> export/serialize model snapshot
  -> SysIDE Modeler CLI renders textual views
  -> generated SVGs + snapshot metadata become a draft GitHub PR
```

Do not claim direct SysML v2 API-to-SysIDE live rendering until an API export or
Automator bridge is proven.

## Human-in-the-loop VS Code lane

SysIDE Modeler also supports a human-in-the-loop lane through its VS Code add-on:

```text
engineer edits .sysml model + view definitions in VS Code
  -> SysIDE Modeler visualizes the selected view
  -> engineer adjusts the textual view definition, not hidden diagram state
  -> Save As Image exports the inspected diagram when needed
  -> CLI re-renders the same textual view in automation
```

This is the preferred human workflow to test next. The human should not manually
recreate diagram semantics in an opaque GUI. The human should edit reviewable
SysML v2 view definitions and use the add-on as immediate visual feedback.

Spike protocol:

1. Open the DE4SDV workspace in VS Code with SysIDE Modeler installed.
2. Open `textual-notation-of-model/views/syside-modeler/de4sdv-syside-views.sysml`.
3. Use **Visualize view** on
   `DE4SDV_SysideModelerViews::DE4SDVViewSet::systemContext`.
4. Compare the add-on visualization with
   `textual-notation-of-model/views/syside-modeler/generated/system-context.svg`.
5. Adjust only textual view definitions or model relationships; do not rely on
   untracked manual layout state.
6. Re-run `syside viz view` and confirm the CLI output matches the view intent.

Acceptance criteria:

- The same textual view definition can be visualized in VS Code and rendered by
  CLI.
- Human changes are captured as `.sysml` diffs.
- Generated SVGs can be reproduced from Git plus the SysIDE license.
- Any manual VS Code "Save As Image" export is treated as review evidence, not
  the authoritative source.
