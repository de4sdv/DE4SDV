# COVESA VSS SysML v2 library

This Sysand-managed SysML v2 interchange project contains a generated
textual SysML v2 package for the leaf signals under the COVESA Vehicle
Signal Specification `spec/` tree.

- Source repository: <https://github.com/COVESA/vehicle_signal_specification>
- Source commit: `6fb1dac2630a8910ee996863b2af02b310dcd7ce`
- Source entry point: `spec/VehicleSignalSpecification.vspec`
- Generated leaves: 626 (280 sensors, 246 actuators, 100 attributes)
- Generated branches: 139

## Unit and quantity policy

The generated package intentionally does **not** import `spec/units.yaml` or
`spec/quantities.yaml` from the VSS repository. Unit comments in
`COVESA_VSS.sysml` map VSS unit tokens to SysML v2 standard quantity/unit
library references such as `ISQ::*`, `SI::*`, and `USCustomaryUnits::*`, or
to derived expressions over those standard units where a direct named unit may
not be available.

## Regeneration

From the repository root, with a local clone of the source repository and
PyYAML available:

```bash
python tools/generate_covesa_vss_sysmlv2.py /path/to/vehicle_signal_specification
cd textual-notation-of-model/libraries/covesa-vss-sysmlv2
sysand include COVESA_VSS.sysml
```

## Sysand usage

```bash
sysand sources
sysand build --update-meta
```

`output/` and `.sysand/` are local build/dependency artifacts and should not
be committed.

## Licensing

This generated library is derived from COVESA VSS source material and is
marked `SPDX-License-Identifier: MPL-2.0`. Keep the COVESA source commit
above with any regenerated update.
