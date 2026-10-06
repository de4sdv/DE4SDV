# ADR 0020: Give the remaining ontology definitions model-resident kernel homes

## Status

Accepted

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

Orkun Yilmaz decided D1–D4, 7 and 8 on 2026-10-05. This ADR records those
decisions and the consequences found while implementing them.

## Decision

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
   `requirement def EvidenceContract :> RequirementCandidate`. Today it is
   specialized only by `OverrideEvidenceContract` (AEBS) and
   `MiddlewareAcceptanceCriterion`. The other seven AEBS evidence-contract
   definitions do not specialize it yet, so its specialization closure is not
   the evidence-contract population and is not used to discriminate
   `hasRelevantEvidenceContract`. The runtime dependency mapping is unchanged.
5. **Decision 7 — feature/common-capability disjointness.** The rule is kept
   and made model-resident. The preferred native form, a standalone
   `disjoining … disjoint A from B;`, was rejected by the licensed toolchain
   inside a SysML package (run 37411981652). The decision's fallback applies:
   a symmetric checked constraint. `CommonProductLineCapability` asserts
   `not (that istype ProductLineFeatureCandidate)`, and the reverse.
6. **Decision 8 — canonical architecture.** `instantiatesCanonicalArchitecture`
   is vocabulary only: not queryable; no product-to-canonical reachability
   claimed. There is no executable mapping or canonical-package selector.
7. **Definition text.** Every authored definition has normalized-exact model
   documentation:
   - 51 definitions own it directly: 40 as an anonymous `doc`, 11 as
     `private doc ontologyDefinition`. These 11 are private so that
     specializations do not inherit the text as their own.
   - 25 concepts without a definition of their own (umbrella, native/library,
     historical and external terms) use a package-owned
     `doc <Term>OntologyDefinition`. The name is the only link to the concept,
     and a test pins it to the inventory row.

   Where a definition carries both an anonymous doc and the exact
   `ontologyDefinition`, the `ontologyDefinition` text is the authored
   definition and replaces the YAML text when the YAML is deleted. The
   anonymous doc stays as explanatory model documentation.

## Consequences

- O4 can delete the YAML once all consumers read model authority. This ADR
  supplies the homes only; it does not delete the YAML, rewire consumers,
  replace the YAML-based `check_model_sync` contract or close O4.
- Named documentation and named comments are package members and are
  re-exported by wildcard imports. Run 37411981652 showed that
  `doc VerificationMethod` hid the library metadata `VerificationMethod` from
  every importer. Kernel doc names must therefore use the `ontologyDefinition`
  or `<Term>OntologyDefinition` form, named comments must use a
  `<Term>VocabularyRole` form, and neither may reuse a class, predicate or
  definition name. A repository test enforces this.
- The licensed check validates the constraint declarations but has not been
  shown to evaluate them against usages. A bounded repository probe guards the
  disjointness rule across all three validated model roots; it is not a SysML
  evaluator.
- Specializing the remaining seven AEBS evidence-contract definitions is a
  separate change: it changes which requirements count as evidence contracts
  and needs its own review. A repository test pins the current population, so
  any new specialization must update D4, this ADR and that test together.
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
