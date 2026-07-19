# ADR 0006: SysML v2 variant selection construct and PLE adequacy

## Status

Proposed

## Context

DE4SDV models the SDV platform stack as a SysML v2 variability model (the
"150% model") and generates configured member products (the "100% model") from
Bill-of-Features YAML via `tools/configure_variant.py`.

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

Separately, this correction surfaces a conceptual tension between SysML v2's
modeling of configured products and ISO/IEC 26580 feature-based PLE:

- In industrial PLE (pure::variants, BigLever Gears), a configured product is a
  derived resolution produced on demand from decisions applied to the 150%
  model. It is not an authored design element and is not part of the design
  space.
- In SysML v2, a configured product is a first-class specialization — a `part
  def` that is structurally indistinguishable from a hand-designed architecture
  element. There is no native construct that marks an element as
  derived/regenerated rather than authored.

This is a SysML v2 adequacy finding relevant to DE4SDV's mission of challenging
SysML v2 adequacy for SDV product-line engineering.

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

3. **Generate configured products via the configurator, not by hand.** The
   generator emits the `part :>> <feature> = <feature>::<variant>;` pattern
   from Bill-of-Features YAML.

4. **Treat generated product models as a distinct artifact class.** They are
   committed to the repository for reference and reviewability, but are derived
   artifacts. Each carries a `DO NOT EDIT` header, a provenance comment naming
   the source Bill-of-Features and feature model, and is regenerable via
   `configure_variant.py`. They are not part of the authored design space.

5. **Capture the PLE adequacy gap as a finding, not a blocker.** SysML v2 has
   no native "configuration resolution" construct. DE4SDV bridges this with a
   generator, provenance headers, and review conventions. This is documented as
   an adequacy finding rather than hidden.

## Consequences

- Variant selection in DE4SDV SysML v2 models follows the OMG reference
  implementation pattern and passes licensed SysIDE validation.
- The `configure_variant.py` generator is the source of truth for configured
  product models. Hand-editing generated `.sysml` files violates the workflow.
- The PLE adequacy gap (SysML v2 lacks a native configuration-resolution
  construct) is an explicit DE4SDV finding. It may inform future methodology
  work, upstream SysML v2 feedback, or tooling proposals.
- Reviewers should distinguish authored model elements (150% model, feature
  definitions, layer definitions) from derived configured products (100%
  model) when assessing changes.
- This decision does not prevent future migration to a resolution-on-demand
  workflow where configured products are not committed at all.

## Non-decisions

This ADR does not:

- choose a production PLE tool (pure::variants, FeatureIDE, etc.);
- remove generated configured products from the repository;
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
