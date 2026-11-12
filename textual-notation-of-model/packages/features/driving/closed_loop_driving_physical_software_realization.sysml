/*
 * SPDX-License-Identifier: Apache-2.0
 *
 * INC-DRIVING-001, phase 8: the physical and software realization of the
 * closed-loop driving system. What software, hardware and deployment elements
 * realize the six logical elements of phase 7, and on which technology do the
 * exchanges travel that REQ-DRIVING-014 and REQ-DRIVING-028 constrain?
 *
 * The owner's picks of 2026-11-06 (A, B, C, D, decisions 3 to 5):
 *
 * - Topology A. The loop is one Eclipse S-CORE program, a FEO agent: the
 *   fixed-execution-order framework of eclipse-score/feo runs four activities
 *   in one Linux process, in the order of the loop, once per camera frame:
 *   condition the inputs, infer the plan, supervise the loop, command the
 *   vehicle. Each activity is a software element that carries one logical
 *   element. The actuation adapter and the operational-state publisher are
 *   S-CORE applications of their own, so the stop response of REQ-DRIVING-028
 *   survives the agent, and the observation stays off the loop (phase 7).
 * - B. The planner runs the pinned AutoE2E checkpoint (source revision
 *   cb50764b8250a3c44ee5b79b87ba02c5a83b0c91) on its training framework,
 *   PyTorch, in the agent's process (amended by the owner's engine decision of
 *   2026-11-08; the pick of 2026-11-06, C++ over an ONNX export on an inference
 *   engine, is now ALT-DRIVING-ONNXENGINE-001). Whether the planner's stack
 *   stands for the checkpoint is GAP-DRIVING-003.
 * - C. Eclipse S-CORE pinned at reference_integration v0.10.0
 *   (ca2a5f03724780be3cebf3d80e0c9c0c6fa64eb2, known_good.json of
 *   2026-08-28): Communication v0.6.0 (mw::com, LoLa), Lifecycle v0.10.0
 *   (Launch Manager), Logging v0.2.6, Time v0.3.1, Configuration Management
 *   v0.3.1, Baselibs v0.2.17. Two modules sit outside that baseline: FEO at
 *   v1.0.5 (313b3d849c17881d3a11b6bf62aa2afab6565ef0) with one DE4SDV patch
 *   (GAP-DRIVING-001), and the SOME/IP gateway of INC-MW-011 at
 *   d9eac670b7534352749da3d30f52aebf5129f168, incubation code (GAP-MW-036).
 *   No source is vendored.
 * - D. KUKSA Databroker stays unselected: ALT-MW-KUKSA-001 stands. It is a
 *   QM gRPC broker of VSS signals; on the command path it would put a hop
 *   beside S-CORE communication (REQ-DRIVING-014), and on the observation
 *   path AAOS SDV consumes a typed Data Tunnel topic (decision 4). A host-side
 *   VSS broker is at most a phase 9 variation point.
 * - Decision 3. The simulator follows the wall clock and never waits for a
 *   plan (phase 0: no retiming of a slow simulation); since 2026-11-08 it
 *   runs in synchronous mode, ticked by a world-side pacer (below).
 *   Simulation time comes with each measurement (REQ-DRIVING-030) and from
 *   the world snapshot at the actuation adapter (REQ-DRIVING-028);
 *   wall-clock time from the host (REQ-DRIVING-013, -015 to -017, -019,
 *   -029, -031, -032).
 * - Decision 4. The operational state reaches AAOS SDV on the production path
 *   INC-MW-011 proved for opaque frames: the publisher's S-CORE event, the
 *   gateway's gatewayd and someipd, SOME/IP across the hypervisor into the
 *   SDV Core VM, the SOME/IP interop of SDV Core into a Data Tunnel topic,
 *   the SDV Gateway on the IVI VM, the observer application. Here the topic
 *   is typed: a VSIDL message for the driving operational state
 *   (GAP-DRIVING-006). No DE4SDV relay on the guest.
 * - Decision 5. The ego-motion sample is typed by COVESA VSS at the port where
 *   it enters the S-CORE contract (Vehicle_Speed, Vehicle_Acceleration_Longitudinal,
 *   Vehicle_Acceleration_Lateral, Vehicle_AngularVelocity_Yaw); the commanded
 *   acceleration and steering angle have no VSS signal and are two
 *   DE4SDV_VSS_Extensions candidates, local to DE4SDV (proposing them to
 *   COVESA needs the owner's word).
 *
 * Amended on the owner's decisions of 2026-11-07 to 2026-11-09, read from
 * the readiness probes P1 to P4. A probe is evidence for this amendment,
 * never a result of the increment: it closes no requirement and no case.
 *
 * - The agent's activities are Rust shells over C++ libraries (2026-11-07).
 *   FEO's topics are Rust-only at the pinned commit and its C++ binding has
 *   no topic API, so the activities that move data on FEO topics are Rust;
 *   the simulator client, the mw::com skeletons and the conversions are C++
 *   libraries behind them.
 * - FEO runs one chain per camera frame through an event trigger, a DE4SDV
 *   patch on top of v1.0.5 (owner decision (a) of 2026-11-07): the
 *   scheduler waits for the next frame instead of a timer, takes the newest
 *   frame and counts the frames it skipped. Unpatched FEO is timer-paced
 *   only. upstream.md says what DE4SDV has put to the FEO maintainers.
 * - FEO builds beside the v0.10.0 modules only with eight
 *   single_version_override entries that force the reference integration's
 *   pins: Communication 0.6.0, Lifecycle 0.10.0, Baselibs 0.2.17,
 *   score_crates 0.0.11, score_docs_as_code 8.6.0, score_bazel_platforms
 *   1.1.0, score_tooling 3.0.1 and flatbuffers 25.12.19.bcr.1. The set is
 *   DE4SDV's integration metadata, checked again whenever FEO or the
 *   baseline moves (GAP-DRIVING-001).
 * - The Launch Manager runs as root: it changes the user of each program it
 *   starts (setuid, setgroups), which an unprivileged Launch Manager cannot.
 * - Engine (2026-11-08): the planner runs PyTorch in the agent's process. Four
 *   exports of the checkpoint to ONNX exhausted 64 GB of host memory in the
 *   exporter's graph passes without reporting an unsupported operator, so
 *   TensorRT and ONNX Runtime have no model to run. The planning stack is the
 *   checkpoint with DE4SDV's rounding-level kernel changes (the owner's stack
 *   decision of 2026-11-08), pinned with its libraries (the library pin of
 *   2026-11-08): torch 2.7.1 built for CUDA 12.8, triton 3.3.1 and the cuDNN of
 *   nvidia-cudnn-cu12 9.26.0.51, with no TensorRT, ONNX Runtime or CUDA 13
 *   library in the planner's environment.
 * - Clock (2026-11-08, amending decision 3): the simulator runs in synchronous
 *   mode with a fixed 100 ms step, and a world-side pacer of the bench's
 *   scenario tooling ticks it on the wall clock, so the simulation keeps
 *   wall-clock pace (real-time factor 0.99999 in the probe) while no client of
 *   the loop ticks it. The simulator's own asynchronous modes ran ahead of the
 *   wall clock or captured off the 100 ms grid. Capture times come from the
 *   frame index: the simulator stores the step as a 32-bit float, and its
 *   stamps drift off the grid that the checkpoint's history cache matches
 *   exactly.
 * - Recording (2026-11-09): separate real-time recordings per host, each
 *   showing its clocks: the simulator's chase view rendered and encoded by
 *   the simulator host's NVENC encoder after one warm-up lap, the IVI VM's
 *   display recorded on the guest, and the terminal sessions recorded as
 *   terminal sessions; nothing retimed. It supersedes the single capture of
 *   2026-11-06 (phase 10).
 * - Bench rules (2026-11-09), the bench's eight operating rules: pinned code
 *   for the planner; a parity check at start; capture-safe preprocessing in
 *   the planner; no recompilation after the warm-up; the history cache at 64
 *   entries for the five interleaved history streams of a 10 Hz loop;
 *   capture times from the frame index; the simulator never on the
 *   planner's card; one warm-up lap of the route with every camera, the
 *   recording view included, in the same simulator session before any
 *   judged or recorded run.
 * - The bench is three hosts (2026-11-09): the S-CORE host with the
 *   planner's GPU, the simulator host with its own GPU, and the guest host
 *   with KVM for the two AAOS SDV guests. The simulator's exchanges cross
 *   the bench network between the simulator host and the S-CORE host; the
 *   operational state crosses a VXLAN segment from the S-CORE host into the
 *   guests' bridge. The cloud's GPU hosts nest no VM, and the planner missed
 *   its 100 ms budget whenever the simulator rendered on its card.
 * - With the simulator on its own card the planner met REQ-DRIVING-013's
 *   budget in the probe at wall-clock pace, so the increment needed no
 *   redirect then: the charter's hold/redirect condition was not met in the
 *   probe. The first verification runs later missed the budget narrowly,
 *   and the owner accepted the miss; later runs kept it with almost no
 *   margin (GAP-DRIVING-013).
 * - GAP-DRIVING-002 and GAP-DRIVING-004 are retired. The gateway built at
 *   the v0.10.0 modules, its mw::com side received every sample of a 0.6.0
 *   publisher, and SOME/IP between two hosts completed the subscription and
 *   carried 600 of 600 events to the IVI VM in order. The simulator's
 *   client library linked into an S-CORE application with one C++ standard
 *   library, read a camera frame and applied a vehicle control.
 *
 * Amended on the owner's decision of 2026-11-12, after phase 10, from the
 * bench that implements this realization. Each mapping record now names
 * where the bench keeps the contract that phase 10 authored and says what
 * is left to do; every record stays a candidate.
 *
 * - The command law is pure pursuit of the plan's path
 *   (MAP-DRIVING-COMMAND). The law this file stated before, the plan's
 *   curvature at the control horizon turned into a front-wheel angle, was
 *   run first: in its two runs of the closed-loop scenario (2026-11-09)
 *   every steering command of the first 23 s was 4 to 10 degrees to the
 *   right, and pure pursuit of the same plans asks for less than 1 degree
 *   in more than nine of ten.
 * - A plan carries the path that its 64 pairs give, beside the pairs
 *   (MAP-DRIVING-PLAN); the command law steers on it.
 * - The loop supervision does not stop on a missed planning period
 *   (MAP-DRIVING-MODE). No requirement asks for that stop; a late plan
 *   stops the vehicle when it is stale (REQ-DRIVING-026).
 * - The operational state has three Data Tunnel topics of one message
 *   type, one per event (MAP-DRIVING-OPERATIONAL-STATE).
 * - The route provider announces the route to the agent again and again,
 *   so that a route can grow old (MAP-DRIVING-ROUTE).
 * - The vehicle's longitudinal response is not identified yet: the table
 *   of the shipped vehicle configuration is a placeholder
 *   (MAP-DRIVING-VEHICLE-CONTROL).
 *
 * Alternatives recorded and not selected:
 * - ALT-DRIVING-PLAINAPPS-001: four plain S-CORE applications instead of the
 *   FEO agent, every exchange of the loop over mw::com. Cheaper to build, no
 *   fixed-order scheduler, two more process hops inside the 100 ms budget of
 *   REQ-DRIVING-013. The fallback if GAP-DRIVING-001 closes against FEO.
 * - ALT-DRIVING-SIMBRIDGE-001: a separate simulation-bridge process holding
 *   the simulator client and publishing camera frames over mw::com, instead
 *   of the client inside the agent's input activity. One more copy of each
 *   frame and one more hop before planning; production-like for a camera
 *   driver, not needed on the bench, where the client links into the
 *   S-CORE application.
 * - ALT-DRIVING-LIBTORCH-001: the planner in C++ on the training
 *   framework's C++ runtime over a traced or exported graph, instead of
 *   PyTorch in the agent's process. No Python on the loop and the closest
 *   numerics, but not among the runtimes the S-CORE AI Platform request
 *   names, and its graph is not exported yet. The fallback if Python in the
 *   agent's process cannot be kept (GAP-DRIVING-003).
 * - ALT-DRIVING-FEOMWCOM-001: FEO from its main branch, whose feo-com has an
 *   mw_com backend, so that the plan hops inside the agent are themselves
 *   mw::com. Unreleased, and its module file pins an older Communication;
 *   the reading question the owner closed on 2026-11-06 would not arise,
 *   the build risk grows.
 * - ALT-DRIVING-ONNXENGINE-001: the pick B of 2026-11-06, the planner in C++
 *   over an ONNX export on TensorRT, ONNX Runtime as the fallback, with no
 *   training framework on the loop. Not selected on 2026-11-08: the export did
 *   not complete (the engine decision of 2026-11-08). Open again if a change of
 *   the graph's shape lets the export fit.
 * - ALT-DRIVING-FEOGATE-001: unpatched FEO with a 1 ms cycle and the first
 *   activity blocking until the next frame. One chain per frame without a
 *   patch, but an error-level overrun log in every cycle, a cycle counter
 *   that no longer measures time, and frames queued under overload unless
 *   the activity drains to the newest. Not selected on 2026-11-07; the
 *   fallback if the patch cannot be kept.
 * - ALT-DRIVING-LOCKSTEP-001: the simulator waits for each plan before its
 *   next step. It meets the latency on one shared card, but it retimes a
 *   slow simulation against decision 3 and missed REQ-DRIVING-013's
 *   real-time factor (0.872 against 0.95 in the probe). Usable for
 *   development runs that produce no verification evidence.
 *
 * The context parts of phase 2 are realized on the bench as context parts of
 * the physical system, so the boundary connections have ends: the simulator
 * server stands for the vehicle and the road environment (System 2), the
 * scenario's route provider for the navigation (System 2, on the Linux
 * host), the AAOS SDV guests for the observing product. They stay context;
 * no logical element is allocated to them. An allocation here is a
 * responsibility assignment, no deployment, execution or runtime claim; a
 * signal mapping is no interoperability claim; a pin is no build claim. The
 * realization-readiness probe runs before phase 10 builds anything.
 */
package DE4SDV_ClosedLoopDrivingPhysicalSoftwareRealization {
  private import ScalarValues::*;
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_MethodProcess::SystemToSoftwareSignalMappingCandidate;
  private import DE4SDV_MethodProcess::LogicalToSoftwareSignalMappingRecord;
  private import DE4SDV_MethodProcess::SignalMappingDisposition;
  private import DE4SDV_TraceVocabulary::PhysicalAllocationElement;
  private import DE4SDV_SDVPlatformStack::LinuxPlatform;
  private import DE4SDV_SDVPlatformStack::KVMHypervisor;
  private import DE4SDV_SDVPlatformStack::EclipseSCORE;
  private import DE4SDV_SDVPlatformStack::AndroidHLOS;
  private import DE4SDV_SDVPlatformStack::AndroidSDVMiddleware;
  private import DE4SDV_SDVPlatformStack::OSHypervisorInterface;
  private import DE4SDV_AAOSSDVMiddlewareBoundary::SDVCoreBoundary;
  private import DE4SDV_AAOSSDVMiddlewareBoundary::SDVGatewayOnIVIBoundary;
  private import DE4SDV_AAOSSDVMiddlewareBoundary::DataTunnelPort;
  private import DE4SDV_ClosedLoopDrivingFraming::ClosedLoopDrivingSystem;
  private import DE4SDV_ClosedLoopDrivingFraming::gapTransportAndControl;
  private import DE4SDV_ClosedLoopDrivingFraming::gapModelInputAndFeedback;
  private import DE4SDV_ClosedLoopDrivingFraming::scoreCommandPathConcern;
  private import DE4SDV_ClosedLoopDrivingFraming::checkpointCommandAuthorityConcern;
  private import DE4SDV_ClosedLoopDrivingFraming::aaosObservationFidelityConcern;
  private import DE4SDV_ClosedLoopDrivingOperationalContext::CameraImages;
  private import DE4SDV_ClosedLoopDrivingOperationalContext::EgoMotionState;
  private import DE4SDV_ClosedLoopDrivingOperationalContext::Route;
  private import DE4SDV_ClosedLoopDrivingOperationalContext::VehicleMotionCommand;
  private import DE4SDV_ClosedLoopDrivingOperationalContext::DrivingOperationalState;
  private import DE4SDV_ClosedLoopDrivingOperationalContext::NavigationSystem;
  private import DE4SDV_ClosedLoopDrivingOperationalContext::DrivingStateObserverApplication;
  private import DE4SDV_ClosedLoopDrivingFunctionalArchitecture::CheckpointInputs;
  private import DE4SDV_ClosedLoopDrivingFunctionalArchitecture::InputCondition;
  private import DE4SDV_ClosedLoopDrivingFunctionalArchitecture::DrivingPlan;
  private import DE4SDV_ClosedLoopDrivingFunctionalArchitecture::DrivingMode;
  private import DE4SDV_ClosedLoopDrivingFunctionalArchitecture::ActuationState;
  private import DE4SDV_ClosedLoopDrivingFunctionalArchitecture::CameraPosition;
  private import DE4SDV_VehicleSensingBoundary::VehicleSensingAssembly;
  private import DE4SDV_ClosedLoopDrivingLogicalArchitecture::ClosedLoopDrivingLogicalSystem;
  private import DE4SDV_ClosedLoopDrivingNeedsRequirements::reqPlansAndCommandsOverSCORE;
  private import COVESA_VSS::SignalDefinitions::Vehicle_Speed;
  private import COVESA_VSS::SignalDefinitions::Vehicle_Acceleration_Longitudinal;
  private import COVESA_VSS::SignalDefinitions::Vehicle_Acceleration_Lateral;
  private import COVESA_VSS::SignalDefinitions::Vehicle_AngularVelocity_Yaw;
  private import DE4SDV_VSS_Extensions::Vehicle_ADAS_Driving_Command_Acceleration;
  private import DE4SDV_VSS_Extensions::Vehicle_ADAS_Driving_Command_SteeringAngle;
  private import DE4SDV_Stakeholders::*;
  private import SAF_Viewpoints::*;
  private import SysideViews::**;
  private import Views::*;

  /* ───────────── The items this phase types at the software contracts ───────────── */

  item def SimulationClock {
    doc /*
     * The simulation time of the newest world snapshot the simulator server
     * publishes, in seconds since the scenario started. A System 2 item: it
     * exists because the vehicle is simulated. REQ-DRIVING-028 counts its
     * 200 ms on this clock at the actuation adapter.
     */
    attribute simulationTime : Real;
  }

  item def EgoMotionSamplePayload :> EgoMotionState {
    doc /*
     * The ego-motion sample as the realization types it where it enters the
     * S-CORE contract: the input activity publishes it for the vehicle
     * commander (an FEO topic) and for the state publisher (an mw::com
     * event). The four vehicle signals are typed by COVESA VSS (decision 5);
     * the capture time is the simulation time of the measurement
     * (REQ-DRIVING-030). The checkpoint takes the history's yaw rate and
     * curvature as zero (REQ-DRIVING-008, GAP-DRIVING-010); the curvature is
     * no vehicle signal (MAP-DRIVING-EGO-MOTION).
     */
    attribute speed : Vehicle_Speed;
    attribute longitudinalAcceleration : Vehicle_Acceleration_Longitudinal;
    attribute lateralAcceleration : Vehicle_Acceleration_Lateral;
    attribute yawRate : Vehicle_AngularVelocity_Yaw;
    attribute captureTime : Real;
  }

  item def VehicleMotionCommandPayload :> VehicleMotionCommand {
    doc /*
     * The steering and acceleration command as the realization types it on
     * the mw::com event from the agent to the actuation adapter, the hop
     * REQ-DRIVING-014 constrains. The two commanded quantities have no COVESA
     * VSS signal; they are typed by two DE4SDV_VSS_Extensions candidates
     * (decision 5). The production time is wall-clock time (REQ-DRIVING-032);
     * the plan reference names the plan the command was computed from
     * (REQ-DRIVING-011, REQ-DRIVING-034).
     */
    attribute acceleration : Vehicle_ADAS_Driving_Command_Acceleration;
    attribute steeringAngle : Vehicle_ADAS_Driving_Command_SteeringAngle;
    attribute productionTime : Real;
    attribute planReference : String;
  }

  item def SimulatorVehicleControl {
    doc /*
     * The information that crosses to the simulator, and the only thing
     * that does: the control the actuation adapter applies to the ego
     * vehicle through the simulator client, the three fields of the client
     * library's VehicleControl the adapter sets, throttle and brake in
     * [0, 1] and steer in [-1, 1] (the client library's API reference; the
     * release is pinned in phase 10). Hand brake, reverse, manual gear
     * shift and gear stay at their defaults. The adapter converts the
     * commanded acceleration and steering angle into these within the
     * vehicle's limits (REQ-DRIVING-012), so the logical VehicleMotionCommand
     * ends at the adapter and this is what the simulated vehicle receives.
     */
    attribute throttle : Real;
    attribute steer : Real;
    attribute brake : Real;
  }

  /* ───────────── Ports: one pair per item, whatever hop carries it ───────────── */

  port def CameraStreamOut {
    doc /* The camera images the simulator server streams to a client. */
    out item cameraImages : CameraImages;
  }
  port def CameraStreamIn {
    doc /* The camera images a client receives from the simulator server. */
    in item cameraImages : CameraImages;
  }
  port def EgoMotionStreamOut {
    doc /* The motion state of the ego vehicle the simulator server provides. */
    out item egoMotion : EgoMotionState;
  }
  port def EgoMotionStreamIn {
    doc /* The motion state of the ego vehicle a client reads from the simulator server. */
    in item egoMotion : EgoMotionState;
  }
  port def RouteOut {
    doc /* The route of the scenario, from the route provider. */
    out item route : Route;
  }
  port def RouteIn {
    doc /* The route of the scenario, into the input activity. */
    in item route : Route;
  }
  port def SimulationClockOut {
    doc /* The simulation time of the newest world snapshot, from the simulator server. */
    out item simulationClock : SimulationClock;
  }
  port def SimulationClockIn {
    doc /* The simulation time of the newest world snapshot, into the actuation adapter. */
    in item simulationClock : SimulationClock;
  }
  port def CheckpointInputsOut {
    doc /* The checkpoint inputs on the FEO topic from the input activity. */
    out item checkpointInputs : CheckpointInputs;
  }
  port def CheckpointInputsIn {
    doc /* The checkpoint inputs on the FEO topic into the plan inference. */
    in item checkpointInputs : CheckpointInputs;
  }
  port def InputConditionOut {
    doc /* The input condition on the FEO topic from the input activity. */
    out item inputCondition : InputCondition;
  }
  port def InputConditionIn {
    doc /* The input condition on the FEO topic into the loop supervision. */
    in item inputCondition : InputCondition;
  }
  port def DrivingPlanOut {
    doc /* A plan leaving an element: on an FEO topic inside the agent, or as an mw::com event. */
    out item plan : DrivingPlan;
  }
  port def DrivingPlanIn {
    doc /* A plan entering an element: from an FEO topic inside the agent, or from an mw::com event. */
    in item plan : DrivingPlan;
  }
  port def DrivingModeOut {
    doc /* The mode leaving the loop supervision: on an FEO topic, or as an mw::com event. */
    out item mode : DrivingMode;
  }
  port def DrivingModeIn {
    doc /* The mode entering an element: from an FEO topic, or from an mw::com event. */
    in item mode : DrivingMode;
  }
  port def EgoMotionSampleOut {
    doc /* The typed ego-motion sample leaving the input activity: an FEO topic and an mw::com event. */
    out item egoMotionSample : EgoMotionSamplePayload;
  }
  port def EgoMotionSampleIn {
    doc /* The typed ego-motion sample entering the vehicle commander or the state publisher. */
    in item egoMotionSample : EgoMotionSamplePayload;
  }
  port def MotionCommandOut {
    doc /* The typed command on the mw::com event from the vehicle commander (REQ-DRIVING-014). */
    out item command : VehicleMotionCommandPayload;
  }
  port def MotionCommandIn {
    doc /* The typed command from the mw::com event into the actuation adapter. */
    in item command : VehicleMotionCommandPayload;
  }
  port def VehicleControlOut {
    doc /* The vehicle control the actuation adapter applies at the simulated actuation. */
    out item vehicleControl : SimulatorVehicleControl;
  }
  port def VehicleControlIn {
    doc /* The vehicle control the simulator server applies to the ego vehicle. */
    in item vehicleControl : SimulatorVehicleControl;
  }
  port def OperationalStateOut {
    doc /* The operational state leaving an element on any hop of the observation path. */
    out item operationalState : DrivingOperationalState;
  }
  port def OperationalStateIn {
    doc /* The operational state entering an element on any hop of the observation path. */
    in item operationalState : DrivingOperationalState;
  }
  port def ActuationStateOut {
    doc /* The actuation adapter's actuation-state event for the publisher: the applied command with its time, or its own stop with the cause. */
    out item actuationState : ActuationState;
  }
  port def ActuationStateIn {
    doc /* The publisher's subscription to the actuation adapter's actuation state. */
    in item actuationState : ActuationState;
  }

  /* ───────────── The software elements: four activities of one agent, two applications ───────────── */

  part def InputConditioningActivity :> PhysicalAllocationElement {
    doc /*
     * Carries the input conditioner of phase 7 as the first activity of the
     * FEO cycle: a Rust shell over a C++ library. It holds the simulator
     * client of the agent: the camera sensor stream and the motion state of
     * the ego vehicle arrive from the simulator host over the bench network,
     * through the client library on its threads, and the route of the
     * scenario from the route provider; the step reads the newest frame and
     * sample, marks each with its capture time in simulation time
     * (REQ-DRIVING-030), computed from the frame index at 100 ms per step
     * rather than read from the simulator's floating-point stamp (a bench
     * rule of 2026-11-09), keeps the camera and
     * ego-motion histories of the run (REQ-DRIVING-004, -008, -010), gives
     * the checkpoint the history's yaw rate and curvature as zero
     * (GAP-DRIVING-010), rasterizes the route mask and the map context
     * (REQ-DRIVING-006, -007) and writes the checkpoint
     * inputs and the input condition to their FEO topics. It publishes the
     * typed ego-motion sample for the vehicle commander and, as an mw::com
     * event, for the state publisher. On the bench the client is the
     * simulator's; in a vehicle a camera driver would fill the same buffer.
     */
    port cameraImagesIn : CameraStreamIn;
    port egoMotionIn : EgoMotionStreamIn;
    port routeIn : RouteIn;
    port checkpointInputsOut : CheckpointInputsOut;
    port inputConditionOut : InputConditionOut;
    port egoMotionSampleOut : EgoMotionSampleOut;
  }

  part def PlanInferenceActivity :> PhysicalAllocationElement {
    doc /*
     * Carries the planner of phase 7, run identity and planning, as the second
     * activity of the FEO cycle: a Rust shell over a C++ library that embeds
     * the Python runtime and runs the pinned checkpoint on PyTorch in the
     * agent's process (the engine decision of 2026-11-08). At startup it reads
     * the configuration, computes the SHA-256 of the checkpoint file it loads,
     * refuses to plan when that SHA-256 differs from the one the configuration
     * names or none is named (REQ-DRIVING-035), checks the cuDNN version of its
     * pinned libraries, warms the planning stack up, checks its parity on a
     * recorded input, and records the run identity, among it the AutoE2E source
     * revision with DE4SDV's kernel changes, before the first plan
     * (REQ-DRIVING-033). Each step runs the planning stack, with capture-safe
     * preprocessing and no recompilation after the warm-up, on the checkpoint
     * inputs and writes the plan, with its producer, its production time and
     * the run record it names (REQ-DRIVING-031, -034), to the FEO topic for the
     * loop supervision and to the mw::com event for the state publisher
     * (REQ-DRIVING-015).
     */
    port checkpointInputsIn : CheckpointInputsIn;
    port planOut : DrivingPlanOut;
    port planEventOut : DrivingPlanOut;
  }

  part def LoopSupervisionActivity :> PhysicalAllocationElement {
    doc /*
     * Carries the loop supervisor of phase 7 as the third activity of the FEO
     * cycle: a Rust shell over a C++ library. It judges the input condition
     * and the plan (REQ-DRIVING-023 to -027), passes the newest valid plan
     * on, and decides the mode: driving, or the stop response with its
     * cause. A plan that misses the planning period of REQ-DRIVING-013 is no
     * cause of a stop. The mode goes to the vehicle commander on an FEO
     * topic and to the state publisher as an mw::com event
     * (REQ-DRIVING-029). It issues no command.
     */
    port inputConditionIn : InputConditionIn;
    port planIn : DrivingPlanIn;
    port validPlanOut : DrivingPlanOut;
    port modeOut : DrivingModeOut;
    port modeEventOut : DrivingModeOut;
  }

  part def VehicleCommandActivity :> PhysicalAllocationElement {
    doc /*
     * Carries the vehicle commander of phase 7 as the last activity of the FEO
     * cycle: a Rust shell over a C++ library. It computes the steering angle
     * and the acceleration from the newest valid plan and the current motion
     * sample (REQ-DRIVING-011), within the limits the configuration names
     * (REQ-DRIVING-012), commands the stop response in its mode
     * (REQ-DRIVING-020 to -022), stamps the command with its production time
     * (REQ-DRIVING-032) and publishes it as the typed mw::com event to the
     * actuation adapter: the hop REQ-DRIVING-014 constrains, on S-CORE
     * communication and nothing beside it.
     */
    port validPlanIn : DrivingPlanIn;
    port modeIn : DrivingModeIn;
    port egoMotionSampleIn : EgoMotionSampleIn;
    port commandOut : MotionCommandOut;
  }

  part def DrivingAgentApplication {
    doc /*
     * The FEO agent: one Linux process of the fixed-execution-order
     * framework (eclipse-score/feo v1.0.5 with DE4SDV's event-trigger patch,
     * a Rust framework), running the four activities in the order of the
     * loop, once per cycle. Each activity is a Rust shell over C++
     * libraries: FEO's topics are Rust-only at the pin, and its C++ activity
     * binding has no topic API. The cycle is paced by the camera frames of
     * the simulation (REQ-DRIVING-001: one plan per 100 ms step of
     * simulation time, no two consecutive steps without one) through the
     * event trigger: the scheduler waits for the next frame instead of a
     * timer, takes the newest frame and counts the frames it skipped, so a
     * slow cycle plans on a current frame, not on a queued one
     * (ASM-DRIVING-001). Inside the
     * agent the checkpoint inputs, the input condition, the plan, the valid
     * plan, the mode and the ego-motion sample move on FEO topics of the
     * framework's communication layer (shared memory on one host); they are
     * no hops between processes, so REQ-DRIVING-014 does not constrain them
     * (the owner's reading of 2026-11-06, reqPlansAndCommandsOverSCOREReading).
     * Across processes the agent speaks mw::com only. It is started and
     * supervised by the Launch Manager of S-CORE Lifecycle.
     */
    port cameraImagesIn : CameraStreamIn;
    port egoMotionIn : EgoMotionStreamIn;
    port routeIn : RouteIn;
    port egoMotionSampleOut : EgoMotionSampleOut;
    port planEventOut : DrivingPlanOut;
    port modeEventOut : DrivingModeOut;
    port commandOut : MotionCommandOut;

    part conditionInputs : InputConditioningActivity;
    part inferPlan : PlanInferenceActivity;
    part superviseLoop : LoopSupervisionActivity;
    part commandVehicle : VehicleCommandActivity;

    connection cameraImagesDelegation connect cameraImagesIn to conditionInputs.cameraImagesIn;
    connection egoMotionDelegation connect egoMotionIn to conditionInputs.egoMotionIn;
    connection routeDelegation connect routeIn to conditionInputs.routeIn;
    connection egoMotionSampleDelegation connect conditionInputs.egoMotionSampleOut to egoMotionSampleOut;
    connection planEventDelegation connect inferPlan.planEventOut to planEventOut;
    connection modeEventDelegation connect superviseLoop.modeEventOut to modeEventOut;
    connection commandDelegation connect commandVehicle.commandOut to commandOut;
    connection checkpointInputsTopic connect conditionInputs.checkpointInputsOut to inferPlan.checkpointInputsIn;
    connection inputConditionTopic connect conditionInputs.inputConditionOut to superviseLoop.inputConditionIn;
    connection egoMotionSampleTopic connect conditionInputs.egoMotionSampleOut to commandVehicle.egoMotionSampleIn;
    connection planTopic connect inferPlan.planOut to superviseLoop.planIn;
    connection validPlanTopic connect superviseLoop.validPlanOut to commandVehicle.validPlanIn;
    connection modeTopic connect superviseLoop.modeOut to commandVehicle.modeIn;
  }

  part def ActuationAdapterApplication :> PhysicalAllocationElement {
    doc /*
     * Carries the actuation gateway of phase 7: an S-CORE application of its
     * own, in C++, with a second simulator client over the bench network.
     * It subscribes to the
     * command event, converts the acceleration and the steering angle into
     * the simulator's vehicle control (throttle, brake, steer) within the
     * limits of the vehicle (REQ-DRIVING-012) and applies it to the ego
     * vehicle. It reads the simulation time from the world snapshot; when no
     * valid command has arrived for 200 ms of simulation time it applies the
     * stop response itself (REQ-DRIVING-028), which is why it is not an
     * activity of the agent. It publishes its actuation state as an mw::com
     * event for the state publisher, the applied command with its actuation
     * time or its own stop with the cause, so that the stop it decides is
     * published within the limit of REQ-DRIVING-029 like the one the
     * supervision decides (the amendment of 2026-11-06). Nothing it knows
     * flows back into the loop.
     */
    port commandIn : MotionCommandIn;
    port simulationClockIn : SimulationClockIn;
    port vehicleControlOut : VehicleControlOut;
    port actuationStateOut : ActuationStateOut;
  }

  part def OperationalStatePublisherApplication :> PhysicalAllocationElement {
    doc /*
     * Carries the operational-state publisher of phase 7: an S-CORE
     * application of its own, in C++, off the loop. It subscribes to the
     * plan, the mode and the ego-motion sample events of the agent and to
     * the actuation-state event of the actuation adapter, and publishes the
     * operational state, each publication with its producer and its time:
     * the plan (REQ-DRIVING-015), the motion sample (REQ-DRIVING-016), the
     * health at least every 200 ms also while no plan arrives
     * (REQ-DRIVING-017), and the stop with its cause when the mode changes
     * or the actuation state reports the adapter's own stop
     * (REQ-DRIVING-029). Its one output is the mw::com event the SOME/IP
     * gateway forwards; it has no port into the agent or the adapter
     * (REQ-DRIVING-018, -019).
     */
    port planIn : DrivingPlanIn;
    port modeIn : DrivingModeIn;
    port egoMotionSampleIn : EgoMotionSampleIn;
    port actuationStateIn : ActuationStateIn;
    port operationalStateOut : OperationalStateOut;
  }

  part def ClosedLoopDrivingSoftwareRealization :> ClosedLoopDrivingSystem {
    doc /*
     * The driving system as phase 8 realizes it: the same system as the
     * context's drivingSystem, now the three programs on the S-CORE host and
     * the S-CORE services they use, owned here with them (one instance on
     * the host, typed by the platform stack's middleware layer). The
     * boundary of phase 6 is kept as ports of the realization: the
     * camera images, the ego motion and the route in, the vehicle command
     * out, the operational state out; the simulation clock is a System 2
     * input the bench adds. Between processes every hop is mw::com (S-CORE
     * Communication v0.6.0): the command to the actuation adapter, the
     * REQ-DRIVING-014 hop; the plan, the mode and the ego-motion sample to
     * the publisher, and the actuation state from the adapter to the
     * publisher; the operational state to gatewayd. From gatewayd on the
     * path is INC-MW-011's: the gateway's IPC to someipd, SOME/IP out of the
     * host. The application-middleware adapter of the platform stack is the
     * mw::com binding code of the three programs; phase 9 derives it per
     * member.
     */
    port cameraImagesIn : CameraStreamIn;
    port egoMotionIn : EgoMotionStreamIn;
    port routeIn : RouteIn;
    port simulationClockIn : SimulationClockIn;
    port vehicleControlOut : VehicleControlOut;
    port operationalStateOut : OperationalStateOut;

    part drivingAgent : DrivingAgentApplication;
    part actuationAdapter : ActuationAdapterApplication;
    part statePublisherApplication : OperationalStatePublisherApplication;
    part scoreServices : EclipseSCORE {
      doc /*
       * The S-CORE services of the host the realization uses, one instance
       * on the host. Lifecycle's Launch Manager starts and supervises the
       * three programs; the SOME/IP gateway of INC-MW-011 (gatewayd and
       * someipd at d9eac670) carries the operational state out of the host.
       */
      part launchManager {
        doc /*
         * The Launch Manager of S-CORE Lifecycle v0.10.0: starts the agent,
         * the actuation adapter and the publisher and supervises them. It
         * runs as root, because it changes the user of each program it
         * starts (setuid, setgroups); the mw::com state a program leaves under
         * /tmp/mw_com_lola belongs to that user, so a change of user between
         * runs clears it first. Its own LmControlService needs two entries in
         * the mw::com manifest. It carries no logical element; its recovery
         * actions are a phase 10 configuration.
         */
      }
      part gatewayd : PhysicalAllocationElement {
        doc /*
         * The gatewayd process of the S-CORE SOME/IP gateway: subscribes to
         * the operational-state event on mw::com and hands it to someipd
         * over the gateway's IPC. Carries the publisher's reach to the
         * observer together with someipd; a process of the pinned gateway,
         * not DE4SDV code, and incubation code outside both baselines
         * (GAP-MW-036).
         */
        port operationalStateIn : OperationalStateIn;
        port operationalStateOut : OperationalStateOut;
      }
      part someipd : PhysicalAllocationElement {
        doc /*
         * The someipd process of the S-CORE SOME/IP gateway: offers the
         * operational-state service on SOME/IP and sends each event over the
         * VXLAN segment into the guests' bridge to the SOME/IP interop of SDV
         * Core. The last element of the driving system on the observation
         * path; a process of the pinned gateway, not DE4SDV code.
         */
        port operationalStateIn : OperationalStateIn;
        port operationalStateOut : OperationalStateOut;
      }
    }

    bind cameraImagesIn = drivingAgent.cameraImagesIn;
    bind egoMotionIn = drivingAgent.egoMotionIn;
    bind routeIn = drivingAgent.routeIn;
    bind simulationClockIn = actuationAdapter.simulationClockIn;
    bind vehicleControlOut = actuationAdapter.vehicleControlOut;
    bind operationalStateOut = scoreServices.someipd.operationalStateOut;
    connection commandOverSCORECommunication connect drivingAgent.commandOut to actuationAdapter.commandIn;
    connection planEventOverSCORECommunication connect drivingAgent.planEventOut to statePublisherApplication.planIn;
    connection modeEventOverSCORECommunication connect drivingAgent.modeEventOut to statePublisherApplication.modeIn;
    connection egoMotionSampleOverSCORECommunication connect drivingAgent.egoMotionSampleOut to statePublisherApplication.egoMotionSampleIn;
    connection actuationStateOverSCORECommunication connect actuationAdapter.actuationStateOut to statePublisherApplication.actuationStateIn;
    connection operationalStateOverSCORECommunication connect statePublisherApplication.operationalStateOut to scoreServices.gatewayd.operationalStateIn;
    connection operationalStateOverGatewayIPC connect scoreServices.gatewayd.operationalStateOut to scoreServices.someipd.operationalStateIn;
  }

  /* ───────────── The context realizations on the bench ───────────── */

  part def CARLASimulationServer {
    doc /*
     * The simulator server, System 2: renders the cameras of the ego vehicle
     * and simulates its dynamics and the road environment, so it stands for
     * the vehicle and the road environment of the phase 2 context on the
     * bench. It follows the wall clock and never waits for a plan (decision
     * 3, amended on 2026-11-08): it runs in synchronous mode with a fixed
     * 100 ms step, and a world-side pacer of the bench's scenario tooling
     * ticks it on the wall clock, so no element of the loop ticks the world.
     * It runs on the simulator host, on its own GPU. Two clients connect to
     * it over the bench network: the agent's input activity for the sensor
     * streams and the actuation adapter for the vehicle control and the
     * world snapshot. Its release is pinned with the scenario in phase 10.
     * The sensors of the loop are its: the simulated sensor rig below
     * renders the six camera streams and samples the ego motion the server
     * puts on its ports (the owner's sensing decision of 2026-11-06,
     * ASM-DRIVING-004). The chase view it renders for the recording is no
     * sensor of the loop.
     */
    port cameraStreamOut : CameraStreamOut;
    port egoMotionOut : EgoMotionStreamOut;
    port simulationClockOut : SimulationClockOut;
    port vehicleControlIn : VehicleControlIn;

    part sensorRig : SimulatedSensorRig;
  }

  part def SimulatedSensorRig {
    doc /*
     * The bench's sensors, System 2: six cameras attached to the simulated
     * ego vehicle and one ego-motion source, standing for the vehicle's
     * cameras and motion sensors of the phase 2 context. The rig's geometry
     * is the rig profile of the pinned checkpoint's dataset at the source
     * pin cb50764b (Model/plugins/alpasim_driver/alpasim_autoe2e/
     * configs/calibration/, one JSON per dataset rig): six cameras in the
     * canonical slots of Model/data_parsing/camera_slots.py, each with its
     * native image size, its intrinsic matrix and its camera-to-reference
     * pose, and the dataset's curvature rule for the ego-motion history. The
     * released checkpoints of the pinned source are trained on the nuPlan
     * and the KITScenes rigs (Model/plugins/alpasim_driver/README.md); which
     * profile applies follows the checkpoint pinned in phase 10, so no
     * profile number is stated here. The simulated cameras take the
     * profile's image size, field of view and pose; their principal point
     * sits at the image centre, where the profile's is offset, so the
     * projection operators of REQ-DRIVING-005 are built from the simulated
     * cameras' calibration and the offset is recorded with the pin. The
     * product line's sensing boundary (DE4SDV_VehicleSensingBoundary) types
     * its camera as a detection camera, one that produces object
     * observations, so it does not type these image cameras; whether an
     * image camera joins the sensing boundary is a product-line decision,
     * not this increment's. The rig stands for the sensing assembly by
     * dependency only. No connection, binding or port inside: the server's
     * ports carry the streams.
     */
    part frontCamera : SimulatedCamera { attribute :>> position = CameraPosition::front; }
    part frontLeftCamera : SimulatedCamera { attribute :>> position = CameraPosition::frontLeft; }
    part frontRightCamera : SimulatedCamera { attribute :>> position = CameraPosition::frontRight; }
    part rearLeftCamera : SimulatedCamera { attribute :>> position = CameraPosition::rearLeft; }
    part rearCamera : SimulatedCamera { attribute :>> position = CameraPosition::rear; }
    part rearRightCamera : SimulatedCamera { attribute :>> position = CameraPosition::rearRight; }
    part egoMotionSource : SimulatedEgoMotionSource;
  }

  part def SimulatedCamera {
    doc /*
     * One rendered camera of the rig, at one of the six positions of
     * REQ-DRIVING-003: it renders an image of the scene at the profile's
     * image size and field of view from the profile's pose on the ego
     * vehicle, stamped with the simulation time of the render
     * (REQ-DRIVING-030). Rendered, not captured: no exposure, no motion
     * blur, no lens distortion beyond what the simulator models
     * (ASM-DRIVING-004).
     */
    attribute position : CameraPosition;
  }

  part def SimulatedEgoMotionSource {
    doc /*
     * The rig's motion sensing: it reads the simulated ego vehicle's
     * vehicle state, its velocity, acceleration and angular velocity, from
     * the simulator's physics each step and stamps the sample with the
     * simulation time (REQ-DRIVING-030). That is ground truth: a vehicle's
     * inertial measurement unit and wheel odometry add noise, bias and
     * latency the bench does not have (ASM-DRIVING-004). The curvature the
     * checkpoint takes is derived inside the driving system
     * (MAP-DRIVING-EGO-MOTION), not here.
     */
  }

  dependency sensorRigStandsForTheSensingAssembly from SimulatedSensorRig to VehicleSensingAssembly;

  part def ScenarioRouteProvider :> NavigationSystem {
    doc /*
     * The navigation of the phase 2 context as the bench realizes it: the
     * pinned route of the scenario, System 2, read from the scenario
     * configuration on the S-CORE host and handed to the input activity at the
     * start of the run; the destination is the scenario's. It runs on the
     * S-CORE host, not on the AAOS SDV guest, so AAOS SDV is no input to the
     * loop and the context-role decision of 2026-11-02 stays closed. The
     * driving system plans along the route and does not choose it.
     */
    port routeOut : RouteOut;
  }

  part def AAOSSDVCoreGuest {
    doc /*
     * The SDV Core VM of the AAOS SDV guest, context of the loop: Android
     * under the guest host's KVM, with the SDV Core middleware. The SOME/IP
     * interop of SDV Core receives the operational-state events from
     * someipd and the Data Tunnel publishes them as the typed topic the IVI
     * VM subscribes to (decision 4). The guest owns its platform layers; the
     * SDV Core boundary model of packages/architecture is referenced and
     * bound to the middleware layer (the platform stack owns the guest,
     * owner decision of 2026-10-25); nothing of it is built by DE4SDV.
     */
    port someIpIn : OperationalStateIn;
    port topicOut : DataTunnelPort;
    part os : AndroidHLOS;
    part sdvMiddleware : AndroidSDVMiddleware;
    ref part sdvCore : SDVCoreBoundary;
    bind sdvCore = sdvMiddleware;
    bind someIpIn = sdvCore.someIp.someIpPort;
    connection operationalStateTopicPublishedByBroker connect sdvCore.someIp.topicPublishOut to sdvCore.dataTunnel.topicPublishPort;
    bind topicOut = sdvCore.dataTunnel.topicSubscribePort;
  }

  part def AAOSIVIGuest {
    doc /*
     * The IVI VM of the AAOS SDV guest, context of the loop: Android under the
     * guest host's KVM, with the SDV Gateway and the observer application of
     * phase 2 that presents the plan, the vehicle state and the health to the
     * driver. The observer subscribes to the typed topic through the SDV
     * Gateway and sends nothing to the driving system. The observer application
     * is a build item of the bench, named here, not claimed.
     */
    port topicIn : DataTunnelPort;
    part os : AndroidHLOS;
    part sdvGateway : SDVGatewayOnIVIBoundary;
    part stateObserver : DrivingStateObserverApplication {
      doc /*
       * The observer application of the bench, a build item named here, not
       * claimed. It presents the operational state and nothing else (owner
       * decision 2026-11-06): the plan with its producer, its production
       * time and the run record it names; the vehicle state sample with its
       * sample time; the health; the mode with the cause of a stop; and the
       * run identity. No camera images, no commands, no route; nothing
       * back. Its screen shows two clocks side by side, the simulation time
       * of the newest input and the wall-clock time of the publication, so
       * that no reading mixes the time domains; the screen's recording is
       * phase 10 evidence.
       */
      port operationalStateIn : OperationalStateIn;
    }
    bind topicIn = sdvGateway.dataTunnelPort;
    connection operationalStateThroughSDVGateway connect sdvGateway.clientPort to stateObserver.operationalStateIn;
  }

  part def ClosedLoopDrivingLinuxHost {
    doc /*
     * The S-CORE host of the bench (owner decision of 2026-11-09: three
     * hosts): x86_64 Linux with the planner's GPU, an NVIDIA RTX PRO 6000
     * class card that runs nothing else. It owns its platform layer, the
     * software realization of the driving system with its S-CORE services,
     * and the route provider. It nests no VM: the cloud's GPU hosts offer no
     * nested virtualization, so the AAOS SDV guests run on the guest host.
     * The camera stream, the ego motion and the simulation clock arrive from
     * the simulator host over the bench network, and the vehicle control
     * leaves for it; the operational state leaves on SOME/IP over the VXLAN
     * segment. Each exchange is handed to the host's own port by a named
     * delegation connection, which SysIDE draws as an edge between exposed
     * ports; flows between these ports were not drawn in six licensed runs
     * (42247403125 to 42253633791). Each port definition carries the one
     * item its exchange moves.
     */
    port cameraImagesIn : CameraStreamIn;
    port egoMotionIn : EgoMotionStreamIn;
    port simulationClockIn : SimulationClockIn;
    port vehicleControlOut : VehicleControlOut;
    port operationalStateOut : OperationalStateOut;
    part os : LinuxPlatform;
    part drivingSoftware : ClosedLoopDrivingSoftwareRealization;
    part routeProvider : ScenarioRouteProvider;
    connection cameraImagesDelegation connect cameraImagesIn to drivingSoftware.cameraImagesIn;
    connection egoMotionDelegation connect egoMotionIn to drivingSoftware.egoMotionIn;
    connection simulationClockDelegation connect simulationClockIn to drivingSoftware.simulationClockIn;
    connection routeFromScenario connect routeProvider.routeOut to drivingSoftware.routeIn;
    connection vehicleControlDelegation connect drivingSoftware.vehicleControlOut to vehicleControlOut;
    connection operationalStateDelegation connect drivingSoftware.operationalStateOut to operationalStateOut;
  }

  part def ClosedLoopDrivingSimulatorHost {
    doc /*
     * The simulator host of the bench (owner decision of 2026-11-09): x86_64
     * Linux with its own GPU for the simulator's rendering, so the simulator
     * never renders on the planner's card (a bench rule of 2026-11-09). It owns
     * its platform layer and the simulator server. The camera stream, the ego
     * motion and the simulation clock leave it, and the vehicle control enters
     * it, over the bench network to and from the S-CORE host: a private routed
     * link that carries the simulator's ports and nothing else. The chase view
     * of the recording is rendered here and encoded by the host's NVENC
     * hardware encoder, after one warm-up lap of the route in the same
     * simulator session: in the probe, the first lap of a session delayed the
     * camera streams once, by about 300 ms, at the same place of the route, and
     * the next lap did not.
     */
    port cameraStreamOut : CameraStreamOut;
    port egoMotionOut : EgoMotionStreamOut;
    port simulationClockOut : SimulationClockOut;
    port vehicleControlIn : VehicleControlIn;
    part os : LinuxPlatform;
    part carlaServer : CARLASimulationServer;
    connection cameraStreamDelegation connect carlaServer.cameraStreamOut to cameraStreamOut;
    connection egoMotionDelegation connect carlaServer.egoMotionOut to egoMotionOut;
    connection simulationClockDelegation connect carlaServer.simulationClockOut to simulationClockOut;
    connection vehicleControlDelegation connect vehicleControlIn to carlaServer.vehicleControlIn;
  }

  part def AAOSGuestHost {
    doc /*
     * The guest host of the bench (owner decision of 2026-11-09): x86_64
     * Linux with KVM for the two AAOS SDV guests and no GPU of the loop. It
     * owns its platform layer and the hypervisor; the guests run under it. A
     * VXLAN segment joins the S-CORE host to the guests' bridge, and the
     * S-CORE host takes 192.168.98.1 on it, the address the SDV Core guest's
     * SOME/IP configuration of INC-MW-011 expects for its peer, so the guest
     * images stay unchanged. It carries no element of the driving system
     * and no port of the loop.
     */
    part os : LinuxPlatform;
    part hypervisor : KVMHypervisor;
  }

  part def ClosedLoopDrivingPhysicalSystem {
    doc /*
     * The physical context of the bench: three hosts and the two AAOS SDV
     * guests (owner decision of 2026-11-09). The simulator's exchanges cross
     * the bench network between the simulator host and the S-CORE host. The
     * operational state crosses the VXLAN segment once on SOME/IP, from
     * someipd to the SDV Core VM, and the VMs once on the Data Tunnel, from
     * the SDV Core VM to the IVI VM. Nothing crosses back: the guests are
     * observers, under the guest host's KVM. The S-CORE host's inside is
     * drawn by the S-CORE path view; what crosses the realization's
     * boundary, on the bench side and on the observer side, by the context
     * exchange view.
     */
    part linuxHost : ClosedLoopDrivingLinuxHost;
    part simulatorHost : ClosedLoopDrivingSimulatorHost;
    part guestHost : AAOSGuestHost;
    part sdvCoreGuest : AAOSSDVCoreGuest;
    part hmiGuest : AAOSIVIGuest;
    interface sdvCoreGuestUnderKVM : OSHypervisorInterface
      connect sdvCoreGuest.os.hypervisorPort to guestHost.hypervisor.guestPort;
    interface hmiGuestUnderKVM : OSHypervisorInterface
      connect hmiGuest.os.hypervisorPort to guestHost.hypervisor.guestPort;
    connection cameraStreamOverBenchNetwork connect simulatorHost.cameraStreamOut to linuxHost.cameraImagesIn {
      doc /* The six camera streams from the simulator host to the agent's input activity, over the bench network. */
    }
    connection egoMotionOverBenchNetwork connect simulatorHost.egoMotionOut to linuxHost.egoMotionIn {
      doc /* The ego vehicle's motion state from the simulator host to the agent's input activity, over the bench network. */
    }
    connection simulationClockOverBenchNetwork connect simulatorHost.simulationClockOut to linuxHost.simulationClockIn {
      doc /* The world snapshot's simulation time from the simulator host to the actuation adapter, over the bench network. */
    }
    connection vehicleControlOverBenchNetwork connect linuxHost.vehicleControlOut to simulatorHost.vehicleControlIn {
      doc /* The vehicle control from the actuation adapter to the simulator host, over the bench network, and nothing else. */
    }
    connection operationalStateOverSOMEIPAcrossVXLANSegment connect linuxHost.operationalStateOut to sdvCoreGuest.someIpIn {
      doc /* The operational state on SOME/IP from someipd to the SDV Core VM's interop, over the VXLAN segment that joins the S-CORE host to the guests' bridge (guest images unchanged). */
    }
    connection operationalStateTopicOverDataTunnelAcrossVMs connect sdvCoreGuest.topicOut to hmiGuest.topicIn {
      doc /* The operational state as the Data Tunnel topic from the SDV Core VM to the IVI VM (its VSIDL message is GAP-DRIVING-006). */
    }
  }

  part closedLoopDrivingPhysicalSystem : ClosedLoopDrivingPhysicalSystem;

  part closedLoopDrivingSoftware : ClosedLoopDrivingSoftwareRealization {
    doc /*
     * Exists for the S-CORE path view, which draws usages: the same
     * realization as the host's drivingSoftware, not a second one. Drawn
     * from the host's usage, the view also drew the host's connections to
     * the realization's ports as boxes with two ends.
     */
  }

  /* ───────────── Logical-to-physical allocations (allocatedTo) ───────────── */

  allocation inputConditionerToConditionInputs allocate ClosedLoopDrivingLogicalSystem::inputConditioner to closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::drivingAgent::conditionInputs;
  allocation plannerToInferPlan allocate ClosedLoopDrivingLogicalSystem::planner to closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::drivingAgent::inferPlan;
  allocation loopSupervisorToSuperviseLoop allocate ClosedLoopDrivingLogicalSystem::loopSupervisor to closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::drivingAgent::superviseLoop;
  allocation vehicleCommanderToCommandVehicle allocate ClosedLoopDrivingLogicalSystem::vehicleCommander to closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::drivingAgent::commandVehicle;
  allocation actuationGatewayToActuationAdapter allocate ClosedLoopDrivingLogicalSystem::actuationGateway to closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::actuationAdapter;
  allocation statePublisherToPublisherApplication allocate ClosedLoopDrivingLogicalSystem::statePublisher to closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::statePublisherApplication;
  allocation statePublisherToGatewayd allocate ClosedLoopDrivingLogicalSystem::statePublisher to closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::scoreServices::gatewayd;
  allocation statePublisherToSomeipd allocate ClosedLoopDrivingLogicalSystem::statePublisher to closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::scoreServices::someipd;

  /* ───────────── System-to-software signal mappings (the method's phase 8 exit rule) ─────────────
   * One per crossing of an information item into a software contract, each
   * with its record. A mapping is no runtime-interoperability claim. The
   * owning allocation targets the port where the item enters the contract,
   * written as a feature chain through the usage (the ports are declared on
   * the definitions, so a qualified name would resolve to the definition's
   * port, outside the realizing usage); the typed ports and the connections
   * give the other endpoints.
   */

  allocation cameraImagesIngressMapping : SystemToSoftwareSignalMappingCandidate
    allocate ClosedLoopDrivingLogicalSystem::inputConditioner
    to closedLoopDrivingPhysicalSystem.linuxHost.drivingSoftware.drivingAgent.conditionInputs.cameraImagesIn {
    item <'MAP-DRIVING-CAMERA-IMAGES'> cameraImagesIngressMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The camera images from the simulator's camera sensors into the input
       * activity: the ingress of the loop through the simulator client. The
       * checkpoint's camera geometry and history (REQ-DRIVING-003 to -005)
       * are the receiving contract; the frames themselves are no vehicle
       * signal.
       */
      attribute :>> semanticSource = "camera images of the ego vehicle's cameras, rendered by the simulator: image frames, no vehicle signal, so no VSS typing applies; the receiving contract is the input geometry of the pinned checkpoint";
      attribute :>> softwareContractArtifact = "in: the simulator client library's camera sensor stream (sensor data callbacks on the client's threads), candidate, at the simulator release and step that section 1 of implementation/closed-loop-driving-bench/interfaces/ICD.md names; out: the checkpoint inputs on the agent's FEO topic, candidate";
      attribute :>> softwareContractMessage = "in: one image measurement per camera per sensor tick with its frame number and simulation timestamp, candidate; out: the camera history tensor of the checkpoint inputs, candidate";
      attribute :>> softwareContractField = "in: raw image buffer, width, height, field of view, timestamp, exact per the client library; out: the history slot of each camera in the checkpoint's input layout, candidate";
      attribute :>> dataTypeAndUnit = "in: 8-bit BGRA pixels per camera, simulation seconds for the timestamp; out: the checkpoint's normalized image tensor, no unit";
      attribute :>> timingQualityAndState = "one frame per camera per 100 ms of simulation time (REQ-DRIVING-001); a frame is marked with its capture time (REQ-DRIVING-030) and enters a history once (REQ-DRIVING-010); a missing or late frame sets the input condition (REQ-DRIVING-023)";
      attribute :>> transformationRule = "projection of each image into the checkpoint's camera geometry and history layout (REQ-DRIVING-003 to -005), defined by the pinned source revision; no retiming of the simulation";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "bring the verification cases of REQ-DRIVING-003 to -005, -010 and -023 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; framing gap gapModelInputAndFeedback (camera calibration and history priming)";
    }
  }

  allocation egoMotionSampleMapping : SystemToSoftwareSignalMappingCandidate
    allocate ClosedLoopDrivingLogicalSystem::inputConditioner
    to closedLoopDrivingPhysicalSystem.linuxHost.drivingSoftware.drivingAgent.conditionInputs.egoMotionSampleOut {
    item <'MAP-DRIVING-EGO-MOTION'> egoMotionSampleMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The ego motion from the simulator's vehicle state through the input
       * activity to the typed sample the vehicle commander and the state
       * publisher take. The owning allocation targets the typed port; its
       * item EgoMotionSamplePayload types speed, longitudinal and lateral
       * acceleration and yaw rate with COVESA VSS (decision 5). The
       * checkpoint takes the history's yaw rate and curvature as zero
       * (GAP-DRIVING-010) and its speed and acceleration worked out from the
       * vehicle's poses, not from the sample (REQ-DRIVING-008).
       */
      attribute :>> semanticSource = "the motion state of the ego vehicle as the simulator reports it (its transform, velocity and acceleration vectors, angular velocity) and, out, the sample typed by COVESA VSS at the port: Vehicle_Speed [km/h], Vehicle_Acceleration_Longitudinal and _Lateral [m/s^2], Vehicle_AngularVelocity_Yaw [deg/s]";
      attribute :>> softwareContractArtifact = "in: the simulator client library's actor state of the ego vehicle, candidate; out: the agent's FEO topic for the vehicle commander and the mw::com event for the state publisher (the ego-motion sample event in section 2 of implementation/closed-loop-driving-bench/interfaces/ICD.md; payload EgoMotionSamplePayload in implementation/closed-loop-driving-bench/interfaces/include/de4sdv/driving/payloads.h), candidate";
      attribute :>> softwareContractMessage = "in: transform, velocity, acceleration and angular velocity of the ego vehicle per world snapshot, candidate; out: EgoMotionSamplePayload with its capture time, candidate";
      attribute :>> softwareContractField = "in: the transform's world matrix, velocity.x/y, acceleration.x/y, angular_velocity.z, snapshot timestamp, exact per the client library; out: speed, longitudinalAcceleration, lateralAcceleration, yawRate, captureTime, exact";
      attribute :>> dataTypeAndUnit = "in: float32 m (the transform), m/s, m/s^2, deg/s, simulation seconds; out: speed : Vehicle_Speed km/h, accelerations : Vehicle_Acceleration_* m/s^2, yawRate : Vehicle_AngularVelocity_Yaw deg/s, captureTime simulation seconds; inside the agent the checkpoint takes speed in m/s, and yaw rate and curvature as zero (GAP-DRIVING-010)";
      attribute :>> timingQualityAndState = "one sample per 100 ms step, marked with its capture time (REQ-DRIVING-030); the sample history of the run has no record twice (REQ-DRIVING-010); a missing or implausible sample sets the input condition (REQ-DRIVING-024); the publisher receives the same sample within 100 ms of wall-clock time (REQ-DRIVING-016)";
      attribute :>> transformationRule = "speed = |velocity| * 3.6 as the VSS km/h value; the checkpoint's history takes speed and acceleration worked out the source's way from the transforms, moved to the origin of the camera rig, of the 66 steps that end at the step (REQ-DRIVING-008), with yaw rate and curvature 0 (GAP-DRIVING-010), in the layout of the pinned source revision's ego-motion history";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "bring the verification cases of REQ-DRIVING-008, -010, -016 and -024 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; GAP-DRIVING-003 (the reference's ego-motion conventions)";
    }
  }

  allocation routeIngressMapping : SystemToSoftwareSignalMappingCandidate
    allocate ClosedLoopDrivingLogicalSystem::inputConditioner
    to closedLoopDrivingPhysicalSystem.linuxHost.drivingSoftware.drivingAgent.conditionInputs.routeIn {
    item <'MAP-DRIVING-ROUTE'> routeIngressMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The route of the scenario from the route provider into the input
       * activity, where it becomes the route mask raster of the checkpoint
       * inputs (REQ-DRIVING-007). A route is no vehicle signal.
       */
      attribute :>> semanticSource = "the route to the scenario's destination as a sequence of map waypoints, from the scenario configuration on the host: route and map data, no vehicle signal";
      attribute :>> softwareContractArtifact = "in: the scenario's route file read by the route provider at the start of the run, and the route announcement the provider sends to the input activity (section 9 of implementation/closed-loop-driving-bench/interfaces/ICD.md), candidate; out: the route mask raster in the checkpoint inputs on the agent's FEO topic, candidate";
      attribute :>> softwareContractMessage = "in: an ordered list of waypoints in the map frame, candidate; out: the route mask and map context rasters of the checkpoint's input layout, candidate";
      attribute :>> softwareContractField = "in: waypoint x, y, heading and road id, candidate; out: the raster channels the pinned source revision defines, candidate";
      attribute :>> dataTypeAndUnit = "in: float32 metres and radians in the map frame; out: the checkpoint's raster tensors, no unit";
      attribute :>> timingQualityAndState = "read once per run before the first plan and announced to the input activity again at a fixed period of simulation time, so that a route that stops arriving grows old; the raster is recomputed per step from the ego pose; a route more than 1 s of simulation time old, a route the ego vehicle has left or a missing route sets the input condition (REQ-DRIVING-025)";
      attribute :>> transformationRule = "rasterization of the route and the map context into the ego frame of each step (REQ-DRIVING-006, -007), as the pinned source revision defines it";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "bring the verification cases of REQ-DRIVING-006, -007 and -025 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; framing gap gapModelInputAndFeedback (coordinate frames)";
    }
  }

  allocation planMapping : SystemToSoftwareSignalMappingCandidate
    allocate ClosedLoopDrivingLogicalSystem::planner
    to closedLoopDrivingPhysicalSystem.linuxHost.drivingSoftware.drivingAgent.inferPlan.planEventOut {
    item <'MAP-DRIVING-PLAN'> planMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The plan from the inference engine's output to the FEO topic the
       * loop supervision reads and the mw::com event the state publisher
       * takes. The owning allocation targets the event port; the FEO topic
       * is the same item one hop earlier. A plan is no vehicle signal.
       */
      attribute :>> semanticSource = "the trajectory the pinned checkpoint predicts for the next planning horizon, in the ego frame, with its producer, its production time and the run record it names: a plan, no vehicle signal";
      attribute :>> softwareContractArtifact = "in: the output tensors of the planning stack, PyTorch over the pinned checkpoint in the agent's process, candidate; out: the agent's FEO topic for the loop supervision and the mw::com plan event for the state publisher (the plan event in section 2 of implementation/closed-loop-driving-bench/interfaces/ICD.md; payload DrivingPlanPayload in implementation/closed-loop-driving-bench/interfaces/include/de4sdv/driving/payloads.h), candidate";
      attribute :>> softwareContractMessage = "in: the checkpoint's output layout (trajectory samples over the horizon), exact per the pinned source revision; out: DrivingPlan with producer, production time and run record, candidate";
      attribute :>> softwareContractField = "in: the 64 pairs of acceleration and curvature of the output head, exact per the pinned source revision; out: samples (each with its pair and the pose of the plan's path at it), horizon, producer, productionTime, runRecord, candidate";
      attribute :>> dataTypeAndUnit = "in: float32 m/s^2 and 1/m; out: the same, metres and radians for the pose of the path, and wall-clock seconds for the production time";
      attribute :>> timingQualityAndState = "one plan per 100 ms step, no two consecutive steps without one (REQ-DRIVING-001), produced within 100 ms of wall-clock time after the newest image (REQ-DRIVING-013), stamped (REQ-DRIVING-031), published for observation within 100 ms (REQ-DRIVING-015); no plan while the checkpoint identity fails (REQ-DRIVING-035)";
      attribute :>> transformationRule = "identity on the 64 pairs; each sample also carries the pose of the plan's path: the pairs integrated the way the pinned source revision integrates them, from the newest speed of the motion history of the step, in the vehicle frame of the step (x forward, y to the left); the plan names the run record (REQ-DRIVING-034); the planning stack's numerical parity with the unmodified reference is GAP-DRIVING-003";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "bring the verification cases of REQ-DRIVING-001, -013, -015 and -031 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; GAP-DRIVING-003, framing gap gapClosedLoopPerformance (the planning times of the runs are in GAP-DRIVING-013)";
    }
  }

  allocation modeMapping : SystemToSoftwareSignalMappingCandidate
    allocate ClosedLoopDrivingLogicalSystem::loopSupervisor
    to closedLoopDrivingPhysicalSystem.linuxHost.drivingSoftware.drivingAgent.superviseLoop.modeEventOut {
    item <'MAP-DRIVING-MODE'> modeMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The mode of the loop from the loop supervision to the vehicle
       * commander (an FEO topic, with the newest valid plan beside it) and
       * to the state publisher (an mw::com event). A mode is no vehicle
       * signal.
       */
      attribute :>> semanticSource = "the mode the loop supervision decides each step: starting, driving, or stopped with its cause (degraded camera images, motion or route, a stale or invalid plan, a refused checkpoint); a system state, no vehicle signal";
      attribute :>> softwareContractArtifact = "in: the plan and the input condition on the agent's FEO topics, candidate; out: the mode and the valid plan on FEO topics for the vehicle commander and the mw::com mode event for the state publisher (the mode event in section 2 and the causes in section 4 of implementation/closed-loop-driving-bench/interfaces/ICD.md; payload DrivingModePayload and the enumerations Mode and Cause in implementation/closed-loop-driving-bench/interfaces/include/de4sdv/driving/payloads.h), candidate";
      attribute :>> softwareContractMessage = "out: DrivingMode with the cause and the decision time, candidate";
      attribute :>> softwareContractField = "out: mode, cause, decisionTime, candidate";
      attribute :>> dataTypeAndUnit = "out: an enumeration for the mode and the cause, wall-clock seconds for the decision time; no unit";
      attribute :>> timingQualityAndState = "decided once per step; the first cause of a stop holds for the rest of the run; the stop response is published with its cause within 100 ms of wall-clock time of its start (REQ-DRIVING-029); the newest valid plan is stale when it is more than 300 ms of simulation time old at a command (REQ-DRIVING-026)";
      attribute :>> transformationRule = "state rule: starting until the first valid plan; then the input condition of REQ-DRIVING-023 to -025, a stale plan (REQ-DRIVING-026) or an invalid plan (REQ-DRIVING-027) gives the stop response with that cause, and standstill after it (REQ-DRIVING-022); a refused checkpoint gives refused from the start (REQ-DRIVING-035); otherwise driving. A plan that misses the planning period of REQ-DRIVING-013 gives no stop: the stop on a late plan is that of the stale plan. The enumerations of the contract have five modes (starting, driving, stop response, standstill, refused) and, beside none, one cause for each limit of REQ-DRIVING-023 to -028 and -035 and one for the orderly end of a run";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "bring the verification cases of REQ-DRIVING-023 to -027 and -029 to evidence of record; none is started; the mode and the cause are not typed in this model yet";
      attribute :>> evidenceOrGap = "no runtime evidence of record; the actuation-side stop reaches the publisher on MAP-DRIVING-ACTUATION-STATE, not on this path";
    }
  }

  allocation commandMapping : SystemToSoftwareSignalMappingCandidate
    allocate ClosedLoopDrivingLogicalSystem::vehicleCommander
    to closedLoopDrivingPhysicalSystem.linuxHost.drivingSoftware.drivingAgent.commandVehicle.commandOut {
    item <'MAP-DRIVING-COMMAND'> commandMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The command from the vehicle commander to the actuation adapter on
       * the mw::com event: the hop REQ-DRIVING-014 constrains between
       * processes. The owning allocation targets the typed port; its item
       * VehicleMotionCommandPayload types the acceleration and the steering
       * angle by the two DE4SDV_VSS_Extensions candidates of decision 5.
       */
      attribute :>> semanticSource = "the commanded longitudinal acceleration and front-wheel steering angle computed from the newest valid plan and the current motion (REQ-DRIVING-011), typed at the port by Vehicle_ADAS_Driving_Command_Acceleration [m/s^2] and Vehicle_ADAS_Driving_Command_SteeringAngle [degrees], DE4SDV candidates absent from the pinned VSS snapshot";
      attribute :>> softwareContractArtifact = "out: the mw::com command event from the agent to the actuation adapter (the command event in section 2 of implementation/closed-loop-driving-bench/interfaces/ICD.md; payload VehicleMotionCommandPayload in implementation/closed-loop-driving-bench/interfaces/include/de4sdv/driving/payloads.h; the vehicle configuration that names the command law in its section 5), candidate; S-CORE communication and nothing beside it (REQ-DRIVING-014)";
      attribute :>> softwareContractMessage = "out: VehicleMotionCommandPayload, one event per command, candidate";
      attribute :>> softwareContractField = "out: acceleration, steeringAngle, productionTime, planReference, exact";
      attribute :>> dataTypeAndUnit = "out: acceleration float m/s^2 (negative decelerates), steeringAngle float degrees (positive to the left, the sign of Vehicle_Chassis_SteeringWheel_Angle), productionTime wall-clock seconds, planReference string";
      attribute :>> timingQualityAndState = "one command per step from the newest valid plan (REQ-DRIVING-011), stamped (REQ-DRIVING-032); in the stop response a deceleration of 4 m/s^2 with the steering angle held until standstill (REQ-DRIVING-020 to -022); the adapter treats 200 ms of simulation time without a valid command as loss (REQ-DRIVING-028)";
      attribute :>> transformationRule = "plan to command, at the control horizon, the sample of the plan for the step of the command: the acceleration is the plan's acceleration there; the steering angle is pure pursuit of the plan's path (MAP-DRIVING-PLAN), read with the vehicle at its origin: the target is the first sample after the control horizon that lies at least the lookahead from the origin, the lookahead is 4 m plus 0.8 s times the speed of the vehicle, kept within 4 m and 15 m, and the front-wheel angle is that of the arc from the origin through the target, by the wheelbase the configuration names; both clipped to the vehicle limits it names (REQ-DRIVING-012). The law of the first design, the plan's curvature at the control horizon turned into a front-wheel angle by the wheelbase, stays selectable in the configuration and is not the shipped one: it steered to the right in every command of the two closed-loop runs made with it, where pure pursuit of the same plans asks for almost no steering. The conversion is the control part of the framing gap gapModelInputAndFeedback";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "bring the verification cases of REQ-DRIVING-011, -012, -014, -020 to -022 and -032 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; GAP-DRIVING-001 (the agent's framework); the in-process hops before this one are not under REQ-DRIVING-014 (owner reading 2026-11-06)";
    }
  }

  allocation vehicleControlMapping : SystemToSoftwareSignalMappingCandidate
    allocate ClosedLoopDrivingLogicalSystem::actuationGateway
    to closedLoopDrivingPhysicalSystem.linuxHost.drivingSoftware.actuationAdapter.vehicleControlOut {
    item <'MAP-DRIVING-VEHICLE-CONTROL'> vehicleControlMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The command from the actuation adapter into the simulator's vehicle
       * control: the boundary item leaves the driving system here and enters
       * the simulator client's contract. The stop response of
       * REQ-DRIVING-028 is applied on this port.
       */
      attribute :>> semanticSource = "the vehicle command applied at the simulated actuation: the simulator's VehicleControl (throttle, brake, steer), a simulator actuation contract, no vehicle signal; the commanded quantities it realizes are the two extension candidates of MAP-DRIVING-COMMAND";
      attribute :>> softwareContractArtifact = "in: the mw::com command event, candidate; out: the simulator client library's vehicle control applied to the ego vehicle, candidate, at the simulator release that section 1 of implementation/closed-loop-driving-bench/interfaces/ICD.md names, by the conversion of its section 5";
      attribute :>> softwareContractMessage = "out: VehicleControl per applied command, candidate";
      attribute :>> softwareContractField = "out: throttle, brake, steer, exact per the client library";
      attribute :>> dataTypeAndUnit = "out: throttle and brake float 0..1, steer float -1..1, no unit; in: m/s^2 and degrees";
      attribute :>> timingQualityAndState = "applied on arrival, once per command; the simulation time of the world snapshot is read with each application; after 200 ms of simulation time without a valid command the adapter applies the stop response itself (REQ-DRIVING-028) and holds it until standstill (REQ-DRIVING-022)";
      attribute :>> transformationRule = "acceleration to throttle or brake by the vehicle's longitudinal response the configuration names, steering angle to the normalized steer by its maximum steering angle, both clipped (REQ-DRIVING-012); the stop response maps 4 m/s^2 of deceleration to a brake value (REQ-DRIVING-020); the conversion is the actuation part of the framing gap gapModelInputAndFeedback";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "identify the vehicle's longitudinal response on the simulator release in a calibration run: the table of the shipped vehicle configuration is a placeholder; then bring the verification cases of REQ-DRIVING-012, -020 to -022 and -028 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; the stop applied here is published through MAP-DRIVING-ACTUATION-STATE";
    }
  }

  allocation actuationStateMapping : SystemToSoftwareSignalMappingCandidate
    allocate ClosedLoopDrivingLogicalSystem::actuationGateway
    to closedLoopDrivingPhysicalSystem.linuxHost.drivingSoftware.actuationAdapter.actuationStateOut {
    item <'MAP-DRIVING-ACTUATION-STATE'> actuationStateMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The actuation state from the actuation adapter to the state publisher,
       * an mw::com event off the loop: the amendment of 2026-11-06 that gives
       * the adapter's own stop (REQ-DRIVING-028) its path to the publication
       * of REQ-DRIVING-029. A state of the actuation, no vehicle signal.
       */
      attribute :>> semanticSource = "the actuation state the adapter reports each step: the command it applied with its actuation time in simulation time, or that its own stop response is in force, since when and why (no valid command for 200 ms of simulation time, REQ-DRIVING-028): a system state, no vehicle signal";
      attribute :>> softwareContractArtifact = "in: the applied vehicle control and the world snapshot's simulation time inside the adapter; out: the mw::com actuation-state event for the state publisher (the actuation state event in section 2 of implementation/closed-loop-driving-bench/interfaces/ICD.md; payload ActuationStatePayload in implementation/closed-loop-driving-bench/interfaces/include/de4sdv/driving/payloads.h), candidate";
      attribute :>> softwareContractMessage = "out: ActuationState with the applied command or the stop in force, its cause and the actuation time, candidate";
      attribute :>> softwareContractField = "out: applied, acceleration, steeringAngle, actuationTime, stopInForce, stopSince, cause, candidate";
      attribute :>> dataTypeAndUnit = "out: a flag for applied, the command's m/s^2 and degrees, simulation-time seconds for the times, an enumeration for the cause; no unit";
      attribute :>> timingQualityAndState = "published once per applied command and once when the stop response begins; the publisher publishes the stop with its cause within 100 ms of wall-clock time of that event (REQ-DRIVING-029); one way, the publisher sends nothing back (REQ-DRIVING-018, -019)";
      attribute :>> transformationRule = "state rule: a valid command applied gives applied with its time; 200 ms of simulation time without a valid command gives the stop in force with the cause lost commands and the time it began (REQ-DRIVING-028); the publisher merges it with the mode of MAP-DRIVING-MODE into the one stop publication";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "bring the verification cases of REQ-DRIVING-028 and -029 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record";
    }
  }

  allocation operationalStateMapping : SystemToSoftwareSignalMappingCandidate
    allocate ClosedLoopDrivingLogicalSystem::statePublisher
    to closedLoopDrivingPhysicalSystem.linuxHost.drivingSoftware.scoreServices.someipd.operationalStateOut {
    item <'MAP-DRIVING-OPERATIONAL-STATE'> operationalStateMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The operational state on the observation path, hop by hop: the
       * publisher's mw::com event, gatewayd to someipd over the gateway's
       * IPC, SOME/IP over the VXLAN segment into the SOME/IP interop of SDV
       * Core, the Data Tunnel topic to the SDV Gateway on the IVI VM, the
       * observer. One mapping covers the processes of the chain; the owning
       * allocation targets someipd's port, where the item leaves the host.
       * The topic is typed (decision 4); INC-MW-011 proved opaque frames.
       */
      attribute :>> semanticSource = "the operational state of the driving system for observation: the plan, the motion sample and the health, each with producer and time, and the stop with its cause; a system state publication, no vehicle signal, though the motion sample inside it carries the VSS-typed fields of MAP-DRIVING-EGO-MOTION";
      attribute :>> softwareContractArtifact = "in: the mw::com operational-state event from the publisher (the operational state event in section 2 of implementation/closed-loop-driving-bench/interfaces/ICD.md), candidate; gatewayd and someipd of the SOME/IP gateway at d9eac670 with the service, instance and event ids and the message fields of its section 3, candidate; out: the SOME/IP service of the driving operational state and the Data Tunnel topics of SDV Core, typed by the message of implementation/closed-loop-driving-bench/ivi-observer/contract/de4sdv_driving_operational_state.proto through the mapping of implementation/closed-loop-driving-bench/ivi-observer/interop/de4sdv_driving_operational_state.vsidl (GAP-DRIVING-006), candidate";
      attribute :>> softwareContractMessage = "one SOME/IP service with three events, plan, vehicle state and health, mapped onto one VSIDL message DrivingOperationalState with a kind field, candidate; three Data Tunnel topics of that message type, one per event";
      attribute :>> softwareContractField = "kind, producer, time, and per kind the plan samples, the motion sample fields or the health with the mode and its cause, candidate";
      attribute :>> dataTypeAndUnit = "the plan's metres and radians, the sample's VSS units, an enumeration for the health and the cause, wall-clock seconds for the time; the SOME/IP payload is the SOME/IP serialization of the message's fields in their order, which the SOME/IP interop of SDV Core translates into the VSIDL message";
      attribute :>> timingQualityAndState = "the plan within 100 ms of its production (REQ-DRIVING-015), the motion sample within 100 ms of its receipt (REQ-DRIVING-016), the health at least every 200 ms also without a plan (REQ-DRIVING-017), the stop with its cause within 100 ms (REQ-DRIVING-029); whether the guest receives on time, late or not at all changes no plan (REQ-DRIVING-018, -019): the publisher has no port into the agent";
      attribute :>> transformationRule = "serialization to the VSIDL message at the SOME/IP interop of SDV Core; no value changes on the path; the discard and ordering behaviour of the chain is INC-MW-011's (GAP-MW-037, GAP-MW-045)";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "bring the verification cases of REQ-DRIVING-015 to -019 and -029 to evidence of record; none is started; the fields of the message are not typed in this model yet";
      attribute :>> evidenceOrGap = "no runtime evidence of record; GAP-DRIVING-006 (typed topic), INC-MW-011's GAP-MW-038 (SOME/IP on the guest untested)";
    }
  }

  /* ───────────── What phase 8 settled on the framing's gaps ───────────── */

  comment phase8TransportSettled about gapTransportAndControl
    /*
     * Settled: S-CORE is on the functional path. The plan goes from the
     * inference to the supervision and the commander inside one FEO agent,
     * the command to the actuation adapter on an mw::com event, the
     * actuation adapter alone touches the simulator's vehicle control: no
     * planner-to-simulator bypass exists. AAOS SDV consumes the plan, the
     * vehicle state and the health as a typed Data Tunnel topic over the
     * gateway chain; the observer sends nothing back. Open: the contract
     * ids and the VSIDL message (phase 10); the actuation-side stop reaches
     * the publisher since the amendment of 2026-11-06
     * (MAP-DRIVING-ACTUATION-STATE); the in-process hops are settled by the
     * owner's reading (reqPlansAndCommandsOverSCOREReading).
     */

  comment reqPlansAndCommandsOverSCOREReading about reqPlansAndCommandsOverSCORE, DrivingAgentApplication
    /*
     * The owner's reading of REQ-DRIVING-014 (2026-11-06): the requirement
     * constrains the hops between processes from planning to the actuation,
     * and the one on this path is the command event from the agent to the
     * actuation adapter, mw::com. The topics inside the agent's process
     * (checkpoint inputs, input condition, plan, valid plan, mode and the
     * ego-motion sample on FEO's communication layer) are no hops between
     * processes, and REQ-DRIVING-014 does not constrain them. The placement
     * stands; the phase 10 case logs them as FEO topics. This closed the
     * phase 8 gap that asked the question; ALT-DRIVING-PLAINAPPS-001 and
     * ALT-DRIVING-FEOMWCOM-001 stay alternatives on other grounds.
     */

  comment phase8ConversionPlacement about gapModelInputAndFeedback
    /*
     * Placed, not closed: the input side of the gap (camera geometry,
     * coordinate frames, history priming, time alignment) sits in the input
     * activity (MAP-DRIVING-CAMERA-IMAGES, -EGO-MOTION, -ROUTE); the control
     * side, plan to acceleration and steering angle, in the vehicle command
     * activity (MAP-DRIVING-COMMAND); the actuation side, acceleration and
     * steering angle to throttle, brake and steer, in the actuation adapter
     * (MAP-DRIVING-VEHICLE-CONTROL). The conversions are designed and
     * measured in phase 10.
     */

  /* ───────────── Assumptions and gaps of the realization ───────────── */

  part <'ASM-DRIVING-001'> asmFixedOrderCycleCarriesTheLoop : IncrementAssumption {
    doc /*
     * The fixed-execution-order cycle of FEO v1.0.5 with DE4SDV's event
     * trigger can host the loop: four activities with startup, step and
     * shutdown, each a Rust shell over C++ libraries, run in the order of
     * the loop once per camera frame at 10 Hz of simulation time, the
     * trigger taking the newest frame and counting the frames it skipped,
     * with the step of the inference activity inside the 100 ms wall-clock
     * budget of REQ-DRIVING-013 beside the three others. The readiness
     * probes measured the parts apart: the patched scheduler ran one chain
     * per external event, Rust and C++ activities built against the v0.10.0
     * modules, and planning took a median of 90 to 91 ms per plan on a card
     * of its own in the closed loop, which leaves the three other
     * activities less than 10 ms. The agent as one program is unmeasured
     * until phase 10. If it fails, the fallback is ALT-DRIVING-PLAINAPPS-001.
     */
  }

  part <'ASM-DRIVING-002'> asmPlannerStackStandsForTheCheckpoint : IncrementAssumption {
    doc /*
     * The planning stack's output equals the unmodified reference's output
     * over the pinned checkpoint on the same recorded inputs within a
     * tolerance phase 10 fixes against the deployed precision, so that a
     * plan made by the stack is a plan made by inference of the pinned
     * checkpoint (REQ-DRIVING-002), and the run identity records the
     * checkpoint's SHA-256 and the AutoE2E source revision with DE4SDV's
     * kernel changes (REQ-DRIVING-033). The stack is PyTorch over the
     * checkpoint with changes that alter rounding only: in the readiness
     * probe its fp32 output stayed within 9.83e-05 of the reference, and its
     * bf16 output differed from the fp32 reference by 6.49e-03 on average
     * and 1.68e-02 at most, against 6.21e-03 and 1.60e-02 for the unmodified
     * code's own bf16 rounding. Until phase 10 measures it on the bench this
     * is an assumption with GAP-DRIVING-003 behind it, not a result.
     */
  }

  part <'ASM-DRIVING-003'> asmSimulatorClientsInsideSCOREApplications : IncrementAssumption {
    doc /*
     * Two simulator clients coexist with the S-CORE applications on the
     * S-CORE host and reach the simulator host over the bench network: the
     * agent's input activity receives the sensor streams on the client
     * library's threads and reads the newest measurement in its step; the
     * actuation adapter applies the vehicle control and reads the world
     * snapshot through a second connection. The simulator runs in
     * synchronous mode and only the world-side pacer of the bench ticks it,
     * so neither client ticks the world and the two connections do not
     * interfere. The readiness probe linked the client library into an
     * S-CORE application with one C++ standard library. The clients are the
     * bench's; in a vehicle the camera driver and the actuation interface
     * would stand there.
     */
  }

  part <'ASM-DRIVING-004'> asmSimulatedSensorsStandForTheVehicles : IncrementAssumption {
    doc /*
     * The simulated sensor rig stands for the vehicle's sensors: the camera
     * images are rendered by the simulator at the rig profile's geometry,
     * not captured by a camera, and the ego-motion samples are the
     * simulator's vehicle state, ground truth without the noise, the bias
     * and the latency of an inertial measurement unit and a wheel odometry.
     * The loop and its evidence are proven on these inputs; what the proof
     * says about a vehicle's camera and motion sensors is outside this
     * increment, which claims no on-road behavior. Where the profile's
     * principal point is offset from the image centre the simulated
     * cameras use, the offset is recorded with the pinned checkpoint in
     * phase 10 (the owner's sensing decision of 2026-11-06). On the nuPlan
     * profile the readiness probe placed the six cameras within 0.01 mm and
     * 0.0001 degrees of the profile's poses; square pixels cannot reproduce
     * the profile's unequal focal lengths at 1920×1080, so each camera
     * renders 1920×963 at the horizontal focal length, and the image
     * squashed to the checkpoint's 512×512 tile keeps the profile's tile
     * focal lengths within 0.15 px, its principal point 9.73 px off.
     */
  }

  part <'GAP-DRIVING-001'> gapFEOOutsideReleasedBaseline : IncrementGap {
    doc /*
     * Open: FEO is not in the known_good.json of reference_integration
     * v0.10.0, the baseline the owner pinned (C). It is consumed as v1.0.5
     * (313b3d849c17881d3a11b6bf62aa2afab6565ef0, released 2026-02-19,
     * Apache-2.0, not vendored) with one DE4SDV patch, the event trigger of
     * the owner's decision (a) of 2026-11-07, which DE4SDV keeps until
     * upstream offers the mode. Its module file pins its own tooling
     * versions; beside the v0.10.0 modules it builds only with eight
     * single_version_override entries that force the reference
     * integration's pins (readiness probe of 2026-11-07), and its default
     * build applies a lint aspect that fetches a toolchain from the
     * network. FEO's topics are Rust-only at the pin, so the activities are
     * Rust shells over C++ libraries. FEO's release note states that it is
     * not released for production and has no safety argumentation. Failure
     * re-scopes to ALT-DRIVING-PLAINAPPS-001; losing the patch, to
     * ALT-DRIVING-FEOGATE-001.
     */
    attribute :>> disposition = LifecycleDisposition::deferred;
  }

  part <'GAP-DRIVING-003'> gapPlannerStackParityUnproven : IncrementGap {
    doc /*
     * Open: the planner runs the pinned checkpoint on PyTorch in the agent's
     * process (the engine decision of 2026-11-08); its ONNX export exhausted 64
     * GB of host memory in the exporter's graph passes without reporting an
     * unsupported operator, so no export exists and none is planned for this
     * increment. What stays open is the parity of the planning stack, the
     * checkpoint with DE4SDV's rounding-level kernel changes on the pinned
     * libraries, with the unmodified reference on the bench: the tolerance
     * against the deployed precision, the recorded inputs it is measured on,
     * and the pin of the stack's source in the run identity. REQ-DRIVING-035
     * refuses to plan from a checkpoint the configuration does not name.
     * Checkpoint and data terms stay open (framing gap gapAdoptionAndRights).
     */
    attribute :>> disposition = LifecycleDisposition::deferred;
  }

  part <'GAP-DRIVING-006'> gapTypedOperationalStateTopicUnproven : IncrementGap {
    doc /*
     * Open: decision 4 takes the production path with a typed topic, a
     * VSIDL message for the driving operational state published by the Data
     * Tunnel of SDV Core from the SOME/IP interop and consumed by the
     * observer through the SDV Gateway on the IVI VM. INC-MW-011 proved the
     * chain for opaque frames on the AEBS member, not for a typed message;
     * the SOME/IP stack on the AAOS guest is untested there too (GAP-MW-038).
     * Which VSIDL types the interop maps, how the three publications share
     * one message, and whether the observer application can be built
     * against the pinned AAOS SDV revision is phase 10 work with its own
     * readiness probe. A readiness probe carried INC-MW-011's opaque frame
     * between two hosts into the AEBS observer of an IVI VM, which leaves
     * the typed message as the open part.
     */
    attribute :>> disposition = LifecycleDisposition::deferred;
  }

  part <'GAP-DRIVING-007'> gapThreeHostBenchUnjoined : IncrementGap {
    doc /*
     * Open: the bench is three hosts (owner decision of 2026-11-09): the
     * S-CORE host with the planner's GPU, the simulator host with its own
     * GPU and the guest host with KVM for the two AAOS SDV guests, cloud
     * machines provisioned under the owner's campaign authorization; the
     * framing's gapBoundedCloudCampaign governs the spend. The readiness
     * probes ran them in pairs: the simulator host with the S-CORE host's
     * planner, and the SOME/IP gateway with the guests over a VXLAN segment
     * between two hosts of one region. The three hosts have not run in one
     * session, the VXLAN segment from the S-CORE host to the guest host
     * crosses two regions untested, and the hosts exist only while the
     * campaign keeps them. Nothing here launches compute.
     */
    attribute :>> disposition = LifecycleDisposition::deferred;
  }
  part <'GAP-DRIVING-010'> gapClosedLoopHistoryFeedback : IncrementGap {
    doc /*
     * Open, and accepted as a known limit: the bounded deviation of
     * asmSourceAuthenticity (owner decision of 2026-11-09). Fed its own yaw
     * rate and curvature history in the closed loop, the pinned checkpoint
     * turns its plans away from the lane within seconds. Upstream's
     * closed-loop results at the pinned commit
     * (experiment/closed-loop/RESULTS.md) trace this to the ego-motion
     * feedback, and the readiness probe in CARLA showed it too: the vehicle
     * left the road or the route 13 to 33 s after the hand-over in four
     * runs. So the input activity gives the checkpoint the ego-motion history
     * with yaw rate and curvature as zero (REQ-DRIVING-008). In the readiness
     * probe the plans then no longer turned off the lane within seconds: the
     * vehicle stayed in its lane for the 12 s to the first junction, though
     * it drifted steadily to one side without steering back, and drove
     * straight on at that junction where the route turned. The plans are
     * therefore not what the checkpoint makes on the full history it was
     * trained with. That the route does not steer the vehicle at junctions is
     * a separate limit, independent of the history (GAP-DRIVING-011). Revisit
     * when upstream publishes a checkpoint or a driver without this feedback.
     */
    attribute :>> disposition = LifecycleDisposition::accepted;
  }

  part <'GAP-DRIVING-011'> gapRouteChoosesNoBranch : IncrementGap {
    doc /*
     * Open, and accepted as a known limit (owner decision of 2026-11-10): the
     * pinned checkpoint takes no turn from the route. Given the same camera
     * images, map and motion history, swapping a route that turns hard left
     * for the same route mirrored to a hard right changes the planned heading
     * at 6.4 s by at most 0.02 degrees, where a turn at a junction needs
     * about 60. This holds with the motion history as REQ-DRIVING-008 gives
     * it (yaw rate and curvature zero) and with the recorded history, with a
     * route corridor drawn road-wide as in the checkpoint's training data,
     * with a destination marker 40 m along the route, and with the cameras
     * blanked and no map, where the route is the only navigation input (0.01
     * degrees). Upstream's other released checkpoint (kitscenes-epoch-5)
     * moves its planned heading by at most 1.5 degrees for the corridor and
     * by 4 degrees for a route that ends 40 m ahead in a destination marker.
     * Upstream's route-reconstruction head reads the navigation encoder's
     * route contribution, not the fused camera and navigation features the
     * planner sees (Model/model_components/reactive_e2e.py), so its training
     * teaches encoding the route, not driving along it; upstream's own
     * evaluation (Academic_Paper/AutoE2E_Route_Conditioned/paper_en.md)
     * states that its route-reconstruction score is not evidence that the
     * policy drove along the route, and lists route-determined branch choice
     * as a hypothesis still to be tested. So the route enters the plans but
     * does not choose the branch at a junction. The scenario's route
     * therefore needs no branch choice: every junction on it is passed
     * straight on (CARLA's route planner gives only lane-follow and straight
     * road options), and the evidence claims no route following at junctions.
     * Revisit when upstream publishes a checkpoint whose plans take the turn
     * from the route.
     */
    attribute :>> disposition = LifecycleDisposition::accepted;
  }

  part <'GAP-DRIVING-012'> gapPlansKeepNoLane : IncrementGap {
    doc /*
     * Open, and accepted as a known limit (owner decision of 2026-11-10):
     * the pinned checkpoint does not keep the vehicle in its lane. Two
     * errors of the bench made the first runs of the closed-loop scenario
     * on a straight route (2026-11-10) drift to the left faster than the
     * plans asked, and both were corrected that day. Its actuation adapter
     * applied every steering command at twice its angle: it scaled the
     * steer by the 35 degree command limit instead of by the vehicle's
     * maximum steering angle of 70 degrees, as MAP-DRIVING-VEHICLE-CONTROL
     * states. Its command law took the pose of a later plan sample, heading
     * included, for the vehicle's, and so asked for 0.6 degrees more
     * steering to the left than the plan did, at the median of two runs. In
     * the three runs made after both corrections, with the motion history
     * as REQ-DRIVING-008 gives it, the vehicle stayed within 0.16 m of the
     * route for the first 10 s after the first plan. From 15 s to 30 s its
     * heading turned 2.3 to 2.4 degrees to the right in each run. In two
     * runs the vehicle crossed the lane marking on its right 31.5 s and
     * 35.1 s after the first plan. In the third it was 1.4 m to the left of
     * the route after 30 s: between 10 s and 14 s its heading had turned
     * 1.6 degrees to the left on a mean steering command of 0.01 degrees,
     * and what turned the simulated vehicle is not determined. The plans
     * steered back on neither side: of 269 plans made with the vehicle more
     * than 0.3 m to the right of the route, none pointed back toward it; of
     * 165 made with it more than 0.3 m to the left, 25 did, by at most 0.5
     * degrees. The plans begin with a turn to the right, 0.6 degrees of
     * heading after 0.1 s, also when the vehicle is held on the route and
     * aligned with it, and the checkpoint's output for upstream's own
     * recorded sample begins the same way. The readiness probe, with the
     * yaw history also given as zero, showed the same: the vehicle drifted
     * steadily to one side without steering back (GAP-DRIVING-010). Other
     * bench-side causes were checked: the inputs the bench hands to the
     * checkpoint were read against upstream's code and, in one run, written
     * out and viewed. Camera order, image orientation and colour order, the
     * motion history and the map and route rasters have the form upstream's
     * code takes; the motion history carries only speed and acceleration
     * (REQ-DRIVING-008), and the camera's principal point is 0.08 degrees
     * off centre. With its own yaw history the checkpoint turns its plans
     * off the lane within seconds (GAP-DRIVING-010); without it, as here,
     * the plans do not correct a drift. So neither setting keeps the
     * vehicle in its lane. The evidence therefore claims no lane keeping
     * and no driving along the route, and the review of NEED-DRIVING-001
     * (SC-DRIVING-005) names this limit. Revisit when upstream publishes a
     * checkpoint that keeps its lane in a closed loop.
     */
    attribute :>> disposition = LifecycleDisposition::accepted;
  }

  part <'GAP-DRIVING-013'> gapPlanningPeriodNarrowlyMissed : IncrementGap {
    doc /*
     * Open, and accepted as a known limit (owner decision of 2026-11-10):
     * the planning period of REQ-DRIVING-013 is kept with almost no margin,
     * and was narrowly missed in the runs behind that decision. In three
     * runs of the closed-loop scenario on a straight route (2026-11-10),
     * 595, 585 and 588 of the 600 plans of the 60 s window were produced
     * within 100 ms after their newest camera image was available (99.2 %,
     * 97.5 % and 98.0 %), and in each run two consecutive plans missed it;
     * the latest plan was 1.7, 7.7 and 3.1 ms late. Since then the agent
     * draws the navigation raster of a step when the step's world snapshot
     * arrives, ahead of the step, and the two complete runs of the
     * closed-loop scenario made with that met the criterion: all 600 plans
     * of the window were in time, the latest 96.5 and 98.3 ms after its
     * image. Two later runs ended in a stop response before the window was
     * complete and cannot show the criterion; in one of them all 504 plans
     * were in time, the latest after 99.1 ms, and in the other three plans
     * were late before the stop response began. In an earlier run
     * (2026-11-09), with the vehicle standing after a contact for about
     * three quarters of the window, 594 of 600 were in time (99.0 %) and no
     * two consecutive plans missed, which meets the criterion at its limit.
     * The margin is small by construction: the checkpoint's inference alone
     * takes about 90 ms, so a delay of a few milliseconds anywhere in the
     * step makes a miss. A run in which the agent only planned alongside
     * and also wrote the checkpoint's inputs to disk on every 50th frame
     * was in time on 585 of its 600 plans. The limit stays at 100 ms, the
     * planning period, and a miss is accepted instead of the hold or
     * redirect that gapClosedLoopPerformance names. Revisit with a faster
     * host, or with a faster engine for the checkpoint, which changes its
     * numbers and needs its own parity evidence.
     */
    attribute :>> disposition = LifecycleDisposition::accepted;
  }


  /* ───────────── Concerns and views of the phase ───────────── */

  concern closedLoopDrivingPhysicalStructureConcern : PhysicalStructureConcern {
    doc /*
     * System architects and software developers need the software and
     * platform elements that realize the driving system on the bench, as
     * they nest: the three hosts with their platform layers, the S-CORE
     * services, the three programs and the four activities of the agent,
     * the route provider, the simulator with its rig, the hypervisor and the
     * two AAOS SDV guests.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder softwareDeveloper : SoftwareDeveloper;
  }

  view closedLoopDrivingPhysicalStructureView {
    viewpoint selectedPhysicalStructureViewpoint : PhysicalStructureDefinitionViewpoint {
      frame closedLoopDrivingPhysicalStructureConcern;
    }
    expose closedLoopDrivingPhysicalSystem;
    expose closedLoopDrivingPhysicalSystem::linuxHost;
    expose closedLoopDrivingPhysicalSystem::linuxHost::os;
    expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware;
    expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::drivingAgent;
    expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::drivingAgent::conditionInputs;
    expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::drivingAgent::inferPlan;
    expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::drivingAgent::superviseLoop;
    expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::drivingAgent::commandVehicle;
    expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::actuationAdapter;
    expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::statePublisherApplication;
    expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::scoreServices;
    expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::scoreServices::launchManager;
    expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::scoreServices::gatewayd;
    expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::scoreServices::someipd;
    expose closedLoopDrivingPhysicalSystem::linuxHost::routeProvider;
    expose closedLoopDrivingPhysicalSystem::simulatorHost;
    expose closedLoopDrivingPhysicalSystem::simulatorHost::os;
    expose closedLoopDrivingPhysicalSystem::simulatorHost::carlaServer;
    expose closedLoopDrivingPhysicalSystem::simulatorHost::carlaServer::sensorRig;
    expose closedLoopDrivingPhysicalSystem::simulatorHost::carlaServer::sensorRig::frontCamera;
    expose closedLoopDrivingPhysicalSystem::simulatorHost::carlaServer::sensorRig::frontLeftCamera;
    expose closedLoopDrivingPhysicalSystem::simulatorHost::carlaServer::sensorRig::frontRightCamera;
    expose closedLoopDrivingPhysicalSystem::simulatorHost::carlaServer::sensorRig::rearLeftCamera;
    expose closedLoopDrivingPhysicalSystem::simulatorHost::carlaServer::sensorRig::rearCamera;
    expose closedLoopDrivingPhysicalSystem::simulatorHost::carlaServer::sensorRig::rearRightCamera;
    expose closedLoopDrivingPhysicalSystem::simulatorHost::carlaServer::sensorRig::egoMotionSource;
    expose closedLoopDrivingPhysicalSystem::guestHost;
    expose closedLoopDrivingPhysicalSystem::guestHost::os;
    expose closedLoopDrivingPhysicalSystem::guestHost::hypervisor;
    expose closedLoopDrivingPhysicalSystem::sdvCoreGuest;
    expose closedLoopDrivingPhysicalSystem::sdvCoreGuest::os;
    expose closedLoopDrivingPhysicalSystem::sdvCoreGuest::sdvMiddleware;
    expose closedLoopDrivingPhysicalSystem::sdvCoreGuest::sdvCore;
    expose closedLoopDrivingPhysicalSystem::hmiGuest;
    expose closedLoopDrivingPhysicalSystem::hmiGuest::os;
    expose closedLoopDrivingPhysicalSystem::hmiGuest::sdvGateway;
    expose closedLoopDrivingPhysicalSystem::hmiGuest::stateObserver;
    filter not (@ SysML::AllocationUsage);
    filter not (@ SysML::BindingConnectorAsUsage);
    render asTreeDiagram;
  }

  concern closedLoopDrivingPhysicalAllocationConcern : PhysicalLogicalMappingConcern {
    doc /*
     * System architects, verification engineers and open-source reviewers
     * need each logical element of phase 7 allocated to the software element
     * that carries it, and each software element carrying one: the four
     * activities of the agent, the actuation adapter, the publisher, and the
     * two gateway processes the publisher reaches the observer through. An
     * allocation is a responsibility assignment, no deployment or runtime
     * claim.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view closedLoopDrivingPhysicalLogicalMappingView : MVD::MatrixView {
    viewpoint selectedPhysicalLogicalMappingViewpoint : PhysicalLogicalMappingViewpoint {
      frame closedLoopDrivingPhysicalAllocationConcern;
    }
    view :>> rowView {
      expose ClosedLoopDrivingLogicalSystem::inputConditioner;
      expose ClosedLoopDrivingLogicalSystem::planner;
      expose ClosedLoopDrivingLogicalSystem::loopSupervisor;
      expose ClosedLoopDrivingLogicalSystem::vehicleCommander;
      expose ClosedLoopDrivingLogicalSystem::actuationGateway;
      expose ClosedLoopDrivingLogicalSystem::statePublisher;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> columnView {
      expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::drivingAgent::conditionInputs;
      expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::drivingAgent::inferPlan;
      expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::drivingAgent::superviseLoop;
      expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::drivingAgent::commandVehicle;
      expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::actuationAdapter;
      expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::statePublisherApplication;
      expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::scoreServices::gatewayd;
      expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::scoreServices::someipd;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    }
    view :>> cellView {
      expose DE4SDV_ClosedLoopDrivingPhysicalSoftwareRealization::*;
      attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;
    }
  }

  view closedLoopDrivingSCOREPathExchangeView {
    doc /*
     * The S-CORE path (scoreCommandPathConcern) and the authority of the
     * checkpoint's plan over the commands (checkpointCommandAuthorityConcern)
     * in one interconnection of the software realization: the plan enters
     * the supervision from the inference only, the valid plan enters the
     * commander from the supervision only, the command enters the actuation
     * adapter from the commander only, over mw::com; no other port leads to
     * the vehicle control. The functional-mapping question is answered by
     * this exchange, not by a matrix: no direct relation exists between a
     * function and a software element to draw.
     */
    viewpoint selectedPhysicalInternalExchangeViewpoint : PhysicalInternalExchangeViewpoint {
      frame scoreCommandPathConcern;
      frame checkpointCommandAuthorityConcern;
    }
    expose closedLoopDrivingSoftware;
    expose closedLoopDrivingSoftware::**;
    filter not (@ SysML::AllocationUsage);
    attribute depth = -1;
    attribute showAnnotationRows = false;
    render asInterconnectionDiagram;
  }

  view closedLoopDrivingPhysicalContextExchangeView {
    doc /*
     * What crosses the boundary of the software realization on the bench,
     * both sides, each exchange labelled with its item. Into the simulator
     * server, which stands for the vehicle and the road environment: the
     * vehicle control, the three fields the actuation adapter sets, and
     * nothing else (checkpointCommandAuthorityConcern: no other source of
     * commands reaches the simulated vehicle). Out of it: the camera
     * stream, the ego motion and the simulation clock; from the route
     * provider: the route. The simulator's exchanges cross from the
     * simulator host's ports to the S-CORE host's over the bench network.
     * Out of the S-CORE host: the operational state on SOME/IP over the
     * VXLAN segment into the SDV Core VM and the topic from the SDV Core VM
     * to the IVI VM, and nothing back (aaosObservationFidelityConcern). Each
     * part, port and exchange is exposed by name: the ports are declared
     * on the definitions and a typed wildcard over a usage drew none of
     * them (runs 42214648709, 42253633791); the exchanges are connections,
     * drawn as edges between exposed ports, where flows were not drawn in
     * six runs. The insides of the realization and of the guests stay
     * hidden: their port delegations are binds, filtered here (a bind or a
     * connection with an unexposed end draws as a box with two ends, runs
     * 42215689738 and 42255511098), and the path view keeps its
     * connections. The package's allocations and the hypervisor
     * interfaces, which span levels, are filtered too.
     */
    viewpoint selectedPhysicalContextExchangeViewpoint : PhysicalContextExchangeViewpoint {
      frame aaosObservationFidelityConcern;
      frame checkpointCommandAuthorityConcern;
    }
    expose closedLoopDrivingPhysicalSystem;
    expose closedLoopDrivingPhysicalSystem::linuxHost;
    expose closedLoopDrivingPhysicalSystem::linuxHost::cameraImagesIn;
    expose closedLoopDrivingPhysicalSystem::linuxHost::egoMotionIn;
    expose closedLoopDrivingPhysicalSystem::linuxHost::simulationClockIn;
    expose closedLoopDrivingPhysicalSystem::linuxHost::vehicleControlOut;
    expose closedLoopDrivingPhysicalSystem::linuxHost::operationalStateOut;
    expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware;
    expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::cameraImagesIn;
    expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::egoMotionIn;
    expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::routeIn;
    expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::simulationClockIn;
    expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::vehicleControlOut;
    expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::operationalStateOut;
    expose closedLoopDrivingPhysicalSystem::linuxHost::routeProvider;
    expose closedLoopDrivingPhysicalSystem::linuxHost::routeProvider::routeOut;
    expose closedLoopDrivingPhysicalSystem::linuxHost::cameraImagesDelegation;
    expose closedLoopDrivingPhysicalSystem::linuxHost::egoMotionDelegation;
    expose closedLoopDrivingPhysicalSystem::linuxHost::simulationClockDelegation;
    expose closedLoopDrivingPhysicalSystem::linuxHost::routeFromScenario;
    expose closedLoopDrivingPhysicalSystem::linuxHost::vehicleControlDelegation;
    expose closedLoopDrivingPhysicalSystem::linuxHost::operationalStateDelegation;
    expose closedLoopDrivingPhysicalSystem::simulatorHost;
    expose closedLoopDrivingPhysicalSystem::simulatorHost::cameraStreamOut;
    expose closedLoopDrivingPhysicalSystem::simulatorHost::egoMotionOut;
    expose closedLoopDrivingPhysicalSystem::simulatorHost::simulationClockOut;
    expose closedLoopDrivingPhysicalSystem::simulatorHost::vehicleControlIn;
    expose closedLoopDrivingPhysicalSystem::simulatorHost::carlaServer;
    expose closedLoopDrivingPhysicalSystem::simulatorHost::carlaServer::cameraStreamOut;
    expose closedLoopDrivingPhysicalSystem::simulatorHost::carlaServer::egoMotionOut;
    expose closedLoopDrivingPhysicalSystem::simulatorHost::carlaServer::simulationClockOut;
    expose closedLoopDrivingPhysicalSystem::simulatorHost::carlaServer::vehicleControlIn;
    expose closedLoopDrivingPhysicalSystem::simulatorHost::cameraStreamDelegation;
    expose closedLoopDrivingPhysicalSystem::simulatorHost::egoMotionDelegation;
    expose closedLoopDrivingPhysicalSystem::simulatorHost::simulationClockDelegation;
    expose closedLoopDrivingPhysicalSystem::simulatorHost::vehicleControlDelegation;
    expose closedLoopDrivingPhysicalSystem::sdvCoreGuest;
    expose closedLoopDrivingPhysicalSystem::sdvCoreGuest::someIpIn;
    expose closedLoopDrivingPhysicalSystem::sdvCoreGuest::topicOut;
    expose closedLoopDrivingPhysicalSystem::hmiGuest;
    expose closedLoopDrivingPhysicalSystem::hmiGuest::topicIn;
    expose closedLoopDrivingPhysicalSystem::cameraStreamOverBenchNetwork;
    expose closedLoopDrivingPhysicalSystem::egoMotionOverBenchNetwork;
    expose closedLoopDrivingPhysicalSystem::simulationClockOverBenchNetwork;
    expose closedLoopDrivingPhysicalSystem::vehicleControlOverBenchNetwork;
    expose closedLoopDrivingPhysicalSystem::operationalStateOverSOMEIPAcrossVXLANSegment;
    expose closedLoopDrivingPhysicalSystem::operationalStateTopicOverDataTunnelAcrossVMs;
    filter not (@ SysML::AllocationUsage);
    filter not (@ SysML::InterfaceUsage);
    filter not (@ SysML::BindingConnectorAsUsage);
    attribute depth = -1;
    attribute showAnnotationRows = false;
    attribute maxCompartmentEntries = 0;
    render asInterconnectionDiagram;
  }
}
