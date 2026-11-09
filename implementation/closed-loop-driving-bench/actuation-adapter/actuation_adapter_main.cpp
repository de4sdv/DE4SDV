// DE4SDV closed-loop driving bench, slice 10b: S-CORE actuation adapter shell.
//
// One S-CORE application (mw::com Communication v0.6.0) with the LibCarla
// 0.9.16 client:
//
//   in   mw::com proxy   de4sdv/driving/command          event "command"
//                        (ICD v2 §2: service id 7404, instance id 1)
//   out  mw::com skeleton de4sdv/driving/actuation_state  event "actuation_state"
//                        (ICD v2 §2: service id 7405, instance id 1)
//   out  CARLA           Vehicle::ApplyControl on the ego vehicle whose
//                        role_name attribute is "hero"
//
// The service ids live in mw_com_config_actuation_adapter.json; 7404/7405 must
// match the ICD v2 table (and the other components' configurations) or the
// skeleton and proxy bind to the wrong service.
//
// The decision logic lives in adapter_core.{h,cpp} (pure C++17, unit tested on
// the build machine); this file only moves samples, applies controls and logs.
//
// Threads: the mw::com receive loop and the CARLA OnTick callback both enter
// Shell, whose mutex serialises the core call, the ApplyControl RPC and the
// log records. The core has its own mutex as well.
//
// Usage:
//   actuation_adapter --run-dir <dir> --config <vehicle_limits.json>
//                     [--host-name score] [--carla-host 127.0.0.1]
//
// MW_COM_CONFIG must name this process's mw::com configuration
// (mw_com_config_actuation_adapter.json), as in the P3/P4 probes.
//
// Logs (ICD v2 section 6): <run_dir>/<host-name>/actuationAdapter.jsonl, events
// start, config, in.command, out.vehicle_control, out.actuation_state,
// stop_response.begin, stop_response.standstill, drop, error, stop.
// Payload fields keep their model names (productionTime, actuationTime,
// stopSince, stopSinceMono) and a sibling "clocks" object names each one's
// clock; shell-only time fields carry the suffix themselves (t_sim_ms,
// arrival_mono_s). No computed latencies are logged: the evaluators compute.
//
// The vehicle limits are the run configuration's (ICD section 5). The values
// read from CARLA's physics control are logged in the config record next to
// the configured ones; a mismatch is the calibration task's signal, not a
// silent override.
#include <atomic>
#include <chrono>
#include <cmath>
#include <csignal>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <memory>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include <unistd.h>
#include <vector>

#include <boost/shared_ptr.hpp>
#include <carla/client/ActorList.h>
#include <carla/client/Client.h>
#include <carla/client/Vehicle.h>
#include <carla/client/World.h>
#include <carla/client/WorldSnapshot.h>
#include <carla/geom/Vector3D.h>
#include <carla/rpc/VehiclePhysicsControl.h>
#include <carla/rpc/WheelPhysicsControl.h>

#include "adapter_config.h"
#include "adapter_core.h"
#include "log_records.h"
#include "de4sdv/driving/payloads.h"
#include "de4sdv/driving/run_log.h"
#include "score/mw/com/runtime.h"
#include "score/mw/com/types.h"

namespace cc = carla::client;
using de4sdv::driving::ActuationStatePayload;
using de4sdv::driving::Cause;
using de4sdv::driving::CaptureTimeMicros;
using de4sdv::driving::JsonNumber;
using de4sdv::driving::JsonString;
using de4sdv::driving::MonotonicSeconds;
using de4sdv::driving::RunLog;
using de4sdv::driving::VehicleMotionCommandPayload;
namespace dlog = de4sdv::driving::log;  // 'log' alone is the C math function
using de4sdv::driving::actuation::ActuationAdapter;
using de4sdv::driving::actuation::ActuationOutput;
using de4sdv::driving::actuation::AdapterConfig;
using de4sdv::driving::actuation::LoadAdapterConfigFile;
using de4sdv::driving::actuation::RejectReason;
using de4sdv::driving::actuation::RejectReasonName;
using de4sdv::driving::actuation::VehicleControlCommand;
using de4sdv::driving::actuation::WorldTick;

namespace {

// ---------------------------------------------------------------- mw::com types

template <typename Trait>
struct CommandInterface : public Trait::Base {
  using Trait::Base::Base;
  typename Trait::template Event<VehicleMotionCommandPayload> command{*this, "command"};
};
using CommandProxy = score::mw::com::AsProxy<CommandInterface>;

template <typename Trait>
struct ActuationStateInterface : public Trait::Base {
  using Trait::Base::Base;
  typename Trait::template Event<ActuationStatePayload> actuation_state{*this, "actuation_state"};
};
using ActuationStateSkeleton = score::mw::com::AsSkeleton<ActuationStateInterface>;

constexpr const char* kCommandSpecifier = "de4sdv/driving/command";
constexpr const char* kActuationStateSpecifier = "de4sdv/driving/actuation_state";

std::atomic<bool> g_stop{false};

void OnSignal(int /*signal*/) { g_stop.store(true); }

const char* CauseName(Cause cause) {
  switch (cause) {
    case Cause::kNone: return "kNone";
    case Cause::kCameraMissing: return "kCameraMissing";
    case Cause::kCameraInvalid: return "kCameraInvalid";
    case Cause::kCameraStale: return "kCameraStale";
    case Cause::kMotionInvalid: return "kMotionInvalid";
    case Cause::kMotionStale: return "kMotionStale";
    case Cause::kRouteStale: return "kRouteStale";
    case Cause::kRouteEmpty: return "kRouteEmpty";
    case Cause::kPlanStale: return "kPlanStale";
    case Cause::kPlanInvalid: return "kPlanInvalid";
    case Cause::kCommandTimeout: return "kCommandTimeout";
    case Cause::kCheckpointRefused: return "kCheckpointRefused";
    case Cause::kRunEnd: return "kRunEnd";
  }
  return "kUnknown";
}

std::string Tag(const std::string& name, const std::string& value) {
  return "\"" + name + "\":" + value;
}

// ---------------------------------------------------------------- Shell

class Shell {
 public:
  Shell(AdapterConfig config, RunLog* log, std::atomic<std::uint64_t>* sequence,
        carla::SharedPtr<cc::Vehicle> vehicle, ActuationStateSkeleton* skeleton)
      : adapter_(std::move(config)),
        log_(log),
        sequence_(sequence),
        vehicle_(std::move(vehicle)),
        skeleton_(skeleton) {}

  // Called on the CARLA client thread, once per world snapshot.
  void OnTick(const cc::WorldSnapshot& snapshot) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (!vehicle_) return;
    const auto actor = snapshot.Find(vehicle_->GetId());
    if (!actor) {
      if (!missing_in_snapshot_logged_) {
        missing_in_snapshot_logged_ = true;
        Log("error", "{\"what\":\"ego vehicle absent from the world snapshot\"}");
      }
      return;
    }
    WorldTick tick;
    tick.frameIndex = static_cast<std::uint64_t>(snapshot.GetFrame());
    tick.speedMps = static_cast<double>(actor->velocity.Length());
    const auto forward = actor->transform.GetForwardVector();
    tick.longitudinalAccelerationMps2 =
        static_cast<double>(actor->acceleration.x * forward.x + actor->acceleration.y * forward.y +
                            actor->acceleration.z * forward.z);
    // The stop's own stamp (ActuationStatePayload::stopSinceMono, ICD v2 §4).
    tick.monotonicSeconds = MonotonicSeconds();
    last_frame_ = tick.frameIndex;
    last_speed_mps_ = tick.speedMps;

    const ActuationOutput out = adapter_.OnWorldTick(tick);
    const bool stop_active = out.stopBegan || out.standstillReached || adapter_.StopLatched();
    const bool never_commanded = adapter_.LastActuationTime() < 0.0;
    if (out.hasControl && (stop_active || out.appliedCommand || never_commanded)) {
      Apply(out.control, tick.frameIndex, stop_active ? "stop" : (out.appliedCommand ? "tick" : "hold"));
    }
    if (out.stopBegan) {
      Log("stop_response.begin", dlog::StopResponseBegin(out.state, CauseName(out.state.cause)));
    }
    if (out.standstillReached) {
      Log("stop_response.standstill",
          dlog::StopResponseStandstill(tick.frameIndex, last_speed_mps_,
                                       CauseName(adapter_.StopCause())));
    }
    if (out.hasState) Publish(out.state);
  }

  // Called on the mw::com receive thread, once per command sample.
  void OnCommand(const VehicleMotionCommandPayload& command) {
    const double arrival = MonotonicSeconds();
    std::lock_guard<std::mutex> lock(mutex_);
    const ActuationOutput out = adapter_.OnCommand(command, arrival);
    LogInCommand(command, arrival, out.reject);
    if (out.reject != RejectReason::kNone) {
      Log("drop", dlog::Drop(command, arrival, RejectReasonName(out.reject),
                             adapter_.RejectedCommandCount()));
      return;
    }
    if (out.hasControl) {
      Apply(out.control, out.frameIndex, "command");
    }
    if (out.hasState) Publish(out.state);
  }

 private:
  void Log(const std::string& event, const std::string& data_json) {
    log_->Write(event, ++(*sequence_), data_json);
  }

  bool Apply(const VehicleControlCommand& command, std::uint64_t frame, const char* trigger) {
    if (!vehicle_) return false;
    cc::Vehicle::Control control;
    control.throttle = static_cast<float>(command.throttle);
    control.steer = static_cast<float>(command.steer);
    control.brake = static_cast<float>(command.brake);
    control.hand_brake = command.handBrake;
    control.manual_gear_shift = false;
    try {
      vehicle_->ApplyControl(control);
    } catch (const std::exception& error) {
      std::ostringstream data;
      data << "{" << Tag("what", JsonString("ApplyControl failed")) << ","
           << Tag("message", JsonString(error.what())) << "}";
      Log("error", data.str());
      return false;
    }
    Log("out.vehicle_control", dlog::VehicleControl(frame, control.throttle, control.brake,
                                                   control.steer, command.handBrake, trigger));
    return true;
  }

  void LogInCommand(const VehicleMotionCommandPayload& command, double arrival,
                    RejectReason reject) {
    Log("in.command", dlog::InCommand(command, arrival, RejectReasonName(reject)));
  }

  void Publish(const ActuationStatePayload& state) {
    auto allocated = skeleton_->actuation_state.Allocate();
    if (!allocated.has_value()) {
      Log("drop", "{\"reason\":\"actuation_state_allocate_failed\"}");
      return;
    }
    auto sample = std::move(allocated).value();
    *sample = state;
    const auto sent = skeleton_->actuation_state.Send(std::move(sample));
    Log("out.actuation_state", dlog::ActuationState(state, CauseName(state.cause)));
    if (!sent.has_value()) {
      Log("error", "{\"what\":\"actuation_state_send_failed\"}");
    }
  }

  ActuationAdapter adapter_;
  RunLog* log_;
  std::atomic<std::uint64_t>* sequence_;
  carla::SharedPtr<cc::Vehicle> vehicle_;
  ActuationStateSkeleton* skeleton_;
  std::mutex mutex_;
  std::uint64_t last_frame_ = 0;
  double last_speed_mps_ = 0.0;
  bool missing_in_snapshot_logged_ = false;
};

// ---------------------------------------------------------------- helpers

std::string RoleName(const cc::Actor& actor) {
  for (const auto& attribute : actor.GetAttributes()) {
    if (attribute.GetId() == "role_name") {
      return attribute.As<std::string>();
    }
  }
  return std::string();
}

carla::SharedPtr<cc::Vehicle> FindHero(cc::World& world) {
  const auto actors = world.GetActors();
  if (!actors) return nullptr;
  for (const auto& actor : *actors->Filter("vehicle.*")) {
    if (RoleName(*actor) == "hero") {
      return boost::static_pointer_cast<cc::Vehicle>(actor);
    }
  }
  return nullptr;
}

struct PhysicsSummary {
  bool valid = false;
  double wheelbase_m = 0.0;
  double max_road_wheel_angle_deg = 0.0;
  float mass_kg = 0.0F;
  std::vector<carla::rpc::WheelPhysicsControl> wheels;
};

PhysicsSummary SummarisePhysics(const cc::Vehicle::PhysicsControl& physics) {
  PhysicsSummary summary;
  summary.mass_kg = physics.mass;
  summary.wheels = physics.wheels;
  if (physics.wheels.size() < 4) return summary;
  // CARLA order: front left, front right, rear left, rear right; x forward.
  const double front_x =
      0.5 * (static_cast<double>(physics.wheels[0].position.x) +
             static_cast<double>(physics.wheels[1].position.x));
  const double rear_x =
      0.5 * (static_cast<double>(physics.wheels[2].position.x) +
             static_cast<double>(physics.wheels[3].position.x));
  summary.wheelbase_m = std::fabs(front_x - rear_x);
  summary.max_road_wheel_angle_deg =
      std::max(static_cast<double>(physics.wheels[0].max_steer_angle),
               static_cast<double>(physics.wheels[1].max_steer_angle));
  summary.valid = summary.wheelbase_m > 0.0 && summary.max_road_wheel_angle_deg > 0.0;
  return summary;
}

std::string PhysicsConfigJson(const AdapterConfig& config, const PhysicsSummary& physics) {
  std::ostringstream data;
  data << "{" << Tag("vehicle_blueprint", JsonString(config.vehicle_blueprint)) << ","
       << Tag("commandLaw", JsonString(config.command_law)) << ","
       << Tag("table_source", JsonString(config.tableSource() ==
                                                 de4sdv::driving::actuation::TableSource::kConfig
                                             ? "config"
                                             : "default")) << ","
       << Tag("table_rows", std::to_string(config.longitudinal.table.size())) << ","
       << "\"configured\":{" << Tag("wheelbase_m", JsonNumber(config.wheelbase_m)) << ","
       << Tag("max_acceleration_mps2", JsonNumber(config.limits.max_acceleration_mps2)) << ","
       << Tag("max_deceleration_mps2", JsonNumber(config.limits.max_deceleration_mps2)) << ","
       << Tag("max_road_wheel_angle_deg", JsonNumber(config.limits.max_road_wheel_angle_deg)) << ","
       << Tag("max_steering_rate_deg_per_s", JsonNumber(config.max_steering_rate_deg_per_s)) << "},"
       << "\"carla\":{" << Tag("physics_valid", physics.valid ? "true" : "false") << ","
       << Tag("wheelbase_m", JsonNumber(physics.wheelbase_m)) << ","
       << Tag("max_road_wheel_angle_deg", JsonNumber(physics.max_road_wheel_angle_deg)) << ","
       << Tag("mass_kg", JsonNumber(physics.mass_kg)) << ",\"wheels\":[";
  for (std::size_t index = 0; index < physics.wheels.size(); ++index) {
    const auto& wheel = physics.wheels[index];
    if (index != 0) data << ",";
    data << "{" << Tag("index", std::to_string(index)) << ","
         << Tag("max_steer_angle_deg", JsonNumber(wheel.max_steer_angle)) << ","
         << Tag("position_m", "[" + JsonNumber(wheel.position.x) + "," +
                                  JsonNumber(wheel.position.y) + "," +
                                  JsonNumber(wheel.position.z) + "]")
         << "}";
  }
  data << "]},"
       << Tag("deltas", "{" + Tag("wheelbase_m", JsonNumber(physics.wheelbase_m - config.wheelbase_m)) +
                            "," +
                            Tag("max_road_wheel_angle_deg",
                                JsonNumber(physics.max_road_wheel_angle_deg -
                                           config.limits.max_road_wheel_angle_deg)) +
                            "}")
       << "}";
  return data.str();
}

void Usage(const char* program) {
  std::fprintf(stderr,
               "usage: %s --run-dir <dir> --config <vehicle_limits.json> "
               "[--host-name score] [--carla-host 127.0.0.1]\n",
               program);
}

}  // namespace

int main(int argc, char** argv) {
  std::string run_dir;
  std::string host_name = "score";
  std::string carla_host = "127.0.0.1";
  std::string config_path;
  for (int i = 1; i < argc; ++i) {
    const std::string argument = argv[i];
    const auto next = [&](const char* flag) -> std::string {
      if (i + 1 >= argc) {
        std::fprintf(stderr, "%s needs a value\n", flag);
        std::exit(1);
      }
      return argv[++i];
    };
    if (argument == "--run-dir") {
      run_dir = next("--run-dir");
    } else if (argument == "--host-name") {
      host_name = next("--host-name");
    } else if (argument == "--carla-host") {
      carla_host = next("--carla-host");
    } else if (argument == "--config") {
      config_path = next("--config");
    } else if (argument == "--help" || argument == "-h") {
      Usage(argv[0]);
      return 0;
    } else {
      std::fprintf(stderr, "unknown argument: %s\n", argument.c_str());
      Usage(argv[0]);
      return 1;
    }
  }
  if (run_dir.empty() || config_path.empty()) {
    Usage(argv[0]);
    return 1;
  }

  const char* mw_config = std::getenv("MW_COM_CONFIG");
  if (mw_config == nullptr) {
    std::fprintf(stderr, "actuationAdapter: MW_COM_CONFIG is unset\n");
    return 2;
  }

  bool config_ok = false;
  std::string config_error;
  AdapterConfig config = LoadAdapterConfigFile(config_path, &config_ok, &config_error);
  if (!config_ok) {
    std::fprintf(stderr, "actuationAdapter: %s\n", config_error.c_str());
    return 3;
  }

  std::error_code directory_error;
  std::filesystem::create_directories(std::filesystem::path(run_dir) / host_name, directory_error);
  const std::string log_path = (std::filesystem::path(run_dir) / host_name / "actuationAdapter.jsonl").string();
  RunLog log(log_path, host_name, "actuationAdapter");
  if (!log.ok()) {
    std::fprintf(stderr, "actuationAdapter: cannot write %s\n", log_path.c_str());
    return 4;
  }
  std::atomic<std::uint64_t> sequence{0};
  const auto write = [&](const std::string& event, const std::string& data) {
    log.Write(event, ++sequence, data);
  };

  std::signal(SIGINT, OnSignal);
  std::signal(SIGTERM, OnSignal);

  {
    std::ostringstream data;
    data << "{" << Tag("pid", std::to_string(static_cast<long long>(::getpid()))) << ","
         << Tag("carla_host", JsonString(carla_host)) << ","
         << Tag("config", JsonString(config_path)) << ","
         << Tag("mw_com_config", JsonString(mw_config)) << ","
         << Tag("run_dir", JsonString(run_dir)) << "}";
    write("start", data.str());
  }

  score::mw::com::runtime::InitializeRuntime(
      score::mw::com::runtime::RuntimeConfiguration{std::string(mw_config)});

  auto state_specifier = score::mw::com::InstanceSpecifier::Create(std::string(kActuationStateSpecifier));
  if (!state_specifier.has_value()) {
    std::fprintf(stderr, "actuationAdapter: bad actuation-state specifier\n");
    return 5;
  }
  auto state_created = ActuationStateSkeleton::Create(state_specifier.value());
  if (!state_created.has_value()) {
    std::fprintf(stderr, "actuationAdapter: skeleton create failed: %s\n",
                 std::string{state_created.error().Message()}.c_str());
    return 6;
  }
  auto skeleton = std::move(state_created).value();
  if (!skeleton.OfferService().has_value()) {
    std::fprintf(stderr, "actuationAdapter: OfferService failed\n");
    return 7;
  }

  auto command_specifier =
      score::mw::com::InstanceSpecifier::Create(std::string(kCommandSpecifier));
  if (!command_specifier.has_value()) {
    std::fprintf(stderr, "actuationAdapter: bad command specifier\n");
    return 8;
  }
  auto handles = CommandProxy::FindService(command_specifier.value());
  for (int attempt = 0; attempt < 300 && !g_stop.load(); ++attempt) {
    handles = CommandProxy::FindService(command_specifier.value());
    if (handles.has_value() && !handles.value().empty()) break;
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
  }
  if (!handles.has_value() || handles.value().empty()) {
    std::fprintf(stderr, "actuationAdapter: command service not found\n");
    write("error", "{\"what\":\"command service not found\"}");
    return 9;
  }
  auto proxy_result = CommandProxy::Create(handles.value().front());
  if (!proxy_result.has_value()) {
    std::fprintf(stderr, "actuationAdapter: proxy create failed\n");
    return 10;
  }
  auto& proxy = proxy_result.value();
  if (!proxy.command.Subscribe(8).has_value()) {
    std::fprintf(stderr, "actuationAdapter: subscribe failed\n");
    return 11;
  }

  std::unique_ptr<cc::Client> client;
  std::unique_ptr<cc::World> world;
  carla::SharedPtr<cc::Vehicle> vehicle;
  PhysicsSummary physics;
  try {
    client = std::make_unique<cc::Client>(carla_host, 2000);
    client->SetTimeout(std::chrono::seconds(30));
    world = std::make_unique<cc::World>(client->GetWorld());
    for (int attempt = 0; attempt < 100 && !g_stop.load() && !vehicle; ++attempt) {
      vehicle = FindHero(*world);
      if (!vehicle) std::this_thread::sleep_for(std::chrono::milliseconds(200));
    }
    if (!vehicle) {
      std::fprintf(stderr, "actuationAdapter: no vehicle with role_name=hero\n");
      write("error", "{\"what\":\"no hero vehicle\"}");
      return 12;
    }
    physics = SummarisePhysics(vehicle->GetPhysicsControl());
  } catch (const std::exception& error) {
    std::fprintf(stderr, "actuationAdapter: CARLA client failed: %s\n", error.what());
    std::ostringstream data;
    data << "{" << Tag("what", JsonString("CARLA client failed")) << ","
         << Tag("message", JsonString(error.what())) << "}";
    write("error", data.str());
    return 13;
  }
  write("config", PhysicsConfigJson(config, physics));

  Shell shell(std::move(config), &log, &sequence, vehicle, &skeleton);
  const std::size_t callback_id = world->OnTick(
      [&shell](cc::WorldSnapshot snapshot) { shell.OnTick(snapshot); });

  std::atomic<bool> receiver_failed{false};
  std::thread receiver([&] {
    while (!g_stop.load()) {
      const auto received = proxy.command.GetNewSamples(
          [&shell](score::mw::com::SamplePtr<VehicleMotionCommandPayload> sample) {
            shell.OnCommand(*sample);
          },
          8);
      if (!received.has_value()) {
        receiver_failed.store(true);
        break;
      }
      std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
  });

  write("ready", "{}");
  while (!g_stop.load() && !receiver_failed.load()) {
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
  }
  if (receiver_failed.load()) {
    g_stop.store(true);
  }

  receiver.join();
  world->RemoveOnTick(callback_id);
  if (receiver_failed.load()) {
    write("error", "{\"what\":\"GetNewSamples failed\"}");
  }
  skeleton.StopOfferService();
  write("stop", "{}");
  return 0;
}
