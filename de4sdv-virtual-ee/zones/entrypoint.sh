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
: "${KUKSA_ADDRESS:=grpc://127.0.0.1:55555}"

if ! ip link show "${ZONE_CHANNEL}" >/dev/null 2>&1; then
  ip link add dev "${ZONE_CHANNEL}" type vcan
fi
ip link set "${ZONE_CHANNEL}" up
echo "[zone] ${ZONE_CHANNEL} up ($(ip -br link show "${ZONE_CHANNEL}"))"

sed -e "s|@@ZONE_DBC@@|${ZONE_DBC}|" \
    -e "s|@@ZONE_CHANNEL@@|${ZONE_CHANNEL}|" \
    -e "s|@@KUKSA_ADDRESS@@|${KUKSA_ADDRESS}|" \
    /opt/zone/dbc_feeder.ini > /tmp/dbc_feeder.ini

python /opt/provider/dbcfeeder.py \
      --config /tmp/dbc_feeder.ini \
      --dbc_default /opt/zone/dbc/dbc_default_values.json \
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
  wait 2>/dev/null || true
  exit 0
}
trap term INT TERM

# Exit as soon as either child does, and report which.
while kill -0 "${provider_pid}" 2>/dev/null && kill -0 "${ecu_pid}" 2>/dev/null; do
  sleep 1
done
wait -n "${provider_pid}" "${ecu_pid}" 2>/dev/null || true
echo "[zone] a child exited; taking the zone down" >&2
term
