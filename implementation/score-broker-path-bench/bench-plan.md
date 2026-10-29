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
| DE4SDV main | `4bcfe628` (phase 8 broker path, ADR 0025, and the phase-10 verification cases) |
| Phase 8 realization | `middleware_score_physical_software_realization.sysml` @ main, with the relay, GAP-MW-045 to GAP-MW-048 and the next action (steps 1 to 11) |
| Requirements | REQ-MW-014, REQ-MW-015, REQ-MW-016 (two findings), REQ-MW-019 @ main |
| Verification cases | `middleware_score_verification_evidence.sysml` at main `4bcfe628` (VC-MW-015 to VC-MW-020 on the broker path). The evaluators follow this commit; rebind when the file changes on main |
| Host half | the S-CORE reference interop bench (`../score-reference-interop-bench`): the adapter, gatewayd, someipd, ASM-MW-021 pins |
| Relay | the IVI frame relay (`implementation/score-reference-interop-bench/ivi-frame-relay`) at `028467e2`, branch `feat/score-someip-receiver`, not yet on main (binary `de4sdv_ivi_frame_relay`, its init file, tag `de4sdv_ivi_frame_relay`, subject `de4sdv.ivi_frame_relay`/`IviFrameRelay`/`default`); the bench parses its phase_start, phase_end, clock_step, data_loss and gateway_client_lost (exit code 4) records at this commit |
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
   control (`host_isolation_firewall.sh`, `host_isolation_probe.sh`). The
   probes, the control and the spoofed offer use `de4sdv_probe_send`, built in
   the AOSP tree and pushed to both guests (`provision_probe_sender.sh`), which
   records its sha256 in the run manifest, so each probe pins its egress
   device, source address and source port. **The first S1 step, ahead of any
   case run, is a smoke step:** one probe to a dropped DDS port (exit 0, the
   marker captured on the host from the named source address and MAC, the
   counter moved), one control (exit 0, captured and delivered) and one SD
   offer from source port 30490 with the core stack's log line about it
   (`sd_core_processed.json`, which confirms the vsomeip lines on the image),
   plus the sudo'd ASM-MW-031 scan. It confirms the guest tooling and the scan
   on the live guests before the long probe.
4. **Guest-internal SOME/IP.** The stack configuration marks the frame service
   secure and accepts it only from the host (`secure-services` and
   `acceptances`), which is meant to keep an SD message from the IVI VM from
   redirecting the subscription; VC-MW-016 tests it with a spoofed offer. With
   service discovery enabled the per-service unicast alone does not pin the
   provider, and AOSP's vsomeip may carry patches, so S1 verifies the effect;
   else SD is filtered in the SDV Core VM, or the residual is recorded for
   REQ-MW-015 under GAP-MW-012.
5. **Clock (ASM-MW-030).** The host chrony serves the IVI (`allow`), auto_time
   off, a set with `toybox sntp -s` and a slew with `toybox sntp -a -d`, the
   offset measured two-way at the start and the end, the drift measured to size
   the session, the host clock steps logged, and the ingress restarted after
   the setting. A run whose offset plus its uncertainty is not below 20 ms, or
   with a clock step in a judged phase, is void (`set_ivi_clock.sh`).
   **S1 check:** after the clock setting, a new relay phase_start appears.
   `set_ivi_clock.sh setup` stops the ingress, waits for it to stop, starts it
   again and asserts a phase_start whose (pid, phase) the relay log did not
   hold before the restart; it fails otherwise. This runs only on the VM.
6. **Relay provisioning.** Exactly one ACL file per subject across /product,
   /system and /vendor before the IVI VM boots, the broker's object policy, the
   relay binary and init file (the relay sets the ingress port 4731 and host
   from its own init file on boot), then an IVI reboot and the post-boot checks
   (`provision_ivi_relay.sh`). The relay inputs are required, with no defaults;
   an S1 preflight compares them with the relay's `.rc` at `028467e2`.
7. **Recovery (GAP-MW-048).** The SDV Core VM reboots in place, which keeps
   the launch configuration; death is detected from the logcat "Critical agent
   has died" and from VmHealth. An IVI SD agent or gateway failure needs an IVI
   reboot (`recover_core_vm.sh`, `launch_two_vms.sh reboot-ivi`).
8. **Evidence of record.** Every script and configuration lives in this repo;
   the spike's live in `~/.hermes`. `build_sdv_core_image.sh` records the SDV
   Core image identity on a successful clean build: the resolved manifest
   digest, the repo status, the `device/google/sdv` diff digest, the build
   fingerprint, the image hashes and the staged overlay files at their
   destinations. `provision_probe_sender.sh install` records the probe sender's
   sha256 (host and both guests) in `run/run-manifest.yaml`, and
   `capture_case.sh stop` records the capture commands and the IVI boot
   identity per case run. The IVI image, the relay binary and init digests,
   the DE4SDV SHA, the S-CORE commits and the boot arguments are not yet
   recorded by a script; the operator records them from the console until the
   run manifest covers them. This is a known limit, not a pass condition.

## Verification cases and where they run

| Case | Method | Bench |
|---|---|---|
| VC-MW-011, 012, 013, 014, 019 | test | the host half (the reference interop bench): CI, and the VM host for the record |
| VC-MW-015, VC-MW-016 | test | this bench, the two VMs, over a 009D AEBS event |
| VC-MW-017 | inspect + test | this bench: the configuration inspection, and the reachability probe from each VM |
| VC-MW-020 | test | this bench, the two VMs, four conditions: HMI down, IVI VM down, SDV Core VM (broker or stack) down with the GAP-MW-048 reboot, and a gatewayd+someipd pair restart |
| VC-MW-018, VC-MW-021 | inspect | no run: the configurations and the wiring the execution slices author |

The guard-rail checks that phase 8 assigns to phase 10 (the relay's phase
starts and stored frames, the resubscription behaviour, the copy window, the
clock steps) are preflight checks of this bench. They verify no requirement,
so no case of record holds them. The evaluators record the measurements they
read off the raw artifacts (the phase count, the judged and band frame counts,
the clock offsets at start and end, the largest inter-arrival gap); the stored
frames, the copy window and the per-phase clock steps come from the relay's
own log, which the operator reviews. The outage, long-session, link-loss,
VM-reboot, corrupted-payload and malformed-wrapper cases of next-action steps 9
and 10 run in S1 to S3 as the preflight of VC-MW-015/016/020 and of the relay's
discard rule; where one of them verifies a requirement, its case holds it as a
step.

## Sequence and estimates

VM cost: n2-standard-16 in europe-west4 is about €0.80 per hour. The host
Autoware AEBS stack with the 009D event runs on this same VM (INC-AEBS-010 ran
it on a separate host, and the VM's Autoware converter is present but not
built), so S0 and S1 budget its build and bring-up.

| Session | Content | Nominal | With contingency |
|---|---|---|---|
| S0 | host-stack readiness: `df -h /`, prove nothing in use points into the 31 GB Bazel cache (`readlink -f` of the cvd binaries, `dpkg -L` of the cuttlefish packages, the host-resources unit, `lsof +D`), then Orkun's prune decision (D3 allows it on that condition); build the Autoware converter and stage the 009D bench | 1.5 h | 2.25 h |
| S1 | prep and identity (`repo manifest -r`, the device diff digest) 0.25 h; the clean SDV Core image build, with the probe sender built and pushed beside the relay 1.5 h; the IVI relay stage 0.5 h; two-VM launch with `--config`, relay provisioning, chrony allow, clock set and drift, and the check that a new phase_start follows the clock setting 1.0 h; guest preflight (the chain byte-identical to the host, the offset known) 0.5 h; **the smoke step first** (one probe, one control, one offer with the sender; exit codes, captured egress interface and source port, counter, sudo'd scan), then the isolation firewall and the reachability probe (VC-MW-017), sized from the measured probes per second 0.75 h | 4.5 h | 6.0 h |
| S2 | the 009D AEBS event over the full chain, MONITORING verified before recording; VC-MW-015 and VC-MW-016 over three events 0.75 h; the resubscription, copy-window, SD-outage and malformed-wrapper preflight checks 0.75 h; the public recording 0.5 h; pull and quiesce 0.4 h | 2.4 h | 3.25 h |
| S3 | VC-MW-020 four conditions: HMI down ×2, IVI VM down ×2, SDV Core VM down with the GAP-MW-048 recovery ×2, and the gatewayd+someipd pair restart with the PublicationDestroyed latency ×2, each with the clock measurements 1.25 h; the recovery timing (stale duration, new subscription) 0.5 h; final pull and teardown 0.4 h | 2.15 h | 3.0 h |
| **Total** | | **≈ 10.55 h (≈ €8.4)** | **≈ 14.5 h (≈ €11.6)** |

Plus disk while the VM is stopped and any idle time; the operator owns the
power state. The clean core build consumed about 30 GB at its peak in the
spike, and the bench started with 19 GB free (below the 20 GB guard), so S0's
prune of the android-cuttlefish Bazel cache is effectively required; it happens
only after the S0 checks pass and Orkun approves.

## Evaluation off the VM

Each running case is evaluated by replay, off the VM, from the raw artifacts
(`python -m de4sdv_broker_path_bench.run <run-dir>`). The evaluators read the
independent captures, not the relay's or the ingress's own logs. No verdict is
typed into a record. Every executed run is retained and reported; a superseded
run is history, not acceptance.

## Risks and non-claims

Ranked risks:
1. The clock bound (ASM-MW-030): at about 60 ppm the 20 ms budget lasts a few
   minutes after a setting. VC-MW-015 wants a long session (many SD cycles),
   which conflicts with the budget unless the slew works; S1 measures the drift
   and, if the slew does not hold, sizes each session from it.
2. The host isolation by interface (GAP-MW-046): the probe must cover every
   interface and address, or REQ-MW-016's second finding is not met.
3. The resubscription of the relay: a layer-caused phase end during the event
   fails VC-MW-015 (REQ-MW-014); the preflight measures the subscribe latency
   and the loss window.
4. The SD multicast across the bridge (GAP-MW-047): no unicast fallback; the
   group and the route must hold over a long session.
5. The moving host half (ASM-MW-021 pins) and the one-process adapter, covered
   by the reference interop bench.

Non-claims: this plan shows no runtime behavior; it verifies no requirement.
No safety, cybersecurity, compliance, certification or homologation statement
is made. The HMI stays an informational display. Google's reference stack is a
non-production reference sample; no SOME/IP conformance or AAOS SDV
compatibility claim is made.

## Known limits

None of these blocks the first VM session; the operator confirms them by hand.

| Step | Status in S1 |
|---|---|
| Disk and prune | Manual (the S0 check and Orkun's decision); the build checks a disk floor |
| Tree identity | Scripted (resolved manifest, repo status, device diff), except the samples clean status before staging |
| Image inspection (broker descriptor, stack config loaded, no offer from .3, `REMOTE SUBSCRIBE`) | Manual; the SD capture is recorded but not judged |
| Launch | Core asserted (`ro.boot.sdv.*`, UNLOCKED, SOME/IP on, SD connection); the IVI and SD-agent lines only logged; guest survival manual |
| IVI authorization | Install and the one-file-per-subject check scripted; the post-boot relay checks only logged |
| Real frame source | Manual (the host runs the real frame assembler, not a synthetic source) |
| Clock | Scripted (chrony allow, auto_time off, set and slew, two measurements, the ingress restart); the host-step log and the `ping`/`tcpdump` presence checks assume the image carries them |
| New phase after the clock setting | Scripted and VM-only: `set_ivi_clock.sh setup` asserts a new relay phase_start after the ingress restart and fails otherwise; S1 confirms it on the live IVI VM |
| Captures | Scripted; the host captures are stopped first and the guest captures last, so the received capture outlives the produced capture (review B1); the kernel drop count is read from the capture tool's exit line, not the pcap; a run whose IVI boot identity changed inside its window fails at stop; the IVI-VM-down condition uses `capture_case.sh ivi-vm-down`, which starts the captures after the reboot |
| Probe sender | Scripted (`provision_probe_sender.sh build`, `install`): built in the AOSP tree, pushed to both guests, its sha256 checked on each guest and recorded in the run manifest; the probe and the offer stop when it is missing or differs. The Android.bp flags are first checked by this build in S1; CI only compiles the C source and exercises it in a namespace |
| S1 smoke step (first) | Scripted and VM-only, ahead of any case run: one probe, one control and one SD offer with the built sender, checking the exit codes, the captured egress interface, source address and MAC, the source port, the counter, the core stack's log line about the offer, and the sudo'd ASM-MW-031 scan |
| Firewall and probe | Scripted; the bridge-family SOME/IP rule is checked only on the VM (no `nf_tables` bridge family on the build host); the probe is serialized and each UDP probe is at least a second, so a full probe over every DDS port, interface and host address takes tens of minutes. A reduced range is a coverage gap, not a pass; S1 measures the probes per second and sizes the slot (the 0.75 h budget does not fit the full cross product) |
| ASM-MW-031 scan | Scripted and VM-only: the root `/proc` scan runs under `sudo` from `src/`, keeps its stderr and records the uid; an unreadable process gives holds=null |
| VLAN 2 Data Tunnel capture | Recorded by `capture_case.sh`, retained for review; the VC-MW-020 judged start is the later of the relay's start and the loopback accept, not this capture |
| Spoofed SD offer | Scripted (`send_sd_offer.sh send <provider> <port> <run-dir>`), sent from the SD source port 30490 with the sender so the core stack does not ignore it; the step takes the core's logcat around the offer and writes `sd_core_processed.json` (processed, ignored or unknown, with the matched vsomeip 3.1.37.1 line; S1 confirms the lines on the image); the provider after the offer is read from the SD capture |
| HMI recording | The MONITORING gate is scripted on the app's real line and time-bounded (the latest frame line at most 2 s older than the IVI clock); the MP4 is validated by hand |
| 2048-byte boundary | Manual (a 2044-byte frame end to end) |
| Run manifest | Partial: the core image identity is recorded; the IVI image, the relay and init digests, the DE4SDV SHA, the S-CORE commits and the boot arguments are recorded from the console until the next slice adds the full manifest |

## Handoff

- Task: plan and build the INC-MW-011 phase-10 broker-path bench.
- Owner: de4sdv-integration. Reviewers: de4sdv-vv, de4sdv-architect,
  de4sdv-assurance. Decider: Orkun.
- Input SHA: DE4SDV main `4bcfe628`.
- Status: the scripts, the evaluators and this plan are on the branch; nothing
  executed on the VM. Blockers: the relay lane's binary and subject identity;
  the verification-case slice merged or on the execution head; the CI dispatch of the reference bench
  is the coordinator's and Orkun's call.
