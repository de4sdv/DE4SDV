// Tests of the DE4SDV driving agent's pure decision logic (slice 10b, WP2).
//
// Build and run (from the library root):
//   g++ -std=c++17 -O2 -Wall -Wextra -Werror -I. -I<bench>/interfaces/include
//       tests/agent_logic_test.cpp agent_logic.cpp json_lite.cpp
//       -o .build/agent_logic_test
//   .build/agent_logic_test
//
// It also emits a scripted run for the Python record test
// (tests/test_records_against_evaluators.py):
//   .build/agent_logic_test --emit-scenario plan_stale <run_dir> <run_identity>
//   .build/agent_logic_test --emit-scenario plan_invalid <run_dir> <run_identity>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <limits>
#include <string>
#include <vector>

#include "agent_logic.h"
#include "de4sdv/driving/run_log.h"

using de4sdv::driving::Cause;
using de4sdv::driving::DrivingPlanPayload;
using de4sdv::driving::EgoMotionSamplePayload;
using de4sdv::driving::kIdLength;
using de4sdv::driving::kPlanSamples;
using de4sdv::driving::Mode;
using de4sdv::driving::RunLog;
using namespace de4sdv::driving::agent;

namespace {

int g_failures = 0;
int g_checks = 0;

void Check(bool condition, const char* expression, const char* file, int line) {
  ++g_checks;
  if (!condition) {
    ++g_failures;
    std::printf("FAIL %s:%d: %s\n", file, line, expression);
  }
}

void CheckNear(double actual, double expected, double tolerance, const char* expression,
               const char* file, int line) {
  ++g_checks;
  if (!(std::fabs(actual - expected) <= tolerance)) {
    ++g_failures;
    std::printf("FAIL %s:%d: %s (actual %.17g, expected %.17g, tolerance %.3g)\n", file, line,
                expression, actual, expected, tolerance);
  }
}

void CheckText(const std::string& actual, const std::string& expected, const char* expression,
               const char* file, int line) {
  ++g_checks;
  if (actual != expected) {
    ++g_failures;
    std::printf("FAIL %s:%d: %s (actual %s, expected %s)\n", file, line, expression,
                actual.c_str(), expected.c_str());
  }
}

void CheckContains(const std::string& haystack, const std::string& needle, const char* file,
                   int line) {
  ++g_checks;
  if (haystack.find(needle) == std::string::npos) {
    ++g_failures;
    std::printf("FAIL %s:%d: record does not contain %s\n      in %s\n", file, line,
                needle.c_str(), haystack.c_str());
  }
}

void CheckMissing(const std::string& haystack, const std::string& needle, const char* file,
                  int line) {
  ++g_checks;
  if (haystack.find(needle) != std::string::npos) {
    ++g_failures;
    std::printf("FAIL %s:%d: record contains %s\n      in %s\n", file, line, needle.c_str(),
                haystack.c_str());
  }
}

#define CHECK(condition) Check((condition), #condition, __FILE__, __LINE__)
#define CHECK_NEAR(actual, expected, tolerance) \
  CheckNear((actual), (expected), (tolerance), #actual " ~= " #expected, __FILE__, __LINE__)
#define CHECK_TEXT(actual, expected) CheckText((actual), (expected), #actual, __FILE__, __LINE__)
#define CHECK_CONTAINS(haystack, needle) CheckContains((haystack), (needle), __FILE__, __LINE__)
#define CHECK_MISSING(haystack, needle) CheckMissing((haystack), (needle), __FILE__, __LINE__)

constexpr const char* kRunIdentity = "0123456789abcdef";
constexpr double kFirstControl005Deg = 8.110047829419099;   // deg(atan(2.85 * 0.05))
constexpr double kFirstControl010Deg = 15.907551930525845;  // deg(atan(2.85 * 0.10))

// ------------------------------------------------------------------ fixtures
void SetField(char* destination, std::size_t capacity, const std::string& value) {
  std::memset(destination, 0, capacity);
  std::memcpy(destination, value.data(), std::min(value.size(), capacity - 1));
}

// Six configured 512x512 cameras, the rig of ICD 10 C2.
const CameraSize* StandardSizes() {
  static const CameraSize sizes[kCameraCount] = {
      {512, 512}, {512, 512}, {512, 512}, {512, 512}, {512, 512}, {512, 512}};
  return sizes;
}

DrivingPlanPayload MakePlan(std::uint64_t frame, double acceleration, double curvature,
                            std::uint32_t sample_count = static_cast<std::uint32_t>(kPlanSamples),
                            const std::string& identity = kRunIdentity) {
  DrivingPlanPayload plan{};
  plan.frameIndex = frame;
  plan.captureTime = FrameSeconds(frame);
  plan.productionTime = 1000.0 + FrameSeconds(frame);
  plan.horizon = 6.4f;
  plan.sampleCount = sample_count;
  for (std::size_t i = 0; i < kPlanSamples; ++i) {
    plan.samples[i].acceleration = static_cast<float>(acceleration);
    plan.samples[i].curvature = static_cast<float>(curvature);
    plan.samples[i].x = static_cast<float>((i + 1) * 0.5);
    plan.samples[i].y = 0.0f;
    plan.samples[i].heading = 0.0f;
  }
  SetField(plan.producer, kIdLength, "drivingAgent/inferPlan");
  SetField(plan.runRecord, kIdLength, identity);
  SetField(plan.planReference, kIdLength, identity + "/" + std::to_string(frame));
  return plan;
}

// An arc of radius R (metres), samples 0.5 m apart, starting at the origin.
DrivingPlanPayload MakeArcPlan(std::uint64_t frame, double radius) {
  DrivingPlanPayload plan = MakePlan(frame, 0.0, 1.0 / radius);
  for (std::size_t i = 0; i < kPlanSamples; ++i) {
    const double s = (i + 1) * 0.5;
    plan.samples[i].x = static_cast<float>(radius * std::sin(s / radius));
    plan.samples[i].y = static_cast<float>(radius * (1.0 - std::cos(s / radius)));
    plan.samples[i].heading = static_cast<float>(s / radius);
  }
  return plan;
}

StepConditions CleanConditions(std::uint64_t frame) {
  StepConditions conditions;
  conditions.step_frame = frame;
  for (std::size_t i = 0; i < kCameraCount; ++i) {
    conditions.cameras[i].present = true;
    conditions.cameras[i].empty = false;
    conditions.cameras[i].width = 512;
    conditions.cameras[i].height = 512;
    conditions.cameras[i].has_frame = true;
    conditions.cameras[i].frame_index = frame;
  }
  conditions.motion.has_sample = true;
  conditions.motion.frame_index = frame;
  conditions.motion.sample.speed = 36.0f;
  conditions.motion.sample.longitudinalAcceleration = 0.0f;
  conditions.motion.sample.lateralAcceleration = 0.0f;
  conditions.motion.sample.yawRate = 0.0f;
  conditions.motion.sample.captureTime = FrameSeconds(frame);
  conditions.route.has_announcement = true;
  conditions.route.corridor_points = 60;
  conditions.route.issue_time = FrameSeconds(frame);
  conditions.route.raster_corridor_cells = 100;
  return conditions;
}

ConditionResult JudgeClean(std::uint64_t frame) {
  return JudgeConditions(CleanConditions(frame), StandardSizes());
}

MotionObservation CleanMotion(std::uint64_t frame, double speed_kmh) {
  MotionObservation motion;
  motion.has_sample = true;
  motion.frame_index = frame;
  motion.sample.speed = static_cast<float>(speed_kmh);
  motion.sample.longitudinalAcceleration = 0.0f;
  motion.sample.lateralAcceleration = 0.0f;
  motion.sample.yawRate = 0.0f;
  motion.sample.captureTime = FrameSeconds(frame);
  return motion;
}

VehicleConfig DefaultConfig() {
  VehicleConfig config;
  config.wheelbase_m = 2.85;
  config.max_acceleration_mps2 = 3.0;
  config.max_deceleration_mps2 = 8.0;
  config.max_road_wheel_angle_deg = 35.0;
  config.max_steering_rate_deg_per_s = 180.0;
  config.law = CommandLaw::kFirstControl;
  return config;
}

std::string ConfigJson(const std::string& law = "first_control",
                       const std::string& wheelbase = "2.85",
                       const std::string& max_acceleration = "3.0",
                       const std::string& max_deceleration = "8.0",
                       const std::string& max_angle = "35.0",
                       const std::string& max_rate = "180.0") {
  return "{\"vehicle_blueprint\":\"vehicle.lincoln.mkz_2020\",\"wheelbase_m\":" + wheelbase +
         ",\"max_acceleration_mps2\":" + max_acceleration + ",\"max_deceleration_mps2\":" +
         max_deceleration + ",\"max_road_wheel_angle_deg\":" + max_angle +
         ",\"max_steering_rate_deg_per_s\":" + max_rate + ",\"command_law\":\"" + law +
         "\",\"longitudinal_controller\":{\"table\":[[-8.0,0.0,1.0],[3.0,0.75,0.0]],"
         "\"kp\":0.3,\"ki\":0.05,\"integrator_limit\":0.3}}";
}

// ------------------------------------------------------------------ times
void TestTimes() {
  CHECK(AgeMs(10, 10) == 0);
  CHECK(AgeMs(12, 10) == 200);
  CHECK(AgeMs(13, 10) == 300);
  CHECK(AgeMs(10, 13) == -300);  // a plan from the future is fresh, not stale
  CHECK(FrameMs(0) == 0);
  CHECK(FrameMs(63) == 6300);
  CHECK(FrameMs(600000) == 60000000);
  CHECK_NEAR(FrameSeconds(63), 6.3, 1e-15);
  CHECK_NEAR(FrameSeconds(0), 0.0, 0.0);
  CHECK(IssueTimeMs(6.3) == 6300);
  CHECK(IssueTimeMs(0.0) == 0);
  CHECK(IssueTimeMs(1.005) == 1005);
  CHECK_TEXT(ModeName(Mode::kStopResponse), "kStopResponse");
  CHECK_TEXT(CauseName(Cause::kPlanStale), "kPlanStale");
  CHECK_TEXT(CauseName(Cause::kCheckpointRefused), "kCheckpointRefused");
  CHECK_TEXT(LawName(static_cast<int>(CommandLaw::kPurePursuit)), "pure_pursuit");
  CHECK(CauseBit(Cause::kCameraMissing) == 2u);
  CHECK(CauseBit(Cause::kNone) == 1u);
  CHECK(CauseBit(Cause::kCameraStale) == 8u);
}

// ------------------------------------------------------------------ conditions
void TestConditionCameras() {
  const CameraSize* sizes = StandardSizes();
  {
    const ConditionResult result = JudgeConditions(CleanConditions(30), sizes);
    CHECK(!result.Any());
    CHECK(result.causes.empty());
    CHECK(result.Lowest() == Cause::kNone);
  }
  {
    // Age exactly 200 ms does not trigger; 300 ms does (REQ-DRIVING-023).
    StepConditions step = CleanConditions(30);
    for (std::size_t i = 0; i < kCameraCount; ++i) step.cameras[i].frame_index = 28;
    CHECK(!JudgeConditions(step, sizes).Has(Cause::kCameraStale));
    step = CleanConditions(30);
    for (std::size_t i = 0; i < kCameraCount; ++i) step.cameras[i].frame_index = 27;
    const ConditionResult stale = JudgeConditions(step, sizes);
    CHECK(stale.Has(Cause::kCameraStale));
    CHECK(stale.causes.size() == 1u);
    CHECK(stale.Lowest() == Cause::kCameraStale);
    CHECK(stale.bits == CauseBit(Cause::kCameraStale));
  }
  {
    // Only the affected camera sets a bit.
    StepConditions step = CleanConditions(30);
    step.cameras[4].frame_index = 20;  // rear, 1 s old
    const ConditionResult result = JudgeConditions(step, sizes);
    CHECK(result.Has(Cause::kCameraStale));
    CHECK(result.bits == CauseBit(Cause::kCameraStale));
  }
  {
    StepConditions step = CleanConditions(30);
    step.cameras[0].present = false;
    step.cameras[0].has_frame = false;  // no image, so no age to judge
    const ConditionResult result = JudgeConditions(step, sizes);
    CHECK(result.Has(Cause::kCameraMissing));
    CHECK(!result.Has(Cause::kCameraStale));
    CHECK(!result.Has(Cause::kCameraInvalid));
  }
  {
    StepConditions step = CleanConditions(30);
    step.cameras[1].empty = true;
    CHECK(JudgeConditions(step, sizes).Has(Cause::kCameraInvalid));
  }
  {
    StepConditions step = CleanConditions(30);
    step.cameras[2].width = 1024;
    CHECK(JudgeConditions(step, sizes).Has(Cause::kCameraInvalid));
  }
  {
    StepConditions step = CleanConditions(30);
    step.cameras[3].height = 480;
    CHECK(JudgeConditions(step, sizes).Has(Cause::kCameraInvalid));
  }
  {
    // A present image with no frame index cannot be dated: invalid, not fresh.
    StepConditions step = CleanConditions(30);
    step.cameras[5].has_frame = false;
    CHECK(JudgeConditions(step, sizes).Has(Cause::kCameraInvalid));
  }
  {
    // Two cameras, two different causes: both bits, ascending cause order.
    StepConditions step = CleanConditions(30);
    step.cameras[0].present = false;
    step.cameras[1].frame_index = 25;
    const ConditionResult result = JudgeConditions(step, sizes);
    CHECK(result.Has(Cause::kCameraMissing));
    CHECK(result.Has(Cause::kCameraStale));
    CHECK(result.causes.size() == 2u);
    CHECK(result.causes[0] == Cause::kCameraMissing);
    CHECK(result.causes[1] == Cause::kCameraStale);
    CHECK(result.Lowest() == Cause::kCameraMissing);
  }
}

void TestConditionMotionRoute() {
  const CameraSize* sizes = StandardSizes();
  {
    // No sample ever received: invalid (REQ-DRIVING-024).
    StepConditions step = CleanConditions(30);
    step.motion.has_sample = false;
    const ConditionResult result = JudgeConditions(step, sizes);
    CHECK(result.Has(Cause::kMotionInvalid));
    CHECK(!result.Has(Cause::kMotionStale));
  }
  {
    const double bad_values[] = {std::numeric_limits<double>::quiet_NaN(),
                                 std::numeric_limits<double>::infinity()};
    for (double bad : bad_values) {
      StepConditions step = CleanConditions(30);
      step.motion.sample.speed = static_cast<float>(bad);
      CHECK(JudgeConditions(step, sizes).Has(Cause::kMotionInvalid));
      step = CleanConditions(30);
      step.motion.sample.longitudinalAcceleration = static_cast<float>(bad);
      CHECK(JudgeConditions(step, sizes).Has(Cause::kMotionInvalid));
      step = CleanConditions(30);
      step.motion.sample.lateralAcceleration = static_cast<float>(bad);
      CHECK(JudgeConditions(step, sizes).Has(Cause::kMotionInvalid));
      step = CleanConditions(30);
      step.motion.sample.yawRate = static_cast<float>(bad);
      CHECK(JudgeConditions(step, sizes).Has(Cause::kMotionInvalid));
    }
  }
  {
    StepConditions step = CleanConditions(30);
    step.motion.frame_index = 28;  // 200 ms: not stale
    CHECK(!JudgeConditions(step, sizes).Has(Cause::kMotionStale));
    step.motion.frame_index = 27;  // 300 ms: stale
    const ConditionResult result = JudgeConditions(step, sizes);
    CHECK(result.Has(Cause::kMotionStale));
    CHECK(result.Lowest() == Cause::kMotionStale);
  }
  {
    // Route stale: no announcement at all.
    StepConditions step = CleanConditions(30);
    step.route.has_announcement = false;
    CHECK(JudgeConditions(step, sizes).Has(Cause::kRouteStale));
  }
  {
    // 1 000 ms old is fresh, 1 100 ms old is stale (REQ-DRIVING-025).
    StepConditions step = CleanConditions(30);
    step.route.issue_time = FrameSeconds(20);  // exactly 1 s
    CHECK(!JudgeConditions(step, sizes).Has(Cause::kRouteStale));
    step.route.issue_time = FrameSeconds(19);  // 1.1 s
    const ConditionResult result = JudgeConditions(step, sizes);
    CHECK(result.Has(Cause::kRouteStale));
    CHECK(result.Lowest() == Cause::kRouteStale);
  }
  {
    // A non-integer issue time rounds to milliseconds once.
    StepConditions step = CleanConditions(30);
    step.route.issue_time = 2.95;  // 2950 ms, step 3000 ms: 50 ms old
    CHECK(!JudgeConditions(step, sizes).Has(Cause::kRouteStale));
    step.route.issue_time = 1.95;  // 1950 ms: 1050 ms old
    CHECK(JudgeConditions(step, sizes).Has(Cause::kRouteStale));
  }
  {
    // Empty corridor: the announcement says zero points.
    StepConditions step = CleanConditions(30);
    step.route.corridor_points = 0;
    const ConditionResult result = JudgeConditions(step, sizes);
    CHECK(result.Has(Cause::kRouteEmpty));
    CHECK(!result.Has(Cause::kRouteStale));
    CHECK(result.Lowest() == Cause::kRouteEmpty);
  }
  {
    // Empty corridor: the step's raster has no corridor cell.
    StepConditions step = CleanConditions(30);
    step.route.raster_corridor_cells = 0;
    CHECK(JudgeConditions(step, sizes).Has(Cause::kRouteEmpty));
  }
  {
    // An empty announcement whose raster is also empty sets one bit, once.
    StepConditions step = CleanConditions(30);
    step.route.corridor_points = 0;
    step.route.raster_corridor_cells = 0;
    const ConditionResult result = JudgeConditions(step, sizes);
    CHECK(result.Has(Cause::kRouteEmpty));
    CHECK(result.causes.size() == 1u);
  }
  {
    // Every family at once: ascending cause order, camera first.
    StepConditions step = CleanConditions(30);
    step.cameras[0].present = false;
    step.motion.has_sample = false;
    step.route.corridor_points = 0;
    const ConditionResult result = JudgeConditions(step, sizes);
    CHECK(result.causes.size() == 3u);
    CHECK(result.causes[0] == Cause::kCameraMissing);
    CHECK(result.causes[1] == Cause::kMotionInvalid);
    CHECK(result.causes[2] == Cause::kRouteEmpty);
    CHECK(result.bits == (CauseBit(Cause::kCameraMissing) | CauseBit(Cause::kMotionInvalid) |
                          CauseBit(Cause::kRouteEmpty)));
  }
}

// ------------------------------------------------------------------ plan validity
void TestPlanValidity() {
  CHECK(IsPlanValid(MakePlan(10, 0.0, 0.0)));
  CHECK(IsPlanValid(MakePlan(10, -9.0, 9.0)));  // outside the limits is still well-formed
  CHECK(!IsPlanValid(MakePlan(10, 0.0, 0.0, 63)));
  CHECK(!IsPlanValid(MakePlan(10, 0.0, 0.0, 65)));
  CHECK(!IsPlanValid(MakePlan(10, 0.0, 0.0, 0)));

  DrivingPlanPayload nan_acceleration = MakePlan(10, 0.0, 0.0);
  nan_acceleration.samples[63].acceleration = std::numeric_limits<float>::quiet_NaN();
  CHECK(!IsPlanValid(nan_acceleration));

  DrivingPlanPayload inf_curvature = MakePlan(10, 0.0, 0.0);
  inf_curvature.samples[0].curvature = std::numeric_limits<float>::infinity();
  CHECK(!IsPlanValid(inf_curvature));

  // x, y and heading are not judged (REQ-DRIVING-027).
  DrivingPlanPayload pose_only = MakePlan(10, 0.0, 0.0);
  pose_only.samples[5].x = std::numeric_limits<float>::quiet_NaN();
  pose_only.samples[5].y = std::numeric_limits<float>::infinity();
  pose_only.samples[5].heading = std::numeric_limits<float>::quiet_NaN();
  CHECK(IsPlanValid(pose_only));
}

// ------------------------------------------------------------------ supervisor
void TestSupervisorStart() {
  Supervisor supervisor;
  const MotionObservation motion = CleanMotion(0, 36.0);

  SupervisorStep step = supervisor.Step(0, 10.0, JudgeClean(0), nullptr, motion);
  CHECK(step.mode == Mode::kStarting);
  CHECK(step.cause == Cause::kNone);
  CHECK(step.mode_changed);  // the first step reports the initial mode once
  CHECK(!step.stop_began);
  CHECK(step.newest_valid_plan == nullptr);
  CHECK(step.mode_payload.frameIndex == 0);
  CHECK_NEAR(step.mode_payload.captureTime, 0.0, 0.0);
  CHECK_NEAR(step.mode_payload.decisionTime, 10.0, 0.0);

  // A fault while starting is logged but starts no stop.
  StepConditions faulty = CleanConditions(1);
  faulty.cameras[0].present = false;
  const DrivingPlanPayload plan = MakePlan(1, 0.0, 0.0);
  step = supervisor.Step(1, 10.1, JudgeConditions(faulty, StandardSizes()), &plan, motion);
  CHECK(step.mode == Mode::kStarting);
  CHECK(step.cause == Cause::kNone);
  CHECK(!step.stop_began);
  CHECK(supervisor.has_valid_plan());  // the plan was retained even while starting

  // The first step with a valid plan and no input bit is the first driving step.
  step = supervisor.Step(2, 10.2, JudgeClean(2), &plan, motion);
  CHECK(step.mode == Mode::kDriving);
  CHECK(step.mode_changed);
  CHECK(!step.stop_began);
  CHECK(step.newest_valid_plan != nullptr);
}

void TestSupervisorPlanAge() {
  Supervisor supervisor;
  const DrivingPlanPayload plan = MakePlan(10, 0.0, 0.0);
  supervisor.Step(10, 1.0, JudgeClean(10), &plan, CleanMotion(10, 36.0));
  CHECK(supervisor.mode() == Mode::kDriving);

  // 200 ms and 300 ms are fresh; 400 ms is stale (REQ-DRIVING-026).
  SupervisorStep step = supervisor.Step(12, 1.2, JudgeClean(12), nullptr, CleanMotion(12, 36.0));
  CHECK(step.mode == Mode::kDriving);
  step = supervisor.Step(13, 1.3, JudgeClean(13), nullptr, CleanMotion(13, 36.0));
  CHECK(step.mode == Mode::kDriving);
  step = supervisor.Step(14, 1.4, JudgeClean(14), nullptr, CleanMotion(14, 36.0));
  CHECK(step.mode == Mode::kStopResponse);
  CHECK(step.cause == Cause::kPlanStale);
  CHECK(step.stop_began);
  CHECK(step.mode_changed);
}

void TestSupervisorStopLatching() {
  const DrivingPlanPayload plan = MakePlan(10, 0.0, 0.0);
  {
    // Any input bit in kDriving starts the stop.
    Supervisor supervisor;
    supervisor.Step(10, 1.0, JudgeClean(10), &plan, CleanMotion(10, 36.0));
    StepConditions faulty = CleanConditions(11);
    faulty.cameras[2].empty = true;
    SupervisorStep step = supervisor.Step(11, 1.1, JudgeConditions(faulty, StandardSizes()),
                                          nullptr, CleanMotion(11, 36.0));
    CHECK(step.mode == Mode::kStopResponse);
    CHECK(step.cause == Cause::kCameraInvalid);
    CHECK(step.stop_began);

    // Later causes never overwrite the latched one, even a lower value.
    StepConditions worse = CleanConditions(12);
    worse.cameras[0].present = false;
    worse.motion.has_sample = false;
    step = supervisor.Step(12, 1.2, JudgeConditions(worse, StandardSizes()), nullptr,
                           CleanMotion(12, 36.0));
    CHECK(step.mode == Mode::kStopResponse);
    CHECK(step.cause == Cause::kCameraInvalid);
    CHECK(!step.stop_began);
    CHECK(!step.mode_changed);
  }
  {
    // Two causes in one step: the lowest Cause value wins, deterministically.
    Supervisor supervisor;
    supervisor.Step(10, 1.0, JudgeClean(10), &plan, CleanMotion(10, 36.0));
    StepConditions step_conditions = CleanConditions(11);
    step_conditions.route.corridor_points = 0;
    step_conditions.motion.has_sample = false;
    step_conditions.cameras[0].present = false;
    const SupervisorStep step =
        supervisor.Step(11, 1.1, JudgeConditions(step_conditions, StandardSizes()), nullptr,
                        CleanMotion(11, 36.0));
    CHECK(step.cause == Cause::kCameraMissing);
    CHECK(step.stop_began);
  }
  {
    // An invalid plan arriving starts the stop and does not replace the newest
    // valid plan (REQ-DRIVING-027).
    Supervisor supervisor;
    const DrivingPlanPayload first = MakePlan(10, 0.0, 0.0);
    supervisor.Step(10, 1.0, JudgeClean(10), &first, CleanMotion(10, 36.0));
    DrivingPlanPayload invalid = MakePlan(11, 0.0, 0.0, 63);
    const SupervisorStep step =
        supervisor.Step(11, 1.1, JudgeClean(11), &invalid, CleanMotion(11, 36.0));
    CHECK(step.mode == Mode::kStopResponse);
    CHECK(step.cause == Cause::kPlanInvalid);
    CHECK(step.stop_began);
    CHECK(step.newest_valid_plan != nullptr);
    CHECK(step.newest_valid_plan->frameIndex == 10);
    CHECK(step.newest_valid_plan->sampleCount == 64);
  }
  {
    // A non-finite pair is an invalid plan too.
    Supervisor supervisor;
    const DrivingPlanPayload first = MakePlan(10, 0.0, 0.0);
    supervisor.Step(10, 1.0, JudgeClean(10), &first, CleanMotion(10, 36.0));
    DrivingPlanPayload invalid = MakePlan(11, 0.0, 0.0);
    invalid.samples[7].curvature = std::numeric_limits<float>::quiet_NaN();
    const SupervisorStep step =
        supervisor.Step(11, 1.1, JudgeClean(11), &invalid, CleanMotion(11, 36.0));
    CHECK(step.mode == Mode::kStopResponse);
    CHECK(step.cause == Cause::kPlanInvalid);
    CHECK(step.newest_valid_plan->frameIndex == 10);
  }
  {
    // An invalid plan while starting does not stop and does not drive.
    Supervisor supervisor;
    DrivingPlanPayload invalid = MakePlan(9, 0.0, 0.0, 63);
    const SupervisorStep step =
        supervisor.Step(9, 1.0, JudgeClean(9), &invalid, CleanMotion(9, 36.0));
    CHECK(step.mode == Mode::kStarting);
    CHECK(!step.stop_began);
    CHECK(step.newest_valid_plan == nullptr);
  }
}

void TestSupervisorStandstill() {
  Supervisor supervisor;
  const DrivingPlanPayload plan = MakePlan(10, 0.0, 0.0);
  supervisor.Step(10, 1.0, JudgeClean(10), &plan, CleanMotion(10, 36.0));

  StepConditions faulty = CleanConditions(11);
  faulty.cameras[0].present = false;
  SupervisorStep step = supervisor.Step(11, 1.1, JudgeConditions(faulty, StandardSizes()),
                                       nullptr, CleanMotion(11, 36.0));
  CHECK(step.mode == Mode::kStopResponse);

  // Exactly 0.1 km/h is not below the threshold.
  step = supervisor.Step(12, 1.2, JudgeConditions(faulty, StandardSizes()), nullptr,
                         CleanMotion(12, 0.1));
  CHECK(step.mode == Mode::kStopResponse);
  CHECK(!step.mode_changed);

  step = supervisor.Step(13, 1.3, JudgeConditions(faulty, StandardSizes()), nullptr,
                         CleanMotion(13, 0.09));
  CHECK(step.mode == Mode::kStandstill);
  CHECK(step.cause == Cause::kCameraMissing);
  CHECK(step.mode_changed);
  CHECK(!step.stop_began);  // the stop began at step 11, not here

  // Standstill is latched: a moving sample afterwards does not restart driving.
  step = supervisor.Step(14, 1.4, JudgeClean(14), &plan, CleanMotion(14, 60.0));
  CHECK(step.mode == Mode::kStandstill);
  CHECK(!step.mode_changed);
}

void TestSupervisorLatchApi() {
  {
    Supervisor supervisor;
    const DrivingPlanPayload plan = MakePlan(10, 0.0, 0.0);
    supervisor.Step(10, 1.0, JudgeClean(10), &plan, CleanMotion(10, 36.0));
    supervisor.Latch(Cause::kPlanStale, 11, 2.5);
    CHECK(supervisor.mode() == Mode::kStopResponse);
    CHECK(supervisor.cause() == Cause::kPlanStale);
    CHECK(supervisor.cause_frame() == 11);
    CHECK_NEAR(supervisor.cause_monotonic(), 2.5, 0.0);
    const SupervisorStep step =
        supervisor.Step(11, 2.5, JudgeClean(11), nullptr, CleanMotion(11, 36.0));
    CHECK(step.mode == Mode::kStopResponse);
    CHECK(step.stop_began);
    CHECK(step.cause == Cause::kPlanStale);

    // First cause wins here too.
    supervisor.Latch(Cause::kCameraMissing, 12, 2.6);
    CHECK(supervisor.cause() == Cause::kPlanStale);
  }
  {
    // Latch before the first driving step: kStarting becomes kStopResponse.
    Supervisor supervisor;
    supervisor.Latch(Cause::kRunEnd, 1, 1.0);
    const SupervisorStep step =
        supervisor.Step(1, 1.0, JudgeClean(1), nullptr, CleanMotion(1, 36.0));
    CHECK(step.mode == Mode::kStopResponse);
    CHECK(step.cause == Cause::kRunEnd);
    CHECK(step.stop_began);
  }
  {
    // A latch while the vehicle already stands still: the stop begins and the
    // same step reports the standstill (REQ-DRIVING-022).
    Supervisor supervisor;
    supervisor.Latch(Cause::kRunEnd, 1, 1.0);
    const SupervisorStep step =
        supervisor.Step(1, 1.0, JudgeClean(1), nullptr, CleanMotion(1, 0.0));
    CHECK(step.mode == Mode::kStandstill);
    CHECK(step.cause == Cause::kRunEnd);
    CHECK(step.stop_began);
  }
}

void TestSupervisorEndRun() {
  {
    Supervisor supervisor;
    const DrivingPlanPayload plan = MakePlan(10, 0.0, 0.0);
    supervisor.Step(10, 1.0, JudgeClean(10), &plan, CleanMotion(10, 36.0));
    supervisor.EndRun(20, 3.0);
    CHECK(supervisor.mode() == Mode::kStopResponse);
    CHECK(supervisor.cause() == Cause::kRunEnd);
    const SupervisorStep step =
        supervisor.Step(20, 3.0, JudgeClean(20), nullptr, CleanMotion(20, 36.0));
    CHECK(step.stop_began);
    CHECK(step.cause == Cause::kRunEnd);
  }
  {
    // A latched stop wins over the end of the run.
    Supervisor supervisor;
    const DrivingPlanPayload plan = MakePlan(9, 0.0, 0.0);
    StepConditions faulty = CleanConditions(10);
    faulty.cameras[0].present = false;
    supervisor.Step(9, 1.0, JudgeClean(9), &plan, CleanMotion(9, 36.0));
    supervisor.Step(10, 1.1, JudgeConditions(faulty, StandardSizes()), nullptr,
                    CleanMotion(10, 36.0));
    supervisor.EndRun(11, 1.2);
    CHECK(supervisor.mode() == Mode::kStopResponse);
    CHECK(supervisor.cause() == Cause::kCameraMissing);
  }
  {
    // Standstill stays standstill at the end of the run.
    Supervisor supervisor;
    const DrivingPlanPayload plan = MakePlan(10, 0.0, 0.0);
    StepConditions faulty = CleanConditions(11);
    faulty.cameras[0].present = false;
    supervisor.Step(10, 1.0, JudgeClean(10), &plan, CleanMotion(10, 36.0));
    supervisor.Step(11, 1.1, JudgeConditions(faulty, StandardSizes()), nullptr,
                    CleanMotion(11, 36.0));
    supervisor.Step(12, 1.2, JudgeConditions(faulty, StandardSizes()), nullptr,
                    CleanMotion(12, 0.0));
    supervisor.EndRun(13, 1.3);
    CHECK(supervisor.mode() == Mode::kStandstill);
    CHECK(supervisor.cause() == Cause::kCameraMissing);
  }
}

void TestSupervisorRefusal() {
  RefusalDetail refusal;
  refusal.refused = true;
  refusal.expected_sha256 = std::string(64, '1');
  refusal.actual_sha256 = std::string(64, '2');
  refusal.reason = "mismatch";
  Supervisor supervisor(refusal);

  for (std::uint64_t frame = 0; frame < 3; ++frame) {
    const SupervisorStep step =
        supervisor.Step(frame, 1.0 + static_cast<double>(frame), JudgeClean(frame), nullptr,
                        CleanMotion(frame, 0.0));
    CHECK(step.mode == Mode::kRefused);
    CHECK(step.cause == Cause::kCheckpointRefused);
    CHECK(!step.stop_began);
    CHECK(step.newest_valid_plan == nullptr);
    CHECK(step.mode_payload.mode == Mode::kRefused);
    CHECK(step.mode_payload.cause == Cause::kCheckpointRefused);
    CHECK(step.mode_payload.checkpointExpectedSha256[63] == '1');
    CHECK(step.mode_payload.checkpointActualSha256[63] == '2');
    CHECK_TEXT(std::string(step.mode_payload.refusalReason), "mismatch");
  }

  // A valid plan and a fault cannot move a refused run.
  const DrivingPlanPayload plan = MakePlan(3, 0.0, 0.0);
  StepConditions faulty = CleanConditions(3);
  faulty.cameras[0].present = false;
  SupervisorStep step = supervisor.Step(3, 4.0, JudgeConditions(faulty, StandardSizes()), &plan,
                                       CleanMotion(3, 0.0));
  CHECK(step.mode == Mode::kRefused);
  CHECK(step.cause == Cause::kCheckpointRefused);

  // The latch API cannot overwrite the refusal.
  supervisor.Latch(Cause::kCameraMissing, 4, 4.1);
  CHECK(supervisor.cause() == Cause::kCheckpointRefused);

  // Non-refused supervisors carry zero refusal fields.
  Supervisor normal;
  const SupervisorStep normal_step =
      normal.Step(0, 1.0, JudgeClean(0), nullptr, CleanMotion(0, 0.0));
  CHECK(normal_step.mode_payload.checkpointExpectedSha256[0] == '\0');
  CHECK(normal_step.mode_payload.refusalReason[0] == '\0');
}

// ------------------------------------------------------------------ commander
void TestCommanderStarting() {
  Commander commander(DefaultConfig());
  const CommandStep step =
      commander.Step(Mode::kStarting, nullptr, 5, CleanMotion(5, 0.0), 2.0);
  CHECK(!step.has_command);
  CHECK(step.step_frame == 5);
  CHECK(step.step_capture_sim_ms == 500);
  CHECK(!step.has_plan);
  CHECK(!step.plan_stale);
  CHECK_TEXT(LawName(static_cast<int>(step.law)), "first_control");
}

void TestCommanderDriving() {
  Commander commander(DefaultConfig());
  DrivingPlanPayload plan = MakePlan(10, 0.0, 0.05);
  plan.samples[0].acceleration = -9.0f;   // below the deceleration limit
  plan.samples[1].acceleration = 9.0f;    // above the acceleration limit
  plan.samples[2].acceleration = 1.5f;    // inside
  plan.samples[3].acceleration = -2.0f;   // inside

  CommandStep step = commander.Step(Mode::kDriving, &plan, 10, CleanMotion(10, 36.0), 5.0);
  CHECK(step.has_command);
  CHECK_NEAR(step.command.acceleration, -8.0, 1e-6);
  CHECK(step.sample_index == 0);
  CHECK(step.has_sample_index);
  CHECK(step.step_capture_sim_ms == 1000);
  CHECK(step.plan_capture_sim_ms == 1000);
  CHECK(step.has_plan_capture);
  CHECK(!step.plan_stale);
  CHECK_NEAR(step.command.productionTime, 5.0, 0.0);
  CHECK_TEXT(std::string(step.command.planReference), "0123456789abcdef/10");
  CHECK_NEAR(step.command.steeringAngle, kFirstControl005Deg, 1e-5);

  step = commander.Step(Mode::kDriving, &plan, 11, CleanMotion(11, 36.0), 5.1);
  CHECK(step.sample_index == 1);
  CHECK_NEAR(step.command.acceleration, 3.0, 1e-6);
  // The rate limiter holds the change to 18 deg per step; the target is the same,
  // so the command stays at the previous value.
  CHECK_NEAR(step.command.steeringAngle, kFirstControl005Deg, 1e-5);

  step = commander.Step(Mode::kDriving, &plan, 12, CleanMotion(12, 36.0), 5.2);
  CHECK(step.sample_index == 2);
  CHECK_NEAR(step.command.acceleration, 1.5, 1e-6);

  step = commander.Step(Mode::kDriving, &plan, 13, CleanMotion(13, 36.0), 5.3);
  CHECK(step.sample_index == 3);
  CHECK_NEAR(step.command.acceleration, -2.0, 1e-6);
}

void TestCommanderSampleIndexClamp() {
  // The clamp itself: 0 at the bottom, 63 at the top.
  CHECK(PlanSampleIndex(10, 10) == 0);
  CHECK(PlanSampleIndex(9, 10) == 0);    // a plan from the future
  CHECK(PlanSampleIndex(13, 10) == 3);   // the last index a fresh plan can reach
  CHECK(PlanSampleIndex(73, 10) == 63);
  CHECK(PlanSampleIndex(200, 10) == 63);

  Commander commander(DefaultConfig());
  // A plan from a later frame than the step: k clamps to 0.
  DrivingPlanPayload future = MakePlan(10, 0.0, 0.0);
  future.samples[0].acceleration = 1.0f;
  future.samples[63].acceleration = -3.0f;
  CommandStep step = commander.Step(Mode::kDriving, &future, 9, CleanMotion(9, 36.0), 1.0);
  CHECK(step.sample_index == 0);
  CHECK_NEAR(step.command.acceleration, 1.0, 1e-6);

  // The upper clamp (63) is defensive: a plan more than 300 ms old never reaches
  // the sample selection (REQ-DRIVING-026 stops first), so k in kDriving is 0..3.
  // k = 3 is the last reachable index, and sample 3 is the one commanded.
  DrivingPlanPayload plan = MakePlan(0, 0.0, 0.0);
  for (std::size_t i = 0; i < kPlanSamples; ++i) plan.samples[i].acceleration = 0.0f;
  plan.samples[3].acceleration = -3.0f;
  step = commander.Step(Mode::kDriving, &plan, 3, CleanMotion(3, 36.0), 1.0);
  CHECK(step.sample_index == 3);
  CHECK_NEAR(step.command.acceleration, -3.0, 1e-6);
}

void TestCommanderPlanStale() {
  Commander commander(DefaultConfig());
  const DrivingPlanPayload plan = MakePlan(10, 0.0, 0.0);
  CommandStep step = commander.Step(Mode::kDriving, &plan, 12, CleanMotion(12, 36.0), 1.0);
  CHECK(!step.plan_stale);
  CHECK(step.has_command);
  step = commander.Step(Mode::kDriving, &plan, 13, CleanMotion(13, 36.0), 1.0);
  CHECK(!step.plan_stale);
  step = commander.Step(Mode::kDriving, &plan, 14, CleanMotion(14, 36.0), 1.0);
  CHECK(step.plan_stale);
  CHECK_NEAR(step.command.acceleration, -4.0, 1e-6);
  CHECK(step.has_plan);
  CHECK(step.plan_capture_sim_ms == 1000);

  // No plan handed over in kDriving: the stop response, kPlanStale reported. The
  // held steering was computed from plan 10, so the command names plan 10
  // (REQ-DRIVING-011; orchestrator review, C2). With no driving command ever
  // computed, the reference is "none" (TestCommanderStopModes, fresh commander).
  const CommandStep no_plan =
      commander.Step(Mode::kDriving, nullptr, 20, CleanMotion(20, 36.0), 1.0);
  CHECK(no_plan.plan_stale);
  CHECK_NEAR(no_plan.command.acceleration, -4.0, 1e-6);
  CHECK_TEXT(std::string(no_plan.command.planReference), "0123456789abcdef/10");
  CHECK(no_plan.has_plan_capture && no_plan.plan_capture_sim_ms == 1000);
  Commander never_drove(DefaultConfig());
  const CommandStep none =
      never_drove.Step(Mode::kDriving, nullptr, 20, CleanMotion(20, 36.0), 1.0);
  CHECK(none.plan_stale);
  CHECK_TEXT(std::string(none.command.planReference), "none");
  CHECK(!none.has_plan_capture);
}

void TestCommanderStopModes() {
  Commander commander(DefaultConfig());
  const DrivingPlanPayload plan = MakePlan(10, 0.0, 0.1);
  const CommandStep driving =
      commander.Step(Mode::kDriving, &plan, 10, CleanMotion(10, 36.0), 1.0);
  CHECK_NEAR(driving.command.steeringAngle, kFirstControl010Deg, 1e-5);

  const Mode stop_modes[] = {Mode::kStopResponse, Mode::kStandstill, Mode::kRefused};
  for (Mode mode : stop_modes) {
    const CommandStep step = commander.Step(mode, &plan, 11, CleanMotion(11, 36.0), 1.1);
    CHECK(step.has_command);
    CHECK_NEAR(step.command.acceleration, -4.0, 1e-6);
    CHECK_NEAR(step.command.steeringAngle, kFirstControl010Deg, 1e-5);  // held, not rate-limited
    CHECK_TEXT(std::string(step.command.planReference), "0123456789abcdef/10");
  }

  // The stop is capped by the vehicle's deceleration limit.
  VehicleConfig gentle = DefaultConfig();
  gentle.max_deceleration_mps2 = 2.0;
  Commander gentle_commander(gentle);
  const CommandStep capped =
      gentle_commander.Step(Mode::kStopResponse, &plan, 12, CleanMotion(12, 36.0), 1.2);
  CHECK_NEAR(capped.command.acceleration, -2.0, 1e-6);

  // With no plan ever, the steer is 0 and the reference is "none".
  Commander fresh(DefaultConfig());
  const CommandStep no_plan =
      fresh.Step(Mode::kStopResponse, nullptr, 1, CleanMotion(1, 0.0), 1.0);
  CHECK_NEAR(no_plan.command.steeringAngle, 0.0, 0.0);
  CHECK_TEXT(std::string(no_plan.command.planReference), "none");
  CHECK(!no_plan.has_plan_capture);

  // Orchestrator review (C2 resolved): a stop command names the plan its held
  // steering was computed from (REQ-021, -032), frozen when the stop begins, never
  // a plan captured later (VC-022: no command from a plan made after T0).
  const DrivingPlanPayload later = MakePlan(12, 0.0, 0.1);
  const CommandStep after =
      commander.Step(Mode::kStopResponse, &later, 13, CleanMotion(13, 36.0), 1.3);
  CHECK_TEXT(std::string(after.command.planReference), "0123456789abcdef/10");
  CHECK(after.has_plan_capture && after.plan_capture_sim_ms == 1000);
  CHECK_NEAR(after.command.steeringAngle, kFirstControl010Deg, 1e-5);
}

// Orchestrator review: inferPlan keeps planning after the stop began; every stop
// command keeps naming the last plan a driving command was computed from.
void TestStopReferenceFrozenInScenario() {
  Supervisor supervisor;
  Commander commander(DefaultConfig());
  std::uint64_t stop_frame = 0;
  std::string driving_reference;
  for (std::uint64_t frame = 100; frame < 130; ++frame) {
    StepConditions conditions = CleanConditions(frame);
    if (frame >= 115) conditions.cameras[2].present = false;   // camera fault from 115
    const ConditionResult judged = JudgeConditions(conditions, StandardSizes());
    const DrivingPlanPayload plan = MakePlan(frame, 0.5, 0.02);  // plans every step, also after the stop
    const SupervisorStep decision =
        supervisor.Step(frame, 1.0 + 0.1 * frame, judged, &plan, CleanMotion(frame, 36.0));
    const CommandStep command = commander.Step(decision.mode, decision.newest_valid_plan, frame,
                                               CleanMotion(frame, 36.0), 1.0 + 0.1 * frame);
    if (decision.mode == Mode::kDriving) driving_reference = std::string(command.command.planReference);
    if (decision.stop_began) stop_frame = frame;
    if (stop_frame != 0 && frame >= stop_frame) {
      CHECK_TEXT(std::string(command.command.planReference), "0123456789abcdef/114");
      CHECK(command.has_plan_capture && command.plan_capture_sim_ms == 11400);
      CHECK(static_cast<std::int64_t>(command.plan_capture_sim_ms) < FrameMs(stop_frame));
    }
  }
  CHECK(stop_frame == 115);
  CHECK_TEXT(driving_reference, "0123456789abcdef/114");
}

// Orchestrator review (C3 resolved): within one step, the input causes first,
// then the plan that arrived in this step, then the age of the newest valid plan.
void TestPlanInvalidOutranksStaleInOneStep() {
  Supervisor supervisor;
  const DrivingPlanPayload valid = MakePlan(200, 0.0, 0.0);
  supervisor.Step(200, 20.0, JudgeClean(200), &valid, CleanMotion(200, 36.0));
  CHECK(supervisor.mode() == Mode::kDriving);
  for (std::uint64_t frame = 201; frame <= 203; ++frame) {
    supervisor.Step(frame, 20.0 + 0.1 * (frame - 200), JudgeClean(frame), nullptr, CleanMotion(frame, 36.0));
  }
  CHECK(supervisor.mode() == Mode::kDriving);  // 300 ms old at 203: not yet stale
  DrivingPlanPayload invalid = MakePlan(204, 0.0, 0.0);
  invalid.samples[7].curvature = std::numeric_limits<float>::quiet_NaN();
  const SupervisorStep decision =
      supervisor.Step(204, 20.4, JudgeClean(204), &invalid, CleanMotion(204, 36.0));
  CHECK(decision.stop_began);
  CHECK(decision.cause == Cause::kPlanInvalid);  // not kPlanStale (400 ms old in the same step)
  // An input cause still outranks both plan causes.
  Supervisor other;
  other.Step(300, 30.0, JudgeClean(300), &valid, CleanMotion(300, 36.0));
  StepConditions faulty = CleanConditions(301);
  faulty.motion.sample.speed = std::numeric_limits<float>::infinity();
  const SupervisorStep both =
      other.Step(301, 30.1, JudgeConditions(faulty, StandardSizes()), &invalid, CleanMotion(301, 36.0));
  CHECK(both.cause == Cause::kMotionInvalid);
}

void TestCommanderLimits() {
  Commander commander(DefaultConfig());
  DrivingPlanPayload plan = MakePlan(10, 0.0, 10.0);  // atan(28.5) = 88 deg, over the limit

  CommandStep step = commander.Step(Mode::kDriving, &plan, 10, CleanMotion(10, 36.0), 1.0);
  CHECK_NEAR(step.command.steeringAngle, 18.0, 1e-6);  // rate limit, not angle limit

  for (int i = 0; i < 10; ++i) {
    step = commander.Step(Mode::kDriving, &plan, static_cast<std::uint64_t>(11 + i),
                          CleanMotion(11 + i, 36.0), 1.1);
  }
  CHECK_NEAR(step.command.steeringAngle, 35.0, 1e-6);  // the road-wheel limit holds

  // The rate limit is quantised by one step (18 deg at 180 deg/s).
  VehicleConfig slow = DefaultConfig();
  slow.max_steering_rate_deg_per_s = 50.0;  // 5 deg per step
  Commander slow_commander(slow);
  const DrivingPlanPayload gentle = MakePlan(0, 0.0, 0.1);
  const CommandStep first =
      slow_commander.Step(Mode::kDriving, &gentle, 0, CleanMotion(0, 36.0), 1.0);
  CHECK_NEAR(first.command.steeringAngle, 5.0, 1e-6);
  const CommandStep second =
      slow_commander.Step(Mode::kDriving, &gentle, 1, CleanMotion(1, 36.0), 1.1);
  CHECK_NEAR(second.command.steeringAngle, 10.0, 1e-6);

  // A negative curvature turns the other way and stops at the negative limit.
  const DrivingPlanPayload left = MakePlan(0, 0.0, -10.0);
  Commander negative(DefaultConfig());
  CommandStep negative_step =
      negative.Step(Mode::kDriving, &left, 0, CleanMotion(0, 36.0), 1.0);
  CHECK_NEAR(negative_step.command.steeringAngle, -18.0, 1e-6);
  for (int i = 0; i < 10; ++i) {
    negative_step = negative.Step(Mode::kDriving, &left, static_cast<std::uint64_t>(1 + i),
                                  CleanMotion(1 + i, 36.0), 1.1);
  }
  CHECK_NEAR(negative_step.command.steeringAngle, -35.0, 1e-6);
}

void TestCommanderPurePursuit() {
  CHECK_NEAR(PurePursuitLookaheadM(0.0), 4.0, 0.0);
  CHECK_NEAR(PurePursuitLookaheadM(18.0), 8.0, 1e-12);   // 5 m/s
  CHECK_NEAR(PurePursuitLookaheadM(45.0), 14.0, 1e-12);  // 12.5 m/s
  CHECK_NEAR(PurePursuitLookaheadM(72.0), 15.0, 0.0);    // 20 m/s clamps to 15

  // On a constant-radius arc the pure-pursuit angle equals the arc's own angle.
  const DrivingPlanPayload arc = MakeArcPlan(0, 20.0);
  CHECK_NEAR(PurePursuitSteeringDeg(arc, 0, 0.0, 2.85), kFirstControl005Deg, 1e-5);
  CHECK_NEAR(PurePursuitSteeringDeg(arc, 10, 72.0, 2.85), kFirstControl005Deg, 1e-5);

  // A straight run has no steering.
  const DrivingPlanPayload straight = MakePlan(0, 0.0, 0.0);
  CHECK_NEAR(PurePursuitSteeringDeg(straight, 0, 36.0, 2.85), 0.0, 1e-12);

  // The lookahead changes the command on a path whose lateral offset appears
  // further ahead than the short lookahead reaches.
  DrivingPlanPayload kinked = MakePlan(0, 0.0, 0.0);
  for (std::size_t i = 0; i < kPlanSamples; ++i) {
    if (i < 20) {
      kinked.samples[i].x = static_cast<float>((i + 1) * 0.5);
      kinked.samples[i].y = 0.0f;
    } else {
      kinked.samples[i].x = static_cast<float>(10.0 + 0.5 * static_cast<double>(i - 19));
      kinked.samples[i].y = static_cast<float>(0.3 * static_cast<double>(i - 19));
    }
    kinked.samples[i].heading = 0.0f;
  }
  const double short_lookahead = PurePursuitSteeringDeg(kinked, 0, 0.0, 2.85);
  const double long_lookahead = PurePursuitSteeringDeg(kinked, 0, 72.0, 2.85);
  CHECK_NEAR(short_lookahead, 0.0, 1e-12);
  CHECK(long_lookahead > 1.0);

  // Degenerate path (every sample at the origin): no NaN, no steering.
  DrivingPlanPayload degenerate = MakePlan(0, 0.0, 0.0);
  for (std::size_t i = 0; i < kPlanSamples; ++i) {
    degenerate.samples[i].x = 0.0f;
    degenerate.samples[i].y = 0.0f;
    degenerate.samples[i].heading = 0.0f;
  }
  CHECK_NEAR(PurePursuitSteeringDeg(degenerate, 0, 0.0, 2.85), 0.0, 0.0);

  // Through the Commander, the configured law decides the steering.
  VehicleConfig config = DefaultConfig();
  config.law = CommandLaw::kPurePursuit;
  Commander commander(config);
  const DrivingPlanPayload plan = MakeArcPlan(10, 20.0);
  const CommandStep step =
      commander.Step(Mode::kDriving, &plan, 10, CleanMotion(10, 36.0), 1.0);
  CHECK_TEXT(LawName(static_cast<int>(step.law)), "pure_pursuit");
  CHECK_NEAR(step.command.steeringAngle, kFirstControl005Deg, 1e-5);
}

// ------------------------------------------------------------------ config
void TestVehicleConfig() {
  VehicleConfig config;
  std::string error;
  CHECK(ParseVehicleConfig(ConfigJson(), &config, &error));
  CHECK_TEXT(error, "");
  CHECK_NEAR(config.wheelbase_m, 2.85, 0.0);
  CHECK_NEAR(config.max_acceleration_mps2, 3.0, 0.0);
  CHECK_NEAR(config.max_deceleration_mps2, 8.0, 0.0);
  CHECK_NEAR(config.max_road_wheel_angle_deg, 35.0, 0.0);
  CHECK_NEAR(config.max_steering_rate_deg_per_s, 180.0, 0.0);
  CHECK(config.law == CommandLaw::kFirstControl);

  CHECK(ParseVehicleConfig(ConfigJson("pure_pursuit"), &config, &error));
  CHECK(config.law == CommandLaw::kPurePursuit);

  // Missing values, non-positive values and unknown laws are rejected.
  CHECK(!ParseVehicleConfig(ConfigJson("first_control", "0"), &config, &error));
  CHECK(error.find("wheelbase_m") != std::string::npos);
  CHECK(!ParseVehicleConfig(ConfigJson("first_control", "-2.85"), &config, &error));
  CHECK(error.find("wheelbase_m") != std::string::npos);
  CHECK(!ParseVehicleConfig(ConfigJson("first_control", "2.85", "0"), &config, &error));
  CHECK(error.find("max_acceleration_mps2") != std::string::npos);
  CHECK(!ParseVehicleConfig(ConfigJson("first_control", "2.85", "3.0", "-8.0"), &config, &error));
  CHECK(error.find("max_deceleration_mps2") != std::string::npos);
  CHECK(
      !ParseVehicleConfig(ConfigJson("first_control", "2.85", "3.0", "8.0", "0"), &config, &error));
  CHECK(error.find("max_road_wheel_angle_deg") != std::string::npos);
  CHECK(!ParseVehicleConfig(ConfigJson("first_control", "2.85", "3.0", "8.0", "35.0", "0"),
                            &config, &error));
  CHECK(error.find("max_steering_rate_deg_per_s") != std::string::npos);
  CHECK(!ParseVehicleConfig(ConfigJson("stanley"), &config, &error));
  CHECK(error.find("command_law") != std::string::npos);
  CHECK(!ParseVehicleConfig("{}", &config, &error));
  CHECK(error.find("wheelbase_m") != std::string::npos);
  CHECK(!ParseVehicleConfig("not json", &config, &error));
  CHECK(!error.empty());
  CHECK(!ParseVehicleConfig("{\"wheelbase_m\":\"2.85\"}", &config, &error));
  CHECK(error.find("wheelbase_m") != std::string::npos);

  // The ICD section 5 document without command_law is rejected too.
  CHECK(!ParseVehicleConfig(
      "{\"wheelbase_m\":2.85,\"max_acceleration_mps2\":3.0,\"max_deceleration_mps2\":8.0,"
      "\"max_road_wheel_angle_deg\":35.0,\"max_steering_rate_deg_per_s\":180.0}",
      &config, &error));
  CHECK(error.find("command_law") != std::string::npos);
}

// ------------------------------------------------------------------ records
void TestRecords() {
  {
    const DrivingPlanPayload plan = MakePlan(63, 1.0, 0.02);
    const std::string json = record::InPlan(plan);
    CHECK_CONTAINS(json, "\"frameIndex\":63");
    CHECK_CONTAINS(json, "\"captureTime\":");
    CHECK_CONTAINS(json, "\"sampleCount\":64");
    CHECK_CONTAINS(json, "\"producer\":\"drivingAgent/inferPlan\"");
    CHECK_CONTAINS(json, "\"runRecord\":\"0123456789abcdef\"");
    CHECK_CONTAINS(json, "\"planReference\":\"0123456789abcdef/63\"");
    CHECK_CONTAINS(json,
                   "\"clocks\":{\"captureTime\":\"simulation\",\"productionTime\":\"monotonic\"}");
    CHECK_CONTAINS(json, "\"samples\":[");
    int sample_objects = 0;
    for (std::size_t at = json.find("\"acceleration\":");
         at != std::string::npos; at = json.find("\"acceleration\":", at + 1)) {
      ++sample_objects;
    }
    CHECK(sample_objects == 64);  // one per plan sample, none at plan level
  }
  {
    // Non-finite sample values become JSON null; the evaluators read null as NaN.
    DrivingPlanPayload plan = MakePlan(10, 0.0, 0.0);
    plan.samples[0].acceleration = std::numeric_limits<float>::quiet_NaN();
    const std::string json = record::InPlan(plan);
    CHECK_CONTAINS(json, "\"acceleration\":null");
    CHECK_MISSING(json, "\"acceleration\":nan");
    CHECK_MISSING(json, "\"acceleration\":inf");
  }
  {
    de4sdv::driving::DrivingModePayload mode{};
    mode.mode = Mode::kStopResponse;
    mode.cause = Cause::kCameraStale;
    mode.frameIndex = 63;
    mode.captureTime = FrameSeconds(63);
    mode.decisionTime = 1234.5;
    const std::string json = record::OutMode(mode);
    CHECK_CONTAINS(json, "\"mode\":2");
    CHECK_CONTAINS(json, "\"modeName\":\"kStopResponse\"");
    CHECK_CONTAINS(json, "\"cause\":3");
    CHECK_CONTAINS(json, "\"causeName\":\"kCameraStale\"");
    CHECK_CONTAINS(json, "\"frameIndex\":63");
    CHECK_CONTAINS(json, "\"decisionTime\":1234.5");
    CHECK_CONTAINS(json,
                   "\"clocks\":{\"captureTime\":\"simulation\",\"decisionTime\":\"monotonic\"}");
    CHECK_MISSING(json, "checkpointExpectedSha256");
  }
  {
    RefusalDetail refusal;
    refusal.refused = true;
    refusal.expected_sha256 = std::string(64, 'a');
    refusal.actual_sha256 = std::string(64, 'b');
    refusal.reason = "mismatch";
    Supervisor supervisor(refusal);
    const SupervisorStep step =
        supervisor.Step(0, 1.0, JudgeClean(0), nullptr, CleanMotion(0, 0.0));
    const std::string json = record::OutMode(step.mode_payload);
    CHECK_CONTAINS(json, "\"mode\":4");
    CHECK_CONTAINS(json, "\"cause\":11");
    CHECK_CONTAINS(json, "\"checkpointExpectedSha256\":\"" + std::string(64, 'a') + "\"");
    CHECK_CONTAINS(json, "\"checkpointActualSha256\":\"" + std::string(64, 'b') + "\"");
    CHECK_CONTAINS(json, "\"refusalReason\":\"mismatch\"");
    CHECK_MISSING(json, std::string(65, 'a'));
  }
  {
    const std::string json = record::StopBegin(63, Cause::kPlanStale, "superviseLoop", 7.5);
    CHECK_CONTAINS(json, "\"cause\":\"kPlanStale\"");
    CHECK_CONTAINS(json, "\"causeValue\":8");
    CHECK_CONTAINS(json, "\"frame\":63");
    CHECK_CONTAINS(json, "\"capture_sim_ms\":6300");
    CHECK_CONTAINS(json, "\"source\":\"superviseLoop\"");
    CHECK_CONTAINS(json, "\"decision_mono_s\":7.5");
    CHECK_CONTAINS(json,
                   "\"clocks\":{\"capture_sim_ms\":\"simulation\","
                   "\"decision_mono_s\":\"monotonic\"}");
    const std::string from_command =
        record::StopBegin(64, Cause::kPlanStale, "commandVehicle", 7.6);
    CHECK_CONTAINS(from_command, "\"source\":\"commandVehicle\"");
  }
  {
    const std::string json = record::Standstill(88, Cause::kCameraMissing, 0.05, 9.0);
    CHECK_CONTAINS(json, "\"cause\":\"kCameraMissing\"");
    CHECK_CONTAINS(json, "\"frame\":88");
    CHECK_CONTAINS(json, "\"capture_sim_ms\":8800");
    CHECK_CONTAINS(json, "\"speedKmh\":");
    CHECK_CONTAINS(json, "\"source\":\"superviseLoop\"");
    CHECK_CONTAINS(json, "\"speedMps\":");
  }
  {
    Commander commander(DefaultConfig());
    const DrivingPlanPayload plan = MakePlan(10, 0.0, 0.02);
    const CommandStep step =
        commander.Step(Mode::kDriving, &plan, 11, CleanMotion(11, 36.0), 5.0);
    const std::string json = record::OutCommand(step);
    CHECK_CONTAINS(json, "\"step_capture_sim_ms\":1100");
    CHECK_CONTAINS(json, "\"plan_capture_sim_ms\":1000");
    CHECK_CONTAINS(json, "\"planReference\":\"0123456789abcdef/10\"");
    CHECK_CONTAINS(json, "\"commandLaw\":\"first_control\"");
    CHECK_CONTAINS(json, "\"sampleIndex\":1");
    CHECK_CONTAINS(json, "\"clocks\":{\"productionTime\":\"monotonic\",");
  }
  {
    Commander commander(DefaultConfig());
    const CommandStep stop =
        commander.Step(Mode::kStopResponse, nullptr, 12, CleanMotion(12, 0.0), 5.1);
    const std::string json = record::OutCommand(stop);
    CHECK_CONTAINS(json, "\"plan_capture_sim_ms\":null");
    CHECK_CONTAINS(json, "\"planReference\":\"none\"");
    CHECK_MISSING(json, "sampleIndex");
  }
  {
    StepConditions faulty = CleanConditions(63);
    faulty.cameras[0].present = false;
    faulty.route.corridor_points = 0;
    const ConditionResult result = JudgeConditions(faulty, StandardSizes());
    const std::string json = record::Condition(faulty, result);
    CHECK_CONTAINS(json, "\"frame\":63");
    CHECK_CONTAINS(json, "\"sim_ms\":6300");
    CHECK_CONTAINS(json, "\"causes\":[\"kCameraMissing\",\"kRouteEmpty\"]");
    CHECK_CONTAINS(json, "\"causeValues\":[1,7]");
    CHECK_CONTAINS(json, "\"input_conditions\":{\"bits\":");
  }
  {
    RefusalDetail refusal;
    refusal.expected_sha256 = std::string(64, 'a');
    refusal.actual_sha256 = std::string(64, 'b');
    refusal.reason = "no_pin";
    const std::string json = record::CheckpointRefusedError(refusal);
    CHECK_CONTAINS(json, "\"code\":\"checkpoint_refused\"");
    CHECK_CONTAINS(json, "\"expectedSha256\":\"" + std::string(64, 'a') + "\"");
    CHECK_CONTAINS(json, "\"actualSha256\":\"" + std::string(64, 'b') + "\"");
    CHECK_CONTAINS(json, "\"reason\":\"no_pin\"");
  }
}

// ------------------------------------------------------------------ scenario
// A scripted run: priming -> driving -> fault -> stop -> standstill. It is
// driven here in-process and, on request, written as a JSONL file for the
// Python record test (both use the same code path).
enum class ScenarioFault { kPlanStale, kPlanInvalid, kCameraMissing };

struct ScenarioResult {
  std::uint64_t fault_frame = 0;
  std::uint64_t stop_frame = 0;
  std::uint64_t standstill_frame = 0;
  int steps = 0;
  bool found_standstill = false;
  bool found_stop = false;
  Cause stop_cause = Cause::kNone;
};

ScenarioResult RunScenario(std::uint64_t fault_frame, ScenarioFault fault, RunLog* log,
                           const std::string& identity) {
  const std::uint64_t prime = 20;
  // A stalled planner makes no plan after the fault; the other faults leave the
  // planner running (the chain keeps producing plans during the stop).
  const std::uint64_t last_plan = fault == ScenarioFault::kPlanStale ? 59 : 200;
  const std::uint64_t steps = 100;

  Supervisor supervisor;
  Commander commander(DefaultConfig());
  ScenarioResult result;
  result.fault_frame = fault_frame;
  result.steps = static_cast<int>(steps);

  double speed_mps = 10.0;
  bool stopped = false;
  for (std::uint64_t frame = 0; frame < steps; ++frame) {
    if (stopped) speed_mps = std::max(0.0, speed_mps - 4.0 * kRateLimitStepSeconds);
    const double speed_kmh = speed_mps * 3.6;

    StepConditions step_conditions = CleanConditions(frame);
    if (fault == ScenarioFault::kCameraMissing && frame >= fault_frame) {
      step_conditions.cameras[0].present = false;  // front image withheld
      step_conditions.cameras[0].has_frame = false;
    }
    const ConditionResult conditions = JudgeConditions(step_conditions, StandardSizes());
    const MotionObservation motion = CleanMotion(frame, speed_kmh);

    // inferPlan: one plan per step while planning; the fault step may inject an
    // invalid one.
    const bool planning = frame >= prime && frame <= last_plan;
    const bool invalid_now = fault == ScenarioFault::kPlanInvalid && frame == fault_frame;
    const bool has_plan = planning || invalid_now;
    DrivingPlanPayload plan = MakePlan(frame, 0.0, 0.05, static_cast<std::uint32_t>(kPlanSamples),
                                       identity);
    if (invalid_now) {
      plan = MakePlan(frame, 0.0, 0.05, 63, identity);
    }
    if (has_plan && log != nullptr) {
      log->Write("out.plan", frame, record::OutPlan(plan));
    }

    const SupervisorStep supervision =
        supervisor.Step(frame, 1000.0 + FrameSeconds(frame), conditions,
                        has_plan ? &plan : nullptr, motion);

    if (log != nullptr) {
      log->Write("out.condition", frame, record::Condition(step_conditions, conditions));
    }
    if (supervision.newest_valid_plan != nullptr && log != nullptr) {
      log->Write("in.plan", frame, record::InPlan(*supervision.newest_valid_plan));
    }
    if (supervision.stop_began) {
      stopped = true;
      if (!result.found_stop) {
        result.found_stop = true;
        result.stop_frame = frame;
        result.stop_cause = supervision.cause;
      }
      if (log != nullptr) {
        log->Write("stop_response.begin", frame,
                   record::StopBegin(frame, supervision.cause, "superviseLoop",
                                     1000.0 + FrameSeconds(frame)));
      }
    }

    const CommandStep command = commander.Step(supervision.mode, supervision.newest_valid_plan,
                                               frame, motion, 1000.5 + FrameSeconds(frame));

    if (log != nullptr) {
      log->Write("out.mode", frame, record::OutMode(supervision.mode_payload));
      if (command.has_command) log->Write("out.command", frame, record::OutCommand(command));
    }

    if (supervision.mode == Mode::kStandstill && !result.found_standstill) {
      result.found_standstill = true;
      result.standstill_frame = frame;
      if (log != nullptr) {
        log->Write("stop_response.standstill", frame,
                   record::Standstill(frame, supervision.cause, speed_kmh,
                                      1000.0 + FrameSeconds(frame)));
      }
    }
  }
  return result;
}

void TestScenario() {
  const ScenarioResult result = RunScenario(60, ScenarioFault::kPlanStale, nullptr, kRunIdentity);
  // Priming ends at 20; the newest plan is frame 59, so the first step whose age
  // exceeds 300 ms is 63.
  CHECK(result.stop_frame == 63);
  CHECK(result.found_standstill);
  CHECK(result.standstill_frame > result.stop_frame);
  CHECK(result.standstill_frame < 100);

  Supervisor supervisor;
  Commander commander(DefaultConfig());
  double speed_mps = 10.0;
  bool stopped = false;
  int stop_commands = 0;
  int pulling_commands = 0;
  double held_steering = 0.0;
  for (std::uint64_t frame = 0; frame < 100; ++frame) {
    if (stopped) speed_mps = std::max(0.0, speed_mps - 4.0 * kRateLimitStepSeconds);
    const MotionObservation motion = CleanMotion(frame, speed_mps * 3.6);
    const bool planning = frame >= 20 && frame <= 59;
    const DrivingPlanPayload plan = MakePlan(frame, 0.0, 0.05);
    const SupervisorStep supervision =
        supervisor.Step(frame, 1000.0 + FrameSeconds(frame), JudgeClean(frame),
                        planning ? &plan : nullptr, motion);
    const CommandStep command = commander.Step(supervision.mode, supervision.newest_valid_plan,
                                               frame, motion, 1000.5 + FrameSeconds(frame));
    if (supervision.mode == Mode::kStarting) {
      CHECK(!command.has_command);
    }
    if (supervision.stop_began) stopped = true;
    if (frame >= 20 && frame < 63) {
      CHECK(supervision.mode == Mode::kDriving);
      CHECK(command.has_command);
    }
    if (frame == 63) {
      CHECK(supervision.mode == Mode::kStopResponse);
      CHECK(supervision.cause == Cause::kPlanStale);
      CHECK(supervision.stop_began);
      held_steering = command.command.steeringAngle;
    }
    if (frame >= 63) {
      ++stop_commands;
      CHECK_NEAR(command.command.acceleration, -4.0, 1e-6);
      CHECK_NEAR(command.command.steeringAngle, held_steering, 1e-6);
      if (command.command.acceleration > 0.0f) ++pulling_commands;
    }
    if (frame == 99) {
      CHECK(supervision.mode == Mode::kStandstill);
      CHECK(supervision.cause == Cause::kPlanStale);
    }
  }
  CHECK(stop_commands == 37);  // frames 63..99
  CHECK(pulling_commands == 0);
  CHECK_NEAR(held_steering, kFirstControl005Deg, 1e-5);

  // The brief's scenario: a camera fault at step 60. The stop begins at the
  // fault step (no plan age involved) and the deceleration is -4 from then on.
  const ScenarioResult camera =
      RunScenario(60, ScenarioFault::kCameraMissing, nullptr, kRunIdentity);
  CHECK(camera.found_stop);
  CHECK(camera.stop_frame == 60);
  CHECK(camera.stop_cause == Cause::kCameraMissing);
  CHECK(camera.found_standstill);
  CHECK(camera.standstill_frame > 60);

  Supervisor camera_supervisor;
  Commander camera_commander(DefaultConfig());
  double camera_speed_mps = 10.0;
  bool camera_stopped = false;
  int camera_commands = 0;
  double camera_held = 0.0;
  for (std::uint64_t frame = 0; frame < 100; ++frame) {
    if (camera_stopped) {
      camera_speed_mps = std::max(0.0, camera_speed_mps - 4.0 * kRateLimitStepSeconds);
    }
    StepConditions step_conditions = CleanConditions(frame);
    if (frame >= 60) {
      step_conditions.cameras[0].present = false;
      step_conditions.cameras[0].has_frame = false;
    }
    const MotionObservation motion = CleanMotion(frame, camera_speed_mps * 3.6);
    const bool planning = frame >= 20;
    const DrivingPlanPayload plan = MakePlan(frame, 0.0, 0.05);
    const SupervisorStep supervision =
        camera_supervisor.Step(frame, 1000.0 + FrameSeconds(frame),
                               JudgeConditions(step_conditions, StandardSizes()),
                               planning ? &plan : nullptr, motion);
    const CommandStep command =
        camera_commander.Step(supervision.mode, supervision.newest_valid_plan, frame, motion,
                              1000.5 + FrameSeconds(frame));
    if (supervision.stop_began) camera_stopped = true;
    if (frame == 60) {
      CHECK(supervision.mode == Mode::kStopResponse);
      CHECK(supervision.cause == Cause::kCameraMissing);
      camera_held = command.command.steeringAngle;
    }
    if (frame >= 60) {
      ++camera_commands;
      CHECK_NEAR(command.command.acceleration, -4.0, 1e-6);
      CHECK_NEAR(command.command.steeringAngle, camera_held, 1e-6);
    }
    if (frame == 99) CHECK(supervision.mode == Mode::kStandstill);
  }
  CHECK(camera_commands == 40);  // frames 60..99
  CHECK_NEAR(camera_held, kFirstControl005Deg, 1e-5);
}

// ------------------------------------------------------------------ emitter
int EmitScenario(const std::string& name, const std::string& run_dir,
                 const std::string& identity) {
  namespace fs = std::filesystem;
  ScenarioFault fault = ScenarioFault::kPlanStale;
  if (name == "plan_stale") {
    fault = ScenarioFault::kPlanStale;
  } else if (name == "plan_invalid") {
    fault = ScenarioFault::kPlanInvalid;
  } else if (name == "camera_missing") {
    fault = ScenarioFault::kCameraMissing;
  } else {
    std::fprintf(stderr, "unknown scenario %s (plan_stale, plan_invalid or camera_missing)\n",
                 name.c_str());
    return 2;
  }
  const fs::path score = fs::path(run_dir) / "score";
  std::error_code error;
  fs::create_directories(score, error);
  if (error) {
    std::fprintf(stderr, "cannot create %s: %s\n", score.string().c_str(),
                 error.message().c_str());
    return 2;
  }
  const fs::path path = score / "drivingAgent.jsonl";
  std::remove(path.string().c_str());
  RunLog log(path.string(), "score", "drivingAgent");
  if (!log.ok()) {
    std::fprintf(stderr, "cannot write %s\n", path.string().c_str());
    return 2;
  }
  const ScenarioResult result = RunScenario(60, fault, &log, identity);
  std::printf("emitted %s: %d steps, fault %llu, stop %llu, standstill %llu\n", name.c_str(),
              result.steps, static_cast<unsigned long long>(result.fault_frame),
              static_cast<unsigned long long>(result.stop_frame),
              static_cast<unsigned long long>(result.standstill_frame));
  return 0;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc >= 2 && std::string(argv[1]) == "--emit-scenario") {
    if (argc != 5) {
      std::fprintf(stderr,
                   "usage: %s --emit-scenario <plan_stale|plan_invalid|camera_missing> "
                   "<run_dir> <identity>\n",
                   argv[0]);
      return 2;
    }
    return EmitScenario(argv[2], argv[3], argv[4]);
  }

  TestTimes();
  TestConditionCameras();
  TestConditionMotionRoute();
  TestPlanValidity();
  TestSupervisorStart();
  TestSupervisorPlanAge();
  TestSupervisorStopLatching();
  TestSupervisorStandstill();
  TestSupervisorLatchApi();
  TestSupervisorEndRun();
  TestSupervisorRefusal();
  TestCommanderStarting();
  TestCommanderDriving();
  TestCommanderSampleIndexClamp();
  TestCommanderPlanStale();
  TestCommanderStopModes();
  TestStopReferenceFrozenInScenario();
  TestPlanInvalidOutranksStaleInOneStep();
  TestCommanderLimits();
  TestCommanderPurePursuit();
  TestVehicleConfig();
  TestRecords();
  TestScenario();

  std::printf("%d checks, %d failures\n", g_checks, g_failures);
  return g_failures == 0 ? 0 : 1;
}
