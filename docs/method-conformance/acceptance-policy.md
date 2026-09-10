# Proposed Authorization Policy: `de4sdv.acceptance.maintainer-decision.v1`

**Status: Proposed** (this document; ADR 0019 amendment). Not activated; no
campaign acceptance exists or is created by this document. Activation and any
actual decision under it belong to the DE4SDV maintainer.

## Identity

```text
policy_id: de4sdv.acceptance.maintainer-decision.v1
status: Proposed
applies_to: acceptance obligations of deterministic method-conformance
            contracts (attestation_policy_ref references)
```

An evaluation that references a policy identity it cannot resolve to this
definition (unknown id, unparseable definition, version mismatch) is a
**contract validation ERROR** (`INVALID_CONTRACT`) — never INDETERMINATE.

## Authority

- Sole decision authority: the DE4SDV maintainer (Orkun Yilmaz) acting in the
  maintainer role established by GOVERNANCE.md/MAINTAINERS.md.
- A decision is attributable only when it names the deciding maintainer and
  the decision date inside the record.

## Accepted outcome (what a decision record must contain)

An acceptable decision record is a committed file under
`docs/acceptance-decisions/` with:

```text
schema: de4sdv.acceptance-decision.v1
policy_id: de4sdv.acceptance.maintainer-decision.v1
decision_id: DEC-<subject>-<seq>          (registered naming-gate prefix)
campaign_scope: increment id + tested-scope fingerprint reference
covered_profiles: [ ... ]                 (enumerated profile identities)
outcome: accepted | rejected              (binary; other literals invalid)
decider: maintainer identity
decision_date: ISO date
supersedes: [ decision_id, ... ]          (optional)
reason: short rationale
```

A record whose `outcome` is neither `accepted` nor `rejected`, that lacks
`decider`/`decision_date`, or that references an unknown campaign scope does
not count as a decision (it is an invalid record — obligation-level
`BINDING_MISMATCH` diagnostic, not acceptance).

## Evidence binding

A decision binds to the campaign's declared tested scope by referencing the
same fingerprint identity the conformance manifest uses
(`execution_head` + scope fingerprint). It does not restate test results; the
evidence remains the retained records. A decision whose scope reference cannot
be matched to the evaluated campaign's declared tested scope does not cover
it (`EVIDENCE_SCOPE_MISMATCH` diagnostic on the matching attempt).

## Decision-population completeness

- A decision covers **exactly** the profiles enumerated in `covered_profiles`.
- Each profile's acceptance obligation is satisfied only by a covering
  `accepted` decision; profiles outside every decision's enumeration have no
  acceptance.
- **Completeness of the population itself is undecidable from enumeration
  alone**: the evaluator therefore treats the declared tested-scope manifest
  (the pinned six-profile set) as the closed universe. A profile is
  acceptance-covered iff some valid `accepted` decision enumerates it. The
  universe being closed and machine-declared (campaign manifest) is what
  makes "no covering decision" a definite FAIL rather than an open-ended
  search.
- A `rejected` decision covering a profile means the acceptance obligation
  for that profile FAILs with the decision as retained reason — it is a
  decision, not an absence.

## Conflict and supersession

- Two or more valid decisions covering the same profile with conflicting
  `outcome` values are **unresolved** unless one explicitly `supersedes` the
  other(s): unresolved conflict ⇒ the profile's acceptance obligation is
  `ASSESSED`/`INDETERMINATE`/null with `ACCEPTANCE_AUTHORITY_MISSING` plus a
  `diagnostics` entry naming the conflicting decision ids (MC-20: no
  timestamp-based winner).
- A valid `supersedes` edge resolves the conflict in favor of the superseding
  decision.
- Supersession cycles (A supersedes B, B supersedes A) are a policy-integrity
  violation ⇒ obligation `ERROR` (`BINDING_MISMATCH`).

## Disposition mapping (summary for obligation 11)

| Condition | Result |
|---|---|
| Valid `accepted` decision covers the profile | COMPLETE/PASS |
| Closed universe, no covering decision (incl. valid `rejected`) | COMPLETE/FAIL (`ACCEPTANCE_AUTHORITY_MISSING`) |
| Conflicting decisions without valid supersession | COMPLETE/INDETERMINATE/null |
| Evidence basis incomplete (records unavailable) | INDETERMINATE (`ACCEPTANCE_AUTHORITY_MISSING` + `INPUT_UNAVAILABLE`) |
| Policy identity unresolvable | Contract ERROR before evaluation (`INVALID_CONTRACT`) |
| Supersession cycle | ERROR (`BINDING_MISMATCH`) |
