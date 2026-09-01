# PLEML Gate A spike

This directory is a bounded representation and API-observability spike. It is
not the DE4SDV product-line scope, feature authority, or a production
configuration model.

## Boundary

Gate A tests only whether pinned PLEML and a small realization-rule extension
survive this chain:

```text
SysML v2 / PLEML
→ official parser and minimal JSON serializer
→ immutable SysML API revision
→ revision-bound DE4SDV semantic repository
→ deterministic validation and realization resolution
→ synthetic SysML projection
```

The fixture must not be used to classify AEBS or any other production
capability as common or variable. Existing YAML feature/configuration authority
is unchanged.

The exact PLEML source is included as the `external/pleml` Git submodule pinned
to commit `5f8ab8560219dc24d8ec7ec90d6f0a145896ef8e`.

## Representations under test

1. **Pinned PLEML `FeatureBinding`:** adequate for one asset-to-feature
   dependency, not for a two-feature Boolean condition. Multiple bindings are
   never interpreted as conjunction.
2. **Native SysML constraint expression:** the fixture includes a formal
   application-and-middleware implication probe so the official serializer/API
   shape can be inspected. It is not selected as the executable rule table
   because binding reusable rules to configuration state would require an
   expression interpreter outside the current semantic repository.
3. **Narrow DE4SDV `AdapterRealizationRule`:** a synthetic occurrence definition
   with governed typed-reference roles for required application, required
   middleware, and optional resulting adapter. Both condition roles are
   mandatory and matched conjunctively by API UUID. A matched rule with no
   resulting adapter explicitly means no adapter is required.

Configuration validity is evaluated before realization. A PLEML
`xorFeatures` incompatibility stops derivation. A valid configuration then
resolves to exactly one rule, no rule, or multiple rules.

## At-least-one / multi-select group

The feature tree includes a `sensorSuite[1..*]` group whose members `radar`
and `camera` are independent optional features specializing the group. Three
configurations prove the semantics through the API path:

- `validBothSensors`: both members resolve (multi-select);
- `validOneSensor`: exactly one member resolves (at-least-one);
- `invalidNoSensor`: no member resolves; the evaluator fails closed with
  `configuration-invalid` semantics and no derivation attempt.

Group membership is resolved through Subsetting relationships by UUID, and
multiplicity bounds are resolved from both observed official-serializer range
shapes (direct literal bounds and the `..` operator expression whose
parameters carry the bound literals). Bound order is derived
order-independently because the serializer does not guarantee that
parameter order matches textual bound order.

## Observability matrix: adequacy vs. observability

Every matrix row records the full API shape evidence: metatype, UUID,
ownership path, reference paths with endpoint UUIDs, resolved multiplicity
bounds, and source provenance. Adequacy is a stronger claim than existence:

- **object observable** — the concept's API element exists with provenance;
- **semantically adequate** — a concept-specific fail-closed check proves the
  required semantics (endpoint UUIDs, membership paths, multiplicity values,
  redefinition chains) on the exact serialized graph.

Rows without a dedicated semantic check are marked `GAP` with
"no concept-specific semantic check proven this row adequate"; they are
observable but not yet semantically proven. Concepts with dedicated checks:
exact-one and optional multiplicity, the at-least-one/multi-select group
(identity, membership, multiplicity, and both resolution configurations),
the `requiresFeatures` and `xorFeatures` constraint chains (source-scoped
base usage, fixture redefinition, excluded-feature UUID), `FeatureBinding`
dependency endpoints, and variant membership. Real common/variable portfolio
classification is Gate C work; the fixture only demonstrates the "common
capability outside feature tree" evidence concept.

## Evidence

The `Privileged PLEML Gate A Evidence` workflow performs the licensed path and
uploads:

- official serialized element bundle and source manifest;
- immutable API project/commit binding;
- complete observability matrix with metatypes, property paths, sources, and
  UUIDs;
- all five required semantic outcomes;
- generated projection with configuration, rule, adapter, Git, and API revision
  trace identities;
- API service log.

Run the local non-licensed checks with:

```bash
python -m pytest \
  tests/test_pleml_adapter_rule_api.py \
  tests/test_pleml_api_observability.py -q
python scripts/check_repo.py
python scripts/smoke_test.py
```

The local AArch64 host cannot execute the available Syside binary. Parser,
serializer, API round-trip, and projection validation therefore remain
privileged exact-head evidence, not simulated local results.
