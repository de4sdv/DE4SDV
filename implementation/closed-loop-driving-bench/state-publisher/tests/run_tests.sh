#!/usr/bin/env bash
# DE4SDV INC-DRIVING-001 slice 10b, S1: build and run the publisher's tests on a
# machine without S-CORE, Bazel or CMake (g++ 11, python3 stdlib only).
#
#   tests/run_tests.sh
#
# 1. builds and runs the C++ unit tests (plain g++, no framework);
# 2. builds the vector dumper, writes tests/vectors/*.bin + expect.jsonl;
# 3. decodes every vector with tests/decode_vectors.py, a decoder written from
#    the ICD v2 section 3 table (not from publisher_core.cpp), and writes
#    tests/vectors/expected.json for cross-checking another decoder;
# 4. syntax-checks the S-CORE shell against a local mock of the mw::com surface.
#    That check only proves the shell parses and type-checks against the
#    signatures I assumed; it is not a build of the real thing.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(dirname "$here")"
include_dir="$root/../interfaces/include"
build="$root/.build"
cxx="${CXX:-g++}"
python="${PYTHON:-python3}"
flags=(-std=c++17 -Wall -Wextra -Werror -O2 -I"$include_dir" -I"$root")

mkdir -p "$build"

echo "== unit tests =="
set -x
"$cxx" "${flags[@]}" "$root/publisher_core.cpp" "$here/test_publisher_core.cpp" \
    -o "$build/test_publisher_core"
"$build/test_publisher_core"
set +x

echo "== test vectors =="
set -x
"$cxx" "${flags[@]}" "$root/publisher_core.cpp" "$here/dump_vectors.cpp" \
    -o "$build/dump_vectors"
rm -rf "$here/vectors"
mkdir -p "$here/vectors"
"$build/dump_vectors" "$here/vectors"
set +x

echo "== independent decoder written from the ICD v2 section 3 table =="
set -x
"$python" "$here/decode_vectors.py" "$here/vectors"
set +x

echo "== shell syntax check against the local mw::com mock (NOT S-CORE) =="
set -x
"$cxx" -std=c++17 -Wall -Wextra -Werror -fsyntax-only -isystem "$here/mock" \
    -I"$include_dir" -I"$root" "$root/state_publisher_main.cpp"
set +x

echo "all tests passed"
