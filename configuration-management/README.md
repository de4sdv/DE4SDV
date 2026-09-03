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

## Versioning and releases

DE4SDV uses semantic `vMAJOR.MINOR.PATCH` tags. While the project is below
`v1.0.0`, minor releases may change model, API, or workflow contracts; release
notes must call those changes out. Patch releases contain compatible repairs,
documentation corrections, or evidence refreshes that do not redefine the
declared baseline contract.

A GitHub milestone is a planning boundary. It is not a release until a
maintainer publishes a tag and release record for one exact commit.

A release candidate must include:

1. a closed or release-ready milestone with unresolved work explicitly
   deferred;
2. a row in [`baseline-register.md`](baseline-register.md) identifying the
   exact commit, scope, dependencies, and validation evidence;
3. green public repository, smoke, and project-owned test gates from a clean
   checkout;
4. required privileged SysML validation evidence bound to the same commit; and
5. release notes that distinguish demonstrated, experimental, deferred, and
   not-yet-validated material.

The release maintainer verifies the candidate SHA, creates the annotated tag,
publishes the release notes, and checks that public services or downloadable
artifacts report the same source revision. A tag is never moved after
publication; corrections use a new version.

## Change-control expectation

Changes should preserve traceability from:

1. the System 3 decision or issue that motivates the change;
2. the System 2 engineering asset or process being changed; and
3. the System 1 feature, product-line asset, variant, or assurance concern being
   managed.

See [`../ROADMAP.md`](../ROADMAP.md) for the current release gate. No baseline
or release is evidence of certification or homologation by itself.
