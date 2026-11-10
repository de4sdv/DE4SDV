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
 *
 * The loop around the system is a process, not a second architecture:
 * navigation gives the route, the vehicle's cameras and motion sensing give
 * the images and the ego motion, its actuation applies the commands and the
 * state observer presents the published state. Those are functions of the
 * context elements, outside the scope of the driving system, and
 * ClosedLoopDrivingSystemProcess runs the system as one action between them.
 * Its participants are the parts of the one operational context of phase 2,
 * bound by reference: the process declares no context of its own.
 * The functions whose behavior differs by mode depend on the modes of
 * ClosedLoopDrivingModes, and the conceptual interfaces of the system are
 * the ports of ClosedLoopDrivingFunctionalBoundary, whose items specialize
 * the items of phase 2. No vehicle signal specification is imported or used
 * anywhere in this package: the interface items are conceptual, their
 * quantities are ISQ quantity values, and the signal typing of an interface
 * starts in phase 8, at the port where an item enters a software contract.
 *
 * Amended on the owner's decision of 2026-11-06 (GAP-DRIVING-005 of phase
 * 8): the actuation reports its state to the publication, so the stop it
 * applies itself reaches the observer with its cause. Described the same
 * day: what the camera images and the motion samples carry at the boundary.
 */

package DE4SDV_ClosedLoopDrivingFunctionalArchitecture {
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_TraceVocabulary::AllocatableFunction;
  private import DE4SDV_ClosedLoopDrivingFraming::degradedInputBehaviorConcern;
  private import DE4SDV_ClosedLoopDrivingFraming::ClosedLoopDrivingSystem;
  private import DE4SDV_OperationalContext::SubjectVehicle;
  private import DE4SDV_ClosedLoopDrivingOperationalContext::CameraImages;
  private import DE4SDV_ClosedLoopDrivingOperationalContext::EgoMotionState;
  private import DE4SDV_ClosedLoopDrivingOperationalContext::Route;
  private import DE4SDV_ClosedLoopDrivingOperationalContext::VehicleMotionCommand;
  private import DE4SDV_ClosedLoopDrivingOperationalContext::DrivingOperationalState;
  private import DE4SDV_ClosedLoopDrivingOperationalContext::NavigationSystem;
  private import DE4SDV_ClosedLoopDrivingOperationalContext::DrivingStateObserverApplication;
  private import DE4SDV_ClosedLoopDrivingOperationalContext::closedLoopDrivingOperationalContext;
  private import DE4SDV_ClosedLoopDrivingNeedsRequirements::*;
  private import ScalarValues::Positive;
  private import SAF_Viewpoints::*;
  private import StandardViewDefinitions::*;
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

  item def ActuationState {
    doc /*
     * For each step, what the actuation did: the command it applied with its
     * actuation time, or that its own stop response is in force, since when
     * and why, when no valid command reached it in the limit of
     * REQ-DRIVING-028. It goes to the publication only, so that the stop the
     * actuation decides is published with its cause (REQ-DRIVING-029) like
     * the stop the supervision decides; nothing of it enters the loop.
     */
  }

  /* ────────────── The loop functions of the context elements of phase 2 ────────────── */

  action def ContextElementFunction {
    doc /*
     * A behavior of a context element of phase 2 in the closed loop. It is
     * outside the scope of the driving system: the system does not provide it
     * and no requirement of phase 5 is allocated to it.
     */
  }

  action def GiveRoute :> ContextElementFunction {
    doc /*
     * Navigation: gives the route to the destination the driver chose, over
     * its map. It chooses no trajectory, and it takes nothing from the
     * driving system.
     */
    out route : Route;
  }

  action def CaptureCameraImages :> ContextElementFunction {
    doc /* The vehicle's cameras: capture the road environment and give the images with their capture times. */
    out cameraImages : CameraImages;
  }

  action def SampleEgoMotion :> ContextElementFunction {
    doc /* The vehicle's motion sensing: sample its own motion and give the samples with their times. */
    out egoMotion : EgoMotionState;
  }

  action def ApplyMotionCommands :> ContextElementFunction {
    doc /* The vehicle's actuation: apply the steering and acceleration commands it is given and move the vehicle. */
    in command : VehicleMotionCommand;
  }

  action def PresentDrivingState :> ContextElementFunction {
    doc /* The state observer: present the published plan, vehicle state and health to the driver and send nothing back. */
    in operationalState : DrivingOperationalState;
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
     * Makes the plan of a step by inference of the pinned checkpoint on the
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
     * the vehicle stops also when the command path does not deliver. It
     * reports its actuation state to the publication: the applied command
     * with its time, or its own stop with the cause.
     */
    in command : VehicleMotionCommand;
    out actuatedCommand : VehicleMotionCommand;
    out actuationState : ActuationState;
  }

  action def PublishOperationalState :> AllocatableFunction {
    doc /*
     * Publishes for observation each plan, the motion sample of each step, the
     * health at least periodically and the stop with its cause, whether the
     * supervision decided it (the mode) or the actuation did (the actuation
     * state), each with its producer and its time. Publication is one way and
     * never waits for a receiver, so how the state observer receives it does
     * not change the plans, the commands or the planning time.
     */
    in plan : DrivingPlan;
    in motion : EgoMotionState;
    in mode : DrivingMode;
    in actuationState : ActuationState;
    out operationalState : DrivingOperationalState;
  }

  /* ─────────────────── The functional breakdown of one step ─────────────────── */

  action def ClosedLoopDrivingFunctionalFlow {
    doc /*
     * The driving system broken into its functions, and the items they
     * exchange in one step. The camera images, the ego-motion state and the
     * route come from the context of phase 2; the commands go to the
     * actuation of the vehicle, and the operational state to the state
     * observer. Only the commands of CommandVehicle reach the actuation, and
     * nothing the publication gives flows back into the loop.
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
      out actuationState;
    }
    flow from commandVehicle.command to applyCommands.command;
    first commandVehicle then applyCommands;

    action publishState : PublishOperationalState {
      in plan;
      in motion = ClosedLoopDrivingFunctionalFlow::egoMotion;
      in mode;
      in actuationState;
      out operationalState = ClosedLoopDrivingFunctionalFlow::operationalState;
    }
    flow from planTrajectory.plan to publishState.plan;
    flow from superviseLoop.mode to publishState.mode;
    flow from applyCommands.actuationState to publishState.actuationState;
  }

  action closedLoopDrivingFunctionalFlow : ClosedLoopDrivingFunctionalFlow;

  /* ─────────── The system process: the system between the context elements ─────────── */

  action def ClosedLoopDrivingSystemProcess {
    doc /*
     * One cycle of the loop as a process. The participants are the context
     * parts of phase 2 themselves and the system of interest, bound by
     * reference as the story's actors are: the process declares no part of
     * its own, so the increment has one context. Each participant owns and
     * performs its functions of the loop, as the swim lane of its function:
     * navigation gives the route, the vehicle's cameras and motion sensing
     * give the images and the ego motion, the driving system plans and
     * commands as one action of the process, the vehicle's actuation applies
     * the commands, and the state observer presents the published state. The
     * functions of the context elements are outside the scope of the driving
     * system; the driving system's functional scope is the one functional
     * flow usage it performs. The items that cross its boundary are the flows
     * of the process, each chained through the participant that gives and
     * the one that takes, in the order the loop runs, and nothing the
     * observation gives flows back into it. The process states the functional scope, the services the
     * context elements are expected to give and the exchanges only: no
     * planning, transport or display technology, no response deadline and no
     * timing claim is fixed here.
     */
    ref part navigation : NavigationSystem = closedLoopDrivingOperationalContext::navigation {
      doc /* Navigation of phase 2: it gives the route, and nothing else. */
      perform action giveRoute : GiveRoute;
    }

    ref part vehicle : SubjectVehicle = closedLoopDrivingOperationalContext::vehicle {
      doc /* The vehicle of phase 2: its cameras and motion sensing give the input, and its actuation applies the commands. */
      perform action captureImages : CaptureCameraImages;
      perform action sampleEgoMotion : SampleEgoMotion;
      perform action applyCommands : ApplyMotionCommands;
    }

    ref part drivingSystem : ClosedLoopDrivingSystem = closedLoopDrivingOperationalContext::drivingSystem {
      doc /* The system of interest of phase 2: it performs its whole functional flow, the one usage its functional boundary performs, from the inputs of the checkpoint to the commands and the published state. */
      perform closedLoopDrivingFunctionalFlow;
    }

    ref part stateObserver : DrivingStateObserverApplication = closedLoopDrivingOperationalContext::aaosSDVGuest::stateObserver {
      doc /* The state observer of phase 2: it presents the published state and sends nothing back. */
      perform action presentState : PresentDrivingState;
    }

    flow from navigation.giveRoute.route to drivingSystem.closedLoopDrivingFunctionalFlow.route;
    flow from vehicle.captureImages.cameraImages to drivingSystem.closedLoopDrivingFunctionalFlow.cameraImages;
    flow from vehicle.sampleEgoMotion.egoMotion to drivingSystem.closedLoopDrivingFunctionalFlow.egoMotion;
    flow from drivingSystem.closedLoopDrivingFunctionalFlow.vehicleCommand to vehicle.applyCommands.command;
    flow from drivingSystem.closedLoopDrivingFunctionalFlow.operationalState to stateObserver.presentState.operationalState;
  }

  action closedLoopDrivingSystemProcess : ClosedLoopDrivingSystemProcess;

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
    state priming {
      doc /*
       * Both histories are incomplete: CommandVehicle holds the vehicle at
       * standstill while plans are produced, and PublishOperationalState
       * publishes the mode.
       */
    }
    state driving {
      doc /*
       * Both histories are complete and no detection has stopped the loop:
       * CommandVehicle commands from the newest valid plan, and
       * PublishOperationalState publishes the plan, the vehicle state and the
       * health.
       */
    }
    state stopped {
      doc /*
       * The stop response, from the first detection of SuperviseDrivingLoop:
       * CommandVehicle computes the stop response, deceleration to standstill
       * with the steering held, then standstill, and PublishOperationalState
       * publishes the stop with its cause. There is no transition out.
       */
    }
    transition first priming then driving;   // both histories complete
    transition first priming then stopped;   // a detection of SuperviseDrivingLoop
    transition first driving then stopped;   // a detection of SuperviseDrivingLoop
  }

  /* ────────── The functions whose behavior differs by mode depend on it ────────── */

  dependency commandVehicleDependsOnPrimingMode
    from ClosedLoopDrivingFunctionalFlow::commandVehicle
    to ClosedLoopDrivingModes::priming;
  dependency commandVehicleDependsOnDrivingMode
    from ClosedLoopDrivingFunctionalFlow::commandVehicle
    to ClosedLoopDrivingModes::driving;
  dependency commandVehicleDependsOnStoppedMode
    from ClosedLoopDrivingFunctionalFlow::commandVehicle
    to ClosedLoopDrivingModes::stopped;
  dependency publishStateDependsOnStoppedMode
    from ClosedLoopDrivingFunctionalFlow::publishState
    to ClosedLoopDrivingModes::stopped;

  /* ────────── The conceptual interfaces of the system: one functional chain ────────── */

  enum def CameraPosition {
    doc /*
     * The six camera positions of the vehicle, in the order REQ-DRIVING-003
     * fixes for the checkpoint's input.
     */
    front;
    frontLeft;
    frontRight;
    rearLeft;
    rear;
    rearRight;
  }

  item def CameraImage {
    doc /*
     * One image of one of the vehicle's cameras: its position, its capture
     * time in simulation time (REQ-DRIVING-030), its size in pixels, and the
     * calibration of its camera, the intrinsic matrix and the pose in the
     * vehicle frame, from which the projection operator of REQ-DRIVING-005
     * is built once the image is scaled to the size the checkpoint takes
     * (REQ-DRIVING-003). The calibration is the camera's and travels with its
     * images; the driving system builds no calibration of its own.
     */
    attribute position : CameraPosition;
    attribute captureTime : ISQ::DurationValue;
    attribute widthPixels : Positive;
    attribute heightPixels : Positive;
  }

  item def CameraImageInput :> CameraImages {
    doc /*
     * The camera images as they enter the driving system at its input: for
     * each step one image per position, the six in the order of
     * CameraPosition (REQ-DRIVING-003), each with its capture time
     * (REQ-DRIVING-030) and its camera's calibration (REQ-DRIVING-005).
     */
    item image : CameraImage[6] ordered;
  }

  item def EgoMotionSample {
    doc /*
     * One sample of the vehicle's own motion: its speed, its longitudinal
     * and lateral acceleration and its yaw rate, as ISQ quantities, with its
     * sample time in simulation time (REQ-DRIVING-030). The curvature of the
     * checkpoint's history (REQ-DRIVING-008) is no sampled quantity: the
     * checkpoint's data derive it from the yaw rate and the speed. Under the
     * bounded deviation of asmSourceAuthenticity, the driving system gives
     * the checkpoint yaw rate and curvature as zero.
     */
    attribute speed : ISQ::SpeedValue;
    attribute longitudinalAcceleration : ISQ::AccelerationValue;
    attribute lateralAcceleration : ISQ::AccelerationValue;
    attribute yawRate : ISQ::AngularVelocityValue;
    attribute sampleTime : ISQ::DurationValue;
  }

  item def EgoMotionInput :> EgoMotionState {
    doc /*
     * The vehicle's motion as it enters the driving system at its input: its
     * samples in the order of their sample times, and the vehicle's position
     * at each, from which the system works out the history REQ-DRIVING-008
     * asks for.
     */
    item sample : EgoMotionSample[*] ordered;
  }

  item def RouteInput :> Route {
    doc /* The route as it enters the driving system at its input: destination, route and map, with their times. */
  }

  item def VehicleCommandOutput :> VehicleMotionCommand {
    doc /* The steering and acceleration commands as they leave the driving system for the vehicle's actuation. */
  }

  item def OperationalStateOutput :> DrivingOperationalState {
    doc /* The published plan, vehicle state and health as they leave the driving system for observation. */
  }

  port def CameraImagesInbound {
    doc /* The input port of the image item: the vehicle's cameras provide it. */
    in item cameraImages : CameraImageInput;
  }

  port def EgoMotionInbound {
    doc /* The input port of the ego-motion item: the vehicle's motion sensing provides it. */
    in item egoMotion : EgoMotionInput;
  }

  port def RouteInbound {
    doc /* The input port of the route item: navigation provides it. */
    in item route : RouteInput;
  }

  port def VehicleCommandOutbound {
    doc /* The output port of the command item: the vehicle's actuation takes it. */
    out item vehicleCommand : VehicleCommandOutput;
  }

  port def OperationalStateOutbound {
    doc /* The output port of the operational state: the state observer takes it. */
    out item operationalState : OperationalStateOutput;
  }

  part def ClosedLoopDrivingFunctionalBoundary :> ClosedLoopDrivingSystem {
    doc /*
     * The driving system at its functional boundary, the one place its
     * conceptual interfaces are stated: three input ports the context elements
     * provide and two output ports they take, each with one directed item
     * typed by an item definition of this package that specializes the item
     * of phase 2. It performs the functional flow and binds its inputs and
     * outputs to the ports. It is not a logical element: neither it nor its
     * ports names a computer, a process, a transport or a technology.
     */
    port cameraImagesIn : CameraImagesInbound;
    port egoMotionIn : EgoMotionInbound;
    port routeIn : RouteInbound;
    port vehicleCommandOut : VehicleCommandOutbound;
    port operationalStateOut : OperationalStateOutbound;

    perform closedLoopDrivingFunctionalFlow : ClosedLoopDrivingFunctionalFlow {
      in item cameraImages = cameraImagesIn.cameraImages;
      in item egoMotion = egoMotionIn.egoMotion;
      in item route = routeIn.route;
      out item vehicleCommand = vehicleCommandOut.vehicleCommand;
      out item operationalState = operationalStateOut.operationalState;
    }
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
    expose closedLoopDrivingFunctionalFlow;
    render asTreeDiagram;
  }

  view closedLoopDrivingRequirementFunctionMappingView : MVD::MatrixView {
    viewpoint selectedRequirementFunctionViewpoint : SystemRequirementTraceabilityViewpoint {
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

  /* ─────────── The loop as a process: the system and its context elements ─────────── */

  concern closedLoopDrivingProcessConcern : SystemProcessConcern {
    doc /*
     * System architects and systems engineers need the loop as a process: the
     * functions navigation, the vehicle's cameras and motion sensing, its
     * actuation and the state observer perform, which of those functions are
     * outside the scope of the driving system, what the driving system
     * provides and what it expects from each context element, and which items
     * cross its boundary in which direction. No response deadline or timing
     * claim follows from it.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder systemsEngineer : SystemsEngineer;
  }

  view closedLoopDrivingSystemProcessView : ActionFlowView {
    viewpoint selectedSystemProcessViewpoint : SystemProcessViewpoint {
      frame closedLoopDrivingProcessConcern;
    }
    expose ClosedLoopDrivingSystemProcess::*;
    expose ClosedLoopDrivingSystemProcess::navigation::*;
    expose ClosedLoopDrivingSystemProcess::vehicle::*;
    expose ClosedLoopDrivingSystemProcess::drivingSystem::*;
    expose ClosedLoopDrivingSystemProcess::stateObserver::*;
    attribute showAnnotationRows = false;
    attribute maxCompartmentEntries = 0;
  }

  /* ───────────── The modes, and the functions that depend on them ───────────── */

  concern closedLoopDrivingModeDependenceConcern : SystemStateConcern {
    doc /*
     * System architects and software developers need the modes of the
     * driving system and each function whose behavior differs by mode: what
     * CommandVehicle commands while priming, while driving and while stopped,
     * and what PublishOperationalState publishes of the stop and its cause,
     * so that the behavior of each function is designed and built per mode.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder softwareDeveloper : SoftwareDeveloper;
  }

  view closedLoopDrivingModeDependenceTableView : TVD::TableView {
    viewpoint selectedSystemStateTableViewpoint : SystemStateViewpoint {
      frame closedLoopDrivingModeDependenceConcern;
      frame degradedInputBehaviorConcern;
    }
    expose ClosedLoopDrivingModes::priming;
    expose ClosedLoopDrivingModes::driving;
    expose ClosedLoopDrivingModes::stopped;
    filter @ SysML::StateUsage;
    attribute :>> maxRowHeight = 300;
    view Mode :> columnViews {
      attribute :>> featureToRender = CT::declaredName;
    }
    view DependentFunctions :> columnViews {
      attribute :>> featureToRender = CT::documentation;
      attribute :>> columnWidth = 360;
    }
  }

  /* ─────────────── The conceptual interfaces of the system ─────────────── */

  concern closedLoopDrivingInterfaceConcern : FunctionalInterfaceConcern {
    doc /*
     * Systems engineers and software developers need the conceptual interfaces
     * of the driving system before phase 7 allocates the functions and phase 8
     * places software on them: the port of the functional chain for each item
     * that crosses its boundary, the direction of that item, and the item of
     * phase 2 the port's item specializes. Signal typing at a software
     * contract belongs to phase 8.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder softwareDeveloper : SoftwareDeveloper;
  }

  view closedLoopDrivingFunctionalInterfaceView {
    viewpoint selectedFunctionalInterfaceViewpoint : SystemInterfaceDefinitionViewpoint {
      frame closedLoopDrivingInterfaceConcern;
    }
    expose CameraImagesInbound;
    expose EgoMotionInbound;
    expose OperationalStateOutbound;
    expose RouteInbound;
    expose VehicleCommandOutbound;
    attribute showAnnotationRows = false;
    render asTreeDiagram;
  }
}
