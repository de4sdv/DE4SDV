#!/usr/bin/env bash
# Builds the DE4SDV minimal SOME/IP receiver (someip-receiver/, CMake, C++17)
# with one compiler and -Werror on a GitHub-hosted ubuntu-22.04 runner, runs
# the gtest suites of the pure core, and records the compiler, the test
# results, and the sha256, the dynamic libraries and the file type of the
# receiver. The g++ build is the binary of the namespace runs; the clang++
# build only shows that the sources build with the compiler family of AOSP.
# With a list of sanitizers (for example address,undefined), the gtest suites
# run under them and every finding fails the build.
# Usage: ci_build_someip_receiver.sh [--runner] <g++|clang++> <build-dir> <facts-dir> <bench-dir> <bin-dir> [<sanitizers>]
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
sanitizers=${6:-}
variant=$compiler
cmake_flags=()
if [ -n "$sanitizers" ]; then
  variant="$compiler-${sanitizers//,/-}"
  cmake_flags+=("-DCMAKE_CXX_FLAGS=-fsanitize=$sanitizers -fno-omit-frame-pointer -fno-sanitize-recover=all"
                "-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=$sanitizers")
  export ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1
fi
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
  echo "sanitizers: ${sanitizers:-none}"
} | tee "$out/someip_receiver_toolchain_$variant.txt"

start=$(date +%s)
set +e
cmake -S "$bench/someip-receiver" -B "$build" -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  "-DCMAKE_CXX_COMPILER=$compiler" "${cmake_flags[@]}" > "$out/someip_receiver_configure_$variant.log" 2>&1 &&
  ninja -C "$build" > "$out/someip_receiver_build_$variant.log" 2>&1
build_status=$?
end=$(date +%s)
test_status=1
if [ "$build_status" -eq 0 ]; then
  "$build/de4sdv_someip_receiver_tests" "--gtest_output=xml:$out/someip_receiver_gtest_$variant.xml" \
    > "$out/someip_receiver_gtest_$variant.txt" 2>&1
  test_status=$?
fi
set -e
echo "{\"compiler\": \"$compiler\", \"sanitizers\": \"${sanitizers:-none}\", \"build_wall_s\": $((end - start)), \"build_exit_code\": $build_status, \"test_exit_code\": $test_status}" |
  tee "$out/someip_receiver_build_$variant.json"
if [ "$build_status" -ne 0 ]; then
  tail -60 "$out/someip_receiver_configure_$variant.log" "$out/someip_receiver_build_$variant.log" >&2 || true
fi
tail -3 "$out/someip_receiver_gtest_$variant.txt" 2>/dev/null || true
if [ "$test_status" -ne 0 ]; then
  grep -h -E "runtime error|ERROR: (Address|Leak)Sanitizer|FAILED" "$out/someip_receiver_gtest_$variant.txt" | head -20 >&2 || true
fi

# The binary of a sanitizer build is not the binary of the namespace runs.
if [ -z "$sanitizers" ] && [ -x "$build/de4sdv_someip_receiver" ]; then
  cp "$build/de4sdv_someip_receiver" "$bin/"
  {
    sha256sum "$bin/de4sdv_someip_receiver"
    file "$bin/de4sdv_someip_receiver"
    ldd "$bin/de4sdv_someip_receiver"
  } | tee "$out/someip_receiver_binary_$variant.txt"
fi

{
  echo "### SOME/IP receiver build and unit tests ($variant)"
  echo '```'
  cat "$out/someip_receiver_build_$variant.json"
  grep -h -E "^\[  (PASSED|FAILED)  \]|tests from .* ran" "$out/someip_receiver_gtest_$variant.txt" 2>/dev/null || true
  head -1 "$out/someip_receiver_binary_$variant.txt" 2>/dev/null || true
  echo '```'
} > "$out/someip_receiver_build_$variant.md"
if [ "$build_status" -ne 0 ] || [ "$test_status" -ne 0 ]; then
  exit 1
fi
