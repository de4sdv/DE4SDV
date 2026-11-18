// The actuation adapter's run configuration: how its simulator client finds
// the simulator and the ego vehicle. One JSON object per run:
//
//   {
//     "carla_host": "127.0.0.1",
//     "carla_port": 2000,
//     "client_timeout_s": 30.0,
//     "hero_role_name": "hero",
//     "hero_wait_s": 20.0
//   }
//
// Every key is optional; an absent key keeps the default shown. An unknown key
// is refused. The rules of MAP-DRIVING-DA-COMMAND (the 0.1 s delay bound, the
// speed rule's 2 s, jerk 10.0, steerSpeed 0.0) are not configuration: they
// are the model's and live in actuation_core.h, so a run cannot change them,
// and a configuration that names one of them is refused as an unknown key.
#pragma once

#include <string>

namespace de4sdv::driver_assistance::actuation {

struct AdapterConfig {
  std::string carla_host = "127.0.0.1";
  int carla_port = 2000;
  double client_timeout_s = 30.0;
  std::string hero_role_name = "hero";
  double hero_wait_s = 20.0;
};

// Parses the configuration document. Returns false and sets *error on a
// malformed document, an unknown key, a value of the wrong type, a port
// outside 1..65535 or not whole, a time that is not finite and positive, or an
// empty host or role name.
AdapterConfig ParseAdapterConfig(const std::string& json_text, bool* ok, std::string* error);

// Reads and parses the file; returns false and sets *error when the file
// cannot be read or the document is invalid.
AdapterConfig LoadAdapterConfigFile(const std::string& path, bool* ok, std::string* error);

}  // namespace de4sdv::driver_assistance::actuation
