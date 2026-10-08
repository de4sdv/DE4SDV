# O4 closure record (Wave C2, draft)

Status: **draft.** This record states what O4 Wave C2 closed and where its
evidence is. It is not a production activation record (production
deployment of a C2 revision is owner-gated:
[activation and rollback](../model-authority-activation.md)) and makes no
compliance, certification or homologation claim.

## What closed

- **One semantic authority.** The authored basic-ontology YAML
  (`approach/framework/ontology/`) was deleted. The kernel contract is built
  from the model-generated projection layers, the frozen O2-chain records,
  the model-generated successor contract and the kernel-internal
  declarations manifest (`KernelContract.from_layers`). Nothing at runtime,
  in the gates or in the tooling reads an authored ontology.
- **One runtime.** The O3 bundle runtime, the legacy runtime and the
  composed O3 + definitions runtime were deleted; the model-authority
  runtime is the only one. `DE4SDV_SEMANTIC_AUTHORITY` accepts only
  `model`; unset, `legacy` and `o3` are refused (owner decision D6).
- **Retired names refused** (D4): `realizedBy`, `deployedTo`,
  `validatedBy`, `validatesFitnessForUse`, `constrainedBy` answer
  `retired; use <successor>`; their model retirement records are kept.
- **Exceptions refused** (D5): `IncrementTraceabilityShell` (MERGE) and
  `derivesNeedFromConcern` (REMOVE) are answered only with their register
  disposition. For `derivesNeedFromConcern` this changes a Wave B gap
  answer into a refusal; the change is intentional.
- **Coverage blocking.** Any residual identity or governed declaration
  blocks; listed kernel-internal and projected declarations are a disjoint
  union (D3); refused and retired sets are ratcheted.
- **Bindings v2.** Revision bindings carry the model-built
  semantic-authority identity (`sai-…`); v1 bindings are refused.
- **Consumer ledger closed** (D7): every remaining reference to the
  authored ontology is documentation, a frozen record, historical tooling,
  a test reference, or the governance machinery that names the tokens
  ([consumer-ledger.yaml](../consumer-ledger.yaml)).

## Evidence

- [contract-equivalence.json](contract-equivalence.json): the last
  executable comparison of the authored ontology (oracle: the Wave B
  revision `6dab3e9`, run in a temporary worktree) with the model-built
  contract, taken at the stage-4 commit before the deletion (reproducible
  there with `scripts/compare_model_contract.py`, deleted in stage 5). The served contracts differ in exactly the
  two refused exceptions and the five retired names; the authored-contract
  differences are classified (none unclassified); the 54 batch-2
  contract fields held by the admission manifest and the 22 batch-1
  reviewed definitions are equal to the authored ones (D9). The record
  also keeps the authored identity lists, definitions and validation
  rules the tests now lock to.
- **Branch-bound artifacts** (the C2 PR must be merged with a merge
  commit, never squashed; each bound commit must stay an ancestor of
  `main`):
  - the regenerated definition batch-1 and vocabulary-carrier pairs, bound
    to branch commit `01acc00`;
  - the definition batch-2 pair, bound to branch commit `6a7538c` (it was
    regenerated after the two stale successor-definition comments were
    corrected in review);
  - [contract-equivalence.json](contract-equivalence.json)
    `model_revision`, bound to branch commit `7cf719c`
    (`tests/test_o4_wave_c2_closure_evidence.py` requires it to be an
    ancestor of HEAD and the comparison script to exist there).
- The C2 PR's gate and suite results at its head, and the without-YAML
  runs of `verify_generated_chain`, `check_model_sync` and `check_repo`.

## Supersession of frozen records

The frozen O1/O2/O3 records are not edited. Where they describe the
authored ontology as the active authority, the deprecated aliases as
answerable, or the O3/legacy selectors as rollback paths, this record and
[model-authority-runtime.md](../model-authority-runtime.md) supersede them
from O4 Wave C2 on.

Two frozen labels are stale and stay unchanged with the frozen file:
`frozen-records.json` (and `LIVE_CONSUMERS` in
`scripts/verify_generated_chain.py`, which must match it) still name an
"O3 equivalence basis" reader of `o1/semantic-authority-inventory.json`, an
"O3 equivalence lane" reader of `o3/o3-equivalence-scope.json`, and the
"O3 bundle" as a reader of the O2 profiles and projections. The O3 runtime
and its equivalence machinery were deleted in C2, so those readers no
longer exist; the model-authority runtime's o2-chain layer is the only
remaining live reader of the O2 files.

## Open follow-ups

- D9: move the 54 manifest-held batch-2 contract fields into the model
  (follow-up issue), and the domain and range of `usesVerificationMethod`
  (authored as `VerificationCase -> VerificationMethod`; the model-built
  contract provides the identity as O2+ vocabulary only, without a
  relationship mapping).
- The two successor-definition comments that still described the authored
  ontology as present (`allocatedToVocabularyRole`,
  `hasEvidenceStatusVocabularyRole`) were corrected in review (comment
  bodies only; the comment-stripped model text is byte-identical). They are
  model-owned definitions, so the owner reviews the new wording with the
  PR.
