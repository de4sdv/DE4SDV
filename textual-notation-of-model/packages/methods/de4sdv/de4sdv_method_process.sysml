/*
 * DE4SDV method process — iteration sequence of the DE4SDV increment workflow.
 *
 * This package models the 13-phase increment workflow from
 * methodologies/sysmod-sysmlv2/increment-workflow.md as a SysML v2 model.
 * The phase sequence and feedback loops are documented in
 * methodologies/sysmod-sysmlv2/process-mapping.md (PR #74) as a mermaid
 * diagram. This SysML model provides the structured data: phase enumeration,
 * SAF domain mapping, required trace chain, recurring logical-to-software
 * signal-mapping control, and increment size guidance.
 *
 * Source: methodologies/sysmod-sysmlv2/increment-workflow.md
 *         methodologies/sysmod-sysmlv2/process-mapping.md
 */

package DE4SDV_MethodProcess {
  private import Views::*;
  private import SAF_Viewpoints::*;
  private import DE4SDV_Stakeholders::*;

  /* ─── Method phases ─── */

  enum def MethodPhase {
    doc /* The 13 phases of the DE4SDV increment workflow. */

    phase0_incrementFraming {
      doc /* What are we changing or learning? Common domain. */
    }
    phase1_concernFraming {
      doc /* Who cares and why? Common/Operational domain. */
    }
    phase2_operationalContext {
      doc /* What happens in the world? Operational domain. */
    }
    phase3_capabilityClassification {
      doc /* Feature, common capability, constraint, or evidence? DE4SDV ontology. */
    }
    phase4_needs {
      doc /* What stakeholder needs exist? Operational domain. */
    }
    phase5_requirements {
      doc /* What shall the system do? Conceptual domain. */
    }
    phase6_functionalArchitecture {
      doc /* What functions, flows, states, interfaces? Conceptual domain. */
    }
    phase7_logicalArchitecture {
      doc /* What system elements realize functions? Conceptual domain. */
    }
    phase8_physicalRealization {
      doc /* What software/hardware realizes the logical design, and which applicable logical or semantic signals cross into typed software contracts? Physical domain. */
    }
    phase9_variabilityConfiguration {
      doc /* How does this vary across member products? DE4SDV product-line layer. */
    }
    phase10_vvEvidence {
      doc /* How will satisfaction be checked? Common/Conceptual domain. */
    }
    phase11_publication {
      doc /* What is reviewable now? DE4SDV workflow. */
    }
    phase12_baselineNextSlice {
      doc /* What is accepted, deferred, or invalidated? Common domain. */
    }
  }

  /* ─── SAF domain mapping ─── */

  part def SAFDomainMapping {
    doc /* Maps each method phase to its SAF domain. */
    attribute phase0Domain : ScalarValues::String = "Common";
    attribute phase1Domain : ScalarValues::String = "Common/Operational";
    attribute phase2Domain : ScalarValues::String = "Operational";
    attribute phase3Domain : ScalarValues::String = "DE4SDV ontology";
    attribute phase4Domain : ScalarValues::String = "Operational";
    attribute phase5Domain : ScalarValues::String = "Conceptual";
    attribute phase6Domain : ScalarValues::String = "Conceptual";
    attribute phase7Domain : ScalarValues::String = "Conceptual";
    attribute phase8Domain : ScalarValues::String = "Physical";
    attribute phase9Domain : ScalarValues::String = "DE4SDV product-line";
    attribute phase10Domain : ScalarValues::String = "Common/Conceptual";
    attribute phase11Domain : ScalarValues::String = "DE4SDV workflow";
    attribute phase12Domain : ScalarValues::String = "Common";
  }

  /* ─── Required trace chain ─── */

  item def TraceLink {
    doc /* A traceability link in the DE4SDV required trace chain. */
    attribute fromElement : ScalarValues::String;
    attribute toElement : ScalarValues::String;
    attribute status : ScalarValues::String = "draft";
  }

  part def RequiredTraceChain {
    doc /*
     * Every substantial increment should establish this chain, even if
     * some links are draft:
     *
     * Stakeholder concern -> Need -> Requirement -> Feature or common
     * capability -> Architecture element -> Logical-to-software signal
     * mapping when a boundary is crossed -> Physical/software realization ->
     * Verification case -> Acceptance criterion -> Evidence artifact ->
     * Baseline decision.
     *
     * If a link is intentionally missing, record the gap.
     */
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
    part architectureToSignalMapping : TraceLink {
      attribute fromElement redefines TraceLink::fromElement = "ArchitectureElementOrFunctionInterface";
      attribute toElement redefines TraceLink::toElement = "LogicalToSoftwareSignalMapping";
    }
    part signalMappingToPhysicalRealization : TraceLink {
      attribute fromElement redefines TraceLink::fromElement = "LogicalToSoftwareSignalMapping";
      attribute toElement redefines TraceLink::toElement = "PhysicalSoftwareRealization";
    }
    part architectureToVerification : TraceLink {
      attribute fromElement redefines TraceLink::fromElement = "PhysicalSoftwareRealization";
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

  /* ─── Recurring system-to-software signal mapping control ─── */

  enum def SignalMappingDisposition {
    mapped {
      doc /* The applicable logical/semantic signal has an accepted software-contract mapping for the declared scope. */
    }
    candidate {
      doc /* A reference or proposed contract mapping exists, but the selected platform realization remains open. */
    }
    deferred {
      doc /* The mapping is known to be needed but is intentionally postponed with an owned gap and next action. */
    }
    notApplicable {
      doc /* The signal does not cross the applicable software/physical boundary; the reason is recorded externally. */
    }
  }

  item def LogicalToSoftwareSignalMappingRecord {
    doc /*
     * Reusable control-record shape for an interface-bearing logical or
     * semantic information item crossing into a software, service, topic, API,
     * or physical boundary. Exact .proto/.vsidl fields and runtime observations
     * remain in their authoritative external artifacts; this record preserves
     * the stable trace and review obligations.
     */
    attribute mappingId : ScalarValues::String;
    attribute semanticSource : ScalarValues::String;
    attribute softwareContractArtifact : ScalarValues::String;
    attribute softwareContractMessage : ScalarValues::String;
    attribute softwareContractField : ScalarValues::String;
    attribute adapterEndpoints : ScalarValues::String;
    attribute direction : ScalarValues::String;
    attribute dataTypeAndUnit : ScalarValues::String;
    attribute timingQualityAndState : ScalarValues::String;
    attribute transformationRule : ScalarValues::String;
    attribute disposition : SignalMappingDisposition;
    attribute owner : ScalarValues::String;
    attribute nextAction : ScalarValues::String;
    attribute evidenceOrGap : ScalarValues::String;
  }

  allocation def SystemToSoftwareSignalMappingCandidate {
    doc /*
     * Reusable non-claiming allocation relationship from a logical/function
     * signal responsibility to a concrete software/adapter signal endpoint.
     * A specialization must still provide the typed payload/port, contract
     * mapping record, transformation, status, owner, next action, and evidence
     * or gap. The allocation alone never proves field identity or runtime
     * interoperability.
     */
  }

  /* ─── Increment size guidance ─── */

  enum def IncrementSize {
    XS {
      doc /* One correction or trace link. */
    }
    S {
      doc /* One feature/scenario/context slice. */
    }
    M {
      doc /* Cross-viewpoint increment. */
    }
    L {
      doc /* End-to-end feature baseline. */
    }
  }

  /* ─── Assurance view for the method process itself ─── */

  concern methodProcessAssuranceConcern : ArgumentationAssuranceConcern {
    doc /*
     * Reviewers need the DE4SDV method process to be visible: phases,
     * SAF domain mapping, required trace chain, recurring logical-to-software
     * signal-mapping control, and increment size guidance.
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
