/* Explicit relationship successor, non-production. Frozen O3 is unchanged.
 * Profile records below are construction inputs, never query-time source text.
 * Relation and retirement records carry engineering semantics only (predicate,
 * carrier, mechanism, strength, endpoint classes, inverse). Endpoint class
 * pins come from the authored ontology's kernel mappings, not from file paths
 * in this model. Each class/carrier pin routes from an ingestion-validated
 * exact source-file and declaration tuple. Runtime never derives UUIDs by name.
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

  comment allocatedToVocabularyRole about RequirementFunctionAssignment, FunctionLogicalAssignment, LogicalPhysicalAssignment /* Successor
   * definition: one canonical allocatedTo predicate. A native AllocationUsage
   * assigns responsibility from its source usage to its target usage for
   * exactly one governed end pair: requirement to function, function to
   * logical element, or logical element to physical element. Endpoint
   * classes come from the ontology kernel mappings of the endpoint lineage,
   * never from usage or allocation names. Allocation proves no satisfaction,
   * execution, deployment, fulfillment or transitivity; it is not a
   * composed requirement-to-architecture realization. The superseded names
   * are realizedBy and deployedTo, and the former Function-to-LogicalElement
   * signature is the second end pair of this version. */

  comment hasValidationScenarioVocabularyRole about ValidationPlanningAssociation /* Successor
   * definition: a stakeholder need has a planned validation scenario. One
   * typed ValidationPlanningAssociation records the planning fact;
   * validationScenarioFor is inverse navigation over the same fact. It
   * records planning only: no execution, result, fitness-for-use verdict,
   * completed validation or stakeholder acceptance. Supersedes validatedBy
   * and merges validatesFitnessForUse. */

  comment hasRegulatorySourceVocabularyRole about RegulatorySourceAssociation /* Successor
   * definition: a requirement has a controlled regulatory source, recorded
   * as requirement-source provenance only. Applicability, interpretation,
   * binding requirements or required conditions, fulfillment evidence and
   * authorized compliance assessment remain distinct; provenance neither
   * makes an applicable obligation optional nor proves compliance.
   * Supersedes constrainedBy. */

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
