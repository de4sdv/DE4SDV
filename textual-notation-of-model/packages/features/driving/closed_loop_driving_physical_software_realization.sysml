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
 * - B. The planner is C++ on an exported form of the pinned AutoE2E checkpoint
 *   (source revision cb50764b8250a3c44ee5b79b87ba02c5a83b0c91): an inference
 *   engine (TensorRT on the NVIDIA host, ONNX Runtime as the fallback) over an
 *   ONNX export, after the shape of the S-CORE AI Platform feature request
 *   (a thin model API over a vendor runtime). The training framework runs
 *   nowhere on the loop; Python stays in System 2 (export and parity tooling).
 *   Whether the export stands for the checkpoint is GAP-DRIVING-003.
 * - C. Eclipse S-CORE pinned at reference_integration v0.10.0
 *   (ca2a5f03724780be3cebf3d80e0c9c0c6fa64eb2, known_good.json of
 *   2026-08-28): Communication v0.6.0 (mw::com, LoLa), Lifecycle v0.10.0
 *   (Launch Manager), Logging v0.2.6, Time v0.3.1, Configuration Management
 *   v0.3.1, Baselibs v0.2.17. Two modules sit outside that baseline: FEO at
 *   v1.0.5 (313b3d849c17881d3a11b6bf62aa2afab6565ef0, GAP-DRIVING-001) and
 *   the SOME/IP gateway of INC-MW-011 at d9eac670b7534352749da3d30f52aebf5129f168
 *   (GAP-DRIVING-002). Nothing is vendored.
 * - D. KUKSA Databroker stays unselected: ALT-MW-KUKSA-001 stands. It is a
 *   QM gRPC broker of VSS signals; on the command path it would put a hop
 *   beside S-CORE communication (REQ-DRIVING-014), and on the observation
 *   path AAOS SDV consumes a typed Data Tunnel topic (decision 4). A host-side
 *   VSS broker is at most a phase 9 variation point.
 * - Decision 3. The simulator runs in asynchronous real-time mode (phase 0:
 *   no retiming of a slow simulation). Simulation time comes with each
 *   measurement (REQ-DRIVING-030) and from the world snapshot at the actuation
 *   adapter (REQ-DRIVING-028); wall-clock time from the host (REQ-DRIVING-013,
 *   -015 to -017, -019, -029, -031, -032).
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
 * Alternatives recorded and not selected:
 * - ALT-DRIVING-PLAINAPPS-001: four plain S-CORE applications instead of the
 *   FEO agent, every exchange of the loop over mw::com. Cheaper to build, no
 *   fixed-order scheduler, two more process hops inside the 100 ms budget of
 *   REQ-DRIVING-013. The fallback if GAP-DRIVING-001 closes against FEO.
 * - ALT-DRIVING-SIMBRIDGE-001: a separate simulation-bridge process holding
 *   the simulator client and publishing camera frames over mw::com, instead
 *   of the client inside the agent's input activity. One more copy of each
 *   frame and one more hop before planning; production-like for a camera
 *   driver, not needed on the bench.
 * - ALT-DRIVING-LIBTORCH-001: the C++ planner on the training framework's
 *   C++ runtime (a traced or exported graph) instead of an ONNX export.
 *   Closest numerics, no conversion, but not among the runtimes the S-CORE
 *   AI Platform request names. The fallback if the export fails on an
 *   unsupported operator (GAP-DRIVING-003).
 * - ALT-DRIVING-FEOMWCOM-001: FEO from its main branch, whose feo-com has an
 *   mw_com backend, so that the plan hops inside the agent are themselves
 *   mw::com. Unreleased, and its module file pins an older Communication;
 *   the reading question the owner closed on 2026-11-06 would not arise,
 *   the build risk grows.
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
     * (REQ-DRIVING-030). The curvature history the checkpoint takes is derived
     * inside the agent from the yaw rate and the speed and is no vehicle
     * signal (MAP-DRIVING-EGO-MOTION).
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

  /* ───────────── The software elements: four activities of one agent, two applications ───────────── */

  part def InputConditioningActivity :> PhysicalAllocationElement {
    doc /*
     * Carries the input conditioner of phase 7 as the first activity of the
     * FEO cycle, in C++. It holds the simulator client of the agent: the
     * camera sensor stream, the motion state of the ego vehicle and the route
     * of the scenario arrive through the client library on its threads; the
     * step reads the newest frame and sample, marks each with its capture
     * time in simulation time (REQ-DRIVING-030), keeps the camera and
     * ego-motion histories of the run (REQ-DRIVING-004, -008, -010), derives
     * the curvature from yaw rate and speed, rasterizes the route mask and
     * the map context (REQ-DRIVING-006, -007) and writes the checkpoint
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
     * Carries the planner of phase 7, run identity and planning, as the
     * second activity of the FEO cycle, in C++. At startup it reads the
     * configuration, computes the SHA-256 of the checkpoint file and of the
     * exported model file it loads, refuses to plan when the checkpoint's
     * SHA-256 differs from the one the configuration names or none is named
     * (REQ-DRIVING-035), and records the run identity before the first plan
     * (REQ-DRIVING-033). Each step runs the inference engine (TensorRT on the
     * NVIDIA host, ONNX Runtime as the fallback) over the ONNX export of the
     * pinned checkpoint on the checkpoint inputs and writes the plan, with
     * its producer, its production time and the run record it names
     * (REQ-DRIVING-031, -034), to the FEO topic for the loop supervision and
     * to the mw::com event for the state publisher (REQ-DRIVING-015).
     */
    port checkpointInputsIn : CheckpointInputsIn;
    port planOut : DrivingPlanOut;
    port planEventOut : DrivingPlanOut;
  }

  part def LoopSupervisionActivity :> PhysicalAllocationElement {
    doc /*
     * Carries the loop supervisor of phase 7 as the third activity of the
     * FEO cycle, in C++. It judges the plan against the input condition and
     * the planning period (REQ-DRIVING-013, -023 to -027), passes the newest
     * valid plan on, and decides the mode: driving, or the stop response
     * with its cause. The mode goes to the vehicle commander on an FEO topic
     * and to the state publisher as an mw::com event (REQ-DRIVING-029). It
     * issues no command.
     */
    port inputConditionIn : InputConditionIn;
    port planIn : DrivingPlanIn;
    port validPlanOut : DrivingPlanOut;
    port modeOut : DrivingModeOut;
    port modeEventOut : DrivingModeOut;
  }

  part def VehicleCommandActivity :> PhysicalAllocationElement {
    doc /*
     * Carries the vehicle commander of phase 7 as the last activity of the
     * FEO cycle, in C++. It computes the steering angle and the acceleration
     * from the newest valid plan and the current motion sample
     * (REQ-DRIVING-011), within the limits the configuration names
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
     * framework (eclipse-score/feo v1.0.5, a Rust framework whose activities
     * may be C++ through its C++ activity bindings), running the four
     * activities in the order of the loop, once per cycle. The cycle is paced
     * by the camera frames of the simulation (REQ-DRIVING-001: one plan per
     * 100 ms step of simulation time); whether the scheduler can be driven by
     * the frame rather than by a timer is part of ASM-DRIVING-001. Inside the
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
     * own, in C++, with a second simulator client. It subscribes to the
     * command event, converts the acceleration and the steering angle into
     * the simulator's vehicle control (throttle, brake, steer) within the
     * limits of the vehicle (REQ-DRIVING-012) and applies it to the ego
     * vehicle. It reads the simulation time from the world snapshot; when no
     * valid command has arrived for 200 ms of simulation time it applies the
     * stop response itself (REQ-DRIVING-028), which is why it is not an
     * activity of the agent. Nothing it knows flows back into the loop; what
     * that means for REQ-DRIVING-029 is GAP-DRIVING-005.
     */
    port commandIn : MotionCommandIn;
    port simulationClockIn : SimulationClockIn;
    port vehicleControlOut : VehicleControlOut;
  }

  part def OperationalStatePublisherApplication :> PhysicalAllocationElement {
    doc /*
     * Carries the operational-state publisher of phase 7: an S-CORE
     * application of its own, in C++, off the loop. It subscribes to the
     * plan, the mode and the ego-motion sample events of the agent and
     * publishes the operational state, each publication with its producer
     * and its time: the plan (REQ-DRIVING-015), the motion sample
     * (REQ-DRIVING-016), the health at least every 200 ms also while no plan
     * arrives (REQ-DRIVING-017), and the stop with its cause when the mode
     * changes (REQ-DRIVING-029). Its one output is the mw::com event the
     * SOME/IP gateway forwards; it has no port into the agent
     * (REQ-DRIVING-018, -019).
     */
    port planIn : DrivingPlanIn;
    port modeIn : DrivingModeIn;
    port egoMotionSampleIn : EgoMotionSampleIn;
    port operationalStateOut : OperationalStateOut;
  }

  part def ClosedLoopDrivingSoftwareRealization :> ClosedLoopDrivingSystem {
    doc /*
     * The driving system as phase 8 realizes it: the same system as the
     * context's drivingSystem, now the three programs on the Linux host and
     * the S-CORE services they use, owned here with them (one instance on
     * the host, typed by the platform stack's middleware layer). The
     * boundary of phase 6 is kept as ports of the realization: the
     * camera images, the ego motion and the route in, the vehicle command
     * out, the operational state out; the simulation clock is a System 2
     * input the bench adds. Between processes every hop is mw::com (S-CORE
     * Communication v0.6.0): the command to the actuation adapter, the
     * REQ-DRIVING-014 hop; the plan, the mode and the ego-motion sample to
     * the publisher; the operational state to gatewayd. From gatewayd on the
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
         * carries no logical element; its recovery actions are a phase 10
         * configuration.
         */
      }
      part gatewayd : PhysicalAllocationElement {
        doc /*
         * The gatewayd process of the S-CORE SOME/IP gateway: subscribes to
         * the operational-state event on mw::com and hands it to someipd
         * over the gateway's IPC. Carries the publisher's reach to the
         * observer together with someipd; a process of the pinned gateway,
         * not DE4SDV code (GAP-DRIVING-002).
         */
        port operationalStateIn : OperationalStateIn;
        port operationalStateOut : OperationalStateOut;
      }
      part someipd : PhysicalAllocationElement {
        doc /*
         * The someipd process of the S-CORE SOME/IP gateway: offers the
         * operational-state service on SOME/IP and sends each event over the
         * virtual network of the hypervisor to the SOME/IP interop of SDV
         * Core. The last element of the driving system on the observation
         * path; a process of the pinned gateway, not DE4SDV code.
         */
        port operationalStateIn : OperationalStateIn;
        port operationalStateOut : OperationalStateOut;
      }
    }

    connection cameraImagesDelegation connect cameraImagesIn to drivingAgent.cameraImagesIn;
    connection egoMotionDelegation connect egoMotionIn to drivingAgent.egoMotionIn;
    connection routeDelegation connect routeIn to drivingAgent.routeIn;
    connection simulationClockDelegation connect simulationClockIn to actuationAdapter.simulationClockIn;
    connection vehicleControlDelegation connect actuationAdapter.vehicleControlOut to vehicleControlOut;
    connection operationalStateDelegation connect scoreServices.someipd.operationalStateOut to operationalStateOut;
    connection commandOverSCORECommunication connect drivingAgent.commandOut to actuationAdapter.commandIn;
    connection planEventOverSCORECommunication connect drivingAgent.planEventOut to statePublisherApplication.planIn;
    connection modeEventOverSCORECommunication connect drivingAgent.modeEventOut to statePublisherApplication.modeIn;
    connection egoMotionSampleOverSCORECommunication connect drivingAgent.egoMotionSampleOut to statePublisherApplication.egoMotionSampleIn;
    connection operationalStateOverSCORECommunication connect statePublisherApplication.operationalStateOut to scoreServices.gatewayd.operationalStateIn;
    connection operationalStateOverGatewayIPC connect scoreServices.gatewayd.operationalStateOut to scoreServices.someipd.operationalStateIn;
  }

  /* ───────────── The context realizations on the bench ───────────── */

  part def CARLASimulationServer {
    doc /*
     * The simulator server, System 2: renders the cameras of the ego vehicle
     * and simulates its dynamics and the road environment, so it stands for
     * the vehicle and the road environment of the phase 2 context on the
     * bench. It runs in asynchronous real-time mode (decision 3): the scene
     * progresses at wall-clock pace and no client ticks the world. Two
     * clients connect to it over the host's loopback: the agent's input
     * activity for the sensor streams and the actuation adapter for the
     * vehicle control and the world snapshot. Its release is pinned with the
     * scenario in phase 10; the client library's build against the S-CORE
     * toolchain is GAP-DRIVING-004.
     */
    port cameraStreamOut : CameraStreamOut;
    port egoMotionOut : EgoMotionStreamOut;
    port simulationClockOut : SimulationClockOut;
    port vehicleControlIn : VehicleControlIn;
  }

  part def ScenarioRouteProvider :> NavigationSystem {
    doc /*
     * The navigation of the phase 2 context as the bench realizes it: the
     * pinned route of the scenario, System 2, read from the scenario
     * configuration on the Linux host and handed to the input activity at
     * the start of the run; the destination is the scenario's. It runs on
     * the host, not on the AAOS SDV guest, so AAOS SDV is no input to the
     * loop and the context-role decision of 2026-11-02 stays closed. The
     * driving system plans along the route and does not choose it.
     */
    port routeOut : RouteOut;
  }

  part def AAOSSDVCoreGuest {
    doc /*
     * The SDV Core VM of the AAOS SDV guest, context of the loop: Android
     * under the host's KVM, with the SDV Core middleware. The SOME/IP
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
    connection someIpDelegation connect someIpIn to sdvCore.someIp.someIpPort;
    connection operationalStateTopicPublishedByBroker connect sdvCore.someIp.topicPublishOut to sdvCore.dataTunnel.topicPublishPort;
    connection topicDelegation connect sdvCore.dataTunnel.topicSubscribePort to topicOut;
  }

  part def AAOSIVIGuest {
    doc /*
     * The IVI VM of the AAOS SDV guest, context of the loop: Android under
     * the host's KVM, with the SDV Gateway and the observer application of
     * phase 2 that presents the plan, the vehicle state and the health to
     * the driver. The observer subscribes to the typed topic through the SDV
     * Gateway and sends nothing to the driving system. The observer
     * application is a build item of the bench, named here, not claimed.
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
    connection topicDelegation connect topicIn to sdvGateway.dataTunnelPort;
    connection operationalStateThroughSDVGateway connect sdvGateway.clientPort to stateObserver.operationalStateIn;
  }

  part def ClosedLoopDrivingLinuxHost {
    doc /*
     * The Linux host of the bench: x86_64, with an NVIDIA GPU for the
     * simulator's rendering and the planner's inference engine, and KVM for
     * the two AAOS SDV guests (GAP-DRIVING-007). It owns the platform
     * layers, the software realization of the driving system with its
     * S-CORE services, the simulator server and the route provider. The sensor
     * streams, the route, the simulation clock and the vehicle control cross
     * the host's loopback between the simulator and the driving software;
     * the operational state leaves the host on SOME/IP. The exchanges are
     * flows, each of its item, so the context exchange view names what
     * crosses; into the simulator goes the vehicle control and nothing else.
     */
    port operationalStateOut : OperationalStateOut;
    part os : LinuxPlatform;
    part hypervisor : KVMHypervisor;
    part drivingSoftware : ClosedLoopDrivingSoftwareRealization;
    part carlaServer : CARLASimulationServer;
    part routeProvider : ScenarioRouteProvider;
    flow cameraStreamOverHostLoopback of CameraImages
      from carlaServer.cameraStreamOut.cameraImages to drivingSoftware.cameraImagesIn.cameraImages;
    flow egoMotionOverHostLoopback of EgoMotionState
      from carlaServer.egoMotionOut.egoMotion to drivingSoftware.egoMotionIn.egoMotion;
    flow simulationClockOverHostLoopback of SimulationClock
      from carlaServer.simulationClockOut.simulationClock to drivingSoftware.simulationClockIn.simulationClock;
    flow routeFromScenario of Route
      from routeProvider.routeOut.route to drivingSoftware.routeIn.route;
    flow vehicleControlOverHostLoopback of SimulatorVehicleControl
      from drivingSoftware.vehicleControlOut.vehicleControl to carlaServer.vehicleControlIn.vehicleControl;
    flow operationalStateDelegation of DrivingOperationalState
      from drivingSoftware.operationalStateOut.operationalState to operationalStateOut.operationalState;
  }

  part def ClosedLoopDrivingPhysicalSystem {
    doc /*
     * The physical context of the bench: the Linux host and the two AAOS SDV
     * guests under its KVM. The operational state crosses the hypervisor
     * once on SOME/IP, from someipd to the SDV Core VM, and the VMs once on
     * the Data Tunnel, from the SDV Core VM to the IVI VM. Nothing crosses
     * back: the guests are observers. The host's inside is drawn by the
     * S-CORE path view; what crosses the realization's boundary, on the
     * bench side and on the observer side, by the context exchange view.
     */
    part linuxHost : ClosedLoopDrivingLinuxHost;
    part sdvCoreGuest : AAOSSDVCoreGuest;
    part hmiGuest : AAOSIVIGuest;
    interface sdvCoreGuestUnderKVM : OSHypervisorInterface
      connect sdvCoreGuest.os.hypervisorPort to linuxHost.hypervisor.guestPort;
    interface hmiGuestUnderKVM : OSHypervisorInterface
      connect hmiGuest.os.hypervisorPort to linuxHost.hypervisor.guestPort;
    flow operationalStateOverSOMEIPAcrossHypervisor of DrivingOperationalState
      from linuxHost.operationalStateOut.operationalState to sdvCoreGuest.someIpIn.operationalState;
    flow operationalStateTopicOverDataTunnelAcrossVMs of DrivingOperationalState
      from sdvCoreGuest.topicOut.topicData to hmiGuest.topicIn.topicData;
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
      attribute :>> softwareContractArtifact = "in: the simulator client library's camera sensor stream (sensor data callbacks on the client's threads), candidate, release pinned in phase 10; out: the checkpoint inputs on the agent's FEO topic, candidate";
      attribute :>> softwareContractMessage = "in: one image measurement per camera per sensor tick with its frame number and simulation timestamp, candidate; out: the camera history tensor of the checkpoint inputs, candidate";
      attribute :>> softwareContractField = "in: raw image buffer, width, height, field of view, timestamp, exact per the client library; out: the history slot of each camera in the checkpoint's input layout, candidate";
      attribute :>> dataTypeAndUnit = "in: 8-bit BGRA pixels per camera, simulation seconds for the timestamp; out: the checkpoint's normalized image tensor, no unit";
      attribute :>> timingQualityAndState = "one frame per camera per 100 ms of simulation time (REQ-DRIVING-001); a frame is marked with its capture time (REQ-DRIVING-030) and enters a history once (REQ-DRIVING-010); a missing or late frame sets the input condition (REQ-DRIVING-023)";
      attribute :>> transformationRule = "projection of each image into the checkpoint's camera geometry and history layout (REQ-DRIVING-003 to -005), defined by the pinned source revision; no retiming of the simulation";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "phase 10: pin the simulator release, the camera placement and the sensor tick with the scenario, then run REQ-DRIVING-003 to -005, -010 and -023 against recorded frames";
      attribute :>> evidenceOrGap = "no runtime evidence of record; GAP-DRIVING-004 (client library build), framing gap gapModelInputAndFeedback (camera calibration and history priming)";
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
       * curvature history is derived.
       */
      attribute :>> semanticSource = "the motion state of the ego vehicle as the simulator reports it (velocity and acceleration vectors, angular velocity) and, out, the sample typed by COVESA VSS at the port: Vehicle_Speed [km/h], Vehicle_Acceleration_Longitudinal and _Lateral [m/s^2], Vehicle_AngularVelocity_Yaw [deg/s]";
      attribute :>> softwareContractArtifact = "in: the simulator client library's actor state of the ego vehicle, candidate; out: the agent's FEO topic for the vehicle commander and the mw::com event for the state publisher (the layer's mw::com configuration, phase 10), candidate";
      attribute :>> softwareContractMessage = "in: velocity, acceleration and angular velocity of the ego vehicle per world snapshot, candidate; out: EgoMotionSamplePayload with its capture time, candidate";
      attribute :>> softwareContractField = "in: velocity.x/y, acceleration.x/y, angular_velocity.z, snapshot timestamp, exact per the client library; out: speed, longitudinalAcceleration, lateralAcceleration, yawRate, captureTime, exact";
      attribute :>> dataTypeAndUnit = "in: float32 m/s, m/s^2, deg/s, simulation seconds; out: speed : Vehicle_Speed km/h, accelerations : Vehicle_Acceleration_* m/s^2, yawRate : Vehicle_AngularVelocity_Yaw deg/s, captureTime simulation seconds; inside the agent the checkpoint takes speed in m/s, yaw rate in rad/s and the curvature in 1/m";
      attribute :>> timingQualityAndState = "one sample per 100 ms step, marked with its capture time (REQ-DRIVING-030); the sample history of the run has no record twice (REQ-DRIVING-010); a missing or implausible sample sets the input condition (REQ-DRIVING-024); the publisher receives the same sample within 100 ms of wall-clock time (REQ-DRIVING-016)";
      attribute :>> transformationRule = "speed = |velocity| * 3.6 as the VSS km/h value; the checkpoint input takes speed / 3.6, yawRate * pi / 180 and curvature = yawRate_rad / speed_mps (0 below a configured minimum speed), as the pinned source revision defines its ego-motion history";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "phase 10: author the mw::com configuration of the sample event and run REQ-DRIVING-008, -010, -016 and -024 on recorded samples, with the unit conversions checked against the Python reference";
      attribute :>> evidenceOrGap = "no runtime evidence of record; GAP-DRIVING-003 (the reference's ego-motion conventions), GAP-DRIVING-004";
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
      attribute :>> softwareContractArtifact = "in: the scenario's route file read by the route provider at the start of the run, candidate; out: the route mask raster in the checkpoint inputs on the agent's FEO topic, candidate";
      attribute :>> softwareContractMessage = "in: an ordered list of waypoints in the map frame, candidate; out: the route mask and map context rasters of the checkpoint's input layout, candidate";
      attribute :>> softwareContractField = "in: waypoint x, y, heading and road id, candidate; out: the raster channels the pinned source revision defines, candidate";
      attribute :>> dataTypeAndUnit = "in: float32 metres and radians in the map frame; out: the checkpoint's raster tensors, no unit";
      attribute :>> timingQualityAndState = "read once per run before the first plan; the raster is recomputed per step from the ego pose; a route the ego vehicle has left or a missing route sets the input condition (REQ-DRIVING-025)";
      attribute :>> transformationRule = "rasterization of the route and the map context into the ego frame of each step (REQ-DRIVING-006, -007), as the pinned source revision defines it";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "phase 10: pin the scenario route with the simulator release and run REQ-DRIVING-006, -007 and -025 against the Python reference's rasters";
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
      attribute :>> semanticSource = "the trajectory the exported checkpoint predicts for the next planning horizon, in the ego frame, with its producer, its production time and the run record it names: a plan, no vehicle signal";
      attribute :>> softwareContractArtifact = "in: the output tensors of the inference engine over the ONNX export of the pinned checkpoint, candidate; out: the agent's FEO topic for the loop supervision and the mw::com plan event for the state publisher, candidate";
      attribute :>> softwareContractMessage = "in: the checkpoint's output layout (trajectory samples over the horizon), exact per the pinned source revision; out: DrivingPlan with producer, production time and run record, candidate";
      attribute :>> softwareContractField = "in: the sampled positions or acceleration/curvature samples of the output head, exact per the pinned source revision; out: samples, horizon, producer, productionTime, runRecord, candidate";
      attribute :>> dataTypeAndUnit = "in: float32 metres and radians, or m/s^2 and 1/m, per the output head; out: the same with wall-clock seconds for the production time";
      attribute :>> timingQualityAndState = "one plan per 100 ms step (REQ-DRIVING-001), produced within 100 ms of wall-clock time after the newest image (REQ-DRIVING-013), stamped (REQ-DRIVING-031), published for observation within 100 ms (REQ-DRIVING-015); no plan while the checkpoint identity fails (REQ-DRIVING-035)";
      attribute :>> transformationRule = "identity on the values; the plan names the run record (REQ-DRIVING-034); the engine's numerical parity with the Python reference is the probe of GAP-DRIVING-003";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "phase 10: export the pinned checkpoint, measure its parity on recorded inputs, author the plan event's mw::com configuration and run REQ-DRIVING-001, -013, -015 and -031";
      attribute :>> evidenceOrGap = "no runtime evidence of record; GAP-DRIVING-003, framing gap gapClosedLoopPerformance (planning time unmeasured)";
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
      attribute :>> semanticSource = "the mode the loop supervision decides each step, driving or the stop response with its cause (degraded camera images, motion or route, a stale or invalid plan, an exceeded planning period): a system state, no vehicle signal";
      attribute :>> softwareContractArtifact = "in: the plan and the input condition on the agent's FEO topics, candidate; out: the mode and the valid plan on FEO topics for the vehicle commander and the mw::com mode event for the state publisher, candidate";
      attribute :>> softwareContractMessage = "out: DrivingMode with the cause and the decision time, candidate";
      attribute :>> softwareContractField = "out: mode, cause, decisionTime, candidate";
      attribute :>> dataTypeAndUnit = "out: an enumeration for the mode and the cause, wall-clock seconds for the decision time; no unit";
      attribute :>> timingQualityAndState = "decided once per step; the stop response is published with its cause within 100 ms of wall-clock time of its start (REQ-DRIVING-029); a plan older than its step is stale (REQ-DRIVING-026)";
      attribute :>> transformationRule = "state rule: the input condition of REQ-DRIVING-023 to -025, a stale plan (REQ-DRIVING-026), an invalid plan (REQ-DRIVING-027) or an exceeded planning period (REQ-DRIVING-013) gives the stop response with that cause; otherwise driving";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "phase 10: fix the mode and cause enumerations in the mw::com configuration and run REQ-DRIVING-023 to -027 and -029 with injected degradations";
      attribute :>> evidenceOrGap = "no runtime evidence of record; GAP-DRIVING-005 (the actuation-side stop has no cause on this path)";
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
      attribute :>> softwareContractArtifact = "out: the mw::com command event from the agent to the actuation adapter (the layer's mw::com configuration, phase 10), candidate; S-CORE communication and nothing beside it (REQ-DRIVING-014)";
      attribute :>> softwareContractMessage = "out: VehicleMotionCommandPayload, one event per command, candidate";
      attribute :>> softwareContractField = "out: acceleration, steeringAngle, productionTime, planReference, exact";
      attribute :>> dataTypeAndUnit = "out: acceleration float m/s^2 (negative decelerates), steeringAngle float degrees (positive to the left, the sign of Vehicle_Chassis_SteeringWheel_Angle), productionTime wall-clock seconds, planReference string";
      attribute :>> timingQualityAndState = "one command per step from the newest valid plan (REQ-DRIVING-011), stamped (REQ-DRIVING-032); in the stop response a deceleration of 4 m/s^2 with the steering angle held until standstill (REQ-DRIVING-020 to -022); the adapter treats 200 ms of simulation time without a valid command as loss (REQ-DRIVING-028)";
      attribute :>> transformationRule = "plan to command: the acceleration and the curvature of the plan at the control horizon, the curvature to a front-wheel angle by the wheelbase the configuration names, both clipped to the vehicle limits it names (REQ-DRIVING-012); the conversion is the control part of the framing gap gapModelInputAndFeedback";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "phase 10: author the command event's mw::com configuration with the two extension candidates and run REQ-DRIVING-011, -012, -014, -020 to -022 and -032 with hop logs";
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
      attribute :>> softwareContractArtifact = "in: the mw::com command event, candidate; out: the simulator client library's vehicle control applied to the ego vehicle, candidate, release pinned in phase 10";
      attribute :>> softwareContractMessage = "out: VehicleControl per applied command, candidate";
      attribute :>> softwareContractField = "out: throttle, brake, steer, exact per the client library";
      attribute :>> dataTypeAndUnit = "out: throttle and brake float 0..1, steer float -1..1, no unit; in: m/s^2 and degrees";
      attribute :>> timingQualityAndState = "applied on arrival, once per command; the simulation time of the world snapshot is read with each application; after 200 ms of simulation time without a valid command the adapter applies the stop response itself (REQ-DRIVING-028) and holds it until standstill (REQ-DRIVING-022)";
      attribute :>> transformationRule = "acceleration to throttle or brake by the vehicle's longitudinal response the configuration names, steering angle to the normalized steer by its maximum steering angle, both clipped (REQ-DRIVING-012); the stop response maps 4 m/s^2 of deceleration to a brake value (REQ-DRIVING-020); the conversion is the actuation part of the framing gap gapModelInputAndFeedback";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "phase 10: identify the vehicle's response on the pinned simulator release, author the conversion and run REQ-DRIVING-012, -020 to -022 and -028 with a withheld command";
      attribute :>> evidenceOrGap = "no runtime evidence of record; GAP-DRIVING-004, GAP-DRIVING-005 (the stop applied here reaches no publication)";
    }
  }

  allocation operationalStateMapping : SystemToSoftwareSignalMappingCandidate
    allocate ClosedLoopDrivingLogicalSystem::statePublisher
    to closedLoopDrivingPhysicalSystem.linuxHost.drivingSoftware.scoreServices.someipd.operationalStateOut {
    item <'MAP-DRIVING-OPERATIONAL-STATE'> operationalStateMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*
       * The operational state on the observation path, hop by hop: the
       * publisher's mw::com event, gatewayd to someipd over the gateway's
       * IPC, SOME/IP across the hypervisor into the SOME/IP interop of SDV
       * Core, the Data Tunnel topic to the SDV Gateway on the IVI VM, the
       * observer. One mapping covers the processes of the chain; the owning
       * allocation targets someipd's port, where the item leaves the host.
       * The topic is typed (decision 4); INC-MW-011 proved opaque frames.
       */
      attribute :>> semanticSource = "the operational state of the driving system for observation: the plan, the motion sample and the health, each with producer and time, and the stop with its cause; a system state publication, no vehicle signal, though the motion sample inside it carries the VSS-typed fields of MAP-DRIVING-EGO-MOTION";
      attribute :>> softwareContractArtifact = "in: the mw::com operational-state event from the publisher, candidate; gatewayd and someipd of the SOME/IP gateway at d9eac670 with their service, instance and event ids (phase 10), candidate; out: the SOME/IP service of the driving operational state and the Data Tunnel topic of SDV Core, typed by a VSIDL message (GAP-DRIVING-006), candidate";
      attribute :>> softwareContractMessage = "one SOME/IP service with three events, plan, vehicle state and health, mapped onto one VSIDL message DrivingOperationalState with a kind field, candidate; the split into three topics is a phase 10 contract decision";
      attribute :>> softwareContractField = "kind, producer, time, and per kind the plan samples, the motion sample fields or the health with the mode and its cause, candidate";
      attribute :>> dataTypeAndUnit = "the plan's metres and radians, the sample's VSS units, an enumeration for the health and the cause, wall-clock seconds for the time; the SOME/IP payload is the VSIDL serialization, exact once pinned";
      attribute :>> timingQualityAndState = "the plan within 100 ms of its production (REQ-DRIVING-015), the motion sample within 100 ms of its receipt (REQ-DRIVING-016), the health at least every 200 ms also without a plan (REQ-DRIVING-017), the stop with its cause within 100 ms (REQ-DRIVING-029); whether the guest receives on time, late or not at all changes no plan (REQ-DRIVING-018, -019): the publisher has no port into the agent";
      attribute :>> transformationRule = "serialization to the VSIDL message at the SOME/IP interop of SDV Core; no value changes on the path; the discard and ordering behaviour of the chain is INC-MW-011's (GAP-MW-037, GAP-MW-045)";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "phase 10, in this order: assign the mw::com instance and the SOME/IP ids, author the VSIDL message and the Data Tunnel topic, build the observer, then run REQ-DRIVING-015 to -019 and -029 with hop logs on both sides of the hypervisor";
      attribute :>> evidenceOrGap = "no runtime evidence of record; GAP-DRIVING-002 (the gateway against Communication v0.6.0), GAP-DRIVING-006 (typed topic), INC-MW-011's GAP-MW-038 (SOME/IP on the guest untested)";
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
     * ids and the VSIDL message (phase 10) and the publication of the
     * actuation-side stop (GAP-DRIVING-005, to be amended in phases 6 and
     * 7); the in-process hops are settled by the owner's reading
     * (reqPlansAndCommandsOverSCOREReading).
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
     * The fixed-execution-order cycle of FEO v1.0.5 can host the loop: four
     * activities with startup, step and shutdown, C++ through the framework's
     * C++ activity bindings, run in the order of the loop once per camera
     * frame at 10 Hz of simulation time, with the step of the inference
     * activity inside the 100 ms wall-clock budget of REQ-DRIVING-013 beside
     * the three others. The framework is described as data-driven or
     * time-driven; the frame-driven pacing and the per-step budget are
     * assumed here and measured by the readiness probe before phase 10
     * builds. If the probe fails, the fallback is ALT-DRIVING-PLAINAPPS-001.
     */
  }

  part <'ASM-DRIVING-002'> asmExportedModelStandsForTheCheckpoint : IncrementAssumption {
    doc /*
     * The inference engine's output over the ONNX export equals the Python
     * reference's output over the pinned checkpoint on the same recorded
     * inputs within a tolerance phase 10 fixes, so that a plan made by the
     * export is a plan made by inference of the pinned checkpoint
     * (REQ-DRIVING-002) and the run identity records both the checkpoint's
     * and the export's SHA-256 (REQ-DRIVING-033). The export tooling is
     * System 2 and is written by DE4SDV; AutoE2E publishes no export of the
     * checkpoint. Until the parity is measured this is an assumption with
     * GAP-DRIVING-003 behind it, not a result.
     */
  }

  part <'ASM-DRIVING-003'> asmSimulatorClientsInsideSCOREApplications : IncrementAssumption {
    doc /*
     * Two simulator clients coexist with the S-CORE applications on one
     * host: the agent's input activity receives the sensor streams on the
     * client library's threads and reads the newest measurement in its
     * step; the actuation adapter applies the vehicle control and reads the
     * world snapshot through a second connection. In asynchronous real-time
     * mode no client ticks the world, so two connections do not interfere.
     * The clients are the bench's; in a vehicle the camera driver and the
     * actuation interface would stand there. The build of the client
     * library against the S-CORE toolchain is GAP-DRIVING-004.
     */
  }

  part <'GAP-DRIVING-001'> gapFEOOutsideReleasedBaseline : IncrementGap {
    doc /*
     * Open: FEO is not in the known_good.json of reference_integration
     * v0.10.0, the baseline the owner pinned (C). It is consumed as a pinned
     * git dependency at v1.0.5 (313b3d849c17881d3a11b6bf62aa2afab6565ef0,
     * released 2026-02-19, Apache-2.0, not vendored), whose module file pins
     * its own Rust toolchain and tooling versions and declares no dependency
     * on Communication, so no version conflict with v0.6.0 arises inside the
     * build, but one toolchain for the Rust framework and the C++ activities
     * beside the C++ applications of the reference integration is unproven.
     * FEO's release note states that it is not released for production and
     * has no safety argumentation. The readiness probe builds a two-activity
     * agent against the v0.10.0 modules before phase 10; failure re-scopes to
     * ALT-DRIVING-PLAINAPPS-001.
     */
    attribute :>> disposition = LifecycleDisposition::deferred;
  }

  part <'GAP-DRIVING-002'> gapSOMEIPGatewayAgainstCommunication060 : IncrementGap {
    doc /*
     * Open: the SOME/IP gateway INC-MW-011 pinned (eclipse-score/inc_someip_gateway
     * d9eac670b7534352749da3d30f52aebf5129f168) was built against Communication
     * 0.5.0, Baselibs 0.2.16 and Lifecycle v0.6.1 of the v0.9.0 baseline.
     * The driving member pins v0.10.0 with Communication 0.6.0; the gateway's
     * build and its mw::com subscription against 0.6.0 are unproven, and the
     * gateway itself is still incubation code outside both baselines
     * (GAP-MW-036). The readiness probe builds gatewayd and someipd against
     * the v0.10.0 modules before phase 10. INC-MW-011 stays on v0.9.0 in its
     * own package.
     */
    attribute :>> disposition = LifecycleDisposition::deferred;
  }

  part <'GAP-DRIVING-003'> gapModelExportAndParityUnproven : IncrementGap {
    doc /*
     * Open: no ONNX export of the pinned checkpoint exists; the source
     * revision's only ONNX references are in an accuracy benchmark of
     * another model. Whether every operator of the checkpoint exports to a
     * supported opset, whether its dynamic shapes export, whether TensorRT
     * builds an engine from the export on the bench GPU and whether the
     * engine's output matches the Python reference within tolerance on
     * recorded inputs is unmeasured; so is the inference time against
     * REQ-DRIVING-013. REQ-DRIVING-035 refuses to plan from a checkpoint the
     * configuration does not name; the export's own SHA-256 is recorded
     * beside it. The readiness probe exports and measures parity before
     * phase 10; an unsupported operator re-scopes to ALT-DRIVING-LIBTORCH-001.
     * Checkpoint and data terms stay open (framing gap gapAdoptionAndRights).
     */
    attribute :>> disposition = LifecycleDisposition::deferred;
  }

  part <'GAP-DRIVING-004'> gapSimulatorClientBuildUnproven : IncrementGap {
    doc /*
     * Open: the simulator's C++ client library (libcarla) is built by the
     * simulator's own toolchain; linking it into S-CORE applications built
     * with the reference integration's gcc 12.2 toolchain under Bazel, with
     * one C++ standard library for both, is unproven, and the simulator
     * release is not pinned before the scenario is. If the library cannot be
     * linked, ALT-DRIVING-SIMBRIDGE-001 moves the client into a separate
     * bridge process built with the simulator's toolchain, at the cost of
     * one hop and one copy per frame. The readiness probe links a client
     * that reads one camera frame and applies one vehicle control before
     * phase 10.
     */
    attribute :>> disposition = LifecycleDisposition::deferred;
  }

  part <'GAP-DRIVING-005'> gapActuationStopUnobservable : IncrementGap {
    doc /*
     * Open, found by this placement: REQ-DRIVING-028 is allocated to
     * applyCommands and so to the actuation adapter, REQ-DRIVING-029 to
     * publishState and so to the publisher, and phase 6 has no flow and
     * phase 7 no connection from the actuation gateway to the publisher. The
     * adapter's own stop response, applied when no valid command arrives for
     * 200 ms of simulation time, therefore has no path to be published with
     * its cause; with the adapter a process of its own the loss case is
     * real (a lost mw::com hop or a stopped agent). The publisher sees the
     * mode of the supervision only, and the supervision cannot see the
     * command hop. Phase 8 adds no connection the logical architecture does
     * not have. The owner decided on 2026-11-06: amend phases 6 and 7 with
     * an actuation-state flow to the publisher (off the loop, like the
     * publisher itself). A follow-up increment PR carries the amendment
     * through phases 6, 7 and 8 and retires this record; until it merges
     * the gap is real in the tree.
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
     * readiness probe.
     */
    attribute :>> disposition = LifecycleDisposition::deferred;
  }

  part <'GAP-DRIVING-007'> gapGPUAndKVMHostUnprovisioned : IncrementGap {
    doc /*
     * Open: the bench host needs an NVIDIA GPU for the simulator's rendering
     * and the planner's inference engine, and KVM for two AAOS SDV guests at
     * once. No such host is provisioned; the AAOS build host of the
     * execution environments has no GPU, and the Jetson of the maintainers
     * is arm64 without KVM guests. The framing's gapBoundedCloudCampaign
     * governs the spend: a GPU and KVM host in the cloud is a System 2
     * candidate that needs the owner's campaign authorization, a regional
     * quote and a bounded shutdown before any paid run. Nothing here
     * launches compute.
     */
    attribute :>> disposition = LifecycleDisposition::deferred;
  }


  /* ───────────── Concerns and views of the phase ───────────── */

  concern closedLoopDrivingPhysicalStructureConcern : PhysicalStructureConcern {
    doc /*
     * System architects and software developers need the software and
     * platform elements that realize the driving system on the bench, as
     * they nest: the host with its platform layers, the S-CORE services, the
     * three programs and the four activities of the agent, the simulator
     * and the route provider beside them, and the two AAOS SDV guests.
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
    expose closedLoopDrivingPhysicalSystem::linuxHost::hypervisor;
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
    expose closedLoopDrivingPhysicalSystem::linuxHost::carlaServer;
    expose closedLoopDrivingPhysicalSystem::linuxHost::routeProvider;
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
     * provider: the route. Out of the host: the operational state on
     * SOME/IP into the SDV Core VM and the topic from the SDV Core VM to
     * the IVI VM, and nothing back (aaosObservationFidelityConcern). The
     * parts, their ports and the flows are exposed by name (the ports are
     * declared on the definitions; a wildcard over a usage drew none of
     * them); the insides of the realization and of the guests stay hidden,
     * which the filter on connections does: the delegations inside them
     * drew as boxes with two ends wherever one end was exposed. The
     * hypervisor interfaces, which span levels, are connections too.
     */
    viewpoint selectedPhysicalContextExchangeViewpoint : PhysicalContextExchangeViewpoint {
      frame aaosObservationFidelityConcern;
      frame checkpointCommandAuthorityConcern;
    }
    expose closedLoopDrivingPhysicalSystem;
    expose closedLoopDrivingPhysicalSystem::linuxHost;
    expose closedLoopDrivingPhysicalSystem::linuxHost::operationalStateOut;
    expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware;
    expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::cameraImagesIn;
    expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::egoMotionIn;
    expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::routeIn;
    expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::simulationClockIn;
    expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::vehicleControlOut;
    expose closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware::operationalStateOut;
    expose closedLoopDrivingPhysicalSystem::linuxHost::carlaServer;
    expose closedLoopDrivingPhysicalSystem::linuxHost::carlaServer::cameraStreamOut;
    expose closedLoopDrivingPhysicalSystem::linuxHost::carlaServer::egoMotionOut;
    expose closedLoopDrivingPhysicalSystem::linuxHost::carlaServer::simulationClockOut;
    expose closedLoopDrivingPhysicalSystem::linuxHost::carlaServer::vehicleControlIn;
    expose closedLoopDrivingPhysicalSystem::linuxHost::routeProvider;
    expose closedLoopDrivingPhysicalSystem::linuxHost::routeProvider::routeOut;
    expose closedLoopDrivingPhysicalSystem::linuxHost::cameraStreamOverHostLoopback;
    expose closedLoopDrivingPhysicalSystem::linuxHost::egoMotionOverHostLoopback;
    expose closedLoopDrivingPhysicalSystem::linuxHost::simulationClockOverHostLoopback;
    expose closedLoopDrivingPhysicalSystem::linuxHost::routeFromScenario;
    expose closedLoopDrivingPhysicalSystem::linuxHost::vehicleControlOverHostLoopback;
    expose closedLoopDrivingPhysicalSystem::linuxHost::operationalStateDelegation;
    expose closedLoopDrivingPhysicalSystem::sdvCoreGuest;
    expose closedLoopDrivingPhysicalSystem::sdvCoreGuest::someIpIn;
    expose closedLoopDrivingPhysicalSystem::sdvCoreGuest::topicOut;
    expose closedLoopDrivingPhysicalSystem::hmiGuest;
    expose closedLoopDrivingPhysicalSystem::hmiGuest::topicIn;
    expose closedLoopDrivingPhysicalSystem::operationalStateOverSOMEIPAcrossHypervisor;
    expose closedLoopDrivingPhysicalSystem::operationalStateTopicOverDataTunnelAcrossVMs;
    filter not (@ SysML::AllocationUsage);
    filter not (@ SysML::ConnectionUsage);
    attribute depth = -1;
    attribute showAnnotationRows = false;
    attribute maxCompartmentEntries = 0;
    render asInterconnectionDiagram;
  }
}
