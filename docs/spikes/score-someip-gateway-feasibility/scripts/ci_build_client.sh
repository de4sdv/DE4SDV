#!/usr/bin/env bash
# DE4SDV throwaway spike (INC-MW-011 gateway feasibility), never merged.
# Builds COVESA vsomeip 3.7.6 (commit 4187431d, unchanged) against the
# runner's Boost and the spike's guest-side client against it. Adds the
# guest entries to paths.json.
# Usage: ci_build_client.sh <work-dir> <facts-dir> <paths.json>
set -euo pipefail

work=${1:?}
out=${2:?}
paths_json=${3:?}
spike_dir=$(cd "$(dirname "$0")/.." && pwd)
: "${VSOMEIP_SHA:?}"
mkdir -p "$work" "$out"
src="$work/vsomeip"
prefix="$work/vsomeip-3.7.6"

logged() {
  local log=$1
  shift
  if ! "$@" > "$log" 2>&1; then
    echo "FAILED: $* (last lines of $log)" >&2
    tail -60 "$log" >&2
    return 1
  fi
}

start=$(date +%s)
git init -q "$src"
git -C "$src" remote add origin https://github.com/COVESA/vsomeip.git
git -C "$src" fetch -q --depth 1 origin "$VSOMEIP_SHA"
git -C "$src" checkout -q --detach FETCH_HEAD
test "$(git -C "$src" rev-parse HEAD)" = "$VSOMEIP_SHA"
version=$(grep -E 'set \(VSOMEIP_(MAJOR|MINOR|PATCH)_VERSION' "$src/CMakeLists.txt" | grep -oE '[0-9]+' | paste -sd.)
echo "vsomeip $VSOMEIP_SHA tree $(git -C "$src" rev-parse 'HEAD^{tree}') CMake version $version" | tee "$out/vsomeip_guest_identity.txt"
test "$version" = "3.7.6"

logged "$out/vsomeip_cmake.log" cmake -S "$src" -B "$work/vsomeip-build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$prefix"
logged "$out/vsomeip_build.log" cmake --build "$work/vsomeip-build" -j "$(nproc)"
logged "$out/vsomeip_install.log" cmake --install "$work/vsomeip-build"
grep -i "boost version" "$out/vsomeip_cmake.log" | tee -a "$out/vsomeip_guest_identity.txt" || true

logged "$out/client_cmake.log" cmake -S "$spike_dir/client" -B "$work/client-build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="$prefix"
logged "$out/client_build.log" cmake --build "$work/client-build"
end=$(date +%s)

client="$work/client-build/frame_client"
libdir="$prefix/lib"
python3 - "$paths_json" "$client" "$libdir" "$out/guest_build.json" "$start" "$end" <<'EOF'
import glob, json, os, sys
paths_json, client, libdir, facts, start, end = sys.argv[1:]
paths = json.load(open(paths_json)) if os.path.exists(paths_json) else {}
paths["client"] = client
paths["guest_ld_library_path"] = libdir
json.dump(paths, open(paths_json, "w"), indent=2)
sizes = {os.path.basename(p): os.path.getsize(os.path.realpath(p))
         for p in [client] + sorted(glob.glob(os.path.join(libdir, "libvsomeip3*.so.3.7.6")))}
json.dump({"wall_s": int(end) - int(start), "sizes_bytes": sizes}, open(facts, "w"), indent=2)
print(json.dumps(paths, indent=2))
EOF
LD_LIBRARY_PATH="$libdir" ldd "$client" > "$out/ldd_guest.txt" 2>&1 || true
