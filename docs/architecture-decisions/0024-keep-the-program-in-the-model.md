# ADR 0024: Keep the program in the model, with releases as increments

## Status

Proposed

## Context

DE4SDV keeps its systems engineering in the SysML model. An increment has a
charter with an owner, expected artifacts and applicable phases, and its
package owns a scope. The increment ends with a phase-12 lifecycle decision.
The Method Check judges it on every pull request. The semantic MCP answers for
the deployed revision.

Program management has no such home. `ROADMAP.md` names four outcome goals and
the v0.1.0 release gate in prose. `GOVERNANCE.md` §2 lists four other
outcomes. Nothing measures the goals, and no increment names the goal it
serves. CI `checks` and `scripts/check_release_evidence.py` cover the
technical gate criteria; pull request #424 first checked the others by hand.
Program risks exist only as prose, such as the risk table of the PLEML plan.
No model element is typed as a risk. The prose also went stale: until #424,
the baseline register missed five production releases.

A program differs from a project. A program coordinates related work to
deliver goals that no single piece of work delivers alone. Its goals stay the
same during its life, while its components start and finish. A project, here
an increment, is bounded work with a deliverable. A release is such a
component: its deliverable is a baseline, and a gate decides it.

The kernel already has the constructs that program management needs. A need
states what a stakeholder expects. A requirement derives from a need, and a
verification case verifies it. An increment ends with a lifecycle decision.
System 3 governs and evolves System 2 (ADR 0004). The method context has no
generic project context by design.

Three alternatives were considered:

- **Prose registers and plans.** This is the current state, and it goes stale.
- **New program types**, such as an outcome, a release gate and a program
  risk. They duplicate `Need` and `Requirement` and need their own checks.
  Both options need a roll-up per goal.
- **The program as one increment.** Its goals would end with that increment,
  but the goals outlive every release.

## Decision

1. **The program is a package, not an increment.** One enduring program
   package holds the program's goals. Its system of interest is the DE4SDV
   program, a model definition that specializes
   `System3OpenSourceGovernanceEcosystem`.
2. **Goals are needs.** Each roadmap goal is a need in the program package,
   with the program as subject. The measure of a goal is the validation
   scenario that phase 4 asks for.
3. **Each versioned release is a release increment.** The first one is
   v0.1.0. Its system of interest is the program, and its applicable phases
   are 0, 4, 5, 10, 11 and 12. Its charter names the program package, so the
   existing checks evaluate the goal needs in the release's scope.
4. **Gate criteria are requirements.** Each criterion of a release gate is a
   requirement of the release increment. It derives from the goal need it
   serves and states its success criteria. The criteria constrain the release
   decision. Their verification cases test or inspect the System 2 release
   candidate.
5. **The release decision is the phase-12 decision.** Go, recycle or no-go is
   the release increment's lifecycle decision. The decision's doc records the
   value, as `BL-MW-010-P12` does. The maintainer's tag and release record,
   and the deploy approval, carry out the decision.
6. **Increments name the goal they serve.** One new relation, with the working
   name `contributesToNeed`, is a typed connection from an increment to a goal
   need. Its carrier is `IncrementNeedContribution` in
   `DE4SDV_TraceVocabulary`, with a relation record, a vocabulary role and an
   inverse for the roll-up per goal. It records relevance only, not
   satisfaction or progress. It is the only ontology addition.
7. **Risks are assumptions and gaps.** The release increment records the
   condition that a risk threatens as an assumption. A risk still open at the
   release decision is a gap. A risk type is added only when a check needs
   one.
8. **Two named roles.** The program owner is a duty of the lead maintainer.
   The program owner proposes goals and priorities through `GOVERNANCE.md` §7
   and makes the release decision. The chief systems engineer owns technical
   coherence and the method. One person can hold both roles. A stakeholder
   typed by `ProjectManager` carries the owner's concerns, not the authority.
9. **Identities use a new subject.** The program and release records use the
   new registered subject `PROGRAM`, for example `INC-PROGRAM-001` for the
   v0.1.0 release increment, `NEED-PROGRAM-001` and `REQ-PROGRAM-001`.

## Consequences

- One model holds the engineering and the program. The existing checks of
  phases 0, 4, 5 and 10 judge the structure of each release increment and of
  the goal needs its charter names. This needs no new gate code. Phase 4
  requires a planned validation scenario for each goal: its measure.
- No check judges the go/no-go, because phases 11 and 12 have no checks.
  `hasEvidence` is external, so no check reports a missing evidence link.
  Whether a criterion passes stays the verdict of its evidence.
- No check reads `contributesToNeed` yet. Once one does, an increment that
  names no goal becomes visible.
- The ontology gains one relation. Its carrier, its records and the generated
  projections change in one commit. The semantic authority changes, so
  production serves the relation only after a privileged run and a deploy.
- `ProjectManager` gets its first usage.
- Follow-up work:
  - the method and ontology pull request, with the subject registry;
  - the program package and the v0.1.0 release increment;
  - a roll-up per goal in the MCP;
  - a program page in the viewer;
  - ROADMAP generated from the model;
  - the roles text in `GOVERNANCE.md`, with §2 pointing to the goals.
- Program content becomes model content. A program change therefore takes the
  same review and checks as an engineering change.

## Non-decisions

- The measure of each goal, and which gate criterion derives from which goal.
  The program-package pull request proposes them.
- The names of the program definition and the program package.
- Whether a missing `contributesToNeed` blocks a phase or only advises.
- A risk type with likelihood and impact.
- The ROADMAP generator and the viewer page.
- Tracking schedule, effort or cost.
- The SYSMOD `Project` concept. DE4SDV keeps declining it as a program root,
  and the upstream question about it stays open.

## Links

- [ADR 0004](0004-adopt-aselcm-three-system-framing.md): the three-system
  framing. System 3 governs and evolves System 2, so the program specializes
  System 3.
- [ADR 0020](0020-give-ontology-definitions-model-resident-kernel-homes.md):
  ontology definitions with kernel homes.
- [ADR 0021](0021-make-model-elements-earn-their-place.md): elements earn
  their place. Decision 7 applies it to risks.
- Pull request #424: the production releases in the baseline register and the
  dated v0.1.0 gate status.
