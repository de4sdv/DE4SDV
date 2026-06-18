# SysON engineering workflow for DE4SDV

This note defines the next practical workflow for including Eclipse SysON in the
DE4SDV SysML v2 engineering loop.

## Decision

Use SysON as the GUI pilot for collaborative graphical SysML v2 modeling.

Keep the existing split from ADR 0005:

- SysML v2 API repository: authoritative live model graph target.
- GitHub: authoritative reviewed publication baseline.
- SysON: GUI authoring/viewing pilot and graphical view source.
- SysIDE Editor/Modeler: textual authoring and validation path where available.

## Current upstream facts

The SysON v2026.5.0 documentation and source indicate:

- SysON is open-source and web-based.
- SysON is under active development and not yet intended for production use.
- SysON's standard SysML v2 REST API is not fully available yet.
- SysON supports GraphQL through Sirius Web.
- SysON supports project/model upload and download using a SysON-specific JSON
  exchange format.
- SysON explicitly warns that this JSON exchange format is not the SysML v2
  standard JSON format.
- SysON supports textual `.sysml` import/export as an exchange path, but some
  concepts are still under development.
- SysON can export diagrams as SVG through the diagram toolbar. PNG export is
  also mentioned in current release notes.

Consequence: SysON should not yet be treated as a direct replacement for the OMG
SysML v2 API Services repository. The GraphQL/Sirius API is a SysON-specific
automation surface used only because SysON's standard SysML v2 REST API
round-trip is not ready enough for the DE4SDV workflow.

The bridge for DE4SDV should initially be file/GraphQL based:

```text
GitHub reviewed .sysml snapshot
  -> SysON textual import
  -> GUI edits and view layout
  -> SysON textual export + diagram SVG export
  -> generated GitHub draft PR
  -> review/validation/merge
  -> import/update live SysML v2 API repository when the exported model is accepted
```

This is not automatic live synchronization. A change made inside SysON is pilot
state until it is exported, validated, committed through a GitHub pull request,
and then imported/synced into the live SysML v2 API repository.

## Local pilot stack

Use the compose file in [`../tools/syson/`](../tools/syson/):

```bash
# x86_64
docker compose -f tools/syson/compose.yaml up -d

# ARM/aarch64
DOCKER_DEFAULT_PLATFORM=linux/amd64 \
  docker compose -f tools/syson/compose.yaml up -d
```

Open:

```text
http://localhost:8080
```

## Import path: GitHub to SysON

1. Start SysON.
2. Create a SysON project named `DE4SDV`.
3. Import the reviewed textual snapshot from GitHub as a `.sysml` document.
4. Prefer read-only import for baseline/library snapshots.
5. Create a writable working model only for the slice being edited.

Script helper:

```bash
python scripts/syson_exchange.py --url http://localhost:8080 list-projects

python scripts/syson_exchange.py \
  --url http://localhost:8080 \
  import-document <syson-project-id> textual-notation-of-model/snapshots/de4sdv.sysml
```

For the current MVP, `textual-notation-of-model/snapshots/de4sdv.sysml` does not
exist yet. Until a normalized textual exporter is implemented, use the smallest
validated `.sysml` slice available for the SysON import spike.

## GUI edit path inside SysON

For the first two DE4SDV views:

- `system-context`
- `lifecycle-engineering-system`

Use SysON General View first. It is the broadest available view and can display
packages, definitions, usages, annotations, and selected relationships.

Rules:

- Keep view names aligned with the Git-tracked `view.yaml` IDs.
- Do not manually edit generated SVG files in Git.
- If SysON creates view/project identifiers, record them in the corresponding
  `manifest.json` once discovered.
- Treat SysON layout as pilot state until deterministic export is proven.

## Export path: SysON to GitHub

After a SysON editing session:

1. Export/download the `.sysml` document from SysON.
2. Export each pilot diagram as SVG from the diagram toolbar.
3. Replace the Git-tracked generated assets:
   - `textual-notation-of-model/views/system-context/system-context.svg`
   - `textual-notation-of-model/views/lifecycle-engineering-system/lifecycle-engineering-system.svg`
4. Update each `manifest.json` with:
   - SysON project ID
   - SysON document ID
   - SysON representation/diagram ID, if available
   - export timestamp
   - source tool/version
5. Run validation.
6. Open a draft PR.

Script helper for textual download once document IDs are known:

```bash
python scripts/syson_exchange.py \
  --url http://localhost:8080 \
  download-document <syson-project-id> <document-id> textual-notation-of-model/snapshots/de4sdv.sysml
```

Diagram SVG export is currently documented as a UI operation. A scripted diagram
export remains an explicit spike item.

## Required next spike

Create one SysON pilot project and answer these with evidence:

1. Can a DE4SDV `.sysml` slice be imported without unresolved relationships?
2. What project/document IDs does SysON expose through GraphQL?
3. Can a General View be created for `DE4SDV::Context`?
4. Can the System 1-2-3 packages/elements be arranged into a usable
   `system-context` view?
5. Can the view be exported as SVG and committed in the expected Git path?
6. Can the edited model be exported back as `.sysml` and pass available
   validation?
7. Is there a GraphQL/Sirius endpoint that can script diagram export, or is UI
   export the only reliable path for now?

## Acceptance criteria for including SysON in DE4SDV workflow

SysON is considered included in the engineering workflow when:

- a local SysON stack can be started from repository instructions;
- a reviewed `.sysml` slice can be imported into SysON;
- at least one pilot view can be exported from SysON as SVG;
- exported SVGs can replace the Git placeholders through a draft PR;
- exported textual `.sysml` is either validated or clearly marked unvalidated;
- manifests identify SysON project/document/diagram IDs where available;
- no generated content is pushed directly to `main`.

## Hard guardrails

- Do not expose SysON publicly without an access-control decision.
- Do not treat SysON-specific JSON as the standard SysML v2 API repository
  format.
- Do not make SysON the only source of truth until standard API/round-trip
  behavior is proven.
- Do not require external contributors to run SysON to submit basic textual
  model PRs.
- Do not delete SysON projects/models without exporting or confirming pilot
  state is disposable.
