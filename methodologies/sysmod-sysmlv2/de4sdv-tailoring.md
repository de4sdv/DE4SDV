# DE4SDV Tailoring of SYSMOD SysML v2

## Tailoring principle

DE4SDV consumes the exact-pinned SYSMOD Sysand package through a narrow local
adapter. Package consumption does not mean implementing the upstream method
wholesale.

The rule is:

```text
Resolve the exact upstream package
  -> expose selected definitions through DE4SDV_SYSMODAdapter
  -> adapt them through DE4SDV method packages
  -> extend only where DE4SDV needs SDV product-line, evidence, governance, or open-source workflow semantics
  -> keep the source mapping and tailoring rationale explicit
```

Conceptually:

```text
MBSE4U SYSMOD Sysand package
  -> exact-pinned external definitions
DE4SDV_SYSMODAdapter
  -> controlled stakeholder, requirement, use-case, and occurrence seams
DE4SDV method packages
  -> selectively adapted problem-statement, context, stakeholder, concern, viewpoint, and traceability concepts
DE4SDV model packages
  -> project-specific context, requirements, architecture, variability, and assurance views
```

This avoids two bad outcomes:

- inventing an incompatible DE4SDV-only method vocabulary when a useful external pattern exists;
- leaking an external namespace and its project-root assumptions across the model.

## Current local method packages

Current DE4SDV method packages live under:

```text
textual-notation-of-model/packages/methods/de4sdv/
```

| Package | Purpose | Source relationship |
|---|---|---|
| `DE4SDV_SYSMODAdapter` | Defines the sole upstream import boundary and selected DE4SDV-owned seams. | Exact package dependency; no vendored source. |
| `DE4SDV_MethodContext` | Defines `ProblemStatement`, requirement-candidate lifecycle types, and `SystemContext` for increment anchoring. It intentionally avoids a generic `ProjectContext` layer. | DE4SDV-owned adaptation; no upstream specialization yet. |
| `DE4SDV_Stakeholders` | Defines reusable stakeholder role part definitions and lightweight risk/effort/category metadata. | DE4SDV-owned roles; a later pilot may specialize the adapter seam. |
| `DE4SDV_MethodViewpoints` | Defines DE4SDV-specific governance concerns and viewpoints with no SAF equivalent. | DE4SDV-owned; SAF definitions remain in `SAF_Viewpoints`. |
| `DE4SDV_MethodProcess` | Models the 13-phase increment sequence, SAF domain assignment, trace chain, and recurring controls. | DE4SDV-owned process; not replaced or reordered by the package. |
| `DE4SDV_ProductLine` | Defines product-line, feature/common-capability, configuration, and derivation semantics. | DE4SDV-owned extension outside the first adapter scope. |
| `DE4SDV_OperationalContext` | Defines reusable operational actors and context semantics. | DE4SDV-owned; operational artifacts provide rationale for later functional architecture. |

## Adoption rule

A new external method concept may enter DE4SDV only when the PR states:

1. source concept or pattern;
2. DE4SDV construct being added;
3. reason DE4SDV needs it now;
4. tailoring or extension from the source;
5. explicit non-claims, such as “not a full upstream implementation” or “not compliance evidence”.

## Relationship to SAF

The GfSE System Architecture Framework can be used as the viewpoint and architecture-description layer around this method:

```text
SAF viewpoint / concern framing
  -> identifies stakeholder concern and required view
Selected SYSMOD architecture artifact or method pattern
  -> provides method/model structure where useful
DE4SDV method package
  -> adapts the pattern for SDV product-line assurance and open-source governance
DE4SDV artifact
  -> implements it in Markdown, YAML, and/or SysML v2 textual notation
```

Example:

```text
SYSMOD problem-statement pattern
  -> DE4SDV_MethodContext::ProblemStatement
  -> AEBS needs/requirements system context
```

SAF domains and SYSMOD architecture artifacts are independent dimensions:

- Operational-domain scenarios, needs, and capabilities provide rationale for
  functional architecture; they are not aliases for functional architecture.
- Functional architecture and technology-independent system architecture are
  distinct artifact kinds in the Conceptual Domain.
- Concrete product/implementation architecture is exposed through Physical-
  domain viewpoints.
- A SYSMOD product architecture is not a DE4SDV configured member product.

The adapter must preserve trace relationships between these artifacts instead
of creating semantic aliases between their labels.

## Guardrails

- Keep method packages small and reviewable.
- Do not claim that DE4SDV implements full SYSMOD unless the project explicitly decides that and validates the upstream dependency/toolchain.
- Keep every `SYSMOD` import inside `DE4SDV_SYSMODAdapter`.
- Do not vendor package source; resolve it with `sysand sync` from the exact lock.
- Do not specialize `Project`, `AIProject`, or requirement-boilerplate
  constraints without a separate decision and upstream review.
- Preserve traceability from stakeholder concerns to needs, requirements, model elements, evidence, and baselines.
- Do not claim certification or homologation compliance from the presence of model artifacts alone.
- Upgrade the exact package constraint and lock file together; validate the same
  commit before readiness claims.
