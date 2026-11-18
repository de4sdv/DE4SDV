// A driver of the identity recorder's real path without mw::com: the POSIX file system, the input resolution, the
// record and the record writer, as identity_recorder_main.cpp runs them, with a printing publisher and a lifecycle
// client that always succeeds. Test code only.
//
//   record_driver --run-dir <dir> [--ldconfig-dir D] [--system-root D] [--upstream-revision R]
//       prints the event's fields and exits with Start()'s status (test_identity_recorder_record.py);
//   record_driver --serve --run-dir <dir> ...
//       stays up and re-sends every 1 s until SIGTERM, like the recorder under the Launch Manager: the stand-in
//       for bin/identity_recorder in score-path's dry runs. DA_TEST_LDCONFIG_DIR and DA_TEST_SYSTEM_ROOT, when
//       set, replace /etc/ld.so.conf.d and /usr/share/visionpilot, and DA_TEST_SERVE stands for --serve (the fake
//       Launch Manager passes only --run-dir).
#include <atomic>
#include <chrono>
#include <csignal>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <string>
#include <system_error>
#include <thread>

#include "candidate_record.h"
#include "file_system.h"
#include "record_inputs.h"
#include "recorder_shell.h"
#include "run_log.h"

namespace id = de4sdv::driver_assistance::identity;
using de4sdv::driver_assistance::CandidateRecordEventPayload;
using de4sdv::driver_assistance::MonotonicSeconds;
using de4sdv::driver_assistance::NowNs;
using de4sdv::driver_assistance::RunLog;

namespace {

class PrintingPublisher final : public id::RecordPublisher {
 public:
  bool Offer(std::string* /*error*/) override { return true; }
  bool Send(const CandidateRecordEventPayload& p) override {
    std::printf("event recordSha256=%s upstreamRevision=%s diffBytes=%u recordPath=%s\n", p.recordSha256,
                p.upstreamRevision, static_cast<unsigned>(p.diffBytes), p.recordPath);
    std::fflush(stdout);
    return true;
  }
  void StopOffer() override {}
};

class PrintingLifecycle final : public id::LifecycleReporter {
 public:
  bool ReportRunning() override {
    std::printf("report_running\n");
    return true;
  }
};

std::atomic<bool> g_stop{false};
void OnSignal(int /*signal*/) { g_stop.store(true); }

}  // namespace

int main(int argc, char** argv) {
  id::RecorderOptions o;
  bool serve = std::getenv("DA_TEST_SERVE") != nullptr;
  if (const char* d = std::getenv("DA_TEST_LDCONFIG_DIR")) o.ldconfig_dir = d;
  if (const char* d = std::getenv("DA_TEST_SYSTEM_ROOT")) o.system_root = d;
  for (int i = 1; i < argc; ++i) {
    const std::string a = argv[i];
    if (a == "--serve") {
      serve = true;
      continue;
    }
    if (i + 1 >= argc) break;
    const std::string v = argv[++i];
    if (a == "--run-dir") o.run_dir = v;
    if (a == "--ldconfig-dir") o.ldconfig_dir = v;
    if (a == "--system-root") o.system_root = v;
    if (a == "--upstream-revision") o.upstream_revision = v;
  }
  id::ApplyDefaults(&o);
  std::signal(SIGTERM, OnSignal);
  std::signal(SIGINT, OnSignal);
  const std::string log_dir = o.run_dir + "/" + o.host_name;
  std::error_code ignored;
  std::filesystem::create_directories(log_dir, ignored);
  RunLog log(log_dir + "/identityRecorder.jsonl", o.host_name, "identityRecorder");
  id::PosixFileSystem fs;
  PrintingPublisher publisher;
  PrintingLifecycle lifecycle;
  id::RecorderShell shell(o, &fs, id::WriteRecordFile, &publisher, &lifecycle, "", &log);
  const int status = shell.Start(NowNs(CLOCK_REALTIME), NowNs(CLOCK_MONOTONIC));
  if (status != id::kStarted || !serve) {
    shell.Stop(MonotonicSeconds());
    return status;
  }
  while (!g_stop.load()) {
    shell.Tick(MonotonicSeconds());
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
  }
  shell.Stop(MonotonicSeconds());
  return 0;
}
