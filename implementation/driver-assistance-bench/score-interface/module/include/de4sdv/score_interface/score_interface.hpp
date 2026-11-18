// DE4SDV S-CORE interface for VisionPilot (INC-DRIVING-002, not part of upstream VisionPilot).
//
// The module as the loop sees it: the S-CORE branch beside vision_pilot.cpp:59-79 calls Start() when
// source.mode = score, takes camera() and vehicle() as its two interfaces, installs the SIGTERM handler, and the
// loop hands each plan to warning_request_publisher() after the write at vision_pilot.cpp:174.
//
// Ownership: the object owns the simulator client, the mw::com ports and every module; camera() and vehicle() share
// two of them. Destroy it after the loop: it stops the client first, then prints and logs the run's counters.
#pragma once

#include <cstdio>
#include <memory>
#include <mutex>
#include <string>

#include "de4sdv/score_interface/core.hpp"
#include "de4sdv/score_interface/score_camera_interface.hpp"
#include "de4sdv/score_interface/score_vehicle_interface.hpp"
#include "de4sdv/score_interface/score_warning_request_publisher.hpp"
#include "de4sdv/score_interface/seams.hpp"
#include "de4sdv/score_interface/settings.hpp"

namespace de4sdv::score_interface {

class ScoreInterface {
 public:
  // Reads the settings (SettingsPath()), makes the mw::com ports and the CARLA client with the two factories of
  // seams.hpp, attaches and starts. nullptr, with the reason on stderr, on any failure.
  static std::unique_ptr<ScoreInterface> Start();
  // The same from given parts; the unit tests pass fakes.
  static std::unique_ptr<ScoreInterface> Start(const Settings& settings, MwComPorts ports,
                                               std::unique_ptr<SimulatorClient> client, std::string* error);
  ~ScoreInterface();
  ScoreInterface(const ScoreInterface&) = delete;
  ScoreInterface& operator=(const ScoreInterface&) = delete;

  std::shared_ptr<ScoreCameraInterface> camera() const { return camera_; }
  std::shared_ptr<ScoreVehicleInterface> vehicle() const { return vehicle_; }
  ScoreWarningRequestPublisher& warning_request_publisher() { return *publisher_; }

  // The run's counters as one JSON object.
  std::string Summary() const;

 private:
  ScoreInterface() = default;
  void Log(const std::string& line);

  std::mutex log_mutex_;
  std::FILE* log_file_ = nullptr;
  LineLog log_;
  PassClock clock_;
  MwComPorts ports_;
  std::unique_ptr<SimulatorClient> client_;
  std::unique_ptr<CandidateRecordGate> gate_;
  std::unique_ptr<DrivingCommandWriter> command_writer_;
  std::unique_ptr<WarningRequestWriter> warning_writer_;
  std::shared_ptr<ScoreCameraInterface> camera_;
  std::shared_ptr<ScoreVehicleInterface> vehicle_;
  std::unique_ptr<ScoreWarningRequestPublisher> publisher_;
};

}  // namespace de4sdv::score_interface
