/*
 * DE4SDV trace vocabulary: the connection definitions and records that trace
 * engineering elements along the method chain.
 *
 * - DerivesFromNeed: a requirement derives from a stakeholder need.
 * - allocatedTo: a requirement, function or logical element is allocated to a
 *   function, logical element or physical element (native allocations).
 * - hasValidationScenario: a stakeholder need has a planned validation
 *   scenario.
 * - hasRegulatorySource: a requirement has a controlled regulatory source.
 *
 * The relation records declare each relationship's predicate, connection
 * definition, mechanism, strength, endpoint classes and inverse; the
 * retirement records name the retired relationship names and why they are
 * refused. The served trace contract is built from these records. Endpoint
 * class pins come from the generated projection layers, not from file paths in
 * this model, and every pin resolves through an ingestion-validated source file
 * and declaration, never by name. An allocation records a responsibility
 * assignment only: it asserts no satisfaction, transitivity, execution,
 * fulfillment, deployment or compliance.
 */
package DE4SDV_TraceVocabulary {
  private import ScalarValues::*;
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_OperationalContext::*;

  /* Requirement derivation discriminator: DE4SDV application connection
   * definition. A requirement usage connected as derivedRequirement
   * originates from the stakeholder need connected as need. The typed ends
   * carry the predicate's domain and range; the definition documentation
   * carries its native direction, claim strength, and claim boundary.
   * Design-input provenance only — no satisfaction, implication,
   * verification, evidence, or acceptance claim. */

  connection def DerivesFromNeed {
    private doc ontologyDefinition /* DE4SDV application connection definition for design-input derivation: the
     * derivedRequirement originates from the stakeholder need. Provenance/traceability
     * semantics only - neither satisfaction nor logical implication between the connected
     * usages is claimed. The typed connection ends (need : StakeholderNeedCandidate,
     * derivedRequirement : RequirementCandidate) carry the predicate's domain and range in
     * the model itself. The standard Requirement Derivation Domain Library remains pinned
     * but unadopted: its originalImpliesDerived semantics change the claim (upstream
     * adoption gate still applies; no floating upgrade, no upstream contact without
     * authorization). */
    end need : StakeholderNeedCandidate;
    end derivedRequirement : RequirementCandidate;
    doc /* Design-input provenance: the derivedRequirement originates from
         * the stakeholder need. Native direction: need -> derivedRequirement.
         * Claim strength: derivation (provenance only: neither satisfaction
         * nor logical implication between the connected usages; no
         * allocation, verification, evidence, or acceptance claim). */
  }

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
   * classes come from the validated kernel bindings of the endpoint lineage,
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

  part def TraceRelationRecord {
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
  part def RetiredRelationRecord {
    attribute predicate : String;
    attribute reason : String;
  }
  part def TraceVocabularyVersionRecord {
    attribute version : String;
    attribute supersedes : String;
  }
  part version : TraceVocabularyVersionRecord {
    attribute :>> version = "de4sdv.relationship-successor/v1";
    attribute :>> supersedes = "Function-to-LogicalElement allocatedTo signature; historical provenance constrainedBy; stronger realizedBy/deployedTo active claims";
  }

  part requirementAllocation : TraceRelationRecord {
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
  part functionAllocation : TraceRelationRecord {
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
  part physicalAllocation : TraceRelationRecord {
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
  part validationPlanning : TraceRelationRecord {
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
  part regulatoryProvenance : TraceRelationRecord {
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

  part oldRealization : RetiredRelationRecord {
    attribute :>> predicate = "realizedBy";
    attribute :>> reason = "Retired stronger active claim; native responsibility assignments use allocatedTo without fulfillment.";
  }
  part oldDeployment : RetiredRelationRecord {
    attribute :>> predicate = "deployedTo";
    attribute :>> reason = "Retired stronger active claim; no deployment assertion is invented.";
  }
  part oldRegulatoryName : RetiredRelationRecord {
    attribute :>> predicate = "constrainedBy";
    attribute :>> reason = "Historical source provenance, not native required conditions; controlled-source successor is hasRegulatorySource, not an alias.";
  }
  part oldValidationForward : RetiredRelationRecord {
    attribute :>> predicate = "validatedBy";
    attribute :>> reason = "Planning successor is hasValidationScenario; no validation result implied.";
  }
  part oldValidationInverse : RetiredRelationRecord {
    attribute :>> predicate = "validatesFitnessForUse";
    attribute :>> reason = "Inverse planning navigation is validationScenarioFor over the same association; not a fitness-for-use verdict.";
  }
}
