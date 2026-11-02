/*
 * DE4SDV closed-loop driving capability: Phase 2 operational context.
 *
 * INC-DRIVING-001, phase 2: what happens in the world of the candidate driving
 * system. The vehicle's cameras and motion sensing feed it, navigation gives
 * it the route to the destination the driver chose, its steering and
 * acceleration commands move the vehicle, and AAOS SDV presents the plan,
 * vehicle state and health it publishes. The route says where the vehicle is
 * to go; the plan, the trajectory the checkpoint computes, says how it moves
 * through the next seconds; the commands carry the plan out. AAOS SDV is a context role, not part
 * of the driving system (owner decision of 2026-11-02): removing it leaves the
 * plan-to-command chain unchanged, and the increment claims no driver-HMI
 * capability. No planning, transport, display or deployment technology is
 * selected here; CARLA, the cloud bench and the capture instruments are
 * System 2 and stay out of this context. No safety, on-road or
 * production-readiness claim is made.
 */

package DE4SDV_ClosedLoopDrivingOperationalContext {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_OperationalContext::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_SYSMODAdapter::*;
  private import DE4SDV_ClosedLoopDrivingFraming::*;
  private import DE4SDV_MiddlewareSCOREOperationalContext::AAOSSDVGuestExecutionDomain;
  private import SAF_Viewpoints::*;
  private import Views::*;

  /* ───────────────────── Phase 2: what happens in the world ───────────────────── */

  item def CameraImages {
    doc /* The images of the vehicle's cameras with their capture times: the scene the driving system plans from. */
  }

  item def EgoMotionState {
    doc /* The vehicle's own motion and its recent history, such as speed, acceleration and yaw rate, with their sample times. */
  }

  item def Route {
    doc /*
     * Where the vehicle is to go, as navigation gives it: the destination the
     * driver chose, the route to it, and the map of the roads around the
     * vehicle that the route runs through, with their times. Not a plan: the
     * plan says how the vehicle moves through the next seconds.
     */
  }

  item def VehicleMotionCommand {
    doc /* The steering and acceleration commands the driving system gives the vehicle's actuation. */
  }

  item def DrivingOperationalState {
    doc /*
     * The live plan, vehicle state and health of the driving system as it
     * publishes them for observation, each with its producer and its time.
     */
  }

  part def NavigationSystem :> OperationalEntity {
    doc /*
     * The navigation of the vehicle: it holds the road map, takes the
     * destination the driver chooses and gives the driving system the route
     * there. It is an operational role, not a platform: which computer runs
     * it is an allocation of phase 8. If a later phase allocates it to the
     * AAOS SDV guest, AAOS SDV becomes an input to the loop and the
     * context-role decision of 2026-11-02 reopens. The driving system plans
     * its trajectory along the route and does not choose the route.
     */
  }

  part def DrivingStateObserverApplication :> OperationalEntity {
    doc /*
     * The AAOS SDV application that presents the driving system's plan,
     * vehicle state and health to the driver. It sends nothing to the
     * driving system.
     */
  }

  part closedLoopDrivingOperationalContext : SystemContext {
    doc /*
     * The operational context of the candidate driving system. Inside the
     * system of interest, as Phase 0 draws it: camera and ego-motion input,
     * learned planning, command execution and operational-state publication;
     * the plan and the commands cross S-CORE inside it. The publication ends
     * at its receiving end in the AAOS SDV guest, as in INC-MW-011. Around
     * it: the vehicle it drives, the road environment its cameras see,
     * navigation, which gives the route, the AAOS SDV guest with the
     * application that presents the published state, and the driver who
     * chooses the destination and watches the state. System 1 roles only:
     * CARLA, the cloud bench and the capture instruments realize the vehicle,
     * the scene and the route for verification
     * (closedLoopVerificationEnvironment). This is the operational
     * environment, not a deployment decomposition.
     */
    part drivingSystem : ClosedLoopDrivingSystem :>> systemOfInterest;
    part vehicle : SubjectVehicle {
      doc /* The vehicle whose motion the driving system commands: its cameras and motion sensing give the input, its steering and acceleration actuation take the commands. */
    }
    part roadEnvironment : RoadEnvironment {
      doc /* The road, lanes and traffic of the bounded driving scenario: what the cameras see and where the vehicle drives. */
    }
    part navigation : NavigationSystem {
      doc /* The navigation the driver chooses the destination on. In verification, the scenario's route and map stand in for it. */
    }
    part aaosSDVGuest : AAOSSDVGuestExecutionDomain {
      doc /* The AAOS SDV guest of the existing S-CORE and AAOS SDV integration, with its SDV Core, Gateway and IVI; phase 8 realizes them. */
      part stateObserver : DrivingStateObserverApplication;
    }
    part driver : Driver {
      doc /* The operator of the problem statement: the person who chooses the destination on navigation and watches the plan, vehicle state and health on AAOS SDV. The driver commands nothing of the driving system in this increment. */
    }
  }

  /* Operational behavior: the loop closes through the vehicle and the world; AAOS SDV only receives. */
  action def ClosedLoopDrivingOperation {
    doc /*
     * One cycle of the loop in the world: navigation gives the route, the
     * vehicle observes the scene, the driving system plans along the route
     * and commands, the vehicle moves, and AAOS SDV presents the published
     * state outside the loop.
     */
    action guideToDestination {
      doc /* Navigation: gives the route to the destination the driver chose, over its map. */
      out route : Route;
    }

    action senseScene {
      doc /* The vehicle: its cameras capture the road environment and its motion sensing samples its own motion. */
      out cameraImages : CameraImages;
      out egoMotion : EgoMotionState;
    }

    action planAndCommand {
      doc /* The driving system: the pinned checkpoint plans from the images, the motion history and the route, and the plan becomes steering and acceleration commands. */
      in cameraImages : CameraImages;
      in egoMotion : EgoMotionState;
      in route : Route;
      out command : VehicleMotionCommand;
      out operationalState : DrivingOperationalState;
    }

    flow from senseScene.cameraImages to planAndCommand.cameraImages;
    flow from senseScene.egoMotion to planAndCommand.egoMotion;
    flow from guideToDestination.route to planAndCommand.route;
    first senseScene then planAndCommand;

    action actuateVehicle {
      doc /* The vehicle: steering and acceleration move it, which changes what its cameras see next. */
      in command : VehicleMotionCommand;
    }

    flow from planAndCommand.command to actuateVehicle.command;
    first planAndCommand then actuateVehicle;

    action presentOperationalState {
      doc /* AAOS SDV: the application presents the published plan, vehicle state and health; nothing flows back into the loop. */
      in operationalState : DrivingOperationalState;
    }

    flow from planAndCommand.operationalState to presentOperationalState.operationalState;
  }

  action closedLoopDrivingOperation : ClosedLoopDrivingOperation;

  /* Operational story on the SYSMOD seam. */
  use case def DriveBoundedScenarioClosedLoop :> SYSMODSystemUseCaseBase {
    doc /* The candidate driving system in operation: learned plans move the vehicle through one bounded scenario while AAOS SDV shows the live state outside the loop. */
    attribute redefines ucMotivation = "DE4SDV needs a camera-based driving capability in which a learned checkpoint's plans actually determine the vehicle's steering and acceleration, while the driver sees the genuine plan, vehicle state and health.";
    attribute redefines ucTrigger = "The driving system starts with a pinned checkpoint in one bounded driving scenario, navigation gives the route to the destination the driver chose, and the vehicle's cameras and motion sensing deliver their first input.";
    attribute redefines ucResult = "The vehicle drives the scenario on the checkpoint's plans, AAOS SDV shows the live plan, vehicle state and health, invalid, lost or stale input or plan leads to the defined stop or disable response, and an unavailable AAOS SDV leaves the loop unchanged.";

    objective {
      doc /*
       * Frame the closed loop only: the driving on learned plans, its
       * observation on AAOS SDV, its degraded behavior and its independence
       * from the observer. The planning, transport and display technology,
       * the response deadlines and the timing claims are fixed later.
       */
    }
  }

  use case driveBoundedScenarioClosedLoop : DriveBoundedScenarioClosedLoop {
    subject drivingSystem : ClosedLoopDrivingSystem = closedLoopDrivingOperationalContext::drivingSystem;
    actor vehicle : SubjectVehicle = closedLoopDrivingOperationalContext::vehicle;
    actor roadEnvironment : RoadEnvironment = closedLoopDrivingOperationalContext::roadEnvironment;
    actor navigation : NavigationSystem = closedLoopDrivingOperationalContext::navigation;
    actor stateObserver : DrivingStateObserverApplication = closedLoopDrivingOperationalContext::aaosSDVGuest::stateObserver;
    actor driver : Driver = closedLoopDrivingOperationalContext::driver;

    objective {
      doc /*
       * Operate the loop without selecting planning, transport or display
       * technology, and without any safety, on-road, driver-HMI or
       * production-readiness claim.
       */
    }

    first start;
    then include driveOnCheckpointPlans;
    then include showLiveStateOnAAOS;
    then include respondToDegradedInputOrPlan;
    then include continueWithoutAAOS;
    then done;
  }

  use case driveOnCheckpointPlans {
    subject drivingSystem : ClosedLoopDrivingSystem = closedLoopDrivingOperationalContext::drivingSystem;
    actor vehicle : SubjectVehicle = closedLoopDrivingOperationalContext::vehicle;
    actor roadEnvironment : RoadEnvironment = closedLoopDrivingOperationalContext::roadEnvironment;
    actor navigation : NavigationSystem = closedLoopDrivingOperationalContext::navigation;

    objective {
      doc /*
       * SC-DRIVING-001 (normal operation, closed loop): the cameras see the
       * road environment; navigation gives the route to the destination the
       * driver chose; the pinned checkpoint plans from the images, the motion
       * history and the route; its plan becomes steering and acceleration
       * commands that move the vehicle; the vehicle's new motion changes the
       * next images. An autopilot, a replayed history or a prediction overlay
       * does not perform this scenario.
       */
    }

    first start;
    then done;
  }

  use case showLiveStateOnAAOS {
    subject drivingSystem : ClosedLoopDrivingSystem = closedLoopDrivingOperationalContext::drivingSystem;
    actor stateObserver : DrivingStateObserverApplication = closedLoopDrivingOperationalContext::aaosSDVGuest::stateObserver;
    actor driver : Driver = closedLoopDrivingOperationalContext::driver;

    objective {
      doc /*
       * SC-DRIVING-002 (observation): the driving system publishes its plan,
       * the vehicle state and its health, each with its producer and time;
       * they reach AAOS SDV and the application presents them; the driver
       * sees the state of this run, not a mock or a replay. The display is
       * outside the control loop: the loop never waits for it.
       */
    }

    first start;
    then done;
  }

  use case respondToDegradedInputOrPlan {
    subject drivingSystem : ClosedLoopDrivingSystem = closedLoopDrivingOperationalContext::drivingSystem;
    actor vehicle : SubjectVehicle = closedLoopDrivingOperationalContext::vehicle;
    actor navigation : NavigationSystem = closedLoopDrivingOperationalContext::navigation;
    actor stateObserver : DrivingStateObserverApplication = closedLoopDrivingOperationalContext::aaosSDVGuest::stateObserver;

    objective {
      doc /*
       * SC-DRIVING-003 (degraded input or plan): the camera images, the
       * motion or the route become invalid, lost or stale, or the plan
       * becomes invalid, late, lost or stale; the driving system gives the
       * vehicle the defined stop or disable response instead of acting on the
       * last plan, and publishes the degraded state. The response and its
       * deadlines are fixed with the requirements (phase 5).
       */
    }

    first start;
    then done;
  }

  use case continueWithoutAAOS {
    subject drivingSystem : ClosedLoopDrivingSystem = closedLoopDrivingOperationalContext::drivingSystem;
    actor stateObserver : DrivingStateObserverApplication = closedLoopDrivingOperationalContext::aaosSDVGuest::stateObserver;
    actor vehicle : SubjectVehicle = closedLoopDrivingOperationalContext::vehicle;

    objective {
      doc /*
       * SC-DRIVING-004 (AAOS SDV unavailable or stale): when AAOS SDV, its
       * application or the path to it is down or late, planning and commands
       * to the vehicle go on unchanged and the degraded-input response does
       * not trigger on its account. A stale state is not presented as live;
       * whether the receiving end marks it or the display stays empty is
       * fixed with the requirements (phase 5).
       */
    }

    first start;
    then done;
  }

  /* Traces to the Phase 0 records this context implements. */
  dependency drivingStoryAnswersProblem
    from driveBoundedScenarioClosedLoop
    to DE4SDV_ClosedLoopDrivingFraming::closedLoopDrivingProblem;
  dependency aaosSDVGuestOnReuseAssumption
    from closedLoopDrivingOperationalContext::aaosSDVGuest
    to DE4SDV_ClosedLoopDrivingFraming::asmCandidateReuse;
  dependency stateObserverOnTransportGap
    from DrivingStateObserverApplication
    to DE4SDV_ClosedLoopDrivingFraming::gapTransportAndControl;
  dependency navigationOnInputGap
    from NavigationSystem
    to DE4SDV_ClosedLoopDrivingFraming::gapModelInputAndFeedback;

  comment navigationInputOfTheCheckpoint about DE4SDV_ClosedLoopDrivingFraming::gapModelInputAndFeedback
    /*
     * Besides camera images and the ego-motion history, the pinned checkpoint
     * takes a map of the roads around the vehicle with the route corridor and
     * the destination (Model/README.md and Model/navigation/geometry.py at
     * cb50764b). The gap covers their geometry, their timing and the raster
     * geometry the checkpoint expects as well. Phase 2 adds navigation as the
     * context role that gives them (owner decision of 2026-11-02).
     */

  concern closedLoopDrivingContextConcern : OperationalContextConcern {
    doc /*
     * Reviewers need to see what is inside the driving system and what is
     * around it: the vehicle, the road environment, navigation, AAOS SDV and
     * the driver, and which items cross the boundary in which direction.
     * Navigation gives the route; AAOS SDV only receives, and nothing it
     * sends enters the loop.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view closedLoopDrivingOperationalContextView {
    viewpoint closedLoopDrivingContextViewpoint : OperationalContextDefinitionViewpoint {
      frame closedLoopDrivingContextConcern;
    }

    expose closedLoopDrivingOperationalContext;
    expose closedLoopDrivingOperationalContext::*;
    expose closedLoopDrivingOperation;
    attribute depth = 2;
    attribute showAnnotationRows = false;
    render asTreeDiagram;
  }

  concern closedLoopDrivingStoryConcern : OperationalStoryConcern {
    doc /*
     * Reviewers need the loop told in stakeholder language: driving on the
     * checkpoint's plans, the live state on AAOS SDV, the response to
     * degraded input or plan, and the loop without AAOS SDV.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view closedLoopDrivingOperationalStoryView {
    viewpoint closedLoopDrivingStoryViewpoint : OperationalStoryViewpoint {
      frame closedLoopDrivingStoryConcern;
    }

    expose driveBoundedScenarioClosedLoop;
    expose driveBoundedScenarioClosedLoop::*;
    attribute depth = 1;
    attribute showAnnotationRows = false;
    render asTreeDiagram;
  }
}
