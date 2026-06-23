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
roots exposed by the API, compares expected elements against observed elements,
and records pass/fail evidence.

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

## Near-term roadmap

1. Run `dry-run` in CI as a deterministic evidence/report smoke path.
2. Run `seed-context` against a local SysML v2 API Services instance and capture
   readback gaps.
3. Add an API-to-textual snapshot exporter for the supported subset.
4. Add a SysON adapter only after the API-centered baseline is working.
5. Convert recurring API mismatches into upstream issues, ADR updates, or
   DE4SDV challenge reports.

## Guardrails

- Do not treat SysON-specific JSON as native SysML v2 API evidence.
- Do not make diagram layout canonical until the API representation question is
  answered.
- Do not push generated snapshots or reports directly to `main`; use pull
  requests.
- Keep the supported subset explicit. Unsupported SysML concepts should be
  recorded as gaps, not silently flattened.
