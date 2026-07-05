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

  /*
   * Reusable view definitions are intentionally not added yet. A `view def`
   * should define a reusable view-construction recipe with filters, rendering,
   * or composition logic. The current AEBS pilot only needs concrete `view`
   * usages that expose feature-package content and render it for review.
   */
}