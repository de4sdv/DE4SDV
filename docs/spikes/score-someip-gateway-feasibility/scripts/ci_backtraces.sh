#!/usr/bin/env bash
# DE4SDV throwaway spike (INC-MW-011 gateway feasibility), never merged.
# Writes a gdb backtrace of every core dump the diagnostic scenarios produced
# (kernel.core_pattern = <cores>/core.%e.%p) next to the scenario results, so
# the raw cores need not be uploaded.
# Usage: ci_backtraces.sh <cores-dir> <paths.json> <results-dir>
set -uo pipefail

cores=${1:?}
paths_json=${2:?}
results=${3:?}
mkdir -p "$results/backtraces"
shopt -s nullglob
for core in "$cores"/core.*; do
  name=$(basename "$core")
  exe_name=$(echo "$name" | cut -d. -f2)
  exe=$(python3 -c "
import json, sys
paths = json.load(open('$paths_json'))
mapping = {'gatewayd': 'gatewayd', 'someipd': 'someipd', 'frame_publisher': 'publisher', 'frame_client': 'client'}
print(paths.get(mapping.get('$exe_name', ''), ''))")
  if [ -z "$exe" ]; then
    echo "no executable for $name" > "$results/backtraces/$name.bt.txt"
    continue
  fi
  sudo gdb -batch -nx -ex "set pagination off" -ex "info threads" -ex "thread apply all bt" \
    "$exe" "$core" > "$results/backtraces/$name.bt.txt" 2>&1 || true
  ls -l "$core" >> "$results/backtraces/$name.bt.txt"
done
ls -l "$results/backtraces"
