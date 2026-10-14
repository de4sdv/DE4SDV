# Generate semantic assets with the source change

A model edit is one commit. The projection and profile files that the runtime
reads are generated from the current sources, so you regenerate them in the
same commit as the model change. They name no Git commit, so the pull request
can be squash-merged.

## When you need this

`python scripts/check_repo.py` compares each generated file with a fresh
regeneration. It fails when a file is missing or stale and names the
generator to run. Typical triggers are edits to a definition or its `doc`
text in the method kernel (`textual-notation-of-model/packages/methods/de4sdv/`),
to the few feature files that witness a projected concept, to an admission
manifest, or to the Syside version pin in
`.github/workflows/privileged-syside-validation.yml`.

## Regenerate, check, commit once

From the repository root, with the pinned dependencies installed:

```bash
sysand sync
python scripts/generate_definition_projection.py --batch all
python scripts/generate_native_grounding_projection.py
python scripts/generate_trace_vocabulary_contract.py
python scripts/check_repo.py
python scripts/smoke_test.py
python tools/check_markdown_links.py
python -m pytest tests -q -p no:cacheprovider
python tools/run_bench_unit_tests.py
```

Run the generators in this order. The trace-vocabulary generator runs
last: it reads the relation and retirement records of
`de4sdv_trace_vocabulary.sysml` and checks their endpoint classes against the
class pins of all the layers before it.
The runtime reads its output, `trace-vocabulary-contract.json`, and never
parses the model.

Stage the source change and the regenerated files together and make one
commit. Do not create a source-only commit first, and do not pass a source
revision: the generators no longer accept one.

### The coverage baseline

`check_repo.py` also compares the model-authority coverage with
`de4sdv/semantic/contract-data/model-authority-coverage-baseline.yaml`. The
baseline is a reviewed ratchet for the provider routing and the refused and
retired names. A residual identity, an unaccounted kernel declaration or a
duplicate provider fails regardless of the baseline. Rewrite the baseline
only when the change is meant to alter routing, refusals or retirements, and
say so in the pull request:

```bash
python scripts/check_model_projection_coverage.py --write-baseline
```

## Frozen records are different

The [frozen records](../../de4sdv/semantic/contract-data/frozen-records.md)
and their manifest never change. `scripts/verify_generated_chain.py` checks
their bytes, record set, recorded source revisions and references. Never
regenerate them against current sources. Their mentions of deleted inputs are
history, not a live dependency.

The closed consumer ledger is retired. A guard test keeps the deleted
ontology file and the ledger from coming back. It scans every tracked file
outside `docs/` and `tests/` case-insensitively and without extension
filtering or truncation. It exempts only the six frozen records and the
ontology review record, which name the deleted file as history.

## Identity and releases

The semantic-authority identity (`sai-…`) digests what the generated files
mean: definitions and their documentation, groundings, relationship ends,
strength and support, serializer mappings, refusals, retirements and the
trace-vocabulary contract. It does not digest Git commits, file bytes, Python code,
review pointers or toolchain receipts. It does label each layer with its
file path, so moving or renaming a projection, profile or frozen record
changes the identity. `de4sdv/semantic/model_contract.py` declares which
fields carry meaning and which are provenance. A field in neither list makes
the loader refuse, so a new field is classified before it can ship.

A change in meaning changes the identity. Deployment still checks the
application revision and the validated-export binding separately. The next
privileged run mints a deployment binding with the new identity; never
hot-apply a new identity to a deployment bound to an older one.
