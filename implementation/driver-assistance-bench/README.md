# Driver-assistance bench (INC-DRIVING-002)

Status: under construction, not yet validated. Eleven sessions have started bench hosts; `session/README.md` lists them
all. The results of these four stand, each at the bench commit named:

- p10-3 run 2 (SID 20261119T130414Z, 2026-11-19, `410293bb`): 21 of 21 test requests received on the IVI guest,
  conditional on a permissive IVI.
- p10-1 try 4 (SID 20261119T160111Z, 2026-11-19, `eae0a6ef`): C1 to C4, C6 and C7 met; C5 and C8 not run by design.
- p10-2 attempt 3 (SID 20261120T092051Z, 2026-11-20, `39a964a2`): both SC-DRIVING-012@20 runs judged; a fail of the
  pinned candidate.
- The judged session S1 (SID 20261121T014447Z, 2026-11-21, `508649ba`): the 14 runs of SC-DRIVING-012 to SC-DRIVING-015
  (10 of them meet their entry conditions) and the stop run, exit 0. VC-DRIVING-036, -037 and -042 fail. VC-DRIVING-039
  passes by a desk analysis of the realization. VC-DRIVING-038, -040, -041, -043 and -044 are inconclusive, although
  the warm start of D-S1-1 ran in all 16 runs, the steering calibration run among them (2 passes, 678.3 to 706.8 ms):
  each of the 14 runs drops 23 or 24 camera images in its first 5 s and 0 to 2 isolated images later. The stop run
  drops 24 in its first 5 s and then 8 in a row right after the stop instant (sim 2870.36 to 2871.06 s): the interface
  keeps receiving images and drops them, because the candidate that takes them is stopped.

A fail is a fail of the pinned candidate on this bench in simulation. No outcome is a compliance claim. The evidence
records and the case statuses come in the phase 10 evidence pull request.

INC-DRIVING-002 judges VisionPilot at `014e0e7a56ee8e597c2cab8175233f74edd9b856` on the Eclipse S-CORE path. The
bench has three hosts:

- the simulator host, which runs CARLA 1.0 at a fixed step of 0.05 s;
- the S-CORE host, which runs the candidate, the identity recorder, the actuation adapter, gatewayd and someipd;
- the guest host, which runs the AAOS SDV guests that present the warning.

The SysML model is the authority for what this bench implements, in particular the phase 8 realization
`textual-notation-of-model/packages/features/driving/driver_assistance_physical_software_realization.sysml` and the
phase 10 verification cases. The guide is `docs/guides/driver-assistance-increment.md`.

| Folder | Content |
|---|---|
| `interfaces/` | The interface control document, its machine-readable ids (`service_ids.json`) and the payload header that the components share |
| `score-interface/` | The VisionPilot patch series: the visualization recorder and the DE4SDV S-CORE interface module |
| `score-path/config/` | The S-CORE host's configs of the warning request: gatewayd, someipd and their mw::com manifests |
| `score-path/scripts/` | The S-CORE host's session entries: stage the bundle, start the Launch Manager as root and wait for its readiness, stop it with SIGTERM and collect every log; the path-only configuration without the candidate |
| `identity-recorder/` | The identity recorder (B4): hashes every input of the candidate, writes the candidate record into the run folder, offers it on event 7413 to late subscribers and reports running; the late-subscriber probe of p10-1 |
| `ivi-warning/` | The warning request on the guests: the Data Tunnel message, the SOME/IP mapping, the ACLs and the SDV Core staging |
| `ivi-warning/injector/` | The p10-3 test publisher of the warning request (event 7412): a sequence of true and false edges with issue times, each send logged with the S-CORE host's real and monotonic clocks; evidence of the path, not of the candidate |
| `launch-manager/` | The S-CORE host's Launch Manager configuration: the start order, the alive supervision of the candidate's process and the adapter, and the recovery target without both |
| `actuation-adapter/` | The actuation end of the S-CORE path: rejects a lost, repeated, corrupted or delayed driving command and applies an accepted one as CARLA's Ackermann control |
| `score-build/` | The S-CORE build of VisionPilot: the Bazel workspace, the build script, the GPU runtime of the S-CORE host and the fallback CMake route; the p10-1 check (`scripts/p10_1_check.sh`) |
| `ivi-warning-app/` | The warning presentation on the IVI guest (`CollisionWarningPresentationApplication`): the app that shows the warning on the display and starts the sound, with its timestamp record |
| `guest-build/` | The incremental guest build on the guest host: adds the SDV Core side of the warning request and the IVI app to the kept AAOS SDV images, installs and verifies them, stops the guests |
| `world-side/` | The simulator host's world side on CARLA 1.0: SC-DRIVING-012 with its entry-condition checks and setting records, the ASM-DRIVING-005/006 calibrations, the camera calibration file and the session entries (`scripts/`) |
| `session/` | The bench session orchestrator: starts the simulator, S-CORE and guest hosts in order, runs each host's steps, stops everything it started, against a cost cap |
| `recording/` | The chase-view recorder, the IVI display capture with its clock, and the side-by-side composition of the two captures |
| `case-evaluators/` | The evaluators of the S1 verification cases: they read one fetched S1 session and give VC-DRIVING-036 to -038 and -040 to -044 their outcomes and each run its evidence record; the contract of the records they read (`OBSERVABLES.md`) |
