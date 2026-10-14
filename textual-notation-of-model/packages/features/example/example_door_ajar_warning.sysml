/*
 * INC-EXAMPLE-001, a method test (reserved EXAMPLE subject): a door-ajar
 * warning, authored only from the what_to_author lines the method tools
 * return for a new increment (B3). Throwaway; never merged.
 */
package DE4SDV_ExampleDoorAjarWarning {

  // Imports: the union of the remedies' Import lines.
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_IncrementWorkflow::*;
  private import DE4SDV_MethodProcess::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_TraceVocabulary::*;

  // incrementHasIdentifier (also the first line of incrementHasProblemStatement and incrementHasStakeholder):
  // the increment's own definition first, then the usage typed by it
  part def DoorAjarWarningIncrement :> DE4SDV_MethodContext::EngineeringIncrement;
  part <'INC-EXAMPLE-001'> incExample001 : DoorAjarWarningIncrement;

  // needSubjectIsSystemOfInterest / requirementSubjectIsSystemOfInterest (system of interest first)
  part def DoorMonitor { doc /* The vehicle function that detects an open door and warns the driver. */ }
  part doorMonitor : DoorMonitor;

  // incrementHasCharter, incrementHasOwner, incrementDeclaresApplicablePhases,
  // incrementDeclaresExpectedArtifacts (and expectedArtifactsCoverIncrementContent),
  // incrementDeclaresExpectedReviewEvidence, and the systemOfInterest line of the two
  // subjectIsSystemOfInterest remedies
  part exampleCharter : DE4SDV_IncrementWorkflow::IncrementCharter {
    ref part :>> increment = incExample001;
    attribute :>> owner = "DE4SDV maintainers (method test)";
    attribute :>> applicablePhases = (DE4SDV_MethodProcess::MethodPhase::phase0_incrementFraming, DE4SDV_MethodProcess::MethodPhase::phase4_needs, DE4SDV_MethodProcess::MethodPhase::phase5_requirements, DE4SDV_MethodProcess::MethodPhase::phase10_vvEvidence);
    attribute :>> expectedArtifacts = ("DE4SDV_ExampleDoorAjarWarning");
    attribute :>> expectedReviewEvidence = ("PR Method Check report on the exact head", "licensed Syside validation of the exact head");
    ref part :>> systemOfInterest = doorMonitor;
  }

  // incrementHasProblemStatement, incrementHasStakeholder
  requirement exampleProblemStatement : DE4SDV_MethodContext::ProblemStatement {
    subject increment : DoorAjarWarningIncrement;
    stakeholder driver : DE4SDV_Stakeholders::Stakeholder;
  }

  // incrementHasEngineeringQuestion
  part exampleQuestion : DE4SDV_MethodContext::IncrementEngineeringQuestion { doc /* Which warning makes a driver notice an open door before driving off? */ }

  // incrementHasLifecycleDecision
  part exampleDecision : DE4SDV_MethodContext::IncrementLifecycleDecision { doc /* Decide whether the warning requirement is ready as design input. */ }

  // incrementHasAssumption
  part exampleAssumption : DE4SDV_MethodContext::IncrementAssumption { doc /* Every door reports a closed-latch signal. */ }

  // incrementHasScope
  part exampleScope : DE4SDV_MethodContext::IncrementScope { doc /* The open-door warning to the driver while the vehicle is powered. */ }

  // incrementHasOutOfScopeItem
  part exampleOutOfScope : DE4SDV_MethodContext::OutOfScopeItem { doc /* Door locking and the latch hardware are out of scope. */ }

  // incrementHasFramedConcern
  concern doorAjarAwareness { subject; stakeholder driver : DE4SDV_Stakeholders::Stakeholder; }
  viewpoint def DoorAjarWarningViewpoint { doc /* Shows the concern the door-ajar warning addresses. */ }
  view doorAjarWarningView { viewpoint doorAjarWarningViewpoint : DoorAjarWarningViewpoint { frame doorAjarAwareness; } }

  // needHasStatement, needHasStakeholder, needHasSource, needHasRationale, needSubjectIsSystemOfInterest
  requirement needDoorAjarNoticed : DE4SDV_MethodContext::StakeholderNeedCandidate {
    subject monitoredSystem :> doorMonitor;
    stakeholder driver : DE4SDV_Stakeholders::Stakeholder;
    require constraint statement { language "English" /* The driver needs to notice a door that is not fully closed before driving off. */ }
    attribute :>> source = "Method test content (illustrative source)";
    attribute :>> rationale = "A door that opens while driving endangers the occupants.";
  }

  // needHasValidationScenario
  part openDoorAtStandstill : DE4SDV_TraceVocabulary::ValidationPlanningScenario;
  connection doorAjarNoticedValidatedAtStandstill : DE4SDV_TraceVocabulary::ValidationPlanningAssociation connect needDoorAjarNoticed to openDoorAtStandstill;

  // requirementHasStatement, requirementHasOneSubject, requirementHasVerificationMethod,
  // requirementStatesSuccessCriteria, requirementSubjectIsSystemOfInterest
  requirement reqDoorAjarIndication : DE4SDV_MethodContext::RequirementCandidate {
    subject monitoredSystem :> doorMonitor;
    require constraint statement { language "English" /* The door monitor shall indicate an open door to the driver within 1 s while the vehicle is powered. */ }
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "With each door opened in turn at standstill, the indication appears within 1 s and clears within 1 s of closing.";
  }

  // requirementDerivesFromNeed
  connection doorAjarIndicationDerivesFromNoticed : DE4SDV_TraceVocabulary::DerivesFromNeed connect needDoorAjarNoticed to reqDoorAjarIndication;

  // verificationCaseVerifiesRequirement, requirementVerifiedByVerificationCase
  verification doorAjarIndicationTest { objective { verify reqDoorAjarIndication; } }
}
