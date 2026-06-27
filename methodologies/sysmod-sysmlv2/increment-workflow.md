# Generic Increment Workflow

This workflow turns the SYSMOD/SysML v2 method reference into a repeatable DE4SDV contribution pattern. It is generic: it can be used for a project-level System 2 increment, a product-line feature such as AEBS, a toolchain integration, or an evidence/assurance increment.

## Purpose

Each increment should answer one engineering question and leave behind reviewable artifacts. The workflow deliberately separates method, semantics, architecture views, and publication:

```text
SAF viewpoints        -> what concerns/views must be addressed
SYSMOD method flow    -> how modeling proceeds from context to architecture
DE4SDV ontology       -> what concepts and trace links mean
SysML v2 / Markdown   -> reviewable expression of the model and rationale
GitHub PR             -> reviewed publication baseline
```

## Increment entry criteria

Before starting an increment, define:

- increment name and owner,
- decision or engineering question,
- system/product-line scope,
- stakeholder concerns,
- selected SAF viewpoints,
- expected artifacts,
- out-of-scope boundaries,
- validation/review evidence expected for the PR,
- lifecycle decision to be supported by the increment.

If these cannot be stated, the increment is not ready.

## Workflow phases

| Phase | Question | SAF domain | Main outputs |
|---|---|---|---|
| 0. Increment framing | What are we changing or learning? | Common | increment charter, scope, assumptions |
| 1. Concern framing | Who cares and why? | Common / Operational | stakeholders, concerns, viewpoint selection |
| 2. Operational context | What happens in the world? | Operational | context, actors, scenarios, operational processes |
| 3. Capability / feature semantics | Is this a feature, common capability, constraint, or evidence capability? | DE4SDV ontology | feature/common-capability classification, variation points |
| 4. Needs | What stakeholder needs exist and how will the needs be validated? | Operational | needs, sources, rationale, validation intent |
| 5. Requirements | What shall the system or product line do and how will those requirements be verified? | Functional | design input requirements, constraints, verification methods, trace links |
| 6. Functional architecture | What functions, flows, states, and interfaces are needed? | Functional | functional breakdown, interfaces, behavior slices |
| 7. Logical architecture | What logical elements realize the functions? | Logical | logical structure, exchanges, allocation/mapping |
| 8. Physical / software realization | What software, hardware, deployment, or tool elements realize the logical design? | Physical | physical/software structure, interfaces, mappings |
| 9. Variability and configuration | How does this vary across member products or configurations? | DE4SDV product-line layer | variation points, feature configurations, applicability |
| 10. V&V and evidence | How will requirement satisfaction and stakeholder fitness-for-use be checked? | Common / Functional | verification cases, validation scenarios, acceptance criteria, evidence records, open gaps |
| 11. Publication | What is reviewable now? | DE4SDV workflow | SysML v2, Markdown, YAML, generated views, reports, PR |
| 12. Baseline and next slice | What is accepted, deferred, or invalidated? | Common | baseline decision, open issues, next increment |

## Increment sizes

Use the smallest size that produces useful evidence:

| Size | Meaning | Typical artifacts |
|---|---|---|
| XS | one correction or trace link | one file/snippet, short rationale |
| S | one feature/scenario/context slice | charter + one or two model/docs artifacts |
| M | cross-viewpoint increment | context + requirements + architecture + evidence links |
| L | end-to-end feature baseline | multiple views, model packages, evidence, generated artifacts |

Default to **S** until the method proves stable.

## Lifecycle decision framing

Every increment should state the lifecycle decision it supports. Examples:

- accept a stakeholder need as in scope,
- approve a requirement as a design input,
- select or defer a product-line feature,
- accept an architecture allocation,
- accept a verification result as evidence,
- baseline or reject a generated view/model artifact.

This keeps the method from producing decorative diagrams with no decision value.

## Required trace chain

Every substantial increment should try to establish this chain, even if some links are draft:

```text
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

If a link is intentionally missing, record the gap instead of hiding it.

## Needs, requirements, verification, and validation

Do not collapse these into one list. DE4SDV increments must keep the distinctions explicit:

| Concept | DE4SDV meaning | Typical question |
|---|---|---|
| Need | stakeholder problem-space intent | Is this what the stakeholder needs in context? |
| Requirement | verifiable design-input obligation or constraint | Can the system/design satisfy this? |
| Verification case | planned or executed check of requirement satisfaction | Did we build/specify it right? |
| Validation scenario | check of stakeholder fitness-for-use in context | Did we address the real need? |
| Acceptance criterion | condition for accepting a result or artifact | What outcome is enough to accept this? |
| Evidence artifact | reviewable result supporting a decision | What can reviewers inspect? |
| Gap | known missing link, uncertainty, or unproven claim | What must not be treated as complete yet? |

For early increments, a planned verification/validation record is acceptable. Hiding that it is only planned is not.

## Feature/common-capability rule

A characteristic is a DE4SDV **feature** only when it distinguishes at least one member product from another member product in the product line. If all member products have it, model it as a **common product-line capability**, not as a feature.

For example, an AEBS pilot might classify:

- baseline forward collision risk mitigation as a common capability if every member product has it,
- VRU detection support as a feature if only selected variants provide it,
- performance level or sensor package as variation points if they differ by configuration.

## Evidence status vocabulary

Use explicit evidence status values:

| Status | Meaning |
|---|---|
| `draft` | proposed and not reviewed |
| `planned` | intended but not executed |
| `simulated` | produced by simulation under stated assumptions |
| `tested` | produced by an executed test under stated conditions |
| `inspected` | reviewed by inspection/checklist |
| `analyzed` | supported by analysis/model calculation |
| `accepted` | accepted for the stated baseline or decision |
| `rejected` | reviewed and not accepted |
| `gap` | deliberately recorded missing evidence or trace link |

Avoid `certified`, `compliant`, or `approved` unless the responsible authority and scope are explicit.

## Review questions

Each increment PR should answer:

- What engineering question does this increment answer?
- Which SAF viewpoints were selected and why?
- Which stakeholder concerns are addressed?
- What is explicitly out of scope?
- Are needs separated from requirements?
- Are features separated from common capabilities?
- What trace links exist and what gaps remain?
- What verification method, validation scenario, acceptance criterion, and evidence status are recorded?
- Are compliance/certification claims avoided or clearly marked as not yet established?

## Publication rule

Generated views, reports, and model snapshots are publication artifacts. They are not automatically evidence of correctness. Each artifact must have enough metadata to show:

- source model or source document,
- generation command or manual source,
- date or baseline reference,
- known limitations,
- reviewer expectations.
