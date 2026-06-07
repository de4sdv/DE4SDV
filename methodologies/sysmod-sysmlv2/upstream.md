# Upstream SYSMOD SysML v2 Library

## Upstream source

- Repository: <https://github.com/MBSE4U/sysmod-sysmlv2>
- Inspected branch: `main`
- Inspected commit: `644065e`
- Inspected commit date: `2026-05-25T14:04:34-04:00`
- License: Apache-2.0
- Primary artifact: `SYSMOD.sysml`
- Upstream description: SYSMOD language extension and examples for SysML v2

## Observed upstream state

At the inspected commit, the upstream repository contains:

- `SYSMOD.sysml`, defining a `library package SYSMOD`,
- a delivery drone example model,
- SYSMOD quick-sheet SVGs,
- SysAND packaging metadata,
- a release workflow, but no published GitHub releases or tags.

The upstream README identifies the project as alpha-stage work with limited documentation. DE4SDV therefore treats the repository as an upstream reference and candidate library dependency, not as a stable standard dependency.

## Relevant upstream concepts

The upstream `SYSMOD.sysml` library includes concepts that are directly relevant to DE4SDV:

- `Project`,
- `SystemContext`,
- `ActorSystemInterface`,
- `ActorPort`,
- `SystemPort`,
- `ExtendedStakeholder`,
- `ExtendedConcern`,
- `ExtendedRequirement`,
- `LevelKind`,
- `StakeholderCategoryKind`,
- `ObligationKind`,
- `StabilityKind`.

The upstream `Project` concept links brownfield context, project owner, stakeholders, problem statement, stakeholder needs, system idea context, specification context, requirements, solution context, functional context, logical context, and product context. That structure is a strong fit for incremental DE4SDV modeling.

## DE4SDV adoption policy

DE4SDV should:

1. reference and attribute the upstream library,
2. pin an upstream commit before vendoring or building against the library,
3. specialize upstream concepts in a DE4SDV tailoring package rather than modifying upstream semantics directly,
4. validate SysML v2 syntax and packaging with the chosen toolchain before treating local models as executable,
5. record any copied upstream files with license and modification notices.

## Not adopted in this step

This first step does not vendor upstream files, add a submodule, copy quick sheets, or add toolchain packaging. Those choices should be made in a follow-up after dependency and validation policy are agreed.
