# Feature Configurations

This directory holds the PLEML feature configurations of the product line,
the configuration authority since the switch of
[ADR 0022](../../docs/architecture-decisions/0022-adopt-pleml-as-product-line-authority.md):
each is a selection of features that describes one configured family member
or candidate projection. Beside each one, its Bill-of-Features (BoF) is the
**non-authoritative shadow** until the YAML retires (ADR 0022, step S7), and
it carries the configuration's evidence record until then.

## Current configurations

| Configuration | Bill-of-Features (shadow) | Family | Evidence status | Meaning |
|---|---|---|---|---|
| `aebs_autoware_linux_lidar_camera.sysml` | `aebs-autoware-linux-lidar-camera.yaml` | SDV product line | not declared | Standalone AEBS reference member (ADR 0014) |
| `middleware_autoware_aaos_sdv_reference.sysml` | `middleware-autoware-aaos-sdv-reference.yaml` | SDV product line | `planned` | Planned AAOS-integrated middleware reference member (ADR 0014) |
| `example_linux_score_autoware.sysml` | `example-linux-score-autoware.yaml` | SDV product line | not declared | Example platform projection |
| `apollo_qnx_qvm.sysml` | `apollo-qnx-qvm.yaml` | SDV product line | not declared | Example mixed-criticality platform projection |
| `fixtures/invalid_score_android.sysml` | `fixtures/invalid-score-android.yaml` | SDV product line | invalid fixture | Deliberate C001 violation |
| `inc_aebs_009a_jetson.sysml` | `inc-aebs-009a-jetson.yaml` | Engineering environment | `inspected` | Exact maintained Jetson target; historical 009A run proved only Jetson 8 GiB identity |
| `apple_silicon_macos_candidate.sysml` | `apple-silicon-macos-candidate.yaml` | Engineering environment | `planned` | Unverified M-series/macOS candidate |
| `nxp_zephyr_vehicle_target_candidate.sysml` | `nxp-zephyr-vehicle-target-candidate.yaml` | Vehicle target | `planned` | Unverified unresolved NXP/Zephyr candidate |

`tested` requires retained repository evidence. `planned` means no execution
claim. Evidence status is metadata about the configuration, not a feature.

The receipts of the feature models record each configuration's verdict, its
derived variants and its admission by the governed scope. A configuration can
be valid without being admitted: of the seven configurations above, the
fixture aside, the two reference members are admitted.

## PLEML configurations

Each configuration is a `#featureConfiguration` typed by the feature tree of
its feature model, in a file of its own with the stem of its Bill-of-Features
in snake case. A selected feature is a `[1]` redefinition, a deselected one a
`[0]` redefinition, and an unset feature is not selected; the value of a group
names its chosen member. The configuration owns only features: a derived
variant, such as the application-middleware adapter, is never selected here.
Its doc is the description, and it owns its projection name, the name of the
part definition its product-model projection declares.

The fixtures under `fixtures/` (the invalid configuration and the parity
probes) are never configurations of the product line: the authority job
validates and serializes them into the receipts, and no production selector
reads them. The export, the API baseline, the served model and its drift
gate, the licensed validation, the repository and naming checks and the
viewer leave them out, and receipt mode never projects them.

## Selection semantics of the Bills-of-Features (shadow)

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

## Fixtures and evidence records

**Parity probes.** `fixtures/parity-probes/` holds one PLEML configuration
per probe row of the parity check of step S4
([`check_pleml_parity.py`](../../scripts/check_pleml_parity.py)). They have
no Bill-of-Features: the check generates each probe's bill from its frozen
selection outside the repository.

**Evidence records.** When the Bills-of-Features retire, the evidence of a
configuration moves to an external evidence record
`evidence/<file stem>.yaml`, for example `evidence/inc-aebs-009a-jetson.yaml`.
It keeps today's schema (`status`, plus `artifacts` with `id` and `path`) and
today's integrity rules. No record exists yet: a YAML file in this directory
is a Bill-of-Features until then.

## Creating a configuration

1. Choose the feature model of the correct family and System 1/System 2 role.
2. Copy a configuration of that family, and its Bill-of-Features until the
   YAML retires.
3. Select every mandatory feature, in both.
4. Declare evidence honestly in the Bill-of-Features: use `planned` until
   retained evidence exists.
5. Open a pull request. The privileged PLE authority workflow validates and
   serializes the configuration and writes fresh receipts; commit them from
   its artifact. A new configuration needs that licensed serialization: it
   cannot be serialized locally.
6. Generate the projection from the receipt:
   `python tools/configure_variant.py --receipt <receipt> --configuration <name> --output <file>`.
   The parity check compares it with the shadow's projection.
