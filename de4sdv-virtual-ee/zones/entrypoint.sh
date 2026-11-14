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
: "${CAN_TUNNEL_TIMEOUT:=1000}"   # cannelloni buffer timeout, microseconds

if ! ip link show "${ZONE_CHANNEL}" >/dev/null 2>&1; then
  ip link add dev "${ZONE_CHANNEL}" type vcan
fi
ip link set "${ZONE_CHANNEL}" up
echo "[zone] ${ZONE_CHANNEL} up ($(ip -br link show "${ZONE_CHANNEL}"))"

# Optional: carry this zone's bus across the slice to the central gateway.
# Without it the zone is a closed segment — which is exactly scope A.
tunnel_pid=""
if [ -n "${CAN_TUNNEL_REMOTE}" ]; then
  : "${CAN_TUNNEL_RPORT:?CAN_TUNNEL_RPORT is required with CAN_TUNNEL_REMOTE}"
  : "${CAN_TUNNEL_LPORT:?CAN_TUNNEL_LPORT is required with CAN_TUNNEL_REMOTE}"
  cannelloni -I "${ZONE_CHANNEL}" -R "${CAN_TUNNEL_REMOTE}" -r "${CAN_TUNNEL_RPORT}" -l "${CAN_TUNNEL_LPORT}" -t "${CAN_TUNNEL_TIMEOUT}" \
    2>&1 | sed -u 's/^/[tunnel] /' &
  tunnel_pid=$!
  echo "[zone] bus tunnel to ${CAN_TUNNEL_REMOTE}:${CAN_TUNNEL_RPORT} (listen ${CAN_TUNNEL_LPORT})"
fi

sed -e "s|@@ZONE_DBC@@|${ZONE_DBC}|" \
    -e "s|@@ZONE_CHANNEL@@|${ZONE_CHANNEL}|" \
    -e "s|@@ZONE_MAPPING@@|${ZONE_MAPPING}|" \
    -e "s|@@KUKSA_ADDRESS@@|${KUKSA_ADDRESS}|" \
    /opt/zone/dbc_feeder.ini > /tmp/dbc_feeder.ini

# The ini keys alone did not enable val2dbc in 0.5.1; the flags are explicit.
python /opt/provider/dbcfeeder.py \
      --config /tmp/dbc_feeder.ini \
      --dbc-default /opt/zone/dbc/dbc_default_values.json \
      --dbc2val --val2dbc \
      2>&1 | sed -u 's/^/[provider] /' &
provider_pid=$!

python /opt/zone/zone_ecu.py \
      --ecu "${ZONE_ECU}" \
      --dbc "${ZONE_DBC}" \
      --channel "${ZONE_CHANNEL}" \
      2>&1 | sed -u 's/^/[ecu] /' &

ecu_pid=$!

term() {
  kill -TERM "${provider_pid}" "${ecu_pid}" 2>/dev/null || true
  [ -n "${tunnel_pid}" ] && kill -TERM "${tunnel_pid}" 2>/dev/null || true
  wait 2>/dev/null || true
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
