# ADR 0020: Give the remaining ontology definitions model-resident kernel homes

## Status

Accepted

The owner accepted implementation decisions I1–I4 on 2026-10-06. I4 is
superseded by the D4 follow-up in O4 Wave A; see
[owner decisions](../method-conformance/o4/owner-decisions-2026-10.md).

## Context

O4 retires the authored ontology YAML
(`approach/framework/ontology/de4sdv-basic-ontology.yaml`) as semantic
authority. The owner decided on 2026-10-05 to delete that file at O4 closure.
Before it can go, every authored definition needs a durable home in the SysML
method kernel. 76 authored definitions (71 classes, 5 predicates) still had
their text only in the YAML, and several open questions blocked the homes:
how to document architecture umbrella terms without a parallel taxonomy, where
acceptance criteria and evidence contracts live, how evaluation exclusions are
recorded, how feature/common-capability disjointness is stated, and whether
`instantiatesCanonicalArchitecture` is queryable.

This ADR separates two kinds of decision. Orkun Yilmaz made the owner
decisions on 2026-10-05. The implementation decisions were taken while
building PR #328, and they need the owner's acceptance before this ADR is
`Accepted`.

## Decision

### Owner decisions (2026-10-05)

1. **D1 — architecture umbrella terms.** `DE4SDV_MethodContext` documents
   `ArchitectureElement`, `Function`, `LogicalElement`, `PhysicalElement` and
   `Interface`. Each points to its native SysML kinds. There is no parallel
   type taxonomy and no widening of the Interface filter.
2. **D2 — acceptance criterion.** The kernel owns
   `requirement def AcceptanceCriterion`, specialized by
   `MiddlewareAcceptanceCriterion`. A test-verdict criterion is distinct from
   an acceptance decision under `de4sdv.acceptance.maintainer-decision.v1`.
3. **D3 — evaluation exclusions.** `MethodEvaluationScope` owns structured
   `MethodEvaluationExclusion[*]` records: the excluded element plus a
   required, non-empty rationale.
4. **D4 — evidence contract.** The kernel owns
   `requirement def EvidenceContract :> RequirementCandidate`, so that typed
   specialization can unblock `hasRelevantEvidenceContract`. See
   implementation decision I4 for what this PR delivers against that aim.
5. **Decision 7 — feature/common-capability disjointness.** The rule is kept
   and made model-resident through native `disjoint from`, with a checked
   constraint as the fallback if the toolchain does not support it. The
   licensed toolchain rejected a standalone `disjoining … disjoint A from B;`
   inside a SysML package (run 37411981652), so the fallback applies:
   `CommonProductLineCapability` asserts
   `not (that istype ProductLineFeatureCandidate)`, and the reverse.
6. **D4 follow-up (2026-10-06).** The seven remaining AEBS
   evidence-contract definitions specialize `EvidenceContract`, and
   `MiddlewareAcceptanceCriterion` drops that specialization; it stays an
   `AcceptanceCriterion` only. The `EvidenceContract` specialization closure is
   exactly the eight AEBS contracts and is documented in the kernel as the
   `hasRelevantEvidenceContract` range discriminator (vocabulary only).
7. **Decision 8 — canonical architecture.**
   `instantiatesCanonicalArchitecture` is vocabulary only: not queryable; no
   product-to-canonical reachability claimed. There is no executable mapping
   or canonical-package selector.

### Implementation decisions taken in PR #328 (pending owner acceptance)

1. **I1 — where the definition text lives.** Every authored definition has
   normalized-exact model documentation:
   - 51 definitions own it directly: 40 as an anonymous `doc`, 11 as a named
     `doc ontologyDefinition`.
   - 25 concepts without a definition of their own (umbrella, native/library,
     historical and external terms) use a package-owned
     `doc <Term>OntologyDefinition`. The name is the only link to the
     concept, and a test pins every name to its inventory row in both
     directions.

   Where a definition carries both an anonymous doc and the exact
   `ontologyDefinition`, the `ontologyDefinition` text is the authored
   definition and replaces the YAML text when the YAML is deleted. The
   anonymous doc stays as explanatory model documentation.
2. **I2 — private definition docs.** The 11 `doc ontologyDefinition` members
   are `private`, so the name `ontologyDefinition` is not an inherited,
   resolvable member of specializations.
3. **I3 — non-shadowing names.** Named docs and named comments are package
   members and are re-exported by wildcard imports. Run 37411981652 showed
   that `doc VerificationMethod` hid the library metadata `VerificationMethod`
   from every importer. Kernel doc names use the `ontologyDefinition` or
   `<Term>OntologyDefinition` form; named comments use a
   `<Term>VocabularyRole` form (`hasStakeholderVocabularyRole`,
   `hasAcceptanceCriterionVocabularyRole`); neither may reuse a class,
   predicate or definition name. A repository test enforces this.
4. **I4 — D4 delivered as vocabulary only (superseded by the D4 follow-up
   above).** At PR #328 only
   `OverrideEvidenceContract` (AEBS) and `MiddlewareAcceptanceCriterion`
   specialize `EvidenceContract`. The other seven AEBS evidence-contract
   definitions do not, so the type's specialization closure is not yet the
   evidence-contract population and is not used to discriminate
   `hasRelevantEvidenceContract`. This falls short of D4's aim. Specializing
   the seven definitions changes which requirements count as evidence
   contracts and is left to a separate change. A repository test pins the
   current closure.

## Consequences

- O4 can delete the YAML once all consumers read model authority. This ADR
  supplies the homes only; it does not delete the YAML, rewire consumers,
  replace the YAML-based `check_model_sync` contract or close O4.
- The licensed check validates the constraint declarations but has not been
  shown to evaluate them against usages. A bounded repository probe guards the
  disjointness rule across all three validated model roots; it is not a SysML
  evaluator.
- All eight AEBS evidence-contract definitions specialize `EvidenceContract`
  (D4 follow-up). `hasRelevantEvidenceContract` still keeps its existing
  dependency mapping at runtime; adopting the type-lineage discriminator is a
  separate reviewed consumer change. Any new specialization must update D4,
  this ADR and the population test together.
- `MiddlewareAcceptanceCriterion` is an `AcceptanceCriterion` only; the 15
  middleware acceptance criteria are no longer typed as evidence contracts.
- O1's text-parity observer reads anonymous definition docs only, so the
  definitions that also carry `ontologyDefinition` still show `differs`
  there. Their review records are unchanged.

## Non-decisions

- Deleting the YAML, rewiring consumers or retiring O4 rows.
- Activating or adopting PLEML semantics, or changing any dependency pin.
- Creating any acceptance record.
- Making the delivery gate required.

## Links

- [O4 kernel definition homes](../method-conformance/o4/kernel-definition-homes.md)
- [kernel-definition-homes.json](../method-conformance/o4/kernel-definition-homes.json)
- [ADR 0019](0019-specify-deterministic-method-conformance-subsystem.md)
- Pull request #328
