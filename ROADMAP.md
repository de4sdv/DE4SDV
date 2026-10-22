# Roadmap

This file names the current project outcomes and release gate. Pull requests
carry live work status. Issues and pull requests carry proposals, questions,
and decisions that need a durable public record. ADRs keep durable outcomes
([GOVERNANCE](GOVERNANCE.md#9-recording-decisions)). This file does not
duplicate a ticket list.

## Foundation milestone

The original foundation milestone established the charter, repository
structure, contributor guide, and initial roadmap. Its four issues and the
milestone are closed as **Foundation setup — completed**. It is a historical
planning milestone, not a published release.

DE4SDV has not yet published a versioned release. The next release milestone is
`v0.1.0 — first reviewable engineering baseline`.

Since 2026-10-11, five production releases have deployed an exact `main`
commit to the public SysML v2 API, viewer, and Ask viewer. The
[baseline register](configuration-management/baseline-register.md#production-releases)
records each one. A production release has no semantic-version tag, so it is
not a versioned release
([release terms](configuration-management/README.md#versioning-and-releases)).

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

### Gate status on 2026-10-22

No v0.1.0 candidate commit exists yet. The table shows what the production
releases already meet.

| Criterion | Status | Evidence |
|---|---|---|
| Checks, smoke tests, and the pytest suite pass from a clean checkout | Met at each production release | CI `checks` passed on push at all five release commits |
| SysML v2 validation evidence is bound to the commit | Met at each production release | One privileged run per release; the baseline register names it |
| Open P0/P1 milestone issues are resolved or deferred | Met | The milestone has one open issue, #37. It has no P0 or P1 label |
| Pull requests are triaged; documents describe current practice | Not met | Open pull requests have no triage record for this gate. The import rehearsal was planned to stop after two releases. It still runs after four |
| The baseline register identifies the release | Partly met | The production releases are recorded. No v0.1.0 row exists |
| Release notes separate demonstrated, experimental, and placeholder assets and limits | Not met | No release notes meet this criterion. The `release-2026-10-15` tag message only lists changes |
| No certification, homologation, or approval claim without evidence | Not checked | No audit for this gate exists yet |

## Capability status

| Area | Status | Activation or next gate |
|---|---|---|
| SysML v2 method kernel, product-line model, viewer, and API integration | Active | Keep model, implementation, validation, and publication evidence synchronized |
| AEBS reference thread | Active | Close the end-to-end traceability and exact-head verification gaps |
| Governance, contribution flow, and release management | Active | Adopt independent-review rules and close the v0.1.0 release gate |
| Continuous homologation and compliance structure | Incubating | Add reviewed, bounded evidence cases without certification claims |
| DevSecOps security controls | Active | Close the Dependabot, code-scanning, and private-reporting gaps listed in `devsecops/devsecops-roadmap.md` |
| Digital continuity and digital twin | Incubating | Name a concrete decision, owner, data boundary, and verification case |
| Simulation interoperability | Dormant (directory-level) | Activate when an owned FMI/FMU/SSP increment and tool-compatibility assumptions exist; reviewed simulator execution already exists under INC-AEBS-008 and AEBS-009 pilots |
| Standards mapping | Dormant (directory-level) | Activate when a named mapping decision has an owner and review source; the SHA-pinned UN R152 mapping is already reviewed pilot work outside the directory |

Broad capability ambitions are not simultaneous delivery commitments. A
workstream moves to **active** only when it has an owner, a decision or issue,
a maintained artifact, and a verifiable next action.
