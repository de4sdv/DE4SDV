# Model-Organization & Lifecycle-Leakage Audit (batch 3)

Scope: model/file naming and model organization — lifecycle/increment leakage,
duplicated concern structures, misleading package/type/view names, semantic
boundaries. This audit precedes any edit; each finding is classified
MUST FIX / SHOULD FIX / KEEP / NEEDS DECISION.

## 0. Governance facts the audit rests on (verified)

These facts constrain what is "leakage" and what is legitimate:

1. **The AEBS chain models real increments per concern.** The pilot YAMLs
   declare `INC-AEBS-001` (framing), `INC-AEBS-002` (operational context),
   `INC-AEBS-003` (needs/requirements), `INC-AEBS-004` (functional), `INC-AEBS-005`
   (functional interfaces), `INC-AEBS-006` (logical), `INC-AEBS-007`
   (physical), `INC-AEBS-008` (simulation) as **separate chained increments**
   (`source_id`/`next_increment` links, `parent_increment` fields).
   Therefore `part incAEBS004 : FeatureIncrement` in
   `aebs_functional_architecture.sysml` is the identity-bearing usage of a
   real increment — NOT phase leakage. Same for `incMW002…incMW010` (the MW
   chain declares INC-MW-002…INC-MW-010 as distinct increments in
   `middleware-adapter-increment-framing.yaml` and downstream pilots).
2. **The INC-AEBS-010 chain is different**: its pilot declares ONE increment
   (`id: INC-AEBS-010`, `parent_increment: INC-AEBS-010`) traversed in
   phases; the architecture/configuration pilot slices describe themselves as
   "Phase 6-8 slice of the INC-AEBS-010 chain". The three model parts
   `incAEBS010Architecture`, `incAEBS010NeedsRequirements`,
   `incAEBS010Configuration` therefore model *phase work products* as
   separate increments — the exact anti-pattern this audit targets.
3. **INC-MW-010 is closed**: its V&V evidence pilot records
   `status: baselined_bounded` with an accepted Phase 12 baseline decision.
   The middleware verification-evidence file is the *retained evidence record*
   of that closed increment.
4. The ontology YAML **binds** `requirement def MiddlewareAcceptanceCriterion010`
   as the kernel mapping for `AcceptanceCriterion`, and cites
   `ScenarioIdentity010`, `RetainedMiddlewareEvidence010`,
   `EvidenceOutcome010`, `EvidenceDisposition010` in `native`/`external`
   descriptions. Any rename must update the ontology YAML in the same commit.
5. `scripts/generate_scenario_manifest.py` **constructs** type names
   `f"ScenarioIdentity{increment}"` / `f"EvidenceOutcome{increment}"` /
   matches benches by `increment in name`; `scripts/check_model_sync.py`
   regex-matches `ScenarioIdentity(\w+)` (suffix-agnostic). The committed
   `scenario-manifest.json` embeds the numbered type names.

## 1. MUST FIX (safe, semantically clear)

### M1. AEBS-010 pseudo-increment phase parts → one increment identity
- `incAEBS010NeedsRequirements` (aebs_visualization_needs_requirements.sysml:48)
- `incAEBS010Architecture` (aebs_visualization_functional_architecture.sysml:24)
- `incAEBS010Configuration` (aebs_visualization_variability_configuration.sysml:27)

These re-model *phases of INC-AEBS-010* as `VisualizationIncrement` parts.
The framing file already holds the single real increment part
`incAEBS010` ("framing through needs and System 2 requirements" — with doc
noting later slices). External references: exactly one
(`framingToNeeds` dependency from `incAEBS010NeedsRequirements to
incAEBS010`); the other two parts have zero references.

Fix: delete the three pseudo-parts; retarget the one dependency to
`incAEBS010`; the phase-3-5/6-8/9 provenance moves to the existing doc blocks
(`doc /* INC-AEBS-010 Phase N… */`) which already carry it. No IDs change;
traceability is preserved by the pilot YAMLs and the increment part.

Risk: low (1 dependency retarget; no external refs; view files untouched).
Type: pure model-organization correction; no semantic content change.

### M2. Middleware verification-evidence reusable vocabulary → de-numbered types
The file `middleware_verification_evidence.sysml` is the **retained evidence
record of the closed INC-MW-010** (status: baselined_bounded; accepted Phase
12 baseline; bound `configurationIdentity` MW-CONFIG-001). Its *record*
identity is legitimate (package keeps `…010VerificationEvidence`, evidence
IDs `E-MW-*` stay). But its *type vocabulary* is reusable middleware
verification semantics that later increments will want to reuse without
importing "010" names:

- `enum def ScenarioIdentity010` → `MiddlewareScenarioIdentity`
- `enum def EvidenceOutcome010` → `MiddlewareEvidenceOutcome`
- `enum def EvidenceDisposition010` → `MiddlewareEvidenceDisposition`
- `item def VehicleSpeedTranslationObservation010` → `VehicleSpeedTranslationObservation`
- `item def LifecycleObservation010` → `MiddlewareLifecycleObservation`
- `item def HealthObservation010` → `MiddlewareHealthObservation`
- `item def RetainedMiddlewareEvidence010` → `RetainedMiddlewareEvidence`
- `item def ReplayedMiddlewareEvaluation010` → `ReplayedMiddlewareEvaluation`
- `part def MiddlewareIntegrationVandVBench010` → `MiddlewareIntegrationVandVBench`
- `requirement def MiddlewareAcceptanceCriterion010` → `MiddlewareAcceptanceCriterion`
- `calc def Map010OutcomeToVerdict` → `MapEvidenceOutcomeToVerdict`
- `requirement def MiddlewareClaim010/Argument010/CounterClaim010` →
  `MiddlewareClaim/MiddlewareAssuranceArgument/MiddlewareCounterClaim`
- usage names `acceptanceCriterion010<Aspect>` → `acceptanceCriterion<Aspect>` (7)

Same-commit consumers: ontology YAML (kernel mapping declaration + 4
description citations), the file itself (12 defs + ~30 usage refs),
`.meta.json`/`sysand-lock.toml` keys unchanged (package name unchanged in
this item), `tests/test_middleware_view_presentations.py` (package ref only —
unchanged). Increment identity preserved: the package name, `incMW010`,
`MW-CONFIG-001`, `E-MW-*`, `AC-MW-010-*`, `VC-MW-010-*`, `CLM/AGT/CCM-MW-010-*`
all keep their identities; only the *type* names lose the number.

Risk: medium (evidence-record file; ontology kernel mapping must move in the
same commit; full-model ingestion revalidates). Type: name-only; zero
semantic change. This directly implements the user's stated preference.

### M3. 009-series verification files: reusable type vocabulary → semantic names
Each 009-series file declares file-local vocabulary carrying the increment
number (`EvidenceOutcome009H`, `Retained009HObservationSet`,
`Replayed009HEvaluation`, `BicycleTargetBench009H`, `EvidenceContract009H`,
`ScenarioIdentity009D/F/E`, per-file bench defs). These are the *reusable
observation/evaluation/bench-contract concepts* of each verification module —
the increment number marks only which increment introduced them. The files
themselves are evidence records of closed 009-series increments, so file
names and package names stay (KEEP below); the internal type names lose the
number and gain the distinguishing semantic stem, with the origin increment
documented in the doc comment at each def:

Pattern (per file, applied to all 8 files + execution environment):
- `EvidenceOutcome009X` → `<Scenario>EvidenceOutcome`
  (`PartialInterventionEvidenceOutcome`, `OverrideEvidenceOutcome`,
  `NonActivationEvidenceOutcome`, `DegradedInputEvidenceOutcome`,
  `PedestrianEvidenceOutcome`, `BicycleEvidenceOutcome`,
  `RegulatoryCriterionEvidenceOutcome`, `NominalEvidenceOutcome`)
- `ScenarioIdentity009X` → `<Scenario>ScenarioIdentity`
- `Retained009XObservationSet` → `<Scenario>ObservationSet`
- `Replayed009XEvaluation` → `<Scenario>Evaluation`
- `<Name>Bench009X` → `<Name>Bench` (BicycleTargetBench,
  NativeInterventionBench, FalseReactionMatrixBench, DegradedInputMatrixBench,
  NominalMovingVehicleTargetBench, …)
- `EvidenceContract009X` → `<Scenario>EvidenceContract`
- `Retained009BObservationSet/Replayed009BEvaluation` →
  `NominalObservationSet`/`NominalEvaluation` (per user's preferred names)
- `*009BRole` → semantic role names (NativeAutowareAEBRole,
  NominalAEBSCoordinatorRole, NominalVehicleCommandGateRole,
  IndependentScenarioEvidenceObserverRole)
- `AEB009AMaintainedJetsonEnvironmentContext` →
  `AEBMaintainedJetsonEnvironmentContext`
- `Nominal009BEvidenceContractRequirement` → `NominalEvidenceContractRequirement`

Same-commit consumers: `scripts/generate_scenario_manifest.py`
(`_extract_enum` constructs `<Prefix><increment>` — change to search the
de-numbered names; the INCREMENT_MAP filename→009X mapping stays as
*provenance metadata*, not name construction), regenerated
`scenario-manifest.json`, `tests/test_generate_scenario_manifest.py`
(bench-name assertions), `tests/test_check_model_sync.py` (fixture text —
already suffix-agnostic regex, update doc/fixture strings),
`scripts/check_model_sync.py` (regex already suffix-agnostic; doc comment
update), `sysand-lock.toml`/`.meta.json` (package names — unchanged in this
item), 4 committed SVGs carrying the old labels (`diagram-aebs009*…svg` —
regenerate via privileged run + byte-swap), VIEWS.md regenerated.

Provenance preserved: package names `DE4SDV_AEBS009*Verification` stay (see
KEEP), increment IDs `INC-AEBS-009B` etc. stay in doc blocks and pilot YAMLs.

Risk: medium (touches 9 model files + generator + manifest + tests + 4-6
SVGs). Mitigation: generator change is small (match by de-numbered name);
`check_model_sync` regex already tolerant; privileged validation re-run.

### M4. aebs_execution_environment package → semantic name
`package DE4SDV_AEBS009AExecutionEnvironment` in
`aebs_execution_environment.sysml` — the file holds the *enduring* execution-
environment context (the maintained Jetson environment) that later
increments build on. The 009A in the package name marks origin, not present
semantics. Per the user's preferred pattern: `DE4SDV_AEBSExecutionEnvironment`.
The view `aebs009AExecutionEnvironmentAssuranceView` →
`aebsExecutionEnvironmentAssuranceView`. Its one numbered def is handled in
M3. Consumers: `.meta.json`, `sysand-lock.toml`, VIEWS.md, 1 SVG, tests
(`test_execution_environment_ple.py` uses filename refs — verify).

Risk: low-medium. Type: name-only; package is the model's namespace anchor.

## 2. NEEDS DECISION — S1. Package nesting: flatten redundant `Features` hierarchy

10 files declare `package DE4SDV_X<Concern> { package Features { package
<Subject> { … } } }`. The unique top-level package already gives the
namespace; the nesting adds three redundant levels to every qualified name
(e.g. `DE4SDV_AEBSNeedsRequirements::Features::AEBS::NeedsRequirements::*`).

Recommendation: flatten — but NOT in this change. Scope check: ~95 qualified
`::Features::` references across 21 model files plus `tests/fixtures/
sysml_viewer_model` copies that mirror the tree shape, the seed script, and
viewer tests. Combined with this change's ~450 real renames it would make the
review undiffable and mix two concerns. Do it as its own follow-up change
(model-tree reshape, one privileged-validation + byte-swap cycle, no name
changes, reviewer sees only import-path deletions).

This audit deliberately re-classifies S1 from SHOULD-FIX-now to NEEDS DECISION
with that recommendation.

## 3. KEEP (classified, not leakage)

- File names/packages of 009-series verification & evidence slices
  (`aebs_bicycle_verification.sysml` + `DE4SDV_AEBS009HVerification`, …):
  these files ARE the retained evidence records of closed increments; the
  number in the *file/package* identity is legitimate (identity-bearing
  record). Only their internal *type* names are normalized (M3).
- `package DE4SDV_Middleware010VerificationEvidence` — retained record of
  closed INC-MW-010 (user's rule 4/13; also success-or-decision: rename
  package would break `sysand-lock.toml` provenance binding and the
  ontology kernel file anchor; keep package, de-number types).
- `part incAEBS001…008`, `incMW002…010` + their pilot YAML increment IDs:
  real increments per governance model (audit fact 1). Not phase leakage.
- `mw010RetroactiveClosureOutOfScope` — increment-scoped out-of-scope record.
- `inc_aebs_009a_jetson_execution_environment.sysml` — exact generated
  configuration projection (user's rule 13).
- `successorIncrementDecision010` — Phase 12 decision record of INC-MW-010.
- Evidence dirs `009b…009i`, `010/`; `board_sepolicy_aebs010.mk`; bench
  package names; branch names in pilot records.
- `firstSliceScope` (aebs_increment_framing) — evaluates as historical
  scope record of INC-AEBS-001; the whole increment-framing file is the
  *increment-chain record* of the AEBS method pilot (KEEP file; see M5 note).
- Configuration status-word filenames (`apple-silicon-macos-candidate`,
  `example-linux-score-autoware`): real configuration classes per PLE README.
- All registered lifecycle IDs (`INC-*`, `REQ-*`, `N-*`/`NEED-*`, `E-MW-*`,
  `EVID-*`, `GAP-*`, `BL-*`, `SC-*`, `AC-*`, `VC-*`, `CLM/AGT/CCM-*`).

## 4. NEEDS DECISION (with recommendations)

### D1. AEBS visualization directory split (user §6)
Recommendation: **do not move** the 7 `aebs_visualization_*.sysml` files
into a `visualization/` (or `system2/visualization/`) subdirectory in this
change. Reasons: (a) the module is 7 files with clean `DE4SDV_AEBSVisualization*`
package prefixes that already make the System 2 boundary unambiguous; (b)
`features/` currently has only `aebs/` and `middleware/` — introducing the
first subject subdirectory is a model-tree reorganization that interacts
with `.meta.json` layout, the privileged workflow's directory-scoped
diagram generation, VIEWS.md generation roots, and PR #177's in-flight
addition of an eighth visualization slice (high conflict surface); (c) the
user's own rule — "do not create directories merely for aesthetic
consistency if the module is too small" — applies: the files are cohesive
in one directory and every name carries `Visualization`.
Recommendation: adopt the directory split when a second System-2 module
arrives, as a model-tree change with its own validation cycle.

### D2. Vocabulary convergence (`needs_requirements` vs `stakeholder_needs`
+ `requirements`; `evidence` vs `verification_evidence`;
`increment_framing` vs `framing`)
Splitting `aebs_needs_requirements.sysml` into two files and renaming
`aebs_evidence.sysml` → `aebs_verification_evidence.sysml` /
`aebs_increment_framing.sysml` → `aebs_framing.sysml` are semantic-model
restructures (file splits change package ownership; the MW files already
demonstrate the target vocabulary). Recommendation: do the renames as part
of the *next content increment* that touches those files, not inside this
naming pass — the current AEBS chain treats each concern traversal as its
own increment (audit fact 1), so the file names mirror real increment
boundaries. Recorded here with a concrete recommendation; not silently
deferred.

### D3. `DE4SDV_Middleware010VerificationEvidence` package name
User's example list offers `DE4SDV_MiddlewareVerificationEvidence`. The
package is the retained record of the *closed* INC-MW-010 (audit fact 3:
baselined_bounded, Phase 12 accepted). Under rule 13 the identity suffix in
the record's package name is legitimate. Recommendation: KEEP the package
name (record identity), executed via M2 for the types. If the middleware
concern later gains a *new* verification-evidence increment, that new
record gets a new identity name; the closed record stays.

## 4b. Post-implementation status (batch 3)

Executed: M1 (3 pseudo-increment parts removed; dependency retargeted to the
single `incAEBS010` with a provenance doc note), M3 (284 type-token renames +
96 usage renames across 9 AEBS files; generator switched from constructed
names to a per-increment semantic-enum registry; manifest regenerated;
11 consumer files updated), M2 (14 MW evidence type defs de-numbered; ontology
kernel mapping + citations updated same-commit; record usages KEEP),
M4 (execution-environment package + view renamed; meta/lock updated).

KEPT per audit §3: all packages of closed-increment evidence records, all
registered IDs, all argumentation/criterion/case usage names encoding
registered IDs, all identity-bearing file names.

NEEDS DECISION: D1 (visualization directory split), D2 (vocabulary
convergence), D3 (MW evidence package name), S1 (Features-nesting flatten).

## 5. Implementation order (this change)

1. M1 (pseudo-increment parts) — model-only, tiny.
2. M3 (009-series types) + generator/manifest/tests update.
3. M2 (MW evidence types) + ontology same-commit update.
4. M4 (execution-environment package) + meta/lock/VIEWS/SVG.
5. Regenerate scenario-manifest, VIEWS.md, view indexes.
6. Full validation battery + privileged validation + byte-swap.

Items 2-4 all ride the same privileged-validation/byte-swap cycle to avoid
three separate diagram-regeneration rounds.
