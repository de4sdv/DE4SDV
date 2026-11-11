// Render-cost probe for the navigation rasterizer on a real exported map (Town10HD_Opt):
// load once, render along the route, report per-render wall time (steady clock).
#include <algorithm>
#include <cmath>
#include <chrono>
#include <array>
#include <cstdio>
#include <string>
#include <vector>

#include "navigation_raster.h"

int main(int argc, char** argv) {
  if (argc < 3) { std::fprintf(stderr, "usage: %s map.json route.json [n]\n", argv[0]); return 2; }
  const int n = argc > 3 ? std::stoi(argv[3]) : 200;
  de4sdv::driving::navigation::NavigationRasterizer r;
  std::string err;
  auto t0 = std::chrono::steady_clock::now();
  if (!r.LoadMap(argv[1], &err) || !r.LoadRoute(argv[2], &err)) { std::fprintf(stderr, "load: %s\n", err.c_str()); return 3; }
  const double load_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
  std::vector<std::array<double, 3>> poses;  // along the route centerlines, heading from consecutive points
  for (const auto& line : r.route().centerlines)
    for (std::size_t k = 0; k + 1 < line.size(); ++k)
      poses.push_back({line[k].x, line[k].y, std::atan2(line[k + 1].y - line[k].y, line[k + 1].x - line[k].x)});
  if (poses.empty()) { std::fprintf(stderr, "no route poses\n"); return 5; }
  std::vector<float> map_context;
  std::vector<std::uint8_t> route_mask;
  std::vector<double> ms;
  for (int i = 0; i < n; ++i) {
    const auto& w = poses[static_cast<std::size_t>(i * 7) % poses.size()];
    const auto a = std::chrono::steady_clock::now();
    if (!r.Render(w[0], w[1], w[2], &map_context, &route_mask, &err)) { std::fprintf(stderr, "render: %s\n", err.c_str()); return 4; }
    ms.push_back(std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - a).count());
  }
  std::sort(ms.begin(), ms.end());
  std::printf("load %.1f ms; renders %d: p50 %.2f ms, p90 %.2f ms, p99 %.2f ms, max %.2f ms\n", load_ms, n, ms[ms.size() / 2],
              ms[ms.size() * 9 / 10], ms[ms.size() * 99 / 100], ms.back());
  return 0;
}
