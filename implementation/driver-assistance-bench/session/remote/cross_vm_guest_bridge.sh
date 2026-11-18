#!/bin/bash
# Reused unchanged below this header from INC-DRIVING-001's session kit (outputs/slice10b/WP2/session10_scripts/,
# sha256 fd315d9430d44eee... of the original). The session runs it with sudo on both ends of the VXLAN segment.
# Bridge a Cuttlefish guest network (cvd-ebr, 192.168.98.0/24) to a second VM over VXLAN.
#   guest-host: the VM running the guests. vx98 becomes a port of cvd-ebr and the host's own bridge
#               address moves from .1 to .254 (run AFTER the guests have leased their addresses).
#   host-half:  the VM running the SOME/IP host half. It takes 192.168.98.1 on vx98 (the address the SDV
#               Core guest's vsomeip configuration pins) and routes SD multicast (224.0.0.0/4) there.
# Generalized from the executed split-bench probe scripts (~/.hermes/outputs/de4sdv-probes/P4/).
# Run `show` first: it changes nothing.
# usage: sudo cross_vm_guest_bridge.sh guest-host|host-half add|remove|show <peer internal IP>
# env:   BR (cvd-ebr) VNI (98) MTU (1410 = VPC 1460 - 50) ADDR (192.168.98.1/24) MOVED (192.168.98.254/24)
set -eu
ROLE=${1:?guest-host|host-half}; ACTION=${2:?add|remove|show}; REMOTE=${3:-}
BR=${BR:-cvd-ebr}; VNI=${VNI:-98}; MTU=${MTU:-1410}
ADDR=${ADDR:-192.168.98.1/24}; MOVED=${MOVED:-192.168.98.254/24}
DEV=$(ip -4 route show default | awk '{print $5; exit}')
LOCAL=$(ip -4 -o addr show dev "$DEV" | awk '{print $4}' | cut -d/ -f1)

make_vxlan() {
  ip link show vx98 >/dev/null 2>&1 || ip link add vx98 type vxlan id "$VNI" remote "${REMOTE:?peer internal IP}" local "$LOCAL" dstport 4789 dev "$DEV"
  ip link set vx98 mtu "$MTU"
}

case "$ROLE:$ACTION" in
  guest-host:add)
    make_vxlan
    ip link set vx98 master "$BR"
    ip link set vx98 up
    # delete .1 first: removing a primary address can take its secondaries with it
    ip addr del "$ADDR" dev "$BR" 2>/dev/null || true
    ip addr show dev "$BR" | grep -q "${MOVED%/*}/" || ip addr add "$MOVED" dev "$BR" ;;
  guest-host:remove)
    ip link del vx98 2>/dev/null || true
    ip addr del "$MOVED" dev "$BR" 2>/dev/null || true
    ip addr show dev "$BR" | grep -q "${ADDR%/*}/" || ip addr add "$ADDR" dev "$BR" ;;
  host-half:add)
    make_vxlan
    ip link set vx98 up
    ip addr replace "$ADDR" dev vx98
    ip route replace 224.0.0.0/4 dev vx98 ;;
  host-half:remove)
    ip route del 224.0.0.0/4 dev vx98 2>/dev/null || true
    ip link del vx98 2>/dev/null || true ;;
  guest-host:show|host-half:show) : ;;
  *) echo "usage: $0 guest-host|host-half add|remove|show <peer internal IP>" >&2; exit 2 ;;
esac

ip -d -br link show vx98 2>/dev/null || echo "no vx98"
if [ "$ROLE" = guest-host ]; then
  ip -4 -br addr show dev "$BR"
  bridge link show 2>/dev/null | grep -E "vx98|cvd-etap" | grep -v NO-CARRIER || true
else
  ip -4 -br addr show dev vx98 2>/dev/null || true
fi
ip route get 224.0.0.0 2>/dev/null | head -1
