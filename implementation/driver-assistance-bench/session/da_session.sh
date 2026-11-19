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
#   --session-id <id>      default: UTC time stamp; letters, digits, '.', '_', '-', first a letter or digit
#   --evidence-root <dir>  default: ~/.hermes/outputs/inc-driving-002/phase10/sessions
#   --bench-tree <dir>     the repository whose bench folder is uploaded (default: this script's repository)
#   --kit-from-worktree    upload the bench folder as it is on disk (default: as committed at HEAD)
#   --kit-extra <dir>      also upload <dir> as <bench>/extra/ (stub entries in the dry-run tests)
#   --carla-host <ip>      CARLA's address for the S-CORE side (default: the simulator host's internal IP, from gcloud)
#   --remote-env NAME=VALUE  a per-session setting of a remote entry (repeatable): NAME must be on the allow-list
#                          (REMOTE_ENV_guest, REMOTE_ENV_score below); it goes to every step on that name's host and
#                          into session.json. Never taken from this shell's environment
#   --permissive-ivi       the IVI guest is set permissive (setenforce 0); every result of the session is then
#                          conditional on a permissive IVI, and session.json says so. Default: the guests as they
#                          boot (Enforcing); their mode is recorded at every window either way
#   --dry-run              use the fake gcloud in $DA_GCLOUD; print every command; shorter waits (DA_T_* knobs)
#
# Every internal IP comes from gcloud at run time; none is configured. SIM_SSH_IAP=1 (hosts.env) sends every ssh and
# scp to the simulator host through IAP.
#
# Start order: the G4 first, still RUNNING 30 s later, then the L4, then the guest host (rounds with short pauses
# while capacity is short). One GPU per project: a session refuses to start while another GPU VM runs in a project
# it starts a GPU VM in. The EXIT trap stops every VM this session started, on every exit, signals included: the
# guests first with cvd stop, then their host. A watchdog ends the session when the cost reaches the cap. Disks are
# never deleted; nothing is created or deleted.
#
# Exit codes: 0 done; 2 refused before any VM start; 3 no capacity or preempted; 4 SSH or upload failed; 5 a step
# failed; 6 start refused (quota or error); 9 dry run refused; 10 cost cap reached; 11 a VM left running (the guest
# host with its guests, or a stop not confirmed), in place of every other code (session.json keeps the code it
# replaced, the VMs' status after the session and the VMs left running); 129/130/143 signals.
set -uo pipefail
export LC_ALL=C   # awk and printf read and write decimal points
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
BENCH_REL=implementation/driver-assistance-bench
# shellcheck source=hosts.env
. "$HERE/hosts.env"
# shellcheck source=entrypoints.env
. "$HERE/entrypoints.env"

KIND=""; DRY=0; CAP=""; OWNER_OK_GUEST=0; WITHOUT_GUEST=0; SID=""; KIT_FROM=head; KIT_EXTRA=""; CARLA_HOST=""
IVI_PERMISSIVE=0; RENV_ARGS=()
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
    --permissive-ivi) IVI_PERMISSIVE=1; shift ;;
    --remote-env) RENV_ARGS+=("${2:?}"); shift 2 ;;
    -h|--help) sed -n '2,39p' "$0"; exit 0 ;;
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

# per-session settings of the remote entries (R6): only the names on its host's list below, and only when given on
# purpose with --remote-env NAME=VALUE (S4: an exported variable of the calling shell, another worker's UNIT_WAIT_S
# say, never reaches a step). Each goes to every step on that host (`env NAME=value` before the command) and into
# session.json, so a guessed pattern or a time-out is changed for the next session without a commit
REMOTE_ENV_guest="UNIT_REGISTERED_RE UNIT_NEGATION_RE BROKER_ERROR_RE UNIT_WAIT_S B12_DIR VERIFY_WAIT_S ADB_TIMEOUT_S
                  UP_TIMEOUT_S CLOCK_READS CLOCK_MAX_OFFSET_S START_WAIT_S"
REMOTE_ENV_score="DA_P10_1_CARLA_HOST GATEWAYD_RX_REGEX DA_P10_1_LATE_WAIT_S DA_P10_1_CUDA_RUNS DA_P10_1_ALIVE_HOLD_S
                  DA_P10_1_STALL_HOLD_S DA_P10_1_SUPERVISED_WAIT_S"
REMOTE_ENV_sim=""
declare -A RVAL=()
for _x in "${RENV_ARGS[@]}"; do
  [[ "$_x" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]] || { echo "refused: --remote-env takes NAME=VALUE, not '$_x'"; exit 2; }
  _n=${_x%%=*}
  [[ " $(echo $REMOTE_ENV_guest $REMOTE_ENV_score $REMOTE_ENV_sim) " == *" $_n "* ]] \
    || { echo "refused: --remote-env $_n is not on the allow-list: $(echo $REMOTE_ENV_guest $REMOTE_ENV_score $REMOTE_ENV_sim)"; exit 2; }
  [ -n "${RVAL[$_n]+x}" ] && { echo "refused: --remote-env $_n given twice"; exit 2; }
  RVAL[$_n]=${_x#*=}
done

# the cap: a positive number of EUR (R21)
[[ "$CAP" =~ ^[0-9]+(\.[0-9]+)?$ ]] && awk -v c="$CAP" 'BEGIN { exit !(c > 0) }' \
  || { echo "refused: --cap-eur must be a positive number of EUR, not '$CAP'"; exit 2; }

# waits, seconds; a dry run may shorten them through DA_T_<NAME>, a real session refuses those knobs
PREEMPT_CHECK_S=30; ROUND_PAUSE_S=45; START_DEADLINE_S=1800; RUNNING_WAIT_S=120; SSH_TRIES=20; SSH_PAUSE_S=10
# GO_LIMIT_S: the go must follow the S-CORE side's start within the candidate's 420 s ready time-out; the clock starts
# before the start step's own SSH call, and 40 s are kept for the go's SSH call (IAP to the G4, GO_SSH_S at most)
POLL_S=20; STEP_TERM_POLLS=6; GO_LIMIT_S=380; GO_SSH_S=35; WATCH_S=30; STOP_TRIES=30; STOP_POLL_S=10; SAFETY_MARGIN_MIN=10; STATUS_TRIES=5; STOP_AGAIN_EVERY=6
GUEST_NOSSH_S=180
T_P10_1=5400; T_GUEST_UP=2400; T_SCORE_START=900; T_SIM_SETUP=1200; T_WARMUP=900; T_RUN=900; T_INJECT=1200
T_CAPTURE_END=180; T_REC_END=200; T_STEP=300; T_CALIBRATE=1800; T_MAKE_H=600; T_READY=300; T_RELEASE=400
T_UNIT=300
KNOBS=(PREEMPT_CHECK_S ROUND_PAUSE_S START_DEADLINE_S RUNNING_WAIT_S SSH_TRIES SSH_PAUSE_S POLL_S WATCH_S STOP_TRIES
       STOP_POLL_S T_P10_1 T_GUEST_UP T_SCORE_START T_SIM_SETUP T_WARMUP T_RUN T_INJECT T_CAPTURE_END T_REC_END T_STEP
       T_CALIBRATE T_MAKE_H T_READY T_RELEASE T_UNIT STATUS_TRIES STOP_AGAIN_EVERY STEP_TERM_POLLS GO_LIMIT_S
       GUEST_NOSSH_S GO_SSH_S)
if [ "$DRY" = 1 ]; then
  GCLOUD=${DA_GCLOUD:-}
  [ -n "$GCLOUD" ] && [ -x "$GCLOUD" ] || { echo "dry run refused: DA_GCLOUD must name the fake gcloud"; exit 9; }
  case "$(readlink -f "$GCLOUD")" in
    "$(readlink -f "$HOME")"/google-cloud-sdk/*|*/google-cloud-sdk/bin/*) echo "dry run refused: $GCLOUD is a real gcloud"; exit 9 ;;
  esac
  for v in "${KNOBS[@]}"; do o="DA_T_$v"; [ -n "${!o:-}" ] && printf -v "$v" '%s' "${!o}"; done
  MAKE_H=${DA_MAKE_H:-}   # a stand-in for camera_calibration.py make-h (the fake capture files are no images)
else
  GCLOUD=$HOME/google-cloud-sdk/bin/gcloud
  for v in "${KNOBS[@]}"; do o="DA_T_$v"; [ -n "${!o:-}" ] && { echo "refused: $o is a dry-run knob"; exit 2; }; done
  [ -n "${DA_MAKE_H:-}" ] && { echo "refused: DA_MAKE_H is a dry-run knob"; exit 2; }
  MAKE_H=""
fi

SID=${SID:-$(date -u +%Y%m%dT%H%M%SZ)}
# the id goes unquoted into remote paths and commands (~/da-kit/<id>, mkdir, tar -C, the safety net's unit): letters,
# digits, '.', '_' and '-' only, never first a '.' or a '-' (S6)
[[ "$SID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || { echo "refused: session id '$SID' (allowed: ^[A-Za-z0-9][A-Za-z0-9._-]*\$)"; exit 2; }
IN=$EVID/incoming_$SID
[ -e "$IN" ] && { echo "refused: $IN exists (one folder per session)"; exit 2; }
# an archived session keeps its id in its folder's name (rule 15: incoming_<id> renamed to session<N>_..._<id>) or
# in its session.json: its id is never reused, or its remote ~/da-kit/<id> would pass this session's fetch (R20)
for _d in "$EVID"/*; do
  [ -d "$_d" ] || continue
  case "${_d##*/}" in
    "$SID"|*_"$SID") echo "refused: session id $SID is taken by $_d"; exit 2 ;;
  esac
  grep -q -F "\"session_id\": \"$SID\"" "$_d/session.json" 2>/dev/null && { echo "refused: session id $SID is taken by $_d"; exit 2; }
done
mkdir -p "$IN" || exit 2
LOG=$IN/session.log; CMDS=$IN/commands.log; COST=$IN/cost.log; STARTS=$IN/starts.tsv
: > "$STARTS"
exec 3>&1   # a dry run prints every command here, outside the command substitutions that capture output
# a broken stdout (the reader of `... | tee` gone with its terminal) must neither end the session nor lose a line of
# session.log (R3): SIGPIPE is ignored, every line goes to the file first, and a failed write to stdout is dropped
trap '' PIPE
MAIN_PID=$$; WD_PID=""; CHILD=""; STARTED=(); STEP_FAIL=""; FINAL_RC=""; ENDED_BY=""; UPLOADED=""; SCORE_UP=""
FETCHED=""; FETCH_OK=""; FETCH_BAD=""
GUEST_STEP_SENT=0   # 1 from the first step sent to the guest host on: from then on guests may run there (S1)
SCORE_RUN=""; STOPS=""; STOP_KILLED_LAST=""   # the run of the S-CORE side up; each of its stops: run:step:rc (S7)
CUR_STEP=""; GUEST_STEP_RUNNING=""   # "<role> <step>" of the step rstep waits for; a guest step alive after its TERM

log() { local l; l="$(date -u +%FT%TZ) $*"; printf '%s\n' "$l" >> "$LOG"; printf '%s\n' "$l" 2>/dev/null || true; }
say() { printf '%s\n' "$*" >&3 2>/dev/null || true; }   # a dry run's command line on stdout
# never log account e-mail addresses or quota limits
sanitize() { sed -E -e 's/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/<email>/g' -e '/[Ll][Ii][Mm][Ii][Tt]/d'; }
one() { sanitize | tr '\n' ' ' | tr -s ' ' | cut -c1-300; }
var() { local n="${1^^}_$2"; echo "${!n}"; }   # var <role> VM|PROJECT|ZONE|EUR_H
gc() {   # gc <role> <gcloud args...>: every call is printed (dry run) and kept in commands.log
  local role=$1; shift
  local p; p=$(var "$role" PROJECT)
  echo "$(date -u +%FT%T.%3NZ) + gcloud --configuration=$GCLOUD_CONFIGURATION --project=$p $*" >> "$CMDS"
  [ "$DRY" = 1 ] && say "+ gcloud --configuration=$GCLOUD_CONFIGURATION --project=$p $*"
  timeout "${GC_TO:-120}" "$GCLOUD" --configuration="$GCLOUD_CONFIGURATION" --project="$p" "$@"
}
vmst() { gc "$1" compute instances describe "$(var "$1" VM)" --zone "$(var "$1" ZONE)" --format='value(status)' 2>/dev/null || echo UNKNOWN; }
vmip() { gc "$1" compute instances describe "$(var "$1" VM)" --zone "$(var "$1" ZONE)" --format='value(networkInterfaces[0].networkIP)' 2>/dev/null; }
iap() { [ "$1" = sim ] && [ "$SIM_SSH_IAP" = 1 ] && echo --tunnel-through-iap; }   # D5: the simulator host by IAP
ssh_r() {   # ssh_r <role> <timeout_s> <remote command>
  local role=$1 to=$2 cmd=$3
  # shellcheck disable=SC2046  # iap prints one word or nothing
  timeout "$to" "$GCLOUD" --configuration="$GCLOUD_CONFIGURATION" --project="$(var "$role" PROJECT)" compute ssh \
    "$(var "$role" VM)" --zone "$(var "$role" ZONE)" $(iap "$role") --command "$cmd" < /dev/null
}
ssh_l() {   # logged ssh: the command goes to commands.log (and to stderr in a dry run)
  echo "$(date -u +%FT%T.%3NZ) + ssh $1: $3" >> "$CMDS"; [ "$DRY" = 1 ] && say "+ ssh $1: $3"
  ssh_r "$@"
}
scp_r() {   # scp_r <role> <timeout_s> <src...> <dst>
  local role=$1 to=$2; shift 2
  echo "$(date -u +%FT%T.%3NZ) + scp $role: $*" >> "$CMDS"; [ "$DRY" = 1 ] && say "+ scp $role: $*"
  # shellcheck disable=SC2046
  timeout "$to" "$GCLOUD" --configuration="$GCLOUD_CONFIGURATION" --project="$(var "$role" PROJECT)" compute scp \
    --zone "$(var "$role" ZONE)" $(iap "$role") "$@" < /dev/null
}
kill_tree() { local c; for c in $(pgrep -P "$1" 2>/dev/null); do kill_tree "$c"; done; kill "$1" 2>/dev/null; }
# a foreground call the main shell can leave at once: a signal interrupts the wait, and the trap ends the call's tree
# (kill_tree). Its subshell outlives a TERM or HUP sent to the whole process group until its own child has ended, so
# kill_tree still finds that child (timeout, gcloud: they run in timeout's own process group, which the group signal
# does not reach) instead of leaving it orphaned (R19)
run_fg() { ( trap 'exit 143' TERM HUP; "$@" ) & CHILD=$!; wait "$CHILD"; local rc=$?; CHILD=""; return $rc; }
nap() { run_fg sleep "$1"; }
# a remote call whose output the caller reads: into a file, never through a pipe or a command substitution, so a
# signal or the cap interrupts the wait at once instead of after the call (R19); ROUT holds its stdout
rout() { local f="$IN/.rout"; run_fg "$@" > "$f" 2>/dev/null; local rc=$?; ROUT=$(cat "$f" 2>/dev/null); rm -f "$f"; return $rc; }
routall() { local f="$IN/.rout"; run_fg "$@" > "$f" 2>&1; local rc=$?; ROUT=$(cat "$f" 2>/dev/null); rm -f "$f"; return $rc; }
cost_now() { awk -v now="$(date +%s.%N)" '{ s += (now - $2) * $3 / 3600 } END { printf "%.3f", s + 0 }' "$STARTS"; }
ge() { awk -v a="$1" -v b="$2" 'BEGIN { exit !(a >= b) }'; }
q() { printf ' %q' "$@"; }   # words quoted for the remote shell
GSTOP=${GUEST_STOP_CMD//\$DA_SESSION_ID/$SID}
# defined before the exit trap can run: a trap's fetch before the steps (the cap or a signal during the SSH and
# upload section) expanded an unset HS under set -u, and that fetch ended silently
HS="bash \$HOME/da-kit/$SID/bench/session/remote/host_step.sh"
od() { echo "\$HOME/da-kit/$SID/out/$1"; }   # a step's output folder on the remote host
crosvm_left() { run_fg ssh_l guest 60 "pgrep -c -x crosvm || true" 2>/dev/null | tail -1 | tr -dc 0-9; }
step_down() {   # in the trap: the step rstep waited for, if any: TERM on its host, its end awaited (bounded) (S2)
  [ -n "$CUR_STEP" ] || return 0
  local r=${CUR_STEP%% *} s=${CUR_STEP#* } i prc=0; CUR_STEP=""
  case " ${LOST:-} " in *" $r "*) return 0 ;; esac
  log "step $s still runs on $(var "$r" VM): TERM to it there, then its end (up to $STEP_TERM_POLLS polls), before any stop"
  rsignal "$r" "$s" TERM
  for i in $(seq 1 "$STEP_TERM_POLLS"); do
    rpoll "$r" "$HS status $s"; prc=$?
    [ "$prc" = 3 ] && break   # the host is gone (preempted): nothing runs there
    case "$ROUT" in "rc "*|absent) break ;; esac
    sleep "$POLL_S"
  done
  log "step $s after the TERM: ${ROUT:-unknown}"
  case "$ROUT" in "rc "*|absent) ;; *) [ "$prc" != 3 ] && [ "$r" = guest ] && GUEST_STEP_RUNNING=$s ;; esac
}

# the remote-step helpers, defined before the exit trap can run: a trap during the starts or the SSH and upload
# section (a signal, the cap) called score_down and fetch before their definitions ("command not found"), and an
# uploaded host was stopped unfetched
host_lost() {   # host_lost <role> <status>: a host gone mid-session (preempted): no fetch, no more polls (R12)
  log "$(var "$1" VM) is $2 during the session (preempted or stopped): its files stay on its disk"
  LOST="${LOST:-} $1"; FETCHED="$FETCHED $1"; FETCH_BAD="$FETCH_BAD $1"; ENDED_BY="host lost: $1 ($2)"
  [ "$1" = score ] && SCORE_UP=""
}
rpoll() {   # rpoll <role> <remote command>: one short poll, its last line in ROUT; 3 when the host is gone (R12)
  local st
  if rout ssh_l "$1" 60 "$2"; then ROUT=$(tail -1 <<< "$ROUT"); return 0; fi
  ROUT=""; st=$(vmst "$1")
  case "$st" in TERMINATED|STOPPING|STOPPED|SUSPENDING|SUSPENDED) host_lost "$1" "$st"; return 3 ;; esac
  return 1
}
rstep() {   # rstep <role> <step> <timeout_s> <command...>: a step, detached on its host and polled; a failure ends
  # the session. No SSH call lasts longer than a poll, so a dropped connection or this host's time-out never leaves
  # a step running on unseen: at the time-out the step is signalled on its host and its end awaited (R10)
  local r=$1 s=$2 to=$3; shift 3
  log "step $s on $(var "$r" VM): $*"; SEQ+=("$r:$s")
  local end=$(( $(date +%s) + to )) rc="" absent=0 i
  [ "$r" = guest ] && GUEST_STEP_SENT=1
  CUR_STEP="$r $s"   # from before its start call: an answer lost on the way may still have started it
  routall ssh_l "$r" 60 "$HS start $s -- $(renv "$r")$*"; printf '%s\n' "$ROUT" >> "$IN/$r.steps.out"
  while :; do   # a start whose answer was lost may still have started: the status decides
    rpoll "$r" "$HS status $s"
    [ $? = 3 ] && { STEP_FAIL=$s; abort 3 "step $s: $(var "$r" VM) is gone"; }
    case "$ROUT" in
      "rc "*) rc=${ROUT#rc }; CUR_STEP=""; break ;;
      absent) absent=$((absent + 1)); [ "$absent" -ge 3 ] && { rc=255; CUR_STEP=""; log "step $s never started"; break; } ;;
    esac
    if [ "$(date +%s)" -ge "$end" ]; then
      log "step $s still ${ROUT:-unknown} after $to s: TERM to the step on its host, then its end"
      rsignal "$r" "$s" TERM
      for i in $(seq 1 "$STEP_TERM_POLLS"); do
        rpoll "$r" "$HS status $s"; case "$ROUT" in "rc "*) CUR_STEP=""; break ;; esac; nap "$POLL_S"
      done
      # a step still alive stays in CUR_STEP: the trap sends it TERM again and waits once more before any stop
      log "step $s after the TERM: ${ROUT:-unknown}"; rc=124; break
    fi
    nap "$POLL_S"
  done
  rout ssh_l "$r" 60 "$HS tail $s"; printf '%s\n' "$ROUT" >> "$IN/$r.steps.out"
  log "step $s rc=$rc"
  # every stop of the S-CORE side has run its collection, whatever its code; each is recorded per run (S7)
  case "$s" in score_stop*) SCORE_UP=""; STOPS="$STOPS ${SCORE_RUN:-none}:$s:$rc" ;; esac
  if [ "$rc" = 7 ] && [[ "$s" == score_stop* ]]; then
    # stop_score_side.sh exit 7: stopped and collected, something had to be killed. Not a failure; recorded
    # (session.json score_stops, stop_killed). Exit 8, collection failed, stays a failure (the lead's decision)
    log "step $s rc=7: the S-CORE side of ${SCORE_RUN:-none} stopped and its records collected, but something had to be killed (stop_killed, recorded; not a failure)"
    STOP_KILLED_LAST=$s; return 0
  fi
  if [ "$rc" != 0 ]; then
    STEP_FAIL=$s; abort 5 "step $s failed (rc $rc)"
  fi
}
rstart() { local r=$1 s=$2; shift 2; log "start $s on $(var "$r" VM): $*"; SEQ+=("$r:$s&")
  [ "$r" = guest ] && GUEST_STEP_SENT=1
  run_fg ssh_l "$r" 60 "$HS start $s -- $(renv "$r")$*" >> "$IN/$r.steps.out" 2>&1 || { STEP_FAIL=$s; abort 5 "start of $s failed"; }; }
rsignal() { run_fg ssh_l "$1" 60 "$HS signal $2 ${3:-INT}" >> "$IN/$1.steps.out" 2>&1; }
rwait() {   # rwait <role> <step> <timeout_s>: waits for a detached step's status
  local r=$1 s=$2 end st; end=$(( $(date +%s) + $3 )); SEQ+=("$r:wait-$s")
  while :; do
    rpoll "$r" "$HS status $s"; [ $? = 3 ] && { STEP_FAIL=$s; return 1; }; st=$ROUT
    case "$st" in "rc "*) log "step $s ${st}"; [ "$st" = "rc 0" ] && return 0; STEP_FAIL=$s; return 1 ;; esac
    [ "$(date +%s)" -ge "$end" ] && { log "step $s still ${st:-unknown} after $3 s"; STEP_FAIL=$s; return 1; }
    nap "$POLL_S"
  done
}
rwaitfile() {   # rwait_file <role> <step> <remote file> <timeout_s>: the file of a running detached step
  local r=$1 s=$2 f=$3 end st; end=$(( $(date +%s) + $4 )); SEQ+=("$r:file-${f##*/}")
  while :; do
    rpoll "$r" "test -e $f && echo present || $HS status $s"; [ $? = 3 ] && { STEP_FAIL=$s; return 1; }; st=$ROUT
    case "$st" in
      present) log "step $s: ${f##*/} present"; return 0 ;;
      "rc "*) log "step $s ended ($st) before ${f##*/}"; STEP_FAIL=$s; return 1 ;;
    esac
    [ "$(date +%s)" -ge "$end" ] && { log "step $s: no ${f##*/} after $4 s"; STEP_FAIL=$s; return 1; }
    nap "$POLL_S"
  done
}
rtouch() {   # rtouch <role> <remote file> [<timeout_s>]: a handshake file of the world side
  log "touch ${2##*/} on $(var "$1" VM): $2"; SEQ+=("$1:touch-${2##*/}")
  rout ssh_l "$1" "${3:-60}" "touch $2 && echo touched"; [[ "$ROUT" == *touched* ]]
}
fetch() {   # fetch <role>: the host's output folder into incoming_<id>/<role>/, checked against this session's id
  local r=$1 sha got
  case " $FETCHED " in *" $r "*) return 0 ;; esac
  FETCHED="$FETCHED $r"
  fetch_one "$r" && { FETCH_OK="$FETCH_OK $r"; return 0; }
  FETCH_BAD="$FETCH_BAD $r"; return 1
}
fetch_one() {
  local r=$1 sha got
  rout ssh_l "$r" "${FETCH_PACK_TO:-600}" "$HS pack"; sha=$(tail -1 <<< "$ROUT")
  mkdir -p "$IN/$r"
  routall scp_r "$r" "${FETCH_SCP_TO:-1200}" "$(var "$r" VM):da-kit/$SID/out.tgz" "$IN/$r/"
  printf '%s\n' "$ROUT" | one >> "$LOG"
  got=$(sha256sum "$IN/$r/out.tgz" 2>/dev/null | cut -d' ' -f1)
  [ -n "$got" ] && [ "$got" = "$sha" ] || { log "fetch from $(var "$r" VM) failed or changed (remote '$sha', local '$got')"; return 1; }
  tar -xzf "$IN/$r/out.tgz" -C "$IN/$r" || return 1
  [ "$(cat "$IN/$r/out/session_id" 2>/dev/null)" = "$SID" ] || { log "fetched files of $(var "$r" VM) are not this session's"; return 1; }
  log "fetched $(var "$r" VM): out.tgz $got"
  return 0
}
score_down() {   # the S-CORE side, if this session started it and has not stopped it: its stop is its only collector (R8)
  [ -n "$SCORE_UP" ] || return 0
  local o=$SCORE_UP rc; SCORE_UP=""
  log "the S-CORE side is up ($o): its stop, which collects its records, before the fetch"
  run_fg ssh_l score "${T_SCORE_DOWN:-$T_SCORE_START}" "$HS run score_stop_on_failure -- $(renv score)bash $ENTRY_SCORE_STOP $o" \
    >> "$IN/score.steps.out" 2>&1; rc=$?
  log "step score_stop_on_failure rc=$rc$([ "$rc" = 7 ] && echo ": stopped and collected, something had to be killed (stop_killed, recorded)")"
  STOPS="$STOPS ${SCORE_RUN:-none}:score_stop_on_failure:$rc"
}
abort() {   # a failure after the starts: the S-CORE side's stop, the fetch, the exit (3 when a host was lost)
  local code=$1; shift
  [ -n "${LOST:-}" ] && code=3
  score_down; fetch_all; fail "$code" "$*"
}
fetch_all() { local r ok=0; for r in "${STARTED[@]}"; do fetch "$r" || ok=1; done; return $ok; }
ipof() {   # ipof <role> <var>: the internal IP, read from gcloud now (never configured: D5 may move the hosts)
  local ip; ip=$(vmip "$1"); [ -n "$ip" ] || abort 5 "no internal IP of $(var "$1" VM) from gcloud"
  IPS="${IPS:-} $1=$ip"; printf -v "$2" '%s' "$ip"
}


# ───────────── exit trap: stop what this session started ─────────────
cleanup() {
  local rc=$? r st i
  # no signal ends the trap before its stops (R1): a second Ctrl-C, HUP or TERM, or the watchdog's TERM, is ignored
  # here, and the trap runs on to the guests' stop, their host's stop and session.json
  trap '' INT TERM HUP
  trap - EXIT
  [ -n "$FINAL_RC" ] && rc=$FINAL_RC
  [ -f "$IN/.cap_reached" ] && rc=10
  [ -n "$WD_PID" ] && { pkill -P "$WD_PID" 2>/dev/null; kill "$WD_PID" 2>/dev/null; }
  [ -n "$CHILD" ] && kill_tree "$CHILD"   # an interrupted SSH step: its local client and timeout too
  # the step still running on its host (a signal or the cap during it): TERM to it there, and its end awaited, before
  # the S-CORE side's stop and any stop; a guest launch never races the guests' stop (S2)
  step_down
  [ -f "$IN/.cap_reached" ] && ENDED_BY=cap
  [ -n "$ENDED_BY" ] || ENDED_BY="exit $rc"
  # the S-CORE side's stop, its only collector, while the world may still tick (R8); then, bounded, the fetch of
  # every host whose evidence was not fetched yet (a signal, the cap), before any stop (R13)
  T_SCORE_DOWN=120 score_down
  for r in $UPLOADED; do
    case " $FETCHED " in *" $r "*) continue ;; esac
    log "fetching $(var "$r" VM) before its stop (bounded)"
    FETCH_PACK_TO=120 FETCH_SCP_TO=300 fetch "$r"
  done
  local gpu=() guest=0
  for r in "${STARTED[@]}"; do if [ "$r" = guest ]; then guest=1; else gpu+=("$r"); fi; done
  # the GPU hosts first (they cost most), without waiting
  for r in "${gpu[@]}"; do
    log "stopping $(var "$r" VM) ($r)"
    GC_TO=300 gc "$r" compute instances stop "$(var "$r" VM)" --zone "$(var "$r" ZONE)" --async --quiet 2>&1 | one >> "$LOG"
  done
  if [ "$guest" = 1 ]; then
    [ -n "$GUEST_STEP_RUNNING" ] && log "step $GUEST_STEP_RUNNING may still run on $(var guest VM) after its TERM: the guests' stop, and the host is kept whatever the count"
    # a failed status read is read again; only a stopped host counts as "no guests" (R2)
    for i in $(seq 1 "$STATUS_TRIES"); do
      st=$(vmst guest); [ "$st" != UNKNOWN ] && break
      log "status read of $(var guest VM) failed (try $i of $STATUS_TRIES)"; sleep "$STOP_POLL_S"
    done
    local left="" try out
    case "$st" in
      TERMINATED|STOPPING|STOPPED|SUSPENDING|SUSPENDED)
        log "guest host status $st: no guest can run there"; left=0 ;;
      *)
        # RUNNING, or any other status, a status still unknown included: the guests' stop, then this session's own
        # check that no crosvm is left; never a stop of the host with guests running, and never one without this
        # session's crosvm count of 0 (lead answer B13.3; the guest-prep-20261118 operator's route)
        [ "$st" = RUNNING ] || log "guest host status $st: the guests' stop all the same, and the host only after a crosvm count of 0"
        local ssh_ok=1 t_end
        if [ "$GUEST_STEP_SENT" = 0 ]; then
          # no guest step went out, so no guest can run there unless its image starts Cuttlefish at boot, which it
          # does not (assumption, checked once by the operator: README, the P10-3 block). Without SSH the host
          # would stay up, unarmed and billing (S1): SSH is tried for a bounded time, then the host is stopped
          ssh_ok=0; t_end=$(( $(date +%s) + GUEST_NOSSH_S ))
          while :; do
            run_fg ssh_l guest 45 true > /dev/null 2>&1 && { ssh_ok=1; break; }
            [ "$(date +%s)" -ge "$t_end" ] && break
            sleep "$SSH_PAUSE_S"
          done
          if [ "$ssh_ok" = 0 ]; then
            log "GUEST HOST STOPPED WITHOUT A CROSVM COUNT: $(var guest VM) never answered SSH within $GUEST_NOSSH_S s in the trap and got no guest step from this session, so no guest can run there (assumption: nothing on its image starts Cuttlefish at boot)"
            left=0
          fi
        fi
        [ "$ssh_ok" = 1 ] && for try in 1 2; do
          log "stopping the guests before their host (try $try): $GSTOP"
          out=$(ssh_l guest 300 "$GSTOP" 2>&1); echo "$out" | sanitize >> "$IN/guest_stop.out"
          left=$(crosvm_left)
          log "crosvm processes left on $(var guest VM): ${left:-unknown}"
          [ "$left" = 0 ] && break
        done ;;
    esac
    if [ "$left" = 0 ] && [ -z "$GUEST_STEP_RUNNING" ]; then
      log "stopping $(var guest VM) (guest)"
      GC_TO=300 gc guest compute instances stop "$(var guest VM)" --zone "$(var guest ZONE)" --async --quiet 2>&1 | one >> "$LOG"
    else
      if [ -n "$GUEST_STEP_RUNNING" ]; then
        log "GUEST HOST LEFT RUNNING: step $GUEST_STEP_RUNNING did not end after its TERM (crosvm '${left:-unknown}'). End it, stop the guests by hand (cvd stop, no crosvm left), then the host"
      else
        log "GUEST HOST LEFT RUNNING: the guests did not stop (crosvm '${left:-unknown}'). Stop them by hand (cvd stop, no crosvm left), then the host"
      fi
      GUEST_LEFT=1
    fi
  fi
  # every VM this session started must read TERMINATED; one that does not is stopped again every few polls, and
  # a VM left running overrides every other exit code with 11 (R4)
  LEFT_RUNNING=""; VM_AFTER=""
  for r in "${STARTED[@]}"; do
    if [ "$r" = guest ] && [ "${GUEST_LEFT:-0}" = 1 ]; then
      st=$(vmst guest); log "status after the session: $(var guest VM) $st (left running)"
      LEFT_RUNNING="$LEFT_RUNNING $(var guest VM)"; VM_AFTER="$VM_AFTER $r=$st"; continue
    fi
    for i in $(seq 1 "$STOP_TRIES"); do
      st=$(vmst "$r"); [ "$st" = TERMINATED ] && break
      if [ $(( i % STOP_AGAIN_EVERY )) = 0 ]; then
        log "$(var "$r" VM) still $st: stop call again"
        GC_TO=300 gc "$r" compute instances stop "$(var "$r" VM)" --zone "$(var "$r" ZONE)" --async --quiet 2>&1 | one >> "$LOG"
      fi
      sleep "$STOP_POLL_S"
    done
    log "status after stop: $(var "$r" VM) $st"
    VM_AFTER="$VM_AFTER $r=$st"
    [ "$st" = TERMINATED ] || { log "STOP NOT CONFIRMED for $(var "$r" VM): stop it by hand now"; LEFT_RUNNING="$LEFT_RUNNING $(var "$r" VM)"; }
  done
  RC_STEPS=$rc
  [ -n "$LEFT_RUNNING" ] && rc=11
  [ -s "$STARTS" ] && echo "$(date -u +%FT%TZ) final cost $(cost_now) EUR of cap $CAP EUR (upper bound: from each start call to now)" | tee -a "$COST" >> "$LOG"
  # every VM of both projects, after the session (SKB: list both projects after every session)
  for p in $(for r in sim score guest; do var "$r" PROJECT; done | sort -u); do
    echo "$(date -u +%FT%T.%3NZ) + gcloud --project=$p compute instances list" >> "$CMDS"
    [ "$DRY" = 1 ] && say "+ gcloud --configuration=$GCLOUD_CONFIGURATION --project=$p compute instances list"
    "$GCLOUD" --configuration="$GCLOUD_CONFIGURATION" --project="$p" compute instances list \
      --format='value(name,zone.basename(),status)' 2>/dev/null | sed "s/^/VM after session [$p]: /" >> "$LOG"
  done
  [ "$KIND" = p10-1 ] && [ -n "$UPLOADED" ] && p10_1_report
  write_record "$rc"
  log "SESSION_END $SID rc=$rc"
  [ -n "$LEFT_RUNNING" ] && log "VMS LEFT RUNNING, THEY BILL: STOP THEM BY HAND NOW:$LEFT_RUNNING (exit 11 in place of $RC_STEPS)"
  exit "$rc"
}
p10_1_report() {   # a p10-1 session judges only the checks that need the S-CORE host alone: which of the 8 did not run
  # or failed, from the fetched p10_1_verdicts.json, in one line of session.log and in session.json (p10_1)
  local f=$IN/score/out/p10_1/p10_1_verdicts.json line
  line=$(python3 - "$f" "$IN/p10_1_summary.json" <<'PY'
import json, sys
ids = ["C%d" % i for i in range(1, 9)]
try:
    rows = json.load(open(sys.argv[1], encoding="utf-8"))["checks"]
    found = True
except (OSError, ValueError, KeyError, TypeError):
    rows, found = [], False
by = {}
for r in rows:
    by.setdefault(str(r.get("check", "")).split("_", 1)[0], r)
def name(k):
    return by[k]["check"] if k in by else k + " (no verdict)"
not_run = [name(k) for k in ids if k not in by or by[k].get("verdict") == "NOT RUN"]
failed = [name(k) for k in ids if k in by and by[k].get("verdict") == "FAIL"]
passed = [name(k) for k in ids if k in by and by[k].get("verdict") == "PASS"]
line = "P10-1: %d of 8 checks NOT RUN" % len(not_run) + (": " + ", ".join(not_run) if not_run else "")
if failed:
    line += "; FAIL: " + ", ".join(failed)
if not found:
    line += "; no p10_1_verdicts.json fetched"
ok = not not_run and not failed and found
line += "; P10-1 passed" if ok else "; P10-1 NOT passed"
json.dump({"line": line, "verdicts_file_fetched": found, "not_run": not_run, "fail": failed, "pass": passed,
           "passed": ok}, open(sys.argv[2], "w"), indent=1)
print(line)
PY
)
  log "$line"
}
write_record() {
  # the hosts not fetched, computed before the assignments below: one of them, STARTED="${STARTED[*]}", turns the
  # array into one word for the rest of that command, and the loop then read "sim score" as one host
  local nf r; nf="$FETCH_BAD $(for r in "${STARTED[@]}"; do case " $FETCHED " in *" $r "*) ;; *) echo "$r" ;; esac; done)"
  KIND="$KIND" SID="$SID" RC="$1" CAP="$CAP" IN="$IN" STARTED="${STARTED[*]}" STEP_FAIL="$STEP_FAIL" \
  KIT_SHA="${KIT_SHA:-}" BENCH_COMMIT="${BENCH_COMMIT:-}" WT_CHANGES="${WT_CHANGES:-}" DRY="$DRY" \
  IAP="$SIM_SSH_IAP" PERM="$IVI_PERMISSIVE" IPS="${IPS:-}" CAMCAL="${CAMCAL_SHA:-}" VM_AFTER="${VM_AFTER:-}" \
  LEFT="${LEFT_RUNNING:-}" RC_STEPS="${RC_STEPS:-$1}" RECEIPTS="${RECEIPTS:-}" \
  FETCH_OK="$FETCH_OK" FETCH_BAD="$nf" \
  ENDED_BY="$ENDED_BY" STOPS="$STOPS" \
  RENV="$(for x in $REMOTE_ENV_SET; do n=${x#*:}; printf '%s\t%s\t%s\n' "${x%%:*}" "$n" "${RVAL[$n]}"; done)" python3 - <<'PY'
import json, os
e = os.environ
p10_1 = os.path.join(e["IN"], "p10_1_summary.json")
ips = dict(x.split("=", 1) for x in e["IPS"].split() if "=" in x)
starts = [l.split() for l in open(os.path.join(e["IN"], "starts.tsv")) if l.strip()]
renv = {}
for line in e["RENV"].splitlines():
    role, name, value = (line.split("\t", 2) + ["", ""])[:3]
    renv.setdefault(role, {})[name] = value
json.dump({"session_id": e["SID"], "kind": e["KIND"], "exit_code": int(e["RC"]), "dry_run": e["DRY"] == "1",
           "cap_eur": float(e["CAP"]), "started": e["STARTED"].split(),
           "start_calls_unix_s": {r: float(t) for r, t, _ in starts}, "eur_per_hour": {r: float(p) for r, _, p in starts},
           "failed_step": e["STEP_FAIL"] or None, "kit_sha256": e["KIT_SHA"] or None,
           "bench_commit": e["BENCH_COMMIT"] or None, "worktree_changes": e["WT_CHANGES"] or None,
           "sim_ssh_iap": e["IAP"] == "1", "internal_ips_from_gcloud": ips,
           "camera_calibration_sha256": dict(x.split("=", 1) for x in e["CAMCAL"].split() if "=" in x) or None,
           "conditional_on_permissive_ivi": e["PERM"] == "1",
           "vm_status_after": dict(x.split("=", 1) for x in e["VM_AFTER"].split() if "=" in x),
           "left_running": e["LEFT"].split(), "exit_code_without_left_running": int(e["RC_STEPS"]),
           "remote_env": renv, "fetched": e["FETCH_OK"].split(), "not_fetched": e["FETCH_BAD"].split(),
           "ended_by": e["ENDED_BY"] or None,
           "score_stops": {run: {"step": step, "rc": int(rc) if rc.lstrip("-").isdigit() else None,
                                 "stop_killed": rc == "7"}
                           for run, step, rc in (x.split(":", 2) for x in e["STOPS"].split())},
           "p10_1": json.load(open(p10_1)) if os.path.exists(p10_1) else None,
           "app_record_receipts": {w: (int(n) if n.isdigit() else None)
                                   for w, n in (x.split("=", 1) for x in e["RECEIPTS"].split() if "=" in x)}},
          open(os.path.join(e["IN"], "session.json"), "w"), indent=1)
PY
}
on_signal() {
  trap '' INT TERM HUP; log "signal $1"; FINAL_RC=$2; ENDED_BY="signal $1"
  [ -f "$IN/.cap_reached" ] && { FINAL_RC=10; ENDED_BY=cap; }
  exit "$FINAL_RC"
}
trap cleanup EXIT
trap 'on_signal TERM 143' TERM
trap 'on_signal INT 130' INT
trap 'on_signal HUP 129' HUP

log "SESSION_START $SID kind=$KIND hosts=${ROLES[*]} cap=$CAP EUR dry_run=$DRY sim_ssh_iap=$SIM_SSH_IAP permissive_ivi=$IVI_PERMISSIVE"
[ "$IVI_PERMISSIVE" = 1 ] && log "every result of this session is conditional on a permissive IVI (--permissive-ivi)"

# the --remote-env settings, per host, in the order of its list
REMOTE_ENV_SET=""
for _r in guest score sim; do
  _l="REMOTE_ENV_$_r"; _a=()
  for _n in ${!_l}; do
    [ -n "${RVAL[$_n]+x}" ] || continue
    _a+=("$_n=${RVAL[$_n]}"); REMOTE_ENV_SET="$REMOTE_ENV_SET $_r:$_n"
  done
  if [ ${#_a[@]} -gt 0 ]; then printf -v "RENV_$_r" '%s ' "env$(q "${_a[@]}")"; else printf -v "RENV_$_r" '%s' ""; fi
done
renv() { local n="RENV_$1"; printf '%s' "${!n}"; }
[ -n "$REMOTE_ENV_SET" ] && log "per-session settings for the remote entries:$REMOTE_ENV_SET (values in session.json)"

# ───────────── 1. preflight: nothing below starts a VM unless every check holds ─────────────
fail() {
  FINAL_RC=$1; shift
  [ -n "$ENDED_BY" ] || ENDED_BY=${STEP_FAIL:+step $STEP_FAIL}
  [ -n "$ENDED_BY" ] || ENDED_BY="exit $FINAL_RC: $*"
  log "$*"; exit "$FINAL_RC"
}
for r in "${ROLES[@]}"; do
  [ "$r" = guest ] && [ "$OWNER_OK_GUEST" != 1 ] && \
    fail 2 "refused: the protected guest host $(var guest VM) starts only with the owner's OK (--owner-ok-guest-host)"
  # guest_up.sh creates the guests fresh, and fresh guests start empty: the app and its ACLs go on every session
  [ "$r" = guest ] && [ -z "$ENTRY_GUEST_PREPARE" ] && \
    fail 2 "refused: ENTRY_GUEST_PREPARE is empty, but fresh guests start without the app and its ACLs"
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
if [ "$KIND" = p10-2 ]; then
  # the camera calibration: upstream's files at the pin, and a Python with OpenCV for make-h on this host
  [ -n "$ENTRY_SIM_CALIBRATE" ] || fail 2 "refused: p10-2 needs ENTRY_SIM_CALIBRATE (the candidate reads the H.yaml it leads to)"
  for f in Calibration/checkerboard-bw-4x4.png Calibration/calc_front_camera_homography.py \
           VisionPilot/scripts/find_homography_C_matrix.py; do
    git -C "$VP_CLONE" cat-file -e "$VP_PIN:$f" 2>/dev/null || fail 2 "refused: $f is not at $VP_PIN in VP_CLONE=$VP_CLONE"
  done
  mkdir -p "$STAGE/bench/session-inputs"
  git -C "$VP_CLONE" show "$VP_PIN:Calibration/checkerboard-bw-4x4.png" > "$STAGE/bench/session-inputs/checkerboard-bw-4x4.png" \
    || fail 2 "refused: cannot take the checkerboard from $VP_CLONE"
  log "checkerboard into the kit from $VP_PIN: $(sha256sum "$STAGE/bench/session-inputs/checkerboard-bw-4x4.png" | cut -d' ' -f1)"
  if [ -n "$MAKE_H" ]; then log "dry run: make-h stand-in $MAKE_H (no OpenCV check)"
  else
    CVV=$("$CV_PY" -c 'import cv2, numpy; print(cv2.__version__, numpy.__version__)' 2>/dev/null) \
      || fail 2 "refused: CV_PY=$CV_PY has no OpenCV and numpy for make-h"
    log "make-h on this host with $CV_PY (OpenCV, numpy $CVV)"
  fi
fi
tar -czf "$KIT" -C "$STAGE" bench && rm -rf "$STAGE"
KIT_SHA=$(sha256sum "$KIT" | cut -d' ' -f1)
log "kit $KIT_SHA from $BENCH_TREE ($KIT_FROM, commit $BENCH_COMMIT, worktree changes in the bench folder: $WT_CHANGES)"
NEED=(session/remote/host_step.sh session/remote/safety_net.sh)
GUEST_NEED=("$ENTRY_GUEST_UP" "$ENTRY_GUEST_PREPARE" "$ENTRY_GUEST_APP_RESTART" "$ENTRY_GUEST_OFFER_CHECK"
            "$ENTRY_GUEST_CLOCK" "$ENTRY_GUEST_CAPTURE" "$ENTRY_VXLAN" session/remote/guest_stop.sh)
case "$KIND" in
  p10-1) NEED+=("$ENTRY_SCORE_P10_1") ;;
  p10-3) NEED+=("${GUEST_NEED[@]}" "$ENTRY_SCORE_START" "$ENTRY_SCORE_INJECT" "$ENTRY_SCORE_STOP") ;;
  p10-2) NEED+=("$ENTRY_SIM_SETUP" "$ENTRY_SIM_WARMUP" "$ENTRY_SIM_CALIBRATE" "$ENTRY_SIM_RUN" "$ENTRY_SIM_RECORD"
                "$ENTRY_SCORE_START" "$ENTRY_SCORE_STOP" world-side/da_world_side.py world-side/camera_calibration.py)
         [ "$WITHOUT_GUEST" = 1 ] || NEED+=("${GUEST_NEED[@]}") ;;
esac
MISSING=$(python3 - "$KIT" "${NEED[@]}" <<'PY'
import sys, tarfile
members = {m.name: m for m in tarfile.open(sys.argv[1]).getmembers()}
for rel in sys.argv[2:]:
    m = members.get("bench/" + rel)
    if m is None or not m.isfile():
        print("missing " + rel)
    elif not m.mode & 0o100 and not rel.endswith(".py"):
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
pstart() { local s; s=$(cat "/proc/$1/stat" 2>/dev/null) || return 1; s=${s##*) }; set -- $s; echo "${20}"; }
MAIN_START=$(pstart "$MAIN_PID")
# the session itself, not a later process with its PID number (the start time in /proc/<pid>/stat, field 22)
main_alive() { if [ -n "$MAIN_START" ]; then [ "$(pstart "$MAIN_PID")" = "$MAIN_START" ]; else kill -0 "$MAIN_PID" 2>/dev/null; fi; }
start_watchdog() {
  # ends with the session, even one killed without its trap (SIGKILL, the OOM killer), and never signals a PID
  # that is no longer the session's (R5)
  ( trap - EXIT TERM INT HUP
    while sleep "$WATCH_S"; do
      main_alive || exit 0
      c=$(cost_now); echo "$(date -u +%FT%TZ) cost $c EUR of cap $CAP EUR" >> "$COST"
      if ge "$c" "$CAP"; then
        main_alive || exit 0
        echo "$(date -u +%FT%TZ) COST CAP reached: $c EUR >= $CAP EUR; ending the session" | tee -a "$LOG" >> "$COST"
        : > "$IN/.cap_reached"; kill -TERM "$MAIN_PID"; exit 0
      fi
    done ) 2> /dev/null &
  WD_PID=$!; disown "$WD_PID"
  log "cost watchdog pid $WD_PID (ends with the session)"
}
start_vm() {   # start_vm <role>: returns 0 when RUNNING, and still RUNNING after the preemption check
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
    if [ "$rc" = 0 ] && [ "$st" = TERMINATED ]; then
      # a start accepted and the Spot VM already reclaimed: the next round, as a preemption (R11)
      log "start round $n of $vm: rc=0, but TERMINATED already (reclaimed)"
      [ "$(date +%s)" -ge "$deadline" ] && { log "start deadline reached"; return 3; }
      nap "$ROUND_PAUSE_S"; continue
    fi
    if [ "$st" = RUNNING ]; then
      log "start round $n of $vm: rc=$rc, RUNNING"
      # every host is Spot: each must still run after the check (rule 4b; the L4 and the guest host too, R11)
      log "preemption check: $vm must still be RUNNING in $PREEMPT_CHECK_S s"
      nap "$PREEMPT_CHECK_S"; st=$(vmst "$r")
      if [ "$st" != RUNNING ]; then
        log "$vm $st $PREEMPT_CHECK_S s after RUNNING (preempted)"
        [ "$(date +%s)" -ge "$deadline" ] && { log "start deadline reached"; return 3; }
        nap "$ROUND_PAUSE_S"; continue
      fi
      log "$vm still RUNNING after $PREEMPT_CHECK_S s"
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
ssh_ready() {   # 0 ready, 3 the VM was reclaimed meanwhile (R11), 1 no SSH
  local r=$1 i st
  for i in $(seq 1 "$SSH_TRIES"); do
    run_fg ssh_l "$r" 45 true > /dev/null 2>&1 && return 0   # gcloud's own exit code (SKB rule 5)
    st=$(vmst "$r")
    case "$st" in TERMINATED|STOPPING|STOPPED) log "$(var "$r" VM) is $st while waiting for SSH (reclaimed)"; return 3 ;; esac
    nap "$SSH_PAUSE_S"
  done
  return 1
}
upload() {
  local r=$1 got gmin
  routall scp_r "$r" 300 "$KIT" "$(var "$r" VM):/tmp/da-kit-$SID.tgz"; local rc=$?
  printf '%s\n' "$ROUT" | one >> "$LOG"
  [ "$rc" = 0 ] || return 1
  rout ssh_l "$r" 120 "if [ -e ~/da-kit/$SID ]; then echo KIT_EXISTS; exit 3; fi; set -e; mkdir -p ~/da-kit/$SID; tar -xzf /tmp/da-kit-$SID.tgz -C ~/da-kit/$SID; echo $SID > ~/da-kit/$SID/session_id; sha256sum /tmp/da-kit-$SID.tgz"
  grep -q -x KIT_EXISTS <<< "$ROUT" && { log "refused: ~/da-kit/$SID exists on $(var "$r" VM) (a session id is used once)"; return 1; }
  got=$(awk 'NF==2 {print $1}' <<< "$ROUT" | tail -1)
  [ "$got" = "$KIT_SHA" ] || { log "kit on $(var "$r" VM): sha256 '$got', expected $KIT_SHA"; return 1; }
  # safety net: the VM powers itself off a little after the cap, should this host lose the session
  # (the guest host: the guests' stop first, and no power-off while a crosvm is left; safety_net.sh)
  gmin=$(( CAP_S / 60 + SAFETY_MARGIN_MIN ))
  local net="bash ~/da-kit/$SID/bench/session/remote/safety_net.sh arm $gmin"
  [ "$r" = guest ] && net="$net$(q "$GSTOP")"
  # no host runs on without its safety net: an arming that is not confirmed ends the session (R15)
  rout ssh_l "$r" 60 "$net"
  if ! grep -q -x "safety-net-$gmin" <<< "$ROUT"; then
    log "safety net of $(var "$r" VM) not armed: $(printf '%s\n' "$ROUT" | one)"; return 2
  fi
  log "$(var "$r" VM): kit ok, power-off safety net in $gmin min$([ "$r" = guest ] && echo ", the guests' stop first"): $(grep '^timer: ' <<< "$ROUT" | one)"
  return 0
}
for r in "${ROLES[@]}"; do
  ssh_ready "$r"; rc=$?
  [ "$rc" = 3 ] && fail 3 "$(var "$r" VM) was reclaimed before SSH answered"
  [ "$rc" = 0 ] || fail 4 "no SSH to $(var "$r" VM)"
  upload "$r"; rc=$?
  [ "$rc" = 2 ] && { UPLOADED="$UPLOADED $r"; fail 4 "the safety net of $(var "$r" VM) is not armed: no host runs without it"; }
  [ "$rc" = 0 ] || fail 4 "upload of the kit to $(var "$r" VM) failed"
  UPLOADED="$UPLOADED $r"
done

# ───────────── 4. the steps of the session kind ─────────────
# the environment the remote entries get from this session's configuration (entrypoints.env)
GENV="env$(q "APP_PACKAGE=$APP_PACKAGE" "APP_COMPONENT=$APP_COMPONENT" "APP_RECORD_PATHS=$APP_RECORD_PATHS" "IVI_PERMISSIVE=$IVI_PERMISSIVE")"
SENV="env$(q "SIM_PY=$SIM_PY")"
CAMCAL_DIR="\$HOME/da-kit/$SID/camera_calibration"   # on the S-CORE host
HAS_GUEST=0; [[ " ${ROLES[*]} " == *" guest "* ]] && HAS_GUEST=1
SEQ=()

guest_bring_up() {   # fresh guests, the app and its ACLs, the VXLAN at both ends
  rstep guest guest_up "$T_GUEST_UP" "$GENV" bash "$ENTRY_GUEST_UP" "$(od guest_up)"
  rstep guest guest_prepare "$T_GUEST_UP" "$GENV" bash "$ENTRY_GUEST_PREPARE" "$(od guest_prepare)"
  local gip sip; ipof guest gip; ipof score sip
  log "VXLAN between the guest host $gip and the S-CORE host $sip (both from gcloud)"
  rstep guest vxlan_guest "$T_STEP" sudo bash "$ENTRY_VXLAN" guest-host add "$sip"
  rstep score vxlan_score "$T_STEP" sudo bash "$ENTRY_VXLAN" host-half add "$gip"
  # 192.168.98.1 moved from cvd-ebr to the S-CORE host's VXLAN end, with another MAC: both guests learn it now, not
  # when their old entry expires (split-bench recipe, step 4; R18)
  rstep guest neigh_flush "$T_STEP" bash "$ENTRY_GUEST_OFFER_CHECK" neigh "$(od neigh_flush)"
}
MCAST_DONE=0
offer_checks() {   # after an S-CORE side start (someipd offers 0x4df1 at 192.168.98.1:30511): route, then the unit
  local w=$1
  if [ "$MCAST_DONE" = 0 ]; then
    rstep guest mcast_route "$T_STEP" bash "$ENTRY_GUEST_OFFER_CHECK" route "$(od mcast_route)"; MCAST_DONE=1
  fi
  rstep guest "unit_$w" "$T_UNIT" bash "$ENTRY_GUEST_OFFER_CHECK" unit "$(od "unit_$w")" "$(od "logmark_$w")"
}
logmark() {   # the SDV Core guest's clock just before an S-CORE side start: the unit check reads only the log since (R7)
  rstep guest "logmark_$1" "$T_STEP" bash "$ENTRY_GUEST_OFFER_CHECK" mark "$(od "logmark_$1")"
}
window_open() {   # the app restarted, then the IVI clock set just before the window (R9), then the capture
  local w=$1
  rstep guest "app_restart_$w" "$T_STEP" "$GENV" bash "$ENTRY_GUEST_APP_RESTART" "$(od app_restart)" "$w"
  rstep guest "ivi_clock_$w" "$T_STEP" bash "$ENTRY_GUEST_CLOCK" set "$(od "ivi_clock_$w")"
  rstart guest "capture_$w" "$GENV" bash "$ENTRY_GUEST_CAPTURE" start "$(od "capture_$w")"
}
window_close() {
  local w=$1
  rstep guest "capture_stop_$w" "$T_CAPTURE_END" bash "$ENTRY_GUEST_CAPTURE" stop "$(od "capture_$w")"
  rwait guest "capture_$w" "$T_CAPTURE_END" || { abort 5 "the display capture of $w did not end well"; }
  # the app's own record of the window: no receipt means the path did not carry, whatever the steps said (R7)
  rstep guest "receipts_$w" "$T_STEP" bash "$ENTRY_GUEST_OFFER_CHECK" receipts "$(od "capture_$w")"
  local n; n=$(grep -o 'RECEIPTS [0-9]*' "$IN/guest.steps.out" | tail -1 | cut -d' ' -f2)
  RECEIPTS="${RECEIPTS:-} $w=${n:-unknown}"
  if [ "${n:-0}" = 0 ]; then
    log "NO RECEIPT IN THE APP'S RECORD OF WINDOW $w (${n:-no count}): the warning path did not carry; see guest/out/capture_$w/"
  else
    log "window $w: $n line(s) in the app's record"
  fi
}
world_run() {   # world_run <label> <scenario> <setting> <recorded 0|1> <another run follows 0|1>: one run with its own
  # S-CORE side
  local w=$1 sc=$2 se=$3 rec=$4 more=${5:-0} o; o=$(od "world_$w")
  [ "$rec" = 1 ] && rstart sim "rec_$w" "$SIM_PY" "$ENTRY_SIM_RECORD" --out "$(od "rec_$w")"
  rstart sim "world_$w" "$SENV" bash "$ENTRY_SIM_RUN" "$o" "$sc" "$se"
  rwaitfile sim "world_$w" "$o/simulator/ready.json" "$T_READY" || { abort 5 "the world side of $w is not ready"; }
  # the S-CORE side after ready.json (the hero stands), with the camera calibration file of this session
  [ "$HAS_GUEST" = 1 ] && [ "$rec" = 1 ] && logmark "$w"
  SCORE_RUN=$w
  # the go clock starts before the start step: the candidate's ready time-out runs from its process start inside
  # that step, which this host sees end only a poll later (S5); so the bound errs early, never late
  local t_up; t_up=$(date +%s)
  rstep score "score_start_$w" "$T_SCORE_START" env "DA_CAMERA_CALIBRATION_DIR=$CAMCAL_DIR" bash "$ENTRY_SCORE_START" \
    "$(od "score_$w")" "$CARLA_HOST"
  SCORE_UP=$(od "score_$w")
  if [ "$HAS_GUEST" = 1 ] && [ "$rec" = 1 ]; then offer_checks "$w"; window_open "$w"; fi
  # the candidate gives up on the world after its 420 s ready time-out: a later go reads as a supervision failure
  # (rule 31), so the run is refused, the world side ended and the S-CORE side stopped (R14)
  local since=$(( $(date +%s) - t_up ))
  if [ "$since" -gt "$GO_LIMIT_S" ]; then
    log "INVALID RUN $w: the go would come $since s after the S-CORE side's start (limit $GO_LIMIT_S s, the candidate's ready time-out 420 s)"
    rsignal sim "world_$w" TERM
    STEP_FAIL="world_$w"; abort 5 "the run $w is invalid: no go within $GO_LIMIT_S s of the S-CORE side's start"
  fi
  log "go of $w $since s after the S-CORE side's start step began (limit $GO_LIMIT_S s, the go's SSH call at most $GO_SSH_S s)"
  rtouch sim "$o/go" "$GO_SSH_S" || { STEP_FAIL="world_$w"; abort 5 "no go file for $w"; }
  log "go of $w done $(( $(date +%s) - t_up )) s after the S-CORE side's start step began (the candidate waits 420 s)"
  rwaitfile sim "world_$w" "$o/simulator/run_end.json" "$T_RUN" || { abort 5 "the run $w did not end"; }
  # the S-CORE side stops while the world still ticks (launch-manager/README.md), then the world is released
  rstep score "score_stop_$w" "$T_SCORE_START" bash "$ENTRY_SCORE_STOP" "$(od "score_$w")"; SCORE_UP=""
  rtouch sim "$o/release" || log "WARNING no release file for $w: the world side ends at its own hold limit"
  rwait sim "world_$w" "$T_RELEASE" || { abort 5 "the world side of $w did not end well"; }
  if [ "$rec" = 1 ]; then rwait sim "rec_$w" "$T_REC_END" || { abort 5 "the recorder of $w did not end well"; }; fi
  if [ "$HAS_GUEST" = 1 ] && [ "$rec" = 1 ]; then window_close "$w"; fi
  # a stop that had to kill, with another run to come: this run is complete and recorded, but the next one would
  # start from a suspect state while every VM bills; the session ends here (the lead's decision, S7)
  if [ "$STOP_KILLED_LAST" = "score_stop_$w" ] && [ "$more" = 1 ]; then
    STEP_FAIL="score_stop_$w"; ENDED_BY="score_stop_$w had to kill (rc 7) and another run would follow"
    abort 5 "the S-CORE stop of $w had to kill (rc 7): no further run from a suspect state"
  fi
}
make_h() {   # on this host: the capture from the simulator host, make-h, both files onto the S-CORE host
  local d=$IN/camcal src="da-kit/$SID/out/calibrate/camcal/simulator" vm f rc loc got
  vm=$(var sim VM); mkdir -p "$d/capture"; SEQ+=("lead:make_h")
  log "step make_h on this host: the camera capture from $vm, then camera_calibration.py make-h"
  routall scp_r sim 300 "$vm:$src/camera_capture.json" "$vm:$src/calibration_frame.png" "$d/capture/"
  printf '%s\n' "$ROUT" | one >> "$LOG"
  [ -s "$d/capture/camera_capture.json" ] && [ -s "$d/capture/calibration_frame.png" ] \
    || { STEP_FAIL=make_h; abort 5 "make_h: the camera capture did not arrive"; }
  if [ -n "$MAKE_H" ]; then
    timeout "$T_MAKE_H" "$MAKE_H" --capture "$d/capture/camera_capture.json" --out-dir "$d/h" > "$d/make_h.log" 2>&1; rc=$?
  else
    mkdir -p "$d/code" && tar -xzf "$KIT" -C "$d/code" bench/world-side
    timeout "$T_MAKE_H" "$CV_PY" "$d/code/bench/world-side/camera_calibration.py" make-h \
      --capture "$d/capture/camera_capture.json" --vp-clone "$VP_CLONE" --python "$CV_PY" --out-dir "$d/h" \
      > "$d/make_h.log" 2>&1; rc=$?
  fi
  log "step make_h rc=$rc"
  for f in H.yaml homography_C_matrix.yaml; do
    [ "$rc" = 0 ] && [ -s "$d/h/$f" ] || { STEP_FAIL=make_h; abort 5 "make_h: no $f (see camcal/make_h.log)"; }
  done
  loc=$(cd "$d/h" && sha256sum H.yaml homography_C_matrix.yaml)
  CAMCAL_SHA=$(echo "$loc" | awk '{printf "%s=%s ", $2, $1}')
  run_fg ssh_l score 60 "mkdir -p da-kit/$SID/camera_calibration" > /dev/null 2>&1
  local up=("$d/h/H.yaml" "$d/h/homography_C_matrix.yaml")
  [ -f "$d/h/camera_calibration_record.json" ] && up+=("$d/h/camera_calibration_record.json")
  routall scp_r score 120 "${up[@]}" "$(var score VM):da-kit/$SID/camera_calibration/"
  printf '%s\n' "$ROUT" | one >> "$LOG"
  rout ssh_l score 60 "cd da-kit/$SID/camera_calibration && sha256sum H.yaml homography_C_matrix.yaml"; got=$ROUT
  [ "$(echo "$got" | awk 'NF==2' | sort)" = "$(echo "$loc" | sort)" ] \
    || { STEP_FAIL=make_h; abort 4 "make_h: the files on $(var score VM) differ from this host's"; }
  log "camera calibration on $(var score VM) in $CAMCAL_DIR: $CAMCAL_SHA"
}

case "$KIND" in
  p10-1)
    rstep score p10_1 "$T_P10_1" bash "$ENTRY_SCORE_P10_1" "$(od p10_1)"
    ;;
  p10-3)
    # the guest-prep-20261118 operator's order: VXLAN, the offer, the multicast route, the broker's unit, then the
    # IVI clock just before the window
    guest_bring_up
    logmark inject
    SCORE_RUN=inject
    rstep score score_start "$T_SCORE_START" bash "$ENTRY_SCORE_START" "$(od score)" none
    SCORE_UP=$(od score)
    offer_checks inject
    window_open inject
    rstep score inject "$T_INJECT" bash "$ENTRY_SCORE_INJECT" "$(od inject)"
    window_close inject
    rstep score score_stop "$T_SCORE_START" bash "$ENTRY_SCORE_STOP" "$(od score)"; SCORE_UP=""
    ;;
  p10-2)
    rstep sim sim_setup "$T_SIM_SETUP" bash "$ENTRY_SIM_SETUP" "$(od sim_setup)"
    [ -n "$CARLA_HOST" ] || ipof sim CARLA_HOST
    log "CARLA host for the S-CORE side: $CARLA_HOST"
    # the bench network (brief R5): CARLA's port must answer from the S-CORE host before anything starts there
    rstep score carla_reach 60 timeout 10 bash -c "\"</dev/tcp/$CARLA_HOST/2000\""
    [ "$HAS_GUEST" = 1 ] && guest_bring_up
    # the lap rule: the warm-up runs with every camera, the recording view included, and its recorder must write;
    # no candidate runs yet (world-side/README.md: the S-CORE side starts only for the runs)
    rstart sim rec_warmup "$SIM_PY" "$ENTRY_SIM_RECORD" --out "$(od rec_warmup)"
    rstep sim warmup "$T_WARMUP" "$SENV" bash "$ENTRY_SIM_WARMUP" "$(od warmup)"
    rwait sim rec_warmup "$T_REC_END" || { abort 5 "the warm-up's recorder did not end well: no recorded run"; }
    # ASM-DRIVING-005 and the camera capture, without candidate or adapter; then the calibration file, which the
    # S-CORE side copies into the candidate's working directory before its identity record
    rstep sim calibrate "$T_CALIBRATE" "$SENV" bash "$ENTRY_SIM_CALIBRATE" "$(od calibrate)"
    make_h
    [ "$P10_2_CALIB_STEER" = 1 ] && world_run calib_steer ASM-DRIVING-006 "$P10_2_SETTING" 0 "$([ "$P10_2_RUNS" -ge 1 ] && echo 1 || echo 0)"
    for n in $(seq 1 "$P10_2_RUNS"); do
      world_run "run$n" "$P10_2_SCENARIO" "$P10_2_SETTING" 1 "$([ "$n" -lt "$P10_2_RUNS" ] && echo 1 || echo 0)"
    done
    ;;
esac
log "SEQUENCE ${SEQ[*]}"
fetch_all || { ENDED_BY=fetch; fail 5 "evidence fetch incomplete"; }
ENDED_BY=steps
log "session steps done; the files are in $IN"
FINAL_RC=0
exit 0
