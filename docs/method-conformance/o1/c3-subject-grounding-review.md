# O1 c3 — `hasSubject` native-semantics / DE4SDV-scope review and hardening

**Scope:** exactly one semantic identity — relationship `hasSubject`
(`Requirement -> MemberProduct`). No class and no second predicate is part of
c3. `MemberProduct`, `Requirement`, `Need`, `SubjectMembership`, and
`ProductLineMemberProduct` were inspected as grounding/restriction evidence
only; none of them is a promoted c3 row.

**Boundary:** O1 review record under `docs/method-conformance/o1/`
(PR #249, branch `feat/o1-semantic-authority-inventory`, base `e99f46d0` =
`origin/main` at task start). `authority_current` stays `legacy-yaml` — no O3
cutover, no YAML retirement, no Semantic Projection row, no model change, and
no privileged ingestion. The reviewed decision lives in
`authority-review-decisions.yaml`; the machine locks live in
`tests/test_o1_c3_subject_grounding.py`.

**Governing rule applied:** reuse native semantics when they match exactly;
otherwise retain only the native grounding and represent the smallest
necessary DE4SDV application semantics. Exact semantic fit outranks the
previously proposed target classification.

---

## 1. Pre-implementation semantic decomposition (Phase A)

### 1.1 Native semantic core — what a subject means in native SysML

Reviewed from the pinned standard library shipped with the locked toolchain
(`sysand-lock.toml`):

- `Systems Library/SysML.sysml`:
  `metadata def SubjectMembership specializes ParameterMembership` with
  `derived item ownedSubjectParameter : Usage[1..1] redefines
  ownedMemberParameter`. A `SubjectMembership` is therefore a
  **parameter membership**: its member is the subject *parameter* of the
  owning requirement-like usage. `ParameterMembership` is where
  `subjectParameter` lives on requirement-like metadata in the same library.
- `Systems Library/Requirements.sysml`: `RequirementCheck` (the most general
  class for requirements checking) declares `subject subj : Anything[1]`,
  documented as "The entity that is being checked for satisfaction of the
  required constraints." The specialized requirement kinds re-type the
  subject (`FunctionalRequirementCheck::subject: Action`,
  `PhysicalRequirementCheck`/`DesignConstraintCheck::subject: Part`), which
  proves the native subject parameter carries **no member-product meaning** —
  its type is whatever the requirement's kind needs it to be.

Native conclusion: the native fact is *subject-of-requirement* — the bounded
declaration that an element plays the subject parameter role of the owning
requirement-like usage. It is agnostic about what kind of thing the subject
is. Deriving "subject means member product" from the API metaclass name
would be exactly the metaclass-name reasoning the plan forbids
(§4 native/library grounding invariant, UG-28).

### 1.2 DE4SDV source restriction — how `Requirement` lineage is proven

The ontology declares domain `Requirement`; the kernel models it as
`requirement def RequirementCandidate`
(`textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml`),
grounded through the SYSMOD seam. `Need` is
`requirement def StakeholderNeedCandidate` in the same file — a **sibling
lineage** with no specialization relationship to `RequirementCandidate`
(verified: the exported lineage closure of `RequirementCandidate` does not
contain `StakeholderNeedCandidate`).

Both serialize as API `RequirementUsage`. Consequently
`@type == RequirementUsage` cannot establish the domain, and the governed
model contains the live negative case: the stakeholder-need usages
`needBoundedDegradationAndAvailability` (N-AEBS-008),
`needTrustworthyInterventionDecisions` (N-AEBS-014), and
`needSafetyPathIsolation` (N-MW-004) are `StakeholderNeedCandidate`
specializations that carry a `subject memberProduct :
ProductLineMemberProduct` — a perfectly valid *native* subject membership
that must not satisfy `hasSubject : Requirement -> MemberProduct`.

Provenance mechanism: the ingestion-validated kernel binding index (ADR 0011)
supplies the validated `Requirement` root UUID; lineage membership follows
the representation-tolerant relationship graph (authored and tool-implied
subsumption kept separate, per the post-Lane-B include_implied export) and
usage typing. No names are consulted.

### 1.3 DE4SDV target restriction — how `MemberProduct` lineage is proven

The ontology declares range `MemberProduct`; the kernel models it as
`part def ProductLineMemberProduct`
(`textual-notation-of-model/packages/methods/de4sdv/de4sdv_product_line.sysml`).
The governed model shows real specializations
(`StandaloneAutowareAEBSReferenceMember`,
`AAOSIntegratedAutowareAEBSReferenceMember`,
`MiddlewareAutowareAAOSSDVConfiguredMember`,
`AEBSAutowareReferenceProduct`,
`AEBSAutowareAAOSSDVVisualizationTestArticle`), so legitimate targets ground
through the same lineage machinery — specialization closure plus usage
typing — never through the name `memberProduct`.

The governed model also contains real non-product subjects reached through
`SubjectMembership` from `RequirementUsage` owners: verification **benches**
(`bench` subjects of evidence contracts), System 2 **increments**
(`increment` subjects of visualization requirements), **claim subjects**
(`claimSubject`), and acceptance criteria subjects. A generic `PartUsage` —
or a part merely named `memberProduct`, or a part typed by an unrelated
same-named definition — is not a member product.

Provenance mechanism: validated `MemberProduct` kernel binding plus the same
lineage/typing machinery. No bare-name fallback.

### 1.4 Serialized shape evidence (Lane B boundary respected)

From the retained full-model candidate export (privileged run
`34576049742` at candidate `0a23902370de9fc74d6118afe480382e0b0d8aa0`,
read offline — no new ingestion):

- the subject member of `reqCommandEmergencyBraking` is a **`ReferenceUsage`
  named `memberProduct`** with an authored `FeatureTyping` to the validated
  `ProductLineMemberProduct` definition (plus tool-implied
  `Subsetting`/`Redefinition` edges to the same member) — so target
  validation must work on `ReferenceUsage`/`PartUsage` alike and must not
  assume `PartUsage`;
- the queried requirement is typed by `FunctionalRequirementCandidate` via an
  authored `FeatureTyping`;
- `SubjectMembership` serializes with `memberElement` (the subject),
  `owningRelatedElement` (the owner), `memberName`, and
  `ownedRelatedElement` — matching the configured `member_property`.

Lane B's verification-case `SubjectMembership` evidence proves the native
subject-membership serialization for verification usages; it does not
establish `hasSubject : Requirement -> MemberProduct` parity. Only the
serialized *shape* is reused here.

---

## 2. Authority-target decision — Case B

The canonical engineering fact is **genuinely narrower than native SysML**:

1. The native subject relationship is untyped with respect to product-line
   semantics — the standard library explicitly re-types subjects per
   requirement kind (Action, Part, AttributeValue, Anything), so no native
   semantics asserts "the subject is a member product".
2. `Requirement` (vs `Need`) and `MemberProduct` (vs bench/increment/claim
   subjects) are DE4SDV-specific restrictions over that native fact. They
   are semantic restrictions on the predicate's meaning, not typed query
   conveniences: they change what the predicate *claims*, and both are
   load-bearing (the need-sourced and bench-sourced negative cases are real
   model content, not hypotheticals).

Therefore `authority_target` changes to **`de4sdv-application-semantic`**,
with native `SubjectMembership` retained as the grounding/witness mechanism.
No second modeled relationship is created; the canonical fact remains derived
from the native witness plus the exact application restrictions.

Why Case A was rejected: Case A would require the Requirement/MemberProduct
constraints to be demonstrably only typed query restrictions over the same
native fact *without independent relation meaning*. They are not — the
domain restriction excludes `Need`, whose usages are native
subject-membership carriers in this very model, and the range restriction
excludes native subjects (benches, increments) that the model legitimately
declares. A predicate whose domain and range are DE4SDV application
restrictions with independent meaning is a DE4SDV application semantic
relation, by the same classification logic that put `specifiesFunction`,
`hasRelevantArchitecture`, and `hasRelevantEvidenceContract` (typed
Dependency-with-endpoint-restrictions) in `de4sdv-application-semantic`.

Why Case C was rejected: the classification is decidable from repository
evidence and the pinned library; nothing is unresolved.

`semantic_strength` review: `native-reference` stays. The strength describes
the witness (a native reference-form membership, not ownership, allocation,
configuration membership, product applicability, or realization). The
restrictions narrow the *claim*, not the *witness kind*; c3 therefore does
not rename the strength, and the predicate does not become any of the
forbidden stronger relations.

---

## 3. Runtime contract review and bounded hardening

### 3.1 Pre-c3 behavior (the over-return, quantified)

`SemanticTraversal._subject_membership_hops` checked only
`source.@type in owner_types` (`[RequirementUsage]`) and returned every
configured `SubjectMembership.memberElement` owned by that source. It did
not establish from the traversal itself that the source grounds in the
Requirement lineage or that the member grounds in the MemberProduct lineage.

Replayed offline against the retained full-model candidate export (289
`SubjectMembership` elements; replay script output preserved in the c3 test
literals):

| Population | Count |
|---|---|
| Pre-c3 `hasSubject` hops (`RequirementUsage`-owned, member resolvable) | 131 |
| Post-c3 hops (both lineages enforced) | 21 |
| Removed: owner outside the Requirement lineage (needs, evidence contracts, acceptance criteria, System 2 claims/requirements) | 57 |
| Removed: member outside the MemberProduct lineage (benches, increments, claim subjects) | 53 |
| Legitimate hops preserved | 21 of 21 |

The 21 preserved hops are exactly the governed member-product requirements
(3 evidence/`FeatureTyping`-typed requirement usages with
`memberProduct : ProductLineMemberProduct` subjects across the AEBS and
middleware need/requirement slices). The 110 removed hops are false
positives of the pre-c3 traversal — every one of them was previously
returned as a `hasSubject` `MemberProduct` product-line hop by
`ImpactService` (which labels subject hops `MemberProduct` /
`product-line` unconditionally).

### 3.2 The correction (narrowing only)

`_subject_membership_hops` now enforces the mapping's **governed
domain/range** — not a new mapping field set:

- `KernelContract.relationship_mapping` exposes the relationship's declared
  `domain`/`range` on `RelationshipMapping` (read from the existing ontology
  contract; the mechanics derive from the semantic contract and cannot
  redefine it — there is no second, competing type contract and nothing new
  to parity-check against the domain/range, because the enforcement inputs
  *are* the domain/range);
- the traversal resolves both lineages through the validated kernel binding
  index (`KernelBindingIndex.element_id_for`) and the representation-tolerant
  relationship graph (`_lineage_resolver`, `_endpoint_grounding`), keeping
  `explicit` vs `implied` grounding provenance in the hop witness;
- behavior is fail-closed in the reviewed directions:
  - source outside the Requirement lineage → quiet absence (no hop);
  - member outside the MemberProduct lineage → quiet absence (no hop);
  - missing validated binding for a declared lineage (or no binding index)
    → `IdentityNotFoundError` when qualifying candidates exist to decide —
    a missing semantic discriminator never broadens the predicate and never
    falls back to API metaclass, `declaredName`, `qualifiedName`, or source
    text;
  - a source owning no subject membership at all is quiet absence and
    performs no lineage resolution;
  - a mapping without a declared domain/range lineage refuses to run
    (`ValueError`) — corrupted configuration cannot silently degrade into
    vocabulary-only behavior;
- no name filter, no string heuristic (`declaredName == "memberProduct"` is
  nowhere), no runtime SysML source parsing.

`ImpactService` was not redesigned: the regression proves the tightened
traversal alone removes the mislabeling path (a non-member-product subject
can no longer reach `add_hop(..., "MemberProduct", "product-line")`), while a
valid Requirement→ProductLineMemberProduct subject still appears correctly.

### 3.3 Quiet absence vs non-qualifying native subject vs corrupted configuration

- **Quiet absence** — no qualifying `SubjectMembership` exists for the
  queried requirement: no hop, no lineage resolution.
- **Non-qualifying native subject** — a valid `SubjectMembership` exists but
  its owner or member is outside the governed lineages: filtered, no hop.
  This is native subject semantics that is simply not this predicate's fact.
- **Corrupted semantic configuration** — the mapping loses its declared
  domain/range lineage, or a required validated binding is missing/invalid
  while candidates exist to decide: hard error, never silent widening.

### 3.4 Product-line boundary

`hasSubject` remains the bounded subject relation only. It is not
`appliesToMemberProduct`, not PLE selection, not
`instantiatesCanonicalArchitecture`, not `realizedBy`, not allocation, not
satisfaction, and not verification success. The PLE rows
(`PLE-R -> PLE-Q -> PLE-S -> PLE-A`) are untouched.

---

## 4. Evidence-state decision

`evidence_state = parity-reviewed`:

- the semantic classification (Case B) is resolved and reviewed;
- the runtime/query mechanics demonstrably enforce the declared
  Requirement→MemberProduct contract (fail-closed positive/negative law
  tests over the real machinery, including the retained-export replay
  numbers locked as test constants).

Not `exact-toolchain-validated`: no fresh revision-bound exact-toolchain
proof specific to c3 exists, and no reviewed mechanism carries the retained
run forward as one (same reasoning as c2). Not
`privileged-closure-proven`: no closure record is created by c3.

No privileged ingestion was dispatched for c3; the retained export is cited,
never re-run.

---

## 5. Claim boundary and non-claims

- `hasSubject` claims the bounded native subject relation restricted to the
  canonical DE4SDV scope: the queried Requirement declares the returned
  member-product-lineage element as its subject. Nothing more.
- Not an authority transition (`legacy-yaml` current authority unchanged);
  not O2 (no generated projection row); no runtime consumer of the O1
  inventory was introduced.
- No `.sysml` file changed: the subject relation is already modeled; c3 only
  stops over-reading it. No parallel `HasSubject` relationship exists.
- c1 rows (7 parity-reviewed + the incomplete `MethodEvaluationScope`), c2
  rows (`VerificationCase` / `verifiedBy`), the K triple, the PLE-gated
  family, and c4/c5 rows are unchanged.

---

## 6. Machine locks (tests/test_o1_c3_subject_grounding.py)

- c3 contains exactly one promoted/reviewed predicate; no second row moved;
  the global parity set is exactly c1(7) + c2(2) + c3(1).
- `authority_current` remains `legacy-yaml`; final target equals the Case B
  decision; evidence maturity matches what is proven; no closure evidence;
  no Semantic Projection row; c1/c2/K/PLE/c4/c5 states unchanged.
- Positive: direct `ProductLineMemberProduct` usage typing and a legitimate
  specialization both produce exactly one hop, with lineage witnesses.
- Source negative laws (1–6 of the task), target negative laws (1–10),
  relationship negative laws (FeatureMembership, OwningMembership,
  RequirementVerificationMembership, Dependency, AllocationUsage, plain
  reference property, PLE configuration relation), missing-binding
  fail-closed, no-name-fallback probes, ImpactService regression, and
  mapping-parity (domain/range-derived enforcement) locks.
