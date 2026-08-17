# Upstream SYSMOD SysML v2 Library

## Historical source review

- Repository: <https://github.com/MBSE4U/sysmod-sysmlv2>
- Historically inspected branch: `main`
- Historically inspected commit: `644065e`
- Historically inspected commit date: `2026-05-25T14:04:34-04:00`
- License: Apache-2.0
- Primary artifact: `SYSMOD.sysml`
- Upstream description: SYSMOD language extension and examples for SysML v2

## State at the historical inspection

At the inspected commit, the upstream repository contains:

- `SYSMOD.sysml`, defining a `library package SYSMOD`,
- a delivery drone example model,
- SYSMOD quick-sheet SVGs,
- SysAND packaging metadata,
- a SysAND folder and release workflow, but no published GitHub releases, tags,
  or official SysAND package-manager release.

This state explains the reference-only decision in
[ADR 0002](../../docs/architecture-decisions/0002-adopt-sysmod-sysmlv2-library.md).
It is retained as provenance and is not a description of the current package.

## Current Sysand dependency

- Registry project: <https://sysand.com/projects/mbse4u/sysmod>
- Resource: `pkg:sysand/mbse4u/sysmod`
- Exact version constraint: `=5.1.1`
- Package license: Apache-2.0
- Registry validation: [validated without warnings](https://sysand.com/projects/mbse4u/sysmod/5.1.1/validation)
- Registry source view: <https://sysand.com/projects/mbse4u/sysmod/5.1.1/source>
- Local declaration: [`.project.json`](../../.project.json)
- Locked resolution: [`sysand-lock.toml`](../../sysand-lock.toml)
- DE4SDV boundary:
  [`DE4SDV_SYSMODAdapter`](../../textual-notation-of-model/packages/methods/de4sdv/de4sdv_sysmod_adapter.sysml)

`sysand sync` installs the package under `.sysand/lib`. That directory is a
generated dependency environment and remains untracked. DE4SDV does not copy or
vendor the package source.

The static repository viewer renders the local adapter source and seam
documentation, but does not publish the generated `.sysand` dependency tree.
Review upstream declarations through the registry source view linked above.

## Relevant upstream concepts

The package includes concepts that are directly relevant to DE4SDV:

- `Project`,
- `SystemContext`,
- `ActorSystemInterface`,
- `ActorPort`,
- `SystemPort`,
- `SystemUseCase`,
- `ConstrainedOccurrence`,
- `ExtendedStakeholder`,
- `ExtendedConcern`,
- `ExtendedRequirement`,
- `LevelKind`,
- `StakeholderCategoryKind`,
- `ObligationKind`,
- `StabilityKind`.

The first DE4SDV adapter exposes only local seams for `ExtendedStakeholder`,
`ExtendedRequirement`, `SystemUseCase`, and `ConstrainedOccurrence`. Exposure
does not migrate existing DE4SDV model definitions automatically.

The upstream `Project` concept links a fixed context and architecture artifact
chain. DE4SDV does not adopt it as a project, program, increment, or product-line
root because that would compete with SAF viewpoint organization, DE4SDV
increments, product-line configuration, and evidence ownership.

## DE4SDV adoption policy

DE4SDV will:

1. reference and attribute the upstream library,
2. pin an exact package version and commit the generated lock resolution,
3. specialize selected upstream concepts only through the DE4SDV adapter,
4. validate SysML v2 syntax and packaging with the chosen toolchain before
   treating local models as executable,
5. review package upgrades against every exposed seam,
6. keep the historical Git commit as provenance for the original tailoring
   review, not as the executable dependency identity.

## Deliberately not adopted

DE4SDV does not vendor upstream files, add a submodule, copy quick sheets,
specialize `Project` or `AIProject`, or consume the requirement-boilerplate
constraints. Candidate compatibility questions are recorded in the
[draft upstream report](upstream-compatibility-report.md). They need upstream
maintainer review before DE4SDV depends on the affected definitions.
