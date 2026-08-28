# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-08-28

### Fixed

- README links now resolve outside the DE4SDV repository: the
  `DE4SDV_VSS_Extensions.sysml` reference and the ADR 0008 reference point to
  their GitHub locations instead of repo-relative paths that were broken on
  the Sysand Index project page.

## [0.1.0] - 2026-08-28

### Added

- Initial packaged release of the generated COVESA VSS SysML v2 library.
- Generated textual SysML v2 library package for the leaf signals under the
  COVESA Vehicle Signal Specification `spec/` tree, pinned to the upstream
  `v6.0` release (source commit
  `20c609bf95c73b51d483fb8f81a099d1d5b73066`; 616 leaves: 270 sensors,
  246 actuators, 100 attributes; 62 allowed-value enum types; 137 branches).
- VSS semantics (path, kind, datatype, description, comment, quantity/unit,
  range, allowed values) promoted into SysML v2 metadata annotations instead of
  comments only.
- Unit references point to SysML v2 standard quantity/unit libraries
  (ISQ/SI/USCustomaryUnits) or derived expressions over those libraries.

### Notes

- The generated root is a SysML v2 `library package`, matching the convention
  used by other published SysML v2 libraries.
- `COVESA_VSS.sysml` is generated from the pinned upstream COVESA VSS source
  commit and carries `SPDX-License-Identifier: MPL-2.0`.
- DE4SDV candidate extension signals are intentionally **not** part of this
  package; they are kept in the DE4SDV repository as a separately authored
  file until they are proposed to and accepted by COVESA upstream.
- The package intentionally does not import `spec/units.yaml` or
  `spec/quantities.yaml` from the VSS repository.
