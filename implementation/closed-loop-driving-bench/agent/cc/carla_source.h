// DE4SDV closed-loop driving bench (INC-DRIVING-001, slice 10b): drivingAgent's CARLA source. The
// world side (world-side/world_side.py) spawns the hero (role_name "hero") with its six cameras
// (cam_front, cam_front_left, cam_front_right, cam_rear_left, cam_rear, cam_rear_right) and ticks the
// synchronous world. This client only reads: it never spawns, ticks or controls anything.
//
//   Attach (de4sdv_agent_init, before FEO starts; may block up to attach_timeout_s):
//     connect; wait for the hero and the six cameras; read the camera sizes and fov; read the rig
//     (vehicle matrix, location, wheels; camera matrices) from ONE world frame: the wheel positions
//     come from an RPC, so the read is accepted only when no tick arrived while it ran.
//   Start (conditionInputs' startup, fast):
//     Listen on the six cameras and OnTick for the hero's snapshot; both feed the frame store; a
//     thread sweeps the store's deadlines every 5 ms.
#pragma once

#include <array>
#include <cstdint>
#include <memory>
#include <string>

#include "frame_store.h"
#include "rig.h"

namespace de4sdv::driving::agent {

struct CarlaSourceConfig {
  std::string host = "127.0.0.1";
  int port = 2000;
  double rpc_timeout_s = 10.0;
  double attach_timeout_s = 300.0;
  std::string hero_role = "hero";
  std::array<std::string, kCameraCount> camera_roles = {"cam_front",     "cam_front_left", "cam_front_right",
                                                        "cam_rear_left", "cam_rear",       "cam_rear_right"};
};

struct CarlaCameraInfo {
  std::uint32_t actor_id = 0;
  int width = 0;
  int height = 0;
  double fov = 0.0;
};

class CarlaSource {
 public:
  CarlaSource();
  ~CarlaSource();
  CarlaSource(const CarlaSource&) = delete;
  CarlaSource& operator=(const CarlaSource&) = delete;

  // rig_json: the set_rig document ({"vehicle": {...}, "cameras": [...]}); info_json: the attach
  // record (actor ids, frame of the rig read, attempts, timings).
  bool Attach(const CarlaSourceConfig& config, std::string* rig_json, std::string* info_json, std::string* error);
  const CarlaCameraInfo& camera(std::size_t index) const;
  const std::string& server_version() const;  // the CARLA server's, read at Attach

  bool Start(FrameStore* store, std::string* error);
  void Stop();  // idempotent

  std::uint64_t ticks() const;                    // hero snapshots fed to the store
  std::uint64_t images(std::size_t index) const;  // images fed per camera
  std::uint64_t ticks_without_hero() const;       // world ticks whose snapshot lacked the hero

 private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};

}  // namespace de4sdv::driving::agent
