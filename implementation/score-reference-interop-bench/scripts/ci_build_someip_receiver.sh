#!/usr/bin/env bash
# Builds the DE4SDV minimal SOME/IP receiver (someip-receiver/, CMake, C++17)
# with one compiler and -Werror on a GitHub-hosted ubuntu-22.04 runner, runs
# the gtest suites of the pure core, and records the compiler, the test
# results, and the sha256, the dynamic libraries and the file type of the
# receiver. The g++ build is the binary of the namespace runs; the clang++
# build only shows that the sources build with the compiler family of AOSP.
# Usage: ci_build_someip_receiver.sh [--runner] <g++|clang++> <build-dir> <facts-dir> <bench-dir> <bin-dir>
set -euo pipefail
# Runner only: the ci_* scripts are written for a disposable CI runner and
# may change the host (packages, ~/.bazelrc, /usr/local, large build trees).
# Each one refuses to run elsewhere unless its first argument is --runner.
# The bench VM has its own path (README, section "Bench VM").
if [ "${1:-}" = "--runner" ]; then
  shift
elif [ "${GITHUB_ACTIONS:-}" != "true" ]; then
  echo "$(basename "$0"): runs only on a CI runner (GITHUB_ACTIONS=true) or with --runner as the first argument" >&2
  exit 2
fi

compiler=${1:?}
build=${2:?}
out=${3:?}
bench=${4:?}
bin=${5:?}
mkdir -p "$build" "$out" "$bin"

packages=(cmake ninja-build libgtest-dev)
if [ "$compiler" = "clang++" ]; then
  packages+=(clang)
fi
if [ -z "${DE4SDV_SKIP_APT:-}" ]; then  # set it for a local build with the tools on PATH
  sudo apt-get update -q
  sudo apt-get install -y -q "${packages[@]}"
fi
{
  dpkg-query -W "${packages[@]}" 2>/dev/null || true
  echo "$compiler: $("$compiler" --version | head -1)"
} | tee "$out/someip_receiver_toolchain_$compiler.txt"

start=$(date +%s)
set +e
cmake -S "$bench/someip-receiver" -B "$build" -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  "-DCMAKE_CXX_COMPILER=$compiler" > "$out/someip_receiver_configure_$compiler.log" 2>&1 &&
  ninja -C "$build" > "$out/someip_receiver_build_$compiler.log" 2>&1
build_status=$?
end=$(date +%s)
test_status=1
if [ "$build_status" -eq 0 ]; then
  "$build/de4sdv_someip_receiver_tests" "--gtest_output=xml:$out/someip_receiver_gtest_$compiler.xml" \
    > "$out/someip_receiver_gtest_$compiler.txt" 2>&1
  test_status=$?
fi
set -e
echo "{\"compiler\": \"$compiler\", \"build_wall_s\": $((end - start)), \"build_exit_code\": $build_status, \"test_exit_code\": $test_status}" |
  tee "$out/someip_receiver_build_$compiler.json"
if [ "$build_status" -ne 0 ]; then
  tail -60 "$out/someip_receiver_configure_$compiler.log" "$out/someip_receiver_build_$compiler.log" >&2 || true
fi
tail -3 "$out/someip_receiver_gtest_$compiler.txt" 2>/dev/null || true

if [ -x "$build/de4sdv_someip_receiver" ]; then
  cp "$build/de4sdv_someip_receiver" "$bin/"
  {
    sha256sum "$bin/de4sdv_someip_receiver"
    file "$bin/de4sdv_someip_receiver"
    ldd "$bin/de4sdv_someip_receiver"
  } | tee "$out/someip_receiver_binary_$compiler.txt"
fi

{
  echo "### SOME/IP receiver build and unit tests ($compiler)"
  echo '```'
  cat "$out/someip_receiver_build_$compiler.json"
  grep -h -E "^\[  (PASSED|FAILED)  \]|tests from .* ran" "$out/someip_receiver_gtest_$compiler.txt" 2>/dev/null || true
  head -1 "$out/someip_receiver_binary_$compiler.txt" 2>/dev/null || true
  echo '```'
} > "$out/someip_receiver_build_$compiler.md"
if [ "$build_status" -ne 0 ] || [ "$test_status" -ne 0 ]; then
  exit 1
fi
