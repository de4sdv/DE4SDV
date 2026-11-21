// DE4SDV driver-assistance bench (INC-DRIVING-002): the late subscriber of the candidate record, for P10-1.
//
// The open readiness item of phase 8 (PSR phase8ScoreIntegrationPlaced, brief R2): the candidate's vehicle
// interface subscribes to the record after the identity recorder has published it. This probe does the same on
// purpose: it waits --wait-s after its start (p10_1_check.sh starts it after the recorder has reported running),
// then finds the service, subscribes and waits up to --timeout-s for a sample, and checks it (record_probe.h).
//
//   in  mw::com proxy  de4sdv/driver_assistance/candidate_record, event "candidate_record" (service 7413)
//
// The record event has one subscriber (maxSubscribers 1 in the recorder's manifest), so the probe runs only while
// the candidate's process does not (the path-only run of p10_1_check.sh). It builds against S-CORE Communication
// v0.6.0 in the B2 workspace; the host's tests check it for syntax against the closed-loop bench's mock.
//
// Usage: candidate_record_probe [--wait-s 3] [--timeout-s 10] [--out <verdict.json>]
// MW_COM_CONFIG names its manifest (mw_com_config_candidate_record_probe.json).
// Exit status: 0 a well-formed record whose file matches; 1 none or a bad one; 2 usage or environment.
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <thread>

#include "de4sdv/driver_assistance/payloads.h"
#include "file_system.h"
#include "record_probe.h"
#include "run_log.h"
#include "score/mw/com/runtime.h"
#include "score/mw/com/types.h"

using de4sdv::driver_assistance::CandidateRecordEventPayload;
using de4sdv::driver_assistance::JsonString;
using de4sdv::driver_assistance::NowNs;
namespace identity = de4sdv::driver_assistance::identity;

namespace {

template <typename Trait>
struct CandidateRecordInterface : public Trait::Base {
  using Trait::Base::Base;
  typename Trait::template Event<CandidateRecordEventPayload> candidate_record{*this, "candidate_record"};
};
using CandidateRecordProxy = score::mw::com::AsProxy<CandidateRecordInterface>;

constexpr const char* kCandidateRecordSpecifier = "de4sdv/driver_assistance/candidate_record";

int Report(const std::string& out_path, bool ok, const std::string& reason, const identity::ProbeVerdict& verdict,
           std::int64_t subscribed_real_ns, std::int64_t received_real_ns) {
  const std::string line =
      "{\"check\":\"candidate_record_late_subscriber\",\"ok\":" + std::string(ok ? "true" : "false") +
      ",\"reason\":" + JsonString(reason) + ",\"record_sha256\":" + JsonString(verdict.record_sha256) +
      ",\"record_path\":" + JsonString(verdict.record_path) +
      ",\"subscribed_real_ns\":" + std::to_string(subscribed_real_ns) +
      ",\"received_real_ns\":" + std::to_string(received_real_ns) + "}\n";
  std::fputs(line.c_str(), stdout);
  if (!out_path.empty()) {
    std::FILE* file = std::fopen(out_path.c_str(), "w");
    if (file != nullptr) {
      std::fputs(line.c_str(), file);
      std::fclose(file);
    }
  }
  return ok ? 0 : 1;
}

}  // namespace

int main(int argc, char** argv) {
  double wait_s = 3.0;
  double timeout_s = 10.0;
  std::string out_path;
  for (int i = 1; i < argc; ++i) {
    const std::string argument = argv[i];
    if (i + 1 >= argc) {
      std::fprintf(stderr, "usage: %s [--wait-s S] [--timeout-s S] [--out FILE]\n", argv[0]);
      return 2;
    }
    const std::string value = argv[++i];
    if (argument == "--wait-s") {
      wait_s = std::atof(value.c_str());
    } else if (argument == "--timeout-s") {
      timeout_s = std::atof(value.c_str());
    } else if (argument == "--out") {
      out_path = value;
    } else {
      std::fprintf(stderr, "unknown argument: %s\n", argument.c_str());
      return 2;
    }
  }
  const char* mw_config = std::getenv("MW_COM_CONFIG");
  if (mw_config == nullptr) {
    std::fprintf(stderr, "candidate_record_probe: MW_COM_CONFIG is unset\n");
    return 2;
  }
  identity::ProbeVerdict none;
  std::this_thread::sleep_for(std::chrono::milliseconds(static_cast<long long>(wait_s * 1000.0)));
  score::mw::com::runtime::InitializeRuntime(score::mw::com::runtime::RuntimeConfiguration{std::string(mw_config)});
  auto specifier = score::mw::com::InstanceSpecifier::Create(std::string(kCandidateRecordSpecifier));
  if (!specifier.has_value()) return Report(out_path, false, "bad instance specifier", none, 0, 0);
  const auto deadline = std::chrono::steady_clock::now() +
                        std::chrono::milliseconds(static_cast<long long>(timeout_s * 1000.0));
  auto handles = CandidateRecordProxy::FindService(specifier.value());
  while (std::chrono::steady_clock::now() < deadline &&
         (!handles.has_value() || handles.value().empty())) {
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    handles = CandidateRecordProxy::FindService(specifier.value());
  }
  if (!handles.has_value() || handles.value().empty()) {
    return Report(out_path, false, "candidate-record service not found", none, 0, 0);
  }
  auto proxy_result = CandidateRecordProxy::Create(handles.value().front());
  if (!proxy_result.has_value()) return Report(out_path, false, "proxy create failed", none, 0, 0);
  auto& proxy = proxy_result.value();
  if (!proxy.candidate_record.Subscribe(1).has_value()) return Report(out_path, false, "subscribe failed", none, 0, 0);
  const std::int64_t subscribed_real_ns = NowNs(CLOCK_REALTIME);
  identity::PosixFileSystem fs;
  while (std::chrono::steady_clock::now() < deadline) {
    bool got = false;
    CandidateRecordEventPayload payload{};
    const auto received = proxy.candidate_record.GetNewSamples(
        [&](score::mw::com::SamplePtr<CandidateRecordEventPayload> sample) {
          payload = *sample;
          got = true;
        },
        1);
    if (!received.has_value()) return Report(out_path, false, "GetNewSamples failed", none, subscribed_real_ns, 0);
    if (got) {
      const identity::ProbeVerdict verdict = identity::CheckReceivedRecord(payload, fs);
      return Report(out_path, verdict.ok, verdict.reason, verdict, subscribed_real_ns, NowNs(CLOCK_REALTIME));
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(20));
  }
  return Report(out_path, false, "no sample before the timeout", none, subscribed_real_ns, 0);
}
