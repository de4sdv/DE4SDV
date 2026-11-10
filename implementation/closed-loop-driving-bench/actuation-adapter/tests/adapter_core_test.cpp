// Tests of the actuation adapter logic against a simulated vehicle.
//
// Build and run:
//   g++ -std=c++17 -Wall -Wextra -Werror -I. -I../interfaces/include
//       -Itests tests/adapter_core_test.cpp adapter_core.cpp adapter_config.cpp
//       json_lite.cpp -o .build/adapter_core_test
//   .build/adapter_core_test config/vehicle_limits.json
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <string>
#include <vector>

#include "adapter_config.h"
#include "adapter_core.h"
#include "json_lite.h"
#include "log_records.h"
#include "simulated_vehicle.h"

using de4sdv::driving::ActuationStatePayload;
using de4sdv::driving::Cause;
using de4sdv::driving::VehicleMotionCommandPayload;
using de4sdv::driving::actuation::ActuationAdapter;
using de4sdv::driving::actuation::ActuationOutput;
using de4sdv::driving::actuation::AdapterConfig;
using de4sdv::driving::actuation::CaptureTimeSeconds;
using de4sdv::driving::actuation::CommandValidity;
using de4sdv::driving::actuation::LoadAdapterConfigFile;
using de4sdv::driving::actuation::ParseAdapterConfig;
using de4sdv::driving::actuation::RejectReason;
using de4sdv::driving::actuation::SetVehicleMaxSteerAngle;
using de4sdv::driving::actuation::TableSource;
using de4sdv::driving::actuation::test::SimulatedVehicle;

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
    std::printf("FAIL %s:%d: %s (actual %.9f, expected %.9f, tolerance %.9f)\n", file, line,
                expression, actual, expected, tolerance);
  }
}

#define CHECK(condition) Check((condition), #condition, __FILE__, __LINE__)
#define CHECK_NEAR(actual, expected, tolerance) \
  CheckNear((actual), (expected), (tolerance), #actual " ~= " #expected, __FILE__, __LINE__)

// The calibration table generated from SimulatedVehicle's parameters at
// 10 m/s: throttle = (a + 0.5) / 5, brake = (-a + 0.5) / 10.
std::string TestConfigJson(double max_angle_deg = 35.0, double max_deceleration_mps2 = 8.0) {
  std::string json =
      "{\"vehicle_blueprint\":\"vehicle.lincoln.mkz_2020\",\"wheelbase_m\":2.85,"
      "\"max_acceleration_mps2\":3.0,\"max_deceleration_mps2\":" +
      std::to_string(max_deceleration_mps2) +
      ",\"max_road_wheel_angle_deg\":" +
      std::to_string(max_angle_deg) +
      ",\"max_steering_rate_deg_per_s\":180.0,"
      "\"longitudinal_controller\":{\"speed_kp\":0.20,\"speed_ki\":0.10,"
      "\"integral_limit\":1.0,\"standstill_brake\":1.0,\"standstill_speed_kmh\":0.1,\"table\":[";
  bool first = true;
  for (double acceleration = -8.0; acceleration <= 3.0001; acceleration += 0.5) {
    double throttle = 0.0;
    double brake = 0.0;
    if (acceleration >= 0.0) {
      throttle = std::min(1.0, std::max(0.0, (acceleration + 0.5) / 5.0));
    } else {
      brake = std::min(1.0, std::max(0.0, (-acceleration - 0.5) / 10.0));
    }
    char row[160];
    std::snprintf(row, sizeof row,
                  "%s{\"acceleration_mps2\":%.6f,\"throttle\":%.6f,\"brake\":%.6f}", first ? "" : ",",
                  acceleration, throttle, brake);
    json += row;
    first = false;
  }
  json += "]}}";
  return json;
}

AdapterConfig MakeTestConfig(double max_angle_deg = 35.0, double max_deceleration_mps2 = 8.0) {
  bool ok = false;
  std::string error;
  AdapterConfig config =
      ParseAdapterConfig(TestConfigJson(max_angle_deg, max_deceleration_mps2), &ok, &error);
  if (!ok) {
    std::printf("FATAL: test configuration does not parse: %s\n", error.c_str());
    std::exit(2);
  }
  return config;
}

// The shell's start-up step: the adapter takes the vehicle's maximum steering
// angle from the simulator (CARLA's front-wheel max_steer_angle).
AdapterConfig WithVehicleSteering(AdapterConfig config, double max_steer_angle_deg) {
  std::string error;
  if (!SetVehicleMaxSteerAngle(&config, max_steer_angle_deg, &error)) {
    std::printf("FATAL: the vehicle's maximum steering angle is refused: %s\n", error.c_str());
    std::exit(2);
  }
  return config;
}

// One world snapshot at `frame`, then one command arriving 20 ms after its
// production, to an adapter without a simulated vehicle.
ActuationOutput TickAndSend(ActuationAdapter& adapter, std::uint64_t frame, double steering_angle) {
  const double monotonic = 1000.0 + 0.1 * static_cast<double>(frame);
  adapter.OnWorldTick({frame, 0.0, 0.0, monotonic});
  VehicleMotionCommandPayload payload{};
  payload.acceleration = 0.0F;
  payload.steeringAngle = static_cast<float>(steering_angle);
  payload.productionTime = monotonic - 0.02;
  std::snprintf(payload.planReference, sizeof payload.planReference, "run/%llu",
                static_cast<unsigned long long>(frame));
  return adapter.OnCommand(payload, monotonic);
}

struct Bench {
  SimulatedVehicle car;
  ActuationAdapter adapter;
  std::uint64_t frame = 0;
  double monotonic = 1000.0;
  std::vector<double> speed_history;
  std::vector<double> accel_history;
  std::vector<double> time_history;

  // `car` is declared first, so the adapter is given the simulated vehicle's own
  // maximum steering angle, as the shell gives it CARLA's.
  explicit Bench(AdapterConfig config)
      : adapter(WithVehicleSteering(std::move(config), car.max_steer_angle_deg)) {
    car.wheelbase_m = adapter.config().wheelbase_m;
  }

  ActuationOutput TickDecision() {
    return adapter.OnWorldTick({frame, car.speed_mps, car.acceleration_mps2, monotonic});
  }

  void Advance() {
    ++frame;
    monotonic += 0.1;
  }

  void PhysicalStep(const de4sdv::driving::actuation::VehicleControlCommand& control) {
    car.Step(control, 0.1);
    time_history.push_back(CaptureTimeSeconds(frame + 1));
    speed_history.push_back(car.speed_mps);
    accel_history.push_back(car.acceleration_mps2);
  }

  ActuationOutput Send(double acceleration, double steering_angle,
                       const char* reference = "run/1", double age_seconds = 0.02) {
    VehicleMotionCommandPayload payload{};
    payload.acceleration = static_cast<float>(acceleration);
    payload.steeringAngle = static_cast<float>(steering_angle);
    payload.productionTime = monotonic - age_seconds;
    std::snprintf(payload.planReference, sizeof payload.planReference, "%s", reference);
    return adapter.OnCommand(payload, monotonic);
  }

  ActuationOutput StepWithCommand(double acceleration, double steering_angle,
                                  const char* reference = "run/1") {
    const ActuationOutput tick = TickDecision();
    const ActuationOutput command = Send(acceleration, steering_angle, reference);
    PhysicalStep(command.hasControl ? command.control : tick.control);
    Advance();
    return command;
  }

  ActuationOutput StepNoCommand() {
    const ActuationOutput tick = TickDecision();
    PhysicalStep(tick.control);
    Advance();
    return tick;
  }
};

double MeanLast(const std::vector<double>& values, std::size_t count) {
  if (values.empty()) return 0.0;
  const std::size_t from = values.size() > count ? values.size() - count : 0;
  double sum = 0.0;
  for (std::size_t i = from; i < values.size(); ++i) sum += values[i];
  return sum / static_cast<double>(values.size() - from);
}

// ---------------------------------------------------------------- tests

void TestTrackingOfConstantAcceleration() {
  struct Case {
    double target;
    double start_speed;
    int steps;
  };
  const Case cases[] = {{1.5, 15.0, 50}, {0.0, 15.0, 100}, {-2.0, 25.0, 80}};
  for (const Case& test : cases) {
    Bench bench(MakeTestConfig());
    bench.car.speed_mps = test.start_speed;
    for (int step = 0; step < test.steps; ++step) bench.StepWithCommand(test.target, 3.0);
    const double mean_accel = MeanLast(bench.accel_history, 30);
    const double mean_speed = MeanLast(bench.speed_history, 30);
    const double reference = bench.adapter.ReferenceSpeedMps();
    std::printf(
        "TRACKING target=%+.2f m/s^2 mean_accel=%+.4f error=%+.4f m/s^2 "
        "mean_speed=%.3f ref=%.3f final_speed_error=%+.4f m/s\n",
        test.target, mean_accel, mean_accel - test.target, mean_speed, reference,
        bench.car.speed_mps - reference);
    CHECK_NEAR(mean_accel, test.target, 0.15);
    CHECK_NEAR(bench.car.speed_mps, reference, 0.3);
    CHECK(!bench.adapter.StopLatched());
  }
}

// REQ-DRIVING-028: with a command every 100 ms, two missed commands mean the path has stopped. The stop
// begins at the first tick more than 200 ms of simulation time after the last actuation: the third.
void TestWatchdogFiresOnlyAfterMoreThan200ms() {
  Bench bench(MakeTestConfig());
  bench.car.speed_mps = 10.0;
  for (int step = 0; step < 10; ++step) bench.StepWithCommand(0.0, 3.0);
  CHECK_NEAR(bench.adapter.LastActuationTime(), 0.9, 1e-9);

  const ActuationOutput at_100ms = bench.StepNoCommand();  // frame 10
  CHECK(!at_100ms.stopBegan);
  CHECK_NEAR(at_100ms.actuationTime, 1.0, 1e-9);

  const ActuationOutput at_200ms = bench.StepNoCommand();  // frame 11: exactly 200 ms, no stop yet
  CHECK(!at_200ms.stopBegan);
  CHECK(!bench.adapter.StopLatched());

  const ActuationOutput at_300ms = bench.StepNoCommand();  // frame 12: two commands missed
  CHECK(at_300ms.stopBegan);
  CHECK(at_300ms.hasState);
  CHECK(at_300ms.state.stopInForce == 1);
  CHECK(at_300ms.state.cause == Cause::kCommandTimeout);
  CHECK_NEAR(at_300ms.actuationTime, 1.2, 1e-9);
  CHECK_NEAR(at_300ms.state.stopSince, 1.2, 1e-9);
  CHECK_NEAR(at_300ms.state.steeringAngle, 3.0, 1e-5);
  CHECK_NEAR(at_300ms.state.acceleration, -4.0, 1e-5);
  CHECK(bench.adapter.StopLatched());
}

// The simulator-host run: a command arrives about one period after its frame's tick, so one of them
// can land just after the next tick. In simulation time that is the same as one missed command: the
// tick before it sees exactly 200 ms. Neither may begin the stop; the vehicle drives on.
void TestOneLateOrMissedCommandDoesNotStop() {
  Bench bench(MakeTestConfig());
  bench.car.speed_mps = 10.0;
  for (int step = 0; step < 10; ++step) bench.StepWithCommand(0.0, 3.0);  // actuations 0.0 .. 0.9
  const ActuationOutput gap = bench.StepNoCommand();  // frame 10: its command is late (or lost)
  CHECK(!gap.stopBegan);
  const ActuationOutput late = bench.StepWithCommand(0.0, 3.0);  // tick 11 (200 ms), then the command
  CHECK(late.appliedCommand);
  CHECK(late.reject == RejectReason::kNone);
  CHECK_NEAR(late.actuationTime, 1.1, 1e-9);
  CHECK(!bench.adapter.StopLatched());
  for (int step = 0; step < 5; ++step) {
    const ActuationOutput out = bench.StepWithCommand(0.0, 3.0);  // back on the frame grid
    CHECK(out.appliedCommand);
  }
  CHECK(!bench.adapter.StopLatched());
  CHECK(bench.adapter.StopCause() == Cause::kNone);
}

void TestACommandAtTheBoundaryPreventsTheStop() {
  Bench bench(MakeTestConfig());
  bench.car.speed_mps = 10.0;
  for (int step = 0; step < 10; ++step) bench.StepWithCommand(0.0, 3.0);
  const ActuationOutput at_100ms = bench.StepNoCommand();  // elapsed 100 ms
  CHECK(!at_100ms.stopBegan);
  const ActuationOutput command = bench.Send(0.5, 3.0);  // arrives before frame 11
  CHECK(command.appliedCommand);
  CHECK_NEAR(command.actuationTime, 1.0, 1e-9);
  const ActuationOutput at_next_tick = bench.StepNoCommand();  // frame 11, elapsed 100 ms
  CHECK(!at_next_tick.stopBegan);
  CHECK(!bench.adapter.StopLatched());
}

void TestInvalidCommandsDoNotFeedTheWatchdog() {
  Bench bench(MakeTestConfig());
  bench.car.speed_mps = 10.0;
  for (int step = 0; step < 10; ++step) bench.StepWithCommand(0.0, 3.0);
  const ActuationOutput at_100ms = bench.StepNoCommand();  // frame 10
  CHECK(!at_100ms.stopBegan);

  VehicleMotionCommandPayload bad{};
  bad.acceleration = std::numeric_limits<float>::quiet_NaN();
  bad.steeringAngle = 0.0F;
  bad.productionTime = bench.monotonic - 0.02;
  std::snprintf(bad.planReference, sizeof bad.planReference, "run/bad");
  const ActuationOutput rejected = bench.adapter.OnCommand(bad, bench.monotonic);
  CHECK(rejected.reject == RejectReason::kNonFinite);  // does not refresh last actuation

  const ActuationOutput at_200ms = bench.StepNoCommand();  // frame 11
  CHECK(!at_200ms.stopBegan);
  const ActuationOutput at_300ms = bench.StepNoCommand();  // frame 12
  CHECK(at_300ms.stopBegan);
  CHECK(at_300ms.state.cause == Cause::kCommandTimeout);
}

void TestStopToStandstillAndHold() {
  Bench bench(MakeTestConfig());
  bench.car.speed_mps = 20.0;
  for (int step = 0; step < 6; ++step) bench.StepWithCommand(0.0, 12.0);

  ActuationOutput stop;
  int guard = 0;
  do {
    stop = bench.StepNoCommand();
  } while (!stop.stopBegan && ++guard < 10);
  CHECK(stop.stopBegan);
  CHECK_NEAR(stop.actuationTime, 0.8, 1e-9);  // last actuation 0.5; more than 200 ms at 0.8
  CHECK_NEAR(stop.state.steeringAngle, 12.0, 1e-5);
  CHECK_NEAR(stop.state.acceleration, -4.0, 1e-5);
  CHECK_NEAR(stop.control.steer, -12.0 / 70.0, 1e-6);
  CHECK_NEAR(stop.control.brake, 0.35, 0.06);
  CHECK(stop.control.throttle == 0.0);

  int state_count = 1;  // the stop-begin state
  double decel_sum = 0.0;
  int decel_count = 0;
  bool reached_standstill = false;
  double standstill_time = 0.0;
  for (int step = 0; step < 300; ++step) {
    const ActuationOutput out = bench.StepNoCommand();
    if (out.hasState) ++state_count;
    if (out.standstillReached) {
      reached_standstill = true;
      standstill_time = bench.time_history.back();
      break;
    }
    if (bench.time_history.back() >= stop.actuationTime + 1.0) {
      decel_sum += bench.accel_history.back();
      ++decel_count;
    }
  }
  CHECK(reached_standstill);
  CHECK(state_count == 1);
  CHECK(decel_count > 30);
  const double mean_decel = decel_sum / static_cast<double>(decel_count);
  const double duration = standstill_time - stop.actuationTime;
  std::printf("STOP mean_decel=%.4f m/s^2 duration=%.2f s states=%d\n", mean_decel, duration,
              state_count);
  CHECK_NEAR(mean_decel, -4.0, 0.25);
  CHECK(duration > 4.5 && duration < 6.0);
  CHECK(bench.car.speed_mps * 3.6 < 0.1);

  for (int step = 0; step < 20; ++step) {
    const ActuationOutput out = bench.StepNoCommand();
    CHECK(!out.hasState);
    CHECK(out.control.brake == 1.0);
    CHECK(out.control.throttle == 0.0);
    CHECK_NEAR(out.control.steer, -12.0 / 70.0, 1e-6);
    CHECK(bench.car.speed_mps * 3.6 < 0.1);
  }
  CHECK(bench.adapter.StopLatched());
  CHECK(bench.adapter.StandstillHold());

  const ActuationOutput rejected = bench.Send(1.0, 0.0);
  CHECK(rejected.reject == RejectReason::kStopLatched);
  CHECK(!rejected.hasControl);
  CHECK(bench.adapter.RejectCount(RejectReason::kStopLatched) == 1);
}

void TestInvalidCommandsAreRejected() {
  Bench bench(MakeTestConfig());
  bench.StepNoCommand();  // one snapshot at frame 0

  CHECK(bench.Send(std::numeric_limits<double>::quiet_NaN(), 0.0).reject ==
        RejectReason::kNonFinite);
  CHECK(bench.Send(0.0, std::numeric_limits<double>::quiet_NaN()).reject ==
        RejectReason::kNonFinite);
  CHECK(bench.Send(3.5, 0.0).reject == RejectReason::kAccelerationOutOfLimits);
  CHECK(bench.Send(-8.5, 0.0).reject == RejectReason::kAccelerationOutOfLimits);
  CHECK(bench.Send(0.0, 36.0).reject == RejectReason::kSteeringOutOfLimits);
  CHECK(bench.Send(0.0, 0.0, "").reject == RejectReason::kEmptyPlanReference);

  VehicleMotionCommandPayload infinite{};
  infinite.acceleration = 0.0F;
  infinite.steeringAngle = 0.0F;
  infinite.productionTime = std::numeric_limits<double>::infinity();
  std::snprintf(infinite.planReference, sizeof infinite.planReference, "run/1");
  CHECK(bench.adapter.OnCommand(infinite, bench.monotonic).reject == RejectReason::kNonFinite);

  CHECK(bench.Send(0.0, 0.0, "run/1", 0.31).reject == RejectReason::kStaleProductionTime);
  CHECK(bench.Send(0.0, 0.0, "run/1", 0.29).reject == RejectReason::kNone);

  CHECK(bench.adapter.RejectedCommandCount() == 8);
  CHECK(bench.adapter.RejectCount(RejectReason::kNonFinite) == 3);
  CHECK(bench.adapter.RejectCount(RejectReason::kAccelerationOutOfLimits) == 2);
  CHECK(bench.adapter.RejectCount(RejectReason::kSteeringOutOfLimits) == 1);
  CHECK(bench.adapter.RejectCount(RejectReason::kEmptyPlanReference) == 1);
  CHECK(bench.adapter.RejectCount(RejectReason::kStaleProductionTime) == 1);
}

// The model's actuation mapping turns the steering angle into the normalized
// steer by the vehicle's maximum steering angle, clipped. The configured limit
// (35) bounds the command; the simulated vehicle's maximum (70) scales it.
void TestSteeringMappingSignsAndClamps() {
  Bench bench(MakeTestConfig());
  bench.StepNoCommand();

  const ActuationOutput angle_minus_35 = bench.Send(0.0, -35.0);
  CHECK_NEAR(angle_minus_35.control.steer, 0.5, 1e-6);  // right command -> CARLA right
  const ActuationOutput angle_minus_17_5 = bench.Send(0.0, -17.5);
  CHECK_NEAR(angle_minus_17_5.control.steer, 0.25, 1e-6);
  const ActuationOutput straight = bench.Send(0.0, 0.0);
  CHECK_NEAR(straight.control.steer, 0.0, 1e-12);
  const ActuationOutput angle_plus_35 = bench.Send(0.0, 35.0);  // left command -> CARLA left
  CHECK_NEAR(angle_plus_35.control.steer, -0.5, 1e-6);
  const ActuationOutput at_tolerance = bench.Send(0.0, 35.0000005);  // valid within 1e-6 of the limit
  CHECK_NEAR(at_tolerance.control.steer, -0.5, 1e-6);

  // Clipped: a vehicle whose maximum is below the command still gets |steer| <= 1.
  // SetVehicleMaxSteerAngle refuses such a vehicle, so the value is set directly.
  AdapterConfig narrow = MakeTestConfig();
  narrow.vehicle_max_steer_angle_deg = 20.0;
  ActuationAdapter adapter(narrow);
  CHECK_NEAR(TickAndSend(adapter, 0, 35.0).control.steer, -1.0, 1e-12);
  CHECK_NEAR(TickAndSend(adapter, 1, -35.0).control.steer, 1.0, 1e-12);
}

// What is commanded and what the vehicle does stay the same (REQ-DRIVING-012's
// rationale): the simulated vehicle, like CARLA's vehicle.lincoln.mkz_2020,
// turns its road wheels 70 degrees at steer +-1 while the configured limit is
// 35, and its wheels turn by the commanded angle.
void TestSteeringTurnsTheWheelsByTheCommandedAngle() {
  Bench bench(MakeTestConfig());
  CHECK_NEAR(bench.car.max_steer_angle_deg, 70.0, 0.0);
  CHECK_NEAR(bench.adapter.config().limits.max_road_wheel_angle_deg, 35.0, 0.0);
  bench.StepNoCommand();
  for (const double angle : {0.64, 7.0, -17.5, 35.0, -35.0, 0.0}) {
    const ActuationOutput out = bench.Send(0.0, angle);
    CHECK(out.reject == RejectReason::kNone);
    CHECK(out.hasControl);
    CHECK_NEAR(bench.car.RoadWheelAngleDeg(out.control), angle, 1e-6);
  }
}

// The shell takes the vehicle's maximum steering angle from CARLA's physics
// control at start-up (the front wheels' max_steer_angle). It refuses a value
// that is not finite and positive, and one below the configured limit, with
// which a command at the limit could not be applied as commanded.
void TestTheVehiclesMaximumSteeringAngleIsValidated() {
  const double refused[] = {std::numeric_limits<double>::quiet_NaN(),
                            std::numeric_limits<double>::infinity(),
                            -std::numeric_limits<double>::infinity(), 0.0, -70.0, 34.9};
  for (const double degrees : refused) {
    AdapterConfig config = MakeTestConfig();  // limit 35
    std::string error;
    CHECK(!SetVehicleMaxSteerAngle(&config, degrees, &error));
    CHECK(error.find("max_steer_angle") != std::string::npos);
    CHECK(config.vehicle_max_steer_angle_deg == 0.0);  // unchanged
  }
  AdapterConfig below = MakeTestConfig();
  std::string below_error;
  CHECK(!SetVehicleMaxSteerAngle(&below, 34.9, &below_error));
  CHECK(below_error.find("max_road_wheel_angle_deg") != std::string::npos);  // names the limit

  const double accepted[] = {35.0, 69.99999237060547, 70.0};
  for (const double degrees : accepted) {
    AdapterConfig config = MakeTestConfig();
    std::string error;
    CHECK(SetVehicleMaxSteerAngle(&config, degrees, &error));
    CHECK(error.empty());
    CHECK_NEAR(config.vehicle_max_steer_angle_deg, degrees, 0.0);
  }
}

// Without the vehicle's maximum steering angle (the shell does not start
// without one) the core sends a straight steer, never an infinite or NaN one.
void TestWithoutTheVehiclesMaximumSteeringAngleTheSteerIsStraight() {
  ActuationAdapter adapter(MakeTestConfig());
  CHECK_NEAR(TickAndSend(adapter, 0, 7.0).control.steer, 0.0, 0.0);
  CHECK_NEAR(TickAndSend(adapter, 1, -7.0).control.steer, 0.0, 0.0);
}

void TestAgentStopIsAnOrdinaryCommand() {
  Bench bench(MakeTestConfig());
  bench.car.speed_mps = 20.0;
  for (int step = 0; step < 15; ++step) {
    const ActuationOutput out = bench.StepWithCommand(-4.0, 5.0);
    CHECK(!out.stopBegan);
    CHECK(out.hasState);
    CHECK(out.state.stopInForce == 0);
    CHECK(out.state.cause == Cause::kNone);
    CHECK_NEAR(out.state.acceleration, -4.0, 1e-6);
  }
  CHECK(!bench.adapter.StopLatched());
  std::printf("AGENT_STOP speed_after_15_steps=%.2f m/s latched=%d\n", bench.car.speed_mps,
              bench.adapter.StopLatched() ? 1 : 0);
}

void TestStartupHoldWithoutStop() {
  Bench bench(MakeTestConfig());
  CHECK(bench.adapter.LastActuationTime() < 0.0);
  CHECK_NEAR(bench.adapter.StopSinceMonoSeconds(), 0.0, 0.0);
  // 3 s of simulation time: well past the 200 ms watchdog window.
  for (int step = 0; step < 30; ++step) {
    const ActuationOutput out = bench.StepNoCommand();
    CHECK(out.control.brake > 0.0);
    CHECK(out.control.throttle == 0.0);
    CHECK(!out.stopBegan);
    CHECK(!out.hasState);
    CHECK(!bench.adapter.StopLatched());
  }
  CHECK(!bench.adapter.StopLatched());
  const ActuationOutput first = bench.StepWithCommand(1.0, 0.0);
  CHECK(first.appliedCommand);
  CHECK(!bench.adapter.StopLatched());
}

void TestValidityWindowIsMinus5To300Ms() {
  Bench bench(MakeTestConfig());
  bench.StepNoCommand();

  // ICD v2 §4: -5 ms <= age <= 300 ms at arrival.
  CHECK(bench.Send(0.0, 0.0, "run/edge300", 0.300).reject == RejectReason::kNone);
  CHECK(bench.Send(0.0, 0.0, "run/late", 0.3005).reject == RejectReason::kStaleProductionTime);
  CHECK(bench.Send(0.0, 0.0, "run/edge5", -0.005).reject == RejectReason::kNone);
  CHECK(bench.Send(0.0, 0.0, "run/future", -0.0055).reject ==
        RejectReason::kFutureProductionTime);
  CHECK(bench.Send(0.0, 0.0, "run/now", 0.0).reject == RejectReason::kNone);

  CHECK(bench.adapter.RejectCount(RejectReason::kStaleProductionTime) == 1);
  CHECK(bench.adapter.RejectCount(RejectReason::kFutureProductionTime) == 1);
  CHECK(bench.adapter.RejectedCommandCount() == 2);

  // A rejected command changes nothing: the last valid one still stands.
  const double actuation_before = bench.adapter.LastActuationTime();
  const std::uint32_t rejected_before = bench.adapter.RejectedCommandCount();
  const ActuationOutput rejected = bench.Send(1.0, 20.0, "run/future2", -0.050);
  CHECK(rejected.reject == RejectReason::kFutureProductionTime);
  CHECK(!rejected.hasControl);
  CHECK(!rejected.hasState);
  CHECK_NEAR(bench.adapter.LastActuationTime(), actuation_before, 1e-12);
  CHECK(bench.adapter.RejectedCommandCount() == rejected_before + 1);
  // The watchdog is not fed by the rejected command either.
  CHECK(!bench.adapter.StopLatched());
}

void TestStopSinceMonoIsTheMonotonicStopBeginTime() {
  Bench bench(MakeTestConfig());
  bench.car.speed_mps = 10.0;
  for (int step = 0; step < 10; ++step) {
    const ActuationOutput out = bench.StepWithCommand(0.0, 3.0);
    CHECK_NEAR(out.state.stopSinceMono, 0.0, 0.0);  // an applied command is not a stop
  }
  CHECK_NEAR(bench.adapter.StopSinceMonoSeconds(), 0.0, 0.0);
  CHECK(bench.adapter.StopCause() == Cause::kNone);

  const ActuationOutput at_100ms = bench.StepNoCommand();  // frame 10
  CHECK(!at_100ms.stopBegan);
  const ActuationOutput at_200ms = bench.StepNoCommand();  // frame 11
  CHECK(!at_200ms.stopBegan);

  const double tick_monotonic = bench.monotonic;
  const ActuationOutput at_300ms = bench.StepNoCommand();  // frame 12
  CHECK(at_300ms.stopBegan);
  CHECK(at_300ms.hasState);
  CHECK(at_300ms.state.stopInForce == 1);
  CHECK(at_300ms.state.stopSinceMono > 0.0);
  CHECK_NEAR(at_300ms.state.stopSinceMono, tick_monotonic, 1e-12);
  CHECK_NEAR(at_300ms.state.stopSince, CaptureTimeSeconds(at_300ms.frameIndex), 1e-9);
  CHECK_NEAR(bench.adapter.StopSinceMonoSeconds(), tick_monotonic, 1e-12);
  CHECK(bench.adapter.StopCause() == Cause::kCommandTimeout);

  // The stop latches with the same monotonic stamp: later ticks do not move it
  // and publish no further state event (ICD §2: one at the stop's start).
  for (int step = 0; step < 10; ++step) {
    const ActuationOutput out = bench.StepNoCommand();
    CHECK(!out.hasState);
    CHECK_NEAR(bench.adapter.StopSinceMonoSeconds(), tick_monotonic, 1e-12);
  }
}

void TestStopClampsToConfiguredDeceleration() {
  // A vehicle that can brake at 3 m/s^2 only: the stop is -3, not -4
  // (ICD v2 §4, REQ-DRIVING-012).
  Bench bench(MakeTestConfig(35.0, 3.0));
  bench.car.speed_mps = 20.0;
  for (int step = 0; step < 6; ++step) bench.StepWithCommand(0.0, 10.0);

  ActuationOutput stop;
  int guard = 0;
  do {
    stop = bench.StepNoCommand();
  } while (!stop.stopBegan && ++guard < 10);
  CHECK(stop.stopBegan);
  CHECK_NEAR(stop.state.acceleration, -3.0, 1e-5);
  CHECK_NEAR(bench.adapter.config().StopAccelerationMps2(), -3.0, 1e-12);
  CHECK_NEAR(stop.state.steeringAngle, 10.0, 1e-5);
  CHECK(stop.control.brake > 0.0);
  CHECK(stop.control.throttle == 0.0);

  double decel_sum = 0.0;
  int decel_count = 0;
  bool reached_standstill = false;
  double standstill_time = 0.0;
  double min_decel = 0.0;
  for (int step = 0; step < 400; ++step) {
    const ActuationOutput out = bench.StepNoCommand();
    if (out.standstillReached) {
      reached_standstill = true;
      standstill_time = bench.time_history.back();
      break;
    }
    if (bench.time_history.back() >= stop.actuationTime + 1.0) {
      decel_sum += bench.accel_history.back();
      ++decel_count;
      min_decel = std::min(min_decel, bench.accel_history.back());
    }
  }
  CHECK(reached_standstill);
  CHECK(decel_count > 30);
  const double mean_decel = decel_sum / static_cast<double>(decel_count);
  const double duration = standstill_time - stop.actuationTime;
  std::printf("STOP_CLAMPED mean_decel=%.4f m/s^2 duration=%.2f s min=%.4f\n", mean_decel,
              duration, min_decel);
  CHECK_NEAR(mean_decel, -3.0, 0.30);
  CHECK(min_decel > -4.0);  // the clamp held for the whole stop
  CHECK(duration > 6.0 && duration < 8.0);
  CHECK(bench.car.speed_mps * 3.6 < 0.1);
}

void TestActuationStateTimesAndReferences() {
  Bench bench(MakeTestConfig());
  bench.StepNoCommand();
  const ActuationOutput first = bench.Send(1.0, 5.0, "runA/0");
  CHECK(first.hasState);
  CHECK(first.state.applied == 1);
  CHECK(first.state.stopInForce == 0);
  CHECK(first.state.cause == Cause::kNone);
  CHECK_NEAR(first.state.actuationTime, 0.0, 1e-9);
  CHECK(std::strcmp(first.state.planReference, "runA/0") == 0);

  bench.StepWithCommand(1.0, 5.0, "runA/1");
  const ActuationOutput second = bench.Send(1.0, 5.0, "runA/2");
  CHECK(second.hasState);
  CHECK_NEAR(second.state.actuationTime, 0.1, 1e-9);
  CHECK(std::strcmp(second.state.planReference, "runA/2") == 0);

  // A 64-character reference is truncated, not overflowed.
  const std::string long_reference(80, 'r');
  const ActuationOutput truncated = bench.Send(1.0, 5.0, long_reference.c_str());
  CHECK(truncated.hasState);
  CHECK(std::strlen(truncated.state.planReference) == 63);
}

void TestConfigParsing(const std::string& path) {
  bool ok = false;
  std::string error;
  const AdapterConfig file_config = LoadAdapterConfigFile(path, &ok, &error);
  CHECK(ok);
  if (!ok) std::printf("CONFIG load error: %s\n", error.c_str());
  CHECK(file_config.tableSource() == TableSource::kConfig);
  CHECK(file_config.longitudinal.table.size() >= 20);
  CHECK_NEAR(file_config.limits.max_road_wheel_angle_deg, 35.0, 1e-9);
  CHECK_NEAR(file_config.StopAccelerationMps2(), -4.0, 1e-9);
  CHECK(file_config.vehicle_blueprint == "vehicle.lincoln.mkz_2020");

  const std::string icd_only =
      "{\"vehicle_blueprint\":\"vehicle.lincoln.mkz_2020\",\"wheelbase_m\":2.85,"
      "\"max_acceleration_mps2\":3.0,\"max_deceleration_mps2\":8.0,"
      "\"max_road_wheel_angle_deg\":35.0,\"max_steering_rate_deg_per_s\":180.0}";
  const AdapterConfig defaults = ParseAdapterConfig(icd_only, &ok, &error);
  CHECK(ok);
  CHECK(defaults.tableSource() == TableSource::kDefault);
  CHECK(!defaults.longitudinal.table.empty());

  const AdapterConfig low_limit = ParseAdapterConfig(
      "{\"wheelbase_m\":2.85,\"max_acceleration_mps2\":3.0,\"max_deceleration_mps2\":3.0,"
      "\"max_road_wheel_angle_deg\":35.0,\"max_steering_rate_deg_per_s\":180.0}",
      &ok, &error);
  CHECK(ok);
  CHECK_NEAR(low_limit.StopAccelerationMps2(), -3.0, 1e-9);

  ParseAdapterConfig(
      "{\"wheelbase_m\":2.85,\"max_acceleration_mps2\":3.0,\"max_deceleration_mps2\":8.0,"
      "\"max_road_wheel_angle_deg\":35.0,\"max_steering_rate_deg_per_s\":180.0,"
      "\"longitudinal_controller\":{\"table\":["
      "{\"acceleration_mps2\":0.0,\"throttle\":0.1,\"brake\":0.0},"
      "{\"acceleration_mps2\":-1.0,\"throttle\":0.0,\"brake\":0.2}]}}",
      &ok, &error);
  CHECK(!ok);  // not sorted

  ParseAdapterConfig(
      "{\"wheelbase_m\":2.85,\"max_acceleration_mps2\":3.0,\"max_deceleration_mps2\":8.0,"
      "\"max_road_wheel_angle_deg\":35.0,\"max_steering_rate_deg_per_s\":180.0,"
      "\"longitudinal_controller\":{\"table\":["
      "{\"acceleration_mps2\":0.0,\"throttle\":0.1,\"brake\":0.0},"
      "{\"acceleration_mps2\":1.0,\"throttle\":0.2,\"brake\":0.2}]}}",
      &ok, &error);
  CHECK(!ok);  // both pedals in one row

  ParseAdapterConfig("{\"wheelbase_m\":0.0}", &ok, &error);
  CHECK(!ok);  // missing limits

  ParseAdapterConfig("not json", &ok, &error);
  CHECK(!ok);
}

void TestIcdV2ConfigDocument() {
  // ICD v2 §5 verbatim: array-rows table, kp/ki/integrator_limit, command_law.
  const std::string icd_v2 =
      "{\"vehicle_blueprint\": \"vehicle.lincoln.mkz_2020\", \"wheelbase_m\": 2.85,"
      " \"max_acceleration_mps2\": 3.0, \"max_deceleration_mps2\": 8.0,"
      " \"max_road_wheel_angle_deg\": 35.0, \"max_steering_rate_deg_per_s\": 180.0,"
      " \"command_law\": \"first_control\","
      " \"longitudinal_controller\": {\"table\": [[-8.0, 0.0, 1.0], [0.0, 0.0, 0.0],"
      "                                             [3.0, 0.75, 0.0]],"
      "                             \"kp\": 0.3, \"ki\": 0.05, \"integrator_limit\": 0.3}}";
  bool ok = false;
  std::string error;
  const AdapterConfig config = ParseAdapterConfig(icd_v2, &ok, &error);
  CHECK(ok);
  if (!ok) std::printf("ICD_V2_CONFIG error: %s\n", error.c_str());
  CHECK(config.command_law == "first_control");
  CHECK(config.vehicle_blueprint == "vehicle.lincoln.mkz_2020");
  CHECK(config.tableSource() == TableSource::kConfig);
  CHECK(config.longitudinal.table.size() == 3);
  if (config.longitudinal.table.size() == 3) {
    CHECK_NEAR(config.longitudinal.table[0].acceleration_mps2, -8.0, 1e-12);
    CHECK_NEAR(config.longitudinal.table[0].throttle, 0.0, 1e-12);
    CHECK_NEAR(config.longitudinal.table[0].brake, 1.0, 1e-12);
    CHECK_NEAR(config.longitudinal.table[1].acceleration_mps2, 0.0, 1e-12);
    CHECK_NEAR(config.longitudinal.table[2].acceleration_mps2, 3.0, 1e-12);
    CHECK_NEAR(config.longitudinal.table[2].throttle, 0.75, 1e-12);
  }
  CHECK_NEAR(config.longitudinal.speed_kp, 0.3, 1e-12);
  CHECK_NEAR(config.longitudinal.speed_ki, 0.05, 1e-12);
  CHECK_NEAR(config.longitudinal.integral_limit, 0.3, 1e-12);
  // The adapter-only extensions keep their defaults when the document omits them.
  CHECK_NEAR(config.longitudinal.standstill_brake, 1.0, 1e-12);
  CHECK_NEAR(config.longitudinal.standstill_speed_kmh, 0.1, 1e-12);
  CHECK_NEAR(config.StopAccelerationMps2(), -4.0, 1e-12);

  const std::string prefix =
      "{\"wheelbase_m\":2.85,\"max_acceleration_mps2\":3.0,\"max_deceleration_mps2\":8.0,"
      "\"max_road_wheel_angle_deg\":35.0,\"max_steering_rate_deg_per_s\":180.0,";

  // A row that is not three numbers.
  ParseAdapterConfig(prefix + "\"longitudinal_controller\":{\"table\":[[-1.0,0.0],[0.0,0.0,0.0]]}}",
                     &ok, &error);
  CHECK(!ok);
  ParseAdapterConfig(
      prefix + "\"longitudinal_controller\":{\"table\":[[-1.0,0.0,\"x\"],[0.0,0.0,0.0]]}}", &ok,
      &error);
  CHECK(!ok);
  // Unsorted array rows.
  ParseAdapterConfig(prefix + "\"longitudinal_controller\":{\"table\":[[0.0,0.1,0.0],[-1.0,0.0,0.2]]}}",
                     &ok, &error);
  CHECK(!ok);
  // Both pedals in one array row.
  ParseAdapterConfig(prefix + "\"longitudinal_controller\":{\"table\":[[0.0,0.1,0.1],[1.0,0.2,0.0]]}}",
                     &ok, &error);
  CHECK(!ok);
  // command_law must be a string when present.
  ParseAdapterConfig(prefix + "\"command_law\":7}", &ok, &error);
  CHECK(!ok);
  // kp must be a number when present.
  ParseAdapterConfig(prefix + "\"longitudinal_controller\":{\"kp\":\"fast\"}}", &ok, &error);
  CHECK(!ok);
}

void TestLogRecordsCarryClocksAndSuffixes() {
  using de4sdv::driving::json::Value;

  const auto parse = [](const std::string& text, std::string* error) {
    return Value::Parse(text, error);
  };
  const auto clocks_clock = [](const Value& record, const char* field) -> std::string {
    const Value* clocks = record.Find("clocks");
    if (clocks == nullptr) return "<no clocks>";
    const Value* clock = clocks->Find(field);
    return clock == nullptr ? "<unmapped>" : clock->AsString("<not a string>");
  };

  VehicleMotionCommandPayload command{};
  command.acceleration = -1.5F;
  command.steeringAngle = 7.0F;
  command.productionTime = 1000.5;
  std::snprintf(command.planReference, sizeof command.planReference, "runA/12");

  std::string error;
  {
    const Value record = parse(de4sdv::driving::log::InCommand(command, 1000.62, "none"), &error);
    CHECK(error.empty());
    CHECK(record.IsObject());
    CHECK(record.Find("acceleration") != nullptr);
    CHECK_NEAR(record.Find("acceleration")->AsNumber(0.0), -1.5, 1e-6);
    CHECK_NEAR(record.Find("productionTime")->AsNumber(0.0), 1000.5, 1e-12);
    CHECK_NEAR(record.Find("arrival_mono_s")->AsNumber(0.0), 1000.62, 1e-12);
    CHECK(record.Find("valid")->AsBool(false));
    CHECK(record.Find("planReference")->AsString("") == "runA/12");
    CHECK(clocks_clock(record, "productionTime") == "monotonic");
    // No computed latency in the record.
    CHECK(record.Find("age_s") == nullptr);
  }
  {
    const Value record = parse(de4sdv::driving::log::Drop(command, 1000.62, "stale_production_time", 3),
                               &error);
    CHECK(error.empty());
    CHECK(record.Find("reason")->AsString("") == "stale_production_time");
    CHECK(record.Find("droppedTotal")->AsNumber(-1.0) == 3.0);
    CHECK(clocks_clock(record, "productionTime") == "monotonic");
  }
  {
    const Value record =
        parse(de4sdv::driving::log::VehicleControl(37, 0.4, 0.0, -0.2, false, "command"), &error);
    CHECK(error.empty());
    CHECK(record.Find("frame")->AsNumber(-1.0) == 37.0);
    CHECK(record.Find("t_sim_ms")->AsNumber(-1.0) == 3700.0);
    CHECK_NEAR(record.Find("throttle")->AsNumber(0.0), 0.4, 1e-12);
    CHECK_NEAR(record.Find("brake")->AsNumber(0.0), 0.0, 1e-12);
    CHECK_NEAR(record.Find("steer")->AsNumber(0.0), -0.2, 1e-12);
    CHECK(record.Find("controlSource")->AsString("") == "actuationAdapter");
    CHECK(clocks_clock(record, "t_sim_ms") == "simulation");
  }

  ActuationStatePayload state{};
  state.applied = 1;
  state.acceleration = 1.0F;
  state.steeringAngle = 5.0F;
  state.actuationTime = 3.7;
  std::snprintf(state.planReference, sizeof state.planReference, "runA/37");
  {
    const Value record = parse(de4sdv::driving::log::ActuationState(state, "kNone"), &error);
    CHECK(error.empty());
    CHECK(record.Find("applied")->AsNumber(-1.0) == 1.0);
    CHECK(record.Find("stopInForce")->AsNumber(-1.0) == 0.0);
    CHECK(clocks_clock(record, "actuationTime") == "simulation");
    CHECK(clocks_clock(record, "stopSince") == "simulation");
    CHECK(clocks_clock(record, "stopSinceMono") == "monotonic");
    CHECK_NEAR(record.Find("stopSinceMono")->AsNumber(-1.0), 0.0, 1e-12);
    CHECK(record.Find("planReference")->AsString("") == "runA/37");
  }
  {
    // The stop's own record: the same field names as the payload plus its clock.
    state.applied = 0;
    state.stopInForce = 1;
    state.cause = Cause::kCommandTimeout;
    state.acceleration = -4.0F;
    state.actuationTime = 3.8;
    state.stopSince = 3.8;
    state.stopSinceMono = 1001.9;
    std::memset(state.planReference, 0, sizeof state.planReference);

    const Value record = parse(de4sdv::driving::log::ActuationState(state, "kCommandTimeout"),
                               &error);
    CHECK(error.empty());
    CHECK(record.Find("cause")->AsString("") == "kCommandTimeout");
    CHECK_NEAR(record.Find("stopSince")->AsNumber(0.0), 3.8, 1e-12);
    CHECK_NEAR(record.Find("stopSinceMono")->AsNumber(0.0), 1001.9, 1e-12);
    CHECK(clocks_clock(record, "stopSinceMono") == "monotonic");

    const Value begin =
        parse(de4sdv::driving::log::StopResponseBegin(state, "kCommandTimeout"), &error);
    CHECK(error.empty());
    CHECK(begin.Find("cause")->AsString("") == "kCommandTimeout");
    CHECK_NEAR(begin.Find("actuationTime")->AsNumber(0.0), 3.8, 1e-12);
    CHECK_NEAR(begin.Find("stopSinceMono")->AsNumber(0.0), 1001.9, 1e-12);
    CHECK(clocks_clock(begin, "actuationTime") == "simulation");
    CHECK(clocks_clock(begin, "stopSinceMono") == "monotonic");
  }
  {
    const Value record = parse(de4sdv::driving::log::StopResponseStandstill(37, 0.02, "kCommandTimeout"),
                               &error);
    CHECK(error.empty());
    CHECK(record.Find("cause")->AsString("") == "kCommandTimeout");
    CHECK(record.Find("t_sim_ms")->AsNumber(-1.0) == 3700.0);
    CHECK_NEAR(record.Find("speedMps")->AsNumber(0.0), 0.02, 1e-12);
    CHECK(clocks_clock(record, "t_sim_ms") == "simulation");
  }
  {
    // Non-finite values are JSON null (ICD v2 §6).
    state.acceleration = std::numeric_limits<float>::quiet_NaN();
    const std::string text = de4sdv::driving::log::ActuationState(state, "kCommandTimeout");
    CHECK(text.find("\"acceleration\":null") != std::string::npos);
  }
}

}  // namespace

int main(int argc, char** argv) {
  const std::string config_path = argc > 1 ? argv[1] : "config/vehicle_limits.json";
  std::printf("ADAPTER_CORE_TESTS config=%s\n", config_path.c_str());

  TestTrackingOfConstantAcceleration();
  TestWatchdogFiresOnlyAfterMoreThan200ms();
  TestOneLateOrMissedCommandDoesNotStop();
  TestACommandAtTheBoundaryPreventsTheStop();
  TestInvalidCommandsDoNotFeedTheWatchdog();
  TestStopToStandstillAndHold();
  TestInvalidCommandsAreRejected();
  TestSteeringMappingSignsAndClamps();
  TestSteeringTurnsTheWheelsByTheCommandedAngle();
  TestTheVehiclesMaximumSteeringAngleIsValidated();
  TestWithoutTheVehiclesMaximumSteeringAngleTheSteerIsStraight();
  TestAgentStopIsAnOrdinaryCommand();
  TestStartupHoldWithoutStop();
  TestValidityWindowIsMinus5To300Ms();
  TestStopSinceMonoIsTheMonotonicStopBeginTime();
  TestStopClampsToConfiguredDeceleration();
  TestActuationStateTimesAndReferences();
  TestConfigParsing(config_path);
  TestIcdV2ConfigDocument();
  TestLogRecordsCarryClocksAndSuffixes();

  std::printf("ADAPTER_CORE_TESTS %s: %d checks, %d failures\n",
              g_failures == 0 ? "PASS" : "FAIL", g_checks, g_failures);
  return g_failures == 0 ? 0 : 1;
}
