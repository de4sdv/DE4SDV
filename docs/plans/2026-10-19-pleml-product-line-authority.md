# PLEML product-line authority: migration plan

**Status:** plan for [ADR 0022](../architecture-decisions/0022-adopt-pleml-as-product-line-authority.md).
Nothing in this plan is evidence, qualification or a compliance claim.
**Decision owner:** Orkun Yilmaz. **Date:** 2026-10-19. **Base:** `b3054100`;
line references are at that commit.

## Owner decisions (2026-10-19)

| ID | Decision |
|---|---|
| D1 | No adapter helper pattern (helper features with implies) in the product-line model now |
| D2 | Requires and implies are evaluated by a DE4SDV module in this repository, built with its first consumer, which is now this migration |
| D3 | PLEML becomes the product-line authority (adoption option C) |
| O1 | Migrate the **full** catalogue, including the reference-only options and every bill of features |
| O2 | Provision PLEML through Sysand at `=1.1.1`, with a CI byte check against the release tag |
| O3 | INC-MW-011 phase 9 waits for the switch. The rollback window runs until phase 9 starts or for 30 days, and a rollback tag marks the last YAML-authority commit |
| O4 | Releases with unchanged content take a fast path. No new frozen-experiment commits |
| O5 | Inform the PLEML maintainers after the switch, with text the owner approves |

## Starting point

- **PLE-Q.** Run `39167884450` on `f967a519` with PLEML 1.1.0. Two cases are observed (`feature-binding`, `group-shapes`). Four are gaps: `xor-counterexample`, `binding-time`, `serializer-identity` and `adapter-realization`.
- **PLE-S.** Run `39169049300` produced the retained record. Its 15 cases have no defect, and both planned members derive the configurator's assets. See [ple-s-scope-alignment.md](../product-line-engineering/ple-s-scope-alignment.md).
- **Toolchain.** SysIDE 0.10.3 does not evaluate PLEML constraint bodies. PLEML defines no derivation: a feature configuration is either valid or invalid.
- **PLEML 1.1.1** (released 2026-10-19). Its library is the same as 1.1.0 apart from its version line. Its Sysand package is byte-identical to the release tag. The 1.1.0 package had CRLF line endings.

## 1. Target state

| Element | Today | Target |
|---|---|---|
| **Feature models** | Three YAML catalogues: SDV product line, engineering execution environments, vehicle-target execution environments ([README](../../model-based-product-line-engineering/README.md) :40-49) | Three PLEML feature models under `model-based-product-line-engineering/feature-models/`, each restating its catalogue node for node. The families stay separate. |
| **Configurations** | 8 YAML bills of features, including two reference-only examples and one invalid fixture | 8 PLEML feature configurations. The invalid fixture becomes a fixture configuration outside the authority roots. |
| **Evaluation** | `tools/configure_variant.py` | A DE4SDV module (D2) reading serializer and API objects only (ADR 0011). It covers multiplicities, requires, XOR and implies, completeness, Development binding time and feature-only ownership. It fails closed. It never reports native execution. |
| **Derivation** | `derived_asset_selections` (`sdv_product_line.yaml:34-60`; `tools/configure_variant.py:1039-1073`) | Feature bindings, plus the 8 adapter rules as model-native DE4SDV derivation rules (§3), evaluated by the same module |
| **Receipt** | None | A licensed job serializes and evaluates each model, then writes a content-addressed evaluation receipt that is committed beside the model. It records input digests, not commit SHAs. |
| **Configurator** | Reads YAML | Retargeted, not retired. It reads the receipts and keeps its projection writer and SysML mapping checks. After S7 it reads receipts only. |
| **Product models** | 7 projections, byte-reproducible (`tests/test_configure_variant.py:377-418`; `tests/test_execution_environment_ple.py:91-131`) | Same bodies and part-def names. Two model slices type parts by one of these names (`middleware_variability_configuration.sysml:35`; `aebs_visualization_variability_configuration.sysml:175-181`). Only the provenance header changes. |
| **Comparison oracle** | Retained scope comparison | The S4 parity check, then the rollback guard. Removed at S7. |
| **PLE-S** | Fenced experiment of the admitted scope | Retired at S3a, superseded by the full-catalogue model. Its record stays as history. |
| **PLE-Q** | Frozen experiments | The frozen experiments and tags stay as history. The `adapter-realization` gap is answered by the authority's derivation-rule round trip (S3a). |
| **Governed scope** | Portfolio authority (ADR 0014) | Unchanged. It stays the **admission** authority, while PLEML becomes the **configuration-validity** authority. Admission follows from model-native correspondences of each feature to the governed scope, which replace `catalogue-correspondence.yaml`. |
| **Kernel** | The texts name the YAML as authority (`de4sdv_product_line.sysml:86-125`; `de4sdv_method_concerns_and_viewpoints.sysml:150-174`) | Two method PRs: S2k adds the rule and configuration-metadata definitions, and S6k points the texts at ADR 0022 |

## 2. Catalogue mapping

| YAML construct | PLEML authority |
|---|---|
| `alternative` group | A `[1]` parent with `[0..1]` sub-features. Exclusivity comes from multiplicity. |
| `or_group` | A `[1..*]` parent with `[0..1]` sub-features |
| `optional` / `mandatory` | `[0..1]` / `[1]`. A mandatory feature is selected by inheritance, which is the implied-leaf rule. Setting it to `false` is invalid. |
| `requires` / `excludes` (C001–C006) | C001 and C003 become exclusions of Android. C004 and C005 become exclusions of QNX. C006 becomes a requires. C002 is vacuous, since every OS option satisfies it, so it is recorded and dropped. |
| `maps_to` / `maps_to_variant` | One feature binding per variant, with the asset as client and the feature as supplier |
| `derived_asset_selections` | DE4SDV derivation rules (§3) |
| `id` (`F-`, `C-`, `D-`, `PL-`) | Kept as SysML short names, so nothing is renamed ([naming-conventions.md](../naming/naming-conventions.md) :296-299, :317-323) |
| `binding_time` | `design` maps to Development. PLEML has no equivalent for `unassigned`, so a DE4SDV annotation carries it. No verdict depends on it: the configurator only checks the value set (`tools/configure_variant.py:734, :792-798`). |
| Bill of features: `name`, `description`, `evidence` | DE4SDV configuration metadata (S2k): the projection part-def name and the evidence status and artifacts, under the same status-to-artifact rule. `description` goes in the configuration's `doc`. |

## 3. The closed world

The full catalogue varies both the application and the middleware. Today the configurator rejects:

- every application–middleware pair without a rule (`sdv_product_line.yaml:34-37`);
- an adapter selected by hand ("Unknown feature path").

The authority keeps both rejections through **two mechanisms and a check that ties them together**.

1. **Derivation rules own the adapters.** The 8 rules become model-native DE4SDV derivation rules: required features in conjunction, then the resulting variant, with `none` for no adapter. They are typed by a kernel definition (S2k) and grouped under `D-ASSET-APPLICATION-MIDDLEWARE-ADAPTER`. For every valid configuration the module requires **exactly one** matching rule per derived variation. With no match it rejects ("no rule"); with several it rejects ("ambiguous"). These are today's verdicts (`tools/configure_variant.py:1057-1066`). The rules live in the model, not in code, so no semantic authority hides in Python.
2. **Exclusions make invalid pairs visible.** Two PLEML XOR constraints exclude the four unsupported pairs: Openpilot and Apollo each exclude Android SDV and AUTOSAR Adaptive. Without them, a reader of the feature model alone would see those pairs as valid, as YAML readers do today.
3. **An agreement check, static and run in CI.** The application–middleware pairs that the constraints allow must equal the pairs the rules cover: 12 pairs, of which 4 are excluded and 8 have rules. Any drift between the two mechanisms fails.

**Hand-picked adapters stay impossible.**

- No feature exists for the adapter variation; its variants appear only as rule results.
- A feature configuration owns only features.
- The module refuses any binding or configuration entry that targets a variant of a derived variation.

So ADR 0014:91-92 holds.

**How this fits D1.** No helper features and no implies. The implies pattern is not needed, because the derivation rules own the adapters. Implies stays available for future product constraints.

**Parity of reasons.** YAML's "no rule matching" corresponds to the PLEML pair exclusion, and the "Unknown feature path" for an adapter corresponds to the "derived variant cannot be selected" refusal. Constraints keep their IDs.

## 4. Migration steps and gates

**The parity gate.** From S4 on, parity is checked on every PR that touches an input, over:

- every file in `model-based-product-line-engineering/feature-configurations/`: 7 bills of features and the invalid fixture;
- the 10 existing probes;
- 5 closed-world probes: the four unsupported pairs and one hand-picked adapter.

**What counts as parity.** Each row compares:

- the verdict;
- the reason class;
- the derived variants;
- the projection body, byte for byte.

The classes are `equal` and `both-reject`; anything else is a `defect`. The expected histogram is 14 `equal`, 9 `both-reject` and 0 `defect`, which S4 confirms. Before S4, the retained scope comparison must stay at 1/9/1/1/3/0.

**The authority switches only at S6.**

| Step | Content | Gate | Size |
|---|---|---|---|
| S0 | ADR 0022 and this plan; docs only | Owner merge | 3 files, ~600 lines |
| S1 | PLEML `=1.1.1` through Sysand (ADR 0007 pattern). Byte check of the installed library against the tag. Pinned `sysand` in `privileged-ple-qualification.yml:160` and `privileged-full-model-api-ingestion.yml:96`. | Licensed validation; Method Check diff shows library elements only | ~6 files, ~150 lines |
| S2 | Evaluator and derivation module. Conformance cases restated from the upstream test verdicts, not vendored. The 8 rules and 4 pairs as unit cases. | Unit tests | ~6 files, ~1,600 lines |
| S2k | Method PR: kernel definitions for derivation rules and configuration metadata, classified per `AGENTS.md`. They must respect decision 4 on evidence status. | `check_repo` projections; Method Check | ~4 files, ~200 lines |
| S3a | SDV feature model: features, constraints, pair exclusions, bindings, the 8 rules and the scope correspondences. Its 4 configurations, plus the fixture configuration. Model selectors updated (`de4sdv/sysml_api/baseline.py:13-25`, `scripts/validate_sysml.py:11-15`, `scripts/check_repo.py:51-55`, `deployment/ask_viewer/entrypoint.py:15-22`, workflow filters). First receipt. PLE-S retired. | Licensed validation; agreement check; API round trip (identity kept, verdicts equal on readback) | ~20 files, ~2,200 lines |
| S3b | Engineering and vehicle-target feature models, with their 3 configurations | Licensed validation; receipts | ~8 files, ~500 lines |
| S4 | Parity check, as defined above | 0 `defect`; histogram as expected | ~8 files, ~900 lines |
| S5 | Configurator retarget for all three families | All 7 projection bodies byte-equal on both paths | ~6 files, ~700 lines |
| S6k | Method PR: kernel texts name "the authority of ADR 0022", which is true before and after S6 | `check_repo`; Method Check | ~3 files, ~120 lines |
| S6 | **Switch.** ADR effective. README flipped. Projections regenerated from the receipts. YAML labelled as shadow. Clerical notes on ADR 0014 and ADR 0006. Rollback tag set first. | Full parity at the head; licensed validation; PLE-Q dispatch on the merge commit; owner merge | ~20 files, ~700 lines |
| S7 | **Retire YAML,** only after full parity held through the window. The three catalogues, the 8 YAML bills of features and the configurator's YAML layer are removed; their tests move to receipts. The reference-only examples stay, migrated. Naming registry note updated the same day. | Window ended; owner yes | ~30 files, about −4,000 lines |

S1 and S2 run in parallel. S3b can run in parallel with S4.

## 5. Provisioning (O2)

PLEML is consumed through Sysand at `=1.1.1`, like SYSMOD (ADR 0007):

- exact constraint;
- committed lock;
- `.sysand/` untracked;
- the library added to `PINNED_DEPENDENCIES`.

A CI step asserts that the installed `PLEML.sysml` is byte-identical to the release tag's file. That makes the package and the tag provably the same text.

The frozen experiments keep reading their pinned submodules as history.

## 6. Rollback (O3)

**From S6 to S7,** the YAML inputs and the YAML path stay runnable in shadow and parity-checked.

- Rollback is one revert of S6. Because parity holds, the projections regenerate byte-equal.
- There is no runtime toggle, so only one authority exists at a time.

**The window** runs from S6 until phase 9 starts or for 30 days, whichever comes first. S7 is phase 9's first PR.

**After S7,** rollback means restoring from the rollback tag and re-expressing later changes in YAML.

## 7. Upstream release policy (O4)

**Pinning and assessment.**

- Exact pin, no ranges, no automatic update.
- Each release is assessed within 14 days from the library diff and the changelog.

**Fast path.** A release with unchanged content, changing only the version line or line endings, gets one re-pin PR. It carries the byte diff, licensed validation and refreshed receipts.

**Full path.** A semantic change gets a re-pin PR that adapts the models and the module. It then needs licensed validation, receipts, parity until S7, re-qualification at the exact revision and an independent review.

**No new frozen-experiment commits.** The authority at an exact revision is the thing qualified.

**Each of these blocks an upgrade:**

- a parity or receipt regression;
- a constraint form the models have not been adapted to;
- an unreviewed change to the configuration or constraint definitions;
- a package that differs from its tag;
- a licence change;
- an incompatibility with the pinned SysIDE;
- an open upstream issue that touches a concept we consume.

## 8. INC-MW-011 phase 9 (O3)

**Phase 9 waits for S6 and starts with S7.** It then delivers:

- the scope-revision ADR that admits "Autoware on S-CORE with an AAOS HMI guest";
- the per-domain platform restructuring (GAP-MW-032, `middleware_score_framing.sysml:300-318`), done once, in PLEML;
- the member configuration, which evolves from the migrated S-CORE example.

**What runs in parallel:** the draft of the scope ADR. Phase 8 merged as #389.

## 9. Risks and mitigations

| Risk | Fact | Mitigation |
|---|---|---|
| **Upstream maturity** | Three releases in three days (2026-10-17 to 10-19). 1.1.0 changed the constraint form about 17 hours after 1.0.0. One active contributor. | Exact pin; §7 gates; constraint usages confined to the feature-model files; shape checks that fail closed; rollback tag |
| **No native evaluation** | SysIDE 0.10.3 failed every attempt on PLEML constraints (scratch run `39117522806`) | DE4SDV module with conformance cases; re-probe at each SysIDE upgrade; never claim native execution |
| **Serializer identity** | 11 PLE-Q rows have no concept check (`tests/test_ple_qualification.py:372-376`) | The S3a round-trip gate covers the concepts the authority consumes; the rest stay recorded gaps |
| **Licensed CI** | Five workflows use the licence, and model changes need serialization | Committed receipts keep other PRs unlicensed; the job joins the existing licensed validation; path filters |
| **Scope growth** | The full catalogue makes reference-only options configurable in the authority, as YAML does today. It supersedes ADR 0014:143-144. | Admission stays with the governed scope through the correspondences, and validity and admission are reported separately |
| **Kernel dependency** | The derivation rules need a kernel home | S2k runs early, as its own method PR |

## 10. Upstream contact (O5)

After S6, one comment on MBSE4U/PLEML#4 (the repository has no discussions). Draft, for owner approval:

> A short update for your information: DE4SDV now uses PLEML 1.1.1, pinned
> through Sysand, as the authority for its product-line feature models and
> configurations. We take new releases by re-pinning and re-running our
> checks. Thanks for the quick 1.1.1 release.

## 11. Effort

| Measure | Estimate |
|---|---|
| PRs | 11 (S0, S1, S2, S2k, S3a, S3b, S4, S5, S6k, S6, S7), of which 2 are method PRs |
| Size | About 7,000 lines added before S7; S7 removes about 4,000 |
| Licensed runs | About 18–22 |
| Calendar | About 12–16 working days to S6 at the observed PLE pace of about a day per PR including review |
