# Model

SysML v2 and related model assets. Keep examples small and traceable.

## Method alignment

DE4SDV SysML v2 artifacts should align with the methodology guidance in
[`../methodologies/sysmod-sysmlv2/`](../methodologies/sysmod-sysmlv2/). The
current adoption step documents the upstream SYSMOD SysML v2 reference and
tailoring approach; future increments may add local packages such as a DE4SDV
tailoring package and context model.

## Method packages

DE4SDV method packages reuse external method patterns selectively. They are not
full implementations of upstream methods; each package should state the source
pattern it adapts and the DE4SDV-specific tailoring.

- [`packages/methods/de4sdv/de4sdv_method_context.sysml`](packages/methods/de4sdv/de4sdv_method_context.sysml)
  adapts the SYSMOD/SysML v2 problem-statement pattern for DE4SDV. It defines a
  small `DE4SDV_MethodContext` package with `ProblemStatement` and
  `SystemContext` concepts used to anchor increments before needs and
  requirements. It deliberately avoids a generic `ProjectContext` abstraction.
  It is not a vendored upstream `SYSMOD.sysml` implementation.
- [`packages/methods/de4sdv/de4sdv_stakeholders.sysml`](packages/methods/de4sdv/de4sdv_stakeholders.sysml)
  defines reusable DE4SDV stakeholder role definitions and lightweight
  risk/effort/category metadata for native SysML v2 `stakeholder` parameters.
- [`packages/methods/de4sdv/de4sdv_method_concerns_and_viewpoints.sysml`](packages/methods/de4sdv/de4sdv_method_concerns_and_viewpoints.sysml)
  defines the current reusable DE4SDV method concern/viewpoint kernel as the
  top-level `DE4SDV_MethodViewpoints` package. Feature packages should
  import/select these `concern def` and `viewpoint def` elements, then add
  feature-specific concern usages inside the feature package and view-local
  viewpoint usages inside concrete views. Reusable `view def` elements are
  deferred until DE4SDV has cross-feature view construction recipes with real
  filters/rendering/composition logic. These are not claimed as SAF-native
  viewpoints yet; they are DE4SDV workflow viewpoints that should be mapped to
  SAF in a later method-alignment increment.

## Context modeling scope

Future context models should preserve the ASELCM-aligned DE4SDV scope:

- System 1: configurable SDV product line and configured vehicle/software
  variants.
- System 2: DE4SDV life-cycle engineering and assurance system.
- System 3: DE4SDV open innovation ecosystem.

A later small example may add
`textual-notation-of-model/context/de4sdv_aselcm_context.sysml` to capture this
framing in SysML v2 textual notation.

## Live repository and generated views

DE4SDV is piloting a SysML v2 API repository as the live model store. Eclipse
SysON is the preferred GUI tool for the initial graphical modeling path.
GitHub remains the reviewed publication baseline for textual snapshots,
generated views, documentation, and validation evidence.

The initial pilot views are bootstrap placeholders until the SysML v2 API
repository, SysON editing path, and view renderer/exporter are connected:

### System context

![DE4SDV System Context](views/system-context/system-context.svg)

Source metadata:
[`views/system-context/manifest.json`](views/system-context/manifest.json)

### Life-cycle engineering system

![DE4SDV Life-Cycle Engineering System](views/lifecycle-engineering-system/lifecycle-engineering-system.svg)

Source metadata:
[`views/lifecycle-engineering-system/manifest.json`](views/lifecycle-engineering-system/manifest.json)

## Validation

All generated or modified `.sysml` textual notation in this directory must be
validated before the modeling step is considered complete. Use one of two
validation paths:

1. Local validation, if Syside is available, using the Syside Editor VS Code
   extension or the repository wrapper:

```bash
python scripts/validate_sysml.py
```

The validation wrapper uses Sensmetry SysIDE Modeler CLI (`syside check`) and
reports a clean no-op when the repository has no `.sysml` files yet.

1. Maintainer-run privileged validation, requested from the pull request after
   initial review. Maintainers run the `Privileged Syside Validation` workflow
   from GitHub Actions with the reviewed branch, tag, or commit SHA and the
   model path to validate.

## Libraries

- [`libraries/covesa-vss-sysmlv2`](libraries/covesa-vss-sysmlv2/) — draft
  Sysand-managed SysML v2 interchange project for COVESA VSS leaf signals.
  The generated package uses SysML v2 standard quantity/unit library references
  instead of copying the VSS unit and quantity YAML definitions.
