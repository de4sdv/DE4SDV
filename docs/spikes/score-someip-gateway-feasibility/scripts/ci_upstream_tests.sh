#!/usr/bin/env bash
# DE4SDV throwaway spike (INC-MW-011 gateway feasibility), never merged.
# Runs the gateway's own tests on an untouched checkout, the way its CI does,
# and records per-target results. Never fails the job: the report states
# pass, fail or skip per target.
# Usage: ci_upstream_tests.sh <gateway-checkout> <facts-dir> unit|qemu
set -uo pipefail

gw=${1:?}
out=${2:?}
mode=${3:?}
spike_dir=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$out"
cd "$gw" || exit 1

bazel --version | tee "$out/bazel_version.txt"

run() {
  local name=$1
  shift
  local start end status
  start=$(date +%s)
  bazel "$@" 2>&1 | tee "$out/$name.log"
  status=${PIPESTATUS[0]}
  end=$(date +%s)
  echo "{\"name\": \"$name\", \"command\": \"bazel $*\", \"exit_code\": $status, \"wall_s\": $((end - start))}" \
    > "$out/$name.status.json"
  return 0
}

case "$mode" in
  unit)
    run build_all build //score/... //tests/...
    run quality_pack_suites test //:unit_tests //:component_tests --keep_going
    run score_and_tests test //score/... //tests/... --build_tests_only --keep_going
    ;;
  qemu)
    sudo chmod 666 /dev/kvm || true
    ls -l /dev/kvm > "$out/kvm.txt" 2>&1 || true
    run qemu_integration test --config=qemu-integration //quality/... //tests/integration_test/... --keep_going
    run tc8_conformance test --config=tc8-itf //tests/tc8_conformance/... --keep_going
    ;;
  *)
    echo "unknown mode $mode" >&2
    exit 1
    ;;
esac

# Keep every test.xml and test.log for the record.
logs=$(readlink -f bazel-testlogs || true)
if [ -n "$logs" ] && [ -d "$logs" ]; then
  (cd "$logs" && find . \( -name test.xml -o -name test.log \) -print0 | tar --null -czf "$out/testlogs.tar.gz" -T -)
fi
python3 "$spike_dir/scripts/summarize_tests.py" "$out" > "$out/tests_summary.md" || true
cat "$out/tests_summary.md" || true
exit 0
