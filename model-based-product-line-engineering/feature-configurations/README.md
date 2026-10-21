# Feature Configurations

This directory holds the PLEML feature configurations of the product line,
the configuration authority since the switch of
[ADR 0022](../../docs/architecture-decisions/0022-adopt-pleml-as-product-line-authority.md):
each is a selection of features that describes one configured family member
or candidate projection. Each restates a Bill-of-Features (BoF); the
Bills-of-Features retired at step S7 of ADR 0022, and the evidence records in
[`evidence/`](evidence/) now carry the evidence status they declared.

## Current configurations

| Configuration | Family | Evidence record (status) | Meaning |
|---|---|---|---|
| `aebs_autoware_linux_lidar_camera.sysml` | SDV product line | none | Standalone AEBS reference member (ADR 0014) |
| `middleware_autoware_aaos_sdv_reference.sysml` | SDV product line | `evidence/middleware-autoware-aaos-sdv-reference.yaml` (`planned`) | Planned AAOS-integrated middleware reference member (ADR 0014) |
| `example_linux_score_autoware.sysml` | SDV product line | none | Example platform projection |
| `apollo_qnx_qvm.sysml` | SDV product line | none | Example mixed-criticality platform projection |
| `fixtures/invalid_score_android.sysml` | SDV product line | none (invalid fixture) | Deliberate C001 violation |
| `inc_aebs_009a_jetson.sysml` | Engineering environment | `evidence/inc-aebs-009a-jetson.yaml` (`inspected`) | Exact maintained Jetson target; historical 009A run proved only Jetson 8 GiB identity |
| `apple_silicon_macos_candidate.sysml` | Engineering environment | `evidence/apple-silicon-macos-candidate.yaml` (`planned`) | Unverified M-series/macOS candidate |
| `nxp_zephyr_vehicle_target_candidate.sysml` | Vehicle target | `evidence/nxp-zephyr-vehicle-target-candidate.yaml` (`planned`) | Unverified unresolved NXP/Zephyr candidate |

`tested` requires retained repository evidence. `planned` means no execution
claim. Evidence status is metadata about the configuration, not a feature.

The receipts of the feature models record each configuration's verdict, its
derived variants and its admission by the governed scope. A configuration can
be valid without being admitted: of the seven configurations above, the
fixture aside, the two reference members are admitted.

## PLEML configurations

Each configuration is a `#featureConfiguration` typed by the feature tree of
its feature model, in a file of its own with the stem of its retired
Bill-of-Features in snake case. A selected feature is a `[1]` redefinition, a
deselected one a `[0]` redefinition, and an unset feature is not selected; the
value of a group names its chosen member. The configuration owns only
features: a derived variant, such as the application-middleware adapter, is
never selected here. Its doc is the description, and it owns its projection
name, the name of the part definition its product-model projection declares.

The fixtures under `fixtures/` (the invalid configuration and the parity
probes) are never configurations of the product line: the authority job
validates and serializes them into the receipts, and no production selector
reads them. The export, the API baseline, the served model and its drift
gate, the licensed validation, the repository and naming checks and the
viewer leave them out, and the configurator never projects them.

## Fixtures and evidence records

**Parity probes.** `fixtures/parity-probes/` holds the 17 probe
configurations of step S4. Ten restate probe selections of the retired PLE-S
record; seven probe the closed world: the four unsupported
application-middleware pairs, one hand-picked adapter and the two allowed
pairs that no other configuration exercises. The receipts record their
verdicts, and a test pins them (`tests/test_ple_authority_receipts.py`).
Until S7 the parity check compared each with the configurator's verdict on
the same selection.

**Evidence records.** The evidence record of a configuration is
`evidence/<configuration file stem in kebab case>.yaml`, for example
`evidence/inc-aebs-009a-jetson.yaml`. It keeps the schema of the evidence
block of the retired Bills-of-Features (`status`, plus `artifacts` with `id`
and `path`) and its integrity rules. A CI check
(`tests/test_configuration_evidence_records.py`) refuses duplicate keys,
unknown fields and statuses, invalid or duplicate artifact IDs, and unsafe or
missing artifacts: an artifact must be a direct, Git-tracked regular file
inside the repository, and symbolic-link paths and repository metadata are
refused. A configuration without evidence has no record.

## Creating a configuration

1. Choose the feature model of the correct family and System 1/System 2 role.
2. Copy a configuration of that family.
3. Select every mandatory feature.
4. Declare evidence honestly in an evidence record: use `planned` until
   retained evidence exists.
5. Open a pull request. The privileged PLE authority workflow validates and
   serializes the configuration and writes fresh receipts; commit them from
   its artifact. A new configuration needs that licensed serialization: it
   cannot be serialized locally.
6. Generate the projection from the receipt:
   `python tools/configure_variant.py --receipt <receipt> --configuration <name> --output <file>`.
