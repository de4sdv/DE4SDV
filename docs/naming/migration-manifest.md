# DE4SDV Naming/Identity Migration Manifest

Companion to [`naming-conventions.md`](naming-conventions.md) and
[`naming-qa-report.md`](naming-qa-report.md). Every rename in this repository
migration is listed here with its impact set. Identity types:
`semantic` (canonical, reusable), `record` (identity-bearing, lifecycle-bound),
`external` (not ours), `legacy` (kept, documented alias).

## Sequencing constraint (read first)

**PR #177** (`feat/aebs010-visualization-verification-evidence`, open,
non-draft, review-ready) adds the INC-AEBS-010 Phase 10 slice and touches the
same `aebs_010_visualization_*` family this migration renames. Renaming under
an in-flight review would force a full re-review. Therefore:

- **Batch 1 (this migration, now):** middleware normalization, AEBS
  canonical-slice normalization that PR #177 does not touch
  (`functional_behavior`, `aebs_evidence` naming), pilot-file scheme,
  terminology fix, registries, enforcement, generated-artifact regeneration.
- **Batch 2 (scheduled, after #177 merges):** the `aebs_010_visualization_* →
  aebs_visualization_*` family — full manifest entries are prepared below and
  must be executed verbatim then.

## Batch 1 — executed in this migration

### M1. Middleware SysML slice renames (semantic; representation+name only)

For each row: rename file, global package, all qualified references, imports;
sweep `.meta.json`, pilots, tests, docs, workflows. Semantic meaning is
unchanged — only representation/name changes. No SysML ID/provenance UUIDs
change (packages are not usage elements; no `api_object_id` is bound to
package names in the fixtures — verified against `de4sdv/sysml_api/fixture.py`,
which binds only aebs usage names).

| Old file | New file | Old package | New package | Reason |
|---|---|---|---|---|
| `middleware_increment_framing.sysml` | `middleware_increment_framing.sysml` | `DE4SDV_MiddlewareIncrementFraming` | `DE4SDV_MiddlewareIncrementFraming` | Abbreviation policy (record usage `incMW002` inside keeps its identity) |
| `middleware_feature_classification.sysml` | `middleware_feature_classification.sysml` | `DE4SDV_MiddlewareFeatureClassification` | `DE4SDV_MiddlewareFeatureClassification` | Abbreviation policy |
| `middleware_operational_context.sysml` | `middleware_operational_context.sysml` | `DE4SDV_MiddlewareOperationalContext` | `DE4SDV_MiddlewareOperationalContext` | Abbreviation policy |
| `middleware_stakeholder_needs.sysml` | `middleware_stakeholder_needs.sysml` | `DE4SDV_MiddlewareStakeholderNeeds` | `DE4SDV_MiddlewareStakeholderNeeds` | Abbreviation policy |
| `middleware_requirements.sysml` | `middleware_requirements.sysml` | `DE4SDV_MiddlewareRequirements` | `DE4SDV_MiddlewareRequirements` | Abbreviation policy |
| `middleware_functional_architecture.sysml` | `middleware_functional_architecture.sysml` | `DE4SDV_MiddlewareFunctionalArchitecture` | `DE4SDV_MiddlewareFunctionalArchitecture` | Abbreviation policy |
| `middleware_logical_architecture.sysml` | `middleware_logical_architecture.sysml` | `DE4SDV_MiddlewareLogicalArchitecture` | `DE4SDV_MiddlewareLogicalArchitecture` | Abbreviation policy |
| `middleware_physical_software_realization.sysml` | `middleware_physical_software_realization.sysml` | `DE4SDV_MiddlewarePhysicalSoftwareRealization` | `DE4SDV_MiddlewarePhysicalSoftwareRealization` | Abbreviation policy |
| `middleware_variability_configuration.sysml` | `middleware_variability_configuration.sysml` | `DE4SDV_MiddlewareVariabilityConfiguration` | `DE4SDV_MiddlewareVariabilityConfiguration` | Abbreviation policy |
| `middleware_verification_evidence.sysml` | `middleware_verification_evidence.sysml` | `DE4SDV_Middleware010VerificationEvidence` | `DE4SDV_Middleware010VerificationEvidence` | Abbreviation policy; the `010` stays — the package **is** the immutable INC-MW-010 evidence record (identity type: record) |

Impact set for M1 (all migrated in the same commits as the renames):
- SysML internal: `private import DE4SDV_Middleware010VerificationEvidence::*` in the
  two AEBS 010-visualization files (framing, variability-configuration) —
  these import names must change **in the same commit** even though the files
  themselves belong to Batch 2 (import-name-only edit, batch-2 files get
  their own rename later; this is the one deliberate cross-batch touch, kept
  minimal and recorded here).
- `.meta.json`: key `MiddlewareAutowareAAOSSDVReference` is a product-model key (M2),
  no middleware-feature keys exist. Verified.
- Pilot YAMLs (M3): `artifact: …mw_*.sysml`, `sysml_element: DE4SDV_MW*`,
  `INC-MW-00N` identity IDs unchanged, `schema:` IDs unchanged (schemas are
  versioned API surface, not names).
- Tests: `test_vv_evidence_parse_gate.py` PILOTS list,
  `test_sysmod_sysand_integration.py`, `tests/test_check_naming.py` new guard
  tests asserting them. (Correction, verified during audit: no
  `MW-00N`-style slice keys exist inside pilot files — each pilot is one
  increment record — so no key migration is needed.)
- Scripts: `scripts/generate_view_index.py` middleware folder path (unchanged
  — the *directory* `features/middleware/` already uses the canonical
  spelling; only filenames change), `scripts/check_model_sync.py` (no MW
  refs — verified), privileged workflow path
  `.github/workflows/privileged-syside-validation.yml` middleware path
  (directory unchanged; filename globs none — verified no per-file listing).
- Docs: `docs/repository-tree.md`, `docs/guides/sysml-elements.md`,
  `docs/references/model-html-viewer.md`,
  `methodologies/sysmod-sysmlv2/process-mapping.md`,
  `implementation/aaos-sdv-reference-interop-bench/README.md`,
  `textual-notation-of-model/packages/features/middleware/VIEWS.md` (regenerated),
  `approach/framework/ontology/de4sdv-basic-ontology.yaml`
  (kernel mapping `file:` path for `AcceptanceCriterion` →
  `middleware_verification_evidence.sysml`; declaration name
  `MiddlewareAcceptanceCriterion010` unchanged — it is the record's
  requirement def and is already spelled `Middleware`).
- Generated: middleware `VIEWS.md`, 2 diagram SVGs keyed by view names (M5).
- Historical docs NOT touched: `docs/plans/2026-07-29-middleware-integration-chain.md`
  keeps historical `mw_*` references **only where they narrate merged
  history**; its forward-looking filename references are updated (wording
  fix M7 covers the phase/increment conflation).
- Evidence records under `implementation/aaos-sdv-reference-interop-bench/evidence/`
  (`e-mw-*.yaml`, `mw-010-*.yaml`): NOT renamed — evidence-ID-bound legacy
  filenames (registered alias). One non-identity reference inside
  `e-mw-014-health-disposition.yaml` pointing at a renamed slice path is
  updated as a reference fix, not a rename.

Risk: LOW-MEDIUM. Pure representation rename inside one model area; import
graph is closed (only the two AEBS 010 files import MW packages); no runtime
code binds these package names. Validation: full test suite + generated-index
regeneration + privileged SysIDE validation request at PR review (syside not
executable on this host — documented in the PR).

### M2. Middleware product-model + configuration (semantic)

| Old | New | Type |
|---|---|---|
| `model-based-product-line-engineering/product-models/middleware_autoware_aaos_sdv_reference.sysml` | `middleware_autoware_aaos_sdv_reference.sysml` | semantic (generated projection — regenerate via configurator, not hand-edit) |
| `model-based-product-line-engineering/feature-configurations/middleware-autoware-aaos-sdv-reference.yaml` | `middleware-autoware-aaos-sdv-reference.yaml` | semantic |
| `.meta.json` key `MiddlewareAutowareAAOSSDVReference` | `MiddlewareAutowareAAOSSDVReference` | generated index key (regenerated with product model) |

Impact: `test_execution_environment_ple.py`, `test_configure_variant.py`
(config list), PLE README, `docs/repository-tree.md`, viewer docs. The
product model's internal package/defs already use `Middleware`/full names
(verified: `MiddlewareAutowareAAOSSDVReference` exists only as filename+meta key).

Risk: LOW.

### M3. Pilot YAML filename scheme (semantic; representation only)

Unify to `<subject>-<concern>.yaml` kebab-case; increment-visualization
pilots keep their increment-scoped names (they intentionally are that
increment's framing records).

| Old | New | Note |
|---|---|---|
| `pilots/middleware-feature-classification.yaml` | `pilots/middleware-feature-classification.yaml` | +8 more `mw-*` → `middleware-*` (all ten slices) |
| `pilots/aebs-functional-architecture.yaml` | `pilots/aebs-functional-architecture.yaml` | M6 companion |
| `pilots/aebs-010-visualization.yaml`, `-architecture.yaml`, `-configuration.yaml` | unchanged | increment-scoped records (identity type: record) |
| `pilots/aebs-*.yaml` (canonical slices) | unchanged | already conform |
| `pilots/middleware-adapter-increment-framing.yaml` | unchanged | already conforms |

Impact: `tests/test_vv_evidence_parse_gate.py` PILOTS list,
`test_sysmod_sysand_integration.py`, cross-references inside pilots,
`docs/repository-tree.md`, process-mapping doc. Slice keys `MW-00N:` inside
renamed pilots become `MIDDLEWARE-00N:`? — **No**: slice keys are file-local
anchors referenced by view-index prose and guard tests; they are migrated
(`MW-00N` → `MIDDLEWARE-00N`) together with the view-index prose that quotes
them, and the guard tests asserting them. This is an internal-key migration,
not an evidence-ID migration (no evidence ID has the form `MW-00N` — verified:
evidence IDs are `E-MW-0NN`; `E-` prefix differs).

Risk: LOW. Guard tests updated in same commit.

### M4. AEBS canonical-slice normalization not touching #177 (semantic)

| Old | New | Old package | New package | Reason |
|---|---|---|---|---|
| `aebs_functional_architecture.sysml` | `aebs_functional_architecture.sysml` | `DE4SDV_AEBSFunctionalArchitecture` | `DE4SDV_AEBSFunctionalArchitecture` | Align filename/package with method vocabulary (functional architecture is the concern; "behavior" was the slice's action set) |
| `aebs_evidence.sysml` | `aebs_evidence.sysml` (file kept) | `DE4SDV_AEBS009BNominalEvidence` | unchanged | Resolved choice: file is the INC-AEBS-009B nominal evidence record; rather than rename the file to half-generic, the conventions doc declares `*_evidence.sysml` valid and the package makes the record explicit. No rename — the mismatch is resolved by documentation + enforcement exemption note. |

M4a impact: `scripts/check_model_sync.py` (imports
`aebs_needs_requirements.sysml` only — unaffected), pilot
`aebs-functional-architecture.yaml` (M3 renames it), `docs/repository-tree.md`,
`tests/test_aebs_view_presentations.py` + `test_mw_view_presentations.py`
(view-identity strings `aebsFunctionalArchitectureView →
aebsFunctionalArchitectureView` — wait: view name inside the file is
`aebsFunctionalArchitectureView`; it is an enduring canonical view introduced by
INC-AEBS-004 → renamed to `aebsFunctionalArchitectureView` per §12 rules),
`scripts/generate_view_index.py` notes regex unaffected, diagram
`diagram-aebsFunctionalArchitectureView.svg` regenerated (name change propagated
by generator), `VIEWS.md` regenerated, `.meta.json` has no
FunctionalBehavior keys (verified).

Risk: LOW.

### M5. View-identity normalization inside MW evidence record (record's view names)

`middleware_verification_evidence.sysml` (→ `middleware_verification_evidence.sysml`)
declares `middlewareVerificationAssuranceView` and `middlewareOpenCounterclaimAssuranceView`.
These views are the canonical assurance views of the middleware evidence
record — they are enduring views *of that record*, and the record persists.
Decision per conventions §8: the views take semantic names without the
lifecycle number, the increment stays in doc/provenance:

- `middlewareVerificationAssuranceView` → `middlewareVerificationAssuranceView`
- `middlewareOpenCounterclaimAssuranceView` → `middlewareOpenCounterclaimAssuranceView`

Impact: diagram filenames (`diagram-middlewareVerificationAssuranceView.svg`,
`diagram-middlewareOpenCounterclaimAssuranceView.svg`) regenerated under new
names, old SVGs deleted, `VIEWS.md` regenerated,
`tests/test_middleware_v_and_v_evidence.py` +
`tests/test_middleware_view_presentations.py` identity strings. **Diagram regeneration requires SysIDE (`syside viz view`),
which is not executable on this ARM host** — handled by the documented
privileged-validation swap procedure (skill: download `syside-diagrams`
artifact from the failed CI run and byte-swap), prepared in the PR body as
the expected one repair cycle.

Risk: MEDIUM (needs one privileged CI round-trip for the two SVGs).

### M6. Kernel/ontology contract touch (semantic)

`approach/framework/ontology/de4sdv-basic-ontology.yaml` `AcceptanceCriterion.kernel.file`
points at `middleware_verification_evidence.sysml` — updated to the renamed path in
the same commit (M1). No new kernel declarations are introduced by this
migration, so the ontology-kernel set equation is untouched. Verified by
`scripts/check_model_sync.py` in validation.

Risk: LOW.

### M7. Increment/phase terminology fixes (prose)

- `docs/plans/2026-07-29-middleware-integration-chain.md`: fix
  "phase N increment" conflation → "increment slice" wording; keep historical
  narrative references.
- Any residual "12-phase" label: none found (guard test already pins this).
- The conventions doc (§1) is the authoritative increment/phase/record
  distinction.

Risk: LOW (docs only).

### M8. Configuration filename status audit (assessment; two actions)

- `fixtures/invalid-score-android.yaml`: deliberately-invalid fixture → move to
  `model-based-product-line-engineering/feature-configurations/fixtures/fixtures/invalid-score-android.yaml`;
  update `test_configure_variant.py` and PLE README.
- `apple-silicon-macos-candidate.yaml`, `nxp-zephyr-vehicle-target-candidate.yaml`:
  "candidate" is real scope metadata (Gate C ratified scope class, PR #181)
  → keep filename, rationale documented in conventions §7.
- `example-linux-score-autoware.yaml`: deliberate example class → keep,
  documented.
- `inc-aebs-009a-jetson.yaml` and product models `inc_aebs_009a_*.sysml`:
  exact-increment configuration projection (identity type: record) → keep,
  documented.

Risk: LOW.

### M9. Enforcement (new)

- New `scripts/check_naming.py`: conservative checks — project-owned `.sysml`
  filename shape; canonical-concern filenames must not embed
  increment-number patterns except registered exemptions (evidence records,
  increment-scoped records, batch-2 pending list); registered ID prefixes +
  subject namespaces for ID-shaped tokens in project-owned sources;
  abbreviation policy for new filenames/packages. Wired into
  `scripts/check_repo.py` (separate module; no overlap with PR #181's
  `check_repo.py` edits — PR #181 adds a scope check; merge is additive and
  conflicts, if any, are trivial).
- Exemptions encoded as data with reasons (upstream, fixtures, experiments,
  evidence records, bench tooling, batch-2 pending list).
- New test `tests/test_check_naming.py`.

Risk: LOW (checks are additive; failure mode is a clear message).

### M10. Documentation (new)

- `docs/naming/naming-conventions.md`, `naming-qa-report.md`, this manifest.
- `docs/repository-tree.md` regenerated paths.
- `AGENTS.md`/`CLAUDE.md`: no change required (they do not reference renamed
  paths — verified); glossary gains increment/phase/record pointers to the
  conventions doc.

## Batch 2 — execution record (this PR; merged before PR #177's Phase 10 slice)

> Note: batch 2 was executed on `chore/repo-naming-identity-migration` ahead of
> PR #177's merge (maintainer directed the repository-wide normalization to
> proceed). PR #177 adds an eighth slice
> (`aebs_010_visualization_verification_evidence.sysml` + 2 SVGs + tests +
> evidence YAML); after #177 merges, its filenames follow the same M11 mapping
> (`aebs_visualization_verification_evidence.sysml`,
> `DE4SDV_AEBSVisualizationVerificationEvidence`) and its tests/SVGs inherit
> the canonical names. The overlap is declared here so reviewers of both PRs
> see one authoritative mapping — no silent divergence.

### M11. `aebs_010_visualization_*` → canonical concern integration — EXECUTED

INC-AEBS-010 provenance is preserved in each file's header doc and pilot YAML;
filenames/packages/views drop the increment number because the slices are the
enduring canonical concern models for the AEBS visualization System 2 test
system (there is exactly one such concern family — no parallel canonical AEBS
visualization architecture exists or is planned, so integration does not
create a duplicate authority).

| Old file | New file | Old package | New package |
|---|---|---|---|
| `aebs_010_visualization_framing.sysml` | `aebs_visualization_framing.sysml` | `DE4SDV_AEBS010VisualizationFraming` | `DE4SDV_AEBSVisualizationFraming` |
| `aebs_010_visualization_operational_context.sysml` | `aebs_visualization_operational_context.sysml` | `DE4SDV_AEBS010VisualizationOperationalContext` | `DE4SDV_AEBSVisualizationOperationalContext` |
| `aebs_010_visualization_needs_requirements.sysml` | `aebs_visualization_needs_requirements.sysml` | `DE4SDV_AEBS010VisualizationNeedsRequirements` | `DE4SDV_AEBSVisualizationNeedsRequirements` |
| `aebs_010_visualization_functional_architecture.sysml` | `aebs_visualization_functional_architecture.sysml` | `DE4SDV_AEBS010VisualizationFunctionalArchitecture` | `DE4SDV_AEBSVisualizationFunctionalArchitecture` |
| `aebs_010_visualization_logical_architecture.sysml` | `aebs_visualization_logical_architecture.sysml` | `DE4SDV_AEBS010VisualizationLogicalArchitecture` | `DE4SDV_AEBSVisualizationLogicalArchitecture` |
| `aebs_010_visualization_physical_realization.sysml` | `aebs_visualization_physical_software_realization.sysml` | `DE4SDV_AEBS010VisualizationPhysicalRealization` | `DE4SDV_AEBSVisualizationPhysicalSoftwareRealization` |
| `aebs_010_visualization_variability_configuration.sysml` | `aebs_visualization_variability_configuration.sysml` | `DE4SDV_AEBS010VisualizationVariabilityConfiguration` | `DE4SDV_AEBSVisualizationVariabilityConfiguration` |
| (PR #177's Phase 10 slice when merged) | `aebs_visualization_verification_evidence.sysml` | (`…010VisualizationVerificationEvidence` if so named) | `DE4SDV_AEBSVisualizationVerificationEvidence` |

In-file renames: `VisualizationIncrement` usage `incAEBS010` (keeps ID),
`Aebs010VisualizationFunctionalFlow` → `AebsVisualizationFunctionalFlow`,
`AEBS010VisualizationPhysicalSystem` → `AEBSVisualizationPhysicalSystem`,
views `aebs010FramingView → aebsVisualizationFramingView`,
`aebs010FunctionStructureView → aebsVisualizationFunctionStructureView`,
`aebs010FunctionInternalExchangeView`, `aebs010FunctionRequirementMappingView`,
`aebs010LogicalStructureView`, `aebs010LogicalInternalExchangeView`,
`aebs010NeedsView`, `aebs010RequirementTraceView`,
`aebs010OperationalContextView`, `aebs010PhysicalStructureView`,
`aebs010PhysicalInternalExchangeView`, `aebs010PhysicalLogicalMappingView`,
`aebs010ProductLineConfigurationView`, `aebs010ProductModelAssemblyView` →
`aebsVisualization*` forms (enduring canonical views; increment → doc
provenance). `ScenarioIdentity010`, `SC-AEBS-010-*`, `REQ-AEBS-S2-*`,
`INC-AEBS-010`, `EVID-*`, `AC-*` IDs: unchanged (registered identities).

Impact set (same-commit sweep): the two `private import
DE4SDV_Middleware010VerificationEvidence`/`DE4SDV_AEBS010…` files cross-import each
other; pilots `aebs-010-visualization*.yaml` `sysml_element:`/`artifact:`
references (pilot filenames stay increment-scoped, their element refs update);
tests `test_aebs_010_*.py` (5 files; renamed `test_aebs_visualization_*.py`),
`test_aebs_hmi_presentation_contract.py` refs; `.meta.json` (7 keys);
`docs/repository-tree.md`; diagrams (13 SVGs) regenerated from renamed views;
VIEWS.md regenerated; privileged workflow unaffected (directory-level path).
Bench-side names (`de4sdv_aebs_010_bridge` ROS package, `board_sepolicy_aebs010.mk`,
evidence dirs `010/`, `inc-aebs-010-live-visualization.mp4`, PF records):
**external/retained — never renamed**.

Risk: medium-high (largest family, in-flight PR dependency) — mitigated by the
declared #177 overlap note above and a full consumer sweep (executed).

### M12. Numbered reusable definitions in 009-series evidence slices — EXECUTED (canonical-file subset)

The 009-series slices are immutable evidence records of bounded increments;
their **declarations** carry the increment suffix because the evidence
records are identity-bearing. Per conventions §2 these are legitimate
records — **no rename**. The one flagged item
(`PlannedAEBScenarioHarness009B009C`, `PlannedAEBScenarioAssets009B009C`,
`AEBReadinessInputs009A` in `aebs_logical_architecture.sysml` /
`aebs_physical_software_realization.sysml` — *canonical* files, not evidence
records) is a genuine violation of §2: planned (reusable) definitions named
by origin increments. Migration (batch 2, model-content-adjacent — flagged as
a name-only change, semantics unchanged):
`AEBReadinessInputs009A → AEBReadinessInputs`,
`PlannedAEBScenarioHarness009B009C → PlannedAEBScenarioHarness`,
`PlannedAEBScenarioAssets009B009C → PlannedAEBScenarioAssets`, with the
origin increments documented in their doc blocks. Impact: qualified refs in
`aebs_execution_environment.sysml` + `aebs_simulation_deployment.sysml`
imports, `tests/test_aebs_009g_009h_crossing_target.py`,
`tests/test_verification_model_invariants.py`,
`scripts/check_model_sync.py` (no refs — verified), diagrams
(`diagram-aebsSystemStructureView.svg` etc.) regenerated if labels change.

Risk: MEDIUM (touches canonical architecture files; name-only).

## Compatibility handling

- No heuristic string aliases in the semantic layer (rule §13): old package
  names are **not** added as alias imports. Grep-verified zero residual
  references after each batch (residual audit §21 of the task).
- Legacy spellings that remain (`MW` subject code, `E-` prefix, `e-mw-*`
  evidence filenames, `inc*` usage names, bench package names) are registered
  in the conventions doc with reasons — documented compatibility, not hidden
  drift.

## Validation gates (per batch)

1. `python scripts/check_repo.py` (includes ontology-kernel sync + new
   naming checks)
2. `python scripts/smoke_test.py`
3. `python -m unittest discover -s tests` + `pytest tests/test_semantic_mcp.py -q`
   (CI-equivalent local set)
4. Generated-index regeneration + staleness check
   (`scripts/generate_view_index.py` per folder; committed-artifact check
   runs privileged-only for SVGs)
5. Privileged SysIDE validation + diagram byte-swap: maintainer-run at PR
   review (local syside not executable on ARM — qemu loader missing). PR body
   documents this per AGENTS.md feedback-loop rule 3.

## Risk assessment summary

| Batch | Highest risk | Mitigation |
|---|---|---|
| 1 | MW evidence view SVGs need privileged regeneration | Prepared swap procedure; one CI round-trip budgeted |
| 1 | PR #181 merge conflict in `check_repo.py`/`validate_sysml.py` | Naming checks live in a new module; hook point is one import line |
| 1 | Missed stale path literal | Case-insensitive repo-wide grep sweep for every retired name (residual audit) |
| 2 | 010 family rename collides with #177 review | Sequenced after merge; manifest entries pre-written |
| 2 | Numbered-def rename touches architecture files | Name-only, full test set + privileged validation |

---

## Batch 1 execution record (post-implementation)

Commit `1f45409` on `chore/repo-naming-identity-migration` (102 files:
1879 insertions, 3977 deletions — deletions dominated by the 23 removed
stale-named SVGs and their VIEWS.md embeds).

### Old → new canonical name map (implemented)

- 10 middleware SysML slices: `mw_<concern>.sysml → middleware_<concern>.sysml`;
  packages `DE4SDV_MW<Concern> → DE4SDV_Middleware<Concern>`;
  `DE4SDV_MW010VerificationEvidence → DE4SDV_Middleware010VerificationEvidence`
  (record identity kept).
- 22 middleware view identities: `mw<Name>View → middleware<Name>View`;
  `mw010VerificationAssuranceView → middlewareVerificationAssuranceView`,
  `mw010OpenCounterclaimAssuranceView → middlewareOpenCounterclaimAssuranceView`;
  concern usage `mwIncrementAssuranceConcern → middlewareIncrementAssuranceConcern`.
- Product line: `mw_autoware_aaos_sdv_reference.sysml →
  middleware_autoware_aaos_sdv_reference.sysml`;
  `MWAutowareAAOSSDVReference[ConfiguredMember] →
  MiddlewareAutowareAAOSSDVReference[ConfiguredMember]`; BoF
  `mw-autoware-aaos-sdv-reference.yaml → middleware-autoware-aaos-sdv-reference.yaml`;
  product model regenerated by `tools/configure_variant.py` (new BoF SHA
  `bd06674c…`, provenance header updated by the generator).
- Pilot YAMLs: 9 × `mw-<concern>.yaml → middleware-<concern>.yaml`;
  `aebs-functional-behavior.{yaml,md} → aebs-functional-architecture.{yaml,md}`.
- AEBS functional architecture:
  `aebs_functional_behavior.sysml → aebs_functional_architecture.sysml`,
  `DE4SDV_AEBSFunctionalBehavior → DE4SDV_AEBSFunctionalArchitecture`,
  `aebsFunctionalBehaviorView → aebsFunctionalArchitectureView`.
- Configurations: `invalid-score-android.yaml →
  feature-configurations/fixtures/invalid-score-android.yaml`.
- Prose normalization: 5 × bare `MW-010` → `INC-MW-010`.
- Tests renamed: `test_mw_* → test_middleware_*` (4 files).
- `.meta.json` keys regenerated (`MiddlewareAutowareAAOSSDVReference`,
  `DE4SDV_AEBSFunctionalArchitecture`, 10 middleware entries).

### Preserved legacy identities (verified unchanged)

All `INC-*`, `REQ-*`, `N-*`, `AC-*`, `VC-*`, `E-MW-*`, `EVID-*`, `GAP-*`,
`BL-*`, `SC-*`, `SCN-*`, `SRC-*`, `PF-*`, `EC-*` IDs; `MW-CONFIG-001` and
`AEBS-CONFIG-010-001` configuration identities; retained-evidence filenames
(`e-mw-*.yaml`, `mw-010-google-cloud-vsidlc-cuttlefish.yaml`, `evidence/009d/`,
`evidence/010/`); bench identities (`de4sdv_aebs_009b_bench`,
`de4sdv_aebs_010_bridge`, `board_sepolicy_aebs010.mk`, launch/param/config
YAMLs); `SAF_Viewpoints.sysml` (upstream-named); ADRs, `experiments/`,
retained PR history; `sysand-lock.toml` upstream digests.

### Generator updates / regenerated artifacts

- `tools/configure_variant.py`: no code change; regenerated product model.
- `scripts/generate_view_index.py`: presentation-note keys updated to new view
  identities; `VIEWS.md` regenerated for aebs, middleware, product-models.
- `scripts/render_grid_csv.py`: grid metadata keys updated.
- `.github/workflows/privileged-syside-validation.yml`: 3 materialization
  checks + path expectations updated to new view names.
- 23 stale-named SVGs deleted (22 middleware + 1 aebs functional) — new-name
  SVGs must be produced by the privileged SysIDE run and byte-swapped
  (procedure in de4sdv-increment-chain-governance skill); `VIEWS.md` marks
  them "Diagram not present … regenerate via the Privileged Syside Validation
  workflow".

### Residual audit outcome

Generic sweeps (case-insensitive, all file types, untruncated):
`mw_<file>`, `mw-<kebab>`, `DE4SDV_MW*`, `MWAutoware*`, camel tokens starting
with `mw` followed by an uppercase letter or digit,
tokens, `aebs_functional_behavior`, `test_mw_*`, `diagram-mw*` — zero
unexplained residuals outside `docs/naming/` (where old names appear only as
manifest documentation). Remaining `mw`-shaped tokens are registered legacy
identities enumerated above. Expected CI-diagram state after this commit:
`check_svg_view_materialization`/byte-exact gates fail for the 23 renamed
views until the privileged-run byte-swap lands — this is the one planned
repair cycle, pre-declared here.

### Validation results (local)

- `python scripts/check_repo.py` — pass (includes new naming checks +
  ontology-kernel sync + scenario manifest checks).
- `python scripts/smoke_test.py` — pass.
- `python -m pytest tests/ -q` (excluding live-API) — 740 passed,
  137 subtests passed, 10 failed: 7 verified pre-existing on pristine
  `origin/main` (010-chain guard trio incl. the `de4sdv_aebs_010_bridge`
  deferred-artifact guard, SAF aspect classification, framework parity
  009D evidence file, middleware campaign connection-count doc drift,
  sysand pin assertion), 1 environmental (missing gitignored `.sysand`
  package cache in this worktree), 1 documented pending state
  (`test_all_published_diagrams_match_current_view_sets` — the 23 renamed
  diagrams above). No new failures beyond the declared pending state.
- `python scripts/check_naming.py` — pass with the 7 batch-2 advisories.
- Local SysML validation: syside binary is x86_64-only and this host is
  arm64 without qemu-user; per AGENTS.md feedback-loop rule 3, maintainer-run
  privileged Syside validation is requested at review (documented in PR).

### Unresolved / deferred decisions

1. Batch 2 (M11/M12) — scheduled after PR #177 merges; manifest entries are
   execution-ready.
2. Needs/requirements split for AEBS (separate enduring concerns) — recorded
   as a recommendation; it is a model-architecture change, not a rename.
3. Legacy nested `package Features { … }` shape in 10 slices — tolerated,
   flattening queued as an optional low-priority follow-up (must ride the
   privileged-validation cycle).
4. AEBS needs/requirements split (mirror of middleware's
   `stakeholder_needs`/`requirements` pair) — **model-architecture change**,
   explicitly out of naming-migration scope; recorded as the recommended
   follow-up increment work, not silently reshaped here.
5. 009-series scenario verification files (bicycle/pedestrian/degraded/…)
   keep generic filenames with 009-specific packages — assessed as option B
   (explicit increment/evidence records, kept as stable semantic modules per
   conventions §7); renaming would churn 8+ tracked consumers for zero
   semantic gain. Documented, not migrated.
6. Bench runtime identities (`de4sdv_aebs_010_bridge` ROS package,
   `board_sepolicy_aebs010.mk`, `evidence/010/`, branch names
   `feat/aebs010-*` in the increment record) — identity-bearing/retained,
   never renamed (conventions §10 upstream/external exception).
4. AGENTS.md pointer to the conventions doc — approval-gated edit, left for
   the maintainer (one line under "Documentation style").


---

## Batch 2 execution record (post-implementation)

Executed on `chore/repo-naming-identity-migration` (this PR), head before the
documentation commit. Scope: M11 (7 files), M12 (canonical-file subset), plus
the policy refinement that retired the `E-`/`N-` grammars behind deterministic
grandfathering.

### Old → new canonical name map (implemented)

- 7 SysML slices renamed `aebs_010_visualization_<concern>.sysml →
  aebs_visualization_<concern>.sysml`; the physical slice further aligned to
  the method vocabulary: `…_physical_realization.sysml →
  aebs_visualization_physical_software_realization.sysml`.
- Packages `DE4SDV_AEBS010Visualization<Concern> →
  DE4SDV_AEBSVisualization<Concern>`; physical package →
  `DE4SDV_AEBSVisualizationPhysicalSoftwareRealization`.
- Reusable usage names de-numbered: `Aebs010VisualizationFunctionalFlow →
  AebsVisualizationFunctionalFlow`, `AEBS010VisualizationPhysicalSystem →
  AEBSVisualizationPhysicalSystem`, `req010<Name> → req<Name>` (14),
  derivation dependencies `s2NNNDerivedFromN0NN →
  s2NNNDerivedFrom<NeedSemanticStem>` (15, target-need semantics verified
  against each requirement's doc/source), increment-frame dependencies
  `framingToNeeds010/successorMandate010/framingToProblemStatement010/
  scopeToTraceabilityShell010 → <stem>` (4), assumptions/gaps
  `asm010*/gap010* → asm*/gap*` (8).
- 14 view identities `aebs010<Name>View → aebsVisualization<Name>View`.
- 4 test modules renamed `test_aebs_010_visualization_*.py →
  test_aebs_visualization_*.py` (+ `test_aebs_010_hmi_presentation_contract.py
  → test_aebs_visualization_hmi_presentation_contract.py`).
- M12: `AEBReadinessInputs009A → AEBReadinessInputs`,
  `PlannedAEBScenarioHarness009B009C → PlannedAEBScenarioHarness`,
  `PlannedAEBScenarioAssets009B009C → PlannedAEBScenarioAssets` (defs in
  `aebs_simulation_deployment.sysml` + executable-bench test expectations);
  origin increments now documented in doc comments at the def sites.
- Policy: `E-`/`N-` retired grammars → deterministic grandfathering
  (`_GRANDFATHERED_IDENTITIES` closed sets); `NEED` registered canonical;
  registry doc gains the four-way classification (CANONICAL / EXTERNAL /
  GRANDFATHERED / RETIRED→MIGRATE) and §5.1 closed-set documentation.

### Preserved identity-bearing records (verified unchanged)

`INC-AEBS-010` (parts `incAEBS010*`, increment-frame semantics),
`INC-AEBS-010` pilot YAMLs and their increment-scoped filenames/schemas,
`de4sdv_aebs_010_bridge` ROS package and its Android.bp/launch/evidence
bindings, `board_sepolicy_aebs010.mk`, `evidence/010/` trees,
`feat/aebs010-*` branch names in the increment record, `DE4SDV_
Middleware010VerificationEvidence` (Phase 12 record) and its `successor
IncrementDecision010` element, all `REQ-AEBS-S2-*`/`SC-AEBS-010-*`/
`ASM-AEBS-010-*`/`GAP-AEBS-010-*`/`CLS-AEBS-010-001` IDs, all grandfathered
`E-MW-*`/`N-*` identities, `MW-CONFIG-001`, `AEBS-CONFIG-010-001`.

### Connected artifacts updated

`.meta.json` (7 keys + 1 alias entry), `sysand-lock.toml` (9 lines),
`scripts/generate_view_index.py` (5 presentation keys),
`.github/workflows/privileged-syside-validation.yml` (3 expected-diagram
names), 3 pilot YAMLs (paths, deferred-list reconciliation:
`created_by_implementation_slice` now records the five materialized
entries), 4 renamed test modules + `test_check_naming.py` (batch-2 advisory
removed; closed-set grandfathering tests added), `VIEWS.md` regenerated
(aebs; others verified byte-stable), bench README/VISUALIZATION-CONTRACT/
config/proto references updated where they named model files (runtime
identities untouched).

### Regenerated artifacts / diagram state

13 `aebs010*` SVGs + 2 SVGs carrying M12 labels deleted (`git rm`); the
privileged SysIDE run must regenerate and byte-swap the renamed views —
`VIEWS.md` marks each as "Diagram not present … regenerate via the Privileged
Syside Validation workflow". Expected CI state: committed-diagram gates fail
for exactly these until the byte-swap lands (one pre-declared repair cycle,
same as batch 1).

### Validation results (local, this batch)

- `python scripts/check_naming.py` — pass (no advisories; batch-2 pending
  list removed with execution).
- `python scripts/check_repo.py` — pass (includes naming, ontology-kernel
  sync, scenario-manifest checks).
- `python scripts/smoke_test.py` — pass.
- `pytest` visualization + naming + executable-bench suites — green except
  the two documented pre-existing framing failures (host-browser wording,
  S2-012/013/014 index), verified failing identically on the pre-migration
  tree.
