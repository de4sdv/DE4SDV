#!/bin/bash
# INC-DRIVING-002 bench session orchestrator (brief row B13). Runs on the lead host (the Jetson) and drives up to three
# hosts in two GCP projects: the simulator host (G4, Spot), the S-CORE host (L4) and the protected guest host.
#
#   da_session.sh --kind p10-1|p10-3|p10-2 [options]
#
#   --kind p10-1           the S-CORE host only: the S-CORE build check (P10-1)
#   --kind p10-3           the guest host and the S-CORE host as the S-CORE side: the warning on the guests (P10-3)
#   --kind p10-2           all three: the first closed loop, recorded (P10-2)
#   --owner-ok-guest-host  required for p10-3 and p10-2: the owner's OK to start de4sdv-aaos-build this session
#   --without-guest-host   p10-2 on the simulator host and the S-CORE host only (no display capture)
#   --cap-eur <EUR>        cost cap of this session (default per kind in hosts.env)
#   --session-id <id>      default: UTC time stamp
#   --evidence-root <dir>  default: ~/.hermes/outputs/inc-driving-002/phase10/sessions
#   --bench-tree <dir>     the repository whose bench folder is uploaded (default: this script's repository)
#   --kit-from-worktree    upload the bench folder as it is on disk (default: as committed at HEAD)
#   --kit-extra <dir>      also upload <dir> as <bench>/extra/ (stub entries in the dry-run tests)
#   --carla-host <ip>      CARLA's address for the S-CORE side (default: the simulator host's internal IP)
#   --dry-run              use the fake gcloud in $DA_GCLOUD; print every command; shorter waits (DA_T_* knobs)
#
# Start order: the G4 first, still RUNNING 30 s later, then the L4, then the guest host (rounds with short pauses
# while capacity is short). One GPU per project: a session refuses to start while another GPU VM runs in a project
# it starts a GPU VM in. The EXIT trap stops every VM this session started, on every exit, signals included: the
# guests first with cvd stop, then their host. A watchdog ends the session when the cost reaches the cap. Disks are
# never deleted; nothing is created or deleted.
#
# Exit codes: 0 done; 2 refused before any VM start; 3 no capacity or preempted; 4 SSH or upload failed; 5 a step
# failed; 6 start refused (quota or error); 9 dry run refused; 10 cost cap reached; 11 a stop not confirmed after an
# otherwise good session; 129/130/143 signals.
set -uo pipefail
export LC_ALL=C   # awk and printf read and write decimal points
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
BENCH_REL=implementation/driver-assistance-bench
# shellcheck source=hosts.env
. "$HERE/hosts.env"
# shellcheck source=entrypoints.env
. "$HERE/entrypoints.env"

KIND=""; DRY=0; CAP=""; OWNER_OK_GUEST=0; WITHOUT_GUEST=0; SID=""; KIT_FROM=head; KIT_EXTRA=""; CARLA_HOST=""
EVID=${DA_EVIDENCE_ROOT:-$HOME/.hermes/outputs/inc-driving-002/phase10/sessions}
BENCH_TREE=$(cd -- "$HERE/../../.." && pwd)
while [ $# -gt 0 ]; do
  case "$1" in
    --kind) KIND=${2:?}; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    --cap-eur) CAP=${2:?}; shift 2 ;;
    --owner-ok-guest-host) OWNER_OK_GUEST=1; shift ;;
    --without-guest-host) WITHOUT_GUEST=1; shift ;;
    --session-id) SID=${2:?}; shift 2 ;;
    --evidence-root) EVID=${2:?}; shift 2 ;;
    --bench-tree) BENCH_TREE=$(cd -- "${2:?}" && pwd); shift 2 ;;
    --kit-from-worktree) KIT_FROM=worktree; shift ;;
    --kit-extra) KIT_EXTRA=$(cd -- "${2:?}" && pwd); shift 2 ;;
    --carla-host) CARLA_HOST=${2:?}; shift 2 ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

case "$KIND" in
  p10-1) ROLES=(score); CAP=${CAP:-$CAP_EUR_P10_1} ;;
  p10-3) ROLES=(score guest); CAP=${CAP:-$CAP_EUR_P10_3} ;;
  p10-2) if [ "$WITHOUT_GUEST" = 1 ]; then ROLES=(sim score); else ROLES=(sim score guest); fi
         CAP=${CAP:-$CAP_EUR_P10_2} ;;
  *) echo "--kind p10-1|p10-3|p10-2 is required" >&2; exit 2 ;;
esac

# waits, seconds; a dry run may shorten them through DA_T_<NAME>, a real session refuses those knobs
PREEMPT_CHECK_S=30; ROUND_PAUSE_S=45; START_DEADLINE_S=1800; RUNNING_WAIT_S=120; SSH_TRIES=20; SSH_PAUSE_S=10
POLL_S=20; WATCH_S=30; STOP_TRIES=30; STOP_POLL_S=10; SAFETY_MARGIN_MIN=10
T_P10_1=5400; T_GUEST_UP=2400; T_SCORE_START=900; T_SIM_SETUP=1200; T_WARMUP=900; T_RUN=900; T_INJECT=1200
T_CAPTURE_END=180; T_REC_END=200; T_STEP=300
KNOBS=(PREEMPT_CHECK_S ROUND_PAUSE_S START_DEADLINE_S RUNNING_WAIT_S SSH_TRIES SSH_PAUSE_S POLL_S WATCH_S STOP_TRIES
       STOP_POLL_S T_P10_1 T_GUEST_UP T_SCORE_START T_SIM_SETUP T_WARMUP T_RUN T_INJECT T_CAPTURE_END T_REC_END T_STEP)
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
fi

SID=${SID:-$(date -u +%Y%m%dT%H%M%SZ)}
IN=$EVID/incoming_$SID
[ -e "$IN" ] && { echo "refused: $IN exists (one folder per session)"; exit 2; }
mkdir -p "$IN" || exit 2
LOG=$IN/session.log; CMDS=$IN/commands.log; COST=$IN/cost.log; STARTS=$IN/starts.tsv
: > "$STARTS"
exec 3>&1   # a dry run prints every command here, outside the command substitutions that capture output
MAIN_PID=$$; WD_PID=""; CHILD=""; STARTED=(); STEP_FAIL=""; FINAL_RC=""

log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }
# never log account e-mail addresses or quota limits
sanitize() { sed -E -e 's/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/<email>/g' -e '/[Ll][Ii][Mm][Ii][Tt]/d'; }
one() { sanitize | tr '\n' ' ' | tr -s ' ' | cut -c1-300; }
var() { local n="${1^^}_$2"; echo "${!n}"; }   # var <role> VM|PROJECT|ZONE|EUR_H
gc() {   # gc <role> <gcloud args...>: every call is printed (dry run) and kept in commands.log
  local role=$1; shift
  local p; p=$(var "$role" PROJECT)
  echo "$(date -u +%FT%T.%3NZ) + gcloud --configuration=$GCLOUD_CONFIGURATION --project=$p $*" >> "$CMDS"
  [ "$DRY" = 1 ] && echo "+ gcloud --configuration=$GCLOUD_CONFIGURATION --project=$p $*" >&3
  timeout "${GC_TO:-120}" "$GCLOUD" --configuration="$GCLOUD_CONFIGURATION" --project="$p" "$@"
}
vmst() { gc "$1" compute instances describe "$(var "$1" VM)" --zone "$(var "$1" ZONE)" --format='value(status)' 2>/dev/null || echo UNKNOWN; }
vmip() { gc "$1" compute instances describe "$(var "$1" VM)" --zone "$(var "$1" ZONE)" --format='value(networkInterfaces[0].networkIP)' 2>/dev/null; }
ssh_r() {   # ssh_r <role> <timeout_s> <remote command>
  local role=$1 to=$2 cmd=$3
  timeout "$to" "$GCLOUD" --configuration="$GCLOUD_CONFIGURATION" --project="$(var "$role" PROJECT)" compute ssh \
    "$(var "$role" VM)" --zone "$(var "$role" ZONE)" --command "$cmd" < /dev/null
}
ssh_l() {   # logged ssh: the command goes to commands.log (and to stderr in a dry run)
  echo "$(date -u +%FT%T.%3NZ) + ssh $1: $3" >> "$CMDS"; [ "$DRY" = 1 ] && echo "+ ssh $1: $3" >&3
  ssh_r "$@"
}
scp_r() {   # scp_r <role> <timeout_s> <src...> <dst>
  local role=$1 to=$2; shift 2
  echo "$(date -u +%FT%T.%3NZ) + scp $role: $*" >> "$CMDS"; [ "$DRY" = 1 ] && echo "+ scp $role: $*" >&3
  timeout "$to" "$GCLOUD" --configuration="$GCLOUD_CONFIGURATION" --project="$(var "$role" PROJECT)" compute scp \
    --zone "$(var "$role" ZONE)" "$@" < /dev/null
}
kill_tree() { local c; for c in $(pgrep -P "$1" 2>/dev/null); do kill_tree "$c"; done; kill "$1" 2>/dev/null; }
run_fg() { "$@" & CHILD=$!; wait "$CHILD"; local rc=$?; CHILD=""; return $rc; }   # signals interrupt the wait
nap() { run_fg sleep "$1"; }
cost_now() { awk -v now="$(date +%s.%N)" '{ s += (now - $2) * $3 / 3600 } END { printf "%.3f", s + 0 }' "$STARTS"; }
ge() { awk -v a="$1" -v b="$2" 'BEGIN { exit !(a >= b) }'; }

# ───────────── exit trap: stop what this session started ─────────────
cleanup() {
  local rc=$? r st i
  trap - EXIT INT TERM HUP
  [ -n "$FINAL_RC" ] && rc=$FINAL_RC
  [ -f "$IN/.cap_reached" ] && rc=10
  [ -n "$WD_PID" ] && { pkill -P "$WD_PID" 2>/dev/null; kill "$WD_PID" 2>/dev/null; }
  [ -n "$CHILD" ] && kill_tree "$CHILD"   # an interrupted SSH step: its local client and timeout too
  local gpu=() guest=0
  for r in "${STARTED[@]}"; do if [ "$r" = guest ]; then guest=1; else gpu+=("$r"); fi; done
  # the GPU hosts first (they cost most), without waiting
  for r in "${gpu[@]}"; do
    log "stopping $(var "$r" VM) ($r)"
    GC_TO=300 gc "$r" compute instances stop "$(var "$r" VM)" --zone "$(var "$r" ZONE)" --async --quiet 2>&1 | one >> "$LOG"
  done
  if [ "$guest" = 1 ]; then
    st=$(vmst guest)
    if [ "$st" = RUNNING ]; then
      log "stopping the guests with cvd stop before their host"
      local out; out=$(ssh_l guest 300 "$GUEST_STOP_CMD" 2>&1); echo "$out" | sanitize > "$IN/guest_stop.out"
      if echo "$out" | grep -q "crosvm_processes_after_stop: 0"; then log "guests stopped (no crosvm process left)"
      else log "WARNING guests' stop not confirmed (see guest_stop.out); the host is stopped anyway: resume with cvd stop, then cvd start --resume=true"; fi
    else
      log "guest host status $st: no cvd stop possible"
    fi
    log "stopping $(var guest VM) (guest)"
    GC_TO=300 gc guest compute instances stop "$(var guest VM)" --zone "$(var guest ZONE)" --async --quiet 2>&1 | one >> "$LOG"
  fi
  for r in "${STARTED[@]}"; do
    for i in $(seq 1 "$STOP_TRIES"); do st=$(vmst "$r"); [ "$st" = TERMINATED ] && break; sleep "$STOP_POLL_S"; done
    log "status after stop: $(var "$r" VM) $st"
    [ "$st" = TERMINATED ] || { log "STOP NOT CONFIRMED for $(var "$r" VM): stop it by hand now"; [ "$rc" = 0 ] && rc=11; }
  done
  [ -s "$STARTS" ] && echo "$(date -u +%FT%TZ) final cost $(cost_now) EUR of cap $CAP EUR (upper bound: from each start call to now)" | tee -a "$COST" >> "$LOG"
  # every VM of both projects, after the session (SKB: list both projects after every session)
  for p in $(for r in sim score guest; do var "$r" PROJECT; done | sort -u); do
    echo "$(date -u +%FT%T.%3NZ) + gcloud --project=$p compute instances list" >> "$CMDS"
    [ "$DRY" = 1 ] && echo "+ gcloud --configuration=$GCLOUD_CONFIGURATION --project=$p compute instances list" >&3
    "$GCLOUD" --configuration="$GCLOUD_CONFIGURATION" --project="$p" compute instances list \
      --format='value(name,zone.basename(),status)' 2>/dev/null | sed "s/^/VM after session [$p]: /" >> "$LOG"
  done
  write_record "$rc"
  log "SESSION_END $SID rc=$rc"
  exit "$rc"
}
write_record() {
  KIND="$KIND" SID="$SID" RC="$1" CAP="$CAP" IN="$IN" STARTED="${STARTED[*]}" STEP_FAIL="$STEP_FAIL" \
  KIT_SHA="${KIT_SHA:-}" BENCH_COMMIT="${BENCH_COMMIT:-}" WT_CHANGES="${WT_CHANGES:-}" DRY="$DRY" python3 - <<'PY'
import json, os
e = os.environ
starts = [l.split() for l in open(os.path.join(e["IN"], "starts.tsv")) if l.strip()]
json.dump({"session_id": e["SID"], "kind": e["KIND"], "exit_code": int(e["RC"]), "dry_run": e["DRY"] == "1",
           "cap_eur": float(e["CAP"]), "started": e["STARTED"].split(),
           "start_calls_unix_s": {r: float(t) for r, t, _ in starts}, "eur_per_hour": {r: float(p) for r, _, p in starts},
           "failed_step": e["STEP_FAIL"] or None, "kit_sha256": e["KIT_SHA"] or None,
           "bench_commit": e["BENCH_COMMIT"] or None, "worktree_changes": e["WT_CHANGES"] or None},
          open(os.path.join(e["IN"], "session.json"), "w"), indent=1)
PY
}
on_signal() { log "signal $1"; FINAL_RC=$2; [ -f "$IN/.cap_reached" ] && FINAL_RC=10; exit "$FINAL_RC"; }
trap cleanup EXIT
trap 'on_signal TERM 143' TERM
trap 'on_signal INT 130' INT
trap 'on_signal HUP 129' HUP

log "SESSION_START $SID kind=$KIND hosts=${ROLES[*]} cap=$CAP EUR dry_run=$DRY"

# ───────────── 1. preflight: nothing below starts a VM unless every check holds ─────────────
fail() { FINAL_RC=$1; shift; log "$*"; exit "$FINAL_RC"; }
for r in "${ROLES[@]}"; do
  [ "$r" = guest ] && [ "$OWNER_OK_GUEST" != 1 ] && \
    fail 2 "refused: the protected guest host $(var guest VM) starts only with the owner's OK (--owner-ok-guest-host)"
done
# the kit: the bench folder, committed (default) or as on disk, plus the optional extra folder
KIT=$IN/kit.tgz; STAGE=$(mktemp -d "${TMPDIR:-/tmp}/da-kit.XXXXXX")
mkdir -p "$STAGE/bench"
if [ "$KIT_FROM" = head ]; then
  BENCH_COMMIT=$(git -C "$BENCH_TREE" rev-parse HEAD 2>/dev/null) || fail 2 "no git tree at $BENCH_TREE"
  git -C "$BENCH_TREE" archive --format=tar HEAD "$BENCH_REL" | tar -x -C "$STAGE/bench" --strip-components=2 \
    || fail 2 "git archive of $BENCH_REL failed"
else
  BENCH_COMMIT=$(git -C "$BENCH_TREE" rev-parse HEAD 2>/dev/null || echo none)
  cp -a "$BENCH_TREE/$BENCH_REL/." "$STAGE/bench/" || fail 2 "copy of $BENCH_REL failed"
fi
WT_CHANGES=$(git -C "$BENCH_TREE" status --porcelain -- "$BENCH_REL" 2>/dev/null | wc -l)
[ -n "$KIT_EXTRA" ] && cp -a "$KIT_EXTRA" "$STAGE/bench/extra"
tar -czf "$KIT" -C "$STAGE" bench && rm -rf "$STAGE"
KIT_SHA=$(sha256sum "$KIT" | cut -d' ' -f1)
log "kit $KIT_SHA from $BENCH_TREE ($KIT_FROM, commit $BENCH_COMMIT, worktree changes in the bench folder: $WT_CHANGES)"
NEED=(session/remote/host_step.sh)
case "$KIND" in
  p10-1) NEED+=("$ENTRY_SCORE_P10_1") ;;
  p10-3) NEED+=("$ENTRY_GUEST_UP" "$ENTRY_GUEST_CLOCK" "$ENTRY_GUEST_CAPTURE" "$ENTRY_VXLAN" "$ENTRY_SCORE_START"
                "$ENTRY_SCORE_INJECT" "$ENTRY_SCORE_STOP" ${ENTRY_GUEST_PREPARE:+"$ENTRY_GUEST_PREPARE"}) ;;
  p10-2) NEED+=("$ENTRY_SIM_SETUP" "$ENTRY_SIM_WARMUP" "$ENTRY_SIM_RUN" "$ENTRY_SIM_RECORD" "$ENTRY_SCORE_START"
                "$ENTRY_SCORE_STOP" ${ENTRY_SIM_CALIBRATE:+"$ENTRY_SIM_CALIBRATE"})
         [ "$WITHOUT_GUEST" = 1 ] || NEED+=("$ENTRY_GUEST_UP" "$ENTRY_GUEST_CLOCK" "$ENTRY_GUEST_CAPTURE" "$ENTRY_VXLAN"
                                            ${ENTRY_GUEST_PREPARE:+"$ENTRY_GUEST_PREPARE"}) ;;
esac
MISSING=$(python3 - "$KIT" "${NEED[@]}" <<'PY'
import sys, tarfile
members = {m.name: m for m in tarfile.open(sys.argv[1]).getmembers()}
for rel in sys.argv[2:]:
    m = members.get("bench/" + rel)
    if m is None or not m.isfile():
        print("missing " + rel)
    elif not m.mode & 0o100:
        print("not executable " + rel)
PY
)
[ -z "$MISSING" ] || fail 2 "refused: entry points not ready in the kit: $(echo "$MISSING" | tr '\n' ';')"
log "entry points in the kit, executable: ${NEED[*]}"
for r in "${ROLES[@]}"; do
  st=$(vmst "$r")
  [ "$st" = TERMINATED ] || fail 2 "refused: $(var "$r" VM) is $st, expected TERMINATED (not adopting a VM this session did not start)"
done
# one GPU per project: no other GPU VM may run where this session starts one
for r in "${ROLES[@]}"; do
  [ "$r" = guest ] && continue
  OTHER=$(gc "$r" compute instances list --filter=status=RUNNING \
    --format='value(name,guestAccelerators[0].acceleratorType.basename())' 2>/dev/null | awk -F'\t' -v me="$(var "$r" VM)" '$2 != "" && $1 != me {print $1}')
  [ -z "$OTHER" ] || fail 2 "refused: GPU VM(s) running in $(var "$r" PROJECT): $OTHER (one GPU per project)"
done
EUR_H=0; for r in "${ROLES[@]}"; do EUR_H=$(awk -v a="$EUR_H" -v b="$(var "$r" EUR_H)" 'BEGIN{print a+b}'); done
CAP_S=$(awk -v c="$CAP" -v h="$EUR_H" 'BEGIN{printf "%d", c / h * 3600}')
log "preflight ok: hosts ${ROLES[*]} at $EUR_H EUR/h together; the cap of $CAP EUR is $CAP_S s of all of them"

# ───────────── 2. starts, in order, with rounds ─────────────
classify() {
  case "$1" in
    *STOCKOUT*|*ZONE_RESOURCE_POOL_EXHAUSTED*|*"does not have enough resources"*|*"resource pool exhausted"*) echo capacity ;;
    *QUOTA_EXCEEDED*|*[Qq]uota*) echo quota ;;
    *) echo other ;;
  esac
}
register_start() {   # before the start call: from here on the trap stops this VM
  local r=$1 x
  for x in "${STARTED[@]}"; do [ "$x" = "$r" ] && return 0; done
  STARTED+=("$r"); echo "$r $(date +%s.%N) $(var "$r" EUR_H)" >> "$STARTS"
}
start_watchdog() {
  ( trap - EXIT TERM INT HUP
    while sleep "$WATCH_S"; do
      c=$(cost_now); echo "$(date -u +%FT%TZ) cost $c EUR of cap $CAP EUR" >> "$COST"
      if ge "$c" "$CAP"; then
        echo "$(date -u +%FT%TZ) COST CAP reached: $c EUR >= $CAP EUR; ending the session" | tee -a "$LOG" >> "$COST"
        : > "$IN/.cap_reached"; kill -TERM "$MAIN_PID"; exit 0
      fi
    done ) 2> /dev/null &
  WD_PID=$!; disown "$WD_PID"
}
start_vm() {   # start_vm <role>: returns 0 when RUNNING (for the simulator host: still RUNNING after the check)
  local r=$1 vm zone deadline n=0 out rc st c i
  vm=$(var "$r" VM); zone=$(var "$r" ZONE); deadline=$(( $(date +%s) + START_DEADLINE_S ))
  while :; do
    n=$((n + 1))
    register_start "$r"
    [ -z "$WD_PID" ] && start_watchdog
    out=$(GC_TO=300 gc "$r" compute instances start "$vm" --zone "$zone" 2>&1); rc=$?   # never interrupted (SKB 13)
    st=$(vmst "$r")
    if [ "$st" != RUNNING ] && [ "$st" != TERMINATED ] && [ "$st" != UNKNOWN ]; then
      for i in $(seq 1 $(( RUNNING_WAIT_S / 10 + 1 ))); do st=$(vmst "$r"); [ "$st" = RUNNING ] && break; nap "$(( RUNNING_WAIT_S < 10 ? 1 : 10 ))"; done
    fi
    if [ "$st" = RUNNING ]; then
      log "start round $n of $vm: rc=$rc, RUNNING"
      if [ "$r" = sim ]; then
        log "preemption check: $vm must still be RUNNING in $PREEMPT_CHECK_S s"
        nap "$PREEMPT_CHECK_S"; st=$(vmst "$r")
        if [ "$st" != RUNNING ]; then
          log "$vm $st $PREEMPT_CHECK_S s after RUNNING (preempted)"
          [ "$(date +%s)" -ge "$deadline" ] && { log "start deadline reached"; return 3; }
          nap "$ROUND_PAUSE_S"; continue
        fi
        log "$vm still RUNNING after $PREEMPT_CHECK_S s"
      fi
      return 0
    fi
    c=$(classify "$out")
    case "$c" in
      capacity) log "start round $n of $vm: no capacity ($(echo "$out" | grep -o -E 'STOCKOUT|ZONE_RESOURCE_POOL_EXHAUSTED[A-Z_]*|not have enough resources' | head -1))" ;;
      quota) log "start of $vm: QUOTA error $(echo "$out" | grep -o -E "Quota '[A-Za-z0-9_-]+'" | head -1) (limit values not logged); no retry"; return 6 ;;
      *) log "start of $vm: error rc=$rc status $st, no retry: $(echo "$out" | one)"; return 6 ;;
    esac
    [ "$(date +%s)" -ge "$deadline" ] && { log "no capacity for $vm within $START_DEADLINE_S s ($n rounds)"; return 3; }
    nap "$ROUND_PAUSE_S"
  done
}
for r in "${ROLES[@]}"; do
  start_vm "$r"; rc=$?; [ "$rc" = 0 ] || fail "$rc" "session ends: $(var "$r" VM) not started"
done

# ───────────── 3. SSH, the kit, the safety net ─────────────
ssh_ready() {
  local r=$1 i
  for i in $(seq 1 "$SSH_TRIES"); do
    run_fg ssh_l "$r" 45 true > /dev/null 2>&1 && return 0   # gcloud's own exit code (SKB rule 5)
    nap "$SSH_PAUSE_S"
  done
  return 1
}
upload() {
  local r=$1 got gmin
  run_fg scp_r "$r" 300 "$KIT" "$(var "$r" VM):/tmp/da-kit-$SID.tgz" 2>&1 | one >> "$LOG"
  [ "${PIPESTATUS[0]}" = 0 ] || return 1
  got=$(run_fg ssh_l "$r" 120 "set -e; mkdir -p ~/da-kit/$SID; tar -xzf /tmp/da-kit-$SID.tgz -C ~/da-kit/$SID; echo $SID > ~/da-kit/$SID/session_id; sha256sum /tmp/da-kit-$SID.tgz" 2>/dev/null | awk 'NF==2 {print $1}' | tail -1)
  [ "$got" = "$KIT_SHA" ] || { log "kit on $(var "$r" VM): sha256 '$got', expected $KIT_SHA"; return 1; }
  # safety net: the VM powers itself off a little after the cap, should this host lose the session
  gmin=$(( CAP_S / 60 + SAFETY_MARGIN_MIN ))
  run_fg ssh_l "$r" 60 "sudo shutdown -h +$gmin > /dev/null 2>&1; echo safety-net-$gmin" 2>/dev/null | grep -q "safety-net-$gmin" \
    && log "$(var "$r" VM): kit ok, power-off safety net in $gmin min" \
    || log "WARNING $(var "$r" VM): safety net not confirmed (the watchdog and the trap still stop it)"
}
for r in "${ROLES[@]}"; do
  ssh_ready "$r" || fail 4 "no SSH to $(var "$r" VM)"
  upload "$r" || fail 4 "upload of the kit to $(var "$r" VM) failed"
done

# ───────────── 4. the steps of the session kind ─────────────
HS="bash \$HOME/da-kit/$SID/bench/session/remote/host_step.sh"
od() { echo "\$HOME/da-kit/$SID/out/$1"; }   # a step's output folder on the remote host
rstep() {   # rstep <role> <step> <timeout_s> <command...>: foreground step; a failure ends the session
  local r=$1 s=$2 to=$3; shift 3
  log "step $s on $(var "$r" VM): $*"
  run_fg ssh_l "$r" "$to" "$HS run $s -- $*" >> "$IN/$r.steps.out" 2>&1; local rc=$?
  log "step $s rc=$rc"
  [ "$rc" = 0 ] || { STEP_FAIL=$s; fetch_all; fail 5 "step $s failed (rc $rc)"; }
}
rstart() { local r=$1 s=$2; shift 2; log "start $s on $(var "$r" VM): $*"
  run_fg ssh_l "$r" 60 "$HS start $s -- $*" >> "$IN/$r.steps.out" 2>&1 || { STEP_FAIL=$s; fetch_all; fail 5 "start of $s failed"; }; }
rsignal() { run_fg ssh_l "$1" 60 "$HS signal $2 ${3:-INT}" >> "$IN/$1.steps.out" 2>&1; }
rwait() {   # rwait <role> <step> <timeout_s>: waits for a detached step's status
  local r=$1 s=$2 end st; end=$(( $(date +%s) + $3 ))
  while :; do
    st=$(run_fg ssh_l "$r" 60 "$HS status $s" 2>/dev/null | tail -1)
    case "$st" in "rc "*) log "step $s ${st}"; [ "$st" = "rc 0" ] && return 0; STEP_FAIL=$s; return 1 ;; esac
    [ "$(date +%s)" -ge "$end" ] && { log "step $s still ${st:-unknown} after $3 s"; STEP_FAIL=$s; return 1; }
    nap "$POLL_S"
  done
}
FETCHED=""
fetch() {   # fetch <role>: the host's output folder into incoming_<id>/<role>/, checked against this session's id
  local r=$1 sha got
  case " $FETCHED " in *" $r "*) return 0 ;; esac
  FETCHED="$FETCHED $r"
  sha=$(run_fg ssh_l "$r" 600 "$HS pack" 2>/dev/null | tail -1)
  mkdir -p "$IN/$r"
  run_fg scp_r "$r" 1200 "$(var "$r" VM):da-kit/$SID/out.tgz" "$IN/$r/" 2>&1 | one >> "$LOG"
  got=$(sha256sum "$IN/$r/out.tgz" 2>/dev/null | cut -d' ' -f1)
  [ -n "$got" ] && [ "$got" = "$sha" ] || { log "fetch from $(var "$r" VM) failed or changed (remote '$sha', local '$got')"; return 1; }
  tar -xzf "$IN/$r/out.tgz" -C "$IN/$r" || return 1
  [ "$(cat "$IN/$r/out/session_id" 2>/dev/null)" = "$SID" ] || { log "fetched files of $(var "$r" VM) are not this session's"; return 1; }
  log "fetched $(var "$r" VM): out.tgz $got"
}
fetch_all() { local r ok=0; for r in "${STARTED[@]}"; do fetch "$r" || ok=1; done; return $ok; }

case "$KIND" in
  p10-1)
    rstep score p10_1 "$T_P10_1" bash "$ENTRY_SCORE_P10_1" "$(od p10_1)"
    ;;
  p10-3|p10-2)
    if [ "$KIND" = p10-2 ]; then
      rstep sim sim_setup "$T_SIM_SETUP" bash "$ENTRY_SIM_SETUP" "$(od sim_setup)"
      CARLA_HOST=${CARLA_HOST:-$(vmip sim)}
      [ -n "$CARLA_HOST" ] || fail 5 "no internal IP of $(var sim VM)"
      log "CARLA host for the S-CORE side: $CARLA_HOST"
      # the bench network (brief R5): CARLA's port must answer from the S-CORE host before anything starts there
      rstep score carla_reach 60 timeout 10 bash -c "\"</dev/tcp/$CARLA_HOST/2000\""
    fi
    if [[ " ${ROLES[*]} " == *" guest "* ]]; then
      rstep guest guest_up "$T_GUEST_UP" bash "$ENTRY_GUEST_UP" "$(od guest_up)"
      [ -n "$ENTRY_GUEST_PREPARE" ] && rstep guest guest_prepare "$T_GUEST_UP" bash "$ENTRY_GUEST_PREPARE" "$(od guest_prepare)"
      GIP=$(vmip guest); SIP=$(vmip score)
      [ -n "$GIP" ] && [ -n "$SIP" ] || fail 5 "no internal IPs for the VXLAN (guest '$GIP', S-CORE '$SIP')"
      rstep guest vxlan_guest "$T_STEP" sudo bash "$ENTRY_VXLAN" guest-host add "$SIP"
      rstep score vxlan_score "$T_STEP" sudo bash "$ENTRY_VXLAN" host-half add "$GIP"
    fi
    rstep score score_start "$T_SCORE_START" bash "$ENTRY_SCORE_START" "$(od score)" "${CARLA_HOST:-none}"
    if [ "$KIND" = p10-2 ]; then
      # the lap rule: the warm-up runs with every camera, the recording view included, and its recorder must write
      rstart sim rec_warmup "$SIM_PY" "$ENTRY_SIM_RECORD" --out "$(od rec_warmup)"
      rstep sim warmup "$T_WARMUP" bash "$ENTRY_SIM_WARMUP" "$(od warmup)"
      rwait sim rec_warmup "$T_REC_END" || { fetch_all; fail 5 "the warm-up's recorder did not end well: no recorded run"; }
      # optional: the ASM-DRIVING-005/006 calibration runs of the calibration lane, before the recorded run
      [ -n "$ENTRY_SIM_CALIBRATE" ] && rstep sim calibrate "$T_RUN" bash "$ENTRY_SIM_CALIBRATE" "$(od calibrate)"
    fi
    if [[ " ${ROLES[*]} " == *" guest "* ]]; then
      rstep guest ivi_clock "$T_STEP" bash "$ENTRY_GUEST_CLOCK" set "$(od ivi_clock)"   # just before the window (R9)
      rstart guest capture bash "$ENTRY_GUEST_CAPTURE" start "$(od capture)"
    fi
    if [ "$KIND" = p10-3 ]; then
      rstep score inject "$T_INJECT" bash "$ENTRY_SCORE_INJECT" "$(od inject)"
    else
      rstart sim rec_run "$SIM_PY" "$ENTRY_SIM_RECORD" --out "$(od rec_run)"
      rstep sim run "$T_RUN" bash "$ENTRY_SIM_RUN" "$(od run)" "$P10_2_SCENARIO" "$P10_2_SETTING"
      rwait sim rec_run "$T_REC_END" || { fetch_all; fail 5 "the run's recorder did not end well"; }
    fi
    if [[ " ${ROLES[*]} " == *" guest "* ]]; then
      rstep guest capture_stop "$T_CAPTURE_END" bash "$ENTRY_GUEST_CAPTURE" stop "$(od capture)"
      rwait guest capture "$T_CAPTURE_END" || { fetch_all; fail 5 "the display capture did not end well"; }
    fi
    rstep score score_stop "$T_SCORE_START" bash "$ENTRY_SCORE_STOP" "$(od score)"
    ;;
esac
fetch_all || fail 5 "evidence fetch incomplete"
log "session steps done; the files are in $IN"
FINAL_RC=0
exit 0
