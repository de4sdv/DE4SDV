# Reading the DE4SDV SysML v2 model

DE4SDV expresses its systems model in SysML v2 textual notation. The model is
not a diagram collection: the `.sysml` files are the source of truth, and the
diagrams you see in the model viewer are rendered *from* the declared views.

This guide explains, on a high level, the element kinds DE4SDV uses and why
it uses them. It is organized by what the elements *do* — from framing an
increment to recording evidence — so you can open any `.sysml` file under
`textual-notation-of-model/packages/` and read it with context.

The examples below use real elements from the AEBS and middleware feature
packages. Element names follow the same pattern across both pilots.

## The package structure

Every increment produces one or more **packages** (files) that live under
`textual-notation-of-model/packages/`:

- `methods/de4sdv/` — reusable DE4SDV method definitions (increment types,
  requirement-candidate types, product-line semantics, stakeholders,
  process phases, viewpoints).
- `methods/saf/` — the GfSE SAF viewpoint and concern definitions DE4SDV
  uses.
- `architecture/` — platform-stack and execution-environment definitions
  shared across features.
- `features/aebs/` and `features/middleware/` — the feature pilots; one
  file per increment slice (`middleware_requirements.sysml`, `aebs_logical_architecture.sysml`,
  ...).

Packages import only what they need (`private import`) and define their own
element names. **Why:** a contributor can review one slice — one engineering
question — without reading the whole model, and the package boundary keeps
naming collisions and unintended coupling out.

## The increment shell (every file starts here)

Every slice begins with a part that names the increment and its scope:

```sysml
part incMW007 : FeatureIncrement {
  doc /* INC-MW-007: middleware integration logical architecture. */
}
```

- `FeatureIncrement` (defined in `de4sdv_method_context.sysml`) is the
  bounded work package that the slice serves. Specializations exist for
  needs/requirements increments and similar.
- `doc /* ... */` blocks carry the rationale and identifier (INC-…), which
  is how the model keeps traceability to the increment workflow.
- Framing files additionally use `ProblemStatement`, `IncrementScope`,
  `IncrementTraceabilityShell`, and `IncrementEngineeringQuestion` parts.

**Why:** every slice answers one engineering question and says so in the
model itself — the file is self-describing for reviewers and for the viewer.

## Concerns, viewpoints, and views

DE4SDV works viewpoint-first:

```sysml
concern argumentationAssuranceConcern : ArgumentationAssuranceConcern {
  stakeholder systemsEngineer : SystemsEngineer;
  stakeholder verificationEngineer : VerificationEngineer;
}

view middlewareVerificationAssuranceView {
  viewpoint selectedArgumentationAssuranceViewpoint : ArgumentationAssuranceViewpoint {
    frame argumentationAssuranceConcern;
  }
  expose mw010ReferenceContractClaim;
  expose signalTranslationArgument010;
  ...
  render asTreeDiagram;
}
```

- **`concern`** — a topic of interest for named stakeholders (from
  `DE4SDV_Stakeholders` and the SAF packages).
- **`viewpoint`** — the convention that frames the concern; DE4SDV uses GfSE
  SAF viewpoints plus DE4SDV method-governance viewpoints (increment
  framing, product-line classification, regulatory scope).
- **`view`** — the scoped selection of elements that answers the concern.
  `expose` lists exactly what the view shows; `render` picks the expression
  (tree, interconnection diagram, table, matrix).

**Why:** views keep the model reviewable and scoped. A view answers a
stakeholder question; it is not a dump of a package. Because `expose` lists
elements explicitly, a view can never silently include elements the model
does not declare. Diagrams in the viewer are SysIDE renders of these views —
if a renderer omits a relationship, the model remains authoritative.

## Needs and requirements

Needs and requirements are modeled as **requirement candidates** — a
DE4SDV-owned hierarchy that specializes the SYSMOD seam:

```sysml
requirement def MiddlewareHealthMonitoringRequirement :> FunctionalRequirementCandidate;

requirement reqMonitorMiddlewareHealth : MiddlewareHealthMonitoringRequirement {
  doc /* REQ-MW-004 draft design-input requirement. */
  subject memberProduct : ProductLineMemberProduct;
  require constraint statement { language "English" /* Each SDV product-line
    member product shall monitor the health of the selected middleware
    integration boundary ... */ }
}
```

- `requirement def` declares the type; the lowercase `requirement` usage
  declares a concrete requirement with an ID (`REQ-MW-…`), a `subject`
  (what it constrains), and a verifiable `require constraint statement`.
- Candidate kinds distinguish functional, safety-constraint,
  product-line-constraint, traceability-constraint, and
  evidence-contract-traceability requirements, so reviewers can see the
  *kind* of obligation at a glance.
- Stakeholder **needs** stay in their own slice (`middleware_stakeholder_needs.sysml`,
  `aebs-needs-requirements` docs) — needs are not requirements.

**Why:** separating needs from requirements, and typing the requirement
kind, is what makes the trace chain reviewable: a safety-constraint
candidate cannot be mistaken for a functional requirement, and a draft
candidate is visibly a draft.

## Architecture elements: parts, ports, items, connections

Functional, logical, and physical slices share the same structural
vocabulary:

```sysml
part def MiddlewareIntegrationVandVBench {
  part system1MemberProduct : MiddlewareAutowareAAOSSDVConfiguredMember;
  part system2TestEnvironment : AOSPAAOSBuildRuntimeEnvironment;
  attribute scenario : MiddlewareScenarioIdentity;
}

port def SignalAccessApplicationPort {
  in item signalRequest : VehicleSignalAccessRequest;
  out item signalResponse : VehicleSignalAccessResponse;
}
```

- **`part def` / `part`** — the type/usage split: a definition declares the
  structure once; usages place it in a context.
- **`port def`** with typed `in`/`out` **`item`** — interfaces are explicit:
  a port says *which* item flows in and out, and the item type carries the
  semantics (`VehicleSignalAccessRequest`, `HealthForwardingStatus`, ...).
- **`attribute`** — typed properties such as scenario identity or timing.
- **`enum def`** — closed vocabularies (`MiddlewareScenarioIdentity`,
  `MiddlewareEvidenceOutcome`).
- **`dependency`** — trace links between elements (see below).
- Functional slices add `action`/flow definitions and state definitions for
  behavior; allocation from functions to logical elements is modeled as
  explicit dependencies/metadata, never as a diagram annotation.

**Why:** type/usage separation and typed ports are what make architecture
composable across product-line variants: the same `MiddlewareIntegrationVandVBench`
definition is reused by six verification cases with only the `scenario`
attribute changing. Interfaces are checkable by tools and humans alike.

## Variability and configuration

Product-line slices assemble **configured members** from shared assets:

```sysml
part def MiddlewareAutowareAAOSSDVConfiguredMember :> ProductLineMemberProduct {
  part platformStack : MiddlewareAutowareAAOSSDVReference;
  part middlewareBoundary : MiddlewarePhysicalSoftwareBoundary;
}

part configuredMember : MiddlewareAutowareAAOSSDVConfiguredMember {
  doc /* MW-CONFIG-001. Configuration evidence only. ... */
}
```

- `ProductLineMemberProduct`, `variation`/`variant` memberships, and
  `:>>` selections express *which* member product is configured and *what
  varies* — see `de4sdv_product_line.sysml` and
  `model-based-product-line-engineering/`.
- A characteristic is a **feature** only when it distinguishes one member
  product from another; otherwise it is a **common capability**. The model
  keeps this classification explicit (Phase 3) and assembles configurations
  in Phase 9.
- `DeferredProductLineScope` parts (with `GAP-…` doc IDs) record what is
  *not yet* decided — out-of-scope and deferred choices stay visible instead
  of being silently assumed.

**Why:** configuration evidence is not runtime proof. The doc comment on
`configuredMember` says exactly that — this is how the model prevents
"configuration exists" from being read as "the product works".

## Verification, evidence, and verdicts

The verification/evidence slices (`middleware_verification_evidence.sysml`,
`aebs_*_verification.sysml`, `aebs_nominal_evidence.sysml`) contain the
richest element set. The pattern, in order:

1. **Observation items** — `item def` types that capture what was observed
   (`VehicleSpeedTranslationObservation` with input/expected/observed
   values, `MiddlewareLifecycleObservation` with transition flags, ...).
2. **Retained evidence** — `RetainedMiddlewareEvidence` binds raw
   observations to identities: configuration, execution environment,
   contract, raw artifact, independent observer, a `disposition`
   (planned / observed-bounded / partial / blocked / accepted / rejected),
   and a **claim boundary**.
3. **Evaluation** — `ReplayedMiddlewareEvaluation` turns retained
   evidence into a scenario-scoped evaluation with an `outcome`
   (`passBoundedVerification`, `passBoundedValidation`, `failObservedBehavior`,
   `inconclusiveMissingEvidence`, `blockedTargetRuntime`, `errorEvidence`).
4. **Outcome → verdict** — a `calc def` (`MapEvidenceOutcomeToVerdict`) maps the
   outcome enum to a `VerdictKind` (`pass` / `fail` / `error` /
   `inconclusive`) from the SysML v2 standard library. Blocked or missing
   evidence can never map to `pass`.
5. **The V&V bench** — `MiddlewareIntegrationVandVBench` pairs the
   **System 1 configured member under evaluation** with the **System 2 test
   environment**, plus the scenario identity. This makes explicit *what is
   being evaluated* and *in what environment* — the two are never conflated.
6. **Acceptance criteria** — `requirement` usages (`AC-MW-010-…`) with a
   `subject bench` and a `require constraint`; they are the verifiable
   conditions the verification objectives check.
7. **Verification cases** — `verification def`/`verification` with a
   `subject` bench, `objective`s that `verify` acceptance criteria, and a
   three-action pipeline `collectData → processData → evaluateData` with
   `@VerificationMethod{ kind = (test, inspect, analyze) }` annotations
   (from the standard library). A `verificationSystem` part `perform`s the
   cases.
8. **Evidence artifacts** — parts typed by the execution-environment
   evidence hierarchy (`ExecutionEnvironmentEvidenceArtifact` →
   `InspectedExecutionEnvironmentEvidence`, `PlannedExecutionEnvironmentEvidence`)
   from `packages/architecture/execution_environments.sysml`. A planned
   artifact is visibly planned, and its doc comment names the evidence path
   and its limits (`boundedAAOSBootBaseline010`).
9. **Gaps** — `DeferredProductLineScope` parts (`GAP-MW-025..028`) record
   exactly which evidence does not exist yet.

**Why:** the whole chain exists to make one discipline mechanical: **a
verdict is only as strong as its evidence, and the model says which
environment, which contract, and which claim boundary that evidence belongs
to.** `planned` or `blocked` can never render as a runtime pass, and every
gap is a named element that stays visible until closed.

### Claims, arguments, and counter-claims

On top of the verdict chain, assurance slices add an argumentation layer
(framed by the SAF Argumentation Assurance viewpoint):

- **`MiddlewareClaim`** — what the configured member is asserted to
  realize, bounded by a `claimBoundary` (`CLM-MW-010-01`).
- **`MiddlewareAssuranceArgument`** — one argument per verification dimension
  (`AGT-MW-010-…`), each supported by verification cases and evidence via
  `dependency` links (`claimSupportedBy*`, `*ReinforcesArgument`).
- **`MiddlewareCounterClaim`** — explicit bounds on the claim where
  evidence is missing (`CCM-MW-010-…`), each traced to its gap.

Two views publish the two sides: the positive slice (`middlewareVerificationAssuranceView`)
and the challenge slice (`middlewareOpenCounterclaimAssuranceView`). **Why:**
DE4SDV does not hide weaknesses. Counter-claims and gaps are first-class
model elements precisely so an assurance argument shows what is *not* yet
established, not just what is.

## Trace links

Traceability is expressed as **`dependency` usages** in the SysML model —
not in YAML, not in prose:

```sysml
dependency startupValidationToDiscoveryRequirement
  from acceptanceCriterion010VehicleStartup
  to reqProvideServiceDiscovery;
```

Every phase traces to the prior phase's accepted elements (acceptance
criteria → requirements → needs → context), and verification/evidence traces
to the configured member, physical boundary, signal mapping, contract, and
execution environment. Pilot YAML files only *index* these dependency names;
they never replace them. **Why:** the trace chain lives in the artifact that
can be validated, queried, and rendered — and a PR can be reviewed for
"what traces to what" instead of trusting prose claims.

## Element kinds at a glance

| Kind | Used for | Example |
|---|---|---|
| `package` | one reviewable slice | `DE4SDV_MiddlewareRequirements` |
| `part def` / `part` | structure, types and usages | `MiddlewareIntegrationVandVBench` |
| `port def` | typed interface with `in`/`out` items | `SignalAccessApplicationPort` |
| `item def` | exchanged or observed information | `VehicleSpeedTranslationObservation` |
| `enum def` | closed vocabularies | `MiddlewareEvidenceOutcome` |
| `requirement def` / `requirement` | needs and verifiable obligations | `reqMonitorMiddlewareHealth` |
| `verification` (def/usage) | verification/validation cases | `signalTranslationVerification010` |
| `calc def` | deterministic mappings (outcome → verdict) | `MapEvidenceOutcomeToVerdict` |
| `concern` / `viewpoint` / `view` | scoped stakeholder-facing expressions | `middlewareVerificationAssuranceView` |
| `dependency` | trace links across the chain | `startupValidationToDiscoveryRequirement` |
| `doc /* */` | rationale, IDs, and explicit limits | `GAP-MW-025`, `MW-CONFIG-001` |

## What comes from the standard library

Some types are not defined in DE4SDV files: `VerdictKind`, `VerificationMethod`
(annotation kind), `Views`, and `ScalarValues` come from the SysML v2
standard library shipped with the pinned modeling environment. DE4SDV types
always specialize DE4SDV-owned seams (`DE4SDV_MethodContext`,
`DE4SDV_ProductLine`, `packages/architecture/execution_environments.sysml`)
so upstream libraries stay behind controlled boundaries — see
[`methodologies/sysmod-sysmlv2/de4sdv-tailoring.md`](../../methodologies/sysmod-sysmlv2/de4sdv-tailoring.md).

## Where this fits

- The **increment workflow** ([`methodologies/sysmod-sysmlv2/increment-workflow.md`](../../methodologies/sysmod-sysmlv2/increment-workflow.md))
  explains when each slice is produced.
- The **phase-to-artifact map** ([`methodologies/sysmod-sysmlv2/process-mapping.md`](../../methodologies/sysmod-sysmlv2/process-mapping.md#phase-to-artifact-map))
  names the files per phase.
- The **viewpoint map** ([`methodologies/sysmod-sysmlv2/saf-viewpoint-map.md`](../../methodologies/sysmod-sysmlv2/saf-viewpoint-map.md))
  explains which viewpoints frame which concerns.
