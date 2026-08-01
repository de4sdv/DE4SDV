#!/usr/bin/env bash
# Read-only WSL/Linux preflight for the DE4SDV AAOS SDV reference proof.
set -u

printf 'DE4SDV AAOS SDV WSL preflight\n\n'
printf '[system]\n'
uname -a
printf 'architecture: '; uname -m
if [ -r /etc/os-release ]; then
  . /etc/os-release
  printf 'distribution: %s %s\n' "${ID:-unknown}" "${VERSION_ID:-unknown}"
  if [ "${ID:-}" = "docker-desktop" ]; then
    printf 'WARNING: this is Docker Desktop internal WSL; use Ubuntu-22.04 instead.\n'
  fi
fi
printf '\n[memory]\n'
free -h
printf '\n[storage]\n'
df -h "$HOME" /
printf '\n[tools]\n'
for tool in git python3 make gcc adb fastboot repo docker; do
  if command -v "$tool" >/dev/null 2>&1; then
    printf '%-10s %s\n' "$tool" "$(command -v "$tool")"
  else
    printf '%-10s MISSING\n' "$tool"
  fi
done
printf '\n[docker]\n'
if command -v docker >/dev/null 2>&1; then
  docker info --format 'server={{.ServerVersion}} arch={{.Architecture}}' 2>&1 || true
else
  printf 'Docker CLI unavailable\n'
fi
printf '\n[recommendation]\n'
printf 'Keep AOSP under the WSL Linux filesystem, for example ~/aosp, not /mnt/c.\n'
printf 'Minimum practical target: x86_64, 16 GiB RAM, 300 GiB free storage.\n'
