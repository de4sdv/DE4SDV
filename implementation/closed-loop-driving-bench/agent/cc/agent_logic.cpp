// DE4SDV INC-DRIVING-001 slice 10b: the pure decision logic of the driving
// agent's conditionInputs, superviseLoop and commandVehicle activities.
// See agent_logic.h for the contract and README.md for the rule-to-code map.
#include "agent_logic.h"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <sstream>
#include <utility>

#include "de4sdv/driving/run_log.h"
#include "json_lite.h"

namespace de4sdv::driving::agent {

namespace {

constexpr double kPi = 3.141592653589793238462643383279502884;

double Degrees(double radians) { return radians * 180.0 / kPi; }

// A fixed-size char field as a std::string, stopping at NUL or the capacity.
std::string FixedField(const char* data, std::size_t capacity) {
  std::size_t length = 0;
  while (length < capacity && data[length] != '\0') ++length;
  return std::string(data, length);
}

// Writes a NUL-terminated identifier, truncating at the field's capacity - 1.
void SetId(char* destination, std::size_t capacity, const std::string& value) {
  std::memset(destination, 0, capacity);
  const std::size_t length = std::min(value.size(), capacity - 1);
  std::memcpy(destination, value.data(), length);
}

// Writes a fixed field of exactly `capacity` characters, NUL-padded. The
// checkpoint hashes are 64 hex characters with no terminating NUL (ICD 9, A5).
void SetExact(char* destination, std::size_t capacity, const std::string& value) {
  std::memset(destination, 0, capacity);
  std::memcpy(destination, value.data(), std::min(value.size(), capacity));
}

// ------------------------------------------------------------------ json text
std::string Field(const char* name, const std::string& value) {
  return std::string("\"") + name + "\":" + value;
}

std::string Join(const std::vector<std::string>& fields) {
  std::string out = "{";
  for (std::size_t i = 0; i < fields.size(); ++i) {
    if (i != 0) out += ",";
    out += fields[i];
  }
  return out + "}";
}

std::string Object(std::initializer_list<std::string> fields) {
  return Join(std::vector<std::string>(fields.begin(), fields.end()));
}

std::string Int(std::int64_t value) { return std::to_string(value); }

std::string Number(double value) { return JsonNumber(value); }

std::string Text(const std::string& value) { return JsonString(value); }

std::string Clocks(std::initializer_list<std::pair<const char*, const char*>> pairs) {
  std::string out = "{";
  bool first = true;
  for (const auto& pair : pairs) {
    if (!first) out += ",";
    out += Field(pair.first, Text(pair.second));
    first = false;
  }
  return out + "}";
}

// A plan sample as a JSON object; non-finite values become null.
std::string SampleJson(const PlanSample& sample) {
  return Object({Field("acceleration", Number(sample.acceleration)),
                 Field("curvature", Number(sample.curvature)), Field("x", Number(sample.x)),
                 Field("y", Number(sample.y)), Field("heading", Number(sample.heading))});
}

std::string PlanPayloadJson(const DrivingPlanPayload& plan) {
  std::string samples = "[";
  for (std::size_t i = 0; i < plan.sampleCount && i < kPlanSamples; ++i) {
    if (i != 0) samples += ",";
    samples += SampleJson(plan.samples[i]);
  }
  samples += "]";
  return Object({Field("frameIndex", Int(static_cast<std::int64_t>(plan.frameIndex))),
                 Field("captureTime", Number(plan.captureTime)),
                 Field("productionTime", Number(plan.productionTime)),
                 Field("horizon", Number(plan.horizon)),
                 Field("sampleCount", Int(static_cast<std::int64_t>(plan.sampleCount))),
                 Field("samples", samples),
                 Field("producer", Text(FixedField(plan.producer, kIdLength))),
                 Field("runRecord", Text(FixedField(plan.runRecord, kIdLength))),
                 Field("planReference", Text(FixedField(plan.planReference, kIdLength))),
                 Field("clocks", Clocks({{"captureTime", "simulation"},
                                         {"productionTime", "monotonic"}}))});
}

std::string PlanReferenceOf(const DrivingPlanPayload& plan) {
  return FixedField(plan.planReference, kIdLength);
}

}  // namespace

// ------------------------------------------------------------------ times
std::int64_t AgeMs(std::uint64_t step_frame, std::uint64_t other_frame) {
  return (static_cast<std::int64_t>(step_frame) - static_cast<std::int64_t>(other_frame)) * kStepMs;
}

std::int64_t IssueTimeMs(double issue_time_simulation_seconds) {
  return static_cast<std::int64_t>(std::llround(issue_time_simulation_seconds * 1000.0));
}

std::int64_t FrameMs(std::uint64_t frame) { return CaptureTimeMicros(frame) / 1000; }

double FrameSeconds(std::uint64_t frame) {
  return static_cast<double>(CaptureTimeMicros(frame)) / 1e6;
}

std::uint64_t PlanSampleIndex(std::uint64_t step_frame, std::uint64_t plan_frame) {
  const std::int64_t index =
      static_cast<std::int64_t>(step_frame) - static_cast<std::int64_t>(plan_frame);
  if (index < 0) return 0;
  if (index >= static_cast<std::int64_t>(kPlanSamples)) return kPlanSamples - 1;
  return static_cast<std::uint64_t>(index);
}

// ------------------------------------------------------------------ names
const char* ModeName(Mode mode) {
  switch (mode) {
    case Mode::kStarting: return "kStarting";
    case Mode::kDriving: return "kDriving";
    case Mode::kStopResponse: return "kStopResponse";
    case Mode::kStandstill: return "kStandstill";
    case Mode::kRefused: return "kRefused";
  }
  return "unknown";
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
  return "unknown";
}

const char* LawName(int law) {
  switch (static_cast<CommandLaw>(law)) {
    case CommandLaw::kFirstControl: return "first_control";
    case CommandLaw::kPurePursuit: return "pure_pursuit";
  }
  return "unknown";
}

std::uint32_t CauseBit(Cause cause) {
  return 1u << static_cast<std::uint32_t>(cause);
}

// ------------------------------------------------------------------ conditionInputs
Cause ConditionResult::Lowest() const {
  Cause lowest = Cause::kNone;
  bool found = false;
  for (Cause cause : causes) {
    if (!found || static_cast<std::uint8_t>(cause) < static_cast<std::uint8_t>(lowest)) {
      lowest = cause;
      found = true;
    }
  }
  return found ? lowest : Cause::kNone;
}

ConditionResult JudgeConditions(const StepConditions& conditions,
                                const CameraSize sizes[kCameraCount]) {
  ConditionResult result;

  const auto add = [&result](Cause cause) {
    if (!result.Has(cause)) {
      result.bits |= CauseBit(cause);
      result.causes.push_back(cause);
    }
  };

  // One bit per camera condition: missing, else invalid, else stale. A camera
  // cannot be stale without an image to date, so the checks are exclusive per
  // camera; different cameras can set different bits in the same step.
  for (std::size_t i = 0; i < kCameraCount; ++i) {
    const CameraObservation& camera = conditions.cameras[i];
    if (!camera.present) {
      add(Cause::kCameraMissing);
      continue;
    }
    const bool wrong_size = camera.width != sizes[i].width || camera.height != sizes[i].height;
    if (camera.empty || wrong_size || !camera.has_frame) {
      add(Cause::kCameraInvalid);
      continue;
    }
    if (AgeMs(conditions.step_frame, camera.frame_index) > kCameraStaleMs) {
      add(Cause::kCameraStale);
    }
  }

  // Motion: no sample ever, or any measured field not finite, is invalid;
  // otherwise the sample's age decides staleness.
  const EgoMotionSamplePayload& sample = conditions.motion.sample;
  const bool motion_finite = std::isfinite(sample.speed) &&
                             std::isfinite(sample.longitudinalAcceleration) &&
                             std::isfinite(sample.lateralAcceleration) &&
                             std::isfinite(sample.yawRate);
  if (!conditions.motion.has_sample || !motion_finite) {
    add(Cause::kMotionInvalid);
  } else if (AgeMs(conditions.step_frame, conditions.motion.frame_index) > kMotionStaleMs) {
    add(Cause::kMotionStale);
  }

  // Route: no announcement yet or more than 1 s old is stale; an empty newest
  // announcement or a raster without a corridor cell is empty.
  const RouteObservation& route = conditions.route;
  const std::int64_t route_age_ms =
      FrameMs(conditions.step_frame) - IssueTimeMs(route.issue_time);
  if (!route.has_announcement || route_age_ms > kRouteStaleMs) {
    add(Cause::kRouteStale);
  }
  if ((route.has_announcement && route.corridor_points == 0) ||
      route.raster_corridor_cells == 0) {
    add(Cause::kRouteEmpty);
  }

  std::sort(result.causes.begin(), result.causes.end(),
            [](Cause a, Cause b) {
              return static_cast<std::uint8_t>(a) < static_cast<std::uint8_t>(b);
            });
  return result;
}

bool IsPlanValid(const DrivingPlanPayload& plan) {
  if (plan.sampleCount != kPlanSamples) return false;
  for (std::size_t i = 0; i < kPlanSamples; ++i) {
    if (!std::isfinite(plan.samples[i].acceleration) ||
        !std::isfinite(plan.samples[i].curvature)) {
      return false;
    }
  }
  return true;
}

// ------------------------------------------------------------------ superviseLoop
Supervisor::Supervisor(RefusalDetail refusal) : refusal_(std::move(refusal)) {
  if (refusal_.refused) {
    mode_ = Mode::kRefused;
    cause_ = Cause::kCheckpointRefused;
  }
}

void Supervisor::EnterStop(Cause cause, std::uint64_t frame, double monotonic_seconds) {
  mode_ = Mode::kStopResponse;
  cause_ = cause;
  cause_frame_ = frame;
  cause_monotonic_ = monotonic_seconds;
  stop_pending_ = true;
}

void Supervisor::Latch(Cause cause, std::uint64_t frame, double monotonic_seconds) {
  // First cause wins: a refused checkpoint and a latched stop are never
  // overwritten by a later cause.
  if (cause_ != Cause::kNone) return;
  if (cause == Cause::kNone) return;
  EnterStop(cause, frame, monotonic_seconds);
}

void Supervisor::EndRun(std::uint64_t frame, double monotonic_seconds) {
  if (cause_ != Cause::kNone) return;  // a latched stop (or the refusal) wins
  EnterStop(Cause::kRunEnd, frame, monotonic_seconds);
}

void Supervisor::FillModePayload(DrivingModePayload* payload, std::uint64_t step_frame,
                                 double monotonic_seconds) const {
  *payload = DrivingModePayload{};
  payload->mode = mode_;
  payload->cause = cause_;
  payload->frameIndex = step_frame;
  payload->captureTime = FrameSeconds(step_frame);
  payload->decisionTime = monotonic_seconds;
  if (mode_ == Mode::kRefused) {
    // A5: 64 hex characters with no NUL in the 64-byte fields; reasons are
    // "mismatch" or "no_pin", NUL-padded in the 16-byte field.
    SetExact(payload->checkpointExpectedSha256, kIdLength, refusal_.expected_sha256);
    SetExact(payload->checkpointActualSha256, kIdLength, refusal_.actual_sha256);
    SetExact(payload->refusalReason, sizeof payload->refusalReason, refusal_.reason);
  }
}

SupervisorStep Supervisor::Step(std::uint64_t step_frame, double monotonic_seconds,
                                const ConditionResult& conditions,
                                const DrivingPlanPayload* plan_this_step,
                                const MotionObservation& motion) {
  const bool plan_arrived = plan_this_step != nullptr;
  const bool plan_valid = plan_arrived && IsPlanValid(*plan_this_step);

  // An invalid plan never replaces the newest valid one (REQ-DRIVING-027).
  if (plan_valid) {
    newest_valid_ = *plan_this_step;
    has_valid_plan_ = true;
  }

  if (mode_ == Mode::kRefused) {
    // kRefused is permanent: the checkpoint identity was refused before any
    // plan existed, so no step can leave it.
    mode_ = Mode::kRefused;
  } else if (mode_ == Mode::kStarting) {
    // Faults while starting are logged but start no stop; the first step with a
    // valid plan and no input bit is the first driving step.
    if (plan_valid && !conditions.Any()) mode_ = Mode::kDriving;
  } else if (mode_ == Mode::kDriving) {
    // One cause per stop, in pipeline order (ICD.md section 4): the step's input
    // conditions first (lowest Cause value among them), then a plan that arrived
    // in this step and is invalid (REQ-DRIVING-027), then the age of the newest
    // valid plan (REQ-DRIVING-026). An invalid plan arriving in the step its
    // predecessor goes stale is reported as kPlanInvalid, as VC-DRIVING-027 reads.
    Cause stop = Cause::kNone;
    if (conditions.Any()) {
      stop = conditions.Lowest();
    } else if (plan_arrived && !plan_valid) {
      stop = Cause::kPlanInvalid;
    } else if (has_valid_plan_ &&
               AgeMs(step_frame, newest_valid_.frameIndex) > kPlanStaleMs) {
      stop = Cause::kPlanStale;
    }
    if (stop != Cause::kNone) EnterStop(stop, step_frame, monotonic_seconds);
  } else if (mode_ == Mode::kStopResponse) {
    // REQ-DRIVING-022: the first step whose newest motion sample is below the
    // standstill threshold; latched for the run.
    if (motion.has_sample && motion.sample.speed < kStandstillKmh) {
      mode_ = Mode::kStandstill;
    }
  }

  SupervisorStep out;
  out.mode = mode_;
  out.cause = cause_;
  out.mode_changed = !has_last_reported_ || last_reported_ != mode_;
  out.stop_began = stop_pending_;
  out.newest_valid_plan = has_valid_plan_ ? &newest_valid_ : nullptr;
  FillModePayload(&out.mode_payload, step_frame, monotonic_seconds);

  stop_pending_ = false;
  has_last_reported_ = true;
  last_reported_ = mode_;
  return out;
}

// ------------------------------------------------------------------ commandVehicle
bool ParseVehicleConfig(const std::string& json_text, VehicleConfig* out, std::string* error) {
  const auto fail = [error](const std::string& message) {
    if (error != nullptr) *error = message;
    return false;
  };
  std::string parse_error;
  const json::Value root = json::Value::Parse(json_text, &parse_error);
  if (!parse_error.empty() || !root.IsObject()) {
    return fail("vehicle configuration is not a JSON object: " +
                (parse_error.empty() ? std::string("not an object") : parse_error));
  }

  const auto positive = [&](const char* key, double* value) {
    const json::Value* field = root.Find(key);
    if (field == nullptr) return fail(std::string("vehicle configuration: missing ") + key);
    if (!field->IsNumber()) {
      return fail(std::string("vehicle configuration: ") + key + " must be a number");
    }
    const double number = field->AsNumber(0.0);
    if (!std::isfinite(number) || !(number > 0.0)) {
      return fail(std::string("vehicle configuration: ") + key + " must be positive");
    }
    *value = number;
    return true;
  };

  VehicleConfig config;
  if (!positive("wheelbase_m", &config.wheelbase_m) ||
      !positive("max_acceleration_mps2", &config.max_acceleration_mps2) ||
      !positive("max_deceleration_mps2", &config.max_deceleration_mps2) ||
      !positive("max_road_wheel_angle_deg", &config.max_road_wheel_angle_deg) ||
      !positive("max_steering_rate_deg_per_s", &config.max_steering_rate_deg_per_s)) {
    return false;
  }

  const json::Value* law = root.Find("command_law");
  if (law == nullptr) return fail("vehicle configuration: missing command_law");
  if (!law->IsString()) {
    return fail("vehicle configuration: command_law must be a string");
  }
  const std::string law_name = law->AsString("");
  if (law_name == "first_control") {
    config.law = CommandLaw::kFirstControl;
  } else if (law_name == "pure_pursuit") {
    config.law = CommandLaw::kPurePursuit;
  } else {
    return fail("vehicle configuration: unknown command_law '" + law_name +
                "' (first_control or pure_pursuit)");
  }

  if (out != nullptr) *out = config;
  return true;
}

bool LoadVehicleConfigFile(const std::string& path, VehicleConfig* out, std::string* error) {
  std::ifstream file(path);
  if (!file) {
    if (error != nullptr) *error = "cannot read vehicle configuration " + path;
    return false;
  }
  std::ostringstream contents;
  contents << file.rdbuf();
  return ParseVehicleConfig(contents.str(), out, error);
}

double FirstControlSteeringDeg(double wheelbase_m, double curvature) {
  return Degrees(std::atan(wheelbase_m * curvature));
}

double PurePursuitLookaheadM(double speed_kmh) {
  const double speed_mps = speed_kmh / 3.6;
  const double lookahead = 4.0 + 0.8 * speed_mps;
  return std::min(15.0, std::max(4.0, lookahead));
}

double PurePursuitSteeringDeg(const DrivingPlanPayload& plan, std::uint64_t k,
                              double speed_kmh, double wheelbase_m) {
  if (k >= kPlanSamples) k = kPlanSamples - 1;
  const PlanSample& reference = plan.samples[k];
  const double cosine = std::cos(reference.heading);
  const double sine = std::sin(reference.heading);

  // The plan's integrated path, shifted to the origin and heading of sample k.
  const auto shifted = [&](std::size_t index, double* x, double* y) {
    const double dx = static_cast<double>(plan.samples[index].x) - reference.x;
    const double dy = static_cast<double>(plan.samples[index].y) - reference.y;
    *x = cosine * dx + sine * dy;
    *y = -sine * dx + cosine * dy;
  };

  const double lookahead = PurePursuitLookaheadM(speed_kmh);
  std::size_t target = kPlanSamples - 1;  // the last sample when none is far enough
  for (std::size_t index = static_cast<std::size_t>(k) + 1; index < kPlanSamples; ++index) {
    double x = 0.0;
    double y = 0.0;
    shifted(index, &x, &y);
    if (std::hypot(x, y) >= lookahead) {
      target = index;
      break;
    }
  }

  double x = 0.0;
  double y = 0.0;
  shifted(target, &x, &y);
  const double distance = std::max(1.0, std::hypot(x, y));
  const double curvature = 2.0 * y / (distance * distance);
  return FirstControlSteeringDeg(wheelbase_m, curvature);
}

Commander::Commander(const VehicleConfig& config) : config_(config) {}

double Commander::LimitSteering(double raw_deg) {
  const double limit = config_.max_road_wheel_angle_deg;
  const double clamped = std::min(limit, std::max(-limit, raw_deg));
  const double max_step = config_.max_steering_rate_deg_per_s * kRateLimitStepSeconds;
  const double delta = clamped - previous_commanded_deg_;
  const double rate_limited =
      previous_commanded_deg_ + std::min(max_step, std::max(-max_step, delta));
  previous_commanded_deg_ = rate_limited;
  return rate_limited;
}

void Commander::EmitStopCommand(CommandStep* out, double monotonic_seconds) {
  // REQ-DRIVING-020: -min(4, max_deceleration). REQ-DRIVING-021: the steering
  // is held at the last value computed from a valid plan, not rate-limited.
  // The command names that plan (REQ-DRIVING-011), so the reference is frozen
  // at the stop; "none" when no driving command was ever computed.
  out->has_command = true;
  out->command = VehicleMotionCommandPayload{};
  out->command.acceleration =
      static_cast<float>(-std::min(kStopAccelerationMps2, config_.max_deceleration_mps2));
  out->command.steeringAngle =
      static_cast<float>(has_held_steering_ ? held_steering_deg_ : 0.0);
  out->command.productionTime = monotonic_seconds;
  SetId(out->command.planReference, kIdLength,
        has_held_steering_ ? held_plan_reference_ : std::string("none"));
  if (has_held_steering_) {
    out->has_plan = true;
    out->has_plan_capture = true;
    out->plan_capture_sim_ms = static_cast<std::uint64_t>(FrameMs(held_plan_frame_));
  }
}

CommandStep Commander::Step(Mode mode, const DrivingPlanPayload* newest_valid_plan,
                            std::uint64_t step_frame, const MotionObservation& motion,
                            double monotonic_seconds) {
  CommandStep out;
  out.step_frame = step_frame;
  out.step_capture_sim_ms = static_cast<std::uint64_t>(FrameMs(step_frame));
  out.law = config_.law;

  if (mode == Mode::kStarting) {
    return out;  // no command before the first driving step
  }

  if (mode != Mode::kDriving) {
    // kRefused, kStopResponse, kStandstill: the stop response, with the steering
    // held and the plan it was computed from named.
    EmitStopCommand(&out, monotonic_seconds);
    return out;
  }

  if (newest_valid_plan == nullptr) {
    // The supervisor never enters kDriving without a valid plan; should the
    // shell hand one over anyway, the command is the stop response and the
    // shell latches kPlanStale.
    out.plan_stale = true;
    EmitStopCommand(&out, monotonic_seconds);
    return out;
  }

  // REQ-DRIVING-026 re-checked at the command.
  if (AgeMs(step_frame, newest_valid_plan->frameIndex) > kPlanStaleMs) {
    out.plan_stale = true;
    EmitStopCommand(&out, monotonic_seconds);
    return out;
  }

  const std::size_t k =
      static_cast<std::size_t>(PlanSampleIndex(step_frame, newest_valid_plan->frameIndex));

  const double acceleration =
      std::min(config_.max_acceleration_mps2,
               std::max(-config_.max_deceleration_mps2,
                        static_cast<double>(newest_valid_plan->samples[k].acceleration)));

  double steering = 0.0;
  if (config_.law == CommandLaw::kFirstControl) {
    steering = FirstControlSteeringDeg(
        config_.wheelbase_m, static_cast<double>(newest_valid_plan->samples[k].curvature));
  } else {
    const double speed_kmh = motion.has_sample ? motion.sample.speed : 0.0;
    steering = PurePursuitSteeringDeg(*newest_valid_plan, k, speed_kmh, config_.wheelbase_m);
  }
  steering = LimitSteering(steering);
  held_steering_deg_ = steering;
  has_held_steering_ = true;
  held_plan_reference_ = PlanReferenceOf(*newest_valid_plan);
  held_plan_frame_ = newest_valid_plan->frameIndex;

  out.has_command = true;
  out.command = VehicleMotionCommandPayload{};
  out.command.acceleration = static_cast<float>(acceleration);
  out.command.steeringAngle = static_cast<float>(steering);
  out.command.productionTime = monotonic_seconds;
  SetId(out.command.planReference, kIdLength, PlanReferenceOf(*newest_valid_plan));
  out.has_plan = true;
  out.has_plan_capture = true;
  out.plan_capture_sim_ms = static_cast<std::uint64_t>(FrameMs(newest_valid_plan->frameIndex));
  out.sample_index = k;
  out.has_sample_index = true;
  return out;
}

// ------------------------------------------------------------------ records
namespace record {

std::string InPlan(const DrivingPlanPayload& plan) { return PlanPayloadJson(plan); }

std::string OutPlan(const DrivingPlanPayload& plan) { return PlanPayloadJson(plan); }

std::string OutMode(const DrivingModePayload& mode) {
  std::vector<std::string> fields = {
      Field("mode", Int(static_cast<std::int64_t>(mode.mode))),
      Field("modeName", Text(ModeName(mode.mode))),
      Field("cause", Int(static_cast<std::int64_t>(mode.cause))),
      Field("causeName", Text(CauseName(mode.cause))),
      Field("frameIndex", Int(static_cast<std::int64_t>(mode.frameIndex))),
      Field("captureTime", Number(mode.captureTime)),
      Field("decisionTime", Number(mode.decisionTime))};
  if (mode.mode == Mode::kRefused) {
    // A5: the refusal detail is carried only by the kRefused mode.
    fields.push_back(Field("checkpointExpectedSha256",
                           Text(FixedField(mode.checkpointExpectedSha256, kIdLength))));
    fields.push_back(Field("checkpointActualSha256",
                           Text(FixedField(mode.checkpointActualSha256, kIdLength))));
    fields.push_back(Field("refusalReason",
                           Text(FixedField(mode.refusalReason, sizeof mode.refusalReason))));
  }
  fields.push_back(Field("clocks", Clocks({{"captureTime", "simulation"},
                                           {"decisionTime", "monotonic"}})));
  return Join(fields);
}

std::string StopBegin(std::uint64_t frame, Cause cause, const char* source,
                      double monotonic_seconds) {
  return Object({Field("cause", Text(CauseName(cause))),
                 Field("causeValue", Int(static_cast<std::int64_t>(cause))),
                 Field("frame", Int(static_cast<std::int64_t>(frame))),
                 Field("capture_sim_ms", Int(FrameMs(frame))),
                 Field("source", Text(source != nullptr ? source : "")),
                 Field("decision_mono_s", Number(monotonic_seconds)),
                 Field("clocks", Clocks({{"capture_sim_ms", "simulation"},
                                         {"decision_mono_s", "monotonic"}}))});
}

std::string Standstill(std::uint64_t frame, Cause cause, double speed_kmh,
                       double monotonic_seconds) {
  return Object({Field("cause", Text(CauseName(cause))),
                 Field("causeValue", Int(static_cast<std::int64_t>(cause))),
                 Field("frame", Int(static_cast<std::int64_t>(frame))),
                 Field("capture_sim_ms", Int(FrameMs(frame))),
                 Field("speedKmh", Number(speed_kmh)),
                 Field("speedMps", Number(speed_kmh / 3.6)),
                 Field("source", Text("superviseLoop")),
                 Field("decision_mono_s", Number(monotonic_seconds)),
                 Field("clocks", Clocks({{"capture_sim_ms", "simulation"},
                                         {"decision_mono_s", "monotonic"}}))});
}

std::string OutCommand(const CommandStep& step) {
  std::vector<std::string> fields = {
      Field("acceleration", Number(step.command.acceleration)),
      Field("steeringAngle", Number(step.command.steeringAngle)),
      Field("productionTime", Number(step.command.productionTime)),
      Field("planReference", Text(FixedField(step.command.planReference, kIdLength))),
      Field("step_capture_sim_ms", Int(static_cast<std::int64_t>(step.step_capture_sim_ms))),
      Field("plan_capture_sim_ms",
            step.has_plan_capture ? Int(static_cast<std::int64_t>(step.plan_capture_sim_ms))
                                  : std::string("null")),
      Field("commandLaw", Text(LawName(static_cast<int>(step.law))))};
  if (step.has_sample_index) {
    fields.push_back(Field("sampleIndex", Int(static_cast<std::int64_t>(step.sample_index))));
  }
  fields.push_back(Field("clocks", Clocks({{"productionTime", "monotonic"},
                                           {"step_capture_sim_ms", "simulation"},
                                           {"plan_capture_sim_ms", "simulation"}})));
  return Join(fields);
}

std::string Condition(const StepConditions& conditions, const ConditionResult& result) {
  std::string names = "[";
  std::string values = "[";
  for (std::size_t i = 0; i < result.causes.size(); ++i) {
    if (i != 0) {
      names += ",";
      values += ",";
    }
    names += Text(CauseName(result.causes[i]));
    values += Int(static_cast<std::int64_t>(result.causes[i]));
  }
  names += "]";
  values += "]";
  return Object(
      {Field("frame", Int(static_cast<std::int64_t>(conditions.step_frame))),
       Field("sim_ms", Int(FrameMs(conditions.step_frame))),
       Field("bits", Int(static_cast<std::int64_t>(result.bits))),
       Field("causes", names), Field("causeValues", values),
       Field("input_conditions",
             Object({Field("bits", Int(static_cast<std::int64_t>(result.bits))),
                     Field("causes", names)})),
       Field("clocks", Clocks({{"sim_ms", "simulation"}}))});
}

std::string CheckpointRefusedError(const RefusalDetail& refusal) {
  return Object({Field("code", Text("checkpoint_refused")),
                 Field("expectedSha256", Text(refusal.expected_sha256)),
                 Field("actualSha256", Text(refusal.actual_sha256)),
                 Field("reason", Text(refusal.reason))});
}

}  // namespace record

}  // namespace de4sdv::driving::agent
