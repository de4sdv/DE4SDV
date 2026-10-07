# W6 governed transition record (relationship and trace redesigns)

**Draft.** Licensed Syside validation passed on the Wave A integration head
`8432c81` (privileged run 37536280145: `All checks passed!`, committed views
match 5/5). Later commits on this branch need their own exact-head run. This
record documents how the W6 relationship
and trace identities are retired or redesigned in the model under the owner
approvals in
[approved-semantic-decisions.yaml](approved-semantic-decisions.yaml)
(topics 1 to 5). It is a governance record, not runtime authority. Runtime
meaning comes from the model-derived successor contract
(`de4sdv.relationship-successor/v1`). No automatic alias translates an old
signature into a successor, and no signature is changed silently.

What this record does not establish: production activation, consumer
retirement, live API closure, semantic proof beyond what the licensed
parser and validator accept, satisfaction, deployment, completed validation, applicability or compliance.

## Transition table

| Old identity | Disposition | Successor | Model home | What changed | No longer claimed |
| --- | --- | --- | --- | --- | --- |
| `allocatedTo` (`Function -> LogicalElement`) | signature widened by explicit version | `allocatedTo` v1, three end pairs | `de4sdv_relationship_carriers.sysml`: `allocatedToVocabularyRole`; records `requirementAllocation`, `functionAllocation`, `physicalAllocation`; `version` | One predicate over native `AllocationUsage` with governed requirement-to-function, function-to-logical and logical-to-physical end pairs. The old pair is the second end pair. Endpoint classes come from ontology kernel mappings of the endpoint lineage. | Transitivity, composed realization, satisfaction, execution, deployment |
| `realizedBy` | retire name | `allocatedTo` (requirement-to-function pair) | `oldRealization` retirement record | Requirement-sourced native allocations are read as responsibility assignment only. | "Realized" semantics; requirement-to-architecture realization chain |
| `deployedTo` | retire name | `allocatedTo` (logical-to-physical pair) | `oldDeployment` retirement record | Logical-to-physical native allocations are read as responsibility assignment only. | Software deployment, observed operation |
| `specifiesFunction` | retain at weaker meaning | none (unchanged) | `de4sdv_method_context.sysml`: `specifiesFunctionOntologyDefinition` and its comment | Nothing. The requirement-to-function dependency keeps its relevance/specification meaning. Allocations are not converted into dependencies or the reverse. | Allocation, satisfaction, verification |
| `validatedBy` | rename planning association | `hasValidationScenario` | `hasValidationScenarioVocabularyRole`; `validationPlanning` record; `oldValidationForward` | A typed `ValidationPlanningAssociation` from a need to a `ValidationPlanningScenario`. | Completed validation, result, fitness-for-use verdict, stakeholder acceptance |
| `validatesFitnessForUse` | merge | `validationScenarioFor` (inverse of `hasValidationScenario`) | `oldValidationInverse` | Inverse navigation over the same association; no second fact. | An independent validation outcome |
| `constrainedBy` | rename to provenance | `hasRegulatorySource` | `hasRegulatorySourceVocabularyRole`; `regulatoryProvenance` record; `oldRegulatoryName` | A typed `RegulatorySourceAssociation` from a requirement to a `ControlledRegulatorySource`. | Native required constraint, applicability, interpretation, fulfillment, compliance |
| `RequiredTraceChain` | redesign | `IncrementTraceObligations` declared under `ApprovedTraceMethod` | `de4sdv_method_traces.sysml`: historical doc plus comment; `approvedScopedTraceMethod`; `IncrementTraceObligations` | Trace obligations come from the selected approved method for the declared scope, phases and completion claim. RFLP layers stay distinct. | A universal concern-to-baseline chain for every increment |
| `TraceLink` | redesign | native relationships (ownership, typing, subject, `HasStakeholder`, framed concerns, allocations, connections) | `de4sdv_method_traces.sysml`: historical doc plus comment | Trace facts are native relationships with resolvable element ends. | Category-string link records |
| `hasEvidenceStatus` (`EvidenceArtifact -> EvidenceStatus`) | redesign (topic 4) | unchanged adopted `VVStatus` on `ScopedVVActivityRecord` `status` | `de4sdv_scoped_assurance.sysml`: `hasEvidenceStatusVocabularyRole` about `ScopedVVActivityRecord` | Activity status is the pinned `VVStatus` with its subject, configuration, activity, comparison basis and result or evidence references. `EvidenceStatus` resolves to that `VVStatus` and to slice-local bounded outcome or disposition enums. The legacy predicate takes no new model usage. | A universal status enum, artifact maturity, evidence-set adequacy, authority acceptance; `Completed` as passed or accepted |
| `supportedByEvidence` (`AssuranceClaim -> EvidenceArtifact`) | redesign (topic 3) | one `EvidenceSupportCitation` per cited artifact, assessed by `ScopedEvidenceAdequacyAssessment` | `de4sdv_scoped_assurance.sysml`: `supportedByEvidenceVocabularyRole` about `EvidenceSupportCitation`, `ScopedEvidenceAdequacyAssessment` | Cited support for an exact scoped claim with versioned reference, rationale and known limits, distinct from `hasEvidence`. Establishing the claim needs a separate adequacy assessment; acceptance stays a separate `AcceptanceAttestationReference`. | Adequacy or acceptance by citation; citation, adequacy and acceptance implying each other |
| `IncrementTraceabilityShell` | redesign: merge into the `RequiredTraceChain` successor | `IncrementTraceObligations` | `de4sdv_method_traces.sysml`: historical doc plus comment | The two framing usages were migrated together: `visualizationTraceObligations` (INC-AEBS-010) and `traceObligationsMW002` (INC-MW-002). | A populated string shell as completion evidence |

Missing required traces block the declared completion claim unless an
authorized visible disposition permits it. Evaluation that is unavailable
stays UNASSESSED, never a synthetic PASS.

## Migrated model population (this change)

Lexical counts at this branch, before any licensed ingestion. Live closure is
not assessed here.

- **Endpoint lineage for allocatedTo.** Endpoint definitions now specialize
  the governed endpoint classes in INC-AEBS-010 and in the middleware chain.
  The AEBS core slices already carried endpoint lineage before this change,
  with two pre-existing composite exceptions (see the deviation below):
  - `aebs_visualization_functional_architecture.sysml`: 8 action defs
    `:> AllocatableFunction`;
  - `aebs_visualization_logical_architecture.sysml`: 9 role part defs
    `:> LogicalAllocationElement`;
  - `aebs_visualization_physical_software_realization.sysml`: 7 part defs
    `:> PhysicalAllocationElement`. `PinnedAutowareAEBExecution` already
    inherits the lineage from `AutowareAutonomousEmergencyBrakingNode`;
  - `middleware_functional_architecture.sysml`: 7 action defs;
  - `middleware_logical_architecture.sysml`: 6 part defs;
  - `middleware_physical_software_realization.sysml`: 6 client part defs.

  In these six files, composite flows and systems, item defs and port defs
  get no lineage. No allocation was added, removed or retargeted. The middleware
  `SystemToSoftwareSignalMappingCandidate` item mapping stays outside the
  allocatedTo end pairs.

- **Candidate allocatedTo witnesses.** Native allocations whose two endpoints
  now carry governed lineage: 17 requirement-to-function (AEBS needs 7,
  INC-AEBS-010 10), 25 function-to-logical (AEBS 10, INC-AEBS-010 8,
  middleware 7), 29 logical-to-physical (AEBS software 7, AEBS simulation
  7, INC-AEBS-010 9, middleware 6).

- **hasValidationScenario.** All nine AEBS validation-planning rows in
  `methodologies/sysmod-sysmlv2/pilots/aebs-needs-requirements.yaml`
  (`VAL-AEBS-001` to `-008`, `-014`) now have a `ValidationPlanningScenario`
  and a `ValidationPlanningAssociation` in `aebs_needs_requirements.sysml`.
  Before this change only `VAL-AEBS-001` did. The YAML keeps the review
  question, method and status.

- **hasRegulatorySource.** No change. Only the two requirements with a
  controlled R152 source link already carry one. No new provenance was
  invented.

## Engineering naming and wiring choices

- `allocatedTo`, `hasValidationScenario`, `validationScenarioFor` and
  `hasRegulatorySource` are the predicate names. Successor definitions are
  named comments (`<predicate>VocabularyRole`) because these predicates have
  no authored YAML definition. A `<Term>OntologyDefinition` name is reserved
  for YAML-defined text.
- Only actual allocation endpoint definitions gain lineage. In this change's
  files, composites stay plain, so a composite cannot acquire a second layer
  meaning.
- **Recorded deviation (pre-existing, unchanged).** Two AEBS core composites
  carry endpoint lineage: `VehicleTargetAEBSFunctionalFlow`
  (`aebs_functional_architecture.sysml`, `:> AllocatableFunction`) and
  `VehicleTargetAEBSSystem` (`aebs_logical_architecture.sysml`,
  `:> LogicalAllocationElement`). Neither is an allocation endpoint in the
  counted allocations, and each keeps a single layer. Removing the lineage is
  a separate model change. The test pins the AEBS core lineage sets with these
  two names, so a new composite exception fails.
- INC-AEBS-010 is a System 2 instrument. Its requirement, function, logical
  and physical layers use the same governed end pairs. Its
  `nativeAebSource` role is allocated to the System 1 `pinnedAeb`
  execution. That allocation is unchanged and shown here for review.
- The INC-AEBS-010 allocation definition `LogicalRoleToFunction` allocates
  functions to logical roles. Its name reads in the reverse direction; it is
  unchanged.

## Deferred

- **Wave B:** rewire runtime and consumers from the authored YAML
  relationship rows to the successor contract; exact-revision API closure of
  typed allocation ends (the `allocatedTo` register blocker); regenerate the
  generated O4 artifacts.
- **Wave C:** delete the old YAML relationship rows (`realizedBy`,
  `deployedTo`, `allocatedTo` with the old signature, `validatedBy`,
  `validatesFitnessForUse`, `constrainedBy`) and the historical trace class
  rows when no consumer reads them.
- **Wave B:** `variesAt` stays vocabulary-only and is not runtime-queryable.
  Its register evidence gate is native variant membership: a feature usage
  that participates in a variation's variant membership. No such usage
  exists, so the register target (model-authoritative through native
  variation structure, runtime-queryable) is unmet here. The same holds for
  native realizations of `specifiesFeature` and `specifiesCommonCapability`.
  See [kernel-definition-homes.md](kernel-definition-homes.md).
- Exact-head licensed Syside validation of any commit after `8432c81`.
