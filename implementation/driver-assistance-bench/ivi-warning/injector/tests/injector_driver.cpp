// The test publisher's real plan and shell with a sink that writes each payload to a file instead of mw::com:
// the stand-in for bin/warning_injector in the dry runs of inject_warning_requests.sh and p10_1_check.sh. Test code
// only. Takes the main's arguments; DA_TEST_SINK_FILE names the file (one hex line per send); DA_TEST_OFFER_FAIL=1
// makes the offer fail.
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <thread>

#include "injection_plan.h"
#include "injector_shell.h"
#include "run_log.h"

namespace inj = de4sdv::driver_assistance::injector;
using de4sdv::driver_assistance::NowNs;
using de4sdv::driver_assistance::RunLog;

namespace {

class FileSink final : public inj::WarningSink {
 public:
  explicit FileSink(const char* path) : path_(path != nullptr ? path : "") {}
  bool Offer(std::string* error) override {
    if (std::getenv("DA_TEST_OFFER_FAIL") != nullptr) {
      *error = "test: offer refused";
      return false;
    }
    return true;
  }
  bool Send(const std::uint8_t* bytes, std::size_t size) override {
    std::FILE* f = std::fopen(path_.c_str(), "a");
    if (f == nullptr) return false;
    std::fprintf(f, "%s\n", inj::HexBytes(bytes, size).c_str());
    std::fclose(f);
    return true;
  }
  void StopOffer() override {}

 private:
  std::string path_;
};

}  // namespace

int main(int argc, char** argv) {
  std::string sequence, log_path;
  inj::InjectionOptions options;
  for (int i = 1; i + 1 < argc; i += 2) {
    const std::string a = argv[i];
    if (a == "--sequence") sequence = argv[i + 1];
    if (a == "--log") log_path = argv[i + 1];
    if (a == "--lead-in-s") options.lead_in_s = std::atof(argv[i + 1]);
    if (a == "--tail-s") options.tail_s = std::atof(argv[i + 1]);
  }
  if (std::getenv("MW_COM_CONFIG") == nullptr) return 2;
  RunLog log(log_path, "score", "warningInjector");
  std::string text;
  if (std::FILE* f = std::fopen(sequence.c_str(), "rb")) {
    char b[4096];
    std::size_t n = 0;
    while ((n = std::fread(b, 1, sizeof b, f)) > 0) text.append(b, n);
    std::fclose(f);
  }
  inj::InjectionPlan plan;
  std::string error;
  if (!inj::ParsePlan(text, &plan, &error)) return 3;
  FileSink sink(std::getenv("DA_TEST_SINK_FILE"));
  inj::Clocks clocks;
  clocks.mono_ns = [] { return NowNs(CLOCK_MONOTONIC); };
  clocks.real_ns = [] { return NowNs(CLOCK_REALTIME); };
  clocks.sleep_until = [](std::int64_t t) {
    while (NowNs(CLOCK_MONOTONIC) < t) std::this_thread::sleep_for(std::chrono::milliseconds(1));
    return true;
  };
  return inj::Inject(plan, options, &sink, clocks, &log);
}
