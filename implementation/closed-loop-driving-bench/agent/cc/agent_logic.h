// DE4SDV INC-DRIVING-001 slice 10b: the pure decision logic of the
// driving agent's activities.
//
// Three activities of the FEO chain are decided here, with no S-CORE, CARLA or
// Python in sight:
//   * conditionInputs  -> JudgeConditions (REQ-DRIVING-023, -024, -025)
//   * superviseLoop    -> Supervisor         (REQ-DRIVING-020..-022, -026, -027, -035)
//   * commandVehicle   -> Commander          (REQ-DRIVING-011, -012, -020..-022, -026)
// plus the record builders of ICD.md section 6 that the case evaluators read.
//
// Interface Control Document: ../../ICD.md (v2 + Amendment 1); the payloads are
// de4sdv/driving/payloads.h, the log writer de4sdv/driving/run_log.h, the design
// agent/DESIGN.md.
//
// Rules this file implements, and the ones it deliberately does not (the shell's
// job): the supervisor issues no command; the commander holds no plan; neither
// reads a clock of its own (the caller passes the monotonic time in, so every
// decision is reproducible in a test).
//
// Determinism: every age is computed from frame indices, never from a float
// stamp. One frame = one step = 100 ms of simulation time (ICD 1).
#pragma once

#include "rig.h"

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

#include "de4sdv/driving/payloads.h"

namespace de4sdv::driving::agent {

// ------------------------------------------------------------------ constants
// One step is 100 ms of simulation time; a frame index times this is the only
// time base of the conditions, the plan age and the command's sample index.
inline constexpr std::int64_t kStepMs = 100;

// REQ-DRIVING-023: an image captured more than 200 ms before the step is stale.
inline constexpr std::int64_t kCameraStaleMs = 200;
// REQ-DRIVING-024: a motion sample more than 200 ms old is stale.
inline constexpr std::int64_t kMotionStaleMs = 200;
// REQ-DRIVING-025: an announcement more than 1 s old is stale.
inline constexpr std::int64_t kRouteStaleMs = 1000;
// REQ-DRIVING-026: a newest valid plan more than 300 ms old is stale.
inline constexpr std::int64_t kPlanStaleMs = 300;

// REQ-DRIVING-020: the stop response's deceleration, capped by the vehicle's
// configured deceleration limit (ICD 4).
inline constexpr double kStopAccelerationMps2 = 4.0;
// ICD 4 / REQ-DRIVING-022: at standstill while the speed is below this.
inline constexpr double kStandstillKmh = 0.1;

// ICD 5: the steering rate limit is per second; one step is 0.1 s.
inline constexpr double kRateLimitStepSeconds = 0.1;

// kCameraCount: rig.h

// Simulation age of `other_frame` at `step_frame`, in milliseconds. Never a
// float: (step - other) * 100.
std::int64_t AgeMs(std::uint64_t step_frame, std::uint64_t other_frame);

// Simulation milliseconds of an announcement's issue time, rounded once, so the
// comparison with the step's stamp stays integer.
std::int64_t IssueTimeMs(double issue_time_simulation_seconds);

// Simulation milliseconds of a frame (frame * 100), exact.
std::int64_t FrameMs(std::uint64_t frame);

// Simulation seconds of a frame (frame * 0.1), exact for multiples of 100 us.
double FrameSeconds(std::uint64_t frame);

// The plan sample index of a command: (step - plan) clamped to 0 .. 63. The
// commander uses it; in kDriving the REQ-DRIVING-026 age check makes the value
// 0..3, so the upper clamp is defensive against a shell that passes an older
// plan past the age check.
std::uint64_t PlanSampleIndex(std::uint64_t step_frame, std::uint64_t plan_frame);

// ------------------------------------------------------------------ names
const char* ModeName(Mode mode);
const char* CauseName(Cause cause);
const char* LawName(int law);  // "first_control", "pure_pursuit", "unknown"

// A cause's bit in the input-condition mask: 1u << static_cast<unsigned>(cause).
std::uint32_t CauseBit(Cause cause);

// ------------------------------------------------------------------ conditionInputs
// The configured image size of one camera (ICD 10 C2 / REQ-DRIVING-003). A
// camera whose delivered image differs in either dimension is invalid.
struct CameraSize {
  int width = 0;
  int height = 0;
};

// One camera's image in the step's slot. `frame_index` is the image's own
// capture frame (the camera's frame number, not the step's).
struct CameraObservation {
  bool present = false;      // an image exists in the slot
  bool empty = false;        // present but zero bytes
  int width = 0;
  int height = 0;
  bool has_frame = false;    // the image's frame index is known
  std::uint64_t frame_index = 0;
};

// The newest ego-motion sample the agent holds. `has_sample` is false before the
// first sample ever arrived, which REQ-DRIVING-024 counts as invalid.
struct MotionObservation {
  bool has_sample = false;
  std::uint64_t frame_index = 0;   // the sample's capture frame
  EgoMotionSamplePayload sample{}; // VSS units (km/h, m/s^2, deg/s)
};

// The route channel at a step (MAP-DRIVING-ROUTE).
struct RouteObservation {
  bool has_announcement = false;
  std::uint32_t corridor_points = 0;   // the newest announcement's corridor
  double issue_time = 0.0;             // simulation seconds of that announcement
  std::uint32_t raster_corridor_cells = 0;  // corridor cells of this step's raster
};

struct StepConditions {
  std::uint64_t step_frame = 0;
  CameraObservation cameras[kCameraCount];
  MotionObservation motion;
  RouteObservation route;
};

// The one input-condition word of a step, plus the causes it names in ascending
// Cause order (the supervisor's deterministic tie-break).
struct ConditionResult {
  std::uint32_t bits = 0;
  std::vector<Cause> causes;

  bool Has(Cause cause) const { return (bits & CauseBit(cause)) != 0; }
  bool Any() const { return bits != 0; }
  Cause Lowest() const;  // kNone when empty; the minimum Cause value otherwise
};

// Judges one step. `sizes` are the six configured camera sizes in slot order
// (front, front_left, front_right, rear_left, rear, rear_right).
ConditionResult JudgeConditions(const StepConditions& conditions,
                                const CameraSize sizes[kCameraCount]);

// REQ-DRIVING-023 as written (ICD A28): a camera is judged by its newest valid
// image to date, not only by the image of the step. A camera whose image of the
// step missed the frame deadline is observed through that newest image, so the
// step has no camera condition while the image is at most 200 ms older than
// the step (kCameraStale beyond); kCameraMissing means no valid image to date.
// An invalid image of the step is observed as it is (kCameraInvalid).
class CameraHistory {
 public:
  // The observations JudgeConditions takes for one step, from the images the
  // frame store handed over for it (`arrived`: present, size and frame index
  // as delivered). A valid image of the step becomes the camera's newest.
  void Observe(const CameraObservation arrived[kCameraCount],
               const CameraSize sizes[kCameraCount],
               CameraObservation observed[kCameraCount]);
  // A frame merged into a later step (ICD A23) whose cameras were all valid
  // and which went into the checkpoint's histories: its images count as
  // received, as the case evaluators count them.
  void RecordMergedFrame(std::uint64_t frame);

 private:
  bool has_valid_[kCameraCount] = {};
  std::uint64_t newest_valid_frame_[kCameraCount] = {};
};

// REQ-DRIVING-027: a plan is valid when sampleCount == 64 and all 64
// acceleration and curvature values are finite. x, y and heading are not judged.
bool IsPlanValid(const DrivingPlanPayload& plan);

// Whether the planner's histories are ready at a step: C2 `primed`, C10 `priming.complete`, and inferPlan's
// choice between warming and planning (ICD A26). With a planner engine only the engine knows, and only for
// a step it conditioned: a step it did not condition (an input condition, a refused checkpoint) is not
// in the histories, so it is not primed. Without an engine (the stand-in), the histories are the number of
// steps since the first one.
bool StepPrimed(bool engine, bool conditioned, bool engine_primed, std::uint64_t frame,
                std::uint64_t first_frame, std::uint64_t priming_frames);

// REQ-DRIVING-035: the checkpoint refusal detail the agent carries.
struct RefusalDetail {
  bool refused = false;
  std::string expected_sha256;  // 64 hex characters, or empty for "no_pin"
  std::string actual_sha256;    // 64 hex characters
  std::string reason;           // "mismatch" | "no_pin"
};

// ------------------------------------------------------------------ superviseLoop
struct SupervisorStep {
  Mode mode = Mode::kStarting;
  Cause cause = Cause::kNone;
  bool mode_changed = false;   // the mode differs from the previous Step's
  bool stop_began = false;     // the stop response began at this step
  // The newest valid plan, or nullptr before the first one. It points into the
  // supervisor's own storage and stays valid until the next Step call.
  const DrivingPlanPayload* newest_valid_plan = nullptr;
  DrivingModePayload mode_payload{};
};

// The latching mode machine of superviseLoop (REQ-DRIVING-020..-029, -035).
//
// One Step per step, in step order. The newest valid plan is retained here, so
// the commander always receives the newest plan that was ever valid: an invalid
// plan never replaces it (REQ-DRIVING-027).
class Supervisor {
 public:
  explicit Supervisor(RefusalDetail refusal = RefusalDetail());

  // `plan_this_step` is the plan produced at this step, valid or not; nullptr
  // when none was produced. `motion` is the step's newest motion sample (the
  // standstill test of REQ-DRIVING-022).
  SupervisorStep Step(std::uint64_t step_frame, double monotonic_seconds,
                      const ConditionResult& conditions,
                      const DrivingPlanPayload* plan_this_step,
                      const MotionObservation& motion);

  // The commander's latch (or the shell's re-check of REQ-DRIVING-026 at the
  // command). First cause wins, as in the step decision.
  void Latch(Cause cause, std::uint64_t frame, double monotonic_seconds);

  // Orderly end of a run: latches the stop response with kRunEnd when nothing
  // has latched yet.
  void EndRun(std::uint64_t frame, double monotonic_seconds);

  Mode mode() const { return mode_; }
  Cause cause() const { return cause_; }
  bool refused() const { return refusal_.refused; }
  bool has_valid_plan() const { return has_valid_plan_; }
  const DrivingPlanPayload& newest_valid_plan() const { return newest_valid_; }
  std::uint64_t cause_frame() const { return cause_frame_; }
  double cause_monotonic() const { return cause_monotonic_; }
  bool stop_pending() const { return stop_pending_; }

 private:
  void EnterStop(Cause cause, std::uint64_t frame, double monotonic_seconds);
  void FillModePayload(DrivingModePayload* payload, std::uint64_t step_frame,
                       double monotonic_seconds) const;

  RefusalDetail refusal_;
  Mode mode_ = Mode::kStarting;
  Cause cause_ = Cause::kNone;
  bool has_valid_plan_ = false;
  DrivingPlanPayload newest_valid_{};
  bool stop_pending_ = false;
  bool has_last_reported_ = false;
  Mode last_reported_ = Mode::kStarting;
  std::uint64_t cause_frame_ = 0;
  double cause_monotonic_ = 0.0;
};

// ------------------------------------------------------------------ commandVehicle
enum class CommandLaw { kFirstControl = 0, kPurePursuit = 1 };

// The vehicle configuration of ICD section 5, the fields the commander uses.
struct VehicleConfig {
  double wheelbase_m = 0.0;
  double max_acceleration_mps2 = 0.0;
  double max_deceleration_mps2 = 0.0;
  double max_road_wheel_angle_deg = 0.0;
  double max_steering_rate_deg_per_s = 0.0;
  CommandLaw law = CommandLaw::kFirstControl;
};

// Parses the ICD section 5 document. Returns false and sets *error on a missing
// or non-positive value, a non-numeric value, or a command_law other than
// "first_control" / "pure_pursuit".
bool ParseVehicleConfig(const std::string& json_text, VehicleConfig* out, std::string* error);

// Reads and parses the file; false and *error when it cannot be read.
bool LoadVehicleConfigFile(const std::string& path, VehicleConfig* out, std::string* error);

// The pure-pursuit steering of REQ-DRIVING-011's alternative law, on the plan's
// path in the plan's own frame: the vehicle at the origin, heading along x, as
// at the capture of the plan's frame. The first sample after sample k that lies
// at least the lookahead from the origin is the target, and the curvature of
// the arc from the origin through it is turned into a road-wheel angle. No
// sample's pose stands in for the vehicle's (ICD A32). Exposed for testing.
double PurePursuitLookaheadM(double speed_kmh);
double PurePursuitSteeringDeg(const DrivingPlanPayload& plan, std::uint64_t k,
                              double speed_kmh, double wheelbase_m);

// The steering of the first_control law: deg(atan(wheelbase * curvature[k])).
double FirstControlSteeringDeg(double wheelbase_m, double curvature);

struct CommandStep {
  bool has_command = false;             // false: kStarting issues no command
  VehicleMotionCommandPayload command{};
  std::uint64_t step_frame = 0;
  std::uint64_t step_capture_sim_ms = 0;
  bool has_plan = false;                // a plan was named: the newest valid plan when driving,
                                        // the plan of the held steering in the stop modes
  bool has_plan_capture = false;        // its capture stamp is known
  std::uint64_t plan_capture_sim_ms = 0;
  std::uint64_t sample_index = 0;       // k of the plan sample used
  bool has_sample_index = false;
  bool plan_stale = false;              // report kPlanStale to the shell
  CommandLaw law = CommandLaw::kFirstControl;
};

// commandVehicle: turns the mode and the newest valid plan into one command per
// step (REQ-DRIVING-011, -012, -020..-022, -026).
class Commander {
 public:
  explicit Commander(const VehicleConfig& config);

  CommandStep Step(Mode mode, const DrivingPlanPayload* newest_valid_plan,
                   std::uint64_t step_frame, const MotionObservation& motion,
                   double monotonic_seconds);

  double held_steering_deg() const { return held_steering_deg_; }
  const VehicleConfig& config() const { return config_; }

 private:
  // Clamps to the road-wheel limit, then rate-limits against the previous
  // commanded angle. Returns the angle that may be commanded.
  double LimitSteering(double raw_deg);
  void EmitStopCommand(CommandStep* out, double monotonic_seconds);

  VehicleConfig config_;
  double held_steering_deg_ = 0.0;   // last value computed from a valid plan
  bool has_held_steering_ = false;
  // The plan the held steering was computed from. A stop command names it, frozen
  // when the stop begins (REQ-DRIVING-011: a command names the plan it was computed
  // from; VC-DRIVING-022: no command after T0 names a plan captured after T0).
  std::string held_plan_reference_;
  std::uint64_t held_plan_frame_ = 0;
  double previous_commanded_deg_ = 0.0;  // the rate limiter's state, starts at 0
};

// ------------------------------------------------------------------ records
// The data object of each record, as ICD.md section 6 defines it: payload
// fields keep their model names and carry a sibling "clocks" object; shell-only
// stamps carry a clock suffix; non-finite numbers become JSON null.
//
// The shell writes these with RunLog::Write(event, seq, data_json).
namespace record {

// `in.plan`: the commander's view of the newest valid plan, one per step.
std::string InPlan(const DrivingPlanPayload& plan);
// `out.plan`: the producer's view (inferPlan), identical payload shape.
std::string OutPlan(const DrivingPlanPayload& plan);
// `out.mode`: the decision of superviseLoop.
std::string OutMode(const DrivingModePayload& mode);
// `stop_response.begin`: the stop began at this step.
std::string StopBegin(std::uint64_t frame, Cause cause, const char* source,
                      double monotonic_seconds);
// `stop_response.standstill`: the stop reached the standstill threshold.
std::string Standstill(std::uint64_t frame, Cause cause, double speed_kmh,
                       double monotonic_seconds);
// `out.command`: commandVehicle's command, with ICD v2 C3's two sim stamps.
std::string OutCommand(const CommandStep& step);
// `out.condition`: the input-condition word and its causes (C2 metadata; the
// shell embeds `input_conditions` in score/checkpointInputs.jsonl).
std::string Condition(const StepConditions& conditions, const ConditionResult& result);
// `error`: the checkpoint refusal, before any plan (ICD v2 C6).
std::string CheckpointRefusedError(const RefusalDetail& refusal);

}  // namespace record

}  // namespace de4sdv::driving::agent
