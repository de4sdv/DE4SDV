# AEBS Visualization Contract — INC-AEBS-010

Status: proposed (pending plan Tasks 3–7 implementation and runtime review)
Owner: implementation/aebs-aaos-sdv-visualization-bench
Authority: SysML packages under `textual-notation-of-model/packages/features/aebs/`
Related plan: `.hermes/plans/2026-08-30_143728-aebs-human-centered-linkedin-visualization.md`

## 1. Purpose

This contract freezes what every visual element in the AEBS center-display
app means, where its value comes from, and what it does **not** claim. It is
written to prevent the failure mode observed in the v2 video review: viewers
reasonably interpreted overlapping circles as physical thresholds and
causal triggers. Every element below must be implementable, testable, and
explainable in one sentence to a non-engineer.

## 2. Authority and read-only boundary

- The AAOS app is **System 2 instrumentation**. It derives no AEBS decision,
  publishes nothing, and issues no command (REQ-AEBS-S2-005).
- The presentation disposition is decided **only** by
  `VisualizationStateReducer` from accepted `VisualizationFrame` facts.
- Display geometry (positions, boundaries, trails) never feeds the reducer.
  No visual intersection, contact, or overlap can trigger or influence state.
- The wire contract (`interface/aebs_visualization.proto`) and the SysML item
  definitions remain the semantic authority. This contract adds **no** new
  fields and **no** new decision semantics. It is presentation-only.

## 3. Element contract

| # | Visual element | Source (frame field) | Provenance | Rendering rule | State authority | Non-claim |
|---|---|---|---|---|---|---|
| 1 | Ego origin marker | none (display coordinate origin) | display | fixed at bottom center of the forward view; small blue dot | none | not a rendered vehicle body; not vehicle pose |
| 2 | Closest obstacle point | `target_range` (m), `target_bearing` (rad) | `displayDerived` (projected from the native filtered obstacle point cloud) | orange dot, position = bounded top-down projection; hidden when fields absent or `> MAX_RANGE_M` (60 m) | none | not target classification; not perception accuracy; not "the vehicle" |
| 3 | Obstacle history trail | prior accepted `target_range`/`target_bearing` values | `displayDerived` | ≤ 12 small faded dots, oldest first; cleared on degraded disposition | none | not object trajectory prediction |
| 4 | RSS boundary | `rss_distance` (m) | `nativeAutowareAEB` | one horizontal line across the forward view at the shared range scale; labeled `RSS distance` | none | does not trigger intervention; not a safety envelope of the vehicle |
| 5 | Distance ticks | display scale only | display | subdued marks every 10 m up to 60 m | none | not sensor range/FOV |
| 6 | State progression panel | `VisualizationStateReducer.Disposition` | derived | `MONITORING → WARNING → INTERVENTION → RELEASED`; active state gets color **and** icon **and** text; inactive states subdued | reducer exclusively | no geometry input; no display-derived decision |
| 7 | Metric cards | latest `target_range`, `rss_distance`, frame age | mixed per field | exact numeric text; `—` when absent; cleared on degraded dispositions | none | not averages/smoothed/interpolated values |
| 8 | Data-health chip | frame receipt age; subscriber state | display | small chip in header (`● LIVE · 10 Hz · age N ms`); opacity pulse allowed; **must not** enter scene geometry | watchdog/reducer fail-closed states | not risk; not heartbeat of any physical system |
| 9 | Provenance ribbon | static text | display | two lines at bottom (see §6) | none | the ribbon itself makes no safety claim |

**Removed by this contract** (was in v1/v2, must not return):
- rotating radar sweep (wrong sensor metaphor: source is an obstacle-segmentation
  pointcloud, not a scanning antenna);
- expanding frame-arrival pulse ring inside the scene (conflated with the RSS
  envelope; radius depended on draw scheduling);
- concentric RSS envelope circle (circle geometry implied a safety zone around
  the vehicle; replaced by the labeled boundary line);
- renderer rule `rss_distance < 15 m → red` (a display threshold that competed
  with the reducer's intervention transition);
- radar terminology in user-facing strings.

## 4. State-to-color mapping (single authority: the reducer)

| Disposition | Color | Icon/shape | Text |
|---|---|---|---|
| `MONITORING` | blue `rgb(0,102,204)` | outline eye | `monitoring` |
| `WARNING` | orange `rgb(255,165,0)` | outline triangle-! | `warning` |
| `INTERVENTION` | red `rgb(204,0,0)` | filled octagon | `intervention` |
| `RELEASED` | green `rgb(0,153,51)` | check mark | `released` |
| `STALE` | gray | pause bars | `stale` (health overlay) |
| `INVALID` | gray | x-cross | `invalid` (health overlay) |
| `UNAVAILABLE` | gray | empty circle | `unavailable` (health overlay) |
| `RESTORED` | green (transient) | reconnection arrows | `restored` (transient health overlay) |

Rules:

- Color is never the only cue; icon + text always accompany it.
- `STALE`/`INVALID`/`UNAVAILABLE`/`RESTORED` are **health overlays**, shown in
  the health chip and by graying the scene; they are not AEBS operational
  states and must not appear in the four-stage progression panel.
- The progression panel highlights exactly one stage, taken from the reducer
  disposition via the mapping in §4 of the plan (lifecycle/intervention/
  braking/warning precedence unchanged).

## 5. Geometry rules

Display scale: `MAX_RANGE_M = 60.0` (display bound, not a data bound).

```
normalized(r)  = clamp(r / 60, 0, 1)
forward_y(r)   = origin_y − normalized(r) × usable_height
lateral_x(r,θ) = origin_x + sin(θ) × normalized(r) × usable_half_width
rss_y(d)       = origin_y − normalized(d) × usable_height
```

- Bearing convention: CCW-positive from +x (base_link), matching the bridge
  projection; screen up = forward, so screen angle = −θ.
- Target dot hidden when `target_range` is null or `> 60 m` (same rule as the
  current renderer; unchanged behavior).
- RSS boundary hidden when `rss_distance` is null.
- All geometry updates are stepwise from accepted frames. **No interpolation,
  no smoothing, no prediction** of target or RSS positions.
- Degraded dispositions (`stale`/`invalid`/`unavailable`) clear items 2, 3, 4
  immediately (fail closed), per the existing `radarView.clear()` pathway,
  renamed to the new view.

## 6. Provenance ribbon (exact text)

```text
SIMULATED POINT CLOUD → AUTOWARE AEB → ROS BRIDGE → SDV GATEWAY → AAOS
Read-only engineering visualization · issues no vehicle commands
```

- Both lines must remain readable at 1080×600 and at LinkedIn feed width.
- "SIMULATED" must remain visible in every public frame.
- No physical LiDAR/camera detection-performance claim, no radar claim, no
  certification/compliance implication, no statement that the app is a safety
  authority.

## 7. Acceptance checks (map to plan §5 Definition of Done)

1. No concentric pulse, sweep, or radar terminology in the human-facing UI.
2. Target, RSS boundary, state, and liveness occupy distinct visual regions.
3. Orange marker labeled "closest obstacle point" (on-screen or in the
   metric card header).
4. Warning cannot render as red intervention; envelope color cannot diverge
   from reducer state.
5. Geometry cannot trigger or influence the reducer (enforced by code review
   + pure tests: render model takes disposition as input, never outputs it).
6. Missing/stale/invalid/unavailable clears target, trail, and RSS geometry.
7. Exact numeric target range and RSS distance visible.
8. Simulated-pointcloud boundary visible in every public frame.
9. Color is not the sole state cue.
10. No unsupported object classification, sensor FOV, lane, or vehicle geometry.

## 8. Evidence and disposition

- Local layout previews: `EXPLORATORY — NOT RUNTIME EVIDENCE`; synthetic
  fixtures only; never mirrored model files.
- Final screenshots and video: real AAOS Cuttlefish center display only.
- Retained per public evidence: raw recording + edited cut + correlated
  app/ingress/bridge logs + segment disposition YAML (`observed_bounded` /
  `deferred_not_proven` / `not_claimed`).
- The visualization remains System 2 instrumentation; no product feature is
  added to any Bill-of-Features.
