# INC-AEBS-010 video evidence disposition index

Classifies every retained video in `evidence/010/` for publication vs
forensic/non-publication use. Statuses follow the evidence vocabulary of
VISUALIZATION-CONTRACT.md §8 (`observed_bounded` / `deferred_not_proven` /
`not_claimed`) plus the disposition labels `publication_cut` and
`forensic_only`.

## Authoritative publication evidence

| Artifact | Path (under evidence/010/) | Disposition | Role |
|---|---|---|---|
| Final publication cut | `forward-ui/final-hmi-v21-corrected/final-cut-v2.mp4` | `publication_cut` — 26.1 s: 3 s editing title card, 20 s untouched real-time take (0–20 s of the raw below), 3 s editing end card | The only video cleared for public/LinkedIn publication |
| Continuous raw runtime recording | `forward-ui/final-hmi-v21-corrected/raw-continuous.mp4` | `observed_bounded` — 70.15 s, 1080×600, untrimmed single take of the corrected final UI generation | Authoritative runtime source; the cut's middle section is bytes of this take, unmodified in content |
| Per-state stills | `forward-ui/final-hmi-v21-corrected/state-{monitoring,warning,intervention,released}.png` | `observed_bounded` — extracted from the same raw take at verified state boundaries | Correlated frame-level evidence |
| Correlated logs + disposition | `forward-ui/final-hmi-v21-corrected/` (`segment.yaml`, `revision-checksums.md`, `app-ingress-frame.log`, `observer.log`, `observer-raw.json`, capture timestamps, guest logcat, bridge/bench journal slices) | `observed_bounded` with `scenario_safety_outcome: deferred_not_proven` | Provenance and chain correlation for the cut above. Note: the host-side `bridge.log`/`bench.log` journal slices in this directory are 0-byte (the journal filter matched nothing on this run); the load-bearing correlation evidence is `app-ingress-frame.log` + `observer-raw.json` + guest logcat. They are retained empty for directory-completeness of the bundle. |
| Editing card assets | `forward-ui/final-hmi-v21-corrected/card-title-v2.mp4`, `card-end-v2.mp4` | `publication_cut` component — 3 s editing frames only, not app output | Composited into `final-cut-v2.mp4`; never evidence of runtime behavior |

## Forensic / non-publication evidence (obsolete or superseded HMI semantics)

These recordings show UI generations whose HMI semantics were later
corrected — earlier generations rendered `target_range`/`rss_distance`-derived
elements (distance pill, RSS reference line, closest-point labeling) that the
final corrected contract (VISUALIZATION-CONTRACT.md §3, "Removed by this
contract") explicitly retired because the display-derived cloud-point range
and the native Autoware path-longitudinal RSS quantity are not an aligned
decision pair. They are retained for the correction trail only. They must not
be published, embedded in docs or posts, or cited as current HMI evidence.

| Artifact | Path (under evidence/010/) | HMI generation | Obsolete/misleading semantics | Disposition |
|---|---|---|---|---|
| v1 raw + cut | `video/raw-recording-full.mp4`, `video/inc-aebs-010-live-visualization.mp4`, disposition `video/video-segment.yaml` | v1 scene | rotating radar sweep (wrong sensor metaphor for a point-cloud source) | `forensic_only` |
| v2 raw + cut | `video/raw-recording-v2-no-sweep.mp4`, `video/inc-aebs-010-live-visualization-v2-no-sweep.mp4`, disposition `video/video-segment-v2.yaml` | v2 scene | radar-sweep removed but distance pill/RSS-line rendering still present | `forensic_only` |
| Early forward-UI live takes | `forward-ui/live-v8-braking-to-released.mp4`, `forward-ui/live-v9-full-arc.mp4`, disposition `forward-ui/live-v9-segment.yaml` | early professional-UI iterations | mixed generations; v12-era ego-speed gap documented in disposition | `forensic_only` |
| v17/v19 professional takes + cut | `forward-ui/live-v17-pro-ui.mp4`, `forward-ui/live-v19-pro-ui.mp4`, `forward-ui/linkedin-cut-pro.mp4`, `forward-ui/linkedin-cut-v3.mp4`, disposition `forward-ui/pro-ui-segment.yaml` | pre-correction professional UI | rendered `target_range`/RSS threshold pair later removed as unaligned; the v17/v19 takes additionally had fixture-injection timing limitations (monitoring phase off-camera) recorded in the superseded revision of `pro-ui-segment.yaml` | `forensic_only` |
| v20 final-HMI take | `forward-ui/final-hmi-v20/live-v20-final-hmi-continuous.mp4` + its logs/stills | final-HMI generation, pre-semantic-correction | displayed the `Target range` / `AEB braking threshold` pair removed by the corrected revision (see `revision-checksums.md`) | `forensic_only` |

## Hard boundary

- The raw take and per-state stills in `final-hmi-v21-corrected/` are the only
  runtime pixels of the corrected final UI generation; no other directory
  carries publication-clearance.
- The title/end cards inside `final-cut-v2.mp4` are editing frames, not app
  output. The 20 s middle is untouched guest capture.
- Obsolete videos are never deleted silently: they are the audit trail of
  what was corrected and why (see VISUALIZATION-CONTRACT.md §3 removed list).
