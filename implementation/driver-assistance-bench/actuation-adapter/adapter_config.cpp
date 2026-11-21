#include "adapter_config.h"

#include <cmath>
#include <fstream>
#include <sstream>

#include "json_lite.h"

namespace de4sdv::driver_assistance::actuation {
namespace {

using json::Value;

bool Fail(std::string* error, const std::string& message) {
  if (error != nullptr) *error = message;
  return false;
}

bool ReadString(const Value& value, const char* key, std::string* out, std::string* error) {
  if (!value.IsString() || value.AsString("").empty()) {
    return Fail(error, std::string(key) + " must be a non-empty string");
  }
  *out = value.AsString("");
  return true;
}

bool ReadPositiveSeconds(const Value& value, const char* key, double* out, std::string* error) {
  const double seconds = value.AsNumber(-1.0);
  if (!value.IsNumber() || !std::isfinite(seconds) || seconds <= 0.0) {
    return Fail(error, std::string(key) + " must be a finite number above 0");
  }
  *out = seconds;
  return true;
}

bool ReadPort(const Value& value, int* out, std::string* error) {
  const double port = value.AsNumber(-1.0);
  if (!value.IsNumber() || !std::isfinite(port) || port != std::floor(port) || port < 1.0 ||
      port > 65535.0) {
    return Fail(error, "carla_port must be a whole number from 1 to 65535");
  }
  *out = static_cast<int>(port);
  return true;
}

}  // namespace

AdapterConfig ParseAdapterConfig(const std::string& json_text, bool* ok, std::string* error) {
  if (ok != nullptr) *ok = false;
  AdapterConfig config;
  std::string parse_error;
  const Value document = Value::Parse(json_text, &parse_error);
  if (!parse_error.empty()) {
    Fail(error, "configuration: " + parse_error);
    return config;
  }
  if (!document.IsObject()) {
    Fail(error, "configuration: the document must be a JSON object");
    return config;
  }
  for (const auto& [key, value] : document.members()) {
    bool read = false;
    if (key == "carla_host") {
      read = ReadString(value, "carla_host", &config.carla_host, error);
    } else if (key == "carla_port") {
      read = ReadPort(value, &config.carla_port, error);
    } else if (key == "client_timeout_s") {
      read = ReadPositiveSeconds(value, "client_timeout_s", &config.client_timeout_s, error);
    } else if (key == "hero_role_name") {
      read = ReadString(value, "hero_role_name", &config.hero_role_name, error);
    } else if (key == "hero_wait_s") {
      read = ReadPositiveSeconds(value, "hero_wait_s", &config.hero_wait_s, error);
    } else {
      read = Fail(error, "configuration: unknown key " + key);
    }
    if (!read) return AdapterConfig{};
  }
  if (ok != nullptr) *ok = true;
  return config;
}

AdapterConfig LoadAdapterConfigFile(const std::string& path, bool* ok, std::string* error) {
  if (ok != nullptr) *ok = false;
  std::ifstream file(path);
  if (!file) {
    Fail(error, "cannot read " + path);
    return AdapterConfig{};
  }
  std::ostringstream text;
  text << file.rdbuf();
  return ParseAdapterConfig(text.str(), ok, error);
}

}  // namespace de4sdv::driver_assistance::actuation
