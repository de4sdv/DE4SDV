# Process Set

Reusable process guidance for SDV systems engineering.

DE4SDV separates product-line engineering work from method and ecosystem
evolution work. This page is the **catalog** of reusable processes by system
layer. It tells you which process exists, what it does, and where it lives in
the repository.

For the **logical sequence of work** — the order in which these processes are
exercised inside a modeling increment — see
[`methodologies/sysmod-sysmlv2/process-mapping.md`](../../methodologies/sysmod-sysmlv2/process-mapping.md),
which defines the 13-phase increment workflow, feedback loops, and the
viewpoint flow per phase. For the repeatable contribution pattern (entry
criteria, sizes, review questions), see
[`methodologies/sysmod-sysmlv2/increment-workflow.md`](../../methodologies/sysmod-sysmlv2/increment-workflow.md).

## System 1-facing processes

These processes define or assess the configurable SDV product line and its
configured variants (System 1).

| Process | What it does | Where it lives |
|---|---|---|
| Feature modeling | Define common and variable capabilities of the product line; classify capabilities as features or common capabilities per the feature/common-capability rule | `model-based-product-line-engineering/feature-models/`; SysML: `packages/methods/de4sdv/de4sdv_product_line.sysml` |
| Feature configuration | Select features for a member product and record the configuration | `model-based-product-line-engineering/feature-configurations/` |
| Product-model assembly | Assemble variant-specific product models from shared assets and configuration decisions | `model-based-product-line-engineering/product-models/` |
| Architecture definition | Define functional, logical, and physical/software architecture with variation points | SysML: `textual-notation-of-model/packages/` (features, architecture) |
| Interface definition | Define system and physical interfaces and exchanged items | SysML interface packages; `methodologies/sysmod-sysmlv2/saf-viewpoint-map.md` (System Interface/Physical Interface viewpoints) |
| Behavior modeling | Model operational processes, use cases, functional flows, and states | SysML feature packages (operational context, functional behavior slices) |
| Hazard and threat analysis inputs | Provide model inputs (assets, context, functions) for safety and security analysis | `compliance/safety/`, `compliance/security/` |
| Variant-specific verification and validation planning | Plan verification and validation for configured variants, including acceptance criteria | `methodologies/sysmod-sysmlv2/increment-workflow.md` (phase 10); `continuous-homologation/` |

## System 2 processes

These processes operate the DE4SDV life-cycle engineering and assurance
system (System 2).

| Process | What it does | Where it lives |
|---|---|---|
| SysML v2 model authoring and review | Author model increments in SysML v2 textual notation and review them through PRs | `textual-notation-of-model/`; review gate: `methodologies/sysmod-sysmlv2/review-checklist.md` |
| Product-line asset management | Maintain feature models, configurations, shared assets, and product models as reusable assets | `model-based-product-line-engineering/` |
| Digital-thread traceability management | Keep trace links across needs, requirements, architecture, evidence, and baselines; SysML `dependency` usages are the trace artifact | `digital-continuity/`; `increment-workflow.md` (trace chain) |
| Simulation and digital-twin workflow management | Manage FMI/FMU/SSP simulation and digital-twin scope, synchronization, and credibility | `simulation/`, `digital-twin/` |
| Model credibility and VVUQ planning | Plan how much confidence a model, simulation, or evidence artifact earns for its declared use | `approach/framework/ontology/` (credibility assessment); `digital-twin/` |
| Evidence generation and evidence-register maintenance | Generate and record verification/validation evidence with explicit evidence status vocabulary | `continuous-homologation/evidence-register.md`; `increment-workflow.md` (evidence status) |
| Configuration and baseline management | Control baselines, change, versioning, and release evidence | `configuration-management/` |
| Continuous homologation evidence preparation | Prepare compliance evidence continuously across engineering changes without claiming approval | `continuous-homologation/` |
| DevSecOps automation for repeatable checks | Automate repository checks, CI, SBOM, and security scans | `scripts/`, `devsecops/`, `.github/workflows/` |

## System 3 processes

These processes evolve DE4SDV itself as an open innovation ecosystem
(System 3).

| Process | What it does | Where it lives |
|---|---|---|
| Methodology evolution | Tailor and evolve the modeling method; feed lessons from increments back into method docs and ADRs | `methodologies/sysmod-sysmlv2/` (tailoring, process mapping) |
| Standards and reference adoption | Map and adopt standards and reference frameworks with explicit provenance | `standards/`; `docs/references/source-notes.md` |
| Upstream maintainer coordination | Coordinate with upstream project owners before deep integration or vendoring | `methodologies/sysmod-sysmlv2/upstream.md`, `upstream-compatibility-report.md` |
| ADR governance | Record architecture decisions with rationale, alternatives, and consequences | `docs/architecture-decisions/` |
| Contributor onboarding and review | Onboard contributors and review contributions consistently | `CONTRIBUTING.md`, `GOVERNANCE.md`, `docs/getting-started/` |
| Toolchain evaluation | Evaluate modeling, simulation, and automation toolchains before adoption | ADRs; `experiments/` |
| Roadmap prioritization | Prioritize work in scope for upcoming milestones | `ROADMAP.md` |
| Community learning from System 2 usage | Turn increment experience into method and governance improvements | ADRs, methodology docs, review checklists |

## Cross-layer interactions

Processes from different layers interact. When adding or changing a process,
state whether it primarily affects System 1, System 2, System 3, or a
traceable cross-layer interaction, and make the interaction explicit rather
than implied.

Examples of cross-layer interactions:

- A feature-modeling increment (System 1) is executed through the System 2
  increment workflow and reviewed under System 3 governance.
- A digital-thread link (System 2) connects a System 1 feature, a System 2
  evidence record, and a System 3 ADR that changed the method.
- A toolchain evaluation (System 3) can change the System 2 modeling process
  and therefore the artifacts System 1 increments produce.

## Realization-readiness feedback control

A realization-readiness probe is a cross-phase System 2 control used when a
physical/software realization depends on an enabling system such as a build
host, toolchain, hypervisor, runtime, simulator, or verification environment.
It is not a new lifecycle phase.

The probe happens before expensive source synchronization, build, deployment,
or evidence execution. It answers whether a candidate enabling system can
build, deploy, execute, or verify the selected realization under its stated
capability envelope. A probe record identifies the realization question,
candidate enabling system, required capabilities, retained evidence and
observations, affected model elements, and the disposition (proceed,
re-scope, or defer).

Do not promote enabling-system readiness into product interoperability,
safety, certification, or production-readiness evidence without the
corresponding target-runtime observation.

The full loop and its feedback paths are defined in
[`process-mapping.md`](../../methodologies/sysmod-sysmlv2/process-mapping.md#cross-phase-realization-readiness-control)
and [`increment-workflow.md`](../../methodologies/sysmod-sysmlv2/increment-workflow.md#realization-readiness-control).

## Related guidance

- [`methodologies/sysmod-sysmlv2/process-mapping.md`](../../methodologies/sysmod-sysmlv2/process-mapping.md) — logical sequence of work, 13 phases, viewpoint flow
- [`methodologies/sysmod-sysmlv2/increment-workflow.md`](../../methodologies/sysmod-sysmlv2/increment-workflow.md) — repeatable contribution pattern and review questions
- [`methodologies/sysmod-sysmlv2/artifact-map.md`](../../methodologies/sysmod-sysmlv2/artifact-map.md) — method concepts to repository artifacts
- [`methodologies/sysmod-sysmlv2/saf-viewpoint-map.md`](../../methodologies/sysmod-sysmlv2/saf-viewpoint-map.md) — viewpoint selection per increment type
- [`methodologies/sysmod-sysmlv2/de4sdv-tailoring.md`](../../methodologies/sysmod-sysmlv2/de4sdv-tailoring.md) — how external method concepts enter DE4SDV
- [`approach/framework/viewpoint/README.md`](../framework/viewpoint/README.md) — what viewpoints and views are in DE4SDV
