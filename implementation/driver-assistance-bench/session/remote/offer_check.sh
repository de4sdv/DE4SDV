#!/bin/bash
# After the S-CORE host's someipd offers the warning service, before any window: the SD multicast route on the
# guest host, then the readiness of the warning path's guest legs (guest-prep-20261118 report, item 7: "only after the
# offer, check the broker's unit registration and the absence of someip_broker_agent errors for the service").
#
#   offer_check.sh route <out_dir>   sudo ip route replace 224.0.0.0/4 dev $BR (cvd-ebr); prints the route
#   offer_check.sh mark <out_dir>    each guest's clock now, on its own clock: the SDV Core guest's into
#                                    <out_dir>/logcat_since.txt, the IVI guest's into ivi_logcat_since.txt. Run before
#                                    the S-CORE side starts, so the unit check reads only the logs since that start
#   offer_check.sh unit <out_dir> [<mark_dir>]
#                                    waits up to UNIT_WAIT_S for the unit's readiness, from UNIT_SOURCE:
#                                    app (default): the IVI app's own link line, `DE4SDV_COLLISION_WARNING: ...
#                                      phase=link link=SUBSCRIBED`, in the IVI log since the IVI mark. A SUBSCRIBED
#                                      line since the mark passes. UNAVAILABLE never decides: the app logs it for
#                                      every failed initComms, subscribe or read and retries after 5 s, so the gate
#                                      counts those lines, names the last one's detail, and waits for SUBSCRIBED up
#                                      to its bound; WAITING waits.
#                                    core: a core logcat line naming the unit, matching UNIT_REGISTERED_RE and not
#                                      UNIT_NEGATION_RE (the bench's guess before the first p10-3; that session's core
#                                      log has no line naming the unit at all, so this source cannot pass there).
#                                    Either source fails on a broker error line naming the service or the unit in the
#                                    core log. With <mark_dir>, only the logs since its marks (`logcat -d -T <epoch>`);
#                                    without, the whole buffers since the guests booted. Always kept: unit_context.txt
#                                    (the core's REGISTER EVENT and SUBSCRIBE lines for the service id, the app's link
#                                    lines: both legs). On any FAIL, diag/ (below) before the exit
#   offer_check.sh neigh <out_dir>   flushes both guests' neighbour caches (ip neigh flush dev $GUEST_IF), so they
#                                    learn the S-CORE host's MAC for 192.168.98.1 over the VXLAN
#   offer_check.sh receipts <capture_dir> [<app_restart record>]
#                                    counts the receipt events of the window in the app's records of its capture
#                                    (app_record_*.jsonl): the lines whose "event" is "receipt" after the window's app
#                                    start. The record is appended (RecordWriter.java) and every app start writes
#                                    lifecycle, link and status lines, so a line count is never 0 (W1 of the re-check
#                                    at 437a833b). With the app_restart record, the window's start is the last run of
#                                    "lifecycle" "start" lines, and only if they carry its "pid <n>" line's pid;
#                                    without it, the last "lifecycle" "start" line. Prints "RECEIPTS <n>" and exits 0
#                                    either way (the session says it loudly when 0)
# The unit, the service id and the broker's tag come from the bench's interfaces/service_ids.json. Why the app's line
# (T6 of the p10-3 record of 2026-11-19): the SDV Core guest's broker logged no line naming the unit at its default
# level; the core's SOME/IP stack agent logged `REGISTER EVENT(...)` and `SUBSCRIBE(...)` for 4df1, and only the IVI
# app says that the unit reached the IVI. UNIT_REGISTERED_RE (default "regist"), UNIT_NEGATION_RE (default: a negation
# tied to the verb, NEG_DEFAULT below) and BROKER_ERROR_RE (default " E someip_broker_agent| E SomeIpBroker") stay
# settable per session (session/README.md, per-session settings), as does UNIT_SOURCE.
# diag/ on a FAIL: ivi_collision_warning_since_boot.txt (every DE4SDV_COLLISION_WARNING line of the IVI since boot),
# ivi_sdv_service_manager_broker_mesh.txt (the IVI's SdvServiceManager, SomeIpBroker and mesh lines since boot),
# core_sdv_service_manager_since_mark.txt, core_someip_service.txt (the core's someip lines naming the service id,
# since the mark), net_core.txt and net_ivi.txt (ip -br addr, ip route, ip rule and each netns's addresses).
# env: ADB, CORE_ADB (0.0.0.0:6521), IVI_ADB (0.0.0.0:6522), BR (cvd-ebr), GUEST_IF (eth1), UNIT_SOURCE (app),
#      UNIT_WAIT_S (120), POLL_S (5), ADB_TO_S (30, every adb call).
set -uo pipefail
export LC_ALL=C
ACTION=${1:?route|mark|neigh|unit|receipts}; OUT=${2:?out dir}; mkdir -p "$OUT"
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
IDS=$HERE/../../interfaces/service_ids.json
: "${AOSP_TOP:=$HOME/aosp}"
ADB=${ADB:-${ANDROID_HOST_OUT:-$AOSP_TOP/out/host/linux-x86}/bin/adb}
CORE_ADB=${CORE_ADB:-0.0.0.0:6521}; IVI_ADB=${IVI_ADB:-0.0.0.0:6522}
# --foreground: the bounded call stays in the step's process group, so a TERM to the step reaches it (plain timeout
# would move it into a group of its own, which outlives the step)
adbt() { timeout --foreground "${ADB_TO_S:-30}" "$ADB" "$@"; }
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
    # the IVI's own clock: its log is read since this mark, as the core's since the line above; the guests' clocks are
    # not in step (each free-runs), so no mark is ever moved from one guest to the other
    TI=$(adbt -s "$IVI_ADB" shell date +%s.%N 2>/dev/null | tr -d '\r')
    if [[ "$TI" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then printf '%.3f\n' "$TI" > "$OUT/ivi_logcat_since.txt"
    elif [ "${UNIT_SOURCE:-app}" = app ]; then echo "FAIL no clock read of the IVI guest ('$TI')"; exit 1
    else echo "NOTE no clock read of the IVI guest ('$TI'); UNIT_SOURCE=${UNIT_SOURCE} does not need it"; fi
    echo "LOGCAT_MARK $(cat "$OUT/logcat_since.txt") IVI $(cat "$OUT/ivi_logcat_since.txt" 2>/dev/null || echo none)"
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
    RREC=${3:-}; PID=""
    if [ -n "$RREC" ]; then
      PID=$(sed -n 's/^pid \([0-9][0-9]*\)\( .*\)\{0,1\}$/\1/p' "$RREC" 2>/dev/null | tail -1)
      if [ -z "$PID" ]; then
        echo "no pid of the window's app start in $RREC: no receipt event counted"; echo "RECEIPTS 0"; exit 0
      fi
    fi
    shopt -s nullglob; recs=("$OUT"/app_record_*.jsonl); shopt -u nullglob
    [ ${#recs[@]} -gt 0 ] || { echo "no app record in $OUT"; echo "RECEIPTS 0"; exit 0; }
    # the app's JSON keys (WarningRecord.json): every line opens with {"event":"<e>", a start is "lifecycle" with
    # "phase":"start","pid":<n> first; mawk has no {n} intervals, so index() and a plain match()
    n=$(awk -v pid="$PID" '
      FNR == 1 { tot += n; n = 0; inwin = 0; last = "" }
      index($0, "{\"event\":\"lifecycle\",") == 1 && match($0, /,"phase":"start","pid":[0-9]+/) {
        p = substr($0, RSTART + 23, RLENGTH - 23)
        if (pid == "") { n = 0; inwin = 1 }
        else if (p == pid) { if (last != p) n = 0; inwin = 1 }
        else { n = 0; inwin = 0 }
        last = p; next
      }
      inwin && index($0, "{\"event\":\"receipt\",") == 1 { n++ }
      END { print tot + n }' "${recs[@]}")
    echo "receipt events since the window's app start${PID:+ (pid $PID)}: ${n:-0}, in $(cat "${recs[@]}" | grep -c .) record line(s)"
    echo "RECEIPTS ${n:-0}"
    ;;
  unit)
    MARK=${3:-}; SINCE=""; ISINCE=""; SRC=${UNIT_SOURCE:-app}
    case "$SRC" in app|core) ;; *) echo "FAIL UNIT_SOURCE '$SRC' (app or core)"; exit 2 ;; esac
    if [ -n "$MARK" ]; then
      SINCE=$(cat "$MARK/logcat_since.txt" 2>/dev/null) || { echo "FAIL no logcat mark in $MARK"; exit 1; }
      if [ "$SRC" = app ]; then
        ISINCE=$(cat "$MARK/ivi_logcat_since.txt" 2>/dev/null) || { echo "FAIL no IVI logcat mark in $MARK"; exit 1; }
      fi
    fi
    read -r UNIT SERVICE < <(python3 -c 'import json, sys; d = json.load(open(sys.argv[1]))
print(d["icd"]["data_tunnel"]["service_unit"], d["icd"]["someip_warning_request"]["service_id"])' "$IDS") \
      || { echo "FAIL cannot read $IDS"; exit 1; }
    SVC=${SERVICE#0x}; RE=${UNIT_REGISTERED_RE:-regist}
    # the negation is tied to the verb (S8): "unregistered", "failed to register", "registration ... failed"; a word
    # like "timeout" or "errors=0" elsewhere in a registration line is no negation (a false fail costs a paid p10-3).
    # Still a guess of the broker's lines: changed per session through --remote-env UNIT_NEGATION_RE=...
    NEG_DEFAULT="(un|de|not |non-?)regist|(fail(s|ed)?|unable|cannot|can't|could not|couldn't) (to )?regist"
    NEG_DEFAULT="$NEG_DEFAULT|regist[a-z]*( [^ ]+){0,3} (failed|refused|denied|rejected|timed out)"
    NEG=${UNIT_NEGATION_RE:-$NEG_DEFAULT}
    ERR_RE=${BROKER_ERROR_RE:- E someip_broker_agent| E SomeIpBroker}
    APP_TAG="DE4SDV_COLLISION_WARNING:"; LINK_RE=" phase=link link=(SUBSCRIBED|UNAVAILABLE|WAITING)( |$)"
    if [ "$SRC" = app ]; then
      echo "unit $UNIT service $SERVICE; source app: waiting up to ${UNIT_WAIT_S:-120} s for the IVI app's" \
        "'phase=link link=SUBSCRIBED' line ($IVI_ADB, the IVI log since ${ISINCE:-boot}, the IVI's clock); its" \
        "link=UNAVAILABLE lines are counted, never decisive (the app retries them every 5 s); broker errors in the" \
        "core log ($CORE_ADB) since ${SINCE:-boot}"
    else
      echo "unit $UNIT service $SERVICE; source core: waiting up to ${UNIT_WAIT_S:-120} s for a line naming the unit" \
        "matching /$RE/ and not /$NEG/; the log since ${SINCE:-boot}"
    fi
    echo "${SINCE:-boot}" > "$OUT/logcat_since.txt"
    [ "$SRC" = app ] && echo "${ISINCE:-boot}" > "$OUT/ivi_logcat_since.txt"
    # both legs, kept on a pass and on a fail: the core's SOME/IP stack agent's REGISTER EVENT and SUBSCRIBE lines for
    # the service id (the S-CORE-to-core leg), the IVI app's link lines (the core-to-IVI leg)
    context() {
      { echo "# the SDV Core guest's REGISTER EVENT and SUBSCRIBE lines for service $SERVICE since ${SINCE:-boot}"
        grep -i -E "(REGISTER EVENT|SUBSCRIBE)\([0-9a-f]+\): \[$SVC\." "$OUT/core_logcat.txt" 2>/dev/null
        echo "# the IVI app's link lines since ${ISINCE:-boot}"
        cat "$OUT/app_link_lines.txt" 2>/dev/null
      } > "$OUT/unit_context.txt"
    }
    # on any FAIL, before the exit: what a reader needs to tell which leg broke (every adb call bounded by ADB_TO_S)
    diagnose() {
      local D=$OUT/diag g f
      DIAG_DONE=1; mkdir -p "$D"
      adbt -s "$IVI_ADB" logcat -d 2>/dev/null | tr -d '\r' > "$D/ivi_logcat_since_boot.txt"
      grep -F "$APP_TAG" "$D/ivi_logcat_since_boot.txt" > "$D/ivi_collision_warning_since_boot.txt"
      # never the app's own lines: its start line names the broker (publisher=...SomeIpBroker) (W6)
      grep -v -F "$APP_TAG" "$D/ivi_logcat_since_boot.txt" | grep -E "SdvServiceManager|SomeIpBroker|[Mm]esh" \
        > "$D/ivi_sdv_service_manager_broker_mesh.txt"
      [ -e "$OUT/core_logcat.txt" ] || adbt -s "$CORE_ADB" logcat -d 2>/dev/null | tr -d '\r' > "$OUT/core_logcat.txt"
      grep -F "SdvServiceManagerServer" "$OUT/core_logcat.txt" > "$D/core_sdv_service_manager_since_mark.txt"
      grep -i "someip" "$OUT/core_logcat.txt" | grep -i -F "$SVC" > "$D/core_someip_service.txt"
      for g in core ivi; do
        if [ "$g" = core ]; then f=$CORE_ADB; else f=$IVI_ADB; fi
        adbt -s "$f" shell 'ip -br addr; echo "# ip route"; ip route; echo "# ip rule"; ip rule;
          for n in $(ip netns list 2>/dev/null | cut -d" " -f1); do echo "# netns $n"; ip -n "$n" -br addr; done' \
          2>&1 | tr -d '\r' | sed "s|^|$f: |" > "$D/net_$g.txt"
      done
      context
      echo "DIAGNOSTICS $D:$(cd "$D" && for f in *.txt; do printf ' %s(%s)' "$f" "$(grep -c . "$f")"; done)"
    }
    DIAG_DONE=""
    fail_unit() { echo "FAIL $*"; [ -n "$DIAG_DONE" ] || diagnose; exit 1; }   # the diagnostics once (T_UNIT, W4)
    end=$(( $(date +%s) + ${UNIT_WAIT_S:-120} ))
    while :; do
      if [ -n "$SINCE" ]; then adbt -s "$CORE_ADB" logcat -d -T "$SINCE" 2>/dev/null
      else adbt -s "$CORE_ADB" logcat -d 2>/dev/null; fi | tr -d '\r' > "$OUT/core_logcat.txt"
      grep -i -E "$ERR_RE" "$OUT/core_logcat.txt" | grep -i -E "$UNIT|$SVC" > "$OUT/broker_errors.txt"
      if [ "$SRC" = app ]; then
        if [ -n "$ISINCE" ]; then adbt -s "$IVI_ADB" logcat -d -T "$ISINCE" 2>/dev/null
        else adbt -s "$IVI_ADB" logcat -d 2>/dev/null; fi | tr -d '\r' > "$OUT/ivi_logcat.txt"
        grep -F "$APP_TAG" "$OUT/ivi_logcat.txt" | grep -E "$LINK_RE" > "$OUT/app_link_lines.txt"
      else
        grep -F "$UNIT" "$OUT/core_logcat.txt" | grep -i -E "$RE" | grep -v -i -E "$NEG" > "$OUT/unit_lines.txt"
      fi
      context
      if [ -s "$OUT/broker_errors.txt" ]; then
        echo "FAIL broker errors for the service:"; head -5 "$OUT/broker_errors.txt"; diagnose; exit 1
      fi
      if [ "$SRC" = app ]; then
        # the last link line since the mark decides: SUBSCRIBED passes, a later WAITING or UNAVAILABLE says the link
        # dropped, so the gate waits on (W5). UNAVAILABLE never decides: the app logs it for every failed initComms,
        # subscribe or read and retries after RETRY_DELAY_MS (5 s)
        sub=$(tail -1 "$OUT/app_link_lines.txt" | grep -E " link=SUBSCRIBED( |$)")
        nun=$(grep -c -E " link=UNAVAILABLE( |$)" "$OUT/app_link_lines.txt")
        lun=$(grep -E " link=UNAVAILABLE( |$)" "$OUT/app_link_lines.txt" | tail -1); lun=${lun#* detail=}
        if [ -n "$sub" ]; then
          if [ "${nun:-0}" -gt 0 ]; then
            echo "the IVI app's link was UNAVAILABLE $nun time(s) since the mark (the app retries every 5 s); the last: $lun"
          fi
          echo "$sub"; echo "UNIT_SUBSCRIBED $UNIT source=app"; exit 0
        fi
      elif [ -s "$OUT/unit_lines.txt" ]; then
        head -3 "$OUT/unit_lines.txt"; echo "UNIT_REGISTERED $UNIT source=core"; exit 0
      fi
      if [ "$(date +%s)" -ge "$end" ]; then
        if [ "$SRC" = app ]; then
          last=$(tail -1 "$OUT/app_link_lines.txt"); last=${last#* link=}
          # with none since the mark, the last one before it (from the IVI log since boot): a naming problem is
          # logged once, at the app's start, before the mark (W3)
          before=""
          if [ -z "$last" ]; then
            diagnose
            before=$(grep -E "$LINK_RE" "$OUT/diag/ivi_collision_warning_since_boot.txt" | tail -1)
            before="; last link line before the mark: ${before:-none}"
          fi
          fail_unit "no 'phase=link link=SUBSCRIBED' line of the IVI app for $UNIT within ${UNIT_WAIT_S:-120} s" \
            "(last link line: ${last:-none since the mark}$before; UNAVAILABLE lines since the mark: ${nun:-0}${lun:+; the last: $lun})"
        fi
        fail_unit "no registration of $UNIT within ${UNIT_WAIT_S:-120} s (source core)"
      fi
      sleep "${POLL_S:-5}"
    done
    ;;
  *) echo "usage: offer_check.sh route|mark|neigh <out_dir> | unit <out_dir> [<mark_dir>] | receipts <capture_dir>" >&2
     exit 2 ;;
esac
