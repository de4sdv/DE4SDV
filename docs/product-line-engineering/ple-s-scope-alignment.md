# PLE-S: scope alignment of the admitted AEBS product line in PLEML

**Status:** experiment, not an authority. Draft evidence of the third PLEML
gate; every receipt says `qualified: false`.
**Decision authority for anything beyond this record:** Orkun Yilmaz, DE4SDV
technical lead and maintainer.
**Model:** [`aebs_product_line_scope_alignment.sysml`](../../model-based-product-line-engineering/pleml-scope-alignment/aebs_product_line_scope_alignment.sysml)
**Governed inputs:** [ADR 0014](../architecture-decisions/0014-ratify-initial-aebs-product-line-scope.md),
the [governed scope model](../../model-based-product-line-engineering/scoping/de4sdv_aebs_product_line_scope.sysml)
and the [platform-stack superset](../../textual-notation-of-model/packages/architecture/sdv_platform_stack.sysml).

## Where it sits

The PLEML gates run in order: PLE-R and PLE-Q observed the pinned library's
representation and serialization on synthetic fixtures; PLE-S (this record)
aligns the *admitted* scope with the library; PLE-A would be the separate
adoption decision. PLE-S keeps the operational path (the YAML catalogue, the
committed configurations and `tools/configure_variant.py`) as it is. The
comparison oracle between the operational path and this model is a later
step and not part of this record.

## What PLE-S demonstrates

The model contains, and the licensed run evaluates:

- **One variability.** `vehiclePlatformIntegrationMode[1]` with
  `standalone[0..1]` and `aaosIntegrated[0..1]` subsetting it. Exclusivity is
  the `[1]` bound of the parent plus subsetting, the same shape Gate A used
  for its exact-one feature; no XOR usage anywhere.
- **Two member configurations**, one per planned reference member, each
  selecting exactly one alternative, and each bound from its governed member
  part by a `#FeatureConfigurationBinding` dependency (observability only; the
  governed member-to-alternative dependencies remain the membership
  statement).
- **Two invalid probes.** `bothIntegrationModesProbe` selects both
  alternatives (upper bound); `noIntegrationModeProbe` selects none (lower
  bound). Neither is a member.
- **Eight feature bindings**, one `#FeatureBinding` dependency per shared-asset
  variant, each naming one feature, every variant bound at most once:
  `aaosIntegrated` binds `middleware::androidSDV`, `hypervisor::kvm`,
  `osPlatform::android` and `applicationMiddlewareAdapter::autowareToAAOSSDV`;
  `standalone` binds `middleware::none`, `hypervisor::none`, `osPlatform::linux`
  and `applicationMiddlewareAdapter::none`. These are the derived technical
  realizations of ADR 0014 expressed against the real superset. A binding is
  linkage and provenance only; nothing infers AND, OR or precedence from the
  number of bindings.
- **Common content without bindings.** The five common items are classified
  by the governed scope only. Where the superset realizes one
  (`autowareApplication` by `vehicleApplication::autoware`), a plain
  dependency records it.
- **Correspondence.** Every feature of the tree refers to the governed element
  it restates; a feature with no correspondence, or one corresponding to
  common, derived, reference-only, deferred or excluded content, fails the
  evaluation. Reference-only, deferred and excluded content gets no feature
  and no configuration.
- **Development only.** Every feature and configuration keeps the PLEML
  Development default binding time.

### Expected outcomes

The licensed run must reproduce this table; the evaluator refuses anything it
cannot classify.

| Configuration | Role | Outcome | Derived shared-asset variants |
|---|---|---|---|
| `standaloneAutowareAEBSReferenceMemberConfiguration` | member | valid | `middleware::none`, `hypervisor::none`, `osPlatform::linux`, `applicationMiddlewareAdapter::none` |
| `aaosIntegratedAutowareAEBSReferenceMemberConfiguration` | member | valid | `middleware::androidSDV`, `hypervisor::kvm`, `osPlatform::android`, `applicationMiddlewareAdapter::autowareToAAOSSDV` |
| `bothIntegrationModesProbe` | probe | invalid, upper bound | none (validity is evaluated before realization) |
| `noIntegrationModeProbe` | probe | invalid, lower bound | none |

## What PLE-S does not do

- No PLEML adoption, qualification or upstream agreement: `qualified: false`,
  `adoption_authorized: false`, `authority_activation_authorized: false` in
  every receipt.
- No change of selection authority: the YAML catalogue, the committed
  configurations and the configurator are untouched.
- No new member: Eclipse S-CORE and every other reference-only alternative
  stays reference-only; admitting one is a scope revision with its own ADR.
- No XOR semantics (no `xorFeatures`, no `XORConstraint`), no multi-binding
  semantics (`multiple_binding_policy_proven: false`), no stage-aware
  binding-time semantics (`stage_aware_evaluation_proven: false`).
- No execution of a PLEML constraint body (`native_expression_executed:
  false`); no API ingestion (owner decision D4).
- No change to the production export, the method check, the served model or
  the semantic authority identity: the directory is outside every production
  selector.
- No compliance, certification or homologation claim.

## PLE-R and PLE-Q status (observed, not qualified)

The observed PLE-R/PLE-Q status is the privileged PLE qualification run
`38780181818` on main at `03f7fd22`, this record's base (artifact
`ple-qualification-03f7fd22137ad8caaba8dc3d1006c308164f62a1-38780181818`).
Its three receipts (historical replay, current serialization with API
readback, scoped probes) record the executor `03f7fd22` with
`executor_source_dirty: false`, `qualified: false` throughout, and the six
qualification cases as observed, not qualified: `feature-binding` and
`group-shapes` observed; `xor-counterexample`, `binding-time`,
`serializer-identity` and `adapter-realization` as gaps. Its frozen
interpreter, PLEML pin and library digests are the ones this record's receipt
carries. Three of the six cases depend on open upstream questions to the
PLEML maintainers (the XOR constraint body, the meaning of two bindings on
one element, and the binding-time rule); PLE-S is built not to depend on
them. The earlier runs `37410659181` (`e37c7f1`, 2026-10-06) and
`38755211223` (`60847add`, 2026-10-15) are superseded history: the same case
statuses, but receipts with `executor_source_dirty: true` because the frozen
experiment checkout and the API log sat inside the executor checkout, the
defect #375 fixed. No formal PLE-R or PLE-Q disposition is recorded on main;
PLE-S proceeds on this observed status (owner decision D0).

### Dependence on the open upstream questions

| Question | Would apply to | How PLE-S avoids it |
|---|---|---|
| XOR loop | any cross-tree exclusion | one variability, no cross-tree constraint; exclusivity is the `[1]` bound |
| two bindings on one element | an asset bound to two features | every variant has exactly one binding, each to one alternative |
| binding-time rule | later-stage or partial configurations | everything stays at the Development default; both members set the only Development feature |

## Known representation difference (owner decision D6)

`linuxROS2AutowareRuntime` is common in the governed scope, but the superset
has a single `osPlatform` slot, which the AAOS-integrated alternative binds to
`android` (the vehicle-platform domain) while the Autoware application domain
keeps its Linux runtime. The superset cannot express the split topology, so
the common runtime has no superset realization dependency and `osPlatform` is
bound per alternative. The receipt records this as
`intentional-representation` and confirms the structural facts in the graph.
The split execution-domain representation of the superset is owned by
INC-MW-011 (owner decision D6, 2026-10-15), whose member product has two
execution domains (a Linux host and an AAOS SDV HMI guest under KVM); it is
not fixed in PLE-S.

## Evidence and how to rerun

- **Workflow:** `.github/workflows/privileged-ple-scope-alignment.yml` runs on
  pull requests that touch the scope-alignment paths (same-repository,
  allowlisted authors, as the licensed validation) and on maintainer
  dispatch with a `ref`. It checks out the exact head, reads the frozen Gate A
  experiment at `6a99626b` with the PLEML submodule at pin `5f8ab856`,
  relocates it outside the executor checkout, runs `syside check` on the
  reviewed roots with the pinned library and the model, then
  `scripts/run_ple_scope_alignment.py --licensed`, which serializes the same
  set with the pinned serializer, validates the governed scope exactly as
  production does, and evaluates every configuration with the frozen Gate A
  resolver extended only for exact-one parents. A refusal of a dirty checkout
  precedes every recording step and follows the evaluation.
- **Artifact:** `ple-scope-alignment-<head SHA>-<run id>` (30 days):
  `receipt.json`, `scope-alignment-elements.json` (the serialized elements of
  the model, the governed scope, the platform stack and the library),
  `governed-scope-validation.json`, `serializer-diagnostics.txt` and
  `syside-check.txt`.
- **Receipt identity:** executor SHA and `executor_source_dirty`, the
  verified digests of the executor inputs, the frozen interpreter revision
  and digest, the PLEML pin and library digest, the model and evaluator
  digests, the serializer version, the `sysand-lock.toml` digest, the source
  manifest, the per-configuration outcomes with selected features, violated
  bound, derived variants and correspondence, the common-asset
  classification, the recorded representation difference, and the
  non-claims above.
- **Offline replay:** `python scripts/run_ple_scope_alignment.py --replay
  <scope-alignment-elements.json> --out <directory outside the repository>`
  re-evaluates a retained element file with the frozen interpreter read from
  this repository's Git history: the frozen revision `6a99626b` is kept by the
  tag `pleml-gate-a-frozen`, the code reads the exact revision, and the bytes
  are verified against the reviewed digest. Replay evidence is not fresh
  serialization and says so.
- **Unlicensed checks (public CI):** `tests/test_ple_scope_alignment_model.py`
  (boundary fence, textual shape, every qualified reference resolvable in
  its source), `tests/test_ple_scope_alignment_evaluator.py` (the evaluator on
  synthetic API-shaped graphs with the real frozen interpreter) and
  `tests/test_ple_scope_alignment_workflow.py` (workflow wiring and secret
  scoping).

Evidence is valid for its exact head only. A move of main rebinds nothing;
the next run on the new head is the next evidence.
