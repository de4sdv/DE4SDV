#!/bin/bash
# The chase videos of a session, fetched after it from the simulator host alone (C6 of the S1 build; session/README.md
# "The chase videos"). The session's pack leaves every out/rec_*/chase_view.mp4 on the simulator host and lists each
# with its size and sha256 in out/pack_excluded.tsv (remote/host_step.sh pack): about 144 MB a run, 2.2 GB for s1,
# past any fetch bound through IAP inside the paid session. Adapted from the proven after-the-fact fetch of p10-2
# attempt 3 (sessions/incoming_20261120T092051Z/sim-lead-fetch/fetch_g4_ranges.sh, 306 MB at about 1.03 MB/s).
#
#   fetch_chase.sh [--dry-run] <incoming dir>     the session's folder, holding sim/out/pack_excluded.tsv
#
# It refuses unless the simulator host reads TERMINATED and no da-session-* user unit is active (never a host a
# session holds). Then, in rounds: start the host and read RUNNING back, SSH through IAP, arm the host's power-off
# safety net (the fetch's bound plus its margin), read each video not fetched yet as ranges of FETCH_RANGE_MIB MiB over
# FETCH_PARALLEL IAP tunnels (`dd` on the host, nothing written there; hosts.env), join the ranges, compare the sha256
# with pack_excluded.tsv, and keep the file under its name only when they agree. The EXIT trap stops the host and
# reads TERMINATED back. A start refused for capacity costs nothing: the next round follows after RETRY_S (180 s), up
# to RETRY_N rounds (20: an hour). A video already fetched whole is skipped, so a later run resumes.
#
# Records: <incoming>/sim/fetch_chase/ (fetch_chase.log, ranges.tsv, fetch_chase.json: each video's result, the
# host's start and stop, its status after, the cost at the simulator host's hourly price). The videos go to
# <incoming>/sim/out/rec_<run>/chase_view.mp4, where the session would have put them.
#
# Exit codes: 0 every video fetched and equal; 2 refused (the host not TERMINATED, a session unit active, no list, a
# dry-run knob in a real run); 3 no SSH; 4 no capacity within the rounds; 5 a video failed (sha256, size, bound);
# 6 start refused (quota or error) or the safety net not armed; 9 dry run refused; 11 the host not TERMINATED after.
set -uo pipefail
export LC_ALL=C
unset PYTHONPATH   # gcloud's own Python, never another runtime's site-packages (rule 39)
trap '' PIPE       # a gone stdout reader never ends the fetch or its trap; every line goes to the log file first
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=hosts.env
. "$HERE/hosts.env"
DRY=0; ONCE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1; shift ;;
    --once) ONCE=1; shift ;;
    -h|--help) sed -n '2,27p' "$0"; exit 0 ;;
    -*) echo "unknown argument: $1" >&2; exit 2 ;;
    *) break ;;
  esac
done
IN_ARG=${1:?usage: fetch_chase.sh [--dry-run] <incoming dir>}
IN=$(cd -- "$IN_ARG" 2>/dev/null && pwd) || { echo "refused: no folder $IN_ARG"; exit 2; }

RETRY_S=180; RETRY_N=20; SSH_TRIES=30; SSH_PAUSE_S=10; RUNNING_WAIT_S=120; STOP_TRIES=30; STOP_POLL_S=10
FETCH_BASE_S=120; FETCH_PLAN_BPS=500000; FETCH_TRY_BASE_S=30; FETCH_TRIES=3; SAFETY_MARGIN_MIN=15
KNOBS=(RETRY_S RETRY_N SSH_TRIES SSH_PAUSE_S RUNNING_WAIT_S STOP_TRIES STOP_POLL_S FETCH_BASE_S FETCH_PLAN_BPS)
if [ "$DRY" = 1 ]; then
  GCLOUD=${DA_GCLOUD:-}
  [ -n "$GCLOUD" ] && [ -x "$GCLOUD" ] || { echo "dry run refused: DA_GCLOUD must name the fake gcloud"; exit 9; }
  case "$(readlink -f "$GCLOUD")" in
    "$(readlink -f "$HOME")"/google-cloud-sdk/*|*/google-cloud-sdk/bin/*) echo "dry run refused: $GCLOUD is a real gcloud"; exit 9 ;;
  esac
  for v in "${KNOBS[@]}"; do o="DA_T_$v"; [ -n "${!o:-}" ] && printf -v "$v" '%s' "${!o}"; done
else
  GCLOUD=$HOME/google-cloud-sdk/bin/gcloud
  for v in "${KNOBS[@]}"; do o="DA_T_$v"; [ -n "${!o:-}" ] && { echo "refused: $o is a dry-run knob"; exit 2; }; done
  [ -n "${DA_GCLOUD:-}" ] && { echo "refused: DA_GCLOUD is a dry-run knob"; exit 2; }
fi
for _n in FETCH_PARALLEL FETCH_RANGE_MIB; do
  [[ "${!_n}" =~ ^[1-9][0-9]*$ ]] || { echo "refused: $_n must be a whole number >= 1, not '${!_n}'"; exit 2; }
done

# the rounds: each a fresh process (--once) with its own EXIT trap; only a capacity refusal (4) is tried again
if [ "$ONCE" = 0 ]; then
  # a signal to this process (systemctl stop of its unit sends TERM to the main process only) goes on to the round,
  # whose EXIT trap stops the host; no round starts after it, and this process ends with the round's code
  args=(); [ "$DRY" = 1 ] && args+=(--dry-run); child=""; sig=""
  trap 'sig=1; [ -n "$child" ] && kill -TERM "$child" 2>/dev/null' TERM INT HUP
  for t in $(seq 1 "$RETRY_N"); do
    echo "round $t of $RETRY_N $(date -u +%FT%TZ)"
    bash "$0" "${args[@]}" --once "$IN" & child=$!
    while :; do wait "$child"; rc=$?; kill -0 "$child" 2>/dev/null || break; done
    child=""
    [ -n "$sig" ] && exit "$rc"
    [ "$rc" = 4 ] || exit "$rc"
    [ "$t" -lt "$RETRY_N" ] && { sleep "$RETRY_S" & wait $!; [ -n "$sig" ] && exit 143; }
  done
  echo "no capacity for $SIM_VM in $RETRY_N rounds: the videos stay on its disk"; exit 4
fi

VM=$SIM_VM; Z=$SIM_ZONE; PROJ=$SIM_PROJECT
OUT=$IN/sim/fetch_chase; mkdir -p "$OUT"; LOG=$OUT/fetch_chase.log
log() { local l; l="$(date -u +%FT%TZ) $*"; printf '%s\n' "$l" >> "$LOG"; printf '%s\n' "$l" 2>/dev/null || true; }
gc() { timeout "${GC_TO:-120}" "$GCLOUD" --configuration="$GCLOUD_CONFIGURATION" --project="$PROJ" "$@"; }
iap() { [ "$SIM_SSH_IAP" = 1 ] && echo --tunnel-through-iap; }
# shellcheck disable=SC2046  # iap prints one word or nothing
ssh_c() { local to=$1; shift; timeout "$to" "$GCLOUD" --configuration="$GCLOUD_CONFIGURATION" --project="$PROJ" \
  compute ssh "$VM" --zone "$Z" $(iap) "$@" < /dev/null; }
vmst() { gc compute instances describe "$VM" --zone "$Z" --format='value(status)' 2>/dev/null || echo UNKNOWN; }

SID=$(head -1 "$IN/sim/out/session_id" 2>/dev/null)
[[ "$SID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || { log "refused: no session id in $IN/sim/out/session_id"; exit 2; }
TSV=$IN/sim/out/pack_excluded.tsv
[ -s "$TSV" ] || { log "refused: no $TSV (the session's simulator host was not fetched, or packed before C3)"; exit 2; }
# the videos: <path> <bytes> <sha256> rows of the recorder's videos; *.rrd rows (no sha256) are not this script's
PATHS=(); declare -A WANT_B=() WANT_SHA=()
while IFS=$'\t' read -r p b h; do
  [[ "$p" =~ ^out/rec_[A-Za-z0-9._-]+/chase_view\.mp4$ ]] || continue
  [[ "$b" =~ ^[0-9]+$ ]] && [[ "$h" =~ ^[0-9a-f]{64}$ ]] || { log "refused: a malformed row in $TSV: $p $b $h"; exit 2; }
  PATHS+=("$p"); WANT_B[$p]=$b; WANT_SHA[$p]=$h
done < "$TSV"
TODO=(); TOTAL=0
for p in "${PATHS[@]}"; do
  if [ -f "$IN/sim/$p" ] && [ "$(sha256sum "$IN/sim/$p" | cut -d' ' -f1)" = "${WANT_SHA[$p]}" ]; then
    log "already fetched whole: $p"; continue
  fi
  TODO+=("$p"); TOTAL=$(( TOTAL + WANT_B[$p] ))
done
log "session $SID: ${#PATHS[@]} chase videos listed, ${#TODO[@]} to fetch ($TOTAL B) from $VM"
if [ ${#TODO[@]} = 0 ]; then
  python3 - "$OUT/fetch_chase.json" "$SID" <<'PY'
import json, sys
json.dump({"session_id": sys.argv[2], "result": "ok", "files": [], "note": "nothing left to fetch"}, open(sys.argv[1], "w"), indent=1)
PY
  exit 0
fi

# never a host a session holds: TERMINATED, and no session unit active
ST=$(vmst); log "before: $VM $ST"
[ "$ST" = TERMINATED ] || { log "refused: $VM is $ST, expected TERMINATED (a session or another fetch may hold it)"; exit 2; }
UNITS=$(timeout --foreground 30 systemctl --user list-units 'da-session-*' --state=active --no-legend 2>&1) \
  || { log "refused: cannot read the da-session units: $UNITS"; exit 2; }
[ -z "$UNITS" ] || { log "refused: a da-session unit is active: $(head -1 <<< "$UNITS")"; exit 2; }

BOUND=$(( FETCH_BASE_S + (TOTAL + FETCH_PLAN_BPS - 1) / FETCH_PLAN_BPS ))
try_s() { echo $(( FETCH_TRY_BASE_S + (2 * FETCH_RANGE_MIB * 1048576 * FETCH_PARALLEL + 1000000 - 1) / 1000000 )); }
T_START=""; T_STOP=""; ST_AFTER=""; RESULT=fail; RC=1
RES_TSV=$OUT/.results.tsv; : > "$RES_TSV"
record() {
  python3 - "$OUT/fetch_chase.json" "$SID" "$VM" "$T_START" "$T_STOP" "$ST_AFTER" "$SIM_EUR_H" "$RESULT" "$BOUND" \
    "$RES_TSV" "$FETCH_PARALLEL" "$FETCH_RANGE_MIB" <<'PY'
import json, os, sys
out, sid, vm, t0, t1, st, eur, result, bound, res, par, mib = sys.argv[1:]
files = []
for line in open(res, encoding="utf-8"):
    p, b, want, got, r, secs = (line.rstrip("\n").split("\t") + [""] * 6)[:6]
    files.append({"path": p, "bytes": int(b), "sha256": want, "sha256_got": got or None, "result": r,
                  "seconds": float(secs) if secs else None})
up = float(t1) - float(t0) if t0 and t1 else None
prev = []
if os.path.exists(out):
    try:
        old = json.load(open(out))
        prev = old.get("earlier", []) + [{k: v for k, v in old.items() if k != "earlier"}]
    except ValueError:
        prev = []
json.dump({"session_id": sid, "vm": vm, "result": result, "files": files, "bound_s": int(bound),
           "parallel": int(par), "range_mib": int(mib), "start_call_unix_s": float(t0) if t0 else None,
           "stopped_unix_s": float(t1) if t1 else None, "vm_status_after": st or None,
           "eur_upper_bound": round(up * float(eur) / 3600, 3) if up is not None else None, "eur_per_hour": float(eur),
           "earlier": prev}, open(out, "w"), indent=1)
PY
}
kill_tree() { local c; for c in $(pgrep -P "$1" 2>/dev/null); do kill_tree "$c"; done; kill "$1" 2>/dev/null; }
stop_vm() {
  trap '' INT TERM HUP
  local i
  # a signal during the ranges: every tunnel's tree first (timeout and gcloud sit in timeout's own process group)
  [ -n "${PIDS:-}" ] && for i in $PIDS; do kill_tree "$i"; done
  log "stopping $VM"
  GC_TO=300 gc compute instances stop "$VM" --zone "$Z" --async --quiet >> "$LOG" 2>&1
  for i in $(seq 1 "$STOP_TRIES"); do ST_AFTER=$(GC_TO=30 vmst); [ "$ST_AFTER" = TERMINATED ] && break; sleep "$STOP_POLL_S"; done
  T_STOP=$(date +%s.%N)
  log "after: $VM $ST_AFTER"
  rm -rf "$OUT/.ranges"
  record; rm -f "$RES_TSV"
  if [ "$ST_AFTER" != TERMINATED ]; then log "STOP NOT CONFIRMED for $VM: stop it by hand now"; exit 11; fi
  exit "$RC"
}
on_sig() { trap '' INT TERM HUP; RC=$1; exit "$1"; }   # a second signal (the group's and the main process's) never cuts the trap
trap stop_vm EXIT
trap 'on_sig 143' TERM; trap 'on_sig 130' INT; trap 'on_sig 129' HUP

T_START=$(date +%s.%N)
SOUT=$(GC_TO=300 gc compute instances start "$VM" --zone "$Z" 2>&1); src=$?
printf '%s\n' "$SOUT" >> "$LOG"
ST=""; for i in $(seq 1 $(( RUNNING_WAIT_S / 10 + 1 ))); do ST=$(vmst); [ "$ST" = RUNNING ] && break; [ "$src" = 0 ] || break; sleep 1; done
if [ "$ST" != RUNNING ]; then
  case "$SOUT" in
    *STOCKOUT*|*ZONE_RESOURCE_POOL_EXHAUSTED*|*"does not have enough resources"*|*"resource pool exhausted"*)
      log "no capacity for $VM ($(grep -o -E 'STOCKOUT|ZONE_RESOURCE_POOL_EXHAUSTED[A-Z_]*|not have enough resources' <<< "$SOUT" | head -1)): the next round after $RETRY_S s"
      RESULT="no capacity"; RC=4; exit 4 ;;
    *) log "start of $VM refused (rc $src, status $ST): $(tail -1 <<< "$SOUT")"; RESULT="start refused"; RC=6; exit 6 ;;
  esac
fi
log "$VM RUNNING"
ok=""; for i in $(seq 1 "$SSH_TRIES"); do ssh_c 60 --command true > /dev/null 2>&1 && { ok=1; break; }; sleep "$SSH_PAUSE_S"; done
[ -n "$ok" ] || { log "no SSH to $VM"; RESULT="no ssh"; RC=3; exit 3; }
# the host's own power-off: the fetch's bound plus its margin, should this host lose this script
NET_MIN=$(( BOUND / 60 + SAFETY_MARGIN_MIN ))
NET=$(ssh_c 60 --command "bash ~/da-kit/$SID/bench/session/remote/safety_net.sh arm $NET_MIN" 2>&1)
grep -q -x "safety-net-$NET_MIN" <<< "$NET" || { log "safety net of $VM not armed: $(tail -1 <<< "$NET")"; RESULT="safety net not armed"; RC=6; exit 6; }
log "$VM: SSH ok, power-off safety net in $NET_MIN min; the fetch's bound $BOUND s ($FETCH_BASE_S s plus $TOTAL B at $FETCH_PLAN_BPS B/s), $FETCH_PARALLEL tunnels, ranges of $FETCH_RANGE_MIB MiB"

END=$(( $(date +%s) + BOUND ))
RT=$OUT/ranges.tsv; [ -s "$RT" ] || printf 'path\trange\ttry\tstart_s\tend_s\tbytes\twant\tresult\n' > "$RT"
range_get() {   # range_get <path> <index> <bytes> <dir>: one range, FETCH_TRIES tries, size-checked
  local p=$1 i=$2 size=$3 dir=$4 rb want t to s e got rc res f cmd
  rb=$(( FETCH_RANGE_MIB * 1048576 )); want=$(( size - i * rb )); [ "$want" -gt "$rb" ] && want=$rb
  f=$dir/$(printf 'p%06d' "$i")
  cmd="dd if=\$HOME/da-kit/$SID/$p bs=1M skip=$(( i * FETCH_RANGE_MIB )) count=$FETCH_RANGE_MIB status=none"
  for (( t = 1; t <= FETCH_TRIES; t++ )); do
    to=$(( END - $(date +%s) )); [ "$to" -gt "$(try_s)" ] && to=$(try_s)
    [ "$to" -ge 1 ] || { res="the fetch's bound reached"; break; }
    s=$(date +%s.%N)
    ssh_c "$to" --ssh-flag=-T --command "$cmd" > "$f.part" 2>> "$dir/stderr.txt"; rc=$?
    e=$(date +%s.%N); got=$(stat -c %s "$f.part" 2>/dev/null || echo 0)
    if [ "$got" = "$want" ]; then res=ok; elif [ "$rc" = 124 ]; then res="rc 124"
    elif [ "$got" -lt "$want" ]; then res=short; else res="size $got"; fi
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$p" "$i" "$t" "$s" "$e" "$got" "$want" "$res" >> "$RT"
    [ "$res" = ok ] && { mv "$f.part" "$f"; return 0; }
  done
  rm -f "$f.part"; echo "range $i of $p failed: $res" >> "$dir/failed"; return 1
}
fetch_one() {   # fetch_one <path>: its ranges, joined, its sha256 against the list's; the file only when equal
  local p=$1 size=${WANT_B[$1]} n i running=0 dir=$OUT/.ranges t0 got dest r=""
  t0=$(date +%s.%N); rm -rf "$dir"; mkdir -p "$dir"
  n=$(( (size + FETCH_RANGE_MIB * 1048576 - 1) / (FETCH_RANGE_MIB * 1048576) )); [ "$n" -ge 1 ] || n=1
  PIDS=""
  for (( i = 0; i < n; i++ )); do
    while [ "$running" -ge "$FETCH_PARALLEL" ]; do wait -n; running=$(( running - 1 )); done
    [ -e "$dir/failed" ] && break
    # the worker outlives a TERM or HUP to the whole group until its tunnel ended, so the trap's kill_tree still finds
    # that tunnel's timeout and gcloud (in timeout's own process group) instead of leaving them to their bound
    ( trap 'exit 143' TERM HUP; range_get "$p" "$i" "$size" "$dir" ) & PIDS="$PIDS $!"; running=$(( running + 1 ))
  done
  wait; PIDS=""
  for (( i = 0; i < n; i++ )); do [ -f "$dir/$(printf 'p%06d' "$i")" ] || { r="failed: $(head -1 "$dir/failed" 2>/dev/null || echo "range $i not read")"; break; }; done
  dest=$IN/sim/$p; mkdir -p "$(dirname "$dest")"
  if [ -z "$r" ]; then
    cat "$dir"/p* > "$dest.part"; got=$(sha256sum "$dest.part" | cut -d' ' -f1)
    if [ "$got" = "${WANT_SHA[$p]}" ]; then mv "$dest.part" "$dest"; r=ok
    else rm -f "$dest.part"; r="sha256 mismatch: got $got, the list's ${WANT_SHA[$p]}"; fi
  fi
  rm -rf "$dir"
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$p" "$size" "${WANT_SHA[$p]}" "${got:-}" "$r" \
    "$(awk -v a="$t0" -v b="$(date +%s.%N)" 'BEGIN { printf "%.1f", b - a }')" >> "$RES_TSV"
  log "$p: $r"
  [ "$r" = ok ]
}
bad=0
for p in "${TODO[@]}"; do fetch_one "$p" || bad=1; done
if [ "$bad" = 0 ]; then RESULT=ok; RC=0; log "every chase video fetched, sha256 equal"
else RESULT="failed"; RC=5; log "FETCH INCOMPLETE: see $OUT/fetch_chase.json; the videos stay on $VM under ~/da-kit/$SID/out"; fi
exit "$RC"
