/*
 * DE4SDV closed-loop driving stakeholder needs and design-input requirements.
 *
 * INC-DRIVING-001, phase 4: the stakeholder needs of the candidate driving
 * system, the system of interest the charter declares. Each need is
 * elaborated from one non-boundary concern of phase 1 and traces to it
 * through the concern's stakeholders, its source and its rationale; each
 * has a planned stakeholder review on a scenario of phase 2. Phase 5 adds
 * the requirements derived from these needs to this package. No safety,
 * on-road or production-readiness claim is made, and no member product is
 * claimed.
 */

package DE4SDV_ClosedLoopDrivingNeedsRequirements {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_TraceVocabulary::*;
  private import DE4SDV_Stakeholders::*;
  private import SAF_Viewpoints::*;
  private import SysideViews::**;
  private import Views::*;

  /* ───────────────────── Phase 4: stakeholder needs ───────────────────── */

  requirement <'NEED-DRIVING-001'> needCheckpointPlansMoveTheVehicle : StakeholderNeedCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
    require constraint statement { language "English" /* Systems engineers, verification engineers and open-source reviewers need the steering and acceleration of the vehicle to follow the plans that the pinned AutoE2E checkpoint makes from the vehicle's live camera images and motion, with no autopilot, replayed history, prediction overlay or other command source acting in their place. */ }
    attribute :>> source = "INC-DRIVING-001 checkpointCommandAuthorityConcern, scope item learnedDrivingInScope, assumption asmSourceAuthenticity, scenario SC-DRIVING-001";
    attribute :>> rationale = "The increment shows closed-loop driving only if the checkpoint's own plans move the vehicle and the vehicle's new motion changes what the checkpoint plans next; a command from any other source turns the loop into a trajectory preview.";
  }

  requirement <'NEED-DRIVING-002'> needCheckpointInputsAsTrained : StakeholderNeedCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
    require constraint statement { language "English" /* Systems engineers and verification engineers need the pinned AutoE2E checkpoint to plan from inputs in the form its runtime contract fixes: the camera images with the calibration of the cameras that took them, the ego-motion history of the vehicle, and the map around the vehicle with the route to its destination, aligned in time with one another. */ }
    attribute :>> source = "INC-DRIVING-001 checkpointCommandAuthorityConcern, assumption asmSourceAuthenticity (the pinned checkpoint and its compatible input geometry and history), gap gapModelInputAndFeedback, scenario SC-DRIVING-001; the runtime contract of AutoE2E at cb50764b (Model/README.md: surround camera images with a projection operator that carries their calibration, a semantic map raster with the route corridor and destination, and an ego-motion history of speed, acceleration, yaw rate and curvature; Model/data_parsing/nvidia_physical_ai/egomotion.py: 64 history samples at 10 Hz); owner review of 2026-11-02 (ego motion)";
    attribute :>> rationale = "A checkpoint given inputs other than those it was trained on plans for a different problem: another camera geometry, a missing or misaligned motion history or a missing route leaves its plans meaningless even when every interface accepts the data.";
  }

  requirement <'NEED-DRIVING-003'> needPlansAndCommandsThroughSCORE : StakeholderNeedCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder softwareDeveloper : SoftwareDeveloper;
    stakeholder maintainer : Maintainer;
    require constraint statement { language "English" /* System architects, software developers and maintainers need the plans and commands of the driving system to pass between planning and the vehicle's actuation through Eclipse S-CORE communication, with no exchange on that path that goes around it. */ }
    attribute :>> source = "INC-DRIVING-001 scoreCommandPathConcern, scope item integrationAndObservationInScope (S-CORE part), gap gapTransportAndControl, assumption asmCandidateReuse, scenario SC-DRIVING-001";
    attribute :>> rationale = "The increment evaluates S-CORE on a functional path. An exchange that skips S-CORE means it is not on the path, and a direct connection from the planner to the vehicle would hide that while the loop still drives.";
  }

  requirement <'NEED-DRIVING-004'> needLiveStateForAAOS : StakeholderNeedCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
    require constraint statement { language "English" /* Verification engineers and open-source reviewers need the driving system to publish its plan, the vehicle state and its health as it produces them in the running loop, each with its producer and its time, so that what AAOS SDV presents is this run and a stale, mocked or replayed state cannot pass for it. */ }
    attribute :>> source = "INC-DRIVING-001 aaosObservationFidelityConcern, scope item integrationAndObservationInScope (AAOS part), gap gapTransportAndControl, scenario SC-DRIVING-002; owner decision 2026-11-02 (AAOS SDV is a context role)";
    attribute :>> rationale = "AAOS SDV shows reviewers the closed loop only if what reaches it is the live output of this run attributed to its producer; with the producer and the time, a receiver can also tell a state that stopped arriving from a current one.";
  }

  requirement <'NEED-DRIVING-005'> needLoopIndependentOfAAOS : StakeholderNeedCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
    require constraint statement { language "English" /* Verification engineers and open-source reviewers need the driving system to go on planning and commanding the vehicle unchanged, without its degraded-input response, when AAOS SDV, its application or the path to it is down or late. */ }
    attribute :>> source = "INC-DRIVING-001 aaosObservationFidelityConcern (AAOS SDV typed as a context role), gap gapTransportAndControl (the display is not in the fast control loop), scenario SC-DRIVING-004; owner decision 2026-11-02 (removing AAOS SDV leaves the plan-to-command chain unchanged)";
    attribute :>> rationale = "AAOS SDV observes the loop and is no part of it. If its absence or delay changed planning or commands, observation would become a dependency of driving and the context-role decision would not hold.";
  }

  requirement <'NEED-DRIVING-006'> needDefinedResponseToDegradedInputOrPlan : StakeholderNeedCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    stakeholder safetyExpert : SafetyExpert;
    stakeholder systemArchitect : SystemArchitect;
    require constraint statement { language "English" /* Safety experts and system architects need the driving system, when the camera images or the motion of the vehicle become invalid, lost or stale, or a plan becomes invalid, late, lost or stale, to give the vehicle a defined stop or disable response instead of acting on the last plan, and to publish that it is degraded. */ }
    attribute :>> source = "INC-DRIVING-001 degradedInputBehaviorConcern, scope item feedbackAndTimingInScope (behavior part), gap gapTransportAndControl, scenario SC-DRIVING-003";
    attribute :>> rationale = "A learned planner given a frozen or late input still produces a plausible plan, so without a defined response the vehicle acts on a world that has moved on. Phase 5 fixes the response and its deadlines; the response is shown in simulation and carries no safety claim.";
  }

  requirement <'NEED-DRIVING-007'> needTimesMeasurableInTheirOwnDomain : StakeholderNeedCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder systemsEngineer : SystemsEngineer;
    require constraint statement { language "English" /* Verification engineers and systems engineers need the driving system to carry the time of each camera image, motion sample, plan and command with it, so that the age of an input at actuation, the planning cadence and the transport delay can each be measured in its own time domain and simulation time is never read as wall-clock time. */ }
    attribute :>> source = "INC-DRIVING-001 timeDomainHonestyConcern, scope item feedbackAndTimingInScope (timing part), gap gapClosedLoopPerformance";
    attribute :>> rationale = "Each timing claim needs a measurement in its own time domain; a rate or an age measured in one domain and read in another leaves the claim unfounded. Phase 5 fixes the limits themselves (gapClosedLoopPerformance).";
  }

  requirement <'NEED-DRIVING-008'> needRunsIdentifyCheckpointAndConfiguration : StakeholderNeedCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder maintainer : Maintainer;
    stakeholder reviewer : OpenSourceReviewer;
    require constraint statement { language "English" /* Verification engineers, maintainers and open-source reviewers need each run of the driving system to identify the checkpoint and the configuration it ran with, so that another engineer can rerun it and an undisclosed checkpoint swap shows. */ }
    attribute :>> source = "INC-DRIVING-001 reproducibleClosedLoopEvidenceConcern, scope item closedLoopEvidenceInScope, out-of-scope item modelTrainingOutOfScope (no undisclosed checkpoint swap), gap gapAdoptionAndRights (source, checkpoint and configuration pinned separately)";
    attribute :>> rationale = "Closed-loop evidence can be rerun only if each run names what ran. The scenario and the bench belong to System 2 and are pinned there, so this need covers only what the driving system itself runs.";
  }

  /* ───────────────── Phase 4: planned stakeholder reviews ───────────────── */

  part <'SC-DRIVING-005'> checkpointAuthorityValidationPlan : ValidationPlanningScenario {
    doc /* For NEED-DRIVING-001, a planned stakeholder review. While the
         * driving system runs the closed-loop scenario (SC-DRIVING-001), can
         * systems engineers, verification engineers and open-source reviewers
         * confirm that each steering and acceleration command derives from a
         * plan of the pinned checkpoint, that the next camera images reflect
         * the motion those commands caused, and that no autopilot, replay or
         * overlay issued a command? */
  }
  connection checkpointAuthorityValidationPlanning : ValidationPlanningAssociation
    connect needCheckpointPlansMoveTheVehicle to checkpointAuthorityValidationPlan;
  dependency checkpointAuthorityValidationFromClosedLoopScenario
    from checkpointAuthorityValidationPlan
    to DE4SDV_ClosedLoopDrivingOperationalContext::driveOnCheckpointPlans;

  part <'SC-DRIVING-006'> checkpointInputsValidationPlan : ValidationPlanningScenario {
    doc /* For NEED-DRIVING-002, a planned stakeholder review. While the
         * closed-loop scenario runs (SC-DRIVING-001), can systems engineers
         * and verification engineers confirm against the runtime contract of
         * the pinned checkpoint that the camera images carry the calibration
         * of the cameras that took them, that the ego-motion history has the
         * signals, sample count and spacing the checkpoint expects, that the
         * map and the route are present, and that all of them are aligned in
         * time? */
  }
  connection checkpointInputsValidationPlanning : ValidationPlanningAssociation
    connect needCheckpointInputsAsTrained to checkpointInputsValidationPlan;
  dependency checkpointInputsValidationFromClosedLoopScenario
    from checkpointInputsValidationPlan
    to DE4SDV_ClosedLoopDrivingOperationalContext::driveOnCheckpointPlans;

  part <'SC-DRIVING-007'> scoreCommandPathValidationPlan : ValidationPlanningScenario {
    doc /* For NEED-DRIVING-003, a planned stakeholder review. While the
         * closed-loop scenario runs (SC-DRIVING-001), can system architects,
         * software developers and maintainers confirm that every plan and
         * command between planning and actuation passed through Eclipse
         * S-CORE communication, and that no other exchange on that path
         * carried them? */
  }
  connection scoreCommandPathValidationPlanning : ValidationPlanningAssociation
    connect needPlansAndCommandsThroughSCORE to scoreCommandPathValidationPlan;
  dependency scoreCommandPathValidationFromClosedLoopScenario
    from scoreCommandPathValidationPlan
    to DE4SDV_ClosedLoopDrivingOperationalContext::driveOnCheckpointPlans;

  part <'SC-DRIVING-008'> liveStateValidationPlan : ValidationPlanningScenario {
    doc /* For NEED-DRIVING-004, a planned stakeholder review. While the
         * observation scenario runs (SC-DRIVING-002), can verification
         * engineers and open-source reviewers confirm that each plan, vehicle
         * state and health item that reached AAOS SDV matches what the
         * driving system produced in that run, with its producer and its
         * time, and that a state that stopped arriving was not shown as
         * live? */
  }
  connection liveStateValidationPlanning : ValidationPlanningAssociation
    connect needLiveStateForAAOS to liveStateValidationPlan;
  dependency liveStateValidationFromObservationScenario
    from liveStateValidationPlan
    to DE4SDV_ClosedLoopDrivingOperationalContext::showLiveStateOnAAOS;

  part <'SC-DRIVING-009'> aaosIndependenceValidationPlan : ValidationPlanningScenario {
    doc /* For NEED-DRIVING-005, a planned stakeholder review. While AAOS
         * SDV, its application or the path to it is down or late
         * (SC-DRIVING-004), can verification engineers and open-source
         * reviewers confirm that planning and commands go on as in a run
         * with AAOS SDV available, and that the degraded-input response did
         * not trigger? */
  }
  connection aaosIndependenceValidationPlanning : ValidationPlanningAssociation
    connect needLoopIndependentOfAAOS to aaosIndependenceValidationPlan;
  dependency aaosIndependenceValidationFromAAOSUnavailableScenario
    from aaosIndependenceValidationPlan
    to DE4SDV_ClosedLoopDrivingOperationalContext::continueWithoutAAOS;

  part <'SC-DRIVING-010'> degradedResponseValidationPlan : ValidationPlanningScenario {
    doc /* For NEED-DRIVING-006, a planned stakeholder review. In the
         * degraded input or plan scenario (SC-DRIVING-003), can safety
         * experts and system architects confirm for each injected case
         * (invalid, lost or stale camera images or motion; an invalid, late,
         * lost or stale plan) that the vehicle received the defined stop or
         * disable response instead of a command from the last plan, and that
         * the driving system published its degraded state? */
  }
  connection degradedResponseValidationPlanning : ValidationPlanningAssociation
    connect needDefinedResponseToDegradedInputOrPlan to degradedResponseValidationPlan;
  dependency degradedResponseValidationFromDegradedScenario
    from degradedResponseValidationPlan
    to DE4SDV_ClosedLoopDrivingOperationalContext::respondToDegradedInputOrPlan;

  part <'SC-DRIVING-011'> timeDomainValidationPlan : ValidationPlanningScenario {
    doc /* For NEED-DRIVING-007, a planned stakeholder review. While the
         * closed-loop scenario runs (SC-DRIVING-001), can verification
         * engineers and systems engineers measure the age of the inputs at
         * actuation, the planning cadence and the transport delay from the
         * times the driving system carries, each in its own time domain, and
         * confirm that no measurement mixes simulation time with wall-clock
         * time? */
  }
  connection timeDomainValidationPlanning : ValidationPlanningAssociation
    connect needTimesMeasurableInTheirOwnDomain to timeDomainValidationPlan;
  dependency timeDomainValidationFromClosedLoopScenario
    from timeDomainValidationPlan
    to DE4SDV_ClosedLoopDrivingOperationalContext::driveOnCheckpointPlans;

  part <'SC-DRIVING-012'> rerunValidationPlan : ValidationPlanningScenario {
    doc /* For NEED-DRIVING-008, a planned stakeholder review. After a
         * bounded closed-loop run, can verification engineers, maintainers
         * and open-source reviewers rerun it from the checkpoint and the
         * configuration the run identifies, together with the scenario that
         * System 2 pins, and confirm that a run with another checkpoint
         * identifies that other checkpoint? */
  }
  connection rerunValidationPlanning : ValidationPlanningAssociation
    connect needRunsIdentifyCheckpointAndConfiguration to rerunValidationPlan;
  dependency rerunValidationFromBoundedScenario
    from rerunValidationPlan
    to DE4SDV_ClosedLoopDrivingOperationalContext::driveBoundedScenarioClosedLoop;

  /* ─────────────────────────────── Views ─────────────────────────────── */

  concern closedLoopDrivingNeedsConcern : StakeholderNeedsConcern {
    doc /*
     * Reviewers need the stakeholder needs of the driving system with their
     * statements and sources, and the planned stakeholder review of each, to
     * judge whether the needs cover the concerns of phase 1.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view closedLoopDrivingNeedsView : TVD::TableView {
    viewpoint selectedNeedsViewpoint : StakeholderRequirementDefinitionViewpoint {
      frame closedLoopDrivingNeedsConcern;
    }

    expose needCheckpointPlansMoveTheVehicle;
    expose needCheckpointInputsAsTrained;
    expose needPlansAndCommandsThroughSCORE;
    expose needLiveStateForAAOS;
    expose needLoopIndependentOfAAOS;
    expose needDefinedResponseToDegradedInputOrPlan;
    expose needTimesMeasurableInTheirOwnDomain;
    expose needRunsIdentifyCheckpointAndConfiguration;
    filter @ SysML::RequirementUsage;
    attribute :>> includeReferenceElements = true;
    attribute :>> maxRowHeight = 300;
    view ID :> columnViews {
      attribute :>> featureToRender = CT::reqId;
    }
    view Need :> columnViews {
      attribute :>> featureToRender = CT::declaredName;
    }
    view Statement :> columnViews {
      attribute :>> featureToRender = CT::constraintLanguage {
        attribute constraintName = "statement";
        attribute constraintType = CL::ConT::required;
        attribute constraintLanguage = "English";
      }
      attribute :>> columnWidth = 360;
    }
    view Source :> columnViews {
      attribute :>> featureToRender = CT::attributeValue {
        attribute attributeName = "source";
      }
      attribute :>> columnWidth = 320;
    }
  }

  view closedLoopDrivingNeedValidationView : TVD::TableView {
    viewpoint selectedNeedValidationViewpoint : StakeholderRequirementDefinitionViewpoint {
      frame closedLoopDrivingNeedsConcern;
    }

    expose checkpointAuthorityValidationPlan;
    expose checkpointInputsValidationPlan;
    expose scoreCommandPathValidationPlan;
    expose liveStateValidationPlan;
    expose aaosIndependenceValidationPlan;
    expose degradedResponseValidationPlan;
    expose timeDomainValidationPlan;
    expose rerunValidationPlan;
    filter @ SysML::PartUsage;
    attribute :>> includeReferenceElements = true;
    attribute :>> maxRowHeight = 300;
    view ID :> columnViews {
      attribute :>> featureToRender = CT::reqId;
    }
    view Plan :> columnViews {
      attribute :>> featureToRender = CT::declaredName;
    }
    view Review :> columnViews {
      attribute :>> featureToRender = CT::documentation;
      attribute :>> columnWidth = 480;
    }
  }
}
