#!/usr/bin/env bash
# Execute each closed INC-AEBS-009D profile as an isolated serial runtime run.
set -euo pipefail

BENCH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
profiles=(
  fresh_false_control
  fresh_true_conscious_override
  stale
  missing
  malformed
  future_stamped
)

for profile in "${profiles[@]}"; do
  printf 'Executing isolated 009D profile: %s\n' "$profile"
  "$BENCH/scripts/run_override_profile.sh" "$profile"
done

printf 'All six 009D profiles produced separate replay-validated canonical records.\n'
