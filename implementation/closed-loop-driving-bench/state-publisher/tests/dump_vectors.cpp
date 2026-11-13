// DE4SDV INC-DRIVING-001 slice 10b, S1: writes the publisher's frames as
// test vectors for an independent decoder.
//
//   dump_vectors <out-dir>
//
// For every vector it writes <out-dir>/<name>.bin (the whole PreSerializedData
// frame: 4-byte little-endian length, then the ICD v2 section 3 struct) and
// appends {"name": ..., "intent": {...}} to <out-dir>/expect.jsonl. The intent
// holds only the fields that differ from the ICD type defaults (0, "", []); it
// is written from the payload values this program fed in, not by decoding the
// bytes, so it is a real oracle for tests/decode_vectors.py.
//
// non-finite f32 values are the JSON strings "NaN", "Infinity", "-Infinity";
// a negative zero is "-0". tests/decode_vectors.py maps them back.
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <limits>
#include <string>
#include <string_view>
#include <vector>

#include "de4sdv/driving/payloads.h"
#include "publisher_core.h"

using namespace de4sdv::driving;             // NOLINT
using namespace de4sdv::driving::publisher;  // NOLINT

namespace {

std::string g_dir;
std::string g_expect;  // expect.jsonl, one object per line

// --------------------------------------------------------------- tiny JSON
std::string Quote(std::string_view text) {
  std::string out = "\"";
  for (unsigned char c : text) {
    switch (c) {
      case '"': out += "\\\""; break;
      case '\\': out += "\\\\"; break;
      case '\n': out += "\\n"; break;
      case '\r': out += "\\r"; break;
      case '\t': out += "\\t"; break;
      default:
        if (c < 0x20) {
          char buffer[8];
          std::snprintf(buffer, sizeof buffer, "\\u%04x", static_cast<unsigned>(c));
          out += buffer;
        } else {
          out += static_cast<char>(c);
        }
    }
  }
  return out + "\"";
}

std::string FloatText(float value) {
  if (std::isnan(value)) return "\"NaN\"";
  if (std::isinf(value)) return value > 0 ? "\"Infinity\"" : "\"-Infinity\"";
  if (value == 0.0f && std::signbit(value)) return "\"-0\"";
  if (value == 0.0f) return "0";
  char buffer[40];
  std::snprintf(buffer, sizeof buffer, "%.9g", static_cast<double>(value));
  return buffer;
}

class J {
 public:
  J& U(const char* key, std::uint64_t value) {
    Raw(key, std::to_string(value));
    return *this;
  }
  J& Str(const char* key, std::string_view value) {
    Raw(key, Quote(value));
    return *this;
  }
  J& F(const char* key, float value) {
    Raw(key, FloatText(value));
    return *this;
  }
  J& Arr(const char* key, const float* values, std::size_t count) {
    std::string out = "[";
    for (std::size_t i = 0; i < count; ++i) {
      if (i != 0) out += ',';
      out += FloatText(values[i]);
    }
    out += ']';
    Raw(key, out);
    return *this;
  }
  std::string Done() const { return "{" + body_ + "}"; }

 private:
  void Raw(const char* key, const std::string& value) {
    if (!first_) body_ += ',';
    first_ = false;
    body_ += Quote(key);
    body_ += ':';
    body_ += value;
  }
  std::string body_;
  bool first_ = true;
};

// The fields every message carries: schema_major, kind, sequence, producer and
// both clock splits (schema_minor stays at its 0 default).
void HeaderFields(J& j, std::uint32_t kind, std::uint64_t sequence, std::uint64_t monoS,
                  std::uint64_t monoNs, std::uint64_t realS, std::uint64_t realNs) {
  j.U("schema_major", 2)
      .U("kind", kind)
      .U("sequence", sequence)
      .Str("producer", "statePublisher")
      .U("publish_real_s", realS)
      .U("publish_real_ns", realNs)
      .U("publish_mono_s", monoS)
      .U("publish_mono_ns", monoNs);
}

void Emit(const char* name, const Frame& frame, const std::string& intentJson) {
  const std::string path = g_dir + "/" + name + ".bin";
  std::ofstream out(path, std::ios::binary);
  out.write(reinterpret_cast<const char*>(frame.bytes), frame.size);
  out.close();
  g_expect += std::string{"{\"name\":"} + Quote(name) + ",\"intent\":" + intentJson + "}\n";
  std::printf("VECTOR %-24s message=%5u frame=%5u\n", name, frame.messageBytes, frame.size);
}

// ------------------------------------------------------------- payloads
DrivingPlanPayload MakePlan(std::uint64_t frameIndex, std::uint32_t sampleCount, const char* run,
                            const char* reference, const char* producer) {
  DrivingPlanPayload plan{};
  plan.frameIndex = frameIndex;
  plan.captureTime = static_cast<double>(frameIndex) * kStepSeconds;
  plan.productionTime = 1000.0 + static_cast<double>(frameIndex) * kStepSeconds;
  plan.horizon = 6.4f;
  plan.sampleCount = sampleCount;
  for (std::size_t i = 0; i < kPlanSamples; ++i) {
    plan.samples[i].acceleration = 0.25f * static_cast<float>(i) - 4.0f;
    plan.samples[i].curvature = 0.5f * static_cast<float>(i);
    plan.samples[i].x = 0.75f * static_cast<float>(i);
    plan.samples[i].y = -0.125f * static_cast<float>(i);
    plan.samples[i].heading = 0.0625f * static_cast<float>(i);
  }
  std::snprintf(plan.runRecord, sizeof plan.runRecord, "%s", run);
  std::snprintf(plan.planReference, sizeof plan.planReference, "%s", reference);
  std::snprintf(plan.producer, sizeof plan.producer, "%s", producer);
  return plan;
}

// The intent of a well-formed plan, from the same formulas as MakePlan.
std::string PlanIntent(const float* acceleration, const float* curvature, const float* x,
                       const float* y, std::uint32_t count, std::uint64_t frameIndex,
                       std::uint64_t sequence, const std::string& run,
                       const std::string& reference, const std::string& producer, float horizon,
                       std::uint64_t publishMonoS, std::uint64_t publishMonoNs,
                       std::uint64_t publishRealS, std::uint64_t publishRealNs) {
  const std::uint64_t productionNs = static_cast<std::uint64_t>(
      std::llround((1000.0 + static_cast<double>(frameIndex) * kStepSeconds) * 1e9));
  J j;
  HeaderFields(j, 1, sequence, publishMonoS, publishMonoNs, publishRealS, publishRealNs);
  j.U("plan_frame_index", frameIndex)
      .U("plan_capture_ms", frameIndex * 100ULL)
      .U("plan_production_mono_s", productionNs / 1000000000ULL)
      .U("plan_production_mono_ns", productionNs % 1000000000ULL)
      .Str("plan_reference", reference)
      .Str("run_record", run)
      .Str("plan_producer", producer)
      .U("plan_sample_count", count)
      .F("plan_horizon_s", horizon);
  if (count > 0) {
    j.Arr("plan_acceleration", acceleration, count)
        .Arr("plan_curvature", curvature, count)
        .Arr("plan_x", x, count)
        .Arr("plan_y", y, count);
  }
  return j.Done();
}

// 1000.0 s of CLOCK_MONOTONIC equals 1762700000.0 s of CLOCK_REALTIME here.
constexpr double kMonoAtStart = 1000.0;
constexpr double kRealAtStart = 1762700000.0;

// The deterministic LCG of the random-value vector: state * 1664525 +
// 1013904223, the top 20 bits as a signed value / 1024. Every value is exact in
// binary32, and tests/decode_vectors.py re-derives the sequence.
float RandomFloat(std::uint32_t& state) {
  state = state * 1664525U + 1013904223U;
  std::int32_t value = static_cast<std::int32_t>(state >> 12);
  if ((state & 0x80000000U) != 0U) value -= (1 << 20);
  return static_cast<float>(value) / 1024.0f;
}

}  // namespace

int main(int argc, char* argv[]) {
  if (argc != 2) {
    std::fprintf(stderr, "usage: %s <out-dir>\n", argv[0]);
    return 2;
  }
  g_dir = argv[1];

  float acceleration[kPlanSamples];
  float curvature[kPlanSamples];
  float x[kPlanSamples];
  float y[kPlanSamples];

  // 1. Priming health: schema, kind, both clocks, and every other field at its
  //    type default (empty strings, empty arrays).
  {
    PublisherCore core;
    core.SetRealTimeAtMono(kMonoAtStart, kRealAtStart);
    const std::vector<Frame> frames = core.Tick(kMonoAtStart);
    J j;
    HeaderFields(j, 3, 1, 1000, 0, 1762700000, 0);
    Emit("health_priming", frames[0], j.Done());
  }

  // 2. A full 64-sample plan with the standard strings.
  {
    PublisherCore core;
    core.SetRealTimeAtMono(kMonoAtStart, kRealAtStart);
    const DrivingPlanPayload plan =
        MakePlan(7, 64, "0123456789abcdef", "0123456789abcdef/7", "drivingAgent/inferPlan");
    for (std::size_t i = 0; i < kPlanSamples; ++i) {
      acceleration[i] = plan.samples[i].acceleration;
      curvature[i] = plan.samples[i].curvature;
      x[i] = plan.samples[i].x;
      y[i] = plan.samples[i].y;
    }
    const std::vector<Frame> frames = core.OnPlan(plan, kMonoAtStart);
    Emit("plan_full", frames[1],
         PlanIntent(acceleration, curvature, x, y, 64, 7, 1, "0123456789abcdef",
                    "0123456789abcdef/7", "drivingAgent/inferPlan", 6.4f, 1000, 0, 1762700000, 0));
  }

  // 3. A plan of pseudo-random values: the property test (float32 round-trip).
  {
    PublisherCore core;
    DrivingPlanPayload plan{};
    plan.frameIndex = 3;
    plan.captureTime = 0.3;
    plan.productionTime = 1000.3;
    plan.horizon = -12.5f;
    plan.sampleCount = 64;
    std::uint32_t state = 0x12345678U;
    for (std::size_t i = 0; i < kPlanSamples; ++i) {
      plan.samples[i].acceleration = RandomFloat(state);
      plan.samples[i].curvature = RandomFloat(state);
      plan.samples[i].x = RandomFloat(state);
      plan.samples[i].y = RandomFloat(state);
      acceleration[i] = plan.samples[i].acceleration;
      curvature[i] = plan.samples[i].curvature;
      x[i] = plan.samples[i].x;
      y[i] = plan.samples[i].y;
    }
    std::snprintf(plan.runRecord, sizeof plan.runRecord, "%s", "run-random");
    std::snprintf(plan.planReference, sizeof plan.planReference, "%s", "run-random/3");
    std::snprintf(plan.producer, sizeof plan.producer, "%s", "drivingAgent/inferPlan");
    const std::vector<Frame> frames = core.OnPlan(plan, 0.0);
    Emit("plan_random", frames[1],
         PlanIntent(acceleration, curvature, x, y, 64, 3, 1, "run-random", "run-random/3",
                    "drivingAgent/inferPlan", -12.5f, 0, 0, 0, 0));
  }

  // 4. A short plan: 3 of 64 samples.
  {
    PublisherCore core;
    const DrivingPlanPayload plan = MakePlan(1, 3, "", "", "drivingAgent/inferPlan");
    for (std::size_t i = 0; i < 3; ++i) {
      acceleration[i] = plan.samples[i].acceleration;
      curvature[i] = plan.samples[i].curvature;
      x[i] = plan.samples[i].x;
      y[i] = plan.samples[i].y;
    }
    const std::vector<Frame> frames = core.OnPlan(plan, 2000.0);
    Emit("plan_short", frames[1],
         PlanIntent(acceleration, curvature, x, y, 3, 1, 1, "", "", "drivingAgent/inferPlan", 6.4f,
                    2000, 0, 2000, 0));
  }

  // 5. A plan with zero samples: the four arrays are empty (length 0), the
  //    strings still carry their BOM + NUL.
  {
    PublisherCore core;
    const DrivingPlanPayload plan =
        MakePlan(0, 0, "0123456789abcdef", "0123456789abcdef/0", "drivingAgent/inferPlan");
    const std::vector<Frame> frames = core.OnPlan(plan, 3000.0);
    Emit("plan_empty", frames[1],
         PlanIntent(acceleration, curvature, x, y, 0, 0, 1, "0123456789abcdef",
                    "0123456789abcdef/0", "drivingAgent/inferPlan", 6.4f, 3000, 0, 3000, 0));
  }

  // 6. UTF-8 strings: run record, plan reference and plan producer.
  {
    PublisherCore core;
    const DrivingPlanPayload plan =
        MakePlan(9, 64, "运行记录-甲", "运行记录-甲/9", "驾驶智能体/inferPlan");
    for (std::size_t i = 0; i < kPlanSamples; ++i) {
      acceleration[i] = plan.samples[i].acceleration;
      curvature[i] = plan.samples[i].curvature;
      x[i] = plan.samples[i].x;
      y[i] = plan.samples[i].y;
    }
    const std::vector<Frame> frames = core.OnPlan(plan, 4000.0);
    Emit("plan_unicode", frames[1],
         PlanIntent(acceleration, curvature, x, y, 64, 9, 1, "运行记录-甲", "运行记录-甲/9",
                    "驾驶智能体/inferPlan", 6.4f, 4000, 0, 4000, 0));
  }

  // 7. The longest strings the payload allows (63 characters each).
  {
    PublisherCore core;
    const std::string run(63, 'r');
    const std::string reference(63, 'p');
    const DrivingPlanPayload plan =
        MakePlan(9, 64, run.c_str(), reference.c_str(), "drivingAgent/inferPlan");
    for (std::size_t i = 0; i < kPlanSamples; ++i) {
      acceleration[i] = plan.samples[i].acceleration;
      curvature[i] = plan.samples[i].curvature;
      x[i] = plan.samples[i].x;
      y[i] = plan.samples[i].y;
    }
    const std::vector<Frame> frames = core.OnPlan(plan, 5000.0);
    Emit("plan_max_strings", frames[1],
         PlanIntent(acceleration, curvature, x, y, 64, 9, 1, run, reference,
                    "drivingAgent/inferPlan", 6.4f, 5000, 0, 5000, 0));
  }

  // 8. A vehicle state.
  {
    PublisherCore core;
    EgoMotionSamplePayload sample{};
    sample.speed = 36.5f;
    sample.longitudinalAcceleration = -0.5f;
    sample.lateralAcceleration = 0.25f;
    sample.yawRate = 1.75f;
    sample.captureTime = 12.3;
    const std::vector<Frame> frames = core.OnEgoMotionSample(sample, 1234.5);
    J j;
    HeaderFields(j, 2, 1, 1234, 500000000, 1234, 500000000);
    j.F("speed_kmh", 36.5f)
        .F("longitudinal_acceleration", -0.5f)
        .F("lateral_acceleration", 0.25f)
        .F("yaw_rate_dps", 1.75f)
        .U("sample_capture_ms", 12300)
        .U("sample_receipt_mono_s", 1234)
        .U("sample_receipt_mono_ns", 500000000);
    Emit("vehicle_state", frames[1], j.Done());
  }

  // 9. Non-finite and signed-zero values pass through the f32 field exactly.
  {
    PublisherCore core;
    EgoMotionSamplePayload sample{};
    sample.speed = std::nanf("");
    sample.longitudinalAcceleration = std::numeric_limits<float>::infinity();
    sample.lateralAcceleration = -std::numeric_limits<float>::infinity();
    sample.yawRate = -0.0f;
    sample.captureTime = 12.3;
    const std::vector<Frame> frames = core.OnEgoMotionSample(sample, 1234.5);
    J j;
    HeaderFields(j, 2, 1, 1234, 500000000, 1234, 500000000);
    j.F("speed_kmh", std::nanf(""))
        .F("longitudinal_acceleration", std::numeric_limits<float>::infinity())
        .F("lateral_acceleration", -std::numeric_limits<float>::infinity())
        .F("yaw_rate_dps", -0.0f)
        .U("sample_capture_ms", 12300)
        .U("sample_receipt_mono_s", 1234)
        .U("sample_receipt_mono_ns", 500000000);
    Emit("vehicle_state_specials", frames[1], j.Done());
  }

  // 10. Health when the agent's stop begins, then standstill (cause kept).
  {
    PublisherCore core;
    core.SetRealTimeAtMono(kMonoAtStart, kRealAtStart);
    core.Tick(kMonoAtStart);
    DrivingModePayload stop{};
    stop.mode = Mode::kStopResponse;
    stop.cause = Cause::kPlanStale;
    stop.frameIndex = 40;
    stop.captureTime = 4.0;
    stop.decisionTime = 1000.42;
    const std::vector<Frame> begun = core.OnMode(stop, 1000.43);
    {
      J j;
      HeaderFields(j, 3, 2, 1000, 430000000, 1762700000, 430000000);
      j.U("mode", 2)
          .U("cause", 8)
          .Str("mode_source", "superviseLoop")
          .U("cause_since_mono_s", 1000)
          .U("cause_since_mono_ns", 420000000);
      Emit("health_stop_supervise", begun.back(), j.Done());
    }
    DrivingModePayload standstill = stop;
    standstill.mode = Mode::kStandstill;
    standstill.cause = Cause::kNone;
    standstill.frameIndex = 60;
    standstill.captureTime = 6.0;
    standstill.decisionTime = 1003.0;
    const std::vector<Frame> stopped = core.OnMode(standstill, 1003.01);
    J j;
    HeaderFields(j, 3, 3, 1003, 10000000, 1762700003, 10000000);
    j.U("mode", 3)
        .U("cause", 8)  // the first cause latches
        .Str("mode_source", "superviseLoop")
        .U("cause_since_mono_s", 1000)
        .U("cause_since_mono_ns", 420000000);
    Emit("health_standstill", stopped.back(), j.Done());
  }

  // 11. Health when the adapter's own stop begins: cause_since from stopSinceMono.
  {
    PublisherCore core;
    core.Tick(2000.0);
    ActuationStatePayload state{};
    state.applied = 0;
    state.stopInForce = 1;
    state.cause = Cause::kCommandTimeout;
    state.acceleration = -4.0f;
    state.steeringAngle = 1.5f;
    state.actuationTime = 8.4;
    state.stopSince = 8.3;
    state.stopSinceMono = 2000.02;
    std::snprintf(state.planReference, sizeof state.planReference, "%s", "0123456789abcdef/84");
    const std::vector<Frame> frames = core.OnActuationState(state, 2000.05);
    J j;
    HeaderFields(j, 3, 2, 2000, 50000000, 2000, 50000000);
    j.U("mode", 2)
        .U("cause", 10)
        .Str("mode_source", "actuationAdapter")
        .U("cause_since_mono_s", 2000)
        .U("cause_since_mono_ns", 20000000);
    Emit("health_stop_actuation", frames.back(), j.Done());
  }

  // 12. The refusal health: fields 41-43 plus the kRefused stop. ICD v2
  //     amendment 1 (A5): the detail rides the agent's kRefused mode.
  {
    PublisherCore core;
    core.Tick(0.0);
    DrivingModePayload refused{};
    refused.mode = Mode::kRefused;
    refused.cause = Cause::kCheckpointRefused;
    refused.frameIndex = 0;
    refused.captureTime = 0.0;
    refused.decisionTime = 0.7;
    std::memset(refused.checkpointExpectedSha256, 'a', sizeof(refused.checkpointExpectedSha256));
    std::memset(refused.checkpointActualSha256, 'b', sizeof(refused.checkpointActualSha256));
    std::memcpy(refused.refusalReason, "mismatch", 8);
    const std::vector<Frame> frames = core.OnMode(refused, 0.71);
    J j;
    HeaderFields(j, 3, 2, 0, 710000000, 0, 710000000);
    j.U("mode", 4)
        .U("cause", 11)
        .Str("mode_source", "superviseLoop")
        .U("cause_since_mono_s", 0)
        .U("cause_since_mono_ns", 700000000)
        .Str("checkpoint_expected_sha256", std::string(64, 'a'))
        .Str("checkpoint_actual_sha256", std::string(64, 'b'))
        .Str("refusal_reason", "mismatch");
    Emit("health_refusal", frames.back(), j.Done());
  }

  // 13. Health 35-40 after a plan, a later sample, and a drop.
  {
    PublisherCore core;
    const DrivingPlanPayload plan =
        MakePlan(7, 64, "0123456789abcdef", "0123456789abcdef/7", "drivingAgent/inferPlan");
    core.OnPlan(plan, 1000.0);
    EgoMotionSamplePayload sample{};
    sample.speed = 5.0f;
    sample.captureTime = 1.5;
    core.OnEgoMotionSample(sample, 1000.2);
    core.NoteDownstreamDrop("send_failed");
    const std::vector<Frame> frames = core.Tick(1000.3);
    J j;
    HeaderFields(j, 3, 2, 1000, 300000000, 1000, 300000000);
    j.U("last_plan_frame_index", 7)
        .U("last_plan_capture_ms", 700)
        .U("step_capture_ms", 1500)
        .U("last_plan_production_mono_s", 1000)
        .U("last_plan_production_mono_ns", 700000000)
        .U("dropped_samples", 1);
    Emit("health_capture_fields", frames.back(), j.Done());
  }

  // 14. The second plan of a core: per-kind sequence 2.
  {
    PublisherCore core;
    core.OnPlan(MakePlan(1, 64, "0123456789abcdef", "0123456789abcdef/1",
                         "drivingAgent/inferPlan"),
                0.0);
    const DrivingPlanPayload plan =
        MakePlan(2, 64, "0123456789abcdef", "0123456789abcdef/2", "drivingAgent/inferPlan");
    for (std::size_t i = 0; i < kPlanSamples; ++i) {
      acceleration[i] = plan.samples[i].acceleration;
      curvature[i] = plan.samples[i].curvature;
      x[i] = plan.samples[i].x;
      y[i] = plan.samples[i].y;
    }
    const std::vector<Frame> frames = core.OnPlan(plan, 0.1);
    Emit("plan_sequence_2", frames[0],
         PlanIntent(acceleration, curvature, x, y, 64, 2, 2, "0123456789abcdef",
                    "0123456789abcdef/2", "drivingAgent/inferPlan", 6.4f, 0, 100000000, 0,
                    100000000));
  }

  // 15. The time split carry: .9999999996 s rounds to the next whole second.
  {
    PublisherCore core;
    const std::vector<Frame> frames = core.Tick(5.9999999996);
    J j;
    HeaderFields(j, 3, 1, 6, 0, 6, 0);
    Emit("health_time_carry", frames[0], j.Done());
  }

  std::ofstream expect(g_dir + "/expect.jsonl");
  expect << g_expect;
  expect.close();
  return 0;
}
