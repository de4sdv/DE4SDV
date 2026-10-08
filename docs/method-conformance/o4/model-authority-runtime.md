# Model-authority runtime (O4 Wave B, closed by Wave C2)

Status: **draft, not activated by this record.** This record describes the
runtime core for the owner decisions of 2026-10-07 (Wave B) and the closure
decisions of Wave C (2026-10-07/08). It does not claim production
activation, live API closure, compliance or certification. Production
deployment and the activation decision naming the `mab-` id stay with the
owner ([activation and rollback](model-authority-activation.md)).

## Problem

Under the O3 authority only 13 identities came from projection artifacts;
every other identity came from the authored ontology YAML. Wave B cut the
runtime over to one bundle that binds every model projection layer and made
the remaining authored-YAML use an explicit residual. Wave C2 removed that
residual and the YAML itself: the model-built kernel contract is the only
semantic authority, and nothing at runtime reads an authored ontology.

## Model-built kernel contract

`KernelContract.from_layers(root)` (`de4sdv/semantic/kernel_contract.py`,
built by `de4sdv/semantic/model_contract.py`) assembles the contract from:

- the model-generated layers: definition admission batch 1
  (`definition-projection.json` / `-profile.json`), batch 2
  (`definition-batch2-…`), the O2+ pair (`o2plus-…`) and the
  vocabulary-carrier pair (`vocabulary-carriers-…`);
- the frozen O2-chain layer: the 13 O3-migrated identities read from the
  frozen O2 Projection/Profile records (`o2/semantic-projection-v1…v1.2`
  and profiles), unchanged since O3;
- the successor contract generated from the model
  (`relationship_successor_contract.generate_contract`, class pins from the
  layers);
- the kernel-internal declarations manifest
  ([kernel-internal-declarations.yaml](kernel-internal-declarations.yaml),
  owner decision D3), the governed-directory accounting.

Its identity is the **semantic-authority identity** (`sai-<32 hex>`,
schema `de4sdv.semantic-authority/v1`): a digest over every layer path and
sha256 and the contract content. Revision bindings v2 carry it as
`semantic_authority`; a v1 binding (authored-YAML `ontology` block) is
refused.

The contract also carries:

- `refused`: every identity answered only with its disposition — the
  registered non-retained rows (`IncrementTraceabilityShell` MERGE,
  `derivesNeedFromConcern` REMOVE, owner decision D5, refused with the
  register disposition) and the retired names (D4, below). A refused
  identity raises `RetiredIdentityError` with `<name>: <disposition>`;
- `lineage_pinned`: the natively represented successor endpoint classes
  (`Function`, `LogicalElement`, `PhysicalElement`, `ValidationScenario`)
  map to their successor lineage pins (`AllocatableFunction`,
  `LogicalAllocationElement`, `PhysicalAllocationElement`,
  `ValidationPlanningScenario`). Ingestion binds those pins only under
  the owning successor class (validation status `lineage-pinned`), so the
  kernel binding set equals the one Wave B served.

The equivalence of this contract with the deleted authored ontology was
proven before the deletion and is committed as evidence:
[closure/contract-equivalence.json](closure/contract-equivalence.json). The
served contract differs from the authored one in exactly seven identities:
the two refused exceptions and the five retired names. The 54 batch-2
contract fields held by the admission manifest (domain/range/strength,
mechanics, kernel mapping kind, ontology relations) are recorded there with
their pre-deletion equality (owner decision D9).

## Bundle

`de4sdv/semantic/model_authority_runtime.py` builds and verifies the
model-authority bundle (`de4sdv.model-authority-bundle/v2`). Its id is
`mab-<32 hex>`, the digest of `schema`, `git_revision` and `components`. The
service authority id is `mab:<bundle id>`.

| Component | Content |
| --- | --- |
| `layers` | Projection/profile pairs (path, schema, sha256, source revision) of every model layer, and the frozen O2-chain records |
| `semantic_authority` | The `sai-` identity of the model-built contract |
| `successor_contract` | Id, digest and relation names of the model-generated successor contract, and the `retired` table (name → successor navigation) |
| `routing` | Exactly one provider per identity, agreeing corroborations, duplicates (must be empty), the residual (must be empty: bundle construction refuses otherwise) and the retired names |
| `implementation_manifest` | sha256 of each executed runtime source (21 files) |

Closure (`de4sdv.model-authority-closure/v2`) binds the bundle to one
revision binding: binding digest, SysML project/commit, whether the
definition closure is closed, the bound `EvidenceContract` closure members
with the element id each one validated to, and the required validations
`model_projection_coverage`, `model_runtime_answers`,
`verification_anchor_readback`, `full_model_semantic_queries`,
`product_line_scope` and `semantic_mcp`. Each must be exactly `passed` and
carry the sha256 of its artifact. Activation eligibility (definition
closure closed and every validation passed) is recomputed during
verification, never trusted. The requirement-population delta is measured,
not gating.

Verification recomputes every component from the checkout and refuses any
mismatch: layer bytes, the regenerated successor contract, routing, the
semantic-authority identity and the implementation sources (an external
substitute is refused).

## Selection and rollback

```text
DE4SDV_SEMANTIC_AUTHORITY=model
DE4SDV_MODEL_AUTHORITY_BUNDLE=<path to closed bundle JSON>
DE4SDV_MODEL_AUTHORITY_BUNDLE_ID=mab-<32 hex>
```

`authority_selection.require_model_selection` accepts only `model`. Unset
(owner decision D6), `legacy`, `o3` or any other value is refused; the
message names the rollback procedure (rollback is a redeploy of the pre-C2
revision). `composition_construction.build_explicit_semantic_runtime`
routes the model selection to `build_model_authority_runtime`; every entry
point delegates to it. Activation eligibility is required by default; only
an explicit `require_activation_eligible=False` (the
`--allow-candidate-bundle` flag of the evidence scripts) serves a candidate
bundle, for evidence runs and tests. `ModelAuthorityRefused` is an
`AuthoritySelectionError`.

```python
from de4sdv.semantic.model_authority_runtime import (
    ModelAuthorityRefused, build_model_authority_runtime)

runtime = build_model_authority_runtime(
    repo_root, bundle_path, expected_id,  # None -> the two environment variables
    api_url=..., binding_path=..., expected_git_revision=...,
    require_activation_eligible=True)
runtime.authority_status()
# {"authority": "model", "bundle_id": "mab-...", "authority_id": "mab:mab-...",
#  "source_revision": "<40 hex>", "semantic_authority": "sai-...",
#  "refused": [...], "rollback": "redeploy the pre-Wave-C production revision",
#  "activation_blocked": <bool>}
```

## Successor exposure and retired names

`allocatedTo`, `hasValidationScenario` (inverse `validationScenarioFor`) and
`hasRegulatorySource` are default predicates. The Wave B deprecated aliases
are **retired names** (owner decision D4): no fact is answered under them;
every request is refused with `retired; use <successor>`. The model
retirement records are kept as history.

| Retired name | Refusal |
| --- | --- |
| `realizedBy` | `retired; use allocatedTo` |
| `deployedTo` | `retired; use allocatedTo` |
| `validatedBy` | `retired; use hasValidationScenario` |
| `validatesFitnessForUse` | `retired; use validationScenarioFor` |
| `constrainedBy` | `retired; use hasRegulatorySource` |

The impact surface's requirement-to-architecture hop traverses
`allocatedTo` (from a Requirement source only the Requirement → Function
end pair applies, exactly what the `realizedBy` alias served).

## `hasRelevantEvidenceContract` discriminator

The range is the authored type closure of the validated `EvidenceContract`
kernel root. It must contain exactly eight specializing requirement
definitions: the AEBS evidence contracts. Members are the usages explicitly
typed by the root or by one of those definitions. Any other population fails
closed with `MODEL_EVIDENCE_CONTRACT_BLOCKED_REASON`. `traversal.py` is
untouched; the discriminator is a subclass override.

## Coverage gate (blocking)

`scripts/check_model_projection_coverage.py` (module
`de4sdv/semantic/model_projection_coverage.py`) classifies every register
row, every model identity and every governed kernel declaration as
projected (layer + digest), refused, retired or residual. Mode `blocking`
(O4 Wave C2): any residual identity, any residual governed declaration and
any kernel-accounting error fails regardless of the baseline. Kernel
accounting: every governed declaration is projected by a model-generated
layer or listed in the D3 manifest with a reason, as a disjoint union (a
listed declaration that is also projected fails); a stale, reason-less or
out-of-directory entry fails; a feature slice must not re-declare a
class-mapped kernel name.

It compares the result with `model-authority-coverage-baseline.yaml`
(schema v3, no binding block), which ratchets the refused and retired sets,
the routing digest and the layer digests. With `--bundle`, it also fails
when a bundle differs from the checkout. `scripts/check_repo.py` runs it.
Current summary: 101 projected, 0 residual, 2 refused, 5 retired, 138
governed declarations (0 residual).

The model-contract → kernel mapping direction (every class mapping resolves
to its declaration in the named file) is `scripts/check_model_sync.py` sync
point 5.
