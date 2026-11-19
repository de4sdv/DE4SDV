#!/bin/bash
# After the S-CORE host's someipd offers the warning service, before any window: the SD multicast route on the
# guest host, then the SDV Core broker's registration of the unit (guest-prep-20261118 report, item 7: "only after
# the offer, check the broker's unit registration and the absence of someip_broker_agent errors for the service").
#
#   offer_check.sh route <out_dir>   sudo ip route replace 224.0.0.0/4 dev $BR (cvd-ebr); prints the route
#   offer_check.sh mark <out_dir>    the SDV Core guest's clock now, into <out_dir>/logcat_since.txt: run before the
#                                    S-CORE side starts, so the unit check reads only the log since that start
#   offer_check.sh unit <out_dir> [<mark_dir>]
#                                    waits up to UNIT_WAIT_S for a core logcat line naming the unit, matching
#                                    UNIT_REGISTERED_RE and not UNIT_NEGATION_RE; fails on a broker error line naming
#                                    the service or the unit. With <mark_dir>, only the log since its mark
#                                    (`logcat -d -T <epoch>`); without, the whole buffer since the guest booted
#   offer_check.sh neigh <out_dir>   flushes both guests' neighbour caches (ip neigh flush dev $GUEST_IF), so they
#                                    learn the S-CORE host's MAC for 192.168.98.1 over the VXLAN
#   offer_check.sh receipts <capture_dir>
#                                    counts the lines of the app's records in a window's capture; prints
#                                    "RECEIPTS <n>" and exits 0 either way (the session says it loudly when 0)
# The unit, the service id and the broker's tag come from the bench's interfaces/service_ids.json. The texts of the
# broker's lines are not known from a run yet: UNIT_REGISTERED_RE (default "regist"), UNIT_NEGATION_RE (default: a
# negation tied to the verb, NEG_DEFAULT below: "unregistered", "failed to register", "registration ... failed")
# and BROKER_ERROR_RE (default
# " E someip_broker_agent| E SomeIpBroker") are the bench's guess, and the matched lines are kept as evidence. The
# session passes changed values per session (session/README.md, per-session settings).
# env: ADB, CORE_ADB (0.0.0.0:6521), IVI_ADB (0.0.0.0:6522), BR (cvd-ebr), GUEST_IF (eth1), UNIT_WAIT_S (120),
#      POLL_S (5), ADB_TO_S (30, every adb call).
set -uo pipefail
export LC_ALL=C
ACTION=${1:?route|mark|neigh|unit|receipts}; OUT=${2:?out dir}; mkdir -p "$OUT"
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
IDS=$HERE/../../interfaces/service_ids.json
: "${AOSP_TOP:=$HOME/aosp}"
ADB=${ADB:-${ANDROID_HOST_OUT:-$AOSP_TOP/out/host/linux-x86}/bin/adb}
CORE_ADB=${CORE_ADB:-0.0.0.0:6521}; IVI_ADB=${IVI_ADB:-0.0.0.0:6522}
adbt() { timeout "${ADB_TO_S:-30}" "$ADB" "$@"; }
case "$ACTION" in
  route)
    BR=${BR:-cvd-ebr}
    sudo ip route replace 224.0.0.0/4 dev "$BR" || { echo "FAIL multicast route on $BR"; exit 1; }
    ip route get 224.0.0.251 2>/dev/null | head -1 | tee "$OUT/mcast_route.txt"
    grep -q "dev $BR" "$OUT/mcast_route.txt" || { echo "FAIL 224.0.0.0/4 does not leave by $BR"; exit 1; }
    echo "MCAST_ROUTE_OK $BR"
    ;;
  mark)
    T=$(adbt -s "$CORE_ADB" shell date +%s.%N 2>/dev/null | tr -d '\r')
    [[ "$T" =~ ^[0-9]+(\.[0-9]+)?$ ]] || { echo "FAIL no clock read of the SDV Core guest ('$T')"; exit 1; }
    printf '%.3f\n' "$T" > "$OUT/logcat_since.txt"
    echo "LOGCAT_MARK $(cat "$OUT/logcat_since.txt")"
    ;;
  neigh)
    GUEST_IF=${GUEST_IF:-eth1}
    for g in "$CORE_ADB" "$IVI_ADB"; do
      adbt -s "$g" root > /dev/null 2>&1
      adbt -s "$g" shell ip neigh flush dev "$GUEST_IF" || { echo "FAIL ip neigh flush dev $GUEST_IF on $g"; exit 1; }
      adbt -s "$g" shell ip neigh show dev "$GUEST_IF" 2>&1 | sed "s|^|$g: |" | tee -a "$OUT/neigh_after_flush.txt"
    done
    echo "NEIGH_FLUSHED $GUEST_IF"
    ;;
  receipts)
    n=$(cat "$OUT"/app_record_*.jsonl 2>/dev/null | grep -c . || true)
    echo "RECEIPTS ${n:-0}"
    ;;
  unit)
    MARK=${3:-}; SINCE=""
    if [ -n "$MARK" ]; then
      SINCE=$(cat "$MARK/logcat_since.txt" 2>/dev/null) || { echo "FAIL no logcat mark in $MARK"; exit 1; }
    fi
    read -r UNIT SERVICE < <(python3 -c 'import json, sys; d = json.load(open(sys.argv[1]))
print(d["icd"]["data_tunnel"]["service_unit"], d["icd"]["someip_warning_request"]["service_id"])' "$IDS") \
      || { echo "FAIL cannot read $IDS"; exit 1; }
    SVC=${SERVICE#0x}; RE=${UNIT_REGISTERED_RE:-regist}
    # the negation is tied to the verb (S8): "unregistered", "failed to register", "registration ... failed"; a word
    # like "timeout" or "errors=0" elsewhere in a registration line is no negation (a false fail costs a paid P10-3).
    # Still a guess of the broker's lines: changed per session through --remote-env UNIT_NEGATION_RE=...
    NEG_DEFAULT="(un|de|not |non-?)regist|(fail(s|ed)?|unable|cannot|can't|could not|couldn't) (to )?regist"
    NEG_DEFAULT="$NEG_DEFAULT|regist[a-z]*( [^ ]+){0,3} (failed|refused|denied|rejected|timed out)"
    NEG=${UNIT_NEGATION_RE:-$NEG_DEFAULT}
    ERR_RE=${BROKER_ERROR_RE:- E someip_broker_agent| E SomeIpBroker}
    echo "unit $UNIT service $SERVICE; waiting up to ${UNIT_WAIT_S:-120} s for a line naming the unit matching /$RE/" \
      "and not /$NEG/; the log since ${SINCE:-boot}"
    echo "${SINCE:-boot}" > "$OUT/logcat_since.txt"
    end=$(( $(date +%s) + ${UNIT_WAIT_S:-120} ))
    while :; do
      if [ -n "$SINCE" ]; then adbt -s "$CORE_ADB" logcat -d -T "$SINCE" 2>/dev/null
      else adbt -s "$CORE_ADB" logcat -d 2>/dev/null; fi | tr -d '\r' > "$OUT/core_logcat.txt"
      grep -i -E "$ERR_RE" "$OUT/core_logcat.txt" | grep -i -E "$UNIT|$SVC" > "$OUT/broker_errors.txt"
      grep -F "$UNIT" "$OUT/core_logcat.txt" | grep -i -E "$RE" | grep -v -i -E "$NEG" > "$OUT/unit_lines.txt"
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
  *) echo "usage: offer_check.sh route|mark|neigh <out_dir> | unit <out_dir> [<mark_dir>] | receipts <capture_dir>" >&2
     exit 2 ;;
esac
