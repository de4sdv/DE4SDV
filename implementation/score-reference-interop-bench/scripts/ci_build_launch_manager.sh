#!/usr/bin/env bash
# Builds the Launch Manager of eclipse-score/lifecycle v0.6.1 in a throwaway
# checkout of its own workspace (Bazel 8.7.0 from .bazelversion via bazelisk,
# communication 0.4.0 and baselibs 0.2.12 from its MODULE.bazel), with the
# toolchain configuration of lifecycle's own CI (--config=x86_64-linux), and
# serializes the DE4SDV Launch Manager configuration with lifecycle's own
# launch_manager_config rule (schema check, mapping, flatbuffer). First
# scripts/render_launch_manager_config.py renders the configuration for this
# host: the ROS 2 setup of /opt/ros/humble for the ROS 2 components, and the
# bench user as sandbox user and group.
# Usage: ci_build_launch_manager.sh <checkout-dir> <facts-dir> <output-dir> <bench-dir>
set -euo pipefail

lc=${1:?}
out=${2:?}
dest=${3:?}
bench=${4:?}
: "${LIFECYCLE_REPO:?}" "${LIFECYCLE_SHA:?}"
mkdir -p "$out" "$dest"
here=$(cd "$(dirname "$0")" && pwd)

overlay=$(mktemp -d)
cp -r "$bench/launch-manager/." "$overlay/"
python3 "$here/render_launch_manager_config.py" "$bench/launch-manager/launch_manager_config.json" \
  "$overlay/launch_manager_config.json" --uid "$(id -u)" --gid "$(id -g)" > "$out/launch_manager_ros_setup.json"
cp "$overlay/launch_manager_config.json" "$out/launch_manager_config_rendered.json"
{
  echo "committed: $(sha256sum "$bench/launch-manager/launch_manager_config.json")"
  echo "rendered for uid $(id -u) gid $(id -g): $(sha256sum "$overlay/launch_manager_config.json")"
} | tee "$out/launch_manager_config_render.txt"

bash "$here/ci_checkout_upstream.sh" "$LIFECYCLE_REPO" "$LIFECYCLE_SHA" "$lc" "$out" lifecycle \
  "$overlay=de4sdv_score_bench"
cd "$lc"
bazel --version | tee "$out/launch_manager_bazel_version.txt"
targets=(//score/launch_manager:launch_manager //de4sdv_score_bench:de4sdv_lm_config)
start=$(date +%s)
set +e
bazel build --config=x86_64-linux "${targets[@]}" 2>&1 | tee "$out/launch_manager_build.log"
status=${PIPESTATUS[0]}
set -e
end=$(date +%s)
echo "{\"command\": \"bazel build --config=x86_64-linux ${targets[*]}\", \"wall_s\": $((end - start)), \"exit_code\": $status, \"bazel_cache_restored\": \"${BAZEL_CACHE_RESTORED:-unknown}\"}" |
  tee "$out/launch_manager_build_time.json"
bazel mod explain score_communication score_baselibs > "$out/launch_manager_mod_explain.txt" 2>&1 || true
git status --porcelain --untracked-files=all > "$out/lifecycle_status_after_build.txt"
if [ "$status" -ne 0 ]; then
  exit "$status"
fi
# "bazel info" with --config=x86_64-linux cannot resolve the apparent
# repository name in --host_platform; the workspace's bazel-bin link points to
# the output tree of this build instead.
bin="$lc/bazel-bin"
cp -L "$bin/score/launch_manager/src/daemon/launch_manager" "$dest/launch_manager"
find -L "$bin/de4sdv_score_bench" -type f \( -name '*.bin' -o -name '*_gen.json' \) -exec cp {} "$dest/" \;
{
  echo "== outputs"
  (cd "$dest" && sha256sum ./*)
  echo "== launch_manager"
  file "$dest/launch_manager" || true
  ldd "$dest/launch_manager" || true
} | tee "$out/launch_manager_outputs.txt"
