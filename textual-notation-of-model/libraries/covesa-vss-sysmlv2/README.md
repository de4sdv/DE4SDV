# COVESA VSS SysML v2 library

This Sysand-managed SysML v2 interchange project contains a generated
textual SysML v2 package for the leaf signals under the COVESA Vehicle
Signal Specification `spec/` tree.

- Source repository: <https://github.com/COVESA/vehicle_signal_specification>
- Source release: `v6.0`
- Source commit: `20c609bf95c73b51d483fb8f81a099d1d5b73066`
- Source entry point: `spec/VehicleSignalSpecification.vspec`
- Generated leaves: 616 (270 sensors, 246 actuators, 100 attributes)
- Generated allowed-value enum types: 62
- Generated branches: 137

## DE4SDV candidate extensions

[`DE4SDV_VSS_Extensions.sysml`](https://github.com/de4sdv/DE4SDV/blob/main/textual-notation-of-model/libraries/covesa-vss-sysmlv2/DE4SDV_VSS_Extensions.sysml) contains
DE4SDV candidate signal definitions for AEBS semantics that were needed by the
functional behavior slice but were not present in the generated COVESA VSS
snapshot.

Keep this extension package separate from `COVESA_VSS.sysml`:

- `COVESA_VSS.sysml` is generated from the pinned upstream COVESA source commit.
- `DE4SDV_VSS_Extensions.sysml` is DE4SDV candidate vocabulary for review,
  interface refinement, and possible upstream proposal.
- Extension paths are not accepted upstream COVESA VSS paths unless and until
  upstream accepts them.

## Semantic metadata policy

The generated package intentionally does **not** leave VSS semantics only in
comments. Stable VSS source fields are promoted into SysML v2 metadata
annotations:

- VSS path, kind, datatype, description, and source comment use
  `VssSignalMetadata`.
- VSS unit tokens map to SysML v2 standard quantity/unit references through
  `VssQuantityMetadata`.
- VSS min/max bounds use `VssRangeMetadata`.
- VSS allowed-value lists are promoted into generated SysML v2 `enum def`
  types and also retained in `VssAllowedValuesMetadata` for source
  provenance.

The package intentionally does **not** import `spec/units.yaml` or
`spec/quantities.yaml` from the VSS repository. Quantity/unit metadata points
to SysML v2 standard quantity/unit library references such as `ISQ::*`,
`SI::*`, and `USCustomaryUnits::*`, or to derived expressions over those
standard units where a direct named unit may not be available.

## Regeneration

From the repository root, with a local clone of the source repository and
PyYAML available:

```bash
python tools/generate_covesa_vss_sysmlv2.py /path/to/vehicle_signal_specification
cd textual-notation-of-model/libraries/covesa-vss-sysmlv2
sysand include COVESA_VSS.sysml
```

## Sysand usage

Install the library into a Sysand project:

```bash
sysand add de4sdv/covesa-vss-sysmlv2
```

Point your SysML v2 tool at every file listed by `sysand sources` and import
the library package from your model:

```sysml
package MyModel {
    private import COVESA_VSS::*;

    attribute mySpeed : Vehicle_Speed;
}
```

VSS semantics for each signal are available through the metadata annotations
(`VssSignalMetadata`, `VssQuantityMetadata`, `VssRangeMetadata`,
`VssAllowedValuesMetadata`); for example, the original VSS path string of a
signal definition is carried in its `VssSignalMetadata` `path` attribute.

### Maintainer commands

```bash
sysand sources
sysand build --update-meta
```

The project is published on the Sysand Index as
`de4sdv/covesa-vss-sysmlv2` (see
[ADR 0008](https://github.com/de4sdv/DE4SDV/blob/main/docs/architecture-decisions/0008-publish-covesa-vss-sysand-package.md)):

```bash
sysand build --update-meta
sysand publish --index https://sysand.com
```

Each published version is permanent on the index; regenerating from a new
pinned VSS commit requires a new version number and changelog entry.

`output/` and `.sysand/` are local build/dependency artifacts and should not
be committed.

## Licensing

`COVESA_VSS.sysml` is derived from COVESA VSS source material and is marked
`SPDX-License-Identifier: MPL-2.0`. Keep the COVESA source commit above with
any regenerated update.

`DE4SDV_VSS_Extensions.sysml` is separately authored DE4SDV content and is
marked `SPDX-License-Identifier: Apache-2.0`. Keep candidate extensions in
that separate file; do not move generated or copied COVESA material into it.
