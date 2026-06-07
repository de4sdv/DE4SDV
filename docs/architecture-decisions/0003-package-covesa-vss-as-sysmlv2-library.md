# ADR 0003: Package COVESA VSS as a draft SysML v2 library

## Status

Draft for review.

## Context

DE4SDV needs a reviewable way to reference vehicle signal definitions in
SysML v2 model assets. COVESA Vehicle Signal Specification (VSS) provides an
established open vehicle signal hierarchy, including signal leaves,
datatypes, descriptions, and unit tokens.

The VSS repository also contains its own quantity and unit YAML files. For
DE4SDV SysML v2 model integration, those unit and quantity concepts should not
be copied as a separate unit system when equivalent concepts are already
available in SysML v2 standard libraries.

Sysand can manage SysML v2/KerML interchange projects and build a KPAR package
from textual `.sysml` sources.

## Decision

Add a Sysand-managed draft interchange project at:

`textual-notation-of-model/libraries/covesa-vss-sysmlv2/`

The project contains a generated `COVESA_VSS.sysml` package with all leaf VSS
attributes, sensors, and actuators reachable from
`spec/VehicleSignalSpecification.vspec` in the referenced source commit.

The package:

- imports SysML v2 standard scalar, quantity, and unit packages
  (`ScalarValues`, `ISQ`, `SI`, and `USCustomaryUnits`);
- does not import or copy VSS `units.yaml` or `quantities.yaml`;
- records VSS unit tokens as comments mapped to SysML v2 standard
  quantity/unit references or derived expressions over standard units;
- marks generated source derived from VSS as `SPDX-License-Identifier:
  MPL-2.0`.

## Consequences

- DE4SDV gains a concrete VSS signal library candidate that can be reviewed,
  packaged with Sysand, and referenced by future model increments.
- The package is not yet a validated normative DE4SDV dependency. Tool
  compatibility, exact SysML v2 unit-reference syntax, and COVESA review
  should be resolved before deeper integration or publication.
- Future changes should regenerate the library from a pinned VSS commit and
  update the source commit note in the package README.

## Validation

Initial validation uses:

```bash
cd textual-notation-of-model/libraries/covesa-vss-sysmlv2
sysand sources
sysand build --update-meta
```
