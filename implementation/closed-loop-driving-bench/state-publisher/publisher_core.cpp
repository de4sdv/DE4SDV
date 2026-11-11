// DE4SDV INC-DRIVING-001 slice 10b, S1: the operational-state publisher's
// logic. See publisher_core.h for the contract and ../../interfaces/ICD.md for
// the message (section 3) and the logging rules (section 6).
#include "publisher_core.h"

#include <algorithm>
#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <utility>

namespace de4sdv::driving::publisher {
namespace {

// ------------------------------------------------------------- small helpers
std::uint32_t FloatBits(float v) {
  std::uint32_t bits = 0;
  std::memcpy(&bits, &v, sizeof bits);
  return bits;
}

// A fixed char array of the payloads is NUL-terminated and truncated; read at
// most `capacity` bytes and stop at the first NUL.
std::string_view SafeString(const char* text, std::size_t capacity) {
  std::size_t length = 0;
  while (length < capacity && text[length] != '\0') ++length;
  return std::string_view{text, length};
}

std::string Format(const char* format, ...) {
  char buffer[512];
  va_list args;
  va_start(args, format);
  const int written = std::vsnprintf(buffer, sizeof buffer, format, args);
  va_end(args);
  if (written < 0) return std::string{};
  return std::string{buffer, static_cast<std::size_t>(std::min<int>(written, sizeof buffer - 1))};
}

// JSON has no NaN or infinity.
std::string JsonFloat(float v) {
  if (!std::isfinite(v)) return "null";
  return Format("%.9g", static_cast<double>(v));
}

std::string JsonDouble(double v) {
  if (!std::isfinite(v)) return "null";
  return Format("%.17g", v);
}

void AppendEscaped(std::string& out, std::string_view text) {
  out += '"';
  for (unsigned char c : text) {
    switch (c) {
      case '"': out += "\\\""; break;
      case '\\': out += "\\\\"; break;
      case '\n': out += "\\n"; break;
      case '\r': out += "\\r"; break;
      case '\t': out += "\\t"; break;
      default:
        if (c < 0x20) {
          out += Format("\\u%04x", static_cast<unsigned>(c));
        } else {
          out += static_cast<char>(c);  // UTF-8 passes through unchanged
        }
    }
  }
  out += '"';
}

// Builds one JSON object; keys are written in call order.
class JsonObj {
 public:
  JsonObj& Str(const char* key, std::string_view value) {
    Key(key);
    AppendEscaped(out_, value);
    return *this;
  }
  JsonObj& F32(const char* key, float value) {
    Key(key);
    out_ += JsonFloat(value);
    return *this;
  }
  JsonObj& Num(const char* key, double value) {
    Key(key);
    out_ += JsonDouble(value);
    return *this;
  }
  JsonObj& U64(const char* key, std::uint64_t value) {
    Key(key);
    out_ += std::to_string(value);
    return *this;
  }
  JsonObj& I64(const char* key, std::int64_t value) {
    Key(key);
    out_ += std::to_string(value);
    return *this;
  }
  JsonObj& Bool(const char* key, bool value) {
    Key(key);
    out_ += value ? "true" : "false";
    return *this;
  }
  JsonObj& Raw(const char* key, const std::string& json) {
    Key(key);
    out_ += json;
    return *this;
  }
  std::string Build() const { return "{" + out_ + "}"; }

 private:
  void Key(const char* key) {
    if (!first_) out_ += ',';
    first_ = false;
    AppendEscaped(out_, key);
    out_ += ':';
  }

  std::string out_;
  bool first_ = true;
};

std::string JsonFloatArray(const float* values, std::size_t count) {
  std::string out = "[";
  for (std::size_t i = 0; i < count; ++i) {
    if (i != 0) out += ',';
    out += JsonFloat(values[i]);
  }
  out += ']';
  return out;
}

// The two arrays must have the same length: a mismatch is a compile error, not
// an out-of-bounds read at run time.
template <std::size_t N>
std::string ClocksMap(const char* const (&keys)[N], const char* const (&clocks)[N]) {
  static_assert(N > 0, "a clocks map needs at least one entry");
  JsonObj object;
  for (std::size_t i = 0; i < N; ++i) object.Str(keys[i], clocks[i]);
  return object.Build();
}

// Rounded nanoseconds of a host-clock instant, the one rounding rule of the
// wire format; also the number the JSONL log carries as `_mono_ns`/`_real_ns`.
std::int64_t TotalNanos(double seconds) {
  if (!std::isfinite(seconds) || seconds <= 0.0) return 0;
  // llround(x * 1e9) must stay inside int64: 2^32-1 s is 4.29e18 ns.
  if (seconds >= 4294967295.0) return 4294967295999999999LL;
  return static_cast<std::int64_t>(std::llround(seconds * 1e9));
}

std::uint32_t ClampU32(std::uint64_t value) {
  return value > 0xFFFFFFFFULL ? 0xFFFFFFFFU : static_cast<std::uint32_t>(value);
}

// ---------------------------------------------------------------- the encoder
// ICD section 3: the DrivingOperationalState as a SOME/IP struct, fields in
// table order, no struct length field, big-endian. u32 is UINT32, f32 is
// IEEE-754 binary32, str is AUTOSAR UTF-8 (4-byte BE byte count covering BOM +
// bytes + NUL, then EF BB BF, the bytes, 00), f32[] is a 4-byte BE byte count
// then the elements. Every field is always written: the layout is fixed.
class StructEncoder {
 public:
  StructEncoder(std::uint8_t* buffer, std::size_t capacity)
      : buffer_(buffer), capacity_(capacity) {}

  bool ok() const { return ok_; }
  std::size_t size() const { return size_; }

  void U32(std::uint32_t value) {
    const std::uint8_t bytes[4] = {
        static_cast<std::uint8_t>((value >> 24U) & 0xFFU),
        static_cast<std::uint8_t>((value >> 16U) & 0xFFU),
        static_cast<std::uint8_t>((value >> 8U) & 0xFFU),
        static_cast<std::uint8_t>(value & 0xFFU)};
    Put(bytes, sizeof bytes);
  }

  void F32(float value) { U32(FloatBits(value)); }

  void Str(std::string_view text) {
    // Length covers the BOM (3), the bytes and the terminating NUL: n + 4.
    U32(static_cast<std::uint32_t>(text.size() + 4U));
    const std::uint8_t bom[3] = {0xEFU, 0xBBU, 0xBFU};
    Put(bom, sizeof bom);
    Put(reinterpret_cast<const std::uint8_t*>(text.data()), text.size());
    const std::uint8_t nul = 0;
    Put(&nul, 1);
  }

  void F32Array(const float* values, std::size_t count) {
    U32(static_cast<std::uint32_t>(count * sizeof(float)));  // length in bytes
    for (std::size_t i = 0; i < count; ++i) F32(values[i]);
  }

 private:
  void Put(const std::uint8_t* data, std::size_t count) {
    if (!ok_) return;
    if (size_ + count > capacity_) {
      ok_ = false;
      return;
    }
    std::memcpy(buffer_ + size_, data, count);
    size_ += count;
  }

  std::uint8_t* buffer_;
  std::size_t capacity_;
  std::size_t size_ = 0;
  bool ok_ = true;
};

bool IsStopMode(Mode mode) {
  return mode == Mode::kStopResponse || mode == Mode::kStandstill || mode == Mode::kRefused;
}

}  // namespace

// -------------------------------------------------------------------- times
TimeSplit SplitNanos(std::int64_t totalNanos) {
  TimeSplit out;
  if (totalNanos <= 0) return out;
  if (totalNanos >= 4294967296000000000LL) {  // 2^32 s in ns
    out.seconds = 0xFFFFFFFFU;
    out.nanos = 999999999U;
    return out;
  }
  out.seconds = static_cast<std::uint32_t>(totalNanos / 1000000000LL);
  out.nanos = static_cast<std::uint32_t>(totalNanos % 1000000000LL);
  return out;
}

TimeSplit SplitSeconds(double seconds) { return SplitNanos(TotalNanos(seconds)); }

std::uint32_t SimulationMs(double seconds) {
  if (!std::isfinite(seconds) || seconds <= 0.0) return 0;
  const double ms = std::llround(seconds * 1000.0);
  if (ms <= 0.0) return 0;
  if (ms >= 4294967295.0) return 0xFFFFFFFFU;
  return static_cast<std::uint32_t>(ms);
}

// -------------------------------------------------------------------- names
const char* KindName(Kind kind) {
  switch (kind) {
    case Kind::kPlan: return "PLAN";
    case Kind::kVehicleState: return "VEHICLE_STATE";
    case Kind::kHealth: return "HEALTH";
    case Kind::kUnspecified: break;
  }
  return "KIND_UNSPECIFIED";
}

const char* ModeName(Mode mode) {
  switch (mode) {
    case Mode::kStarting: return "kStarting";
    case Mode::kDriving: return "kDriving";
    case Mode::kStopResponse: return "kStopResponse";
    case Mode::kStandstill: return "kStandstill";
    case Mode::kRefused: return "kRefused";
  }
  return "kUnknown";
}

const char* CauseName(Cause cause) {
  switch (cause) {
    case Cause::kNone: return "kNone";
    case Cause::kCameraMissing: return "kCameraMissing";
    case Cause::kCameraInvalid: return "kCameraInvalid";
    case Cause::kCameraStale: return "kCameraStale";
    case Cause::kMotionInvalid: return "kMotionInvalid";
    case Cause::kMotionStale: return "kMotionStale";
    case Cause::kRouteStale: return "kRouteStale";
    case Cause::kRouteEmpty: return "kRouteEmpty";
    case Cause::kPlanStale: return "kPlanStale";
    case Cause::kPlanInvalid: return "kPlanInvalid";
    case Cause::kCommandTimeout: return "kCommandTimeout";
    case Cause::kCheckpointRefused: return "kCheckpointRefused";
    case Cause::kRunEnd: return "kRunEnd";
  }
  return "kUnknown";
}

const char* PortName(Port port) {
  switch (port) {
    case Port::kPlan: return "plan";
    case Port::kVehicleState: return "vehicle_state";
    case Port::kHealth: return "health";
  }
  return "unknown";
}

// ------------------------------------------------------------ log payloads
namespace logjson {

std::string Plan(const DrivingPlanPayload& plan, double receiptMono) {
  JsonObj object;
  object.U64("frame_index", plan.frameIndex)
      .Num("capture_time", plan.captureTime)
      .Num("production_time", plan.productionTime)
      .F32("horizon", plan.horizon)
      .U64("sample_count", plan.sampleCount)
      .Str("producer", SafeString(plan.producer, kIdLength))
      .Str("run_record", SafeString(plan.runRecord, kIdLength))
      .Str("plan_reference", SafeString(plan.planReference, kIdLength));

  const std::size_t count = std::min<std::size_t>(plan.sampleCount, kPlanSamples);
  std::string samples = "[";
  for (std::size_t i = 0; i < count; ++i) {
    if (i != 0) samples += ',';
    JsonObj sample;
    sample.F32("acceleration", plan.samples[i].acceleration)
        .F32("curvature", plan.samples[i].curvature)
        .F32("x", plan.samples[i].x)
        .F32("y", plan.samples[i].y)
        .F32("heading", plan.samples[i].heading);
    samples += sample.Build();
  }
  samples += ']';
  object.Raw("samples", samples);
  static const char* const kKeys[] = {"capture_time", "production_time", "receipt_time_mono_ns"};
  static const char* const kClocks[] = {"simulation", "monotonic", "monotonic"};
  object.Raw("clocks", ClocksMap(kKeys, kClocks));
  object.I64("receipt_time_mono_ns", TotalNanos(receiptMono));
  return object.Build();
}

std::string EgoMotionSample(const EgoMotionSamplePayload& sample, double receiptMono) {
  JsonObj object;
  object.F32("speed_kmh", sample.speed)
      .F32("longitudinal_acceleration", sample.longitudinalAcceleration)
      .F32("lateral_acceleration", sample.lateralAcceleration)
      .F32("yaw_rate_dps", sample.yawRate)
      .Num("capture_time", sample.captureTime);
  static const char* const kKeys[] = {"capture_time", "receipt_time_mono_ns"};
  static const char* const kClocks[] = {"simulation", "monotonic"};
  object.Raw("clocks", ClocksMap(kKeys, kClocks));
  object.I64("receipt_time_mono_ns", TotalNanos(receiptMono));
  return object.Build();
}

std::string ModeEvent(const DrivingModePayload& mode, double receiptMono) {
  JsonObj object;
  object.Str("mode", ModeName(mode.mode))
      .Str("cause", CauseName(mode.cause))
      .U64("frame_index", mode.frameIndex)
      .Num("capture_time", mode.captureTime)
      .Num("decision_time", mode.decisionTime)
      .Str("checkpoint_expected_sha256", SafeString(mode.checkpointExpectedSha256, kIdLength))
      .Str("checkpoint_actual_sha256", SafeString(mode.checkpointActualSha256, kIdLength))
      .Str("refusal_reason", SafeString(mode.refusalReason, sizeof(mode.refusalReason)));
  static const char* const kKeys[] = {"capture_time", "decision_time", "receipt_time_mono_ns"};
  static const char* const kClocks[] = {"simulation", "monotonic", "monotonic"};
  object.Raw("clocks", ClocksMap(kKeys, kClocks));
  object.I64("receipt_time_mono_ns", TotalNanos(receiptMono));
  return object.Build();
}

std::string ActuationState(const ActuationStatePayload& state, double receiptMono) {
  JsonObj object;
  object.Bool("applied", state.applied != 0)
      .Bool("stop_in_force", state.stopInForce != 0)
      .Str("cause", CauseName(state.cause))
      .F32("acceleration", state.acceleration)
      .F32("steering_angle", state.steeringAngle)
      .Num("actuation_time", state.actuationTime)
      .Num("stop_since", state.stopSince)
      .Num("stop_since_mono", state.stopSinceMono)
      .Str("plan_reference", SafeString(state.planReference, kIdLength));
  static const char* const kKeys[] = {"actuation_time", "stop_since", "stop_since_mono",
                                      "receipt_time_mono_ns"};
  static const char* const kClocks[] = {"simulation", "simulation", "monotonic", "monotonic"};
  object.Raw("clocks", ClocksMap(kKeys, kClocks));
  object.I64("receipt_time_mono_ns", TotalNanos(receiptMono));
  return object.Build();
}

}  // namespace logjson

// ------------------------------------------------------------------ publisher
PublisherCore::PublisherCore(Options options) : options_(std::move(options)) {}

void PublisherCore::SetRealTimeAtMono(double monoSeconds, double realSeconds) {
  // One exact integer offset: every later real time is mono_ns + offset, so the
  // nanoseconds of a monotonic instant survive the addition unchanged (a double
  // at 1.7e9 s only resolves ~238 ns, and re-adding it would wobble the ns part).
  realOffsetNanos_ = TotalNanos(realSeconds) - TotalNanos(monoSeconds);
}

void PublisherCore::SetRefusal(std::string_view expectedSha, std::string_view actualSha,
                               std::string_view reason) {
  // The contract fixes 64 hex characters for a SHA-256 and a short token for
  // the reason. Longer input is cut here, not silently on the wire, and the cut
  // is logged so no detail disappears without a record.
  auto take = [this](std::string_view text, std::size_t limit, const char* field) {
    if (text.size() <= limit) return std::string{text};
    JsonObj object;
    object.Str("code", "refusal_detail_truncated")
        .Str("field", field)
        .U64("length", text.size())
        .U64("limit", limit);
    log_.push_back(LogRecord{"error", 0, object.Build()});
    return std::string{text.substr(0, limit)};
  };
  refusalExpected_ = take(expectedSha, kRefusalShaLength, "checkpoint_expected_sha256");
  refusalActual_ = take(actualSha, kRefusalShaLength, "checkpoint_actual_sha256");
  refusalReason_ = take(reason, kRefusalReasonLength, "refusal_reason");
}

std::uint64_t PublisherCore::Sequence(Kind kind) const {
  return sequence_[static_cast<std::size_t>(kind) & 3U];
}

Mode PublisherCore::ReportedMode() const {
  if (stopLatched_) return stopMode_;
  if (haveMode_) return lastMode_;
  return Mode::kStarting;
}

Cause PublisherCore::ReportedCause() const {
  if (stopLatched_) return stopCause_;
  if (haveMode_) return lastCause_;
  return Cause::kNone;
}

std::string_view PublisherCore::ReportedModeSource() const {
  if (stopLatched_) return stopSource_;
  if (haveMode_) return "superviseLoop";
  // Before the first mode event: the priming health reports kStarting, and no
  // source has said so yet. See README ("mode_source during priming").
  return std::string_view{};
}

PublisherCore::Header PublisherCore::MakeHeader(Kind kind, std::uint64_t sequence,
                                                double nowMono) const {
  Header header;
  header.kind = kind;
  header.sequence = sequence;
  header.publishMonoNs = TotalNanos(nowMono);
  header.publishRealNs = header.publishMonoNs + realOffsetNanos_;
  header.publishMono = SplitNanos(header.publishMonoNs);
  header.publishReal = SplitNanos(header.publishRealNs);
  return header;
}

void PublisherCore::CommitFrame(Frame& frame, const std::uint8_t* message, std::size_t length) {
  frame.messageBytes = static_cast<std::uint32_t>(length);
  frame.size = static_cast<std::uint32_t>(length + 4);
  std::memset(frame.bytes, 0, 4);
  frame.bytes[0] = static_cast<std::uint8_t>(length & 0xFFU);
  frame.bytes[1] = static_cast<std::uint8_t>((length >> 8U) & 0xFFU);
  frame.bytes[2] = static_cast<std::uint8_t>((length >> 16U) & 0xFFU);
  frame.bytes[3] = static_cast<std::uint8_t>((length >> 24U) & 0xFFU);
  std::memcpy(frame.bytes + 4, message, length);
}

void PublisherCore::NoteDrop(std::string_view reason, Kind kind) {
  ++droppedSamples_;
  JsonObj object;
  object.Str("reason", reason)
      .Str("kind", KindName(kind))
      .U64("message_capacity_bytes", static_cast<std::uint64_t>(options_.messageCapacityBytes))
      .U64("dropped_samples", droppedSamples_);
  log_.push_back(LogRecord{"drop", droppedSamples_, object.Build()});
}

void PublisherCore::NoteDownstreamDrop(std::string_view reason) {
  NoteDrop(reason, Kind::kUnspecified);
}

void PublisherCore::EnsureStarted(double nowMono, std::vector<Frame>& frames) {
  if (started_) return;
  started_ = true;
  nextHealthMono_ = nowMono + kHealthPeriodSeconds;
  // The priming health: the observer learns the publisher is up at once, and
  // REQ-DRIVING-017's spacing starts from here.
  Frame health = EmitHealth(nowMono);
  if (health.size != 0) frames.push_back(std::move(health));
}

std::uint32_t PublisherCore::CheckPlanCaptureMs(const DrivingPlanPayload& plan) {
  // ICD section 1: simulation time is the frame index x 100 ms, exact. The
  // capture time is the payload's own statement of the same instant; if the two
  // disagree the frame index wins and the disagreement is logged once.
  const std::uint64_t fromFrame = plan.frameIndex * 100ULL;
  const std::uint32_t expected = ClampU32(fromFrame);
  const std::uint32_t derived = SimulationMs(plan.captureTime);
  if (derived != expected && !captureMismatchLogged_) {
    captureMismatchLogged_ = true;
    JsonObj object;
    object.Str("code", "capture_time_mismatch")
        .Str("kind", "PLAN")
        .U64("frame_index", plan.frameIndex)
        .U64("frame_sim_ms", expected)
        .U64("derived_sim_ms", derived);
    log_.push_back(LogRecord{"error", 0, object.Build()});
  }
  return expected;
}

Frame PublisherCore::EmitHealth(double nowMono) {
  Frame frame;
  frame.kind = Kind::kHealth;
  frame.port = Port::kHealth;
  const std::uint64_t sequence = Sequence(Kind::kHealth) + 1;

  const Mode mode = ReportedMode();
  const Cause cause = ReportedCause();
  const std::string_view source = ReportedModeSource();
  const double causeSince = stopLatched_ ? causeSinceMono_ : 0.0;

  const Header header = MakeHeader(Kind::kHealth, sequence, nowMono);
  const TimeSplit since = SplitSeconds(causeSince);
  const TimeSplit planProduction = SplitSeconds(lastPlanProductionMono_);

  std::uint8_t message[kMaxMessageBytes];
  StructEncoder encoder(message, options_.messageCapacityBytes);
  encoder.U32(kSchemaMajor);                                     // 1 schema_major
  encoder.U32(kSchemaMinor);                                     // 2 schema_minor
  encoder.U32(static_cast<std::uint32_t>(Kind::kHealth));        // 3 kind
  encoder.U32(ClampU32(sequence));                               // 4 sequence
  encoder.Str(options_.producer);                                // 5 producer
  encoder.U32(header.publishReal.seconds);                       // 6 publish_real_s
  encoder.U32(header.publishReal.nanos);                         // 7 publish_real_ns
  encoder.U32(header.publishMono.seconds);                       // 8 publish_mono_s
  encoder.U32(header.publishMono.nanos);                         // 9 publish_mono_ns
  encoder.U32(0);                                                // 10 plan_frame_index
  encoder.U32(0);                                                // 11 plan_capture_ms
  encoder.U32(0);                                                // 12 plan_production_mono_s
  encoder.U32(0);                                                // 13 plan_production_mono_ns
  encoder.Str(std::string_view{});                               // 14 plan_reference
  encoder.Str(std::string_view{});                               // 15 run_record
  encoder.Str(std::string_view{});                               // 16 plan_producer
  encoder.U32(0);                                                // 17 plan_sample_count
  encoder.F32(0.0f);                                             // 18 plan_horizon_s
  encoder.F32Array(nullptr, 0);                                  // 19 plan_acceleration
  encoder.F32Array(nullptr, 0);                                  // 20 plan_curvature
  encoder.F32Array(nullptr, 0);                                  // 21 plan_x
  encoder.F32Array(nullptr, 0);                                  // 22 plan_y
  encoder.F32(0.0f);                                             // 23 speed_kmh
  encoder.F32(0.0f);                                             // 24 longitudinal_acceleration
  encoder.F32(0.0f);                                             // 25 lateral_acceleration
  encoder.F32(0.0f);                                             // 26 yaw_rate_dps
  encoder.U32(0);                                                // 27 sample_capture_ms
  encoder.U32(0);                                                // 28 sample_receipt_mono_s
  encoder.U32(0);                                                // 29 sample_receipt_mono_ns
  encoder.U32(static_cast<std::uint32_t>(mode));                 // 30 mode
  encoder.U32(static_cast<std::uint32_t>(cause));                // 31 cause
  encoder.Str(source);                                           // 32 mode_source
  encoder.U32(since.seconds);                                    // 33 cause_since_mono_s
  encoder.U32(since.nanos);                                      // 34 cause_since_mono_ns
  encoder.U32(ClampU32(lastPlanFrameIndex_));                    // 35 last_plan_frame_index
  encoder.U32(lastPlanCaptureMs_);                               // 36 last_plan_capture_ms
  encoder.U32(stepCaptureMs_);                                   // 37 step_capture_ms
  encoder.U32(planProduction.seconds);                           // 38 last_plan_production_mono_s
  encoder.U32(planProduction.nanos);                             // 39 last_plan_production_mono_ns
  encoder.U32(ClampU32(droppedSamples_));                        // 40 dropped_samples
  encoder.Str(refusalExpected_);                                 // 41 checkpoint_expected_sha256
  encoder.Str(refusalActual_);                                   // 42 checkpoint_actual_sha256
  encoder.Str(refusalReason_);                                   // 43 refusal_reason

  if (!encoder.ok()) {
    NoteDrop("message_too_large", Kind::kHealth);
    Frame dropped;
    dropped.kind = Kind::kUnspecified;
    return dropped;  // size == 0
  }

  CommitFrame(frame, message, encoder.size());
  sequence_[static_cast<std::size_t>(Kind::kHealth)] = sequence;
  frame.sequence = sequence;

  JsonObj object;
  object.Str("kind", KindName(Kind::kHealth))
      .U64("sequence", sequence)
      .Str("producer", options_.producer)
      .I64("publish_mono_ns", TotalNanos(nowMono))
      .I64("publish_real_ns", header.publishRealNs)
      .Str("mode", ModeName(mode))
      .Str("cause", CauseName(cause))
      .Str("mode_source", source)
      .U64("cause_since_mono_ns", stopLatched_ ? static_cast<std::uint64_t>(TotalNanos(causeSince)) : 0)
      .U64("last_plan_frame_index", lastPlanFrameIndex_)
      .U64("last_plan_capture_sim_ms", lastPlanCaptureMs_)
      .U64("step_capture_sim_ms", stepCaptureMs_)
      .U64("last_plan_production_mono_ns",
           static_cast<std::uint64_t>(TotalNanos(lastPlanProductionMono_)))
      .U64("dropped_samples", droppedSamples_);
  if (!refusalReason_.empty() || !refusalExpected_.empty()) {
    object.Str("checkpoint_expected_sha256", refusalExpected_)
        .Str("checkpoint_actual_sha256", refusalActual_)
        .Str("refusal_reason", refusalReason_);
  }
  static const char* const kKeys[] = {"publish_mono_ns",   "publish_real_ns",
                                      "cause_since_mono_ns", "last_plan_capture_sim_ms",
                                      "step_capture_sim_ms", "last_plan_production_mono_ns"};
  static const char* const kClocks[] = {"monotonic", "real",         "monotonic",
                                        "simulation", "simulation", "monotonic"};
  object.Raw("clocks", ClocksMap(kKeys, kClocks));
  frame.logDataJson = object.Build();
  return frame;
}

std::vector<Frame> PublisherCore::Tick(double nowMono) {
  std::vector<Frame> frames;
  EnsureStarted(nowMono, frames);
  const double epsilon = 1e-9;  // 1 ns: double accumulation of 0.1 s steps
  if (nowMono + epsilon < nextHealthMono_) return frames;
  Frame health = EmitHealth(nowMono);
  // One publication per call even after a stall: the deadlines that passed
  // while the loop was away are skipped, not replayed as a burst of duplicates
  // carrying the same time.
  const double missed =
      std::floor((nowMono - nextHealthMono_) / kHealthPeriodSeconds + 1e-9) + 1.0;
  nextHealthMono_ += missed * kHealthPeriodSeconds;
  while (nextHealthMono_ <= nowMono + epsilon) nextHealthMono_ += kHealthPeriodSeconds;
  if (health.size != 0) frames.push_back(std::move(health));
  return frames;
}

std::vector<Frame> PublisherCore::OnPlan(const DrivingPlanPayload& plan, double receiptMono) {
  std::vector<Frame> frames;
  EnsureStarted(receiptMono, frames);

  Frame frame;
  frame.kind = Kind::kPlan;
  frame.port = Port::kPlan;
  const std::uint64_t sequence = Sequence(Kind::kPlan) + 1;
  const Header header = MakeHeader(Kind::kPlan, sequence, receiptMono);

  // The message carries the newest 64 pairs of the plan; a shorter plan is
  // published as it came. ICD v2 amendment 1 (A4): plan_sample_count (17) is
  // the payload's raw sampleCount, so a malformed plan (> 64) stays visible;
  // the arrays carry min(sampleCount, 64) samples (REQ-DRIVING-027 judges such
  // a plan, not the publisher).
  const std::size_t count = std::min<std::size_t>(plan.sampleCount, kPlanSamples);
  float acceleration[kPlanSamples];
  float curvature[kPlanSamples];
  float x[kPlanSamples];
  float y[kPlanSamples];
  for (std::size_t i = 0; i < count; ++i) {
    acceleration[i] = plan.samples[i].acceleration;
    curvature[i] = plan.samples[i].curvature;
    x[i] = plan.samples[i].x;
    y[i] = plan.samples[i].y;
  }

  const std::uint32_t captureMs = CheckPlanCaptureMs(plan);
  const TimeSplit production = SplitSeconds(plan.productionTime);
  const std::string_view planProducer = SafeString(plan.producer, kIdLength);

  std::uint8_t message[kMaxMessageBytes];
  StructEncoder encoder(message, options_.messageCapacityBytes);
  encoder.U32(kSchemaMajor);                                     // 1 schema_major
  encoder.U32(kSchemaMinor);                                     // 2 schema_minor
  encoder.U32(static_cast<std::uint32_t>(Kind::kPlan));          // 3 kind
  encoder.U32(ClampU32(sequence));                               // 4 sequence
  encoder.Str(options_.producer);                                // 5 producer
  encoder.U32(header.publishReal.seconds);                       // 6 publish_real_s
  encoder.U32(header.publishReal.nanos);                         // 7 publish_real_ns
  encoder.U32(header.publishMono.seconds);                       // 8 publish_mono_s
  encoder.U32(header.publishMono.nanos);                         // 9 publish_mono_ns
  encoder.U32(ClampU32(plan.frameIndex));                        // 10 plan_frame_index
  encoder.U32(captureMs);                                        // 11 plan_capture_ms
  encoder.U32(production.seconds);                               // 12 plan_production_mono_s
  encoder.U32(production.nanos);                                 // 13 plan_production_mono_ns
  encoder.Str(SafeString(plan.planReference, kIdLength));        // 14 plan_reference
  encoder.Str(SafeString(plan.runRecord, kIdLength));            // 15 run_record
  encoder.Str(planProducer);                                     // 16 plan_producer
  encoder.U32(plan.sampleCount);                                 // 17 plan_sample_count (raw, A4)
  encoder.F32(plan.horizon);                                     // 18 plan_horizon_s
  encoder.F32Array(acceleration, count);                         // 19 plan_acceleration
  encoder.F32Array(curvature, count);                            // 20 plan_curvature
  encoder.F32Array(x, count);                                    // 21 plan_x
  encoder.F32Array(y, count);                                    // 22 plan_y
  encoder.F32(0.0f);                                             // 23 speed_kmh
  encoder.F32(0.0f);                                             // 24 longitudinal_acceleration
  encoder.F32(0.0f);                                             // 25 lateral_acceleration
  encoder.F32(0.0f);                                             // 26 yaw_rate_dps
  encoder.U32(0);                                                // 27 sample_capture_ms
  encoder.U32(0);                                                // 28 sample_receipt_mono_s
  encoder.U32(0);                                                // 29 sample_receipt_mono_ns
  encoder.U32(0);                                                // 30 mode
  encoder.U32(0);                                                // 31 cause
  encoder.Str(std::string_view{});                               // 32 mode_source
  encoder.U32(0);                                                // 33 cause_since_mono_s
  encoder.U32(0);                                                // 34 cause_since_mono_ns
  encoder.U32(0);                                                // 35 last_plan_frame_index
  encoder.U32(0);                                                // 36 last_plan_capture_ms
  encoder.U32(0);                                                // 37 step_capture_ms
  encoder.U32(0);                                                // 38 last_plan_production_mono_s
  encoder.U32(0);                                                // 39 last_plan_production_mono_ns
  encoder.U32(0);                                                // 40 dropped_samples
  encoder.Str(std::string_view{});                               // 41 checkpoint_expected_sha256
  encoder.Str(std::string_view{});                               // 42 checkpoint_actual_sha256
  encoder.Str(std::string_view{});                               // 43 refusal_reason

  if (!encoder.ok()) {
    NoteDrop("message_too_large", Kind::kPlan);
    return frames;
  }

  CommitFrame(frame, message, encoder.size());
  sequence_[static_cast<std::size_t>(Kind::kPlan)] = sequence;
  frame.sequence = sequence;

  JsonObj object;
  object.Str("kind", KindName(Kind::kPlan))
      .U64("sequence", sequence)
      .Str("producer", options_.producer)
      .I64("publish_mono_ns", TotalNanos(receiptMono))
      .I64("publish_real_ns", header.publishRealNs)
      .U64("plan_frame_index", plan.frameIndex)
      .U64("plan_capture_sim_ms", captureMs)
      .U64("plan_production_mono_ns", static_cast<std::uint64_t>(TotalNanos(plan.productionTime)))
      .Str("plan_reference", SafeString(plan.planReference, kIdLength))
      .Str("run_record", SafeString(plan.runRecord, kIdLength))
      .Str("plan_producer", planProducer)
      .U64("plan_sample_count", plan.sampleCount)
      .F32("plan_horizon_s", plan.horizon)
      .Raw("plan_acceleration", JsonFloatArray(acceleration, count))
      .Raw("plan_curvature", JsonFloatArray(curvature, count))
      .Raw("plan_x", JsonFloatArray(x, count))
      .Raw("plan_y", JsonFloatArray(y, count));
  static const char* const kKeys[] = {"publish_mono_ns", "publish_real_ns",
                                      "plan_capture_sim_ms", "plan_production_mono_ns"};
  static const char* const kClocks[] = {"monotonic", "real", "simulation", "monotonic"};
  object.Raw("clocks", ClocksMap(kKeys, kClocks));
  frame.logDataJson = object.Build();

  lastPlanFrameIndex_ = plan.frameIndex;
  lastPlanCaptureMs_ = captureMs;
  lastPlanProductionMono_ = plan.productionTime;
  stepCaptureMs_ = std::max(stepCaptureMs_, captureMs);
  frames.push_back(std::move(frame));
  return frames;
}

std::vector<Frame> PublisherCore::OnEgoMotionSample(const EgoMotionSamplePayload& sample,
                                                    double receiptMono) {
  std::vector<Frame> frames;
  EnsureStarted(receiptMono, frames);

  Frame frame;
  frame.kind = Kind::kVehicleState;
  frame.port = Port::kVehicleState;
  const std::uint64_t sequence = Sequence(Kind::kVehicleState) + 1;
  const Header header = MakeHeader(Kind::kVehicleState, sequence, receiptMono);

  // The sample carries no frame index (MAP-DRIVING-EGO-MOTION has the capture
  // time only), so simulation ms is derived from it, rounded to the nearest
  // millisecond of a 100 ms grid.
  const std::uint32_t captureMs = SimulationMs(sample.captureTime);
  const TimeSplit receipt = SplitSeconds(receiptMono);

  std::uint8_t message[kMaxMessageBytes];
  StructEncoder encoder(message, options_.messageCapacityBytes);
  encoder.U32(kSchemaMajor);                                     // 1 schema_major
  encoder.U32(kSchemaMinor);                                     // 2 schema_minor
  encoder.U32(static_cast<std::uint32_t>(Kind::kVehicleState));  // 3 kind
  encoder.U32(ClampU32(sequence));                               // 4 sequence
  encoder.Str(options_.producer);                                // 5 producer
  encoder.U32(header.publishReal.seconds);                       // 6 publish_real_s
  encoder.U32(header.publishReal.nanos);                         // 7 publish_real_ns
  encoder.U32(header.publishMono.seconds);                       // 8 publish_mono_s
  encoder.U32(header.publishMono.nanos);                         // 9 publish_mono_ns
  encoder.U32(0);                                                // 10 plan_frame_index
  encoder.U32(0);                                                // 11 plan_capture_ms
  encoder.U32(0);                                                // 12 plan_production_mono_s
  encoder.U32(0);                                                // 13 plan_production_mono_ns
  encoder.Str(std::string_view{});                               // 14 plan_reference
  encoder.Str(std::string_view{});                               // 15 run_record
  encoder.Str(std::string_view{});                               // 16 plan_producer
  encoder.U32(0);                                                // 17 plan_sample_count
  encoder.F32(0.0f);                                             // 18 plan_horizon_s
  encoder.F32Array(nullptr, 0);                                  // 19 plan_acceleration
  encoder.F32Array(nullptr, 0);                                  // 20 plan_curvature
  encoder.F32Array(nullptr, 0);                                  // 21 plan_x
  encoder.F32Array(nullptr, 0);                                  // 22 plan_y
  encoder.F32(sample.speed);                                     // 23 speed_kmh
  encoder.F32(sample.longitudinalAcceleration);                  // 24 longitudinal_acceleration
  encoder.F32(sample.lateralAcceleration);                       // 25 lateral_acceleration
  encoder.F32(sample.yawRate);                                   // 26 yaw_rate_dps
  encoder.U32(captureMs);                                        // 27 sample_capture_ms
  encoder.U32(receipt.seconds);                                  // 28 sample_receipt_mono_s
  encoder.U32(receipt.nanos);                                    // 29 sample_receipt_mono_ns
  encoder.U32(0);                                                // 30 mode
  encoder.U32(0);                                                // 31 cause
  encoder.Str(std::string_view{});                               // 32 mode_source
  encoder.U32(0);                                                // 33 cause_since_mono_s
  encoder.U32(0);                                                // 34 cause_since_mono_ns
  encoder.U32(0);                                                // 35 last_plan_frame_index
  encoder.U32(0);                                                // 36 last_plan_capture_ms
  encoder.U32(0);                                                // 37 step_capture_ms
  encoder.U32(0);                                                // 38 last_plan_production_mono_s
  encoder.U32(0);                                                // 39 last_plan_production_mono_ns
  encoder.U32(0);                                                // 40 dropped_samples
  encoder.Str(std::string_view{});                               // 41 checkpoint_expected_sha256
  encoder.Str(std::string_view{});                               // 42 checkpoint_actual_sha256
  encoder.Str(std::string_view{});                               // 43 refusal_reason

  if (!encoder.ok()) {
    NoteDrop("message_too_large", Kind::kVehicleState);
    return frames;
  }

  CommitFrame(frame, message, encoder.size());
  sequence_[static_cast<std::size_t>(Kind::kVehicleState)] = sequence;
  frame.sequence = sequence;

  JsonObj object;
  object.Str("kind", KindName(Kind::kVehicleState))
      .U64("sequence", sequence)
      .Str("producer", options_.producer)
      .I64("publish_mono_ns", TotalNanos(receiptMono))
      .I64("publish_real_ns", header.publishRealNs)
      .F32("speed_kmh", sample.speed)
      .F32("longitudinal_acceleration", sample.longitudinalAcceleration)
      .F32("lateral_acceleration", sample.lateralAcceleration)
      .F32("yaw_rate_dps", sample.yawRate)
      .U64("sample_capture_sim_ms", captureMs)
      .U64("sample_receipt_mono_ns", static_cast<std::uint64_t>(TotalNanos(receiptMono)));
  static const char* const kKeys[] = {"publish_mono_ns", "publish_real_ns", "sample_capture_sim_ms",
                                      "sample_receipt_mono_ns"};
  static const char* const kClocks[] = {"monotonic", "real", "simulation", "monotonic"};
  object.Raw("clocks", ClocksMap(kKeys, kClocks));
  frame.logDataJson = object.Build();

  stepCaptureMs_ = std::max(stepCaptureMs_, captureMs);
  frames.push_back(std::move(frame));
  return frames;
}

std::vector<Frame> PublisherCore::OnMode(const DrivingModePayload& mode, double receiptMono) {
  std::vector<Frame> frames;
  EnsureStarted(receiptMono, frames);

  lastMode_ = mode.mode;
  lastCause_ = mode.cause;
  haveMode_ = true;

  // ICD v2 amendment 1 (A5): the refusal detail rides the kRefused mode; set it
  // before the stop's immediate health so that health already holds 41-43.
  if (mode.mode == Mode::kRefused) {
    SetRefusal(SafeString(mode.checkpointExpectedSha256, kIdLength),
               SafeString(mode.checkpointActualSha256, kIdLength),
               SafeString(mode.refusalReason, sizeof(mode.refusalReason)));
  }

  if (!IsStopMode(mode.mode)) return frames;

  if (!stopLatched_) {
    // The stop enters here: publish its health in this call (REQ-DRIVING-029
    // wants it within 100 ms of the start; the same call leaves no room).
    stopLatched_ = true;
    stopMode_ = mode.mode;
    stopCause_ = mode.cause;
    stopSource_ = "superviseLoop";
    // The mode carries the decision time on the monotonic clock; it is when
    // the stop began.
    causeSinceMono_ = mode.decisionTime > 0.0 ? mode.decisionTime : receiptMono;

    JsonObj object;
    object.Str("source", "superviseLoop")
        .Str("mode", ModeName(mode.mode))
        .Str("cause", CauseName(mode.cause))
        .U64("frame_index", mode.frameIndex)
        .Num("capture_time", mode.captureTime)
        .Num("decision_time", mode.decisionTime)
        .U64("receipt_time_mono_ns", static_cast<std::uint64_t>(TotalNanos(receiptMono)))
        .U64("cause_since_mono_ns", static_cast<std::uint64_t>(TotalNanos(causeSinceMono_)));
    static const char* const kKeys[] = {"capture_time", "decision_time", "receipt_time_mono_ns",
                                        "cause_since_mono_ns"};
    static const char* const kClocks[] = {"simulation", "monotonic", "monotonic", "monotonic"};
    object.Raw("clocks", ClocksMap(kKeys, kClocks));
    log_.push_back(LogRecord{"stop_response.begin", 0, object.Build()});

    if (mode.mode == Mode::kStandstill) {
      // The run was already stopped when the agent first reported it: both
      // moments of ICD section 6 fall together.
      standstillLogged_ = true;
      JsonObj standstill;
      standstill.Str("source", "superviseLoop")
          .Str("mode", ModeName(mode.mode))
          .Str("cause", CauseName(mode.cause))
          .U64("frame_index", mode.frameIndex)
          .Num("capture_time", mode.captureTime)
          .Num("decision_time", mode.decisionTime)
          .U64("receipt_time_mono_ns", static_cast<std::uint64_t>(TotalNanos(receiptMono)))
          .U64("cause_since_mono_ns", static_cast<std::uint64_t>(TotalNanos(causeSinceMono_)));
      standstill.Raw("clocks", ClocksMap(kKeys, kClocks));
      log_.push_back(LogRecord{"stop_response.standstill", 0, standstill.Build()});
    }

    Frame health = EmitHealth(receiptMono);
    if (health.size != 0) frames.push_back(std::move(health));
    return frames;
  }

  // The stop stays in force. Only a stop the agent named follows the agent's
  // own mode (kStopResponse -> kStandstill): a stop the adapter named keeps its
  // source, cause and instant, so mode_source always names the report that
  // began it.
  if (stopSource_ != "superviseLoop") return frames;

  stopMode_ = mode.mode;
  if (stopCause_ == Cause::kNone && mode.cause != Cause::kNone) stopCause_ = mode.cause;
  if (mode.mode == Mode::kStandstill && !standstillLogged_) {
    standstillLogged_ = true;
    JsonObj object;
    object.Str("source", "superviseLoop")
        .Str("mode", ModeName(mode.mode))
        .Str("cause", CauseName(stopCause_))
        .U64("frame_index", mode.frameIndex)
        .Num("capture_time", mode.captureTime)
        .Num("decision_time", mode.decisionTime)
        .U64("receipt_time_mono_ns", static_cast<std::uint64_t>(TotalNanos(receiptMono)))
        .U64("cause_since_mono_ns", static_cast<std::uint64_t>(TotalNanos(causeSinceMono_)));
    static const char* const kKeys[] = {"capture_time", "decision_time", "receipt_time_mono_ns",
                                        "cause_since_mono_ns"};
    static const char* const kClocks[] = {"simulation", "monotonic", "monotonic", "monotonic"};
    object.Raw("clocks", ClocksMap(kKeys, kClocks));
    log_.push_back(LogRecord{"stop_response.standstill", 0, object.Build()});
    Frame health = EmitHealth(receiptMono);
    if (health.size != 0) frames.push_back(std::move(health));
  }
  return frames;
}

std::vector<Frame> PublisherCore::OnActuationState(const ActuationStatePayload& state,
                                                   double receiptMono) {
  std::vector<Frame> frames;
  EnsureStarted(receiptMono, frames);

  if (state.stopInForce == 0 || stopLatched_) return frames;

  // The adapter applies the stop response itself (REQ-DRIVING-028) and dates
  // it on the monotonic clock (ICD v2: stopSinceMono). That stamp is when the
  // stop began; the receipt time is the fallback for a producer that left it 0.
  stopLatched_ = true;
  stopMode_ = Mode::kStopResponse;
  stopCause_ = state.cause;
  stopSource_ = "actuationAdapter";
  causeSinceMono_ = state.stopSinceMono > 0.0 ? state.stopSinceMono : receiptMono;

  JsonObj object;
  object.Str("source", "actuationAdapter")
      .Str("mode", ModeName(stopMode_))
      .Str("cause", CauseName(state.cause))
      .F32("acceleration", state.acceleration)
      .F32("steering_angle", state.steeringAngle)
      .Num("actuation_time", state.actuationTime)
      .Num("stop_since", state.stopSince)
      .Num("stop_since_mono", state.stopSinceMono)
      .U64("receipt_time_mono_ns", static_cast<std::uint64_t>(TotalNanos(receiptMono)))
      .U64("cause_since_mono_ns", static_cast<std::uint64_t>(TotalNanos(causeSinceMono_)));
  static const char* const kKeys[] = {"actuation_time", "stop_since", "stop_since_mono",
                                      "receipt_time_mono_ns", "cause_since_mono_ns"};
  static const char* const kClocks[] = {"simulation", "simulation", "monotonic", "monotonic",
                                        "monotonic"};
  object.Raw("clocks", ClocksMap(kKeys, kClocks));
  log_.push_back(LogRecord{"stop_response.begin", 0, object.Build()});

  Frame health = EmitHealth(receiptMono);
  if (health.size != 0) frames.push_back(std::move(health));
  return frames;
}

std::vector<LogRecord> PublisherCore::DrainLog() {
  std::vector<LogRecord> records;
  records.swap(log_);
  return records;
}

}  // namespace de4sdv::driving::publisher
