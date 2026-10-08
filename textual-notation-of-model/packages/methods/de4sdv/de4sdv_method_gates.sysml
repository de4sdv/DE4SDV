/* DE4SDV method gates: generic, model-resident gates of the increment workflow.
 *
 * Source: methodologies/sysmod-sysmlv2/increment-workflow.md (entry criteria,
 * phase outputs, required trace chain, review questions) and the eight DE4SDV
 * method rules accepted by the owner on 2026-10-08.
 */
package DE4SDV_MethodGates {
  doc /* Generic method gates for the increment framing, needs, requirements,
       * and V&V and evidence phases of the DE4SDV increment workflow. A gate is
       * a typed method-contract obligation over the native model relationships
       * of one increment. The agent authors; a deterministic evaluation reads
       * these gates from the model and reports the gaps. Declaring a gate is
       * not evaluating it: no evaluation engine reads this package at this
       * revision, and no conformance, acceptance, compliance or certification
       * claim follows from it.
       *
       * Method rules: the gates encode the eight DE4SDV method rules accepted
       * by the owner. Each rule is a comment about exactly the gates that
       * encode it, one gate per rule clause, so changing a rule edits that
       * comment and those gates only.
       *
       * Increment declaration convention:
       * 1. Identity: the increment usage carries its registered increment
       *    identifier (INC prefix, registered subject, sequence) as its
       *    declared short name and is typed by a specialization of
       *    EngineeringIncrement. The usage name keeps its own identity.
       * 2. Charter declaration: exactly one IncrementCharter usage references
       *    the increment. It declares the applicable phases and, as plain
       *    attributes, the owner, the expected artifacts and the expected
       *    review evidence. It also carries the trace scope kind and
       *    completion claim it inherits from IncrementTraceObligations.
       * 3. Charter content: the native relationships of the package that owns
       *    the increment usage (the increment package): one ProblemStatement
       *    whose native subject is typed by the increment definition, with
       *    its stakeholder members; one IncrementEngineeringQuestion, one
       *    IncrementLifecycleDecision and one IncrementScope part; at least
       *    one IncrementAssumption and one OutOfScopeItem part; and concerns
       *    framed by a viewpoint of a view of that package.
       * 4. Later-phase content: needs and requirements of the increment have
       *    a native subject typed by the increment definition; verification
       *    cases of the increment are owned by the increment package or by a
       *    package that declares references to the increment usage.
       *
       * Subject selectors (typed populations of one increment):
       * - incrementIdentifier: the requested increment identifier (one subject);
       * - increment: the identified increment usage (one subject);
       * - incrementNeeds: requirement usages in the StakeholderNeedCandidate
       *   lineage whose native subject is typed by the increment definition;
       * - incrementRequirements: requirement usages in the RequirementCandidate
       *   lineage, outside the EvidenceContract lineage, whose native subject
       *   is typed by the increment definition;
       * - incrementVerificationCases: verification case usages owned by the
       *   increment package or by a package that references the increment.
       *
       * Applicability: increment framing gates are unconditional; every other
       * gate applies when the charter declares the gate phase.
       *
       * Blocking or advisory: the inherited required flag, set by the
       * blocking principle. Structural checks block (required = true).
       * Judgment checks, such as wording and verifiability, are advisory and
       * have no deterministic gate; the advisory gates (required = false) are
       * the trace checks the advisory rule names.
       *
       * Empty populations: a gate over its own phase output (needs,
       * requirements, verification cases) fails when that population is empty
       * (minimumPopulation = 1, permittedEmpty = false). A gate over another
       * phase's output and every advisory gate is not applicable when its
       * population is empty (permittedEmpty = true, noEligibleSubjects).
       *
       * Prerequisites: a gate whose prerequisite is not a completed pass is not
       * attempted. Every gate after the identity gate needs the increment to be
       * identified; every gate outside increment framing needs the declared
       * applicable phases. */

  private import ScalarValues::*;
  private import DE4SDV_MethodProcess::*;
  private import DE4SDV_MethodConformance::*;
  private import DE4SDV_MethodTraces::*;

  // Gate vocabulary

  enum def PermittedEmptyDisposition {
    doc /* The recorded disposition of a gate whose subject population is
         * empty and whose policy permits an empty population. */
    noEligibleSubjects {
      doc /* No subject of the declared population exists; the gate is not applicable, not passed. */
    }
    explicitDisposition {
      doc /* A reviewed explicit disposition makes the gate not applicable, not passed. */
    }
  }

  item def MethodGate :> MethodContractObligation {
    doc /* A method-contract obligation that guards one method phase for any
         * increment. It adds the two contract fields MethodContractObligation
         * lacks: prerequisites and the permitted-empty disposition. An
         * unbounded per-subject maximum is the infinity literal (*) bound to
         * the inherited Natural cardinalityMaximum. Blocking or advisory is
         * the inherited required flag: true blocks the phase exit, false
         * reports an advisory gap. The gate's obligationId repeats its
         * declared name; no separate identifier family is introduced. */
    ref item prerequisites : MethodContractObligation[0..*] {
      doc /* Obligations that must be a completed pass (or not applicable)
           * before this gate is attempted; otherwise this gate is not attempted. */
    }
    attribute permittedEmptyDisposition : PermittedEmptyDisposition[0..1] {
      doc /* Disposition reported when the subject population is empty and
           * permittedEmpty is true; carries no value otherwise. */
    }
  }

  comment about MethodGate /* Principle: structural checks
   * block; judgment checks (wording, verifiability) are advisory. A gate
   * records this through its required flag. */

  part def IncrementCharter :> IncrementTraceObligations {
    doc /* The charter declaration of one engineering increment: the inherited
         * increment reference, selected trace method, trace scope kind,
         * applicable phases and completion claim, plus the owner, expected
         * artifacts and expected review evidence as plain attributes. The
         * rest of the charter is the native content of the increment package
         * (problem statement, engineering question, lifecycle decision,
         * assumptions, stakeholders, framed concerns, scope and out-of-scope
         * items), never restated here. Populating this declaration is not
         * completion evidence and assigns no authority. */
    attribute owner : String {
      doc /* The person, role or group that owns the increment. */
    }
    attribute expectedArtifacts : String[1..*] {
      doc /* The artifacts the increment is expected to produce. */
    }
    attribute expectedReviewEvidence : String[1..*] {
      doc /* The validation and review evidence expected for the increment's pull requests. */
    }
  }

  // Increment framing gates

  comment about incrementHasIdentifier, incrementHasCharter,
      incrementHasProblemStatement, incrementHasEngineeringQuestion,
      incrementHasLifecycleDecision, incrementHasAssumption, incrementHasStakeholder,
      incrementHasFramedConcern, incrementHasScope, incrementHasOutOfScopeItem,
      incrementHasOwner, incrementDeclaresApplicablePhases,
      incrementDeclaresExpectedArtifacts, incrementDeclaresExpectedReviewEvidence
    /* Increment rule: every increment is declared in the model with a short
     * identifier and a charter: problem statement, engineering question,
     * lifecycle decision, at least one assumption, at least one stakeholder,
     * at least one concern framed by a viewpoint, scope and out-of-scope, and
     * owner. It also declares which phases apply. Owner, expected artifacts
     * and expected review evidence are plain attributes, not new kernel
     * classes. */

  item incrementHasIdentifier : MethodGate {
    doc /* Claim boundary: exactly one part usage in the EngineeringIncrement
         * lineage carries the requested increment identifier as its declared
         * short name. No claim that the identifier is registered or allocated
         * correctly; registry rules stay a review policy. */
    attribute :>> obligationId = "incrementHasIdentifier";
    attribute :>> phase = MethodPhase::phase0_incrementFraming;
    attribute :>> subjectSelector = "incrementIdentifier";
    attribute :>> applicability = "unconditional";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "increment-identity";
    attribute :>> targetFilter = "EngineeringIncrement lineage; declared short name equals the increment identifier";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = 1;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "exactly one EngineeringIncrement-lineage part usage carries the increment identifier as its declared short name; no registry or allocation claim";
  }

  item incrementHasCharter : MethodGate {
    doc /* Claim boundary: exactly one IncrementCharter declaration references
         * the increment usage. The declaration states applicability and plain
         * charter attributes only; it is not completion evidence. */
    attribute :>> obligationId = "incrementHasCharter";
    attribute :>> phase = MethodPhase::phase0_incrementFraming;
    attribute :>> subjectSelector = "increment";
    attribute :>> applicability = "unconditional";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "increment-charter-declaration";
    attribute :>> targetFilter = "IncrementCharter lineage; increment reference resolves to the increment usage";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = 1;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "exactly one IncrementCharter declaration references the increment usage; declaration only, no completion evidence";
    ref item :>> prerequisites = incrementHasIdentifier;
  }

  item incrementHasProblemStatement : MethodGate {
    doc /* Claim boundary: exactly one ProblemStatement requirement owned by
         * the increment package has a native subject typed by the increment
         * definition. No claim about the problem statement's wording. */
    attribute :>> obligationId = "incrementHasProblemStatement";
    attribute :>> phase = MethodPhase::phase0_incrementFraming;
    attribute :>> subjectSelector = "increment";
    attribute :>> applicability = "unconditional";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "increment-problem-statement";
    attribute :>> targetFilter = "ProblemStatement lineage; owned by the increment package; native subject typed by the increment definition";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = 1;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "exactly one ProblemStatement owned by the increment package has a native subject typed by the increment definition; no wording claim";
    ref item :>> prerequisites = incrementHasIdentifier;
  }

  item incrementHasEngineeringQuestion : MethodGate {
    doc /* Claim boundary: exactly one IncrementEngineeringQuestion part is
         * owned by the increment package. No claim that the question is
         * answered. */
    attribute :>> obligationId = "incrementHasEngineeringQuestion";
    attribute :>> phase = MethodPhase::phase0_incrementFraming;
    attribute :>> subjectSelector = "increment";
    attribute :>> applicability = "unconditional";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "package-typed-member";
    attribute :>> targetFilter = "IncrementEngineeringQuestion lineage";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = 1;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "exactly one IncrementEngineeringQuestion part is owned by the increment package; no claim that it is answered";
    ref item :>> prerequisites = incrementHasIdentifier;
  }

  item incrementHasLifecycleDecision : MethodGate {
    doc /* Claim boundary: exactly one IncrementLifecycleDecision part is owned
         * by the increment package. No claim that the decision was taken or
         * accepted. */
    attribute :>> obligationId = "incrementHasLifecycleDecision";
    attribute :>> phase = MethodPhase::phase0_incrementFraming;
    attribute :>> subjectSelector = "increment";
    attribute :>> applicability = "unconditional";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "package-typed-member";
    attribute :>> targetFilter = "IncrementLifecycleDecision lineage";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = 1;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "exactly one IncrementLifecycleDecision part is owned by the increment package; no decision or acceptance claim";
    ref item :>> prerequisites = incrementHasIdentifier;
  }

  item incrementHasAssumption : MethodGate {
    doc /* Claim boundary: at least one IncrementAssumption part is owned by
         * the increment package. The assumptions are recorded, not validated. */
    attribute :>> obligationId = "incrementHasAssumption";
    attribute :>> phase = MethodPhase::phase0_incrementFraming;
    attribute :>> subjectSelector = "increment";
    attribute :>> applicability = "unconditional";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "package-typed-member";
    attribute :>> targetFilter = "IncrementAssumption lineage";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = *;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "at least one IncrementAssumption part is owned by the increment package; recorded only, not validated";
    ref item :>> prerequisites = incrementHasIdentifier;
  }

  item incrementHasStakeholder : MethodGate {
    doc /* Claim boundary: the increment's problem statement has at least one
         * native stakeholder member typed in the Stakeholder lineage. No
         * assignment of a real person, approval authority or competence. */
    attribute :>> obligationId = "incrementHasStakeholder";
    attribute :>> phase = MethodPhase::phase0_incrementFraming;
    attribute :>> subjectSelector = "increment";
    attribute :>> applicability = "unconditional";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "problem-statement-stakeholder";
    attribute :>> targetFilter = "Stakeholder lineage";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = *;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "the increment problem statement has at least one native Stakeholder-lineage stakeholder member; no assignment, authority or competence claim";
    ref item :>> prerequisites = incrementHasProblemStatement;
  }

  item incrementHasFramedConcern : MethodGate {
    doc /* Claim boundary: at least one concern owned by the increment package
         * is framed by a viewpoint of a view owned by the same package. No
         * claim that the concern is addressed or the view conforms. */
    attribute :>> obligationId = "incrementHasFramedConcern";
    attribute :>> phase = MethodPhase::phase0_incrementFraming;
    attribute :>> subjectSelector = "increment";
    attribute :>> applicability = "unconditional";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "package-view-framed-concern";
    attribute :>> targetFilter = "ConcernUsage owned by the increment package; framed by a viewpoint of a view owned by the same package";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = *;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "at least one concern of the increment package is framed by a viewpoint of a view of that package; no addressed-concern or view-conformance claim";
    ref item :>> prerequisites = incrementHasIdentifier;
  }

  item incrementHasScope : MethodGate {
    doc /* Claim boundary: exactly one IncrementScope part is owned by the
         * increment package. No claim that the scope is complete. */
    attribute :>> obligationId = "incrementHasScope";
    attribute :>> phase = MethodPhase::phase0_incrementFraming;
    attribute :>> subjectSelector = "increment";
    attribute :>> applicability = "unconditional";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "package-typed-member";
    attribute :>> targetFilter = "IncrementScope lineage";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = 1;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "exactly one IncrementScope part is owned by the increment package; no scope-completeness claim";
    ref item :>> prerequisites = incrementHasIdentifier;
  }

  item incrementHasOutOfScopeItem : MethodGate {
    doc /* Claim boundary: at least one OutOfScopeItem part is owned by the
         * increment package. No claim that every exclusion is listed. */
    attribute :>> obligationId = "incrementHasOutOfScopeItem";
    attribute :>> phase = MethodPhase::phase0_incrementFraming;
    attribute :>> subjectSelector = "increment";
    attribute :>> applicability = "unconditional";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "package-typed-member";
    attribute :>> targetFilter = "OutOfScopeItem lineage";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = *;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "at least one OutOfScopeItem part is owned by the increment package; no exclusion-completeness claim";
    ref item :>> prerequisites = incrementHasIdentifier;
  }

  item incrementHasOwner : MethodGate {
    doc /* Claim boundary: the increment charter carries one non-empty owner
         * value. No authority, assignment or competence claim. */
    attribute :>> obligationId = "incrementHasOwner";
    attribute :>> phase = MethodPhase::phase0_incrementFraming;
    attribute :>> subjectSelector = "increment";
    attribute :>> applicability = "unconditional";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "charter-attribute-value";
    attribute :>> targetFilter = "IncrementCharter owner; non-empty String";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = 1;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "the increment charter carries one non-empty owner value; no authority, assignment or competence claim";
    ref item :>> prerequisites = incrementHasCharter;
  }

  item incrementDeclaresApplicablePhases : MethodGate {
    doc /* Claim boundary: the increment charter declares at least one
         * applicable MethodPhase literal. Declaring a phase is not completing
         * it; it makes that phase's gates applicable. */
    attribute :>> obligationId = "incrementDeclaresApplicablePhases";
    attribute :>> phase = MethodPhase::phase0_incrementFraming;
    attribute :>> subjectSelector = "increment";
    attribute :>> applicability = "unconditional";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "charter-attribute-value";
    attribute :>> targetFilter = "IncrementCharter applicablePhases; MethodPhase literal";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = *;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "the increment charter declares at least one applicable MethodPhase literal; declaration only, no phase completion claim";
    ref item :>> prerequisites = incrementHasCharter;
  }

  item incrementDeclaresExpectedArtifacts : MethodGate {
    doc /* Claim boundary: the increment charter lists at least one non-empty
         * expected artifact. No claim that the artifacts exist or are complete. */
    attribute :>> obligationId = "incrementDeclaresExpectedArtifacts";
    attribute :>> phase = MethodPhase::phase0_incrementFraming;
    attribute :>> subjectSelector = "increment";
    attribute :>> applicability = "unconditional";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "charter-attribute-value";
    attribute :>> targetFilter = "IncrementCharter expectedArtifacts; non-empty String";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = *;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "the increment charter lists at least one non-empty expected artifact; no artifact existence or completeness claim";
    ref item :>> prerequisites = incrementHasCharter;
  }

  item incrementDeclaresExpectedReviewEvidence : MethodGate {
    doc /* Claim boundary: the increment charter lists at least one non-empty
         * expected review evidence item. No claim that the evidence exists or
         * that a review passed. */
    attribute :>> obligationId = "incrementDeclaresExpectedReviewEvidence";
    attribute :>> phase = MethodPhase::phase0_incrementFraming;
    attribute :>> subjectSelector = "increment";
    attribute :>> applicability = "unconditional";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "charter-attribute-value";
    attribute :>> targetFilter = "IncrementCharter expectedReviewEvidence; non-empty String";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = *;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "the increment charter lists at least one non-empty expected review evidence item; no evidence existence or review outcome claim";
    ref item :>> prerequisites = incrementHasCharter;
  }

  // Needs gates

  comment about needHasStatement, needHasStakeholder, needHasSource,
      needHasRationale, needHasValidationScenario
    /* Needs rule: each need has a statement, at least one stakeholder, an
     * ODE4HERA source and rationale, and at least one planned validation
     * scenario. */

  comment about needFramesConcern
    /* Need-to-concern rule: each need frames at least one stakeholder concern
     * through native SysML v2 framing. This replaces the retired
     * need-from-concern derivation. */

  item needHasStatement : MethodGate {
    doc /* Claim boundary: each need of the increment owns at least one
         * required constraint (require constraint) as its statement. Framed
         * concerns do not count as a statement. No wording or verifiability
         * claim; those are advisory judgment checks without a gate. */
    attribute :>> obligationId = "needHasStatement";
    attribute :>> phase = MethodPhase::phase4_needs;
    attribute :>> subjectSelector = "incrementNeeds";
    attribute :>> applicability = "increment declares the gate phase";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "required-constraint";
    attribute :>> targetFilter = "require constraint; framed concerns excluded";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = *;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "each need owns at least one require constraint as its statement; no wording or verifiability claim";
    ref item :>> prerequisites = incrementDeclaresApplicablePhases;
  }

  item needHasStakeholder : MethodGate {
    doc /* Claim boundary: each need has at least one native stakeholder
         * member typed in the Stakeholder lineage. No assignment of a real
         * person or authority. */
    attribute :>> obligationId = "needHasStakeholder";
    attribute :>> phase = MethodPhase::phase4_needs;
    attribute :>> subjectSelector = "incrementNeeds";
    attribute :>> applicability = "increment declares the gate phase";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "stakeholder-membership";
    attribute :>> targetFilter = "Stakeholder lineage";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = *;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "each need has at least one native Stakeholder-lineage stakeholder member; no assignment or authority claim";
    ref item :>> prerequisites = incrementDeclaresApplicablePhases;
  }

  item needHasSource : MethodGate {
    doc /* Claim boundary: each need carries one non-empty value of the
         * ODE4HERA requirements-management source attribute. No claim that
         * the source is correct or authoritative. */
    attribute :>> obligationId = "needHasSource";
    attribute :>> phase = MethodPhase::phase4_needs;
    attribute :>> subjectSelector = "incrementNeeds";
    attribute :>> applicability = "increment declares the gate phase";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "requirement-attribute-value";
    attribute :>> targetFilter = "ODE4HERA source; non-empty String";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = 1;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "each need carries one non-empty ODE4HERA source value; no source-correctness claim";
    ref item :>> prerequisites = incrementDeclaresApplicablePhases;
  }

  item needHasRationale : MethodGate {
    doc /* Claim boundary: each need carries one non-empty value of the
         * ODE4HERA requirements-management rationale attribute. No claim
         * that the rationale is sound. */
    attribute :>> obligationId = "needHasRationale";
    attribute :>> phase = MethodPhase::phase4_needs;
    attribute :>> subjectSelector = "incrementNeeds";
    attribute :>> applicability = "increment declares the gate phase";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "requirement-attribute-value";
    attribute :>> targetFilter = "ODE4HERA rationale; non-empty String";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = 1;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "each need carries one non-empty ODE4HERA rationale value; no soundness claim";
    ref item :>> prerequisites = incrementDeclaresApplicablePhases;
  }

  item needHasValidationScenario : MethodGate {
    doc /* Claim boundary: each need is the source end of at least one
         * ValidationPlanningAssociation to a ValidationPlanningScenario.
         * Planning only: no validation execution, result or fitness-for-use
         * verdict. */
    attribute :>> obligationId = "needHasValidationScenario";
    attribute :>> phase = MethodPhase::phase4_needs;
    attribute :>> subjectSelector = "incrementNeeds";
    attribute :>> applicability = "increment declares the gate phase";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "hasValidationScenario";
    attribute :>> targetFilter = "ValidationPlanningScenario lineage; through a ValidationPlanningAssociation connection";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = *;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "each need has at least one planned validation scenario association; planning only, no validation result or fitness-for-use verdict";
    ref item :>> prerequisites = incrementDeclaresApplicablePhases;
  }

  item needFramesConcern : MethodGate {
    doc /* Claim boundary: each need owns at least one native framed-concern
         * membership whose concern references a concern usage with at least
         * one stakeholder member. In SysML v2 a framed concern is a required
         * subrequirement of the need: the need declares that it addresses
         * the concern. No claim that the concern is satisfied, and no
         * derivation provenance. */
    attribute :>> obligationId = "needFramesConcern";
    attribute :>> phase = MethodPhase::phase4_needs;
    attribute :>> subjectSelector = "incrementNeeds";
    attribute :>> applicability = "increment declares the gate phase";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "framed-concern-membership";
    attribute :>> targetFilter = "ConcernUsage with at least one native stakeholder member";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = *;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "each need natively frames at least one stakeholder concern; framing only, no concern satisfaction or derivation claim";
    ref item :>> prerequisites = incrementDeclaresApplicablePhases;
  }

  // Requirements gates

  comment about requirementDerivesFromNeed
    /* Requirement-to-need rule: only the governed DerivesFromNeed connection
     * counts; plain dependencies do not. */

  comment about requirementHasOneSubject, requirementHasVerificationMethod
    /* Requirement rule: exactly one native subject, and exactly one primary
     * verification method from the standard kinds. */

  item requirementDerivesFromNeed : MethodGate {
    doc /* Claim boundary: each requirement is the derivedRequirement end of at
         * least one DerivesFromNeed connection whose need end is in the
         * StakeholderNeedCandidate lineage. A plain dependency never counts.
         * Provenance only: no satisfaction, implication or verification. */
    attribute :>> obligationId = "requirementDerivesFromNeed";
    attribute :>> phase = MethodPhase::phase5_requirements;
    attribute :>> subjectSelector = "incrementRequirements";
    attribute :>> applicability = "increment declares the gate phase";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "derivesRequirementFromNeed";
    attribute :>> targetFilter = "StakeholderNeedCandidate lineage; through a DerivesFromNeed connection only; plain dependencies excluded";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = *;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "each requirement derives from at least one need through a DerivesFromNeed connection; provenance only, no satisfaction or verification claim";
    ref item :>> prerequisites = incrementDeclaresApplicablePhases;
  }

  item requirementHasOneSubject : MethodGate {
    doc /* Claim boundary: each requirement has exactly one native subject
         * member. No claim about what the subject is or that it satisfies the
         * requirement. */
    attribute :>> obligationId = "requirementHasOneSubject";
    attribute :>> phase = MethodPhase::phase5_requirements;
    attribute :>> subjectSelector = "incrementRequirements";
    attribute :>> applicability = "increment declares the gate phase";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "subject-membership";
    attribute :>> targetFilter = "";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = 1;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "each requirement has exactly one native subject member; no satisfaction claim";
    ref item :>> prerequisites = incrementDeclaresApplicablePhases;
  }

  item requirementHasVerificationMethod : MethodGate {
    doc /* Claim boundary: each requirement records exactly one primary
         * verification method: its ODE4HERA verificationMethod value is one
         * of the standard kinds inspect, demo, test or analyze. Planning
         * only: no verification result or evidence. */
    attribute :>> obligationId = "requirementHasVerificationMethod";
    attribute :>> phase = MethodPhase::phase5_requirements;
    attribute :>> subjectSelector = "incrementRequirements";
    attribute :>> applicability = "increment declares the gate phase";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "requirement-attribute-value";
    attribute :>> targetFilter = "ODE4HERA verificationMethod; one of inspect, demo, test, analyze";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = 1;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "each requirement records exactly one standard verification method kind; planning only, no verification result";
    ref item :>> prerequisites = incrementDeclaresApplicablePhases;
  }

  item requirementSpecifiesFeatureOrCapability : MethodGate {
    doc /* Advisory. Claim boundary: each requirement traces to at least one
         * product-line feature candidate or common capability. The governed
         * specifiesFeature and specifiesCommonCapability relations have no
         * native carrier at this revision, so this gap is reported, never
         * blocking. No product-line classification claim. */
    attribute :>> obligationId = "requirementSpecifiesFeatureOrCapability";
    attribute :>> phase = MethodPhase::phase5_requirements;
    attribute :>> subjectSelector = "incrementRequirements";
    attribute :>> applicability = "increment declares the gate phase";
    attribute :>> minimumPopulation = 0;
    attribute :>> permittedEmpty = true;
    attribute :>> predicate = "specifiesFeatureOrCommonCapability";
    attribute :>> targetFilter = "ProductLineFeatureCandidate or CommonProductLineCapability lineage";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = *;
    attribute :>> required = false;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "each requirement traces to at least one feature candidate or common capability; advisory, no classification claim";
    ref item :>> prerequisites = incrementDeclaresApplicablePhases;
    attribute :>> permittedEmptyDisposition = PermittedEmptyDisposition::noEligibleSubjects;
  }

  // V&V and evidence gates

  comment about verificationCaseVerifiesRequirement,
      requirementVerifiedByVerificationCase
    /* Verification rule: each verification case verifies at least one
     * requirement of the increment, and every in-scope requirement is
     * verified by at least one verification case. */

  comment about requirementSpecifiesFeatureOrCapability,
      verificationCaseVerifiesAcceptanceCriterion, verificationCaseHasEvidenceRecordOrStatus
    /* Advisory rule: requirement to feature or common capability,
     * acceptance-criterion targets, and evidence record or status are
     * advisory, not blocking. */

  item verificationCaseVerifiesRequirement : MethodGate {
    doc /* Claim boundary: the objective of each verification case of the
         * increment verifies at least one requirement of the increment
         * requirements population, owned or inherited from the case
         * definition. No verification result, evidence or acceptance. */
    attribute :>> obligationId = "verificationCaseVerifiesRequirement";
    attribute :>> phase = MethodPhase::phase10_vvEvidence;
    attribute :>> subjectSelector = "incrementVerificationCases";
    attribute :>> applicability = "increment declares the gate phase";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "verifies";
    attribute :>> targetFilter = "requirement usage in the increment requirements population";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = *;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "each verification case objective verifies at least one requirement of the increment; no result, evidence or acceptance claim";
    ref item :>> prerequisites = incrementDeclaresApplicablePhases;
  }

  item requirementVerifiedByVerificationCase : MethodGate {
    doc /* Claim boundary: each in-scope requirement of the increment is
         * natively verified by at least one verification case. When the
         * increment owns no requirement, the gate is not applicable. No
         * verification result, evidence or acceptance. */
    attribute :>> obligationId = "requirementVerifiedByVerificationCase";
    attribute :>> phase = MethodPhase::phase10_vvEvidence;
    attribute :>> subjectSelector = "incrementRequirements";
    attribute :>> applicability = "increment declares the gate phase";
    attribute :>> minimumPopulation = 0;
    attribute :>> permittedEmpty = true;
    attribute :>> predicate = "verifiedBy";
    attribute :>> targetFilter = "VerificationCaseUsage";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = *;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "each in-scope requirement is verified by at least one verification case; no result, evidence or acceptance claim";
    ref item :>> prerequisites = incrementDeclaresApplicablePhases;
    attribute :>> permittedEmptyDisposition = PermittedEmptyDisposition::noEligibleSubjects;
  }

  item verificationCaseVerifiesAcceptanceCriterion : MethodGate {
    doc /* Advisory. Claim boundary: the objective of each verification case
         * verifies at least one requirement in the AcceptanceCriterion
         * lineage. A test-verdict criterion, not an acceptance decision. */
    attribute :>> obligationId = "verificationCaseVerifiesAcceptanceCriterion";
    attribute :>> phase = MethodPhase::phase10_vvEvidence;
    attribute :>> subjectSelector = "incrementVerificationCases";
    attribute :>> applicability = "increment declares the gate phase";
    attribute :>> minimumPopulation = 0;
    attribute :>> permittedEmpty = true;
    attribute :>> predicate = "verifies";
    attribute :>> targetFilter = "AcceptanceCriterion lineage";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = *;
    attribute :>> required = false;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "each verification case objective verifies at least one acceptance criterion; advisory, test-verdict criterion only, no acceptance decision";
    ref item :>> prerequisites = incrementDeclaresApplicablePhases;
    attribute :>> permittedEmptyDisposition = PermittedEmptyDisposition::noEligibleSubjects;
  }

  item verificationCaseHasEvidenceRecordOrStatus : MethodGate {
    doc /* Advisory. Claim boundary: each verification case has at least one
         * evidence record or evidence status. Evidence content stays
         * external; no native case-to-evidence relation exists at this
         * revision. No result, adequacy or acceptance claim. */
    attribute :>> obligationId = "verificationCaseHasEvidenceRecordOrStatus";
    attribute :>> phase = MethodPhase::phase10_vvEvidence;
    attribute :>> subjectSelector = "incrementVerificationCases";
    attribute :>> applicability = "increment declares the gate phase";
    attribute :>> minimumPopulation = 0;
    attribute :>> permittedEmpty = true;
    attribute :>> predicate = "evidence-record-or-status";
    attribute :>> targetFilter = "evidence record referencing the verification case, or an evidence status of the case";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = *;
    attribute :>> required = false;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "each verification case has at least one evidence record or evidence status; advisory, no result, adequacy or acceptance claim";
    ref item :>> prerequisites = incrementDeclaresApplicablePhases;
    attribute :>> permittedEmptyDisposition = PermittedEmptyDisposition::noEligibleSubjects;
  }
}
