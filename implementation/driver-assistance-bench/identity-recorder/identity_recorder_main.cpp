// DE4SDV driver-assistance bench (INC-DRIVING-002): the identity recorder, an S-CORE application
// (PSR CandidateIdentityRecordingApplication, MAP-DRIVING-DA-CANDIDATE-RECORD).
//
//   out  mw::com skeleton  de4sdv/driver_assistance/candidate_record, event "candidate_record"
//                          (ICD.md: service 7413, CandidateRecordEventPayload), re-sent every 1 s
//   out  file              <run_dir>/<host-name>/candidate_record.json
//
// The rules and the order are the shell's (recorder_shell.h): hash, write, offer and send, then report running to
// the Launch Manager (type Reporting in launch-manager/config/launch_manager_config.json), then re-send every 1 s
// until SIGTERM. This file only wires: it builds against S-CORE Communication v0.6.0 and Lifecycle v0.10.0 in the
// B2 workspace, and the host's tests check it only for syntax, against the closed-loop bench's local mw::com mock.
//
// Usage:
//   identity_recorder --run-dir <dir> [--stage-root <dir>] [--launch-config <json>] [--candidate vision_pilot]
//                     [--ldconfig-conf <conf>] [--facts-dir <dir>] [--upstream-revision <40 hex>]
//                     [--host-name score]
// MW_COM_CONFIG names this process's mw::com configuration (mw_com_config_identity_recorder.json).
//
// Log: <run_dir>/<host-name>/identityRecorder.jsonl (run_log.h format): start, input, record, offer, publish,
// lifecycle, error, stop.
#include <atomic>
#include <chrono>
#include <csignal>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <memory>
#include <optional>
#include <string>
#include <thread>
#include <utility>

#include "candidate_record.h"
#include "de4sdv/driver_assistance/payloads.h"
#include "file_system.h"
#include "record_inputs.h"
#include "recorder_shell.h"
#include "run_log.h"
#include "score/mw/com/runtime.h"
#include "score/mw/com/types.h"

using de4sdv::driver_assistance::CandidateRecordEventPayload;
using de4sdv::driver_assistance::MonotonicSeconds;
using de4sdv::driver_assistance::NowNs;
using de4sdv::driver_assistance::RunLog;
namespace identity = de4sdv::driver_assistance::identity;

namespace {

template <typename Trait>
struct CandidateRecordInterface : public Trait::Base {
  using Trait::Base::Base;
  typename Trait::template Event<CandidateRecordEventPayload> candidate_record{*this, "candidate_record"};
};
using CandidateRecordSkeleton = score::mw::com::AsSkeleton<CandidateRecordInterface>;

constexpr const char* kCandidateRecordSpecifier = "de4sdv/driver_assistance/candidate_record";

class LolaRecordPublisher final : public identity::RecordPublisher {
 public:
  bool Offer(std::string* error) override {
    auto specifier = score::mw::com::InstanceSpecifier::Create(std::string(kCandidateRecordSpecifier));
    if (!specifier.has_value()) {
      *error = "bad instance specifier";
      return false;
    }
    auto created = CandidateRecordSkeleton::Create(specifier.value());
    if (!created.has_value()) {
      *error = "skeleton create failed";
      return false;
    }
    skeleton_.emplace(std::move(created).value());
    if (!skeleton_->OfferService().has_value()) {
      skeleton_.reset();
      *error = "OfferService failed";
      return false;
    }
    return true;
  }
  bool Send(const CandidateRecordEventPayload& payload) override {
    if (!skeleton_) return false;
    auto slot = skeleton_->candidate_record.Allocate();
    if (!slot.has_value()) return false;
    auto sample = std::move(slot).value();
    *sample = payload;
    return skeleton_->candidate_record.Send(std::move(sample)).has_value();
  }
  void StopOffer() override {
    if (skeleton_) skeleton_->StopOfferService();
    skeleton_.reset();
  }

 private:
  std::optional<CandidateRecordSkeleton> skeleton_;
};

std::atomic<bool> g_stop{false};
void OnSignal(int /*signal*/) { g_stop.store(true); }

void Usage(const char* program) {
  std::fprintf(stderr,
               "usage: %s --run-dir <dir> [--stage-root <dir>] [--launch-config <json>] [--candidate <name>]\n"
               "          [--ldconfig-conf <conf>] [--facts-dir <dir>] [--upstream-revision <hex>] "
               "[--host-name score]\n",
               program);
}

}  // namespace

int main(int argc, char** argv) {
  identity::RecorderOptions options;
  for (int i = 1; i < argc; ++i) {
    const std::string argument = argv[i];
    if (argument == "--help" || argument == "-h") {
      Usage(argv[0]);
      return 0;
    }
    if (i + 1 >= argc) {
      std::fprintf(stderr, "%s needs a value\n", argument.c_str());
      return 1;
    }
    const std::string value = argv[++i];
    if (argument == "--run-dir") {
      options.run_dir = value;
    } else if (argument == "--stage-root") {
      options.stage_root = value;
    } else if (argument == "--launch-config") {
      options.launch_config = value;
    } else if (argument == "--candidate") {
      options.candidate = value;
    } else if (argument == "--ldconfig-conf") {
      options.ldconfig_conf = value;
    } else if (argument == "--facts-dir") {
      options.facts_dir = value;
    } else if (argument == "--upstream-revision") {
      options.upstream_revision = value;
    } else if (argument == "--host-name") {
      options.host_name = value;
    } else {
      std::fprintf(stderr, "unknown argument: %s\n", argument.c_str());
      Usage(argv[0]);
      return 1;
    }
  }
  if (options.run_dir.empty()) {
    Usage(argv[0]);
    return 1;
  }
  const char* mw_config = std::getenv("MW_COM_CONFIG");
  if (mw_config == nullptr) {
    std::fprintf(stderr, "identityRecorder: MW_COM_CONFIG is unset\n");
    return 2;
  }
  std::error_code directory_error;
  std::filesystem::create_directories(std::filesystem::path(options.run_dir) / options.host_name, directory_error);
  const std::string log_path =
      (std::filesystem::path(options.run_dir) / options.host_name / "identityRecorder.jsonl").string();
  RunLog log(log_path, options.host_name, "identityRecorder");
  if (!log.ok()) {
    std::fprintf(stderr, "identityRecorder: cannot write %s\n", log_path.c_str());
    return 8;
  }
  std::signal(SIGINT, OnSignal);
  std::signal(SIGTERM, OnSignal);

  score::mw::com::runtime::InitializeRuntime(score::mw::com::runtime::RuntimeConfiguration{std::string(mw_config)});
  identity::PosixFileSystem fs;
  LolaRecordPublisher publisher;
  std::string off_reason;
  const std::unique_ptr<identity::LifecycleReporter> lifecycle = identity::MakeLifecycleReporter(&off_reason);
  identity::RecorderShell shell(options, &fs, identity::WriteRecordFile, &publisher, lifecycle.get(), off_reason,
                                &log);
  const int status = shell.Start(NowNs(CLOCK_REALTIME), NowNs(CLOCK_MONOTONIC));
  if (status != identity::kStarted) {
    std::fprintf(stderr, "identityRecorder: no record (status %d), see %s\n", status, log_path.c_str());
    return status;
  }
  std::fprintf(stderr, "identityRecorder: record %s sha256 %s\n", shell.record_path().c_str(),
               shell.record_sha256().c_str());
  while (!g_stop.load()) {
    shell.Tick(MonotonicSeconds());
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
  }
  shell.Stop(MonotonicSeconds());
  return 0;
}
