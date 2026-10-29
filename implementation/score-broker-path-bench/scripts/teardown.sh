#!/usr/bin/env bash
# Undo every change the bench scripts make on the VM, in the safe order, and
# record what it did in a run-directory session log. It is idempotent: a change
# already undone is skipped. It never deletes the evidence under the run
# directory, and it never edits the tracked VM-CHANGE-LOG.md.
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"
: "${RUN_DIR:=$HERE/../run}"; mkdir -p "$RUN_DIR"

log "teardown start"
# 1. Stop the recording panes and the guest screenrecord.
"$HERE/record_full_chain.sh" stop "$RUN_DIR/recording" 2>/dev/null || true
"$ADB" -s "$IVI_ADB" shell "pkill -INT screenrecord" 2>/dev/null || true
# 2. Remove the relay provisioning from the IVI VM (reboots it), when the relay
#    inputs are set; otherwise nothing was provisioned by this bench to undo.
if require_relay_inputs >/dev/null 2>&1; then
  "$HERE/provision_ivi_relay.sh" remove 2>/dev/null || log "relay provisioning already removed or IVI down"
else
  log "relay inputs unset; skipping relay-provisioning undo"
fi
# 3. Remove the host isolation firewall, the SD multicast route and the chrony allow.
"$HERE/host_isolation_firewall.sh" remove || true
"$HERE/host_sd_multicast_route.sh" remove || true
"$HERE/set_ivi_clock.sh" deny || true
# 4. Stop and remove both guest VMs.
"$HERE/launch_two_vms.sh" down || true
# 5. Revert the SDV Core image overlay (the base image is rebuilt on demand).
"$HERE/build_sdv_core_image.sh" revert || true

cat >> "$RUN_DIR/vm-change-log.session.txt" <<EOF
teardown $(date -u +%FT%T.%NZ): stopped recordings; removed relay provisioning, firewall, SD route, chrony allow; stopped and removed $CORE_GROUP and $IVI_GROUP; reverted the SDV Core overlay; kept the run evidence under $RUN_DIR
EOF
log "teardown done; session log in $RUN_DIR/vm-change-log.session.txt"
