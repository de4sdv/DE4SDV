# SYSMOD SysML v2 Methodology

DE4SDV uses a SYSMOD-inspired modeling workflow for incremental SysML v2 model development. This methodology area records how DE4SDV adopts and tailors the public MBSE4U SYSMOD SysML v2 library for software-defined vehicle product-line engineering and assurance work.

## Intent

The method provides a shared modeling sequence for contributors:

1. frame the problem and brownfield context,
2. identify stakeholders and concerns,
3. define the System of Interest and its context,
4. derive needs and requirements,
5. describe use cases and interactions,
6. develop functional, logical, and product architecture views,
7. connect product-line variability to configured product models,
8. link requirements, model elements, evidence, and baselines.

## Adoption model

DE4SDV does not redefine SYSMOD from scratch. It references the upstream MBSE4U SysML v2 library and adds DE4SDV-specific guidance for:

- software-defined vehicle product-line engineering,
- model-based product-line engineering,
- digital continuity and traceability,
- evidence and baseline management,
- continuous homologation support,
- open-source contribution and review workflows.

## Current maturity

This repository is in a foundation phase. The first adoption step is documentation and decision capture only. Future increments may add a local tailoring package and small SysML v2 examples after toolchain validation.

## Files

- [`upstream.md`](upstream.md) records the upstream repository, inspected commit, license, and adoption caveats.
- [`de4sdv-tailoring.md`](de4sdv-tailoring.md) explains how DE4SDV specializes the upstream library concepts.
- [`increment-workflow.md`](increment-workflow.md) defines the generic repeatable increment workflow for features, architecture, toolchain, and evidence work.
- [`saf-viewpoint-map.md`](saf-viewpoint-map.md) maps GfSE SAF viewpoint families to DE4SDV increment outputs.
- [`artifact-map.md`](artifact-map.md) maps method concepts to DE4SDV repository artifacts.
- [`review-checklist.md`](review-checklist.md) provides a checklist for future method/model contributions.
- [`pilots/aebs-pilot-charter.md`](pilots/aebs-pilot-charter.md) applies the method to an AEBS regulatory-aligned feature pilot without claiming compliance.
