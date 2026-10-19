# ADR 0022: Adopt PLEML as the product-line authority

## Status

Proposed

## Context

[ADR 0014](0014-ratify-initial-aebs-product-line-scope.md) ratified the
initial AEBS product-line scope: two planned members and one admitted
variability, bound at Development. It kept the YAML catalogue, the bills of
features and `tools/configure_variant.py` operationally authoritative until a
separate migration decision. It kept PLEML exact-pinned and experimental, and
it asked a future PLEML feature model to start from the admitted variability
rather than restate the catalogue node for node.

[ADR 0006](0006-variant-selection-construct-and-ple-adequacy.md) made the YAML
decision layer the bridge between native SysML v2 variability and
feature-model semantics. The configurator derives the application-middleware
adapter from a rule table and rejects unsupported pairs and hand-picked
adapters.

The PLEML adoption gates have run:

- **PLE-Q.** Run `39167884450` recorded six cases on PLEML 1.1.0, observed
  but not qualified. Two are observed and four are gaps.
- **PLE-S.** Run `39169049300` compared 15 cases of the admitted scope with the
  configurator and found no defect.
- **Trial.** A scratch trial showed that PLEML can express a two-premise
  adapter condition as a check, but not as a derivation.
- **Upstream.** The maintainers answered three questions and released 1.0.0,
  1.1.0 and 1.1.1. Version 1.1.1 has the library of 1.1.0, and its Sysand
  package is byte-identical to its release tag.

Two capabilities are missing from PLEML and the toolchain:

- SysIDE 0.10.3 does not evaluate PLEML constraint bodies.
- PLEML defines no derivation: a feature configuration is either valid or
  invalid.

On 2026-10-19 the owner decided:

- to make PLEML the product-line authority, with DE4SDV owning evaluation and
  derivation;
- to migrate the full catalogue and every bill of features;
- to provision PLEML through Sysand;
- the rollback, release and sequencing rules that the
  [migration plan](../plans/2026-10-19-pleml-product-line-authority.md)
  records.

## Decision

1. **Authority.** PLEML is the representation and the configuration-validity
   authority of DE4SDV's feature models, feature configurations and
   feature-to-shared-asset bindings.
   - It is pinned as `pkg:sysand/mbse4u/pleml` `=1.1.1` through the committed
     Sysand lock, as [ADR 0007](0007-pin-sysmod-sysand-dependency.md) does for
     SYSMOD.
   - A CI step checks that the installed library is byte-identical to the
     release tag.
   - The authority takes effect at the switch step of the migration plan.
     Until then the YAML clause of ADR 0014 stays in force.
2. **Scope.** The migration covers the full SDV product-line catalogue,
   including its reference-only options, and the engineering and
   vehicle-target execution-environment catalogues. Each catalogue becomes its
   own feature model.
   - Every committed bill of features becomes a PLEML feature configuration,
     and the invalid fixture becomes a fixture configuration.
   - The governed scope of ADR 0014 stays the admission authority: a
     configuration can be valid without being admitted. Model-native
     correspondences from features to the governed scope decide admission.
3. **Evaluation.** DE4SDV evaluates configurations in a repository module that
   reads serializer and API objects only
   ([ADR 0011](0011-import-reviewed-sysml-baseline-into-api.md)). It checks:
   - multiplicities;
   - requires, XOR and implies, as the library defines them;
   - completeness and Development binding time;
   - that a configuration owns only features.

   It refuses unknown shapes and never reports native expression execution.
4. **Derivation and the closed world.**
   - A valid configuration derives the variants bound to its selected
     features.
   - The adapter rule table becomes model-native DE4SDV derivation rules,
     typed by a kernel definition. For each derived variation exactly one
     rule must match a valid configuration; with none or several, the
     configuration is rejected.
   - PLEML exclusions state the unsupported application-middleware pairs, and
     a CI check proves that the allowed pairs equal the pairs the rules cover.
   - The adapter remains a derived realization: never a feature, never a
     manual product choice.
   - No helper features and no implies pattern are introduced for adapters,
     because the derivation rules own them.
5. **Generation.** A licensed job writes a content-addressed evaluation receipt
   for each feature model. `tools/configure_variant.py` generates the
   product-model projections from the receipts, keeping its writer and
   mapping checks, and keeps the existing part-definition names.
6. **Migration and rollback.**
   - YAML parity gates every migration step. Every bill of features, the
     fixture and the probes must give the same verdict, reason class, derived
     variants and projection body.
   - The authority switches only once parity is complete.
   - The YAML path stays runnable as a shadow during the rollback window, and
     YAML is retired only after full parity has held through that window.
   - An annotated tag marks the last commit under YAML authority.
7. **Upstream releases.** DE4SDV takes a new PLEML release only through a
   reviewed re-pin and a re-qualification at an exact revision.
   - A release whose content is unchanged takes a fast path.
   - No new frozen-experiment commits are made.
   - Any of these blocks an upgrade: a parity or receipt regression, an
     unadapted constraint form, an unreviewed change to the configuration or
     constraint definitions, a package that differs from its tag, or a licence
     change.

### Superseded, amended and retained clauses

Superseded:

- ADR 0014:111 ("PLEML remains exact-pinned and experimental"), at the
  switch. PLEML stays exact-pinned.
- ADR 0014:114-115, the open XOR defect, which upstream fixed in 1.0.0.
- ADR 0014:140-142, the YAML authority, at the switch.
- ADR 0014:143-144, the admitted-variability starting point, by the owner's
  decision to migrate the full catalogue.
- ADR 0006:104-109, the YAML decision layer as the bridge.

Amended:

- ADR 0014:91. The adapter is a DE4SDV-owned derivation outcome, and the word
  "experimental" goes. "It is not a manual product choice" (:91-92) stays.
- ADR 0006:90-95. Projections are generated from evaluation receipts instead
  of bills of features.
- ADR 0006:110-116. The adapter rules move from the YAML catalogue to
  model-native derivation rules, under the same exactly-one rule.

Decided here, though left open earlier:

- ADR 0014:152-155;
- ADR 0006:144;
- wave-A decision 9 on configurator authority, which said "Revisit after
  the PLE migration".

Retained:

- ADR 0014:41-44, the governed scope as portfolio authority;
- ADR 0014:94-99. Reference-only options are configurable, as they are in
  the YAML catalogue today, and admitted only by a scope decision.
- ADR 0014:101-103. Engineering environments get their own feature model and
  remain outside System 1 product variability.
- ADR 0014:78-80 and :115-116;
- ADR 0006 decisions 1, 2 and 4.

Rewritten at the switch:

- `model-based-product-line-engineering/README.md:3-11, :27-36, :51-66`;
- the feature-model namespace note in `docs/naming/naming-conventions.md`,
  updated the same day the YAML is retired;
- the kernel texts in `de4sdv_product_line.sysml:86-125` and
  `de4sdv_method_concerns_and_viewpoints.sysml:150-174`, by separate method
  pull requests.

## Consequences

Benefits:

- **One source.** Features, configurations and bindings have a single SysML
  v2 source, served and traced with the rest of the model, and the YAML
  decision layer can be retired.
- **Phase 9.** INC-MW-011 phase 9 restructures the platform choices per
  domain once, in PLEML.
- **Reuse.** The configurator's tested projection writer and mapping checks
  are kept.

Costs and risks:

- **Owned semantics.** DE4SDV owns the evaluation and derivation semantics,
  so a defect there is DE4SDV's. Conformance cases are restated from the
  library's documented test verdicts.
- **Licensed loop.** A feature-model change needs licensed serialization.
  The committed receipts keep every other pull request unlicensed, but
  contributors can't regenerate them locally.
- **Young upstream.** There were three releases in three days, one of them
  breaking, from one active contributor. Exact pins and the release gate
  contain this.
- **Gaps.** Serializer identity is closed only for the concepts the authority
  consumes; the other qualification gaps stay recorded.
- **Kernel work.** The derivation rules and the configuration metadata need
  kernel definitions, delivered as method pull requests.
- **Two representations.** The YAML shadow and PLEML coexist until the rollback
  window ends. Rollback is one revert of the switch while the shadow exists.
  After that, rollback means restoring from the tag.

## Non-decisions

This ADR does not:

- admit a new member or change the governed scope;
- make engineering execution environments product variability;
- merge the governed scope's native variation with any PLEML feature model;
- use PLEML for the method, evidence or ontology vocabulary;
- ground further kernel identities on PLEML;
- claim native execution of PLEML constraint expressions;
- modify the frozen PLEML experiments or their tags; or
- make any safety, compliance, certification or homologation claim.

## Links

- [Migration plan](../plans/2026-10-19-pleml-product-line-authority.md)
- [ADR 0006: Variant-selection construct and PLE adequacy](0006-variant-selection-construct-and-ple-adequacy.md)
- [ADR 0007: Pin SYSMOD as a Sysand dependency](0007-pin-sysmod-sysand-dependency.md)
- [ADR 0011: Import the reviewed SysML baseline into the API](0011-import-reviewed-sysml-baseline-into-api.md)
- [ADR 0014: Ratify the initial AEBS product-line scope](0014-ratify-initial-aebs-product-line-scope.md)
- [PLE-S scope alignment](../product-line-engineering/ple-s-scope-alignment.md)
- [Governed product-line scope](../../model-based-product-line-engineering/scoping/de4sdv_aebs_product_line_scope.sysml)
- Wave-A decision 9: tag `release-2026-10-11`,
  `docs/method-conformance/o4/owner-decisions-2026-10.md`

Upstream references:

- PLEML: <https://github.com/MBSE4U/PLEML>
- Release 1.1.1: <https://github.com/MBSE4U/PLEML/releases/tag/v1.1.1>
- Sysand package: `pkg:sysand/mbse4u/pleml`
- Questions answered upstream: MBSE4U/PLEML issues 3, 4 and 5
