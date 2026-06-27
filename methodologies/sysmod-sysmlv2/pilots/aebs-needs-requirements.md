# AEBS Needs and Draft Requirements

## Status

Draft needs and requirements increment for `INC-AEBS-003`. This is not a functional design, VSS mapping, logical architecture, test procedure, or UNECE R152 compliance claim.

## Purpose

This increment turns the accepted AEBS operational slice into a small needs and draft design-input requirements baseline.

The intent is to create the bridge:

```text
operational story
  -> stakeholder needs
  -> draft design-input requirements
  -> V&V planning fields
  -> explicit gaps
```

Functional decomposition and VSS signal selection start only in the next increment.

## Scope

### In scope

- Product-line common AEBS capability need.
- Vehicle-target rear-end in-lane collision risk slice.
- Draft design-input requirement candidates.
- Requirement quality findings.
- Verification and validation planning fields.
- Initial SysML v2 requirements model slice.

### Out of scope

- Pedestrian-target requirements.
- Bicycle-target requirements.
- Quantified speed, distance, TTC, or deceleration thresholds.
- VSS signal selection or mapping.
- Functional decomposition.
- Logical or physical/software realization.
- UNECE R152 clause-level compliance interpretation.
- Certification, homologation, or type-approval claim.

## Needs baseline

| ID | Stakeholder | Need |
|---|---|---|
| `N-AEBS-001` | road users and vehicle occupants | Road users and vehicle occupants need the SDV product line to provide a common AEBS capability that reduces forward rear-end in-lane collision risk with a vehicle target across applicable member products under defined operating conditions. |
| `N-AEBS-002` | systems engineer | Systems engineers need the AEBS operational boundary, assumptions, source constraints, and out-of-scope cases to stay explicit while draft requirements are derived. |
| `N-AEBS-003` | product-line engineer | Product-line engineers need AEBS to remain classified as a product-line common capability candidate until member-product applicability and variation points are modeled explicitly. |
| `N-AEBS-004` | compliance engineer | Compliance engineers need regulatory assumptions, source references, and open interpretation gaps to be visible without implying UNECE R152 compliance or type approval. |
| `N-AEBS-005` | verification engineer | Verification engineers need each draft AEBS requirement to carry a planned verification method, validation reference, evidence status, and explicit gap when acceptance criteria are not yet quantified. |

## Draft requirements baseline

| ID | Type | Draft requirement | Verification | Evidence status |
|---|---|---|---|---|
| `REQ-AEBS-001` | functional | Applicable SDV product-line member products shall realize the common AEBS capability by detecting imminent forward collision risk with a vehicle target under selected operating conditions. | analysis | planned |
| `REQ-AEBS-002` | functional | Applicable SDV product-line member products shall realize the common AEBS capability by providing a collision warning to the driver when selected warning conditions are met. | demonstration | planned |
| `REQ-AEBS-003` | functional | Applicable SDV product-line member products shall realize the common AEBS capability by commanding emergency braking when selected activation conditions are met and no overriding condition prevents intervention. | simulation | planned |
| `REQ-AEBS-004` | functional | Applicable SDV product-line member products shall allow conscious driver override of AEBS intervention under defined override conditions. | demonstration | planned |
| `REQ-AEBS-005` | safety constraint | Applicable SDV product-line member products shall support detection or indication of AEBS-related failure conditions without hiding safe-operation concerns. | inspection | gap |
| `REQ-AEBS-006` | product-line constraint | The AEBS model baseline shall keep common-capability, feature, and variation-point classifications explicit for each AEBS behavior or scope element. | inspection | planned |
| `REQ-AEBS-007` | traceability constraint | The DE4SDV AEBS increment shall trace each draft AEBS requirement to its source assumption, stakeholder need, validation reference, planned verification method, evidence status, and unresolved gap when applicable. | inspection | planned |

## Traceability matrix

| Need | Derived requirements | Validation reference |
|---|---|---|
| `N-AEBS-001` | `REQ-AEBS-001`, `REQ-AEBS-002`, `REQ-AEBS-003`, `REQ-AEBS-004`, `REQ-AEBS-005` | `VAL-AEBS-001` |
| `N-AEBS-002` | `REQ-AEBS-004`, `REQ-AEBS-005` | `VAL-AEBS-002` |
| `N-AEBS-003` | `REQ-AEBS-006` | `VAL-AEBS-003` |
| `N-AEBS-004` | `REQ-AEBS-005` | `VAL-AEBS-004` |
| `N-AEBS-005` | `REQ-AEBS-007` | `VAL-AEBS-005` |

## V&V planning

| ID | Validates | Method | Question |
|---|---|---|---|
| `VAL-AEBS-001` | `N-AEBS-001` | stakeholder scenario review | Do the draft requirements preserve the stakeholder-visible vehicle-target collision-risk mitigation intent without exceeding the operational slice? |
| `VAL-AEBS-002` | `N-AEBS-002` | inspection | Are assumptions and out-of-scope cases still visible after requirements are derived? |
| `VAL-AEBS-003` | `N-AEBS-003` | inspection | Does the requirement set keep AEBS framed as product-line common capability before variation modeling? |
| `VAL-AEBS-004` | `N-AEBS-004` | inspection | Are regulatory assumptions traceable without compliance wording or copied source text? |
| `VAL-AEBS-005` | `N-AEBS-005` | inspection | Does every requirement expose V&V planning and unresolved criteria gaps? |

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
| `GAP-AEBS-REQ-008` | Product-line variation points and member-product applicability are not yet modeled. |
| `GAP-AEBS-REQ-009` | VSS signal candidates are intentionally deferred until the functional-interface increment. |

## Requirement quality findings

| ID | Severity | Finding |
|---|---|---|
| `QF-AEBS-REQ-001` | expected gap | Several requirements are not yet quantitatively verifiable because scenario parameters and thresholds are deferred. |
| `QF-AEBS-REQ-002` | controlled scope | Requirements are vehicle-target only; pedestrian and bicycle target requirements must be separate future increments. |
| `QF-AEBS-REQ-003` | controlled scope | Requirements avoid VSS signal names until functional interfaces are modeled. |
| `QF-AEBS-REQ-004` | controlled scope | Regulatory alignment is captured as a source constraint, not as compliance evidence. |

## SysML v2 model artifact

```text
textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml
```

The SysML v2 slice models needs, draft requirements, validation scenarios, verification methods, evidence status, gaps, and acceptance criteria as an initial model backbone. It intentionally does not introduce functional decomposition or VSS signal references.

## Acceptance criteria

This increment is acceptable if:

- needs remain separate from design-input requirements;
- AEBS remains framed as an SDV product-line common capability across applicable member products;
- each draft requirement has derived needs, verification method, validation reference, evidence status, and known gaps;
- requirements do not introduce VSS signal mappings, functional decomposition, logical realization, or compliance claims;
- the SysML v2 requirements slice is present and validated by the available validation path.

## Next increment

`INC-AEBS-004` — AEBS functional behavior and VSS signal candidates.

Entry condition: this draft needs and requirements baseline is reviewed and accepted as sufficient basis for functional modeling.
