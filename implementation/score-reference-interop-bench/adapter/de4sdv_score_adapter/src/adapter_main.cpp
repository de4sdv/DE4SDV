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
// The node creates no other publisher or subscription: the parameter event
// publisher and /rosout are off. The parameter services stay, for the abort
// matrix of VC-MW-019. Every log line on stdout is one JSON object.

#include <arpa/inet.h>
#include <netinet/in.h>
#include <poll.h>
#include <signal.h>
#include <sys/socket.h>
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
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include "autoware_vehicle_msgs/msg/velocity_report.hpp"
#include "de4sdv_score_adapter/frame_path_controller.hpp"
#include "de4sdv_score_adapter/frame_splitter.hpp"
#include "de4sdv_score_adapter/speed_path_controller.hpp"
#include "de4sdv_score_facade/score_facade.h"
#include "facade_ports.hpp"
#include "fault_hook.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rmw/rmw.h"

namespace {

using de4sdv::score_adapter::FacadeFrameEventPort;
using de4sdv::score_adapter::FacadeSpeedEventPort;
using de4sdv::score_adapter::FramePathController;
using de4sdv::score_adapter::FrameSplitter;
using de4sdv::score_adapter::ReconnectBackoff;
using de4sdv::score_adapter::ShutdownResult;
using de4sdv::score_adapter::SpeedPathController;
using de4sdv::score_adapter::SpeedPathEvents;
using de4sdv::score_adapter::SubscriptionState;
using de4sdv::score_adapter::TranslationOutcome;
using de4sdv::score_adapter::VelocityPublisherPort;
namespace fault_hook = de4sdv::score_adapter::fault_hook;
namespace score_facade = de4sdv::score_facade;

constexpr const char* kNodeName = "de4sdv_score_adapter";
constexpr const char* kVelocityTopic = "/de4sdv/middleware/velocity_status";
constexpr const char* kFrameId = "base_link";
constexpr const char* kSpeedInstanceSpecifier = "de4sdv/reference_vehicle_speed";
constexpr const char* kFrameInstanceSpecifier = "de4sdv/aebs_signal_frame";
constexpr std::size_t kSpeedMaxSamples = 5;
constexpr int kExitConfigurationError = 2;
constexpr int kExitStillSubscribed = 3;
constexpr int kExitFrameOfferFailed = 4;

std::atomic<bool> g_stop_requested{false};

extern "C" void OnStopSignal(int /*signal*/) { g_stop_requested.store(true); }

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
      : node_{node},
        publisher_{node.create_publisher<autoware_vehicle_msgs::msg::VelocityReport>(
            kVelocityTopic, rclcpp::QoS(rclcpp::KeepLast(10)).reliable())} {}

  void Publish(float longitudinal_velocity_mps) override {
    autoware_vehicle_msgs::msg::VelocityReport message;
    message.header.stamp = node_.get_clock()->now();
    message.header.frame_id = kFrameId;
    message.longitudinal_velocity = longitudinal_velocity_mps;
    message.lateral_velocity = 0.0F;
    message.heading_rate = 0.0F;
    publisher_->publish(message);
  }

 private:
  rclcpp::Node& node_;
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

void FrameIngestLoop(const Options& options, FramePathController& controller, FrameSplitter& splitter,
                     const std::atomic<bool>& stop) {
  ReconnectBackoff backoff{std::chrono::milliseconds{100}, std::chrono::milliseconds{2000}};
  std::vector<std::uint8_t> buffer(8192);
  sockaddr_in address{};
  address.sin_family = AF_INET;
  address.sin_port = htons(options.frame_port);
  if (inet_pton(AF_INET, options.frame_host.c_str(), &address.sin_addr) != 1) {
    LogEvent("frame_stream_error", Field("reason", std::string{"invalid --frame-host"}));
    return;
  }
  bool waiting_logged = false;
  while (!stop.load()) {
    const int fd = ::socket(AF_INET, SOCK_STREAM | SOCK_CLOEXEC, 0);
    if (fd < 0 || ::connect(fd, reinterpret_cast<const sockaddr*>(&address), sizeof(address)) != 0) {
      if (fd >= 0) {
        ::close(fd);
      }
      if (!waiting_logged) {
        LogEvent("frame_stream_waiting", Field("host", options.frame_host) + "," +
                                             Field("port", static_cast<std::uint64_t>(options.frame_port)));
        waiting_logged = true;
      }
      SleepUnlessStopped(backoff.NextDelay(), stop);
      continue;
    }
    backoff.Reset();
    waiting_logged = false;
    controller.OnConnectionEstablished();
    LogEvent("frame_stream_connected");
    while (!stop.load()) {
      pollfd poll_fd{fd, POLLIN, 0};
      const int ready = ::poll(&poll_fd, 1, 100);
      if (ready < 0) {
        if (errno == EINTR) {
          continue;
        }
        break;
      }
      if (ready == 0) {
        continue;
      }
      const ssize_t received = ::recv(fd, buffer.data(), buffer.size(), 0);
      if (received > 0) {
        splitter.Feed(buffer.data(), static_cast<std::size_t>(received),
                      [&controller](const std::uint8_t* sample, std::size_t size) { controller.OnFrame(sample, size); });
        continue;
      }
      if (received < 0 && (errno == EINTR || errno == EAGAIN)) {
        continue;
      }
      break;  // closed by the frame assembler, or an error
    }
    ::close(fd);
    splitter.Reset();
    if (stop.load()) {
      break;  // the adapter's own shutdown, not a loss of the stream
    }
    controller.OnConnectionLost();  // rule 3: the offer stays
    LogEvent("frame_stream_lost");
  }
}

void LogStatus(const char* event, const SpeedPathController& speed, const FramePathController& frames,
               const FrameSplitter& splitter, SubscriptionState state) {
  const auto s = speed.counters();
  const auto f = frames.counters();
  const auto& split = splitter.stats();
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
               Field("frames_dropped_oversize", split.frames_dropped_oversize) + "," +
               Field("frame_bytes_read", split.bytes_read) + "," +
               Field("frame_partial_frames_discarded", split.partial_frames_discarded) + "," +
               Field("rss_kib", ResidentKiB()));
}

rcl_interfaces::msg::SetParametersResult OnFaultHookParameter(const std::vector<rclcpp::Parameter>& parameters) {
  rcl_interfaces::msg::SetParametersResult result;
  result.successful = true;
  for (const auto& parameter : parameters) {
    if (parameter.get_name() != fault_hook::kParameterName) {
      continue;
    }
    if (parameter.get_type() != rclcpp::ParameterType::PARAMETER_STRING) {
      result.successful = false;
      result.reason = "a string is expected";
      continue;
    }
    const std::string variant = parameter.as_string();
    if (variant == "adapter_code") {
      LogEvent("fault_hook_trigger", Field("variant", variant));
      const std::string caught = fault_hook::ThrowInAdapterCode();
      LogEvent("fault_hook_caught", Field("variant", variant) + "," + Field("what", caught));
    } else if (variant == "libstdcxx") {
      LogEvent("fault_hook_trigger", Field("variant", variant));
      const std::string caught = fault_hook::ThrowInsideLibstdcxx();
      LogEvent("fault_hook_caught", Field("variant", variant) + "," + Field("what", caught));
    } else if (variant != "none") {
      result.successful = false;
      result.reason = "unknown variant";
    }
  }
  return result;
}

}  // namespace

int main(int argc, char** argv) {
  Options options;
  if (!ParseOptions(argc, argv, &options)) {
    std::fprintf(stderr,
                 "usage: de4sdv_score_adapter --mw-com-config <mw_com_config.json> [--frame-host 127.0.0.1] "
                 "[--frame-port 4721] [--status-period-s 10] [--ros-args ...]\n");
    return kExitConfigurationError;
  }
  struct sigaction action {};
  action.sa_handler = OnStopSignal;
  sigemptyset(&action.sa_mask);
  sigaction(SIGTERM, &action, nullptr);
  sigaction(SIGINT, &action, nullptr);

  const bool hook_enabled = fault_hook::EnabledByEnvironment();
  LogEvent("start", Field("pid", static_cast<std::int64_t>(::getpid())) + "," +
                        Field("mw_com_config", options.mw_com_config) + "," +
                        Field("fault_hook_enabled", hook_enabled) + "," +
                        Field("fault_hook_environment",
                              std::string{fault_hook::kEnvironmentVariable} + "=" + fault_hook::EnvironmentSetting()));

  // Rule 2 needs SIGTERM to set the flag only; rclcpp installs no handler.
  rclcpp::init(argc, argv, rclcpp::InitOptions(), rclcpp::SignalHandlerOptions::None);
  if (!score_facade::InitializeRuntime(options.mw_com_config.c_str())) {
    LogEvent("configuration_error", Field("reason", std::string{"mw::com configuration not readable"}));
    rclcpp::shutdown();
    return kExitConfigurationError;
  }

  auto node = std::make_shared<rclcpp::Node>(
      kNodeName, rclcpp::NodeOptions().start_parameter_event_publisher(false).enable_rosout(false));
  VelocityPublisher publisher{*node};
  rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr hook_handle;
  if (hook_enabled) {
    node->declare_parameter<std::string>(fault_hook::kParameterName, "none");
    hook_handle = node->add_on_set_parameters_callback(&OnFaultHookParameter);
  }
  LogEvent("ros_node_ready", Field("node", std::string{kNodeName}) + "," +
                                 Field("topic", std::string{kVelocityTopic}) + "," +
                                 Field("rmw", std::string{rmw_get_implementation_identifier()}));

  // Rule 3: offer the frame skeleton once, at start.
  score_facade::FramePublisher frame_publisher{kFrameInstanceSpecifier};
  FacadeFrameEventPort frame_port{frame_publisher};
  FramePathController frame_controller{frame_port};
  if (!frame_publisher.Create() || !frame_controller.Start()) {
    LogEvent("frame_offer_failed", Field("reason", std::string{frame_publisher.LastError()}));
    rclcpp::shutdown();
    return kExitFrameOfferFailed;
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

  bool ready_logged = false;
  bool not_found_logged = false;
  const auto status_period = std::chrono::seconds{options.status_period_s};
  auto next_find = std::chrono::steady_clock::now();
  auto next_status = std::chrono::steady_clock::now() + status_period;
  while (!g_stop_requested.load()) {
    const auto now = std::chrono::steady_clock::now();
    if (!subscriber.HasProxy() && now >= next_find) {
      if (subscriber.FindAndCreate()) {
        // Handlers first, so the controller sees every state change.
        if (!subscriber.SetStateHandler(&OnSpeedSubscriptionState, &handler_context) ||
            !subscriber.SetReceiveHandler(&OnSpeedSamplesReceived, &handler_context) ||
            !speed_controller.Subscribe()) {
          LogEvent("speed_subscribe_failed", Field("reason", std::string{subscriber.LastError()}));
        } else {
          LogEvent("speed_proxy_subscribed", Field("instance", std::string{kSpeedInstanceSpecifier}) + "," +
                                                 Field("max_samples", static_cast<std::uint64_t>(kSpeedMaxSamples)));
        }
      } else {
        if (!not_found_logged) {
          LogEvent("speed_provider_not_found", Field("reason", std::string{subscriber.LastError()}));
          not_found_logged = true;
        }
        next_find = now + std::chrono::milliseconds{200};
      }
    }
    speed_controller.ReadAvailable();
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

  LogEvent("stop_requested");
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
    std::_Exit(kExitStillSubscribed);
  }
  frame_stop.store(true);
  frame_thread.join();
  frame_controller.Stop();  // rule 3: the skeleton goes only at exit
  LogEvent("frame_skeleton_destroyed");
  executor.cancel();
  executor_thread.join();
  LogStatus("final_status", speed_controller, frame_controller, splitter, speed_port.State());
  hook_handle.reset();
  executor.remove_node(node);
  node.reset();
  rclcpp::shutdown();
  LogEvent("exit", Field("code", static_cast<std::int64_t>(0)));
  return 0;
}
