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

## Where the DE4SDV vocabulary lives

The DE4SDV method vocabulary lives in the SysML v2 method kernel
(`textual-notation-of-model/packages/methods/de4sdv/`) and reaches consumers
through model-generated projection layers. The authored basic-ontology YAML
that used to sit in this directory was deleted in O4 Wave C2 (owner decision 6:
delete at closure, no generated YAML copy). There is one semantic authority:

| What | Where |
|---|---|
| Definitions, typed ends, carriers, successor and retirement records | the method kernel `.sysml` files |
| Class and relationship mappings (identity → kernel declaration, native construct or external artifact; domain/range; mechanics) | the generated projection/profile pairs under `docs/method-conformance/o4/` and `docs/method-conformance/o2plus/`, plus the frozen O2 chain under `docs/method-conformance/o2/` |
| The runtime kernel contract built from them | `KernelContract.from_layers` (`de4sdv/semantic/model_contract.py`) |
| Kernel declarations that are deliberately not projected vocabulary, each with a reason | `docs/method-conformance/o4/kernel-internal-declarations.yaml` |
| Validation rules R001–R010 | `de4sdv_ontology_validation_rules.sysml` (one model home per rule) |
| Kernel accounting gate | `de4sdv/semantic/model_projection_coverage.py` |

The vocabulary stays intentionally lightweight: no OWL/OML/openCAESAR
toolchain is adopted, and no formal reasoning or SHACL validation is enabled.

### Query coverage (executable semantic queries)

Only relationships whose projection row carries executable mechanics are
traversable through the revision-bound semantic API; the rest are vocabulary
whose links live natively in the model, in external records, or in review
artifacts:

| Relationship | Mapping strategy | Semantic strength |
|---|---|---|
| `allocatedTo` | successor (native `AllocationUsage`, three governed end pairs) | allocation |
| `specifiesFunction` | `dependency` (outgoing, action-typed targets) | relevance |
| `hasRelevantArchitecture` | `dependency` (incoming, part/action-typed sources, member-product lineage excluded) | relevance |
| `hasRelevantEvidenceContract` | `dependency` (incoming; range = the EvidenceContract type closure) | relevance |
| `verifiedBy` | `verification-membership` (reverse) | native-verification |
| `hasSubject` | `subject-membership` | native-reference |
| `derivesRequirementFromNeed` | `derivation-connection` (inverse over the `DerivesFromNeed` witness) | derivation |
| `derivedRequirementsOfNeed` | `derivation-connection` (forward over the same witness) | derivation |
| `hasValidationScenario` / `validationScenarioFor` | successor (typed carrier connection) | validation-planning |
| `hasRegulatorySource` | successor (typed carrier connection) | source-provenance |
| `hasEvidence` | `external` (evidence registers) | external data required |

The former names `realizedBy`, `deployedTo`, `validatedBy`,
`validatesFitnessForUse` and `constrainedBy` are retired: the runtime refuses
them with `retired; use <successor>` (owner decision D4); their model
retirement records in `de4sdv_relationship_carriers.sysml` are kept.
`IncrementTraceabilityShell` and `derivesNeedFromConcern` are refused with
their register disposition (owner decision D5).

Absence of a hop is not proof that no model relationship exists, and external
evidence is never traversed. Canonical kernel identity is established exactly
once at ingestion, when the kernel/API binding validation confirms the API
type and name against the serializer-recorded source document; runtime
traversal pins that UUID and never re-derives identity from element names or
SysML source text (ADR 0011).

### Terminology alignment

Status vocabulary is not redefined here: requirement and verification status
come from the ODE4HERA requirements-management library (`ReqStatus`,
`VVStatus`) adopted via ADR 0009 through the method-context adapter. Needs are
modeled as `StakeholderNeedCandidate` specializations and design-input
requirements as `RequirementCandidate` specializations. Product-line classes
map to `DE4SDV_ProductLine` (`CommonProductLineCapability`,
`ProductLineFeatureCandidate`), which enforces the ISO/IEC 26580-aligned rule
that a characteristic is only a feature once it distinguishes member products.
