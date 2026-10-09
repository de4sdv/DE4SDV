# Genuine export cut

`inc-aebs-010.json.gz` is a frozen sample of real serializer shapes. It is a
cut of the licensed full-model export of one revision, made by
`cut_increment_export.py` beside it. The cut keeps every element unchanged:

- INC-AEBS-010's framing and needs packages, and the package elements of its
  other declared packages;
- the increment workflow;
- every kernel declaration the contract binds;
- the library attribute bases its content redefines;
- what those elements reference.

## What the tests use it for

The tests evaluate this frozen cut, never the current model:

- `tests/test_genuine_export_evaluation.py` evaluates it end to end as an
  export snapshot;
- unit tests adopt its method layer (kernel, workflow, library) through
  `cut_method_builder`;
- one test checks that the cut is consistent with its own records: its
  canonical serialization, the sha256 of its elements and element sources,
  and a source manifest that lists every source file. It is never compared
  with the model files at HEAD.

The file records its source revision (`git_commit`) and the sha256 of the
source export, for information only. That revision need not be on main: its
branch may have been squash-merged.

## When to re-cut

Model content changes never require a re-cut. The live model is evaluated on
each model pull request by the method check, not by these tests.

Re-cut the fixture when the exporter, the Syside version or the export format
changes. Re-cut it also when the contract binds a kernel declaration the cut
does not carry: the export evaluation refuses such an export, by design.
Re-cutting needs a licensed export:

```bash
python tests/fixtures/genuine_export/cut_increment_export.py <export.json> INC-AEBS-010 \
  tests/fixtures/genuine_export/inc-aebs-010.json.gz \
  DE4SDV_AEBSVisualizationFraming DE4SDV_AEBSVisualizationNeedsRequirements
```
