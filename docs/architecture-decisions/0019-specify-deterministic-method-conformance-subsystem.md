# ADR 0019: Specify the deterministic method-conformance subsystem (Package A)

## Status

Proposed

## Context

The unified semantic engineering plan requires a deterministic, fail-closed
method-conformance engine whose specification already exists as a frozen
planning baseline (digest
`427410f3070ed591287ec0dd3b819be7e95ee22fa7608b4c87d1e82192abd661`). The
baseline defers two things to "Increment A": the exact schema spelling and the
complete finite reason vocabulary. The real Phase-10 pilot, admitted
configuration, and the acceptance-authority gap were identified during R0
reconciliation against repository evidence at HEAD `816ad11`.

The repository currently has no in-repo home for this specification; the
baseline, matrix, and pilot decisions live outside the repository as review
outputs, which makes them invisible to contributors and CI.

## Decision

1. Adopt `docs/method-conformance/` as the governing specification home:
   - `conformance-baseline.md` — the frozen baseline, committed byte-unchanged;
   - `result-algebra.md` — the normative field spellings, allowed values, and
     the complete finite reason vocabulary fixed by this ADR;
   - `mc-outcome-owner-matrix.md` + `mc-matrix.json` — all 40 MC cases with
     owning packages (B: 4, C: 29, D: 7), machine-extracted from the frozen
     baseline and pinned by a digest test;
   - `pilot-scope.md` — the declared pilot
     (`ConsciousOverrideVerification`, INC-AEBS-009D), admitted configuration
     (`AEBSAutowareLinuxLidarCamera`), and the admitted acceptance-authority
     gap with reason code `ACCEPTANCE_AUTHORITY_MISSING`.
2. Fix the result algebra exactly as specified in `result-algebra.md`:
   `assessment_coverage`/`evaluation_state`/`conformance_verdict`/`readiness`
   semantics, JSON-null rules, aggregate precedence
   (ERROR > INDETERMINATE > COMPLETE), the finite reason vocabulary (sixteen
   codes plus the `PERMITTED_EMPTY` sub-vocabulary), and the normative
   state/reason compatibility table of legal tuples. Unknown reason codes are
   serialization errors; extending the vocabulary requires a reviewed
   amendment.
3. Declare the pilot's acceptance obligation fail-closed with the explicit
   FAIL/INDETERMINATE discriminator: authorization absent with evidence
   present resolves COMPLETE/FAIL; authorization unprovable with an
   incomplete evidence basis resolves INDETERMINATE. No evaluation may return
   acceptance PASS without an attributable authorized decision.
4. Instantiate the bounded pilot contract as specified in `pilot-scope.md`
   (obligations `PC-009D-SCOPE-POPULATION` through
   `PC-009D-ACCEPTANCE-AUTHORITY`, with the normative obligation dependency
   graph and the structured twin `pilot-obligations.yaml` asserted
   row-for-row against the markdown table) with subjects, selectors,
   population policies, predicates, target filters, cardinalities, evaluation
   sources, and expected dispositions; B encodes this table verbatim.
5. Bind evaluation to the candidate revision and compare the declared tested
   scope separately (rebinding rule): campaign replay is required only when
   the tested boundary changes or cannot be established — documentation or
   acceptance-record commits rebind without replay.
6. Enforce baseline integrity mechanically: a test recomputes the SHA-256 of
   `docs/method-conformance/conformance-baseline.md` over raw bytes and fails
   on any drift (including line-ending or encoding mutation); `mc-matrix.json`
   must match a re-extraction from the committed baseline; the reason
   vocabulary is pinned by exact set equality with negative probes (removals
   and additions both fail).

## Consequences

- When accepted, Package A's exit gate is satisfied in-repo: every MC case
  has a defined outcome and owner; pilot scope and acceptance authority are
  identified. Until Orkun accepts the A contract, this ADR remains Proposed
  and B does not start.
- B/C/D gain a pinned, machine-checkable specification; drift is caught by CI
  rather than review memory.
- The reason vocabulary is intentionally small; real evaluations that need new
  reasons must amend this ADR instead of inventing codes.
- The frozen baseline remains the authority on any conflict; this ADR adds
  spelling, vocabulary, pilot declaration, and integrity mechanics only.

## Non-decisions

- No evaluator, contract-binding, snapshot, or delivery implementation is
  approved or shipped here (Packages C/D and the MC cases they own).
### Amendment (follow-up review repairs, 2026-09-10)

The follow-up review returned R2a–R2c, R1/R3/R4 follow-ups, and a provenance
correction. Repairs, all bounded to the A contract and its guards:

1. **Exact model identities.** The pilot population is the six named
   verification usages (not the shared definition, not phase metadata); the
   exact phase literal is `phase10_vvEvidence`; method metadata is observed on
   its real owners (usage-level metadata; definition action-level metadata);
   `hasSubject` (Requirement → MemberProduct) is not claimed; kernel class
   bindings are declared non-instance bindings.
2. **Per-subject algebra.** Profile subjects carry `[1..1]` canonical-record,
   execution-outcome, scope-equality, and acceptance obligations each; the
   six-profile population is its own scope-composition obligation. No global
   counts (MC-03 preserved); a separate passing-execution obligation exists
   (MC-15); conservative scope equality is over pinned provenance fingerprint
   fields (MC-17/18).
3. **Single normative state/reason table.** Validity rules reference the
   compatibility table as the single normative source; rule 9 added —
   obligation prerequisites are not applicability (dependent children are
   UNASSESSED/`NOT_ATTEMPTED`, never `NOT_APPLICABLE`); the old pilot
   shorthand was removed.
4. **Handoff hygiene.** R0 handoff copies that conflict with the maintained
   contract are labeled SUPERSEDED with pointers; the zero-risk claim was
   withdrawn and corrected; provenance records the review as an AI-assisted
   direct review returning changes requested.
5. **Specification-integrity guards.** `pilot-obligations.yaml` is the
   structured twin of the obligation table, asserted row-for-row (IDs, exact
   phase literal verified against the method kernel, subject/target types,
   per-subject bounds, evaluation sources); the compatibility table is
   asserted by exact state tuples; duplicate reason declarations are
   rejected; expected outcomes for missing-case, missing-profile,
   failed-execution, incomplete-scope, absent-attestation, and
   prerequisite-blocked children are pinned by test.

- No acceptance decision for the 009D campaign is made or implied.
- No readiness target is activated; advisory evaluation and later mandatory
  checks remain separate authorized activations.
- Phase-specific populations, thresholds, and obligations stay model data; no
  contract content beyond the schema is decided here.

## Links

- Frozen baseline: `docs/method-conformance/conformance-baseline.md`
- Proposed authorization policy: `docs/method-conformance/acceptance-policy.md`
  (`de4sdv.acceptance.maintainer-decision.v1`, Proposed — activation is the
  maintainer's)
- Unified plan: DE4SDV_Unified_Semantic_Engineering_Plan_Final.md (§13, §16)
- ADR 0017 (engineering authority separation), ADR 0010 (revision-bound
  semantic reads), ADR 0014 (admitted product scope)
- R0 outputs: reconciliation, inventory, pilot identification
  (review-branch record)
