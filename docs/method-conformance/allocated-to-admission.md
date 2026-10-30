# Native allocation admission evidence

The API-side method checks that read native allocations were withheld while
`allocatedTo` had two open forward obligations. Both now have retained
exact-revision evidence. The admission records their discharge; it does not
remove the checks.

## Evidence subject

- Execution revision: `ab551cec7b1de0cdc3c1431aa65709569df75381`.
- Workflow: `.github/workflows/privileged-full-model-api-ingestion.yml`.
- Successful run: [40931858718](https://github.com/de4sdv/DE4SDV/actions/runs/40931858718).
- Successful step: `Exercise production semantic concerns and the successor parity`.
- Artifact: [12934060375](https://github.com/de4sdv/DE4SDV/actions/runs/40931858718/artifacts/12934060375),
  `full-model-api-ingestion-ab551cec7b1de0cdc3c1431aa65709569df75381`.
- Archive SHA-256: `3cd8fccd27f354e03e20a019f2d8b89abfe4b96b4dad2856f48e39fc6c70ff08`.

The run metadata, checkout log and artifact digest identify that execution.
The retained archive and extracted files were byte-checked against that digest.
This is historical evidence, not an ingestion run of the admission candidate.
Owner authorization is not execution evidence.

## Obligation map

Both records cite `de4sdv-full-model-semantic-query-coverage.json`, SHA-256
`90ba497f29341f75e16fcadb5ad65df2b018cfd7607b4666d64dbd428dcfacaf`.
Its `git_commit` names the execution revision above.

| Obligation | Exact artifact keys and observed values | Bounded result |
| --- | --- | --- |
| Exact-revision traversal evidence | `successor_parity.schema` = `de4sdv.successor-parity/v1`; `successor_parity.passed` = `true`; `successor_parity.relations.allocatedTo.passed` = `true` | The API-served traversal and the method reader return the export's source, target, end-pair and witness tuples. All six relation checks pass, with empty differences, reader problems and incomplete answers. |
| Exact-revision API closure of typed allocation ends | `successor_parity.allocation_end_closure.passed` = `true`; `.allocations` = `100`; `.end_pair_classes.Requirement.closed`, `.Function.closed`, `.LogicalElement.closed`, `.PhysicalElement.closed` = `true` | The kernel bindings equal the profile pins and export identities. All four closure checks pass: served ends are readable, allocation ends match the export and typing decides. |

The traversal records 26 `RequirementFunctionAssignment`, 27
`FunctionLogicalAssignment` and 36 `LogicalPhysicalAssignment` facts. These
are observed populations, not acceptance thresholds. Closure checks all native
allocation usages, including those outside these three end pairs and directed
workflow parameters; it does not claim 100 governed relation facts.

Both records also cite `de4sdv-release-evidence.json`, SHA-256
`8e3afd62950096ab0b81af495d2429f34e633878aace14ff07d132417bddb445`:
`git_revision` names the same execution revision and `passed` is `true`.
Its query-coverage check records both relation parity and allocation-end closure.
The release summary alone is not the proof.

## Validation boundary

The admission generator checks record shape, named revision fields and literal
successful result values. It does not authenticate an artifact, contact GitHub
or infer proof from a digest-shaped string. Review of the exact run and retained
bytes is the trust boundary. Tests pin the reviewed file hashes and can compare
every citation against retained bytes:

```bash
DE4SDV_RELEASE_EVIDENCE_DIR=/path/to/extracted/artifact \
  python -m pytest -q tests/test_kernel_vocabulary_projection.py
```

Normal tests still exercise the withholding guard with an open obligation.
The privileged workflow retains its executable parity and closure checks. A
failed parity exits nonzero; each later release needs its own valid evidence.
No earlier run is evidence that a later candidate passed.

The change adds no runtime textual parsing or name fallback. Kernel identity
still uses `KernelBindingIndex`. It changes no method or kernel definition and
makes no satisfaction, realization, deployment, validation-result, compliance
or certification claim.
