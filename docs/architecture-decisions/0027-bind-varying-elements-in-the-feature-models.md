# ADR 0027: Bind varying elements to features in the feature models

## Status

Proposed

The owner took decisions 1 to 4 and 7 on 2026-11-14, as rule-5 option A, and
decision 5 on 2026-11-15, as the form for a pair. Decisions 6 and 8 work out
their consequences. They were drafted after his choices, and he decides on
them with this record. Until the order of decision 8 is complete, rule 5's
dependency form stays in force.

## Context

Since 2026-10-21, rule 5 of the
[increment workflow](../../methodologies/sysmod-sysmlv2/increment-workflow.md#method-rules-and-the-increment-workflow-model)
has said that a requirement varies with the features that bring its system of
interest into a member product. Its links are plain dependencies, declared
next to the requirement or its system of interest, outside the feature-model
documents. No check reads them.

At `65129d60`, the six requirement packages hold 100 requirements. By the
rule's own links, 11 of them vary, all of them of INC-MW-011. The 35
requirements of INC-DRIVING-001 read as core, because their links start from
the phase 8 realization, which the rule does not count. The phase 5 header of
INC-DRIVING-002 says that its nine requirements are not core; their links wait
for its phase 9.

The PLEML library binds a model element to a feature with a `#FeatureBinding`
dependency, the element as client and the feature as supplier. Under
[ADR 0022](0022-adopt-pleml-as-product-line-authority.md), the PLEML
configuration evaluator reads only the bindings of shared-asset variants. It
refuses a binding whose client is no variant, and a plain dependency in a
feature-model document.

One case needs two features. The integration layer of INC-MW-011, its
increment's system of interest, needs both an application and a middleware.
For each supported pair, the derivation rules derive an adapter variant that
no configuration selects (ADR 0022 decision 4).

## Decision

1. **One superset.** Every element of the shared assets is in every member
   product, unless one link binds it to a feature.
2. **Placement.** The link is owned in the feature-model document, next to the
   platform-stack bindings. The element carries nothing: no attribute, no
   metadata and no dependency of its own
   ([ADR 0009](0009-adopt-ode4hera-requirements-attributes.md)).
3. **One feature.** A PLEML `#FeatureBinding` binds an element that one
   feature brings, with the element as client and the feature as supplier.
4. **Through the subject.** A requirement applies where its system of interest
   applies and where its own link applies. The system of interest is bound
   once. A requirement is bound only for what its subject does not bring. A
   link that repeats its subject's has no consumer and does not earn its place
   ([ADR 0021](0021-make-model-elements-earn-their-place.md) decision 2).
5. **A pair.** An element that by itself needs an application and a
   middleware, with no subject that carries either, follows the adapter
   variant that the derivation rules derive for the pair. One link names that
   derived variant, and a DE4SDV kernel definition next to `#DerivationRule`
   types it. The element is in a member product exactly when the adapter is
   derived there. The derived variant names every premise of its rule, as
   rule 5 says today.
6. **One link per element.** No element carries two links, and two links on
   one element are not read as both. A combination that neither form covers
   goes to the owner before it is modeled.
7. **The reader.** The PLEML configuration evaluator reads both forms. The
   evaluation receipt of each configuration lists the elements and the
   requirements of its member product.
8. **Order.** Rule 5 states the form first. The evaluator and the receipt
   format follow, then the privileged receipts, then the move of the existing
   links of INC-MW-011 and INC-DRIVING-001. INC-DRIVING-002 binds directly in
   its phase 9. Until the existing links have moved, rule 5's dependency form
   governs, and no slice declares a link that the evaluator refuses.

This amends ADR 0022 decision 3: the integrity of the bindings covers both
forms. It amends decision 5: the receipts list each member product's
elements. Decision 4 stands and is extended: the adapter stays a derived
realization, with no helper feature and no implies constraint.

## Consequences

- **A reader.** Each configuration's requirement list comes out of the
  licensed run instead of a reading of the model.
- **A check.** A link that the evaluator cannot resolve fails the evaluation
  instead of going unnoticed.
- **Receipts.** A receipt binds the digests of the documents it read. A
  binding whose client lives in an increment package would let every edit of
  that package stale every receipt. The evaluator change names the bound
  elements by identity, or it brings the recurring cost of licensed runs to
  the owner first.
- **Kernel work.** The pair link needs its kernel definition. The evaluator,
  the receipt readers and the feature-model documentation need their changes.
  Each lands in its own pull request.
- **Migration.** The six links counted at `65129d60` move into the
  feature-model document. The tests that keep requirement names out of the
  feature-model documents turn around.
- **Ontology.** `specifiesFeature` stays a vocabulary-only relation. Its range
  is the kernel class Feature, not a PLEML feature, so a binding does not
  realize it.

## Non-decisions

- The kernel name of the pair link and its evaluation.
- The receipt format.
- The wording of ADR 0023 and ADR 0026 on the requirement dependencies on the
  HMI display, which the migration revisits.
- The pedestrian and bicycle target requirements of the AEBS
  (REQ-AEBS-010, REQ-AEBS-011, REQ-AEBS-014 and REQ-AEBS-015). They have no
  link, while the feature model holds the optional features
  `pedestrianDetection` and `bicycleDetection`. The model records their
  applicability as open (GAP-AEBS-REQ-015 and GAP-AEBS-REQ-016).
- The eight product requirements of INC-MW-005. Each concerns the middleware
  integration boundary and reads as core, while a member product can have no
  vehicle-level middleware (`middleware::none`). The migration brings their
  classification to the owner.
- Which requirements a receipt lists. A requirement whose subject is the
  increment or an element of System 2 belongs to no member product; the
  evaluator change defines the population.
- Any message to the PLEML maintainers.

## Alternatives not chosen

- **A helper feature per pair.** An implies constraint and a requires
  constraint would tie it to the pair, and every configuration with the pair
  would select it. It reverses ADR 0022 decision 4 and adds features that no
  stakeholder chooses.
- **Two bindings read as both.** The library gives two bindings on one
  element no such meaning.
- **Plain dependencies outside the feature models.** This is rule 5 today.
  Nothing reads them.

## Links

- [Rule 5 of the increment workflow](../../methodologies/sysmod-sysmlv2/increment-workflow.md#method-rules-and-the-increment-workflow-model)
- [ADR 0009](0009-adopt-ode4hera-requirements-attributes.md),
  [ADR 0021](0021-make-model-elements-earn-their-place.md) and
  [ADR 0022](0022-adopt-pleml-as-product-line-authority.md)
- [PLEML configuration evaluation](../product-line-engineering/pleml-configuration-evaluation.md)
