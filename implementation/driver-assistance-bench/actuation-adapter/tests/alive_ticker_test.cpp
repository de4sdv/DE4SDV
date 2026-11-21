// Tests of the actuation adapter's alive supervision (alive_ticker.h) against a fake lifecycle client: the
// supervision decision of 2026-11-18. The times are monotonic seconds chosen by the test; no clock is read.
#include <cstdint>
#include <string>
#include <vector>

#include "alive_ticker.h"
#include "check.h"
#include "json_lite.h"
#include "run_log.h"

using de4sdv::driver_assistance::RecordSink;
using de4sdv::driver_assistance::actuation::AliveTicker;
using de4sdv::driver_assistance::actuation::LifecycleClient;
using de4sdv::driver_assistance::actuation::RecordWriter;
using de4sdv::driver_assistance::actuation::test::Finish;
using de4sdv::driver_assistance::json::Value;

namespace {

class FakeLifecycle : public LifecycleClient {
 public:
  bool ReportRunning() override {
    calls.push_back("running");
    return running_ok;
  }
  void ReportAlive() override { calls.push_back("alive"); }
  int Count(const std::string& name) const {
    int n = 0;
    for (const auto& c : calls) n += (c == name) ? 1 : 0;
    return n;
  }
  std::vector<std::string> calls;
  bool running_ok = true;
};

struct Record {
  std::string event;
  Value data;
};

class CaptureSink : public RecordSink {
 public:
  void Write(const std::string& event, std::uint64_t /*seq*/, const std::string& data_json) override {
    std::string error;
    records.push_back({event, Value::Parse(data_json, &error)});
    parse_errors += error.empty() ? 0 : 1;
  }
  std::vector<Record> records;
  int parse_errors = 0;
  std::vector<std::string> States() const {
    std::vector<std::string> out;
    for (const auto& r : records) {
      if (r.event == "supervision") out.push_back(r.data.Find("state") ? r.data.Find("state")->AsString("") : "");
    }
    return out;
  }
};

constexpr double kPeriodS = 0.1;  // one notification per 0.1 s command cycle (launch-manager/README.md)

// One alive notification per 0.1 s of the receive loop, whatever the loop's own pace (1 ms polls here).
void TestOneAlivePerTick() {
  FakeLifecycle lc;
  CaptureSink sink;
  RecordWriter writer(&sink);
  AliveTicker ticker(&lc, kPeriodS, &writer);
  CHECK(lc.calls.empty());
  CHECK(ticker.Start(10.0, ""));
  // running first, then the first notification at once
  CHECK((lc.calls == std::vector<std::string>{"running", "alive"}));
  // 1 s of 1 ms passes: 10 more notifications (at 10.1, 10.2, ..., 11.0)
  for (int ms = 1; ms <= 1000; ++ms) ticker.Tick(10.0 + ms * 0.001, false);
  CHECK(lc.Count("alive") == 11);
  CHECK(ticker.AliveCount() == 11u);
  CHECK(lc.Count("running") == 1);
  CHECK((sink.States() == std::vector<std::string>{"start"}));
  CHECK(sink.parse_errors == 0);
  const Value& start = sink.records.front().data;
  CHECK(start.Find("period_s") != nullptr && start.Find("period_s")->AsNumber(0.0) == kPeriodS);
  CHECK(start.Find("running_reported") != nullptr && start.Find("running_reported")->AsBool(false));
}

// A stalled loop gives no burst afterwards: one notification when it resumes, then the period again.
void TestNoBurstAfterAStall() {
  FakeLifecycle lc;
  CaptureSink sink;
  RecordWriter writer(&sink);
  AliveTicker ticker(&lc, kPeriodS, &writer);
  CHECK(ticker.Start(0.0, ""));
  ticker.Tick(0.05, false);  // not yet
  CHECK(lc.Count("alive") == 1);
  ticker.Tick(0.75, false);  // the loop stalled for 0.7 s
  CHECK(lc.Count("alive") == 2);
  ticker.Tick(0.76, false);
  ticker.Tick(0.84, false);
  CHECK(lc.Count("alive") == 2);
  ticker.Tick(0.85, false);
  CHECK(lc.Count("alive") == 3);
}

// No notification after the stop request, and none after Stop().
void TestNoneAfterStop() {
  FakeLifecycle lc;
  CaptureSink sink;
  RecordWriter writer(&sink);
  AliveTicker ticker(&lc, kPeriodS, &writer);
  CHECK(ticker.Start(0.0, ""));
  ticker.Tick(0.1, false);
  CHECK(lc.Count("alive") == 2);
  ticker.Tick(0.2, true);   // the signal arrived
  ticker.Tick(0.3, false);  // and stays
  CHECK(lc.Count("alive") == 2);
  ticker.Stop(0.35);
  ticker.Tick(0.5, false);
  ticker.Stop(0.6);  // idempotent
  CHECK(lc.Count("alive") == 2);
  CHECK((sink.States() == std::vector<std::string>{"start", "stop"}));
  const Value& stop = sink.records.back().data;
  CHECK(stop.Find("alive_reported") != nullptr && stop.Find("alive_reported")->AsNumber(-1.0) == 2.0);
}

// Nothing before Start(): the adapter reports running only once it has subscribed.
void TestNothingBeforeStart() {
  FakeLifecycle lc;
  CaptureSink sink;
  RecordWriter writer(&sink);
  AliveTicker ticker(&lc, kPeriodS, &writer);
  ticker.Tick(1.0, false);
  ticker.Tick(2.0, false);
  CHECK(lc.calls.empty());
  CHECK(sink.records.empty());
}

// Not started by the Launch Manager as a supervised component: no client, one supervision record that says so.
void TestUnsupervised() {
  CaptureSink sink;
  RecordWriter writer(&sink);
  AliveTicker ticker(nullptr, kPeriodS, &writer);
  CHECK(ticker.Start(0.0, "LCM_ALIVE_INTERFACE_PATH is unset"));
  ticker.Tick(0.5, false);
  ticker.Stop(1.0);
  CHECK(ticker.AliveCount() == 0u);
  CHECK((sink.States() == std::vector<std::string>{"off"}));
  const Value& off = sink.records.front().data;
  CHECK(off.Find("reason") != nullptr && off.Find("reason")->AsString("") == "LCM_ALIVE_INTERFACE_PATH is unset");
}

// report_running fails: recorded as an error, Start() returns false, the notifications still go out.
void TestRunningFails() {
  FakeLifecycle lc;
  lc.running_ok = false;
  CaptureSink sink;
  RecordWriter writer(&sink);
  AliveTicker ticker(&lc, kPeriodS, &writer);
  CHECK(!ticker.Start(0.0, ""));
  ticker.Tick(0.1, false);
  CHECK(lc.Count("alive") == 2);
  CHECK((sink.States() == std::vector<std::string>{"error"}));
}

}  // namespace

int main() {
  TestOneAlivePerTick();
  TestNoBurstAfterAStall();
  TestNoneAfterStop();
  TestNothingBeforeStart();
  TestUnsupervised();
  TestRunningFails();
  return Finish("alive_ticker_test");
}
