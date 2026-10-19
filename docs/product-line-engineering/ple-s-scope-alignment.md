# PLE-S: scope alignment of the admitted AEBS product line in PLEML

**Status:** experiment, not an authority. Draft evidence of the third PLEML
gate; every receipt says `qualified: false`. **Retired** at step S3 of
[ADR 0022](../architecture-decisions/0022-adopt-pleml-as-product-line-authority.md):
the fenced [PLEML feature models](pleml-feature-models.md) supersede the
experiment, and its model, workflow and runner were removed. This record
stays as history: the files below are cited at the revision of the
retained run.
**Decision authority for anything beyond this record:** Orkun Yilmaz, DE4SDV
technical lead and maintainer.
**Model:** [`aebs_product_line_scope_alignment.sysml`](https://github.com/de4sdv/DE4SDV/blob/f967a519a9f98a2ab1b6dc8e886c3e7ad1415cdb/model-based-product-line-engineering/pleml-scope-alignment/aebs_product_line_scope_alignment.sysml)
(at the retained run's revision `f967a519`)
**Governed inputs:** [ADR 0014](../architecture-decisions/0014-ratify-initial-aebs-product-line-scope.md),
the [governed scope model](../../model-based-product-line-engineering/scoping/de4sdv_aebs_product_line_scope.sysml)
and the [platform-stack superset](../../textual-notation-of-model/packages/architecture/sdv_platform_stack.sysml).

## Where it sits

The PLEML gates run in order: PLE-R and PLE-Q observed the pinned library's
representation and serialization on synthetic fixtures; PLE-S (this record)
aligns the *admitted* scope with the library; PLE-A would be the separate
adoption decision. PLE-S keeps the operational path (the YAML catalogue, the
committed configurations and `tools/configure_variant.py`) as it is and runs
it as a comparison oracle beside this model, not as a second selection
authority ([below](#the-comparison-oracle)).

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
  configurations and the configurator are untouched; the comparison oracle
  reads them and compares, it selects nothing and admits nothing.
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
`39167884450` on main at `f967a519`, the commit this record's run executed
(artifact
`ple-qualification-f967a519a9f98a2ab1b6dc8e886c3e7ad1415cdb-39167884450`).
Its three receipts (historical replay, current serialization with API
readback, scoped probes) record the executor `f967a519` with
`executor_source_dirty: false` and `qualified: false` throughout; the
historical replay and the current serialization record the six qualification
cases as observed, not qualified: `feature-binding` and `group-shapes`
observed; `xor-counterexample`, `binding-time`, `serializer-identity` and
`adapter-realization` as gaps. The frozen
interpreter, PLEML pin and library digests of its current serialization and
scoped probes are the ones this record's receipt carries; its historical
replay stays on the Gate A experiment. Three of the six cases depended on
questions to the PLEML maintainers (the XOR constraint body, the meaning of
two bindings on one element, and the binding-time rule); their status is in
the table below, and PLE-S is built not to depend on them. The run
`39114284825` on main at `f1da5c0c` (artifact
`ple-qualification-f1da5c0c707990efeb378990b288778246b0d975-39114284825`)
recorded the same six case statuses at PLEML 1.0.0, and the run `38780181818`
on main at `03f7fd22` (artifact
`ple-qualification-03f7fd22137ad8caaba8dc3d1006c308164f62a1-38780181818`) at
the Gate A pin `5f8ab856`; both are kept as history. The earlier runs
`37410659181` (`e37c7f1`, 2026-10-06) and `38755211223` (`60847add`,
2026-10-15) are superseded history: the same case statuses, but receipts with
`executor_source_dirty: true` because the frozen experiment checkout and the
API log sat inside the executor checkout, the defect #375 fixed. No formal
PLE-R or PLE-Q disposition is recorded on main; PLE-S proceeds on this
observed status (owner decision D0).

**PLEML 1.1.0.** The PLE workflows read the frozen experiment at PLEML 1.1.0:
revision `69bbe093` (tag `pleml-1.1.0-frozen`), a child of the experiment at
PLEML 1.0.0, `84673ea2` (tag `pleml-1.0.0-frozen`), which is a child of the
Gate A revision `6a99626b` (tag `pleml-gate-a-frozen`). Its PLEML submodule is
at `76e2be93`. PLEML 1.1.0 gives every feature constraint the parameter
`constrainedFeatures` with the operands A and B, so the fixture's XOR and
REQUIRES usages take the 1.1 form (`in occurrence constrainedFeatures = new
FeatureOperand(that, androidSDV);`), and the interpreter reads the excluded
feature as operand B. It refuses an operand A that names another feature of the
model than the owner, but it cannot tell the kernel `that` from another feature
the bundle leaves out. The PLE-Q runner therefore checks the operands by
identity: operand A must be the owner or the kernel `that` (the target of the
library's own `featureConfiguration = that`), and the constructor must
instantiate the pinned library's `FeatureOperand`. A constraint without an
owner refuses, and the receipt's `constraint_operands` counts the constraints
the check verified. Before the tag, a licensed scratch check (run
`39151970312`, not evidence) loaded this fixture with the 1.1.0 library and
passed the Gate A path. The historical replay and the prior of the fresh
serialization stay on the Gate A experiment, which produced the retained
export. The run above and the run this record retains (below) read PLEML
1.1.0. The PLE-Q run `39114284825` and the record's previous run
`39115737098` read PLEML 1.0.0, from the experiment `84673ea2` with the
submodule at `071a69fd`; the run `38780181818` and the record's earlier run
`38788579272` describe the Gate A pin `5f8ab856`.

**PLEML 1.1.1.** The PLE workflows now install PLEML 1.1.1 through the fenced
Sysand lock in
[`libraries/pleml/`](../../model-based-product-line-engineering/libraries/pleml/README.md)
and byte-check it against the committed record of its release tag before any
step reads it
([ADR 0022](../architecture-decisions/0022-adopt-pleml-as-product-line-authority.md)).
They no longer check out the experiment's PLEML submodule. The 1.1.1 library
equals the 1.1.0 library except for its version line, so the interpreter, the
fixture and the library label stay those of the experiment `69bbe093`, and no
frozen-experiment commit is made. The receipts name the release tag commit
`b694648c` as the PLEML pin. The runs named above and the retained record read
PLEML 1.1.0 and stay history.

### Dependence on the upstream questions

| Question | Status (2026-10-18) | Would apply to | How PLE-S avoids it |
|---|---|---|---|
| XOR loop ([MBSE4U/PLEML#3](https://github.com/MBSE4U/PLEML/issues/3)) | fixed in PLEML 1.0.0 by reading: the body iterates over `excluded`; no tool here evaluates it; closed upstream | any cross-tree exclusion | one variability, no cross-tree constraint; exclusivity is the `[1]` bound |
| two bindings on one element ([#4](https://github.com/MBSE4U/PLEML/issues/4)) | answered upstream and closed: PLEML 1.1.0 adds `ImpliesConstraint` (`(A and B) implies C`); PLE-S keeps one binding per variant and does not use it; the adapter pattern is the planned follow-up | an asset bound to two features | every variant has exactly one binding, each to one alternative |
| binding-time rule ([#5](https://github.com/MBSE4U/PLEML/issues/5)) | answered: the intent is completeness, a configuration that leaves a phase decides every feature bound in it; no stage-aware evaluator here; closed upstream | later-stage or partial configurations | everything stays at the Development default; both members set the only Development feature |

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
not fixed in PLE-S. The comparison oracle's catalogue correspondence of
`F-PLATFORM-OS-LINUX` to `linuxROS2AutowareRuntime`, through which it sees
the runtime represented in the standalone member, is a catalogue-node
correspondence and not a superset realization dependency; it does not
contradict the model's statement that the runtime has no superset
realization.

## The comparison oracle

The operational path stays a comparison oracle, not a second selection
authority (plan cases UG-09, UG-10 and UG-14).
`scripts/compare_ple_scope_alignment.py` runs the unchanged
`tools/configure_variant.py` once per case, records its exit code (0 valid,
1 invalid, 2 input error) and the `part :>> <variation> =
<variation>::<variant>;` selections of the projection, and sets the result
beside the PLE-S evaluation of the same statement. Each row reports two
independent fields:

- `configuration-valid-under-current-tool`: the configurator's verdict, with
  its messages and violated constraints;
- `admitted-by-governed-scope`: derived from serialized governed-scope data
  only. A selected catalogue node is a derived realization of an admitted
  alternative when the receipt binds its shared-asset variant to that feature
  (`alignment.bindings`); common when the receipt records its variant as the
  superset realization of common content (`alignment.common_assets`); and
  otherwise classified by the governed-scope validation set (common,
  reference-only, deferred, excluded) of the element that the declared
  correspondence
  [`catalogue-correspondence.yaml`](https://github.com/de4sdv/DE4SDV/blob/f967a519a9f98a2ab1b6dc8e886c3e7ad1415cdb/model-based-product-line-engineering/pleml-scope-alignment/catalogue-correspondence.yaml)
  names for it. The correspondence carries no classification and is validated
  against the catalogue and the serialization; a node without any
  classification is unclassified and fails the run. A configuration is
  admitted when every selection is common content or a derived realization
  of exactly one alternative, that alternative's selectable derived
  realizations are all present, and every common asset the catalogue can
  represent is fully represented: all of its selectable nodes are chosen, a
  mandatory leaf the selections leave untouched counts as implied, and one
  switched off counts as dropped. The receipt's confirmed representation
  difference exempts an asset only in rows whose implied alternative binds
  the variation that causes the difference.

Each row also carries the PLE-S outcome (validity, violated bound, derived
shared-asset variants, common assets), a difference class, and provenance:
the feature-model, Bill-of-Features and shared-assets SHA-256 of the
projection header (computed by the oracle when the tool generates no
projection) plus the receipt identity (executor revision, run id, artifact,
model, evaluator, interpreter, PLEML pin and library digests).

### Difference classes (UG-14)

| Class | Meaning |
|---|---|
| `equal` | tool-valid and admitted, and the projection selects exactly the PLE-S derived variants and common realization |
| `intentional-scope` | tool-valid, not admitted. The configurator accepts content the governed scope keeps reference-only, deferred or excluded (UG-09, UG-10); content the governed scope has no element for (`not-in-governed-scope`: a catalogue feature candidate such as adaptive cruise control); a selection that realizes more than one admitted alternative (derived realizations of both alternatives mixed in one selection); or a selection that leaves common content incompletely represented (a dropped baseline sensor) |
| `intentional-representation` | equal on every variant, but a common asset of the governed scope is not representable in the single slot the superset offers; the receipt's confirmed representation difference names it (owner decision D6) |
| `not-expressible-under-tool` | the PLE-S statement has no scalar encoding in the catalogue (an alternative group takes one value); the oracle records the tool's actual response to the list encoding |
| `both-reject` | tool-invalid and not admitted, for independent reasons: the tool's violations, the scope's reasons and the PLE-S outcome are recorded side by side; there are no derived assets on either side to compare |
| `defect` | anything else: an admitted member the tool rejects, a derivation the two paths disagree on, a valid PLE-S configuration for non-admitted content, an input error, an unclassified selection. A defect or an unclassified row exits non-zero |

### Cases

| Case | Operational input | PLE-S statement |
|---|---|---|
| standalone-member | `aebs-autoware-linux-lidar-camera.yaml` | `standaloneAutowareAEBSReferenceMemberConfiguration` |
| aaos-integrated-member | `middleware-autoware-aaos-sdv-reference.yaml` | `aaosIntegratedAutowareAEBSReferenceMemberConfiguration` |
| both-alternatives | generated: the probe's alternatives encoded per bound layer, a list where two variants compete | `bothIntegrationModesProbe` |
| no-alternative | generated: the member template without the bound layers; the tool's response is recorded, not asserted in advance | `noIntegrationModeProbe` |
| ug-09-eclipse-score, ug-09-apollo-qnx-qvm | the committed examples `example-linux-score-autoware.yaml` and `apollo-qnx-qvm.yaml` | none: reference-only content has no feature |
| ug-09-autosar-acrn | generated from the member template: `Middleware: AUTOSARAdaptive`, `Hypervisor: ACRN` (the remaining reference-only elements with a catalogue node) | none: reference-only content has no feature |
| ug-10-openpilot-no-middleware, ug-10-radar-only | generated from the member template: `VehicleApplication: Openpilot` with `Middleware: None`; `PerceptionSensors: [Radar]` | none: common and deferred content has no feature |
| ug-10-lidar-only, ug-10-camera-only | generated: `PerceptionSensors: [LiDAR]`; `[Camera]` (the common baseline without one of its sensors) | none: common content has no feature |
| ug-10-vehicle-target-aebs-false | generated: `VehicleTargetAEBS: false`; the configurator rejects it, since a mandatory leaf set to false is a violation (its mandatory-leaf check never fired while the catalogue root defaulted to optional, fixed in #381) | none: common content has no feature |
| catalogue-only-adaptive-cruise-control | generated: `AdaptiveCruiseControl: true` | none: the governed scope has no element for it |
| derived-set-mixed | generated: `Middleware: AndroidSDV` on the standalone derived set; tool-valid, the adapter derives | none: derived realizations are not independently selectable |
| both-axes-negative | `fixtures/invalid-score-android.yaml` | none |

Generated probes are written to a temporary directory outside the repository
and are never committed under `feature-configurations/`. Excluded System 2
content (engineering execution environments, simulation benchmarks, CI
evidence campaigns, visualization instrumentation) cannot be exercised with
this catalogue: the engineering-environment configurations use other
catalogues, and `sdv_product_line.yaml` has no node that corresponds to an
excluded element, so the `excluded` classification is defined but has no row.

### Classified table (retained)

PLE-S receipt: `retained` evidence of run `39169049300` at executor `f967a519a9f98a2ab1b6dc8e886c3e7ad1415cdb` (artifact `ple-scope-alignment-f967a519a9f98a2ab1b6dc8e886c3e7ad1415cdb-39169049300`); receipt SHA-256 `53ba633c99695e5d38b96cc7a11f68097290f2ffd94943a2d1adbe03cff5f78b`; model `23f53587e727f24aa2f24f148e2de77720bbcfa6701df57f3b0d1b4152f77dde`; evaluator `0780e4f66a3d2e8e6086ec19f895a7ba86dc51bae2713f40385fde29b25dfb16`; PLEML pin `76e2be934453d77c4094141400b8ad8eb90a54a2`; library `a89dc5c3436e3c8e5601e278f2b184e1a6d91f66a77f8616854ee0dd1abca787`; serializer `0.10.3`; qualified: false.

| Case | Operational input | Valid under current tool | Admitted by governed scope | PLE-S outcome | Difference class |
|---|---|---|---|---|---|
| standalone-member | `model-based-product-line-engineering/feature-configurations/aebs-autoware-linux-lidar-camera.yaml` | yes (exit 0) | yes: standalone | configuration-valid | equal |
| aaos-integrated-member | `model-based-product-line-engineering/feature-configurations/middleware-autoware-aaos-sdv-reference.yaml` | yes (exit 0) | yes: aaosIntegrated | configuration-valid | intentional-representation |
| both-alternatives | generated `BothIntegrationModesProbe` from `model-based-product-line-engineering/feature-configurations/aebs-autoware-linux-lidar-camera.yaml` | no (exit 1) | no: the selections realize more than one admitted alternative: aaosIntegrated, standalone | configuration-invalid (upper bound) | not-expressible-under-tool |
| no-alternative | generated `NoIntegrationModeProbe` from `model-based-product-line-engineering/feature-configurations/aebs-autoware-linux-lidar-camera.yaml` | no (exit 1) | no: no admitted alternative is realized by the selections; common content not fully represented by the selections: linuxROS2AutowareRuntime not represented (missing: F-PLATFORM-OS-LINUX) | configuration-invalid (lower bound) | both-reject |
| ug-09-eclipse-score | `model-based-product-line-engineering/feature-configurations/example-linux-score-autoware.yaml` | yes (exit 0) | no: not admitted content selected: PlatformStack.Middleware = EclipseSCORE: reference-only eclipseSCORE; derived realizations of standalone missing from the selections: middleware::none | no PLE-S configuration: the admitted tree has no feature for eclipseSCORE (reference-only) | intentional-scope |
| ug-09-apollo-qnx-qvm | `model-based-product-line-engineering/feature-configurations/apollo-qnx-qvm.yaml` | yes (exit 0) | no: not admitted content selected: PlatformStack.VehicleApplication = Apollo: reference-only apollo; PlatformStack.Middleware = EclipseSCORE: reference-only eclipseSCORE; PlatformStack.OS = QNX: reference-only qnxQVM; PlatformStack.Hypervisor = QVM: reference-only qnxQVM; SensingBoundary.PerceptionSensors = Radar: deferred sensingVariability; no admitted alternative is realized by the selections; common content not fully represented by the selections: autowareApplication not represented (missing: F-PLATFORM-VEHICLE-APPLICATION-AUTOWARE); currentSensingBaseline partially represented (missing: F-SENSING-PERCEPTION-CAMERA); linuxROS2AutowareRuntime not represented (missing: F-PLATFORM-OS-LINUX) | no PLE-S configuration: the admitted tree has no feature for apollo (reference-only), eclipseSCORE (reference-only), qnxQVM (reference-only), sensingVariability (deferred) | intentional-scope |
| ug-09-autosar-acrn | generated `AUTOSARAdaptiveACRNProbe` from `model-based-product-line-engineering/feature-configurations/aebs-autoware-linux-lidar-camera.yaml` | yes (exit 0) | no: not admitted content selected: PlatformStack.Middleware = AUTOSARAdaptive: reference-only autosarAdaptive; PlatformStack.Hypervisor = ACRN: reference-only acrn; derived realizations of standalone missing from the selections: hypervisor::none, middleware::none | no PLE-S configuration: the admitted tree has no feature for acrn (reference-only), autosarAdaptive (reference-only) | intentional-scope |
| ug-10-openpilot-no-middleware | generated `OpenpilotNoMiddlewareProbe` from `model-based-product-line-engineering/feature-configurations/aebs-autoware-linux-lidar-camera.yaml` | yes (exit 0) | no: not admitted content selected: PlatformStack.VehicleApplication = Openpilot: reference-only openpilot; common content not fully represented by the selections: autowareApplication not represented (missing: F-PLATFORM-VEHICLE-APPLICATION-AUTOWARE) | no PLE-S configuration: the admitted tree has no feature for openpilot (reference-only) | intentional-scope |
| ug-10-radar-only | generated `RadarOnlySensingProbe` from `model-based-product-line-engineering/feature-configurations/aebs-autoware-linux-lidar-camera.yaml` | yes (exit 0) | no: not admitted content selected: SensingBoundary.PerceptionSensors = Radar: deferred sensingVariability; common content not fully represented by the selections: currentSensingBaseline partially represented (missing: F-SENSING-PERCEPTION-CAMERA, F-SENSING-PERCEPTION-LIDAR) | no PLE-S configuration: the admitted tree has no feature for sensingVariability (deferred) | intentional-scope |
| ug-10-lidar-only | generated `LidarOnlySensingProbe` from `model-based-product-line-engineering/feature-configurations/aebs-autoware-linux-lidar-camera.yaml` | yes (exit 0) | no: common content not fully represented by the selections: currentSensingBaseline partially represented (missing: F-SENSING-PERCEPTION-CAMERA) | no PLE-S configuration: common content not fully represented by the selections: currentSensingBaseline partially represented (missing: F-SENSING-PERCEPTION-CAMERA) | intentional-scope |
| ug-10-camera-only | generated `CameraOnlySensingProbe` from `model-based-product-line-engineering/feature-configurations/aebs-autoware-linux-lidar-camera.yaml` | yes (exit 0) | no: common content not fully represented by the selections: currentSensingBaseline partially represented (missing: F-SENSING-PERCEPTION-LIDAR) | no PLE-S configuration: common content not fully represented by the selections: currentSensingBaseline partially represented (missing: F-SENSING-PERCEPTION-LIDAR) | intentional-scope |
| ug-10-vehicle-target-aebs-false | generated `VehicleTargetAEBSOffProbe` from `model-based-product-line-engineering/feature-configurations/aebs-autoware-linux-lidar-camera.yaml` | no (exit 1) | no: common content not fully represented by the selections: vehicleTargetAEBS not represented (dropped: C-CAPABILITY-AEBS-VEHICLE-TARGET) | no PLE-S configuration: common content not fully represented by the selections: vehicleTargetAEBS not represented (dropped: C-CAPABILITY-AEBS-VEHICLE-TARGET) | both-reject |
| catalogue-only-adaptive-cruise-control | generated `AdaptiveCruiseControlProbe` from `model-based-product-line-engineering/feature-configurations/aebs-autoware-linux-lidar-camera.yaml` | yes (exit 0) | no: not admitted content selected: Capabilities.AdaptiveCruiseControl = True: not-in-governed-scope | no PLE-S configuration: the admitted tree has no feature for Capabilities.AdaptiveCruiseControl (not-in-governed-scope) | intentional-scope |
| derived-set-mixed | generated `MixedDerivedSetProbe` from `model-based-product-line-engineering/feature-configurations/aebs-autoware-linux-lidar-camera.yaml` | yes (exit 0) | no: the selections realize more than one admitted alternative: aaosIntegrated, standalone | no PLE-S configuration: the selections realize more than one admitted alternative: aaosIntegrated, standalone | intentional-scope |
| both-axes-negative | `model-based-product-line-engineering/feature-configurations/fixtures/invalid-score-android.yaml` | no (exit 1; C001) | no: not admitted content selected: PlatformStack.Middleware = EclipseSCORE: reference-only eclipseSCORE; the selections realize more than one admitted alternative: aaosIntegrated, standalone; common content not fully represented by the selections: currentSensingBaseline partially represented (missing: F-SENSING-PERCEPTION-CAMERA); linuxROS2AutowareRuntime not represented (missing: F-PLATFORM-OS-LINUX) | no PLE-S configuration: the admitted tree has no feature for eclipseSCORE (reference-only) | both-reject |

| Case | Tool projection | PLE-S derived variants and common realization | Equal on | Differing | Class reason |
|---|---|---|---|---|---|
| standalone-member | applicationMiddlewareAdapter::none, hypervisor::none, middleware::none, osPlatform::linux, vehicleApplication::autoware | applicationMiddlewareAdapter::none, hypervisor::none, middleware::none, osPlatform::linux, vehicleApplication::autoware | applicationMiddlewareAdapter::none, hypervisor::none, middleware::none, osPlatform::linux, vehicleApplication::autoware | - | the projection selects exactly the PLE-S derived variants and common realization |
| aaos-integrated-member | applicationMiddlewareAdapter::autowareToAAOSSDV, hypervisor::kvm, middleware::androidSDV, osPlatform::android, vehicleApplication::autoware | applicationMiddlewareAdapter::autowareToAAOSSDV, hypervisor::kvm, middleware::androidSDV, osPlatform::android, vehicleApplication::autoware | applicationMiddlewareAdapter::autowareToAAOSSDV, hypervisor::kvm, middleware::androidSDV, osPlatform::android, vehicleApplication::autoware | - | equal on applicationMiddlewareAdapter::autowareToAAOSSDV, hypervisor::kvm, middleware::androidSDV, osPlatform::android, vehicleApplication::autoware; linuxROS2AutowareRuntime is common in the governed scope but not represented (osPlatform is bound per alternative): recorded; the split execution-domain representation of the superset is owned by INC-MW-011 (owner decision D6, 2026-10-15), not by the scope alignment |
| both-alternatives | - | - | - | - | an alternative group takes one scalar; the statement needs more than one variant per variation and the tool rejected the list encoding (exit 1); PLE-S: configuration-invalid (upper bound) |
| no-alternative | - | - | - | - | the tool rejects and the governed scope does not admit, for independent reasons: tool invalid (4 violations): Mandatory alternative group 'PlatformStack.Middleware' has no selection; governed scope no: no admitted alternative is realized by the selections \| common content not fully represented by the selections: linuxROS2AutowareRuntime not represented (missing: F-PLATFORM-OS-LINUX); PLE-S configuration-invalid (lower bound) |
| ug-09-eclipse-score | applicationMiddlewareAdapter::autowareToSCORE, hypervisor::none, middleware::eclipseSCORE, osPlatform::linux, vehicleApplication::autoware | - | - | - | tool-valid; no: not admitted content selected: PlatformStack.Middleware = EclipseSCORE: reference-only eclipseSCORE \| derived realizations of standalone missing from the selections: middleware::none |
| ug-09-apollo-qnx-qvm | applicationMiddlewareAdapter::apolloToSCORE, hypervisor::qvm, middleware::eclipseSCORE, osPlatform::qnx, vehicleApplication::apollo | - | - | - | tool-valid; no: not admitted content selected: PlatformStack.VehicleApplication = Apollo: reference-only apollo; PlatformStack.Middleware = EclipseSCORE: reference-only eclipseSCORE; PlatformStack.OS = QNX: reference-only qnxQVM; PlatformStack.Hypervisor = QVM: reference-only qnxQVM; SensingBoundary.PerceptionSensors = Radar: deferred sensingVariability \| no admitted alternative is realized by the selections \| common content not fully represented by the selections: autowareApplication not represented (missing: F-PLATFORM-VEHICLE-APPLICATION-AUTOWARE); currentSensingBaseline partially represented (missing: F-SENSING-PERCEPTION-CAMERA); linuxROS2AutowareRuntime not represented (missing: F-PLATFORM-OS-LINUX) |
| ug-09-autosar-acrn | applicationMiddlewareAdapter::autowareToAUTOSAR, hypervisor::acrn, middleware::autosarAdaptive, osPlatform::linux, vehicleApplication::autoware | - | - | - | tool-valid; no: not admitted content selected: PlatformStack.Middleware = AUTOSARAdaptive: reference-only autosarAdaptive; PlatformStack.Hypervisor = ACRN: reference-only acrn \| derived realizations of standalone missing from the selections: hypervisor::none, middleware::none |
| ug-10-openpilot-no-middleware | applicationMiddlewareAdapter::none, hypervisor::none, middleware::none, osPlatform::linux, vehicleApplication::openpilot | - | - | - | tool-valid; no: not admitted content selected: PlatformStack.VehicleApplication = Openpilot: reference-only openpilot \| common content not fully represented by the selections: autowareApplication not represented (missing: F-PLATFORM-VEHICLE-APPLICATION-AUTOWARE) |
| ug-10-radar-only | applicationMiddlewareAdapter::none, hypervisor::none, middleware::none, osPlatform::linux, vehicleApplication::autoware | - | - | - | tool-valid; no: not admitted content selected: SensingBoundary.PerceptionSensors = Radar: deferred sensingVariability \| common content not fully represented by the selections: currentSensingBaseline partially represented (missing: F-SENSING-PERCEPTION-CAMERA, F-SENSING-PERCEPTION-LIDAR) |
| ug-10-lidar-only | applicationMiddlewareAdapter::none, hypervisor::none, middleware::none, osPlatform::linux, vehicleApplication::autoware | - | - | - | tool-valid; no: common content not fully represented by the selections: currentSensingBaseline partially represented (missing: F-SENSING-PERCEPTION-CAMERA) |
| ug-10-camera-only | applicationMiddlewareAdapter::none, hypervisor::none, middleware::none, osPlatform::linux, vehicleApplication::autoware | - | - | - | tool-valid; no: common content not fully represented by the selections: currentSensingBaseline partially represented (missing: F-SENSING-PERCEPTION-LIDAR) |
| ug-10-vehicle-target-aebs-false | - | - | - | - | the tool rejects and the governed scope does not admit, for independent reasons: tool invalid (1 violation): Mandatory feature not selected: 'Capabilities.ForwardCollisionMitigation.VehicleTargetAEBS'; governed scope no: common content not fully represented by the selections: vehicleTargetAEBS not represented (dropped: C-CAPABILITY-AEBS-VEHICLE-TARGET); PLE-S no PLE-S configuration: common content not fully represented by the selections: vehicleTargetAEBS not represented (dropped: C-CAPABILITY-AEBS-VEHICLE-TARGET) |
| catalogue-only-adaptive-cruise-control | applicationMiddlewareAdapter::none, hypervisor::none, middleware::none, osPlatform::linux, vehicleApplication::autoware | - | - | - | tool-valid; no: not admitted content selected: Capabilities.AdaptiveCruiseControl = True: not-in-governed-scope |
| derived-set-mixed | applicationMiddlewareAdapter::autowareToAAOSSDV, hypervisor::none, middleware::androidSDV, osPlatform::linux, vehicleApplication::autoware | - | - | - | tool-valid; no: the selections realize more than one admitted alternative: aaosIntegrated, standalone |
| both-axes-negative | - | - | - | - | the tool rejects and the governed scope does not admit, for independent reasons: tool invalid (1 violation): C001; governed scope no: not admitted content selected: PlatformStack.Middleware = EclipseSCORE: reference-only eclipseSCORE \| the selections realize more than one admitted alternative: aaosIntegrated, standalone \| common content not fully represented by the selections: currentSensingBaseline partially represented (missing: F-SENSING-PERCEPTION-CAMERA); linuxROS2AutowareRuntime not represented (missing: F-PLATFORM-OS-LINUX); PLE-S no PLE-S configuration: the admitted tree has no feature for eclipseSCORE (reference-only) |

| Case | Feature model | Bill-of-Features | Shared assets | Digest origin |
|---|---|---|---|---|
| standalone-member | `57b4f7eda267` | `08a73fd91ff1` | `70cbc35d9583` | projection header |
| aaos-integrated-member | `57b4f7eda267` | `bd06674c4a6c` | `70cbc35d9583` | projection header |
| both-alternatives | `57b4f7eda267` | `b052ec94073d` | `70cbc35d9583` | computed by the oracle (the tool generated no projection) |
| no-alternative | `57b4f7eda267` | `c1e297c203bb` | `70cbc35d9583` | computed by the oracle (the tool generated no projection) |
| ug-09-eclipse-score | `57b4f7eda267` | `08d6a8315a95` | `70cbc35d9583` | projection header |
| ug-09-apollo-qnx-qvm | `57b4f7eda267` | `a99a0d0ca81b` | `70cbc35d9583` | projection header |
| ug-09-autosar-acrn | `57b4f7eda267` | `fe47bc4124b0` | `70cbc35d9583` | projection header |
| ug-10-openpilot-no-middleware | `57b4f7eda267` | `ee3335fed0c4` | `70cbc35d9583` | projection header |
| ug-10-radar-only | `57b4f7eda267` | `ee536c2733aa` | `70cbc35d9583` | projection header |
| ug-10-lidar-only | `57b4f7eda267` | `9290aa06a63a` | `70cbc35d9583` | projection header |
| ug-10-camera-only | `57b4f7eda267` | `4bcd6cd1fdfb` | `70cbc35d9583` | projection header |
| ug-10-vehicle-target-aebs-false | `57b4f7eda267` | `0d8a4d476e56` | `70cbc35d9583` | computed by the oracle (the tool generated no projection) |
| catalogue-only-adaptive-cruise-control | `57b4f7eda267` | `7d8ffb1bbef5` | `70cbc35d9583` | projection header |
| derived-set-mixed | `57b4f7eda267` | `5a861b6b65d8` | `70cbc35d9583` | projection header |
| both-axes-negative | `57b4f7eda267` | `4fa3f5a4982c` | `70cbc35d9583` | computed by the oracle (the tool generated no projection) |

Classes: equal: standalone-member; intentional-scope: ug-09-eclipse-score, ug-09-apollo-qnx-qvm, ug-09-autosar-acrn, ug-10-openpilot-no-middleware, ug-10-radar-only, ug-10-lidar-only, ug-10-camera-only, catalogue-only-adaptive-cruise-control, derived-set-mixed; intentional-representation: aaos-integrated-member; not-expressible-under-tool: both-alternatives; both-reject: no-alternative, ug-10-vehicle-target-aebs-false, both-axes-negative; defect: none. Full digests and reasons: the JSON comparison.

### What the table shows

- The two members derive the same assets on both paths. The AAOS-integrated
  row is `intentional-representation`: the common `linuxROS2AutowareRuntime`
  is not represented because `osPlatform` holds `android`; the receipt's
  recorded difference owns it (INC-MW-011, owner decision D6), and the
  exemption applies because `aaosIntegrated` binds `osPlatform`. The
  standalone row represents the runtime by `osPlatform::linux` and is the
  only `equal` row.
- UG-09: the configurator accepts the committed S-CORE and Apollo/QNX/QVM
  examples and the generated AUTOSAR Adaptive/ACRN probe; the governed scope
  admits none of them, and the reason is read from the serialized
  reference-only set, element ids included. Every reference-only element
  with a catalogue node is exercised (Openpilot by its UG-10 row).
- UG-10: Openpilot without middleware and a radar-only sensing selection are
  tool-valid; the governed scope keeps Autoware and the LiDAR/camera baseline
  common and defers driving-stack and sensing variability, so neither is a
  distinguishing feature within the admitted portfolio. A baseline without
  its camera or without its LiDAR is tool-valid and not admitted: the common
  sensing baseline is partially represented (the motion sensors are implied
  by the catalogue's mandatory leaf). The vehicle-target capability switched
  off is `both-reject`: the configurator rejects a mandatory leaf set to
  false, and the governed scope does not admit the dropped common content.
- Adaptive cruise control is a catalogue feature candidate the governed scope
  has no element for (`not-in-governed-scope`); a selection mixing the derived
  realizations of both alternatives is tool-valid (the adapter derives) and
  not admitted because it realizes more than one admitted alternative.
- The both-alternatives statement has no scalar encoding; the tool rejects
  the list encoding, and PLE-S violates the upper bound. The no-alternative
  probe is `both-reject`: each path rejects it for its own reason (mandatory
  groups without a selection; the lower bound).
- `fixtures/invalid-score-android.yaml` is `both-reject`: it fails constraint
  C001 under the tool and is not admitted because of reference-only content;
  the two fields are independent.

The table is the **retained** comparison of run `39169049300` at
`f967a519a9f98a2ab1b6dc8e886c3e7ad1415cdb`, the main commit the run executed
(the merge of #391, dispatched as `ref`; no pull-request head); the retained
files and their manifest are in
[`ple-s-scope-alignment-evidence/`](ple-s-scope-alignment-evidence/README.md).
The record is **retained, bound to its own revision**: the commit that last
changed that directory. `tests/test_ple_scope_alignment_oracle.py` extracts
that revision's files from Git history and reproduces the comparison there at
every CI run, never against the working tree, so a later change to the
governed scope, the superset, the scope validator, the catalogue or the
configurator makes the record **historical**, not failing (owner decision,
2026-10-16); a pull request that changes the record must make it consistent
at its own commit. Fresh evidence for a head needs a licensed run: the
**fresh** comparison of a head is the `comparison/` directory of that head's
workflow artifact, the same oracle on the receipt of that run, valid for that
head only, and the oracle refuses a receipt whose digests differ from the
tree it is compared with. Both carry `qualified: false`.

## Evidence and how to rerun

Since the retirement, the workflow, the model and the runner below exist
only in history, up to `cdb20aa0`, the last revision of main before the
retirement. A replay runs at such a revision; the retained record itself is
still verified at its own revision by CI.

- **Workflow:** `.github/workflows/privileged-ple-scope-alignment.yml` runs on
  pull requests that touch the scope-alignment paths (same-repository,
  allowlisted authors, as the licensed validation) and on maintainer
  dispatch with a `ref`. It checks out the exact head, reads the frozen
  interpreter from the experiment at PLEML 1.1.0, `69bbe093` (tag
  `pleml-1.1.0-frozen`), checked out without its PLEML submodule and
  relocated outside the executor checkout, installs PLEML 1.1.1 from the
  fenced Sysand lock and byte-checks it against its release tag, runs
  `syside check` on the reviewed roots with the pinned library and the
  model, then
  `scripts/run_ple_scope_alignment.py --licensed`, which serializes the same
  set with the pinned serializer, validates the governed scope exactly as
  production does, and evaluates every configuration with the frozen Gate A
  resolver extended only for exact-one parents. A refusal of a dirty checkout
  precedes every recording step and follows the evaluation. After the receipt
  check, `scripts/compare_ple_scope_alignment.py --evidence fresh` compares
  the operational path with the fresh receipt of the same head, between two
  further refusals of a dirty checkout; it runs without the licence.
- **Artifact:** `ple-scope-alignment-<head SHA>-<run id>` (30 days):
  `receipt.json`, `scope-alignment-elements.json` (the serialized elements of
  the model, the governed scope, the platform stack and the library),
  `governed-scope-validation.json`, `serializer-diagnostics.txt`,
  `syside-check.txt`, and `comparison/comparison.json` with
  `comparison/comparison.md` (the fresh comparison).
- **Retained record:**
  [`ple-s-scope-alignment-evidence/`](ple-s-scope-alignment-evidence/README.md)
  keeps the receipt, the governed-scope validation and the comparison of run
  `39169049300` with a manifest of digests. It is retained evidence of that
  run, bound to the record's own revision and verified there by CI;
  historical, not failing, once the files it was produced from move; fresh
  evidence of a later head needs a licensed run, and the oracle refuses a
  receipt whose digests differ from the tree it is compared with.
- **Receipt identity:** executor SHA and `executor_source_dirty`, the
  verified digests of the executor inputs, the frozen interpreter revision
  and digest, the PLEML pin and library digest, the library's Sysand
  provision (package, version, tag and lock), the model and evaluator
  digests, the serializer version, the `sysand-lock.toml` digest, the source
  manifest, the per-configuration outcomes with selected features, violated
  bound, derived variants and correspondence, the common-asset
  classification, the recorded representation difference, and the
  non-claims above.
- **Offline replay:** `python scripts/run_ple_scope_alignment.py --replay
  <scope-alignment-elements.json> --out <directory outside the repository>`
  re-evaluates a retained element file with the frozen interpreter read from
  this repository's Git history: the frozen revision `69bbe093` is kept by the
  tag `pleml-1.1.0-frozen`, the code reads the exact revision, and the bytes
  are verified against the reviewed digest. An element file replays only with
  the experiment it records: the runner refuses another one and names the
  file's executor revision. Replay it at a revision that pins its experiment:
  the element file of the retained run `39169049300` records the PLEML 1.1.0
  experiment and replays on main from `f967a519` until the PLEML 1.1.1
  re-pin, such as `cdb20aa0`; the element file of the
  previous run `39115737098` records the PLEML 1.0.0 experiment and replays on
  main from `f1da5c0c` until the PLEML 1.1.0 re-pin, such as `2a9a1c81`; the
  element file of the earlier run `38788579272` records the Gate A experiment
  and replays on main before PLEML 1.0.0, such as `099d33e6`. Replay evidence
  is not fresh serialization and says so.
- **Unlicensed checks (public CI):** `tests/test_ple_scope_alignment_model.py`
  (boundary fence, textual shape, every qualified reference resolvable in
  its source), `tests/test_ple_scope_alignment_evaluator.py` (the evaluator on
  synthetic API-shaped graphs with the real frozen interpreter),
  `tests/test_ple_scope_alignment_workflow.py` (workflow wiring and secret
  scoping) and `tests/test_ple_scope_alignment_oracle.py` (the oracle on the
  retained receipt: UG-09, UG-10 and UG-14 as sets, admission moving with a
  reclassified governed element, a changed derivation and a missing
  correspondence exiting non-zero, the refusals, and the retained record
  reproduced from the retained receipt).

Evidence is valid for its exact head only. A move of main rebinds nothing;
the next run on the new head is the next evidence.
