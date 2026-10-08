# O4 definition-migration path (verified, explicitly selected, fail-closed)

Status: **non-production migration path — prepared, not activated.** No
consumer is retired, the authored authority stays active, and every
runtime/validation consumer ledger row stays `pending`. This record is not a
migration-complete claim.

## What moved

The admitted 22-identity definition consumption now has a verified
non-production construction entry point, not merely a caller-supplied object.
One module — `de4sdv/semantic/definition_migration.py` —
loads and verifies the candidate pair through
`de4sdv.semantic.definition_candidate` (pair contract, recorded
source-revision binding, regeneration equality, frozen-O3 disjointness),
builds the explicit `DefinitionCandidateProvider`, and passes that verified
provider through the existing runtime seam into the same consumer classes the
production paths use:

- `OntologyApiBinder` (class mapping → governed declaration → validated UUID);
- `KernelBindingIndex` (ingestion-validated identity, both directions);
- `SemanticTraversal` (relationship mappings; unadmitted identities delegate);
- `SemanticQueryService` plus the impact-service provenance (authority id
  `definition-candidate:<source_revision>`).

Admitted identities resolve exclusively from the candidate artifacts. Every
other identity delegates explicitly to the authored `KernelContract` — the
remaining legacy dependency stays visible and is never hidden.

## Selection

O4 Wave C2 removed the separate migration selector and its runtime builder
(`build_definition_migration_runtime`, `DE4SDV_DEFINITION_MIGRATION`): the
admitted definitions are part of the model-built kernel contract served by
the model-authority runtime ([model-authority-runtime.md](model-authority-runtime.md)).
The definition-candidate provider and the migration probe
(`scripts/probe_definition_migration.py`) remain build-time evidence; the
probe's report feeds the model bundle closure.

## Activation prerequisite (fresh exact-revision API closure)

The admitted rows are published `api_identity: unclaimed` / `traversal:
false` (vocabulary-only). Activating the migration path therefore requires a
**fresh exact-revision API closure**: the validated revision binding for the
exact revision must carry an ingestion-validated kernel binding for every
admitted identity whose `source_file`/`declaration` agree with the candidate
pair, with non-empty, unique binding identities. The caller must supply the
expected Git revision explicitly, and both revision and ontology identity
must match the validated binding. A missing, stale, foreign-ontology,
ambiguous, or incomplete binding cannot establish closure. This is a binding
consistency prerequisite, not production authorization or proof of a deployed
consumer migration. Run privileged ingestion/binding validation for the
admitted declarations at the intended permanent revision before any such
claim. The production default is unchanged.

### Historical retained replay

A local probe of retained run `34576049742` used its real full-model export
and binding at `0a23902370de9fc74d6118afe480382e0b0d8aa0`, compared with the
permanent inspection basis `26b8fccf7df6435e38465e60665974a6a9fc2acf`.
All 22 candidate mappings equal the authored comparison mappings; the
82,011-element export has declaration-form matches for 21. The historical
binding lacks `Scenario` and is not bound to the inspection revision or its
ontology digest. It therefore does **not** establish current closure.
The real consumer-wiring regression uses synthetic validated bindings;
that test is not privileged API evidence or consumer retirement.

## Executable offline probe

    python scripts/probe_definition_migration.py [--binding PATH] [--export PATH] [--expected-git-revision SHA]

Read-only, offline: reports per-identity candidate-vs-authored mappings, the
closure state and its prerequisite, the remaining legacy-only class count,
and — when a retained export is supplied — declaration-form matches as
representation evidence (never an identity claim).

## Non-claims

- Not migration-complete: partial migration retires nothing; the consumer
  ledger keeps every runtime/validation consumer row `pending`.
- No production activation; no authored-YAML retirement; no API identity or
  traversal claim for the admitted rows.
- The frozen O3 13-identity semantics and the accepted bundle route are
  preserved; the migration path never composes with them.