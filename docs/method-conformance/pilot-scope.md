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

## Unautomated obligations (named)

1. Attributable acceptance decision for the 009D campaign — human authority,
   outside the engine by design (MC-16 / `ACCEPTANCE_AUTHORITY_MISSING`).
2. Fresh exact-head replay if the reviewed head moves — evidence binds
   `01d9f58...`; rebind and rerun after head/base changes (frozen baseline §17).

## Scope separation (per frozen baseline §16)

This pilot satisfies the *real-baseline demonstration* requirement for the
declared Phase-10 contract scope only. It does not claim full phase or method
coverage; broader exits stay BLOCKED until their required units are assessed
(MC-40). Synthetic fixtures prove the full positive/negative/indeterminate
matrix; no real model file is copied into test fixtures.
