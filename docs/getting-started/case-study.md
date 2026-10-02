# DE4SDV through one case study

DE4SDV helps engineers keep a vehicle's design, software choices, tests, and
supporting evidence connected when the vehicle changes. We build an open
engineering reference, not a production car or a certificate.

Start with the story below. Then follow the engineering workflow or pick a
small contribution. You do not need to know SysML or install tools to read it.

## 1. The problem, the case, and the solution

### The problem: a change is bigger than a code change

Imagine changing the software or computing platform in a vehicle. A build can
pass while the behavior, interfaces, or assumptions behind earlier tests have
changed. Engineers need to answer: **what changed, which vehicle versions are
affected, and what must be checked again?**

DE4SDV's answer is to keep the intended behavior, requirements, design choices,
implementation, and test evidence connected and under review. A missing test
or unresolved assumption should be visible, not mistaken for proof.

### The case: emergency braking behind another vehicle

A vehicle is traveling in the same lane behind another vehicle. The distance
closes and a collision becomes imminent. The intended behavior is to detect
the risk, warn the driver when required, and request emergency braking when
the activation conditions are met. Driver override and failure handling are
separate paths that also need defined conditions and evidence.

This is the vehicle-target **Advanced Emergency Braking System (AEBS)** case.
The [operational story](../../methodologies/sysmod-sysmlv2/pilots/aebs-operational-story.md)
records the situation; it is not a report that a real vehicle passed a test.

The initial product line has two planned reference members — related vehicle
versions whose shared design is managed together:

- **Standalone Autoware AEBS Reference Member** — the standalone alternative.
- **AAOS-Integrated Autoware AEBS Reference Member** — the alternative integrated
  with Android Automotive OS (AAOS).

Both share vehicle-target AEBS and Autoware, the driving-software stack used
by the reference. The admitted product difference is **Vehicle Platform
Integration Mode: Standalone or AAOS Integrated**. Emergency braking is common
to both, not an optional feature in this scope. Planned membership does not
mean both implementations have the same test maturity. See the
[governed scope decision](../architecture-decisions/0014-ratify-initial-aebs-product-line-scope.md)
for the boundaries; other stacks mentioned in the repository are not thereby
selectable members of this portfolio.

### The solution: an engineering thread, not just a braking demo

The case tests whether we can follow one connected thread:

**Road-user need → requirement → design → configured member → implementation
→ verification case and evidence.**

One concrete example is the emergency-braking request:

| Step | What to look for |
|---|---|
| Need | `N-AEBS-001`: road users and occupants need reduced vehicle-target collision risk. |
| Candidate requirement | `REQ-AEBS-003`: command emergency braking under defined activation and override conditions. |
| Modeled responsibility | `requestBraking`: the functional action to which that candidate requirement traces. |

Read the [needs and requirements](../../methodologies/sysmod-sysmlv2/pilots/aebs-needs-requirements.md),
then find `reqCommandEmergencyBraking` and its candidate trace in the
[requirements model](../../textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml).
The [functional model](../../textual-notation-of-model/packages/features/aebs/aebs_functional_architecture.sysml)
defines `requestBraking`. This trace records design intent, not requirement
satisfaction or verification; the candidate's verification status is
`NotStarted`.

The
[nominal moving-target bench](../../implementation/aebs-autoware-nominal-vehicle-target-bench/README.md)
provides bounded, replayable evidence for a configured simulation chain.
These are connected engineering artifacts, not proof that the candidate product
requirement is satisfied.

The vehicle versions are what we study (**System 1**). The models, tools,
processes, and evidence workflow we build are the engineering system
(**System 2**). Contributors, maintainers, and upstream communities evolve it
(**System 3**). The [project charter](../project-goals/project-charter.md)
defines the broader mission.

### What is demonstrated, and what is not

The repository contains models, reference implementations, automated checks,
and retained evidence with different maturity levels. The moving-target bench
supports a narrow simulation claim; its evidence boundary excludes conscious
driver override, false-reaction and degraded-operation matrices, pedestrian
and bicycle behavior, and real-vehicle brake performance. Other increments
must be judged by their own evidence, not this bench's result.

No example establishes vehicle safety, regulatory compliance, certification,
homologation, or type approval. Check the owning artifact's status and
[evidence rules](../evidence-management.md), not just whether a file exists.
The [roadmap](../../ROADMAP.md) separates active work from broader ambitions.

## 2. How a change travels through the engineering workflow

SysML v2 is the modeling language used to record the system's requirements,
structure, behavior, and relationships. The model is the design reference;
implementation should reflect it, not quietly define a different system.

1. **Frame the change.** State the user problem, affected member, operating
   conditions, and what is outside scope. For AEBS, a moving vehicle target is
   not interchangeable with a pedestrian or bicycle target.
2. **Update the connected artifacts.** Keep the story, requirements, model,
   configuration, implementation, and verification plan consistent. Record
   missing criteria as gaps rather than inventing thresholds or pass results.
3. **Submit a focused pull request (PR).** A PR is a proposed change for review,
   not an accepted baseline. Link the issue and explain the intended result.
4. **Run automated checks and obtain the relevant validation.** Fix failures;
   keep model validation and runtime evidence separate, as described below.
5. **Review and baseline.** An independent reviewer checks the change and its
   claim boundaries; maintainers decide whether to merge it. Preserve the
   exact revision and evidence needed to reproduce a result.
6. **Publish separately.** Viewer/API publication makes a revision inspectable.
   It does not approve the vehicle design or turn a simulation into road-test
   evidence.

### A first look at the model

**Question: which responsibilities does the vehicle-target AEBS model name?**

![SysIDE view listing the AEBS functional responsibilities](../../textual-notation-of-model/packages/features/aebs/diagrams/diagram-aebsFunctionalArchitectureView.svg)

Look for `assessRisk` (assess collision risk), `requestWarning` (request a
driver warning), and `requestBraking` (request emergency braking). This existing
SysIDE view lists responsibilities and information items; it does not show
their execution order or prove their implementation. Open the
[original SVG](../../textual-notation-of-model/packages/features/aebs/diagrams/diagram-aebsFunctionalArchitectureView.svg)
at full size, or use the
[AEBS view index](../../textual-notation-of-model/packages/features/aebs/VIEWS.md)
to explore structure, exchanges, and evidence separately.

### CI/CD in plain language

**Continuous integration (CI)** automatically checks a proposed repository
change. The [public CI workflow](../../.github/workflows/ci.yml) checks repository
consistency and local documentation links, restores pinned model dependencies,
runs the complete project test
suite, runs bench unit/contract tests in separate processes, and runs smoke
tests. Bench unit tests do **not** build and execute the vehicle simulation.

For changed SysML models, syntax and semantic validation is a separate gate:
contributors with Syside access can validate locally; otherwise maintainers
run licensed validation after initial review. See the
[contribution guide](../../CONTRIBUTING.md#sysml-v2-validation-gate).
A valid model is not a successfully executed implementation.

**Delivery/deployment (CD)** makes selected outputs available to readers and
tools. The [Pages workflow](../../.github/workflows/deploy-viewer.yml) publishes
the browse-only engineering mirror. The
[public viewer deployment](../../.github/workflows/deploy-public-ask-viewer.yml)
and [API deployment](../../.github/workflows/deploy-public-sysml-api.yml) are
separate, maintainer-triggered workflows bound to exact revisions. A green PR
is not automatically the deployed public baseline.

For diagrams, open the [AEBS views](../../textual-notation-of-model/packages/features/aebs/VIEWS.md)
or the [model viewer](https://viewer.de4sdv.org), following the
[viewer guide](../guides/model-viewer.md). Those diagrams are rendered from the
model with SysIDE, not a parallel hand-drawn architecture.

## 3. Pick a bounded contribution

These are small task proposals, not assignments or a second ticket tracker.
Check [open issues](https://github.com/de4sdv/DE4SDV/issues) and existing PRs
first. Continue an existing issue where it fits; otherwise agree the scope in
an issue before starting. Each task below names a starting point and a result
that can be reviewed.

| Task | Start here | Reviewable result / done when |
|---|---|---|
| Try the newcomer path (documentation) | This page and [#300](https://github.com/de4sdv/DE4SDV/issues/300) | Report confusing passages and propose one focused correction. A reader can answer the four questions below without private project context. |
| Help a first-time GitHub contributor (community/docs) | [#37: GitHub onboarding](https://github.com/de4sdv/DE4SDV/issues/37) and [CONTRIBUTING](../../CONTRIBUTING.md) | Test or improve one step of the issue-to-PR walkthrough; record where a newcomer got stuck and verify the corrected step. Do not duplicate the existing guide proposal. |
| Follow one requirement (systems/traceability) | `REQ-AEBS-003` in the [requirements baseline](../../methodologies/sysmod-sysmlv2/pilots/aebs-needs-requirements.md) and the example above | Review its need, design, verification-plan, and evidence links at one revision. Report a specific broken/missing link or confirm the bounded chain, keeping candidate status and open gaps visible. |
| Check one bench's evidence boundary (verification/software) | [Moving-target bench](../../implementation/aebs-autoware-nominal-vehicle-target-bench/README.md) | Run its documented validator against retained evidence and record revision, command, result, and exclusions. Replaying retained evidence is not a new simulation or vehicle test. |
| Reconcile one evidence-status summary (docs/QA) | [Implementation index](../../implementation/README.md) and [AAOS visualization campaign dispositions](../../implementation/aebs-aaos-sdv-visualization-bench/evidence/010/VIDEO-EVIDENCE-DISPOSITION.md) | Review the index's blanket runtime-pending wording against retained campaign records. Propose one XS correction that links the bounded observations while preserving the deferred safety outcome and non-public media limitations. |

You can begin with reading and feedback; coding is not required. For a change,
follow [CONTRIBUTING](../../CONTRIBUTING.md). The
[getting started guide](README.md) covers repository layout, setup, and checks.

### Does this page work for a newcomer?

After reading it, can you explain:

1. What problem DE4SDV helps engineers solve?
2. What situation the emergency-braking case examines and how its two members differ?
3. Why passing CI or replaying a simulation does not mean a vehicle is certified?
4. Which small task you could take, what you would produce, and how it is checked?

If not, point out the missing explanation in
[#300](https://github.com/de4sdv/DE4SDV/issues/300). Newcomer feedback is part of
validating this guide, not something automated repository tests can prove.
