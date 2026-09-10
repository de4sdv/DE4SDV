# Result Algebra — normative schema spelling (Package A)

This document fixes the exact field spellings, allowed values, and the complete
finite reason vocabulary for the deterministic method-conformance engine. It
implements the frozen baseline §8 ("Final schema spelling and the complete
finite reason vocabulary are fixed in Increment A") without changing any rule.
Source of authority: [conformance-baseline.md](conformance-baseline.md)
(digest `427410f3070ed591287ec0dd3b819be7e95ee22fa7608b4c87d1e82192abd661`).

## Fields and permitted values (exact spelling)

```text
assessment_coverage   : "ASSESSED" | "UNASSESSED"
evaluation_state      : "COMPLETE" | "INDETERMINATE" | "ERROR" | null
conformance_verdict   : "PASS" | "FAIL" | "NOT_APPLICABLE" | null
readiness             : "READY" | "BLOCKED"          (only inside a readiness block)
readiness_target      : { type: "TASK_ENTRY" | "PHASE_EXIT" | "PR_MERGE", id: string }
reason_codes          : [ ReasonCode, ... ]           (machine-readable, finite vocabulary below)
```

`null` is JSON null — not a string, not a hidden default, not PASS, and not
`NOT_APPLICABLE`. Values are exact-match strings; comparisons are case-sensitive.

## Finite reason vocabulary (complete, v1)

```text
CONTRACT_UNAVAILABLE      no executable contract exists for the unit
OUTSIDE_REQUESTED_SCOPE   unit exists but is not selected by the declared scope
NOT_ATTEMPTED             no evaluation was attempted for the unit
APPLICABILITY_UNRESOLVED  applicability could not be established either way
INPUT_UNAVAILABLE         a necessary input, reference, or page is missing or truncated
INVALID_CONTRACT          contract failed validation (duplicate ID, unknown predicate,
                          type mismatch, invalid bounds, unknown status literal,
                          unresolved policy reference, unsupported applicability form,
                          invalid dependency structure)
BINDING_MISMATCH          identity/integrity mismatch between bound artifacts
SCOPE_RESOLUTION_ERROR    invalid or ambiguous selector; failure to resolve scope
POPULATION_POLICY_VIOLATION  non-empty population required but empty under the
                          declared policy (diagnostic, verdict is FAIL)
EVIDENCE_SCOPE_MISMATCH   declared execution scope does not match the tested scope
ACCEPTANCE_AUTHORITY_MISSING  no attributable authorized acceptance decision exists
STALE_INPUT               delivery input moved or was re-read as changed (delivery projection)
```

Unknown reason codes are a serialization error. Extending this vocabulary
requires a reviewed amendment to this document.

## Validity rules (from frozen baseline §8, unchanged)

1. `conformance_verdict` is non-null only when `evaluation_state = "COMPLETE"`.
2. `evaluation_state` is null only when `assessment_coverage = "UNASSESSED"`;
   then `conformance_verdict` is null.
3. `ASSESSED` + `ERROR` => verdict null with `INVALID_CONTRACT`,
   `BINDING_MISMATCH`, or `SCOPE_RESOLUTION_ERROR` (plus diagnostics).
4. `ASSESSED` + `INDETERMINATE` => verdict null with `APPLICABILITY_UNRESOLVED`
   or `INPUT_UNAVAILABLE` (plus diagnostics).
5. `COMPLETE` + `FAIL` is a valid, expected outcome (completed evaluation,
   violated obligation); reasons carry the violated-condition class.
6. `NOT_APPLICABLE` requires a retained reason (explicit supported
   applicability or explicitly permitted-empty policy).
7. An invalid contract that was submitted for validation is an attempted
   evaluation (`ASSESSED`/`ERROR`), never disguised as "no contract".
8. Result-schema validation rejects illegal field combinations BEFORE
   serialization; no client invents interpretation rules.

## Aggregation (unchanged from frozen baseline)

- Return every required unit with its individual fields plus explicit
  assessed/unassessed ID lists and counts; contract inventories list phases
  with no executable contract (`CONTRACT_UNAVAILABLE`), which never disappear
  from method-level coverage.
- Aggregate `assessment_coverage = ASSESSED` only when every required unit was
  attempted; otherwise `UNASSESSED` (partial assessment shown by lists/counts
  and completed individual results).
- Required units unassessed => aggregate `evaluation_state` and
  `conformance_verdict` are null.
- All required units attempted => aggregate `evaluation_state` precedence:
  `ERROR` (any required child errored) > `INDETERMINATE` (any required child
  indeterminate) > `COMPLETE`.
- Verdict for a COMPLETE aggregate: `FAIL` if any required child fails;
  `NOT_APPLICABLE` if all required children are explicitly not applicable;
  otherwise `PASS` when every required child passes or is explicitly not
  applicable.
- An empty assessment inventory is `UNASSESSED`/null/null, not a vacuous pass;
  this differs from a valid obligation whose subject population is empty under
  its explicit population policy.
- Known child failures stay visible in every summary state.

## Readiness (unchanged from frozen baseline)

- `readiness_target` is mandatory inside a readiness block; no global flag.
- Task-entry: READY when that task's prerequisites are established
  (corrective work may be READY while conformance is failing).
- Scoped phase-exit: READY only when all required obligations for the exit
  target are COMPLETE `PASS` or explicitly permitted `NOT_APPLICABLE` and
  blocking prerequisites are satisfied; otherwise BLOCKED.
- PR-merge readiness: produced only by the delivery projection (Package D);
  a model query cannot grant it.
- Stale inputs are blocking reasons (`STALE_INPUT`), not a third readiness
  value. No requested target => no readiness block.

## Method contract schema spelling (frozen baseline §7, exact fields)

```text
obligation_id            stable explicit identifier, unique in the selected method
phase                    reference to an existing MethodPhase literal
subject_selector         typed selection from the declared evaluation scope
applicability            restricted typed condition over pinned model/configuration data
population_policy        minimum population + explicit permitted-empty disposition
predicate                pinned predicate identifier with declared input/output types
target_filters           typed conditions on returned targets (not on subjects)
cardinality              integer bounds over DISTINCT qualifying targets per applicable subject
required                 whether failure blocks this declared contract scope
evaluation_source        pinned model record | pinned repository artifact | live delivery adapter
attestation_policy_ref   required when acceptance/approval is part of the obligation
claim_boundary           exact claim supported when this obligation passes
```

Status conditions bind to specific vocabulary + target property; V1 uses
explicit allowed-value membership with rejection of unknown values at contract
validation; no global ordering; no example literals hard-coded into
vocabularies that do not contain them. Predicate implementations must not hide
phase rules or branch on phase numbers (MC-33).
