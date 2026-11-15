# Virtual E/E — feasibility report

What was built, what it proves, what it does not. Every number here has a
sample count and an archive behind it. Written against the success definition in
the feasibility plan: a zero-licence-cost, reproducible, functional
software-in-the-loop zonal demonstrator, with an honest statement of what each
gate did and did not prove.

Date: 2026-11-15. Testbed: GCP `e2-standard-4`, Ubuntu 24.04, kernel
7.0.0-1017-gcp, vxedge 0.30.0, rootless Podman.

## 1. Verdict

**The architecture works and the gates pass. The demonstrator is real but
narrow: one host, CAN only, containers on one kernel.**

- Functional: both functions close the loop through the signal plane, one
  diagnostic crosses a policy gateway to an ECU in another zone, and nothing
  crosses that the policy denies.
- Cost: **≈ €0.75** of compute so far (a test day is ~€1.50), **€0** of software licences. No copyleft in
  code DE4SDV writes or links (see §7 for the precise claim).
- Reproducible **by rebuild**, not by pull: every input is pinned and every
  image is built from a pinned commit, but the images live in a loopback
  registry, so a stranger cannot `experiment up` this package without building
  it first (§8).
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

## 3. Gates

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
  there is only one clock to synchronise. gPTP across nodes needs separate
  kernels (§9).
- **No Ethernet backbone, no SOME/IP, no service discovery.** The vehicle network
  modelled here is CAN plus VLAN-separated IP.
- **No safety, no security certification.** No secure boot, no MACsec, no IDS,
  no ASIL claim.

## 6. What broke while building it

Each of these cost real time; all are fixed and visible in the code.

| symptom | cause | fix |
|---|---|---|
| a zone died at boot, `vehicle status` still said up | the provider hit `connection refused` before the broker answered; the entrypoint treated any dead child as a dead zone | bounded 60 s wait on the broker port, provider supervised, only the plant exiting ends the zone |
| teardown hung forever | `wait` on a supervisor that restarts forever | stop flag, no `wait`; teardown returns |
| a broken package reported `succeeded` | the orchestrator has no health gate | our own probe on the zone's **own** status frame |
| the routed path read 25× slow | the first transport buffered 100 ms by default | wrote `transport/bridge.py`: one frame, one datagram, no buffer knob (and no GPL) |
| `pkg lock` rejected the package id | the name after `/` must equal the experiment id | `id: de4sdv-virtual-ee` |
| `podman` refused the registry | plain HTTP to `localhost:5000` | `[[registry]] insecure = true` drop-in |
| a push left no local image | push goes to the registry, not to local storage | read the digest from the registry API |
| `vxota publish` failed with a bare ENOENT | `--signing-key` takes a **path**, the help implies a hex seed | pass the file |
| the OTA service exited in 2 s | no TUF root in the store | `vxota keygen` per checkout |
| `experiment up` could not reach the daemon | CLI defaults to `/run/vxedge.sock`, the user daemon listens under `XDG_RUNTIME_DIR` | resolve the endpoint, prove it answers |
| `up` failed after a failed run | an exited container keeps its name | remove `vx-*` exited containers before provisioning |

## 7. Licence position

Not "GPL-free". The accurate claim:

- **No copyleft in code DE4SDV writes or links.** The one copyleft component in
  the first pass (a GPL-2.0 CAN tunnel) was removed and replaced with our own
  transport.
- Imported LGPL: `python-can` (LGPL-3.0), dynamically, unmodified.
- Unmodified GPL programs used as tools: `iproute2`, `can-utils`, `git`.
- `libstdc++6` under GPL-3.0 **with the GCC runtime exception**.

Per-image component counts and the licence distribution are in `sbom/`
(CycloneDX 1.7: 5 427 components for the zone image, 3 474 for the gateway).

## 8. Reproducibility

**By rebuild: yes.** The lock pins five images by digest, the container files pin
their upstream commits, `versions.md` records every version and licence, and the
demo's `manifest.json` records the lock hash, the OTA root and every image digest
for the run it belongs to.

**By pull: no.** `localhost:5000` is a loopback registry without authentication
and the package is signed with a lab key that stays on the testbed. A third party
rebuilds from source; they cannot pull our artifacts. That is a deliberate lab
fixture, not an oversight — publishing them is a separate decision with a cost
and an owner.

## 9. Recommended next step

**Multi-host, with gPTP.** Distribution is the one gap that changes what the
numbers mean: two hosts have two clocks, which makes time synchronisation real
instead of theatre, and it exercises the transport in the configuration it was
designed for. It also removes the single-kernel caveat from §5.

Concretely: one zone on a second VM, gateway on the first, the bridge over the
tunnel, `network.time_sync: { kind: gptp, followers: [...] }` on the experiment,
and an A/B: offsets with time sync off, then on, plus a re-run of the routed
latency with node-side timestamps.

After that, in order of value: **OpenSOVD** for the diagnostic surface (our
gateway already proves the path a real SOVD server would use), then the OTA
client gap, then A/B banks. SIL Kit and openDuT stay optional, with the triggers
recorded in `landscape.md`.
