/*
 * DE4SDV driver-assistance stakeholder needs and requirements.
 *
 * INC-DRIVING-002, phase 4: the stakeholder needs of the candidate
 * driver-assistance system, the system of interest the charter declares. Each
 * need is held by the parties it serves and leads its source with the phase 1
 * concern it derives from. Each has one planned stakeholder review on the
 * scenarios of phase 2 it covers, carried out by the roles that check the
 * answer. Three concerns are reviewer questions: a need's source names them
 * and its review checks them.
 *
 * Phase 5: the requirements derived from these needs, each with one subject,
 * the candidate driver-assistance system, one verification method and its
 * success criteria. The criteria for a vehicle target are derived from the
 * source regulation SRC-UNECE-R152 and from the product line's requirements
 * REQ-AEBS-002, REQ-AEBS-003, REQ-AEBS-008 and REQ-AEBS-012; the rationale of
 * each names whose obligation it is and what a simulation cannot show of it.
 * The other limits are set here and justified in their rationales. The
 * rationales name the files of VisionPilot at 014e0e7a by their file names;
 * upstream.md gives each with its path. The requirements are not core: the
 * driver-assistance system enters a member product only with the driving
 * stack that phase 3 records as the feature candidate
 * visionPilotDrivingStack, and phase 9 adds that feature to the feature model
 * and links the system of interest to it.
 *
 * No safety, on-road or production-readiness claim is made, and no member
 * product is claimed.
 */

package DE4SDV_DriverAssistanceNeedsRequirements {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_TraceVocabulary::*;
  private import DE4SDV_Stakeholders::*;
  private import SAF_Viewpoints::*;
  private import SysideViews::**;
  private import Views::*;

  /* ───────────────────── Phase 4: stakeholder needs ───────────────────── */

  requirement <'NEED-DRIVING-008'> needWarnAndBrakeForVehicleAhead : StakeholderNeedCandidate {
    subject driverAssistanceSystem :> DE4SDV_DriverAssistanceFraming::candidateDriverAssistanceSystem;
    stakeholder occupant : VehicleOccupant;
    stakeholder roadUser : RoadUser;
    require constraint statement { language "English" /* Vehicle occupants and road users need the driver-assistance system to request the collision warning and to command the braking of the vehicle when a collision with a stationary or a slower moving vehicle ahead in its lane is imminent. */ }
    attribute :>> source = "INC-DRIVING-002 vehicleTargetResponseConcern, emergencyBrakingIndependenceConcern, scoreCommandAndWarningPathConcern, vehicleTargetCriteriaConcern, scope items vehicleTargetResponseInScope, scoreCommandPathInScope and vehicleTargetCriteriaInScope, gaps gapNoSeparateEmergencyFunction, gapScoreIntegration, gapVehicleTargetCriteria and gapCameraImageAndGeometry, assumption asmBenchReuse, scenarios SC-DRIVING-012 and SC-DRIVING-013";
    attribute :>> rationale = "The warning lets the driver act, and the braking is meant to avoid or lessen the collision when the driver does not act in time. The need states what they expect, not how well the candidate meets it, and carries no safety claim. Phase 5 derives the criteria for a vehicle target and their limits (gapVehicleTargetCriteria). Phase 5 also derives from this need the requirements on the Eclipse S-CORE path of the warning request and the braking command, and on the independence of that command: its source names their concerns, and SC-DRIVING-016 asks their questions.";
  }

  requirement <'NEED-DRIVING-009'> needNoReactionWithoutImminentCollision : StakeholderNeedCandidate {
    subject driverAssistanceSystem :> DE4SDV_DriverAssistanceFraming::candidateDriverAssistanceSystem;
    stakeholder occupant : VehicleOccupant;
    stakeholder roadUser : RoadUser;
    require constraint statement { language "English" /* Vehicle occupants and road users need the driver-assistance system to request no collision warning and to command no emergency braking when no collision with a vehicle ahead is imminent, as when a stationary vehicle stands beyond a curve or a vehicle ahead turns off. */ }
    attribute :>> source = "INC-DRIVING-002 vehicleTargetResponseConcern, vehicleTargetCriteriaConcern, scope item noReactionInScope, gap gapVehicleTargetCriteria, scenarios SC-DRIVING-014 and SC-DRIVING-015";
    attribute :>> rationale = "An emergency braking with no collision imminent puts the traffic behind the vehicle at risk, and a needless warning teaches the driver to ignore the next one. Phase 5 confirms the two scenarios and states their criterion (gapVehicleTargetCriteria).";
  }

  requirement <'NEED-DRIVING-010'> needWarningRequestForTheDriver : StakeholderNeedCandidate {
    subject driverAssistanceSystem :> DE4SDV_DriverAssistanceFraming::candidateDriverAssistanceSystem;
    stakeholder occupant : VehicleOccupant;
    require constraint statement { language "English" /* Vehicle occupants need the driver-assistance system to give a warning request at its boundary when a collision with a vehicle ahead in its lane is imminent, so that the AAOS SDV warns the driver on its display and as a sound. */ }
    attribute :>> source = "INC-DRIVING-002 driverWarningSequenceConcern, scope item driverWarningInScope, gap gapWarningOutput, scenarios SC-DRIVING-012 and SC-DRIVING-013";
    attribute :>> rationale = "The driver can act on a warning only if it reaches the display and the sound of the AAOS SDV. NEED-DRIVING-008 needs the candidate to request the warning; this need adds that the request leaves the candidate at its boundary, where the AAOS SDV takes it. At the inspected revision the application has no warning output at its boundary; its warnings go to its own visualization and data log (gapWarningOutput). Phase 5 states when each mode is due relative to the warning request and to the start of the emergency braking. Whether a driver perceives the warning is out of scope.";
  }

  requirement <'NEED-DRIVING-011'> needRunsIdentifyTheCandidate : StakeholderNeedCandidate {
    subject driverAssistanceSystem :> DE4SDV_DriverAssistanceFraming::candidateDriverAssistanceSystem;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder productLineEngineer : ProductLineEngineer;
    require constraint statement { language "English" /* Verification engineers and product-line engineers need each run of the driver-assistance system to identify the candidate revision and the configuration it ran with, so that each verdict is bound to what ran. */ }
    attribute :>> source = "INC-DRIVING-002 candidateVerdictConcern, scope item verdictEvidenceInScope, gap gapCandidateBehaviorUnverified, scenarios SC-DRIVING-012 to SC-DRIVING-015";
    attribute :>> rationale = "The lifecycle decision rests on a verdict for each requirement and scenario, and a verdict holds only for the candidate that ran. A build with a change that upstream has not merged is a different candidate. The candidate's configuration includes its run-time settings, such as its source mode. The scenario and the simulated configuration belong to System 2 and are pinned there, so this need covers only what the candidate itself runs.";
  }

  /* ───────────────── Phase 4: planned stakeholder reviews ───────────────── */

  part <'SC-DRIVING-016'> vehicleAheadResponseValidationPlan : ValidationPlanningScenario {
    doc /* For NEED-DRIVING-008, a planned stakeholder review. While the
         * stationary and the slower moving vehicle target scenarios run
         * (SC-DRIVING-012 and SC-DRIVING-013), can verification engineers and
         * compliance engineers confirm, by the criteria for a vehicle target
         * that phase 5 derives, that the candidate requests the warning and
         * that its driving command brakes the vehicle, and that no autopilot,
         * replay or overlay acts instead of the candidate? Can they trace each
         * of those criteria to the provision of UNECE R152 it is derived from,
         * to the product-line requirement it judges and whose obligation it
         * is, and name what the runs cannot show of it? Can systems engineers
         * and product-line engineers confirm that every driving command passed
         * through Eclipse S-CORE to the actuation and every warning request
         * through S-CORE to the AAOS SDV, and that no other exchange carried
         * them? And can safety experts and product-line engineers tell which
         * element of the candidate gave the braking command, whether it left
         * the candidate in the driving command or apart from it, and whether
         * that command keeps the independence of the protected emergency
         * command path? */
  }
  connection vehicleAheadResponseValidationPlanning : ValidationPlanningAssociation
    connect needWarnAndBrakeForVehicleAhead to vehicleAheadResponseValidationPlan;
  dependency vehicleAheadResponseValidationFromStationaryTargetScenario
    from vehicleAheadResponseValidationPlan
    to DE4SDV_DriverAssistanceOperationalContext::warnAndBrakeForStationaryVehicle;
  dependency vehicleAheadResponseValidationFromSlowerTargetScenario
    from vehicleAheadResponseValidationPlan
    to DE4SDV_DriverAssistanceOperationalContext::warnAndBrakeForSlowerVehicle;

  part <'SC-DRIVING-017'> noReactionValidationPlan : ValidationPlanningScenario {
    doc /* For NEED-DRIVING-009, a planned stakeholder review. While the
         * vehicle drives through the curve past the stationary vehicle beyond
         * the guard pipes (SC-DRIVING-014), and while it follows the vehicle
         * ahead that turns off (SC-DRIVING-015), can verification engineers
         * and compliance engineers confirm, by the criterion that phase 5
         * states for each scenario, that the candidate requests no warning and
         * commands no emergency braking, and that the candidate's own driving
         * command moved the vehicle throughout each run? */
  }
  connection noReactionValidationPlanning : ValidationPlanningAssociation
    connect needNoReactionWithoutImminentCollision to noReactionValidationPlan;
  dependency noReactionValidationFromCurveScenario
    from noReactionValidationPlan
    to DE4SDV_DriverAssistanceOperationalContext::noReactionToStationaryVehicleBeyondTheCurve;
  dependency noReactionValidationFromTurningOffScenario
    from noReactionValidationPlan
    to DE4SDV_DriverAssistanceOperationalContext::noReactionToVehicleAheadTurningOff;

  part <'SC-DRIVING-018'> driverWarningValidationPlan : ValidationPlanningScenario {
    doc /* For NEED-DRIVING-010, a planned stakeholder review. While the
         * stationary and the slower moving vehicle target scenarios run
         * (SC-DRIVING-012 and SC-DRIVING-013), can safety experts and
         * verification engineers confirm that the AAOS SDV gave each warning
         * that the candidate requested on its display and as a sound, and when
         * each mode began relative to the warning request and to the start of
         * the emergency braking, with no recording or overlay in place of
         * either mode? */
  }
  connection driverWarningValidationPlanning : ValidationPlanningAssociation
    connect needWarningRequestForTheDriver to driverWarningValidationPlan;
  dependency driverWarningValidationFromStationaryTargetScenario
    from driverWarningValidationPlan
    to DE4SDV_DriverAssistanceOperationalContext::warnAndBrakeForStationaryVehicle;
  dependency driverWarningValidationFromSlowerTargetScenario
    from driverWarningValidationPlan
    to DE4SDV_DriverAssistanceOperationalContext::warnAndBrakeForSlowerVehicle;

  part <'SC-DRIVING-019'> candidateIdentityValidationPlan : ValidationPlanningScenario {
    doc /* For NEED-DRIVING-011, a planned stakeholder review. After each run
         * of the four scenarios (SC-DRIVING-012, SC-DRIVING-013,
         * SC-DRIVING-014 and SC-DRIVING-015), can verification engineers and
         * product-line engineers bind its verdict to the candidate revision
         * and the configuration that the run identifies, and confirm that a
         * build with a change that upstream has not merged identifies itself
         * as a different candidate? */
  }
  connection candidateIdentityValidationPlanning : ValidationPlanningAssociation
    connect needRunsIdentifyTheCandidate to candidateIdentityValidationPlan;
  dependency candidateIdentityValidationFromStationaryTargetScenario
    from candidateIdentityValidationPlan
    to DE4SDV_DriverAssistanceOperationalContext::warnAndBrakeForStationaryVehicle;
  dependency candidateIdentityValidationFromSlowerTargetScenario
    from candidateIdentityValidationPlan
    to DE4SDV_DriverAssistanceOperationalContext::warnAndBrakeForSlowerVehicle;
  dependency candidateIdentityValidationFromCurveScenario
    from candidateIdentityValidationPlan
    to DE4SDV_DriverAssistanceOperationalContext::noReactionToStationaryVehicleBeyondTheCurve;
  dependency candidateIdentityValidationFromTurningOffScenario
    from candidateIdentityValidationPlan
    to DE4SDV_DriverAssistanceOperationalContext::noReactionToVehicleAheadTurningOff;

  /* ───────────────────── Phase 5: requirements ───────────────────── */

  comment termsOfTheDriverAssistanceRequirements
    /*
     * Terms of the requirements of the driver-assistance system below.
     * - Vehicle: the vehicle that the driver-assistance system drives.
     * - Vehicle ahead: a vehicle ahead of the vehicle in its lane.
     * - Run: one execution of the driver-assistance system on one scenario,
     *   from its start to its end.
     * - Setting: a scenario with an approach speed and its tolerance. The
     *   settings are SC-DRIVING-012 at 20 km/h (20 to 22 km/h), at 42 km/h
     *   (40 to 42 km/h) and at 60 km/h (58 to 60 km/h); SC-DRIVING-013 at 30
     *   km/h (30 to 32 km/h) and at 60 km/h (58 to 60 km/h), behind a target
     *   at 20 km/h (18 to 20 km/h); SC-DRIVING-014 at 30 km/h (28 to 30
     *   km/h), toward a curve of at most 25 m radius; and SC-DRIVING-015 at
     *   40 km/h (38 to 40 km/h), behind the vehicle ahead at the same speed.
     *   Each setting is run twice, and both runs count.
     * - Functional part: the part of a run of SC-DRIVING-012 or
     *   SC-DRIVING-013 from the latest instant at which the vehicle travels
     *   at its approach speed within the tolerance with a time to collision
     *   of at least 4 s, until the vehicle hits the target or comes to the
     *   speed of the target.
     * - Judged run: a run of SC-DRIVING-012 or SC-DRIVING-013 in which the
     *   vehicle travels straight, with its centre line within 0.2 m of that
     *   of the target, for at least 2 s before its functional part. A run
     *   that misses this, or has no functional part, is reported with what it
     *   missed and is not judged.
     * - Time to collision: the distance from the vehicle to the vehicle ahead
     *   in the direction of travel, divided by the speed at which the vehicle
     *   closes on it.
     * - Imminent collision: the term of the source regulation, which gives it
     *   no value. The requirements take a collision as imminent in every
     *   judged run, as the tests of the source regulation do, and in no run
     *   of SC-DRIVING-014 or SC-DRIVING-015.
     * - Driving command: the steering and acceleration command that the
     *   driver-assistance system gives the actuation of the vehicle.
     * - Actuation: the interface at which the vehicle takes the driving
     *   commands.
     * - Warning request: the output by which the driver-assistance system
     *   asks the AAOS SDV to give the driver the collision warning.
     * - Emergency braking: a command of the driver-assistance system for a
     *   deceleration of at least 5.0 m/s², in its driving command or apart
     *   from it. It starts with the first such command after a command for
     *   less.
     * - Uncommanded emergency braking: an emergency braking at the actuation
     *   that is not the newest command of the driver-assistance system.
     * - Eclipse S-CORE path: the part of System 1 outside the
     *   driver-assistance system that carries its driving command to the
     *   actuation and its warning request to the AAOS SDV. A failure of the
     *   path is a loss, a delay, a repetition or a corruption of a message on
     *   it.
     * - Configuration: every setting that the driver-assistance system reads
     *   at its start, from its files and its launch.
     * - Relative approach speed: the speed at which the vehicle closes on the
     *   target at the start of the functional part.
     * - Relative impact speed: the speed at which the vehicle closes on the
     *   target when they touch; 0 km/h when they do not touch.
     * - Maximum relative impact speed: the limit of the source regulation for
     *   a car in running order, by relative approach speed: 0 km/h up to 42
     *   km/h, 15 km/h at 45 km/h, 25 km/h at 50 km/h, 30 km/h at 55 km/h and
     *   35 km/h at 60 km/h. Between two of these speeds, the limit of the
     *   higher one applies.
     * - Simulation time: the time of the simulated world. Wall-clock time:
     *   the time of the host.
     */

  requirement <'REQ-DRIVING-036'> reqEmergencyBrakingForImminentCollision : FunctionalRequirementCandidate {
    subject driverAssistanceSystem :> DE4SDV_DriverAssistanceFraming::candidateDriverAssistanceSystem;
    require constraint statement { language "English" /* When a collision with a vehicle ahead is imminent, the driver-assistance system shall command a deceleration of at least 5.0 m/s². */ }
    attribute :>> source = "NEED-DRIVING-008; SRC-UNECE-R152 emergency braking; REQ-AEBS-003; gap gapVehicleTargetCriteria; scenarios SC-DRIVING-012 and SC-DRIVING-013";
    attribute :>> rationale = "Derived from the emergency braking of the car to car scenario of the source regulation (SRC-UNECE-R152), which asks for a braking demand of at least 5.0 m/s² once the system has detected an imminent collision, and from REQ-AEBS-003. The requirement states the condition that the tests of the source regulation set up, an imminent collision, rather than the detection of it by the system. The obligation is the candidate's: the demand is in its command. At 014e0e7a the candidate writes its planned acceleration to the vehicle in every cycle that has an inference result, with no limit or latch (longitudinal_planning.cpp:36; vision_pilot.cpp:138, 157, 174), so it already decelerates while it flags a warning; its own emergency band starts below -5.0 m/s² (planning.cpp:118). A simulation cannot show the service brakes and the anti-lock function of a real vehicle, which turn the demand into a deceleration.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when the driver-assistance system commands a deceleration of at least 5.0 m/s² within the functional part of each judged run.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-DRIVING-037'> reqImpactSpeedWithinLimit : RequirementCandidate {
    subject driverAssistanceSystem :> DE4SDV_DriverAssistanceFraming::candidateDriverAssistanceSystem;
    require constraint statement { language "English" /* When a collision with a vehicle ahead is imminent, the driver-assistance system shall brake the vehicle to a relative impact speed of at most the maximum relative impact speed for the relative approach speed. */ }
    attribute :>> source = "NEED-DRIVING-008; SRC-UNECE-R152 speed reduction by braking demand; REQ-AEBS-003; gap gapVehicleTargetCriteria; scenarios SC-DRIVING-012 and SC-DRIVING-013";
    attribute :>> rationale = "Derived from the speed reduction by braking demand of the car to car scenario of the source regulation (SRC-UNECE-R152), with the test speeds of its warning and activation tests with a stationary and a moving vehicle target, and from REQ-AEBS-003. The limits and the test speeds are those of a car in running order, because the simulated vehicle carries no load. The source sets the limits for unobstructed targets on a flat and dry road, with the centre lines at most 0.2 m apart, in daylight and on a straight road; the settings and the judged runs keep those conditions. The obligation is the candidate's, with the simulated vehicle and its brakes standing in for a real one (asmSimulatedConfigurationStandsIn); the settings are System 2's. A simulation cannot show the target that the source prescribes, a series production car or a soft target, nor the measured road surface, the illumination and the test masses.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when the relative impact speed is 0 km/h in each judged run of SC-DRIVING-012 at 20 km/h and at 42 km/h and of SC-DRIVING-013 at 30 km/h and at 60 km/h, and at most 35 km/h in each judged run of SC-DRIVING-012 at 60 km/h.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-DRIVING-038'> reqDrivingCommandOverSCORE : RequirementCandidate {
    subject driverAssistanceSystem :> DE4SDV_DriverAssistanceFraming::candidateDriverAssistanceSystem;
    require constraint statement { language "English" /* The driver-assistance system shall give its driving command to the actuation of the vehicle only over the Eclipse S-CORE path. */ }
    attribute :>> source = "NEED-DRIVING-008; scope item scoreCommandPathInScope; gap gapScoreIntegration; scenarios SC-DRIVING-012 to SC-DRIVING-015";
    attribute :>> rationale = "This is a design constraint: the increment judges the candidate on the S-CORE path of the product line. A path around it, such as a direct connection from the candidate to the simulator, would let the vehicle brake while S-CORE carries nothing. At 014e0e7a only the ROS 2 build of the application reads a live speed and commands a vehicle (vision_pilot.cpp:59-78); its vehicle interface publishes steering and acceleration to topics (vehicle_ros2_interface.cpp:25-26), and the application has no binding to S-CORE (gapScoreIntegration). Phases 6 to 8 decide how the command enters the S-CORE path. The no-autopilot, replay or overlay condition of the planned reviews is a criterion of this requirement.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when, in every run of SC-DRIVING-012 to SC-DRIVING-015, every driving command that reaches the actuation is matched in the communication records of the Eclipse S-CORE path to a driving command of the driver-assistance system; when the autopilot and the traffic manager of the simulator have no control of the vehicle at any time of the run and no recorded, replayed, scripted or overlaid control reaches its actuation; and when, in one further run of SC-DRIVING-012 in which the Eclipse S-CORE path of the driver-assistance system is stopped, no driving command reaches the actuation after the stop.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-DRIVING-039'> reqIsolateEmergencyBrakingFromSCORE : RequirementCandidate {
    subject driverAssistanceSystem :> DE4SDV_DriverAssistanceFraming::candidateDriverAssistanceSystem;
    require constraint statement { language "English" /* The driver-assistance system shall prevent each failure of the Eclipse S-CORE path from causing an uncommanded emergency braking. */ }
    attribute :>> source = "NEED-DRIVING-008; REQ-MW-006; gap gapNoSeparateEmergencyFunction; emergencyBrakingIndependenceConcern";
    attribute :>> rationale = "The product line holds the independence of the protected emergency command path as common content, which REQ-MW-006 states: a failure of the middleware integration path may cause no uncontrolled emergency intervention command, whatever its realization. At 014e0e7a the candidate's braking leaves in its one driving command (vision_pilot.cpp:157, 174), which REQ-DRIVING-038 sends over the Eclipse S-CORE path (gapNoSeparateEmergencyFunction). A path apart from S-CORE for an emergency braking command would be the product line's protected path, not a bypass of the driving command, which REQ-DRIVING-038 still covers. The analysis rests on the realization that phase 8 records and makes no freedom-from-interference claim.";
    attribute :>> verificationMethod = "analyze";
    attribute :>> successCriteria = "Met when the analysis of the realization that phase 8 records shows, for a loss, a delay, a repetition and a corruption of a message on the Eclipse S-CORE path, that none can cause an uncommanded emergency braking, and names the element of the realization that prevents each.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-DRIVING-040'> reqWithholdWarningRequest : FunctionalRequirementCandidate {
    subject driverAssistanceSystem :> DE4SDV_DriverAssistanceFraming::candidateDriverAssistanceSystem;
    require constraint statement { language "English" /* While no collision with a vehicle ahead is imminent, the driver-assistance system shall withhold its warning request. */ }
    attribute :>> source = "NEED-DRIVING-009; SRC-UNECE-R152 false reaction avoidance; REQ-AEBS-008; gap gapVehicleTargetCriteria; scenarios SC-DRIVING-014 and SC-DRIVING-015";
    attribute :>> rationale = "Derived from the false reaction avoidance of the source regulation (SRC-UNECE-R152), which asks the system to minimise collision warnings where no collision is imminent and lists false-reaction scenarios for an assessment, and from REQ-AEBS-008. Phase 5 confirms the two scenarios that phase 2 proposed from that list, the curved road with guard pipes and a stationary object (SC-DRIVING-014) and the turn of a vehicle ahead (SC-DRIVING-015). In each, any warning is a false reaction, so the criterion is none. The source gives the speeds and the times to collision of these scenarios as guidance, not as a test: the settings take their approach speeds, and each run records the rest. The obligation is the candidate's; the settings are System 2's. A simulation cannot show the variety of real roads that the assessment of the source covers.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when the driver-assistance system gives no warning request in either run of SC-DRIVING-014 and of SC-DRIVING-015, and each run records the speeds and the times to collision that the guidance of the source regulation names for its scenario.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-DRIVING-041'> reqWithholdEmergencyBraking : FunctionalRequirementCandidate {
    subject driverAssistanceSystem :> DE4SDV_DriverAssistanceFraming::candidateDriverAssistanceSystem;
    require constraint statement { language "English" /* While no collision with a vehicle ahead is imminent, the driver-assistance system shall withhold emergency braking. */ }
    attribute :>> source = "NEED-DRIVING-009; SRC-UNECE-R152 false reaction avoidance; REQ-AEBS-012; gap gapVehicleTargetCriteria; scenarios SC-DRIVING-014 and SC-DRIVING-015";
    attribute :>> rationale = "Derived from the false reaction avoidance of the source regulation (SRC-UNECE-R152), which asks the system to avoid emergency braking where no collision is imminent, and from REQ-AEBS-012. The candidate's speed planner still slows the vehicle for the curve and for the vehicle ahead (longitudinal_planning.cpp:13-14, 34); only a command for 5.0 m/s² or more is an emergency braking. The obligation is the candidate's; the settings are System 2's. A simulation cannot show the variety of real roads that the assessment of the source covers.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when the driver-assistance system commands no deceleration of 5.0 m/s² or more in either run of SC-DRIVING-014 and of SC-DRIVING-015.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-DRIVING-042'> reqWarningRequestBeforeEmergencyBraking : FunctionalRequirementCandidate {
    subject driverAssistanceSystem :> DE4SDV_DriverAssistanceFraming::candidateDriverAssistanceSystem;
    require constraint statement { language "English" /* When a collision with a vehicle ahead is imminent, the driver-assistance system shall give a warning request at its boundary at least 1.0 s of simulation time before the start of its emergency braking. */ }
    attribute :>> source = "NEED-DRIVING-010; SRC-UNECE-R152 collision warning; REQ-AEBS-002; gap gapWarningOutput; scenarios SC-DRIVING-012 and SC-DRIVING-013";
    attribute :>> rationale = "Derived from the collision warning of the car to car scenario of the source regulation (SRC-UNECE-R152), which asks for the warning to the driver at the latest 0.8 s before the start of the emergency braking, and from REQ-AEBS-002. The obligation is the candidate's for the request and for its lead of 1.0 s. Of the 1.0 s, 0.2 s is allotted from the warning request to the start of each mode of the warning, on the display and as a sound. That share is the obligation of the Eclipse S-CORE path and the AAOS SDV, which phases 6 to 8 allocate: each mode is due within 0.2 s of wall-clock time after the request, and so at least 0.8 s before the start of the emergency braking while the simulation runs no faster than wall-clock time, a condition of the bench. The source lets the warning come as late as the start of the emergency braking when the collision cannot be anticipated in time; in SC-DRIVING-012 and SC-DRIVING-013 the target is ahead in the lane from the start of the run, so the exception does not apply. At 014e0e7a the application has no warning output at its boundary, and its forward-collision warning and its emergency braking are two ranges of one planned acceleration, with nothing that orders the first before the second (planning.cpp:113-121; gapWarningOutput). A simulation cannot show whether a driver perceives the warning.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when the driver-assistance system gives a warning request at its boundary in each judged run, and, in each judged run with an emergency braking, at least 1.0 s of simulation time before the start of the first emergency braking of the run.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-DRIVING-043'> reqWarningRequestOverSCORE : RequirementCandidate {
    subject driverAssistanceSystem :> DE4SDV_DriverAssistanceFraming::candidateDriverAssistanceSystem;
    require constraint statement { language "English" /* The driver-assistance system shall give its warning request to the AAOS SDV only over the Eclipse S-CORE path. */ }
    attribute :>> source = "NEED-DRIVING-010; scope item scoreCommandPathInScope; gaps gapWarningOutput and gapScoreIntegration; scenarios SC-DRIVING-012 and SC-DRIVING-013";
    attribute :>> rationale = "This is a design constraint: the warning reaches the driver through the S-CORE path of the product line to the AAOS SDV. At 014e0e7a the application's warnings go only to its own visualization and data log, each when it is switched on (vision_pilot.cpp:177-185), and its vehicle interface carries no warning (gapWarningOutput). A data log can give the evaluators a record of the warnings; it is not a warning request. Phases 6 to 8 decide how the request leaves the candidate.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when, in every run of SC-DRIVING-012 and SC-DRIVING-013, every warning request that reaches the AAOS SDV is matched in the communication records of the Eclipse S-CORE path to a warning request of the driver-assistance system, and when, in one further run of SC-DRIVING-012 in which the Eclipse S-CORE path of the driver-assistance system is stopped, no warning request reaches the AAOS SDV after the stop.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-DRIVING-044'> reqRecordCandidateIdentity : FunctionalRequirementCandidate {
    subject driverAssistanceSystem :> DE4SDV_DriverAssistanceFraming::candidateDriverAssistanceSystem;
    require constraint statement { language "English" /* The driver-assistance system shall record, before its first driving command of each run, the upstream revision of its source, the difference between its source and that revision, the SHA-256 of each network file it loads and the SHA-256 of its configuration. */ }
    attribute :>> source = "NEED-DRIVING-011; gap gapCandidateBehaviorUnverified; scenarios SC-DRIVING-012 to SC-DRIVING-015";
    attribute :>> rationale = "Another engineer can rerun a run only from what it names, and a build with a change that upstream has not merged is a different candidate: the recorded difference tells them apart. Source, network files and configuration are pinned separately, because none of them fixes the others. The configuration includes the run-time settings: at 014e0e7a the key source.mode chooses at run time where the camera image and the speed come from (vision_pilot.cpp:65-78), and the key speed_limit sets the speed that the candidate drives at (vision_pilot.conf:20). The scenario and the simulated configuration belong to System 2 and are pinned there.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when every run of SC-DRIVING-012 to SC-DRIVING-015 has the record before its first driving command; when another engineer who checks out the named revision, applies the recorded difference and hashes the named network files and the configuration obtains the recorded values; and when a build with one change that upstream has not merged records a non-empty difference.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  connection emergencyBrakingForImminentCollisionDerivation : DerivesFromNeed
    connect needWarnAndBrakeForVehicleAhead to reqEmergencyBrakingForImminentCollision;
  connection impactSpeedWithinLimitDerivation : DerivesFromNeed
    connect needWarnAndBrakeForVehicleAhead to reqImpactSpeedWithinLimit;
  connection drivingCommandOverSCOREDerivation : DerivesFromNeed
    connect needWarnAndBrakeForVehicleAhead to reqDrivingCommandOverSCORE;
  connection isolateEmergencyBrakingFromSCOREDerivation : DerivesFromNeed
    connect needWarnAndBrakeForVehicleAhead to reqIsolateEmergencyBrakingFromSCORE;
  connection withholdWarningRequestDerivation : DerivesFromNeed
    connect needNoReactionWithoutImminentCollision to reqWithholdWarningRequest;
  connection withholdEmergencyBrakingDerivation : DerivesFromNeed
    connect needNoReactionWithoutImminentCollision to reqWithholdEmergencyBraking;
  connection warningRequestBeforeEmergencyBrakingDerivation : DerivesFromNeed
    connect needWarningRequestForTheDriver to reqWarningRequestBeforeEmergencyBraking;
  connection warningRequestOverSCOREDerivation : DerivesFromNeed
    connect needWarningRequestForTheDriver to reqWarningRequestOverSCORE;
  connection recordCandidateIdentityDerivation : DerivesFromNeed
    connect needRunsIdentifyTheCandidate to reqRecordCandidateIdentity;

  comment vehicleTargetCriteriaFixedInPhase5 about DE4SDV_DriverAssistanceFraming::gapVehicleTargetCriteria
    /*
     * What phase 5 fixes of this gap, and whose obligation each criterion is.
     * - The approach speeds and the speed of the moving target, the settings
     *   of the terms above, come from the warning and activation tests with a
     *   stationary and a moving vehicle target of the source regulation. They
     *   are the obligation of System 2, which sets each scenario and the
     *   speed setting of the candidate; the own driving of the candidate
     *   holds them, and a run that misses them is not judged.
     * - The time of the warning request before the emergency braking,
     *   REQ-DRIVING-042, is the candidate's. Within it, 0.2 s from the
     *   request to each mode of the warning is the obligation of the Eclipse
     *   S-CORE path and the AAOS SDV, which phases 6 to 8 allocate.
     * - The braking demand, REQ-DRIVING-036, and the speed at impact,
     *   REQ-DRIVING-037, are the candidate's, with the simulated vehicle
     *   standing in for a real one.
     * - The two scenarios without a reaction, SC-DRIVING-014 and
     *   SC-DRIVING-015, are confirmed from the false-reaction scenarios of
     *   the source regulation. Their criterion is no warning request,
     *   REQ-DRIVING-040, and no emergency braking, REQ-DRIVING-041, both the
     *   candidate's.
     * - Two runs of each setting, both counted, are the obligation of System
     *   2.
     * Open: the applicability of the source regulation to the candidate and
     * its interpretation by an authority; what a simulation cannot show of
     * each criterion, which its rationale names and no verdict covers; and
     * the criteria record that the evaluators of phase 10 read.
     */

  /* ─────────────────────────────── Views ─────────────────────────────── */

  concern driverAssistanceNeedsConcern : StakeholderNeedsConcern {
    doc /*
     * Systems engineers and product-line engineers need the stakeholder needs
     * of the candidate driver-assistance system with their statements and
     * sources, and the planned stakeholder review of each, to judge whether
     * the needs cover the concerns of phase 1.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder productLineEngineer : ProductLineEngineer;
  }

  view driverAssistanceNeedsView : TVD::TableView {
    viewpoint selectedNeedsViewpoint : StakeholderRequirementDefinitionViewpoint {
      frame driverAssistanceNeedsConcern;
    }

    expose needWarnAndBrakeForVehicleAhead;
    expose needNoReactionWithoutImminentCollision;
    expose needWarningRequestForTheDriver;
    expose needRunsIdentifyTheCandidate;
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

  view driverAssistanceNeedValidationView : TVD::TableView {
    viewpoint selectedNeedValidationViewpoint : StakeholderRequirementDefinitionViewpoint {
      frame driverAssistanceNeedsConcern;
    }

    expose vehicleAheadResponseValidationPlan;
    expose noReactionValidationPlan;
    expose driverWarningValidationPlan;
    expose candidateIdentityValidationPlan;
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

  concern driverAssistanceRequirementTraceConcern : RequirementTraceConcern {
    doc /*
     * Compliance engineers and verification engineers need each requirement
     * of the driver-assistance system traced to the need it derives from,
     * with its source, its rationale, its verification method and its success
     * criteria, to judge whether the requirements answer the needs and can be
     * verified. The requirement definition table answers
     * vehicleTargetCriteriaConcern of the framing: each criterion for a
     * vehicle target with the provision of the source regulation it is
     * derived from, the product-line requirement it judges, whose obligation
     * it is and what a simulation cannot show of it.
     */
    subject;
    stakeholder complianceEngineer : ComplianceEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
  }

  view driverAssistanceRequirementsView : TVD::TableView {
    viewpoint selectedRequirementDefinitionViewpoint : SystemRequirementDefinitionViewpoint {
      frame driverAssistanceRequirementTraceConcern;
    }

    expose reqEmergencyBrakingForImminentCollision;
    expose reqImpactSpeedWithinLimit;
    expose reqDrivingCommandOverSCORE;
    expose reqIsolateEmergencyBrakingFromSCORE;
    expose reqWithholdWarningRequest;
    expose reqWithholdEmergencyBraking;
    expose reqWarningRequestBeforeEmergencyBraking;
    expose reqWarningRequestOverSCORE;
    expose reqRecordCandidateIdentity;
    filter @ SysML::RequirementUsage;
    attribute :>> includeReferenceElements = true;
    attribute :>> maxRowHeight = 500;
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
    view Rationale :> columnViews {
      attribute :>> featureToRender = CT::attributeValue {
        attribute attributeName = "rationale";
      }
      attribute :>> columnWidth = 420;
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
