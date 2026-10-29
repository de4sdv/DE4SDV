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
  provision_ivi_relay.sh      exactly one ACL, the relay binary and init, port 4731, reboot
  set_ivi_clock.sh       auto_time off, SNTP set and slew, capture the exchange (ASM-MW-030)
  recover_core_vm.sh     death detection and the in-place reboot recovery (GAP-MW-048)
  record_full_chain.sh   the public recording harness (terminals + adb screenrecord)
  teardown.sh            undo everything and append to the change log
aosp-overlay/core/       the SDV Core image overlay (frame type, mapping, stack config, broker ACL)
aosp-overlay/ivi-acl/    the relay's one subscriber ACL (its path encodes the subject)
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
5. The running cases: capture the host `:4721` stream and the guest `:4731`
   stream, the relay logcat and the clock exchanges, then evaluate off the VM.
6. `recover_core_vm.sh` for the GAP-MW-048 case; `teardown.sh` at the end.

## Evaluators

Each evaluator reads a run directory of raw artifacts and returns an outcome of
the middleware evidence vocabulary (passBoundedVerification, failObservedBehavior,
inconclusiveMissingEvidence, blockedTargetRuntime, errorEvidence), mapped to a
verdict as INC-MW-010 maps it. It reads the independent captures, not the
relay's or the ingress's own logs; it reads the relay log only to corroborate.
It never opens a socket and never runs on the VM.

```bash
python -m de4sdv_broker_path_bench.run <run-dir>            # every supported case
python -m de4sdv_broker_path_bench.run <run-dir> --case VC-MW-015
```

| Case | Requirement | What the evaluator checks from raw artifacts |
|---|---|---|
| VC-MW-015 | REQ-MW-014 | every produced frame reaches the HMI, in order, no gap, inter-arrival below 500 ms; a relay phase end during the event is a delivery failure |
| VC-MW-016 | REQ-MW-015 | each received frame equals its produced frame, byte for byte, with its source kind; no coordinator or display-derived field marked native |
| VC-MW-017 | REQ-MW-016 (2nd finding) | no isolated host port is reachable from a guest, confirmed against a positive control |
| VC-MW-020 | REQ-MW-019 | after a new subscription, no frame produced more than the 20 ms margin before it arrives; needs ASM-MW-030 to hold in the run |

The run directory holds, by convention: `produced.pcap` (host `:4721`),
`received.pcap` (guest `:4731`), `relay-logcat.txt`, `clock-start.pcap`,
`clock-end.pcap`, `settings.json`, and the probe JSON for VC-MW-017. See
[`config/run-settings.example.json`](config/run-settings.example.json).

The inspection cases VC-MW-018 and VC-MW-021 need no run; they read the
configurations and the wiring the execution slices author. The verification
cases themselves are the verification-case slice (branch `model/score-phase-10-broker-path`).

## Interfaces this bench needs from the other lanes

- **The relay lane** (the IVI frame relay, in the receiver branch): the relay
  binary name (set `RELAY_BIN`), its init file (`RELAY_RC`), its liblog tag
  (the `relay_logcat_tag` setting), its authz subject package and bundle
  (`RELAY_SUBJECT_PACKAGE`, `RELAY_SUBJECT_BUNDLE`), and its loopback server on
  `127.0.0.1:4731`, one client. The bench keeps the relay's service name out
  of its own committed non-Markdown files so the model guard does not bind to
  it here.
- **The verification-case slice** (branch `model/score-phase-10-broker-path`): VC-MW-015, VC-MW-016, VC-MW-017 and
  VC-MW-020 keep their observation point at the IVI loopback and name the
  relay's discard rule. This bench realizes their running side.

## Recording (owner approved; posting needs a separate approval)

`record_full_chain.sh` records real operator terminals (`script --log-timing`)
and the real IVI HMI display (`adb screenrecord`), started only after MONITORING
shows. Panes: the host stack and gatewayd/someipd, the SDV Core broker logcat,
and the relay log. No rendered or stylized footage. An edited cut is labeled
`publication_cut`; the raw files stay with the evidence.
