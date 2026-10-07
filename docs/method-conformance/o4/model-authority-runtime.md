# Model-authority runtime (O4 Wave B)

Status: **draft, not activated.** This record describes the runtime core for
the owner decisions of 2026-10-07. It does not claim production activation,
consumer retirement, live API closure, compliance or certification.
Production activation and the activation decision naming the `mab-` id stay
with the owner.

## Problem

Under the O3 authority only 13 identities come from projection artifacts.
Every other identity still comes from the authored ontology YAML, and no
runtime loads the O2+, vocabulary-carrier or relationship-successor layers.
Wave B cuts production over to one bundle that binds every model projection
layer, so the remaining authored-YAML use becomes an explicit, visible
residual and not a silent fallback.

## Bundle

`de4sdv/semantic/model_authority_runtime.py` builds and verifies the
model-authority bundle (`de4sdv.model-authority-bundle/v1`). Its id is
`mab-<32 hex>`, the digest of `schema`, `git_revision`,
`ontology_compatibility_identity` and `components`. The service authority id
is `mab:<bundle id>`.

| Component | Content |
| --- | --- |
| `o3` | Closed O3 bundle, embedded. The record holds its id, sha256 and Projection/Profile chain digests. |
| `layers` | Projection/profile pairs (path, schema, sha256, source revision) for `definition`, `o2plus`, `vocabulary-carrier` and, once present in the checkout, `definition-batch2` |
| `successor_contract` | Id, digest and relation names of the contract that `relationship_successor_contract.generate_contract` builds from the model, plus the deprecated-alias table |
| `routing` | Exactly one provider per identity, any agreeing corroborations, duplicates (must be empty) and the residual with a reason for each entry |
| `implementation_manifest` | sha256 of each executed sidecar source that is not a frozen O3 runtime-build input |

Closure (`de4sdv.model-authority-closure/v1`) binds the bundle to one
revision binding. It records the binding digest and SysML project/commit,
whether O3 is activation eligible, whether the definition closure is closed,
and the validation evidence `model_projection_coverage`,
`model_o3_legacy_equivalence` and `verification_anchor_readback`. Each
validation must be exactly `passed` and carry a sha256. Activation
eligibility is recomputed during verification, never trusted. The
requirement-population delta is measured, not gating.

Verification recomputes every component from the checkout and refuses any
mismatch. That covers layer bytes, the regenerated successor contract,
routing, implementation sources (an external substitute is refused) and the
O3 component. A coherent rewrite of the id does not get past it.

## Definition-admission batch 2

The batch-2 pair (`definition-batch2-projection.json` /
`definition-batch2-profile.json`, schemas
`de4sdv.o4-definition-batch2-projection/v1` and `-profile/v1`) is a fourth
layer. It is optional only while the pair is absent from the checkout; once
present it is bound and verified like every other layer. Every admission
class the batch emits has one loader rule, and any other shape is refused:

| Row | Becomes |
| --- | --- |
| class `definition` / `external-reference` | class provider from exactly one of `kernel_binding_contract`, `kernel_native`, `kernel_external` |
| `relationship-vocabulary` / `external-reference` relation | vocabulary relationship (domain, range, optional strength, carrier) |
| relation with profile `serializer_mechanics` | serialized relationship mapping (strength required) |
| `relationship-runtime` with a range `discriminator` | the discriminator is carried; the `hasRelevantEvidenceContract` closure must hold exactly eight definitions |
| `successor` | corroborates the model-generated successor contract when the end-pair sets are equal |
| `deprecated-alias` | never a provider; must equal the alias table (successor, navigation, answer mode) |

While the authored YAML still exists, a batch-2 class mapping or
relationship mapping that differs from it is a routing conflict. The
natively represented successor endpoint classes (`Function`,
`LogicalElement`, `PhysicalElement`, `ValidationScenario`) keep the
successor contract's lineage pin as their runtime mapping, as the approved
successor runtime does. The batch-2 row corroborates that pin only when
exactly one projected direct specialization (by `sub_class_of`) carries it.

With the batch-2 pair from the admission lane overlaid, routing has no
duplicates, and the residual is exactly the two owner-visible exceptions
`IncrementTraceabilityShell` (disposition MERGE) and `derivesNeedFromConcern`
(disposition REMOVE).

## Selection and rollback

```text
DE4SDV_SEMANTIC_AUTHORITY=model
DE4SDV_MODEL_AUTHORITY_BUNDLE=<path to closed bundle JSON>
DE4SDV_MODEL_AUTHORITY_BUNDLE_ID=mab-<32 hex>
```

`composition_construction.build_explicit_semantic_runtime` is the one
canonical router: it routes `model` to `build_model_authority_runtime`, and
entry points delegate every selection, `model` included, to it.
Activation eligibility (a closed bundle whose recomputed closure is eligible)
is required by default. Only an explicit `require_activation_eligible=False`
serves a candidate or ineligible bundle; the privileged compare step and the
tests use it. `ModelAuthorityRefused` is an `AuthoritySelectionError`. The frozen `authority_selection` module, a
recorded O3 runtime-build input, is not changed. Legacy and o3 calls reach it
with byte-identical arguments, and a test asserts this. Rollback is
`DE4SDV_SEMANTIC_AUTHORITY=o3` with a fresh O3 bundle; legacy is the second
fallback. A failed model request raises and never degrades to o3 or legacy.
Callers that use `authority_selection.build_selected_semantic_runtime`
directly still refuse `model`.

The builder can also be called directly:

```python
from de4sdv.semantic.model_authority_runtime import (
    ModelAuthorityRefused, build_model_authority_runtime)

runtime = build_model_authority_runtime(
    repo_root, bundle_path, expected_id,  # None -> the two environment variables
    api_url=..., binding_path=..., expected_git_revision=..., ontology_path=...,
    require_activation_eligible=True)  # default; False only for compare/test
runtime.authority_status()
# {"authority": "model", "bundle_id": "mab-...", "authority_id": "mab:mab-...",
#  "source_revision": "<40 hex>", "residual": [<identity>, ...],
#  "rollback": "o3", "activation_blocked": <bool>}
```

The returned runtime is the query service; `runtime.selection` holds the
verified selection, and `runtime.semantic_authority_id` is `mab:<bundle id>`.
Every refusal raises `ModelAuthorityRefused`.

## Successor exposure and deprecated aliases

`allocatedTo`, `hasValidationScenario` (inverse `validationScenarioFor`) and
`hasRegulatorySource` are default predicates. The retired names answer only
on explicit request, as deprecated aliases. Each alias edge carries
`witness.deprecated_alias`, and each alias-bearing report carries a
`deprecated_aliases` list. Wave C deletes the aliases.

| Alias | Answers through | Claim boundary |
| --- | --- | --- |
| `realizedBy` | `allocatedTo`, Requirement to Function pair only | responsibility assignment only |
| `deployedTo` | `allocatedTo`, LogicalElement to PhysicalElement pair only | no deployment or observed operation |
| `validatedBy` | `hasValidationScenario` | planning association only |
| `validatesFitnessForUse` | `hasValidationScenario`, navigated as `validationScenarioFor` | no fitness-for-use verdict |
| `constrainedBy` | nothing: documentation only, points to `hasRegulatorySource` | historical provenance, not an alias |

`constrainedBy` follows the model retirement record: the controlled-source
successor `hasRegulatorySource` is not an alias. The name stays answerable,
but it returns no edges. It records a `retired` unavailability and carries
the deprecation marker with `answer_mode: documentation-only`.

## `hasRelevantEvidenceContract` discriminator

The range is the authored type closure of the validated `EvidenceContract`
kernel root. It must contain exactly eight specializing requirement
definitions: the AEBS evidence contracts. Members are the usages explicitly
typed by the root or by one of those definitions. Any other population fails
closed with `MODEL_EVIDENCE_CONTRACT_BLOCKED_REASON`. `traversal.py` is
untouched; the discriminator is a subclass override. The legacy and o3 paths
keep the predicate blocked.

## Coverage gate (shadow ratchet)

`scripts/check_model_projection_coverage.py` (module
`de4sdv/semantic/model_projection_coverage.py`) classifies every item in
three populations as projected (layer + digest) or residual (reason):

- every retained register row;
- the ontology YAML identities that the register does not list;
- every governed kernel declaration (excluded declarations are listed
  separately).

It compares the result with
`model-authority-coverage-baseline.yaml`, which has no binding block. It
fails on residual drift in either direction, duplicate providers, and
routing or layer digest mismatch. With `--bundle`, it also fails when a
bundle differs from the checkout. `scripts/check_repo.py` runs it. In shadow
mode, a non-empty residual is reported but does not fail the gate. Wave C
makes an empty residual blocking.
