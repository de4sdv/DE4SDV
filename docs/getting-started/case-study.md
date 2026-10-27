# DE4SDV through one case study

DE4SDV helps engineers build software-defined vehicles from interchangeable
open-source parts and keep the design, configuration choices, tests, and
evidence connected while those parts change. We build an open engineering
reference, not a production car or a certificate.

![Concept illustration, not a model view: four stages from left to right. One SysML v2 model, with requirements, architecture, variability and verification and validation (V&V) evidence (existing today), is configured along dimensions such as these two. Platform stack: a configuration has a main side and can have a guest side under KVM on the same chip. Each side lists its layers in the order application · middleware · OS. Two member configurations exist today: Autoware · Linux with no guest side, and Autoware · Linux with an AAOS SDV · Android guest side. Not admitted yet: the candidate Autoware · Eclipse S-CORE · Linux with an AAOS SDV · Android guest side and a human-machine interface (HMI) display, in progress. More stacks are deferred and not admitted. Sensor set: LiDAR and camera, shared by both members, exists today; variants, for example entry, mid and premium, are deferred and not admitted. Every change is re-checked by CI and review, and model changes also by the Method Check; evidence per member is in progress. The aim is re-checkable evidence for every member and a continuously certifiable product line.](concept-vision-and-aim.drawio.svg)

*Concept illustration, not a model view: the vision at a glance.* DE4SDV
keeps one SysML v2 model for the whole product line and configures each member
product from it. The configuration dimensions include the platform stack
(application, middleware, OS) and the sensor set. Today two members are
admitted. Both select Autoware on Linux for the main side of the chip. One of
them adds a guest side under the KVM hypervisor, with the Android SDV
middleware (AAOS SDV) on Android. Both members share one LiDAR and camera
sensor set. Another configuration is valid but not admitted. It selects
Autoware on Eclipse S-CORE on Linux, with an AAOS SDV guest for a
human-machine interface (HMI) display. The owner decides on its admission after
a runnable proof. Sensor-set variants, for example entry, mid and premium, are
deferred until a scope decision admits them. CI and review re-check every
change, and the Method Check also checks model changes. The aim is traceable,
re-checkable evidence for every member: that is what **continuously certifiable
SDV product lines** means here, and no member is certified.

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
| Hypervisor | Isolates several operating systems on one chip | KVM (Kernel-based Virtual Machine), QNX QVM, ACRN, or none |
| Hardware | The compute platform the stack runs on | Kept abstract |

The operating system above is the one of the **main side**, the part of the
chip that runs the vehicle application. Under a hypervisor, a **guest side**
can run a second operating system with its own middleware: today Android with
the Android SDV middleware (AAOS SDV), or no guest.

Not every combination is valid. The
[feature model](../../model-based-product-line-engineering/feature-models/sdv_product_line.sysml)
records compatibility rules. For example, rule C001 rejects Eclipse S-CORE on
Android because S-CORE targets Linux and QNX.

### The product line: what the stack can express versus what we govern

A **product line** is a family of related vehicle versions whose shared design
is managed together. Two levels matter, and it is easy to confuse them:

- **What the stack can express.** The catalogue above lists every candidate
  so alternatives can be compared and kept in view.
- **What DE4SDV currently governs.** A
  [reviewed scope decision](../architecture-decisions/0014-ratify-initial-aebs-product-line-scope.md)
  and its
  [scope model](../../model-based-product-line-engineering/scoping/de4sdv_aebs_product_line_scope.sysml)
  admit exactly two planned reference members. Apollo, Openpilot, Eclipse
  S-CORE, AUTOSAR Adaptive, QNX/QVM, ACRN, and similar options remain
  reference-only or deferred until a future reviewed decision admits a member
  that needs them.

Eclipse S-CORE is the first of those options under test: increment
`INC-MW-011` (an increment answers one engineering question; see
[part 2](#2-how-the-engineering-work-runs)), in progress, asks whether S-CORE
can realize the middleware layer of a member with Autoware on a Linux host and
an Android Automotive OS (AAOS) guest for the display
([framing model](../../textual-notation-of-model/packages/features/middleware/middleware_score_framing.sysml)).
Admitting such a member would take a new reviewed scope decision.

![Before the switch to PLEML: a concept illustration, not a model view. A shared model holds every option. Platform stack: application Autoware, Openpilot or Apollo; middleware Eclipse S-CORE, Android SDV, AUTOSAR Adaptive or none; operating system Linux, Android or QNX; an adapter derived from application and middleware. Sensors: LiDAR, radar and camera: at least one, in any combination. Common: vehicle-target AEBS and motion sensors. Bill of features A selects Autoware, no middleware, Linux, LiDAR and camera; bill of features B selects Autoware, Android SDV, Android, LiDAR and camera. The configurator checks the rules, derives the adapter and generates the two members' product models: the standalone member with no adapter and simulation-bench evidence, and the AAOS-integrated member with the Autoware-to-AAOS SDV adapter and evidence still planned.](concept-product-line.drawio.svg)

*Concept illustration, not a model view: how the product line worked before
the switch to PLEML
([ADR 0022](../architecture-decisions/0022-adopt-pleml-as-product-line-authority.md)).*
Since the switch, a PLEML feature configuration makes the selections, and the
DE4SDV evaluator checks the rules and derives the adapter; see
[Configuring a member](#configuring-a-member). In the drawing, one shared model
holds every option; a bill of features picks one option per platform-stack
layer and at least one perception sensor, and the configurator checks the
rules, derives the adapter, and generates the member's product model. The
generated model resolves the platform stack; sensor and capability selections
are recorded in its comment, not yet resolved in SysML. Both planned members
come from the same model, not from copies, share the LiDAR and camera sensor
set, and each has its own evidence status. Hypervisor choices are left out of
the picture.

The two governed members differ in one product decision, **Vehicle Platform
Integration Mode**, and that one decision drives several layer choices. The
last two rows are common to both members:

| Aspect | Standalone member | AAOS-integrated member |
|---|---|---|
| Vehicle application | Autoware | Autoware |
| Middleware | none | Android SDV, in the guest¹ |
| Operating system (main side) | Linux | Linux |
| Hypervisor | none | KVM |
| Guest operating system and middleware | none | Android with AAOS SDV¹ |
| Adapter | none (derived) | Autoware→AAOS SDV (derived) |
| Capability (common) | Emergency braking (vehicle-target AEBS) | Emergency braking (vehicle-target AEBS) |
| Sensing baseline (common) | LiDAR + camera, IMU, wheel odometry | LiDAR + camera, IMU, wheel odometry |

¹ Autoware keeps its own Linux and ROS 2 (Robot Operating System 2) runtime on
the main side, which is also the KVM host. The AAOS SDV middleware runs in an
Android guest under KVM on the same chip, and it is the middleware that
Autoware integrates with. In the AAOS member's
[configuration](../../model-based-product-line-engineering/feature-configurations/middleware_autoware_aaos_sdv_reference.sysml),
cross-domain transport remains unresolved. Its
[evidence record](../../model-based-product-line-engineering/feature-configurations/evidence/middleware-autoware-aaos-sdv-reference.yaml)
states the evidence status `planned`.

This is what the right-hand column looks like in the model itself:

![SysIDE render of the model view middlewareProductLineConfigurationView: the part definition MiddlewareAutowareAAOSSDVReference specializes SDVPlatformStack and selects vehicleApplication autoware, middleware androidSDV, osPlatform linux, hypervisor kvm, guestOSPlatform android, guestMiddleware androidSDV and applicationMiddlewareAdapter autowareToAAOSSDV.](../../textual-notation-of-model/packages/features/middleware/diagrams/diagram-middlewareProductLineConfigurationView.svg)

*SysIDE render of the model view `middlewareProductLineConfigurationView`.*
It shows the platform-stack product model that the configurator generated for
the AAOS-integrated member: one selection per layer, and the adapter
`autowareToAAOSSDV` that the rules derived from the application and middleware
choices. It records a configuration; it does not show a built or running
stack.

Two lessons sit in this table. First, the adapter is **derived** from the
application and middleware choices, never selected on its own. Second,
emergency braking, Autoware, and the sensing baseline are **common** to both
members; the
[scope decision](../architecture-decisions/0014-ratify-initial-aebs-product-line-scope.md#common-within-the-governed-portfolio)
lists all common content. A characteristic is a product feature only when it
distinguishes one member from another. Planned membership also does not mean
both members have the same implementation or test maturity.

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
  bounded baseline recorded in the
  [baseline register](../../configuration-management/baseline-register.md);
- the PLEML feature model and the feature configurations of the two planned
  members, the configurator, and the product models it generates from the
  configurations' receipts. The YAML feature catalogue and bills of features
  that they restate retired at step S7 of ADR 0022;
- reference implementations with retained evidence and stated limits:
  Autoware benches on the standalone path, each with its own stated evidence
  boundary, and an AEBS status display in an AAOS SDV guest that was observed
  on a build that is not exactly identified, so its verification verdicts stay
  inconclusive
  ([evidence model](../../textual-notation-of-model/packages/features/aebs/aebs_visualization_verification_evidence.sysml));
- public CI, licensed model validation, the Method Check, and a public viewer
  and SysML v2 API that serve one reviewed revision.

In progress, or not there yet:

- `INC-MW-011`, Eclipse S-CORE as the middleware layer: phases 0 to 9 are
  merged. Phase 8 models how the S-CORE SOME/IP gateway carries the AEBS
  signals to the HMI in the guest. Guard rails in the model bound the
  gateway's known defects, and phase 10 tests them. Variability and
  configuration (phase 9) gave the platform a guest
  side and added the configured product `MW-CONFIG-002`. It is valid and not
  admitted, and admission is the owner's phase-12 decision. Verification and
  evidence (phase 10) is next, with a runnable proof on a bench, and phases 11
  and 12 are still to come
  ([framing model](../../textual-notation-of-model/packages/features/middleware/middleware_score_framing.sysml),
  [physical realization](../../textual-notation-of-model/packages/features/middleware/middleware_score_physical_software_realization.sysml),
  [configured product](../../textual-notation-of-model/packages/features/middleware/middleware_score_variability_configuration.sysml));
- executable method checks for the phases that have none yet;
- verification of the candidate requirements; `REQ-AEBS-003` is still
  `NotStarted`;
- any member beyond the two planned ones, which needs a new reviewed scope
  decision.

No example shows more than its own evidence. The moving-target bench supports
a narrow simulation claim; its evidence boundary excludes conscious driver
override, false-reaction and degraded-operation matrices, pedestrian and
bicycle behavior, and real-vehicle brake performance. A valid configuration
proves only that the selected options satisfy the feature model's rules, not
that the configured stack has been built or run.

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
needs (4), requirements (5), architecture (6 to 8), variability (9), and
verification and validation (V&V) and evidence (10) to publication (11) and the
baseline decision (12).

![Concept illustration, not a model view: three lanes. Agent: read the next obligation, author model content, open a pull request. Deterministic evaluation: on each push the Method Check evaluates the model (same revision, same verdict) and returns gaps and the next obligation to the agent; executable checks today cover phases 0, 4 to 8 and 10. People: the report goes to independent review and owner decisions, and only then to a merge to main.](concept-agentic-engineering.drawio.svg)

*Concept illustration, not a model view: deterministic agentic engineering.*
An agent authors model content and a deterministic evaluation judges it: on
each push the Method Check names the gaps and the next obligation, and the same
revision always gets the same verdict. People review, decide, and merge. The
Method Check runs automatically on maintainer pull requests from this
repository; see [CI/CD](#cicd-in-plain-language).

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
increment the model declares; that export can also be re-evaluated offline.
INC-AEBS-010 was walked this way, push by push
([framing model](../../textual-notation-of-model/packages/features/aebs/aebs_visualization_framing.sysml)),
and INC-MW-011 is being authored the same way
([framing model](../../textual-notation-of-model/packages/features/middleware/middleware_score_framing.sysml)).

The scope is deliberately narrow. Today the steps for framing, needs,
requirements, architecture, and V&V and evidence declare executable checks
(phases 0, 4 to 8, and 10); the other phases are reported as unchecked, never
as passed, and rely on review. The architecture phases 6 to 8 check the
allocation chain from requirement to function, logical element, and physical
element. A missing allocation to the next layer blocks the phase exit; among
requirements only the functional ones block, and the others get an advisory
note. The backward checks, whether an element receives an allocation from the
layer before it, are advisory. The Method Check of a pull request evaluates
these checks on the export of its head; the public method tools give no
verdict for phases 6 to 8 yet. The evaluation checks model content against
the method's checks: it does not judge engineering correctness, and its
results are no acceptance, compliance, or certification claim. The Method
Check is advisory, so gaps never fail it. Independent review and owner
decisions stay with people, and maintainers decide what merges.

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

1. The PLEML **feature model** lists the options and the compatibility rules.
2. A PLEML **feature configuration** records one member's selections, for
   example the
   [standalone member's](../../model-based-product-line-engineering/feature-configurations/aebs_autoware_linux_lidar_camera.sysml).
3. The privileged PLE authority workflow serializes the configurations with
   licensed SysIDE. The DE4SDV evaluator then checks the selections against
   the rules, derives dependent choices such as the adapter, and writes the
   result into a receipt. The pull request commits the receipt.
4. The **configurator** generates a SysML **product model** from the receipt.
   The product model resolves the member's platform stack; the other
   selections are recorded in its comment. Generated product models are
   marked do-not-edit; change the configuration instead.

After `sysand sync`, you can check a configuration against its receipt
yourself:

```bash
python tools/configure_variant.py \
  --receipt model-based-product-line-engineering/feature-models/receipts/sdv_product_line.receipt.json \
  --configuration aebsAutowareLinuxLidarCamera \
  --check-only
```

Swap in `invalidSCOREAndroidVariant`, the invalid fixture, to watch the C001
exclusion (S-CORE excludes Android on the main side) and C011 (Autoware
requires Linux) reject an incompatible combination.
Without `--check-only`, the configurator
prints the generated product model; its doc comment lists the derived adapter
(`none` for the standalone member, `autowareToAAOSSDV` for the AAOS-integrated
one). It never projects a fixture.

See the
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
which includes the **Ask** window (Model and Repository modes), and the
[API deployment](../../.github/workflows/deploy-public-sysml-api.yml) are
separate, maintainer-triggered workflows bound to one exact revision, so the
public viewer can trail `main`. A green PR is not automatically the deployed
public baseline, and an Ask answer is generated, not an engineering or model
authority: follow its element or source links
([viewer guide](../guides/model-viewer.md)).

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

Open tasks live in GitHub issues, so this page links live searches instead of
a fixed list:

- [open issues labelled `good first issue`](https://github.com/de4sdv/DE4SDV/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22),
  small tasks suited to a first contribution;
- [open issues labelled `help wanted`](https://github.com/de4sdv/DE4SDV/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22),
  where maintainers ask for help.

Each issue describes its task. Read it for where to start, what to produce,
and when the task is done, and for whether it needs licensed tools; if that is
unclear, ask in the issue. The labels show the
[lane](../../CONTRIBUTING.md#contribution-lanes) (`lane:*`) and the
[size](../../CONTRIBUTING.md#contribution-sizes) (`size:*`). Comment on an
issue before you start, so that two people do not do the same work.

A contribution task adds no engineering claim by itself: a corrected document
or a passing check is not verification or certification.

You can begin with reading and feedback; coding is not required. For a change,
follow [CONTRIBUTING](../../CONTRIBUTING.md). The
[getting started guide](README.md) covers repository layout, setup, and checks.
To propose a task that is not listed, open an issue with the **Question or
contribution proposal** template.

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

If not, open an issue with the **Documentation / methodology update** template
and point out the missing explanation. Newcomer feedback is part of validating
this guide, not something automated repository tests can prove.
