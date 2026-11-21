// Unit tests of the identity recorder's shell (recorder_shell.h) with fakes for the file system, the record
// writer, mw::com and the Launch Manager's lifecycle client.
#include <cstdint>
#include <cstring>
#include <map>
#include <string>
#include <vector>

#include "check.h"
#include "fake_file_system.h"
#include "record_probe.h"
#include "recorder_shell.h"
#include "run_log.h"
#include "sha256.h"

namespace id = de4sdv::driver_assistance::identity;
using de4sdv::driver_assistance::CandidateRecordEventPayload;
using de4sdv::driver_assistance::RecordSink;

namespace {

struct Calls {
  std::vector<std::string> order;
};

class FakePublisher final : public id::RecordPublisher {
 public:
  explicit FakePublisher(Calls* calls) : calls_(calls) {}
  bool Offer(std::string* error) override {
    calls_->order.push_back("offer");
    if (!offer_ok) *error = "fake offer refused";
    return offer_ok;
  }
  bool Send(const CandidateRecordEventPayload& payload) override {
    calls_->order.push_back("send");
    sent.push_back(payload);
    return send_ok;
  }
  void StopOffer() override { calls_->order.push_back("stop_offer"); }
  bool offer_ok = true;
  bool send_ok = true;
  std::vector<CandidateRecordEventPayload> sent;

 private:
  Calls* calls_;
};

class FakeLifecycle final : public id::LifecycleReporter {
 public:
  explicit FakeLifecycle(Calls* calls) : calls_(calls) {}
  bool ReportRunning() override {
    calls_->order.push_back("report_running");
    return ok;
  }
  bool ok = true;

 private:
  Calls* calls_;
};

class CaptureSink final : public RecordSink {
 public:
  void Write(const std::string& event, std::uint64_t /*seq*/, const std::string& data) override {
    events.push_back(event);
    data_by_event[event].push_back(data);
  }
  int Count(const std::string& event) const {
    int n = 0;
    for (const auto& e : events) n += e == event ? 1 : 0;
    return n;
  }
  std::vector<std::string> events;
  std::map<std::string, std::vector<std::string>> data_by_event;
};

struct Harness {
  Harness() : publisher(&calls), lifecycle(&calls) {
    id::test::PutSyntheticStage(&fs);
    options.run_dir = "/stage/run";
  }
  id::RecordFileWriter Writer() {
    return [this](const std::string& path, const std::string& bytes, std::string* error) {
      calls.order.push_back("write");
      if (!write_ok) {
        *error = "fake disk full";
        return false;
      }
      fs.Put(path, bytes);
      written[path] = bytes;
      return true;
    };
  }
  id::test::FakeFileSystem fs;
  id::RecorderOptions options;
  Calls calls;
  FakePublisher publisher;
  FakeLifecycle lifecycle;
  CaptureSink log;
  bool write_ok = true;
  std::map<std::string, std::string> written;
};

const std::int64_t kStartMonoNs = 5000000000LL;  // 5 s

void TestTheOrderIsWriteOfferSendThenReportRunning() {
  Harness h;
  id::RecorderShell shell(h.options, &h.fs, h.Writer(), &h.publisher, &h.lifecycle, "", &h.log);
  CHECK(shell.Start(1, kStartMonoNs) == id::kStarted);
  CHECK((h.calls.order == std::vector<std::string>{"write", "offer", "send", "report_running"}));
  CHECK(shell.running_reported());
  CHECK(shell.record_path() == "/stage/run/score/candidate_record.json");
  // the event names the file that was written, by its SHA-256
  CHECK(h.written.count(shell.record_path()) == 1);
  CHECK(shell.record_sha256() == id::Sha256Hex(h.written[shell.record_path()]));
  CHECK(h.publisher.sent.size() == 1);
  const CandidateRecordEventPayload& p = h.publisher.sent.front();
  CHECK(std::string(p.recordSha256) == shell.record_sha256());
  CHECK(std::string(p.upstreamRevision) == "0123456789abcdef0123456789abcdef01234567");
  CHECK(p.diffBytes == 48u);
  CHECK(std::string(p.recordPath) == shell.record_path());
  // a late subscriber's check accepts it
  CHECK(id::CheckReceivedRecord(p, h.fs).ok);
  // the log
  CHECK(h.log.Count("start") == 1 && h.log.Count("record") == 1 && h.log.Count("offer") == 1);
  CHECK(h.log.Count("publish") == 1 && h.log.Count("lifecycle") == 1);
  CHECK(h.log.data_by_event["lifecycle"].front() == "{\"state\":\"running_reported\"}");
  CHECK(h.log.Count("input") > 10);
  CHECK(h.log.Count("error") == 0);
}

void TestTheRecordIsResentEverySecond() {
  Harness h;
  id::RecorderShell shell(h.options, &h.fs, h.Writer(), &h.publisher, &h.lifecycle, "", &h.log);
  CHECK(shell.Start(1, kStartMonoNs) == id::kStarted);
  shell.Tick(5.5);
  CHECK(h.publisher.sent.size() == 1);
  shell.Tick(5.999);
  CHECK(h.publisher.sent.size() == 1);
  shell.Tick(6.0);
  CHECK(h.publisher.sent.size() == 2);
  shell.Tick(6.5);
  CHECK(h.publisher.sent.size() == 2);
  shell.Tick(7.0);
  CHECK(h.publisher.sent.size() == 3);
  shell.Tick(19.3);  // a stall: one send, no burst
  CHECK(h.publisher.sent.size() == 4);
  shell.Tick(19.4);
  CHECK(h.publisher.sent.size() == 4);
  shell.Tick(20.3);
  CHECK(h.publisher.sent.size() == 5);
  CHECK(shell.published() == 5);
  // every send carries the same record
  for (const auto& p : h.publisher.sent) CHECK(std::string(p.recordSha256) == shell.record_sha256());
  shell.Stop(21.0);
  shell.Tick(30.0);
  CHECK(h.publisher.sent.size() == 5);  // nothing after the stop
  CHECK(h.calls.order.back() == "stop_offer");
  CHECK(h.log.Count("stop") == 1);
  shell.Stop(22.0);
  CHECK(h.log.Count("stop") == 1);
}

void TestNoReportRunningWithoutARecord() {
  {  // an input missing
    Harness h;
    h.fs.Remove("/stage/vision_pilot/config/H.yaml");
    id::RecorderShell shell(h.options, &h.fs, h.Writer(), &h.publisher, &h.lifecycle, "", &h.log);
    CHECK(shell.Start(1, kStartMonoNs) == id::kInputsFailed);
    CHECK(h.calls.order.empty());
    CHECK(h.log.Count("error") == 1);
  }
  {  // the write fails
    Harness h;
    h.write_ok = false;
    id::RecorderShell shell(h.options, &h.fs, h.Writer(), &h.publisher, &h.lifecycle, "", &h.log);
    CHECK(shell.Start(1, kStartMonoNs) == id::kWriteFailed);
    CHECK((h.calls.order == std::vector<std::string>{"write"}));
  }
  {  // the offer fails
    Harness h;
    h.publisher.offer_ok = false;
    id::RecorderShell shell(h.options, &h.fs, h.Writer(), &h.publisher, &h.lifecycle, "", &h.log);
    CHECK(shell.Start(1, kStartMonoNs) == id::kOfferFailed);
    CHECK((h.calls.order == std::vector<std::string>{"write", "offer"}));
    shell.Tick(100.0);
    CHECK(h.publisher.sent.empty());
  }
  {  // the first send fails
    Harness h;
    h.publisher.send_ok = false;
    id::RecorderShell shell(h.options, &h.fs, h.Writer(), &h.publisher, &h.lifecycle, "", &h.log);
    CHECK(shell.Start(1, kStartMonoNs) == id::kSendFailed);
    CHECK((h.calls.order == std::vector<std::string>{"write", "offer", "send", "stop_offer"}));
  }
  {  // a path too long for the event: no file either
    Harness h;
    h.options.run_dir = "/stage/" + std::string(240, 'r');
    h.options.stage_root = "/stage";
    id::RecorderShell shell(h.options, &h.fs, h.Writer(), &h.publisher, &h.lifecycle, "", &h.log);
    CHECK(shell.Start(1, kStartMonoNs) == id::kPayloadFailed);
    CHECK(h.calls.order.empty());
  }
}

void TestAFailedReportIsLoggedAndThePublishingGoesOn() {
  Harness h;
  h.lifecycle.ok = false;
  id::RecorderShell shell(h.options, &h.fs, h.Writer(), &h.publisher, &h.lifecycle, "", &h.log);
  CHECK(shell.Start(1, kStartMonoNs) == id::kStarted);
  CHECK(!shell.running_reported());
  CHECK(h.log.data_by_event["lifecycle"].front().find("\"state\":\"error\"") != std::string::npos);
  shell.Tick(6.0);
  CHECK(h.publisher.sent.size() == 2);
}

void TestWithoutALifecycleClient() {
  Harness h;
  id::RecorderShell shell(h.options, &h.fs, h.Writer(), &h.publisher, nullptr, "not under the Launch Manager",
                          &h.log);
  CHECK(shell.Start(1, kStartMonoNs) == id::kStarted);
  CHECK((h.calls.order == std::vector<std::string>{"write", "offer", "send"}));
  CHECK(h.log.data_by_event["lifecycle"].front() ==
        "{\"state\":\"off\",\"reason\":\"not under the Launch Manager\"}");
}

void TestTheLateSubscribersCheck() {
  Harness h;
  id::RecorderShell shell(h.options, &h.fs, h.Writer(), &h.publisher, &h.lifecycle, "", &h.log);
  CHECK(shell.Start(1, kStartMonoNs) == id::kStarted);
  const CandidateRecordEventPayload good = h.publisher.sent.front();
  CHECK(id::CheckReceivedRecord(good, h.fs).ok);
  {
    CandidateRecordEventPayload p = good;
    p.recordSha256[0] = p.recordSha256[0] == '0' ? '1' : '0';
    CHECK(!id::CheckReceivedRecord(p, h.fs).ok);
  }
  {
    CandidateRecordEventPayload p = good;
    p.diffBytes += 1;
    CHECK(!id::CheckReceivedRecord(p, h.fs).ok);
  }
  {
    CandidateRecordEventPayload p = good;
    p.diffBytes = 0;
    CHECK(!id::CheckReceivedRecord(p, h.fs).ok);
  }
  {
    CandidateRecordEventPayload p = good;
    std::memset(p.recordPath, 'x', sizeof p.recordPath);
    const id::ProbeVerdict v = id::CheckReceivedRecord(p, h.fs);
    CHECK(!v.ok && v.reason.find("terminator") != std::string::npos);
  }
  {  // the file changed after the event
    id::test::FakeFileSystem changed = h.fs;
    changed.Put(shell.record_path(), h.written[shell.record_path()] + " ");
    CHECK(!id::CheckReceivedRecord(good, changed).ok);
  }
  {  // the file is gone
    id::test::FakeFileSystem gone = h.fs;
    gone.Remove(shell.record_path());
    CHECK(!id::CheckReceivedRecord(good, gone).ok);
  }
}

}  // namespace

int main() {
  TestTheOrderIsWriteOfferSendThenReportRunning();
  TestTheRecordIsResentEverySecond();
  TestNoReportRunningWithoutARecord();
  TestAFailedReportIsLoggedAndThePublishingGoesOn();
  TestWithoutALifecycleClient();
  TestTheLateSubscribersCheck();
  return de4sdv::driver_assistance::actuation::test::Finish("recorder_shell_test");
}
