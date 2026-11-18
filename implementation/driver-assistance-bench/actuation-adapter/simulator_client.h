// The actuation adapter's simulator client, behind a plain function interface.
//
// Two translation units implement it:
//   simulator_client_carla.cpp       the CARLA 1.0 C++ client (LibCarla at
//                                    14ac3b1a50), compiled as C++20, the
//                                    client's own standard (DA-P8 h, owner
//                                    decision h-a, option a); it needs LibCarla
//                                    and is built only in the S-CORE workspace;
//   tests/fake_simulator_client.cpp  the fake the host's tests link instead.
// This header is C++17, so the rest of the adapter stays at the S-CORE
// toolchain's default.
//
// What crosses (PSR): the client takes the simulation time and the ego
// vehicle's speed from each world snapshot (simulationClockIn,
// vehicleSpeedIn) and applies the Ackermann control (ackermannControlOut,
// SimulatorAckermannControl). It never sets the autopilot and applies no other
// control (PSR DrivingCommandActuationAdapter: "The autopilot of the ego
// vehicle stays off").
#pragma once

#include <cstdint>
#include <functional>
#include <string>

namespace de4sdv::driver_assistance::actuation::simulator {

struct ClientOptions {
  std::string host = "127.0.0.1";
  int port = 2000;
  double timeoutS = 30.0;
  std::string heroRoleName = "hero";
  double heroWaitS = 20.0;
};

// What Connect found.
struct ClientInfo {
  std::string clientVersion;
  std::string serverVersion;
  std::uint32_t heroActorId = 0;
  std::string heroTypeId;
};

// One world snapshot, as the client reads it.
struct SnapshotSample {
  std::uint64_t frame = 0;
  double simTimeS = 0.0;    // the snapshot's simulation time (Timestamp::elapsed_seconds)
  bool egoPresent = false;  // the ego vehicle is in the snapshot
  double speedMps = 0.0;    // its speed, the length of its velocity; 0 when absent
};

// The Ackermann control as the simulator receives it: CARLA's
// VehicleAckermannControl holds five floats.
struct AppliedAckermannControl {
  float steer = 0.0F;
  float steerSpeed = 0.0F;
  float speed = 0.0F;
  float acceleration = 0.0F;
  float jerk = 0.0F;
};

using SnapshotHandler = std::function<void(const SnapshotSample&)>;

// Connects to the simulator server and waits up to heroWaitS for the vehicle
// whose role_name is heroRoleName. Returns false and sets *error otherwise.
bool Connect(const ClientOptions& options, ClientInfo* info, std::string* error);

// Calls handler once per world snapshot, on the client's thread, until
// StopSnapshots. Returns false and sets *error when it cannot subscribe.
bool StartSnapshots(SnapshotHandler handler, std::string* error);
void StopSnapshots();

// Applies the control to the ego vehicle, and nothing else. Returns false and
// sets *error when the simulator refuses it.
bool ApplyAckermannControl(const AppliedAckermannControl& control, std::string* error);

void Disconnect();

}  // namespace de4sdv::driver_assistance::actuation::simulator
