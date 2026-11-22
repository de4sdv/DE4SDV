/*
 * DE4SDV E/E architecture stakeholder needs and requirements.
 *
 * INC-EE-001, phase 4: the stakeholder needs of the vehicle network, the
 * system of interest the charter declares. Each need is held by the
 * parties the vehicle network serves and leads its source with the phase
 * 1 concern it derives from. Each has one planned stakeholder review on
 * the scenarios of phase 2 it covers, carried out by the roles that check
 * the answer. Four concerns are reviewer questions: a need's source names
 * them and its review checks them.
 *
 * Each of these four concerns asks to see the answer that the view of a
 * later phase gives, and the vehicle network gives its roles nothing that
 * they use in their own work: eeTopologyStructureConcern, held by system
 * architects and product-line engineers, and
 * eeCommandRouteExchangeConcern, held by system architects and systems
 * engineers, ask about the elements that carry the command, and
 * NEED-EE-001 names them; eeCommandItemConcern, held by systems engineers
 * and safety experts, and eeNetworkFaultResponseConcern, held by safety
 * experts and systems engineers, ask about the items and the sequence of
 * a fault, and NEED-EE-002 names them. The stakeholder needs of the
 * driver-assistance increment, INC-DRIVING-002, keep such concerns as
 * reviewer questions in the same way.
 *
 * Phase 5: the requirements derived from these needs, each with one
 * subject, the vehicle network, one verification method and its success
 * criteria. They derive from the needs and from REQ-DRIVING-028,
 * REQ-DRIVING-039 and REQ-MW-006, and the scope of the increment caps
 * them at ten. From the driver-assistance increment, the terms take the
 * form of the driving command and the rules by which its actuation
 * adapter takes a command for valid, and REQ-EE-005 derives the cadence
 * from its realization; from INC-DRIVING-001, they take the stop response
 * and its limits of 200 ms and 300 ms of simulation time. Set here, each
 * with its reason in a rationale: the share of the vehicle network in the
 * delay limit; the arrival time at the actuation ECU in place of the
 * newest world time of that adapter; the start of the stop response once
 * more than 200 ms pass, and no earlier; its deceleration until the run
 * ends and its steering of 0° before any valid command; the run set, with
 * its delay of 300 ms; and the end of each run 100 ms after its last
 * command. Keeping the rules of that adapter makes one lost or corrupted
 * command start the stop response, which REQ-DRIVING-028 reads as a
 * stopped path only after two missed commands. Each time limit counts on
 * the clock of the virtual vehicle. The comment on gapEEActuationEnd
 * gives what phase 5 fixes of that gap and what stays open, and the
 * comment on gapEEBenchPlatform and gapEERecordedCommandStream gives what
 * the criteria ask of System 2. Rule 5 of the increment workflow makes a
 * requirement core when its subject has no link and it has none of its
 * own. No requirement carries a link at this revision, so all ten read as
 * core. REQ-EE-002 names the Eclipse S-CORE path and so depends on the
 * feature eclipseSCORE beyond its subject; phase 9 links it. Phase 3
 * records no feature candidate for the vehicle network and leaves open
 * whether the governed scope takes it as common content, so phase 9
 * decides on a link of its system of interest.
 *
 * No safety, timing, on-road or production-readiness claim is made, and
 * no member product is claimed.
 */

package DE4SDV_EEArchitectureNeedsRequirements {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_TraceVocabulary::*;
  private import DE4SDV_Stakeholders::*;
  private import SAF_Viewpoints::*;
  private import SysideViews::**;
  private import Views::*;

  /* ───────────────────── Phase 4: stakeholder needs ───────────────────── */

  requirement <'NEED-EE-001'> needDrivingCommandReachesActuationOnEachRoute : StakeholderNeedCandidate {
    subject vehicleNetwork :> DE4SDV_EEArchitectureFraming::eeVehicleNetworkSystem;
    stakeholder occupant : VehicleOccupant;
    stakeholder roadUser : RoadUser;
    require constraint statement { language "English" /* Vehicle occupants and road users need the vehicle network to carry the driving command that the central computer gives to the actuation ECU on each route of the command, so that the actuation ECU applies that command to the vehicle. */ }
    attribute :>> source = "INC-EE-001 eeVehicleCommandConcern, eeCommandRouteExchangeConcern, eeTopologyStructureConcern, scope items eeCommandFlowInScope, eeCommandRouteInScope and eeTopologyInScope, assumptions asmEECommandFromDrivingBaseline and asmEEScoreCommandSource, gaps gapEEZoneRouteInVehicles and gapEEStackAndNetworkBoundary, scenarios SC-EE-001 and SC-EE-002";
    attribute :>> rationale = "The vehicle can act on the driving command only if the command reaches the actuation ECU, and the increment takes neither route as given (gapEEZoneRouteInVehicles), so the need holds on each. The form of the command is the one that the driver-assistance increment fixes at its baseline; that baseline states no cadence of the command as such. The need states what the occupants and road users expect, not how well the network meets it, and carries no safety claim and no timing claim. Phase 5 derives its limits. Phase 5 also derives from this need the requirements on the elements that exchange the command on each route and on the topology that holds both routes: its source names their concerns, and SC-EE-005 asks their questions.";
  }

  requirement <'NEED-EE-002'> needNoInvalidCommandApplied : StakeholderNeedCandidate {
    subject vehicleNetwork :> DE4SDV_EEArchitectureFraming::eeVehicleNetworkSystem;
    stakeholder occupant : VehicleOccupant;
    stakeholder roadUser : RoadUser;
    require constraint statement { language "English" /* Vehicle occupants and road users need the vehicle network to apply to the vehicle no driving command that a fault of the network has made invalid on its way, on each route of the command. */ }
    attribute :>> source = "INC-EE-001 eeVehicleCommandConcern, eeNetworkFaultResponseConcern, eeCommandItemConcern, scope items eeNetworkFaultsInScope and eeCommandFlowInScope, assumption asmEECommandFromDrivingBaseline, gap gapEEActuationEnd, scenarios SC-EE-003 and SC-EE-004";
    attribute :>> rationale = "A command that is lost, delayed, repeated or corrupted on its way no longer stands for what the central computer gave, so the vehicle is not to act on it. When a link of the route goes down, the last command to arrive ages, and a lost command is a fault of the network. The driver-assistance increment places at its actuation end, DrivingCommandActuationAdapter, the share of REQ-MW-006 that is not applying a rejected command: the adapter rejects each command in which the form that REQ-DRIVING-039 requires lets it detect a loss, a delay, a repetition or a corruption, and has no stop response. A corruption that the adapter does not detect counts there as a valid command and can make it reject later valid commands as repetitions (the check-value bound decision of 2026-11-21 of that increment), so this need states the expectation and Phase 5 states the requirement within that bound. Which element detects a fault, rejects a command and gives a response is open (gapEEActuationEnd). The need carries no safety claim and no claim of freedom from interference. Phase 5 derives the detection and the rejection with their limits, and the share of the network in the response when no valid command reaches the actuation ECU, after REQ-DRIVING-028 of INC-DRIVING-001. A time limit counts on the clock of the virtual vehicle. Phase 5 also derives from this need the requirements on the exchange items that carry the command and on the sequence from each fault to its response: its source names their concerns, and SC-EE-006 asks their questions.";
  }

  requirement <'NEED-EE-003'> needRunsIdentifyRouteAndNetwork : StakeholderNeedCandidate {
    subject vehicleNetwork :> DE4SDV_EEArchitectureFraming::eeVehicleNetworkSystem;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder productLineEngineer : ProductLineEngineer;
    require constraint statement { language "English" /* Verification engineers and product-line engineers need each run of the vehicle network to identify the route that carried the driving command and the topology and the revision of the network that ran, so that each verdict is bound to what ran. */ }
    attribute :>> source = "INC-EE-001 eeRouteVerdictConcern, scope item eeVerdictEvidenceInScope, assumption asmEESoftwareTestbedStandsIn, gap gapEERecordedCommandStream, scenarios SC-EE-001 to SC-EE-004";
    attribute :>> rationale = "The lifecycle decision rests on a pass or a fail for each requirement on each route, and a verdict holds only for the route, the topology and the revision that ran. The recorded command stream, its binding to the revision that made it and the testbed belong to System 2 and are bound there (gapEERecordedCommandStream, asmEESoftwareTestbedStandsIn), so this need covers only what the vehicle network itself runs. A verdict holds for the software testbed only and is no timing claim for a vehicle network.";
  }

  /* ───────────────── Phase 4: planned stakeholder reviews ───────────────── */

  part <'SC-EE-005'> commandOnEachRouteValidationPlan : ValidationPlanningScenario {
    doc /*
     * For NEED-EE-001, a planned stakeholder review. While the route through
     * a zone controller and the direct link run (SC-EE-001 and SC-EE-002),
     * can systems engineers and verification engineers confirm whether the
     * command that the actuation ECU applies on each route is the command
     * that the central computer gave? Can system architects and systems
     * engineers tell, on each route, which elements of the vehicle network
     * exchange the command on its way from the network side of the central
     * computer to the actuation ECU, through the Ethernet backbone and a zone
     * controller or over the direct link, and by which boundary interface it
     * enters the network from the Eclipse S-CORE path? And can system
     * architects and product-line engineers tell which elements make up the
     * one topology that holds both routes, in which role each is used and
     * what its relation to the platform stack and to the vehicle network
     * boundary of the AAOS SDV middleware is (gapEEStackAndNetworkBoundary),
     * and judge from that whether the product line admits this topology as
     * its reference vehicle network?
     */
  }
  connection commandOnEachRouteValidationPlanning : ValidationPlanningAssociation
    connect needDrivingCommandReachesActuationOnEachRoute to commandOnEachRouteValidationPlan;
  dependency commandOnEachRouteValidationFromZoneControllerRoute
    from commandOnEachRouteValidationPlan
    to DE4SDV_EEArchitectureOperationalContext::carryCommandThroughZoneController;
  dependency commandOnEachRouteValidationFromDirectLink
    from commandOnEachRouteValidationPlan
    to DE4SDV_EEArchitectureOperationalContext::carryCommandOverDirectLink;

  part <'SC-EE-006'> networkFaultValidationPlan : ValidationPlanningScenario {
    doc /*
     * For NEED-EE-002, a planned stakeholder review. While a command fault on
     * the route and a link that goes down run (SC-EE-003 and SC-EE-004), can
     * verification engineers and safety experts confirm whether the actuation
     * ECU applied any command that was lost, delayed, repeated or corrupted
     * on its way, or kept applying a command after a link of its route went
     * down, and whether a response followed when no valid command reached it,
     * and which? Can safety experts and systems engineers follow, for each
     * fault of the vehicle network on the route of the command, the sequence
     * from the fault to its detection at the actuation and to the response
     * that follows there, independent of the elements that realize it? And
     * can systems engineers and safety experts tell which exchange item
     * carries the command on each part of its way, on the Ethernet backbone,
     * through a zone controller and on CAN, and whether each keeps the parts
     * of the command by which the actuation detects its loss, delay,
     * repetition or corruption, including where a zone controller repacks it
     * from Ethernet to CAN?
     */
  }
  connection networkFaultValidationPlanning : ValidationPlanningAssociation
    connect needNoInvalidCommandApplied to networkFaultValidationPlan;
  dependency networkFaultValidationFromCommandFault
    from networkFaultValidationPlan
    to DE4SDV_EEArchitectureOperationalContext::rejectFaultyCommandOnTheRoute;
  dependency networkFaultValidationFromLinkDown
    from networkFaultValidationPlan
    to DE4SDV_EEArchitectureOperationalContext::respondToLinkDownOnTheRoute;

  part <'SC-EE-007'> runIdentityValidationPlan : ValidationPlanningScenario {
    doc /*
     * For NEED-EE-003, a planned stakeholder review. While the route through
     * a zone controller, the direct link, a command fault on the route and a
     * link that goes down run (SC-EE-001 to SC-EE-004), can verification
     * engineers and product-line engineers tell from each run which route
     * carried the command and which topology and revision of the vehicle
     * network ran, and whether each verdict is bound to them?
     */
  }
  connection runIdentityValidationPlanning : ValidationPlanningAssociation
    connect needRunsIdentifyRouteAndNetwork to runIdentityValidationPlan;
  dependency runIdentityValidationFromZoneControllerRoute
    from runIdentityValidationPlan
    to DE4SDV_EEArchitectureOperationalContext::carryCommandThroughZoneController;
  dependency runIdentityValidationFromDirectLink
    from runIdentityValidationPlan
    to DE4SDV_EEArchitectureOperationalContext::carryCommandOverDirectLink;
  dependency runIdentityValidationFromCommandFault
    from runIdentityValidationPlan
    to DE4SDV_EEArchitectureOperationalContext::rejectFaultyCommandOnTheRoute;
  dependency runIdentityValidationFromLinkDown
    from runIdentityValidationPlan
    to DE4SDV_EEArchitectureOperationalContext::respondToLinkDownOnTheRoute;

  /* ───────────────────── Phase 5: requirements ───────────────────── */

  comment termsOfTheVehicleNetworkRequirements
    /*
     * Terms of the requirements of the vehicle network below, which the needs
     * above use in the same sense.
     * - Vehicle network: the system of interest that the charter declares:
     *   the network side of the central computer, the Ethernet backbone, the
     *   two zone controllers, the CAN bus of each zone, the direct link and
     *   the actuation ECU.
     * - Element: a node or a link of the vehicle network: the network side of
     *   the central computer, a zone controller or the actuation ECU, or the
     *   Ethernet backbone, a CAN bus or the direct link.
     * - Topology: the arrangement of the elements that the scope of the
     *   increment fixes: one central computer, two zone controllers that act
     *   as gateways between the Ethernet backbone and CAN, the Ethernet
     *   backbone between the central computer and the zone controllers, a CAN
     *   bus in each zone, and a direct link from the central computer to the
     *   actuation ECU that passes no zone controller.
     * - Route: the way of a driving command from the boundary interface to
     *   the actuation ECU. The route through a zone controller passes the
     *   network side of the central computer, the Ethernet backbone, the zone
     *   controller of the zone of the actuation ECU and the CAN bus of that
     *   zone; the direct route passes the network side of the central
     *   computer and the direct link. The elements of a route are those that
     *   it passes and the actuation ECU.
     * - Boundary interface: the interface on the central computer at which
     *   the vehicle network takes each driving command from the path that
     *   carries it there.
     * - Take: receive a driving command at the boundary interface, at the
     *   simulation time at which the path that carries it there gives it.
     * - Actuation ECU: the ECU on the CAN bus of one zone, at the end of both
     *   routes, that applies the driving commands to the vehicle.
     * - Vehicle: the vehicle that the actuation ECU drives, which the virtual
     *   vehicle of the increment models.
     * - Driving command: a steering and acceleration command in the form that
     *   the driver-assistance increment, INC-DRIVING-002, fixes at its
     *   baseline, with five parts: a steering angle in degrees, positive to
     *   the left; an acceleration in m/s², negative when it decelerates; an
     *   issue time in seconds of simulation time; a sequence count, an
     *   unsigned 32-bit count from 1 in each run; and a check value, the
     *   CRC-32 over the other parts. The check value holds when it equals the
     *   CRC-32 over the other parts as they reach the actuation ECU.
     * - Detection parts: the issue time, the sequence count and the check
     *   value of a driving command, which show a delay, a loss or a
     *   repetition, and a corruption.
     * - Command stream: the driving commands that the vehicle network takes
     *   in a run, in the order in which it takes them.
     * - Run: one execution of the vehicle network on one route of one
     *   scenario, from the first driving command that it takes until 100 ms
     *   of simulation time after the last one that it takes.
     * - Fault: a disturbance of one link of the route of a run, made from
     *   outside the vehicle network, that makes a driving command lost,
     *   delayed so that it reaches the actuation ECU more than 100 ms of
     *   simulation time after its issue time, repeated, or changed in a part,
     *   that is a loss, a delay, a repetition or a corruption, or that takes
     *   the link down for the rest of the run. A fault affects the driving
     *   command that it loses, delays, repeats or changes, and each driving
     *   command given to the link while the link is down; it affects no other
     *   command, so a command that a delay holds behind the delayed one
     *   counts as unaffected. A defect of an element is no fault; the
     *   requirements hold with it in every run.
     * - Judged run: a run in which the path that carries the driving commands
     *   to the boundary interface gives each of them there no more than 50 ms
     *   of simulation time after its issue time.
     * - Run set: for each route, a run without a fault, of SC-EE-001 on the
     *   route through a zone controller or of SC-EE-002 on the direct route;
     *   a run of SC-EE-003 for each of a loss, a delay, a repetition and a
     *   corruption on each link of the route, the delay holding the command
     *   on the link for 300 ms of simulation time; and a run of SC-EE-004 for
     *   each link of the route. The run set is judged when each of its runs
     *   is a judged run.
     * - Simulation time: the time on the clock of the virtual vehicle, the
     *   testbed with its model of the vehicle, in seconds; the issue time of
     *   each driving command counts on it.
     * - Reference count: the highest sequence count among the driving
     *   commands that reached the actuation ECU earlier in the run with a
     *   check value that holds; it is 0 at the start of each run.
     * - Valid driving command: a driving command that reaches the actuation
     *   ECU with a check value that holds, a sequence count one more than the
     *   reference count, and an issue time that is a finite number no more
     *   than 100 ms of simulation time before the simulation time at which it
     *   reaches the actuation ECU. A corruption that leaves the check value
     *   holding is judged by its sequence count and its issue time alone: the
     *   bound of the check value.
     * - Apply: give the vehicle, at the simulation time at which a driving
     *   command reaches the actuation ECU, its steering angle and its
     *   acceleration, and hold them as the output of the actuation ECU until
     *   it gives others.
     * - Stop response: from its start until the run ends, the actuation ECU
     *   gives the vehicle a deceleration of 4 m/s², within the tolerance of
     *   REQ-DRIVING-020, and the steering angle of the last valid driving
     *   command that it applied, or 0° when it applied none. It is the share
     *   of the vehicle network in the response that REQ-DRIVING-028 of
     *   INC-DRIVING-001 asks when the commands stop, after REQ-DRIVING-020 to
     *   REQ-DRIVING-022; the deceleration until the run ends and the 0° are
     *   set here.
     * - Configuration: every file that sets the topology, the route of a run
     *   or the software of an element of the vehicle network.
     * - Network identity: the route of the run; the commit of the DE4SDV
     *   repository from which the software of the vehicle network was built
     *   and its configuration taken, and the difference between the source
     *   that was built and that commit; the SHA-256 of each file of the
     *   configuration; and each setting that the vehicle network reads from
     *   outside a file, as read.
     */

  requirement <'REQ-EE-001'> reqBothRoutesInOneTopology : RequirementCandidate {
    subject vehicleNetwork :> DE4SDV_EEArchitectureFraming::eeVehicleNetworkSystem;
    require constraint statement { language "English" /* The vehicle network shall hold the route through a zone controller and the direct route in one topology. */ }
    attribute :>> source = "NEED-EE-001; eeTopologyStructureConcern; eeCommandRouteExchangeConcern; scope item eeTopologyInScope; gap gapEEZoneRouteInVehicles";
    attribute :>> rationale = "This is a design constraint on the structure of the vehicle network. The lifecycle decision is whether the product line admits one zonal vehicle network as its reference vehicle network, from a verdict for each requirement on each route, so both routes run in the same topology: verdicts from two topologies would judge two networks. The increment takes neither route as given (gapEEZoneRouteInVehicles). Phases 6 to 8 decide the realization of each element and the medium of the direct link, and how the topology relates to the platform stack and to the vehicle network boundary of the AAOS SDV middleware stays open (gapEEStackAndNetworkBoundary).";
    attribute :>> verificationMethod = "inspect";
    attribute :>> successCriteria = "Met when the inspection of the realization that phase 8 records, and of the configuration of each run of the run set, shows one topology that holds both routes: one central computer, two zone controllers, one Ethernet backbone between them, a CAN bus in each zone and a direct link from the central computer to the actuation ECU that passes no zone controller.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-EE-002'> reqCommandsOnlyFromSCOREPath : RequirementCandidate {
    subject vehicleNetwork :> DE4SDV_EEArchitectureFraming::eeVehicleNetworkSystem;
    require constraint statement { language "English" /* The vehicle network shall take driving commands only from the Eclipse S-CORE path. */ }
    attribute :>> source = "NEED-EE-001; assumption asmEEScoreCommandSource; eeCommandRouteExchangeConcern";
    attribute :>> rationale = "This is a design constraint on the input of the vehicle network. The driving command enters the vehicle network from the Eclipse S-CORE path of the existing increments on the central computer (asmEEScoreCommandSource), the only path over which REQ-DRIVING-038 lets the driver-assistance system give it, and a readiness probe is to test this first. A command that reaches the actuation ECU by another way, such as one given straight to the CAN bus of its zone, would let the vehicle act while the routes carry nothing, so the criteria hold that each command that reaches the actuation ECU was taken at the boundary interface. The statement names the Eclipse S-CORE path, so phase 9 links it to the feature eclipseSCORE.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when the run set is judged and, in each of its runs, each driving command that reaches the actuation ECU is one that the vehicle network took from the Eclipse S-CORE path at its boundary interface.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-EE-003'> reqCommandsOnlyOnTheirRoute : RequirementCandidate {
    subject vehicleNetwork :> DE4SDV_EEArchitectureFraming::eeVehicleNetworkSystem;
    require constraint statement { language "English" /* The vehicle network shall carry the driving commands of each run only through the elements of the route of the run. */ }
    attribute :>> source = "NEED-EE-001; eeCommandRouteExchangeConcern; scope item eeCommandRouteInScope; scenarios SC-EE-001 to SC-EE-004";
    attribute :>> rationale = "This is a design constraint on the way of the command. A verdict holds for the route that ran: a command of a run on the direct route that also passes a zone controller, or one of a run through a zone controller that also takes the direct link, would give that verdict to a route that did not carry the command alone. Which elements realize each route is decided in phases 6 to 8, with the medium of the direct link.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when the run set is judged and, in each of its runs, the records show each driving command forwarded only by the elements of the route of the run: on the route through a zone controller, the network side of the central computer, the Ethernet backbone, the zone controller of the zone of the actuation ECU and the CAN bus of that zone; on the direct route, the network side of the central computer and the direct link.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-EE-004'> reqDeliverCommandStreamUnchanged : FunctionalRequirementCandidate {
    subject vehicleNetwork :> DE4SDV_EEArchitectureFraming::eeVehicleNetworkSystem;
    require constraint statement { language "English" /* In each run, the vehicle network shall deliver to the actuation ECU each driving command that no fault affects, once, in its order and with each part unchanged. */ }
    attribute :>> source = "NEED-EE-001; eeVehicleCommandConcern; assumption asmEECommandFromDrivingBaseline; scenarios SC-EE-001 to SC-EE-004";
    attribute :>> rationale = "The vehicle can act on a driving command only if the command reaches the actuation ECU as the vehicle network took it. The actuation ECU takes a command for valid only when its check value holds and its sequence count is one more than the reference count, so a command lost, repeated, put out of order or changed on its way is rejected, and a lost or changed one costs the command after it as well. The form of the command is the one that the driver-assistance increment fixes at its baseline (asmEECommandFromDrivingBaseline). Whether it fits a CAN frame is open (gapEEActuationEnd); however the elements pack it, each part arrives as it was taken. In a run with a fault, of SC-EE-003 or SC-EE-004, it holds for each command that no fault affects, so the vehicle network keeps carrying the stream around the fault; REQ-EE-008 and REQ-EE-009 state what the actuation ECU does with what reaches it.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when the run set is judged and, in each of its runs, the driving commands that reach the actuation ECU, apart from those that the fault of the run affects, are the command stream without those, each once and in its order, with each part equal to the part that the vehicle network took.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-EE-005'> reqCarryEachCommandWithin50Ms : RequirementCandidate {
    subject vehicleNetwork :> DE4SDV_EEArchitectureFraming::eeVehicleNetworkSystem;
    require constraint statement { language "English" /* In each run without a fault, the vehicle network shall carry each driving command from the boundary interface to the actuation ECU within 50 ms of simulation time after taking it. */ }
    attribute :>> source = "NEED-EE-001; eeVehicleCommandConcern; assumption asmEECommandFromDrivingBaseline; scenarios SC-EE-001 and SC-EE-002";
    attribute :>> rationale = "This is a performance requirement on the carriage of the command. The actuation ECU takes a command for valid only when its issue time is no more than 100 ms of simulation time older than its arrival, the delay limit of the actuation adapter of the driver-assistance increment. The vehicle network gets half of that limit, from the boundary interface to the actuation ECU; the other half is the share of the path that carries the command to the boundary interface, which a judged run keeps. At its baseline the source gives at most one driving command each 100 ms of simulation time: one image of the front camera each 100 ms, one plan per frame with a result and one command per plan. A command carried within 50 ms reaches the actuation ECU before the next one is given, so the vehicle network carries the commands at the cadence at which they come. A run with a fault, of SC-EE-003 or SC-EE-004, is outside this requirement. The limit counts on the clock of the virtual vehicle and makes no timing claim for a vehicle network (asmEESoftwareTestbedStandsIn).";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when the run set is judged and, in each of its runs without a fault, each driving command reaches the actuation ECU no more than 50 ms of simulation time after the vehicle network took it.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-EE-006'> reqApplyEachValidCommand : FunctionalRequirementCandidate {
    subject vehicleNetwork :> DE4SDV_EEArchitectureFraming::eeVehicleNetworkSystem;
    require constraint statement { language "English" /* Until the stop response starts, the vehicle network shall apply each valid driving command at the actuation ECU. */ }
    attribute :>> source = "NEED-EE-001; eeVehicleCommandConcern; scenarios SC-EE-001 to SC-EE-004";
    attribute :>> rationale = "The vehicle acts on a driving command only when the actuation ECU applies it, at the simulation time at which it arrives. After a repetition the actuation ECU applies the next valid driving command; a loss, a corruption, the delay of the run set or a link that goes down leaves it more than 200 ms without one, so the stop response starts (REQ-EE-009) and no later command is applied. A valid command that arrives more than 200 ms after the last one comes when the stop response is due, so the criteria leave it out even while the start of the response is within its tolerance. The stop response holds until the run ends, as the standstill of REQ-DRIVING-022 does.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when the run set is judged and, in each of its runs, the actuation ECU applies each valid driving command that reaches it before the stop response starts and no more than 200 ms of simulation time after the last valid driving command before it reached the actuation ECU, or after the run started when it is the first, at the simulation time at which it reaches it.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-EE-007'> reqPassDetectionPartsOnAsTaken : RequirementCandidate {
    subject vehicleNetwork :> DE4SDV_EEArchitectureFraming::eeVehicleNetworkSystem;
    require constraint statement { language "English" /* The vehicle network shall pass the detection parts of each driving command on to the actuation ECU at each element as the element received them, without computing any of them anew. */ }
    attribute :>> source = "NEED-EE-002; eeCommandItemConcern; REQ-DRIVING-039; gap gapEEActuationEnd";
    attribute :>> rationale = "This is a design constraint on the exchange items of the vehicle network. REQ-DRIVING-039 makes the driving command detectable by its form: its issue time shows a delay, its sequence count a loss or a repetition, and its check value a corruption. That detection holds from the boundary interface to the actuation ECU only if no element computes a detection part anew: a zone controller that repacks the command from Ethernet to CAN with a new check value, issue time or sequence count would hide from the actuation ECU a fault that came before it. A record shows a detection part that changes at an element in a run with a fault, but no test can tell a new check value over unchanged parts from the one taken, so the requirement is verified by analysis of the realization and of the records. How a zone controller repacks the command, and whether the command fits a CAN frame, are decided in phases 6 to 8 (gapEEActuationEnd). The analysis rests on the realization that phase 8 records and makes no freedom-from-interference claim.";
    attribute :>> verificationMethod = "analyze";
    attribute :>> successCriteria = "Met when the run set is judged and the analysis of the realization that phase 8 records, and of the records of the runs of SC-EE-003 of the run set, shows, for each element of each route, that the element passes on the issue time, the sequence count and the check value of each driving command as it received them and computes none of them anew.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-EE-008'> reqGiveOnlyLastValidCommand : FunctionalRequirementCandidate {
    subject vehicleNetwork :> DE4SDV_EEArchitectureFraming::eeVehicleNetworkSystem;
    require constraint statement { language "English" /* Until the stop response starts, the vehicle network shall give the vehicle at the actuation ECU only the steering angle and the acceleration of the last valid driving command that it applied. */ }
    attribute :>> source = "NEED-EE-002; REQ-MW-006; REQ-DRIVING-039; eeNetworkFaultResponseConcern; gap gapEEActuationEnd; scenario SC-EE-003";
    attribute :>> rationale = "The driver-assistance increment places at its actuation end the share of REQ-MW-006 that is not applying a command that the actuation rejects, and this increment puts the actuation in the actuation ECU, so the vehicle network holds that share: a command that a fault has made invalid on its way no longer stands for what its source gave. A fault shows at the actuation ECU in the sequence count for a loss or a repetition, in the check value for a corruption, and in the issue time against the simulation time at its arrival for a delay, by the rules of the actuation adapter of the driver-assistance increment (the adapter counting decision of 2026-11-18), with the arrival time set here in place of the newest world time of that adapter. Nothing is applied in place of an invalid command, so the vehicle keeps the last valid one; an invalid command, a neutral control in place of one, or a value that no command carried each breaks this requirement. A repetition costs that one command; the delay of the run set costs the delayed command and those that it holds behind it, and the stop response follows (REQ-EE-009); a loss or a corruption costs the lost or corrupted command and the next one, which reveals the gap. A corruption that the check value misses is judged by its sequence count and its issue time alone and can make the actuation ECU reject later valid commands as repetitions: the bound of the check value (the check-value bound decision of 2026-11-21 of that increment). Which element detects and rejects is decided in phases 6 to 8 (gapEEActuationEnd). The requirement carries no safety claim and no claim of freedom from interference.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when the run set is judged and, in each of its runs, what the actuation ECU gives the vehicle before the stop response starts is the steering angle and the acceleration of the last valid driving command that it applied, and nothing before it applies the first.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-EE-009'> reqStopResponseAfter200Ms : FunctionalRequirementCandidate {
    subject vehicleNetwork :> DE4SDV_EEArchitectureFraming::eeVehicleNetworkSystem;
    require constraint statement { language "English" /* The vehicle network shall start the stop response at the actuation ECU once more than 200 ms of simulation time pass with no valid driving command reaching the actuation ECU. */ }
    attribute :>> source = "NEED-EE-002; REQ-DRIVING-028; eeNetworkFaultResponseConcern; gap gapEEActuationEnd; scenarios SC-EE-003 and SC-EE-004";
    attribute :>> rationale = "This is the share of the vehicle network in the stop response that REQ-DRIVING-028 of INC-DRIVING-001 asks and SC-EE-004 takes for a link that goes down. The adapter of the driver-assistance increment has no stop response, and the actuation ECU is the last element that a command reaches, so it gives the response itself because it can no longer be told to. The 200 ms of simulation time and the 300 ms of the criteria are those of REQ-DRIVING-028, whose rationale counts a command every 100 ms, so that two missed commands mean that the path has stopped; the source of this increment gives at most one each 100 ms. Set here: a command that reaches the actuation ECU exactly 200 ms after the last valid one still counts, and the stop response starts only after that. Set here too: with the rules of the actuation adapter of the driver-assistance increment kept, one lost or corrupted command costs two, so it leaves the actuation ECU 300 ms without a valid command and starts the stop response, although REQ-DRIVING-028 reads two missed commands as a stopped path. A repetition costs only its copy. A delay that only just makes a command late would leave exactly 200 ms without a valid one, where the outcome would depend on the clock of the testbed, so the run set delays the command by 300 ms; with the commands that it holds behind it, that leaves more than 200 ms without a valid one on every clock, and the stop response follows. The stop response gives the deceleration of REQ-DRIVING-020 with the steering of REQ-DRIVING-021 until the run ends, which holds the vehicle at standstill as REQ-DRIVING-022 does, so that it needs no vehicle speed at the actuation ECU, whose inputs stay open (gapEEActuationEnd). The response is shown on the virtual vehicle and carries no safety claim; its time limit counts on the clock of the virtual vehicle and makes no timing claim for a vehicle network.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when the run set is judged and, in each of its runs in which more than 200 ms of simulation time pass with no valid driving command reaching the actuation ECU, the actuation ECU gives the vehicle the stop response, with its deceleration and its steering angle, from later than 200 ms and no later than 300 ms of simulation time after the last valid driving command reached it, or after the run started when none did, until the run ends, and applies no driving command that reaches it after those 200 ms; and when no run of the run set holds a start of the stop response at another time.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-EE-010'> reqRecordNetworkIdentity : FunctionalRequirementCandidate {
    subject vehicleNetwork :> DE4SDV_EEArchitectureFraming::eeVehicleNetworkSystem;
    require constraint statement { language "English" /* The vehicle network shall record its network identity before it takes the first driving command of each run. */ }
    attribute :>> source = "NEED-EE-003; eeRouteVerdictConcern; scope item eeVerdictEvidenceInScope; scenarios SC-EE-001 to SC-EE-004";
    attribute :>> rationale = "A verdict holds only for the route, the topology and the revision of the vehicle network that ran, and another engineer can rerun a run only from what it names. The commit names the revision, and the recorded difference tells a build with a change that the commit lacks apart from it, as the candidate identity of REQ-DRIVING-044 does; the SHA-256 of each file of the configuration and the settings read from outside a file pin what the vehicle network read, because a run can read what the commit does not fix, and the files that set the topology pin it. The recorded command stream, its binding to the revision that made it and the testbed belong to System 2 and are bound there (gapEERecordedCommandStream, asmEESoftwareTestbedStandsIn), so the record covers only what the vehicle network itself runs. Phase 8 names the files of the configuration (gapEEBenchPlatform).";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when each run of the run set has the record before the vehicle network takes its first driving command; when its route is the route that the records show the commands of the run passing; when the named files are the files of the configuration that phase 8 names; and when another engineer who checks out the named commit, applies the recorded difference and hashes the named files obtains the recorded values.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  connection bothRoutesInOneTopologyDerivation : DerivesFromNeed
    connect needDrivingCommandReachesActuationOnEachRoute to reqBothRoutesInOneTopology;
  connection commandsOnlyFromSCOREPathDerivation : DerivesFromNeed
    connect needDrivingCommandReachesActuationOnEachRoute to reqCommandsOnlyFromSCOREPath;
  connection commandsOnlyOnTheirRouteDerivation : DerivesFromNeed
    connect needDrivingCommandReachesActuationOnEachRoute to reqCommandsOnlyOnTheirRoute;
  connection deliverCommandStreamUnchangedDerivation : DerivesFromNeed
    connect needDrivingCommandReachesActuationOnEachRoute to reqDeliverCommandStreamUnchanged;
  connection carryEachCommandWithin50MsDerivation : DerivesFromNeed
    connect needDrivingCommandReachesActuationOnEachRoute to reqCarryEachCommandWithin50Ms;
  connection applyEachValidCommandDerivation : DerivesFromNeed
    connect needDrivingCommandReachesActuationOnEachRoute to reqApplyEachValidCommand;
  connection passDetectionPartsOnAsTakenDerivation : DerivesFromNeed
    connect needNoInvalidCommandApplied to reqPassDetectionPartsOnAsTaken;
  connection giveOnlyLastValidCommandDerivation : DerivesFromNeed
    connect needNoInvalidCommandApplied to reqGiveOnlyLastValidCommand;
  connection stopResponseAfter200MsDerivation : DerivesFromNeed
    connect needNoInvalidCommandApplied to reqStopResponseAfter200Ms;
  connection recordNetworkIdentityDerivation : DerivesFromNeed
    connect needRunsIdentifyRouteAndNetwork to reqRecordNetworkIdentity;

  comment actuationEndFixedInPhase5 about DE4SDV_EEArchitectureFraming::gapEEActuationEnd
    /*
     * What phase 5 fixes of this gap, and what stays open. Fixed: a driving
     * command is valid at the actuation ECU by the rules of the actuation
     * adapter of the driver-assistance increment, by its check value, by its
     * sequence count against the reference count and by its issue time
     * against the simulation time at its arrival, which is set here in place
     * of the newest world time of that adapter (the term valid driving
     * command); the vehicle network applies each valid driving command
     * (REQ-EE-006), gives the vehicle only the last valid one that it applied
     * (REQ-EE-008) and starts the stop response once more than 200 ms of
     * simulation time pass without a valid driving command (REQ-EE-009); no
     * element computes a detection part anew, so the detection holds from the
     * boundary interface to the actuation ECU through a zone controller that
     * repacks the command (REQ-EE-007); and the actuation ECU gives the
     * vehicle the steering angle and the acceleration of a command as they
     * arrive (the term apply), so it needs no vehicle speed. Open, for phases
     * 6 to 8: which element holds each of these duties other than giving the
     * stop response, which the actuation ECU gives, where it takes the
     * simulation time, how a zone controller repacks the command and whether
     * the command with its detection parts fits a CAN frame. Neither adapter
     * of the driving benches changes.
     */

  comment testbedObligationsOfPhase5 about DE4SDV_EEArchitectureFraming::gapEEBenchPlatform, DE4SDV_EEArchitectureFraming::gapEERecordedCommandStream
    /*
     * What the criteria of phase 5 ask of System 2, whose testbed is not
     * chosen yet: each is an obligation of the verification environment and
     * none a criterion of the vehicle network. The testbed gives every
     * element the one clock of the virtual vehicle, which counts the
     * simulation time of the recorded run so that the issue time of each
     * driving command counts on it, and the records name the step at which
     * each element reads it. The replay gives a recorded run from its first
     * driving command, whose sequence count is 1, to the Eclipse S-CORE path
     * on the central computer, each command at the simulation time of its
     * issue time, one each 100 ms of simulation time with none missing. The
     * path gives each command to the boundary interface no more than 50 ms of
     * simulation time after its issue time; a run in which it misses this is
     * reported with what it missed, gets no verdict and is run again, and
     * both runs are reported. The fault injection makes the one fault that a
     * run of the run set names, on its link, after the first valid driving
     * command and at least 500 ms of simulation time before the run ends, so
     * that the stop response starts within the run and a command that a delay
     * holds reaches the actuation ECU, with those held behind it, before the
     * run ends; a delay holds the delayed command on its link for 300 ms of
     * simulation time and keeps the order of the commands, and the records
     * name its size. The replay and the fault injection give no element of
     * the vehicle network a driving command other than through the Eclipse
     * S-CORE path. The records hold, with its simulation time, each driving
     * command where the vehicle network takes it, at each element that it
     * passes and where it reaches the actuation ECU, identified by the
     * sequence count that the vehicle network took, and what the actuation
     * ECU gives the vehicle. The vehicle model takes the steering angle and
     * the acceleration that the actuation ECU gives it, keeps a vehicle at
     * standstill under a deceleration, and gets its control only from the
     * actuation ECU. Open: the testbed, its readiness probe, its cost and its
     * host (gapEEBenchPlatform), and which recording gives the stream and how
     * the stream is bound to the revision that made it
     * (gapEERecordedCommandStream).
     */

  /* ─────────────────────────────── Views ─────────────────────────────── */

  concern eeArchitectureNeedsConcern : StakeholderNeedsConcern {
    doc /*
     * Systems engineers and product-line engineers need the stakeholder needs
     * of the vehicle network with their statements and sources, and the
     * planned stakeholder review of each, to judge whether the needs cover
     * the concerns of phase 1.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder productLineEngineer : ProductLineEngineer;
  }

  view eeArchitectureNeedsView : TVD::TableView {
    viewpoint selectedNeedsViewpoint : StakeholderRequirementDefinitionViewpoint {
      frame eeArchitectureNeedsConcern;
    }

    expose needDrivingCommandReachesActuationOnEachRoute;
    expose needNoInvalidCommandApplied;
    expose needRunsIdentifyRouteAndNetwork;
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

  view eeArchitectureNeedValidationView : TVD::TableView {
    viewpoint selectedNeedValidationViewpoint : StakeholderRequirementDefinitionViewpoint {
      frame eeArchitectureNeedsConcern;
    }

    expose commandOnEachRouteValidationPlan;
    expose networkFaultValidationPlan;
    expose runIdentityValidationPlan;
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

  concern eeArchitectureRequirementTraceConcern : RequirementTraceConcern {
    doc /*
     * Verification engineers and open-source reviewers need each requirement
     * of the vehicle network traced to the need it derives from, with its
     * source, its rationale, its verification method and its success
     * criteria, to judge whether the requirements answer the needs and can be
     * verified. No concern of the framing names this table:
     * eeRouteVerdictConcern asks a verdict for each requirement on each
     * route, and the table gives those requirements.
     */
    subject;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view eeArchitectureRequirementsView : TVD::TableView {
    viewpoint selectedRequirementDefinitionViewpoint : SystemRequirementDefinitionViewpoint {
      frame eeArchitectureRequirementTraceConcern;
    }

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
    filter @ SysML::RequirementUsage;
    attribute :>> includeReferenceElements = true;
    attribute :>> maxRowHeight = 500;
    view ID :> columnViews {
      attribute :>> featureToRender = CT::reqId;
    }
    view Requirement :> columnViews {
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
    view Rationale :> columnViews {
      attribute :>> featureToRender = CT::attributeValue {
        attribute attributeName = "rationale";
      }
      attribute :>> columnWidth = 420;
    }
    view Method :> columnViews {
      attribute :>> featureToRender = CT::attributeValue {
        attribute attributeName = "verificationMethod";
      }
    }
    view Criteria :> columnViews {
      attribute :>> featureToRender = CT::attributeValue {
        attribute attributeName = "successCriteria";
      }
      attribute :>> columnWidth = 360;
    }
  }
}
