#!/usr/bin/env bash
# Builds the core and the shell of the DE4SDV IVI frame relay
# (ivi-frame-relay/, CMake, C++17) with one compiler and -Werror on a
# GitHub-hosted ubuntu-22.04 runner, runs their gtest suites with the fake
# gateway client, and records the compiler and the test results. CI has no
# AOSP tree, so it does not build the AOSP adapter to libsdvgatewayclient or
# the main of the relay (src/aosp/); the VM session of phase 10 builds them
# with Android.bp. The clang++ build shows that the sources build with the
# compiler family of AOSP. With a list of sanitizers (address,undefined or
# thread), the gtest suites run under them and every finding fails the build.
# Usage: ci_build_ivi_frame_relay.sh [--runner] <g++|clang++> <build-dir> <facts-dir> <bench-dir> [<sanitizers>]
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]:?}")/runner_only.sh" || exit 2

compiler=${1:?}
build=${2:?}
out=${3:?}
bench=${4:?}
sanitizers=${5:-}
variant=$compiler
cmake_flags=()
if [ -n "$sanitizers" ]; then
  variant="$compiler-${sanitizers//,/-}"
  cmake_flags+=("-DCMAKE_CXX_FLAGS=-fsanitize=$sanitizers -fno-omit-frame-pointer -fno-sanitize-recover=all"
                "-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=$sanitizers")
  export ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1
  export TSAN_OPTIONS=halt_on_error=1:second_deadlock_stack=1
fi
mkdir -p "$build" "$out"

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
  echo "sanitizers: ${sanitizers:-none}"
} | tee "$out/ivi_frame_relay_toolchain_$variant.txt"

start=$(date +%s)
set +e
cmake -S "$bench/ivi-frame-relay" -B "$build" -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  "-DCMAKE_CXX_COMPILER=$compiler" "${cmake_flags[@]}" > "$out/ivi_frame_relay_configure_$variant.log" 2>&1 &&
  ninja -C "$build" > "$out/ivi_frame_relay_build_$variant.log" 2>&1
build_status=$?
end=$(date +%s)
test_status=1
if [ "$build_status" -eq 0 ]; then
  "$build/de4sdv_ivi_frame_relay_tests" "--gtest_output=xml:$out/ivi_frame_relay_gtest_$variant.xml" \
    > "$out/ivi_frame_relay_gtest_$variant.txt" 2>&1
  test_status=$?
fi
set -e
echo "{\"compiler\": \"$compiler\", \"sanitizers\": \"${sanitizers:-none}\", \"build_wall_s\": $((end - start)), \"build_exit_code\": $build_status, \"test_exit_code\": $test_status}" |
  tee "$out/ivi_frame_relay_build_$variant.json"
if [ "$build_status" -ne 0 ]; then
  tail -60 "$out/ivi_frame_relay_configure_$variant.log" "$out/ivi_frame_relay_build_$variant.log" >&2 || true
fi
tail -3 "$out/ivi_frame_relay_gtest_$variant.txt" 2>/dev/null || true
if [ "$test_status" -ne 0 ]; then
  grep -h -E "runtime error|ERROR: (Address|Leak)Sanitizer|WARNING: ThreadSanitizer|FAILED" \
    "$out/ivi_frame_relay_gtest_$variant.txt" | head -20 >&2 || true
fi

{
  echo "### IVI frame relay build and unit tests ($variant)"
  echo '```'
  cat "$out/ivi_frame_relay_build_$variant.json"
  grep -h -E "^\[  (PASSED|FAILED)  \]|tests from .* ran" "$out/ivi_frame_relay_gtest_$variant.txt" 2>/dev/null || true
  echo '```'
} > "$out/ivi_frame_relay_build_$variant.md"
if [ "$build_status" -ne 0 ] || [ "$test_status" -ne 0 ]; then
  exit 1
fi
