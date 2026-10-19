/*
 * DE4SDV product-line derivation semantic kernel.
 *
 * Metadata definitions that a feature model and its configurations apply:
 * the shared-asset variations that no configuration selects (derived
 * variations), the rules that derive their variants, the product-model
 * projection a feature model generates, the projection name of each
 * configuration, and the features whose binding time is not yet decided.
 *
 * The definitions annotate native SysML v2 variations, dependencies and the
 * occurrences of a feature model. They declare no variation-point part
 * definition and no selection record, and they import no PLEML package
 * (ADR 0022 confines PLEML imports to the feature models). Kernel identity
 * follows ADR 0011: each definition is an ontology class that ingestion binds
 * by metatype, declared name and this source file.
 *
 * Authority: until the switch of ADR 0022, the YAML catalogue and the
 * configurator remain the derivation authority (ADR 0006 decision 6), and
 * only the fenced feature models apply these definitions.
 */

package DE4SDV_ProductLineDerivation {
  private import ScalarValues::String;

  metadata def DerivedVariation {
    doc /* A shared-asset variation whose variant no configuration selects: its derivation
         * rules derive the variant from the selected features. Applied to a dependency
         * whose client is the variation and whose suppliers are its source features, the
         * features whose selected alternative the rules condition on. A valid configuration
         * derives exactly one variant of the variation: exactly one of its rules must
         * match, and a configuration that matches no rule or several is rejected. A
         * derived variant is never a feature and never a manual product choice, so a
         * feature binding or configuration entry that targets one is refused. The short
         * name of the dependency is the stable identity of the derivation. */
    :> annotatedElement : SysML::Dependency;
  }

  metadata def DerivationRule {
    doc /* A rule that derives one variant of a derived variation. Applied to a dependency
         * whose client is that variant and whose suppliers are the premises: one
         * alternative of each source feature of the variation. The rule matches a
         * configuration that selects every premise. Derivation applies to valid
         * configurations only. */
    :> annotatedElement : SysML::Dependency;
  }

  metadata def ProductModelProjection {
    doc /* Feature-model metadata naming the product-model projection that each
         * configuration of the annotated feature model generates. ownerName is the
         * shared-asset part definition that owns the variations the feature bindings and
         * derived variations resolve, and packageName is the package that owns it; every
         * generated product model specializes that part definition. label names the
         * projection in the generated text. The names identify nothing: they must agree
         * with the owner of the bound and derived variants. */
    :> annotatedElement : SysML::OccurrenceDefinition;
    :> annotatedElement : SysML::OccurrenceUsage;
    attribute packageName : String {
      doc /* The package that owns the shared-asset part definition. */
    }
    attribute ownerName : String {
      doc /* The shared-asset part definition that every generated product model specializes. */
    }
    attribute label : String {
      doc /* The projection label in the generated text. */
    }
  }

  metadata def ProductModelProjectionName {
    doc /* Configuration metadata: the name of the part definition that the product-model
         * projection of the annotated configuration declares. It annotates the
         * configuration and is not one of its features. */
    :> annotatedElement : SysML::OccurrenceDefinition;
    :> annotatedElement : SysML::OccurrenceUsage;
    attribute partDefinitionName : String {
      doc /* The name of the generated product-model part definition. */
    }
  }

  metadata def UnassignedBindingTime {
    doc /* Feature metadata: the binding time of the annotated feature is not yet decided.
         * The feature keeps its default binding time, and no configuration verdict depends
         * on the annotation. A feature that a feature binding, a derived variation or a
         * derivation rule names has a decided binding time, so it never carries this
         * annotation. */
    :> annotatedElement : SysML::OccurrenceDefinition;
    :> annotatedElement : SysML::OccurrenceUsage;
  }
}
