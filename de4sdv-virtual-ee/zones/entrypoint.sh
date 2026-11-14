#!/bin/sh
# Zone entrypoint: own the bus, then run the two halves of a zonal ECU.
#
#   1. create this zone's vcan (needs CAP_NET_ADMIN, granted per part in the
#      vxedge baseline via `run.cap_add: [NET_ADMIN]`);
#   2. kuksa-can-provider bridges that bus to the databroker on the slice;
#   3. zone_ecu.py is the plant: it consumes command frames and emits status
#      frames, including the acknowledgement the reference demo never sent.
#
# Either one dying takes the zone down (set -e + background job wait), because a
# zone that keeps its interface but lost its ECU would look healthy and feed
# nothing.
set -eu

: "${ZONE_DBC:?ZONE_DBC must point at this zone's DBC}"
: "${ZONE_ECU:?ZONE_ECU must be headlamp or wiper}"
: "${ZONE_CHANNEL:=vcan0}"
: "${ZONE_MAPPING:=/opt/zone/vss/mapping/${ZONE_ECU}.json}"
: "${KUKSA_ADDRESS:=grpc://127.0.0.1:55555}"
: "${CAN_TUNNEL_REMOTE:=}"

if ! ip link show "${ZONE_CHANNEL}" >/dev/null 2>&1; then
  ip link add dev "${ZONE_CHANNEL}" type vcan
fi
ip link set "${ZONE_CHANNEL}" up
echo "[zone] ${ZONE_CHANNEL} up ($(ip -br link show "${ZONE_CHANNEL}"))"

# Optional: carry this zone's bus across the slice to the central gateway.
# Without it the zone is a closed segment — which is exactly scope A.
# The bridge is DE4SDV's own: one frame in, one datagram out, no buffering.
tunnel_pid=""
if [ -n "${CAN_TUNNEL_REMOTE}" ]; then
  : "${CAN_TUNNEL_RPORT:?CAN_TUNNEL_RPORT is required with CAN_TUNNEL_REMOTE}"
  : "${CAN_TUNNEL_LPORT:?CAN_TUNNEL_LPORT is required with CAN_TUNNEL_REMOTE}"
  python -u /opt/zone/bridge.py --can "${ZONE_CHANNEL}" \
      --remote "${CAN_TUNNEL_REMOTE}:${CAN_TUNNEL_RPORT}" \
      --listen "${CAN_TUNNEL_LPORT}" \
    2>&1 | sed -u 's/^/[tunnel] /' &
  tunnel_pid=$!
  echo "[zone] bus tunnel to ${CAN_TUNNEL_REMOTE}:${CAN_TUNNEL_RPORT} (listen ${CAN_TUNNEL_LPORT})"
fi

sed -e "s|@@ZONE_DBC@@|${ZONE_DBC}|" \
    -e "s|@@ZONE_CHANNEL@@|${ZONE_CHANNEL}|" \
    -e "s|@@ZONE_MAPPING@@|${ZONE_MAPPING}|" \
    -e "s|@@KUKSA_ADDRESS@@|${KUKSA_ADDRESS}|" \
    /opt/zone/dbc_feeder.ini > /tmp/dbc_feeder.ini

# The broker may still be starting when the zone does. Waiting for it beats a
# boot-order race that killed a whole zone on the testbed: the front zone's
# provider hit "connection refused" three seconds early and the entrypoint took
# the zone down, so the vehicle came up with a silent zone.
broker_host_port="${KUKSA_ADDRESS#grpc://}"
broker_host="${broker_host_port%%:*}"
broker_port="${broker_host_port##*:}"
i=0
while [ "$i" -lt 60 ]; do
  if python - "$broker_host" "$broker_port" <<'PY'
import socket, sys
s = socket.socket()
s.settimeout(0.5)
sys.exit(0 if s.connect_ex((sys.argv[1], int(sys.argv[2]))) == 0 else 1)
PY
  then
    echo "[zone] broker ${broker_host}:${broker_port} reachable after ${i}s"
    break
  fi
  i=$((i + 1))
  sleep 1
done
if [ "$i" -ge 60 ]; then
  echo "[zone] broker unreachable after 60s; starting the provider anyway" >&2
fi

# The provider is supervised: a broker restart must not take the zone down.
# The plant is the zone — if it exits, the zone exits.
(
  while :; do
    [ -f /tmp/zone-stopping ] && break
    python /opt/provider/dbcfeeder.py \
          --config /tmp/dbc_feeder.ini \
          --dbc-default /opt/zone/dbc/dbc_default_values.json \
          --dbc2val --val2dbc \
          2>&1 | sed -u 's/^/[provider] /'
    [ -f /tmp/zone-stopping ] && break
    echo "[provider] exited; restarting in 2s" >&2
    sleep 2
  done
) &
provider_pid=$!

python /opt/zone/zone_ecu.py \
      --ecu "${ZONE_ECU}" \
      --dbc "${ZONE_DBC}" \
      --channel "${ZONE_CHANNEL}" \
      2>&1 | sed -u 's/^/[ecu] /' &

ecu_pid=$!

# Optional: this zone also hosts the OpenBSW reference ECU, which answers UDS over
# DoCAN. It shares the zone's bus with the plant, because that is what a zonal
# controller is — several functions on one node, one segment. A diagnostic sent to
# 0x7E0 on the far side of the gateway reaches it through the router.
uds_pid=""
if [ "${ZONE_UDS_ECU:-0}" = "1" ]; then
  if [ "${ZONE_CHANNEL}" = "vcan0" ]; then
    /opt/zone/openbsw/referenceApp 2>&1 | sed -u 's/^/[openbsw] /' &
    uds_pid=$!
    echo "[zone] OpenBSW reference ECU on ${ZONE_CHANNEL}: UDS 0x7E0 request, 0x7E8 response"
  else
    echo "[zone] ZONE_UDS_ECU=1 needs vcan0: the reference app binds that name" >&2
  fi
fi

term() {
  # Tell the provider supervisor to stop restarting, then take the children down.
  : > /tmp/zone-stopping
  kill -TERM "${provider_pid}" "${ecu_pid}" 2>/dev/null || true
  [ -n "${tunnel_pid}" ] && kill -TERM "${tunnel_pid}" 2>/dev/null || true
  [ -n "${uds_pid}" ] && kill -TERM "${uds_pid}" 2>/dev/null || true
  # No `wait` here. The provider runs under a supervisor, so waiting for every child
  # waits forever on that supervisor — which is how a zone whose plant had died kept
  # its container "running" while it published nothing. The container must exit so the
  # orchestrator, and whoever is watching, can see the zone is gone.
  exit 0
}
trap term INT TERM

alive() {
  kill -0 "${provider_pid}" 2>/dev/null && kill -0 "${ecu_pid}" 2>/dev/null || return 1
  [ -n "${tunnel_pid}" ] && { kill -0 "${tunnel_pid}" 2>/dev/null || return 1; }
  return 0
}

while alive; do
  sleep 1
done
wait -n "${provider_pid}" "${ecu_pid}" 2>/dev/null || true
echo "[zone] a child exited; taking the zone down" >&2
term
