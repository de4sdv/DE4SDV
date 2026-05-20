# DE4SDV Project Charter

## Project purpose

DE4SDV exists to provide an open, model-based reference foundation for engineering Software-Defined Vehicle (SDV) product lines with continuous assurance.

## Problem statement

Software-Defined Vehicles (SDVs) require coordinated engineering across many domains - architecture, variants, software, safety, security, compliance, simulation, digital twins, and lifecycle traceability. Yet many teams do not have an open reference framework that links these concerns. At the same time, an ever-growing portion of SDV-related technology is being released as open source. As a result, a holistic approach for integrating these disparate technologies into configurable stacks is essential.

## Target users / personas

- Systems engineers and solution architects designing SDV system structures.
- MBSE/SysML v2 practitioners creating and governing formal models.
- Product line engineers managing features, variants, and reusable assets.
- Simulation and digital twin engineers integrating FMI/FMU/SSP workflows.
- Safety and cybersecurity engineers building assurance cases and evidence.
- Compliance and homologation teams preparing continuous approval artifacts.
- DevSecOps and toolchain engineers implementing traceable automation.
- Researchers, educators, and open-source contributors advancing SDV methods.

## Goals

- Define a practical, open repository structure for SDV digital engineering assets.
- Establish end-to-end traceability across requirements, models, variants, tests, and compliance evidence.
- Enable configurable SDV product-line engineering with reusable patterns.
- Enable certified freedom: support configurable vehicle feature tailoring within clearly defined safety, security, and compliance guardrails.
- Support simulation-backed engineering decisions and digital twin readiness.
- Integrate safety, security, and regulatory evidence into everyday development.
- Promote ecosystem diversity by enabling systematic comparison of alternative open-source subsystem stacks rather than mandating a single stack.
- Provide AI-ready, machine-readable documentation and governance artifacts.
- Build a contributor community around transparent, standards-aware practices.
- Improve openness and trust through explicit data-handling transparency and user-control-oriented design patterns for vehicle and user data.

## Non-goals (current scope)

- Delivering certified production vehicle platforms.
- Issuing legal/regulatory approval or replacing authority decisions.
- Replacing OEM, supplier, or tool-vendor proprietary engineering environments.
- Standardizing every SDV methodology; DE4SDV is a reference baseline, not a single mandated process.
- Guaranteeing compliance by default without project-specific validation and tailoring.

## Core principles

- Open by default: methods and artifacts should be reusable and reviewable.
- Model-centered: architecture and behavior are defined through structured models.
- Ecosystem diversity over lock-in: evaluate and compose multiple open-source alternatives instead of prescribing a single technical stack.
- Traceability first: every important claim should be linkable to evidence.
- Variant-aware: product-line variability is explicit, governed, and testable.
- Certified freedom with guardrails: configurable vehicle features are enabled within clearly defined safety, security, and compliance boundaries.
- Compliance as flow: assurance evidence is created continuously, not at the end.
- Data openness and user control: data handling should be transparent, with meaningful user control where applicable.
- Automation with accountability: CI/CD and AI assist, humans remain responsible.
- Incremental evolution: start simple, baseline often, mature through iteration.

## Relationship to key technical domains

- SysML v2: primary modeling language and API ecosystem for formal system definition and exchange.
- MBPLE: mechanism to represent features, variability, and configured product models.
- Digital twin: runtime-informed engineering objective connected to model and simulation assets.
- Simulation (FMI/FMU/SSP): interoperability layer for verification, validation, and design-space exploration.
- Compliance (safety, security, UNECE-oriented): structured evidence domains linked to engineered artifacts.
- DevSecOps: delivery and assurance automation backbone for reproducible engineering workflows.
- Continuous homologation: target operating model where compliance evidence is versioned and continuously maintained.

## Maintainer agreement / decision record

Maintainers agree that this charter defines DE4SDV's initial direction and decision filter. New roadmap items, issues, and pull requests should be evaluated against this charter. Substantive charter changes require maintainer discussion and an explicit decision record (ADR or governance note).
