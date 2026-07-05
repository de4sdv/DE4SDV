/*
 * DE4SDV reusable method concern and viewpoint kernel.
 *
 * This package is intentionally small. It does not claim to reproduce SAF.
 * It captures DE4SDV-tailored concern and viewpoint definitions needed by
 * the current feature-increment workflow so feature packages can instantiate
 * reusable concerns and select/apply reusable viewpoints instead of defining
 * one-off feature-specific concern/viewpoint taxonomies.
 *
 * These concern and viewpoint definitions are DE4SDV method concepts.
 * Engineering-domain viewpoints carry a doc comment naming the SAF viewpoint
 * they are tailored from. Method-governance viewpoints (increment framing,
 * product-line classification, regulatory scope) remain DE4SDV-specific.
 *
 * Note: this package currently uses a distinct top-level package name instead
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

  concern def OperationalContextConcern {
    require constraint {
      doc /*
       * Reviewers need to see the operational actors, context boundary,
       * and operational story for the feature increment.
       */
    }
  }

  concern def StakeholderNeedsConcern {
    require constraint {
      doc /*
       * Reviewers need stakeholder needs and validation intent to be
       * visible as requirement-like usages, not generic prose.
       */
    }
  }

  concern def RequirementTraceConcern {
    require constraint {
      doc /*
       * Reviewers need requirement candidates traced to stakeholder needs,
       * with verification methods and satisfaction status, including
       * what is not yet satisfied.
       */
    }
  }

  concern def FunctionalBehaviorConcern {
    require constraint {
      doc /*
       * Reviewers need the functional responsibilities, information items,
       * flows, and sequencing for the feature increment to be visible
       * with requirement trace.
       */
    }
  }

  concern def FunctionalInterfaceConcern {
    require constraint {
      doc /*
       * Reviewers need the functional boundary ports, signal character,
       * direction, producer/consumer mapping, and upstreaming posture
       * for DE4SDV candidate VSS extension signals.
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

  viewpoint def OperationalContextViewpoint {
    doc /*
     * SAF-tailored from: Operational Context Definition Viewpoint
     * (GfSE SAF Operational Domain).
     */
    require constraint {
      doc /*
       * An operational context view shall show external actors, context
       * boundary, use case/actor framing, and operational behavior
       * (actions, items, flows, sequencing) for the increment.
       */
    }
  }

  viewpoint def StakeholderNeedsViewpoint {
    doc /*
     * SAF-tailored from: Stakeholder Requirement Definition Viewpoint
     * (GfSE SAF Operational Domain).
     */
    require constraint {
      doc /*
       * A stakeholder needs view shall show stakeholder needs as native
       * requirement usages, stakeholder roles, and validation intent
       * for the increment.
       */
    }
  }

  viewpoint def RequirementTraceViewpoint {
    doc /*
     * SAF-tailored from: System Requirement Definition Viewpoint and
     * System Requirement Traceability Viewpoint (GfSE SAF Functional Domain).
     */
    require constraint {
      doc /*
       * A requirement trace view shall show requirement candidates,
       * their stakeholder need sources, verification methods, and
       * satisfaction status, including explicitly unsatisfied items.
       */
    }
  }

  viewpoint def FunctionalBehaviorViewpoint {
    doc /*
     * SAF-tailored from: System Functional Breakdown Structure Viewpoint
     * and System Process Viewpoint (GfSE SAF Functional Domain).
     */
    require constraint {
      doc /*
       * A functional behavior view shall show functional responsibilities
       * (actions), information items, flows, and sequencing, with
       * requirement trace to functions.
       */
    }
  }

  viewpoint def FunctionalInterfaceViewpoint {
    doc /*
     * SAF-tailored from: System Interface Definition Viewpoint
     * (GfSE SAF Functional Domain).
     */
    require constraint {
      doc /*
       * A functional interface view shall show boundary port definitions,
       * their typed items, signal character, direction, and the functional
       * chain that owns the ports.
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
