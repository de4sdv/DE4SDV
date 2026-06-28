# SysML v2 Semantic Audit

## Status

Draft semantic audit for the current DE4SDV SysML v2 textual notation baseline.

This audit separates three different claims:

1. **Syntax-valid** — a SysML v2 parser/validator accepts the file.
2. **Semantically appropriate** — the model uses SysML v2 constructs that match the engineering meaning.
3. **Engineering complete** — the model is sufficient for downstream design, V&V, or compliance decisions.

A file can be syntax-valid and still be semantically weak. That is the problem this audit starts to fix.

## Source discipline

Authoritative semantic checks should use the OMG SysML v2 specification/release materials and then validate syntax with the repository validation path.

The semantic repair in this increment uses the public SysML v2 release materials for the following constructs:

- `use case def` / `use case` for operational context and actor/subject framing;
- `action def` / `action` for operational behavior;
- `item def`, `in item`, `out item`, `flow`, and `first ... then ...` for operational information and sequencing;
- `concern def` and typed `concern` usages for stakeholder concerns;
- imported reusable `viewpoint def`, nested local `viewpoint`, and concrete `view` for stakeholder concerns and architecture viewpoint framing;
- native `requirement def` / `requirement` / `satisfy` remains the required direction for requirement slices.

## Current inventory

| File | Status | Finding | Action |
|---|---|---|---|
| `textual-notation-of-model/packages/features/aebs/aebs_operational_context.sysml` | repaired in this PR | Previously modeled operational actors, story, and steps almost entirely as generic parts. That was syntax-valid but semantically weak because behavior was represented as structure. | Reworked the operational story into use case and action constructs while preserving assumptions, gaps, validation seeds, and acceptance criteria as lightweight placeholders. |
| `textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_concerns_and_viewpoints.sysml` | added in this PR | Reusable DE4SDV method concern and viewpoint definitions did not exist as shared model assets. PR #44 temporarily kept method-like viewpoint definitions inside the AEBS feature package, and the first PR #45 draft left AEBS concerns as untyped concern usages. | Added a small shared method kernel with reusable `concern def` and `viewpoint def` elements for increment framing, product-line classification, regulatory scope, increment boundary, and method-stack review. Reusable `view def` elements are intentionally deferred until there are real cross-feature view construction recipes. These are not claimed as SAF-native viewpoints yet. |
| `textual-notation-of-model/packages/features/aebs/aebs_increment_framing.sysml` | repaired in PR #44 and refactored in this PR | Previously represented method stack, viewpoints, concerns, product-line classifications, scope, and gaps mostly as generic parts. The first repair draft made the viewpoints AEBS-specific, which would not scale across features. | AEBS now imports reusable DE4SDV method concern/viewpoint definitions, uses typed AEBS concern usages, nests feature-specific viewpoint usages inside concrete views, and exposes AEBS content through those views. |
| `textual-notation-of-model/snapshots/de4sdv-context-spike.sysml` | obsolete spike candidate | Minimal context sketch with only part definitions and no relationships. It is useful as historical evidence but weak as a current baseline. | Either retire from baseline documentation or upgrade into a real context model. |
| `textual-notation-of-model/libraries/covesa-vss-sysmlv2/COVESA_VSS.sysml` | mostly appropriate catalog layer | Uses attributes, enums, and metadata for generated signal/catalog semantics. Branches are represented as part definitions, which is acceptable only if documented as catalog grouping rather than architecture topology. | Follow-up should document catalog-layer semantics and avoid using the library as architecture interconnection evidence. |
| `textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml` | open PR #42, not on `main` yet | PR #42 now uses native requirement notation and marks the statements as requirement candidates, not accepted requirements. | Keep PR #42 draft until requirement quality gaps are reviewed. |

## Repairs performed so far

The operational context file now distinguishes:

- **operational subject and actors** via a SysML v2 use case;
- **operational behavior** via action definitions and an action usage;
- **information passed between operational actions** via item definitions and flows;
- **nominal sequencing** via `first ... then ...` successions;
- **open assumptions/gaps/criteria** as explicit placeholders rather than hidden completeness claims.

The increment framing file now distinguishes:

- **reusable DE4SDV method concern definitions** and **typed AEBS concern usages** via native `concern def` / `concern` constructs;
- **reusable DE4SDV method viewpoint definitions** in `DE4SDV_MethodViewpoints`;
- **view-local feature viewpoint usages** nested inside concrete AEBS views so they are satisfied by the containing view without polluting the package namespace;
- **feature-specific view selections** via concrete `view` usages that expose the AEBS package content and declare the current rendering directly;
- **method stack and product-line classification records** as lightweight model elements that remain intentionally less formal than executable architecture.

This does not make the AEBS model complete. It fixes two clear bad modeling patterns: behavior-as-parts and concerns/viewpoints-as-parts, without creating one-off viewpoint definitions per feature.

## Remaining semantic debt

- Requirement candidates still need quality refinement before becoming accepted design-input requirements.
- Operational assumptions and gaps may need a richer representation after the project decides whether to model them as metadata, concerns, requirements, constraints, or governance records.
- Increment framing still uses lightweight parts for method-stack and product-line classification records; that may be acceptable for framing, but later product-line variability modeling should use stronger semantics.
- VSS remains a catalog/library layer; functional interfaces and signal mappings must be added in a separate adapter/model slice.

## Acceptance criteria for semantic repairs

A semantic repair should meet all of these before being treated as complete:

- the construct choice is tied to engineering meaning;
- syntax validation passes locally or in privileged CI;
- the PR description states what validation proves and does not prove;
- the repair is small enough to review;
- deferred semantic debt remains explicit.
