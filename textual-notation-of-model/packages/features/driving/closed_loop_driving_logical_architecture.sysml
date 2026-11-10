/*
 * INC-DRIVING-001, phase 7: the logical architecture of the closed-loop driving
 * system. What technology-independent logical elements realize the seven
 * functions of phase 6?
 *
 * The decomposition subject is the system of interest itself, one level below
 * the functional boundary of phase 6: ClosedLoopDrivingLogicalSystem
 * specializes ClosedLoopDrivingFunctionalBoundary, so it keeps the five
 * boundary ports and gives the system an inside of six logical elements. The
 * context elements of phase 2 stay outside and undivided. Functions stay where
 * phase 6 put them; each is allocated to the element that carries it by a
 * native allocation (allocatedTo), a responsibility assignment, not a
 * realization, deployment or runtime claim.
 *
 * Six elements, not seven (owner decision of 2026-11-06): functions share an
 * element when nothing requires them to be separately placeable, and split
 * where a requirement constrains the exchange between them or demands that one
 * keeps working when the other does not. Run identity and planning share the
 * planner, since the identity check is on the checkpoint the planner loads.
 * The commander and the actuation gateway are separate, since the stop
 * response of REQ-DRIVING-028 must survive the command path failing. The
 * publisher is separate, since observation is one way and off the loop.
 *
 * REQ-DRIVING-014 constrains the plan and the command exchanges, planner to
 * supervisor to commander to actuation gateway; phase 8 places them on a
 * technology. Nothing here names a computer, a process, a transport or a
 * signal catalogue, and nothing is a vehicle signal specification.
 *
 * Amended on the owner's decision of 2026-11-06 (GAP-DRIVING-005 of phase
 * 8): the actuation gateway reports its actuation state to the publisher, so
 * the stop it applies itself (REQ-DRIVING-028) is published with its cause
 * (REQ-DRIVING-029) like the stop the supervisor decides. The publisher stays
 * off the loop; the new exchange is one way, like the ones it joins.
 */
package DE4SDV_ClosedLoopDrivingLogicalArchitecture {
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_TraceVocabulary::LogicalAllocationElement;
  private import DE4SDV_ClosedLoopDrivingOperationalContext::VehicleMotionCommand;
  private import DE4SDV_ClosedLoopDrivingFunctionalArchitecture::ClosedLoopDrivingFunctionalBoundary;
  private import DE4SDV_ClosedLoopDrivingFunctionalArchitecture::ClosedLoopDrivingFunctionalFlow;
  private import DE4SDV_ClosedLoopDrivingFunctionalArchitecture::closedLoopDrivingFunctionalFlow;
  private import DE4SDV_ClosedLoopDrivingFunctionalArchitecture::CheckpointInputs;
  private import DE4SDV_ClosedLoopDrivingFunctionalArchitecture::InputCondition;
  private import DE4SDV_ClosedLoopDrivingFunctionalArchitecture::DrivingPlan;
  private import DE4SDV_ClosedLoopDrivingFunctionalArchitecture::DrivingMode;
  private import DE4SDV_ClosedLoopDrivingFunctionalArchitecture::ActuationState;
  private import DE4SDV_ClosedLoopDrivingFunctionalArchitecture::CameraImagesInbound;
  private import DE4SDV_ClosedLoopDrivingFunctionalArchitecture::EgoMotionInbound;
  private import DE4SDV_ClosedLoopDrivingFunctionalArchitecture::RouteInbound;
  private import DE4SDV_ClosedLoopDrivingFunctionalArchitecture::VehicleCommandOutbound;
  private import DE4SDV_ClosedLoopDrivingFunctionalArchitecture::OperationalStateOutbound;
  private import SAF_Viewpoints::*;
  private import SysideViews::**;
  private import Views::*;

  /* ──────────── The ports of the exchanges inside the driving system ──────────── */

  port def CheckpointInputsOutbound {
    doc /* The output port of the checkpoint inputs of one step: the input conditioner provides them. */
    out item checkpointInputs : CheckpointInputs;
  }
  port def CheckpointInputsInbound {
    doc /* The input port of the checkpoint inputs of one step: the planner takes them. */
    in item checkpointInputs : CheckpointInputs;
  }
  port def InputConditionOutbound {
    doc /* The output port of the input condition of one step: the input conditioner reports it. */
    out item inputCondition : InputCondition;
  }
  port def InputConditionInbound {
    doc /* The input port of the input condition of one step: the loop supervisor reads it. */
    in item inputCondition : InputCondition;
  }
  port def DrivingPlanOutbound {
    doc /* The output port of a plan: the planner provides each plan, the loop supervisor passes the newest valid one on. */
    out item plan : DrivingPlan;
  }
  port def DrivingPlanInbound {
    doc /* The input port of a plan: the loop supervisor, the vehicle commander and the state publisher take plans. */
    in item plan : DrivingPlan;
  }
  port def DrivingModeOutbound {
    doc /* The output port of the mode: the loop supervisor sets it. */
    out item mode : DrivingMode;
  }
  port def DrivingModeInbound {
    doc /* The input port of the mode: the vehicle commander and the state publisher follow it. */
    in item mode : DrivingMode;
  }
  port def MotionCommandOutbound {
    doc /* The output port of a command inside the driving system: the vehicle commander issues it. */
    out item command : VehicleMotionCommand;
  }
  port def MotionCommandInbound {
    doc /* The input port of a command inside the driving system: the actuation gateway takes it. */
    in item command : VehicleMotionCommand;
  }
  port def ActuationStateOutbound {
    doc /* The output port of the actuation state inside the driving system: the actuation gateway reports it. */
    out item actuationState : ActuationState;
  }
  port def ActuationStateInbound {
    doc /* The input port of the actuation state inside the driving system: the publisher takes it. */
    in item actuationState : ActuationState;
  }

  /* ──────────────── The six logical elements of the driving system ──────────────── */

  part def InputConditioner :> LogicalAllocationElement {
    doc /*
     * Carries the assembly of the checkpoint inputs: it takes the camera
     * images, the ego motion and the route at the boundary of the driving
     * system and provides, for each step, the inputs the checkpoint takes and
     * the condition of those inputs. It is the ingress of the driving system;
     * the element that supplies it with the inputs of phase 2 stays outside.
     */
    port cameraImagesIn : CameraImagesInbound;
    port egoMotionIn : EgoMotionInbound;
    port routeIn : RouteInbound;
    port checkpointInputsOut : CheckpointInputsOutbound;
    port inputConditionOut : InputConditionOutbound;
  }

  part def TrajectoryPlanner :> LogicalAllocationElement {
    doc /*
     * Carries the identification of the run and the planning of the
     * trajectory: it holds the pinned checkpoint, refuses to plan when the
     * checkpoint is not the one the configuration names, records the run
     * identity, and makes the plans from the checkpoint inputs.
     * The identity check is on the checkpoint this element loads, so the two
     * functions share it.
     */
    port checkpointInputsIn : CheckpointInputsInbound;
    port planOut : DrivingPlanOutbound;
  }

  part def LoopSupervisor :> LogicalAllocationElement {
    doc /*
     * Carries the supervision of the loop: it detects degraded inputs and
     * plans, sets the mode, priming, driving or stopped with its cause, and
     * passes the newest valid plan on. It is the one authority on the mode;
     * it issues no command of its own.
     */
    port inputConditionIn : InputConditionInbound;
    port planIn : DrivingPlanInbound;
    port validPlanOut : DrivingPlanOutbound;
    port modeOut : DrivingModeOutbound;
  }

  part def VehicleCommander :> LogicalAllocationElement {
    doc /*
     * Carries the commanding of the vehicle: it computes the steering and
     * acceleration commands from the newest valid plan, the mode and the
     * current motion of the vehicle, within the limits of the vehicle its
     * configuration names, and the stop response as a mode of that one
     * command computation. It is the one command source of the driving
     * system.
     */
    port validPlanIn : DrivingPlanInbound;
    port modeIn : DrivingModeInbound;
    port egoMotionIn : EgoMotionInbound;
    port commandOut : MotionCommandOutbound;
  }

  part def ActuationGateway :> LogicalAllocationElement {
    doc /*
     * Carries the application of the commands at the actuation: it gives
     * each command to the actuation of the vehicle at the boundary of the
     * driving system and applies the stop response itself when no valid
     * command reaches it in the limit of REQ-DRIVING-028. It is separate from
     * the vehicle commander so that the vehicle stops also when the command
     * path between them does not deliver. It reports its actuation state,
     * the applied command with its time or its own stop with the cause, to
     * the publisher, which is off the loop; nothing of it flows back.
     */
    port commandIn : MotionCommandInbound;
    port vehicleCommandOut : VehicleCommandOutbound;
    port actuationStateOut : ActuationStateOutbound;
  }

  part def OperationalStatePublisher :> LogicalAllocationElement {
    doc /*
     * Carries the publication of the operational state: each plan, the motion
     * of each step, the health and the stop with its cause, whether the loop
     * supervisor decided it (the mode) or the actuation gateway did (the
     * actuation state), one way, for the state observer outside the driving
     * system. Nothing it provides flows back into the loop, so it is separate
     * from the elements of the loop.
     */
    port planIn : DrivingPlanInbound;
    port egoMotionIn : EgoMotionInbound;
    port modeIn : DrivingModeInbound;
    port actuationStateIn : ActuationStateInbound;
    port operationalStateOut : OperationalStateOutbound;
  }

  /* ──────────────── The driving system one level inside its boundary ──────────────── */

  part def ClosedLoopDrivingLogicalSystem :> ClosedLoopDrivingFunctionalBoundary {
    doc /*
     * The driving system of phase 2, one level inside the functional boundary
     * of phase 6: the same system, now with its six logical elements and the
     * exchanges between them. The boundary ports are inherited and delegated
     * to the elements that take or provide their items: the ego motion goes
     * to the input conditioner, the vehicle commander and the state publisher
     * alike. Inside, the plan goes from the planner to the loop supervisor
     * and, as the newest valid plan, on to the vehicle commander; the command
     * goes from the vehicle commander to the actuation gateway. Those are the
     * exchanges REQ-DRIVING-014 constrains and phase 8 places. No exchange
     * runs from the state publisher or the actuation gateway back into the
     * loop. This definition names no computer, process, transport or
     * technology. closedLoopDrivingLogicalSystem is its usage for the views,
     * which draw usages; it is the same system as the context's
     * drivingSystem, not a second one.
     */
    part inputConditioner : InputConditioner;
    part planner : TrajectoryPlanner;
    part loopSupervisor : LoopSupervisor;
    part vehicleCommander : VehicleCommander;
    part actuationGateway : ActuationGateway;
    part statePublisher : OperationalStatePublisher;

    // The boundary items, delegated from the inherited ports of phase 6.
    connection cameraImagesDelegation
      connect cameraImagesIn to inputConditioner.cameraImagesIn;
    connection egoMotionToConditioner
      connect egoMotionIn to inputConditioner.egoMotionIn;
    connection egoMotionToCommander
      connect egoMotionIn to vehicleCommander.egoMotionIn;
    connection egoMotionToPublisher
      connect egoMotionIn to statePublisher.egoMotionIn;
    connection routeDelegation
      connect routeIn to inputConditioner.routeIn;
    connection vehicleCommandDelegation
      connect actuationGateway.vehicleCommandOut to vehicleCommandOut;
    connection operationalStateDelegation
      connect statePublisher.operationalStateOut to operationalStateOut;

    // The exchanges between the elements, in the order of the loop.
    connection checkpointInputsExchange
      connect inputConditioner.checkpointInputsOut to planner.checkpointInputsIn;
    connection inputConditionExchange
      connect inputConditioner.inputConditionOut to loopSupervisor.inputConditionIn;
    connection planToSupervisor
      connect planner.planOut to loopSupervisor.planIn;
    connection planToPublisher
      connect planner.planOut to statePublisher.planIn;
    connection validPlanExchange
      connect loopSupervisor.validPlanOut to vehicleCommander.validPlanIn;
    connection modeToCommander
      connect loopSupervisor.modeOut to vehicleCommander.modeIn;
    connection modeToPublisher
      connect loopSupervisor.modeOut to statePublisher.modeIn;
    connection commandExchange
      connect vehicleCommander.commandOut to actuationGateway.commandIn;
    connection actuationStateToPublisher
      connect actuationGateway.actuationStateOut to statePublisher.actuationStateIn;
  }

  part closedLoopDrivingLogicalSystem : ClosedLoopDrivingLogicalSystem {
    doc /* The driving system as the views draw it: the one usage of the logical definition, the same system as the context's drivingSystem. */
  }

  /* ─────────────── Function-to-logical-element allocations (allocatedTo) ─────────────── */

  allocation inputConditioningResponsibility
    allocate ClosedLoopDrivingFunctionalFlow::assembleInputs to ClosedLoopDrivingLogicalSystem::inputConditioner;
  allocation runIdentityResponsibility
    allocate ClosedLoopDrivingFunctionalFlow::identifyRun to ClosedLoopDrivingLogicalSystem::planner;
  allocation planningResponsibility
    allocate ClosedLoopDrivingFunctionalFlow::planTrajectory to ClosedLoopDrivingLogicalSystem::planner;
  allocation supervisionResponsibility
    allocate ClosedLoopDrivingFunctionalFlow::superviseLoop to ClosedLoopDrivingLogicalSystem::loopSupervisor;
  allocation commandingResponsibility
    allocate ClosedLoopDrivingFunctionalFlow::commandVehicle to ClosedLoopDrivingLogicalSystem::vehicleCommander;
  allocation actuationResponsibility
    allocate ClosedLoopDrivingFunctionalFlow::applyCommands to ClosedLoopDrivingLogicalSystem::actuationGateway;
  allocation publicationResponsibility
    allocate ClosedLoopDrivingFunctionalFlow::publishState to ClosedLoopDrivingLogicalSystem::statePublisher;

  /* ─────────────────────────────── Views ─────────────────────────────── */

  concern closedLoopDrivingLogicalStructureConcern : ConceptualStructureConcern {
    doc /*
     * System architects and software developers need the logical elements of
     * the driving system, one level inside its functional boundary, each with
     * the responsibility it carries and its ports, before phase 8 places
     * software on them: which elements there are, and why each stands alone.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder softwareDeveloper : SoftwareDeveloper;
  }

  view closedLoopDrivingLogicalStructureView {
    viewpoint selectedLogicalStructureViewpoint : SystemStructureDefinitionViewpoint {
      frame closedLoopDrivingLogicalStructureConcern;
    }
    expose closedLoopDrivingLogicalSystem;
    expose closedLoopDrivingLogicalSystem::inputConditioner;
    expose closedLoopDrivingLogicalSystem::planner;
    expose closedLoopDrivingLogicalSystem::loopSupervisor;
    expose closedLoopDrivingLogicalSystem::vehicleCommander;
    expose closedLoopDrivingLogicalSystem::actuationGateway;
    expose closedLoopDrivingLogicalSystem::statePublisher;
    filter not (@ SysML::AllocationUsage);
    render asTreeDiagram;
  }

  concern closedLoopDrivingFunctionMappingConcern : ConceptualFunctionMappingConcern {
    doc /*
     * System architects and verification engineers need each function of
     * phase 6 allocated to the logical element that carries it, and each
     * element carrying at least one function: phase 8 places the elements,
     * and phase 10 verifies each requirement on the functions of its element.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder verificationEngineer : VerificationEngineer;
  }

  view closedLoopDrivingFunctionMappingView : MVD::MatrixView {
    viewpoint selectedFunctionMappingViewpoint : SystemFunctionMappingViewpoint {
      frame closedLoopDrivingFunctionMappingConcern;
    }
    view :>> rowView {
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
    view :>> columnView {
      expose ClosedLoopDrivingLogicalSystem::inputConditioner;
      expose ClosedLoopDrivingLogicalSystem::planner;
      expose ClosedLoopDrivingLogicalSystem::loopSupervisor;
      expose ClosedLoopDrivingLogicalSystem::vehicleCommander;
      expose ClosedLoopDrivingLogicalSystem::actuationGateway;
      expose ClosedLoopDrivingLogicalSystem::statePublisher;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> cellView {
      expose DE4SDV_ClosedLoopDrivingLogicalArchitecture::*;
      attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;
    }
  }

  concern closedLoopDrivingInternalExchangeConcern : ConceptualInternalExchangeConcern {
    doc /*
     * Systems engineers and software developers need the exchanges between
     * the logical elements of the driving system, the item each carries and
     * its direction: the plan and the command exchanges that REQ-DRIVING-014
     * and REQ-DRIVING-028 constrain, the actuation state exchange that
     * REQ-DRIVING-029 times, and the boundary items delegated to the elements
     * that take or provide them. Phase 8 places each exchange on a
     * technology.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder softwareDeveloper : SoftwareDeveloper;
  }

  view closedLoopDrivingInternalExchangeView {
    viewpoint selectedInternalExchangeViewpoint : SystemInternalExchangeViewpoint {
      frame closedLoopDrivingInternalExchangeConcern;
    }
    expose closedLoopDrivingLogicalSystem;
    expose closedLoopDrivingLogicalSystem::**;
    filter not (@ SysML::AllocationUsage);
    attribute depth = -1;
    attribute showAnnotationRows = false;
    render asInterconnectionDiagram;
  }
}
