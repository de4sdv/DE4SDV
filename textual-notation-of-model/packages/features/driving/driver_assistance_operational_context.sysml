/*
 * DE4SDV camera-only driver assistance: Phase 2 operational context.
 *
 * INC-DRIVING-002, phase 2: what happens in the world of the candidate
 * driver-assistance system. The vehicle's front camera and its speed feed it;
 * its driving command and its warning request leave it. The Eclipse S-CORE
 * path carries them to the actuation and to the AAOS SDV, and the AAOS SDV
 * gives the driver the collision warning on its display and as a sound. Both
 * are System 1 parts outside the candidate, as phase 0 draws the boundary;
 * phases 6 to 8 decide their realization. CARLA, the cloud hosts, the
 * scenario runner, the evaluators, the capture of the display and of the
 * sound, and the recordings are System 2 and stay out of this context. No
 * safety, on-road, compliance or production-readiness claim is made.
 */

package DE4SDV_DriverAssistanceOperationalContext {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_OperationalContext::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_SYSMODAdapter::*;
  private import DE4SDV_DriverAssistanceFraming::*;
  private import DE4SDV_MiddlewareSCOREOperationalContext::AAOSSDVGuestExecutionDomain;
  private import SAF_Viewpoints::*;
  private import Views::*;

  /* ───────────────────── Phase 2: what happens in the world ───────────────────── */

  item def FrontCameraImage {
    doc /* The image of the vehicle's front camera with its capture time: the scene the candidate perceives the lane and the objects in the path from. */
  }

  item def VehicleSpeed {
    doc /* The speed of the vehicle with its sample time. */
  }

  item def DrivingCommand {
    doc /* The steering and acceleration command of the candidate, braking included, for the vehicle's actuation. */
  }

  item def WarningRequest {
    doc /*
     * The candidate's request that the driver be warned of an imminent
     * collision, with its time. At the inspected revision the candidate has
     * no such output at its boundary (gapWarningOutput).
     */
  }

  item def CollisionWarning {
    doc /* The collision warning the driver gets in two modes: on the display and as a sound. */
  }

  part def SCORECommandAndWarningPath :> OperationalEntity {
    doc /*
     * The Eclipse S-CORE path of the vehicle: it carries the candidate's
     * driving command to the actuation and its warning request to the AAOS
     * SDV, with no exchange beside it. A System 1 part outside the candidate
     * and no enabling system. Phases 6 to 8 decide its realization
     * (gapScoreIntegration). The S-CORE integration layer of INC-MW-011 is that
     * increment's system of interest and holds the Autoware adapter, so it is
     * not reused as this role.
     */
  }

  part def DriverWarningPresentation :> OperationalEntity {
    doc /*
     * What in the AAOS SDV gives the driver the collision warning on the
     * display and as a sound when the warning request arrives. It sends
     * nothing to the candidate. It is not the informational visualization of
     * the AEBS visualization increment (gapDriverHmiInProductLine).
     */
  }

  part driverAssistanceOperationalContext : SystemContext {
    doc /*
     * The operational context of the candidate driver-assistance system.
     * Inside the system of interest, as phase 0 draws it: perception of the
     * lane and of the closest object in the path, speed and steering
     * planning, and the warning and braking decision; it stays a black box
     * until the architecture phases. Around it: the vehicle whose front camera
     * and speed feed it and whose actuation moves it, the road environment,
     * the vehicle targets, the Eclipse S-CORE path, the AAOS SDV with the
     * warning presentation, and the driver who gets the warning. The S-CORE
     * path and the AAOS SDV are System 1 parts outside the candidate; the path
     * between them is an internal exchange of the realization that phases 6 to
     * 8 decide. System 1 roles only: CARLA, the cloud hosts, the scenario
     * runner, the evaluators, the capture of the display and of the sound,
     * and the recordings stay in driverAssistanceVerificationEnvironment.
     * This is the operational environment, not a deployment decomposition.
     */
    part candidateSystem : DriverAssistanceSystem :>> systemOfInterest;
    part vehicle : SubjectVehicle {
      doc /* The vehicle the candidate assists: its front camera and speed give the input, its steering, acceleration and brakes take the driving command. */
    }
    part roadEnvironment : RoadEnvironment {
      doc /* The road and the lanes of the scenario: what the front camera sees and where the vehicle drives. */
    }
    part stationaryVehicleTarget : VehicleTarget {
      doc /* A vehicle that stands still: ahead in the vehicle's lane, or just outside the guard pipes of a curve. */
    }
    part movingVehicleTarget : VehicleTarget {
      doc /* A vehicle that drives ahead in the vehicle's lane: slower than the vehicle, or turning off at a corner. */
    }
    part scorePath : SCORECommandAndWarningPath {
      doc /* The Eclipse S-CORE path that carries the driving command to the actuation and the warning request to the AAOS SDV. */
    }
    part aaosSDVGuest : AAOSSDVGuestExecutionDomain {
      doc /* The AAOS SDV of the existing S-CORE and AAOS SDV integration, which gives the driver the collision warning; phases 6 to 8 decide its realization. */
      part warningPresentation : DriverWarningPresentation;
    }
    part driver : Driver {
      doc /* The driver who gets the collision warning on the display and as a sound. Driver monitoring, override and deactivation are out of scope. */
    }
  }

  /* Operational behavior: the candidate's items cross its boundary; the driver only receives. */
  action def DriverAssistanceOperation {
    doc /*
     * One cycle in the world: the vehicle captures the front-camera image and
     * its speed, the candidate decides, its driving command reaches the
     * actuation and its warning request reaches the AAOS SDV through the
     * S-CORE path, and the AAOS SDV warns the driver.
     */
    action senseScene {
      doc /* The vehicle: its front camera captures the road environment and the targets, and it samples its speed. */
      out frontCameraImage : FrontCameraImage;
      out vehicleSpeed : VehicleSpeed;
    }

    action assistDriving {
      doc /* The candidate: perceives the lane and the closest object in the path, plans speed and steering, and decides on the warning and the braking. */
      in frontCameraImage : FrontCameraImage;
      in vehicleSpeed : VehicleSpeed;
      out drivingCommand : DrivingCommand;
      out warningRequest : WarningRequest;
    }

    flow from senseScene.frontCameraImage to assistDriving.frontCameraImage;
    flow from senseScene.vehicleSpeed to assistDriving.vehicleSpeed;
    first senseScene then assistDriving;

    action carryOverSCORE {
      doc /* The S-CORE path: carries the driving command and the warning request, with no exchange beside it. */
      in drivingCommand : DrivingCommand;
      in warningRequest : WarningRequest;
      out carriedCommand : DrivingCommand;
      out carriedWarningRequest : WarningRequest;
    }

    flow from assistDriving.drivingCommand to carryOverSCORE.drivingCommand;
    flow from assistDriving.warningRequest to carryOverSCORE.warningRequest;
    first assistDriving then carryOverSCORE;

    action actuateVehicle {
      doc /* The vehicle: steering, acceleration and brakes move it, which changes what its front camera sees next. */
      in drivingCommand : DrivingCommand;
    }

    flow from carryOverSCORE.carriedCommand to actuateVehicle.drivingCommand;

    action presentWarning {
      doc /* The AAOS SDV: gives the collision warning on its display and as a sound. */
      in warningRequest : WarningRequest;
      out collisionWarning : CollisionWarning;
    }

    flow from carryOverSCORE.carriedWarningRequest to presentWarning.warningRequest;

    action receiveWarning {
      doc /* The driver: gets the warning; nothing flows back to the candidate. */
      in collisionWarning : CollisionWarning;
    }

    flow from presentWarning.collisionWarning to receiveWarning.collisionWarning;
  }

  action driverAssistanceOperation : DriverAssistanceOperation;

  /* Operational story on the SYSMOD seam. */
  use case def AssistDriverForVehicleTargetAhead :> SYSMODSystemUseCaseBase {
    doc /* The candidate in operation: it warns and brakes for a vehicle target ahead in its lane, and does neither when no collision is imminent. */
    attribute redefines ucMotivation = "Vehicle occupants and road users need the vehicle to warn its driver and to brake when a collision with a vehicle ahead in its lane is imminent, and to do neither when it is not.";
    attribute redefines ucTrigger = "The vehicle drives with the candidate active, and its front camera and speed deliver input while a vehicle target is ahead in its lane or in view outside its path.";
    attribute redefines ucResult = "For a vehicle target ahead in the lane, the warning request leads to the collision warning on the display and as a sound, and the driving command brakes the vehicle; where no collision is imminent, neither a warning nor braking is given.";

    objective {
      doc /*
       * Frame the warning and the braking for a vehicle target, and the false
       * reaction, only. The criteria, the time of the warning before the
       * braking and the parameters of each scenario are fixed with the
       * requirements (phase 5).
       */
    }
  }

  use case driverAssistanceStory : AssistDriverForVehicleTargetAhead {
    subject candidateSystem : DriverAssistanceSystem = driverAssistanceOperationalContext::candidateSystem;
    actor vehicle : SubjectVehicle = driverAssistanceOperationalContext::vehicle;
    actor roadEnvironment : RoadEnvironment = driverAssistanceOperationalContext::roadEnvironment;
    actor stationaryVehicleTarget : VehicleTarget = driverAssistanceOperationalContext::stationaryVehicleTarget;
    actor movingVehicleTarget : VehicleTarget = driverAssistanceOperationalContext::movingVehicleTarget;
    actor scorePath : SCORECommandAndWarningPath = driverAssistanceOperationalContext::scorePath;
    actor warningPresentation : DriverWarningPresentation = driverAssistanceOperationalContext::aaosSDVGuest::warningPresentation;
    actor driver : Driver = driverAssistanceOperationalContext::driver;

    objective {
      doc /*
       * Operate the candidate without selecting perception, transport or
       * display technology, and without any safety, on-road, compliance or
       * production-readiness claim.
       */
    }

    first start;
    then include warnAndBrakeForStationaryVehicle;
    then include warnAndBrakeForSlowerVehicle;
    then include noReactionToStationaryVehicleBeyondTheCurve;
    then include noReactionToVehicleAheadTurningOff;
    then done;
  }

  use case warnAndBrakeForStationaryVehicle {
    subject candidateSystem : DriverAssistanceSystem = driverAssistanceOperationalContext::candidateSystem;
    actor vehicle : SubjectVehicle = driverAssistanceOperationalContext::vehicle;
    actor stationaryVehicleTarget : VehicleTarget = driverAssistanceOperationalContext::stationaryVehicleTarget;
    actor scorePath : SCORECommandAndWarningPath = driverAssistanceOperationalContext::scorePath;
    actor warningPresentation : DriverWarningPresentation = driverAssistanceOperationalContext::aaosSDVGuest::warningPresentation;
    actor driver : Driver = driverAssistanceOperationalContext::driver;

    objective {
      doc /*
       * SC-DRIVING-012 (stationary vehicle target ahead): the vehicle
       * approaches a stationary vehicle target ahead in its lane; the
       * candidate requests the warning, the AAOS SDV warns the driver on the
       * display and as a sound, and the candidate's driving command brakes
       * the vehicle.
       */
    }

    first start;
    then done;
  }

  use case warnAndBrakeForSlowerVehicle {
    subject candidateSystem : DriverAssistanceSystem = driverAssistanceOperationalContext::candidateSystem;
    actor vehicle : SubjectVehicle = driverAssistanceOperationalContext::vehicle;
    actor movingVehicleTarget : VehicleTarget = driverAssistanceOperationalContext::movingVehicleTarget;
    actor scorePath : SCORECommandAndWarningPath = driverAssistanceOperationalContext::scorePath;
    actor warningPresentation : DriverWarningPresentation = driverAssistanceOperationalContext::aaosSDVGuest::warningPresentation;
    actor driver : Driver = driverAssistanceOperationalContext::driver;

    objective {
      doc /*
       * SC-DRIVING-013 (slower moving vehicle target ahead): the vehicle
       * approaches a slower moving vehicle target ahead in its lane; the
       * candidate requests the warning, the AAOS SDV warns the driver on the
       * display and as a sound, and the candidate's driving command brakes
       * the vehicle.
       */
    }

    first start;
    then done;
  }

  use case noReactionToStationaryVehicleBeyondTheCurve {
    subject candidateSystem : DriverAssistanceSystem = driverAssistanceOperationalContext::candidateSystem;
    actor vehicle : SubjectVehicle = driverAssistanceOperationalContext::vehicle;
    actor roadEnvironment : RoadEnvironment = driverAssistanceOperationalContext::roadEnvironment;
    actor stationaryVehicleTarget : VehicleTarget = driverAssistanceOperationalContext::stationaryVehicleTarget;
    actor scorePath : SCORECommandAndWarningPath = driverAssistanceOperationalContext::scorePath;

    objective {
      doc /*
       * SC-DRIVING-014 (no reaction, stationary vehicle beyond a curve): the
       * vehicle drives through a tight curve with guard pipes on its outer
       * side, and a stationary vehicle stands just outside the guard pipes, on
       * the extension of the centre of the lane: ahead of the vehicle before
       * the curve turns it away, never in its path. The candidate requests no
       * warning and commands no emergency braking. The regulation's
       * false-reaction scenarios include this situation, as a curved road with
       * guard pipes and a stationary object. Phase 2 proposes it; phase 5
       * confirms the selection and states the criterion
       * (gapVehicleTargetCriteria).
       */
    }

    first start;
    then done;
  }

  use case noReactionToVehicleAheadTurningOff {
    subject candidateSystem : DriverAssistanceSystem = driverAssistanceOperationalContext::candidateSystem;
    actor vehicle : SubjectVehicle = driverAssistanceOperationalContext::vehicle;
    actor roadEnvironment : RoadEnvironment = driverAssistanceOperationalContext::roadEnvironment;
    actor movingVehicleTarget : VehicleTarget = driverAssistanceOperationalContext::movingVehicleTarget;
    actor scorePath : SCORECommandAndWarningPath = driverAssistanceOperationalContext::scorePath;

    objective {
      doc /*
       * SC-DRIVING-015 (no reaction, vehicle ahead turning off): the vehicle
       * follows a vehicle ahead in its lane that slows down and turns off at a
       * corner, while the vehicle goes straight on; no collision becomes
       * imminent. The candidate requests no warning and commands no emergency
       * braking. The regulation's false-reaction scenarios include this
       * situation, as a right or left turn of a forward vehicle. Phase 2
       * proposes it; phase 5 confirms the selection and states the criterion
       * (gapVehicleTargetCriteria).
       */
    }

    first start;
    then done;
  }

  /* Traces to the Phase 0 records this context implements. */
  dependency driverAssistanceStoryAnswersProblem
    from driverAssistanceStory
    to DE4SDV_DriverAssistanceFraming::driverAssistanceProblem;
  dependency scorePathOnBenchReuse
    from driverAssistanceOperationalContext::scorePath
    to DE4SDV_DriverAssistanceFraming::asmBenchReuse;
  dependency aaosSDVGuestOnBenchReuse
    from driverAssistanceOperationalContext::aaosSDVGuest
    to DE4SDV_DriverAssistanceFraming::asmBenchReuse;
  dependency scorePathOnScoreIntegrationGap
    from SCORECommandAndWarningPath
    to DE4SDV_DriverAssistanceFraming::gapScoreIntegration;
  dependency warningPresentationOnDriverHmiGap
    from DriverWarningPresentation
    to DE4SDV_DriverAssistanceFraming::gapDriverHmiInProductLine;
  dependency warningRequestOnWarningOutputGap
    from WarningRequest
    to DE4SDV_DriverAssistanceFraming::gapWarningOutput;
  dependency noReactionScenariosOnCriteriaGap
    from driverAssistanceStory
    to DE4SDV_DriverAssistanceFraming::gapVehicleTargetCriteria;

  concern driverAssistanceContextConcern : OperationalContextConcern {
    doc /*
     * System architects, systems engineers and open-source reviewers need to
     * see what is inside the candidate and what is around it: the vehicle,
     * the road environment, the vehicle targets, the Eclipse S-CORE path, the
     * AAOS SDV and the driver, and which items cross the boundary in which
     * direction. The S-CORE path and the AAOS SDV are outside the candidate;
     * the driver only receives.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view driverAssistanceOperationalContextView {
    viewpoint driverAssistanceContextViewpoint : OperationalContextDefinitionViewpoint {
      frame driverAssistanceContextConcern;
    }

    expose driverAssistanceOperationalContext;
    expose driverAssistanceOperationalContext::*;
    expose driverAssistanceOperation;
    attribute depth = 2;
    attribute showAnnotationRows = false;
    render asTreeDiagram;
  }

  concern driverAssistanceStoryConcern : OperationalStoryConcern {
    doc /*
     * Systems engineers, verification engineers and open-source reviewers
     * need the candidate told in stakeholder language: the warning and the
     * braking for a stationary and for a slower moving vehicle target ahead,
     * and no reaction where none is due.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view driverAssistanceOperationalStoryView {
    viewpoint driverAssistanceStoryViewpoint : OperationalStoryViewpoint {
      frame driverAssistanceStoryConcern;
      frame vehicleTargetResponseConcern;
    }

    expose driverAssistanceStory;
    expose driverAssistanceStory::*;
    attribute depth = 1;
    attribute showAnnotationRows = false;
    render asTreeDiagram;
  }
}
