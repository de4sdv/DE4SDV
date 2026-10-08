# Drive an increment with the method tools

The DE4SDV method lives in the model: the method gates in
[`DE4SDV_MethodGates`](../../textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_gates.sysml)
state what each phase of an increment must contain. Four read-only tools
evaluate one increment against those gates, so an agent (or a person) can run
the loop **next → author → gaps**: the agent authors model content, the
deterministic evaluation judges it.

## The four tools

All four take the increment identifier: the registered `INC-<SUBJECT>-<SEQ>`
identity carried as the increment usage's declared short name, for example
`part <'INC-AEBS-010'> incAEBS010 : VisualizationIncrement`
(see [naming conventions](../naming/naming-conventions.md)). `phase` is an
optional `MethodPhase` literal, such as `phase4_needs`, that filters the answer.

| Tool | Answers |
| --- | --- |
| `next_obligation(increment, phase?)` | The first gate the agent can act on, with the failing elements, what to author and in which package |
| `method_gaps(increment, phase?)` | Every unmet blocking gate (with its subjects) and the advisory notes |
| `increment_status(increment, phase?)` | Per phase: the aggregate verdict and whether the phase exit is `READY` or `BLOCKED` |
| `phase_contract(phase?, increment?)` | The gates themselves, and for an increment whether each applies; never a verdict |

The three evaluation tools project one evaluation of the increment, so their
answers carry the same `evaluation_key`.

## How the answers are built

- **Identity.** The increment is the part usage in the `EngineeringIncrement`
  lineage whose declared short name is the identifier. Its charter
  declaration states the applicable phases; gates of undeclared phases are
  not applicable, which is reported as such, never as passed.
- **Blocking and advisory.** A gate's `required` flag decides. Structural
  checks block the phase exit; advisory gates are reported as notes.
- **Prerequisites.** A gate whose prerequisite gate has not passed is not
  attempted, and `method_gaps` names the prerequisite that blocks it.
- **Ranking.** `next_obligation` ranks open gates by their depth in the
  prerequisite graph, then by phase, then by gate order.
- **Relations.** The relation a gate checks is decided by the relation check
  of that name in `de4sdv/semantic/relation_checks.py`: a relation of the
  model-built contract through the production traversal (a connection-carried
  relation from the connections of its pinned carrier), and the native SysML
  relations `frame`, `stakeholder`, `subject` and `verify` from their
  memberships. A relation check reads only the model, never gate fields.
- **Method side versus model.** Some inputs only a method or kernel change can
  supply, for example a declaration without a validated kernel identity or a
  relation without a SysML mapping. Those gates are listed under
  `method_side_blockers`, not offered as authoring work.

Results describe model content against the declared gates only. They make no
acceptance, compliance, certification or evidence-adequacy claim.

## Offline, over a model export

The same evaluation runs without the API, over a full-model JSON export:

```bash
python scripts/evaluate_increment.py \
  --export de4sdv-full-model-export.json \
  --binding de4sdv-full-model-binding.json \
  --increment INC-AEBS-010 --query next
```

With the validated revision binding of the same commit, the evaluation key
equals the one the API service computes for that revision. Without
`--binding`, the export is evaluated as an export snapshot: kernel identity
is validated from the export by the ingestion validator, and the revision
identity carries the scope `export-snapshot`. Element source files appear in
a separate `presentation` block, because only an export records them.

## Fast restarts

The semantic MCP server keeps an identity-bound snapshot of the bound
revision's element corpus in `DE4SDV_SEMANTIC_SNAPSHOT_DIR` (default
`~/.cache/de4sdv/semantic-snapshots`). The first start on a machine loads
the corpus from the API; later starts load the snapshot. A snapshot is only
used for the exact revision, binding, semantic authority and API endpoint
it was written for; any doubt falls back to the API.
