# Model

SysML v2 and related model assets. Keep examples small and traceable.

## Method alignment

DE4SDV SysML v2 artifacts should align with the methodology guidance in
[`../methodologies/sysmod-sysmlv2/`](../methodologies/sysmod-sysmlv2/). The
current adoption step documents the upstream SYSMOD SysML v2 reference and
tailoring approach; future increments may add local packages such as a DE4SDV
tailoring package and context model.

## Libraries

- [`libraries/covesa-vss-sysmlv2`](libraries/covesa-vss-sysmlv2/) — draft
  Sysand-managed SysML v2 interchange project for COVESA VSS leaf signals.
  The generated package uses SysML v2 standard quantity/unit library references
  instead of copying the VSS unit and quantity YAML definitions.
