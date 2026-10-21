# ADR 0022: Adopt PLEML as the product-line authority

## Status

Accepted

The owner took the decision on 2026-10-19. It takes effect at the switch,
step S6 of the
[migration plan](../plans/2026-10-19-pleml-product-line-authority.md). Until
then, the YAML authority of ADR 0014 stays in force.

> Note (2026-10-21): on 2026-10-21 the owner dropped the minimum of 30 days
> between the switch and the retirement of the YAML (OQ2 of the plan). The
> YAML retires at step S7 once all of these hold: the privileged ingestion and
> the deploy of S6 are green, the PLE-Q-style dispatch is green, one parity
> run on main is green, and no rollback trigger is open. Decision 6 is read
> with this change: its "at least 30 days" for the shadow and for the
> retirement no longer applies, and its other conditions stay. S7 retires the
> YAML catalogues, the Bills-of-Features, the YAML path of
> `tools/configure_variant.py`, the parity check and its shadow, and the
> comparison oracle with its retained record. The evidence status of the
> configurations moves to evidence records, and the `C-` common-capability
> node IDs retire. After S7 a rollback restores the YAML layer from the tag
> `pleml-yaml-authority-final`. The decision itself is unchanged.

## Context

[ADR 0014](0014-ratify-initial-aebs-product-line-scope.md) ratified the
initial AEBS product-line scope: two planned members and one admitted
variability, bound at Development. It also:

- kept the YAML catalogue, the bills of features and
  `tools/configure_variant.py` authoritative until a separate migration
  decision;
- kept PLEML exact-pinned and experimental;
- asked a future PLEML feature model to start from the admitted variability.

[ADR 0006](0006-variant-selection-construct-and-ple-adequacy.md) made the YAML
decision layer the bridge between native SysML v2 variability and
feature-model semantics. The configurator derives the application-middleware
adapter from a rule table. It rejects unsupported pairs and adapters chosen by
hand.

The PLEML adoption gates have run:

- **PLE-Q.** Run `39167884450` on PLEML 1.1.0 recorded six cases as observed,
  not qualified. Native constraint evaluation was not executed.
- **PLE-S.** Run `39169049300` compared 15 cases of the admitted scope with the
  configurator and found no defect.
- **Trial.** A scratch trial showed that PLEML can express a two-premise
  adapter condition as a check, but not as a derivation.
- **Upstream.** The maintainers answered three questions and released 1.0.0,
  1.1.0 and 1.1.1. Version 1.1.1 has the library of 1.1.0, and its Sysand
  package is byte-identical to its release tag.

PLEML defines no derivation: a feature configuration is either valid or
invalid. SysIDE 0.10.3 does not evaluate PLEML constraint bodies.

On 2026-10-19 the owner decided:

- to make PLEML the product-line authority, with DE4SDV owning evaluation and
  derivation;
- to migrate the full catalogue and every bill of features, including the two
  execution-environment catalogues;
- to provision PLEML through Sysand;
- the rollback, release and sequencing rules below.

## Decision

1. **Authority and provisioning.** PLEML is the configuration-validity
   authority of DE4SDV's feature models, feature configurations and
   feature-to-shared-asset bindings.
   - **Pin.** `pkg:sysand/mbse4u/pleml` `=1.1.1` (license MIT), through the
     committed Sysand lock, as [ADR 0007](0007-pin-sysmod-sysand-dependency.md)
     does for SYSMOD.
   - **Byte check.** A CI step compares the installed library with committed
     values:
     - tag commit `b694648cce4b96126eda2de3eb881c54397ae035`;
     - blob `8624fe1e29f9ac96299484f86dfb9a0725e48c2e`;
     - sha256
       `a3f23c2531272b4cab684f0f1d1a982a443f0a2cdca824cc893f4004980ae02c`.
   - **Confinement.** Only the feature-model packages and their fixtures
     import PLEML, and a CI guard enforces this. Two exceptions are allowed:
     - the PLE-S model, until S3 retires it;
     - the PLE-Q probe text that `scripts/run_ple_scoped_execution.py` writes.
2. **Scope.**
   - The migration covers the full SDV product-line catalogue, including its
     reference-only options.
   - It also covers the engineering and vehicle-target execution-environment
     catalogues and their three configurations, by the owner's decision of
     2026-10-19. Each catalogue becomes its own feature model.
   - Every committed bill of features becomes a PLEML feature configuration,
     and the invalid fixture becomes a fixture configuration.
   - Common capabilities are not features. The catalogue's `C-` nodes become
     common content, with no PLEML feature and no new model element. Until S7,
     the parity check maps them to the governed common elements.
   - The governed scope of ADR 0014 stays the admission authority: a
     configuration can be valid without being admitted.
3. **Evaluation and identity.**
   - **Module.** DE4SDV evaluates configurations in a repository module that
     reads serializer and API objects only
     ([ADR 0011](0011-import-reviewed-sysml-baseline-into-api.md)). It checks:
     - multiplicities;
     - requires and XOR constraints, and implies once one is modeled, as the
       library defines them;
     - completeness and Development binding time;
     - that a configuration owns only features;
     - the integrity of the bindings.
   - **Identity.** It recognises PLEML and kernel definitions by API metatype,
     declaration name and serializer-recorded source document (the
     byte-checked library or a reviewed kernel file), or by a validated
     binding. It never recognises them by a name alone, or by a name in
     another document.
   - **After S6.** Variation and variant identity come from the evaluation
     receipt.
   - **Limits.** It refuses unknown shapes and never reports native expression
     execution.
4. **Derivation and the closed world.**
   - A valid configuration derives the variants bound to its selected
     features.
   - **Rules.** The adapter rule table becomes model-native DE4SDV derivation
     rules, typed by a kernel definition. For each derived variation exactly one
     rule must match a valid configuration. A configuration that matches none,
     or several, is rejected.
   - **Exclusions.** PLEML exclusions state the unsupported
     application-middleware pairs.
   - **Agreement check.** A CI check covers all pairs. It requires exactly one
     rule for each allowed pair and exactly one exclusion for each unsupported
     one. Each rule must have exactly one application premise and one
     middleware premise.
   - **Allowed lists.** C001 and C003 keep their allowed lists as reviewed
     source, and a CI check proves that each exclusion set equals its list's
     complement.
   - **Dropped rules.** C002 and C006 are dropped as constraints, because they
     never fire. Their rationale stays in the model, and the complement check
     also reads the list recorded in C002's rationale, so a new operating
     system option fails CI until C002 is re-assessed.
   - **Adapters.** The adapter remains a derived realization: never a feature,
     never a manual product choice. No helper features and no implies pattern
     are introduced for adapters now, because the derivation rules own them.
5. **Generation and receipts.**
   - A licensed job writes an evaluation receipt for each feature model,
     together with the serialized elements it evaluated.
   - Unlicensed CI re-runs the evaluator on those elements and refuses a stale
     receipt by digest.
   - `tools/configure_variant.py` generates the product-model projections from
     the receipts with its existing writer, and keeps the existing
     part-definition names.
6. **Migration, rollback and phase 9.**
   - **Parity.** From step S4 on, YAML parity gates every step. Every bill of
     features, the fixture and the probes must give the same verdict, reason
     class, derived variants and normalised projection body. The only
     exception is a row on the plan's pinned `not-expressible` list. The steps
     before S4 change no YAML input, configurator path or projection.
   - **Switch.** The authority switches only once parity is complete. An
     annotated tag marks the last commit under YAML authority.
   - **Shadow.** After the switch, the YAML path stays as a non-authoritative
     shadow for at least 30 days.
   - **Rollback triggers.** A rollback trigger is any of:
     - a parity defect on main;
     - a failed post-merge check of S6;
     - an evaluator or derivation defect that changes a verdict or a derived
       variant;
     - the owner's call.
   - **Rollback.** A rollback reverts S6 together with S5o. It needs its own
     privileged ingestion and deploy, because the served-model identity
     changes back.
   - **Retiring YAML.** It is retired only when three conditions hold:
     - the 30 days have passed;
     - at least one full-parity run on main after the switch is green;
     - no rollback trigger is open.
   - **Phase 9.** INC-MW-011 phase 9 waits for the switch and may start right
     after it. On a rollback, phase-9 content the YAML cannot express must be
     re-expressed or withdrawn.
7. **Upstream releases and contact.**
   - DE4SDV takes a new PLEML release only through a reviewed re-pin with
     bounded re-verification at an exact revision.
   - A release that changes only its version line or line endings takes a fast
     path; any other release takes the full path.
   - No new frozen-experiment commits are made.
   - Any of these blocks an upgrade:
     - a parity or receipt regression;
     - an unadapted constraint form;
     - an unreviewed change to the configuration or constraint definitions;
     - a package that differs from its tag;
     - a license change.
   - The maintainers are informed after the switch, in a note that explains
     the derivation-rule approach, with text the owner approves.
8. **Ontology and evidence status.**
   - **Ontology PR (S5o).** A method and ontology pull request decides the
     post-switch classification of `FeatureConfiguration`, the four selection
     relations and `variesAt`.
     - It needs the owner's yes.
     - S5o and S6 merge as one gate: S5o directly before S6, with no ingestion
       or deploy between them.
     - S6's gate requires S5o.
   - **Evidence status.** The kernel gets no evidence-status type.
     Configuration evidence status stays an external typed reference until
     the ontology review's `decision-4` (the EvidenceStatus split) is decided.

### Clause changes

Clauses are quoted. The step that rewrites a text is named in brackets.

**Superseded:**

- ADR 0014: "PLEML remains exact-pinned and experimental." [S6] PLEML stays
  exact-pinned.
- ADR 0014: "No interpretation is upstream-confirmed." and "The suspected
  `xorFeatures` / `XORConstraint` defect remains unresolved." [S0] Both are
  overtaken: upstream answered the questions and fixed XOR in 1.0.0.
- ADR 0014: "The current YAML catalogue, feature configurations, and
  configurator remain operationally authoritative and unchanged until a
  separate migration decision." [S6]
- ADR 0014: "A future PLEML feature model must begin with the one admitted
  product variability rather than reproducing the current catalogue
  node-for-node." [S0, by the owner's decision on scope]
- ADR 0006 decision 5, the YAML decision layer that "bridges that boundary".
  [S6]
- ADR 0006 consequences on "the external configuration decision layer", and
  "A derived technical variation is reviewable in the feature catalogue".
  [S6] The derivation rules carry it instead.
- ADR 0021 link: "external selection authority, which the kernel guard
  keeps". [S6]
- Wave-A decision 9: "Keep the external catalogue authority (ADR 0006) …
  Revisit after the PLE migration." [S6]

**Amended:**

- ADR 0014: "The adapter remains a DE4SDV-defined experimental derivation
  outcome." The word "experimental" goes. "It is not a manual product
  choice." stays.
- ADR 0014: "The following are derived from Vehicle Platform Integration Mode
  and are not independently selectable product features". This stays as an
  admission rule. The catalogue configures operating system, hypervisor and
  middleware, as it does today, and admission classifies them as derived
  realizations. The adapter stays non-selectable.
- ADR 0014: "They become selectable only after a future reviewed scope
  decision admits a planned member". This stays, read as "admitted".
  Reference-only options are configurable, as today, and the non-decision
  "make Apollo or another reference alternative selectable" keeps that
  reading.
- ADR 0006 decision 3. Projections are generated from evaluation receipts, not
  from bill-of-features YAML. [S6]
- ADR 0006 decision 6. `derived_asset_selections` becomes model-native
  derivation rules under the same exactly-one rule. [S3, effective at S6]
- ADR 0011 import scope ("the pinned SysML library sources required to resolve
  those documents"). The PLEML library and the feature models join it. [S6]

**Decided here, though left open earlier:**

- ADR 0014 non-decisions on a production PLEML feature tree, on production
  migration, on retargeting the configurator and on retiring the YAML
  authority.
- ADR 0014 non-decisions "contact PLEML maintainers" (decision 7) and "resolve
  the suspected PLEML XOR defect" (resolved upstream).
- ADR 0006 non-decision "choose a production PLE tool", for the
  feature-model representation.
- ADR 0006 non-decision "define a full SysML v2 configuration-resolution
  metamodel", in part: kernel definitions for derivation rules and
  configuration metadata only. [S2k]

**Retained:**

- ADR 0014: the governed scope model as the portfolio authority.
- ADR 0014: "Driving Stack becomes genuine product variability" once a
  governed Apollo member is accepted.
- ADR 0014: "System 2 engineering environments … remain outside System 1
  product variability"; their feature model is not product variability.
- ADR 0014: "Future upstream clarification or a new PLEML pin triggers
  bounded re-verification before an affected claim is used."
- ADR 0006 decisions 1, 2 and 4.
- ADR 0021 decision 1 (S2k is its method pull request) and decision 4 (the
  feature model covers variability only).
- Ontology rule R001 and the kernel rule that common capabilities are not
  features unless they distinguish member products.

**Rewritten:**

- [S3]
  - The feature-model namespace note in
    `docs/naming/naming-conventions.md`, once `F-`, `D-` and `PL-` IDs become
    SysML short names.
  - The product-line README paragraph and the `docs/repository-tree.md` row
    that name the PLE-S experiment, which S3 retires.
- [S5o]
  - The register rows of `FeatureConfiguration`, `appliesToMemberProduct`,
    `selectsFeature`, `includesCommonCapability` and `selectsVariant`, all
    "external-reference: Bill-of-Features YAML", and the review decision
    `decision-9`.
  - The `native-grounding-admission.yaml` exclusions for those five and
    `variesAt`.
  - The guard test `tests/test_vocabulary_roles.py`.
  - The kernel comment that "Bill-of-Features contents and
    catalogue/configurator authority remain external. No PLEML adoption".
  - The vocabulary-role comments that say "selection authority stays with the
    external catalogue (ADR 0006)" or "no PLEML dependency".
  - The method concern and viewpoints that name "the feature catalogue and
    bill-of-features" or the YAML as the "source of truth".
  - These change the served-model `sai-` identity, which is why S5o and S6
    form one gate and the switch needs a fresh privileged binding.
- [S6]
  - The governed scope model's "does not replace the current YAML
    configuration authority", and `scoping/README.md`.
  - The product-line, product-model, feature-model and feature-configuration
    READMEs.
  - The validation scope in `AGENTS.md`.
  - The "three external Sysand dependency sources" check in
    `.github/workflows/deploy-public-sysml-api.yml`.
  - At S6 ADR 0014 gets a marked partial-supersession note and stays
    `Accepted`, and ADR 0006 gets a note.
- [S7] Remaining YAML references.

## Consequences

Benefits:

- **One source.** Features, configurations and bindings have a single SysML
  v2 source, served and traced with the rest of the model, and the YAML
  decision layer can be retired.
- **Phase 9.** INC-MW-011 phase 9 restructures the platform choices per
  domain once, in PLEML.
- **Reuse.** The configurator's tested projection writer is kept.

Costs and risks:

- **Owned semantics.** DE4SDV owns the evaluation and derivation semantics,
  so a defect there is DE4SDV's. Conformance cases are restated from the
  library's documented test verdicts.
- **Licensed loop.** A feature-model change needs licensed serialization.
  The committed receipts and elements keep every other pull request
  unlicensed, but contributors can't serialize a new configuration locally.
- **Young upstream.** There were three releases in three days, one of them
  breaking, from one active contributor. Exact pins, confinement and the
  release gate contain this.
- **Gaps.** Serializer identity is closed only for the concepts the authority
  consumes; the other PLE-Q gaps stay recorded.
- **Kernel work.** The derivation rules and the configuration metadata need
  kernel definitions, delivered as method pull requests. The ontology
  classification needs its own pull request.
- **Production change.** The switch changes the served-model identity, so it
  needs a privileged ingestion and a deploy, and so does a rollback.
- **Two representations.** The YAML shadow and PLEML coexist for at least 30
  days after the switch. While the shadow exists, a rollback reverts S6
  together with S5o. After that, rollback means restoring from the tag.

## Non-decisions

This ADR does not:

- admit a new member or change the governed scope;
- make engineering execution environments product variability;
- merge the governed scope's native variation with any PLEML feature model;
- use PLEML for the method, evidence or ontology vocabulary;
- decide the post-switch ontology classification or grounding of
  `FeatureConfiguration`, the selection relations or `variesAt` (S5o does);
- decide the ontology review's `decision-4` on evidence status;
- claim native execution of PLEML constraint expressions;
- modify the frozen PLEML experiments or their tags; or
- make any safety, compliance, certification or homologation claim.

## Links

- [Migration plan](../plans/2026-10-19-pleml-product-line-authority.md)
- [ADR 0006: Variant-selection construct and PLE adequacy](0006-variant-selection-construct-and-ple-adequacy.md)
- [ADR 0007: Pin SYSMOD as a Sysand dependency](0007-pin-sysmod-sysand-dependency.md)
- [ADR 0011: Import the reviewed SysML baseline into the API](0011-import-reviewed-sysml-baseline-into-api.md)
- [ADR 0014: Ratify the initial AEBS product-line scope](0014-ratify-initial-aebs-product-line-scope.md)
- [ADR 0021: Model elements earn their place](0021-make-model-elements-earn-their-place.md)
- [PLE-S scope alignment](../product-line-engineering/ple-s-scope-alignment.md)
- [Governed product-line scope](../../model-based-product-line-engineering/scoping/de4sdv_aebs_product_line_scope.sysml)
- Wave-A decision 9, archived at the release tag:
  <https://github.com/de4sdv/DE4SDV/blob/release-2026-10-11/docs/method-conformance/o4/owner-decisions-2026-10.md>

Upstream references:

- PLEML: <https://github.com/MBSE4U/PLEML>
- Release 1.1.1: <https://github.com/MBSE4U/PLEML/releases/tag/v1.1.1>
- Sysand package: `pkg:sysand/mbse4u/pleml`
- Questions answered upstream: MBSE4U/PLEML issues 3, 4 and 5
