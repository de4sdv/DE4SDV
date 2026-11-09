// Vehicle limits and longitudinal calibration configuration of the actuation
// adapter (ICD v2 section 5). The file is one JSON object per run, the same one
// the commander reads:
//
//   {
//     "vehicle_blueprint": "vehicle.lincoln.mkz_2020",
//     "wheelbase_m": 2.85,
//     "max_acceleration_mps2": 3.0,
//     "max_deceleration_mps2": 8.0,
//     "max_road_wheel_angle_deg": 35.0,
//     "max_steering_rate_deg_per_s": 180.0,
//     "command_law": "pure_pursuit",
//     "longitudinal_controller": {
//       "table": [[-8.0, 0.0, 1.0], [0.0, 0.0, 0.0], [3.0, 0.75, 0.0]],
//       "kp": 0.3,
//       "ki": 0.05,
//       "integrator_limit": 0.3
//     }
//   }
//
// That is the ICD v2 section 5 document verbatim. The adapter reads:
//
//  * the limits and vehicle_blueprint (validity, steering clamp, config log);
//  * "command_law": accepted and logged with the config record, then ignored
//    (the commander owns it; the adapter applies whatever command arrives);
//  * "longitudinal_controller.table": rows are [acceleration_mps2, throttle,
//    brake] arrays; the older object form
//    {"acceleration_mps2": .., "throttle": .., "brake": ..} is still accepted;
//  * "longitudinal_controller.kp"/"ki": the ICD v2 names, mapped onto
//    LongitudinalConfig::speed_kp/speed_ki (the "speed_kp"/"speed_ki" aliases
//    are still accepted, and the calibration script writes neither);
//  * "longitudinal_controller.integrator_limit".
//
// Adapter-only extensions, kept for the bench and documented in README.md:
//  * "longitudinal_controller.standstill_brake" (default 1.0);
//  * "longitudinal_controller.standstill_speed_kmh" (default 0.1, the
//    REQ-DRIVING-022 standstill threshold);
//  * the object row form above.
//
// Absent "longitudinal_controller", a built-in demo table is used and
// tableSource() reports TableSource::kDefault.
#pragma once

#include <string>
#include <vector>

namespace de4sdv::driving::actuation {

struct VehicleLimits {
  double max_acceleration_mps2 = 3.0;
  double max_deceleration_mps2 = 8.0;
  double max_road_wheel_angle_deg = 35.0;
};

struct LongitudinalPoint {
  double acceleration_mps2 = 0.0;
  double throttle = 0.0;
  double brake = 0.0;
};

// Feedforward lookup plus PI on the speed error against the reference speed
// integrated from the commanded acceleration. speed_kp/speed_ki carry the ICD
// v2 "kp"/"ki" values.
struct LongitudinalConfig {
  std::vector<LongitudinalPoint> table;  // ascending acceleration, one-sided pedals
  double speed_kp = 0.20;                // throttle fraction per m/s (ICD v2 "kp")
  double speed_ki = 0.10;                // throttle fraction per (m/s * s) ("ki")
  double integral_limit = 1.0;           // anti-windup clamp of the integral term
  double standstill_brake = 1.0;         // brake held at standstill (extension)
  double standstill_speed_kmh = 0.1;     // REQ-DRIVING-022 standstill threshold (extension)
};

enum class TableSource { kConfig, kDefault };

struct AdapterConfig {
  std::string vehicle_blueprint;
  double wheelbase_m = 2.85;
  double max_steering_rate_deg_per_s = 180.0;
  std::string command_law;  // ICD v2 section 5; read for the log, not acted on here
  VehicleLimits limits;
  LongitudinalConfig longitudinal;

  TableSource tableSource() const { return table_source_; }
  void setTableSource(TableSource source) { table_source_ = source; }

  // The stop response's deceleration (REQ-DRIVING-020): -4 m/s^2, clamped to
  // the configured deceleration limit so REQ-DRIVING-012 is not violated by a
  // vehicle whose limit is below 4 (only possible with a non-default config).
  double StopAccelerationMps2() const;

 private:
  TableSource table_source_ = TableSource::kDefault;
};

// Parses the configuration document. Returns false and sets *error on a
// malformed or inconsistent document (missing limits, non-positive angle,
// unsorted table, pedal outside [0,1], both pedals in one row, a table row
// that is neither a 3-number array nor an object).
AdapterConfig ParseAdapterConfig(const std::string& json_text, bool* ok, std::string* error);

// Reads and parses the file; returns false and sets *error when the file
// cannot be read or the document is invalid.
AdapterConfig LoadAdapterConfigFile(const std::string& path, bool* ok, std::string* error);

// The built-in demo table (uncalibrated; for a vehicle with 5 m/s^2 at full
// throttle and 10 m/s^2 at full brake, 0.05/s drag at 10 m/s).
const std::vector<LongitudinalPoint>& DefaultLongitudinalTable();

}  // namespace de4sdv::driving::actuation
