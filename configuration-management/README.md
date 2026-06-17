# Configuration Management

Baselines, change control, versioning, release evidence, and traceability.

## Baseline scope

DE4SDV baselines should identify which ASELCM layer they primarily concern:

- **System 1 baselines**: configured SDV product-line variants, feature selections,
  product models, architecture variants, interfaces, and variant evidence.
- **System 2 baselines**: engineering environment assets such as SysML v2 models,
  simulation assets, digital-twin definitions, evidence registers, toolchain
  assumptions, and reusable methods.
- **System 3 baselines**: governance, methodology, standards, upstream-reference,
  and toolchain-evolution decisions that shape System 2.

A baseline may span layers, but the affected layer should be explicit.

## Change-control expectation

Changes should preserve traceability from:

1. the System 3 decision or issue that motivates the change;
2. the System 2 engineering asset or process being changed; and
3. the System 1 feature, product-line asset, variant, or assurance concern being
   managed.
