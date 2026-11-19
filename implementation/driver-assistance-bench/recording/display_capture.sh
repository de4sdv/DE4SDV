#!/bin/bash
# Display capture on the IVI guest (brief row B15), run on the guest host. It records what the driver's display
# shows during a window, with the guest clock read around every screen recording, so that the video can later be
# placed on the guest clock.
#
#   display_capture.sh start <out_dir> [--max-s N]   runs until `stop` or N s (default 900); run it detached
#   display_capture.sh stop  <out_dir> [--wait-s N] [--wait-cap-s N]
#                                                     asks the running capture to end and waits for capture.done: N s
#                                                     (default 60) for the capture's tail, from the stop or from the
#                                                     last progress of the pulls (a pull that ended, or a local .part
#                                                     file that grew), plus the bytes still to pull at PULL_BPS; never
#                                                     more than --wait-cap-s (default 95) from the stop. 95 s fit the
#                                                     session's T_CAPTURE_END of 180 s: rstep's start SSH call (60 s at
#                                                     most) + 95 + 2 (the stop's own last poll and exit) + one status
#                                                     poll (POLL_S, 20 s) = 177 s
#
# What one capture keeps in <out_dir> (the raw files are never changed afterwards):
#   seg_<k>.mp4             adb screenrecord of the display, in segments of at most SEGMENT_S (screenrecord's limit
#                           is 180 s); each segment's launch is bracketed by two reads of the guest clock in the same
#                           guest shell: segments.jsonl {segment, file, display_id, guest_before_s, guest_after_s,
#                           host_before_s, host_after_s, guest_end_s, end}. guest_end_s is a guest clock read after
#                           the recording was seen ended: the next segment's first read, or a read of its own for the
#                           last one. end: time-limit; stop (the SIGINT reached the live recording); ended-early (the
#                           guest saw it end more than EARLY_S before its limit with no stop asked; the 2nd such end
#                           ends the capture with END=error); no-answer (ALIVE_UNKNOWN_S of polls without the guest's
#                           answer: END=error, the recording is sent SIGINT, and its file is pulled only if the guest
#                           then reports it ended). guest_seen_ended_s: the guest clock in the poll answer that saw it
#                           end; guest_data_free_kb: df -k /data, read in the launch's guest shell
#   pulls.jsonl             one line per segment pull: bytes on the guest, the host times, adb's rc, pulled or not,
#                           the sha256. A segment is pulled in the background while the next one records (at most
#                           MAX_PULLS at a time, the others wait their turn), so the pull is not part of the
#                           unrecorded span at a boundary. A pull writes seg_<k>.mp4.part and renames it only once it
#                           has the guest's size; the guest file is then removed. A failed pull keeps the guest file
#                           (named in capture.json) and its part as seg_<k>.mp4.partial
#   screencap_<when>_<id>.png  one still per display (screencap -d <id>), at the start and at the end
#   clock.jsonl             the guest clock's offset to this host's, with its bound, at the start and at the end
#                           (session/remote/ivi_clock.sh measure)
#   audio_flinger_<when>.txt  dumpsys media.audio_flinger at the start and the end: the sound route (brief R8)
#   logcat.txt              the guest's log of the window, epoch time stamps (the app's receipt, frame and sound
#                           records, and any player start)
#   app_record_<name>       the app's own timestamp record, if APP_RECORD_PATHS names files that exist (@user@ in a
#                           path is replaced by the IVI's current user)
#   capture.json            the list of the files with their sha256, the display ids, how the capture ended, and per
#                           boundary the unrecorded span's lower bound on the guest clock (boundaries;
#                           recording/README.md). No frame times: they are read by compose_side_by_side.py on the
#                           composing host (not_filled_here), so nothing in the stop scales with the recording
#
# The sound is not recorded as audio: no capture route from the Cuttlefish guest's audio to the host is known yet
# (brief R8). The sound start is taken from the app's own timestamp record; without that record it is unmeasured.
# env: ADB, IVI_ADB (0.0.0.0:6522), DISPLAY_ID (default: the first id dumpsys lists), SEGMENT_S (170),
#      BIT_RATE (8000000), APP_RECORD_PATHS (guest paths, space separated), POLL_S (1), FAST_POLL_S (0.2: the poll
#      within NEAR_END_S (2) of a segment's time limit), PULL_BPS (10000000: the pull rate the stop's wait assumes),
#      PULL_TIMEOUT_S (600: one segment's pull), WAIT_CAP_S (95), ADB_TIMEOUT_S (10: every other adb call),
#      POLL_TIMEOUT_S (5: one alive poll), ALIVE_UNKNOWN_S (15), EARLY_S (2), MAX_PULLS (2), CLOCK_TIMEOUT_S (30)
set -uo pipefail
export LC_ALL=C
ACTION=${1:?start|stop}; OUT=${2:?out dir}; shift 2
MAX_S=900; WAIT_S=60; WAIT_CAP_S=${WAIT_CAP_S:-95}
while [ $# -gt 0 ]; do
  case "$1" in
    --max-s) MAX_S=$2; shift 2 ;; --wait-s) WAIT_S=$2; shift 2 ;; --wait-cap-s) WAIT_CAP_S=$2; shift 2 ;;
    *) echo "unknown $1" >&2; exit 2 ;;
  esac
done
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
CLOCK=${CLOCK_SCRIPT:-$HERE/../session/remote/ivi_clock.sh}
: "${AOSP_TOP:=$HOME/aosp}"
ADB=${ADB:-${ANDROID_HOST_OUT:-$AOSP_TOP/out/host/linux-x86}/bin/adb}
export ADB
IVI_ADB=${IVI_ADB:-0.0.0.0:6522}; export IVI_ADB
SEGMENT_S=${SEGMENT_S:-170}; BIT_RATE=${BIT_RATE:-8000000}; POLL_S=${POLL_S:-1}
FAST_POLL_S=${FAST_POLL_S:-0.2}; NEAR_END_S=${NEAR_END_S:-2}; PULL_BPS=${PULL_BPS:-10000000}
PULL_TIMEOUT_S=${PULL_TIMEOUT_S:-600}; ADB_TIMEOUT_S=${ADB_TIMEOUT_S:-10}; POLL_TIMEOUT_S=${POLL_TIMEOUT_S:-5}
ALIVE_UNKNOWN_S=${ALIVE_UNKNOWN_S:-15}; EARLY_S=${EARLY_S:-2}; EARLY_MAX=2; MAX_PULLS=${MAX_PULLS:-2}
CLOCK_TIMEOUT_S=${CLOCK_TIMEOUT_S:-30}
GDIR=/data/local/tmp/da_capture
# every adb call has a bound (--foreground: it stays in the step's process group, so the step's TERM reaches it)
a() { timeout --foreground "$ADB_TIMEOUT_S" "$ADB" -s "$IVI_ADB" "$@"; }
ab() { local t=$1; shift; timeout --foreground "$t" "$ADB" -s "$IVI_ADB" "$@"; }
now() { date +%s.%N; }

if [ "$ACTION" = stop ]; then
  [ -d "$OUT" ] || { echo "no capture in $OUT"; exit 1; }
  : > "$OUT/STOP"
  # seg_<k>.pending holds the bytes still to pull of segment k (a bound while it records, the guest's size once it
  # ended). The wait: WAIT_S for the tail, from the stop or from the last progress (the pending set changed, or a
  # pull's local .part grew), plus the pending bytes at PULL_BPS; at most WAIT_CAP_S from the stop (the session's
  # step bound is T_CAPTURE_END)
  t0=$(date +%s); since=$t0; last=-; pend=0
  while [ ! -e "$OUT/capture.done" ]; do
    set_now=$(cd "$OUT" && { echo seg_*.pending; stat -c '%n %s' seg_*.mp4.part 2>/dev/null; } | tr '\n' ' ')
    [ "$set_now" != "$last" ] && { since=$(date +%s); last=$set_now; }
    pend=$(cat "$OUT"/seg_*.pending 2>/dev/null | awk '{ s += $1 } END { printf "%d", s }')
    end=$(( since + WAIT_S + (pend + PULL_BPS - 1) / PULL_BPS )); [ "$end" -gt $(( t0 + WAIT_CAP_S )) ] && end=$(( t0 + WAIT_CAP_S ))
    [ "$(date +%s)" -ge "$end" ] && break
    sleep "$POLL_S"
  done
  [ -e "$OUT/capture.done" ] || {
    left=$(cd "$OUT" && for f in seg_*.pending; do [ -e "$f" ] && echo "$GDIR/${f%.pending}.mp4"; done | tr '\n' ' ')
    echo "capture did not end within $(( $(date +%s) - t0 )) s (tail $WAIT_S s, $pend byte(s) still to pull at $PULL_BPS B/s, cap $WAIT_CAP_S s); still to pull, on the guest until pulled: ${left:-none}"; exit 1; }
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
timeout --foreground "$CLOCK_TIMEOUT_S" bash "$CLOCK" measure "$OUT" capture_start > /dev/null || echo "WARNING: no clock measurement at the start"
stills start
a shell dumpsys media.audio_flinger > "$OUT/audio_flinger_start.txt" 2>&1
LOGCAT_FROM=$(a shell date +%s.%N | tr -d '\r')
a shell "mkdir -p $GDIR" > /dev/null
# the guest keeps the segment that records and those not yet pulled (at most MAX_PULLS in flight; more wait when the
# pulls are slower than the segments): /data is read again at every launch (guest_data_free_kb per segment)
GUEST_KB=$(a shell "df -k /data" 2>/dev/null | tr -d '\r' | awk 'NR == 2 { print $4 }'); case "$GUEST_KB" in ''|*[!0-9]*) GUEST_KB="" ;; esac
NEED_KB=$(( 2 * (BIT_RATE / 8) * SEGMENT_S / 1024 ))
if [ -z "$GUEST_KB" ]; then echo "WARNING: the guest's free space on /data is unknown (df -k /data)"
elif [ "$GUEST_KB" -lt "$NEED_KB" ]; then
  echo "WARNING: the guest's /data has $GUEST_KB KiB free, less than two segments ($NEED_KB KiB): a recording may be cut short"
fi

pending() { echo "$2" > "$OUT/seg_$1.pending.tmp" && mv -f "$OUT/seg_$1.pending.tmp" "$OUT/seg_$1.pending"; }
pull_seg() {   # pull_seg <k>: run in the background, beside the next recording
  local k=$1 g="$GDIR/seg_$1.mp4" f="$OUT/seg_$1.mp4" n hs he rc ok=false sum=null
  n=$(a shell "stat -c %s $g" 2>/dev/null | tr -d '\r'); case "$n" in ''|*[!0-9]*) n="" ;; esac
  [ -n "$n" ] && pending "$k" "$n"
  hs=$(now)
  # into .part, renamed once complete: a cut or failed pull never leaves a part of the file under the final name
  timeout --foreground "$PULL_TIMEOUT_S" "$ADB" -s "$IVI_ADB" pull "$g" "$f.part" > /dev/null 2>&1; rc=$?
  he=$(now)
  if [ "$rc" = 0 ] && [ -e "$f.part" ] && { [ -z "$n" ] || [ "$(stat -c %s "$f.part" 2>/dev/null)" = "$n" ]; }; then
    sum=\"$(sha256sum "$f.part" | awk '{ print $1 }')\"; mv -f "$f.part" "$f"; ok=true
    [ -n "$n" ] && a shell "rm -f $g" > /dev/null 2>&1   # here with the guest's size: the guest's space is freed
  else
    [ -e "$f.part" ] && mv -f "$f.part" "$f.partial"
    echo "WARNING: pull of seg_$k.mp4 failed; the guest file is kept: $g"
  fi
  printf '{"segment": %d, "file": "seg_%d.mp4", "guest_path": "%s", "guest_bytes": %s, "host_start_s": %s, "host_end_s": %s, "rc": %d, "pulled": %s, "sha256": %s}\n' \
    "$k" "$k" "$g" "${n:-null}" "$hs" "$he" "$rc" "$ok" "$sum" >> "$OUT/pulls.jsonl"
  rm -f "$OUT/seg_$k.pending"
}
unpulled() {   # unpulled <k> <why>: a segment whose recording's state is unknown is not pulled; it stays on the guest
  printf '{"segment": %d, "file": "seg_%d.mp4", "guest_path": "%s", "guest_bytes": null, "host_start_s": null, "host_end_s": null, "rc": null, "pulled": false, "sha256": null, "why": "%s"}\n' \
    "$1" "$1" "$GDIR/seg_$1.mp4" "$2" >> "$OUT/pulls.jsonl"
  rm -f "$OUT/seg_$1.pending"; echo "WARNING: seg_$1.mp4 not pulled ($2); the guest file is kept: $GDIR/seg_$1.mp4"
}
pump() {   # reaps the pulls that ended, then starts queued ones while fewer than MAX_PULLS run
  local p live=()
  for p in ${PULLS[@]+"${PULLS[@]}"}; do kill -0 "$p" 2>/dev/null && live+=("$p"); done
  PULLS=(${live[@]+"${live[@]}"})
  while [ "${#QUEUE[@]}" -gt 0 ] && [ "${#PULLS[@]}" -lt "$MAX_PULLS" ]; do
    pull_seg "${QUEUE[0]}" & PULLS+=($!)
    QUEUE=("${QUEUE[@]:1}")
  done
}
drain() { while pump; [ "${#QUEUE[@]}" -gt 0 ] || [ "${#PULLS[@]}" -gt 0 ]; do sleep 0.1; done; wait; }
launch() {   # launch <k>: sets gb, pid, ga, hb, ha, lim, NEAR, kb; 1 if no recording started
  local k=$1 r
  pending "$k" $(( BIT_RATE / 8 * lim ))   # a bound until the segment ends
  hb=$(now)
  # one guest shell: clock, the background recording, clock (its output goes to /dev/null, so the call returns at
  # once), then /data's free space (after the bracket: no time added to it)
  r=$(a shell "date +%s.%N; screenrecord --time-limit $lim --bit-rate $BIT_RATE --display-id $DID $GDIR/seg_$k.mp4 > /dev/null 2>&1 & echo pid=\$!; date +%s.%N; df -k /data 2>/dev/null" | tr -d '\r')
  ha=$(now)
  gb=$(echo "$r" | sed -n 1p); pid=$(echo "$r" | sed -n 's/^pid=//p'); ga=$(echo "$r" | sed -n 3p)
  kb=$(echo "$r" | awk 'NR == 5 { print $4 }'); case "$kb" in ''|*[!0-9]*) kb="" ;; esac
  [ -n "$kb" ] && [ "$kb" -lt "$NEED_KB" ] && \
    echo "WARNING: at segment $k the guest's /data has $kb KiB free, less than two segments ($NEED_KB KiB)"
  NEAR=$(awk -v h="$hb" -v l="$lim" -v n="$NEAR_END_S" 'BEGIN { printf "%.3f", h + l - n }')
  [ -n "$pid" ] || { rm -f "$OUT/seg_$k.pending"; echo "screenrecord did not start: $r"; return 1; }
}
pause() {   # POLL_S until NEAR_END_S before the time limit, then FAST_POLL_S (never longer than POLL_S)
  sleep "$(awk -v now="$(now)" -v near="$NEAR" -v p="$POLL_S" -v f="$FAST_POLL_S" \
    'BEGIN { if (f > p) f = p; s = near - now; if (s <= 0) s = f; else if (s > p) s = p; printf "%.3f", s }')"
}
poll() {   # v: "alive", "ended <guest clock>", or anything else (no answer: adb failed or timed out)
  v=$(ab "$POLL_TIMEOUT_S" shell "kill -0 $pid 2>/dev/null && echo alive || echo ended \$(date +%s.%N)" 2>/dev/null | tr -d '\r')
}
seg_limit() { local left=$(( MAX_S - ($(date +%s) - T_START) )); lim=$(( left < SEGMENT_S ? left : SEGMENT_S )); }

END=stop; K=1; PULLS=(); QUEUE=(); EARLY=0; T_START=$(date +%s)   # --max-s counts from the first recording
seg_limit
if launch "$K"; then
  while :; do
    seg_end=time-limit; unk=""; te=""
    # a segment ends only on the guest's own answer "ended": adb's whole answer is read (tr reads to the end) and
    # compared, so neither a reader that stops at its match (SIGPIPE under pipefail) nor a failed adb call reads a
    # live recording as ended. No answer for ALIVE_UNKNOWN_S: the capture ends (error), below
    while :; do
      poll
      case "$v" in
        alive) unk="" ;;
        "ended "*) te=${v#ended }; case "$te" in ''|*[!0-9.]*) te="" ;; esac; break ;;
        *) [ -n "$unk" ] || unk=$(now)
           awk -v s="$unk" -v n="$(now)" -v b="$ALIVE_UNKNOWN_S" 'BEGIN { exit !(n - s >= b) }' && { seg_end=no-answer; break; } ;;
      esac
      if [ -e "$OUT/STOP" ] && [ "$seg_end" != stop ]; then
        # SIGINT finishes the file. A recording that reached its time limit since the poll is gone: kill fails,
        # nothing is sent, and the segment says time-limit
        s=$(a shell "kill -INT $pid 2>/dev/null && echo sent" | tr -d '\r'); [ "$s" = sent ] && seg_end=stop
      fi
      pump
      pause
    done
    pk=$K; pgb=$gb; pga=$ga; phb=$hb; pha=$ha; pkb=$kb; pend_k=$seg_end; next=1; ge=""
    if [ "$pend_k" = no-answer ]; then
      END=error; next=0
      echo "WARNING: no answer from the guest about recording $pk for $ALIVE_UNKNOWN_S s: the capture ends (error)"
      a shell "kill -INT $pid 2>/dev/null" > /dev/null 2>&1   # ends a live recording; its file is finished
      for _ in 1 2 3 4 5; do poll; case "$v" in "ended "*) te=${v#ended }; break ;; esac; sleep "$POLL_S"; done
    elif [ "$pend_k" = time-limit ] && [ ! -e "$OUT/STOP" ] && [ -n "$te" ] && \
         awk -v e="$te" -v b="$gb" -v l="$lim" -v x="$EARLY_S" 'BEGIN { exit !(e - b < l - x) }'; then
      pend_k=ended-early; EARLY=$((EARLY + 1))   # a full /data, a display gone, an encoder failure: no time limit
      echo "WARNING: recording $pk ended early (guest $gb .. $te, limit $lim s)"
      [ "$EARLY" -ge "$EARLY_MAX" ] && { END=error; next=0; echo "WARNING: $EARLY recordings ended early: the capture ends (error)"; }
    fi
    seg_limit
    if [ "$next" = 0 ]; then :
    elif [ "$seg_end" = stop ] || [ -e "$OUT/STOP" ]; then next=0
    elif [ "$lim" -le 0 ]; then next=0; END=max-s; fi
    if [ "$next" = 1 ]; then
      K=$((K + 1))
      # the next segment's first guest clock read comes after this one was seen ended: it is this one's end read
      if launch "$K"; then ge=$gb; else next=0; END=error; K=$((K - 1)); fi
    fi
    [ -n "$ge" ] || ge=$(a shell date +%s.%N | tr -d '\r')
    printf '{"segment": %d, "file": "seg_%d.mp4", "display_id": "%s", "guest_before_s": %s, "guest_after_s": %s, "host_before_s": %s, "host_after_s": %s, "guest_end_s": %s, "guest_seen_ended_s": %s, "guest_data_free_kb": %s, "end": "%s"}\n' \
      "$pk" "$pk" "$DID" "$pgb" "$pga" "$phb" "$pha" "${ge:-null}" "${te:-null}" "${pkb:-null}" "$pend_k" >> "$OUT/segments.jsonl"
    if [ "$pend_k" = no-answer ] && [ -z "$te" ]; then
      unpulled "$pk" "no answer from the guest: the recording may still run"
    else
      QUEUE+=("$pk"); pump
    fi
    [ "$next" = 1 ] || break
  done
else
  END=error; K=0
fi

# the app's records first, each call bounded: no trouble with the segments or the other end calls costs them
# @user@ in a path: the IVI's current user (an AAOS IVI may run its apps as a secondary user; the app's files are
# under /data/user/<user>/<package>/), as ivi-warning-app/scripts/stage_ivi_warning_app.sh pull reads it
GUSER=$(a shell am get-current-user 2>/dev/null | tr -d '\r'); case "$GUSER" in ''|*[!0-9]*) GUSER=0 ;; esac
for p in ${APP_RECORD_PATHS:-}; do
  p=${p//@user@/$GUSER}
  a pull "$p" "$OUT/app_record_$(basename "$p")" > /dev/null 2>&1 || echo "app record $p: not on the guest" >> "$OUT/app_record_missing.txt"
done
stills end
a shell dumpsys media.audio_flinger > "$OUT/audio_flinger_end.txt" 2>&1
a logcat -d -v epoch -T "$LOGCAT_FROM" > "$OUT/logcat.txt" 2>&1 || a logcat -d -v epoch > "$OUT/logcat.txt" 2>&1
timeout --foreground "$CLOCK_TIMEOUT_S" bash "$CLOCK" measure "$OUT" capture_end > /dev/null || echo "WARNING: no clock measurement at the end"
# the pulls end within PULL_TIMEOUT_S each; the guest's folder goes only if every segment is here
drain
KEPT=$(grep -h '"pulled": false' "$OUT/pulls.jsonl" 2>/dev/null | sed -n 's/.*"guest_path": "\([^"]*\)".*/\1/p' | tr '\n' ' ')
if [ -z "$KEPT" ]; then a shell "rm -rf $GDIR" > /dev/null 2>&1; else echo "WARNING: kept on the guest: $KEPT"; fi
OUT="$OUT" END="$END" IDS="$IDS" DID="$DID" GDIR="$GDIR" KEPT="$KEPT" GUEST_KB="$GUEST_KB" python3 - <<'PY'
import hashlib, json, os
o = os.environ["OUT"]
def lines(name):
    p = os.path.join(o, name)
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []
segs, pulls, clock = lines("segments.jsonl"), lines("pulls.jsonl"), lines("clock.jsonl")
def digest(f):   # the segments' digests were taken by their pulls: nothing here reads a whole recording again
    h = hashlib.sha256()
    with open(os.path.join(o, f), "rb") as r:
        for chunk in iter(lambda: r.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
by_pull = {p["file"]: p["sha256"] for p in pulls if p["pulled"] and p.get("sha256")}
files = sorted(f for f in os.listdir(o) if f not in ("capture.json", "capture.done", "STOP"))
sha = {f: by_pull.get(f) or digest(f) for f in files}
pulled = {p["segment"]: p["pulled"] for p in pulls}
for s in segs:
    s["pulled"] = pulled.get(s["segment"], False)
    s["sha256"] = sha.get(s["file"]) if s["pulled"] else None
# the unrecorded span between segment k's last frame and segment k+1's first frame, on the guest clock. From below:
# first_k+1 >= guest_before_k+1 and last_k <= guest_end_k. The upper bound needs the frame times, which the
# composer reads (compose_side_by_side.py, manifest.json display.boundaries)
bounds = []
for a, b in zip(segs, segs[1:]):
    bounds.append({
        "after_segment": a["segment"], "before_segment": b["segment"],
        "unrecorded_min_s": None if a["guest_end_s"] is None else b["guest_before_s"] - a["guest_end_s"],
        "unrecorded_max_s": None,
        "unrecorded_max_where": "compose_side_by_side.py, manifest.json display.boundaries: (guest_end_s of the "
                                "later segment - its frame span) - (guest_before_s of the earlier one + its frame "
                                "span), the spans from the segments' packet times"})
kept = os.environ["KEPT"].split()
json.dump({"display_ids": os.environ["IDS"].split(), "recorded_display_id": os.environ["DID"], "end": os.environ["END"],
           "segments": segs, "boundaries": bounds, "pulls": pulls,
           "pull_failures": [{"segment": p["segment"], "guest_path": p["guest_path"]} for p in pulls if not p["pulled"]],
           "guest_dir_kept": os.environ["GDIR"] if kept else None,
           "guest_data_free_kb": int(os.environ["GUEST_KB"]) if os.environ["GUEST_KB"] else None,
           "clock": clock, "sha256": sha,
           "not_filled_here": {"fields": ["boundaries[].unrecorded_max_s", "frame times"],
                               "where": "compose_side_by_side.py on the composing host reads the segments' packet "
                                        "times (no decode, under a time bound) and writes them to its "
                                        "manifest.json (display.segments, display.boundaries)"},
           "sound": "no audio capture; the sound start comes from the app's own record, if present"},
          open(os.path.join(o, "capture.json"), "w"), indent=1)
PY
echo "capture ended ($END), $K segment(s)${KEPT:+; pull failed, kept on the guest: ${KEPT% }}" | tee "$OUT/capture.done"
[ "$END" != error ]
