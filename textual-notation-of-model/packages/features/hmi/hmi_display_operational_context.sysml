/*
 * DE4SDV HMI display: Phase 2 operational context.
 *
 * INC-HMI-001, phase 2: what happens in the world of the HMI display. The
 * candidate application of the driver-assistance increment gives its scene
 * and its warning request, the Eclipse S-CORE path carries the request, the
 * vehicle gives its speed, and the display shows the driver the scene and the
 * speed and gives the collision warning on the display and as a sound. The
 * candidate and the S-CORE path are System 1 parts outside the display, as
 * phase 0 draws the boundary. The story is the driver-assistance increment's
 * scenarios as the driver sees them on the display, with the outages in the
 * IVI VM added to them; it names those scenarios and restates none of them.
 * CARLA, the cloud hosts, the scenario runner, the means that make Android in
 * the IVI VM hang, end and restart, the captures, the evaluators and the
 * recordings are System 2 and stay out of this context. No human-factors,
 * timing, safety, compliance or production-readiness claim is made.
 */

package DE4SDV_HmiDisplayOperationalContext {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_OperationalContext::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_SYSMODAdapter::*;
  private import DE4SDV_HmiDisplayFraming::*;
  private import DE4SDV_DriverAssistanceFraming::DriverAssistanceSystem;
  private import DE4SDV_DriverAssistanceOperationalContext::VehicleSpeed;
  private import DE4SDV_DriverAssistanceOperationalContext::WarningRequest;
  private import DE4SDV_DriverAssistanceOperationalContext::CollisionWarning;
  private import DE4SDV_DriverAssistanceOperationalContext::SCORECommandAndWarningPath;
  private import SAF_Viewpoints::*;
  private import Views::*;

  /* ───────────────────── Phase 2: what happens in the world ───────────────────── */

  item def PerceivedScene {
    doc /*
     * The scene as the candidate gives it from its own perception: its lane,
     * the path it fits to that lane, the objects it detects with their level
     * relative to its path, and the closest object in its path with the
     * distance and the speed that its fusion gives. It holds nothing that the
     * candidate does not give: neither the simulator's record of the scene nor
     * an estimate of the display's own (hmiSimulatorTruthOutOfScope). At the
     * inspected revision the candidate gives no such output (gapHmiSceneOutput).
     */
  }

  item def HmiDisplayContent {
    doc /*
     * What the HMI display shows the driver beside the collision warning: the
     * scene as the candidate gives it, the vehicle speed, and the fact that the
     * warning is unavailable when it is, with no element shown as current when
     * it is not (hmiStaleContentInScope). The collision warning itself, on the
     * display and as a sound, is the collision warning of the driver-assistance
     * increment.
     */
  }

  part hmiDisplayOperationalContext : SystemContext {
    doc /*
     * The operational context of the HMI display of the VisionPilot
     * configuration. Inside the system of interest, as phase 0 draws it: what
     * the display shows and where, the app in the IVI VM that draws the scene,
     * the high availability renderer in an SDV Media VM that draws the speed
     * and the collision warning and gives the warning's sound, and the paths
     * from the SDV Core VM to both; it stays a black box until the
     * architecture phases. Around it: the candidate application, which gives
     * its scene and its warning request, the Eclipse S-CORE path, which carries
     * the warning request, the vehicle, which gives its speed, and the driver,
     * who only receives. The candidate and the S-CORE path are System 1 parts
     * outside the display and no enabling systems. The road, the vehicle
     * targets and the simulator reach the display only as the candidate
     * perceives them, so the context holds no part for them. System 1 roles
     * only: CARLA, the cloud hosts, the scenario runner, the means that make
     * Android in the IVI VM hang, end and restart, the record of what the
     * candidate gives, the capture of the display and of the sound, the
     * evaluators and the recordings stay in hmiDisplayVerificationEnvironment.
     * This is the operational environment, not a deployment decomposition.
     */
    part hmiDisplay : HmiDisplaySystem :>> systemOfInterest;
    part candidate : DriverAssistanceSystem {
      doc /*
       * The candidate application of the driver-assistance increment in the
       * VisionPilot configuration: it gives its scene and its warning request,
       * and the display sends it nothing (hmiCandidateChangeOutOfScope).
       */
    }
    part scorePath : SCORECommandAndWarningPath {
      doc /*
       * The Eclipse S-CORE path of the driver-assistance increment: it carries
       * the candidate's warning request to the SDV Core VM, where the display
       * takes it.
       */
    }
    part vehicle : SubjectVehicle {
      doc /*
       * The vehicle whose speed the display shows: the speed that the candidate
       * is given.
       */
    }
    part driver : Driver {
      doc /*
       * The driver, a vehicle occupant, who supervises the driver assistance on
       * the display and gets the collision warning on it and as a sound. Driver
       * interaction is out of scope (hmiDriverInteractionOutOfScope).
       */
    }
  }

  /* Operational behavior: the display takes the scene, the request and the speed; the driver only receives. */
  action def HmiDisplayOperation {
    doc /*
     * The display in the world: the candidate gives its scene and its warning
     * request, the Eclipse S-CORE path carries the request, the vehicle gives
     * its speed, and the display shows the driver the scene and the speed and
     * gives the collision warning on the display and as a sound. Nothing flows
     * back to the candidate, to the path or to the vehicle.
     */
    action giveSceneAndWarningRequest {
      doc /*
       * The candidate: gives the scene from its own perception and, when it
       * decides on a warning, the warning request.
       */
      out perceivedScene : PerceivedScene;
      out warningRequest : WarningRequest;
    }

    action carryWarningRequestOverSCORE {
      doc /*
       * The S-CORE path: carries the warning request to the SDV Core VM.
       */
      in warningRequest : WarningRequest;
      out carriedWarningRequest : WarningRequest;
    }

    flow from giveSceneAndWarningRequest.warningRequest to carryWarningRequestOverSCORE.warningRequest;
    first giveSceneAndWarningRequest then carryWarningRequestOverSCORE;

    action giveVehicleSpeed {
      doc /*
       * The vehicle: gives its speed, the speed that the candidate is given.
       */
      out vehicleSpeed : VehicleSpeed;
    }

    action showOnDisplay {
      doc /*
       * The HMI display: shows the scene as the candidate gives it and the
       * speed, shows no element as current when it is not, and gives the
       * collision warning on the display and as a sound when the warning
       * request arrives, or shows that the warning is unavailable.
       */
      in perceivedScene : PerceivedScene;
      in warningRequest : WarningRequest;
      in vehicleSpeed : VehicleSpeed;
      out shownContent : HmiDisplayContent;
      out collisionWarning : CollisionWarning;
    }

    flow from giveSceneAndWarningRequest.perceivedScene to showOnDisplay.perceivedScene;
    flow from carryWarningRequestOverSCORE.carriedWarningRequest to showOnDisplay.warningRequest;
    flow from giveVehicleSpeed.vehicleSpeed to showOnDisplay.vehicleSpeed;

    action superviseOnDisplay {
      doc /*
       * The driver: sees the display and gets the warning; nothing flows back
       * to the display.
       */
      in shownContent : HmiDisplayContent;
      in collisionWarning : CollisionWarning;
    }

    flow from showOnDisplay.shownContent to superviseOnDisplay.shownContent;
    flow from showOnDisplay.collisionWarning to superviseOnDisplay.collisionWarning;
  }

  action hmiDisplayOperation : HmiDisplayOperation;

  /* Operational story on the SYSMOD seam. */
  use case def SuperviseDriverAssistanceOnHmiDisplay :> SYSMODSystemUseCaseBase {
    doc /*
     * The HMI display in operation: in the scenarios of the driver-assistance
     * increment it shows the driver what the candidate perceives beside the
     * speed and gives the collision warning when the candidate requests it,
     * also while the app that draws the scene or Android in the IVI VM is out.
     */
    attribute redefines ucMotivation = "The driver, a vehicle occupant, needs to see on the HMI display what the driving application perceives beside the vehicle speed, to get the collision warning on the display and as a sound, and to see the speed and the warning, or the fact that the warning is unavailable, also while Android in the IVI VM hangs, boots or restarts.";
    attribute redefines ucTrigger = "The vehicle drives with the candidate active in a scenario of the driver-assistance increment: the candidate gives its scene and, when it decides on a warning, its warning request, and the vehicle gives its speed; at times the app that draws the scene ends or hangs, or Android in the IVI VM boots, hangs or restarts.";
    attribute redefines ucResult = "The display shows the scene as the candidate gives it and the speed, gives the collision warning on the display and as a sound when the warning request arrives, shows no element as current when it is not, and keeps the speed and the warning, or the fact that the warning is unavailable, apparent while the app that draws the scene or Android in the IVI VM is out.";

    objective {
      doc /*
       * Frame what the driver sees in the scenarios of the driver-assistance
       * increment and in each outage in the IVI VM, only. How the display
       * detects an outage is for the system process of phase 6; the criteria,
       * the age from which an element counts as late and how the time that the
       * driver-assistance increment allots from the warning request to each
       * mode divides (gapHmiWarningPresentation) are fixed with the
       * requirements (phase 5).
       */
    }
  }

  use case hmiDisplayStory : SuperviseDriverAssistanceOnHmiDisplay {
    subject hmiDisplay : HmiDisplaySystem = hmiDisplayOperationalContext::hmiDisplay;
    actor candidate : DriverAssistanceSystem = hmiDisplayOperationalContext::candidate;
    actor scorePath : SCORECommandAndWarningPath = hmiDisplayOperationalContext::scorePath;
    actor vehicle : SubjectVehicle = hmiDisplayOperationalContext::vehicle;
    actor driver : Driver = hmiDisplayOperationalContext::driver;

    objective {
      doc /*
       * Operate the HMI display without selecting the realization of an
       * element or of a path, and without any human-factors, safety, on-road,
       * compliance or production-readiness claim.
       */
    }

    first start;
    then include showWarningInTheWarningScenarios;
    then include showNoWarningInTheNoReactionScenarios;
    then include keepSpeedAndWarningWhenTheSceneAppIsOut;
    then include showSpeedAndWarningWhileAndroidBoots;
    then include keepSpeedAndWarningWhileAndroidHangs;
    then include keepSpeedAndWarningThroughAndroidRestart;
    then done;
  }

  use case showWarningInTheWarningScenarios {
    subject hmiDisplay : HmiDisplaySystem = hmiDisplayOperationalContext::hmiDisplay;
    actor candidate : DriverAssistanceSystem = hmiDisplayOperationalContext::candidate;
    actor scorePath : SCORECommandAndWarningPath = hmiDisplayOperationalContext::scorePath;
    actor vehicle : SubjectVehicle = hmiDisplayOperationalContext::vehicle;
    actor driver : Driver = hmiDisplayOperationalContext::driver;

    objective {
      doc /*
       * SC-HMI-001 (the warning scenarios of the driver-assistance increment on
       * the display): in SC-DRIVING-012 and SC-DRIVING-013 the display shows
       * the driver the candidate's lane, the path it fits to that lane and the
       * objects it detects, the closest object in its path among them with the
       * distance that its fusion gives, beside the vehicle speed. When the
       * candidate's warning request arrives, the driver gets the collision
       * warning on the display and as a sound. The display shows the vehicle
       * target as the candidate perceives it, right or wrong, never as the
       * simulator places it (hmiSimulatorTruthOutOfScope,
       * hmiPerceptionQualityOutOfScope). No human-factors or safety claim is
       * made.
       */
    }

    first start;
    then done;
  }

  use case showNoWarningInTheNoReactionScenarios {
    subject hmiDisplay : HmiDisplaySystem = hmiDisplayOperationalContext::hmiDisplay;
    actor candidate : DriverAssistanceSystem = hmiDisplayOperationalContext::candidate;
    actor vehicle : SubjectVehicle = hmiDisplayOperationalContext::vehicle;
    actor driver : Driver = hmiDisplayOperationalContext::driver;

    objective {
      doc /*
       * SC-HMI-002 (the no-reaction scenarios of the driver-assistance
       * increment on the display): in SC-DRIVING-014 and SC-DRIVING-015 the
       * display shows the scene as the candidate gives it, with the objects
       * that it detects outside its path, beside the vehicle speed, and no
       * warning request arrives, so the driver gets no collision warning. The
       * display gives a warning only on the candidate's request; whether one is
       * due is the candidate's decision, which the driver-assistance increment
       * judges (hmiCandidateChangeOutOfScope). No human-factors or safety claim
       * is made.
       */
    }

    first start;
    then done;
  }

  use case keepSpeedAndWarningWhenTheSceneAppIsOut {
    subject hmiDisplay : HmiDisplaySystem = hmiDisplayOperationalContext::hmiDisplay;
    actor candidate : DriverAssistanceSystem = hmiDisplayOperationalContext::candidate;
    actor scorePath : SCORECommandAndWarningPath = hmiDisplayOperationalContext::scorePath;
    actor vehicle : SubjectVehicle = hmiDisplayOperationalContext::vehicle;
    actor driver : Driver = hmiDisplayOperationalContext::driver;

    objective {
      doc /*
       * SC-HMI-003 (the app that draws the scene is out): during a scenario of
       * the driver-assistance increment the app that draws the scene ends, or
       * hangs with its last frame on the display. The display shows that the
       * scene is not current, never the last frame as current
       * (hmiStaleContentInScope), and the driver still sees the vehicle speed
       * and gets the collision warning on the display and as a sound when the
       * candidate requests it, or the fact that the warning is unavailable. No
       * human-factors or safety claim is made.
       */
    }

    first start;
    then done;
  }

  use case showSpeedAndWarningWhileAndroidBoots {
    subject hmiDisplay : HmiDisplaySystem = hmiDisplayOperationalContext::hmiDisplay;
    actor candidate : DriverAssistanceSystem = hmiDisplayOperationalContext::candidate;
    actor scorePath : SCORECommandAndWarningPath = hmiDisplayOperationalContext::scorePath;
    actor vehicle : SubjectVehicle = hmiDisplayOperationalContext::vehicle;
    actor driver : Driver = hmiDisplayOperationalContext::driver;

    objective {
      doc /*
       * SC-HMI-004 (Android in the IVI VM boots): during a scenario of the
       * driver-assistance increment, before Android in the IVI VM gives its
       * first frame, and so before the scene appears, the driver sees the
       * vehicle speed and the collision warning when the candidate requests it,
       * or the fact that the warning is unavailable. The scene appears once the
       * app that draws it gives its first frame. Whether the display learns
       * that the warning is unavailable from the age of its inputs or from a
       * signal of its own is open (gapHmiWarningAvailability). No human-factors
       * or safety claim is made.
       */
    }

    first start;
    then done;
  }

  use case keepSpeedAndWarningWhileAndroidHangs {
    subject hmiDisplay : HmiDisplaySystem = hmiDisplayOperationalContext::hmiDisplay;
    actor candidate : DriverAssistanceSystem = hmiDisplayOperationalContext::candidate;
    actor scorePath : SCORECommandAndWarningPath = hmiDisplayOperationalContext::scorePath;
    actor vehicle : SubjectVehicle = hmiDisplayOperationalContext::vehicle;
    actor driver : Driver = hmiDisplayOperationalContext::driver;

    objective {
      doc /*
       * SC-HMI-005 (Android in the IVI VM hangs): during a scenario of the
       * driver-assistance increment Android in the IVI VM hangs and its last
       * frame stays on the display. The display shows that the scene is not
       * current, never the last frame as current (hmiStaleContentInScope), and
       * the driver sees the vehicle speed and the collision warning when the
       * candidate requests it, or the fact that the warning is unavailable. No
       * human-factors or safety claim is made.
       */
    }

    first start;
    then done;
  }

  use case keepSpeedAndWarningThroughAndroidRestart {
    subject hmiDisplay : HmiDisplaySystem = hmiDisplayOperationalContext::hmiDisplay;
    actor candidate : DriverAssistanceSystem = hmiDisplayOperationalContext::candidate;
    actor scorePath : SCORECommandAndWarningPath = hmiDisplayOperationalContext::scorePath;
    actor vehicle : SubjectVehicle = hmiDisplayOperationalContext::vehicle;
    actor driver : Driver = hmiDisplayOperationalContext::driver;

    objective {
      doc /*
       * SC-HMI-006 (Android in the IVI VM restarts): during a scenario of the
       * driver-assistance increment Android in the IVI VM ends and boots again.
       * From its end until its first frame the display shows no scene as
       * current, and the driver sees the vehicle speed and the collision
       * warning when the candidate requests it, or the fact that the warning is
       * unavailable; then the scene appears again. No human-factors or safety
       * claim is made.
       */
    }

    first start;
    then done;
  }

  /* Traces to the Phase 0 records this context implements. */
  dependency hmiDisplayStoryAnswersProblem
    from hmiDisplayStory
    to DE4SDV_HmiDisplayFraming::hmiDisplayProblem;
  dependency candidateOnDrivingBenchReuse
    from hmiDisplayOperationalContext::candidate
    to DE4SDV_HmiDisplayFraming::asmHmiDrivingBenchReuse;
  dependency scorePathOnDrivingBenchReuse
    from hmiDisplayOperationalContext::scorePath
    to DE4SDV_HmiDisplayFraming::asmHmiDrivingBenchReuse;
  dependency perceivedSceneOnSceneOutputGap
    from PerceivedScene
    to DE4SDV_HmiDisplayFraming::gapHmiSceneOutput;
  dependency perceivedSceneOnSceneContentGap
    from PerceivedScene
    to DE4SDV_HmiDisplayFraming::gapHmiSceneContent;
  dependency outageScenariosOnWarningAvailabilityGap
    from hmiDisplayStory
    to DE4SDV_HmiDisplayFraming::gapHmiWarningAvailability;
  dependency hmiDisplayContentOnWarningAvailabilityGap
    from HmiDisplayContent
    to DE4SDV_HmiDisplayFraming::gapHmiWarningAvailability;

  /* The scenarios of the driver-assistance increment that the story shows, by reference, never restated. */
  dependency hmiDisplayStoryInDrivingStory
    from hmiDisplayStory
    to DE4SDV_DriverAssistanceOperationalContext::driverAssistanceStory;
  dependency warningScenarioOnStationaryVehicle
    from showWarningInTheWarningScenarios
    to DE4SDV_DriverAssistanceOperationalContext::warnAndBrakeForStationaryVehicle;
  dependency warningScenarioOnSlowerVehicle
    from showWarningInTheWarningScenarios
    to DE4SDV_DriverAssistanceOperationalContext::warnAndBrakeForSlowerVehicle;
  dependency noReactionScenarioBeyondTheCurve
    from showNoWarningInTheNoReactionScenarios
    to DE4SDV_DriverAssistanceOperationalContext::noReactionToStationaryVehicleBeyondTheCurve;
  dependency noReactionScenarioOnTurningOff
    from showNoWarningInTheNoReactionScenarios
    to DE4SDV_DriverAssistanceOperationalContext::noReactionToVehicleAheadTurningOff;

  comment vehicleSpeedSourceComment about DE4SDV_HmiDisplayFraming::hmiSpeedInScope
  /*
   * Phase 2 places the source of the vehicle speed: the vehicle gives the
   * display the speed that it gives the candidate. Phase 0 leaves its carrier
   * to phases 2 and 3; phase 3 places no element, so the carrier, a platform
   * element of System 1 that brings the speed to the SDV Core VM, goes to the
   * architecture phases. The Eclipse S-CORE path of the driver-assistance
   * increment carries the driving command and the warning request, so this
   * context draws no path for the speed.
   */

  comment sceneOutputComment about DE4SDV_HmiDisplayFraming::gapHmiSceneOutput
  /*
   * Phase 2 draws the scene as a flow from the candidate to the display,
   * which the candidate does not give at the inspected revision. No path is
   * drawn for it: whether the scene can leave the candidate's process, and
   * on which path, stays open, and this context changes nothing of what the
   * candidate perceives, plans, requests or commands.
   */

  comment guestAcrossBoundaryComment about DE4SDV_HmiDisplayFraming::gapHmiMemberGuestLayout
  /*
   * The AAOS SDV guest lies across the boundary: the app in the IVI VM that
   * draws the scene, with the Android that runs it, the renderer in an SDV
   * Media VM and the paths from the SDV Core VM are inside the display; the
   * Eclipse S-CORE path is outside. So the context draws no part for the
   * guest, and an outage of Android in the IVI VM is an event inside the
   * black box, whose detection phases 6 to 8 decide. This context changes
   * neither the guest layout nor the assumption of the Eclipse S-CORE
   * middleware increment on the HMI application.
   */

  concern hmiDisplayContextConcern : OperationalContextConcern {
    doc /*
     * System architects, systems engineers and open-source reviewers need to
     * see what is inside the HMI display and what is around it: the candidate
     * application, the Eclipse S-CORE path, the vehicle and the driver, and
     * which item crosses the boundary in which direction. The candidate and
     * the S-CORE path are outside; the driver only receives; nothing flows
     * back to the candidate.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view hmiDisplayOperationalContextView {
    viewpoint hmiDisplayContextViewpoint : OperationalContextDefinitionViewpoint {
      frame hmiDisplayContextConcern;
    }

    expose hmiDisplayOperationalContext;
    expose hmiDisplayOperationalContext::*;
    expose hmiDisplayOperation;
    attribute depth = 2;
    attribute showAnnotationRows = false;
    render asTreeDiagram;
  }

  concern hmiDisplayStoryConcern : OperationalStoryConcern {
    doc /*
     * Systems engineers, verification engineers and open-source reviewers
     * need the HMI display told in stakeholder language: what the driver sees
     * in the scenarios of the driver-assistance increment, with and without a
     * warning, and while the app that draws the scene or Android in the IVI
     * VM is out.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view hmiDisplayOperationalStoryView {
    viewpoint hmiDisplayStoryViewpoint : OperationalStoryViewpoint {
      frame hmiDisplayStoryConcern;
      frame hmiDriverSupervisionConcern;
    }

    expose hmiDisplayStory;
    expose hmiDisplayStory::*;
    attribute depth = 1;
    attribute showAnnotationRows = false;
    render asTreeDiagram;
  }
}
