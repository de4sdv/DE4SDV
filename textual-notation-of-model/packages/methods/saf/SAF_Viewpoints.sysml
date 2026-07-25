/*
 * GfSE SAF viewpoint and concern definitions used by DE4SDV.
 *
 * Source: https://saf.gfse.org/userdoc/viewpoints.html
 *
 * This package contains only the SAF viewpoints that DE4SDV has actually
 * used in the AEBS pilot so far. New SAF viewpoints are added incrementally
 * as future DE4SDV increments need them. This is not a full reproduction
 * of the SAF viewpoint catalog.
 *
 * SAF viewpoint names match the published SAF documentation. Each viewpoint
 * def carries a doc comment identifying its SAF domain.
 *
 * DE4SDV-specific method-governance viewpoints (increment framing,
 * product-line classification, regulatory scope) remain in
 * DE4SDV_MethodViewpoints, not here.
 */

package SAF_Viewpoints {
  private import Views::*;

  // ─── Operational Domain ───

  concern def OperationalContextConcern {
    require constraint {
      doc /*
       * Reviewers need to see the operational actors, context boundary,
       * and operational story for the feature increment.
       */
    }
  }

  viewpoint def OperationalContextDefinitionViewpoint {
    doc /*
     * SAF Operational Domain: Operational Context Definition Viewpoint.
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * An operational context view shall show external actors, context
       * boundary, use case/actor framing, and operational behavior
       * (actions, items, flows, sequencing) for the increment.
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

  viewpoint def StakeholderRequirementDefinitionViewpoint {
    doc /*
     * SAF Operational Domain: Stakeholder Requirement Definition Viewpoint.
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * A stakeholder needs view shall show stakeholder needs as native
       * requirement usages, stakeholder roles, and validation intent
       * for the increment.
       */
    }
  }

  // ─── Functional Domain ───

  concern def FunctionalBehaviorConcern {
    require constraint {
      doc /*
       * Reviewers need the functional responsibilities, information items,
       * flows, and sequencing for the feature increment to be visible
       * with requirement trace.
       */
    }
  }

  viewpoint def SystemFunctionalBreakdownStructureViewpoint {
    doc /*
     * SAF Functional Domain: System Functional Breakdown Structure Viewpoint.
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * A functional behavior view shall show functional responsibilities
       * (actions), information items, flows, and sequencing, with
       * requirement trace to functions.
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

  viewpoint def SystemInterfaceDefinitionViewpoint {
    doc /*
     * SAF Functional Domain: System Interface Definition Viewpoint.
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * A functional interface view shall show boundary port definitions,
       * their typed items, signal character, direction, and the functional
       * chain that owns the ports.
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

  viewpoint def SystemRequirementDefinitionViewpoint {
    doc /*
     * SAF Functional Domain: System Requirement Definition Viewpoint.
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * A requirement definition view shall show requirement candidates
       * with their subject, stakeholder parameters, and required constraint
       * bodies.
       */
    }
  }

  viewpoint def SystemRequirementTraceabilityViewpoint {
    doc /*
     * SAF Functional Domain: System Requirement Traceability Viewpoint.
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * A requirement traceability view shall show requirement candidates,
       * their stakeholder need sources, verification methods, and
       * satisfaction status, including explicitly unsatisfied items.
       */
    }
  }

  // ─── Logical Domain ───

  concern def LogicalStructureConcern {
    require constraint {
      doc /*
       * Reviewers need the logical system decomposition, logical element
       * responsibilities, and ownership boundaries to be visible.
       */
    }
  }

  viewpoint def LogicalStructureDefinitionViewpoint {
    doc /*
     * SAF Logical Domain: Logical Structure Definition Viewpoint.
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * A logical structure view shall show the logical system boundary and
       * its hierarchical decomposition into logical elements responsible for
       * realizing system functions.
       */
    }
  }

  concern def LogicalInternalExchangeConcern {
    require constraint {
      doc /*
       * Reviewers need the typed logical interfaces, exchanges, directions,
       * and delegation from the logical system boundary to internal elements.
       */
    }
  }

  viewpoint def LogicalInternalExchangeViewpoint {
    doc /*
     * SAF Logical Domain: Logical Internal Exchange Viewpoint.
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * A logical internal exchange view shall show the logical system
       * boundary, internal logical elements, connected interfaces, delegated
       * boundary interfaces, and exchanged logical items.
       */
    }
  }

  concern def LogicalFunctionalMappingConcern {
    require constraint {
      doc /*
       * Reviewers need every system function allocated to one or more logical
       * elements without implying a physical or software implementation.
       */
    }
  }

  viewpoint def LogicalFunctionalMappingViewpoint {
    doc /*
     * SAF Logical Domain: Logical Functional Mapping Viewpoint.
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * A logical functional mapping view shall show the allocation of system
       * functions and partial functions to logical system elements.
       */
    }
  }

  // ─── Physical Domain ───

  concern def PhysicalContextConcern {
    require constraint {
      doc /*
       * Reviewer question: What is inside the candidate physical system,
       * which external physical systems interact with it, and where is the
       * physical context boundary?
       */
    }
  }

  viewpoint def PhysicalContextDefinitionViewpoint {
    doc /*
     * SAF Physical Domain: P1_PCXD Physical Context Definition Viewpoint.
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * A physical context definition view shall show the candidate physical
       * system boundary, external physical systems, and their context roles.
       */
    }
  }

  concern def PhysicalContextExchangeConcern {
    require constraint {
      doc /*
       * Reviewer question: What typed physical items cross the candidate
       * system boundary, and which context roles participate in each exchange?
       */
    }
  }

  viewpoint def PhysicalContextExchangeViewpoint {
    doc /*
     * SAF Physical Domain: P1_PCXE Physical Context Exchange Viewpoint.
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * A physical context exchange view shall show boundary-crossing physical
       * exchanges, their typed items, and participating context roles. Textual
       * bindings and flows remain authoritative for exchange direction.
       */
    }
  }

  concern def PhysicalExchangeTypeConcern {
    require constraint {
      doc /*
       * Reviewer question: Which reusable physical exchange item, endpoint,
       * and protocol definitions type the candidate realization?
       */
    }
  }

  viewpoint def PhysicalExchangeTypeDefinitionViewpoint {
    doc /*
     * SAF Physical Domain: P2_PETD Physical Exchange Type Definition Viewpoint.
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * A physical exchange type definition view shall show reusable physical
       * item, endpoint, and protocol definitions. It shall not infer exchange
       * direction from diagram placement; typed textual features define it.
       */
    }
  }

  concern def PhysicalStructureConcern {
    require constraint {
      doc /*
       * Reviewer question: What physical hardware, software, and mechanical
       * elements make up the candidate system, and in which internal roles
       * are they used?
       */
    }
  }

  viewpoint def PhysicalStructureDefinitionViewpoint {
    doc /*
     * SAF Physical Domain: P2_PSTD Physical Structure Definition Viewpoint.
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * A physical structure definition view shall show the physical system
       * boundary and its breakdown into physical hardware, software, and
       * mechanical elements, including the roles in which elements are used.
       */
    }
  }

  concern def PhysicalInterfaceConcern {
    require constraint {
      doc /*
       * Reviewer question: Which reusable physical interface and protocol
       * definitions apply, and what typed ports and exchanged item directions
       * do they define?
       */
    }
  }

  viewpoint def PhysicalInterfaceDefinitionViewpoint {
    doc /*
     * SAF Physical Domain: P5_PIFD Physical Interface Definition Viewpoint.
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * A physical interface definition view shall show physical interface
       * definitions with typed ports, exchanged item directions, protocol
       * definitions, and compatibility or specialization relationships.
       */
    }
  }

  concern def PhysicalInternalExchangeConcern {
    require constraint {
      doc /*
       * Reviewer question: Which internal physical roles exchange each typed
       * item, and how are those exchanges delegated through boundaries?
       */
    }
  }

  viewpoint def PhysicalInternalExchangeViewpoint {
    doc /*
     * SAF Physical Domain: P4_PIEX Physical Internal Exchange Viewpoint.
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * A physical internal exchange view shall show internal physical roles,
       * typed exchanges, and boundary delegation. Textual bindings and flows
       * remain authoritative for exchange direction.
       */
    }
  }

  concern def PhysicalLogicalMappingConcern {
    require constraint {
      doc /*
       * Reviewer question: Which logical element roles are realized by which
       * physical element roles?
       */
    }
  }

  viewpoint def PhysicalLogicalMappingViewpoint {
    doc /*
     * SAF Physical Domain: P8_PLOM Physical Logical Mapping Viewpoint.
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * A physical logical mapping view shall show logical and physical
       * element breakdowns and the realization relationships that identify
       * which physical element roles implement each logical element role.
       */
    }
  }

  concern def PhysicalLogicalItemMappingConcern {
    require constraint {
      doc /*
       * Reviewer question: Which logical information items are realized by
       * which physical exchange items, and which similarly named or adjacent
       * physical items remain semantically distinct?
       */
    }
  }

  viewpoint def PhysicalLogicalItemMappingViewpoint {
    doc /*
     * Proposed SAF Physical Domain viewpoint: Physical Logical Item Mapping.
     * No short code is assigned in the current SAF catalog. This DE4SDV
     * definition is explicitly provisional.
     */
    require constraint {
      doc /*
       * A physical logical item mapping view shall show logical-to-physical
       * item allocations and explicit non-equivalence records. It shall not
       * reverse allocations or infer transport semantics from visual layout.
       */
    }
  }
}
