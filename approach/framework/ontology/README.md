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

## Minimal increment ontology kernel

[`de4sdv-basic-ontology.yaml`](de4sdv-basic-ontology.yaml) defines the current
minimal vocabulary for SYSMOD/SysML v2 increments. It is intentionally lightweight:

- no OWL/OML/openCAESAR toolchain is adopted by this file,
- no formal reasoning or SHACL validation is enabled yet,
- terms exist to keep feature increments, SAF viewpoints, requirements,
  architecture elements, evidence, and baselines semantically consistent.

### Kernel sync

The YAML is not a free-floating word list: every class carries a `kernel`
mapping stating where its semantics actually live:

- `file` + `declaration` — a SysML declaration in the method kernel
  (for example `part def EngineeringIncrement` in
  `de4sdv_method_context.sysml`);
- `native` — a native SysML v2 language construct (`variation`, `variant`,
  `viewpoint def`, `verification def`, and so on) rather than a kernel
  declaration;
- `external` — an artifact outside the SysML model (the feature catalogue and
  Bill-of-Features records, the ODE4HERA requirements-management library, or
  evidence registers).

The `kernel_sync` block makes the vocabulary contract bidirectional and
complete:

- `governed_directory` names the method-kernel directory whose declarations
  are under contract;
- `exclusions` lists every kernel declaration that is deliberately not
  ontology vocabulary, each with a reason.

The ontology-kernel contract check in `scripts/check_model_sync.py` enforces
the set equation `kernel declarations = ontology-mapped declarations +
exclusions` as exact `(file, declaration)` pairs, so the ontology cannot
silently drift from the model in either direction. The gate runs as part of
`python scripts/check_repo.py`, and its failure modes are covered by
`tests/test_ontology_kernel_contract.py`.

### Terminology alignment

Status vocabulary is not redefined here: requirement and verification status
come from the ODE4HERA requirements-management library (`ReqStatus`,
`VVStatus`) adopted via ADR 0009 through the method-context adapter. Needs are
modeled as `StakeholderNeedCandidate` specializations and design-input
requirements as `RequirementCandidate` specializations; the ontology's `Need`
and `Requirement` classes map to those kernel declarations. Product-line
classes map to `DE4SDV_ProductLine` (`CommonProductLineCapability`,
`ProductLineFeatureCandidate`), which enforces the ISO/IEC 26580-aligned rule
that a characteristic is only a feature once it distinguishes member products.

## Candidate ontology elements

Superseded: the concepts previously listed here as draft candidates
(`SDVProductLine`, `ConfiguredSDVVariant`, `FeatureConfiguration`,
`EvidenceBaseline`, and others) now exist as concrete kernel declarations or
kernel mappings in `de4sdv-basic-ontology.yaml`. See the `kernel_sync`
section of that file for the current class-to-declaration mapping.


## Executable SysML traversal mappings

Relationships may declare an executable `sysml_mapping` block. Strategies are
bound to the native SysML v2 API representation of the reviewed model:

- `dependency` — `Dependency` objects with `source`/`target` references;
  semantic strength `relevance`.
- `allocation` — `AllocationUsage` objects; semantic strength `allocation`.
- `subject-membership` — native `SubjectMembership` objects owned by a
  requirement usage, referencing the product-line subject through
  `memberElement`; semantic strength `native-reference`.
- `verification-membership` — native `RequirementVerificationMembership`
  objects referencing the verified requirement through `verifiedRequirement`;
  the verification case is resolved from the membership owner; semantic
  strength `native-verification`.
- `external` — the authoritative object lives outside the SysML API baseline.

These mappings are the explicit contract between DE4SDV concepts and SysML
semantics. Traversal uses only these declared strategies; there is no
name-based or heuristic inference. The bounded test fixture keeps its own
simplified shapes for deterministic tests and does not define production
semantics.
