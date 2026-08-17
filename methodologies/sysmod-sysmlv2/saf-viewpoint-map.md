# SAF Viewpoint Map for DE4SDV Increments

DE4SDV uses the GfSE System Architecture Framework (SAF) as the viewpoint layer around SYSMOD-style method work. SAF helps contributors decide which views are needed for an increment and prevents every contribution from becoming a full-system model.

Source reference: <https://saf.gfse.org/userdoc/viewpoints.html>

## How to use this map

For each increment:

1. state the engineering question,
2. select the smallest useful set of viewpoints,
3. produce the matching DE4SDV artifacts,
4. record omitted viewpoints as out of scope,
5. add trace links to needs, requirements, verification cases, validation scenarios, architecture, evidence, and baselines where relevant.

Do not require all viewpoints for every increment.

## Domain mapping

| SAF domain | Role in DE4SDV | Typical DE4SDV artifacts |
|---|---|---|
| Common Domain | shared terms, standards, argumentation, traceability | glossary, standards register, evidence register, traceability reports |
| Operational Domain | stakeholder needs, operational context, capabilities, scenarios/processes | increment charter, operational context, needs, use cases/scenarios |
| Conceptual Domain | system context, functional behavior, requirements, interfaces, safety/security concerns, logical structure and exchanges, function-to-logical mapping (Functional and Logical merged into Conceptual) | requirements, functional model, interface model, risk/security notes, system architecture, service/component model, allocation map |
| Physical Domain | physical/software realization and mappings | deployment/software/hardware model, interface contracts, realization map |

## Recommended viewpoint subsets

### 1. Increment framing subset

Use for every increment.

| SAF viewpoint | DE4SDV purpose | Output |
|---|---|---|
| Common Terms Definition Viewpoint | define terms introduced by the increment | glossary additions or terminology section |
| Common Standards Definition Viewpoint | register standards/regulations used as constraints or references | standards/source notes |
| EA Traceability Viewpoint | show how increment artifacts link together | traceability table or YAML with gaps/status |
| Stakeholder Identification Viewpoint | identify roles affected by the increment | stakeholder/concern list |

### 2. Operational feature subset

Use when the increment changes an SDV product-line capability or feature.

| SAF viewpoint | DE4SDV purpose | Output |
|---|---|---|
| Operational Context Definition Viewpoint | define external actors/systems and context boundary | operational context model/doc |
| Operational Story Viewpoint | tell the scenario in stakeholder language | scenario narrative |
| Operational Capability Definition Viewpoint | describe operational capability expected from the product line | capability description |
| Operational Process Viewpoint | describe operational flow or lifecycle process | process/behavior sketch |
| Stakeholder Requirement Definition Viewpoint | capture stakeholder-level needs and validation intent | needs, validation scenarios, stakeholder requirements where appropriate |

### 3. System behavior and requirements subset

Use when deriving system behavior, requirements, or interfaces.

| SAF viewpoint | DE4SDV purpose | Output |
|---|---|---|
| System Context Definition Viewpoint | define system boundary and external interfaces | SysML v2 context package or Markdown context |
| System Use Case Viewpoint | capture system use cases | use case model/doc |
| System Capability Definition Viewpoint | define system capabilities | capability model |
| System Functional Breakdown Structure Viewpoint | decompose functions | functional breakdown |
| System Process Viewpoint | describe behavior/process sequencing | process/state model |
| System Interface Definition Viewpoint | define interfaces and exchanged items | interface model |
| System Requirement Definition Viewpoint | define design input requirements and verification intent | requirements model/table with methods and acceptance criteria |
| System Requirement Traceability Viewpoint | trace requirements to needs, model, V&V, evidence, and gaps | traceability report |

### 4. Safety/security subset

Use when the increment affects safety, cybersecurity, or assurance claims.

| SAF viewpoint | DE4SDV purpose | Output |
|---|---|---|
| Asset Identification Viewpoint | identify assets affected by the feature or toolchain | asset list/model |
| Security Context Viewpoint | identify security boundary and context | security context notes/model |
| Security Risk Analysis Viewpoint | capture threat/risk analysis | risk table / threat model draft |
| Threat Szenario Viewpoint | describe threat scenarios | threat scenario narratives |
| Argumentation Assurance Viewpoint | link claims, arguments, evidence, and gaps | assurance argument/evidence stub |

Safety analysis should distinguish hazard analysis, risk assessment, safety requirements, verification evidence, and validation evidence. Security analysis should distinguish threat modeling, vulnerability management, mitigation, and evidence.

### 5. Logical realization subset

Use when the increment introduces or changes logical services/components.

| SAF viewpoint | DE4SDV purpose | Output |
|---|---|---|
| System Structure Definition Viewpoint | define conceptual elements and composition | system architecture model |
| System Internal Exchange Viewpoint | define internal exchanges | exchange/interface model |
| System Internal Interaction Viewpoint | describe interactions | sequence/process model |
| System Function Mapping Viewpoint | allocate functions to conceptual elements | allocation map |

### 6. Physical/software realization subset

Use when the increment touches software/hardware/deployment realization.

| SAF viewpoint | DE4SDV purpose | Output |
|---|---|---|
| Physical Context Definition Viewpoint | define physical/software context | deployment context |
| Physical Context Exchange Viewpoint | identify typed exchanges crossing a physical/software boundary | context exchange model |
| Physical Exchange Type Definition Viewpoint | define reusable physical exchange item and endpoint types | exchange type catalog |
| Physical Structure Definition Viewpoint | define physical/software components | implementation/deployment model |
| Physical Interface Definition Viewpoint | define concrete interfaces | interface contracts |
| Physical Internal Exchange Viewpoint | define exchanged signals/messages/data | exchange model |
| Physical Functional Mapping Viewpoint | map functions to physical/software elements | function realization map |
| Physical Logical Mapping Viewpoint | map logical to physical/software realization | logical-to-physical trace |
| Physical Logical Item Mapping Viewpoint (proposed; no current SAF short code) | map logical information to physical exchange items while recording non-equivalence | logical-to-physical item trace |

The physical viewpoint short codes used by the AEBS deployment slice are
`P1_PCXD` (Physical Context Definition), `P1_PCXE` (Physical Context Exchange),
`P2_PETD` (Physical Exchange Type Definition), `P2_PSTD` (Physical Structure
Definition), `P4_PIEX` (Physical Internal Exchange), `P5_PIFD` (Physical
Interface Definition), and `P8_PLOM` (Physical Logical Mapping). Physical
Logical Item Mapping is a proposed DE4SDV addition and deliberately has no SAF
short code. `P8_PFUM` Physical Functional Mapping is deferred for the AEBS
simulation deployment until executable responsibilities stabilize.

## AEBS pilot viewpoint selection

For the first AEBS pilot, keep the set intentionally small:

| Phase | Selected viewpoints |
|---|---|
| Framing | Common Terms Definition, Common Standards Definition, EA Traceability |
| Operational | Stakeholder Identification, Operational Context Definition, Operational Story, Operational Capability Definition |
| Conceptual | System Context Definition, System Requirement Definition, System Interface Definition, System Requirement Traceability |
| Product-line | feature/common-capability classification using DE4SDV ontology |
| Evidence | Argumentation Assurance as a stub only |

Out of scope for the first AEBS pilot:

- full logical/physical architecture,
- detailed sensor physics,
- production ECU deployment,
- complete UNECE R152 compliance claim,
- complete safety case or cybersecurity case.

## SysML cross-references

The `DE4SDV_MethodViewpoints` SysML package
(`textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_concerns_and_viewpoints.sysml`)
defines reusable concern and viewpoint definitions that implement this mapping.
Each engineering-domain viewpoint def carries a `doc` comment naming its SAF source.

| SysML package | Viewpoint def | Source | AEBS SysML slice with concrete view |
|---|---|---|---|
| `SAF_Viewpoints` | `OperationalContextDefinitionViewpoint` | SAF Operational Domain | `aebs_operational_context.sysml` → `aebsOperationalContextView` |
| `SAF_Viewpoints` | `StakeholderRequirementDefinitionViewpoint` | SAF Operational Domain | `aebs_needs_requirements.sysml` → `aebsStakeholderNeedsView` |
| `SAF_Viewpoints` | `SystemRequirementDefinitionViewpoint` | SAF Conceptual Domain | `aebs_needs_requirements.sysml` → `aebsRequirementTraceView` |
| `SAF_Viewpoints` | `SystemRequirementTraceabilityViewpoint` | SAF Conceptual Domain | `aebs_needs_requirements.sysml` → `aebsRequirementTraceView` |
| `SAF_Viewpoints` | `SystemFunctionalBreakdownStructureViewpoint` | SAF Conceptual Domain | `aebs_functional_behavior.sysml` → `aebsFunctionalBehaviorView` |
| `SAF_Viewpoints` | `SystemInterfaceDefinitionViewpoint` | SAF Conceptual Domain | `aebs_functional_behavior.sysml` → `aebsFunctionalInterfaceView` |
| `SAF_Viewpoints` | `PhysicalStructureDefinitionViewpoint` | SAF Physical Domain (`P2_PSTD`) | `aebs_physical_software_realization.sysml` → `aebsPhysicalSoftwareStructureView` |
| `SAF_Viewpoints` | `PhysicalInterfaceDefinitionViewpoint` | SAF Physical Domain (`P5_PIFD`) | `aebs_physical_software_realization.sysml` → `aebsPhysicalSoftwareInterfaceView` |
| `SAF_Viewpoints` | `PhysicalLogicalMappingViewpoint` | SAF Physical Domain (`P8_PLOM`) | `aebs_physical_software_realization.sysml` → `aebsPhysicalLogicalMappingView` |
| `SAF_Viewpoints` | `PhysicalContextDefinitionViewpoint` | SAF Physical Domain (`P1_PCXD`) | `aebs_simulation_deployment.sysml` → `aebsSimulationPhysicalContextView` |
| `SAF_Viewpoints` | `PhysicalContextExchangeViewpoint` | SAF Physical Domain (`P1_PCXE`) | `aebs_simulation_deployment.sysml` → `aebsSimulationPhysicalContextExchangeView` |
| `SAF_Viewpoints` | `PhysicalExchangeTypeDefinitionViewpoint` | SAF Physical Domain (`P2_PETD`) | `aebs_simulation_deployment.sysml` → `aebsSimulationPhysicalExchangeTypeView` |
| `SAF_Viewpoints` | `PhysicalStructureDefinitionViewpoint` | SAF Physical Domain (`P2_PSTD`) | `aebs_simulation_deployment.sysml` → `aebsSimulationPhysicalStructureView` |
| `SAF_Viewpoints` | `PhysicalInternalExchangeViewpoint` | SAF Physical Domain (`P4_PIEX`) | `aebs_simulation_deployment.sysml` models the System 1 internal flows; no generated view is published until the native renderer can isolate those flows without adding context exchanges or dropping the topology |
| `SAF_Viewpoints` | `PhysicalInterfaceDefinitionViewpoint` | SAF Physical Domain (`P5_PIFD`) | `aebs_simulation_deployment.sysml` → `aebsSimulationPhysicalInterfaceView` |
| `SAF_Viewpoints` | `PhysicalLogicalMappingViewpoint` | SAF Physical Domain (`P8_PLOM`) | `aebs_simulation_deployment.sysml` → `aebsSimulationPhysicalLogicalMappingView` |
| `SAF_Viewpoints` | `PhysicalLogicalItemMappingViewpoint` | Proposed; no current SAF short code | `aebs_simulation_deployment.sysml` → `aebsSimulationPhysicalLogicalItemMappingView` |
| `DE4SDV_MethodViewpoints` | `IncrementFramingViewpoint` | DE4SDV method-governance | `aebs_increment_framing.sysml` → `aebsIncrementFramingView` |
| `DE4SDV_MethodViewpoints` | `ProductLineClassificationViewpoint` | DE4SDV method-governance | `aebs_increment_framing.sysml` → `aebsProductLineClassificationView` |
| `DE4SDV_MethodViewpoints` | `RegulatoryScopeViewpoint` | DE4SDV method-governance | `aebs_increment_framing.sysml` → `aebsRegulatoryScopeView` |

SAF viewpoints are in `textual-notation-of-model/packages/methods/saf/SAF_Viewpoints.sysml`.
DE4SDV method-governance viewpoints are in `textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_concerns_and_viewpoints.sysml`.
New SAF viewpoints are added to `SAF_Viewpoints` incrementally as DE4SDV increments need them.

Each concrete `view` uses a `viewpoint` selection with `frame` bindings to
concerns. Exposures are scoped to the elements and relationships needed to
answer that concern rather than dumping whole packages.

Presentation follows the concern: ownership/decomposition uses trees,
processes use action-flow diagrams, exchanges use interconnection diagrams,
requirement definitions use tables, and allocation mappings use matrices.
Grid views are modeled with a pinned library and exported by the privileged
workflow as both CSV and review SVG. SysML remains authoritative when a
renderer omits or simplifies a valid relationship.

## Current middleware publication exceptions

The middleware increment intentionally withholds four expected views rather
than publish diagrams that do not answer their framed concerns:

- **System Internal Exchange:** the conceptual source currently has boundary
  delegations but no cross-component connections or item flows.
- **System Process:** the source has an internal functional flow, not a
  context-partitioned process with ordered actions and exchanges.
- **System 1 Physical Interface:** the current candidate software endpoint is
  not yet a reviewed pin, bus, deployed service, or production transport
  contract; its native projection also leaks an unrelated allocation.
- **System 2 Physical Internal Exchange:** five connections and five item flows
  are authoritative in the source, but the native projection renders nested
  parts without the connector path, direction, or exchanged item types.

The middleware package does publish one smaller Physical Internal Exchange
slice: `mwAAOSVehicleSpeedServiceBundleInternalExchangeView` selects the
provider and independent observer inside the AAOS service bundle, their owned
ports, the authoritative connection, and the directed
`VehicleSpeedProviderMessage` flow. It is deliberately not a substitute for
the withheld four-hop campaign view.

Each exception and its rationale is also recorded with the framed concern in
the architecture description. A view can return only after its source
semantics exist and exact-head rendering visibly materializes them.

## Guardrails

- SAF selects views; it does not replace SYSMOD method flow.
- Viewpoints should be chosen because they answer stakeholder concerns, not because they are available.
- A missing viewpoint is acceptable when explicitly out of scope.
- Compliance-oriented viewpoints may register constraints and evidence gaps, but must not imply regulatory approval.
- Verification viewpoints check requirement satisfaction; validation viewpoints check stakeholder fitness-for-use in context. Keep both visible.
