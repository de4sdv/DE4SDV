# R0-6: Bounded PLEML semantic/adoption requalification scope (PLE-Q)

## Basis (recovered, verified)

- Exact pin: `5f8ab8560219dc24d8ec7ec90d6f0a145896ef8e` (submodule at frozen Gate A head).
- Frozen Gate A head: `6a99626b4af7cd01108f27dac88bf5b55bba207a`; PR #175 CLOSED (not merged).
- Historical evidence: privileged run 33543909037 + CI 33543909098, both success at that head (verified 2026-09-10).
- Gate B record: source-informed experimental override, upstream contact deferred
  (docs/product-line-engineering/gate-b-source-informed-experimental-override.md).
- PLEML remains experimental; this scope does NOT authorize adoption, upstream
  contact, pin change, or YAML authority replacement.

## Requalification principle

Exercise only affected serialization/identity/typing/group/constraint cases on
the CURRENT exact toolchain (current sysand lock + current Syside/serializer
revision). Keep representation proof separate from constraint evaluation.
Historical Gate A evidence stays historical; no row promotes without a fresh
concept-specific adequacy check.

## Case list (each: reproduce on current toolchain, compare against Gate A matrix)

1. **XOR counterexample (UG-12)** — reproduce the suspected vacuous/
   range-iteration defect on the current toolchain. Record interpretation and
   keep the failure/unsupported status; any override stays separately labeled.
2. **FeatureBinding (UG-11)** — multiple bindings, no inferred AND/OR/precedence;
   binding = linkage/provenance metadata only.
3. **Group membership/subsetting + multiplicity (UG-11)** — both serializer
   range shapes (literal bounds and `..` operator form); subsetting is not
   disjointness; at-least-one/multi-select/none configurations.
4. **bindingTime** — serialization + stage-relative interpretation only;
   Development-only scope; no stage-aware evaluator claim.
5. **Serializer/identity cases** — UUID preservation, out-of-export pruning,
   metatype survival for feature/group/binding/constraint concepts (re-run the
   Gate A observability rows that have dedicated adequacy checks; rows without
   dedicated checks remain GAP).
6. **AdapterRealizationRule** — internal experimental extension stays internal,
   conditional, pin-specific; distinct from product features.

## Requalification exit criteria

- Fresh current-toolchain evidence for each case above, exact-pinned, with
  representation vs. evaluation kept separate.
- Diff report vs. frozen Gate A observability matrix: every semantic
  difference classified (toolchain change vs. interpretation change).
- Re-verification trigger check (Gate B doc §Re-verification triggers): pin
  unchanged -> no automatic re-verification of UNaffected cases.
- If necessary semantics cannot be established: deliver reproducer, failed
  requirement, upstream disposition (where available), bounded alternative for
  Orkun's decision (plan §7.3). No silent substitution.

## Explicit non-goals

No PLE-S scope-alignment runs, no configurator retargeting, no YAML authority
change, no upstream contact, no adoption decision. Those are later gated steps
(PLE-S needs PLE-Q output; PLE-A needs authorization).
