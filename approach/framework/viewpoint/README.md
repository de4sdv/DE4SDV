# Viewpoints

Viewpoints, views, and concerns are how DE4SDV keeps model work scoped to
stakeholder questions instead of growing a whole-system model. This page
explains the concepts, where they live in the model, and how to select
viewpoints for an increment.

For the practical selection map — which viewpoints to use for which kind of
increment — see
[`methodologies/sysmod-sysmlv2/saf-viewpoint-map.md`](../../../methodologies/sysmod-sysmlv2/saf-viewpoint-map.md).

## Concepts

- **Concern** — any topic of interest for one or more stakeholders:
  functionality, variability, safety, security, compliance, cost,
  evolvability. Concerns are not risks; they are the questions a view must
  answer.
- **Viewpoint** — a convention that frames one or more concerns: who the
  stakeholders are, what the viewpoint addresses, and how views are
  expressed. In SysML v2, a `viewpoint def` frames `concern usage` elements.
- **View** — the result of applying a viewpoint to the model: a scoped
  selection of model elements that answers the framed concerns. In SysML v2,
  a `view` selects a `viewpoint` and exposes the elements needed to answer
  it.

A viewpoint is not a diagram type and not a folder. It is a contract that
says *what question is answered*, *for whom*, and *with what kind of
expression* (tree, table, interconnection diagram, matrix, ...). Views are
reviewable model elements; the diagrams in the model viewer are what SysIDE
renders from them.

## How DE4SDV uses viewpoints

DE4SDV uses the GfSE System Architecture Framework (SAF) as the viewpoint
layer around its SYSMOD-style method flow, plus a small set of DE4SDV-owned
governance viewpoints that have no SAF equivalent.

| Source | Package | Viewpoints |
|---|---|---|
| GfSE SAF | `textual-notation-of-model/packages/methods/saf/SAF_Viewpoints.sysml` | Operational, Conceptual (System*), and Physical-domain viewpoints actually used by DE4SDV increments; names match the published SAF documentation |
| DE4SDV method | `textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_concerns_and_viewpoints.sysml` | Increment framing, product-line classification, and regulatory scope (without compliance claim) |

Concrete views live in the feature packages next to the elements they expose
(for example `aebs_operational_context.sysml` contains `aebsOperationalContextView`).
Each view selects a viewpoint with `frame` bindings to concerns, and its
exposures are scoped to the elements needed to answer those concerns.

## Selecting viewpoints for an increment

1. State the engineering question the increment answers.
2. Select the smallest useful set of viewpoints — those that answer
   stakeholder concerns, not every viewpoint that is available.
3. Produce the matching DE4SDV artifacts.
4. Record omitted viewpoints as out of scope.
5. Add trace links where relevant.

The
[`saf-viewpoint-map.md`](../../../methodologies/sysmod-sysmlv2/saf-viewpoint-map.md)
groups viewpoints into practical subsets (increment framing, operational
feature, system behavior and requirements, safety/security, logical
realization, physical/software realization) and shows the AEBS pilot
selection. The
[`process-mapping.md`](../../../methodologies/sysmod-sysmlv2/process-mapping.md#viewpoint-flow-per-phase)
table shows which viewpoints each of the 13 phases typically produces.

## Stakeholders and concerns by system layer

The stakeholder groups below frame the concerns DE4SDV addresses. They are
not viewpoints themselves — they are the audiences whose concerns the SAF and
DE4SDV method viewpoints frame.

### System 1 product-line stakeholders

Primary stakeholders:

- systems engineers;
- product-line engineers;
- safety and cybersecurity engineers;
- compliance specialists; and
- SDV architects.

Typical concerns:

- SDV variant structure and feature configurations;
- product-line commonality and variability;
- behavior, interfaces, and operational scenarios;
- safety, security, privacy, and compliance boundaries; and
- verification and validation targets for configured variants.

Representative views and artifacts:

- feature models, feature configurations, and product models
  (`model-based-product-line-engineering/`);
- operational context and story views (Operational domain);
- system context, use case, requirement, and interface views (Conceptual
  domain);
- physical/software structure and mapping views (Physical domain);
- variant-specific evidence links (`continuous-homologation/`).

### System 2 life-cycle management stakeholders

Primary stakeholders:

- MBSE/SysML v2 practitioners;
- simulation and digital-twin engineers;
- DevSecOps engineers;
- assurance and evidence managers; and
- configuration managers.

Typical concerns:

- engineering process flow;
- SysML v2 model structure and reuse;
- digital-thread traceability;
- simulation and digital-twin scope, synchronization, and credibility;
- baseline and evidence management;
- continuous homologation workflow; and
- reproducible automation.

Representative views and artifacts:

- SysML v2 packages and libraries (`textual-notation-of-model/`);
- increment framing, product-line classification, and regulatory scope views
  (DE4SDV method viewpoints);
- traceability links (`digital-continuity/`);
- evidence registers (`continuous-homologation/evidence-register.md`);
- baseline registers (`configuration-management/baseline-register.md`);
- CI/CD and DevSecOps workflows (`devsecops/`, `.github/workflows/`).

### System 3 innovation ecosystem stakeholders

Primary stakeholders:

- maintainers;
- contributors;
- upstream project owners;
- standards participants;
- methodology owners; and
- toolchain maintainers.

Typical concerns:

- governance and review workflow;
- standards and upstream alignment;
- ADRs and decision traceability;
- external dependency adoption;
- community learning and contribution pathways;
- method and tool evolution; and
- ecosystem diversity without lock-in.

Representative artifacts:

- project charter and governance documents (`docs/project-goals/`,
  `GOVERNANCE.md`);
- contribution guides (`CONTRIBUTING.md`, `docs/getting-started/`);
- ADRs (`docs/architecture-decisions/`);
- source notes and standards maps (`docs/references/`, `standards/`);
- roadmap items (`ROADMAP.md`);
- maintainer review checklists (`methodologies/sysmod-sysmlv2/review-checklist.md`).

## Browsing views

Every declared view is rendered in the model viewer
(<https://viewer.de4sdv.org>, or locally with
`python -m tools.sysml_html_viewer.serve --repo . --port 8787`). Hover a
viewpoint name in the viewer to see its SAF description; left-click opens the
SAF user documentation page.

## Guardrails

- SAF selects views; it does not replace the method flow.
- Viewpoints are chosen because they answer stakeholder concerns, not because
  they are available.
- A missing viewpoint is acceptable when explicitly out of scope.
- Compliance-oriented viewpoints may register constraints and evidence gaps,
  but must not imply regulatory approval.
- Verification viewpoints check requirement satisfaction; validation
  viewpoints check stakeholder fitness-for-use in context. Keep both visible.
- Views reflect the model only — never invent elements that the SysML source
  does not declare.
