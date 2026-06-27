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
- native `requirement def` / `requirement` / `satisfy` remains the required direction for requirement slices.

## Current inventory

| File | Status | Finding | Action |
|---|---|---|---|
| `textual-notation-of-model/packages/features/aebs/aebs_operational_context.sysml` | repaired in this PR | Previously modeled operational actors, story, and steps almost entirely as generic parts. That was syntax-valid but semantically weak because behavior was represented as structure. | Reworked the operational story into use case and action constructs while preserving assumptions, gaps, validation seeds, and acceptance criteria as lightweight placeholders. |
| `textual-notation-of-model/packages/features/aebs/aebs_increment_framing.sysml` | needs follow-up | Method stack, viewpoints, concerns, product-line classifications, scope, and gaps are still represented mostly as generic parts. | Follow-up should introduce `concern`, `viewpoint`, and possibly `view` constructs where validation supports them. |
| `textual-notation-of-model/snapshots/de4sdv-context-spike.sysml` | obsolete spike candidate | Minimal context sketch with only part definitions and no relationships. It is useful as historical evidence but weak as a current baseline. | Either retire from baseline documentation or upgrade into a real context model. |
| `textual-notation-of-model/libraries/covesa-vss-sysmlv2/COVESA_VSS.sysml` | mostly appropriate catalog layer | Uses attributes, enums, and metadata for generated signal/catalog semantics. Branches are represented as part definitions, which is acceptable only if documented as catalog grouping rather than architecture topology. | Follow-up should document catalog-layer semantics and avoid using the library as architecture interconnection evidence. |
| `textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml` | open PR #42, not on `main` yet | PR #42 now uses native requirement notation and marks the statements as requirement candidates, not accepted requirements. | Keep PR #42 draft until requirement quality gaps are reviewed. |

## Repair performed in this increment

The operational context file now distinguishes:

- **operational subject and actors** via a SysML v2 use case;
- **operational behavior** via action definitions and an action usage;
- **information passed between operational actions** via item definitions and flows;
- **nominal sequencing** via `first ... then ...` successions;
- **open assumptions/gaps/criteria** as explicit placeholders rather than hidden completeness claims.

This does not make the AEBS model complete. It only fixes the first bad modeling pattern: behavior-as-parts.

## Remaining semantic debt

- Increment framing still needs concern/viewpoint/view modeling.
- Requirement candidates still need quality refinement before becoming accepted design-input requirements.
- Operational assumptions and gaps may need a richer representation after the project decides whether to model them as metadata, concerns, requirements, constraints, or governance records.
- VSS remains a catalog/library layer; functional interfaces and signal mappings must be added in a separate adapter/model slice.

## Acceptance criteria for semantic repairs

A semantic repair should meet all of these before being treated as complete:

- the construct choice is tied to engineering meaning;
- syntax validation passes locally or in privileged CI;
- the PR description states what validation proves and does not prove;
- the repair is small enough to review;
- deferred semantic debt remains explicit.
