# DE4SDV Naming QA Report — Repository-Wide Audit (Pre-Migration)

Scope: full repository sweep at `origin/main` `8bb7f79` (worktree
`chore/repo-naming-identity-migration`). Sources swept case-insensitively:
all `.sysml`, `.yaml`, `.yml`, `.json`, `.py`, `.md`, `.sh`, workflow YAML,
implementation benches, evidence records, `.meta.json`, excluding `.git/`,
`.sysand/lib/` (upstream), and `tests/fixtures/` (deliberate fixtures).

Companion documents: [`naming-conventions.md`](naming-conventions.md) (the
convention this audit implements), [`migration-manifest.md`](migration-manifest.md)
(full old→new mapping, impact sets, risks).

## 1. Identifier families found

Complete set (no other `XXX-…` family exists anywhere in project-owned
sources — swept with a bounded all-caps-hyphen token regex over all file types,
then classified):

| Family | Form | Count (occurrences) | Where | Classification | Disposition |
|---|---|---|---|---|---|
| Engineering increments | `INC-AEBS-001…010`, `INC-AEBS-009A…009I`, `INC-MW-001…010` | 310 AEBS + 173 MW | pilots YAML, SysML doc blocks, tests, implementation configs | Genuine historical increment identities | **Keep** — registered in §5 of the convention; never renumbered |
| Stakeholder needs | `N-AEBS-001…014`, `N-MW-001…009` | 185 + 42 | `aebs_needs_requirements.sysml`, `middleware_stakeholder_needs.sysml`, pilots, view index | Canonical, readable | **Keep** |
| Requirements | `REQ-AEBS-001…014`, `REQ-MW-001…009`, `REQ-AEBS-S2-001…010` | 169 + 85 + ~60 | needs/requirements slices, pilots, guard tests | Canonical, readable (S2 = System 2 series) | **Keep** |
| Acceptance criteria | `AC-MW-001…010-NN`, `AC-AEBS-PHY-*` | 42 + per-phase series | `middleware_verification_evidence.sysml`, pilot YAML, `test_aebs_010_visualization_*` | Canonical | **Keep** |
| Evidence (legacy spelling) | `E-MW-008…014` | 60 | `middleware_verification_evidence.sysml`, `e-mw-*.yaml` evidence files, baseline register, tests | Readable? No — ambiguous prefix; **externally stable** (retained evidence filenames, baseline register, merged PRs) | **Keep as legacy spelling**, registered; new evidence IDs use `EVID` |
| Evidence (new spelling) | `EVID-AEBS-001` | 4 | `inc-aebs-009a-jetson.yaml` configuration | Canonical | **Keep** |
| Gaps | `GAP-MW-001…022`, `GAP-AEBS-001…003` | 93 + 16 | verification slices, pilots | Canonical | **Keep** |
| Baselines | `BL-MW-001…010` | 4 | `middleware_verification_evidence.sysml`, `configuration-management/baseline-register.md`, pilot, test | Canonical | **Keep** |
| Verification cases | `VC-MW-010-01…NN` | 18 | verification slice + pilot | Canonical | **Keep** |
| Validation scenarios | `SC-AEBS-010-01…NN` | 12 | 010 operational context + pilot | Canonical | **Keep** |
| Bench scenario IDs | `SCN-AEBS-009D-STALE` etc. | evidence JSON | retained runtime evidence | Bench tooling identity | **Keep** (bench tooling namespace) |
| Source anchors | `SRC-UNECE-R152` | 12 | regulatory slices, criteria script | Canonical | **Keep** |
| Preflight checks | `PF-002…004` | evidence PNGs/status | 010 bench evidence | Bench tooling identity | **Keep** |
| Middleware counterexample | `middlewareVerificationAssuranceView`, `MW-010` bare tokens in view/prose | view identities | `middleware_verification_evidence.sysml` VIEWS | **Lifecycle number inside a semantic view name** — the exception case | **Migrate** (see manifest): `middlewareVerificationAssuranceView → middlewareVerificationAssuranceView` etc. |
| Sorted-pilot YAML anchor IDs | none — corrected during audit: each pilot file *is* one increment record (`id: INC-MW-007`); no `MW-00N:` slice keys exist. Early counts were tails of registered IDs (`INC-MW-001`, `E-MW-011`) | — | — | **No action** |

No `CR-*`, `VS-*`, `VW-*`, `REQS-*`, or other families exist. The registry in
the conventions doc covers exactly these.

## 2. Abbreviations found

### Domain acronyms (keep, registered)
`AEBS`, `ADAS`, `SDV`, `AAOS`, `ROS2` (identifier syntax), `AUTOSAR`, `ECU`,
`VSS`, `FMI`, `FMU`, `SSP`, `HIL`, `SIL`, `MIL`, `UNECE`, `V&V` (prose),
`MBSE`, `ASELCM`, `SAF`, `SYSMOD`, `VSIDL`, `SBOM`, `GCP`, `SKU`, `RAM`,
`OSS`, `MIT`, `API`, `MCP`, `CI`.

### Project-local shorthand (migrate where canonical, preserve where registered/evidence-bound)

| Shorthand | Occurrences | Classification | Disposition |
|---|---|---|---|
| `mw`/`MW` in filenames, packages, types, view names, pilot files, tests, docs | 10 SysML files, 10 pilot YAMLs, 1 product model + config, ~14 tests, 5 docs | Canonical semantic names using project-local shorthand | **Migrate** to `middleware*`/`Middleware*` per manifest |
| `MW`/`AEBS` inside trace IDs | registered namespaces | Registered subject codes | **Keep** (registry documents `MW = Middleware`) |
| `mw` inside evidence filenames (`e-mw-011-…yaml`, `mw-010-google-cloud-…yaml`) | retained evidence | Evidence-ID-bound historical records | **Keep** (legacy spelling; convention documents the alias) |
| `pf`/`PF` | bench preflight | Tooling namespace | Keep |
| `inc`/`INC` in usage names (`incMW002`, `incAEBS010`) | SysML usages of increment records | Identity-bearing usages | Keep |

No `reqs`, `cfg`, `viz`, `arch`, `ver` shorthand exists in canonical names —
the policy is now defined so it stays that way.

## 3. Increment/phase terminology conflation

Swept every doc/script/test for "12-phase", "phase = increment", and
phase-numbered filenames:

- The repository's authoritative workflow (13 phases, 0–12) is already
  correctly documented in `methodologies/sysmod-sysmlv2/increment-workflow.md`,
  `process-mapping.md`, the ontology (`MethodPhase`), and glossary. A guard
  test (`test_sysmod_sysand_integration.py`) already pins "13-phase" vs
  "12-phase".
- **Residual conflation found:** `docs/plans/2026-07-29-middleware-integration-chain.md`
  line 3 says "Aligned to DE4SDV increment-workflow.md (13 phases)" while
  using "phase 3 increment", "Phase 2 increment"-style labels for what are
  per-subject increment slices — corrected wording applied.
- **Structural conflation (the substantive one):** filenames like
  `aebs_010_visualization_framing.sysml` and `middleware_increment_framing.sysml`
  encode increment number as filesystem structure. Full disposition per file
  in the manifest.
- Old "12-phase" labels: none found outside the guard test's negative
  assertion (correct).

## 4. Package-shape audit

- 10 files use the legacy nested shape
  `package DE4SDV_X { package Features { package AEBS { … } } }`
  (4 AEBS: framing, operational context, needs/requirements, functional
  behavior; 6 middleware: framing, classification, context, needs,
  requirements, functional architecture).
- 24 files use the canonical flat unique global package.
- Disposition: document flat as canonical; tolerate legacy inner nesting
  (no semantic benefit justifies mass edits of 10 files that must re-pass
  privileged validation; flattening is a queued follow-up in the manifest,
  not silently done here).

## 5. Externally/historically stable names (must NOT change)

1. All `INC-*`, `REQ-*`, `N-*`, `AC-*`, `E-*`, `GAP-*`, `BL-*`, `VC-*`,
   `SC-*`, `SCN-*`, `SRC-*`, `PF-*` identifiers (registered namespaces;
   evidence-bound and PR-history-bound).
2. Retained-evidence filenames under `implementation/*/evidence/` including
   `e-mw-*.yaml`, `mw-010-google-cloud-vsidlc-cuttlefish.yaml`, evidence dirs
   `009d/`, `010/`, PNG/MP4/SHA256SUMS names, bench launch/package names
   (`de4sdv_aebs_009b_bench`, `de4sdv_aebs_010_bridge` — ROS 2 python package
   names deployed in campaigns), `aebs-009b.param.yaml`, `contract-009*.yaml`,
   `scenario-009*.yaml` (bench config identities referenced by retained
   evidence).
3. `.sysand/lib/**` (upstream Sysand libraries), `tests/fixtures/**`
   (deliberate synthetic fixtures), `experiments/**` (historical spike).
4. External identifiers: ROS 2 topics/services, Autoware package names, AAOS
   APIs, VSS paths, UNECE references.
5. ADR titles/filenames and merged-PR text (history).
6. `.meta.json` keys (viewer index keys keyed by product-model package names
   — migrated only together with the package rename they key, per manifest).
7. `EVID-AEBS-001` (already canonical, in a committed configuration).

## 6. Violations of the new convention (feed the manifest)

1. `mw_*` filenames/packages/types/view names → `middleware*` (10 slices +
   product model + pilot YAMLs + tests + docs + one workflow path).
2. `aebs_010_visualization_*` filenames/packages/types/view names carrying
   the increment number as filesystem structure → semantic names with
   provenance (manifest; **sequenced after PR #177 merges** — see manifest
   §Sequencing).
3. `aebs_functional_architecture.sysml` → `aebs_functional_architecture.sysml`
   (align with method vocabulary; package `DE4SDV_AEBSFunctionalArchitecture →
   DE4SDV_AEBSFunctionalArchitecture`).
4. Numbered reusable definitions inside evidence slices
   (`EvidenceOutcome009H`, `ScenarioIdentity009F/D/E/I`, `BicycleTargetBench009H`,
   `AEBReadinessInputs009A`, `PlannedAEBScenarioHarness009B009C`) → semantic
   names; increment stays in doc/provenance (manifest; sequenced after #177).
5. `aebs_evidence.sysml` is named generically but contains
   `DE4SDV_AEBS009BNominalEvidence` (INC-AEBS-009B record) — resolved to the
   explicit evidence-record name (manifest).
6. Pilot YAML naming mixed conventions (`aebs-010-visualization*.yaml` vs
   `aebs-needs-requirements.yaml` vs `mw-*.yaml`) → one kebab-case scheme per
   subject (manifest).
7. Status words in configuration filenames (`apple-silicon-macos-candidate`,
   `invalid-score-android`, `example-linux-score-autoware`) — assessed:
   `fixtures/invalid-score-android.yaml` is a deliberately-invalid test fixture, move
   to fixtures; `candidate`/`example` names are real configuration classes
   documented in the PLE README — kept with rationale (manifest).
8. Diagram SVGs keyed by old view names regenerate from generator (manifest).
