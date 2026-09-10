# R0-4: First bounded K predicate selection

> **STATUS: SUPERSEDED IN PART (specification record).** The selection of
> `derivesRequirementFromNeed` and the `allocatedTo` alternative analysis
> remain current. The zero-risk claim in reason 2 below is WITHDRAWN per
> review: introducing a model-native discriminator for a vocabulary-only
> predicate is a semantic change to the model even though no implemented
> runtime mapping is repurposed; it requires the full review discipline
> (reviewed meaning, tests, exact-toolchain evidence) from the start.

## Selection: `derivesRequirementFromNeed` (Requirement -> Need)

Selection reason (per plan §5 and handoff step 3):

1. **Plan's stated preference holds under repository evidence.** The plan prefers
   `derivesRequirementFromNeed` unless inspection shows `allocatedTo` gives the
   stronger bounded proof. Inspection result: derivation has a native SysML
   grounding path plus a locked upstream candidate
   (`SysML Requirement Derivation Library 2.0.0`, in `sysand-lock.toml`, not yet
   consumed by the model), while `allocatedTo`'s native allocation representation
   would have to be proven against allocation usages that today carry the
   *different* `realizedBy` mapping (Requirement -> ArchitectureElement,
   strength=allocation). Proving allocation ends for `allocatedTo`
   (Function -> LogicalElement) risks colliding with the frozen `realizedBy`
   signature boundary (plan §10). Derivation is the cleaner first proof.

2. **Vocabulary-only today.** No sysml_mapping exists; nothing implemented
   can be silently repurposed. NOTE (review correction): this removes silent
   *repurposing* risk only — introducing a model-native discriminator for a
   vocabulary-only predicate is itself a semantic change to the model and
   carries full review obligations.

3. **Real, current semantic need in the model.** AEBS requirements express
   derivation as free-text `source` attributes ("Derived from N-AEBS-001") in
   `aebs_needs_requirements.sysml`. A proven typed discriminator replaces a real
   hand-authored semantic practice — it is not a demo for demo's sake.

4. **Semantically discriminating.** The model uses native `Dependency` heavily
   (e.g., seven acceptance-criterion dependencies in
   `aebs_visualization_verification_evidence.sysml`), so the adversarial case
   (unrelated Dependency with identical endpoint types must NOT satisfy the
   stronger predicate — UG-05) is exercised against real serializer shapes.

## Engineering claim boundary

"Requirement R is derived from stakeholder need N" — a design-input derivation
relation, direction R -> N. It does NOT claim satisfaction, allocation,
verification, evidence, or acceptance. Inverse navigation (from N to its derived
requirements) reuses the same witness.

## Required positive witnesses

- kernel/definition identity: the Requirement and Need definitions (via
  ingestion-validated KernelBindingIndex, not names);
- the derivation relationship/usage witness (native derivation representation),
  with endpoint UUIDs and direction;
- generated Semantic Projection row for the predicate (schema v0 below);
- runtime consumer returning the edge with predicate identity, strength,
  witnesses, bound revision, completeness, and diagnostics;
- inverse navigation over the same witness.

## Required negative cases

- missing derivation (no edge) -> empty result, not absence-based pass;
- wrong-type endpoints (e.g., Requirement -> Function);
- unrelated generic Dependency with identical endpoint types -> NOT matched
  without its discriminator;
- multiple DISTINCT valid derivation witnesses are legal and returned as separate edges (one requirement may derive from several needs and vice versa); fail-closed applies to ambiguous IDENTITY RESOLUTION only: two API elements resolving the same declared binding, homonymous identifiers without a discriminating binding, or contradictory duplicate witnesses for one identity (plan §17 UG negative list: "ambiguous/homonymous identity");
- incomplete serializer/reference closure (derivation witness pruned by
  importer) -> query incomplete/unsupported, never absence-based pass (UG-06).

## Required serializer/import closure

- derivation relationships survive official serialization + API import
  (explicit closure check; importer may drop out-of-export references);
- if the locked Requirement Derivation Library is adopted as grounding: its
  imports must survive ingestion closure, or the native-SysML-only grounding is
  used instead and the library row stays "not consumed" (upstream-involvement
  gate applies before any library adoption);
- UUID preservation across one export/import/read-back transaction.

## Documented alternative (not selected)

`allocatedTo` remains the fallback if exact-toolchain evidence shows native
derivation representation is weaker than expected. Per plan: record the reason;
do not force either predicate. Decision revisited only with new evidence.
