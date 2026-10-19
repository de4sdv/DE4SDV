# PLEML product-line authority: migration plan

**Status:** plan for [ADR 0022](../architecture-decisions/0022-adopt-pleml-as-product-line-authority.md).
Nothing in it is evidence, qualification or a compliance claim.
**Decision owner:** Orkun Yilmaz. **Date:** 2026-10-19. **Base:** `3cca3eae`;
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
| Speed | Finish the PLEML work as fast as possible: the consolidated PR set and the parallel lanes of §6 |

**Proposed during review and confirmed by the owner on 2026-10-19:**

- **OQ2**, which refines O3. After the switch, the YAML stays a non-authoritative shadow for at least 30 days. S7 needs all three of:
  - the 30 days have passed;
  - one full-parity run on main after S6 is green;
  - no rollback trigger is open (§8).

  Phase 9 may start right after S6.
- **OQ3.** S2k creates no kernel evidence-status type. Configuration evidence status stays an external typed reference until the ontology review's `decision-4` (the EvidenceStatus split) is decided.
- **OQ5.** S5o, a method and ontology PR, decides the post-switch classification of `FeatureConfiguration`, the four selection relations and `variesAt`. It needs the owner's yes and merges as one gate with S6.
- **OQ6.** The ADR is `Accepted` on the S0 merge and takes effect at S6. At S6, ADR 0014 gets a marked partial-supersession note and stays `Accepted`.

## Starting point

- **PLE-Q.** Run `39167884450` on PLEML 1.1.0 recorded 2 cases observed and 4 gaps. Native constraint evaluation was not executed.
- **PLE-S.** Run `39169049300` covered 15 cases with no defect. See [ple-s-scope-alignment.md](../product-line-engineering/ple-s-scope-alignment.md).
- **PLEML itself.** It defines no derivation: a feature configuration is either valid or invalid.
- **PLEML 1.1.1.** Its library equals 1.1.0 apart from the version line. Its Sysand package is byte-identical to the release tag; the 1.1.0 package had CRLF line endings.

## 1. Target state

| Element | Target |
|---|---|
| **Feature models** | Three PLEML feature models under `model-based-product-line-engineering/feature-models/`, one per family: the SDV product line with its reference-only options, engineering execution environments, and vehicle-target execution environments. Variability only: `C-` common capabilities have no feature (§2). |
| **Configurations** | All 7 bills of features and the invalid fixture in `feature-configurations/` (its `README.md` excluded) become PLEML feature configurations. The fixture stays outside the authority roots. |
| **Evaluation** | A DE4SDV module reading serializer and API objects only (ADR 0011). It identifies definitions by metatype, declaration name and serializer-recorded source document, or by a validated binding (`de4sdv/semantic/kernel_binding_index.py:1-20`); never by a name alone. It checks multiplicities; requires and XOR, and implies once one is modeled; completeness and Development binding time; feature-only ownership; binding integrity; the static rule checks of §3; and admission (valid versus admitted). It fails closed and never reports native execution. |
| **Derivation** | Bindings, plus the 8 adapter rules as model-native DE4SDV derivation rules (§3) |
| **Receipts** | A licensed job serializes and evaluates each model. It commits the receipt (verdicts, derived variants, admission, input digests) together with the compressed serialized elements. The precedents are the Gate A export (`.xz`, 71 KB) and the genuine export (`.gz`, 1.2 MB). Committing them needs the owner's yes at S3 (the "Ask first" rule of `AGENTS.md`). Unlicensed CI re-runs the evaluator on the elements and refuses stale receipts by digest. Receipt paths are in the licensed path filter. |
| **Configurator** | Retargeted. It reads receipts and keeps its writer. After S6, variation and variant identity come from the receipt, and the lexical mapping checks (`tools/configure_variant.py:1203-1315`) stay only for the YAML shadow. |
| **Product models** | 7 projections with unchanged part-def names, compared on the normalised body (§5). One slice types a part by `MiddlewareAutowareAAOSSDVReference` (`middleware_variability_configuration.sysml:35`); another aliases and exposes it (`aebs_visualization_variability_configuration.sysml:174-181`). |
| **Production surface** | Unchanged until S6. Until then the models are fenced, as PLE-S was, and licensed-validated together with the reviewed roots and the pinned library (`ple-s-scope-alignment.md:367-378`). S6 changes the selectors and `PINNED_DEPENDENCIES`. |
| **Oracle** | Becomes the S4 parity check, then the rollback guard. Removed at S7. |
| **PLE-S** | Retired at S3, superseded by the fenced full-catalogue model. Its record stays as history. |
| **PLE-Q** | The frozen experiments stay as history. From S1, PLEML comes from the fenced Sysand lock. The current arm reads the interpreter and fixture of the experiment at PLEML 1.1.0 (`69bbe093`) until the S2 evaluator replaces them, at S4 at the latest. The `adapter-realization` gap is answered by the S3 derivation-rule round trip. |
| **Governed scope** | Stays the admission authority. Admission follows from model-native correspondences of each feature, which replace `catalogue-correspondence.yaml`. |

## 2. Catalogue mapping

| YAML | PLEML authority |
|---|---|
| `alternative` / `or_group` / `optional` | A `[1]` parent with `[0..1]` sub-features / a `[1..*]` parent / `[0..1]` |
| `C-` common capability nodes (`sdv_product_line.yaml:131-136, :162-174`) | No feature and no new model element (ADR 0021 decisions 1 and 4). Until S7, the parity check maps them to the governed common elements, as `catalogue-correspondence.yaml` does today. Their IDs retire at S7. Pedestrian and bicycle detection move under Capabilities. |
| Mandatory `F-` grouping nodes (`F-PLATFORM-STACK`, `F-SENSING`, `F-CAPABILITIES`) | Documented `[1]` grouping features that hold the variation points |
| C001, C003 (allowed lists "OS in […]") | XOR exclusions of the complement. The allowed list stays reviewed source in the model rationale, and a CI check fails when the complement drifts. |
| C004, C005 | XOR exclusions |
| C002, C006 | Dropped as constraints: in all 864 structurally valid selections neither ever fires. C002 allows every OS, and C006 targets common content. Their rationale is a comment in the SDV feature model. The complement check also reads the list recorded for C002, so a new OS option fails CI until C002 is re-assessed. |
| `maps_to` / `maps_to_variant` | One binding per variant, with the asset as client. Mapped variations and variants must stay at Development, as the configurator requires today (`tools/configure_variant.py:836-839, :857-860`). |
| `derived_asset_selections` | DE4SDV derivation rules (§3) |
| `F-`/`D-`/`PL-` IDs | Kept as SysML short names. The registry note (`naming-conventions.md:317-323`) is updated at S3. |
| `binding_time: unassigned` | No PLEML equivalent: a DE4SDV annotation (S2k). No verdict depends on it. |
| Bill-of-features `name`, `description`, `true`/`false` | Configuration metadata for the projection name (S2k); `doc`; `[1]`/`[0]` redefinitions. An omission stays an omission. |
| Bill-of-features `evidence` | An external evidence record per configuration (OQ3), proposed as `feature-configurations/evidence/<projection-name>.yaml`. It keeps today's schema: status, plus artifacts with id and path. The format is decided at S3, and the integrity rules of §4 apply. |
| Catalogue `projection` block (`tools/configure_variant.py:112-122, :181-199`) | Feature-model metadata for package, owner and label (S2k), carried in the receipt |

## 3. The closed world

Today the configurator rejects any pair without a rule (`sdv_product_line.yaml:34-37`) and any adapter chosen by hand. The authority keeps both rejections.

1. **Rules own the adapters.** The 8 rules become DE4SDV derivation rules: their premises in conjunction yield the resulting variant, which may be `none`. For each derived variation exactly one rule must match a valid configuration. With no match the configuration is rejected as "no rule"; with several, as "ambiguous". These are today's verdicts (`tools/configure_variant.py:1057-1066`). The rules live in the model, so no semantic authority hides in code.
2. **Exclusions state the unsupported pairs.** Two PLEML XOR constraints do this: Openpilot and Apollo each exclude Android SDV and AUTOSAR Adaptive.
3. **A total agreement check over all 12 pairs.** It requires:
   - exactly one rule for each of the 8 allowed pairs;
   - exactly one exclusion for each of the 4 unsupported ones;
   - exactly one application premise and one middleware premise per rule.

   Until S7 the rule table is also compared row by row with `sdv_product_line.yaml:45-60`. That keeps today's static checks against duplicate conditions and wrong keys (`tools/configure_variant.py:985-1027`).
4. **Hand-picked adapters stay impossible.** No adapter feature exists, a configuration owns only features, and the module refuses a binding or entry that targets a derived variant. ADR 0014's "It is not a manual product choice" holds.

**D1:** no helper features and no implies. The pattern is not needed, because the rules own the adapters.

## 4. Where today's configurator checks go

| Today (`tools/configure_variant.py`) | After S7 |
|---|---|
| Document and bill-of-features shapes (`:167-272`) | Licensed model validation; receipt schema in the module |
| Name and description (`validate_bof_metadata`) | Configuration-metadata check in the module |
| Evidence status and artifact integrity (`:274-340`): id grammar, duplicates, relative paths, no `.git`, no symlink escape, the file exists and is Git-tracked | A CI check over the external evidence records, with the same rules |
| Structure: unknown paths, XOR choice, or-groups, mandatory groups (`:503-600`) | Multiplicities and completeness in the module; validation errors for unknown features |
| Mapping integrity (`:728-875`): ids, binding times, every child mapped, one feature per variant | Binding-integrity checks in the module |
| Rule metadata (`:877-1037`) | Agreement and well-formedness checks (§3) |
| Rule resolution (`:1039-1073`) | Derivation in the module |
| Constraints (`:618-726`) | PLEML constraints in the module; allowed-list complement check |
| Lexical SysML mapping targets (`:1076-1315`) | Receipt identity. The regex checks stay only for the shadow and are dropped at S7. |
| Projection block (`:112-122`, `:181-199`) | Feature-model metadata check |
| Mandatory-leaf implication (#381) | Dropped: common content has no feature |
| Writer (`generate_sysml`) | Kept, reading receipts |
| Local unlicensed `--check-only` | Kept for committed configurations through offline replay. A new configuration needs licensed serialization. |

## 5. Parity

**Coverage.** From S4 on, every PR that touches an input runs parity over 25 rows:

- the 8 files in `feature-configurations/`;
- the 10 existing probes, frozen as the selections recorded in the retained `comparison.json` of the PLE-S record, so that S4 does not depend on the PLE-S receipt;
- 7 closed-world probes: the four unsupported pairs, one hand-picked adapter, and the two pairs that no other row exercises (Openpilot with S-CORE, Apollo with none).

**What each row compares:** the verdict, the reason class, the derived variants and the **normalised body**.

**The normalised body** is the projection below the provenance header, with the derivation-source line ("Derived … projection from …") normalised. The receipt carries:

- the description, folded as the writer folds it;
- each optional feature's explicit enabled or disabled state;
- until S7, each feature's catalogue path, taken from its short name.

**Reason classes.**

| YAML | PLEML |
|---|---|
| Invalid XOR choice, or a list for an alternative | Upper bound |
| Mandatory group or or-group without a selection | Lower bound |
| Unknown feature path | Unknown feature (validation) |
| Unknown path for the adapter | Derived variant not selectable |
| C001, C003, C004, C005 | Exclusion with the same ID |
| No rule matching | Pair exclusion |
| Several rules matching | Derivation ambiguous |
| Evidence errors | Evidence-record check |
| Input error | Serialization or validation error |

**Classes.** The classes are `equal`, `both-reject` (same reason class), `not-expressible` and `defect`. `not-expressible` applies only under all of these conditions:

- the construct is on a pinned, reviewed list. Today that list holds one entry: a common capability set to `false`, in row `ug-10-vehicle-target-aebs-false`.
- the construct is the sole YAML violation.
- the remainder is still compared: the same configuration without the construct must be PLEML-valid, with equal derived variants and an equal normalised body.

Any other `not-expressible` row is a `defect`.

**Histogram.** It is asserted on every parity run until S7. Expected: 16 `equal`, 8 `both-reject`, 1 `not-expressible`, 0 `defect`. The YAML side, as executed, gives 16 valid and 9 rejected:

- the independent recount of all 25 rows at `910b196b`;
- the two pair probes, which are both valid and derive `openpilotToSCORE` and `none`.

## 6. Steps and gates

**Before S4,** no step changes a YAML input, the configurator path or a projection, and a diff check proves it. **From S4 on,** parity gates every step.

| PR | Content | Gate | Size |
|---|---|---|---|
| S0 | ADR 0022 and this plan | Owner merge | 3 files, 664 lines |
| S1 | Lock `=1.1.1` and the byte check. Pinned `sysand` in `privileged-ple-qualification.yml:160` and `privileged-full-model-api-ingestion.yml:96`. Nothing in the export changes. | CI; Method Check unchanged | ~6 files, ~150 lines |
| S2k | Method PR. Kernel definitions for derivation rules and for configuration and feature-model metadata: projection name, projection block, `unassigned`. No evidence-status type. | `check_repo` projections; Method Check | ~4 files, ~250 lines |
| S2 | Evaluator and derivation module with all checks of §3 and §4, offline replay, and conformance cases restated from upstream's documented verdicts (not vendored) | Unit tests | ~6–8 files, 1,600–3,000 lines |
| S3 | **Fenced feature models: SDV, engineering and vehicle-target.** All 7 configurations and the fixture, with bindings, rules, exclusions, correspondences and rationale; receipts with their elements; the authority job, which is the former PLE-S workflow; the naming note, plus the PLE-S references in the product-line README and `docs/repository-tree.md`; PLE-S retired. | Licensed validation; agreement and complement checks; API round trip; offline replay equals receipt; owner's yes to committing compressed elements | ~28 files, 2,700–4,500 lines |
| S4 | **Parity check and retargeted configurator** (§5) | 0 `defect` and the expected histogram, **and** all 7 normalised bodies equal | ~14 files, ~1,600 lines |
| S5o | **Method and ontology PR** (owner's yes). Classifies `FeatureConfiguration`, the selection relations and `variesAt`; rewrites the register rows, admission exclusions and guard test, the kernel comment of `de4sdv_product_line.sysml:35-37`, the vocabulary-role comments, and the concern and viewpoint texts. | `check_repo`; Method Check; **one gate with S6**: merged directly before S6, with no ingestion or deploy between them | ~9 files, ~420 lines |
| S6 | **Switch.** Selectors, `PINNED_DEPENDENCIES` and the `AGENTS.md` validation scope; the deploy workflow's dependency comment and a fourth `test -f` (`deploy-public-sysml-api.yml:302-309, :357-359`); projections regenerated from receipts; docs and the scope-model header rewritten; YAML labelled a non-authoritative shadow; notes on ADR 0014 and ADR 0006; rollback tag first. | S5o merged directly before; full parity; licensed validation; Method Check (the `sai-` identity changes); a fresh privileged binding (full-model ingestion) and a deploy; a PLE-Q-style dispatch on the merge commit; owner merge. A failed post-merge check is a rollback trigger. | ~20 files, ~900 lines |
| S7 | **Retire YAML**: the catalogues, the YAML bills of features, the YAML path and lexical checks, the oracle, and the `C-` IDs (registry updated the same day). The reference-only examples stay as PLEML configurations. The projection source wording changes in a reviewed regeneration. | The three OQ2 conditions; owner yes | ~30 files, about −4,000 lines |

**Order.**

**Lanes.** These start now, in parallel with the review of S0:

- S1;
- S2k;
- S2;
- the authoring of S3;
- the authoring of S5o.

**Merges** follow the dependencies:

- **S0** merges first.
- **S1** can merge at any time after S0.
- **The rest is a chain:** S2k → S2 → S3 → S4 → (S5o + S6, one gate).

There are six sequential merge points to the switch: S0, S2k, S2, S3, S4 and S5o + S6.

## 7. Provisioning (O2)

PLEML follows ADR 0007, plus three additions:

- the byte check against the committed tag commit, blob and sha256 (ADR 0022 decision 1);
- the MIT license on record;
- a CI guard so that only the feature-model packages and their fixtures import PLEML.

The guard has two exemptions:

- the PLE-S model, until S3 retires it;
- the PLE-Q probe text written by `scripts/run_ple_scoped_execution.py:137`.

The frozen experiments keep their pinned submodules as history.

## 8. Rollback (O3, refined by OQ2)

- **Shadow.** From S6 to S7 the YAML stays runnable as a non-authoritative shadow, and parity is checked against it.
- **Rollback triggers.** Any one of these is a trigger:
  - a parity defect on main;
  - a failed post-merge check of S6 (licensed validation, ingestion, deploy or PLE-Q-style dispatch);
  - an evaluator or derivation defect that changes a verdict or a derived variant;
  - the owner's call.
- **A rollback** reverts S6 together with S5o, and re-runs the privileged ingestion and the deploy, because the served-model identity changes back. There is no runtime toggle.
- **Phase-9 content** that YAML cannot express (per-domain platforms) must be re-expressed in YAML or withdrawn on a rollback. That cost grows with phase 9 and is accepted.
- **After S7,** rollback means restoring from the tag.

## 9. Upstream release policy (O4)

**Pinning and assessment.**

- Exact pin, no ranges, no automatic update.
- Each release is assessed within 14 days from the library diff and the changelog.

**Fast path.** A release that changes only the version line or line endings gets one re-pin PR with:

- the byte diff;
- licensed validation;
- refreshed receipts.

**Full path.** Any other release adapts the models and the module. It then re-runs:

- licensed validation;
- the receipts;
- parity, until S7;
- the bounded re-verification checks;
- an independent review.

**What blocks an upgrade:**

- a parity or receipt regression;
- an unadapted constraint form;
- an unreviewed change to the configuration or constraint definitions;
- a package that differs from its tag;
- a license change;
- an incompatibility with the pinned SysIDE;
- an open upstream issue that touches a concept DE4SDV consumes.

## 10. INC-MW-011 phase 9

Phase 9 waits for S6 and may start right after it. It delivers:

- the scope-revision ADR for "Autoware on S-CORE with an AAOS HMI guest";
- per-domain platform modeling (GAP-MW-032, `middleware_score_framing.sysml:300-318`), done once, in PLEML;
- the member configuration, evolved from the migrated S-CORE example.

The rollback cost in §8 applies. Phase 8 merged as #389.

## 11. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Upstream maturity: three releases in three days, one of them breaking, from one active contributor | Exact pin, confinement, the §9 gates, fail-closed shape checks, rollback tag |
| No native evaluation (PLE-Q `39167884450`) | DE4SDV module with conformance cases; re-probe at each SysIDE upgrade; never claim native execution |
| Serializer identity: 11 PLE-Q rows without a concept check (`tests/test_ple_qualification.py:372-376`) | The S3 round trip covers the consumed concepts; the rest stay recorded gaps |
| Licensed CI | Committed receipts and elements keep other PRs unlicensed; path filters |
| Receipt authenticity | Committed elements, offline replay, digest refusal |
| Scope growth: reference-only options become configurable, as in YAML today | Admission stays with the governed scope; validity and admission are reported separately |
| Kernel and ontology dependency | S2k early; S5o as one gate with S6, with the owner's yes |
| Production identity change at S6 | Fresh privileged binding and a deploy in the S6 gate |
| Calendar: a second review round on S2 or S3, or an upstream release mid-way | §13 range; the §9 fast path for an unchanged-content release |

## 12. Upstream contact (O5)

After S6, one comment on MBSE4U/PLEML#4 (the repository has no discussions). The note explains the derivation-rule approach to the maintainers. The draft below needs the owner's approval of the text before posting, and it carries no design suggestions.

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
| PRs | 9: eight to the switch (S0, S1, S2k, S2, S3, S4, S5o, S6), plus S7. S2k and S5o are method or ontology PRs. |
| Size | 8,200–11,500 lines added before S7; S7 removes about 4,000 |
| Licensed runs | About 18–28, counting review rounds and receipt refreshes |
| Licensed runs by PR | S1 1–2, S2k 2–4, S2 1–2, S3 3–6, S4 3–5, S5o 2–4, S6 3–5, S7 2–3 |
| Privileged and deploy | One full-model ingestion and one deploy at S6, about 4.5 h plus the owner's approval; a rollback would need its own |
| Calendar to S6 | About 5–8 working days: six sequential merge points at about one working day each, including one review round |
| Measured cadence | Open-to-merge took 12.2 h (#384), 5.8 h (#387), 14.7 h (#388) and 13.7 h (#389) |
| Assumptions | The owner merges within a day; one review round per big PR |
| S7 | At least 30 days after S6 |
