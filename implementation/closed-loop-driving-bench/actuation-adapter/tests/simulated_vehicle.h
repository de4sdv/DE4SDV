// Longitudinal point mass with drag and a first-order throttle/brake lag,
// stepped at 0.1 s of simulation time; a kinematic bicycle integrates the
// heading so the steering sign and clamp can be exercised.
//
// This is the test fixture, not a model of CARLA. Its parameters are the ones
// the test's calibration table was generated from (5 m/s^2 at full throttle,
// 10 m/s^2 at full brake, 0.05/s drag), so the feedforward lookup is exact at
// 10 m/s and the PI sees a realistic drag error elsewhere.
#pragma once

#include <algorithm>
#include <cmath>

#include "adapter_core.h"

namespace de4sdv::driving::actuation::test {

struct SimulatedVehicle {
  double speed_mps = 0.0;
  double acceleration_mps2 = 0.0;
  double heading_rad = 0.0;
  double wheelbase_m = 2.85;
  double max_road_wheel_angle_deg = 35.0;
  double lag_tau_s = 0.25;
  double throttle_gain_mps2 = 5.0;
  double brake_gain_mps2 = 10.0;
  double drag_per_s = 0.05;

  void Step(const VehicleControlCommand& control, double dt) {
    const double target =
        control.throttle * throttle_gain_mps2 - control.brake * brake_gain_mps2 -
        drag_per_s * speed_mps;
    const double alpha = 1.0 - std::exp(-dt / lag_tau_s);
    acceleration_mps2 += (target - acceleration_mps2) * alpha;
    if (speed_mps <= 0.0 && acceleration_mps2 < 0.0) acceleration_mps2 = 0.0;  // no reverse
    speed_mps = std::max(0.0, speed_mps + acceleration_mps2 * dt);
    const double delta_rad =
        control.steer * max_road_wheel_angle_deg * 3.14159265358979323846 / 180.0;
    const double yaw_rate = speed_mps / wheelbase_m * std::tan(delta_rad);
    heading_rad += yaw_rate * dt;
  }
};

}  // namespace de4sdv::driving::actuation::test
