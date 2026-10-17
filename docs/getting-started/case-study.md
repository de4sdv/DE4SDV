# DE4SDV through one case study

DE4SDV helps engineers build software-defined vehicles from interchangeable
open-source parts and keep the design, configuration choices, tests, and
evidence connected while those parts change. We build an open engineering
reference, not a production car or a certificate.

![Concept illustration, not a model view: four stages from left to right. One SysML v2 model, with requirements, architecture, variability and V&V evidence (existing today), is configured into the member products Autoware · Linux and Autoware · AAOS SDV (existing today). An Autoware · S-CORE candidate is under test outside the member set; only a scope decision can admit it. Every change is re-checked by CI and review, and model changes also by the Method Check (existing today); evidence per member is in progress. The aim is re-checkable evidence for every member and a continuously certifiable product line.](concept-vision-and-aim.drawio.svg)

*Concept illustration, not a model view: the vision at a glance.* DE4SDV
keeps one SysML v2 model for the whole product line, configures each member
product from it, and re-checks changes: CI and review check every change, and
the Method Check also checks model changes. The aim is traceable, re-checkable
evidence for every member; that is what **continuously certifiable SDV product
lines** means here. Green exists today, blue is in progress, yellow is the aim,
and no member is certified.

Start with the story below. Then follow the engineering workflow or pick a
small contribution. You do not need to know SysML or install tools to read it.

## 1. The problem, the case, and the solution

### The problem: many stacks, many combinations, one question

A software-defined vehicle runs a layered software stack. For almost every
layer, several open-source options exist. Picking one per layer gives many
possible vehicles, and each change raises the same questions: **which
combinations actually work together, which vehicle versions are affected, and
what must be checked again?**

DE4SDV's answer is to model the stack and its options explicitly, choose
between them through governed decisions, and keep requirements, design,
implementation, and test evidence connected to each choice. A missing test or
unresolved assumption should be visible, not mistaken for proof.

### The case: a configurable SDV stack

The [platform stack model](../../textual-notation-of-model/packages/architecture/sdv_platform_stack.sysml)
describes six layers. Each layer has a defined boundary to its neighbors, and
most layers have several candidate implementations:

| Layer | What it does | Candidates in the model |
|---|---|---|
| Vehicle application | Domain functions such as driver assistance (perception, planning, control) | Autoware, Openpilot, Apollo |
| Application–middleware adapter | Translates between the application's internal messaging and the vehicle middleware | Derived from the two choices around it, never picked by hand |
| Middleware | Vehicle-level communication, lifecycle, service discovery, diagnostics | Eclipse S-CORE, Android SDV, AUTOSAR Adaptive, or none |
| Operating system | Scheduling, memory, drivers | Linux, Android, QNX |
| Hypervisor | Isolates several operating systems on one chip | KVM, QNX QVM, ACRN, or none |
| Hardware | The compute platform the stack runs on | Kept abstract |

Not every combination is valid. The
[feature catalogue](../../model-based-product-line-engineering/feature-models/sdv_product_line.yaml)
records compatibility rules. For example, rule C001 rejects Eclipse S-CORE on
Android because S-CORE targets Linux and QNX.

### The product line: what the stack can express versus what we govern

A **product line** is a family of related vehicle versions whose shared design
is managed together. Two levels matter, and it is easy to confuse them:

- **What the stack can express.** The catalogue above lists every candidate
  so alternatives can be compared and kept in view.
- **What DE4SDV currently governs.** A
  [reviewed scope decision](../architecture-decisions/0014-ratify-initial-aebs-product-line-scope.md)
  admits exactly two planned reference members. Apollo, Openpilot, Eclipse
  S-CORE, AUTOSAR Adaptive, QNX/QVM, ACRN, and similar options remain
  reference-only or deferred until a future reviewed decision admits a member
  that needs them.

Eclipse S-CORE is the first of those options under test: increment
`INC-MW-011`, in progress, asks whether S-CORE can realize the middleware layer
of a member with Autoware on a Linux host and an Android Automotive OS (AAOS)
guest for the display. Admitting such a member would take a new reviewed scope
decision.

![Concept illustration, not a model view: a shared model holds every option per layer: application Autoware, Openpilot or Apollo; middleware Eclipse S-CORE, Android SDV, AUTOSAR Adaptive or none; operating system Linux, Android or QNX; an adapter derived from application and middleware; and the common vehicle-target AEBS and motion sensors. Bill of features A selects Autoware, no middleware and Linux; bill of features B selects Autoware, Android SDV and Android. The configurator checks the rules, derives the adapter and generates the two members' product models: the standalone member with no adapter and simulation-bench evidence, and the AAOS-integrated member with the Autoware-to-AAOS SDV adapter and evidence still planned.](concept-product-line.drawio.svg)

*Concept illustration, not a model view: how the product line works.* One
shared model holds every option; a bill of features picks one option per
layer, and the configurator checks the rules, derives the adapter, and
generates the member's product model. Both planned members come from the same
model, not from copies, and each has its own evidence status. Hypervisor and
sensor choices are left out of the picture.

The two governed members differ in one product decision, **Vehicle Platform
Integration Mode**, and that one decision drives several layer choices:

| Layer | Standalone member | AAOS-integrated member |
|---|---|---|
| Vehicle application | Autoware | Autoware |
| Middleware | none | Android SDV |
| Operating system (platform domain) | Linux | Android¹ |
| Hypervisor | none | KVM |
| Adapter | none (derived) | Autoware→AAOS SDV (derived) |

¹ Autoware keeps its own Linux/ROS 2 runtime; the AAOS domain is added beside
it. In the AAOS member's
[configuration](../../model-based-product-line-engineering/feature-configurations/middleware-autoware-aaos-sdv-reference.yaml),
cross-domain deployment and transport remain unresolved and the evidence
status is `planned`.

This is what the right-hand column looks like in the model itself:

![SysIDE render of the model view middlewareProductLineConfigurationView: the part definition MiddlewareAutowareAAOSSDVReference specializes SDVPlatformStack and selects vehicleApplication autoware, middleware androidSDV, osPlatform android, hypervisor kvm and applicationMiddlewareAdapter autowareToAAOSSDV.](../../textual-notation-of-model/packages/features/middleware/diagrams/diagram-middlewareProductLineConfigurationView.svg)

*SysIDE render of the model view `middlewareProductLineConfigurationView`.*
It shows the product model that the configurator generated for the
AAOS-integrated member: one selection per layer, and the adapter
`autowareToAAOSSDV` that the rules derived from the application and middleware
choices. It records a configuration; it does not show a built or running
stack.

Two lessons sit in this table. First, the adapter is **derived** from the
application and middleware choices, never selected on its own. Second,
emergency braking, Autoware, and the sensing baseline are **common** to both
members. A characteristic is a product feature only when it distinguishes one
member from another. Planned membership also does not mean both members have
the same implementation or test maturity.

### The capability that exercises it: emergency braking

To test whether the stack and product line hold together, we follow one
vehicle capability through them. A vehicle is traveling in the same lane
behind another vehicle. The distance closes and a collision becomes imminent.
The intended behavior is to detect the risk, warn the driver when required,
and request emergency braking when the activation conditions are met. Driver
override and failure handling are separate paths that also need defined
conditions and evidence.

This is the vehicle-target **Advanced Emergency Braking System (AEBS)** case.
The [operational story](../../methodologies/sysmod-sysmlv2/pilots/aebs-operational-story.md)
records the situation; it is not a report that a real vehicle passed a test.

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
then find `reqCommandEmergencyBraking` in the
[requirements model](../../textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml).
Its link to the need is a governed `DerivesFromNeed` connection; its link to
`requestBraking` in the
[functional model](../../textual-notation-of-model/packages/features/aebs/aebs_functional_architecture.sysml)
is a candidate trace. Both record design intent, not requirement satisfaction
or verification; the candidate's verification status is `NotStarted`.

The
[nominal moving-target bench](../../implementation/aebs-autoware-nominal-vehicle-target-bench/README.md)
provides bounded, replayable evidence for a configured simulation chain on the
standalone path. These are connected engineering artifacts, not proof that the
candidate product requirement is satisfied.

The vehicle versions are what we study (**System 1**). The models, tools,
processes, and evidence workflow we build are the engineering system
(**System 2**). Contributors, maintainers, and upstream communities evolve it
(**System 3**). The [project charter](../project-goals/project-charter.md)
defines the broader mission.

### What exists today, and what does not yet

In the repository today:

- the SysML v2 model of the platform stack and its candidates;
- the method kernel: the increment workflow with its 13 phases, the checks the
  method declares, and the read-only method tools that answer with the next
  obligation (see [part 2](#2-how-the-engineering-work-runs));
- the AEBS reference thread, increments `INC-AEBS-001` to `INC-AEBS-010`,
  with no recorded baseline yet;
- the middleware chain, increments `INC-MW-001` to `INC-MW-010`, closed at a
  recorded baseline;
- the feature catalogue, the bills of features of the two planned members,
  the configurator, and the product models it generated;
- reference implementations with retained, bounded evidence: Autoware
  benches on the standalone path, and an AEBS status display in an AAOS SDV
  guest that was observed on a build that is not exactly identified, so its
  verification verdicts stay inconclusive;
- public CI, licensed model validation, the Method Check, and a public viewer
  and SysML v2 API that serve one reviewed revision.

In progress, or not there yet:

- `INC-MW-011`, Eclipse S-CORE as the middleware layer: phases 0 to 3 are
  merged, the next phases are in progress;
- a fenced experiment that restates the governed scope in the PLEML
  product-line library, pinned to an exact upstream revision. It is not
  adopted: the catalogue and the configurator remain the selection authority;
- executable method checks for the phases that have none yet;
- verification of the candidate requirements; `REQ-AEBS-003` is still
  `NotStarted`;
- any member beyond the two planned ones, which needs a new reviewed scope
  decision.

No example shows more than its own evidence. The moving-target bench supports
a narrow simulation claim; its evidence boundary excludes conscious driver
override, false-reaction and degraded-operation matrices, pedestrian and
bicycle behavior, and real-vehicle brake performance. A valid configuration
proves only that the selected options satisfy the catalogue's rules, not that
the configured stack has been built or run.

No example establishes vehicle safety, regulatory compliance, certification,
homologation, or type approval. Check the owning artifact's status and
[evidence rules](../evidence-management.md), not just whether a file exists.
The [roadmap](../../ROADMAP.md) separates active work from broader ambitions.

## 2. How the engineering work runs

SysML v2 is the modeling language used to record the system's requirements,
structure, behavior, and relationships. The model is the design reference;
implementation should reflect it, not quietly define a different system.

### Increments and deterministic agentic engineering

Work happens in **increments**. An increment answers one engineering question,
such as "can Eclipse S-CORE realize the middleware layer?". Its charter, which
is part of the model, names the question, the scope, the owner, and the phases
the increment covers. The method has 13 phases, from framing (0) through
needs (4), requirements (5), architecture (6 to 8), variability (9), and V&V
and evidence (10) to publication (11) and the baseline decision (12).

![Concept illustration, not a model view: three lanes. Agent: read the next obligation, author model content, open a pull request. Deterministic evaluation: on each push the Method Check evaluates the model (same revision, same verdict) and returns gaps and the next obligation to the agent; executable checks today cover phases 0, 4, 5 and 10. People: the report goes to independent review and owner decisions, and only then to a merge to main.](concept-agentic-engineering.drawio.svg)

*Concept illustration, not a model view: deterministic agentic engineering.*
An agent authors model content and a deterministic evaluation judges it: on
each push the Method Check names the gaps and the next obligation, and the same
revision always gets the same verdict. People review, decide, and merge.

This works because the method itself is part of the model: a phase step can
declare the checks its artifacts must pass, and evaluating those checks is
deterministic
([method tools guide](../guides/drive-an-increment-with-the-method-tools.md),
[read-only, deterministic tools](../guides/query-the-public-model-via-mcp.md)).
An agent, or a person, runs the loop **next → author → gaps**: it reads the
**next obligation** (the first open check, what to author, and in which
package), authors that content, and pushes. The method tools answer for the
published revision, so work on a branch is evaluated by the **Method Check** of
its pull request, which exports the pull-request head and evaluates every
increment the model declares; that export can also be re-evaluated offline. INC-AEBS-010 was walked this way, push by push
([#349](https://github.com/de4sdv/DE4SDV/pull/349)), and INC-MW-011 is being
authored the same way ([#374](https://github.com/de4sdv/DE4SDV/pull/374)).

The scope is deliberately narrow. Today only the steps for framing, needs,
requirements, and V&V and evidence declare executable checks; the other phases
are reported as unchecked, never as passed, and rely on review. The evaluation
checks model content against the method's checks: it does not judge
engineering correctness, and its results are no acceptance, compliance, or
certification claim. The Method Check is advisory, so gaps never fail it.
Independent review and owner decisions stay with people, and maintainers
decide what merges.

A change travels like this:

1. **Frame the change.** State the user problem, the affected member, the
   operating conditions, and what is outside scope. For AEBS, a moving vehicle
   target is not interchangeable with a pedestrian or bicycle target.
2. **Update the connected artifacts.** Keep the story, requirements, model,
   configuration, implementation, and verification plan consistent. Record
   missing criteria as gaps rather than inventing thresholds or pass results.
3. **Submit a focused pull request (PR).** A PR is a proposed change for review,
   not an accepted baseline. Link the issue and explain the intended result.
4. **Run the checks and obtain the relevant validation.** Fix failures; keep
   model validation and runtime evidence separate, as described below.
5. **Review and baseline.** An independent reviewer checks the change and its
   claim boundaries; maintainers decide whether to merge it. Preserve the
   exact revision and evidence needed to reproduce a result.

### Configuring a member

Choosing layer options is done with files, not by editing the model by hand:

1. The **feature catalogue** lists the options and compatibility rules.
2. A **bill of features** records one member's selections, for example the
   [standalone member's](../../model-based-product-line-engineering/feature-configurations/aebs-autoware-linux-lidar-camera.yaml).
3. The **configurator** checks the selections against the rules and derives
   dependent choices such as the adapter.
4. It generates a SysML **product model** for that member. Generated product
   models are marked do-not-edit; change the selections instead.

You can try the check yourself:

```bash
python tools/configure_variant.py \
  --feature-model model-based-product-line-engineering/feature-models/sdv_product_line.yaml \
  --bof model-based-product-line-engineering/feature-configurations/aebs-autoware-linux-lidar-camera.yaml \
  --check-only
```

Swap in `feature-configurations/fixtures/invalid-score-android.yaml` to watch
rule C001 reject an incompatible combination. Without `--check-only`, the
configurator prints the generated product model; its doc comment lists the
derived adapter (`none` for the standalone member, `autowareToAAOSSDV` for the
AAOS-integrated one). See the
[product-line engineering guide](../../model-based-product-line-engineering/README.md)
for the full chain and its validation boundary.

### CI/CD in plain language

![Concept illustration, not a model view: the model in Git goes by pull request to SysIDE validation and export in licensed CI, and the author commits the rendered diagrams back to Git, where CI checks them. The export feeds the Method Check in licensed CI; public CI runs the tests on every pull request. Both report to review and merge, and a maintainer publishes the exact revision to the viewer with Ask.](concept-ci-evidence-pipeline.drawio.svg)

*Concept illustration, not a model view: from a model change to the published
model.* Each result is tied to a commit; the Method Check and publication name
the exact one. A passing check is not approval, and publishing is not
certification.

**Continuous integration (CI)** checks every proposed change automatically.
The [public CI workflow](../../.github/workflows/ci.yml) checks repository
consistency and local documentation links, restores pinned model dependencies,
runs the complete project test suite, runs bench unit/contract tests in
separate processes, and runs smoke tests. Bench unit tests do **not** build and
execute the vehicle simulation.

Changed SysML models get two licensed checks on top. **SysIDE validation**
checks syntax and semantics and renders the views declared in the model; the
diagrams committed next to the model come from that run. The **Method Check**
described above evaluates the increments. Both run automatically for model
changes in pull requests that maintainers open from this repository; for other
pull requests, a maintainer runs them after initial review, and contributors
with SysIDE access can validate locally. See the
[contribution guide](../../CONTRIBUTING.md#sysml-v2-validation-gate). A valid
model is not a successfully executed implementation.

**Delivery/deployment (CD)** makes selected outputs available to readers and
tools. The [Pages workflow](../../.github/workflows/deploy-viewer.yml)
publishes a browse-only engineering mirror after each change to `main`. The
[public viewer deployment](../../.github/workflows/deploy-public-ask-viewer.yml),
which includes **Ask the model**, and the
[API deployment](../../.github/workflows/deploy-public-sysml-api.yml) are
separate, maintainer-triggered workflows bound to one exact revision, so the
public viewer can trail `main`. A green PR is not automatically the deployed
public baseline, and an Ask answer is generated, not model authority: follow
its links back to the model.

### More model views

The illustrations on this page are concepts. Every diagram in the
[model viewer](https://viewer.de4sdv.org) is generated from a view declared in
the model by the licensed validation run; none is drawn by hand. The
[viewer guide](../guides/model-viewer.md) explains how to use it. Good next
views:

- the [AEBS functional architecture](../../textual-notation-of-model/packages/features/aebs/diagrams/diagram-aebsFunctionalArchitectureView.svg),
  which lists `assessRisk`, `requestWarning`, and `requestBraking`; it lists
  responsibilities, not their execution order;
- the [platform stack structure view](../../textual-notation-of-model/packages/architecture/diagrams/diagram-sdvPlatformStackStructureView.svg),
  a dense reference diagram best viewed at full size;
- the [standalone member's product structure view](../../model-based-product-line-engineering/product-models/diagrams/diagram-productStructureView.svg);
- the [AEBS view index](../../textual-notation-of-model/packages/features/aebs/VIEWS.md),
  which covers structure, exchanges, and evidence separately.

## 3. Pick a bounded contribution

These are small task proposals, not assignments or a second ticket tracker.
Check [open issues](https://github.com/de4sdv/DE4SDV/issues) and existing PRs
first. Continue an existing issue where it fits; otherwise agree the scope in
an issue before starting. Each task below names a starting point and a result
that can be reviewed.

| Task | Start here | Reviewable result / done when |
|---|---|---|
| Try the newcomer path (documentation) | This page and [#300](https://github.com/de4sdv/DE4SDV/issues/300) | Report confusing passages and propose one focused correction. A reader can answer the four questions below without private project context. |
| Try the issue-to-PR path as a first-time GitHub user (community/docs) | [CONTRIBUTING](../../CONTRIBUTING.md) and [#37: GitHub onboarding](https://github.com/de4sdv/DE4SDV/issues/37), where an onboarding guide is proposed | Follow the issue-to-pull-request steps once and post in #37 where you got stuck and what helped. Feed that guide; do not start a second one. |
| Configure both reference members (product line) | The two bills of features named above and the [configurator](../../tools/configure_variant.py) | Run the check for both members and the invalid fixture, then run without `--check-only`. Record the revision, commands, results, and the derived adapter for each member. Report any mismatch with the member table on this page. |
| Follow one requirement (systems/traceability) | `REQ-AEBS-003` in the [draft needs and requirements](../../methodologies/sysmod-sysmlv2/pilots/aebs-needs-requirements.md) and the example above | At one revision, review its need, design, verification, and evidence links. Report one broken or missing link, or confirm the bounded chain, keeping candidate status and open gaps visible. |
| Make one bench's evidence check reproducible (verification/software) | The [moving-target bench](../../implementation/aebs-autoware-nominal-vehicle-target-bench/README.md) and its [evidence hygiene test](../../tests/test_evidence_repository_hygiene.py) | From a clean checkout, the documented check of the retained evidence stops because an empty run log is deliberately not tracked (empty files are not evidence). Agree the fix in an issue, then show the check passing from a clean checkout. Replaying retained evidence is not a new simulation or vehicle test. |
| Bring the implementation index up to date (docs/QA) | The [implementation index](../../implementation/README.md), the [AAOS visualization evidence model](../../textual-notation-of-model/packages/features/aebs/aebs_visualization_verification_evidence.sysml), and the [video disposition index](../../implementation/aebs-aaos-sdv-visualization-bench/evidence/010/VIDEO-EVIDENCE-DISPOSITION.md) | The index lists four of the seven implementation folders and calls the visualization bench's runtime evidence pending. The owning model records observations on a build that is not exactly identified, with inconclusive verdicts, while the video disposition index still says `observed_bounded`. Propose one small correction that follows the model and keeps the deferred safety outcome and the media limits visible. |

You can begin with reading and feedback; coding is not required. For a change,
follow [CONTRIBUTING](../../CONTRIBUTING.md). The
[getting started guide](README.md) covers repository layout, setup, and checks.

### Does this page work for a newcomer?

After reading it, can you explain:

1. What problem DE4SDV helps engineers solve, and what "continuously
   certifiable" means here as an aim?
2. What the stack layers are, how the two governed members differ, and why the
   adapter is derived rather than chosen?
3. What an increment is, what the agent, the Method Check, and people each do
   in it, and why a valid configuration, passing checks, or a replayed
   simulation does not mean a vehicle is certified?
4. Which small task you could take, what you would produce, and how it is
   checked?

If not, point out the missing explanation in
[#300](https://github.com/de4sdv/DE4SDV/issues/300). Newcomer feedback is part of
validating this guide, not something automated repository tests can prove.
