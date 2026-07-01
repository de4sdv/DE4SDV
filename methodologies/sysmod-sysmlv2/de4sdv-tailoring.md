# DE4SDV Tailoring of SYSMOD SysML v2

## Tailoring principle

DE4SDV uses SYSMOD SysML v2 material as a source-backed method reference, not as a method to implement wholesale.

The rule is:

```text
Reuse selected external method patterns
  -> adapt them through DE4SDV method packages
  -> extend only where DE4SDV needs SDV product-line, evidence, governance, or open-source workflow semantics
  -> keep the source mapping and tailoring rationale explicit
```

Conceptually:

```text
MBSE4U SYSMOD / SysML v2 examples
  -> source-backed method patterns
DE4SDV method packages
  -> selectively adapted problem-statement, context, stakeholder, concern, viewpoint, and traceability concepts
DE4SDV model packages
  -> project-specific context, requirements, architecture, variability, and assurance views
```

This avoids two bad outcomes:

- inventing an incompatible DE4SDV-only method vocabulary when a useful external pattern exists;
- cloning or vendoring a full upstream method library before DE4SDV actually needs it.

## Current local method packages

Current DE4SDV method packages live under:

```text
textual-notation-of-model/packages/methods/de4sdv/
```

| Package | Purpose | Source relationship |
|---|---|---|
| `DE4SDV_MethodContext` | Defines `ProblemStatement` and `SystemContext` for increment anchoring. It intentionally avoids a generic `ProjectContext` layer. | Selective adaptation of the SYSMOD/SysML v2 problem-statement pattern. |
| `DE4SDV_Stakeholders` | Defines reusable stakeholder role part definitions and lightweight risk/effort/category metadata. | Aligns with SysML v2 stakeholder-parameter semantics and the SYSMOD stakeholder-property pattern. |
| `DE4SDV_MethodViewpoints` | Defines reusable DE4SDV concern and viewpoint definitions for method review. | DE4SDV method layer; SAF mapping remains follow-up work, not a claim of SAF-native viewpoint definitions. |

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
Selected SYSMOD/SysML v2 method pattern
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

## Guardrails

- Keep method packages small and reviewable.
- Do not claim that DE4SDV implements full SYSMOD unless the project explicitly decides that and validates the upstream dependency/toolchain.
- Do not vendor or import upstream method libraries casually; consume selected concepts through DE4SDV packages first.
- Preserve traceability from stakeholder concerns to needs, requirements, model elements, evidence, and baselines.
- Do not claim certification or homologation compliance from the presence of model artifacts alone.
- Prefer commit-pinned dependencies over floating references if executable upstream tooling is introduced later.
