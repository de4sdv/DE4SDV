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
 * Phase 5 adds to this package the requirements derived from these needs.
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

  comment commandFormContract about needDrivingCommandReachesActuationOnEachRoute
    /*
     * The vehicle network takes the driving command, DrivingCommand of
     * INC-DRIVING-002, in the form that that increment fixes at its baseline,
     * from the Eclipse S-CORE path (asmEEScoreCommandSource). Phase 5 states
     * it as requirements and derives the cadence that the vehicle network
     * carries.
     */

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
}
