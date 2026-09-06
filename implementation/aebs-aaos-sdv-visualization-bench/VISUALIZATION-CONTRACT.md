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
- Display geometry never feeds the reducer.
  No visual intersection, contact, or overlap can trigger or influence state.
- The wire contract (`interface/aebs_visualization.proto`) and the SysML item
  definitions remain the semantic authority. This contract adds **no** new
  fields and **no** new decision semantics. It is presentation-only.

## 3. Element contract

| # | Visual element | Source (frame field) | Provenance | Rendering rule | State authority | Non-claim |
|---|---|---|---|---|---|---|
| 1 | Ego reference silhouette | pinned fixture dimensions at the display coordinate origin | display | fixed at bottom center and labeled `EGO`; visually emphasized but not used as a measurement scale | none | not live vehicle pose; not a production vehicle rendering |
| 2 | Filtered obstacle cluster | `target_points` | `displayDerived` | bounded cyan point projection in `base_link`; hidden when absent or degraded | none | no object classification, confidence, authoritative object distance, or physical extent claim |
| 3 | Retained distance telemetry | `target_range`, `target_bearing`, `rss_distance` | mixed per field | retained in the wire and evidence logs but not rendered in the public HMI | none | the display-derived cloud-point range and native RSS calculation are not an aligned decision pair and must not be presented as a comparable pair |
| 4 | Distance ticks | display scale only | display | subdued marks every 10 m up to 60 m | none | not sensor range/FOV and not the native AEB path-distance axis |
| 5 | State progression panel | `VisualizationStateReducer.Disposition` | derived | dominant current-state heading plus `MONITORING → WARNING → INTERVENTION → RELEASED`; active state gets color **and** icon **and** text; inactive states subdued | reducer exclusively | no geometry input; no display-derived decision |
| 6 | Engineering-status rows | `target_points` count, `ego_speed` | mixed per field | point count and speed; explicit `AEB decision distances not visualized` boundary; frame age is internal staleness logic only and is never rendered | none | no implied distance comparison or decision reconstruction |
| 7 | Data-health chip | frame receipt age (internal); subscriber state | display | small chip in header (`● LIVE · 10 Hz`); opacity pulse allowed; **must not** enter scene geometry; age value is never displayed | watchdog/reducer fail-closed states | not risk; not heartbeat of any physical system |
| 8 | Provenance ribbon | static text | display | two lines at bottom (see §6) | none | the ribbon itself makes no safety claim |

**Removed by this contract** (was in v1/v2, must not return):
- rotating radar sweep (wrong sensor metaphor: source is an obstacle-segmentation
  pointcloud, not a scanning antenna);
- expanding frame-arrival pulse ring inside the scene (conflated with the RSS
  envelope; radius depended on draw scheduling);
- concentric RSS envelope circle (circle geometry implied a safety zone around
  the vehicle; replaced by the labeled boundary line);
- renderer rule `rss_distance < 15 m → red` (a display threshold that competed
  with the reducer's intervention transition);
- closest-point distance pill and RSS reference line (the former was Euclidean
  range from `base_link` to one cloud point; the latter is compared by native
  Autoware against a different path-longitudinal front-clearance quantity);
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
normalized(r) = clamp(r / 60, 0, 1)
forward_y(x)  = origin_y − normalized(x) × usable_height
lateral_x(y)  = origin_x + y/(60/2) × usable_half_width
```

- Bearing convention: CCW-positive from +x (base_link), matching the bridge
  projection; screen up = forward, so screen angle = −θ.
- Cluster points use their filtered-cloud `base_link` forward/lateral
  coordinates. The bridge retains `target_range`/`target_bearing` for evidence
  compatibility, but the public HMI does not render those scalars.
- `rss_distance` remains native evidence telemetry. The public HMI does not
  render it as a line or numeric metric because the frame carries no atomically
  aligned native `ObjectData.distance_to_object` partner.
- All geometry updates are stepwise from accepted frames. **No interpolation,
  no smoothing, no prediction** of target or RSS positions.
- Degraded dispositions (`stale`/`invalid`/`unavailable`) clear live geometry
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
2. Filtered obstacle points, state, speed, and liveness occupy distinct visual regions.
3. Point geometry is identified as filtered obstacle points without a
   classification glyph or authoritative-distance label.
4. Warning cannot render as red intervention.
5. Geometry cannot trigger or influence the reducer (enforced by code review
   + pure tests: render model takes disposition as input, never outputs it).
6. Missing/stale/invalid/unavailable clears the cluster and live speed.
7. The public HMI renders neither `target_range` nor `rss_distance` and states
   that AEB decision distances are not visualized.
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

## 9. Model-sync audit (plan Task 8)

Confirmed 2026-08-30: the forward-situation redesign is presentation-only.
- No `VisualizationFrame` field added/removed; proto untouched.
- No `VisualizationPresentationMachine` or `VisualizationHealthKind`
  semantic change; the reducer remains the sole disposition authority.
- No new SysML requirements or architecture elements are needed: the
  render model consumes only existing frame fields and the existing
  disposition enumeration.
- Non-goal retained: no closing speed, TTC, lane geometry, FOV, target
  classification, or margin-to-intervention display fields.

## 10. Schema minor 1 — professional scene elements (2026-08-30)

SysML-first change (aebs_visualization_functional_architecture.sysml,
item defs AEBSVisualizationFrame + TargetPointProjection; proto schema_minor
0 -> 1). Display-presentational only; no new decision or state semantics:

| Element | Source | Rendering | Non-claim |
|---|---|---|---|
| Target cluster | downsampled filtered obstacle cloud (<=24 pts, `target_points`) | cyan point cluster with no classification glyph | not object classification; not a rendered car body |
| Ego car shape | scenario fixture footprint (3.74/1.03/1.83 m) | labeled rounded-rect reference silhouette, visually emphasized 2.5x for feed-size legibility | stylized fixture reference, not live pose or a vehicle model |
| Ego speed | Autoware kinematic state -> `ego_speed` | big glanceable km/h banner (HMI focal point) + metric row | display-presentational; speed of the bench ego only |


Fail-closed unchanged: degraded dispositions clear cluster, ego speed, and
all live geometry.

## 11. Distance-semantic audit (2026-08-31)

The pinned Autoware implementation does **not** compare `rss_distance` with
the bridge's `target_range`:

- `target_range` is `hypot(x, y)` to the closest finite positive-x point in
  the native filtered obstacle debug cloud. It is display-derived, Euclidean,
  and referenced to `base_link`.
- Native `ObjectData.distance_to_object` is the absolute path-signed arc
  length to the selected object point minus the ego longitudinal offset. For
  forward travel this is a path-longitudinal clearance from the ego front.
- Native `rss_distance` is response distance + ego braking distance + signed
  object braking contribution + longitudinal margin. Native collision logic
  compares `ObjectData.distance_to_object <= rss_distance`.
- The diagnostic `Distance` and `RSS` values are the native comparable pair,
  but they are collision-data diagnostics with retention behavior and are not
  carried as an aligned pair by schema 1.1.

Additional native semantics confirmed by the pinned-commit audit and relevant
to the observed RELEASED presentation:

- `~/debug/rss_distance` is published **only inside `hasCollision()`** and is
  a signed float32 (it can legitimately go negative for fast receding
  objects; the bridge clamps negatives to 0). It is not published when AEB is
  inactive, the ego is stationary, no candidate exists, or speed estimation
  fails — absence of messages is not "no object", and the last value lingers.
- Release on the bench is **purely temporal**: the native collision record is
  retained for `collision_keeping_sec` (3.0 s, measured from the object
  stamp) and the diagnostic flips to `OK "[AEB]: No Collision"` on expiry
  with no re-evaluation of distance or object presence. The DE4SDV
  coordinator additionally latches `braking_latched` until verified standstill
  and then reports `released_verified_stop`. A viewer can therefore observe
  RELEASED while the obstacle remains physically present — this is correct
  latched behaviour, not a distance contradiction, and displaying a distance
  pair during that window would still mislead.

The frame assembler samples the latest independently received cloud, RSS,
odometry, diagnostic, and coordinator values at 10 Hz. It preserves scalar
source timestamps but enforces no cross-field skew bound; target-point source
time is not carried in schema 1.1. Therefore `target_range` and `rss_distance`
must not be presented as a comparable pair. Both remain in the wire/evidence
record for traceability; neither appears as public decision-distance geometry
or text.

Corroborated by the end-to-end data audit of the final-hmi-v20 evidence: the
displayed `target_range` decayed 11.38 → 0.002 m while the ego re-accelerated
into the (still present) fixture target after RELEASED, with the sampled
`rss_distance` rising to 15.42 m — and `de4sdv_braking_request` held
`active=true` through seq 2731 under `released_verified_stop` because the
coordinator's sample-hold keeps the last braking sample while nominal control
is republished. Every displayed value was individually correct; the
presentation as a comparable pair was the defect, which this contract and the
public HMI now prohibit.

Forensic binding of the same evidence (observer monotonic clock ↔ app epoch
via offset 1788183800.963 s): native ERROR diagnostics span 5141.04–5143.04;
`braking_latched` 5141.04–5143.49; `released_verified_stop` from 5143.55; the
app's INTERVENTION display latched the native diagnostic within ~3 ms. All
443 post-release frames carried `braking=true` (sample-hold), 394/481
target-bearing frames held an unchanged range value across polls, and the
closest-point range reached 0.002 m at 6.94 m/s — the ego physically passed
the simulated fixture point, a display-geometry fact that is not an AEBS
decision and must not be rendered as one.

## 12. Display Safety positioning (2026-08-30)

This app is System 2 instrumentation rendered on the AAOS IVI partition by a
Java application. It is NOT a Display Safety artifact: production AEBS
driver warnings would render through the High Availability Renderer with
the safety-monitor toolchain on the safety-critical partition. The claim
boundary stays: read-only engineering visualization, no safety telltale,
no production readiness implied. Permissive-SELinux bench provisioning
remains diagnostic-only.

## 13. Presentation-scale and diagnostic-range contract (2026-09-01)

Follow-up to merged PR #164. After merge, the recorded HMI showed the cyan
obstacle cluster visually touching the ego silhouette during INTERVENTION
even though the fixture geometry never brings them into contact. Root cause:
the ego silhouette was drawn at 2.5x (plus a lateral 1.4x) its fixture
footprint while the obstacle cloud used the true scene scale, and the point
glow radius extended apparent contact beyond the projected points. Rules
below are binding and testable (`tests/test_aebs_010_hmi_presentation_contract.py`,
`SituationRenderModelTest`).

### 13.1 One scene scale

- All geometry sharing the metric scene — ego footprint, filtered obstacle
  points, range ticks — uses ONE consistent metre-per-pixel scale (one
  consistent metre-per-pixel scale across the whole scene), isotropic
  in both axes (`ForwardSituationView.sceneGeometry()`).
- The ego footprint is drawn at the TRUE fixture dimensions (front 3.74 m,
  rear 1.03 m, width 1.83 m) with no presentation-only enlargement relative
  to obstacle geometry. At 1080×600 the fixture-true silhouette is a few
  pixels wide; it is stylized (bright core plus a soft low-alpha emphasis
  halo whose radius never exceeds the footprint span) but its represented
  physical dimensions are never enlarged for readability.
- Visual overlap must never be introduced by unequal scaling: if ego and
  obstacle pixels touch, the underlying metric geometry — not the renderer —
  brought them there. Renderer-side overlap or contact carries no AEBS
  decision semantics; collision decisions remain System 1 output.

### 13.2 Point glow is decoration

- Cluster point rendering uses a small core (3.5 px) plus a subtler glow
  (6 px); both radii are constants in the view, smaller than the spacing of
  the projected geometry they decorate.
- The glow is visual decoration only and does not represent physical extent:
  point-rendering size is never usable as an object-size or contact measure.

### 13.3 EGO label placement

- The `EGO` label is drawn BELOW the ego silhouette with a fixed clearance
  (5 px) between the silhouette boundary and the glyphs, so anti-aliasing at
  1080×600 can no longer blend the text into the vehicle edge or the
  background. The footprint is never enlarged to fit the label.

### 13.4 Displayed obstacle range (diagnostic only)

- The engineering-status panel shows `Displayed obstacle range` — the
  closest finite forward point projected from Autoware's filtered obstacle
  point cloud (`target_range`, display-derived), in metres with one decimal
  (`13.4 m`), with the smaller clarification line `filtered point cloud`.
- It is a diagnostic echo of the displayed cloud geometry. It is NOT a
  native Autoware AEB decision distance (see §11: the native comparable pair
  is `ObjectData.distance_to_object` vs `rss_distance`, which schema 1.1
  does not carry as an aligned pair).
- It is never compared against `rss_distance`, never shown beside a
  braking/RSS threshold, and never feeds state or reducer logic.
- It clears on stale/invalid/unavailable with the rest of the live geometry
  (fail closed, same block as the scene clearing).
- The former `AEB decision distances not visualized` boundary row is
  removed: the HMI displays only available engineering information and does
  not add unavailable internal concepts. The distinction between the
  display-derived range and native decision semantics remains documented
  here and in the evidence record; native AEB decision metrics remain
  intentionally not shown in the HMI.

### 13.5 Semantic boundaries (unchanged)

- cyan geometry = display-derived filtered obstacle cloud;
- displayed obstacle range = closest projected point derived from that cloud;
- ego speed = Autoware kinematic state;
- AEBS state = authoritative reducer/coordinator input;
- native Autoware AEB/RSS decision distances are not reconstructed by the HMI;
- visualization remains read-only and issues no vehicle commands.

Still prohibited (§3 removed list stands): radar sweep, RSS reference
geometry, braking-threshold visualization, target-range/RSS comparison,
renderer-side thresholds, invented object classification, lane/FOV
geometry, collision semantics.
