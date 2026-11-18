#!/bin/bash
# After the S-CORE host's someipd offers the warning service, before any window: the SD multicast route on the
# guest host, then the SDV Core broker's registration of the unit (guest-prep-20261118 report, item 7: "only after
# the offer, check the broker's unit registration and the absence of someip_broker_agent errors for the service").
#
#   offer_check.sh route <out_dir>   sudo ip route replace 224.0.0.0/4 dev $BR (cvd-ebr); prints the route
#   offer_check.sh unit <out_dir>    waits up to UNIT_WAIT_S for a core logcat line naming the unit and matching
#                                    UNIT_REGISTERED_RE; fails on a broker error line naming the service or the unit
# The unit, the service id and the broker's tag come from the bench's interfaces/service_ids.json. The texts of the
# broker's lines are not known from a run yet: UNIT_REGISTERED_RE (default "regist") and BROKER_ERROR_RE (default
# " E someip_broker_agent| E SomeIpBroker") are the bench's guess, and the matched lines are kept as evidence.
# env: ADB, CORE_ADB (0.0.0.0:6521), BR (cvd-ebr), UNIT_WAIT_S (120), POLL_S (5).
set -uo pipefail
ACTION=${1:?route|unit}; OUT=${2:?out dir}; mkdir -p "$OUT"
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
IDS=$HERE/../../interfaces/service_ids.json
: "${AOSP_TOP:=$HOME/aosp}"
ADB=${ADB:-${ANDROID_HOST_OUT:-$AOSP_TOP/out/host/linux-x86}/bin/adb}
CORE_ADB=${CORE_ADB:-0.0.0.0:6521}
case "$ACTION" in
  route)
    BR=${BR:-cvd-ebr}
    sudo ip route replace 224.0.0.0/4 dev "$BR" || { echo "FAIL multicast route on $BR"; exit 1; }
    ip route get 224.0.0.251 2>/dev/null | head -1 | tee "$OUT/mcast_route.txt"
    grep -q "dev $BR" "$OUT/mcast_route.txt" || { echo "FAIL 224.0.0.0/4 does not leave by $BR"; exit 1; }
    echo "MCAST_ROUTE_OK $BR"
    ;;
  unit)
    read -r UNIT SERVICE < <(python3 -c 'import json, sys; d = json.load(open(sys.argv[1]))
print(d["icd"]["data_tunnel"]["service_unit"], d["icd"]["someip_warning_request"]["service_id"])' "$IDS") \
      || { echo "FAIL cannot read $IDS"; exit 1; }
    SVC=${SERVICE#0x}; RE=${UNIT_REGISTERED_RE:-regist}
    ERR_RE=${BROKER_ERROR_RE:- E someip_broker_agent| E SomeIpBroker}
    echo "unit $UNIT service $SERVICE; waiting up to ${UNIT_WAIT_S:-120} s for a line naming the unit matching /$RE/"
    end=$(( $(date +%s) + ${UNIT_WAIT_S:-120} ))
    while :; do
      "$ADB" -s "$CORE_ADB" logcat -d 2>/dev/null | tr -d '\r' > "$OUT/core_logcat.txt"
      grep -i -E "$ERR_RE" "$OUT/core_logcat.txt" | grep -i -E "$UNIT|$SVC" > "$OUT/broker_errors.txt"
      grep -F "$UNIT" "$OUT/core_logcat.txt" | grep -i -E "$RE" > "$OUT/unit_lines.txt"
      if [ -s "$OUT/broker_errors.txt" ]; then
        echo "FAIL broker errors for the service:"; head -5 "$OUT/broker_errors.txt"; exit 1
      fi
      if [ -s "$OUT/unit_lines.txt" ]; then
        head -3 "$OUT/unit_lines.txt"; echo "UNIT_REGISTERED $UNIT"; exit 0
      fi
      [ "$(date +%s)" -ge "$end" ] && { echo "FAIL no registration of $UNIT within ${UNIT_WAIT_S:-120} s"; exit 1; }
      sleep "${POLL_S:-5}"
    done
    ;;
  *) echo "usage: offer_check.sh route|unit <out_dir>" >&2; exit 2 ;;
esac
