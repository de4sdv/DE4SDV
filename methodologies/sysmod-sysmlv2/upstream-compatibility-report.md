# Draft upstream compatibility report: SYSMOD Sysand package

Status: **draft; not sent upstream**

## Purpose

DE4SDV proposes to consume `pkg:sysand/mbse4u/sysmod` through an exact-pinned
Sysand dependency and a narrow local adapter. Before relying on more than the
selected adapter seams, DE4SDV should confirm the observations below with the
upstream maintainer.

## Intended DE4SDV integration

DE4SDV intends to:

- resolve the package through Sysand rather than vendor `SYSMOD.sysml`;
- expose local seams for `ExtendedStakeholder`, `ExtendedRequirement`,
  `SystemUseCase`, and `ConstrainedOccurrence`;
- keep SAF concerns, viewpoints, and Operational/Conceptual/Physical domains;
- keep the DE4SDV 13-phase increment workflow, product-line engineering, and
  evidence lifecycle; and
- avoid adopting `Project` as the DE4SDV root until its context and architecture
  ownership has been reconciled with those structures.

## Candidate upstream findings

These are review questions, not confirmed defects.

### 1. Requirement-boilerplate package spelling

The packaged source declares `RequirementBoilderplates`, while accompanying
package material refers to requirement boilerplates with the conventional
spelling. Is the declaration name intentional and stable API, or should clients
expect it to change?

DE4SDV disposition: do not import this package through the adapter.

### 2. Minimum-value constraint direction

`MinValue` describes a lower bound but constrains `minValue > currentValue`.
That expression appears to accept a current value below the minimum. Should the
relation be reversed or is the prose describing a different intended rule?

DE4SDV disposition: do not use this constraint.

### 3. Availability threshold type

`MinAvailability` compares the ratio `uptime / totalTime` with
`minAvailability`, but the threshold is typed as a duration. Is the threshold
intended to be dimensionless?

DE4SDV disposition: do not use this constraint.

### 4. AI project context references

`AIProject` guidance refers to a `solutionContext`, while the current `Project`
structure exposes the specification and architecture contexts directly. Which
context chain should a consumer treat as current?

DE4SDV disposition: do not adopt `AIProject` or execute embedded prompt text.

## Questions for the maintainer

1. Are the four observations above known or intentional?
2. Which definitions are intended as stable extension points for downstream
   method adapters?
3. Is specialization of `ExtendedStakeholder`, `ExtendedRequirement`,
   `SystemUseCase`, and `ConstrainedOccurrence` the recommended reuse pattern?
4. Is `Project` intended to support product-line programs with multiple member
   products, or should downstream methods define a separate program/increment
   root?
5. Is a trace-based crosswalk—rather than semantic aliases—between SYSMOD
   architecture artifacts and external architecture-framework domains the
   expected integration approach?

## Reproduction boundary

The observations come from the package source resolved by:

```text
sysand sync
.sysand/lib/mbse4u-sysmod_5.1.1/SYSMOD.sysml
```

DE4SDV should update this report if the locked package changes. No public issue,
post, or message should be sent without maintainer approval of the wording.
