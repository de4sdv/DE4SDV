# Model

SysML v2 and related model assets. Keep examples small and traceable.

## Method alignment

DE4SDV SysML v2 artifacts should align with the methodology guidance in
[`../methodologies/sysmod-sysmlv2/`](../methodologies/sysmod-sysmlv2/). The
current adoption step documents the upstream SYSMOD SysML v2 reference and
tailoring approach; future increments may add local packages such as a DE4SDV
tailoring package and context model.

## Validation

All generated or modified `.sysml` textual notation in this directory must be
validated before the modeling step is considered complete:

```bash
python scripts/validate_sysml.py
```

The validation wrapper uses Sensmetry SysIDE Modeler CLI (`syside check`) and
reports a clean no-op when the repository has no `.sysml` files yet.

## Libraries

- [`libraries/covesa-vss-sysmlv2`](libraries/covesa-vss-sysmlv2/) — draft
  Sysand-managed SysML v2 interchange project for COVESA VSS leaf signals.
  The generated package uses SysML v2 standard quantity/unit library references
  instead of copying the VSS unit and quantity YAML definitions.
