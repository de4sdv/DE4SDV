# O4 kernel definition homes

**Draft — under review.** Licensed Syside validation runs automatically on
every pull-request head; the pull request carries the exact-head evidence.
Generated artifacts are regenerated with the repository generators and bound
to this branch's commits (temporary binding); a content-only rebind follows
the squash merge.

The remaining authored definitions need durable model homes before O4 can
retire its YAML authority. This package supplies those homes; it does not
retire the authority, rewire consumers, admit predicates or close O4.

## Owner decisions (2026-10-05)

The decisions and their consequences are recorded in
[ADR 0020](../../architecture-decisions/0020-give-ontology-definitions-model-resident-kernel-homes.md).

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
- **D4:** kernel `requirement def EvidenceContract :> RequirementCandidate`,
  specialized today only by `OverrideEvidenceContract` (AEBS) and
  `MiddlewareAcceptanceCriterion`. The other seven AEBS evidence-contract
  definitions do not specialize it yet, so its specialization closure is not
  the evidence-contract population and does not discriminate
  `hasRelevantEvidenceContract`. Its current dependency mapping is unchanged.
  A test pins the population.
- **7:** licensed Syside (PR #328, run 37411981652) rejected the standalone
  KerML `disjoining` inside a SysML package as a syntax error. Per the
  decision's fallback, the axiom is a symmetric **checked constraint**:
  `CommonProductLineCapability` asserts `not (that istype
  ProductLineFeatureCandidate)` and vice versa. The bounded static negative
  probe detects direct and inherited dual typing; it is not a compiler,
  general source parser or licensed semantic-validation verdict.
- **8:** the complete `instantiatesCanonicalArchitecture` definition is owned
  by `DE4SDV_ProductLine`, with **not queryable; no product-to-canonical
  reachability claimed**. No executable mapping or canonical-package selector.

## Definition-text parity and register targets

[kernel-definition-homes.json](kernel-definition-homes.json) is a
location inventory, not a second meaning authority: it contains paths,
declarations and owned Documentation locators, never copies of definition
text. The model owns normalized-exact text for all 76 authored class/predicate
definitions. Exact named docs supplement existing explanatory docs without
changing their reviewed meaning.

Where the text lives:

- 51 definitions own it directly: 40 as an anonymous `doc`, 11 as
  `private doc ontologyDefinition`. The 11 are private so specializations do
  not inherit the text. Where a definition has both, the `ontologyDefinition`
  text is the authored definition and replaces the YAML text at deletion; the
  anonymous doc stays as explanatory documentation. O1's text-parity observer
  reads anonymous docs only, which is why those rows still show `differs`.
- 25 concepts without their own definition use a package-owned
  `doc <Term>OntologyDefinition`. The name is the only link to the concept; a
  test pins every name to its inventory row. Native/library, historical and external
concepts use package-owned documentation, not copied library types, resurrected
trace shells, new assurance taxonomies or PLE configurator authority.

The requested W2/W4 target rows are listed below. **33/40 have exact definition
text. The seven relationship rows have no authored definition field: five use
their existing reviewed, typed vocabulary carriers; `hasStakeholder` and
`hasAcceptanceCriterion` have explicit vocabulary-role comments
(`hasStakeholderVocabularyRole`, `hasAcceptanceCriterionVocabularyRole`) next
to the relevant kernel definitions. The comments do not reuse the predicate
names, because named comments are re-exported by wildcard imports.** These are definition-home observations,
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

## Licensed validation findings

The first exact-head licensed run (run 37411981652) rejected two constructs:

- standalone KerML `disjoining … disjoint A from B;` in a SysML package
  (`syntax-error`). Replaced by the decision-7 checked-constraint fallback.
- named Documentation whose name equals a referenced type
  (`doc VerificationMethod /* … */` in `DE4SDV_MethodContext`) shadowed the
  library metadata `VerificationMethod` for every importer (`Expected Type
  element but found Documentation`, 52 middleware and AEBS usages). All
  umbrella and predicate documentation names now use the
  `<Term>OntologyDefinition` form, so no Documentation name equals a model,
  library or predicate name.

After both repairs the licensed check reports no model errors. The model
changes alter four published renders: the three AEBS product-line views show
the new checked constraint, and the method process view shows the new
definition text. The committed renders are the licensed run's own output, and
the method `VIEWS.md` is regenerated from them with
`scripts/generate_view_index.py`. This host is aarch64, so no local licensed
result is claimed.

## Generated artifacts and frozen runtime

Generated outputs are not hand-edited or rebound to a commit that lacks the
input bytes. Each lane is regenerated with its repository generator and bound
to the branch commit that contains its inputs, in chain order: direct lanes,
then v1.1, then v1.2 and the O3 scope. After the squash merge, a content-only
rebind binds each level to its permanent merge commit. No gate is bypassed.

O3's 13 frozen identities, the runtime build files and composition sidecar
sources are preserved byte-for-byte against the package base. Only definition
homes and explicitly requested reusable typing/structure are supplied here;
no semantic runtime sources, PLEML files, dependency pins, acceptance records,
consumer routing or policy activation change.
