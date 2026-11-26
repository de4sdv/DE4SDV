/*
 * DE4SDV HMI display physical and software realization.
 *
 * INC-HMI-001, phase 8: the physical and software realization of the HMI
 * display. What software, hardware and deployment elements realize the three
 * logical elements of phase 7, and which elements carry each input from the
 * SDV Core VM to the high availability renderer and to the app that draws the
 * scene, as REQ-HMI-009 asks?
 *
 * The placement (owner decision of 2026-11-25):
 *
 * - The identity recorder is a DE4SDV service on the computer that starts the
 *   VMs, and that service starts them: the central computer in the vehicle,
 *   the guest host on the bench. Before it starts the IVI and SDV Media VMs,
 *   it records the display identity, every part that the term names. It
 *   follows the pattern of the identity recording application of the
 *   driver-assistance increment, which the platform's launcher starts first.
 *   The record is a self-report of System 1; System 2 only reads it into the
 *   evidence of a run.
 * - The drawn scene reaches the screen by composition, the design that Android
 *   SDV documents (upstream.md): the renderer's plane lies over the IVI plane
 *   on one display. The app in the IVI VM that draws the scene sends the
 *   renderer a heartbeat with each frame that it draws, carrying the time of
 *   the scene in that frame. While that scene is current by the term current,
 *   the renderer keeps the scene area transparent; while it is not, the
 *   renderer covers the area with its placeholder. So the drawn scenes of
 *   phase 7 are realized by the heartbeats and by the composition of the IVI
 *   plane under the renderer's plane.
 * - In the display's runs the IVI VM runs no other warning presentation: the
 *   warning presentation of the driver-assistance increment does not run
 *   there, so no element but the renderer draws the vehicle speed or the
 *   collision warning. The realization, the runs and the verdicts of the
 *   driver-assistance increment stay as they are.
 * - The vehicle speed follows the vehicle's own path: an ECU measures it, the
 *   vehicle network carries it to the central computer, and the SDV Core VM
 *   takes it in as vehicle data. A DE4SDV publisher in the SDV Core VM gives
 *   it, over the platform's messaging, to the vehicle data of the renderer,
 *   which has a speed message. On the bench the simulator stands in for the
 *   ECU and the network and feeds the SDV Core VM. The vehicle-network
 *   increment names that path and keeps it out of its scope
 *   (eeSensorDataOutOfScope).
 * - No readiness session runs with this phase. One follows it, at its cost and
 *   with the owner's go each time, so this phase states its readiness
 *   questions as gaps.
 *
 * What follows from the phase 7 elements and the defaults of this phase:
 *
 * - Topology: four software elements carry the three logical elements. The
 *   identity recording service and the composition of the display are on the
 *   central computer, the scene drawing app is in the IVI VM, and the high
 *   availability renderer is in the SDV Media VM. The presenter is carried by
 *   the renderer and the composition together, so the drawn scene reaches the
 *   display only through the presenter's side. The central computer runs three
 *   VMs, SDV Core, IVI and SDV Media, under its hypervisor; on the bench the
 *   guest host of INC-DRIVING-001 stands in for it, and no element of the
 *   bench is modeled here.
 * - Paths: the inputs reach the display in the SDV Core VM. The warning
 *   request reaches it as the Data Tunnel topic that the SOME/IP interop
 *   publishes for the Eclipse S-CORE path of the driver-assistance increment,
 *   the vehicle speed as vehicle data, and the scene as a Data Tunnel topic
 *   that a context stand-in publishes, since the scene's way out of the
 *   candidate stays open. The Data Tunnel carries the scene on to the SDV
 *   Gateway on the IVI VM and to the app. The vehicle data publisher gives the
 *   speed, the warning request and the time of each scene to the renderer.
 * - Time: of the display's 0.1 s, 0.05 s is for the hop from the SDV Core VM
 *   to the renderer or to the app, and 0.05 s for the drawing and for the
 *   start of the sound; both are unmeasured and revisited when a readiness
 *   probe measures them. The clocks and the simulator's mode are those of the
 *   driver-assistance increment: simulation time is the time that each value
 *   carries from its source, and wall-clock time is the time of the host.
 * - VSS at the ports only: the vehicle speed as Vehicle.Speed, the distance to
 *   the object that the system acts on in the scene as
 *   Vehicle.ADAS.ObstacleDetection.Distance, and the warning request in the
 *   payload of the driver-assistance increment. Apart from that distance, the
 *   scene, the time of a scene, the heartbeat, the planes, the frames of the
 *   display and the chime are no vehicle signal, and their records say so. No
 *   VSS extension is added.
 * - Looks of an outdated element (REQ-HMI-006): the renderer's placeholder
 *   covers the scene area, the speed shows no number, and the warning shows
 *   one fixed symbol while it is unavailable. The visual design stays out of
 *   scope (hmiHumanFactorsOutOfScope).
 * - The changes to the projects of the renderer and of the candidate stay
 *   gaps; nothing is written to their maintainers.
 *
 * Alternatives recorded and not selected:
 * - ALT-HMI-RECORDERINCORE-001: the identity recorder inside the SDV Core VM.
 *   A recorder in a VM records no image of the IVI or SDV Media VM before
 *   their start, which the record has to precede.
 * - ALT-HMI-SCENESTREAM-001: the app streams its drawn frames to the renderer,
 *   which draws them. The renderer would draw video, a larger change to it
 *   than a time in a heartbeat.
 * - ALT-HMI-SPEEDOVERSCORE-001: the vehicle speed on the Eclipse S-CORE path
 *   beside the warning request. It changes the path of the driver-assistance
 *   increment, and the speed is no output of the candidate.
 *
 * The IVI and SDV Media VMs with the software of the display, the identity
 * recording service and the composition on the central computer, and the paths
 * from the SDV Core VM are inside the display. The platform of the SDV Core
 * VM, where the inputs reach the display, is shared with the Eclipse S-CORE
 * path, which is outside it. The candidate, the S-CORE path and the simulator
 * stay in the realization of the driver-assistance increment; the simulator,
 * the capture of the display and of the sound, and the evaluators are System
 * 2. An allocation here is a responsibility assignment, no deployment,
 * execution or runtime claim; a signal mapping is no interoperability claim.
 * Nothing in this package claims that a requirement is met, that a case ran or
 * that the bench has shown anything.
 */
package DE4SDV_HmiDisplayPhysicalSoftwareRealization {
  private import ScalarValues::*;
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_MethodProcess::SystemToSoftwareSignalMappingCandidate;
  private import DE4SDV_MethodProcess::LogicalToSoftwareSignalMappingRecord;
  private import DE4SDV_MethodProcess::SignalMappingDisposition;
  private import DE4SDV_TraceVocabulary::PhysicalAllocationElement;
  private import DE4SDV_SDVPlatformStack::AndroidHLOS;
  private import DE4SDV_SDVPlatformStack::AndroidSDVMiddleware;
  private import DE4SDV_SDVPlatformStack::OSPlatformLayer;
  private import DE4SDV_SDVPlatformStack::OSHypervisorInterface;
  private import DE4SDV_SDVPlatformStack::HypervisorLayer;
  private import DE4SDV_AAOSSDVMiddlewareBoundary::SDVCoreBoundary;
  private import DE4SDV_AAOSSDVMiddlewareBoundary::SDVGatewayOnIVIBoundary;
  private import DE4SDV_DriverAssistancePhysicalSoftwareRealization::WarningRequestEventPayload;
  private import DE4SDV_DriverAssistancePhysicalSoftwareRealization::WarningRequestEventIn;
  private import DE4SDV_DriverAssistancePhysicalSoftwareRealization::WarningRequestEventOut;
  private import DE4SDV_HmiDisplayFraming::gapHmiSceneOutput;
  private import DE4SDV_HmiDisplayFraming::gapHmiRendererCollisionWarning;
  private import DE4SDV_HmiDisplayFraming::gapHmiRendererIntegration;
  private import DE4SDV_HmiDisplayFraming::gapHmiWarningPresentation;
  private import DE4SDV_HmiDisplayFraming::gapHmiMemberGuestLayout;
  private import DE4SDV_HmiDisplayFraming::asmHmiRendererWithoutGraphicsCard;
  private import DE4SDV_HmiDisplayFraming::hmiRendererAllocationConcern;
  private import DE4SDV_HmiDisplayFraming::hmiRendererPathConcern;
  private import DE4SDV_HmiDisplayFunctionalArchitecture::DisplaySceneInput;
  private import DE4SDV_DriverAssistanceOperationalContext::VehicleSpeed;
  private import DE4SDV_HmiDisplayFunctionalArchitecture::DisplayContentOutput;
  private import DE4SDV_HmiDisplayLogicalArchitecture::HmiDisplayLogicalSystem;
  private import DE4SDV_HmiDisplayNeedsRequirements::reqRendererSplitAndInputPaths;
  private import COVESA_VSS::SignalDefinitions::Vehicle_Speed;
  private import COVESA_VSS::SignalDefinitions::Vehicle_ADAS_ObstacleDetection_Distance;
  private import DE4SDV_Stakeholders::*;
  private import SAF_Viewpoints::*;
  private import SysideViews::**;
  private import Views::*;

  /* ───────────── The items this phase types at the software contracts ───────────── */

  item def DisplaySceneMessage :> DisplaySceneInput {
    doc /*
     * The scene as the realization types it on the Data Tunnel topic of the
     * SDV Core VM and through the SDV Gateway into the scene drawing app: the
     * scene of one result pass with its capture time in simulation time. Its
     * message type is new and stays open until phase 10. A scene is no vehicle
     * signal, except the distance to the object that the system acts on:
     * COVESA VSS types it at the port as obstacleDistance
     * (Vehicle_ADAS_ObstacleDetection_Distance, m), the value in m of the
     * inherited actedOnObjectDistance (MAP-HMI-SCENE).
     */
    attribute obstacleDistance : Vehicle_ADAS_ObstacleDetection_Distance[0..1];
  }

  item def DisplayVehicleSpeedSample :> VehicleSpeed {
    doc /*
     * The vehicle speed as the realization types it from the vehicle data of
     * the SDV Core VM to the speed message of the renderer's vehicle data. The
     * speed is typed by COVESA VSS at the port (Vehicle_Speed, km/h); the
     * sample time is the time that its source gives it, on the bench the
     * simulation time of the world snapshot (MAP-HMI-VEHICLE-SPEED).
     */
    attribute speed : Vehicle_Speed;
    attribute sampleTime : Real;
  }

  item def DisplaySceneTime {
    doc /*
     * The time of a scene that has reached the HMI display, the capture time
     * in simulation time of the camera image of its result pass, as the
     * vehicle data publisher gives it to the renderer to judge the currency of
     * the scene. The rest of the scene does not go to the renderer. No vehicle
     * signal (MAP-HMI-SCENE-TIME).
     */
    attribute captureTime : Real;
  }

  item def DrawnSceneHeartbeat {
    doc /*
     * The heartbeat that the scene drawing app sends the renderer with each
     * frame that it draws, in the place of the heartbeats of Android SDV's
     * design (upstream.md), carrying the time of the scene in that frame. With
     * the IVI plane it realizes the drawn scenes of phase 7. No vehicle signal
     * (MAP-HMI-DRAWN-SCENE-HEARTBEAT).
     */
    attribute sceneCaptureTime : Real;
  }

  item def DisplayPlane {
    doc /*
     * The frames of one plane of the display: the IVI plane, on which the
     * scene drawing app draws the scene, or the renderer's plane, which lies
     * over it. Pixels, no vehicle signal (MAP-HMI-IVI-PLANE).
     */
  }

  item def ComposedDisplayFrame :> DisplayContentOutput {
    doc /*
     * What the HMI display shows, as the frames of the one display: the
     * renderer's plane composed over the IVI plane. Pixels, no vehicle signal
     * (MAP-HMI-SHOWN-CONTENT).
     */
  }

  item def CollisionWarningChime {
    doc /*
     * The collision warning as a sound: the chime that the renderer gives
     * while the warning request asks for the warning. A sound, no vehicle
     * signal (MAP-HMI-WARNING-CHIME).
     */
  }

  /* ───────────── Ports: one pair per item, whatever hop carries it ───────────── */

  port def DisplaySceneMessageOut {
    doc /* The typed scene leaving an element: from the Data Tunnel of the SDV Core VM to the IVI VM. */
    out item sceneMessage : DisplaySceneMessage;
  }
  port def DisplaySceneMessageIn {
    doc /* The typed scene entering an element: the SDV Core VM, the IVI VM, the publisher or the app. */
    in item sceneMessage : DisplaySceneMessage;
  }
  port def DisplayVehicleSpeedSampleOut {
    doc /* The typed vehicle speed leaving an element: the vehicle data publisher or the SDV Core VM. */
    out item speedSample : DisplayVehicleSpeedSample;
  }
  port def DisplayVehicleSpeedSampleIn {
    doc /*
     * The typed vehicle speed entering an element: the SDV Core VM, the
     * publisher, the SDV Media VM or the renderer.
     */
    in item speedSample : DisplayVehicleSpeedSample;
  }
  port def DisplaySceneTimeOut {
    doc /* The time of a scene leaving the vehicle data publisher or the SDV Core VM for the renderer. */
    out item sceneTime : DisplaySceneTime;
  }
  port def DisplaySceneTimeIn {
    doc /* The time of a scene entering the SDV Media VM or the renderer. */
    in item sceneTime : DisplaySceneTime;
  }
  port def DrawnSceneHeartbeatOut {
    doc /* The heartbeat of a drawn frame leaving the scene drawing app or the IVI VM. */
    out item heartbeat : DrawnSceneHeartbeat;
  }
  port def DrawnSceneHeartbeatIn {
    doc /* The heartbeat of a drawn frame entering the SDV Media VM or the renderer. */
    in item heartbeat : DrawnSceneHeartbeat;
  }
  port def DisplayPlaneOut {
    doc /* A plane of the display leaving the element that draws it: the scene drawing app or the renderer. */
    out item plane : DisplayPlane;
  }
  port def DisplayPlaneIn {
    doc /* A plane of the display entering the composition, or the central computer on its way there. */
    in item plane : DisplayPlane;
  }
  port def ComposedDisplayFrameOut {
    doc /* The frames of the one display leaving the composition for the driver. */
    out item displayFrame : ComposedDisplayFrame;
  }
  port def CollisionWarningChimeOut {
    doc /* The chime of the collision warning leaving the renderer for the driver. */
    out item chime : CollisionWarningChime;
  }

  /* ───────────── The software elements: four, for three logical elements ───────────── */

  part def DisplayIdentityRecordingService :> PhysicalAllocationElement {
    doc /*
     * Carries the identity recorder of phase 7, beside the software of the
     * scene drawing app and of the renderer and inside neither VM: a DE4SDV
     * service on the computer that starts the VMs, which starts them (owner
     * decision of 2026-11-25). In the vehicle that computer is the central
     * computer; on the bench the guest host stands in for it. In each run,
     * before it starts the IVI and SDV Media VMs, it records the display
     * identity as the term of the requirements defines it: the SHA-256 of the
     * files of the build of the high availability renderer, of the files of
     * the build of the scene drawing app, of the image of the IVI VM and of
     * the SDV Media VM, and of the sound file of the collision warning; the
     * SHA-256 of each configuration file that the HMI display reads at its
     * start; and the settings of its start, verbatim. Only then does it start
     * the two VMs, so the record comes before the first frame of the display
     * (REQ-HMI-010). It follows the pattern of the identity recording
     * application of the driver-assistance increment, which the platform's
     * launcher starts first. The record is a self-report of System 1, a file
     * of the run that System 2 only reads into the evidence of the run. It
     * sends nothing to another element of the display, so it has no port. How
     * long the recording delays the start of the two VMs is not measured. A
     * build item, named here, not claimed.
     */
  }

  part def SceneDrawingApplication :> PhysicalAllocationElement {
    doc /*
     * Carries the scene drawer of phase 7: a DE4SDV Android app in the IVI VM,
     * a build item, named here, not claimed. It subscribes to the topic of the
     * scene through the SDV Gateway and draws each scene that reaches it, or a
     * newer one, with the object that the system acts on, when the scene has
     * one, as an element of its own, in the scene area of the display of the
     * IVI VM, the IVI plane. With each frame that it draws, it sends the
     * renderer a heartbeat that carries the time of the scene in that frame.
     * It takes the place that Android SDV's design gives DriverUI, the app in
     * the IVI VM whose heartbeats tell the renderer that Android is alive
     * (upstream.md), for the scene area only. It draws neither the vehicle
     * speed nor the collision warning and gives no sound (REQ-HMI-009). While
     * it, or Android in the IVI VM, is out, no heartbeat comes, and the
     * renderer covers the scene area. Of the display's 0.1 s it has 0.05 s,
     * from the arrival of a scene to its first frame on the display,
     * unmeasured. How a drawn position is read against the scene is not set
     * yet (gapHmiDrawingToleranceUnset). The look of the scene stays out of
     * scope (hmiHumanFactorsOutOfScope).
     */
    port sceneMessageIn : DisplaySceneMessageIn;
    port heartbeatOut : DrawnSceneHeartbeatOut;
    port iviPlaneOut : DisplayPlaneOut;
  }

  part def HighAvailabilityRenderer :> PhysicalAllocationElement {
    doc /*
     * Carries the presenter of phase 7, together with the composition of the
     * display: the high availability renderer of Android SDV's display safety
     * with its app, in the SDV Media VM, at the commits that the upstream
     * record names (upstream.md), with DE4SDV changes that its project has not
     * taken (gapHmiRendererCollisionWarning, gapHmiRendererJudgesSceneCurrency).
     * From its vehicle data it takes the vehicle speed, each event of the
     * warning request and the time of each scene that reaches the display,
     * which the vehicle data publisher of the SDV Core VM gives it; from the
     * scene drawing app it takes a heartbeat with each drawn frame. It judges by
     * the term current whether the scene as drawn, the vehicle speed and the
     * warning request are current. On its plane, which lies over the IVI plane
     * on the one display, it draws the vehicle speed to the whole km/h and no
     * number while the speed is outdated; the collision warning while the
     * warning request asks for it; and one fixed symbol while the warning is
     * unavailable. It keeps the scene area transparent while the scene as drawn
     * is current and covers it with its placeholder while it is outdated. It
     * gives the collision warning as a sound, its chime. It takes nothing from
     * the IVI VM but the heartbeats, so it goes on through each outage in the
     * IVI VM (REQ-HMI-008). Of the display's 0.1 s it has 0.05 s, from the
     * arrival of a value to the first frame on the display that shows it and to
     * the start of the chime, unmeasured. The symbols and the chime stay with
     * their design (gapHmiRendererCollisionWarning).
     */
    port speedSampleIn : DisplayVehicleSpeedSampleIn;
    port warningEventIn : WarningRequestEventIn;
    port sceneTimeIn : DisplaySceneTimeIn;
    port heartbeatIn : DrawnSceneHeartbeatIn;
    port rendererPlaneOut : DisplayPlaneOut;
    port chimeOut : CollisionWarningChimeOut;
  }

  part def DisplayPlaneComposition :> PhysicalAllocationElement {
    doc /*
     * Carries the presenter of phase 7, together with the high availability
     * renderer: the composition of the one display on the central computer,
     * which puts the renderer's plane over the IVI plane, as Android SDV's
     * design places them (upstream.md), and gives the frames on the display.
     * It adds nothing of its own and chooses nothing: of the IVI plane the
     * driver sees what the renderer's plane leaves transparent. The presenter
     * is allocated to it because the drawn scene reaches the display only
     * through it; carrying no logical element, it would be a way from the
     * scene drawer to the driver beside the presenter. It is outside the IVI
     * VM, so it goes on through each outage there. In the vehicle the central
     * computer composes its display; on the bench the guest host stands in for
     * it, and whether it composes the two planes there is not observed
     * (gapHmiRendererIntegration).
     */
    port iviPlaneIn : DisplayPlaneIn;
    port rendererPlaneIn : DisplayPlaneIn;
    port displayFrameOut : ComposedDisplayFrameOut;
  }

  /* ───────────── The path element in the SDV Core VM ───────────── */

  part def RendererVehicleDataPublisher {
    doc /*
     * The vehicle data publisher of the display: a DE4SDV service in the SDV
     * Core VM, inside the boundary of the display, a build item named here, not
     * claimed. It carries no logical element: it is a hop of the paths that
     * bring the presenter its inputs (REQ-HMI-009). It reads the vehicle speed
     * from the vehicle data of the SDV Core VM and subscribes to the Data
     * Tunnel topics of the warning request and of the scene. Over the
     * platform's messaging between the VMs it publishes each vehicle speed to
     * the speed message of the renderer's vehicle data, and each event of the
     * warning request and the time of each scene, which are new to that vehicle
     * data (gapHmiRendererCollisionWarning, gapHmiRendererJudgesSceneCurrency).
     * It changes no value and no time. How a producer in the SDV Core VM
     * reaches the renderer's topics is open (gapHmiRendererIntegration).
     */
    port speedSampleIn : DisplayVehicleSpeedSampleIn;
    port warningEventIn : WarningRequestEventIn;
    port sceneMessageIn : DisplaySceneMessageIn;
    port speedSampleOut : DisplayVehicleSpeedSampleOut;
    port warningEventOut : WarningRequestEventOut;
    port sceneTimeOut : DisplaySceneTimeOut;
  }

  /* ───────────── The VMs and the central computer ───────────── */

  part def HmiDisplaySDVCoreGuest {
    doc /*
     * The SDV Core VM of the display's runs, where the inputs reach the HMI
     * display: Android under the hypervisor of the central computer, with the
     * SDV Core middleware. Its SOME/IP interop receives the warning request
     * from the Eclipse S-CORE path of the driver-assistance increment, outside
     * the display, and its broker publishes it as the Data Tunnel topic of
     * that increment. The vehicle speed reaches it as vehicle data: in the
     * vehicle from the ECU that measures it, over the vehicle network; on the
     * bench from the simulator, which stands in for both
     * (gapHmiBenchSpeedFeed). The scene reaches it as a Data Tunnel topic that
     * a context stand-in publishes, since the scene's way out of the candidate
     * is open (gapHmiSceneOutput). The Data Tunnel carries the scene on to the
     * IVI VM, and the vehicle data publisher of the display gives the speed,
     * the warning request and the time of each scene to the SDV Media VM. The
     * SDV Core boundary model of packages/architecture is referenced and bound
     * to the middleware layer; nothing of the platform is built by DE4SDV.
     */
    port warningSomeIpIn : WarningRequestEventIn;
    port speedSampleIn : DisplayVehicleSpeedSampleIn;
    port sceneMessageIn : DisplaySceneMessageIn;
    port sceneMessageOut : DisplaySceneMessageOut;
    port speedSampleOut : DisplayVehicleSpeedSampleOut;
    port warningEventOut : WarningRequestEventOut;
    port sceneTimeOut : DisplaySceneTimeOut;
    part os : AndroidHLOS;
    part sdvMiddleware : AndroidSDVMiddleware;
    ref part sdvCore : SDVCoreBoundary;
    part vehicleDataPublisher : RendererVehicleDataPublisher;
    bind sdvCore = sdvMiddleware;
    bind warningSomeIpIn = sdvCore.someIp.someIpPort;
    bind speedSampleIn = sdvCore.vsidlMiddleware.signalAccessPort;
    bind sceneMessageIn = sdvCore.dataTunnel.topicPublishPort;
    bind sceneMessageOut = sdvCore.dataTunnel.topicSubscribePort;
    connection warningTopicPublishedByInterop
      connect sdvCore.someIp.topicPublishOut to sdvCore.dataTunnel.topicPublishPort;
    connection warningTopicToPublisher
      connect sdvCore.dataTunnel.topicSubscribePort to vehicleDataPublisher.warningEventIn;
    connection sceneTopicToPublisher
      connect sdvCore.dataTunnel.topicSubscribePort to vehicleDataPublisher.sceneMessageIn;
    connection speedDataToPublisher
      connect sdvCore.vsidlMiddleware.signalAccessPort to vehicleDataPublisher.speedSampleIn;
    bind speedSampleOut = vehicleDataPublisher.speedSampleOut;
    bind warningEventOut = vehicleDataPublisher.warningEventOut;
    bind sceneTimeOut = vehicleDataPublisher.sceneTimeOut;
  }

  part def HmiDisplayIVIGuest {
    doc /*
     * The IVI VM of the display's runs, inside the display: Android under the
     * hypervisor of the central computer, with the SDV Gateway and the scene
     * drawing app. It runs no other warning presentation: the warning
     * presentation of the driver-assistance increment does not run in the
     * display's runs, so no element of this VM draws the vehicle speed or the
     * collision warning (owner decision of 2026-11-25, REQ-HMI-009). It is a
     * definition of its own, not a specialization of that increment's IVI VM,
     * which owns that presentation. The app subscribes to the topic of the
     * scene through the SDV Gateway. The VM gives the renderer the heartbeats,
     * and the composition its display, the IVI plane.
     */
    port sceneMessageIn : DisplaySceneMessageIn;
    port heartbeatOut : DrawnSceneHeartbeatOut;
    port iviPlaneOut : DisplayPlaneOut;
    part os : AndroidHLOS;
    part sdvGateway : SDVGatewayOnIVIBoundary;
    part sceneDrawingApp : SceneDrawingApplication;
    bind sceneMessageIn = sdvGateway.dataTunnelPort;
    connection sceneThroughSDVGateway connect sdvGateway.clientPort to sceneDrawingApp.sceneMessageIn;
    bind heartbeatOut = sceneDrawingApp.heartbeatOut;
    bind iviPlaneOut = sceneDrawingApp.iviPlaneOut;
  }

  part def HmiDisplaySDVMediaGuest {
    doc /*
     * The SDV Media VM, inside the display: a guest of its own under the
     * hypervisor of the central computer, which Android SDV's documentation
     * also calls the rapid boot VM (upstream.md), with the high availability
     * renderer. Its operating system is typed by the platform stack's
     * operating-system layer only: no source that DE4SDV keeps names it. It
     * takes the speed, the warning request and the time of each scene from the
     * SDV Core VM and the heartbeats from the IVI VM, and gives its plane to
     * the composition and the chime to the driver. The boundary model of the
     * AAOS SDV middleware leaves this VM out of its scope; this realization
     * models only what the display needs of it.
     */
    port speedSampleIn : DisplayVehicleSpeedSampleIn;
    port warningEventIn : WarningRequestEventIn;
    port sceneTimeIn : DisplaySceneTimeIn;
    port heartbeatIn : DrawnSceneHeartbeatIn;
    port rendererPlaneOut : DisplayPlaneOut;
    port chimeOut : CollisionWarningChimeOut;
    ref part os : OSPlatformLayer;
    part highAvailabilityRenderer : HighAvailabilityRenderer;
    bind speedSampleIn = highAvailabilityRenderer.speedSampleIn;
    bind warningEventIn = highAvailabilityRenderer.warningEventIn;
    bind sceneTimeIn = highAvailabilityRenderer.sceneTimeIn;
    bind heartbeatIn = highAvailabilityRenderer.heartbeatIn;
    bind rendererPlaneOut = highAvailabilityRenderer.rendererPlaneOut;
    bind chimeOut = highAvailabilityRenderer.chimeOut;
  }

  part def HmiDisplayCentralComputer {
    doc /*
     * The central computer of the vehicle as the HMI display needs it: the
     * computer that hosts the SDV Core, IVI and SDV Media VMs under its
     * hypervisor. Beside the VMs it holds two elements of the display: the
     * identity recording service, which records the display identity and then
     * starts the IVI and SDV Media VMs, and the composition of the display, to
     * whose ports its own are bound. Its own platform and its hypervisor are
     * typed by the generic layers of the platform stack only. On the bench the
     * guest host of INC-DRIVING-001 stands in for it, with the SDV Media VM as
     * a third guest (asmHmiRendererWithoutGraphicsCard); no element of the
     * bench is modeled here. No E/E realization declares the central computer
     * yet; once one does, this realization imports it and no longer declares
     * it.
     */
    port iviPlaneIn : DisplayPlaneIn;
    port rendererPlaneIn : DisplayPlaneIn;
    port displayFrameOut : ComposedDisplayFrameOut;
    ref part os : OSPlatformLayer;
    ref part hypervisor : HypervisorLayer;
    part identityRecordingService : DisplayIdentityRecordingService;
    part planeComposition : DisplayPlaneComposition;
    bind iviPlaneIn = planeComposition.iviPlaneIn;
    bind rendererPlaneIn = planeComposition.rendererPlaneIn;
    bind displayFrameOut = planeComposition.displayFrameOut;
  }

  part def HmiDisplayPhysicalSystem {
    doc /*
     * The physical realization of the HMI display in the vehicle: the central
     * computer and its three VMs. Inside the display are the identity
     * recording service and the composition on the central computer, the IVI
     * VM with the scene drawing app, the SDV Media VM with the high
     * availability renderer, and the paths from the SDV Core VM, with the
     * vehicle data publisher in it. The platform of the SDV Core VM, where the
     * inputs reach the display, is shared with the Eclipse S-CORE path outside
     * it. The candidate, the S-CORE path and the simulator stay in the
     * realization of the driver-assistance increment, and no part here stands
     * for them or for an element of the bench. Between the VMs, the scene goes
     * from the SDV Core VM to the IVI VM on the Data Tunnel; the speed, the
     * warning request and the time of each scene go from the SDV Core VM to
     * the SDV Media VM over the platform's messaging; and the heartbeats go
     * from the IVI VM to the SDV Media VM. The two planes go to the
     * composition on the central computer, the renderer's over the IVI plane.
     * Nothing crosses back to the SDV Core VM or to the IVI VM. It carries
     * REQ-HMI-009 by the elements that it places on those paths.
     */
    part centralComputer : HmiDisplayCentralComputer;
    part hmiSDVCoreGuest : HmiDisplaySDVCoreGuest;
    part hmiIVIGuest : HmiDisplayIVIGuest;
    part hmiSDVMediaGuest : HmiDisplaySDVMediaGuest;
    interface hmiSDVCoreGuestUnderHypervisor : OSHypervisorInterface
      connect hmiSDVCoreGuest.os.hypervisorPort to centralComputer.hypervisor.guestPort;
    interface hmiIVIGuestUnderHypervisor : OSHypervisorInterface
      connect hmiIVIGuest.os.hypervisorPort to centralComputer.hypervisor.guestPort;
    interface hmiSDVMediaGuestUnderHypervisor : OSHypervisorInterface
      connect hmiSDVMediaGuest.os.hypervisorPort to centralComputer.hypervisor.guestPort;
    connection sceneTopicToIVIOverDataTunnel connect hmiSDVCoreGuest.sceneMessageOut to hmiIVIGuest.sceneMessageIn {
      doc /*
       * The scene as the Data Tunnel topic from the SDV Core VM to the SDV
       * Gateway on the IVI VM; its message type stays open until phase 10.
       */
    }
    connection speedToRendererAcrossVMs connect hmiSDVCoreGuest.speedSampleOut to hmiSDVMediaGuest.speedSampleIn {
      doc /*
       * The vehicle speed from the vehicle data publisher to the speed message
       * of the renderer's vehicle data, over the platform's messaging between
       * the VMs.
       */
    }
    connection warningToRendererAcrossVMs connect hmiSDVCoreGuest.warningEventOut to hmiSDVMediaGuest.warningEventIn {
      doc /*
       * Each event of the warning request from the vehicle data publisher to
       * the renderer's vehicle data, over the platform's messaging between the
       * VMs; new to that vehicle data (gapHmiRendererCollisionWarning).
       */
    }
    connection sceneTimeToRendererAcrossVMs connect hmiSDVCoreGuest.sceneTimeOut to hmiSDVMediaGuest.sceneTimeIn {
      doc /*
       * The time of each scene that reaches the display, from the vehicle data
       * publisher to the renderer, over the platform's messaging between the
       * VMs; new to the renderer's vehicle data
       * (gapHmiRendererJudgesSceneCurrency).
       */
    }
    connection drawnSceneHeartbeatToRenderer connect hmiIVIGuest.heartbeatOut to hmiSDVMediaGuest.heartbeatIn {
      doc /*
       * One heartbeat for each frame that the scene drawing app draws, with the
       * time of the scene in it, from the IVI VM to the renderer: with the IVI
       * plane, the drawn scenes of phase 7.
       */
    }
    connection iviPlaneToComposition connect hmiIVIGuest.iviPlaneOut to centralComputer.iviPlaneIn {
      doc /*
       * The IVI plane, on which the scene drawing app draws the scene, into the
       * composition of the display, under the renderer's plane: with the
       * heartbeats, the drawn scenes of phase 7.
       */
    }
    connection rendererPlaneToComposition connect hmiSDVMediaGuest.rendererPlaneOut to centralComputer.rendererPlaneIn {
      doc /* The renderer's plane into the composition of the display, over the IVI plane. */
    }
  }

  part hmiDisplayPhysicalSystem : HmiDisplayPhysicalSystem {
    doc /*
     * The HMI display as the views draw it: the one usage of the physical
     * definition. It depicts the realization of the context's hmiDisplay and
     * is bound to nothing.
     */
  }

  /* ───────────── Logical-to-physical allocations (allocatedTo) ───────────── */

  allocation recorderToIdentityRecordingService
    allocate HmiDisplayLogicalSystem::displayIdentityRecorder
    to hmiDisplayPhysicalSystem::centralComputer::identityRecordingService;
  allocation drawerToSceneDrawingApplication
    allocate HmiDisplayLogicalSystem::sceneDrawer
    to hmiDisplayPhysicalSystem::hmiIVIGuest::sceneDrawingApp;
  allocation presenterToHighAvailabilityRenderer
    allocate HmiDisplayLogicalSystem::displayPresenter
    to hmiDisplayPhysicalSystem::hmiSDVMediaGuest::highAvailabilityRenderer;
  allocation presenterToPlaneComposition
    allocate HmiDisplayLogicalSystem::displayPresenter
    to hmiDisplayPhysicalSystem::centralComputer::planeComposition;

  /* ───────────── The path requirement, carried by the realization that places the paths ───────────── */

  dependency physicalSystemCarriesRendererSplitAndInputPaths
    from HmiDisplayPhysicalSystem to reqRendererSplitAndInputPaths;

  /* ───────────── System-to-software signal mappings (the method's phase 8 exit rule) ─────────────
   * One per crossing of an information item into a software contract, each
   * with its record. A mapping is no runtime-interoperability claim. The
   * owning allocation targets the port of the realizing element where the
   * item enters or leaves it, written as a feature chain through the usage.
   * One mapping covers the hops of a chain: the vehicle data publisher, a hop
   * that carries no logical element, is covered by the mapping at the
   * renderer's port.
   */

  allocation sceneIngressMapping : SystemToSoftwareSignalMappingCandidate
    allocate HmiDisplayLogicalSystem::sceneDrawer
    to hmiDisplayPhysicalSystem.hmiIVIGuest.sceneDrawingApp.sceneMessageIn {
    item <'MAP-HMI-SCENE'> sceneIngressMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The scene from the Data Tunnel topic of the SDV Core VM through the
       * SDV Gateway on the IVI VM into the scene drawing app. A scene is no
       * vehicle signal, except the distance to the object that the system acts
       * on, which COVESA VSS types at the port.
       */
      attribute :>> semanticSource = "the scene of one result pass of the candidate with the capture time of its camera image in simulation time: the output that the candidate does not give yet (gapHmiSceneOutput), no vehicle signal, except the distance to the object that the system acts on, which COVESA VSS types at the port as Vehicle_ADAS_ObstacleDetection_Distance (Vehicle.ADAS.ObstacleDetection.Distance, m)";
      attribute :>> softwareContractArtifact = "a Data Tunnel topic of the SDV Core VM that a context stand-in publishes, and the subscription of the scene drawing app to it through the SDV Gateway on the IVI VM, candidate";
      attribute :>> softwareContractMessage = "DisplaySceneMessage, one per result pass; a new message type, open until phase 10, candidate";
      attribute :>> softwareContractField = "the capture time, the lane points, the path, the objects with their levels, and the object that the system acts on with its distance and the speed of the closest object; not typed in this model yet";
      attribute :>> dataTypeAndUnit = "capture time in simulation seconds; distance in m; speed of the closest object in m/s, negative while it approaches";
      attribute :>> timingQualityAndState = "one scene per 0.1 s of simulation time; of the display's 0.1 s of wall-clock time, 0.05 s is for the hop from the SDV Core VM to the app and 0.05 s for the drawing, both unmeasured and revisited when a readiness probe measures them";
      attribute :>> transformationRule = "none on the path: the capture time reaches the app unchanged, and the app draws the scene as the candidate gives it";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "settle the scene's way out of the candidate and the message type, then bring the verification cases of REQ-HMI-001 and REQ-HMI-002 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; framing gap gapHmiSceneOutput";
    }
  }

  allocation drawnSceneHeartbeatMapping : SystemToSoftwareSignalMappingCandidate
    allocate HmiDisplayLogicalSystem::sceneDrawer
    to hmiDisplayPhysicalSystem.hmiIVIGuest.sceneDrawingApp.heartbeatOut {
    item <'MAP-HMI-DRAWN-SCENE-HEARTBEAT'> drawnSceneHeartbeatMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The heartbeat of each drawn frame from the scene drawing app in the
       * IVI VM to the renderer in the SDV Media VM: with the IVI plane, the
       * drawn scenes of phase 7. No vehicle signal.
       */
      attribute :>> semanticSource = "the time of the scene that the scene drawing app has drawn in a frame, sent with that frame in the place of the heartbeats of Android SDV's design: a liveness message, no vehicle signal";
      attribute :>> softwareContractArtifact = "the heartbeat by which the renderer learns that the app in the IVI VM is alive, extended with the time of the drawn scene, candidate";
      attribute :>> softwareContractMessage = "DrawnSceneHeartbeat, one per drawn frame, candidate";
      attribute :>> softwareContractField = "sceneCaptureTime, exact; the other fields of the heartbeat are not typed in this model yet";
      attribute :>> dataTypeAndUnit = "sceneCaptureTime in simulation seconds";
      attribute :>> timingQualityAndState = "one heartbeat per drawn frame; none while the app or Android in the IVI VM is out; the renderer judges the scene as drawn by the term current from the newest heartbeat";
      attribute :>> transformationRule = "sceneCaptureTime = the capture time of the scene that the frame shows, unchanged";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "settle the heartbeat's interface with the renderer, then bring the verification cases of REQ-HMI-006 and REQ-HMI-008 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; framing gap gapHmiRendererIntegration and gap gapHmiRendererJudgesSceneCurrency";
    }
  }

  allocation iviPlaneMapping : SystemToSoftwareSignalMappingCandidate
    allocate HmiDisplayLogicalSystem::sceneDrawer
    to hmiDisplayPhysicalSystem.hmiIVIGuest.sceneDrawingApp.iviPlaneOut {
    item <'MAP-HMI-IVI-PLANE'> iviPlaneMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The IVI plane, on which the scene drawing app draws the scene, into the
       * composition of the display under the renderer's plane: with the
       * heartbeats, the drawn scenes of phase 7. Pixels, no vehicle signal.
       */
      attribute :>> semanticSource = "the frames of the display of the IVI VM, on which the scene drawing app draws the scene in the scene area: pixels, no vehicle signal";
      attribute :>> softwareContractArtifact = "the display of the IVI VM as a plane of the one display, composed under the renderer's plane on the central computer, candidate";
      attribute :>> softwareContractMessage = "one frame of the IVI plane for each frame that the display of the IVI VM gives, candidate";
      attribute :>> softwareContractField = "the pixels of the scene area; the rest of the IVI plane lies under the renderer's own drawing";
      attribute :>> dataTypeAndUnit = "pixels; the size and the scale of the scene area are set with the app's drawing";
      attribute :>> timingQualityAndState = "a frame for each drawing of the app; none while the app or Android in the IVI VM is out, when the renderer covers the scene area";
      attribute :>> transformationRule = "none: the composition puts the renderer's plane over the IVI plane and adds nothing";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "show that the bench composes the two planes, then bring the verification cases of REQ-HMI-001 and REQ-HMI-006 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; framing gap gapHmiRendererIntegration (the drawing over the display of the IVI VM)";
    }
  }

  allocation displaySpeedMapping : SystemToSoftwareSignalMappingCandidate
    allocate HmiDisplayLogicalSystem::displayPresenter
    to hmiDisplayPhysicalSystem.hmiSDVMediaGuest.highAvailabilityRenderer.speedSampleIn {
    item <'MAP-HMI-VEHICLE-SPEED'> displaySpeedMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The vehicle speed from the vehicle data of the SDV Core VM through the
       * vehicle data publisher to the speed message of the renderer's vehicle
       * data. The owning allocation targets the typed port; its item
       * DisplayVehicleSpeedSample types the speed by COVESA VSS.
       */
      attribute :>> semanticSource = "the speed of the vehicle as vehicle data of the SDV Core VM, typed at the port by COVESA VSS Vehicle_Speed [km/h]; on the bench the simulator's speed of the ego vehicle stands in for it";
      attribute :>> softwareContractArtifact = "in: the vehicle data of the SDV Core VM, read by the vehicle data publisher, candidate; out: the speed message of the renderer's vehicle data (upstream.md), published over the platform's messaging between the VMs, candidate";
      attribute :>> softwareContractMessage = "DisplayVehicleSpeedSample, one per sample of the vehicle data; the renderer's speed message, candidate";
      attribute :>> softwareContractField = "speed, sampleTime, exact; the fields of the renderer's speed message as its vehicle data catalogue gives them";
      attribute :>> dataTypeAndUnit = "speed : Vehicle_Speed km/h; sampleTime in simulation seconds";
      attribute :>> timingQualityAndState = "one sample per sample of the vehicle data, on the bench one per world snapshot, every 0.05 s of simulation time; of the display's 0.1 s of wall-clock time, 0.05 s is for the hop from the SDV Core VM to the renderer and 0.05 s for the drawing, both unmeasured";
      attribute :>> transformationRule = "none on the path; the renderer shows the speed rounded to the whole km/h";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "build the feed of the speed into the SDV Core VM on the bench and the vehicle data publisher, then bring the verification cases of REQ-HMI-003 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; gap gapHmiBenchSpeedFeed and framing gap gapHmiRendererIntegration (the path from the SDV Core VM to the SDV Media VM)";
    }
  }

  allocation rendererWarningRequestMapping : SystemToSoftwareSignalMappingCandidate
    allocate HmiDisplayLogicalSystem::displayPresenter
    to hmiDisplayPhysicalSystem.hmiSDVMediaGuest.highAvailabilityRenderer.warningEventIn {
    item <'MAP-HMI-WARNING-REQUEST'> rendererWarningRequestMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The warning request from the Data Tunnel topic that the SOME/IP interop
       * of the SDV Core VM publishes, through the vehicle data publisher, to
       * the renderer's vehicle data. The item is the payload of the
       * driver-assistance increment, unchanged.
       */
      attribute :>> semanticSource = "the warning request of the candidate, typed at the port by Vehicle_ADAS_AEBS_DriverWarning_IsActive in the payload of the driver-assistance increment, WarningRequestEventPayload; the issue time is no vehicle signal";
      attribute :>> softwareContractArtifact = "in: the Data Tunnel topic of the warning request that the driver-assistance increment publishes in the SDV Core VM, candidate; out: a message of the renderer's vehicle data that its catalogue does not hold yet, published over the platform's messaging between the VMs, candidate";
      attribute :>> softwareContractMessage = "WarningRequestEventPayload, one event per plan, candidate";
      attribute :>> softwareContractField = "requested, issueTime, exact; the fields of the message in the renderer's vehicle data are not typed in this model yet";
      attribute :>> dataTypeAndUnit = "requested boolean; issueTime in simulation seconds";
      attribute :>> timingQualityAndState = "one event per plan, every 0.1 s of simulation time; a request starts with the first event that asks after one that does not. Of the display's 0.1 s of wall-clock time from the start of a request reaching the SDV Core VM to the start of each mode, 0.05 s is for the hop to the renderer and 0.05 s for the first frame with the warning and the start of the chime; both are unmeasured and revisited when a readiness probe measures them";
      attribute :>> transformationRule = "none on the path; the renderer draws the warning and gives the chime while the request asks, and the symbol that the warning is unavailable while the request is outdated";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "add the warning request, its symbols and the chime to the renderer, then bring the verification cases of REQ-HMI-004, REQ-HMI-005 and REQ-HMI-007 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; framing gap gapHmiRendererCollisionWarning";
    }
  }

  allocation sceneTimeMapping : SystemToSoftwareSignalMappingCandidate
    allocate HmiDisplayLogicalSystem::displayPresenter
    to hmiDisplayPhysicalSystem.hmiSDVMediaGuest.highAvailabilityRenderer.sceneTimeIn {
    item <'MAP-HMI-SCENE-TIME'> sceneTimeMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The time of each scene that reaches the display, from the Data Tunnel
       * topic of the scene in the SDV Core VM through the vehicle data
       * publisher to the renderer, which judges the currency of the scene from
       * it. No vehicle signal.
       */
      attribute :>> semanticSource = "the capture time in simulation time of the camera image of the result pass of each scene that reaches the display: a time, no vehicle signal";
      attribute :>> softwareContractArtifact = "in: the Data Tunnel topic of the scene in the SDV Core VM, candidate; out: a message of the renderer's vehicle data that its catalogue does not hold yet, published over the platform's messaging between the VMs, candidate";
      attribute :>> softwareContractMessage = "DisplaySceneTime, one per scene, candidate";
      attribute :>> softwareContractField = "captureTime, exact";
      attribute :>> dataTypeAndUnit = "captureTime in simulation seconds";
      attribute :>> timingQualityAndState = "one per scene, every 0.1 s of simulation time; 0.05 s of wall-clock time for the hop from the SDV Core VM to the renderer, unmeasured";
      attribute :>> transformationRule = "captureTime = the capture time of the scene, unchanged; the rest of the scene does not go to the renderer";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "add the time of the scene to the renderer's vehicle data, then bring the verification cases of REQ-HMI-006 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; gap gapHmiRendererJudgesSceneCurrency";
    }
  }

  allocation warningChimeMapping : SystemToSoftwareSignalMappingCandidate
    allocate HmiDisplayLogicalSystem::displayPresenter
    to hmiDisplayPhysicalSystem.hmiSDVMediaGuest.highAvailabilityRenderer.chimeOut {
    item <'MAP-HMI-WARNING-CHIME'> warningChimeMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The collision warning as a sound, from the renderer to the driver: a
       * chime of the renderer's chime configuration. A sound, no vehicle
       * signal.
       */
      attribute :>> semanticSource = "the collision warning as a sound: a chime, no vehicle signal";
      attribute :>> softwareContractArtifact = "a chime of the renderer's chime configuration, which holds no collision chime yet (upstream.md), and the sound output of the SDV Media VM, candidate";
      attribute :>> softwareContractMessage = "one chime for as long as the warning request asks, candidate";
      attribute :>> softwareContractField = "the sound file of the collision warning, which the display identity hashes";
      attribute :>> dataTypeAndUnit = "a sound; its design stays open";
      attribute :>> timingQualityAndState = "starts within the presentation time after the start of a request reaches the display: 0.05 s of wall-clock time for the hop and 0.05 s to the start of the chime, unmeasured";
      attribute :>> transformationRule = "the chime plays while the warning request asks and stops once it asks for none or is outdated";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "design and review the chime, then bring the verification cases of REQ-HMI-004 and REQ-HMI-005 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; framing gaps gapHmiRendererCollisionWarning and gapHmiRendererIntegration (the sound output and its capture)";
    }
  }

  allocation shownContentMapping : SystemToSoftwareSignalMappingCandidate
    allocate HmiDisplayLogicalSystem::displayPresenter
    to hmiDisplayPhysicalSystem.centralComputer.planeComposition.displayFrameOut {
    item <'MAP-HMI-SHOWN-CONTENT'> shownContentMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * What the HMI display shows: the frames of the one display, the
       * renderer's plane composed over the IVI plane. The looks of an outdated
       * element are those of this phase. Pixels, no vehicle signal.
       */
      attribute :>> semanticSource = "the frames of the one display: the renderer's plane, with the vehicle speed, the collision warning, the symbol that the warning is unavailable and the placeholder of the scene area, over the IVI plane with the drawn scene; pixels, no vehicle signal";
      attribute :>> softwareContractArtifact = "the composition of the display on the central computer, with the renderer's plane over the IVI plane, candidate";
      attribute :>> softwareContractMessage = "one frame of the display per composition, candidate";
      attribute :>> softwareContractField = "the scene area, the speed, the warning and the symbol that the warning is unavailable, each at a place that the renderer's design sets";
      attribute :>> dataTypeAndUnit = "pixels; the speed to the whole km/h";
      attribute :>> timingQualityAndState = "each change of what the display shows within the presentation time: 0.05 s of wall-clock time for the hop and 0.05 s for the drawing and the composition, unmeasured";
      attribute :>> transformationRule = "an outdated scene shows as the renderer's placeholder over the scene area; an outdated speed shows no number; an unavailable warning shows one fixed symbol; a current element shows as given";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "show that the bench composes the two planes and captures the display, then bring the verification cases of REQ-HMI-001, REQ-HMI-003, REQ-HMI-006 and REQ-HMI-007 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; framing gap gapHmiRendererIntegration";
    }
  }

  /* ───────────── What phase 8 settled on the framing's records ───────────── */

  comment phase8RendererIntegrationPlaced about gapHmiRendererIntegration
    /*
     * Placed, not observed: the vehicle data publisher in the SDV Core VM
     * gives the renderer the speed, the warning request and the time of each
     * scene over the platform's messaging between the VMs; the scene drawing
     * app in the IVI VM sends it a heartbeat with each drawn frame, which is
     * how it tells the renderer that Android is alive; the composition of the
     * display on the central computer puts the renderer's plane over the IVI
     * plane; and the renderer gives the chime. None of this has run on the
     * bench. Which transport carries the renderer's topics between the VMs,
     * whether the bench composes the two planes, which IVI image runs the app,
     * and how the sound is captured are readiness questions. One readiness
     * session follows this phase, at its cost and with the owner's go (owner
     * decision of 2026-11-25).
     */

  comment phase8RendererCollisionWarningPlaced about gapHmiRendererCollisionWarning
    /*
     * Placed, not closed: the vehicle data publisher gives the renderer each
     * event of the warning request, a message that the renderer's vehicle data
     * does not hold yet. The renderer learns that the warning is unavailable
     * from the age of those events (warningAvailabilityFixedInPhase5) and shows
     * one fixed symbol then. The symbol of the collision warning, that of the
     * unavailable warning and the chime stay to be designed and reviewed; they
     * are changes to the renderer's project.
     */

  comment phase8WarningPresentationSettled about gapHmiWarningPresentation
    /*
     * Settled for this realization (owner decision of 2026-11-25): in the
     * display's runs the IVI VM runs no other warning presentation, and the
     * warning presentation of the driver-assistance increment does not run
     * there. Its realization, its runs and its verdicts stay as they are. Of the
     * display's 0.1 s, 0.05 s is for the hop from the SDV Core VM to the
     * renderer or to the app and 0.05 s for the drawing and the start of the
     * sound. Both shares are unmeasured and revisited when a readiness probe
     * measures them (warningPresentationFixedInPhase5).
     */

  comment phase8SceneOutputHeld about gapHmiSceneOutput
    /*
     * Held open: this realization changes nothing in the candidate
     * (hmiCandidateChangeOutOfScope). A context stand-in publishes the scene as
     * a Data Tunnel topic in the SDV Core VM, where the scene reaches the
     * display; what stands in, and how, is decided with the scene's way out of
     * the candidate.
     */

  comment phase8MemberGuestLayoutUntouched about gapHmiMemberGuestLayout
    /*
     * Not settled here: the central computer of this realization runs three
     * VMs, which says nothing of the guest partition of a member product. That
     * layout is settled outside this increment.
     */

  comment phase8RendererReadinessOpen about asmHmiRendererWithoutGraphicsCard
    /*
     * Not yet shown: no readiness probe has measured the renderer drawing on
     * the guest host with the SDV Core, IVI and SDV Media VMs running on it
     * together. The probe runs after this phase, so that it tests the
     * realization placed here: the heartbeats, the composition and the
     * renderer's judging of the scene by the term current.
     */

  /* ───────────── The gaps of the realization ───────────── */

  part <'GAP-HMI-001'> gapHmiRendererJudgesSceneCurrency : IncrementGap {
    doc /*
     * The renderer has to judge the scene as drawn by the term current: from
     * the time of the scene in the newest heartbeat, against the newest time
     * of a value that has reached the display, and from when the newest
     * heartbeat came. Android SDV's design keeps the scene area transparent
     * while the heartbeats arrive (upstream.md), whatever scene the app has
     * drawn. The time in the heartbeat and in the renderer's vehicle data, and
     * the judging by the term current, are changes to the renderer's project.
     * How the renderer learns when the newest value of each input reached the
     * SDV Core VM, where the values reach the display, is open.
     */
  }

  part <'GAP-HMI-002'> gapHmiBenchSpeedFeed : IncrementGap {
    doc /*
     * On the bench the simulator stands in for the ECU that measures the
     * vehicle speed and for the vehicle network that carries it to the central
     * computer. No element of the bench feeds the simulator's speed into the
     * vehicle data of the SDV Core VM yet, and which element does is open.
     */
  }

  part <'GAP-HMI-003'> gapHmiDrawingToleranceUnset : IncrementGap {
    doc /*
     * REQ-HMI-001 reads a frame on the display against the scene within the
     * tolerance of a drawn position that phase 8 states with the drawing. The
     * scale of the scene area and the drawing of the scene drawing app are
     * not built, so the tolerance is not set. It is set with the app's drawing,
     * before phase 10.
     */
  }

  part <'GAP-HMI-004'> gapHmiIdentityMissesPhase8Elements : IncrementGap {
    doc /*
     * The display identity of the requirements names the builds of the
     * renderer and of the scene drawing app and the images of the IVI and SDV
     * Media VMs. Phase 8 places three more elements inside the display whose
     * builds it does not name: the vehicle data publisher in the SDV Core VM,
     * and the identity recording service and the composition on the central
     * computer. Nor does it name the image of the SDV Core VM, whose platform
     * carries the scene on to the IVI VM and the other inputs to the
     * publisher. A change to one of them records the same display identity, so
     * REQ-HMI-010 is not met as worded until the term names them, before phase
     * 10.
     */
  }

  /* ───────────── Concerns and views of the phase ───────────── */

  concern hmiDisplayPhysicalStructureConcern : PhysicalStructureConcern {
    doc /*
     * System architects and software developers need the software and platform
     * elements that realize the HMI display, as they nest: the central
     * computer with the identity recording service and the composition of the
     * display, the SDV Core VM with the vehicle data publisher, the IVI VM
     * with the scene drawing app and no other warning presentation, and the
     * SDV Media VM with the high availability renderer.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder softwareDeveloper : SoftwareDeveloper;
  }

  view hmiDisplayPhysicalStructureView {
    viewpoint selectedPhysicalStructureViewpoint : PhysicalStructureDefinitionViewpoint {
      frame hmiDisplayPhysicalStructureConcern;
    }
    expose hmiDisplayPhysicalSystem;
    expose hmiDisplayPhysicalSystem::centralComputer;
    expose hmiDisplayPhysicalSystem::centralComputer::os;
    expose hmiDisplayPhysicalSystem::centralComputer::hypervisor;
    expose hmiDisplayPhysicalSystem::centralComputer::identityRecordingService;
    expose hmiDisplayPhysicalSystem::centralComputer::planeComposition;
    expose hmiDisplayPhysicalSystem::hmiSDVCoreGuest;
    expose hmiDisplayPhysicalSystem::hmiSDVCoreGuest::os;
    expose hmiDisplayPhysicalSystem::hmiSDVCoreGuest::sdvMiddleware;
    expose hmiDisplayPhysicalSystem::hmiSDVCoreGuest::sdvCore;
    expose hmiDisplayPhysicalSystem::hmiSDVCoreGuest::vehicleDataPublisher;
    expose hmiDisplayPhysicalSystem::hmiIVIGuest;
    expose hmiDisplayPhysicalSystem::hmiIVIGuest::os;
    expose hmiDisplayPhysicalSystem::hmiIVIGuest::sdvGateway;
    expose hmiDisplayPhysicalSystem::hmiIVIGuest::sceneDrawingApp;
    expose hmiDisplayPhysicalSystem::hmiSDVMediaGuest;
    expose hmiDisplayPhysicalSystem::hmiSDVMediaGuest::os;
    expose hmiDisplayPhysicalSystem::hmiSDVMediaGuest::highAvailabilityRenderer;
    filter not (@ SysML::AllocationUsage);
    filter not (@ SysML::BindingConnectorAsUsage);
    render asTreeDiagram;
  }

  concern hmiDisplayPhysicalAllocationConcern : PhysicalLogicalMappingConcern {
    doc /*
     * System architects and verification engineers need each logical element
     * of phase 7 allocated to the software elements that carry it, and each
     * software element carrying one: the identity recording service, the
     * scene drawing app, and the high availability renderer and the
     * composition of the display, which carry the presenter together. An
     * allocation is a responsibility assignment, no deployment or runtime
     * claim.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder verificationEngineer : VerificationEngineer;
  }

  view hmiDisplayPhysicalLogicalMappingView : MVD::MatrixView {
    viewpoint selectedPhysicalLogicalMappingViewpoint : PhysicalLogicalMappingViewpoint {
      frame hmiDisplayPhysicalAllocationConcern;
      frame hmiRendererAllocationConcern;
    }
    view :>> rowView {
      expose HmiDisplayLogicalSystem::displayIdentityRecorder;
      expose HmiDisplayLogicalSystem::sceneDrawer;
      expose HmiDisplayLogicalSystem::displayPresenter;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> columnView {
      expose hmiDisplayPhysicalSystem::centralComputer::identityRecordingService;
      expose hmiDisplayPhysicalSystem::hmiIVIGuest::sceneDrawingApp;
      expose hmiDisplayPhysicalSystem::hmiSDVMediaGuest::highAvailabilityRenderer;
      expose hmiDisplayPhysicalSystem::centralComputer::planeComposition;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> cellView {
      expose DE4SDV_HmiDisplayPhysicalSoftwareRealization::*;
      attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;
    }
  }

  view hmiDisplayRendererPathView {
    doc /*
     * The paths of the inputs inside the display (hmiRendererPathConcern): the
     * scene from the SDV Core VM over the Data Tunnel and the SDV Gateway to
     * the scene drawing app in the IVI VM; the vehicle speed, the warning
     * request and the time of each scene from the vehicle data publisher in
     * the SDV Core VM to the high availability renderer in the SDV Media VM;
     * the heartbeat of each drawn frame from the app to the renderer, by which
     * the app tells the renderer that Android is alive; and the two planes
     * into the composition on the central computer. No other port leads to the
     * renderer, and nothing leads back. Each edge between the VMs and the
     * central computer is labelled with the ports at its ends, and each port
     * definition carries the one item that its exchange moves. The platform of
     * the SDV Core VM is listed by name only; where a path enters or leaves it,
     * its binds and connections are drawn as boxes that name their two ends.
     * The hypervisor interfaces are drawn in no view of this phase; the
     * structure tree shows the hypervisor and each VM's operating system.
     */
    viewpoint selectedPhysicalInternalExchangeViewpoint : PhysicalInternalExchangeViewpoint {
      frame hmiRendererPathConcern;
    }
    expose hmiDisplayPhysicalSystem;
    expose hmiDisplayPhysicalSystem::hmiSDVCoreGuest;
    expose hmiDisplayPhysicalSystem::hmiSDVCoreGuest::warningSomeIpIn;
    expose hmiDisplayPhysicalSystem::hmiSDVCoreGuest::speedSampleIn;
    expose hmiDisplayPhysicalSystem::hmiSDVCoreGuest::sceneMessageIn;
    expose hmiDisplayPhysicalSystem::hmiSDVCoreGuest::sceneMessageOut;
    expose hmiDisplayPhysicalSystem::hmiSDVCoreGuest::speedSampleOut;
    expose hmiDisplayPhysicalSystem::hmiSDVCoreGuest::warningEventOut;
    expose hmiDisplayPhysicalSystem::hmiSDVCoreGuest::sceneTimeOut;
    expose hmiDisplayPhysicalSystem::hmiSDVCoreGuest::vehicleDataPublisher;
    expose hmiDisplayPhysicalSystem::hmiSDVCoreGuest::vehicleDataPublisher::speedSampleIn;
    expose hmiDisplayPhysicalSystem::hmiSDVCoreGuest::vehicleDataPublisher::warningEventIn;
    expose hmiDisplayPhysicalSystem::hmiSDVCoreGuest::vehicleDataPublisher::sceneMessageIn;
    expose hmiDisplayPhysicalSystem::hmiSDVCoreGuest::vehicleDataPublisher::speedSampleOut;
    expose hmiDisplayPhysicalSystem::hmiSDVCoreGuest::vehicleDataPublisher::warningEventOut;
    expose hmiDisplayPhysicalSystem::hmiSDVCoreGuest::vehicleDataPublisher::sceneTimeOut;
    expose hmiDisplayPhysicalSystem::hmiIVIGuest;
    expose hmiDisplayPhysicalSystem::hmiIVIGuest::sceneMessageIn;
    expose hmiDisplayPhysicalSystem::hmiIVIGuest::heartbeatOut;
    expose hmiDisplayPhysicalSystem::hmiIVIGuest::iviPlaneOut;
    expose hmiDisplayPhysicalSystem::hmiIVIGuest::sdvGateway;
    expose hmiDisplayPhysicalSystem::hmiIVIGuest::sdvGateway::dataTunnelPort;
    expose hmiDisplayPhysicalSystem::hmiIVIGuest::sdvGateway::clientPort;
    expose hmiDisplayPhysicalSystem::hmiIVIGuest::sceneDrawingApp;
    expose hmiDisplayPhysicalSystem::hmiIVIGuest::sceneDrawingApp::sceneMessageIn;
    expose hmiDisplayPhysicalSystem::hmiIVIGuest::sceneDrawingApp::heartbeatOut;
    expose hmiDisplayPhysicalSystem::hmiIVIGuest::sceneDrawingApp::iviPlaneOut;
    expose hmiDisplayPhysicalSystem::hmiIVIGuest::sceneThroughSDVGateway;
    expose hmiDisplayPhysicalSystem::hmiSDVMediaGuest;
    expose hmiDisplayPhysicalSystem::hmiSDVMediaGuest::speedSampleIn;
    expose hmiDisplayPhysicalSystem::hmiSDVMediaGuest::warningEventIn;
    expose hmiDisplayPhysicalSystem::hmiSDVMediaGuest::sceneTimeIn;
    expose hmiDisplayPhysicalSystem::hmiSDVMediaGuest::heartbeatIn;
    expose hmiDisplayPhysicalSystem::hmiSDVMediaGuest::rendererPlaneOut;
    expose hmiDisplayPhysicalSystem::hmiSDVMediaGuest::chimeOut;
    expose hmiDisplayPhysicalSystem::hmiSDVMediaGuest::highAvailabilityRenderer;
    expose hmiDisplayPhysicalSystem::hmiSDVMediaGuest::highAvailabilityRenderer::speedSampleIn;
    expose hmiDisplayPhysicalSystem::hmiSDVMediaGuest::highAvailabilityRenderer::warningEventIn;
    expose hmiDisplayPhysicalSystem::hmiSDVMediaGuest::highAvailabilityRenderer::sceneTimeIn;
    expose hmiDisplayPhysicalSystem::hmiSDVMediaGuest::highAvailabilityRenderer::heartbeatIn;
    expose hmiDisplayPhysicalSystem::hmiSDVMediaGuest::highAvailabilityRenderer::rendererPlaneOut;
    expose hmiDisplayPhysicalSystem::hmiSDVMediaGuest::highAvailabilityRenderer::chimeOut;
    expose hmiDisplayPhysicalSystem::centralComputer;
    expose hmiDisplayPhysicalSystem::centralComputer::iviPlaneIn;
    expose hmiDisplayPhysicalSystem::centralComputer::rendererPlaneIn;
    expose hmiDisplayPhysicalSystem::centralComputer::displayFrameOut;
    expose hmiDisplayPhysicalSystem::centralComputer::planeComposition;
    expose hmiDisplayPhysicalSystem::centralComputer::planeComposition::iviPlaneIn;
    expose hmiDisplayPhysicalSystem::centralComputer::planeComposition::rendererPlaneIn;
    expose hmiDisplayPhysicalSystem::centralComputer::planeComposition::displayFrameOut;
    expose hmiDisplayPhysicalSystem::sceneTopicToIVIOverDataTunnel;
    expose hmiDisplayPhysicalSystem::speedToRendererAcrossVMs;
    expose hmiDisplayPhysicalSystem::warningToRendererAcrossVMs;
    expose hmiDisplayPhysicalSystem::sceneTimeToRendererAcrossVMs;
    expose hmiDisplayPhysicalSystem::drawnSceneHeartbeatToRenderer;
    expose hmiDisplayPhysicalSystem::iviPlaneToComposition;
    expose hmiDisplayPhysicalSystem::rendererPlaneToComposition;
    filter not (@ SysML::AllocationUsage);
    filter not (@ SysML::InterfaceUsage);
    attribute depth = -1;
    attribute showAnnotationRows = false;
    render asInterconnectionDiagram;
  }
}
