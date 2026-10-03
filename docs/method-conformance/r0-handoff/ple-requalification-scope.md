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

## Executable observation path (draft, not qualification acceptance)

`scripts/run_ple_qualification.py` uses the original frozen experiment in a
separate read-only checkout. It does not copy its model or vendor PLEML into
the current product model. The current executor, its library-lock digest,
installed serializer, frozen interpreter, pinned PLEML input and historical
export revisions are recorded independently.

The `Privileged PLE Qualification` workflow checks a reviewed permanent
executor SHA, verifies the provider-side origin of the retained Gate A
artifact, freshly serializes the frozen inputs with the current pinned
serializer, and imports them into an isolated loopback API. Both provider
run identities and the exact retained artifact ID are cross-checked. UUID,
metatype and internal-reference readback (including reference multiplicity
and canonical reference shape) are checked before concept-specific
observations and the historical comparison are retained. The executor's
library lock is recorded as current context; unrelated current product-model
libraries are not claimed to be exercised by the frozen fixture.

For a diagnostic replay only:

```bash
python scripts/run_ple_qualification.py \
  --experiment /path/to/frozen-experiment \
  --historical-export /path/to/de4sdv-pleml-gate-a-export.json \
  --out /path/to/new-receipt.json
```

The fresh path additionally requires `--expected-executor` and
`--api-url http://127.0.0.1:9000`; it refuses non-loopback API writes,
uncommitted executing sources, changed frozen inputs and overwritten receipts.
The CI workflow retains actual export, API binding, readback, interpreter
outcomes, pruning records and all six case observations. A disappeared or
expired historical artifact is a refusal, not permission to invent a baseline.

This path does **not** complete PLE-Q. Observability rows without
concept-specific adequacy remain gaps. Differences are `review-required`
until independently classified; all qualification/adoption/activation
acceptance flags remain false.

## Missing-scope executable probes (draft)

`scripts/run_ple_scoped_execution.py` is one executable package, not another
observation-review harness. It verifies the original read-only oracle and PLEML
pin, generates independent small synthetic graphs and a new draft SysML source,
then executes the frozen bounded group resolver. It does not copy the frozen
fixture or library. `--binding-count` selects 2–8 linkage-only dependencies from
one asset to distinct features; no AND/OR/precedence rule is supplied.

```bash
python scripts/run_ple_scoped_execution.py \
  --experiment /path/to/frozen-experiment \
  --binding-count 2 --out /path/outside/repository/new-probes
```

Both direct literal-bound and `..` operator graph forms execute at-least-one,
multi-select and none scenarios (six rows). None must fail the lower bound.
These graphs are explicitly **synthetic test doubles**, not serialized model
outputs or API evidence. Their bounded interpreter results establish neither
native evaluation nor disjointness. Development-only scope is not a lifecycle
stage evaluator. Generated source remains draft pending licensed validation.
Syntax traces: pinned PLEML `FeatureBinding` at lines 203–217 and XOR body at
170–176; frozen group primitives at `tools/pleml_gate_a.py:918–1179`.

`--native-xor` retains a failed/unsupported native requirement, source location,
counterexample population and rerunnable command, and exits **2** rather than
pretending that the specialized incompatibility resolver executed XOR. Without
licensed execution, the native range/vacuity defect is **not reproduced**.

The existing privileged workflow now also invokes this package with `--licensed`
and `--expected-executor` at its reviewed permanent SHA. It serializes only the
new generated source plus the verified original pinned library, retains actual
elements/diagnostics, and attempts `syside.Compiler.evaluate(nativeXorProbe)`
with a bounded step budget. This interface was source-inspected in the existing
Syside type stubs; it documents limited function/body-expression support.
No local ARM licensed execution is claimed. The workflow retains exit 2 and
requires fresh serialization plus an explicit `attempted: true`; missing or
ambiguous `ConstraintUsage` selection is an execution error, not an unsupported
attempt. The receipt initializes `attempted: false` and records candidate count,
UUIDs and source document URLs. A genuinely attempted compiler refusal can
retain exit 2 without becoming qualification. No new API ingestion or
acceptance path is added.

The native call and materialization of returned value representations and
compiler diagnostic fields occur under the target's document lock. Actual
`CompilationReport.diagnostics` entries retain message, code, severity, source
and UTF8 segment offset/end where available; `fatal` stays separate. Refusal
messages come from those entries, not an opaque `str(CompilationReport)`.
Diagnostic `source` is a producer label, not necessarily a source file; the
target document URL supplies context. Offsets are not interpreted as line/column
mappings. This is single-threaded orchestration, not a claim of arbitrary
concurrent-model safety or native instance correctness.

Workflow tests set `DE4SDV_PLE_ORACLE` to the separate `_ple-experiment` checkout;
a configured missing/empty oracle fails instead of silently skipping. Local
unconfigured tests may still skip if the optional `/tmp/de4sdv-pleml-gate-a`
checkout is absent. Oracle identity and pins are verified by the existing
read-only loader. Clearly labeled synthetic API fakes test selection, emitted
receipt diagnostics, workflow predicates and lock lifetimes only: they prove
neither Syside semantics nor licensed/native execution.

Global presence of literal/operator ranges and dependency anchors is reported
separately from per-group evaluation, binding metadata/provenance adequacy and
Boolean instance constraint correctness; those remain explicit gaps. A returned
compiler value is retained unqualified, not interpreted by a custom native
solver. Receipts hash generated artifacts, the executing script and current
library lock; existing receipts and repository-contained output are refused.

### Scoped fixture typing repair (draft; native validation pending)

Retained privileged run **36853224284**, executor
`23d48abc54fc76fbee1726aa163c34197d899251`, failed scoped serialization with
**17 reference errors**. Four configuration usages incorrectly subset the
`ScopedTree` occurrence **definition** as though it were a Feature. The other
errors are unresolved inherited group/member names. Its receipt records
`executor_source_dirty: true`, `fresh_serialization: false`, and XOR
`attempted: false`; the later API observation step was skipped. This is a
fixture-typing failure, not evidence of native XOR evaluation or its suspected
range/vacuity defect. Preserve the original failed receipt, generated source,
serializer diagnostics and workflow log unchanged; do not relabel that run.

All four generated usages (`atLeastOne`, `multiSelect`, `noneSelected`, and
`xorCounterexample`) now use `: ScopedTree :> featureConfigurations`: typing
targets the definition, while subsetting still targets the pinned library's
configuration **usage**. At the unchanged PLEML pin, `PLEML/PLEML.sysml:55–72`
declares `FeatureConfiguration` and `featureConfigurations`, and lines 187–201
define tree/configuration metadata. The pinned drone example
`Examples/MBPLE-Example-DroneProductLine-PLEML-SysMLv2-FeatureModel.sysml:28,61–81`
subsets `droneProductLineFeatureTree`, an occurrence **usage**, not a definition;
that form cannot be copied unchanged onto `ScopedTree`.

The common builder feeds both ordinary diagnostic emission and the licensed
serializer's `scoped-fixture.sysml` input, including the empty-group diagnostic
and XOR negative fixture. Lexical regressions cover every supported binding
count (2–8) and all four headers. CLI regressions cover ordinary and
`--native-xor` emission, group selections, the single excluded feature, binding
endpoints, artifact digest and unchanged false acceptance flags. These tests
do **not** parse or validate SysML with Syside and do not evaluate native XOR.

**Requested gate after source review/delivery:** maintainer-run validation on
the delivered exact commit SHA, using Syside **0.10.3** and the unchanged
verified PLEML pin. No licensed dispatch or API activation is authorized by
this repair. Retain a new, separate receipt and diagnostics: first require
error-free scoped loading/serialization, then exactly one `nativeXorProbe`
target and a real bounded Compiler attempt (`attempted: true`). Any additional
type/reference errors remain draft failures; typed parse progress alone is
not XOR/solver evidence. Keep the native requirement failed/unqualified,
exit 2, and all qualification/adoption/authority-activation flags false even
if serialization succeeds. Local aarch64 tests cannot discharge this gate.
The vendor/oracle, library/toolchain pins, catalogue/configurator authority,
semantic agents and workflow are unchanged.
