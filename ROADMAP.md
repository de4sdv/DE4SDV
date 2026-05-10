# Roadmap

This roadmap aligns project work with the GitHub milestone:
- v0.1 Foundation: https://github.com/de4sdv/DE4SDV/milestone/1

## v0.1 Foundation (current)

Objective: establish a shared project foundation (scope, governance, contribution workflow, and repository baseline) so implementation work can proceed with clear rules and structure.

### In scope for v0.1

Prioritized issues (P0):
1. #1 Create DE4SDV project charter
2. #2 Decide initial repository structure
3. #3 Define DE4SDV v0.1 roadmap
4. #4 Rework CONTRIBUTING.md into a practical contributor guide

Issue links:
- https://github.com/de4sdv/DE4SDV/issues/1
- https://github.com/de4sdv/DE4SDV/issues/2
- https://github.com/de4sdv/DE4SDV/issues/3
- https://github.com/de4sdv/DE4SDV/issues/4

### v0.1 deliverables

- Project charter defining purpose, scope, target users, goals, non-goals, and guiding principles (#1)
- Initial repository structure documented and adopted (#2)
- Contributor workflow and review expectations documented in CONTRIBUTING.md (#4)
- Roadmap and milestone scope explicitly defined and synchronized in ROADMAP.md (#3)

### Blocking order and dependencies

- #1 and #2 are foundational and should be completed first.
- #4 depends on decisions from #1 and #2 to avoid workflow/documentation drift.
- #3 integrates the agreed scope and must remain aligned with milestone contents.

Recommended execution order:
1) #1 and #2 (parallel)
2) #4
3) #3 (final sync pass)

### Explicitly postponed to v0.2+

- SysML v2 modeling patterns and modeling guidelines beyond baseline references
- MBPLE method details and full feature-model workflow examples
- Executable SysML v2 API, FMU/FMI/SSP, and digital twin integration examples
- Continuous compliance automation, homologation pipelines, and release evidence workflows
- DevSecOps automation beyond initial repository hygiene

### Definition of Done for v0.1

v0.1 Foundation is done when all of the following are true:

- All v0.1 milestone issues (#1–#4) are completed and closed.
- README.md links to the charter and contributing guide.
- CONTRIBUTING.md describes accepted contribution types, issue-first workflow, PR workflow, and review/approval expectations.
- The repository structure is documented and reflected in the actual tree.
- This ROADMAP.md stays synchronized with milestone scope (in-scope issues, postponed topics, and dependencies).
- Maintainers confirm agreement on v0.1 in/out scope and completion criteria.

## v0.2 and later (preview)

After v0.1, priority shifts from governance/setup to executable technical assets:
- Conceptual framework consolidation (ontology, viewpoints, ADRs, standards mapping)
- Reference SysML v2 and MBPLE examples
- Simulation interoperability examples (FMI/FMUs/SSP)
- Digital continuity and continuous compliance workflows
