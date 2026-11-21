// The identity recorder's shell (recorder_shell.h). C++17.
#include "recorder_shell.h"

#include <cstdint>
#include <string>
#include <utility>

#include "sha256.h"

namespace de4sdv::driver_assistance::identity {

namespace {

using ::de4sdv::driver_assistance::JsonNumber;
using ::de4sdv::driver_assistance::JsonString;

std::string Tag(const char* name, const std::string& value) { return "\"" + std::string(name) + "\":" + value; }

}  // namespace

RecorderShell::RecorderShell(RecorderOptions options, const FileSystem* fs, RecordFileWriter writer,
                             RecordPublisher* publisher, LifecycleReporter* lifecycle, std::string off_reason,
                             RecordSink* log)
    : options_(std::move(options)),
      fs_(fs),
      writer_(std::move(writer)),
      publisher_(publisher),
      lifecycle_(lifecycle),
      off_reason_(std::move(off_reason)),
      log_(log) {
  ApplyDefaults(&options_);
}

void RecorderShell::Log(const std::string& event, const std::string& data) {
  if (log_ != nullptr) log_->Write(event, ++log_seq_, data);
}

int RecorderShell::Fail(int status, const std::string& stage, const std::string& reason) {
  Log("error", "{" + Tag("stage", JsonString(stage)) + "," + Tag("reason", JsonString(reason)) + "}");
  return status;
}

int RecorderShell::Start(std::int64_t real_ns, std::int64_t mono_ns) {
  Log("start", "{" + Tag("run_dir", JsonString(options_.run_dir)) + "," +
                   Tag("stage_root", JsonString(options_.stage_root)) + "," +
                   Tag("launch_config", JsonString(options_.launch_config)) + "," +
                   Tag("candidate", JsonString(options_.candidate)) + "}");
  RecordInputs inputs;
  std::string error;
  if (!ResolveInputs(options_, *fs_, &inputs, &error)) return Fail(kInputsFailed, "inputs", error);
  const auto log_files = [this](const char* list, const std::vector<HashedFile>& files) {
    for (const HashedFile& f : files) {
      Log("input", "{" + Tag("list", JsonString(list)) + "," + Tag("role", JsonString(f.role)) + "," +
                       Tag("path", JsonString(f.path)) + "," + Tag("sha256", JsonString(f.sha256)) + "," +
                       Tag("bytes", std::to_string(f.bytes)) + "}");
    }
  };
  log_files("configuration_files", inputs.configuration);
  log_files("network_files", inputs.networks);
  log_files("binaries", inputs.binaries);
  log_files("runtime_libraries", inputs.runtime_libraries);

  record_path_ = JoinPath(JoinPath(options_.run_dir, options_.host_name), kRecordFileName);
  RecordStamp stamp;
  stamp.host = options_.host_name;
  stamp.record_path = record_path_;
  stamp.written_real_ns = real_ns;
  stamp.written_mono_ns = mono_ns;
  const std::string bytes = RecordJson(inputs, options_.candidate, stamp);
  record_sha256_ = Sha256Hex(bytes);
  if (!MakeEventPayload(record_sha256_, inputs.upstream_revision, DiffBytes(inputs), record_path_, &payload_,
                        &error)) {
    return Fail(kPayloadFailed, "payload", error);
  }
  if (!writer_(record_path_, bytes, &error)) return Fail(kWriteFailed, "write", error);
  Log("record", "{" + Tag("path", JsonString(record_path_)) + "," + Tag("sha256", JsonString(record_sha256_)) + "," +
                    Tag("bytes", std::to_string(bytes.size())) + "," +
                    Tag("upstream_revision", JsonString(inputs.upstream_revision)) + "," +
                    Tag("diff_bytes", std::to_string(DiffBytes(inputs))) + "," +
                    Tag("diff_sha256", JsonString(DiffSha256(inputs))) + "}");

  if (!publisher_->Offer(&error)) return Fail(kOfferFailed, "offer", error);
  offered_ = true;
  const double now_s = static_cast<double>(mono_ns) / 1e9;
  Log("offer", "{" + Tag("t_mono_s", JsonNumber(now_s)) + "}");
  if (!SendOnce(now_s)) {
    publisher_->StopOffer();
    offered_ = false;
    return Fail(kSendFailed, "send", "the first send of the record failed");
  }

  if (lifecycle_ == nullptr) {
    Log("lifecycle", "{" + Tag("state", JsonString("off")) + "," + Tag("reason", JsonString(off_reason_)) + "}");
  } else if (lifecycle_->ReportRunning()) {
    running_reported_ = true;
    Log("lifecycle", "{" + Tag("state", JsonString("running_reported")) + "}");
  } else {
    Log("lifecycle", "{" + Tag("state", JsonString("error")) + "," +
                         Tag("reason", JsonString("report_running failed: the component is Native in effect")) + "}");
  }
  return kStarted;
}

bool RecorderShell::SendOnce(double now_mono_s) {
  const bool ok = publisher_->Send(payload_);
  if (ok) {
    ++published_;
  } else {
    ++send_failed_;
  }
  Log("publish", "{" + Tag("ok", ok ? "true" : "false") + "," + Tag("published", std::to_string(published_)) + "," +
                     Tag("t_mono_s", JsonNumber(now_mono_s)) + "}");
  next_due_mono_s_ = now_mono_s + kRepublishPeriodS;
  return ok;
}

void RecorderShell::Tick(double now_mono_s) {
  if (!offered_ || stopped_) return;
  if (now_mono_s + 1e-9 < next_due_mono_s_) return;
  SendOnce(now_mono_s);
}

void RecorderShell::Stop(double now_mono_s) {
  if (stopped_) return;
  stopped_ = true;
  if (offered_) publisher_->StopOffer();
  Log("stop", "{" + Tag("published", std::to_string(published_)) + "," +
                  Tag("send_failed", std::to_string(send_failed_)) + "," + Tag("t_mono_s", JsonNumber(now_mono_s)) +
                  "}");
}

}  // namespace de4sdv::driver_assistance::identity
