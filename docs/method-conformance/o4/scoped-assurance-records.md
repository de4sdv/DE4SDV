# Scoped assurance and V&V records

Status: draft implementation of the approved assurance-support and V&V-status
decisions. Native semantic validation and exact-revision integration gates remain
required. This is not an activated semantic authority or an acceptance mechanism.

## Problem

A cited artifact, a completed activity, an adequate evidence set and an authorized
acceptance decision answer different questions. Keeping those questions separate
must not restrict verification or validation to requirements alone.

## Minimal records

Current maturity: these are reusable definitions plus an offline checker for
supplied JSON records. No feature or product model instantiates them yet, so no
increment currently carries a scoped V&V activity, citation or adequacy record in
the model. Treat them as available infrastructure, not as working assurance.

The method kernel provides three reusable record definitions:

- `EvidenceSupportCitation`: identify the scoped claim, exact subject and
  configuration, conditions, versioned artifact reference, rationale and limits.
  This implements cited support, not evidence adequacy or satisfaction.
- `ScopedVVActivityRecord`: identify one verification **or** validation activity,
  its lifecycle context, comparison basis, criteria, existing `VVStatus`,
  responsible actor and retained result/evidence references. It applies to needs,
  requirements, designs, production outputs, system elements, integrated systems
  and other lifecycle artifacts. Existing native need/requirement attachments do
  not change. Execution verdicts remain distinct from activity status.
- `ScopedEvidenceAdequacyAssessment`: record the proportionate assessment of an
  evidence **set** for an exact claim and scope, with agreed criteria, coverage,
  confidence and rigor bases, assessor, conclusion, reasoning and exceptions.
  No standalone sufficiency verdict is demanded of each artifact.

`Completed` is not automatic PASS or product acceptance. `CompletedUnsuccessful`
means the activity could not complete; `CompletedFailed` and `CompletedPassed`
retain completed unsuccessful/successful activity meanings. Required result
approval is distinct from the designated authority's acceptance decision.

## Predicate vocabulary roles (O4 Wave A)

Named kernel comments record how the legacy predicates map onto these records.
They are vocabulary only; no runtime consumer, traversal or projection changes.

- `supportedByEvidenceVocabularyRole`: `supportedByEvidence` is represented by
  one `EvidenceSupportCitation` per cited artifact. It is distinct from
  `hasEvidence`. A claim counts as established, or acceptance is sought, only
  after a `ScopedEvidenceAdequacyAssessment` for the same scope.
  The model declares `ref item citations` on the assessment. This is a
  model-structure declaration only: supplied records and the read-only adapter
  do not carry citation references yet (assessments carry `activity_refs`).
  The record and adapter field is Wave B work.
  Acceptance stays a separate `AcceptanceAttestationReference`.
- `hasEvidenceStatusVocabularyRole`: the successor of `hasEvidenceStatus` is
  the unchanged `VVStatus` on `ScopedVVActivityRecord`. `EvidenceStatus`
  resolves to that pinned library enum. No universal status enum is added.
  Retirement path: no new model usage of `hasEvidenceStatus`. Consumers move
  to the successor in a reviewed runtime change (Wave B). The legacy name stays
  in the authored ontology until it is retired (Wave C).
- `EvidenceArtifactVocabularyRole`, `hasEvidenceVocabularyRole`,
  `BaselineVocabularyRole`, `capturedInBaselineVocabularyRole` and
  `ArchitectureDecisionRecordVocabularyRole` state the external boundary:
  content is external and the model has no authority over it. The model owns
  only the typed reference roles under the accepted
  `de4sdv.evidence-reference/v1` and `de4sdv.baseline-manifest-reference/v1`
  schemas.

## Supplied-record validation

The read-only CLI accepts `de4sdv.scoped-assurance-records/v1` JSON packages:

```bash
python -m de4sdv.semantic.scoped_assurance path/to/records.json
```

`evidence` uses the existing typed external-reference contract. `supports`
contains cited support; optional `activities`, `results`, `assessments` and
`requests` are projections of retained records, not a second evidence store.
Synthetic examples live only in the tests.

The checker rejects ambiguous record identities, duplicate JSON keys, overloaded
digest fields, scope/case/basis mismatches, unsupported status/result combinations,
uncovered criteria and omitted relevant supplied activities or contrary results.
Record scopes preserve subject, configuration and condition roles; reordering
conditions does not change scope, but swapping identities between roles does.
The existing external-reference `tested_scope` remains an unlabelled set at its
own compatibility seam, not a substitute for role-aware record matching.
An assessment must retain every evidence input of its assessed activities and
applicable cited limitations. Silent evidence exclusion cannot erase a known
limit or turn a qualified presentation into an unqualified one.
A request to present a claim as established or seek acceptance needs the exact
scoped adequacy assessment. Limitations and exceptions stay visible; they cannot
become unqualified technical satisfaction.

A successful check means **supplied-record structural eligibility only**. It does
not resolve engineering identities against the API, inspect artifact bytes,
establish substantive evidence adequacy, authenticate an assessor or authority,
verify an acceptance registry, or establish a claim. Reports explicitly keep
`implies_pass`, `claims_established`, `implies_acceptance` and
`production_activation` false on successful, source-check and error JSON reports.
Real authority and evidence checks remain owned
by their existing controlled evaluation and acceptance paths.

## Source parity and validation boundary

```bash
python -m de4sdv.semantic.scoped_assurance --check-native-sources
python -m de4sdv.semantic.scoped_assurance --check-native-sources \
  --upstream-archive path/to/already-retained-library.kpar
```

The first command checks lexical declaration/field parity and the existing public
`VVStatus` adapter seam; it reports archive verification as false. The optional
archive command checks exact lockfile digest and size, then compares the actual
pinned enum declaration with the model's status references. Neither command
fetches, adopts or modifies a library, or invokes a SysML semantic validator.
Both report `native_semantic_validation` false.

Status and activity-kind admission uses the intended directly owned executable
constraints, not a whole-file search for vocabulary mentions. Comments, quoted
text and constraints nested under foreign owners cannot add values. The existing
adopted `VVStatus` identity and population remain the vocabulary seam; optional
archive verification is separate from this mandatory supplied-record guard.
Direct same-identity definitions or aliases, including short-name headers, refuse
in the model package, activity owner and adapter seam. Inert or foreign-owned
lookalikes cannot shadow the adopted identity.

New kernel declarations must be classified by the existing ontology-kernel
contract. Aggregate inventories and revision bindings must be regenerated after
the source checkpoint; until then the repository gate is expected to refuse the
draft. This refusal is not waived by the focused test suite. Modeling completion
requires exact-head privileged Syside evidence after review; local lexical checks
and archive parity do not substitute for it.
