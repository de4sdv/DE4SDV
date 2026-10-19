/*
 * DE4SDV reusable product-line semantic kernel.
 *
 * This package keeps product-line vocabulary out of feature-specific slices.
 * It follows the DE4SDV/ISO 26580-aligned distinction that common capabilities
 * are not features unless they distinguish member products.
 *
 * SysML v2 variability is modeled with native `variation` / `variant` notation:
 * a variation marks the varying definition or usage, and its owned variant
 * usages enumerate allowed choices. Do not introduce a project-local
 * variation-point part definition in place of native SysML v2 variation semantics.
 */

package DE4SDV_ProductLine {
  doc instantiatesCanonicalArchitectureOntologyDefinition /* Explicit binding from a composite member product's contained architecture instances
   * (its logical-system and software usages) to the canonical architecture usages whose
   * allocation and evidence records govern them. The modeled dependencies originate from
   * the contained usages, not from the member-product root; the executable mapping must
   * therefore define which elements carry this relationship and how a query walks it before
   * any product-level query reachability is claimed. Vocabulary only for now: no
   * sysml_mapping is declared because a generic dependency traversal cannot distinguish
   * canonical-architecture bindings from ordinary part-to-part dependencies without
   * inventing a naming heuristic. Declaring an executable mapping requires an explicit
   * canonical-usage selector (for example an API-side allowlist of canonical packages), not
   * a name-based filter. The binding does not restate allocations at product level and does
   * not make a composite projection a resolved configured product. */
  comment about instantiatesCanonicalArchitectureOntologyDefinition /* not queryable; no product-to-canonical reachability claimed. Vocabulary only; no
   * executable mapping and no canonical-package selector are introduced. The selector
   * discussion in the retained definition is a future prerequisite, not implementation in
   * this package. */


  doc FeatureConfigurationOntologyDefinition /* A selection of features that describes a member
   * product or scenario. Its variation choices are derived from the selected features. It
   * does not select common capabilities, because every member product has them. */
  comment about FeatureConfigurationOntologyDefinition /* Definition text is model-resident.
   * Configurations are recorded where the configuration authority of ADR 0022 puts them: as
   * Bill-of-Features records until the switch, and as PLEML feature configurations from the
   * switch. This package adds no selection algebra and no consumer wiring. */


  doc VariantOntologyDefinition /* A native SysML v2 variant usage owned by a variation point and representing one allowed
   * choice for that variation. */
  comment about VariantOntologyDefinition /* Native SysML variant usage owned by a variation remains the representation; no new
   * reusable variant class or selection authority. */


  doc VariationPointOntologyDefinition /* A native SysML v2 variation definition or usage that identifies an element whose
   * allowed instances vary across product-line configurations. */
  comment about VariationPointOntologyDefinition /* Native SysML variation definition/usage remains the representation, not a generic
   * variation-point part taxonomy or configurator adoption. */


  /* Vocabulary roles of the reviewed product-line relationships.
   * The ontology declares these relationships by domain and range only; no
   * authored definition text exists, so these comments record the
   * model-resident vocabulary home and claim boundary, not a new meaning. The
   * comment names end in VocabularyRole and never reuse a predicate, class or
   * declaration name, because named comments are package members re-exported by
   * wildcard imports. */

  comment specifiesFeatureVocabularyRole about ProductLineFeatureCandidate /* Vocabulary role
   * of the reviewed relationship specifiesFeature: domain Requirement (kernel
   * RequirementCandidate), range Feature (kernel ProductLineFeatureCandidate).
   * Vocabulary only: no runtime traversal, no sysml_mapping, no semantic-support
   * claim and no PLEML dependency. A native realization is deferred until feature
   * usages exist in models; any realization is an explicit signature/migration
   * review. */

  comment specifiesCommonCapabilityVocabularyRole about CommonProductLineCapability /* Vocabulary
   * role of the reviewed relationship specifiesCommonCapability: domain Requirement
   * (kernel RequirementCandidate), range CommonCapability (kernel
   * CommonProductLineCapability). Vocabulary only: no runtime traversal, no
   * sysml_mapping, no semantic-support claim and no PLEML dependency. Any future
   * native realization is decided together with specifiesFeature. */

  comment variesAtVocabularyRole about ProductLineFeatureCandidate /* Vocabulary role of the
   * reviewed relationship variesAt: domain Feature (kernel
   * ProductLineFeatureCandidate), range VariationPoint (native SysML v2 variation
   * definition/usage; see VariationPointOntologyDefinition). The identity is kept as
   * navigation vocabulary only. Its model authority is the native variation
   * structure: a realization is a derived fact over native variation/variant
   * membership, and its evidence gate is a feature usage that participates in a
   * variation's variant membership. Until such a usage exists, variesAt stays
   * vocabulary-only: no runtime traversal, no sysml_mapping, no variation-point part
   * taxonomy, no YAML edge mapping and no PLEML dependency. The switch of ADR 0022 does
   * not change this grounding: a PLEML feature binding of a variant is not that evidence
   * gate. */

  comment FeatureConfigurationVocabularyRole about FeatureConfigurationOntologyDefinition /* Vocabulary
   * only. No configurator authority; configuration authority follows ADR 0022. Until the
   * switch, the YAML Feature Catalogue and Bill-of-Features configuration decision layer,
   * evaluated by the configurator, selects the features. From the switch, the PLEML
   * feature configurations, evaluated by the DE4SDV evaluator, select them, and the class
   * grounds on the pinned PLEML library definition FeatureConfiguration, which owns only
   * features. This package declares no FeatureConfiguration definition, no selection
   * algebra and no model relationship. */

  comment appliesToMemberProductVocabularyRole about FeatureConfigurationOntologyDefinition /* Vocabulary
   * role of the reviewed relationship appliesToMemberProduct: domain
   * FeatureConfiguration, range MemberProduct (kernel ProductLineMemberProduct).
   * Vocabulary only, with no sysml_mapping and no runtime traversal. No configurator
   * authority; configuration authority follows ADR 0022. Until the switch, the
   * Bill-of-Features configuration layer owns the binding. From the switch, the
   * relationship grounds on the PLEML FeatureConfigurationBinding, which binds a member
   * product's model element to its configuration, and the governed scope stays the
   * admission authority. Existing runtime exclusions are preserved verbatim and are not
   * collapsed into hasSubject. */

  comment selectsFeatureVocabularyRole about FeatureConfigurationOntologyDefinition /* Vocabulary
   * role of the reviewed relationship selectsFeature: domain FeatureConfiguration,
   * range Feature (kernel ProductLineFeatureCandidate). Vocabulary only, with no
   * sysml_mapping and no runtime traversal. No configurator authority; configuration
   * authority follows ADR 0022. Until the switch, Bill-of-Features selections, evaluated
   * by the configurator, are the operational selection. From the switch, the relationship
   * grounds on the PLEML feature configuration, which selects a feature by redefining it
   * with multiplicity 1. A realization needs a reviewed carrier, because a PLEML
   * configuration selects PLEML features and the range is the kernel
   * ProductLineFeatureCandidate: the correspondence that links a PLEML feature to the
   * governed Feature it restates is the candidate bridge. */

  comment selectsVariantVocabularyRole about FeatureConfigurationOntologyDefinition /* Vocabulary
   * role of the reviewed relationship selectsVariant: domain FeatureConfiguration,
   * range Variant (native SysML v2 variant usage; see VariantOntologyDefinition).
   * Vocabulary only. No configurator authority; configuration authority follows ADR 0022.
   * A configuration selects no variant directly: its variants are derived from its
   * selected features, through the Bill-of-Features mappings and the configurator until
   * the switch, and through the PLEML feature bindings and the DE4SDV derivation rules
   * from the switch. Native variant usages own the choice space. No new model
   * relationship kind, no sysml_mapping and no runtime traversal; model-native configured
   * products use the native variant-selection construct of ADR 0006. */


  part def ProductLine {
    doc /* A family of related member products managed through shared assets and variability. */
  }

  part def SDVProductLine :> ProductLine {
    doc /* Software-defined vehicle product line managed through DE4SDV product-line semantics. */
  }

  part def ProductLineMemberProduct {
    doc /* A configured product or product variant that belongs to a product line. */
  }

  part def ProductLineCharacteristic {
    doc /* The product-line classification base: a characteristic is a common capability, a feature candidate, deferred scope, or a native SysML v2 variation choice. */
  }

  part def CommonProductLineCapability :> ProductLineCharacteristic {
    private doc ontologyDefinition /* A capability or characteristic present in all relevant member products; not a feature
     * unless it distinguishes variants. */
    doc /* Capability required across member products; not a feature unless it distinguishes member products. */
    comment /* Phase 3 instantiates no common capability: core elements are common by
             * default and get no record, because ClassifyCapabilities records only
             * feature candidates. The definition stays for the ontology's
             * CommonCapability class, the disjointness below and the records that
             * use it. */
    /* Feature/common-capability disjointness (ADR 0020, decision 7) as a checked
     * constraint: the licensed toolchain rejects the standalone KerML disjoining in a
     * SysML package, so the axiom is a checked constraint on both definitions. */
    assert constraint notAFeatureCandidate { not (that istype ProductLineFeatureCandidate) }
  }

  part def ProductLineFeatureCandidate :> ProductLineCharacteristic {
    private doc ontologyDefinition /* A distinguishing characteristic expressing variability among member products. In the
     * kernel a feature is a candidate until member-product variability is shown; it must
     * not be accepted as a feature before that. */
    doc /* Candidate distinguishing characteristic; must not be accepted as a feature until member-product variability is shown. */
    comment /* The ontology Feature stays this kernel definition before and after the switch
             * of ADR 0022, and R001 governs it. A feature of a PLEML feature model is a
             * distinct element: an option that the configuration authority makes
             * configurable. Reference-only options and derived realizations are PLEML
             * features without being Features. Where a PLEML feature restates a governed
             * Feature, a correspondence in the feature models links the two. */
    assert constraint notACommonCapability { not (that istype CommonProductLineCapability) }
  }

  part def DeferredProductLineScope :> ProductLineCharacteristic {
    doc /* Product-line scope deliberately deferred from the current increment, including recorded gaps. */
  }

  part def ProductLineVariantChoice :> ProductLineCharacteristic {
    doc /* Descriptive project vocabulary for variant choices in YAML/Markdown traces. Concrete SysML variant usages should be represented with native `variant` membership and should not rely on this type as a substitute for variation semantics. */
  }

  part def DeferredVariantChoice :> ProductLineVariantChoice {
    doc /* Descriptive vocabulary for unresolved variant choices outside a concrete SysML variation body; not an accepted product configuration choice. */
  }

  /*
   * Generic native variation definition for unresolved product-line choices.
   *
   * SysML v2 requires the owned members of a variation definition/usage to be
   * variant usages. Keep the body limited to `variant` usages.
   */
  variation part def DeferredProductLineVariation {
    variant part deferredChoice;
  }
}
