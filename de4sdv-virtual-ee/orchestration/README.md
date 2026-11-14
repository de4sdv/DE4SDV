# Ankaios spike — can it host the zonal E/E?

Ankaios v1.1.0 (Apache-2.0), run as server + one agent on the testbed host, hosting the
same three workloads the vxedge vehicle runs: `zone-fl`, `zone-rl`, `gateway`
([`ankaios-spike.yaml`](ankaios-spike.yaml)). The databroker was left out on purpose —
this is a bus-path and lifecycle comparison, not a VSS one.

## What Ankaios did

All three domains came up `Running(Ok)` within a second of `ank apply`, and the bus
behaved exactly as under vxedge:

| | front bus | rear bus |
|---|---:|---:|
| `0x180` headlamp command | 1 (local) | **0** |
| `0x181` headlamp status | 79 | 80 (routed in) |
| `0x280` wiper command | **0** | 1 (local) |
| `0x281` wiper status | 79 (routed in) | 80 |
| `0x558` OpenBSW counter | 0 | 8 |

The headlamp state reached `01` in 60 of those status frames after a single command,
so the plant, the bridge and the gateway policy all worked through Ankaios.

**Restart is declarative and stronger than ours.** Killing the plant made the zone exit
(our entrypoint's rule), and Ankaios recreated the workload on its own:

```text
23:16:12  Successfully created workload 'zone-fl'.
23:19:00  Successfully created workload 'zone-fl'.     ← after the plant was killed
```

vxedge leaves a dead zone dead until someone re-converges. That is a real advantage and
the one thing worth taking from this spike.

## What Ankaios does not do

It is a workload orchestrator, not a testbed platform. Everything below had to be
provided outside it, or does not exist:

- **Network fabric.** No namespaces, VLANs, queue trees or slices. The spike created a
  podman network (`10.100.0.0/24`) and static container IPs by hand, and passed
  `--cap-add=NET_ADMIN` through `commandOptions`. The zonal isolation in the vxedge
  vehicle is not reproducible from an Ankaios manifest.
- **Supply chain.** It runs whatever image the manifest names. There is no package
  digest, no signature, no trust policy — the three refusals the vxedge host makes
  (`LOCK_MISMATCH`, `SIGNATURE_INVALID`, unverified digest) have no equivalent.
- **Measurement.** No slices, traffic profiles, measurements, campaigns or result
  archives; nothing to compare runs with.
- **Structure.** One flat `workloads:` map. There is no separation of vehicle structure
  from software baseline, so an update is a manifest edit rather than a new signed
  package.

## Verdict

Adopt nothing wholesale. Ankaios is the credible production-shaped *lifecycle* layer and
vxedge is a research platform that also does networking, supply chain and measurement —
switching now would move one manifest into three systems and lose the guarantees this
directory spent its evidence on.

Two things are worth doing:

1. **Take the restart idea.** A zone's health should be a declared policy of the
   orchestrator, not a side effect of `tini` plus an `alive()` loop. That is a small,
   real improvement to `zones/entrypoint.sh`'s contract.
2. **If DE4SDV ever needs production orchestration, start the conversation with the
   Ankaios maintainers** before building on it — the same rule as every other upstream
   dependency here.

Recorded because it is evidence, not because the stack uses it: Ankaios is not a
dependency of this directory and nothing in `versions.md`'s stack table depends on it.
