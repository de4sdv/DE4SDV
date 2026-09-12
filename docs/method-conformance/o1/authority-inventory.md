# O1 Semantic Authority Inventory — generated review table

Generated from the canonical inventory data by `scripts/generate_semantic_authority_inventory.py`; do not edit by hand. The canonical machine-readable artifact is `semantic-authority-inventory.json`.

## Binding

- Source revision: `6817f7ebe5679d5ae9859b3f7eddd72a61d2d83e`
- Artifact commit: unclaimed (cannot be known when the artifact is generated)
- ontology_contract: `approach/framework/ontology/de4sdv-basic-ontology.yaml` (sha256:80dd19ae748183a2b886fb83f4d832bcb8f17f31c1e052175544208356a854c4)
- reviewed_decisions: `docs/method-conformance/o1/authority-review-decisions.yaml` (sha256:1b346a9b1d799465eba84f64e24c6b28b3cff4ed8ebb839feb790fdd9e9d285c)
- closure_evidence: `docs/method-conformance/o1/closure-evidence.json` (sha256:96578697f05d64ec26b25b81b78b978d55235bc66cf8c1c872f2e33b63f80171)
- runtime_strategy_source: `de4sdv/semantic/traversal.py` (sha256:ed6b1cee3a422d181e9e4c8a7b8c6374e1bde67c4f1c1cfc0d6751378417d86a)
- Bound inputs: 25 files (content-addressed; see the canonical JSON `binding.bound_inputs`)

## Coverage

| Metric | Count |
|---|---|
| classes | 59 |
| relationships | 34 |
| total_entries | 93 |
| relationship_mappings | 9 |
| relationship_vocabulary_only | 25 |
| kernel_declarations_governed_dir | 110 |
| kernel_mapped_in_dir | 39 |
| kernel_mapped_out_of_dir | 1 |
| kernel_exclusions | 71 |
| governance_rules | 10 |
| runtime_strategies_implemented | 8 |
| runtime_strategies_unassociated | 2 |
| authority_current_counts | accepted-library-grounded: 2, external-reference: 3, legacy-yaml: 78, model-authoritative: 3, native-sysml: 6, unknown: 1 |
| authority_target_counts | accepted-library-grounded: 12, de4sdv-application-semantic: 4, external-reference: 2, model-authoritative: 61, native-sysml: 8, unknown: 6 |
| authority_target_conditional_counts | accepted-library-grounded: 8, de4sdv-application-semantic: 1 |
| evidence_state_counts | blocked: 14, privileged-closure-proven: 3, repository-evidenced: 75, unknown: 1 |
| adoption_status_counts | accepted: 4, candidate: 1, not-applicable: 77, pinned-not-adopted: 8, rejected: 3 |

## Classes (59)

| id | grounding | runtime support | authority (current -> target) | evidence | adoption | disposition | stage | closure |
|---|---|---|---|---|---|---|---|---|
| EngineeringIncrement | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml: part def EngineeringIncrement | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| FeatureIncrement | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml: part def FeatureIncrement | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| NeedsRequirementsIncrement | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml: part def NeedsRequirementsIncrement | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| IncrementEngineeringQuestion | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml: part def IncrementEngineeringQuestion | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| IncrementLifecycleDecision | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml: part def IncrementLifecycleDecision | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| IncrementTraceabilityShell | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml: part def IncrementTraceabilityShell | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| MethodPhase | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_process.sysml: enum def MethodPhase | consumed by method-conformance data | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| SignalMappingDisposition | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_process.sysml: enum def SignalMappingDisposition | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| LogicalToSoftwareSignalMappingRecord | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_process.sysml: item def LogicalToSoftwareSignalMappingRecord | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| SystemToSoftwareSignalMappingCandidate | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_process.sysml: allocation def SystemToSoftwareSignalMappingCandidate | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| IncrementSize | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_process.sysml: enum def IncrementSize | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| SystemLayer | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml: part def SystemLayer | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| ProductLine | textual-notation-of-model/packages/methods/de4sdv/de4sdv_product_line.sysml: part def ProductLine | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| MemberProduct | textual-notation-of-model/packages/methods/de4sdv/de4sdv_product_line.sysml: part def ProductLineMemberProduct | consumed (identity/lineage) | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| Feature | textual-notation-of-model/packages/methods/de4sdv/de4sdv_product_line.sysml: part def ProductLineFeatureCandidate | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| ProductLineCharacteristic | textual-notation-of-model/packages/methods/de4sdv/de4sdv_product_line.sysml: part def ProductLineCharacteristic | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| CommonCapability | textual-notation-of-model/packages/methods/de4sdv/de4sdv_product_line.sysml: part def CommonProductLineCapability | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| DeferredProductLineScope | textual-notation-of-model/packages/methods/de4sdv/de4sdv_product_line.sysml: part def DeferredProductLineScope | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| VariationPoint | native: SysML v2 variation definition/usage | vocabulary-only | native-sysml -> native-sysml | repository-evidenced | not-applicable | keep-as-is | O2+ (parity pointer) |  |
| Variant | native: SysML v2 variant usage | vocabulary-only | native-sysml -> native-sysml | repository-evidenced | not-applicable | keep-as-is | O2+ (parity pointer) |  |
| FeatureConfiguration | external: Bill-of-Features records under model-based-product-line-engineering/feature-configurations/ resolved against the feature catalogue in model-based-product-line-engineering/feature-models/ | vocabulary-only | external-reference -> accepted-library-grounded [cond] | blocked | pinned-not-adopted | retain-explicit-external-boundary | PLE |  |
| Stakeholder | textual-notation-of-model/packages/methods/de4sdv/de4sdv_stakeholders.sysml: part def Stakeholder | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | candidate | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| Concern | native: SysML v2 concern def and concern usage; kernel examples in DE4SDV_MethodViewpoints | vocabulary-only | native-sysml -> native-sysml | repository-evidenced | not-applicable | keep-as-is | O2+ (parity pointer) |  |
| Need | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml: requirement def StakeholderNeedCandidate | consumed (identity/lineage) | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| Requirement | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml: requirement def RequirementCandidate | consumed (identity/lineage) | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| ProblemStatement | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml: requirement def ProblemStatement | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| ArchitectureDecisionRecord | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml: part def ArchitectureDecisionRecord | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| RegulatoryConstraint | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml: requirement def RegulatoryConstraintCandidate | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| ArchitectureElement | native: part def, port def, and behavior definitions in feature and architecture slices | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | defer | O2+ (design decision) |  |
| Function | native: SysML v2 action/state/behavior definitions in functional-architecture slices | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | defer | O2+ (design decision) |  |
| LogicalElement | native: part def elements in logical-architecture slices | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | defer | O2+ (design decision) |  |
| PhysicalElement | native: part def elements in physical/software realization slices | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | defer | O2+ (design decision) |  |
| Interface | native: SysML v2 port def and connection elements | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | defer | O2+ (design decision) |  |
| Scenario | native: Operational-context parts plus scenario-identity enums (for example MiddlewareScenarioIdentity) in verification slices | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| VerificationCase | native: SysML v2 verification def; see aebs and middleware verification slices | consumed (verifiedBy) | native-sysml -> native-sysml | repository-evidenced | not-applicable | prove-existing-model-authority | c2 |  |
| ValidationScenario | native: Scenario parts with bounded validation outcomes (for example passBoundedValidation) | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | O2+ |  |
| VerificationMethod | external: ODE4HERA requirements-management library verificationMethod (NRM A8) populated with the SysML standard-library VerificationMethodKind values | consumed (model attributes) | accepted-library-grounded -> accepted-library-grounded | repository-evidenced | accepted | keep-as-is | O2+ (parity) |  |
| AcceptanceCriterion | textual-notation-of-model/packages/features/middleware/middleware_verification_evidence.sysml: requirement def MiddlewareAcceptanceCriterion | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| EvidenceArtifact | external: Evidence registers and retained-evidence items referenced by verification slices (for example RetainedMiddlewareEvidence) and bench evidence YAML records | vocabulary-only | external-reference -> external-reference | repository-evidenced | not-applicable | retain-explicit-external-boundary | T/E |  |
| EvidenceContract | native: Requirement usages verified by SysML v2 verification cases in DE4SDV verification slices | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| EvidenceStatus | external: ODE4HERA requirements-management library VVStatus (NRM A13+A14) via the DE4SDV method-context adapter | consumed (model attributes) | accepted-library-grounded -> accepted-library-grounded | repository-evidenced | accepted | keep-as-is | O2+ (parity) |  |
| Assumption | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml: part def IncrementAssumption | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| Gap | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml: part def IncrementGap | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| MissingRealizationRecord | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml: part def MissingRealizationRecord | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| BlockedRealizationBranchRecord | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml: part def BlockedRealizationBranchRecord | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| AssuranceClaim | native: Claim usages framed by the argumentation-assurance viewpoint | vocabulary-only | unknown -> unknown | unknown | not-applicable | defer | O2+ |  |
| Viewpoint | native: SysML v2 viewpoint def; kernel selections in DE4SDV_MethodViewpoints and SAF_Viewpoints | vocabulary-only | native-sysml -> native-sysml | repository-evidenced | not-applicable | keep-as-is | O2+ (parity pointer) |  |
| View | native: SysML v2 view | vocabulary-only | native-sysml -> native-sysml | repository-evidenced | not-applicable | keep-as-is | O2+ (parity pointer) |  |
| TraceLink | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_process.sysml: item def TraceLink | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| RequiredTraceChain | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_process.sysml: part def RequiredTraceChain | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| Baseline | textual-notation-of-model/packages/methods/de4sdv/de4sdv_operational_context.sysml: part def DE4SDVEvidenceBaseline | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| MethodContractObligation | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_conformance.sysml: item def MethodContractObligation | consumed by method-conformance (Lane C/D) | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | c1 (conformance batch) |  |
| EvaluationSourceKind | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_conformance.sysml: enum def EvaluationSourceKind | consumed by method-conformance (Lane C/D) | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | c1 (conformance batch) |  |
| MethodEvaluationScope | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_conformance.sysml: part def MethodEvaluationScope | consumed by method-conformance (Lane C/D) | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | c1 (conformance batch) |  |
| EvaluationScopeMembership | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_conformance.sysml: item def EvaluationScopeMembership | consumed by method-conformance (Lane C/D) | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | c1 (conformance batch) |  |
| TestedScopeDeclaration | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_conformance.sysml: item def TestedScopeDeclaration | consumed by method-conformance (Lane C/D) | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | c1 (conformance batch) |  |
| RetainedExecutionRecordReference | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_conformance.sysml: item def RetainedExecutionRecordReference | consumed by method-conformance (Lane C/D) | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | c1 (conformance batch) |  |
| AcceptanceAttestationReference | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_conformance.sysml: item def AcceptanceAttestationReference | consumed by method-conformance (Lane C/D) | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | c1 (conformance batch) |  |
| DerivesFromNeed | textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml: connection def DerivesFromNeed | vocabulary-only | model-authoritative -> model-authoritative | privileged-closure-proven | rejected | keep-as-is | K | r6-3 |

## Relationships (34)

| id | grounding | runtime support | authority (current -> target) | evidence | adoption | disposition | stage | closure |
|---|---|---|---|---|---|---|---|---|
| addressesConcern | EngineeringIncrement -> Concern | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| hasStakeholder | EngineeringIncrement -> Stakeholder | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| selectedViewpoint | EngineeringIncrement -> Viewpoint | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| producesView | EngineeringIncrement -> View | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| derivesNeedFromConcern | Need -> Concern | vocabulary-only | legacy-yaml -> de4sdv-application-semantic [cond] | blocked | not-applicable | introduce-minimal-de4sdv-relation | c4 |  |
| derivesRequirementFromNeed | Requirement -> Need (derivation-connection) | supported (closure-verified) | model-authoritative -> model-authoritative | privileged-closure-proven | rejected | keep-as-is | K | r6-3 |
| derivedRequirementsOfNeed | Need -> Requirement (derivation-connection) | supported (closure-verified) | model-authoritative -> model-authoritative | privileged-closure-proven | rejected | keep-as-is | K | r6-3 |
| constrainedBy | Requirement -> RegulatoryConstraint | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| specifiesFeature | Requirement -> Feature | vocabulary-only | legacy-yaml -> accepted-library-grounded [cond] | blocked | pinned-not-adopted | defer | PLE |  |
| specifiesCommonCapability | Requirement -> CommonCapability | vocabulary-only | legacy-yaml -> accepted-library-grounded [cond] | blocked | pinned-not-adopted | defer | PLE |  |
| realizedBy | Requirement -> ArchitectureElement (allocation) | implemented (allocation) | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | prove-existing-model-authority | c5 |  |
| specifiesFunction | Requirement -> Function (dependency) | implemented (dependency) | legacy-yaml -> de4sdv-application-semantic | repository-evidenced | not-applicable | prove-existing-model-authority | c5 |  |
| hasRelevantArchitecture | Requirement -> ArchitectureElement (dependency) | implemented (dependency) | legacy-yaml -> de4sdv-application-semantic | repository-evidenced | not-applicable | prove-existing-model-authority | c5 |  |
| allocatedTo | Function -> LogicalElement | vocabulary-only | legacy-yaml -> unknown | blocked | not-applicable | defer | T/E |  |
| deployedTo | LogicalElement -> PhysicalElement | vocabulary-only | legacy-yaml -> unknown | blocked | not-applicable | defer | T/E |  |
| verifiedBy | Requirement -> VerificationCase (verification-membership) | implemented (verification-membership) | legacy-yaml -> native-sysml | repository-evidenced | not-applicable | prove-existing-model-authority | c2 |  |
| usesVerificationMethod | VerificationCase -> VerificationMethod | vocabulary-only | legacy-yaml -> accepted-library-grounded | repository-evidenced | accepted | adopt-accepted-library-relation | batched-parity (post-0a/0b) |  |
| hasAcceptanceCriterion | VerificationCase -> AcceptanceCriterion | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| validatedBy | Need -> ValidationScenario | vocabulary-only | legacy-yaml -> unknown | blocked | not-applicable | defer | O2+ |  |
| validatesFitnessForUse | ValidationScenario -> Need | vocabulary-only | legacy-yaml -> unknown | blocked | not-applicable | defer | O2+ |  |
| hasEvidence | VerificationCase -> EvidenceArtifact (external) | external (no traversal) | external-reference -> external-reference | repository-evidenced | not-applicable | retain-explicit-external-boundary | T/E |  |
| hasEvidenceStatus | EvidenceArtifact -> EvidenceStatus | vocabulary-only | legacy-yaml -> accepted-library-grounded | repository-evidenced | accepted | adopt-accepted-library-relation | batched-parity (post-0a/0b) |  |
| recordsAssumption | EngineeringIncrement -> Assumption | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| recordsGap | EngineeringIncrement -> Gap | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | batched-parity (post-0a/0b) |  |
| supportedByEvidence | AssuranceClaim -> EvidenceArtifact | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | O2+ |  |
| appliesToMemberProduct | FeatureConfiguration -> MemberProduct | vocabulary-only | legacy-yaml -> accepted-library-grounded [cond] | blocked | pinned-not-adopted | defer | PLE |  |
| hasSubject | Requirement -> MemberProduct (subject-membership) | implemented (subject-membership) | legacy-yaml -> native-sysml | repository-evidenced | not-applicable | prove-existing-model-authority | c3 |  |
| hasRelevantEvidenceContract | Requirement -> EvidenceContract (dependency) | implemented (dependency) | legacy-yaml -> de4sdv-application-semantic | repository-evidenced | not-applicable | prove-existing-model-authority | c5 |  |
| selectsFeature | FeatureConfiguration -> Feature | vocabulary-only | legacy-yaml -> accepted-library-grounded [cond] | blocked | pinned-not-adopted | defer | PLE |  |
| instantiatesCanonicalArchitecture | MemberProduct -> ArchitectureElement | vocabulary-only | legacy-yaml -> unknown | blocked | not-applicable | defer | T/E |  |
| includesCommonCapability | FeatureConfiguration -> CommonCapability | vocabulary-only | legacy-yaml -> accepted-library-grounded [cond] | blocked | pinned-not-adopted | defer | PLE |  |
| variesAt | Feature -> VariationPoint | vocabulary-only | legacy-yaml -> accepted-library-grounded [cond] | blocked | pinned-not-adopted | defer | PLE |  |
| selectsVariant | FeatureConfiguration -> Variant | vocabulary-only | legacy-yaml -> accepted-library-grounded [cond] | blocked | pinned-not-adopted | defer | PLE |  |
| capturedInBaseline | EvidenceArtifact -> Baseline | vocabulary-only | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | O2+ |  |

## Reviewed consumer associations (Layer B) with witnessed evidence (Layer A)

| class | support | consumer | role | evidence (witnessed) |
|---|---|---|---|---|
| MethodPhase | consumed by method-conformance data | method-conformance model data (phase attribute typing) | phase enumeration class consumed as a typed attribute in method-contract items | sysml-type-usage 'MethodPhase' in textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_conformance.sysml |
| MemberProduct | consumed (identity/lineage) | de4sdv/semantic/impact.py | kernel-bound identity/lineage class consumed as a product-line traversal root | python-string-constant 'MemberProduct' in de4sdv/semantic/impact.py |
| Need | consumed (identity/lineage) | de4sdv/semantic/projection.py (K projection) | kernel-bound identity/lineage class consumed as a projection binding root | python-string-constant 'Need' in de4sdv/semantic/projection.py |
| Requirement | consumed (identity/lineage) | de4sdv/semantic/impact.py | kernel-bound identity/lineage class consumed as an impact binding root | python-string-constant 'Requirement' in de4sdv/semantic/impact.py |
| VerificationCase | consumed (verifiedBy) | de4sdv/semantic/impact.py (verifiedBy category) | native verification-case class consumed by the verifiedBy traversal | python-string-constant 'VerificationCase' in de4sdv/semantic/impact.py |
| VerificationMethod | consumed (model attributes) | DE4SDV model metadata usages + method-conformance evaluator | model-attribute class consumed via @VerificationMethod metadata annotations | sysml-code-token '@VerificationMethod' in textual-notation-of-model/packages/features/aebs/aebs_degraded_input_verification.sysml, exact-token 'VerificationMethod' in de4sdv/semantic/method_evaluator.py |
| EvidenceStatus | consumed (model attributes) | DE4SDV method-context adapter (ODE4HERA VVStatus) | external status-attribute vocabulary imported through the method-context adapter | sysml-code-token 'VVStatus' in textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml |
| MethodContractObligation | consumed by method-conformance (Lane C/D) | Lane C/D method-conformance pilot data (obligation items) | method-contract obligation class consumed by the declared pilot obligation items | sysml-type-usage 'MethodContractObligation' in textual-notation-of-model/packages/features/aebs/aebs_override_verification.sysml |
| EvaluationSourceKind | consumed by method-conformance (Lane C/D) | method-conformance model data (evaluationSource attribute typing) | evaluation-source enumeration class consumed as a typed attribute in obligations | sysml-type-usage 'EvaluationSourceKind' in textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_conformance.sysml |
| MethodEvaluationScope | consumed by method-conformance (Lane C/D) | de4sdv/semantic/method_contract.py | evaluation-scope dataclass mirroring the model-resident scope vocabulary | python-identifier 'MethodEvaluationScope' in de4sdv/semantic/method_contract.py |
| EvaluationScopeMembership | consumed by method-conformance (Lane C/D) | Lane C/D method-conformance pilot data (scope memberships) | scope-membership class consumed by the pilot scope-member items | sysml-type-usage 'EvaluationScopeMembership' in textual-notation-of-model/packages/features/aebs/aebs_override_verification.sysml |
| TestedScopeDeclaration | consumed by method-conformance (Lane C/D) | Lane C/D method-conformance pilot data (tested-scope declaration) | tested-scope declaration class consumed by the pilot testedScope item | sysml-type-usage 'TestedScopeDeclaration' in textual-notation-of-model/packages/features/aebs/aebs_override_verification.sysml |
| RetainedExecutionRecordReference | consumed by method-conformance (Lane C/D) | Lane C/D method-conformance obligation data (execution records) | retained execution-record reference class reserved for C/D execution-record obligations; declaration + obligation data witness | exact-token 'execution-outcome' in docs/method-conformance/pilot-obligations.yaml, exact-token 'item def RetainedExecutionRecordReference' in textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_conformance.sysml |
| AcceptanceAttestationReference | consumed by method-conformance (Lane C/D) | Lane C/D method-conformance pilot data (acceptance attestation) | acceptance-attestation reference class consumed by the pilot acceptanceAttestation item | sysml-type-usage 'AcceptanceAttestationReference' in textual-notation-of-model/packages/features/aebs/aebs_override_verification.sysml |

## Runtime strategy registry

| strategy | association | entries | classification |
|---|---|---|---|
| allocation | ontology-mapping | realizedBy |  |
| dependency | ontology-mapping | hasRelevantArchitecture, hasRelevantEvidenceContract, specifiesFunction |  |
| derivation-connection | ontology-mapping | derivedRequirementsOfNeed, derivesRequirementFromNeed |  |
| external | ontology-mapping | hasEvidence |  |
| property-reference | unassociated-capability |  | unassociated-capability-pending-review |
| subject-membership | ontology-mapping | hasSubject |  |
| verification | unassociated-capability |  | unassociated-capability-pending-review |
| verification-membership | ontology-mapping | verifiedBy |  |

## Closure evidence

| id | git sha | sysml project | sysml commit | workflow run | artifact | archive digest | proof |
|---|---|---|---|---|---|---|---|
| r6-3 | 72926c958d2bd3b1001088fa657ec906dffd53e7 | ea96301d-343a-4592-bad4-5dd997ca906a | 82ef02df-94fe-4100-94c9-2f961f314a28 | 34630102233 | full-model-api-ingestion-72926c958d2bd3b1001088fa657ec906dffd53e7 | sha256:70d37f39798114ceb9fbdb7e975e9ba9959bcae7a298164e204b12fa59d65a93 | pass |
