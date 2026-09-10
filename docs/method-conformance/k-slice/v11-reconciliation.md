# K slice — v1.1 semantic reconciliation (post-`ee19627`)

Status: bounded reconciliation per `DE4SDV_Unified_Semantic_Engineering_Plan_v1.1.md`
(§5 "Normative `SemanticMetadata` restriction", §5 "Requirement-derivation
preference", UG-29, UG-30). Baseline: `ee19627` (R1–R5 repair accepted). No
traversal/projection/test infrastructure is discarded; only the marker
representation and its authority story change.

## 1. Is `RequirementDerivation :> SemanticMetadata` on a `Dependency` normatively valid?

**No — under plan v1.1's normative restriction, and in substance under
SysML v2 §7.27.3 "Semantic Metadata".**

Spec basis (Systems Modeling Language v2.0, Part 1 — the extracted spec text
at `~/.hermes/knowledge/public-sources/sysml-v2-release/extracted/`, the same
basis used for §9.6 inspection):

- §7.27.3: "If the metadata definition of a metadata usage is a direct or
  indirect specialization of KerML metaclass **SemanticMetadata** … then the
  annotated elements of the metadata usage **must all be types** (e.g.,
  definitions or usages), and the inherited feature
  **SemanticMetadata::baseType** must be bound to a value of type
  KerML::Type". Each annotated element is then considered to **implicitly
  specialize (definition) / subset (usage) a definition or usage determined
  from the baseType value**.
- A `Dependency` is a **Relationship** (§8.3.3, Figure 3: `Dependency`
  specializes `Relationship`, `client {redefines source}`, `supplier
  {redefines target}`) — not a Type/definition/usage. Annotating it with a
  `SemanticMetadata` specialization violates the "must all be types"
  constraint, and no meaningful `baseType` binding exists: there is no
  library definition of "derivation dependency" for a Dependency to
  implicitly specialize, so the required semantic effect (implicit
  specialization/subclassification/subsetting) is undefined.
- Corroboration from the standard's own Domain Libraries: where the spec
  applies semantic metadata to connections, it does so to the connection's
  **Definition/Usage types** — §9.5.3.2.1 `CausationMetadata` features
  `annotatedElement1 : ConnectionDefinition`, `annotatedElement2 :
  ConnectionUsage`; §9.6.3.2.1 `DerivationMetadata` features
  `annotatedElement1 : ConnectionDefinition`, `annotatedElement2 :
  ConnectionUsage`. No standard pattern annotates a bare `Dependency`
  (Relationship) instance with SemanticMetadata.
- The licensed SysIDE acceptance of the current form is tool acceptance, not
  normative evidence (plan v1.1 UG-29: "do not treat validator acceptance
  alone as proof of normative semantics").

Conclusion: the `:> SemanticMetadata` specialization is removed. Per
instruction, it is **not** replaced with another semantic-metadata
workaround.

## 2. Does standard SysML `Derivation` (Requirement Derivation Domain Library, §9.6) fit DE4SDV Need → Requirement?

**Yes — semantically compatible.** Inspection of §9.6.2.2.1 (`Derivation`,
ConnectionDefinition):

- "A Derivation connection asserts that one or more derivedRequirements are
  **derived from** a single originalRequirement." — exactly the DE4SDV claim
  "a design-input Requirement is derived/transformed from a stakeholder
  Need", read with the Need in the `originalRequirement` role.
- "A ConnectionUsage typed by Derivation must have **RequirementUsages for
  all its ends**." — DE4SDV's Need *is* a `RequirementUsage`: the kernel
  defines `StakeholderNeedCandidate :> RequirementsManagementAttributeBase`
  as a `requirement def` (kernel
  `de4sdv_method_context.sysml`), i.e. a SysML requirement definition whose
  usages are RequirementUsages typed (via FeatureTyping) by that definition.
  The endpoint metaclasses fit because DE4SDV models needs as requirements —
  this is now understood as a **sufficient** alignment, not a coincidence.
- `originalRequirement : RequirementCheck {subsets participant}` — the Need
  is the original/design-input origin.
- `derivedRequirements : RequirementCheck [1..*] {subsets participant}` — the
  derived design-input requirements.
- **Satisfaction/implication semantics** (`originalImpliesDerived`:
  "Whenever the originalRequirement is satisfied, all of the
  derivedRequirements must also be satisfied"): meaningful and **stronger
  than, but consistent with**, the DE4SDV derivation claim. Deriving a design
  requirement from a stakeholder need does intend that satisfying the need
  (through its derived requirements) carries forward; the DE4SDV claim
  boundary (no satisfaction/allocation/verification/evidence/acceptance
  claims) is about what DE4SDV asserts, not a rejection of the library's
  built-in implication constraint. The constraint is evaluated only if/when
  requirement checking is exercised; DE4SDV K does not execute it and does
  not rely on it.
- **Participant constraints** (`originalNotDerived`: the original must not be
  a derived requirement): acceptable — a stakeholder Need is not itself a
  derived design requirement, so the exclusion matches DE4SDV's intent
  (Need ≠ Requirement per the INCOSE NRM distinction, which stays reference
  material only).

**Direction mapping:** native witness direction is
`originalRequirement → derivedRequirements` (Need → Requirement). DE4SDV's
canonical query `derivesRequirementFromNeed` (Requirement → Need) becomes
**inverse navigation over the same native witness** (plan v1.1 §5: "DE4SDV's
canonical query `Requirement → Need` is then inverse navigation over that
same native witness"; §9: "Preserve standard-library role identities when
they carry domain meaning (for example `originalRequirement` versus
`derivedRequirements`)").

**Adoption gate:** the library is pinned in `sysand-lock.toml` (2.0.0, exports
`DerivationConnections`, `RequirementDerivation`) but not yet materialized
into `.sysand/lib/`. Per plan §5/§16 the K exit requires an
imported-AND-consumed library with exact-toolchain evidence; the adoption
decision (first materialization + import via `sysand sync` at an exact head)
is part of the K implementation this reconciliation proposes, and remains
subject to the maintainer's review gate — no upstream contact, no floating
upgrade.

## 3. Selected representation

**Standard-library reuse (smallest native form):**

- `private import DerivationConnections::*;` (exact-pinned Requirement
  Derivation Domain Library) in the kernel package.
- The five confirmed AEBS derivation edges change from
  `#RequirementDerivation dependency X from req to need;` to native
  **`connection derivation <name>: Derivation connects <need> to <req>;`**
  form: the **Need is the `originalRequirement` end**, the **Requirement is
  the `derivedRequirements` end** — i.e. native direction Need → Requirement,
  with DE4SDV's Requirement → Need as inverse navigation.
- The `metadata def RequirementDerivation :> SemanticMetadata` and its
  `#` applications are **removed entirely** (no ordinary-metadata
  discriminator is introduced; the native typed connection is itself the
  discriminator — a `ConnectionUsage` typed by the library `Derivation`
  definition, distinguishable from a generic `Dependency` by metaclass and
  typing witness, never by name).
- No parallel canonical relation is introduced (UG-30): the standard library
  relation IS the canonical relation; DE4SDV `derivesRequirementFromNeed` /
  `derivedRequirementsOfNeed` remain the query identities over it.

## 4. Where authoritative meaning resides after the repair

For this predicate (K exit per plan v1.1 §16 K row: "domain/range/direction/
strength must no longer be authored only in YAML"):

- **Identity & meaning:** the standard library definitions
  `DerivationConnections::Derivation` (identity/meaning of the derivation
  connection) — grounded in the pinned library artifact, plus the kernel
  `derivesRequirementFromNeed`-role binding documented model-resident.
- **Domain/range/direction:** the library's
  `originalRequirement`/`derivedRequirements` role features (Need =
  originalRequirement end, Requirement = derivedRequirements end) plus the
  kernel's DE4SDV role binding (stakeholder need vs design-input obligation,
  per the kernel `StakeholderNeedCandidate` / `RequirementCandidate`
  definitions).
- **Semantic strength / claim boundary:** the kernel's model-resident doc
  contract on the role binding (design-input derivation only; no
  satisfaction/verification/evidence claims — the library's
  `originalImpliesDerived` constraint is library semantics, not a DE4SDV
  claim).
- **YAML** remains the O0/O1 parity oracle: it keeps its mapping rows, and
  projection generation cross-checks model authority vs YAML (UG-20/26), but
  the projection's `support_state`/meaning fields are generated from
  model/library authority with the YAML row as parity input, not as the sole
  authority.

## 5. What changed from `ee19627`

Model:
- Kernel: `metadata def RequirementDerivation` and the
  `Metaobjects::SemanticMetadata` import removed; `DerivationConnections`
  import added; role-binding contract documented model-resident.
- AEBS: five `#RequirementDerivation dependency` edges → five native
  `Derivation` connection usages (Need = originalRequirement, Requirement =
  derivedRequirements).
- Ontology YAML: `RequirementDerivation` class entry retired; the two
  predicate mappings now declare `strategy: derivation-connection` with
  `native_library: DerivationConnections::Derivation` and role names; old
  marker mapping rows removed (semantic migration recorded, UG-04-style).

Runtime:
- Traversal: `metadata-tagged-dependency` strategy replaced by
  `derivation-connection` — discriminator = ConnectionUsage typed by the
  validated library `Derivation` definition UUID (kernel-bound), with
  end-role extraction via the connection's ends; R1 lineage checks, R2
  witness closure, fail-closed behavior, and R4 same-witness inverse
  navigation preserved (roles swapped).
- Projection/profile: meaning fields generated from the model/library
  authority (native grounding = `DerivationConnections::Derivation` + roles,
  explicit vs implied provenance flagged per plan §8.1); YAML kept as parity
  oracle; `assert_profile_compatible` gate retained.
- Proof CLI: same assertions (exact endpoints/witness, no gaps, inverse per
  case) against the new witness shape.

Docs/tests: representation decision rewritten (this file); tests updated to
`Derivation` ConnectionUsage shapes; `test_prove_derivation_slice.py`
fault-injection retained.

## 6. Exact head and suite result

- Head: `ee19627` → reconciliation commit (see git log; SHA recorded in the
  PR body update). Full suite at the new head: recorded in the commit/PR
  evidence block (1075+ tests, 0 failures expected; exact count pinned at
  commit time).

## 7. R6 justification

**Yes — after this reconciliation, exactly one exact-head privileged
ingestion is justified and necessary** for K evidence: it must (a) materialize
the pinned Requirement Derivation Library via `sysand sync` at the exact
head, (b) validate/export the native `Derivation` connections, (c) prove
import/read-back closure of the connection + ends + typing witnesses (C1),
and (d) feed the live `prove_derivation_slice.py` run. Not executed yet —
explicit authorization required (plan §18 stop conditions; instruction "do
not run R6 yet").
