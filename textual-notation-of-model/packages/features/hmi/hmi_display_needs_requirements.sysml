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
 * Each of these seven concerns asks to see an answer that the model gives
 * elsewhere, the view of a later phase or, for the common content, the
 * classification of phase 3 and the lifecycle decision, and the HMI display
 * gives its roles nothing that they use in their own work:
 * hmiDisplayInputsConcern, held by systems engineers and safety experts, and
 * hmiContentVarianceConcern, held by product-line engineers, ask about the
 * items that cross into the display and about its common content, and
 * NEED-HMI-001 names them; hmiWarningSequenceConcern, held by safety experts
 * and systems engineers, asks about the sequence of the warning, and
 * NEED-HMI-003 names it; hmiAndroidOutageConcern, held by safety experts and
 * systems engineers, hmiRendererAllocationConcern, held by product-line
 * engineers and safety experts, and hmiRendererPathConcern, held by system
 * architects and systems engineers, ask about the outages, the renderers and
 * their paths, and NEED-HMI-004 names them; hmiContentCurrencyConcern, held by
 * safety experts and verification engineers, asks about the states of each
 * element, and NEED-HMI-005 names it. The stakeholder needs of the
 * driver-assistance increment and of the E/E architecture increment keep such
 * concerns as reviewer questions in the same way.
 *
 * The needs name no drawing: how the app in the IVI VM draws the scene is a
 * choice of phase 8, and the visual design stays out of scope
 * (hmiHumanFactorsOutOfScope). No need asks for gear, set speed, speed limit
 * or another telltale (hmiFurtherContentOutOfScope).
 *
 * The owner decided on 2026-11-22 that the display shows what the
 * driver-assistance system perceives, right or wrong, with the object that the
 * system acts on marked, and not only what reaches the control of the vehicle:
 * the display-rule decision of 2026-11-22. NEED-HMI-001 and its review carry
 * it.
 *
 * Phase 5: the requirements derived from these needs, each with one subject,
 * the HMI display, one verification method and its success criteria. They
 * derive from the needs and rest on REQ-AEBS-002 and REQ-AEBS-013, and the
 * scope of the increment caps them at ten. From the driver-assistance
 * increment the terms take the form of the warning request and the start of
 * each mode; from the files of VisionPilot at 014e0e7a they take the levels,
 * the fixed distance of 150 m and the sign that the fusion declares for the
 * speed of the closest object. The rationales name those files by their file
 * names, and upstream.md gives each with its path. Set here, each with its
 * reason in a rationale: the speed of the closest object as its fusion gives
 * it; the object that the system acts on; distances to the whole metre and
 * speeds to the whole km/h; the vehicle speed at the input of the
 * driver-assistance system; the share of the HMI display in the time that the
 * driver-assistance increment allots from the warning request to each mode,
 * 0.1 s of wall-clock time, which every change of what the display shows takes
 * as its presentation time; the limits of 0.2 s of simulation time and of
 * 0.2 s of wall-clock time beyond which an element is outdated; the warning
 * unavailable while the warning request is outdated; and the split of the
 * renderers, by the owner's decision of 2026-11-17. The comments on
 * gapHmiWarningPresentation and gapHmiWarningAvailability give what phase 5
 * fixes of those gaps and what stays open, and the comment on
 * gapHmiRendererIntegration gives what the criteria ask of System 2.
 *
 * Rule 5 of the increment workflow makes a requirement core when its subject
 * has no link and it has none of its own. Phase 3 classes the HMI display as
 * content of every member of the governed scope and leaves open which of its
 * content is common, so phase 9 claims no member. In the framing, phase 9
 * makes the system of interest depend on the features visionPilot and
 * guestAndroidSDV. Every requirement follows it, and none carries a link of
 * its own. REQ-HMI-003 to REQ-HMI-007 name no variant beyond their subject.
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
    require constraint statement { language "English" /* Vehicle occupants need the HMI display to show the driver the scene as the driver-assistance system gives it from its own perception: its lane, the path it fits to that lane, the objects it detects with their level relative to that path, and, marked apart from the other objects, the closest object in its path, which the system acts on, with the distance and the speed that its fusion gives. */ }
    attribute :>> source = "INC-HMI-001 hmiDriverSupervisionConcern, hmiDisplayInputsConcern, hmiContentVarianceConcern, scope item hmiSceneInScope, gaps gapHmiSceneOutput and gapHmiSceneContent, scenarios SC-HMI-001 and SC-HMI-002";
    attribute :>> rationale = "The display shows the driver what the driver-assistance system perceives, right or wrong, with the object that the system acts on marked, so that the driver can supervise the system with it, and it shows the scene that the system gives and no other (the display-rule decision of 2026-11-22). At the inspected revision the system gives no such output (gapHmiSceneOutput), and what the scene carries bounds what the display can show of it (gapHmiSceneContent). The need states what the driver expects to see, not how a driver reads it, and carries no safety claim. Phase 5 derives its requirements. Phase 5 also derives from this need the requirements on the items that cross into the display, and states which requirements on the content of the display are core and which follow the driving application: its source names their concerns, and SC-HMI-008 asks their questions.";
  }

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

  requirement <'NEED-HMI-004'> needSpeedAndWarningThroughOutages : StakeholderNeedCandidate {
    subject hmiDisplay :> DE4SDV_HmiDisplayFraming::hmiDisplaySystem;
    stakeholder occupant : VehicleOccupant;
    require constraint statement { language "English" /* Vehicle occupants need the HMI display to show the driver the vehicle speed and to give the collision warning when it is requested, or, when the warning cannot be given, to show that it is unavailable, also while the app that draws the scene hangs or ends and while Android in the IVI VM hangs, boots or restarts. */ }
    attribute :>> source = "INC-HMI-001 hmiDriverSupervisionConcern, hmiAndroidOutageConcern, hmiRendererAllocationConcern, hmiRendererPathConcern, scope items hmiAndroidOutageInScope and hmiRendererSplitInScope, gaps gapHmiRendererIntegration and gapHmiMemberGuestLayout, scenarios SC-HMI-003 to SC-HMI-006";
    attribute :>> rationale = "While the drawing of the scene or Android in the IVI VM is out, the driver-assistance system goes on driving the vehicle, and the driver still needs the speed and the warning then, or to know that the warning cannot come. NEED-HMI-002 and NEED-HMI-003 state the speed and the warning; this need adds that they stay through each outage. It rests on N-AEBS-008, the need of the product line that the availability of the AEBS be apparent, and on the status indication of REQ-AEBS-013. Each outage is an event inside the boundary of the display, whose detection phases 6 to 8 decide. The need names no renderer and carries no safety claim. Phase 5 derives its requirements and their limits. Phase 5 also derives from this need the requirements on the sequence from each outage to what the display shows, on which renderer draws each element and on the paths of the inputs to the renderers: its source names their concerns, and SC-HMI-011 asks their questions.";
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
     * that the driver-assistance system gave, whether the display marked the
     * closest object in the path apart from the other objects, and whether the
     * display showed any object that the system did not give, from the
     * simulator's record of the scene or from an estimate of the display's
     * own? Can systems engineers and safety experts tell which items cross
     * into the HMI display from outside its boundary, the lane of the
     * driver-assistance system, the path it fits to that lane, the objects it
     * detects with their level relative to its path, the closest object in its
     * path with the distance and the speed that its fusion gives, the vehicle
     * speed that the system is given and its warning request, and whether each
     * reaches the display as its source gives it? And can product-line
     * engineers tell which content of the HMI display is common to the member
     * products and which derives from a member's driving application?
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
     * throughout and got the collision warning for each warning request, or,
     * where the warning could not be given, saw that it was unavailable? Can
     * safety experts and systems engineers follow the sequence from each
     * outage of the drawing of the scene and of the environment that hosts it,
     * the drawing hanging or ending and its host hanging, booting or
     * restarting, to its detection and to what the display shows then,
     * independent of the elements that realize it? Can product-line engineers
     * and safety experts tell which renderer realizes the drawing of each
     * element of the HMI display, and whether the split that the owner decided
     * on 2026-11-17, the high availability renderer in an SDV Media VM for the
     * speed, the collision warning and its sound and an app in the IVI VM for
     * the scene, keeps what the driver sees while Android in the IVI VM hangs,
     * boots or restarts? And can system architects and systems engineers tell
     * which elements exchange each input of the HMI display on its way from
     * the SDV Core VM to the high availability renderer in the SDV Media VM
     * and to the app in the IVI VM that draws the scene, by which exchange
     * that app tells the renderer that Android is alive, and by which boundary
     * interface each input enters the display?
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

  /* ───────────────────── Phase 5: requirements ───────────────────── */

  comment termsHmiDisplayRequirements
    /*
     * Terms of the requirements of the HMI display below, which the needs
     * above use in the same sense.
     * - Driver-assistance system: the candidate application that drives the
     *   vehicle in the configuration that the HMI display serves. It gives the
     *   scene and the warning request, and the vehicle gives it the vehicle
     *   speed.
     * - Result pass: a pass of the loop of the driver-assistance system in
     *   which it gives an inference result. At 014e0e7a VisionPilot makes one
     *   pass for each camera image that it takes, and the bench of the
     *   driver-assistance increment gives it one each 0.1 s of simulation
     *   time.
     * - Scene: the output of the driver-assistance system for one result pass,
     *   in the form of the scene of the panel of VisionPilot at 014e0e7a, with
     *   the speed of the closest object and the time of the scene, which that
     *   scene lacks: the lane points, the path that the system fits to its
     *   lane, the objects it detects, each with its level, and the closest
     *   object in its path that its fusion gives, with its validity, its
     *   distance and its speed.
     * - Level: the class that the driver-assistance system gives an object it
     *   detects, relative to its path: 1 for the same lane, 2 for the adjacent
     *   lane, and any other class as the system gives it.
     * - Object that the system acts on: the closest object of a scene when the
     *   fusion of the driver-assistance system gives it as valid at a distance
     *   below 150 m. A scene whose closest object lies at 150 m or more, the
     *   fixed distance of 150 m included, has none.
     * - Distance: the distance of the closest object of a scene, in m, as the
     *   fusion of the driver-assistance system gives it.
     * - Speed of the closest object: the speed of the closest object of a
     *   scene, in m/s, as the fusion of the driver-assistance system gives it,
     *   negative when the object approaches.
     * - Vehicle speed: the speed of the vehicle in km/h, with its sample time
     *   in simulation time, as the vehicle gives it to the driver-assistance
     *   system at its input. Each sample is one vehicle speed.
     * - Warning request: the input by which the HMI display is asked for the
     *   collision warning, in the form that the driver-assistance increment
     *   gives it at its boundary: one event for each plan of the
     *   driver-assistance system, telling whether it requests the collision
     *   warning, with its issue time in simulation time.
     * - Ask: the warning request asks while its newest event that has reached
     *   the HMI display is current and requests the collision warning.
     * - Start of a request: the event of the warning request with which the
     *   asking begins: the first event that makes the warning request ask
     *   after an instant at which it asks for no collision warning.
     * - Collision warning: the warning to the driver of an imminent collision,
     *   which the HMI display gives in two modes, on the display and as a
     *   sound.
     * - Mode: one of the two forms of the collision warning: the warning on
     *   the display, or the warning as a sound.
     * - Start of a mode: for the mode on the display, the first frame on the
     *   display with the warning; for the sound, the start of the sound, as
     *   the realization of the driver-assistance increment takes the start of
     *   each mode.
     * - Presentation time: the 0.1 s of wall-clock time that REQ-HMI-005 sets
     *   from the start of a request reaching the HMI display to the start of
     *   each mode, which the other requirements take for each change of what
     *   the HMI display shows.
     * - Within: a time within a span after an instant is less than that span
     *   after it.
     * - Input: the scene, the vehicle speed or the warning request, each a
     *   series of values that reach the HMI display: scenes, vehicle speeds or
     *   events of the warning request.
     * - Time of a value: the time in simulation time that a value of an input
     *   carries as its source gives it: for a scene, the capture time of the
     *   camera image of its result pass; for a vehicle speed, its sample time;
     *   for an event of the warning request, its issue time. The newest value
     *   of an input is the one with the latest time.
     * - Element: each thing that the HMI display shows from an input: the
     *   scene, which holds the object that the system acts on, and the vehicle
     *   speed.
     * - Current: a value of an input is current while the time of the value is
     *   at most 0.2 s of simulation time older than the newest time of a value
     *   that has reached the HMI display, and the newest value of the same
     *   input reached it at most 0.2 s of wall-clock time before. An element
     *   is current while it shows a current value, and the warning request is
     *   current while its newest event is current.
     * - Outdated: an element or the warning request is outdated at each
     *   instant at which it is other than current: a value that comes late and
     *   a value that never comes count alike, and so does the time before the
     *   first value of its input reaches the HMI display.
     * - Reach: a value reaches the HMI display when it arrives at the boundary
     *   of the display from the path that carries it there.
     * - Outage in the IVI VM: the time from the start of a hang or the end of
     *   the app in the IVI VM that draws the scene, or of a hang, a boot or a
     *   restart of Android in the IVI VM, until that app gives its first frame
     *   on the display after it.
     * - Display identity: the SHA-256 of the files of the build of the high
     *   availability renderer in the SDV Media VM, of the files of the build
     *   of the app in the IVI VM that draws the scene, of the image of the IVI
     *   VM and of the SDV Media VM, and of the sound file of the collision
     *   warning; the SHA-256 of each configuration file that the HMI display
     *   reads at its start; and the settings of its start, verbatim.
     * - Run: one execution of the HMI display on one scenario of SC-HMI-001 to
     *   SC-HMI-007, from its start to its end.
     * - Simulation time: the time of the simulated world.
     * - Wall-clock time: the time of the host.
     */

  requirement <'REQ-HMI-001'> reqShowTheSceneAsGiven : FunctionalRequirementCandidate {
    subject hmiDisplay :> DE4SDV_HmiDisplayFraming::hmiDisplaySystem;
    require constraint statement { language "English" /* The HMI display shall show, within the presentation time, each scene that reaches it outside an outage in the IVI VM, or a newer scene, as the driver-assistance system gives it. */ }
    attribute :>> source = "NEED-HMI-001; hmiDisplayInputsConcern; hmiContentVarianceConcern; scope item hmiSceneInScope; gaps gapHmiSceneOutput and gapHmiSceneContent; scenarios SC-HMI-001 to SC-HMI-007";
    attribute :>> rationale = "The driver supervises the driver-assistance system with what it perceives, right or wrong, so the display shows the scene that the system gives and no other. At 014e0e7a the system builds a scene only inside its own visualization, in a build with the option ENABLE_OCCUPANCY and with the visualization switched on (visual_interface.cpp:645-648; vision_pilot.cpp:177). The bridge of its panel builds it from the lane points of AutoSteer placed on the road through the homography that the system loads, the path that the lateral fusion fits, the offset and the heading of the vehicle in its lane, the detections of AutoSpeed as boxes with a score and a class, and the validity and the distance of the closest object, and it does not read the plan (occupancy_bridge.cpp:20-77). That scene carries no speed of the closest object and no time, and the inference result carries a frame identity and no capture time (occupancy_view.hpp:23-48; inference.hpp:38-52). So the scene that the display takes is an output that the system does not give yet (gapHmiSceneOutput), and what it carries bounds what the display can show of it (gapHmiSceneContent). The scene is the one input whose form follows the driving application, so this requirement and REQ-HMI-002 follow it. The display may skip a scene only for a newer one. The presentation time bounds the delay, so that a display that shows each scene late cannot hide behind REQ-HMI-006. During an outage in the IVI VM the app that draws the scene cannot show it; REQ-HMI-006 then shows the scene as outdated, and once the app gives its first frame again this requirement holds again. A display that shows the simulator's record of the scene or an estimate of its own shows another scene (hmiSimulatorTruthOutOfScope).";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when each of SC-HMI-001 to SC-HMI-007 has at least one run, each run of SC-HMI-004 and SC-HMI-006 has the end of its outage in the IVI VM before its own end, and in each run every scene that reaches the HMI display outside an outage in the IVI VM, or a newer scene, is on the display less than 0.1 s of wall-clock time after it arrives, with its lane points, its path and each of its objects with its level, as many objects as the scene gives and at the positions that it gives, read within the drawing tolerance that phase 8 states; and when no frame on the display shows a lane, a path or an object that no scene of the run gives, from the simulator's record of the scene or from an estimate of the display's own.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-HMI-002'> reqMarkTheObjectTheSystemActsOn : FunctionalRequirementCandidate {
    subject hmiDisplay :> DE4SDV_HmiDisplayFraming::hmiDisplaySystem;
    require constraint statement { language "English" /* With each scene that it shows, the HMI display shall show the object that the system acts on, when the scene has one, and no other object, as an element of its own apart from the objects of the scene, with its distance to the whole metre and the speed of the closest object to the whole km/h. */ }
    attribute :>> source = "NEED-HMI-001; scope item hmiSceneInScope; gap gapHmiSceneContent; scenarios SC-HMI-001 and SC-HMI-002";
    attribute :>> rationale = "NEED-HMI-001 asks for the closest object in the path, which the system acts on, marked apart from the other objects. At 014e0e7a the fusion takes as the closest object the nearest detection of the first level, or of the second when that one is nearer, a cut-in (longitudinal_fusion.cpp:181-182, 207-210), and fuses its distance with the distance that AutoDrive gives where AutoDrive flags an object in the path. Where AutoSpeed gives no detection of the first level and AutoDrive flags no object in the path, the fusion still gives a valid closest object at a fixed distance of 150 m (longitudinal_fusion.cpp:56, 63-73), and the system plans on the closest object only when it is valid and nearer than 150 m (vision_pilot.cpp:147-150). So the object that the system acts on is that one, and no object is marked at the fixed distance. The value of 150 m is compared when the pin moves, and a change revises the term. The scene names no detection as the closest object, so the display shows that object as an element of its own and marks no detection as it: choosing a box would be an estimate of the display's own. The fusion gives the distance in m and the speed in m/s, negative when the object approaches, as its own declaration states (longitudinal_fusion.hpp:17-18); the display shows that speed with its sign, in km/h. The whole metre is the resolution of the system's own label of the distance (visual_interface.cpp:304-323), and the whole km/h is set here for each speed on the display. The scene of the panel gives no speed of the closest object, so the scene that the display takes carries it (REQ-HMI-001). The mark that the visualization draws from AutoDrive alone (occupancy_bridge.cpp:79-84) is no closest object of the fusion, and the display shows no such mark as that object.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when each of SC-HMI-001 and SC-HMI-002 has at least one run whose scenes give an object that the system acts on, and in each run of SC-HMI-001 to SC-HMI-007 each frame on the display that shows a scene shows, as an element of its own, the object that the system acts on of that scene when it has one and no such element when it has none, the fixed distance of 150 m included; marks no box of the objects and no mark of AutoDrive alone as that object; and shows its distance as the distance of the scene rounded to the whole metre and its speed as the speed of the closest object of the scene times 3.6, rounded to the whole km/h, with its sign.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-HMI-003'> reqShowTheVehicleSpeed : FunctionalRequirementCandidate {
    subject hmiDisplay :> DE4SDV_HmiDisplayFraming::hmiDisplaySystem;
    require constraint statement { language "English" /* The HMI display shall show, within the presentation time, each vehicle speed that reaches it, or a newer one, to the whole km/h. */ }
    attribute :>> source = "NEED-HMI-002; scope item hmiSpeedInScope; scenarios SC-HMI-001, SC-HMI-002 and SC-HMI-007";
    attribute :>> rationale = "The driver supervises the driver-assistance system with the same speed that the system acts on (NEED-HMI-002). In the realization of the driver-assistance increment the vehicle speed enters the system with its sample time in simulation time, typed by COVESA VSS in km/h (VehicleSpeedSamplePayload and MAP-DRIVING-DA-VEHICLE-SPEED), and the system reads it once in each result pass. The display takes the speed of each world snapshot that reaches the input of the system, not the copy that the system reads in each result pass (MAP-DRIVING-DA-VEHICLE-SPEED): the signal is the same, and the snapshots go on when the system gives no result. The vehicle gives the speed, and which element brings it to the display is for the architecture phases (vehicleSpeedSourceComment). The display may skip a sample only for a newer one, and the presentation time bounds the delay. Before the first vehicle speed of a run reaches the display there is no speed to show, and REQ-HMI-006 shows the element as outdated. In the runs of SC-HMI-003 to SC-HMI-006, REQ-HMI-008 judges this obligation through each outage.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when each of SC-HMI-001, SC-HMI-002 and SC-HMI-007 has at least one run, and in each of their runs each speed on a frame on the display is the value of a vehicle speed of the run that has reached the HMI display, rounded to the whole km/h; each vehicle speed that reaches the HMI display, or a newer one, is on the display less than 0.1 s of wall-clock time after it arrives; and no frame shows a speed from another source, a fixed value of the display's own, or a speed before the first vehicle speed of the run reaches the HMI display.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-HMI-004'> reqCollisionWarningWhileRequested : FunctionalRequirementCandidate {
    subject hmiDisplay :> DE4SDV_HmiDisplayFraming::hmiDisplaySystem;
    require constraint statement { language "English" /* The HMI display shall give the collision warning on the display and as a sound while, and only while, the warning request asks for it, each mode following each change of the asking within the presentation time. */ }
    attribute :>> source = "NEED-HMI-003; REQ-AEBS-002; hmiWarningSequenceConcern; scope item hmiCollisionWarningInScope; gap gapHmiRendererCollisionWarning; scenarios SC-HMI-001, SC-HMI-002 and SC-HMI-007";
    attribute :>> rationale = "The display gives the warning so that the driver can act on an imminent collision, and none without a request (NEED-HMI-003). The warning request is the output that the driver-assistance increment realizes from the warnings of each plan: one event for each plan, which asks for the collision warning when the plan holds the forward-collision warning or the emergency braking and carries the capture time in simulation time of the frame that the plan came from, with no value changed on its path (CollisionWarningRequestOutput and MAP-DRIVING-DA-WARNING-REQUEST). The request does not tell the two apart, so the display gives one collision warning for both. The request carries no end, so the warning lasts while the request asks: a continuing request continues the warning, and the warning ends once the request asks for none or is outdated, when REQ-HMI-007 shows that it is unavailable. Each mode follows each change within the presentation time that REQ-HMI-005 sets, at the start and at the end alike. The term takes only the form of the request, so the requirement names no variant. It rests on REQ-AEBS-002, the collision warning that the product line asks for; whether a warning is due is the decision of the driver-assistance system, which that increment judges. The vehicle data of the renderer holds no collision warning yet (gapHmiRendererCollisionWarning). In the runs of SC-HMI-003 to SC-HMI-006, REQ-HMI-008 judges this obligation through each outage. No safety claim is made.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when each run of SC-HMI-001 has at least one start of a request that reaches the HMI display, and in each run of SC-HMI-001, SC-HMI-002 and SC-HMI-007 each mode of the collision warning is on from less than 0.1 s of wall-clock time after each start of a request reaches the HMI display until less than 0.1 s of wall-clock time after the warning request ends its asking, and at no other time, with no recording or overlay in place of either mode.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-HMI-005'> reqStartEachWarningModeWithinLimit : RequirementCandidate {
    subject hmiDisplay :> DE4SDV_HmiDisplayFraming::hmiDisplaySystem;
    require constraint statement { language "English" /* When the start of a request reaches the HMI display, the HMI display shall start each mode of the collision warning within 0.1 s of wall-clock time. */ }
    attribute :>> source = "NEED-HMI-003; REQ-AEBS-002; hmiWarningSequenceConcern; gap gapHmiWarningPresentation; scenarios SC-HMI-001 and SC-HMI-002";
    attribute :>> rationale = "This is a performance requirement on the share of the HMI display in the time that the driver-assistance increment allots from the warning request to each mode. REQ-DRIVING-042 allots 0.2 s of wall-clock time to the Eclipse S-CORE path and the AAOS SDV together, and the realization of that increment divides it, on its path to its own app on the IVI VM, into 0.1 s for the path and 0.1 s for the presentation, from the receipt to the first frame with the warning and to the start of the sound (MAP-DRIVING-DA-WARNING-REQUEST). The boundary of the HMI display lies at the SDV Core VM, with the Eclipse S-CORE path outside it and the paths from the SDV Core VM inside it, so the share of the display starts when the start of a request reaches it. Unlike that division, whose path share runs to the receipt on the IVI VM, the share of the display also holds the paths from the SDV Core VM to the renderer and to the app. The 0.1 s is chosen here by analogy with that division and leaves the other 0.1 s to the part before the boundary. It is unmeasured for the high availability renderer and for the sound, and it is revisited when a readiness probe measures them (gapHmiWarningPresentation). Within is strict, so a mode that starts exactly at the limit is late. A mode starts at its start of a mode; a recording or an overlay in place of a mode is no start. The limit counts in wall-clock time while the simulation runs no faster than wall-clock time, which is the obligation of System 2, and makes no timing claim for a vehicle.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when each run of SC-HMI-001 has at least one start of a request that reaches the HMI display, and for each start of a request that reaches the HMI display in a run of SC-HMI-001 or SC-HMI-002, the first frame on the display with the warning and the start of the sound each come less than 0.1 s of wall-clock time after it arrives, with no recording or overlay in place of either mode.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-HMI-006'> reqShowOutdatedElementsAsOutdated : FunctionalRequirementCandidate {
    subject hmiDisplay :> DE4SDV_HmiDisplayFraming::hmiDisplaySystem;
    require constraint statement { language "English" /* The HMI display shall show each element as outdated while, and only while, the element is outdated, following each change of its state within the presentation time. */ }
    attribute :>> source = "NEED-HMI-005; hmiContentCurrencyConcern; scope item hmiStaleContentInScope; scenarios SC-HMI-001 to SC-HMI-007";
    attribute :>> rationale = "The display shows no element as current when it is not, so that the driver supervises the driver-assistance system on what it perceives now (NEED-HMI-005). The scene and the warning request share one period of 0.1 s of simulation time in the realization of the driver-assistance increment: one camera image, one result pass, one plan and one event of the warning request each 0.1 s; the vehicle speed comes with each world snapshot at the input of the system, every step of 0.05 s. The limits of the term current take two periods, so that one late value is tolerated. The vehicle speed brings the newest time to the display with each world snapshot, so the limit in simulation time also counts the time from the capture of a frame to the arrival of its scene and its event at the display, and the time that the display takes to show the scene. While those times stay within one period together, a scene stays current until the next one is shown, and the warning request until its next event; with longer times an element can turn outdated before its next value comes, and the limit is revisited once a readiness probe measures them (warningPresentationFixedInPhase5). The limit in simulation time counts against the newest time that has reached the display, so it catches a delay before the display, which an age taken from the arrival would hide, and a value whose time the display changes. The limit in wall-clock time counts from the arrival of the newest value of the input, so it catches every input stopping, when the newest time stops as well. Late and missing values give one state, outdated, and phase 8 states how an outdated element looks; the visual design stays out of scope (hmiHumanFactorsOutOfScope). An element is shown as current again once it is current, which is the validity rule of the display; the converse, current while it is current, keeps a display from showing everything as outdated. The state of each element counts on its own, so a late scene leaves the vehicle speed current. No safety claim is made.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when each of SC-HMI-001 to SC-HMI-007 has at least one run, each run of SC-HMI-003 to SC-HMI-006 has its outage in the IVI VM and each run of SC-HMI-007 the stop of the Eclipse S-CORE path, and in each run each frame on the display shows each element as outdated, in the form that phase 8 states for it, from less than 0.1 s of wall-clock time after the element turns outdated until less than 0.1 s of wall-clock time after it turns current again, and as current at every other time; an element is outdated from the start of the run until a first current value of its input reaches the HMI display.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-HMI-007'> reqShowWarningUnavailableWhileRequestOutdated : FunctionalRequirementCandidate {
    subject hmiDisplay :> DE4SDV_HmiDisplayFraming::hmiDisplaySystem;
    require constraint statement { language "English" /* The HMI display shall show that the collision warning is unavailable while, and only while, the warning request is outdated, following each change of the state of the warning request within the presentation time. */ }
    attribute :>> source = "NEED-HMI-005; REQ-AEBS-013; hmiContentCurrencyConcern; gap gapHmiWarningAvailability; scenarios SC-HMI-001 to SC-HMI-007";
    attribute :>> rationale = "The display shows when the warning is unavailable, so that the driver can tell a warning that cannot come from one that is not due (NEED-HMI-005); it rests on N-AEBS-008, that the availability of the AEBS be apparent, and on the status indication of REQ-AEBS-013. This is the one degraded response of the set. The warning request carries no indication of its own availability (gapHmiWarningAvailability), and one of its events comes for each plan, telling whether it asks, so the display learns from their age that the warning cannot come: the warning is unavailable while the warning request is outdated. A signal of its own would need a change of the driver-assistance system (hmiCandidateChangeOutOfScope). The warning shows as available again once the warning request is current, which is the validity rule; the converse keeps a display from showing the warning as unavailable at all times. In SC-HMI-007 the Eclipse S-CORE path ends carrying the request, and the display shows the warning as unavailable while the driver still sees the vehicle speed. A renderer that cannot give the warning, such as a sound output that is out, is left for a later increment (warningAvailabilityFixedInPhase5). No safety claim is made.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when each of SC-HMI-001 to SC-HMI-007 has at least one run, each run of SC-HMI-007 has the stop of the Eclipse S-CORE path at least 0.3 s of wall-clock time before its end, and in each run the display shows that the collision warning is unavailable from less than 0.1 s of wall-clock time after the warning request turns outdated until less than 0.1 s of wall-clock time after it turns current again, and at no other time, so that the warning shows as available again only once an event of the warning request is current.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-HMI-008'> reqSpeedAndWarningThroughOutages : FunctionalRequirementCandidate {
    subject hmiDisplay :> DE4SDV_HmiDisplayFraming::hmiDisplaySystem;
    require constraint statement { language "English" /* Throughout each outage in the IVI VM, the HMI display shall show the vehicle speed, give the collision warning while the warning request asks for it, and show that the warning is unavailable while the warning request is outdated. */ }
    attribute :>> source = "NEED-HMI-004; REQ-AEBS-013; hmiAndroidOutageConcern; scope item hmiAndroidOutageInScope; scenarios SC-HMI-003 to SC-HMI-006";
    attribute :>> rationale = "While the drawing of the scene or Android in the IVI VM is out, the driver-assistance system goes on driving the vehicle, and the driver still needs the speed and the warning, or to know that the warning cannot come (NEED-HMI-004). The outages are those of the story: the app that draws the scene ends or hangs (SC-HMI-003), and Android in the IVI VM boots (SC-HMI-004), hangs (SC-HMI-005) or restarts (SC-HMI-006). REQ-HMI-003, REQ-HMI-004, REQ-HMI-005 and REQ-HMI-007 state the speed and the warning in every run; this requirement carries them through each outage, and its criteria judge them there. It rests on N-AEBS-008 and on the status indication of REQ-AEBS-013. Each outage is an event inside the boundary of the display, whose detection phases 6 to 8 decide (guestAcrossBoundaryComment). The speed and the warning hold throughout, the scene returns under REQ-HMI-001 once the app gives frames again, and until then REQ-HMI-006 shows it as outdated, within the limits of the term current and the presentation time from the last scene that the app has shown. No time from a restart to the scene is set here; that limit, and whether the HMI display meets those of REQ-HMI-006 through a hang of the app or of Android in the IVI VM, stay open with the owner until a probe measures them. No safety claim is made.";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when each of SC-HMI-003 to SC-HMI-006 has at least one run, each run has its outage in the IVI VM with at least one start of a request reaching the HMI display during it, and throughout the outage of each run each frame on the display and each mode of the collision warning meet what the criteria of REQ-HMI-003, REQ-HMI-004, REQ-HMI-005 and REQ-HMI-007 ask of them.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-HMI-009'> reqRendererSplitAndInputPaths : RequirementCandidate {
    subject hmiDisplay :> DE4SDV_HmiDisplayFraming::hmiDisplaySystem;
    require constraint statement { language "English" /* The HMI display shall draw the vehicle speed and the collision warning and give its sound by the high availability renderer in an SDV Media VM, and draw the scene by an app in the IVI VM, each taking its inputs from the SDV Core VM over paths inside the boundary of the HMI display. */ }
    attribute :>> source = "NEED-HMI-004; hmiRendererAllocationConcern; hmiRendererPathConcern; scope item hmiRendererSplitInScope; gaps gapHmiRendererIntegration and gapHmiMemberGuestLayout";
    attribute :>> rationale = "This is a design constraint on the realization of the HMI display, from the owner's decision of 2026-11-17: the high availability renderer in an SDV Media VM draws the speed and the collision warning and gives its sound, and an app in the IVI VM draws the scene, so that the speed and the warning do not depend on Android in the IVI VM (hmiRendererSplitInScope). The boundary puts the paths from the SDV Core VM inside the display and the Eclipse S-CORE path outside it. How a collision warning and its sound reach the renderer is open (gapHmiRendererCollisionWarning), and so is how the renderer and the guest fit a bench (gapHmiRendererIntegration). Phases 6 to 8 decide the elements on each path and how the app tells the renderer that Android is alive; this requirement fixes only the split and that the paths stay inside the boundary. It names the AAOS SDV guest, and phase 9 links it.";
    attribute :>> verificationMethod = "inspect";
    attribute :>> successCriteria = "Met when the inspection of the realization that phase 8 records shows the vehicle speed, the collision warning on the display and its sound in the high availability renderer in an SDV Media VM, the scene in an app in the IVI VM, and for each input the elements that carry it from the SDV Core VM to the renderer or to the app, all inside the boundary of the HMI display, with no other element drawing the vehicle speed or the collision warning.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  requirement <'REQ-HMI-010'> reqRecordDisplayIdentity : FunctionalRequirementCandidate {
    subject hmiDisplay :> DE4SDV_HmiDisplayFraming::hmiDisplaySystem;
    require constraint statement { language "English" /* The HMI display shall record its display identity before its first frame on the display in each run. */ }
    attribute :>> source = "NEED-HMI-006; hmiDisplayVerdictConcern; scope item hmiVerdictEvidenceInScope; assumption asmHmiSimulationStandsIn; scenarios SC-HMI-001 to SC-HMI-007";
    attribute :>> rationale = "A verdict holds only for the display that ran, and the configuration of the display is every setting that it reads at its start (NEED-HMI-006). The parts of the identity are pinned each on its own, because none of them fixes the others: the build of each of the two drawing elements, the image of each guest VM, the sound of the warning, the files of the configuration and the settings of the start. Each part is the SHA-256 of named files or a setting written out, so that another engineer can check it. The candidate revision is bound by the run of the driver-assistance system (NEED-DRIVING-011 and REQ-DRIVING-044), and the record of what that system gives, the captures and the evaluators belong to System 2 and are bound there. Like REQ-DRIVING-044, the record is a behaviour of the display in each run, which phase 6 allocates to a function. A verdict holds for the simulated configuration only (asmHmiSimulationStandsIn).";
    attribute :>> verificationMethod = "test";
    attribute :>> successCriteria = "Met when every run of SC-HMI-001 to SC-HMI-007 has the record of its display identity before its first frame on the display; when another engineer who hashes the named files obtains the recorded values; and when a display with one changed build, image, sound file, configuration file or start setting records a different display identity.";
    attribute :>> verificationStatus = VVStatus::NotStarted;
  }

  connection showTheSceneAsGivenDerivation : DerivesFromNeed
    connect needPerceivedSceneOnTheDisplay to reqShowTheSceneAsGiven;
  connection markTheObjectTheSystemActsOnDerivation : DerivesFromNeed
    connect needPerceivedSceneOnTheDisplay to reqMarkTheObjectTheSystemActsOn;
  connection showTheVehicleSpeedDerivation : DerivesFromNeed
    connect needVehicleSpeedOnTheDisplay to reqShowTheVehicleSpeed;
  connection collisionWarningWhileRequestedDerivation : DerivesFromNeed
    connect needCollisionWarningOnRequest to reqCollisionWarningWhileRequested;
  connection startEachWarningModeWithinLimitDerivation : DerivesFromNeed
    connect needCollisionWarningOnRequest to reqStartEachWarningModeWithinLimit;
  connection showOutdatedElementsAsOutdatedDerivation : DerivesFromNeed
    connect needNoElementShownAsCurrentWhenItIsNot to reqShowOutdatedElementsAsOutdated;
  connection showWarningUnavailableWhileRequestOutdatedDerivation : DerivesFromNeed
    connect needNoElementShownAsCurrentWhenItIsNot to reqShowWarningUnavailableWhileRequestOutdated;
  connection speedAndWarningThroughOutagesDerivation : DerivesFromNeed
    connect needSpeedAndWarningThroughOutages to reqSpeedAndWarningThroughOutages;
  connection rendererSplitAndInputPathsDerivation : DerivesFromNeed
    connect needSpeedAndWarningThroughOutages to reqRendererSplitAndInputPaths;
  connection recordDisplayIdentityDerivation : DerivesFromNeed
    connect needRunsIdentifyTheDisplay to reqRecordDisplayIdentity;

  comment warningPresentationFixedInPhase5 about DE4SDV_HmiDisplayFraming::gapHmiWarningPresentation
    /*
     * What phase 5 fixes of this gap, and what stays open. Fixed: the HMI
     * display starts each mode of the collision warning within 0.1 s of
     * wall-clock time after the start of a request reaches it (REQ-HMI-005),
     * its share of the 0.2 s of wall-clock time that the driver-assistance
     * increment allots from the warning request to each mode, and each change
     * of what it shows takes the same 0.1 s (the term presentation time).
     * Open: the 0.1 s is chosen by analogy with the division on the path to
     * the app of the driver-assistance increment and is unmeasured for the
     * high availability renderer, for the app that draws the scene and for the
     * sound; the owner revisits it when a readiness probe measures them.
     * Whether the time from the capture of a frame to the arrival of its scene
     * and its event at the HMI display, with the time to show the scene, stays
     * within one period of 0.1 s, as the limit in simulation time of the term
     * current needs, is open until a readiness probe measures it; a longer
     * time revises that limit. Which part of System 1 holds the other 0.1 s,
     * before the boundary of the display on the Eclipse S-CORE path, is for
     * the architecture phases of both increments. Whether a build of this
     * display replaces the app of the driver-assistance increment stays open;
     * the realization and the verdicts of that increment stay as they are.
     */

  comment warningAvailabilityFixedInPhase5 about DE4SDV_HmiDisplayFraming::gapHmiWarningAvailability
    /*
     * What phase 5 fixes of this gap, and what stays open. Fixed: the HMI
     * display learns that the collision warning is unavailable from the age of
     * the events of the warning request, with no signal of its own: the
     * warning is unavailable while the warning request is outdated, and
     * available again once it is current (REQ-HMI-007 and the term current).
     * Open, for a later increment: a renderer that cannot give the warning,
     * such as a sound output that is out or a high availability renderer that
     * cannot draw it, makes the warning unavailable as well, and no
     * requirement of this increment states what the display shows then. A
     * signal of the driver-assistance system of its own stays a change of that
     * system, out of scope here.
     */

  comment hmiTestbedObligationsOfPhase5 about DE4SDV_HmiDisplayFraming::gapHmiRendererIntegration
    /*
     * What the criteria of phase 5 ask of System 2: each is an obligation of
     * the verification environment and none a criterion of the HMI display.
     * The bench runs the simulation no faster than wall-clock time. The
     * records hold each value of each input as its source gives it, with its
     * simulation time, and where it reaches the HMI display, with the
     * wall-clock time of its arrival; each frame on the display and the start
     * of each sound, with their wall-clock times; and the files and the
     * settings that the display identity names. The fault injection makes the
     * outage of each run of SC-HMI-003 to SC-HMI-006 after the first value of
     * each input reaches the display and while at least one start of a request
     * reaches it, and the stop of the Eclipse S-CORE path in each run of
     * SC-HMI-007. It leaves at least 0.3 s of wall-clock time before the end
     * of the run, the longest response that the criteria judge: 0.2 s to turn
     * outdated and 0.1 s to show it. Each run of SC-HMI-004 and SC-HMI-006 has
     * a length that System 2 states before the run, so that the scene has to
     * return within it; a limit on that time stays open with the owner until a
     * probe measures the boot of Android in the IVI VM. How a frame on the
     * display is read against the scene that it shows, with the tolerance of a
     * drawn position, is set with the drawing in phase 8. Open: the bench of
     * the renderer and of the guest, and its readiness probe
     * (gapHmiRendererIntegration).
     */

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

  concern hmiDisplayRequirementTraceConcern : RequirementTraceConcern {
    doc /*
     * Verification engineers and open-source reviewers need each requirement
     * of the HMI display traced to the need it derives from, with its source,
     * its rationale, its verification method and its success criteria, to
     * judge whether the requirements answer the needs and can be verified. No
     * concern of the framing names this table: hmiDisplayVerdictConcern asks a
     * verdict for each requirement and scenario, and the table gives those
     * requirements.
     */
    subject;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view hmiDisplayRequirementsView : TVD::TableView {
    viewpoint selectedHmiRequirementDefinitionViewpoint : SystemRequirementDefinitionViewpoint {
      frame hmiDisplayRequirementTraceConcern;
    }

    expose reqShowTheSceneAsGiven;
    expose reqMarkTheObjectTheSystemActsOn;
    expose reqShowTheVehicleSpeed;
    expose reqCollisionWarningWhileRequested;
    expose reqStartEachWarningModeWithinLimit;
    expose reqShowOutdatedElementsAsOutdated;
    expose reqShowWarningUnavailableWhileRequestOutdated;
    expose reqSpeedAndWarningThroughOutages;
    expose reqRendererSplitAndInputPaths;
    expose reqRecordDisplayIdentity;
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
    }
  }
}
