/*
 * GfSE SAF viewpoint and concern definitions used by DE4SDV.
 *
 * Source: https://saf.gfse.org/userdoc/viewpoints.html
 * Repository: https://github.com/GfSE/SAF-SysMLV2
 * License: Apache-2.0
 *
 * This package is a source-backed reference catalogue, not a vendored copy.
 * DE4SDV-specific method-governance viewpoints remain in
 * DE4SDV_MethodViewpoints, not here.
 */

package SAF_Viewpoints {
  private import Views::*;

  // ─── Common Domain ───

  concern def CommonTermsConcern {
    require constraint {
      doc /*
       * Reviewers need terms introduced by an increment to be defined
       * in a glossary or terminology section.
       */
    }
  }

  viewpoint def CommonTermsDefinitionViewpoint {
    doc /*
     * SAF Common Domain: Common Terms Definition Viewpoint.
     * Aspect: Traceability & Mapping
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * A common terms view shall define terms introduced by the
       * increment in a glossary or terminology section.
       */
    }
  }

  concern def CommonStandardsConcern {
    require constraint {
      doc /*
       * Reviewers need standards and regulations used as constraints
       * or references to be registered with source attribution.
       */
    }
  }

  viewpoint def CommonStandardsDefinitionViewpoint {
    doc /*
     * SAF Common Domain: Common Standards Definition Viewpoint.
     * Aspect: Traceability & Mapping
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * A common standards view shall register standards, regulations,
       * and external references used as constraints with source
       * attribution and scope notes.
       */
    }
  }

  concern def EATraceabilityConcern {
    require constraint {
      doc /*
       * Reviewers need increment artifacts linked together in a
       * traceability chain from needs to evidence.
       */
    }
  }


  concern def StakeholderIdentificationConcern {
    require constraint {
      doc /*
       * Reviewers need roles affected by the increment to be
       * identified with their concerns.
       */
    }
  }

  viewpoint def StakeholderIdentificationViewpoint {
    doc /*
     * SAF Common Domain: Stakeholder Identification Viewpoint.
     * Aspect: Context & Exchange
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * A stakeholder identification view shall identify roles
       * affected by the increment and their concerns.
       */
    }
  }

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
     * Aspect: Context & Exchange
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

  concern def OperationalStoryConcern {
    require constraint {
      doc /*
       * Reviewers need the operational scenario told in stakeholder
       * language to validate fitness-for-use intent.
       */
    }
  }

  viewpoint def OperationalStoryViewpoint {
    doc /*
     * SAF Operational Domain: Operational Story Viewpoint.
     * Aspect: Interaction & Collaboration
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * An operational story view shall tell the scenario in
       * stakeholder language, connecting operational context to
       * validation intent.
       */
    }
  }

  concern def OperationalCapabilityConcern {
    require constraint {
      doc /*
       * Reviewers need the operational capability expected from the
       * product line to be described for the increment.
       */
    }
  }

  viewpoint def OperationalCapabilityDefinitionViewpoint {
    doc /*
     * SAF Operational Domain: Operational Capability Definition Viewpoint.
     * Aspect: Process & Behavior
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * An operational capability view shall describe the operational
       * capability expected from the product line for the increment.
       */
    }
  }

  concern def OperationalProcessConcern {
    require constraint {
      doc /*
       * Reviewers need the operational flow or lifecycle process to be
       * described for the increment.
       */
    }
  }

  viewpoint def OperationalProcessViewpoint {
    doc /*
     * SAF Operational Domain: Operational Process Viewpoint.
     * Aspect: Process & Behavior
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * An operational process view shall describe the operational
       * flow or lifecycle process for the increment.
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
     * Aspect: Traceability & Mapping
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

  concern def SystemContextConcern {
    require constraint {
      doc /*
       * Reviewers need the system boundary and external interfaces to
       * be defined for the increment.
       */
    }
  }


  concern def SystemUseCaseConcern {
    require constraint {
      doc /*
       * Reviewers need system use cases captured for the increment.
       */
    }
  }

  viewpoint def SystemUseCaseViewpoint {
    doc /*
     * SAF Functional Domain: System Use Case Viewpoint.
     * Aspect: Interaction & Collaboration
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * A system use case view shall capture system use cases with
       * actors and objectives.
       */
    }
  }

  concern def SystemCapabilityConcern {
    require constraint {
      doc /*
       * Reviewers need system capabilities defined for the increment.
       */
    }
  }

  viewpoint def SystemCapabilityDefinitionViewpoint {
    doc /*
     * SAF Functional Domain: System Capability Definition Viewpoint.
     * Aspect: Process & Behavior
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * A system capability view shall define system capabilities
       * and their relationships.
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

  viewpoint def SystemFunctionalBreakdownStructureViewpoint {
    doc /*
     * SAF Functional Domain: System Functional Breakdown Structure Viewpoint.
     * Aspect: Process & Behavior
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

  concern def SystemProcessConcern {
    require constraint {
      doc /*
       * Reviewers need behavior and process sequencing described for
       * the increment.
       */
    }
  }

  viewpoint def SystemProcessViewpoint {
    doc /*
     * SAF Functional Domain: System Process Viewpoint.
     * Aspect: Process & Behavior
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * A system process view shall describe behavior and process
       * sequencing for the increment, including state transitions
       * and temporal ordering.
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
     * Aspect: Interaction & Collaboration
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
     * Aspect: Traceability & Mapping
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
     * Aspect: Traceability & Mapping
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
     * Aspect: Taxonomy & Structure
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
     * Aspect: Interaction & Collaboration
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

  concern def LogicalInternalInteractionConcern {
    require constraint {
      doc /*
       * Reviewers need logical interactions (sequences, message ordering)
       * described for the increment.
       */
    }
  }

  viewpoint def LogicalInternalInteractionViewpoint {
    doc /*
     * SAF Logical Domain: Logical Internal Interaction Viewpoint.
     * Aspect: Interaction & Collaboration
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * A logical internal interaction view shall show interactions
       * between logical elements, including message sequencing and
       * temporal relationships.
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
     * Aspect: Process & Behavior
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
     * Aspect: Context & Exchange
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
     * Aspect: Context & Exchange
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
     * Aspect: Taxonomy & Structure
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
     * Aspect: Interaction & Collaboration
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
     * Aspect: Interaction & Collaboration
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

  concern def PhysicalFunctionalMappingConcern {
    require constraint {
      doc /*
       * Reviewer question: Which physical/software elements realize which
       * system functions?
       */
    }
  }

  viewpoint def PhysicalFunctionalMappingViewpoint {
    doc /*
     * SAF Physical Domain: P8_PFUM Physical Functional Mapping Viewpoint.
     * Aspect: Process & Behavior
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * A physical functional mapping view shall show the allocation of
       * system functions to physical/software elements, including partial
       * and missing realizations.
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
     * Aspect: Traceability & Mapping
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


  // ─── Safety/Security Domain ───

  concern def AssetIdentificationConcern {
    require constraint {
      doc /*
       * Reviewers need assets affected by the feature or toolchain to be
       * identified for safety and security analysis.
       */
    }
  }

  viewpoint def AssetIdentificationViewpoint {
    doc /*
     * SAF Safety/Security Domain: Asset Identification Viewpoint.
     * Aspect: Safety & Security
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * An asset identification view shall identify assets affected by
       * the feature or toolchain, including safety-relevant and
       * security-relevant assets.
       */
    }
  }

  concern def SecurityContextConcern {
    require constraint {
      doc /*
       * Reviewers need the security boundary and context identified for
       * the increment.
       */
    }
  }

  viewpoint def SecurityContextViewpoint {
    doc /*
     * SAF Safety/Security Domain: Security Context Viewpoint.
     * Aspect: Safety & Security
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * A security context view shall identify the security boundary,
       * trusted/untrusted domains, and security-relevant context roles.
       */
    }
  }

  concern def SecurityRiskAnalysisConcern {
    require constraint {
      doc /*
       * Reviewers need threat and risk analysis captured for the increment.
       */
    }
  }

  viewpoint def SecurityRiskAnalysisViewpoint {
    doc /*
     * SAF Safety/Security Domain: Security Risk Analysis Viewpoint.
     * Aspect: Safety & Security
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * A security risk analysis view shall capture threats, risks,
       * mitigations, and residual risk for the increment.
       */
    }
  }

  concern def ThreatSzenarioConcern {
    require constraint {
      doc /*
       * Reviewers need threat scenarios described for the increment.
       */
    }
  }

  viewpoint def ThreatSzenarioViewpoint {
    doc /*
     * SAF Safety/Security Domain: Threat Szenario Viewpoint.
     * Aspect: Safety & Security
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * A threat scenario view shall describe threat scenarios with
       * attack vectors, affected assets, and potential impacts.
       */
    }
  }

  concern def ArgumentationAssuranceConcern {
    require constraint {
      doc /*
       * Reviewers need claims, arguments, evidence, and gaps linked
       * in an assurance argument for the increment.
       */
    }
  }

  viewpoint def ArgumentationAssuranceViewpoint {
    doc /*
     * SAF Safety/Security Domain: Argumentation Assurance Viewpoint.
     * Aspect: Traceability & Mapping
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     */
    require constraint {
      doc /*
       * An argumentation assurance view shall link claims, arguments,
       * evidence, and gaps in an assurance argument structure.
       */
    }
  }

  // ─── GfSE SAF-SysMLV2 additions ───
  concern def ImpactAnalysisConcern {
    require constraint {
      doc /*
       * Reviewers need ImpactAnalysisViewpoint captured with source-backed frame bindings for the increment.
       */
    }
  }

  viewpoint def ImpactAnalysisViewpoint {
    doc /*
     * SAF Safety/Security Domain: ImpactAnalysis Viewpoint
     * Aspect: Safety & Security
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     * GfSE frame bindings: SeverityOfLoss.
     */
    require constraint {
      doc /*
       * A ImpactAnalysisViewpoint view shall show the source-backed SAF frame bindings for the increment.
       */
    }
  }
  concern def OperationalDomainItemKindConcern {
    require constraint {
      doc /*
       * Reviewers need OperationalDomainItemKindViewpoint captured with source-backed frame bindings for the increment.
       */
    }
  }

  viewpoint def OperationalDomainItemKindViewpoint {
    doc /*
     * SAF Operational Domain: OperationalDomainItemKind Viewpoint
     * Aspect: Taxonomy & Structure
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     * GfSE frame bindings: OperationalExchanges.
     */
    require constraint {
      doc /*
       * A OperationalDomainItemKindViewpoint view shall show the source-backed SAF frame bindings for the increment.
       */
    }
  }
  concern def SystemContextInteractionConcern {
    require constraint {
      doc /*
       * Reviewers need SystemContextInteractionViewpoint captured with source-backed frame bindings for the increment.
       */
    }
  }

  viewpoint def SystemContextInteractionViewpoint {
    doc /*
     * SAF Functional Domain: SystemContextInteraction Viewpoint
     * Aspect: Context & Exchange
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     * GfSE frame bindings: SystemUtilization, ResponseTimeRequirements, ConceptualInteractionSequence.
     */
    require constraint {
      doc /*
       * A SystemContextInteractionViewpoint view shall show the source-backed SAF frame bindings for the increment.
       */
    }
  }
  concern def OperationalContextExchangeConcern {
    require constraint {
      doc /*
       * Reviewers need OperationalContextExchangeViewpoint captured with source-backed frame bindings for the increment.
       */
    }
  }

  viewpoint def OperationalContextExchangeViewpoint {
    doc /*
     * SAF Operational Domain: OperationalContextExchange Viewpoint
     * Aspect: Context & Exchange
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     * GfSE frame bindings: OperationalContextExchanges.
     */
    require constraint {
      doc /*
       * A OperationalContextExchangeViewpoint view shall show the source-backed SAF frame bindings for the increment.
       */
    }
  }
  concern def SystemDomainItemKindConcern {
    require constraint {
      doc /*
       * Reviewers need SystemDomainItemKindViewpoint captured with source-backed frame bindings for the increment.
       */
    }
  }

  viewpoint def SystemDomainItemKindViewpoint {
    doc /*
     * SAF Functional Domain: SystemDomainItemKind Viewpoint
     * Aspect: Taxonomy & Structure
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     * GfSE frame bindings: LogicalArchitectureItems.
     */
    require constraint {
      doc /*
       * A SystemDomainItemKindViewpoint view shall show the source-backed SAF frame bindings for the increment.
       */
    }
  }
  concern def SystemFunctionalRefinementConcern {
    require constraint {
      doc /*
       * Reviewers need SystemFunctionalRefinementViewpoint captured with source-backed frame bindings for the increment.
       */
    }
  }

  viewpoint def SystemFunctionalRefinementViewpoint {
    doc /*
     * SAF Functional Domain: SystemFunctionalRefinement Viewpoint
     * Aspect: Process & Behavior
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     * GfSE frame bindings: SubfunctionInteractions, SystemFunctionBreakdown, SystemFunctionDecomposition.
     */
    require constraint {
      doc /*
       * A SystemFunctionalRefinementViewpoint view shall show the source-backed SAF frame bindings for the increment.
       */
    }
  }
  concern def SystemStateConcern {
    require constraint {
      doc /*
       * Reviewers need SystemStateViewpoint captured with source-backed frame bindings for the increment.
       */
    }
  }

  viewpoint def SystemStateViewpoint {
    doc /*
     * SAF Functional Domain: SystemState Viewpoint
     * Aspect: Taxonomy & Structure
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     * GfSE frame bindings: SystemModes, SystemFunctionsDependentOnModes.
     */
    require constraint {
      doc /*
       * A SystemStateViewpoint view shall show the source-backed SAF frame bindings for the increment.
       */
    }
  }
  concern def OperationalContextInteractionConcern {
    require constraint {
      doc /*
       * Reviewers need OperationalContextInteractionViewpoint captured with source-backed frame bindings for the increment.
       */
    }
  }

  viewpoint def OperationalContextInteractionViewpoint {
    doc /*
     * SAF Operational Domain: OperationalContextInteraction Viewpoint
     * Aspect: Context & Exchange
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     * GfSE frame bindings: OperationalProcessThreads.
     */
    require constraint {
      doc /*
       * A OperationalContextInteractionViewpoint view shall show the source-backed SAF frame bindings for the increment.
       */
    }
  }
  concern def GridDefinitionConcern {
    require constraint {
      doc /*
       * Reviewers need GridDefinitionViewpoint captured with source-backed frame bindings for the increment.
       */
    }
  }

  viewpoint def GridDefinitionViewpoint {
    doc /*
     * SAF Functional Domain: GridDefinition Viewpoint
     * Aspect: Traceability & Mapping
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     * GfSE frame bindings: ViewpointsUsedInSystemModel, FrameworkViewpoints.
     */
    require constraint {
      doc /*
       * A GridDefinitionViewpoint view shall show the source-backed SAF frame bindings for the increment.
       */
    }
  }
  concern def FrameworkConceptDefinitionConcern {
    require constraint {
      doc /*
       * Reviewers need FrameworkConceptDefinitionViewpoint captured with source-backed frame bindings for the increment.
       */
    }
  }

  viewpoint def FrameworkConceptDefinitionViewpoint {
    doc /*
     * SAF Framework Domain: FrameworkConceptDefinition Viewpoint
     * Aspect: SAF Development Domain
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     * GfSE frame bindings: RelationsBetweenSEConcepts, ConstraintsOnSEConcepts, SEConceptsCovered.
     */
    require constraint {
      doc /*
       * A FrameworkConceptDefinitionViewpoint view shall show the source-backed SAF frame bindings for the increment.
       */
    }
  }
  concern def FrameworkConcernOverviewConcern {
    require constraint {
      doc /*
       * Reviewers need FrameworkViewpointOverviewViewpoint captured with source-backed frame bindings for the increment.
       */
    }
  }

  viewpoint def FrameworkViewpointOverviewViewpoint {
    doc /*
     * SAF Framework Domain: Framework ViewpointOverview Viewpoint
     * Aspect: SAF Development Domain
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     * GfSE frame bindings: DefinitionOfGridRows, DefinitionOfGridColumns, FrameworkGridStructure, ViewpointLocationInGrid, MaturityOfViewpoints, AvailableViewpoints.
     */
    require constraint {
      doc /*
       * A FrameworkViewpointOverviewViewpoint view shall show the source-backed SAF frame bindings for the increment.
       */
    }
  }
  concern def FrameworkStakeholderandConcernDefinitionConcern {
    require constraint {
      doc /*
       * Reviewers need FrameworkStakeholderandConcernDefinitionViewpoint captured with source-backed frame bindings for the increment.
       */
    }
  }

  viewpoint def FrameworkStakeholderandConcernDefinitionViewpoint {
    doc /*
     * SAF Framework Domain: FrameworkStakeholderandConcernDefinition Viewpoint
     * Aspect: SAF Development Domain
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     * GfSE frame bindings: StakeholderConcerns, FrameworkStakeholders, StakeholderConcernsReasons.
     */
    require constraint {
      doc /*
       * A FrameworkStakeholderandConcernDefinitionViewpoint view shall show the source-backed SAF frame bindings for the increment.
       */
    }
  }
  concern def FrameworkConcernDefinitionConcern {
    require constraint {
      doc /*
       * Reviewers need FrameworkViewpointDefinitionViewpoint captured with source-backed frame bindings for the increment.
       */
    }
  }

  viewpoint def FrameworkViewpointDefinitionViewpoint {
    doc /*
     * SAF Framework Domain: Framework ViewpointDefinition Viewpoint
     * Aspect: SAF Development Domain
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     * GfSE frame bindings: ConceptsExposedInViewpoints, ConcernsFramedByViewpoints, DefinitionOfViewpoints, ViewpointLocationInGrid, ViewpointPurpose, ViewpointPresentations, ViewpointDependencies, SupportForSEStandards.
     */
    require constraint {
      doc /*
       * A FrameworkViewpointDefinitionViewpoint view shall show the source-backed SAF frame bindings for the increment.
       */
    }
  }
  concern def FrameworkConcernImplementationConcern {
    require constraint {
      doc /*
       * Reviewers need FrameworkViewpointImplementationViewpoint captured with source-backed frame bindings for the increment.
       */
    }
  }

  viewpoint def FrameworkViewpointImplementationViewpoint {
    doc /*
     * SAF Framework Domain: Framework ViewpointImplementation Viewpoint
     * Aspect: SAF Development Domain
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     * GfSE frame bindings: ImplementationOfFrameworkConcepts, ViewpointImplementation.
     */
    require constraint {
      doc /*
       * A FrameworkViewpointImplementationViewpoint view shall show the source-backed SAF frame bindings for the increment.
       */
    }
  }
  concern def FrameworkImplementationTraceabilityConcern {
    require constraint {
      doc /*
       * Reviewers need FrameworkImplementationTraceabilityViewpoint captured with source-backed frame bindings for the increment.
       */
    }
  }

  viewpoint def FrameworkImplementationTraceabilityViewpoint {
    doc /*
     * SAF Framework Domain: FrameworkImplementationTraceability Viewpoint
     * Aspect: SAF Development Domain
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     * GfSE frame bindings: ImplementationOfFrameworkConcepts, FrameworkModelElements.
     */
    require constraint {
      doc /*
       * A FrameworkImplementationTraceabilityViewpoint view shall show the source-backed SAF frame bindings for the increment.
       */
    }
  }
  concern def FrameworkStereotypeOverviewConcern {
    require constraint {
      doc /*
       * Reviewers need FrameworkStereotypeOverviewViewpoint captured with source-backed frame bindings for the increment.
       */
    }
  }

  viewpoint def FrameworkStereotypeOverviewViewpoint {
    doc /*
     * SAF Framework Domain: FrameworkStereotypeOverview Viewpoint
     * Aspect: SAF Development Domain
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     * GfSE frame bindings: FrameworkModelElements.
     */
    require constraint {
      doc /*
       * A FrameworkStereotypeOverviewViewpoint view shall show the source-backed SAF frame bindings for the increment.
       */
    }
  }
  concern def OperationalPerformerConcern {
    require constraint {
      doc /*
       * Reviewers need OperationalPerformerViewpoint captured with source-backed frame bindings for the increment.
       */
    }
  }

  viewpoint def OperationalPerformerViewpoint {
    doc /*
     * SAF Operational Domain: OperationalPerformer Viewpoint
     * Aspect: Taxonomy & Structure
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     * GfSE frame bindings: OrganizationalEntitiesForCapability, RelationshipsBetweenParties.
     */
    require constraint {
      doc /*
       * A OperationalPerformerViewpoint view shall show the source-backed SAF frame bindings for the increment.
       */
    }
  }
  concern def OperationalCapabilityMappingConcern {
    require constraint {
      doc /*
       * Reviewers need OperationalCapabilityMappingViewpoint captured with source-backed frame bindings for the increment.
       */
    }
  }

  viewpoint def OperationalCapabilityMappingViewpoint {
    doc /*
     * SAF Operational Domain: OperationalCapabilityMapping Viewpoint
     * Aspect: Process & Behavior
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     * GfSE frame bindings: OperationalCapabilityRelationships.
     */
    require constraint {
      doc /*
       * A OperationalCapabilityMappingViewpoint view shall show the source-backed SAF frame bindings for the increment.
       */
    }
  }
  concern def OperationalProcessMappingConcern {
    require constraint {
      doc /*
       * Reviewers need OperationalProcessMappingViewpoint captured with source-backed frame bindings for the increment.
       */
    }
  }

  viewpoint def OperationalProcessMappingViewpoint {
    doc /*
     * SAF Operational Domain: OperationalProcessMapping Viewpoint
     * Aspect: Process & Behavior
     * Source: https://saf.gfse.org/userdoc/viewpoints.html
     * GfSE frame bindings: OperationalProcessRelationships.
     */
    require constraint {
      doc /*
       * A OperationalProcessMappingViewpoint view shall show the source-backed SAF frame bindings for the increment.
       */
    }
  }
}
