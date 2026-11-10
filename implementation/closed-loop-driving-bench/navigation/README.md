# Navigation inputs of the closed-loop driving bench (S3, INC-DRIVING-001 slice 10b)

The bench used to feed the AutoE2E checkpoint zeros for its two navigation
inputs.  This directory builds the real ones:

* a **CARLA map** exported from the running simulator into AutoE2E's navigation
  map contract (JSON);
* a **route** between two points of that map, in the ICD section 9 format;
* a **C++ library** that renders the checkpoint's `map_context` (14 channels)
  and `route_mask` (2 channels) for an ego pose.  It packs the primitives
  exactly as upstream's `rasterizer.py` does — same order, channel, width and
  level — but **once** per map/route, culls them to the pose's raster window,
  and fills the map channels with a span rasterizer that reproduces upstream's
  per-pixel decisions bit for bit.  The output zeroing and the route corridor
  stay in upstream's own native renderer.  `RenderReference` keeps the original
  pack-every-call path; the two are bit-identical;
* the **route provider** process that announces the route to the input activity
  every 500 ms of simulation time.

Upstream is pinned at `cb50764b8250a3c44ee5b79b87ba02c5a83b0c91`
(github.com/autowarefoundation/auto_e2e) and lives read-only in `.upstream/`.
Nothing upstream is modified; the native library is built with upstream's own
`Model/navigation/native/build.py`.

## Files

| File | What it is |
|---|---|
| `carla_map_export.py` | CARLA map → navigation map JSON (bench, needs `carla`) |
| `route_from_carla.py` | CARLA `GlobalRoutePlanner` route → ICD section 9 file (bench) |
| `carla_frame.py` | the CARLA ↔ map frame conversion, in one place |
| `nav_map_json.py` | map JSON ↔ upstream `NavigationMap`; route file reader |
| `autoe2e_bridge.py` | imports the pinned upstream modules read-only |
| `navigation_raster.{h,cpp}` | the C++ rasterizer library (no dependencies beyond libstdc++) |
| `route_provider.py` | the route provider process (UDP 127.0.0.1:47110, JSONL logs) |
| `parity_report.py` | per-channel C++ vs Python difference report (synthetic maps) |
| `tests/` | 74 tests: exporters on a fake `carla`, parity, provider, layout |
| `tests/parity_sweep.cpp` | `Render` vs `RenderReference` sweep on a real map (`make parity`) |
| `tests/render_cost.cpp` | per-render wall clock on a real map (`make bench`) |
| `tests/render_profile.cpp` | the unoptimised path split into zero-fill / packing / native call (`make profile`) |
| `tests/fakes/` | fake `carla` and fake `agents.navigation.global_route_planner` |

## Build and test (local, no CARLA, no GPU)

```bash
cd implementation/closed-loop-driving-bench/navigation
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python numpy pytest
make all          # native rasterizer (as-is) + library + raster_cli + the probes
.venv/bin/python -m pytest -q tests
.venv/bin/python parity_report.py

# real map and route exported on the bench:
make bench && build/render_cost map.json route.json 500
make parity && build/parity_sweep --map map.json --route route.json --json
```

The real-map parity test (`tests/test_navigation_raster_real_parity.py`) runs
when the directory named by `DE4SDV_NAVIGATION_REAL_MAP_DIR` holds `map.json`
and `route.json`, and skips otherwise: the export is a run artefact, not a
repository file.

`make native` runs upstream's `build.py` unchanged; `make lib` compiles
`navigation_raster.cpp` and links `build/libnavigation_rasterizer.so` with
`-Wl,-rpath,'$ORIGIN'`, so the pair can be copied to the S-CORE host as-is.
Set `AUTO_E2E_ROOT` if the upstream clone is elsewhere and
`AUTO_E2E_NAVIGATION_RASTERIZER_LIBRARY` if the .so is elsewhere.

## On the bench, in order

```bash
# 1. map (once per simulator release, on the simulator host or where the wheel is)
python3 carla_map_export.py --host 10.10.0.2 --port 2000 --map Town10HD_Opt \
    --out /runs/$RUN/navigation/map.json

# 2. route between two spawn points (once per run)
python3 route_from_carla.py --host 10.10.0.2 --port 2000 \
    --start-spawn 0 --end-spawn 40 --map Town10HD_Opt \
    --out /runs/$RUN/navigation/route.json
#    or --start 12.5,-3.0 --end 210.0,88.0

# 3. the route provider, on the S-CORE host, started by the Launch Manager
python3 route_provider.py --route /runs/$RUN/navigation/route.json \
    --run-dir /runs/$RUN --carla-host 10.10.0.2 --carla-port 2000
#    fault injection (SC-DRIVING-003):  --stale-after-s 6   --empty-after-s 8
```

The input activity loads both files once and renders per step:

```cpp
using namespace de4sdv::driving::navigation;
NavigationRasterizer rasterizer;
std::string error;
rasterizer.LoadMap("/runs/$RUN/navigation/map.json", &error);    // once
rasterizer.LoadRoute("/runs/$RUN/navigation/route.json", &error); // once

std::vector<float> map_context;        // 14 * 450 * 300 floats, CHW
std::vector<std::uint8_t> route_mask;  //  2 * 450 * 300 bytes, CHW
rasterizer.Render(x_map, y_map, yaw_map, &map_context, &route_mask, &error);

RouteAnnouncement announcement;        // the newest datagram, payloads.h layout
const RouteValidity validity =
    rasterizer.EvaluateRoute(&announcement, simulation_time_s, route_mask);
// validity.corridor_present, validity.route_age_seconds, validity.stale,
// validity.empty, validity.cause  (kNone / kRouteStale / kRouteEmpty)
```

`Render` is `const` and allocation-free after the first call apart from the two
output vectors; one instance per step thread.

## The 16 channels, as upstream defines them

Geometry `autoe2e-bev-450x300-0p4m-v1`: 450 rows × 300 columns, 0.4 m/pixel,
row 0 at x=+120 m (front), row 449 at x=-60 m; column 0 at y=+60 m (left),
column 299 at y=-60 m; pixel centres, ego at (row, col) = (299.5, 149.5).
Channel-major, row-major inside a channel.

| # | `MapChannel` | dtype | filled by |
|---|---|---|---|
| 0 | `DRIVABLE_AREA` | f32 0/1 | drivable lane polygons (one per lane: left boundary + reversed right) |
| 1 | `LANE_BOUNDARY` | f32 0/1 | lane side lines, 1 m wide (polyline distance test) |
| 2 | `LANE_CENTERLINE` | f32 0/1 | lane centre lines, 1 m wide |
| 3 | `INTERSECTION` | f32 0/1 | junction footprint polygons |
| 4 | `CROSSWALK` | f32 0/1 | `map.get_crosswalks()` closed rings, one polygon each |
| 5 | `STOP_LINE` | f32 0/1 | 1 m lines at the traffic lights |
| 6 | `STATIC_TRAFFIC_SIGNAL` | f32 0/1 | 2 m discs at the light positions |
| 7 | `TRAFFIC_DIRECTION_SIN` | f32 | `(sin θ + 1)/2` per lane segment, θ the lane's driving direction |
| 8 | `TRAFFIC_DIRECTION_COS` | f32 | `(cos θ + 1)/2` per lane segment, θ the lane's driving direction |
| 9 | `TRAFFIC_DIRECTION_VALID` | f32 0/1 | 1 where a direction is drawn |
| 10 | `KNOWN_MAP_AREA` | f32 0/1 | the map `bounds_enu_m` rectangle (always) |
| 11 | `ROAD_LEVEL` | f32 | `(level + 8)/16`; all zero for CARLA (no layered roads) |
| 12 | `ROAD_LEVEL_VALID` | f32 0/1 | zero for CARLA |
| 13 | `OVERLAPPING_LEVEL_AMBIGUITY` | f32 0/1 | zero for CARLA |
| R0 | `SELECTED_CORRIDOR` | u8 0/1 | route centre lines in a 3.5 m corridor, clipped behind x=-10 m |
| R1 | `DESTINATION` | u8 0/1 | 2 m disc at the route's destination |

Levels 11-13 stay zero because a CARLA map has no layered roads; the fields
exist and the loader honours a `level` if a future export provides one.

## Frame conventions

CARLA's world is left-handed (x forward, **y to the right**, yaw clockwise).
The map frame is right-handed and the ICD fixes the conversion:
`x_map = x_carla`, `y_map = -y_carla`, `yaw_map = -yaw_carla`.  The exporter
applies it to every point, heading and boundary offset; the route file and the
ego pose are in the same frame; upstream's rasterizer rotates map points into
the ego frame with the usual `R(-yaw)`.

Two consequences worth knowing:

* the conversion mirrors the plane, so a side that is on the driver's left in
  CARLA is on the driver's right in the map frame.  Primitive ids keep the
  CARLA-side label as provenance; the rasterizer draws both sides into
  `LANE_BOUNDARY` and closes drivable polygons by the even-odd rule, so no
  raster depends on the label or on polygon winding.
* distances, widths and angle magnitudes are unchanged.

The map JSON's `frame` carries `frame_id = "carla:<map>"`, and
`provenance.frame_conversion` records the rule in the file itself.

## Route announcement (ICD section 9)

`route_provider.py` sends one 272-byte datagram to `127.0.0.1:47110`:

```
0   4  version         uint32   kInterfaceVersion = 1
4   4  corridorPoints  uint32   route waypoints; 0 means "no route corridor"
8   8  issueTime       double   simulation s of the newest world tick (frame * 0.1)
16  192 routeFile       char[192] absolute path, NUL-terminated
208 64  routeSha256     char[64]  exactly 64 hex chars (no room for a NUL)
```

`struct.pack("<IId192s64s")`; the offsets are asserted against `payloads.h` in
`tests/test_route_provider.py` through `raster_cli --layout` (compiled against
the real header).  Cadence: the first tick announces at once, then every 0.5 s
of simulation time; `issueTime` is the tick that triggered the datagram, not the
scheduled instant.  Simulation time is always `frame * 0.1 s`, never CARLA's
float stamp.  Fault knobs are measured from the first observed tick.

Logs (`<run_dir>/score/route_provider.jsonl`), ICD section 6: `start`,
`config` twice (provider and clock source), `out.route_announcement` per
datagram with the full payload and `clocks {issueTime: simulation}` (the record
VC-DRIVING-025 reads, `case-evaluators/OBSERVABLES.md` row 025), `fault.stale`,
`fault.empty`, `error`, `stop`.

## REQ-DRIVING-025 semantics in the library

`EvaluateRoute(announcement, now_simulation_s, route_mask)`:

* `corridor_present` — the rendered `SELECTED_CORRIDOR` channel has a pixel;
* `corridor_declared` — the announcement says `corridorPoints > 0`;
* `route_age_seconds` = `now - issueTime` (infinite when nothing was announced);
* `stale` — age > 1.0 s, or nothing announced yet;
* `empty` — no corridor pixel **or** the announcement declares 0 points;
* `cause` — `kNone`, else `kRouteEmpty` first and `kRouteStale` second.

An empty corridor is reported ahead of staleness: it is a definite condition,
while a stale route may only be late.  Both begin the stop response, so the
order only selects the reported cause (see the open question below).

## Render cost and why it is shaped this way

`render_cost` on the first real `Town10HD_Opt` export, before the crosswalk fix (903 KB: 168 centre lines, 336
boundaries, 168 drivable polygons, 20 crosswalks, 9 junction polygons, 15
signals, 18657 points) and its 282-waypoint route, on this aarch64 host
(Cortex-A78AE), one `Render` per call, 500 renders:

| | p50 | p90 | p99 | max |
|---|---|---|---|---|
| before (pack every call, whole map to the native renderer) | 39.2 ms | 47.1 ms | 68.1 ms | 69.4 ms |
| after (`Render`) | 3.21 ms | 4.44 ms | **6.70 ms** | 7.6 ms |

A phase split of the old path (`render_profile`) put 98.5 % of a render inside
the native `nav_render` call: 0.39 ms zero-fill, 0.24 ms packing, 38.3 ms
native.  Inside that call the drivable polygons alone were 28.6 ms and the
lane/direction lines 8.5 ms -- per-pixel `point_in_polygon` over every vertex
and a per-pixel `hypot`, plus one heap allocation per line segment.  Culling
alone was measured at ~3 %: the window is 180 m x 120 m of a ~235 m x 219 m
map, so it keeps 312 of 900 primitives on average (min 73, max 659), and the
expensive primitives are the ones that stay.  The speed therefore comes from
the fill itself:

* the primitives are packed once, at `SetMap`/`SetRoute` (0.24 ms per render
  saved, no per-call `std::vector` growth);
* an axis-aligned map-frame box, inflated by the stroke's reach, decides which
  primitives are drawn, in upstream's packing order (draw order is what
  overlapping writes depend on);
* polygons are filled as spans: `point_in_polygon` toggles once per crossed
  edge, so a column's crossings sorted by row give the inside row intervals --
  same crossing test, same `x_intersection` expression, same writes;
* lines compare squared point-segment distances (no per-pixel `hypot`, no
  per-pixel division, no per-segment allocation); the pixel candidates are the
  stroke's own reach instead of upstream's +1 px slack, and the exact test
  still decides every candidate;
* neither the outputs nor the scratch buffers are reallocated per call, and the
  buffers are not zero-filled twice.

Nothing upstream normalises over primitives and `KNOWN_MAP_AREA` is an ordinary
4-point primitive, so no channel needs un-culled input: a culled primitive
writes no pixel of the window, and the level channels (11-13) are read and
written per pixel by the same primitive that writes the mask.

## Test evidence (local, aarch64, no CARLA)

```
$ make all && .venv/bin/python -m pytest -q tests
74 passed in 19.5s
$ .venv/bin/python parity_report.py
cases: 25, mismatched: 0
  map   DRIVABLE_AREA ... OVERLAPPING_LEVEL_AMBIGUITY   max abs diff 0   (all 14)
  route SELECTED_CORRIDOR, DESTINATION                  max abs diff 0   (both)
$ build/parity_sweep --map map.json --route route.json --json      # real map
{"poses":80,"route_poses":60,"random_poses":20,"mismatched_poses":0,
 "map_mismatch_pixels":0,"route_mismatch_pixels":0,
 "map_max_abs":[0,0,0,0,0,0,0,0,0,0,0,0,0,0],"route_max_abs":[0,0],...}
```

The parity tests compare arrays, not tolerances: float32 bit patterns and
uint8 pixels.  Coverage:

* 25 pose cases over a straight road, an L junction and a roundabout ring, each
  with and without a route (`parity_report.py`, `test_navigation_raster_parity.py`);
* the real map and route at 80 poses -- 60 evenly spaced along the route and 20
  inside the map bounds (4 held at the map edge, 2 at junction centroids) --
  against both `RenderReference` (`parity_sweep`) and upstream's
  `NativeNavigationRasterizer.render` (`test_navigation_raster_real_parity.py`);
  a wider sweep of 200 route + 200 random poses is the same command with
  `--route-poses 200 --random-poses 200`;
* a level-carrying fixture, because the CARLA export has no road levels and
  channels 11-13 would otherwise stay untested (`test_navigation_raster_levels.py`).

## What is untested without CARLA

Only testable on the bench (no aarch64 CARLA wheel, no GPU here):

1. `carla_map_export.py` against the real `carla` API: `generate_waypoints`,
   `get_topology`, `get_crosswalks` (beta in 0.9.16), traffic-light actors and
   `traffic.traffic_light` filtering.  The fake exercises every code path but
   with CARLA-shaped objects, not CARLA.  The first `Town10HD_Opt` export
   (2026-11-09) showed two shapes the fake did not have, both fixed with tests
   on 2026-11-10:
   - `get_crosswalks` gives each crosswalk as a closed ring, its first point
     repeated at its end (16 rings of 5 points).  Grouped by 4, they became
     20 polygons joining corners of different crosswalks, up to 189 m long; at
     the start of the bench route the whole road 40 m ahead was crosswalk.
     The export now splits the list at each ring's closing point and leaves
     out a run that never closes (before, any count that was no multiple of 4
     gave one convex hull of all crosswalks).
   - CARLA lets `s` grow along the road's reference line in every lane and
     faces each waypoint in its lane's driving direction.  Written in `s`
     order, every lane with a positive id ran against its traffic in the
     direction channels.  The export now turns each lane to its waypoints'
     heading, and a boundary that two opposite lanes share is still drawn once.
   The fake now gives its crosswalk as CARLA does; a two-way road in the tests
   gives its lanes as CARLA does.  The real export has to be made again with
   this code.
2. `route_from_carla.py` against the real `GlobalRoutePlanner` (the fake
   reproduces only `trace_route`'s contract).
3. Junction polygons: CARLA publishes no junction footprint, so the export is
   the convex hull of the junction's drivable lanes.  Its fidelity to the real
   junction is unmeasured.
4. Stop lines: CARLA publishes none; the export draws the lateral line through
   the waypoint under each traffic light.  Real stop-line placement is
   unverified.
5. `route_provider.py --carla-host`: `world.on_tick` cadence under the pacer,
   and whether announcements keep up when the pacer runs faster than real time.
6. End-to-end: that a CARLA route's corridor covers the driven path
   (REQ-DRIVING-007 success criterion), and the 100 ms stop response of
   REQ-DRIVING-025 with the real agent.
7. Render cost on the S-CORE host: the numbers above are this aarch64 host
   (Cortex-A78AE).  The 100 ms planning budget leaves ~15x margin here, so the
   x86 host has more, but it has not been measured.  The cull is a linear scan
   over the 900 primitives (no spatial index) and the fast path is our own
   rasterizer: parity is proven over the sweeps listed above, not by
   construction, so a new map shape (self-intersecting polygons, levels) is
   worth a `parity_sweep` run before it is trusted.

## Assumptions

* The map and the route name the same map: the route's `map` must equal the map
  JSON's `map_version`, otherwise the route raster is zero (upstream's rule).
* One `NavigationMap` per run; `Level` is absent because CARLA 0.9.16 has no
  layered roads.
* Lane geometry comes from CARLA waypoints every 2 m and the per-waypoint
  `lane_width`; boundaries are offsets of the centre line, not CARLA data.
  Only lanes whose `lane_type` is `Driving` are exported (CARLA also samples
  sidewalks and bike lanes); a waypoint without `lane_type` is kept.
* The route is fixed for the run; the provider does not re-read the file.
  If the file changes under a running provider, the announced SHA-256 no longer
  matches the content (the C++ library computes the SHA-256 of what it loaded,
  so a mismatch is detectable, but nothing compares the two yet).
* A route split by `road_id` runs gives one corridor polyline per run; a lane
  change inside one road is a single polyline, which is what the corridor
  channel needs.

## Contract and model notes

* **`payloads.h`, `RouteAnnouncement.routeSha256[64]`**: the comment above
  `kIdLength` says "NUL-terminated, truncated", but 64 bytes hold exactly 64
  hex characters, so this field cannot be NUL-terminated.  Proposed change:
  state it as "exactly 64 hex characters, not NUL-terminated", or widen to 65.
  Implemented as the former; the layout is byte-identical.
* **ICD section 9 has no map artefact**: the rasterizer needs the exported map,
  its identity and the map/route match rule, but the ICD fixes only the route
  file.  Proposed addition to section 7/9: `<run_dir>/navigation/map.json`,
  its SHA-256 in the run record, and "a route whose `map` differs from the
  map's `map_version` renders no corridor".
* **ICD section 6 does not name the provider's log file**: using
  `<run_dir>/score/route_provider.jsonl`; propose fixing the name.
* **Model (MAP-DRIVING-ROUTE, `ScenarioRouteProvider`) says the route is "read
  ... at the start of the run and handed to the input activity"; the ICD adds a
  500 ms announcement stream.**  That is a refinement needed to make the 1 s age
  of REQ-DRIVING-025 observable, not a contradiction, but the model names no
  route protocol.  Proposed: add the announcement (identity, issue time,
  corridor count) as the candidate software contract message of
  `ScenarioRouteProvider.routeOut`.
* **Model says "a route the ego vehicle has left ... sets the input condition";
  the contract has no such signal.**  `kRouteStale`/`kRouteEmpty` cover age and
  emptiness only.  Proposed: either add a cause (e.g. `kRouteDeparted`, meaning
  no corridor pixel ahead of the ego) or record off-route detection as out of
  scope for the bench.
* **REQ-DRIVING-025 is stated in simulation time**, so the age must be judged
  per step against `issueTime`, never at datagram arrival; a 500 ms cadence plus
  a 1 s limit leaves 0.5 s of margin, and the step granularity bounds detection
  to 100 ms.  The consumer, not the provider, owns that judgement.
