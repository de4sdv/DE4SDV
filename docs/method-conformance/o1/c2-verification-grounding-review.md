# O1 c2 — VerificationCase / verifiedBy native-library semantic grounding review

**Scope:** exactly two semantic identities — class `VerificationCase` and
relationship `verifiedBy`. No other class or predicate is part of c2.

**Boundary:** this is an O1 review record under
`docs/method-conformance/o1/` (PR #249, branch
`feat/o1-semantic-authority-inventory`, base `e99f46d0` = `origin/main` at
task start). It changes no runtime and no model semantics; it makes no
authority transition. The reviewed decisions live in
`authority-review-decisions.yaml`; the machine locks live in
`tests/test_o1_c2_verification_grounding.py`.

**Governing rule applied:** the DE4SDV Unified Semantic Engineering Plan v1.1
(§4 native/library grounding invariant, §10 verification-case proof
requirement, UG-28): an API metaclass alone is not sufficient semantic
evidence — for every standard KerML/SysML semantic kind, preserve and prove
the applicable standard-library grounding, with explicit/implied provenance,
and keep the representation mechanics separate from the engineering meaning.
The Method Conformance Plan's separation of a modeled verification
relationship, an execution result, and an acceptance decision governs the
claim boundary.

---

## 1. Exact-fit review — `VerificationCase`

### 1.1 What was inspected

- Pinned standard library (via the locked toolchain),
  `Systems Library/VerificationCases.sysml`:
  - `abstract verification def VerificationCase :> Case` — documented as
    "the most general class of performances of VerificationCaseDefinitions";
  - `abstract verification verificationCases : VerificationCase[0..*]
    nonunique :> cases` — "the base feature of all VerificationCaseUsages";
  - the case objective carries
    `requirement requirementVerifications : RequirementCheck[0..*] :>
    subrequirements` — "a record of the evaluations of the RequirementChecks
    of requirements being verified".
- Pinned standard library `Systems Library/Requirements.sysml`:
  `RequirementCheck` is "the most general class for requirements checking";
  its subject doc says the entity "being checked for satisfaction of the
  required constraints".
- Real DE4SDV constructs (committed model): the verification definition
  `VC-AEBS-009D-DE` (`ConsciousOverrideVerification`), six verification
  usages `VC-AEBS-009D-01..06` with authored typing to the definition, and
  the definition objective's three `verify` statements. The verify targets
  across the model are evidence contracts and acceptance criteria — all
  requirement usages.
- Retained Lane B grounding witnesses (§3).

### 1.2 Clause-by-clause review of the YAML description

> "A planned or executed check that evaluates whether a requirement or model
> claim is satisfied."

| Clause | Standard basis | Verdict |
|---|---|---|
| "check" | `RequirementCheck` check vocabulary; the case's objective is a record of requirement checks | exact |
| "planned or executed" | the construct spans specification (definitions/usages) and performance level ("performances of VerificationCaseDefinitions"); it does NOT assert execution of any given case | bounded — recorded |
| "evaluates whether … is satisfied" | library doc: checks on whether the verified requirements "have been satisfied"; the subject is "checked for satisfaction" — the check evaluates, it does not assert satisfaction | exact |
| "a requirement or model claim" | DE4SDV verify targets are requirement usages (evidence contracts, acceptance criteria); claims enter the construct through requirement-modeled checkables | bounded — recorded |

### 1.3 Decision

**Exact bounded fit.** The DE4SDV concept is the native construct itself;
DE4SDV adds no competing semantics and no parallel application class is
introduced. The wording describes the specification/performance scope and the
check-for-satisfaction purpose without asserting any outcome. Recorded
boundary: the class is a verification-objective carrier only — it does not
assert that any check ran, produced a result, or reached an outcome.

No YAML edit was made (none is required for an exact fit; silence was not
"fixed" by rewording).

---

## 2. Exact-fit review — `verifiedBy`

### 2.1 What was inspected

- Pinned standard library `Systems Library/SysML.sysml`:
  `metadata def RequirementVerificationMembership specializes
  RequirementConstraintMembership` with
  `derived ref item verifiedRequirement : RequirementUsage[1..1] redefines
  referencedConstraint` (and `ownedRequirement` redefining `ownedConstraint`);
  case-side `verifiedRequirement : RequirementUsage[0..*]` features on
  `VerificationCaseDefinition` and `VerificationCaseUsage`.
- The DE4SDV mapping (`de4sdv-basic-ontology.yaml`): strategy
  `verification-membership`, membership type
  `RequirementVerificationMembership`, element types
  `VerificationCaseUsage`/`VerificationCaseDefinition`, reference property
  `verifiedRequirement`, direction `reverse`, strength
  `native-verification`.
- The runtime traversal `_verification_membership_hops` (unchanged by c2;
  behavior locked by the c2 tests and the pre-existing traversal tests).

### 2.2 Semantic reading

- The bounded query `Requirement -> VerificationCase` means: **the requirement
  is declared as a verification objective of the returned verification case
  through native SysML verification semantics.**
- The native witness is the `RequirementVerificationMembership`: it anchors on
  the verified requirement (`verifiedRequirement` / member, with the
  `ReferenceSubsetting` bridge where the serializer references a shadow
  usage), and the case is resolved from the ownership chain
  (objective objective-membership -> case), stopping only at a
  `VerificationCaseUsage` or `VerificationCaseDefinition`.
- The reverse direction reverses traversal only; the modeled fact is the
  declared verification objective.
- Representation mechanics — membership type, reference property,
  owner-chain traversal, direction, usage/definition resolution — remain in
  the `sysml_mapping` and the traversal implementation. They implement the
  reviewed meaning; they are not themselves the engineering meaning, and
  serializer path equality is not treated as semantic proof.

### 2.3 Decision

**Exact bounded fit.** Native verification-objective semantics support the
declared query exactly, and the relationship exists independently of
execution or evaluation records. Recorded claim boundary: declared
verification-objective / coverage relation only — no execution, outcome,
satisfaction, approval, or certification implication. The predicate name is an
English label for the native fact, never an outcome claim.

Named semantic laws (machine-locked as negative tests): only configured
`RequirementVerificationMembership` objects qualify; a generic Dependency, a
SubjectMembership, `VerificationMethod` metadata, retained execution or
evaluation records, and name-only correspondence are not substitutes; the
owner chain must resolve to a verification case usage/definition; there is no
name-based fallback.

---

## 3. Standard-library grounding evidence (Lane B, retained)

The retained exact-toolchain evidence is the privileged run **34576049742**
(conclusion: success) at candidate
`0a23902370de9fc74d6118afe480382e0b0d8aa0`, artifact `10195168006`
(`full-model-api-ingestion-0a23902370de9fc74d6118afe480382e0b0d8aa0`).
Its read-back (`de4sdv-pilot-readback.json`) proves, from the imported
closure produced with `include_implied`:

- **definition** — `VC-AEBS-009D-DE` (`VerificationCaseDefinition`) grounds
  through a toolchain-materialized implied `Subclassification` to the
  recorded anchor for `VerificationCases::VerificationCase`
  (`47f5248d-9140-50c8-b28c-16d68d573621`), property path `general`,
  mechanism `external-reference` (split out-of-bundle shape), provenance
  `implied`, uri into the pinned `Systems Library/VerificationCases.sysml`;
- **usage** — each of the six `VC-AEBS-009D-01..06`
  (`VerificationCaseUsage`) carries the authored typing to the DE4SDV
  definition (serializer shape: explicit `FeatureTyping`) plus an implied
  `Subsetting` to the recorded anchor for `VerificationCases::verificationCases`
  (`91f01a71-e825-5ed0-851e-540cac929303`), same document, provenance
  `implied`;
- **verified objective** — the definition objective carries three
  `RequirementVerificationMembership` witnesses (the verified requirement
  references), inherited by all six usages.

The API metaclass and the library grounding are separate evidence fields in
the read-back; the metaclass alone fails closed (UG-28), and a missing
implied edge, wrong anchor id, or wrong library document fails closed — all
machine-locked in the c2 tests.

**Anchor handling:** the pinned standard-library qualified names
(`VerificationCases::VerificationCase`, `VerificationCases::verificationCases`)
are used only by the controlled library-proof step: the licensed exporter
resolves those known library anchors by name from the pinned library
documents and records them in the export artifact (`library_anchors`); the
read-back then proves each implied edge targets exactly the recorded anchor
id and carries a uri into `VerificationCases.sysml`. That controlled
library-proof step must never become a general runtime name fallback: model
and user identities do not fall back to names — the read-back resolves pilot
identities by authored `declaredShortName` only, and the runtime traversal
resolves by identity (never by `declaredName`). The anchor evidence is pinned
to the run-specific ids above; no library UUID is treated as a general
runtime constant.

---

## 4. Evidence-state decision (Option A, not Option B)

The historical exact-toolchain run is retained as **supporting evidence
only**. The rows record `parity-reviewed`, not `exact-toolchain-validated`,
because no existing reviewed mechanism binds that historical run to the
claim as exact-toolchain evidence for the current inventory revision. The
distinction was made explicitly:

| Dimension | Lane B evidence | Current review baseline |
|---|---|---|
| Historical exact candidate revision | `0a23902…` (branch `feat/lane-b-method-contract`; squash-merged as `d68d4a2`) | — |
| Current PR revision | — | this branch's head (moves with each c2 commit) |
| Relevant model sources | `aebs_override_verification.sysml` | blob `3842467e…` byte-identical at both revisions |
| Read-back/proof implementation | `scripts/verify_pilot_readback.py` | blob `7dec02d8…` byte-identical at both revisions |
| Traversal / relationship machinery | `de4sdv/semantic/traversal.py` `_verification_membership_hops`, `relationships.py`, `method_contract.py` | function and blobs byte-identical (`relationships.py`, `method_contract.py` unchanged; the traversal file gained unrelated K content, the verification function is unchanged) |
| Pinned standard library identity | `sysand-lock.toml` | blob `5f0700b3…` byte-identical at both revisions |

Identical blobs are strong supporting evidence, but no reviewed
revision/content-equivalence mechanism exists that carries a historical run
forward into an `exact-toolchain-validated` inventory claim — and this
review does not invent one. (`privileged-closure-proven` is not appropriate
here: no closure record is created by c2, and the retained artifact window
does not change that.) Advancing either row beyond `parity-reviewed` requires
a documented, revision-bound exact-toolchain mechanism (or a fresh
exact-head run plus a reviewed binding record); neither is fabricated here.

---

## 5. Claim boundary and non-claims

- `verifiedBy` (and the `VerificationCase` class) claim **declared
  verification-objective / coverage semantics only**. Qualifying a
  requirement as a verification objective of a case implies no execution, no
  outcome, no satisfaction, no approval, and no certification.
- Not an authority transition: `VerificationCase` stays `native-sysml`
  (unchanged); `verifiedBy` current authority stays `legacy-yaml` (the
  authored mapping remains the O1 authority; any transition is an O3
  decision). No authority-current count changes.
- Not O2: no Semantic Projection row is generated for either identity; the
  generated inventory remains governance metadata, never runtime authority.
- No runtime/query/model change: no traversal behavior change, no model file
  change, no new traversal strategy, no second verification traversal.
- No privileged ingestion was dispatched for c2; the retained Lane B run is
  cited, not repeated. The retained run is not claimed as a
  `privileged-closure-proven` closure.
- No YAML ontology edit was made; the reviewed decisions dataset is
  governance metadata.

---

## 6. Source-domain grounding of the `verifiedBy` witness (c5-R2 consistency review addition)

The declared predicate is `Requirement -> VerificationCase`. Section 2
established the native witness and its claim boundary; the **source-domain
side** of the declaration had remained implicit. The c5 R2 verifiedBy-domain
consistency review — recorded in the c5 integration review, Section 17.2 —
asked the exact question: for a real `RequirementVerificationMembership`
anchor in the retained full-model export, can the anchored
`RequirementUsage` be machine-resolved, deterministically and without
heuristics, to the governed DE4SDV `Requirement` domain?

Measured on the retained Lane B export (offline replay through the
repository machinery):

- every RVM anchors a serialized **shadow reference usage**; through the
  ReferenceSubsetting bridge of Section 2.2, **30 of the 64 anchors resolve
  to 15 declared acceptance-criterion-role usages** whose authored
  typing/classification chain
  (`MiddlewareAcceptanceCriterion` / `VisualizationAcceptanceCriterion`
  -> `EvidenceContractTraceabilityRequirementCandidate` ->
  `RequirementCandidate`) grounds them in the validated Requirement lineage
  with `explicit` provenance per the reviewed model-edge classifier. Under
  the c5 review's identity rule (the Requirement lineage includes the
  acceptance criterion) these are DE4SDV Requirements;
- the remaining **34 anchors resolve to evidence-contract-role usages whose
  definitions carry no specialization lineage**: identity unresolved, no
  DE4SDV class claim, fail closed — they are never emitted as `verifiedBy`
  subjects.

Enforced discriminator (machine-resolvable, deterministic, revision-bound,
fail-closed, independent of names and layout): **direct Requirement-lineage
grounding of the queried usage, or the reviewed ReferenceSubsetting shadow
bridge followed by that grounding proof on the declared usage**. The
enforcement lives in the **semantic runtime itself**: the `verifiedBy`
traversal strategy (`_verification_membership_hops`, `de4sdv/semantic/
traversal.py`) resolves the relationship's declared ontology `domain`
through the validated lineage resolver and emits a hop only for a source
proven in the governed `Requirement` domain — candidate-first (a source
with no native verification participation is quiet absence without lineage
resolution), never name-based, failing closed when a candidate must be
decided but no validated binding is available. The Proof-B
subject-selection/assertion boundary in `scripts/validate_semantic_mcp.py`
consumes the same runtime-owned identity rule (`requirement_identity`)
as defense-in-depth; it does not define a stronger rule than the runtime.
Every public predicate consumer — `semantic_neighbors`, `impact`, `trace`,
`verification_coverage` — is therefore domain-enforcing by construction:
the 34 unresolved anchors receive zero public `verifiedBy` claims, not
merely zero MCP Proof-B selection. The c2 claim boundaries in Sections 2
and 5 are unchanged — no execution, outcome, satisfaction, approval, or
certification meaning is added by this record. Both c2 rows remain
`parity-reviewed`; `verifiedBy` current authority remains `legacy-yaml`
during O1, and no O2/O3 action follows from this addition.
