/*
 * DE4SDV closed-loop driving stakeholder needs and design-input requirements.
 *
 * INC-DRIVING-001, phase 4: the stakeholder needs of the candidate driving
 * system, the system of interest the charter declares. Each need is held by
 * the parties it serves, names in its source the non-boundary concern of
 * phase 1 it derives from, and traces to that concern through its
 * stakeholders and its rationale; each has a planned stakeholder review on
 * a scenario of phase 2, carried out by the roles that check the answer.
 * Phase 5: the requirements derived from these needs, each with one
 * subject, the candidate driving system, one verification method and its
 * success criteria. Their values come from the AutoE2E source at the
 * checkpoint pin cb50764b, which each rationale cites. The requirements are
 * not core: the driving system enters a member product only with the
 * driving stack that phase 3 records as the feature candidate
 * autoE2EDrivingStack, and phase 9 adds that feature to the feature model
 * and links the system of interest to it.
 * No safety, on-road or production-readiness claim is made, and no member
 * product is claimed.
 */

package DE4SDV_ClosedLoopDrivingNeedsRequirements {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_TraceVocabulary::*;
  private import DE4SDV_Stakeholders::*;
  private import SAF_Viewpoints::*;
  private import SysideViews::**;
  private import Views::*;

  /* ───────────────────── Phase 4: stakeholder needs ───────────────────── */

  requirement <'NEED-DRIVING-001'> needDrivenAlongTheRoute : StakeholderNeedCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    stakeholder occupant : VehicleOccupant;
    require constraint statement { language "English" /* Vehicle occupants need the vehicle to take them along the route to the destination the driver chose, steered and accelerated by the driving system's own plans, made from the vehicle's live camera images, its motion and the route. */ }
    attribute :>> source = "INC-DRIVING-001 drivenAlongTheRouteConcern, scope item learnedDrivingInScope, scenario SC-DRIVING-001 (the route from the navigation context role); the review answers checkpointCommandAuthorityConcern";
    attribute :>> rationale = "Occupants reach the destination the driver chose only if the driving system's own plans move the vehicle and its new motion changes what it plans next. The need states what the occupants expect, not how well the vehicle drives.";
  }

  requirement <'NEED-DRIVING-002'> needPlansAndCommandsThroughSCORE : StakeholderNeedCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder softwareDeveloper : SoftwareDeveloper;
    stakeholder maintainer : Maintainer;
    require constraint statement { language "English" /* System architects, software developers and maintainers need the plans and commands of the driving system to pass between planning and the vehicle's actuation through Eclipse S-CORE communication, with no exchange on that path that goes around it. */ }
    attribute :>> source = "INC-DRIVING-001 scoreCommandPathConcern, scope item integrationAndObservationInScope (S-CORE part), gap gapTransportAndControl, assumption asmCandidateReuse, scenario SC-DRIVING-001";
    attribute :>> rationale = "The increment evaluates S-CORE on a functional path. An exchange that skips S-CORE means it is not on the path, and a direct connection from the planner to the vehicle would hide that while the loop still drives.";
  }

  requirement <'NEED-DRIVING-003'> needLiveStateForAAOS : StakeholderNeedCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    stakeholder occupant : VehicleOccupant;
    stakeholder verificationEngineer : VerificationEngineer;
    require constraint statement { language "English" /* Vehicle occupants and verification engineers need the driving system to publish its plan, the vehicle state and its health as it produces them in the running loop, each with its producer and its time, so that what AAOS SDV presents is what the vehicle is doing now. */ }
    attribute :>> source = "INC-DRIVING-001 aaosObservationFidelityConcern, scope item integrationAndObservationInScope (AAOS part), gap gapTransportAndControl, scenario SC-DRIVING-002; owner decision 2026-11-02 (AAOS SDV is a context role)";
    attribute :>> rationale = "The driver sees on AAOS SDV what the vehicle is doing only if what reaches it is the live output of this run, attributed to its producer; with the producer and the time, a receiver can also tell a state that stopped arriving from a current one.";
  }

  requirement <'NEED-DRIVING-004'> needLoopIndependentOfAAOS : StakeholderNeedCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    stakeholder occupant : VehicleOccupant;
    require constraint statement { language "English" /* Vehicle occupants need the vehicle to keep driving when AAOS SDV, its application or the path to it is down or late: a failed or slow display neither stops the driving system nor changes how it plans and commands. */ }
    attribute :>> source = "INC-DRIVING-001 aaosObservationFidelityConcern (AAOS SDV typed as a context role), gap gapTransportAndControl (the display is not in the fast control loop), scenario SC-DRIVING-004; owner decision 2026-11-02 (removing AAOS SDV leaves the plan-to-command chain unchanged)";
    attribute :>> rationale = "AAOS SDV observes the loop and is no part of it. If its absence or delay changed planning or commands, observation would become a dependency of driving and the context-role decision would not hold.";
  }

  requirement <'NEED-DRIVING-005'> needDefinedResponseToDegradedInputOrPlan : StakeholderNeedCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    stakeholder occupant : VehicleOccupant;
    stakeholder roadUser : RoadUser;
    require constraint statement { language "English" /* Vehicle occupants and road users need the driving system, when the camera images, the motion of the vehicle or the route become invalid, lost or stale, or a plan becomes invalid, late, lost or stale, to give the vehicle a defined stop or disable response instead of acting on the last plan, and to publish that it is degraded. */ }
    attribute :>> source = "INC-DRIVING-001 degradedInputBehaviorConcern, scope item feedbackAndTimingInScope (behavior part), gap gapTransportAndControl, scenario SC-DRIVING-003";
    attribute :>> rationale = "A learned planner given a frozen or late input still produces a plausible plan, so without a defined response the vehicle acts on a world that has moved on. Phase 5 fixes the response and its deadlines; the response is shown in simulation and carries no safety claim.";
  }

  requirement <'NEED-DRIVING-006'> needTimesMeasurableInTheirOwnDomain : StakeholderNeedCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder systemsEngineer : SystemsEngineer;
    require constraint statement { language "English" /* Verification engineers and systems engineers need the driving system to carry the time of each camera image, motion sample, plan and command with it, so that the age of an input at actuation, the planning cadence and the transport delay can each be measured in its own time domain. */ }
    attribute :>> source = "INC-DRIVING-001 timeDomainHonestyConcern, scope item feedbackAndTimingInScope (timing part), gap gapClosedLoopPerformance";
    attribute :>> rationale = "Each timing claim needs a measurement in its own time domain; a rate or an age measured in one domain and read in another leaves the claim unfounded. Phase 5 fixes the limits themselves (gapClosedLoopPerformance).";
  }

  requirement <'NEED-DRIVING-007'> needRunsIdentifyCheckpointAndConfiguration : StakeholderNeedCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder maintainer : Maintainer;
    stakeholder reviewer : OpenSourceReviewer;
    require constraint statement { language "English" /* Verification engineers, maintainers and open-source reviewers need each run of the driving system to identify the checkpoint and the configuration it ran with, so that another engineer can rerun it. */ }
    attribute :>> source = "INC-DRIVING-001 reproducibleClosedLoopEvidenceConcern, scope item closedLoopEvidenceInScope, out-of-scope item modelTrainingOutOfScope (no undisclosed checkpoint swap), gap gapAdoptionAndRights (source, checkpoint and configuration pinned separately)";
    attribute :>> rationale = "Closed-loop evidence can be rerun only if each run names what ran. The scenario and the bench belong to System 2 and are pinned there, so this need covers only what the driving system itself runs.";
  }

  /* ───────────────── Phase 4: planned stakeholder reviews ───────────────── */

  part <'SC-DRIVING-005'> checkpointAuthorityValidationPlan : ValidationPlanningScenario {
    doc /* For NEED-DRIVING-001, a planned stakeholder review that
         * verification engineers and open-source reviewers carry out for the
         * occupants. While the driving system runs the closed-loop scenario
         * (SC-DRIVING-001), does the vehicle follow the route the driver
         * chose, with each steering and acceleration command derived from a
         * plan of the pinned checkpoint, the next camera images reflecting
         * the motion those commands caused, and no autopilot, replay or
         * overlay issuing a command? */
  }
  connection checkpointAuthorityValidationPlanning : ValidationPlanningAssociation
    connect needDrivenAlongTheRoute to checkpointAuthorityValidationPlan;
  dependency checkpointAuthorityValidationFromClosedLoopScenario
    from checkpointAuthorityValidationPlan
    to DE4SDV_ClosedLoopDrivingOperationalContext::driveOnCheckpointPlans;

  part <'SC-DRIVING-006'> scoreCommandPathValidationPlan : ValidationPlanningScenario {
    doc /* For NEED-DRIVING-002, a planned stakeholder review. While the
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

  part <'SC-DRIVING-007'> liveStateValidationPlan : ValidationPlanningScenario {
    doc /* For NEED-DRIVING-003, a planned stakeholder review. While the
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

  part <'SC-DRIVING-008'> aaosIndependenceValidationPlan : ValidationPlanningScenario {
    doc /* For NEED-DRIVING-004, a planned stakeholder review. While AAOS
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

  part <'SC-DRIVING-009'> degradedResponseValidationPlan : ValidationPlanningScenario {
    doc /* For NEED-DRIVING-005, a planned stakeholder review. In the
         * degraded input or plan scenario (SC-DRIVING-003), can safety
         * experts and system architects confirm for each injected case
         * (invalid, lost or stale camera images, motion or route; an invalid,
         * late, lost or stale plan) that the vehicle received the defined stop or
         * disable response instead of a command from the last plan, and that
         * the driving system published its degraded state? */
  }
  connection degradedResponseValidationPlanning : ValidationPlanningAssociation
    connect needDefinedResponseToDegradedInputOrPlan to degradedResponseValidationPlan;
  dependency degradedResponseValidationFromDegradedScenario
    from degradedResponseValidationPlan
    to DE4SDV_ClosedLoopDrivingOperationalContext::respondToDegradedInputOrPlan;

  part <'SC-DRIVING-010'> timeDomainValidationPlan : ValidationPlanningScenario {
    doc /* For NEED-DRIVING-006, a planned stakeholder review. While the
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

  part <'SC-DRIVING-011'> rerunValidationPlan : ValidationPlanningScenario {
    doc /* For NEED-DRIVING-007, a planned stakeholder review. After a
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

  /* ───────────────────── Phase 5: requirements ───────────────────── */

  requirement <'REQ-DRIVING-012'> reqPlanEachStepByCheckpointInference : FunctionalRequirementCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    require constraint statement { language "English" /* The driving system shall produce one plan for each 100 ms step of simulation time, by inference of the pinned AutoE2E checkpoint on the camera images, the ego-motion history and the route of that step. */ }
    attribute :>> source = "NEED-DRIVING-001; scenario SC-DRIVING-001; assumption asmSourceAuthenticity";
    attribute :>> rationale = "Checkpoint authority starts with plans the checkpoint itself makes from the inputs of the run. The source at the checkpoint pin cb50764b invokes the model at 10 Hz (MODEL_HZ in Model/navigation/geometry.py, OUTPUT_FREQUENCY_HZ in the AlpaSim driver plugin), and each plan holds 64 pairs of acceleration and curvature 0.1 s apart, a 6.4 s horizon in the vehicle frame, x forward and y left (the control contract in Tools/trajectory_visualization/kinematics.py). The step is counted in simulation time, the time of the vehicle's world, so a slower simulation does not thin out the plans.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when, in a run of SC-DRIVING-001, the records hold one plan for each 100 ms of simulation time from the end of priming to the end of the run or the start of the stop response, each naming the SHA-256 of the checkpoint it was inferred with, and an offline inference of that checkpoint on the inputs recorded for a plan, on the same host and software, gives every acceleration and curvature of that plan within 1 % of the largest magnitude of that signal in the plan.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-DRIVING-013'> reqCameraImagesInCheckpointForm : FunctionalRequirementCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    require constraint statement { language "English" /* The driving system shall give the checkpoint, for each step, the images of six cameras in the order front, front left, front right, rear left, rear and rear right, each resized to 512 by 512 pixels, the front image also at 1024 by 1024 pixels, the seven earlier images of each camera captured 0.5 s to 3.5 s before the step at 0.5 s intervals, and for every image a projection operator built from the calibration of its camera, scaled to its size and expressed in the vehicle frame of the step. */ }
    attribute :>> source = "NEED-DRIVING-001; gap gapModelInputAndFeedback (calibration, frames, image history); assumption asmSourceAuthenticity";
    attribute :>> rationale = "These are the camera inputs of the source at cb50764b: the six view slots of Model/data_parsing/camera_slots.py; tiles of 512 and a front tile of 1024 with eight frames per view 500 ms apart (Model/reactive_training_contracts.py; BEVFormer V2 T8 takes exactly eight frames); the geometry as a projection operator object, since matrix arguments are refused (Model/model_components/auto_e2e.py); and the projections of the earlier images re-expressed in the vehicle frame of the current step. The configuration the checkpoint records (camera_slots, view_fusion_kwargs) is compared with these values when it is pinned; a difference revises this requirement.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when the inputs recorded for every plan of a run of SC-DRIVING-001 hold six current images of 512 by 512 pixels in that order, a current front image of 1024 by 1024 pixels, and seven earlier images of each camera whose capture times lie 0.5 s to 3.5 s before the step at 0.5 s intervals, with one projection operator for each image, and when the operator of each camera maps a reference point at a known position in the vehicle frame to within 2 pixels of where that point appears in its image.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-DRIVING-014'> reqRouteAsNavigationRasters : FunctionalRequirementCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    require constraint statement { language "English" /* The driving system shall give the checkpoint, for each step, the map of the roads around the vehicle and the route from navigation as the map_context raster of 14 channels and the route_mask raster of two channels, route corridor and destination, both in the geometry autoe2e-bev-450x300-0p4m-v1 of 450 by 300 pixels at 0.4 m per pixel, brought to the time of the step. */ }
    attribute :>> source = "NEED-DRIVING-001; scenario SC-DRIVING-001 (the route from the navigation context role); gap gapModelInputAndFeedback";
    attribute :>> rationale = "AutoE2E is conditioned on a route raster, not on discrete commands. The geometry is the one the training and packing manifests of the source at cb50764b record (AUTOE2E_NAVIGATION_GEOMETRY in Model/navigation/geometry.py: 60 m behind to 120 m ahead and 60 m to each side); the module default is another geometry of 256 by 256 pixels at 1.0 m per pixel, so the geometry is named. The route channels are the selected corridor and the destination. The source renders the rasters at 2 Hz and warps them to each 10 Hz step with the localization of the vehicle.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when the inputs recorded for every plan of a run of SC-DRIVING-001 hold a map_context of 14 channels and a route_mask of two channels, both of 450 by 300 pixels and tagged with the geometry autoe2e-bev-450x300-0p4m-v1, whose route corridor covers the route navigation gave for the run, and whose raster was rendered no more than 500 ms of simulation time before the step.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-DRIVING-015'> reqEgoMotionHistoryOfCommandedVehicle : FunctionalRequirementCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    require constraint statement { language "English" /* The driving system shall give the checkpoint, for each step, the last 64 motion samples of the vehicle it commands, 100 ms apart and ending at the step, each holding speed in m/s, longitudinal acceleration in m/s², yaw rate in rad/s and curvature in 1/m. */ }
    attribute :>> source = "NEED-DRIVING-001; gap gapModelInputAndFeedback (ego-motion history, time alignment); assumption asmSourceAuthenticity";
    attribute :>> rationale = "This closes the loop: the motion the commands produce is what the next plan is made from. The source at cb50764b takes 64 history steps (Model/data_parsing/kit_scenes/temporal_contract.py) of speed, acceleration, yaw rate and curvature at 10 Hz in SI units, curvature being yaw rate over speed with speed floored at 0.1 m/s (egomotion.py in Model/data_parsing/kit_scenes). The model scales speed and acceleration itself and takes yaw rate and curvature as given, so a unit error there passes unseen.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when the inputs recorded for every plan of a run of SC-DRIVING-001 hold 64 samples 100 ms apart by their sample times, the newest at the step, each within 0.05 m/s, 0.1 m/s², 0.01 rad/s and 0.001 1/m of the speed, acceleration, yaw rate and curvature that the simulator reports for the commanded vehicle at that time.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-DRIVING-016'> reqNoMotionBeforeHistoriesComplete : FunctionalRequirementCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    require constraint statement { language "English" /* The driving system shall command no motion until its camera and ego-motion histories are complete with images and samples captured in the run, none of them filled in by a copy or an estimate. */ }
    attribute :>> source = "NEED-DRIVING-001; gap gapModelInputAndFeedback (history priming); assumption asmSourceAuthenticity";
    attribute :>> rationale = "The checkpoint plans only from complete histories. In the source at cb50764b the camera cache of BEVFormer V2 T8 requires source timestamps exactly 500 ms apart and forbids synthesizing continuity across dropped frames (Model/model_components/reactive_e2e.py), and repeated camera histories are no substitute for the source (asmSourceAuthenticity). The ego-motion history spans 6.3 s, so priming takes at least that long from the start of a run.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when, in a run of SC-DRIVING-001 that starts with the vehicle at rest, the commands hold it at standstill until the run has recorded eight images of each camera 0.5 s apart and 64 motion samples, and every image and sample given to the checkpoint has its own capture record of the run, a sensor frame number and a capture time, with no capture record given twice in one history.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-DRIVING-017'> reqCommandsOnlyFromNewestPlan : FunctionalRequirementCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    require constraint statement { language "English" /* The driving system shall compute each steering and acceleration command only from its newest valid plan and the current motion of the vehicle. */ }
    attribute :>> source = "NEED-DRIVING-001; checkpointCommandAuthorityConcern, checked by SC-DRIVING-005; scope item learnedDrivingInScope";
    attribute :>> rationale = "A plan is acceleration and curvature, not steering and pedal input, and the source at the checkpoint pin has no conversion to vehicle commands and no vehicle model (gapModelInputAndFeedback), so the driving system computes the commands. Computing them only from the plan and the motion of the vehicle keeps the checkpoint the one source of what the vehicle does. The no-autopilot, replay or overlay condition of SC-DRIVING-005 is a criterion of this requirement.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when, in a run of SC-DRIVING-001, every command that reaches the actuation of the vehicle names the plan it was computed from and that plan names its inference; when the autopilot and the traffic manager of the simulator have no control of the vehicle at any time of the run and no recorded, replayed or scripted control reaches its actuation; and when a test plan of opposite curvature sign, put in place of one checkpoint plan, reverses the sign of the steering command within 100 ms of simulation time.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-DRIVING-018'> reqPlanWithinPlanningPeriod : RequirementCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    require constraint statement { language "English" /* The driving system shall produce each plan within 100 ms of wall-clock time after the newest camera image of its step is available to it. */ }
    attribute :>> source = "NEED-DRIVING-001; gap gapClosedLoopPerformance (measurement window, drop tolerance)";
    attribute :>> rationale = "With the scene at wall-clock pace, one plan is due every 100 ms of wall-clock time, and a plan that takes longer leaves the vehicle on an older plan. The source at the checkpoint pin states no latency budget, and the rows of Model/speed_benchmark/BENCHMARKS.md measure a legacy configuration of 256 by 256 pixels, not the input form of REQ-DRIVING-013, so this limit is set by the planning period and checked early by the readiness probe. A checkpoint that cannot meet it is the hold or redirect condition of gapClosedLoopPerformance.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when, over a 60 s wall-clock window that starts at the end of priming, in a run of SC-DRIVING-001 with the simulation at a real-time factor of at least 0.95, at least 99 % of the plans are produced within 100 ms of wall-clock time after their newest camera image is available, and no two consecutive plans miss it.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-DRIVING-019'> reqPlansAndCommandsOverSCORE : FunctionalRequirementCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    require constraint statement { language "English" /* The driving system shall carry its plans and the commands computed from them from planning to the actuation of the vehicle only over Eclipse S-CORE communication. */ }
    attribute :>> source = "NEED-DRIVING-002; scenario SC-DRIVING-001; gap gapTransportAndControl; assumption asmCandidateReuse";
    attribute :>> rationale = "The increment evaluates S-CORE on a functional path. A path around it, such as a direct connection from the planner to the simulator, would let the loop drive while S-CORE carries nothing. Stopping the S-CORE communication of the driving system in a run shows that no such path exists: no plan-derived command reaches the actuation after it, and the stop response of REQ-DRIVING-026 takes over.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when, in a run of SC-DRIVING-001, every command that reaches the actuation of the vehicle is matched in the Eclipse S-CORE communication records to the plan it was computed from, and when, after the Eclipse S-CORE communication of the driving system is stopped in the run, no further command computed from a plan reaches the actuation.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-DRIVING-020'> reqPublishPlanStateAndHealth : FunctionalRequirementCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    require constraint statement { language "English" /* The driving system shall publish for observation each plan, the motion sample and the command of its step, and its health, each with its producer and its production time, within 100 ms of wall-clock time after producing them. */ }
    attribute :>> source = "NEED-DRIVING-003; scenario SC-DRIVING-002; gap gapTransportAndControl (genuine plan, state and health)";
    attribute :>> rationale = "What reaches AAOS SDV is the live output of this run only if each item is published as it is produced and says who produced it and when; with the time, a receiver can tell how old what it shows is. 100 ms is one planning period, so a published plan is at most one plan behind.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when, over a 60 s window of a run of SC-DRIVING-001, every plan, motion sample and command in the records of the run is published once, equal to its record, with its producer and its production time, within 100 ms of wall-clock time after that production time.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-DRIVING-021'> reqPublishHealthPeriodically : FunctionalRequirementCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    require constraint statement { language "English" /* The driving system shall publish its health, its mode of priming, driving or stopped, the cause of a stop and the age of its newest valid plan, at least every 200 ms of wall-clock time, also while it produces no plan. */ }
    attribute :>> source = "NEED-DRIVING-003; scenario SC-DRIVING-004 (no stale state shown as live)";
    attribute :>> rationale = "A receiver can tell a state that stopped arriving from a current one only if something arrives while nothing changes. With health at least every 200 ms, a receiver that has no health newer than 500 ms marks what it shows as stale. That marking is done by the observer application, a context role, so this requirement states what the driving system gives it, and the planned review SC-DRIVING-007 checks the marking.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when, over a 60 s window of a run of SC-DRIVING-001 that includes priming, driving and a stop, no two consecutive health publications are more than 200 ms of wall-clock time apart, and each holds the mode, the cause of the stop while stopped, and the age of the newest valid plan.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-DRIVING-022'> reqLoopIndependentOfObservation : RequirementCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    require constraint statement { language "English" /* The driving system shall produce the same plans and commands at the same times whether AAOS SDV receives its publications on time, late or not at all. */ }
    attribute :>> source = "NEED-DRIVING-004; scenario SC-DRIVING-004; gap gapTransportAndControl (the display is not in the fast control loop)";
    attribute :>> rationale = "Publication must not wait for a receiver or depend on what it does. The criteria compare runs on the same recorded inputs, because two closed-loop runs drive differently anyway, and they measure sameness by how far two runs with AAOS SDV receiving normally differ, because inference on a GPU is not bit-exact.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when, with the same recorded camera images, motion samples and route given to the driving system, the plans and commands of runs in which AAOS SDV receives normally, receives every publication 1 s late, and is stopped differ from those of a reference run with AAOS SDV receiving normally by no more than a second such reference run differs from the first, and the 99th percentile of the planning time of REQ-DRIVING-018 differs by no more than 10 ms between them.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-DRIVING-023'> reqDefinedStopResponse : FunctionalRequirementCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    require constraint statement { language "English" /* The stop response of the driving system shall decelerate the vehicle at 4 m/s² to standstill, with the steering held at its last valid command, and then hold it at standstill for the rest of the run without acting on any later plan. */ }
    attribute :>> source = "NEED-DRIVING-005; scenario SC-DRIVING-003; gap gapTransportAndControl (defined stop or disable response)";
    attribute :>> rationale = "One defined response serves every degraded condition, so the review checks a single behavior. 4 m/s² stays inside the longitudinal comfort bound of -4.05 m/s² that the evaluation of the checkpoint uses (the paper in Academic_Paper of the source at cb50764b), so the stop is firm without counting as a comfort violation. The vehicle stays stopped for the rest of the run, because resuming would need a validity rule of its own that this increment does not need. The response is shown in simulation and carries no safety claim.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when, in runs of SC-DRIVING-003 entered at 10 m/s and at 20 m/s, the commanded deceleration from the start of the response is 4 m/s² within 0.2 m/s² until standstill, the steering command stays at its last valid value, and the vehicle stays at standstill to the end of the run with no command computed from a later plan.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-DRIVING-024'> reqStopOnDegradedInput : FunctionalRequirementCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    require constraint statement { language "English" /* When the images of any camera for a step are missing, invalid or captured more than 200 ms before it, the newest motion sample is invalid or more than 200 ms old, or the route is more than 1 s old or holds no route corridor, all counted in simulation time, the driving system shall begin the stop response within 100 ms of simulation time. */ }
    attribute :>> source = "NEED-DRIVING-005; scenario SC-DRIVING-003; gap gapClosedLoopPerformance (freshness limits)";
    attribute :>> rationale = "Each freshness limit is two periods of its input in simulation time: camera images and motion samples come every 100 ms, the route raster every 500 ms (RASTER_HZ of 2 in Model/navigation/geometry.py at cb50764b). One late input is tolerated; a second means it has stopped. An image is invalid when its size is wrong or it cannot be decoded, a motion sample when a value is not finite, a route when its corridor channel is empty. The limits are counted in simulation time, the time in which the vehicle moves on an old input.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when, in runs of SC-DRIVING-003 that withhold the images of one camera, freeze the motion samples, stop the route, and deliver a corrupt image, a motion sample with a value that is not finite, and a route with an empty corridor, the stop response begins within 100 ms of simulation time after the limit of that condition is passed, and when it does not begin in a run of SC-DRIVING-001 without these conditions.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-DRIVING-025'> reqStopOnInvalidOrStalePlan : FunctionalRequirementCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    require constraint statement { language "English" /* When the newest valid plan is more than 300 ms old at a command, counted from the capture time of its newest camera image, or a plan arrives that does not hold 64 finite pairs of acceleration and curvature, the driving system shall begin the stop response within 100 ms of simulation time. */ }
    attribute :>> source = "NEED-DRIVING-005; scenario SC-DRIVING-003; gap gapClosedLoopPerformance (control deadlines)";
    attribute :>> rationale = "The control head of the checkpoint is a plain linear layer with no bound on its output (gru_planner.py in Model/model_components/trajectory_planning at cb50764b), so without a vehicle model only a plan of the wrong size or with a value that is not finite can be rejected. 300 ms is three planning periods: one late plan within the drop tolerance of REQ-DRIVING-018 passes, a plan that stays away does not. A late plan and a lost plan both show as a plan that has grown too old.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when, in runs of SC-DRIVING-003 that stall planning, drop plans, and inject a plan with a value that is not finite and a plan of 63 pairs, the stop response begins within 100 ms of simulation time after the age of the newest valid plan passes 300 ms or after the invalid plan arrives, and no command is computed from the invalid plan.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-DRIVING-026'> reqStopOnLostCommands : FunctionalRequirementCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    require constraint statement { language "English" /* When no valid command has reached the actuation of the vehicle for 200 ms of simulation time, the driving system shall apply the stop response at the actuation. */ }
    attribute :>> source = "NEED-DRIVING-005; scenario SC-DRIVING-003; gap gapTransportAndControl (lost plans)";
    attribute :>> rationale = "A simulator keeps applying the last control it was given, so a command path that stops would leave the vehicle acting on the last plan. With a command every 100 ms, two missed commands mean the path has stopped, and the actuation end applies the response itself because it can no longer be told to.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when, in a run of SC-DRIVING-001 in which the Eclipse S-CORE communication of the driving system is stopped, the commands at the actuation follow the stop response from no later than 300 ms of simulation time after the last command arrived.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-DRIVING-027'> reqPublishStop : FunctionalRequirementCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    require constraint statement { language "English" /* The driving system shall publish that it is stopped and why within 100 ms of wall-clock time after the stop response begins, and in its health until the run ends. */ }
    attribute :>> source = "NEED-DRIVING-005; scenario SC-DRIVING-003";
    attribute :>> rationale = "The need asks that the degradation be published, so that what the occupants see on AAOS SDV says that the vehicle is stopping and why instead of showing a vehicle that drives. The 100 ms is one planning period, as for every other publication of REQ-DRIVING-020.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when, in each run of the criteria of REQ-DRIVING-024 to REQ-DRIVING-026, the health shows the mode stopped and the cause of that run within 100 ms of wall-clock time after the stop response begins, and in every later health publication of the run.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-DRIVING-028'> reqTimesInTheirOwnDomain : FunctionalRequirementCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    require constraint statement { language "English" /* The driving system shall carry with each camera image its capture time, with each motion sample its sample time, with each plan the capture time of its newest image and its production time, and with each command the plan it was computed from and its issue and actuation times, each time marked with its domain: simulation time for capture, sample and actuation times, and the monotonic clock of the host for production and issue times. */ }
    attribute :>> source = "NEED-DRIVING-006; scenario SC-DRIVING-001; gap gapClosedLoopPerformance (separate time domains)";
    attribute :>> rationale = "The input age at actuation and the planning interval belong to the world of the vehicle and are measured in simulation time; the planning time and the transport delay belong to the host and are measured on its monotonic clock. With each time marked by its domain, no rate or age is read in a domain it was not measured in. The 0.1 s spacing of the samples in a plan is a property of the plan, not of how often plans are made.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when, from the records of a run of SC-DRIVING-001 alone, for every command the input age at actuation and the planning interval are computed in simulation time and the planning time and the Eclipse S-CORE transport delay on the monotonic clock of the host, every time used carries its domain, and no computation combines times of two domains.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-DRIVING-029'> reqRecordCheckpointSourceAndConfiguration : FunctionalRequirementCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    require constraint statement { language "English" /* The driving system shall record, before the first plan of each run, the SHA-256 of the checkpoint file it loaded, the AutoE2E source revision it runs and the SHA-256 of its complete configuration, and name that record in every plan of the run. */ }
    attribute :>> source = "NEED-DRIVING-007; scenario SC-DRIVING-001; out-of-scope item modelTrainingOutOfScope; gap gapAdoptionAndRights";
    attribute :>> rationale = "Another engineer can rerun a run only from what it names. The source at cb50764b already identifies a checkpoint by the SHA-256 of its file (Platform/pipelines/inference.py). Source, checkpoint and configuration are pinned separately because a checkpoint does not fix the code that feeds it. The scenario and the bench belong to System 2 and are pinned there.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when every run of SC-DRIVING-001 has the record before its first plan, every plan names it, and another engineer who hashes the named checkpoint file and configuration and checks out the named source revision obtains the recorded values.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-DRIVING-030'> reqRefuseUnpinnedCheckpoint : FunctionalRequirementCandidate {
    subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;
    require constraint statement { language "English" /* The driving system shall produce no plan from a checkpoint whose SHA-256 differs from the one its configuration names, or when its configuration names none. */ }
    attribute :>> source = "NEED-DRIVING-007; out-of-scope item modelTrainingOutOfScope (no undisclosed checkpoint swap); assumption asmSourceAuthenticity";
    attribute :>> rationale = "A swapped or untrained checkpoint would still drive, and the run would still name its configuration; refusing to plan makes a swap visible instead of undisclosed. Random weights are no substitute for the source (asmSourceAuthenticity); the AlpaSim driver plugin of the source at cb50764b has an untrained mode (UNTRAINED_CHECKPOINT), which names no checkpoint and is refused as well.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when, given a checkpoint file that differs from the named one in a single byte, and given a configuration that names no checkpoint SHA-256, the driving system produces no plan, the vehicle stays at standstill, and the health names the mismatch.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  connection planEachStepByCheckpointInferenceDerivation : DerivesFromNeed
    connect needDrivenAlongTheRoute to reqPlanEachStepByCheckpointInference;
  connection cameraImagesInCheckpointFormDerivation : DerivesFromNeed
    connect needDrivenAlongTheRoute to reqCameraImagesInCheckpointForm;
  connection routeAsNavigationRastersDerivation : DerivesFromNeed
    connect needDrivenAlongTheRoute to reqRouteAsNavigationRasters;
  connection egoMotionHistoryOfCommandedVehicleDerivation : DerivesFromNeed
    connect needDrivenAlongTheRoute to reqEgoMotionHistoryOfCommandedVehicle;
  connection noMotionBeforeHistoriesCompleteDerivation : DerivesFromNeed
    connect needDrivenAlongTheRoute to reqNoMotionBeforeHistoriesComplete;
  connection commandsOnlyFromNewestPlanDerivation : DerivesFromNeed
    connect needDrivenAlongTheRoute to reqCommandsOnlyFromNewestPlan;
  connection planWithinPlanningPeriodDerivation : DerivesFromNeed
    connect needDrivenAlongTheRoute to reqPlanWithinPlanningPeriod;
  connection plansAndCommandsOverSCOREDerivation : DerivesFromNeed
    connect needPlansAndCommandsThroughSCORE to reqPlansAndCommandsOverSCORE;
  connection publishPlanStateAndHealthDerivation : DerivesFromNeed
    connect needLiveStateForAAOS to reqPublishPlanStateAndHealth;
  connection publishHealthPeriodicallyDerivation : DerivesFromNeed
    connect needLiveStateForAAOS to reqPublishHealthPeriodically;
  connection loopIndependentOfObservationDerivation : DerivesFromNeed
    connect needLoopIndependentOfAAOS to reqLoopIndependentOfObservation;
  connection definedStopResponseDerivation : DerivesFromNeed
    connect needDefinedResponseToDegradedInputOrPlan to reqDefinedStopResponse;
  connection stopOnDegradedInputDerivation : DerivesFromNeed
    connect needDefinedResponseToDegradedInputOrPlan to reqStopOnDegradedInput;
  connection stopOnInvalidOrStalePlanDerivation : DerivesFromNeed
    connect needDefinedResponseToDegradedInputOrPlan to reqStopOnInvalidOrStalePlan;
  connection stopOnLostCommandsDerivation : DerivesFromNeed
    connect needDefinedResponseToDegradedInputOrPlan to reqStopOnLostCommands;
  connection publishStopDerivation : DerivesFromNeed
    connect needDefinedResponseToDegradedInputOrPlan to reqPublishStop;
  connection timesInTheirOwnDomainDerivation : DerivesFromNeed
    connect needTimesMeasurableInTheirOwnDomain to reqTimesInTheirOwnDomain;
  connection recordCheckpointSourceAndConfigurationDerivation : DerivesFromNeed
    connect needRunsIdentifyCheckpointAndConfiguration to reqRecordCheckpointSourceAndConfiguration;
  connection refuseUnpinnedCheckpointDerivation : DerivesFromNeed
    connect needRunsIdentifyCheckpointAndConfiguration to reqRefuseUnpinnedCheckpoint;

  comment performanceLimitsFixedInPhase5 about DE4SDV_ClosedLoopDrivingFraming::gapClosedLoopPerformance
    /*
     * What phase 5 fixes of this gap for the driving system: the scenario of
     * the measurements, SC-DRIVING-001; the input resolution, REQ-DRIVING-013;
     * the measurement window and the drop tolerance, REQ-DRIVING-018; and the
     * control deadlines and freshness limits, REQ-DRIVING-024 to
     * REQ-DRIVING-026. Open, with the System 2 bench: the rendered frame rate,
     * the capture rate and the render resolution of the simulator, and the
     * CARLA map and route of SC-DRIVING-001, chosen before the readiness
     * probe.
     */

  /* ─────────────────────────────── Views ─────────────────────────────── */

  concern closedLoopDrivingNeedsConcern : StakeholderNeedsConcern {
    doc /*
     * Systems engineers and open-source reviewers need the stakeholder needs
     * of the driving system with their statements and sources, and the
     * planned stakeholder review of each, to judge whether the needs cover
     * the concerns of phase 1.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view closedLoopDrivingNeedsView : TVD::TableView {
    viewpoint selectedNeedsViewpoint : StakeholderRequirementDefinitionViewpoint {
      frame closedLoopDrivingNeedsConcern;
    }

    expose needDrivenAlongTheRoute;
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
    }
  }

  view closedLoopDrivingNeedValidationView : TVD::TableView {
    viewpoint selectedNeedValidationViewpoint : StakeholderRequirementDefinitionViewpoint {
      frame closedLoopDrivingNeedsConcern;
    }

    expose checkpointAuthorityValidationPlan;
    expose scoreCommandPathValidationPlan;
    expose liveStateValidationPlan;
    expose aaosIndependenceValidationPlan;
    expose degradedResponseValidationPlan;
    expose timeDomainValidationPlan;
    expose rerunValidationPlan;
    filter @ SysML::PartUsage;
    attribute :>> includeReferenceElements = true;
    attribute :>> maxRowHeight = 300;
    view Plan :> columnViews {
      attribute :>> featureToRender = CT::declaredName;
    }
    view Review :> columnViews {
      attribute :>> featureToRender = CT::documentation;
    }
  }

  concern closedLoopDrivingRequirementTraceConcern : RequirementTraceConcern {
    doc /*
     * Verification engineers and open-source reviewers need each requirement
     * of the driving system traced to the need it derives from, with its
     * verification method and success criteria, to judge whether the
     * requirements answer the needs and can be verified.
     */
    subject;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view closedLoopDrivingRequirementsView : TVD::TableView {
    viewpoint selectedRequirementTraceViewpoint : SystemRequirementTraceabilityViewpoint {
      frame closedLoopDrivingRequirementTraceConcern;
    }

    expose reqPlanEachStepByCheckpointInference;
    expose reqCameraImagesInCheckpointForm;
    expose reqRouteAsNavigationRasters;
    expose reqEgoMotionHistoryOfCommandedVehicle;
    expose reqNoMotionBeforeHistoriesComplete;
    expose reqCommandsOnlyFromNewestPlan;
    expose reqPlanWithinPlanningPeriod;
    expose reqPlansAndCommandsOverSCORE;
    expose reqPublishPlanStateAndHealth;
    expose reqPublishHealthPeriodically;
    expose reqLoopIndependentOfObservation;
    expose reqDefinedStopResponse;
    expose reqStopOnDegradedInput;
    expose reqStopOnInvalidOrStalePlan;
    expose reqStopOnLostCommands;
    expose reqPublishStop;
    expose reqTimesInTheirOwnDomain;
    expose reqRecordCheckpointSourceAndConfiguration;
    expose reqRefuseUnpinnedCheckpoint;
    filter @ SysML::RequirementUsage;
    attribute :>> includeReferenceElements = true;
    attribute :>> maxRowHeight = 300;
    view ID :> columnViews {
      attribute :>> featureToRender = CT::reqId;
    }
    view Requirement :> columnViews {
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
    }
  }

  view closedLoopDrivingRequirementVerificationView : TVD::TableView {
    viewpoint selectedRequirementVerificationViewpoint : SystemRequirementTraceabilityViewpoint {
      frame closedLoopDrivingRequirementTraceConcern;
    }

    expose reqPlanEachStepByCheckpointInference;
    expose reqCameraImagesInCheckpointForm;
    expose reqRouteAsNavigationRasters;
    expose reqEgoMotionHistoryOfCommandedVehicle;
    expose reqNoMotionBeforeHistoriesComplete;
    expose reqCommandsOnlyFromNewestPlan;
    expose reqPlanWithinPlanningPeriod;
    expose reqPlansAndCommandsOverSCORE;
    expose reqPublishPlanStateAndHealth;
    expose reqPublishHealthPeriodically;
    expose reqLoopIndependentOfObservation;
    expose reqDefinedStopResponse;
    expose reqStopOnDegradedInput;
    expose reqStopOnInvalidOrStalePlan;
    expose reqStopOnLostCommands;
    expose reqPublishStop;
    expose reqTimesInTheirOwnDomain;
    expose reqRecordCheckpointSourceAndConfiguration;
    expose reqRefuseUnpinnedCheckpoint;
    filter @ SysML::RequirementUsage;
    attribute :>> includeReferenceElements = true;
    attribute :>> maxRowHeight = 300;
    view ID :> columnViews {
      attribute :>> featureToRender = CT::reqId;
    }
    view Requirement :> columnViews {
      attribute :>> featureToRender = CT::declaredName;
    }
    view Method :> columnViews {
      attribute :>> featureToRender = CT::attributeValue {
        attribute attributeName = "verificationMethod";
      }
    }
    view Criteria :> columnViews {
      attribute :>> featureToRender = CT::attributeValue {
        attribute attributeName = "successCriteria";
      }
      attribute :>> columnWidth = 360;
    }
  }
}
