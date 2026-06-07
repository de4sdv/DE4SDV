# ADR 0002: Adopt the MBSE4U SYSMOD SysML v2 library as a modeling reference

## Status

Proposed

## Context

DE4SDV needs a contributor-friendly method for creating SysML v2 model content. The method should support System of Interest definition, stakeholder concerns, context modeling, requirements, functional/logical/product architecture, product-line variability, and traceability to evidence and baselines.

A public upstream repository, `MBSE4U/sysmod-sysmlv2`, provides a SysML v2 library implementing SYSMOD concepts. At the inspected commit, the upstream repository is Apache-2.0 licensed and contains a `SYSMOD.sysml` library package plus examples. The upstream README describes the project as alpha-stage work with no official release yet.

## Decision

DE4SDV will adopt `MBSE4U/sysmod-sysmlv2` as an upstream modeling-method reference for SYSMOD concepts in SysML v2.

DE4SDV will not copy or vendor the upstream library in this decision. Instead, DE4SDV will document the upstream source, inspected commit, license, maturity caveats, and intended tailoring approach. A future decision can pin and vendor the upstream library after syntax, packaging, and toolchain validation.

DE4SDV-specific model content should specialize or import upstream SYSMOD concepts through a DE4SDV tailoring layer rather than modifying upstream concepts directly.

## Consequences

- DE4SDV avoids inventing a separate, incompatible SYSMOD-in-SysML-v2 vocabulary.
- Future SysML v2 model packages can use a clearer method structure for projects, contexts, stakeholders, concerns, requirements, and architecture contexts.
- The project must track upstream maturity and avoid presenting alpha-stage upstream content as stable.
- Any future vendoring must preserve Apache-2.0 license and attribution requirements.
- Toolchain validation is required before upstream-derived SysML v2 models are treated as executable or CI-enforced artifacts.

## Follow-up work

- Decide whether to vendor a pinned copy of `SYSMOD.sysml` or consume it as an external dependency.
- Add a small DE4SDV tailoring package after dependency policy is agreed.
- Map selected GfSE SAF viewpoints to SYSMOD concepts and DE4SDV artifacts.
- Add a small System of Interest/context model as the first executable SysML v2 slice.
