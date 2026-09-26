# O4 W5 external-reference acceptance — bounded engineering review

Status: **accepted-as-engineering-review-evidence** (bounded engineering review
evidence recorded in-repository; NOT a personal owner approval and NOT authority
activation).

## Purpose of this record

This document records the bounded engineering review that accepts the W5
external-reference contract: the model-owned typed-reference schema
`de4sdv.evidence-reference/v1`, the baseline manifest schema
`de4sdv.baseline-manifest-reference/v1`, and the four profile entries in
`docs/method-conformance/o4/external-reference-profile.yaml`
(`EvidenceArtifact`, `hasEvidence`, `capturedInBaseline`, `Baseline`). The
profile references this document per identity, and that reference is recorded
here as the retirement precondition for those rows; the YAML retirement itself
completes with the O4 closure stage — this review does not retire a row and
does not activate anything.

## Reviewed identities (one row per profile entry)

| identity | reviewed disposition | reviewed representation |
| --- | --- | --- |
| EvidenceArtifact | KEEP_EXTERNAL_REFERENCE (external evidence systems; model owns typed reference schema) | external-reference-record |
| hasEvidence | KEEP_EXTERNAL_REFERENCE (external evidence system; model owns only typed reference schema) | external-reference-record |
| capturedInBaseline | KEEP_EXTERNAL_REFERENCE (external configuration/evidence baseline manifest; modeled references only) | external-reference-record |
| Baseline | KEEP_EXTERNAL_REFERENCE (external for baseline content; model-authoritative for the reference identity and its claim boundary) | model-resident-boundary-identity |

Definitions are read from the canonical integrated review
(`docs/method-conformance/o4/ontology-review/integrated-review.json`) at check
time by the governed contract; this document is a review record, never a second
source of definition text.

## Reviewed profile payload binding

Reviewed-profile-payload: `sha256:94c072a63caf2e8a8074d25bef5227b8d17e8994439de153d7bfad30fd06cd10`

This digest pins the existing reviewed profile content, including mechanics,
schema contracts, representations, declarations and scope. It uses Unicode JSON
with sorted keys, compact separators and unescaped Unicode over the fields
selected by `reviewed_profile_digest`. The acceptance-document back-reference
and progress prose are excluded to avoid circular hashing. The profile in turn
pins this document's complete bytes. Changes require deliberate review and
updates to both records; matching digests do not constitute personal approval.

## Review method

1. Each identity's canonical review row was required to carry exactly one
   `KEEP_EXTERNAL_REFERENCE` disposition with no projection requirement, no
   API profile requirement, no traversal and external runtime support; nothing
   wider is accepted here.
2. The accepted typed-reference and baseline-manifest mechanics were read for
   unambiguity: every field names one exact external fact (case identity,
   artifact identity, exact revision, digest, run, tested scope; baseline
   identity, manifest digest, exact version identities), and inclusion is exact
   membership — a different revision of the same artifact identity is not
   included (no carry-forward).
3. The claim boundary was checked to be strictly narrower than the reviewed
   definitions: the contract records references only and never a verdict, a
   pass, a verification, an acceptance or an approval, and it implements no
   traversal.

## Per-identity acceptance

### EvidenceArtifact

Accepted as reviewed: *a reviewable artifact that supports a verification,
validation, assurance, or release decision* (canonical review definition). The
model-owned representation is the typed reference record
(`de4sdv.evidence-reference/v1`) carrying case identity, artifact identity,
exact revision, digest, run and tested scope. Artifact bytes, artifact status,
artifact acceptance decisions and any verdict stay with the external evidence
systems; external authority is retained in full.

Non-claims: no artifact content is mirrored; no pass, verification, acceptance
or approval is inferred from a validated reference; no traversal is implemented
or claimed; no row is retired by this review.

### hasEvidence

Accepted as reviewed: *verification case is associated with an externally
retained evidence artifact whose identity, digest, run and tested scope are
explicit; association implies neither pass nor acceptance* (canonical review
definition). The model-owned representation is the association carried by the
typed reference record of the verification case. The association exposes no
verdict, no pass and no acceptance, and the external-data-required condition is
surfaced rather than reported as an empty hop.

Non-claims: no content mirroring; no pass/verification/acceptance/approval
inference; no traversal; external evidence-system authority retained.

### capturedInBaseline

Accepted as reviewed: *evidence artifact version is explicitly included in an
immutable identified baseline manifest; inclusion does not itself approve
evidence* (canonical review definition). The model-owned representation is the
typed reference to the identified immutable external manifest
(`de4sdv.baseline-manifest-reference/v1`); membership is exact version-identity
membership. The model keeps no second mutable baseline list, and baseline
contents stay with the external configuration/evidence system.

Non-claims: inclusion never approves evidence; no content mirroring; no
verdict, pass, verification, acceptance or approval inference; no traversal;
external baseline authority retained.

### Baseline

Accepted as reviewed: *a reviewed and controlled state of model, evidence,
configuration, or publication artifacts, referenced without implying accepted
evidence* (canonical review definition). The model-owned representation is the
existing model-resident boundary identity `part def DE4SDVEvidenceBaseline`
(reference documentation parity only; no rename, no second mutable baseline
list). The declaration describes what is referenced, not who grants approval;
baseline content stays external.

Non-claims: no content mirroring; no verdict, pass, verification, acceptance or
approval inference; no traversal; external baseline authority retained.

## Explicit non-claims (document-wide)

- This is engineering review evidence recorded in-repository. It is **not** a
  personal owner approval, not a method-owner signature, and not a compliance
  or certification statement.
- Acceptance is a review act on the schema, the mechanics and the profile
  entries. It changes no runtime behavior: `activation` stays `none`, support
  stays `external`, and no traversal, mirroring, baseline list or admission is
  introduced.
- The contract never fetches, mirrors or re-hosts external content; the runtime
  never reads the profile, this review, or the review/register inputs.

## Bounded note — ArchitectureDecisionRecord

`ArchitectureDecisionRecord` is **not** a member of this evidence-reference
family: `dependency_flags.evidence_lineage` is false for it, so it receives no
`accepted_ref` and no row in this document (the family is derived from the
governed register, and a false flag keeps it out). Its O1 residual string was
corrected from the inapplicable O2-admission text to external-boundary
retention: the reference identity and typing role are bound through the kernel
mapping plus the R003 origin grounding, while ADR content stays external. Those
structured flags require no projection and no profile, so no acceptance entry
for this identity is asserted or needed here.

## Machine-checked anchors

`external_reference_contract.py` refuses a profile entry whose `accepted_ref`
does not resolve to a repository governance document under `docs/` that
carries the `accepted-as-engineering-review-evidence` marker, records the
identity as a fragment (this document's section headings), and records the
identity as a table row. A free-text reference, a personal approval claim or a
missing identity row fails closed.