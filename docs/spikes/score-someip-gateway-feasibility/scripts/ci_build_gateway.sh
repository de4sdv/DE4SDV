#!/usr/bin/env bash
# DE4SDV throwaway spike (INC-MW-011 gateway feasibility), never merged.
# Builds gatewayd, someipd, the null serializer, the spike publisher, the
# gateway configuration binary and the gateway's own deployment tar with the
# toolchain the repository registers (Bazel from .bazelversion via bazelisk),
# optimised. Records build time, the resolved S-CORE module versions, the
# lockfile state, binary and package sizes, the runtime library closure, and
# writes paths.json for xdomain.py.
# Usage: ci_build_gateway.sh <gateway-checkout> <facts-dir> <paths.json>
set -euo pipefail

gw=${1:?}
out=${2:?}
paths_json=${3:?}
spike_dir=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$out"
cd "$gw"

bazel --version | tee "$out/bazel_version.txt"
bazelisk version 2>/dev/null | tee -a "$out/bazel_version.txt" || true

targets=(//score/gatewayd //score/someipd //score/serializer:null_serializer
         //de4sdv_spike:frame_publisher //de4sdv_spike:spike_someip_config //deployment:gateway_tar)

start=$(date +%s)
set +e
bazel build -c opt --keep_going "${targets[@]}" 2>&1 | tee "$out/bazel_build.log"
build_status=${PIPESTATUS[0]}
set -e
end=$(date +%s)
python3 - "$out/build_time.json" "$start" "$end" "$build_status" "${SPIKE_CACHE_HIT:-unknown}" <<'EOF'
import json, sys
path, start, end, status, cache_hit = sys.argv[1:]
json.dump({"command": "bazel build -c opt (gateway daemons, serializer, spike publisher, config, gateway_tar)",
           "wall_s": int(end) - int(start), "exit_code": int(status),
           "bazel_cache_restored": cache_hit}, open(path, "w"), indent=2)
EOF
cat "$out/build_time.json"

# Resolved module versions (communication, baselibs) and the lockfile state.
bazel mod explain score_communication score_baselibs > "$out/bazel_mod_explain.txt" 2>&1 || true
bazel mod graph --depth=1 > "$out/bazel_mod_graph_depth1.txt" 2>&1 || true
bazel mod show_repo score_communication score_baselibs > "$out/bazel_mod_show_repo.txt" 2>&1 || true
git status --porcelain --untracked-files=all > "$out/gateway_status_after_build.txt"
git diff --stat > "$out/gateway_diff_after_build.txt"

if [ "$build_status" -ne 0 ]; then
  echo "bazel build failed with $build_status" >&2
  exit "$build_status"
fi

set +e
bazel test -c opt //de4sdv_spike:all 2>&1 | tee "$out/bazel_test_spike_configs.log"
set -e

bin=$(bazel info -c opt bazel-bin)
gatewayd="$bin/score/gatewayd/gatewayd"
someipd="$bin/score/someipd/someipd"
publisher="$bin/de4sdv_spike/frame_publisher"
config_bin="$bin/de4sdv_spike/spike_someip_config.bin"
serializer=$(find -L "$bin/score/serializer" -maxdepth 1 -name 'score_com_serializer.so' | head -1)
# The directory must hold the plugins vsomeip dlopens by name (-cfg, -sd, -e2e).
vsomeip_lib=""
for candidate in $(find -L "$bin" -name 'libvsomeip3.so.3' -not -path '*.runfiles*' 2>/dev/null); do
  if [ -e "$(dirname "$candidate")/libvsomeip3-sd.so.3" ] && [ -e "$(dirname "$candidate")/libvsomeip3-cfg.so.3" ]; then
    vsomeip_lib=$candidate
    break
  fi
done
if [ -z "$vsomeip_lib" ]; then
  echo "no directory with libvsomeip3.so.3 and its plugins under $bin" >&2
  find -L "$bin" -name 'libvsomeip3*' 2>/dev/null | head -20 >&2
  exit 1
fi
gateway_tar=$(find -L "$bin/deployment" -maxdepth 1 -name 'gateway_tar*.tar.gz' | head -1)
host_ld="$(dirname "$serializer"):$(dirname "$vsomeip_lib")"

python3 - "$paths_json" <<EOF
import json, os
paths = json.load(open("$paths_json")) if os.path.exists("$paths_json") else {}
paths.update({
    "gatewayd": "$gatewayd",
    "someipd": "$someipd",
    "publisher": "$publisher",
    "someip_config_bin": "$config_bin",
    "mw_com_publisher": "$spike_dir/config/mw_com_config_publisher.json",
    "mw_com_gatewayd": "$spike_dir/config/mw_com_config_gatewayd.json",
    "mw_com_publisher_2subs": "$spike_dir/config/mw_com_config_publisher_2subs.json",
    "mw_com_gatewayd_2subs": "$spike_dir/config/mw_com_config_gatewayd_2subs.json",
    "mw_com_gatewayd_mwcom": "$spike_dir/config/mw_com_config_gatewayd_mwcom.json",
    "mw_com_gatewayd_2subs_mwcom": "$spike_dir/config/mw_com_config_gatewayd_2subs_mwcom.json",
    "mw_com_someipd": "$spike_dir/config/mw_com_config_someipd.json",
    "mw_log_debug": "$spike_dir/config/mw_log_debug.json",
    "vsomeip_host": "$spike_dir/config/vsomeip_host.json",
    "vsomeip_guest": "$spike_dir/config/vsomeip_guest.json",
    "host_ld_library_path": "$host_ld",
    # message_passing (main a4dce403 and earlier) or mw_com (PR #375): decides the
    # daemons' command lines, manifests and log lines in xdomain.py
    "ipc_binding": "${IPC_BINDING:-message_passing}",
    "pin": "${SPIKE_PIN:-}",
    "gateway_sha": "${GATEWAY_SHA:-}",
})
json.dump(paths, open("$paths_json", "w"), indent=2)
EOF
cat "$paths_json"

{
  for f in "$gatewayd" "$someipd" "$publisher"; do
    echo "== ldd $(basename "$f")"
    LD_LIBRARY_PATH="$host_ld" ldd "$f" || true
  done
} > "$out/ldd_host.txt" 2>&1

# Sizes: as built (opt, not stripped) and stripped copies; the gateway's own
# deployment package.
python3 - "$out/sizes_host.json" "$gatewayd" "$someipd" "$serializer" "$publisher" "$gateway_tar" \
  "$(dirname "$vsomeip_lib")" <<'EOF'
import json, os, shutil, subprocess, sys, tempfile, glob
path, gatewayd, someipd, serializer, publisher, gateway_tar, vsomeip_dir = sys.argv[1:]
files = {"gatewayd": gatewayd, "someipd": someipd, "score_com_serializer.so": serializer,
         "frame_publisher (spike)": publisher}
for lib in sorted(glob.glob(os.path.join(vsomeip_dir, "libvsomeip3*.so.3*"))):
    files[os.path.basename(lib)] = lib
sizes = {}
tmp = tempfile.mkdtemp()
for name, f in files.items():
    real = os.path.realpath(f)
    entry = {"path": f, "bytes": os.path.getsize(real)}
    copy = os.path.join(tmp, os.path.basename(real))
    shutil.copy(real, copy)
    os.chmod(copy, 0o755)
    if subprocess.run(["strip", "--strip-all", copy]).returncode == 0:
        entry["stripped_bytes"] = os.path.getsize(copy)
    sizes[name] = entry
runtime = ["gatewayd", "someipd", "score_com_serializer.so"] + [n for n in files if n.startswith("libvsomeip3")]
total = sum(sizes[n]["bytes"] for n in runtime if n in sizes)
total_stripped = sum(sizes[n].get("stripped_bytes", sizes[n]["bytes"]) for n in runtime if n in sizes)
result = {"files": sizes, "gateway_runtime_closure_bytes": total, "gateway_runtime_closure_stripped_bytes": total_stripped,
          "note": "runtime closure = gatewayd, someipd, null serializer and the vsomeip 3.6.1 libraries Bazel built; "
                  "system libraries (libc, libstdc++) excluded; see ldd_host.txt"}
if gateway_tar:
    result["deployment_gateway_tar"] = {"path": gateway_tar, "bytes": os.path.getsize(os.path.realpath(gateway_tar))}
json.dump(result, open(path, "w"), indent=2)
print(json.dumps(result, indent=2))
EOF

# The gateway's own launch script, as packaged in //deployment:gateway_tar.
# Each daemon alone first (exit 124 = still running when the 5 s timeout hit),
# then both together for 8 s in a throwaway network and mount namespace with a
# private /tmp and /dev/shm, so that their LoLa files cannot reach the scenarios.
if [ -n "$gateway_tar" ]; then
  tar_dir=$(mktemp -d "${RUNNER_TEMP:-/var/tmp}/gateway_tar.XXXXXX")
  tar -xzf "$gateway_tar" -C "$tar_dir"
  tar -tzvf "$gateway_tar" > "$out/gateway_tar_listing.txt"
  script=$(find "$tar_dir" -name run_gateway.sh | head -1)
  {
    echo "== $script gatewayd"
    set +e
    (cd "$(dirname "$script")" && timeout 5 ./run_gateway.sh gatewayd)
    echo "exit=$?"
    echo "== $script someipd"
    (cd "$(dirname "$script")" && VSOMEIP_CONFIGURATION=/nonexistent timeout 5 ./run_gateway.sh someipd)
    echo "exit=$?"
    echo "== packaged score_com_serializer.so"
    find "$tar_dir" -name 'score_com_serializer.so' | sed "s|$tar_dir/||" || true
    set -e
  } > "$out/run_gateway_sh_check.txt" 2>&1 || true
  {
    echo "== both packaged daemons for 8 s (someipd first, gatewayd 1 s later)"
    sudo unshare --net --mount --propagation private -- bash -c '
      set +e
      mount -t tmpfs tmpfs /tmp && mount -t tmpfs tmpfs /dev/shm
      ip link set lo up
      cd "$1"
      VSOMEIP_CONFIGURATION=/nonexistent timeout 8 ./run_gateway.sh someipd > /tmp/someipd.log 2>&1 &
      someipd_pid=$!
      sleep 1
      timeout 7 ./run_gateway.sh gatewayd > /tmp/gatewayd.log 2>&1
      echo "gatewayd exit=$?"
      wait "$someipd_pid"
      echo "someipd exit=$?"
      echo "--- someipd log (head)"; head -40 /tmp/someipd.log
      echo "--- gatewayd log (head)"; head -40 /tmp/gatewayd.log
    ' _ "$(dirname "$script")"
  } > "$out/gateway_tar_pair_check.txt" 2>&1 || true
  rm -rf "$tar_dir"
fi
