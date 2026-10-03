# W6 approved semantic implementation boundary

## Purpose and scope

The owner has approved all six semantic directions. Implementation must no
longer treat the historical advisory alternatives as unanswered questions.
`approved-semantic-decisions.yaml` records those scoped approvals;
`w6-transition-plan.yaml` version 2 reconciles the eight relationship/trace
transition entries against them. Assurance and V&V approval scopes are recorded
in the same owner record, but their implementation is not a rename entry.

`de4sdv/semantic/rename_transition.py` is build-time governance only, with no
runtime consumers. Its `approved` state means direction approved, not deployed,
accepted or retired. No automatic compatibility aliases are authorized.

## Accepted decisions and engineering obligations

The historical review/register retain their inspection-time gate identities.
Tests compare those prerequisite sets against the validator; scoped owner
records resolve them. Historical gate text is not a new approval request.

- `realizedBy`, `specifiesFunction`, `validatedBy`, `deployedTo`: decision-1.
- `constrainedBy`: decision-1 plus decision-2, resolved as provenance only.
- `RequiredTraceChain` and `TraceLink`: decision-8 plus decision-15.
- `IncrementTraceabilityShell`: its own register gate set is empty; its proposed
  merge into `RequiredTraceChain` inherits that target's decision-8 and
  decision-15 prerequisites. This is not a new intrinsic gate on the shell.

The old `allocatedToArchitecture`, `hasRelevantFunction` and
`logicalAllocatedToPhysical` advisory alternatives are superseded. The successor
uses one versioned `allocatedTo`; genuine weaker dependencies are preserved,
not automatically converted. `hasValidationScenario` is planning and
`hasRegulatorySource` is controlled provenance. Trace successor names and wiring
are ordinary engineering decisions, not another owner gate.

## Fail-closed contract

Version 2 requires the fixed repository approval-record path, explicit false
activation/automatic-alias flags, exact accounting of all eight identities,
accepted treatment, and complete applicable decision sets. Each authorization
must resolve to the exact topic fragments covering that set. Missing records,
unknown/duplicate keys or identities, incomplete approvals, contradictory flags
and superseded advisory treatments refuse. The owner record must retain all six
topics and cannot authorize production activation, whole-consumer retirement,
PLE adoption or upstream contact.

Historical version 1 preparation inputs remain supported. Its synthetic
`decided` state proves schema consistency only; it never becomes actual approval.
`allow_authorized=True` cannot bypass version 2 record resolution. Repository
record validation is not independent authentication of the owner's identity.

## Delivery and operational boundary

Deliver this reconciliation with substantive model and consumer implementation,
not a preparation-only PR. Runtime meaning comes from model-derived versioned
contracts and API witness/identity evidence, never these governance strings.
Preserve frozen O3 inputs/meanings and historical evidence; rebind changed
generation inputs. Exact-head checks and independent review remain required.
Production activation, actual consumer retirement and operational acceptance
retain their own evidence and authorization gates.
