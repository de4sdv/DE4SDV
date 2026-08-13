# Middleware Integration Increment Chain

Aligned to DE4SDV increment-workflow.md (13 phases). Each increment produces a reviewable SysML v2 slice with correct SAF viewpoints and a YAML framing file.

## Status

- INC-MW-001: DONE (merged PR #70) — increment framing, adapter layer in SDV platform stack
- INC-MW-002 (old): DONE but needs repositioning (merged PR #71) — AAOS SDV boundary model. This is a physical-domain artifact that belongs in INC-MW-008, not as the second increment. It will be referenced as source material when we reach physical realization.
- INC-MW-002 through INC-MW-010: TODO — follow the DE4SDV method chain

## Increment chain

### INC-MW-002: Operational context for middleware integration
- Phase: 2 (Operational context)
- Question: What operational scenarios require middleware integration between an ADAS application and the vehicle platform?
- SAF viewpoints: OperationalContextDefinitionViewpoint, OperationalStoryViewpoint, StakeholderIdentificationViewpoint
- Outputs: operational context, actors, scenarios, operational processes
- Content: ADAS app needs vehicle speed signal, diagnostic state, lifecycle coordination from vehicle platform. Operational stories: normal driving (signal exchange), service update (A/B partition swap), fault detection (health monitoring), vehicle startup (lifecycle coordination)
- SysML file: textual-notation-of-model/packages/features/middleware/mw_operational_context.sysml
- YAML: methodologies/sysmod-sysmlv2/pilots/mw-operational-context.yaml

### INC-MW-003: Feature/common-capability classification
- Phase: 3 (Capability/feature semantics)
- Question: Is each middleware element a feature, common capability, constraint, or evidence capability?
- Viewpoints: ProductLineClassificationViewpoint (DE4SDV method), EATraceabilityViewpoint (SAF)
- Outputs: feature/common-capability classification, variation points
- Content: adapter layer = common capability, AAOS SDV = feature, S-CORE = feature, variation points in SDV platform stack
- Note: Phase 3 labels capabilities; Phase 9 assembles the variation points into configured product models
- SysML file: textual-notation-of-model/packages/features/middleware/mw_feature_classification.sysml
- YAML: methodologies/sysmod-sysmlv2/pilots/mw-feature-classification.yaml

### INC-MW-004: Stakeholder needs
- Phase: 4 (Needs)
- Question: What stakeholder needs exist for middleware integration and how will they be validated?
- SAF viewpoints: StakeholderRequirementDefinitionViewpoint
- Outputs: needs, sources, rationale, validation intent
- Content: platform engineer (no coupling), systems engineer (traceability), product-line engineer (middleware as feature), safety engineer (safety path isolation), maintainer (upstream engagement)
- SysML file: textual-notation-of-model/packages/features/middleware/mw_needs_requirements.sysml
- YAML: methodologies/sysmod-sysmlv2/pilots/mw-needs-requirements.yaml

### INC-MW-005: Requirements
- Phase: 5 (Requirements)
- Question: What shall the middleware integration do and how will requirements be verified?
- SAF viewpoints: SystemRequirementDefinitionViewpoint, SystemRequirementTraceabilityViewpoint
- Outputs: design input requirements, constraints, verification methods, trace links
- Content: signal access, diagnostic access, lifecycle coordination, safety path isolation, service discovery with auth
- SysML file: (same file as needs, or separate mw_requirements.sysml)
- YAML: methodologies/sysmod-sysmlv2/pilots/mw-requirements.yaml

### INC-MW-006: Functional architecture
- Phase: 6 (Functional architecture)
- Question: What functions, flows, states, and interfaces are needed for middleware integration?
- SAF viewpoints: SystemFunctionalBreakdownStructureViewpoint, SystemProcessViewpoint, SystemInterfaceDefinitionViewpoint
- Outputs: functional breakdown, interfaces, behavior slices
- Content: signal translation, lifecycle delegation, health forwarding, diagnostic proxy, update coordination. State machines: service lifecycle, health states, connection states
- SysML file: textual-notation-of-model/packages/features/middleware/mw_functional_behavior.sysml
- YAML: methodologies/sysmod-sysmlv2/pilots/mw-functional-behavior.yaml

### INC-MW-007: Logical architecture
- Phase: 7 (Logical architecture)
- Question: What logical elements realize the middleware integration functions?
- SAF viewpoints: SystemStructureDefinitionViewpoint, SystemInternalExchangeViewpoint, SystemFunctionMappingViewpoint
- Outputs: logical structure, exchanges, allocation/mapping
- Content: SignalTranslator, LifecycleBridge, HealthProxy, DiagnosticProxy, UpdateCoordinator. Mapping from AEBS logical architecture external service dependencies to middleware logical components
- SysML file: textual-notation-of-model/packages/features/middleware/mw_logical_architecture.sysml
- YAML: methodologies/sysmod-sysmlv2/pilots/mw-logical-architecture.yaml

### INC-MW-008: Physical/software realization
- Phase: 8 (Physical/software realization)
- Question: What software elements realize the middleware logical design?
- SAF viewpoints: PhysicalStructureDefinitionViewpoint, PhysicalInterfaceDefinitionViewpoint, PhysicalFunctionalMappingViewpoint, PhysicalLogicalMappingViewpoint
- Outputs: physical/software structure, interfaces, mappings
- Content: existing AAOS SDV boundary model (INC-MW-002/PR #71) goes HERE. AutowareToAAOSSDVAdapter concrete mapping. ROS 2 topics to VSIDL services. Which AAOS SDV services satisfy which logical components
- SysML file: textual-notation-of-model/packages/features/middleware/mw_physical_software_realization.sysml (reposition aaos_sdv_middleware_boundary.sysml content here)
- YAML: methodologies/sysmod-sysmlv2/pilots/mw-physical-software-realization.yaml

### INC-MW-009: Variability and configuration
- Phase: 9 (Variability and configuration)
- Question: How does middleware integration vary across member products?
- Viewpoints: ProductLineConfigurationViewpoint (DE4SDV method), ProductModelAssemblyViewpoint (DE4SDV method)
- Outputs: variation points, feature configurations, product model assembly
- Content: PLE feature model (middleware selection: AAOS SDV, S-CORE, AUTOSAR, none). Adapter variant follows from (app, middleware) pair. Bill-of-features for AAOS SDV member product. Product model projection. Consolidates variation points from phases 3-8.
- SysML file: (updates to existing PLE feature model and product models)
- YAML: methodologies/sysmod-sysmlv2/pilots/mw-variability-configuration.yaml

### INC-MW-010: V&V and evidence
- Phase: 10 (V&V and evidence)
- Question: How will middleware integration requirement satisfaction be checked?
- SAF viewpoints: ArgumentationAssuranceViewpoint
- Outputs: verification cases, validation scenarios, acceptance criteria, evidence records, open gaps
- Content: signal translation correctness, lifecycle coordination, health forwarding. Integration test results. Evidence status: planned/draft
- SysML file: textual-notation-of-model/packages/features/middleware/mw_verification_evidence.sysml
- YAML: methodologies/sysmod-sysmlv2/pilots/mw-vv-evidence.yaml

## Trace chain

Each increment must establish:
```
Stakeholder concern
  -> Need
  -> Requirement / constraint
  -> Feature or common capability
  -> Architecture element / function / interface
  -> Verification case and validation scenario
  -> Acceptance criterion
  -> Evidence artifact and evidence status
  -> Baseline or release decision
```

## Viewpoint flow

Per PR #74 process-mapping.md, each phase has typical viewpoints. The middleware chain uses:

| Phase | Viewpoints | Source |
|---|---|---|
| 0 — Framing | IncrementFramingViewpoint, CommonTermsDefinition, CommonStandardsDefinition, EATraceability | DE4SDV method + SAF |
| 1 — Concern framing | StakeholderIdentificationViewpoint | SAF |
| 2 — Operational context | OperationalContextDefinition, OperationalStory, OperationalCapabilityDefinition | SAF |
| 3 — Capability classification | ProductLineClassificationViewpoint | DE4SDV method |
| 4 — Needs | StakeholderRequirementDefinitionViewpoint | SAF |
| 5 — Requirements | SystemRequirementDefinition, SystemRequirementTraceability | SAF |
| 6 — Functional architecture | SystemFunctionalBreakdownStructure, SystemProcess, SystemInterfaceDefinition | SAF |
| 7 — Logical architecture | LogicalStructureDefinition, LogicalInternalExchange, LogicalFunctionalMapping | SAF |
| 8 — Physical realization | PhysicalStructureDefinition, PhysicalInterfaceDefinition, PhysicalFunctionalMapping, PhysicalLogicalMapping | SAF |
| 9 — Variability and configuration | ProductLineConfigurationViewpoint, ProductModelAssemblyViewpoint | DE4SDV method |
| 10 — V&V and evidence | ArgumentationAssurance | SAF |

## Key constraints

- The AEBS emergency intervention path does NOT go through the adapter or middleware (ASM-MW-003)
- AAOS SDV is modeled as a boundary, not a vendored implementation
- Upstream AAOS SDV maintainers should be engaged before deeper integration (GAP-MW-005)
- No compliance/certification claims
- The existing aaos_sdv_middleware_boundary.sysml (PR #71) is reference material for INC-MW-008

## Source references

- AAOS SDV integration guide: https://source.android.com/docs/automotive/sdv/workstreams/core/integration-guide (last updated 2026-06-17, Apache 2.0)
- DE4SDV increment workflow: methodologies/sysmod-sysmlv2/increment-workflow.md
- SAF viewpoints: textual-notation-of-model/packages/methods/saf/SAF_Viewpoints.sysml
- SAF aspects: https://saf.gfse.org/userdoc/aspects.html
- INC-MW-001 framing: methodologies/sysmod-sysmlv2/pilots/middleware-adapter-increment-framing.yaml
- SDV platform stack: textual-notation-of-model/packages/architecture/sdv_platform_stack.sysml
- AEBS physical realization (required boundaries): textual-notation-of-model/packages/features/aebs/aebs_physical_software_realization.sysml
