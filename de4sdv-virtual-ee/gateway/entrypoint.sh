#!/bin/sh
# Central gateway entrypoint: two buses in, one policy between them.
#
# Each bridge owns one side of the gateway and speaks UDP to exactly one zone
# over the slice. The router never sees a tunnel directly; it forwards between
# the two local vcan interfaces, which keeps the policy independent of the
# transport.
set -eu

: "${GW_FRONT_PEER:?GW_FRONT_PEER must be the front zone address}"
: "${GW_REAR_PEER:?GW_REAR_PEER must be the rear zone address}"
: "${GW_FRONT_LISTEN:=10001}"
: "${GW_REAR_LISTEN:=10002}"
: "${GW_FRONT_PEER_PORT:=20001}"
: "${GW_REAR_PEER_PORT:=20002}"

for iface in vcan-front vcan-rear; do
  ip link show "${iface}" >/dev/null 2>&1 || ip link add "${iface}" type vcan
  ip link set "${iface}" up
done
echo "[gw] buses up: $(ip -br link show vcan-front) | $(ip -br link show vcan-rear)"

python -u /opt/gw/bridge.py --can vcan-front \
    --remote "${GW_FRONT_PEER}:${GW_FRONT_PEER_PORT}" --listen "${GW_FRONT_LISTEN}" \
  2>&1 | sed -u 's/^/[tun-front] /' &
python -u /opt/gw/bridge.py --can vcan-rear \
    --remote "${GW_REAR_PEER}:${GW_REAR_PEER_PORT}" --listen "${GW_REAR_LISTEN}" \
  2>&1 | sed -u 's/^/[tun-rear] /' &

sleep 1
exec python /opt/gw/router.py --front vcan-front --rear vcan-rear
