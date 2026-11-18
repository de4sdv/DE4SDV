// DE4SDV S-CORE interface for VisionPilot (INC-DRIVING-002, not part of upstream VisionPilot).
//
// The three seams of the module. Everything behind them is a separate translation unit that only the S-CORE Bazel
// build compiles:
//   - SimulatorClient: the CARLA 1.0 C++ client (src/carla_client.cpp, C++20);
//   - MwComPorts: the LoLa/mw::com skeletons and the proxy (src/lola_bindings.cpp, C++17);
//   - LifecycleClient: S-CORE Lifecycle's report_running and Alive API (src/lifecycle_bindings.cpp, C++17).
// The module's own units see only these abstract interfaces, so the unit tests replace them with fakes.
#pragma once

#include <cstddef>
#include <cstdint>
#include <functional>
#include <memory>
#include <string>

#include "de4sdv/driver_assistance/payloads.h"

namespace de4sdv::score_interface {

// One front-camera image as the simulator client delivers it (MAP-DRIVING-DA-CAMERA-IMAGE, "in"): 8-bit BGRA
// pixels, the frame number and the simulation time of the world snapshot the image was rendered in. The pixels are
// valid only during the callback.
struct CameraImageView {
  std::uint64_t frame = 0;
  double sim_time_s = 0.0;
  int width = 0;
  int height = 0;
  std::size_t row_bytes = 0;  // bytes per row, at least 4 * width
  const std::uint8_t* bgra = nullptr;
};

// The velocity of the ego vehicle in one world snapshot (MAP-DRIVING-DA-VEHICLE-SPEED, "in"), m/s.
struct EgoVelocity {
  std::uint64_t frame = 0;
  double sim_time_s = 0.0;
  double x = 0.0;
  double y = 0.0;
  double z = 0.0;
};

// The simulator client. It attaches to the hero and its front camera that the world side spawned; it never spawns,
// ticks or controls anything.
class SimulatorClient {
 public:
  using ImageHandler = std::function<void(const CameraImageView&)>;
  virtual ~SimulatorClient() = default;
  // Connects and waits for the hero and its front camera. Blocks up to the attach timeout.
  virtual bool Attach(std::string* error) = 0;
  // Starts listening on the front camera; the handler runs on the client's thread.
  virtual bool Start(ImageHandler on_image, std::string* error) = 0;
  // The hero's velocity in the newest world snapshot the client holds; false if there is none.
  virtual bool NewestEgoVelocity(EgoVelocity* out) = 0;
  virtual void Stop() = 0;  // idempotent
};

// mw::com, one port per event of the S-CORE path (interfaces/ICD.md).
class DrivingCommandSink {  // de4sdv/driver_assistance/driving_command, MAP-DRIVING-DA-COMMAND
 public:
  virtual ~DrivingCommandSink() = default;
  virtual bool Send(const driver_assistance::DrivingCommandEventPayload& payload) = 0;
};

class WarningRequestSink {  // de4sdv/driver_assistance/warning_request, MAP-DRIVING-DA-WARNING-REQUEST
 public:
  virtual ~WarningRequestSink() = default;
  // The 8 SOME/IP bytes of EncodeWarningRequestSomeip, as they are.
  virtual bool Send(const std::uint8_t* bytes, std::size_t size) = 0;
};

class CandidateRecordSource {  // de4sdv/driver_assistance/candidate_record, MAP-DRIVING-DA-CANDIDATE-RECORD
 public:
  virtual ~CandidateRecordSource() = default;
  // Non-blocking: the newest sample received since the last call, if any.
  virtual bool TakeNewest(driver_assistance::CandidateRecordEventPayload* out) = 0;
};

struct MwComPorts {
  std::unique_ptr<DrivingCommandSink> command;
  std::unique_ptr<WarningRequestSink> warning;
  std::unique_ptr<CandidateRecordSource> record;
};

struct CarlaSettings {
  std::string host;
  int port = 2000;
  double timeout_s = 10.0;
  double attach_timeout_s = 300.0;
  std::string hero_role;
  std::string camera_role;
};

// The Launch Manager of S-CORE Lifecycle v0.10.0 as the module sees it, for the supervision decision of 2026-11-18:
// the Launch Manager supervises the candidate's process by its alive notifications.
class LifecycleClient {
 public:
  virtual ~LifecycleClient() = default;
  // score_mw_lifecycle_report_running(): the process is ready; the Launch Manager then starts its alive supervision.
  virtual bool ReportRunning() = 0;
  // score::mw::lifecycle::Alive::ReportAlive(): one alive notification. Called from one thread only.
  virtual void ReportAlive() = 0;
};

// Defined in src/lifecycle_bindings.cpp (S-CORE Lifecycle v0.10.0). nullptr, with the reason, when the Launch Manager
// did not start this process as a supervised component (LCM_ALIVE_INTERFACE_PATH unset) or the Alive instance fails.
std::unique_ptr<LifecycleClient> MakeLifecycleClient(std::string* reason);

// Defined in src/carla_client.cpp (C++20, CARLA 1.0 client library).
std::unique_ptr<SimulatorClient> MakeCarlaClient(const CarlaSettings& settings);

// Defined in src/lola_bindings.cpp (mw::com). Initializes the mw::com runtime with the given configuration, offers
// the two skeletons and starts finding the candidate record service. Ports are null on failure, with the reason.
MwComPorts MakeLolaPorts(const std::string& mw_com_config_path, std::string* error);

}  // namespace de4sdv::score_interface
