/*
 * DE4SDV closed-loop driving functional architecture.
 *
 * INC-DRIVING-001, phase 6: the functions of the candidate driving system
 * and the requirements of phase 5 each carries. Seven functions identify
 * the run, assemble the inputs the checkpoint takes, plan by checkpoint
 * inference, supervise the inputs and the plans, command the vehicle, apply
 * the commands at the actuation and publish the operational state. The stop
 * response is a mode of the one command path, not a second command source;
 * the actuation applies it itself only when commands stop arriving there.
 * Every requirement but REQ-DRIVING-014 is allocated to a function.
 * REQ-DRIVING-014 constrains how the plan and the commands are carried
 * between the functions, over Eclipse S-CORE communication, not what a
 * function does: phase 8 carries it by the S-CORE elements it places on
 * those exchanges. An allocation assigns responsibility only (allocatedTo);
 * it asserts no satisfaction. No logical element, platform, transport or
 * technology is chosen, and no safety claim is made.
 */

package DE4SDV_ClosedLoopDrivingFunctionalArchitecture {
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_TraceVocabulary::AllocatableFunction;
  private import DE4SDV_ClosedLoopDrivingFraming::degradedInputBehaviorConcern;
  private import DE4SDV_ClosedLoopDrivingOperationalContext::CameraImages;
  private import DE4SDV_ClosedLoopDrivingOperationalContext::EgoMotionState;
  private import DE4SDV_ClosedLoopDrivingOperationalContext::Route;
  private import DE4SDV_ClosedLoopDrivingOperationalContext::VehicleMotionCommand;
  private import DE4SDV_ClosedLoopDrivingOperationalContext::DrivingOperationalState;
  private import DE4SDV_ClosedLoopDrivingNeedsRequirements::*;
  private import SAF_Viewpoints::*;
  private import SysideViews::**;
  private import Views::*;

  /* ───────────── Items the functions exchange inside the driving system ───────────── */

  item def CheckpointInputs {
    doc /*
     * The inputs of one step in the form the checkpoint takes: the camera
     * images with their histories and projection operators, the map_context
     * and route_mask rasters, and the ego-motion history (REQ-DRIVING-003 to
     * REQ-DRIVING-008).
     */
  }

  item def InputCondition {
    doc /*
     * For one step: whether the camera history and the ego-motion history are
     * complete, and the capture times and the validity of the newest camera
     * images, of the newest motion sample and of the route.
     */
  }

  item def DrivingPlan {
    doc /*
     * A plan as the terms of the requirements define it, marked with the
     * capture time of its newest camera image, its production time and the
     * run record that identifies its checkpoint.
     */
  }

  item def DrivingMode {
    doc /* The mode of ClosedLoopDrivingModes the driving system is in, with the cause of a stop. */
  }

  item def RunRecord {
    doc /*
     * The identity of a run: the SHA-256 of the checkpoint file it loaded, the
     * AutoE2E source revision it runs and the SHA-256 of its complete
     * configuration.
     */
  }

  /* ─────────────────────────────── Functions ─────────────────────────────── */

  action def IdentifyRun :> AllocatableFunction {
    doc /*
     * Before the first plan of a run: compares the SHA-256 of the checkpoint
     * file with the one the configuration names, refuses to plan when they
     * differ or the configuration names none, and records the run identity.
     */
    out runRecord : RunRecord;
  }

  action def AssembleCheckpointInputs :> AllocatableFunction {
    doc /*
     * Marks each camera image and each motion sample with its capture time and
     * builds, for each step, the inputs the checkpoint takes: the images in its
     * camera order and sizes with their histories and projection operators,
     * the two rasters of the route and its map, and the ego-motion history,
     * all from inputs captured in the run. Reports whether the histories are
     * complete and how old and how valid the newest inputs are.
     */
    in cameraImages : CameraImages;
    in egoMotion : EgoMotionState;
    in route : Route;
    out checkpointInputs : CheckpointInputs;
    out inputCondition : InputCondition;
  }

  action def PlanTrajectory :> AllocatableFunction {
    doc /*
     * Makes one plan for each step by inference of the pinned checkpoint on the
     * inputs of the step, and marks it with the capture time of its newest
     * camera image, its production time and the run record.
     */
    in checkpointInputs : CheckpointInputs;
    in runRecord : RunRecord;
    out plan : DrivingPlan;
  }

  action def SuperviseDrivingLoop :> AllocatableFunction {
    doc /*
     * Detects degraded input and plans in the limits of REQ-DRIVING-023 to
     * REQ-DRIVING-027: camera images missing, invalid or too old, a motion
     * sample invalid or too old, a route too old or without a route corridor,
     * a newest valid plan too old at a command, and a plan that is not valid.
     * Sets the mode: priming until both histories are complete, then driving;
     * stopped, with the cause, from its first detection. Passes the newest
     * valid plan on.
     */
    in inputCondition : InputCondition;
    in plan : DrivingPlan;
    out mode : DrivingMode;
    out validPlan : DrivingPlan;
  }

  action def CommandVehicle :> AllocatableFunction {
    doc /*
     * Computes the steering and acceleration commands within the limits of the
     * vehicle its configuration names: while priming, commands that hold the
     * vehicle at standstill; while driving, commands from the newest valid plan
     * and the current motion of the vehicle; while stopped, the stop response,
     * deceleration to standstill with the steering held, then standstill until
     * the run ends. Marks each command with the plan it was computed from and
     * its issue time.
     */
    in validPlan : DrivingPlan;
    in mode : DrivingMode;
    in currentMotion : EgoMotionState;
    out command : VehicleMotionCommand;
  }

  action def ApplyCommandsAtActuation :> AllocatableFunction {
    doc /*
     * Gives each command to the actuation of the vehicle and marks it with its
     * actuation time. When no valid command has reached the actuation in the
     * limit of REQ-DRIVING-028, it applies the stop response there itself, so
     * the vehicle stops also when the command path does not deliver.
     */
    in command : VehicleMotionCommand;
    out actuatedCommand : VehicleMotionCommand;
  }

  action def PublishOperationalState :> AllocatableFunction {
    doc /*
     * Publishes for observation each plan, the motion sample of each step, the
     * health at least periodically and the stop with its cause, each with its
     * producer and its time. Publication is one way and never waits for a
     * receiver, so how AAOS SDV receives it does not change the plans, the
     * commands or the planning time.
     */
    in plan : DrivingPlan;
    in motion : EgoMotionState;
    in mode : DrivingMode;
    out operationalState : DrivingOperationalState;
  }

  /* ─────────────────── The functional breakdown of one step ─────────────────── */

  action def ClosedLoopDrivingFunctionalFlow {
    doc /*
     * The driving system broken into its functions, and the items they
     * exchange in one step. The camera images, the ego-motion state and the
     * route come from the context of phase 2; the commands go to the
     * actuation of the vehicle, and the operational state to AAOS SDV. Only
     * the commands of CommandVehicle reach the actuation, and nothing the
     * publication gives flows back into the loop.
     */
    in item cameraImages : CameraImages;
    in item egoMotion : EgoMotionState;
    in item route : Route;
    out item vehicleCommand : VehicleMotionCommand;
    out item operationalState : DrivingOperationalState;

    action identifyRun : IdentifyRun {
      out runRecord;
    }

    action assembleInputs : AssembleCheckpointInputs {
      in cameraImages = ClosedLoopDrivingFunctionalFlow::cameraImages;
      in egoMotion = ClosedLoopDrivingFunctionalFlow::egoMotion;
      in route = ClosedLoopDrivingFunctionalFlow::route;
      out checkpointInputs;
      out inputCondition;
    }

    action planTrajectory : PlanTrajectory {
      in checkpointInputs;
      in runRecord;
      out plan;
    }
    flow from assembleInputs.checkpointInputs to planTrajectory.checkpointInputs;
    flow from identifyRun.runRecord to planTrajectory.runRecord;
    first assembleInputs then planTrajectory;

    action superviseLoop : SuperviseDrivingLoop {
      in inputCondition;
      in plan;
      out mode;
      out validPlan;
    }
    flow from assembleInputs.inputCondition to superviseLoop.inputCondition;
    flow from planTrajectory.plan to superviseLoop.plan;
    first planTrajectory then superviseLoop;

    action commandVehicle : CommandVehicle {
      in validPlan;
      in mode;
      in currentMotion = ClosedLoopDrivingFunctionalFlow::egoMotion;
      out command;
    }
    flow from superviseLoop.validPlan to commandVehicle.validPlan;
    flow from superviseLoop.mode to commandVehicle.mode;
    first superviseLoop then commandVehicle;

    action applyCommands : ApplyCommandsAtActuation {
      in command;
      out actuatedCommand = ClosedLoopDrivingFunctionalFlow::vehicleCommand;
    }
    flow from commandVehicle.command to applyCommands.command;
    first commandVehicle then applyCommands;

    action publishState : PublishOperationalState {
      in plan;
      in motion = ClosedLoopDrivingFunctionalFlow::egoMotion;
      in mode;
      out operationalState = ClosedLoopDrivingFunctionalFlow::operationalState;
    }
    flow from planTrajectory.plan to publishState.plan;
    flow from superviseLoop.mode to publishState.mode;
  }

  action closedLoopDrivingFunctionalFlow : ClosedLoopDrivingFunctionalFlow;

  /* ────────────────────────────────── Modes ────────────────────────────────── */

  state def ClosedLoopDrivingModes {
    doc /*
     * The modes the health of the driving system names. Priming holds the
     * vehicle at standstill until both histories are complete; driving
     * commands from the newest valid plan; stopped is the stop response, then
     * standstill until the run ends, with no transition out. The first
     * detection of SuperviseDrivingLoop leads to stopped, from priming as from
     * driving; CommandVehicle computes the commands of each mode.
     */
    state priming;
    state driving;
    state stopped;
    transition first priming then driving;   // both histories complete
    transition first priming then stopped;   // a detection of SuperviseDrivingLoop
    transition first driving then stopped;   // a detection of SuperviseDrivingLoop
  }

  /* ─────────────── Requirement-to-function allocations (allocatedTo) ─────────────── */

  /* Identifying the run. */
  allocation runIdentityResponsibility
    allocate reqRecordRunIdentity to ClosedLoopDrivingFunctionalFlow::identifyRun;
  allocation unpinnedCheckpointResponsibility
    allocate reqRefuseUnpinnedCheckpoint to ClosedLoopDrivingFunctionalFlow::identifyRun;

  /* Assembling the inputs the checkpoint takes. */
  allocation cameraFormResponsibility
    allocate reqCameraImagesInCheckpointForm to ClosedLoopDrivingFunctionalFlow::assembleInputs;
  allocation cameraHistoryResponsibility
    allocate reqCameraHistory to ClosedLoopDrivingFunctionalFlow::assembleInputs;
  allocation projectionOperatorResponsibility
    allocate reqProjectionOperators to ClosedLoopDrivingFunctionalFlow::assembleInputs;
  allocation mapContextResponsibility
    allocate reqMapContextRaster to ClosedLoopDrivingFunctionalFlow::assembleInputs;
  allocation routeMaskResponsibility
    allocate reqRouteMaskRaster to ClosedLoopDrivingFunctionalFlow::assembleInputs;
  allocation egoMotionHistoryResponsibility
    allocate reqEgoMotionHistory to ClosedLoopDrivingFunctionalFlow::assembleInputs;
  allocation capturedInputsResponsibility
    allocate reqHistoriesFromCapturedInputs to ClosedLoopDrivingFunctionalFlow::assembleInputs;
  allocation inputStampResponsibility
    allocate reqStampInputs to ClosedLoopDrivingFunctionalFlow::assembleInputs;

  /* Planning. */
  allocation planEachStepResponsibility
    allocate reqPlanEachStep to ClosedLoopDrivingFunctionalFlow::planTrajectory;
  allocation checkpointInferenceResponsibility
    allocate reqPlansByCheckpointInference to ClosedLoopDrivingFunctionalFlow::planTrajectory;
  allocation planningPeriodResponsibility
    allocate reqPlanWithinPlanningPeriod to ClosedLoopDrivingFunctionalFlow::planTrajectory;
  allocation planStampResponsibility
    allocate reqStampPlans to ClosedLoopDrivingFunctionalFlow::planTrajectory;
  allocation planRunRecordResponsibility
    allocate reqPlansNameRunRecord to ClosedLoopDrivingFunctionalFlow::planTrajectory;

  /* Supervising the inputs and the plans. */
  allocation degradedCameraResponsibility
    allocate reqStopOnDegradedCameraImages to ClosedLoopDrivingFunctionalFlow::superviseLoop;
  allocation degradedMotionResponsibility
    allocate reqStopOnDegradedMotion to ClosedLoopDrivingFunctionalFlow::superviseLoop;
  allocation degradedRouteResponsibility
    allocate reqStopOnDegradedRoute to ClosedLoopDrivingFunctionalFlow::superviseLoop;
  allocation stalePlanResponsibility
    allocate reqStopOnStalePlan to ClosedLoopDrivingFunctionalFlow::superviseLoop;
  allocation invalidPlanResponsibility
    allocate reqStopOnInvalidPlan to ClosedLoopDrivingFunctionalFlow::superviseLoop;

  /* Commanding the vehicle, the stop response included. */
  allocation primingHoldResponsibility
    allocate reqHoldUntilHistoriesComplete to ClosedLoopDrivingFunctionalFlow::commandVehicle;
  allocation newestValidPlanResponsibility
    allocate reqCommandsFromNewestValidPlan to ClosedLoopDrivingFunctionalFlow::commandVehicle;
  allocation actuationLimitsResponsibility
    allocate reqCommandsWithinActuationLimits to ClosedLoopDrivingFunctionalFlow::commandVehicle;
  allocation stopDecelerationResponsibility
    allocate reqStopResponseDeceleration to ClosedLoopDrivingFunctionalFlow::commandVehicle;
  allocation stopSteeringResponsibility
    allocate reqStopResponseSteeringHeld to ClosedLoopDrivingFunctionalFlow::commandVehicle;
  allocation standstillAfterStopResponsibility
    allocate reqStandstillAfterStop to ClosedLoopDrivingFunctionalFlow::commandVehicle;
  allocation commandStampResponsibility
    allocate reqStampCommands to ClosedLoopDrivingFunctionalFlow::commandVehicle;

  /* Applying the commands at the actuation. */
  allocation lostCommandsResponsibility
    allocate reqStopOnLostCommands to ClosedLoopDrivingFunctionalFlow::applyCommands;
  allocation actuationStampResponsibility
    allocate reqStampCommands to ClosedLoopDrivingFunctionalFlow::applyCommands;

  /* Publishing the operational state. */
  allocation planPublicationResponsibility
    allocate reqPublishPlans to ClosedLoopDrivingFunctionalFlow::publishState;
  allocation vehicleStatePublicationResponsibility
    allocate reqPublishVehicleState to ClosedLoopDrivingFunctionalFlow::publishState;
  allocation healthPublicationResponsibility
    allocate reqPublishHealthPeriodically to ClosedLoopDrivingFunctionalFlow::publishState;
  allocation stopPublicationResponsibility
    allocate reqPublishStop to ClosedLoopDrivingFunctionalFlow::publishState;
  allocation planIndependenceResponsibility
    allocate reqPlansIndependentOfObservation to ClosedLoopDrivingFunctionalFlow::publishState;
  allocation planningTimeIndependenceResponsibility
    allocate reqPlanningTimeIndependentOfObservation to ClosedLoopDrivingFunctionalFlow::publishState;

  /* ─────────────────────────────── Views ─────────────────────────────── */

  concern closedLoopDrivingFunctionsConcern : FunctionalBehaviorConcern {
    doc /*
     * System architects and verification engineers need the functions of the
     * driving system and each requirement of phase 5 mapped to the functions
     * that carry it: phase 7 gives the functions to logical elements, and
     * phase 10 verifies each requirement on its functions.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder verificationEngineer : VerificationEngineer;
  }

  view closedLoopDrivingFunctionBreakdownView {
    viewpoint selectedFunctionalBreakdownViewpoint : SystemFunctionalBreakdownStructureViewpoint {
      frame closedLoopDrivingFunctionsConcern;
    }
    expose ClosedLoopDrivingFunctionalFlow;
    expose ClosedLoopDrivingFunctionalFlow::identifyRun;
    expose ClosedLoopDrivingFunctionalFlow::assembleInputs;
    expose ClosedLoopDrivingFunctionalFlow::planTrajectory;
    expose ClosedLoopDrivingFunctionalFlow::superviseLoop;
    expose ClosedLoopDrivingFunctionalFlow::commandVehicle;
    expose ClosedLoopDrivingFunctionalFlow::applyCommands;
    expose ClosedLoopDrivingFunctionalFlow::publishState;
    attribute showAnnotationRows = false;
    attribute maxCompartmentEntries = 0;
    render asTreeDiagram;
  }

  view closedLoopDrivingRequirementFunctionMappingView : MVD::MatrixView {
    viewpoint selectedRequirementFunctionViewpoint : SystemFunctionalBreakdownStructureViewpoint {
      frame closedLoopDrivingFunctionsConcern;
      frame degradedInputBehaviorConcern;
    }
    view :>> rowView {
      expose reqPlanEachStep;
      expose reqPlansByCheckpointInference;
      expose reqCameraImagesInCheckpointForm;
      expose reqCameraHistory;
      expose reqProjectionOperators;
      expose reqMapContextRaster;
      expose reqRouteMaskRaster;
      expose reqEgoMotionHistory;
      expose reqHoldUntilHistoriesComplete;
      expose reqHistoriesFromCapturedInputs;
      expose reqCommandsFromNewestValidPlan;
      expose reqCommandsWithinActuationLimits;
      expose reqPlanWithinPlanningPeriod;
      expose reqPlansAndCommandsOverSCORE;
      expose reqPublishPlans;
      expose reqPublishVehicleState;
      expose reqPublishHealthPeriodically;
      expose reqPlansIndependentOfObservation;
      expose reqPlanningTimeIndependentOfObservation;
      expose reqStopResponseDeceleration;
      expose reqStopResponseSteeringHeld;
      expose reqStandstillAfterStop;
      expose reqStopOnDegradedCameraImages;
      expose reqStopOnDegradedMotion;
      expose reqStopOnDegradedRoute;
      expose reqStopOnStalePlan;
      expose reqStopOnInvalidPlan;
      expose reqStopOnLostCommands;
      expose reqPublishStop;
      expose reqStampInputs;
      expose reqStampPlans;
      expose reqStampCommands;
      expose reqRecordRunIdentity;
      expose reqPlansNameRunRecord;
      expose reqRefuseUnpinnedCheckpoint;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> columnView {
      expose closedLoopDrivingFunctionalFlow::identifyRun;
      expose closedLoopDrivingFunctionalFlow::assembleInputs;
      expose closedLoopDrivingFunctionalFlow::planTrajectory;
      expose closedLoopDrivingFunctionalFlow::superviseLoop;
      expose closedLoopDrivingFunctionalFlow::commandVehicle;
      expose closedLoopDrivingFunctionalFlow::applyCommands;
      expose closedLoopDrivingFunctionalFlow::publishState;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> cellView {
      expose DE4SDV_ClosedLoopDrivingFunctionalArchitecture::*;
      attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;
    }
  }
}
