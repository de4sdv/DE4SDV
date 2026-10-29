# DE4SDV AAOS SDV broker-path bench (INC-MW-011 phase 10)

This bench runs and evaluates the HMI frame path of the Eclipse S-CORE member
(MW-CONFIG-002) over the AAOS SDV broker path (ADR 0025). SOME/IP ends in an
SDV Core VM; the broker maps the frame event to a Data Tunnel topic; the IVI
frame relay in the IVI VM serves the reused INC-AEBS-010 ingress. The bench
holds the VM scripts, the public recording harness and the pure evaluators of
the running verification cases.

## Claim boundary

This directory is bench tooling and evaluators. It is **not** evidence of
record, it verifies no requirement by itself, and every result stays draft
until independent review. No safety, cybersecurity, compliance, certification
or homologation statement is made. The HMI is an informational display, not
the AEBS driver warning, and makes no UN R152 claim. The bench runs on the
System 2 VM (GAP-MW-044); nothing here starts, stops or reboots the VM, and
nothing dispatches a workflow. In the UNLOCKED boot mode of the bench the SD
mesh and Data Tunnel run as cleartext HTTP/2 (no channel authentication).

## Path (one direction, always)

```text
vehicle-speed provider (S-CORE) --> AutowareToSCORE adapter (host)
AEBS stack + 009D coordinator (host, ROS 2) --> frame assembler :4721 (host)
    --> adapter --> S-CORE mw::com --> gatewayd --> someipd (host)
    --> SOME/IP over the KVM guest network --> SDV Core VM stack + SOME/IP broker
    --> Data Tunnel --> SDV Gateway on IVI (IVI VM)
    --> IVI frame relay :4731 (IVI VM loopback) --> INC-AEBS-010 ingress --> HMI app
```

The relay holds the REQ-MW-019 discard rule. The host half (adapter, gatewayd,
someipd) is the S-CORE reference interop bench next door
([`../score-reference-interop-bench`](../score-reference-interop-bench/README.md)).

## Layout

```text
scripts/                 VM scripts, each idempotent and with an undo
  bench_env.sh           shared settings (addresses, ports, names, the DDS port set)
  build_sdv_core_image.sh  stage the mapping and stack config, clean recorded build, revert
  launch_two_vms.sh      core (instance 1) + IVI (instance 2), UNLOCKED, reboot-in-place
  host_sd_multicast_route.sh  the SD group route on cvd-ebr (GAP-MW-047)
  host_isolation_firewall.sh  the owner-approved rules (GAP-MW-046) + remove
  host_isolation_probe.sh     the reachability check of REQ-MW-016, records for the evaluator
  provision_ivi_relay.sh      one ACL per subject + the broker object policy, relay binary and init, reboot
  set_ivi_clock.sh       chrony allow, auto_time off, SNTP set and slew, capture the exchange (ASM-MW-030)
  capture_case.sh        produce the case artifacts: the :4721 and :4731 streams, the relay log, the ss check, the clocks
  recover_core_vm.sh     death detection (a VmHealth subscriber) and the in-place reboot recovery (GAP-MW-048)
  record_full_chain.sh   the public recording harness (terminals + adb screenrecord)
  teardown.sh            undo everything and write a run-dir session log
aosp-overlay/core/       the SDV Core image overlay (frame type, mapping, stack config, broker ACL)
aosp-overlay/ivi-acl/    the relay's subscriber ACL and the broker's object policy
config/run-settings.example.json   the settings the evaluators read
src/de4sdv_broker_path_bench/       pure evaluators (read the raw artifacts off the VM)
tests/                   the evaluator unit tests (CI, with synthetic captures)
VM-CHANGE-LOG.md         what each script changes on the VM and how to undo it
bench-plan.md            the session plan (S1 to S3), VM-hours and cost
```

## Order on the VM (riskiest first)

1. `build_sdv_core_image.sh build` — the SDV Core image with the mapping and the
   stack configuration, clean and recorded. The spike's images are not reused.
2. `host_sd_multicast_route.sh add`, then `launch_two_vms.sh up`.
3. `provision_ivi_relay.sh install`, then `set_ivi_clock.sh setup` and `drift`.
4. `host_isolation_firewall.sh add`, then `host_isolation_probe.sh run <dir>`.
5. The running cases: `capture_case.sh start <dir>`, verify MONITORING, run the
   009D AEBS event, `capture_case.sh stop <dir>`, then evaluate off the VM. It
   produces the host `:4721` stream, the guest `:4731` stream, the relay log,
   the `ss` client check and the clock exchanges.
6. `recover_core_vm.sh` for the GAP-MW-048 case; `teardown.sh` at the end.

## Evaluators

Each evaluator reads a run directory of raw artifacts and returns an outcome of
the middleware evidence vocabulary (passBoundedVerification, failObservedBehavior,
inconclusiveMissingEvidence, blockedTargetRuntime, errorEvidence), mapped to a
verdict as INC-MW-010 maps it. The independent captures are authoritative; the
relay's log is the record of its subscription phases, which the captures
corroborate (a layer-caused phase end in the event is a delivery failure of
the layer, so the relay log can fail the case). It compares raw clock readings,
with no offset correction, as the phase-8 rule and the verification case do.
Precedence follows #448: only a failure whose evidence does not depend on an
inconclusive condition dominates, so a capture gap or a failed clock bound
turns a completeness failure into missing evidence, not a fail. It never opens
a socket and never runs on the VM. It evaluates one condition (one run) at a
time; a case pass needs every condition the case names.

```bash
python -m de4sdv_broker_path_bench.run <run-dir>            # every supported case
python -m de4sdv_broker_path_bench.run <run-dir> --case VC-MW-015
```

| Case | Requirement | What the evaluator checks from raw artifacts |
|---|---|---|
| VC-MW-015 | REQ-MW-014 | every frame produced while the HMI was subscribed reaches it, in order, inter-arrival below 500 ms; a layer-caused phase end or a DATA_LOSS in the event fails; an ingress disconnect, a second `:4721` client, or ASM-MW-030 not holding is inconclusive |
| VC-MW-016 | REQ-MW-015 | each received frame equals its produced frame byte for byte, with its source kind; a received frame the stack never produced fails; frames must keep arriving after the SD offer, which must not redirect the provider |
| VC-MW-017 | REQ-MW-016 | second finding: no host DDS port of the layer is reachable from a guest (host-socket receipt, with a positive control and full coverage); a reachable `:4721` is an ASM-MW-029 finding, not a failure; the first finding needs the inspection record |
| VC-MW-020 | REQ-MW-019 | per condition (HMI down, IVI VM down, SDV Core VM down, pair restart): each frame in a new phase was produced no more than the 20 ms margin before the phase start, compared raw; needs ASM-MW-030 to hold |

The run directory holds, by convention: `produced.pcap` (host `:4721`),
`received.pcap` (guest `:4731`), `relay-logcat.txt` (the relay's events, with
its tag), `clock-start.pcap`, `clock-end.pcap`, `settings.json`,
`frame_assembler_clients.json` (the ASM-MW-029 `ss` check), and for VC-MW-016
`sd_offer.json` or `residual.json`, and for VC-MW-017 the probe JSON
(`host_listeners.json`, `probe_attempts.json`, `host_socket_receipts.json`,
`control.json`, `coverage.json`, `asm_mw_031.json`, `inspection.json`). The
run directory lives outside the repository (or under the git-ignored `run/`),
and each run records its identity (`core-image-identity.txt` and the manifest
of the capture commands). See
[`config/run-settings.example.json`](config/run-settings.example.json).

The inspection cases VC-MW-018 and VC-MW-021 need no run; they read the
configurations and the wiring the execution slices author. The verification
cases are pinned at #448 `5d14317c` (branch `model/score-phase-10-broker-path`).

## Interfaces this bench needs from the other lanes

- **The relay lane** (the IVI frame relay, branch `feat/score-someip-receiver`,
  #439 at `21882005`): these are required inputs with no defaults, and a script
  fails fast when any is unset.
  - binary `RELAY_BIN` = `/system/bin/de4sdv_ivi_frame_relay`;
  - init file `RELAY_RC` = `ivi-frame-relay/de4sdv_ivi_frame_relay.rc`;
  - liblog tag `RELAY_LOGCAT_TAG` = `de4sdv_ivi_frame_relay` (set
    `relay_logcat_tag` in the run settings to it);
  - authz subject `RELAY_SUBJECT_PACKAGE` = `de4sdv.ivi_frame_relay`,
    `RELAY_SUBJECT_BUNDLE` = `IviFrameRelay`, `RELAY_SUBJECT_INSTANCE` =
    `default`;
  - loopback server on `127.0.0.1:4731`, one client; it sets the ingress port
    and host from its own init file on boot.

  The binary, the init-service name and the tag are the model-guard marker, so
  this bench keeps them out of its committed non-Markdown files (they are
  required inputs, named here only). Once #439 is on main the scripts and the
  example settings may name them directly; until then the model guard binds to
  the relay's own header and `.rc`. An S1 preflight compares these values with
  #439's `.rc`.
- **The verification-case slice** (#448 `5d14317c`, branch
  `model/score-phase-10-broker-path`): VC-MW-015, VC-MW-016, VC-MW-017 and
  VC-MW-020 keep their observation point at the IVI loopback and name the
  relay's discard rule. This bench realizes their running side.

## Recording (owner approved; posting needs a separate approval)

`record_full_chain.sh` records real operator terminals (`script --log-timing`)
and the real IVI HMI display (`adb screenrecord`), started only after MONITORING
shows. Panes: the host stack and gatewayd/someipd, the SDV Core broker logcat,
and the relay log. No rendered or stylized footage. An edited cut is labeled
`publication_cut`; the raw files stay with the evidence.
