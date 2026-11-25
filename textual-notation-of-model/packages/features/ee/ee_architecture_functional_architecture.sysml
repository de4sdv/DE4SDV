/*
 * DE4SDV E/E architecture functional architecture.
 *
 * INC-EE-001, phase 6: the functions of the vehicle network and the
 * requirements of phase 5 each carries. Five functions record the network
 * identity, take the driving command at the boundary interface, carry it
 * to the actuation ECU, check it, apply it at the actuation ECU, and give
 * the stop response when no valid driving command reaches the actuation
 * ECU for more than 200 ms of simulation time. Eight requirements are
 * allocated to the functions. The two left constrain the structure that
 * realizes the functions, not what a function does: REQ-EE-001 holds both
 * routes in one topology, and REQ-EE-003 keeps the commands of a run on
 * the elements of its route. Phases 7 and 8 carry them by the elements
 * that they place; the inspection of the realization that phase 8
 * records, and of the configuration of each run, verifies REQ-EE-001, and
 * the records of the runs verify REQ-EE-003. An allocation assigns
 * responsibility only (allocatedTo); it asserts no satisfaction. No
 * logical element, element of a route, transport or technology is chosen,
 * and no safety claim is made.
 *
 * The functions do not depend on the route: a run takes one route, and
 * which elements carry a command on it is for the architecture phases.
 * The stop response is given at the actuation ECU, the last element that
 * a command reaches, by the function that applies the valid driving
 * commands, on the same output: it is a state of that function, not a
 * second source of commands. Which element checks a command, and where
 * each element takes the simulation time, are left to phases 7 and 8;
 * every time here counts on the one clock of the virtual vehicle that the
 * testbed gives every element.
 *
 * The vehicle network in operation is a process, not a second
 * architecture: the command source gives the driving command, the Eclipse
 * S-CORE path hands it to the vehicle network at the boundary interface,
 * and the vehicle moves by what the actuation ECU gives it. Those are
 * functions of the context elements, outside the scope of the vehicle
 * network, and EEVehicleNetworkSystemProcess runs the network as one
 * action between them, with the sequence from a fault to the stop
 * response. Its participants are the parts of the one operational context
 * of phase 2, bound by reference. The function whose behavior differs by
 * state depends on the states of EEActuationStates, and the conceptual
 * interfaces of the network are the ports of
 * EEVehicleNetworkFunctionalBoundary, whose items specialize the driving
 * command of phase 2 and the item that the driver-assistance increment
 * defines for it. No vehicle signal specification is imported or used
 * anywhere in this package: the interface items are conceptual, their
 * quantities are ISQ quantity values, and the signal typing of an
 * interface starts in phase 8.
 */

package DE4SDV_EEArchitectureFunctionalArchitecture {
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_TraceVocabulary::AllocatableFunction;
  private import DE4SDV_EEArchitectureFraming::EEVehicleNetworkSystem;
  private import DE4SDV_EEArchitectureFraming::eeNetworkFaultResponseConcern;
  private import DE4SDV_EEArchitectureOperationalContext::DrivingCommandSource;
  private import DE4SDV_EEArchitectureOperationalContext::eeArchitectureOperationalContext;
  private import DE4SDV_DriverAssistanceOperationalContext::DrivingCommand;
  private import DE4SDV_DriverAssistanceOperationalContext::SCORECommandAndWarningPath;
  private import DE4SDV_OperationalContext::SubjectVehicle;
  private import DE4SDV_DriverAssistanceFunctionalArchitecture::DrivingCommandOutput;
  private import DE4SDV_EEArchitectureNeedsRequirements::*;
  private import SAF_Viewpoints::*;
  private import StandardViewDefinitions::*;
  private import SysideViews::**;
  private import Views::*;

  /* The item the functions exchange inside the vehicle network */

  item def EENetworkIdentityRecord {
    doc /*
     * The record of the network identity of one run, by the term network
     * identity, made before the vehicle network takes the first driving
     * command of the run.
     */
  }

  /* The functions of the context elements of phase 2 */

  action def EEContextFunction {
    doc /*
     * A behavior of a context element of phase 2 while the vehicle network
     * operates. It is outside the scope of the vehicle network: the network
     * does not provide it and no requirement of phase 5 is allocated to it.
     */
  }

  action def EEGiveDrivingCommand :> EEContextFunction {
    doc /*
     * The command source: gives each driving command, in this increment the
     * command of the driver-assistance candidate with its detection parts.
     */
    out drivingCommand : DrivingCommand;
  }

  action def EECarryCommandOverSCORE :> EEContextFunction {
    doc /*
     * The Eclipse S-CORE path: hands each driving command to the vehicle
     * network at the boundary interface, with no exchange beside it.
     */
    in drivingCommand : DrivingCommand;
    out carriedCommand : DrivingCommand;
  }

  action def EEMoveVehicle :> EEContextFunction {
    doc /*
     * The vehicle: steering, acceleration and brakes move it by what the
     * actuation ECU gives it; nothing flows back to the vehicle network.
     */
    in appliedCommand : DrivingCommand;
  }

  /* Functions */

  action def EERecordNetworkIdentity :> AllocatableFunction {
    doc /*
     * Records the network identity of the vehicle network before it takes the
     * first driving command of each run, so that each verdict binds the
     * route, the commit with its difference, the configuration and the
     * settings that ran.
     */
    out identityRecord : EENetworkIdentityRecord;
  }

  action def EETakeDrivingCommand :> AllocatableFunction {
    doc /*
     * Takes each driving command at the boundary interface as the Eclipse
     * S-CORE path gives it there, at the simulation time at which the path
     * gives it, and takes driving commands from nowhere else.
     */
    in drivingCommand : DrivingCommand;
    out takenCommand : DrivingCommand;
  }

  action def EECarryDrivingCommand :> AllocatableFunction {
    doc /*
     * Carries each driving command taken at the boundary interface to the
     * actuation ECU, once, in its order and with each part as the path gave
     * it, and hands its detection parts on as it received them, computing
     * none of them anew. In a run without a fault each command reaches the
     * actuation ECU within 50 ms of simulation time after it is taken. Around
     * a fault it goes on carrying each command that the fault does not
     * affect.
     */
    in takenCommand : DrivingCommand;
    out carriedCommand : DrivingCommand;
  }

  action def EECheckDrivingCommand :> AllocatableFunction {
    doc /*
     * Decides, by the term valid driving command, whether each driving
     * command that reaches the actuation ECU is valid: its check value, its
     * sequence count against the reference count, and its issue time against
     * the simulation time at which it reaches the actuation ECU. It passes
     * each valid command on to be applied, and nothing in place of an invalid
     * one.
     */
    in carriedCommand : DrivingCommand;
    out validCommand : DrivingCommand;
  }

  action def EEApplyDrivingCommand :> AllocatableFunction {
    doc /*
     * Applies each valid driving command at the actuation ECU when it reaches
     * it, and gives the vehicle the steering angle and the acceleration of
     * the last valid command that it applied, and nothing before the first.
     * Once more than 200 ms of simulation time pass with no valid driving
     * command reaching the actuation ECU, counted from the last one or from
     * the start of the run when none did, it applies no driving command that
     * reaches it after that, and gives the vehicle the stop response on the
     * same output, from no later than 300 ms of simulation time after that
     * last valid command or the start of the run until the run ends.
     */
    in validCommand : DrivingCommand;
    out appliedCommand : DrivingCommand;
  }

  /* The functional breakdown of the vehicle network */

  action def EEVehicleNetworkFunctionalFlow {
    doc /*
     * The vehicle network broken into its functions, and the items they
     * exchange. The driving command comes from the Eclipse S-CORE path at the
     * boundary interface, and what the actuation ECU gives goes to the
     * vehicle: the steering angle and the acceleration of the last valid
     * driving command, or the stop response. Only what applyDrivingCommand
     * gives leaves the network. The network identity is recorded before the
     * network takes the first driving command of each run.
     */
    in item drivingCommand : DrivingCommand;
    out item appliedCommand : DrivingCommand;

    action recordNetworkIdentity : EERecordNetworkIdentity {
      out identityRecord;
    }

    action takeDrivingCommand : EETakeDrivingCommand {
      in drivingCommand = EEVehicleNetworkFunctionalFlow::drivingCommand;
      out takenCommand;
    }
    first recordNetworkIdentity then takeDrivingCommand;

    action carryDrivingCommand : EECarryDrivingCommand {
      in takenCommand;
      out carriedCommand;
    }
    flow from takeDrivingCommand.takenCommand to carryDrivingCommand.takenCommand;

    action checkDrivingCommand : EECheckDrivingCommand {
      in carriedCommand;
      out validCommand;
    }
    flow from carryDrivingCommand.carriedCommand to checkDrivingCommand.carriedCommand;

    action applyDrivingCommand : EEApplyDrivingCommand {
      in validCommand;
      out appliedCommand = EEVehicleNetworkFunctionalFlow::appliedCommand;
    }
    flow from checkDrivingCommand.validCommand to applyDrivingCommand.validCommand;
  }

  action eeVehicleNetworkFunctionalFlow : EEVehicleNetworkFunctionalFlow;

  /* The system process: the vehicle network between the context elements */

  action def EEVehicleNetworkSystemProcess {
    doc /*
     * One run of the vehicle network in operation, as a process. The
     * participants are the context parts of phase 2 themselves and the system
     * of interest, bound by reference: the process declares no part of its
     * own, so the increment has one context. Each participant owns and
     * performs its functions, as the swim lane of its functions: the command
     * source gives each driving command, and the Eclipse S-CORE path hands it
     * to the vehicle network at the boundary interface. The vehicle network
     * records its network identity, takes the command, carries it to the
     * actuation ECU, checks it, and applies it at the actuation ECU, as one
     * action of the process. The vehicle moves by what the actuation ECU
     * gives it and sends nothing back. The functions of the context elements
     * are outside the scope of the vehicle network; its functional scope is
     * the one functional flow usage it performs. The items that cross its
     * boundary are the flows of the process, each chained through the
     * participant that gives and the one that takes.
     *
     * The sequence from a fault to the response: a fault, made from outside
     * the vehicle network, loses a driving command on the route of the run,
     * holds it so that it reaches the actuation ECU more than 100 ms of
     * simulation time after its issue time, repeats it or corrupts it, or
     * takes a link of that route down for the rest of the run. The carriage
     * goes on with each command that the fault does not affect. The check
     * decides by the term valid driving command which of the commands that
     * reach the actuation ECU are valid, and nothing is applied in place of
     * an invalid one, so the vehicle keeps the steering angle and the
     * acceleration of the last valid command. Once more than 200 ms of
     * simulation time pass with no valid driving command reaching the
     * actuation ECU, the actuation ECU applies no driving command that
     * reaches it after that and gives the vehicle the stop response itself: a
     * deceleration of 4 m/s², within the tolerance of REQ-DRIVING-020, with
     * the steering angle of the last valid driving command that it applied,
     * or 0° when it applied none, from no later than 300 ms after the last
     * valid command, or after the start of the run when none reached it,
     * until the run ends. In SC-EE-004 a link of the route goes down, so no
     * valid command reaches the actuation ECU after it, and the vehicle gets
     * the stop response, as phase 2 states for that scenario. Every time
     * counts on the one clock of the virtual vehicle that the testbed gives
     * every element. No element, transport or technology is fixed here.
     */
    ref part commandSource : DrivingCommandSource = eeArchitectureOperationalContext::commandSource {
      doc /*
       * The command source of phase 2: gives each driving command.
       */
      perform action giveCommands : EEGiveDrivingCommand;
    }

    ref part scorePath : SCORECommandAndWarningPath = eeArchitectureOperationalContext::scorePath {
      doc /*
       * The Eclipse S-CORE path of phase 2: hands each driving command to the
       * vehicle network at the boundary interface, with no exchange beside it.
       */
      perform action handOverCommands : EECarryCommandOverSCORE;
    }

    ref part vehicleNetwork : EEVehicleNetworkSystem = eeArchitectureOperationalContext::vehicleNetwork {
      doc /*
       * The system of interest of phase 2: it performs its whole functional
       * flow, the one usage its functional boundary performs. Around a fault it
       * goes on carrying each driving command that the fault does not affect,
       * and at the actuation ECU it applies only the valid ones, so the vehicle
       * keeps the steering angle and the acceleration of the last valid
       * command. Once more than 200 ms of simulation time pass with no valid
       * driving command reaching the actuation ECU, it applies no driving
       * command that reaches the actuation ECU after that and gives the vehicle
       * the stop response there, from no later than 300 ms of simulation time
       * after the last valid command, or after the start of the run when none
       * reached the actuation ECU, until the run ends.
       */
      perform eeVehicleNetworkFunctionalFlow;
    }

    ref part vehicle : SubjectVehicle = eeArchitectureOperationalContext::vehicle {
      doc /*
       * The vehicle of phase 2: steering, acceleration and brakes move it by
       * what the actuation ECU gives it; nothing flows back.
       */
      perform action moveByActuation : EEMoveVehicle;
    }

    flow from commandSource.giveCommands.drivingCommand to scorePath.handOverCommands.drivingCommand;
    flow from scorePath.handOverCommands.carriedCommand to vehicleNetwork.eeVehicleNetworkFunctionalFlow.drivingCommand;
    flow from vehicleNetwork.eeVehicleNetworkFunctionalFlow.appliedCommand to vehicle.moveByActuation.appliedCommand;
  }

  action eeVehicleNetworkSystemProcess : EEVehicleNetworkSystemProcess;

  /* States */

  state def EEActuationStates {
    doc /*
     * The states of the actuation ECU in a run, by the valid driving commands
     * that reach it. It has no valid command from the start of each run until
     * the first one reaches it, and once it gives the stop response it gives
     * it until the run ends.
     */
    state noValidCommandYet {
      doc /*
       * No valid driving command has reached the actuation ECU in this run:
       * applyDrivingCommand gives the vehicle nothing (REQ-EE-008).
       */
    }
    state applyingValidCommands {
      doc /*
       * applyDrivingCommand applies each valid driving command that reaches the
       * actuation ECU and gives the vehicle the steering angle and the
       * acceleration of the last one that it applied (REQ-EE-006, REQ-EE-008).
       * An invalid command changes nothing.
       */
    }
    state givingStopResponse {
      doc /*
       * Entered once more than 200 ms of simulation time pass with no valid
       * driving command reaching the actuation ECU. From then on
       * applyDrivingCommand applies no driving command that reaches the
       * actuation ECU. Until the stop response starts, it gives the vehicle the
       * steering angle and the acceleration of the last valid driving command
       * that it applied, or nothing when it applied none (REQ-EE-008). From no
       * later than 300 ms of simulation time after the last valid command, or
       * after the start of the run when none reached the actuation ECU, until
       * the run ends, it gives the vehicle the stop response: a deceleration of
       * 4 m/s², within the tolerance of REQ-DRIVING-020, with the steering
       * angle of that last valid driving command, or 0° when it applied none
       * (REQ-EE-009).
       */
    }
    transition first noValidCommandYet then applyingValidCommands;  // the first valid driving command reaches the
                                                                    // actuation ECU within 200 ms of simulation time
                                                                    // after the start of the run
    transition first noValidCommandYet then givingStopResponse;  // more than 200 ms of simulation time pass after the
                                                                 // start of the run with no valid driving command
                                                                 // reaching the actuation ECU
    transition first applyingValidCommands then givingStopResponse;  // more than 200 ms of simulation time pass after
                                                                     // the last valid driving command with no other
                                                                     // reaching the actuation ECU
  }

  /* The function whose behavior differs by state depends on it */

  dependency eeApplyDrivingCommandDependsOnNoValidCommandYetState
    from EEVehicleNetworkFunctionalFlow::applyDrivingCommand
    to EEActuationStates::noValidCommandYet;
  dependency eeApplyDrivingCommandDependsOnApplyingValidCommandsState
    from EEVehicleNetworkFunctionalFlow::applyDrivingCommand
    to EEActuationStates::applyingValidCommands;
  dependency eeApplyDrivingCommandDependsOnGivingStopResponseState
    from EEVehicleNetworkFunctionalFlow::applyDrivingCommand
    to EEActuationStates::givingStopResponse;

  /* The conceptual interfaces of the vehicle network */

  item def EEDrivingCommandInput :> DrivingCommandOutput {
    doc /*
     * The driving command as it reaches the boundary interface of the vehicle
     * network: the command that the driver-assistance system gives at its
     * boundary, its steering angle and its acceleration with its detection
     * parts.
     */
  }

  item def EEActuationOutput :> DrivingCommand {
    doc /*
     * What the actuation ECU gives the vehicle: the steering angle and the
     * acceleration of the last valid driving command that it applied, or,
     * during the stop response, the steering angle of the stop response and
     * its deceleration as an acceleration below zero. It carries no detection
     * part.
     */
    attribute steeringAngle : ISQ::AngularMeasureValue;
    attribute acceleration : ISQ::AccelerationValue;
  }

  port def EEDrivingCommandInbound {
    doc /*
     * The input port of the driving command at the boundary interface: the
     * Eclipse S-CORE path gives it there.
     */
    in item drivingCommand : EEDrivingCommandInput;
  }

  port def EEActuationOutbound {
    doc /*
     * The output port of what the actuation ECU gives the vehicle: the
     * vehicle takes it.
     */
    out item appliedCommand : EEActuationOutput;
  }

  part def EEVehicleNetworkFunctionalBoundary :> EEVehicleNetworkSystem {
    doc /*
     * The vehicle network as a functional boundary: one input port and one
     * output port, each with the item of one exchange of phase 2, typed by an
     * item definition of this package that specializes the driving command of
     * phase 2 or the item that the driver-assistance increment defines for
     * it. It performs the functional flow of the network.
     */
    port drivingCommandIn : EEDrivingCommandInbound;
    port actuationOut : EEActuationOutbound;

    perform eeVehicleNetworkFunctionalFlow : EEVehicleNetworkFunctionalFlow {
      in item drivingCommand = drivingCommandIn.drivingCommand;
      out item appliedCommand = actuationOut.appliedCommand;
    }
  }

  /* Requirement-to-function allocations (allocatedTo) */

  comment eeIdentityAllocations
    /*
     * recordNetworkIdentity carries REQ-EE-010: the record is made before the
     * vehicle network takes the first driving command of each run.
     */
  allocation eeNetworkIdentityResponsibility
    allocate reqRecordNetworkIdentity to EEVehicleNetworkFunctionalFlow::recordNetworkIdentity;

  comment eeInputAllocations
    /*
     * takeDrivingCommand carries REQ-EE-002, a design constraint on the input
     * of the vehicle network: it takes driving commands at the boundary
     * interface from the Eclipse S-CORE path and from nowhere else.
     */
  allocation eeTakeOnlyFromSCOREPathResponsibility
    allocate reqCommandsOnlyFromSCOREPath to EEVehicleNetworkFunctionalFlow::takeDrivingCommand;

  comment eeCarriageAllocations
    /*
     * carryDrivingCommand carries REQ-EE-004; REQ-EE-005, a performance
     * requirement on the carriage; and REQ-EE-007, a design constraint on the
     * detection parts that the carriage hands on, whose analysis rests on the
     * realization that phase 8 records.
     */
  allocation eeCarryStreamUnchangedResponsibility
    allocate reqDeliverCommandStreamUnchanged to EEVehicleNetworkFunctionalFlow::carryDrivingCommand;
  allocation eeCarriageTimeResponsibility
    allocate reqCarryEachCommandWithin50Ms to EEVehicleNetworkFunctionalFlow::carryDrivingCommand;
  allocation eeDetectionPartsResponsibility
    allocate reqPassDetectionPartsOnAsTaken to EEVehicleNetworkFunctionalFlow::carryDrivingCommand;

  comment eeActuationAllocations
    /*
     * checkDrivingCommand and applyDrivingCommand share REQ-EE-006 and
     * REQ-EE-008: the check decides which commands are valid, and the
     * application applies them and gives the vehicle only the last valid one.
     * applyDrivingCommand alone carries REQ-EE-009, the stop response at the
     * actuation ECU.
     */
  allocation eeCheckValidCommandResponsibility
    allocate reqApplyEachValidCommand to EEVehicleNetworkFunctionalFlow::checkDrivingCommand;
  allocation eeApplyValidCommandResponsibility
    allocate reqApplyEachValidCommand to EEVehicleNetworkFunctionalFlow::applyDrivingCommand;
  allocation eeCheckLastValidCommandResponsibility
    allocate reqGiveOnlyLastValidCommand to EEVehicleNetworkFunctionalFlow::checkDrivingCommand;
  allocation eeGiveLastValidCommandResponsibility
    allocate reqGiveOnlyLastValidCommand to EEVehicleNetworkFunctionalFlow::applyDrivingCommand;
  allocation eeStopResponseResponsibility
    allocate reqStopResponseAfter200Ms to EEVehicleNetworkFunctionalFlow::applyDrivingCommand;

  /* Views */

  concern eeVehicleNetworkFunctionsConcern : FunctionalBehaviorConcern {
    doc /*
     * System architects and verification engineers need the functions of the
     * vehicle network and each requirement of phase 5 mapped to the functions
     * that carry it: phase 7 gives the functions to logical elements, and
     * phase 10 verifies each requirement on its functions.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder verificationEngineer : VerificationEngineer;
  }

  view eeVehicleNetworkFunctionBreakdownView {
    viewpoint eeFunctionBreakdownViewpoint : SystemFunctionalBreakdownStructureViewpoint {
      frame eeVehicleNetworkFunctionsConcern;
    }
    expose eeVehicleNetworkFunctionalFlow;
    render asTreeDiagram;
  }

  view eeVehicleNetworkRequirementFunctionMatrixView : MVD::MatrixView {
    viewpoint eeRequirementFunctionViewpoint : SystemRequirementTraceabilityViewpoint {
      frame eeVehicleNetworkFunctionsConcern;
    }
    view :>> rowView {
      expose reqBothRoutesInOneTopology;
      expose reqCommandsOnlyFromSCOREPath;
      expose reqCommandsOnlyOnTheirRoute;
      expose reqDeliverCommandStreamUnchanged;
      expose reqCarryEachCommandWithin50Ms;
      expose reqApplyEachValidCommand;
      expose reqPassDetectionPartsOnAsTaken;
      expose reqGiveOnlyLastValidCommand;
      expose reqStopResponseAfter200Ms;
      expose reqRecordNetworkIdentity;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> columnView {
      expose eeVehicleNetworkFunctionalFlow::recordNetworkIdentity;
      expose eeVehicleNetworkFunctionalFlow::takeDrivingCommand;
      expose eeVehicleNetworkFunctionalFlow::carryDrivingCommand;
      expose eeVehicleNetworkFunctionalFlow::checkDrivingCommand;
      expose eeVehicleNetworkFunctionalFlow::applyDrivingCommand;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> cellView {
      expose DE4SDV_EEArchitectureFunctionalArchitecture::*;
      attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;
    }
  }

  /* The vehicle network in operation as a process: the sequence from a fault to the stop response */

  view eeVehicleNetworkSystemProcessView : ActionFlowView {
    viewpoint eeSystemProcessViewpoint : SystemProcessViewpoint {
      frame eeNetworkFaultResponseConcern;
    }
    expose EEVehicleNetworkSystemProcess::*;
    expose EEVehicleNetworkSystemProcess::commandSource::*;
    expose EEVehicleNetworkSystemProcess::scorePath::*;
    expose EEVehicleNetworkSystemProcess::vehicleNetwork::*;
    expose EEVehicleNetworkSystemProcess::vehicle::*;
    attribute showAnnotationRows = false;
    attribute maxCompartmentEntries = 0;
  }

  /* The states, and the function that depends on them */

  concern eeActuationStatesConcern : SystemStateConcern {
    doc /*
     * Safety experts and systems engineers need the states of the actuation
     * ECU in a run, by the valid driving commands that reach it, and the
     * function whose behavior differs in each: before the first valid
     * command, while it applies valid commands, and once more than 200 ms of
     * simulation time pass without a valid driving command, until the run
     * ends.
     */
    subject;
    stakeholder safetyExpert : SafetyExpert;
    stakeholder systemsEngineer : SystemsEngineer;
  }

  view eeVehicleNetworkStateTableView : TVD::TableView {
    viewpoint eeStateTableViewpoint : SystemStateViewpoint {
      frame eeActuationStatesConcern;
    }
    expose EEActuationStates::noValidCommandYet;
    expose EEActuationStates::applyingValidCommands;
    expose EEActuationStates::givingStopResponse;
    filter @ SysML::StateUsage;
    attribute :>> maxRowHeight = 300;
    view State :> columnViews {
      attribute :>> featureToRender = CT::declaredName;
    }
    view DependentFunctions :> columnViews {
      attribute :>> featureToRender = CT::documentation;
      attribute :>> columnWidth = 360;
    }
  }

  /* The conceptual interfaces of the vehicle network */

  concern eeVehicleNetworkInterfaceConcern : FunctionalInterfaceConcern {
    doc /*
     * Systems engineers and software developers need the conceptual
     * interfaces of the vehicle network before phase 7 allocates its
     * functions and phase 8 places elements and software on them: the port at
     * its boundary for each item that crosses it, the direction of that item,
     * and the item that the port's item specializes. Signal typing at a
     * software contract belongs to phase 8.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder softwareDeveloper : SoftwareDeveloper;
  }

  view eeVehicleNetworkFunctionalInterfaceView {
    viewpoint eeFunctionalInterfaceViewpoint : SystemInterfaceDefinitionViewpoint {
      frame eeVehicleNetworkInterfaceConcern;
    }
    expose EEActuationOutbound;
    expose EEDrivingCommandInbound;
    attribute showAnnotationRows = false;
    render asTreeDiagram;
  }
}
