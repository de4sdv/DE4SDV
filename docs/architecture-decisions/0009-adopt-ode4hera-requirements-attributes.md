# ADR 0009: Adopt the ODE4HERA requirements-management attribute library as a Sysand dependency

## Status

Proposed

**Amendment (2026-08):** the adopted attribute set is extended with the
library's verification-planning attributes — `verificationMethod` (NRM A8)
and `verificationStatus` via the `VVStatus` enum (NRM A13+A14) — so each
requirement usage carries its planned verification method and status natively
in the model. The pilot YAML files no longer duplicate `method` or
`evidence_status` columns; they retain criterion gaps and evidence artifact
locations. `verificationMethod` is typed upstream as `String[0..1]`; DE4SDV
populates it with the standard `VerificationMethodKind` vocabulary
(`inspect`, `demo`, `test`, `analyze`) and enforces that vocabulary by test
until an upstream enum-typed attribute exists. Adoption began with the AEBS
needs/requirements slice; other slices follow the same pattern on touch.

## Context

The DE4SDV needs/requirements corpus (AEBS INC-AEBS-003, AEBS-010, middleware
INC-MW-004/005) carries its expression attributes as prose inside doc
comments: status words ("draft", "candidate"), rationale, and source
references are free text that the viewer extracts heuristically and reviewers
read by eye. The INCOSE Guide to Writing Requirements and the Needs and
Requirements Manual both make an expression more than its statement: source
traces, rationale, owner, status, and version attributes are part of the
controlled record.

The ODE4HERA project (DLR Institute of System Architectures in Aeronautics)
publishes an MIT-licensed SysML v2 library that models exactly this attribute
catalog — the NRM Chapter 15 attributes A1–A49 — as native SysML v2
definitions, and distributes it as the Sysand package
`ode4hera/requirements-management` (v2.0.1 at the time of writing). Its
specialization root (`NeedsRequirementsAttributes :> ProvenanceAttributes`)
and DE4SDV's existing method context (`RequirementCandidate :>
SYSMODRequirementBase`) graft onto the same SYSMOD seam, so the two libraries
compose rather than compete.

The library's own tailoring matches DE4SDV practice: it drops roughly twenty
of the 49 attributes as "semantically covered" (trace-to-parent by derivation
dependencies, stakeholders by links, identifier/name by model names), the
same tailoring logic DE4SDV applied in its GtWR-aligned quality gate.

DE4SDV already has the consumption pattern and toolchain in place: ADR 0007
pins SYSMOD 5.1.1 as a Sysand dependency behind a DE4SDV-owned adapter, and
Sysand 0.2.1 with a committed lockfile is the established acquisition path.

## Decision

DE4SDV will:

1. consume `ode4hera/requirements-management` as a Sysand dependency with an
   exact version constraint, committed lockfile, and untracked package source;
2. confine upstream imports to `DE4SDV_MethodContext`, extending the existing
   adapter boundary rather than creating a second one;
3. adopt the scoped attribute set: `rationale` (A1), `source` (A3), `status`
   (A30 via the `ReqStatus` enum), and the authoring-provenance attributes
   (`owner`, `version`, `createdBy`, date attributes) where a record needs
   them;
4. migrate existing status words ("draft", "candidate") to `ReqStatus` enum
   values in the needs/requirements slices;
5. keep the viewer's ID/status extraction working, reading the structured
   attribute where present and falling back to doc text during migration; and
6. record the adoption as a controlled change to the draft baselines, not a
   silent rewrite.

The decision does **not** adopt `ReqPriority` (no DE4SDV priority semantics
exist yet), `ReqImplementationStatus` (overlaps with evidence-slice
realization status; adopting it now would invite overclaim), or any
product-line applicability attribute (the upstream library explicitly does
not cover NRM A41–A49).

## Product-line gap and upstream contribution

NRM attributes A41–A49 (Applicability/Reuse, Product Lines) are explicitly
out of scope for the upstream library. For a software-defined-vehicle
*product line*, per-record applicability (common capability vs. member-product
variant scope) is a first-class concern DE4SDV currently carries in prose. We
intend to raise this with the upstream maintainers — proposing a
product-line-applicability extension for a future upstream version rather
than forking privately. Until that lands, DE4SDV keeps its own
`applicability` convention.

## Consequences

- Attribute data becomes structured and machine-checkable; the requirements
  browser can filter/sort by real status values instead of parsing prose.
- Package acquisition is reproducible and not vendored; upstream upgrades
  become explicit dependency-review events like ADR 0007.
- The method context gains a narrow upstream import surface; feature packages
  remain untouched.
- Status migration touches draft baselines; the change is recorded through
  the normal review path with validation evidence.
- Some attribute values (owner, approval dates) are low-value for a small
  open-source project where git provides provenance; we adopt them
  opportunistically rather than mandating population.
- Risk: upstream is young (v2.x, small user base). The exact-pin and adapter
  boundary contain this; a defect means a pin review, not a rewrite.

## Non-decisions

- Whether DE4SDV should publish its own requirements-management extensions as
  a separate Sysand package (deferred until the upstream product-line
  discussion matures).
- Whether `ReqPriority` or `ReqImplementationStatus` should be adopted later.
- Any change to the DE4SDV increment workflow, SYSMOD adapter seams, or SAF
  viewpoint organization.

## Links

- Upstream repository:
  https://github.com/ode4hera/SysML-v2-Requirements-Management
- Sysand package: https://sysand.com/projects/ode4hera/requirements-management/
- ADR 0007 (SYSMOD Sysand dependency — the adapter precedent)
- ADR 0002 (SYSMOD adoption as modeling reference)
- DE4SDV requirements QA gate PR and its GtWR v4 alignment
