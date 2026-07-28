#!/usr/bin/env bash
# Execute each closed INC-AEBS-009E profile as an isolated serial runtime run.
set -euo pipefail

BENCH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
profiles=(
  clear_path
  adjacent_object
  non_closing_target
  below_trigger
)

for profile in "${profiles[@]}"; do
  printf 'Executing isolated 009E profile: %s\n' "$profile"
  "$BENCH/scripts/run_non_activation_profile.sh" "$profile"
done

python3 "$BENCH/scripts/finalize_non_activation_campaign.py" --bench-root "$BENCH"
printf 'All four 009E profiles produced separate replay-validated canonical records.\n'
