# Contract data

The runtime builds the kernel contract from the files in this directory
(`build_model_contract` in `de4sdv/semantic/model_contract.py`). The paths of
the projections, profiles and frozen records are part of the
semantic-authority identity (`sai-…`), so moving or renaming one of them
changes the identity.

Never edit a generated file by hand. Change its source and run its generator,
as described in
[generated-semantic-assets.md](../../../docs/guides/generated-semantic-assets.md).

| File | Content | Changed by |
|---|---|---|
| `class-definition-projection.json`, `class-definition-profile.json` | Kernel class definitions and their API representation | `scripts/generate_definition_projection.py` |
| `kernel-vocabulary-projection.json`, `kernel-vocabulary-profile.json` | The other kernel classes and relationships, the successor predicates and the retired names | `scripts/generate_definition_projection.py` |
| `native-grounding-projection.json`, `native-grounding-profile.json` | Identities grounded in native or standard-library SysML v2 constructs | `scripts/generate_semantic_projection_o2p.py` |
| `increment-relationship-projection.json`, `increment-relationship-profile.json` | The increment relationship carriers | `scripts/generate_vocabulary_carriers.py` |
| `*-admission.yaml` | The reviewed admission manifest of each generated pair | a reviewed edit, then the generator |
| `frozen-records/`, `frozen-records.json` | Six historical records that still serve 13 identities, and the manifest that freezes them ([frozen-records.md](frozen-records.md)) | never |
| `ontology-identity-register.json` | One row per ontology identity with its disposition; the runtime refuses merged and removed identities with it | a reviewed edit |
| `kernel-internal-declarations.yaml` | Kernel declarations that are deliberately not projected, each with a reason | a reviewed edit |
| `external-reference-profile.yaml` | Typed references for the evidence identities whose content stays in external systems. Its reviewed payload still names the paths it was accepted with; the [acceptance record](../../../docs/method-conformance/o4/external-reference-acceptance-review.md) pins it by digest | a reviewed edit that updates both digest records |
| `ontology-review.json` | The integrated ontology review; the increment relationship generator and the external-reference check read its reviewed definitions | a new review |
| `model-authority-coverage-baseline.yaml` | Coverage ratchet for provider routing, refusals and retirements | `scripts/check_model_projection_coverage.py --write-baseline` |
| `pilot-obligations.yaml` | Obligation table of the declared method evaluation pilot ([pilot-scope.md](../../../docs/method-evaluation/pilot-scope.md)) | a reviewed edit |
