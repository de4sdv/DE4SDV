# Gate B: source-informed experimental override

**Disposition:** **Source-informed experimental override — upstream contact deferred**

**Decision authority:** Orkun Yilmaz, DE4SDV technical lead and maintainer  
**Decision date:** 2026-09-01  
**Scope:** experimental PLEML interpretation only; no production adoption

## Decision

No PLEML upstream issue or maintainer contact is created for Gate B.

PLEML remains:

- exact-pinned at commit
  `5f8ab8560219dc24d8ec7ec90d6f0a145896ef8e`;
- experimental and reversible in DE4SDV;
- subject to the frozen Gate A revision-bound evidence;
- unsupported as a source of upstream-confirmed semantics where questions
  remain open.

The source QA against the stored product-line method source, SysML v2
specification source, and official pilot implementation sources is retained
below as supporting evidence. Source agreement is not upstream maintainer
agreement.

## Frozen Gate A evidence

Gate A remains isolated in draft PR #175 at exact head
`6a99626b4af7cd01108f27dac88bf5b55bba207a`.

Its accepted evidence chain was:

```text
exact-pinned PLEML source
→ official SysML parser/serializer
→ immutable SysML API project and commit
→ UUID-resolved semantic repository
→ deterministic experimental evaluation
→ SysML projection
```

The privileged PLEML Gate A Evidence run `33543909037` and exact-head CI run
`33543909098` succeeded for that frozen head. Gate C does not modify or extend
those artifacts.

Gate A proved that the relevant modeled constructs survive official
serialization with API UUIDs, ownership, relationships, and source provenance.
It did not prove that DE4SDV's interpretations are PLEML maintainer intent, and
it did not execute PLEML constraint expression bodies.

## Retained source QA

| Semantic topic | Source-informed finding | Authorized experimental handling |
|---|---|---|
| `xorFeatures` / `XORConstraint` | The pinned body is vacuous for the documented single-excluded-feature case and appears to iterate range values rather than excluded features. Native SysML variant subsetting does not itself imply mutual exclusion. | Keep the defect suspected and unresolved. Do not call the body correct or upstream-conformant. Experimental evaluation may follow the documented owner-versus-excluded intent by API identity, while explicitly reporting that override. |
| `FeatureBinding` | The pinned construct serializes as a dependency plus metadata and derives a feature name from a supplier. The method and pilot sources support feature-to-asset linkage but do not establish Boolean semantics for multiple bindings. | Treat each binding as linkage/provenance metadata. Do not infer AND, OR, precedence, or configuration logic from binding multiplicity. |
| feature groups | The method, specification, and pilot evidence support multiplicity plus variant subsetting as the observable group structure. Subsetting is membership, not disjointness. | Resolve group members, bounds, and selections through API UUIDs and official multiplicity objects. Do not invent Python-only grouping conventions. |
| conditional technical realization | The reviewed sources contain no settled construct that maps a conjunction of product selections to one technical realization. | Keep DE4SDV's `AdapterRealizationRule` as an internal experimental extension. It is pin-specific, reversible, and not a PLEML feature or upstream-confirmed pattern. |
| `bindingTime` | The method and pinned library both support stage-relative configuration completeness rather than descriptive metadata alone. Exact evaluator behavior remains unimplemented and untested. | Retain staged semantics as a source-supported interpretation, but admit only Development in the current governed scope. Do not claim production evaluator support. |
| project maturity | The pinned library identifies itself as work in progress and the evidence spike intentionally uses an exact commit rather than floating upstream state. | Keep the dependency exact-pinned and experimental. Re-review before changing the pin or presenting the feature layer as production authority. |

## Boundaries of the override

The override authorizes only bounded experimental work that:

- records the exact PLEML pin;
- preserves source and API UUID provenance;
- labels internal extensions and interpretations as experimental;
- reports unsupported semantics rather than silently supplying them;
- keeps current YAML configuration authority intact;
- remains reviewable and reversible.

It does not authorize:

- a production PLEML feature tree or FeatureConfiguration;
- PLEML-based replacement of current YAML authority;
- retargeting `tools/configure_variant.py`;
- claims that PLEML maintainers agreed with DE4SDV;
- claims that the suspected XOR defect is fixed;
- automatic use of later lifecycle binding stages;
- upstream contact from this decision.

## Re-verification triggers

Bounded Gate B re-verification is required if any of these occurs:

- a PLEML maintainer later clarifies an affected semantic;
- the exact PLEML pin changes;
- the suspected XOR body changes;
- official serializer shapes used by the evaluator change;
- DE4SDV implements stage-aware `bindingTime` evaluation;
- an internal experimental extension is proposed for production adoption.

Until then, the source-informed interpretations above remain internal,
pin-specific, reversible, and not upstream-confirmed.
