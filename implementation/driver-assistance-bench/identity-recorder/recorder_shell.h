// DE4SDV driver-assistance bench (INC-DRIVING-002): the identity recorder's shell.
//
// The order is the model's (PSR CandidateIdentityRecordingApplication, MAP-DRIVING-DA-CANDIDATE-RECORD) and the
// Launch Manager lane's (type Reporting: the candidate's process starts only after report_running):
//
//   1. resolve and hash every input (record_inputs.h);
//   2. write the record file (candidate_record.h, the record writer);
//   3. offer the record's mw::com event and send it once;
//   4. report running to the Launch Manager;
//   5. re-send the event every 1 s for the whole run (ICD.md), so a subscriber that comes late gets it.
//
// A failure in 1 to 3 ends the process with no report_running: the Launch Manager's ready timeout then expires and
// the candidate never starts. A failed report_running is logged and the recorder keeps publishing: if the Launch
// Manager cannot take the report, the component falls back to type Native (lead answer, B6 item 2) and the record
// says nothing about it, the log does.
//
// No middleware and no clock here: identity_recorder_main.cpp gives the mw::com publisher, the lifecycle client
// and the times; the host's tests give fakes.
#pragma once

#include <cstdint>
#include <functional>
#include <memory>
#include <string>

#include "candidate_record.h"
#include "de4sdv/driver_assistance/payloads.h"
#include "file_system.h"
#include "record_inputs.h"
#include "run_log.h"

namespace de4sdv::driver_assistance::identity {

class RecordPublisher {
 public:
  virtual ~RecordPublisher() = default;
  virtual bool Offer(std::string* error) = 0;
  virtual bool Send(const CandidateRecordEventPayload& payload) = 0;
  virtual void StopOffer() = 0;
};

class LifecycleReporter {
 public:
  virtual ~LifecycleReporter() = default;
  // score_mw_lifecycle_report_running(): true on success.
  virtual bool ReportRunning() = 0;
};

// Defined in lifecycle_reporter_score.cpp (the S-CORE build). off_reason says why when it gives nullptr.
std::unique_ptr<LifecycleReporter> MakeLifecycleReporter(std::string* off_reason);

using RecordFileWriter = std::function<bool(const std::string& path, const std::string& bytes, std::string* error)>;

// Exit statuses of Start(), also the process's.
enum StartStatus : int {
  kStarted = 0,
  kInputsFailed = 3,
  kWriteFailed = 4,
  kPayloadFailed = 5,
  kOfferFailed = 6,
  kSendFailed = 7,
};

class RecorderShell {
 public:
  static constexpr double kRepublishPeriodS = 1.0;  // ICD.md: re-published every 1 s for the whole run

  // lifecycle may be null: not started by the Launch Manager (logged as lifecycle "off" with off_reason).
  RecorderShell(RecorderOptions options, const FileSystem* fs, RecordFileWriter writer, RecordPublisher* publisher,
                LifecycleReporter* lifecycle, std::string off_reason, RecordSink* log);

  int Start(std::int64_t real_ns, std::int64_t mono_ns);
  // Re-sends when the period is due. After a stall, one send and the period again, never a burst.
  void Tick(double now_mono_s);
  void Stop(double now_mono_s);

  const std::string& record_path() const { return record_path_; }
  const std::string& record_sha256() const { return record_sha256_; }
  std::uint64_t published() const { return published_; }
  std::uint64_t send_failed() const { return send_failed_; }
  bool running_reported() const { return running_reported_; }

 private:
  void Log(const std::string& event, const std::string& data);
  int Fail(int status, const std::string& stage, const std::string& reason);
  bool SendOnce(double now_mono_s);

  RecorderOptions options_;
  const FileSystem* fs_;
  RecordFileWriter writer_;
  RecordPublisher* publisher_;
  LifecycleReporter* lifecycle_;
  std::string off_reason_;
  RecordSink* log_;
  std::uint64_t log_seq_ = 0;

  CandidateRecordEventPayload payload_{};
  std::string record_path_;
  std::string record_sha256_;
  bool offered_ = false;
  bool stopped_ = false;
  bool running_reported_ = false;
  double next_due_mono_s_ = 0.0;
  std::uint64_t published_ = 0;
  std::uint64_t send_failed_ = 0;
};

}  // namespace de4sdv::driver_assistance::identity
