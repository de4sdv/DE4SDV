#!/usr/bin/env bash
# Installs ROS 2 Humble on a GitHub-hosted ubuntu-22.04 runner from the
# immutable ROS snapshot repository of one date, so every job of every run
# gets the same Debian packages. The snapshot's signing key is fetched from
# the Ubuntu key server and accepted only with the pinned fingerprint. The
# installed versions are recorded.
# Usage: ci_install_ros.sh [--runner] <facts-dir> <build|runtime>
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]:?}")/runner_only.sh" || exit 2

out=${1:?usage: ci_install_ros.sh <facts-dir> <build|runtime>}
mode=${2:?usage: ci_install_ros.sh <facts-dir> <build|runtime>}
mkdir -p "$out"

snapshot_date=2026-10-12
key_fingerprint=4B63CF8FDE49746E98FA01DDAD19BAB3CBF125EA
keyring=/usr/share/keyrings/ros-snapshots-archive-keyring.gpg

work=$(mktemp -d)
curl -fsSL --retry 5 -o "$work/key.asc" \
  "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x${key_fingerprint}"
fingerprints=$(gpg --show-keys --with-colons "$work/key.asc" | awk -F: '$1 == "fpr" {print $10}')
if ! printf '%s\n' "$fingerprints" | grep -qx "$key_fingerprint"; then
  echo "the key server returned no key with fingerprint $key_fingerprint" >&2
  exit 1
fi
if [ "$(printf '%s\n' "$fingerprints" | head -1)" != "$key_fingerprint" ]; then
  echo "the primary key is not $key_fingerprint" >&2
  exit 1
fi
gpg --dearmor < "$work/key.asc" > "$work/keyring.gpg"
sudo install -m 0644 "$work/keyring.gpg" "$keyring"
echo "deb [arch=amd64 signed-by=$keyring] http://snapshots.ros.org/humble/$snapshot_date/ubuntu jammy main" |
  sudo tee /etc/apt/sources.list.d/ros2-snapshot.list

# rmw_cyclonedds_cpp by name: rmw_implementation of ros-base asks for one
# ROS 2 middleware (rmw_fastrtps_cpp, rmw_cyclonedds_cpp or rmw_connextdds),
# and apt takes the named one, so no Fast DDS is installed.
packages=(ros-humble-ros-base ros-humble-rmw-cyclonedds-cpp ros-humble-autoware-vehicle-msgs)
if [ "$mode" = "build" ]; then
  packages+=(ros-humble-ament-cmake-gtest python3-colcon-common-extensions)
else
  packages+=(gdb)
fi
sudo apt-get update -o Acquire::Retries=5
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -o Acquire::Retries=5 --no-install-recommends "${packages[@]}"

{
  echo "snapshot: http://snapshots.ros.org/humble/$snapshot_date/ubuntu jammy main"
  echo "signing key fingerprint: $key_fingerprint"
  echo "mode: $mode"
  dpkg-query -W 'ros-humble-*' python3-colcon-core python3-colcon-common-extensions gdb 2>/dev/null || true
} > "$out/ros_packages_${mode}.txt"
grep -E "ros-humble-(rclcpp|rmw-cyclonedds-cpp|cyclonedds|autoware-vehicle-msgs|ros2param)\s" \
  "$out/ros_packages_${mode}.txt" || true
rm -rf "$work"
