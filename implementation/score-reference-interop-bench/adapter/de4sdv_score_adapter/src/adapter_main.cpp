// DE4SDV AutowareToSCORE adapter of INC-MW-011: one process that is an
// Eclipse S-CORE communication (mw::com) application and a ROS 2 node
// (phase-8 realization, GAP-MW-035, REQ-MW-018).
//
// Ports (phase 8), one to one:
//   referenceSpeedIn            mw::com proxy of de4sdv/reference_vehicle_speed
//   middlewareVelocityStatusOut /de4sdv/middleware/velocity_status, VelocityReport,
//                               reliable, depth 10; the adapter's only publisher
//   aebsSignalFrameIn           TCP client of 127.0.0.1:4721 (length-delimited frames)
//   aebsSignalFrameOut          mw::com skeleton of de4sdv/aebs_signal_frame
// Threads: the rclcpp executor; the main thread, which finds the provider,
// reads the speed samples and publishes them, and runs the shutdown of rule
// 2; the frame ingest thread. The mw::com receive and state handlers only
// wake the main thread.
//
// ROS 2 endpoints (adapterAbortConditions of the model): the node starts
// without parameter services, without a parameter event publisher and
// without /rosout, so its endpoints are its VelocityReport publication and
// the /parameter_events subscription of rclcpp's time source. There the time
// source reads only this node's use_sim_time, and it logs a value of a wrong
// type without a throw. With parameter services, any ROS 2 process on the
// host could abort the adapter: rclcpp throws and catches
// ParameterNotDeclaredException for a request that names an undeclared
// parameter. The stamp of each VelocityReport comes from a clock of system
// time, not from the node clock, so a switch of the node clock to /clock
// cannot change the stamps.
//
// Abort matrix of VC-MW-019: real-time signals select a throw inside a
// try/catch (fault_signal.hpp, fault_hook.hpp). The matrix so runs this
// start configuration and this binary.
//
// Logging: the adapter writes its own events to stdout, one JSON object per
// line. mw::log writes its own text lines to stdout as well (configured by
// MW_LOG_CONFIG_FILE), and rclcpp and the ROS 2 middleware write to stderr.
//
// Exit codes: exit_codes.hpp.

#include <signal.h>
#include <unistd.h>

#include <atomic>
#include <cerrno>
#include <chrono>
#include <cinttypes>
#include <cmath>
#include <condition_variable>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <fstream>
#include <initializer_list>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include "autoware_vehicle_msgs/msg/velocity_report.hpp"
#include "de4sdv_score_adapter/exit_codes.hpp"
#include "de4sdv_score_adapter/fault_signal.hpp"
#include "de4sdv_score_adapter/frame_path_controller.hpp"
#include "de4sdv_score_adapter/frame_splitter.hpp"
#include "de4sdv_score_adapter/frame_stream_client.hpp"
#include "de4sdv_score_adapter/speed_path_controller.hpp"
#include "de4sdv_score_facade/score_facade.h"
#include "facade_ports.hpp"
#include "fault_hook.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rmw/rmw.h"

namespace {

using de4sdv::score_adapter::FacadeFrameEventPort;
using de4sdv::score_adapter::FacadeSpeedEventPort;
using de4sdv::score_adapter::FaultRequest;
using de4sdv::score_adapter::FaultVariant;
using de4sdv::score_adapter::FramePathController;
using de4sdv::score_adapter::FrameSplitter;
using de4sdv::score_adapter::FrameStreamClient;
using de4sdv::score_adapter::FrameStreamEvents;
using de4sdv::score_adapter::ReconnectBackoff;
using de4sdv::score_adapter::ShutdownResult;
using de4sdv::score_adapter::SpeedPathController;
using de4sdv::score_adapter::SpeedPathEvents;
using de4sdv::score_adapter::SubscribeResult;
using de4sdv::score_adapter::SubscriptionState;
using de4sdv::score_adapter::TranslationOutcome;
using de4sdv::score_adapter::VelocityPublisherPort;
namespace exit_code = de4sdv::score_adapter::exit_code;
namespace fault_hook = de4sdv::score_adapter::fault_hook;
namespace score_facade = de4sdv::score_facade;

constexpr const char* kNodeName = "de4sdv_score_adapter";
constexpr const char* kVelocityTopic = "/de4sdv/middleware/velocity_status";
constexpr const char* kFrameId = "base_link";
constexpr const char* kSpeedInstanceSpecifier = "de4sdv/reference_vehicle_speed";
constexpr const char* kFrameInstanceSpecifier = "de4sdv/aebs_signal_frame";
constexpr std::size_t kSpeedMaxSamples = 5;

std::atomic<bool> g_stop_requested{false};
FaultRequest g_fault_request;

extern "C" void OnStopSignal(int /*signal*/) { g_stop_requested.store(true); }
extern "C" void OnFaultSignal(int signal) { g_fault_request.Store(signal); }

std::int64_t ClockNs(clockid_t clock) {
  timespec ts{};
  clock_gettime(clock, &ts);
  return static_cast<std::int64_t>(ts.tv_sec) * 1000000000LL + ts.tv_nsec;
}

std::string Escape(const std::string& text) {
  std::string out;
  out.reserve(text.size());
  for (const char c : text) {
    switch (c) {
      case '"':
        out += "\\\"";
        break;
      case '\\':
        out += "\\\\";
        break;
      case '\n':
        out += "\\n";
        break;
      default:
        if (static_cast<unsigned char>(c) < 0x20U) {
          out += ' ';
        } else {
          out += c;
        }
    }
  }
  return out;
}

std::string Quote(const std::string& text) { return "\"" + Escape(text) + "\""; }

std::mutex g_log_mutex;

// One JSON object per line: {"monotonic_ns":..,"realtime_ns":..,"event":..,...}
void LogEvent(const std::string& event, const std::string& fields = "") {
  std::lock_guard<std::mutex> lock{g_log_mutex};
  std::fprintf(stdout, "{\"monotonic_ns\":%" PRId64 ",\"realtime_ns\":%" PRId64 ",\"event\":%s%s%s}\n",
               ClockNs(CLOCK_MONOTONIC), ClockNs(CLOCK_REALTIME), Quote(event).c_str(), fields.empty() ? "" : ",",
               fields.c_str());
  std::fflush(stdout);
}

std::string Field(const char* name, const std::string& value) { return Quote(name) + ":" + Quote(value); }
std::string Field(const char* name, std::uint64_t value) { return Quote(name) + ":" + std::to_string(value); }
std::string Field(const char* name, std::int64_t value) { return Quote(name) + ":" + std::to_string(value); }
std::string Field(const char* name, bool value) { return Quote(name) + ":" + (value ? "true" : "false"); }

std::string ValueText(double value) {
  if (std::isnan(value)) {
    return "nan";
  }
  if (std::isinf(value)) {
    return value > 0 ? "inf" : "-inf";
  }
  char buffer[64];
  std::snprintf(buffer, sizeof(buffer), "%.17g", value);
  return buffer;
}

std::string BitsText(double value) {
  std::uint64_t bits = 0;
  std::memcpy(&bits, &value, sizeof(bits));
  char buffer[24];
  std::snprintf(buffer, sizeof(buffer), "%016" PRIx64, bits);
  return buffer;
}

std::uint64_t ResidentKiB() {
  std::ifstream status{"/proc/self/status"};
  std::string line;
  while (std::getline(status, line)) {
    if (line.rfind("VmRSS:", 0) == 0) {
      return std::strtoull(line.c_str() + 6, nullptr, 10);
    }
  }
  return 0;
}

struct Options {
  std::string mw_com_config;
  std::string frame_host{"127.0.0.1"};
  std::uint16_t frame_port{4721};
  long status_period_s{10};
};

bool ParseOptions(int argc, char** argv, Options* options) {
  for (int i = 1; i < argc; ++i) {
    const std::string argument{argv[i]};
    if (argument == "--ros-args") {
      break;
    }
    if (i + 1 >= argc) {
      return false;
    }
    const std::string value{argv[++i]};
    if (argument == "--mw-com-config") {
      options->mw_com_config = value;
    } else if (argument == "--frame-host") {
      options->frame_host = value;
    } else if (argument == "--frame-port") {
      const long port = std::strtol(value.c_str(), nullptr, 10);
      if (port <= 0 || port > 65535) {
        return false;
      }
      options->frame_port = static_cast<std::uint16_t>(port);
    } else if (argument == "--status-period-s") {
      options->status_period_s = std::strtol(value.c_str(), nullptr, 10);
      if (options->status_period_s <= 0) {
        return false;
      }
    } else {
      return false;
    }
  }
  return !options->mw_com_config.empty();
}

class VelocityPublisher final : public VelocityPublisherPort {
 public:
  explicit VelocityPublisher(rclcpp::Node& node)
      : publisher_{node.create_publisher<autoware_vehicle_msgs::msg::VelocityReport>(
            kVelocityTopic, rclcpp::QoS(rclcpp::KeepLast(10)).reliable())} {}

  void Publish(float longitudinal_velocity_mps) override {
    autoware_vehicle_msgs::msg::VelocityReport message;
    // System time, not the node clock: /parameter_events can switch the node
    // clock to /clock, but not this one.
    message.header.stamp = stamp_clock_.now();
    message.header.frame_id = kFrameId;
    message.longitudinal_velocity = longitudinal_velocity_mps;
    message.lateral_velocity = 0.0F;
    message.heading_rate = 0.0F;
    publisher_->publish(message);
  }

 private:
  rclcpp::Clock stamp_clock_{RCL_SYSTEM_TIME};
  rclcpp::Publisher<autoware_vehicle_msgs::msg::VelocityReport>::SharedPtr publisher_;
};

class SpeedEventLog final : public SpeedPathEvents {
 public:
  void OnSampleWithheld(double speed_kmh, TranslationOutcome outcome) override {
    LogEvent("speed_sample_withheld",
             Field("reason", std::string{outcome == TranslationOutcome::kWithheldNonFinite ? "non_finite"
                                                                                           : "out_of_float32_range"}) +
                 "," + Field("speed_kmh", ValueText(speed_kmh)) + "," + Field("bits", BitsText(speed_kmh)));
  }
  void OnStoredSamplesDiscarded(std::size_t count) override {
    LogEvent("stored_speed_samples_discarded", Field("count", static_cast<std::uint64_t>(count)));
  }
  void OnUnstableReadDropped(std::size_t count) override {
    LogEvent("unstable_speed_read_dropped", Field("count", static_cast<std::uint64_t>(count)));
  }
};

class Wakeup {
 public:
  void Notify() {
    {
      std::lock_guard<std::mutex> lock{mutex_};
      pending_ = true;
    }
    condition_.notify_one();
  }
  void WaitFor(std::chrono::milliseconds timeout) {
    std::unique_lock<std::mutex> lock{mutex_};
    condition_.wait_for(lock, timeout, [this] { return pending_; });
    pending_ = false;
  }

 private:
  std::mutex mutex_;
  std::condition_variable condition_;
  bool pending_{false};
};

struct SpeedHandlerContext {
  SpeedPathController* controller;
  Wakeup* wakeup;
};

// mw::com state handler: runs under the binding's lock, so it only records
// the state and wakes the main thread.
void OnSpeedSubscriptionState(void* context, score_facade::SubscriptionState facade_state) {
  auto* handler = static_cast<SpeedHandlerContext*>(context);
  const SubscriptionState state = de4sdv::score_adapter::FromFacade(facade_state);
  handler->controller->OnSubscriptionStateChanged(state);
  LogEvent("speed_subscription_state", Field("state", std::string{de4sdv::score_adapter::ToText(state)}));
  handler->wakeup->Notify();
}

void OnSpeedSamplesReceived(void* context) { static_cast<SpeedHandlerContext*>(context)->wakeup->Notify(); }

void SleepUnlessStopped(std::chrono::milliseconds duration, const std::atomic<bool>& stop) {
  const auto end = std::chrono::steady_clock::now() + duration;
  while (!stop.load() && std::chrono::steady_clock::now() < end) {
    std::this_thread::sleep_for(std::chrono::milliseconds{10});
  }
}

// Rule 3: the frame stream comes and goes; the skeleton offer stays.
class FrameStreamLog final : public FrameStreamEvents {
 public:
  explicit FrameStreamLog(const Options& options) : options_{options} {}
  void OnWaiting() override {
    LogEvent("frame_stream_waiting",
             Field("host", options_.frame_host) + "," + Field("port", static_cast<std::uint64_t>(options_.frame_port)));
  }
  void OnConnected() override { LogEvent("frame_stream_connected"); }
  void OnLost(std::chrono::milliseconds next_delay) override {
    LogEvent("frame_stream_lost", Field("next_attempt_in_ms", static_cast<std::int64_t>(next_delay.count())));
  }
  void OnInvalidAddress() override {
    LogEvent("frame_stream_error", Field("reason", std::string{"invalid --frame-host"}));
  }

 private:
  const Options& options_;
};

void FrameIngestLoop(const Options& options, FramePathController& controller, FrameSplitter& splitter,
                     const std::atomic<bool>& stop) {
  FrameStreamLog log{options};
  FrameStreamClient client{options.frame_host,
                           options.frame_port,
                           splitter,
                           controller,
                           ReconnectBackoff{std::chrono::milliseconds{100}, std::chrono::milliseconds{2000}},
                           [&stop](std::chrono::milliseconds delay) { SleepUnlessStopped(delay, stop); },
                           &log};
  client.Run(stop);
}

void LogStatus(const char* event, const SpeedPathController& speed, const FramePathController& frames,
               const FrameSplitter& splitter, SubscriptionState state) {
  const auto s = speed.counters();
  const auto f = frames.counters();
  const FrameSplitter::Stats split = splitter.stats();
  LogEvent(event,
           Field("speed_state", std::string{de4sdv::score_adapter::ToText(state)}) + "," +
               Field("speed_reads", s.reads) + "," + Field("speed_discard_reads", s.discard_reads) + "," +
               Field("speed_samples_read", s.samples_read) + "," +
               Field("speed_samples_discarded_stored", s.samples_discarded_stored) + "," +
               Field("speed_samples_dropped_unstable", s.samples_dropped_unstable) + "," +
               Field("speed_samples_published", s.samples_published) + "," +
               Field("speed_samples_withheld_non_finite", s.samples_withheld_non_finite) + "," +
               Field("speed_samples_withheld_out_of_range", s.samples_withheld_out_of_range) + "," +
               Field("speed_read_errors", s.read_errors) + "," + Field("speed_state_changes", s.state_changes) +
               "," + Field("frame_offers", f.offers) + "," + Field("frame_connections", f.connections) + "," +
               Field("frame_connection_losses", f.connection_losses) + "," + Field("frames_sent", f.frames_sent) +
               "," + Field("frames_allocate_failed", f.frames_allocate_failed) + "," +
               Field("frames_send_failed", f.frames_send_failed) + "," +
               Field("frames_not_offered", f.frames_not_offered) + "," +
               Field("frames_forwarded", split.frames_forwarded) + "," +
               Field("frames_dropped_oversize", split.frames_dropped_oversize) + "," +
               Field("frame_bytes_read", split.bytes_read) + "," +
               Field("frame_partial_frames_discarded", split.partial_frames_discarded) + "," +
               Field("rss_kib", ResidentKiB()));
}

// Runs the throw of a fault signal inside a try/catch (abort matrix).
void RunFault(FaultVariant variant, rclcpp::Node& node) {
  const std::string name{de4sdv::score_adapter::ToText(variant)};
  LogEvent("fault_hook_trigger", Field("variant", name));
  std::string caught;
  switch (variant) {
    case FaultVariant::kRclcpp:
      caught = fault_hook::ThrowInsideRclcpp(node);
      break;
    case FaultVariant::kAdapterCode:
      caught = fault_hook::ThrowInAdapterCode();
      break;
    case FaultVariant::kLibstdcxx:
      caught = fault_hook::ThrowInsideLibstdcxx();
      break;
    case FaultVariant::kNone:
    default:
      return;
  }
  LogEvent("fault_hook_caught", Field("variant", name) + "," + Field("what", caught));
}

std::string FaultSignalsField() {
  std::string text = Quote("fault_signals") + ":{";
  bool first = true;
  for (const FaultVariant variant : {FaultVariant::kRclcpp, FaultVariant::kAdapterCode, FaultVariant::kLibstdcxx}) {
    text += (first ? "" : ",") + Quote(de4sdv::score_adapter::ToText(variant)) + ":" +
            std::to_string(de4sdv::score_adapter::SignalFor(variant));
    first = false;
  }
  return text + "}";
}

}  // namespace

int main(int argc, char** argv) {
  Options options;
  if (!ParseOptions(argc, argv, &options)) {
    std::fprintf(stderr,
                 "usage: de4sdv_score_adapter --mw-com-config <mw_com_config.json> [--frame-host 127.0.0.1] "
                 "[--frame-port 4721] [--status-period-s 10] [--ros-args ...]\n");
    return exit_code::kConfigurationError;
  }
  struct sigaction action {};
  action.sa_handler = OnStopSignal;
  sigemptyset(&action.sa_mask);
  sigaction(SIGTERM, &action, nullptr);
  sigaction(SIGINT, &action, nullptr);
  struct sigaction fault_action {};
  fault_action.sa_handler = OnFaultSignal;
  sigemptyset(&fault_action.sa_mask);
  for (const FaultVariant variant : {FaultVariant::kRclcpp, FaultVariant::kAdapterCode, FaultVariant::kLibstdcxx}) {
    sigaction(de4sdv::score_adapter::SignalFor(variant), &fault_action, nullptr);
  }

  LogEvent("start", Field("pid", static_cast<std::int64_t>(::getpid())) + "," +
                        Field("mw_com_config", options.mw_com_config) + "," + FaultSignalsField());

  // Rule 2 needs SIGTERM to set the flag only; rclcpp installs no handler.
  rclcpp::init(argc, argv, rclcpp::InitOptions(), rclcpp::SignalHandlerOptions::None);
  if (!score_facade::InitializeRuntime(options.mw_com_config.c_str())) {
    LogEvent("configuration_error", Field("reason", std::string{"mw::com configuration not readable"}));
    rclcpp::shutdown();
    return exit_code::kConfigurationError;
  }

  auto node = std::make_shared<rclcpp::Node>(kNodeName, rclcpp::NodeOptions()
                                                            .start_parameter_services(false)
                                                            .start_parameter_event_publisher(false)
                                                            .enable_rosout(false));
  VelocityPublisher publisher{*node};
  LogEvent("ros_node_ready", Field("node", std::string{kNodeName}) + "," +
                                 Field("topic", std::string{kVelocityTopic}) + "," +
                                 Field("parameter_services", false) + "," +
                                 Field("rmw", std::string{rmw_get_implementation_identifier()}));

  // Rule 3: offer the frame skeleton once, at start.
  score_facade::FramePublisher frame_publisher{kFrameInstanceSpecifier};
  FacadeFrameEventPort frame_port{frame_publisher};
  FramePathController frame_controller{frame_port};
  if (!frame_publisher.Create() || !frame_controller.Start()) {
    LogEvent("frame_offer_failed", Field("reason", std::string{frame_publisher.LastError()}) + "," +
                                       Field("exit_code", static_cast<std::int64_t>(exit_code::kFrameOfferFailed)));
    rclcpp::shutdown();
    return exit_code::kFrameOfferFailed;
  }
  LogEvent("frame_offered", Field("instance", std::string{kFrameInstanceSpecifier}));
  FrameSplitter splitter{score_facade::kFrameSampleBytes};
  std::atomic<bool> frame_stop{false};
  std::thread frame_thread{FrameIngestLoop, std::cref(options), std::ref(frame_controller), std::ref(splitter),
                           std::cref(frame_stop)};

  rclcpp::executors::SingleThreadedExecutor executor;
  executor.add_node(node);
  std::thread executor_thread{[&executor] { executor.spin(); }};

  score_facade::SpeedSubscriber subscriber{kSpeedInstanceSpecifier};
  FacadeSpeedEventPort speed_port{subscriber};
  SpeedEventLog speed_log;
  SpeedPathController speed_controller{speed_port, publisher, kSpeedMaxSamples, &speed_log};
  Wakeup wakeup;
  SpeedHandlerContext handler_context{&speed_controller, &wakeup};
  speed_port.BindHandlers(&OnSpeedSubscriptionState, &OnSpeedSamplesReceived, &handler_context);

  int exit_status = 0;
  bool ready_logged = false;
  bool not_found_logged = false;
  const auto status_period = std::chrono::seconds{options.status_period_s};
  auto next_find = std::chrono::steady_clock::now();
  auto next_status = std::chrono::steady_clock::now() + status_period;
  while (!g_stop_requested.load()) {
    const auto now = std::chrono::steady_clock::now();
    if (!subscriber.HasProxy() && now >= next_find) {
      if (subscriber.FindAndCreate()) {
        const SubscribeResult subscribed = speed_controller.Subscribe();
        if (subscribed != SubscribeResult::kSubscribed) {
          // Not retried in the process: the adapter ends with its own exit
          // code, through the shutdown of rule 2, so the Launch Manager sees
          // the failure.
          LogEvent("speed_subscribe_failed",
                   Field("step", std::string{de4sdv::score_adapter::ToText(subscribed)}) + "," +
                       Field("reason", std::string{subscriber.LastError()}) + "," +
                       Field("exit_code", static_cast<std::int64_t>(exit_code::kSpeedSubscribeFailed)));
          exit_status = exit_code::kSpeedSubscribeFailed;
          break;
        }
        LogEvent("speed_proxy_subscribed", Field("instance", std::string{kSpeedInstanceSpecifier}) + "," +
                                               Field("max_samples", static_cast<std::uint64_t>(kSpeedMaxSamples)));
      } else {
        if (!not_found_logged) {
          LogEvent("speed_provider_not_found", Field("reason", std::string{subscriber.LastError()}));
          not_found_logged = true;
        }
        next_find = now + std::chrono::milliseconds{200};
      }
    }
    speed_controller.ReadAvailable();
    const FaultVariant fault = g_fault_request.Take();
    if (fault != FaultVariant::kNone) {
      RunFault(fault, *node);
    }
    if (!ready_logged && subscriber.HasProxy() && speed_port.State() == SubscriptionState::kSubscribed &&
        frame_controller.offered()) {
      LogEvent("ready");
      ready_logged = true;
    }
    if (now >= next_status) {
      LogStatus("status", speed_controller, frame_controller, splitter, speed_port.State());
      next_status += status_period;
    }
    wakeup.WaitFor(std::chrono::milliseconds{20});
  }

  if (exit_status == 0) {
    LogEvent("stop_requested");
  }
  // Rule 2: no read, no receive handler, no held sample, Unsubscribe(), wait
  // for kNotSubscribed, then destroy the proxy.
  const ShutdownResult speed_result = speed_controller.Shutdown(std::chrono::milliseconds{2000});
  const char* speed_result_text = speed_result == ShutdownResult::kProxyDestroyed  ? "proxy_destroyed"
                                  : speed_result == ShutdownResult::kNoProxy       ? "no_proxy"
                                                                                   : "still_subscribed";
  LogEvent("speed_path_stopped", Field("result", std::string{speed_result_text}));
  if (speed_result == ShutdownResult::kStillSubscribed) {
    // Destroying a subscribed proxy aborts the process (GAP-MW-041); end
    // without destructors instead.
    std::fflush(stdout);
    std::_Exit(exit_code::kStillSubscribed);
  }
  frame_stop.store(true);
  frame_thread.join();
  frame_controller.Stop();  // rule 3: the skeleton goes only at exit
  LogEvent("frame_skeleton_destroyed");
  executor.cancel();
  executor_thread.join();
  LogStatus("final_status", speed_controller, frame_controller, splitter, speed_port.State());
  executor.remove_node(node);
  node.reset();
  rclcpp::shutdown();
  LogEvent("exit", Field("code", static_cast<std::int64_t>(exit_status)));
  return exit_status;
}
