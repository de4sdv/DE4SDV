# O2.3 design — semantic projection v1.2 extension (K pair + architecture relevance)

Date: 2026-09-15 · Plan: DE4SDV Unified Semantic Engineering Plan v1.2 (wins on
conflict) + DE4SDV Method Conformance Plan · Base: `main` after O2.2 completion
= `b948c7fb6983f0d3b9a71063cdf787fcc7b36f3a`.

## Scope

**Final bounded O2 generation stage**: exactly the three remaining reviewed
identities:

- `derivesRequirementFromNeed` (`Requirement -> Need`, semantic strength
  `derivation`),
- `derivedRequirementsOfNeed` (`Need -> Requirement`, semantic strength
  `derivation`),
- `hasRelevantArchitecture` (`Requirement -> ArchitectureElement`, semantic
  strength `relevance`).

After O2.3 the cumulative O2 projection surface is exactly thirteen
identities: O2.1 seven (in the immutable `semantic-projection-v1.json`
baseline) + O2.2 three (in the immutable `semantic-projection-v1.1.json`
baseline) + O2.3 three (this extension). No fourteenth identity. Nothing
else is admitted; the guarded set (MethodEvaluationScope, DerivesFromNeed
class, derivesNeedFromConcern, realizedBy, specifiesFunction,
hasRelevantEvidenceContract, EvidenceContract, ArchitectureElement class
row, Function, LogicalElement, PhysicalElement, Interface, allocatedTo,
deployedTo, and the full published baseline sets) is machine-locked as
never-emitted.

## Delivery

**Stage A (this PR)**: additive implementation foundation —
`de4sdv/semantic/projection_o23.py`, `scripts/generate_semantic_projection_o23.py`,
`docs/method-conformance/o2/o23-admission.yaml`, this design record, and
`tests/test_semantic_projection_o23.py`; plus the minimum deliberate
allowlist updates in three existing guard scans that enumerate build-time
semantic modules (documented in each test). No canonical v1.2 artifacts, no
`check_repo.py` registration.

**Stage B (after Stage-A squash-merge)**: the permanent resulting `main`
commit becomes the O2.3 `source_revision`; `semantic-projection-v1.2.json`
and `api-representation-profile-v1.2.json` are generated bound to that
revision, committed, and the v1.2 `--check` gate is registered in
`scripts/check_repo.py` together with the committed-artifact tests. Topology:
Stage A squash → X = permanent `main`; Stage B artifacts bind to X; Stage B
squash → Y with X still an ancestor of Y. A feature-branch commit can never
serve as durable `source_revision` in a squash-only repository.

## Baseline-extension architecture

- `semantic-projection-v1.2` extends `semantic-projection-v1.1`
  (schema `de4sdv.semantic-projection.v1.1`).
- `api-representation-profile-v1.2` independently extends
  `api-representation-profile-v1.1` (schema
  `de4sdv.api-representation-profile.v1.1`).
- Each pin records and verifies artifact path, schema, source revision, and
  artifact digest; both v1.1 baselines are bound inputs; a missing,
  wrong-schema, revision-less, digest-drifted, or non-ancestor baseline fails
  closed, as does a projection/profile baseline swap (the generator builds
  the two pins independently and the gate validates each against its own
  expected path/schema). The two baseline source revisions are verified
  independently, never assumed equal.

## K pair — one modeled fact, two navigations

The final K decision (`docs/method-conformance/k-slice/v11-final-decision.md`)
is preserved exactly:

- **One witness**: the DE4SDV application connection definition
  `connection def DerivesFromNeed` (kernel-mapped, file-anchored in
  `de4sdv_method_context.sysml`) with typed ends `need :
  StakeholderNeedCandidate` and `derivedRequirement : RequirementCandidate`.
  The governed model carries exactly five authored
  `connection … : DerivesFromNeed connect <need> to <req>;` usages; the
  population is a reviewed lock (5): disappearance, addition, or foreign
  typing fails generation.
- **Two navigations**: native modeled direction is `Need -> Requirement`
  (authored end order). `derivesRequirementFromNeed` (Requirement → Need) is
  inverse traversal over that witness; `derivedRequirementsOfNeed` is the
  forward traversal over the SAME witness. Both rows are emitted from ONE
  model-derived semantic core (`derive_k_semantics`) — the companion row is
  computed from the canonical row by the pair contract, never derived from
  the model a second time, so independent drift is structurally impossible.
  Emitted-row invariants are re-asserted (inverse domain/range, opposite
  canonical directions, identical strength/claim boundary/grounding), and
  the iff-equivalence `derivesRequirementFromNeed(R, N) iff
  derivedRequirementsOfNeed(N, R)` is locked at contract level.
- **Role identity is keyed by typing**: each end's TYPE resolves to the
  governed Need/Requirement lineage class through the contract's kernel
  mappings. End order, connection argument order, query direction,
  declaredName, qualifiedName, package path, and source text never establish
  role identity (machine-locked, including the end-order-swap trap: a swap
  changes only the recorded native direction, never role meaning).
- **Claim**: design-input provenance only ("the design-input Requirement
  originates from the stakeholder Need"). No logical implication, need or
  requirement satisfaction, allocation, realization, verification, evidence,
  acceptance, approval, or certification. The standard Requirement Derivation
  Domain Library `Derivation` is deliberately NOT adopted
  (`originalImpliesDerived` is stronger and semantically wrong for this
  claim) and is never silently substituted (machine-locked).
- **K semantic authority comes from the model**: the definition's typed ends
  carry domain/range; the ingested definition documentation carries the
  provenance meaning and the claim boundary, located by the reviewed v0
  probes (`model_authority.CLAIM_STRENGTH`, `PREDICATE_SHAPE` reused
  read-only). Missing or conflicting claim-strength statements fail closed.
- **YAML is parity oracle only**: both K rows are pair-parity-checked
  against the model-derived semantics through the reviewed v0 parity gate
  (`_assert_oracle_parity`); any drift in either row fails generation naming
  the exact field. YAML is never promoted back into semantic authority.

## hasRelevantArchitecture — reviewed application semantic

Exact declared direction `Requirement -> ArchitectureElement`; exact
proposition "a native architecture-side part/action element is relevant to
Requirement R through an authored incoming Dependency"; strength
`relevance`. This is NOT native `ArchitectureElement` semantics:

- **Umbrella identity**: the reviewed model has no single file/declaration
  kernel binding for `ArchitectureElement`; none is fabricated, and API
  metaclass equality is never upgraded into semantic identity proof. The
  range meaning is carried by the exact reviewed application contract
  (serialized in the row: architecture-side part/action representation AND
  not MemberProduct lineage AND authored incoming relevance dependency AND a
  query source machine-proven in the governed Requirement lineage).
- **Load-bearing restrictions** (serialized as scope restrictions, each with
  its meaning): governed Requirement domain (Need-sourced and other
  non-Requirement queries are quiet absence; Requirement identity proven
  through the validated kernel-binding/lineage mechanism, never from the
  `RequirementUsage` metaclass); source types PartUsage/PartDefinition/
  ActionUsage/ActionDefinition (the representation-level carrier of the
  umbrella); MemberProduct-lineage exclusion (product-line relationships are
  not architecture relevance; proven by lineage, not name); incoming
  Dependency witness with architecture-side source and requirement target.
- **Representation direction**: the authored witness is incoming
  (architecture-side source → requirement target); the canonical
  `Requirement -> ArchitectureElement` query reads that witness without
  reversing the semantic claim.
- **Negative laws**: relevance only — no satisfaction, realization,
  allocation, verification, specification, product-line selection,
  configuration membership, deployment, or physical realization; not
  realizedBy/specifiesFunction/allocatedTo/deployedTo/appliesToMemberProduct;
  the canonical RFLP chain is not collapsed; a direct relevance edge is
  navigation/traceability only.

## Projection/profile separation

Same discipline as corrected O2.2, machine-checked:

- **Projection rows** carry identity, semantic kind, domain, range (with the
  governed lineage anchors), canonical direction, native modeled direction
  (K rows), semantic strength, load-bearing scope restrictions, native
  grounding identity at the abstract semantic level, model witness anchors,
  and support_state. A committed mechanics-leak scan proves no serializer
  vocabulary (`strategy`, `membership_types`, `query_direction`, roles,
  property paths, `direction`, `relationship_types`, `source_types`,
  metaclass/ReferenceSubsetting/implied mechanics) appears in the rows.
- **Profile entries** carry ALL representation mechanics: the
  derivation-connection configuration (connection definition, roles, query
  direction, lineage sides), the dependency configuration (relationship
  types, incoming direction, source/target properties, source types,
  exclusion root), resolution rules, witness forms, and
  `runtime_mapping_state = existing-not-authority`. The compatibility gate
  (`assert_profile_compatible_o23`) holds each entry's
  `semantic_contract_echo` equal to the projection's semantic contract —
  mechanics can never redefine domain, range, canonical direction, semantic
  strength, scope restrictions, or claim boundaries.

## Schema-level claim boundaries

Negative laws live in the projection-level
`projection_contract.identity_claim_boundaries` block as schema-level
reviewed contract metadata (transcribed from the final K decision, the
merged O1 c5 review, and the governing plans; machine-locked against the
module's reviewed negative-witness registry), never as per-row
engineering-semantic fields. The four-way separation is preserved:
model-derived semantic core vs reviewed projection-schema claim-boundary
metadata vs representation-profile mechanics vs admission/provenance
metadata. O1 governance files are never read at generation (decoy-O1 and
O1-less fixture tests prove it).

## v0 reuse discipline

The v0 K implementation (`projection.py`, `model_authority.py`) is an
existing reviewed implementation/evidence source, NOT a second authority:

- Reused read-only: the `CLAIM_STRENGTH` and `PREDICATE_SHAPE` locator
  probes and the `_assert_oracle_parity` pair gate (imported, with errors
  translated into this stage's error type). No v0 file is modified.
- The O2.3 K semantics are derived from the governed model representation
  (definition anchor, typed ends, documentation) — v0 output is not the
  semantic source; parity between the O2.3 K rows and the established v0
  semantics is machine-tested (the v0-compatible semantics dict is verified
  against the model truth and the v0 parity gate must pass).
- The O2.2 structural anchor locators (`_locate_required_declaration`,
  `_contract_class_anchor`) are reused read-only with error translation.

## Support state and API binding

`support_state = vocabulary-only` for all three rows. The K slice's
historical structured closure (retained privileged run at its own earlier
revision) does NOT promote current support: promotion remains exact-revision
and attestation-bound, no promotion input exists anywhere in the module, and
the runtime-mapping fact is recorded only as non-support profile metadata
(`runtime_mapping_state = existing-not-authority`). `api_binding.status =
unclaimed` for the v1.2 family; retained privileged runs (including
`10195168006`) remain representation-shape evidence only. No privileged
ingestion was dispatched for Stage A.

## Bound inputs (14)

Program: `projection_o23.py`, `projection_o22.py` (anchor locators),
`projection_v1.py` (frozen locks), `authority_inventory.py`,
`kernel_contract.py`, `model_authority.py` (K probes),
`generate_semantic_projection_o23.py`. Data: `o23-admission.yaml`, ontology
YAML, both v1.1 baseline artifacts, `de4sdv_method_context.sysml` (Need,
Requirement, DerivesFromNeed anchors), `de4sdv_product_line.sysml`
(MemberProduct anchor), `aebs_needs_requirements.sysml` (K usage
witnesses).

## Runtime boundary

Generation, not authority activation: no runtime semantic authority switch,
no production traversal routing through v1.2, no YAML retirement, no
evaluator/`phase_contract()`/`increment_status()`/`method_gaps()`/
`next_obligation()` change, no `.sysml` change (the K connection and
architecture-relevance witnesses already exist), no O3/O4 work. The runtime
does not read these artifacts (machine-locked).

## Verification (Stage A)

79 O2.3 tests: positive scope against the real production model (including
the five-usage witness population and the full K semantics dict); pair
invariants; admission locks; negative scope; K adversarial set (missing
definition, ambiguous definition, wrong/missing end typing, single-lineage
ends, missing/conflicting claim-strength doc, missing/extra/foreign-typed
witnesses, generic-Dependency decoys, oracle drift in both directions,
contract drift, library-substitution lock, extra vocabulary, decoy/absent O1
data); architecture adversarial set (exclusion/direction/source-type/
relationship-type drift, umbrella non-fabrication, RFLP non-collapse,
name/metaclass prohibition); separation scans; support-state locks; O2.1/
O2.2/v0 preservation; runtime independence. All four existing gates
(inventory, v1, v1.1, check_repo) remain green on the Stage-A checkout;
full pytest, smoke, model-sync, naming, Markdown links, `git diff --check`,
public CI, and the mandatory squash simulation are recorded in the PR.
