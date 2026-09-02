# Getting started with DE4SDV

DE4SDV (Digital Engineering for Software-Defined Vehicle) is an open-source
project that develops reference assets for systems engineering of
software-defined vehicles (SDVs): SysML v2 models, product-line engineering,
digital continuity, simulation interoperability, and continuous compliance
work. It is also a workstream within the INCOSE Automotive Working Group.

This guide gets you oriented. If you want to contribute, read
[`CONTRIBUTING`](../../CONTRIBUTING.md) afterwards.

## What DE4SDV is working on

DE4SDV applies product-line engineering to SDVs so that variability across
subsystems (ADAS, operating systems, core software) is modeled explicitly as
configurable architectures — enabling comparison of alternatives, transparent
trade-offs, and lifecycle-wide assurance.

The project uses the ASELCM three-system framing to keep scopes distinct (see
[ADR 0004](../architecture-decisions/0004-adopt-aselcm-three-system-framing.md)):

- **System 1** — the configurable SDV product line and configured
  vehicle/software variants (the engineered system).
- **System 2** — the DE4SDV life-cycle engineering and assurance system: the
  models, processes, and evidence structures in this repository.
- **System 3** — the open innovation ecosystem: governance, standards,
  methodology, contributors, and upstream projects that evolve System 2.

Most day-to-day work happens in System 2: SysML v2 model increments that
produce reviewable artifacts, trace links, and evidence.

## Repository layout at a glance

| Area | What lives there |
|---|---|
| `docs/` | Human-facing documentation: this guide, guides, terminology, ADRs, runbooks |
| `approach/` | Process set, framework, ontology, and viewpoint guidance |
| `methodologies/` | The DE4SDV method: increment workflow, process mapping, SAF viewpoint map, pilots |
| `textual-notation-of-model/` | The SysML v2 systems model: method packages, SAF viewpoints, feature packages (AEBS, middleware) |
| `model-based-product-line-engineering/` | Feature models, configurations, shared assets, product models |
| `implementation/` | Reference implementations with reproducible evidence (e.g. Autoware AEBS benches) |
| `compliance/`, `continuous-homologation/`, `configuration-management/` | Safety, security, evidence, baseline structures |
| `simulation/`, `digital-twin/`, `digital-continuity/`, `sysmlv2-api/` | Simulation, twin, traceability, and API integration assets |
| `devsecops/` | CI/CD, SBOM, security automation notes |
| `scripts/`, `tools/` | Repository checks and tooling (including the model viewer) |

The full index lives in [`docs/repository-tree.md`](../repository-tree.md).

## Explore the model

The core artifact is the SysML v2 systems model under
`textual-notation-of-model/`. The easiest way to explore it is the model
viewer:

- Public read-only instance: <https://viewer.de4sdv.org>
- Locally, serving **your own working tree and unmerged branches**:

```bash
python -m tools.sysml_html_viewer.serve --repo . --port 8787
# open http://127.0.0.1:8787/
```

In the viewer you can browse the model tree, read member documentation,
open every declared view (the diagrams SysIDE renders from the model), hover
elements and connections for tooltips, jump to definitions, and inspect
viewpoints and concerns. See the
[model viewer guide](../guides/model-viewer.md) for all features.

If you prefer the source, start here:

- `textual-notation-of-model/packages/methods/saf/SAF_Viewpoints.sysml` —
  GfSE SAF viewpoints used by DE4SDV
- `textual-notation-of-model/packages/methods/de4sdv/` — DE4SDV method
  packages (context, stakeholders, product line, viewpoints)
- `textual-notation-of-model/packages/features/aebs/` — the AEBS pilot
  model slices, one per increment phase
- `textual-notation-of-model/packages/features/middleware/` — the
  middleware pilot slices

To understand the element kinds you will meet in these files — packages,
parts and ports, requirement candidates, verification cases, evidence items,
views — and why DE4SDV uses them, read the
[model element guide](../guides/sysml-elements.md). It is also published in
the model viewer under **Elements**.

## Understand the process

DE4SDV builds the model in small, reviewable increments. Each increment walks
a 13-phase sequence (numbered 0–12) from framing, through operational
context, needs, requirements, functional/logical architecture, physical
realization, variability, V&V and evidence, to publication and baseline.

Key documents:

| Document | Answers |
|---|---|
| [`methodologies/sysmod-sysmlv2/process-mapping.md`](../../methodologies/sysmod-sysmlv2/process-mapping.md) | The logical order of work: 13 phases, feedback loops, viewpoint flow per phase |
| [`methodologies/sysmod-sysmlv2/increment-workflow.md`](../../methodologies/sysmod-sysmlv2/increment-workflow.md) | The repeatable contribution pattern: entry criteria, phase table, increment sizes, review questions |
| [`approach/process-set/README.md`](../../approach/process-set/README.md) | The catalog of reusable processes by system layer |
| [`methodologies/sysmod-sysmlv2/saf-viewpoint-map.md`](../../methodologies/sysmod-sysmlv2/saf-viewpoint-map.md) | Which viewpoints to select for which kind of increment |
| [`methodologies/sysmod-sysmlv2/artifact-map.md`](../../methodologies/sysmod-sysmlv2/artifact-map.md) | How method concepts map to repository artifacts |

Two rules you will meet constantly:

- **Feature/common-capability rule** — a characteristic is a *feature* only
  when it distinguishes one member product from another. If every member
  product has it, model it as a *common capability*.
- **Needs ≠ requirements** — stakeholder needs (problem space) stay separate
  from verifiable design-input requirements.

## Run the repository checks

```bash
python scripts/check_repo.py
python scripts/smoke_test.py
git diff --check
```

These are the public gates that CI runs on pull requests. SysML v2 textual
validation is a separate, privileged step — see
[`CONTRIBUTING`](../../CONTRIBUTING.md#sysml-v2-validation-gate) for the two
validation paths.

## Make your first contribution

1. Read [`CONTRIBUTING`](../../CONTRIBUTING.md) — it explains contribution
   sizes (XS–L), lanes, the issue-first rule for larger work, and the PR
   workflow.
2. Pick a small, focused improvement: a documentation fix, a terminology
   addition, a trace link, or an issue marked as good for newcomers.
3. Open an issue if the change is larger than a typo or small clarification.
4. Submit a pull request and answer the review questions from the
   [increment workflow](../../methodologies/sysmod-sysmlv2/increment-workflow.md#review-questions).

For real-time coordination, DE4SDV uses Mattermost at <https://chat.de4sdv.org>
(invite-only; request an invite through the issue template — see
[`COMMUNICATION`](../../COMMUNICATION.md)).

## Learn the terms

The [glossary](../terminology/glossary.md) defines the project vocabulary:
SDV, product line, feature model, digital thread, System 1/2/3, increment,
phase, record, and the viewpoint-related terms used across the model and docs.

## Name things consistently

Naming, identifiers, and abbreviations follow the authoritative
[naming conventions](../naming/naming-conventions.md) — including the
identifier-prefix and subject-namespace registries that tell you what
`INC-AEBS-010`, `REQ-AEBS-014`, or `EVID-MW-011` mean. `check_repo.py`
enforces the objective rules via `scripts/check_naming.py`.

## Repository conventions

- Directory names are Git-friendly kebab-case, with corrected spellings
  (for example `continuous-homologation`, not `continous-homologation`).
- Keep documents short and concrete; explain the user problem first, then
  the technical solution.
- Decisions go into Architecture Decision Records under
  `docs/architecture-decisions/`; see the [ADR index](../architecture-decisions/README.md).
- Never present examples as certified or homologated artifacts, and never
  claim compliance without traceable evidence.

## Next steps

- Read the [project charter](../project-goals/project-charter.md) for the
  full vision and scope.
- Browse the [roadmap](../../ROADMAP.md) to see what is in flight.
- Look at the [AEBS pilot](../../methodologies/sysmod-sysmlv2/pilots/aebs-pilot-charter.md)
  to see a complete increment chain in action.
