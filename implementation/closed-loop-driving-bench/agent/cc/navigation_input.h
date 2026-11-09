// DE4SDV closed-loop driving bench (INC-DRIVING-001, slice 10b): conditionInputs' navigation input.
// The route provider's newest announcement (ICD section 9, RouteListener) names the route file and
// its SHA-256; the rasterizer (navigation_raster, upstream's renderer) draws map_context and
// route_mask at the step's REF pose; the route observation goes to the input judgement
// (REQ-DRIVING-025) and both rasters to the checkpoint.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "agent_logic.h"
#include "frame_store.h"
#include "navigation_raster.h"
#include "route_listener.h"

namespace de4sdv::driving::agent {

// The REF pose in the map frame (ICD section 9: x_map = x_carla, y_map = -y_carla, yaw_map = -yaw),
// as the closed-loop harness posed the raster: T = S4 * M_world_vehicle * T(origin) * S4, with
// x = T[0][3], y = T[1][3], yaw = atan2(T[1][0], T[0][0]). origin_ue: REF in the vehicle's UE frame
// (set_rig's "origin").
struct MapPose {
  double x = 0.0;
  double y = 0.0;
  double yaw = 0.0;
};
MapPose RefPoseInMap(const Pose& vehicle_pose_ue, const double origin_ue[3]);

class NavigationInput {
 public:
  struct Step {
    RouteObservation route;
    MapPose pose;
    double render_ms = 0.0;
    bool route_in_raster = false;  // a route file with the announced SHA-256 is loaded
    std::string route_sha256;      // that file's SHA-256, else empty
    std::string route_event;       // JSON when the route changed or failed at this step, else empty
    std::uint32_t destination_cells = 0;
    // Coverage (VC-DRIVING-007): route waypoints inside the raster window, 2 px clear of its edges
    // and of the 10 m rear clip, and how many of them fall on a corridor cell. Upstream's own
    // geometry: map_to_ego, then row = (x_max - x) / 0.4, column = (y_max - y) / 0.4.
    std::uint32_t waypoints_in_window = 0;
    std::uint32_t waypoints_on_corridor = 0;
  };

  // Loads the map (carla_map_export.py JSON) and binds the route listener (port 0: ephemeral).
  bool Start(const std::string& map_path, const std::string& host, int port, std::string* error);
  void Stop();
  int listener_port() const { return listener_.port(); }
  const std::string& map_version() const { return raster_.map().map_version; }

  bool Render(const Pose& vehicle_pose_ue, const double origin_ue[3], Step* step, std::string* error);
  const std::vector<float>& map_context() const { return map_context_; }
  const std::vector<float>& route_mask() const { return route_mask_f32_; }

 private:
  RouteListener listener_;
  navigation::NavigationRasterizer raster_;
  bool started_ = false;
  std::string loaded_file_;  // the route the rasterizer holds ("" = none)
  std::string loaded_sha_;
  bool route_ok_ = false;
  std::vector<float> map_context_;
  std::vector<std::uint8_t> route_u8_;
  std::vector<float> route_mask_f32_;
};

}  // namespace de4sdv::driving::agent
