#!/bin/sh
# Central gateway entrypoint: two buses in, one policy between them.
#
# Each bridge owns one side of the gateway and speaks UDP to exactly one zone
# over the slice. The router never sees a tunnel directly; it forwards between
# the two local vcan interfaces, which keeps the policy independent of the
# transport.
#
# The three processes are one gateway: if any of them exits, the gateway is
# broken, so the entrypoint stops the others and exits non-zero for whoever
# supervises the container. SIGTERM stops all three and exits 0.
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

run_dir="${TMPDIR:-/tmp}/gw.$$"
mkdir -p "${run_dir}"

# tunnel NAME CAN PEER PEER_PORT LISTEN: a bridge with its log prefixed. The
# bridge's own pid goes to a file, so it (not the log filter) gets the signal;
# the pipeline's pid ($!) lives exactly as long as the bridge does.
tunnel() {
  { python -u /opt/gw/bridge.py --can "$2" --remote "$3:$4" --listen "$5" &
    echo "$!" > "${run_dir}/$1.pid"
    rc=0; wait "$!" || rc=$?
    echo "exited with status ${rc}"
  } 2>&1 | sed -u "s/^/[$1] /" &
}

tunnel tun-front vcan-front "${GW_FRONT_PEER}" "${GW_FRONT_PEER_PORT}" "${GW_FRONT_LISTEN}"
front_pid=$!
tunnel tun-rear vcan-rear "${GW_REAR_PEER}" "${GW_REAR_PEER_PORT}" "${GW_REAR_LISTEN}"
rear_pid=$!

sleep 1
python /opt/gw/router.py --front vcan-front --rear vcan-rear &
router_pid=$!

shutdown() {
  trap '' INT TERM
  set +e  # a child that is already gone must not end the cleanup early
  for name in tun-front tun-rear; do
    [ -f "${run_dir}/${name}.pid" ] && kill -TERM "$(cat "${run_dir}/${name}.pid")" 2>/dev/null
  done
  kill -TERM "${router_pid}" 2>/dev/null
  wait  # let the router and bridges print their counters
  rm -rf "${run_dir}"
  exit "$1"
}
trap 'shutdown 0' INT TERM

while :; do
  for pid in "${front_pid}" "${rear_pid}" "${router_pid}"; do
    kill -0 "${pid}" 2>/dev/null || break 2
  done
  sleep 1
done
echo "[gw] a gateway process exited; taking the gateway down" >&2
shutdown 1
