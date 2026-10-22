# ADR 0021: Model elements earn their place

## Status

Proposed

> Note (2026-10-20): from the switch of [ADR 0022](0022-adopt-pleml-as-product-line-authority.md) (step S6) the
> selection authority is no longer the external catalogue of ADR 0006, as the
> link below says: it is the PLEML feature models with the DE4SDV evaluation
> and derivation rules. The kernel guard still keeps configuration algebra out
> of the method kernel. The decision text below is unchanged.
>
> Note (2026-10-22): decision 5 no longer holds where it says that "a varying
> requirement is a variant of a variation, which phase 9 binds to its
> feature". On 2026-10-21 the owner decided that a requirement varies with the
> feature that brings its system of interest, as existing links state. Phase 9
> binds no requirement variant to a feature: that waits until the evaluator
> binds requirement variants. Rule 5 of the
> [increment workflow](../../methodologies/sysmod-sysmlv2/increment-workflow.md#method-rules-and-the-increment-workflow-model)
> states the current rule. The decision text below is unchanged.

## Context

The INC-MW-011 element audit and the cross-increment review of #382 found the
same bloat across increments. Slices carried elements that no gate required
and nothing consumed. They restated what other elements or native
relationships already said, invented method types with no kernel base, and
put engineering and assurance roles into member-product contexts. Phase 3
recorded every core element as a common capability. The kernel taught a
vocabulary-only `HasStakeholder` relation as a native trace, although no
gate, check or traversal read it.

The owner decided the rules on 2026-10-16 and 2026-10-17 and answered the
open items on #383 on 2026-10-18. They change the method and the contributor
workflow, which `GOVERNANCE.md` asks to capture in an ADR.

## Decision

1. **Method types come from the kernel.** Types for method concepts come only
   from the ontology and the method kernel. A slice may specialize a kernel
   definition, and must where the method asks for it. A method concept with
   no kernel base goes through an ontology or method pull request first.
2. **An element earns its place.** Every element needs one of three reasons:
   a method gate requires it; something consumes it (a trace, a typing, a
   later phase, or a view framing a concern a reviewer needs); or it carries
   a decision, assumption or gap that a later phase acts on. A doc-only
   restatement has none of them. Reviewers judge necessity, not only
   correctness.
3. **Unconsumed elements are reported, advisory.** The Method Check will
   report, once the follow-up pull request implements it, an element in an
   increment's scope that no gate requires and nothing consumes. The report
   never blocks a phase.
4. **Phase 3 records only the feature-model delta.** The characteristics it
   records are feature candidates. Core elements are common by default and
   get no record, so `CommonProductLineCapability` stays in the kernel but is
   not instantiated for them. Constraints go to phase 5 and evidence to
   phase 10. The basis is ISO/IEC 26580: a feature differentiates member
   products, and the feature model covers variability only.
5. **Requirements are shared assets.** A requirement without a feature link
   is core. A varying requirement is a variant of a variation, which phase 9
   binds to its feature. The phase-5 advisory gate that asked every
   requirement for a feature or common capability is retired.
6. **No System 2 roles in System 1.** Bench, reviewer and evidence roles stay
   out of a member product's operational context and story; they belong to
   the engineering and assurance system.
7. **Stories bind to their context.** A use case's subject is the system of
   interest, and its actors are bound to the context parts around it.
8. **`HasStakeholder` is retired.** An increment's stakeholders are the native
   stakeholder members of its problem statement, which the method's checks
   read.

## Consequences

- `AGENTS.md`, the increment workflow (rules 5, 7, 9, 10 and 11) and the
  kernel steps carry the rules. Reviewers have two new review questions.
- The method kernel serves one relation less. The runtime refuses
  `hasStakeholder` with its register disposition, and the semantic-authority
  identity changes; a redeploy needs a fresh privileged binding.
- Phase 5 has six checks instead of seven. Blocking verdicts do not change.
- Closed increments keep their records until a clean-up removes the
  restatements, System 2 roles and core-element common capabilities they
  still carry.
- The frozen projection that serves `MethodPhase` keeps the old phase-3 text
  until the next release rebuilds it.
- Fewer elements per slice, at the cost of a judgment call per element that
  reviewers must make explicitly.

## Non-decisions

- How the unconsumed-element report defines consumption, for example whether
  a wildcard `expose` counts. The implementation pull request decides it.
- Retiring the vocabulary relation `specifiesCommonCapability`. That is a
  separate ontology decision.
- The clean-up of closed increments and of INC-MW-011's story.
- Refreshing the frozen records.

## Links

- [ADR 0004](0004-adopt-aselcm-three-system-framing.md): the three-system
  framing that decision 6 applies to operational contexts.
- [ADR 0006](0006-variant-selection-construct-and-ple-adequacy.md): external
  selection authority, which the kernel guard keeps.
- [ADR 0020](0020-give-ontology-definitions-model-resident-kernel-homes.md):
  the feature/common-capability disjointness `CommonProductLineCapability`
  keeps.
- Pull request #365: the precedent for removing unused kernel vocabulary.
- Pull requests #382 (INC-MW-011 simplification) and #383 (this decision).
