#!/usr/bin/env bash
# Prepares a GitHub-hosted ubuntu-22.04 runner for a Bazel build of a pinned
# Eclipse S-CORE workspace: installs bazelisk v1.29.0 (checked by digest; the
# workflow also pins the Bazel binary by BAZELISK_VERIFY_SHA256), writes
# ~/.bazelrc with the output base on the larger disk and with the repository
# and disk caches under ~/.cache/de4sdv-bazel, and records the runner facts.
# Usage: ci_prepare_runner.sh [--runner] <facts-dir>
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]:?}")/runner_only.sh" || exit 2

out=${1:?usage: ci_prepare_runner.sh <facts-dir>}
mkdir -p "$out"

{
  echo "== runner"
  echo "ImageOS=${ImageOS:-} ImageVersion=${ImageVersion:-} RUNNER_ARCH=${RUNNER_ARCH:-}"
  uname -a
  echo "nproc=$(nproc)"
  free -g
  echo "== user (the bench runs as this non-root user)"
  id
  echo "== disk"
  df -h / /mnt 2>/dev/null || df -h /
  echo "== compilers"
  for compiler in gcc g++ gcc-12 g++-12; do
    command -v "$compiler" >/dev/null && "$compiler" --version | head -1 | sed "s|^|$compiler: |"
  done
  dpkg-query -W libstdc++6 binutils 2>/dev/null || true
  ld --version | head -1
} | tee "$out/runner.txt"

bazelisk_sha=5a408715e932c0250d28bd84555f12edbf70117de42f9181691c736eacc4a992
curl -fsSL --retry 5 -o /tmp/bazelisk https://github.com/bazelbuild/bazelisk/releases/download/v1.29.0/bazelisk-linux-amd64
echo "$bazelisk_sha  /tmp/bazelisk" | sha256sum -c - | tee -a "$out/runner.txt"
sudo install -m 0755 /tmp/bazelisk /usr/local/bin/bazelisk
sudo ln -sf /usr/local/bin/bazelisk /usr/local/bin/bazel
echo "BAZELISK_VERIFY_SHA256=${BAZELISK_VERIFY_SHA256:-unset}" | tee -a "$out/runner.txt"

base="$HOME/de4sdv-bazel"
if sudo mkdir -p /mnt/de4sdv-bazel 2>/dev/null; then
  avail_mnt=$(df --output=avail -k /mnt | tail -1)
  avail_root=$(df --output=avail -k / | tail -1)
  if [ "$avail_mnt" -gt "$avail_root" ]; then
    sudo chown -R "$(id -u):$(id -g)" /mnt/de4sdv-bazel
    base=/mnt/de4sdv-bazel
  fi
fi
mkdir -p "$base/output_base" "$HOME/.cache/de4sdv-bazel"
cat > "$HOME/.bazelrc" <<EOF
startup --output_base=$base/output_base
common --repository_cache=$HOME/.cache/de4sdv-bazel/repo
common --color=no --curses=no --show_progress_rate_limit=60
build --disk_cache=$HOME/.cache/de4sdv-bazel/disk
EOF
{
  echo "== ~/.bazelrc"
  cat "$HOME/.bazelrc"
  echo "== bazel on PATH: $(command -v bazel)"
} | tee -a "$out/runner.txt"
