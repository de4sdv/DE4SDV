# Source Notes

This scaffold was informed by:

- The Open Source Way 2.0 guidebook: community formation, project goals, new
  project checklist, communication norms, governance, contribution process,
  onboarding, and health metrics.
- GitHub Blog: guidance on effective [`agents.md`](../../AGENTS.md) files,
  including commands, testing, project structure, code style, git workflow, and
  boundaries.
- Mykhailo Chalyi's "Making Your Repository AI-Ready": feedback loops, entry
  points, specs, progressive disclosure, skills, and testing documentation.

Additional model-library references:

- COVESA Vehicle Signal Specification: source for the draft SysML v2 VSS signal
  library under the [COVESA VSS SysML v2 library][covesa-vss-library]. The
  generated package is pinned to the source commit recorded in that library's
  README.
- Sysand User Guide: installation and project workflow for creating a SysML v2
  or KerML interchange project and building the library KPAR.

Methodology references added during DE4SDV modeling-method development:

- MBSE4U `sysmod-sysmlv2`: public Apache-2.0 SysML v2 library for SYSMOD
  concepts, referenced as an upstream modeling-method source. See the local
  upstream notes in `methodologies/sysmod-sysmlv2/upstream.md`.

Product-line and ontology references added for the ontology feature-variability
pilot:

- ISO/IEC 26580:2021, Software and systems engineering — Methods and tools for
  the feature-based approach to software and systems product line engineering.
  Used as the primary vocabulary source for feature-based PLE terms such as
  feature, feature catalogue, bill-of-features, member product, product line,
  shared asset superset, variation point, and PLE factory. The pilot uses the
  feature/common-capability distinction from this source.
- ISO/IEC/IEEE 12207, Systems and software engineering — Software life cycle
  processes. Normative lifecycle vocabulary source referenced by ISO/IEC 26580.
- ISO/IEC/IEEE 15288, Systems and software engineering — System life cycle
  processes. Normative lifecycle vocabulary source referenced by ISO/IEC 26580.
- ISO/IEC/IEEE 24765 / SEVOCAB. Public systems and software engineering
  vocabulary reference noted by ISO/IEC 26580 for additional terminology.
- ISO/IEC 26550. General software and systems product-line engineering reference
  model specialized by ISO/IEC 26580; useful for inherited terms and process
  context.
- ISO/IEC 26556 and ISO/IEC 26562. Related ISO/IEC product-line engineering
  standards referenced by ISO/IEC 26580 for organizational/process context; not
  adopted as DE4SDV governance in this pilot.
- W3C RDF, RDFS, OWL 2, SHACL, and SPARQL specifications. Candidate graph,
  ontology, validation, and query technologies for later experiments; not
  adopted by the first pilot PR.
- openCAESAR / OML documentation. Candidate ontology-based systems engineering
  stack for later evaluation; no toolchain adoption or vendoring is introduced
  by the first pilot PR.
- SysML v2 and KerML specifications. Candidate system-modeling alignment targets
  for later mapping work; the first pilot intentionally avoids `.sysml`
  artifacts.
- COVESA VSS/VSSo, SOSA/SSN, and OSLC. Candidate external alignment vocabularies
  for later SDV signal, observation, and lifecycle-federation work; not imported
  by the first pilot PR.

Keep this file updated as new external references are added.

[covesa-vss-library]: ../../textual-notation-of-model/libraries/covesa-vss-sysmlv2/
