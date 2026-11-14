# Eclipse SDV landscape — what we use, and what we looked at and did not

Every project on `eclipsesdv.org/projects` (37 as of 2026-11-14), with a verdict. The
point of writing the skips down is that they stop being re-litigated.

## Worth taking next

| Project | Why it matters here |
|---|---|
| **[OpenSOVD](https://github.com/eclipse-opensovd/opensovd)** — ISO 17978 SOVD | Our entire diagnostic story is UDS over DoCAN: one session, one ECU. SOVD is the service-oriented replacement for that at vehicle level, and `classic-diagnostic-adapter` is explicitly the bridge that exposes existing UDS ECUs through it. Active: `opensovd` 48★ (pushed 2026-11-11), `opensovd-core` 22★, `classic-diagnostic-adapter` 30★ (pushed 2026-11-14). |
| **[OpenXilEnv](https://github.com/eclipse-openxilenv/openxilenv)** — SIL/HIL environment | Our plants are ~30-line Python state machines. OpenXilEnv runs embedded software functions on a PC without a target or compiler, against a configured plant — the honest upgrade from "toy plant" to "ECU code against a simulated environment". Active: 23★, pushed 2026-11-13. |

Both Apache-2.0. Neither is a dependency today.

## Track (no action now, but they are the right answer to a question we will ask)

| Project | The question it answers | Note |
|---|---|---|
| [BlueChi](https://github.com/eclipse-bluechi/bluechi) | Deterministic multi-node service control (systemd/D-Bus) for regulated ecosystems | 161★, v1.2.2 Regular status, **LGPL-2.1** (a licence consideration), last push 2026-08-25 |
| [openDuT](https://github.com/eclipse-opendut/opendut) | Automating test/validation across distributed benches | Apache-2.0, 51★, pushed 2026-11-13 — relevant to the two-host CARLA bench |
| [ThreadX](https://projects.eclipse.org/projects/iot.threadx) | A real RTOS target for OpenBSW instead of POSIX | needs QEMU/hardware |
| [Leda](https://github.com/eclipse-leda/leda) / [Leda Incubator](https://projects.eclipse.org/projects/automotive.leda.ledaincubator) | An in-vehicle OS image with the SDV stack preinstalled | Apache-2.0, last push 2026-10-12 |
| [Automotive Integration for AutoSD](https://projects.eclipse.org/projects/automotive.autosd) | An AutoSD image to run and test SDV projects | the step after Leda |
| [uProtocol](https://projects.eclipse.org/projects/automotive.uprotocol) | Transport-agnostic messaging across vehicle/cloud | the multi-transport gap the MQTT bridge exposed |
| [Chariott](https://projects.eclipse.org/projects/automotive.chariott) | Metadata-driven service discovery for in-vehicle apps | app-facing, not our bus path |
| [Heimlig](https://projects.eclipse.org/projects/automotive.heimlig) | HSM firmware (Rust) for key storage and crypto | what a real ECU needs for secure boot |
| [Pullpiri](https://projects.eclipse.org/projects/automotive.pullpiri) | K8s-model in-vehicle orchestration | third orchestrator option, no release |
| [Muto](https://projects.eclipse.org/projects/automotive.muto) | Runtime for dynamically composable ROS stacks | relevant to Autoware, not to this testbed |
| [Zenoh](https://projects.eclipse.org/projects/iot.zenoh) | Pub/sub transport with low overhead | used by the blueprint's fleet stack, not by us |

## In use, or already decided

| Project | Status |
|---|---|
| [Kuksa](https://projects.eclipse.org/projects/automotive.kuksa) | In use — the signal plane's broker (0.7.1) |
| [OpenBSW](https://projects.eclipse.org/projects/automotive.openbsw) | In use — the reference ECU in a zone |
| [S-CORE](https://projects.eclipse.org/projects/automotive.score) | In use elsewhere in DE4SDV, not in this testbed |
| [Trustable Software Framework](https://projects.eclipse.org/projects/technology.tsf) | In use elsewhere in DE4SDV |
| [SDV Blueprints](https://projects.eclipse.org/projects/automotive.sdv-blueprints) | Reference: `e2e-vehicle-signals` was reviewed for this testbed |
| [Ankaios](https://projects.eclipse.org/projects/automotive.ankaios) | Evaluated in a spike — [`orchestration/README.md`](orchestration/README.md). Its restart policy is the one idea worth borrowing. |

## Skip, with the reason

| Project | Why not |
|---|---|
| ArchE | Architecture modelling tool; SysML v2 is the modelling authority here, and a second modelling environment would fork it |
| Automotive API Framework | API layer between apps and BSW — a layer above what this testbed models |
| Open Vehicle API | Vehicle abstraction API that overlaps what Kuksa already does for us |
| Velocitas | Vehicle-app SDK; we write plants, gateways and contracts, not vehicle apps |
| eCAL, iceoryx, p3com | Same-host pub/sub and shared-memory IPC; our path is CAN + VSS over a network |
| CANought | Automotive extensions to Kanto, aimed at edge/cloud device management |
| Symphony | Cloud IoT orchestration — fleet backend territory we have not entered |
| Autowrx | digital.auto authoring platform — a playground, not a component |
| Ambient Light Services | A lighting-concept showcase |
| LMOS | Language-model OS — unrelated to the E/E problem |
| Ibeji | In-vehicle digital twin, but **stale: last push 2024-07-15** (MIT, 11★). Reviewed and set aside on evidence, not taste |
| SDV Developer Console, Hephaestus | Tooling for contributing to SDV projects; nothing to run here |
| SDV Landscape, SDV-LVL | Maps and maturity levels — useful reading, not software |

## What this changes

Two candidates are worth real work (**OpenSOVD**, **OpenXilEnv**), and both fill gaps this
page has been honest about: diagnostics that stop at UDS, and a plant model that is a toy.
Nothing else on the list is a better answer to a question this testbed is currently asking.
