# O4 kernel definition homes

**Draft — licensed Syside validation is pending.** Generated artifacts are
regenerated with the repository generators and bound to this branch's commits
(temporary binding); a content-only rebind follows the squash merge.

The remaining authored definitions need durable model homes before O4 can
retire its YAML authority. This package supplies those homes; it does not
retire the authority, rewire consumers, admit predicates or close O4.

## Owner decisions (2026-10-05)

- **D1:** `DE4SDV_MethodContext` owns named documentation for
  `ArchitectureElement`, `Function`, `LogicalElement`, `PhysicalElement` and
  the unchanged `Interface` meaning. Comments name their native SysML kinds;
  there is no parallel type taxonomy or Interface filter widening.
- **D2:** kernel `requirement def AcceptanceCriterion`, specialized by
  `MiddlewareAcceptanceCriterion`. Test-verdict criteria are distinct from
  authorized decisions under `de4sdv.acceptance.maintainer-decision.v1`.
- **D3:** `MethodEvaluationScope` owns `MethodEvaluationExclusion[*]` records
  with `ref excludedElement : Base::Anything` and a required, non-empty
  rationale. The record is kernel-internal and reasoned in the sync exclusions.
  Existing scope memberships and the Python exclusion dictionary stay intact.
- **D4:** kernel `requirement def EvidenceContract :> RequirementCandidate`;
  middleware and AEBS override evidence requirements specialize it.
  `hasRelevantEvidenceContract` can be discriminated by type and specialization
  closure, not names. Its current dependency mapping is unchanged.
- **7:** standalone native KerML `disjoining` relates
  `CommonProductLineCapability` and `ProductLineFeatureCandidate`. The bounded
  static negative probe detects direct and inherited dual typing; it is not a
  compiler, general source parser or licensed semantic-validation verdict.
- **8:** the complete `instantiatesCanonicalArchitecture` definition is owned
  by `DE4SDV_ProductLine`, with **not queryable; no product-to-canonical
  reachability claimed**. No executable mapping or canonical-package selector.

## Definition-text parity and register targets

[kernel-definition-homes.json](kernel-definition-homes.json) is a
location inventory, not a second meaning authority: it contains paths,
declarations and owned Documentation locators, never copies of definition
text. The model owns normalized-exact text for all 76 authored class/predicate
definitions. Exact named docs supplement existing explanatory docs without
changing their reviewed meaning. Native/library, historical and external
concepts use package-owned documentation, not copied library types, resurrected
trace shells, new assurance taxonomies or PLE configurator authority.

The requested W2/W4 target rows are listed below. **33/40 have exact definition
text. The seven relationship rows have no authored definition field: five use
their existing reviewed, typed vocabulary carriers; `hasStakeholder` and
`hasAcceptanceCriterion` have explicit vocabulary-role comments on the relevant
kernel definitions.** These are definition-home observations,
not runtime-admission or row-lifecycle closure. The generated execution register
is untouched: it requires revision-bound regeneration and still records its
pre-package blockers. Projection/API admission, remaining cardinality decisions,
consumer retirement and whole-row closure are separate obligations.

| Register identity | Base wave | Migration class | Model file / declaration |
|---|---|---|---|
| `EngineeringIncrement` | W2 | MODEL_AUTHORITY_PARITY | `de4sdv_method_context.sysml` / `part def EngineeringIncrement` |
| `FeatureIncrement` | W2 | MODEL_AUTHORITY_PARITY | `de4sdv_method_context.sysml` / `part def FeatureIncrement` |
| `NeedsRequirementsIncrement` | W2 | MODEL_AUTHORITY_PARITY | `de4sdv_method_context.sysml` / `part def NeedsRequirementsIncrement` |
| `IncrementEngineeringQuestion` | W2 | MODEL_AUTHORITY_PARITY | `de4sdv_method_context.sysml` / `part def IncrementEngineeringQuestion` |
| `IncrementLifecycleDecision` | W2 | MODEL_AUTHORITY_PARITY | `de4sdv_method_context.sysml` / `part def IncrementLifecycleDecision` |
| `SignalMappingDisposition` | W2 | MODEL_AUTHORITY_PARITY | `de4sdv_method_process.sysml` / `enum def SignalMappingDisposition` |
| `LogicalToSoftwareSignalMappingRecord` | W2 | MODEL_AUTHORITY_PARITY | `de4sdv_method_process.sysml` / `item def LogicalToSoftwareSignalMappingRecord` |
| `SystemToSoftwareSignalMappingCandidate` | W2 | MODEL_AUTHORITY_PARITY | `de4sdv_method_process.sysml` / `allocation def SystemToSoftwareSignalMappingCandidate` |
| `SystemLayer` | W2 | MODEL_AUTHORITY_PARITY | `de4sdv_method_context.sysml` / `part def SystemLayer` |
| `ProductLine` | W2 | MODEL_AUTHORITY_PARITY | `de4sdv_product_line.sysml` / `part def ProductLine` |
| `MemberProduct` | W2 | MODEL_AUTHORITY_PARITY | `de4sdv_product_line.sysml` / `part def ProductLineMemberProduct` |
| `Feature` | W2 | MODEL_AUTHORITY_PARITY | `de4sdv_product_line.sysml` / `part def ProductLineFeatureCandidate` |
| `ProductLineCharacteristic` | W2 | MODEL_AUTHORITY_PARITY | `de4sdv_product_line.sysml` / `part def ProductLineCharacteristic` |
| `CommonCapability` | W2 | MODEL_AUTHORITY_PARITY | `de4sdv_product_line.sysml` / `part def CommonProductLineCapability` |
| `DeferredProductLineScope` | W2 | MODEL_AUTHORITY_PARITY | `de4sdv_product_line.sysml` / `part def DeferredProductLineScope` |
| `Stakeholder` | W2 | MODEL_AUTHORITY_PARITY | `de4sdv_stakeholders.sysml` / `part def Stakeholder` |
| `Need` | W2 | MODEL_AUTHORITY_PARITY | `de4sdv_method_context.sysml` / `requirement def StakeholderNeedCandidate` |
| `Requirement` | W2 | MODEL_AUTHORITY_PARITY | `de4sdv_method_context.sysml` / `requirement def RequirementCandidate` |
| `ProblemStatement` | W2 | MODEL_AUTHORITY_PARITY | `de4sdv_method_context.sysml` / `requirement def ProblemStatement` |
| `RegulatoryConstraint` | W2 | MODEL_AUTHORITY_PARITY | `de4sdv_method_context.sysml` / `requirement def RegulatoryConstraintCandidate` |
| `ArchitectureElement` | W2 | NEW_APPLICATION_SEMANTICS | `de4sdv_method_context.sysml` / `package DE4SDV_MethodContext` |
| `Function` | W2 | NEW_APPLICATION_SEMANTICS | `de4sdv_method_context.sysml` / `package DE4SDV_MethodContext` |
| `LogicalElement` | W2 | NEW_APPLICATION_SEMANTICS | `de4sdv_method_context.sysml` / `package DE4SDV_MethodContext` |
| `PhysicalElement` | W2 | NEW_APPLICATION_SEMANTICS | `de4sdv_method_context.sysml` / `package DE4SDV_MethodContext` |
| `Scenario` | W2 | MODEL_AUTHORITY_PARITY | `de4sdv_operational_context.sysml` / `part def Scenario` |
| `ValidationScenario` | W4 | NEW_APPLICATION_SEMANTICS | `de4sdv_operational_context.sysml` / `package DE4SDV_OperationalContext` |
| `AcceptanceCriterion` | W2 | NEW_APPLICATION_SEMANTICS | `de4sdv_method_context.sysml` / `requirement def AcceptanceCriterion` |
| `Assumption` | W2 | MODEL_AUTHORITY_PARITY | `de4sdv_method_context.sysml` / `part def IncrementAssumption` |
| `Gap` | W2 | MODEL_AUTHORITY_PARITY | `de4sdv_method_context.sysml` / `part def IncrementGap` |
| `MissingRealizationRecord` | W2 | MODEL_AUTHORITY_PARITY | `de4sdv_method_context.sysml` / `part def MissingRealizationRecord` |
| `BlockedRealizationBranchRecord` | W2 | MODEL_AUTHORITY_PARITY | `de4sdv_method_context.sysml` / `part def BlockedRealizationBranchRecord` |
| `AssuranceClaim` | W2 | NEW_APPLICATION_SEMANTICS | `de4sdv_scoped_assurance.sysml` / `package DE4SDV_ScopedAssurance` |
| `MethodEvaluationScope` | W2 | MODEL_AUTHORITY_PARITY | `de4sdv_method_conformance.sysml` / `part def MethodEvaluationScope` |
| `addressesConcern` | W4 | NEW_APPLICATION_SEMANTICS | `de4sdv_method_vocabulary_carriers.sysml` / `connection def AddressesConcern` |
| `hasStakeholder` | W4 | NEW_APPLICATION_SEMANTICS | `de4sdv_method_context.sysml` / `part def EngineeringIncrement` |
| `selectedViewpoint` | W4 | NEW_APPLICATION_SEMANTICS | `de4sdv_method_vocabulary_carriers.sysml` / `connection def SelectedViewpoint` |
| `producesView` | W4 | NEW_APPLICATION_SEMANTICS | `de4sdv_method_vocabulary_carriers.sysml` / `connection def ProducesView` |
| `hasAcceptanceCriterion` | W2 | NEW_APPLICATION_SEMANTICS | `de4sdv_method_context.sysml` / `requirement def AcceptanceCriterion` |
| `recordsAssumption` | W4 | NEW_APPLICATION_SEMANTICS | `de4sdv_method_vocabulary_carriers.sysml` / `connection def RecordsAssumption` |
| `recordsGap` | W4 | NEW_APPLICATION_SEMANTICS | `de4sdv_method_vocabulary_carriers.sysml` / `connection def RecordsGap` |

## Validation request and source grammar

The standalone form is defined by KerML 8.2.4.1.4 (`Disjoining`):
`('disjoining' Identification)? 'disjoint' Type 'from' Type RelationshipBody`.
SysML documentation allows `doc Identification? /* body */`; named
Documentation avoids inventing semantic types for umbrella terms.
Grammar inspection is not evidence of the pinned licensed parser accepting
mixed SysML/KerML syntax. Request maintainer-run **Privileged Syside Validation**
for the eventual exact reviewed revision, validating both model roots,
new documentation/comment references, exclusion reference/constraint typing,
multiple requirement inheritance and native disjoining. The licensed check must
also reject a separate synthetic dual-typed usage. If that toolchain rejects
native disjoining, use the owner-authorized checked-constraint fallback and
report the change. This host is aarch64; no local licensed result is claimed.
No workflow is dispatched by this package.

Grammar sources (inspection only; no toolchain pin change):

- [KerML textual BNF, SysML-v2-Release fb97b754](https://github.com/Systems-Modeling/SysML-v2-Release/blob/fb97b754f29588b8e9c7a35f370880cd15eb29e7/bnf/KerML-textual-bnf.kebnf)
- [SysML pilot grammar, 2026-08](https://github.com/Systems-Modeling/SysML-v2-Pilot-Implementation/blob/2026-08/org.omg.sysml.xtext/src/org/omg/sysml/xtext/SysML.xtext)

## Generated artifacts and frozen runtime

Generated outputs are not hand-edited or rebound to a commit that lacks the
input bytes. The documented generators require the input commit first, then
artifact generation bound to that real revision (the two-commit pattern;
squash delivery additionally needs permanent revision recovery). This package
is staged/uncommitted by instruction, so revision-bound regeneration is blocked.
Keep generated-chain failures visible; no gate bypass or fake ingestion.

O3's 13 frozen identities, the runtime build files and composition sidecar
sources are preserved byte-for-byte against the package base. Only definition
homes and explicitly requested reusable typing/structure are supplied here;
no semantic runtime sources, PLEML files, dependency pins, acceptance records,
consumer routing or policy activation change.
