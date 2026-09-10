# Phase-10 Conformance Pilot — scope and acceptance authority (Package A)

Basis: R0 reconciliation of the unified plan with repository evidence at
DE4SDV HEAD `816ad1198ff90b8cd8293b3ca07011268400783a`; all identities below
were verified against repository files during R0.

## Declared pilot

| Role | Identity | Verified basis |
|---|---|---|
| Verification case (model) | `ConsciousOverrideVerification` (usage `overrideTrueVerification` and per-scenario specializations) | `textual-notation-of-model/packages/features/aebs/aebs_override_verification.sysml` (package `DE4SDV_AEBSOverrideVerification`) |
| Increment | INC-AEBS-009D conscious-override matrix | same file header; `config/contract-009d.yaml` (`increment_id`) |
| Subject | `verifiedBench : OverrideMatrixBench`, specialized per scenario | subject memberships in the verification case |
| Objective | `evidenceObjective` verifying three evidence-contract requirements | `verify` memberships: closed override scenario, freshness replay, independent verdict |
| Methods | `test` + `analyze` via `@VerificationMethod` metadata | in-file |
| Admitted configuration | `AEBSAutowareLinuxLidarCamera` (Standalone Autoware AEBS Reference Member) | `model-based-product-line-engineering/feature-configurations/aebs-autoware-linux-lidar-camera.yaml`; ADR 0014 |
| Tested subject state | runtime pinned at repo head `01d9f586865bf7fb4bc0b3f76be2b5a916451da4` | `implementation/aebs-autoware-nominal-vehicle-target-bench/evidence/009d/campaign-manifest.json` (`execution_head`), `evidence/009d/STATUS.md` |
| Execution records | canonical run per profile machine-declared with sha256 digests in `campaign-manifest.json`; earlier iteration runs retained with superseded markers | committed evidence tree |
| Evaluation scope | six typed override profiles: fresh_false_control, fresh_true_conscious_override, stale, missing, malformed, future_stamped | `config/contract-009d.yaml` (`profile_values`) |
| Claim boundary | configuration-bounded scenario only; no compliance/type-approval claim | STATUS.md + contract `claim_boundary` |

## Acceptance authority: explicit gap (admitted)

`evidence/009d/STATUS.md`: *"executed and independently replay-validated;
pending exact-head review."* No attributable authorized acceptance decision
exists for the 009D campaign. Under the frozen baseline §10 (evidence and
acceptance) a mutable status field cannot grant acceptance; acceptance requires
an attributable decision under a pinned authorization policy.

**Normative consequence for the pilot evaluation** (fixed here, per frozen
baseline §8): the pilot's replay-verifiable obligations can reach
`ASSESSED`/`COMPLETE`/`PASS`; any obligation requiring an authorized acceptance
decision returns `ASSESSED`/`COMPLETE`/`FAIL`-or-`INDETERMINATE` per its
contract — with reason code `ACCEPTANCE_AUTHORITY_MISSING` — never a
fabricated `PASS`. This makes the real pilot a positive test of the fail-closed
algebra; MC-16 is the owning synthetic case (C exit).

## Bounded pilot obligation table (Package A specification; B encodes it verbatim)

Evaluated candidate = the exact candidate revision under evaluation (not
necessarily the retained evidence's execution head). Selector targets resolve
through ingestion-validated kernel bindings at the candidate revision. Vocabulary
mappings bind to the model elements named above; no name-based resolution.

| # | obligation_id | phase | subject_selector | applicability | population_policy | predicate | target_filters | cardinality | required | evaluation_source | expected disposition at the time of writing |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P1 | `PC-009D-VC-EXISTS` | 10 | MethodPhase literal `phase10_vAndVEvidence` scope, package `DE4SDV_AEBSOverrideVerification` | candidate revision contains the pilot verification case | min 1; no permitted-empty | model-resident element-existence check (typed, binding-based) | element type `VerificationCaseDefinition`/`VerificationCaseUsage` for `ConsciousOverrideVerification` | [1..1] distinct | required | pinned model record | COMPLETE/PASS when bound; CONTRACT_UNAVAILABLE => UNASSESSED |
| P2 | `PC-009D-SUBJECT-MEMBERSHIP` | 10 | `ConsciousOverrideVerification` element | P1 passed | min 1 | `hasSubject`-family subject-membership witness (verifiedBench specializations) | member type `OverrideMatrixBench` specializations | [1..6] distinct per case | required | pinned model record | COMPLETE/PASS when memberships present; REQUIRED_RELATION_MISSING => FAIL |
| P3 | `PC-009D-OBJECTIVE-CONTRACTS` | 10 | `ConsciousOverrideVerification` element | P1 passed | min 3 | verify-membership witnesses to the three evidence-contract requirements | target type requirement usages of `OverrideEvidenceContract` | [3..3] distinct | required | pinned model record | COMPLETE/PASS; REQUIRED_RELATION_MISSING => FAIL |
| P4 | `PC-009D-METHOD-METADATA` | 10 | the three evidence-contract requirements | P3 passed | min 1 per case | `@VerificationMethod` metadata witness | method-kind vocabulary {test, analyze} | [1..2] distinct per case | required | pinned model record | COMPLETE/PASS; INPUT_UNAVAILABLE => INDETERMINATE if metadata absent from export |
| P5 | `PC-009D-EXECUTION-RECORDS` | 10 | declared tested scope: the 6 override profiles of INC-AEBS-009D | P1 passed | exactly 6 profiles | external evidence-reference match by profile identity | canonical runs machine-declared in `campaign-manifest.json` (sha256-verified at ingestion) | [6..6] distinct | required | pinned repository artifact | COMPLETE/PASS; EVIDENCE_SCOPE_MISMATCH => FAIL on profile-set mismatch; INPUT_UNAVAILABLE => INDETERMINATE |
| P6 | `PC-009D-ACCEPTANCE-AUTHORITY` | 10 | declared tested scope (P5) | P5 passed | min 1 attributable decision | acceptance-record match under the pinned authorization policy | decision record referencing the campaign scope and profiles | [1..1] | required | pinned repository artifact | per the FAIL/INDETERMINATE discriminator in result-algebra.md (evidence availability) |

Claim boundary of the whole pilot contract: configuration-bounded scenario
correctness of the declared model-to-evidence chain for INC-AEBS-009D. It does
not claim requirement satisfaction beyond the three evidence contracts, vehicle
behavior correctness, or any compliance approval.

## Tested-scope boundary and candidate revision (R3 rebinding rule)

Evaluation binds to the **candidate revision being evaluated**, and separately
compares the **declared tested scope** (execution head `01d9f58...`, profile
set, configuration, inputs) recorded by the retained evidence. Rebinding is
per-revision bookkeeping, not re-execution:

- A HEAD change that does not touch the tested boundary (docs, acceptance
  records, tooling) does NOT automatically demand campaign replay; the
  evaluation rebinds to the new candidate and re-checks scope declarations.
- New execution evidence is required only when the declared tested boundary
  changes (model/code/configuration under test) or when the scope comparison
  cannot establish the boundary (=> INDETERMINATE, never inferred freshness).
- Scope comparison is conservative equality at V1: a known mismatch fails the
  matching obligation (P5) rather than carrying evidence forward (frozen
  baseline §10 V1 validity limits).

## Unautomated obligations (named)

1. Attributable acceptance decision for the 009D campaign — human authority,
   outside the engine by design (MC-16 / `ACCEPTANCE_AUTHORITY_MISSING`).
2. Fresh exact-head replay only when the tested boundary changes or cannot be
   established (see rebinding rule above).

## Scope separation (per frozen baseline §16)

This pilot satisfies the *real-baseline demonstration* requirement for the
declared Phase-10 contract scope only. It does not claim full phase or method
coverage; broader exits stay BLOCKED until their required units are assessed
(MC-40). Synthetic fixtures prove the full positive/negative/indeterminate
matrix; no real model file is copied into test fixtures.
