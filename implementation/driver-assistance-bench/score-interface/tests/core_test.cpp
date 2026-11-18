// Unit tests of the DE4SDV S-CORE interface's core (core.hpp, stop_signal.hpp, settings.hpp): no upstream header, no
// OpenCV, mw::com and the CARLA client replaced by fakes.
//
// Build: g++ -std=c++17 -Wall -Wextra -Werror -I<module>/include -I<bench>/interfaces/include core_test.cpp
//        <module>/src/core.cpp <module>/src/stop_signal.cpp <module>/src/settings.cpp
// Run:   core_test                 the tests
//        core_test --vectors       one line per vector; test_score_interface.py checks each against Python's zlib
//                                  and struct
#include <signal.h>

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

#include "de4sdv/score_interface/core.hpp"
#include "de4sdv/score_interface/settings.hpp"
#include "de4sdv/score_interface/stop_signal.hpp"
#include "fakes.hpp"

namespace da = de4sdv::driver_assistance;
namespace si = de4sdv::score_interface;

static int failures = 0;
#define EXPECT(cond)                                              \
  do {                                                            \
    if (!(cond)) {                                                \
      std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
      ++failures;                                                 \
    }                                                             \
  } while (0)

static std::uint32_t Bits(float f) {
  std::uint32_t u;
  std::memcpy(&u, &f, 4);
  return u;
}

static void TestLatestSlotKeepsNewestAndCountsDrops() {
  si::LatestSlot<int> slot;
  int out = 0;
  EXPECT(!slot.Take(&out));
  int replaced = 0;
  EXPECT(!slot.Put(1, &replaced));
  EXPECT(slot.Put(2, &replaced));
  EXPECT(replaced == 1);
  EXPECT(slot.Put(3, &replaced));
  EXPECT(replaced == 2);
  EXPECT(slot.Take(&out));
  EXPECT(out == 3);  // the newest
  EXPECT(slot.received() == 3);
  EXPECT(slot.dropped() == 2);  // 1 and 2, each replaced unread
  EXPECT(!slot.Take(&out));     // taken once only
  slot.Put(4);
  EXPECT(slot.Take(&out));
  EXPECT(out == 4);
  EXPECT(slot.dropped() == 2);  // a taken item is no drop
  EXPECT(slot.received() == 4);
}

static void TestBgraToBgr() {
  // 2 x 2 pixels, rows padded to 12 bytes.
  const std::uint8_t src[24] = {1, 2, 3, 255, 4, 5, 6, 255, 0xEE, 0xEE, 0xEE, 0xEE,
                                7, 8, 9, 255, 10, 11, 12, 0, 0xEE, 0xEE, 0xEE, 0xEE};
  si::CameraImageView v;
  v.width = 2;
  v.height = 2;
  v.row_bytes = 12;
  v.bgra = src;
  std::uint8_t dst[12];
  std::memset(dst, 0x55, sizeof dst);
  EXPECT(si::ConvertBgraToBgr(v, dst, sizeof dst));
  const std::uint8_t want[12] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12};
  EXPECT(std::memcmp(dst, want, 12) == 0);

  // Refused, nothing written: too small a destination, rows shorter than 4 * width, no pixels, no size.
  std::uint8_t keep[12];
  std::memset(keep, 0x55, sizeof keep);
  EXPECT(!si::ConvertBgraToBgr(v, keep, 11));
  si::CameraImageView w = v;
  w.row_bytes = 7;
  EXPECT(!si::ConvertBgraToBgr(w, keep, sizeof keep));
  w = v;
  w.bgra = nullptr;
  EXPECT(!si::ConvertBgraToBgr(w, keep, sizeof keep));
  w = v;
  w.width = 0;
  EXPECT(!si::ConvertBgraToBgr(w, keep, sizeof keep));
  bool untouched = true;
  for (std::uint8_t b : keep) untouched = untouched && b == 0x55;
  EXPECT(untouched);
}

static void TestSpeedIsMagnitudeInMetersPerSecond() {
  si::EgoVelocity v;
  v.x = 3.0;
  v.y = -4.0;
  EXPECT(si::SpeedOf(v) == 5.0);
  v.x = 1.0;
  v.y = 2.0;
  v.z = -2.0;
  EXPECT(si::SpeedOf(v) == 3.0);
}

static void TestSteeringSignVectors() {
  // Expected float32 bit patterns computed with Python:
  //   struct.pack('<f', -s * 180 / math.pi) for s = 0.1, -0.05, 0.0, math.pi / 6
  EXPECT(Bits(si::SteeringAngleDegrees(0.1)) == 0xc0b758b4u);    // -5.729578: right in CARLA, negative (right) in VSS
  EXPECT(Bits(si::SteeringAngleDegrees(-0.05)) == 0x403758b4u);  // +2.864789: left
  EXPECT(Bits(si::SteeringAngleDegrees(0.0)) == 0x80000000u);    // -0.0, as the formula gives it
  EXPECT(Bits(si::SteeringAngleDegrees(0.5235987755982988)) == 0xc1f00000u);  // -30.0
}

static void TestCheckValueVectors() {
  // Expected values computed with Python: c = zlib.crc32(struct.pack('<ffdI', a, sa, t, seq)), with
  // sa = float32(-s * 180 / math.pi); the payload is struct.pack('<ffdII', a, sa, t, seq, c).
  da::DrivingCommandEventPayload p = si::MakeDrivingCommand(0.1, -4.0, 12.35, 1u);
  EXPECT(p.acceleration == -4.0f);
  EXPECT(Bits(p.steeringAngle) == 0xc0b758b4u);
  EXPECT(p.issueTime == 12.35);
  EXPECT(p.sequenceCount == 1u);
  EXPECT(p.checkValue == 0x79171f0eu);
  p = si::MakeDrivingCommand(-0.05, -5.5, 0.05, 2u);
  EXPECT(p.checkValue == 0xfc0d4de7u);
  p = si::MakeDrivingCommand(0.0, 0.0, 100.0, 4294967295u);
  EXPECT(p.checkValue == 0x02769f0fu);
}

static void TestRecordGate() {
  fakes::RecordSource source;
  si::CandidateRecordGate gate(&source, nullptr);
  EXPECT(!gate.Open());  // nothing yet

  da::CandidateRecordEventPayload bad = fakes::GoodRecord();
  bad.diffBytes = 0;  // "never 0"
  source.pending.push_back(bad);
  EXPECT(!gate.Open());
  EXPECT(gate.rejected() == 1);

  bad = fakes::GoodRecord();
  bad.recordSha256[10] = 'g';  // not hex
  source.pending.push_back(bad);
  EXPECT(!gate.Open());
  bad = fakes::GoodRecord();
  bad.upstreamRevision[40] = 'x';  // not terminated
  source.pending.push_back(bad);
  EXPECT(!gate.Open());
  bad = fakes::GoodRecord();
  bad.recordSha256[63] = '\0';  // 63 digits
  source.pending.push_back(bad);
  EXPECT(!gate.Open());
  EXPECT(gate.rejected() == 4);

  source.pending.push_back(fakes::GoodRecord());
  EXPECT(gate.Open());
  const int polls = source.polls;
  EXPECT(gate.Open());  // stays open with no further sample
  EXPECT(source.polls == polls);  // and polls no more
}

static void TestNoCommandBeforeRecord() {
  fakes::CommandSink sink;
  fakes::RecordSource source;
  si::CandidateRecordGate gate(&source, nullptr);
  si::PassClock clock;
  std::vector<std::string> log;
  si::DrivingCommandWriter writer(&sink, &gate, &clock, [&](const std::string& l) { log.push_back(l); });
  clock = {true, 1.0, 20};
  EXPECT(!writer.Write(0.0, -1.0));
  EXPECT(!writer.Write(0.0, -1.0));
  EXPECT(sink.sent.empty());
  EXPECT(writer.counters().withheld_before_record == 2);
  source.pending.push_back(fakes::GoodRecord());
  EXPECT(writer.Write(0.0, -1.0));
  EXPECT(sink.sent.size() == 1);
  EXPECT(sink.sent.size() == 1 && sink.sent[0].sequenceCount == 1u);  // withheld commands use no sequence count
}

static void TestSequenceAndCaptureTimePerPass() {
  fakes::CommandSink sink;
  fakes::RecordSource source;
  source.pending.push_back(fakes::GoodRecord());
  si::CandidateRecordGate gate(&source, nullptr);
  si::PassClock clock;
  std::vector<std::string> log;
  si::DrivingCommandWriter writer(&sink, &gate, &clock, [&](const std::string& l) { log.push_back(l); });

  EXPECT(!writer.Write(0.1, -1.0));  // no frame handed on yet: no capture time
  EXPECT(writer.counters().withheld_without_capture_time == 1);
  EXPECT(sink.sent.empty());

  clock = {true, 1.05, 21};
  EXPECT(writer.Write(0.1, -4.0));
  clock = {true, 1.15, 23};
  EXPECT(writer.Write(-0.05, -5.5));
  clock = {true, 1.35, 27};  // a pass after dropped images
  sink.fail_next = true;
  EXPECT(!writer.Write(0.0, 0.0));  // the send fails: the count is used, the adapter sees a loss
  clock = {true, 1.45, 29};
  EXPECT(writer.Write(0.0, 0.5));

  EXPECT(sink.sent.size() == 3);
  if (sink.sent.size() == 3) {
    EXPECT(sink.sent[0].sequenceCount == 1u);
    EXPECT(sink.sent[0].issueTime == 1.05);
    EXPECT(sink.sent[1].sequenceCount == 2u);
    EXPECT(sink.sent[1].issueTime == 1.15);
    EXPECT(sink.sent[2].sequenceCount == 4u);
    EXPECT(sink.sent[2].issueTime == 1.45);
  }
  for (const auto& p : sink.sent) EXPECT(p.checkValue == da::DrivingCommandCheckValue(p));
  EXPECT(writer.counters().sent == 3);
  EXPECT(writer.counters().send_failed == 1);
  // One log line per command handed to the sink, with seq, crc and issue time.
  EXPECT(log.size() == 4);
  EXPECT(log.size() == 4 && log[0].find("\"seq\":1,") != std::string::npos);
  EXPECT(log.size() == 4 && log[0].find("\"issueTime_sim_s\":1.05,") != std::string::npos);
  EXPECT(log.size() == 4 && log[2].find("\"sent\":false") != std::string::npos);
}

static void TestWarningRequestOneEventPerWrite() {
  fakes::WarningSink sink;
  si::PassClock clock;
  si::WarningRequestWriter writer(&sink, &clock, nullptr);
  EXPECT(!writer.Write(true));  // no capture time
  EXPECT(sink.sent.empty());
  EXPECT(writer.counters().not_encodable == 1);
  clock = {true, 12.35, 247};
  EXPECT(writer.Write(true));
  clock = {true, 12.45, 249};
  EXPECT(writer.Write(false));
  EXPECT(sink.sent.size() == 2);
  EXPECT(sink.sizes.size() == 2 && sink.sizes[0] == 8 && sink.sizes[1] == 8);
  std::uint8_t want[8];
  EXPECT(da::EncodeWarningRequestSomeip({true, 12.35}, want));
  EXPECT(sink.sent.size() == 2 && std::memcmp(sink.sent[0].data(), want, 8) == 0);
  EXPECT(da::EncodeWarningRequestSomeip({false, 12.45}, want));
  EXPECT(sink.sent.size() == 2 && std::memcmp(sink.sent[1].data(), want, 8) == 0);
  EXPECT(writer.counters().sent == 2);
  EXPECT(writer.counters().requested == 1);
}

static void TestSettings(const char* dir) {
  const std::string path = std::string(dir) + "/score_interface_test.conf";
  {
    std::ofstream f(path);
    f << "# synthetic\nmw_com.config = /etc/de4sdv/mw_com_config.json\ncarla.host = 10.0.0.2\ncarla.port = 2010\n"
         "carla.hero_role = hero\ncarla.camera_role = front_test\nlog.path = /var/log/de4sdv/x.jsonl\n";
  }
  si::Settings s;
  std::string error;
  EXPECT(si::LoadSettings(path, &s, &error));
  EXPECT(s.mw_com_config == "/etc/de4sdv/mw_com_config.json");
  EXPECT(s.carla.host == "10.0.0.2");
  EXPECT(s.carla.port == 2010);
  EXPECT(s.carla.hero_role == "hero");
  EXPECT(s.carla.camera_role == "front_test");
  EXPECT(s.carla.timeout_s == 10.0);
  EXPECT(s.log_path == "/var/log/de4sdv/x.jsonl");
  {
    std::ofstream f(path);
    f << "mw_com.config = a\ncarla.host = h\ncarla.hero_role = hero\n";  // no camera role
  }
  EXPECT(!si::LoadSettings(path, &s, &error));
  EXPECT(error.find("carla.camera_role") != std::string::npos);
  {
    std::ofstream f(path);
    f << "mw_com.config = a\ncarla.host = h\ncarla.hero_role = hero\ncarla.camera_role = c\ncarla.prot = 1\n";
  }
  EXPECT(!si::LoadSettings(path, &s, &error));  // unknown key
  EXPECT(error.find("carla.prot") != std::string::npos);
  {
    std::ofstream f(path);
    f << "mw_com.config = a\ncarla.host = h\ncarla.hero_role = hero\ncarla.camera_role = c\ncarla.port = 70000\n";
  }
  EXPECT(!si::LoadSettings(path, &s, &error));
  EXPECT(!si::LoadSettings(std::string(dir) + "/missing.conf", &s, &error));
  std::remove(path.c_str());
}

static void TestStopSignal() {
  EXPECT(!si::StopRequested());
  EXPECT(si::InstallStopHandler());
  EXPECT(!si::StopRequested());
  EXPECT(raise(SIGTERM) == 0);  // the process survives: the handler only sets the flag
  EXPECT(si::StopRequested());
}

// The supervision decision of 2026-11-18: one alive notification per completed pass, the first pass also reports
// the process running, nothing after a stop request.
static void TestCycleSupervisionOneAlivePerCycle() {
  fakes::LifecycleClient lc;
  std::vector<std::string> lines;
  si::CycleSupervision sup(&lc, [&lines](const std::string& l) { lines.push_back(l); });
  EXPECT(!sup.running_reported());
  EXPECT(lc.calls.empty());  // nothing before the first completed pass
  sup.CycleCompleted(false);
  EXPECT(sup.running_reported());
  EXPECT((lc.calls == std::vector<std::string>{"running", "alive"}));
  for (int i = 0; i < 9; ++i) sup.CycleCompleted(false);
  EXPECT(lc.Count("running") == 1);
  EXPECT(lc.Count("alive") == 10);
  EXPECT(sup.alive_reported() == 10u);
  // the start of the supervision is logged once, at the first pass
  int starts = 0;
  for (const auto& l : lines) starts += l.find("\"kind\":\"supervision.start\"") != std::string::npos ? 1 : 0;
  EXPECT(starts == 1);
  EXPECT(!lines.empty() && lines.front().find("\"kind\":\"supervision.start\"") != std::string::npos);
}

static void TestCycleSupervisionNoneAfterStop() {
  fakes::LifecycleClient lc;
  std::vector<std::string> lines;
  si::CycleSupervision sup(&lc, [&lines](const std::string& l) { lines.push_back(l); });
  sup.CycleCompleted(false);
  sup.CycleCompleted(false);
  sup.CycleCompleted(true);   // the stop request arrived during this pass
  sup.CycleCompleted(false);  // and stays: never an alive again
  EXPECT(lc.Count("alive") == 2);
  EXPECT(sup.alive_reported() == 2u);
  sup.Stop();
  sup.Stop();  // idempotent
  EXPECT(lc.Count("alive") == 2);
  int stops = 0;
  for (const auto& l : lines) {
    if (l.find("\"kind\":\"supervision.stop\"") != std::string::npos) {
      ++stops;
      EXPECT(l.find("\"alive_reported\":2") != std::string::npos);
    }
  }
  EXPECT(stops == 1);
}

static void TestCycleSupervisionStopBeforeFirstPass() {
  fakes::LifecycleClient lc;
  si::CycleSupervision sup(&lc, nullptr);
  sup.CycleCompleted(true);  // a stop before the first completed pass: the process never reports running
  EXPECT(lc.calls.empty());
  EXPECT(!sup.running_reported());
}

static void TestCycleSupervisionRunningFails() {
  fakes::LifecycleClient lc;
  lc.running_ok = false;
  std::vector<std::string> lines;
  si::CycleSupervision sup(&lc, [&lines](const std::string& l) { lines.push_back(l); });
  sup.CycleCompleted(false);
  EXPECT(!sup.running_reported());
  bool logged = false;
  for (const auto& l : lines) logged |= l.find("\"kind\":\"error.supervision\"") != std::string::npos;
  EXPECT(logged);
  // the alive notifications still go out: the Launch Manager decides, by its ready timeout
  EXPECT(lc.Count("alive") == 1);
}

static void TestCycleSupervisionWithoutClient() {
  si::CycleSupervision sup(nullptr, nullptr);
  sup.CycleCompleted(false);
  sup.Stop();
  EXPECT(sup.alive_reported() == 0u);
  EXPECT(!sup.running_reported());
}

static void PrintVectors() {
  const double steer[] = {0.1, -0.05, 0.0, 0.5235987755982988, -0.0123456789};
  const double accel[] = {-4.0, -5.5, 0.0, 2.5, -3.0000001};
  const double issue[] = {12.35, 0.05, 100.0, 0.0, 3599.95};
  const std::uint32_t seq[] = {1u, 2u, 4294967295u, 3u, 72000u};
  for (int i = 0; i < 5; ++i) {
    const auto p = si::MakeDrivingCommand(steer[i], accel[i], issue[i], seq[i]);
    unsigned char b[sizeof p];
    std::memcpy(b, &p, sizeof p);
    std::printf("CMD %.17g %.17g %.17g %u ", steer[i], accel[i], issue[i], seq[i]);
    for (unsigned char c : b) std::printf("%02x", c);
    std::printf("\n");
  }
  fakes::WarningSink sink;
  si::PassClock clock;
  si::WarningRequestWriter writer(&sink, &clock, nullptr);
  const double t[] = {0.05, 12.35, 3599.95};
  for (int i = 0; i < 3; ++i) {
    clock = {true, t[i], 0};
    if (!writer.Write(i != 1) || sink.sent.empty()) {
      std::printf("WRN not sent\n");
      continue;
    }
    std::printf("WRN %d %.17g ", i != 1 ? 1 : 0, t[i]);
    for (std::uint8_t c : sink.sent.back()) std::printf("%02x", c);
    std::printf("\n");
  }
}

int main(int argc, char** argv) {
  if (argc > 1 && std::strcmp(argv[1], "--vectors") == 0) {
    PrintVectors();
    return 0;
  }
  const char* dir = std::getenv("TMPDIR");
  TestLatestSlotKeepsNewestAndCountsDrops();
  TestBgraToBgr();
  TestSpeedIsMagnitudeInMetersPerSecond();
  TestSteeringSignVectors();
  TestCheckValueVectors();
  TestRecordGate();
  TestNoCommandBeforeRecord();
  TestSequenceAndCaptureTimePerPass();
  TestWarningRequestOneEventPerWrite();
  TestSettings(dir != nullptr ? dir : ".");
  TestCycleSupervisionOneAlivePerCycle();
  TestCycleSupervisionNoneAfterStop();
  TestCycleSupervisionStopBeforeFirstPass();
  TestCycleSupervisionRunningFails();
  TestCycleSupervisionWithoutClient();
  TestStopSignal();
  if (failures != 0) {
    std::printf("core_test: %d failed\n", failures);
    return 1;
  }
  std::printf("core_test: all passed\n");
  return 0;
}
