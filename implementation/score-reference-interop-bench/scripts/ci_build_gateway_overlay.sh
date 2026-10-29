#!/usr/bin/env bash
# Builds, in the throwaway checkout of the S-CORE SOME/IP gateway with the
# DE4SDV overlay package //de4sdv_score_bench, with the gateway's own
# toolchain (Bazel from .bazelversion via bazelisk, LLVM, communication 0.5.0,
# baselibs from MODULE.bazel), optimised:
#   - the facade archive and the abort-override archive of the adapter
#     (cc_static_library) with their linkopts and linkdeps;
#   - the vehicle-speed provider;
#   - gatewayd, someipd, the null serializer and the gateway configuration
#     binary, for the soak.
# It runs the schema tests of the overlay's mw::com configuration, stages the
# facade SDK for the ament_cmake link (<sdk>) and the S-CORE runtime files for
# the bench (<bundle>), and records the build facts.
# Usage: ci_build_gateway_overlay.sh [--runner] <gateway-checkout> <facts-dir> <sdk-dir> <bundle-dir> <bench-dir>
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]:?}")/runner_only.sh" || exit 2

gw=${1:?}
out=${2:?}
sdk=${3:?}
bundle=${4:?}
bench=${5:?}
mkdir -p "$out" "$sdk/include/de4sdv_score_facade" "$sdk/lib" "$bundle/bin" "$bundle/lib" "$bundle/config"
cd "$gw"

bazel --version | tee "$out/bazel_version.txt"

facade=//de4sdv_score_bench/facade:de4sdv_score_facade
abort=//de4sdv_score_bench/facade:de4sdv_aborts_upon_exception
targets=("$facade" "$abort"
         //de4sdv_score_bench/provider:vehicle_speed_provider
         //de4sdv_score_bench/config:someip_gateway_config
         //score/gatewayd //score/someipd //score/serializer:null_serializer)

start=$(date +%s)
set +e
bazel build -c opt --keep_going --output_groups=+linkopts,+linkdeps "${targets[@]}" 2>&1 | tee "$out/bazel_build.log"
build_status=${PIPESTATUS[0]}
set -e
end=$(date +%s)
python3 - "$out/build_time.json" "$start" "$end" "$build_status" "${BAZEL_CACHE_RESTORED:-unknown}" <<'PY'
import json, sys
path, start, end, status, cache = sys.argv[1:]
json.dump({"command": "bazel build -c opt (facade archives, provider, gateway daemons, serializer, gateway config)",
           "wall_s": int(end) - int(start), "exit_code": int(status), "bazel_cache_restored": cache},
          open(path, "w"), indent=2)
PY
cat "$out/build_time.json"
bazel mod explain score_communication score_baselibs > "$out/bazel_mod_explain.txt" 2>&1 || true
git status --porcelain --untracked-files=all > "$out/gateway_status_after_build.txt"
if [ "$build_status" -ne 0 ]; then
  echo "bazel build failed with $build_status" >&2
  exit "$build_status"
fi

set +e
bazel test -c opt //de4sdv_score_bench/config:all 2>&1 | tee "$out/bazel_test_overlay_config.log"
test_status=${PIPESTATUS[0]}
set -e

bin=$(bazel info -c opt bazel-bin)
output_base=$(bazel info output_base)

# The C++ toolchain and the libstdc++ headers it selected.
clang=$(find -L "$output_base/external" -maxdepth 3 -path '*llvm_toolchain_llvm*/bin/clang' -type f 2>/dev/null | head -1)
{
  echo "== clang of the gateway toolchain: $clang"
  if [ -n "$clang" ]; then "$clang" -v -x c++ -E /dev/null -o /dev/null 2>&1 | grep -E "clang version|Selected GCC installation|Target:"; fi
  echo "== the facade compile command"
  bazel aquery -c opt "mnemonic('CppCompile', //de4sdv_score_bench/facade:score_facade)" --output=text 2>/dev/null |
    grep -E "^  Command Line" -A 200 | tr -s ' ' | head -60
} > "$out/toolchain.txt" 2>&1 || true

facade_archive="$bin/de4sdv_score_bench/facade/libde4sdv_score_facade.a"
abort_archive="$bin/de4sdv_score_bench/facade/libde4sdv_aborts_upon_exception.a"
linkopts_file="$bin/de4sdv_score_bench/facade/de4sdv_score_facade_linkopts.txt"
linkdeps_file="$bin/de4sdv_score_bench/facade/de4sdv_score_facade_linkdeps.txt"
for file in "$facade_archive" "$abort_archive" "$linkopts_file" "$linkdeps_file"; do
  test -f "$file" || { echo "missing $file" >&2; find "$bin/de4sdv_score_bench/facade" -maxdepth 1 >&2; exit 1; }
done
cp "$facade_archive" "$abort_archive" "$sdk/lib/"
cp "$bench/adapter/facade/include/de4sdv_score_facade/score_facade.h" "$sdk/include/de4sdv_score_facade/"
cp "$linkopts_file" "$linkdeps_file" "$out/"

# Further link inputs, in order: the static libraries that the facade needs
# but does not hold (linkdeps), then the user linkopts of its dependencies.
: > "$sdk/link_inputs.txt"
while IFS= read -r label; do
  [ -n "$label" ] || continue
  case "$label" in
    *acl-deb*)
      acl=$(find -L "$output_base/external" -path '*acl-deb*' -name 'libacl.a' -type f | head -1)
      test -n "$acl" || { echo "libacl.a of $label not found" >&2; exit 1; }
      cp "$acl" "$sdk/lib/libacl.a"
      echo "$sdk/lib/libacl.a" >> "$sdk/link_inputs.txt"
      ;;
    *)
      echo "unhandled linkdeps entry of the facade: $label" >&2
      exit 1
      ;;
  esac
done < "$linkdeps_file"
python3 - "$linkopts_file" >> "$sdk/link_inputs.txt" <<'PY'
import shlex, sys
seen = []
for line in open(sys.argv[1]):
    for item in shlex.split(line):
        if item not in seen:
            seen.append(item)
print("\n".join(seen))
PY
sed -i '/^$/d' "$sdk/link_inputs.txt"

{
  echo "== link inputs after the facade archive"
  cat "$sdk/link_inputs.txt"
  echo "== archive members"
  echo "facade: $(ar t "$sdk/lib/libde4sdv_score_facade.a" | wc -l) objects, $(stat -c %s "$sdk/lib/libde4sdv_score_facade.a") bytes"
  echo "abort override: $(ar t "$sdk/lib/libde4sdv_aborts_upon_exception.a" | tr '\n' ' ')"
  echo "== __cxa_allocate_exception in the archives (T = defined, U = referenced)"
  nm -A "$sdk/lib/libde4sdv_aborts_upon_exception.a" 2>/dev/null | grep -E "__cxa_allocate_exception" || true
  nm -A "$sdk/lib/libde4sdv_score_facade.a" 2>/dev/null | grep -E " [TW] __cxa_allocate_exception" || echo "facade archive defines no __cxa_allocate_exception"
  echo "== libstdc++ definitions in the facade archive (expected none)"
  nm -A --defined-only "$sdk/lib/libde4sdv_score_facade.a" 2>/dev/null |
    grep -E " [TW] (__cxa_throw|__cxa_free_exception|_ZSt20__throw_length_errorPKc|_Znwm)$" || echo "none"
} | tee "$out/facade_sdk.txt"

# The S-CORE runtime files of the bench.
cp "$bin/de4sdv_score_bench/provider/vehicle_speed_provider" "$bundle/bin/"
cp "$bin/score/gatewayd/gatewayd" "$bin/score/someipd/someipd" "$bundle/bin/"
serializer=$(find -L "$bin/score/serializer" -maxdepth 1 -name 'score_com_serializer.so' | head -1)
cp "$serializer" "$bundle/lib/"
vsomeip_lib=""
for candidate in $(find -L "$bin" -name 'libvsomeip3.so.3' -not -path '*.runfiles*' 2>/dev/null); do
  if [ -e "$(dirname "$candidate")/libvsomeip3-sd.so.3" ] && [ -e "$(dirname "$candidate")/libvsomeip3-cfg.so.3" ]; then
    vsomeip_lib=$candidate
    break
  fi
done
test -n "$vsomeip_lib" || { echo "no vsomeip library directory" >&2; exit 1; }
cp -L "$(dirname "$vsomeip_lib")"/libvsomeip3*.so* "$bundle/lib/"
cp "$bin/de4sdv_score_bench/config/someip_gateway_config.bin" "$bundle/config/"
cp "$bench"/config/*.json "$bundle/config/"
# The one ROS 2 environment of every host ROS 2 process, for the runtime jobs
# now and for the Launch Manager wrappers later.
cp "$bench/config/ros_environment.sh" "$bench/config/cyclonedds.xml" "$bundle/config/"
chmod -R u+w "$bundle"
(cd "$bundle" && find . -type f -print0 | sort -z | xargs -0 sha256sum) > "$out/bundle_score_sha256.txt"
(cd "$sdk" && find . -type f -print0 | sort -z | xargs -0 sha256sum) > "$out/facade_sdk_sha256.txt"
for binary in "$bundle/bin/gatewayd" "$bundle/bin/someipd" "$bundle/bin/vehicle_speed_provider"; do
  echo "== ldd $(basename "$binary")"
  LD_LIBRARY_PATH="$bundle/lib" ldd "$binary" || true
done > "$out/ldd_score.txt" 2>&1
exit "$test_status"
