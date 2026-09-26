# W6 rename-transition preparation (inert scaffolding)

## Purpose and scope

Prepare a machine-checked place for future decisions without activating them.
The plan `w6-transition-plan.yaml` carries five proposed predicate renames and
one proposed shell merge. It does not cover all nine W6 register rows.
`RequiredTraceChain`, `TraceLink`, `hasEvidenceStatus` and `supportedByEvidence`
are not separate entries in this six-entry preparation plan.

The module `de4sdv/semantic/rename_transition.py` is build-time only, with no
runtime consumers. Every committed authorization remains null. No rename,
alias, deprecation interval, semantic admission or migration is performed.

## Required decisions

The canonical source is `o4-execution-register.json`; tests compare its gate
sets against the validator's supported identity rules.

- `realizedBy`, `specifiesFunction`, `validatedBy`, `deployedTo`: decision-1.
- `constrainedBy`: decision-1 plus decision-2 (provenance versus normative meaning).
- `RequiredTraceChain` and `TraceLink`: decision-8 plus decision-15.
- `IncrementTraceabilityShell`: its own register gate set is empty; its proposed
  merge into `RequiredTraceChain` inherits that target's decision-8 and
  decision-15 prerequisites. This is not a new intrinsic gate on the shell.

Successors remain proposals from `ontology-review/integrated-review.json`.
`hasRegulatorySource (proposed)` retains its annotation in the plan note, while
its identifier is `hasRegulatorySource`. `RequiredTraceChain` is a working
successor name, not an approved trace redesign.

## Fail-closed contract

Only `schema`, `status`, `note`, `entries` are allowed at top level. Entries
carry exactly `identity`, `proposed_successor`, `authorization`. Unknown keys,
duplicate identities, malformed identifiers and duplicate YAML keys are refused.
Proposed names are lowercase-initial except trace successor identifiers.

Loading the committed plan refuses every non-null authorization. The
`allow_authorized=True` mode exists for synthetic schema exercises only:
`authorization` must contain exactly `decisions` (a unique list equal to the
complete applicable gate set) and `record` (a non-empty reference). Unknown
identities have no authorization rule. Both public state helpers validate
explicitly supplied documents before interpreting them.

A synthetic `decided` result proves schema consistency only, not that an owner
actually approved anything. A reference is not independent approval evidence.
The default load path remains inert regardless of synthetic test results.

## Later migration

Resolve every applicable owner decision, then propose a separately reviewed
change that reconciles successor names, evidence, alias/deprecation policy and
migration tests. This scaffold cannot authorize that change. RequiredTraceChain
and TraceLink redesign, evidence-status work, and assurance work remain outside
this prepared implementation's scope.
