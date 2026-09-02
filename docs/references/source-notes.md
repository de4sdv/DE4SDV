# Source Notes

This scaffold was informed by:

- The Open Source Way 2.0 guidebook: community formation, project goals, new
  project checklist, communication norms, governance, contribution process,
  onboarding, and health metrics.
- GitHub Blog: guidance on effective [`agents`](../../AGENTS.md) files,
  including commands, testing, project structure, code style, git workflow, and
  boundaries.
- Mykhailo Chalyi's "Making Your Repository AI‑Ready": feedback loops, entry
  points, specs, progressive disclosure, skills, and testing documentation.
- ASELCM three-system framing: Schindel and Dove's *Introduction to the Agile
  Systems Engineering Life Cycle MBSE Pattern*, v1.6.6, published and used by
  INCOSE with permission. The paper describes ASELCM reference boundaries for
  System 1 as the target system, System 2 as the target-system life-cycle domain
  system, and System 3 as the system of innovation. See the [INCOSE/OMG MBSE
  Wiki PDF][aselcm-pattern].
- Digital-twin reference guidance: purpose, use case, managed boundary,
  credibility, consistency management, and digital-thread context for digital
  twins.

Additional model-library references:

- COVESA Vehicle Signal Specification: source for the draft SysML v2 VSS signal
  library under the [COVESA VSS SysML v2 library][covesa-vss-library]. The
  generated package is pinned to the source commit recorded in that library's
  README.
- Sysand User Guide: installation and project workflow for creating a SysML v2
  or KerML interchange project and building the library KPAR.

Methodology references added during DE4SDV modeling-method development:

- MBSE4U `sysmod-sysmlv2`: public Apache-2.0 SysML v2 library for SYSMOD
  concepts, referenced as an upstream modeling-method source. See
  [`../../methodologies/sysmod-sysmlv2/upstream`](../../methodologies/sysmod-sysmlv2/upstream.md).

Keep this file updated as new external references are added.

[covesa-vss-library]: ../../textual-notation-of-model/libraries/covesa-vss-sysmlv2/
[aselcm-pattern]: https://www.omgwiki.org/MBSE/lib/exe/fetch.php?media=mbse:patterns:intro_to_the_aselcm_pattern_v1.6.6.pdf
