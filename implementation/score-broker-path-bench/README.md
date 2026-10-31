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
  provision_probe_sender.sh   build the probe sender, push it to both guests, record its sha256 in the run manifest
  set_ivi_clock.sh       chrony allow, auto_time off, SNTP measure/step/verify and slew, capture the exchange (ASM-MW-030)
  send_sd_offer.sh       send a spoofed SOME/IP SD offer from the IVI VM (VC-MW-016)
  capture_case.sh        produce the case artifacts: the :4721 and :4731 streams, the relay log, the ss check, the clocks;
                         `ivi-vm-down` reboots the IVI VM and starts the captures after the reboot
  recover_core_vm.sh     death detection (a VmHealth subscriber) and the in-place reboot recovery (GAP-MW-048)
  record_full_chain.sh   the public recording harness (terminals + adb screenrecord)
  teardown.sh            undo everything and write a run-dir session log
aosp-overlay/core/       the SDV Core image overlay (frame type, mapping, stack config, broker ACL)
aosp-overlay/ivi-acl/    the relay's subscriber ACL and the broker's object policy
aosp-overlay/probe-sender/  de4sdv_probe_send.c + Android.bp: the probe/offer sender, built on the guest in S1
config/run-settings.example.json   the settings the evaluators read
src/de4sdv_broker_path_bench/       pure evaluators and the host-side readers (hostscan, sd) the VM scripts call
tests/                   the evaluator and reader unit tests (CI, from real pcap and ss shapes)
VM-CHANGE-LOG.md         what each script changes on the VM and how to undo it
bench-plan.md            the session plan (S1 to S3), VM-hours and cost
```

## Order on the VM (riskiest first)

1. `build_sdv_core_image.sh build` — the SDV Core image with the mapping and the
   stack configuration, clean and recorded. The spike's images are not reused.
2. `host_sd_multicast_route.sh add`, then `launch_two_vms.sh up`.
3. `provision_ivi_relay.sh install`, then `set_ivi_clock.sh setup` and `drift`.
4. `provision_probe_sender.sh build` and `install`: the sender on both guests,
   with its sha256 in `run/run-manifest.yaml`. The probe and the SD offer stop
   when a guest lacks it or holds other bytes.
5. The S1 smoke step first (one probe, one control and one offer with the built
   `de4sdv_probe_send`, checking the exit codes, the captured egress interface,
   source address and MAC, the source port, the counter, the core stack's log
   line about the offer, and the sudo'd scan), then
   `host_isolation_firewall.sh add`, then `host_isolation_probe.sh run <dir>`.
6. The running cases: `capture_case.sh start <dir>`, verify MONITORING
   (`record_full_chain.sh hmi` gates on a fresh app frame line), run the 009D
   AEBS event, `capture_case.sh stop <dir>`, then evaluate off the VM. It
   produces the host `:4721` stream, the guest `:4731` stream, the relay log,
   the `ss` client check and the clock exchanges. For VC-MW-016,
   `send_sd_offer.sh send <provider> <port> <dir>` inside the window adds the
   core stack's record of the offer. For the IVI-VM-down condition of
   VC-MW-020, use `capture_case.sh ivi-vm-down <dir>` in place of `start`.
7. `recover_core_vm.sh` for the GAP-MW-048 case; `teardown.sh` at the end.

## Evaluators

Each evaluator reads a run directory of raw artifacts and returns an outcome of
the middleware evidence vocabulary (passBoundedVerification, failObservedBehavior,
inconclusiveMissingEvidence, blockedTargetRuntime, errorEvidence), mapped to a
verdict as INC-MW-010 maps it. The independent captures are authoritative; the
relay's log is the record of its subscription phases (a layer-caused phase end
in the event is a delivery failure of the layer, so the relay log can fail the
case). For VC-MW-020 the judged start of a new phase is the later of the
relay's phase start and the ingress's loopback accept in the guest capture;
both times and their difference are recorded. A later start only makes the
check stricter: a relay that claims a start before the ingress connected is
judged against the accept, and in the normal order (the accept, then the
relay's log line) the later time is the relay's own. If the capture has no
accept for a connection and first saw it after the relay's start, the start is
not known and the phase gives no pass. A capture gap also gives no pass,
because a lost frame can be an old one. A captured old frame fails in both
cases. It compares
raw clock readings, with no offset correction, as the phase-8 rule and the
verification case do. Precedence follows the verification cases (`middleware_score_verification_evidence.sysml`):
only a failure whose evidence
does not depend on an inconclusive condition dominates, so a capture gap, a
second `:4721` client or a failed clock bound turns a completeness failure into
missing evidence, not a fail. The evaluators never open a socket and never run
on the VM. Each run is one condition; a case pass needs every condition the
case names.

```bash
PYTHONPATH=src python -m de4sdv_broker_path_bench.run <run-dir>            # every supported case
PYTHONPATH=src python -m de4sdv_broker_path_bench.run <run-dir> --case VC-MW-015
# VC-MW-020 over its four condition runs (one run directory per condition):
PYTHONPATH=src python -m de4sdv_broker_path_bench.run --vc020-runs <hmi-down> <ivi-vm-down> <core-down> <pair-restart>
```

On one run directory the reported VC-MW-020 outcome is the case outcome over
that one condition, so it is never a case pass; each condition's own result
stays under `conditions`. The report also holds the sha256 of every artifact
it read and a digest of the evaluator sources.

| Case | Requirement | What the evaluator checks from raw artifacts |
|---|---|---|
| VC-MW-015 | REQ-MW-014 | every frame produced unambiguously inside a subscription phase (beyond the 20 ms clock band) reaches the HMI, in order, inter-arrival below 500 ms; a layer-caused phase end or a DATA_LOSS inside the AEBS event fails (the event is the span of `produced.pcap`, its first to its last frame timestamp, not the stage sequence); an ingress disconnect that the relay causes in the event fails too: the relay's exit (`gateway_client_lost`, exit code 4), its own close after a write failure, or a close of a frame-carrying stream from port 4731 in `received.pcap`; an ingress that closes its own stream in the event, a second `:4721` client (recorded as a bench discrepancy), a capture gap or ASM-MW-030 not holding is inconclusive |
| VC-MW-016 | REQ-MW-015 | each received frame equals its produced frame byte for byte, with its source kind; a received frame the stack never produced fails; after a spoofed SD offer the provider must stay 192.168.98.1 and the frames must keep arriving; the spoofed offer must come from the SD source port 30490 and `sd_core_processed.json` must show the core stack processed it (status `processed` with the matched log line), else inconclusive (a stack ignores an SD message from another port); a subscription to another provider after the offer fails even with no log line; a written `sd_offer.json` is data only and gives no pass |
| VC-MW-017 | REQ-MW-016 | second finding: no host DDS port of the layer is reachable from a guest, judged by a capture on the guest-facing interface plus the drop-rule counter (reached = captured and not dropped; isolated = captured and dropped, so a counter that moved with nothing captured is a gap, not isolated; a recorded host-socket receipt or a completed guest TCP connect also counts as reached); the probes use the bench sender, which pins the egress device, source address and source port, so a probe leaves on its named interface; a probe covers its (guest, interface, host) pair only when the capture shows it arrived from the named source address and the named guest interface's MAC (the `:4721` SYN is found by its pinned source port); each expected pair must cover the full DDS port set of `dds_range.json` (domain 91, index 120) plus 4721, else a gap; a probe that arrived from another interface or source covers nothing but a reach is still a reach; a failed, unsent or malformed probe is a coverage gap; a positive control by the same observation; without a readable firewall table the run is inconclusive; a reachable `:4721` is an ASM-MW-029 finding, not a failure; the first finding needs the inspection record |
| VC-MW-020 | REQ-MW-019 | per condition (HMI down, IVI VM down, SDV Core VM down, pair restart): each frame in a new phase was produced no more than the 20 ms margin before the judged phase start (the later of the relay's start and the ingress's loopback accept), compared raw; a frame earlier than that start by more than the offset plus its uncertainty plus 20 ms fails whatever the clock shows, but only when the relay logged no clock step between the two offset measurements; the same check runs again with the subscription time in `data-tunnel-vlan2.pcap` as the start, over every received frame delivered at or after that start, including frames outside relay phases and after a phase end; if it fails while the first passes the run is inconclusive; without that time (no capture, or neither the stream's opening nor a flow from before the judged start in it) the run gives no pass; with only a flow bound, any frame delivered outside relay phases between the previous phase end (or capture start) and the judged start gives inconclusive, and every later delivery must meet the stricter judged-start margin; a missing frame timestamp gives no pass; the IVI-VM-down condition keeps the first post-reboot phase as data outside both checks; a capture gap in `received.pcap`, or a judged connection that the capture joined after the relay's start with no accept, is inconclusive unless a captured frame fails; needs ASM-MW-030 to hold |

The run directory holds, by convention: `produced.pcap` (host `:4721`),
`received.pcap` (guest `:4731`), `relay-logcat.txt` (the relay's events, with
its tag), `clock-start.pcap`, `clock-end.pcap`, `settings.json`,
`frame_assembler_clients.json` (the two-step ASM-MW-029 `ss` check),
`ivi_boot.txt` (the IVI boot identity at the start and the stop),
`data-tunnel-vlan2.pcap` (the cleartext Data Tunnel on VLAN 2, VC-MW-020's
second start), and for
VC-MW-016 `host-cvd-ebr.pcap` (the SD capture) with `sd_core_processed.json`
and `core-logcat-sd-offer.txt`, or `residual.json` (GAP-MW-012), and
for VC-MW-017 the probe JSON (`firewall.json`, `host_listeners.json`,
`probe_attempts.json`, `captured_markers.json`, `control.json`,
`coverage.json`, `dds_range.json`, `probe_sender.json`, `asm_mw_031.json`,
`inspection.json`). The run directory lives outside the repository (or under
the git-ignored `run/`). See
[`config/run-settings.example.json`](config/run-settings.example.json).

What the scripts record about identity, and what they do not:

- `build_sdv_core_image.sh build` writes `core-image-identity.txt` into the
  session run directory (`run/`), once per successful build: the resolved
  manifest digest, the repo status, the `device/google/sdv` diff digest, the
  build fingerprint, the image hashes and the staged overlay files.
- `provision_probe_sender.sh install` writes the `probe_sender` block of
  `run/run-manifest.yaml`: the host path and sha256 of the sender and the
  sha256 read back from each guest. The probe copies what it found into
  `probe_sender.json` of its run directory.
- `capture_case.sh stop` writes `capture-manifest.yaml` per case run: the
  capture commands, the relay tag, the stop time and the IVI boot identity.
- `run.py` reports the sha256 of every artifact it read and a digest of the
  evaluator sources.
- Not recorded by a script: the IVI image, the relay binary and init digests,
  the DE4SDV SHA, the S-CORE commits, the boot arguments and `settings.json`.
  The operator records these from the console (see Known limits).

The inspection cases VC-MW-018 and VC-MW-021 need no run; they read the
configurations and the wiring the execution slices author. The verification
cases are pinned at main `4bcfe628` (`middleware_score_verification_evidence.sysml`).

## Interfaces this bench needs from the other lanes

- **The IVI frame relay** (`implementation/score-reference-interop-bench/ivi-frame-relay`,
  on main at `5835cb6f`). `scripts/bench_env.sh` names its values, and
  `tests/test_relay_inputs.py` holds them to the relay's own files (its `.rc`,
  `options.hpp` and `Android.bp`); a script fails fast when one is set empty.
  - binary `RELAY_BIN` = the relay's AOSP build output on the host
    (`$AOSP_TOP/out/target/product/$IVI_PRODUCT/system/bin/de4sdv_ivi_frame_relay`),
    which the install pushes to `/system/bin/` on the IVI VM; the install
    checks the host path, not the guest path;
  - init file `RELAY_RC` = `ivi-frame-relay/de4sdv_ivi_frame_relay.rc`;
  - liblog tag `RELAY_LOGCAT_TAG` = `de4sdv_ivi_frame_relay` (the example
    settings carry it as `relay_logcat_tag`);
  - authz subject `RELAY_SUBJECT_PACKAGE` = `de4sdv.ivi_frame_relay`,
    `RELAY_SUBJECT_BUNDLE` = `IviFrameRelay`, `RELAY_SUBJECT_INSTANCE` =
    `default`;
  - loopback server on `127.0.0.1:4731`, one client; it sets the ingress port
    and host from its own init file on boot.

  The bench parses the relay's phase_start, phase_end, clock_step, data_loss
  and gateway_client_lost (exit code 4) records at `5835cb6f`.
- **The verification cases** (`middleware_score_verification_evidence.sysml` at main `4bcfe628`):
  VC-MW-015, VC-MW-016, VC-MW-017 and
  VC-MW-020 keep their observation point at the IVI loopback and name the
  relay's discard rule. This bench realizes their running side.

## Recording (owner approved; posting needs a separate approval)

`record_full_chain.sh` records real operator terminals (`script --log-timing`)
and the real IVI HMI display (`adb screenrecord`), started only after MONITORING
shows. Panes: the host stack and gatewayd/someipd, the SDV Core broker logcat,
the relay log, and the IVI frame path (the ingress's per-frame line beside the
app's, both with epoch stamps). No rendered or stylized footage. An edited cut is
labeled `publication_cut`; the raw files stay with the evidence.

`hmi` also writes `hmi-anchor.yaml`: the IVI clock read immediately before and
after the screenrecord launch, and the host time around it. The video's `t = 0`
lies inside that interval, so a log line or a frame record can be placed on the
video from the anchors (the bracket is one adb round trip, roughly 0.2 s) and
the placement is re-checkable from the state transitions the app logs. Without
the anchors the alignment would have to be inferred from the pixels.

## Known limits

These stay manual or run only on the VM. The guest tooling and the sudo'd scan
first run on the live guests in the S1 smoke step (the plan's first S1 step),
before any case run, so none blocks the first session once that smoke step
passes.

- **The guest sender and the sudo'd scan first run on the VM.** The probes, the
  control and the spoofed SD offer use `de4sdv_probe_send`, built in the AOSP
  tree by `provision_probe_sender.sh build` (the `aosp-overlay/probe-sender`
  Android.bp) and pushed to both guests by `install`, which records its sha256
  in the run manifest; the probe and the offer stop when a guest lacks it or
  holds other bytes. The Android.bp flags (`vendor`, `sdk_version`, the
  warnings as errors) are first checked by that AOSP build in S1. CI compiles
  the C source with the host compiler; the namespace exercise
  (six tests in `tests/test_probe_sender.py`) is skipped on the CI runner, which has no
  unprivileged user namespaces; it ran locally and in the harness. The
  ASM-MW-031 scan runs under `sudo` from `src/`. Both are
  confirmed in the S1 smoke step: one probe, one control and one offer,
  checking the exit codes, the captured egress interface, source address and
  MAC, the source port, the counter, and the scan.
- **The core stack's log lines about the offer are vsomeip 3.1.37.1's.**
  `send_sd_offer.sh send` takes the SDV Core VM's logcat around the offer and
  writes `sd_core_processed.json`. The default lines come from the COVESA
  3.1.37.1 source: "Ignoring offer of [4dee.0001]" (secure services) and "Do
  not accept offer from ..." (acceptances) show the stack processed and
  refused the offer; "Ignored SD message from unknown port" or "... unknown
  address" show it never reached service discovery. The image's copy may log
  other lines or at another level, so S1 confirms them, and
  `SD_PROCESSED_PATTERNS` and `SD_IGNORED_PATTERNS` replace them. The 3.1.37.1
  service discovery logs no line of its own when it accepts an offer: then the
  record says "unknown" and the case is inconclusive, unless the SD capture
  shows a subscription to another provider, which fails.
- **A probe's interface is identified by its MAC and source address.** The
  host names its interfaces differently from the guest, so the evaluator ties a
  captured probe to the guest interface by the frame's source MAC (from the
  guest inventory) and source address. VLAN interfaces keep their parent's
  MAC, so their own source addresses tell them apart. Every expected (guest
  interface, host address) pair needs its own captured probes. A guest
  interface whose segment does not carry the host (no captured probe) is a
  gap for each of its pairs, so the run is inconclusive. The spike inventory
  already shows such interfaces: sd_mesh, sdv_dt and sdv_rpc (VLAN 1, 2 and 3,
  on 192.168.99, 100 and 101) share eth1's MAC, and the host has no address on
  those VLANs, so they are expected but cannot carry probes to the host. So S1
  needs the owner's decision on the expected set.
- **Scripted or manual on the VM.** These steps the scripts record but do not
  judge, so the operator confirms them by eye in S1: the image inspection (the
  broker descriptor built, the DE4SDV stack configuration loaded, no SOME/IP
  offer from 192.168.98.3, the `REMOTE SUBSCRIBE` line); the launch of the SD
  agent and the guest survival of the operator's shell; the post-boot relay
  checks; the MP4 of the recording; and the 2048-byte frame boundary.
- **The IVI-VM-down capture starts after the reboot.** The guest captures and
  the relay-log stream end when the IVI VM reboots. So `capture_case.sh
  ivi-vm-down` reboots the IVI VM, checks the new boot identity, starts the
  captures, sets the clock and only then measures the clock start. Any run
  whose IVI boot identity changed inside its window fails `capture_case.sh
  stop`. The reboot and the boot identity are checked only on the VM.
- **The MONITORING gate is time-bounded.** `record_full_chain.sh hmi` takes the
  app's latest frame line and opens the gate only when it shows MONITORING and
  is at most `MONITORING_MAX_AGE_S` (2 s) older than the IVI VM clock, which
  is read to the second. The app's line format is INC-AEBS-010's; S1 confirms it.
- **A new phase after the clock setting is checked only on the VM.**
  `set_ivi_clock.sh setup` stops and restarts the ingress after the clock
  setting and then asserts that a new relay phase_start appears (a (pid,
  phase) the relay log did not hold before the restart); it fails otherwise.
  The assertion runs only against a live IVI VM, so S1 confirms it.
- **The clock set is measured, applied and re-measured, because `toybox sntp -s`
  is not a step on the sdv_ivi_cf image.** It prints the offset, exits 0 and
  leaves the clock where it was (a fresh guest read -183.6 ms before and -183.5 ms
  after the set), so a set built on it reports success while the window runs on
  the guest's free-running drift — the S2 window measured +44.5 ms against a
  20 ms bound exactly this way. `set_ivi_clock.sh set` (and `setup`, which calls
  it) therefore measures with `toybox sntp -q`, applies the offset with
  `toybox date -s` inside one guest shell — read, add and set in a single command,
  since two adb round trips leave the set 50-150 ms late and never converge — and
  then takes a second exchange that must show the residual inside
  `CLOCK_SET_BOUND_MS` (5 ms). The second exchange is the verification; a set that
  does not land fails the script. The guest needs an `awk` for the arithmetic
  (`/system/bin/awk` on this image); the script says so if it is missing. The
  harness runs under `LC_ALL=C`, because a host locale with a decimal comma makes
  the computed epoch unparseable for the guest's `date`.
- **The bridge-family firewall rule is not executable off the VM.** The
  SOME/IP bridge-port hardening (`host_isolation_firewall.sh`) sits in an
  `nf_tables` bridge input chain, which this development host's kernel does not
  carry, so it is checked only on the VM. It is a recorded design measure, no
  part of any case's pass condition (VC-MW-017, VC-MW-020).
- **The Data Tunnel subscription time rests on design data.** VC-MW-020 runs
  its check a second time with the subscription time in
  `data-tunnel-vlan2.pcap` as the start. In the UNLOCKED mode Data Tunnel is
  gRPC over cleartext HTTP/2: the IVI agent opens a stream with a HEADERS
  frame and the core streams the publication's messages back, each carrying
  the frame bytes. So the evaluator finds the phase's first frame by its bytes
  and takes the opening HEADERS of the stream that carried it as the
  subscription time. The spike's VLAN 2 captures show this framing (truncated
  at 256 bytes there; the bench captures with `-s0`); S1 confirms it on the
  bench. The second check judges every received frame delivered at or after
  the Data Tunnel start, including frames outside relay phases and after a
  phase end. The first post-reboot phase in ivi_vm_down stays data outside both
  checks. The spike also shows the Data Tunnel stream keeps running
  while no IVI client subscribes, so the stream can open before the capture
  starts. Then the evaluator accepts a bound instead: the produced frames
  flowed on the same carrier, with no gap of 500 ms or more, from before the
  judged start to the phase's first frame, so the subscription started before
  the judged start. With the bound, no frame may have been delivered outside a
  relay phase between the previous phase end (or the capture start) and the
  judged start; such a frame gives inconclusive. Every delivery at or after
  the judged start must meet its stricter margin, even outside relay phases;
  otherwise the bound alone gives no pass. A missing timestamp gives no pass
  too. With those checks, the bound holds in all four
  conditions. Without the opening and without that flow, the time is unknown
  and the run gives no pass. Two cases give no pass that way, failing closed:
  in pair_restart neither VM restarts, so a new stream may open on a VLAN 2
  connection older than the capture, whose opening the capture cannot read,
  and the publication's re-creation can leave a flow gap (S1 shows whether
  the connection is new); in ivi_vm_down, a forward clock step of 500 ms or
  more within the 3 s look-back before the judged start can split the flow,
  making the bound unknown and the run inconclusive. A gRPC message split
  across HTTP/2 frames, or a Data Tunnel layout other than this, gives
  "unknown" (never a pass). The VC-MW-015 evaluator still takes its phase
  windows from the relay log alone; it does not yet apply the capture
  comparison that VC-MW-015 also names for it.
- **A clock step near a measurement disables the wide limit.** The relay
  stamps a clock step with the realtime after it, so a step that the times
  cannot place between or outside the two offset measurements counts as
  between: the wide limit is not applied, which can only remove a fail. The
  clock setting just before the start measurement (as in `capture_case.sh
  ivi-vm-down`) can fall in that margin.
- **The probe is serialized and long.** `host_isolation_probe.sh` reads the
  drop counter around each of the 244 DDS ports plus 4721, for each interface
  and host address, from both VMs. Each probe is one guest command and two
  counter reads (the sender itself does not wait). A reduced DDS range is a
  coverage gap, not a pass (`dds_range.json`), so a dry run is inconclusive by
  design. S1 measures the probes per second and sizes the slot from it; the
  0.75 h the plan budgets for the firewall and probe may not fit the full
  cross product.
- **ASM-MW-031 needs root over `/proc`, and `ss -p` runs without sudo.** The
  host ROS 2 environment scan reads `/proc/<pid>/environ` for every ROS 2
  process; a process it cannot read gives inconclusive, so the scan runs as
  root on the VM (it keeps its stderr and records the uid). `ss -p` runs
  without sudo, so another user's socket shows no owner and a reached layer
  port then counts as "other" (FAIL if ASM-MW-031 holds, inconclusive if not;
  never a false pass). The probe does not cover IPv6: it sends IPv4 only.
  Per-interface egress is pinned by the sender's `SO_BINDTODEVICE`, not by the
  host route, and the evaluator checks it from the capture.
- **Two latent issues, not live on this image.** The probe's markers and
  coverage keys leave out the guest namespace, which is harmless while each
  namespace's interfaces have distinct names (as on this image). A relay phase
  whose phase_end is missing while a later phase of the same pid exists is not
  flagged as a record problem.
- **The inspection record is written by hand.** `inspection.json` (the first
  finding) is recorded by the operator; the evaluator reads only its
  `no_host_endpoint` field.
- **The VC-MW-015 event is the span of the produced capture.** The evaluator
  takes the AEBS event window as the first to the last frame timestamp in
  `produced.pcap` (with the 20 ms band), not as the stage sequence. A phase
  end or a DATA_LOSS anywhere in the capture span therefore counts as inside
  the event, which is the stricter reading.
- **A genuine stop versus a cut capture.** VC-MW-015 and VC-MW-016 bound at the
  end of the received capture: a stream cut mid-connection (no clean close) is
  read as a guest capture stopped early, so frames produced after it are not
  required; a cleanly closed stream keeps no ceiling, so a real stop still
  fails. The S1 capture order (host captures stopped first) makes the received
  capture outlive the produced capture.
