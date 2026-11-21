// Unit tests of the stop run's Launch Manager control client core (launch-manager/control/lm_control_client.h):
// a fake ControlPort (its callbacks delivered as Lifecycle v0.10.0's receive handler would, on another thread when
// asked) and a fake clock. No S-CORE header.
//
// Build: g++ -std=c++17 -Wall -Wextra -Werror -pthread -I<control> lm_control_client_test.cpp <control>/lm_control_client.cpp
// Run:   lm_control_client_test
#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <string>
#include <thread>
#include <vector>

#include "lm_control_client.h"

namespace lm = de4sdv::lm_control;

static int failures = 0;
#define EXPECT(cond)                                              \
  do {                                                            \
    if (!(cond)) {                                                \
      std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
      ++failures;                                                 \
    }                                                             \
  } while (0)

namespace {

// A clock whose instants advance by 1000 ns each read; SleepMs adds the sleep.
class FakeClock final : public lm::Clock {
 public:
  std::int64_t RealNs() override { return real_ += 1000; }  // atomic: the callback reads it on its own thread
  std::int64_t MonoNs() override { return mono_ += 1000; }
  void SleepMs(int ms) override {
    slept_ms += ms;
    real_ += static_cast<std::int64_t>(ms) * 1000000;
    mono_ += static_cast<std::int64_t>(ms) * 1000000;
    if (on_sleep) on_sleep();
  }
  std::atomic<std::int64_t> real_{1795168000000000000LL};
  std::atomic<std::int64_t> mono_{1000000000000LL};
  int slept_ms = 0;
  std::function<void()> on_sleep;
};

struct FakePort final : lm::ControlPort {
  Callback callback;
  bool register_ok = true;
  bool connect_ok = true;
  bool activate_ok = true;
  std::string error = "kRunTargetDoesntExist";
  std::vector<std::string> calls;
  // what the Launch Manager reports after the request: (source, target), each on its own thread
  std::vector<std::pair<lm::Source, std::string>> after_request;
  std::vector<std::thread> threads;

  bool RegisterCallback(Callback cb, std::string* err) override {
    calls.push_back("register");
    if (!register_ok) *err = "kInvalidArguments";
    callback = std::move(cb);
    return register_ok;
  }
  bool WaitForConnection(int timeout_ms, std::string* err) override {
    calls.push_back("connect:" + std::to_string(timeout_ms));
    if (!connect_ok) *err = "kCommunicationError";
    return connect_ok;
  }
  bool Activate(const std::string& target, std::string* err) override {
    calls.push_back("activate:" + target);
    if (!activate_ok) {
      *err = error;
      return false;
    }
    int delay_ms = 0;
    for (const auto& r : after_request) {
      delay_ms += 20;  // in the listed order
      threads.emplace_back([this, r, delay_ms] {
        std::this_thread::sleep_for(std::chrono::milliseconds(delay_ms));
        callback(r.first, r.second);
      });
    }
    return true;
  }
  ~FakePort() override {
    for (auto& t : threads) t.join();
  }
};

lm::Options Opts() {
  lm::Options o;
  o.run_target = "path_stopped";
  o.mw_com_config = "/tmp/de4sdv-da-bench/config/mw_com_config_lm_control_client.json";
  o.settle_timeout_ms = 2000;
  return o;
}

void ParsesTheArguments() {
  const char* argv[] = {"lm_control_client", "--run-target", "path_stopped", "--mw-com-config", "/x.json",
                        "--settle-timeout-ms", "15000", "--connect-timeout-ms", "4000", "--drain-ms", "0"};
  lm::Options o;
  std::string error;
  EXPECT(lm::ParseArguments(11, argv, &o, &error));
  EXPECT(o.run_target == "path_stopped" && o.mw_com_config == "/x.json");
  EXPECT(o.settle_timeout_ms == 15000 && o.connect_timeout_ms == 4000 && o.drain_ms == 0);
  EXPECT(o.instance_specifier == "StateManager/LaunchManager/Instance");
  const char* no_config[] = {"c", "--run-target", "path_stopped"};
  lm::Options o2;
  EXPECT(!lm::ParseArguments(3, no_config, &o2, &error));
  const char* bad[] = {"c", "--run-target", "path_stopped", "--mw-com-config", "/x", "--settle-timeout-ms", "x"};
  lm::Options o3;
  EXPECT(!lm::ParseArguments(7, bad, &o3, &error));
  const char* unknown[] = {"c", "--force", "no"};
  lm::Options o4;
  EXPECT(!lm::ParseArguments(3, unknown, &o4, &error));
}

void SettlesOnTheRequestedTarget() {
  FakePort port;
  FakeClock clock;
  // the start's activation, read at the subscription, arrives during the drain: set aside
  clock.on_sleep = [&] { port.callback(lm::Source::kInitial, "supervised_path"); };
  port.after_request = {{lm::Source::kRequest, "path_stopped"}};
  const lm::Outcome out = lm::ActivateAndSettle(port, clock, Opts());
  EXPECT(out.rc == lm::kSettled);
  EXPECT(out.earlier_results == 1);
  EXPECT(out.settled_target == "path_stopped" && out.settled_source == "request");
  EXPECT(out.settled_real_ns > out.request_real_ns && out.settled_mono_ns > out.request_mono_ns);
  // the stop instant is the settlement, when the target's components had ended
  EXPECT(out.StopRealNs() == out.settled_real_ns && out.StopMonoNs() == out.settled_mono_ns);
  EXPECT((port.calls == std::vector<std::string>{"register", "connect:5000", "activate:path_stopped"}));
  EXPECT(clock.slept_ms == 200);
  const std::string json = lm::OutcomeJson(Opts(), out);
  EXPECT(json.rfind("{\"runTarget\":\"path_stopped\",\"stopInstantRealNs\":" + std::to_string(out.settled_real_ns) +
                        ",\"stopInstantMonoNs\":" + std::to_string(out.settled_mono_ns) + ",\"rc\":0,",
                    0) == 0);
  EXPECT(json.find('\n') == std::string::npos);
}

void ALateInitialResultIsNotTheSettlement() {
  FakePort port;
  FakeClock clock;
  port.after_request = {{lm::Source::kInitial, "supervised_path"}, {lm::Source::kRequest, "path_stopped"}};
  const lm::Outcome out = lm::ActivateAndSettle(port, clock, Opts());
  EXPECT(out.rc == lm::kSettled);
  EXPECT(out.settled_target == "path_stopped");
}

void ARecoveryAfterTheRequestIsReported() {
  FakePort port;
  FakeClock clock;
  port.after_request = {{lm::Source::kRecovery, "fallback_run_target"}};
  const lm::Outcome out = lm::ActivateAndSettle(port, clock, Opts());
  EXPECT(out.rc == lm::kSettledElsewhere);
  EXPECT(out.settled_target == "fallback_run_target" && out.settled_source == "recovery");
  EXPECT(out.StopRealNs() == out.request_real_ns);  // no stop of the path was reported
}

void ARejectionIsReportedWithTheRequestInstant() {
  FakePort port;
  FakeClock clock;
  port.activate_ok = false;
  const lm::Outcome out = lm::ActivateAndSettle(port, clock, Opts());
  EXPECT(out.rc == lm::kRejected);
  EXPECT(out.error.find("kRunTargetDoesntExist") != std::string::npos);
  EXPECT(out.request_real_ns != 0 && out.StopRealNs() == out.request_real_ns);
  EXPECT(lm::OutcomeJson(Opts(), out).find("\"rc\":4,") != std::string::npos);
}

void NoServiceIsReported() {
  FakePort port;
  FakeClock clock;
  port.connect_ok = false;
  const lm::Outcome out = lm::ActivateAndSettle(port, clock, Opts());
  EXPECT(out.rc == lm::kNotConnected);
  EXPECT((port.calls == std::vector<std::string>{"register", "connect:5000"}));  // nothing requested
}

void NoSettlementTimesOut() {
  FakePort port;
  FakeClock clock;
  lm::Options o = Opts();
  o.settle_timeout_ms = 100;
  const auto t0 = std::chrono::steady_clock::now();
  const lm::Outcome out = lm::ActivateAndSettle(port, clock, o);
  EXPECT(out.rc == lm::kNotSettled);
  EXPECT(std::chrono::steady_clock::now() - t0 >= std::chrono::milliseconds(100));
}

void TheJsonEscapesTheError() {
  lm::Outcome out;
  out.rc = lm::kRejected;
  out.error = "a \"quoted\" \\ line\nbreak";
  const std::string json = lm::OutcomeJson(Opts(), out);
  EXPECT(json.find("\"error\":\"a \\\"quoted\\\" \\\\ line\\nbreak\"}") != std::string::npos);
}

}  // namespace

int main() {
  ParsesTheArguments();
  SettlesOnTheRequestedTarget();
  ALateInitialResultIsNotTheSettlement();
  ARecoveryAfterTheRequestIsReported();
  ARejectionIsReportedWithTheRequestInstant();
  NoServiceIsReported();
  NoSettlementTimesOut();
  TheJsonEscapesTheError();
  if (failures != 0) {
    std::printf("lm_control_client_test: %d failed\n", failures);
    return 1;
  }
  std::printf("lm_control_client_test: all passed\n");
  return 0;
}
