// Differential parity sweep for the optimised Render: on a real exported map,
// render a set of poses with both paths (Render and RenderReference) and compare
// all 16 channels bit for bit.  The pose list can be written out so the Python
// test can compare the same poses against upstream's own reference path.
//
//   parity_sweep --map M --route R [--route-poses N] [--random-poses N]
//                [--seed S] [--poses-out FILE] [--json]
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <random>
#include <string>
#include <vector>

#include "navigation_raster.h"

namespace nav = de4sdv::driving::navigation;
using Pose = std::array<double, 3>;  // x, y, yaw

namespace {

bool WritePoses(const std::string& path, const std::vector<Pose>& poses) {
  std::FILE* file = std::fopen(path.c_str(), "w");
  if (file == nullptr) return false;
  for (const Pose& pose : poses) {
    // %.17g round-trips a double exactly through repr()/stod on the Python side
    std::fprintf(file, "%.17g %.17g %.17g\n", pose[0], pose[1], pose[2]);
  }
  std::fclose(file);
  return true;
}

// Poses evenly spaced along the route centre lines, heading from the next point.
std::vector<Pose> RoutePoses(const nav::NavigationRasterizer& rasterizer,
                             int count) {
  std::vector<Pose> poses;
  for (const std::vector<nav::Point>& line : rasterizer.route().centerlines) {
    for (std::size_t index = 0; index + 1 < line.size(); ++index) {
      poses.push_back({line[index].x, line[index].y,
                       std::atan2(line[index + 1].y - line[index].y,
                                  line[index + 1].x - line[index].x)});
    }
  }
  if (poses.size() <= static_cast<std::size_t>(count)) return poses;
  std::vector<Pose> selected;
  selected.reserve(static_cast<std::size_t>(count));
  const double step =
      static_cast<double>(poses.size() - 1) / static_cast<double>(count - 1);
  for (int index = 0; index < count; ++index) {
    const std::size_t source = static_cast<std::size_t>(
        std::llround(static_cast<double>(index) * step));
    selected.push_back(poses[std::min(source, poses.size() - 1)]);
  }
  return selected;
}

// Poses inside the map bounds: a few held at the map edge and at junction
// centroids, the rest uniform (deterministic for a given seed).
std::vector<Pose> RandomPoses(const nav::NavigationRasterizer& rasterizer,
                              int count, unsigned seed) {
  const nav::MapData& map = rasterizer.map();
  const double x_min = map.bounds_enu_m[0];
  const double y_min = map.bounds_enu_m[1];
  const double x_max = map.bounds_enu_m[2];
  const double y_max = map.bounds_enu_m[3];
  const double x_centre = 0.5 * (x_min + x_max);
  const double y_centre = 0.5 * (y_min + y_max);
  std::vector<Pose> poses;
  poses.push_back({x_min + 2.0, y_centre, 0.7});
  poses.push_back({x_max - 2.0, y_centre, -0.7});
  poses.push_back({x_centre, y_min + 2.0, 2.0});
  poses.push_back({x_centre, y_max - 2.0, -2.0});
  int junctions = 0;
  for (const nav::Primitive& primitive : map.primitives) {
    if (primitive.channel !=
            static_cast<std::int32_t>(nav::MapChannel::kIntersection) ||
        primitive.points.empty()) {
      continue;
    }
    double x = 0.0;
    double y = 0.0;
    for (const nav::Point& point : primitive.points) {
      x += point.x;
      y += point.y;
    }
    x /= static_cast<double>(primitive.points.size());
    y /= static_cast<double>(primitive.points.size());
    poses.push_back({x, y, 0.35});
    if (++junctions >= 2) break;
  }
  std::mt19937 generator(seed);
  std::uniform_real_distribution<double> x_distribution(x_min, x_max);
  std::uniform_real_distribution<double> y_distribution(y_min, y_max);
  std::uniform_real_distribution<double> yaw_distribution(-M_PI, M_PI);
  while (static_cast<int>(poses.size()) < count) {
    poses.push_back({x_distribution(generator), y_distribution(generator),
                     yaw_distribution(generator)});
  }
  return poses;
}

}  // namespace

int main(int argc, char** argv) {
  std::string map_path;
  std::string route_path;
  std::string poses_out;
  int route_poses = 60;
  int random_poses = 20;
  unsigned seed = 7;
  bool json = false;
  for (int index = 1; index < argc; ++index) {
    const std::string argument = argv[index];
    const auto next = [&]() -> std::string {
      if (index + 1 >= argc) {
        std::fprintf(stderr, "error: %s needs a value\n", argument.c_str());
        std::exit(2);
      }
      return argv[++index];
    };
    if (argument == "--map") map_path = next();
    else if (argument == "--route") route_path = next();
    else if (argument == "--poses-out") poses_out = next();
    else if (argument == "--route-poses") route_poses = std::stoi(next());
    else if (argument == "--random-poses") random_poses = std::stoi(next());
    else if (argument == "--seed") seed = static_cast<unsigned>(std::stoul(next()));
    else if (argument == "--json") json = true;
    else {
      std::fprintf(stderr, "error: unknown argument %s\n", argument.c_str());
      return 2;
    }
  }
  if (map_path.empty() || route_path.empty()) {
    std::fprintf(stderr,
                 "usage: %s --map M --route R [--route-poses N] "
                 "[--random-poses N] [--seed S] [--poses-out FILE] [--json]\n",
                 argv[0]);
    return 2;
  }

  nav::NavigationRasterizer rasterizer;
  std::string error;
  if (!rasterizer.LoadMap(map_path, &error) ||
      !rasterizer.LoadRoute(route_path, &error)) {
    std::fprintf(stderr, "load: %s\n", error.c_str());
    return 3;
  }
  std::vector<Pose> poses = RoutePoses(rasterizer, route_poses);
  const std::vector<Pose> random = RandomPoses(rasterizer, random_poses, seed);
  poses.insert(poses.end(), random.begin(), random.end());
  if (!poses_out.empty() && !WritePoses(poses_out, poses)) {
    std::fprintf(stderr, "cannot write %s\n", poses_out.c_str());
    return 4;
  }

  std::array<double, nav::kMapChannels> map_max_abs{};
  std::array<double, nav::kRouteChannels> route_max_abs{};
  std::vector<float> fast_map;
  std::vector<float> reference_map;
  std::vector<std::uint8_t> fast_route;
  std::vector<std::uint8_t> reference_route;
  std::size_t map_mismatch_pixels = 0;
  std::size_t route_mismatch_pixels = 0;
  int mismatched_poses = 0;
  for (const Pose& pose : poses) {
    if (!rasterizer.Render(pose[0], pose[1], pose[2], &fast_map, &fast_route,
                           &error) ||
        !rasterizer.RenderReference(pose[0], pose[1], pose[2], &reference_map,
                                    &reference_route, &error)) {
      std::fprintf(stderr, "render: %s\n", error.c_str());
      return 5;
    }
    bool identical = true;
    for (std::int32_t channel = 0; channel < nav::kMapChannels; ++channel) {
      const std::size_t offset =
          static_cast<std::size_t>(channel) * nav::kHeightPx * nav::kWidthPx;
      for (std::size_t index = offset;
           index < offset + static_cast<std::size_t>(nav::kHeightPx) *
                                nav::kWidthPx;
           ++index) {
        if (fast_map[index] == reference_map[index]) continue;
        identical = false;
        ++map_mismatch_pixels;
        map_max_abs[static_cast<std::size_t>(channel)] =
            std::max(map_max_abs[static_cast<std::size_t>(channel)],
                     std::fabs(static_cast<double>(fast_map[index]) -
                               static_cast<double>(reference_map[index])));
      }
    }
    for (std::int32_t channel = 0; channel < nav::kRouteChannels; ++channel) {
      const std::size_t offset =
          static_cast<std::size_t>(channel) * nav::kHeightPx * nav::kWidthPx;
      for (std::size_t index = offset;
           index < offset + static_cast<std::size_t>(nav::kHeightPx) *
                                nav::kWidthPx;
           ++index) {
        if (fast_route[index] == reference_route[index]) continue;
        identical = false;
        ++route_mismatch_pixels;
        route_max_abs[static_cast<std::size_t>(channel)] =
            std::max(route_max_abs[static_cast<std::size_t>(channel)],
                     std::fabs(static_cast<double>(fast_route[index]) -
                               static_cast<double>(reference_route[index])));
      }
    }
    if (!identical) ++mismatched_poses;
  }

  double map_max = 0.0;
  for (const double value : map_max_abs) map_max = std::max(map_max, value);
  double route_max = 0.0;
  for (const double value : route_max_abs) route_max = std::max(route_max, value);

  if (json) {
    std::printf("{\"poses\":%zu,\"route_poses\":%d,\"random_poses\":%d,"
                "\"mismatched_poses\":%d,\"map_mismatch_pixels\":%zu,"
                "\"route_mismatch_pixels\":%zu,\"map_max_abs\":[",
                poses.size(), route_poses, random_poses, mismatched_poses,
                map_mismatch_pixels, route_mismatch_pixels);
    for (std::size_t channel = 0; channel < map_max_abs.size(); ++channel) {
      std::printf("%s%.17g", channel == 0 ? "" : ",", map_max_abs[channel]);
    }
    std::printf("],\"route_max_abs\":[");
    for (std::size_t channel = 0; channel < route_max_abs.size(); ++channel) {
      std::printf("%s%.17g", channel == 0 ? "" : ",", route_max_abs[channel]);
    }
    std::printf("],\"map_max\":%.17g,\"route_max\":%.17g}\n", map_max,
                route_max);
  } else {
    std::printf("poses %zu: mismatched %d, map pixels %zu, route pixels %zu\n",
                poses.size(), mismatched_poses, map_mismatch_pixels,
                route_mismatch_pixels);
    for (std::size_t channel = 0; channel < map_max_abs.size(); ++channel) {
      std::printf("  map   channel %2zu max abs diff %.17g\n", channel,
                  map_max_abs[channel]);
    }
    for (std::size_t channel = 0; channel < route_max_abs.size(); ++channel) {
      std::printf("  route channel %2zu max abs diff %.17g\n", channel,
                  route_max_abs[channel]);
    }
  }
  return (mismatched_poses == 0 && map_max == 0.0 && route_max == 0.0) ? 0 : 1;
}
