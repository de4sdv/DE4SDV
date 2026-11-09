// Phase profiler for the unoptimised reference path on a real exported map:
// splits one render into the C++ zero-fill, the per-call primitive packing, the
// native nav_render call and the total.  This is the "before" measurement that
// chose the optimisation target (98.5 % of the old render was the native call);
// NavigationRasterizer::Render no longer looks like this.
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

#include "navigation_raster.h"
#include "navigation_rasterizer.h"

namespace nav = de4sdv::driving::navigation;
using Clock = std::chrono::steady_clock;

static double Ms(Clock::time_point a, Clock::time_point b) {
  return std::chrono::duration<double, std::milli>(b - a).count();
}

static void Report(const char* name, std::vector<double> values) {
  if (values.empty()) return;
  std::sort(values.begin(), values.end());
  std::printf("%-22s p50 %7.3f  p90 %7.3f  p99 %7.3f  max %7.3f  mean %7.3f\n",
              name, values[values.size() / 2], values[values.size() * 9 / 10],
              values[values.size() * 99 / 100], values.back(),
              [&] {
                double sum = 0.0;
                for (double v : values) sum += v;
                return sum / static_cast<double>(values.size());
              }());
}

int main(int argc, char** argv) {
  if (argc < 3) {
    std::fprintf(stderr, "usage: %s map.json route.json [n]\n", argv[0]);
    return 2;
  }
  const int n = argc > 3 ? std::stoi(argv[3]) : 200;
  nav::NavigationRasterizer rasterizer;
  std::string error;
  if (!rasterizer.LoadMap(argv[1], &error) ||
      !rasterizer.LoadRoute(argv[2], &error)) {
    std::fprintf(stderr, "load: %s\n", error.c_str());
    return 3;
  }
  std::vector<std::array<double, 3>> poses;
  for (const auto& line : rasterizer.route().centerlines)
    for (std::size_t k = 0; k + 1 < line.size(); ++k)
      poses.push_back({line[k].x, line[k].y,
                       std::atan2(line[k + 1].y - line[k].y,
                                  line[k + 1].x - line[k].x)});
  if (poses.empty()) return 5;

  std::vector<float> map_context;
  std::vector<std::uint8_t> route_mask;
  std::vector<double> t_total, t_zero, t_pack, t_native;
  for (int i = 0; i < n; ++i) {
    const auto& w = poses[static_cast<std::size_t>(i * 7) % poses.size()];
    const auto t0 = Clock::now();
    map_context.assign(nav::NavigationRasterizer::MapContextSize(), 0.0F);
    route_mask.assign(nav::NavigationRasterizer::RouteMaskSize(), 0);
    const auto t1 = Clock::now();

    std::vector<double> map_points;
    std::vector<NavPrimitive> primitives;
    primitives.reserve(rasterizer.map().primitives.size());
    for (const nav::Primitive& primitive : rasterizer.map().primitives) {
      NavPrimitive packed{};
      packed.point_offset = static_cast<std::int32_t>(map_points.size() / 2);
      packed.point_count = static_cast<std::int32_t>(primitive.points.size());
      packed.kind = static_cast<std::int32_t>(primitive.kind);
      packed.channel = primitive.channel;
      packed.level = primitive.level_valid ? primitive.level : 0;
      packed.level_valid = primitive.level_valid ? 1 : 0;
      packed.width_m = primitive.width_m;
      packed.value = primitive.value;
      for (const nav::Point& point : primitive.points) {
        map_points.push_back(point.x);
        map_points.push_back(point.y);
      }
      primitives.push_back(packed);
    }
    std::vector<double> route_points;
    std::vector<std::int32_t> route_offsets{0};
    std::array<double, 2> destination{{0.0, 0.0}};
    std::int32_t route_line_count = 0;
    if (rasterizer.EffectiveRouteValid()) {
      for (const auto& line : rasterizer.route().centerlines) {
        for (const nav::Point& point : line) {
          route_points.push_back(point.x);
          route_points.push_back(point.y);
        }
        route_offsets.push_back(
            static_cast<std::int32_t>(route_points.size() / 2));
      }
      route_line_count = static_cast<std::int32_t>(route_offsets.size()) - 1;
      destination = {{rasterizer.route().destination.x,
                      rasterizer.route().destination.y}};
    }
    const auto t2 = Clock::now();

    NavPose pose{};
    pose.x_enu_m = w[0];
    pose.y_enu_m = w[1];
    pose.yaw_rad = w[2];
    NavGeometry geometry{};
    geometry.height_px = nav::kHeightPx;
    geometry.width_px = nav::kWidthPx;
    geometry.meters_per_pixel = nav::kMetersPerPixel;
    geometry.x_min_m = nav::kXMinM;
    geometry.x_max_m = nav::kXMaxM;
    geometry.y_min_m = nav::kYMinM;
    geometry.y_max_m = nav::kYMaxM;
    const std::int32_t status = nav_render(
        map_points.data(), static_cast<std::int32_t>(map_points.size() / 2),
        primitives.data(), static_cast<std::int32_t>(primitives.size()),
        route_points.data(), static_cast<std::int32_t>(route_points.size() / 2),
        route_offsets.data(), route_line_count, destination.data(),
        rasterizer.EffectiveRouteValid() ? 1 : 0, pose, geometry,
        nav::kRouteCorridorWidthM, nav::kDestinationMarkerRadiusM,
        nav::kRouteRearClipM, 0, 0, map_context.data(), route_mask.data());
    const auto t3 = Clock::now();
    if (status != 0) return 4;

    t_zero.push_back(Ms(t0, t1));
    t_pack.push_back(Ms(t1, t2));
    t_native.push_back(Ms(t2, t3));
    t_total.push_back(Ms(t0, t3));
  }
  std::printf("primitives %zu, map points %zu\n",
              rasterizer.map().primitives.size(),
              [&] {
                std::size_t p = 0;
                for (const auto& prim : rasterizer.map().primitives)
                  p += prim.points.size();
                return p;
              }());
  Report("output zero-fill", t_zero);
  Report("primitive packing", t_pack);
  Report("native nav_render", t_native);
  Report("phase total", t_total);
  return 0;
}
