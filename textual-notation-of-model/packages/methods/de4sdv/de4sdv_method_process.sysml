/*
 * DE4SDV method process — iteration sequence of the DE4SDV increment workflow.
 *
 * This package models the 13-phase increment workflow from
 * methodologies/sysmod-sysmlv2/increment-workflow.md as a SysML v2 process.
 * It shows how each increment moves through the method phases and how
 * the phases chain together with feedback loops.
 *
 * The process is NOT a rigid waterfall. Iteration is expected:
 * - A later phase may expose a gap that requires returning to an earlier phase.
 * - The trace chain (concern -> need -> requirement -> architecture -> V&V)
 *   may be partially drafted and completed incrementally.
 * - Each increment produces a reviewable slice, not a complete system.
 *
 * Source: methodologies/sysmod-sysmlv2/increment-workflow.md
 */

package DE4SDV_MethodProcess {
  private import Views::*;
  private import SAF_Viewpoints::*;
  private import DE4SDV_Stakeholders::*;

  /* ─── Method phases ─── */

  enumeration def MethodPhase {
    doc /* The 13 phases of the DE4SDV increment workflow. */;

    phase0_incrementFraming = 0 {
      doc /* What are we changing or learning? Common domain. */;
    }
    phase1_concernFraming = 1 {
      doc /* Who cares and why? Common/Operational domain. */;
    }
    phase2_operationalContext = 2 {
      doc /* What happens in the world? Operational domain. */;
    }
    phase3_capabilityClassification = 3 {
      doc /* Feature, common capability, constraint, or evidence? DE4SDV ontology. */;
    }
    phase4_needs = 4 {
      doc /* What stakeholder needs exist? Operational domain. */;
    }
    phase5_requirements = 5 {
      doc /* What shall the system do? Functional domain. */;
    }
    phase6_functionalArchitecture = 6 {
      doc /* What functions, flows, states, interfaces? Functional domain. */;
    }
    phase7_logicalArchitecture = 7 {
      doc /* What logical elements realize functions? Logical domain. */;
    }
    phase8_physicalRealization = 8 {
      doc /* What software/hardware realizes the logical design? Physical domain. */;
    }
    phase9_variabilityConfiguration = 9 {
      doc /* How does this vary across member products? DE4SDV product-line layer. */;
    }
    phase10_vvEvidence = 10 {
      doc /* How will satisfaction be checked? Common/Functional domain. */;
    }
    phase11_publication = 11 {
      doc /* What is reviewable now? DE4SDV workflow. */;
    }
    phase12_baselineNextSlice = 12 {
      doc /* What is accepted, deferred, or invalidated? Common domain. */;
    }
  }

  /* ─── Phase transitions (normal flow) ─── */

  part def MethodPhaseTransition {
    doc /* A transition between two method phases. */;
    attribute fromPhase : MethodPhase;
    attribute toPhase : MethodPhase;
    attribute isForward : ScalarValues::Boolean;
    attribute isFeedback : ScalarValues::Boolean;
  }

  part def MethodProcess {
    doc /*
     * The DE4SDV increment workflow process. Each increment traverses
     * phases 0 through 12. Forward transitions produce artifacts.
     * Feedback transitions return to earlier phases when gaps are found.
     *;

    attribute currentPhase : MethodPhase = MethodPhase::phase0_incrementFraming;

    /* Normal forward sequence */
    transition phase0to1 {
      from MethodProcess::currentPhase = MethodPhase::phase0_incrementFraming
      to MethodProcess::currentPhase = MethodPhase::phase1_concernFraming;
    }
    transition phase1to2 {
      from MethodProcess::currentPhase = MethodPhase::phase1_concernFraming
      to MethodProcess::currentPhase = MethodPhase::phase2_operationalContext;
    }
    transition phase2to3 {
      from MethodProcess::currentPhase = MethodPhase::phase2_operationalContext
      to MethodProcess::currentPhase = MethodPhase::phase3_capabilityClassification;
    }
    transition phase3to4 {
      from MethodProcess::currentPhase = MethodPhase::phase3_capabilityClassification
      to MethodProcess::currentPhase = MethodPhase::phase4_needs;
    }
    transition phase4to5 {
      from MethodProcess::currentPhase = MethodPhase::phase4_needs
      to MethodProcess::currentPhase = MethodPhase::phase5_requirements;
    }
    transition phase5to6 {
      from MethodProcess::currentPhase = MethodPhase::phase5_requirements
      to MethodProcess::currentPhase = MethodPhase::phase6_functionalArchitecture;
    }
    transition phase6to7 {
      from MethodProcess::currentPhase = MethodPhase::phase6_functionalArchitecture
      to MethodProcess::currentPhase = MethodPhase::phase7_logicalArchitecture;
    }
    transition phase7to8 {
      from MethodProcess::currentPhase = MethodPhase::phase7_logicalArchitecture
      to MethodProcess::currentPhase = MethodPhase::phase8_physicalRealization;
    }
    transition phase8to9 {
      from MethodProcess::currentPhase = MethodPhase::phase8_physicalRealization
      to MethodProcess::currentPhase = MethodPhase::phase9_variabilityConfiguration;
    }
    transition phase9to10 {
      from MethodProcess::currentPhase = MethodPhase::phase9_variabilityConfiguration
      to MethodProcess::currentPhase = MethodPhase::phase10_vvEvidence;
    }
    transition phase10to11 {
      from MethodProcess::currentPhase = MethodPhase::phase10_vvEvidence
      to MethodProcess::currentPhase = MethodPhase::phase11_publication;
    }
    transition phase11to12 {
      from MethodProcess::currentPhase = MethodPhase::phase11_publication
      to MethodProcess::currentPhase = MethodPhase::phase12_baselineNextSlice;
    }

    /* Feedback transitions — when gaps are found, return to earlier phases */
    transition feedbackToOperational {
      doc /* If requirements expose unknown operational scenarios, return to phase 2. */;
      from MethodProcess::currentPhase = MethodPhase::phase5_requirements
      to MethodProcess::currentPhase = MethodPhase::phase2_operationalContext;
    }
    transition feedbackToNeeds {
      doc /* If functional architecture reveals missing needs, return to phase 4. */;
      from MethodProcess::currentPhase = MethodPhase::phase6_functionalArchitecture
      to MethodProcess::currentPhase = MethodPhase::phase4_needs;
    }
    transition feedbackToRequirements {
      doc /* If logical architecture reveals missing requirements, return to phase 5. */;
      from MethodProcess::currentPhase = MethodPhase::phase7_logicalArchitecture
      to MethodProcess::currentPhase = MethodPhase::phase5_requirements;
    }
    transition feedbackToFunctional {
      doc /* If physical realization reveals functional gaps, return to phase 6. */;
      from MethodProcess::currentPhase = MethodPhase::phase8_physicalRealization
      to MethodProcess::currentPhase = MethodPhase::phase6_functionalArchitecture;
    }
    transition feedbackToLogical {
      doc /* If V&V evidence reveals logical allocation gaps, return to phase 7. */;
      from MethodProcess::currentPhase = MethodPhase::phase10_vvEvidence
      to MethodProcess::currentPhase = MethodPhase::phase7_logicalArchitecture;
    }
  }

  /* ─── SAF domain mapping ─── */

  part def SAFDomainMapping {
    doc /* Maps each method phase to its SAF domain. */;
    attribute phase0 : MethodPhase = MethodPhase::phase0_incrementFraming;
    attribute phase0Domain : ScalarValues::String = "Common";
    attribute phase1 : MethodPhase = MethodPhase::phase1_concernFraming;
    attribute phase1Domain : ScalarValues::String = "Common/Operational";
    attribute phase2 : MethodPhase = MethodPhase::phase2_operationalContext;
    attribute phase2Domain : ScalarValues::String = "Operational";
    attribute phase3 : MethodPhase = MethodPhase::phase3_capabilityClassification;
    attribute phase3Domain : ScalarValues::String = "DE4SDV ontology";
    attribute phase4 : MethodPhase = MethodPhase::phase4_needs;
    attribute phase4Domain : ScalarValues::String = "Operational";
    attribute phase5 : MethodPhase = MethodPhase::phase5_requirements;
    attribute phase5Domain : ScalarValues::String = "Functional";
    attribute phase6 : MethodPhase = MethodPhase::phase6_functionalArchitecture;
    attribute phase6Domain : ScalarValues::String = "Functional";
    attribute phase7 : MethodPhase = MethodPhase::phase7_logicalArchitecture;
    attribute phase7Domain : ScalarValues::String = "Logical";
    attribute phase8 : MethodPhase = MethodPhase::phase8_physicalRealization;
    attribute phase8Domain : ScalarValues::String = "Physical";
    attribute phase9 : MethodPhase = MethodPhase::phase9_variabilityConfiguration;
    attribute phase9Domain : ScalarValues::String = "DE4SDV product-line";
    attribute phase10 : MethodPhase = MethodPhase::phase10_vvEvidence;
    attribute phase10Domain : ScalarValues::String = "Common/Functional";
    attribute phase11 : MethodPhase = MethodPhase::phase11_publication;
    attribute phase11Domain : ScalarValues::String = "DE4SDV workflow";
    attribute phase12 : MethodPhase = MethodPhase::phase12_baselineNextSlice;
    attribute phase12Domain : ScalarValues::String = "Common";
  }

  /* ─── Required trace chain ─── */

  item def TraceLink {
    doc /* A traceability link in the DE4SDV required trace chain. */;
    attribute fromElement : ScalarValues::String;
    attribute toElement : ScalarValues::String;
    attribute status : ScalarValues::String = "draft";
  }

  part def RequiredTraceChain {
    doc /*
     * Every substantial increment should establish this chain, even if
     * some links are draft:
     *
     * Stakeholder concern
     *   -> Need
     *   -> Requirement / constraint
     *   -> Feature or common capability
     *   -> Architecture element / function / interface
     *   -> Verification case and validation scenario
     *   -> Acceptance criterion
     *   -> Evidence artifact and evidence status
     *   -> Baseline or release decision
     *
     * If a link is intentionally missing, record the gap.
     */;
    part concernToNeed : TraceLink {
      attribute fromElement redefines TraceLink::fromElement = "StakeholderConcern";
      attribute toElement redefines TraceLink::toElement = "Need";
    }
    part needToRequirement : TraceLink {
      attribute fromElement redefines TraceLink::fromElement = "Need";
      attribute toElement redefines TraceLink::toElement = "Requirement";
    }
    part requirementToFeature : TraceLink {
      attribute fromElement redefines TraceLink::fromElement = "Requirement";
      attribute toElement redefines TraceLink::toElement = "FeatureOrCommonCapability";
    }
    part featureToArchitecture : TraceLink {
      attribute fromElement redefines TraceLink::fromElement = "FeatureOrCommonCapability";
      attribute toElement redefines TraceLink::toElement = "ArchitectureElement";
    }
    part architectureToVerification : TraceLink {
      attribute fromElement redefines TraceLink::fromElement = "ArchitectureElement";
      attribute toElement redefines TraceLink::toElement = "VerificationCase";
    }
    part verificationToAcceptance : TraceLink {
      attribute fromElement redefines TraceLink::fromElement = "VerificationCase";
      attribute toElement redefines TraceLink::toElement = "AcceptanceCriterion";
    }
    part acceptanceToEvidence : TraceLink {
      attribute fromElement redefines TraceLink::fromElement = "AcceptanceCriterion";
      attribute toElement redefines TraceLink::toElement = "EvidenceArtifact";
    }
    part evidenceToBaseline : TraceLink {
      attribute fromElement redefines TraceLink::fromElement = "EvidenceArtifact";
      attribute toElement redefines TraceLink::toElement = "BaselineDecision";
    }
  }

  /* ─── Increment size guidance ─── */

  enumeration def IncrementSize {
    XS {
      doc /* One correction or trace link. */;
    }
    S {
      doc /* One feature/scenario/context slice. */;
    }
    M {
      doc /* Cross-viewpoint increment. */;
    }
    L {
      doc /* End-to-end feature baseline. */;
    }
  }

  /* ─── Assurance view for the method process itself ─── */

  concern methodProcessAssuranceConcern : ArgumentationAssuranceConcern {
    doc /*
     * Reviewers need the DE4SDV method process to be visible: phases,
     * transitions, feedback loops, SAF domain mapping, required trace
     * chain, and increment size guidance.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view methodProcessView {
    viewpoint selectedMethodProcessAssuranceViewpoint : ArgumentationAssuranceViewpoint {
      frame methodProcessAssuranceConcern;
    }

    expose DE4SDV_MethodProcess::*;
    render asTreeDiagram;
  }
}
