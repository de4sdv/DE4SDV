# Feature Configurations

This directory contains Bills-of-Features (BoFs): validated selections for one
configured family member or candidate projection.

## Current configurations

| File | Family | Evidence status | Meaning |
|---|---|---|---|
| `example-linux-score-autoware.yaml` | SDV product line | not declared | Example platform projection |
| `apollo-qnx-qvm.yaml` | SDV product line | not declared | Example mixed-criticality platform projection |
| `invalid-score-android.yaml` | SDV product line | invalid fixture | Deliberate C001 violation |
| `inc-aebs-009a-jetson.yaml` | Engineering environment | `inspected` | Exact maintained Jetson target; historical 009A run proved only Jetson 8 GiB identity |
| `apple-silicon-macos-candidate.yaml` | Engineering environment | `planned` | Unverified M-series/macOS candidate |
| `nxp-zephyr-vehicle-target-candidate.yaml` | Vehicle target | `planned` | Unverified unresolved NXP/Zephyr candidate |

`tested` requires retained repository evidence. `planned` means no execution
claim. Evidence status is metadata about the configuration, not a feature.

## Selection semantics

- Alternative groups select one child name as a scalar.
- OR groups select a non-empty YAML list.
- Optional/mandatory leaves use YAML Booleans.
- Cross-tree compatibility rules reject structurally selectable but unsupported
  hardware/OS/runtime combinations.

The loader rejects duplicate keys, malformed shapes, invalid identifiers,
unknown statuses, and unsafe or missing evidence artifacts. Evidence-bearing
statuses may reference only direct, Git-tracked regular files inside the
repository; symbolic-link paths and repository metadata are rejected.

## Creating a configuration

1. Choose the catalogue matching the correct family and System 1/System 2 role.
2. Copy a BoF from that family.
3. Select every mandatory decision.
4. Declare evidence honestly: use `planned` until retained evidence exists.
5. Validate and generate with `tools/configure_variant.py` and the catalogue's
   shared SysML asset.
