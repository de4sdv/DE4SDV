# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-08-28

### Added

- Initial packaged release of the generated COVESA VSS SysML v2 library.
- Generated textual SysML v2 package for the leaf signals under the COVESA
  Vehicle Signal Specification `spec/` tree, pinned to upstream source commit
  `6fb1dac2630a8910ee996863b2af02b310dcd7ce`
  (626 leaves: 280 sensors, 246 actuators, 100 attributes; 65 allowed-value
  enum types; 139 branches).
- VSS semantics (path, kind, datatype, description, comment, quantity/unit,
  range, allowed values) promoted into SysML v2 metadata annotations instead of
  comments only.
- Unit references point to SysML v2 standard quantity/unit libraries
  (ISQ/SI/USCustomaryUnits) or derived expressions over those libraries.

### Notes

- `COVESA_VSS.sysml` is generated from the pinned upstream COVESA VSS source
  commit and carries `SPDX-License-Identifier: MPL-2.0`.
- DE4SDV candidate extension signals are intentionally **not** part of this
  package; they are kept in the DE4SDV repository as a separately authored
  file until they are proposed to and accepted by COVESA upstream.
- The package intentionally does not import `spec/units.yaml` or
  `spec/quantities.yaml` from the VSS repository.
