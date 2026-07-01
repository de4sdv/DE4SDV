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
- native `requirement def` / `requirement` / `satisfy` remains the required direction for requirement slices;
- requirement `stakeholder` parameters are part usages typed by shared stakeholder role part definitions;
- selected external method patterns, such as the SYSMOD/SysML v2 problem-statement pattern, should enter through DE4SDV method packages with explicit tailoring notes rather than full upstream method implementation.

## Current inventory

| File | Status | Finding | Action |
|---|---|---|---|
| `textual-notation-of-model/packages/features/aebs/aebs_operational_context.sysml` | repaired in this PR | Previously modeled operational actors, story, and steps almost entirely as generic parts. That was syntax-valid but semantically weak because behavior was represented as structure. | Reworked the operational story into use case and action constructs while preserving assumptions, gaps, validation seeds, and acceptance criteria as lightweight placeholders. |
| `textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_concerns_and_viewpoints.sysml` | added in this PR | Reusable DE4SDV method concern and viewpoint definitions did not exist as shared model assets. PR #44 temporarily kept method-like viewpoint definitions inside the AEBS feature package, and the first PR #45 draft left AEBS concerns as untyped concern usages. | Added a small shared method kernel with reusable `concern def` and `viewpoint def` elements for increment framing, product-line classification, regulatory scope, increment boundary, and method-stack review. Reusable `view def` elements are intentionally deferred until there are real cross-feature view construction recipes. These are not claimed as SAF-native viewpoints yet. |
| `textual-notation-of-model/packages/features/aebs/aebs_increment_framing.sysml` | repaired in PR #44 and refactored in this PR | Previously represented method stack, viewpoints, concerns, product-line classifications, scope, and gaps mostly as generic parts. The first repair draft made the viewpoints AEBS-specific, which would not scale across features. | AEBS now imports reusable DE4SDV method concern/viewpoint definitions, uses typed AEBS concern usages, nests feature-specific viewpoint usages inside concrete views, and exposes AEBS content through those views. |
| `textual-notation-of-model/snapshots/de4sdv-context-spike.sysml` | obsolete spike candidate | Minimal context sketch with only part definitions and no relationships. It is useful as historical evidence but weak as a current baseline. | Either retire from baseline documentation or upgrade into a real context model. |
| `textual-notation-of-model/libraries/covesa-vss-sysmlv2/COVESA_VSS.sysml` | mostly appropriate catalog layer | Uses attributes, enums, and metadata for generated signal/catalog semantics. Branches are represented as part definitions, which is acceptable only if documented as catalog grouping rather than architecture topology. | Follow-up should document catalog-layer semantics and avoid using the library as architecture interconnection evidence. |
| `textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml` | added in PR #42 update | The AEBS needs/requirements slice was SYSMOD-inspired but had no explicit problem statement or system context anchor. | Added a small DE4SDV method context package adapting the SYSMOD/SysML v2 problem-statement pattern with `ProblemStatement` and `SystemContext`. A generic `ProjectContext` layer is intentionally not introduced. This is not a full upstream SYSMOD implementation. |
| `textual-notation-of-model/packages/methods/de4sdv/de4sdv_stakeholders.sysml` | added in PR #42 update | Stakeholder role definitions were initially local to the AEBS needs/requirements slice, even though SysML v2 stakeholder parameters are reusable role usages typed by part definitions. | Added a shared DE4SDV stakeholder role package and imported it into the AEBS needs/requirements slice. |
| `textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml` | open PR #42, repaired in this PR update | Initial PR #42 moved from requirements-as-parts to native requirement notation, but stakeholder needs were still generic parts, V&V/evidence/quality records were modeled as generic parts in the requirements slice, needs were briefly duplicated as a concern usage, satisfaction was asserted against placeholder parts before any functional/logical realization existed, and the AEBS common-capability intent was weakened by `ApplicableMemberProduct` subset wording. | Needs are now requirement-like usages only, AEBS is modeled as a common capability required across product-line member products rather than an applicable-subset feature, requirement candidates carry required constraint bodies, stakeholder parameters use shared role definitions, V&V/evidence/gap/quality planning records stay in Markdown/YAML instead of generic SysML part taxonomies, and satisfaction assertions are deferred until concrete satisfying features exist. Keep PR #42 draft until requirement quality gaps are reviewed. |

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

The needs/requirements file now distinguishes:

- **problem statement / system context** as a DE4SDV method-context adaptation of the SYSMOD/SysML v2 problem-statement pattern;
- **stakeholder needs** as native requirement usages rather than generic parts or duplicate concern usages;
- **stakeholder roles** as shared part definitions imported into feature slices and used by native `stakeholder` parameters;
- **requirement candidates** as native requirement usages with `require constraint` bodies rather than prose-only placeholders;
- **satisfaction assertions** as deferred until a later functional/logical realization model contains concrete satisfying features.

The V&V planning fields, evidence status, gaps, and requirement quality findings remain in the Markdown/YAML reviewer artifacts for PR #42. They are intentionally not modeled as generic SysML part taxonomies in `aebs_needs_requirements.sysml`.

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
