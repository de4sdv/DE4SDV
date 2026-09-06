# INC-AEBS-009D exact-head warning-lead campaign (PR #188, head 108bfa9)

Three independent runtime campaigns on the single-VM bench (Autoware 009D
scenario + coordinator + bridge + AAOS `sdv_ivi_cf` guest), staged from exact
Git head `108bfa9aa4aa63c4d3dc52fd56884db345b53357` (archive SHA-256
`fed9458c19a8729efbeee7e4830c7b9e779674e9500065e2f2ad3e61b956e905`),
executed 2026-09-06 on the DE4SDV bench VM. This supersedes the phase-1
multi-run report, which lacked deployed-source provenance and is retained only
as a historical report.

## Acceptance evidence per run

The authoritative gate is the observer `lifecycle_gate` block (collector
monotonic receipt timestamps), never video. WARNING presence in Gateway/app
frames is the secondary gate; the video is the tertiary illustration.

| Run | first warning (s) | first intervention (s) | lead (s) | gate (≥ 0.8 s) | app WARNING frames | frame gaps |
|-----|-------------------|------------------------|----------|----------------|--------------------|------------|
| 1   | 1740.999784413    | 1742.110054757         | 1.1103   | pass           | 39 (14 pre-braking) | 0          |
| 2   | 2720.462842340    | 2721.575145472         | 1.1123   | pass           | 39 (14 pre-braking) | 0          |
| 3   | 3501.110963614    | 3502.034806381         | 0.9238   | pass           | 36 (11 pre-braking) | 0          |

- Lead cluster 0.92–1.11 s across three independent runs; all above the 0.8 s
  contract minimum (`scenario-009d-moving-vehicle-target.yaml`
  `outcome_contract.warning_lead_min_s: 0.8`).
- Live AEB parameter verified per run from the running node:
  `use_object_velocity_calculation = False` (009D calibration active; the
  nondeterministic estimator is off).
- App frames: WARNING frames precede first braking frame in every run
  (run 1/2: warning seq 1534–1547, braking from 1548; run 3: warning
  1541–1551, braking from 1552), zero sequence gaps across the capture.
- Source-side truth: `warning_request` active samples observed per run
  (28 / 29 / 24); the warning was genuinely published upstream, not
  fabricated downstream.
- Recordings show the full lifecycle on camera: MONITORING (blue) →
  WARNING (orange) → INTERVENTION (red) → RELEASED (green), verified by
  per-state stills and pixel classification of the state panel.

## Known bounded non-pass (unchanged from phase 1)

All three runs fail `footprint_outcome` ("Required post-braking map-pose
footprint evidence not observed"): `footprint_state` samples stop ~3.2 s into
the run, before the gate command, while lifecycle/warning gates pass. This is
the documented separate collection issue; it does not affect the warning-lead
determinism claim of this campaign. Full-lifecycle `pass_observed_chain`
remains not claimed for 009D mode.

## Evidence separation boundary

The app in the guest image is the image-bundled generation (pre-PR #180
geometry). This campaign validates lifecycle/warning propagation through the
coordinator fix; it does not claim the corrected final HMI geometry, which
requires a combined-head run (#188 + #180). No safety, certification,
compliance, or homologation claim is made.

## Media disposition

Video bytes are not tracked in Git. The three continuous raw recordings are
held in the maintainer archive under
`2026-09-06/p188-exact-head-108bfa9/`; their checksums are recorded in
[`external-media.yaml`](../../../external-media.yaml). Per-state stills are
retained here as frame-level evidence.

## Per-run record contents

- `observer-raw.json` — independent observer raw record incl. `lifecycle_gate`
- `app-frame.log` — Gateway/app frame log (`onGatewayFrame` lines, epoch-stamped)
- `aeb_param_check.txt` — live `use_object_velocity_calculation` read
- `bench.log` — bench unit journal (launch arguments visible)
- `capture.log` — UTC capture start/observer activation/pull times
- `state-{monitoring,warning,intervention,released}.png` — identified state stills
