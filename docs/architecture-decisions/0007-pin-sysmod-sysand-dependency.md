# ADR 0007: Pin SYSMOD as a Sysand dependency behind a DE4SDV adapter

## Status

Proposed

## Context

[ADR 0002](0002-adopt-sysmod-sysmlv2-library.md) adopted the public SYSMOD
SysML v2 library as a modeling reference. It deliberately deferred package
consumption until an official package was available and the dependency and
validation path had been tested.

The official Sysand package is now available as `pkg:sysand/mbse4u/sysmod`.
DE4SDV already uses Sysand for its view library, and a disposable compatibility
probe confirmed that the exact package version selected here can be resolved,
imported, and built by the repository's pinned Sysand client. Registry validation
is useful upstream evidence, but DE4SDV still requires exact-head model
validation before readiness claims.

Directly adopting the upstream `Project` structure would create a competing
artifact root beside DE4SDV's SAF viewpoint organization, product-line model,
13-phase increment workflow, and evidence lifecycle. The dependency therefore
needs a controlled semantic boundary.

## Decision

DE4SDV will:

1. consume `pkg:sysand/mbse4u/sysmod` with the exact constraint `=5.1.1`;
2. commit the Sysand lock resolution and keep downloaded package source under
   `.sysand/` untracked;
3. confine upstream imports to `DE4SDV_SYSMODAdapter`;
4. expose DE4SDV-owned seams for selected stakeholder, requirement, system-use-
   case, and constrained-occurrence concepts;
5. require model packages to depend on those DE4SDV seams rather than import
   `SYSMOD::*` directly; and
6. review each later specialization as a small migration with exact-head
   validation.

This decision does **not** adopt or specialize upstream `Project` or
`AIProject`, use the upstream requirement-boilerplate constraints, replace SAF,
rename DE4SDV product-line concepts, or change the DE4SDV increment sequence.

SAF domains and SYSMOD architecture artifacts remain independent
classifications:

- Operational-domain needs, scenarios, and capabilities provide input and
  rationale for functional architecture;
- functional architecture and logical architecture are
  distinct artifact kinds in the Conceptual Domain; and
- product/implementation architecture is exposed through Physical-domain
  viewpoints when it represents concrete realization.

The SYSMOD `product` terminology is not an alias for a DE4SDV configured member
product. DE4SDV product-line configuration, derivation, and evidence remain
DE4SDV-owned extensions.

## Consequences

- Package acquisition is reproducible and source is not vendored.
- Upstream upgrades become explicit dependency-review events.
- The adapter adds a narrow maintenance point but prevents external definitions
  from spreading through feature packages.
- Existing DE4SDV method definitions, SAF viewpoints, product-line assets, and
  evidence contracts remain authoritative unless a later ADR changes them.
- Selected adapter seams are available for later pilots; adding the dependency
  does not by itself migrate existing DE4SDV model elements.
- Exact-head repository checks and licensed SysML validation remain required.
  Registry validation is supporting evidence, not proof that the DE4SDV model
  compiles against the package.
- Candidate upstream inconsistencies are recorded separately for maintainer
  review before DE4SDV depends on the affected definitions.

## Upgrade gate

A proposed package upgrade must:

1. update the exact constraint and lock file together;
2. review upstream changes affecting every exposed adapter seam;
3. keep `Project`, `AIProject`, and requirement-boilerplate constraints outside
   the adapter unless a later decision justifies them;
4. run dependency sync, repository checks, tests, viewer generation, and SysML
   validation on the same commit; and
5. document any semantic migration or retained incompatibility.
