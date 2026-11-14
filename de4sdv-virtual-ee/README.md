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
vss/mapping/vss_dbc.json      VSS tree + dbc2vss/vss2dbc per leaf
vss/metadata.json             same tree, stripped: what the databroker is given
zones/Containerfile           zone image: provider at a pinned tag + plant model
zones/entrypoint.sh           creates this zone's vcan, runs provider + plant
zones/zone_ecu.py             headlamp/wiper plant, acknowledges the sequence
zones/dbc_feeder.ini          provider config, templated per zone
checks/check_contract.py      DBC ↔ mapping ↔ defaults consistency
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

## What this does not prove

No frame has yet crossed a real virtual bus to a real broker through this
contract; the provider and plant have not run together. The offline checks prove
the contract is consistent and the plant acknowledges correctly — nothing about
latency, ordering, or the databroker. Gate 1 evidence is the next step, and the
report must state the segment latencies rather than a single end-to-end number.
