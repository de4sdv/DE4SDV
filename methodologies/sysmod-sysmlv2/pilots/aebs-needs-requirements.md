# AEBS Needs and Draft Requirements

## Status

Draft needs and requirements increment for `INC-AEBS-003`. This is not a functional design, VSS mapping, system architecture, test procedure, or UNECE R152 compliance/type-approval claim. UNECE R152 is treated here as a regulatory driver for the common AEBS capability, not as fulfilled evidence.

## Purpose

This increment turns the accepted AEBS operational slice into a small problem-statement, needs, and draft design-input requirements baseline.

The intent is to create the bridge:

```text
operational story
  -> problem statement / system context
  -> stakeholder needs
  -> draft design-input requirements
  -> V&V planning fields
  -> explicit gaps
```

Functional decomposition and VSS signal selection start only in the next increment.

## Problem statement

This increment adapts the SYSMOD/SysML v2 problem-statement pattern into a DE4SDV method context. It does not implement or vendor the full upstream method library.

> How can DE4SDV define an AEBS needs and draft requirements baseline for the SDV product-line common AEBS capability required across member products that preserves the vehicle-target collision-risk mitigation intent, keeps operational boundaries and regulatory assumptions visible, and exposes requirement quality gaps without claiming functional realization, VSS signal mapping, or UNECE R152 compliance/type-approval fulfillment?

The SysML v2 model represents this as a `ProblemStatement` requirement inside a DE4SDV `SystemContext` with stakeholder roles and the SDV product line as the system of interest for this common-capability slice.

## Scope

### In scope

- Product-line common AEBS capability need.
- Vehicle-target rear-end in-lane collision risk slice.
- Draft design-input requirement candidates.
- Requirement quality findings.
- Verification and validation planning fields.
- Initial SysML v2 requirements model slice.

### Out of scope

- Quantified speed, distance, TTC, or deceleration thresholds.
- VSS signal selection or mapping.
- Functional decomposition.
- Logical or physical/software realization.
- UNECE R152 clause-level compliance interpretation.
- Certification, homologation, or type-approval claim.

## Controlled set partition

The baseline is partitioned by responsible system and one entity per set. Product-line needs, member-product needs, member-product design inputs, and obligations on the DE4SDV AEBS increment are controlled separately. System 2 visibility or evidence-governance needs are not parents of System 1 product behavior.

| Set | System | Controlled members |
|---|---|---|
| `SET-AEBS-S1-NEEDS` | System 1 product-line needs | `N-AEBS-001`, `N-AEBS-006`, `N-AEBS-007` |
| `SET-AEBS-S1-MEMBER-NEEDS` | System 1 member-product needs | `N-AEBS-008` |
| `SET-AEBS-S1-REQS` | System 1 product requirements | `REQ-AEBS-001`–`REQ-AEBS-005`, `REQ-AEBS-008`–`REQ-AEBS-015` |
| `SET-AEBS-S2-NEEDS` | System 2 engineering-assurance needs | `N-AEBS-002`–`N-AEBS-005` |
| `SET-AEBS-S2-REQS` | System 2 engineering-assurance requirements | `REQ-AEBS-006`, `REQ-AEBS-007`, `REQ-AEBS-S2-001` |

## Needs baseline

### System 1 product stakeholder needs

| ID | Stakeholder | Need |
|---|---|---|
| `N-AEBS-001` | road users and vehicle occupants | Road users and vehicle occupants need the SDV product line to define AEBS as a common capability required across member products to reduce forward rear-end in-lane collision risk with a vehicle target under defined operating conditions. |
| `N-AEBS-006` | pedestrians | Pedestrians need the SDV product line to provide a common AEBS capability that reduces forward collision risk with a pedestrian target under controlled applicable operating conditions. |
| `N-AEBS-007` | cyclists | Cyclists need the SDV product line to provide a common AEBS capability that reduces forward collision risk with a bicycle target under controlled applicable operating conditions. |
| `N-AEBS-008` | road users and vehicle occupants | Road users and vehicle occupants need each SDV product-line member product to manage AEBS degradation so that behavior remains bounded and AEBS availability is apparent when required inputs or AEBS functions are not healthy. |

### System 2 engineering-assurance needs

| ID | Stakeholder | Need |
|---|---|---|
| `N-AEBS-002` | systems engineer | Systems engineers need the DE4SDV AEBS increment to keep its operational boundary, assumptions, source constraints, and out-of-scope cases explicit while draft requirements are derived. |
| `N-AEBS-003` | product-line engineer | Product-line engineers need the DE4SDV AEBS increment to keep AEBS classified as a product-line common capability, with native SysML v2 variation and variant choices modeled separately. |
| `N-AEBS-004` | compliance engineer | Compliance engineers need the DE4SDV AEBS increment to keep regulatory assumptions, source references, and open interpretation gaps visible without implying UNECE R152 compliance or type approval. |
| `N-AEBS-005` | verification engineer | Verification engineers need the DE4SDV AEBS increment to maintain a separate, controlled V&V planning attachment for each draft AEBS requirement without changing the product obligation. |

## Requirement quality gate

The statements below are **requirement candidates**, not accepted design-input requirements.

They preserve the trace chain from the operational story, but several still fail or defer quality checks from the requirements-writing rule set:

- explicit operating conditions are missing;
- quantitative ranges/thresholds are missing;
- warning and braking timing are not yet measurable;
- temporal dependencies are not yet explicit;
- failure-handling success criteria are not yet defined;
- verification success criteria are still mostly `TBD`;
- satisfaction is intentionally deferred until a functional/logical realization model contains concrete satisfying features.

Promotion rule: a candidate can become an accepted design-input requirement only after the relevant rule findings are closed or explicitly accepted with rationale.

## Draft requirement candidates baseline

Normative requirement expressions are listed independently from V&V methods, criteria, and evidence status. All split product records remain `draft_requirement_with_gap`; the split does not settle applicability, thresholds, timing, authority, or response mappings.

### System 1 product design inputs

| ID | Type | Candidate requirement |
|---|---|---|
| `REQ-AEBS-001` | functional | Each SDV product-line member product shall realize the common AEBS capability by detecting imminent forward collision risk with a vehicle target under selected operating conditions. |
| `REQ-AEBS-002` | functional | Each SDV product-line member product shall realize the common AEBS capability by providing a collision warning to the driver when selected warning conditions are met. |
| `REQ-AEBS-003` | functional | Each SDV product-line member product shall realize the common AEBS capability by commanding emergency braking when selected activation conditions are met and no overriding condition prevents intervention. |
| `REQ-AEBS-004` | functional | When a valid, fresh, and unambiguous driver input is classified as a conscious override under controlled override criteria during AEBS intervention, each SDV product-line member product shall apply the intervention response selected by the controlled override-response mapping. |
| `REQ-AEBS-005` | safety constraint | Under controlled failure-detection criteria, each SDV product-line member product shall detect AEBS-related failure conditions. |
| `REQ-AEBS-008` | safety constraint | When controlled non-activation criteria determine that imminent forward collision risk is absent under defined operating conditions, each member product shall not issue an AEBS collision warning. |
| `REQ-AEBS-009` | safety constraint | When a required AEBS input is unhealthy under controlled input-health criteria, each member product shall enter the AEBS state selected by the controlled degraded-state mapping. |
| `REQ-AEBS-010` | functional | Each member product shall detect imminent forward collision risk with a pedestrian target under controlled applicable pedestrian-target operating conditions. |
| `REQ-AEBS-011` | functional | Each member product shall detect imminent forward collision risk with a bicycle target under controlled applicable bicycle-target operating conditions. |
| `REQ-AEBS-012` | safety constraint | When controlled non-activation criteria determine that imminent forward collision risk is absent under defined operating conditions, each member product shall not command AEBS emergency braking. |
| `REQ-AEBS-013` | safety constraint | When a required AEBS input is unhealthy under controlled input-health criteria, each member product shall provide the status indication selected by the controlled degraded-state indication mapping. |
| `REQ-AEBS-014` | functional | Under controlled applicable pedestrian-target operating conditions, each member product shall apply the controlled AEBS response to classified pedestrian-target collision risk. |
| `REQ-AEBS-015` | functional | Under controlled applicable bicycle-target operating conditions, each member product shall apply the controlled AEBS response to classified bicycle-target collision risk. |

`REQ-AEBS-004` now has one response-selection obligation. Its controlled override-response mapping is still a blocker: no suppress/release selection is invented here.

### System 2 engineering-assurance design inputs

| ID | Type | Candidate requirement |
|---|---|---|
| `REQ-AEBS-006` | product-line model constraint | The DE4SDV AEBS increment shall keep common-capability, feature, and native SysML v2 variation and variant classifications explicit for each AEBS behavior or scope element in its model baseline. |
| `REQ-AEBS-007` | assurance traceability constraint | The DE4SDV AEBS increment shall maintain separate trace links from each draft AEBS requirement to its source, stakeholder need, unresolved gaps, validation reference, and controlled V&V planning attachment. |
| `REQ-AEBS-S2-001` | evidence-contract traceability constraint | The DE4SDV AEBS increment shall maintain trace links from each AEBS evidence contract to its controlled operational boundary, assumptions, source constraints, and exclusions. |

The pedestrian and bicycle records are distinct candidates; neither reinterprets the retained vehicle-target candidates. Their source link resolves through controlled public-safe metadata for `E/ECE/TRANS/505/Rev.3/Add.151/Rev.2`. Applicability remains candidate-only, and target definitions, conditions, response criteria, tolerances, and uncertainty remain gaps.

## Quantified regulatory candidate control

No quantified regulatory System 1 candidate is added in this increment. The repository now controls an exact public-safe source identity, revision, digest, and selected clause anchors. It does not establish vehicle-category applicability, amendment-selection rationale, authority interpretation, full tolerance treatment, measurement uncertainty, or promotion into product obligations. Quantified candidates are therefore deferred rather than invented.

## Traceability matrix

| Need | System | Derived requirements | Validation reference |
|---|---|---|---|
| `N-AEBS-001` | System 1 | `REQ-AEBS-001`, `REQ-AEBS-002`, `REQ-AEBS-003`, `REQ-AEBS-004`, `REQ-AEBS-008`, `REQ-AEBS-012` | `VAL-AEBS-001` |
| `N-AEBS-002` | System 2 | `REQ-AEBS-S2-001` | `VAL-AEBS-002` |
| `N-AEBS-003` | System 2 | `REQ-AEBS-006` | `VAL-AEBS-003` |
| `N-AEBS-004` | System 2 | `REQ-AEBS-007` | `VAL-AEBS-004` |
| `N-AEBS-005` | System 2 | `REQ-AEBS-007` | `VAL-AEBS-005` |
| `N-AEBS-006` | System 1 | `REQ-AEBS-010`, `REQ-AEBS-014` | `VAL-AEBS-006` |
| `N-AEBS-007` | System 1 | `REQ-AEBS-011`, `REQ-AEBS-015` | `VAL-AEBS-007` |
| `N-AEBS-008` | System 1 | `REQ-AEBS-005`, `REQ-AEBS-009`, `REQ-AEBS-013` | `VAL-AEBS-008` |

`N-AEBS-002` traces only to the System 2 evidence-contract baseline obligation. It is not a parent of `REQ-AEBS-004` or any other System 1 product requirement. Likewise, `N-AEBS-004` is not a parent of degraded product behavior.

## V&V planning attachments

Methods, candidate criteria, and evidence status are maintained in the separate `verification_planning` section of the YAML artifact. They do not form part of the normative requirement statements. All unsettled criteria remain explicit gaps; this increment assigns no pass result or product compliance conclusion.

| ID | Validates | Method | Question |
|---|---|---|---|
| `VAL-AEBS-001` | `N-AEBS-001` | stakeholder scenario review | Do the draft requirements preserve the stakeholder-visible vehicle-target collision-risk mitigation intent without exceeding the operational slice? |
| `VAL-AEBS-002` | `N-AEBS-002` | inspection | Are assumptions and out-of-scope cases still visible after requirements are derived? |
| `VAL-AEBS-003` | `N-AEBS-003` | inspection | Does the requirement set keep AEBS framed as product-line common capability while deferring variable realization choices to native SysML v2 variation and variant modeling? |
| `VAL-AEBS-004` | `N-AEBS-004` | inspection | Are regulatory assumptions traceable without compliance wording or copied source text? |
| `VAL-AEBS-005` | `N-AEBS-005` | inspection | Does every requirement have a separate controlled V&V planning attachment and visible unresolved criteria gaps? |
| `VAL-AEBS-006` | `N-AEBS-006` | pedestrian stakeholder and applicability review | Does the pedestrian candidate preserve distinct intent without importing vehicle criteria or implying regulatory acceptance? |
| `VAL-AEBS-007` | `N-AEBS-007` | cyclist stakeholder and applicability review | Does the bicycle candidate preserve distinct intent without importing vehicle criteria or implying regulatory acceptance? |
| `VAL-AEBS-008` | `N-AEBS-008` | road-user and vehicle-occupant safety/availability review | Do degraded-state and indication candidates preserve System 1 intent without importing System 2 evidence governance? |

## Known requirement gaps

| ID | Gap |
|---|---|
| `GAP-AEBS-REQ-001` | Selected operating conditions remain undefined. |
| `GAP-AEBS-REQ-002` | Vehicle-target detection criteria remain undefined. |
| `GAP-AEBS-REQ-003` | Collision-warning timing, modality, and observability criteria remain undefined. |
| `GAP-AEBS-REQ-004` | Emergency-braking activation conditions and braking demand profile remain undefined. |
| `GAP-AEBS-REQ-005` | Non-activation and false-reaction constraints remain undefined. |
| `GAP-AEBS-REQ-006` | Conscious driver override inputs and resulting behavior remain undefined. |
| `GAP-AEBS-REQ-007` | AEBS failure detection, indication, and safe-operation criteria remain undefined. |
| `GAP-AEBS-REQ-008` | Native SysML v2 variation and variant choices are not yet modeled; they must not weaken the common AEBS capability obligation across member products. |
| `GAP-AEBS-REQ-009` | VSS signal candidates are intentionally deferred until the functional-interface increment. |
| `GAP-AEBS-REQ-010` | Requirement satisfaction remains deferred until concrete satisfying features exist. |
| `GAP-AEBS-REQ-011` | Complete non-activation scenarios, observation windows, classification rules, and false-reaction tolerances remain undefined. |
| `GAP-AEBS-REQ-012` | Degraded/unavailable state ownership, transition timing, indication behavior, and safe-operation response remain undefined. |
| `GAP-AEBS-REQ-013` | Source identity is controlled, but amendment-selection rationale, vehicle-category applicability, and authority interpretation remain unresolved. |
| `GAP-AEBS-REQ-014` | Promotion of quantified thresholds into System 1 obligations, complete tolerance treatment, uncertainty, and repetition interpretation are deferred. |
| `GAP-AEBS-REQ-015` | Pedestrian target definition, conditions, response criteria, and applicability remain unresolved. |
| `GAP-AEBS-REQ-016` | Bicycle target definition, conditions, response criteria, and applicability remain unresolved. |

## Requirement quality findings

| ID | Severity | Finding |
|---|---|---|
| `QF-AEBS-REQ-001` | expected gap | Several requirements are not yet quantitatively verifiable because scenario parameters and thresholds are deferred. |
| `QF-AEBS-REQ-002` | controlled scope | Vehicle, pedestrian, and bicycle target candidates remain separate; none borrows another target class's criteria. |
| `QF-AEBS-REQ-003` | controlled scope | Requirements avoid VSS signal names until functional interfaces are modeled. |
| `QF-AEBS-REQ-004` | controlled scope | Regulatory alignment is captured as a source constraint, not as compliance evidence. |
| `QF-AEBS-REQ-005` | correction | SysML v2 model representation must use native requirement definitions/usages rather than modeling requirements only as generic parts. |

## SysML v2 model artifact

```text
textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml
```

The SysML v2 slice models the adapted DE4SDV method context, problem statement, stakeholder needs, and draft requirements with native SysML v2 constructs. Stakeholder needs are specified only as requirement-like usages typed by `StakeholderNeedCandidate` specializations; they are not duplicated as concerns. Stakeholder parameters use shared DE4SDV stakeholder role definitions, draft requirements carry required constraint bodies, and satisfaction links are intentionally deferred until a later functional/logical realization model contains concrete satisfying features. V&V planning, evidence status, gaps, and quality findings remain in the Markdown/YAML reviewer artifacts for this PR; they are not modeled as generic SysML part taxonomies in the needs/requirements slice. The slice intentionally does not introduce functional decomposition or VSS signal references.

## Acceptance criteria

This increment is acceptable if:

- a DE4SDV method-context problem statement anchors the needs/requirements slice;
- needs remain separate from design-input requirements;
- AEBS remains framed as an SDV product-line common capability required across member products;
- each draft requirement traces to its need and gaps while V&V methods, criteria, and evidence status remain separate planning attachments;
- requirements do not introduce VSS signal mappings, functional decomposition, logical realization, or compliance claims;
- the SysML v2 requirements slice uses native requirement definitions/usages for needs and requirement candidates;
- the model avoids satisfaction assertions until concrete satisfying features exist;
- the SysML v2 requirements slice is present for privileged Syside validation after integration.

## Next increment

`INC-AEBS-004` — AEBS functional behavior and VSS signal candidates.

Entry condition: this draft needs and requirements baseline is reviewed and accepted as sufficient basis for functional modeling.
