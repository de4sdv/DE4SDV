# aebs-bench-framework

A shared evidence-pipeline framework for the AEBS bench increments. It replaces
the per-increment duplicated evidence builders, validators, finalizers, and
runners with **one parameterized implementation** driven by a *contract* — a
plain YAML file that describes the increment-specific schema, evaluator wiring,
and raw-observer field contract.

## Why

The existing bench produces five near-identical evidence builders
(`override_evidence.py`, `non_activation_evidence.py`,
`degraded_input_evidence.py`, `crossing_target_evidence.py`, and the 009B base),
five validators, four finalizers, and seven shell runners.  Each copy differs
only in a handful of string constants (schema id, increment id, profile enum,
evaluator module, success terminal).  This framework collapses them into one
implementation each so that future increments add **a contract YAML, not a new
code file**.

This package is **additive** — the existing per-increment files are untouched
and remain the authoritative implementation.  The framework provides the shared
infrastructure; per-increment files can be migrated to use it in a follow-up
step.

## Layout

```
aebs-bench-framework/
├── __init__.py            # package marker (empty)
├── evidence_pipeline.py   # build_evidence() — replay-based builder
├── evidence_validator.py  # validate_evidence() — independent replay validator
├── campaign_finalizer.py  # finalize_campaign() — retained campaign manifest
├── run_scenario.sh        # single-profile runtime runner
├── run_matrix.sh          # multi-profile serial runner + finalizer
└── README.md              # this file
```

## Contract

A contract is a YAML mapping.  Example for INC-AEBS-009D:

```yaml
schema_id: de4sdv.aebs-009d.override-evidence.v1
increment_id: INC-AEBS-009D
claim_boundary: one_profile_runtime_verdict_only_no_safety_or_compliance_claim
raw_contract_fields:
  - collector_id
  - monotonic_start_s
  - monotonic_end_s
  - clock_boundary
  - observations
  - evaluator_result
  - activation
  - errors
  - terminal_reason
  - command_exit
  - limits
  - override_profile
  - override_evaluator_result
profile_field: override_profile
profile_enum_module: de4sdv_aebs_009b_bench.override_matrix
profile_enum_name: OverrideScenario
profile_values:
  - fresh_false_control
  - fresh_true_conscious_override
  - stale
  - missing
  - malformed
  - future_stamped
success_terminal: pass_override_profile
additional_terminal_reasons:
  - terminal_override_failure
evaluator_module: de4sdv_aebs_009b_bench.override_matrix
evaluator_function: evaluate_profile
evaluator_result_key: override_evaluator_result
result_serializer: override_result_to_json
matrix_config: scenario-009d-conscious-override-matrix.yaml
scenario_config: scenario-009d-moving-vehicle-target.yaml   # optional; 009D inherits 009B
campaign_manifest_schema: de4sdv.aebs-009d.campaign-manifest.v1
campaign_shape: multi_profile        # or single_scenario
evidence_dir: evidence/009d
artifact_path_prefix_template: "{evidence_dir}/profiles/{profile}"
execution_manifest_function: execution_manifest_sha256_at_revision
profile_manifest_key: override_execution_manifest_sha256
config_sha256_key: override_matrix_sha256
metadata_fields: [observer_exit_code, raw_output, override_profile]
metadata_profile_field: override_profile
profile_key_field: profile
evidence_root_fields:
  - schema
  - increment_id
  - profile
  - scenario_id
  - provenance
  - collection
  - collector_contract
  - evaluation
  - artifacts
  - claim_boundary
```

### Contract keys

| Key | Description |
|---|---|
| `schema_id` | Evidence document schema identifier. |
| `increment_id` | Increment label (e.g. `INC-AEBS-009D`). |
| `claim_boundary` | Fixed claim-boundary string. |
| `raw_contract_fields` | Exact set of keys in the raw observer document. |
| `profile_field` | Key holding the profile value in raw + evidence. |
| `profile_enum_module` / `profile_enum_name` | Python import path to the profile Enum. |
| `profile_values` | Closed list of profile string values (for the matrix runner). |
| `success_terminal` | Terminal reason that marks a closed pass. |
| `additional_terminal_reasons` | Extra terminal reasons beyond the base 009B set. |
| `evaluator_module` | Python module with the evaluator + serializer. |
| `evaluator_function` | Function: `evaluate(matrix, profile, observations, *, window_end_receipt_s)`. |
| `result_serializer` | Function: `serialize(result) -> dict`. |
| `evaluator_result_key` | Key in raw holding the stored evaluator result. |
| `matrix_config` | Config YAML filename (under `config/`). |
| `scenario_config` | *(optional)* Inherited 009B scenario config for increments that replay 009B. |
| `raw_semantics_validator` | *(optional)* Standalone validator for non-009D increments. |
| `campaign_manifest_schema` | Schema id for the campaign manifest. |
| `campaign_shape` | `multi_profile` (009D/009E) or `single_scenario` (009F/009G/009H). |
| `evidence_dir` | Bench-relative evidence directory. |
| `artifact_path_prefix_template` | `"{evidence_dir}/profiles/{profile}"` for 009D/E; `"{evidence_dir}/{profile}"` for 009F. |
| `execution_manifest_function` | Name in `execution_identity` for the profile-bound manifest. |
| `profile_manifest_key` | Provenance key for the profile-bound manifest hash. |
| `config_sha256_key` | *(optional)* Provenance key for the matrix config hash. |
| `metadata_fields` | Exact set of keys in `run-metadata.json`. |
| `metadata_profile_field` | *(optional)* Key in metadata holding the profile value. |
| `evidence_root_fields` | Exact set of keys in the evidence root document. |

## Usage

### Python API

```python
import sys
sys.path.insert(0, "implementation/aebs-autoware-nominal-vehicle-target-bench/scripts")
sys.path.insert(0, "implementation/aebs-autoware-nominal-vehicle-target-bench/src/de4sdv_aebs_009b_bench")

from aebs_bench_framework.evidence_pipeline import build_evidence, load_contract, resolve_profile
from aebs_bench_framework.evidence_validator import validate_evidence
from aebs_bench_framework.campaign_finalizer import finalize_campaign

contract = load_contract("contracts/009d.yaml")
profile = resolve_profile(contract, "fresh_false_control")

document = build_evidence(raw, profile, provenance, artifacts,
                          contract=contract, bench_root="…")
validate_evidence(evidence_path, contract=contract, bench_root="…")
finalize_campaign(bench_root="…", contract=contract, profiles=[…])
```

### CLI

```bash
python3 evidence_pipeline.py \
  --contract contracts/009d.yaml --bench-root "$BENCH" \
  --raw raw.json --profile fresh_false_control \
  --provenance provenance.json --artifacts artifacts.json \
  --output scenario-evidence.json

python3 evidence_validator.py \
  scenario-evidence.json \
  --contract contracts/009d.yaml --bench-root "$BENCH"

python3 campaign_finalizer.py \
  --contract contracts/009d.yaml --bench-root "$BENCH"
```

### Shell runners

```bash
export BENCH_ROOT=…/aebs-autoware-nominal-vehicle-target-bench
export FRAMEWORK_DIR=…/aebs-bench-framework

# Single profile:
AEBS_INCREMENT=INC-AEBS-009D \
AEBS_PROFILE=fresh_false_control \
AEBS_CONTRACT="$FRAMEWORK_DIR/contracts/009d.yaml" \
AEBS_SCENARIO_CONFIG=/de4sdv/…/scenario-009d-moving-vehicle-target.yaml \
AEBS_EVIDENCE_DIR=evidence/009d \
AEBS_PROFILE_PREFIX=profiles \
AEBS_OBSERVER_PARAM=override_scenario \
AEBS_LAUNCH_ENV_PREFIX=DE4SDV_009D \
  "$FRAMEWORK_DIR/run_scenario.sh"

# Full matrix (profiles read from contract):
AEBS_SCENARIO_CONFIG=… AEBS_EVIDENCE_DIR=evidence/009d \
AEBS_OBSERVER_PARAM=override_scenario AEBS_LAUNCH_ENV_PREFIX=DE4SDV_009D \
  "$FRAMEWORK_DIR/run_matrix.sh" "$FRAMEWORK_DIR/contracts/009d.yaml"
```

## Design principles (preserved from per-increment files)

1. **Replay, never trust.**  The builder recomputes the evaluator result from
   raw observations; the stored verdict is never promoted.
2. **Closed contracts.**  Every document is checked for an *exact* key set —
   any extra or missing key is rejected.
3. **Hash-bound artifacts.**  The validator resolves every artifact by a
   non-symlink, regular-file path under the bench root and checks its SHA-256.
4. **Atomic publication.**  Evidence and manifests are written via temp-file +
   `os.replace` / hard-link so canonical files are never partially written.
5. **Additive.**  This framework does not modify or replace the existing
   per-increment files; they remain authoritative until migrated.
