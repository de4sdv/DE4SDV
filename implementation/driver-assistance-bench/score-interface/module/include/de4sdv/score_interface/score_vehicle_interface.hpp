// DE4SDV S-CORE interface for VisionPilot (INC-DRIVING-002, not part of upstream VisionPilot).
//
// SCOREVehicleInterface of the model: upstream's vehicle seam (vehicle_interface.hpp:11, 14).
//   read():  the ego speed in m/s from the newest world snapshot (MAP-DRIVING-DA-VEHICLE-SPEED);
//   write(): the driving command on mw::com (MAP-DRIVING-DA-COMMAND) through DrivingCommandWriter: issueTime, a
//            sequence count from 1, the check value, and nothing before the candidate record (REQ-DRIVING-044).
#pragma once

#include <cstdint>
#include <functional>

#include <vehicle_interface/vehicle_interface.hpp>

#include "de4sdv/score_interface/core.hpp"
#include "de4sdv/score_interface/seams.hpp"

namespace de4sdv::score_interface {

class ScoreVehicleInterface : public VehicleInterface {
 public:
  using SpeedSource = std::function<bool(EgoVelocity*)>;
  ScoreVehicleInterface(SpeedSource speed_source, DrivingCommandWriter* writer, LineLog log);
  ~ScoreVehicleInterface() override = default;

  // 0.0 while the client holds no snapshot of the hero yet (counted).
  double read() override;
  // steering: the plan's steering[1], a tyre angle in rad; acceleration in m/s^2 (vision_pilot.cpp:174).
  void write(double steering, double acceleration) override;

  std::uint64_t speed_unavailable() const { return speed_unavailable_; }

 private:
  SpeedSource speed_source_;
  DrivingCommandWriter* writer_;
  LineLog log_;
  std::uint64_t speed_unavailable_ = 0;
};

}  // namespace de4sdv::score_interface
