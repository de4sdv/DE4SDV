# DE4SDV virtual E/E — the CAN signal contract

A zonal E/E topology that runs entirely in software, with a signal layer that is
**modelled before it is wired**: the DBC is the contract, the VSS mapping is the
interpretation, and the zone ECU is a plant that acknowledges what it was told.

This directory is the reference implementation of work items W3 and W4 of the
virtual E/E feasibility plan. The control-plane side (vxedge vehicle, gateway,
slices, zone provisioning) lives on the testbed host; what is versioned here is
everything that must survive the testbed.

## Signal contract

Two frames per ECU, request and status. Every status frame carries the sequence
number of the last accepted command, so an acknowledgement is a property of the
contract rather than of one implementation.

| Frame | ID | Direction | Signals | VSS leaf |
|---|---|---|---|---|
| `DE4SDV_Headlamp_Cmd` | `0x180` | central → front zone | `Headlamp_Low_Req`, `Headlamp_High_Req`, `Headlamp_Cmd_Seq` | `Vehicle.Body.Lights.Beam.{Low,High}.IsOn` (actuator target) |
| `DE4SDV_Headlamp_Status` | `0x181` | front zone → central | `Headlamp_Low_On`, `Headlamp_High_On`, `Headlamp_Fault`, `Headlamp_Seq_Ack` | same leaves (`value`), `Beam.{Low,High}.IsDefect` |
| `DE4SDV_Wiper_Cmd` | `0x280` | central → rear zone | `Wiper_Mode_Req`, `Wiper_Interval_ms`, `Wiper_Cmd_Seq` | `Vehicle.Body.Windshield.Front.Wiping.Mode` |
| `DE4SDV_Wiper_Status` | `0x281` | rear zone → central | `Wiper_Mode_State`, `Wiper_Position_pct`, `Wiper_Position_Reached`, `Wiper_Error`, `Wiper_Seq_Ack` | `Wiping.Mode` (`value`), `Wiping.System.ActualPosition`, `Wiping.System.IsPositionReached`, `Wiping.System.IsWiperError` |

Three deliberate choices:

- **The upstream demo codec is replaced, not described.** The SDV simulation's
  CMD/ACK/NACK byte protocol is a private format for a demo binary; here the
  layout is the DBC, so a different toolchain can implement the same ECU. The
  upstream binaries are therefore not used, patched or forked.
- **Tell-back exists.** The reference wiper never acknowledges anything. Here
  `Wiper_Position_Reached` and every `*_Seq_Ack` make the acknowledgement
  observable on the bus, which is what makes a timed closed loop measurable.
- **Sequence and interval counters stay off the VSS tree.** `*_Seq`, `*_Seq_Ack`
  and `Wiper_Interval_ms` are bus-level facts observed in traces. Mapping every
  DBC signal onto a VSS path would invent vehicle signals that do not exist.

## Files

```text
versions.md                   pins and licences of every upstream component
dbc/headlamp.dbc              frame layout, VAL_ tables, comments
dbc/wiper.dbc
dbc/dbc_default_values.json   every signal of every transmitted frame (--dbc_default)
vss/mapping/vss_dbc.json      VSS tree + dbc2vss/vss2dbc per leaf (source of truth)
vss/mapping/headlamp.json     per-zone mapping, generated (a zone's provider gets only its own signals)
vss/mapping/wiper.json
vss/metadata.json             same tree, stripped: reference copy of what the broker holds
zones/Containerfile           zone image: provider at a pinned tag + plant model + bridge + reference ECU
gateway/Containerfile         central gateway image: bridge + router
transport/bridge.py           CAN over UDP: fixed framing, one frame per datagram
gateway/router.py             per-frame allow-list between two zone buses
gateway/entrypoint.sh         creates both buses, starts the bridges and the router
zones/entrypoint.sh           creates this zone's vcan, waits for the broker, runs provider + plant
zones/zone_ecu.py             headlamp/wiper plant, acknowledges the sequence
zones/dbc_feeder.ini          provider config, templated per zone
checks/check_contract.py      DBC ↔ mapping ↔ defaults consistency
checks/build_zone_mappings.py generates the per-zone mappings from the full tree
checks/test_zone_ecu.py       plant model and frame round-trip tests
checks/test_bridge.py         bridge framing: round-trip, padding, malformed input
checks/update_with_rollback.sh  apply a package, gate on the zone working, roll back if it does not
checks/make_sbom.sh           regenerate the committed CycloneDX SBOMs from the images
checks/run_demo.sh            one command: up, capture, drive, diagnose, tear down, archive
checks/demo_measure.py        the archive's numbers: segments, routed pairs, leaks
checks/timesync_probe.py      clock offset between two hosts, four-timestamp exchange
time-sync.md                  what a cross-host time claim costs, measured, with PTP tried
results/                      the committed demo archive, with its own manifest
REPORT.md                     the feasibility report: gates, demo numbers, limits
sbom/                         CycloneDX 1.7 for both images, gzipped, plus how to regenerate
upstream-reports/             two upstream defects, drafted and not filed
orchestration/                Ankaios spike: the same workloads under a second orchestrator
landscape.md                  all 37 Eclipse SDV projects: use, track, or skip, with reasons
vehicle/vehicle.yaml          the vehicle composition: zones, devices, links, services
vehicle/parts.yaml            the software baseline: images, capabilities, per-zone env
vehicle/main.yaml             the experiment: slices, what is under test, method
vehicle/vxp.yaml, vxp.lock    the package descriptor and its lock (five files pinned)
deploy/README.md              lock, sign, verify, run — and what the host refuses
deploy/trust.yaml.example     the host policy: require signed packages
deploy/systemd/vxedged.service  the daemon as a user unit
deployment-gaps.md            the deployment plane a production SDV needs, and what is missing here
```

`vehicle/` is a `vxp/1` package, not a folder of documents: it is locked, packed to
`sha256:45ac175e…`, signed with a lab key, and the host runs it only because the
policy found that verification record. Its two images are pinned by digest from a
registry on the host, and a moved tag does not change what runs. That registry is a
lab fixture on loopback with no auth, so the refs are not publishable as they stand
— [`deployment-gaps.md`](deployment-gaps.md) says what publishing would need.

`vss/metadata.json` is generated from the mapping by stripping `dbc2vss` and
`vss2dbc`; the two must never be edited apart.

## Run the offline checks

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r de4sdv-virtual-ee/checks/requirements-dev.txt
python de4sdv-virtual-ee/checks/check_contract.py
python de4sdv-virtual-ee/checks/test_zone_ecu.py
```

`check_contract.py` proves the four-way consistency: both DBCs parse, every
mapping signal exists, the defaults cover every frame the provider may transmit,
and every enumerated VSS leaf agrees with the DBC `VAL_` table it is fed from.

## Run it on the testbed

The zone needs `CAP_NET_ADMIN` to create its own bus. That is granted per part in
the vxedge baseline, not by the image:

```yaml
kind: baseline
parts:
  - ref: localhost/de4sdv/zone-ecu:1
    target_ids: [fn-fl]
    run:
      cap_add: [NET_ADMIN]
      env: { ZONE_ECU: headlamp, ZONE_DBC: /opt/zone/dbc/headlamp.dbc }
```

Build the image from this directory:

```bash
podman build -f de4sdv-virtual-ee/zones/Containerfile -t localhost/de4sdv/zone-ecu:1 de4sdv-virtual-ee
```

## Run the demo

One command produces the whole thing: bring the vehicle up, prime both plants,
capture four buses and the CAN-over-Ethernet datagrams, drive eight value
changes per function, send one diagnostic from the front bus to the rear ECU,
tear down, and score the run.

```bash
de4sdv-virtual-ee/checks/run_demo.sh            # ~90 s, exit code is the verdict
de4sdv-virtual-ee/checks/run_demo.sh --keep     # leave the vehicle up to look at it
```

It writes `results/<utc>-<sha>/` with `manifest.json` (sha, lock hash, image
digests, OTA root), four `candump` traces, `slice.pcap`, `commands.jsonl`,
`uds.txt`, the container logs, `gateway-stats.txt`, and `summary.json`/`.txt`.
It exits non-zero if a denied frame crossed, nothing converged, or the
diagnostic did not come back. A committed run is under `results/`, and
[`REPORT.md`](REPORT.md) reads it.

## Gate 1 result (testbed, 2026-11-14)

The loop closed on a `vx-de4sdv-ee` vehicle (Ubuntu 24.04, kernel 7.0.0-1017-gcp,
vxedge 0.30.0): three container zones, two VLAN slices, KUKSA on the central node.

- **Headlamp**: target `Low.IsOn=true` → `0x180 01` on the front zone's bus →
  `0x181 01` 29 ms later → broker value `True`.
- **Wiper**: target `Mode=FAST` → `0x280 03` → status payloads climbing
  `03 00 → 03 14 → 03 28 → 03 3C → 03 50` (position 0 → 80 %) → broker value `FAST`.
- **Cross-zone leakage**: 0 headlamp frames on the wiper bus, 0 wiper frames on the
  headlamp bus, in both directions.

What that does not cover: per-segment latency (T0–T5), restart and loss behaviour,
concurrent commands, and repeatability. Those are gate 2, and their numbers belong
in a table with sample counts, not in prose.

## Gate 2 result — failure matrix (testbed, 2026-11-14)

3 repetitions per scenario, 6 iterations per repetition per arm, 150 records.

| scenario | arm | n | converged | S1 med/p95 ms | S2 med/p95 ms | S3 med/p95 ms |
|---|---|---:|---:|---|---|---|
| baseline | headlamp | 18 | 18/18 | 3.49 / 4.35 | 26.59 / 82.94 | 6.40 / 106.06 |
| baseline | wiper | 18 | 18/18 | 3.34 / 4.12 | 59.50 / 88.07 | 6.17 / 105.98 |
| concurrency | headlamp | 18 | 18/18 | 3.34 / 4.51 | 68.99 / 93.68 | 6.08 / 106.80 |
| concurrency | wiper | 18 | 18/18 | 3.65 / 6.08 | 41.26 / 95.68 | 7.70 / 107.73 |
| impairment | headlamp | 18 | 18/18 | 3.20 / 4.09 | 55.58 / 84.17 | 29.77 / 134.81 |
| impairment | wiper | 18 | 18/18 | 3.18 / 4.90 | 27.57 / 83.12 | 26.27 / 164.73 |
| linkloss down | headlamp | 3 | 0/3 | — | — | — |
| linkloss up | headlamp | 18 | 18/18 | 3.15 / 3.49 | 38.19 / 83.83 | 4.72 / 105.62 |
| restart down | headlamp | 3 | 0/3 | — | — | — |
| restart up | headlamp | 18 | 18/18 | — | — | — |

**Cross-zone frames observed on the wrong bus: 0** across all 150 records.

Four things these numbers say, and one they refuse to say:

1. **S2 is the status period, not the ECU.** Median 26–69 ms with p95 near 85–95 ms
   against a 100 ms status period: the acknowledgement lands on the next periodic
   status frame, not on an event. The loop is faster than the contract's reporting
   cadence; an immediate status-on-command would cut S2 to S1's scale.
2. **Impairment moves S3 and nothing else.** 20 ms ± 5 ms delay and 1 % loss on the
   zone's `eth0` took S3 from 6.2 ms to ~28 ms while S1 stayed at 3.2 ms. That is
   scope A's honest claim, measured: only gRPC crosses the slice; the CAN bus is
   zone-local.
3. **Failure is detectable by timeout, and recovery is automatic.** With the zone
   stopped or its link down, the value never converged (0/3); after recovery 18/18
   converged. No silent staleness.
4. **Concurrency costs nothing measurable.** Both ECUs commanded at the same
   instant: 18/18 each, S1 unchanged.

What the numbers refuse to say: nothing here is a bus-latency measurement. T1
(provider receive) and T4 (provider publish) happen inside `kuksa-can-provider`
and are not instrumented; they sit inside S1 and S3 by construction. Caveats that
travel with every cell: one host, generic kernel, userspace timestamps
(`candump` realtime vs `time.time()`), 2 ms poll granularity on t5.

## Gate 2b result — CAN routed over the vehicle Ethernet (testbed, 2026-11-14)

The buses meet at a gateway that decides what may cross:

```text
zone-fl vcan0 ──DE4SDV bridge, UDP over the adas slice──▶ central vcan-front
                                                          │  router allow-list
                            zone-rl vcan0 ◀──UDP─────────── vcan-rear
```

Policy is per frame, not per link: `0x181` (headlamp status) may be published
rear-ward, `0x180` (headlamp command) may not; `0x281` (wiper status) travels
front-ward, `0x280` (wiper command) does not. A zone observes its neighbours; no
zone actuates another's hardware.

The transport is [`transport/bridge.py`](transport/bridge.py): one CAN frame
becomes one UDP datagram, fixed 17-byte framing, no batching. It exists because
the first pass used a GPL-2.0 third-party tunnel, and an image we might publish
should not carry copyleft to move bytes. Every measurement below is that bridge.

| transport | direction | pairs | median | min / max |
|---|---|---:|---|---|
| DE4SDV bridge | headlamp status front→rear | 138 | **0.79 ms** | 0.57 / 2.63 |
| DE4SDV bridge | wiper status rear→front | 138 | **0.77 ms** | 0.49 / 2.58 |

A pair is one frame seen on both buses, matched by payload; the delta is taken
between the two `candump -ta` stamps on the same host clock. 139 and 140 status
frames were published in the window, so the pairing covered all but one or two.

Denied directions, counted on the wire and at the gateway: **10** command frames
of `0x180` on the front bus, **0** on the rear; **10** of `0x280` on the rear,
**0** on the front. The gateway's own counters, printed when it was stopped:

```text
front->rear.denied.0x180     21
front->rear.forwarded.0x181  1816
rear->front.denied.0x280     20
rear->front.forwarded.0x281  1815
```

### What the replaced tunnel would have taught us

The first pass used cannelloni, and its numbers are kept because the lesson is
about measurement, not about that project:

| configuration | direction | n | median | min / max |
|---|---|---:|---|---|
| default buffer (100 ms) | headlamp status front→rear | 5 | 77.71 ms | 28.90 / 159.33 |
| default buffer (100 ms) | wiper status rear→front | 5 | 52.02 ms | 23.44 / 94.34 |
| explicit 1 ms timeout | headlamp status front→rear | 8 | 2.96 ms | 1.78 / 3.18 |
| explicit 1 ms timeout | wiper status rear→front | 8 | 2.99 ms | 2.76 / 3.58 |

A routed-path number is only as meaningful as the transport's buffering. The
default held frames for 100 ms and made the gateway look 25× slower than it was;
the same topology read 3 ms with the timeout set. The bridge has no such knob,
which is why it cannot be silently misconfigured into a 100 ms path.

Caveat that travels with every row: two UDP hops and one userspace router on one
host — no switch, no PHY, no contending traffic. These are not production
Ethernet numbers.

## Gate 3 result — OpenBSW POSIX as a zonal ECU (testbed, 2026-11-14)

Eclipse OpenBSW's reference application built and ran as an ECU on a virtual bus.

| Step | Result |
|---|---|
| Build (`cmake --preset posix-freertos`) | 450/450 targets, exit 0 · `app.referenceApp.elf`, 1 265 176 bytes |
| Lifecycle | runs level by level, `Initialize level 1 done current=0 target=9`, independently of any other process |
| Addressing | DoCAN, ISO 15765-4 OBD — tester `0x7E0`, ECU `0x7E8` |
| UDS | request `7E0 02 10 03` → response `7E8 06 50 03 00 32 01 F4` in 0.8 ms |

`0x50` is the positive DiagnosticSessionControl response; `0x0032` and `0x01F4`
are the ECU's P2 (50 ms) and P2* (500 × 10 ms) session timings. The 0.8 ms is one
exchange on a virtual bus, not a latency distribution — the gate-2 harness is what
produces those.

What this section did not yet show: the ECU sitting behind the gateway. It ran
on the testbed host's own `vcan0`, beside the vehicle rather than inside it.
[Gate 3b](#gate-3b-result--the-diagnostic-crosses-the-routed-path-testbed-2026-11-14)
closes that. The plan's "light state machine" is covered by this directory's own
plant model, not by OpenBSW's demo routines.

## Gate 3b result — the diagnostic crosses the routed path (testbed, 2026-11-14)

The reference ECU now lives inside the rear zone container, on the same bus as
the wiper plant — a zonal controller hosting several functions, which is what
that image is for. Only a zone started with `ZONE_UDS_ECU=1` runs it.

A tester on the **front** bus sends a single-frame UDS request. Nothing else in
the topology changes:

```text
front vcan0   7E0  02 10 03                                   ← tester
                    │  bridge → gateway, policy 0x7E0 front→rear
rear  vcan0        7E0  02 10 03                  +0.73 ms
                    OpenBSW reference ECU answers
rear  vcan0        7E8  06 50 03 00 32 01 F4 CC
front vcan0   7E8  06 50 03 00 32 01 F4 CC        +0.67 ms back, 2.5 ms round trip
```

| claim | evidence |
|---|---|
| the request crossed | 1 frame of `0x7E0` on each bus, forward in **0.73 ms** |
| the answer came back | 1 frame of `0x7E8` on each bus, `06 50 03 00 32 01 F4 CC`, back in **0.67 ms** |
| the gateway did it | `front->rear.forwarded.0x7E0 2`, `rear->front.forwarded.0x7E8 2` |
| actuators are still refused | probe `0x180` on the rear bus: none on the front, `rear->front.denied.0x180 1` |

The 2.5 ms round trip is the two forwarded hops plus the ECU's own processing; the
0.73/0.67 ms figures are the hops alone.

One frame the contract does not define: the reference app publishes `0x558`, four
bytes with an incrementing counter, about once a second. The policy has no row for
it, so it was refused and never reached the front bus — an allow-list refusing an
ECU's own demo frame is the policy working. A blocklist would have leaked it.

Building OpenBSW inside the image cost two toolchain facts worth keeping: the
presets need CMake ≥ 3.28.3 (bookworm ships 3.25, so the build stage pins it from
pip), and the code generators run the image's `/usr/local/bin/python3.12`, which
cannot see Debian's apt packages — `pyyaml`, `jinja2` and `jsonschema` come from
pip at the versions the testbed used.

## Findings from the routed run

Two more defects were only visible once the buses were actually joined:

1. **A zone died on a boot-order race.** The front zone's provider started before
   KUKSA answered and hit `connection refused`; the entrypoint treated any dead
   child as a dead zone and tore it down. The vehicle came up reporting three
   zones while one was silent — the failure mode a zonal architecture must not
   have. Fixed: the entrypoint waits (up to 60 s) for the broker's port, and the
   provider is supervised and restarted, so only the plant exiting takes a zone
   down.
2. **A short command frame is rejected, and that is correct.** `cansend` with a
   one-byte payload produced `undecodable command frame` and the plant kept its
   state: cantools refuses a frame shorter than the DBC message. Commands carry
   the full 8 bytes. Worth knowing before concluding that a plant "ignores" the
   bus.

## Findings from the first run

Four defects were only visible with the pieces actually running:

1. `Message.encode(..., choices=True)` — cantools has no such kwarg; drop it.
2. The provider's flag is `--dbc-default`, not `--dbc_default`.
3. `val2dbc = True` in the ini did not enable the direction in 0.5.1; pass
   `--val2dbc` explicitly.
4. **One mapping per zone.** A provider given the full tree rejects every leaf owned
   by another zone (`mapped to CAN signal … not used in any message definition`).
   `checks/build_zone_mappings.py` generates them from the single source tree.

A fifth was a real crash: decoding with `decode_choices=True` feeds the plant a
`NamedSignalValue`, and an `int()` on it kills the ECU on the first enumerated
command. The plant now accepts both forms and a test pins that behaviour.

The broker runs vxedge's own full VSS 6.0 metadata (`vss_release_6.0.json`), not
this directory's `metadata.json`; the file is kept as the reference of what this
contract expects the tree to contain.
