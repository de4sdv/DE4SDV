# Method-Conformance MC Outcome/Owner Matrix

Machine-extracted from the frozen planning baseline
([conformance-baseline.md](conformance-baseline.md), §16, digest
`427410f3070ed591287ec0dd3b819be7e95ee22fa7608b4c87d1e82192abd661`).
The frozen matrix is the conformance specification; this document
re-materializes it with owner grouping and A-exit annotations. It does not
re-decide any outcome, add cases, or change any required behavior.

Counts: **40 cases** — B-owned: 4, C-owned: 29, D-owned: 7.

Per the frozen baseline (§16): *"A approves the specification for all
cases, not their implementation. B, C, and D use only their assigned/prior
cases under Section 15."* The pilot scope and acceptance authority are
identified in [pilot-scope.md](pilot-scope.md).

## B-owned cases (first required exit)

| ID | Scenario | Required outcome |
|---|---|---|
| MC-10 | Ordinary selector includes a method contract | Scope validation error; shared type references alone remain legal |
| MC-14 | Reimport changes API UUIDs while explicit IDs and meaning remain stable | Preserve identity correspondence without name-based merging |
| MC-36 | Caller has uncommitted edits or requests dirty-working-tree evaluation | Export of a selected commit excludes uncommitted content and declares its commit identity; an explicit dirty-tree evaluation request is refused |
| MC-37 | Candidate is imported and validated before merge, including concurrent candidates | Candidate bindings remain isolated; published accepted-baseline selection is unchanged; validation does not imply approval |

## C-owned cases (first required exit)

| ID | Scenario | Required outcome |
|---|---|---|
| MC-01 | Complete scoped pilot; passing executions, authorized attestations, exact execution-scope matches | `COMPLETE` / `PASS` for the declared pilot only |
| MC-02 | One subject has no required evidence in an otherwise complete graph | `COMPLETE` / `FAIL`; identify the subject and missing relationship |
| MC-03 | One case has several records; another case has none | Fail the uncovered case; no global-count pass |
| MC-04 | Several graph paths reach the same evidence target | Count one distinct target per subject |
| MC-05 | Valid scope resolves to no subjects despite non-empty policy | `COMPLETE` / `FAIL` with population diagnostic |
| MC-06 | Missing membership, broken selector, ambiguous ID, or wrong target type | Error/indeterminate as specified; never an empty-population pass |
| MC-07 | Explicit, supported non-applicability | `NOT_APPLICABLE` with reason, not completed engineering work |
| MC-08 | Unknown applicability, missing API page/reference, or truncated traversal | `INDETERMINATE`; no pass |
| MC-09 | Unsupported predicate, invalid cardinality, or unknown status literal | Contract `ERROR` before normative evaluation |
| MC-11 | Different Git/API/ontology/method/evaluator/policy identity | Refuse the mismatched evaluation |
| MC-12 | API enumeration order and timestamps differ, semantic inputs identical | Same canonical conformance payload |
| MC-13 | Configuration, evaluation scope, or meaningful ordered collection changes | Different evaluation identity; recompute rather than reuse |
| MC-15 | Accepted evidence records a failed execution | Fail an obligation requiring a passing execution |
| MC-16 | Record says accepted but lacks attributable authorized decision | No acceptance pass; missing authority is explicit |
| MC-17 | Verification-case text unchanged, implementation/configuration/test/inputs change | No automatic evidence carry-forward; scope mismatch fails |
| MC-18 | Execution scope cannot establish required dependency boundary | Indeterminate validity, not inferred freshness |
| MC-19 | Evidence is committed after execution | Compare tested-scope identity; no impossible self-containing Git SHA requirement |
| MC-20 | Conflicting acceptance/rejection decisions lack valid supersession | Unresolved acceptance; no timestamp-based winner |
| MC-23 | Product candidate weakens obligation, interpretation, evaluator, or policy | Governing-policy mismatch/migration blocker; no self-acceptance |
| MC-26 | Hindsight claims evidence exists but graph does not | Memory does not change the result |
| MC-27 | Blocking prerequisite cycle versus legitimate feedback loop | Reject unsupported blocking cycle; allow separate feedback relation |
| MC-29 | All selected obligations explicitly not applicable versus no executable phase contract | First case: ASSESSED / COMPLETE / NOT_APPLICABLE; second: UNASSESSED / null / null; neither claims completed engineering work |
| MC-31 | Unmerged candidate revision is validated/imported with complete scope | Conformance may be evaluated against that exact candidate revision; merge is not required |
| MC-33 | A non-Phase-10 contract uses the same generic operators | Evaluate without phase-specific code path; phase number does not alter semantics |
| MC-34 | Phase has no reviewed executable contract yet | UNASSESSED / null / null with CONTRACT_UNAVAILABLE reason; required broader exit readiness remains BLOCKED |
| MC-35 | Approved phase contract exists; candidate is absent, invalid, or missing scope | phase_contract returns method identity, obligations, and unresolved applicability inputs without a conformance verdict; no obligations silently disappear |
| MC-38 | Result fields include illegal combinations or missing required reasons/target | Reject serialization; no verdict for INDETERMINATE/ERROR/UNASSESSED, null evaluation fields only as specified, and readiness always names its target |
| MC-39 | Candidate fails a required exit condition while a corrective task has satisfied entry prerequisites | Phase-exit readiness BLOCKED and corrective-task entry readiness READY may coexist under distinct explicit targets |
| MC-40 | Broader scope mixes attempted and unassessed required units, including known child failures | Preserve all child results and coverage lists/counts; aggregate coverage UNASSESSED with null evaluation/verdict, and broader exit readiness BLOCKED |

## D-owned cases (first required exit)

| ID | Scenario | Required outcome |
|---|---|---|
| MC-21 | Snapshot corrupt, incomplete, wrong-bound, or self-attested without trusted provenance | Reject snapshot; never silently load latest |
| MC-22 | Same verified inputs loaded through API and snapshot | Identical canonical conformance payload |
| MC-24 | PR head/base moves while status is gathered | `readiness = BLOCKED` for the exact PR-merge target, with `STALE_INPUT` and a head-moved/base-moved reason; no successful delivery verdict |
| MC-25 | Required delivery obligation unsupported; model pilot passes | Model pass stays scoped; full readiness does not pass |
| MC-28 | Remote artifact later unavailable; pinned record unchanged | Historical model verdict reproducible; availability reported separately |
| MC-30 | Evaluator API/snapshot comparison and independent manual pilot review disagree | Block readiness and investigate; neither timeout nor partial result counts as acceptance |
| MC-32 | Same verified candidate evaluated through API and validated local/CI snapshot | Same canonical conformance payload |

## A-exit annotations (specification, not implementation)

- Every case above has a defined outcome and a single owning package;
  A's exit gate ("all MC cases have defined outcomes/owners; pilot scope
  and acceptance authority identified") is satisfied by this document plus
  [pilot-scope.md](pilot-scope.md) and the [result-algebra](result-algebra.md)
  spelling fixed below.
- A approves this specification; B/C/D implement their assigned cases;
  no case is demanded of A at its exit.
- Any conflict between this matrix and the frozen baseline is resolved in
  favor of the frozen baseline; changes require a separate reviewed
  amendment (unified plan §13).

