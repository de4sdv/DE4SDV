# K slice: representation decision for `derivesRequirementFromNeed`

Status: decision recorded from live repository + deployed-baseline evidence on
2026-09-10, before implementation. Scope: one predicate
(`derivesRequirementFromNeed`, Requirement -> Need), one real AEBS derivation
witness slice, no library adoption, no signature change.

## 1. Engineering question and claim boundary

"Requirement R is derived from stakeholder need N" (design-input derivation,
direction R -> N). Inverse navigation (N -> its derived requirements) reuses
the same witness. No satisfaction, allocation, verification, evidence, or
acceptance claim.

## 2. What inspection found (all evidence from live sources)

- The ontology declares `derivesRequirementFromNeed` (Requirement -> Need) as
  vocabulary-only: no `sysml_mapping` exists
  (`approach/framework/ontology/de4sdv-basic-ontology.yaml`, relationships
  section). R0 selected this predicate
  (`docs/method-conformance/r0-handoff/k-predicate-selection.md`, merged with
  PR #239).
- The model already expresses derivation as bare named `dependency ... from
  reqX to needY` edges (17 in
  `aebs_needs_requirements.sysml` System 1 block; 41 `DerivedFrom`-named
  Dependency objects baseline-wide) plus free-text `attribute :>> source =
  "Derived from N-AEBS-001"`. None of this is a semantic discriminator.
- The deployed validated baseline (Git 90b4d5d1, project
  1e33ed46-..., commit 81b948af-..., 59123 elements) contains **96 Dependency
  objects whose endpoints are both RequirementUsage**. Only ~40 of those are
  derivations; the rest are relevance/trace/counter-claim edges (e.g.
  `bicycleCriterionRelevantToBicycleResponseCandidate`,
  `needFramingTrace`, `overrideClearRelevantToBrakingCandidate`). Endpoint
  types alone cannot discriminate (UG-05); C3 forbids name-based matching.
  Today's offline checker (R003/SP6) is source-text static analysis, not an
  API-mode capability.
- A typed marker mechanism already survives the full official
  serialize -> import -> read-back path **in the deployed baseline**:
  1246 MetadataUsage objects, 1136 MetadataUsage-owned Annotation objects
  (VssSignalMetadata 623, VssQuantityMetadata 323, VssRangeMetadata 116,
  VssAllowedValuesMetadata 62, AI 12), plus the in-repo DE4SDV precedent
  `#AdapterExchangeExcluded dependency ...`
  (`middleware_physical_software_realization.sysml`): 8 such tagged
  Dependencies read back with the complete witness
  Dependency -> (owned Annotation) -> (MetadataUsage) -> (FeatureTyping) ->
  MetadataDefinition, UUID-preserved.
- The locked `SysML Requirement Derivation Library 2.0.0`
  (`sysand-lock.toml`) is pinned but **not materialized or consumed**
  (`.sysand/env.toml` lists only Requirements Management, Syside Views,
  sysmod). Per plan §5 and R0: a lock entry is not adoption; upstream
  involvement gate applies. Not used by this slice.
- Kernel identity is ingestion-validated and available: the privileged run
  for the deployed SHA carries 32 kernel bindings including
  `Need -> StakeholderNeedCandidate` and
  `Requirement -> RequirementCandidate` (element UUIDs verified present with
  matching types in the deployed revision).

## 3. Representation decision

**Semantic grounding (option order of plan §4/§5 applied):**

1. Native SysML requirement derivation construct: none in the pinned
   Systems Library for requirement-to-need derivation; the spec-native
   `Derivation` connection is a Requirement-to-Requirement connection in the
   (locked, unconsumed) Requirement Derivation Domain Library and does not
   express Need endpoints. Rejected for this slice.
2. **Selected: DE4SDV kernel `metadata def` discriminator** — a typed marker
   (SemanticMetadata specialization) applied to the dependency that carries
   the derivation meaning. This follows the spec's own domain-library pattern
   (e.g. CausationMetadata over causation connections) and the repo's
   existing, serializer-proven `#AdapterExchangeExcluded` precedent. The
   *meaning* (Requirement -> Need, direction, strength) stays in the ontology
   contract during migration; the marker makes the dependency an instance of
   the predicate instead of an untyped edge.

**Exact form (validated form corrected by the licensed toolchain, see below):**

- `metadata def RequirementDerivation :> SemanticMetadata` in the method
  kernel (`de4sdv_method_context.sysml`), with a doc comment carrying
  the engineering meaning and non-claims.
- The chosen AEBS derivation dependencies carry `#RequirementDerivation`.

**Licensed-validator correction (2026-09-10, exact-head CI run 34487362191):**
the initial draft typed the metadata feature
(`ref :>> annotatedElement : SysML::Dependency;`). The licensed SysIDE
validation rejected every application with
`metadata-feature-annotated-element: Metadata feature cannot annotate
Dependency` — a metadata *feature* cannot annotate a Relationship in the
pinned toolchain, even though the spec's CausationMetadata annotates
Connection*Definition* elements. The accepted form carries **no typed
annotatedElement feature**: the marker is a plain SemanticMetadata
specialization (the same shape as the already-deployed
`AdapterExchangeExcluded` marker), applied with the `#` prefix, and the
dependency-annotation binding is established by the `#` application itself.
The discriminating power is unchanged: the marker identity is still resolved
through the ingestion-validated kernel binding, not by name or endpoint
types.

**Subject/target types and direction:** source (client) = RequirementUsage
grounded in `RequirementCandidate` lineage; target (supplier) = RequirementUsage
grounded in `StakeholderNeedCandidate` lineage. Canonical direction
R -> N; inverse navigation reuses the identical witness.

**Discriminator:** the marker MetadataUsage typed by
`RequirementDerivation` owned by the Dependency via Annotation. A Dependency
without the marker is not a derivation, regardless of endpoint types.

**Expected serialized witness shape** — from the deployed-baseline
`#AdapterExchangeExcluded` evidence (same mechanism), **not yet observed for
the new definition (UNVERIFIED until the exact-head privileged run)**:

```text
Dependency (client=[R], supplier=[N])
  --ownedRelationship--> Annotation
       --annotatedElement--> the same Dependency
       --ownedRelatedElement--> MetadataUsage (#RequirementDerivation)
             --FeatureTyping--> MetadataDefinition RequirementDerivation
```

**Library/adoption dependencies:** none. `Metaobjects::SemanticMetadata`
comes from the already-consumed pinned Kernel Semantic Library (same base the
VSS library specializes). The locked Requirement Derivation Library remains
unconsumed; adopting it is a separately authorized decision.

**Supported claim / explicit non-claims:** this slice supports the model-native
discriminated derivation edge, its projection row, and API-mode traversal for
the slice. It does not claim: satisfaction, allocation, verification, evidence,
acceptance, full-ontology migration (O4), library adoption, or universal
derivation checking of every future model file.

## 4. Free-text conversion discipline

Free-text `source = "Derived from N-AEBS-001"` attributes are discovery leads.
Each converted edge requires confirming the engineering derivation itself.
The first slice converts exactly the witnesses needed for the proof; the
remaining edges migrate in bounded follow-ups (UG-03/UG-20 gates apply).

## 5. Independent review repair record (2026-09-10)

The independent review at head `cf9f48bc` returned R1–R6 (changes requested).
All finding probes were re-executed locally, then repaired:

- **R1 (endpoint lineage):** traversal now grounds both endpoints in the
  declared `source_lineage_of` / `target_lineage_of` kernel lineages via
  ingestion-validated UUIDs plus Subclassification/FeatureTyping witnesses.
  A tagged dependency with an out-of-lineage endpoint fails closed with a
  precise diagnostic; it is never a quiet absence.
- **R2 (witness closure):** the discriminator requires the complete witness —
  the dependency owns an Annotation that annotates that same dependency, the
  Annotation owns an existing `MetadataUsage` typed by the validated marker
  definition, and annotation ownership is consistent in both directions
  (dangling, mistyped, orphaned, or contradictory-ownership witnesses fail
  closed). Witness identity (relationship, marker usage, owner) is carried on
  every hop and echoed in query edges.
- **R3 (projection/profile):** `RevisionIdentity` only accepts a full 40-hex
  SHA + project/commit ids and is constructed from a validated revision
  binding; the ontology contract identity (path + SHA-256) is recomputed from
  the actual file at generation time; `support_state` is `vocabulary-only`
  until exact-candidate closure evidence is supplied (`witness_closure_verified`);
  profile mechanics are derived from the executable mapping and the generated
  profile passes a semantic compatibility gate (`assert_profile_compatible`)
  that rejects contradictions with the mapping (UG-25). The YAML is honestly
  labeled the ontology/kernel contract (O0/O1 authority), not a
  model-resident contract.
- **R4 (inverse navigation):** `derivedRequirementsOfNeed` added as an
  incoming `metadata-tagged-dependency` mapping over the SAME witness with
  swapped lineage sides; forward/inverse witness-identity equality is tested.
- **R5 (proof CLI):** `scripts/prove_derivation_slice.py` v2 requires an
  independently supplied `--expected-revision` (validated against the
  binding), resolves case identities from the revision, asserts exact
  endpoint/witness sets, treats explicit gaps as failures, proves inverse
  navigation per case, and imports fail-safe from any cwd. Fault-injection
  tests cover wrong source/target, incomplete witness, gap-with-edge,
  adversarial edge, wrong revision, and missing expected revision.
- **R6 (ingestion proof):** still pending by design — the authorized
  exact-candidate privileged ingestion runs only after this repair passes
  independent re-review. PR stays draft; claims stay PREPARED, not PROVEN.

