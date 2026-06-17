# Ontology

Domain concepts and relationships.

## Core ASELCM concepts

- **System 1**: configurable SDV product line and configured vehicle/software
  variants.
- **System 2**: DE4SDV life-cycle engineering and assurance system that manages
  System 1.
- **System 3**: open innovation ecosystem that governs and evolves System 2.
- **Environment 1**: operational, manufacturing, support, and retirement contexts
  with which System 1 interacts.
- **Environment 2**: organizational, tool, standards, supply-chain, and project
  contexts with which System 2 interacts.
- **Life-cycle management process**: a process that plans, engineers, verifies,
  validates, baselines, supports, operates, sustains, updates, or retires a
  system or its evidence.
- **Consistency management**: activity that checks or reconciles consistency among
  stakeholder needs, requirements, designs, models, variants, simulations,
  baselines, evidence, and observed behavior.
- **Credibility assessment**: activity that establishes confidence in a model,
  simulation, digital twin, or evidence artifact for a declared use.

## Core relationships

- System 2 **manages** System 1 across its life cycle.
- System 2 **learns about** System 1 and Environment 1.
- System 2 **uses learning** to configure, verify, validate, baseline, and assure
  System 1 variants.
- System 3 **evolves** System 2 methods, governance, tooling, and reference assets.
- System 3 **learns about** System 2 and Environment 2.
- Digital twins are System 2 capabilities when they observe, simulate, assess, or
  predict aspects of System 1.
- Digital-thread links connect System 1, System 2, and System 3 artifacts.
- Evidence baselines support System 2 consistency management.
- Configuration baselines constrain System 1 variants and System 2 engineering
  assets.
- ADRs record System 3 decisions that shape System 2 capabilities.

## Candidate ontology elements

Future SysML v2 or structured ontology artifacts may introduce elements such as:

- `SDVProductLine`
- `ConfiguredSDVVariant`
- `DE4SDVLifeCycleEngineeringSystem`
- `DE4SDVInnovationEcosystem`
- `FeatureConfiguration`
- `ProductModel`
- `DigitalThreadLink`
- `DigitalTwinCapability`
- `EvidenceBaseline`
- `ConfigurationBaseline`
- `CredibilityAssessment`
- `ConsistencyManagementConcern`
- `ArchitectureDecisionRecord`

These names are draft conceptual terms, not yet a normative model vocabulary.
