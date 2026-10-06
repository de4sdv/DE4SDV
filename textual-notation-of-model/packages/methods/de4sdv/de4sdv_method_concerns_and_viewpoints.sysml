/*
 * DE4SDV reusable method-governance concern and viewpoint kernel.
 *
 * This package contains only DE4SDV-specific method-governance viewpoints
 * that are not part of GfSE SAF. SAF viewpoints are in the separate
 * SAF_Viewpoints package.
 *
 * Method-governance viewpoints (increment framing, product-line
 * classification, regulatory scope) address DE4SDV workflow concerns:
 * increment boundaries, product-line classification discipline, and
 * regulatory visibility without compliance claims. These do not map to
 * any published SAF viewpoint.
 *
 * Note: this package uses a distinct top-level package name instead
 * of nested `DE4SDV::Methods::*` because the current SysIDE validation path
 * reports repeated top-level `DE4SDV` package declarations as shadowed rather
 * than namespace-merged across files.
 */

package DE4SDV_MethodViewpoints {
  doc ViewOntologyDefinition /* A representation produced according to a viewpoint for stakeholder review. */
  comment about ViewOntologyDefinition /* Native SysML view remains the representation; documentation is not a publication,
   * renderer or conformance result. */


  doc ViewpointOntologyDefinition /* A specification of stakeholder concerns, conventions, and expected view content. */
  comment about ViewpointOntologyDefinition /* Native SysML viewpoint definitions remain the representation; existing DE4SDV/SAF
   * selections and their provenance remain unchanged. */


  doc ConcernOntologyDefinition /* An interest or issue that matters to a stakeholder and motivates views, needs,
   * requirements, or evidence. */
  comment about ConcernOntologyDefinition /* Native SysML concern definitions/usages remain the representation; no local generic
   * Concern type or additional satisfaction claim. */


  /* Native grounding records (O4 W3, KEEP_NATIVE): the normative SysML Systems
   * Library carries these concepts; DE4SDV copies no library type. */
  comment about ViewOntologyDefinition /* Grounding: Systems Library Views package, abstract view def
   * View (every view definition specializes it; view usages expose model content and
   * are checked through viewpointSatisfactions). Concrete DE4SDV/SAF view usages are the
   * model representation; the producesView carrier types its view end by the library
   * View. */
  comment about ViewpointOntologyDefinition /* Grounding: Systems Library Views package, abstract
   * viewpoint def ViewpointCheck (base of every viewpoint definition; viewpointChecks is
   * the base feature of viewpoint usages). DE4SDV method viewpoints in this package and
   * SAF_Viewpoints specialize it natively; no generic DE4SDV Viewpoint type exists. */
  comment about ConcernOntologyDefinition /* Grounding: Systems Library Requirements package, concern
   * def ConcernCheck (base of every concern definition; concernChecks is the base feature
   * of concern usages; viewpoints frame concerns natively). DE4SDV method concerns in this
   * package specialize it natively; no generic DE4SDV Concern type exists. */


  private import Views::*;

  concern def ProductLineCapabilityClassificationConcern {
    require constraint {
      doc /*
       * Reviewers need model content to distinguish common product-line
       * capabilities from features, candidate features, variability decisions, and
       * deferred variability decisions.
       */
    }
  }

  concern def RegulatoryScopeWithoutComplianceClaimConcern {
    require constraint {
      doc /*
       * Reviewers need regulatory anchors, source assumptions, missing evidence,
       * and scope boundaries to be visible without implying compliance,
       * certification, or type approval.
       */
    }
  }

  concern def IncrementBoundaryConcern {
    require constraint {
      doc /*
       * Reviewers need each increment to separate framing, operational context,
       * needs, requirements, functional modeling, logical realization,
       * physical/software realization, and evidence work.
       */
    }
  }

  concern def MethodStackConcern {
    require constraint {
      doc /*
       * Reviewers need the relationship between viewpoint selection, method flow,
       * ontology terms, SysML v2 expression, and external catalog use to remain
       * explicit rather than collapsed into one method blob.
       */
    }
  }

  concern def ProductLineConfigurationConcern {
    require constraint {
      doc /*
       * Reviewers need the native SysML v2 variation and variant structure
       * in the model to be visible for review, so that configured choices
       * can be checked against the feature catalogue and bill-of-features.
       */
    }
  }

  concern def ProductModelAssemblyConcern {
    require constraint {
      doc /*
       * Reviewers need a composite product model's assembly of shared assets
       * (platform stack, sensing, feature realization) and its product-level
       * trace links to be visible for review, so that the composition can be
       * checked for completeness and correctness against the selected
       * configuration.
       */
    }
  }

  viewpoint def IncrementFramingViewpoint {
    require constraint {
      doc /*
       * An increment framing view shall show the selected stakeholder
       * concerns, system layers, method-stack elements, scope boundary,
       * deferred scope, and decision guardrails for the current increment.
       */
    }
  }

  viewpoint def ProductLineClassificationViewpoint {
    require constraint {
      doc /*
       * A product-line classification view shall separate common product-line
       * capabilities from features, candidate features, variability decisions, and
       * deferred variability decisions before downstream functional modeling
       * starts.
       */
    }
  }

  viewpoint def RegulatoryScopeViewpoint {
    require constraint {
      doc /*
       * A regulatory-scope view shall identify regulatory anchors, source
       * assumptions, scope boundaries, and missing evidence while explicitly
       * avoiding unearned compliance, certification, or type-approval claims.
       */
    }
  }

  viewpoint def ProductLineConfigurationViewpoint {
    require constraint {
      doc /*
       * A product-line configuration view shall expose native SysML v2
       * variation and variant elements in the model so that configured
       * choices can be reviewed against the feature catalogue and
       * bill-of-features. The view frames the variation structure; the
       * YAML feature model and bill-of-features remain the source of
       * truth for configuration decisions.
       */
    }
  }

  viewpoint def ProductModelAssemblyViewpoint {
    require constraint {
      doc /*
       * A product-model assembly view shall expose how a composite product
       * model assembles shared assets (platform stack, sensing, feature
       * realization) and its product-level trace links, so that the
       * composition can be reviewed for completeness and correctness
       * against the selected configuration. The view frames the assembly
       * and trace structure; the bill-of-features and generated projections
       * remain the source of truth for variant selection.
       */
    }
  }

  /*
   * Reusable view definitions are intentionally not added yet. A `view def`
   * should define a reusable view-construction recipe with filters, rendering,
   * or composition logic. The current AEBS pilot only needs concrete `view`
   * usages that expose feature-package content and render it for review.
   */
}