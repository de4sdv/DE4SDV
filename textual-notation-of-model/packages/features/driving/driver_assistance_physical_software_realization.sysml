/*
 * SPDX-License-Identifier: Apache-2.0
 *
 * INC-DRIVING-002, phase 8: the physical and software realization of the
 * candidate driver-assistance system. What software, hardware and
 * deployment elements realize the four logical elements of phase 7, and on
 * which technology do the driving command and the warning request travel,
 * which REQ-DRIVING-038 and REQ-DRIVING-043 constrain?
 *
 * On 2026-11-15 the owner chose that the candidate's process becomes an
 * Eclipse S-CORE application through a DE4SDV S-CORE interface module: an
 * S-CORE branch beside the existing interface selection in the application's
 * main function, before its loop (VisionPilot/app/vision_pilot.cpp:59-79 at
 * the pin), and one hand-off of the warnings that the planner already
 * computes, in the loop after vision_pilot.cpp:174; the decision logic under
 * VisionPilot/modules/ is unchanged. It is a small change with an upstream
 * path: upstream's own safety element description lists warning requests
 * among the outputs and calls the interface technology implementation
 * dependent (Functional_Safety/SAFETY_ELEMENT_OUT_OF_CONTEXT.md:95-104 at the
 * pin). The consequence is recorded with gapCandidateBehaviorUnverified:
 * every build on the S-CORE path carries this change, which upstream has not
 * merged, so every verdict names the build: 014e0e7a with the DE4SDV S-CORE
 * interface, and REQ-DRIVING-044's record carries the difference. Before
 * phase 10 builds, the VisionPilot maintainers are shown a draft of the
 * warning output and the interface seam; nothing is posted without the owner.
 *
 * On 2026-11-15 the owner also chose a GPU of its own for the S-CORE host, an
 * NVIDIA L4, for the candidate's networks, which run with the CUDA provider
 * that upstream's configuration sets (VisionPilot/config/vision_pilot.conf:11
 * at the pin): the GPU decision of 2026-11-15. The readiness probe of this
 * phase found the processor alone too slow for the 0.1 s cycle, so
 * asmProcessorInferenceSufficient does not hold
 * (phase8ProcessorInferenceNotHeld).
 *
 * On 2026-11-15 the owner also chose CARLA 1.0 on Unreal Engine 5.8 for the
 * bench's simulator, in place of CARLA 0.9.16 on Unreal Engine 4, and the build
 * that the readiness probe of this phase ran: commit
 * 14ac3b1a502da45a44506cb2ed82ab800f1baf4c of CARLA's branch ue58-dev, two
 * commits after the tag 1.0, from CARLA's weekly package of that day, of which
 * DE4SDV keeps a copy (upstream.md): the simulator decision of 2026-11-15. The
 * probe ran its server in synchronous mode with the fixed step of 0.1 s at
 * wall-clock pace on one NVIDIA L4, and its C++ client library inside an S-CORE
 * process; synchronous mode, the fixed step and the pacer of the clock decision
 * of 2026-11-08 stay.
 *
 * On 2026-11-17 the owner chose a fixed step of 0.05 s for the bench's
 * simulator, so that the bench's recording view can be rendered at 20 frames
 * per second: a camera renders at most once per step. The front camera keeps
 * one image per 0.1 s of simulation time, every second step, so the candidate
 * still receives images 0.1 s apart, the spacing that its fusion takes for two
 * processed frames. Synchronous mode and the world-side pacer of the clock
 * decision of 2026-11-08 stay, and the limits that were written in steps are
 * written in simulation time: the step decision of 2026-11-17.
 *
 * On 2026-11-17 the owner also chose an NVIDIA RTX PRO 6000 for the simulator
 * host. At the step of 0.05 s, with the front camera and a recording camera of
 * 1920 by 1080 pixels, one NVIDIA L4 did not keep wall-clock pace in the
 * readiness probe of 2026-11-16, and one NVIDIA RTX PRO 6000 did in the
 * readiness probe of 2026-11-17: the simulator host decision of 2026-11-17.
 *
 * On 2026-11-17 the owner also chose that the bench records the candidate's
 * own visualization with each run: upstream's drawing, at the pin, of what the
 * candidate perceives and plans over its camera image. It is not the driver's
 * display: it goes only into the bench's recording. A DE4SDV visualization
 * recorder in the candidate's process draws it on a thread of its own, from a
 * second hand-off in the loop after vision_pilot.cpp:174, and encodes it with
 * the video encoder of the S-CORE host's GPU: an observer of System 2 that
 * carries no logical element. The configuration keeps visualization_on = false,
 * so upstream's drawing in the loop stays off. That the candidate keeps its
 * timing with the recorder running is a readiness item of this phase
 * (phase8VisualizationRecorderPlaced): the visualization decision of
 * 2026-11-17. The draft shown to the VisionPilot maintainers includes this
 * hand-off.
 *
 * Carried over from the dated decisions of INC-DRIVING-001
 * (closed_loop_driving_physical_software_realization.sysml):
 *
 * - Clock, the clock decision of 2026-11-08: CARLA 0.9.16 in synchronous mode
 *   with a fixed step of 0.1 s, ticked by a world-side pacer at wall-clock
 *   pace. Simulation time is the time of the world snapshot, in seconds since
 *   the scenario started, one step of 0.1 s per frame; each camera image
 *   carries the simulation time of the snapshot it was rendered in. The issue
 *   time of a driving command and of a warning request is the capture
 *   simulation time of the frame it was computed from, so it and the newest
 *   world time that the actuation adapter compares it with are read on one
 *   clock; the 0.2 s share of REQ-DRIVING-042 is wall-clock time. Upstream's
 *   own simulator setup runs the simulator the same way
 *   (Simulation/CARLA/ROS2/src/carla_bridge_bringup/scripts/config_carla.py:192-240
 *   at the pin).
 * - Hosts, the three-host decision of 2026-11-09: the S-CORE host, the
 *   simulator host, and the guest host with KVM for the two AAOS SDV
 *   guests, with a VXLAN segment from the S-CORE host into the guests'
 *   bridge.
 *
 * What follows from the phase 7 elements and the defaults of this phase:
 *
 * - Topology: the candidate stays one process, VisionPilotSCOREApplication.
 *   Its upstream modules are physical elements at module level, the
 *   perception and fusion and the safety guardian's planner, and three
 *   modules of the DE4SDV S-CORE interface sit beside them in the process:
 *   the camera interface, the vehicle interface and the warning request
 *   publisher. The identity recorder is an S-CORE application of its own,
 *   started first, beside the software that gives the commands. The
 *   warning requester and the driving commander share the planner module:
 *   the forward-collision warning and the emergency braking are two ranges
 *   of one planned acceleration (planning.cpp:113-121).
 * - Warning path: the chain that INC-DRIVING-001 ran (mw::com, gatewayd,
 *   someipd, SOME/IP over the VXLAN segment, the SOME/IP interop of SDV
 *   Core, a Data Tunnel topic, the SDV Gateway on the IVI VM, the
 *   application), with a new message type for the warning request, open
 *   until phase 10. Of REQ-DRIVING-042's 0.2 s, 0.1 s is for the path and
 *   0.1 s for the presentation (MAP-DRIVING-DA-WARNING-REQUEST).
 * - Actuation: CARLA's Ackermann control, as upstream's own simulator path
 *   drives the vehicle, typed by the simulator's contract
 *   (SimulatorAckermannControl): the simulator receives the candidate's
 *   steering unchanged and the planned acceleration, as on that path. That
 *   the vehicle follows the commanded deceleration is ASM-DRIVING-005, and
 *   that the candidate's steering turns it toward its lane centre is
 *   ASM-DRIVING-006.
 * - VSS at the ports only: the command's acceleration and steering angle,
 *   the speed and the warning request; no new VSS extension.
 * - Revision: the bench runs VisionPilot at
 *   014e0e7a56ee8e597c2cab8175233f74edd9b856, upstream's main on
 *   2026-11-15; the tag v1.2 (9a96c3e7) is an older ancestor. The
 *   configuration is in VisionPilotSCOREApplication.
 *
 * Alternatives recorded and not selected:
 * - ALT-DRIVING-WARNFROMCOMMAND-001: no hand-off of the warnings; the
 *   publisher applies the ranges of planning.cpp:113-121 to the commanded
 *   acceleration. The candidate's code stays as it is for the warning, but
 *   the warning request is DE4SDV's, a copy of the candidate's rule.
 * - ALT-DRIVING-ROS2BRIDGE-001: the unchanged ROS 2 build with a DE4SDV
 *   bridge from ROS 2 to mw::com. A ROS 2 hop before S-CORE is a hop beside
 *   it under REQ-DRIVING-038, and the ROS 2 build gives no warning.
 *
 * The S-CORE path and the AAOS SDV are System 1 parts outside the
 * candidate (driver_assistance_operational_context.sysml): the actuation
 * adapter, the gateway processes, the guests and the warning presentation
 * are context realizations, and the simulator server stands for the
 * vehicle and the road environment (System 2). No logical element is
 * allocated to them. An allocation here is a responsibility assignment, no
 * deployment, execution or runtime claim; a signal mapping is no
 * interoperability claim; a pin is no build claim. Nothing in this package
 * claims a requirement met or a case run.
 */
package DE4SDV_DriverAssistancePhysicalSoftwareRealization {
  private import ScalarValues::*;
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_MethodProcess::SystemToSoftwareSignalMappingCandidate;
  private import DE4SDV_MethodProcess::LogicalToSoftwareSignalMappingRecord;
  private import DE4SDV_MethodProcess::SignalMappingDisposition;
  private import DE4SDV_TraceVocabulary::PhysicalAllocationElement;
  private import DE4SDV_SDVPlatformStack::LinuxPlatform;
  private import DE4SDV_SDVPlatformStack::EclipseSCORE;
  private import DE4SDV_SDVPlatformStack::AndroidHLOS;
  private import DE4SDV_SDVPlatformStack::AndroidSDVMiddleware;
  private import DE4SDV_SDVPlatformStack::OSHypervisorInterface;
  private import DE4SDV_AAOSSDVMiddlewareBoundary::SDVCoreBoundary;
  private import DE4SDV_AAOSSDVMiddlewareBoundary::SDVGatewayOnIVIBoundary;
  private import DE4SDV_AAOSSDVMiddlewareBoundary::DataTunnelPort;
  private import DE4SDV_ClosedLoopDrivingPhysicalSoftwareRealization::SimulationClockOut;
  private import DE4SDV_ClosedLoopDrivingPhysicalSoftwareRealization::SimulationClockIn;
  private import DE4SDV_ClosedLoopDrivingPhysicalSoftwareRealization::AAOSGuestHost;
  private import DE4SDV_DriverAssistanceFraming::DriverAssistanceSystem;
  private import DE4SDV_DriverAssistanceFraming::gapNoSeparateEmergencyFunction;
  private import DE4SDV_DriverAssistanceFraming::gapWarningOutput;
  private import DE4SDV_DriverAssistanceFraming::gapCandidateBehaviorUnverified;
  private import DE4SDV_DriverAssistanceFraming::gapScoreIntegration;
  private import DE4SDV_DriverAssistanceFraming::asmProcessorInferenceSufficient;
  private import DE4SDV_DriverAssistanceFraming::asmSimulatorPathUsable;
  private import DE4SDV_DriverAssistanceFraming::emergencyBrakingIndependenceConcern;
  private import DE4SDV_DriverAssistanceFraming::scoreCommandAndWarningPathConcern;
  private import DE4SDV_DriverAssistanceOperationalContext::FrontCameraImage;
  private import DE4SDV_DriverAssistanceOperationalContext::VehicleSpeed;
  private import DE4SDV_DriverAssistanceOperationalContext::DrivingCommand;
  private import DE4SDV_DriverAssistanceOperationalContext::WarningRequest;
  private import DE4SDV_DriverAssistanceOperationalContext::DriverWarningPresentation;
  private import DE4SDV_DriverAssistanceFunctionalArchitecture::VehicleAheadAssessment;
  private import DE4SDV_DriverAssistanceFunctionalArchitecture::CandidateIdentityRecord;
  private import DE4SDV_DriverAssistanceLogicalArchitecture::DriverAssistanceLogicalSystem;
  private import DE4SDV_DriverAssistanceNeedsRequirements::reqDrivingCommandOverSCORE;
  private import DE4SDV_DriverAssistanceNeedsRequirements::reqDetectableDrivingCommand;
  private import DE4SDV_DriverAssistanceNeedsRequirements::reqWarningRequestOverSCORE;
  private import COVESA_VSS::SignalDefinitions::Vehicle_Speed;
  private import DE4SDV_VSS_Extensions::Vehicle_ADAS_Driving_Command_Acceleration;
  private import DE4SDV_VSS_Extensions::Vehicle_ADAS_Driving_Command_SteeringAngle;
  private import DE4SDV_VSS_Extensions::Vehicle_ADAS_AEBS_DriverWarning_IsActive;
  private import DE4SDV_Stakeholders::*;
  private import SAF_Viewpoints::*;
  private import SysideViews::**;
  private import Views::*;

  /* ───────────── The items this phase types at the software contracts ───────────── */

  item def VehicleSpeedSamplePayload :> VehicleSpeed {
    doc /*
     * The speed of the vehicle as the realization types it where it enters
     * the candidate's process: the vehicle interface reads it from the
     * simulator's world snapshot through its client and hands it to the
     * planner in the process. The speed is typed by COVESA VSS at the port
     * (Vehicle_Speed, km/h); the sample time is the simulation time of the
     * snapshot (MAP-DRIVING-DA-VEHICLE-SPEED).
     */
    attribute speed : Vehicle_Speed;
    attribute sampleTime : Real;
  }

  item def DrivingCommandEventPayload :> DrivingCommand {
    doc /*
     * The driving command as the realization types it on the mw::com event
     * from the candidate's process to the actuation adapter, the first hop
     * of REQ-DRIVING-038. The acceleration and the steering angle are typed
     * by the two DE4SDV_VSS_Extensions candidates of INC-DRIVING-001. The
     * issue time, the sequence count and the check value are the parts by
     * which the actuation detects a loss, a delay, a repetition or a
     * corruption on the path (REQ-DRIVING-039): protocol fields, no vehicle
     * signal (MAP-DRIVING-DA-COMMAND).
     */
    attribute acceleration : Vehicle_ADAS_Driving_Command_Acceleration;
    attribute steeringAngle : Vehicle_ADAS_Driving_Command_SteeringAngle;
    attribute issueTime : Real;
    attribute sequenceCount : Natural;
    attribute checkValue : Natural;
  }

  item def WarningRequestEventPayload :> WarningRequest {
    doc /*
     * The warning request as the realization types it on the mw::com event
     * from the candidate's process, the first hop of REQ-DRIVING-043, and on
     * every later hop to the warning presentation. Whether it asks for the
     * collision warning is typed by the DE4SDV_VSS_Extensions candidate
     * Vehicle_ADAS_AEBS_DriverWarning_IsActive, since the candidate is
     * judged against the AEBS content of the product line; the issue time is
     * no vehicle signal (MAP-DRIVING-DA-WARNING-REQUEST).
     */
    attribute requested : Vehicle_ADAS_AEBS_DriverWarning_IsActive;
    attribute issueTime : Real;
  }

  item def PlannedWarnings {
    doc /*
     * The warnings of one plan of the candidate as the planner hands them to
     * the warning request publisher in the process: the list of the plan
     * (Plan in types.hpp:34-38 at the pin), whose values are FCW, AEB, LLDW
     * and RLDW of Warning (types.hpp:26-32). The publisher reads FCW and
     * AEB. A decision state of the candidate, no vehicle signal: phase 7's
     * warning state, whether the request has started and when, is formed
     * from it at the publisher (MAP-DRIVING-DA-PLANNED-WARNINGS).
     */
    attribute forwardCollisionWarning : Boolean;
    attribute emergencyBraking : Boolean;
  }

  item def SimulatorAckermannControl {
    doc /*
     * The information that crosses to the simulator, and the only thing that
     * does: the Ackermann control that the actuation adapter applies to the ego
     * vehicle through the simulator client, the five fields of
     * carla.VehicleAckermannControl in the Python API reference of CARLA 1.0,
     * the same as in CARLA 0.9.16 (five floats in the client library's
     * VehicleAckermannControl): steer, the desired steering angle in rad,
     * positive to the right; steerSpeed, the steering velocity in rad/s, where
     * zero changes the angle as quickly as possible; speed, the desired speed
     * in m/s; acceleration, the desired acceleration in m/s²; and jerk, the
     * desired jerk in m/s³; each defaults to 0.0. The adapter sets steer,
     * speed, acceleration and jerk, as upstream's own simulator path sets them
     * (carla_control_publisher_node.py:43-54 at the pin); steerSpeed stays at
     * its default of 0.0. The driving command ends at the adapter; this is what
     * the simulated vehicle receives.
     */
    attribute steer : Real;
    attribute steerSpeed : Real;
    attribute speed : Real;
    attribute acceleration : Real;
    attribute jerk : Real;
  }

  /* ───────────── Ports: one pair per item, whatever hop carries it ───────────── */

  port def FrontCameraStreamOut {
    doc /* The front-camera image leaving an element: from the simulator server to a client, or from the camera interface to the perception in the process. */
    out item frontCameraImage : FrontCameraImage;
  }
  port def FrontCameraStreamIn {
    doc /* The front-camera image entering an element: the camera interface's client, or the perception in the process. */
    in item frontCameraImage : FrontCameraImage;
  }
  port def VehicleSpeedSampleOut {
    doc /* The typed speed sample leaving an element: from the simulator server, or from the vehicle interface to the planner in the process. */
    out item vehicleSpeed : VehicleSpeedSamplePayload;
  }
  port def VehicleSpeedSampleIn {
    doc /* The typed speed sample entering an element: the vehicle interface's client, or the planner in the process. */
    in item vehicleSpeed : VehicleSpeedSamplePayload;
  }
  port def AssessmentResultOut {
    doc /* The assessment leaving the perception and fusion, in the process. */
    out item assessment : VehicleAheadAssessment;
  }
  port def AssessmentResultIn {
    doc /* The assessment entering the planner, in the process. */
    in item assessment : VehicleAheadAssessment;
  }
  port def PlannedCommandOut {
    doc /* The plan's acceleration and steering leaving the planner, in the process. */
    out item plannedCommand : DrivingCommand;
  }
  port def PlannedCommandIn {
    doc /* The plan's acceleration and steering entering the vehicle interface, in the process. */
    in item plannedCommand : DrivingCommand;
  }
  port def PlannedWarningsOut {
    doc /* The plan's warnings leaving the planner, in the process. */
    out item plannedWarnings : PlannedWarnings;
  }
  port def PlannedWarningsIn {
    doc /* The plan's warnings entering the warning request publisher, in the process. */
    in item plannedWarnings : PlannedWarnings;
  }
  port def DrivingCommandEventOut {
    doc /* The typed driving command on the mw::com event (REQ-DRIVING-038). */
    out item drivingCommand : DrivingCommandEventPayload;
  }
  port def DrivingCommandEventIn {
    doc /* The typed driving command from the mw::com event into the actuation adapter. */
    in item drivingCommand : DrivingCommandEventPayload;
  }
  port def WarningRequestEventOut {
    doc /* The typed warning request leaving an element on any hop of the warning path (REQ-DRIVING-043). */
    out item warningRequest : WarningRequestEventPayload;
  }
  port def WarningRequestEventIn {
    doc /* The typed warning request entering an element on any hop of the warning path. */
    in item warningRequest : WarningRequestEventPayload;
  }
  port def CandidateRecordEventOut {
    doc /* The candidate record on the mw::com event from the identity recording application (REQ-DRIVING-044). */
    out item candidateRecord : CandidateIdentityRecord;
  }
  port def CandidateRecordEventIn {
    doc /* The candidate record from the mw::com event into the candidate's vehicle interface. */
    in item candidateRecord : CandidateIdentityRecord;
  }
  port def AckermannControlOut {
    doc /* The Ackermann control the actuation adapter applies at the simulated actuation. */
    out item ackermannControl : SimulatorAckermannControl;
  }
  port def AckermannControlIn {
    doc /* The Ackermann control the simulator server applies to the ego vehicle. */
    in item ackermannControl : SimulatorAckermannControl;
  }

  /* ───────────── The software elements: one recording application, five modules of one process ───────────── */

  part def CandidateIdentityRecordingApplication :> PhysicalAllocationElement {
    doc /*
     * Carries the identity recorder of phase 7, beside the software that
     * gives the commands and not inside it: an S-CORE application of its own,
     * in C++, DE4SDV code, which the Launch Manager starts first. Before the
     * candidate's process starts, it records the candidate identity of the
     * run as the terms of the requirements define it: the upstream revision,
     * the difference between the built source and that revision, the SHA-256
     * of each configuration, calibration, manifest and network file that the
     * candidate's process reads (vision_pilot.conf, H.yaml, the DE4SDV
     * interface configuration, the mw::com manifest of the process and the
     * network files that the configuration selects) and the launch settings
     * verbatim, the working directory included, since the process reads
     * H.yaml from it. It publishes the record on an mw::com event; the
     * candidate's vehicle interface publishes no driving command before the
     * record has arrived (REQ-DRIVING-044).
     */
    port candidateRecordOut : CandidateRecordEventOut;
  }

  part def SCORECameraInterface :> PhysicalAllocationElement {
    doc /*
     * Carries the vehicle-ahead assessor of phase 7, together with the
     * perception and fusion: the camera input of the candidate's process, a
     * module of the DE4SDV S-CORE interface in C++ that implements the
     * candidate's camera interface. A client of the simulator, the C++ client
     * library of CARLA 1.0, receives the front-camera images over the bench
     * network, and the module hands the newest one to the loop as the frame
     * that vision_pilot.cpp:117 takes; it drops older images and counts each
     * image it drops, as upstream's own camera interface counts its dropped
     * frames. The frame goes to the loop without a time
     * (camera_interface.hpp:18): the module keeps its capture time, the
     * simulation time of the world snapshot the image was rendered in, and the
     * vehicle interface and the warning request publisher, modules of the same
     * interface, read it in the same pass of the loop. In a vehicle a camera
     * driver would stand here.
     */
    port frontCameraImageIn : FrontCameraStreamIn;
    port imageOut : FrontCameraStreamOut;
  }

  part def VisionPilotPerceptionAndFusion :> PhysicalAllocationElement {
    doc /*
     * Carries the vehicle-ahead assessor of phase 7: the upstream modules of
     * the candidate at the pin, unchanged, that turn the image into the
     * assessment. They are the image preprocessing, the three networks
     * AutoSpeed, AutoSteer and AutoDrive on ONNX Runtime with the CUDA
     * provider in fp32 on the S-CORE host's GPU (vision_pilot.cpp:96-98,
     * 138; onnx_engine.cpp:36-38, 63-76), and the longitudinal and lateral
     * fusion. They give the closest object in the path with its
     * distance and its velocity, negative while it approaches
     * (longitudinal_fusion.hpp:13-18), and the geometry of the lane. They compute no time to collision, no needed
     * deceleration and no imminence, so the assessment of phase 6 is
     * realized in part (MAP-DRIVING-DA-ASSESSMENT); phase 10 judges the
     * imminence from the simulator's ground truth. They read no vehicle
     * speed: the speed reaches the planner only.
     */
    port imageIn : FrontCameraStreamIn;
    port assessmentOut : AssessmentResultOut;
  }

  part def VisionPilotSafetyGuardianPlanner :> PhysicalAllocationElement {
    doc /*
     * Carries the warning requester and the driving commander of phase 7: the
     * planning module of the candidate's safety guardian at the pin,
     * unchanged. One call of its longitudinal planner gives the planned
     * acceleration (planning.cpp:51-52), and its lateral planner the
     * steering, a tyre angle in rad (planning.cpp:94-98). The
     * forward-collision warning and the emergency braking are two ranges of
     * that one planned acceleration: the warning from -5.0 to -3.0 m/s², the
     * emergency braking below -5.0 m/s² (planning.cpp:113-121). At the pin
     * there is no emergency function apart from this planner, so the warning
     * requester and the driving commander share it. The plan's warnings go to
     * the warning request publisher, which forms the warning request from
     * them; the exchange of phase 7 from the warning requester to the driving
     * commander, the warning state, has no realization in the candidate,
     * since one planned acceleration gives both the warning and the braking.
     * REQ-DRIVING-042 holds only if the planned acceleration reaches -3.0
     * m/s² at least 1.0 s of simulation time before it falls below -5.0 m/s²;
     * phase 10 judges it. The plan's acceleration and steering go to the
     * vehicle interface, its warnings to the warning request publisher, both
     * in the process.
     */
    port assessmentIn : AssessmentResultIn;
    port vehicleSpeedIn : VehicleSpeedSampleIn;
    port planOut : PlannedCommandOut;
    port plannedWarningsOut : PlannedWarningsOut;
  }

  part def SCOREVehicleInterface :> PhysicalAllocationElement {
    doc /*
     * Carries the driving commander of phase 7, together with the planner:
     * the command output of the candidate's process, a module of the DE4SDV
     * S-CORE interface in C++ that implements the candidate's vehicle
     * interface (vehicle_interface.hpp:11-14). Its read gives the speed of
     * the ego vehicle in m/s from the simulator's world snapshot through its
     * client. Its write takes the plan's steering and acceleration, adds the
     * issue time, the capture simulation time of the frame the command was
     * computed from, which the interface module keeps from the camera
     * interface for the pass, a sequence count from 1 in each run and a
     * CRC-32 check value over the other fields, and publishes the command on
     * an mw::com event: the first hop of REQ-DRIVING-038, on S-CORE
     * communication and nothing beside it. It publishes no driving command
     * before the candidate record has arrived on its mw::com subscription
     * (REQ-DRIVING-044). The candidate's planner is not changed for any of
     * this.
     */
    port vehicleSpeedIn : VehicleSpeedSampleIn;
    port vehicleSpeedOut : VehicleSpeedSampleOut;
    port planIn : PlannedCommandIn;
    port candidateRecordIn : CandidateRecordEventIn;
    port drivingCommandOut : DrivingCommandEventOut;
  }

  part def SCOREWarningRequestPublisher :> PhysicalAllocationElement {
    doc /*
     * Carries the warning requester of phase 7, together with the planner:
     * the warning output of the candidate's process, a module of the DE4SDV
     * S-CORE interface in C++, the realization of its own that phase 7 asked
     * for (gapWarningOutput). It takes the warnings of each plan through the
     * one hand-off added in the loop after vision_pilot.cpp:174 and publishes
     * the warning request on an mw::com event, the first hop of
     * REQ-DRIVING-043: requested is true while the plan holds a
     * forward-collision warning or an emergency braking, and the issue time
     * is the capture simulation time of the frame the plan was computed from,
     * which the interface module keeps from the camera interface for the
     * pass. The candidate's decision logic is not changed.
     */
    port plannedWarningsIn : PlannedWarningsIn;
    port warningRequestOut : WarningRequestEventOut;
  }

  part def VisionPilotSCOREApplication {
    doc /*
     * The candidate's process as an Eclipse S-CORE application: one Linux
     * process, VisionPilot at 014e0e7a56ee8e597c2cab8175233f74edd9b856 built
     * with the DE4SDV S-CORE interface module and without ROS 2, started and
     * supervised by the Launch Manager of S-CORE Lifecycle. Its main function
     * takes the S-CORE branch beside the existing interface selection before
     * the loop (vision_pilot.cpp:59-79), and its loop hands the plan's
     * warnings to the warning request publisher after the write at
     * vision_pilot.cpp:174. The process links mw::com, the simulator's C++
     * client library, ONNX Runtime with its CUDA provider, OpenCV and the
     * Rerun SDK, a readiness item. It runs its five modules in the order of
     * the loop, once per frame: the camera interface, the perception and
     * fusion, the planner, then the vehicle interface and the warning
     * request publisher. Inside
     * the process the image, the assessment, the speed, the plan and the
     * warnings are hand-offs, and the interface module passes the capture
     * time of the frame from the camera interface to the vehicle interface
     * and the warning request publisher: no hops between processes; across
     * processes it speaks mw::com only. Beside the loop, on a thread of its
     * own, runs the DE4SDV visualization recorder of the visualization decision
     * of 2026-11-17, an observer of System 2: a second hand-off after the write
     * at vision_pilot.cpp:174 gives it a copy of the pass's image, inference
     * result, plan and speed. From the copy it draws upstream's visualization
     * at the pin, the drawing that visualization_on = true would do in the loop
     * (vision_pilot.cpp:176-181, visual_interface.hpp:77-82), and it encodes
     * each drawn image with the video encoder of the host's GPU into the
     * bench's recording. The loop never waits for it: a hand-off that finds it
     * busy replaces the copy that waits and is counted. It is no module of the
     * loop, carries no logical element and sends nothing to any element of the
     * candidate or of the path. Its configuration: engine.provider = cuda, as
     * upstream's configuration sets it (vision_pilot.conf:11), model.precision
     * = fp32, visualization_on = false, rrd_on = true for the evaluators'
     * record of the warnings, and speed_limit set per scenario by System 2.
     */
    port frontCameraImageIn : FrontCameraStreamIn;
    port vehicleSpeedIn : VehicleSpeedSampleIn;
    port candidateRecordIn : CandidateRecordEventIn;
    port drivingCommandOut : DrivingCommandEventOut;
    port warningRequestOut : WarningRequestEventOut;

    part cameraInterface : SCORECameraInterface;
    part perceptionAndFusion : VisionPilotPerceptionAndFusion;
    part safetyGuardianPlanner : VisionPilotSafetyGuardianPlanner;
    part vehicleInterface : SCOREVehicleInterface;
    part warningRequestPublisher : SCOREWarningRequestPublisher;

    bind frontCameraImageIn = cameraInterface.frontCameraImageIn;
    bind vehicleSpeedIn = vehicleInterface.vehicleSpeedIn;
    bind candidateRecordIn = vehicleInterface.candidateRecordIn;
    bind drivingCommandOut = vehicleInterface.drivingCommandOut;
    bind warningRequestOut = warningRequestPublisher.warningRequestOut;
    connection imageHandOff connect cameraInterface.imageOut to perceptionAndFusion.imageIn;
    connection assessmentHandOff connect perceptionAndFusion.assessmentOut to safetyGuardianPlanner.assessmentIn;
    connection vehicleSpeedHandOff connect vehicleInterface.vehicleSpeedOut to safetyGuardianPlanner.vehicleSpeedIn;
    connection plannedCommandHandOff connect safetyGuardianPlanner.planOut to vehicleInterface.planIn;
    connection plannedWarningsHandOff connect safetyGuardianPlanner.plannedWarningsOut to warningRequestPublisher.plannedWarningsIn;
  }

  part def DriverAssistanceSoftwareRealization :> DriverAssistanceSystem {
    doc /*
     * The driver-assistance system as phase 8 realizes it: the same system
     * as the context's candidateSystem, now two programs on the S-CORE host,
     * the identity recording application and the candidate's process. The
     * boundary of phase 0 stays where it was: the S-CORE path and the AAOS
     * SDV are outside it, so the actuation adapter and the gateway processes
     * sit on the host beside the realization, not in it. Its ports are the
     * boundary items as the software types them: the front-camera image and
     * the vehicle speed in, the driving command and the warning request out,
     * each of the two outputs on the mw::com event that is the first hop of
     * REQ-DRIVING-038 or REQ-DRIVING-043. Between its two programs the
     * candidate record travels on an mw::com event. The application-middleware
     * adapter of the platform stack is the DE4SDV S-CORE interface module;
     * phase 9 derives it.
     */
    port frontCameraImageIn : FrontCameraStreamIn;
    port vehicleSpeedIn : VehicleSpeedSampleIn;
    port drivingCommandOut : DrivingCommandEventOut;
    port warningRequestOut : WarningRequestEventOut;

    part identityRecording : CandidateIdentityRecordingApplication;
    part visionPilotApplication : VisionPilotSCOREApplication;

    bind frontCameraImageIn = visionPilotApplication.frontCameraImageIn;
    bind vehicleSpeedIn = visionPilotApplication.vehicleSpeedIn;
    bind drivingCommandOut = visionPilotApplication.drivingCommandOut;
    bind warningRequestOut = visionPilotApplication.warningRequestOut;
    connection candidateRecordOverSCORECommunication connect identityRecording.candidateRecordOut to visionPilotApplication.candidateRecordIn;
  }

  /* ───────────── The context realizations on the bench ───────────── */

  part def DrivingCommandActuationAdapter {
    doc /*
     * The actuation end of the S-CORE path on the bench, a context
     * realization: an S-CORE application of its own, in C++, DE4SDV code,
     * with a client of the simulator over the bench network. It carries no
     * logical element; it is a share of the S-CORE path, which is outside the
     * candidate. It subscribes to the driving command event and rejects a
     * command whose sequence count is not one more than that of the last
     * accepted command (a loss or a repetition), whose check value fails (a
     * corruption), or whose issue time is older than the newest world time by
     * more than 0.1 s of simulation time (a delay): the share of the product
     * that holds the path (REQ-MW-006). The issue time and the newest world
     * time are simulation times of world snapshots, on one clock. It applies
     * nothing in place of a rejected command: the simulator keeps the last
     * valid control. It has no stop response of its own. REQ-DRIVING-038's
     * success criterion runs SC-DRIVING-012 with the S-CORE path stopped and
     * requires that no driving command reaches the actuation after the stop;
     * a stop or a neutral control applied by the adapter would blur that run,
     * no requirement of this increment asks for a stop response, and the
     * share of REQ-MW-006 placed here is not applying the rejected command.
     * An accepted command becomes the simulator's Ackermann control by the
     * rule of MAP-DRIVING-DA-COMMAND. Its simulator client takes the
     * simulation time and the speed of the ego vehicle from the newest world
     * snapshot: the delay check needs the time, the speed rule of
     * MAP-DRIVING-DA-COMMAND the speed. The autopilot of the ego vehicle
     * stays off.
     */
    port drivingCommandIn : DrivingCommandEventIn;
    port simulationClockIn : SimulationClockIn;
    port vehicleSpeedIn : VehicleSpeedSampleIn;
    port ackermannControlOut : AckermannControlOut;
  }

  part def DriverAssistanceSimulationServer {
    doc /*
     * The simulator server, System 2: CARLA 1.0 on Unreal Engine 5.8, at
     * 14ac3b1a50 (the simulator decision of 2026-11-15), which renders the
     * front camera of the ego vehicle and simulates its dynamics, the road and
     * the targets, so it stands for the vehicle and the road environment of the
     * phase 2 context on the bench. It runs in synchronous mode with a fixed
     * step of 0.05 s (the step decision of 2026-11-17), and a world-side pacer
     * of the bench's scenario tooling ticks it at wall-clock pace, so no
     * element of the candidate or of the path ticks the world (the clock
     * decision of 2026-11-08). Simulation time is the time of the world
     * snapshot, in seconds since the scenario started; each camera image
     * carries the simulation time of the snapshot it was rendered in. Three
     * clients connect to it over the bench network: the camera interface and
     * the vehicle interface of the candidate's process, and the actuation
     * adapter. The autopilot and the traffic manager have no control of the ego
     * vehicle. Its one sensor is the front camera of the rig below; the camera
     * of the bench's recording view stands for no sensor of the vehicle.
     */
    port frontCameraStreamOut : FrontCameraStreamOut;
    port vehicleSpeedOut : VehicleSpeedSampleOut;
    port simulationClockOut : SimulationClockOut;
    port ackermannControlIn : AckermannControlIn;

    part cameraRig : FrontCameraRig;
  }

  part def FrontCameraRig {
    doc /*
     * The bench's sensor, System 2: one front camera attached to the simulated
     * ego vehicle, standing for the vehicle's front camera of the phase 2
     * context. It renders one image per 0.1 s of simulation time, every second
     * step of the server (the step decision of 2026-11-17). Upstream's own rig
     * at the pin is one RGB camera of 1920 by 1280 pixels with a field of view
     * of 50 degrees, at the pose that
     * Simulation/CARLA/ROS2/config/carla916.json:5-15 gives. It sits on
     * vehicle.lincoln.mkz_2020 (carla916.json:2), which CARLA 1.0 does not
     * have, so the bench mounts the camera on another vehicle. The candidate
     * estimates distances through the homography of H.yaml, which has to match
     * the simulated camera (gapCameraImageAndGeometry). The speed comes from
     * the world snapshot, ground truth, not from a sensor. No connection,
     * binding or port inside: the server's ports carry the stream.
     */
    part frontCamera : SimulatedFrontCamera;
  }

  part def SimulatedFrontCamera {
    doc /*
     * The rendered front camera: an image of the scene at the rig's size,
     * field of view and pose, stamped with the simulation time of its frame.
     * Rendered, not captured: no exposure, no motion blur and no lens
     * distortion beyond what the simulator models.
     */
  }

  part def DriverAssistanceSDVCoreGuest {
    doc /*
     * The SDV Core VM of the AAOS SDV, context of the candidate: Android
     * under the guest host's KVM, with the SDV Core middleware. The SOME/IP
     * interop of SDV Core receives the warning request from someipd, and the
     * Data Tunnel publishes it as a typed topic that the IVI VM subscribes
     * to. The message type of the warning request is new and stays open
     * until phase 10, like the operational-state message of INC-DRIVING-001.
     * The SDV Core boundary model of packages/architecture is referenced and
     * bound to the middleware layer; nothing of it is built by DE4SDV.
     */
    port someIpIn : WarningRequestEventIn;
    port topicOut : DataTunnelPort;
    part os : AndroidHLOS;
    part sdvMiddleware : AndroidSDVMiddleware;
    ref part sdvCore : SDVCoreBoundary;
    bind sdvCore = sdvMiddleware;
    bind someIpIn = sdvCore.someIp.someIpPort;
    connection warningRequestTopicPublishedByBroker connect sdvCore.someIp.topicPublishOut to sdvCore.dataTunnel.topicPublishPort;
    bind topicOut = sdvCore.dataTunnel.topicSubscribePort;
  }

  part def CollisionWarningPresentationApplication :> DriverWarningPresentation {
    doc /*
     * The warning presentation of phase 2 on the IVI VM, a build item of the
     * bench, named here, not claimed: an Android application that subscribes
     * to the warning-request topic through the SDV Gateway and, when a
     * request starts, shows the collision warning on the display and starts
     * a warning sound. It sends nothing to the candidate. Of the 0.2 s of
     * wall-clock time that REQ-DRIVING-042 allots from the request to each
     * mode of the warning, 0.1 s is the path's, from the publisher's send to
     * the receipt by this application, and 0.1 s is this application's, from
     * the receipt to the first displayed frame with the warning and to the
     * start of the sound. It logs the receipt, the displayed frame and the
     * start of the sound with their times for phase 10. It is not the
     * informational visualization of the AEBS visualization increment.
     */
    port warningRequestIn : WarningRequestEventIn;
  }

  part def DriverAssistanceIVIGuest {
    doc /*
     * The IVI VM of the AAOS SDV, context of the candidate: Android under the
     * guest host's KVM, with the SDV Gateway and the warning presentation,
     * which gives the driver the collision warning on the display and as a
     * sound. The presentation subscribes to the typed topic through the SDV
     * Gateway and sends nothing to the driver-assistance system.
     */
    port topicIn : DataTunnelPort;
    part os : AndroidHLOS;
    part sdvGateway : SDVGatewayOnIVIBoundary;
    part warningPresentation : CollisionWarningPresentationApplication;
    bind topicIn = sdvGateway.dataTunnelPort;
    connection warningRequestThroughSDVGateway connect sdvGateway.clientPort to warningPresentation.warningRequestIn;
  }

  part def DriverAssistanceSCOREHost {
    doc /*
     * The S-CORE host of the bench (the three-host decision of 2026-11-09,
     * carried over): x86_64 Linux with a GPU of its own, an NVIDIA L4, for
     * the candidate's networks (the GPU decision of 2026-11-15). It owns its
     * platform layer, the software realization of the candidate and, beside
     * it, the share of the S-CORE path on the host: the actuation adapter
     * and the S-CORE services. The camera stream and the speed
     * arrive from the simulator host over the bench network for the
     * candidate's process, the simulation clock and the speed for the
     * actuation adapter, and the Ackermann control leaves for the simulator
     * host; the warning request leaves on SOME/IP over the VXLAN segment into
     * the guests' bridge, where the host takes 192.168.98.1 as in
     * INC-DRIVING-001. The host's ports are bound to the ports of the
     * elements that own the exchanges, as the realization of INC-DRIVING-001
     * binds its own; the S-CORE path view draws the binds as edges between
     * exposed ports.
     */
    port frontCameraImageIn : FrontCameraStreamIn;
    port vehicleSpeedIn : VehicleSpeedSampleIn;
    port simulationClockIn : SimulationClockIn;
    port adapterVehicleSpeedIn : VehicleSpeedSampleIn;
    port ackermannControlOut : AckermannControlOut;
    port warningRequestOut : WarningRequestEventOut;
    part os : LinuxPlatform;
    part assistanceSoftware : DriverAssistanceSoftwareRealization;
    part actuationAdapter : DrivingCommandActuationAdapter;
    part scoreServices : EclipseSCORE {
      doc /*
       * The S-CORE services of the host, one instance, a share of the S-CORE
       * path outside the candidate: Lifecycle's Launch Manager starts the
       * identity recording application first, then the candidate's process
       * and the actuation adapter, and supervises them; the SOME/IP gateway
       * of INC-MW-011 (gatewayd and someipd at d9eac670) carries the warning
       * request out of the host. They carry no logical element.
       */
      part launchManager {
        doc /*
         * The Launch Manager of S-CORE Lifecycle v0.10.0: starts the identity
         * recording application before the candidate's process, so that the
         * candidate record exists before the first driving command, and
         * supervises the three programs. Stopping the candidate's process or
         * the actuation adapter through it stops the S-CORE path of the
         * candidate for the further run of REQ-DRIVING-038.
         */
      }
      part gatewayd {
        doc /*
         * The gatewayd process of the S-CORE SOME/IP gateway: subscribes to
         * the warning-request event on mw::com and hands it to someipd over
         * the gateway's IPC. A process of the pinned gateway, not DE4SDV
         * code, and incubation code outside both baselines.
         */
        port warningRequestIn : WarningRequestEventIn;
        port warningRequestOut : WarningRequestEventOut;
      }
      part someipd {
        doc /*
         * The someipd process of the S-CORE SOME/IP gateway: offers the
         * warning-request service on SOME/IP and sends each event over the
         * VXLAN segment to the SOME/IP interop of SDV Core. A process of the
         * pinned gateway, not DE4SDV code.
         */
        port warningRequestIn : WarningRequestEventIn;
        port warningRequestOut : WarningRequestEventOut;
      }
    }
    bind frontCameraImageIn = assistanceSoftware.frontCameraImageIn;
    bind vehicleSpeedIn = assistanceSoftware.vehicleSpeedIn;
    bind simulationClockIn = actuationAdapter.simulationClockIn;
    bind adapterVehicleSpeedIn = actuationAdapter.vehicleSpeedIn;
    bind ackermannControlOut = actuationAdapter.ackermannControlOut;
    bind warningRequestOut = scoreServices.someipd.warningRequestOut;
    connection drivingCommandOverSCORECommunication connect assistanceSoftware.drivingCommandOut to actuationAdapter.drivingCommandIn;
    connection warningRequestOverSCORECommunication connect assistanceSoftware.warningRequestOut to scoreServices.gatewayd.warningRequestIn;
    connection warningRequestOverGatewayIPC connect scoreServices.gatewayd.warningRequestOut to scoreServices.someipd.warningRequestIn;
  }

  part def DriverAssistanceSimulatorHost {
    doc /*
     * The simulator host of the bench (the three-host decision of
     * 2026-11-09, carried over): x86_64 Linux with its own GPU for the
     * simulator's rendering, an NVIDIA RTX PRO 6000 (the simulator host
     * decision of 2026-11-17). It owns its platform layer and the simulator
     * server. The camera stream, the speed and the simulation clock leave
     * it, and the Ackermann control enters it, over the bench network to and
     * from the S-CORE host.
     */
    port frontCameraStreamOut : FrontCameraStreamOut;
    port vehicleSpeedOut : VehicleSpeedSampleOut;
    port simulationClockOut : SimulationClockOut;
    port ackermannControlIn : AckermannControlIn;
    part os : LinuxPlatform;
    part carlaServer : DriverAssistanceSimulationServer;
    connection frontCameraStreamDelegation connect carlaServer.frontCameraStreamOut to frontCameraStreamOut;
    connection vehicleSpeedDelegation connect carlaServer.vehicleSpeedOut to vehicleSpeedOut;
    connection simulationClockDelegation connect carlaServer.simulationClockOut to simulationClockOut;
    connection ackermannControlDelegation connect ackermannControlIn to carlaServer.ackermannControlIn;
  }

  part def DriverAssistancePhysicalSystem {
    doc /*
     * The physical context of the bench: three hosts and the two AAOS SDV
     * guests. The guest host is INC-DRIVING-001's definition, reused: Linux
     * with KVM and no element of the driver-assistance system. The
     * simulator's exchanges cross the bench network between the simulator
     * host and the S-CORE host, and into the simulator goes the Ackermann
     * control and nothing else. The warning request crosses the VXLAN
     * segment once on SOME/IP, from someipd to the SDV Core VM, and the VMs
     * once on the Data Tunnel, from the SDV Core VM to the IVI VM. Nothing
     * crosses back. The S-CORE host's inside is drawn by the S-CORE path
     * view.
     */
    part scoreHost : DriverAssistanceSCOREHost;
    part simulatorHost : DriverAssistanceSimulatorHost;
    part guestHost : AAOSGuestHost;
    part sdvCoreGuest : DriverAssistanceSDVCoreGuest;
    part iviGuest : DriverAssistanceIVIGuest;
    interface sdvCoreGuestUnderKVM : OSHypervisorInterface
      connect sdvCoreGuest.os.hypervisorPort to guestHost.hypervisor.guestPort;
    interface iviGuestUnderKVM : OSHypervisorInterface
      connect iviGuest.os.hypervisorPort to guestHost.hypervisor.guestPort;
    connection frontCameraStreamOverBenchNetwork connect simulatorHost.frontCameraStreamOut to scoreHost.frontCameraImageIn {
      doc /* The front-camera images from the simulator host to the camera interface of the candidate's process, over the bench network. */
    }
    connection vehicleSpeedOverBenchNetwork connect simulatorHost.vehicleSpeedOut to scoreHost.vehicleSpeedIn {
      doc /* The speed of the ego vehicle from the simulator host to the vehicle interface of the candidate's process, over the bench network. */
    }
    connection vehicleSpeedToActuationOverBenchNetwork connect simulatorHost.vehicleSpeedOut to scoreHost.adapterVehicleSpeedIn {
      doc /* The speed of the ego vehicle from the simulator host to the actuation adapter, over the bench network, for the speed rule of MAP-DRIVING-DA-COMMAND. */
    }
    connection simulationClockOverBenchNetwork connect simulatorHost.simulationClockOut to scoreHost.simulationClockIn {
      doc /* The world snapshot's simulation time from the simulator host to the actuation adapter, over the bench network. */
    }
    connection ackermannControlOverBenchNetwork connect scoreHost.ackermannControlOut to simulatorHost.ackermannControlIn {
      doc /* The Ackermann control from the actuation adapter to the simulator host, over the bench network, and nothing else. */
    }
    connection warningRequestOverSOMEIPAcrossVXLANSegment connect scoreHost.warningRequestOut to sdvCoreGuest.someIpIn {
      doc /* The warning request on SOME/IP from someipd to the SDV Core VM's interop, over the VXLAN segment that joins the S-CORE host to the guests' bridge (guest images unchanged). */
    }
    connection warningRequestTopicOverDataTunnelAcrossVMs connect sdvCoreGuest.topicOut to iviGuest.topicIn {
      doc /* The warning request as the Data Tunnel topic from the SDV Core VM to the IVI VM; its message type stays open until phase 10. */
    }
  }

  part driverAssistancePhysicalSystem : DriverAssistancePhysicalSystem;

  part driverAssistanceSCOREHost : DriverAssistanceSCOREHost {
    doc /*
     * Exists for the S-CORE path view, which draws usages: the same host as
     * the physical system's scoreHost, not a second one. Drawn from the
     * system's usage, the view would also draw the system's connections to
     * the host's ports as boxes with two ends.
     */
  }

  /* ───────────── Logical-to-physical allocations (allocatedTo) ───────────── */

  allocation recorderToIdentityRecording allocate DriverAssistanceLogicalSystem::identityRecorder to driverAssistancePhysicalSystem::scoreHost::assistanceSoftware::identityRecording;
  allocation assessorToCameraInterface allocate DriverAssistanceLogicalSystem::vehicleAheadAssessor to driverAssistancePhysicalSystem::scoreHost::assistanceSoftware::visionPilotApplication::cameraInterface;
  allocation assessorToPerceptionAndFusion allocate DriverAssistanceLogicalSystem::vehicleAheadAssessor to driverAssistancePhysicalSystem::scoreHost::assistanceSoftware::visionPilotApplication::perceptionAndFusion;
  allocation requesterToSafetyGuardianPlanner allocate DriverAssistanceLogicalSystem::warningRequester to driverAssistancePhysicalSystem::scoreHost::assistanceSoftware::visionPilotApplication::safetyGuardianPlanner;
  allocation requesterToWarningRequestPublisher allocate DriverAssistanceLogicalSystem::warningRequester to driverAssistancePhysicalSystem::scoreHost::assistanceSoftware::visionPilotApplication::warningRequestPublisher;
  allocation commanderToSafetyGuardianPlanner allocate DriverAssistanceLogicalSystem::drivingCommander to driverAssistancePhysicalSystem::scoreHost::assistanceSoftware::visionPilotApplication::safetyGuardianPlanner;
  allocation commanderToVehicleInterface allocate DriverAssistanceLogicalSystem::drivingCommander to driverAssistancePhysicalSystem::scoreHost::assistanceSoftware::visionPilotApplication::vehicleInterface;

  /* ───────────── The path requirements, carried by the elements that publish on the path ───────────── */

  dependency drivingCommandPublisherCarriesCommandOverSCORE from SCOREVehicleInterface to reqDrivingCommandOverSCORE;
  dependency warningRequestPublisherCarriesWarningOverSCORE from SCOREWarningRequestPublisher to reqWarningRequestOverSCORE;

  /* ───────────── System-to-software signal mappings (the method's phase 8 exit rule) ─────────────
   * One per crossing of an information item into a software contract, each
   * with its record. A mapping is no runtime-interoperability claim. The
   * owning allocation targets the port where the item enters the contract,
   * written as a feature chain through the usage (the ports are declared on
   * the definitions, so a qualified name would resolve to the definition's
   * port, outside the realizing usage).
   */

  allocation cameraImageIngressMapping : SystemToSoftwareSignalMappingCandidate
    allocate DriverAssistanceLogicalSystem::vehicleAheadAssessor
    to driverAssistancePhysicalSystem.scoreHost.assistanceSoftware.visionPilotApplication.cameraInterface.frontCameraImageIn {
    item <'MAP-DRIVING-DA-CAMERA-IMAGE'> cameraImageIngressMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The front-camera image from the simulator's camera into the camera
       * interface of the candidate's process: the ingress of the candidate
       * through the simulator client. An image is no vehicle signal.
       */
      attribute :>> semanticSource = "the front-camera image of the ego vehicle, rendered by the simulator: image frames, no vehicle signal, so no VSS typing applies; the receiving contract is the candidate's camera interface at 014e0e7a";
      attribute :>> softwareContractArtifact = "in: the camera sensor stream of the simulator client library of CARLA 1.0, an RGB camera as in upstream's rig (Simulation/CARLA/ROS2/config/carla916.json:5-15), candidate; out: the frame that the candidate's loop takes (vision_pilot.cpp:117), candidate";
      attribute :>> softwareContractMessage = "in: one RGB image per 0.1 s of simulation time, every second simulation step (the step decision of 2026-11-17), with its frame number and simulation time, candidate; out: one image per pass of the loop, candidate";
      attribute :>> softwareContractField = "in: raw image buffer, width, height, field of view, frame number and simulation time, exact per the client library; out: the image to the loop, candidate, and its capture time to the vehicle interface and the warning request publisher inside the interface module, candidate";
      attribute :>> dataTypeAndUnit = "in: 8-bit BGRA pixels, 1920 by 1280 at a field of view of 50 degrees in upstream's rig; out: 8-bit BGR pixels; the capture time in simulation seconds";
      attribute :>> timingQualityAndState = "one image per 0.1 s of simulation time; the camera interface hands on the newest image, drops older ones and counts each image it drops; the candidate's fusion takes two processed frames as 0.1 s apart, its nominal step, since no step is passed to it (longitudinal_fusion.hpp:40, inference.cpp:206-207), so every run reports the images dropped, and phase 10 judges no run whose judged window holds a dropped image; the capture time is the simulation time of the world snapshot the image was rendered in";
      attribute :>> transformationRule = "BGRA to BGR, no resampling; the camera calibration is no part of the item: the candidate reads the homography from H.yaml in its working directory (vision_pilot.cpp:114), which has to match the simulated camera";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "check that H.yaml matches the simulated camera, then bring the verification cases of REQ-DRIVING-036, -040 and -041 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; framing gap gapCameraImageAndGeometry";
    }
  }

  allocation vehicleSpeedIngressMapping : SystemToSoftwareSignalMappingCandidate
    allocate DriverAssistanceLogicalSystem::drivingCommander
    to driverAssistancePhysicalSystem.scoreHost.assistanceSoftware.visionPilotApplication.vehicleInterface.vehicleSpeedIn {
    item <'MAP-DRIVING-DA-VEHICLE-SPEED'> vehicleSpeedIngressMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The speed of the ego vehicle from the simulator's world snapshot into
       * the vehicle interface of the candidate's process, which hands it to
       * the planner. The owning allocation targets the typed port; its item
       * VehicleSpeedSamplePayload types the speed by COVESA VSS.
       */
      attribute :>> semanticSource = "the speed of the ego vehicle from the simulator's world snapshot, typed at the port by COVESA VSS Vehicle_Speed [km/h]";
      attribute :>> softwareContractArtifact = "in: the velocity of the ego vehicle in the world snapshot of the simulator client library of CARLA 1.0, candidate; out: the value that the candidate's vehicle interface read returns to the loop (vehicle_interface.hpp:11, vision_pilot.cpp:142), candidate";
      attribute :>> softwareContractMessage = "in: the velocity vector per world snapshot, candidate; out: VehicleSpeedSamplePayload, one per pass of the loop, candidate";
      attribute :>> softwareContractField = "in: velocity x, y and z and the frame of the snapshot, exact per the client library; out: speed, sampleTime, exact";
      attribute :>> dataTypeAndUnit = "in: float m/s; at the port: speed : Vehicle_Speed km/h and sampleTime in simulation seconds; the candidate's planner takes m/s";
      attribute :>> timingQualityAndState = "read once per pass of the loop that has an inference result, after the inference (vision_pilot.cpp:142); the sample time is the simulation time of the snapshot";
      attribute :>> transformationRule = "speed = |velocity| * 3.6 as the VSS km/h value, and the planner takes speed / 3.6 in m/s; the speed reaches the planner only, not the perception: phase 7 delegates the speed to the vehicle-ahead assessor too, but the candidate's perception reads none (vision_pilot.cpp:138, 142)";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "bring the verification cases of REQ-DRIVING-036 and -037 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; framing assumption asmSimulatedConfigurationStandsIn (the speed is the simulator's ground truth)";
    }
  }

  allocation vehicleAheadAssessmentMapping : SystemToSoftwareSignalMappingCandidate
    allocate DriverAssistanceLogicalSystem::vehicleAheadAssessor
    to driverAssistancePhysicalSystem.scoreHost.assistanceSoftware.visionPilotApplication.perceptionAndFusion.assessmentOut {
    item <'MAP-DRIVING-DA-ASSESSMENT'> vehicleAheadAssessmentMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The assessment from the candidate's perception and fusion to its
       * planner, a hand-off in the process. It realizes the assessment of
       * phase 6 in part. An estimate, no vehicle signal.
       */
      attribute :>> semanticSource = "the assessment of the vehicle ahead as the candidate computes it: the closest object in the path with its distance and its velocity, and the geometry of the lane; an estimate, no vehicle signal";
      attribute :>> softwareContractArtifact = "in-process: the inference result of the candidate's pipeline at 014e0e7a, the estimate of the closest object of longitudinal_fusion.hpp:13-18 and the lateral estimate, handed to the planner in the same pass of the loop (vision_pilot.cpp:138-158), candidate";
      attribute :>> softwareContractMessage = "one inference result per frame for which the pipeline gives a result, candidate";
      attribute :>> softwareContractField = "cipo valid, distance_m and velocity_ms; lateral cte_m, yaw_rad and curvature, exact per the pinned source";
      attribute :>> dataTypeAndUnit = "float metres, m/s with negative values while approaching, rad and 1/m";
      attribute :>> timingQualityAndState = "computed from each frame for which the pipeline gives a result; a pass without a result plans nothing";
      attribute :>> transformationRule = "none in the process; the candidate computes no time to collision, no needed deceleration and no imminence, so the assessment of phase 6 is realized in part, and phase 10 judges the imminence from the simulator's ground truth";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "bring the verification cases of REQ-DRIVING-040 and -041 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; framing gap gapCameraImageAndGeometry (the distance estimate)";
    }
  }

  allocation plannedWarningsMapping : SystemToSoftwareSignalMappingCandidate
    allocate DriverAssistanceLogicalSystem::warningRequester
    to driverAssistancePhysicalSystem.scoreHost.assistanceSoftware.visionPilotApplication.safetyGuardianPlanner.plannedWarningsOut {
    item <'MAP-DRIVING-DA-PLANNED-WARNINGS'> plannedWarningsMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The warnings of the candidate's plan from the planner to the warning
       * request publisher, a hand-off in the process, typed by
       * PlannedWarnings. A decision state, no vehicle signal; the publisher
       * forms the warning request from it.
       */
      attribute :>> semanticSource = "the warnings of the candidate's plan, a forward-collision warning or an emergency braking from the one planned acceleration: a decision state, no vehicle signal";
      attribute :>> softwareContractArtifact = "in-process: the warnings of the plan (Plan in types.hpp:34-38, Warning in types.hpp:26-32), handed to the warning request publisher in the loop after vision_pilot.cpp:174, candidate";
      attribute :>> softwareContractMessage = "PlannedWarnings, one per plan, candidate";
      attribute :>> softwareContractField = "warnings: FCW, AEB, LLDW and RLDW, exact per the pinned source; the publisher reads FCW and AEB";
      attribute :>> dataTypeAndUnit = "an enumeration, no unit";
      attribute :>> timingQualityAndState = "one list per plan, in the same pass of the loop as the driving command";
      attribute :>> transformationRule = "FCW for a planned acceleration from -5.0 to -3.0 m/s², AEB below -5.0 m/s² (planning.cpp:113-121); the planner is not changed";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "bring the verification cases of REQ-DRIVING-040 and -042 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; framing gaps gapNoSeparateEmergencyFunction and gapWarningOutput";
    }
  }

  allocation plannedCommandMapping : SystemToSoftwareSignalMappingCandidate
    allocate DriverAssistanceLogicalSystem::drivingCommander
    to driverAssistancePhysicalSystem.scoreHost.assistanceSoftware.visionPilotApplication.safetyGuardianPlanner.planOut {
    item <'MAP-DRIVING-DA-PLAN'> plannedCommandMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The acceleration and the steering of the candidate's plan from the
       * planner to the vehicle interface, a hand-off in the process. A plan,
       * no vehicle signal; the VSS typing starts at the command event.
       */
      attribute :>> semanticSource = "the planned acceleration and steering of the candidate's plan: a plan, no vehicle signal; the VSS typing starts at the command event (MAP-DRIVING-DA-COMMAND)";
      attribute :>> softwareContractArtifact = "in-process: the acceleration and the steering of the plan (Plan in types.hpp:34-38) that the loop writes to the vehicle interface at vision_pilot.cpp:174, candidate";
      attribute :>> softwareContractMessage = "one plan per frame for which the pipeline gives a result, candidate";
      attribute :>> softwareContractField = "acceleration and steering[1], exact per the pinned source";
      attribute :>> dataTypeAndUnit = "acceleration float m/s², negative decelerates; steering a tyre angle in rad, taken in the sign of CARLA's steer, positive to the right, as upstream's own simulator path takes it (ASM-DRIVING-006)";
      attribute :>> timingQualityAndState = "one plan per pass of the loop that has an inference result, from the frame of that pass";
      attribute :>> transformationRule = "identity; the steering written is the second sample of the lateral plan, steering[1]";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "bring the verification cases of REQ-DRIVING-036, -037 and -041 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; framing gap gapNoSeparateEmergencyFunction";
    }
  }

  allocation drivingCommandMapping : SystemToSoftwareSignalMappingCandidate
    allocate DriverAssistanceLogicalSystem::drivingCommander
    to driverAssistancePhysicalSystem.scoreHost.assistanceSoftware.visionPilotApplication.vehicleInterface.drivingCommandOut {
    item <'MAP-DRIVING-DA-COMMAND'> drivingCommandMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The driving command from the candidate's vehicle interface to the
       * actuation adapter on the mw::com event: the first hop of
       * REQ-DRIVING-038. The owning allocation targets the typed port; its
       * item DrivingCommandEventPayload types the acceleration and the
       * steering angle by the two DE4SDV_VSS_Extensions candidates.
       */
      attribute :>> semanticSource = "the driving command of the candidate, typed at the port by Vehicle_ADAS_Driving_Command_Acceleration [m/s^2] and Vehicle_ADAS_Driving_Command_SteeringAngle [degrees], two DE4SDV candidates absent from the pinned VSS snapshot; the issue time, the sequence count and the check value are protocol fields, no vehicle signal";
      attribute :>> softwareContractArtifact = "out: the mw::com driving-command event from the candidate's process to the actuation adapter, candidate; S-CORE communication and nothing beside it (REQ-DRIVING-038)";
      attribute :>> softwareContractMessage = "out: DrivingCommandEventPayload, one event per command, candidate";
      attribute :>> softwareContractField = "out: acceleration, steeringAngle, issueTime, sequenceCount, checkValue, exact";
      attribute :>> dataTypeAndUnit = "out: acceleration float m/s^2, negative decelerates; steeringAngle float degrees, positive to the left; issueTime in simulation seconds; sequenceCount an unsigned 32-bit count from 1 in each run; checkValue the CRC-32 over the other fields";
      attribute :>> timingQualityAndState = "one command per plan; none before the candidate record has arrived (REQ-DRIVING-044); the issue time is the capture simulation time of the frame the command was computed from";
      attribute :>> transformationRule = "acceleration unchanged; steeringAngle = -steering[1] * 180 / pi: the integration takes the candidate's steering in the sign of CARLA's steer, positive to the right, as upstream's own simulator path does, which gives the steering to CARLA's steer without a change (vehicle_ros2_interface.cpp:67, carla_control_publisher_node.py:49), and the VSS steering angle is positive to the left (ASM-DRIVING-006). At the actuation adapter, for CARLA's Ackermann control, whose steer is positive to the right (the Python API references of CARLA 1.0 and of CARLA 0.9.16, which upstream's path runs): steer = -steeringAngle * pi / 180 in rad, so the simulator receives the candidate's steering unchanged, as on upstream's path; speed = max(0, v + 2 * acceleration) with v the speed of the ego vehicle in the newest world snapshot, acceleration unchanged and jerk = 10.0, as upstream's own simulator path sets them (carla_control_publisher_node.py:44-53); steerSpeed stays at its default of 0.0. The adapter rejects a command whose sequence count is not one more than that of the last accepted, whose check value fails or whose issue time is older than the newest world time by more than 0.1 s of simulation time, and applies nothing in its place (REQ-DRIVING-039, REQ-MW-006)";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "run the calibrations of ASM-DRIVING-005 and ASM-DRIVING-006, then bring the verification cases of REQ-DRIVING-036, -038, -039 and -044 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; ASM-DRIVING-005 (the simulated vehicle follows the commanded deceleration) and ASM-DRIVING-006 (the candidate's steering turns the vehicle toward its lane centre)";
    }
  }

  allocation warningRequestMapping : SystemToSoftwareSignalMappingCandidate
    allocate DriverAssistanceLogicalSystem::warningRequester
    to driverAssistancePhysicalSystem.scoreHost.assistanceSoftware.visionPilotApplication.warningRequestPublisher.warningRequestOut {
    item <'MAP-DRIVING-DA-WARNING-REQUEST'> warningRequestMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The warning request on the warning path, hop by hop: the publisher's
       * mw::com event, gatewayd to someipd over the gateway's IPC, SOME/IP
       * over the VXLAN segment into the SOME/IP interop of SDV Core, the Data
       * Tunnel topic to the SDV Gateway on the IVI VM, the warning
       * presentation. One mapping covers the processes of the chain; the
       * owning allocation targets the publisher's port, where the item
       * enters the S-CORE contract: the first hop of REQ-DRIVING-043.
       */
      attribute :>> semanticSource = "the warning request of the candidate, typed at the port by Vehicle_ADAS_AEBS_DriverWarning_IsActive, the DE4SDV candidate for an AEBS that requests or presents a driver collision warning; the issue time is no vehicle signal";
      attribute :>> softwareContractArtifact = "out: the mw::com warning-request event from the candidate's process; gatewayd and someipd of the SOME/IP gateway at d9eac670; SOME/IP over the VXLAN segment into the SOME/IP interop of SDV Core; a Data Tunnel topic to the SDV Gateway on the IVI VM and the warning presentation. The event, the SOME/IP service and the topic are new, candidate; on the Eclipse S-CORE path and nothing beside it (REQ-DRIVING-043)";
      attribute :>> softwareContractMessage = "WarningRequestEventPayload, one event per plan; on the guest a new typed message for the warning request, open until phase 10, candidate";
      attribute :>> softwareContractField = "requested, issueTime, exact; the fields of the message on the guest are not typed in this model yet";
      attribute :>> dataTypeAndUnit = "requested boolean; issueTime in simulation seconds";
      attribute :>> timingQualityAndState = "one event per plan; a request starts with the first event that is true after one that is false. Of the 0.2 s of wall-clock time that REQ-DRIVING-042 allots from the request to each mode of the warning, 0.1 s is for the path, from the publisher's send to the receipt by the warning presentation on the IVI VM, and 0.1 s is for the presentation, from the receipt to the first displayed frame with the warning and to the start of the sound. Basis: the latency of the same chain was measured in a readiness probe of INC-DRIVING-001; the start of the sound on the guest is unmeasured, and the split is revisited when it is measured";
      attribute :>> transformationRule = "requested = the plan's warnings hold FCW or AEB; issueTime = the capture simulation time of the frame the plan was computed from; serialization to the new message at the SOME/IP interop of SDV Core; no value changes on the path";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "type the message on the guest, then bring the verification cases of REQ-DRIVING-040, -042 and -043 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; framing assumption asmBenchReuse (whether the reused path carries the warning in time)";
    }
  }

  allocation candidateRecordMapping : SystemToSoftwareSignalMappingCandidate
    allocate DriverAssistanceLogicalSystem::identityRecorder
    to driverAssistancePhysicalSystem.scoreHost.assistanceSoftware.identityRecording.candidateRecordOut {
    item <'MAP-DRIVING-DA-CANDIDATE-RECORD'> candidateRecordMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The candidate record from the identity recording application to the
       * candidate's vehicle interface on an mw::com event, and the record
       * file the evaluators keep. A record of files and settings, no vehicle
       * signal.
       */
      attribute :>> semanticSource = "the candidate identity of the run as the terms of the requirements define it: a record of files and settings, no vehicle signal";
      attribute :>> softwareContractArtifact = "out: the mw::com candidate-record event from the identity recording application to the candidate's vehicle interface, and the record file the evaluators keep, candidate";
      attribute :>> softwareContractMessage = "one record per run, published before the candidate's process starts, candidate";
      attribute :>> softwareContractField = "the upstream revision, the source difference, the SHA-256 of each configuration, calibration, manifest and network file that the candidate's process reads (vision_pilot.conf, H.yaml, the DE4SDV interface configuration, the mw::com manifest and the network files) and the launch settings with the working directory, candidate";
      attribute :>> dataTypeAndUnit = "strings; each SHA-256 in hexadecimal";
      attribute :>> timingQualityAndState = "once per run, before the candidate's process starts; the vehicle interface publishes no driving command before the record has arrived (REQ-DRIVING-044); the record has to reach the vehicle interface, which subscribes after it was published; how mw::com delivers it is a readiness item (phase8ScoreIntegrationPlaced)";
      attribute :>> transformationRule = "the difference is that of the built source against 014e0e7a56ee8e597c2cab8175233f74edd9b856: every build on the S-CORE path carries the DE4SDV S-CORE interface, so the difference is never empty (gapCandidateBehaviorUnverified)";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "bring the verification cases of REQ-DRIVING-044 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; framing gap gapCandidateBehaviorUnverified";
    }
  }

  /* ───────────── What phase 8 settled on the framing's records ───────────── */

  comment phase8WarningOutputPlaced about gapWarningOutput
    /*
     * Placed, not closed: the warning request leaves the candidate through
     * one hand-off of the warnings that its planner already computes, added
     * in the main loop after vision_pilot.cpp:174, to the warning request
     * publisher, which publishes it on an mw::com event
     * (MAP-DRIVING-DA-WARNING-REQUEST). The decision logic under
     * VisionPilot/modules/ is not changed. The hand-off is a change that
     * upstream has not merged (gapCandidateBehaviorUnverified). The data log
     * stays on for the evaluators' record of the warnings (rrd_on = true); it
     * is no warning request.
     */

  comment phase8ScoreIntegrationPlaced about gapScoreIntegration
    /*
     * Placement decided, readiness items open: the candidate's process becomes
     * an Eclipse S-CORE application through the DE4SDV S-CORE interface module
     * (the owner's choice of 2026-11-15), started and supervised by the Launch
     * Manager. Its driving command and its warning request enter the S-CORE
     * path on mw::com events at the boundary of the process, with no hop beside
     * S-CORE before them; its state enters no path, since no requirement asks
     * for it. The readiness probe of 2026-11-15 built one process with the
     * S-CORE toolchain that links mw::com, the simulator's C++ client library,
     * ONNX Runtime, OpenCV and the Rerun SDK, and ran it: one network, one
     * frame conversion, one data log, mw::com events to a second process, and
     * the simulator's client connected to the server. It then built the same
     * process with the C++ client library of CARLA 1.0, which needs C++20: only
     * the unit that calls the library was compiled as C++20, the rest of the
     * process as C++17. Run against a CARLA 1.0 server, it gave the same
     * network, data log and mw::com events, every front-camera image at the
     * rig's size, and an Ackermann control that moved the ego vehicle. Its ONNX
     * Runtime was the prebuilt build for the processor, which loads a second
     * C++ standard library into the process beside the binary's own. Open
     * before phase 10: the link with the build of ONNX Runtime for CUDA that
     * the GPU decision of 2026-11-15 needs; whether the process may hold a
     * second C++ standard library or builds ONNX Runtime with the S-CORE
     * toolchain; and that the candidate record reaches the vehicle interface,
     * which subscribes after the record was published: the probe did not test
     * it.
     */

  comment phase8ProcessorInferenceNotHeld about asmProcessorInferenceSufficient
    /*
     * Does not hold, by the readiness probe of this phase on 2026-11-15: on a
     * host with eight vCPUs and the CPU provider, the candidate took longer
     * than the 0.1 s cycle for every image measured, most of it in its three
     * networks in fp32, so its loop left most images unprocessed. With the
     * CUDA provider on an NVIDIA L4 that it shared with the simulator, the
     * candidate's ROS 2 build gave a command for every step of the simulator
     * in the minute measured. The owner then chose a GPU of the S-CORE host
     * for the networks (the GPU decision of 2026-11-15), so the bench
     * topology rests on that GPU, not on the processor. Whether the S-CORE
     * host's own GPU keeps the cycle with the S-CORE build is not shown yet:
     * every run reports the images dropped, and phase 10 judges no run whose
     * judged window holds one (MAP-DRIVING-DA-CAMERA-IMAGE).
     */

  comment phase8SimulatorPathHeld about asmSimulatorPathUsable
    /*
     * Holds, by the readiness probe of this phase on 2026-11-15: upstream's
     * simulator path at the pin, CARLA 0.9.16 with its ROS 2 interface and
     * upstream's two bridge nodes, ran in synchronous mode with a fixed step of
     * 0.1 s, and with the CUDA provider the candidate's ROS 2 build gave a
     * command for every step in the minute measured, with no change to its
     * source. The S-CORE path of this realization takes the commands from the
     * same loop through the DE4SDV S-CORE interface module instead of ROS 2.
     * The simulator of this realization is CARLA 1.0 (the simulator decision of
     * 2026-11-15): the probe ran its server in synchronous mode with the fixed
     * step of 0.1 s at wall-clock pace, with the bench's front camera and a
     * recording camera, on one NVIDIA L4, and drove its ego vehicle from a
     * client inside an S-CORE process (phase8ScoreIntegrationPlaced). At the
     * step of 0.05 s of the step decision of 2026-11-17, with the front camera
     * and a recording camera of 1920 by 1080 pixels, the same server did not
     * keep wall-clock pace on one NVIDIA L4 in the readiness probe of
     * 2026-11-16 and kept it on one NVIDIA RTX PRO 6000 in the readiness probe
     * of 2026-11-17 (the simulator host decision of 2026-11-17). The candidate
     * itself has not yet driven on CARLA 1.0: its passes in the probe ran on
     * CARLA 0.9.16.
     */

  comment phase8EmergencyFunctionAnswered about gapNoSeparateEmergencyFunction
    /*
     * Answered for the realization, not closed: at the pin there is no
     * emergency function apart from the planner, so the warning requester and
     * the driving commander are both allocated to the planner module
     * (VisionPilotSafetyGuardianPlanner), and the emergency braking leaves in
     * the one driving command. The independence of a protected emergency
     * command path is not realized by the candidate. The exchange of phase 7
     * from the warning requester to the driving commander, the warning state,
     * has no realization in the candidate: the warning and the braking come
     * from the one planned acceleration. The share recorded is
     * REQ-DRIVING-039's detectable command and the actuation adapter's
     * rejection of what it detects (reqDetectableDrivingCommandRejection).
     * Whether the candidate's braking can stand for the common capability
     * stays with the member decision after the evidence of phase 10.
     */

  comment phase8CandidateBuildCarriesTheSCOREInterface about gapCandidateBehaviorUnverified
    /*
     * What the owner's choice of 2026-11-15 means for this gap: every build
     * on the S-CORE path carries the DE4SDV S-CORE interface module and the
     * hand-off of the warnings, a change that upstream has not merged, so
     * every build is such a different candidate. Every verdict names the
     * build, 014e0e7a with the DE4SDV S-CORE interface, and the record of
     * REQ-DRIVING-044 carries the difference (MAP-DRIVING-DA-CANDIDATE-RECORD).
     */

  comment phase8VisualizationRecorderPlaced about gapCandidateBehaviorUnverified
    /*
     * What the visualization decision of 2026-11-17 means for this gap: every
     * build on the S-CORE path also carries the DE4SDV visualization recorder
     * and its hand-off after vision_pilot.cpp:174, a change that upstream has
     * not merged. The record of REQ-DRIVING-044 carries it in the difference,
     * and every verdict names the build as 014e0e7a with the DE4SDV S-CORE
     * interface and the visualization recorder. The recorder only observes: it
     * takes copies after the command is written, and it gives nothing back to
     * the loop, to the candidate's inputs or to its outputs. Readiness item,
     * open until the readiness probe of this phase has run: that the candidate
     * keeps its timing with the recorder running, the time from an image to its
     * command and the images dropped, measured with the recorder on and off in
     * one build on an NVIDIA L4.
     */

  comment reqDetectableDrivingCommandRejection about reqDetectableDrivingCommand, DrivingCommandActuationAdapter
    /*
     * Where the parts of REQ-DRIVING-039 sit, and where the rejection sits:
     * the vehicle interface of the candidate's process adds to each command
     * its issue time, a sequence count from 1 in each run and a CRC-32 check
     * value (MAP-DRIVING-DA-COMMAND). The actuation adapter, a context
     * realization of the S-CORE path, detects a loss or a repetition by the
     * sequence count, a corruption by the check value and a delay by the
     * issue time against the newest world time, rejects the command and
     * applies nothing in its place. The analysis of REQ-DRIVING-039 reads
     * this record; it makes no freedom-from-interference claim.
     */

  /* ───────────── The assumption of the realization ───────────── */

  part <'ASM-DRIVING-005'> asmActuationFollowsCommandedDeceleration : IncrementAssumption {
    doc /*
     * The actuation adapter's Ackermann control makes the simulated ego
     * vehicle follow the commanded acceleration up to a deceleration of 5.0
     * m/s², so that REQ-DRIVING-036 and REQ-DRIVING-037 cannot fail for the
     * bench. The control sets a desired speed and a desired acceleration;
     * whether the simulated vehicle reaches 5.0 m/s² with a jerk of 10.0
     * m/s³ is not measured. A calibration run before phase
     * 10 shows it: the commanded against the achieved deceleration of the
     * scenario's vehicle on the scenario's road. No evidence of record holds
     * it, so it stays an assumption.
     */
  }

  part <'ASM-DRIVING-006'> asmCandidateSteeringTurnsTowardLaneCentre : IncrementAssumption {
    doc /*
     * The candidate's steering, given to the simulator by the rule of
     * MAP-DRIVING-DA-COMMAND, turns the simulated ego vehicle back toward its
     * lane centre. The rule takes the candidate's steering in the sign of
     * CARLA's steer, positive to the right, as upstream's own simulator path
     * does: that path gives the steering to CARLA's steer without a change
     * (vehicle_ros2_interface.cpp:67 and carla_control_publisher_node.py:49
     * at the pin). With the other sign the lateral control would diverge in
     * the first run. The readiness probe of 2026-11-15 drove upstream's path
     * in closed loop, and the vehicle swung about its lane centre on a
     * straight road. A calibration run before phase 10 shows it with the
     * bench's own adapter: with the ego vehicle placed to the right of its
     * lane centre, the candidate's commands turn it left, by the sign of the
     * yaw rate. No evidence of record holds it, so it stays an assumption.
     */
  }

  /* ───────────── Concerns and views of the phase ───────────── */

  concern driverAssistancePhysicalStructureConcern : PhysicalStructureConcern {
    doc /*
     * System architects and software developers need the software and
     * platform elements that realize the driver-assistance system on the
     * bench, as they nest: the three hosts with their platform layers, the
     * two programs of the candidate and the five modules of its process, the
     * actuation adapter and the S-CORE services, the simulator with its
     * camera rig, the hypervisor and the two AAOS SDV guests with the warning
     * presentation.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder softwareDeveloper : SoftwareDeveloper;
  }

  view driverAssistancePhysicalStructureView {
    viewpoint selectedPhysicalStructureViewpoint : PhysicalStructureDefinitionViewpoint {
      frame driverAssistancePhysicalStructureConcern;
    }
    expose driverAssistancePhysicalSystem;
    expose driverAssistancePhysicalSystem::scoreHost;
    expose driverAssistancePhysicalSystem::scoreHost::os;
    expose driverAssistancePhysicalSystem::scoreHost::assistanceSoftware;
    expose driverAssistancePhysicalSystem::scoreHost::assistanceSoftware::identityRecording;
    expose driverAssistancePhysicalSystem::scoreHost::assistanceSoftware::visionPilotApplication;
    expose driverAssistancePhysicalSystem::scoreHost::assistanceSoftware::visionPilotApplication::cameraInterface;
    expose driverAssistancePhysicalSystem::scoreHost::assistanceSoftware::visionPilotApplication::perceptionAndFusion;
    expose driverAssistancePhysicalSystem::scoreHost::assistanceSoftware::visionPilotApplication::safetyGuardianPlanner;
    expose driverAssistancePhysicalSystem::scoreHost::assistanceSoftware::visionPilotApplication::vehicleInterface;
    expose driverAssistancePhysicalSystem::scoreHost::assistanceSoftware::visionPilotApplication::warningRequestPublisher;
    expose driverAssistancePhysicalSystem::scoreHost::actuationAdapter;
    expose driverAssistancePhysicalSystem::scoreHost::scoreServices;
    expose driverAssistancePhysicalSystem::scoreHost::scoreServices::launchManager;
    expose driverAssistancePhysicalSystem::scoreHost::scoreServices::gatewayd;
    expose driverAssistancePhysicalSystem::scoreHost::scoreServices::someipd;
    expose driverAssistancePhysicalSystem::simulatorHost;
    expose driverAssistancePhysicalSystem::simulatorHost::os;
    expose driverAssistancePhysicalSystem::simulatorHost::carlaServer;
    expose driverAssistancePhysicalSystem::simulatorHost::carlaServer::cameraRig;
    expose driverAssistancePhysicalSystem::simulatorHost::carlaServer::cameraRig::frontCamera;
    expose driverAssistancePhysicalSystem::guestHost;
    expose driverAssistancePhysicalSystem::guestHost::os;
    expose driverAssistancePhysicalSystem::guestHost::hypervisor;
    expose driverAssistancePhysicalSystem::sdvCoreGuest;
    expose driverAssistancePhysicalSystem::sdvCoreGuest::os;
    expose driverAssistancePhysicalSystem::sdvCoreGuest::sdvMiddleware;
    expose driverAssistancePhysicalSystem::sdvCoreGuest::sdvCore;
    expose driverAssistancePhysicalSystem::iviGuest;
    expose driverAssistancePhysicalSystem::iviGuest::os;
    expose driverAssistancePhysicalSystem::iviGuest::sdvGateway;
    expose driverAssistancePhysicalSystem::iviGuest::warningPresentation;
    filter not (@ SysML::AllocationUsage);
    filter not (@ SysML::BindingConnectorAsUsage);
    render asTreeDiagram;
  }

  concern driverAssistancePhysicalAllocationConcern : PhysicalLogicalMappingConcern {
    doc /*
     * System architects and verification engineers need each logical element
     * of phase 7 allocated to the software elements that carry it, and each
     * software element carrying one: the identity recording application, the
     * camera interface and the perception and fusion of the candidate's
     * process, its planner, which carries both the warning requester and the
     * driving commander, its vehicle interface and its warning request
     * publisher. An allocation is a responsibility assignment, no deployment
     * or runtime claim.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder verificationEngineer : VerificationEngineer;
  }

  view driverAssistancePhysicalLogicalMappingView : MVD::MatrixView {
    viewpoint selectedPhysicalLogicalMappingViewpoint : PhysicalLogicalMappingViewpoint {
      frame driverAssistancePhysicalAllocationConcern;
      frame emergencyBrakingIndependenceConcern;
    }
    view :>> rowView {
      expose DriverAssistanceLogicalSystem::identityRecorder;
      expose DriverAssistanceLogicalSystem::vehicleAheadAssessor;
      expose DriverAssistanceLogicalSystem::warningRequester;
      expose DriverAssistanceLogicalSystem::drivingCommander;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> columnView {
      expose driverAssistancePhysicalSystem::scoreHost::assistanceSoftware::identityRecording;
      expose driverAssistancePhysicalSystem::scoreHost::assistanceSoftware::visionPilotApplication::cameraInterface;
      expose driverAssistancePhysicalSystem::scoreHost::assistanceSoftware::visionPilotApplication::perceptionAndFusion;
      expose driverAssistancePhysicalSystem::scoreHost::assistanceSoftware::visionPilotApplication::safetyGuardianPlanner;
      expose driverAssistancePhysicalSystem::scoreHost::assistanceSoftware::visionPilotApplication::vehicleInterface;
      expose driverAssistancePhysicalSystem::scoreHost::assistanceSoftware::visionPilotApplication::warningRequestPublisher;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> cellView {
      expose DE4SDV_DriverAssistancePhysicalSoftwareRealization::*;
      attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;
    }
  }

  view driverAssistanceSCOREPathExchangeView {
    doc /*
     * The S-CORE path (scoreCommandAndWarningPathConcern) and the
     * independence of the emergency braking's command
     * (emergencyBrakingIndependenceConcern) in one interconnection of the
     * S-CORE host: the driving command leaves the candidate's vehicle
     * interface on an mw::com event to the actuation adapter, the only
     * element that writes the simulator's Ackermann control; the warning
     * request leaves the candidate's warning request publisher on an mw::com
     * event to gatewayd, then someipd, and leaves the host on SOME/IP to the
     * AAOS SDV; the emergency braking leaves in the one driving command. No
     * other port leads to the Ackermann control or to the guests. Inside the
     * candidate's process the hand-offs are drawn as such. The
     * functional-mapping question is answered by this exchange and by the
     * matrix, not by a function-by-software matrix: no direct relation
     * exists between a function and a software element to draw. The guests
     * are drawn in the structure tree only.
     */
    viewpoint selectedPhysicalInternalExchangeViewpoint : PhysicalInternalExchangeViewpoint {
      frame scoreCommandAndWarningPathConcern;
      frame emergencyBrakingIndependenceConcern;
    }
    expose driverAssistanceSCOREHost;
    expose driverAssistanceSCOREHost::**;
    filter not (@ SysML::AllocationUsage);
    attribute depth = -1;
    attribute showAnnotationRows = false;
    render asInterconnectionDiagram;
  }
}
