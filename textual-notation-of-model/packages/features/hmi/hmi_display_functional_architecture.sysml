/*
 * DE4SDV HMI display functional architecture.
 *
 * INC-HMI-001, phase 6: the functions of the HMI display and the requirements
 * of phase 5 each carries. Five functions record the display identity, draw
 * the scene, judge the currency of what the display shows, show the content
 * and give the collision warning. Every requirement but REQ-HMI-009 is
 * allocated to a function. REQ-HMI-009 constrains which elements draw the
 * scene, the vehicle speed and the warning, and the paths that bring them
 * their inputs, not what a function does: phase 8 carries it by the elements
 * that it places, and the inspection of the realization that phase 8 records
 * verifies it. An allocation assigns responsibility only (allocatedTo); it
 * asserts no satisfaction. No logical element, platform, transport or
 * technology is chosen, and no safety claim is made.
 *
 * The drawing of the scene stands apart from the other functions: they take
 * nothing from it but the scenes that it has drawn, and the function that
 * gives the warning takes nothing from it at all. An outage of the drawing of
 * the scene or of the environment that hosts it is therefore an event inside
 * the HMI display that stops the drawn scenes and leaves the vehicle speed and
 * the warning going: judgeCurrency finds the scene outdated by the term
 * current, and showContent shows it as outdated until the drawing gives a
 * current scene again.
 *
 * The display in operation is a process, not a second architecture: the
 * candidate gives the scene and the warning request, the command and warning
 * path carries the warning request to the display, the vehicle gives its
 * speed, and the driver supervises the system with what the display shows and
 * gets the collision warning. Those are functions of the context elements,
 * outside the scope of the display, and HmiDisplaySystemProcess runs the
 * display as one action between them, with the times from the start of a
 * request to each mode of the warning. Its participants are the parts of the
 * one operational context of phase 2, bound by reference. The functions whose
 * behavior differs by state depend on the states of ElementCurrency and
 * CollisionWarningStates, and the conceptual interfaces of the display are the
 * ports of HmiDisplayFunctionalBoundary, whose items specialize the items of
 * phase 2. No vehicle signal specification is imported or used anywhere in
 * this package: the interface items are conceptual, their quantities are ISQ
 * quantity values, and the signal typing of an interface starts in phase 8.
 * The functions state what the display has to do, not what any element does at
 * an inspected revision; phase 8 maps them to its software.
 */

package DE4SDV_HmiDisplayFunctionalArchitecture {
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_TraceVocabulary::AllocatableFunction;
  private import DE4SDV_HmiDisplayFraming::hmiDisplayInputsConcern;
  private import DE4SDV_HmiDisplayFraming::hmiWarningSequenceConcern;
  private import DE4SDV_HmiDisplayFraming::hmiContentCurrencyConcern;
  private import DE4SDV_HmiDisplayFraming::hmiAndroidOutageConcern;
  private import DE4SDV_HmiDisplayFraming::HmiDisplaySystem;
  private import DE4SDV_HmiDisplayOperationalContext::PerceivedScene;
  private import DE4SDV_HmiDisplayOperationalContext::HmiDisplayContent;
  private import DE4SDV_HmiDisplayOperationalContext::hmiDisplayOperationalContext;
  private import DE4SDV_DriverAssistanceFraming::DriverAssistanceSystem;
  private import DE4SDV_OperationalContext::SubjectVehicle;
  private import DE4SDV_OperationalContext::Driver;
  private import DE4SDV_DriverAssistanceOperationalContext::VehicleSpeed;
  private import DE4SDV_DriverAssistanceOperationalContext::WarningRequest;
  private import DE4SDV_DriverAssistanceOperationalContext::CollisionWarning;
  private import DE4SDV_DriverAssistanceOperationalContext::SCORECommandAndWarningPath;
  private import DE4SDV_DriverAssistanceFunctionalArchitecture::VehicleSpeedInput;
  private import DE4SDV_DriverAssistanceFunctionalArchitecture::CollisionWarningRequestOutput;
  private import DE4SDV_HmiDisplayNeedsRequirements::*;
  private import ScalarValues::Boolean;
  private import SAF_Viewpoints::*;
  private import StandardViewDefinitions::*;
  private import SysideViews::**;
  private import Views::*;

  /* Items the functions exchange inside the HMI display */

  item def DisplayIdentityRecord {
    doc /*
     * The record of the display identity of one run, made before the first
     * frame of the HMI display on the display in that run.
     */
  }

  item def DrawnScene {
    doc /*
     * A scene as the drawing of the scene shows it, with the time of that
     * scene. The drawing gives one for each scene that it draws, and none
     * while it, or the environment that hosts it, is out.
     */
  }

  item def ContentCurrency {
    doc /*
     * Whether each element, the scene as drawn and the vehicle speed, and the
     * warning request is current or outdated by the term current, as
     * judgeCurrency judges it.
     */
  }

  /* The functions of the context elements of phase 2 */

  action def HmiDisplayContextFunction {
    doc /*
     * A behavior of a context element of phase 2 while the HMI display
     * operates. It is outside the scope of the HMI display: the display does
     * not provide it and no requirement of phase 5 is allocated to it.
     */
  }

  action def GiveSceneAndWarningRequest :> HmiDisplayContextFunction {
    doc /*
     * The candidate: gives the scene of each result pass with its time, and
     * the warning request of each plan with its issue time, as the
     * driver-assistance increment defines the request, both every 0.1 s of
     * simulation time. At the inspected revision it gives no scene at its
     * boundary (gapHmiSceneOutput).
     */
    out perceivedScene : PerceivedScene;
    out warningRequest : WarningRequest;
  }

  action def CarryWarningRequestToDisplay :> HmiDisplayContextFunction {
    doc /*
     * The command and warning path: carries the warning request to the
     * boundary of the HMI display, with no exchange beside it.
     */
    in warningRequest : WarningRequest;
    out carriedWarningRequest : WarningRequest;
  }

  action def GiveVehicleSpeed :> HmiDisplayContextFunction {
    doc /*
     * The vehicle: gives its speed with each world snapshot, every step of
     * 0.05 s of simulation time, with its sample time. Which element of System
     * 1 brings it to the display is for the architecture phases.
     */
    out vehicleSpeed : VehicleSpeed;
  }

  action def SuperviseWithTheDisplay :> HmiDisplayContextFunction {
    doc /*
     * The driver: supervises the driver-assistance system with what the HMI
     * display shows, and gets the collision warning on the display and as a
     * sound; nothing flows back to the display.
     */
    in shownContent : HmiDisplayContent;
    in collisionWarning : CollisionWarning;
  }

  /* Functions */

  action def RecordDisplayIdentity :> AllocatableFunction {
    doc /*
     * Records the display identity of the HMI display before its first frame
     * on the display in each run, so that each verdict binds the display that
     * ran.
     */
    out identityRecord : DisplayIdentityRecord;
  }

  action def DrawScene :> AllocatableFunction {
    doc /*
     * Draws each scene that reaches the HMI display, or a newer one, as the
     * driver-assistance system gives it, with the object that the system acts
     * on, when the scene has one, as an element of its own with its distance
     * to the whole metre and the speed of the closest object to the whole
     * km/h. It gives each scene that it draws with the time of that scene, and
     * none while it, or the environment that hosts it, is out.
     */
    in perceivedScene : PerceivedScene;
    out drawnScene : DrawnScene;
  }

  action def JudgeCurrency :> AllocatableFunction {
    doc /*
     * Judges, by the term current, whether each element, the scene as drawn
     * and the vehicle speed, and the warning request is current or outdated.
     * It judges from the times of the values that reach the HMI display, from
     * when the newest value of each input reached it, and, for the scene, from
     * the drawn scenes, which stop while the drawing of the scene or the
     * environment that hosts it is out. It takes nothing else from the drawing
     * of the scene, so it goes on through each such outage.
     */
    in perceivedScene : PerceivedScene;
    in vehicleSpeed : VehicleSpeed;
    in warningRequest : WarningRequest;
    in drawnScene : DrawnScene;
    out contentCurrency : ContentCurrency;
  }

  action def ShowContent :> AllocatableFunction {
    doc /*
     * Shows on the HMI display, within the presentation time, the drawn scene
     * and the vehicle speed to the whole km/h. It shows each element as
     * outdated while, and only while, it is outdated, the scene included while
     * its drawing is out. It shows that the collision warning is unavailable
     * while, and only while, the warning request is outdated. It takes nothing
     * from the drawing of the scene but the drawn scenes, so it goes on
     * through each outage of that drawing or of the environment that hosts it.
     */
    in drawnScene : DrawnScene;
    in vehicleSpeed : VehicleSpeed;
    in contentCurrency : ContentCurrency;
    out shownContent : HmiDisplayContent;
  }

  action def GiveCollisionWarning :> AllocatableFunction {
    doc /*
     * Gives the collision warning on the HMI display and as a sound while, and
     * only while, the warning request asks for it. Each mode starts within 0.1
     * s of wall-clock time after the start of a request reaches the display,
     * and follows each change of the asking within the presentation time. It
     * takes nothing from the drawing of the scene, so it goes on through each
     * outage of that drawing or of the environment that hosts it.
     */
    in warningRequest : WarningRequest;
    in contentCurrency : ContentCurrency;
    out collisionWarning : CollisionWarning;
  }

  /* The functional breakdown of the HMI display */

  action def HmiDisplayFunctionalFlow {
    doc /*
     * The HMI display broken into its functions, and the items they exchange.
     * The scene and the warning request come from the candidate, the warning
     * request over the command and warning path, and the vehicle speed from
     * the vehicle. What the display shows and the collision warning go to the
     * driver. Only the content of showContent leaves as what the display
     * shows, and only the warning of giveWarning as the collision warning. The
     * display identity is recorded before the display gives its first frame.
     */
    in item perceivedScene : PerceivedScene;
    in item vehicleSpeed : VehicleSpeed;
    in item warningRequest : WarningRequest;
    out item shownContent : HmiDisplayContent;
    out item collisionWarning : CollisionWarning;

    action recordDisplayIdentity : RecordDisplayIdentity {
      out identityRecord;
    }

    action drawScene : DrawScene {
      in perceivedScene = HmiDisplayFunctionalFlow::perceivedScene;
      out drawnScene;
    }
    first recordDisplayIdentity then drawScene;

    action judgeCurrency : JudgeCurrency {
      in perceivedScene = HmiDisplayFunctionalFlow::perceivedScene;
      in vehicleSpeed = HmiDisplayFunctionalFlow::vehicleSpeed;
      in warningRequest = HmiDisplayFunctionalFlow::warningRequest;
      in drawnScene;
      out contentCurrency;
    }
    flow from drawScene.drawnScene to judgeCurrency.drawnScene;

    action showContent : ShowContent {
      in drawnScene;
      in vehicleSpeed = HmiDisplayFunctionalFlow::vehicleSpeed;
      in contentCurrency;
      out shownContent = HmiDisplayFunctionalFlow::shownContent;
    }
    flow from drawScene.drawnScene to showContent.drawnScene;
    flow from judgeCurrency.contentCurrency to showContent.contentCurrency;
    first recordDisplayIdentity then showContent;

    action giveWarning : GiveCollisionWarning {
      in warningRequest = HmiDisplayFunctionalFlow::warningRequest;
      in contentCurrency;
      out collisionWarning = HmiDisplayFunctionalFlow::collisionWarning;
    }
    flow from judgeCurrency.contentCurrency to giveWarning.contentCurrency;
    first recordDisplayIdentity then giveWarning;
  }

  action hmiDisplayFunctionalFlow : HmiDisplayFunctionalFlow;

  /* The system process: the HMI display between the context elements */

  action def HmiDisplaySystemProcess {
    doc /*
     * One run of the HMI display in operation, as a process. The participants
     * are the context parts of phase 2 themselves and the system of interest,
     * bound by reference: the process declares no part of its own, so the
     * increment has one context. Each participant owns and performs its
     * functions, as the swim lane of its functions: the candidate gives the
     * scene and the warning request, the command and warning path carries the
     * warning request to the display, and the vehicle gives its speed. The
     * display records its identity, draws the scene, judges the currency of
     * what it shows, shows the content and gives the warning, as one action of
     * the process. The driver supervises the system with what the display
     * shows and gets the collision warning. The functions of the context
     * elements are outside the scope of the HMI display; its functional scope
     * is the one functional flow usage it performs. The items that cross its
     * boundary are the flows of the process, each chained through the
     * participant that gives and the one that takes, and nothing flows back
     * from the driver.
     *
     * The sequence and its times: the candidate gives the scene and the
     * warning request every 0.1 s of simulation time, and the vehicle gives
     * its speed with each world snapshot, every step of 0.05 s. The
     * driver-assistance increment allots 0.2 s of wall-clock time from the
     * warning request at the boundary of the candidate to each mode of the
     * warning. The display starts each mode within 0.1 s of wall-clock time
     * after the start of a request reaches it, and the other 0.1 s lies before
     * its boundary, on the path, which the architecture phases of both
     * increments place. Phase 8 divides the 0.1 s of the display among its
     * elements. An outage of the drawing of the scene or of the environment
     * that hosts it is an event inside the display: the drawn scenes stop, and
     * the scene shows as outdated within the limits of the term current and
     * the presentation time from the last scene drawn, while the vehicle speed
     * and the warning go on. Once the drawing gives a current scene again, the
     * scene shows as current. No transport, display or sound technology is
     * fixed here.
     */
    ref part candidate : DriverAssistanceSystem = hmiDisplayOperationalContext::candidate {
      doc /*
       * The candidate of phase 2: gives the scene with its time and the
       * warning request with its issue time, every 0.1 s of simulation time.
       * At the inspected revision it gives no scene at its boundary
       * (gapHmiSceneOutput).
       */
      perform action giveSceneAndRequest : GiveSceneAndWarningRequest;
    }

    ref part scorePath : SCORECommandAndWarningPath = hmiDisplayOperationalContext::scorePath {
      doc /*
       * The command and warning path of phase 2: carries the warning request
       * to the HMI display, with no exchange beside it. Of the 0.2 s of
       * wall-clock time that the driver-assistance increment allots from the
       * warning request at the boundary of the candidate to each mode of the
       * warning, 0.1 s lies before the boundary of the display, on this path,
       * and the architecture phases of both increments place it.
       */
      perform action carryRequest : CarryWarningRequestToDisplay;
    }

    ref part vehicle : SubjectVehicle = hmiDisplayOperationalContext::vehicle {
      doc /*
       * The vehicle of phase 2: gives its speed with each world snapshot,
       * every step of 0.05 s of simulation time.
       */
      perform action giveSpeed : GiveVehicleSpeed;
    }

    ref part hmiDisplay : HmiDisplaySystem = hmiDisplayOperationalContext::hmiDisplay {
      doc /*
       * The system of interest of phase 2: it performs its whole functional
       * flow, the one usage its functional boundary performs, and starts each
       * mode of the warning within 0.1 s of wall-clock time after the start of
       * a request reaches it; phase 8 divides that 0.1 s among its elements.
       * An outage of the drawing of the scene or of the environment that hosts
       * it is an event inside the display: the drawn scenes stop,
       * judgeCurrency finds the scene outdated by the term current, and
       * showContent shows it as outdated within the limits of that term and
       * the presentation time from the last scene drawn. Through the outage
       * the display goes on showing the vehicle speed, giving the warning
       * while the request asks for it, and showing the warning as unavailable
       * while the request is outdated.
       */
      perform hmiDisplayFunctionalFlow;
    }

    ref part driver : Driver = hmiDisplayOperationalContext::driver {
      doc /*
       * The driver of phase 2: supervises the system with what the HMI display
       * shows and gets the collision warning; nothing flows back to the
       * display.
       */
      perform action supervise : SuperviseWithTheDisplay;
    }

    flow from candidate.giveSceneAndRequest.perceivedScene to hmiDisplay.hmiDisplayFunctionalFlow.perceivedScene;
    flow from candidate.giveSceneAndRequest.warningRequest to scorePath.carryRequest.warningRequest;
    flow from scorePath.carryRequest.carriedWarningRequest to hmiDisplay.hmiDisplayFunctionalFlow.warningRequest;
    flow from vehicle.giveSpeed.vehicleSpeed to hmiDisplay.hmiDisplayFunctionalFlow.vehicleSpeed;
    flow from hmiDisplay.hmiDisplayFunctionalFlow.shownContent to driver.supervise.shownContent;
    flow from hmiDisplay.hmiDisplayFunctionalFlow.collisionWarning to driver.supervise.collisionWarning;
  }

  action hmiDisplaySystemProcess : HmiDisplaySystemProcess;

  /* States */

  state def ElementCurrency {
    doc /*
     * The state of each element of the HMI display, the scene as drawn and the
     * vehicle speed, by the term current. Each element is in one of them on
     * its own, and is outdated from the start of each run until its first
     * current value.
     */
    state outdated {
      doc /*
       * The element shows no current value: its value came late or never, no
       * value of its input has reached the display yet, or, for the scene, the
       * drawing of the scene or the environment that hosts it is out and the
       * scene shown is no longer current. showContent shows the element as
       * outdated (REQ-HMI-006).
       */
    }
    state current {
      doc /*
       * The element shows a current value: showContent shows the scene as
       * drawn and the vehicle speed to the whole km/h (REQ-HMI-001,
       * REQ-HMI-003).
       */
    }
    transition first outdated then current;  // a current value is shown
    transition first current then outdated;  // the value shown is no longer current, the drawing of the scene being out included
  }

  state def CollisionWarningStates {
    doc /*
     * The state of the collision warning at the HMI display, by the warning
     * request. It is unavailable from the start of each run until the first
     * current event of the request.
     */
    state unavailable {
      doc /*
       * The warning request is outdated: giveWarning gives no collision
       * warning, and showContent shows that the warning is unavailable
       * (REQ-HMI-007), through each outage of the drawing of the scene as well
       * (REQ-HMI-008).
       */
    }
    state notAsking {
      doc /* The warning request is current and asks for no collision warning: giveWarning gives none. */
    }
    state asking {
      doc /*
       * The warning request asks: giveWarning gives the collision warning on
       * the display and as a sound, each mode starting within 0.1 s of
       * wall-clock time after the start of a request reaches the display
       * (REQ-HMI-004, REQ-HMI-005), through each outage of the drawing of the
       * scene as well (REQ-HMI-008).
       */
    }
    transition first unavailable then notAsking;  // a current event that asks for none
    transition first unavailable then asking;     // a current event that asks: the start of a request
    transition first notAsking then asking;       // the start of a request
    transition first asking then notAsking;       // a current event that asks for none
    transition first asking then unavailable;     // the warning request becomes outdated
    transition first notAsking then unavailable;  // the warning request becomes outdated
  }

  /* The functions whose behavior differs by state depend on it */

  dependency showContentDependsOnOutdatedState
    from HmiDisplayFunctionalFlow::showContent
    to ElementCurrency::outdated;
  dependency showContentDependsOnCurrentState
    from HmiDisplayFunctionalFlow::showContent
    to ElementCurrency::current;
  dependency showContentDependsOnUnavailableState
    from HmiDisplayFunctionalFlow::showContent
    to CollisionWarningStates::unavailable;
  dependency giveWarningDependsOnUnavailableState
    from HmiDisplayFunctionalFlow::giveWarning
    to CollisionWarningStates::unavailable;
  dependency giveWarningDependsOnNotAskingState
    from HmiDisplayFunctionalFlow::giveWarning
    to CollisionWarningStates::notAsking;
  dependency giveWarningDependsOnAskingState
    from HmiDisplayFunctionalFlow::giveWarning
    to CollisionWarningStates::asking;

  /* The conceptual interfaces of the HMI display: one functional chain */

  item def DisplaySceneInput :> PerceivedScene {
    doc /*
     * The scene as it reaches the HMI display at its input, with its time, the
     * capture time in simulation time of the camera image of its result pass.
     * When the scene has an object that the system acts on, it also carries
     * that object's distance and the speed of the closest object that the
     * fusion gives. The rest of the scene travels with it.
     */
    attribute captureTime : ISQ::DurationValue;
    attribute actedOnObjectDistance : ISQ::LengthValue[0..1];
    attribute actedOnObjectSpeed : ISQ::SpeedValue[0..1];
  }

  item def DisplayVehicleSpeedInput :> VehicleSpeedInput {
    doc /*
     * The vehicle speed as it reaches the HMI display: the speed of each world
     * snapshot, the same speed that the driver-assistance system takes at its
     * input, with its sample time in simulation time.
     */
  }

  item def DisplayWarningRequestInput :> CollisionWarningRequestOutput {
    doc /*
     * The warning request as it reaches the HMI display: the request that the
     * driver-assistance system gives at its boundary, whether it asks for the
     * collision warning, with its issue time in simulation time.
     */
  }

  item def DisplayContentOutput :> HmiDisplayContent {
    doc /*
     * What the HMI display shows: the drawn scene, the vehicle speed to the
     * whole km/h, whether each element is shown as outdated, and whether the
     * collision warning is shown as unavailable. How each looks is for phase
     * 8.
     */
    attribute shownSpeed : ISQ::SpeedValue[0..1];
    attribute sceneOutdated : Boolean;
    attribute speedOutdated : Boolean;
    attribute warningUnavailable : Boolean;
  }

  item def DisplayWarningOutput :> CollisionWarning {
    doc /* The collision warning as the HMI display gives it, in its two modes: on the display and as a sound. */
    attribute onDisplay : Boolean;
    attribute asSound : Boolean;
  }

  port def DisplaySceneInbound {
    doc /* The input port of the scene: the candidate gives it. */
    in item perceivedScene : DisplaySceneInput;
  }

  port def DisplaySpeedInbound {
    doc /* The input port of the vehicle speed: the vehicle gives it. */
    in item vehicleSpeed : DisplayVehicleSpeedInput;
  }

  port def DisplayWarningRequestInbound {
    doc /* The input port of the warning request: the command and warning path brings it from the candidate. */
    in item warningRequest : DisplayWarningRequestInput;
  }

  port def DisplayContentOutbound {
    doc /* The output port of what the display shows: the driver sees it. */
    out item shownContent : DisplayContentOutput;
  }

  port def DisplayWarningOutbound {
    doc /* The output port of the collision warning, on the display and as a sound: the driver gets it. */
    out item collisionWarning : DisplayWarningOutput;
  }

  part def HmiDisplayFunctionalBoundary :> HmiDisplaySystem {
    doc /*
     * The HMI display at its functional boundary, the one place its conceptual
     * interfaces are stated: three input ports and two output ports, each with
     * one directed item typed by an item definition of this package that
     * specializes the item of phase 2, or the item that the driver-assistance
     * increment defines for it. It performs the functional flow and binds its
     * inputs and outputs to the ports. It is not a logical element: neither it
     * nor its ports names a computer, a process, a transport or a technology.
     */
    port sceneIn : DisplaySceneInbound;
    port speedIn : DisplaySpeedInbound;
    port warningRequestIn : DisplayWarningRequestInbound;
    port contentOut : DisplayContentOutbound;
    port warningOut : DisplayWarningOutbound;

    perform hmiDisplayFunctionalFlow : HmiDisplayFunctionalFlow {
      in item perceivedScene = sceneIn.perceivedScene;
      in item vehicleSpeed = speedIn.vehicleSpeed;
      in item warningRequest = warningRequestIn.warningRequest;
      out item shownContent = contentOut.shownContent;
      out item collisionWarning = warningOut.collisionWarning;
    }
  }

  /* Requirement-to-function allocations (allocatedTo) */

  /* Recording the display identity. */
  allocation displayIdentityResponsibility
    allocate reqRecordDisplayIdentity to HmiDisplayFunctionalFlow::recordDisplayIdentity;

  /* Drawing the scene, with the object that the system acts on. */
  allocation sceneDrawingResponsibility
    allocate reqShowTheSceneAsGiven to HmiDisplayFunctionalFlow::drawScene;
  allocation actedOnObjectResponsibility
    allocate reqMarkTheObjectTheSystemActsOn to HmiDisplayFunctionalFlow::drawScene;

  /* Judging the currency of the elements and of the warning request. */
  allocation requestAskingResponsibility
    allocate reqCollisionWarningWhileRequested to HmiDisplayFunctionalFlow::judgeCurrency;
  allocation requestStartResponsibility
    allocate reqStartEachWarningModeWithinLimit to HmiDisplayFunctionalFlow::judgeCurrency;
  allocation elementCurrencyResponsibility
    allocate reqShowOutdatedElementsAsOutdated to HmiDisplayFunctionalFlow::judgeCurrency;
  allocation requestCurrencyResponsibility
    allocate reqShowWarningUnavailableWhileRequestOutdated to HmiDisplayFunctionalFlow::judgeCurrency;
  allocation currencyThroughOutagesResponsibility
    allocate reqSpeedAndWarningThroughOutages to HmiDisplayFunctionalFlow::judgeCurrency;

  /* Showing the content. */
  allocation sceneShowingResponsibility
    allocate reqShowTheSceneAsGiven to HmiDisplayFunctionalFlow::showContent;
  allocation actedOnObjectShowingResponsibility
    allocate reqMarkTheObjectTheSystemActsOn to HmiDisplayFunctionalFlow::showContent;
  allocation speedShowingResponsibility
    allocate reqShowTheVehicleSpeed to HmiDisplayFunctionalFlow::showContent;
  allocation outdatedShowingResponsibility
    allocate reqShowOutdatedElementsAsOutdated to HmiDisplayFunctionalFlow::showContent;
  allocation unavailableShowingResponsibility
    allocate reqShowWarningUnavailableWhileRequestOutdated to HmiDisplayFunctionalFlow::showContent;
  allocation contentThroughOutagesResponsibility
    allocate reqSpeedAndWarningThroughOutages to HmiDisplayFunctionalFlow::showContent;

  /* Giving the collision warning. */
  allocation warningWhileRequestedResponsibility
    allocate reqCollisionWarningWhileRequested to HmiDisplayFunctionalFlow::giveWarning;
  allocation warningModeStartResponsibility
    allocate reqStartEachWarningModeWithinLimit to HmiDisplayFunctionalFlow::giveWarning;
  allocation warningThroughOutagesResponsibility
    allocate reqSpeedAndWarningThroughOutages to HmiDisplayFunctionalFlow::giveWarning;

  /* Views */

  concern hmiDisplayFunctionsConcern : FunctionalBehaviorConcern {
    doc /*
     * System architects and verification engineers need the functions of the
     * HMI display and each requirement of phase 5 mapped to the functions that
     * carry it: phase 7 gives the functions to logical elements, and phase 10
     * verifies each requirement on its functions.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder verificationEngineer : VerificationEngineer;
  }

  view hmiDisplayFunctionBreakdownView {
    viewpoint selectedFunctionalBreakdownViewpoint : SystemFunctionalBreakdownStructureViewpoint {
      frame hmiDisplayFunctionsConcern;
    }
    expose hmiDisplayFunctionalFlow;
    render asTreeDiagram;
  }

  view hmiDisplayRequirementFunctionMatrixView : MVD::MatrixView {
    viewpoint selectedRequirementFunctionViewpoint : SystemRequirementTraceabilityViewpoint {
      frame hmiDisplayFunctionsConcern;
    }
    view :>> rowView {
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
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> columnView {
      expose hmiDisplayFunctionalFlow::recordDisplayIdentity;
      expose hmiDisplayFunctionalFlow::drawScene;
      expose hmiDisplayFunctionalFlow::judgeCurrency;
      expose hmiDisplayFunctionalFlow::showContent;
      expose hmiDisplayFunctionalFlow::giveWarning;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> cellView {
      expose DE4SDV_HmiDisplayFunctionalArchitecture::*;
      attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;
    }
  }

  /* The HMI display in operation as a process: its inputs, the warning and the outages */

  view hmiDisplaySystemProcessView : ActionFlowView {
    viewpoint selectedSystemProcessViewpoint : SystemProcessViewpoint {
      frame hmiDisplayInputsConcern;
      frame hmiWarningSequenceConcern;
      frame hmiAndroidOutageConcern;
    }
    expose HmiDisplaySystemProcess::*;
    expose HmiDisplaySystemProcess::candidate::*;
    expose HmiDisplaySystemProcess::scorePath::*;
    expose HmiDisplaySystemProcess::vehicle::*;
    expose HmiDisplaySystemProcess::hmiDisplay::*;
    expose HmiDisplaySystemProcess::driver::*;
    attribute showAnnotationRows = false;
    attribute maxCompartmentEntries = 0;
  }

  /* The states, and the functions that depend on them */

  view hmiDisplayStateTableView : TVD::TableView {
    viewpoint selectedSystemStateTableViewpoint : SystemStateViewpoint {
      frame hmiContentCurrencyConcern;
    }
    expose ElementCurrency::outdated;
    expose ElementCurrency::current;
    expose CollisionWarningStates::unavailable;
    expose CollisionWarningStates::notAsking;
    expose CollisionWarningStates::asking;
    filter @ SysML::StateUsage;
    attribute :>> maxRowHeight = 300;
    view State :> columnViews {
      attribute :>> featureToRender = CT::declaredName;
    }
    view DependentFunctions :> columnViews {
      attribute :>> featureToRender = CT::documentation;
      attribute :>> columnWidth = 360;
    }
  }

  /* The conceptual interfaces of the HMI display */

  concern hmiDisplayInterfaceConcern : FunctionalInterfaceConcern {
    doc /*
     * Systems engineers and software developers need the conceptual interfaces
     * of the HMI display before phase 7 allocates the functions and phase 8
     * places software on them: the port of the functional chain for each item
     * that crosses its boundary, and the direction of that item. Signal typing
     * at a software contract belongs to phase 8.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder softwareDeveloper : SoftwareDeveloper;
  }

  view hmiDisplayFunctionalInterfaceView {
    viewpoint selectedFunctionalInterfaceViewpoint : SystemInterfaceDefinitionViewpoint {
      frame hmiDisplayInterfaceConcern;
    }
    expose DisplayContentOutbound;
    expose DisplaySceneInbound;
    expose DisplaySpeedInbound;
    expose DisplayWarningOutbound;
    expose DisplayWarningRequestInbound;
    attribute showAnnotationRows = false;
    render asTreeDiagram;
  }
}
