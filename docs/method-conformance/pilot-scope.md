# Phase-10 Conformance Pilot — scope and acceptance authority (Package A)

Basis: R0 reconciliation of the unified plan with repository evidence at
DE4SDV HEAD `816ad1198ff90b8cd8293b3ca07011268400783a`; all identities below
were verified against repository files during R0 and re-verified during the
review repair (exact phase literal, usage names, metadata owners, disposition
vocabulary, provenance fields).

## Declared pilot

| Role | Identity | Verified basis |
|---|---|---|
| Verification case definition (model) | `ConsciousOverrideVerification` (verification def) | `textual-notation-of-model/packages/features/aebs/aebs_override_verification.sysml:71` (package `DE4SDV_AEBSOverrideVerification`) |
| Evaluation population (exact usages) | `overrideFalseControlVerification`, `overrideTrueVerification`, `overrideStaleVerification`, `overrideMissingVerification`, `overrideMalformedVerification`, `overrideFutureStampedVerification` — six `verification` usages specializing the shared definition | same file, lines 95–117; performed by `part verificationSystem` (lines 119–125) |
| Phase identity | `phase10_vvEvidence` (exact `MethodPhase` literal) | `textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_process.sysml:56` |
| Subject role per usage | `verifiedBench :> override<Scenario>Bench` (native verification-subject membership) | same file, per-usage subject lines |
| Subject type | `OverrideMatrixBench` specializations (`overrideFalseControlBench` … `overrideFutureStampedBench`) | same file |
| Objective | `evidenceObjective` on the shared definition verifying three evidence-contract requirements | `verify` memberships: `evidenceContractClosedOverrideScenario`, `evidenceContractOverrideFreshnessReplay`, `evidenceContractIndependentVerdict` |
| Method metadata owners | usage level: `@VerificationMethod{ kind = (test, analyze); }` on each of the six usages; definition level: `@VerificationMethod{ kind = test; }` on `collectData`, `kind = analyze;` on `processData` and `evaluateData` | same file, lines 96–116 (usages) and 79/83/89 (definition actions) |
| Increment | INC-AEBS-009D conscious-override matrix | same file header; `config/contract-009d.yaml` (`increment_id`) |
| Admitted configuration | `AEBSAutowareLinuxLidarCamera` (Standalone Autoware AEBS Reference Member) | `model-based-product-line-engineering/feature-configurations/aebs-autoware-linux-lidar-camera.yaml`; ADR 0014 |
| Tested subject state | runtime pinned at repo head `01d9f586865bf7fb4bc0b3f76be2b5a916451da4` | `campaign-manifest.json` (`execution_head`), `evidence/009d/STATUS.md` |
| Execution records | one canonical run per profile, machine-declared with sha256 digests in `campaign-manifest.json`; earlier iteration runs retained with superseded markers | committed evidence tree |
| Outcome vocabulary (pinned) | `OverrideScenario` identities and `OverrideDisposition` literals (`control_clear`, `conscious_override`, `degraded_stale_source`, `inconclusive_missing_source`, `error_malformed_source`, `error_future_source`, …) | `implementation/.../src/de4sdv_aebs_009b_bench/override_matrix.py` (enum source of the pinned vocabulary) |
| Scope-fingerprint fields (pinned) | `repository_head`, `execution_manifest_sha256`, `override_matrix_sha256`, `override_execution_manifest_sha256`, `runtime_lock_sha256` (incl. `inherited_009a`), `image_digest`, `map_digest`, `host_arch` | per-record `provenance` objects; `config/contract-009d.yaml` provenance mapping |
| Claim boundary | configuration-bounded scenario verdicts only (`one_profile_runtime_verdict_only_no_safety_or_compliance_claim`); no compliance/type-approval claim | `config/contract-009d.yaml` (`claim_boundary`) + STATUS.md |

## Evaluation target: current candidate realization (chosen)

The pilot evaluates the **current candidate revision**: the model obligations
bind to the candidate's validated API revision via ingestion-validated kernel
bindings; the evidence obligations compare the retained external records
against the **declared tested scope** that the candidate declares for the
pilot. Historical evidence remains valid as history (reproducible against its
own recorded scope, MC-28) but satisfies current-scope obligations only under
conservative scope equality (MC-17). A moved tested boundary therefore fails
the scope-equality obligation instead of silently carrying evidence forward.

## Kernel bindings are not instance-identity bindings

Class-level kernel bindings (e.g. a bound `OverrideMatrixBench` definition)
establish vocabulary identity only. Every obligation below binds **instance
identities** (the six named usages, their per-usage subject members, the three
requirement usages) through API element identity at the candidate revision.
The shared definition `ConsciousOverrideVerification` is a distinct identity
from its six usages; `MethodPhase` metadata is never a subject.

## Bounded pilot obligation table (Package A specification; B encodes it verbatim)

Conventions: population and cardinality are **per applicable subject** (frozen
baseline §7); `[a..b]` bounds count distinct qualifying targets per subject.
`applicability` holds only supported explicit conditions over pinned
model/configuration data. Prerequisites are obligation-to-obligation
dependencies, NOT applicability: a failed prerequisite makes the dependent
obligation `UNASSESSED`/null/null with `NOT_ATTEMPTED` plus a `diagnostics`
entry naming the failed prerequisite (rule 9 in result-algebra.md) — never
`NOT_APPLICABLE`. The six declared usage names and the phase literal are
pinned strings; resolution is by ingestion-validated binding, never by name
matching.

### Obligation dependency graph (normative)

```text
1  PC-009D-SCOPE-POPULATION        depends on: none (root of model branch)
2  PC-009D-VC-BINDING              depends on: 1
3  PC-009D-SUBJECT-MEMBERSHIP      depends on: 2 (its own usage)
4  PC-009D-OBJECTIVE-CONTRACTS     depends on: 2 (its own usage)
5  PC-009D-USAGE-METHOD-METADATA   depends on: 2 (its own usage)
6  PC-009D-DEFINITION-METHOD-METADATA   depends on: 1 (scope resolution)
7  PC-009D-PROFILE-POPULATION      depends on: none (independent branch)
8  PC-009D-EXECUTION-RECORD        depends on: 7 (its own profile)
9  PC-009D-EXECUTION-OUTCOME       depends on: 8 (its own profile record)
10 PC-009D-SCOPE-EQUALITY          depends on: 8 (its own profile record)
11 PC-009D-ACCEPTANCE-AUTHORITY    depends on: 8 (its own profile record)
```

The graph is the **single** dependency source: no table cell may add or imply
dependencies beyond it, and the aggregate examples below are derived from it
mechanically. Two independent branches exist: the model branch (1→2→{3,4,5},
1→6) and the evidence branch (7→8→{9,10,11}). **No edge crosses between the
branches**: execution-outcome (9) and acceptance (11) observe the retained
records independently of scope equality (10). A `SCOPE_EQUALITY` failure does
not unassess anything — it blocks **current-candidate conformance claims** at
the readiness layer (a required scope-equality FAIL makes the pilot's
declared-scope conformance claim BLOCKED for current-candidate use, while the
per-obligation results stay individually visible).

| # | obligation_id | phase | subject_selector | applicability | population_policy | predicate (exact subject → target types) | target_filters | cardinality (per subject) | required | evaluation_source | expected disposition at time of writing |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `PC-009D-SCOPE-POPULATION` | 10 (`phase10_vvEvidence`) | the declared pilot scope itself (one subject: the declared scope) | candidate revision declares the INC-AEBS-009D pilot scope | exactly 1 scope subject | scope-composition check: declared usage set = the six pinned usage names, as distinct identities | element type `VerificationCaseUsage` | `[6..6]` distinct usages in scope | required | pinned model record | COMPLETE/PASS at a candidate containing the slice; COMPLETE/FAIL (`REQUIRED_RELATION_MISSING`) if a declared usage is absent in complete scope; INDETERMINATE (`INPUT_UNAVAILABLE`) if scope input is missing/incomplete |
| 2 | `PC-009D-VC-BINDING` | 10 | each of the six declared usages (`VerificationCaseUsage`) | candidate revision declares the INC-AEBS-009D pilot scope | min 1, exactly 6 expected | binding-resolution check: usage identity → API element | element type `VerificationCaseUsage` | `[1..1]` API element per usage | required | pinned model record | COMPLETE/PASS; ERROR (`BINDING_MISMATCH`/`SCOPE_RESOLUTION_ERROR`) on ambiguous or contradictory binding |
| 3 | `PC-009D-SUBJECT-MEMBERSHIP` | 10 | each of the six usages (`VerificationCaseUsage`) | (no applicability condition) | min 1 per usage | native verification-subject membership: `VerificationCaseUsage` (owner) → `OverrideMatrixBench` specialization usage (member, role `verifiedBench`) | member element type `OverrideMatrixBench` specialization | `[1..1]` member per usage | required | pinned model record | COMPLETE/PASS; COMPLETE/FAIL (`REQUIRED_RELATION_MISSING`) on absent member in complete scope |
| 4 | `PC-009D-OBJECTIVE-CONTRACTS` | 10 | each of the six usages (`VerificationCaseUsage`) | (no applicability condition) | min 1 per usage | `verifiedBy`-family verification-membership, direction reverse (requirement ← verified), witness path: usage → specialization of `ConsciousOverrideVerification` → `evidenceObjective` → verify memberships → requirement usages | target type: the three pinned requirement usages (evidence-contract requirements) | `[3..3]` distinct requirements per usage | required | pinned model record | COMPLETE/PASS with full inherited witness path returned per usage (UG-07: no fabricated direct membership); COMPLETE/FAIL (`REQUIRED_RELATION_MISSING`) on missing objective member in complete scope |
| 5 | `PC-009D-USAGE-METHOD-METADATA` | 10 | each of the six usages (`VerificationCaseUsage`) | (no applicability condition) | min 1 per usage | metadata observation on the usage's real owner: `@VerificationMethod` metadata feature on the `VerificationCaseUsage` | method-kind value set exactly `{test, analyze}` | `[1..1]` metadata witness per usage | required | pinned model record | COMPLETE/PASS; COMPLETE/FAIL (`REQUIRED_RELATION_MISSING`) on missing metadata in complete scope |
| 6 | `PC-009D-DEFINITION-METHOD-METADATA` | 10 | the shared verification definition `ConsciousOverrideVerification` (`VerificationCaseDefinition`) | (no applicability condition) | exactly 1 definition subject | metadata observation on the definition's actions: `@VerificationMethod` on `collectData`, `processData`, `evaluateData` | per-action kind: `collectData`→`test`; `processData`→`analyze`; `evaluateData`→`analyze` | `[3..3]` action-metadata witnesses on the definition | required | pinned model record | COMPLETE/PASS; COMPLETE/FAIL (`REQUIRED_RELATION_MISSING`) on missing/retargeted metadata |
| 7 | `PC-009D-PROFILE-POPULATION` | 10 | the declared tested scope (one subject: the scope) | candidate declares the INC-AEBS-009D tested-scope manifest | exactly 1 scope subject | scope-composition check: declared profile set = the six pinned `OverrideScenario` identities | profile identity equality (pinned set, exact) | `[6..6]` distinct profiles in scope | required | pinned repository artifact | COMPLETE/PASS; COMPLETE/FAIL (`REQUIRED_RELATION_MISSING`) on a missing declared profile; COMPLETE/FAIL (`EVIDENCE_SCOPE_MISMATCH`) on an extra undeclared profile |
| 8 | `PC-009D-EXECUTION-RECORD` | 10 | each profile in the declared tested scope (obligation 7) | (no applicability condition) | min 1 per profile | external evidence-reference match: profile → its one canonical record declared by `campaign-manifest.json` | record integrity: `sha256` of `scenario-evidence.json` matches the manifest entry | `[1..1]` canonical record per profile | required | pinned repository artifact | COMPLETE/PASS; COMPLETE/FAIL (`REQUIRED_RELATION_MISSING`) when no canonical record; ERROR (`BINDING_MISMATCH`) on digest mismatch; INDETERMINATE (`INPUT_UNAVAILABLE`) when the record is unreadable/absent from retained storage |
| 9 | `PC-009D-EXECUTION-OUTCOME` | 10 | each profile's canonical record (obligation 8) | (no applicability condition) | min 1 per profile | execution-outcome observation: record `evaluation.passed == true` AND `evaluation.disposition` equals the pinned per-profile expected value (fresh_false_control→`control_clear`; fresh_true_conscious_override→`conscious_override`; stale→`degraded_stale_source`; missing→`inconclusive_missing_source`; malformed→`error_malformed_source`; future_stamped→`error_future_source`) | disposition from the pinned `OverrideDisposition` vocabulary; unknown disposition literal ⇒ ERROR (`INVALID_CONTRACT`) | `[1..1]` outcome per record | required | pinned repository artifact | COMPLETE/PASS (all six retained records currently satisfy this); COMPLETE/FAIL (`EXECUTION_FAILED`) otherwise |
| 10 | `PC-009D-SCOPE-EQUALITY` | 10 | each profile's canonical record (obligation 8) | (no applicability condition) | min 1 per profile | conservative equality: record `provenance` fields (`repository_head`, `override_matrix_sha256`, `override_execution_manifest_sha256`, `execution_manifest_sha256`, `runtime_lock_sha256` incl. `inherited_009a`, `image_digest`, `map_digest`, `host_arch`) equal the candidate's declared tested-scope manifest values for that profile | all pinned fields compared; no field may be skipped | `[1..1]` comparison per record | required | pinned repository artifact + candidate-declared manifest | COMPLETE/PASS at the evidence's own execution head; COMPLETE/FAIL (`EVIDENCE_SCOPE_MISMATCH`) on any known mismatch; INDETERMINATE (`INPUT_UNAVAILABLE`) when any required field is missing from either side — matching profiles alone never proves scope equality |
| 11 | `PC-009D-ACCEPTANCE-AUTHORITY` | 10 | each profile's canonical record (obligation 8) | (no applicability condition) | min 1 per profile | acceptance-record match under the proposed policy `de4sdv.acceptance.maintainer-decision.v1` ([acceptance-policy.md](acceptance-policy.md)): an attributable, authorized decision record referencing the campaign scope and enumerating covered profiles | decision-population completeness over the closed six-profile universe (policy §Decision-population completeness); conflicts without supersession ⇒ INDETERMINATE | `[1..1]` applicable decision per profile | required | pinned repository artifact | discriminator per result-algebra.md (evidence availability): currently expected COMPLETE/FAIL (`ACCEPTANCE_AUTHORITY_MISSING`) — records and STATUS are retained and complete, the authorized decision is absent |

### Expected aggregate outcomes (declared, derived from the dependency graph)

Evaluation model: **all obligations always evaluate the current candidate's
model** (bindings, memberships, metadata). Retained execution records are
external observations; their **usability for the current candidate** is
decided solely by the scope-equality obligation (10). There is no
"evaluation of the historical model" in this contract: at the recorded
execution head the model slice used different declaration names
(`ConsciousOverrideVerification009D` family in `aebs_009d_verification.sysml`,
renamed by later reviewed PRs), so binding today's identities against that
revision is meaningless and is not attempted. A reviewed identity migration
mapping (old→new declaration names) belongs to the T/O rename-tracking lane,
not to this pilot contract.

- **Candidate whose declared tested scope matches the retained evidence
  (scope-equality PASS per profile):** 1–8 PASS; 9 PASS (records show
  `passed=true` with pinned dispositions); 10 PASS; 11 FAIL
  (`ACCEPTANCE_AUTHORITY_MISSING` — records complete, decision absent).
  All required units attempted ⇒ aggregate `ASSESSED` / `COMPLETE` / **FAIL**;
  readiness BLOCKED for any exit target requiring acceptance.
- **Candidate whose tested boundary moved (scope-equality FAIL, known
  mismatch):** model branch 1–6 resolves and passes against the candidate;
  evidence branch 7–8 PASS (profiles declared, records found); 10 FAIL
  (`EVIDENCE_SCOPE_MISMATCH`); 9 and 11 still evaluate (graph has no
  10→9/10→11 edges) and their individual results stand — 9 PASS as a
  historical observation, 11 FAIL — but the **scope-equality FAIL blocks
  current-candidate conformance**: the pilot's declared-scope claim is not
  usable for the current candidate and readiness is BLOCKED with the 10-FAIL
  as a blocking reason, all child results visible.
- **Missing profile / missing record:** 7 FAIL (`REQUIRED_RELATION_MISSING`)
  or 8 FAIL/INDETERMINATE per its row; dependents on the failed edge (9/10/11
  for that profile) are UNASSESSED/`NOT_ATTEMPTED` children (rule 9) ⇒
  aggregate `UNASSESSED`/null/null with the failed parent visible; readiness
  BLOCKED.
- **Failed execution:** 9 FAIL (`EXECUTION_FAILED`) independently; 10 and 11
  still evaluate (no 9→10/9→11 edges); a failed execution may be validly
  accepted as an observation (MC-15) — it does not satisfy a passing-outcome
  obligation but does not block the acceptance record from being evaluated.
- **Incomplete declared scope (missing required field on either side):**
  10 INDETERMINATE (`INPUT_UNAVAILABLE`) — matching profiles alone never
  proves scope equality (MC-08).
- Missing-scope or missing-record conditions never produce empty-population
  passes (MC-05/06/08); conflicting decisions without supersession stay
  unresolved (MC-20).

### Non-goals of this table

No evaluator implementation is specified here (Package C, after B's real API
proof). No acceptance decision is made or implied (obligation 11 measures its
absence). The table does not redefine any existing predicate identity: it
reuses `verifiedBy`'s verification-membership semantics and subject-membership
primitives with exact owner/member types; `hasSubject`
(Requirement → MemberProduct) is NOT claimed by any row.

## Acceptance authority: explicit gap (admitted)

`evidence/009d/STATUS.md`: *"executed and independently replay-validated;
pending exact-head review."* No attributable authorized acceptance decision
exists for the 009D campaign. Under the frozen baseline §10 (evidence and
acceptance) a mutable status field cannot grant acceptance; acceptance requires
an attributable decision under a pinned authorization policy
(`de4sdv.acceptance.maintainer-decision.v1`, ADR 0019 §5).

**Normative consequence for the pilot evaluation**: the acceptance obligation
(11) follows the FAIL/INDETERMINATE discriminator fixed in
[result-algebra.md](result-algebra.md) ("FAIL vs INDETERMINATE for the
acceptance obligation"): authorization absent with an otherwise complete
evidence basis resolves `ASSESSED`/`COMPLETE`/`FAIL` with
`ACCEPTANCE_AUTHORITY_MISSING`; an incomplete evidence basis resolves
`ASSESSED`/`INDETERMINATE`/null with `ACCEPTANCE_AUTHORITY_MISSING` (plus
`INPUT_UNAVAILABLE` as diagnostic). A fabricated PASS is impossible by
construction.

## Unautomated obligations (named)

1. Attributable acceptance decision for the 009D campaign — human authority,
   outside the engine by design (MC-16 / obligation 11).
2. Fresh exact-head replay only when the tested boundary changes or cannot be
   established (rebinding rule below).

## Tested-scope boundary and candidate revision (rebinding rule)

Evaluation binds to the **candidate revision being evaluated**, and separately
compares the **declared tested scope** recorded by the retained evidence
(obligation 10). Rebinding is per-revision bookkeeping, not re-execution:

- A HEAD change that does not touch the tested boundary (docs, acceptance
  records, tooling) does NOT demand campaign replay; the evaluation rebinds to
  the new candidate and re-checks scope declarations.
- New execution evidence is required only when the declared tested boundary
  changes (model/code/configuration under test) or when the scope comparison
  cannot establish the boundary (⇒ INDETERMINATE, never inferred freshness).
- Scope comparison is conservative equality at V1 against the pinned
  fingerprint fields; a known mismatch fails obligation 10 rather than
  carrying evidence forward (frozen baseline §10 V1 validity limits).

## Scope separation (per frozen baseline §16)

This pilot satisfies the *real-baseline demonstration* requirement for the
declared Phase-10 contract scope only. It does not claim full phase or method
coverage; broader exits stay BLOCKED until their required units are assessed
(MC-40). Synthetic fixtures prove the full positive/negative/indeterminate
matrix; no real model file is copied into test fixtures.
