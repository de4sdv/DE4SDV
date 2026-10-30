#!/usr/bin/env bash
# The host route for the SOME/IP service-discovery group on the KVM bridge
# (GAP-MW-047). The path has no unicast fallback: with multicast blocked the
# events stop when the TTL runs out. The group stays in 224.0.0.0/24, which a
# Linux bridge floods; a group outside it needs an IGMP querier or snooping
# off on the bridge.
#
#   host_sd_multicast_route.sh add       add the route (idempotent)
#   host_sd_multicast_route.sh remove    remove it (the undo)
#   host_sd_multicast_route.sh show      show the route and the group choice
set -u
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"

ROUTE="${SD_GROUP}/4"

snoop_warning() {
  local path="/sys/class/net/${HOST_BRIDGE}/bridge/multicast_snooping"
  if [ -r "$path" ] && [ "$(cat "$path" 2>/dev/null)" = "1" ]; then
    case "$SD_GROUP" in
      224.0.0.*) : ;;  # link-local group range: flooded regardless of snooping
      *) log "WARNING: IGMP snooping is on for ${HOST_BRIDGE} and ${SD_GROUP} is not in 224.0.0.0/24;"
         log "         run an IGMP querier or disable snooping, or the group may stop reaching a guest." ;;
    esac
  fi
}

case "${1:-show}" in
  add)
    require_cmd ip || exit 1
    if ip route show "$ROUTE" dev "$HOST_BRIDGE" 2>/dev/null | grep -q .; then
      log "route ${ROUTE} dev ${HOST_BRIDGE} already present"
    else
      sudo ip route add "$ROUTE" dev "$HOST_BRIDGE" scope link && log "added route ${ROUTE} dev ${HOST_BRIDGE}"
    fi
    snoop_warning ;;
  remove)
    sudo ip route del "$ROUTE" dev "$HOST_BRIDGE" 2>/dev/null && log "removed route ${ROUTE} dev ${HOST_BRIDGE}" \
      || log "no route ${ROUTE} dev ${HOST_BRIDGE}" ;;
  show)
    ip route show "$ROUTE" dev "$HOST_BRIDGE" 2>&1 || true
    log "SD group ${SD_GROUP}:${SD_PORT}" ;;
  *) echo "usage: $0 {add|remove|show}" >&2; exit 2 ;;
esac
