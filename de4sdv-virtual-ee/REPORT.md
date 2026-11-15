# Virtual E/E — feasibility report

Historical feasibility measurements and the acceptance boundary for this
software-in-the-loop zonal demonstrator. Existing archives are retained unchanged.
Some early campaigns have only the reported figures, not committed raw records;
those figures are not exact-revision acceptance evidence.

**Review status: acceptance reopened.** The original evaluators could admit
incomplete or failed runs, the routing topology outgrew the old isolation check,
and the source/image identities were incomplete. Local repairs and fresh
committed-input execution must be verified before this increment is called closed.

Date: 2026-11-15. Testbed: GCP `e2-standard-4`, Ubuntu 24.04, kernel
7.0.0-1017-gcp, vxedge 0.30.0, rootless Podman.

## 1. Verdict

**The historical runs show a narrow functional demonstrator: one host,
virtual CAN, routed UDP, a small SOME/IP service plane, and containers on one
kernel. They do not prove acceptance of the repaired revision.**

- Historical captures show closed loops, a routed diagnostic and policy counters.
  Their summaries can be recomputed, but the old pass conditions were incomplete.
- The earlier compute estimate was approximately €0.75, not a current billing
  record. No paid software licence was required; that does not remove third-party
  licence or distribution obligations (§7).
- Image identities are digest-pinned; rebuilding is not fully hermetic (§8).
  Images remain in an operator-owned loopback registry, not a public registry.
- Not production, not certified, and not a latency predictor (§5).

## 2. What exists

```text
                    central node (hpc1, container)
        ┌───────────────────────────────────────────────┐
        │ KUKSA databroker 0.7.1        vxota (OTA)     │
        │        ▲  gRPC over the adas slice            │
        │        │                                      │
        │  DE4SDV bridge ◀── UDP ──▶ CAN gateway        │
        │  vcan-front / vcan-rear   per-frame allow-list│
        └───────┬───────────────────────┬───────────────┘
                │ adas (vlan 101)       │ adas (vlan 101)
        ┌───────┴────────┐      ┌───────┴────────┐
        │ zone-fl        │      │ zone-rl        │
        │ plant (headlamp│      │ plant (wiper)  │
        │ + kuksa-provider      │ + provider     │
        │ vcan0)         │      │ + OpenBSW ECU  │
        └────────────────┘      └────────────────┘
                 zone-fr: a probe node on the infotainment slice (vlan 103)
```

Four zones, three payload containers plus a probe, two VLAN slices, one userspace
gateway that decides per frame. Policy, counted on the wire and at the gateway:

| direction | allowed | denied |
|---|---|---|
| front → rear | `0x181` (headlamp status), `0x7E0` (diagnostic request) | `0x180` (headlamp command) |
| rear → front | `0x281` (wiper status), `0x7E8` (diagnostic response) | `0x280` (wiper command) |

## 3. Historical gate reports

The table records the earlier reported outcomes, not current-head acceptance.
The original raw gate-2 matrix and several earlier comparison campaigns are not
committed here. The later demo archive is not a substitute for those raw runs.
Its twelve-command scenario also differs from the current sixteen-transition
driver; do not relabel its manifest or apply a new acceptance label to it.

| gate | what it had to show | result | evidence |
|---|---|---|---|
| 0a control plane | daemon provisioned a two-zone vehicle | **pass** | `vxedge doctor --tier 0` clean; zones up |
| 0b data plane | kernel can impair a slice | **pass** | 20 ms ± 5 ms delay, 1 % loss applied to a zone's `eth0` in gate 2 |
| 1 closed loop | target → zone bus → actuator → value back | **pass** | headlamp `0x180 01` → `0x181 01` in 29 ms; wiper `0x280 03`, tell-back climbing `03 00 → 03 50` |
| 2 failure matrix | isolation, restart, loss, concurrency, repeatability | **pass** | 150 records, 3 repetitions × 6 iterations, **0** cross-zone frames |
| 2b routed CAN | a frame crosses zones through a gateway | **pass** | 138 matched pairs at **0.79 / 0.77 ms** median; denied directions 10/0 and 10/0 on the wire |
| 3 ECU software | OpenBSW as an ECU on a virtual bus | **pass** | 450/450 build, `app.referenceApp.elf` 1 265 176 B; `10 03` → `50 03 00 32 01 F4` in 0.8 ms |
| 3b diagnostic across the router | a tester on one bus reaches an ECU on another | **pass** | 0.73 ms forward, 0.67 ms back, **2.5 ms** round trip; `0x558` refused every time |
| demo (this report) | one command reproduces all of it | **pass** | `results/20261115T005422Z-657d64c6/` |

## 4. The demo, measured

`checks/run_demo.sh` brings the vehicle up, primes both plants, captures four
buses plus the CAN-over-Ethernet datagrams, drives eight value changes per
function, sends one UDS session request from the front bus to the rear ECU, tears
down, and writes the archive.

From `20261115T005422Z-657d64c6` (60 s capture):

| claim | numbers |
|---|---|
| commands converge | 12/12 transitions, both functions |
| target → frame on the zone bus (S1) | headlamp **2.86 ms** (n=6), wiper **2.74 ms** (n=6) |
| frame on bus → status frame back (S2) | headlamp **65.50 ms**, wiper **70.18 ms** |
| status frame → app sees the value (S3) | headlamp **4.93 ms**, wiper **3.77 ms** |
| target → app sees it (total) | headlamp **75.23 ms**, wiper **81.30 ms** |
| routed status, zone to zone | front→rear **0.835 ms**, rear→front **0.782 ms**, n=**798** each |
| diagnostic through the gateway | request **0.827 ms**, response **0.651 ms**, 1 each way |
| policy on the wire | `0x180` denied 7× at the gateway, 0 on the rear bus; `0x280` denied 7×, 0 on the front bus |
| foreign frame refused | OpenBSW's `0x558` counter refused **91×** |
| packet capture | **6 500** datagrams of the bridge path |

Two things the table says that prose usually hides:

- **S2 is the status cadence, not the ECU.** The plants publish status every
  100 ms; the acknowledgement lands on the next periodic frame. That is why S2 is
  ~60–70 ms while S1 is ~3 ms.
- **S3 is bimodal.** Three of twelve rows read ~104 ms — the client's poll
  caught the value one status period later. The median over six is stable; a
  single run's S3 on its own is not a result.

## 4b. The Ethernet spine — first cut (B1, B2, B4)

The zone controllers now also expose a service on the spine: an event at 10 Hz and
one method at 2 Hz, speaking a DE4SDV-owned SOME/IP subset — the 16-byte header,
methods, events, static endpoints, no discovery ([`service/someip.py`](service/someip.py),
14 tests). Archive:
[`results/20261115T022118Z-04ee8739-backbone/`](results/20261115T022118Z-04ee8739-backbone/).

| claim | number |
|---|---|
| method round trip | **0.351 ms** median, p95 0.576 ms, max 6.508 ms (n=203) |
| event latency, provider stamp to client receipt | **0.260 ms** median, p95 0.376 ms, max 3.041 ms (n=1013) |
| event jitter | 0.499 ms (stdev of the inter-arrival gaps) |
| deadline misses, 50 ms | **0** |
| period misses, 1.5 × the 100 ms period | **0** |
| missing inside the observed sequence | **0**, across seq 1–1013 |
| window | 101.2 s |

Both endpoints are containers on one host and both stamps come from one clock, so
these are functional numbers, not production Ethernet numbers. The provider's log
and the client's are cut at different instants, which is why the table reports the
sequence span the client holds instead of comparing two line counts.

**B4, the regression gate:** the CAN demo re-ran on the same image that carries
the service — 12/12 commands converged, the diagnostic crossed the gateway, the
policy leaked nothing. The spine did not disturb the edge. Its summary is kept
under `results/20261115T022218Z-04ee8739-regression/`.

**B3**, the gate schedule, is §4c: rendered exactly as declared, and provably
inert on this traffic because nothing here crosses the gated port.

## 4c. The gate schedule — rendered, and inert where we can see it (B3)

`network.shaping` is in the experiment: a 10 ms cycle, the `adas` class open for
the first 5 ms, `infotainment` and unclassified traffic for the second. vxedge
rendered it exactly as declared, on the gateway uplink (host-level, `vxup0p` ↔
`vxup0`):

```text
qdisc taprio 100: dev vxup0 root refcnt 4 tc 3 map 0 1 2 0 0 0 0 0 0 0 0 0 0 0 0 0
queues offset 0 count 1 offset 1 count 1 offset 2 count 1
clockid TAI  base-time 0 cycle-time 10000000 cycle-time-extension 0
    index 0 cmd S gatemask 0x2 interval 5000000
    index 1 cmd S gatemask 0x5 interval 5000000
```

Three classes, one queue each, `clsact` in front of it, `pfifo` per class. The
declared windows are the rendered windows.

**It does nothing to the traffic this vehicle carries, and that is the finding.**
Every device sits on `vxbr0`; zone-to-zone service traffic never leaves the
bridge, so it never reaches the gated uplink. The A/B, same service, same host:

| | HTB (default) | gate schedule |
|---|---|---|
| method median | 0.351 ms (n=203) | 0.391 ms (n=120) |
| method p95 | 0.576 ms | 0.549 ms |
| event median | 0.260 ms (n=1013) | 0.233 ms (n=599) |
| event p95 | 0.376 ms | 0.362 ms |
| event max | 3.041 ms | 3.130 ms |
| jitter | 0.499 ms | 0.257 ms |
| misses | 0 of 1013 | 0 of 599 |

The differences are run-to-run noise in both directions, including one where the
gated run looks better. **Zero measurable effect is the correct reading**: the
gate is on a port this traffic never uses.

What the gate did show, at the gate itself: while the schedule was in force the
qdisc held packets in per-class queues — `87 pkt` sent, a `239p` backlog in the
`adas` class, `0` dropped, `0` requeues — while the other two classes drained.
So the schedule queues by class as designed.

**What could not be measured:** arrival timing behind the gate. The uplink is a
bridge port with no L3 peer (its far side is a veth with link-local addresses
only), so a probe sent across it enters the gate, is queued, and is delivered to
no receiver. `checks/gate_probe.py` is the tool for that measurement and it could
not complete here; the honest statement is that this topology has **no trunk**, and
a zonal E/E's TSN applies to the trunk. Gate timing needs a peer on the far side —
another host, a tunnel, or a device placed behind the uplink.

Archive: `results/20261115T022807Z-04ee8739-gate-schedule/`.

## 5. What the numbers do not say

- **Not a bus-latency measurement.** The providers are not instrumented: T1
  (provider receive) and T4 (provider publish) sit inside S1 and S3 by
  construction. Only S2 is purely a bus observation.
- **Not production Ethernet.** One host, two UDP hops, one userspace router, no
  switch, no PHY, no contending traffic. These are loopback-class numbers.
- **No arbitration, error frames or bit timing.** `vcan` models the frame flow,
  not the electrical bus.
- **No timing determinism.** Every process shares one kernel clock; scheduler
  jitter is real and unmeasured.
- **No time synchronisation is possible in this topology** — with one kernel
  there is only one clock to synchronise. Measured on two hosts: **0.198 ms**
  offset just after boot, **44 µs** once chrony converges, and PTP unicast locks
  but does not beat it — [`time-sync.md`](time-sync.md) has the numbers and what a
  cross-host claim would need.
- **Only a narrow Ethernet service plane.** The owned SOME/IP subset exercises
  static endpoints, methods and events. There is no service discovery, complete
  middleware implementation, physical switch/PHY, or inter-host trunk.
- **No safety, no security certification.** No secure boot, no MACsec, no IDS,
  no ASIL claim.

## 6. What broke while building it

These historical implementation problems informed the current recipes. This
list is not an assertion that every runtime or acceptance defect is closed.

| symptom | cause | fix |
|---|---|---|
| a zone died at boot, `vehicle status` still said up | the provider hit `connection refused` before the broker answered; the entrypoint treated any dead child as a dead zone | bounded 60 s wait on the broker port, provider supervised, only the plant exiting ends the zone |
| teardown hung forever | `wait` on a supervisor that restarts forever | stop flag, no `wait`; teardown returns |
| a broken package reported `succeeded` | the orchestrator has no health gate | our own probe on the zone's **own** status frame |
| the routed path read 25× slow | the first transport buffered 100 ms by default | selected a narrow single-frame `transport/bridge.py`; separate component licensing/provenance review remains necessary |
| `pkg lock` rejected the package id | the name after `/` must equal the experiment id | `id: de4sdv-virtual-ee` |
| `podman` refused the registry | plain HTTP to `localhost:5000` | `[[registry]] insecure = true` drop-in |
| a push left no local image | push goes to the registry, not to local storage | read the digest from the registry API |
| `vxota publish` failed with a bare ENOENT | `--signing-key` takes a **path**, the help implies a hex seed | pass the file |
| the OTA service exited in 2 s | no TUF root in the store | `vxota keygen` per checkout |
| `experiment up` could not reach the daemon | CLI defaults to `/run/vxedge.sock`, the user daemon listens under `XDG_RUNTIME_DIR` | resolve the endpoint, prove it answers |
| `up` failed after a failed run | an exited container keeps its name | remove `vx-*` exited containers before provisioning |

## 7. Licence position

The images contain GPL/LGPL and other third-party components. `python-can` is
imported by the Python application; Debian tools run as separate programs.
Neither Python imports nor container packaging remove the applicable obligations.

Removing cannelloni from the recipes removes that component, not every copyleft
component. The replacement's declared source licence is not proof of clean-room
authorship. [`versions.md`](versions.md) records the factual provenance boundary,
component licences and the review needed before distributing exact images.

[`sbom/`](sbom/README.md) describes digest-bound inventory generation. The original
zone-image-10 inventory is historical, not evidence for later zone images; quote
counts only from an inventory whose binding check passes for the current baseline.
An inventory is not legal clearance.

## 8. Reproducibility

**Rebuildable recipes, not a byte-reproducible build claim.** Application sources
and executable images have pins, but base-image tags and distribution package
resolution do not make the full build hermetic. Rebuilding may produce a different
image digest. A run must identify the resulting images, not assume equality.

The earlier archives carry short/stale or unknown Git identities and do not bind
all executed harness/configuration bytes. Preserve those identities as recorded.
New acceptance needs a committed checkout, full commit/tree identity, scoped
cleanliness, content-addressed runtime inputs, locked images and active deployment
identity, checked before and after execution.

**By public pull: no.** The registry is loopback-only, with private-CA TLS and
operator-owned authentication. The lab signing key and credentials stay on the
host. A third party builds and signs their own package; making images public is
a separate approval and distribution-compliance decision.

## 8b. State of this testbed

**The earlier closure claim is withdrawn pending repaired acceptance.** Required
closure is a fail-closed demo, policy-aware failure matrix, service-plane regression,
executed-byte identities, current digest-bound SBOMs and independent review.
Historical gate numbers alone do not close those obligations.

A trunk, OpenSOVD, device-side OTA/A-B banks and multi-host remain candidates,
not additions to this repair. External engagement is outside this change.

## 9. Recommended next step

**Multi-host is blocked, not skipped.** vxedge 0.30's daemon listens on `unix://`
only — "TCP+mTLS arrives with the auth work" — so a second host cannot join a
vehicle, and `network.time_sync` is single-host by construction. Waiting on that
is a platform dependency; faking it with a hand-assembled second host would
produce a topology the orchestrator does not know about.

**Time sync is settled as a measurement problem, not a deployment one.**
[`time-sync.md`](time-sync.md) measures both hosts: 0.198 ms offset just after
boot, 44 µs once chrony converges, and PTP unicast locks (16 µs median, 135 µs
tail) without beating the platform, because every timestamp here is software on a
virtual NIC. So the rule for any future cross-host run is: measure the offset in
the same window, state it, correct by it. No PTP service to operate.

The next action is **repair and rerun this increment**, not another feature.
First make the DBC/VSS restbus campaign independently reproducible: both directions,
repeated commands, outage/restart expectations, permitted and forbidden traffic,
and exact executed inputs. Only then consider a bounded interoperability campaign.

OpenSOVD, a device-side OTA client, A/B banks and multi-host stay deferred. None is
needed to establish whether this demonstrator's current verdicts are trustworthy.

SIL Kit and openDuT stay optional, with the triggers recorded in `landscape.md`.
