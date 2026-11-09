#include "navigation_input.h"

#include <chrono>
#include <cmath>
#include <cstring>
#include <sstream>

#include "de4sdv/driving/run_log.h"
#include "ego_motion.h"

namespace de4sdv::driving::agent {

namespace nav = de4sdv::driving::navigation;

MapPose RefPoseInMap(const Pose& p, const double o[3]) {
  double f[3], r[3], u[3];
  CarlaAxes(p.pitch, p.yaw, p.roll, f, r, u);
  MapPose m;
  m.x = p.x + o[0] * f[0] + o[1] * r[0] + o[2] * u[0];
  m.y = -(p.y + o[0] * f[1] + o[1] * r[1] + o[2] * u[1]);
  m.yaw = std::atan2(-f[1], f[0]);
  return m;
}

bool NavigationInput::Start(const std::string& map_path, const std::string& host, int port, std::string* error) {
  std::string e;
  if (!raster_.LoadMap(map_path, &e)) {
    *error = "map " + map_path + ": " + e;
    return false;
  }
  if (!listener_.Start(host, port, error)) return false;
  started_ = true;
  return true;
}

void NavigationInput::Stop() {
  listener_.Stop();
  started_ = false;
}

bool NavigationInput::Render(const Pose& vehicle_pose_ue, const double origin_ue[3], Step* st, std::string* error) {
  *st = Step{};
  const RouteState rs = listener_.Newest();
  st->route.has_announcement = rs.has_announcement;
  if (rs.has_announcement) {
    st->route.corridor_points = rs.newest.corridorPoints;
    st->route.issue_time = rs.newest.issueTime;
    const std::string file(rs.newest.routeFile, ::strnlen(rs.newest.routeFile, sizeof(rs.newest.routeFile)));
    const std::string sha(rs.newest.routeSha256, sizeof(rs.newest.routeSha256));
    // An announcement without a corridor withdraws the route (the route_empty fault).
    const std::string want = rs.newest.corridorPoints > 0 ? file : std::string{};
    if (want != loaded_file_ || (!want.empty() && sha != loaded_sha_)) {
      std::ostringstream ev;
      if (want.empty()) {
        raster_.SetRoute(nav::RouteData{});
        route_ok_ = false;
        ev << "{\"route\":\"withdrawn\",\"reason\":\"announcement without corridor\"}";
      } else {
        std::string e;
        if (!raster_.LoadRoute(want, &e)) {
          raster_.SetRoute(nav::RouteData{});
          route_ok_ = false;
          ev << "{\"route\":\"load_failed\",\"file\":" << JsonString(want) << ",\"message\":" << JsonString(e) << "}";
        } else if (raster_.route().sha256 != sha) {
          const std::string file_sha = raster_.route().sha256;
          raster_.SetRoute(nav::RouteData{});
          route_ok_ = false;
          ev << "{\"route\":\"sha256_mismatch\",\"file\":" << JsonString(want) << ",\"announced\":" << JsonString(sha)
             << ",\"file_sha256\":" << JsonString(file_sha) << "}";
        } else {
          route_ok_ = true;
          ev << "{\"route\":\"loaded\",\"file\":" << JsonString(want) << ",\"sha256\":" << JsonString(sha)
             << ",\"corridorPoints\":" << raster_.route().corridor_points
             << ",\"routeMap\":" << JsonString(raster_.route().map_name)
             << ",\"mapVersion\":" << JsonString(raster_.map().map_version)
             << ",\"effectiveRouteValid\":" << (raster_.EffectiveRouteValid() ? "true" : "false") << "}";
        }
      }
      loaded_file_ = want;
      loaded_sha_ = sha;
      st->route_event = ev.str();
    }
  }
  st->route_in_raster = route_ok_;
  st->pose = RefPoseInMap(vehicle_pose_ue, origin_ue);
  const auto t0 = std::chrono::steady_clock::now();
  if (!raster_.Render(st->pose.x, st->pose.y, st->pose.yaw, &map_context_, &route_u8_, error)) return false;
  st->render_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
  route_mask_f32_.resize(route_u8_.size());
  for (std::size_t i = 0; i < route_u8_.size(); ++i) route_mask_f32_[i] = static_cast<float>(route_u8_[i]);
  const std::size_t plane = static_cast<std::size_t>(nav::kHeightPx) * static_cast<std::size_t>(nav::kWidthPx);
  const std::size_t corridor = static_cast<std::size_t>(nav::RouteChannel::kSelectedCorridor) * plane;
  std::uint32_t cells = 0;
  if (route_u8_.size() >= corridor + plane) {
    for (std::size_t i = 0; i < plane; ++i) cells += route_u8_[corridor + i] != 0 ? 1u : 0u;
  }
  st->route.raster_corridor_cells = cells;
  const std::size_t destination = static_cast<std::size_t>(nav::RouteChannel::kSelectedCorridor) == 0 ? plane : 0;
  std::uint32_t dest_cells = 0;
  if (route_u8_.size() >= destination + plane) {
    for (std::size_t i = 0; i < plane; ++i) dest_cells += route_u8_[destination + i] != 0 ? 1u : 0u;
  }
  st->destination_cells = dest_cells;
  st->route_sha256 = route_ok_ ? loaded_sha_ : std::string{};
  if (route_ok_ && raster_.EffectiveRouteValid()) {
    const double c = std::cos(st->pose.yaw), s = std::sin(st->pose.yaw);
    const double margin = 2.0 * nav::kMetersPerPixel;
    for (const auto& line : raster_.route().centerlines) {
      for (const auto& p : line) {
        const double dx = p.x - st->pose.x, dy = p.y - st->pose.y;
        const double ex = c * dx + s * dy, ey = -s * dx + c * dy;  // upstream map_to_ego
        if (ex <= -static_cast<double>(nav::kRouteRearClipM) + margin || ex >= nav::kXMaxM - margin ||
            ey <= nav::kYMinM + margin || ey >= nav::kYMaxM - margin) {
          continue;
        }
        const auto row = static_cast<std::size_t>(std::floor((nav::kXMaxM - ex) / nav::kMetersPerPixel));
        const auto col = static_cast<std::size_t>(std::floor((nav::kYMaxM - ey) / nav::kMetersPerPixel));
        ++st->waypoints_in_window;
        if (route_u8_[corridor + row * static_cast<std::size_t>(nav::kWidthPx) + col] != 0) ++st->waypoints_on_corridor;
      }
    }
  }
  return true;
}

}  // namespace de4sdv::driving::agent
