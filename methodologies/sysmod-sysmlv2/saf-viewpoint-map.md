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
| Functional Domain | system context, functional behavior, requirements, interfaces, safety/security concerns | requirements, functional model, interface model, risk/security notes |
| Logical Domain | logical structure and logical exchanges; function-to-logical mapping | logical architecture, service/component model, allocation map |
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

### 3. Functional system subset

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
| Logical Structure Definition Viewpoint | define logical elements and composition | logical architecture model |
| Logical Internal Exchange Viewpoint | define internal exchanges | exchange/interface model |
| Logical Internal Interaction Viewpoint | describe interactions | sequence/process model |
| Logical Functional Mapping Viewpoint | allocate functions to logical elements | allocation map |

### 6. Physical/software realization subset

Use when the increment touches software/hardware/deployment realization.

| SAF viewpoint | DE4SDV purpose | Output |
|---|---|---|
| Physical Context Definition Viewpoint | define physical/software context | deployment context |
| Physical Structure Definition Viewpoint | define physical/software components | implementation/deployment model |
| Physical Interface Definition Viewpoint | define concrete interfaces | interface contracts |
| Physical Internal Exchange Viewpoint | define exchanged signals/messages/data | exchange model |
| Physical Functional Mapping Viewpoint | map functions to physical/software elements | function realization map |
| Physical Logical Mapping Viewpoint | map logical to physical/software realization | logical-to-physical trace |

## AEBS pilot viewpoint selection

For the first AEBS pilot, keep the set intentionally small:

| Phase | Selected viewpoints |
|---|---|
| Framing | Common Terms Definition, Common Standards Definition, EA Traceability |
| Operational | Stakeholder Identification, Operational Context Definition, Operational Story, Operational Capability Definition |
| Functional | System Context Definition, System Requirement Definition, System Interface Definition, System Requirement Traceability |
| Product-line | feature/common-capability classification using DE4SDV ontology |
| Evidence | Argumentation Assurance as a stub only |

Out of scope for the first AEBS pilot:

- full logical/physical architecture,
- detailed sensor physics,
- production ECU deployment,
- complete UNECE R152 compliance claim,
- complete safety case or cybersecurity case.

## Guardrails

- SAF selects views; it does not replace SYSMOD method flow.
- Viewpoints should be chosen because they answer stakeholder concerns, not because they are available.
- A missing viewpoint is acceptable when explicitly out of scope.
- Compliance-oriented viewpoints may register constraints and evidence gaps, but must not imply regulatory approval.
- Verification viewpoints check requirement satisfaction; validation viewpoints check stakeholder fitness-for-use in context. Keep both visible.
