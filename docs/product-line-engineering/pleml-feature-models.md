# PLEML feature models and configurations

**Status:** draft, fenced. These models restate the YAML catalogues and every
Bill-of-Features with the exact-pinned PLEML library, under
[ADR 0022](../architecture-decisions/0022-adopt-pleml-as-product-line-authority.md).
They take no authority until its switch (step S6): until then the YAML
catalogues, the Bills-of-Features and `tools/configure_variant.py` remain the
selection authority. Nothing here is qualification, adoption evidence or a
compliance claim; every record says `qualified: false`.
**Decision authority:** Orkun Yilmaz, DE4SDV technical lead and maintainer.

## What the models contain

| Family | Feature model | Configurations |
|---|---|---|
| SDV product line | [`sdv_product_line.sysml`](../../model-based-product-line-engineering/feature-models/sdv_product_line.sysml) | the four SDV Bills-of-Features, plus the invalid fixture under `fixtures/` |
| Engineering execution environments (System 2) | [`engineering_execution_environments.sysml`](../../model-based-product-line-engineering/feature-models/engineering_execution_environments.sysml) | `inc_aebs_009a_jetson.sysml`, `apple_silicon_macos_candidate.sysml` |
| Vehicle-target execution environments (System 1) | [`vehicle_execution_environments.sysml`](../../model-based-product-line-engineering/feature-models/vehicle_execution_environments.sysml) | `nxp_zephyr_vehicle_target_candidate.sysml` |

Each feature model is a `#featureModel` definition whose feature tree is a
`#featureTree` definition. Each configuration is a `#featureConfiguration`
typed by that tree, in its own file with the stem of its Bill-of-Features,
so the fixture can stay outside the authority roots.

How the catalogue is restated:

- **IDs.** Every `F-` and `PL-` ID is the SysML short name of its feature or
  tree, and every constraint ID that of its constraint.
- **Common content.** A `C-` common-capability node has no feature and no
  element: features distinguish member products. Pedestrian and bicycle
  detection therefore sit directly under the capabilities feature.
- **Structure.** A mandatory grouping node becomes a `[1]` feature that holds
  its variation points; an alternative group a `[1]` feature whose `[0..1]`
  choices subset it; the perception sensors a `[1..*]` group; an optional
  capability a `[0..1]` feature. Every feature keeps the Development binding
  time; the four capabilities with an unassigned binding time carry
  `#UnassignedBindingTime`.
- **Exclusions.** C001 and C003 (allowed lists) and C004 and C005 become
  exclusions. C002 and C006 never fire in any structurally valid selection,
  so they are dropped as constraints; their rationale stays in the model.
  The execution-environment constraints become requires constraints.
- **Bindings.** One feature binding per shared-asset variant, with the variant
  as client.
- **Derivation.** The application-middleware adapter is a derived variation,
  `D-ASSET-APPLICATION-MIDDLEWARE-ADAPTER`, with the eight rules of the
  catalogue as derivation rules. A derived variant is never a feature, and no
  binding or configuration entry targets one.
- **Correspondences.** Each SDV feature that restates a governed-scope element
  has a dependency to it; the governed scope classifies it. A derived
  realization of an admitted alternative corresponds to that alternative.
  Each execution-environment family corresponds as a whole: the engineering
  family to the excluded System 2 concern, the vehicle-target family to the
  deferred vehicle runtime variability.
- **Projection metadata.** Each feature model carries its catalogue's
  projection block, and each configuration the name of its projection. The
  metadata sits in the body of the element it annotates, never in an `about`
  from outside, because the evaluator reads only the metadata an element owns.
- **Descriptions.** The doc of a configuration is its Bill-of-Features'
  description, a `false` selection is a `[0]` redefinition, and an unlisted
  feature is left unset.

## The closed world

The eight derivation rules and the exclusions of Openpilot and Apollo cover
all twelve application-middleware pairs, each exactly once: a rule for each
allowed pair and an exclusion for each unsupported one. Each rule has one
application and one middleware premise, and the rule table equals the
catalogue's row by row. A configuration that matches no rule or several is
rejected.

The allowed lists of C001 and C003 stay the reviewed source in the rationale
of their exclusions, and C002's list in its rationale comment. The complement
check proves that each exclusion set equals the complement of its list over
the current operating-system options, so a new option fails CI until the
rules are re-assessed.

## The fence

The files are outside every production selector: not in the reviewed export
roots or the pinned dependencies, not a validation root, not a viewer root,
not served and not in the method check. No production workflow triggers on
them. Only the feature models and their fixture import PLEML.

## The authority job

[`privileged-ple-authority.yml`](../../.github/workflows/privileged-ple-authority.yml)
runs on pull requests that touch these models, their runner or their tests
(same-repository, allowlisted authors) and on maintainer dispatch. On the
exact head it:

1. runs the unlicensed checks;
2. validates the reviewed roots, the pinned library and the PLEML files with
   the licensed `syside check`;
3. serializes them once with the production export options
   ([`run_ple_authority.py`](../../scripts/run_ple_authority.py)), validates
   the governed scope as production does, and builds the authority bundle:
   the PLEML files, the shared-asset supersets, the governed scope, the
   derivation kernel and the library;
4. imports the bundle into an ephemeral SysML v2 API and verifies the
   full-payload readback (the API round trip);
5. hands the bundle to the evaluator (ADR 0022, step S2), which writes the
   receipts.

The receipts and their compressed elements are committed after a licensed
run, with the owner's yes to committing them. Unlicensed CI then re-runs the
evaluator on the committed elements and refuses a stale receipt. Until the
Sysand lock of step S1 provides PLEML 1.1.1, the job reads the library from
the frozen experiment at 1.1.0, whose content equals 1.1.1 apart from its
version line.

The unlicensed checks are
[`test_ple_authority_model.py`](../../tests/test_ple_authority_model.py)
(the fence, the catalogue restatement, the agreement and complement checks,
the bindings, correspondences and configurations),
[`test_ple_authority_runner.py`](../../tests/test_ple_authority_runner.py)
and [`test_ple_authority_workflow.py`](../../tests/test_ple_authority_workflow.py).
They are lexical: licensed validation is the validator, and the evaluator
owns the semantics.

## Evidence records

The `evidence` block of a Bill-of-Features is not a feature selection. When
the Bills-of-Features retire, it moves to an external evidence record per
configuration, `feature-configurations/evidence/<file stem>.yaml`, with
today's schema and integrity rules. Until then it stays in the
Bill-of-Features.

## History

The PLE-S scope-alignment experiment is retired; these models supersede it.
Its record stays in [`ple-s-scope-alignment.md`](ple-s-scope-alignment.md).
