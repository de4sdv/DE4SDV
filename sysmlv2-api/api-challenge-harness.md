# SysML v2 API challenge harness

## Purpose

DE4SDV should not only wrap current tools. It should actively test whether the
SysML v2 API can support an open, reviewable, continuously validated engineering
workflow for software-defined vehicle product lines.

The API challenge harness makes the SysML v2 API repository the system under
test. SysON remains a candidate GUI adapter, but this harness deliberately starts
from the native API boundary instead of SysON-specific GraphQL or exchange JSON.

## Current harness

The initial executable harness is:

```bash
python scripts/sysml_api_challenge.py dry-run
```

It creates a deterministic expected graph for the DE4SDV ASELCM context slice and
writes an evidence report to:

```text
sysmlv2-api/challenge-reports/de4sdv-context-api-challenge.json
```

To exercise a running SysML v2 API Services instance:

```bash
python scripts/sysml_api_challenge.py seed-context \
  --api-url http://127.0.0.1:9000 \
  --project "DE4SDV API Challenge"
```

The command seeds the context graph through API commits, reads back the commit
elements exposed by the API, compares expected elements against observed
elements, and records pass/fail evidence.

Current live-service finding: SysML v2 API Services reassigns element IDs during
commit persistence. The harness therefore stages seeding in two commits:

1. packages, part definitions, and part usages;
2. dependency relationships using the API-assigned IDs read back from commit 1.

With that staged flow, the DE4SDV context graph reads back successfully. The
report status is `passed-with-warnings` because all semantic elements pass but
API-assigned IDs differ from the deterministic expected IDs.

To export the supported subset from an API commit into textual SysML:

```bash
python scripts/sysml_api_challenge.py export-snapshot \
  --api-url http://127.0.0.1:9000 \
  --project-id <project-id> \
  --commit-id <commit-id> \
  --output /tmp/api-exported-de4sdv.sysml
```

## Model slice under test

The first challenge slice intentionally stays small:

```text
DE4SDV
  Context
    ConfigurableSDVProductLine
    LifecycleEngineeringSystem
    OpenInnovationEcosystem
  EngineeringAssets
    ModelRepository
    ValidationPipeline
    EvidenceBaseline
  RelationshipIntents
    governs / evolves
    engineers / assures
    manages model baselines
    executes validation
    maintains assurance evidence
```

The harness tests these API-facing capabilities first:

- package containment;
- part definitions;
- part usages;
- reference part usages;
- dependency source/target relationships;
- project commit creation/readback;
- deterministic evidence reporting.

## Why this is different from the SysON sidecar

The SysON sidecar idea is useful for near-term GUI workflow, but it mostly works
around missing native API support. The challenge harness instead asks whether the
standard API can act as the model repository backbone.

Target architecture:

```text
GitHub reviewed baseline
  <-> API import/export harness
  <-> SysML v2 API repository under test
  <-> future SysON/tool adapters
```

SysON integration should plug into this API-centered loop after the API slice is
seeded, exported, and compared. That keeps SysON from becoming the hidden source
of truth.

## Gap questions recorded by the report

The initial report records open questions that matter for DE4SDV adoption:

1. Can the standard API carry enough view/layout semantics for SysON/Sirius
   diagrams, or must layout remain tool-specific publication state?
2. Can API state be exported to stable, reviewable SysML v2 textual notation
   without losing identifiers and relationship intent?
3. Can model commits support reviewable branch/merge workflows aligned with
   GitHub pull requests?

These questions should become concrete findings as the harness grows.

## SysON v2026.5.0 import/export finding

The API-exported textual snapshot imports into SysON v2026.5.0 through the
existing GraphQL upload endpoint:

```bash
python scripts/syson_exchange.py --url http://127.0.0.1:8080 import-document \
  <syson-project-id> \
  /tmp/api-exported-de4sdv.sysml
```

SysON search confirms the imported project contains the expected packages, part
definitions, part usages, and dependency objects.

The correct textual document download endpoint is the Sirius Web document
endpoint already used by `scripts/syson_exchange.py`:

```text
GET /api/editingcontexts/{editingContextId}/documents/{documentId}
Accept: text/html
```

The `Accept` value matters: SysON's `SysMLv2DocumentExporter` is registered for
`text/html`, not `text/plain`. On ARM/QEMU the export can take around 20 seconds,
so the helper uses a longer timeout.

Current roundtrip gap: SysON exports the package/part structure but drops the
imported dependency relationships from the textual document export. Example
observed export result:

```sysml
package DE4SDV {
  package EngineeringAssets { ... }
  package Context { ... }
  package RelationshipIntents;
}
```

So the current state is:

```text
SysML v2 API -> textual snapshot -> SysON import: works
SysON textual export endpoint: found and callable
SysON export preserving dependencies: not working yet
Full SysON -> API roundtrip: not complete
```

This is an actual API/tool challenge finding, not a script failure: SysON can
hold dependency objects after import, but its textual exporter does not preserve
those dependencies in the downloaded `.sysml` document for this slice.

## Near-term roadmap

1. Run `dry-run` in CI as a deterministic evidence/report smoke path.
2. Run `seed-context` against a local SysML v2 API Services instance and capture
   readback gaps.
3. Keep the API-to-textual snapshot exporter limited to the supported subset.
4. Investigate whether SysON's textual exporter intentionally omits dependency
   relationships or needs a different containment/import pattern.
5. Convert recurring API/SysON mismatches into upstream issues, ADR updates, or
   DE4SDV challenge reports.

## Guardrails

- Do not treat SysON-specific JSON as native SysML v2 API evidence.
- Do not make diagram layout canonical until the API representation question is
  answered.
- Do not push generated snapshots or reports directly to `main`; use pull
  requests.
- Keep the supported subset explicit. Unsupported SysML concepts should be
  recorded as gaps, not silently flattened.
