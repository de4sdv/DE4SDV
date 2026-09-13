# O1 c5 — relevance and RFLP realization semantic review

**Scope:** exactly four governed identities — relationships `realizedBy`
(`Requirement -> ArchitectureElement`), `specifiesFunction`
(`Requirement -> Function`), `hasRelevantArchitecture`
(`Requirement -> ArchitectureElement`), and `hasRelevantEvidenceContract`
(`Requirement -> EvidenceContract`). No class and no second relationship is
part of c5. Conceptually the batch splits into **c5a** (`realizedBy` and the
RFLP cross-layer trace question) and **c5b** (the generic-Dependency relevance
family: `specifiesFunction`, `hasRelevantArchitecture`,
`hasRelevantEvidenceContract`); the split is conceptual only — one branch,
one PR, one batch.

**Boundary:** O1 review record under `docs/method-conformance/o1/` (PR #249,
branch `feat/o1-semantic-authority-inventory`). `authority_current` stays
`legacy-yaml` for all four rows — no O3 cutover, no YAML retirement, no
Semantic Projection row, no `.sysml` model change, and no new privileged
ingestion. The reviewed decisions live in `authority-review-decisions.yaml`;
the machine locks live in `tests/test_o1_c5_relevance_realization.py`.

**Retained evidence (supporting only):** every witness number below was
measured by replaying the retained full-model candidate export — privileged
run `34576049742` (success) at candidate
`0a23902370de9fc74d6118afe480382e0b0d8aa0`, artifact `10195168006`, digest
`sha256:e1c13b2e9d525dadddf4e861b52035e05252c7079b0e6ac989c7fef702a1718d` —
read offline through the repository traversal machinery. This is **supporting
evidence only** and **not current-head privileged closure**: the retained
revision predates HEAD by five requirement-to-need dependency sites converted
to `DerivesFromNeed` connections (see Section 7.4); that delta touches only
non-qualifying (domain-violation) witnesses and leaves every admitted set in
this review unchanged. No privileged ingestion was dispatched for c5.

**Governing rule applied:** native semantics are reused where they match
exactly; otherwise only the smallest necessary DE4SDV application semantics
are retained, derived from the declared domain/range, and enforced
fail-closed. A query shortcut is never promoted into a new engineering fact.
The authored YAML remains current authority for its unmigrated scope during
O1; the reviewed rows record the target migration, not its implementation.

**c5 correction (independent review, this revision):** the original c5b
disposition for `hasRelevantEvidenceContract` was rejected. Native
verification association cannot discriminate the declared `EvidenceContract`
range: its retained execution result (18 evidence-contract-role hops / 16
acceptance-criterion-role hops) treated acceptance-criterion-role usages as
successful evidence-contract witnesses. The re-review (Section 7.5) found
**no** machine-resolvable, non-heuristic `EvidenceContract` discriminator at
the reviewed revision, so the predicate moves to the governed
**blocked/deferred** state, the runtime range gate fails closed (**0 hops
emitted**), and the acceptance-criterion-role hop count after correction is
**0**. The other three identities in this batch are unaffected.

---

## 1. The four reviewed identities

| Identity | Declared contract (authored YAML) | Executable representation | c5 review question |
|---|---|---|---|
| `realizedBy` | `Requirement -> ArchitectureElement`; strength `allocation` | strategy `allocation`, `AllocationUsage`, outgoing | What does the `AllocationUsage` witness actually mean, and is `realizedBy` the correct canonical identity for it? |
| `specifiesFunction` | `Requirement -> Function`; strength `relevance` | strategy `dependency`, outgoing, source `RequirementUsage`, targets action-typed | Is the fact specification, or only relevance/addressal? |
| `hasRelevantArchitecture` | `Requirement -> ArchitectureElement`; strength `relevance` | strategy `dependency`, incoming, sources part/action-typed, MemberProduct lineage excluded | Is this a useful distinct cross-layer architecture relevance relation, and what exactly are its domain/range? |
| `hasRelevantEvidenceContract` | `Requirement -> EvidenceContract`; strength `relevance` | strategy `dependency`, incoming, sources `RequirementUsage` | Is there a machine-resolvable `EvidenceContract` discriminator, or does native verification association over-return? (correction: none exists — range blocked) |

The four identities do not share one semantic disposition. c5a resolves two
distinct primitives with different fates, and c5b resolves three relevance
predicates whose admissible sets required different corrections.

## 2. Governing RFLP invariant

DE4SDV preserves the engineering decomposition as the canonical progression
from design input toward realization:

```text
Need
  |
  v
Requirement
  |
  v   requirement/function relevance
Function
  |
  v   allocation
LogicalElement
  |
  v   realization
PhysicalElement
```

`PhysicalElement` covers physical realization broadly: software today, and
extensible to E/E, hardware/platform, ECU/sensor/actuator, and
mechatronic realization as those domains are modeled. The engineering graph
is **not required to contain exactly this hop count for every query**: direct
trace, allocation, or reference witnesses may exist for impact analysis,
navigation, traceability, and provenance. However, a direct
Requirement -> ArchitectureElement edge **must not collapse or redefine** the
canonical decomposition, and **a query shortcut is not automatically a new
engineering fact**. This invariant governs every disposition below: the
direct requirement-to-architecture witnesses are cross-layer trace or
allocation facts, and they are **not the canonical RFLP realization chain**.

## 3. `realizedBy` — layer classification of the AllocationUsage witnesses

Mandatory classification of every real allocation witness at the retained
revision, resolved through the serialized end chains (the allocation target
is a direct `target` reference; the source end resolves through
`EndFeatureMembership` `memberName = source` -> end feature -> authored
`ReferenceSubsetting`):

| Allocation definition (model-resident) | Count | Sides |
|---|---|---|
| `FunctionalToSystemResponsibility` | 17 | function -> logical responsibility |
| `System2RequirementToFunction` | 10 | **Requirement -> Function** |
| `LogicalRoleToPhysicalRealization` | 9 | logical role -> physical |
| `LogicalRoleToFunction` | 8 | logical role -> function |
| `SimulationLogicalToPhysicalRealization` | 7 | logical -> physical (simulation) |
| `LogicalToPhysicalSoftwareCandidate` | 6 | logical -> software |
| `PartialLogicalToPhysicalSoftwareRealization` | 5 | logical -> software (partial) |
| `LogicalToPhysicalItemRealization` | 4 | logical -> item |
| `AvailableLogicalToPhysicalSoftwareRealization` | 2 | logical -> software |
| `SystemToSoftwareSignalMappingCandidate` | 1 | part -> item |
| untyped allocation usages | 2 | part -> part |

Requirement-sourced allocation witnesses, by RFLP target layer:

- Requirement -> Function: **10** (all `System2RequirementToFunction`:
  `reqSourceFidelity`, `reqNativeParticipation`, `reqDe4sdvParticipation`,
  `reqNonInterference`, `reqFailClosedFreshness`,
  `reqAvailabilityDisposition`, `reqInvalidRejection`,
  `reqRestorationBehavior`, `reqRealAAOSRendering`, `reqEvidenceCorrelation`
  -> the `AebsVisualizationFunctionalFlow` actions `assemble`, `observe`,
  `supervise`, `validate`, `present`, `record`);
- Requirement -> LogicalElement: **0**;
- Requirement -> PhysicalElement: **0**;
- Requirement -> other ArchitectureElement: **0**;
- rejected/invalid requirement-sourced allocations: **0**.

Layer counts: **10 Function / 0 LogicalElement / 0 PhysicalElement / 0 other
ArchitectureElement / 0 rejected**.

No witness supports a physical-realization reading, and none collapses the
decomposition: the Requirement -> Function allocations are cross-layer
design-input allocation facts. **Representation finding (measured):** none of
the 71 real allocation objects serializes a `source` end through the
configured source property, so the current property-based mapping returns
**zero hops against the real serialized model**; the mapping is executable
only against fixture shapes. This representation gap is recorded as part of
the rename/replacement migration requirement (the replacement identity must
define its end-resolution mechanics). c5 performs **no runtime promotion**:
the bounded allocation trace stays inert on real shapes.

## 4. Primitive vs derived/composite

The propositions are explicitly distinguished and not interchangeable:

| Proposition | Status in the reviewed model |
|---|---|
| Requirement is allocated to ArchitectureElement | **modeled** — the native `AllocationUsage` fact (strength `allocation`) |
| Requirement is traced/relevant to ArchitectureElement | modeled separately as incoming/outgoing relevance dependencies (c5b family) |
| ArchitectureElement contributes to realizing Requirement | not modeled; not derivable from allocation alone |
| ArchitectureElement realizes Requirement | **not a primitive fact** — a composite statement |
| ArchitectureElement satisfies Requirement | not modeled; no satisfaction claim anywhere in c5 |
| Requirement realization can be derived by following Requirement -> Function -> Logical -> Physical | **future composite query**, not implemented in c5 |

`realizedBy` as currently named claims the realization proposition while its
executable witness carries only the allocation proposition. The composite
realization query (`realization_for(Requirement)`) is **not implemented in
c5**: it requires reviewed witnesses for requirement-to-function relevance,
`allocatedTo` (Function -> LogicalElement), and `deployedTo`
(LogicalElement -> PhysicalElement) — the latter two are independently
deferred with their own gates and were not touched. **`allocatedTo` and
`deployedTo` are untouched**; no `realizedBy = allocatedTo` or
`realizedBy = deployedTo` relation was defined.

## 5. Relevance-family semantic propositions (exact)

- `specifiesFunction`: **"function F is relevant to and addresses
  requirement R through an authored design-input trace (relevance only)"** —
  not specification, satisfaction, allocation, or verification.
- `hasRelevantArchitecture`: **"a native architecture-side part/action
  element is relevant to requirement R through an authored incoming
  dependency"** — no satisfaction, realization, allocation, verification, or
  product-line meaning.
- `hasRelevantEvidenceContract`: **no proposition is emitted at the reviewed
  revision** — the declared `Requirement -> EvidenceContract` range is
  **blocked**: native verification association is supporting evidence only
  (it also admits the acceptance-criterion role), no machine-resolvable
  `EvidenceContract` discriminator exists at this revision, and the
  fail-closed range gate returns nothing. The exact blocker, the accounting,
  and the forward resolution are Sections 7.5 and 14.

## 6. Native SysML/KerML analysis

- `AllocationUsage` is a native SysML v2 relationship-type usage. Its native
  meaning is allocation — the systematic assignment of responsibility — not
  realization. An allocation witness does not prove realization, and a
  requirement allocated to a function does not state that the function
  realizes the requirement.
- `Dependency` is a generic native relationship. Endpoint types and direction
  constrain which dependencies are traversable; they do not upgrade the
  relationship into specification, satisfaction, allocation, or verification.
- `RequirementVerificationMembership` is the native verification-objective
  witness (c2 review): the verified requirement anchors the membership
  (directly or through the serialized ReferenceSubsetting shadow bridge),
  and the owning verification case is resolved from the ownership chain.
  This machinery resolves the **supporting** evidence relation only; the c5
  correction showed it cannot establish `EvidenceContract` identity (it
  admits the acceptance-criterion role) and it no longer qualifies any hop.
- No native SysML/KerML relationship expresses "specifies" between a
  requirement usage and an action usage; the modeled fact is an authored
  generic dependency.
- The `ArchitectureElement`, `Function`, and `EvidenceContract` ontology
  classes are native-umbrella concepts without kernel declarations of their
  own (no file/declaration binding exists for them); the executable class
  filters are representation-level carriers of those umbrellas, and the only
  governed identity restrictions available at this revision are the
  Requirement, Need, AcceptanceCriterion, and MemberProduct lineages plus the
  native verification memberships. For `EvidenceContract` the correction
  makes this load-bearing: the class carries **no** kernel declaration
  binding and **no** model-resident structural discriminator (Section 7.5).

## 7. Real-model witness inventory (retained revision)

### 7.1 Before/after counts (hardened traversal)

| Predicate | Pre-c5 hops | Executed c5 hops | Corrected hops | Kept sources (correction) |
|---|---|---|---|---|
| `realizedBy` | 0 (zero real serialized witnesses) | 0 | 0 | 0 |
| `specifiesFunction` | 16 | 16 | 16 | 15 requirement sources |
| `hasRelevantArchitecture` | 143 | 42 | 42 | 42 |
| `hasRelevantEvidenceContract` | 140 | 34 (rejected as over-broad) | **0** | **0** |

### 7.2 `hasRelevantArchitecture` — false-positive inventory

The 101 removed hops were queried sources outside the declared Requirement
domain (part, item, behavior, and decision contexts that merely have
part/action-typed incoming dependencies — 97 hops; 2 need-typed usages; 2
member-product-typed usages). Rejections are quiet absence; the MemberProduct
lineage exclusion stays load-bearing.

### 7.3 `hasRelevantEvidenceContract` — classification and the corrected outcome

Every distinct pre-c5 source (90) was classified and every pre-c5 hop (140)
is accounted for exactly once (full accounting in Section 7.5):

- **16 evidence-contract candidates** — typed by per-slice evidence-contract
  requirement definitions that carry **no** specialization lineage (none is
  in the Requirement lineage) and **no** kernel binding;
- **14 acceptance-criterion usages** — 7 middleware typed by the definition
  the ontology binds as `AcceptanceCriterion`
  (`MiddlewareAcceptanceCriterion`), 7 visualization typed
  `VisualizationAcceptanceCriterion` (co-specializing the same
  requirement-candidate parent); all natively verified;
- **60 further sources** that evidence no verification association
  (assurance claims, assurance arguments, counterclaims, plain requirement
  usages) or ground outside the Requirement domain (four need usages).

Post-enforcement the executed c5 returned 34 hops over **29** distinct sources
(18 hops over 15 sources lacking machine identity; 16 acceptance-criterion-role
hops over 14 sources). **That result is rejected by the independent review**: it
is not semantic parity but a measured wrong/broader population, and none of
its returned sources is a proven evidence contract. Acceptance-criterion
witnesses remain documented here as the evidence that native verification
membership is insufficient; they are **not** counted as successful
evidence-contract-range witnesses, and neither are the ambiguous candidates
(which lack exact machine identity — Section 7.5).

Corrected outcome: **0 hops over 0 sources**. The three modeled links of
`reqCommandEmergencyBraking` are not emitted as evidence-contract hops under
the corrected semantics; the `Dependency` witness objects remain raw model
facts, but they no longer qualify through this predicate.

### 7.4 Current-head delta

Between the retained candidate and HEAD, five requirement-to-need dependency
sites were converted to `DerivesFromNeed` connections
(`reqDetectForwardCollisionRisk`, `reqProvideCollisionWarning`,
`reqCommandEmergencyBraking`, `reqPedestrianTargetResponse`,
`reqBicycleTargetResponse` -> their needs). All are domain-violation
(need-query) witnesses removed before and after c5; every admitted set above
is unaffected. No new ingestion was dispatched to rebind this delta.

### 7.5 Correction re-review — the `EvidenceContract` identity question

The independent review asked the exact question: *does the current governed
SysML/API representation contain a machine-resolvable, non-heuristic
discriminator that distinguishes an `EvidenceContract` usage from every other
verified `Requirement` usage, especially `AcceptanceCriterion`?*

The re-review measured every allowed discriminator category against the
current governed representation and the retained export:

1. **Explicit specialization lineage — none.** The eight per-slice
   evidence-contract requirement definitions
   (`NominalEvidenceContractRequirement`, `BicycleEvidenceContract`,
   `DegradedInputEvidenceContract`, `NonActivationEvidenceContract`,
   `OverrideEvidenceContract`, `PartialInterventionEvidenceContract`,
   `PedestrianEvidenceContract`, `RegulatoryCriterionEvidenceContract`)
   carry no authored or implied `Subclassification` chain; nothing joins them
   to each other or to any `EvidenceContract` root. They are not in the
   `Requirement` lineage either — that lineage contains the
   acceptance-criterion definitions (through
   `EvidenceContractTraceabilityRequirementCandidate`) and none of the eight
   evidence-contract definitions.
2. **Exact application-definition/type binding — none.** No model-resident
   definition is bound as the `EvidenceContract` type; the authored ontology
   class carries only a `native` kernel note with no file/declaration
   mapping, so ingestion validates no binding for it (the revision kernel
   bindings contain no `EvidenceContract` entry, while the
   acceptance-criterion side IS kernel-bound).
3. **Governed kernel binding — none**, as above.
4. **Native semantic relationship whose meaning uniquely establishes the
   role — none.** `RequirementVerificationMembership` is a verification
   association, not a class identity, and it admits both the
   acceptance-criterion role and any other natively verified requirement
   usage. The rejected c5 text treated this membership as the ontology
   kernel rule for the class; a rule that admits two distinct roles cannot
   discriminately define either.
5. **Already-reviewed identity discriminator or an exact conjunction of
   governed relationships — none available.** The reviewed discriminators at
   this revision (Requirement lineage, Need lineage, MemberProduct lineage,
   kernel-bound `AcceptanceCriterion`) do not separate the two roles; the
   only "separation" that matches the 16 candidates today is a negative
   bundle (verified AND not in the reviewed lineages) that is defined by the
   current population, not by meaning — a heuristic, not an identity.

**Exact blocker:** EvidenceContract-specific identity is not
machine-resolvable at the reviewed revision; native verification membership
also admits AcceptanceCriterion and therefore cannot establish the declared
EvidenceContract range.

**Verification association vs identity (the distinction that matters):** a
`RequirementVerificationMembership` records that a verification case verifies
a requirement usage; it says nothing about what kind of requirement usage
that is. The acceptance criteria are natively verified exactly like the
evidence-contract usages, so "verified requirement usage" is a superset of
both roles and cannot be the range discriminator. Class identity must come
from governed semantic evidence — lineage, definition/binding, or a
relationship whose meaning establishes the role — and none exists for
`EvidenceContract`.

**Full retained accounting (140 pre-c5 hops / 90 distinct sources):**

- 89 hops rejected by the Requirement-domain gate (43 need-queried, 46
  non-requirement-queried);
- 51 hops with a Requirement-grounded query evaluated against the range:
  - 17 hops: returned source without verification association — quiet
    absence;
  - **16 acceptance-criterion-role hops over 14 sources** — rejected: not
    `EvidenceContract`;
  - **18 hops over 15 distinct sources: natively verified, no machine
    identity** — ambiguous; fail closed (not emitted, not relabelled);
  - 0 ordinary verified Requirement hops (none in the population).
- One further ambiguous candidate (16 distinct candidates overall) appears
  only under a need-queried hop and is already rejected by the domain gate.
- Corrected emission: **0 hops over 0 sources**; acceptance-criterion-role
  hops after correction: **0**; no returned target without proven
  `EvidenceContract` identity.

Distinct returned sources (90): 16 ambiguous candidates + 14
acceptance-criterion-role + 56 unverified requirement + 4 Need. (The
previous c5 text counted 30 sources for the rejected result; the measured
value is 29 distinct returned sources — 15 ambiguous + 14
acceptance-criterion-role — with the 16th ambiguous candidate appearing only
under the need-queried hop noted above.)

## 8. False-positive inventory (summary)

| Class | Count | Correction |
|---|---|---|
| `realizedBy`: realization readings of allocation witnesses | 0 real; any reading is wrong | rename/replacement recorded; no promotion |
| `specifiesFunction`: specification readings | 16 hops are relevance facts; 0 specification facts | bounded relevance claim; rename recorded |
| `hasRelevantArchitecture`: non-Requirement queried sources | 101 | domain enforcement fail-closed |
| `hasRelevantEvidenceContract`: non-Requirement queried sources | 89 | domain enforcement fail-closed (unchanged by the correction) |
| `hasRelevantEvidenceContract`: unverified sources (claims/arguments/counterclaims/plain traces) | 17 hops (Requirement-queried) / 56 sources overall | verification association absent; quiet absence |
| `hasRelevantEvidenceContract`: acceptance-criterion role admitted by native verification association | 16 hops / 14 sources | rejected: not `EvidenceContract`; acceptance-criterion-role hops after correction **0** |
| `hasRelevantEvidenceContract`: natively verified sources with no machine `EvidenceContract` identity | 18 hops / 15 sources (16 candidates overall) | rejected: fail closed as quiet absence; never relabelled as evidence contracts |
| `hasRelevantEvidenceContract`: parity claim on the broader verified population | rejected by the independent review | a measured wrong/broader population is not semantic parity; the row is governed blocked/deferred |
| any: same-name / qualifiedName / package-path / source-text heuristics | 0 | no such mechanism exists or was added |

## 9. Consumer inventory

| Consumer | Engineering question it answers | c5 impact |
|---|---|---|
| `SemanticTraversal` (all four predicates) | execute only configured, reviewed mappings | domain enforcement; the `EvidenceContract` range gate fails closed (0 emitted); candidate-first quiet absence |
| `ImpactService.impact` | "If requirement R changes, which architecture, function, and evidence may be affected?" | no evidence edges/nodes while the range is blocked; the evidence gap names the blocked range — see note |
| `SemanticQueryService.semantic_neighbors` | "what is semantically adjacent to this element?" | narrowed per routed predicates |
| `SemanticQueryService.trace` | "is there a modeled path R -> target?" | same narrowed edges |
| `SemanticQueryService.verification_coverage` | "which evidence contracts / cases cover R?" | consumes the blocked `hasRelevantEvidenceContract` (no evidence contracts claimed while blocked) + `verifiedBy` |
| MCP (`semantic_neighbors`, `impact`, `trace`, `verification_coverage`) | thin adapter over the service | unchanged surface; narrowed results |
| Viewer ask-model tooling (`tools/sysml_html_viewer/ask_model_semantic.py`) | browse-time method context: incoming dependencies, realized allocations | reads the raw mapping configuration + raw elements, not the traversal; its derivation label stays at the raw "Dependency edges" / "AllocationUsage edges" level (documented, not a traversal witness) |
| `scripts/validate_full_model_semantic_queries.py` | retained-run assertion about the braking requirement's modeled links | updated: asserts that **no** evidence-contract hop is claimed while the range is blocked (the previous three-link requirement asserted the rejected semantics) |
| `scripts/query_model_impact.py` | human rendering of impact output | unchanged |
| Full-inventory tests + batch tests | governance locks | extended by this batch |

Label note: no traversal witness is labeled with a semantic class stronger
than identity grounding proves. While the `EvidenceContract` range is
blocked, no evidence-category node claims evidence-contract identity; the
only "evidence" surface is the impact gap that names the blocked range.

## 10. Identity/lineage rules (enforced)

- **DE4SDV Requirement** = validated `RequirementCandidate` lineage
  (25 members incl. the middleware requirement definitions, acceptance
  criterion, claim/argument bases). Query sources must ground in it;
  `StakeholderNeedCandidate` usages are a **sibling lineage** (both serialize
  as `RequirementUsage`) and are quiet absence. Enforced for all four
  predicates.
- **EvidenceContract identity — blocked (c5 correction).** No
  machine-resolvable discriminator exists at the reviewed revision (Section
  7.5): the per-slice evidence-contract definitions carry no specialization
  lineage, no kernel binding grounds an `EvidenceContract` root, and native
  verification membership admits the acceptance-criterion role as well. The
  range gate therefore fails closed and emits nothing. Native verification
  membership (`RequirementVerificationMembership` anchor, directly or
  through the serialized ReferenceSubsetting shadow bridge) resolves as
  **supporting evidence only**. Missing membership configuration fails
  closed.
- **MemberProduct** = validated `ProductLineMemberProduct` lineage
  (definitions and usages typed by them), exclusion enforced on incoming
  architecture sources.
- **AcceptanceCriterion** = validated `MiddlewareAcceptanceCriterion` root;
  the visualization acceptance criteria are not specialized to it.
- All fail-closed behaviors: candidate-first quiet absence outside the
  domain; `IdentityNotFoundError` on missing validated binding when
  candidates exist; `ValueError` when a mapping declares no domain; no
  name/qualifiedName/package/source-text fallback anywhere.

## 11. Overlap/disjointness matrix

| Pair | Shared witnesses | Disposition |
|---|---|---|
| `specifiesFunction` vs `hasRelevantArchitecture` | 0 | disjoint by construction: opposite directions; a requirement-sourced outgoing edge is never an incoming architecture edge. Not redundant: different projections (F addresses R vs A relevant to R). |
| `specifiesFunction` vs `hasRelevantEvidenceContract` | 0 | different directions and source/target types. |
| `hasRelevantArchitecture` vs `hasRelevantEvidenceContract` | 0 | source `@type` classes are mutually exclusive (part/action vs requirement-like). |
| `realizedBy` vs the relevance family | 0 | different relationship objects (`AllocationUsage` vs `Dependency`) and strengths. |
| same element in two queries | allowed and role-preserving | e.g. an action may be both a `specifiesFunction` target and an `hasRelevantArchitecture` source through **distinct** dependency objects; `ImpactService` keeps both roles on one node. |

A single model witness supports more than one query only where the resulting
propositions are semantically compatible (relevance + relevance through
distinct authored edges) and explicitly reviewed here; no generic
relationship produces two incompatible DE4SDV claims.

## 12. Exact-fit decisions

- `realizedBy`: **not exact native fit as named — Outcome D**. The witness is
  a bounded requirement-allocation trace; allocation is not realization;
  every real requirement-sourced allocation is Requirement -> Function;
  the name overclaims; rename/replacement required; no replacement invented;
  composite realization not implemented.
- `specifiesFunction`: **not exact native fit as named — Outcome D**. The
  provable proposition is relevance; the name reads as specification;
  rename/replacement required; relevance semantics retained unchanged.
- `hasRelevantArchitecture`: **not exact native fit — Outcome B**. Native
  Dependency witness plus load-bearing DE4SDV restrictions (Requirement
  domain, part/action constituent filter, MemberProduct exclusion); retained
  with the exact bounded claim.
- `hasRelevantEvidenceContract`: **not exact native fit — Outcome B,
  blocked/deferred.** The declared range cannot be enforced at the reviewed
  revision: no governed semantic evidence establishes `EvidenceContract`
  identity, and native verification membership (supporting evidence only)
  also admits the acceptance-criterion role. The predicate emits nothing;
  ambiguous verified requirement usages fail closed as quiet absence and are
  never relabelled as evidence contracts.

## 13. Chosen dispositions

| Identity | Disposition | Evidence state | Target | Note |
|---|---|---|---|---|
| `realizedBy` | `rename-required` (schema extension — see below) | `parity-reviewed` | `model-authoritative` | fact retained; identity rename/replacement recorded |
| `specifiesFunction` | `rename-required` | `parity-reviewed` | `de4sdv-application-semantic` | relevance retained; rename recorded |
| `hasRelevantArchitecture` | `prove-existing-model-authority` | `parity-reviewed` | `de4sdv-application-semantic` | retained with enforcement |
| `hasRelevantEvidenceContract` | `defer` | `blocked` | `de4sdv-application-semantic` | range blocked on the missing identity discriminator; gate emits nothing |

Schema decision: the reviewed outcome "rename/replacement required" had no
representable disposition value, so c5 extends the disposition vocabulary
with **`rename-required`** (documented in
`de4sdv/semantic/authority_inventory.py`), deliberately distinct from
`defer` (target undetermined pending a gate) and from
`retire-without-replacement` (no target meaning): a rename-required entry
keeps a location target and a decided evidence state, and its underlying
facts stay model-resident. Neither `retired` nor `unknown` semantics apply.
The blocked `hasRelevantEvidenceContract` row keeps its decided location
target (`de4sdv-application-semantic`) and its transition gate; `blocked`
states that the range cannot currently be enforced, not that any meaning
was retired.

## 14. Unresolved evidence and forward obligations

Carried in `required_evidence` only (completed c5 work is not listed):

1. `realizedBy`: reviewed identity rename/replacement decision (name,
   signature, and serialized end-resolution mechanics) before any O2
   projection row; then O2, then O3.
2. `specifiesFunction`: reviewed identity rename to the relevance-exact
   proposition (no strengthening); then O2, then O3.
3. `hasRelevantArchitecture`: O2, then O3.
4. `hasRelevantEvidenceContract`: reviewed EvidenceContract-specific
   identity/lineage contract — a machine-resolvable, revision-bound,
   fail-closed discriminator separating the evidence-contract role from the
   acceptance-criterion role and every other verified requirement usage —
   then O2, then O3. Until that contract exists, the range stays blocked and
   emits nothing.

The c5 questions themselves are decided: three identities are
parity-reviewed with retained-run evidence and forward migration stages;
`hasRelevantEvidenceContract` is decided **blocked/deferred** because the
declared range cannot be enforced at the reviewed revision. The open item is
the discriminator design (recorded in the row's `unknowns`), not missing c5
evidence; no identity is silently left in limbo and none is retired.

## 15. Explicit non-claims

- No realization, satisfaction, compliance, or certification claim follows
  from any allocation, dependency, or verification witness in this review.
- **No evidence contract is claimed anywhere in this batch.** While the
  `EvidenceContract` range is blocked, no returned target is presented as an
  evidence contract: the three modeled links of
  `reqCommandEmergencyBraking` are not evidence-contract hops, and the
  acceptance-criterion-role usages are not evidence-contract witnesses.
- No composite realization query exists; `realizedBy` is not equal to
  `allocatedTo` or `deployedTo`.
- No authority transition (all four rows stay `legacy-yaml` during O1); no
  Semantic Projection row; no YAML retirement; no `.sysml` change; no model,
  ontology, or PLE/T/E work. **No `.sysml` file changed.**
- The correction introduces no new ontology YAML semantics: the
  `hasRelevantEvidenceContract` row's disposition/metadata changed
  (blocked/defer), its declared domain/range and mapping configuration did
  not.
- The c4 retirement remains intact (`derivesNeedFromConcern` stays retired
  without replacement, unchanged); `addressesConcern` remains unchanged.
- The retained artifact is supporting evidence, not current-head privileged
  closure; c5 makes no `exact-toolchain-validated` or
  `privileged-closure-proven` claim; no new privileged full-model ingestion
  was dispatched for this correction.

## 16. Machine locks

`tests/test_o1_c5_relevance_realization.py` locks: the four-identity scope and
the executed c5 stage; the global parity-reviewed set (c1 + c2 + c3 + c4 +
three c5 rows = 14; the corrected `hasRelevantEvidenceContract` row is
governed `blocked`/`defer` with non-empty `unknowns` and the exact blocker
statement); the row fields, dispositions, and forward-only required
evidence; the retained-run replay numbers (143 -> 42; 140 -> 34 rejected
-> 0 corrected; the 89 / 51 / 17 / 16 / 18 / 0 classification accounting;
18 / 15 and 16 / 14 hop/source splits, 16 candidates overall, 29 distinct
sources in the rejected result); the fail-closed runtime laws (domain enforcement,
the EvidenceContract range gate emitting nothing — including the verified
acceptance-criterion and ordinary-verified-requirement negative fixtures
with verification support demonstrably present — candidate-first quiet
absence, missing-binding errors, no-name fallback probes, MemberProduct
exclusion, disjointness); the `rename-required` schema laws; c1–c4/K/PLE
states unchanged; and the artifact-vs-source consistency gate (red between
Commit A and Commit B by design — the two-commit binding gate working). No
privileged ingestion was dispatched for c5.
