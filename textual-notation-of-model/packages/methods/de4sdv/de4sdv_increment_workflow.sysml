/* DE4SDV increment workflow: method steps, their artifacts and their checks.
 * Source: methodologies/sysmod-sysmlv2/increment-workflow.md, which states the
 * method rules the checks below implement. */
package DE4SDV_IncrementWorkflow {
  doc /* The increment workflow: one step per method phase, typed by a step
       * definition whose parameters are the artifacts it reads and produces. A
       * MethodCheck usage inside a step definition, about one of its parameters,
       * states a rule that a deterministic evaluation checks. A check result is
       * not a conformance, acceptance, compliance or certification claim. */

  doc RequiredTraceChainOntologyDefinition /* The ordered trace chain every substantial increment should establish, even if some
   * links are draft: stakeholder concern, need, requirement, feature (for a varying
   * requirement only; a core requirement has none), architecture element,
   * logical-to-software signal mapping when a boundary is crossed,
   * physical/software realization, verification case, acceptance criterion, evidence
   * artifact, baseline decision. Intentionally missing links are recorded as gaps. */
  comment about RequiredTraceChainOntologyDefinition /* Historical vocabulary, kept for compatibility. It defines no
   * universal completion policy: each increment's charter and its native traces govern
   * instead. */

  doc TraceLinkOntologyDefinition /* A relationship connecting source, rationale, requirement, model, evidence, or baseline
   * artifacts. */
  comment about TraceLinkOntologyDefinition /* Historical vocabulary, kept as documentation only: not a
   * string-endpoint record and not a completion witness. */

  doc IncrementTraceabilityShellOntologyDefinition /* The traceability structure connecting an increment to its sources and downstream
   * artifacts. */
  comment about IncrementTraceabilityShellOntologyDefinition /* Historical vocabulary, kept as documentation only: no
   * string-shell record is reintroduced; IncrementTraceObligations and the native
   * relationships represent an increment's traces. */

  private import ScalarValues::*;
  private import DE4SDV_MethodProcess::*;
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_ProductLine::ProductLineCharacteristic;
  private import DE4SDV_TraceVocabulary::AllocatableFunction;
  private import DE4SDV_TraceVocabulary::LogicalAllocationElement;
  private import DE4SDV_TraceVocabulary::PhysicalAllocationElement;

  metadata def MethodCheck {
    doc /* A method rule about one parameter of a step definition. Its subjects are
         * the increment's elements that conform to that parameter's type and scope;
         * their number must lie within the parameter's multiplicity, and an empty
         * population with lower bound 0 means the check does not apply. A parameter
         * typed by a function, logical or physical element class counts the scope at
         * any depth and the elements the increment's own allocations name. Principle:
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

  part def IncrementTraceObligations {
    doc /* Scope declaration of an increment's trace obligations: the increment
         * and its applicable phases. Required traces derive from the checks
         * that the workflow steps of those phases declare, not from
         * candidate-selected easy checks. The traces themselves are the
         * increment's native model relationships (owning membership, typing,
         * requirement subject and stakeholder membership, framed concerns),
         * never parallel reference slots in this declaration. Populating this
         * declaration is not completion evidence.
         * Reuse prior artifacts, preserve R/F/L/P, and do not invent realization
         * or execution for early framing. Missing required traces block the
         * exit of the phase they belong to unless an authorized visible
         * disposition permits it, such as a step parameter whose multiplicity
         * allows none. Unsupported or unavailable evaluation stays UNASSESSED,
         * never synthetic PASS. */
    ref part increment : EngineeringIncrement;
    attribute applicablePhases[*] : MethodPhase;
  }

  part def IncrementCharter :> IncrementTraceObligations {
    doc /* Charter declaration of one increment: the inherited increment reference and
         * applicable phases, plus the plain attributes owner, expected artifacts and
         * expected review evidence, and the system of interest by reference. The
         * expected artifacts name the top-level packages the checks evaluate; content
         * elsewhere is never evaluated. The rest of the charter is native content of
         * the increment package. */
    attribute owner : String;
    attribute expectedArtifacts : String[1..*];
    attribute expectedReviewEvidence : String[1..*];
    ref part systemOfInterest[0..1] {
      doc /* The system of interest: the entity the increment's needs and requirements
           * take as subject, never the increment itself. An increment sets it by
           * reference to a usage (ref part :>> systemOfInterest = <usage>;) or by type
           * (ref part :>> systemOfInterest : <Definition>;). A subject matches it when
           * it is, narrows, or is typed by that usage's definition or a specialization
           * of it: the match is type-level, so another usage of the definition also
           * matches. */
    }
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
         * Owner, expected artifacts and expected review evidence are plain attributes.
         * The expected artifacts name the packages the checks evaluate. Advisory: they
         * name every package holding increment content. */
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
    metadata expectedArtifactsCoverIncrementContent : MethodCheck about charter {
      doc /* Advisory: the expected artifacts name every top-level package holding increment content:
           * the increment usage, elements connected by DerivesFromNeed to an element in scope,
           * verification cases verifying an in-scope requirement, requirements verified by an
           * in-scope verification case, allocations from an element in scope, and elements
           * referencing the increment usage. Content in a package they do not name is never
           * evaluated. No completeness claim. */
      :>> check = "charterExpectedArtifactsCoverContent";
      :>> advisory = true;
    }
  }

  action def FrameConcerns :> IncrementStep {
    doc /* Who cares and why? Rules: each concern of the increment has a native
         * stakeholder member, and a viewpoint of a view of the increment frames
         * it. The stakeholders are the native stakeholder members of the concerns,
         * the problem statement and the needs; no check counts stakeholder parts. */
    attribute :>> phase = MethodPhase::phase1_concernFraming;
    in requirement problemStatement : ProblemStatement;
    out part stakeholders[1..*] : Stakeholder;
    out concern concerns[1..*];

    metadata concernHasStakeholder : MethodCheck about concerns {
      doc /* Each concern of the increment has a native stakeholder member; no assignment or authority claim. */
      :>> check = "stakeholderMember";
    }
    metadata concernFramedByViewpoint : MethodCheck about concerns {
      doc /* Each concern of the increment is framed by a viewpoint of a view in a package of the increment; no claim that the view addresses the concern. */
      :>> check = "framedByViewpoint";
    }
  }

  action def SpecifyOperationalContext :> IncrementStep {
    doc /* What happens in the world? Rules: a member product's operational
         * context and story hold System 1 roles only; bench, reviewer and
         * evidence roles belong to the engineering and assurance system. Each
         * use case of the story binds its subject to the system of interest
         * and each actor to a context part around it. The context's own
         * systemOfInterest is the system of interest the charter declares. The
         * checks read the context and the bindings of the increment's use cases.
         * Review judges the roles: the kernel classifies no role as System 1 or
         * System 2. */
    attribute :>> phase = MethodPhase::phase2_operationalContext;
    in requirement problemStatement : ProblemStatement;
    out part operationalContext : SystemContext;

    metadata incrementHasOperationalContext : MethodCheck about operationalContext {
      doc /* The increment has exactly one operational context; the count is the rule, no completeness claim. */
      :>> check = "populationMember";
    }
    metadata operationalContextHoldsSystemOfInterest : MethodCheck about operationalContext {
      doc /* The operational context redefines its systemOfInterest with the system of interest the charter declares, by usage, narrowing, binding or type lineage; no completeness claim. */
      :>> check = "contextSystemOfInterest";
    }
    metadata storyBindsSubjectToSystemOfInterest : MethodCheck about operationalContext {
      doc /* Each use case of the increment binds its subject to the operational context's system of interest; no claim about what the story says. */
      :>> check = "storySubjectBound";
    }
    metadata storyBindsActorsToContextParts : MethodCheck about operationalContext {
      doc /* Each actor of each use case of the increment is bound to a part of the operational context around its system of interest; no claim that a role is a System 1 role. */
      :>> check = "storyActorsBound";
    }
  }

  action def ClassifyCapabilities :> IncrementStep {
    doc /* Which characteristics distinguish member products? Rule: the step
         * records only the feature-model delta, the feature candidates the
         * increment adds, and the delta may be empty. Core elements are common
         * by default and get no record; constraints go to the requirements and
         * evidence to V&V. Product-line scope the increment defers, such as a
         * gap, is no classification record and is allowed. */
    attribute :>> phase = MethodPhase::phase3_capabilityClassification;
    in part operationalContext : SystemContext;
    out part characteristics[0..*] : ProductLineCharacteristic;

    metadata characteristicIsFeatureDelta : MethodCheck about characteristics {
      doc /* Each product-line characteristic of the increment is a feature candidate or deferred product-line scope; a common-capability record is no feature-model delta. No claim that a candidate distinguishes member products. */
      :>> check = "featureDeltaOnly";
    }
  }

  action def ElaborateNeeds :> IncrementStep {
    doc /* What stakeholder needs exist and how will the needs be validated? Rules:
         * each need has a statement, at least one stakeholder, an ODE4HERA source
         * and rationale, and at least one planned validation scenario. Needs are
         * elaborated from the concerns that viewpoints frame and trace to them
         * through stakeholder, source and rationale. A need doesn't frame a
         * concern: it would then be satisfied only when the whole concern is
         * addressed, while a need usually covers only part of one. Advisory: a
         * need takes the system of interest the charter declares as subject,
         * never the increment. */
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
    metadata needSubjectIsSystemOfInterest : MethodCheck about needs {
      doc /* Advisory: each need's subject is the system of interest the charter declares (matched by its usage or its definition's lineage), never the increment; no satisfaction claim. */
      :>> check = "subjectIsSystemOfInterest";
      :>> advisory = true;
    }
  }

  action def SpecifyRequirements :> IncrementStep {
    doc /* What shall the system or product line do and how will those requirements be
         * verified? Rules: only DerivesFromNeed traces a requirement to a need, plain
         * dependencies do not count; a requirement has a statement, exactly one native
         * subject and one primary verification method of the standard kinds. Advisory:
         * a requirement's subject is the system of interest the charter declares, never
         * the increment; a requirement states its success criteria. A requirement
         * varies with the features that bring its system of interest into a member
         * product. These existing links name such a feature:
         * - a dependency of the requirement or of its system of interest on the feature;
         * - such a dependency on a variant bound to the feature, on a variant that a
         *   derivation rule derives from it, or on that variant's definition;
         * - the typing of the system of interest by the definition of such a variant.
         * A definition names a feature only when it types no other bound or derived
         * variant. Otherwise, link to the variant itself. A derived variant names
         * every premise of the rule that derives it. When the links name more than
         * one feature, the requirement applies to a member product that selects all
         * of them. Declare these dependencies with the requirement or its system of
         * interest, outside the feature-model and configuration documents. A
         * requirement with no such link is core, common to every member product. An
         * element that only restates such a link does not earn its place. No check
         * reads these links. The PLEML configuration evaluator binds only the
         * variations of a feature model's projection owner, one per feature group.
         * Binding a requirement variant to a feature in phase 9 therefore waits until
         * the evaluator binds requirement variants. */
    attribute :>> phase = MethodPhase::phase5_requirements;
    in requirement needs[0..*] : StakeholderNeedCandidate;
    out requirement requirements[1..*] : RequirementCandidate;

    metadata requirementHasStatement : MethodCheck about requirements {
      doc /* Each requirement owns a require constraint as its statement; no wording or verifiability claim. */
      :>> check = "requireConstraint";
    }
    metadata requirementDerivesFromNeed : MethodCheck about requirements {
      doc /* Each requirement derives from a need through DerivesFromNeed only; provenance, no satisfaction claim. */
      :>> check = "derivesRequirementFromNeed";
    }
    metadata requirementHasOneSubject : MethodCheck about requirements {
      doc /* Each requirement has exactly one native subject; no satisfaction claim. */
      :>> check = "oneNativeSubject";
    }
    metadata requirementSubjectIsSystemOfInterest : MethodCheck about requirements {
      doc /* Advisory: each requirement's subject is the system of interest the charter declares (matched by its usage or its definition's lineage), never the increment; no satisfaction claim. */
      :>> check = "subjectIsSystemOfInterest";
      :>> advisory = true;
    }
    metadata requirementHasVerificationMethod : MethodCheck about requirements {
      doc /* Each requirement records exactly one of inspect, demo, test or analyze; planning only, no result. */
      :>> check = "oneVerificationMethodKind";
    }
    metadata requirementStatesSuccessCriteria : MethodCheck about requirements {
      doc /* Advisory: each requirement states its success criteria; a test-verdict criterion, no verdict or acceptance claim. */
      :>> check = "successCriteriaAttribute";
      :>> advisory = true;
    }
  }

  action def DefineFunctionalArchitecture :> IncrementStep {
    doc /* What functions, flows, states, and interfaces are needed? Rules: the
         * increment has at least one function, and each functional requirement of
         * the increment is allocated to at least one function by a native allocation
         * (allocatedTo); plain dependencies do not count. Advisory: each requirement
         * of the increment, functional or not, is allocated to a function or named as
         * relevant by an architecture element (hasRelevantArchitecture); one that is
         * neither is reported with what else holds it, an allocation that does not
         * count or its verification; each function carries a requirement. The
         * increment's functions are the AllocatableFunction usages its packages own
         * at any depth and the functions its own allocations name. An allocation
         * assigns responsibility only; flows, states and interfaces are not checked. */
    attribute :>> phase = MethodPhase::phase6_functionalArchitecture;
    in requirement requirements[0..*] : RequirementCandidate;
    in requirement functionalRequirements[0..*] : FunctionalRequirementCandidate;
    out action functions[1..*] : AllocatableFunction;

    metadata functionalRequirementAllocatedToFunction : MethodCheck about functionalRequirements {
      doc /* Each functional requirement of the increment is allocated to at least one function; a responsibility assignment only, no satisfaction, realization or verification claim. */
      :>> check = "allocatedTo";
    }
    metadata incrementHasFunction : MethodCheck about functions {
      doc /* The increment has at least one function; the count is the rule, no completeness or necessity claim. */
      :>> check = "populationMember";
    }
    metadata requirementCarriedByArchitecture : MethodCheck about requirements {
      doc /* Advisory: each requirement of the increment, functional or not, is allocated to a function or named as relevant by an architecture element (hasRelevantArchitecture); one that is neither is reported with what else holds it: an allocation that grounds in no end pair, its verification alone, or no verification case yet. No satisfaction claim. */
      :>> check = "carriedByArchitecture";
      :>> advisory = true;
    }
    metadata functionCarriesRequirement : MethodCheck about functions {
      doc /* Advisory: each function of the increment receives an allocation from a requirement; no necessity or completeness claim. */
      :>> check = "receivesAllocation";
      :>> advisory = true;
    }
  }

  action def DefineLogicalArchitecture :> IncrementStep {
    doc /* What technology-independent logical elements realize the functions? Rules:
         * each function of the increment is allocated to at least one logical element
         * (allocatedTo). The increment's logical elements are the
         * LogicalAllocationElement usages its packages own at any depth and the ones
         * its own allocations name. Advisory: each logical element carries a function.
         * Exchanges and interfaces are not checked. */
    attribute :>> phase = MethodPhase::phase7_logicalArchitecture;
    in action functions[1..*] : AllocatableFunction;
    out part logicalElements[1..*] : LogicalAllocationElement;

    metadata functionAllocatedToLogicalElement : MethodCheck about functions {
      doc /* Each function of the increment is allocated to at least one logical element; a responsibility assignment only, no realization or transitivity claim. */
      :>> check = "allocatedTo";
    }
    metadata logicalElementCarriesFunction : MethodCheck about logicalElements {
      doc /* Advisory: each logical element of the increment receives an allocation from a function; no necessity or completeness claim. */
      :>> check = "receivesAllocation";
      :>> advisory = true;
    }
  }

  action def DefinePhysicalRealization :> IncrementStep {
    doc /* What software, hardware, deployment, or tool elements realize the system
         * design? Rules: each logical element of the increment is allocated to at
         * least one physical element (allocatedTo). The increment's physical elements
         * are the PhysicalAllocationElement usages its packages own at any depth and
         * the ones its own allocations name. Advisory: each physical element carries a
         * logical element. Advisory, the system-to-software signal-mapping control: a
         * physical element that realizes a logical element and has a port with a
         * directed feature, of its own, of its definition, of a feature it narrows or
         * of a connected port, is a crossing, and each logical element it realizes has a
         * SystemToSoftwareSignalMappingCandidate allocation, owned by a package of the
         * increment, to a physical element of the increment that realizes it or a port
         * of one, whose LogicalToSoftwareSignalMappingRecords each state a disposition,
         * an owner and a next action, and when notApplicable why; each record of a
         * signal mapping states the semantic source, or the item at its port is
         * VSS-typed. An allocation is no deployment, execution or runtime claim, and a
         * mapping no runtime-interoperability claim; the realization-readiness control
         * stays with review. */
    attribute :>> phase = MethodPhase::phase8_physicalRealization;
    in part logicalElements[1..*] : LogicalAllocationElement;
    out part physicalElements[1..*] : PhysicalAllocationElement;
    out allocation signalMappings[0..*] : SystemToSoftwareSignalMappingCandidate;

    metadata logicalElementAllocatedToPhysicalElement : MethodCheck about logicalElements {
      doc /* Each logical element of the increment is allocated to at least one physical element; a responsibility assignment only, no deployment, execution or runtime claim. */
      :>> check = "allocatedTo";
    }
    metadata physicalElementCarriesLogicalElement : MethodCheck about physicalElements {
      doc /* Advisory: each physical element of the increment receives an allocation from a logical element; no necessity or completeness claim. */
      :>> check = "receivesAllocation";
      :>> advisory = true;
    }
    metadata crossingHasSignalMapping : MethodCheck about physicalElements {
      doc /* Advisory: each crossing has a system-to-software signal mapping whose record states a disposition, an owner and a next action; a control record, no runtime-interoperability claim. */
      :>> check = "signalMappingRecorded";
      :>> advisory = true;
    }
    metadata signalMappingNamesSemanticSource : MethodCheck about signalMappings {
      doc /* Advisory: each record of a signal mapping states the semantic source, or the item at the mapping's port is typed by a VSS signal (COVESA VSS or the DE4SDV extensions); no claim that the item is or is not a vehicle signal. */
      :>> check = "semanticSourceNamed";
      :>> advisory = true;
    }
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
         * every in-scope requirement is verified by a verification case. Advisory: an
         * evidence record or status per case. */
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
    metadata verificationCaseHasEvidenceRecordOrStatus : MethodCheck about verificationCases {
      doc /* Advisory: each verification case has an evidence record or status; no adequacy or acceptance claim. */
      :>> check = "evidenceRecordOrStatus";
      :>> advisory = true;
    }
  }

  action def PublishIncrement :> IncrementStep {
    doc /* What is reviewable now? Rules: each view of the increment has a
         * viewpoint that frames a concern, and the view, or a view it owns,
         * exposes model content. The checks judge the model only. The pull
         * request, its review and the rendered diagrams are judged outside the
         * model: CI checks the diagrams and the view index, review the rest. */
    attribute :>> phase = MethodPhase::phase11_publication;
    in part charter : IncrementCharter;
    out view publishedViews[0..*];

    metadata publishedViewFramesConcern : MethodCheck about publishedViews {
      doc /* Each view of the increment has a viewpoint, of its own or of its definition, that frames a concern; no claim that the view addresses the concern. */
      :>> check = "viewpointFramesConcern";
    }
    metadata publishedViewExposesContent : MethodCheck about publishedViews {
      doc /* Each view of the increment, or a view it owns at any depth, exposes model content; no rendering, publication or review claim. */
      :>> check = "exposesModelContent";
    }
  }

  action def DecideBaselineAndNextSlice :> IncrementStep {
    doc /* What is accepted, deferred, or invalidated? */
    attribute :>> phase = MethodPhase::phase12_baselineNextSlice;
    in part charter : IncrementCharter;
    out part baselineDecision : IncrementLifecycleDecision;
    out part openGaps[0..*] : IncrementGap;
  }
}
