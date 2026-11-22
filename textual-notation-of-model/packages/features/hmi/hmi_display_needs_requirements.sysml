/*
 * DE4SDV HMI display stakeholder needs and requirements.
 *
 * INC-HMI-001, phase 4: the stakeholder needs of the HMI display, the system
 * of interest the charter declares. Each need is held by the parties the
 * display serves and leads its source with the phase 1 concern it derives
 * from. Each has one planned stakeholder review on the scenarios of phase 2 it
 * covers, carried out by the roles that check the answer. Seven concerns are
 * reviewer questions: a need's source names them and its review checks them.
 *
 * Each of these seven concerns asks to see the answer that the view of a later
 * phase gives, and the HMI display gives its roles nothing that they use in
 * their own work: hmiDisplayInputsConcern, held by systems engineers and
 * safety experts, and hmiContentVarianceConcern, held by product-line
 * engineers, ask about the items that cross into the display and about its
 * common content, and NEED-HMI-001 names them; hmiWarningSequenceConcern, held
 * by safety experts and systems engineers, asks about the sequence of the
 * warning, and NEED-HMI-003 names it; hmiAndroidOutageConcern, held by safety
 * experts and systems engineers, hmiRendererAllocationConcern, held by
 * product-line engineers and safety experts, and hmiRendererPathConcern, held
 * by system architects and systems engineers, ask about the outages, the
 * renderers and their paths, and NEED-HMI-004 names them;
 * hmiContentCurrencyConcern, held by safety experts and verification
 * engineers, asks about the states of each element, and NEED-HMI-005 names it.
 * The stakeholder needs of the driver-assistance increment and of the E/E
 * architecture increment keep such concerns as reviewer questions in the same
 * way.
 *
 * The needs name no drawing: how the app in the IVI VM draws the scene is a
 * choice of phase 8, and the visual design stays out of scope
 * (hmiHumanFactorsOutOfScope). No need asks for gear, set speed, speed limit
 * or another telltale (hmiFurtherContentOutOfScope).
 *
 * Phase 5 adds to this package the requirements derived from these needs.
 *
 * No safety, timing, on-road or production-readiness claim is made, and no
 * member product is claimed.
 */

package DE4SDV_HmiDisplayNeedsRequirements {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_TraceVocabulary::*;
  private import DE4SDV_Stakeholders::*;
  private import SAF_Viewpoints::*;
  private import SysideViews::**;
  private import Views::*;

  /* ───────────────────── Phase 4: stakeholder needs ───────────────────── */

  requirement <'NEED-HMI-001'> needPerceivedSceneOnTheDisplay : StakeholderNeedCandidate {
    subject hmiDisplay :> DE4SDV_HmiDisplayFraming::hmiDisplaySystem;
    stakeholder occupant : VehicleOccupant;
    require constraint statement { language "English" /* Vehicle occupants need the HMI display to show the driver the scene as the driver-assistance system gives it from its own perception: its lane, the path it fits to that lane, the objects it detects with their level relative to that path, and the closest object in its path with the distance and the speed that its fusion gives. */ }
    attribute :>> source = "INC-HMI-001 hmiDriverSupervisionConcern, hmiDisplayInputsConcern, hmiContentVarianceConcern, scope item hmiSceneInScope, gaps gapHmiSceneOutput and gapHmiSceneContent, scenarios SC-HMI-001 and SC-HMI-002";
    attribute :>> rationale = "The display shows the driver what the driver-assistance system perceives, right or wrong, so that the driver can supervise the system with it, and it shows the scene that the system gives and no other. At the inspected revision the system gives no such output (gapHmiSceneOutput), and what the scene carries bounds what the display can show of it (gapHmiSceneContent). The need states what the driver expects to see, not how a driver reads it, and carries no safety claim. Phase 5 derives its requirements. Phase 5 also derives from this need the requirements on the items that cross into the display, and states which requirements on the content of the display are core and which follow the driving application: its source names their concerns, and SC-HMI-008 asks their questions.";
  }

  comment perceivedSceneContract about needPerceivedSceneOnTheDisplay
    /*
     * At the inspected revision the driver-assistance system builds a scene
     * only inside its own visualization. The bridge of its panel builds it
     * from the path that the lateral fusion fits, the offset and the heading
     * of the vehicle in its lane, the lane points of AutoSteer placed on the
     * road through the homography that the system loads, the detections of
     * AutoSpeed as boxes with a score and a class, which is a level relative
     * to the path, and the validity and the distance of the closest object,
     * and it does not read the plan. The scene of the panel carries no speed
     * of the closest object and no time, and the inference result carries a
     * frame identity and no capture time. The fusion gives the closest object
     * a distance and a speed, and its comment reads a negative speed as
     * approaching, so whether the speed that its fusion gives is the speed of
     * the object or the speed at which it closes is open. The fusion reads the
     * first level as the same lane and the second as the adjacent lane. Where
     * AutoDrive flags an object in the path and AutoSpeed gives no box for it,
     * the visualization draws a mark for the closest object with a distance
     * that it derives from the network output itself; the planner does not use
     * it, it is an estimate of the display's own, and NEED-HMI-001 leaves it
     * out by its words. Phase 5 states as requirements what the display takes
     * from the scene.
     */

  requirement <'NEED-HMI-002'> needVehicleSpeedOnTheDisplay : StakeholderNeedCandidate {
    subject hmiDisplay :> DE4SDV_HmiDisplayFraming::hmiDisplaySystem;
    stakeholder occupant : VehicleOccupant;
    require constraint statement { language "English" /* Vehicle occupants need the HMI display to show the driver the vehicle speed that the driver-assistance system is given. */ }
    attribute :>> source = "INC-HMI-001 hmiDriverSupervisionConcern, scope item hmiSpeedInScope, scenarios SC-HMI-001 and SC-HMI-002";
    attribute :>> rationale = "The display shows the driver the speed that the driver-assistance system is given, so that the driver can supervise the system with the same speed that the system acts on. The vehicle gives it, and which element brings it to the display is for the architecture phases (vehicleSpeedSourceComment). The need carries no safety claim. Phase 5 derives its requirements. NEED-HMI-004 adds that the speed stays on the display through the outages of the drawing of the scene and of Android in the IVI VM.";
  }

  requirement <'NEED-HMI-003'> needCollisionWarningOnRequest : StakeholderNeedCandidate {
    subject hmiDisplay :> DE4SDV_HmiDisplayFraming::hmiDisplaySystem;
    stakeholder occupant : VehicleOccupant;
    require constraint statement { language "English" /* Vehicle occupants need the HMI display to give the driver the collision warning on the display and as a sound when the warning request of the driver-assistance system asks for it, and no collision warning without such a request. */ }
    attribute :>> source = "INC-HMI-001 hmiDriverSupervisionConcern, hmiWarningSequenceConcern, scope item hmiCollisionWarningInScope, gaps gapHmiRendererCollisionWarning and gapHmiWarningPresentation, scenarios SC-HMI-001 and SC-HMI-002";
    attribute :>> rationale = "The warning lets the driver act on an imminent collision, and the display gives none without a request, so that each collision warning that the driver gets stands for a request of the driver-assistance system. The warning request is the driver-assistance increment's, taken as that increment defines it, and whether a warning is due is the decision of the driver-assistance system, which that increment judges. NEED-DRIVING-010 of that increment needs the system to give the request at its boundary; this need adds that the display gives the warning from it. The need rests on REQ-AEBS-002, the collision warning that the product line asks for. The vehicle data of the renderer holds no collision warning yet (gapHmiRendererCollisionWarning). The need carries no safety claim. Phase 5 derives its requirements and states when each mode is due within the time that the driver-assistance increment allots from the request to each mode (gapHmiWarningPresentation). Phase 5 also derives from this need the requirements on the sequence from the request to the warning on the display and to its sound: its source names its concern, and SC-HMI-010 asks its question.";
  }

  comment warningRequestContract about needCollisionWarningOnRequest
    /*
     * The warning request is the output that the driver-assistance increment
     * realizes from the warnings of each plan: it asks for the collision
     * warning when the plan holds the forward-collision warning or the
     * emergency braking, and it carries the capture time of the frame that the
     * plan came from. One plan holds at most one of the two. The request does
     * not tell them apart, and the system's own visualization does. Phase 5
     * states as requirements what the display takes from it.
     */

  requirement <'NEED-HMI-004'> needSpeedAndWarningThroughOutages : StakeholderNeedCandidate {
    subject hmiDisplay :> DE4SDV_HmiDisplayFraming::hmiDisplaySystem;
    stakeholder occupant : VehicleOccupant;
    require constraint statement { language "English" /* Vehicle occupants need the HMI display to show the driver the vehicle speed and to give the collision warning when it is requested, or to show that the warning is unavailable, also while the app that draws the scene hangs or ends and while Android in the IVI VM hangs, boots or restarts. */ }
    attribute :>> source = "INC-HMI-001 hmiDriverSupervisionConcern, hmiAndroidOutageConcern, hmiRendererAllocationConcern, hmiRendererPathConcern, scope items hmiAndroidOutageInScope and hmiRendererSplitInScope, gaps gapHmiRendererIntegration and gapHmiMemberGuestLayout, scenarios SC-HMI-003 to SC-HMI-006";
    attribute :>> rationale = "The driver keeps driving while the drawing of the scene or Android in the IVI VM is out, and still needs the speed and the warning then, or to know that the warning cannot come. NEED-HMI-002 and NEED-HMI-003 state the speed and the warning; this need adds that they stay through each outage. It rests on N-AEBS-008, the need of the product line that the availability of the AEBS be apparent, and on the status indication of REQ-AEBS-013. Each outage is an event inside the boundary of the display, whose detection phases 6 to 8 decide. The need names no renderer and carries no safety claim. Phase 5 derives its requirements and their limits. Phase 5 also derives from this need the requirements on the sequence from each outage to what the display shows, on which renderer draws each element and on the paths of the inputs to the renderers: its source names their concerns, and SC-HMI-011 asks their questions.";
  }

  requirement <'NEED-HMI-005'> needNoElementShownAsCurrentWhenItIsNot : StakeholderNeedCandidate {
    subject hmiDisplay :> DE4SDV_HmiDisplayFraming::hmiDisplaySystem;
    stakeholder occupant : VehicleOccupant;
    require constraint statement { language "English" /* Vehicle occupants need the HMI display to show the driver no element as current when it is not, and to show the driver when the collision warning is unavailable. */ }
    attribute :>> source = "INC-HMI-001 hmiDriverSupervisionConcern, hmiContentCurrencyConcern, scope item hmiStaleContentInScope, gap gapHmiWarningAvailability, scenarios SC-HMI-003 to SC-HMI-007";
    attribute :>> rationale = "The display shows no element as current when it is not, so that the driver supervises the driver-assistance system on what it perceives now, and it shows when the warning is unavailable, so that the driver can tell a warning that cannot come from one that is not due. From which age an element counts as late is for Phase 5 to state, and whether the display learns that the warning is unavailable from the age of its inputs or from a signal of its own is open (gapHmiWarningAvailability). The second part rests on N-AEBS-008 and REQ-AEBS-013. NEED-HMI-004 states what the display keeps through the outages in the IVI VM; this need holds for every element at any time, also when an input of the display is late or missing. The need carries no safety claim. Phase 5 derives its requirements and their limits. Phase 5 also derives from this need the requirements on the states of each element, current, late or missing, and on what the display shows in each: its source names its concern, and SC-HMI-012 asks its question.";
  }

  requirement <'NEED-HMI-006'> needRunsIdentifyTheDisplay : StakeholderNeedCandidate {
    subject hmiDisplay :> DE4SDV_HmiDisplayFraming::hmiDisplaySystem;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder productLineEngineer : ProductLineEngineer;
    require constraint statement { language "English" /* Verification engineers and product-line engineers need each run of the HMI display to identify the build and the configuration of the display that ran, so that each verdict is bound to what ran. */ }
    attribute :>> source = "INC-HMI-001 hmiDisplayVerdictConcern, scope item hmiVerdictEvidenceInScope, assumption asmHmiSimulationStandsIn, scenarios SC-HMI-001 to SC-HMI-007";
    attribute :>> rationale = "The lifecycle decision rests on a pass or a fail for each requirement and scenario, and a verdict holds only for the display that ran. The configuration of the display is every setting that it reads at its start. The candidate revision is bound by the run of the driver-assistance system (NEED-DRIVING-011 of the driver-assistance increment), and the record of what that system gives, the captures and the evaluators belong to System 2 and are bound there, so this need covers only what the display itself runs. A verdict holds for the simulated configuration only (asmHmiSimulationStandsIn).";
  }

  /* ───────────────── Phase 4: planned stakeholder reviews ───────────────── */

  part <'SC-HMI-008'> hmiSceneValidationPlan : ValidationPlanningScenario {
    doc /*
     * For NEED-HMI-001, a planned stakeholder review. While the warning
     * scenarios and the no-reaction scenarios of the driver-assistance
     * increment run on the display (SC-HMI-001 and SC-HMI-002), can
     * verification engineers and systems engineers confirm whether the lane,
     * the path, the objects with their level and the closest object in the
     * path with its distance and its speed that the display shows are those
     * that the driver-assistance system gave, and whether the display showed
     * any object that the system did not give, from the simulator's record of
     * the scene or from an estimate of the display's own? Can systems
     * engineers and safety experts tell which items cross into the HMI display
     * from outside its boundary, the lane of the driver-assistance system, the
     * path it fits to that lane, the objects it detects with their level
     * relative to its path, the closest object in its path with the distance
     * and the speed that its fusion gives, the vehicle speed that the system
     * is given and its warning request, and whether each reaches the display
     * as its source gives it? And can product-line engineers tell which
     * content of the HMI display is common to the member products and which
     * derives from a member's driving application?
     */
  }
  connection hmiSceneValidationPlanning : ValidationPlanningAssociation
    connect needPerceivedSceneOnTheDisplay to hmiSceneValidationPlan;
  dependency hmiSceneValidationFromWarningScenarios
    from hmiSceneValidationPlan
    to DE4SDV_HmiDisplayOperationalContext::showWarningInTheWarningScenarios;
  dependency hmiSceneValidationFromNoReactionScenarios
    from hmiSceneValidationPlan
    to DE4SDV_HmiDisplayOperationalContext::showNoWarningInTheNoReactionScenarios;

  part <'SC-HMI-009'> hmiSpeedValidationPlan : ValidationPlanningScenario {
    doc /*
     * For NEED-HMI-002, a planned stakeholder review. While the warning
     * scenarios and the no-reaction scenarios of the driver-assistance
     * increment run on the display (SC-HMI-001 and SC-HMI-002), can
     * verification engineers and systems engineers confirm whether the speed
     * that the display shows is the vehicle speed that the driver-assistance
     * system was given, and whether any other source of the speed reached the
     * display?
     */
  }
  connection hmiSpeedValidationPlanning : ValidationPlanningAssociation
    connect needVehicleSpeedOnTheDisplay to hmiSpeedValidationPlan;
  dependency hmiSpeedValidationFromWarningScenarios
    from hmiSpeedValidationPlan
    to DE4SDV_HmiDisplayOperationalContext::showWarningInTheWarningScenarios;
  dependency hmiSpeedValidationFromNoReactionScenarios
    from hmiSpeedValidationPlan
    to DE4SDV_HmiDisplayOperationalContext::showNoWarningInTheNoReactionScenarios;

  part <'SC-HMI-010'> hmiWarningValidationPlan : ValidationPlanningScenario {
    doc /*
     * For NEED-HMI-003, a planned stakeholder review. While the warning
     * scenarios and the no-reaction scenarios of the driver-assistance
     * increment run on the display (SC-HMI-001 and SC-HMI-002), can
     * verification engineers and safety experts confirm whether the display
     * gave the collision warning on the display and as a sound for each
     * warning request of the driver-assistance system, whether it gave one
     * without a request, and when each mode began relative to the request,
     * with no recording or overlay in place of either mode? And can safety
     * experts and systems engineers follow the sequence from the warning
     * request of the driver-assistance system to the collision warning on the
     * display and to its sound, and the time of each step within the time that
     * the driver-assistance increment allots from the request to each mode,
     * independent of the elements that realize it?
     */
  }
  connection hmiWarningValidationPlanning : ValidationPlanningAssociation
    connect needCollisionWarningOnRequest to hmiWarningValidationPlan;
  dependency hmiWarningValidationFromWarningScenarios
    from hmiWarningValidationPlan
    to DE4SDV_HmiDisplayOperationalContext::showWarningInTheWarningScenarios;
  dependency hmiWarningValidationFromNoReactionScenarios
    from hmiWarningValidationPlan
    to DE4SDV_HmiDisplayOperationalContext::showNoWarningInTheNoReactionScenarios;

  part <'SC-HMI-011'> hmiOutageValidationPlan : ValidationPlanningScenario {
    doc /*
     * For NEED-HMI-004, a planned stakeholder review. While the app that draws
     * the scene is out and while Android in the IVI VM boots, hangs and
     * restarts (SC-HMI-003 to SC-HMI-006), can verification engineers and
     * safety experts confirm whether the driver saw the vehicle speed
     * throughout and got the collision warning for each warning request, or
     * saw that the warning was unavailable? Can safety experts and systems
     * engineers follow the sequence from each outage of the drawing of the
     * scene and of the environment that hosts it, the drawing hanging or
     * ending and its host hanging, booting or restarting, to its detection and
     * to what the display shows then, independent of the elements that realize
     * it? Can product-line engineers and safety experts tell which renderer
     * realizes the drawing of each element of the HMI display, and whether the
     * split that the owner decided on 2026-11-17, the high availability
     * renderer in an SDV Media VM for the speed, the collision warning and its
     * sound and an app in the IVI VM for the scene, keeps what the driver sees
     * while Android in the IVI VM hangs, boots or restarts? And can system
     * architects and systems engineers tell which elements exchange each input
     * of the HMI display on its way from the SDV Core VM to the high
     * availability renderer in the SDV Media VM and to the app in the IVI VM
     * that draws the scene, by which exchange that app tells the renderer that
     * Android is alive, and by which boundary interface each input enters the
     * display?
     */
  }
  connection hmiOutageValidationPlanning : ValidationPlanningAssociation
    connect needSpeedAndWarningThroughOutages to hmiOutageValidationPlan;
  dependency hmiOutageValidationFromSceneAppOut
    from hmiOutageValidationPlan
    to DE4SDV_HmiDisplayOperationalContext::keepSpeedAndWarningWhenTheSceneAppIsOut;
  dependency hmiOutageValidationFromAndroidBoot
    from hmiOutageValidationPlan
    to DE4SDV_HmiDisplayOperationalContext::showSpeedAndWarningWhileAndroidBoots;
  dependency hmiOutageValidationFromAndroidHang
    from hmiOutageValidationPlan
    to DE4SDV_HmiDisplayOperationalContext::keepSpeedAndWarningWhileAndroidHangs;
  dependency hmiOutageValidationFromAndroidRestart
    from hmiOutageValidationPlan
    to DE4SDV_HmiDisplayOperationalContext::keepSpeedAndWarningThroughAndroidRestart;

  part <'SC-HMI-012'> hmiCurrencyValidationPlan : ValidationPlanningScenario {
    doc /*
     * For NEED-HMI-005, a planned stakeholder review. While the app that draws
     * the scene is out, while Android in the IVI VM boots, hangs and restarts,
     * and while the warning request stops reaching the display (SC-HMI-003 to
     * SC-HMI-007), can safety experts and verification engineers tell the
     * states that each element of the HMI display can be in, current, late or
     * missing, and the state in which the collision warning is unavailable,
     * what the display shows in each, and whether the display showed any
     * element as current when it was not, or the warning as available when it
     * could not be given?
     */
  }
  connection hmiCurrencyValidationPlanning : ValidationPlanningAssociation
    connect needNoElementShownAsCurrentWhenItIsNot to hmiCurrencyValidationPlan;
  dependency hmiCurrencyValidationFromSceneAppOut
    from hmiCurrencyValidationPlan
    to DE4SDV_HmiDisplayOperationalContext::keepSpeedAndWarningWhenTheSceneAppIsOut;
  dependency hmiCurrencyValidationFromAndroidBoot
    from hmiCurrencyValidationPlan
    to DE4SDV_HmiDisplayOperationalContext::showSpeedAndWarningWhileAndroidBoots;
  dependency hmiCurrencyValidationFromAndroidHang
    from hmiCurrencyValidationPlan
    to DE4SDV_HmiDisplayOperationalContext::keepSpeedAndWarningWhileAndroidHangs;
  dependency hmiCurrencyValidationFromAndroidRestart
    from hmiCurrencyValidationPlan
    to DE4SDV_HmiDisplayOperationalContext::keepSpeedAndWarningThroughAndroidRestart;
  dependency hmiCurrencyValidationFromMissingRequest
    from hmiCurrencyValidationPlan
    to DE4SDV_HmiDisplayOperationalContext::showWarningUnavailableWhenTheRequestStops;

  part <'SC-HMI-013'> hmiDisplayIdentityValidationPlan : ValidationPlanningScenario {
    doc /*
     * For NEED-HMI-006, a planned stakeholder review. While the seven
     * scenarios run (SC-HMI-001 to SC-HMI-007), can verification engineers and
     * product-line engineers tell from each run which build and which
     * configuration of the HMI display ran and which candidate revision the
     * run of the driver-assistance system identifies, whether each verdict is
     * bound to them, and whether a display with a changed build or setting
     * identifies itself as a different one?
     */
  }
  connection hmiDisplayIdentityValidationPlanning : ValidationPlanningAssociation
    connect needRunsIdentifyTheDisplay to hmiDisplayIdentityValidationPlan;
  dependency hmiDisplayIdentityValidationFromWarningScenarios
    from hmiDisplayIdentityValidationPlan
    to DE4SDV_HmiDisplayOperationalContext::showWarningInTheWarningScenarios;
  dependency hmiDisplayIdentityValidationFromNoReactionScenarios
    from hmiDisplayIdentityValidationPlan
    to DE4SDV_HmiDisplayOperationalContext::showNoWarningInTheNoReactionScenarios;
  dependency hmiDisplayIdentityValidationFromSceneAppOut
    from hmiDisplayIdentityValidationPlan
    to DE4SDV_HmiDisplayOperationalContext::keepSpeedAndWarningWhenTheSceneAppIsOut;
  dependency hmiDisplayIdentityValidationFromAndroidBoot
    from hmiDisplayIdentityValidationPlan
    to DE4SDV_HmiDisplayOperationalContext::showSpeedAndWarningWhileAndroidBoots;
  dependency hmiDisplayIdentityValidationFromAndroidHang
    from hmiDisplayIdentityValidationPlan
    to DE4SDV_HmiDisplayOperationalContext::keepSpeedAndWarningWhileAndroidHangs;
  dependency hmiDisplayIdentityValidationFromAndroidRestart
    from hmiDisplayIdentityValidationPlan
    to DE4SDV_HmiDisplayOperationalContext::keepSpeedAndWarningThroughAndroidRestart;
  dependency hmiDisplayIdentityValidationFromMissingRequest
    from hmiDisplayIdentityValidationPlan
    to DE4SDV_HmiDisplayOperationalContext::showWarningUnavailableWhenTheRequestStops;

  /* ─────────────────────────────── Views ─────────────────────────────── */

  concern hmiDisplayNeedsConcern : StakeholderNeedsConcern {
    doc /*
     * Systems engineers and product-line engineers need the stakeholder needs
     * of the HMI display with their statements and sources, and the planned
     * stakeholder review of each, to judge whether the needs cover the
     * concerns of phase 1.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder productLineEngineer : ProductLineEngineer;
  }

  view hmiDisplayNeedsView : TVD::TableView {
    viewpoint selectedNeedsViewpoint : StakeholderRequirementDefinitionViewpoint {
      frame hmiDisplayNeedsConcern;
    }

    expose needPerceivedSceneOnTheDisplay;
    expose needVehicleSpeedOnTheDisplay;
    expose needCollisionWarningOnRequest;
    expose needSpeedAndWarningThroughOutages;
    expose needNoElementShownAsCurrentWhenItIsNot;
    expose needRunsIdentifyTheDisplay;
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

  view hmiDisplayNeedValidationView : TVD::TableView {
    viewpoint selectedNeedValidationViewpoint : StakeholderRequirementDefinitionViewpoint {
      frame hmiDisplayNeedsConcern;
    }

    expose hmiSceneValidationPlan;
    expose hmiSpeedValidationPlan;
    expose hmiWarningValidationPlan;
    expose hmiOutageValidationPlan;
    expose hmiCurrencyValidationPlan;
    expose hmiDisplayIdentityValidationPlan;
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
