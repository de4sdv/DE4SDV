#!/bin/bash
# The IVI guest's clock against the guest host's (entry ENTRY_GUEST_CLOCK; brief R9). The IVI clock free-runs, so
# the session sets it just before the window and records the offset that remains, with its bound.
#
#   ivi_clock.sh set <out_dir>              set the IVI clock from this host's, then measure; <out_dir>/clock.jsonl
#   ivi_clock.sh measure <out_dir> <label>  measure only (one more line in <out_dir>/clock.jsonl)
#
# A measurement is Cristian's method over adb: N reads of the guest clock, each bracketed by this host's clock; the
# read with the shortest round trip gives offset = guest - (host_before + host_after) / 2, bound = round trip / 2.
# The set is `toybox date -s @<epoch>` in one guest shell (sntp -s leaves this image's clock where it was).
# env: ADB, IVI_ADB (0.0.0.0:6522), CLOCK_READS (15), CLOCK_SET_AGAIN_S (0.02: a second set if the offset is larger)
set -uo pipefail
ACTION=${1:?set|measure}; OUT=${2:?out dir}; LABEL=${3:-$ACTION}
mkdir -p "$OUT"
: "${AOSP_TOP:=$HOME/aosp}"
ADB=${ADB:-${ANDROID_HOST_OUT:-$AOSP_TOP/out/host/linux-x86}/bin/adb}
IVI_ADB=${IVI_ADB:-0.0.0.0:6522}; N=${CLOCK_READS:-15}; AGAIN=${CLOCK_SET_AGAIN_S:-0.02}

measure() {   # measure <label>: prints one JSON line and appends it to clock.jsonl
  local i h1 g h2 best="" line
  for i in $(seq 1 "$N"); do
    h1=$(date +%s.%N); g=$("$ADB" -s "$IVI_ADB" shell date +%s.%N 2>/dev/null | tr -d '\r'); h2=$(date +%s.%N)
    [ -n "$g" ] || continue
    best=$(awk -v h1="$h1" -v g="$g" -v h2="$h2" -v best="$best" 'BEGIN {
      rtt = h2 - h1; split(best, b, " ");
      if (best == "" || rtt < b[1]) printf "%.6f %.6f %s %s %s", rtt, g - (h1 + h2) / 2, h1, g, h2; else print best }')
  done
  [ -n "$best" ] || { echo "no guest clock read on $IVI_ADB" >&2; return 1; }
  line=$(echo "$best" | awk -v l="$1" -v n="$N" '{ printf "{\"label\": \"%s\", \"reads\": %d, \"offset_s\": %s, \"bound_s\": %.6f, \"rtt_s\": %s, \"host_before\": %s, \"guest\": %s, \"host_after\": %s}", l, n, $2, $1 / 2, $1, $3, $4, $5 }')
  echo "$line" | tee -a "$OUT/clock.jsonl"
}
offset_of() { sed -E 's/.*"offset_s": (-?[0-9.]+).*/\1/'; }

case "$ACTION" in
  set)
    measure before_set > /dev/null || exit 1
    "$ADB" -s "$IVI_ADB" shell "toybox date -s @$(date +%s.%N) > /dev/null" || exit 1
    L=$(measure after_set) || exit 1
    if awk -v o="$(echo "$L" | offset_of)" -v a="$AGAIN" 'BEGIN { exit !(o > a || -o > a) }'; then
      # one more set that takes the measured offset off (the adb latency of the first set)
      O=$(echo "$L" | offset_of)
      "$ADB" -s "$IVI_ADB" shell "toybox date -s @$(awk -v t="$(date +%s.%N)" -v o="$O" 'BEGIN { printf "%.6f", t - o }') > /dev/null"
      measure after_second_set > /dev/null || exit 1
    fi
    ;;
  measure) measure "$LABEL" > /dev/null || exit 1 ;;
  *) echo "usage: ivi_clock.sh set|measure <out_dir> [label]" >&2; exit 2 ;;
esac
tail -1 "$OUT/clock.jsonl"
