# Roadmap

This roadmap aligns project work with the GitHub milestone:
- v0.1 Foundation: https://github.com/de4sdv/DE4SDV/milestone/1

## v0.1 Foundation (substantially complete)

Objective: establish a shared project foundation (scope, governance, contribution workflow, and repository baseline) so implementation work can proceed with clear rules and structure.

### P0 issues — all closed

1. ✅ #1 Create DE4SDV project charter
2. ✅ #2 Decide initial repository structure
3. ✅ #3 Define DE4SDV v0.1 roadmap
4. ✅ #4 Rework CONTRIBUTING.md into a practical contributor guide

Issue links:
- https://github.com/de4sdv/DE4SDV/issues/1
- https://github.com/de4sdv/DE4SDV/issues/2
- https://github.com/de4sdv/DE4SDV/issues/3
- https://github.com/de4sdv/DE4SDV/issues/4

### v0.1 deliverables — status

| Deliverable | Status |
|---|---|
| Project charter (#1) | ✅ Done |
| Initial repository structure (#2) | ✅ Done — tree documented in `docs/repository-tree.md` |
| Contributor guide (#4) | ✅ Done — `CONTRIBUTING.md` |
| Roadmap synchronized (#3) | ✅ Done |
| Initial process set | ✅ Done — `approach/process-set/README.md` |
| Initial ontology baseline | ✅ Done — `approach/framework/ontology/de4sdv-basic-ontology.yaml` |
| System context view | ✅ Done — `textual-notation-of-model/views/system-context/` |
| ASELCM three-system framing | ✅ Done — ADR #4 |

### Work completed beyond v0.1 scope

Several technical increments were delivered ahead of the v0.2 timeline:

- AEBS pilot: operational context, needs/requirements, functional behavior, functional interface slices (#42, #48, #49, #50)
- COVESA VSS generated as SysML v2 library (ADR #3)
- DE4SDV VSS extension package for AEBS-specific signals
- SysML v2 API repository spike (ADR #5)
- SysIDE Modeler view automation spike
- SAF viewpoint map and methodology tailoring
- Branch protection and repository hygiene on GitHub

### Blocking order and dependencies

All v0.1 P0 issues are closed. The original dependency graph (#1 and #2 → #4 → #3) is fully resolved.

### Explicitly postponed to v0.2+

- SysML v2 modeling patterns and modeling guidelines beyond baseline references
- MBPLE method details and full feature-model workflow examples
- Executable SysML v2 API, FMU/FMI/SSP, and digital twin integration examples
- Continuous compliance automation, homologation pipelines, and release evidence workflows
- DevSecOps automation beyond initial repository hygiene

### Definition of Done for v0.1

All conditions are met:

- ✅ All v0.1 milestone issues (#1–#4) are completed and closed.
- ✅ README.md links to the charter and contributing guide.
- ✅ CONTRIBUTING.md describes accepted contribution types, issue-first workflow, PR workflow, and review/approval expectations.
- ✅ The repository structure is documented and reflected in the actual tree.
- ✅ This ROADMAP.md stays synchronized with milestone scope (in-scope issues, postponed topics, and dependencies).

Remaining:
- Maintainer confirmation of v0.1 completion and agreement to close the milestone.

## v0.2 and later (in progress)

After v0.1, priority shifts from governance/setup to executable technical assets.

### Already in flight

- AEBS feature pilot — operational context, needs/requirements, functional behavior, functional interfaces (PRs #42, #48, #49, #50 merged)
- COVESA VSS as SysML v2 library with DE4SDV extension signals (ADR #3)
- SysML v2 API repository spike (ADR #5) — draft PR #36
- SysIDE Modeler view automation spike — draft PR #34

### Next priorities

- Consolidate AEBS pilot: interface/refinement increment, allocation to architecture elements
- Promote spike PRs (#34, #36) from draft to reviewed, or close with documented outcomes
- Conceptual framework consolidation (ontology, viewpoints, ADRs, standards mapping)
- More reference SysML v2 product-line examples beyond AEBS
- Simulation interoperability examples (FMI/FMUs/SSP)
- Digital continuity and continuous compliance workflows
