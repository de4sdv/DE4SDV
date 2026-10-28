#!/usr/bin/env bash
# Builds and tests the ament_cmake package de4sdv_score_adapter with g++-12
# against ROS 2 Humble and the facade SDK of the gateway build, and records
# the link facts of the one-process adapter (REQ-MW-018, GAP-MW-035): one
# shared libstdc++ in the process, __cxa_allocate_exception defined in and
# exported by the executable, and the libstdc++ throw sites that bind to it.
# The control build without the abort override is built next to it.
# Usage: ci_build_colcon.sh [--runner] <workspace-dir> <facts-dir> <sdk-dir> <bench-dir> <bundle-dir>
set -eo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/runner_only.sh" || exit 2

ws=${1:?}
out=${2:?}
sdk=${3:?}
bench=${4:?}
bundle=${5:?}
mkdir -p "$ws/src" "$out" "$bundle"
# ROS setup scripts reference unset variables; nounset only after sourcing.
source /opt/ros/humble/setup.bash
set -u

rm -rf "$ws/src/de4sdv_score_adapter"
cp -r "$bench/adapter/de4sdv_score_adapter" "$ws/src/"
cd "$ws"
export CC=gcc-12 CXX=g++-12
{
  echo "CC=$CC $($CC --version | head -1)"
  echo "CXX=$CXX $($CXX --version | head -1)"
  echo "$CXX selects: $($CXX -print-file-name=libstdc++.so)"
} | tee "$out/colcon_compilers.txt"

start=$(date +%s)
set +e
colcon build --packages-select de4sdv_score_adapter --event-handlers console_direct+ \
  --cmake-args -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_VERBOSE_MAKEFILE=ON \
  "-DDE4SDV_SCORE_FACADE_DIR=$sdk" -DDE4SDV_BUILD_DISCRIMINATION_CONTROL=ON > "$out/colcon_build.log" 2>&1
build_status=$?
set -e
end=$(date +%s)
echo "{\"command\": \"colcon build de4sdv_score_adapter\", \"wall_s\": $((end - start)), \"exit_code\": $build_status}" |
  tee "$out/colcon_build_time.json"
grep -E "(-o|--output) [^ ]*de4sdv_score_adapter(_no_abort_control)? " "$out/colcon_build.log" |
  grep -E "whole-archive|libde4sdv_score_facade" > "$out/adapter_link_commands.txt" || true
if [ "$build_status" -ne 0 ]; then
  tail -80 "$out/colcon_build.log" >&2
  exit "$build_status"
fi

set +e
colcon test --packages-select de4sdv_score_adapter --event-handlers console_direct+ > "$out/colcon_test.log" 2>&1
colcon test-result --verbose > "$out/colcon_test_result.txt" 2>&1
test_status=$?
set -e
tail -5 "$out/colcon_test_result.txt"

prefix="$ws/install/de4sdv_score_adapter/lib/de4sdv_score_adapter"
adapter="$prefix/de4sdv_score_adapter"
control="$prefix/de4sdv_score_adapter_no_abort_control"
libstdcxx=$(ldd "$adapter" | awk '/libstdc\+\+/ {print $3}')
{
  echo "== nm -D --defined-only de4sdv_score_adapter | grep __cxa_allocate_exception"
  nm -D --defined-only "$adapter" | grep -E "__cxa_allocate_exception" || echo "NOT EXPORTED"
  echo "== nm -D --defined-only de4sdv_score_adapter_no_abort_control | grep __cxa_allocate_exception"
  nm -D --defined-only "$control" | grep -E "__cxa_allocate_exception" || echo "not exported (control, expected)"
  echo "== readelf --dyn-syms de4sdv_score_adapter (allocation symbol)"
  readelf -W --dyn-syms "$adapter" | grep -E "__cxa_allocate_exception" || true
  echo "== libstdc++ in the process (ldd)"
  ldd "$adapter" | grep -E "libstdc\+\+|libgcc_s|librclcpp|libc\.so" || true
  echo "== copies of libstdc++ code defined in the executable (expected none)"
  nm --defined-only "$adapter" | grep -E " [TW] (__cxa_throw|__cxa_free_exception|__cxa_begin_catch)$" || echo "none"
  echo "== shared libstdc++: $libstdcxx"
  readelf -d "$libstdcxx" | grep -E "SYMBOLIC|FLAGS" || echo "no DT_SYMBOLIC and no DT_FLAGS"
  echo "calls to __cxa_allocate_exception@plt inside it: $(objdump -d "$libstdcxx" | grep -c 'call.*<__cxa_allocate_exception@plt>' || true)"
  echo "== sha256"
  sha256sum "$adapter" "$control" "$libstdcxx"
} | tee "$out/adapter_link_facts.txt"

# The runtime jobs source /opt/ros/humble from the same snapshot and run the
# executables by path; the install tree itself is not needed there.
mkdir -p "$bundle/bin"
cp "$adapter" "$control" "$bundle/bin/"
exit "$test_status"
