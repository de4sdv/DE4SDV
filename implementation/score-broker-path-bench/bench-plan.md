# INC-MW-011 phase 10: broker-path bench plan (path C, two VMs)

Status: **plan**. It rewrites the own-receiver plan for the AAOS SDV broker
path of ADR 0025. The guest is two VMs: the SDV Core VM, where SOME/IP ends in
the broker, and the IVI VM, where the frame relay serves the reused
INC-AEBS-010 ingress. Nothing here runs on the VM; the scripts of this bench
do, under the operator. No workflow is dispatched.

Author role: Systems Integration Engineer. Reviewers before execution:
de4sdv-vv (case procedures and pass logic), de4sdv-assurance (evidence form).
Decision authority: Orkun.

## Inputs (exact)

| Input | Identity |
|---|---|
| DE4SDV main | `1d36b55b` (phase 8 broker path, ADR 0025) |
| Phase 8 realization | `middleware_score_physical_software_realization.sysml` @ main, with the relay, GAP-MW-045 to GAP-MW-048 and the next action (steps 1 to 11) |
| Requirements | REQ-MW-014, REQ-MW-015, REQ-MW-016 (two findings), REQ-MW-019 @ main |
| Verification cases | the verification-case slice, branch `model/score-phase-10-broker-path` (VC-MW-015 to VC-MW-020 rebound to the broker path) |
| Host half | the S-CORE reference interop bench (`../score-reference-interop-bench`): the adapter, gatewayd, someipd, ASM-MW-021 pins |
| Relay | the receiver branch, re-scoped to the IVI frame relay (binary, init file, logcat tag, authz subject) |
| Spike facts | design data only (GAP-MW-038, GAP-MW-039, GAP-MW-047, GAP-MW-048); not evidence of record |
| System 2 VM | GAP-MW-044: `de4sdv-aaos-build`, n2-standard-16, europe-west4, nested virtualization, from the snapshot of 2026-10-14 |

## The three systems

- **Linux host.** The S-CORE host half and the Autoware-based AEBS stack with
  the 009D event. The adapter, gatewayd and someipd run under the Launch
  Manager in the one ROS 2 environment of adapterAbortConditions. The frame
  assembler serves `:4721`. This is the reference interop bench next door; its
  CI covers the speed-path cases.
- **SDV Core VM** (cvd instance 1, headless). The SOME/IP stack and the broker,
  started by `ro.boot.sdv.someip.enable=true`. The DE4SDV mapping and stack
  configuration are built into the image. The broker publishes the frame topic
  on Data Tunnel.
- **IVI VM** (cvd instance 2, display). The SDV Gateway on IVI, the IVI frame
  relay (`:4731`), the reused INC-AEBS-010 ingress and HMI app.

Both VMs sit on the host bridge `cvd-ebr`; each also has a network of its own
(buried_eth0) and the SDV VLANs on eth1.

## Prerequisites (the refreshed S1 list)

1. **Images.** Both from one android17-release revision, same boot mode
   (UNLOCKED, ADR 0025 decision 8). The SDV Core image is rebuilt clean with
   the mapping (INTERPRET_AS_BYTES; a VSIDL type whose bytes field holds the
   2048 bytes and not much more) and the stack configuration (no offered
   service, the frame service's remote endpoint pinned to the host). A data
   APEX update is dropped, so only a rebuild works. The spike's cp2a eng core
   images with the spike broker APEX are not reused (`build_sdv_core_image.sh`).
2. **Host SD network.** The route for the SD group on `cvd-ebr`, and a group
   the bridge forwards: 224.0.0.0/24, or an IGMP querier, or no snooping
   (GAP-MW-047). A long session checks that the offers and renewals keep
   coming (`host_sd_multicast_route.sh`).
3. **Host isolation (GAP-MW-046).** The owner-approved rules, by interface:
   the DDS ports of the domain and port 4721 dropped on every interface but
   lo; the SOME/IP ports accepted to the host only from the SDV Core VM's
   bridge port, matched by its MAC and address. The reachability probe runs
   from both VMs over every interface to every host address, with a positive
   control (`host_isolation_firewall.sh`, `host_isolation_probe.sh`).
4. **Guest-internal SOME/IP.** The stack configuration pins the frame
   service's remote endpoint to the host, so an SD message from the IVI VM
   cannot redirect the subscription; else the residual is recorded for
   REQ-MW-015 under GAP-MW-012.
5. **Clock (ASM-MW-030).** auto_time off, a set and a slew with the image SNTP
   client, the offset measured two-way at the start and the end, and the drift
   measured to size the session. A run whose offset plus its uncertainty is
   not below 20 ms is void (`set_ivi_clock.sh`).
6. **Relay provisioning.** Exactly one ACL file for the relay's subject before
   the IVI VM boots, the relay binary and init file, the ingress port set to
   4731, then an IVI reboot (`provision_ivi_relay.sh`).
7. **Recovery (GAP-MW-048).** The SDV Core VM reboots in place, which keeps
   the launch configuration; death is detected from the logcat "Critical agent
   has died" and from VmHealth. An IVI SD agent or gateway failure needs an IVI
   reboot (`recover_core_vm.sh`, `launch_two_vms.sh reboot-ivi`).
8. **Evidence of record.** Every script and configuration lives in this repo;
   the spike's live in `~/.hermes`. Each run records the image digests, the
   model revision, the S-CORE commits, and the digests of every binary and
   configuration.

## Verification cases and where they run

| Case | Method | Bench |
|---|---|---|
| VC-MW-011, 012, 013, 014, 019 | test | the host half (the reference interop bench): CI, and the VM host for the record |
| VC-MW-015, VC-MW-016 | test | this bench, the two VMs, over a 009D AEBS event |
| VC-MW-017 | inspect + test | this bench: the configuration inspection, and the reachability probe from each VM |
| VC-MW-020 | test | this bench, the two VMs: HMI down, IVI VM down, SDV Core VM (broker) down |
| VC-MW-018, VC-MW-021 | inspect | no run: the configurations and the wiring the execution slices author |

The guard-rail checks that phase 8 assigns to phase 10 (the relay's phase
starts and stored frames, the resubscription behaviour, the copy window, the
clock steps) are preflight checks of this bench. They verify no requirement,
so no case of record holds them, and the evaluators record them as
measurements.

## Sequence and estimates

VM cost: n2-standard-16 in europe-west4 is about €0.80 per hour.

| Session | Content | Nominal | With contingency |
|---|---|---|---|
| S1 | prep (identity, `df`, prune if approved) 0.25 h; the SDV Core image build 1.25 h; the IVI relay build or stage 0.5 h; two-VM launch, relay provisioning, clock set and drift 0.75 h; guest preflight (the chain byte-identical to the host, the offset known) 0.5 h; isolation firewall and the reachability probe (VC-MW-017) 0.5 h | 3.75 h | 5.0 h |
| S2 | the 009D AEBS event over the full chain, MONITORING verified before recording; VC-MW-015 and VC-MW-016 over three events 0.75 h; the resubscription and copy-window preflight checks 0.5 h; the public recording 0.5 h; pull and quiesce 0.4 h | 2.4 h | 3.25 h |
| S3 | VC-MW-020: HMI down ×2, IVI VM down ×2, SDV Core VM (broker) down with the GAP-MW-048 recovery ×2, each with the clock measurements 1.0 h; the recovery timing (stale duration, new subscription) 0.5 h; final pull and teardown 0.4 h | 1.9 h | 2.75 h |
| **Total** | | **≈ 8.05 h (≈ €6.5)** | **≈ 11.0 h (≈ €8.8)** |

Plus disk while the VM is stopped and any idle time; the operator owns the
power state. Prune the spike's android-cuttlefish Bazel cache first if free
space is below the floor, with the owner's OK (it is a deletion).

## Evaluation off the VM

Each running case is evaluated by replay, off the VM, from the raw artifacts
(`python -m de4sdv_broker_path_bench.run <run-dir>`). The evaluators read the
independent captures, not the relay's or the ingress's own logs. No verdict is
typed into a record. Every executed run is retained and reported; a superseded
run is history, not acceptance.

## Risks and non-claims

Ranked risks:
1. The clock bound (ASM-MW-030): at about 60 ppm the 20 ms budget lasts a few
   minutes after a setting, so a slew or short sessions are needed.
2. The host isolation by interface (GAP-MW-046): the probe must cover every
   interface and address, or REQ-MW-016's second finding is not met.
3. The resubscription of the relay: a phase end during the event fails
   VC-MW-014; the preflight measures the subscribe latency and the loss window.
4. The SD multicast across the bridge (GAP-MW-047): no unicast fallback; the
   group and the route must hold over a long session.
5. The moving host half (ASM-MW-021 pins) and the one-process adapter, covered
   by the reference interop bench.

Non-claims: this plan shows no runtime behavior; it verifies no requirement.
No safety, cybersecurity, compliance, certification or homologation statement
is made. The HMI stays an informational display. Google's reference stack is a
non-production reference sample; no SOME/IP conformance or AAOS SDV
compatibility claim is made.

## Handoff

- Task: plan and build the INC-MW-011 phase-10 broker-path bench.
- Owner: de4sdv-integration. Reviewers: de4sdv-vv, de4sdv-architect,
  de4sdv-assurance. Decider: Orkun.
- Input SHA: DE4SDV main `1d36b55b`.
- Status: the scripts, the evaluators and this plan are on the branch; nothing
  executed on the VM. Blockers: the relay lane's binary and subject identity;
  the verification-case slice merged or on the execution head; the CI dispatch of the reference bench
  is the coordinator's and Orkun's call.
