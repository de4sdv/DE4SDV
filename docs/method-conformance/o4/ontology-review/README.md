# O4 — governed ontology review (accepted target input)

This directory records the independently rechecked, accepted semantic review
of the complete DE4SDV ontology inventory. It is **migration governance**: the
governed TARGET for the remaining O4 ontology-authority migration work. It is
**never runtime semantic authority** — no production path reads this package,
and nothing here changes current semantics.

## 1. What this review is

The review classified and dispositioned every identity of the ontology
inventory and established what the final DE4SDV semantic architecture should
contain before O4 migration is implemented. Current source inventory: **93
identities (59 classes, 34 relationships)**. Accepted target: **90 retained
identities** = 93 − 1 removal (`derivesNeedFromConcern`) − 2 merges
(`IncrementTraceabilityShell` into the redesigned trace expectation,
`validatesFitnessForUse` into the redesigned validation-planning relation).
The review also records an integration corruption that was found and repaired
during package revision 2 (see §2 below and `RECHECK-REPORT.md`).

## 2. Reviewed semantic baseline

Exact repository revision used as the reviewed semantic baseline:
`bc2b65abb623e50032f177d566e34e1a41c09f34` (repository `main` at review
time; recorded in `integrated-review.json` as `source_revision`).

## 3. Architecture rereview

The 24 architecture identities were independently rechecked at the reviewed
revision against repository evidence (declarations, native metadata usage,
normative clauses, runtime consumers, ADR and R3 enforcement, tests):
**24/24 decisions confirmed unchanged** (several evidence anchors
strengthened). Full record: `RECHECK-REPORT.md` §1.

## 4. O3 status

**No O3 semantic amendment required.** The frozen O3 13-identity production
migration is untouched by this package. The validator rejects any substantive
change to those identities without an explicit amendment record, and the
accepted state pins zero amendment records.

## 5. Authority boundary

This package is migration governance, never runtime authority. Applying it is
governed subsequent migration work (bounded waves with their own model,
projection, profile, evidence, and cutover steps). No ontology YAML, model,
Semantic Projection, API Representation Profile, traversal, query, or runtime
behavior is changed by this package, and no runtime consumer reads it as
semantic authority.

## 6. Relationship to O1, O3 and O4

- **O1 (historical)** — `docs/method-conformance/o1/`: semantic-authority
  inventory and reviewed authority decisions **at their revisions**. History;
  not rewritten by this review.
- **O3 (current production migration)** — the frozen 13-identity
  semantic-authority selection (Stage B). Current semantics; unchanged.
- **O4 (this package)** — the accepted review target for the remaining
  migration: current authority → this review's target dispositions → bounded
  migration waves → generated projection/profile expansion → per-wave
  evidence and cutover → authored-YAML consumer retirement → O4 closure.
  Wave structure, dependencies, blockers, and exit criteria live in
  `REVIEW.md` (Deliverable 8, "O4 migration burn-down").

## 7. Validating and regenerating

```bash
python scripts/ontology_review/validate_review.py            # validate + (re)write validation-report.json
python scripts/ontology_review/validate_review.py --check    # validate only
python scripts/ontology_review/consolidate_review.py         # regenerate integrated-review.json from decisions/
python scripts/ontology_review/generate_review_matrix.py     # regenerate REVIEW-matrix.md
```

The hardened validator is wired into `scripts/check_repo.py` (lightweight JSON
checks only — no licensed tools, no network, no specification inputs needed).
It enforces: exactly 93 source rows; 59 classes / 34 relationships; the exact
identity set with no duplicates; enum integrity; structured type integrity
(string-typed array fields rejected); path/reference sanity (character-split
fragments rejected); exactly the frozen O3 13 marked protected; no O3 semantic
change without an amendment record; required review fields present; the
accepted-target pins (90 retained, one removal, two merges); plus a
mutation self-test that must reject all planted defects.

## 8. Blocked / open

The review carries explicit unresolved owner decisions and blockers. They are
preserved, not resolved, by this package — see `REVIEW.md` (open-decisions
register and Deliverable 8 blocker/exit criteria). Highlights: the five
predicate renames; umbrella definition homes; the EvidenceContract identity
discriminator; the AcceptanceCriterion criterion-role contract; the
assurance-claim design decision; external evidence/status boundaries;
typed allocation-end proofs; and the product-line relations gated by the PLE
requalification gates. Verification follow-up: live-API read-back of the
22 implementation / 34 usage implied verification anchors before any claim
stronger than the export-level equivalence.

## Artifacts

| Artifact | Role |
|---|---|
| [`REVIEW.md`](REVIEW.md) | The complete review: executive assessment, detailed findings, target ontology counts, native/implicit semantic map, O3 findings, migration waves, dependency graph, open decisions, final answers. |
| [`REVIEW-matrix.md`](REVIEW-matrix.md) | All 93 identities, one row each (generated from `integrated-review.json`). |
| [`RECHECK-REPORT.md`](RECHECK-REPORT.md) | Package revision 2: integration-repair record, architecture recheck (24/24), integrity evidence, final decision answer. |
| [`normative-crosscut.md`](normative-crosscut.md) | Normative-source identity/version record, clause table, implicit-semantics conclusions, citation-drift hazard. |
| `integrated-review.json` | Canonical machine-readable review (schema `de4sdv-ontology-review-integrated/v2`). |
| `validation-report.json` | Output of the hardened validator. |
| `decisions/` | Canonical decision inputs: the four reviewed group decision files plus the pinned `base-records.json` inventory snapshot. |

Audit-only working files from the review (pre-repair artifacts, corruption
scans, specification extractions, legacy decision sources) are deliberately
**not** committed here; the repair and recheck conclusions are preserved in
`RECHECK-REPORT.md` and `validation-report.json`.
