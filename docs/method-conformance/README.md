# Method Conformance — deterministic engine specification (Packages A–D)

This directory holds the governing specification for the deterministic
method-conformance subsystem: the frozen planning baseline, the normative
result-algebra spelling, the extracted MC acceptance matrix, and the declared
Phase-10 pilot.

## Status — 2026-10-05

**V1 Core (A–D) delivered** under Orkun Yilmaz's definition: the checker is
proven by an honest real INC-AEBS-009D disposition and independent MC-30
agreement. This is checker delivery, not acceptance of the 009D campaign.
The campaign evidence is **not yet accepted**; its readiness remains BLOCKED.
The retained hosted run and independent agreement are identified in
[core-operational-evidence.md](core-operational-evidence.md).

The acceptance policy is Active as written; the README-only decision registry
contains zero decisions. The delivery gate remains **ADVISORY**: required-check
activation is a later owner decision, with no branch-protection change here.
The unified semantic engineering plan remains **incomplete**: O4 ontology
migration and PLE qualification/adoption work are outstanding. No certification,
compliance, product acceptance or new production-authority activation is claimed.

| Document | Role |
|---|---|
| [conformance-baseline.md](conformance-baseline.md) | FROZEN planning baseline (digest `427410f3...`); the conformance specification. Unchanged copy; changes require a reviewed amendment. |
| [result-algebra.md](result-algebra.md) | Normative field/reason-vocabulary spelling fixed by Package A (frozen baseline §7–§8). |
| [mc-outcome-owner-matrix.md](mc-outcome-owner-matrix.md) + [mc-matrix.json](mc-matrix.json) | All 40 MC cases with owners (B: 4, C: 29, D: 7), machine-extracted from the frozen baseline. |
| [pilot-scope.md](pilot-scope.md) | Declared real Phase-10 pilot, admitted configuration, identities, and the admitted acceptance-authority gap. |
| [core-operational-evidence.md](core-operational-evidence.md) | Executable fresh-process retained-export/snapshot battery and intended-runner workflow; receipts are evidence, not Core or pilot acceptance. |
| [o3/o3-completion-record.md](o3/o3-completion-record.md) + [o3-production-cutover-evidence.json](o3/o3-production-cutover-evidence.json) | O3 COMPLETE — production cutover record for the frozen 13-identity semantic-authority scope: deployment-bound closure, activation / rollback / re-activation evidence, probe batteries, cache isolation, final production authority. Evidence only — never runtime authority. |
| [o4/ontology-review/](o4/ontology-review/README.md) | Accepted O4 ontology-review package: governed target input for the remaining ontology-authority migration, with architecture rereview and hardened validation. Governance only — never runtime authority. |
| [o4/o4-execution-plan.md](o4/o4-execution-plan.md) + [o4-execution-register.json](o4/o4-execution-register.json) | O4 execution register + wave plan, deterministically generated from the governed review using reviewed, machine-checked wave-mapping rules: all 93 identities accounted exactly once, one base wave + decision gate per retained target, blockers/dependencies/closure boundary, first-wave recommendation. Planning only — no semantic migration. |

Ownership: A approves this specification (this branch); B implements the
minimum normative API slice for B-owned cases and encodes the pilot obligation
table (`pilot-scope.md`) verbatim; C the evaluator and discovery; D snapshots
and delivery. Method owner: Orkun Yilmaz; independent V&V per package.
Implementation files proposed by later packages:
`de4sdv/method_conformance/` (`method_contract.py`, `method_evaluator.py`),
tests under `tests/test_method_contract_binding.py`,
`tests/test_method_conformance.py`, `tests/test_method_snapshot.py`,
`tests/test_method_delivery_gate.py`.

Review-amendment record: the independent R0 review (findings R1–R4) was
addressed on this branch — completed reason vocabulary with state/reason
compatibility table, instantiated pilot contract, candidate-revision rebinding
rule, and hardened integrity tests with verified mutation probes.
