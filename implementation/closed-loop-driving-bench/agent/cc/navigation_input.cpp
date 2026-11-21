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

std::string NavigationInput::RouteIdentity(const RouteState& rs) {
  if (!rs.has_announcement) return "none";
  if (rs.newest.corridorPoints == 0) return "withdrawn";
  const std::string file(rs.newest.routeFile, ::strnlen(rs.newest.routeFile, sizeof(rs.newest.routeFile)));
  const std::string sha(rs.newest.routeSha256, sizeof(rs.newest.routeSha256));
  return "route " + file + " sha256 " + sha;
}

void NavigationInput::ObserveAnnouncement(const RouteState& rs, RouteObservation* route) {
  route->has_announcement = rs.has_announcement;
  route->corridor_points = rs.has_announcement ? rs.newest.corridorPoints : 0;
  route->issue_time = rs.has_announcement ? rs.newest.issueTime : 0.0;
}

bool NavigationInput::Render(const Pose& vehicle_pose_ue, const double origin_ue[3], Step* st, std::string* error) {
  std::lock_guard<std::mutex> lock(render_mu_);
  return RenderLocked(vehicle_pose_ue, origin_ue, st, &map_context_, &route_mask_f32_, error);
}

bool NavigationInput::RenderInto(const Pose& vehicle_pose_ue, const double origin_ue[3], Step* st,
                                 std::vector<float>* map_context, std::vector<float>* route_mask, std::string* error) {
  std::lock_guard<std::mutex> lock(render_mu_);
  return RenderLocked(vehicle_pose_ue, origin_ue, st, map_context, route_mask, error);
}

bool NavigationInput::RenderLocked(const Pose& vehicle_pose_ue, const double origin_ue[3], Step* st,
                                   std::vector<float>* map_context, std::vector<float>* route_mask, std::string* error) {
  *st = Step{};
  const RouteState rs = listener_.Newest();
  st->route_identity = RouteIdentity(rs);
  ObserveAnnouncement(rs, &st->route);
  if (rs.has_announcement) {
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
  if (!raster_.Render(st->pose.x, st->pose.y, st->pose.yaw, map_context, &route_u8_, error)) return false;
  st->render_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
  route_mask->resize(route_u8_.size());
  for (std::size_t i = 0; i < route_u8_.size(); ++i) (*route_mask)[i] = static_cast<float>(route_u8_[i]);
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

void RenderNavPrefetch(NavigationInput* nav, const double origin_ue[3], std::uint64_t frame, const Pose& pose,
                       NavPrefetchResult* r) {
  r->pose = pose;
  r->ok = nav->RenderInto(pose, origin_ue, &r->step, &r->map_context, &r->route_mask, &r->error);
  if (r->ok && !r->step.route_event.empty()) {
    r->route_event = "{\"frame\":" + std::to_string(frame) + ",\"event\":" + r->step.route_event + "}";
  }
}

const char* NavPrefetchOutcomeName(NavPrefetchOutcome outcome) {
  switch (outcome) {
    case NavPrefetchOutcome::kHit: return "hit";
    case NavPrefetchOutcome::kNotSubmitted: return "not_submitted";
    case NavPrefetchOutcome::kTimedOut: return "timed_out";
    case NavPrefetchOutcome::kRouteChanged: return "route_changed";
    case NavPrefetchOutcome::kPoseChanged: return "pose_changed";
    case NavPrefetchOutcome::kRenderFailed: return "render_failed";
  }
  return "unknown";
}

NavPrefetchTake TakeNavPrefetch(NavPrefetch<NavPrefetchResult>* prefetch, const NavigationInput& nav,
                                std::uint64_t frame, const Pose& step_pose, std::int64_t max_wait_ns,
                                std::vector<float>* hit_map, std::vector<float>* hit_route) {
  NavPrefetchTake take;
  NavPrefetchResult pf;
  // The route changes of renders never used come first, oldest first (nav_prefetch.h carries them).
  const TakeOutcome o = prefetch->Take(frame, max_wait_ns, &pf, &take.route_events, &take.take_ms);
  if (o == TakeOutcome::kTimedOut) {
    take.outcome = NavPrefetchOutcome::kTimedOut;
    return take;
  }
  if (o == TakeOutcome::kNotSubmitted) {
    take.outcome = NavPrefetchOutcome::kNotSubmitted;
    return take;
  }
  // Used only if it is what a render here would draw: the same pose and the same route. The newest
  // announcement is read once, now, for the decision and for a use's route observation.
  const RouteState now = nav.NewestRoute();
  const UseDecision use =
      DecideUse(pf.ok, pf.pose, step_pose, pf.step.route_identity, NavigationInput::RouteIdentity(now));
  if (use != UseDecision::kUse) {
    if (use == UseDecision::kRenderFailed) take.outcome = NavPrefetchOutcome::kRenderFailed;
    if (use == UseDecision::kPoseChanged) take.outcome = NavPrefetchOutcome::kPoseChanged;
    if (use == UseDecision::kRouteChanged) take.outcome = NavPrefetchOutcome::kRouteChanged;
    // The step renders on the chain; the route change this render raised is logged now, with its frame.
    if (!pf.route_event.empty()) take.route_events.push_back(pf.route_event);
    return take;
  }
  // The announcement, corridor count and issue time as a render here reads them.
  NavigationInput::ObserveAnnouncement(now, &pf.step.route);
  take.outcome = NavPrefetchOutcome::kHit;
  take.step = std::move(pf.step);   // its route_event: the step logs it once, with its frame
  // This frame's rasters into the caller's buffers; pf takes the previous use's, freed here.
  hit_map->swap(pf.map_context);
  hit_route->swap(pf.route_mask);
  take.map_context = hit_map;
  take.route_mask = hit_route;
  return take;
}

}  // namespace de4sdv::driving::agent
