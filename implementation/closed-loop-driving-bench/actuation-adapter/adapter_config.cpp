#include "adapter_config.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <sstream>

#include "json_lite.h"

namespace de4sdv::driving::actuation {
namespace {

bool Finite(double value) { return std::isfinite(value); }

bool InRange(double value, double low, double high) {
  return Finite(value) && value >= low && value <= high;
}

const std::vector<LongitudinalPoint>& BuildDefaultTable() {
  static const std::vector<LongitudinalPoint> table = [] {
    std::vector<LongitudinalPoint> rows;
    // 5 m/s^2 at throttle 1, 10 m/s^2 at brake 1, 0.5 m/s^2 of drag at 10 m/s.
    for (double acceleration = -8.0; acceleration <= 3.0001; acceleration += 0.5) {
      LongitudinalPoint row;
      row.acceleration_mps2 = acceleration;
      if (acceleration >= 0.0) {
        row.throttle = std::min(1.0, std::max(0.0, (acceleration + 0.5) / 5.0));
        row.brake = 0.0;
      } else {
        row.throttle = 0.0;
        row.brake = std::min(1.0, std::max(0.0, (-acceleration - 0.5) / 10.0));
      }
      rows.push_back(row);
    }
    return rows;
  }();
  return table;
}

bool Fail(std::string* error, const std::string& message) {
  if (error != nullptr) *error = message;
  return false;
}

}  // namespace

const std::vector<LongitudinalPoint>& DefaultLongitudinalTable() { return BuildDefaultTable(); }

double AdapterConfig::StopAccelerationMps2() const {
  // REQ-DRIVING-020 asks for 4 m/s^2; the stop may not exceed the vehicle's
  // configured deceleration limit (REQ-DRIVING-012). The default limit is 8.
  return -std::min(4.0, limits.max_deceleration_mps2);
}

AdapterConfig ParseAdapterConfig(const std::string& json_text, bool* ok, std::string* error) {
  if (ok != nullptr) *ok = false;
  AdapterConfig config;

  std::string parse_error;
  const json::Value root = json::Value::Parse(json_text, &parse_error);
  if (!parse_error.empty()) {
    Fail(error, "invalid JSON: " + parse_error);
    return config;
  }
  if (!root.IsObject()) {
    Fail(error, "the configuration must be a JSON object");
    return config;
  }

  const json::Value* blueprint = root.Find("vehicle_blueprint");
  if (blueprint != nullptr && blueprint->IsString()) {
    config.vehicle_blueprint = blueprint->AsString("");
  }

  const json::Value* wheelbase = root.Find("wheelbase_m");
  if (wheelbase == nullptr || !wheelbase->IsNumber()) {
    Fail(error, "wheelbase_m is required and must be a number");
    return config;
  }
  config.wheelbase_m = wheelbase->AsNumber(0.0);

  // ICD v2 section 5 "command_law": the commander's business, logged and then
  // ignored by this adapter. Reject only a non-string value.
  const json::Value* command_law = root.Find("command_law");
  if (command_law != nullptr) {
    if (!command_law->IsString()) {
      Fail(error, "command_law must be a string");
      return config;
    }
    config.command_law = command_law->AsString("");
  }

  const auto require_number = [&](const char* key, double* out) {
    const json::Value* value = root.Find(key);
    if (value == nullptr || !value->IsNumber()) {
      return Fail(error, std::string(key) + " is required and must be a number");
    }
    *out = value->AsNumber(0.0);
    return true;
  };
  if (!require_number("max_acceleration_mps2", &config.limits.max_acceleration_mps2) ||
      !require_number("max_deceleration_mps2", &config.limits.max_deceleration_mps2) ||
      !require_number("max_road_wheel_angle_deg", &config.limits.max_road_wheel_angle_deg) ||
      !require_number("max_steering_rate_deg_per_s", &config.max_steering_rate_deg_per_s)) {
    return config;
  }

  if (!(config.wheelbase_m > 0.0) || !Finite(config.wheelbase_m)) {
    Fail(error, "wheelbase_m must be positive");
    return config;
  }
  if (!(config.limits.max_acceleration_mps2 > 0.0) || !Finite(config.limits.max_acceleration_mps2)) {
    Fail(error, "max_acceleration_mps2 must be positive");
    return config;
  }
  if (!(config.limits.max_deceleration_mps2 > 0.0) || !Finite(config.limits.max_deceleration_mps2)) {
    Fail(error, "max_deceleration_mps2 must be positive");
    return config;
  }
  if (!(config.limits.max_road_wheel_angle_deg > 0.0) || !Finite(config.limits.max_road_wheel_angle_deg)) {
    Fail(error, "max_road_wheel_angle_deg must be positive");
    return config;
  }
  if (!(config.max_steering_rate_deg_per_s > 0.0) || !Finite(config.max_steering_rate_deg_per_s)) {
    Fail(error, "max_steering_rate_deg_per_s must be positive");
    return config;
  }

  config.longitudinal.table = DefaultLongitudinalTable();
  config.setTableSource(TableSource::kDefault);

  const json::Value* controller = root.Find("longitudinal_controller");
  if (controller == nullptr) {
    if (ok != nullptr) *ok = true;
    return config;
  }
  if (!controller->IsObject()) {
    Fail(error, "longitudinal_controller must be an object");
    return config;
  }

  const auto optional_number = [&](const json::Value& object, const char* key, double* out) {
    const json::Value* value = object.Find(key);
    if (value == nullptr) return true;
    if (!value->IsNumber()) {
      return Fail(error, std::string("longitudinal_controller.") + key + " must be a number");
    }
    *out = value->AsNumber(0.0);
    return true;
  };
  if (!optional_number(*controller, "standstill_brake", &config.longitudinal.standstill_brake) ||
      !optional_number(*controller, "standstill_speed_kmh", &config.longitudinal.standstill_speed_kmh)) {
    return config;
  }

  // Gains: ICD v2 names "kp"/"ki" first, then the older "speed_kp"/"speed_ki".
  const auto optional_gain = [&](const char* key, const char* alias, double* out) {
    const json::Value* value = controller->Find(key);
    if (value == nullptr) value = controller->Find(alias);
    if (value == nullptr) return true;
    if (!value->IsNumber()) {
      return Fail(error, std::string("longitudinal_controller.") + key + " must be a number");
    }
    *out = value->AsNumber(0.0);
    return true;
  };
  if (!optional_gain("kp", "speed_kp", &config.longitudinal.speed_kp) ||
      !optional_gain("ki", "speed_ki", &config.longitudinal.speed_ki) ||
      !optional_number(*controller, "integrator_limit", &config.longitudinal.integral_limit)) {
    return config;
  }

  if (!InRange(config.longitudinal.speed_kp, 0.0, 100.0)) {
    Fail(error, "longitudinal_controller.speed_kp must be in [0, 100]");
    return config;
  }
  if (!InRange(config.longitudinal.speed_ki, 0.0, 100.0)) {
    Fail(error, "longitudinal_controller.speed_ki must be in [0, 100]");
    return config;
  }
  if (!(config.longitudinal.integral_limit > 0.0) || !Finite(config.longitudinal.integral_limit)) {
    Fail(error, "longitudinal_controller.integral_limit must be positive");
    return config;
  }
  if (!InRange(config.longitudinal.standstill_brake, 0.0, 1.0)) {
    Fail(error, "longitudinal_controller.standstill_brake must be in [0, 1]");
    return config;
  }
  if (!InRange(config.longitudinal.standstill_speed_kmh, 0.0, 10.0)) {
    Fail(error, "longitudinal_controller.standstill_speed_kmh must be in [0, 10]");
    return config;
  }

  const json::Value* table = controller->Find("table");
  if (table == nullptr) {
    if (ok != nullptr) *ok = true;
    return config;  // gains only, demo table kept
  }
  if (!table->IsArray() || table->size() < 2) {
    Fail(error, "longitudinal_controller.table must be an array of at least two rows");
    return config;
  }

  std::vector<LongitudinalPoint> rows;
  rows.reserve(table->size());
  for (std::size_t i = 0; i < table->size(); ++i) {
    const json::Value* row = table->At(i);
    if (row == nullptr) {
      Fail(error, "longitudinal_controller.table row " + std::to_string(i) + " is missing");
      return config;
    }
    LongitudinalPoint point;
    if (row->IsArray()) {
      // ICD v2 form: [acceleration_mps2, throttle, brake].
      const json::Value* acceleration = row->At(0);
      const json::Value* throttle = row->At(1);
      const json::Value* brake = row->At(2);
      if (row->size() != 3 || acceleration == nullptr || !acceleration->IsNumber() ||
          throttle == nullptr || !throttle->IsNumber() || brake == nullptr || !brake->IsNumber()) {
        Fail(error, "longitudinal_controller.table row " + std::to_string(i) +
                        " must be [acceleration_mps2, throttle, brake] with three numbers");
        return config;
      }
      point.acceleration_mps2 = acceleration->AsNumber(0.0);
      point.throttle = throttle->AsNumber(0.0);
      point.brake = brake->AsNumber(0.0);
    } else if (row->IsObject()) {
      // Adapter extension, kept for older calibration files.
      const json::Value* acceleration = row->Find("acceleration_mps2");
      const json::Value* throttle = row->Find("throttle");
      const json::Value* brake = row->Find("brake");
      if (acceleration == nullptr || !acceleration->IsNumber() || throttle == nullptr ||
          !throttle->IsNumber() || brake == nullptr || !brake->IsNumber()) {
        Fail(error, "longitudinal_controller.table row " + std::to_string(i) +
                        " needs numeric acceleration_mps2, throttle and brake");
        return config;
      }
      point.acceleration_mps2 = acceleration->AsNumber(0.0);
      point.throttle = throttle->AsNumber(0.0);
      point.brake = brake->AsNumber(0.0);
    } else {
      Fail(error, "longitudinal_controller.table row " + std::to_string(i) +
                      " must be an array or an object");
      return config;
    }
    if (!Finite(point.acceleration_mps2) || !InRange(point.throttle, 0.0, 1.0) ||
        !InRange(point.brake, 0.0, 1.0)) {
      Fail(error, "longitudinal_controller.table row " + std::to_string(i) +
                      ": acceleration must be finite and the pedals in [0, 1]");
      return config;
    }
    if (point.throttle > 1e-9 && point.brake > 1e-9) {
      Fail(error, "longitudinal_controller.table row " + std::to_string(i) +
                      " sets throttle and brake together; one pedal per row");
      return config;
    }
    if (!rows.empty() && !(point.acceleration_mps2 > rows.back().acceleration_mps2)) {
      Fail(error, "longitudinal_controller.table must be sorted by strictly increasing acceleration_mps2");
      return config;
    }
    rows.push_back(point);
  }
  config.longitudinal.table = std::move(rows);
  config.setTableSource(TableSource::kConfig);
  if (ok != nullptr) *ok = true;
  return config;
}

AdapterConfig LoadAdapterConfigFile(const std::string& path, bool* ok, std::string* error) {
  if (ok != nullptr) *ok = false;
  AdapterConfig config;
  std::ifstream file(path);
  if (!file) {
    Fail(error, "cannot open the configuration file: " + path);
    return config;
  }
  std::ostringstream buffer;
  buffer << file.rdbuf();
  if (!file.good() && !file.eof()) {
    Fail(error, "cannot read the configuration file: " + path);
    return config;
  }
  return ParseAdapterConfig(buffer.str(), ok, error);
}

}  // namespace de4sdv::driving::actuation
