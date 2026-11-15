# Ethernet backbone increment — scope

Status: **scoped, not started.** This is the next increment for the virtual E/E
testbed. It adds the one architectural layer the testbed does not have.

## Why this, and not another feature

The testbed proves a zonal **CAN** architecture: per-zone buses, a policy
gateway, an ECU answering diagnostics through it. What a production zonal E/E
adds on top is an **Ethernet spine** carrying service traffic between the HPC and
the zone controllers, with CAN surviving only at the zone edge.

Today the only thing crossing a slice is KUKSA gRPC — the topology diagram in
[`README.md`](README.md) says so. That means the architecture we simulate has no
service plane, no TSN scheduling on the spine, and no place for a diagnostics
protocol that is not CAN-based. Those are architecture decisions a simulation is
supposed to test before hardware exists.

## What it builds on (verified on the testbed, 2026-11-15)

- **TSN is available.** Kernel `7.0.0-1017-gcp`: `modprobe sch_taprio` succeeds
  (49 152 B), and a gate schedule renders on a veth created with 8 tx queues —
  `num_tc 3`, `map 0 1 2 …`, `queues 2@0 2@2 2@4`, 1 ms cycle, two 500 µs
  windows. Recorded warning: *"Size table not specified, frame length estimations
  may be inaccurate"* — so gate timing is approximate for frame transmission.
- **vxedge renders it.** `network.shaping: { kind: gate-schedule, windows: [...] }`
  becomes a `taprio` qdisc on the gateway uplink (`gateway/provision.rs`,
  `taprio_args`), up to 7 shaped slices plus `default`, and the package loader
  refuses a manifest whose kernel cannot run `taprio`.
- **The data plane can be OVS** (`network.data_plane: ovs`) instead of a kernel
  bridge.
- **Our CAN edge is unaffected**: gateway policy, plants, OpenBSW ECU and the demo
  harness all stay as they are.
- **`channels:` is declarative only** — protocol and QoS are parsed and never
  consumed ([`upstream-reports/`](upstream-reports/README.md), report 3). The
  increment must not attribute any measurement to a declared channel QoS.

## The decision this increment needs first

Which service protocol rides the spine:

| option | what it gives | what it costs |
|---|---|---|
| **A. Minimal DE4SDV SOME/IP subset** (recommended) | The 16-byte SOME/IP header, method request/response, event notification, static endpoints. Owned, Apache-2.0, ~400 lines with tests, wire format inspectable on the capture | No service discovery, no E2E protection, no full stack |
| B. [vsomeip](https://github.com/COVESA/vsomeip) (MPL-2.0, active) | Full SOME/IP including service discovery; a real implementation to compare against | Weak-copyleft dependency, a stack we do not control, and its behaviour becomes ours to explain |
| C. Plain UDP with a declared channel | Cheapest by far | Proves nothing about a service-oriented architecture |

**Recommended: A.** It follows the same reasoning as the CAN transport — own the
codec rather than inherit a licence and a behaviour — and it keeps the increment
about the architecture rather than about integrating a stack. The trade is stated
plainly: **static endpoints, no discovery**, so the increment proves the message
plane and the scheduling, not dynamic service lookup.

## Topology it targets

```text
        hpc1 ── service provider (vehicle state events + one control method)
          │        adas vlan 101, spine, 802.1Qbv gate schedule on the uplink
   ┌──────┴──────┐
 zone-fl        zone-rl ── clients: subscribe to state, call the method
   │                │
 vcan0           vcan0 ── the existing CAN edge, unchanged:
   headlamp        wiper + OpenBSW ECU, behind the policy gateway
```

Two planes, measured separately: service traffic on the spine, CAN frames at the
edge. The gateway keeps deciding what crosses, exactly as now.

## Gates

| gate | what it has to show | pass criterion |
|---|---|---|
| **B0** feasibility *(done)* | the host can render a gate schedule and vxedge accepts the block | `tc qdisc show` carries `taprio` with the declared windows; a kernel without `sch_taprio` fails `vxp lock` |
| **B1** spine | service traffic crosses the Ethernet spine | method call returns and an event is delivered to both zone clients, n ≥ 100 |
| **B2** service measurement | latency and jitter with sample counts | method RTT and event latency reported as median/p95/max, n ≥ 200, plus deadline misses |
| **B3** TSN | the gate schedule changes something measurable, or provably does not | qdisc rendered with the declared windows; A/B against the HTB baseline with both numbers stated |
| **B4** regression | the CAN edge is untouched | `checks/run_demo.sh` still exits 0 on the same archive shape |
| **B5** honesty | limits written down before the numbers | no switch, no PHY, software timestamps, no service discovery, no E2E, one host |

## Risks, with the mitigation each needs

- **Gate schedule on a veth in software mode** — no size table, so frame
  transmission time is estimated. State it, and prefer measuring latency over
  claiming a schedule is met to the microsecond.
- **`taprio` and the HTB tree cannot stack** — vxedge refuses to render over an
  uplink that already has a qdisc. The experiment declares one or the other.
- **VLAN and traffic classes interact** — the schedule maps classes, the slices
  map VLANs. Verify the mapping on the wire before trusting a latency difference.
- **Declared channel QoS means nothing** — do not build a claim on `channels:`.
- **Static endpoints** — no discovery; a moved service is a config change and must
  be recorded as such.

## Deliverables

1. `service/` — the SOME/IP subset, its tests, and a capture proving the header on
   the wire.
2. Backbone parts in `vehicle/parts.yaml`, the spine links in `vehicle/vehicle.yaml`,
   the gate schedule in `vehicle/main.yaml`.
3. `checks/backbone_measure.py` — method RTT, event latency/jitter, deadline misses.
4. One archive under `results/` from a scripted run, in the shape the demo already
   writes.
5. A section in [`REPORT.md`](REPORT.md) with the gate table and the numbers, and a
   `## What this does not prove` written before the numbers are read.

## Effort

Two focused sessions: service plus spine plus B1/B2; then TSN plus B3 plus the
regression run and the report. A third if the gate schedule needs tuning against
the kernel's behaviour.
