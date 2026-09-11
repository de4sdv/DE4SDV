# Lane B — A-obligation → model identity → serialized/API witness matrix

Derived from the merged A specification (`docs/method-conformance/pilot-obligations.yaml`,
`pilot-scope.md`) and the implemented model slice at branch
`feat/lane-b-method-contract`. This document is a **derived view**, not a
second semantic authority: `pilot-obligations.yaml` remains the structured
contract source; the model is the semantic authority.

Serialized/API witness column states the expected witness shape at the bound
candidate revision — **verified only by the privileged run's
`verify_pilot_readback.py` output**, not by this table's existence.

| A obligation | Model identity (stable explicit id) | Model element (kind / package) | Serialized/API witness (expected) |
|---|---|---|---|
| PC-009D-SCOPE-POPULATION | `PSC-009D` | `part aebsOverridePilotScope : AebsOverridePilotScopeBase` in `DE4SDV_AEBSOverrideVerification` | PartUsage with `declaredShortName=PSC-009D`; `attribute incrementId = "INC-AEBS-009D"`; six scope usages resolvable by short name |
| PC-009D-VC-BINDING | `VC-AEBS-009D-01…06` | six `verification` usages specializing `<'VC-AEBS-009D-DE'>ConsciousOverrideVerification` | VerificationCaseUsage per short name; `Generalization` edge to the shared definition; definition distinct (its own short name) |
| PC-009D-SUBJECT-MEMBERSHIP | per-usage `verifiedBench` | `subject verifiedBench :> override<Scenario>Bench` on each usage | `SubjectMembership` owned by each usage; memberElement → `OverrideMatrixBench` specialization part usage |
| PC-009D-OBJECTIVE-CONTRACTS | `EC-009D-01…03` | `requirement evidenceContract…` usages verified by `evidenceObjective` | Inherited witness path: usage → (specialization) → definition → `ObjectiveMembership` → objective `RequirementUsage` → `RequirementVerificationMembership` ×3 → requirement usages |
| PC-009D-USAGE-METHOD-METADATA | on each `VC-AEBS-009D-0N` usage | `@VerificationMethod{ kind = (test, analyze); }` owned by each usage | Metadata annotation feature owned by the usage; owner = usage UUID |
| PC-009D-DEFINITION-METHOD-METADATA | on `VC-AEBS-009D-DE` definition | `@VerificationMethod{kind=test}` on `collectData`; `kind=analyze` on `processData`, `evaluateData` | Metadata annotations owned by the three action usages of the definition |
| PC-009D-PROFILE-POPULATION | `INC-AEBS-009D` (external) | ` TestedScopeDeclaration` model vocabulary + retained `campaign-manifest.json` (external, digest-pinned) | External identity: manifest `profiles` keys = the six `OverrideScenario` identities; NOT API UUIDs |
| PC-009D-EXECUTION-RECORD | run ids e.g. `20260727T222325Z-d6cda4ace4b3a9ca` | `RetainedExecutionRecordReference` model vocabulary; retained records under `implementation/…/evidence/009d/` (external) | External identity: manifest per-profile `run_id` + `sha256` of `scenario-evidence.json`; bytes stay external |
| PC-009D-EXECUTION-OUTCOME | per-record `evaluation.passed` / `evaluation.disposition` | retained `scenario-evidence.json` (external) | External identity: pinned `OverrideDisposition` literal per profile; digests via manifest |
| PC-009D-SCOPE-EQUALITY | provenance fingerprint fields | `TestedScopeDeclaration` model vocabulary; retained `provenance` objects (external) | External identity comparison: `repository_head`, `override_matrix_sha256`, `override_execution_manifest_sha256`, `execution_manifest_sha256`, `runtime_lock_sha256` (+inherited_009a), `image_digest`, `map_digest`, `host_arch` |
| PC-009D-ACCEPTANCE-AUTHORITY | policy `de4sdv.acceptance.maintainer-decision.v1` (Proposed) | `AcceptanceAttestationReference` model vocabulary; decision registry `docs/acceptance-decisions/` (currently absent) | External identity: registry scan state recorded; missing registry ≠ known-empty; no acceptance decision exists (explicit gap, not fabricated) |

## Model-side vocabulary added (kernel, all ontology-classified)

`MethodContractObligation`, `EvaluationSourceKind`, `MethodEvaluationScope`,
`EvaluationScopeMembership`, `TestedScopeDeclaration`,
`RetainedExecutionRecordReference`, `AcceptanceAttestationReference` — item
definitions in `de4sdv_method_conformance.sysml`
(`DE4SDV_MethodConformance` package). These are the typed carriers the
contract schema materializes into; the INC-AEBS-009D scope usage
(`PSC-009D`) instantiates the scope in the pilot package.

## v1.1 native/library grounding (read-back proof requirements)

Per the v1.1 plan invariant (an `@type` check alone is not sufficient
semantic evidence), the privileged read-back additionally proves:

| Identity | API metaclass | Standard-library grounding | DE4SDV application definition | Explicit vs implied |
|---|---|---|---|---|
| `VC-AEBS-009D-DE` | `VerificationCaseDefinition` | toolchain-materialized implied `Subclassification` to `VerificationCases::VerificationCase` (`isImplied: true`, target `@uri` into the pinned `Systems Library/VerificationCases.sysml`; target id equals the anchor the licensed exporter resolved BY NAME) | the DE4SDV verification definition itself (`ConsciousOverrideVerification`) | grounding is SysML-implied (`checkVerificationCaseDefinitionSpecialization`); the licensed serializer materializes it via `SerializationOptions include_implied`, so the closure carries the relationship with implied provenance — no redundant authorship required |
| `VC-AEBS-009D-01…06` | `VerificationCaseUsage` | toolchain-materialized implied `Subsetting` to `VerificationCases::verificationCases` (same implied markers, target `@uri`, anchor id cross-check) | explicit `FeatureTyping` witness to `VC-AEBS-009D-DE` (the serializer's real shape for `verification … : Def`) | definition/usage typing is explicitly authored and serialized; library subsetting is implied and materialized by the toolchain; subject memberships and usage-level `@VerificationMethod` metadata are explicitly authored |
| `EC-009D-01…03` | `RequirementUsage` | ODE4HERA requirements-management vocabulary via the DE4SDV method-context adapter (ADR 0009) | `OverrideEvidenceContract` specializations | `RequirementVerificationMembership` witnesses explicitly authored in the objective |

Grounding evidence chain: the export runs with
`SerializationOptions.minimal().with_options(include_implied=True)` (KerML
10.3 `includesImplied`; `minimal()` alone documents that it EXCLUDES implied
relationships) and records `library_anchors` — the ids of
`VerificationCases::VerificationCase` and `VerificationCases::verificationCases`
resolved by the licensed toolchain by name from the pinned library documents.
The read-back then proves, from the imported closure, that each implied edge
exists with `isImplied`, targets exactly the recorded anchor id, and carries
an inline `@uri` into `VerificationCases.sysml`. A missing edge, missing
anchor, non-implied edge to a library target, or wrong target id fails the
read-back closed.

The privileged evidence is produced by two independent serialization
transactions of the same committed source (candidate-1, candidate-2), each
imported into its own distinct API project/commit; correspondence is
verified by `scripts/verify_reimport_correspondence.py` from PERSISTENT
explicit identities only (`declaredShortName`), plus relationship structure
in persistent-identity space. `declaredName` never establishes identity and
is never a fallback key — names are compared only as attributes after the
persistent identity has been established. Elements without a persistent
identity stay out of the global correspondence key-space; serializer-internal
anonymous witnesses are matched structurally only inside an
already-corresponded witness path. Ambiguous persistent identities — the
same short name on multiple elements within one transaction, legal across
namespaces and used by the pinned upstream libraries (e.g. sysmod's per-view
`soi`/`soiImpl`) — are excluded from global correspondence with recorded
occurrence counts and are never matched arbitrarily; a required pilot
identity that is missing OR ambiguous fails closed. UUIDs are attributed per
identity by transaction
(`uuid_by_transaction`); UUID equality is reported, never required or
assumed. The required Lane B pilot identities
(`VC-AEBS-009D-DE`, `VC-AEBS-009D-01..06`, `EC-009D-01..03`, `PSC-009D`)
must carry a persistent identity in BOTH transactions.

The read-back (`scripts/verify_pilot_readback.py`) proves grounding from the
serializer's ACTUAL relationship representation — discovered by
`de4sdv/semantic/relationships.py` (relationship-object families:
Subclassification/FeatureTyping/Generalization/..., or inlined reference
properties) rather than a hard-coded metaclass — and reports, per identity:

- `definition_grounding`: API metaclass, DE4SDV definition witness, library
  grounding witness (specialization closure to
  `VerificationCases::VerificationCase`), provenance, exact hop witness ids;
- `usage_grounding` (per usage `VC-AEBS-009D-01..06`): API metaclass,
  DE4SDV definition witness, library grounding witness through the usage
  closure, the `VerificationCases::verificationCases` anchor grounding INTO
  the library definition, provenance, exact witness ids, completeness state
  with diagnostics;
- `library_anchors`: the name-resolved anchor ids recorded by the licensed
  exporter (`VerificationCases::VerificationCase`,
  `VerificationCases::verificationCases`), cross-checked against the
  implied edges' targets in the imported closure.

Library-anchor presence alone is not grounding; any missing witness fails
the read-back closed.

## External-boundary rule (frozen baseline Section 10)

Evidence records, decision registry, and provenance fingerprints keep
explicit external identities (path + digest + run id). No API UUID is
invented for them. Model references (`RetainedExecutionRecordReference`,
`AcceptanceAttestationReference`, `TestedScopeDeclaration`) carry the typed
identity of the reference, not the bytes.
