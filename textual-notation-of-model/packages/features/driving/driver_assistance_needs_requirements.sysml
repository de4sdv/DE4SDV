/*
 * DE4SDV driver-assistance stakeholder needs.
 *
 * INC-DRIVING-002, phase 4: the stakeholder needs of the candidate
 * driver-assistance system, the system of interest the charter declares.
 * Each need is held by the parties it serves and leads its source with the
 * phase 1 concern it derives from. Each has one planned stakeholder review on
 * the scenarios of phase 2 it covers, carried out by the roles that check the
 * answer. Three concerns are reviewer questions: a need's source names them
 * and its review checks them. Phase 5 adds the requirements to this package.
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
    attribute :>> source = "INC-DRIVING-002 vehicleTargetResponseConcern, emergencyBrakingIndependenceConcern, scoreCommandAndWarningPathConcern, vehicleTargetCriteriaConcern, scope items vehicleTargetResponseInScope and scoreCommandPathInScope, gaps gapNoSeparateEmergencyFunction, gapScoreIntegration and gapCameraImageAndGeometry, assumption asmBenchReuse, scenarios SC-DRIVING-012 and SC-DRIVING-013";
    attribute :>> rationale = "The warning lets the driver act, and the braking is meant to avoid or lessen the collision when the driver does not act in time. The need states what they expect, not how well the candidate meets it, and carries no safety claim. Phase 5 derives the criteria for a vehicle target and their limits (gapVehicleTargetCriteria).";
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
    attribute :>> rationale = "The driver can act on a warning only if it reaches the display and the sound of the AAOS SDV. At the inspected revision the application has no warning output at its boundary; its warnings go to its own visualization and data log (gapWarningOutput). Phase 5 states when each mode is due relative to the warning request and to the start of the emergency braking. Whether a driver perceives the warning is out of scope.";
  }

  requirement <'NEED-DRIVING-011'> needRunsIdentifyTheCandidate : StakeholderNeedCandidate {
    subject driverAssistanceSystem :> DE4SDV_DriverAssistanceFraming::candidateDriverAssistanceSystem;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder productLineEngineer : ProductLineEngineer;
    require constraint statement { language "English" /* Verification engineers and product-line engineers need each run of the driver-assistance system to identify the candidate revision and the configuration it ran with, so that each verdict is bound to what ran. */ }
    attribute :>> source = "INC-DRIVING-002 candidateVerdictConcern, scope item verdictEvidenceInScope, gap gapCandidateBehaviorUnverified, scenarios SC-DRIVING-012 to SC-DRIVING-015";
    attribute :>> rationale = "The lifecycle decision rests on a verdict for each requirement and scenario, and a verdict holds only for the candidate that ran. A build with a change that upstream has not merged is a different candidate. The scenario and the simulated configuration belong to System 2 and are pinned there, so this need covers only what the candidate itself runs.";
  }

  comment visionPilotContractAtPin about needWarnAndBrakeForVehicleAhead, needWarningRequestForTheDriver
    /*
     * The runtime contract of VisionPilot at commit
     * 014e0e7a56ee8e597c2cab8175233f74edd9b856, kept for phase 5.
     * - The application reads one camera frame and the vehicle speed, and
     *   writes steering and acceleration
     *   (VisionPilot/app/vision_pilot.cpp:117, 142, 174).
     * - The ROS 2 build (ENABLE_ROS2_INTERFACE,
     *   VisionPilot/app/vision_pilot.cpp:59-64) reads the camera image and
     *   the speed from topics and writes the commands to topics.
     * - The file build reads a video and a speed file, and its vehicle write
     *   does nothing
     *   (VisionPilot/modules/sensing/vehicle_interface/src/file_interface.cpp:37-61).
     * - The live V4L2 build pairs with a CAN vehicle interface whose read
     *   returns zero and whose write does nothing
     *   (VisionPilot/modules/sensing/vehicle_interface/src/can_interface.cpp:4-12;
     *   VisionPilot/app/vision_pilot.cpp:73-78).
     * So at the pin only the ROS 2 build gives a real speed and commands a
     * vehicle.
     * - The forward-collision warning and the emergency braking are two
     *   ranges of the acceleration that one speed planner computes
     *   (VisionPilot/modules/safety_guardian/planning/src/planning.cpp:113-121).
     *   One planning cycle flags at most one of the two, and nothing in the
     *   code orders the warning before the braking; phase 5 derives the
     *   criterion for the time between them.
     */

  /* ───────────────── Phase 4: planned stakeholder reviews ───────────────── */

  part <'SC-DRIVING-016'> vehicleAheadResponseValidationPlan : ValidationPlanningScenario {
    doc /* For NEED-DRIVING-008, a planned stakeholder review. While the
         * stationary and the slower moving vehicle target scenarios run
         * (SC-DRIVING-012 and SC-DRIVING-013), can verification engineers and
         * compliance engineers confirm, by the criteria for a vehicle target
         * that phase 5 derives, that the candidate requests the warning and
         * that its driving command brakes the vehicle, and that no autopilot,
         * replay or overlay acts instead of the candidate? Can systems
         * engineers and product-line engineers confirm that every driving
         * command passed through Eclipse S-CORE to the actuation and every
         * warning request through S-CORE to the AAOS SDV, and that no other
         * exchange carried them? And can safety experts and product-line
         * engineers tell which element of the candidate gave the braking
         * command, whether it left the candidate in the driving command or
         * apart from it, and whether that command keeps the independence of
         * the protected emergency command path? */
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
         * verification engineers confirm that each warning request of the
         * candidate reached the AAOS SDV, that the AAOS SDV gave the warning
         * on its display and as a sound, and when each mode began relative to
         * the warning request and to the start of the emergency braking, with
         * no recording or overlay in place of either mode? */
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
}
