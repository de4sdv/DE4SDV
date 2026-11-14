// DE4SDV closed-loop driving bench (INC-DRIVING-001, slice 10b): drivingAgent, the C++ side of the
// four FEO activities (DESIGN.md). Stage 1b:
//   - real: configuration, run logs (ICD section 6), the mw::com runtime and the four skeletons
//     offered at init (ICD section 2), the ABI size check, the frame store with one pace datagram
//     per ready frame (FEO event trigger), the decision logic (agent_logic: input conditions,
//     supervision, command, and the records the case evaluators read), the run record (ICD
//     section 8), and the embedded CPython planner (inference "python"; its stub engine needs no
//     GPU) or a C++ stub plan (inference "stub");
//   - stand-ins: a fake world feeds the frame store as LibCarla will (one snapshot and six images
//     per tick) and integrates the commanded acceleration (CARLA and the actuation adapter); it
//     also stands in for the bench controller's fault injections (bench/injection.jsonl, C8); the
//     route channel is a fresh full-corridor announcement at every step.
// Every record of this stage carries "stage": "stage-1b-fake-world", so none can pass for driving
// evidence.
#include "agent_ffi.h"

#include <unistd.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <limits>
#include <memory>
#include <optional>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

#include "score/mw/com/runtime.h"

#include "agent_logic.h"
#include "carla_source.h"
#include "de4sdv/driving/payloads.h"
#include "de4sdv/driving/run_log.h"
#include "ego_motion.h"
#include "frame_store.h"
#include "json_lite.h"
#include "nav_prefetch.h"
#include "navigation_input.h"
#include "pace_signal.h"
#include "planner_bridge.h"
#include "services.h"

namespace dd = de4sdv::driving;
namespace da = de4sdv::driving::agent;
namespace dn = de4sdv::driving::navigation;

static_assert(sizeof(De4sdvPlanSample) == sizeof(dd::PlanSample));
static_assert(sizeof(De4sdvPlanPayload) == sizeof(dd::DrivingPlanPayload));
static_assert(offsetof(De4sdvPlanPayload, samples) == offsetof(dd::DrivingPlanPayload, samples));
static_assert(offsetof(De4sdvPlanPayload, planReference) == offsetof(dd::DrivingPlanPayload, planReference));
static_assert(sizeof(De4sdvModePayload) == sizeof(dd::DrivingModePayload));
static_assert(offsetof(De4sdvModePayload, frameIndex) == offsetof(dd::DrivingModePayload, frameIndex));
static_assert(offsetof(De4sdvModePayload, refusalReason) == offsetof(dd::DrivingModePayload, refusalReason));

namespace {

// Every record names the stage: the stand-ins still in use. Set in de4sdv_agent_init from the source.
std::string g_stage = "stage-1b-fake-world";
const char* Stage() { return g_stage.c_str(); }

struct Config {
  std::string path;
  std::string run_dir;
  std::string mw_com_config;
  std::string source = "fake";     // "fake" (stand-in world) or "carla" (the world side's hero, CarlaSource)
  std::string carla_host = "127.0.0.1";
  double carla_port = 2000;
  double carla_attach_timeout_s = 300.0;
  double carla_rpc_timeout_s = 10.0;
  // Navigation (ICD section 9): the map JSON on this host and the route provider's datagrams. Without
  // nav_map the route channel is the stand-in (a fresh full corridor every step), named in the stage.
  std::string nav_map;
  // The nav prefetch (DESIGN.md): the step's rasters drawn when its snapshot arrives, off the chain.
  bool nav_prefetch = true;
  double nav_prefetch_wait_ms = 5.0;   // a take waits this long for a render in flight, then renders itself
  std::string route_file;     // the route file the provider announces (run record, ICD amendment 2 A19)
  std::string route_host = "127.0.0.1";
  double route_port = 47110;
  std::string inference = "stub";  // "stub" (C++) or "python" (embedded de4sdv_planner)
  std::string python_executable;
  std::vector<std::string> python_paths;
  std::string planner_config;      // JSON file handed to de4sdv_planner.setup
  std::string vehicle_config;      // ICD section 5 document (required)
  int fake_image_width = 64;   // every camera, unless fake_rig names the sizes
  int fake_image_height = 36;
  std::string fake_rig;          // rig JSON (make_fake_rig.py): per-camera sizes and poses for set_rig
  std::string fake_rig_json;     // its content
  int cam_w[da::kCameraCount] = {};
  int cam_h[da::kCameraCount] = {};
  double fake_rate_hz = 10.0;
  std::uint64_t fake_first_frame = 1000;
  std::uint64_t priming_frames = 66;  // 6.4 s ego-motion history + its differences
  double fake_speed_kmh = 18.0;
  double fake_start[4] = {0.0, 0.0, 0.0, 0.0};  // fake_start_pose: UE x, y, z (m), yaw (deg)
  // fake_route: a route file (ICD section 9, map frame); the fake world then drives along its
  // centre line, converted to UE (y = -y_map), instead of straight on from fake_start_pose.
  std::string fake_route;
  std::vector<double> fake_route_x, fake_route_y, fake_route_s;  // UE, cumulative length
  // Run record (ICD section 8, C4).
  std::string campaign_id = "wp2-stage-1b";
  std::string run_role = "integration";
  std::string scenario = "degradedInputOrPlan";
  std::string fault = "none";
  std::string aaos_mode = "absent";
  std::string checkpoint_case = "pinned";
  std::string score_feo_revision = "unknown";
  // Fault injection by the fake world (stand-in for the bench controller, C8); 0 = off.
  std::uint64_t fault_camera_stop_frame = 0;
  std::uint64_t fault_camera_index = 2;
  std::uint64_t fault_plan_stall_frame = 0;
  std::uint64_t fault_plan_invalid_frame = 0;
};

std::string ReadFile(const std::string& path, bool* ok) {
  std::ifstream in(path);
  std::stringstream ss;
  ss << in.rdbuf();
  *ok = static_cast<bool>(in) || in.eof();
  return ss.str();
}

bool LoadConfig(const std::string& path, Config* cfg, std::string* error) {
  bool ok = false;
  const std::string text = ReadFile(path, &ok);
  if (!ok || text.empty()) {
    *error = "cannot read " + path;
    return false;
  }
  const auto doc = dd::json::Value::Parse(text, error);
  if (!doc.IsObject()) return false;
  cfg->path = path;
  auto str = [&](const char* key, std::string* out) {
    if (const auto* v = doc.Find(key)) *out = v->AsString(*out);
  };
  auto u64 = [&](const char* key, std::uint64_t* out) {
    if (const auto* v = doc.Find(key)) *out = static_cast<std::uint64_t>(v->AsNumber(static_cast<double>(*out)));
  };
  auto num = [&](const char* key, double* out) {
    if (const auto* v = doc.Find(key)) *out = v->AsNumber(*out);
  };
  str("run_dir", &cfg->run_dir);
  str("mw_com_config", &cfg->mw_com_config);
  str("source", &cfg->source);
  str("carla_host", &cfg->carla_host);
  num("carla_port", &cfg->carla_port);
  num("carla_attach_timeout_s", &cfg->carla_attach_timeout_s);
  num("carla_rpc_timeout_s", &cfg->carla_rpc_timeout_s);
  str("nav_map", &cfg->nav_map);
  if (const auto* v = doc.Find("nav_prefetch")) cfg->nav_prefetch = v->AsBool(cfg->nav_prefetch);
  num("nav_prefetch_wait_ms", &cfg->nav_prefetch_wait_ms);
  str("route_file", &cfg->route_file);
  str("route_host", &cfg->route_host);
  num("route_port", &cfg->route_port);
  str("inference", &cfg->inference);
  str("python_executable", &cfg->python_executable);
  str("planner_config", &cfg->planner_config);
  str("vehicle_config", &cfg->vehicle_config);
  str("fake_rig", &cfg->fake_rig);
  if (const auto* v = doc.Find("python_paths")) {
    for (const auto& item : v->items()) cfg->python_paths.push_back(item.AsString(""));
  }
  double fw = cfg->fake_image_width, fh = cfg->fake_image_height;
  num("fake_image_width", &fw);
  num("fake_image_height", &fh);
  cfg->fake_image_width = static_cast<int>(fw);
  cfg->fake_image_height = static_cast<int>(fh);
  num("fake_rate_hz", &cfg->fake_rate_hz);
  u64("fake_first_frame", &cfg->fake_first_frame);
  u64("priming_frames", &cfg->priming_frames);
  num("fake_speed_kmh", &cfg->fake_speed_kmh);
  str("fake_route", &cfg->fake_route);
  if (!cfg->fake_route.empty()) {
    bool route_ok = false;
    const std::string route_text = ReadFile(cfg->fake_route, &route_ok);
    std::string route_error;
    const auto route = dd::json::Value::Parse(route_text, &route_error);
    const auto* wps = route.IsObject() ? route.Find("waypoints") : nullptr;
    if (!route_ok || wps == nullptr || wps->items().size() < 2) {
      *error = "fake_route " + cfg->fake_route + " has no waypoints " + route_error;
      return false;
    }
    double s_acc = 0.0;
    for (const auto& w : wps->items()) {
      const double x = w.items().at(0).AsNumber(0.0), y = -w.items().at(1).AsNumber(0.0);
      if (!cfg->fake_route_x.empty()) s_acc += std::hypot(x - cfg->fake_route_x.back(), y - cfg->fake_route_y.back());
      cfg->fake_route_x.push_back(x);
      cfg->fake_route_y.push_back(y);
      cfg->fake_route_s.push_back(s_acc);
    }
  }
  if (const auto* sp = doc.Find("fake_start_pose")) {
    if (sp->items().size() != 4) {
      *error = "fake_start_pose needs [x, y, z, yaw_deg]";
      return false;
    }
    for (std::size_t i = 0; i < 4; ++i) cfg->fake_start[i] = sp->items()[i].AsNumber(0.0);
  }
  str("campaign_id", &cfg->campaign_id);
  str("run_role", &cfg->run_role);
  str("scenario", &cfg->scenario);
  str("fault", &cfg->fault);
  str("aaos_mode", &cfg->aaos_mode);
  str("checkpoint_case", &cfg->checkpoint_case);
  str("score_feo_revision", &cfg->score_feo_revision);
  u64("fault_camera_stop_frame", &cfg->fault_camera_stop_frame);
  u64("fault_camera_index", &cfg->fault_camera_index);
  u64("fault_plan_stall_frame", &cfg->fault_plan_stall_frame);
  u64("fault_plan_invalid_frame", &cfg->fault_plan_invalid_frame);
  if (cfg->run_dir.empty() || cfg->mw_com_config.empty() || cfg->vehicle_config.empty()) {
    *error = "run_dir, mw_com_config and vehicle_config are required";
    return false;
  }
  if ((cfg->source != "fake" && cfg->source != "carla") || (cfg->inference != "stub" && cfg->inference != "python")) {
    *error = "source must be fake|carla and inference stub|python";
    return false;
  }
  if (cfg->inference == "python" && (cfg->python_executable.empty() || cfg->planner_config.empty())) {
    *error = "inference=python needs python_executable and planner_config";
    return false;
  }
  if (cfg->fault_camera_index >= da::kCameraCount || cfg->fake_rate_hz <= 0.0 || cfg->fake_image_width <= 0 ||
      cfg->fake_image_height <= 0) {
    *error = "fault_camera_index, fake_rate_hz or the fake image size is out of range";
    return false;
  }
  for (std::size_t i = 0; i < da::kCameraCount; ++i) {
    cfg->cam_w[i] = cfg->fake_image_width;
    cfg->cam_h[i] = cfg->fake_image_height;
  }
  if (!cfg->fake_rig.empty()) {
    bool rig_ok = false;
    cfg->fake_rig_json = ReadFile(cfg->fake_rig, &rig_ok);
    std::string rig_error;
    const auto rig = dd::json::Value::Parse(cfg->fake_rig_json, &rig_error);
    const auto* cams = rig.IsObject() ? rig.Find("cameras") : nullptr;
    if (!rig_ok || cams == nullptr || cams->items().size() != da::kCameraCount) {
      *error = "fake_rig " + cfg->fake_rig + " is unreadable or does not hold six cameras " + rig_error;
      return false;
    }
    for (std::size_t i = 0; i < da::kCameraCount; ++i) {
      const auto& cam = cams->items()[i];
      cfg->cam_w[i] = cam.Find("width") ? static_cast<int>(cam.Find("width")->AsNumber(0)) : 0;
      cfg->cam_h[i] = cam.Find("height") ? static_cast<int>(cam.Find("height")->AsNumber(0)) : 0;
      if (cfg->cam_w[i] <= 0 || cfg->cam_h[i] <= 0) {
        *error = "fake_rig camera " + std::to_string(i) + " has no size";
        return false;
      }
    }
  }
  return true;
}

std::int64_t MonoNs() {
  return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch())
      .count();
}

std::int64_t RealNs() {
  return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::system_clock::now().time_since_epoch())
      .count();
}

// Every record of this stage names it: "stage" is inserted as the object's first member.
std::string WithStage(const std::string& object_json) {
  if (object_json.size() < 2 || object_json.front() != '{') return object_json;
  const std::string head = std::string("{\"stage\":\"") + Stage() + "\"";
  return object_json == "{}" ? head + "}" : head + "," + object_json.substr(1);
}

// Appends one member to a JSON object.
std::string WithMember(const std::string& object_json, const std::string& key, const std::string& value_json) {
  if (object_json.size() < 2 || object_json.back() != '}') return object_json;
  return object_json.substr(0, object_json.size() - 1) + ",\"" + key + "\":" + value_json + "}";
}

std::string CStr(const char* s, std::size_t n) { return std::string(s, strnlen(s, n)); }

void CopyId(char* dst, std::size_t n, const std::string& src) {
  std::memset(dst, 0, n);
  std::memcpy(dst, src.data(), std::min(n - 1, src.size()));
}

struct Agent;
Agent* g_agent = nullptr;
void Log(const char* event, const std::string& data);
void Bench(const char* action, std::uint64_t frame, const std::string& detail_json);

// Stand-in for CARLA, LibCarla's callbacks and the actuation adapter: one world tick per period, the
// hero's snapshot and six patterned BGRA images into the frame store (from the tick thread, as
// LibCarla's callback threads will), the commanded acceleration integrated into the speed, and the
// owner-driven 5 ms deadline sweep of the store.
class FakeWorld {
 public:
  FakeWorld(const Config& cfg, da::FrameStore* store)
      : cfg_(cfg),
        store_(store),
        period_(std::chrono::nanoseconds(static_cast<std::int64_t>(1e9 / cfg.fake_rate_hz))),
        next_frame_(cfg.fake_first_frame),
        speed_mps_(cfg.fake_speed_kmh / 3.6) {
    for (std::size_t i = 0; i < da::kCameraCount; ++i) {
      images_.emplace_back(static_cast<std::size_t>(cfg.cam_w[i]) * cfg.cam_h[i] * 4);
    }
  }
  void Start() {
    running_ = true;
    tick_ = std::thread([this] { TickLoop(); });
    poll_ = std::thread([this] { PollLoop(); });
  }
  void Stop() {
    running_ = false;
    if (tick_.joinable()) tick_.join();
    if (poll_.joinable()) poll_.join();
  }
  void SetAcceleration(float a) { accel_.store(a); }
  std::uint64_t produced() const { return produced_.load(); }

 private:
  void TickLoop() {
    const double dt = 1.0 / cfg_.fake_rate_hz;
    double x = 0.0;
    auto t = std::chrono::steady_clock::now();
    while (running_.load()) {
      t += period_;
      std::this_thread::sleep_until(t);
      const std::uint64_t n = next_frame_++;
      const double v_prev = speed_mps_;
      speed_mps_ = std::max(0.0, speed_mps_ + static_cast<double>(accel_.load()) * dt);
      x += 0.5 * (speed_mps_ + v_prev) * dt;
      da::HeroSnapshot s{};
      if (!cfg_.fake_route_s.empty()) {  // along the route's centre line (UE), x = distance driven
        const auto& rs = cfg_.fake_route_s;
        const double d = std::min(x, rs.back());
        std::size_t i = 1;
        while (i + 1 < rs.size() && rs[i] < d) ++i;
        const double seg = std::max(1e-9, rs[i] - rs[i - 1]);
        const double t = std::clamp((d - rs[i - 1]) / seg, 0.0, 1.0);
        const double dx = cfg_.fake_route_x[i] - cfg_.fake_route_x[i - 1];
        const double dy = cfg_.fake_route_y[i] - cfg_.fake_route_y[i - 1];
        s.pose.x = cfg_.fake_route_x[i - 1] + t * dx;
        s.pose.y = cfg_.fake_route_y[i - 1] + t * dy;
        s.pose.yaw = std::atan2(dy, dx) * 180.0 / M_PI;
        double dyaw = s.pose.yaw - last_yaw_deg_;  // UE yaw rate: CARLA's z angular velocity
        while (dyaw > 180.0) dyaw -= 360.0;
        while (dyaw < -180.0) dyaw += 360.0;
        s.angularVelocity.z = produced_.load() > 0 ? dyaw * M_PI / 180.0 / dt : 0.0;
        last_yaw_deg_ = s.pose.yaw;
      } else {
        const double yaw = cfg_.fake_start[3] * M_PI / 180.0;  // straight on from fake_start_pose
        s.pose.x = cfg_.fake_start[0] + x * std::cos(yaw);
        s.pose.y = cfg_.fake_start[1] + x * std::sin(yaw);
        s.pose.z = cfg_.fake_start[2];
        s.pose.yaw = cfg_.fake_start[3];
      }
      s.velocity.x = speed_mps_;  // vehicle frame
      s.acceleration.x = (speed_mps_ - v_prev) / dt;
      store_->OnSnapshot(n, s, MonoNs());
      for (std::size_t cam = 0; cam < da::kCameraCount; ++cam) {
        if (cfg_.fault_camera_stop_frame != 0 && n >= cfg_.fault_camera_stop_frame && cam == cfg_.fault_camera_index) {
          if (!camera_stop_logged_) {
            camera_stop_logged_ = true;
            Bench("camera_stop", n, std::string("{\"camera\":\"") + da::CameraName(cam) + "\",\"fault\":\"camera_missing\"}");
          }
          continue;  // the images of this camera are withheld from frame n on
        }
        std::memset(images_[cam].data(), static_cast<int>((n + cam) & 0xff), images_[cam].size());
        store_->OnImage(cam, n, images_[cam].data(), images_[cam].size(), cfg_.cam_w[cam], cfg_.cam_h[cam], 90.0,
                        MonoNs());
      }
      produced_.fetch_add(1);
    }
  }
  void PollLoop() {
    while (running_.load()) {
      store_->PollDeadlines(MonoNs());
      std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }
  }

  const Config& cfg_;
  da::FrameStore* store_;
  std::chrono::nanoseconds period_;
  std::uint64_t next_frame_;
  double speed_mps_;
  std::atomic<float> accel_{0.0f};
  std::atomic<bool> running_{false};
  std::atomic<std::uint64_t> produced_{0};
  bool camera_stop_logged_ = false;
  double last_yaw_deg_ = 0.0;
  std::vector<std::vector<std::uint8_t>> images_;
  std::thread tick_;
  std::thread poll_;
};

struct Agent {
  Config cfg;
  std::unique_ptr<dd::RunLog> log;
  std::unique_ptr<dd::RunLog> inputs_log;  // score/checkpointInputs.jsonl (ICD section 10, C2)
  std::unique_ptr<dd::RunLog> bench_log;   // bench/injection.jsonl (C8), the fake world's injections
  std::atomic<std::uint64_t> seq{0};
  std::atomic<std::uint64_t> inputs_seq{0};
  std::atomic<std::uint64_t> bench_seq{0};
  std::optional<da::EgoMotionSampleSkeleton> ego_skeleton;
  std::optional<da::PlanSkeleton> plan_skeleton;
  std::optional<da::ModeSkeleton> mode_skeleton;
  std::optional<da::CommandSkeleton> command_skeleton;
  std::unique_ptr<da::PaceSignal> pace;
  std::unique_ptr<da::FrameStore> store;
  std::unique_ptr<FakeWorld> world;
  da::CameraSize sizes[da::kCameraCount];
  da::VehicleConfig vehicle;
  da::PlannerBridge planner;
  bool python = false;
  da::PlannerBridge::Identity identity;
  da::RefusalDetail refusal;
  std::string run_identity = "no-run-record";
  double setup_s = 0.0;          // the engine build in BuildEngine
  std::unique_ptr<da::CarlaSource> carla;  // source == "carla"
  std::string carla_rig_json;             // read at Attach
  std::string setup_config_json;          // the planner configuration handed to setup
  std::unique_ptr<da::NavigationInput> nav;  // nav_map set
  // Declared after nav: destroyed (its thread joined) before it. The store's snapshot sink calls it.
  std::unique_ptr<da::NavPrefetch<da::NavPrefetchResult>> nav_prefetch;  // nav_map and nav_prefetch set
  std::vector<float> nav_hit_map, nav_hit_route;  // a hit's rasters, kept until the next step's
  std::uint64_t nav_hits = 0, nav_route_changed = 0, nav_pose_changed = 0, nav_render_failed = 0,
                nav_not_submitted = 0, nav_timed_out = 0;
  double ref_origin[3] = {0.0, 0.0, 0.0};   // REF in the vehicle UE frame, from set_rig
  // What the engine hands the checkpoint (set_rig; ICD amendments 1 and 2): the tile size (0: the
  // engine hands the simulator image as it is), the front high-resolution size and the projection
  // operators, written once into C2.
  int tile_w = 0, tile_h = 0;
  std::string front_hi_res_json, c2_projections_json;
  bool c2_projections_written = false;
  std::string setup_result = "{}";  // de4sdv_planner.setup's result
  bool rig_set = false;
  // conditionInputs
  std::uint64_t first_frame = 0;
  std::uint64_t steps = 0;
  bool priming_logged = false;
  std::uint64_t merged_conditioned = 0;      // merged frames in the histories (DESIGN.md, merged frames)
  std::uint64_t merged_not_conditioned = 0;  // merged frames left out: an input not valid, or no planner
  da::CameraHistory camera_history;          // ICD A28: each camera's newest valid image to date
  // inferPlan
  bool stall_logged = false;
  std::uint64_t warm_calls = 0;     // warm-up calls while priming (DESIGN.md)
  // superviseLoop / commandVehicle
  std::unique_ptr<da::Supervisor> supervisor;
  std::unique_ptr<da::Commander> commander;
  bool standstill_logged = false;
  std::uint64_t in_plan_frame = 0;
  bool in_plan_logged = false;
  std::uint64_t commands = 0;
};

void Log(const char* event, const std::string& data) {
  if (g_agent != nullptr && g_agent->log) g_agent->log->Write(event, g_agent->seq.fetch_add(1), data);
}

// C8: {action, t_sim_ms, t_mono_ns, t_real_ns, detail}.
void Bench(const char* action, std::uint64_t frame, const std::string& detail_json) {
  if (g_agent == nullptr || !g_agent->bench_log) return;
  std::ostringstream os;
  os << "{\"stage\":\"" << Stage() << "\",\"action\":" << dd::JsonString(action) << ",\"t_sim_ms\":" << frame * 100
     << ",\"t_mono_ns\":" << MonoNs() << ",\"t_real_ns\":" << RealNs() << ",\"detail\":" << detail_json << "}";
  g_agent->bench_log->Write("injection", g_agent->bench_seq.fetch_add(1), os.str());
}

template <typename EventT, typename T>
bool Publish(EventT& event, const T& value, const char* name) {
  auto allocated = event.Allocate();
  if (!allocated.has_value()) {
    Log("drop", std::string("{\"reason\":\"allocate_failed\",\"event\":") + dd::JsonString(name) + "}");
    return false;
  }
  auto sample = std::move(allocated).value();
  *sample = value;
  if (!event.Send(std::move(sample)).has_value()) {
    Log("error", std::string("{\"what\":\"send_failed\",\"event\":") + dd::JsonString(name) + "}");
    return false;
  }
  return true;
}

template <typename SkeletonT>
bool Offer(std::optional<SkeletonT>* slot, const char* specifier_text) {
  auto specifier = score::mw::com::InstanceSpecifier::Create(std::string{specifier_text});
  if (!specifier.has_value()) {
    std::fprintf(stderr, "drivingAgent: bad instance specifier %s\n", specifier_text);
    return false;
  }
  auto created = SkeletonT::Create(specifier.value());
  if (!created.has_value()) {
    std::fprintf(stderr, "drivingAgent: skeleton create failed for %s: %s\n", specifier_text,
                 std::string{created.error().Message()}.c_str());
    return false;
  }
  slot->emplace(std::move(created).value());
  if (!(*slot)->OfferService().has_value()) {
    std::fprintf(stderr, "drivingAgent: OfferService failed for %s\n", specifier_text);
    return false;
  }
  return true;
}

std::string CausesJson(const da::ConditionResult& r) {
  std::string out = "[";
  for (std::size_t i = 0; i < r.causes.size(); ++i) {
    out += (i ? "," : "") + dd::JsonString(da::CauseName(r.causes[i]));
  }
  return out + "]";
}

// The condition word superviseLoop receives over the FEO topic, back to the judged form.
da::ConditionResult FromBits(std::uint32_t bits) {
  da::ConditionResult r;
  r.bits = bits;
  for (unsigned v = 1; v < 32; ++v) {
    if ((bits & (1u << v)) != 0) r.causes.push_back(static_cast<dd::Cause>(v));
  }
  return r;
}

// The measured ego-motion sample of a frame (VSS units), from the hero's snapshot.
// VSS signs (ISO 8855, left positive) and units: ego_motion.h, tests/ego_motion_test.cpp.
dd::EgoMotionSamplePayload EgoFromSnapshot(const da::HeroSnapshot& s, std::uint64_t frame) {
  return da::EgoSampleFromSnapshot(s, frame);
}

std::string RowsJson(const float rows[64][4]) {
  std::ostringstream os;
  os << "[";
  for (int r = 0; r < 64; ++r) {
    os << (r ? "," : "") << "[" << dd::JsonNumber(rows[r][0]) << "," << dd::JsonNumber(rows[r][1]) << ","
       << dd::JsonNumber(rows[r][2]) << "," << dd::JsonNumber(rows[r][3]) << "]";
  }
  os << "]";
  return os.str();
}

// Stage-1b stand-in for the rig the world side spawns: a vehicle at the origin, six cameras.
std::string FakeRigJson(const Config& cfg) {
  std::ostringstream os;
  os << "{\"vehicle\":{\"world_matrix\":[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1],\"location\":[0,0,0],"
        "\"wheel_positions\":[[1.4,-0.8,0.35],[1.4,0.8,0.35],[-1.45,-0.8,0.35],[-1.45,0.8,0.35]],"
        "\"wheel_radii\":[0.35,0.35,0.35,0.35]},\"cameras\":[";
  for (std::size_t i = 0; i < da::kCameraCount; ++i) {
    os << (i ? "," : "") << "{\"width\":" << cfg.cam_w[i] << ",\"height\":" << cfg.cam_h[i]
       << ",\"fov\":90.0,\"world_matrix\":[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]}";
  }
  os << "],\"stage\":\"" << Stage() << "\"}";
  return os.str();
}

// The status of one camera at a step: the rules of REQ-DRIVING-023 per camera, for C2.
const char* CameraStatus(const da::CameraView& cv, const da::CameraSize& size, std::uint64_t step_frame) {
  if (!cv.present) return "missing";
  if (!cv.valid || cv.size == 0 || cv.width != size.width || cv.height != size.height) return "invalid";
  if (da::AgeMs(step_frame, cv.imageFrame) > da::kCameraStaleMs) return "stale";
  return "valid";
}

// The checkpoint's inputs from one slot: the six images and the hero's pose (no map context).
void FillConditionIn(const da::FrameView& view, da::PlannerBridge::ConditionIn* in) {
  in->frame = view.frame;
  for (std::size_t i = 0; i < da::kCameraCount; ++i) {
    in->image[i] = view.cameras[i].data;
    in->image_bytes[i] = view.cameras[i].size;
    in->width[i] = view.cameras[i].width;
    in->height[i] = view.cameras[i].height;
  }
  // UE local -> world, row-major: GetMatrix's columns are the forward, right and up axes
  const auto& pose = view.snapshot.pose;
  double f[3], r[3], u[3];
  da::CarlaAxes(pose.pitch, pose.yaw, pose.roll, f, r, u);
  const double m[16] = {f[0], r[0], u[0], pose.x, f[1], r[1], u[1], pose.y,
                        f[2], r[2], u[2], pose.z, 0.0,  0.0,  0.0,  1.0};
  for (int i = 0; i < 16; ++i) in->world_from_vehicle[i] = m[i];
}

// Merged frames (DESIGN.md, merged frames): the older ready frames FEO merged into this chain, oldest
// first. Each goes into the checkpoint's histories (camera tiles, pose, ego-motion rows) and is released
// at once; none is planned, gets a C2 step record or an ego_motion_sample. A merged frame with a camera
// that is not valid is left out, and the histories re-prime as after a skipped frame. Returns the C2
// "mergedFrames" list; on a planner error every handle is released and the error is returned.
bool ConditionMerged(Agent& a, std::vector<da::FrameHandle>& merged, std::string* json, std::string* error) {
  std::ostringstream os;
  os << "[";
  bool ok = true;
  for (std::size_t m = 0; m < merged.size(); ++m) {
    da::FrameHandle& handle = merged[m];
    if (!ok) {
      a.store->Release(handle);
      continue;
    }
    const da::FrameView& view = handle.view();
    const char* why = nullptr;
    if (!a.python) why = "no_planner";
    else if (a.refusal.refused) why = "refused";
    for (std::size_t i = 0; why == nullptr && i < da::kCameraCount; ++i) {
      if (std::strcmp(CameraStatus(view.cameras[i], a.sizes[i], view.frame), "valid") != 0) why = "camera_not_valid";
    }
    double ms = 0.0;
    if (why == nullptr) {
      da::PlannerBridge::ConditionIn in;
      FillConditionIn(view, &in);
      da::PlannerBridge::ConditionOut out;
      const auto t0 = std::chrono::steady_clock::now();
      if (!a.planner.Condition(in, &out, error)) {
        *error = "merged frame " + std::to_string(view.frame) + ": " + *error;
        ok = false;
        a.store->Release(handle);
        continue;
      }
      ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
      ++a.merged_conditioned;
      a.camera_history.RecordMergedFrame(view.frame);  // ICD A28: its six valid images count as received
    } else {
      ++a.merged_not_conditioned;
    }
    os << (m ? "," : "") << "{\"frame\":" << view.frame << ",\"conditioned\":" << (why == nullptr ? "true" : "false");
    if (why != nullptr) os << ",\"why\":\"" << why << "\"";
    os << ",\"condition_ms\":" << dd::JsonNumber(ms) << ",\"readyByDeadline\":" << (view.readyByDeadline ? "true" : "false")
       << "}";
    a.store->Release(handle);
  }
  os << "]";
  *json = os.str();
  return ok;
}

// ---------------------------------------------------------------- the engine, before FEO starts
// FEO waits for each activity's ready signal with its receive timeout (5 s), whatever the startup
// timeout says, and the checkpoint's load, compile, warm-up and parity take about a minute. So the
// engine is built here, on the main thread before the primary starts; inferPlan's startup binds it to
// worker 40 (PlannerBridge::BindThread). A refused checkpoint (REQ-DRIVING-035) is decided here too:
// the agent still starts, offers its services and reports kRefused from the first step.
bool BuildEngine(Agent& a) {
  if (!a.python) return true;
  bool ok = false;
  const std::string setup_json = ReadFile(a.cfg.planner_config, &ok);
  if (!ok || setup_json.empty()) {
    Log("error", "{\"what\":\"planner_config_unreadable\",\"path\":" + dd::JsonString(a.cfg.planner_config) + "}");
    return false;
  }
  std::string result, error;
  const auto t0 = std::chrono::steady_clock::now();
  if (!a.planner.Start(a.cfg.python_executable, a.cfg.python_paths, setup_json, &a.identity, &result, &error)) {
    Log("error", "{\"what\":\"planner_start_failed\",\"message\":" + dd::JsonString(error) + "}");
    return false;
  }
  a.setup_s = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
  a.setup_result = result;
  a.setup_config_json = setup_json;
  if (a.identity.refused) {
    // REQ-DRIVING-035: inferPlan starts but never plans; the supervision reports kRefused.
    a.refusal.refused = true;
    a.refusal.expected_sha256 = a.identity.expected;
    a.refusal.actual_sha256 = a.identity.actual;
    a.refusal.reason = a.identity.reason;
    Log("error", WithStage(da::record::CheckpointRefusedError(a.refusal)));
  }
  Log("engine", "{\"stage\":\"" + std::string(Stage()) + "\",\"setup_s\":" + dd::JsonNumber(a.setup_s) +
                    ",\"refused\":" + (a.refusal.refused ? "true" : "false") + ",\"setup\":" + result + "}");
  return true;
}

// ICD section 8: the run record, written once the source is attached and before FEO starts (a
// refused run writes it too, REQ-DRIVING-035).
bool WriteRunRecordNow(Agent& a, const std::string& simulator_build) {
  if (!a.python) return true;
  std::string error;
  // ICD section 8: the run record, before the first plan; its identity names every plan.
  std::string checkpoint_path, camera_profile;
  {
    std::string parse_error;
    const auto doc = dd::json::Value::Parse(a.setup_config_json, &parse_error);
    if (doc.IsObject()) {
      if (const auto* v = doc.Find("checkpoint_path")) checkpoint_path = v->AsString("");
      if (const auto* v = doc.Find("profile")) camera_profile = v->AsString("");
    }
  }
  // ICD amendment 2 A19: every file that shapes the inputs is named with its SHA-256 (the
  // writer hashes each {"path"} object). The hero starts at rest in CARLA runs (A20).
  const auto path_field = [](const char* key, const std::string& path) {
    return path.empty() ? std::string() : ",\"" + std::string(key) + "\":{\"path\":" + dd::JsonString(path) + "}";
  };
  std::ostringstream fields;
  fields << "{\"stage\":\"" << Stage() << "\",\"contractIdentity\":\"de4sdv.driving.icd.v2\""
         << ",\"scenario\":" << dd::JsonString(a.cfg.scenario) << ",\"scenarioVariant\":{\"fault\":"
         << dd::JsonString(a.cfg.fault) << ",\"entrySpeedMps\":" << dd::JsonNumber(a.carla ? 0.0 : a.cfg.fake_speed_kmh / 3.6)
         << ",\"aaosMode\":" << dd::JsonString(a.cfg.aaos_mode) << ",\"checkpointCase\":"
         << dd::JsonString(a.cfg.checkpoint_case) << "},\"campaignId\":" << dd::JsonString(a.cfg.campaign_id)
         << ",\"runRole\":" << dd::JsonString(a.cfg.run_role) << ",\"checkpointSha256\":"
         << dd::JsonString(a.identity.actual) << ",\"checkpointPath\":" << dd::JsonString(checkpoint_path)
         << ",\"configurationPath\":" << dd::JsonString(a.cfg.path) << ",\"vehicleConfiguration\":{\"path\":"
         << dd::JsonString(a.cfg.vehicle_config) << "},\"commandLaw\":"
         << dd::JsonString(da::LawName(static_cast<int>(a.vehicle.law))) << ",\"scoreFEORevision\":"
         << dd::JsonString(a.cfg.score_feo_revision) << ",\"simulatorBuild\":" << dd::JsonString(simulator_build)
         << path_field("navigationMap", a.cfg.nav_map) << path_field("route", a.cfg.route_file)
         << path_field("cameraProfile", camera_profile)
         << ",\"setup\":" << a.setup_result << "}";
  std::string record_result;
  if (!a.planner.WriteRunRecord(a.cfg.run_dir + "/run_record.json", fields.str(), &record_result, &error)) {
    Log("error", "{\"what\":\"run_record_failed\",\"message\":" + dd::JsonString(error) + "}");
    return false;
  }
  {
    std::string parse_error;
    const auto doc = dd::json::Value::Parse(record_result, &parse_error);
    if (!doc.IsObject() || doc.Find("identity") == nullptr) {
      Log("error", "{\"what\":\"run_record_result\",\"result\":" + dd::JsonString(record_result) + "}");
      return false;
    }
    a.run_identity = doc.Find("identity")->AsString("");
  }
  Log("run_record", WithStage(record_result));
  return true;
}

}  // namespace

extern "C" {

De4sdvAbiSizes de4sdv_abi_sizes(void) {
  return De4sdvAbiSizes{sizeof(De4sdvPlanPayload), sizeof(De4sdvModePayload), sizeof(De4sdvInputsMsg),
                        sizeof(De4sdvConditionMsg), sizeof(De4sdvEgoMsg),     sizeof(De4sdvPlanMsg),
                        sizeof(De4sdvValidPlanMsg), sizeof(De4sdvModeMsg)};
}

int32_t de4sdv_agent_init(const char* config_path) {
  auto agent = std::make_unique<Agent>();
  std::string error;
  if (config_path == nullptr || !LoadConfig(config_path, &agent->cfg, &error)) {
    std::fprintf(stderr, "drivingAgent: configuration: %s\n", error.c_str());
    return -1;
  }
  if (!da::LoadVehicleConfigFile(agent->cfg.vehicle_config, &agent->vehicle, &error)) {
    std::fprintf(stderr, "drivingAgent: vehicle configuration %s: %s\n", agent->cfg.vehicle_config.c_str(),
                 error.c_str());
    return -1;
  }
  std::error_code ec;
  std::filesystem::create_directories(agent->cfg.run_dir + "/score", ec);
  std::filesystem::create_directories(agent->cfg.run_dir + "/bench", ec);
  agent->log = std::make_unique<dd::RunLog>(agent->cfg.run_dir + "/score/drivingAgent.jsonl", "score", "drivingAgent");
  agent->inputs_log =
      std::make_unique<dd::RunLog>(agent->cfg.run_dir + "/score/checkpointInputs.jsonl", "score", "drivingAgent");
  agent->bench_log = std::make_unique<dd::RunLog>(agent->cfg.run_dir + "/bench/injection.jsonl", "bench", "fakeWorld");
  agent->python = agent->cfg.inference == "python";
  g_stage = std::string(agent->cfg.source == "carla" ? "stage-2-carla-world" : "stage-1b-fake-world") +
            (agent->cfg.nav_map.empty() ? "-route-stand-in" : "");
  for (std::size_t i = 0; i < da::kCameraCount; ++i) agent->sizes[i] = da::CameraSize{agent->cfg.cam_w[i], agent->cfg.cam_h[i]};
  g_agent = agent.get();
  {
    std::ostringstream os;
    os << "{\"stage\":\"" << Stage() << "\",\"config\":" << dd::JsonString(config_path)
       << ",\"mw_com_config\":" << dd::JsonString(agent->cfg.mw_com_config) << ",\"source\":"
       << dd::JsonString(agent->cfg.source) << ",\"inference\":" << dd::JsonString(agent->cfg.inference)
       << ",\"fault\":" << dd::JsonString(agent->cfg.fault) << ",\"commandLaw\":"
       << dd::JsonString(da::LawName(static_cast<int>(agent->vehicle.law)))
       << ",\"interfaceVersion\":" << dd::kInterfaceVersion << ",\"pid\":" << ::getpid() << "}";
    Log("start", os.str());
  }
  if (!BuildEngine(*agent)) {
    g_agent = nullptr;
    return -3;
  }
  if (agent->cfg.source == "carla") {
    // Attach before FEO starts: waiting for the world side's hero may take minutes.
    da::CarlaSourceConfig cc;
    cc.host = agent->cfg.carla_host;
    cc.port = static_cast<int>(agent->cfg.carla_port);
    cc.attach_timeout_s = agent->cfg.carla_attach_timeout_s;
    cc.rpc_timeout_s = agent->cfg.carla_rpc_timeout_s;
    agent->carla = std::make_unique<da::CarlaSource>();
    std::string info, attach_error;
    if (!agent->carla->Attach(cc, &agent->carla_rig_json, &info, &attach_error)) {
      Log("error", "{\"what\":\"carla_attach_failed\",\"message\":" + dd::JsonString(attach_error) + "}");
      g_agent = nullptr;
      return -4;
    }
    for (std::size_t i = 0; i < da::kCameraCount; ++i) {
      agent->cfg.cam_w[i] = agent->carla->camera(i).width;
      agent->cfg.cam_h[i] = agent->carla->camera(i).height;
      agent->sizes[i] = da::CameraSize{agent->cfg.cam_w[i], agent->cfg.cam_h[i]};
    }
    Log("attach", "{\"stage\":\"" + std::string(Stage()) + "\",\"carla\":" + info + "}");
  }
  if (!WriteRunRecordNow(*agent, agent->carla ? "CARLA " + agent->carla->server_version() : "fake world (stage 1b)")) {
    g_agent = nullptr;
    return -5;
  }
  score::mw::com::runtime::InitializeRuntime(score::mw::com::runtime::RuntimeConfiguration{agent->cfg.mw_com_config});
  if (!Offer(&agent->ego_skeleton, da::kEgoMotionSampleSpecifier) || !Offer(&agent->plan_skeleton, da::kPlanSpecifier) ||
      !Offer(&agent->mode_skeleton, da::kModeSpecifier) || !Offer(&agent->command_skeleton, da::kCommandSpecifier)) {
    Log("error", "{\"what\":\"offer_failed\"}");
    g_agent = nullptr;
    return -2;
  }
  Log("offered", "{\"services\":[\"de4sdv/driving/ego_motion_sample\",\"de4sdv/driving/plan\","
                 "\"de4sdv/driving/mode\",\"de4sdv/driving/command\"]}");
  agent->pace = std::make_unique<da::PaceSignal>();
  agent.release();
  return 0;
}

void de4sdv_agent_fini(void) {
  if (g_agent == nullptr) return;
  if (g_agent->world) g_agent->world->Stop();
  if (g_agent->carla) g_agent->carla->Stop();
  if (g_agent->nav_prefetch) g_agent->nav_prefetch->Stop();   // no more snapshots: join its thread
  if (g_agent->command_skeleton) g_agent->command_skeleton->StopOfferService();
  if (g_agent->mode_skeleton) g_agent->mode_skeleton->StopOfferService();
  if (g_agent->plan_skeleton) g_agent->plan_skeleton->StopOfferService();
  if (g_agent->ego_skeleton) g_agent->ego_skeleton->StopOfferService();
  std::ostringstream os;
  os << "{\"stage\":\"" << Stage() << "\",\"frames_produced\":" << (g_agent->world ? g_agent->world->produced() : (g_agent->carla ? g_agent->carla->ticks() : 0))
     << ",\"steps\":" << g_agent->steps << ",\"commands\":" << g_agent->commands
     << ",\"warmCalls\":" << g_agent->warm_calls
     << ",\"mergedConditioned\":" << g_agent->merged_conditioned
     << ",\"mergedNotConditioned\":" << g_agent->merged_not_conditioned
     << ",\"pace_sent\":" << (g_agent->pace ? g_agent->pace->sent() : 0)
     << ",\"pace_send_failures\":" << (g_agent->pace ? g_agent->pace->failures() : 0);
  if (g_agent->nav_prefetch) {
    const da::PrefetchStats p = g_agent->nav_prefetch->Stats();
    os << ",\"navPrefetch\":{\"submitted\":" << p.submitted << ",\"refusedUnarmed\":" << p.refusedUnarmed
       << ",\"droppedQueue\":" << p.droppedQueue << ",\"rendered\":" << p.rendered << ",\"discarded\":" << p.discarded
       << ",\"hit\":" << g_agent->nav_hits << ",\"routeChanged\":" << g_agent->nav_route_changed
       << ",\"poseChanged\":" << g_agent->nav_pose_changed << ",\"renderFailed\":" << g_agent->nav_render_failed
       << ",\"notSubmitted\":" << g_agent->nav_not_submitted << ",\"timedOut\":" << g_agent->nav_timed_out << "}";
  }
  if (g_agent->store) {
    const auto c = g_agent->store->Counters();
    os << ",\"frameStore\":{\"readyComplete\":" << c.readyComplete << ",\"readyDeadline\":" << c.readyDeadline
       << ",\"skipped\":" << c.skipped << ",\"merged\":" << c.merged << ",\"droppedIncomplete\":" << c.droppedIncomplete
       << ",\"overflow\":" << c.overflow << ",\"misuse\":" << c.misuse << ",\"lateImages\":[";
    for (std::size_t i = 0; i < da::kCameraCount; ++i) os << (i ? "," : "") << c.lateImages[i];
    os << "]}";
  }
  os << "}";
  Log("stop", os.str());
  delete g_agent;
  g_agent = nullptr;
}

// ---------------------------------------------------------------- conditionInputs
int32_t de4sdv_condition_startup(void) {
  if (g_agent == nullptr) return -1;
  auto& a = *g_agent;
  da::FrameStoreConfig fc;
  for (std::size_t i = 0; i < da::kCameraCount; ++i) {
    fc.cameras[i] = da::CameraConfig{a.cfg.cam_w[i], a.cfg.cam_h[i]};
  }
  da::PaceSignal* pace = a.pace.get();
  fc.readySink = [pace](std::uint64_t frame, bool) { pace->Send(frame); };
  if (!a.cfg.nav_map.empty() && a.cfg.nav_prefetch) {
    // Created before the store and armed once the navigation input and the REF origin exist: until
    // then the sink's requests are refused and the steps render on the chain.
    a.nav_prefetch = std::make_unique<da::NavPrefetch<da::NavPrefetchResult>>();
    da::NavPrefetch<da::NavPrefetchResult>* np = a.nav_prefetch.get();
    fc.snapshotSink = [np](std::uint64_t frame, const da::HeroSnapshot& snapshot, std::int64_t arrival) {
      np->Submit(frame, snapshot.pose, arrival);
    };
  }
  a.store = std::make_unique<da::FrameStore>(fc);
  if (a.carla) {
    std::string error;
    if (!a.carla->Start(a.store.get(), &error)) {
      Log("error", "{\"what\":\"carla_start_failed\",\"message\":" + dd::JsonString(error) + "}");
      return -1;
    }
  } else {
    a.world = std::make_unique<FakeWorld>(a.cfg, a.store.get());
    a.world->Start();
  }
  // The rig, before the first step: the raster is drawn at the REF pose, whose origin set_rig returns.
  if (a.python && !a.refusal.refused) {
    std::string result, error;
    const std::string rig = a.carla ? a.carla_rig_json
                                    : (a.cfg.fake_rig_json.empty() ? FakeRigJson(a.cfg) : a.cfg.fake_rig_json);
    if (!a.planner.SetRig(rig, &result, &error)) {
      Log("error", "{\"what\":\"set_rig_failed\",\"message\":" + dd::JsonString(error) + "}");
      return -1;
    }
    a.rig_set = true;
    std::string parse_error;
    const auto doc = dd::json::Value::Parse(result, &parse_error);
    const auto* origin = doc.IsObject() ? doc.Find("origin") : nullptr;
    if (origin == nullptr || origin->items().size() != 3) {
      Log("error", "{\"what\":\"set_rig_no_origin\",\"result\":" + dd::JsonString(result) + "}");
      return -1;
    }
    for (int i = 0; i < 3; ++i) a.ref_origin[i] = origin->items()[static_cast<std::size_t>(i)].AsNumber(0.0);
    if (const auto* t = doc.Find("tile_wh"); t != nullptr && t->items().size() == 2) {
      a.tile_w = static_cast<int>(t->items()[0].AsNumber(0.0));
      a.tile_h = static_cast<int>(t->items()[1].AsNumber(0.0));
    }
    if (const auto* f = doc.Find("front_hi_res"); f != nullptr && f->IsObject()) {
      const auto* fw = f->Find("width");
      const auto* fh = f->Find("height");
      if (fw != nullptr && fh != nullptr) {
        a.front_hi_res_json = "{\"width\":" + dd::JsonNumber(fw->AsNumber(0.0)) + ",\"height\":" +
                              dd::JsonNumber(fh->AsNumber(0.0)) + "}";
      }
    }
    if (const auto* c = doc.Find("c2_projections_json")) a.c2_projections_json = c->AsString("");
    Log("rig", WithStage("{\"result\":" + result + "}"));
    // CARLA's rig must reproduce the camera profile: a mount read back more than 10 mm or 0.1 degree
    // off means a rig read across a world tick or a world side that spawned other mounts. Both
    // engines report the errors per camera when they hold the profile; fake rigs are not checked.
    if (a.carla) {
      const auto* err_mm = doc.Find("rig_pose_err_mm");
      const auto* err_deg = doc.Find("rig_pose_err_deg");
      if (err_mm == nullptr || err_deg == nullptr || err_mm->items().size() != da::kCameraCount ||
          err_deg->items().size() != da::kCameraCount) {
        Log("error", "{\"what\":\"rig_unchecked\",\"why\":\"set_rig reported no per-camera mount errors; "
                     "the planner configuration needs the camera profile\"}");
        return -1;
      }
      for (std::size_t i = 0; i < da::kCameraCount; ++i) {
        const double mm = err_mm->items()[i].AsNumber(1e9);
        const double deg = err_deg->items()[i].AsNumber(1e9);
        if (!(mm <= 10.0) || !(deg <= 0.1)) {
          Log("error", "{\"what\":\"rig_mismatch\",\"camera\":" + dd::JsonString(da::CameraName(i)) +
                           ",\"pose_err_mm\":" + dd::JsonNumber(mm) + ",\"pose_err_deg\":" + dd::JsonNumber(deg) +
                           ",\"limit_mm\":10,\"limit_deg\":0.1}");
          return -1;
        }
      }
    }
  }
  if (!a.cfg.nav_map.empty()) {
    a.nav = std::make_unique<da::NavigationInput>();
    std::string error;
    if (!a.nav->Start(a.cfg.nav_map, a.cfg.route_host, static_cast<int>(a.cfg.route_port), &error)) {
      Log("error", "{\"what\":\"navigation_start_failed\",\"message\":" + dd::JsonString(error) + "}");
      return -1;
    }
    if (a.nav_prefetch) {
      da::NavigationInput* nav = a.nav.get();
      const std::array<double, 3> origin{a.ref_origin[0], a.ref_origin[1], a.ref_origin[2]};   // set once, above
      a.nav_prefetch->Start([nav, origin](std::uint64_t frame, const da::Pose& pose, std::int64_t,
                                          da::NavPrefetchResult* r) {
        da::RenderNavPrefetch(nav, origin.data(), frame, pose, r);
      });
      a.nav_prefetch->Arm(true);
    }
  }
  Log("ready", "{\"activity\":\"conditionInputs\",\"source\":" + dd::JsonString(a.cfg.source) +
                   ",\"navigation\":" + (a.nav ? "{\"map\":" + dd::JsonString(a.cfg.nav_map) + ",\"mapVersion\":" +
                                                       dd::JsonString(a.nav->map_version()) + ",\"routePort\":" +
                                                       std::to_string(a.nav->listener_port()) + ",\"prefetch\":" +
                                                       (a.nav_prefetch ? "{\"waitMs\":" + dd::JsonNumber(a.cfg.nav_prefetch_wait_ms) + "}"
                                                                       : std::string("null")) + "}"
                                                 : std::string("\"stand-in\"")) +
                   ",\"frameStore\":{\"ring\":" +
                   std::to_string(a.store->ringSize()) + ",\"bytesPerSlot\":" + std::to_string(a.store->bytesPerSlot()) +
                   "}}");
  return 0;
}

int32_t de4sdv_condition_step(De4sdvInputsMsg* inputs, De4sdvConditionMsg* condition, De4sdvEgoMsg* ego) {
  *inputs = De4sdvInputsMsg{};
  *condition = De4sdvConditionMsg{};
  *ego = De4sdvEgoMsg{};
  auto& a = *g_agent;
  std::vector<da::FrameHandle> merged;
  merged.reserve(da::kMaxMerged);
  da::FrameHandle handle = a.store->TakeNewestReady(&merged);
  if (!handle.valid()) return 1;  // a wake-up without a new frame
  const da::FrameView& view = handle.view();
  const std::uint64_t frame = view.frame;
  if (a.first_frame == 0) a.first_frame = merged.empty() ? frame : merged.front().frame();
  ++a.steps;

  // The frames FEO merged into this chain go into the histories first, oldest first (DESIGN.md).
  std::string merged_json = "[]";
  {
    std::string error;
    if (!ConditionMerged(a, merged, &merged_json, &error)) {
      Log("error", "{\"what\":\"condition_failed\",\"frame\":" + std::to_string(frame) + ",\"message\":" +
                       dd::JsonString(error) + "}");
      a.store->Release(handle);
      return -1;
    }
  }

  // REQ-DRIVING-023 to -025: the step's input conditions.
  da::StepConditions sc;
  sc.step_frame = frame;
  {
    // ICD A28: the images handed over for this step; a camera whose image missed the deadline is
    // judged by its newest valid image (stale only beyond 200 ms). The step still goes into the
    // histories below (its pose; Python gets no image for that camera, so the frame has no tiles).
    da::CameraObservation arrived[da::kCameraCount];
    for (std::size_t i = 0; i < da::kCameraCount; ++i) {
      const da::CameraView& cv = view.cameras[i];
      arrived[i].present = cv.present;
      // An image the frame store found unusable (byte count or size not as configured) is invalid,
      // as C2 reports it; it is never a camera's newest valid image.
      arrived[i].empty = cv.present && (cv.size == 0 || !cv.valid);
      arrived[i].width = cv.width;
      arrived[i].height = cv.height;
      arrived[i].has_frame = cv.present;
      arrived[i].frame_index = cv.imageFrame;
    }
    a.camera_history.Observe(arrived, a.sizes, sc.cameras);
  }
  const dd::EgoMotionSamplePayload sample = EgoFromSnapshot(view.snapshot, frame);
  sc.motion.has_sample = true;
  sc.motion.frame_index = frame;
  sc.motion.sample = sample;
  da::NavigationInput::Step nav_step;
  bool rendered = false;
  const std::vector<float>* map_buf = nullptr;
  const std::vector<float>* route_buf = nullptr;
  const char* prefetch_outcome = nullptr;   // C2 navPrefetch (A31); null without the prefetch
  double prefetch_take_ms = 0.0;
  if (a.nav) {
    std::string error;
    bool from_prefetch = false;
    if (a.nav_prefetch) {
      // The rasters drawn when this step's snapshot arrived, if they are what a render here would
      // draw: the same pose and the same route (the issue time and corridor count are read now).
      // TakeNavPrefetch (navigation_input.h) decides; the step logs, counts and renders otherwise.
      const auto wait_ns = static_cast<std::int64_t>(a.cfg.nav_prefetch_wait_ms * 1e6);
      da::NavPrefetchTake take = da::TakeNavPrefetch(a.nav_prefetch.get(), *a.nav, frame, view.snapshot.pose,
                                                     wait_ns, &a.nav_hit_map, &a.nav_hit_route);
      for (const auto& ev : take.route_events) Log("route", WithStage(ev));   // renders this step does not use
      prefetch_outcome = da::NavPrefetchOutcomeName(take.outcome);
      prefetch_take_ms = take.take_ms;
      switch (take.outcome) {
        case da::NavPrefetchOutcome::kHit: ++a.nav_hits; break;
        case da::NavPrefetchOutcome::kNotSubmitted: ++a.nav_not_submitted; break;
        case da::NavPrefetchOutcome::kTimedOut: ++a.nav_timed_out; break;
        case da::NavPrefetchOutcome::kRouteChanged: ++a.nav_route_changed; break;
        case da::NavPrefetchOutcome::kPoseChanged: ++a.nav_pose_changed; break;
        case da::NavPrefetchOutcome::kRenderFailed: ++a.nav_render_failed; break;
      }
      if (take.map_context != nullptr) {   // a use: this frame's prefetched rasters, held in nav_hit_*
        nav_step = std::move(take.step);
        map_buf = take.map_context;
        route_buf = take.route_mask;
        from_prefetch = true;
      }
    }
    if (!from_prefetch) {
      if (!a.nav->Render(view.snapshot.pose, a.ref_origin, &nav_step, &error)) {
        Log("error", "{\"what\":\"render_failed\",\"frame\":" + std::to_string(frame) + ",\"message\":" +
                         dd::JsonString(error) + "}");
        a.store->Release(handle);
        return -1;
      }
      map_buf = &a.nav->map_context();
      route_buf = &a.nav->route_mask();
    }
    rendered = true;
    sc.route = nav_step.route;
    if (!nav_step.route_event.empty()) {
      Log("route", WithStage("{\"frame\":" + std::to_string(frame) + ",\"event\":" + nav_step.route_event + "}"));
    }
  } else {
    sc.route.has_announcement = true;  // stand-in: a fresh full corridor every step
    sc.route.corridor_points = 60;
    sc.route.issue_time = da::FrameSeconds(frame);
    sc.route.raster_corridor_cells = 100;
  }
  const da::ConditionResult judged = da::JudgeConditions(sc, a.sizes);
  Log("out.condition", WithStage(da::record::Condition(sc, judged)));

  // The checkpoint inputs, from clean inputs only (a faulted step starts the stop instead).
  da::PlannerBridge::ConditionOut out;
  double condition_ms = 0.0;
  bool conditioned = false;
  if (a.python && !a.refusal.refused && !judged.Any()) {
    std::string error;
    da::PlannerBridge::ConditionIn in;
    FillConditionIn(view, &in);
    if (rendered) {
      in.map_context = map_buf->data();
      in.map_bytes = map_buf->size() * sizeof(float);
      in.route_mask = route_buf->data();
      in.route_bytes = route_buf->size() * sizeof(float);
    }
    const auto t0 = std::chrono::steady_clock::now();
    if (!a.planner.Condition(in, &out, &error)) {
      Log("error", "{\"what\":\"condition_failed\",\"frame\":" + std::to_string(frame) + ",\"message\":" +
                       dd::JsonString(error) + "}");
      a.store->Release(handle);
      return -1;
    }
    condition_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
    conditioned = true;
  }
  // ICD A26: with an engine, only a step it conditioned can be primed; a faulted step is not in the histories.
  const bool primed = da::StepPrimed(a.python, conditioned, out.primed, frame, a.first_frame, a.cfg.priming_frames);

  // C2 (ICD section 10): one record per step, read by runio.input_steps.
  {
    std::ostringstream os;
    os << "{\"stage\":\"" << Stage() << "\",\"frame\":" << frame << ",\"sim_ms\":" << frame * 100 << ",\"cameras\":[";
    for (std::size_t i = 0; i < da::kCameraCount; ++i) {
      const da::CameraView& cv = view.cameras[i];
      const char* status = CameraStatus(cv, a.sizes[i], frame);
      os << (i ? "," : "") << "{\"name\":" << dd::JsonString(da::CameraName(i));
      if (cv.present) {
        os << ",\"image_frame\":" << cv.imageFrame << ",\"capture_sim_ms\":" << cv.imageFrame * 100
           << ",\"arrival_mono_ns\":" << cv.arrivalMonoNs;
      } else {
        os << ",\"image_frame\":null,\"capture_sim_ms\":null,\"arrival_mono_ns\":null";
      }
      // A17: the size of the image handed to the checkpoint (the engine's tile), and the simulator's.
      const bool tiled = a.tile_w > 0 && cv.present;
      os << ",\"width\":" << (tiled ? a.tile_w : cv.width) << ",\"height\":" << (tiled ? a.tile_h : cv.height)
         << ",\"source_width\":" << cv.width << ",\"source_height\":" << cv.height;
      if (i == 0 && !a.front_hi_res_json.empty() && cv.present) os << ",\"front_hi_res\":" << a.front_hi_res_json;
      os << ",\"valid\":"
         << (std::strcmp(status, "valid") == 0 ? "true" : "false") << ",\"status\":\"" << status << "\",\"history\":[";
      for (int j = 7; j >= 1; --j) os << (j != 7 ? "," : "") << static_cast<long long>(frame) - 5 * j;
      os << "]}";
    }
    os << "]";
    if (!a.c2_projections_written && !a.c2_projections_json.empty()) {
      os << ",\"projections\":" << a.c2_projections_json;   // once per run (the rig does not change)
      a.c2_projections_written = true;
    }
    os << ",\"ego_motion_history\":" << (conditioned && out.has_rows ? RowsJson(out.checkpoint) : std::string("[]"))
       << ",\"map_context_render_sim_ms\":" << (rendered ? std::to_string(frame * 100) : std::string("null"))
       << ",\"corridor_cell_count\":" << sc.route.raster_corridor_cells << ",\"destination_cell_count\":"
       << (rendered ? std::to_string(nav_step.destination_cells) : std::string("null"));
    if (rendered) {
      // VC-DRIVING-006/007 metadata: the tensors' shape and geometry, the route they carry, the pose
      // they were drawn at, and the corridor's coverage of the route's waypoints in the window.
      os << ",\"mapContext\":{\"channels\":" << dn::kMapChannels << ",\"height\":" << dn::kHeightPx
         << ",\"width\":" << dn::kWidthPx << ",\"geometry\":\"" << dn::kGeometryId << "\"}"
         << ",\"routeMask\":{\"channels\":" << dn::kRouteChannels << ",\"height\":" << dn::kHeightPx
         << ",\"width\":" << dn::kWidthPx << ",\"geometry\":\"" << dn::kGeometryId
         << "\",\"corridorCells\":" << nav_step.route.raster_corridor_cells << ",\"routeSha256\":"
         << (nav_step.route_sha256.empty() ? std::string("null") : dd::JsonString(nav_step.route_sha256))
         << ",\"waypointsInWindow\":" << nav_step.waypoints_in_window
         << ",\"waypointsOnCorridor\":" << nav_step.waypoints_on_corridor << "}"
         << ",\"rasterPose\":{\"x_map_m\":" << dd::JsonNumber(nav_step.pose.x) << ",\"y_map_m\":"
         << dd::JsonNumber(nav_step.pose.y) << ",\"yaw_map_rad\":" << dd::JsonNumber(nav_step.pose.yaw)
         << "},\"render_ms\":" << dd::JsonNumber(nav_step.render_ms)
         << ",\"navPrefetch\":"
         << (prefetch_outcome == nullptr ? std::string("null")
                                         : "{\"outcome\":\"" + std::string(prefetch_outcome) + "\",\"take_ms\":" +
                                               dd::JsonNumber(prefetch_take_ms) + "}")
         << ",\"route\":{\"has_announcement\":" << (sc.route.has_announcement ? "true" : "false")
         << ",\"corridor_points\":" << sc.route.corridor_points << ",\"issue_time_s\":"
         << dd::JsonNumber(sc.route.issue_time) << "}";
    }
    os << ",\"input_conditions\":{\"bits\":" << judged.bits
       << ",\"causes\":" << CausesJson(judged) << "},\"primed\":" << (primed ? "true" : "false")
       << ",\"conditioned\":" << (conditioned ? "true" : "false") << ",\"condition_ms\":" << dd::JsonNumber(condition_ms)
       << ",\"frameStore\":{\"readyByDeadline\":" << (view.readyByDeadline ? "true" : "false") << "}"
       << ",\"mergedFrames\":" << merged_json;
    if (conditioned && !out.record_json.empty()) os << ",\"planner\":" << out.record_json;
    os << "}";
    a.inputs_log->Write("out.checkpoint_inputs", a.inputs_seq.fetch_add(1), os.str());
  }
  a.store->Release(handle);  // the images were copied into the checkpoint's inputs

  if (primed && !a.priming_logged && !a.refusal.refused) {  // a refused run conditions no history
    a.priming_logged = true;
    Log("priming.complete", WithStage("{\"frame\":" + std::to_string(frame) + ",\"sim_ms\":" +
                                      std::to_string(frame * 100) + ",\"historiesReady\":true}"));
  }
  Publish(a.ego_skeleton->ego_motion_sample, sample, "ego_motion_sample");
  {
    std::ostringstream os;
    os << "{\"stage\":\"" << Stage() << "\",\"speed\":" << dd::JsonNumber(sample.speed)
       << ",\"longitudinalAcceleration\":" << dd::JsonNumber(sample.longitudinalAcceleration)
       << ",\"lateralAcceleration\":" << dd::JsonNumber(sample.lateralAcceleration)
       << ",\"yawRate\":" << dd::JsonNumber(sample.yawRate) << ",\"captureTime\":" << dd::JsonNumber(sample.captureTime)
       << ",\"frame\":" << frame << ",\"clocks\":{\"captureTime\":\"simulation\"}}";
    Log("out.ego_motion_sample", os.str());
  }
  inputs->step_frame = frame;
  inputs->has_step = 1;
  inputs->primed = primed ? 1u : 0u;
  inputs->condition_bits = judged.bits;
  inputs->speed_mps = sample.speed / 3.6f;
  condition->step_frame = frame;
  condition->has_step = 1;
  condition->condition_bits = judged.bits;
  condition->primed = inputs->primed;
  condition->speed_kmh = sample.speed;
  ego->frame = frame;
  ego->has_sample = 1;
  ego->speed_kmh = sample.speed;
  return 0;
}

void de4sdv_condition_shutdown(void) {
  if (g_agent != nullptr && g_agent->world) g_agent->world->Stop();
  if (g_agent != nullptr && g_agent->carla) g_agent->carla->Stop();
}

// ---------------------------------------------------------------- inferPlan
// The engine is built in de4sdv_agent_init (BuildEngine); this startup binds it to worker 40, well
// inside FEO's receive timeout.
int32_t de4sdv_infer_startup(void) {
  auto& a = *g_agent;
  if (!a.python) {
    Log("ready", "{\"activity\":\"inferPlan\",\"inference\":\"stub\",\"runRecord\":\"none\"}");
    return 0;
  }
  if (a.refusal.refused) {
    Log("ready", "{\"activity\":\"inferPlan\",\"inference\":\"python\",\"refused\":true,\"runRecord\":" +
                     dd::JsonString(a.run_identity) + "}");
    return 0;
  }
  std::string bind, error;
  if (!a.planner.BindThread(&bind, &error)) {
    Log("error", "{\"what\":\"planner_bind_failed\",\"message\":" + dd::JsonString(error) + "}");
    return -1;
  }
  Log("ready", "{\"activity\":\"inferPlan\",\"inference\":\"python\",\"setup_s\":" + dd::JsonNumber(a.setup_s) +
                   ",\"runRecord\":" + dd::JsonString(a.run_identity) + ",\"bind\":" + bind + ",\"setup\":" +
                   a.setup_result + "}");
  return 0;
}

int32_t de4sdv_infer_step(const De4sdvInputsMsg* inputs, De4sdvPlanMsg* plan) {
  *plan = De4sdvPlanMsg{};
  auto& a = *g_agent;
  if (a.python && !a.refusal.refused && inputs->has_step && !inputs->primed && inputs->condition_bits == 0) {
    // While the agent primes (DESIGN.md, warm-up while priming), the engine may warm its camera history cache with
    // one call on the frame's phase stream (output discarded) when its lag budget allows; the first
    // plan of every phase then runs warm. No plan is produced. A faulted step was not conditioned, so
    // there is nothing to warm.
    std::string record, error;
    ++a.warm_calls;
    if (!a.planner.Warm(inputs->step_frame, &record, &error)) {
      Log("error", "{\"what\":\"warm_failed\",\"frame\":" + std::to_string(inputs->step_frame) +
                       ",\"message\":" + dd::JsonString(error) + "}");
    } else if (!record.empty()) {
      Log("warm", WithStage(record));
    }
    return 1;
  }
  if (a.refusal.refused || !inputs->has_step || !inputs->primed || inputs->condition_bits != 0) return 1;
  const std::uint64_t frame = inputs->step_frame;
  if (a.cfg.fault_plan_stall_frame != 0 && frame >= a.cfg.fault_plan_stall_frame) {
    if (!a.stall_logged) {
      a.stall_logged = true;
      Bench("fault_begin", frame, "{\"fault\":\"plan_stale\",\"what\":\"inferPlan stops producing plans\"}");
    }
    return 1;  // planning stalls: the supervision judges the plan age (REQ-DRIVING-026)
  }
  da::PlannerBridge::InferOut out;
  if (a.python) {
    std::string error;
    if (!a.planner.Infer(frame, &out, &error)) {
      Log("error", "{\"what\":\"infer_failed\",\"frame\":" + std::to_string(frame) + ",\"message\":" +
                       dd::JsonString(error) + "}");
      return 1;  // no plan this step: the supervision judges the plan age
    }
    if (!out.planned) return 1;
  }
  dd::DrivingPlanPayload p{};
  p.frameIndex = frame;
  p.captureTime = static_cast<double>(dd::CaptureTimeMicros(frame)) / 1e6;
  p.horizon = 6.4f;
  p.sampleCount = dd::kPlanSamples;
  for (std::size_t i = 0; i < dd::kPlanSamples; ++i) {
    p.samples[i] = a.python ? dd::PlanSample{out.samples[i][0], out.samples[i][1], out.samples[i][2], out.samples[i][3],
                                             out.samples[i][4]}
                            : dd::PlanSample{0.0f, 0.0f, inputs->speed_mps * 0.1f * static_cast<float>(i + 1), 0.0f, 0.0f};
  }
  CopyId(p.producer, sizeof(p.producer), "drivingAgent/inferPlan");
  CopyId(p.runRecord, sizeof(p.runRecord), a.run_identity);
  CopyId(p.planReference, sizeof(p.planReference), a.run_identity + "/" + std::to_string(frame));
  if (a.cfg.fault_plan_invalid_frame != 0 && frame == a.cfg.fault_plan_invalid_frame) {
    p.samples[7].curvature = std::numeric_limits<float>::quiet_NaN();  // REQ-DRIVING-027's fault
    Bench("plan_inject", frame, "{\"planReference\":" + dd::JsonString(CStr(p.planReference, sizeof(p.planReference))) +
                                    ",\"invalid\":\"nan_curvature\",\"sample\":7}");
  }
  p.productionTime = dd::MonotonicSeconds();
  Publish(a.plan_skeleton->plan, p, "plan");
  std::string record = WithStage(da::record::OutPlan(p));
  if (a.python && !out.record_json.empty()) record = WithMember(record, "planner", out.record_json);
  Log("out.plan", record);
  plan->has_plan = 1;
  plan->new_this_step = 1;
  std::memcpy(&plan->plan, &p, sizeof(p));
  return 0;
}

void de4sdv_infer_shutdown(void) {
  if (g_agent != nullptr && g_agent->python) g_agent->planner.Stop();
}

// ---------------------------------------------------------------- superviseLoop
int32_t de4sdv_supervise_startup(void) {
  Log("ready", "{\"activity\":\"superviseLoop\",\"logic\":\"agent_logic\"}");
  return 0;
}

int32_t de4sdv_supervise_step(const De4sdvConditionMsg* condition, const De4sdvPlanMsg* plan,
                              De4sdvValidPlanMsg* valid_plan, De4sdvModeMsg* mode) {
  *valid_plan = De4sdvValidPlanMsg{};
  *mode = De4sdvModeMsg{};
  auto& a = *g_agent;
  if (!condition->has_step) return 1;
  // Built at the first step: every startup has run, so a refusal of the checkpoint is known.
  if (!a.supervisor) a.supervisor = std::make_unique<da::Supervisor>(a.refusal);
  dd::DrivingPlanPayload arrived{};
  const dd::DrivingPlanPayload* plan_this_step = nullptr;
  if (plan->has_plan && plan->new_this_step) {
    std::memcpy(&arrived, &plan->plan, sizeof(arrived));
    plan_this_step = &arrived;
  }
  da::MotionObservation motion;
  motion.has_sample = true;
  motion.frame_index = condition->step_frame;
  motion.sample.speed = condition->speed_kmh;
  const double mono = dd::MonotonicSeconds();
  const da::SupervisorStep s =
      a.supervisor->Step(condition->step_frame, mono, FromBits(condition->condition_bits), plan_this_step, motion);
  Publish(a.mode_skeleton->mode, s.mode_payload, "mode");
  Log("out.mode", WithStage(da::record::OutMode(s.mode_payload)));
  if (s.stop_began) {
    Log("stop_response.begin", WithStage(da::record::StopBegin(a.supervisor->cause_frame(), s.cause, "superviseLoop",
                                                               a.supervisor->cause_monotonic())));
  }
  if (s.mode == dd::Mode::kStandstill && !a.standstill_logged) {
    a.standstill_logged = true;
    Log("stop_response.standstill",
        WithStage(da::record::Standstill(condition->step_frame, s.cause, condition->speed_kmh, mono)));
  }
  mode->changed = s.mode_changed ? 1u : 0u;
  mode->stop_began = s.stop_began ? 1u : 0u;
  std::memcpy(&mode->mode, &s.mode_payload, sizeof(s.mode_payload));
  if (s.newest_valid_plan != nullptr) {
    valid_plan->has_plan = 1;
    std::memcpy(&valid_plan->plan, s.newest_valid_plan, sizeof(valid_plan->plan));
  }
  return 0;
}

void de4sdv_supervise_shutdown(void) {}

// ---------------------------------------------------------------- commandVehicle
int32_t de4sdv_command_startup(void) {
  auto& a = *g_agent;
  a.commander = std::make_unique<da::Commander>(a.vehicle);
  Log("ready", "{\"activity\":\"commandVehicle\",\"logic\":\"agent_logic\",\"commandLaw\":" +
                   dd::JsonString(da::LawName(static_cast<int>(a.vehicle.law))) + "}");
  return 0;
}

int32_t de4sdv_command_step(const De4sdvEgoMsg* ego, const De4sdvValidPlanMsg* valid_plan, const De4sdvModeMsg* mode) {
  auto& a = *g_agent;
  if (!ego->has_sample) return 1;
  dd::DrivingPlanPayload view{};
  const dd::DrivingPlanPayload* newest_valid = nullptr;
  if (valid_plan->has_plan) {
    std::memcpy(&view, &valid_plan->plan, sizeof(view));
    newest_valid = &view;
    if (!a.in_plan_logged || view.frameIndex != a.in_plan_frame) {  // the commander's view, on change
      a.in_plan_logged = true;
      a.in_plan_frame = view.frameIndex;
      Log("in.plan", WithStage(da::record::InPlan(view)));
    }
  }
  da::MotionObservation motion;
  motion.has_sample = true;
  motion.frame_index = ego->frame;
  motion.sample.speed = ego->speed_kmh;
  const double mono = dd::MonotonicSeconds();
  const da::CommandStep cs =
      a.commander->Step(static_cast<dd::Mode>(mode->mode.mode), newest_valid, ego->frame, motion, mono);
  if (cs.plan_stale && a.supervisor) {
    a.supervisor->Latch(dd::Cause::kPlanStale, ego->frame, mono);  // REQ-DRIVING-026 at the command
  }
  if (!cs.has_command) return 1;
  Publish(a.command_skeleton->command, cs.command, "command");
  Log("out.command", WithStage(da::record::OutCommand(cs)));
  ++a.commands;
  if (a.world) a.world->SetAcceleration(cs.command.acceleration);
  return 0;
}

void de4sdv_command_shutdown(void) {}

}  // extern "C"
