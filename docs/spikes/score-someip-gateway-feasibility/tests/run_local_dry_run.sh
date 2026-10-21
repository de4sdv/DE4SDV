#!/usr/bin/env bash
# DE4SDV throwaway spike (INC-MW-011 gateway feasibility), never merged.
# Local dry run of the tooling only: xdomain.py and analyze.py with stand-in
# processes (tests/fakes) in an unprivileged user, mount and network namespace,
# with private /tmp, /dev/shm and /run. Proves the plumbing (namespaces, veth,
# private guest /tmp, capture, waits, control files, analysis), never the
# gateway. Usage: run_local_dry_run.sh <out-dir> [scenarios]
set -euo pipefail

out=$(realpath -m "${1:?usage: run_local_dry_run.sh <out-dir> [scenarios]}")
scenarios=${2:-all}
here=$(cd "$(dirname "$0")" && pwd)
scripts=$(cd "$here/../scripts" && pwd)
config=$(cd "$here/../config" && pwd)
rm -rf "$out"
mkdir -p "$out"

cat > "$out/paths.json" <<EOF
{
  "gatewayd": "$here/fakes/fake_gatewayd.py",
  "someipd": "$here/fakes/fake_someipd.py",
  "publisher": "$here/fakes/fake_publisher.py",
  "client": "$here/fakes/fake_client.py",
  "someip_config_bin": "/nonexistent.bin",
  "mw_com_publisher": "$config/mw_com_config_publisher.json",
  "mw_com_gatewayd": "$config/mw_com_config_gatewayd.json",
  "mw_com_publisher_2subs": "$config/mw_com_config_publisher_2subs.json",
  "mw_com_gatewayd_2subs": "$config/mw_com_config_gatewayd_2subs.json",
  "mw_log_debug": "$config/mw_log_debug.json",
  "vsomeip_host": "$config/vsomeip_host.json",
  "vsomeip_guest": "$config/vsomeip_guest.json",
  "host_ld_library_path": "",
  "guest_ld_library_path": ""
}
EOF

# The output directory may live under /tmp (the scratch area); it is bound to
# /run/spike-out first, because /tmp is then replaced by a private tmpfs.
unshare --user --map-root-user --mount --net --fork bash -c "
  set -euo pipefail
  mount -t tmpfs tmpfs /run
  mkdir -p /run/netns /run/spike-out
  mount --bind '$out' /run/spike-out
  mount -t tmpfs tmpfs /tmp
  mount -t tmpfs tmpfs /dev/shm
  export SPIKE_CAPTURE_CMD='[\"python3\", \"$here/fakes/capture.py\", \"{if}\", \"{pcap}\"]'
  python3 '$scripts/xdomain.py' netns-up --out /run/spike-out/facts
  python3 '$scripts/xdomain.py' run --paths /run/spike-out/paths.json --out /run/spike-out/results --scenarios '$scenarios'
  python3 '$scripts/xdomain.py' netns-down
"
python3 "$scripts/analyze.py" "$out/results" --json "$out/results/analysis.json" --markdown "$out/results/analysis.md"
