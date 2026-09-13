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

---

## 1. The four reviewed identities

| Identity | Declared contract (authored YAML) | Executable representation | c5 review question |
|---|---|---|---|
| `realizedBy` | `Requirement -> ArchitectureElement`; strength `allocation` | strategy `allocation`, `AllocationUsage`, outgoing | What does the `AllocationUsage` witness actually mean, and is `realizedBy` the correct canonical identity for it? |
| `specifiesFunction` | `Requirement -> Function`; strength `relevance` | strategy `dependency`, outgoing, source `RequirementUsage`, targets action-typed | Is the fact specification, or only relevance/addressal? |
| `hasRelevantArchitecture` | `Requirement -> ArchitectureElement`; strength `relevance` | strategy `dependency`, incoming, sources part/action-typed, MemberProduct lineage excluded | Is this a useful distinct cross-layer architecture relevance relation, and what exactly are its domain/range? |
| `hasRelevantEvidenceContract` | `Requirement -> EvidenceContract`; strength `relevance` | strategy `dependency`, incoming, sources `RequirementUsage` | Can the relation prove `EvidenceContract`, or does API `RequirementUsage` over-return? |

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
- `hasRelevantEvidenceContract`: **"a natively verified requirement usage
  (evidence-contract or acceptance-criterion role) is relevant to requirement
  R"** — the reviewed identity basis is the ontology kernel rule for
  `EvidenceContract` (requirement usages verified by SysML v2 verification
  cases), enforced together with the Requirement-lineage query domain; the
  narrower EvidenceContract-specific class separation is a recorded forward
  obligation (Section 14).

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
  This is the machinery the EvidenceContract identity basis reuses.
- No native SysML/KerML relationship expresses "specifies" between a
  requirement usage and an action usage; the modeled fact is an authored
  generic dependency.
- The `ArchitectureElement`, `Function`, and `EvidenceContract` ontology
  classes are native-umbrella concepts without kernel declarations of their
  own (no file/declaration binding exists for them); the executable class
  filters are representation-level carriers of those umbrellas, and the only
  governed identity restrictions available at this revision are the
  Requirement, Need, AcceptanceCriterion, and MemberProduct lineages plus the
  native verification memberships.

## 7. Real-model witness inventory (retained revision)

### 7.1 Before/after counts (hardened traversal)

| Predicate | Pre-c5 hops | Post-c5 hops | Removed | Kept sources |
|---|---|---|---|---|
| `realizedBy` | 0 (zero real serialized witnesses) | 0 | 0 | 0 |
| `specifiesFunction` | 16 | 16 | 0 | 15 requirement sources |
| `hasRelevantArchitecture` | 143 | 42 | 101 | 42 |
| `hasRelevantEvidenceContract` | 140 | 34 | 106 | 30 |

### 7.2 `hasRelevantArchitecture` — false-positive inventory

The 101 removed hops were queried sources outside the declared Requirement
domain (part, item, behavior, and decision contexts that merely have
part/action-typed incoming dependencies — 97 hops; 2 need-typed usages; 2
member-product-typed usages). Rejections are quiet absence; the MemberProduct
lineage exclusion stays load-bearing.

### 7.3 `hasRelevantEvidenceContract` — classification and rejection

Every distinct pre-c5 source (90) was classified:

- **16 AEBS evidence-contract usages** — typed by per-slice evidence-contract
  requirement definitions that carry no DE4SDV specialization lineage;
  natively verified by verification memberships;
- **14 acceptance-criterion usages** — 7 middleware typed
  `MiddlewareAcceptanceCriterion`, 7 visualization typed
  `VisualizationAcceptanceCriterion`; all natively verified;
- **60 further sources** that evidence no verification association
  (assurance claims, assurance arguments, counterclaims, plain requirement
  usages) or ground outside the Requirement domain (four need usages).

89 of the 140 hops were query-side domain violations (needs, actions, use
cases, concerns, parts, items); 17 further hops were requirement-grounded
sources with no verification association. Post-enforcement: **34 hops over 30
sources** (18 evidence-contract-role hops over 16 sources; 16
acceptance-criterion-role hops over 14 sources). **The three modeled
evidence-contract links of `reqCommandEmergencyBraking` are preserved**, as
are the middleware acceptance-criterion traces.

### 7.4 Current-head delta

Between the retained candidate and HEAD, five requirement-to-need dependency
sites were converted to `DerivesFromNeed` connections
(`reqDetectForwardCollisionRisk`, `reqProvideCollisionWarning`,
`reqCommandEmergencyBraking`, `reqPedestrianTargetResponse`,
`reqBicycleTargetResponse` -> their needs). All are domain-violation
(need-query) witnesses removed before and after c5; every admitted set above
is unaffected. No new ingestion was dispatched to rebind this delta.

## 8. False-positive inventory (summary)

| Class | Count | Correction |
|---|---|---|
| `realizedBy`: realization readings of allocation witnesses | 0 real; any reading is wrong | rename/replacement recorded; no promotion |
| `specifiesFunction`: specification readings | 16 hops are relevance facts; 0 specification facts | bounded relevance claim; rename recorded |
| `hasRelevantArchitecture`: non-Requirement queried sources | 101 | domain enforcement fail-closed |
| `hasRelevantEvidenceContract`: non-Requirement queried sources | 89 | domain enforcement fail-closed |
| `hasRelevantEvidenceContract`: unverified sources (claims/arguments/counterclaims/plain traces) | 17 | native-verification identity basis enforced |
| `hasRelevantEvidenceContract`: acceptance-criterion role under the evidence-contract name | 16 hops / 14 sources | reviewed co-satisfaction of the operative kernel rule; class separation recorded as forward obligation |
| any: same-name / qualifiedName / package-path / source-text heuristics | 0 | no such mechanism exists or was added |

## 9. Consumer inventory

| Consumer | Engineering question it answers | c5 impact |
|---|---|---|
| `SemanticTraversal` (all four predicates) | execute only configured, reviewed mappings | domain + EvidenceContract-identity enforcement; candidate-first fail-closed |
| `ImpactService.impact` | "If requirement R changes, which architecture, function, and evidence may be affected?" | narrowed hops flow through; labels "function"/"architecture"/"EvidenceContract" assessed — see note |
| `SemanticQueryService.semantic_neighbors` | "what is semantically adjacent to this element?" | narrowed per routed predicates |
| `SemanticQueryService.trace` | "is there a modeled path R -> target?" | same narrowed edges |
| `SemanticQueryService.verification_coverage` | "which evidence contracts / cases cover R?" | consumes the narrowed `hasRelevantEvidenceContract` + `verifiedBy` |
| MCP (`semantic_neighbors`, `impact`, `trace`, `verification_coverage`) | thin adapter over the service | unchanged surface; narrowed results |
| Viewer ask-model tooling (`tools/sysml_html_viewer/ask_model_semantic.py`) | browse-time method context: incoming dependencies, realized allocations | reads the raw mapping configuration + raw elements, not the traversal; its derivation label stays at the raw "Dependency edges" / "AllocationUsage edges" level (documented, not a traversal witness) |
| `scripts/validate_full_model_semantic_queries.py` | retained-run assertion that the braking requirement keeps its modeled evidence-contract links | still satisfied: all three links are natively verified |
| `scripts/query_model_impact.py` | human rendering of impact output | unchanged |
| Full-inventory tests + batch tests | governance locks | extended by this batch |

Label note: no traversal witness is labeled with a semantic class stronger
than identity grounding proves in this batch; the "EvidenceContract" impact
label remains the method-family label per the recorded co-satisfaction (the
class-separation obligation below covers the narrower reading).

## 10. Identity/lineage rules (enforced)

- **DE4SDV Requirement** = validated `RequirementCandidate` lineage
  (25 members incl. the middleware requirement definitions, acceptance
  criterion, claim/argument bases). Query sources must ground in it;
  `StakeholderNeedCandidate` usages are a **sibling lineage** (both serialize
  as `RequirementUsage`) and are quiet absence. Enforced for all four
  predicates.
- **EvidenceContract identity basis** = a natively verified requirement
  usage: a `RequirementVerificationMembership` anchor, directly or through
  the serialized ReferenceSubsetting shadow bridge; membership types and
  reference property come from the governed `verifiedBy` mapping
  configuration. Missing membership configuration fails closed.
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
- `hasRelevantEvidenceContract`: **not exact native fit — Outcome B** with
  the reviewed identity basis enforced; `RequirementUsage` alone does not
  prove `EvidenceContract`.

## 13. Chosen dispositions

| Identity | Disposition | Evidence state | Target | Note |
|---|---|---|---|---|
| `realizedBy` | `rename-required` (schema extension — see below) | `parity-reviewed` | `model-authoritative` | fact retained; identity rename/replacement recorded |
| `specifiesFunction` | `rename-required` | `parity-reviewed` | `de4sdv-application-semantic` | relevance retained; rename recorded |
| `hasRelevantArchitecture` | `prove-existing-model-authority` | `parity-reviewed` | `de4sdv-application-semantic` | retained with enforcement |
| `hasRelevantEvidenceContract` | `prove-existing-model-authority` | `parity-reviewed` | `de4sdv-application-semantic` | retained with identity basis enforced |

Schema decision: the reviewed outcome "rename/replacement required" had no
representable disposition value, so c5 extends the disposition vocabulary
with **`rename-required`** (documented in
`de4sdv/semantic/authority_inventory.py`), deliberately distinct from
`defer` (target undetermined pending a gate) and from
`retire-without-replacement` (no target meaning): a rename-required entry
keeps a location target and a decided evidence state, and its underlying
facts stay model-resident. Neither `retired` nor `unknown` semantics apply.

## 14. Unresolved evidence and forward obligations

Carried in `required_evidence` only (completed c5 work is not listed):

1. `realizedBy`: reviewed identity rename/replacement decision (name,
   signature, and serialized end-resolution mechanics) before any O2
   projection row; then O2, then O3.
2. `specifiesFunction`: reviewed identity rename to the relevance-exact
   proposition (no strengthening); then O2, then O3.
3. `hasRelevantArchitecture`: O2, then O3.
4. `hasRelevantEvidenceContract`: reviewed EvidenceContract-specific
   identity/lineage contract separating the evidence-contract role from the
   acceptance-criterion role before any narrowing of the claimed class; then
   O2, then O3.

No identity is left blocked: every c5 question is decided with retained-run
evidence; the obligations above are forward migration stages, not missing c5
evidence.

## 15. Explicit non-claims

- No realization, satisfaction, compliance, or certification claim follows
  from any allocation, dependency, or verification witness in this review.
- No composite realization query exists; `realizedBy` is not equal to
  `allocatedTo` or `deployedTo`.
- No authority transition (all four rows stay `legacy-yaml` during O1); no
  Semantic Projection row; no YAML retirement; no `.sysml` change; no model,
  ontology, or PLE/T/E work. **No `.sysml` file changed.**
- The c4 retirement remains intact (`derivesNeedFromConcern` stays retired
  without replacement, unchanged); `addressesConcern` remains unchanged.
- The retained artifact is supporting evidence, not current-head privileged
  closure; c5 makes no `exact-toolchain-validated` or
  `privileged-closure-proven` claim.

## 16. Machine locks

`tests/test_o1_c5_relevance_realization.py` locks: the four-identity scope and
the executed c5 stage; the global parity-reviewed set (c1 + c2 + c3 + c4 +
c5); the row fields, dispositions, and forward-only required evidence; the
retained-run replay numbers (143 -> 42; 140 -> 34; 16; 0; classification
counts); the fail-closed runtime laws (domain enforcement, EvidenceContract
identity basis incl. the shadow bridge, candidate-first quiet absence,
missing-binding errors, no-name fallback probes, MemberProduct exclusion,
disjointness); the `rename-required` schema laws; c1–c4/K/PLE states
unchanged; and the artifact-vs-source consistency gate (red between Commit A
and Commit B by design — the two-commit binding gate working). No privileged
ingestion was dispatched for c5.
