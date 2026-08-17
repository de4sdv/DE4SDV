# Process Set

Reusable process guidance for SDV systems engineering.

## Process scope by system layer

DE4SDV separates product-line engineering work from method and ecosystem
evolution work.

### System 1-facing processes

These processes define or assess the configurable SDV product line and its
configured variants:

- feature modeling;
- feature configuration;
- product-model assembly;
- architecture definition;
- interface definition;
- behavior modeling;
- hazard and threat analysis inputs; and
- variant-specific verification and validation planning.

### System 2 processes

These processes operate the DE4SDV life-cycle engineering and assurance system:

- SysML v2 model authoring and review;
- product-line asset management;
- digital-thread traceability management;
- simulation and digital-twin workflow management;
- model credibility and VVUQ planning;
- evidence generation and evidence-register maintenance;
- configuration and baseline management;
- continuous homologation evidence preparation; and
- DevSecOps automation for repeatable checks.

### System 3 processes

These processes evolve DE4SDV itself as an open innovation ecosystem:

- methodology evolution;
- standards and reference adoption;
- upstream maintainer coordination;
- ADR governance;
- contributor onboarding and review;
- toolchain evaluation;
- roadmap prioritization; and
- community learning from System 2 usage.

## Process guidance rule

When adding or changing a process, state whether it primarily affects System 1,
System 2, System 3, or a traceable cross-layer interaction.

## Realization-readiness feedback control

A realization-readiness probe is a cross-phase System 2 control used when a
physical/software realization depends on an enabling system such as a build
host, toolchain, hypervisor, runtime, simulator, or verification environment.
It is not a new lifecycle phase.

The probe happens before expensive source synchronization, build, deployment,
or evidence execution. It answers whether a candidate enabling system can
build, deploy, execute, or verify the selected realization under its stated
capability envelope.

A probe record should identify:

- the realization question and probe ID;
- the candidate enabling system;
- the required resource, operating-system, toolchain, and runtime capabilities;
- the evidence status and retained observations;
- the model, process, or gap elements affected; and
- the disposition: proceed, re-scope, or defer.

Use this loop:

```text
state the realization question
  -> compare the candidate with the capability envelope
  -> perform a bounded implementation/toolchain inspection or experiment
  -> retain the observed constraint or enabling evidence
  -> update SysML assumptions, constraints, allocations, or gaps
  -> update YAML planning/index metadata
  -> proceed, re-scope, or defer
```

The loop may return to requirements, logical architecture, physical/software
realization, or V&V planning. Do not promote enabling-system readiness into
product interoperability, safety, certification, or production-readiness
evidence without the corresponding target-runtime observation.

For the logical sequence of work within System 2 increments, see
[`methodologies/sysmod-sysmlv2/process-mapping.md`](../../methodologies/sysmod-sysmlv2/process-mapping.md).
It defines the 13-phase increment workflow, feedback loops, and the
viewpoint flow per phase.
