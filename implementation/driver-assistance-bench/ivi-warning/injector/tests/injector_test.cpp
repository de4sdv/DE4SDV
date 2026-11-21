// Unit tests of the warning-request test publisher: the plan (injection_plan.h) and the shell (injector_shell.h)
// with a fake mw::com sink and a fake clock. With --encode <requested> <issue_time_s> it prints the 8 bytes, which
// test_injector_units.py compares with Python's struct (no byte vector is written into this file).
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <string>
#include <vector>

#include "check.h"
#include "injection_plan.h"
#include "injector_shell.h"
#include "run_log.h"

namespace inj = de4sdv::driver_assistance::injector;
using de4sdv::driver_assistance::RecordSink;

namespace {

class FakeSink final : public inj::WarningSink {
 public:
  bool Offer(std::string* error) override {
    calls.push_back("offer");
    if (!offer_ok) *error = "fake refused";
    return offer_ok;
  }
  bool Send(const std::uint8_t* bytes, std::size_t size) override {
    calls.push_back("send");
    sent.emplace_back(bytes, bytes + size);
    sent_at.push_back(*now);
    return fail_at < 0 || static_cast<int>(sent.size()) != fail_at;
  }
  void StopOffer() override { calls.push_back("stop_offer"); }
  bool offer_ok = true;
  int fail_at = -1;
  std::int64_t* now = nullptr;
  std::vector<std::string> calls;
  std::vector<std::vector<std::uint8_t>> sent;
  std::vector<std::int64_t> sent_at;
};

class CaptureSink final : public RecordSink {
 public:
  void Write(const std::string& event, std::uint64_t seq, const std::string& data) override {
    events.push_back(event);
    data_of.push_back(data);
    seqs.push_back(seq);
  }
  std::vector<std::string> events;
  std::vector<std::string> data_of;
  std::vector<std::uint64_t> seqs;
};

struct FakeClock {
  std::int64_t mono = 7000000000LL;
  std::int64_t real_offset = 1763500000000000000LL;
  int stop_after_sleeps = -1;
  int sleeps = 0;
  inj::Clocks Make() {
    inj::Clocks c;
    c.mono_ns = [this] { return mono; };
    c.real_ns = [this] { return mono + real_offset; };
    c.sleep_until = [this](std::int64_t t) {
      ++sleeps;
      if (stop_after_sleeps >= 0 && sleeps > stop_after_sleeps) return false;
      if (t > mono) mono = t;
      return true;
    };
    return c;
  }
};

void TestThePlan() {
  inj::InjectionPlan plan;
  std::string error;
  CHECK(inj::ParsePlan("# c\n0 false 10.0\n\n1.5 true 10.05  # rising\n2 1 10.1\n3.0 0 10.15\n", &plan, &error));
  CHECK(plan.requests.size() == 4);
  CHECK(plan.rising_edges == 1 && plan.falling_edges == 1);
  CHECK(plan.requests.size() == 4 && plan.requests[1].requested && plan.requests[1].issue_time_sim_ms == 10050u);
  CHECK(plan.requests.size() == 4 && plan.requests[1].offset_s == 1.5);
  const struct {
    const char* text;
    const char* fragment;
  } bad[] = {
      {"", "no request"},
      {"0 maybe 1.0\n", "requested must be"},
      {"0 true\n", "expected"},
      {"0 true 1.0 extra\n", "expected"},
      {"1 true 1.0\n1 false 2.0\n", "rise strictly"},
      {"1 true 1.0\n0.5 false 2.0\n", "rise strictly"},
      {"-1 true 1.0\n", "offset"},
      {"0 true -0.5\n", "32-bit"},
      {"0 true 5000000.0\n", "32-bit"},
      {"0 true nan\n", "not a number"},
      {"0 true 1.0\n1 false 1.0004\n", "used twice"},
  };
  for (const auto& b : bad) {
    error.clear();
    const bool ok = inj::ParsePlan(b.text, &plan, &error);
    CHECK(!ok);
    CHECK(error.find(b.fragment) != std::string::npos);
    if (ok || error.find(b.fragment) == std::string::npos) std::printf("  '%s' gave '%s'\n", b.text, error.c_str());
  }
  CHECK(inj::ParsePlan("0 true 1.0\n", &plan, &error) && plan.rising_edges == 1);  // a first true is an edge
}

void TestTheDefaultSequence(const char* path) {
  std::string text;
  if (std::FILE* f = std::fopen(path, "rb")) {
    char b[4096];
    std::size_t n = 0;
    while ((n = std::fread(b, 1, sizeof b, f)) > 0) text.append(b, n);
    std::fclose(f);
  }
  inj::InjectionPlan plan;
  std::string error;
  CHECK(inj::ParsePlan(text, &plan, &error));
  CHECK(plan.rising_edges == 10 && plan.falling_edges == 10);
  CHECK(!plan.requests.empty() && !plan.requests.front().requested && !plan.requests.back().requested);
}

void TestTheShellSendsOnScheduleAndLogsBothClocks() {
  inj::InjectionPlan plan;
  std::string error;
  CHECK(inj::ParsePlan("0 false 100.0\n0.5 true 100.05\n2.25 false 100.1\n", &plan, &error));
  FakeClock clock;
  FakeSink sink;
  sink.now = &clock.mono;
  CaptureSink log;
  inj::InjectionOptions options;
  options.lead_in_s = 5.0;
  options.tail_s = 2.0;
  const std::int64_t offered = clock.mono;
  CHECK(inj::Inject(plan, options, &sink, clock.Make(), &log) == inj::kInjected);
  CHECK((sink.calls == std::vector<std::string>{"offer", "send", "send", "send", "stop_offer"}));
  CHECK(sink.sent_at.size() == 3);
  if (sink.sent_at.size() == 3) {
    CHECK(sink.sent_at[0] == offered + 5000000000LL);
    CHECK(sink.sent_at[1] == offered + 5500000000LL);
    CHECK(sink.sent_at[2] == offered + 7250000000LL);
  }
  CHECK(clock.mono == offered + 9250000000LL);  // the tail
  // the bytes are the encoder's, nothing in front
  CHECK(sink.sent.size() == 3 && sink.sent[1].size() == 8);
  CHECK(sink.sent.size() == 3 && std::memcmp(sink.sent[1].data(), plan.requests[1].bytes, 8) == 0);
  CHECK((log.events == std::vector<std::string>{"offer", "out.warning_request", "out.warning_request",
                                                "out.warning_request", "stop"}));
  CHECK(log.seqs.back() == 5u);
  const std::string& second = log.data_of[2];
  CHECK(second.find("\"requested\":true") != std::string::npos);
  CHECK(second.find("\"issue_time_sim_ms\":100050") != std::string::npos);
  CHECK(second.find("\"bytes\":\"" + inj::HexBytes(plan.requests[1].bytes, 8) + "\"") != std::string::npos);
  CHECK(second.find("\"send_mono_ns\":" + std::to_string(offered + 5500000000LL)) != std::string::npos);
  CHECK(second.find("\"send_real_ns\":" + std::to_string(offered + 5500000000LL + clock.real_offset)) !=
        std::string::npos);
  CHECK(second.find("\"sent_real_ns\":") != std::string::npos && second.find("\"ok\":true") != std::string::npos);
  CHECK(log.data_of[0].find("\"rising_edges\":1") != std::string::npos);
  CHECK(log.data_of[4].find("\"sent\":3") != std::string::npos);
}

void TestFailures() {
  inj::InjectionPlan plan;
  std::string error;
  CHECK(inj::ParsePlan("0 false 1.0\n1 true 2.0\n2 false 3.0\n", &plan, &error));
  {
    FakeClock clock;
    FakeSink sink;
    sink.now = &clock.mono;
    sink.offer_ok = false;
    CaptureSink log;
    CHECK(inj::Inject(plan, inj::InjectionOptions{}, &sink, clock.Make(), &log) == inj::kOfferFailed);
    CHECK((sink.calls == std::vector<std::string>{"offer"}));
    CHECK(log.events.size() == 1 && log.events[0] == "error");
  }
  {  // a failed send is logged, the rest still go out
    FakeClock clock;
    FakeSink sink;
    sink.now = &clock.mono;
    sink.fail_at = 2;
    CaptureSink log;
    CHECK(inj::Inject(plan, inj::InjectionOptions{}, &sink, clock.Make(), &log) == inj::kSendFailed);
    CHECK(sink.sent.size() == 3);
    CHECK(log.data_of[2].find("\"ok\":false") != std::string::npos);
    CHECK(log.data_of.back().find("\"sent\":2") != std::string::npos);
  }
  {  // a stop request ends it and the offer
    FakeClock clock;
    clock.stop_after_sleeps = 1;
    FakeSink sink;
    sink.now = &clock.mono;
    CaptureSink log;
    CHECK(inj::Inject(plan, inj::InjectionOptions{}, &sink, clock.Make(), &log) == inj::kStopped);
    CHECK(sink.sent.size() == 1);
    CHECK(sink.calls.back() == "stop_offer");
  }
}

}  // namespace

int main(int argc, char** argv) {
  if (argc == 4 && std::strcmp(argv[1], "--encode") == 0) {
    inj::InjectionPlan plan;
    std::string error;
    if (!inj::ParsePlan(std::string("0 ") + argv[2] + " " + argv[3] + "\n", &plan, &error)) {
      std::printf("error %s\n", error.c_str());
      return 1;
    }
    std::printf("%s\n", inj::HexBytes(plan.requests[0].bytes, 8).c_str());
    return 0;
  }
  TestThePlan();
  if (argc == 2) TestTheDefaultSequence(argv[1]);
  TestTheShellSendsOnScheduleAndLogsBothClocks();
  TestFailures();
  return de4sdv::driver_assistance::actuation::test::Finish("injector_test");
}
