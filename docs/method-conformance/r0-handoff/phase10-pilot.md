# R0-7: Phase-10 conformance pilot identification

> **STATUS: SUPERSEDED (specification record).** This is the R0 identification
> record, retained for provenance. The maintained, normative pilot contract —
> including the instantiated obligation table, the candidate-revision
> rebinding rule (which REPLACES the replay-on-HEAD-move wording below), and
> the reviewed FAIL/INDETERMINATE discriminator — lives in
> [`../pilot-scope.md`](../pilot-scope.md). Where this record and the
> maintained contract disagree, the maintained contract governs.

## Pilot (real, admitted, evidence-bearing)

**Verification case:** `ConsciousOverrideVerification` (verification usage
`overrideTrueVerification` among subjects) in
`textual-notation-of-model/packages/features/aebs/aebs_override_verification.sysml`.

**Increment:** INC-AEBS-009D conscious-override matrix.

**Why this one:** it is the only candidate with ALL of — native SysML v2
verification case (subject + objective + verify membership + methods
test/analyze), bounded evidence contract requirements, six immutable retained
runs, independent replay validation, and an explicit honest acceptance gap.

## Admitted configuration

`AEBSAutowareLinuxLidarCamera` (feature-configurations/aebs-autoware-linux-lidar-camera.yaml)
— the Standalone Autoware AEBS Reference Member per ADR 0014; the configuration
the 009 bench evidence exercises. Configuration-valid under the current tool;
admitted by governed scope; both reported separately per plan §6.2.

## Identities (grounded)

| Role | Identity | Basis |
|---|---|---|
| Verification case (model) | `ConsciousOverrideVerification` | verification def in aebs_override_verification.sysml:71 |
| Subject | `verifiedBench : OverrideMatrixBench` (per-scenario specializations) | same file, subject membership |
| Objective | `evidenceObjective` verifying 3 evidence-contract requirements | same file |
| Tested subject state | pinned runtime at repo head `01d9f586865bf7fb4bc0b3f76be2b5a916451da4` | evidence/009d/STATUS.md |
| Execution records | `evidence/009d/campaign-manifest.json` machine-declares the canonical run per profile with sha256 digests (execution_head `01d9f58...`; e.g. `fresh_true_conscious_override` → `20260727T222325Z-d6cda4ace4b3a9ca`). Earlier iteration runs remain retained in the same runs/ directories (5 under fresh_false_control) with superseded markers (`scenario-evidence.validated-superseded.json`); canonical vs superseded distinguishable, all immutable. | committed evidence + `git ls-tree` |
| Retained result | per-profile `scenario-evidence.json`, replay-validated | STATUS.md; independent replay passed |
| Evaluation scope | 6 typed override profiles (freshFalseControl, freshTrueOverride, stale, missing, malformed, futureStamped) | config/contract-009d.yaml |
| Claim boundary | configuration-bounded scenario only; no compliance/type-approval claim | STATUS.md + contracts |

## Acceptance authority: EXPLICIT GAP (admitted, not hidden)

STATUS.md: "executed and independently replay-validated; **pending exact-head
review**." No attributable acceptance decision exists for the 009D campaign.
Under plan §3, acceptance requires an attributable decision under a pinned
authorization policy — a mutable status field cannot grant acceptance.

**Consequence for the pilot:** the conformance evaluation can reach
ASSESSED/COMPLETE for replay-verifiable obligations, and must return
INDETERMINATE (or an explicit acceptance-gap disposition) for the acceptance
obligation — never a fabricated PASS. This makes the pilot an honest positive
test of the fail-closed result algebra (plan §13), and UG-18 (separate
ingestion/result/attestation/scope/availability outcomes) applies directly.

## Unautomated obligations (named, not hidden)

- Attributable acceptance decision for the 009D campaign (human authority; not
  automatable by design).
- Fresh exact-head replay if the reviewed head moves (evidence is bound to
  `01d9f58...`).

## Verification identities needed from the model (B-slice inputs)

- VerificationCase element UUID via ingestion-validated kernel binding;
- subject membership witnesses (verifiedBench specializations);
- objective verify-membership witnesses (3 evidence-contract requirements);
- verification-method metadata witnesses (test, analyze);
- evidence references remain EXTERNAL identities (path + sha256 from the
  retained records), not fabricated API UUIDs.
