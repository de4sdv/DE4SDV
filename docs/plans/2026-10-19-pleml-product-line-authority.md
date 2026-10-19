# PLEML product-line authority: migration plan

**Status:** plan for [ADR 0022](../architecture-decisions/0022-adopt-pleml-as-product-line-authority.md).
Nothing in it is evidence, qualification or a compliance claim.
**Decision owner:** Orkun Yilmaz. **Date:** 2026-10-19. **Base:** `910b196b`;
line references are at that commit.

## Owner decisions (2026-10-19)

| ID | Decision |
|---|---|
| D1 | No adapter helper pattern (helper features with implies) in the product-line model now |
| D2 | Requires, implies and XOR are evaluated by a main-repo module built with its first consumer; no new frozen-experiment commit |
| D3 | PLEML becomes the product-line authority (adoption option C) |
| O1 | Migrate the full catalogue, including the reference-only options and every bill of features |
| OQ1 | The engineering and vehicle-target execution-environment catalogues and their three configurations migrate too |
| O2 | Sysand `=1.1.1`, with a CI byte check against the release tag |
| O3 | INC-MW-011 phase 9 waits for the switch; a rollback window and a rollback tag |
| O4 | Releases with unchanged content take a fast path; no more frozen-experiment commits |
| O5 | Inform the PLEML maintainers after the switch, with text the owner approves |
| OQ0 | The planned adapter follow-up on MBSE4U/PLEML#4 is held. The O5 note explains the derivation-rule approach instead. |
| OQ4 | Features distinguish member products, so common capabilities are not features (the owner's standing rule) |

**Defaults set by the coordinator.** The owner can veto any of these before merge.

- **OQ2** (refines O3): after the switch, the YAML stays as a non-authoritative shadow for 30 days. S7 requires all three of:
  - the 30 days have passed;
  - one full-parity run on main after S6 is green;
  - no rollback trigger is open.

  Phase 9 may start right after S6.
- **OQ3:** S2k creates no kernel evidence-status type. Configuration evidence status stays an external typed reference until the ontology review's `decision-4` (the EvidenceStatus split) is decided.
- **OQ5:** an ontology PR before S6 decides the post-switch classification of `FeatureConfiguration`, the four selection relations and `variesAt`. It needs the owner's yes and is part of S6's gate.
- **OQ6:** the ADR is `Accepted` on the S0 merge and takes effect at S6. At S6, ADR 0014 gets a marked partial-supersession note and stays `Accepted`.

## Starting point

- **PLE-Q.** Run `39167884450` on PLEML 1.1.0 recorded 2 cases observed and 4 gaps. Native constraint evaluation was not executed.
- **PLE-S.** Run `39169049300` has 15 cases and no defect. See [ple-s-scope-alignment.md](../product-line-engineering/ple-s-scope-alignment.md).
- **PLEML itself.** It defines no derivation: a feature configuration is either valid or invalid.
- **PLEML 1.1.1.** Its library equals 1.1.0 apart from the version line. Its Sysand package is byte-identical to the release tag; the 1.1.0 package had CRLF line endings.

## 1. Target state

| Element | Target |
|---|---|
| **Feature models** | Three PLEML feature models under `model-based-product-line-engineering/feature-models/`, one per family: the SDV product line with its reference-only options, engineering execution environments, and vehicle-target execution environments. Variability only: `C-` common capabilities have no feature (§2). |
| **Configurations** | All 7 bills of features and the invalid fixture in `feature-configurations/` (its `README.md` excluded) become PLEML feature configurations. The fixture stays outside the authority roots. |
| **Evaluation** | A DE4SDV module reading serializer and API objects only (ADR 0011). Identity comes from validated bindings or serializer-recorded source documents, never names (`de4sdv/semantic/kernel_binding_index.py:1-20`). It checks: <ul><li>multiplicities;</li><li>requires and XOR, and implies once one is modelled;</li><li>completeness and Development binding time;</li><li>feature-only ownership;</li><li>binding integrity;</li><li>the static rule checks of §3;</li><li>admission (valid versus admitted).</li></ul> It fails closed and never reports native execution. |
| **Derivation** | Bindings, plus the 8 adapter rules as model-native DE4SDV derivation rules (§3) |
| **Receipts** | A licensed job serializes and evaluates each model. It commits the receipt (verdicts, derived variants, admission, input digests) together with the compressed serialized elements, as the Gate A baseline does with `.json.xz`. Unlicensed CI re-runs the evaluator on those elements and refuses stale receipts by digest. Receipt paths are in the licensed path filter. |
| **Configurator** | Retargeted. It reads receipts and keeps its writer. After S6, variation and variant identity come from the receipt, and the lexical mapping checks (`tools/configure_variant.py:1203-1315`) stay only for the YAML shadow. |
| **Product models** | 7 projections with unchanged part-def names, compared on the normalised body (§5). One slice types a part by `MiddlewareAutowareAAOSSDVReference` (`middleware_variability_configuration.sysml:35`); another aliases and exposes it (`aebs_visualization_variability_configuration.sysml:174-181`). |
| **Production surface** | Unchanged until S6. Until then the models are fenced, as PLE-S was, and licensed-validated with the reviewed roots and the pinned library (`ple-s-scope-alignment.md:367-378`). S6 changes the selectors and `PINNED_DEPENDENCIES`. |
| **Oracle** | Becomes the S4 parity check, then the rollback guard. Removed at S7. |
| **PLE-S** | Retired at S3a, superseded by the fenced full-catalogue model. Its record stays as history. |
| **PLE-Q** | The frozen experiments stay as history. The `adapter-realization` gap is answered by the S3a derivation-rule round trip. |
| **Governed scope** | Stays the admission authority. Admission follows from model-native correspondences, which replace `catalogue-correspondence.yaml`. |

## 2. Catalogue mapping

| YAML | PLEML authority |
|---|---|
| `alternative` / `or_group` / `optional` | A `[1]` parent with `[0..1]` sub-features / a `[1..*]` parent / `[0..1]` |
| `C-` common capability nodes (`sdv_product_line.yaml:131-136, :162-174`) | No feature. Common content, with a correspondence to the governed common elements. Pedestrian and bicycle detection move under Capabilities. |
| Mandatory `F-` grouping nodes (`F-PLATFORM-STACK`, `F-SENSING`, `F-CAPABILITIES`) | Documented `[1]` grouping features that hold the variation points |
| C001, C003 (allowed lists "OS in […]") | XOR exclusions of the complement. The allowed list stays as the reviewed source in the model rationale, and a CI check fails when the complement drifts, for example when an OS option is added. |
| C004, C005 | XOR exclusions |
| C002, C006 | Dropped. In all 864 structurally valid selections neither ever fires: C002 allows every OS, and C006 targets common content. The rationale is a comment in the SDV feature model. |
| `maps_to` / `maps_to_variant` | One binding per variant, with the asset as client. Mapped variations and variants must stay at Development, as the configurator requires today (`tools/configure_variant.py:836-839, :857-860`). |
| `derived_asset_selections` | DE4SDV derivation rules (§3) |
| `F-`/`C-`/`D-`/`PL-` IDs | Kept as SysML short names. The registry note (`naming-conventions.md:317-323`) is updated at S3a. |
| `binding_time: unassigned` | No PLEML equivalent: a DE4SDV annotation (S2k). No verdict depends on it. |
| Bill-of-features `name`, `description`, `true`/`false` | Configuration metadata for the projection name (S2k); `doc`; `[1]`/`[0]` redefinitions. An omission stays an omission. |
| Bill-of-features `evidence` | An external typed reference (OQ3) with today's integrity rules (§4) |
| Catalogue `projection` block | Feature-model metadata for package, owner and label (S2k), carried in the receipt |

## 3. The closed world

The configurator rejects any pair without a rule (`sdv_product_line.yaml:34-37`) and any adapter chosen by hand. The authority keeps both rejections.

1. **Rules own the adapters.** The 8 rules become DE4SDV derivation rules: their premises in conjunction yield the resulting variant, which may be `none`. For each derived variation, exactly one rule must match a valid configuration. With no match the configuration is rejected as "no rule"; with several, as "ambiguous". Those are today's verdicts (`tools/configure_variant.py:1057-1066`). The rules live in the model, so no semantic authority hides in code.
2. **Exclusions state the unsupported pairs.** Two PLEML XOR constraints do it: Openpilot and Apollo each exclude Android SDV and AUTOSAR Adaptive.
3. **A total agreement check over all 12 pairs.** It requires:
   - exactly one rule for each of the 8 allowed pairs;
   - exactly one exclusion for each of the 4 unsupported pairs;
   - exactly one application premise and one middleware premise per rule.

   Until S7, the rule table is also compared row by row with `sdv_product_line.yaml:45-60`. This keeps today's static checks against duplicate conditions and wrong keys (`tools/configure_variant.py:985-1027`).
4. **Hand-picked adapters stay impossible.**
   - No adapter feature exists.
   - A configuration owns only features.
   - The module refuses a binding or entry that targets a derived variant.

   ADR 0014's "It is not a manual product choice" holds.

**D1:** no helper features and no implies. The pattern isn't needed because the rules own the adapters.

## 4. Where today's configurator checks go

| Today (`tools/configure_variant.py`) | After S7 |
|---|---|
| Document and bill-of-features shapes (`:167-272`) | Licensed model validation; receipt schema in the module |
| Name and description (`validate_bof_metadata`) | Configuration-metadata check in the module |
| Evidence status and artifact integrity: id grammar, duplicates, relative paths, no `.git`, no symlink escape, exists, Git-tracked (`:274-340`) | A CI check over the external evidence references, with the same rules |
| Structure: unknown paths, XOR choice, or-groups, mandatory groups (`:503-600`) | Multiplicities and completeness in the module; validation errors for unknown features |
| Mapping integrity: ids, binding times, every child mapped, one feature per variant (`:728-875`) | Binding-integrity checks in the module |
| Rule metadata (`:877-1037`) | Agreement and well-formedness checks (§3) |
| Rule resolution (`:1039-1073`) | Derivation in the module |
| Constraints (`:618-726`) | PLEML constraints in the module; allowed-list complement check |
| Lexical SysML mapping targets (`:1076-1315`) | Receipt identity; the regex checks are confined to the shadow and dropped at S7 |
| Projection block (`:119-165`) | Feature-model metadata check |
| Mandatory-leaf implication (#381) | Dropped: common content is no feature |
| Writer (`generate_sysml`) | Kept, reading receipts |
| Local unlicensed `--check-only` | Kept for committed configurations through offline replay; a new configuration needs licensed serialization |

## 5. Parity

**Coverage.** From S4 on, every PR that touches an input runs parity over 25 rows:

- the 8 files in `feature-configurations/`;
- the 10 existing probes;
- 7 closed-world probes: the four unsupported pairs, one hand-picked adapter, and the two pairs no other row exercises (Openpilot with S-CORE, and Apollo with none).

Each row compares the verdict, the reason class, the derived variants and the **normalised body**.

**The normalised body** is the projection below the provenance header, with the derivation-source line ("Derived … projection from …") normalised. The receipt carries:

- the description, folded as the writer folds it;
- each optional feature's explicit enabled or disabled state;
- until S7, each feature's catalogue path, taken from its short name.

**Reason classes:**

| YAML | PLEML |
|---|---|
| Invalid XOR choice / list for an alternative | Upper bound |
| Mandatory group or or-group without selection | Lower bound |
| Unknown feature path | Unknown feature (validation) |
| Unknown path for the adapter | Derived variant not selectable |
| C001, C003, C004, C005 | Exclusion with the same ID |
| No rule matching | Pair exclusion |
| Several rules matching | Derivation ambiguous |
| Mandatory leaf `false` | `not-expressible`: common content has no feature |
| Evidence errors | Evidence-reference check |
| Input error | Serialization or validation error |

**Classes.** The classes are `equal`, `both-reject` (same reason class), `not-expressible` (reviewed) and `defect`.

**Expected histogram:** 16 `equal`, 8 `both-reject`, 1 `not-expressible` (`ug-10-vehicle-target-aebs-false`), 0 `defect`. The YAML side, as executed, gives 16 valid and 9 rejected:

- the independent recount of 23 rows at `b3054100` gave 14 valid and 9 rejected;
- the two new pair probes were run at `910b196b` and are both valid, deriving `openpilotToSCORE` and `none`.

## 6. Steps and gates

**Before S4,** no step changes a YAML input, the configurator path or a projection, and a diff check proves it.

**From S4 on,** parity gates every step.

| Step | Content | Gate | Size |
|---|---|---|---|
| S0 | ADR 0022 and this plan | Owner merge | 3 files, ~700 lines |
| S1 | Lock `=1.1.1` and the byte check. Pinned `sysand` in `privileged-ple-qualification.yml:160` and `privileged-full-model-api-ingestion.yml:96`. Nothing in the export changes. | CI; Method Check unchanged | ~6 files, ~150 lines |
| S2 | Evaluator and derivation module with all checks of §3 and §4, offline replay, and conformance cases restated from upstream's documented verdicts (not vendored) | Unit tests | ~6–8 files, 1,600–3,000 lines |
| S2k | Method PR. Kernel definitions for derivation rules and for configuration and feature-model metadata (projection name, projection block, `unassigned`). No evidence-status type. | `check_repo` projections; Method Check | ~4 files, ~250 lines |
| S3a | Fenced SDV feature model, 4 configurations and the fixture, with bindings, rules, exclusions, correspondences and rationale. Receipt with elements. Authority job (the former PLE-S workflow). Naming note. PLE-S retired. | Licensed validation; agreement check; API round trip; offline replay equals receipt | ~20 files, 2,200–4,000 lines |
| S3b | Execution-environment feature models and 3 configurations | Licensed validation; receipts | ~8 files, ~500 lines |
| S4 | Parity check (§5) | 0 `defect`; histogram as expected | ~8 files, ~900 lines |
| S5 | Configurator reads receipts | All 7 normalised bodies equal | ~6 files, ~700 lines |
| S5o | Ontology PR (owner's yes). Classifies `FeatureConfiguration`, the selection relations and `variesAt`. Rewrites their register rows, admission exclusions, guard test and vocabulary-role comments. Merges directly before S6. | `check_repo`; Method Check | ~6 files, ~300 lines |
| S6k | Method PR: concern and viewpoint texts name "the authority of ADR 0022", which is true before and after S6 | `check_repo`; Method Check | ~3 files, ~120 lines |
| S6 | **Switch.** Selectors, `PINNED_DEPENDENCIES`, `AGENTS.md` validation scope, and the deploy workflow's dependency comment and fourth `test -f` (`deploy-public-sysml-api.yml:302-309, :357-359`). Projections from receipts. Docs and scope-model header rewritten. YAML labelled a non-authoritative shadow. Notes on ADR 0014 and ADR 0006. Rollback tag first. | Full parity; licensed validation; Method Check (the `sai-` identity changes); a fresh privileged binding (full-model ingestion) and a deploy; PLE-Q-style dispatch on the merge commit; owner merge. A failed post-merge check reverts S6 and S5o. | ~20 files, ~900 lines |
| S7 | Retire YAML: the catalogues, the YAML bills of features, the YAML path and lexical checks, and the oracle. The reference-only examples stay as PLEML configurations. The projection source wording changes in a reviewed regeneration. | The three OQ2 conditions; owner yes | ~30 files, about −4,000 lines |

**Order.** S1 and S2 run in parallel, and S3b can run in parallel with S4.

## 7. Provisioning (O2)

PLEML follows ADR 0007, adding:

- the byte check against the committed tag commit, blob and sha256 (ADR 0022 decision 1);
- the MIT licence on record;
- a CI guard that only the feature-model packages and their fixtures import PLEML.

The frozen experiments keep their pinned submodules as history.

## 8. Rollback (O3, refined by OQ2)

- **Shadow.** From S6 to S7 the YAML stays runnable as a non-authoritative shadow, and parity is checked on it.
- **Rollback** is the revert of S6 and S5o. Parity makes the projections regenerate equal. There is no runtime toggle.
- **Phase-9 content.** Content that YAML cannot express (per-domain platforms) must be re-expressed in YAML or withdrawn on a rollback. That cost grows with phase 9 and is accepted.
- **After S7,** rollback means restoring from the tag.

## 9. Upstream release policy (O4)

**Pinning.** Exact pin, no ranges, no automatic update. Each release is assessed within 14 days from the library diff and the changelog.

**Two paths:**

- **Fast path.** A release that changes only the version line or line endings gets one re-pin PR with the byte diff, licensed validation and refreshed receipts.
- **Full path.** Any other release adapts the models and the module, then re-runs licensed validation, the receipts, parity until S7, the bounded re-verification checks and an independent review.

**What blocks an upgrade:**

- a parity or receipt regression;
- an unadapted constraint form;
- an unreviewed change to the configuration or constraint definitions;
- a package that differs from its tag;
- a licence change;
- an incompatibility with the pinned SysIDE;
- an open upstream issue that touches a concept DE4SDV consumes.

## 10. INC-MW-011 phase 9

**Phase 9 waits for S6 and may start right after it.** It delivers:

- the scope-revision ADR for "Autoware on S-CORE with an AAOS HMI guest";
- per-domain platform modeling (GAP-MW-032, `middleware_score_framing.sysml:300-318`), done once, in PLEML;
- the member configuration, evolved from the migrated S-CORE example.

The rollback cost of §8 applies. Phase 8 merged as #389.

## 11. Risks and mitigations

| Risk | Mitigation |
|---|---|
| **Upstream maturity:** three releases in three days, one breaking, from one active contributor | Exact pin, confinement, §9 gates, fail-closed shape checks, rollback tag |
| **No native evaluation** (PLE-Q `39167884450`) | DE4SDV module with conformance cases; re-probe at each SysIDE upgrade; never claim native execution |
| **Serializer identity:** 11 PLE-Q rows without a concept check (`tests/test_ple_qualification.py:372-376`) | The S3a round trip covers the consumed concepts; the other rows stay recorded gaps |
| **Licensed CI** | Committed receipts and elements keep other PRs unlicensed; path filters |
| **Receipt authenticity** | Committed elements, offline replay, digest refusal |
| **Scope growth:** reference-only options configurable, as in YAML today | Admission stays with the governed scope; validity and admission are reported separately |
| **Kernel and ontology dependency** | S2k early; S5o before S6, with the owner's yes |
| **Production identity change at S6** | Fresh privileged binding and a deploy in the S6 gate |

## 12. Upstream contact (O5)

After S6, one comment on MBSE4U/PLEML#4 (the repository has no discussions). The note explains the derivation-rule approach to the maintainers. This is a draft; the owner approves the text before anything is posted, and it contains no design suggestions.

> A short update for your information: DE4SDV now uses PLEML 1.1.1, pinned
> through Sysand, as the authority for its feature models and configurations.
> We derive the application-middleware adapters with our own derivation rules
> over the feature model, and state the unsupported pairs as PLEML exclusions,
> so no helper features or implies constraints are needed for them. We take
> new releases by re-pinning and re-running our checks. Thanks for the quick
> 1.1.1 release.

## 13. Effort

| Measure | Estimate |
|---|---|
| PRs | 12 (S0, S1, S2, S2k, S3a, S3b, S4, S5, S5o, S6k, S6, S7), 3 of them method or ontology PRs |
| Size | 8,000–11,500 lines added before S7; S7 removes about 4,000 |
| Licensed runs | 24–30, including receipt refreshes and review rounds |
| Privileged and deploy | 1–2 full-model ingestion runs and 1–2 deploy runs at S6 |
| Calendar | 15–25 working days to S6; S7 no earlier than 30 days after S6 |
