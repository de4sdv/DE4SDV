/* DE4SDV increment workflow: method steps, their artifacts and their checks.
 * Source: methodologies/sysmod-sysmlv2/increment-workflow.md and the eight method
 * rules accepted by the owner on 2026-10-08 (rule 3 revised on 2026-10-09). */
package DE4SDV_IncrementWorkflow {
  doc /* The increment workflow: one step per method phase, typed by a step
       * definition whose parameters are the artifacts it reads and produces. A
       * MethodCheck usage inside a step definition, about one of its parameters,
       * states a rule that a deterministic evaluation checks. A check result is
       * not a conformance, acceptance, compliance or certification claim. */

  private import ScalarValues::*;
  private import DE4SDV_MethodProcess::*;
  private import DE4SDV_MethodTraces::*;
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_Stakeholders::*;

  metadata def MethodCheck {
    doc /* A method rule about one parameter of a step definition. Its subjects are
         * the increment's elements that conform to that parameter's type and scope;
         * their number must lie within the parameter's multiplicity, and an empty
         * population with lower bound 0 means the check does not apply. Principle:
         * structural checks block; judgment checks (wording, verifiability) are advisory. */
    attribute check : String {
      doc /* Check identifier in the evaluation registry; an unknown identifier fails closed. */
    }
    attribute minimum : Natural default 1 {
      doc /* Minimum number of qualifying targets per subject. */
    }
    attribute advisory : Boolean default false {
      doc /* True: a failure is reported but never blocks the step. */
    }
  }

  part def IncrementCharter :> IncrementTraceObligations {
    doc /* Charter declaration of one increment: the inherited increment reference,
         * trace method, scope kind, applicable phases and completion claim, plus the
         * plain attributes owner, expected artifacts and expected review evidence. The
         * rest of the charter is native content of the increment package. */
    attribute owner : String;
    attribute expectedArtifacts : String[1..*];
    attribute expectedReviewEvidence : String[1..*];
    action workflow : IncrementWorkflow {
      doc /* The workflow this increment follows; an increment may tailor it later by redefinition. */
    }
  }

  abstract action def IncrementStep {
    doc /* One step of the increment workflow; phase is the method phase it performs. */
    attribute phase : MethodPhase;
  }

  action def IncrementWorkflow {
    doc /* The steps of one increment in method order. Framing always applies; a later
         * step applies when the charter lists its phase in the applicable phases. The
         * pattern follows SYSMOD's SYSMODDefaultProcess without specializing it;
         * formal alignment with SYSMOD comes later. */
    first start;
    then action frameIncrement : FrameIncrement;
    then action frameConcerns[0..1] : FrameConcerns;
    then action specifyOperationalContext[0..1] : SpecifyOperationalContext;
    then action classifyCapabilities[0..1] : ClassifyCapabilities;
    then action elaborateNeeds[0..1] : ElaborateNeeds;
    then action specifyRequirements[0..1] : SpecifyRequirements;
    then action defineFunctionalArchitecture[0..1] : DefineFunctionalArchitecture;
    then action defineLogicalArchitecture[0..1] : DefineLogicalArchitecture;
    then action definePhysicalRealization[0..1] : DefinePhysicalRealization;
    then action defineVariabilityAndConfiguration[0..1] : DefineVariabilityAndConfiguration;
    then action planVerificationAndEvidence[0..1] : PlanVerificationAndEvidence;
    then action publishIncrement[0..1] : PublishIncrement;
    then action decideBaselineAndNextSlice[0..1] : DecideBaselineAndNextSlice;
    then done;

    flow from frameIncrement.problemStatement to elaborateNeeds.problemStatement;
    flow from frameConcerns.concerns to elaborateNeeds.concerns;
    flow from elaborateNeeds.needs to specifyRequirements.needs;
    flow from specifyRequirements.requirements to planVerificationAndEvidence.requirements;
  }

  action def FrameIncrement :> IncrementStep {
    doc /* What are we changing or learning? Rule: every increment is declared with a
         * short identifier and a charter: problem statement, engineering question,
         * lifecycle decision, at least one assumption, stakeholder and viewpoint-framed
         * concern, scope and out-of-scope, and owner; it declares which phases apply.
         * Owner, expected artifacts and expected review evidence are plain attributes. */
    attribute :>> phase = MethodPhase::phase0_incrementFraming;
    out part increment : EngineeringIncrement;
    out part charter : IncrementCharter;
    out requirement problemStatement : ProblemStatement;
    out part engineeringQuestion : IncrementEngineeringQuestion;
    out part lifecycleDecision : IncrementLifecycleDecision;
    out part assumptions[1..*] : IncrementAssumption;
    out part scope : IncrementScope;
    out part outOfScopeItems[1..*] : OutOfScopeItem;
    out concern framedConcerns[1..*];

    metadata incrementHasIdentifier : MethodCheck about increment {
      doc /* Exactly one increment usage carries the increment identifier as its short name; no registry claim. */
      :>> check = "incrementShortName";
    }
    metadata incrementHasCharter : MethodCheck about charter {
      doc /* Exactly one charter declaration references the increment; declaration only, not completion evidence. */
      :>> check = "charterReferencesIncrement";
    }
    metadata incrementHasProblemStatement : MethodCheck about problemStatement {
      doc /* Exactly one problem statement in the increment package has a native subject typed by the increment definition. */
      :>> check = "problemStatementSubject";
    }
    metadata incrementHasEngineeringQuestion : MethodCheck about engineeringQuestion {
      doc /* The increment package owns its engineering question; no claim that it is answered. */
      :>> check = "ownedByIncrementPackage";
    }
    metadata incrementHasLifecycleDecision : MethodCheck about lifecycleDecision {
      doc /* The increment package owns its lifecycle decision; no decision or acceptance claim. */
      :>> check = "ownedByIncrementPackage";
    }
    metadata incrementHasAssumption : MethodCheck about assumptions {
      doc /* The increment package owns at least one assumption; recorded, not validated. */
      :>> check = "ownedByIncrementPackage";
    }
    metadata incrementHasStakeholder : MethodCheck about problemStatement {
      doc /* The problem statement has a native stakeholder member; no assignment or authority claim. */
      :>> check = "stakeholderMember";
    }
    metadata incrementHasFramedConcern : MethodCheck about framedConcerns {
      doc /* A concern of the increment package is framed by a viewpoint of a view of that package. */
      :>> check = "framedByIncrementView";
    }
    metadata incrementHasScope : MethodCheck about scope {
      doc /* The increment package owns exactly one scope; no completeness claim. */
      :>> check = "ownedByIncrementPackage";
    }
    metadata incrementHasOutOfScopeItem : MethodCheck about outOfScopeItems {
      doc /* The increment package owns at least one out-of-scope item; no completeness claim. */
      :>> check = "ownedByIncrementPackage";
    }
    metadata incrementHasOwner : MethodCheck about charter {
      doc /* The charter carries one non-empty owner; no authority claim. */
      :>> check = "charterOwner";
    }
    metadata incrementDeclaresApplicablePhases : MethodCheck about charter {
      doc /* The charter declares at least one applicable MethodPhase; not a completion claim. */
      :>> check = "charterApplicablePhases";
    }
    metadata incrementDeclaresExpectedArtifacts : MethodCheck about charter {
      doc /* The charter lists at least one expected artifact; no existence claim. */
      :>> check = "charterExpectedArtifacts";
    }
    metadata incrementDeclaresExpectedReviewEvidence : MethodCheck about charter {
      doc /* The charter lists at least one expected review evidence item; no review outcome claim. */
      :>> check = "charterExpectedReviewEvidence";
    }
  }

  action def FrameConcerns :> IncrementStep {
    doc /* Who cares and why? */
    attribute :>> phase = MethodPhase::phase1_concernFraming;
    in requirement problemStatement : ProblemStatement;
    out part stakeholders[1..*] : Stakeholder;
    out concern concerns[1..*];
  }

  action def SpecifyOperationalContext :> IncrementStep {
    doc /* What happens in the world? */
    attribute :>> phase = MethodPhase::phase2_operationalContext;
    in requirement problemStatement : ProblemStatement;
    out part operationalContext : SystemContext;
  }

  action def ClassifyCapabilities :> IncrementStep {
    doc /* Is this a feature, common capability, constraint, or evidence capability? */
    attribute :>> phase = MethodPhase::phase3_capabilityClassification;
    in part operationalContext : SystemContext;
    out part characteristics[1..*];
  }

  action def ElaborateNeeds :> IncrementStep {
    doc /* What stakeholder needs exist and how will the needs be validated? Rules:
         * each need has a statement, at least one stakeholder, an ODE4HERA source
         * and rationale, and at least one planned validation scenario. Needs are
         * elaborated from the concerns that viewpoints frame and trace to them
         * through stakeholder, source and rationale. A need doesn't frame a
         * concern: it would then be satisfied only when the whole concern is
         * addressed, while a need usually covers only part of one. */
    attribute :>> phase = MethodPhase::phase4_needs;
    in requirement problemStatement : ProblemStatement;
    in concern concerns[0..*];
    out requirement needs[1..*] : StakeholderNeedCandidate;

    metadata needHasStatement : MethodCheck about needs {
      doc /* Each need owns a require constraint as its statement; no wording or verifiability claim. */
      :>> check = "requireConstraint";
    }
    metadata needHasStakeholder : MethodCheck about needs {
      doc /* Each need has a native stakeholder member; no assignment or authority claim. */
      :>> check = "stakeholderMember";
    }
    metadata needHasSource : MethodCheck about needs {
      doc /* Each need carries one non-empty ODE4HERA source; no source-correctness claim. */
      :>> check = "sourceAttribute";
    }
    metadata needHasRationale : MethodCheck about needs {
      doc /* Each need carries one non-empty ODE4HERA rationale; no soundness claim. */
      :>> check = "rationaleAttribute";
    }
    metadata needHasValidationScenario : MethodCheck about needs {
      doc /* Each need has a planned validation scenario association; planning only, no validation result. */
      :>> check = "hasValidationScenario";
    }
  }

  action def SpecifyRequirements :> IncrementStep {
    doc /* What shall the system or product line do and how will those requirements be
         * verified? Rules: only DerivesFromNeed traces a requirement to a need, plain
         * dependencies do not count; a requirement has exactly one native subject and
         * one primary verification method of the standard kinds. Advisory: a
         * requirement traces to a feature or common capability. */
    attribute :>> phase = MethodPhase::phase5_requirements;
    in requirement needs[0..*] : StakeholderNeedCandidate;
    out requirement requirements[1..*] : RequirementCandidate;

    metadata requirementDerivesFromNeed : MethodCheck about requirements {
      doc /* Each requirement derives from a need through DerivesFromNeed only; provenance, no satisfaction claim. */
      :>> check = "derivesRequirementFromNeed";
    }
    metadata requirementHasOneSubject : MethodCheck about requirements {
      doc /* Each requirement has exactly one native subject; no satisfaction claim. */
      :>> check = "oneNativeSubject";
    }
    metadata requirementHasVerificationMethod : MethodCheck about requirements {
      doc /* Each requirement records exactly one of inspect, demo, test or analyze; planning only, no result. */
      :>> check = "oneVerificationMethodKind";
    }
    metadata requirementSpecifiesFeatureOrCapability : MethodCheck about requirements {
      doc /* Advisory: each requirement traces to a feature or common capability; no native carrier exists yet. */
      :>> check = "specifiesFeatureOrCommonCapability";
      :>> advisory = true;
    }
  }

  action def DefineFunctionalArchitecture :> IncrementStep {
    doc /* What functions, flows, states, and interfaces are needed? */
    attribute :>> phase = MethodPhase::phase6_functionalArchitecture;
    in requirement requirements[0..*] : RequirementCandidate;
    out action functions[1..*];
  }

  action def DefineLogicalArchitecture :> IncrementStep {
    doc /* What technology-independent logical elements realize the functions? */
    attribute :>> phase = MethodPhase::phase7_logicalArchitecture;
    in action functions[0..*];
    out part logicalElements[1..*];
  }

  action def DefinePhysicalRealization :> IncrementStep {
    doc /* What software, hardware, deployment, or tool elements realize the system design? */
    attribute :>> phase = MethodPhase::phase8_physicalRealization;
    in part logicalElements[0..*];
    out part physicalElements[1..*];
  }

  action def DefineVariabilityAndConfiguration :> IncrementStep {
    doc /* How does this vary across member products or configurations? */
    attribute :>> phase = MethodPhase::phase9_variabilityConfiguration;
    in part physicalElements[0..*];
    out part variationPoints[1..*];
  }

  action def PlanVerificationAndEvidence :> IncrementStep {
    doc /* How will requirement satisfaction and stakeholder fitness-for-use be checked?
         * Rules: each verification case verifies a requirement of the increment, and
         * every in-scope requirement is verified by a verification case. Advisory:
         * acceptance-criterion targets, and an evidence record or status per case. */
    attribute :>> phase = MethodPhase::phase10_vvEvidence;
    in requirement requirements[0..*] : RequirementCandidate;
    out verification verificationCases[1..*];

    metadata verificationCaseVerifiesRequirement : MethodCheck about verificationCases {
      doc /* Each verification case verifies a requirement of the increment; no result, evidence or acceptance claim. */
      :>> check = "verifiesIncrementRequirement";
    }
    metadata requirementVerifiedByVerificationCase : MethodCheck about requirements {
      doc /* Each in-scope requirement is verified by a verification case; no result, evidence or acceptance claim. */
      :>> check = "verifiedBy";
    }
    metadata verificationCaseVerifiesAcceptanceCriterion : MethodCheck about verificationCases {
      doc /* Advisory: each verification case verifies an acceptance criterion; test-verdict criterion, not acceptance. */
      :>> check = "verifiesAcceptanceCriterion";
      :>> advisory = true;
    }
    metadata verificationCaseHasEvidenceRecordOrStatus : MethodCheck about verificationCases {
      doc /* Advisory: each verification case has an evidence record or status; no adequacy or acceptance claim. */
      :>> check = "evidenceRecordOrStatus";
      :>> advisory = true;
    }
  }

  action def PublishIncrement :> IncrementStep {
    doc /* What is reviewable now? */
    attribute :>> phase = MethodPhase::phase11_publication;
    in part charter : IncrementCharter;
    out view publishedViews[0..*];
  }

  action def DecideBaselineAndNextSlice :> IncrementStep {
    doc /* What is accepted, deferred, or invalidated? */
    attribute :>> phase = MethodPhase::phase12_baselineNextSlice;
    in part charter : IncrementCharter;
    out part baselineDecision : IncrementLifecycleDecision;
    out part openGaps[0..*] : IncrementGap;
  }
}
