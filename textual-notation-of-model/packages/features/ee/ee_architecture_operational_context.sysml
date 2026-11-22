/*
 * DE4SDV E/E architecture: Phase 2 operational context.
 *
 * INC-EE-001, phase 2: what happens in the world of the vehicle network. The
 * source of the driving command on the central computer gives the command,
 * the Eclipse S-CORE path hands it to the vehicle network, the network
 * carries it on one of its two routes to the actuation ECU on CAN, and the
 * vehicle takes the command that the actuation ECU applies. The source and
 * the S-CORE path are System 1 parts outside the vehicle network, as phase 0
 * draws the boundary. The testbed, the replay, the fault injection, the
 * vehicle model, the records and the evaluators are System 2 and stay out of
 * this context. No timing, safety, compliance or production-readiness claim
 * is made.
 */

package DE4SDV_EEArchitectureOperationalContext {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_OperationalContext::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_SYSMODAdapter::*;
  private import DE4SDV_EEArchitectureFraming::*;
  private import DE4SDV_DriverAssistanceOperationalContext::DrivingCommand;
  private import DE4SDV_DriverAssistanceOperationalContext::SCORECommandAndWarningPath;
  private import SAF_Viewpoints::*;
  private import Views::*;

  /* ───────────────────── Phase 2: what happens in the world ───────────────────── */

  part def DrivingCommandSource :> OperationalEntity {
    doc /*
     * What gives the driving command on the central computer. In this
     * increment the driver-assistance candidate of INC-DRIVING-002 gives the
     * driving command, and that increment fixes its form at its baseline
     * (asmEECommandFromDrivingBaseline). A System 1 part outside the vehicle
     * network and no enabling system. In verification a System 2 part stands
     * in for it (eeVerificationEnvironment).
     */
  }

  part eeArchitectureOperationalContext : SystemContext {
    doc /*
     * The operational context of the vehicle network. Inside the system of
     * interest, as phase 0 draws it: the network side of the central
     * computer, the Ethernet backbone, the two zone controllers, a CAN bus in
     * each zone, the direct link and the actuation ECU on CAN that receives
     * the command and acts on it; it stays a black box until the architecture
     * phases. The source of the driving command on the central computer and
     * the Eclipse S-CORE path are System 1 parts outside the vehicle network
     * and no enabling systems; the central computer lies across the boundary.
     * Around it the vehicle only takes the command that the actuation ECU
     * applies. System 1 roles only: the testbed, the replay, the fault
     * injection, the vehicle model, the records and the evaluators stay in
     * eeVerificationEnvironment. This is the operational environment, not a
     * deployment decomposition.
     */
    part vehicleNetwork : EEVehicleNetworkSystem :>> systemOfInterest;
    part commandSource : DrivingCommandSource {
      doc /*
       * The source of the driving command on the central computer.
       */
    }
    part scorePath : SCORECommandAndWarningPath {
      doc /*
       * The Eclipse S-CORE path of the existing increments on the central
       * computer: it hands the driving command to the network side of the
       * central computer (asmEEScoreCommandSource); the scope holds one flow,
       * so it carries no warning request in this increment.
       */
    }
    part vehicle : SubjectVehicle {
      doc /*
       * The vehicle whose steering, acceleration and brakes move it: it takes
       * the command that the actuation ECU applies and sends nothing back.
       */
    }
  }

  /* Operational behavior: the command crosses the boundary once in and once out; nothing flows back. */
  action def VehicleNetworkCommandOperation {
    doc /*
     * One command in the world: the source gives it, the Eclipse S-CORE path
     * hands it to the vehicle network, the network carries it on one of its
     * two routes to the actuation ECU, which applies it to the vehicle or,
     * when it detects a fault, applies nothing; nothing flows back from the
     * vehicle.
     */
    action giveDrivingCommand {
      doc /*
       * The command source: gives the driving command.
       */
      out drivingCommand : DrivingCommand;
    }

    action carryCommandOverSCORE {
      doc /*
       * The S-CORE path: hands the driving command to the vehicle network.
       */
      in drivingCommand : DrivingCommand;
      out carriedCommand : DrivingCommand;
    }

    flow from giveDrivingCommand.drivingCommand to carryCommandOverSCORE.drivingCommand;
    first giveDrivingCommand then carryCommandOverSCORE;

    action carryAndApplyCommand {
      doc /*
       * The vehicle network: carries the command on a route to the actuation
       * ECU, which applies a command that reaches it whole and applies none
       * that it rejects. Where the requirements ask for a stop response, the
       * stop response reaches the vehicle on the same flow.
       */
      in drivingCommand : DrivingCommand;
      out appliedCommand : DrivingCommand;
    }

    flow from carryCommandOverSCORE.carriedCommand to carryAndApplyCommand.drivingCommand;
    first carryCommandOverSCORE then carryAndApplyCommand;

    action moveVehicle {
      doc /*
       * The vehicle: steering, acceleration and brakes move it; nothing flows
       * back to the vehicle network.
       */
      in appliedCommand : DrivingCommand;
    }

    flow from carryAndApplyCommand.appliedCommand to moveVehicle.appliedCommand;
  }

  action vehicleNetworkCommandOperation : VehicleNetworkCommandOperation;

  /* Operational story on the SYSMOD seam. */
  use case def CarryDrivingCommandToActuation :> SYSMODSystemUseCaseBase {
    doc /*
     * The vehicle network in operation: it carries the driving command to the
     * actuation ECU on each of its two routes, applies no command that a
     * fault has made invalid, and leaves the vehicle the stop response when
     * no valid command reaches the actuation.
     */
    attribute redefines ucMotivation = "The product line needs a vehicle network that carries the driving command from the central computer to an actuation ECU on CAN and keeps, on each of two routes, the properties that the model asks of the command paths of earlier increments.";
    attribute redefines ucTrigger = "The command source on the central computer gives driving commands, and the Eclipse S-CORE path hands each one to the vehicle network.";
    attribute redefines ucResult = "On each route a command that reaches the actuation ECU whole is applied to the vehicle, a command that is lost, delayed, repeated or corrupted on its way is detected and not applied, and when no valid command reaches the actuation the vehicle gets the stop response.";

    objective {
      doc /*
       * Frame the two routes, the command fault and the link that goes down,
       * only. The criteria and their limits are fixed with the requirements
       * (phase 5); a time limit counts on the clock of the virtual vehicle and
       * makes no timing claim for a vehicle network.
       */
    }
  }

  use case vehicleNetworkStory : CarryDrivingCommandToActuation {
    subject vehicleNetwork : EEVehicleNetworkSystem = eeArchitectureOperationalContext::vehicleNetwork;
    actor commandSource : DrivingCommandSource = eeArchitectureOperationalContext::commandSource;
    actor scorePath : SCORECommandAndWarningPath = eeArchitectureOperationalContext::scorePath;
    actor vehicle : SubjectVehicle = eeArchitectureOperationalContext::vehicle;

    objective {
      doc /*
       * Operate the vehicle network without selecting the medium of the direct
       * link or a realization, and without any timing, safety, compliance or
       * production-readiness claim.
       */
    }

    first start;
    then include carryCommandThroughZoneController;
    then include carryCommandOverDirectLink;
    then include rejectFaultyCommandOnTheRoute;
    then include respondToLinkDownOnTheRoute;
    then done;
  }

  use case carryCommandThroughZoneController {
    subject vehicleNetwork : EEVehicleNetworkSystem = eeArchitectureOperationalContext::vehicleNetwork;
    actor commandSource : DrivingCommandSource = eeArchitectureOperationalContext::commandSource;
    actor scorePath : SCORECommandAndWarningPath = eeArchitectureOperationalContext::scorePath;
    actor vehicle : SubjectVehicle = eeArchitectureOperationalContext::vehicle;

    objective {
      doc /*
       * SC-EE-001 (route through a zone controller): the command enters the
       * vehicle network from the Eclipse S-CORE path, crosses the Ethernet
       * backbone and a zone controller, which passes it to CAN, reaches the
       * actuation ECU, and the actuation ECU applies it to the vehicle. No
       * timing claim for a vehicle network is made.
       */
    }

    first start;
    then done;
  }

  use case carryCommandOverDirectLink {
    subject vehicleNetwork : EEVehicleNetworkSystem = eeArchitectureOperationalContext::vehicleNetwork;
    actor commandSource : DrivingCommandSource = eeArchitectureOperationalContext::commandSource;
    actor scorePath : SCORECommandAndWarningPath = eeArchitectureOperationalContext::scorePath;
    actor vehicle : SubjectVehicle = eeArchitectureOperationalContext::vehicle;

    objective {
      doc /*
       * SC-EE-002 (direct link): the command enters the vehicle network from
       * the Eclipse S-CORE path, goes over the direct link from the central
       * computer, which passes no zone controller, reaches the actuation ECU,
       * and the actuation ECU applies it to the vehicle. Phases 6 to 8 decide
       * what the link is. No timing claim for a vehicle network is made.
       */
    }

    first start;
    then done;
  }

  use case rejectFaultyCommandOnTheRoute {
    subject vehicleNetwork : EEVehicleNetworkSystem = eeArchitectureOperationalContext::vehicleNetwork;
    actor commandSource : DrivingCommandSource = eeArchitectureOperationalContext::commandSource;
    actor scorePath : SCORECommandAndWarningPath = eeArchitectureOperationalContext::scorePath;
    actor vehicle : SubjectVehicle = eeArchitectureOperationalContext::vehicle;

    objective {
      doc /*
       * SC-EE-003 (command fault on the route): on either route a command is
       * lost, delayed, repeated or corrupted on its way; the actuation detects
       * it and applies no command that it rejects. How it detects the fault is
       * fixed with the requirements (phase 5) and decided in the architecture
       * phases. No timing claim for a vehicle network is made.
       */
    }

    first start;
    then done;
  }

  use case respondToLinkDownOnTheRoute {
    subject vehicleNetwork : EEVehicleNetworkSystem = eeArchitectureOperationalContext::vehicleNetwork;
    actor commandSource : DrivingCommandSource = eeArchitectureOperationalContext::commandSource;
    actor scorePath : SCORECommandAndWarningPath = eeArchitectureOperationalContext::scorePath;
    actor vehicle : SubjectVehicle = eeArchitectureOperationalContext::vehicle;

    objective {
      doc /*
       * SC-EE-004 (link down): on either route one link of the route goes down;
       * no valid command reaches the actuation, and the vehicle gets the stop
       * response that the engineering question names, after REQ-DRIVING-028 of
       * INC-DRIVING-001, not from the driver-assistance increment, whose
       * adapter has no stop response (gapEEActuationEnd). As there, the
       * response and its time limit are fixed with the requirements (phase 5).
       * No timing claim for a vehicle network is made.
       */
    }

    first start;
    then done;
  }

  /* Traces to the Phase 0 records this context implements. */
  dependency vehicleNetworkStoryAnswersProblem
    from vehicleNetworkStory
    to DE4SDV_EEArchitectureFraming::eeArchitectureProblem;
  dependency commandSourceOnDrivingBaseline
    from DrivingCommandSource
    to DE4SDV_EEArchitectureFraming::asmEECommandFromDrivingBaseline;
  dependency scorePathOnScoreCommandSource
    from eeArchitectureOperationalContext::scorePath
    to DE4SDV_EEArchitectureFraming::asmEEScoreCommandSource;
  dependency routeScenariosOnZoneRouteGap
    from vehicleNetworkStory
    to DE4SDV_EEArchitectureFraming::gapEEZoneRouteInVehicles;

  comment actuationEndComment about DE4SDV_EEArchitectureFraming::gapEEActuationEnd
  /*
   * Phase 2 draws no input from the vehicle to the actuation ECU. Whether
   * the actuation end takes a vehicle speed for its conversion of the
   * command, and which element holds the detection, the rejection and the
   * stop response, phases 6 to 8 decide inside the black box; this context
   * changes neither the driver-assistance nor the closed-loop adapter. A
   * speed input would reopen this context.
   */

  comment stackAndNetworkBoundaryComment about DE4SDV_EEArchitectureFraming::gapEEStackAndNetworkBoundary
  /*
   * The central computer lies across the boundary: its network side is
   * inside the vehicle network, the command source and the S-CORE path are
   * outside. This context reuses no element of the platform stack, no SoC
   * and no VehicleNetworkBoundary; how the vehicle network relates to them
   * is for phase 3.
   */

  concern eeArchitectureContextConcern : OperationalContextConcern {
    doc /*
     * System architects, systems engineers and open-source reviewers need to
     * see what is inside the vehicle network and what is around it: the
     * source of the driving command, the Eclipse S-CORE path and the vehicle,
     * and which item crosses the boundary in which direction. The actuation
     * ECU is inside; the source and the S-CORE path are outside; the vehicle
     * only receives.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view eeArchitectureOperationalContextView {
    viewpoint eeArchitectureContextViewpoint : OperationalContextDefinitionViewpoint {
      frame eeArchitectureContextConcern;
    }

    expose eeArchitectureOperationalContext;
    expose eeArchitectureOperationalContext::*;
    expose vehicleNetworkCommandOperation;
    attribute depth = 2;
    attribute showAnnotationRows = false;
    render asTreeDiagram;
  }

  concern eeArchitectureStoryConcern : OperationalStoryConcern {
    doc /*
     * Systems engineers, verification engineers and open-source reviewers
     * need the vehicle network told in stakeholder language: the driving
     * command on each of its two routes, a command that a fault makes
     * invalid, and a link of the route that goes down.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view eeArchitectureOperationalStoryView {
    viewpoint eeArchitectureStoryViewpoint : OperationalStoryViewpoint {
      frame eeArchitectureStoryConcern;
      frame eeVehicleCommandConcern;
    }

    expose vehicleNetworkStory;
    expose vehicleNetworkStory::*;
    attribute depth = 1;
    attribute showAnnotationRows = false;
    render asTreeDiagram;
  }
}
