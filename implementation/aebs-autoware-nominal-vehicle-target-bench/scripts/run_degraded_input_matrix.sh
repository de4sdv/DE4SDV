#!/usr/bin/env bash
# Run all five INC-AEBS-009F degraded-input matrix profiles in sequence.
# Each profile requires a separate pinned-runtime execution and verdict.
# Usage: run_degraded_input_matrix.sh
set -euo pipefail

BENCH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILES=(
  stale_input
  missing_input
  malformed_input
  inconsistent_input
  unavailable_input
)

for profile in "${PROFILES[@]}"; do
  printf '=== Running 009F profile: %s ===\n' "$profile"
  "$BENCH/scripts/run_degraded_input_profile.sh" "$profile"
done

for profile in "${PROFILES[@]}"; do
  printf '=== Finalizing 009F profile: %s ===\n' "$profile"
  python3 "$BENCH/scripts/finalize_degraded_input_campaign.py" \
    --profile "$profile" --bench-root "$BENCH"
done

printf 'All five 009F degraded-input profiles finalized and replay-validated.\n'
