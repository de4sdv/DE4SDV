/*
 * DE4SDV E/E architecture physical E/E realization.
 *
 * INC-EE-001, phase 8: the E/E realization of the vehicle network. Which
 * nodes and links of the vehicle network realize the three logical
 * elements of phase 7, and what carries each driving command on each
 * route from the network side of the central computer to the actuation
 * ECU?
 *
 * The realization (owner decisions of 2026-11-26):
 *
 * - Phase 8 realizes the vehicle network in two packages: this E/E
 *   realization of its nodes, its links and the frame on them, and a
 *   software realization of the software of each node, which follows a
 *   change to the method that relates software to a node. This package
 *   places no software.
 * - The network side of the central computer takes each driving command
 *   from the Eclipse S-CORE path and puts it, with its three detection
 *   parts, into one CAN FD frame. No vehicle signal broker and no other
 *   element sits between the take and the frame.
 * - Each driving command is one CAN FD frame, which the network side
 *   builds. On the route through a zone controller the frame goes over
 *   the Ethernet backbone inside an IEEE 1722 packet, and the zone
 *   controller of the actuation ECU's zone unpacks it onto the CAN FD bus
 *   of its zone and repacks nothing. On the direct route the same frame
 *   goes over a CAN FD link to the actuation ECU. The actuation ECU gets
 *   the same bytes on both routes, so the design keeps each part
 *   unchanged (REQ-EE-004) and has each element pass the detection parts
 *   on as it received them (REQ-EE-007).
 *
 * What follows from the phase 7 elements and the defaults of this phase:
 *
 * - Topology: the one topology of REQ-EE-001, with the central computer,
 *   two zone controllers, the Ethernet backbone between the central
 *   computer and the zone controllers, a CAN FD bus in each zone, and the
 *   direct link, which passes no zone controller, to the actuation ECU.
 *   Of the central computer only its network side is an element of the
 *   vehicle network; the command source and the Eclipse S-CORE path on it
 *   are outside. The central computer, the two zone controllers and the
 *   actuation ECU are typed as vehicle compute nodes, a typing that
 *   claims no board, no operating system and no qualification; the links
 *   are not. The central computer is declared here, and the realization
 *   of the HMI display keeps its own declaration of it until software can
 *   be placed on a node (gapEECentralComputerHandover).
 * - Placement: the network side carries the identity recorder and the
 *   command carrier, the zone controller of the actuation ECU's zone
 *   carries the command carrier, and the actuation ECU carries the
 *   actuation end. The links carry the frame, compute nothing and receive
 *   no allocation; the signal mappings name them. The other zone
 *   controller and its CAN FD bus lie on neither route and carry no
 *   logical element.
 * - Time: the network side reads the vehicle's clock when it takes a
 *   driving command, and the actuation ECU reads it when one arrives; no
 *   other element of the vehicle network reads a clock for the command.
 *   The vehicle's clock is one time base that the central computer and
 *   the actuation ECU share; the source sets the issue time on it too, so
 *   the check of the issue time and the 50 ms of REQ-EE-005 rest on the
 *   two nodes reading the same time. How the nodes share it, time
 *   synchronisation between them, stays out of scope
 *   (eeTimingOutOfScope). On the bench the testbed's simulation clock,
 *   one clock for every element, stands in for the vehicle's clock.
 * - VSS at the frame: the steering angle and the acceleration of the
 *   frame are typed by the two DE4SDV_VSS_Extensions command signals of
 *   the driving increments, beside the quantities of phase 6 that the
 *   frame inherits. The issue time, the sequence count and the check
 *   value are protocol fields, no vehicle signal. No VSS extension is
 *   added.
 * - Configuration: the files that REQ-EE-010 reads are named by role: the
 *   frame layout, the routing entry of the zone controller and the route
 *   setting; their paths come with the implementation
 *   (gapEEConfigurationNamedByRole).
 *
 * Alternatives recorded and not selected:
 *
 * - ALT-EE-VSSBROKER-001: the driving command through a vehicle signal
 *   broker on the central computer, from which a provider builds the
 *   frame. The three detection parts are no vehicle signal, so they would
 *   cross the broker as signals that they are not, or be computed anew
 *   after it, which REQ-EE-007 does not allow; and no requirement of this
 *   increment asks for what a broker adds.
 * - ALT-EE-SIGNALGATEWAY-001: the backbone carries the driving command as
 *   an Ethernet service message, and the zone controller builds a new
 *   CAN FD frame from it. The zone controller would encode each part
 *   anew, its check value with them, which REQ-EE-007 does not allow.
 * - ALT-EE-CLASSICALCAN-001: classical CAN, more than one frame per
 *   driving command, which the actuation ECU joins again. The sequence
 *   count and the check value alone fill the data of one classical CAN
 *   frame.
 *
 * The network side of the central computer, the Ethernet backbone, the
 * two zone controllers, the CAN FD bus of each zone, the direct link and
 * the actuation ECU are inside the vehicle network; the rest of the
 * central computer and the vehicle are outside it, and the testbed that
 * stands in for them is System 2. An allocation here is a responsibility
 * assignment, no deployment, execution or runtime claim; a signal mapping
 * is no interoperability claim. Nothing in this package claims that a
 * requirement is met, that a case ran or that the bench has shown
 * anything.
 */
package DE4SDV_EEArchitecturePhysicalEERealization {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_MethodProcess::SystemToSoftwareSignalMappingCandidate;
  private import DE4SDV_MethodProcess::LogicalToSoftwareSignalMappingRecord;
  private import DE4SDV_MethodProcess::SignalMappingDisposition;
  private import DE4SDV_TraceVocabulary::PhysicalAllocationElement;
  private import DE4SDV_ExecutionEnvironments::VehicleComputeNode;
  private import DE4SDV_DriverAssistancePhysicalSoftwareRealization::DrivingCommandEventPayload;
  private import DE4SDV_EEArchitectureFraming::gapEEActuationEnd;
  private import DE4SDV_EEArchitectureFraming::gapEEStackAndNetworkBoundary;
  private import DE4SDV_EEArchitectureFraming::gapEEBenchPlatform;
  private import DE4SDV_EEArchitectureFraming::asmEEScoreCommandSource;
  private import DE4SDV_EEArchitectureFraming::eeTopologyStructureConcern;
  private import DE4SDV_EEArchitectureFraming::eeCommandItemConcern;
  private import DE4SDV_EEArchitectureFraming::eeCommandRouteExchangeConcern;
  private import DE4SDV_EEArchitectureFunctionalArchitecture::EEDrivingCommandInput;
  private import DE4SDV_EEArchitectureFunctionalArchitecture::EEActuationOutput;
  private import DE4SDV_EEArchitectureLogicalArchitecture::EEVehicleNetworkLogicalSystem;
  private import DE4SDV_EEArchitectureNeedsRequirements::reqBothRoutesInOneTopology;
  private import DE4SDV_EEArchitectureNeedsRequirements::reqCommandsOnlyOnTheirRoute;
  private import DE4SDV_VSS_Extensions::Vehicle_ADAS_Driving_Command_Acceleration;
  private import DE4SDV_VSS_Extensions::Vehicle_ADAS_Driving_Command_SteeringAngle;
  private import DE4SDV_Stakeholders::*;
  private import SAF_Viewpoints::*;
  private import SysideViews::**;
  private import Views::*;

  /* ─── The items on the links ─── */

  item def EECommandFrame :> EEDrivingCommandInput {
    doc /*
     * The driving command as the realization types it on the links: one
     * CAN FD frame per driving command, which the network side of the central
     * computer builds from the parts as it takes them, and which reaches the
     * actuation ECU with the same bytes on both routes. It keeps the five
     * parts of the boundary item of phase 6 as it inherits them: the steering
     * angle, the acceleration, and the issue time, the sequence count and the
     * check value, the detection parts. Beside the inherited steering angle
     * and acceleration it carries their values typed by the two
     * DE4SDV_VSS_Extensions command signals: eeSteeringAngleSignal, the value
     * in degrees of the inherited steeringAngle, positive to the left, and
     * eeAccelerationSignal, the value in m/s² of the inherited acceleration,
     * negative to decelerate. The issue time counts in seconds on the
     * vehicle's clock, the sequence count is an unsigned 32-bit count from 1
     * in each run, and the check value is the CRC-32 over the other parts;
     * these three are protocol fields, no vehicle signal. The five parts fit
     * the data of one CAN FD frame; the frame's identifier and the layout of
     * its bytes are set by the frame layout of the configuration
     * (gapEEConfigurationNamedByRole).
     */
    attribute eeSteeringAngleSignal : Vehicle_ADAS_Driving_Command_SteeringAngle;
    attribute eeAccelerationSignal : Vehicle_ADAS_Driving_Command_Acceleration;
  }

  item def EECommandPacket {
    doc /*
     * The packet in which the Ethernet backbone carries the command frame
     * from the network side of the central computer to the zone controller of
     * the actuation ECU's zone: an IEEE 1722 packet, which carries a CAN
     * frame over Ethernet as one encapsulated bus frame (upstream.md). It
     * holds the one CAN FD frame as the network side built it. Nothing in the
     * packet changes or adds a part of the driving command. Its stream and
     * its address are set by the frame layout of the configuration
     * (gapEEConfigurationNamedByRole). A frame of the vehicle network, no
     * vehicle signal (MAP-EE-ZONE-ROUTE-PACKET).
     */
    item eeCarriedFrame : EECommandFrame;
  }

  /* ─── The ports: one item each, and the attachment that carries none ─── */

  port def EEBoundaryCommandIn {
    doc /*
     * The boundary interface of the vehicle network: each driving command as
     * the mw::com event of the driver-assistance increment gives it to the
     * network side of the central computer.
     */
    in item eeDrivingCommand : DrivingCommandEventPayload;
  }
  port def EECommandPacketOut {
    doc /*
     * The command packet leaving an element onto the Ethernet backbone, or
     * the backbone towards a zone controller.
     */
    out item eeCommandPacket : EECommandPacket;
  }
  port def EECommandPacketIn {
    doc /*
     * The command packet entering the Ethernet backbone or the zone
     * controller of the actuation ECU's zone.
     */
    in item eeCommandPacket : EECommandPacket;
  }
  port def EECommandFrameOut {
    doc /*
     * The command frame leaving an element onto a CAN FD bus or the direct
     * link, or such a link towards a node.
     */
    out item eeCommandFrame : EECommandFrame;
  }
  port def EECommandFrameIn {
    doc /*
     * The command frame entering a CAN FD bus, the direct link or the
     * actuation ECU.
     */
    in item eeCommandFrame : EECommandFrame;
  }
  port def EEAppliedCommandOut {
    doc /*
     * The applied steering angle and acceleration leaving the actuation ECU
     * for the vehicle.
     */
    out item eeAppliedCommand : EEActuationOutput;
  }
  port def EEAppliedCommandIn {
    doc /*
     * The applied steering angle and acceleration entering the vehicle's
     * steering, drive and brakes.
     */
    in item eeAppliedCommand : EEActuationOutput;
  }
  port def EENetworkAttachment {
    doc /*
     * The attachment of the other zone controller to a link, which carries no
     * item of the vehicle network: neither route passes it.
     */
  }

  /* ─── The nodes that carry the logical elements ─── */

  part def EECentralComputerNetworkSide :> PhysicalAllocationElement {
    doc /*
     * Carries the identity recorder and the command carrier of phase 7: the
     * network side of the central computer, the element of the vehicle
     * network on that computer. Its boundary interface is the port at which
     * it takes each driving command from the Eclipse S-CORE path on the
     * central computer (asmEEScoreCommandSource), as the mw::com event of the
     * driver-assistance increment gives it; it takes driving commands from
     * nowhere else (REQ-EE-002). When it takes a driving command it reads the
     * vehicle's clock. It puts the five parts, as it takes them, into one
     * CAN FD frame and computes none of the detection parts anew
     * (REQ-EE-007); no element sits between the take and the frame (owner
     * decision of 2026-11-26). By the route of the run, which the route
     * setting of the configuration sets, it sends the frame on the direct
     * link, or inside an IEEE 1722 packet on the Ethernet backbone. Before it
     * takes the first driving command of each run, it records the network
     * identity as the term of phase 5 names it (REQ-EE-010): the route of the
     * run, the commit with its difference, the SHA-256 of each file of the
     * configuration and each setting read from outside a file. The record is
     * a self-report of System 1, a file of the run that System 2 only reads.
     * Its software comes with the software realization
     * (gapEENodeSoftwareOpen). On the bench a node of the testbed stands in
     * for it.
     */
    port eeDrivingCommandIn : EEBoundaryCommandIn;
    port eeBackbonePacketOut : EECommandPacketOut;
    port eeDirectLinkFrameOut : EECommandFrameOut;
  }

  part def EEActuationZoneController :> PhysicalAllocationElement, VehicleComputeNode {
    doc /*
     * Carries the command carrier of phase 7 on the route through a zone
     * controller: the zone controller of the actuation ECU's zone, a gateway
     * between the Ethernet backbone and the CAN FD bus of its zone. It takes
     * each IEEE 1722 packet of the command's stream from the backbone and
     * puts the frame that the packet holds onto the CAN FD bus of its zone as
     * it is, by its routing entry of the configuration. It unpacks the frame
     * and repacks nothing, so it gives the actuation ECU the bytes that the
     * network side built and computes no detection part anew (REQ-EE-007). It
     * reads no clock for the driving command. Its typing as a vehicle compute
     * node of the execution environments claims no board, no operating system
     * and no qualification. Its software comes with the software realization
     * (gapEENodeSoftwareOpen). On the bench a node of the testbed stands in
     * for it.
     */
    port eePacketIn : EECommandPacketIn;
    port eeFrameOut : EECommandFrameOut;
  }

  part def EEActuationECU :> PhysicalAllocationElement, VehicleComputeNode {
    doc /*
     * Carries the actuation end of phase 7: the actuation ECU on the CAN FD
     * bus of its zone and at the end of the direct link, the last element
     * that a driving command reaches on both routes. It takes each command
     * frame from the CAN FD bus of its zone or from the direct link, by the
     * route of the run, and reads the vehicle's clock when one arrives. It
     * judges each by the term valid driving command: its check value over the
     * other parts as they arrive, its sequence count against the reference
     * count, and its issue time against the time of its arrival. It applies
     * each valid one and nothing in place of an invalid one, gives the
     * vehicle the steering angle and the acceleration of the last valid
     * driving command that it applied, and gives the stop response once more
     * than 200 ms pass on that clock with no valid driving command reaching
     * it (REQ-EE-006, REQ-EE-008, REQ-EE-009). The stop response needs no
     * vehicle speed. How it turns the steering angle and the acceleration
     * into the set-points of the vehicle's actuators is set with its software
     * (gapEENodeSoftwareOpen). Its typing as a vehicle compute node of the
     * execution environments claims no board, no operating system and no
     * qualification. On the bench a node of the testbed stands in for it.
     */
    port eeZoneBusFrameIn : EECommandFrameIn;
    port eeDirectLinkFrameIn : EECommandFrameIn;
    port eeAppliedCommandOut : EEAppliedCommandOut;
  }

  /* ─── The central computer and the other zone controller ─── */

  part def EECentralComputer :> VehicleComputeNode {
    doc /*
     * The central computer of the vehicle, declared here as a node of the
     * vehicle network. Its typing as a vehicle compute node of the execution
     * environments claims no board, no operating system and no qualification.
     * No platform layer is claimed either. Of it only its network side is an
     * element of the vehicle network; the rest of the computer, where the
     * command source and the Eclipse S-CORE path run, lies outside the
     * boundary and holds no part here. Its two ports, to the Ethernet
     * backbone and to the direct link, are those of its network side, to
     * which they are bound. The software that it runs and the layers that it
     * runs on come with the software realization (gapEENodeSoftwareOpen). The
     * realization of the HMI display declares the same computer for its own
     * needs (gapEECentralComputerHandover). On the bench a host of the
     * testbed stands in for it.
     */
    port eeBackbonePacketOut : EECommandPacketOut;
    port eeDirectLinkFrameOut : EECommandFrameOut;
    part eeNetworkSide : EECentralComputerNetworkSide;
    bind eeBackbonePacketOut = eeNetworkSide.eeBackbonePacketOut;
    bind eeDirectLinkFrameOut = eeNetworkSide.eeDirectLinkFrameOut;
  }

  part def EEOtherZoneController :> VehicleComputeNode {
    doc /*
     * The zone controller of the other zone: a gateway between the Ethernet
     * backbone and the CAN FD bus of its zone, as the topology of REQ-EE-001
     * holds it. Neither route passes it, so it carries no logical element:
     * the backbone gives it no command packet, and its attachments to the
     * backbone and to the CAN FD bus of its zone carry no item of the vehicle
     * network (REQ-EE-003). Its typing as a vehicle compute node of the
     * execution environments claims no board, no operating system and no
     * qualification. On the bench a node of the testbed stands in for it.
     */
    port eeBackboneAttachment : EENetworkAttachment;
    port eeZoneBusAttachment : EENetworkAttachment;
  }

  /* ─── The links: they carry the frame and compute nothing ─── */

  part def EEEthernetBackbone {
    doc /*
     * The Ethernet backbone between the central computer and the two zone
     * controllers, a link of the vehicle network on the route through a zone
     * controller. It carries each IEEE 1722 packet of the command's stream
     * from the network side of the central computer to the zone controller of
     * the actuation ECU's zone, as the network side sent it, and computes
     * nothing: it changes no part of the driving command and computes none
     * (REQ-EE-007). To the other zone controller it carries no command
     * packet: the destination address of the command's stream, which the
     * frame layout of the configuration sets, names only the zone controller
     * of the actuation ECU's zone. It receives no allocation; the mapping of
     * the route through a zone controller names it
     * (MAP-EE-ZONE-ROUTE-PACKET). On the bench a virtual link of the testbed
     * stands in for it.
     */
    port eePacketIn : EECommandPacketIn;
    port eePacketOut : EECommandPacketOut;
    port eeOtherZoneAttachment : EENetworkAttachment;
  }

  part def EEActuationZoneCANFDBus {
    doc /*
     * The CAN FD bus of the actuation ECU's zone, a link of the vehicle
     * network on the route through a zone controller. It carries each command
     * frame from the zone controller of its zone to the actuation ECU as the
     * zone controller put it on the bus, and computes nothing (REQ-EE-007).
     * It receives no allocation; the mapping of the zone's bus names it
     * (MAP-EE-ZONE-BUS-FRAME). On the bench a virtual CAN FD bus of the
     * testbed stands in for it.
     */
    port eeFrameIn : EECommandFrameIn;
    port eeFrameOut : EECommandFrameOut;
  }

  part def EEOtherZoneCANFDBus {
    doc /*
     * The CAN FD bus of the other zone, a link of the topology that
     * REQ-EE-001 holds. Neither route passes it: it carries no item of the
     * vehicle network and receives no allocation. On the bench a virtual
     * CAN FD bus of the testbed stands in for it.
     */
    port eeZoneControllerAttachment : EENetworkAttachment;
  }

  part def EEDirectCANFDLink {
    doc /*
     * The direct link from the central computer to the actuation ECU, which
     * passes no zone controller: a CAN FD link, the medium that phase 8
     * decides for it (owner decision of 2026-11-26). It carries each command
     * frame from the network side of the central computer to the actuation
     * ECU as the network side sent it, and computes nothing (REQ-EE-007). It
     * receives no allocation; the mapping of the direct route names it
     * (MAP-EE-DIRECT-LINK-FRAME). On the bench a virtual CAN FD link of the
     * testbed stands in for it.
     */
    port eeFrameIn : EECommandFrameIn;
    port eeFrameOut : EECommandFrameOut;
  }

  /* ─── The vehicle, as context ─── */

  part def EEActuatedVehicle {
    doc /*
     * The vehicle that the actuation ECU drives, as context: its steering,
     * drive and brakes take the steering angle and the acceleration that the
     * actuation ECU applies, and send nothing back. It realizes the context's
     * vehicle so that the applied command has an end; it is no element of the
     * vehicle network and carries no logical element. On the bench the
     * vehicle model of the testbed stands in for it.
     */
    port eeAppliedCommandIn : EEAppliedCommandIn;
  }

  /* ─── The vehicle network ─── */

  part def EEVehicleNetworkPhysicalSystem {
    doc /*
     * The physical realization of the vehicle network in the vehicle: the
     * central computer with its network side, the Ethernet backbone, the two
     * zone controllers, the CAN FD bus of each zone, the direct link and the
     * actuation ECU, in the one topology of REQ-EE-001, with the vehicle that
     * the actuation ECU drives as context. Of the central computer only its
     * network side is an element of the vehicle network. Each driving command
     * is one CAN FD frame: on the route through a zone controller it goes
     * from the network side over the Ethernet backbone inside an IEEE 1722
     * packet to the zone controller of the actuation ECU's zone, which puts
     * it on the CAN FD bus of its zone; on the direct route it goes over the
     * direct link. The actuation ECU gets the same bytes on both routes and
     * gives the vehicle the applied command. Nothing crosses back to the
     * network side, and no item of the vehicle network reaches the other zone
     * controller or its CAN FD bus. It carries REQ-EE-001 and REQ-EE-003 by
     * the elements that it places on the routes. No part here stands for an
     * element of the bench.
     */
    part eeCentralComputer : EECentralComputer;
    part eeEthernetBackbone : EEEthernetBackbone;
    part eeActuationZoneController : EEActuationZoneController;
    part eeOtherZoneController : EEOtherZoneController;
    part eeActuationZoneCANFDBus : EEActuationZoneCANFDBus;
    part eeOtherZoneCANFDBus : EEOtherZoneCANFDBus;
    part eeDirectCANFDLink : EEDirectCANFDLink;
    part eeActuationECU : EEActuationECU;
    part eeActuatedVehicle : EEActuatedVehicle;

    // The route through a zone controller.
    connection eeBackbonePacketFromCentralComputer
      connect eeCentralComputer.eeBackbonePacketOut to eeEthernetBackbone.eePacketIn;
    connection eeBackbonePacketToActuationZone
      connect eeEthernetBackbone.eePacketOut to eeActuationZoneController.eePacketIn;
    connection eeZoneBusFrameFromZoneController
      connect eeActuationZoneController.eeFrameOut to eeActuationZoneCANFDBus.eeFrameIn;
    connection eeZoneBusFrameToActuationECU
      connect eeActuationZoneCANFDBus.eeFrameOut to eeActuationECU.eeZoneBusFrameIn;

    // The direct route.
    connection eeDirectLinkFrameFromCentralComputer
      connect eeCentralComputer.eeDirectLinkFrameOut to eeDirectCANFDLink.eeFrameIn;
    connection eeDirectLinkFrameToActuationECU
      connect eeDirectCANFDLink.eeFrameOut to eeActuationECU.eeDirectLinkFrameIn;

    // The applied command, to the vehicle.
    connection eeAppliedCommandToVehicle
      connect eeActuationECU.eeAppliedCommandOut to eeActuatedVehicle.eeAppliedCommandIn;

    // The other zone, on neither route: attachments that carry no item.
    connection eeOtherZoneOnBackbone
      connect eeEthernetBackbone.eeOtherZoneAttachment to eeOtherZoneController.eeBackboneAttachment;
    connection eeOtherZoneBusOnZoneController
      connect eeOtherZoneController.eeZoneBusAttachment to eeOtherZoneCANFDBus.eeZoneControllerAttachment;
  }

  part eeVehicleNetworkPhysicalSystem : EEVehicleNetworkPhysicalSystem {
    doc /*
     * The vehicle network as the views draw it: the one usage of the physical
     * definition. It depicts the realization of the context's vehicleNetwork
     * and is bound to nothing.
     */
  }

  /* ─── Logical-to-physical allocations (allocatedTo) ─── */

  allocation eeRecorderToNetworkSide
    allocate EEVehicleNetworkLogicalSystem::eeIdentityRecorder
    to eeVehicleNetworkPhysicalSystem::eeCentralComputer::eeNetworkSide;
  allocation eeCarrierToNetworkSide
    allocate EEVehicleNetworkLogicalSystem::eeCommandCarrier
    to eeVehicleNetworkPhysicalSystem::eeCentralComputer::eeNetworkSide;
  allocation eeCarrierToActuationZoneController
    allocate EEVehicleNetworkLogicalSystem::eeCommandCarrier
    to eeVehicleNetworkPhysicalSystem::eeActuationZoneController;
  allocation eeActuationEndToActuationECU
    allocate EEVehicleNetworkLogicalSystem::eeActuationEnd
    to eeVehicleNetworkPhysicalSystem::eeActuationECU;

  /* ─── The topology and route requirements, carried by the realization that places the routes ─── */

  dependency eePhysicalSystemCarriesBothRoutesInOneTopology
    from EEVehicleNetworkPhysicalSystem to reqBothRoutesInOneTopology;
  dependency eePhysicalSystemCarriesCommandsOnlyOnTheirRoute
    from EEVehicleNetworkPhysicalSystem to reqCommandsOnlyOnTheirRoute;

  /* ─── Signal mappings: one per crossing, each with its record ─── */

  allocation eeScoreCommandMapping : SystemToSoftwareSignalMappingCandidate
    allocate EEVehicleNetworkLogicalSystem::eeCommandCarrier
    to eeVehicleNetworkPhysicalSystem.eeCentralComputer.eeNetworkSide.eeDrivingCommandIn {
    item <'MAP-EE-SCORE-COMMAND'> eeScoreCommandMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The driving command from the mw::com event of the driver-assistance
       * increment into the network side of the central computer, at the
       * boundary interface. The item is that increment's payload, unchanged.
       */
      attribute :>> semanticSource = "the driving command of the driver-assistance increment, typed at the port by its payload DrivingCommandEventPayload, whose steering angle and acceleration are the DE4SDV_VSS_Extensions signals Vehicle_ADAS_Driving_Command_SteeringAngle and Vehicle_ADAS_Driving_Command_Acceleration; the issue time, the sequence count and the check value are protocol fields, no vehicle signal";
      attribute :>> softwareContractArtifact = "the mw::com event of the driving command that the vehicle interface of the driver-assistance increment publishes on the Eclipse S-CORE path, taken by the network side of the central computer at the boundary interface, candidate";
      attribute :>> softwareContractMessage = "DrivingCommandEventPayload, one event per driving command, candidate";
      attribute :>> softwareContractField = "steeringAngle, acceleration, issueTime, sequenceCount, checkValue, exact";
      attribute :>> dataTypeAndUnit = "steeringAngle in degrees, positive to the left; acceleration in m/s², negative to decelerate; issueTime in seconds on the vehicle's clock; sequenceCount an unsigned 32-bit count from 1 in each run; checkValue the CRC-32 over the other parts";
      attribute :>> timingQualityAndState = "the driving commands at the rate the source gives them; the network side reads the vehicle's clock when it takes each one, the time from which the 50 ms of REQ-EE-005 count; on the bench the testbed's simulation clock stands in";
      attribute :>> transformationRule = "none: the network side takes each part as the event gives it and puts it into the command frame unchanged";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "realize the take of the event on the network side with the software realization, then bring the verification cases of REQ-EE-002 and REQ-EE-005 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; gap gapEENodeSoftwareOpen and framing assumption asmEEScoreCommandSource";
    }
  }

  allocation eeZoneRoutePacketMapping : SystemToSoftwareSignalMappingCandidate
    allocate EEVehicleNetworkLogicalSystem::eeCommandCarrier
    to eeVehicleNetworkPhysicalSystem.eeCentralComputer.eeNetworkSide.eeBackbonePacketOut {
    item <'MAP-EE-ZONE-ROUTE-PACKET'> eeZoneRoutePacketMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The command frame inside an IEEE 1722 packet, from the network side
       * of the central computer over the Ethernet backbone to the zone
       * controller of the actuation ECU's zone, on the route through a zone
       * controller. A frame of the vehicle network, no vehicle signal.
       */
      attribute :>> semanticSource = "the command frame as the network side built it, held unchanged in a packet of the backbone: a frame of the vehicle network, no vehicle signal; the steering angle and the acceleration in it keep their typing by the two DE4SDV_VSS_Extensions signals of the frame";
      attribute :>> softwareContractArtifact = "the communication matrix of the vehicle network, by role: the frame layout of the command frame and the IEEE 1722 stream that carries it on the backbone to the zone controller of the actuation ECU's zone, candidate";
      attribute :>> softwareContractMessage = "EECommandPacket, one per driving command on the route through a zone controller, holding one EECommandFrame, candidate";
      attribute :>> softwareContractField = "eeCarriedFrame, the whole frame with its five parts and the two signal values, exact; the fields of the packet around it are set by the stream of the configuration";
      attribute :>> dataTypeAndUnit = "the bytes of the frame as the network side built them; the units of the parts as at the boundary interface";
      attribute :>> timingQualityAndState = "one packet per driving command on the route through a zone controller; no element reads a clock on the backbone; the 50 ms of REQ-EE-005 count from the take to the arrival at the actuation ECU";
      attribute :>> transformationRule = "the packet holds the frame as the network side built it; nothing on the backbone changes or computes a part (REQ-EE-007)";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "set the frame layout and the stream in the configuration, then bring the verification cases of REQ-EE-003, REQ-EE-004 and REQ-EE-007 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; gap gapEEConfigurationNamedByRole";
    }
  }

  allocation eeZoneBusFrameMapping : SystemToSoftwareSignalMappingCandidate
    allocate EEVehicleNetworkLogicalSystem::eeCommandCarrier
    to eeVehicleNetworkPhysicalSystem.eeActuationZoneController.eeFrameOut {
    item <'MAP-EE-ZONE-BUS-FRAME'> eeZoneBusFrameMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The command frame from the zone controller of the actuation ECU's
       * zone onto the CAN FD bus of its zone, as the packet held it. A frame
       * of the vehicle network; the steering angle and the acceleration in it
       * are typed by the two signals of the frame.
       */
      attribute :>> semanticSource = "the command frame as the network side built it, typed at the port by EECommandFrame, whose eeSteeringAngleSignal and eeAccelerationSignal are the DE4SDV_VSS_Extensions signals Vehicle_ADAS_Driving_Command_SteeringAngle and Vehicle_ADAS_Driving_Command_Acceleration; the issue time, the sequence count and the check value are protocol fields, no vehicle signal";
      attribute :>> softwareContractArtifact = "the communication matrix of the vehicle network, by role: the frame layout of the command frame on the CAN FD bus of the actuation ECU's zone, and the routing entry by which the zone controller puts the frames of the stream on that bus, candidate";
      attribute :>> softwareContractMessage = "EECommandFrame, one CAN FD frame per driving command, candidate";
      attribute :>> softwareContractField = "the five parts and the two signal values as the network side built them, exact";
      attribute :>> dataTypeAndUnit = "eeSteeringAngleSignal in degrees, the value of steeringAngle; eeAccelerationSignal in m/s², the value of acceleration; the issue time, the sequence count and the check value as at the boundary interface";
      attribute :>> timingQualityAndState = "one frame per packet that reaches the zone controller; the zone controller reads no clock for the driving command";
      attribute :>> transformationRule = "the zone controller unpacks: the frame leaves it with the bytes that the packet held, no part repacked and none computed anew (REQ-EE-007)";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "set the routing entry of the zone controller in the configuration, then bring the verification cases of REQ-EE-004 and REQ-EE-007 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; gaps gapEEConfigurationNamedByRole and gapEENodeSoftwareOpen";
    }
  }

  allocation eeDirectLinkFrameMapping : SystemToSoftwareSignalMappingCandidate
    allocate EEVehicleNetworkLogicalSystem::eeCommandCarrier
    to eeVehicleNetworkPhysicalSystem.eeCentralComputer.eeNetworkSide.eeDirectLinkFrameOut {
    item <'MAP-EE-DIRECT-LINK-FRAME'> eeDirectLinkFrameMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The command frame from the network side of the central computer over
       * the direct link to the actuation ECU, on the direct route. A frame of
       * the vehicle network; the steering angle and the acceleration in it
       * are typed by the two signals of the frame.
       */
      attribute :>> semanticSource = "the command frame as the network side built it, typed at the port by EECommandFrame, whose eeSteeringAngleSignal and eeAccelerationSignal are the DE4SDV_VSS_Extensions signals Vehicle_ADAS_Driving_Command_SteeringAngle and Vehicle_ADAS_Driving_Command_Acceleration; the issue time, the sequence count and the check value are protocol fields, no vehicle signal";
      attribute :>> softwareContractArtifact = "the communication matrix of the vehicle network, by role: the frame layout of the command frame on the direct link, candidate";
      attribute :>> softwareContractMessage = "EECommandFrame, one CAN FD frame per driving command, candidate";
      attribute :>> softwareContractField = "steeringAngle, acceleration, issueTime, sequenceCount, checkValue, eeSteeringAngleSignal, eeAccelerationSignal, exact; the layout of their bytes is set by the frame layout";
      attribute :>> dataTypeAndUnit = "eeSteeringAngleSignal in degrees, the value of steeringAngle; eeAccelerationSignal in m/s², the value of acceleration; the issue time, the sequence count and the check value as at the boundary interface";
      attribute :>> timingQualityAndState = "one frame per driving command on the direct route; no element reads a clock on the direct link";
      attribute :>> transformationRule = "eeSteeringAngleSignal = steeringAngle in degrees and eeAccelerationSignal = acceleration in m/s², each as taken; the other parts as taken; nothing on the direct link changes or computes a part (REQ-EE-007)";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "set the frame layout in the configuration, then bring the verification cases of REQ-EE-003, REQ-EE-004 and REQ-EE-007 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; gap gapEEConfigurationNamedByRole";
    }
  }

  allocation eeActuationFrameMapping : SystemToSoftwareSignalMappingCandidate
    allocate EEVehicleNetworkLogicalSystem::eeActuationEnd
    to eeVehicleNetworkPhysicalSystem::eeActuationECU {
    item <'MAP-EE-ACTUATION-FRAME'> eeActuationFrameMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The command frame as the actuation ECU takes it, from the CAN FD bus
       * of its zone or from the direct link, by the route of the run, with
       * the same bytes on both routes. The owning allocation targets the
       * element, which the frame enters at two ports.
       */
      attribute :>> semanticSource = "the command frame of the vehicle network, typed at the two ports of the actuation ECU by EECommandFrame, whose two signal values are the DE4SDV_VSS_Extensions command signals; the issue time, the sequence count and the check value are protocol fields, no vehicle signal";
      attribute :>> softwareContractArtifact = "the communication matrix of the vehicle network, by role: the frame layout of the command frame as the actuation ECU reads it, candidate";
      attribute :>> softwareContractMessage = "EECommandFrame, one CAN FD frame per driving command, candidate";
      attribute :>> softwareContractField = "the five parts and the two signal values, exact";
      attribute :>> dataTypeAndUnit = "eeSteeringAngleSignal in degrees, the value of steeringAngle; eeAccelerationSignal in m/s², the value of acceleration; the issue time, the sequence count and the check value as at the boundary interface";
      attribute :>> timingQualityAndState = "the actuation ECU reads the vehicle's clock when a frame arrives; a frame is valid only with an issue time no more than 100 ms before that time, and the stop response starts once more than 200 ms pass with no valid driving command; on the bench the testbed's simulation clock stands in";
      attribute :>> transformationRule = "the actuation ECU judges each frame by the term valid driving command: the check value over the other parts as they arrive, the sequence count against the reference count, the issue time against the time of arrival; it computes no part anew";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "realize the check in the software of the actuation ECU, then bring the verification cases of REQ-EE-004, REQ-EE-006, REQ-EE-008 and REQ-EE-009 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; gap gapEENodeSoftwareOpen";
    }
  }

  allocation eeAppliedCommandMapping : SystemToSoftwareSignalMappingCandidate
    allocate EEVehicleNetworkLogicalSystem::eeActuationEnd
    to eeVehicleNetworkPhysicalSystem.eeActuationECU.eeAppliedCommandOut {
    item <'MAP-EE-APPLIED-COMMAND'> eeAppliedCommandMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The applied command from the actuation ECU to the vehicle's steering,
       * drive and brakes: the steering angle and the acceleration of the last
       * valid driving command that it applied, or those of the stop response.
       * It carries no detection part.
       */
      attribute :>> semanticSource = "the steering angle and the acceleration that the actuation ECU gives the vehicle, typed by the item of phase 6, EEActuationOutput, with its quantities; they are the values that the frame carries as Vehicle_ADAS_Driving_Command_SteeringAngle and Vehicle_ADAS_Driving_Command_Acceleration, or those of the stop response";
      attribute :>> softwareContractArtifact = "the actuator interfaces of the vehicle's steering, drive and brakes, by role, set with the design of the actuation ECU; on the bench the vehicle model of the testbed stands in for them, candidate";
      attribute :>> softwareContractMessage = "EEActuationOutput, the applied command, candidate";
      attribute :>> softwareContractField = "steeringAngle, acceleration, exact; the set-points of the actuators are set with the software of the actuation ECU";
      attribute :>> dataTypeAndUnit = "steeringAngle in degrees, positive to the left; acceleration in m/s², negative to decelerate";
      attribute :>> timingQualityAndState = "the actuation ECU applies each valid driving command at the time at which it arrives, and gives the stop response from later than 200 ms and no later than 300 ms after the last valid driving command reached it, or after the run started when none did, until the run ends";
      attribute :>> transformationRule = "the steering angle and the acceleration of the last valid driving command, as it carried them; in the stop response a deceleration of 4 m/s² and the steering angle of the last valid driving command, or 0° when it applied none";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "set the actuator interfaces with the design of the actuation ECU, then bring the verification cases of REQ-EE-006, REQ-EE-008 and REQ-EE-009 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; gap gapEENodeSoftwareOpen and framing gap gapEEBenchPlatform";
    }
  }

  allocation eeIdentityRecordMapping : SystemToSoftwareSignalMappingCandidate
    allocate EEVehicleNetworkLogicalSystem::eeIdentityRecorder
    to eeVehicleNetworkPhysicalSystem.eeCentralComputer.eeNetworkSide {
    item <'MAP-EE-IDENTITY-RECORD'> eeIdentityRecordMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The record of the network identity that the network side of the
       * central computer writes before it takes the first driving command of
       * each run, a file of the run that System 2 only reads. A record of
       * files and settings, no vehicle signal. The owning allocation targets
       * the element: the record crosses no port.
       */
      attribute :>> semanticSource = "the network identity of the run as the term of phase 5 names it: a record of files and settings, no vehicle signal";
      attribute :>> softwareContractArtifact = "the record file of the network identity of each run, written on the central computer, candidate";
      attribute :>> softwareContractMessage = "one record per run, written before the first driving command of the run is taken, candidate";
      attribute :>> softwareContractField = "the route of the run, the commit of the DE4SDV repository with the difference, the SHA-256 of each file of the configuration, and each setting that the vehicle network reads from outside a file, as read; the files are named by role until the implementation names them";
      attribute :>> dataTypeAndUnit = "strings; each SHA-256 in hexadecimal";
      attribute :>> timingQualityAndState = "once per run, before the network side takes the first driving command of the run";
      attribute :>> transformationRule = "none: each value as read or hashed";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "name the files of the configuration with the implementation, then bring the verification cases of REQ-EE-010 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; gaps gapEEConfigurationNamedByRole and gapEENodeSoftwareOpen";
    }
  }

  /* ─── What phase 8 settled on the framing's records ─── */

  comment eePhase8ActuationEndPlaced about gapEEActuationEnd
    /*
     * Placed, not observed: the actuation ECU holds the check, the
     * application and the stop response of the actuation end. Each driving
     * command with its issue time, sequence count and check value is one
     * CAN FD frame (owner decision of 2026-11-26), and the zone controller of
     * the actuation ECU's zone unpacks the frame from its packet and repacks
     * nothing, so the detection reaches from the network side of the central
     * computer to the actuation ECU on both routes. The stop response needs
     * no vehicle speed. Still open: how the actuation ECU turns the steering
     * angle and the acceleration into the set-points of the vehicle's
     * actuators, and whether that needs a vehicle speed
     * (gapEENodeSoftwareOpen). The adapters of the driving benches stay as
     * they are.
     */

  comment eePhase8StackBoundaryPartlySettled about gapEEStackAndNetworkBoundary
    /*
     * Settled in part: the central computer, the two zone controllers and the
     * actuation ECU are typed as vehicle compute nodes of the execution
     * environments of the product line, a typing that claims no board, no
     * operating system, no qualification and no candidate of that family; the
     * links are not. The Ethernet backbone of this realization is its own and
     * reuses no port of VehicleNetworkBoundary of the AAOS SDV middleware
     * boundary. How the network side relates to the SoC and the hardware
     * layer of the platform stack, and the layers that each node runs on,
     * stay open for the software realization of this phase
     * (gapEENodeSoftwareOpen).
     */

  comment eePhase8BoundaryInterfacePlaced about asmEEScoreCommandSource
    /*
     * Placed, not observed: the boundary interface is the port of the network
     * side of the central computer at which it takes the mw::com event of the
     * driving command of the driver-assistance increment. What on the central
     * computer gives that event to the network side is placed with the
     * software realization of this phase. The readiness probe still tests
     * first that the Eclipse S-CORE path hands the driving command to the
     * network side.
     */

  comment eePhase8TestbedQuestionsAsked about gapEEBenchPlatform
    /*
     * Not settled here: the testbed stays to be chosen. This realization asks
     * of it, before phase 10, whether its buses and its direct link carry
     * CAN FD frames; whether it gives every element the one clock of the
     * virtual vehicle and records each driving command at each element with
     * its simulation time; and whether it makes one fault on one link of a
     * route at a time. On the testbed a node, a virtual link or a virtual
     * CAN FD bus stands in for each element of this realization.
     */

  /* ─── The gaps of the realization ─── */

  part gapEECentralComputerHandover : IncrementGap {
    doc /*
     * The realization of the HMI display,
     * DE4SDV_HmiDisplayPhysicalSoftwareRealization, declares the central
     * computer too, as HmiDisplayCentralComputer with the VMs that it hosts,
     * and its doc says that it imports the declaration of an E/E realization
     * once one exists. This realization declares the central computer as a
     * node, the declaration that the realization of the HMI display is to
     * import. The realization of the HMI display keeps its own declaration
     * until the method can place software on a node, and its file is changed
     * in its own increment, not here. Until then the model holds two
     * declarations of one computer.
     */
  }

  part gapEEConfigurationNamedByRole : IncrementGap {
    doc /*
     * REQ-EE-010 reads the network identity over the files of the
     * configuration that phase 8 names. This realization names them by role
     * only: the frame layout of the command frame, with the IEEE 1722 stream
     * of its packet; the routing entry of the zone controller of the
     * actuation ECU's zone; the route setting of the network side; and the
     * files that set the software of each element. Their paths come with the
     * implementation, so phase 8 does not name the files yet, and REQ-EE-010
     * cannot be verified as worded until they are named, which is due before
     * phase 10.
     */
  }

  part gapEENodeSoftwareOpen : IncrementGap {
    doc /*
     * This realization places the logical elements on the nodes and the
     * command frame on the links; it places no software. The software of the
     * network side of the central computer, which takes the event and builds
     * the frame, of the zone controller, which unpacks it, and of the
     * actuation ECU, which checks and applies it, the layers that each node
     * runs on, and the typing by VSS at their software ports come with the
     * software realization of this phase, after the change to the method that
     * relates software to a node. How the identity recorder reads the
     * software and the configuration of the zone controller and of the
     * actuation ECU is set there too. If the recorder reads them over the
     * vehicle network, that reading is an exchange between logical elements,
     * which phase 7 lacks: there the identity recorder exchanges nothing. The
     * owner then decides between an amendment of phase 7 and a narrower
     * REQ-EE-010.
     */
  }

  /* ─── Concerns and views of the phase ─── */

  view eeVehicleNetworkPhysicalStructureView {
    viewpoint eePhysicalStructureViewpoint : PhysicalStructureDefinitionViewpoint {
      frame eeTopologyStructureConcern;
    }
    expose eeVehicleNetworkPhysicalSystem;
    expose eeVehicleNetworkPhysicalSystem::eeCentralComputer;
    expose eeVehicleNetworkPhysicalSystem::eeCentralComputer::eeNetworkSide;
    expose eeVehicleNetworkPhysicalSystem::eeEthernetBackbone;
    expose eeVehicleNetworkPhysicalSystem::eeActuationZoneController;
    expose eeVehicleNetworkPhysicalSystem::eeOtherZoneController;
    expose eeVehicleNetworkPhysicalSystem::eeActuationZoneCANFDBus;
    expose eeVehicleNetworkPhysicalSystem::eeOtherZoneCANFDBus;
    expose eeVehicleNetworkPhysicalSystem::eeDirectCANFDLink;
    expose eeVehicleNetworkPhysicalSystem::eeActuationECU;
    expose eeVehicleNetworkPhysicalSystem::eeActuatedVehicle;
    filter not (@ SysML::AllocationUsage);
    filter not (@ SysML::BindingConnectorAsUsage);
    render asTreeDiagram;
  }

  concern eeVehicleNetworkPhysicalAllocationConcern : PhysicalLogicalMappingConcern {
    doc /*
     * System architects and verification engineers need each logical element
     * of phase 7 allocated to the nodes of the vehicle network that carry it,
     * and each node that carries one: the network side of the central
     * computer, which carries the identity recorder and the command carrier,
     * the zone controller of the actuation ECU's zone, which carries the
     * command carrier, and the actuation ECU, which carries the actuation
     * end. The links, the other zone controller and its CAN FD bus carry no
     * logical element. An allocation is a responsibility assignment, no
     * deployment or runtime claim.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder verificationEngineer : VerificationEngineer;
  }

  view eeVehicleNetworkPhysicalLogicalMappingView : MVD::MatrixView {
    viewpoint eePhysicalLogicalMappingViewpoint : PhysicalLogicalMappingViewpoint {
      frame eeVehicleNetworkPhysicalAllocationConcern;
    }
    view :>> rowView {
      expose EEVehicleNetworkLogicalSystem::eeIdentityRecorder;
      expose EEVehicleNetworkLogicalSystem::eeCommandCarrier;
      expose EEVehicleNetworkLogicalSystem::eeActuationEnd;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> columnView {
      expose eeVehicleNetworkPhysicalSystem::eeCentralComputer::eeNetworkSide;
      expose eeVehicleNetworkPhysicalSystem::eeActuationZoneController;
      expose eeVehicleNetworkPhysicalSystem::eeActuationECU;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> cellView {
      expose DE4SDV_EEArchitecturePhysicalEERealization::*;
      attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;
    }
  }

  view eeVehicleNetworkRouteExchangeView {
    doc /*
     * The two routes of a driving command inside the vehicle network
     * (eeCommandRouteExchangeConcern) and the item on each part of its way
     * (eeCommandItemConcern): from the network side of the central computer,
     * the command frame inside an IEEE 1722 packet over the Ethernet backbone
     * to the zone controller of the actuation ECU's zone, and as the frame on
     * the CAN FD bus of that zone to the actuation ECU; or the frame over the
     * direct link to the actuation ECU; and the applied command from the
     * actuation ECU to the vehicle. The other zone controller and its CAN FD
     * bus are drawn with their attachments, which carry no item. Each edge
     * joins two ports, and each port definition on a route carries the one
     * item that its exchange moves; the attachments carry none. The boundary
     * interface of the network side takes the payload of the
     * driver-assistance increment; nothing is drawn into it here, since the
     * Eclipse S-CORE path on the central computer is placed with the software
     * realization.
     */
    viewpoint eeRouteExchangeViewpoint : PhysicalInternalExchangeViewpoint {
      frame eeCommandRouteExchangeConcern;
      frame eeCommandItemConcern;
    }
    expose eeVehicleNetworkPhysicalSystem;
    expose eeVehicleNetworkPhysicalSystem::eeCentralComputer;
    expose eeVehicleNetworkPhysicalSystem::eeCentralComputer::eeBackbonePacketOut;
    expose eeVehicleNetworkPhysicalSystem::eeCentralComputer::eeDirectLinkFrameOut;
    expose eeVehicleNetworkPhysicalSystem::eeCentralComputer::eeNetworkSide;
    expose eeVehicleNetworkPhysicalSystem::eeCentralComputer::eeNetworkSide::eeDrivingCommandIn;
    expose eeVehicleNetworkPhysicalSystem::eeCentralComputer::eeNetworkSide::eeBackbonePacketOut;
    expose eeVehicleNetworkPhysicalSystem::eeCentralComputer::eeNetworkSide::eeDirectLinkFrameOut;
    expose eeVehicleNetworkPhysicalSystem::eeEthernetBackbone;
    expose eeVehicleNetworkPhysicalSystem::eeEthernetBackbone::eePacketIn;
    expose eeVehicleNetworkPhysicalSystem::eeEthernetBackbone::eePacketOut;
    expose eeVehicleNetworkPhysicalSystem::eeEthernetBackbone::eeOtherZoneAttachment;
    expose eeVehicleNetworkPhysicalSystem::eeActuationZoneController;
    expose eeVehicleNetworkPhysicalSystem::eeActuationZoneController::eePacketIn;
    expose eeVehicleNetworkPhysicalSystem::eeActuationZoneController::eeFrameOut;
    expose eeVehicleNetworkPhysicalSystem::eeOtherZoneController;
    expose eeVehicleNetworkPhysicalSystem::eeOtherZoneController::eeBackboneAttachment;
    expose eeVehicleNetworkPhysicalSystem::eeOtherZoneController::eeZoneBusAttachment;
    expose eeVehicleNetworkPhysicalSystem::eeActuationZoneCANFDBus;
    expose eeVehicleNetworkPhysicalSystem::eeActuationZoneCANFDBus::eeFrameIn;
    expose eeVehicleNetworkPhysicalSystem::eeActuationZoneCANFDBus::eeFrameOut;
    expose eeVehicleNetworkPhysicalSystem::eeOtherZoneCANFDBus;
    expose eeVehicleNetworkPhysicalSystem::eeOtherZoneCANFDBus::eeZoneControllerAttachment;
    expose eeVehicleNetworkPhysicalSystem::eeDirectCANFDLink;
    expose eeVehicleNetworkPhysicalSystem::eeDirectCANFDLink::eeFrameIn;
    expose eeVehicleNetworkPhysicalSystem::eeDirectCANFDLink::eeFrameOut;
    expose eeVehicleNetworkPhysicalSystem::eeActuationECU;
    expose eeVehicleNetworkPhysicalSystem::eeActuationECU::eeZoneBusFrameIn;
    expose eeVehicleNetworkPhysicalSystem::eeActuationECU::eeDirectLinkFrameIn;
    expose eeVehicleNetworkPhysicalSystem::eeActuationECU::eeAppliedCommandOut;
    expose eeVehicleNetworkPhysicalSystem::eeActuatedVehicle;
    expose eeVehicleNetworkPhysicalSystem::eeActuatedVehicle::eeAppliedCommandIn;
    expose eeVehicleNetworkPhysicalSystem::eeBackbonePacketFromCentralComputer;
    expose eeVehicleNetworkPhysicalSystem::eeBackbonePacketToActuationZone;
    expose eeVehicleNetworkPhysicalSystem::eeZoneBusFrameFromZoneController;
    expose eeVehicleNetworkPhysicalSystem::eeZoneBusFrameToActuationECU;
    expose eeVehicleNetworkPhysicalSystem::eeDirectLinkFrameFromCentralComputer;
    expose eeVehicleNetworkPhysicalSystem::eeDirectLinkFrameToActuationECU;
    expose eeVehicleNetworkPhysicalSystem::eeAppliedCommandToVehicle;
    expose eeVehicleNetworkPhysicalSystem::eeOtherZoneOnBackbone;
    expose eeVehicleNetworkPhysicalSystem::eeOtherZoneBusOnZoneController;
    filter not (@ SysML::AllocationUsage);
    filter not (@ SysML::InterfaceUsage);
    attribute depth = -1;
    attribute showAnnotationRows = false;
    render asInterconnectionDiagram;
  }
}
