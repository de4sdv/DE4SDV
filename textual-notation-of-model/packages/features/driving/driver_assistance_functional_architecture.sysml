/*
 * DE4SDV driver-assistance functional architecture.
 *
 * INC-DRIVING-002, phase 6: the functions of the candidate driver-assistance
 * system and the requirements of phase 5 each carries. Four functions record
 * the candidate identity, assess the vehicle ahead, request the collision
 * warning and command the vehicle. The emergency braking is a mode of the one
 * command function, not a second command source: it leaves in the driving
 * command, as the term of phase 5 allows, and whether the candidate's braking
 * can stand for the common capability stays open
 * (gapNoSeparateEmergencyFunction). Every requirement but REQ-DRIVING-038 and
 * REQ-DRIVING-043 is allocated to a function. Those two constrain how the
 * driving command and the warning request travel to the actuation and to the
 * AAOS SDV, over the Eclipse S-CORE path, not what a function does: phase 8
 * carries them by the elements it places on those exchanges
 * (gapScoreIntegration). An allocation assigns responsibility only
 * (allocatedTo); it asserts no satisfaction. No logical element, platform,
 * transport or technology is chosen, and no safety claim is made.
 *
 * The system in operation is a process, not a second architecture: the
 * vehicle's front camera and motion sensing give the image and the speed, the
 * command and warning path carries the driving command to the vehicle's
 * actuation and the warning request to the warning presentation, which gives
 * the driver the collision warning on the display and as a sound. Those are
 * functions of the context elements, outside the scope of the system, and
 * DriverAssistanceSystemProcess runs the system as one action between them,
 * with the times between the warning request, each mode of the warning and
 * the start of the emergency braking. Its participants are the parts of the
 * one operational context of phase 2, bound by reference. The functions whose
 * behavior differs by mode depend on the modes of DriverAssistanceModes, and
 * the conceptual interfaces of the system are the ports of
 * DriverAssistanceFunctionalBoundary, whose items specialize the items of
 * phase 2. No vehicle signal specification is imported or used anywhere in
 * this package: the interface items are conceptual, their quantities are ISQ
 * quantity values, and the signal typing of an interface starts in phase 8.
 * The functions state what the system has to do, not what the candidate does
 * at its inspected revision; phase 8 maps them to its software.
 */

package DE4SDV_DriverAssistanceFunctionalArchitecture {
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_TraceVocabulary::AllocatableFunction;
  private import DE4SDV_DriverAssistanceFraming::driverWarningSequenceConcern;
  private import DE4SDV_DriverAssistanceFraming::DriverAssistanceSystem;
  private import DE4SDV_OperationalContext::SubjectVehicle;
  private import DE4SDV_OperationalContext::Driver;
  private import DE4SDV_DriverAssistanceOperationalContext::FrontCameraImage;
  private import DE4SDV_DriverAssistanceOperationalContext::VehicleSpeed;
  private import DE4SDV_DriverAssistanceOperationalContext::DrivingCommand;
  private import DE4SDV_DriverAssistanceOperationalContext::WarningRequest;
  private import DE4SDV_DriverAssistanceOperationalContext::CollisionWarning;
  private import DE4SDV_DriverAssistanceOperationalContext::SCORECommandAndWarningPath;
  private import DE4SDV_DriverAssistanceOperationalContext::DriverWarningPresentation;
  private import DE4SDV_DriverAssistanceOperationalContext::driverAssistanceOperationalContext;
  private import DE4SDV_DriverAssistanceNeedsRequirements::*;
  private import ScalarValues::Boolean;
  private import ScalarValues::Natural;
  private import SAF_Viewpoints::*;
  private import StandardViewDefinitions::*;
  private import SysideViews::**;
  private import Views::*;

  /* ──────────── Items the functions exchange inside the driver-assistance system ──────────── */

  item def VehicleAheadAssessment {
    doc /*
     * For one front-camera image: whether a vehicle ahead is in the lane of
     * the vehicle, the distance to it in the direction of travel, the speed at
     * which the vehicle closes on it, the time to collision, which has no value
     * while the vehicle does not close on it, the needed deceleration, and
     * whether a collision is imminent, each as the terms of the requirements
     * define it.
     */
  }

  item def WarningRequestState {
    doc /* Whether the warning request has started, and its start time in simulation time. */
  }

  item def CandidateIdentityRecord {
    doc /* The candidate identity of the run, as the terms of the requirements define it, recorded before its first driving command. */
  }

  /* ──────────────── The functions of the context elements of phase 2 ──────────────── */

  action def DriverAssistanceContextFunction {
    doc /*
     * A behavior of a context element of phase 2 while the driver-assistance
     * system operates. It is outside the scope of the driver-assistance
     * system: the system does not provide it and no requirement of phase 5 is
     * allocated to it.
     */
  }

  action def CaptureFrontCameraImage :> DriverAssistanceContextFunction {
    doc /* The vehicle's front camera: captures the road ahead, its lanes and the vehicles in them, and gives the image with its capture time. */
    out frontCameraImage : FrontCameraImage;
  }

  action def SampleVehicleSpeed :> DriverAssistanceContextFunction {
    doc /* The vehicle's motion sensing: samples the speed of the vehicle and gives it with its sample time. */
    out vehicleSpeed : VehicleSpeed;
  }

  action def CarryDrivingCommand :> DriverAssistanceContextFunction {
    doc /* The command and warning path: carries each driving command from the boundary of the system to the actuation of the vehicle, with no exchange beside it. */
    in drivingCommand : DrivingCommand;
    out carriedCommand : DrivingCommand;
  }

  action def CarryWarningRequest :> DriverAssistanceContextFunction {
    doc /* The command and warning path: carries the warning request from the boundary of the system to the warning presentation, with no exchange beside it. */
    in warningRequest : WarningRequest;
    out carriedWarningRequest : WarningRequest;
  }

  action def ActuateVehicle :> DriverAssistanceContextFunction {
    doc /*
     * The vehicle's actuation: applies the steering and the acceleration of
     * each driving command that reaches it, braking included, which moves the
     * vehicle and changes what its front camera sees next. By its form it can
     * detect a command lost, delayed, repeated or corrupted on the path;
     * rejecting what it detects is the share of the product that holds the
     * path (REQ-MW-006), which phases 7 and 8 allocate.
     */
    in drivingCommand : DrivingCommand;
  }

  action def ShowCollisionWarning :> DriverAssistanceContextFunction {
    doc /*
     * The warning presentation: gives the driver the collision warning on the
     * display, starting within 0.2 s of wall-clock time after the warning
     * request starts at the boundary of the system, the time on the path
     * included.
     */
    in warningRequest : WarningRequest;
    out collisionWarning : CollisionWarning;
  }

  action def SoundCollisionWarning :> DriverAssistanceContextFunction {
    doc /*
     * The warning presentation: gives the driver the collision warning as a
     * sound, starting within 0.2 s of wall-clock time after the warning
     * request starts at the boundary of the system, the time on the path
     * included.
     */
    in warningRequest : WarningRequest;
    out collisionWarning : CollisionWarning;
  }

  action def ReceiveCollisionWarning :> DriverAssistanceContextFunction {
    doc /* The driver: gets the collision warning on the display and as a sound, and sends nothing back to the system. */
    in shownWarning : CollisionWarning;
    in soundedWarning : CollisionWarning;
  }

  /* ─────────────────────────────── Functions ─────────────────────────────── */

  action def IdentifyCandidate :> AllocatableFunction {
    doc /*
     * Before the first driving command of each run, records the candidate
     * identity: the upstream revision, the difference between the source of
     * the system and that revision, the SHA-256 of each network file the
     * system loads and of each file of its configuration, and the settings of
     * its launch, verbatim.
     */
    out candidateRecord : CandidateIdentityRecord;
  }

  action def AssessVehicleAhead :> AllocatableFunction {
    doc /*
     * Perceives from the front-camera image the lane of the vehicle and the
     * closest vehicle ahead in it, and estimates, with the speed of the
     * vehicle, the distance to that vehicle in the direction of travel and the
     * speed at which the vehicle closes on it. From them it works out the time
     * to collision and the needed deceleration, and whether a collision is
     * imminent: a time to collision of at most 4.0 s and a needed deceleration
     * of at least 1.0 m/s².
     */
    in frontCameraImage : FrontCameraImage;
    in vehicleSpeed : VehicleSpeed;
    out assessment : VehicleAheadAssessment;
  }

  action def RequestCollisionWarning :> AllocatableFunction {
    doc /*
     * Starts the warning request at the boundary of the system when a
     * collision with a vehicle ahead becomes imminent, and starts none while
     * no collision is imminent; a request may go on after the imminence ends,
     * as when the braking ends it. Starting with the imminence puts the
     * request ahead of the emergency braking, which starts only once the
     * needed deceleration reaches 5.0 m/s²: in each setting at a constant
     * approach speed the two are at least 1.11 s apart. Reports whether the
     * request has started, and when, to the command of the vehicle.
     */
    in assessment : VehicleAheadAssessment;
    out warningRequest : WarningRequest;
    out warningState : WarningRequestState;
  }

  action def GiveDrivingCommand :> AllocatableFunction {
    doc /*
     * Gives the one driving command of the system, the steering and the
     * acceleration, from the assessment of the vehicle ahead and the speed of
     * the vehicle. It gives none before the candidate identity is recorded.
     * Until an emergency braking starts, it follows the lane and keeps the
     * speed and the distance to the vehicle ahead, braking included, with a
     * deceleration below 5.0 m/s². It starts the emergency braking, a command
     * for 5.0 m/s² or more, only while a collision is imminent and only after
     * the warning request has started, and commands at least 5.0 m/s² while
     * the needed deceleration is at least 5.0 m/s². When a collision is
     * imminent it brakes the vehicle to a relative impact speed of at most the
     * maximum relative impact speed for the relative approach speed. It gives
     * each command with its issue time, a sequence count and a check value,
     * the form by which the actuation can detect its loss, delay, repetition
     * or corruption on the path.
     */
    in assessment : VehicleAheadAssessment;
    in currentSpeed : VehicleSpeed;
    in warningState : WarningRequestState;
    in candidateRecord : CandidateIdentityRecord;
    out drivingCommand : DrivingCommand;
  }

  /* ─────────────────── The functional breakdown of one step ─────────────────── */

  action def DriverAssistanceFunctionalFlow {
    doc /*
     * The driver-assistance system broken into its functions, and the items
     * they exchange in one step. The front-camera image and the vehicle speed
     * come from the context of phase 2; the driving command and the warning
     * request go to the command and warning path, which takes them to the
     * actuation of the vehicle and to the warning presentation. Only the
     * command of commandVehicle leaves as the driving command, and only the
     * request of requestWarning as the warning request.
     */
    in item frontCameraImage : FrontCameraImage;
    in item vehicleSpeed : VehicleSpeed;
    out item drivingCommand : DrivingCommand;
    out item warningRequest : WarningRequest;

    action identifyCandidate : IdentifyCandidate {
      out candidateRecord;
    }

    action assessVehicleAhead : AssessVehicleAhead {
      in frontCameraImage = DriverAssistanceFunctionalFlow::frontCameraImage;
      in vehicleSpeed = DriverAssistanceFunctionalFlow::vehicleSpeed;
      out assessment;
    }

    action requestWarning : RequestCollisionWarning {
      in assessment;
      out warningRequest = DriverAssistanceFunctionalFlow::warningRequest;
      out warningState;
    }
    flow from assessVehicleAhead.assessment to requestWarning.assessment;
    first assessVehicleAhead then requestWarning;

    action commandVehicle : GiveDrivingCommand {
      in assessment;
      in currentSpeed = DriverAssistanceFunctionalFlow::vehicleSpeed;
      in warningState;
      in candidateRecord;
      out drivingCommand = DriverAssistanceFunctionalFlow::drivingCommand;
    }
    flow from assessVehicleAhead.assessment to commandVehicle.assessment;
    flow from requestWarning.warningState to commandVehicle.warningState;
    flow from identifyCandidate.candidateRecord to commandVehicle.candidateRecord;
    first requestWarning then commandVehicle;
  }

  action driverAssistanceFunctionalFlow : DriverAssistanceFunctionalFlow;

  /* ─────────── The system process: the system between the context elements ─────────── */

  action def DriverAssistanceSystemProcess {
    doc /*
     * One cycle of the driver-assistance system in operation, as a process.
     * The participants are the context parts of phase 2 themselves and the
     * system of interest, bound by reference: the process declares no part of
     * its own, so the increment has one context. Each participant owns and
     * performs its functions, as the swim lane of its functions: the vehicle's
     * front camera and motion sensing give the image and the speed, the
     * system assesses, warns and commands as one action of the process, and
     * the command and warning path carries the driving command to the
     * vehicle's actuation and the warning request to the warning
     * presentation, which gives the driver the collision warning on the
     * display and as a sound. The functions of the context elements are
     * outside the scope of the driver-assistance system; its functional scope
     * is the one functional flow usage it performs. The items that cross its
     * boundary are the flows of the process, each chained through the
     * participant that gives and the one that takes, and nothing flows back
     * from the driver. The sequence and its times: the system gives its
     * warning request at its boundary at least 1.0 s of simulation time
     * before the start of its emergency braking, which leaves in its driving
     * command (REQ-DRIVING-042); within that lead, the path and the warning
     * presentation start each mode of the warning within 0.2 s of wall-clock
     * time after the request, so that each mode starts at least 0.8 s before
     * the emergency braking while the simulation runs no faster than
     * wall-clock time, which is the obligation of System 2. Phases 7 and 8
     * divide the 0.2 s between the path and the warning presentation. No
     * transport, display or sound technology is fixed here.
     */
    ref part vehicle : SubjectVehicle = driverAssistanceOperationalContext::vehicle {
      doc /* The vehicle of phase 2: its front camera and motion sensing give the input, and its actuation applies the driving command. */
      perform action captureImage : CaptureFrontCameraImage;
      perform action sampleSpeed : SampleVehicleSpeed;
      perform action actuateVehicle : ActuateVehicle;
    }

    ref part candidateSystem : DriverAssistanceSystem = driverAssistanceOperationalContext::candidateSystem {
      doc /* The system of interest of phase 2: it performs its whole functional flow, the one usage its functional boundary performs, and gives its warning request at least 1.0 s of simulation time before the start of its emergency braking. */
      perform driverAssistanceFunctionalFlow;
    }

    ref part scorePath : SCORECommandAndWarningPath = driverAssistanceOperationalContext::scorePath {
      doc /* The command and warning path of phase 2: it carries the driving command to the actuation and the warning request to the warning presentation, with no exchange beside it. */
      perform action carryCommand : CarryDrivingCommand;
      perform action carryWarningRequest : CarryWarningRequest;
    }

    ref part warningPresentation : DriverWarningPresentation = driverAssistanceOperationalContext::aaosSDVGuest::warningPresentation {
      doc /* The warning presentation of phase 2: it starts each mode of the warning, on the display and as a sound, within 0.2 s of wall-clock time after the request, the time on the path included, and sends nothing to the system. */
      perform action showWarning : ShowCollisionWarning;
      perform action soundWarning : SoundCollisionWarning;
    }

    ref part driver : Driver = driverAssistanceOperationalContext::driver {
      doc /* The driver of phase 2: gets the collision warning; nothing flows back to the system. */
      perform action receiveWarning : ReceiveCollisionWarning;
    }

    flow from vehicle.captureImage.frontCameraImage to candidateSystem.driverAssistanceFunctionalFlow.frontCameraImage;
    flow from vehicle.sampleSpeed.vehicleSpeed to candidateSystem.driverAssistanceFunctionalFlow.vehicleSpeed;
    flow from candidateSystem.driverAssistanceFunctionalFlow.drivingCommand to scorePath.carryCommand.drivingCommand;
    flow from candidateSystem.driverAssistanceFunctionalFlow.warningRequest to scorePath.carryWarningRequest.warningRequest;
    flow from scorePath.carryCommand.carriedCommand to vehicle.actuateVehicle.drivingCommand;
    flow from scorePath.carryWarningRequest.carriedWarningRequest to warningPresentation.showWarning.warningRequest;
    flow from scorePath.carryWarningRequest.carriedWarningRequest to warningPresentation.soundWarning.warningRequest;
    flow from warningPresentation.showWarning.collisionWarning to driver.receiveWarning.shownWarning;
    flow from warningPresentation.soundWarning.collisionWarning to driver.receiveWarning.soundedWarning;
  }

  action driverAssistanceSystemProcess : DriverAssistanceSystemProcess;

  /* ────────────────────────────────── Modes ────────────────────────────────── */

  state def DriverAssistanceModes {
    doc /*
     * The modes of the driver-assistance system. Identifying holds every
     * driving command until the candidate identity is recorded; assisting
     * follows the lane and the speed with no collision imminent; warning is
     * the imminence of a collision before an emergency braking, with the
     * warning request given; emergency braking holds a deceleration of at
     * least 5.0 m/s² while the needed deceleration is at least 5.0 m/s², until
     * the collision is no longer imminent. The modes follow from the
     * requirements, not from a term of phase 5.
     */
    state identifying {
      doc /* The candidate identity of the run is not yet recorded: commandVehicle gives no driving command (REQ-DRIVING-044). */
    }
    state assisting {
      doc /*
       * No collision with a vehicle ahead is imminent: requestWarning starts no
       * warning request (REQ-DRIVING-040), and commandVehicle follows the lane
       * and keeps the speed and the distance to the vehicle ahead with a
       * deceleration below 5.0 m/s² and starts no emergency braking
       * (REQ-DRIVING-041).
       */
    }
    state warning {
      doc /*
       * A collision with a vehicle ahead is imminent and no emergency braking
       * has started: requestWarning gives the warning request from the start
       * of the imminence (REQ-DRIVING-042), and commandVehicle starts the
       * emergency braking once the needed deceleration reaches 5.0 m/s², after
       * the request has started.
       */
    }
    state emergencyBraking {
      doc /*
       * From the first command for 5.0 m/s² or more until the collision is no
       * longer imminent: commandVehicle commands a deceleration of at least 5.0
       * m/s² while the needed deceleration is at least 5.0 m/s²
       * (REQ-DRIVING-036), and brakes the vehicle to a relative impact speed of
       * at most the maximum relative impact speed for the relative approach
       * speed (REQ-DRIVING-037).
       */
    }
    transition first identifying then assisting;       // the candidate identity is recorded
    transition first assisting then warning;           // a collision with a vehicle ahead becomes imminent
    transition first warning then emergencyBraking;    // the needed deceleration reaches 5.0 m/s²
    transition first warning then assisting;           // the collision is no longer imminent
    transition first emergencyBraking then assisting;  // the collision is no longer imminent
  }

  /* ────────── The functions whose behavior differs by mode depend on it ────────── */

  dependency commandVehicleDependsOnIdentifyingMode
    from DriverAssistanceFunctionalFlow::commandVehicle
    to DriverAssistanceModes::identifying;
  dependency commandVehicleDependsOnAssistingMode
    from DriverAssistanceFunctionalFlow::commandVehicle
    to DriverAssistanceModes::assisting;
  dependency commandVehicleDependsOnWarningMode
    from DriverAssistanceFunctionalFlow::commandVehicle
    to DriverAssistanceModes::warning;
  dependency commandVehicleDependsOnEmergencyBrakingMode
    from DriverAssistanceFunctionalFlow::commandVehicle
    to DriverAssistanceModes::emergencyBraking;
  dependency requestWarningDependsOnAssistingMode
    from DriverAssistanceFunctionalFlow::requestWarning
    to DriverAssistanceModes::assisting;
  dependency requestWarningDependsOnWarningMode
    from DriverAssistanceFunctionalFlow::requestWarning
    to DriverAssistanceModes::warning;

  /* ────────── The conceptual interfaces of the system: one functional chain ────────── */

  item def FrontCameraImageInput :> FrontCameraImage {
    doc /*
     * The front-camera image as it enters the driver-assistance system at its
     * input, with its capture time in simulation time. The calibration of the
     * camera, its intrinsic matrix and its pose in the vehicle frame, travels
     * with its images: the distance to the vehicle ahead is estimated with it,
     * and the system builds no calibration of its own.
     */
    attribute captureTime : ISQ::DurationValue;
  }

  item def VehicleSpeedInput :> VehicleSpeed {
    doc /* The speed of the vehicle as it enters the system at its input, with its sample time in simulation time. */
    attribute speed : ISQ::SpeedValue;
    attribute sampleTime : ISQ::DurationValue;
  }

  item def DrivingCommandOutput :> DrivingCommand {
    doc /*
     * The driving command as it leaves the system at its boundary: the
     * steering angle and the acceleration, a braking as a negative
     * acceleration, with the three parts by which the actuation can detect a
     * failure of the path (REQ-DRIVING-039): its issue time in simulation
     * time, by which a delay shows; a sequence count, one more than that of
     * the command before it, by which a loss or a repetition shows; and a
     * check value over the other parts, by which a corruption shows.
     */
    attribute steeringAngle : ISQ::AngularMeasureValue;
    attribute acceleration : ISQ::AccelerationValue;
    attribute issueTime : ISQ::DurationValue;
    attribute sequenceCount : Natural;
    attribute checkValue : Natural;
  }

  item def CollisionWarningRequestOutput :> WarningRequest {
    doc /*
     * The warning request as it leaves the system at its boundary: whether it
     * asks for the collision warning, with its issue time in simulation time.
     * A request starts when it begins to ask.
     */
    attribute requested : Boolean;
    attribute issueTime : ISQ::DurationValue;
  }

  port def FrontCameraImageInbound {
    doc /* The input port of the front-camera image: the vehicle's front camera provides it. */
    in item frontCameraImage : FrontCameraImageInput;
  }

  port def VehicleSpeedInbound {
    doc /* The input port of the vehicle speed: the vehicle's motion sensing provides it. */
    in item vehicleSpeed : VehicleSpeedInput;
  }

  port def DrivingCommandOutbound {
    doc /* The output port of the driving command: the command and warning path takes it to the actuation. */
    out item drivingCommand : DrivingCommandOutput;
  }

  port def WarningRequestOutbound {
    doc /* The output port of the warning request: the command and warning path takes it to the warning presentation. */
    out item warningRequest : CollisionWarningRequestOutput;
  }

  part def DriverAssistanceFunctionalBoundary :> DriverAssistanceSystem {
    doc /*
     * The driver-assistance system at its functional boundary, the one place
     * its conceptual interfaces are stated: two input ports the vehicle
     * provides and two output ports the command and warning path takes, each
     * with one directed item typed by an item definition of this package that
     * specializes the item of phase 2. It performs the functional flow and
     * binds its inputs and outputs to the ports. It is not a logical element:
     * neither it nor its ports names a computer, a process, a transport or a
     * technology.
     */
    port frontCameraImageIn : FrontCameraImageInbound;
    port vehicleSpeedIn : VehicleSpeedInbound;
    port drivingCommandOut : DrivingCommandOutbound;
    port warningRequestOut : WarningRequestOutbound;

    perform driverAssistanceFunctionalFlow : DriverAssistanceFunctionalFlow {
      in item frontCameraImage = frontCameraImageIn.frontCameraImage;
      in item vehicleSpeed = vehicleSpeedIn.vehicleSpeed;
      out item drivingCommand = drivingCommandOut.drivingCommand;
      out item warningRequest = warningRequestOut.warningRequest;
    }
  }

  /* ─────────────── Requirement-to-function allocations (allocatedTo) ─────────────── */

  /* Recording the candidate identity. */
  allocation candidateIdentityRecordResponsibility
    allocate reqRecordCandidateIdentity to DriverAssistanceFunctionalFlow::identifyCandidate;

  /* Assessing the vehicle ahead: the needed deceleration and the imminence. */
  allocation neededDecelerationResponsibility
    allocate reqEmergencyBrakingForImminentCollision to DriverAssistanceFunctionalFlow::assessVehicleAhead;
  allocation warningImminenceResponsibility
    allocate reqWithholdWarningRequest to DriverAssistanceFunctionalFlow::assessVehicleAhead;
  allocation brakingImminenceResponsibility
    allocate reqWithholdEmergencyBraking to DriverAssistanceFunctionalFlow::assessVehicleAhead;

  /* Requesting the collision warning. */
  allocation warningStartResponsibility
    allocate reqWithholdWarningRequest to DriverAssistanceFunctionalFlow::requestWarning;
  allocation warningLeadResponsibility
    allocate reqWarningRequestBeforeEmergencyBraking to DriverAssistanceFunctionalFlow::requestWarning;

  /* Commanding the vehicle, the emergency braking included. */
  allocation emergencyBrakingDemandResponsibility
    allocate reqEmergencyBrakingForImminentCollision to DriverAssistanceFunctionalFlow::commandVehicle;
  allocation impactSpeedResponsibility
    allocate reqImpactSpeedWithinLimit to DriverAssistanceFunctionalFlow::commandVehicle;
  allocation detectableCommandResponsibility
    allocate reqDetectableDrivingCommand to DriverAssistanceFunctionalFlow::commandVehicle;
  allocation emergencyBrakingStartResponsibility
    allocate reqWithholdEmergencyBraking to DriverAssistanceFunctionalFlow::commandVehicle;
  allocation brakingAfterWarningResponsibility
    allocate reqWarningRequestBeforeEmergencyBraking to DriverAssistanceFunctionalFlow::commandVehicle;
  allocation commandAfterIdentityResponsibility
    allocate reqRecordCandidateIdentity to DriverAssistanceFunctionalFlow::commandVehicle;

  /* ─────────────────────────────── Views ─────────────────────────────── */

  concern driverAssistanceFunctionsConcern : FunctionalBehaviorConcern {
    doc /*
     * System architects and verification engineers need the functions of the
     * driver-assistance system and each requirement of phase 5 mapped to the
     * functions that carry it: phase 7 gives the functions to logical
     * elements, and phase 10 verifies each requirement on its functions.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder verificationEngineer : VerificationEngineer;
  }

  view driverAssistanceFunctionBreakdownView {
    viewpoint selectedFunctionalBreakdownViewpoint : SystemFunctionalBreakdownStructureViewpoint {
      frame driverAssistanceFunctionsConcern;
    }
    expose driverAssistanceFunctionalFlow;
    render asTreeDiagram;
  }

  view driverAssistanceRequirementFunctionMappingView : MVD::MatrixView {
    viewpoint selectedRequirementFunctionViewpoint : SystemRequirementTraceabilityViewpoint {
      frame driverAssistanceFunctionsConcern;
    }
    view :>> rowView {
      expose reqEmergencyBrakingForImminentCollision;
      expose reqImpactSpeedWithinLimit;
      expose reqDrivingCommandOverSCORE;
      expose reqDetectableDrivingCommand;
      expose reqWithholdWarningRequest;
      expose reqWithholdEmergencyBraking;
      expose reqWarningRequestBeforeEmergencyBraking;
      expose reqWarningRequestOverSCORE;
      expose reqRecordCandidateIdentity;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> columnView {
      expose driverAssistanceFunctionalFlow::identifyCandidate;
      expose driverAssistanceFunctionalFlow::assessVehicleAhead;
      expose driverAssistanceFunctionalFlow::requestWarning;
      expose driverAssistanceFunctionalFlow::commandVehicle;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> cellView {
      expose DE4SDV_DriverAssistanceFunctionalArchitecture::*;
      attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;
    }
  }

  /* ─────────── The system in operation as a process, with the warning sequence ─────────── */

  concern driverAssistanceProcessConcern : SystemProcessConcern {
    doc /*
     * System architects and systems engineers need the driver-assistance
     * system in operation as a process: the functions that the vehicle, the
     * command and warning path, the warning presentation and the driver
     * perform, which of those functions are outside the scope of the system,
     * what the system provides and what it expects from each context element,
     * and which items cross its boundary in which direction.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder systemsEngineer : SystemsEngineer;
  }

  view driverAssistanceSystemProcessView : ActionFlowView {
    viewpoint selectedSystemProcessViewpoint : SystemProcessViewpoint {
      frame driverAssistanceProcessConcern;
      frame driverWarningSequenceConcern;
    }
    expose DriverAssistanceSystemProcess::*;
    expose DriverAssistanceSystemProcess::vehicle::*;
    expose DriverAssistanceSystemProcess::candidateSystem::*;
    expose DriverAssistanceSystemProcess::scorePath::*;
    expose DriverAssistanceSystemProcess::warningPresentation::*;
    expose DriverAssistanceSystemProcess::driver::*;
    attribute showAnnotationRows = false;
    attribute maxCompartmentEntries = 0;
  }

  /* ───────────── The modes, and the functions that depend on them ───────────── */

  concern driverAssistanceModeDependenceConcern : SystemStateConcern {
    doc /*
     * System architects and software developers need the modes of the
     * driver-assistance system and each function whose behavior differs by
     * mode: what commandVehicle commands before the candidate identity is
     * recorded, while assisting, while a collision is imminent and in an
     * emergency braking, and when requestWarning starts its request, so that
     * the behavior of each function is designed and built per mode.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder softwareDeveloper : SoftwareDeveloper;
  }

  view driverAssistanceModeDependenceTableView : TVD::TableView {
    viewpoint selectedSystemStateTableViewpoint : SystemStateViewpoint {
      frame driverAssistanceModeDependenceConcern;
    }
    expose DriverAssistanceModes::identifying;
    expose DriverAssistanceModes::assisting;
    expose DriverAssistanceModes::warning;
    expose DriverAssistanceModes::emergencyBraking;
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

  concern driverAssistanceInterfaceConcern : FunctionalInterfaceConcern {
    doc /*
     * Systems engineers and software developers need the conceptual interfaces
     * of the driver-assistance system before phase 7 allocates the functions
     * and phase 8 places software on them: the port of the functional chain
     * for each item that crosses its boundary, the direction of that item, the
     * item of phase 2 the port's item specializes, and the parts of the
     * driving command by which the actuation detects a failure of the path.
     * Signal typing at a software contract belongs to phase 8.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder softwareDeveloper : SoftwareDeveloper;
  }

  view driverAssistanceFunctionalInterfaceView {
    viewpoint selectedFunctionalInterfaceViewpoint : SystemInterfaceDefinitionViewpoint {
      frame driverAssistanceInterfaceConcern;
    }
    expose DrivingCommandOutbound;
    expose FrontCameraImageInbound;
    expose VehicleSpeedInbound;
    expose WarningRequestOutbound;
    attribute showAnnotationRows = false;
    render asTreeDiagram;
  }
}
