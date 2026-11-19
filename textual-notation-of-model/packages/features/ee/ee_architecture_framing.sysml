/*
 * DE4SDV E/E architecture: Phase 0 framing and the Phase 1 concerns only.
 * One increment spans framing, realization and verification on a virtual
 * vehicle. The framing asserts no implementation, no runtime result, no
 * product-line admission and no compliance.
 */
package DE4SDV_EEArchitectureFraming {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_IncrementWorkflow::IncrementCharter;
  private import DE4SDV_MethodProcess::*;
  private import DE4SDV_MethodViewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import SAF_Viewpoints::*;
  private import Views::*;

  part def EEArchitectureIncrement :> EngineeringIncrement;

  part <'INC-EE-001'> eeArchitectureIncrement : EEArchitectureIncrement {
    doc /*
     * Owner-requested increment on a first part of the electrical/electronic
     * (E/E) architecture of the product line: the vehicle network between the
     * central computer and an actuation ECU on CAN. The owner decided on
     * 2026-11-17 to start this increment and to frame it now, and on
     * 2026-11-18 to carry out Phases 1 to 3 of this increment before the
     * baseline of the driver-assistance increment, INC-DRIVING-002, whose
     * driving command it carries. Phase 4 onward and the testbed with its
     * readiness probe wait for that baseline and for a further decision of
     * the owner. This framing changes neither the platform stack, the
     * governed product-line scope nor another increment. All phases retain
     * this identity. This package holds Phase 0 and the Phase 1 concerns.
     */
  }

  requirement eeArchitectureProblem : ProblemStatement {
    subject eeArchitectureSubject : EEArchitectureIncrement;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder safetyExpert : SafetyExpert;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
    doc /*
     * The model describes one SoC as the compute of a member product and
     * names the vehicle network only as a boundary. The platform stack
     * describes one SoC with a main side and an optional guest side, and
     * keeps abstract its hardware layer, which names SoC, MCU, sensors and
     * actuators. The boundary model of the AAOS SDV middleware gives the
     * vehicle network two Ethernet ports; its text names a VLAN-capable
     * switch, an optional DMZ, a telematics control unit and legacy ECUs, and
     * models none of them, nor any zone, bus or route. The hand-off from the
     * vehicle interface to the brake ECU is a recorded open obligation of the
     * AEBS realization. In the benches the actuation is a simulator or a
     * simulator client on a bench host, not an ECU; in the driving benches it
     * is an actuation adapter on the host that runs Eclipse S-CORE. Nothing
     * in the model says how a command reaches an actuator across a vehicle
     * network, or what happens when that network fails.
     */
  }

  part eeArchitectureQuestion : IncrementEngineeringQuestion {
    doc /*
     * When the actuation is an ECU on a CAN bus at the edge of a zonal
     * vehicle network, does the path of the driving command keep, across that
     * network, the properties that the model asks of the command paths of
     * earlier increments, on each of two routes: through the Ethernet
     * backbone and a zone controller, and over a direct link from the central
     * computer? The properties are a command whose loss, delay, repetition or
     * corruption the actuation can detect, which REQ-DRIVING-039 asks on the
     * Eclipse S-CORE path; a stop response when no valid command has reached
     * the actuation for 200 ms of simulation time, which REQ-DRIVING-028 asks
     * of the closed-loop driving system; and no uncontrolled emergency
     * intervention command from a failure of the non-safety middleware
     * integration path, which REQ-MW-006 asks of each member product. For the
     * driving command, the driver-assistance increment places a share of that
     * requirement at the actuation: to apply no command that the actuation
     * rejects. The model asks none of these properties of a vehicle network.
     * Phase 5 derives the requirements of this increment from them. A verdict
     * for each requirement of the increment on each route, on a virtual
     * vehicle, answers this. A run in which commands arrive does not.
     */
  }

  part eeArchitectureDecision : IncrementLifecycleDecision {
    doc /*
     * Decide whether the product line admits this zonal vehicle network, with
     * the route that the driving command takes, as its reference vehicle
     * network, from which later topologies vary, admits it with named
     * changes, or does not admit it. The decision rests on executed cases
     * with a pass or a fail for each requirement of the increment on each
     * route. A fail is a result to record. It is no reason to change a
     * scenario or a criterion until the network passes.
     */
  }

  part def EEVehicleNetworkSystem {
    doc /*
     * Candidate System 1 boundary. In: the driving command of the
     * driver-assistance increment, which its source on the central computer
     * gives. Inside: the vehicle network of one topology, with the network
     * side of the central computer, one Ethernet backbone, two zone
     * controllers that act as gateways between the backbone and CAN, a CAN
     * bus in each zone, and a direct link from the central computer to the
     * actuation ECU that passes no zone controller, as the other route; and
     * an actuation ECU on CAN that receives the command and acts on it. Out:
     * the command that the actuation ECU applies. Two parts of System 1 are
     * outside this boundary, and neither is an enabling system: the source of
     * the driving command on the central computer, and the Eclipse S-CORE
     * path that carries the command to the vehicle network. Phases 2 and 3
     * add the actors, the interfaces and the product-line classification, and
     * Phases 6 to 8 decide the realization, with the medium of the direct
     * link. The vehicle network is not a member product: this increment
     * admits no member to the governed product-line scope.
     */
  }
  part eeVehicleNetworkSystem : EEVehicleNetworkSystem;

  part eeArchitectureScope : IncrementScope {
    doc /*
     * Whether the path of the driving command keeps, across a zonal vehicle
     * network, the properties that the model asks of the command paths of
     * earlier increments, on each of two routes: one topology that holds both
     * routes, with one central computer, two zone controllers and one
     * Ethernet backbone, one flow, the driving command down to the actuation
     * ECU, for one configuration and with at most ten requirements. Phase 5
     * derives those requirements from the needs of Phase 4 and from
     * REQ-DRIVING-028, REQ-DRIVING-039 and REQ-MW-006. The evidence comes
     * from the replay of a recorded command stream on a virtual vehicle, in
     * Phase 10 of this same increment. A time limit of a requirement counts
     * on the clock of the virtual vehicle, and a verdict on it is no timing
     * claim for a vehicle network. A readiness probe comes before the
     * architecture rests on what it tests. Implementation is not part of this
     * framing slice.
     */
  }

  part eeTopologyInScope : InScopeItem {
    doc /*
     * One topology of the vehicle network: one central computer, two zone
     * controllers, one Ethernet backbone between them, a CAN bus at the edge
     * of each zone, and a direct link from the central computer to the
     * actuation ECU that passes no zone controller.
     */
  }
  part eeCommandFlowInScope : InScopeItem {
    doc /*
     * The driving command of the driver-assistance increment, down from its
     * source on the central computer to an actuation ECU on CAN.
     */
  }
  part eeCommandRouteInScope : InScopeItem {
    doc /*
     * Two routes of the driving command to the actuation ECU: through the
     * Ethernet backbone and a zone controller, and over the direct link.
     */
  }
  part eeNetworkFaultsInScope : InScopeItem {
    doc /*
     * Faults of the vehicle network on the route of the command: one link of
     * that route that goes down, and a command that is lost, delayed,
     * repeated or corrupted on its way.
     */
  }
  part eeVerdictEvidenceInScope : InScopeItem {
    doc /*
     * A pass or a fail for each requirement of the increment on each route,
     * on a virtual vehicle, from the replay of a recorded command stream,
     * bound to the route, the topology, the configuration and the revision
     * that ran.
     */
  }

  part eeTimingOutOfScope : OutOfScopeItem {
    doc /*
     * Claims on the timing of the vehicle network, such as latency and jitter
     * budgets, and time synchronisation between its nodes.
     */
  }
  part eeTrafficShapingOutOfScope : OutOfScopeItem {
    doc /*
     * Traffic shaping, and the behavior of the command under competing load
     * on the network.
     */
  }
  part eeDiagnosticsUpdateOutOfScope : OutOfScopeItem {
    doc /* Diagnostics and software update of the ECUs through the zone controllers. */
  }
  part eeSecurityOutOfScope : OutOfScopeItem {
    doc /* Security hardening: segmentation, authenticated messages and link protection. */
  }
  part eeRedundancyOutOfScope : OutOfScopeItem {
    doc /*
     * Redundancy, the operation of the vehicle after the loss of a whole
     * zone, and power modes such as sleep and wake.
     */
  }
  part eeVariabilityOutOfScope : OutOfScopeItem {
    doc /*
     * A second topology, and any variability of the E/E architecture in the
     * product line.
     */
  }
  part eeSensorDataOutOfScope : OutOfScopeItem {
    doc /*
     * Sensor data, such as the vehicle speed, up from an ECU on CAN to the
     * central computer.
     */
  }
  part eeClosedLoopOutOfScope : OutOfScopeItem {
    doc /* Closed loop with a driving simulator through the vehicle network. */
  }
  part eeHardwareEffectsOutOfScope : OutOfScopeItem {
    doc /*
     * Effects of hardware: the physical layer, bit timing on CAN and the
     * timing of microcontrollers.
     */
  }
  part eeSafetyClaimOutOfScope : OutOfScopeItem {
    doc /*
     * Any safety argument, including freedom from interference, and any
     * compliance, type approval or certification claim.
     */
  }

  part eeVerificationEnvironment : System2EngineeringAndAssuranceSystem {
    doc /*
     * A software testbed stands for the vehicle network: it runs the network
     * and its nodes as software on virtual links, replays a recorded stream
     * of driving commands into the Eclipse S-CORE path on the central
     * computer, takes links down and makes commands get lost, delayed,
     * repeated or corrupted, models the vehicle that the actuation ECU
     * drives, and records what reaches each node. The testbed with its model
     * of the vehicle is the virtual vehicle of this increment. The testbed,
     * its host, the replay, the fault injection, the vehicle model, the
     * records and the evaluators enable engineering and verification. They
     * are not vehicle features and not contents of the System 1 boundary. The
     * testbed is chosen after a readiness probe; this framing selects none.
     */
  }

  part asmEECommandFromDrivingBaseline : IncrementAssumption {
    doc /*
     * The form and the cadence of the driving command are those that the
     * driver-assistance increment, INC-DRIVING-002, fixes at its baseline.
     * Until that baseline, both can change.
     */
  }
  part asmEESoftwareTestbedStandsIn : IncrementAssumption {
    doc /*
     * A software testbed stands for the vehicle network in function. It gives
     * no hardware timing: a time that it measures is the testbed's, not that
     * of a vehicle network. A verdict holds for that testbed only.
     */
  }
  part asmEEScoreCommandSource : IncrementAssumption {
    doc /*
     * The driving command enters the vehicle network from the Eclipse S-CORE
     * path of the existing increments on the central computer. A readiness
     * probe tests this first. If it does not hold, the owner decides how the
     * increment goes on.
     */
  }

  part gapEESafetyPathArchitecture : IncrementGap {
    doc /*
     * REQ-MW-006 asks each member product to keep a failure of the non-safety
     * middleware integration path from causing an uncontrolled emergency
     * intervention command, by a middleware partition with a safety
     * certification or by a direct vehicle-command path, and leaves that
     * choice and its containment criteria open per GAP-MW-029. That direct
     * path keeps the AEBS emergency intervention command around the
     * middleware, from the AEB node to the vehicle command gate on the Linux
     * host (ASM-MW-003, ASM-MW-028, REQ-MW-017). It is not one of the routes
     * that this increment judges, and this increment does not carry that AEBS
     * command. The routes that this increment judges lie after the
     * middleware. Whether a verdict on them bears on that choice is open. The
     * containment criteria stay open, and this increment makes no
     * freedom-from-interference claim.
     */
  }
  part gapEEZoneRouteInVehicles : IncrementGap {
    doc /*
     * The public sources in the folder's upstream record describe zone
     * controllers as gateways or aggregators of input and output between the
     * central computer and the sensors and actuators of their zone. None of
     * them shows a production vehicle whose brake command takes a route
     * through a zone controller: one plans braking among the systems on the
     * Ethernet backbone of a central architecture for 2028, one places the
     * brake actuators apart from the zone controllers, and one says that the
     * move of chassis control into the zones may need more time. Whether
     * vehicles carry a driving command through a zone controller is open. So
     * this increment judges that route and a direct link from the central
     * computer, and takes neither as given.
     */
  }
  part gapEEActuationEnd : IncrementGap {
    doc /*
     * In the driving benches the actuation end is an actuation adapter on the
     * host that runs Eclipse S-CORE. The adapter of the closed-loop driving
     * increment applies the stop response of REQ-DRIVING-028. The adapter of
     * the driver-assistance increment rejects a command whose sequence count,
     * check value or issue time fails, and has no stop response. It turns an
     * accepted command into the simulator's control by a rule that takes the
     * speed of the ego vehicle from the newest world snapshot
     * (MAP-DRIVING-DA-COMMAND). This increment puts the actuation in an ECU
     * on CAN. Which element then holds each of these duties, where the
     * actuation end takes a vehicle speed if its conversion of the command
     * needs one, whether the driving command with its issue time, sequence
     * count and check value fits a CAN frame, and whether a zone controller
     * that repacks the command from Ethernet to CAN keeps the detection end
     * to end, is open. This framing changes neither adapter.
     */
  }
  part gapEEBrakeHandoff : IncrementGap {
    doc /*
     * The AEBS realization records the hand-off from the vehicle interface to
     * the brake ECU and actuator as an open integration obligation, and
     * deferred the boundary of the brake ECU and actuator to INC-AEBS-008.
     * INC-AEBS-008, the AEBS simulation deployment, uses a vehicle-dynamics
     * test double and makes no brake ECU or actuator claim, so the obligation
     * stays open. This increment carries the driving command of the
     * driver-assistance increment to an actuation ECU on CAN, not an AEBS
     * command. Whether a result of this increment meets that obligation for
     * the AEBS is open, and this increment does not decide it.
     */
  }
  part gapEEStackAndNetworkBoundary : IncrementGap {
    doc /*
     * The platform stack describes one SoC and keeps its hardware layer
     * abstract, the execution-environment shared asset and its feature model
     * describe one vehicle compute target, with an NXP and Zephyr candidate,
     * and VehicleNetworkBoundary of the AAOS SDV middleware boundary holds
     * two Ethernet ports and no part. How the vehicle network of this
     * increment relates to them is open for Phases 2 and 3. This framing
     * changes none of them.
     */
  }
  part gapEENetworkInProductLine : IncrementGap {
    doc /*
     * The governed product-line scope has no element for the vehicle network.
     * This increment admits no member and changes no scope decision. Phase 3
     * classifies the vehicle network against the scope as it then stands.
     */
  }
  part gapEEBenchPlatform : IncrementGap {
    doc /*
     * No bench of the repository runs a vehicle network with zone
     * controllers, a backbone or CAN; the driving benches carry the vehicle
     * control and the speed between hosts over a bench network. The testbed
     * that stands for the vehicle network in this increment is not chosen.
     * Its readiness probe, its cost, its host and whether it runs on one host
     * are open.
     */
  }
  part gapEERecordedCommandStream : IncrementGap {
    doc /*
     * The evidence replays a recorded stream of driving commands in the form
     * that the driver-assistance increment fixes. Which recording gives that
     * stream, and how the stream is bound to the revision that made it, is
     * open.
     */
  }

  part eeArchitectureCharter : IncrementCharter {
    ref part :>> increment = eeArchitectureIncrement;
    ref part :>> systemOfInterest = eeVehicleNetworkSystem;
    attribute :>> owner = "Orkun Yilmaz";
    attribute :>> applicablePhases = (
      MethodPhase::phase0_incrementFraming,
      MethodPhase::phase1_concernFraming,
      MethodPhase::phase2_operationalContext,
      MethodPhase::phase3_capabilityClassification,
      MethodPhase::phase4_needs,
      MethodPhase::phase5_requirements,
      MethodPhase::phase6_functionalArchitecture,
      MethodPhase::phase7_logicalArchitecture,
      MethodPhase::phase8_physicalRealization,
      MethodPhase::phase9_variabilityConfiguration,
      MethodPhase::phase10_vvEvidence,
      MethodPhase::phase11_baseline
    );
    attribute :>> expectedArtifacts = (
      "DE4SDV_EEArchitectureFraming",
      "DE4SDV_EEArchitectureOperationalContext",
      "DE4SDV_EEArchitectureCapabilityClassification"
    );
    attribute :>> expectedReviewEvidence = (
      "owner confirmation of the engineering question and the scope",
      "independent review of the System 1 and System 2 boundary and the nonclaims",
      "repository, smoke and focused regression checks on the reviewed changes",
      "exact-head licensed SysML validation and Syside-generated framing view"
    );
    doc /*
     * Expected artifacts name only content present now, not future packages.
     * Review evidence is expected, not asserted available by this declaration.
     */
  }

  dependency scopeToEEArchitectureQuestion
    from eeArchitectureScope to eeArchitectureQuestion;
  dependency eeArchitectureQuestionToProblem
    from eeArchitectureQuestion to eeArchitectureProblem;

  concern eeArchitectureBoundary : IncrementBoundaryConcern {
    subject increment : EEArchitectureIncrement;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
    doc /*
     * Systems engineers and verification engineers need the framing proposal
     * kept distinct from realized, tested or accepted scope, and the verdicts
     * of Phase 10, which hold what reaches the actuation against what the
     * requirements ask, kept distinct from a run of the network that only
     * looks right.
     */
  }

  /* Phase 1: one concern per question of the in-scope items, held by the
   * parties whose interest it states, not only by the roles that check the
   * answer. Each is typed by the SAF concern that asks its question and
   * names the view of a later phase that answers it; that is the viewpoint
   * selection of this phase. The framing viewpoint frames all of them until
   * then. */
  concern eeVehicleCommandConcern : OperationalCapabilityConcern {
    doc /*
     * eeCommandFlowInScope and eeNetworkFaultsInScope, operational part.
     * Vehicle occupants and road users need the vehicle to act on the driving
     * command that its central computer gives across the vehicle network,
     * whichever route the command takes, and to act on no command that a
     * fault of the network has made invalid on its way. It states what they
     * expect, not how well the network meets it: no safety, timing or
     * performance claim for a vehicle network follows from it. Answered by
     * the operational story of phase 2.
     */
    subject;
    stakeholder occupant : VehicleOccupant;
    stakeholder roadUser : RoadUser;
  }

  concern eeTopologyStructureConcern : PhysicalStructureConcern {
    doc /*
     * eeTopologyInScope. System architects and product-line engineers need to
     * see which elements make up the one topology of the vehicle network and
     * in which role each is used: the network side of the central computer,
     * the Ethernet backbone, the two zone controllers as gateways between the
     * backbone and CAN, the CAN bus of each zone, the direct link that passes
     * no zone controller, and the actuation ECU on CAN. The lifecycle
     * decision is whether the product line admits this topology as its
     * reference vehicle network. How it relates to the platform stack and to
     * the vehicle network boundary of the AAOS SDV middleware is open for
     * phases 2 and 3 (gapEEStackAndNetworkBoundary). Answered by the physical
     * structure definition of phase 8.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder productLineEngineer : ProductLineEngineer;
  }

  concern eeCommandItemConcern : PhysicalLogicalItemMappingConcern {
    doc /*
     * eeCommandFlowInScope. Systems engineers and safety experts need to see
     * which exchange item of the vehicle network carries the driving command
     * on each part of its way, on the Ethernet backbone, through a zone
     * controller and on CAN, and whether each keeps the parts of the command
     * by which the actuation detects its loss, delay, repetition or
     * corruption, including where a zone controller repacks it from Ethernet
     * to CAN (gapEEActuationEnd). The form and the cadence of the command are
     * those that the driver-assistance increment fixes at its baseline
     * (asmEECommandFromDrivingBaseline). Answered by the view of the claimed
     * path in phase 8.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder safetyExpert : SafetyExpert;
  }

  concern eeCommandRouteExchangeConcern : PhysicalInternalExchangeConcern {
    doc /*
     * eeCommandRouteInScope. System architects and systems engineers need to
     * see, on each of the two routes, which elements of the vehicle network
     * exchange the driving command on its way from the network side of the
     * central computer to the actuation ECU, through the Ethernet backbone
     * and a zone controller or over the direct link, and the boundary
     * interface by which the command enters the network from the Eclipse
     * S-CORE path (asmEEScoreCommandSource). This increment takes neither
     * route as given (gapEEZoneRouteInVehicles), and phases 6 to 8 decide the
     * medium of the direct link. Answered by the view of the claimed path in
     * phase 8.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder systemsEngineer : SystemsEngineer;
  }

  concern eeNetworkFaultResponseConcern : SystemProcessConcern {
    doc /*
     * eeNetworkFaultsInScope. Safety experts and systems engineers need to
     * see the sequence from each fault of the vehicle network on the route of
     * the command, a link of that route that goes down and a command that is
     * lost, delayed, repeated or corrupted, to its detection at the actuation
     * and to the response that follows there, independent of the elements
     * that realize it. A time limit on a response counts on the clock of the
     * virtual vehicle. No safety argument follows from it. Answered by the
     * system process of phase 6.
     */
    subject;
    stakeholder safetyExpert : SafetyExpert;
    stakeholder systemsEngineer : SystemsEngineer;
  }

  concern eeRouteVerdictConcern : ArgumentationAssuranceConcern {
    doc /*
     * eeVerdictEvidenceInScope. Product-line engineers and verification
     * engineers need the lifecycle decision to rest on a pass or a fail for
     * each requirement of the increment on each route, each bound to the
     * route, the topology, the configuration and the revision that ran, from
     * the replay of a recorded command stream whose binding to the revision
     * that made it is open (gapEERecordedCommandStream). A verdict holds for
     * the software testbed only (asmEESoftwareTestbedStandsIn) and is no
     * timing claim for a vehicle network, and a fail stays a recorded result.
     * Answered by the argumentation assurance view of phase 10.
     */
    subject;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
  }

  view eeArchitectureFramingView {
    viewpoint eeArchitectureFramingViewpoint : IncrementFramingViewpoint {
      frame eeArchitectureBoundary;
      frame eeVehicleCommandConcern;
      frame eeTopologyStructureConcern;
      frame eeCommandItemConcern;
      frame eeCommandRouteExchangeConcern;
      frame eeNetworkFaultResponseConcern;
      frame eeRouteVerdictConcern;
    }
    expose EEArchitectureIncrement;
    expose eeArchitectureIncrement;
    expose eeArchitectureProblem;
    expose eeArchitectureQuestion;
    expose eeArchitectureDecision;
    expose eeVehicleNetworkSystem;
    expose eeArchitectureScope;
    expose eeArchitectureBoundary;
    expose eeVehicleCommandConcern;
    expose eeTopologyStructureConcern;
    expose eeCommandItemConcern;
    expose eeCommandRouteExchangeConcern;
    expose eeNetworkFaultResponseConcern;
    expose eeRouteVerdictConcern;
    expose eeTopologyInScope;
    expose eeCommandFlowInScope;
    expose eeCommandRouteInScope;
    expose eeNetworkFaultsInScope;
    expose eeVerdictEvidenceInScope;
    expose eeTimingOutOfScope;
    expose eeTrafficShapingOutOfScope;
    expose eeDiagnosticsUpdateOutOfScope;
    expose eeSecurityOutOfScope;
    expose eeRedundancyOutOfScope;
    expose eeVariabilityOutOfScope;
    expose eeSensorDataOutOfScope;
    expose eeClosedLoopOutOfScope;
    expose eeHardwareEffectsOutOfScope;
    expose eeSafetyClaimOutOfScope;
    expose eeArchitectureCharter;
    expose eeVerificationEnvironment;
    expose asmEECommandFromDrivingBaseline;
    expose asmEESoftwareTestbedStandsIn;
    expose asmEEScoreCommandSource;
    expose gapEESafetyPathArchitecture;
    expose gapEEZoneRouteInVehicles;
    expose gapEEActuationEnd;
    expose gapEEBrakeHandoff;
    expose gapEEStackAndNetworkBoundary;
    expose gapEENetworkInProductLine;
    expose gapEEBenchPlatform;
    expose gapEERecordedCommandStream;
    render asTreeDiagram;
  }
}
