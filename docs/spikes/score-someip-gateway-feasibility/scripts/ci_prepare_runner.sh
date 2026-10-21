#!/usr/bin/env bash
# DE4SDV throwaway spike (INC-MW-011 gateway feasibility), never merged.
# Prepares a GitHub-hosted ubuntu runner: installs bazelisk, lets Bazel's
# linux-sandbox create user namespaces (Ubuntu 24.04 AppArmor restriction, as
# the gateway's own CI does with its unblock-user-namespace action), and writes
# ~/.bazelrc with an output base on the larger disk. Prints the runner facts
# the report needs.
set -euo pipefail

out=${1:?usage: ci_prepare_runner.sh <facts-dir> [--disk-cache]}
disk_cache=${2:-}
mkdir -p "$out"

{
  echo "== runner"
  echo "ImageOS=${ImageOS:-} ImageVersion=${ImageVersion:-} RUNNER_ARCH=${RUNNER_ARCH:-}"
  uname -a
  nproc
  free -g
  echo "== disk before cleanup"
  df -h / /mnt 2>/dev/null || df -h /
} | tee "$out/runner.txt"

# No disk cleanup: the ubuntu-24.04 runner (image 20261012.334.1) has a 145G
# root disk with 86G free. Run 39678067776 showed that deleting the preinstalled
# Android SDK breaks the gateway's Bazel analysis: ANDROID_HOME stays set and
# the rules_android SDK repository rule fails on the missing SDK.
echo "ANDROID_HOME=${ANDROID_HOME:-} ANDROID_SDK_ROOT=${ANDROID_SDK_ROOT:-}" | tee -a "$out/runner.txt"

# The ubuntu-24.04 image (20261012.334.1) has no bazel or bazelisk on PATH:
# install bazelisk v1.29.0, checked by digest. It runs the Bazel version of the
# checkout's .bazelversion; BAZELISK_VERIFY_SHA256 (workflow env) pins that
# binary's digest too.
bazelisk_sha=5a408715e932c0250d28bd84555f12edbf70117de42f9181691c736eacc4a992
curl -fsSL -o /tmp/bazelisk https://github.com/bazelbuild/bazelisk/releases/download/v1.29.0/bazelisk-linux-amd64
echo "$bazelisk_sha  /tmp/bazelisk" | sha256sum -c - | tee -a "$out/runner.txt"
sudo install -m 0755 /tmp/bazelisk /usr/local/bin/bazelisk
sudo ln -sf /usr/local/bin/bazelisk /usr/local/bin/bazel

# Bazel's linux-sandbox needs unprivileged user namespaces for the tests.
sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0 | tee -a "$out/runner.txt" || true

base="$HOME/spike-bazel"
if sudo mkdir -p /mnt/spike-bazel 2>/dev/null; then
  avail_mnt=$(df --output=avail -k /mnt | tail -1)
  avail_root=$(df --output=avail -k / | tail -1)
  if [ "$avail_mnt" -gt "$avail_root" ]; then
    sudo chown -R "$USER:$USER" /mnt/spike-bazel
    base=/mnt/spike-bazel
  fi
fi
mkdir -p "$base/output_base"
cat > "$HOME/.bazelrc" <<EOF
startup --output_base=$base/output_base
common --repository_cache=$HOME/.cache/spike-bazel/repo
common --color=no --curses=no --show_progress_rate_limit=60
EOF
if [ "$disk_cache" = "--disk-cache" ]; then
  echo "build --disk_cache=$HOME/.cache/spike-bazel/disk" >> "$HOME/.bazelrc"
fi
echo "== ~/.bazelrc" | tee -a "$out/runner.txt"
cat "$HOME/.bazelrc" | tee -a "$out/runner.txt"
echo "== bazel (bazelisk) on PATH: $(command -v bazel)" | tee -a "$out/runner.txt"
