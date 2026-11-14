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
dbc/headlamp.dbc              frame layout, VAL_ tables, comments
dbc/wiper.dbc
dbc/dbc_default_values.json   every signal of every transmitted frame (--dbc_default)
vss/mapping/vss_dbc.json      VSS tree + dbc2vss/vss2dbc per leaf (source of truth)
vss/mapping/headlamp.json     per-zone mapping, generated (a zone's provider gets only its own signals)
vss/mapping/wiper.json
vss/metadata.json             same tree, stripped: reference copy of what the broker holds
zones/Containerfile           zone image: provider at a pinned tag + plant model
zones/entrypoint.sh           creates this zone's vcan, runs provider + plant
zones/zone_ecu.py             headlamp/wiper plant, acknowledges the sequence
zones/dbc_feeder.ini          provider config, templated per zone
checks/check_contract.py      DBC ↔ mapping ↔ defaults consistency
checks/build_zone_mappings.py generates the per-zone mappings from the full tree
checks/test_zone_ecu.py       plant model and frame round-trip tests
```

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
