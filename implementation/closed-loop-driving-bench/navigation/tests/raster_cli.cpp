// Parity and unit driver for navigation_raster: renders one pose with the C++
// library and writes the two rasters as raw little-endian arrays, so the Python
// test can compare them with upstream's NativeNavigationRasterizer pixel by
// pixel.  Also probes the RouteAnnouncement layout against payloads.h.
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include "de4sdv/driving/payloads.h"
#include "navigation_raster.h"

namespace nav = de4sdv::driving::navigation;

static bool WriteFile(const std::string& path, const void* data,
                      std::size_t bytes) {
  std::FILE* file = std::fopen(path.c_str(), "wb");
  if (file == nullptr) return false;
  const bool ok = std::fwrite(data, 1, bytes, file) == bytes;
  std::fclose(file);
  return ok;
}

static int PrintLayout() {
  using de4sdv::driving::RouteAnnouncement;
  static_assert(sizeof(nav::RouteAnnouncement) == sizeof(RouteAnnouncement),
                "RouteAnnouncement size differs from payloads.h");
  static_assert(offsetof(nav::RouteAnnouncement, version) ==
                    offsetof(RouteAnnouncement, version),
                "version offset");
  static_assert(offsetof(nav::RouteAnnouncement, corridorPoints) ==
                    offsetof(RouteAnnouncement, corridorPoints),
                "corridorPoints offset");
  static_assert(offsetof(nav::RouteAnnouncement, issueTime) ==
                    offsetof(RouteAnnouncement, issueTime),
                "issueTime offset");
  static_assert(offsetof(nav::RouteAnnouncement, routeFile) ==
                    offsetof(RouteAnnouncement, routeFile),
                "routeFile offset");
  static_assert(offsetof(nav::RouteAnnouncement, routeSha256) ==
                    offsetof(RouteAnnouncement, routeSha256),
                "routeSha256 offset");
  std::printf(
      "{\"size\":%zu,\"version\":%zu,\"corridorPoints\":%zu,\"issueTime\":%zu,"
      "\"routeFile\":%zu,\"routeSha256\":%zu,\"routeFileBytes\":%zu,"
      "\"routeSha256Bytes\":%zu,\"kInterfaceVersion\":%u}\n",
      sizeof(nav::RouteAnnouncement),
      offsetof(nav::RouteAnnouncement, version),
      offsetof(nav::RouteAnnouncement, corridorPoints),
      offsetof(nav::RouteAnnouncement, issueTime),
      offsetof(nav::RouteAnnouncement, routeFile),
      offsetof(nav::RouteAnnouncement, routeSha256),
      sizeof(nav::RouteAnnouncement::routeFile),
      sizeof(nav::RouteAnnouncement::routeSha256),
      de4sdv::driving::kInterfaceVersion);
  return 0;
}

int main(int argc, char** argv) {
  std::string map_path;
  std::string route_path;
  std::string map_out;
  std::string route_out;
  double x = 0.0;
  double y = 0.0;
  double yaw = 0.0;
  bool have_pose = false;
  double announce_issue = 0.0;
  double now = 0.0;
  int announce_corridor = -1;
  bool have_evaluate = false;
  for (int index = 1; index < argc; ++index) {
    const std::string argument = argv[index];
    const auto next = [&](const char* name) -> const char* {
      if (index + 1 >= argc) {
        std::fprintf(stderr, "error: %s needs a value\n", name);
        std::exit(2);
      }
      return argv[++index];
    };
    if (argument == "--layout") return PrintLayout();
    if (argument == "--map") map_path = next("--map");
    else if (argument == "--route") route_path = next("--route");
    else if (argument == "--map-out") map_out = next("--map-out");
    else if (argument == "--route-out") route_out = next("--route-out");
    else if (argument == "--pose") {
      x = std::stod(next("--pose"));
      y = std::stod(next("--pose"));
      yaw = std::stod(next("--pose"));
      have_pose = true;
    } else if (argument == "--announce-issue") {
      announce_issue = std::stod(next("--announce-issue"));
      have_evaluate = true;
    } else if (argument == "--now") {
      now = std::stod(next("--now"));
    } else if (argument == "--announce-corridor-points") {
      announce_corridor = std::stoi(next("--announce-corridor-points"));
    } else if (argument == "--version") {
      std::printf("%s\n", nav::NavigationRasterizer::RendererVersion());
      return 0;
    } else {
      std::fprintf(stderr, "error: unknown argument %s\n", argument.c_str());
      return 2;
    }
  }
  if (map_path.empty() || !have_pose) {
    std::fprintf(stderr, "usage: raster_cli --map M [--route R] --pose x y yaw "
                         "[--map-out F] [--route-out F] [--layout] "
                         "[--announce-issue S --now S "
                         "--announce-corridor-points N]\n");
    return 2;
  }

  nav::NavigationRasterizer rasterizer;
  std::string error;
  if (!rasterizer.LoadMap(map_path, &error)) {
    std::fprintf(stderr, "error: %s\n", error.c_str());
    return 3;
  }
  if (!route_path.empty() && !rasterizer.LoadRoute(route_path, &error)) {
    std::fprintf(stderr, "error: %s\n", error.c_str());
    return 3;
  }
  std::vector<float> map_context;
  std::vector<std::uint8_t> route_mask;
  if (!rasterizer.Render(x, y, yaw, &map_context, &route_mask, &error)) {
    std::fprintf(stderr, "error: %s\n", error.c_str());
    return 4;
  }
  if (!map_out.empty() &&
      !WriteFile(map_out, map_context.data(), map_context.size() * sizeof(float))) {
    std::fprintf(stderr, "error: cannot write %s\n", map_out.c_str());
    return 5;
  }
  if (!route_out.empty() &&
      !WriteFile(route_out, route_mask.data(), route_mask.size())) {
    std::fprintf(stderr, "error: cannot write %s\n", route_out.c_str());
    return 5;
  }

  // Cheap invariants, printed for the Python test to assert on.
  double map_sum = 0.0;
  std::size_t map_nonzero = 0;
  for (const float value : map_context) {
    map_sum += value;
    if (value != 0.0F) ++map_nonzero;
  }
  std::size_t corridor_pixels = 0;
  std::size_t destination_pixels = 0;
  const std::size_t pixels =
      static_cast<std::size_t>(nav::kHeightPx) * nav::kWidthPx;
  for (std::size_t index = 0; index < pixels; ++index) {
    if (route_mask[index] != 0) ++corridor_pixels;
    if (route_mask[pixels + index] != 0) ++destination_pixels;
  }
  // The points the agent counts for ICD A16 (waypointsInWindow).
  std::size_t centerline_points = 0;
  for (const auto& line : rasterizer.route().centerlines) {
    centerline_points += line.size();
  }
  std::printf(
      "{\"renderer_version\":\"%s\",\"map_nonzero\":%zu,\"map_sum\":%.17g,"
      "\"corridor_pixels\":%zu,\"destination_pixels\":%zu,\"route_valid\":%s,"
      "\"map_valid\":%s,\"route_centerline_points\":%zu",
      nav::NavigationRasterizer::RendererVersion(), map_nonzero, map_sum,
      corridor_pixels, destination_pixels,
      rasterizer.EffectiveRouteValid() ? "true" : "false",
      rasterizer.map_valid() ? "true" : "false", centerline_points);

  if (have_evaluate) {
    nav::RouteAnnouncement announcement;
    announcement.version = de4sdv::driving::kInterfaceVersion;
    announcement.corridorPoints = static_cast<std::uint32_t>(
        announce_corridor >= 0 ? announce_corridor
                               : rasterizer.route().corridor_points);
    announcement.issueTime = announce_issue;
    const nav::RouteValidity validity =
        rasterizer.EvaluateRoute(&announcement, now, route_mask);
    std::printf(
        ",\"validity\":{\"corridor_present\":%s,\"corridor_declared\":%s,"
        "\"route_age_seconds\":%.17g,\"stale\":%s,\"empty\":%s,\"cause\":%d}",
        validity.corridor_present ? "true" : "false",
        validity.corridor_declared ? "true" : "false",
        validity.route_age_seconds, validity.stale ? "true" : "false",
        validity.empty ? "true" : "false", validity.cause);
    const nav::RouteValidity never =
        rasterizer.EvaluateRoute(nullptr, now, route_mask);
    std::printf(
        ",\"no_announcement\":{\"stale\":%s,\"cause\":%d,\"age_infinite\":%s}",
        never.stale ? "true" : "false", never.cause,
        std::isinf(never.route_age_seconds) ? "true" : "false");
  }
  std::printf("}\n");
  return 0;
}
