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
`check`, `increment`, `applicablePhases`, `expectedArtifacts`,
`systemOfInterest`) select features of elements reached that way, and
`expectedArtifacts` names top-level packages by their declared names.

- **Scope.** A check's subjects are the elements that conform to the
  parameter (typed by its type, or of its usage kind when it is untyped). For
  the framing step they come from the increment's own package, the package
  that owns the increment usage and its charter; for the later steps, from the
  packages the charter declares in `expectedArtifacts`, with their nested
  packages. A value that names no single top-level package leaves the later
  steps' subjects unresolved, never narrower, and fails
  `incrementDeclaresExpectedArtifacts`. On framing subjects
  `ownedByIncrementPackage` holds by construction; the population bounds carry
  that rule until a model change removes the redundancy. Content in a package
  the charter does not name is never evaluated;
  `charterExpectedArtifactsCoverContent` reports such a package (advisory).
- **Subject.** Needs and requirements take the increment's system of interest
  as subject, the one the charter declares in `systemOfInterest` by
  reference to a usage or by type, never the increment. A subject matches
  when it is, narrows, or is typed by that system of interest's definition or
  a specialization of it (type-level: another usage of the definition also
  passes); `subjectIsSystemOfInterest` reports a deviation (advisory).
- **Population.** The parameter's multiplicity bounds the number of subjects:
  `[1]` means exactly one, `[0..*]` lets an empty population mean "does not
  apply". `phase_contract` gives it per check as `population`, for example
  `[1, "*"]` for "the increment package owns at least one assumption". Its
  `cardinality` is a different count: the distinct targets each subject must
  reach through the check, such as the one package that owns each assumption
  (`[1, 1]`). A claim of "at least one" reads on whichever of the two it
  counts.
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
| `next_obligation(increment, phase?)` | The first check the agent can act on, in workflow order, with the failing elements, what to author and in which package; `reason` always says why it was chosen, or why none is open |
| `method_gaps(increment, phase?)` | Every unmet blocking check (with its subjects) and the advisory notes |
| `increment_status(increment, phase?)` | Per phase: the aggregate verdict and whether the phase exit is `READY` or `BLOCKED`; a declared phase without executable checks is listed as such, its exit blocked by the method, never by a gap |
| `phase_contract(phase?, increment?)` | Every workflow step with what it declares (`steps`), the checks themselves (`gates`), and for an increment whether each applies; never a verdict |

The three evaluation tools project one evaluation of the increment, so their
answers carry the same `evaluation_key`. Each answer also says what it
covers: see coverage and revision below.

To learn a definition an answer names, pass its qualified name to
`inspect_element`: a check's `subject_type`, a step parameter's `type` or a
step's `definition`, for example `DE4SDV_IncrementWorkflow::IncrementCharter`.
It lists the definition's owned and inherited features with their keywords,
types and multiplicities, and an enumeration's values, such as the 13
`MethodPhase` literals (see
[name an element, describe a definition](query-the-public-model-via-mcp.md#name-an-element-describe-a-definition)).
A `subject_type` without `::`, such as `ConcernUsage`, is the SysML metaclass
of an untyped parameter, not a model element (`subject_type_kind` is
`metaclass`); you declare such a subject by its `subject_keyword`, for example
`concern`.

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
- **What to author.** `what_to_author` (and `what_satisfies` in
  `phase_contract`) is SysML built from the step parameter the check is about:
  its keyword, its type's qualified name with the `private import` of that
  type's package, the types the check admits, and the order of declarations,
  such as a subject before stakeholder members. `authoring` gives the same as
  `declarations`, `imports`, `types` and `notes`; a placeholder in angle
  brackets is a name or text you choose, never a type.
- **Coverage.** Only some steps of the workflow carry checks. `phase_contract`
  lists every step in `steps`, with its phase, documentation, inputs and
  outputs (name, kind, type, multiplicity) and its checks; a step without
  checks has the coverage "no executable checks at this revision". In
  `increment_status`, every phase the charter declares that no executable
  check judges is listed with that coverage and its step's declared outputs
  (no step: `step` null, no outputs), also when the workflow cannot be read.
  It is never evaluated (`UNASSESSED`, reason `CONTRACT_UNAVAILABLE`), so its
  exit stays `BLOCKED` by the method, not by your model: it is never a gap,
  `method_gaps` and `next` never list it, and nothing you author opens it at
  this revision (its `exit_note` says so). Every evaluation answer carries
  `coverage`: the phases with executable checks, and the declared phases
  without them. Zero blocking gaps, or `next` none, says nothing about the
  latter, and `next_obligation`'s `reason` names them.
- **Revision.** An answer evaluates the bound revision, named in `revision`,
  and nothing else. The `increment` block's `resolution` says how the
  identifier resolved there: `resolved`, `ambiguous` (several increment
  usages carry it), `lineage-unavailable` (the `EngineeringIncrement`
  lineage cannot be established) or `not-declared` (no increment usage
  carries it). For `not-declared` the block adds a `message` that names the
  revision and says that a usage without the identifier as its short name,
  such as a legacy increment, is not found either; `next_obligation` gives
  it as its `reason`. Work on a branch is invisible to the deployed
  revision: the PR Method Check evaluates the head of a pull request. `next`
  still names the framing check that declares a new increment (for example
  `INC-EXAMPLE-001`). `resolution` is not a reason code of the result
  algebra, so it never appears in `reason_codes`.
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

## On a pull request

Every pull request that touches the model, the check's own scripts and
workflow, or a module or data file the evaluation reads (the `de4sdv`
semantic and SysML API packages, and the data files of the trace-vocabulary
contract listed in `model_contract.TRACE_CONTRACT_INPUTS`) runs the
**Method Check** workflow
([`method-check.yml`](../../.github/workflows/method-check.yml)). It exports
the pull-request head with the licensed serializer, finds every increment the
model declares (through the charters and the increments' short names), and
runs `scripts/evaluate_increment.py` for each one over that export. A run
takes a few minutes; no ingestion is involved.

The check is advisory: gaps never fail it. It fails only on a technical
error, such as a failed or refused export, a refusal of the evaluation entry
point (exit code 2), or a workflow that cannot be read (`INVALID_CONTRACT`).
An increment whose method is unavailable, for example because its charter
declares no workflow, is reported, not failed. Pull
requests from forks get no licensed export; a maintainer can run the workflow
by hand with the reviewed ref.

Read the result for your head commit:

```bash
sha=$(git rev-parse HEAD)
run=$(gh api "repos/{owner}/{repo}/actions/workflows/method-check.yml/runs?head_sha=$sha" \
  --jq '.workflow_runs[0].id')
gh run view "$run"          # status; add --log to read the summary in the job log
gh run download "$run" -n "method-check-$sha"
jq '.increments[] | {id, outcome, next: .next.gate, counts}' method-check.json
```

`method-check.json` has one entry per increment in `increments`:

| Field | Holds |
| --- | --- |
| `id`, `outcome` | The increment identifier, for example `INC-AEBS-010`; `evaluated`, `method-unavailable`, `method-invalid`, `refused` or `error` |
| `next` | The first check to act on: `gate`, `stage`, `kind`, `what_to_author`, `authoring`, `where`, `subjects`; `null` when none is open |
| `counts` | `blocking`, `blocking_by_kind`, `advisory`, `method_side_blockers` |
| `phase_exits`, `phase_checks` | Per phase with executable checks: `READY` or `BLOCKED`, and how many of its checks pass (`pass`, `total`, `not_applicable`) |
| `phases_without_checks` | The declared phases whose step has no executable checks: `phase`, `step` and its `outputs`; never evaluated, so the counts say nothing about them |
| `evaluation.gaps.blocking` | Every unmet blocking check with all its subjects; `evaluation.gaps.advisory` holds the advisory notes |
| `evaluation` | The full `scripts/evaluate_increment.py` report: `status`, `gaps`, `next`, `contract` |

The summary shows the next check's imports and declarations as a SysML block
to copy. The top-level `errors` lists technical errors, and `notes` lists what could
not be evaluated, such as a charter whose increment carries no identifier.
Such an increment is also listed in `not_evaluated` with its `usage`,
`charters` and `reason` (outcome `not-evaluated`), and the summary shows it
as a "not evaluated" row: the method finds an increment only by its
identifier, so it never evaluates one without it.
The artifact also holds one `<increment id>.json` per increment and the
summary as `method-check.md`. The export stays available for three days as
`method-check-export-<sha>`, so you can repeat the evaluation locally with
`--phase` or another `--query`.

## Fast restarts

The semantic MCP server keeps an identity-bound snapshot of the bound
revision's element corpus in `DE4SDV_SEMANTIC_SNAPSHOT_DIR` (default
`~/.cache/de4sdv/semantic-snapshots`). The first start on a machine loads
the corpus from the API; later starts load the snapshot. A snapshot is only
used for the exact revision, binding, semantic authority and API endpoint
it was written for; any doubt falls back to the API.
