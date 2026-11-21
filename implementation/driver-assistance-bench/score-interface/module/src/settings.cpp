// DE4SDV S-CORE interface for VisionPilot (INC-DRIVING-002, not part of upstream VisionPilot). See settings.hpp.
#include "de4sdv/score_interface/settings.hpp"

#include <cstdlib>
#include <fstream>
#include <map>
#include <string>

namespace de4sdv::score_interface {

namespace {

std::string Trim(const std::string& s) {
  const auto a = s.find_first_not_of(" \t\r\n");
  if (a == std::string::npos) return "";
  return s.substr(a, s.find_last_not_of(" \t\r\n") - a + 1);
}

bool ParseNumber(const std::string& text, double low, double high, double* out) {
  char* end = nullptr;
  const double v = std::strtod(text.c_str(), &end);
  if (end == text.c_str() || *end != '\0' || !(v >= low && v <= high)) return false;
  *out = v;
  return true;
}

}  // namespace

bool LoadSettings(const std::string& path, Settings* out, std::string* error) {
  std::ifstream file(path);
  if (!file) {
    *error = "cannot open " + path;
    return false;
  }
  std::map<std::string, std::string> kv;
  std::string line;
  int number = 0;
  while (std::getline(file, line)) {
    ++number;
    line = Trim(line);
    if (line.empty() || line[0] == '#') continue;
    const auto eq = line.find('=');
    if (eq == std::string::npos || Trim(line.substr(0, eq)).empty()) {
      *error = path + ":" + std::to_string(number) + ": expected key = value";
      return false;
    }
    kv[Trim(line.substr(0, eq))] = Trim(line.substr(eq + 1));
  }
  static const char* const kKnown[] = {"mw_com.config",     "carla.host",      "carla.port",
                                       "carla.timeout_s",   "carla.attach_timeout_s",
                                       "carla.hero_role",   "carla.camera_role", "log.path"};
  for (const auto& entry : kv) {
    bool known = false;
    for (const char* k : kKnown) known = known || entry.first == k;
    if (!known) {
      *error = path + ": unknown key " + entry.first;
      return false;
    }
  }
  for (const char* k : {"mw_com.config", "carla.host", "carla.hero_role", "carla.camera_role"}) {
    const auto it = kv.find(k);
    if (it == kv.end() || it->second.empty()) {
      *error = path + ": missing required key " + k;
      return false;
    }
  }
  Settings s;
  s.mw_com_config = kv["mw_com.config"];
  s.carla.host = kv["carla.host"];
  s.carla.hero_role = kv["carla.hero_role"];
  s.carla.camera_role = kv["carla.camera_role"];
  if (kv.count("log.path") != 0) s.log_path = kv["log.path"];
  double v = 0.0;
  if (kv.count("carla.port") != 0) {
    if (!ParseNumber(kv["carla.port"], 1.0, 65535.0, &v) || v != static_cast<int>(v)) {
      *error = path + ": carla.port must be an integer from 1 to 65535";
      return false;
    }
    s.carla.port = static_cast<int>(v);
  }
  if (kv.count("carla.timeout_s") != 0) {
    if (!ParseNumber(kv["carla.timeout_s"], 0.1, 600.0, &v)) {
      *error = path + ": carla.timeout_s must be from 0.1 to 600";
      return false;
    }
    s.carla.timeout_s = v;
  }
  if (kv.count("carla.attach_timeout_s") != 0) {
    if (!ParseNumber(kv["carla.attach_timeout_s"], 0.1, 3600.0, &v)) {
      *error = path + ": carla.attach_timeout_s must be from 0.1 to 3600";
      return false;
    }
    s.carla.attach_timeout_s = v;
  }
  *out = s;
  return true;
}

std::string SettingsPath() {
  const char* path = std::getenv(kSettingsPathVariable);
  return (path != nullptr && path[0] != '\0') ? path : kDefaultSettingsPath;
}

}  // namespace de4sdv::score_interface
