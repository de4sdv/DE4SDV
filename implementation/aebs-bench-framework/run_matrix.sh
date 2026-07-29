#!/usr/bin/env bash
# Shared matrix runner: execute a list of closed profiles as isolated serial
# runtime runs, then finalize the retained campaign.
#
# Usage: run_matrix.sh CONTRACT_YAML [PROFILE ...]
#
# If no PROFILE arguments are given the closed profile set is read from the
# contract YAML (profile_values key).
#
# Required environment variables (same as run_scenario.sh):
#   BENCH_ROOT, FRAMEWORK_DIR, AEBS_SCENARIO_CONFIG (or derived from contract),
#   AEBS_EVIDENCE_DIR, AEBS_OBSERVER_PARAM, AEBS_LAUNCH_ENV_PREFIX
#
set -euo pipefail

: "${BENCH_ROOT:?BENCH_ROOT is required}"
: "${FRAMEWORK_DIR:?FRAMEWORK_DIR is required}"

CONTRACT="${1:?Usage: run_matrix.sh CONTRACT_YAML [PROFILE ...]}"
shift

BENCH="$BENCH_ROOT"

# Resolve the increment and profiles from the contract.
INC="$(python3 -c 'import sys,yaml; print(yaml.safe_load(open(sys.argv[1],encoding="utf-8"))["increment_id"])' "$CONTRACT")"

if [ "$#" -gt 0 ]; then
  profiles=("$@")
else
  # Read closed profile set from the contract YAML.
  mapfile -t profiles < <(python3 -c '
import sys,yaml,json
contract=yaml.safe_load(open(sys.argv[1],encoding="utf-8"))
for value in contract.get("profile_values",[]):
    print(value)
' "$CONTRACT")
fi

if [ "${#profiles[@]}" -eq 0 ]; then
  printf 'No profiles resolved for %s from %s\n' "$INC" "$CONTRACT" >&2
  exit 2
fi

for profile in "${profiles[@]}"; do
  printf 'Executing isolated %s profile: %s\n' "$INC" "$profile"
  AEBS_INCREMENT="$INC" \
  AEBS_PROFILE="$profile" \
  AEBS_CONTRACT="$CONTRACT" \
    "$FRAMEWORK_DIR/run_scenario.sh"
done

# Finalize the campaign.
PYTHONPATH="$FRAMEWORK_DIR:$BENCH/scripts${PYTHONPATH:+:$PYTHONPATH}" python3 "$FRAMEWORK_DIR/campaign_finalizer.py" \
  --contract "$CONTRACT" --bench-root "$BENCH"
printf 'All %s profiles produced separate replay-validated canonical records.\n' "$INC"
