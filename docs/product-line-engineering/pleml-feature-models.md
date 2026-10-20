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
| SDV product line | [`sdv_product_line.sysml`](../../model-based-product-line-engineering/feature-models/sdv_product_line.sysml) | the four SDV Bills-of-Features, plus the invalid fixture and the 17 parity probes under `fixtures/` |
| Engineering execution environments (System 2) | [`engineering_execution_environments.sysml`](../../model-based-product-line-engineering/feature-models/engineering_execution_environments.sysml) | `inc_aebs_009a_jetson.sysml`, `apple_silicon_macos_candidate.sysml` |
| Vehicle-target execution environments (System 1) | [`vehicle_execution_environments.sysml`](../../model-based-product-line-engineering/feature-models/vehicle_execution_environments.sysml) | `nxp_zephyr_vehicle_target_candidate.sysml` |

Each feature model is a `#featureModel` definition whose feature tree is a
`#featureTree` definition. Each configuration is a `#featureConfiguration`
typed by that tree, in its own file with the stem of its Bill-of-Features in
snake case, so the fixture can stay outside the authority roots. The parity
probes have no Bill-of-Features (see [Parity](#parity-with-the-yaml-path)).

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

A test also evaluates the closed world: for every structurally valid
selection of each catalogue (16,128 for the SDV product line), the model's
groups, exclusions, requires constraints and derivation rules give the same
verdict, the same constraint IDs and the same derived adapter as the
configurator. Structurally invalid selections are outside that equality:
both sides reject them, but not always for the same constraint IDs, because
an exclusion presumes the exactly-one structure of its group.

## Admission

The governed scope is the admission authority, so a configuration can be
valid without being admitted. Admission requires validity: an invalid
configuration is never admitted, however its features correspond. The
correspondences are read as the PLE-S record read its catalogue
correspondence, the reading that reproduced its retained verdicts. A valid
configuration is admitted when all of these hold:

- Every selected choice and leaf corresponds to an admitted alternative or to
  common content. One that corresponds only to reference-only, deferred or
  excluded content, or to nothing, blocks.
- A grouping feature carries no admission. A group feature's correspondence
  (`vehicleApplication`, `perceptionSensors`) classifies its variation point:
  it is a note and never blocks. An execution-environment family corresponds
  as a whole, so its classification applies to every configuration of the
  family.
- The selections realize exactly one admitted alternative and select every
  derived realization of it.
- Every common asset that features represent is represented by all of them.
  The exception is the representation difference that PLE-S recorded: the
  AAOS-integrated alternative takes the single operating-system slot, so the
  common Linux runtime is exempt under that alternative. Common content without
  a feature is part of every member.

So the two governed members of ADR 0014 are admitted: the standalone member
(`aebs_autoware_linux_lidar_camera`) and the AAOS-integrated member
(`middleware_autoware_aaos_sdv_reference`). The two reference examples
(Eclipse S-CORE, and Apollo on QNX) are not admitted. Neither is any
configuration of the two execution-environment families: the engineering
family is the excluded System 2 concern, and the vehicle-target family is
the deferred vehicle runtime variability. A test computes these verdicts from
the model. The evaluator of step S2 owns the verdict.

## Features that distinguish no member yet

Ontology rule R001 asks every feature to distinguish at least one member
product from another. These features restate catalogue options that no
configuration of their family selects, or that every one selects:

| Family | In every configuration | In no configuration |
|---|---|---|
| SDV product line (4 configurations) | LiDAR | Openpilot, AUTOSAR Adaptive, ACRN, and the four capabilities |
| Engineering execution environments (2) | none | the Intel x86-64 nested-KVM host, the x86-64 Linux AOSP build, and nested-KVM Cuttlefish |
| Vehicle-target execution environments (1) | NXP compute, Zephyr and native Zephyr | the three "no concrete" choices |

They stay features. The migration restates the full catalogue, reference-only
options included (owner decision O1 of the plan), and a family with one
configuration can distinguish nothing. The ontology pull request before the
switch (S5o) decides whether R001 applies to the features of a PLEML feature
model. The grouping and group features are structure, not member
distinctions.

## The fence

The files are outside every production selector: not in the reviewed export
roots or the pinned dependencies, not a validation root, not a viewer root,
not served and not in the method check. No production workflow triggers on
them. Only the feature models, their configurations, the fixture and the
parity probes import PLEML.

## The authority job

[`privileged-ple-authority.yml`](../../.github/workflows/privileged-ple-authority.yml)
runs on pull requests that touch these models, their runner, their tests,
the PLEML pin, the committed receipts or the documents and catalogues the
receipts bind (same-repository, allowlisted authors), and on maintainer
dispatch. On the exact head it:

1. installs PLEML 1.1.1 from the fenced Sysand project of step S1
   ([`libraries/pleml/`](../../model-based-product-line-engineering/libraries/pleml/README.md))
   and byte-checks it against the committed record of its release tag before
   any step reads it;
2. runs the unlicensed model, runner and workflow tests;
3. validates the reviewed roots, the pinned library and the PLEML files with
   the licensed `syside check`;
4. serializes them once with the production export options
   ([`run_ple_authority.py`](../../scripts/run_ple_authority.py)), validates
   the governed scope as production does, and builds the authority bundle:
   the PLEML files, the shared-asset supersets, the governed scope, the
   derivation kernel and the library;
5. imports the bundle into an ephemeral SysML v2 API and verifies the
   full-payload readback (the API round trip);
6. hands the bundle to the entry point of the evaluator (ADR 0022, step S2),
   `write_receipts` of `scripts/run_pleml_configuration_evaluation.py`, which
   writes the compressed elements and one receipt per feature model;
7. runs both checks of the committed receipts with the evaluator's own
   functions, and fails when either fails. `compare_with_committed` requires
   their elements to equal the fresh ones; only the run's provenance, which
   the receipts record beside the elements, may differ. `replay_committed`
   re-evaluates them from those elements and requires the evaluation and the
   shadow checks to reproduce byte for byte, which catches an edited verdict
   over genuine elements. A code-identity difference is recorded as an
   advisory, not a failure;
8. runs the receipt test on the exact head. It runs after the runner, never
   before the serialization: a document change leaves the committed receipts
   stale until the fresh receipts of a run are committed, so the test must
   not stop the run that writes them.

The library document of the bundle is labelled by its repository path,
`LIBRARY_PATH` of `de4sdv/semantic/pleml_package.py`.

## Receipts

The receipts and their compressed elements, in the evaluator's format and
layout, are committed in
[`feature-models/receipts/`](../../model-based-product-line-engineering/feature-models/receipts/):
`pleml-feature-models.elements.json.xz` and one `<feature-model file
stem>.receipt.json` per feature model. The owner said yes to committing them
on 2026-10-19. Unlicensed CI re-runs the evaluator on the committed elements
and refuses a receipt that is stale by digest or does not reproduce. Each
receipt binds the documents of the bundle by digest, so a change to a
feature model, a configuration, a superset, the governed scope, the kernel,
the library or a catalogue makes it stale:

- when a document changes, the authority job writes fresh receipts into
  `authority/receipts/` of its evidence; commit those;
- when only the evaluator changes what it reports, the replay fails; refresh
  the receipts offline with
  `python scripts/run_pleml_configuration_evaluation.py refresh <receipt>...`.
  A refresh that would change a verdict, a derived variant or an admission
  writes nothing unless `--accept-verdict-changes` says so: such a change is
  a rollback trigger and needs a reviewed decision, never a silent rewrite.
  A code change that still reproduces every receipt only adds an advisory.

Both the job and the public CI sync and byte-check the fenced PLEML package
before the replay, which reads the installed library.

A receipt binds by content, never by a commit:

- the digest of every document of the bundle;
- the digest of the elements file and of its content;
- the pinned PLEML release;
- the evaluator's code record.

Its `provenance` names the commit of the licensed run whose bundle it was
written from. That record is informational only, because a rebase or a squash
merge may leave the commit unreachable. Authenticity does not rest on it:
every licensed run at a later head serializes afresh and requires the
committed elements to equal its own (`compare_with_committed`).

The unlicensed checks are
[`test_ple_authority_model.py`](../../tests/test_ple_authority_model.py)
(the fence, the catalogue restatement, the agreement and complement checks,
the closed world, admission, the bindings, correspondences and
configurations),
[`test_ple_authority_runner.py`](../../tests/test_ple_authority_runner.py),
[`test_ple_authority_workflow.py`](../../tests/test_ple_authority_workflow.py)
and [`test_ple_authority_receipts.py`](../../tests/test_ple_authority_receipts.py)
(the committed receipts: their files, digests, sources and verdicts, and
their offline replay).
They read the model text: the closed-world and admission checks evaluate the
stated semantics on it, and the other checks pin its shape. Licensed
validation is the validator, and the evaluator owns the semantics.

## Parity with the YAML path

From step S4 on, [`check_pleml_parity.py`](../../scripts/check_pleml_parity.py)
gates every step until the YAML retires at S7. The required public CI runs it
on the committed receipts and the YAML catalogues, without a licence. It
compares the two paths on the 25 rows of the plan:

- the 8 files of `feature-configurations/` with their PLEML configurations;
- the 10 probes of the retained PLE-S comparison, whose selections and names
  it freezes from `comparison.json`, pinned by digest;
- 7 closed-world probes: the four unsupported application-middleware pairs,
  one hand-picked adapter, and the two allowed pairs that no other row
  exercises, Openpilot with Eclipse S-CORE and Apollo without middleware.

A probe is a PLEML configuration in `fixtures/parity-probes/`, outside the
authority roots. A new configuration needs licensed serialization, so the
authority job serializes the probes into the receipts like the invalid
fixture. The YAML side of a probe is generated from the same frozen
selection, with the probe's description, outside the repository.

Each row compares the validity, the reason class, the derived variants, the
normalised projection body of a valid row and, where the retained record
holds the YAML-era verdict, admission. No invalid configuration may be
admitted, on any row. The receipt must also restate the row's selection
feature by feature, through the catalogue paths it records.
A row is `equal`, `both-reject`, `not-expressible` or `defect`.
`not-expressible` is only a construct on the pinned list that is the sole
YAML violation, with the remainder still compared. The list holds one
construct: the common vehicle-target AEBS capability switched off, in row
`ug-10-vehicle-target-aebs-false`. Every run requires the histogram of the
plan, 16 `equal`, 8 `both-reject`, 1 `not-expressible` and 0 `defect`.

The configurator reads the receipts with its existing writer:
`python tools/configure_variant.py --receipt <receipt> --configuration <name>`
replays the receipt and generates the projection of one valid configuration.
The parity requires each of the seven committed projections to have one
normalised body on all three sides: the committed file, the YAML path and the
receipt. Until the switch, the committed projections stay those of the YAML
path.

## Evidence records

The `evidence` block of a Bill-of-Features is not a feature selection. When
the Bills-of-Features retire, it moves to an external evidence record per
configuration, `feature-configurations/evidence/<file stem>.yaml`, with
today's schema and integrity rules. Until then it stays in the
Bill-of-Features.

## History

The PLE-S scope-alignment experiment is retired; these models supersede it.
Its record stays in [`ple-s-scope-alignment.md`](ple-s-scope-alignment.md).
