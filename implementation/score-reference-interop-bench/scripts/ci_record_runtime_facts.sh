#!/usr/bin/env bash
# Records the facts of a runtime job of the bench: the runner image, the
# kernel, the user, the flags of the loopback interface, the shared libstdc++
# (package version, resolved file and SHA-256), gdb, the ROS 2 environment
# that config/ros_environment.sh of the runtime bundle gives, and the digests
# of the runtime bundle.
# Usage: ci_record_runtime_facts.sh [--runner] <facts-dir> <bundle-dir> [<bundle-archive>]
set -uo pipefail
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

out=${1:?usage: ci_record_runtime_facts.sh <facts-dir> <bundle-dir> [<bundle-archive>]}
bundle=${2:?usage: ci_record_runtime_facts.sh <facts-dir> <bundle-dir> [<bundle-archive>]}
archive=${3:-}
mkdir -p "$out"

{
  echo "== runner image"
  echo "ImageOS=${ImageOS:-} ImageVersion=${ImageVersion:-} RUNNER_ARCH=${RUNNER_ARCH:-}"
  if [ -r /imagegeneration/imagedata.json ]; then
    cat /imagegeneration/imagedata.json
  fi
  echo "== kernel"
  uname -a
  echo "== user (the bench runs as this non-root user)"
  id
  echo "== loopback interface (IFF_MULTICAST is 0x1000)"
  ip -d link show lo
  echo "flags=$(cat /sys/class/net/lo/flags)"
  echo "== shared libstdc++"
  dpkg-query -W libstdc++6
  libstdcxx=$(readlink -f /lib/x86_64-linux-gnu/libstdc++.so.6)
  echo "resolved: $libstdcxx"
  sha256sum "$libstdcxx"
  echo "== gdb"
  gdb --version | head -1
  echo "== ROS 2 environment of the bench ($bundle/config/ros_environment.sh)"
  (
    set +u
    unset ROS_LOCALHOST_ONLY RMW_IMPLEMENTATION CYCLONEDDS_URI ROS_DOMAIN_ID
    source /opt/ros/humble/setup.bash
    source "$bundle/config/ros_environment.sh"
    for name in RMW_IMPLEMENTATION CYCLONEDDS_URI ROS_DOMAIN_ID ROS_LOCALHOST_ONLY; do
      echo "$name=${!name-<unset>}"
    done
  )
  echo "== runtime bundle"
  if [ -n "$archive" ] && [ -f "$archive" ]; then
    sha256sum "$archive"
  fi
  sha256sum "$bundle"/bin/* "$bundle"/config/*
} 2>&1 | tee "$out/runtime_facts.txt"
