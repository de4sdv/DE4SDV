/*
 * DE4SDV E/E architecture logical architecture.
 *
 * INC-EE-001, phase 7: the logical architecture of the vehicle network.
 * What technology-independent logical elements realize the five functions
 * of phase 6?
 *
 * The decomposition subject is the system of interest itself, one level
 * below the functional boundary of phase 6: EEVehicleNetworkLogicalSystem
 * specializes EEVehicleNetworkFunctionalBoundary, so it keeps the two
 * boundary ports and gives the vehicle network an inside of three logical
 * elements. The context elements of phase 2 stay outside and undivided.
 * Functions stay where phase 6 put them; each is allocated to the logical
 * element that carries it by a native allocation (allocatedTo), a
 * responsibility assignment, not a realization, deployment or runtime
 * claim.
 *
 * Three logical elements for five functions (owner decision of
 * 2026-11-26). Functions share a logical element when nothing requires
 * them to be separately placeable, and split where a requirement
 * constrains the exchange between them or demands that one keeps working
 * when the other does not. The command carrier takes each driving command
 * at the boundary interface and carries it to the actuation end: nothing
 * asks the taking and the carrying to be placed apart. The actuation end
 * checks each driving command that reaches it and applies each valid one
 * until the stop response starts. It stands apart from the command
 * carrier: REQ-EE-004, REQ-EE-005 and REQ-EE-007 constrain the carriage
 * to it, and by REQ-EE-009 the stop response starts there once more than
 * 200 ms of simulation time pass with no valid driving command reaching
 * it, so it keeps working when the carriage delivers nothing. The check
 * stays with the application: phase 5 judges a driving command valid as
 * it reaches the end of its route, and the two functions share REQ-EE-006
 * and REQ-EE-008. The identity recorder stands alone because the record
 * covers the software and the configuration of both other logical
 * elements and comes before the first driving command of each run is
 * taken.
 *
 * The carried driving commands are the one exchange between logical
 * elements, and the three carriage requirements constrain it. REQ-EE-002
 * keeps one input: the boundary delegates the driving command to the
 * command carrier alone. REQ-EE-010 orders the record before the first
 * driving command; phase 6 holds that order by succession, with no item,
 * so it crosses no exchange here. REQ-EE-001 and REQ-EE-003 constrain the
 * topology and the routes, so phase 8 carries them by the elements that
 * it places on the routes. Phase 6 left to phases 7 and 8 which element
 * checks a driving command: here, the actuation end. Where each element
 * of the routes takes the simulation time stays with phase 8. Nothing
 * here names a computer, a process, a transport or a signal catalogue.
 */
package DE4SDV_EEArchitectureLogicalArchitecture {
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_TraceVocabulary::LogicalAllocationElement;
  private import DE4SDV_EEArchitectureFunctionalArchitecture::EEVehicleNetworkFunctionalBoundary;
  private import DE4SDV_EEArchitectureFunctionalArchitecture::EEVehicleNetworkFunctionalFlow;
  private import DE4SDV_EEArchitectureFunctionalArchitecture::eeVehicleNetworkFunctionalFlow;
  private import DE4SDV_EEArchitectureFunctionalArchitecture::EEDrivingCommandInbound;
  private import DE4SDV_EEArchitectureFunctionalArchitecture::EEActuationOutbound;
  private import DE4SDV_DriverAssistanceOperationalContext::DrivingCommand;
  private import SAF_Viewpoints::*;
  private import SysideViews::**;
  private import Views::*;

  /* ─── The ports of the exchange inside the vehicle network ─── */

  port def EECarriedCommandOutbound {
    doc /*
     * The output port of the carried driving commands: the command carrier
     * gives the actuation end each driving command that it carries, with each
     * part as the path gave it.
     */
    out item eeCarriedCommand : DrivingCommand;
  }
  port def EECarriedCommandInbound {
    doc /*
     * The input port of the carried driving commands: the actuation end takes
     * each driving command that reaches it and judges it there by the term
     * valid driving command.
     */
    in item eeCarriedCommand : DrivingCommand;
  }

  /* ─── The three logical elements of the vehicle network ─── */

  part def EEIdentityRecorder :> LogicalAllocationElement {
    doc /*
     * Carries the recording of the network identity: before the first driving
     * command of each run is taken, it records the network identity, whose
     * parts phase 5 names one by one, so that each verdict binds the route,
     * the commit with its difference, the configuration and the settings that
     * ran. The record covers the software and the configuration of the
     * command carrier and of the actuation end alike, so it is a
     * responsibility of its own: phase 8 realizes it, and its order before
     * the first driving command, in the software of the vehicle network. It
     * exchanges nothing with another logical element: phase 6 orders the
     * record before the first driving command by succession, with no item.
     */
  }

  part def EECommandCarrier :> LogicalAllocationElement {
    doc /*
     * Carries the taking and the carriage of the driving commands: it takes
     * each driving command at the boundary interface as the path that carries
     * it there gives it, at the simulation time at which the path gives it,
     * and from nowhere else, and carries it to the actuation end once, in its
     * order and with each part as the path gave it, handing its detection
     * parts on as it received them and computing none of them anew. In a run
     * without a fault each driving command reaches the actuation end within
     * 50 ms of simulation time after it is taken; around a fault the carrier
     * goes on carrying each driving command that the fault does not affect.
     * Nothing asks the taking and the carrying to be placed apart, so they
     * share one logical element. It takes nothing from another logical
     * element. Phase 8 realizes it on the elements that each route passes,
     * which REQ-EE-001 and REQ-EE-003 constrain.
     */
    port eeCommandIn : EEDrivingCommandInbound;
    port eeCarriedCommandOut : EECarriedCommandOutbound;
  }

  part def EEActuationEnd :> LogicalAllocationElement {
    doc /*
     * Carries what the vehicle gets from the vehicle network: it decides, by
     * the term valid driving command, whether each driving command that
     * reaches it is valid, applies each valid one when it reaches it and
     * nothing in place of an invalid one, and gives the vehicle the steering
     * angle and the acceleration of the last valid driving command that it
     * applied, and nothing before the first. Once more than 200 ms of
     * simulation time pass with no valid driving command reaching it, counted
     * from the last one or from the start of the run when none did, it
     * applies no driving command that reaches it after that, and gives the
     * vehicle the stop response on the same output, from no later than 300 ms
     * of simulation time after that last valid driving command or the start
     * of the run until the run ends. The check and the application share
     * REQ-EE-006 and REQ-EE-008, and phase 5 judges a driving command valid
     * as it reaches the end of its route, so they share one logical element.
     * It stands apart from the command carrier because it keeps working when
     * the carriage delivers nothing. It gives nothing to another logical
     * element. Phase 8 realizes it on the last element that a driving command
     * reaches.
     */
    port eeCarriedCommandIn : EECarriedCommandInbound;
    port eeActuationOut : EEActuationOutbound;
  }

  /* ─── The vehicle network one level inside its boundary ─── */

  part def EEVehicleNetworkLogicalSystem :> EEVehicleNetworkFunctionalBoundary {
    doc /*
     * The vehicle network of phase 2, one level inside the functional
     * boundary of phase 6, with its three logical elements and the exchange
     * between them. The boundary ports are inherited and delegated to the
     * logical elements that take or provide their items: the driving command
     * goes to the command carrier, and the applied command leaves from the
     * actuation end. Inside, the carried driving commands go from the command
     * carrier to the actuation end, the one exchange between logical
     * elements. No exchange runs from the actuation end to another logical
     * element, nothing runs into the command carrier from another logical
     * element, and the identity recorder exchanges nothing. This definition
     * names no computer, process, transport or technology.
     * eeVehicleNetworkLogicalSystem is its usage for the views, which draw
     * usages. It depicts the context's vehicleNetwork, whose definition
     * EEVehicleNetworkLogicalSystem specializes, and is bound to nothing.
     */
    part eeIdentityRecorder : EEIdentityRecorder;
    part eeCommandCarrier : EECommandCarrier;
    part eeActuationEnd : EEActuationEnd;

    // The boundary items, delegated from the inherited ports of phase 6.
    connection eeCommandToCarrierDelegation connect drivingCommandIn to eeCommandCarrier.eeCommandIn;
    connection eeActuationFromEndDelegation connect eeActuationEnd.eeActuationOut to actuationOut;

    // The exchange between the logical elements.
    connection eeCommandExchange connect eeCommandCarrier.eeCarriedCommandOut to eeActuationEnd.eeCarriedCommandIn;
  }

  part eeVehicleNetworkLogicalSystem : EEVehicleNetworkLogicalSystem {
    doc /*
     * The vehicle network as the views draw it: the one usage of the logical
     * definition. It depicts the context's vehicleNetwork and is bound to
     * nothing.
     */
  }

  /* ─── Function-to-logical-element allocations (allocatedTo) ─── */

  allocation eeRecordNetworkIdentityAllocation
    allocate EEVehicleNetworkFunctionalFlow::recordNetworkIdentity to EEVehicleNetworkLogicalSystem::eeIdentityRecorder;
  allocation eeTakeDrivingCommandAllocation
    allocate EEVehicleNetworkFunctionalFlow::takeDrivingCommand to EEVehicleNetworkLogicalSystem::eeCommandCarrier;
  allocation eeCarryDrivingCommandAllocation
    allocate EEVehicleNetworkFunctionalFlow::carryDrivingCommand to EEVehicleNetworkLogicalSystem::eeCommandCarrier;
  allocation eeCheckDrivingCommandAllocation
    allocate EEVehicleNetworkFunctionalFlow::checkDrivingCommand to EEVehicleNetworkLogicalSystem::eeActuationEnd;
  allocation eeApplyDrivingCommandAllocation
    allocate EEVehicleNetworkFunctionalFlow::applyDrivingCommand to EEVehicleNetworkLogicalSystem::eeActuationEnd;

  /* ─── Views ─── */

  concern eeVehicleNetworkLogicalStructureConcern : ConceptualStructureConcern {
    doc /*
     * System architects and software developers need the logical elements of
     * the vehicle network, one level inside its functional boundary, each
     * with the responsibility it carries and its ports, before phase 8
     * allocates each of them to a physical element: which logical elements
     * there are, and why each stands alone.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder softwareDeveloper : SoftwareDeveloper;
  }

  view eeVehicleNetworkLogicalStructureView {
    viewpoint eeLogicalStructureViewpoint : SystemStructureDefinitionViewpoint {
      frame eeVehicleNetworkLogicalStructureConcern;
    }
    expose eeVehicleNetworkLogicalSystem;
    expose eeVehicleNetworkLogicalSystem::eeIdentityRecorder;
    expose eeVehicleNetworkLogicalSystem::eeCommandCarrier;
    expose eeVehicleNetworkLogicalSystem::eeActuationEnd;
    filter not (@ SysML::AllocationUsage);
    render asTreeDiagram;
  }

  concern eeVehicleNetworkFunctionMappingConcern : ConceptualFunctionMappingConcern {
    doc /*
     * System architects and verification engineers need each function of
     * phase 6 allocated to the logical element that carries it, and each
     * logical element carrying a function: phase 8 allocates each logical
     * element to a physical element, and phase 10 verifies the requirements
     * that their functions carry.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder verificationEngineer : VerificationEngineer;
  }

  view eeVehicleNetworkFunctionMappingView : MVD::MatrixView {
    viewpoint eeFunctionMappingViewpoint : SystemFunctionMappingViewpoint {
      frame eeVehicleNetworkFunctionMappingConcern;
    }
    view :>> rowView {
      expose eeVehicleNetworkFunctionalFlow::recordNetworkIdentity;
      expose eeVehicleNetworkFunctionalFlow::takeDrivingCommand;
      expose eeVehicleNetworkFunctionalFlow::carryDrivingCommand;
      expose eeVehicleNetworkFunctionalFlow::checkDrivingCommand;
      expose eeVehicleNetworkFunctionalFlow::applyDrivingCommand;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> columnView {
      expose EEVehicleNetworkLogicalSystem::eeIdentityRecorder;
      expose EEVehicleNetworkLogicalSystem::eeCommandCarrier;
      expose EEVehicleNetworkLogicalSystem::eeActuationEnd;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> cellView {
      expose DE4SDV_EEArchitectureLogicalArchitecture::*;
      attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;
    }
  }

  concern eeVehicleNetworkInternalExchangeConcern : ConceptualInternalExchangeConcern {
    doc /*
     * Systems engineers and software developers need the exchanges of the
     * vehicle network between its logical elements, the item each carries and
     * its direction: the carried driving commands, the one exchange between
     * logical elements, which REQ-EE-004, REQ-EE-005 and REQ-EE-007 constrain
     * and whose lack of a valid driving command for more than 200 ms of
     * simulation time starts the stop response of REQ-EE-009; and the
     * boundary items delegated to the logical element that takes or provides
     * them, the driving command by the one input that REQ-EE-002 keeps. Phase
     * 8 places the exchange on the routes.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder softwareDeveloper : SoftwareDeveloper;
  }

  view eeVehicleNetworkInternalExchangeView {
    viewpoint eeInternalExchangeViewpoint : SystemInternalExchangeViewpoint {
      frame eeVehicleNetworkInternalExchangeConcern;
    }
    expose eeVehicleNetworkLogicalSystem;
    expose eeVehicleNetworkLogicalSystem::**;
    filter not (@ SysML::AllocationUsage);
    attribute depth = -1;
    attribute showAnnotationRows = false;
    render asInterconnectionDiagram;
  }
}
