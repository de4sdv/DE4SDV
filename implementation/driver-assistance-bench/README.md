# Driver-assistance bench (INC-DRIVING-002)

Status: under construction, not yet validated. Nothing in this folder has run on the bench yet.

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
| `ivi-warning/` | The warning request on the guests: the Data Tunnel message, the SOME/IP mapping, the ACLs and the SDV Core staging |
| `launch-manager/` | The S-CORE host's Launch Manager configuration: the start order, the alive supervision of the candidate's process and the adapter, and the recovery target without both |
| `actuation-adapter/` | The actuation end of the S-CORE path: rejects a lost, repeated, corrupted or delayed driving command and applies an accepted one as CARLA's Ackermann control |
| `score-build/` | The S-CORE build of VisionPilot: the Bazel workspace, the build script, the GPU runtime of the S-CORE host and the fallback CMake route |
| `world-side/` | The simulator host's world side on CARLA 1.0: SC-DRIVING-012 with its entry-condition checks and setting records, the ASM-DRIVING-005/006 calibrations and the camera calibration file |
