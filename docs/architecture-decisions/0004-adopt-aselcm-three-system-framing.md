# ADR 0004: Adopt ASELCM three-system framing for DE4SDV

## Status

Accepted

## Context

DE4SDV needs a stable way to distinguish three related but different concerns:

- the SDV product line and configured SDV variants being engineered;
- the model-based engineering, product-line, assurance, simulation, and evidence
  environment that manages those variants across their life cycle; and
- the open-source, standards, governance, methodology, contributor, and toolchain
  ecosystem that evolves that engineering environment.

Without this distinction, repository language can collapse the engineered vehicle
product line, the engineering environment, and the community ecosystem into one
undifferentiated System-of-Interest. That makes digital twins, digital threads,
baselines, evidence, governance, and product-line assets harder to scope.

ASELCM provides a useful three-system reference framing:

- System 1 is the engineered system.
- System 2 is the life-cycle domain system that manages System 1.
- System 3 is the innovation ecosystem that manages and evolves System 2.

## Decision

DE4SDV will use the ASELCM three-system framing as a conceptual scope model.

For DE4SDV:

- **System 1** is the configurable SDV product line and configured
  vehicle/software variants.
- **System 2** is the DE4SDV model-based life-cycle engineering, assurance,
  simulation, digital-thread, digital-twin, configuration-management, and
  evidence system used to manage System 1 across its life cycle.
- **System 3** is the open innovation ecosystem that governs, evolves, reviews,
  and improves DE4SDV/System 2.

DE4SDV therefore primarily models and governs a System 2 life-cycle management
system for SDV product-line System 1 variants, while being evolved by a System 3
open innovation ecosystem.

## Consequences

- README and charter language should distinguish the repository's primary System
  2 scope from the System 1 SDV product-line variants it manages.
- Framework, ontology, and viewpoint documentation should use the three-system
  framing for scoping concerns and artifacts.
- Digital twins should be described as System 2 capabilities when they observe,
  simulate, assess, or predict aspects of System 1.
- Planning, deploying, governing, and evolving digital-twin and digital-thread
  capabilities should be treated as System 3 concerns where they affect the
  DE4SDV method, governance, or toolchain.
- Configuration and evidence baselines should identify whether they concern
  System 1, System 2, or System 3.
- Continuous homologation remains a draft/reference System 2 capability and does
  not imply legal certification or approval.

## Non-decisions

This ADR does not:

- adopt a specific executable ASELCM model implementation;
- vendor external model libraries or patterns;
- claim compliance, certification, or homologation; or
- replace future SysML v2 context models.

A later PR may add a small SysML v2 context model that captures the same
three-system scope in textual notation.
