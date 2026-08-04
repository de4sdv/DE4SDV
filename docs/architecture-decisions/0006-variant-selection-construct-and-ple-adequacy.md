# ADR 0006: SysML v2 variant selection construct and PLE adequacy

## Status

Proposed

## Context

DE4SDV models the SDV platform stack as a SysML v2 variability model (the
"150% model") and generates a platform-stack projection for a configured member
product from Bill-of-Features YAML via `tools/configure_variant.py`. The
projection is a partial product model: it is not the complete member-product
specification.

The initial implementation selected variants in configured products using:

```sysml
part def ExampleLinuxSCOREVariant :> SDVPlatformStack {
    part vehicleApplication redefines autoware;   // ERROR
    part middleware redefines eclipseSCORE;        // ERROR
    ...
}
```

Licensed SysIDE validation rejects this with `reference-error: No Feature
named 'autoware' found` and `namespace-distinguishability` errors.

Per the OMG SysML v2 specification (§7.6.7 Variations and Variants):

> "Variants are usage elements. If the containing variation is a usage, then
> each of its variants implicitly subsets the variation usage."

A variant is therefore a nested subset usage of the variation point, not a
feature of the owning definition. `redefines` targets features of the owning
definition, so `redefines <variantName>` cannot resolve a variant. This is a
semantic error in the construct, not a tooling quirk.

The correct construct is documented in the OMG SysML v2 reference
implementation
(`Systems-Modeling/SysML-v2-Release`, `examples/Variability Examples/VehicleVariabilityModel.sysml`,
"100% Model" section):

```sysml
part vehicle4Cyl :> vehicleFamily {
    part :>> engine = engine::'4cylEngine';
    part :>> transmission = transmission::manualTransmission;
    part :>> sunroof = sunroof::withoutSunroof;
}
```

The pattern subsets the inherited variation-point feature (`:>>`) and assigns
the selected variant via the `variation::variant` qualified path.

The spec also shows how to model an absent/optional variant using multiplicity
`[0]` (e.g. `variant part withoutSunroof[0];`). DE4SDV's `variant part none;`
for the no-hypervisor case is corrected to `variant part none[0];`.

Separately, this correction clarifies a boundary between SysML v2 variability and
feature-based PLE:

- SysML v2 provides native variation/variant semantics and the `:>>` construct
  for resolving a selected variant in a specialized product model.
- SysML v2 does not provide a feature model, feature-configuration algebra,
  managed cross-model feature-to-asset links, or a lifecycle/provenance marker
  distinguishing generated product assets from authored design elements.

DE4SDV therefore uses the YAML Feature Catalogue and Bill-of-Features as the
configuration decision layer, then generates a reviewable SysML v2 product-model
projection. This is a SysML v2 adequacy finding relevant to DE4SDV's mission of
challenging SysML v2 adequacy for SDV product-line engineering.

## Decision

1. **Use the spec-correct variant-selection construct.** Configured products
   select variants by subsetting the inherited variation-point feature and
   assigning the variant via the qualified path:

   ```sysml
   part def ExampleLinuxSCOREVariant :> SDVPlatformStack {
       part :>> vehicleApplication = vehicleApplication::autoware;
       part :>> middleware = middleware::eclipseSCORE;
       part :>> osPlatform = osPlatform::linux;
       part :>> hypervisor = hypervisor::none;
   }
   ```

2. **Model absent variants with multiplicity `[0]`.** The no-hypervisor case
   uses `variant part none[0];` in the 150% model.

3. **Generate platform-stack product-model projections via the configurator, not
   by hand.** The generator emits the
   `part :>> <feature> = <feature>::<variant>;` pattern from Bill-of-Features
   YAML. It does not claim to resolve feature selections that have no mapped
   variable shared asset.

4. **Apply a DE4SDV generated-artifact policy.** Generated projections are
   committed for reference and reviewability, carry `DO NOT EDIT` and source
   baseline/content-hash provenance, and are regenerable via
   `configure_variant.py`. This is a DE4SDV governance choice, not a claim that
   all PLE product models must be immutable. A product-specific change must be
   either elevated to the shared assets/feature model or managed as an explicit
   member-product customization with its own traceability.

5. **Capture the actual PLE adequacy boundary as a finding.** SysML v2 supports
   variation/variant resolution, but does not natively supply the external
   feature-model and feature-to-asset traceability technology. DE4SDV bridges
   that boundary with the YAML decision layer, mapping metadata, provenance,
   generator, and review conventions.

6. **Derive technical variations from their driving feature choices.** A
   feature catalogue may declare `derived_asset_selections` for a mapped SysML
   variation that must not be selected independently in a Bill-of-Features.
   The configurator requires exactly one rule to match the declared source
   selections, rejects unsupported or ambiguous combinations, and verifies the
   derived variation and variant against the shared SysML model before emitting
   the configured projection.

## Consequences

- Variant selection in DE4SDV SysML v2 models follows the OMG reference
  implementation pattern. Licensed SysIDE validation remains a required
  independent gate; this ADR does not claim a passing validation result.
- The `configure_variant.py` generator is the source of truth for platform-stack
  product-model projections. Hand-editing generated `.sysml` files violates the
  workflow.
- The PLE adequacy boundary (SysML v2 lacks native feature-model algebra,
  managed feature-to-asset links, and generated-artifact provenance) is explicit.
  It may inform future methodology work, upstream SysML v2 feedback, or tooling
  proposals.
- Reviewers distinguish authored shared assets (150% model), the external
  configuration decision layer, and derived platform-stack projections when
  assessing changes.
- Capability feature selections are not evidence of a derived capability model
  until DE4SDV maps them to variable shared assets and resolves them.
- A derived technical variation is reviewable in the feature catalogue and
  generated projection, while the Bill-of-Features remains limited to its
  driving product choices. A syntactically valid but unrealizable feature pair
  is rejected instead of yielding a product with an omitted adapter.

## Non-decisions

This ADR does not:

- choose a production PLE tool (pure::variants, FeatureIDE, etc.);
- remove generated platform-stack projections from the repository;
- define a full SysML v2 configuration-resolution metamodel;
- claim that SysML v2 variability is sufficient for full feature-model algebra
  (it is not — see the external feature-tree YAML for mandatory/optional/
  alternative/or-group semantics and cross-tree constraints); or
- affect the 150% model's variation/variant definitions, which remain native
  SysML v2.

## Links

- OMG SysML v2 Specification, §7.6.7 Variations and Variants
- OMG SysML v2 Specification, Annex A.12 Variability
- Reference implementation:
  `Systems-Modeling/SysML-v2-Release` → `examples/Variability Examples/VehicleVariabilityModel.sysml`
- [ADR 0004: Adopt ASELCM three-system framing](0004-adopt-aselcm-three-system-framing.md)
- [SDV platform stack model](../../textual-notation-of-model/packages/architecture/sdv_platform_stack.sysml)
- [PLE configurator](../../tools/configure_variant.py)
