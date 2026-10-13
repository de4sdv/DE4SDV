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
| [pilot-obligations.yaml](../../de4sdv/semantic/contract-data/pilot-obligations.yaml) | Machine-readable obligation table of the declared pilot that the evaluator and runner load; kept with the contract data. |

The ontology migration records that used to sit next to this specification
are archived at the
[`release-2026-10-11`](https://github.com/de4sdv/DE4SDV/tree/release-2026-10-11/docs/method-conformance)
tag. The data the runtime reads, including the frozen records and the
identity register, is in
[`de4sdv/semantic/contract-data/`](../../de4sdv/semantic/contract-data/README.md).

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
