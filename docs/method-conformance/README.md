# Method Conformance — deterministic engine specification (Packages A–D)

This directory holds the governing specification for the deterministic
method-conformance subsystem: the frozen planning baseline, the normative
result-algebra spelling, the extracted MC acceptance matrix, and the declared
Phase-10 pilot.

| Document | Role |
|---|---|
| [conformance-baseline.md](conformance-baseline.md) | FROZEN planning baseline (digest `427410f3...`); the conformance specification. Unchanged copy; changes require a reviewed amendment. |
| [result-algebra.md](result-algebra.md) | Normative field/reason-vocabulary spelling fixed by Package A (frozen baseline §7–§8). |
| [mc-outcome-owner-matrix.md](mc-outcome-owner-matrix.md) + [mc-matrix.json](mc-matrix.json) | All 40 MC cases with owners (B: 4, C: 29, D: 7), machine-extracted from the frozen baseline. |
| [pilot-scope.md](pilot-scope.md) | Declared real Phase-10 pilot, admitted configuration, identities, and the admitted acceptance-authority gap. |

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
