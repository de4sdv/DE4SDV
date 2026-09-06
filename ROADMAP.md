# Roadmap

This file names the current project outcomes and release gate. GitHub milestones
and issues carry live work status; this file should not duplicate a ticket list.

## Foundation milestone

The original foundation milestone established the charter, repository
structure, contributor guide, and initial roadmap. Its four issues and the
milestone are closed as **Foundation setup — completed**. It is a historical
planning milestone, not a published release.

DE4SDV has not yet published a tagged release. The next release milestone is
`v0.1.0 — first reviewable engineering baseline`.

## Current outcome goals

### 1. Trustworthy change control

A contributor can identify and claim work, submit a focused pull request,
obtain the appropriate independent review, and find the resulting decision in
the public project record. Administrator review bypasses are exceptional and
recorded rather than treated as the default workflow.

### 2. One coherent engineering thread

At least one reference slice is traversable from mission and scenario through
needs, requirements, conceptual architecture, configuration, realization,
verification, and bounded evidence. AEBS is the first target thread.

### 3. Reproducible public baseline

A clean checkout can run every public project-owned check. Licensed validation
is separately bound to the exact reviewed commit, and published viewer/API
outputs identify their source revision.

### 4. Contributor-usable project surface

Active, incubating, and dormant areas are explicit. Every active increment has
an owner or maintainer decision, a reviewable artifact, and a next action.
New contributors can complete the documented XS/S contribution path without
private project knowledge.

## v0.1.0 release gate

The release candidate must satisfy all of the following at one exact commit:

- repository checks, smoke tests, and the complete project-owned pytest suite
  pass from a clean checkout;
- required SysML v2 validation evidence is bound to the candidate commit;
- open P0/P1 milestone issues are resolved or explicitly deferred with a
  recorded reason;
- active pull requests are triaged and the roadmap and contributor/governance
  documents describe current practice;
- the baseline register identifies the model, implementation assets,
  dependencies, validation evidence, and source commit;
- release notes distinguish demonstrated assets, experimental assets,
  placeholders, and known limitations; and
- no artifact claims certification, homologation, or regulatory approval that
  the evidence does not establish.

## Capability status

| Area | Status | Activation or next gate |
|---|---|---|
| SysML v2 method kernel, product-line model, viewer, and API integration | Active | Keep model, implementation, validation, and publication evidence synchronized |
| AEBS reference thread | Active | Close the end-to-end traceability and exact-head verification gaps |
| Governance, contribution flow, and release management | Active | Adopt independent-review rules and publish the first release baseline |
| Continuous homologation and compliance structure | Incubating | Add reviewed, bounded evidence cases without certification claims |
| DevSecOps security controls | Active | Close the Dependabot, code-scanning, and private-reporting gaps listed in `devsecops/devsecops-roadmap.md` |
| Digital continuity and digital twin | Incubating | Name a concrete decision, owner, data boundary, and verification case |
| Simulation interoperability | Dormant (directory-level) | Activate when an owned FMI/FMU/SSP increment and tool-compatibility assumptions exist; reviewed simulator execution already exists under INC-AEBS-008 and AEBS-009 pilots |
| Standards mapping | Dormant (directory-level) | Activate when a named mapping decision has an owner and review source; the SHA-pinned UN R152 mapping is already reviewed pilot work outside the directory |

Broad capability ambitions are not simultaneous delivery commitments. A
workstream moves to **active** only when it has an owner, a decision or issue,
a maintained artifact, and a verifiable next action.
