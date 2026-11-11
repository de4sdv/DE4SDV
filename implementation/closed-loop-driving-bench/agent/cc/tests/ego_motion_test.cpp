// ego_motion.h: the frames and signs of the hero's kinematics (CARLA world -> vehicle frame -> VSS).
#include <cmath>
#include <cstdio>

#include "ego_motion.h"

namespace da = de4sdv::driving::agent;

static int g_checks = 0, g_fail = 0;
#define CHECK_NEAR(a, b, tol)                                                                          \
  do {                                                                                                  \
    ++g_checks;                                                                                         \
    const double va = (a), vb = (b);                                                                    \
    if (!(std::fabs(va - vb) <= (tol))) {                                                               \
      ++g_fail;                                                                                         \
      std::printf("FAIL %s:%d: %s = %.9g, expected %.9g\n", __FILE__, __LINE__, #a, va, vb);            \
    }                                                                                                   \
  } while (0)

int main() {
  // The axes are CARLA's GetMatrix columns: yaw 90 deg looks along world +y; right is then world -x.
  double f[3], r[3], u[3];
  da::CarlaAxes(0.0, 90.0, 0.0, f, r, u);
  CHECK_NEAR(f[0], 0.0, 1e-12);
  CHECK_NEAR(f[1], 1.0, 1e-12);
  CHECK_NEAR(r[0], -1.0, 1e-12);
  CHECK_NEAR(r[1], 0.0, 1e-12);
  CHECK_NEAR(u[2], 1.0, 1e-12);

  // Straight on at 10 m/s with heading 30 deg: all of it is forward speed in the vehicle frame.
  da::CarlaKinematics k;
  k.yaw = 30.0;
  k.vx = 10.0 * std::cos(M_PI / 6.0);
  k.vy = 10.0 * std::sin(M_PI / 6.0);
  da::HeroSnapshot s = da::SnapshotFromCarla(k);
  CHECK_NEAR(s.velocity.x, 10.0, 1e-9);
  CHECK_NEAR(s.velocity.y, 0.0, 1e-9);
  de4sdv::driving::EgoMotionSamplePayload e = da::EgoSampleFromSnapshot(s, 1234);
  CHECK_NEAR(e.speed, 36.0, 1e-4);
  CHECK_NEAR(e.captureTime, 123.4, 1e-9);

  // Braking along the heading: negative longitudinal acceleration.
  k.ax = -4.0 * std::cos(M_PI / 6.0);
  k.ay = -4.0 * std::sin(M_PI / 6.0);
  e = da::EgoSampleFromSnapshot(da::SnapshotFromCarla(k), 1);
  CHECK_NEAR(e.longitudinalAcceleration, -4.0, 1e-6);
  CHECK_NEAR(e.lateralAcceleration, 0.0, 1e-6);

  // A left turn, heading 0: CARLA's yaw decreases (left-handed, z up), so its z rate is negative,
  // and the centripetal acceleration points to the vehicle's left, world -y. VSS: both positive.
  da::CarlaKinematics left;
  left.vx = 10.0;
  left.ay = -2.0;   // towards the left of a vehicle heading along world +x
  left.wz = -11.459155902616464;  // -0.2 rad/s in deg/s
  s = da::SnapshotFromCarla(left);
  CHECK_NEAR(s.acceleration.y, -2.0, 1e-9);  // vehicle frame: y right, so left is negative
  CHECK_NEAR(s.angularVelocity.z, -0.2, 1e-12);
  e = da::EgoSampleFromSnapshot(s, 1);
  CHECK_NEAR(e.yawRate, 11.459155902616464, 1e-4);   // deg/s, left positive
  CHECK_NEAR(e.lateralAcceleration, 2.0, 1e-6);      // m/s^2, left positive

  // The same left turn while heading 90 deg (world +y): right is world -x (the axes above), so
  // left is world +x.
  da::CarlaKinematics left90;
  left90.yaw = 90.0;
  left90.vy = 10.0;
  left90.ax = 2.0;
  left90.wz = -11.459155902616464;
  e = da::EgoSampleFromSnapshot(da::SnapshotFromCarla(left90), 1);
  CHECK_NEAR(e.speed, 36.0, 1e-4);
  CHECK_NEAR(e.lateralAcceleration, 2.0, 1e-6);
  CHECK_NEAR(e.yawRate, 11.459155902616464, 1e-4);

  // Pitch: driving up a 10-degree slope at 10 m/s along the slope is still 10 m/s forward.
  da::CarlaKinematics up;
  up.pitch = 10.0;
  up.vx = 10.0 * std::cos(10.0 * M_PI / 180.0);
  up.vz = 10.0 * std::sin(10.0 * M_PI / 180.0);
  s = da::SnapshotFromCarla(up);
  CHECK_NEAR(s.velocity.x, 10.0, 1e-9);
  CHECK_NEAR(s.velocity.z, 0.0, 1e-9);

  std::printf("%d checks, %d failures\n", g_checks, g_fail);
  return g_fail == 0 ? 0 : 1;
}
