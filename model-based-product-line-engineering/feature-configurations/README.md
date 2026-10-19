# Feature Configurations

This directory contains Bills-of-Features (BoFs): validated selections for one
configured family member or candidate projection.

## Current configurations

| File | Family | Evidence status | Meaning |
|---|---|---|---|
| `aebs-autoware-linux-lidar-camera.yaml` | SDV product line | not declared | Standalone AEBS reference member (ADR 0014) |
| `middleware-autoware-aaos-sdv-reference.yaml` | SDV product line | `planned` | Planned AAOS-integrated middleware reference member (ADR 0014) |
| `example-linux-score-autoware.yaml` | SDV product line | not declared | Example platform projection |
| `apollo-qnx-qvm.yaml` | SDV product line | not declared | Example mixed-criticality platform projection |
| `fixtures/invalid-score-android.yaml` | SDV product line | invalid fixture | Deliberate C001 violation |
| `inc-aebs-009a-jetson.yaml` | Engineering environment | `inspected` | Exact maintained Jetson target; historical 009A run proved only Jetson 8 GiB identity |
| `apple-silicon-macos-candidate.yaml` | Engineering environment | `planned` | Unverified M-series/macOS candidate |
| `nxp-zephyr-vehicle-target-candidate.yaml` | Vehicle target | `planned` | Unverified unresolved NXP/Zephyr candidate |

`tested` requires retained repository evidence. `planned` means no execution
claim. Evidence status is metadata about the configuration, not a feature.

## Selection semantics

- Alternative groups select one child name as a scalar.
- OR groups select a non-empty YAML list.
- Optional/mandatory leaves use YAML Booleans.
- A mandatory leaf whose ancestors below the catalogue root are all mandatory
  counts as selected when the Bill-of-Features leaves it out, for the
  mandatory-leaf check and for the catalogue's constraints alike; setting it
  to `false` is a violation.
- Cross-tree compatibility rules reject structurally selectable but unsupported
  hardware/OS/runtime combinations.

The loader rejects duplicate keys, malformed shapes, invalid identifiers,
unknown statuses, and unsafe or missing evidence artifacts. Evidence-bearing
statuses may reference only direct, Git-tracked regular files inside the
repository; symbolic-link paths and repository metadata are rejected.

## PLEML configurations (fenced)

Each Bill-of-Features has a PLEML feature configuration with the same stem
in snake case (`aebs-autoware-linux-lidar-camera.yaml` restates as
`aebs_autoware_linux_lidar_camera.sysml`), and the fixture has one under
`fixtures/`, outside the authority roots. They are fenced until the switch
of [ADR 0022](../../docs/architecture-decisions/0022-adopt-pleml-as-product-line-authority.md);
until then the Bills-of-Features remain the selection authority, and their
`evidence` blocks stay here.

**Evidence records.** When the Bills-of-Features retire, the evidence of a
configuration moves to an external evidence record
`evidence/<file stem>.yaml`, for example `evidence/inc-aebs-009a-jetson.yaml`.
It keeps today's schema (`status`, plus `artifacts` with `id` and `path`) and
today's integrity rules. No record exists yet: a YAML file in this directory
is a Bill-of-Features until then.

## Creating a configuration

1. Choose the catalogue matching the correct family and System 1/System 2 role.
2. Copy a BoF from that family.
3. Select every mandatory decision.
4. Declare evidence honestly: use `planned` until retained evidence exists.
5. Validate and generate with `tools/configure_variant.py` and the catalogue's
   shared SysML asset.
