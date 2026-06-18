# Bootstrap DE4SDV context in the SysML v2 API repository

This note describes the first implementation step after
[ADR 0005](../docs/architecture-decisions/0005-use-sysml-v2-api-repository-as-live-model-store.md):
create or reuse a live SysML v2 API project named `DE4SDV`, create an initial
ASELCM-aligned context commit if needed, and sync the real project/commit IDs
back into GitHub-tracked view manifests.

## Scope

The bootstrap is intentionally narrow:

- SysML v2 API project: `DE4SDV`
- model slice: DE4SDV context / System 1-2-3 framing
- initial package names:
  - `DE4SDV`
  - `DE4SDV::Context`
  - `DE4SDV::Context::ConfigurableSDVProductLine`
  - `DE4SDV::Context::DE4SDV_LifecycleEngineeringSystem`
  - `DE4SDV::Context::DE4SDV_OpenInnovationEcosystem`
  - `DE4SDV::LifecycleEngineeringSystem`
- generated metadata targets:
  - `textual-notation-of-model/views/system-context/manifest.json`
  - `textual-notation-of-model/views/lifecycle-engineering-system/manifest.json`
  - `textual-notation-of-model/sync/last-synced-commit.json`

## Run

With a local SysML v2 API service listening on `http://127.0.0.1:9000`:

```bash
python scripts/sync_sysml_repository.py \
  --api-url http://127.0.0.1:9000 \
  --project DE4SDV \
  --branch main
```

Dry-run mode checks access and reports the intended metadata without writing
files or creating a commit:

```bash
python scripts/sync_sysml_repository.py --dry-run --json
```

## Current limitations

This MVP proves the repository boundary. It does not yet solve:

- textual `.sysml` import/export;
- SysON connection to the same backing repository;
- SysON diagram/view export;
- deterministic SVG rendering from the API graph;
- semantic relationship modeling beyond bootstrap package structure.

Those belong in the next SysON feasibility spike and renderer/export PR.

## Tooling direction

For the DE4SDV pilot:

- SysON remains the preferred GUI path for collaborative graphical modeling.
- SysIDE Editor is textual authoring only.
- SysIDE Modeler, including its visualization add-on, remains relevant as a
  higher-end modeling/validation option, but it is not the default GUI path for
  the open-source pilot.
