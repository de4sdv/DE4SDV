// DE4SDV closed-loop driving bench (INC-DRIVING-001, slice 10b): the hero's kinematics, from CARLA's
// world quantities to the frame store's snapshot and the published ego-motion sample. Pure functions,
// no LibCarla: the CARLA source passes plain numbers in.
//
// Conventions:
//   - CARLA (Unreal) is left-handed: x forward, y right, z up; rotations in degrees; a positive yaw
//     rate turns right. Velocity, acceleration and angular velocity come in world axes; angular
//     velocity in deg/s.
//   - HeroSnapshot (frame_store.h): pose as CARLA reports it; velocity and acceleration rotated into
//     the vehicle frame (x forward, y right, z up); angular velocity in rad/s, world axes.
//   - EgoMotionSamplePayload (payloads.h, MAP-DRIVING-EGO-MOTION): VSS signals, ISO 8855 frame
//     (x forward, y LEFT, z up): Vehicle.Acceleration.Lateral positive to the left,
//     Vehicle.AngularVelocity.Yaw positive to the left (counter-clockwise), deg/s. So both carry
//     CARLA's y and z with the opposite sign (DESIGN.md "Frame of the motion sample").
#pragma once

#include <cmath>
#include <cstdint>

#include "de4sdv/driving/payloads.h"
#include "frame_store.h"

namespace de4sdv::driving::agent {

struct CarlaKinematics {
  double x = 0.0, y = 0.0, z = 0.0;           // m, world
  double roll = 0.0, pitch = 0.0, yaw = 0.0;  // deg
  double vx = 0.0, vy = 0.0, vz = 0.0;        // m/s, world
  double ax = 0.0, ay = 0.0, az = 0.0;        // m/s^2, world
  double wx = 0.0, wy = 0.0, wz = 0.0;        // deg/s, world
};

// The columns of carla::geom::Transform::GetMatrix(): the vehicle's forward, right and up axes in
// world coordinates.
inline void CarlaAxes(double pitch_deg, double yaw_deg, double roll_deg, double fwd[3], double right[3],
                      double up[3]) {
  const double k = M_PI / 180.0;
  const double cy = std::cos(yaw_deg * k), sy = std::sin(yaw_deg * k);
  const double cr = std::cos(roll_deg * k), sr = std::sin(roll_deg * k);
  const double cp = std::cos(pitch_deg * k), sp = std::sin(pitch_deg * k);
  fwd[0] = cp * cy;
  fwd[1] = cp * sy;
  fwd[2] = sp;
  right[0] = cy * sp * sr - sy * cr;
  right[1] = sy * sp * sr + cy * cr;
  right[2] = -cp * sr;
  up[0] = -cy * sp * cr - sy * sr;
  up[1] = -sy * sp * cr + cy * sr;
  up[2] = cp * cr;
}

inline HeroSnapshot SnapshotFromCarla(const CarlaKinematics& k) {
  double f[3], r[3], u[3];
  CarlaAxes(k.pitch, k.yaw, k.roll, f, r, u);
  auto dot = [](const double a[3], double x, double y, double z) { return a[0] * x + a[1] * y + a[2] * z; };
  HeroSnapshot s{};
  s.pose = Pose{k.x, k.y, k.z, k.roll, k.pitch, k.yaw};
  s.velocity = Vector3{dot(f, k.vx, k.vy, k.vz), dot(r, k.vx, k.vy, k.vz), dot(u, k.vx, k.vy, k.vz)};
  s.acceleration = Vector3{dot(f, k.ax, k.ay, k.az), dot(r, k.ax, k.ay, k.az), dot(u, k.ax, k.ay, k.az)};
  const double rad = M_PI / 180.0;
  s.angularVelocity = Vector3{k.wx * rad, k.wy * rad, k.wz * rad};
  return s;
}

// The published sample of a frame (VSS units and signs).
inline EgoMotionSamplePayload EgoSampleFromSnapshot(const HeroSnapshot& s, std::uint64_t frame) {
  EgoMotionSamplePayload e{};
  const double v = std::sqrt(s.velocity.x * s.velocity.x + s.velocity.y * s.velocity.y + s.velocity.z * s.velocity.z);
  e.speed = static_cast<float>(v * 3.6);
  e.longitudinalAcceleration = static_cast<float>(s.acceleration.x);
  e.lateralAcceleration = static_cast<float>(-s.acceleration.y);           // ISO 8855: left positive
  e.yawRate = static_cast<float>(-s.angularVelocity.z * 180.0 / M_PI);     // left (counter-clockwise) positive
  e.captureTime = static_cast<double>(CaptureTimeMicros(frame)) / 1e6;
  return e;
}

}  // namespace de4sdv::driving::agent
