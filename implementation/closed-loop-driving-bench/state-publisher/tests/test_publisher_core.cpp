// DE4SDV INC-DRIVING-001 slice 10b, S1: unit tests of the publisher logic.
// Plain g++, no framework: the CHECK macros count and report, the process exit
// code is the verdict. The encoder is checked field-by-field, independently of
// this file, by tests/decode_vectors.py (Python decoder written from the ICD v2
// section 3 table); this file checks the framing, the time splits, the timing
// rules and the per-kind bookkeeping with a simulated clock.
//
// Build and run: tests/run_tests.sh
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "de4sdv/driving/payloads.h"
#include "publisher_core.h"

using namespace de4sdv::driving;              // NOLINT
using namespace de4sdv::driving::publisher;   // NOLINT

namespace {

int g_checks = 0;
int g_failures = 0;
const char* g_test = "";

#define CHECK(condition)                                                      \
  do {                                                                        \
    ++g_checks;                                                               \
    if (!(condition)) {                                                       \
      ++g_failures;                                                           \
      std::printf("FAIL [%s] %s:%d: %s\n", g_test, __FILE__, __LINE__, #condition); \
    }                                                                         \
  } while (0)

#define CHECK_NEAR(actual, expected, tolerance)                               \
  do {                                                                        \
    ++g_checks;                                                               \
    const double a_ = static_cast<double>(actual);                            \
    const double e_ = static_cast<double>(expected);                          \
    if (!(std::fabs(a_ - e_) <= (tolerance))) {                               \
      ++g_failures;                                                           \
      std::printf("FAIL [%s] %s:%d: %s = %.17g, expected %.17g (%s)\n", g_test, \
                  __FILE__, __LINE__, #actual, a_, e_, #expected);            \
    }                                                                         \
  } while (0)

// ------------------------------------------------------------------ fixtures
DrivingPlanPayload MakePlan(std::uint64_t frameIndex) {
  DrivingPlanPayload plan{};
  plan.frameIndex = frameIndex;
  plan.captureTime = static_cast<double>(frameIndex) * kStepSeconds;
  plan.productionTime = 1000.0 + static_cast<double>(frameIndex) * kStepSeconds;
  plan.horizon = 6.4f;
  plan.sampleCount = static_cast<std::uint32_t>(kPlanSamples);
  for (std::size_t i = 0; i < kPlanSamples; ++i) {
    plan.samples[i].acceleration = 0.5f * static_cast<float>(i) - 3.0f;
    plan.samples[i].curvature = 0.001f * static_cast<float>(i);
    plan.samples[i].x = 0.25f * static_cast<float>(i);
    plan.samples[i].y = -0.125f * static_cast<float>(i);
    plan.samples[i].heading = 0.01f * static_cast<float>(i);
  }
  std::snprintf(plan.producer, sizeof plan.producer, "%s", "drivingAgent/inferPlan");
  std::snprintf(plan.runRecord, sizeof plan.runRecord, "%s", "0123456789abcdef");
  std::snprintf(plan.planReference, sizeof plan.planReference, "%s/%llu", "0123456789abcdef",
                static_cast<unsigned long long>(frameIndex));
  return plan;
}

EgoMotionSamplePayload MakeSampleAt(float speed, double captureSeconds) {
  EgoMotionSamplePayload sample{};
  sample.speed = speed;
  sample.longitudinalAcceleration = -0.5f;
  sample.lateralAcceleration = 0.25f;
  sample.yawRate = 1.75f;
  sample.captureTime = captureSeconds;
  return sample;
}

EgoMotionSamplePayload MakeSample(float speed) { return MakeSampleAt(speed, 12.3); }

DrivingModePayload MakeMode(Mode mode, Cause cause, std::uint64_t frameIndex, double decisionTime) {
  DrivingModePayload payload{};
  payload.mode = mode;
  payload.cause = cause;
  payload.frameIndex = frameIndex;
  payload.captureTime = static_cast<double>(frameIndex) * kStepSeconds;
  payload.decisionTime = decisionTime;
  return payload;
}

std::vector<const Frame*> Of(const std::vector<Frame>& frames, Kind kind) {
  std::vector<const Frame*> out;
  for (const Frame& frame : frames) {
    if (frame.kind == kind) out.push_back(&frame);
  }
  return out;
}

std::uint32_t PrefixLength(const Frame& frame) {
  return static_cast<std::uint32_t>(frame.bytes[0]) |
         (static_cast<std::uint32_t>(frame.bytes[1]) << 8U) |
         (static_cast<std::uint32_t>(frame.bytes[2]) << 16U) |
         (static_cast<std::uint32_t>(frame.bytes[3]) << 24U);
}

// Big-endian u32 at a frame offset (the struct starts at byte 4).
std::uint32_t BeU32(const Frame& frame, std::size_t offset) {
  return (static_cast<std::uint32_t>(frame.bytes[offset]) << 24U) |
         (static_cast<std::uint32_t>(frame.bytes[offset + 1]) << 16U) |
         (static_cast<std::uint32_t>(frame.bytes[offset + 2]) << 8U) |
         static_cast<std::uint32_t>(frame.bytes[offset + 3]);
}

bool Contains(const Frame& frame, const std::string& needle) {
  return frame.logDataJson.find(needle) != std::string::npos;
}

bool HasLog(const std::vector<LogRecord>& records, const std::string& event) {
  for (const LogRecord& record : records) {
    if (record.event == event) return true;
  }
  return false;
}

bool LogContains(const std::vector<LogRecord>& records, const std::string& event,
                 const std::string& needle) {
  for (const LogRecord& record : records) {
    if (record.event == event && record.dataJson.find(needle) != std::string::npos) return true;
  }
  return false;
}

// --------------------------------------------------------------------- tests
void TestTimeSplit() {
  g_test = "time_split";
  TimeSplit split = SplitSeconds(0.0);
  CHECK(split.seconds == 0 && split.nanos == 0);
  split = SplitSeconds(-1.5);
  CHECK(split.seconds == 0 && split.nanos == 0);
  split = SplitSeconds(std::nan(""));
  CHECK(split.seconds == 0 && split.nanos == 0);

  split = SplitSeconds(1000.0);
  CHECK(split.seconds == 1000 && split.nanos == 0);
  split = SplitSeconds(1000.43);
  CHECK(split.seconds == 1000 && split.nanos == 430000000);
  split = SplitSeconds(1762700000.5);
  CHECK(split.seconds == 1762700000 && split.nanos == 500000000);

  // The carry: .6 ns past the last nanosecond rounds up into the next second.
  split = SplitSeconds(5.9999999996);
  CHECK(split.seconds == 6 && split.nanos == 0);
  split = SplitSeconds(0.9999999996);
  CHECK(split.seconds == 1 && split.nanos == 0);
  split = SplitSeconds(999.9999999996);
  CHECK(split.seconds == 1000 && split.nanos == 0);
  // ... and the nanosecond part never reaches 1e9.
  split = SplitSeconds(0.9999999994);
  CHECK(split.seconds == 0 && split.nanos == 999999999);

  // Saturation, not wraparound, past 2^32-1 s.
  split = SplitSeconds(5.0e9);
  CHECK(split.seconds == 0xFFFFFFFFU);

  CHECK(SimulationMs(12.3) == 12300);
  CHECK(SimulationMs(0.1) == 100);
  CHECK(SimulationMs(4.9) == 4900);
  CHECK(SimulationMs(0.0) == 0);
  CHECK(SimulationMs(-2.0) == 0);
  CHECK(SimulationMs(std::nan("")) == 0);
}

void TestFrameLayout() {
  g_test = "frame_layout";
  PublisherCore core;
  const std::vector<Frame> frames = core.OnPlan(MakePlan(7), 1000.0);
  // The priming health comes first, then the plan.
  CHECK(frames.size() == 2);
  if (frames.size() != 2) return;
  CHECK(frames[0].kind == Kind::kHealth);
  CHECK(frames[1].kind == Kind::kPlan);
  CHECK(frames[1].port == Port::kPlan);

  const Frame& plan = frames[1];
  CHECK(plan.messageBytes == PrefixLength(plan));
  CHECK(plan.size == plan.messageBytes + 4);
  CHECK(plan.size <= kFrameBytes);
  CHECK(plan.messageBytes <= kMaxMessageBytes);
  CHECK(plan.bytes[2] == 0 && plan.bytes[3] == 0);  // length < 64 KiB, high half zero

  // ICD v2 section 3, big-endian, field order, no struct length field.
  CHECK(BeU32(plan, 4) == 2);   // 1 schema_major
  CHECK(BeU32(plan, 8) == 0);   // 2 schema_minor
  CHECK(BeU32(plan, 12) == 1);  // 3 kind = PLAN
  CHECK(BeU32(plan, 16) == 1);  // 4 sequence
  // 5 producer: a 4-byte byte count covering BOM + bytes + NUL.
  CHECK(BeU32(plan, 20) == 18);  // 14 characters + 4
  CHECK(plan.bytes[24] == 0xEF && plan.bytes[25] == 0xBB && plan.bytes[26] == 0xBF);
  CHECK(std::memcmp(plan.bytes + 27, "statePublisher", 14) == 0);
  CHECK(plan.bytes[41] == 0);
  // 10 plan_frame_index and 11 plan_capture_ms (= frame x 100, ICD section 1).
  CHECK(BeU32(plan, 4 + 54) == 7);
  CHECK(BeU32(plan, 4 + 58) == 700);
  // The health-only fields of a PLAN message are zero (30 mode, 31 cause).
  CHECK(BeU32(plan, 4 + 1226) == 0);
  CHECK(BeU32(plan, 4 + 1230) == 0);

  CHECK(plan.sequence == 1);
  CHECK(core.Sequence(Kind::kPlan) == 1);
  CHECK(Contains(plan, "\"kind\":\"PLAN\""));
  CHECK(Contains(plan, "\"plan_capture_sim_ms\":700"));
  CHECK(Contains(plan, "\"clocks\":{\"publish_mono_ns\":\"monotonic\""));
}

void TestPlanMessageSize() {
  g_test = "plan_size";
  PublisherCore core;
  const std::vector<Frame> frames = core.OnPlan(MakePlan(0), 1.0);
  const std::vector<const Frame*> plans = Of(frames, Kind::kPlan);
  CHECK(plans.size() == 1);
  if (plans.empty()) return;
  std::printf("INFO 64-sample PLAN message = %u bytes, frame = %u bytes, budget %zu\n",
              plans[0]->messageBytes, plans[0]->size, kMaxMessageBytes);
  CHECK(plans[0]->messageBytes <= kMaxMessageBytes);
  // Fixed layout (ICD v2 section 3): 4 u32 header, the four strings, 18
  // scalars, four empty-string fields of 8 bytes, and four 4 + 64*4-byte arrays.
  // 1298 bytes at these string lengths.
  CHECK(plans[0]->messageBytes == 1298);
}

void TestSequencesArePerKind() {
  g_test = "sequences";
  PublisherCore core;
  core.Tick(0.0);  // priming health -> health sequence 1
  for (int i = 0; i < 3; ++i) {
    const std::vector<Frame> plan = core.OnPlan(MakePlan(static_cast<std::uint64_t>(i)), 0.05);
    CHECK(Of(plan, Kind::kPlan).size() == 1);
    const std::vector<Frame> sample = core.OnEgoMotionSample(MakeSample(30.0f), 0.06);
    CHECK(Of(sample, Kind::kVehicleState).size() == 1);
  }
  CHECK(core.Sequence(Kind::kPlan) == 3);
  CHECK(core.Sequence(Kind::kVehicleState) == 3);
  CHECK(core.Sequence(Kind::kHealth) == 1);

  const std::vector<Frame> more = core.OnPlan(MakePlan(9), 0.07);
  CHECK(Of(more, Kind::kPlan)[0]->sequence == 4);
  CHECK(core.Sequence(Kind::kHealth) == 1);  // untouched by plan traffic
}

void TestHealthPeriod() {
  g_test = "health_period";
  PublisherCore core;
  const std::vector<Frame> first = core.Tick(500.0);
  CHECK(first.size() == 1);  // priming health at once
  CHECK(first.size() == 1 && first[0].kind == Kind::kHealth);
  CHECK(first.size() == 1 && first[0].sequence == 1);

  // 100 ms period: nothing before the deadline, one at each deadline.
  CHECK(core.Tick(500.05).empty());
  CHECK(core.Tick(500.099).empty());
  const std::vector<Frame> due = core.Tick(500.1);
  CHECK(due.size() == 1);
  CHECK(core.NextHealthMono() > 500.19 && core.NextHealthMono() < 500.21);

  // Twenty periods of 100 ms, ticked at each deadline: exactly one each.
  PublisherCore clock;
  clock.Tick(1000.0);
  int emitted = 0;
  for (int i = 1; i <= 20; ++i) {
    const std::vector<Frame> frames = clock.Tick(1000.0 + 0.1 * i);
    emitted += static_cast<int>(Of(frames, Kind::kHealth).size());
    for (const Frame* frame : Of(frames, Kind::kHealth)) CHECK(frame->sequence == static_cast<std::uint64_t>(i) + 1U);
  }
  CHECK(emitted == 20);

  // A stall catches up in one publication, not a burst of duplicates.
  const std::vector<Frame> late = clock.Tick(1005.0);
  CHECK(Of(late, Kind::kHealth).size() == 1);
  // The next deadline after 1005.0 (the schedule was at 1002.1 + 0.1 steps).
  CHECK(clock.NextHealthMono() > 1005.0 && clock.NextHealthMono() < 1005.2);
}

void TestHealthIndependentOfInputs() {
  g_test = "health_without_inputs";
  PublisherCore core;
  double now = 10.0;
  int healths = 0;
  for (int i = 0; i < 100; ++i) {  // 1 s of 10 ms polling, no inputs at all
    now += 0.01;
    healths += static_cast<int>(Of(core.Tick(now), Kind::kHealth).size());
  }
  // Priming health at 10.01 plus the nine deadlines 10.11 ... 10.91 inside
  // the window (11.01 falls outside it).
  CHECK(healths == 10);
  CHECK(core.ReportedMode() == Mode::kStarting);
  CHECK(core.ReportedCause() == Cause::kNone);
  CHECK(core.ReportedModeSource().empty());  // no mode event yet
}

void TestHealthWithPlanTraffic() {
  g_test = "health_with_plans";
  PublisherCore core;
  double now = 0.0;
  int healths = 0;
  for (int step = 0; step < 50; ++step) {  // 5 s of 100 ms steps with plan and sample
    now = 0.1 * step;
    healths += static_cast<int>(Of(core.Tick(now), Kind::kHealth).size());
    core.OnPlan(MakePlan(static_cast<std::uint64_t>(step)), now);
    core.OnEgoMotionSample(MakeSampleAt(42.0f, now), now);
  }
  CHECK(healths == 50);  // priming at 0.0 plus one at each of 0.1 ... 4.9
  CHECK(core.LastPlanFrameIndex() == 49);
  CHECK(core.LastPlanCaptureMs() == 4900);
  CHECK(core.StepCaptureMs() == 4900);
  CHECK(core.Sequence(Kind::kPlan) == 50);
  CHECK(core.Sequence(Kind::kVehicleState) == 50);
}

void TestVehicleStateCarriesReceiptTime() {
  g_test = "vehicle_state";
  PublisherCore core;
  const std::vector<Frame> frames = core.OnEgoMotionSample(MakeSample(36.5f), 1234.5);
  const std::vector<const Frame*> states = Of(frames, Kind::kVehicleState);
  CHECK(states.size() == 1);
  if (states.empty()) return;
  CHECK(states[0]->sequence == 1);
  CHECK(BeU32(*states[0], 12) == 2);  // kind = VEHICLE_STATE
  CHECK(BeU32(*states[0], 16) == 1);  // sequence
  // 23 speed_kmh: IEEE-754 binary32 big-endian (36.5 = 0x42120000).
  CHECK(states[0]->bytes[4 + 118] == 0x42);
  CHECK(states[0]->bytes[4 + 119] == 0x12);
  CHECK(states[0]->bytes[4 + 120] == 0x00);
  CHECK(states[0]->bytes[4 + 121] == 0x00);
  // 27 sample_capture_ms = 12300 on the 100 ms grid, 28/29 the receipt split.
  CHECK(BeU32(*states[0], 4 + 134) == 12300);
  CHECK(BeU32(*states[0], 4 + 138) == 1234);
  CHECK(BeU32(*states[0], 4 + 142) == 500000000);
  CHECK(Contains(*states[0], "\"speed_kmh\":36.5"));
  CHECK(Contains(*states[0], "\"sample_receipt_mono_ns\":1234500000000"));
  CHECK(Contains(*states[0], "\"sample_capture_sim_ms\":12300"));
}

void TestStopFromModeIsImmediate() {
  g_test = "stop_from_mode";
  PublisherCore core;
  core.Tick(2000.0);
  core.DrainLog();

  const DrivingModePayload mode = MakeMode(Mode::kStopResponse, Cause::kPlanStale, 40, 2000.42);
  const std::vector<Frame> frames = core.OnMode(mode, 2000.43);
  CHECK(Of(frames, Kind::kHealth).size() == 1);  // same call, no Tick needed
  if (!Of(frames, Kind::kHealth).empty()) {
    const Frame& health = *Of(frames, Kind::kHealth)[0];
    CHECK(health.sequence == 2);  // after the priming health
    CHECK(Contains(health, "\"mode\":\"kStopResponse\""));
    CHECK(Contains(health, "\"cause\":\"kPlanStale\""));
    CHECK(Contains(health, "\"mode_source\":\"superviseLoop\""));
    CHECK(Contains(health, "\"cause_since_mono_ns\":2000420000000"));  // the decision time
    // 30 mode / 31 cause / 32 mode_source on the wire.
    CHECK(BeU32(health, 4 + 146) == 2);  // kStopResponse
    CHECK(BeU32(health, 4 + 150) == 8);  // kPlanStale
    CHECK(BeU32(health, 4 + 154) == 4 + 13);  // "superviseLoop" + 4
  }
  CHECK(core.StopLatched());
  CHECK(core.ReportedMode() == Mode::kStopResponse);
  CHECK(core.ReportedCause() == Cause::kPlanStale);
  CHECK(core.ReportedModeSource() == "superviseLoop");
  CHECK(HasLog(core.DrainLog(), "stop_response.begin"));

  // Latching: the stop survives a later driving mode and keeps reporting.
  const std::vector<Frame> resumed = core.OnMode(MakeMode(Mode::kDriving, Cause::kNone, 41, 2000.52),
                                                2000.53);
  CHECK(resumed.empty());
  CHECK(core.ReportedMode() == Mode::kStopResponse);
  const std::vector<Frame> ticked = core.Tick(2000.53);
  CHECK(Of(ticked, Kind::kHealth).size() == 1);
  CHECK(Contains(*Of(ticked, Kind::kHealth)[0], "\"mode\":\"kStopResponse\""));
  CHECK(Contains(*Of(ticked, Kind::kHealth)[0], "\"cause\":\"kPlanStale\""));
}

void TestStandstillIsLogged() {
  g_test = "standstill";
  PublisherCore core;
  core.Tick(0.0);
  core.OnMode(MakeMode(Mode::kStopResponse, Cause::kCameraMissing, 10, 0.5), 0.51);
  core.DrainLog();
  const std::vector<Frame> frames = core.OnMode(MakeMode(Mode::kStandstill, Cause::kNone, 30, 3.0), 3.01);
  CHECK(Of(frames, Kind::kHealth).size() == 1);  // the transition is published too
  CHECK(core.ReportedMode() == Mode::kStandstill);
  CHECK(core.ReportedCause() == Cause::kCameraMissing);  // the cause of the run survives
  CHECK(HasLog(core.DrainLog(), "stop_response.standstill"));
  // Only once per run.
  core.OnMode(MakeMode(Mode::kStandstill, Cause::kNone, 31, 3.1), 3.11);
  CHECK(!HasLog(core.DrainLog(), "stop_response.standstill"));
}

void TestStopFromActuationState() {
  g_test = "stop_from_actuation";
  PublisherCore core;
  core.Tick(3000.0);
  core.DrainLog();

  ActuationStatePayload state{};
  state.applied = 0;
  state.stopInForce = 1;
  state.cause = Cause::kCommandTimeout;
  state.acceleration = -4.0f;
  state.steeringAngle = 1.5f;
  state.actuationTime = 12.4;
  state.stopSince = 12.3;
  state.stopSinceMono = 3000.02;  // ICD v2: the adapter's own monotonic stamp
  std::snprintf(state.planReference, sizeof state.planReference, "%s", "0123456789abcdef/123");

  const std::vector<Frame> frames = core.OnActuationState(state, 3000.05);
  CHECK(Of(frames, Kind::kHealth).size() == 1);
  if (!Of(frames, Kind::kHealth).empty()) {
    const Frame& health = *Of(frames, Kind::kHealth)[0];
    CHECK(Contains(health, "\"mode\":\"kStopResponse\""));
    CHECK(Contains(health, "\"cause\":\"kCommandTimeout\""));
    CHECK(Contains(health, "\"mode_source\":\"actuationAdapter\""));
    // 33/34 come from stopSinceMono, not from the (later) receipt time.
    CHECK(BeU32(health, 4 + 178) == 3000);  // after "actuationAdapter"
    CHECK(BeU32(health, 4 + 182) == 20000000);
    CHECK(Contains(health, "\"cause_since_mono_ns\":3000020000000"));
  }
  CHECK(core.ReportedModeSource() == "actuationAdapter");
  const std::vector<LogRecord> log = core.DrainLog();
  CHECK(HasLog(log, "stop_response.begin"));
  CHECK(LogContains(log, "stop_response.begin", "\"stop_since\":12.3"));
  CHECK(LogContains(log, "stop_response.begin", "\"stop_since_mono\":3000.02"));
  CHECK(LogContains(log, "stop_response.begin", "\"cause_since_mono_ns\":3000020000000"));

  // A second actuation-state sample does not restart the stop.
  state.cause = Cause::kCameraStale;
  CHECK(core.OnActuationState(state, 3000.15).empty());
  CHECK(core.ReportedCause() == Cause::kCommandTimeout);
}

void TestOversizeIsDropped() {
  g_test = "oversize";
  Options options;
  options.messageCapacityBytes = 800;  // the ICD's 2044 is unreachable for a real plan
  PublisherCore core(options);
  core.OnEgoMotionSample(MakeSample(10.0f), 0.0);  // priming health + one state, both fit
  core.DrainLog();
  CHECK(core.Sequence(Kind::kPlan) == 0);
  CHECK(core.DroppedSamples() == 0);

  const std::vector<Frame> frames = core.OnPlan(MakePlan(1), 0.05);
  CHECK(Of(frames, Kind::kPlan).empty());
  CHECK(core.DroppedSamples() == 1);
  CHECK(core.Sequence(Kind::kPlan) == 0);  // a dropped message consumes no sequence number
  const std::vector<LogRecord> log = core.DrainLog();
  CHECK(HasLog(log, "drop"));
  for (const LogRecord& record : log) {
    if (record.event == "drop") {
      CHECK(record.dataJson.find("\"reason\":\"message_too_large\"") != std::string::npos);
      CHECK(record.dataJson.find("\"kind\":\"PLAN\"") != std::string::npos);
    }
  }

  // The health keeps reporting the drop count (field 40).
  const std::vector<Frame> health = core.Tick(0.1);
  CHECK(Of(health, Kind::kHealth).size() == 1);
  CHECK(Contains(*Of(health, Kind::kHealth)[0], "\"dropped_samples\":1"));
  CHECK(BeU32(*Of(health, Kind::kHealth)[0], 4 + 190) == 1);

  // A downstream failure counts the same way.
  core.NoteDownstreamDrop("allocate_failed");
  CHECK(core.DroppedSamples() == 2);
}

void TestRealTimeOffset() {
  g_test = "real_time_offset";
  PublisherCore core;
  core.SetRealTimeAtMono(1000.0, 1762700000.0);
  CHECK_NEAR(core.RealOffsetSeconds(), 1762699000.0, 1e-6);
  const std::vector<Frame> frames = core.OnEgoMotionSample(MakeSample(1.0f), 1000.5);
  const std::vector<const Frame*> states = Of(frames, Kind::kVehicleState);
  CHECK(states.size() == 1);
  if (states.empty()) return;
  CHECK(Contains(*states[0], "\"publish_mono_ns\":1000500000000"));
  CHECK(Contains(*states[0], "\"publish_real_ns\":1762700000500000000"));
  // 6 publish_real_s / 7 ns / 8 publish_mono_s / 9 ns on the wire.
  CHECK(BeU32(*states[0], 4 + 38) == 1762700000);
  CHECK(BeU32(*states[0], 4 + 42) == 500000000);
  CHECK(BeU32(*states[0], 4 + 46) == 1000);
  CHECK(BeU32(*states[0], 4 + 50) == 500000000);
}

void TestPlanClampingAndShortPlan() {
  g_test = "plan_clamping";
  PublisherCore core;
  DrivingPlanPayload plan = MakePlan(3);
  plan.sampleCount = 128;  // malformed: the arrays carry the 64 samples of the payload
  const std::vector<Frame> frames = core.OnPlan(plan, 1.0);
  CHECK(Of(frames, Kind::kPlan).size() == 1);
  CHECK(Of(frames, Kind::kPlan)[0]->messageBytes <= kMaxMessageBytes);
  // ICD v2 amendment 1 (A4): 17 plan_sample_count is the raw count of the
  // payload, so a malformed plan stays visible; the arrays hold min(count, 64).
  CHECK(Contains(*Of(frames, Kind::kPlan)[0], "\"plan_sample_count\":128"));
  CHECK(BeU32(*Of(frames, Kind::kPlan)[0], 4 + 150) == 128);
  CHECK(BeU32(*Of(frames, Kind::kPlan)[0], 4 + 158) == 64 * 4);  // 19 acceleration: byte length

  DrivingPlanPayload shortPlan = MakePlan(4);
  shortPlan.sampleCount = 0;
  const std::vector<Frame> second = core.OnPlan(shortPlan, 1.1);
  CHECK(Of(second, Kind::kPlan).size() == 1);
  CHECK(Of(second, Kind::kPlan)[0]->messageBytes < Of(frames, Kind::kPlan)[0]->messageBytes);
  // Empty arrays are a 4-byte zero length each, not an omitted field.
  CHECK(BeU32(*Of(second, Kind::kPlan)[0], 4 + 158) == 0);
  CHECK(BeU32(*Of(second, Kind::kPlan)[0], 4 + 162) == 0);
  CHECK(BeU32(*Of(second, Kind::kPlan)[0], 4 + 166) == 0);
  CHECK(BeU32(*Of(second, Kind::kPlan)[0], 4 + 170) == 0);
}

void TestLogJsonPayloads() {
  g_test = "log_json";
  const std::string plan = logjson::Plan(MakePlan(2), 2000.0);
  CHECK(plan.find("\"plan_reference\":\"0123456789abcdef/2\"") != std::string::npos);
  CHECK(plan.find("\"horizon\":6.4") != std::string::npos);
  CHECK(plan.find("\"samples\":[{") != std::string::npos);
  CHECK(plan.find("\"heading\"") != std::string::npos);
  CHECK(plan.find("\"clocks\":{\"capture_time\":\"simulation\"") != std::string::npos);
  CHECK(plan.find("\"receipt_time_mono_ns\":2000000000000") != std::string::npos);

  const std::string mode = logjson::ModeEvent(MakeMode(Mode::kRefused, Cause::kCheckpointRefused, 0, 5.0), 5.01);
  CHECK(mode.find("\"mode\":\"kRefused\"") != std::string::npos);
  CHECK(mode.find("\"cause\":\"kCheckpointRefused\"") != std::string::npos);
  CHECK(mode.find("\"clocks\":{\"capture_time\":\"simulation\"") != std::string::npos);
  CHECK(mode.find("\"decision_mono_ns\"") == std::string::npos);  // payload keeps its name

  ActuationStatePayload state{};
  state.applied = 1;
  state.cause = Cause::kNone;
  state.acceleration = -4.0f;
  state.stopSinceMono = 77.5;
  const std::string actuation = logjson::ActuationState(state, 77.6);
  CHECK(actuation.find("\"applied\":true") != std::string::npos);
  CHECK(actuation.find("\"stop_in_force\":false") != std::string::npos);
  CHECK(actuation.find("\"acceleration\":-4") != std::string::npos);
  CHECK(actuation.find("\"stop_since_mono\":77.5") != std::string::npos);
}

void TestRefusedModeStartsStop() {
  g_test = "refused";
  PublisherCore core;
  core.Tick(0.0);
  const std::vector<Frame> frames =
      core.OnMode(MakeMode(Mode::kRefused, Cause::kCheckpointRefused, 0, 0.7), 0.71);
  CHECK(Of(frames, Kind::kHealth).size() == 1);
  CHECK(core.StopLatched());
  CHECK(core.ReportedMode() == Mode::kRefused);
}

void TestRefusalDetailRidesTheMode() {
  // ICD v2 amendment 1 (A5): the agent's kRefused mode carries the detail, and
  // the immediate stop health already holds fields 41-43.
  g_test = "refusal_from_mode";
  PublisherCore core;
  core.Tick(0.0);
  core.DrainLog();
  DrivingModePayload mode = MakeMode(Mode::kRefused, Cause::kCheckpointRefused, 0, 0.7);
  const std::string expected(64, 'e');
  const std::string actual(64, 'f');
  std::memcpy(mode.checkpointExpectedSha256, expected.data(), 64);   // no NUL: exactly 64
  std::memcpy(mode.checkpointActualSha256, actual.data(), 64);
  std::memcpy(mode.refusalReason, "mismatch", 8);
  const std::vector<Frame> frames = core.OnMode(mode, 0.71);
  const std::vector<const Frame*> healths = Of(frames, Kind::kHealth);
  CHECK(healths.size() == 1);
  if (healths.empty()) return;
  CHECK(Contains(*healths[0], "\"checkpoint_expected_sha256\":\"" + expected + "\""));
  CHECK(Contains(*healths[0], "\"checkpoint_actual_sha256\":\"" + actual + "\""));
  CHECK(Contains(*healths[0], "\"refusal_reason\":\"mismatch\""));
  // The mode's own log record carries the detail too (ICD §6: full payload).
  const std::string logged = logjson::ModeEvent(mode, 0.71);
  CHECK(logged.find("\"checkpoint_expected_sha256\":\"" + expected + "\"") != std::string::npos);
  CHECK(logged.find("\"refusal_reason\":\"mismatch\"") != std::string::npos);
  // A non-refused mode leaves the detail unset.
  PublisherCore other;
  other.Tick(0.0);
  DrivingModePayload driving = MakeMode(Mode::kDriving, Cause::kNone, 3, 0.9);
  std::memcpy(driving.refusalReason, "mismatch", 8);  // ignored outside kRefused
  other.OnMode(driving, 0.91);
  CHECK(!other.RefusalSet());
}

void TestHealthPlanAndStepFields() {
  g_test = "health_plan_fields";
  PublisherCore core;
  core.OnPlan(MakePlan(7), 1000.0);   // capture 0.7 s -> 700 ms, production 1000.7 s
  core.DrainLog();
  const std::vector<Frame> frames = core.Tick(1000.1);
  const std::vector<const Frame*> healths = Of(frames, Kind::kHealth);
  CHECK(healths.size() == 1);
  if (healths.empty()) return;
  const Frame& health = *healths[0];
  // 35 last_plan_frame_index, 36 last_plan_capture_ms, 37 step_capture_ms,
  // 38/39 last_plan_production_mono_s/ns.
  CHECK(BeU32(health, 4 + 170) == 7);
  CHECK(BeU32(health, 4 + 174) == 700);
  CHECK(BeU32(health, 4 + 178) == 700);
  CHECK(BeU32(health, 4 + 190) == 0);        // dropped_samples
  CHECK(BeU32(health, 4 + 182) == 1000);
  CHECK(BeU32(health, 4 + 186) == 700000000);
  CHECK(Contains(health, "\"last_plan_frame_index\":7"));
  CHECK(Contains(health, "\"last_plan_capture_sim_ms\":700"));
  CHECK(Contains(health, "\"step_capture_sim_ms\":700"));
  CHECK(Contains(health, "\"last_plan_production_mono_ns\":1000700000000"));

  // A later ego-motion sample advances the newest step the publisher saw.
  core.OnEgoMotionSample(MakeSampleAt(1.0f, 1.5), 1000.2);
  const std::vector<Frame> next = core.Tick(1000.2);
  CHECK(BeU32(*Of(next, Kind::kHealth)[0], 4 + 178) == 1500);
  // The plan fields do not move with it.
  CHECK(BeU32(*Of(next, Kind::kHealth)[0], 4 + 174) == 700);
}

void TestRefusalFields() {
  g_test = "refusal_fields";
  PublisherCore core;
  core.Tick(0.0);
  core.DrainLog();
  const std::string expected(64, 'a');
  const std::string actual(64, 'b');
  core.SetRefusal(expected, actual, "mismatch");
  CHECK(core.RefusalSet());
  CHECK(core.DrainLog().empty());  // a setter only, no record and no frame

  const std::vector<Frame> frames = core.Tick(0.1);
  const std::vector<const Frame*> healths = Of(frames, Kind::kHealth);
  CHECK(healths.size() == 1);
  if (healths.empty()) return;
  CHECK(Contains(*healths[0], "\"checkpoint_expected_sha256\":\"" + expected + "\""));
  CHECK(Contains(*healths[0], "\"checkpoint_actual_sha256\":\"" + actual + "\""));
  CHECK(Contains(*healths[0], "\"refusal_reason\":\"mismatch\""));

  // Walking the 41/42/43 offsets: three AUTOSAR strings, back to back.
  const Frame& health = *healths[0];
  std::size_t offset = 4 + 194;  // after 40 dropped_samples, at 41
  CHECK(BeU32(health, offset) == 64 + 4);
  CHECK(health.bytes[offset + 4] == 0xEF);
  CHECK(BeU32(health, offset + 72) == 64 + 4);
  CHECK(BeU32(health, offset + 144) == 8 + 4);
  CHECK(health.messageBytes == 194 + 72 + 72 + 16);

  // Over-long detail is cut at the contract length and the cut is recorded.
  core.SetRefusal(std::string(80, 'c'), std::string(70, 'd'), std::string(40, 'r'));
  bool truncated = false;
  for (const LogRecord& record : core.DrainLog()) {
    if (record.event == "error" &&
        record.dataJson.find("\"code\":\"refusal_detail_truncated\"") != std::string::npos) {
      truncated = true;
    }
  }
  CHECK(truncated);
  const std::vector<Frame> again = core.Tick(0.2);
  if (!Of(again, Kind::kHealth).empty()) {
    const Frame& second = *Of(again, Kind::kHealth)[0];
    CHECK(BeU32(second, 4 + 194) == 64 + 4);
    CHECK(BeU32(second, 4 + 194 + 144) == 32 + 4);
  }
}

void TestCaptureMismatchIsLoggedOnce() {
  g_test = "capture_mismatch";
  PublisherCore core;
  core.Tick(0.0);
  core.DrainLog();
  DrivingPlanPayload plan = MakePlan(7);
  plan.captureTime = 12.5;  // says 12500 ms; frame 7 is 700 ms (ICD section 1)
  const std::vector<Frame> frames = core.OnPlan(plan, 1.0);
  CHECK(Of(frames, Kind::kPlan).size() == 1);
  // The frame index wins on the wire.
  CHECK(BeU32(*Of(frames, Kind::kPlan)[0], 4 + 58) == 700);
  const std::vector<LogRecord> log = core.DrainLog();
  CHECK(LogContains(log, "error", "\"code\":\"capture_time_mismatch\""));
  CHECK(LogContains(log, "error", "\"derived_sim_ms\":12500"));

  // Logged once, not per plan.
  core.OnPlan(plan, 1.1);
  CHECK(!HasLog(core.DrainLog(), "error"));
}

void TestFramesNeverExceedCapacity() {
  g_test = "capacity";
  PublisherCore core;
  std::uint64_t now = 0;
  for (int i = 0; i < 200; ++i) {
    std::vector<Frame> frames = core.Tick(0.005 * static_cast<double>(now++));
    const std::vector<Frame> plan = core.OnPlan(MakePlan(static_cast<std::uint64_t>(i)),
                                                0.005 * static_cast<double>(now++));
    const std::vector<Frame> sample = core.OnEgoMotionSample(MakeSample(1.0f),
                                                            0.005 * static_cast<double>(now++));
    frames.insert(frames.end(), plan.begin(), plan.end());
    frames.insert(frames.end(), sample.begin(), sample.end());
    for (const Frame& frame : frames) {
      CHECK(frame.size > 4);  // a dropped message is never handed back as a frame
      CHECK(frame.size <= kFrameBytes);
      CHECK(frame.size == 4 + frame.messageBytes);
      CHECK(PrefixLength(frame) == frame.messageBytes);
      CHECK(frame.sequence >= 1);
    }
  }
  CHECK(core.DroppedSamples() == 0);
}

void TestTinyCapacityDropsEverything() {
  g_test = "tiny_capacity";
  Options options;
  options.messageCapacityBytes = 10;  // below even a health message
  PublisherCore core(options);
  const std::vector<Frame> frames = core.OnEgoMotionSample(MakeSample(1.0f), 0.0);
  CHECK(frames.empty());          // priming health and vehicle state both dropped
  CHECK(core.DroppedSamples() == 2);
  CHECK(core.Sequence(Kind::kHealth) == 0);
  CHECK(core.Sequence(Kind::kVehicleState) == 0);
  CHECK(core.Tick(0.1).empty());
  CHECK(core.DroppedSamples() == 3);
}

void TestAdapterStopKeepsItsProvenance() {
  g_test = "adapter_stop_provenance";
  PublisherCore core;
  core.Tick(4000.0);
  ActuationStatePayload state{};
  state.stopInForce = 1;
  state.cause = Cause::kCommandTimeout;
  state.stopSince = 20.3;
  state.actuationTime = 20.4;
  state.stopSinceMono = 4000.02;
  core.OnActuationState(state, 4000.05);
  core.DrainLog();

  // The agent now reports the same stop a step later: the published stop keeps
  // the source that began it, its cause and its instant.
  const std::vector<Frame> frames =
      core.OnMode(MakeMode(Mode::kStopResponse, Cause::kCameraStale, 20, 4000.06), 4000.07);
  CHECK(frames.empty());
  CHECK(core.ReportedCause() == Cause::kCommandTimeout);
  CHECK(core.ReportedModeSource() == "actuationAdapter");
  CHECK(core.ReportedMode() == Mode::kStopResponse);
  const std::vector<Frame> ticked = core.Tick(4000.15);
  CHECK(Contains(*Of(ticked, Kind::kHealth)[0], "\"mode_source\":\"actuationAdapter\""));
  CHECK(Contains(*Of(ticked, Kind::kHealth)[0], "\"cause_since_mono_ns\":4000020000000"));
}

void TestStandstillAsFirstReportLogsBoth() {
  g_test = "standstill_first";
  PublisherCore core;
  core.Tick(0.0);
  core.DrainLog();
  const std::vector<Frame> frames =
      core.OnMode(MakeMode(Mode::kStandstill, Cause::kMotionStale, 12, 1.34), 1.35);
  CHECK(Of(frames, Kind::kHealth).size() == 1);
  const std::vector<LogRecord> log = core.DrainLog();
  CHECK(HasLog(log, "stop_response.begin"));
  CHECK(HasLog(log, "stop_response.standstill"));
  CHECK(core.ReportedMode() == Mode::kStandstill);
  CHECK(core.ReportedCause() == Cause::kMotionStale);
}

}  // namespace

int main() {
  TestTimeSplit();
  TestFrameLayout();
  TestPlanMessageSize();
  TestSequencesArePerKind();
  TestHealthPeriod();
  TestHealthIndependentOfInputs();
  TestHealthWithPlanTraffic();
  TestVehicleStateCarriesReceiptTime();
  TestStopFromModeIsImmediate();
  TestStandstillIsLogged();
  TestStopFromActuationState();
  TestOversizeIsDropped();
  TestRealTimeOffset();
  TestPlanClampingAndShortPlan();
  TestLogJsonPayloads();
  TestRefusedModeStartsStop();
  TestRefusalDetailRidesTheMode();
  TestHealthPlanAndStepFields();
  TestRefusalFields();
  TestCaptureMismatchIsLoggedOnce();
  TestFramesNeverExceedCapacity();
  TestAdapterStopKeepsItsProvenance();
  TestStandstillAsFirstReportLogsBoth();
  TestTinyCapacityDropsEverything();

  std::printf("%s: %d checks, %d failures\n", g_failures == 0 ? "PASS" : "FAIL", g_checks, g_failures);
  return g_failures == 0 ? 0 : 1;
}
