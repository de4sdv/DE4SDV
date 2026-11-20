#!/bin/bash
# INC-DRIVING-002 bench session orchestrator (brief row B13). Runs on the lead host (the Jetson) and drives up to three
# hosts in two GCP projects: the simulator host (G4, Spot), the S-CORE host (L4) and the protected guest host.
#
#   da_session.sh --kind p10-1|p10-3|p10-2 [options]
#
#   --kind p10-1           the simulator host and the S-CORE host: the S-CORE build check (P10-1) while a CARLA world
#                          ticks (the world side's handshake: go before the check, release after it)
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
#   --camcal checkerboard|settings  p10-2's camera calibration source (default checkerboard): checkerboard runs
#                          upstream's procedure on the captured frame and ends the session on a failing frame;
#                          settings writes H.yaml from the simulated camera's settings and pose (make-h --source
#                          settings), keeps the frame as evidence with its pre-check recorded only, and runs no
#                          cross-check. Taken only from this flag, never as a fallback; session.json records it
#   --dry-run              use the fake gcloud in $DA_GCLOUD; print every command; shorter waits (DA_T_* knobs)
#
# Every internal IP comes from gcloud at run time; none is configured. SIM_SSH_IAP=1 (hosts.env) sends every ssh and
# scp to the simulator host through IAP.
#
# Start order: the G4 first, still RUNNING 30 s later, then the L4, then the guest host (rounds with short pauses
# while capacity is short). One GPU per project: a session refuses to start while another GPU VM runs in a project
# it starts a GPU VM in. The EXIT trap stops every VM this session started, on every exit, signals included: the
# guests first with cvd stop, then their host. A watchdog ends the session when the cost reaches the cap, and a host
# watch ends it when a VM it started reads anything but RUNNING (a Spot preemption: no SSH, no stop step and no fetch
# on that host; session.json hosts_lost). Disks are never deleted; nothing is created or deleted.
#
# Exit codes: 0 done; 2 refused before any VM start; 3 no capacity, or a host lost (preempted) before any step failed;
# 4 SSH or upload failed; 5 a step
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
unset GC_TO   # a gcloud call's time-out is the session's own (gc: 120 s, the trap: 30 s), never the caller's (S10)

KIND=""; DRY=0; CAP=""; OWNER_OK_GUEST=0; WITHOUT_GUEST=0; SID=""; KIT_FROM=head; KIT_EXTRA=""; CARLA_HOST=""
IVI_PERMISSIVE=0; RENV_ARGS=(); CAMCAL_SOURCE=checkerboard; CAMCAL_GIVEN=0
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
    --camcal) CAMCAL_SOURCE=${2:?}; CAMCAL_GIVEN=1; shift 2 ;;
    -h|--help) sed -n '2,44p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

case "$KIND" in
  p10-1) ROLES=(sim score); CAP=${CAP:-$CAP_EUR_P10_1} ;;
  p10-3) ROLES=(score guest); CAP=${CAP:-$CAP_EUR_P10_3} ;;
  p10-2) if [ "$WITHOUT_GUEST" = 1 ]; then ROLES=(sim score); else ROLES=(sim score guest); fi
         CAP=${CAP:-$CAP_EUR_P10_2} ;;
  *) echo "--kind p10-1|p10-3|p10-2 is required" >&2; exit 2 ;;
esac
# the camera calibration's source: only from --camcal (the lead's decision of 2026-11-19 for p10-2), never a fallback
case "$CAMCAL_SOURCE" in
  checkerboard|settings) ;;
  *) echo "refused: --camcal takes checkerboard or settings, not '$CAMCAL_SOURCE'"; exit 2 ;;
esac
[ "$CAMCAL_GIVEN" = 1 ] && [ "$KIND" != p10-2 ] && { echo "refused: --camcal is for p10-2 only (no other kind makes a calibration file)"; exit 2; }
if [ "$CAMCAL_SOURCE" = settings ]; then
  CAMCAL_REASON="the lead's decision of 2026-11-19 (owner informed): CARLA 1.0's apply_texture sets only material parameters named BaseColor, Difuse, Normal, Emissive or ORMH (CarlaGameModeBase.cpp:505-548 at 14ac3b1a50) and the engine plane's material has none of them, so the boards render flat grey and upstream's script finds 0 boards; H.yaml comes from the simulated camera's settings and pose"
else
  CAMCAL_REASON="upstream's procedure (Calibration/calc_front_camera_homography.py at the VisionPilot pin) on the captured frame"
fi
CAMCAL_XCHECK=""; CAMCAL_PRECHECK=""

# per-session settings of the remote entries (R6): only the names on its host's list below, and only when given on
# purpose with --remote-env NAME=VALUE (S4: an exported variable of the calling shell, another worker's UNIT_WAIT_S
# say, never reaches a step). Each goes to every step on that host (`env NAME=value` before the command) and into
# session.json, so a guessed pattern or a time-out is changed for the next session without a commit
REMOTE_ENV_guest="UNIT_SOURCE UNIT_REGISTERED_RE UNIT_NEGATION_RE BROKER_ERROR_RE UNIT_WAIT_S B12_DIR VERIFY_WAIT_S ADB_TIMEOUT_S
                  UP_TIMEOUT_S CLOCK_READS CLOCK_MAX_OFFSET_S START_WAIT_S APP_SUBSCRIBE_WAIT_S"
# (DA_P10_1_CARLA_HOST is not on it: p10-1 sets it from its own simulator host, the address read from gcloud)
REMOTE_ENV_score="GATEWAYD_RX_REGEX DA_P10_1_LATE_WAIT_S DA_P10_1_CUDA_RUNS DA_P10_1_ALIVE_HOLD_S
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

# the ranged fetch's settings (hosts.env, F7): whole numbers >= 1
for _n in FETCH_PARALLEL FETCH_RANGE_MIB; do
  [[ "${!_n}" =~ ^[1-9][0-9]*$ ]] || { echo "refused: $_n must be a whole number >= 1, not '${!_n}'"; exit 2; }
done
# the cap: a positive number of EUR (R21)
[[ "$CAP" =~ ^[0-9]+(\.[0-9]+)?$ ]] && awk -v c="$CAP" 'BEGIN { exit !(c > 0) }' \
  || { echo "refused: --cap-eur must be a positive number of EUR, not '$CAP'"; exit 2; }

# waits, seconds; a dry run may shorten them through DA_T_<NAME>, a real session refuses those knobs
PREEMPT_CHECK_S=30; ROUND_PAUSE_S=45; START_DEADLINE_S=1800; RUNNING_WAIT_S=120; SSH_TRIES=20; SSH_PAUSE_S=10
# GO_LIMIT_S: the go must follow the S-CORE side's start within the candidate's 420 s ready time-out; the clock starts
# before the start step's own SSH call, and 40 s are kept for the go's SSH call (IAP to the G4, GO_SSH_S at most)
POLL_S=20; STEP_TERM_POLLS=6; GO_LIMIT_S=380; GO_SSH_S=35; WATCH_S=30; HOST_WATCH_S=30; HOST_WATCH_TO_S=25; STOP_TRIES=30; STOP_POLL_S=10; SAFETY_MARGIN_MIN=10; STATUS_TRIES=5; STOP_AGAIN_EVERY=6
GUEST_NOSSH_S=180
# the exit trap's pre-stop phase is bounded as a whole (S9), and each step in it has its own slot (P1, below): each
# fetch at most TRAP_PACK_S to pack and TRAP_SCP_S to copy, the S-CORE side's stop TRAP_SCORE_S. PRESTOP_S is derived
# per kind from those bounds (a dry run's DA_T_PRESTOP_S caps the whole phase below that sum)
PRESTOP_S=""; TRAP_PACK_S=120; TRAP_SCP_S=300; TRAP_SCORE_S=120
TRAP_GC_TO_S=30   # each gcloud status read in the trap: on a gcloud outage the stop loop must not sit for hours (S10)
T_P10_1=2400; T_GUEST_UP=2400; T_SCORE_START=900; T_SIM_SETUP=1200; T_WARMUP=900; T_RUN=900; T_INJECT=1200
T_CAPTURE_END=240; T_REC_END=200; T_REC_LISTEN=150; T_STEP=300; T_CALIBRATE=1800; T_MAKE_H=600; T_READY=300; T_RELEASE=400
# the bounds of the steps whose waits are per-session settings follow them (W4, W2 of the re-check at 437a833b):
# unit_<w>: UNIT_WAIT_S, its last poll (2 adb reads of 30 s and POLL_S 5), then on a fail the diagnostics (4 adb calls
# of 30 s): UNIT_WAIT_S + 185, kept as UNIT_WAIT_S + 240. app_restart_<w>: START_WAIT_S + APP_SUBSCRIBE_WAIT_S + 10 adb
# calls of 30 s (8 before the wait, the wait's last read, and POLL_S 1)
for _n in UNIT_WAIT_S START_WAIT_S APP_SUBSCRIBE_WAIT_S; do
  [ -z "${RVAL[$_n]+x}" ] || [[ "${RVAL[$_n]}" =~ ^[0-9]+$ ]] \
    || { echo "refused: --remote-env $_n must be a whole number of seconds, not '${RVAL[$_n]}'"; exit 2; }
done
T_UNIT=$(( ${RVAL[UNIT_WAIT_S]:-120} + 240 ))
T_APP_RESTART=$(( ${RVAL[START_WAIT_S]:-5} + ${RVAL[APP_SUBSCRIBE_WAIT_S]:-30} + 300 ))
# the S-CORE host's disk check before p10-2's first run (F3 of 20261119T174606Z): the candidate's Rerun record grows at
# most at the measured rate (calib_steer: 4,729,613,610 B in 542 passes, 8,726,224 B a pass, at most 10 passes a second
# at the front camera's sensor_tick 0.1 s, rounded up to 88 MB/s) and stays on the host; a run's planned running is
# its setting's run cap plus RRD_HOLD_S of hold until its S-CORE stop (the poll of run_end.json and the stop's start
# call); the need is the rate times those seconds, plus 10 % and 5 GB
RRD_RATE_BPS=88000000; RRD_HOLD_S=60; RRD_MARGIN_B=5000000000
# the evidence fetch of a host reached through IAP (F7 of 20261120T092051Z; README "The evidence fetch"): the whole
# fetch is bounded by FETCH_BASE_S plus the pack's size at FETCH_PLAN_BPS (8 IAP tunnels read the G4's 305,986,299 B pack
# at about 1.03 MB/s), never above the pre-stop phase's fetch budget of a host (PRE_FETCH_S); each try of a range by
# FETCH_TRY_BASE_S plus twice the range at its tunnel's share of FETCH_PLAN_BPS (8 MiB: 165 s; F7's slowest range 87 s)
FETCH_BASE_S=60; FETCH_PLAN_BPS=1000000; FETCH_TRY_BASE_S=30; FETCH_TRIES=3
# a pack that needs more than that budget is not read at all (R2 of the closure check of 1bfbd6b4): it stays on the host,
# and session.json not_fetched names it, with its sha256 and size, as a fetch owed (fetch_owed.sh, README "A fetch
# owed"). A host reached by direct SSH is copied by one scp of at most FETCH_SCP_S
FETCH_SCP_S=1200
CARLA_PORTS="2000 2001 2002"   # p10-1's port test: CARLA's ports that carla-net admits from the S-CORE host
KNOBS=(PREEMPT_CHECK_S ROUND_PAUSE_S START_DEADLINE_S RUNNING_WAIT_S SSH_TRIES SSH_PAUSE_S POLL_S WATCH_S STOP_TRIES
       STOP_POLL_S T_P10_1 T_GUEST_UP T_SCORE_START T_SIM_SETUP T_WARMUP T_RUN T_INJECT T_CAPTURE_END T_REC_END T_REC_LISTEN T_STEP
       T_CALIBRATE T_MAKE_H T_READY T_RELEASE T_UNIT T_APP_RESTART STATUS_TRIES STOP_AGAIN_EVERY STEP_TERM_POLLS GO_LIMIT_S
       GUEST_NOSSH_S GO_SSH_S PRESTOP_S TRAP_PACK_S TRAP_SCP_S TRAP_SCORE_S HOST_WATCH_S FETCH_BASE_S FETCH_PLAN_BPS
       FETCH_TRY_BASE_S)
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
# the display capture's caps follow this session's bounds (Q3, Q4; README "The display capture's caps"). POLL_S counts
# as whole seconds (a dry run's 0.1 as 1)
CAP_P=$(awk -v x="$POLL_S" 'BEGIN { c = int(x); if (c < x) c++; print c }')
# --wait-cap-s: the stop's cap inside capture_stop's T_CAPTURE_END, counted from before rstep's start SSH call (60 s):
# the stop's own last poll and exit (2 s), then one status poll that read "running" just before its end (its SSH
# call, 60 s) and POLL_S
CAP_WAIT_S=$(( T_CAPTURE_END - 60 - 2 - 60 - CAP_P )); [ "$CAP_WAIT_S" -ge 1 ] || CAP_WAIT_S=1
# --max-s: the longest window that ends well, every step inside it at its bound: an rstep its start SSH call + its
# bound + POLL_S + one poll + its tail call, an rwait or rwaitfile its bound + POLL_S + one poll, a touch its SSH
# bound; then capture_stop's start SSH call. Past it the capture would end on its own (max-s) before the window
if [ "$KIND" = p10-3 ]; then CAP_MAX_S=$(( (60 + T_INJECT + CAP_P + 120) + 60 ))
else CAP_MAX_S=$(( GO_SSH_S + (T_RUN + CAP_P + 60) + (60 + T_SCORE_START + CAP_P + 120) + 60 + (T_RELEASE + CAP_P + 60)
                   + (T_REC_END + CAP_P + 60) + 60 )); fi
# the exit trap's pre-stop budget (P1; README "The exit trap's pre-stop budget"): every step the trap runs before a VM
# stops gets a slot of its own bound, and the phase is the sum of the slots of this kind's hosts, so no step can use
# another's time: the running step's end (step: its TERM's call 60 s, STEP_TERM_POLLS waits of POLL_S, the last poll
# 60 s, its tail 60 s); the open window's capture stop (capture, guest kinds: T_CAPTURE_END, then its status poll
# 60 s); the S-CORE side's stop (score: TRAP_SCORE_S); the world side's end (world, sim kinds: its release and TERM
# call 60 s, 3 polls of 60 s and POLL_S); each host's fetch (fetch: TRAP_PACK_S + TRAP_SCP_S per host)
PRE_STEP_S=$(( 60 + STEP_TERM_POLLS * CAP_P + 60 + 60 )); PRE_CAP_S=$(( T_CAPTURE_END + 60 )); PRE_SCORE_S=$TRAP_SCORE_S
PRE_WORLD_S=$(( 60 + 3 * (60 + CAP_P) )); PRE_FETCH_S=$(( TRAP_PACK_S + TRAP_SCP_S ))
PRE_SUM=$(( PRE_STEP_S + PRE_SCORE_S + ${#ROLES[@]} * PRE_FETCH_S )); PRE_PARTS="step $PRE_STEP_S"
[[ " ${ROLES[*]} " == *" guest "* ]] && { PRE_SUM=$(( PRE_SUM + PRE_CAP_S )); PRE_PARTS="$PRE_PARTS, capture $PRE_CAP_S"; }
PRE_PARTS="$PRE_PARTS, score $PRE_SCORE_S"
[[ " ${ROLES[*]} " == *" sim "* ]] && { PRE_SUM=$(( PRE_SUM + PRE_WORLD_S )); PRE_PARTS="$PRE_PARTS, world $PRE_WORLD_S"; }
PRE_PARTS="$PRE_PARTS, fetch $(( ${#ROLES[@]} * PRE_FETCH_S ))"
[ -n "$PRESTOP_S" ] || PRESTOP_S=$PRE_SUM

SID=${SID:-$(date -u +%Y%m%dT%H%M%SZ)}
T0_ISO=$(date -u +%FT%TZ)   # the session's start: a preemption operation older than it is not this session's
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
MAIN_PID=$$; WD_PID=""; HW_PID=""; CHILD=""; STARTED=(); STEP_FAIL=""; FINAL_RC=""; ENDED_BY=""; UPLOADED=""; SCORE_UP=""
FETCHED=""; FETCH_OK=""; FETCH_BAD=""
GUEST_STEP_SENT=0   # 1 from the first step sent to the guest host on: from then on guests may run there (S1)
SCORE_RUN=""; STOPS=""; STOP_KILLED_LAST=""   # the run of the S-CORE side up; each of its stops: run:step:rc (S7)
TERMED_STEP=""; TERMED_NAME=""; TERMED_AFTER=""; TERMED_FAIL=""   # the step the trap's TERM cut (step_down)
CUR_STEP=""; GUEST_STEP_RUNNING=""; FETCHING=""; PRE_END=""; PHASE_END=""   # "<role> <step>" of the step rstep waits for; a guest step alive after its TERM
WORLD_UP=""; STEP_RC=""; P10_1_RC=""; ALLOW_RC=""   # the detached world sides not seen ending (world_down); rstep's last rc
# the window whose display capture is open (from window_open's capture start to window_close's end of it), the tries
# of its stop at the session's end, and each capture's end: <w>:<end>:<rc>:<closed by>:<guest files kept 0|1> (Q1, Q2)
CAP_OPEN=""; CAP_TRY=0; CAPTURES=""
CHASE=""   # each recorded run's chase recorder end: <run>:<rc> (F4)

log() { local l; l="$(date -u +%FT%TZ) $*"; printf '%s\n' "$l" >> "$LOG"; printf '%s\n' "$l" 2>/dev/null || true; }
say() { printf '%s\n' "$*" >&3 2>/dev/null || true; }   # a dry run's command line on stdout
# never log account e-mail addresses or quota limits
sanitize() { sed -E -e 's/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/<email>/g' -e '/[Ll][Ii][Mm][Ii][Tt]/d'; }
one() { sanitize | tr '\n' ' ' | tr -s ' ' | cut -c1-300; }
var() { local n="${1^^}_$2"; echo "${!n}"; }   # var <role> VM|PROJECT|ZONE|EUR_H
gc() {   # gc <role> <gcloud args...>: every call is printed (dry run) and kept in commands.log
  local role=$1; shift
  local p; p=$(var "$role" PROJECT)
  echo "$(date -u +%FT%T.%3NZ) + gcloud --configuration=$GCLOUD_CONFIGURATION --project=$p $* [timeout ${GC_TO:-120} s]" >> "$CMDS"
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
  echo "$(date -u +%FT%T.%3NZ) + ssh $1: $3 [timeout $2 s]" >> "$CMDS"; [ "$DRY" = 1 ] && say "+ ssh $1: $3"
  ssh_r "$@"
}
scp_r() {   # scp_r <role> <timeout_s> <src...> <dst>
  local role=$1 to=$2; shift 2
  echo "$(date -u +%FT%T.%3NZ) + scp $role: $* [timeout $to s]" >> "$CMDS"; [ "$DRY" = 1 ] && say "+ scp $role: $*"
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
# in the trap's pre-stop phase (PRE_END set): a time-out cut to the time left of the phase, at least 1 s
bnd() { [ -n "$PRE_END" ] || { echo "$1"; return; }; local l=$(( PRE_END - $(date +%s) )); [ "$l" -lt 1 ] && l=1
  [ "$l" -lt "$1" ] && echo "$l" || echo "$1"; }
pre_left() { [ -z "$PRE_END" ] || [ "$(date +%s)" -lt "$PRE_END" ]; }
# slot <s>: the next step of the pre-stop phase gets <s> seconds, never past the phase's end (P1): a step that runs
# to its bound leaves every later step its own
slot() { local e=$(( $(date +%s) + $1 )); [ "$e" -gt "$PHASE_END" ] && e=$PHASE_END; PRE_END=$e; }
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
  rsignal "$r" "$s" TERM   # a failed TERM call: the status poll below reads the VM's state (rpoll, lost_check)
  for i in $(seq 1 "$STEP_TERM_POLLS"); do
    rpoll "$r" "$HS status $s" "$(bnd 60)"; prc=$?
    [ "$prc" = 3 ] && break   # the host is gone (preempted): nothing runs there
    case "$ROUT" in "rc "*|absent) break ;; esac
    pre_left || { log "the pre-stop phase's bound reached while step $s still reads ${ROUT:-unknown}"; break; }
    sleep "$POLL_S"
  done
  log "step $s after the TERM: ${ROUT:-unknown}"
  local after=${ROUT:-unknown} fl=""
  case "$ROUT" in "rc "*|absent) ;; *) [ "$prc" != 3 ] && [ "$r" = guest ] && GUEST_STEP_RUNNING=$s ;; esac
  # the step's own last FAIL line (guest_up: "FAIL launch ended by TERM ..."): session.json names the step this TERM
  # cut, and how it ended, so a cut launch is never only an exit code 143 (T1)
  # whatever its exit status: `host_step.sh tail` exits 1 for a step killed before it wrote its .rc, the TERM's case
  if [ "$prc" != 3 ]; then
    rout ssh_l "$r" "$(bnd 60)" "$HS tail $s"
    printf '%s\n' "$ROUT" >> "$IN/$r.steps.out"; fl=$(grep '^FAIL ' <<< "$ROUT" | tail -1)
  fi
  log "step $s ended by the session's TERM: ${fl:-no FAIL line in its tail} (status after the TERM: $after)"
  TERMED_STEP="$r"; TERMED_NAME="$s"; TERMED_AFTER="$after"; TERMED_FAIL="$fl"
}

# the remote-step helpers, defined before the exit trap can run: a trap during the starts or the SSH and upload
# section (a signal, the cap) called score_down and fetch before their definitions ("command not found"), and an
# uploaded host was stopped unfetched
preempted_at() {   # preempted_at <role>: PRE_AT, the UTC time of the VM's newest compute.instances.preempted operation
  # since the session's start (GCP's own record of a Spot preemption), or empty
  local t
  GC_TO=$(bnd 60) rout gc "$1" compute operations list --zones="$(var "$1" ZONE)" \
    --filter="operationType=compute.instances.preempted AND targetLink~instances/$(var "$1" VM)\$ AND insertTime>=$T0_ISO" \
    --format='value(insertTime)' --sort-by=insertTime
  t=$(tail -1 <<< "$ROUT"); PRE_AT=""
  [ -n "$t" ] && PRE_AT=$(date -u -d "$t" +%FT%T.%3NZ 2>/dev/null)
  return 0
}
host_lost() {   # host_lost <role> <status> [<detected by>] [<detected at>]: a host gone mid-session (preempted): no SSH,
  # no stop step and no fetch on it, no more polls (R12, R12b). ended_by names it unless something ended the session
  # before (a failed step: abort decides by the time of the loss)
  case " ${LOST:-} " in *" $1 "*) return 0 ;; esac
  local by=${3:-a poll of its step} at=${4:-$(date -u +%FT%TZ)}
  # first: the host watch skips a role named here, so it never TERMs the session for a loss already being handled
  # (R1, R4 of the closure check of 1bfbd6b4: its TERM cut the fetch of a healthy host and the operations read below)
  echo "$1" >> "$IN/.lost_known"
  log "HOST LOST: $(var "$1" VM) ($1) is $2 during the session (preempted or stopped), detected by $by at $at: no SSH, no stop step and no fetch on it; its $(owed)"
  LOST="${LOST:-} $1"; FETCHED="$FETCHED $1"; FETCH_BAD="$FETCH_BAD $1"
  [ -n "$ENDED_BY" ] || ENDED_BY="host lost: $1 ($2)"
  [ "$1" = score ] && SCORE_UP=""
  # the row before GCP's operations read, which a TERM may cut (R4): its preempted_at is filled in after the read
  printf '%s\t%s\t%s\t%s\t\n' "$1" "$2" "$at" "$by" >> "$IN/hosts_lost.tsv"
  preempted_at "$1"
  log "$(var "$1" VM): preempted at ${PRE_AT:-unknown (no compute.instances.preempted operation since $T0_ISO)}"
  if [ -n "$PRE_AT" ]; then
    awk -F'\t' -v OFS='\t' -v r="$1" -v p="$PRE_AT" '$1 == r && $5 == "" { $5 = p } { print }' "$IN/hosts_lost.tsv" \
      > "$IN/.hosts_lost.tmp" && mv "$IN/.hosts_lost.tmp" "$IN/hosts_lost.tsv"
  fi
}
owed() { echo "records on its disk under ~/da-kit/$SID/out (fetch owed)"; }
lost_check() {   # lost_check <role> <detected by>: after a failed SSH or scp, the VM's state; 0 (and host_lost) when it
  # is gone, so the caller never reads the failure as a failed step or fetch (R12b)
  local st; st=$(vmst "$1")
  case "$st" in TERMINATED|STOPPING|STOPPED|SUSPENDING|SUSPENDED) host_lost "$1" "$st" "$2"; return 0 ;; esac
  return 1
}
rpoll() {   # rpoll <role> <remote command> [<timeout_s>]: one short poll, its last line in ROUT; 3 when the host is
  # gone (R12)
  if rout ssh_l "$1" "${3:-60}" "$2"; then ROUT=$(tail -1 <<< "$ROUT"); return 0; fi
  ROUT=""
  lost_check "$1" "a poll on its host" && return 3
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
  log "step $s rc=$rc"; STEP_RC=$rc
  # every stop of the S-CORE side has run its collection, whatever its code; each is recorded per run (S7)
  case "$s" in score_stop*) SCORE_UP=""; STOPS="$STOPS ${SCORE_RUN:-none}:$s:$rc" ;; esac
  if [ "$rc" = 7 ] && [[ "$s" == score_stop* ]]; then
    # stop_score_side.sh exit 7: stopped and collected, something had to be killed. Not a failure; recorded
    # (session.json score_stops, stop_killed). Exit 8, collection failed, stays a failure (the lead's decision)
    log "step $s rc=7: the S-CORE side of ${SCORE_RUN:-none} stopped and its records collected, but something had to be killed (stop_killed, recorded; not a failure)"
    STOP_KILLED_LAST=$s; return 0
  fi
  # ALLOW_RC: an exit status the caller judges itself (p10-1's check: 1 is a FAIL verdict, not a step failure)
  if [ "$rc" != 0 ] && [ "$rc" != "${ALLOW_RC:-0}" ]; then
    STEP_FAIL=$s; abort 5 "step $s failed (rc $rc)"
  fi
}
rstart() { local r=$1 s=$2; shift 2; log "start $s on $(var "$r" VM): $*"; SEQ+=("$r:$s&")
  [ "$r" = guest ] && GUEST_STEP_SENT=1
  case "$r:$s" in sim:world_*) WORLD_UP="$WORLD_UP $s" ;; esac   # from before its start call, as CUR_STEP
  run_fg ssh_l "$r" 60 "$HS start $s -- $(renv "$r")$*" >> "$IN/$r.steps.out" 2>&1 || { STEP_FAIL=$s; abort 5 "start of $s failed"; }; }
rsignal() { run_fg ssh_l "$1" 60 "$HS signal $2 ${3:-INT}" >> "$IN/$1.steps.out" 2>&1; }
rwait() {   # rwait <role> <step> <timeout_s>: waits for a detached step's status
  local r=$1 s=$2 end st; end=$(( $(date +%s) + $3 )); SEQ+=("$r:wait-$s")
  while :; do
    rpoll "$r" "$HS status $s"; [ $? = 3 ] && { STEP_FAIL=$s; return 1; }; st=$ROUT
    case "$st" in "rc "*) world_ended "$s"; log "step $s ${st}"; [ "$st" = "rc 0" ] && return 0; STEP_FAIL=$s; return 1 ;; esac
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
      "rc "*) world_ended "$s"; log "step $s ended ($st) before ${f##*/}"; STEP_FAIL=$s; return 1 ;;
    esac
    [ "$(date +%s)" -ge "$end" ] && { log "step $s: no ${f##*/} after $4 s"; STEP_FAIL=$s; return 1; }
    nap "$POLL_S"
  done
}
rlisten() {   # rlisten <run>: the chase recorder's listening file, which it writes once it took its list of the heroes
  # already there, before world_<run> spawns the run's hero (R7 of the closure check of 1bfbd6b4, T2 of 8fae4100: the
  # margin was about 4 s). Bounded by T_REC_LISTEN, polled every 2 s at most; past it, or after the recorder's end,
  # the run goes on as before (its recorder's end is recorded as the run's chase view). Not a step of SEQUENCE
  local w=$1 f end p=$POLL_S; f="$(od "rec_$w")/listening"; end=$(( $(date +%s) + T_REC_LISTEN ))
  ge "$p" 2 && p=2
  while :; do
    rpoll sim "test -e $f && echo present || $HS status rec_$w"
    [ $? = 3 ] && { STEP_FAIL="rec_$w"; abort 5 "the chase recorder of $w: $(var sim VM) is gone"; }
    case "$ROUT" in
      present) log "the chase recorder of $w listens (its list of the heroes already there taken): world_$w starts"; return 0 ;;
      "rc "*) log "WARNING the chase recorder of $w ended ($ROUT) before its listening file: world_$w starts all the same"; return 0 ;;
    esac
    [ "$(date +%s)" -ge "$end" ] && { log "WARNING no listening file of the chase recorder of $w after $T_REC_LISTEN s: world_$w starts all the same (the recorder may take the run's hero for one already there)"; return 0; }
    nap "$p"
  done
}
rtouch() {   # rtouch <role> <remote file> [<timeout_s>]: a handshake file of the world side
  log "touch ${2##*/} on $(var "$1" VM): $2"; SEQ+=("$1:touch-${2##*/}")
  rout ssh_l "$1" "${3:-60}" "touch $2 && echo touched"; [[ "$ROUT" == *touched* ]]
}
fetch() {   # fetch <role>: the host's output folder into incoming_<id>/<role>/, checked against this session's id
  local r=$1 sha got
  case " $FETCHED " in *" $r "*) return 0 ;; esac
  FETCHED="$FETCHED $r"; FETCHING=$r   # a fetch a signal interrupts is recorded as not fetched
  fetch_one "$r" && { FETCHING=""; FETCH_OK="$FETCH_OK $r"; return 0; }
  FETCHING=""; case " ${LOST:-} " in *" $r "*) return 1 ;; esac   # host_lost named it already
  FETCH_BAD="$FETCH_BAD $r"; return 1
}
owe() {   # owe <role> <sha256> <bytes> <whole ranges kept> <ranges>: a pack left on its host, owed (R2): not_fetched
  printf '%s\t%s\t%s\t%s\t%s\n' "$@" >> "$IN/fetch_owed.tsv"
}
fetch_rec() {   # fetch_rec <role> <method> <bytes> <sha256> <bound_s> <ranges> <tries> <seconds> <result>: session.json fetch
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$@" >> "$IN/fetch.tsv"
}
fetch_one() {
  local r=$1 sha got rc line size="" how=scp bound b0 cap lbl n="" tries="" secs="" t0 tsv rows0
  rout ssh_l "$r" "$(bnd "${FETCH_PACK_TO:-600}")" "$HS pack"; rc=$?; line=$(tail -1 <<< "$ROUT")
  sha=${line%% *}; [[ "$line" == *" "* ]] && size=${line##* }   # the pack's last line: "<sha256> <bytes>" (F7)
  [ -n "$(iap "$r")" ] && how=ranges
  # an SSH failure reads the VM's state: a host gone is host_lost, never a failed fetch (R12b)
  [ "$rc" = 255 ] && lost_check "$r" "ssh: fetch (pack)" && { fetch_rec "$r" "$how" "$size" "" "" "" "" "" "host lost"; return 1; }
  mkdir -p "$IN/$r"
  if [ "$how" = ranges ]; then
    # a host reached through IAP (F7): one IAP scp ran at about 150-175 KB/s and was cut at its bound; the pack is read
    # as ranges over FETCH_PARALLEL tunnels instead, each range by dd on the host (nothing written there)
    if ! [[ "$sha" =~ ^[0-9a-f]{64}$ ]] || ! [[ "$size" =~ ^[0-9]+$ ]]; then
      lost_check "$r" "ssh: fetch (pack)" && { fetch_rec "$r" ranges "" "" "" "" "" "" "host lost"; return 1; }
      log "fetch from $(var "$r" VM) failed: its pack gave no sha256 and size (rc $rc): '$line'"
      fetch_rec "$r" ranges "" "" "" "" "" "" "failed: no sha256 and size from the pack"; return 1
    fi
    n=$(( (size + FETCH_RANGE_MIB * 1048576 - 1) / (FETCH_RANGE_MIB * 1048576) ))
    b0=$(( FETCH_BASE_S + (size + FETCH_PLAN_BPS - 1) / FETCH_PLAN_BPS ))
    # the pre-stop phase's fetch budget of a host, the slot of each fetch in the exit trap; there bnd cuts the bound to
    # the slot's time left after the pack, never to TRAP_SCP_S (R3 of the closure check of 1bfbd6b4)
    cap=$PRE_FETCH_S; lbl="the pre-stop phase's fetch budget of a host: $cap s"
    [ -n "$PRE_END" ] && lbl="$lbl, cut to its slot's time left in the exit trap"
    if [ "$b0" -gt "$cap" ]; then
      # R2: a pack over the budget is not read at all (S1's 2.2 GB would need 2260 s of 420); it stays on the host and
      # is named, with its sha256 and size, as a fetch owed
      log "fetch of $(var "$r" VM) by ranges: out.tgz $size B (sha256 $sha) needs $b0 s ($FETCH_BASE_S s plus the pack at $FETCH_PLAN_BPS B/s), more than the bound $cap s ($lbl): not read by the session; the pack stays on the host as ~/da-kit/$SID/out.tgz (fetch owed: see the README, \"A fetch owed\")"
      fetch_rec "$r" ranges "$size" "$sha" "$cap" "$n" 0 0 "skipped: needs $b0 s, more than the fetch budget of $cap s (fetch owed)"
      owe "$r" "$sha" "$size" 0 "$n"; return 1
    fi
    bound=$(bnd "$b0")
    log "fetch of $(var "$r" VM) by ranges: out.tgz $size B (sha256 $sha), $n ranges of $FETCH_RANGE_MIB MiB over $FETCH_PARALLEL IAP tunnels, $FETCH_TRIES tries a range of $(try_s) s at most; bound $bound s ($FETCH_BASE_S s plus the pack at $FETCH_PLAN_BPS B/s: $b0 s; $lbl)"
    # the tries of a fetch the host watch's TERM cut stay in the file, before the rows of this fetch (R1)
    tsv=$IN/$r/fetch_ranges.tsv; [ -s "$tsv" ] || printf 'range\ttry\tstart_s\tend_s\tbytes\twant\tresult\n' > "$tsv"
    rows0=$(wc -l < "$tsv"); t0=$(date +%s)
    run_fg fetch_ranges "$r" "$size" "$bound" "$IN/$r/.ranges" "$sha" > "$IN/.franges" 2>&1; rc=$?
    ROUT=$(cat "$IN/.franges" 2>/dev/null); rm -f "$IN/.franges"
    tries=$(( $(wc -l < "$tsv") - rows0 )); secs=$(( $(date +%s) - t0 ))
    if [ "$rc" != 0 ]; then
      # the whole ranges stay in <role>/.ranges beside its pack file (sha256, bytes, range MiB), so that the hand
      # fetch of the owed pack reads only the others (R2)
      lost_check "$r" "ranges: fetch" && { fetch_rec "$r" ranges "$size" "$sha" "$bound" "$n" "$tries" "$secs" "host lost"; return 1; }
      log "fetch from $(var "$r" VM) failed: $(tail -1 <<< "$ROUT") ($tries tries in $secs s; fetch_ranges.tsv; the whole ranges kept in $r/.ranges; fetch owed: see the README, \"A fetch owed\")"
      fetch_rec "$r" ranges "$size" "$sha" "$bound" "$n" "$tries" "$secs" "failed: $(tail -1 <<< "$ROUT")"
      owe "$r" "$sha" "$size" "$(find "$IN/$r/.ranges" -maxdepth 1 -name 'p[0-9][0-9][0-9][0-9][0-9][0-9]' | wc -l)" "$n"
      return 1
    fi
    cat "$IN/$r/.ranges"/p[0-9][0-9][0-9][0-9][0-9][0-9] > "$IN/$r/out.tgz"; rm -rf "$IN/$r/.ranges"
    log "ranges of $(var "$r" VM): $n ranges joined in order, $tries tries, $secs s"
  else
    bound=$(bnd "${FETCH_SCP_TO:-$FETCH_SCP_S}")
    routall scp_r "$r" "$bound" "$(var "$r" VM):da-kit/$SID/out.tgz" "$IN/$r/"; rc=$?
    printf '%s\n' "$ROUT" | one >> "$LOG"
    [ "$rc" != 0 ] && lost_check "$r" "scp: fetch" && { fetch_rec "$r" scp "$size" "$sha" "$bound" "" "" "" "host lost"; return 1; }
  fi
  got=$(sha256sum "$IN/$r/out.tgz" 2>/dev/null | cut -d' ' -f1)
  [ -n "$got" ] && [ "$got" = "$sha" ] || { log "fetch from $(var "$r" VM) failed or changed (remote '$sha', local '$got')"
    fetch_rec "$r" "$how" "$size" "$sha" "$bound" "$n" "$tries" "$secs" "failed or changed (local '$got')"; return 1; }
  tar -xzf "$IN/$r/out.tgz" -C "$IN/$r" || { fetch_rec "$r" "$how" "$size" "$sha" "$bound" "$n" "$tries" "$secs" "failed: tar"; return 1; }
  [ "$(cat "$IN/$r/out/session_id" 2>/dev/null)" = "$SID" ] || { log "fetched files of $(var "$r" VM) are not this session's"
    fetch_rec "$r" "$how" "$size" "$sha" "$bound" "$n" "$tries" "$secs" "failed: not this session's files"; return 1; }
  log "fetched $(var "$r" VM): out.tgz $got"
  fetch_rec "$r" "$how" "$size" "$sha" "$bound" "$n" "$tries" "$secs" ok
  return 0
}
try_s() { echo $(( FETCH_TRY_BASE_S + (2 * FETCH_RANGE_MIB * 1048576 * FETCH_PARALLEL + FETCH_PLAN_BPS - 1) / FETCH_PLAN_BPS )); }
fetch_ranges() {   # fetch_ranges <role> <bytes> <bound_s> <dir> <sha256>: in run_fg's subshell (F7). The ranges of the
  # host's out.tgz, FETCH_PARALLEL at once, into <dir>/p<index>; 0 when every range came whole within the bound. Its own
  # TERM (a signal, the cap) ends every range's tunnel first: kill_tree reaches timeout and gcloud there. <dir>/pack
  # names the pack the ranges are of: "<sha256> <bytes> <range MiB>" (the hand fetch of an owed pack reads it, R2)
  local r=$1 size=$2 bound=$3 dir=$4 sha=$5 n i end running=0 pids=()
  n=$(( (size + FETCH_RANGE_MIB * 1048576 - 1) / (FETCH_RANGE_MIB * 1048576) )); end=$(( $(date +%s) + bound ))
  trap 'for p in "${pids[@]}"; do kill_tree "$p"; done; exit 143' TERM HUP INT
  rm -rf "$dir"; mkdir -p "$dir" || { echo "no folder $dir"; return 1; }
  echo "$sha $size $FETCH_RANGE_MIB" > "$dir/pack"
  for (( i = 0; i < n; i++ )); do
    while [ "$running" -ge "$FETCH_PARALLEL" ]; do wait -n; running=$(( running - 1 )); done
    [ -e "$dir/failed" ] && break   # a range failed its tries: the fetch cannot be whole
    [ "$(date +%s)" -lt "$end" ] || break
    ( trap 'exit 143' TERM HUP; range_get "$r" "$i" "$size" "$end" "$dir" ) & pids+=("$!"); running=$(( running + 1 ))
  done
  wait
  for (( i = 0; i < n; i++ )); do
    [ -f "$dir/$(printf 'p%06d' "$i")" ] && continue
    if [ -e "$dir/failed" ]; then echo "$(head -1 "$dir/failed")"
    else echo "range $i not read: the fetch's bound of $bound s reached"; fi
    return 1
  done
  echo "$n ranges whole"
}
range_get() {   # range_get <role> <index> <bytes> <end>: one range by dd over an IAP tunnel, FETCH_TRIES tries, each
  # bounded (try_s, cut to the fetch's end) and size-checked; one row per try in fetch_ranges.tsv
  local r=$1 i=$2 size=$3 end=$4 dir=$5 rb want t to s e got rc res cmd f
  rb=$(( FETCH_RANGE_MIB * 1048576 )); want=$(( size - i * rb )); [ "$want" -gt "$rb" ] && want=$rb
  f=$dir/$(printf 'p%06d' "$i")
  cmd="dd if=\$HOME/da-kit/$SID/out.tgz bs=1M skip=$(( i * FETCH_RANGE_MIB )) count=$FETCH_RANGE_MIB status=none"
  for (( t = 1; t <= FETCH_TRIES; t++ )); do
    to=$(( end - $(date +%s) )); [ "$to" -gt "$(try_s)" ] && to=$(try_s)
    [ "$to" -ge 1 ] || { res="the fetch's bound reached"; break; }
    echo "$(date -u +%FT%T.%3NZ) + ssh $r: $cmd [timeout $to s]" >> "$CMDS"; [ "$DRY" = 1 ] && say "+ ssh $r: $cmd"
    s=$(date +%s.%N)
    # shellcheck disable=SC2046  # iap prints one word
    timeout "$to" "$GCLOUD" --configuration="$GCLOUD_CONFIGURATION" --project="$(var "$r" PROJECT)" compute ssh \
      "$(var "$r" VM)" --zone "$(var "$r" ZONE)" $(iap "$r") --ssh-flag=-T --command "$cmd" < /dev/null > "$f.part" 2>> "$dir/stderr.txt"
    rc=$?; e=$(date +%s.%N); got=$(stat -c %s "$f.part" 2>/dev/null || echo 0)
    if [ "$got" = "$want" ]; then res=ok; elif [ "$rc" = 124 ]; then res="rc 124"
    elif [ "$got" -lt "$want" ]; then res=short; else res="size $got"; fi
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$i" "$t" "$s" "$e" "$got" "$want" "$res" >> "$IN/$r/fetch_ranges.tsv"
    [ "$res" = ok ] && { mv "$f.part" "$f"; return 0; }
  done
  rm -f "$f.part"
  echo "range $i ($want B at $(( i * FETCH_RANGE_MIB )) MiB) failed after $(( t - 1 )) tries: $res" >> "$dir/failed"
  return 1
}
score_down() {   # the S-CORE side, if this session started it and has not stopped it: its stop is its only collector (R8)
  [ -n "$SCORE_UP" ] || return 0
  local o=$SCORE_UP rc; SCORE_UP=""
  log "the S-CORE side is up ($o): its stop, which collects its records, before the fetch"
  run_fg ssh_l score "${T_SCORE_DOWN:-$T_SCORE_START}" "$HS run score_stop_on_failure -- $(renv score)bash $ENTRY_SCORE_STOP $o" \
    >> "$IN/score.steps.out" 2>&1; rc=$?
  log "step score_stop_on_failure rc=$rc$([ "$rc" = 7 ] && echo ": stopped and collected, something had to be killed (stop_killed, recorded)")"
  [ "$rc" = 255 ] && lost_check score "ssh: score_stop_on_failure" && log "the S-CORE side of $o was not stopped by the session: its host is gone"
  STOPS="$STOPS ${SCORE_RUN:-none}:score_stop_on_failure:$rc"
}
world_ended() { local s; WORLD_UP=$(for s in $WORLD_UP; do [ "$s" = "$1" ] || printf ' %s' "$s"; done); }
world_down() {   # a detached world side not seen ending (a trap or abort path): after the S-CORE side's stop, its
  # release file, then a TERM to its step, its end awaited (bounded), before the simulator host's fetch packs it
  local s i
  case " ${LOST:-} " in *" sim "*) WORLD_UP=""; return 0 ;; esac
  for s in $WORLD_UP; do
    log "the world side $s still runs on $(var sim VM): its release file, then a TERM to it, before the fetch"
    rout ssh_l sim "$(bnd 60)" "touch $(od "$s")/release; $HS signal $s TERM"
    for i in 1 2 3; do
      rpoll sim "$HS status $s" "$(bnd 60)"; [ $? = 3 ] && break
      case "$ROUT" in "rc "*|absent) break ;; esac
      pre_left || break
      nap "$POLL_S"
    done
    log "world side $s after its release and TERM: ${ROUT:-unknown}"
  done
  WORLD_UP=""
}
capture_end() {   # capture_end <w> <closed by> <the capture's rc> <file with the stop's answer>: session.json's entry
  local e=unknown k=0 l
  l=$(grep -o 'capture ended ([a-z-]*).*' "$4" 2>/dev/null | tail -1)
  [[ "$l" =~ ^capture\ ended\ \(([a-z-]+)\) ]] && e=${BASH_REMATCH[1]}
  [[ "$l" == *"kept on the guest"* ]] && k=1
  CAPTURES="$CAPTURES $1:$e:${3:-}:${2// /_}:$k"
}
capture_down() {   # a window still open when the session ends (an abort, a signal, the cap): its capture's stop before
  # any fetch of the guest host, so the recording gets its SIGINT and its pull, and the app's records and capture.json
  # are written (Q1). Bounded by T_CAPTURE_END, in the trap by what the pre-stop phase leaves
  [ -n "$CAP_OPEN" ] || return 0
  local w=$CAP_OPEN b rc crc="" f=$IN/.capdown
  case " ${LOST:-} " in *" guest "*) CAP_OPEN=""; capture_end "$w" "session end" "" /dev/null; return 0 ;; esac
  b=$(bnd "$T_CAPTURE_END"); CAP_TRY=$((CAP_TRY + 1))
  log "the display capture of window $w is still open: its stop (the recording's SIGINT and pull, the app's records, capture.json) before the guest host's fetch, $b s at most"
  run_fg ssh_l guest "$b" "$HS run capture_down${CAP_TRY}_$w -- bash $ENTRY_GUEST_CAPTURE stop $(od "capture_$w") --wait-cap-s $(( b > 23 ? b - 22 : 1 ))" > "$f" 2>&1; rc=$?
  cat "$f" >> "$IN/guest.steps.out"; CAP_OPEN=""
  rpoll guest "$HS status capture_$w" "$(bnd 60)"; case "$ROUT" in "rc "*) crc=${ROUT#rc } ;; esac
  log "step capture_down${CAP_TRY}_$w rc=$rc: $(grep -o 'capture ended ([a-z-]*).*' "$f" | tail -1); capture_$w ${ROUT:-unknown}"
  capture_end "$w" "session end" "$crc" "$f"; rm -f "$f"
}
abort() {   # a failure after the starts: a step still alive after rstep's own TERM (its TERM again and its end, R8 of
  # the closure check of 7befc3c1: the fetch came before the trap's step_down), the open window's capture stop, the
  # S-CORE side's stop, the world side's end, the fetch, the exit (3 when a host was lost)
  local code=$1 lost0=${LOST:-} eb0=$ENDED_BY t_fail r; t_fail=$(date +%s%3N); shift
  [ -n "$lost0" ] && code=3
  step_down; capture_down; score_down; world_down; fetch_all
  # a host found lost on the way (an SSH of the stop path failed, R12b): the step's failure is recorded as after the
  # loss when GCP's preemption came first (failed_step stays; ended_by names the loss, exit 3), else as before it
  if [ -z "$lost0" ] && [ -n "${LOST:-}" ] && [ -n "$STEP_FAIL" ]; then
    ENDED_BY=$eb0
    for r in $LOST; do
      local pre; pre=$(awk -F'\t' -v r="$r" '$1 == r {print $5}' "$IN/hosts_lost.tsv" | tail -1)
      if [ -n "$pre" ] && [ "$(date -u -d "$pre" +%s%3N 2>/dev/null || echo 0)" -le "$t_fail" ]; then
        ENDED_BY="host lost: $r ($(awk -F'\t' -v r="$r" '$1 == r {print $2}' "$IN/hosts_lost.tsv" | tail -1))"; code=3
        log "step $STEP_FAIL failed after the loss of $r (preempted at $pre): the session ends as the host lost"
        break
      fi
    done
    [[ "$ENDED_BY" == "host lost: "* ]] || log "step $STEP_FAIL failed before the loss of a host was known to have come (hosts lost:$LOST): the session ends as the failed step"
  fi
  fail "$code" "$*"
}
fetch_all() { local r ok=0; for r in "${STARTED[@]}"; do fetch "$r" || ok=1; done; return $ok; }
ipof() {   # ipof <role> <var>: the internal IP, read from gcloud now (never configured: D5 may move the hosts)
  local ip; ip=$(vmip "$1"); [ -n "$ip" ] || abort 5 "no internal IP of $(var "$1" VM) from gcloud"
  IPS="${IPS:-} $1=$ip"; printf -v "$2" '%s' "$ip"
}


# ───────────── exit trap: stop what this session started ─────────────
cleanup() {
  local rc=$? r st i
  local GC_TO=$TRAP_GC_TO_S   # every gcloud call of the trap without its own time-out: the status reads (S10)
  # no signal ends the trap before its stops (R1): a second Ctrl-C, HUP or TERM, or the watchdog's TERM, is ignored
  # here, and the trap runs on to the guests' stop, their host's stop and session.json
  trap '' INT TERM HUP
  trap - EXIT
  # first: the host watch reads no VM from here on, so the trap's own stops are never a lost host (R12b)
  : > "$IN/.trap_stopping"
  [ -n "$FINAL_RC" ] && rc=$FINAL_RC
  [ -f "$IN/.cap_reached" ] && rc=10
  [ -n "$WD_PID" ] && { pkill -P "$WD_PID" 2>/dev/null; kill "$WD_PID" 2>/dev/null; }
  [ -n "$CHILD" ] && kill_tree "$CHILD"   # an interrupted SSH step: its local client and timeout too
  # the host watch's TERM (on_signal: exit 3): the host it read lost gets no SSH, no stop step and no fetch
  if [ -f "$IN/.host_lost" ]; then
    local hr hst hat x; read -r hr hst hat < "$IN/.host_lost"
    # a healthy host's fetch that this TERM cut (R1 of the closure check of 1bfbd6b4: attempt 3's G4 fetch, cut by the
    # L4's loss): out of FETCHED, so that the fetch loop below fetches it again in its slot, before its stop
    if [ -n "$FETCHING" ] && [ "$FETCHING" != "$hr" ]; then
      log "the fetch from $(var "$FETCHING" VM) was cut by the host watch's TERM for the loss of $hr: it is fetched again in its slot of the pre-stop phase"
      FETCHED=$(for x in $FETCHED; do [ "$x" = "$FETCHING" ] || printf ' %s' "$x"; done); FETCHING=""
    fi
    host_lost "$hr" "$hst" "host watch" "$hat"
  fi
  [ -f "$IN/.cap_reached" ] && ENDED_BY=cap
  [ -n "$ENDED_BY" ] || ENDED_BY="exit $rc"
  # a fetch the signal interrupted is not tried again (the session ends at once, R19); it is recorded as not fetched
  if [ -n "$FETCHING" ]; then log "the fetch from $(var "$FETCHING" VM) was interrupted: not fetched"; FETCH_BAD="$FETCH_BAD $FETCHING"; FETCHING=""; fi
  local gpu=() guest=0 early=""
  for r in "${STARTED[@]}"; do if [ "$r" = guest ]; then guest=1; else gpu+=("$r"); fi; done
  # the pre-stop phase, bounded as a whole (S9): after the cap every VM bills on while it runs, and the safety nets
  # fire at the cap plus this bound plus their margin. First the GPU hosts with nothing left to collect or fetch
  # (no kit there, or already fetched, no S-CORE side up, no step running) stop at once
  log "pre-stop phase, $PRESTOP_S s at most ($PRE_PARTS): the running step's end, the open capture's stop, the S-CORE side's stop, the world side's end, the fetches"
  for r in "${gpu[@]}"; do
    case " $UPLOADED " in *" $r "*) case " $FETCHED " in *" $r "*) ;; *) continue ;; esac ;; esac
    [ "$r" = score ] && [ -n "$SCORE_UP" ] && continue
    [ "${CUR_STEP%% *}" = "$r" ] && continue
    log "stopping $(var "$r" VM) ($r) first: nothing left to collect or fetch there"
    GC_TO=300 gc "$r" compute instances stop "$(var "$r" VM)" --zone "$(var "$r" ZONE)" --async --quiet 2>&1 | one >> "$LOG"
    early="$early $r"
  done
  PHASE_END=$(( $(date +%s) + PRESTOP_S )); PRE_END=$PHASE_END
  # the step still running on its host (a signal or the cap during it): TERM to it there, and its end awaited, before
  # the S-CORE side's stop and any stop; a guest launch never races the guests' stop (S2). Each step below runs in its
  # own slot (P1)
  slot "$PRE_STEP_S"; step_down
  # a window still open: its capture's stop before any fetch of the guest host (Q1)
  slot "$PRE_CAP_S"; pre_left && capture_down
  # the S-CORE side's stop, its only collector, while the world may still tick (R8); then the fetch of every host
  # whose evidence was not fetched yet (a signal, the cap), before its stop (R13); all within the phase's bound
  slot "$PRE_SCORE_S"
  if pre_left; then T_SCORE_DOWN=$(bnd "$TRAP_SCORE_S") score_down
  elif [ -n "$SCORE_UP" ]; then log "the pre-stop phase's bound reached: no stop of the S-CORE side by the session (its records stay incomplete on its disk)"; fi
  slot "$PRE_WORLD_S"; pre_left && world_down
  for r in $UPLOADED; do
    case " $FETCHED " in *" $r "*) continue ;; esac
    slot "$PRE_FETCH_S"
    if ! pre_left; then
      log "the pre-stop phase's bound reached: $(var "$r" VM) not fetched (its files stay on its disk)"
      FETCHED="$FETCHED $r"; FETCH_BAD="$FETCH_BAD $r"; continue
    fi
    if [ -n "$(iap "$r")" ]; then
      log "fetching $(var "$r" VM) before its stop (pack at most $TRAP_PACK_S s, then its ranges within the slot's time left, within the pre-stop phase)"
    else
      log "fetching $(var "$r" VM) before its stop (pack at most $TRAP_PACK_S s, copy at most $TRAP_SCP_S s, within the pre-stop phase)"
    fi
    FETCH_PACK_TO=$TRAP_PACK_S FETCH_SCP_TO=$TRAP_SCP_S fetch "$r"
  done
  PRE_END=""; PHASE_END=""
  # the other GPU hosts (they cost most), without waiting
  for r in "${gpu[@]}"; do
    case " $early " in *" $r "*) continue ;; esac
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
          # does not (assumption, checked once by the operator: README, the p10-3 block). Without SSH the host
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
    timeout "$TRAP_GC_TO_S" "$GCLOUD" --configuration="$GCLOUD_CONFIGURATION" --project="$p" compute instances list \
      --format='value(name,zone.basename(),status)' 2>/dev/null | sed "s/^/VM after session [$p]: /" >> "$LOG"
  done
  [ -n "$HW_PID" ] && { pkill -P "$HW_PID" 2>/dev/null; kill "$HW_PID" 2>/dev/null; }
  rm -f "$IN"/.hw_* "$IN/.host_lost.tmp"
  lost_report
  [ "$KIND" = p10-1 ] && [ -n "$UPLOADED" ] && p10_1_report
  [ "$KIND" = p10-3 ] && p10_3_report
  [ "$KIND" = p10-2 ] && p10_2_report
  write_record "$rc"
  log "SESSION_END $SID rc=$rc"
  [ -n "$LEFT_RUNNING" ] && log "VMS LEFT RUNNING, THEY BILL: STOP THEM BY HAND NOW:$LEFT_RUNNING (exit 11 in place of $RC_STEPS)"
  exit "$rc"
}
lost_report() {   # one line per host lost (R12b): its status, when and how it was found, GCP's preemption, the records
  local r st at by pre
  [ -s "$IN/hosts_lost.tsv" ] || return 0
  while IFS=$'\t' read -r r st at by pre; do
    log "$KIND host lost: $r ($st, detected at $at by $by, preempted at ${pre:-unknown}): $(var "$r" VM) was not fetched; its $(owed)"
  done < "$IN/hosts_lost.tsv"
}
p10_3_report() {   # p10-3 is passed only when its steps ended with 0 and every window's app record holds a receipt
  # event since the window's app start (window_close);
  # exit 0 alone means its steps ran (T4). One line in session.log, and session.json's p10_3 (passed, reason)
  local x w n bad="" good="" why=()
  for x in ${RECEIPTS:-}; do
    w=${x%%=*}; n=${x#*=}
    case "$n" in ""|*[!0-9]*|0) bad="$bad $w" ;; *) good="$good $w($n)" ;; esac
  done
  [ "${RC_STEPS:-1}" = 0 ] || why+=("the steps did not end with 0 (exit ${RC_STEPS:-unknown})")
  [ -n "$bad$good" ] || why+=("no window's app record was read")
  for w in $bad; do why+=("no receipt event since the app's start in the record of window $w"); done
  if [ ${#why[@]} = 0 ]; then
    P10_3_PASSED=1
    P10_3_REASON="the steps ended with 0 and every window's app record holds receipt events since the window's app start:$good"
    log "p10-3 passed: $P10_3_REASON"
  else
    P10_3_PASSED=0; P10_3_REASON=$(printf '%s; ' "${why[@]}"); P10_3_REASON=${P10_3_REASON%; }
    log "p10-3 NOT passed: $P10_3_REASON"
  fi
}
p10_2_report() {   # p10-2's display recording is complete only when every recorded window's capture ended by its stop
  # at the window's close with rc 0 and nothing kept on the guest (Q2). One line in session.log, and session.json p10_2
  local n w x e rc by k why=() PERM_NOTE=""
  # R2 of the closure check of 7befc3c1: a --permissive-ivi session's report says so, as session.json does
  [ "$IVI_PERMISSIVE" = 1 ] && PERM_NOTE=" (conditional on a permissive IVI)"
  log "p10-2 camera calibration source: $CAMCAL_SOURCE ($CAMCAL_REASON); cross-check: ${CAMCAL_XCHECK:-not reached (no make_h)}"
  # the candidate's Rerun records (rrd_on = true) stay on the S-CORE host: each one's size and sha256, from the host
  local rrd; rrd=$(python3 - "$IN/score/out" <<'PY'
import json, os, sys
parts = []
for name in sorted(os.listdir(sys.argv[1])) if os.path.isdir(sys.argv[1]) else []:
    try:
        rows = json.load(open(os.path.join(sys.argv[1], name, "candidate_rrd.json"), encoding="utf-8"))
    except (OSError, ValueError):
        continue
    for r in rows if isinstance(rows, list) else []:
        parts.append("%s %s B sha256 %s (%s)" % (name[len("score_"):] if name.startswith("score_") else name,
                                                r.get("bytes"), r.get("sha256"), r.get("path")))
print("; ".join(parts) or "none recorded")
PY
)
  log "p10-2 candidate Rerun records (rrd_on = true), kept on the S-CORE host, not fetched: $rrd"
  # each run's chase recorder: rc 0 or not, with the summary's end from the fetched files (F4). rc 0 says only that the
  # recorder attached, wrote a frame and ffmpeg ended 0, not that the view has no gap (T6): session.json chase_view
  # carries written, gaps and ticks_seen beside it
  local cgood=() cbad=() crc cend
  for n in $(seq 1 "$P10_2_RUNS"); do
    w=run$n; x=$(tr ' ' '\n' <<< "$CHASE" | grep "^$w:" | tail -1)
    [ -n "$x" ] || { cbad+=("$w (no end of its recorder recorded: the session ended before it)"); continue; }
    crc=${x#*:}
    if [ "$crc" = 0 ]; then cgood+=("$w"); continue; fi
    cend=$(python3 -c 'import json, sys
try:
    print(json.load(open(sys.argv[1], encoding="utf-8")).get("end") or "")
except (OSError, ValueError, AttributeError):
    print("")' "$IN/sim/out/rec_$w/summary.json")
    cbad+=("$w (recorder rc $crc: ${cend:-no summary fetched})")
  done
  if [ ${#cbad[@]} = 0 ]; then
    CHASE_COMPLETE=1; log "p10-2 chase recorder ended rc 0 in every run: $(printf '%s, ' "${cgood[@]}" | sed 's/, $//') (rc 0 only: written, gaps and ticks_seen per run in session.json chase_view)"
  else
    CHASE_COMPLETE=0; log "p10-2 chase recorder NOT rc 0 in every run: $(printf '%s; ' "${cbad[@]}" | sed 's/; $//')"
  fi
  # each run's actuation adapter (T4): its config event's heroActorId, or its error, from the fetched S-CORE output; a
  # run whose adapter never attached sent no command to the car, whatever its exit code
  local ad; ad=$(HERE="$HERE" python3 - "$IN/score/out" "$([[ " $FETCH_OK " == *" score "* ]] && echo 1 || echo 0)" \
    $(cut -f1 "$IN/score_runs.tsv" 2>/dev/null | awk '!s[$0]++') <<'PY'
import json, os, sys
sys.path.insert(0, os.environ["HERE"])
from adapter_attach import attach
ok, bad = [], []
for run in sys.argv[3:]:
    a = attach(sys.argv[1], run, sys.argv[2] == "1")
    if isinstance(a, dict) and a["heroActorId"] is not None:
        ok.append("%s (hero %s)" % (run, a["heroActorId"]))
    else:
        bad.append("%s (%s)" % (run, (a["error"] or "no config or error event in its record") if isinstance(a, dict) else a))
if bad:
    print("p10-2 adapter NO ATTACH in " + ", ".join(bad) + ("; attached in " + ", ".join(ok) if ok else ""))
else:
    print("p10-2 adapter attached in every run: " + ", ".join(ok))
PY
)
  log "$ad"
  if [[ " ${ROLES[*]} " != *" guest "* ]]; then
    P10_2_COMPLETE=none; P10_2_REASON="no display capture: --without-guest-host"; log "p10-2: $P10_2_REASON"; return 0
  fi
  for n in $(seq 1 "$P10_2_RUNS"); do
    w=run$n; x=$(tr ' ' '\n' <<< "$CAPTURES" | grep "^$w:" | tail -1)
    [ -n "$x" ] || { why+=("window $w: no end of its capture recorded (the session ended before it)"); continue; }
    IFS=: read -r _ e rc by k <<< "$x"
    [ "$e" = stop ] || why+=("window $w: capture ended ($e)")
    [ "$rc" = 0 ] || why+=("window $w: capture rc ${rc:-unknown}")
    [ "$by" = window_close ] || why+=("window $w: capture stopped at the ${by//_/ }")
    [ "$k" = 0 ] || why+=("window $w: guest files kept unpulled")
  done
  if [ ${#why[@]} = 0 ]; then
    P10_2_COMPLETE=1; P10_2_REASON="every window's capture ended by its stop at the window's close, rc 0, nothing kept on the guest"
    log "p10-2 display recording complete: $P10_2_REASON$PERM_NOTE"
  else
    P10_2_COMPLETE=0; P10_2_REASON=$(printf '%s; ' "${why[@]}"); P10_2_REASON=${P10_2_REASON%; }
    log "p10-2 display recording NOT complete: $P10_2_REASON$PERM_NOTE"
  fi
}
p10_1_report() {   # a p10-1 session judges only the checks that need the S-CORE host alone (without a CARLA server C1's
  # full start and C2-C4 are NOT RUN, C5 without a receive line of gatewayd, C8 without a replayer): which of the 8 did
  # not run or failed, from the fetched p10_1_verdicts.json, in one line of session.log and in session.json (p10_1)
  local f=$IN/score/out/p10_1/p10_1_verdicts.json line
  line=$(python3 - "$f" "$IN/p10_1_summary.json" <<'PY'
import json, sys
ids = ["C%d" % i for i in range(1, 9)]
try:
    doc = json.load(open(sys.argv[1], encoding="utf-8"))
    rows, cut = doc["checks"], doc.get("cut")
    found = True
except (OSError, ValueError, KeyError, TypeError, AttributeError):
    rows, found, cut = [], False, None
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
if cut:
    line += "; the check was cut by %s during part %s" % (cut.get("signal"), cut.get("part"))
ok = not not_run and not failed and found
line += "; P10-1 passed" if ok else "; P10-1 NOT passed"
json.dump({"line": line, "verdicts_file_fetched": found, "not_run": not_run, "fail": failed, "pass": passed,
           "passed": ok, "cut": cut}, open(sys.argv[2], "w"), indent=1)
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
  ENDED_BY="$ENDED_BY" STOPS="$STOPS" TERMED_STEP="$TERMED_STEP" TERMED_NAME="$TERMED_NAME" \
  TERMED_AFTER="$TERMED_AFTER" TERMED_FAIL="$TERMED_FAIL" P10_3_PASSED="${P10_3_PASSED:-}" \
  P10_3_REASON="${P10_3_REASON:-}" CROSVM_BEFORE="${CROSVM_BEFORE:-}" CAPTURES="$CAPTURES" \
  P10_2_COMPLETE="${P10_2_COMPLETE:-}" P10_2_REASON="${P10_2_REASON:-}" \
  CAMCAL_SOURCE="$CAMCAL_SOURCE" CAMCAL_REASON="$CAMCAL_REASON" CAMCAL_XCHECK="$CAMCAL_XCHECK" \
  CAMCAL_PRECHECK="$CAMCAL_PRECHECK" DISK_RC="${DISK_RC:-}" DISK_LINE="${DISK_LINE:-}" NEED_DISK="${NEED_DISK:-}" \
  NEED_DISK_STAGE="${NEED_DISK_STAGE:-}" RRD_RATE_BPS="$RRD_RATE_BPS" ROLES_ALL="${STARTED[*]}" \
  CHASE="$CHASE" CHASE_COMPLETE="${CHASE_COMPLETE:-}" HERE="$HERE" SCORE_FETCHED="$([[ " $FETCH_OK " == *" score "* ]] && echo 1)" \
  LOST="${LOST:-}" OWED_TEXT="$(owed)" FETCH_PARALLEL="$FETCH_PARALLEL" FETCH_RANGE_MIB="$FETCH_RANGE_MIB" \
  RENV="$(for x in $REMOTE_ENV_SET; do n=${x#*:}; printf '%s\t%s\t%s\n' "${x%%:*}" "$n" "${RVAL[$n]}"; done)" python3 - <<'PY'
import json, os, sys
e = os.environ
sys.path.insert(0, e["HERE"])
from adapter_attach import attach
p10_1 = os.path.join(e["IN"], "p10_1_summary.json")
ips = dict(x.split("=", 1) for x in e["IPS"].split() if "=" in x)
starts = [l.split() for l in open(os.path.join(e["IN"], "starts.tsv")) if l.strip()]
camcal = {"camera_calibration_source": e["CAMCAL_SOURCE"], "camera_calibration_source_reason": e["CAMCAL_REASON"],
          "camera_calibration_cross_check": e["CAMCAL_XCHECK"] or None} if e["KIND"] == "p10-2" else {}
try:
    precheck = json.loads(e["CAMCAL_PRECHECK"]) if e["CAMCAL_PRECHECK"] else None
except ValueError:
    precheck = None
score_runs = {}
try:
    for line in open(os.path.join(e["IN"], "score_runs.tsv"), encoding="utf-8"):
        run, key, value = (line.rstrip("\n").split("\t", 2) + ["", ""])[:3]
        score_runs.setdefault(run, {})[key] = value
except OSError:
    pass
for run, d in score_runs.items():
    for key in ("speed_limit_mps", "run_cap_s"):
        if key in d:
            d[key] = float(d[key])
    if "staged" in d:   # the start's SCORE_CONFIG words; None: the start printed none
        d["staged"] = dict(w.split("=", 1) for w in d["staged"].split() if "=" in w) or None
    if "planned_running_s" in d:
        d["planned_running_s"] = int(d["planned_running_s"])
    # the run's actuation adapter: its heroActorId or its error, from the fetched S-CORE output (T4)
    d["adapter"] = attach(os.path.join(e["IN"], "score", "out"), run, e["SCORE_FETCHED"] == "1")
    try:   # the stop's record of the candidate's Rerun record, kept on the S-CORE host (computed there)
        d["candidate_rrd"] = json.load(open(os.path.join(e["IN"], "score", "out", "score_" + run, "candidate_rrd.json")))
    except (OSError, ValueError):
        d["candidate_rrd"] = None
excluded = {}
for role in e["ROLES_ALL"].split():
    try:
        rows = [l.rstrip("\n").split("\t") for l in open(os.path.join(e["IN"], role, "out", "pack_excluded.tsv"))]
    except OSError:
        continue
    excluded[role] = [{"path": r[0], "bytes": int(r[1]) if r[1:] and r[1].isdigit() else None} for r in rows if r[0]]
chase = {}
for x in e["CHASE"].split():
    run, rc = x.split(":", 1)
    try:
        summ = json.load(open(os.path.join(e["IN"], "sim", "out", "rec_" + run, "summary.json")))
        summ = summ if isinstance(summ, dict) else {}
    except (OSError, ValueError):
        summ = {}
    # "complete" is the recorder's rc 0 only (T6): its written frames, gaps and ticks seen stand beside it
    chase[run] = {"complete": rc == "0", "rc": int(rc) if rc.isdigit() else None, "end": summ.get("end"),
                  "written": summ.get("written"), "gaps": summ.get("gaps"), "ticks_seen": summ.get("ticks_seen")}
hosts_lost = {}
try:
    for line in open(os.path.join(e["IN"], "hosts_lost.tsv"), encoding="utf-8"):
        role, status, at, by, pre = (line.rstrip("\n").split("\t") + [""] * 5)[:5]
        hosts_lost.setdefault(role, {"status": status, "detected_at": at, "detected_by": by,
                                     "preempted_at": pre or None})
except OSError:
    pass
lost = e["LOST"].split()
owed = {}   # a pack left on its host, over the fetch budget or after a failed ranged fetch (R2): its last row
try:
    for line in open(os.path.join(e["IN"], "fetch_owed.tsv"), encoding="utf-8"):
        role, sha, size, kept, n = (line.rstrip("\n").split("\t") + [""] * 5)[:5]
        owed[role] = (sha, size, kept, n)
except OSError:
    pass
not_fetched = []
for r in e["FETCH_BAD"].split():   # a host lost names where its records wait (R12b), an owed pack its sha256 (R2)
    if r in lost:
        x = "%s: %s" % (r, e["OWED_TEXT"])
    elif r in owed:
        sha, size, kept, n = owed[r]
        x = "%s: ~/da-kit/%s/out.tgz sha256 %s %s B (fetch owed%s)" % (
            r, e["SID"], sha, size, "; %s of %s ranges whole in %s/.ranges" % (kept, n, r) if kept not in ("", "0") else "")
    else:
        x = r
    if x not in not_fetched:
        not_fetched.append(x)
disk = None
if e["KIND"] == "p10-2" and e["NEED_DISK"]:
    words = e["DISK_LINE"].split()[1:]
    disk = {"rate_bytes_per_s": int(e["RRD_RATE_BPS"]), "margin": "10 % and 5000000000 B",
            "planned_running_s": {r: d.get("planned_running_s") for r, d in score_runs.items()},
            "need_bytes": int(e["NEED_DISK"]), "need_stage_bytes": int(e["NEED_DISK_STAGE"]),
            "rc": int(e["DISK_RC"]) if e["DISK_RC"].isdigit() else None,
            "result": dict(w.split("=", 1) for w in words if "=" in w) or None}
def num(x):
    return int(x) if x.isdigit() else None
fetch = {}   # each host's last fetch (F7): ranges through IAP, scp otherwise
try:
    for line in open(os.path.join(e["IN"], "fetch.tsv"), encoding="utf-8"):
        role, method, size, sha, bound, n, tries, secs, result = (line.rstrip("\n").split("\t") + [""] * 9)[:9]
        d = {"method": method, "bytes": num(size), "sha256": sha or None, "bound_s": num(bound), "result": result}
        if method == "ranges":
            d.update({"ranges": num(n), "tries": num(tries), "seconds": num(secs),
                      "parallel": int(e["FETCH_PARALLEL"]), "range_mib": int(e["FETCH_RANGE_MIB"]),
                      "ranges_file": role + "/fetch_ranges.tsv"})
        fetch[role] = d
except OSError:
    pass
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
           "camera_calibration_source": camcal.get("camera_calibration_source"),
           "camera_calibration_source_reason": camcal.get("camera_calibration_source_reason"),
           "camera_calibration_cross_check": camcal.get("camera_calibration_cross_check"),
           "camera_capture_precheck": precheck,
           "conditional_on_permissive_ivi": e["PERM"] == "1",
           "vm_status_after": dict(x.split("=", 1) for x in e["VM_AFTER"].split() if "=" in x),
           "left_running": e["LEFT"].split(), "exit_code_without_left_running": int(e["RC_STEPS"]),
           "remote_env": renv, "fetched": e["FETCH_OK"].split(), "not_fetched": not_fetched, "fetch": fetch,
           "hosts_lost": hosts_lost,
           "ended_by": e["ENDED_BY"] or None,
           "score_stops": {run: {"step": step, "rc": int(rc) if rc.lstrip("-").isdigit() else None,
                                 "stop_killed": rc == "7"}
                           for run, step, rc in (x.split(":", 2) for x in e["STOPS"].split())},
           "p10_1": json.load(open(p10_1)) if os.path.exists(p10_1) else None,
           "score_runs": score_runs if e["KIND"] == "p10-2" else None,
           "score_disk_check": disk,
           "chase_view": chase,
           "not_fetched_from_hosts": excluded,
           "app_record_receipts": {w: (int(n) if n.isdigit() else None)
                                   for w, n in (x.split("=", 1) for x in e["RECEIPTS"].split() if "=" in x)},
           "step_ended_by_term": {"host": e["TERMED_STEP"], "step": e["TERMED_NAME"],
                                  "status_after_term": e["TERMED_AFTER"], "fail_line": e["TERMED_FAIL"] or None}
                                 if e["TERMED_STEP"] else None,
           "crosvm_before_guest_up": int(e["CROSVM_BEFORE"]) if e["CROSVM_BEFORE"].isdigit() else None,
           "p10_3": {"passed": e["P10_3_PASSED"] == "1", "reason": e["P10_3_REASON"]}
                    if e["KIND"] == "p10-3" else None,
           "display_capture": {w: {"end": None if end == "unknown" else end,
                                   "capture_rc": int(rc) if rc.isdigit() else None,
                                   "closed_by": by.replace("_", " "), "guest_files_kept": k == "1"}
                               for w, end, rc, by, k in (x.split(":", 4) for x in e["CAPTURES"].split())},
           "p10_2": {"display_recording_complete": {"1": True, "0": False}.get(e["P10_2_COMPLETE"]),
                     "reason": e["P10_2_REASON"], "conditional_on_permissive_ivi": e["PERM"] == "1",
                     "chase_view_complete": {"1": True, "0": False}.get(e["CHASE_COMPLETE"]), **camcal}
                    if e["KIND"] == "p10-2" else None},
          open(os.path.join(e["IN"], "session.json"), "w"), indent=1)
PY
}
on_signal() {
  local eb0=$ENDED_BY
  trap '' INT TERM HUP; log "signal $1"; FINAL_RC=$2; ENDED_BY="signal $1"
  # the host watch's TERM: a VM this session started read lost (R12b); the trap names it (host_lost) and exits 3. A loss
  # the session had named already stays ended_by (R4 of the closure check of 1bfbd6b4)
  if [ "$1" = TERM ] && [ -f "$IN/.host_lost" ]; then
    FINAL_RC=3; ENDED_BY=""; [[ "$eb0" == "host lost: "* ]] && ENDED_BY=$eb0
  fi
  [ -f "$IN/.cap_reached" ] && { FINAL_RC=10; ENDED_BY=cap; }
  exit "$FINAL_RC"
}
trap cleanup EXIT
trap 'on_signal TERM 143' TERM
trap 'on_signal INT 130' INT
trap 'on_signal HUP 129' HUP

log "SESSION_START $SID kind=$KIND hosts=${ROLES[*]} cap=$CAP EUR dry_run=$DRY sim_ssh_iap=$SIM_SSH_IAP permissive_ivi=$IVI_PERMISSIVE"
[ "$IVI_PERMISSIVE" = 1 ] && log "every result of this session is conditional on a permissive IVI (--permissive-ivi)"
[ "$KIND" = p10-2 ] && log "camera calibration source: $CAMCAL_SOURCE (--camcal): $CAMCAL_REASON"

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
log "pre-stop budget: $PRESTOP_S s ($PRE_PARTS); safety net at the cap plus it plus $SAFETY_MARGIN_MIN min"
[[ " ${ROLES[*]} " == *" guest "* ]] && log "step bounds: unit $T_UNIT s (UNIT_WAIT_S + 240), app_restart $T_APP_RESTART s (START_WAIT_S +" \
  "APP_SUBSCRIBE_WAIT_S + 300)"
[[ " ${ROLES[*]} " == *" guest "* ]] && log "display capture caps: --max-s $CAP_MAX_S (the longest $KIND window that ends" \
  "well), --wait-cap-s $CAP_WAIT_S (the stop's cap within T_CAPTURE_END $T_CAPTURE_END s)"

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
  p10-1) NEED+=("$ENTRY_SIM_SETUP" "$ENTRY_SIM_WARMUP" "$ENTRY_SIM_RUN" "$ENTRY_SCORE_P10_1" world-side/da_world_side.py) ;;
  p10-3) NEED+=("${GUEST_NEED[@]}" "$ENTRY_SCORE_START" "$ENTRY_SCORE_INJECT" "$ENTRY_SCORE_STOP") ;;
  p10-2) NEED+=("$ENTRY_SIM_SETUP" "$ENTRY_SIM_WARMUP" "$ENTRY_SIM_CALIBRATE" "$ENTRY_SIM_RUN" "$ENTRY_SIM_RECORD"
                "$ENTRY_SCORE_START" "$ENTRY_SCORE_STOP" "$ENTRY_SCORE_DISK" world-side/da_world_side.py world-side/camera_calibration.py)
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
# each run's setting and speed_limit (F2), from world-side/scenarios.py through run_setting.py, before any VM starts;
# score_runs.tsv holds what session.json's score_runs says per run: <run> <key> <value>
declare -A RUN_SET=() RUN_SPEED=() RUN_CAP=(); PLAN_TOTAL_S=0; PLAN_MAX_S=0; DISK_RC=""; DISK_LINE=""
srun() { printf '%s\t%s\t%s\n' "$1" "$2" "$3" >> "$IN/score_runs.tsv"; }
plan_run() {   # plan_run <label> <scenario> <setting>
  local line id sp cap lo hi
  line=$(python3 "$HERE/run_setting.py" "$2" "$3" 2>&1) || fail 2 "refused: no setting for $1 ($2 $3): $line"
  read -r id sp cap lo hi <<< "$line"
  RUN_SET[$1]=$id; RUN_SPEED[$1]=$sp; RUN_CAP[$1]=$cap
  local plan=$(( ${cap%.*} + RRD_HOLD_S ))
  PLAN_TOTAL_S=$(( PLAN_TOTAL_S + plan )); [ "$plan" -gt "$PLAN_MAX_S" ] && PLAN_MAX_S=$plan
  srun "$1" setting "$id"; srun "$1" speed_limit_mps "$sp"; srun "$1" run_cap_s "$cap"; srun "$1" planned_running_s "$plan"
  srun "$1" speed_limit_source "bench proposal: world-side/scenarios.py $id: the middle of its tolerance $lo to $hi km/h, in m/s (System 2 sets speed_limit per scenario, PSR VisionPilotSCOREApplication)"
  log "run $1: setting $id, the candidate's speed_limit $sp m/s (the middle of $lo to $hi km/h), run cap $cap s"
}
if [ "$KIND" = p10-2 ]; then
  [ "$P10_2_CALIB_STEER" = 1 ] && plan_run calib_steer ASM-DRIVING-006 "$P10_2_SETTING"
  for _n in $(seq 1 "$P10_2_RUNS"); do plan_run "run$_n" "$P10_2_SCENARIO" "$P10_2_SETTING"; done
  NEED_DISK=$(( RRD_RATE_BPS * PLAN_TOTAL_S * 11 / 10 + RRD_MARGIN_B ))
  NEED_DISK_STAGE=$(( RRD_RATE_BPS * PLAN_MAX_S * 11 / 10 + RRD_MARGIN_B ))
  log "disk budget of the S-CORE host for the candidate's Rerun records: $RRD_RATE_BPS B/s x $PLAN_TOTAL_S s of planned running, plus 10 % and $RRD_MARGIN_B B: $NEED_DISK B ($NEED_DISK_STAGE B for the longest run in the stage)"
fi
EUR_H=0; for r in "${ROLES[@]}"; do EUR_H=$(awk -v a="$EUR_H" -v b="$(var "$r" EUR_H)" 'BEGIN{print a+b}'); done
CAP_S=$(awk -v c="$CAP" -v h="$EUR_H" 'BEGIN{printf "%d", c / h * 3600}')
# the fetch at the end runs inside the cap (R6 of the closure check of 1bfbd6b4): the cap must hold the runs and it
log "preflight ok: hosts ${ROLES[*]} at $EUR_H EUR/h together; the cap of $CAP EUR is $CAP_S s of all of them, the fetch at the end included (a host by ranges up to $PRE_FETCH_S s, a host by scp up to $FETCH_SCP_S s)"

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
start_hostwatch() {
  # R12b: a role VM lost while none of its steps is polled (20261119T203947Z: the S-CORE host was preempted while the
  # session ran guest steps, and nothing read it for 5 minutes). Every HOST_WATCH_S: one bounded `instances list` per
  # project of the VMs this session started and saw RUNNING after their preemption check (.watch_roles), and only
  # before the trap begins its own stops (.trap_stopping, the trap's first write). A VM that reads anything but
  # RUNNING ends the session by TERM, with .host_lost naming it; the trap then calls host_lost for it. Guarded as the
  # cost watchdog: it ends with the session and never signals a PID that is no longer the session's
  ( trap - EXIT TERM INT HUP
    while sleep "$HOST_WATCH_S"; do
      main_alive || exit 0
      [ -e "$IN/.trap_stopping" ] && exit 0
      roles=$(cat "$IN/.watch_roles" 2>/dev/null); [ -n "$roles" ] || continue
      for p in $(for r in $roles; do var "$r" PROJECT; done | sort -u); do
        echo "$(date -u +%FT%T.%3NZ) + gcloud --configuration=$GCLOUD_CONFIGURATION --project=$p compute instances list --format=value(name,status) [host watch] [timeout $HOST_WATCH_TO_S s]" >> "$CMDS"
        timeout "$HOST_WATCH_TO_S" "$GCLOUD" --configuration="$GCLOUD_CONFIGURATION" --project="$p" compute instances list \
          --format='value(name,status)' > "$IN/.hw_$p" 2>/dev/null < /dev/null || continue
        for r in $roles; do
          [ "$(var "$r" PROJECT)" = "$p" ] || continue
          st=$(awk -v vm="$(var "$r" VM)" '$1 == vm { print $NF }' "$IN/.hw_$p")
          [ -n "$st" ] && [ "$st" != RUNNING ] || continue   # no row (a failed read) is no answer, never a loss
          [ -e "$IN/.trap_stopping" ] && exit 0
          # a role the session named lost itself (host_lost writes .lost_known first): no TERM for it (R1, R4)
          grep -q -x -F "$r" "$IN/.lost_known" 2>/dev/null && continue
          main_alive || exit 0
          printf '%s %s %s\n' "$r" "$st" "$(date -u +%FT%TZ)" > "$IN/.host_lost.tmp" && mv "$IN/.host_lost.tmp" "$IN/.host_lost"
          echo "$(date -u +%FT%TZ) HOST LOST: $(var "$r" VM) ($r) reads $st in the host watch while none of its steps may be polled: ending the session (exit 3)" >> "$LOG"
          kill -TERM "$MAIN_PID"; exit 0
        done
      done
    done ) 2> /dev/null &
  HW_PID=$!; disown "$HW_PID"
  log "host watch pid $HW_PID: every $HOST_WATCH_S s the state of each VM this session started (ends with the session)"
}
start_vm() {   # start_vm <role>: returns 0 when RUNNING, and still RUNNING after the preemption check
  local r=$1 vm zone deadline n=0 out rc st c i
  vm=$(var "$r" VM); zone=$(var "$r" ZONE); deadline=$(( $(date +%s) + START_DEADLINE_S ))
  while :; do
    n=$((n + 1))
    register_start "$r"
    [ -z "$WD_PID" ] && start_watchdog
    [ -z "$HW_PID" ] && start_hostwatch
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
      echo "$r" >> "$IN/.watch_roles"   # from here on the host watch reads it (R12b)
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
  # the cap, plus the trap's pre-stop phase bound (the S-CORE host's power-off never cuts its own fetch, S9), plus the
  # margin for the trap's stops
  gmin=$(( (CAP_S + PRESTOP_S) / 60 + SAFETY_MARGIN_MIN ))
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
  # S1 (README): the trap's stop of a guest host that never answered SSH assumes that no guest runs there before the
  # session starts one; guest_up counts crosvm before its launch, and its tail's last line carries the count
  CROSVM_BEFORE=$(grep -o 'CROSVM_BEFORE_LAUNCH [0-9a-z]*' "$IN/guest.steps.out" | tail -1 | cut -d' ' -f2)
  case "${CROSVM_BEFORE:-unknown}" in
    0) log "crosvm processes on the guest host before guest_up: 0 (S1 held for this run: no guest ran before the session started one)" ;;
    *[!0-9]*|"") CROSVM_BEFORE=unknown
       log "crosvm processes on the guest host before guest_up: unknown (no count in guest_up's tail): S1 not checked this run" ;;
    *) log "S1 VOID: $CROSVM_BEFORE crosvm process(es) on the guest host before guest_up: a guest ran before this session started one; tell the lead before the next session, and do not rely on the stop without a crosvm count" ;;
  esac
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
  rstep guest "app_restart_$w" "$T_APP_RESTART" "$GENV" bash "$ENTRY_GUEST_APP_RESTART" "$(od app_restart)" "$w"
  rstep guest "ivi_clock_$w" "$T_STEP" bash "$ENTRY_GUEST_CLOCK" set "$(od "ivi_clock_$w")"
  # open from before its start call: an answer lost on the way may still have started it (Q1)
  CAP_OPEN=$w
  rstart guest "capture_$w" "$GENV" bash "$ENTRY_GUEST_CAPTURE" start "$(od "capture_$w")" --max-s "$CAP_MAX_S"
}
window_close() {
  local w=$1 crc=0 f=$IN/.capstop
  rstep guest "capture_stop_$w" "$T_CAPTURE_END" bash "$ENTRY_GUEST_CAPTURE" stop "$(od "capture_$w")" \
    --wait-cap-s "$CAP_WAIT_S"
  printf '%s\n' "$ROUT" > "$f"   # the stop's tail: capture.done's line
  if ! rwait guest "capture_$w" "$T_CAPTURE_END"; then
    # END=error (no answer from the guest, or two early ends): capture.done, the app's records and capture.json are
    # written and the capture exits 1. The error is recorded, the receipts are read and the session goes on (Q2)
    if [ "$ROUT" = "rc 1" ] && grep -q '^capture ended (error)' "$f"; then
      crc=1; STEP_FAIL=""   # rwait named the capture: a recorded error of the window, not a failed step (R7)
      log "DISPLAY CAPTURE ERROR IN WINDOW $w: $(grep '^capture ended (error)' "$f" | tail -1); its app records and" \
        "capture.json were written, so the receipts are read and the session goes on (session.json display_capture)"
    else
      rm -f "$f"; abort 5 "the display capture of $w did not end well"
    fi
  fi
  CAP_OPEN=""; capture_end "$w" "window close" "$crc" "$f"; rm -f "$f"
  # the app's own record of the window: no receipt means the path did not carry, whatever the steps said (R7). Only
  # the receipt events after the window's app start count (the start of the pid app_restart.sh read), never the
  # record's lines: it is appended, and every start writes lifecycle, link and status lines (W1)
  rstep guest "receipts_$w" "$T_STEP" bash "$ENTRY_GUEST_OFFER_CHECK" receipts "$(od "capture_$w")" \
    "$(od app_restart)/app_restart_$w.txt"
  local n; n=$(grep -o 'RECEIPTS [0-9]*' "$IN/guest.steps.out" | tail -1 | cut -d' ' -f2)
  RECEIPTS="${RECEIPTS:-} $w=${n:-unknown}"
  if [ "${n:-0}" = 0 ]; then
    log "NO RECEIPT IN THE APP'S RECORD OF WINDOW $w (${n:-no count}) since the window's app start: the warning path" \
      "did not carry; see guest/out/capture_$w/"
  else
    log "window $w: $n receipt event(s) in the app's record since the window's app start"
  fi
}
score_config_check() {   # score_config_check <label> <the start's SCORE_CONFIG line>: the staged conf carries the
  # run's speed_limit and the identity record hashes that conf, before the go; recorded either way
  local w=$1 cfg=${2#SCORE_CONFIG } x sp="" recd=""
  if [ -z "$2" ]; then
    srun "$w" staged ""
    [ "$DRY" = 1 ] || { STEP_FAIL="score_start_$w"; abort 5 "no SCORE_CONFIG line from the S-CORE start of $w: its speed_limit is not shown staged"; }
    log "speed_limit ${RUN_SPEED[$w]} m/s for $w requested; the start printed no SCORE_CONFIG line (the dry run's stub)"
    return 0
  fi
  srun "$w" staged "$cfg"
  for x in $cfg; do case "$x" in speed_limit=*) sp=${x#*=} ;; conf_recorded=*) recd=${x#*=} ;; esac; done
  if [ "$sp" != "${RUN_SPEED[$w]}" ] || [ "$recd" != 1 ]; then
    STEP_FAIL="score_start_$w"
    abort 5 "the staged vision_pilot.conf of $w does not carry the run's speed limit ${RUN_SPEED[$w]} m/s, or the identity record does not hash it: $cfg"
  fi
  log "speed_limit ${RUN_SPEED[$w]} m/s for $w staged, and the identity record hashes that vision_pilot.conf: $cfg"
}
disk_check() {   # p10-2's first step: room on the S-CORE host for every run's Rerun record, which stays there (F3)
  ALLOW_RC=9 rstep score disk_check "$T_STEP" bash "$ENTRY_SCORE_DISK" "$(od disk_check)" "$NEED_DISK" "$NEED_DISK_STAGE"
  DISK_RC=$STEP_RC; DISK_LINE=$(grep -o 'DISK_CHECK .*' <<< "$ROUT" | tail -1)
  if [ "$DISK_RC" = 9 ]; then
    STEP_FAIL=disk_check
    abort 5 "DISK SPACE SHORT on $(var score VM): the candidate's Rerun records of this session need $NEED_DISK B ($PLAN_TOTAL_S s of planned running at $RRD_RATE_BPS B/s, plus 10 % and $RRD_MARGIN_B B); no run starts: ${DISK_LINE:-no DISK_CHECK line}"
  fi
  log "disk check on $(var score VM): ${DISK_LINE:-no DISK_CHECK line} (need $NEED_DISK B)"
}
world_run() {   # world_run <label> <scenario> <setting> <recorded 0|1> <another run follows 0|1>: one run with its own
  # S-CORE side
  local w=$1 sc=$2 se=$3 rec=$4 more=${5:-0} o; o=$(od "world_$w")
  [ "$rec" = 1 ] && { rstart sim "rec_$w" "$SIM_PY" "$ENTRY_SIM_RECORD" --out "$(od "rec_$w")"; rlisten "$w"; }
  rstart sim "world_$w" "$SENV" bash "$ENTRY_SIM_RUN" "$o" "$sc" "$se"
  rwaitfile sim "world_$w" "$o/simulator/ready.json" "$T_READY" || { abort 5 "the world side of $w is not ready"; }
  # the S-CORE side after ready.json (the hero stands), with the camera calibration file of this session
  [ "$HAS_GUEST" = 1 ] && [ "$rec" = 1 ] && logmark "$w"
  SCORE_RUN=$w
  # the go clock starts before the start step: the candidate's ready time-out runs from its process start inside
  # that step, which this host sees end only a poll later (S5); so the bound errs early, never late
  local t_up; t_up=$(date +%s)
  # speed_limit from the run's setting (F2 of 20261119T174606Z: the model has System 2 set it per scenario, PSR
  # VisionPilotSCOREApplication; the bench left upstream's 33.3 m/s and the car reached 108.9 km/h)
  rstep score "score_start_$w" "$T_SCORE_START" env "DA_CAMERA_CALIBRATION_DIR=$CAMCAL_DIR" \
    "DA_SPEED_LIMIT=${RUN_SPEED[$w]}" bash "$ENTRY_SCORE_START" "$(od "score_$w")" "$CARLA_HOST"
  local cfg; cfg=$(grep -o 'SCORE_CONFIG .*' <<< "$ROUT" | tail -1)
  SCORE_UP=$(od "score_$w")
  score_config_check "$w" "$cfg"
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
  # the chase recorder's own end, rc 0 or not, is a result of the run's window (F4 of 20261119T174606Z: its rc 1 ended
  # the session and skipped receipts_run1 and run 2): recorded per run (session.json chase_view), the window's capture
  # stop, receipts and the next run go on. Only a recorder still running at its bound (it would attach to the next
  # run's hero) or a lost host ends the session
  if [ "$rec" = 1 ]; then
    if rwait sim "rec_$w" "$T_REC_END"; then CHASE="$CHASE $w:0"
    elif [[ "$ROUT" =~ ^rc\ ([0-9]+)$ ]]; then
      CHASE="$CHASE $w:${BASH_REMATCH[1]}"; STEP_FAIL=""   # rwait named the recorder: a recorded result, not a failed step
      log "CHASE VIEW NOT COMPLETE IN RUN $w: the recorder ended rc ${BASH_REMATCH[1]} (its summary's end goes to session.json chase_view); the window's capture stop, its receipts and the next run go on"
    else
      abort 5 "the recorder of $w did not end well (${ROUT:-no answer})"
    fi
  fi
  if [ "$HAS_GUEST" = 1 ] && [ "$rec" = 1 ]; then window_close "$w"; fi
  # a stop that had to kill, with another run to come: this run is complete and recorded, but the next one would
  # start from a suspect state while every VM bills; the session ends here (the lead's decision, S7)
  if [ "$STOP_KILLED_LAST" = "score_stop_$w" ] && [ "$more" = 1 ]; then
    STEP_FAIL="score_stop_$w"; ENDED_BY="score_stop_$w had to kill (rc 7) and another run would follow"
    abort 5 "the S-CORE stop of $w had to kill (rc 7): no further run from a suspect state"
  fi
}
port_test() {   # p10-1: CARLA's ports on the simulator host, from the S-CORE host, before any Launch Manager start
  # there: one bounded TCP connect per port (5 s each, the SSH call 60 s at most), the result in one line of session.log
  local p line="" ok=1; SEQ+=("score:port_test")
  log "port test on $(var score VM): a TCP connect to $CARLA_HOST, ports $CARLA_PORTS, 5 s each"
  rout ssh_l score 60 "for p in $CARLA_PORTS; do if timeout 5 bash -c \"</dev/tcp/$CARLA_HOST/\$p\" 2>/dev/null; then echo \"tcp \$p open\"; else echo \"tcp \$p closed\"; fi; done"
  for p in $CARLA_PORTS; do
    if grep -q -x "tcp $p open" <<< "$ROUT"; then line="$line, tcp $p open"
    elif grep -q -x "tcp $p closed" <<< "$ROUT"; then ok=0; line="$line, tcp $p closed"
    else ok=0; line="$line, tcp $p no answer"; fi
  done
  line="from $(var score VM) to the simulator host $CARLA_HOST: ${line#, }"
  if [ "$ok" = 1 ]; then log "PORT TEST $line"; return 0; fi
  log "PORT TEST FAILED $line: the session ends before any Launch Manager start"
  STEP_FAIL=port_test; abort 5 "the port test failed: no Launch Manager start"
}
make_h() {   # on this host: the capture from the simulator host, make-h, both files onto the S-CORE host
  local d=$IN/camcal src="da-kit/$SID/out/calibrate/camcal/simulator" vm f rc loc got
  vm=$(var sim VM); mkdir -p "$d/capture"; SEQ+=("lead:make_h")
  log "step make_h on this host: the camera capture from $vm, then camera_calibration.py make-h --source $CAMCAL_SOURCE"
  routall scp_r sim 300 "$vm:$src/camera_capture.json" "$vm:$src/calibration_frame.png" "$d/capture/"
  printf '%s\n' "$ROUT" | one >> "$LOG"
  [ -s "$d/capture/camera_capture.json" ] && [ -s "$d/capture/calibration_frame.png" ] \
    || { STEP_FAIL=make_h; abort 5 "make_h: the camera capture did not arrive"; }
  if [ -n "$MAKE_H" ]; then
    timeout "$T_MAKE_H" "$MAKE_H" --capture "$d/capture/camera_capture.json" --out-dir "$d/h" \
      --source "$CAMCAL_SOURCE" > "$d/make_h.log" 2>&1; rc=$?
  else
    mkdir -p "$d/code" && tar -xzf "$KIT" -C "$d/code" bench/world-side
    timeout "$T_MAKE_H" "$CV_PY" "$d/code/bench/world-side/camera_calibration.py" make-h \
      --capture "$d/capture/camera_capture.json" --vp-clone "$VP_CLONE" --python "$CV_PY" --out-dir "$d/h" \
      --source "$CAMCAL_SOURCE" > "$d/make_h.log" 2>&1; rc=$?
  fi
  log "step make_h rc=$rc"
  for f in H.yaml homography_C_matrix.yaml; do
    [ "$rc" = 0 ] && [ -s "$d/h/$f" ] || { STEP_FAIL=make_h; abort 5 "make_h: no $f (see camcal/make_h.log)"; }
  done
  # never a silent fallback: make-h's record must name the source this session's --camcal chose
  local made
  made=$(python3 - "$d/h/camera_calibration_record.json" "$d/capture/camera_capture.json" "$d/camcal_facts.json" \
    "$CAMCAL_SOURCE" <<'PY'
import json, sys
try:
    rec = json.load(open(sys.argv[1], encoding="utf-8"))
except (OSError, ValueError):
    rec = {}
try:
    pre = json.load(open(sys.argv[2], encoding="utf-8")).get("precheck")
except (OSError, ValueError, AttributeError):
    pre = None
x = rec.get("crossCheck")
if isinstance(x, dict):
    x = "maxRelErrXInRange %s (tolerance %s), agreeWithinProposal %s" % (x.get("maxRelErrXInRange"),
                                                                         x.get("tolerance"), x.get("agreeWithinProposal"))
if sys.argv[4] == "settings":   # upstream's script ran on no board frame: no cross-check exists
    x = "not run: no board rendered"
json.dump({"precheck": pre, "cross_check": x or "not in make-h's record"}, open(sys.argv[3], "w"))
print(rec.get("source") if isinstance(rec, dict) else None)
PY
)
  [ "$made" = "$CAMCAL_SOURCE" ] \
    || { STEP_FAIL=make_h; abort 5 "make_h: the record names the source $made, not --camcal $CAMCAL_SOURCE"; }
  CAMCAL_XCHECK=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["cross_check"])' "$d/camcal_facts.json")
  CAMCAL_PRECHECK=$(python3 -c 'import json, sys; print(json.dumps(json.load(open(sys.argv[1]))["precheck"]))' "$d/camcal_facts.json")
  log "camera calibration source $CAMCAL_SOURCE; cross-check: $CAMCAL_XCHECK; the capture's pre-check (recorded$([ "$CAMCAL_SOURCE" = settings ] && echo ', not enforced')): $CAMCAL_PRECHECK"
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
    # the check runs while a CARLA world ticks, so C1-C4 run (lead decision of 2026-11-19, part 2): the world side's
    # handshake of a p10-2 run, with the go before the check (the world ticks through its three parts) and the
    # release only after it ended (the check stops its own Launch Manager starts while the world still ticks). No
    # recorder and no calibration: p10-1 judges no driving and no geometry (the check names upstream's stand-in)
    rstep sim sim_setup "$T_SIM_SETUP" bash "$ENTRY_SIM_SETUP" "$(od sim_setup)"
    [ -n "$CARLA_HOST" ] || ipof sim CARLA_HOST
    log "CARLA host for the S-CORE side: $CARLA_HOST"
    port_test
    # the session's road in world_start.json, which run_scenario.sh needs: the warm-up entry's survey, then its pass
    rstep sim warmup "$T_WARMUP" "$SENV" bash "$ENTRY_SIM_WARMUP" "$(od warmup)"
    o=$(od world_p10_1)
    # after run_end.json the world ticks on until the release file or RELEASE_WAIT_S: longer than the check may run
    rstart sim world_p10_1 "env$(q "SIM_PY=$SIM_PY" "RELEASE_WAIT_S=$(( T_P10_1 + T_STEP ))")" bash "$ENTRY_SIM_RUN" \
      "$o" "$P10_1_SCENARIO" "$P10_1_SETTING"
    rwaitfile sim world_p10_1 "$o/simulator/ready.json" "$T_READY" || { abort 5 "the world side of p10-1 is not ready"; }
    rtouch sim "$o/go" || { STEP_FAIL=world_p10_1; abort 5 "no go file for p10-1"; }
    # the check starts and stops its own Launch Manager (setsid: the step's TERM does not reach it). Marked up for
    # the step, so a cut, the cap or the time-out also has the session's trap stop and collect it, into
    # p10_1/trap_stop, after the check's own cut handler (stop_score_side.sh runs one stop of a stage at a time).
    # Exit 1 is the check's FAIL verdict: the world is released and both hosts fetched all the same, then exit 12
    SCORE_RUN=p10_1; SCORE_UP="$(od p10_1)/trap_stop"
    ALLOW_RC=1 rstep score p10_1 "$T_P10_1" env "DA_P10_1_CARLA_HOST=$CARLA_HOST" bash "$ENTRY_SCORE_P10_1" "$(od p10_1)"
    SCORE_UP=""; P10_1_RC=$STEP_RC
    [ "$P10_1_RC" = 1 ] && log "step p10_1 rc=1: a check FAILed (the check's verdict, not a step failure): the world is released and both hosts fetched, then exit 12"
    rwaitfile sim world_p10_1 "$o/simulator/run_end.json" "$T_RUN" || { abort 5 "the world side of p10-1 did not end its run"; }
    rtouch sim "$o/release" || log "WARNING no release file for p10-1: the world side ends at its own hold limit"
    rwait sim world_p10_1 "$T_RELEASE" || { abort 5 "the world side of p10-1 did not end well"; }
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
    disk_check
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
    # its second argument is the calibration source: with settings the capture's pre-check is recorded, not enforced
    rstep sim calibrate "$T_CALIBRATE" "$SENV" bash "$ENTRY_SIM_CALIBRATE" "$(od calibrate)" "$CAMCAL_SOURCE"
    make_h
    [ "$P10_2_CALIB_STEER" = 1 ] && world_run calib_steer ASM-DRIVING-006 "$P10_2_SETTING" 0 "$([ "$P10_2_RUNS" -ge 1 ] && echo 1 || echo 0)"
    for n in $(seq 1 "$P10_2_RUNS"); do
      world_run "run$n" "$P10_2_SCENARIO" "$P10_2_SETTING" 1 "$([ "$n" -lt "$P10_2_RUNS" ] && echo 1 || echo 0)"
    done
    ;;
esac
log "SEQUENCE ${SEQ[*]}"
fetch_all || { [ -n "${LOST:-}" ] && fail 3 "evidence fetch incomplete: a host was lost"; ENDED_BY=fetch; fail 5 "evidence fetch incomplete"; }
ENDED_BY=steps
log "session steps done; the files are in $IN"
if [ "$P10_1_RC" = 1 ]; then ENDED_BY="steps; the p10_1 check FAILed"; FINAL_RC=12; exit 12; fi
FINAL_RC=0
exit 0
