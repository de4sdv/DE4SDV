# Model-authority runtime

Status: **draft.** This record describes the runtime that serves the
model-built kernel contract: Wave B and the Wave C closure decisions
(2026-10-07/08), and the retirement of the model-authority bundle, closure
and activation ceremony (owner decision 2026-10-11). It claims no
compliance or certification. Deployment, release and rollback are in
[`deployment/README.md`](../../deployment/README.md).

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

- the model-generated pairs in
  [`de4sdv/semantic/contract-data/`](../../de4sdv/semantic/contract-data/README.md):
  class definitions (`class-definition-projection.json` / `-profile.json`),
  kernel vocabulary (`kernel-vocabulary-…`), native groundings
  (`native-grounding-…`) and increment relationships
  (`increment-relationship-…`);
- the frozen-record layer: 13 identities read from the six frozen
  projection/profile records (`frozen-records/semantic-projection-v1…v1.2`
  and their profiles), which never change;
- the successor contract generated from the model
  (`relationship_successor_contract.generate_contract`, class pins from the
  layers);
- the kernel-internal declarations manifest
  ([kernel-internal-declarations.yaml](../../de4sdv/semantic/contract-data/kernel-internal-declarations.yaml),
  owner decision D3), the governed-directory accounting.

Its **semantic-authority identity** (`sai-<32 hex>`) hashes semantic payload,
not raw application or artifact bytes. It covers:

- path-labelled declared projection/profile semantics, including definition
  text, exact grounding, representation rules and claim boundaries;
- the served class mappings, full relationship specifications/mappings and
  refusal/disposition strings;
- lineage ownership and the complete successor payload: schema, supersession,
  class/carrier file-declaration pins, relationship records and retirements.

The identity's layer `sha256` values are semantic digests, not file checksums.
Both paths of a live pair carry that pair's semantic digest; historical paths
carry the selected historical semantic-output digest. Raw file hashes and
historical source revisions remain separate provenance. Incidental Git commits,
Python bytes, pilot data, unrelated model bytes and review/toolchain receipts
are excluded. Unknown record fields require explicit classification and refuse.
See [the generation workflow](../guides/generated-semantic-assets.md) for
the exact exclusions and release boundary. Revision bindings carry this value
as `semantic_authority`; old authored-ontology bindings remain refused.

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
[closure/contract-equivalence.json](https://github.com/de4sdv/DE4SDV/blob/release-2026-10-11/docs/method-conformance/o4/closure/contract-equivalence.json). The
served contract differs from the authored one in exactly seven identities:
the two refused exceptions and the five retired names. The 54 batch-2
contract fields held by the admission manifest (domain/range/strength,
mechanics, kernel mapping kind, ontology relations) are recorded there with
their pre-deletion equality (owner decision D9).

## Runtime construction

`de4sdv/semantic/deployment_runtime.py` builds the production runtime of the
Ask viewer, the semantic MCP server and the batteries from four inputs: a
clean checkout of the deployed commit, the deployment's revision binding, the
deployed API, and one startup check (`verify_startup`). The check refuses
unless:

- **right commit:** the checkout HEAD is the application revision, the
  binding is a passed full-model binding of the expected model revision, and
  the application revision descends from it;
- **clean tree:** `git status --porcelain` is empty;
- **same semantic authority:** the `sai-` identity that
  `build_model_contract` recomputes from the checkout equals the binding's;
- **served model = validated export:** the binding records the served model
  (`served_model`: export file digest, element count, content digest; written
  by the importer after its full-payload read-back), and the service accepts
  a corpus only when its content digest is exactly that record's
  (`de4sdv/sysml_api/served_model.py`). This runs when a corpus loads, from
  the API or from a snapshot. A refused snapshot is a miss; a refused API
  corpus raises `ServedModelMismatchError` on every call.

`build_deployment_runtime` then assembles the facade over the verified
contract (`model_authority_runtime.model_facade`) and the services
(`assemble_model_services`). It installs the served-model guard on the
repository. The served semantic-authority id is the contract identity
(`sai-…`). Every refusal raises `StartupCheckError` before the API is read;
nothing falls back.

```python
from de4sdv.semantic.deployment_runtime import build_deployment_runtime

runtime = build_deployment_runtime(
    repo_root, api_url=..., binding_path=..., expected_git_revision=...)
runtime.authority_status()
# {"kind": "model", "startup_check": "passed", "semantic_authority": "sai-...",
#  "semantic_authority_id": "sai-...", "git_commit": "<40 hex>",
#  "served_model": "sha256:...", "served_model_check": "pending|passed|failed: ...",
#  "refused": [...], "rollback": "redeploy the previous release", ...}
```

There is no bundle, closure attestation, activation-eligibility gate or
authority selector. The bundle bound a digest of what the checkout already
fixes. Its closure re-ran evidence against the deployed API. Both chose
between two authorities, and after Wave C2 there is one. The exact commit,
the clean tree, the `sai-` equality and the served-model digest guard the
same things at every start. Release evidence over the export runs in the
privileged run (`scripts/check_release_evidence.py`).

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

It compares the result with `model-authority-coverage-baseline.yaml`, which
ratchets the routing digest and the refused/retired sets only. Report layer
digests remain diagnostic provenance, not baseline inputs. Regenerate the
baseline with `--write-baseline` after a reviewed routing or disposition change.
Residuals, duplicates and kernel-accounting errors remain absolute blockers.
`scripts/check_repo.py` runs it. Current
summary: 101 projected, 0 residual, 2 refused, 5 retired, 158 governed
declarations (0 residual).

The model-contract → kernel mapping direction (every class mapping resolves
to its declaration in the named file) is `scripts/check_model_sync.py` sync
point 5.
