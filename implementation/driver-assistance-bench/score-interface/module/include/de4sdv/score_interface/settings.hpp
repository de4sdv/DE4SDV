// DE4SDV S-CORE interface for VisionPilot (INC-DRIVING-002, not part of upstream VisionPilot).
//
// The DE4SDV interface configuration, a key=value file in the format of upstream's vision_pilot.conf. The identity
// recorder hashes it with the other configuration files (MAP-DRIVING-DA-CANDIDATE-RECORD).
#pragma once

#include <string>

#include "de4sdv/score_interface/seams.hpp"

namespace de4sdv::score_interface {

inline constexpr const char* kSettingsPathVariable = "DE4SDV_SCORE_INTERFACE_CONFIG";
inline constexpr const char* kDefaultSettingsPath = "config/de4sdv_score_interface.conf";

struct Settings {
  std::string mw_com_config;  // mw_com.config, required
  CarlaSettings carla;        // carla.host, carla.hero_role, carla.camera_role required
  std::string log_path;       // log.path, optional: JSON lines of every event the module sends or receives
};

// Reads the file; false with the reason on a missing file, a malformed line, a missing required key, an unknown
// key or a value out of range.
bool LoadSettings(const std::string& path, Settings* out, std::string* error);

// The path from DE4SDV_SCORE_INTERFACE_CONFIG, else config/de4sdv_score_interface.conf in the working directory.
std::string SettingsPath();

}  // namespace de4sdv::score_interface
