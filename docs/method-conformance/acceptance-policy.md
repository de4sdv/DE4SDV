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
- A `rejected` decision covering a profile means the acceptance obligation
  for that profile FAILs with the decision as retained reason — it is a
  decision, not an absence.

### Registry completeness (independent of profile completeness)

Two distinct completeness questions must not be conflated:

1. **Profile completeness** — is every profile of the closed universe covered
   by some decision? Answered by enumeration against the declared
   tested-scope manifest.
2. **Registry completeness** — does the evaluated decision registry contain
   every decision that exists? The evaluator cannot prove a negative about
   the world; a decision may exist outside the scanned registry location
   (uncommitted, misfiled, forgotten).

The registry is the machine-declared location bound by this policy (the
pinned registry path/pattern below, evaluated against the candidate
revision). Registry completeness is an **evaluation precondition**: the
evaluation asserts, per profile-acceptance obligation, that the registry was
scanned completely and successfully — bounded listing, readable records,
schema-valid entries, no traversal truncation.

| Registry scan condition | Consequence for obligation 11 |
|---|---|
| Registry scanned completely; every record schema-valid | Usable result per the disposition mapping below (FAIL where no covering decision exists) |
| Registry location missing, unreadable, or truncated | `ASSESSED`/`INDETERMINATE`/null (`INPUT_UNAVAILABLE`) — no FAIL may be derived from an incompletely scanned registry |
| Any record in the registry fails schema validation | `ASSESSED`/`ERROR`/null (`BINDING_MISMATCH`) naming the invalid record — an invalid record could be the missing decision |
| Registry resolvable and completely scanned, profile uncovered | `ASSESSED`/`COMPLETE`/`FAIL` (`ACCEPTANCE_AUTHORITY_MISSING`) |

A FAIL for an uncovered profile is therefore sound **only under a proven
complete registry scan** — the closed profile universe answers "which
profiles need decisions"; the proven-complete registry scan answers "no
decision for them exists in the record".

### Registry binding (machine-declared)

```text
registry_path: docs/acceptance-decisions/
registry_binding: candidate revision (the decision records are evaluated as
                  committed at the evaluated candidate revision)
scan_completeness_assertion: bounded recursive listing of registry_path with
                  zero unreadable files and zero schema-invalid records
```

## Conflict and supersession

- Two or more valid decisions covering the same profile with conflicting
  `outcome` values are **unresolved** unless one explicitly `supersedes` the
  other(s): unresolved conflict ⇒ the profile's acceptance obligation is
  `ASSESSED`/`INDETERMINATE`/null with `ACCEPTANCE_AUTHORITY_MISSING` plus a
  `diagnostics` entry naming the conflicting decision ids (MC-20: no
  timestamp-based winner). `INDETERMINATE` here is the evaluation state —
  the conflict is a real, completed observation that prevents a verdict.
- A valid `supersedes` edge resolves the conflict in favor of the superseding
  decision.
- Supersession cycles (A supersedes B, B supersedes A) are a policy-integrity
  violation ⇒ obligation `ERROR` (`BINDING_MISMATCH`).

## Disposition mapping (summary for obligation 11)

| Condition | Result |
|---|---|
| Valid `accepted` decision covers the profile | `ASSESSED`/`COMPLETE`/`PASS` |
| Registry proven completely scanned; profile uncovered (incl. valid `rejected`) | `ASSESSED`/`COMPLETE`/`FAIL` (`ACCEPTANCE_AUTHORITY_MISSING`) |
| Conflicting decisions without valid supersession | `ASSESSED`/`INDETERMINATE`/null (`ACCEPTANCE_AUTHORITY_MISSING` + diagnostics) |
| Registry missing, unreadable, or truncated | `ASSESSED`/`INDETERMINATE`/null (`INPUT_UNAVAILABLE`) |
| Record schema-invalid in registry | `ASSESSED`/`ERROR`/null (`BINDING_MISMATCH`) |
| Evidence basis incomplete (records unavailable) | `ASSESSED`/`INDETERMINATE`/null (`ACCEPTANCE_AUTHORITY_MISSING` + `INPUT_UNAVAILABLE`) |
| Policy identity unresolvable | Contract ERROR before evaluation (`INVALID_CONTRACT`) |
| Supersession cycle | `ASSESSED`/`ERROR`/null (`BINDING_MISMATCH`) |
