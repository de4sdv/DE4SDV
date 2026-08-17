# SYSMOD SysML v2 Artifact Map

This map shows how the upstream SYSMOD SysML v2 concepts can connect to existing DE4SDV repository areas.

## Method concept to repository artifact

| Upstream concept or artifact | DE4SDV boundary | SAF/domain treatment | Adoption state |
|---|---|---|---|
| `Project` | No DE4SDV specialization. Increment, product-line, and evidence roots remain separate. | Not a SAF domain or viewpoint. | Deliberately excluded pending an ownership decision. |
| `SystemContext` | Existing DE4SDV method and feature context packages remain authoritative. | Operational context provides mission/use input; system context participates in Conceptual views. | Pattern reused locally; no upstream specialization yet. |
| `ExtendedStakeholder` | `DE4SDV_SYSMODAdapter::SYSMODStakeholderBase` is the package seam. Existing `DE4SDV_Stakeholders` roles are unchanged. | Stakeholder concerns select views across domains. | Seam available; migration deferred to a separate pilot. |
| `ExtendedConcern` | Existing DE4SDV and SAF concern definitions remain authoritative. | Concerns frame viewpoints; they are not architecture levels. | Not exposed by the first adapter. |
| `ExtendedRequirement` | `DE4SDV_SYSMODAdapter::SYSMODRequirementBase` is the package seam. Existing requirement-candidate lifecycle remains unchanged. | Needs are Operational inputs; design-input requirements are handled through Conceptual viewpoints. | Seam available; migration deferred to a separate pilot. |
| `SystemUseCase` | `DE4SDV_SYSMODAdapter::SYSMODSystemUseCaseBase` is the package seam. | Operational scenarios motivate system use cases; use-case artifacts participate in Conceptual views. | Seam available; no existing model migrated. |
| `ConstrainedOccurrence` | `DE4SDV_SYSMODAdapter::SYSMODConstrainedOccurrenceBase` is the package seam. | Used only when pre/postcondition lifecycle semantics fit the modeled occurrence. | Seam available; no existing model migrated. |
| Functional architecture | Existing feature functional behavior and interface packages. | Distinct artifact kind in the Conceptual Domain, traced to Operational needs/scenarios. | Preserved. |
| Logical architecture | Existing technology-independent system structures, exchanges, and function allocations. | Presented through current SAF `System*` viewpoints in the Conceptual Domain. | Preserved as system-architecture semantics. |
| Product architecture | Existing concrete hardware/software/deployment realization packages. | Presented through Physical-domain viewpoints and traces from system architecture. | Preserved; not a member-product synonym. |

The adapter is the only package allowed to import `SYSMOD`. Feature and
architecture packages consume DE4SDV-owned definitions so dependency upgrades
remain reviewable.

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

## Adoption and migration sequence

1. Resolve and lock the exact package without vendoring source.
2. Validate the unchanged DE4SDV model with the dependency present.
3. Keep selected upstream definitions behind `DE4SDV_SYSMODAdapter`.
4. Review one low-risk specialization pilot separately.
5. Re-run SysML, viewer, product-line, and evidence regression gates.
6. Expand the adapter only when a DE4SDV artifact needs the concept and the
   upstream extension semantics have been reviewed.

Do not introduce a second architecture root, equate SAF domain names with
SYSMOD artifact names, or treat package availability as evidence that an
existing DE4SDV artifact has migrated.
