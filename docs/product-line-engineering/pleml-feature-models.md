# PLEML feature models and configurations

**Status:** the product-line authority of
[ADR 0022](../architecture-decisions/0022-adopt-pleml-as-product-line-authority.md)
since its switch (step S6). Nothing here is qualification, adoption evidence
or a compliance claim; every record says `qualified: false`.
**Decision authority:** Orkun Yilmaz, DE4SDV technical lead and maintainer.

These models restate the YAML catalogues and every Bill-of-Features with the
exact-pinned PLEML library. PLEML is the configuration-validity authority of
the feature models, the configurations and their bindings, and DE4SDV
evaluates the configurations and derives their variants. The YAML catalogues,
the Bills-of-Features and the YAML path of `tools/configure_variant.py` were a
non-authoritative shadow from the switch until they retired at step S7. The
rollback tag `pleml-yaml-authority-final` keeps them as they were before the
switch, and the Git history keeps the versions that S7 deleted.

## What the models contain

| Family | Feature model | Configurations |
|---|---|---|
| SDV product line | [`sdv_product_line.sysml`](../../model-based-product-line-engineering/feature-models/sdv_product_line.sysml) | the four SDV configurations, plus the invalid fixture and the 17 parity probes under `fixtures/` |
| Engineering execution environments (System 2) | [`engineering_execution_environments.sysml`](../../model-based-product-line-engineering/feature-models/engineering_execution_environments.sysml) | `inc_aebs_009a_jetson.sysml`, `apple_silicon_macos_candidate.sysml` |
| Vehicle-target execution environments (System 1) | [`vehicle_execution_environments.sysml`](../../model-based-product-line-engineering/feature-models/vehicle_execution_environments.sysml) | `nxp_zephyr_vehicle_target_candidate.sysml` |

Each feature model is a `#featureModel` definition whose feature tree is a
`#featureTree` definition. Each configuration is a `#featureConfiguration`
typed by that tree, in its own file with the stem of its retired
Bill-of-Features in snake case, so the fixture can stay outside the authority
roots. The parity probes never had a Bill-of-Features (see
[The parity probes](#the-parity-probes)).

How the catalogue was restated:

- **IDs.** Every `F-` and `PL-` ID is the SysML short name of its feature or
  tree, and every constraint ID that of its constraint.
- **Common content.** A `C-` common-capability node has no feature and no
  element: features distinguish member products. Pedestrian and bicycle
  detection therefore sit directly under the capabilities feature.
- **Structure.** A mandatory grouping node becomes a `[1]` feature that holds
  its variation points; an alternative group a `[1]` feature whose `[0..1]`
  choices subset it; the perception sensors a `[1..*]` group; an optional
  capability a `[0..1]` feature. Every feature keeps the Development binding
  time; the five capabilities with an unassigned binding time carry
  `#UnassignedBindingTime`.
- **Exclusions.** C001 and C003 (allowed lists) and C004 and C005 become
  exclusions. C002 and C006 never fire in any structurally valid selection,
  so they are dropped as constraints; their rationale stays in the model.
  The execution-environment constraints become requires constraints.
- **The two sides of one SoC** (INC-MW-011 phase 9, owner decisions of
  2026-10-21 and 2026-10-22). The platform has a main side, the execution
  domain that runs the vehicle application (`operatingSystem`), and an
  optional guest side under the hypervisor: the groups `guestOperatingSystem`
  {`guestAndroid`, `noGuestOperatingSystem`} and `guestMiddleware`
  {`guestAndroidSDV`, `noGuestMiddleware`}. Each none choice is named
  `no<Group>`, like `noMiddleware` and `noHypervisor` (owner decision of
  2026-10-25). With KVM the main side is the KVM host. The `middleware` group
  is the middleware that the vehicle application integrates with, so its
  eight derivation rules stay. The optional capability `hmiDisplay` has no
  shared asset yet. Five requires constraints relate the sides: C007
  `noHypervisor` requires `noGuestOperatingSystem`, C008 `guestAndroidSDV`
  requires `guestAndroid`, C009 `androidSDV` requires `guestAndroidSDV`, C010
  `hmiDisplay` requires `guestAndroidSDV` and C011 `autoware` requires
  `linux`.
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
application and one middleware premise. Until S7 the rule table was also
compared with the catalogue's row by row. A configuration that matches no
rule or several is rejected.

The allowed lists of C001 and C003 stay the reviewed source in the rationale
of their exclusions, and C002's list in its rationale comment. The complement
check proves that each exclusion set equals the complement of its list over
the current main-side operating-system options, so a new option fails CI
until the rules are re-assessed. C002's list names every main-side option:
the AAOS SDV partner runs in the guest (C009). The requires constraints C007
to C011 state their rules exactly, so they need no allowed list. A later
guest operating system, for example, falls under C007 with no edit.

A test also evaluates the closed world: for every structurally valid
selection of each feature model, it pins the verdicts that the model's
groups, exclusions, requires constraints and derivation rules give:
validity, the constraint IDs and the derived adapter. Structurally invalid
selections are outside the enumeration, because an exclusion presumes the
exactly-one structure of its group.

The pinned counts are a reviewed table. Until S7 the test required the
verdicts to equal the configurator's on the YAML catalogue, selection by
selection. The two-sided platform of INC-MW-011 phase 9 changed the SDV
table. Since then, the test computes the table with its lexical model of the
model text only. On 2026-10-22, in the phase-9 review, a one-off run of the
DE4SDV evaluator over a hand-built synthetic mirror of the tree (revision
1fb1250f) agreed with the table selection by selection. That run is not in
the repository, and CI does not repeat it.

| Feature model | Structurally valid selections | Valid | Verdict classes |
|---|---|---|---|
| SDV product line | 129,024 | 16,016 | 78 |
| Engineering execution environments | 27 | 3 | 10 |
| Vehicle-target execution environments | 8 | 2 | 7 |

The 16,016 valid SDV selections are 143 valid platform and display
selections, each with the 112 choices of the sensors and the four other
capabilities, which no constraint names. Each valid selection derives
exactly one adapter, and all eight derivation rules stay reachable.

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
  A choice is exempt only where the realized alternative selects another
  member of its group. Since INC-MW-011 phase 9 no member needs that
  exemption: both run Autoware on Linux on the main side, and the guest
  choices carry the split topology of the AAOS-integrated alternative.
  Common content without a feature is part of every member.

So the two governed members of ADR 0014 are admitted: the standalone member
(`aebs_autoware_linux_lidar_camera`) and the AAOS-integrated member
(`middleware_autoware_aaos_sdv_reference`). The two reference configurations
(Eclipse S-CORE, `middleware_autoware_score_reference`, and Apollo on QNX)
are not admitted. Neither is any
configuration of the two execution-environment families: the engineering
family is the excluded System 2 concern, and the vehicle-target family is
the deferred vehicle runtime variability. A test computes these verdicts from
the model. The evaluator of step S2 owns the verdict.

## Features that distinguish no member yet

Ontology rule R001 asks every feature to distinguish at least one member
product from another. These features restate catalogue options that no
configuration of their family selects, or that every one selects:

| Family | In every configuration | In no configuration | In no governed member yet, with no governed-scope element |
|---|---|---|---|
| SDV product line (4 configurations) | LiDAR | Openpilot, AUTOSAR Adaptive, main-side Android, ACRN, and the four capabilities of the catalogue | the HMI display |
| Engineering execution environments (2) | none | the Intel x86-64 nested-KVM host, the x86-64 Linux AOSP build, and nested-KVM Cuttlefish | none |
| Vehicle-target execution environments (1) | NXP compute, Zephyr and native Zephyr | the three "no concrete" choices | none |

The HMI display (INC-MW-011 phase 9) is an option that no governed member
selects yet: of the four configurations, only the Eclipse S-CORE reference
configuration selects it, and that configuration is not admitted. No shared
asset implements the display yet, so no feature binding resolves it. Like the
sensing and the other capability selections, each projection lists it among
the selections that SysML does not resolve.

They stay features. The migration restates the full catalogue, reference-only
options included (owner decision O1 of the plan), and a family with one
configuration can distinguish nothing. The ontology classification of ADR 0022
decision 8 keeps R001 on the ontology `Feature`, the kernel
`ProductLineFeatureCandidate`: a feature of a PLEML feature model is a
distinct element, a configurable option of the catalogue. The grouping and
group features are structure, not member distinctions.

## The production surface

Since the switch the feature models and the member configurations are model
roots: they are reviewed export roots of the API baseline, validation roots,
viewer roots and roots of the served model's drift gate, and the method check
and the licensed validation run on them. The PLEML library is a pinned
dependency of the API baseline ([provisioning](pleml-provisioning.md)). The
fixtures under `feature-configurations/fixtures/` (the invalid configuration
and the parity probes) are read by no production selector: the export, the
served model and its drift gate, the licensed validation, the repository and
naming checks and the viewer leave them out, and the authority job validates
and serializes them. Only the feature models, their configurations, the
fixture and the parity probes import PLEML.

## The authority job

[`privileged-ple-authority.yml`](../../.github/workflows/privileged-ple-authority.yml)
runs on pull requests that touch these models, their runner, their tests,
the PLEML pin, the committed receipts or the documents the receipts bind
(same-repository, allowlisted authors), and on maintainer dispatch. On the
exact head it:

1. installs PLEML 1.1.1 with the production Sysand lock
   ([provisioning](pleml-provisioning.md)) and byte-checks it against the
   committed record of its release tag before any step reads it;
2. runs the unlicensed model, runner and workflow tests;
3. validates the model roots, the PLEML files among them, and the fixtures
   with the licensed `syside check`;
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
   re-evaluates them from those elements and requires the evaluation to
   reproduce byte for byte, which catches an edited verdict over genuine
   elements. A code-identity difference is recorded as an advisory, not a
   failure;
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
feature model, a configuration, a superset, the governed scope, the kernel or
the library makes it stale:

- when a document changes, the authority job writes fresh receipts into
  `authority/receipts/` of its evidence; commit those;
- when only the evaluator changes what it reports, the replay fails; refresh
  the receipts offline with
  `python scripts/run_pleml_configuration_evaluation.py refresh <receipt>...`.
  A refresh that would change a verdict, a derived variant or an admission
  writes nothing unless `--accept-verdict-changes` says so: such a change is
  a rollback trigger and needs a reviewed decision, never a silent rewrite.
  A code change that still reproduces every receipt only adds an advisory.

Both the job and the public CI sync and byte-check the pinned PLEML package
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
(the production surface, the shape of the feature models, the agreement and
complement checks, the closed world, admission, the bindings, correspondences
and configurations),
[`test_ple_authority_runner.py`](../../tests/test_ple_authority_runner.py),
[`test_ple_authority_workflow.py`](../../tests/test_ple_authority_workflow.py)
and [`test_ple_authority_receipts.py`](../../tests/test_ple_authority_receipts.py)
(the committed receipts: their files, digests, sources and verdicts, and
their offline replay).
They read the model text: the closed-world and admission checks evaluate the
stated semantics on it, and the other checks pin its shape. Licensed
validation is the validator, and the evaluator owns the semantics.

## The configurator

The configurator writes the projections from the receipts:
`python tools/configure_variant.py --receipt <receipt> --configuration <name>`
replays the receipt and generates the projection of one valid configuration
of the served model. It labels each selection outside the projection by its
PLEML feature path, and the members of a group by their feature names. It
refuses to project a fixture (exit 2); `--check-only` reports a fixture's
verdict. Each of the seven committed projections regenerates from its
receipt byte for byte. The public CI replays every committed receipt
(`python scripts/run_pleml_configuration_evaluation.py replay ...`).
A projection is a derived product model, and an increment can complete it in a configured product ([product models](../../model-based-product-line-engineering/product-models/README.md#derived-product-models-and-configured-products)).

## The parity probes

`fixtures/parity-probes/` holds 17 PLEML configurations, outside the
authority roots. Ten restate the probe selections of the retired PLE-S
record, and seven probe the closed world: the four unsupported
application-middleware pairs, one hand-picked adapter, and the two allowed
pairs that no other configuration exercises, Openpilot with Eclipse S-CORE
and Apollo without middleware. Since INC-MW-011 phase 9 every probe but the
one with no integration mode selects a guest side: the two AAOS SDV pair
probes put the partner in a guest under KVM, and the mixed derived-set probe
mixes no middleware with an AAOS SDV guest. A new configuration needs
licensed serialization, so the authority job serializes the probes into the
receipts like the invalid fixture, and
[`test_ple_authority_receipts.py`](../../tests/test_ple_authority_receipts.py)
pins the verdict of each.

From step S4 to step S7 the parity check (`scripts/check_pleml_parity.py`)
compared the receipts with the YAML path on 25 rows: the 8 files of
`feature-configurations/` and the 17 probes. Each row compared the validity,
the reasons, the derived variants and the normalised projection body, and
every run required the histogram of the plan: 16 `equal`, 8 `both-reject`,
1 `not-expressible` and 0 `defect`. The check, the YAML path it ran and the
retained PLE-S record whose probe selections it froze retired at S7. The
rollback tag `pleml-yaml-authority-final` keeps them as they were before the
switch, and the Git history keeps the versions that S7 deleted.

## Evidence records

The `evidence` block of a Bill-of-Features was not a feature selection.
Since the Bills-of-Features retired at S7, it is an evidence record per
configuration, `feature-configurations/evidence/<file stem>.yaml`, with the
configuration's file stem in kebab case. The records keep the schema of the
block (a status, plus artifacts with an id and a path) and its integrity
rules, which
[`test_configuration_evidence_records.py`](../../tests/test_configuration_evidence_records.py)
applies. Four configurations have one: the AAOS-integrated member and the
three execution-environment configurations.

## History

The PLE-S scope-alignment experiment is retired; these models supersede it.
Its record stays in [`ple-s-scope-alignment.md`](ple-s-scope-alignment.md).
