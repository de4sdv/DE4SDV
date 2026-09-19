# External evidence-reference contract — preparation (O4 W5 boundary rows)

Status: **PREPARED — validation machinery only; no boundary crossing, no row
closure.** This package does not activate traversal, does not mirror content,
and does not change any governed state.

## Determination requested by the execution strategy: A (machinery gap)

The execution strategy asked whether the missing contract for
`EvidenceArtifact`, `hasEvidence` and `capturedInBaseline` is

- **A** — already semantically governed, merely missing implementation
  machinery; or
- **B** — genuinely missing an owner semantic decision.

Determination: **A for the validation contract implemented here.** The
reviewed definitions already state exactly what a reference must carry and
what it must not imply:

- `hasEvidence`: a verification case is associated with an externally
  retained evidence artifact whose identity, digest, run and tested scope
  are explicit; the association implies neither pass nor acceptance.
- `capturedInBaseline`: the artifact version is explicitly included in an
  immutable identified baseline manifest; inclusion does not itself approve
  evidence.
- `EvidenceArtifact`: external evidence systems hold the content; the model
  owns only the typed reference schema; no content mirroring.

No either/or semantic choice remains open in those statements. What was
missing is fail-closed machinery that validates supplied records against
them — implemented in `de4sdv/semantic/external_reference_contract.py`.

**Explicit non-determinations (kept out of this package):** any traversal or
representation activation remains governed by the review's
"T/E evidence-reference design (boundary retained until reviewed)" evidence
item — that design remains the gate for stronger claims, and these rows stay
open. The machinery adds no authority; it only refuses malformed or
claim-inflating records.

## Contract

| function | validates | guarantees |
| --- | --- | --- |
| `validate_evidence_reference` | artifact identity, sha256 digest, run, non-empty tested scope | normalized record; `implies_pass`/`implies_acceptance` machine-locked `False` |
| `validate_baseline_manifest` | baseline identity, manifest digest, non-empty immutable entry list | normalized manifest |
| `baseline_inclusion` | reference membership in the manifest | `included` is explicit; `implies_approval`/`implies_pass` machine-locked `False` |
| `association_state` | reference validity | the only state an association may expose; no verdict fields |

## Fail-closed properties (test-locked)

- Missing/malformed identity, digest (non-sha256 or wrong length), run,
  scope (empty or non-string items) refuse.
- A baseline manifest without identity or entries refuses.
- No output ever carries verdict/pass/acceptance/approval fields; the
  contract never fetches content (source-scan test) and is read-only.

## What remains (unchanged by this package)

- The three rows keep their reviewed external-boundary state and their
  "T/E evidence-reference design" evidence item.
- Any future traversal/representation change for these rows goes through the
  normal reviewed path; this machinery is the contract such a change would
  consume, not a substitute for that review.