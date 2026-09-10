# DE4SDV Graph Architecture and Deterministic Method-Conformance — Final Implementation Plan

> **For Hermes:** Use the subagent-driven-development skill to implement this plan task-by-task after implementation is requested. This document authorizes no implementation, publication, deployment, or merge.

**Goal:** Preserve DE4SDV's distinct knowledge authorities while making a bounded set of engineering-method obligations reproducibly queryable, with no false completion caused by missing scope, incomplete data, weak evidence, or unauthorized rule changes.

**Architecture:** One revision-bound engineering baseline contains explicitly distinguished engineering subjects, reusable vocabulary, method contracts, and evidence records. An ontology-backed semantic service evaluates approved contracts over that baseline; a separate delivery projection composes the result with live governance state. Git rationale, external evidence, operational memory, and agent orchestration retain their own responsibilities.

**Tech stack:** Existing SysML v2 model packages, SysML API integration, Python semantic services, ontology YAML, read-only MCP, pytest, and GitHub review/CI. No new graph database, solver, protocol, or external library is selected by this plan.

**Status:** Final consolidated planning deliverable incorporating the agreed review corrections. “Final” freezes this planning revision; it does not mean accepted ADR, implemented capability, or authorization to change production. Implementation begins only when requested.

**Finalization basis:** The user’s `DE4SDV_Deterministic_Method_Conformance_Plan_Revised.md`, with the five agreed corrections: acceptance ownership, committed candidate production, independent method discovery, finite V1, and explicit result-field validity. No architecture redesign is introduced.

**Inspection basis:** Local repository HEAD `75d5f6185dc3023596f8b8e340294cdfb5279973`, inspected on 2026-09-08. Remote/main parity was not established for this planning task. Existing working-tree changes were left untouched.

---

## 1. Relationship to the earlier documents

This plan consolidates the useful decisions from `Graph Architecture-2.md` and `DE4SDV_Deterministic_Method_Conformance_Plan_Latest.md`, while correcting the gaps identified in their review.

The first document defines the parent knowledge and authority architecture. The second develops a method-conformance subsystem within its engineering branch. The subsystem must not replace the parent architecture.

The resulting rule is:

> Git records reviewed intent and baseline history. SysML represents modeled engineering state. The ontology defines allowed interpretation. Evidence stores retain observations. Hindsight retains experience. Hermes routes and coordinates. Conformance results are derived findings, never independent authority.

“Modeled engineering state” does not mean independently proven physical truth. A modeled verification relationship, an execution result, and a product acceptance decision are different claims.

### Material changes from the previous plan

- Restore Git/ADRs/docs and the complete question-routing architecture.
- Preserve the System 1/2/3 framing; do not call all product content System 2.
- Use the existing **13 phases, P0–P12**; do not create another phase vocabulary.
- Specify typed contracts, subject identities, per-subject counting, and failure outcomes.
- Bind actual executable inputs and output scope, not just the expected Git SHA.
- Separate evidence recording, execution outcome, acceptance authority, and validity scope.
- Use conservative execution-scope matching in V1; defer automatic cross-baseline evidence reuse.
- Prevent a candidate increment from silently weakening the rules used to accept it.
- Treat capability/release projections as baseline queries, not sums of increment statuses.
- Make the conformance engine phase-neutral across P0–P12; Phase 10 is only the first validation slice, not the V1 scope boundary.
- Support pre-merge candidate feedback through the same evaluator on validated exact-revision API or snapshot inputs; merge/deployment is not required to discover candidate gaps.
- Expose the selected method obligations to agents as queryable contract data while keeping completion judgment inside the deterministic evaluator.

## 2. Decisions and non-goals

### Decisions

1. Each evaluation uses one resolved engineering baseline and one explicit validated SysML API project/commit binding. Method and engineering content resolve together. Candidate imports are isolated revisions or staging instances, not a second process authority; their creation cannot change the published accepted-baseline selection.
2. Include the selected method definitions in that resolved baseline. Pin external dependencies and reject unresolved imports.
3. Express machine-checkable method contracts in SysML using a bounded, typed vocabulary. Implement generic operators in the semantic service and engineering predicate bindings in the ontology contract.
4. Reuse native SysML relationship semantics. Names, embeddings, comments, and generic dependencies cannot substitute for verification or satisfaction semantics.
5. Keep conformance evaluation read-only. Model changes, evidence ingestion, review, and baseline publication are separate controlled workflows.
6. Implement a phase-neutral deterministic conformance engine for the existing P0–P12 method, and validate that engine first on one difficult evidence-bearing Phase-10 pilot slice. Phase 10 is the validation vehicle, not the architectural scope of V1.
7. After the Phase-10 pilot proves the generic contract/evaluator semantics, add additional P0–P12 phase contracts incrementally using the same engine; no phase-specific evaluator branches are permitted.
8. Require complete, explicit evaluation scope before absence can be treated as a normative failure or a legitimate empty population.
9. Compose operational delivery readiness outside the deterministic evaluator.

### Terminology and architectural independence

Use DE4SDV-native terminology such as **method contract**, **conformance evaluation**, **evaluation scope**, **obligation**, **gap**, and **next obligation**. Do not introduce external workflow-product terminology as normative DE4SDV concepts merely because another tool uses a similar deterministic agent loop. Similarity in the generic pattern “agent acts; deterministic evaluator judges” does not change DE4SDV's authority model, SysML semantics, result algebra, or evidence model.

### Non-goals

- A universal knowledge graph merging Git, SysML, Hindsight, and personal research.
- A second authoritative process graph or manually maintained graph mirror.
- Arbitrary SysML expression execution, a general solver, or a general-purpose rules platform.
- LLM judgments about structural completeness, evidence acceptance, or engineering adequacy.
- Automated certification, homologation, safety, or product-release approval.
- A new agent organization, role-assignment model, or write-capable MCP surface.
- Full impact-aware freshness or cumulative capability/release metrics in V1. All P0–P12 phases are in architectural scope, but only obligations that have reviewed executable contracts are assessed; unsupported phases remain explicitly unassessed rather than implicitly complete.
- Adoption or vendoring of another project's method/library without the established upstream coordination and review process.

## 3. Parent authority and routing architecture

| Concern | Authoritative source for that concern | Agent/evaluator behavior |
|---|---|---|
| Reviewed baseline, method adoption, rationale, architecture decisions | Exact Git revision, reviewed ADRs/docs, attributable governance records | Retrieve and cite the relevant revision; a proposal is not an accepted decision |
| Modeled elements and native relationships | Validated, bound SysML API project/commit | Query through the semantic service; return identity and relationship provenance |
| Meaning and permitted traversal | Pinned ontology/kernel contract | Execute only declared, tested mappings |
| Observed execution payloads | Immutable evidence artifacts and provenance | Reference content digests and retained execution context; do not infer observations |
| Evidence acceptance | Attributable decision under an identified authorization policy | Verify the decision's binding and authority; storage in SysML alone does not authorize it |
| Current PR/review/CI readiness | Exact-head delivery/governance state | Query separately and timestamp the observation |
| Previous discussions, experiments, failures | Hindsight operational memory, with original references where available | Recall for continuity, not current model facts or final decision authority |
| External technical knowledge | Appropriate primary source | Retrieve independently; personal notes remain secondary |

```text
Hermes: reasoning, source routing, and work coordination
  |
  +-- Git / ADRs / docs ---------------- reviewed intent and rationale
  |
  +-- read-only semantic MCP
  |       |
  |       +-- semantic service ---------- modeled facts and conformance
  |               +-- validated SysML API baseline
  |               +-- ontology/predicate contract
  |               +-- generic method evaluator
  |
  +-- delivery projection -------------- live exact-head PR/review/CI state
  |
  +-- Hindsight ------------------------ operational experience
  |
  +-- external research ---------------- primary sources; optional personal notes
```

Mixed questions may use several sources, but each claim retains its authority and revision. Memory can suggest where to inspect; it cannot overwrite a model-backed result. A graph fact can establish what is modeled, not why an ADR was accepted.

Promotion to accepted project authority remains explicit: discussion/research → proposed issue/ADR/model change → review → accepted baseline → validated published API binding. Independently, an exact unmerged candidate may pass validation/import and become queryable as candidate state before acceptance, using Section 12. Semantic validation is not governance acceptance. Memory retention never performs either promotion automatically.

The semantic evaluator has no dependency on Hindsight. Hermes remains replaceable as a client. The protocol adapter contains no engineering interpretation.

## 4. System framing and graph partitions

Preserve the existing repository framing:

- **System 1:** the configurable SDV product line and configured variants.
- **System 2:** the life-cycle engineering and assurance system that manages System 1.
- **System 3:** the ecosystem, governance, and method evolution that govern and evolve System 2.

The method is System 3 content used by System 2 to govern engineering work about System 1 and, where explicitly scoped, System 2 itself. These system roles are not database partitions.

Within the resolved graph, distinguish evaluation roles:

| Graph role | Examples | Default treatment |
|---|---|---|
| Engineering subject | Product requirement, interface, verification case, engineering-system artifact | Eligible only through explicit evaluation scope and type constraints |
| Method contract | Obligation, selector definition, phase dependency | Governs evaluation; not an ordinary product obligation subject |
| Reusable vocabulary | Definitions used to type engineering and method elements | Available for interpretation, not automatically a subject |
| Evidence and decision record | Execution record, acceptance attestation, scope manifest | Read as typed supporting records with provenance |

Positive, explicit memberships identify engineering subjects. Importing a method type or specializing a reusable definition does not make the definition an engineering subject.

Validate that ordinary product selectors do not select method contracts. A dedicated method-evolution review may target method artifacts explicitly; it is not inferred from ownership paths. Shared vocabulary references remain legal. Do not impose a global disjointness rule that prevents legitimate cross-layer relationships.

## 5. Identity, resolution, and graph completeness

### Identity

- Use revision-qualified API UUIDs to identify objects within one imported baseline.
- Require repository-persisted explicit identifiers for pilot subjects, obligations, increments, and evidence that must survive imports or renames.
- Resolve each persistent identifier to exactly one compatible API object in the bound revision. Missing, duplicate, and incompatible bindings are errors; do not choose a candidate by name similarity.
- Names and qualified names are presentation and discovery aids, not sufficient durable evidence identities.
- Preserve relationship-object identities and direction in returned evidence paths.
- A rename preserves the explicit identifier. Replacement/retirement uses an explicit reviewed relationship; identifiers are not silently recycled.
- Reimport tests must preserve persistent-identifier correspondence, not demand identical importer-assigned UUIDs.

The existing identity resolver remains available for interactive discovery. Normative conformance adds stricter type/scope validation and must not silently fall back to structural-name matching.

### Completeness

A resolved baseline must declare its import roots, pinned dependencies, validation status, and supported semantic representation. Loading must finish pagination and validate referenced objects required for evaluation.

An API error, unreadable page, unsupported representation, unresolved import, or missing necessary reference is not an empty graph and not evidence that a required relation is absent.

V1 evaluates a validated full-model baseline at an exact committed revision, including an unmerged candidate. The response distinguishes candidate state from the published accepted baseline. Synthetic fixtures retain explicit fixture scope and cannot produce a current full-model claim. No partial query or fixture may be promoted to full-baseline completeness. V1 does not evaluate dirty working trees.

## 6. Increment contribution and evaluation scope

An increment needs two distinct sets:

1. **Contribution set:** explicit elements introduced or changed by that increment, with the V1 relation limited to “contributes.”
2. **Evaluation scope:** all subjects that the increment is required to evaluate, including reused or affected elements when declared by its reviewed scope.

Contribution membership is not automatically the entire impact set. A reusable verification case may be in evaluation scope without being newly contributed. V1 makes this scope explicit and reviewed; it does not claim exhaustive inferred impact coverage.

Each evaluation scope binds:

- increment identifier and governing contract;
- root subject identifiers and eligible types;
- selected member-product/configuration identity, or explicit variant-independent scope;
- expected subject population policy;
- allowed relationship expansion, if any;
- completeness/impact boundary and exclusions with rationale.

Prefer the existing normative increment vocabulary where it fits. `IncrementContributionMembership` is a proposed domain concept, not a new native SysML metaclass; its concrete SysML representation must be validated in the round-trip pilot.

For the first evidence-bearing Phase-10 pilot, require a non-empty subject set. Do not treat a missing subject selector or missing increment membership as “not applicable.”

## 7. Minimal typed method-contract schema

This is a semantic schema, not asserted valid SysML syntax. The first implementation increment must choose and prove its native representation.

| Field | Required semantics |
|---|---|
| `obligation_id` | Stable explicit identifier; unique in the selected method |
| `phase` | Reference to an existing `MethodPhase` literal |
| `subject_selector` | Typed selection from the declared evaluation scope; no free-text inference |
| `applicability` | Restricted typed condition over pinned model/configuration data |
| `population_policy` | Minimum population and explicit permitted-empty disposition |
| `predicate` | Pinned ontology predicate identifier with declared input/output types |
| `target_filters` | Typed conditions on returned targets, not implicitly on subjects |
| `cardinality` | Integer bounds over distinct qualifying targets **per applicable subject** |
| `required` | Whether failure blocks this declared contract scope |
| `evaluation_source` | Pinned model record, pinned repository artifact, or live delivery adapter |
| `attestation_policy_ref` | Required when acceptance/approval is part of the obligation |
| `claim_boundary` | Exact claim supported when this obligation passes |

V1 predicates return a typed target set plus relationship witnesses, diagnostics, and a completeness flag. Cardinality counts distinct target identities after filtering, not path count. Boolean conditions are separate typed filters; an unresolved Boolean cannot become false silently.

Conceptual Phase-10 rule:

> For every applicable verification case in the approved evaluation scope, require at least one distinct execution record linked through the declared native/domain relations, with a passing result, an authorized acceptance decision, and an exact matching declared execution scope.

Existence, passing execution, acceptance, and matching scope are separate conditions. A failing execution may be validly accepted as an observation; it still does not satisfy a rule requiring a passing execution.

### Status semantics

- Bind each status condition to its specific vocabulary and target property.
- V1 uses explicit allowed-value membership; reject unknown values during contract validation.
- No global ordering. Ordered comparisons may be enabled later only for vocabularies with a reviewed partial/total order and explicit incomparable-value behavior.
- Do not hard-code example literals such as `approved` into a vocabulary that does not contain them.

### Contract validation

Reject duplicate IDs, unknown predicates, type mismatches, invalid bounds, unknown status literals, unresolved policy references, unsupported applicability forms, and invalid dependency structures before normative evaluation.

Generic operators may be code. Phase-specific populations, thresholds, and obligations remain model data. Predicate implementations must not hide phase rules or contain branches on phase numbers.

## 8. Result fields, validity rules, and failure behavior

Do not overload one `status` field. Assessment coverage, evaluation execution, conformance, and readiness answer different questions.

### Fields and permitted values

| Field | Values | Meaning |
|---|---|---|
| `assessment_coverage` | `ASSESSED`, `UNASSESSED` | At an individual obligation/phase-contract unit, whether evaluation was attempted; it does not mean the attempt succeeded |
| `evaluation_state` | `COMPLETE`, `INDETERMINATE`, `ERROR`, or `null` | Whether the attempt completed, lacked necessary information, or failed; null only when no attempt occurred |
| `conformance_verdict` | `PASS`, `FAIL`, `NOT_APPLICABLE`, or `null` | A normative verdict only for a complete evaluation; otherwise null |
| `readiness` | `READY`, `BLOCKED` | Whether prerequisites and required checks for the explicitly identified readiness target are met |
| `readiness_target` | Identified task entry, scoped phase exit, or exact PR merge gate | The specific decision to which readiness applies; never an unspecified global flag |
| `reason_codes` | Defined machine-readable reasons plus diagnostic references | Explain absence of assessment, incomplete evaluation, violation, and blocking |

`null` is an explicit JSON value, not a string, hidden default, PASS, or NOT_APPLICABLE. A contract-discovery response does not need these evaluation fields; it is not an evaluation result.

### Individual-unit state combinations

| Situation | Assessment coverage | Evaluation state | Conformance verdict |
|---|---|---|---|
| Attempt completed; required condition holds | ASSESSED | COMPLETE | PASS |
| Attempt completed; required condition violated | ASSESSED | COMPLETE | FAIL |
| Applicability resolved as false or explicit permitted-empty disposition holds | ASSESSED | COMPLETE | NOT_APPLICABLE |
| Attempt cannot establish necessary data, representation, or applicability | ASSESSED | INDETERMINATE | null |
| Attempt encounters an invalid contract, binding/integrity mismatch, or evaluator failure | ASSESSED | ERROR | null |
| No executable contract exists, the unit is not selected, or evaluation was not attempted | UNASSESSED | null | null |

An invalid candidate contract that was submitted for validation is an attempted evaluation and yields `ERROR`; it is not disguised as “no contract.” Reasons distinguish `CONTRACT_UNAVAILABLE`, `OUTSIDE_REQUESTED_SCOPE`, `NOT_ATTEMPTED`, `APPLICABILITY_UNRESOLVED`, `INPUT_UNAVAILABLE`, `INVALID_CONTRACT`, and `BINDING_MISMATCH`. Final schema spelling and the complete finite reason vocabulary are fixed in Increment A.

### Normative evaluation rules

1. A required relation demonstrably absent in a complete scope produces `FAIL`.
2. A required non-empty population that is empty in a complete, correctly resolved scope produces `FAIL`.
3. Failure to resolve scope is not an empty-population case. An invalid or ambiguous selector is `ERROR`; unavailable required input is `INDETERMINATE`.
4. `NOT_APPLICABLE` requires supported explicit applicability or an explicitly permitted-empty policy, with a retained reason.
5. Unknown applicability, truncated traversal, missing necessary references, or unknown observed status prevents a pass. Invalid status literals in the contract are contract errors.
6. `COMPLETE` means the evaluation completed, not that engineering work passed. `COMPLETE` / `FAIL` is valid.
7. Known individual failures remain visible when another unit is indeterminate, errored, or unassessed. Do not hide them behind a summary label.
8. Invalid field combinations are rejected by result-schema validation before serialization. No client should need to invent interpretation rules.

### Aggregation and unassessed coverage

Return every required assessment unit in the declared claim scope, its individual fields, and explicit assessed/unassessed ID lists and counts. A contract inventory identifies phases with no executable contract; those phases cannot disappear from a method-level coverage report.

For a non-empty aggregate, `assessment_coverage = ASSESSED` only when every required unit in that aggregate was attempted. Otherwise it is `UNASSESSED`; partial assessment is represented by the lists/counts and completed individual results, not hidden by the binary summary. Aggregate `evaluation_state` and `conformance_verdict` are null while required units remain unassessed. Preserve child errors and failures separately.

When all required units were attempted: aggregate evaluation state is `ERROR` if any required child errored, otherwise `INDETERMINATE` if any required child is indeterminate, otherwise `COMPLETE`. Only a complete aggregate receives a verdict: `FAIL` if any required child fails; `NOT_APPLICABLE` if all required children are explicitly not applicable; otherwise `PASS` when every required child passes or is explicitly not applicable.

An empty assessment inventory is `UNASSESSED` / null / null, not a vacuous pass. This differs from a valid obligation whose subject population is empty: that obligation is evaluated under its explicit population policy.

Report non-model obligations as outside the model projection and list them. They never become implicitly passed. A Phase-10 pilot may pass its declared model-contract scope while full phase or method coverage remains unassessed. Broader required unknown or unassessed work blocks the corresponding broader exit/merge readiness target.

### Readiness and next work

- **Task-entry readiness:** READY only when the prerequisites for that identified task are established. Corrective work may be ready to start while the candidate fails conformance.
- **Scoped phase-exit readiness:** READY only when all required obligations for that exit target have complete PASS or explicitly permitted NOT_APPLICABLE outcomes and its blocking prerequisites are satisfied. Required unassessed, indeterminate, error, and failed obligations produce BLOCKED.
- **PR-merge readiness:** produced only by the delivery projection, combining matching engineering conformance with exact-head governance/CI. A model query cannot grant it.

No readiness target is implied. Return its stable identifier, scope, and blocking reasons; if no readiness target was requested, omit the readiness block. An empty required inventory cannot authorize phase exit or merge. For an explicitly non-applicable exit scope, any readiness claim must preserve that limited disposition rather than claim completed engineering work.

V1 blocking prerequisites are acyclic. Iteration/feedback links are a separate relation and may form cycles. Phase numbering alone does not impose a waterfall execution order.

`next_obligation()` returns an organization-neutral actionable gap or prerequisite/input problem. Sorting uses declared priority then stable identifiers. It may recommend resolving an unknown input before attempting engineering work. No write or automatic dispatch occurs inside the query, and work-entry readiness is not phase-exit readiness.

## 9. Reproducibility manifest and provenance

Retain the existing authority tuple; do not replace it with a single self-attested version string.

Each evaluation binds a verified manifest containing:

- Git repository identity and full requested engineering revision;
- SysML project/commit identity, binding validation, import scope, importer identity, and dependency closure;
- ontology repository path and digest;
- selected method identity, contract digest, and schema version;
- actual evaluator build/code digest and locked runtime dependencies;
- governing policy-bundle identity and policy-selection source;
- evaluation scope, increment ID, configuration identity, and all semantic options;
- evidence execution-scope/fingerprint policy versions where used.

Loader-specific provenance is a separate envelope: snapshot payload digest, source-validation handle, transport, load timing, and evaluation timestamp. It must identify the same semantic source binding, but it is not part of the canonical semantic evaluation key. This allows API and snapshot loading to produce identical conformance payloads while retaining different transport evidence.

Compute a canonical evaluation key from the verified semantic inputs. The requested Git SHA is not proof that deployed code matches it. Startup/gate orchestration verifies the loaded artifacts against the expected manifest and refuses mismatch.

Canonicalization specifies encoding, deterministic ordering, numeric handling, and distinction between ordered SysML collections and unordered sets. Sort only sets; preserve meaningful sequence order. Exclude timestamps, request IDs, timing measurements, and presentation-only fields from the conformance payload digest.

The reproducibility requirement is:

> The same verified semantic inputs, evaluator build, scope, configuration, and options yield the same canonical conformance payload.

The same baseline with a different scope or method is a different evaluation. An updated evaluator yields a new result identity even if the verdict is unchanged.

Responses include subject/obligation IDs, expected and actual values, supporting relationship witnesses, missing relations within declared scope, claim boundaries, and the manifest identity. A timestamp describes when the result was obtained; it never establishes semantic freshness.

## 10. Evidence, acceptance, and V1 validity limits

### Evidence structure

A model record references an immutable execution observation containing:

- stable evidence/execution identifiers;
- subject identifiers and tested subject-state identity;
- tested source/model revision and realized implementation artifact digests;
- test definition/version and acceptance-criterion identity;
- scenario, input dataset, environment, toolchain, and configuration identities;
- execution result using a separate outcome vocabulary;
- artifact URI, content digest, and retained ingestion/provenance record;
- acceptance-decision reference, where required.

Large logs, videos, datasets, and HIL/SIL payloads remain in retained evidence storage. A URI alone is not immutable identity. Verify content integrity during ingestion and retain its validation record. Do not fetch mutable URLs during deterministic evaluation.

Current artifact availability is an operational retention/availability projection. An unavailable remote store must not silently change a historical model verdict, and a historical model verdict must not be advertised as proof that the artifact is downloadable now.

### Acceptance is distinct from ingestion

An acceptance attestation identifies:

- decision ID, decision outcome, and exact evidence digest;
- accepting actor or approved automated authority;
- authorization policy and qualification/independence constraints where required;
- tested subject and configuration scope;
- attributable review/decision provenance;
- explicit supersession or rejection relations when applicable.

The ingestion pipeline may record an observation. It may not assign acceptance merely because ingestion succeeded. The evaluator checks an already attributable, policy-authorized attestation; an editable `accepted` attribute alone is insufficient.

Bind the authorization policy snapshot into the evaluation inputs. New revocations or superseding decisions produce a new evaluated baseline. Live reviewer permissions are operational state, not a hidden historical input. Conflicting effective decisions produce an unresolved result; do not choose by timestamp alone.

### V1: exact declared execution scope, no automatic carry-forward

V1 checks equality against an explicit reviewed execution-scope manifest: tested subject state, realization, test definition, criteria, configuration, inputs, and environment. Required missing fields produce `INDETERMINATE`; a known incompatible scope produces `FAIL` for an obligation requiring a match.

Define a conservative source/artifact boundary for the pilot. If its dependency boundary cannot be established, require new evidence or an explicit scoped human assessment; do not infer safe reuse from unchanged names or one node hash.

Avoid circular baseline binding. Evidence committed after execution refers to the earlier tested revision and immutable execution scope; it is not required to contain the SHA of the commit that later records its own acceptance. Evidence records and attestations are not inputs to the tested-subject digest. The later evaluation baseline proves which execution scope is currently selected.

A direct-subject fingerprint may be displayed diagnostically, but it cannot by itself satisfy a general “current/valid evidence” predicate. Automatic cross-baseline reuse based on semantic dependency analysis is V2.

Use precise predicate names and claim boundaries. Distinguish record existence, execution outcome, authorized acceptance, and execution-scope match rather than introducing an undefined catch-all `has_valid_evidence`.

## 11. Governing-method selection and self-change protection

Co-versioning method and product content does not authorize the candidate content to choose its own acceptance rules.

For ordinary product/engineering increments:

1. Select the governing method, ontology interpretation, evaluator, and authorization policy from an approved policy bundle outside the candidate's control.
2. Require the resolved candidate baseline to include the selected compatible method contract.
3. Detect changes to the policy-bearing contract/dependency closure, even when the file path is unchanged.
4. Refuse to use candidate modifications as the acceptance basis without an explicit method-migration decision.

The first method-conformance deployment uses independent human review as its bootstrap authority. Method evolution is a separate reviewed change with old/new contract comparison, affected-obligation analysis, regression evidence, compatibility decision, and an activation boundary.

Where technically possible, run the old approved policy against the candidate while reporting the proposed policy separately. If incompatible, report a migration blocker instead of silently substituting the new evaluator. Approved activation creates a new policy-bundle identity.

This is policy selection and change control, not a second process graph. Separate implementation changes from method/process changes in review. No gate output itself grants merge authorization.

## 12. Agent working loop, contract discovery, and candidate production

The modeled method contract defines obligations. The API exposes that contract and a bound engineering revision; it does not decide what the method ought to require.

### Read the approved method before the candidate is complete

`phase_contract(P9)` means “show the selected approved method’s Phase-9 contract,” not “assess this candidate.” The actual request supplies a method/policy identity, or the service resolves the configured approved selection and returns its full immutable identity. Never silently choose a candidate-modified method.

This read succeeds when the approved contract is available even if the candidate does not exist, fails validation, or lacks Phase-9 scope and subjects. The read returns:

- governing method/policy identity and phase identity;
- obligation identifiers, expected types, predicates, filters, cardinalities, and population policies;
- applicability expressions and their required inputs;
- required/optional disposition, evaluation source, attestation requirements, and claim boundaries;
- whether an executable contract is available for that phase.

It does not return a conformance verdict. Candidate-independent discovery has its own method-only provenance and does not require or fabricate a candidate Git/API binding.

Optional candidate context may resolve applicability as applicable, not applicable, or unresolved. Without sufficient context, return the obligations unchanged with unresolved applicability and the missing inputs. Do not remove obligations because an incomplete candidate cannot yet satisfy their selectors. If no executable phase contract exists, say so and return pointers to identified approved guidance where available; do not derive executable rules from prose.

Use `phase_contract(...)` as the single V1 contract-discovery endpoint. It replaces the earlier proposed `phase_obligations(...)`; no duplicate public endpoint is needed.

### Exact V1 candidate-production path

```text
local Git commit or exact PR-head commit
        |
        v
SysML validation and pinned semantic export
        |
        v
isolated candidate API import
        |
        v
semantic validation and exact Git/API/ontology binding
        |
        +----------------------+
        |                      |
        v                      v
API-backed evaluation     optional bound snapshot
                               |
                               v
                         same evaluator
```

Rules:

1. V1 evaluates committed revisions, not dirty working trees. Load/export from an isolated checkout of the requested full commit. Uncommitted edits must not leak into that export; the caller must be told that only committed content is represented. A request to assess the dirty working tree is refused as unsupported in V1.
2. Resolve pinned dependencies and record serializer/importer identity. Syntax/export success is necessary but not semantic validation or engineering acceptance.
3. Import into an isolated candidate revision or staging instance. Each evaluation binds one project/commit containing the resolved method and engineering content. Reusing infrastructure is allowed, but concurrent candidates cannot overwrite one another’s identities.
4. Read back and semantically validate the graph before issuing its candidate binding. Candidate graph production is implemented and proven in Increment B; API-backed evaluation follows in C; snapshot acceleration follows in D.
5. A validated candidate is queryable before merge. It remains a candidate, and importing it must not change the published accepted-baseline pointer, deploy it publicly, or imply review approval.
6. A V1 snapshot is derived from that validated candidate API revision and retains its source binding. Direct export-only snapshots without a validated API binding are outside V1; they require a separate authority/backend decision.
7. A snapshot accelerates loading of an already validated graph. New committed edits require producing/validating a corresponding candidate graph; reusing an old snapshot does not update the model.
8. When candidate validation fails, return validation diagnostics and keep approved-method discovery available. Never issue a conformance pass from a partially imported graph.
9. Governing policy still comes from Section 11. Candidate queryability does not authorize the candidate to change its acceptance rules.

### Engineering loop

```text
agent reads phase_contract(selected approved method, phase)
        |
        v
agent edits model/evidence and creates a local candidate commit
        |
        v
validated candidate API graph (optional bound snapshot)
        |
        v
canonical deterministic evaluation
        |
        +-- increment_status(...)
        +-- method_gaps(...)
        +-- next_obligation(...)
        |
        v
agent addresses reported gaps and repeats
```

Committing a candidate is not publication or merge. This document does not authorize the assistant to commit or push during planning. The implementation workflow follows the user’s applicable authorization and review rules.

### Canonical evaluation and projection consistency

`increment_status(...)`, `method_gaps(...)`, and `next_obligation(...)` are projections of the same canonical evaluation for the same verified manifest, scope, method, and configuration. Return the same evaluation identity across these projections; they must not recompute incompatible notions of completeness.

`phase_contract(...)` projects the corresponding method inputs independently of candidate evaluation. When used alongside an evaluation, its method/policy identity must match the evaluation’s governing identity. Distinguish its method-only provenance from the full candidate evaluation manifest.

The evaluator uses the separate result fields and nullability rules from Section 8. The agent may explain findings, but it cannot infer unsupported completion or promote task-entry readiness into phase-exit or merge readiness.

## 13. Query and operational projections

### Initial model surface

Extend the existing read-only service with:

- `phase_contract(...)`: candidate-independent read of the selected approved phase contract, including applicability expressions and method/policy provenance; optional applicability resolution never hides unresolved obligations;
- `increment_status(...)`: scoped model-contract conformance;
- `method_gaps(...)`: explicit violations, unresolved inputs, and out-of-scope obligations;
- `next_obligation(...)`: deterministic next actionable gap without agent assignment.

A `method_status(...)` summary may be added once aggregation across actual implemented contracts is supported. The engine is phase-neutral across P0–P12 from V1, but a phase without a reviewed executable contract has `assessment_coverage = UNASSESSED`, null evaluation state/verdict, and an explicit reason. Broader summaries list mixed assessed/unassessed coverage under Section 8; they never infer method completion.

MCP remains a thin adapter over the agent-independent service. Evaluation results carry full evaluation scope and provenance; contract-discovery responses carry approved method/policy identity and phase scope without requiring candidate provenance.

### Delivery projection

`pr_gate_status(...)` composes a matching model result with live exact-head review, CI, method-change authorization, and applicable delivery policy. It identifies PR head, relevant base/merge-candidate identity, policy revision, observation time, and the exact CI/review records used.

Re-read the relevant head/base state after gathering evidence; if it moved, return `readiness = BLOCKED` for the exact PR-merge target with a stale-input reason and no successful operational verdict. Unknown, unassessed, or unsupported required delivery obligations also block. The final platform merge protection remains authoritative for the merge operation. Observational readiness does not promise future readiness.

The delivery adapter may share the read-only MCP transport, but it has a separate runtime/data-source boundary. The pure evaluator never requires GitHub connectivity.

Pinned repository and attestation checks require explicit adapters and schemas. Until supported, report them as unevaluated outside the model projection; full method/merge readiness cannot ignore required unsupported obligations.

### V2 model projections

`capability_status(baseline, capability, configuration)` and `release_readiness(baseline, configuration)` query the resolved current baseline directly. They do not sum historical increment completion flags.

Before implementation, specify active subject populations, explicit supersession/retirement, configuration applicability, evidence validity, numerator/denominator definitions, and historical membership coverage/cutoff. Return unresolved counts and denominator provenance with every metric. Release output is modeled engineering readiness, not regulatory or human release authorization.

## 14. Validated snapshots and operational loading

Snapshots are rebuildable derived caches, never an independent engineering authority.

A snapshot contains immutable graph data, dependency/import scope, schema information, the validated source binding, object/reference completeness checks, and a payload digest. Validate both byte integrity and origin binding; a hash does not prove that the producer used the right baseline.

Use the controlled validated importer/build artifact chain as the trust origin. Bind bundle digests to exact-run retained validation records and verify that binding before evaluation. A bundle cannot authorize itself by carrying its own claimed hash. Reuse existing protected build/review controls; additional signing or security changes require separate approval.

Reject wrong authority tuples, corrupt payloads, incomplete page collections, unsupported schemas, and unresolved required references. On cache mismatch, either rebuild/reload the same immutable source or return a clear blocker; never fall back to “latest.”

API-backed and snapshot-backed runs must produce identical canonical conformance payloads for the same evaluation inputs. Snapshot transport metadata may differ outside that payload.

Measure full-baseline loading, snapshot loading, evaluation time, and peak memory on the actual intended CI runner. Set the gate latency/resource budget from those measurements before making the check required. Do not invent a performance claim or repeat expensive ingestion for an unchanged validated source identity.

## 15. Implementation sequence and review gates

This is an architecture-to-implementation plan, not a claim that new classes or files already exist. Proposed paths below are creation targets. Exact SysML forms and pilot subject IDs are selected from real artifacts during the first bounded increment, not invented here.

### Finite delivery boundary and acceptance ownership

- **V1 Core = Increments A–D:** phase-neutral evaluator, independent approved-contract discovery, real Phase-10 proof, non-Phase-10 genericity test, committed-candidate/API/snapshot workflow, and the operational delivery projection proven in advisory mode.
- **V1 Rollout = separately accepted Increment-E additions:** more real phase contracts using the existing schema and evaluator. Broad P0–P12 coverage is an architectural goal, not a prerequisite for the first usable release.
- **V2 = genuinely new semantics:** impact-aware reuse, richer applicability, or other changes requiring new semantic capability rather than another ordinary phase contract.

Section 16 assigns every acceptance case a single owning implementation increment and first required exit gate. Ownership identifies where the complete acceptance behavior must be proven, not which contributor owns the underlying artifact.

- A specifies expected outcomes and owners; it does not need future executable tests to pass.
- B gates on B-owned cases and existing relevant regressions.
- C gates on C-owned cases, B-owned cases, and existing relevant regressions; D-owned cases are not C exit requirements.
- D gates on D-owned cases and all earlier acceptance/regression cases. Passing these plus retained actual-run evidence completes V1 Core.
- E additions gate on their own new cases and all applicable Core/earlier-rollout regressions. No E work is required to declare V1 Core delivered.

A case may have supporting lower-level tests earlier, but its complete acceptance is required only at its assigned gate. Future capabilities must not be pulled backward merely to satisfy an overbroad “all V1 tests” statement.

### Increment A — Contract and governance foundations

**Outcome:** a reviewed phase-neutral executable-contract specification, proven first against one selected Phase-10 pilot with no unresolved meaning.

**Existing files to inspect/update when implementing:**

- `textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_process.sysml`
- `approach/framework/ontology/de4sdv-basic-ontology.yaml`
- `approach/framework/ontology/README.md`
- `methodologies/sysmod-sysmlv2/increment-workflow.md`
- `methodologies/sysmod-sysmlv2/process-mapping.md`
- `docs/architecture-decisions/0010-bind-semantic-impact-queries-to-api-revisions.md`
- `docs/architecture-decisions/0012-expose-revision-bound-semantic-reads-through-mcp.md`

**Proposed creation targets:**

- A new numbered `deterministic-method-conformance` ADR under `docs/architecture-decisions/` — allocate its exact filename only after checking the current reviewed repository and existing ADR work. The earlier `0017` path was an unreserved planning placeholder, not an assigned identifier.
- `docs/architecture/method-conformance-contract.md` — maintained schema/result contract, not another normative copy of every obligation.

**Tasks:**

1. Define the phase-neutral contract/evaluator boundary for P0–P12, then select one evidence-bearing AEBS Phase-10 increment, one declared configuration, and its actual subject IDs as the first validation slice. Name the engineering decision and reviewer. Do not assume the earlier example increment is suitable.
2. Extract its real exit criteria and classify structural checks, execution checks, acceptance checks, delivery checks, and remaining human judgments.
3. Specify the typed schema, per-unit and aggregate result fields/nullability, readiness targets, subject/target semantics, execution-scope boundary, and approved method-selection policy. Fix candidate-independent `phase_contract(...)` behavior and the committed-candidate production contract.
4. Record pilot required obligations versus unautomated obligations, resolve every acceptance literal against the actual ontology vocabulary, and confirm each acceptance case’s owning increment and first required exit in Section 16.
5. Review the scope and contract independently before model or evaluator implementation.

**Exit gate:** reviewer can determine the expected outcome and assigned implementation gate for every acceptance case in Section 16 without informal phase knowledge. Required/null field combinations, aggregate coverage rules, readiness targets, and candidate production/discovery are unambiguous. Unknown pilot identity, acceptance authority, or evidence boundary blocks progression. This is specification acceptance, not a requirement that B–D executable tests already pass.

### Increment B — Normative graph and real API round trip

**Outcome:** real queryable contract and scope objects, not merely parseable SysML text.

**Existing targets:** method-process file and ontology above; `de4sdv/sysml_api/identity.py`; `de4sdv/semantic/api_binding.py`; `de4sdv/semantic/validation.py`; `de4sdv/semantic/traversal.py`; `tests/test_native_semantic_traversal.py`; `tests/test_sysml_full_ingestion.py`; `scripts/export_sysml_api_baseline.py`; `scripts/import_sysml_api_baseline.py`; `.github/workflows/privileged-full-model-api-ingestion.yml`.

**Proposed targets:** `tests/test_method_contract_binding.py`; extend the selected pilot's existing model files after selection rather than creating a duplicate pilot model. Add a separate method-contract `.sysml` file only if the reviewed schema justifies it.

**Tasks:**

1. Write synthetic tests for missing/duplicate IDs, method-subject leakage, explicit contribution versus evaluation membership, typed target binding, and status vocabulary errors.
2. Run the tests and confirm the intended failures before implementing the binder extensions.
3. Add the minimal native/domain declarations and explicit pilot memberships. Classify every new kernel declaration through the existing ontology/kernel mapping or justified exclusion; do not bypass the synchronization check.
4. Implement only the tested binding/traversal extensions and rerun tests.
5. Implement/prove the exact committed-candidate path in Section 12: isolated checkout, licensed validation/export, isolated candidate API import, semantic read-back validation, and binding emission. Do not require merge before this path can run. Add tests for dirty-tree exclusion/refusal and preservation of the published accepted-baseline selection.
6. Read back the actual selector, obligation, subject, relationship, and evidence/attestation references at the bound API revision. Reimport the same source for a bounded identity-correspondence test; compare persistent IDs and semantic relationships, not raw UUID equality.

**Exit gate:** B-owned Section 16 cases and existing relevant regressions pass. Retained exact-revision candidate API read-back proves the intended graph shape, committed-source isolation, and unchanged published baseline selection. Simplified fixture success does not substitute for real serializer behavior. Do not build the evaluator before this passes; evaluator and snapshot acceptance remain C and D work.

### Increment C — Bounded deterministic evaluator and read-only queries

**Outcome:** a phase-neutral deterministic evaluator, proven by a Phase-10 pilot that cannot pass on missing context or unsupported semantics.

**Existing targets:** `de4sdv/semantic/query.py`; `de4sdv/semantic/runtime.py`; `de4sdv/semantic/kernel_contract.py`; `de4sdv/semantic/mcp_server.py`; `de4sdv/sysml_api/revisions.py`; `tests/test_semantic_mcp.py`.

**Proposed creation targets:**

- `de4sdv/semantic/method_contract.py` — typed decoded contract and validation.
- `de4sdv/semantic/method_evaluator.py` — generic evaluation and canonical result assembly.
- `tests/test_method_conformance.py` — synthetic acceptance matrix and determinism cases.

**Tasks:**

1. Implement contract validation through failing tests, minimal code, and verified passes.
2. Implement manifest verification, legal assessment/evaluation/verdict combinations, reason codes, aggregate coverage, and target-specific readiness using the same test-first loop. Reject illegal combinations before serialization.
3. Add per-subject target filtering/deduplication/cardinality, applicability, aggregation, and deterministic gap ordering with independent tests.
4. Add separate tested evidence-existence, execution-result, attestation, and exact-scope checks. Do not relabel structural `verification_coverage` as executed verification.
5. Add candidate-independent `phase_contract(...)`, the scoped evaluation projections, and thin MCP handlers. Test contract reads with no candidate, missing scope, and invalid candidate content; unresolved applicability must remain visible. Verify method identity and null/absent evaluation fields in discovery responses.
6. Evaluate the real unmerged Phase-10 candidate produced by B and compare against an independently reviewed expected disposition. Repeat with reordered API enumeration and fixed semantic inputs; exercise all result projections against the same evaluation identity. No snapshot implementation is required at this gate.
7. Prove that evaluator code contains no phase-number branches and that at least one synthetic non-Phase-10 contract uses the same generic operators successfully.

**Exit gate:** all C-owned and B-owned Section 16 cases plus existing relevant regressions pass. Actual API-backed unmerged pilot evidence exists; independent approved-method discovery works before candidate completeness; a non-Phase-10 synthetic contract demonstrates phase-neutral execution; and human review agrees with the supported claim level. D-owned snapshot and PR-gate cases are explicitly not required here. No all-method completeness claim.

### Increment D — Snapshot path and delivery integration

**Outcome:** a practical, observable PR-gate input, not an automatic merge mechanism.

**Existing targets:** `de4sdv/sysml_api/repository.py`; `de4sdv/semantic/runtime.py`; `.github/workflows/privileged-full-model-api-ingestion.yml`; `.github/workflows/ci.yml`; `sysmlv2-api/README.md`.

**Proposed creation targets:** `de4sdv/semantic/snapshot.py`; `tests/test_method_snapshot.py`; `de4sdv/semantic/delivery_gate.py`; `tests/test_method_delivery_gate.py`.

**Tasks:**

1. Add snapshot integrity/binding/completeness tests before implementing the loader.
2. Prove API/snapshot canonical-result equivalence and measure startup/evaluation on the intended runner.
3. Add exact-head/base race, stale review/check, policy-change, and unavailable-service tests before implementing delivery composition.
4. Run the check in advisory/shadow mode on real pilot PR revisions. Retain head/base/policy and CI handles; reconcile disagreements with existing review gates.
5. Deliver the tested check in advisory mode with retained exact-head evidence. Making it required is a separate operational activation decision after explicit maintainer authorization; changing branch protection or security settings is outside this plan’s execution authority and is not required to complete V1 Core.

**Exit gate:** all D-owned Section 16 cases, all B/C-owned cases, and existing relevant regressions pass. Retained real-run evidence proves API/snapshot parity, exact-head delivery binding, measured runtime/resource suitability, correct refusal on mismatch, and no hidden live dependency in pure evaluation. The advisory delivery projection is usable. A–D are now complete: V1 Core may be delivered without waiting for additional phase contracts or required-check activation.

### Increment E — V1 Rollout: separately accepted additional phase contracts

**Outcome:** expand method coverage without changing the evaluator architecture.

**Tasks:**

1. Select the next phase contract based on decision value and availability of real model evidence, not phase number.
2. Encode its reviewed obligations using the existing typed schema and ontology predicates.
3. Add acceptance cases and real API read-back for that phase before claiming it assessed.
4. Reuse the same evaluator and query projections; phase-specific Python branches or custom status logic are not allowed.
5. Mark every not-yet-encoded phase explicitly `UNASSESSED` in method-level summaries.
6. End each rollout increment when its explicitly selected contract and acceptance scope pass review. Select further phase contracts as separate increments; do not tie V1 Core completion to coverage of every useful P0–P12 obligation.

**Exit gate per rollout increment:** the named added contract has reviewed obligations, deterministic tests, retained real-model evidence, and passing applicable Core/earlier-rollout regressions. Expanding coverage does not alter the result algebra or authority boundaries. No global “all useful phases covered” gate is introduced.

### V2 — Only after V1 produces useful decisions

Consider impact-aware evidence reuse, richer applicability semantics, cumulative capability/release projections, historical gate attestations, and other capabilities that require genuinely new semantics. Additional ordinary P0–P12 contracts using the existing schema/evaluator belong to V1 rollout, not V2. Each extension needs its own scope, predicates, regression evidence, reviewer, and measurable decision benefit. Do not build them merely because endpoint names appear in a diagram.

## 16. Acceptance matrix

These are required future tests, not reported test results. Use synthetic fixtures; do not copy real model files into test fixtures. The owning increment is the first gate at which the complete case must pass; subsequent increments retain it as a regression. A approves the specification for all cases, not their implementation. B, C, and D use only their assigned/prior cases under Section 15. Each E rollout adds scoped cases without delaying V1 Core.

| ID | Scenario | Required outcome | Owning increment / first required exit |
|---|---|---|---|
| MC-01 | Complete scoped pilot; passing executions, authorized attestations, exact execution-scope matches | `COMPLETE` / `PASS` for the declared pilot only | C |
| MC-02 | One subject has no required evidence in an otherwise complete graph | `COMPLETE` / `FAIL`; identify the subject and missing relationship | C |
| MC-03 | One case has several records; another case has none | Fail the uncovered case; no global-count pass | C |
| MC-04 | Several graph paths reach the same evidence target | Count one distinct target per subject | C |
| MC-05 | Valid scope resolves to no subjects despite non-empty policy | `COMPLETE` / `FAIL` with population diagnostic | C |
| MC-06 | Missing membership, broken selector, ambiguous ID, or wrong target type | Error/indeterminate as specified; never an empty-population pass | C |
| MC-07 | Explicit, supported non-applicability | `NOT_APPLICABLE` with reason, not completed engineering work | C |
| MC-08 | Unknown applicability, missing API page/reference, or truncated traversal | `INDETERMINATE`; no pass | C |
| MC-09 | Unsupported predicate, invalid cardinality, or unknown status literal | Contract `ERROR` before normative evaluation | C |
| MC-10 | Ordinary selector includes a method contract | Scope validation error; shared type references alone remain legal | B |
| MC-11 | Different Git/API/ontology/method/evaluator/policy identity | Refuse the mismatched evaluation | C |
| MC-12 | API enumeration order and timestamps differ, semantic inputs identical | Same canonical conformance payload | C |
| MC-13 | Configuration, evaluation scope, or meaningful ordered collection changes | Different evaluation identity; recompute rather than reuse | C |
| MC-14 | Reimport changes API UUIDs while explicit IDs and meaning remain stable | Preserve identity correspondence without name-based merging | B |
| MC-15 | Accepted evidence records a failed execution | Fail an obligation requiring a passing execution | C |
| MC-16 | Record says accepted but lacks attributable authorized decision | No acceptance pass; missing authority is explicit | C |
| MC-17 | Verification-case text unchanged, implementation/configuration/test/inputs change | No automatic evidence carry-forward; scope mismatch fails | C |
| MC-18 | Execution scope cannot establish required dependency boundary | Indeterminate validity, not inferred freshness | C |
| MC-19 | Evidence is committed after execution | Compare tested-scope identity; no impossible self-containing Git SHA requirement | C |
| MC-20 | Conflicting acceptance/rejection decisions lack valid supersession | Unresolved acceptance; no timestamp-based winner | C |
| MC-21 | Snapshot corrupt, incomplete, wrong-bound, or self-attested without trusted provenance | Reject snapshot; never silently load latest | D |
| MC-22 | Same verified inputs loaded through API and snapshot | Identical canonical conformance payload | D |
| MC-23 | Product candidate weakens obligation, interpretation, evaluator, or policy | Governing-policy mismatch/migration blocker; no self-acceptance | C |
| MC-24 | PR head/base moves while status is gathered | `readiness = BLOCKED` for the exact PR-merge target, with `STALE_INPUT` and a head-moved/base-moved reason; no successful delivery verdict | D |
| MC-25 | Required delivery obligation unsupported; model pilot passes | Model pass stays scoped; full readiness does not pass | D |
| MC-26 | Hindsight claims evidence exists but graph does not | Memory does not change the result | C |
| MC-27 | Blocking prerequisite cycle versus legitimate feedback loop | Reject unsupported blocking cycle; allow separate feedback relation | C |
| MC-28 | Remote artifact later unavailable; pinned record unchanged | Historical model verdict reproducible; availability reported separately | D |
| MC-29 | All selected obligations explicitly not applicable versus no executable phase contract | First case: ASSESSED / COMPLETE / NOT_APPLICABLE; second: UNASSESSED / null / null; neither claims completed engineering work | C |
| MC-30 | Evaluator API/snapshot comparison and independent manual pilot review disagree | Block readiness and investigate; neither timeout nor partial result counts as acceptance | D |
| MC-31 | Unmerged candidate revision is validated/imported with complete scope | Conformance may be evaluated against that exact candidate revision; merge is not required | C |
| MC-32 | Same verified candidate evaluated through API and validated local/CI snapshot | Same canonical conformance payload | D |
| MC-33 | A non-Phase-10 contract uses the same generic operators | Evaluate without phase-specific code path; phase number does not alter semantics | C |
| MC-34 | Phase has no reviewed executable contract yet | UNASSESSED / null / null with CONTRACT_UNAVAILABLE reason; required broader exit readiness remains BLOCKED | C |
| MC-35 | Approved phase contract exists; candidate is absent, invalid, or missing scope | phase_contract returns method identity, obligations, and unresolved applicability inputs without a conformance verdict; no obligations silently disappear | C |
| MC-36 | Caller has uncommitted edits or requests dirty-working-tree evaluation | Export of a selected commit excludes uncommitted content and declares its commit identity; an explicit dirty-tree evaluation request is refused | B |
| MC-37 | Candidate is imported and validated before merge, including concurrent candidates | Candidate bindings remain isolated; published accepted-baseline selection is unchanged; validation does not imply approval | B |
| MC-38 | Result fields include illegal combinations or missing required reasons/target | Reject serialization; no verdict for INDETERMINATE/ERROR/UNASSESSED, null evaluation fields only as specified, and readiness always names its target | C |
| MC-39 | Candidate fails a required exit condition while a corrective task has satisfied entry prerequisites | Phase-exit readiness BLOCKED and corrective-task entry readiness READY may coexist under distinct explicit targets | C |
| MC-40 | Broader scope mixes attempted and unassessed required units, including known child failures | Preserve all child results and coverage lists/counts; aggregate coverage UNASSESSED with null evaluation/verdict, and broader exit readiness BLOCKED | C |

## 17. Verification commands and evidence delivery

During implementation, use the repository's established environment and dependencies. `requirements-mcp.txt` is the inspected MCP dependency manifest; no new package requirement is introduced here.

Existing regression targets:

```bash
python -m pytest tests/test_sysml_api_semantic.py tests/test_native_semantic_traversal.py tests/test_semantic_mcp.py tests/test_sysml_full_ingestion.py
python scripts/check_repo.py
python scripts/smoke_test.py
python scripts/validate_sysml.py
git diff --check
```

New targets, runnable only after the proposed files exist:

```bash
python -m pytest tests/test_method_contract_binding.py tests/test_method_conformance.py
python -m pytest tests/test_method_snapshot.py tests/test_method_delivery_gate.py
```

Run relevant tests first and the complete repository pytest suite before final readiness. Record actual results; do not assume counts or substitute expected output for execution. If local licensed SysML validation is unavailable, use the existing privileged validation path and retain exact-head output. Also exercise the privileged full-model API ingestion path and real MCP calls; syntax validity alone does not prove the graph contract or phase completeness.

For every implementation increment retain: tested Git head, policy/evaluator identity, selected scope/configuration, test results, licensed model-validation evidence where applicable, API read-back/manifest identity, and unresolved claims. After head/base changes, rebind and rerun required evidence. Keep changes on review branches; no direct main pushes, unrequested commits/pushes, or merges.

## 18. Risks, tradeoffs, and remaining decisions

| Topic | Default decision | Tradeoff / what must be resolved |
|---|---|---|
| One engineering baseline | Keep method and engineering content resolved together | Co-versioning is simple; method-selection guardrails remain mandatory |
| Contract language | Small typed operators and named predicates | Explicit limits; unsupported forms block rather than trigger a general interpreter |
| V1 evidence scope | Conservative exact execution-scope match | More re-execution than impact-aware reuse, but narrower defensible claims |
| Scope completeness | Explicit reviewed scope; no inferred exhaustive impact claim | Human scoping remains necessary until impact closure is proven |
| Evidence authority | Attributable policy-authorized attestation | Pilot must identify the real acceptance source; an invented reviewer field is insufficient |
| Snapshot trust | Validated import/build provenance plus content integrity | Actual artifact-origin verification must be proven on the deployment path |
| Pilot selection | One real evidence-bearing Phase-10 slice validates the phase-neutral engine | Exact increment, configuration, and reviewer are acceptance prerequisites; Phase 10 is not the scope boundary |
| Gate adoption | Advisory until evidence and maintainer authorization | Prevents a premature mandatory check from blocking contributors or creating false confidence |

No fixed delivery estimate is asserted before the graph round trip and evidence-authority path are proven. These, not the number of evaluator functions, are the principal uncertainties.

## 19. Source trail and final decision

Inputs reviewed:

- `/home/mrk/.hermes/attachments/Graph Architecture-2.md`
- `/home/mrk/.hermes/attachments/DE4SDV_Deterministic_Method_Conformance_Plan_Latest.md`
- `/home/mrk/.hermes/attachments/DE4SDV_Deterministic_Method_Conformance_Plan_Revised.md` — direct basis for this final consolidation, together with the user’s agreed five-point feedback.
- `AGENTS.md`
- `approach/framework/README.md` and `approach/process-set/README.md`
- `methodologies/sysmod-sysmlv2/increment-workflow.md`, `process-mapping.md`, and `de4sdv-tailoring.md`
- `textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_process.sysml`
- `approach/framework/ontology/README.md`
- `docs/architecture-decisions/0010-bind-semantic-impact-queries-to-api-revisions.md` and `0012-expose-revision-bound-semantic-reads-through-mcp.md` — both marked Proposed in the inspected checkout; cited as existing architectural records, not claimed ratification.
- `de4sdv/semantic/query.py`, `de4sdv/semantic/runtime.py`, `de4sdv/sysml_api/revisions.py`, and `de4sdv/sysml_api/identity.py`
- Existing test and workflow paths listed above were located; their future conformance acceptance is not asserted.

**Final planning decision:** preserve the core architecture and proceed to Increment A when implementation is requested. Deliver finite V1 Core through A–D: a phase-neutral evaluator, independent approved-contract discovery, committed unmerged-candidate production, real Phase-10 and non-Phase-10 genericity proofs, validated snapshots, and advisory delivery composition. Apply acceptance ownership so no gate depends on later work. Keep result fields and readiness targets explicit. Add further real phase contracts as separately accepted V1 Rollout increments; reserve V2 for new semantics. Finalizing this document is not permission to implement, publish, change security controls, or merge.

**Success is not a larger graph or a greener dashboard. Success is a reviewable answer to one engineering-completeness question, backed by the exact modeled relationships, tested execution scope, authorized decisions, and reproducible inputs that justify it.**
