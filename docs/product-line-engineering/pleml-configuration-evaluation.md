# PLEML configuration evaluation

ADR 0022 makes PLEML the configuration-validity authority of the DE4SDV feature
models and leaves the evaluation to DE4SDV: PLEML defines no derivation, and the
pinned serializer does not evaluate constraint bodies. This page states what the
evaluator decides, the model shapes it accepts, and how its receipts are kept.
Nothing here is qualification or compliance evidence, and no PLEML expression is
ever executed natively.

## What it decides

`de4sdv/semantic/pleml_configuration.py` reads serializer and API element objects
only (ADR 0011). For each feature tree it decides:

- **features and groups.** A feature that sibling features subset is a group. Its
  multiplicity bounds the number of selected members: `[1]` means exactly one,
  `[1..*]` at least one.
- **configurations.** A setting `[1]` selects a feature and `[0]` deselects it. An
  omitted optional feature is deselected, and an omitted mandatory one is
  selected. Every bound of every feature and group is checked, as is that a
  configuration owns only features. As in the library, each selected feature
  binds no later than the configuration, which binds at Development: a
  later-bound feature rejects only the configurations that select it.
  Metadata, such as `ProductModelProjectionName`, annotates a configuration and
  is not one of its entries.
- **constraints.** `requires`, XOR and `implies` keep the library's semantics,
  read from the `FeatureOperand` operands.
- **feature bindings.** Each binding names one variant and one feature, and each
  variant is bound once. A bound variation has every variant bound, to the
  members of one exactly-one group. Bound features bind at Development, the
  projection owner owns the variation, and a derived variant is never bound.
- **derivation.** A `DerivedVariation` dependency names a shared-asset variation
  and its source groups, and each `DerivationRule` dependency names one variant
  and its premises. The agreement check is total over every source pair:
  exactly one rule or exactly one pair exclusion. A valid configuration derives
  exactly one variant per derived variation; no matching rule, or several,
  rejects it.
- **admission.** The governed scope of ADR 0014 stays the admission authority,
  so a valid configuration may still not be admitted. Admission requires
  validity: an invalid configuration is never admitted. Its admission record
  says why, and keeps what the correspondences of its features decide (see
  below).

## Admission

A correspondence is a dependency of the tree that carries no binding,
derivation or configuration role. Its one client is a feature, or the tree
definition for the whole family, and each supplier is an element the governed
scope classifies: an admitted alternative of Vehicle Platform Integration
Mode, common content, or a reference-only, deferred or excluded element. The
production scope validator reads that classification. A correspondence is
refused when a grouping feature is its client, or when it names an element the
scope does not classify or a derived realization, which corresponds to its
alternative instead.

A configuration is admitted when all of these hold:

- it is valid. An invalid configuration is not admitted, and the first reason
  of its admission record names its reason classes ("invalid configuration:
  ...");
- grouping features carry no admission, and a group feature's correspondence
  only classifies its variation point;
- every selected choice or leaf has a correspondence that is an admitted
  alternative or common content. One without a correspondence is not in the
  governed scope. A family correspondence counts for every configuration of
  its tree;
- the selection realizes exactly one admitted alternative, and in every group
  where a member corresponds to that alternative, it selects such a member;
- every choice or leaf that corresponds to a common element is selected. A
  choice is exempt where the alternative's derived realization selects another
  member of its group, because the feature model has one slot there. Common
  content no feature corresponds to is outside the selection surface.

On the feature models this admits the standalone and the AAOS-integrated
members. It admits neither the reference examples nor the two execution
environment families.

Identity follows ADR 0011:

- A library definition is recognised by its metatype, its declared name and the
  library's source document.
- A kernel definition is recognised only by the validated binding of its
  ontology class. `validate_ontology_bindings` binds the five classes of
  `de4sdv_product_line_derivation.sysml` by metatype, declared name and that
  file, as ingestion does.
- A same-named definition in another document is refused, not ignored.

## Accepted model shapes

The evaluator refuses anything outside these shapes:

- **trees.** A `#featureTree occurrence def` owns the features. The feature model
  names the definition through `#featureTree occurrence name : Definition :>
  featureTrees;`, a typed usage without a body. A tree usage that owns its
  features, the library's own form, is accepted too;
- **features.** Every tree feature carries `#feature` and an explicit
  multiplicity. Group members are `[0..1]` siblings of their group, and a member
  that is itself a group is refused. The only value a tree feature may carry is
  `default null`. A feature, and a setting, is typed by the library's `Feature`
  only, never by a product-line characteristic;
- **configurations.** A configuration is `#featureConfiguration occurrence name :
  Definition :> featureConfigurations`, typed by its tree definition, in a file
  of its own. One that subsets a tree usage with a body is accepted too, and one
  typed by no tree is refused. Settings state their multiplicity and
  may nest inside the setting of their owning feature. A group setting may list
  its selected members as its value, and the list must agree with the member
  settings;
- **constraints.** A constraint subsets or redefines exactly one of
  `requiresFeatures`, `xorFeatures` and `impliesFeatures`; the library declares
  each base with multiplicity `[*]`. Each named constraint is a constraint of its
  own and keeps its own short name. Its operands are `new FeatureOperand(A, B)`,
  and operand A of a requires or XOR constraint is its owner, either `that` or
  the owner itself;
- **metadata.** Metadata is read only where the annotated element owns it, as
  `#M` or `@M` inside its body. Consumed metadata placed with a package-level
  `about` annotation is refused, never ignored. A feature model carries
  `ProductModelProjection`, a configuration may carry
  `ProductModelProjectionName`, and a feature may carry `UnassignedBindingTime`,
  unless a binding, derived variation or rule names it. A feature that carries
  `UnassignedBindingTime` never redefines `bindingTime`;
- **derivation.** A `DerivedVariation` or `DerivationRule` dependency has exactly
  one client. Each premise of a rule is a direct sub-feature of a distinct source
  feature, and supplier order carries no meaning. A rule whose variant no single
  derived variation names is refused;
- **dependencies.** Every dependency of the model documents is read by exactly
  one feature tree, and none is skipped. A binding, derived variation, rule or
  correspondence with an empty endpoint list is refused. So is one that names
  no feature of a tree: a premise or source that is no feature, a binding of a
  derived variant, a correspondence from an element that is no feature. A
  correspondence needs the governed scope among the evaluated elements;
- **exports.** The production export's options are the accepted ones. Implied
  relationships carry nothing authored, so they are neither refused nor read.
  Document order comes from the ordered ownership properties, never from the
  order of the element list.

## Receipts

The licensed authority job serializes the PLEML models once, with the
production export's options, into one export bundle. Its source manifest names
every document, and marks the model documents with the roles
`pleml-feature-model`, `pleml-feature-configuration` and `pleml-fixture`. The
PLEML library carries the pinned package's path,
`pleml_package.LIBRARY_PATH`. The job then hands the bundle to one entry
point, the function `write_receipts` or the `receipts` command. It writes one
compressed elements file and one receipt per feature model. A receipt covers
its model's documents, and records the verdicts, the derived variants, the
admission and the input digests:

```bash
# The authority job, after its licensed serialization: write
# pleml-feature-models.elements.json.xz and <feature-model file stem>.receipt.json.
python scripts/run_pleml_configuration_evaluation.py receipts \
  --bundle "$RUNNER_TEMP/authority-elements.json" \
  --serializer-version 0.10.3 --executor-revision "$(git rev-parse HEAD)" \
  --out "$RUNNER_TEMP/pleml-receipts"

# Any machine: re-run the evaluator on the committed elements.
python scripts/run_pleml_configuration_evaluation.py replay <receipt>...

# Any machine: rewrite receipts from their intact elements when they no longer reproduce;
# a verdict, derived-variant or admission change needs --accept-verdict-changes.
python scripts/run_pleml_configuration_evaluation.py refresh <receipt>...
```

Every receipt binds the PLEML release the production lock pins: its version,
tag commit, path and digest. A bundle with another library is refused, and a
receipt refuses to replay when the library is missing or the package is
re-pinned. A bundle without the governed scope is refused too, because every
receipt records the admission. The run's provenance (the executor revision and
the bundle's commit) sits in the receipt beside the elements, never inside
them. So the same serialization on another commit gives the same elements file.
`pleml_receipts.compare_with_committed` is the comparison the licensed job runs
against the committed receipts.

A receipt never depends on where it was cut. References are element
identities: the resource path of a serializer URI depends on the checkout and
on where the library is provisioned, so the elements file keeps none, and a
bundle element that carries one is refused. A receipt cut on the licensed
runner replays the same in unlicensed CI and locally.

`replay` refuses a receipt in any of these cases:

- its elements differ from the recorded digest, even by an edit that changes
  no verdict;
- a source document changed after the serialization. The receipts of one
  bundle bind all of its sources, so one edited document makes them all stale;
- the pinned library is missing, or the package pins another release;
- its evaluation (verdicts, derived variants, admission) or its shadow does
  not reproduce byte for byte from the committed elements.

Reproduction is the only code check. A receipt records the digests of the
PLEML-owned code it was evaluated with (the evaluator, the receipts, the shadow,
the package record, the CLI and the configurator) as provenance. Shared
production modules stay outside that record. When other code still reproduces
the receipt, the receipt holds and `replay` reports the difference as an
advisory. When it does not, `refresh` rewrites the receipt from its intact
elements and records the new code. It lists every change of a configuration's
validity, reason classes, derived variants or admission, and writes nothing
when there is one unless `--accept-verdict-changes` says so: a verdict change
is a rollback trigger, never a silent rewrite. `pleml_receipts.replay_committed`
and `replay_receipts` return the failures as a list, empty when every receipt
holds, and the `replay` command calls them.

Replay works offline, so it cannot tell an edit that rewrites an elements file
and the digests of its receipts. The licensed comparison on every head that
carries receipts closes that gap, together with the review of the committed
diff.

`receipts --compare <directory>` refuses when the fresh elements differ from
the committed receipts' elements.

Until the YAML is retired, a receipt also carries these shadow checks, against
the catalogue with the feature model's file stem. `de4sdv/semantic/pleml_shadow.py`
computes them with the configurator's own parser:

- each feature's catalogue path, taken from its short name;
- the allowed-list complement check of C001, C002 and C003;
- the row-by-row comparison of the rules with the catalogue's rule table.

`de4sdv/semantic/pleml_receipts.py` holds the parity primitives:

- the normalised projection body, below the header and with only the
  writer's derivation-source line normalised;
- the writer inputs;
- the reason keys;
- the row classes `equal`, `both-reject`, `not-expressible` and `defect`. Two
  rejections are `both-reject` only with the same reason keys and, where both
  sides give them, the same multiset of located reasons.

Each reason of an evaluated configuration records where it applies, as data
beside its prose: `features`, the tree features it names, and for a
hand-picked derived variant `variations`, the derived variation it chooses.

`not-expressible` is limited to the pinned construct of row
`ug-10-vehicle-target-aebs-false`.
