// DE4SDV INC-DRIVING-001 slice 10b: navigation inputs of the closed-loop
// driving bench (S3). Interface Control Document: ../interfaces/ICD.md.
//
// This library turns the exported CARLA map and the route file into the two
// rasters the pinned AutoE2E checkpoint takes (REQ-DRIVING-006, -007):
//
//   map_context  float32 [14, 450, 300]  semantic map, channel-major (CHW)
//   route_mask   uint8   [ 2, 450, 300]  selected corridor, destination
//
// in the geometry `autoe2e-bev-450x300-0p4m-v1`: 450 rows (longitudinal) by
// 300 columns (lateral), 0.4 m per pixel, x from -60 m (rear) to +120 m
// (front), y from -60 m (right) to +60 m (left), heading counter-clockwise
// from +x, all in the map frame (CARLA's y negated; see carla_frame.py).
//
// The rasters are drawn from primitives packed exactly as upstream
// `Model/navigation/rasterizer.py` does (_map_primitive_specs,
// _pack_primitives, _pack_route): same order, same channel, same width, same
// level handling.  Two paths exist and must stay bit-identical:
//
//   Render           packs once at SetMap/SetRoute, culls the primitives to the
//                    raster window of the pose, zeroes the outputs and
//                    rasterizes the route with upstream's own native renderer
//                    (`navigation_rasterizer.cpp`, built unmodified), then
//                    fills the map channels with a span rasterizer that
//                    reproduces upstream's per-pixel decisions exactly
//                    (same crossing test, same arithmetic, same draw order).
//   RenderReference  the original path: re-packs every call and hands every
//                    primitive to the native renderer.  Kept for the parity
//                    tests (tests/test_navigation_raster_real_parity.py).
//
// Render is const but uses internal scratch buffers: one rasterizer instance
// must not be used from two threads at once.
//
// Validity for REQ-DRIVING-025 comes on top: whether the route corridor is
// present in the rendered raster, and how old the route is relative to the
// newest RouteAnnouncement (ICD section 9, payloads.h).
#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace de4sdv::driving::navigation {

// ------------------------------------------------------------------ geometry
// Mirrors AUTOE2E_NAVIGATION_GEOMETRY in upstream navigation/geometry.py.
inline constexpr std::int32_t kMapChannels = 14;
inline constexpr std::int32_t kRouteChannels = 2;
inline constexpr std::int32_t kHeightPx = 450;
inline constexpr std::int32_t kWidthPx = 300;
inline constexpr double kMetersPerPixel = 0.4;
inline constexpr double kXMinM = -60.0;
inline constexpr double kXMaxM = 120.0;
inline constexpr double kYMinM = -60.0;
inline constexpr double kYMaxM = 60.0;
inline constexpr float kRouteCorridorWidthM = 3.5F;
inline constexpr float kDestinationMarkerRadiusM = 2.0F;
inline constexpr float kRouteRearClipM = 10.0F;
inline constexpr const char* kGeometryId = "autoe2e-bev-450x300-0p4m-v1";

// REQ-DRIVING-025: a route older than one second of simulation time is stale.
inline constexpr double kRouteStaleSeconds = 1.0;

// MapChannel in upstream navigation/geometry.py, same order and numbers.
enum class MapChannel : std::int32_t {
  kDrivableArea = 0,
  kLaneBoundary = 1,
  kLaneCenterline = 2,
  kIntersection = 3,
  kCrosswalk = 4,
  kStopLine = 5,
  kStaticTrafficSignal = 6,
  kTrafficDirectionSin = 7,
  kTrafficDirectionCos = 8,
  kTrafficDirectionValid = 9,
  kKnownMapArea = 10,
  kRoadLevel = 11,
  kRoadLevelValid = 12,
  kOverlappingLevelAmbiguity = 13,
};

enum class RouteChannel : std::int32_t {
  kSelectedCorridor = 0,
  kDestination = 1,
};

// Cause values of payloads.h used by the route check.
inline constexpr std::int32_t kCauseNone = 0;
inline constexpr std::int32_t kCauseRouteStale = 6;
inline constexpr std::int32_t kCauseRouteEmpty = 7;

// ---------------------------------------------------------------- primitives

struct Point {
  double x;
  double y;
};

// NavPrimitiveKind of the native rasterizer.
enum class PrimitiveKind : std::int32_t {
  kLine = 0,
  kPolygon = 1,
  kPoint = 2,
  kDirectionLine = 3,
};

// One map primitive in the map frame, already at the channel and width
// upstream assigns to its group.  `level` is only meaningful when
// `level_valid`, as in the C contract.
struct Primitive {
  PrimitiveKind kind = PrimitiveKind::kLine;
  std::int32_t channel = 0;
  std::int32_t level = 0;
  bool level_valid = false;
  float width_m = 0.0F;
  float value = 1.0F;
  std::vector<Point> points;
};

// The exported map (map JSON, schema v1) in upstream rasterizer order:
// the known-map-area rectangle first, then drivable polygons, lane
// boundaries, lane centre lines, intersections, crosswalks, stop lines,
// traffic signals, directed lane fields -- the order of _map_primitive_specs.
struct MapData {
  std::string map_version;
  std::string provider;
  std::string frame_id;
  std::array<double, 4> bounds_enu_m{{0.0, 0.0, 0.0, 0.0}};  // xmin,ymin,xmax,ymax
  std::vector<Primitive> primitives;
};

// The ICD section 9 route file, split into the lane segments upstream packs
// with _pack_route.
struct RouteData {
  std::string map_name;
  // The waypoints of each run of constant road id with two or more waypoints,
  // as the file gives them.  These are the points ICD A16's waypointsInWindow
  // counts (agent/cc/navigation_input.cpp; VC-DRIVING-007 recounts them from
  // the route file with the same rule).
  std::vector<std::vector<Point>> centerlines;
  // The lines the corridor is drawn from, one per road run: each run after the
  // first starts at the previous run's last waypoint, so the corridor stays
  // continuous where the road changes, as upstream's lane sequence does (its
  // lanelet centre lines share their end points).  A run of one waypoint is
  // the line from the previous waypoint to it.  A first run of one waypoint
  // has no line of its own: its waypoint starts the second run's line.
  std::vector<std::vector<Point>> corridor_lines;
  Point destination{0.0, 0.0};
  bool destination_valid = false;
  std::int64_t corridor_points = 0;
  std::string sha256;
  // The file parses and carries at least two waypoints; whether it belongs to
  // the loaded map is decided by EffectiveRouteValid / Render.
  bool valid = false;
};

// Byte-identical mirror of de4sdv::driving::RouteAnnouncement (payloads.h):
// version, corridorPoints, issueTime, routeFile[192], routeSha256[64].
// tests/raster_cli.cpp static_asserts the layout against payloads.h.
struct RouteAnnouncement {
  std::uint32_t version = 0;
  std::uint32_t corridorPoints = 0;
  double issueTime = 0.0;
  char routeFile[192] = {};
  char routeSha256[64] = {};
};

// Result of the REQ-DRIVING-025 check for one step.
struct RouteValidity {
  bool has_announcement = false;
  bool corridor_declared = false;  // announcement.corridorPoints > 0
  bool corridor_present = false;   // route corridor channel has a pixel
  double route_age_seconds = 0.0;  // now - announcement.issueTime
  bool stale = true;               // age > 1 s, or never announced
  bool empty = true;               // no corridor pixel
  std::int32_t cause = kCauseRouteEmpty;  // kCauseNone when nothing is wrong
};

// ------------------------------------------------------------------ parsing

// Parse the map JSON written by carla_map_export.py.
bool ParseMapJson(const std::string& text, MapData* map, std::string* error);
bool LoadMapJsonFile(const std::string& path, MapData* map, std::string* error);

// Parse the ICD section 9 route file.
bool ParseRouteJson(const std::string& text, RouteData* route, std::string* error);
bool LoadRouteJsonFile(const std::string& path, RouteData* route, std::string* error);

// --------------------------------------------------------------- rasterizer

class NavigationRasterizer {
 public:
  NavigationRasterizer() = default;

  // Load once per run; Render may then be called per step.
  bool LoadMap(const std::string& path, std::string* error);
  bool LoadRoute(const std::string& path, std::string* error);
  void SetMap(MapData map);
  void SetRoute(RouteData route);

  bool has_map() const { return has_map_; }
  bool map_valid() const { return has_map_; }
  // The route file parses and carries a corridor.
  bool route_valid() const { return has_route_ && route_.valid; }
  // The route is also usable for this map: upstream's route_valid rule
  // (route.map_version == map.map_version) on top of the file check.
  bool EffectiveRouteValid() const {
    return route_valid() && has_map_ && route_.map_name == map_.map_version;
  }
  const MapData& map() const { return map_; }
  const RouteData& route() const { return route_; }

  // Render both rasters for one ego pose in the map frame (x, y, yaw).
  // `map_context` receives 14*450*300 floats, `route_mask` 2*450*300 bytes,
  // channel-major, row-major inside a channel (the checkpoint's layout).
  // Returns false with `error` set only for a programming or I/O fault; a
  // missing map or an invalid route renders zeros, as upstream does.
  //
  // Fast path: packed primitives are reused, only those whose inflated map-frame
  // bounding box meets the raster window of the pose are drawn, and the map
  // channels are filled by the span rasterizer.  Bit-identical to
  // RenderReference, which is the unoptimised path kept for parity tests.
  bool Render(double x_map_m, double y_map_m, double yaw_map_rad,
              std::vector<float>* map_context,
              std::vector<std::uint8_t>* route_mask,
              std::string* error) const;

  // The unoptimised reference path: re-pack every call, hand every primitive to
  // upstream's native renderer.  Same signature and contract as Render.
  bool RenderReference(double x_map_m, double y_map_m, double yaw_map_rad,
                       std::vector<float>* map_context,
                       std::vector<std::uint8_t>* route_mask,
                       std::string* error) const;

  // REQ-DRIVING-025: corridor presence in `route_mask` plus the age of the
  // route from the newest announcement.  `announcement` may be null.
  RouteValidity EvaluateRoute(const RouteAnnouncement* announcement,
                              double now_simulation_s,
                              const std::vector<std::uint8_t>& route_mask) const;

  static std::size_t MapContextSize() {
    return static_cast<std::size_t>(kMapChannels) * kHeightPx * kWidthPx;
  }
  static std::size_t RouteMaskSize() {
    return static_cast<std::size_t>(kRouteChannels) * kHeightPx * kWidthPx;
  }

  // The upstream native library's own version string.
  static const char* RendererVersion();

 private:
  // One map primitive in the form the renderer consumes: the native primitive
  // fields plus the map-frame bounding box inflated by the furthest pixel the
  // primitive can touch, for window culling.
  struct PackedMapPrimitive {
    std::int32_t point_offset = 0;  // into map_points_, in points
    std::int32_t point_count = 0;
    std::int32_t kind = 0;
    std::int32_t channel = 0;
    std::int32_t level = 0;
    std::int32_t level_valid = 0;
    float width_m = 0.0F;
    float value = 1.0F;
    std::array<double, 4> bounds{{0.0, 0.0, 0.0, 0.0}};  // xmin,ymin,xmax,ymax
  };

  // One route corridor line: a contiguous run of route_points_ plus its inflated
  // map-frame bounding box (for culling the corridor to the window).
  struct PackedRouteLine {
    std::int32_t point_offset = 0;
    std::int32_t point_count = 0;
    std::array<double, 4> bounds{{0.0, 0.0, 0.0, 0.0}};
  };

  void RepackMap();
  void PackRoute();
  void RefreshEffectiveRoute();

  MapData map_;
  RouteData route_;
  bool has_map_ = false;
  bool has_route_ = false;

  // Packed once per SetMap/SetRoute: the exact doubles and primitive structs
  // upstream's _pack_primitives/_pack_route produce, in the same order.
  std::vector<double> map_points_;
  std::vector<PackedMapPrimitive> packed_map_;
  std::vector<double> route_points_;
  std::vector<std::int32_t> route_offsets_;
  std::vector<PackedRouteLine> packed_route_lines_;
  std::array<double, 2> route_destination_{{0.0, 0.0}};
  bool packed_route_usable_ = false;

  // Per-render scratch, reused so a steady-state Render does not allocate.
  mutable std::vector<std::int32_t> render_selection_;
  mutable std::vector<std::int32_t> render_crossings_;
  mutable std::vector<double> render_route_points_;
  mutable std::vector<std::int32_t> render_route_offsets_;
  mutable std::vector<Point> render_ego_points_;
};

}  // namespace de4sdv::driving::navigation
