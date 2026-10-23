# ADR 0024: Model the program as a release increment

## Status

Proposed

## Context

DE4SDV keeps its systems engineering in the SysML model, and the method
checks it per increment. An increment has a charter with an owner, a size, a
scope and a set of applicable phases. It ends with a phase-12 lifecycle
decision. The Method Check and the semantic MCP (`next`, `gaps`, `status`)
judge it on every pull request.

Program management has no such home. The roadmap names four outcome goals and
the v0.1.0 release gate in prose. Nothing measures the goals, and no increment
says which goal it serves. The technical half of the release gate runs as
`scripts/check_release_evidence.py`. Its other criteria are prose that no
release was checked against. No line in the repository records a program
risk; every "risk" line is about product safety, security or evidence. The
prose also went stale: until pull request #424, the baseline register missed
five production releases.

The kernel already has the constructs that program management needs. A need
states what a stakeholder expects. A requirement derives from a need, and a
verification case verifies it. An increment ends with a lifecycle decision.
The method context has no generic project context by design: increments
compose problem statements, stakeholders and context directly.

Two alternatives were considered:

- **Prose registers and plans.** This is the current state, and it goes stale.
- **New program types**, such as an outcome, a release gate and a program
  risk. They duplicate `Need` and `Requirement`, and they need their own
  checks and roll-up code.

## Decision

1. **Each versioned release is a release increment.** The first one is
   v0.1.0. Its system of interest is `System2EngineeringAndAssuranceSystem`.
   It follows the increment workflow with the applicable phases 0, 4, 5, 10,
   11 and 12.
2. **Roadmap goals are needs.** Each outcome goal is a need of the release
   increment. The need states the goal and how it is measured.
3. **Release-gate criteria are requirements.** Each criterion is a
   requirement that derives from the need it serves and states its success
   criteria.
4. **Checks are verification cases.** The checks that decide a criterion, such
   as CI `checks` and the release evidence, are verification cases. Their run
   records are external evidence (`hasEvidence`).
5. **The release decision is the phase-12 decision.** Go, recycle or no-go for
   the release is the increment's lifecycle decision: accepted, deferred or
   invalidated.
6. **Increments name the goal they serve.** One new relation, with the working
   name `contributesToNeed`, is a native dependency from an increment to a
   program need. It is the only ontology addition.
7. **Program risks start as assumptions and gaps.** A risk is an assumption of
   the release increment. When it is already a shortfall, it is a gap. A risk
   type is added only when a check needs one.
8. **Two named roles.** `GOVERNANCE.md` names the program owner and the chief
   systems engineer. The program owner decides the goals, the priorities and
   the release. The chief systems engineer owns technical coherence and the
   method. One person can hold both roles. In the model, the program owner is
   a stakeholder typed by the kernel's `ProjectManager`.
9. **Identities use a new subject.** The release increment and its records use
   the new registered subject `PROGRAM`, for example `INC-PROGRAM-001`,
   `NEED-PROGRAM-001` and `REQ-PROGRAM-001`.

## Consequences

- One model holds the engineering and the program. The existing checks of
  phases 0, 4, 5 and 10 judge the release increment without new gate code.
  `next` and `gaps` report the program needs and gate criteria that lack
  traces, verification cases or evidence links. Whether a criterion passes
  stays the verdict of its evidence.
- The ontology gains one relation. Its definition, the generated projections
  and the trace vocabulary change in one commit. The semantic authority
  changes, so production serves the relation only after a privileged run and
  a deploy.
- `ProjectManager` gets its first usage.
- An increment that names no program need becomes visible.
- Follow-up work:
  - the method and ontology pull request;
  - the v0.1.0 release increment;
  - a status roll-up per goal in the MCP;
  - a program page in the viewer;
  - ROADMAP generated from the model;
  - the roles text in `GOVERNANCE.md`.
- Program content becomes model content. A program change therefore takes the
  same review and checks as an engineering change.

## Non-decisions

- The measure of each goal, and which gate criterion derives from which goal.
  The release-increment pull request proposes them.
- Whether a missing `contributesToNeed` blocks a phase or only advises.
- A risk type with likelihood and impact.
- The ROADMAP generator and the viewer page.
- Tracking schedule, effort or cost.
- The SYSMOD `Project` concept. DE4SDV keeps declining it as a program root,
  and the upstream question about it stays open.

## Links

- [ADR 0004](0004-adopt-aselcm-three-system-framing.md): the three-system
  framing. The release increment's system of interest is System 2.
- [ADR 0020](0020-give-ontology-definitions-model-resident-kernel-homes.md):
  ontology definitions with kernel homes.
- [ADR 0021](0021-make-model-elements-earn-their-place.md): elements earn
  their place. Decision 7 applies it to risks.
- Pull request #424: the production releases in the baseline register and the
  dated v0.1.0 gate status.
