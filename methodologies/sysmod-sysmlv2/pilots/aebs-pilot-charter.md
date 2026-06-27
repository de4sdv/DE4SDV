# AEBS Pilot Charter

## Status

Draft pilot charter. This is a method and modeling pilot, not a regulatory compliance claim.

## Increment name

AEBS regulatory-aligned feature increment pilot.

## Purpose

Use Advanced Emergency Braking System (AEBS) as the first concrete forcing function for the generic DE4SDV increment workflow. The pilot should test whether DE4SDV can connect:

```text
SAF viewpoints
  -> SYSMOD-style method flow
  -> DE4SDV ontology terms
  -> product-line feature/common-capability semantics
  -> needs and requirements
  -> architecture/evidence artifacts
```

The pilot should be useful even before detailed SysML v2 modeling starts.

## Candidate external reference

UNECE Regulation No. 152 is a candidate regulatory anchor for AEBS terminology, scenarios, and performance constraints. This charter does not assert compliance with UNECE R152 and does not copy regulatory requirements into the repository. Any future regulatory mapping must cite the exact source, version, and clause-level interpretation.

## System framing

The pilot touches two DE4SDV layers:

| Layer | Pilot meaning |
|---|---|
| System 1 | Configured SDV product variant with AEBS-related behavior/capability |
| System 2 | DE4SDV engineering and assurance system that models AEBS variability, requirements, architecture, scenarios, and evidence |
| System 3 | DE4SDV open-source governance that reviews and evolves the AEBS modeling method |

The first pilot is mostly System 2 work: it defines how DE4SDV represents and reviews an AEBS-related System 1 capability/feature slice.

## Engineering question

Can DE4SDV model an AEBS-oriented product-line increment in a way that preserves traceability from stakeholder concerns and regulatory constraints to feature classification, requirements, architecture decisions, verification intent, and evidence artifacts?

## Initial scope

In scope for the first pilot:

- forward collision risk mitigation / AEBS-oriented behavior as a product-line modeling slice,
- stakeholder concerns and needs,
- feature vs common-capability classification,
- selected SAF viewpoint set,
- draft regulatory source registration and constraint placeholder,
- first traceability structure for requirements, scenarios, architecture, and evidence.

Out of scope for the first pilot:

- claim of UNECE R152 compliance,
- complete clause-by-clause regulatory interpretation,
- pedestrian/cyclist/VRU behavior unless explicitly selected later,
- complete sensor physics or perception performance modeling,
- production ECU architecture,
- complete functional safety case,
- complete cybersecurity case,
- vehicle test results.

## Stakeholders and concerns

| Stakeholder | Concern |
|---|---|
| Product-line engineer | AEBS-related capabilities and features must be represented as selectable/common product-line assets without confusing common capabilities with features. |
| Systems engineer | AEBS behavior, context, interfaces, and architecture must be reviewable and traceable. |
| Safety engineer | AEBS hazards, mitigations, and verification evidence must be distinguishable from informal feature descriptions. |
| Compliance engineer | Regulatory assumptions and evidence gaps must be visible without claiming approval. |
| Software architect | Functions and logical/software responsibilities must be allocated clearly enough for implementation planning. |
| Verification engineer | Scenarios, requirements, and evidence artifacts must be linked. |
| Open-source maintainer | The pilot must remain small enough to review and must not import uncontrolled regulatory text or unvalidated tool outputs. |

## Selected SAF viewpoints

| Phase | Viewpoints selected for first pilot |
|---|---|
| Common/framing | Common Terms Definition, Common Standards Definition, EA Traceability |
| Operational | Stakeholder Identification, Operational Context Definition, Operational Story, Operational Capability Definition |
| Functional | System Context Definition, System Requirement Definition, System Interface Definition, System Requirement Traceability |
| Assurance stub | Argumentation Assurance, as a placeholder for claim/evidence structure only |

Deferred viewpoints:

- Logical Structure Definition,
- Logical Functional Mapping,
- Physical Structure Definition,
- Physical Interface Definition,
- Security Risk Analysis,
- Threat Scenario.

These are deferred because the first pilot should validate the method and trace chain before introducing detailed realization architecture.

## Feature/common-capability hypothesis

The pilot must not assume that "AEBS" is automatically a DE4SDV feature. Classification depends on product-line variability:

| Characteristic | Candidate classification | Reason |
|---|---|---|
| Forward collision risk mitigation | CommonCapability, if present in all target member products | It does not distinguish variants when universal. |
| Automatic emergency braking behavior | Feature or CommonCapability, depending on variant applicability | It is a feature only if some member products have it and others do not, or if selected behavior levels vary. |
| Vehicle-target AEBS support | Feature candidate | It may distinguish variants or regulatory configurations. |
| VRU/pedestrian/cyclist support | Feature candidate, deferred | Likely variant-dependent; out of first slice unless selected. |
| Sensor package selection | VariationPoint | Camera/radar/fusion differences affect realization and evidence. |
| Evidence level | VariationPoint | Simulation-only vs HIL vs vehicle-test evidence affects release/certification confidence. |

## Draft needs

| ID | Need statement | Source/rationale |
|---|---|---|
| N-AEBS-001 | Road users and vehicle occupants need the configured SDV variant to reduce forward collision risk under defined operating conditions. | AEBS pilot intent; regulatory alignment candidate. |
| N-AEBS-002 | Systems engineers need AEBS behavior and boundaries to be described in reviewable model artifacts. | DE4SDV modeling workflow. |
| N-AEBS-003 | Product-line engineers need AEBS applicability and variation choices to be explicit across member products. | Product-line governance. |
| N-AEBS-004 | Verification engineers need AEBS requirements to trace to scenarios and evidence artifacts. | Continuous evidence baseline. |
| N-AEBS-005 | Compliance engineers need regulatory assumptions and gaps to be visible without implying certification. | Compliance guardrail. |

## Candidate requirements direction

These are direction-setting placeholders, not final requirements:

| ID | Draft direction | Notes |
|---|---|---|
| REQ-AEBS-001 | The configured SDV variant shall identify forward collision risk under selected AEBS operational design conditions. | Needs regulation/source refinement before thresholds. |
| REQ-AEBS-002 | The configured SDV variant shall command an emergency braking intervention when selected activation conditions are met. | Must be tied to scenario and interface assumptions. |
| REQ-AEBS-003 | The configured SDV variant shall provide driver warning behavior when required by the selected AEBS behavior profile. | Warning modality is a variation point candidate. |
| REQ-AEBS-004 | The AEBS feature increment shall link each requirement to at least one verification case or open evidence gap. | System 2 requirement for DE4SDV evidence discipline. |
| REQ-AEBS-005 | The AEBS feature increment shall record regulatory source assumptions and status for each regulatory constraint used. | Prevents hidden compliance claims. |

## Candidate architecture elements

Functional candidates:

- perceive forward environment,
- track relevant objects,
- assess collision risk,
- decide warning/braking intervention,
- command braking,
- notify driver,
- log evidence-relevant event data.

Logical candidates:

- ForwardPerceptionService,
- ObjectTrackingService,
- CollisionRiskAssessment,
- AEBSDecisionManager,
- BrakeCommandInterface,
- DriverWarningInterface,
- EvidenceLogger.

Physical/software candidates are deferred until a later increment.

## Candidate verification and evidence

| Evidence area | Candidate artifact |
|---|---|
| Requirements quality | requirements review checklist |
| Scenario coverage | AEBS scenario catalog stub |
| Model traceability | traceability YAML/table |
| Functional behavior | simulation or test-case placeholder |
| Interface behavior | brake-command and warning-interface test placeholder |
| Regulatory alignment | clause/source mapping with status field |

Evidence statuses should use explicit labels such as `draft`, `planned`, `simulated`, `tested`, `reviewed`, or `accepted`. Do not use `certified` or `compliant` without formal basis.

## First deliverables after this charter

Recommended next increment:

1. create AEBS traceability YAML using the basic ontology terms,
2. register candidate AEBS terms and source references,
3. draft the first operational context and scenario view,
4. only then add SysML v2 context/requirements artifacts with validation evidence.

## Exit criteria for the pilot

The pilot is useful if it proves:

- the generic increment workflow works for a real SDV feature slice,
- SAF viewpoint selection is lightweight and reviewable,
- feature/common-capability classification prevents terminology drift,
- requirements and evidence links can be represented before detailed architecture,
- open compliance gaps are visible rather than hidden.
