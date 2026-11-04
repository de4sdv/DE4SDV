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

The DE4SDV adapter exposes local seams for `ExtendedStakeholder`,
`ExtendedRequirement`, `SystemUseCase`, and `ConstrainedOccurrence`. The
requirement seam is specialized by `DE4SDV_MethodContext::RequirementCandidate`;
the use-case seam is specialized by the AEBS and middleware integration use
cases. The stakeholder and constrained-occurrence seams remain available but
are not yet specialized by existing DE4SDV definitions.

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

## SAF reference catalogue lineage

The `SAF_Viewpoints` catalogue
(`textual-notation-of-model/packages/methods/saf/`) is a source-backed reference
to the GfSE System Architecture Framework, not a vendored copy. Two GfSE
repositories are involved, and only one of them is the content source.

- Content source: <https://github.com/GfSE/SAF-Specification>, `main` @
  `bc6bd5ce2bf27f3b18b084377198c6de85fe94a3`. This repository builds
  saf.gfse.org, the viewpoint pages the catalogue cites in every definition.
- Viewpoint data: `src/_data/viewpoints.json` at that pin — 58 viewpoints with
  their name, grid identifier, domain, aspect, purpose, maturity, required and
  recommended viewpoints, and concern identifiers.
- Concern data: `src/_data/concerns.json` at the same pin — 146 concerns whose
  `Name` is the question text. The catalogue states the questions of each
  viewpoint it defines verbatim, after its own lead-in.
- Rename evidence: every renamed viewpoint keeps its stable SAF element
  identifier across the `PreRefactor2026` (`6b09c2f7`) and `TdSE2025`
  (`2cda0814`) branches of the same repository.
- Experimental projection, not a content source:
  <https://github.com/GfSE/SAF-SysMLV2>, `main` @
  `c57bd42db60a00c51168f6aba8e2229ba0165b6c`. Its naming predates the 2026
  refactor, so its names and its two purpose texts are not used for catalogue
  content; it is read for SysML v2 mechanics only.
- Not adopted from either repository: the `Presentation` fields, which describe
  SysML v1 diagram kinds, and the stereotype and profile data. DE4SDV chooses
  its SysML v2 renderings itself, limited by what the renderer publishes.
