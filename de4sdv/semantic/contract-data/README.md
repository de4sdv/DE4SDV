# Contract data

The runtime builds the kernel contract from the files in this directory
(`build_model_contract` in `de4sdv/semantic/model_contract.py`) and reads no
SysML text. The paths of the projections, profiles and frozen records are part
of the semantic-authority identity (`sai-…`), so moving or renaming one of them
changes the identity; the trace-vocabulary contract enters the identity through
its content.

Never edit a generated file by hand. Change its source and run its generator,
as described in
[generated-semantic-assets.md](../../../docs/guides/generated-semantic-assets.md).

| File | Content | Changed by |
|---|---|---|
| `class-definition-projection.json`, `class-definition-profile.json` | Kernel class definitions and their API representation | `scripts/generate_definition_projection.py` |
| `kernel-vocabulary-projection.json`, `kernel-vocabulary-profile.json` | The other kernel classes and relationships, the successor predicates and the retired names | `scripts/generate_definition_projection.py` |
| `native-grounding-projection.json`, `native-grounding-profile.json` | Identities grounded in native or standard-library SysML v2 constructs | `scripts/generate_native_grounding_projection.py` |
| `increment-relationship-projection.json`, `increment-relationship-profile.json` | The increment relationship carriers | `scripts/generate_vocabulary_carriers.py` |
| `trace-vocabulary-contract.json` | The trace relations (`allocatedTo`, `hasValidationScenario`, `hasRegulatorySource`) and the retired relation names, read from the trace-vocabulary package of the method kernel. The runtime reads this file and never parses the model | `scripts/generate_trace_vocabulary_contract.py` |
| `*-admission.yaml` | The reviewed admission manifest of each generated pair | a reviewed edit, then the generator |
| `frozen-records/`, `frozen-records.json` | Six historical records that still serve 13 identities, and the manifest that freezes them ([frozen-records.md](frozen-records.md)) | never |
| `ontology-identity-register.json` | One row per ontology identity with its disposition; the runtime refuses merged and removed identities with it | a reviewed edit |
| `kernel-internal-declarations.yaml` | Kernel declarations that are deliberately not projected, each with a reason | a reviewed edit |
| `external-reference-profile.yaml` | Typed references for the evidence identities whose content stays in external systems. Its reviewed payload still names the paths it was accepted with; the [acceptance record](../../../docs/method-conformance/o4/external-reference-acceptance-review.md) pins it by digest | a reviewed edit that updates both digest records |
| `ontology-review.json` | The integrated ontology review; the increment relationship generator and the external-reference check read its reviewed definitions | a new review |
| `model-authority-coverage-baseline.yaml` | Coverage ratchet for provider routing, refusals and retirements | `scripts/check_model_projection_coverage.py --write-baseline` |
| `pilot-obligations.yaml` | Obligation table of the declared method evaluation pilot ([pilot-scope.md](../../../docs/method-evaluation/pilot-scope.md)) | a reviewed edit |

## Citing archived records

Some decision records that `kernel-vocabulary-admission.yaml` cites in its
`resolved_by` fields were archived at the `release-2026-10-11` tag and are no
longer in the tree. The manifest cites them in git's revision-and-path form:

```text
release-2026-10-11:docs/method-conformance/o4/approved-semantic-decisions.yaml#topic1
```

The part before the colon is the tag, the part after it is the file's path at
that tag, and the fragment names the entry inside the file;
`git show release-2026-10-11:<path>` prints the record. A record that is still
in the tree is cited by its path alone. The generator's format check accepts an
optional `release-YYYY-MM-DD:` prefix; `tests/test_kernel_vocabulary_projection.py`
pins the tag to `release-2026-10-11` and resolves every citation: the file
must exist at the tag (`git cat-file -e`), and a fragment that is a real key
(a topic key, an identity row) must exist in it.

Human-facing documents link the same records with GitHub URLs at the tag,
`https://github.com/de4sdv/DE4SDV/blob/release-2026-10-11/<path>`.
