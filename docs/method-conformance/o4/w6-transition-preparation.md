# W6 rename-transition preparation (inert scaffolding)

Preparation record for the W6 rename/alias/deprecation transition. This
document and the files it describes are **preparation, not authorization**.

## Purpose

Give the W6 rename decisions one reviewed, machine-checked place to land
without performing any part of them early:

- `docs/method-conformance/o4/w6-transition-plan.yaml` — the plan skeleton
  (`de4sdv.o4-w6-transition-plan/v1`), one entry per decided-pending W6
  identity, every `authorization: null`.
- `de4sdv/semantic/rename_transition.py` — build-time validator for that
  plan (`load_plan` / `validate_plan` / `transition_state` /
  `authorized_entries`). Not imported by any runtime semantic module.
- `tests/test_rename_transition.py` — fail-closed proof for the above.

## Explicit non-activation

Nothing here executes or changes identities:

- no rename is performed;
- no alias is emitted;
- no deprecation interval is active;
- no runtime consumer reads the plan or the module.

`transition_state` can only report `pending` for the committed plan; the
`decided` branch exists solely so the schema logic can be exercised against
synthetic in-memory plans. Committing an authorized entry requires a future
reviewed change, not this scaffolding.

## Fail-closed rules

`validate_plan` refuses, with an error naming the problem:

- a schema id other than `de4sdv.o4-w6-transition-plan/v1`, or a status other
  than `preparation`;
- unknown top-level keys (only `schema`, `status`, `note` are allowed) and
  unknown entry keys (only `identity`, `proposed_successor`, `authorization`);
- duplicate, empty, or non-identifier identities;
- an empty or non-identifier `proposed_successor`; new proposed names must
  also be lowercase-initial (`^[a-z][A-Za-z0-9]*$`), except the decision-15
  trace entries, whose successor is an existing register identity
  (`RequiredTraceChain`) or an as-yet-undecided name and therefore validates
  as an identifier;
- any non-null `authorization`: the message names the unresolved owner
  decision (`decision-1` for the five renames, `decision-15` for the
  trace-chain identities).

`allow_authorized` exists only for synthetic in-memory plans; it additionally
requires an authorization record shaped `{decision, record}` with a recognized
decision id and a non-empty evidence reference.

## Dependency on owner decisions

Both plan sources are gated in `docs/method-conformance/o4/o4-execution-register.json`:

- **decision-1** — approve the five renames (`allocatedToArchitecture`,
  `hasRelevantFunction`, `hasValidationScenario`, `hasRegulatorySource`,
  `logicalAllocatedToPhysical`) and the alias/deprecation policy per predicate;
  rows: `realizedBy`, `specifiesFunction`, `validatedBy`, `constrainedBy`,
  `deployedTo`.
- **decision-15** — confirm the trace-chain successor identity name; rows:
  `RequiredTraceChain`, `TraceLink` (merged shell `IncrementTraceabilityShell`).

Successor names are taken from the per-row `target.proposed_name` in
`docs/method-conformance/o4/ontology-review/integrated-review.json`, with two
recorded annotations:

1. `constrainedBy` — the review's verbatim proposal is
   `hasRegulatorySource (proposed)`. The plan stores the identifier portion
   `hasRegulatorySource` (the parenthetical is review annotation, not part of a
   name); the verbatim string is preserved in the plan's `note`.
2. `IncrementTraceabilityShell` — the review proposes prose ("Increment trace
   expectation (redesigned RequiredTraceChain)") and the register records
   `merge_into: RequiredTraceChain`; the successor **identity name is pending
   decision-15**, so `RequiredTraceChain` is carried as the working successor
   (all `authorization: null`), not as an approved name.

## Post-decision sequence (sketch, not a commitment)

1. Owner answers decision-1 / decision-15 (owner-decision record).
2. This plan is updated in a reviewed change: the answered entries receive an
   explicit `authorization` record (`{decision, record}` pointing at the
   decision evidence) under `allow_authorized` validation, and the review's
   `proposed_name` annotations are reconciled to approved names.
3. Only then a future reviewed W6 migration performs the renames, alias and
   deprecation window work, with exact-revision equivalence evidence per
   `retirement_condition` in the execution register.

## Boundary

This document is preparation. It grants no authority, approves no successor
name, opens no deprecation interval, and authorizes no migration. Identity
names are unchanged until the owner answers decision-1 and decision-15 and a
separate reviewed migration lands.