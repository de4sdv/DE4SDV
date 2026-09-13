# K slice: v1.1 final representation decision (post-review)

Date: 2026-09-10 · Plan: DE4SDV Unified Semantic Engineering Plan v1.1 · Base head: `eb74b1f`

This record closes the two bounded semantic questions that remained after the
v1.1 reconciliation (`v11-reconciliation.md`) and supersedes that record's
representation choice. PR #243 stays draft; R6 remains gated.

> **Status update (O1 Wave 0c, 2026-09-12):** the decision below was implemented and
> merged. PR #243 is merged; R6 #3 was executed at `72926c95` (workflow `34630102233`)
> with a passing read-back proof and is retained as the `r6-3` closure record in
> [`../o1/closure-evidence.json`](../o1/closure-evidence.json). Support promotion now
> requires a structured, exact-revision closure attestation (O1 Wave 0b). The status
> sentences in this record ("PR #243 stays draft", "R6 remains gated") describe the
> state at decision time; the decision content (Q1/Q2) is unchanged and remains
> current.

## Q1 — Standard `Derivation` vs a minimal DE4SDV application connection

**Decision: minimal DE4SDV application connection definition
(`connection def DerivesFromNeed`). The standard Requirement Derivation
Domain Library is NOT used for this predicate.**

Exact semantic reason: the library's `Derivation` carries the normative
`originalImpliesDerived` constraint — an implication/satisfaction-strength
relation between original and derived requirements. DE4SDV's intended claim
is provenance only: "the design-input Requirement originates from the
stakeholder Need." These are different claims; "stronger than but consistent
with" is not sufficient because adopting the standard type makes the
implication semantics part of the DE4SDV model regardless of whether the
runtime executes it. Additionally, a stakeholder Need does not logically
imply the chosen design Requirement — the requirement operationalizes the
need — so the implication semantics would be semantically wrong here, not
merely stronger. Endpoint-metaclass fit alone does not justify adoption
(plan UG-30). The library stays pinned-but-unadopted (pin removal deferred
to O-stage lockfile hygiene; adoption gate unchanged).

What the application definition is:

```sysml
connection def DerivesFromNeed {
  end need : StakeholderNeedCandidate;
  end derivedRequirement : RequirementCandidate;
  doc /* Design-input provenance: the derivedRequirement originates from
       * the stakeholder need. Provenance/traceability semantics only:
       * neither satisfaction nor logical implication between the
       * connected usages is claimed; verification, evidence, and
       * acceptance claims are out of scope. Native direction:
       * need -> derivedRequirement. */
}
```

Properties:

- Need and Requirement remain distinct DE4SDV semantic roles; both are
  represented as SysML requirement usages typed by the kernel definitions.
- The typed ends are the model-resident carrier of domain
  (`RequirementCandidate` → Requirement lineage) and range
  (`StakeholderNeedCandidate` → Need lineage); the doc carries the meaning
  and claim boundary. No SemanticMetadata, no metadata workaround.
- One modeled fact per derivation; the five confirmed AEBS edges are
  `connection … : DerivesFromNeed connect <need> to <req>;`.
- Native direction is Need → Requirement; the DE4SDV query
  `derivesRequirementFromNeed` (Requirement → Need) is inverse traversal
  over the same witness, and `derivedRequirementsOfNeed` is the forward
  traversal. End roles are identified by the end's own typing against the
  kernel lineages — never by end order, never by query direction.
- No NRM process model; no library constraint is inherited.

## Q2 — YAML as a genuine parity oracle

**Decision: the projection now derives its semantic fields from the
validated model; YAML is loaded only for the parity comparison and any
drift fails generation.**

Authority chain implemented in `de4sdv/semantic/projection.py`:

1. `DerivesFromNeed` identity comes from the ingestion-validated kernel
   binding (no name fallback).
2. Domain/range/roles come from the definition's typed ends
   (`need : StakeholderNeedCandidate`,
   `derivedRequirement : RequirementCandidate`) in the bound revision.
3. Meaning and claim boundary come from the definition's ingested
   documentation; a definition without the claim-boundary doc fails
   generation.
4. The ontology YAML is then compared against these model-derived fields
   (definition name, roles, end types vs kernel declarations, strength,
   oracle definition text). Drift raises
   `ValueError("ontology parity oracle drift for …")` and no projection is
   produced.

Deliberately NOT a third authority: there are no new hard-coded Python
semantic constants — the module carries only the two role names and the
claim-boundary probe, both of which must match the validated model text or
generation fails.

Tests pinning this: `test_projection_definition_comes_from_model_doc_not_yaml`
(YAML definition tampering does not reach the projection; missing doc fails
closed) and `test_profile_mechanics_follow_model_authority_and_oracle_drift_fails`
(tampered oracle mapping fails the parity gate instead of being echoed).

## Q3 — Stale text

Kernel doc block, ontology definitions, SP6 comments, runtime/projection/
CLI docstrings, and test module docstrings were swept. The superseded
decision records (`representation-decision.md`,
`v11-reconciliation.md`) are retained as labeled audit trails with
pointers to this record.

## Non-claims

Design-input provenance only. No satisfaction, allocation, verification,
evidence, or acceptance claim. No library constraint adoption. R6
(privileged exact-head ingestion) was not executed as part of this record
(see the status update above).
