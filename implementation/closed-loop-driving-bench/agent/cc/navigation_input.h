// DE4SDV closed-loop driving bench (INC-DRIVING-001, slice 10b): conditionInputs' navigation input.
// The route provider's newest announcement (ICD section 9, RouteListener) names the route file and
// its SHA-256; the rasterizer (navigation_raster, upstream's renderer) draws map_context and
// route_mask at the step's REF pose; the route observation goes to the input judgement
// (REQ-DRIVING-025) and both rasters to the checkpoint. The step's take of the nav prefetch's
// render (TakeNavPrefetch, ICD A31) is here as well, so that its test runs the real renderer.
#pragma once

#include <cstdint>
#include <mutex>
#include <string>
#include <vector>

#include "agent_logic.h"
#include "frame_store.h"
#include "nav_prefetch.h"
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
    // What decides the route part of the raster: RouteIdentity() of the announcement it was drawn
    // with. Equal identities at the same pose give byte-identical rasters (the nav prefetch's check).
    std::string route_identity;
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

  // Renders into map_context() and route_mask(). Thread-safe against RenderInto: one render at a time.
  bool Render(const Pose& vehicle_pose_ue, const double origin_ue[3], Step* step, std::string* error);
  // The same render into the caller's buffers (the nav prefetch's thread; DESIGN.md).
  bool RenderInto(const Pose& vehicle_pose_ue, const double origin_ue[3], Step* step, std::vector<float>* map_context,
                  std::vector<float>* route_mask, std::string* error);
  const std::vector<float>& map_context() const { return map_context_; }
  const std::vector<float>& route_mask() const { return route_mask_f32_; }

  // The listener's newest announcement, and the part of it that decides the raster: none, a
  // withdrawal, or the announced file and SHA-256 (not the issue time or the corridor count).
  RouteState NewestRoute() const { return listener_.Newest(); }
  static std::string RouteIdentity(const RouteState& rs);
  // The announcement's part of the route observation (announced, corridor count, issue time), as
  // Render sets it: the take of a prefetched render reads it from the announcement at the step.
  static void ObserveAnnouncement(const RouteState& rs, RouteObservation* route);

 private:
  bool RenderLocked(const Pose& vehicle_pose_ue, const double origin_ue[3], Step* step, std::vector<float>* map_context,
                    std::vector<float>* route_mask, std::string* error);

  std::mutex render_mu_;     // the route state, the rasterizer and route_u8_ below
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

// What the nav prefetch's thread hands the step: the step's rasters in buffers of their own, the
// pose they were drawn at, and the "route" record's data when that render changed the route.
struct NavPrefetchResult {
  NavigationInput::Step step;
  std::vector<float> map_context, route_mask;
  Pose pose{};
  bool ok = false;
  std::string error;
  std::string route_event;   // nav_prefetch.h carries it to the next take when the result is never used
};

// The prefetch thread's render of one request (the agent's NavPrefetch render function): `frame`'s
// rasters at `pose` into r's own buffers, and the "route" record's data, with that frame, when the
// render changed the route.
void RenderNavPrefetch(NavigationInput* nav, const double origin_ue[3], std::uint64_t frame, const Pose& pose,
                       NavPrefetchResult* r);

// The step's take of its frame's prefetched render (ICD A31), C2's navPrefetch.outcome.
enum class NavPrefetchOutcome { kHit, kNotSubmitted, kTimedOut, kRouteChanged, kPoseChanged, kRenderFailed };
const char* NavPrefetchOutcomeName(NavPrefetchOutcome outcome);   // "hit", "not_submitted", ...

struct NavPrefetchTake {
  NavPrefetchOutcome outcome = NavPrefetchOutcome::kNotSubmitted;
  double take_ms = 0.0;   // C2 navPrefetch.take_ms
  // The "route" records' data the step logs now, in this order: the route changes of renders never
  // used (oldest first), then this frame's render's own change when the step does not use it.
  std::vector<std::string> route_events;
  // A use (kHit) only: the step's navigation fields (the route observation read at the take; its
  // route_event the step logs once, with its frame) and the rasters the checkpoint gets. Null
  // otherwise: the step renders on the chain.
  NavigationInput::Step step;
  const std::vector<float>* map_context = nullptr;
  const std::vector<float>* route_mask = nullptr;
};

// Takes `frame`'s prefetched render, waiting at most max_wait_ns for one in flight, and decides
// whether the step at `step_pose` uses it: only if a render on the chain would draw the same
// (DecideUse, against the newest announcement read now). On a use the rasters are swapped into
// *hit_map and *hit_route, which the caller keeps until its next use, and the take points at them.
NavPrefetchTake TakeNavPrefetch(NavPrefetch<NavPrefetchResult>* prefetch, const NavigationInput& nav,
                                std::uint64_t frame, const Pose& step_pose, std::int64_t max_wait_ns,
                                std::vector<float>* hit_map, std::vector<float>* hit_route);

}  // namespace de4sdv::driving::agent
