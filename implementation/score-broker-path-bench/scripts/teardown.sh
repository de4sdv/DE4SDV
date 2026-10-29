#!/usr/bin/env bash
# Undo every change the bench scripts make on the VM, in the safe order, and
# record what it did in the VM change log. It is idempotent: a change already
# undone is skipped. It never deletes the evidence under the run directory.
set -u
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"
: "${RUN_DIR:=$HERE/../run}"

log "teardown start"
# 1. Stop the recordings if any are still running (best effort).
pkill -f "screenrecord .*/data/local/tmp/hmi.mp4" 2>/dev/null || true
# 2. Remove the relay provisioning from the IVI VM (reboots it).
"$HERE/provision_ivi_relay.sh" remove 2>/dev/null || log "relay provisioning already removed or IVI down"
# 3. Remove the host isolation firewall and the SD multicast route.
"$HERE/host_isolation_firewall.sh" remove || true
"$HERE/host_sd_multicast_route.sh" remove || true
# 4. Stop and remove both guest VMs.
"$HERE/launch_two_vms.sh" down || true
# 5. Revert the SDV Core image overlay (the base image is rebuilt on demand).
"$HERE/build_sdv_core_image.sh" revert || true

cat >> "$HERE/../VM-CHANGE-LOG.md" <<EOF

## Teardown $(date -u +%FT%T.%NZ)
- stopped recordings, removed the relay provisioning, the firewall and the SD route
- stopped and removed the guest VMs ($CORE_GROUP, $IVI_GROUP)
- reverted the SDV Core image overlay
- kept: the run directory evidence under $RUN_DIR
EOF
log "teardown done; see $HERE/../VM-CHANGE-LOG.md"
