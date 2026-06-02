# Framework

Conceptual framework for SDV engineering assets.

## ASELCM-aligned scope model

DE4SDV uses a three-system framing to separate the product line being engineered,
the life-cycle management system that engineers and assures it, and the ecosystem
that evolves that management system.

### System 1: SDV product line and configured variants

System 1 is the engineered system. In DE4SDV, it is the configurable SDV product
line and configured vehicle/software variants.

System 1 concerns include:

- feature sets and feature configurations;
- SDV architecture variants;
- software, hardware, sensor, compute, and network alternatives;
- behavior, interfaces, and operational scenarios;
- safety, security, privacy, and compliance guardrails; and
- variant-specific verification and validation targets.

### System 2: DE4SDV life-cycle engineering and assurance system

System 2 is the life-cycle domain system that manages System 1. In DE4SDV, this
is the primary repository System-of-Interest.

System 2 concerns include:

- SysML v2 models and model libraries;
- model-based product-line engineering assets;
- digital-thread and OSLC traceability;
- digital-twin, simulation, FMI/FMU, and SSP workflows;
- safety, security, regulatory, and homologation evidence;
- configuration and baseline management; and
- DevSecOps automation for reproducible engineering workflows.

### System 3: DE4SDV open innovation ecosystem

System 3 is the innovation ecosystem that governs and evolves System 2.

System 3 concerns include:

- maintainers, contributors, and review workflows;
- ADRs, governance, and methodology evolution;
- standards and upstream project alignment;
- external OSS project coordination;
- toolchain maturity and adoption decisions; and
- learning feedback from System 2 usage.

## Repository implication

When adding artifacts, identify whether the artifact primarily describes:

- System 1 product-line or variant content;
- System 2 engineering, assurance, simulation, evidence, or baseline capability;
  or
- System 3 governance, standards, ecosystem, or method-evolution content.

Some artifacts intentionally connect layers. For example, a digital-thread link
may connect a System 1 feature, a System 2 simulation result, and a System 3 ADR.
Such cross-layer links should be explicit rather than implied.
