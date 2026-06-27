# SYSMOD SysML v2 Artifact Map

This map shows how the upstream SYSMOD SysML v2 concepts can connect to existing DE4SDV repository areas.

## Method concept to repository artifact

- `Project`
  - DE4SDV project-level modeling context.
  - Candidate artifacts: `README.md`, `docs/project-goals/project-charter.md`, future `textual-notation-of-model/packages/de4sdv_project.sysml`.

- `SystemContext`
  - System of Interest boundary, actors, interfaces, and use cases.
  - Candidate artifacts: `textual-notation-of-model/packages/de4sdv_context.sysml`, `approach/framework/viewpoint/`.

- `ExtendedStakeholder`
  - Stakeholder types, roles, risk/effort prioritization, and concerns.
  - Candidate artifacts: `docs/project-goals/project-charter.md`, `approach/framework/viewpoint/`, future stakeholder model package.

- `ExtendedConcern`
  - Problem statement, stakeholder needs, architecture concerns, and review concerns.
  - Candidate artifacts: `approach/framework/viewpoint/`, `methodologies/sysmod-sysmlv2/review-checklist.md`.

- `ExtendedRequirement`
  - Requirements enriched with obligation, stability, and motivation attributes.
  - Candidate artifacts: future `textual-notation-of-model/packages/de4sdv_requirements.sysml`, `continuous-homologation/evidence-register.md`.

- `functionalContext`
  - Functional capabilities and behavior.
  - Candidate artifacts: `approach/process-set/`, future functional model package.

- `logicalContext`
  - Logical architecture and allocation decisions.
  - Candidate artifacts: future logical architecture model package, `sysmlv2-api/`, `digital-continuity/`.

- `productContext`
  - Product-line variants, configured product models, and shared assets.
  - Candidate artifacts: `model-based-product-line-engineering/`, future variability model package.

## Integration with evidence and baselines

Every substantial modeling increment should identify whether it impacts:

- feature models or feature configurations,
- product models or shared assets,
- requirements or stakeholder needs,
- verification or validation intent,
- evidence records,
- configuration baselines,
- digital thread traceability.

Relevant existing artifacts:

- `configuration-management/baseline-register.md`,
- `continuous-homologation/evidence-register.md`,
- `digital-continuity/traceability-matrix-template.md`,
- `model-based-product-line-engineering/`.

## Suggested contribution sequence

1. Adopt upstream reference and tailoring policy.
2. Define the generic increment workflow and SAF viewpoint selection map.
3. Maintain a minimal ontology kernel for increment traceability and product-line semantics.
4. Use a small pilot, such as AEBS, to test the workflow before expanding model scope.
5. Add a small DE4SDV tailoring package after dependency/tooling policy is agreed.
6. Add a System of Interest context model.
7. Add stakeholder and requirement slices.
8. Add product-line variability and configured-product slices.
9. Add verification/evidence traceability slices.
