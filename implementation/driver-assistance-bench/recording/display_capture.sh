#!/bin/bash
# Display capture on the IVI guest (brief row B15), run on the guest host. It records what the driver's display
# shows during a window, with the guest clock read around every screen recording, so that the video can later be
# placed on the guest clock.
#
#   display_capture.sh start <out_dir> [--max-s N]   runs until `stop` or N s (default 900); run it detached
#   display_capture.sh stop  <out_dir> [--wait-s N]  asks the running capture to end and waits for capture.done
#
# What one capture keeps in <out_dir> (the raw files are never changed afterwards):
#   seg_<k>.mp4             adb screenrecord of the display, in segments of at most SEGMENT_S (screenrecord's limit
#                           is 180 s); each segment's launch is bracketed by two reads of the guest clock in the same
#                           guest shell: segments.jsonl {segment, file, display_id, guest_before_s, guest_after_s,
#                           host_before_s, host_after_s, guest_end_s, end}
#   screencap_<when>_<id>.png  one still per display (screencap -d <id>), at the start and at the end
#   clock.jsonl             the guest clock's offset to this host's, with its bound, at the start and at the end
#                           (session/remote/ivi_clock.sh measure)
#   audio_flinger_<when>.txt  dumpsys media.audio_flinger at the start and the end: the sound route (brief R8)
#   logcat.txt              the guest's log of the window, epoch time stamps (the app's receipt, frame and sound
#                           records, and any player start)
#   app_record_<name>       the app's own timestamp record, if APP_RECORD_PATHS names files that exist (@user@ in a
#                           path is replaced by the IVI's current user)
#   capture.json            the list of the files with their sha256, the display ids, and how the capture ended
#
# The sound is not recorded as audio: no capture route from the Cuttlefish guest's audio to the host is known yet
# (brief R8). The sound start is taken from the app's own timestamp record; without that record it is unmeasured.
# env: ADB, IVI_ADB (0.0.0.0:6522), DISPLAY_ID (default: the first id dumpsys lists), SEGMENT_S (170),
#      BIT_RATE (8000000), APP_RECORD_PATHS (guest paths, space separated), POLL_S (1)
set -uo pipefail
export LC_ALL=C
ACTION=${1:?start|stop}; OUT=${2:?out dir}; shift 2
MAX_S=900; WAIT_S=60
while [ $# -gt 0 ]; do
  case "$1" in --max-s) MAX_S=$2; shift 2 ;; --wait-s) WAIT_S=$2; shift 2 ;; *) echo "unknown $1" >&2; exit 2 ;; esac
done
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
CLOCK=${CLOCK_SCRIPT:-$HERE/../session/remote/ivi_clock.sh}
: "${AOSP_TOP:=$HOME/aosp}"
ADB=${ADB:-${ANDROID_HOST_OUT:-$AOSP_TOP/out/host/linux-x86}/bin/adb}
export ADB
IVI_ADB=${IVI_ADB:-0.0.0.0:6522}; export IVI_ADB
SEGMENT_S=${SEGMENT_S:-170}; BIT_RATE=${BIT_RATE:-8000000}; POLL_S=${POLL_S:-1}
GDIR=/data/local/tmp/da_capture
a() { "$ADB" -s "$IVI_ADB" "$@"; }
now() { date +%s.%N; }

if [ "$ACTION" = stop ]; then
  [ -d "$OUT" ] || { echo "no capture in $OUT"; exit 1; }
  : > "$OUT/STOP"
  end=$(( $(date +%s) + WAIT_S ))
  while [ ! -e "$OUT/capture.done" ] && [ "$(date +%s)" -lt "$end" ]; do sleep "$POLL_S"; done
  [ -e "$OUT/capture.done" ] || { echo "capture did not end within $WAIT_S s"; exit 1; }
  cat "$OUT/capture.done"
  exit 0
fi
[ "$ACTION" = start ] || { echo "usage: display_capture.sh start|stop <out_dir>" >&2; exit 2; }
[ -e "$OUT/capture.json" ] && { echo "a capture already exists in $OUT"; exit 2; }
mkdir -p "$OUT"; rm -f "$OUT/STOP"

displays() { a shell dumpsys SurfaceFlinger --display-id 2>/dev/null | tr -d '\r' | sed -n 's/^Display \([0-9]*\).*/\1/p'; }
stills() {   # stills <when>
  local id
  for id in $IDS; do a exec-out screencap -d "$id" -p > "$OUT/screencap_$1_$id.png" 2>/dev/null || rm -f "$OUT/screencap_$1_$id.png"; done
}
IDS=$(displays | tr '\n' ' ')
DID=${DISPLAY_ID:-$(echo "$IDS" | awk '{print $1}')}
[ -n "$DID" ] || { echo "no display id from dumpsys SurfaceFlinger --display-id"; exit 1; }
echo "displays: $IDS; recording display $DID"
bash "$CLOCK" measure "$OUT" capture_start > /dev/null || echo "WARNING: no clock measurement at the start"
stills start
a shell dumpsys media.audio_flinger > "$OUT/audio_flinger_start.txt" 2>&1
LOGCAT_FROM=$(a shell date +%s.%N | tr -d '\r')
a shell "mkdir -p $GDIR" > /dev/null

END=stop; K=0; T_START=$(date +%s)   # --max-s counts from the first recording
while :; do
  K=$((K + 1)); left=$(( MAX_S - ($(date +%s) - T_START) ))
  [ "$left" -le 0 ] && { END=max-s; K=$((K - 1)); break; }
  lim=$(( left < SEGMENT_S ? left : SEGMENT_S ))
  hb=$(now)
  # one guest shell: clock, the background recording, clock (its output goes to /dev/null, so the call returns at once)
  r=$(a shell "date +%s.%N; screenrecord --time-limit $lim --bit-rate $BIT_RATE --display-id $DID $GDIR/seg_$K.mp4 > /dev/null 2>&1 & echo pid=\$!; date +%s.%N" | tr -d '\r')
  ha=$(now)
  gb=$(echo "$r" | sed -n 1p); pid=$(echo "$r" | sed -n 's/^pid=//p'); ga=$(echo "$r" | sed -n 3p)
  [ -n "$pid" ] || { echo "screenrecord did not start: $r"; END=error; break; }
  seg_end=time-limit
  while a shell "kill -0 $pid 2>/dev/null && echo alive" 2>/dev/null | grep -q alive; do
    if [ -e "$OUT/STOP" ] && [ "$seg_end" != stop ]; then a shell "kill -INT $pid"; seg_end=stop; fi   # SIGINT: the file is finished
    sleep "$POLL_S"
  done
  ge=$(a shell date +%s.%N | tr -d '\r')
  printf '{"segment": %d, "file": "seg_%d.mp4", "display_id": "%s", "guest_before_s": %s, "guest_after_s": %s, "host_before_s": %s, "host_after_s": %s, "guest_end_s": %s, "end": "%s"}\n' \
    "$K" "$K" "$DID" "$gb" "$ga" "$hb" "$ha" "${ge:-null}" "$seg_end" >> "$OUT/segments.jsonl"
  a pull "$GDIR/seg_$K.mp4" "$OUT/seg_$K.mp4" > /dev/null 2>&1 || echo "WARNING: pull of seg_$K.mp4 failed"
  [ "$seg_end" = stop ] && break
  [ -e "$OUT/STOP" ] && break
done

stills end
a shell dumpsys media.audio_flinger > "$OUT/audio_flinger_end.txt" 2>&1
a logcat -d -v epoch -T "$LOGCAT_FROM" > "$OUT/logcat.txt" 2>&1 || a logcat -d -v epoch > "$OUT/logcat.txt" 2>&1
# @user@ in a path: the IVI's current user (an AAOS IVI may run its apps as a secondary user; the app's files are
# under /data/user/<user>/<package>/), as ivi-warning-app/scripts/stage_ivi_warning_app.sh pull reads it
GUSER=$(a shell am get-current-user 2>/dev/null | tr -d '\r'); case "$GUSER" in ''|*[!0-9]*) GUSER=0 ;; esac
for p in ${APP_RECORD_PATHS:-}; do
  p=${p//@user@/$GUSER}
  a pull "$p" "$OUT/app_record_$(basename "$p")" > /dev/null 2>&1 || echo "app record $p: not on the guest" >> "$OUT/app_record_missing.txt"
done
bash "$CLOCK" measure "$OUT" capture_end > /dev/null || echo "WARNING: no clock measurement at the end"
a shell "rm -rf $GDIR" > /dev/null 2>&1
OUT="$OUT" END="$END" IDS="$IDS" DID="$DID" python3 - <<'PY'
import hashlib, json, os
o = os.environ["OUT"]
files = sorted(f for f in os.listdir(o) if f not in ("capture.json", "capture.done", "STOP"))
sha = {f: hashlib.sha256(open(os.path.join(o, f), "rb").read()).hexdigest() for f in files}
p = os.path.join(o, "segments.jsonl")
segs = [json.loads(l) for l in open(p)] if os.path.exists(p) else []
for s in segs:
    s["sha256"] = sha.get(s["file"])
p = os.path.join(o, "clock.jsonl")
clock = [json.loads(l) for l in open(p)] if os.path.exists(p) else []
json.dump({"display_ids": os.environ["IDS"].split(), "recorded_display_id": os.environ["DID"], "end": os.environ["END"],
           "segments": segs, "clock": clock, "sha256": sha,
           "sound": "no audio capture; the sound start comes from the app's own record, if present"},
          open(os.path.join(o, "capture.json"), "w"), indent=1)
PY
echo "capture ended ($END), $K segment(s)" | tee "$OUT/capture.done"
[ "$END" != error ]
