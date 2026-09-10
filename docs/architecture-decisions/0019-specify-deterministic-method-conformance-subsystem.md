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
   (ERROR > INDETERMINATE > COMPLETE), and the finite reason vocabulary.
   Unknown reason codes are serialization errors; extending the vocabulary
   requires a reviewed amendment.
3. Declare the pilot's acceptance obligation fail-closed: no authorized
   attributable decision exists for the 009D campaign, so no evaluation may
   return acceptance PASS for it; the obligation resolves per its contract with
   `ACCEPTANCE_AUTHORITY_MISSING`.
4. Enforce baseline integrity mechanically: a test recomputes the SHA-256 of
   `docs/method-conformance/conformance-baseline.md` and fails on any drift;
   `mc-matrix.json` must match a re-extraction from the committed baseline.

## Consequences

- Package A's exit gate is satisfied in-repo: every MC case has a defined
  outcome and owner; pilot scope and acceptance authority are identified.
- B/C/D gain a pinned, machine-checkable specification; drift is caught by CI
  rather than review memory.
- The reason vocabulary is intentionally small; real evaluations that need new
  reasons must amend this ADR instead of inventing codes.
- The frozen baseline remains the authority on any conflict; this ADR adds
  spelling, vocabulary, pilot declaration, and integrity mechanics only.

## Non-decisions

- No evaluator, contract-binding, snapshot, or delivery implementation is
  approved or shipped here (Packages C/D and the MC cases they own).
- No acceptance decision for the 009D campaign is made or implied.
- No readiness target is activated; advisory evaluation and later mandatory
  checks remain separate authorized activations.
- Phase-specific populations, thresholds, and obligations stay model data; no
  contract content beyond the schema is decided here.

## Links

- Frozen baseline: `docs/method-conformance/conformance-baseline.md`
- Unified plan: DE4SDV_Unified_Semantic_Engineering_Plan_Final.md (§13, §16)
- ADR 0017 (engineering authority separation), ADR 0010 (revision-bound
  semantic reads), ADR 0014 (admitted product scope)
- R0 outputs: reconciliation, inventory, pilot identification
  (review-branch record)
