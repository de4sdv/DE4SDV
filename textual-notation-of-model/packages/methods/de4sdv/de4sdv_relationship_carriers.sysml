/* Explicit relationship successor, non-production. Frozen O3 is unchanged.
 * Profile records below are construction inputs, never query-time source text.
 * Each class/carrier pin routes from an ingestion-validated exact source-file
 * and declaration tuple, even when the authored ontology names the extension
 * separately from its native category. Runtime never derives UUIDs by name.
 * Allocations retain responsibility assignment only; no satisfaction,
 * transitivity, execution, fulfillment, deployment or compliance is asserted.
 */
package DE4SDV_RelationshipSuccessor {
  private import ScalarValues::*;
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_OperationalContext::*;

  action def AllocatableFunction {
    doc /* Functional responsibility identity for this versioned allocation profile. */
  }
  part def LogicalAllocationElement {
    doc /* Technology-neutral logical responsibility grouping. */
  }
  part def PhysicalAllocationElement {
    doc /* Concrete software, hardware or platform realization element; allocation is not deployment. */
  }
  part def ValidationPlanningScenario :> Scenario {
    doc /* Stakeholder fitness-for-use validation planning only; not a native verification case, execution, result or acceptance. */
  }
  part def ControlledRegulatorySource {
    doc /* Controlled external origin reference that informed requirement engineering. Interpretation, applicability, obligations, required conditions, evidence and authorized compliance assessment are separate. */
    attribute sourceIdentifier : String;
    attribute sourceRevision : String;
    attribute sourceLocation : String;
  }

  connection def RequirementFunctionAssignment {
    end source : RequirementCandidate;
    end target : AllocatableFunction;
    doc /* Profile end-pair carrier only. Executable allocatedTo facts require actual native AllocationUsage responsibility assignments. No redundant dependency is required. */
  }
  connection def FunctionLogicalAssignment {
    end source : AllocatableFunction;
    end target : LogicalAllocationElement;
    doc /* Profile end-pair carrier only; actual native allocations supply the witness. */
  }
  connection def LogicalPhysicalAssignment {
    end source : LogicalAllocationElement;
    end target : PhysicalAllocationElement;
    doc /* Responsibility assignment only, not deployment or observed operation. */
  }
  connection def ValidationPlanningAssociation {
    end source : StakeholderNeedCandidate;
    end target : ValidationPlanningScenario;
    doc /* One validation planning association. Inverse navigation is the same fact, not execution or a fitness-for-use verdict. */
  }
  connection def RegulatorySourceAssociation {
    end source : RequirementCandidate;
    end target : ControlledRegulatorySource;
    doc /* Source provenance only. Does not add a required satisfaction condition or establish applicability, correct interpretation, fulfillment, certification or homologation. Historical constrainedBy was provenance, never a native required constraint. */
  }

  part def SuccessorClassRecord {
    attribute identity : String;
    attribute sourceFile : String;
    attribute declaration : String;
  }
  part def SuccessorRelationRecord {
    attribute predicate : String;
    attribute carrier : String;
    attribute mechanism : String;
    attribute strength : String;
    attribute sourceClass : String;
    attribute targetClass : String;
    attribute sourceUsage : String;
    attribute targetUsage : String;
    attribute inverse : String;
  }
  part def SuccessorRetirementRecord {
    attribute predicate : String;
    attribute reason : String;
  }
  part def SuccessorVersionRecord {
    attribute version : String;
    attribute supersedes : String;
  }
  part version : SuccessorVersionRecord {
    attribute :>> version = "de4sdv.relationship-successor/v1";
    attribute :>> supersedes = "Function-to-LogicalElement allocatedTo signature; historical provenance constrainedBy; stronger realizedBy/deployedTo active claims";
  }

  part requirementIdentity : SuccessorClassRecord {
    attribute :>> identity = "Requirement";
    attribute :>> sourceFile = "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml";
    attribute :>> declaration = "requirement def RequirementCandidate";
  }
  part needIdentity : SuccessorClassRecord {
    attribute :>> identity = "Need";
    attribute :>> sourceFile = "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml";
    attribute :>> declaration = "requirement def StakeholderNeedCandidate";
  }
  part functionIdentity : SuccessorClassRecord {
    attribute :>> identity = "Function";
    attribute :>> sourceFile = "textual-notation-of-model/packages/methods/de4sdv/de4sdv_relationship_carriers.sysml";
    attribute :>> declaration = "action def AllocatableFunction";
  }
  part logicalIdentity : SuccessorClassRecord {
    attribute :>> identity = "LogicalElement";
    attribute :>> sourceFile = "textual-notation-of-model/packages/methods/de4sdv/de4sdv_relationship_carriers.sysml";
    attribute :>> declaration = "part def LogicalAllocationElement";
  }
  part physicalIdentity : SuccessorClassRecord {
    attribute :>> identity = "PhysicalElement";
    attribute :>> sourceFile = "textual-notation-of-model/packages/methods/de4sdv/de4sdv_relationship_carriers.sysml";
    attribute :>> declaration = "part def PhysicalAllocationElement";
  }
  part validationIdentity : SuccessorClassRecord {
    attribute :>> identity = "ValidationScenario";
    attribute :>> sourceFile = "textual-notation-of-model/packages/methods/de4sdv/de4sdv_relationship_carriers.sysml";
    attribute :>> declaration = "part def ValidationPlanningScenario";
  }
  part sourceIdentity : SuccessorClassRecord {
    attribute :>> identity = "RegulatorySource";
    attribute :>> sourceFile = "textual-notation-of-model/packages/methods/de4sdv/de4sdv_relationship_carriers.sysml";
    attribute :>> declaration = "part def ControlledRegulatorySource";
  }

  part requirementAllocation : SuccessorRelationRecord {
    attribute :>> predicate = "allocatedTo";
    attribute :>> carrier = "RequirementFunctionAssignment";
    attribute :>> mechanism = "native-allocation";
    attribute :>> strength = "allocation";
    attribute :>> sourceClass = "Requirement";
    attribute :>> targetClass = "Function";
    attribute :>> sourceUsage = "RequirementUsage";
    attribute :>> targetUsage = "ActionUsage";
    attribute :>> inverse = "";
  }
  part functionAllocation : SuccessorRelationRecord {
    attribute :>> predicate = "allocatedTo";
    attribute :>> carrier = "FunctionLogicalAssignment";
    attribute :>> mechanism = "native-allocation";
    attribute :>> strength = "allocation";
    attribute :>> sourceClass = "Function";
    attribute :>> targetClass = "LogicalElement";
    attribute :>> sourceUsage = "ActionUsage";
    attribute :>> targetUsage = "PartUsage";
    attribute :>> inverse = "";
  }
  part physicalAllocation : SuccessorRelationRecord {
    attribute :>> predicate = "allocatedTo";
    attribute :>> carrier = "LogicalPhysicalAssignment";
    attribute :>> mechanism = "native-allocation";
    attribute :>> strength = "allocation";
    attribute :>> sourceClass = "LogicalElement";
    attribute :>> targetClass = "PhysicalElement";
    attribute :>> sourceUsage = "PartUsage";
    attribute :>> targetUsage = "PartUsage";
    attribute :>> inverse = "";
  }
  part validationPlanning : SuccessorRelationRecord {
    attribute :>> predicate = "hasValidationScenario";
    attribute :>> carrier = "ValidationPlanningAssociation";
    attribute :>> mechanism = "typed-connection";
    attribute :>> strength = "validation-planning";
    attribute :>> sourceClass = "Need";
    attribute :>> targetClass = "ValidationScenario";
    attribute :>> sourceUsage = "RequirementUsage";
    attribute :>> targetUsage = "PartUsage";
    attribute :>> inverse = "validationScenarioFor";
  }
  part regulatoryProvenance : SuccessorRelationRecord {
    attribute :>> predicate = "hasRegulatorySource";
    attribute :>> carrier = "RegulatorySourceAssociation";
    attribute :>> mechanism = "typed-connection";
    attribute :>> strength = "source-provenance";
    attribute :>> sourceClass = "Requirement";
    attribute :>> targetClass = "RegulatorySource";
    attribute :>> sourceUsage = "RequirementUsage";
    attribute :>> targetUsage = "PartUsage";
    attribute :>> inverse = "";
  }

  part oldRealization : SuccessorRetirementRecord {
    attribute :>> predicate = "realizedBy";
    attribute :>> reason = "Retired stronger active claim; native responsibility assignments use allocatedTo without fulfillment.";
  }
  part oldDeployment : SuccessorRetirementRecord {
    attribute :>> predicate = "deployedTo";
    attribute :>> reason = "Retired stronger active claim; no deployment assertion is invented.";
  }
  part oldRegulatoryName : SuccessorRetirementRecord {
    attribute :>> predicate = "constrainedBy";
    attribute :>> reason = "Historical source provenance, not native required conditions; controlled-source successor is hasRegulatorySource, not an alias.";
  }
  part oldValidationForward : SuccessorRetirementRecord {
    attribute :>> predicate = "validatedBy";
    attribute :>> reason = "Planning successor is hasValidationScenario; no validation result implied.";
  }
  part oldValidationInverse : SuccessorRetirementRecord {
    attribute :>> predicate = "validatesFitnessForUse";
    attribute :>> reason = "Inverse planning navigation is validationScenarioFor over the same association; not a fitness-for-use verdict.";
  }
}
