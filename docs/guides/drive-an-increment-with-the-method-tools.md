# Drive an increment with the method tools

The DE4SDV method lives in the model: the steps of the increment workflow and
the method checks about their artifacts state what each phase of an increment
must contain. Four read-only tools evaluate one increment against those checks,
so an agent (or a person) can run the loop **next → author → gaps**: the agent
authors model content, the deterministic evaluation judges it.

## Method representation

The method of an increment is the workflow its charter declares
([`DE4SDV_IncrementWorkflow`](../../textual-notation-of-model/packages/methods/de4sdv/de4sdv_increment_workflow.sysml)).
The tools reach it through native relations from validated identity: the
increment's charter (IncrementTraceObligations lineage) -> its definition's
`workflow` feature -> the workflow definition -> its step actions in
succession order -> each step's `phase`, parameters and `MethodCheck` metadata
about a parameter (`check`, `minimum`, `advisory`). Members, phase and check
values may be inherited from the definitions a step or check specializes; a
redefinition replaces what it redefines, so an increment can tailor a step.
No element is identified by its name. Member names (`workflow`, `phase`,
`check`, `increment`, `applicablePhases`, `expectedArtifacts`) select features
of elements reached that way, and `expectedArtifacts` names top-level packages
by their declared names.

- **Scope.** A check's subjects are the elements that conform to the
  parameter (typed by its type, or of its usage kind when it is untyped). For
  the framing step they come from the increment's own package, the package
  that owns the increment usage and its charter; for the later steps, from the
  packages the charter declares in `expectedArtifacts`, with their nested
  packages. A value that names no single top-level package leaves the later
  steps' subjects unresolved, never narrower, and fails
  `incrementDeclaresExpectedArtifacts`. On framing subjects
  `ownedByIncrementPackage` holds by construction; the population bounds carry
  that rule until a model change removes the redundancy.
- **Population.** The parameter's multiplicity bounds the number of subjects:
  `[1]` means exactly one, `[0..*]` lets an empty population mean "does not
  apply".
- **Applicability.** Framing always applies; a later, optional step applies
  when the charter declares its phase.
- **Every check is evaluated.** The step order only ranks `next`; an open check
  never blocks a later one.

Check ids resolve in `de4sdv/semantic/method_checks.py`; an unknown id makes the
method invalid. `de4sdv/semantic/increment_workflow.py` is the only module that
knows this representation.

## The four tools

The three evaluation tools require the increment identifier, and
`phase_contract` takes it optionally: the registered `INC-<SUBJECT>-<SEQ>`
identity carried as the increment usage's declared short name, for example
`part <'INC-AEBS-010'> incAEBS010 : VisualizationIncrement`
(see [naming conventions](../naming/naming-conventions.md)). `phase` is an
optional `MethodPhase` literal, such as `phase4_needs`, that filters the answer.

| Tool | Answers |
| --- | --- |
| `next_obligation(increment, phase?)` | The first check the agent can act on, in workflow order, with the failing elements, what to author and in which package |
| `method_gaps(increment, phase?)` | Every unmet blocking check (with its subjects) and the advisory notes |
| `increment_status(increment, phase?)` | Per phase: the aggregate verdict and whether the phase exit is `READY` or `BLOCKED` |
| `phase_contract(phase?, increment?)` | The checks themselves, and for an increment whether each applies; never a verdict |

The three evaluation tools project one evaluation of the increment, so their
answers carry the same `evaluation_key`.

## How the answers are built

- **Identity.** The increment is the part usage in the `EngineeringIncrement`
  lineage whose declared short name is the identifier. Its charter
  declaration states the applicable phases; checks of undeclared optional
  steps are not applicable, which is reported as such, never as passed.
  Without exactly one charter (a new increment, or two charters) the
  increment is evaluated against the one workflow the revision's charters
  declare: framing says what to author first, the later steps stay unresolved.
- **Blocking and advisory.** A check's `advisory` flag decides (default:
  blocking). Blocking checks hold the phase exit; advisory checks are reported
  as notes.
- **Ranking.** `next_obligation` returns the earliest open blocking check in
  workflow order (step order, then check order).
- **Relations.** A check that names a relation is decided by the relation check
  of that name in `de4sdv/semantic/relation_checks.py`: a relation of the
  model-built contract through the production traversal (a connection-carried
  relation from the connections of its pinned carrier), and the native SysML
  relations `frame`, `stakeholder`, `subject` and `verify` from their
  memberships. A relation check reads only the model, never method fields.
- **Method side versus model.** Some inputs only a method or kernel change can
  supply, for example a declaration without a validated kernel identity or a
  relation without a SysML mapping. Those checks are listed under
  `method_side_blockers`, not offered as authoring work. A check with an
  authorable failure stays actionable; its method-side subjects are listed
  apart as `method_side_subjects`.
- **Library attributes.** `source`, `rationale` and `verificationMethod` count
  only when they redefine a feature of the subject's own type lineage (in the
  model, the ODE4HERA `RequirementsManagement` attribute bases). The contract
  binds no library declaration, so this is a lineage rule.

Results describe model content against the declared checks only. They make no
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
is validated from the export as the ingestion importer validates it, and the
same failures refuse it (exit 2); the revision identity carries the scope
`export-snapshot`. Element source files appear in
a separate `presentation` block, because only an export records them.

## Fast restarts

The semantic MCP server keeps an identity-bound snapshot of the bound
revision's element corpus in `DE4SDV_SEMANTIC_SNAPSHOT_DIR` (default
`~/.cache/de4sdv/semantic-snapshots`). The first start on a machine loads
the corpus from the API; later starts load the snapshot. A snapshot is only
used for the exact revision, binding, semantic authority and API endpoint
it was written for; any doubt falls back to the API.
