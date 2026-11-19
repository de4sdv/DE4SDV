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
#   --carla-host <ip>      CARLA's address for the S-CORE side (default: the simulator host's internal IP, from gcloud)
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
IVI_PERMISSIVE=0
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
    -h|--help) sed -n '2,36p' "$0"; exit 0 ;;
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
POLL_S=20; WATCH_S=30; STOP_TRIES=30; STOP_POLL_S=10; SAFETY_MARGIN_MIN=10; STATUS_TRIES=5
T_P10_1=5400; T_GUEST_UP=2400; T_SCORE_START=900; T_SIM_SETUP=1200; T_WARMUP=900; T_RUN=900; T_INJECT=1200
T_CAPTURE_END=180; T_REC_END=200; T_STEP=300; T_CALIBRATE=1800; T_MAKE_H=600; T_READY=300; T_RELEASE=400
T_UNIT=300
KNOBS=(PREEMPT_CHECK_S ROUND_PAUSE_S START_DEADLINE_S RUNNING_WAIT_S SSH_TRIES SSH_PAUSE_S POLL_S WATCH_S STOP_TRIES
       STOP_POLL_S T_P10_1 T_GUEST_UP T_SCORE_START T_SIM_SETUP T_WARMUP T_RUN T_INJECT T_CAPTURE_END T_REC_END T_STEP
       T_CALIBRATE T_MAKE_H T_READY T_RELEASE T_UNIT STATUS_TRIES)
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
iap() { [ "$1" = sim ] && [ "$SIM_SSH_IAP" = 1 ] && echo --tunnel-through-iap; }   # D5: the simulator host by IAP
ssh_r() {   # ssh_r <role> <timeout_s> <remote command>
  local role=$1 to=$2 cmd=$3
  # shellcheck disable=SC2046  # iap prints one word or nothing
  timeout "$to" "$GCLOUD" --configuration="$GCLOUD_CONFIGURATION" --project="$(var "$role" PROJECT)" compute ssh \
    "$(var "$role" VM)" --zone "$(var "$role" ZONE)" $(iap "$role") --command "$cmd" < /dev/null
}
ssh_l() {   # logged ssh: the command goes to commands.log (and to stderr in a dry run)
  echo "$(date -u +%FT%T.%3NZ) + ssh $1: $3" >> "$CMDS"; [ "$DRY" = 1 ] && echo "+ ssh $1: $3" >&3
  ssh_r "$@"
}
scp_r() {   # scp_r <role> <timeout_s> <src...> <dst>
  local role=$1 to=$2; shift 2
  echo "$(date -u +%FT%T.%3NZ) + scp $role: $*" >> "$CMDS"; [ "$DRY" = 1 ] && echo "+ scp $role: $*" >&3
  # shellcheck disable=SC2046
  timeout "$to" "$GCLOUD" --configuration="$GCLOUD_CONFIGURATION" --project="$(var "$role" PROJECT)" compute scp \
    --zone "$(var "$role" ZONE)" $(iap "$role") "$@" < /dev/null
}
kill_tree() { local c; for c in $(pgrep -P "$1" 2>/dev/null); do kill_tree "$c"; done; kill "$1" 2>/dev/null; }
run_fg() { "$@" & CHILD=$!; wait "$CHILD"; local rc=$?; CHILD=""; return $rc; }   # signals interrupt the wait
nap() { run_fg sleep "$1"; }
cost_now() { awk -v now="$(date +%s.%N)" '{ s += (now - $2) * $3 / 3600 } END { printf "%.3f", s + 0 }' "$STARTS"; }
ge() { awk -v a="$1" -v b="$2" 'BEGIN { exit !(a >= b) }'; }
q() { printf ' %q' "$@"; }   # words quoted for the remote shell
GSTOP=${GUEST_STOP_CMD//\$DA_SESSION_ID/$SID}
crosvm_left() { run_fg ssh_l guest 60 "pgrep -c -x crosvm || true" 2>/dev/null | tail -1 | tr -dc 0-9; }

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
  local gpu=() guest=0
  for r in "${STARTED[@]}"; do if [ "$r" = guest ]; then guest=1; else gpu+=("$r"); fi; done
  # the GPU hosts first (they cost most), without waiting
  for r in "${gpu[@]}"; do
    log "stopping $(var "$r" VM) ($r)"
    GC_TO=300 gc "$r" compute instances stop "$(var "$r" VM)" --zone "$(var "$r" ZONE)" --async --quiet 2>&1 | one >> "$LOG"
  done
  if [ "$guest" = 1 ]; then
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
        for try in 1 2; do
          log "stopping the guests before their host (try $try): $GSTOP"
          out=$(ssh_l guest 300 "$GSTOP" 2>&1); echo "$out" | sanitize >> "$IN/guest_stop.out"
          left=$(crosvm_left)
          log "crosvm processes left on $(var guest VM): ${left:-unknown}"
          [ "$left" = 0 ] && break
        done ;;
    esac
    if [ "$left" = 0 ]; then
      log "stopping $(var guest VM) (guest)"
      GC_TO=300 gc guest compute instances stop "$(var guest VM)" --zone "$(var guest ZONE)" --async --quiet 2>&1 | one >> "$LOG"
    else
      log "GUEST HOST LEFT RUNNING: the guests did not stop (crosvm '${left:-unknown}'). Stop them by hand (cvd stop, no crosvm left), then the host"
      GUEST_LEFT=1
    fi
  fi
  for r in "${STARTED[@]}"; do
    [ "$r" = guest ] && [ "${GUEST_LEFT:-0}" = 1 ] && { log "status after the session: $(var guest VM) $(vmst guest) (left running)"; rc=11; continue; }
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
  KIT_SHA="${KIT_SHA:-}" BENCH_COMMIT="${BENCH_COMMIT:-}" WT_CHANGES="${WT_CHANGES:-}" DRY="$DRY" \
  IAP="$SIM_SSH_IAP" PERM="$IVI_PERMISSIVE" IPS="${IPS:-}" CAMCAL="${CAMCAL_SHA:-}" python3 - <<'PY'
import json, os
e = os.environ
ips = dict(x.split("=", 1) for x in e["IPS"].split() if "=" in x)
starts = [l.split() for l in open(os.path.join(e["IN"], "starts.tsv")) if l.strip()]
json.dump({"session_id": e["SID"], "kind": e["KIND"], "exit_code": int(e["RC"]), "dry_run": e["DRY"] == "1",
           "cap_eur": float(e["CAP"]), "started": e["STARTED"].split(),
           "start_calls_unix_s": {r: float(t) for r, t, _ in starts}, "eur_per_hour": {r: float(p) for r, _, p in starts},
           "failed_step": e["STEP_FAIL"] or None, "kit_sha256": e["KIT_SHA"] or None,
           "bench_commit": e["BENCH_COMMIT"] or None, "worktree_changes": e["WT_CHANGES"] or None,
           "sim_ssh_iap": e["IAP"] == "1", "internal_ips_from_gcloud": ips,
           "camera_calibration_sha256": dict(x.split("=", 1) for x in e["CAMCAL"].split() if "=" in x) or None,
           "conditional_on_permissive_ivi": e["PERM"] == "1"},
          open(os.path.join(e["IN"], "session.json"), "w"), indent=1)
PY
}
on_signal() { trap '' INT TERM HUP; log "signal $1"; FINAL_RC=$2; [ -f "$IN/.cap_reached" ] && FINAL_RC=10; exit "$FINAL_RC"; }
trap cleanup EXIT
trap 'on_signal TERM 143' TERM
trap 'on_signal INT 130' INT
trap 'on_signal HUP 129' HUP

log "SESSION_START $SID kind=$KIND hosts=${ROLES[*]} cap=$CAP EUR dry_run=$DRY sim_ssh_iap=$SIM_SSH_IAP permissive_ivi=$IVI_PERMISSIVE"
[ "$IVI_PERMISSIVE" = 1 ] && log "every result of this session is conditional on a permissive IVI (--permissive-ivi)"

# ───────────── 1. preflight: nothing below starts a VM unless every check holds ─────────────
fail() { FINAL_RC=$1; shift; log "$*"; exit "$FINAL_RC"; }
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
  # (the guest host: the guests' stop first, and no power-off while a crosvm is left; safety_net.sh)
  gmin=$(( CAP_S / 60 + SAFETY_MARGIN_MIN ))
  local net="bash ~/da-kit/$SID/bench/session/remote/safety_net.sh arm $gmin"
  [ "$r" = guest ] && net="$net$(q "$GSTOP")"
  run_fg ssh_l "$r" 60 "$net" 2>/dev/null | grep -q "safety-net-$gmin" \
    && log "$(var "$r" VM): kit ok, power-off safety net in $gmin min$([ "$r" = guest ] && echo ", the guests' stop first")" \
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
  log "step $s on $(var "$r" VM): $*"; SEQ+=("$r:$s")
  run_fg ssh_l "$r" "$to" "$HS run $s -- $*" >> "$IN/$r.steps.out" 2>&1; local rc=$?
  log "step $s rc=$rc"
  [ "$rc" = 0 ] || { STEP_FAIL=$s; fetch_all; fail 5 "step $s failed (rc $rc)"; }
}
rstart() { local r=$1 s=$2; shift 2; log "start $s on $(var "$r" VM): $*"; SEQ+=("$r:$s&")
  run_fg ssh_l "$r" 60 "$HS start $s -- $*" >> "$IN/$r.steps.out" 2>&1 || { STEP_FAIL=$s; fetch_all; fail 5 "start of $s failed"; }; }
rsignal() { run_fg ssh_l "$1" 60 "$HS signal $2 ${3:-INT}" >> "$IN/$1.steps.out" 2>&1; }
rwait() {   # rwait <role> <step> <timeout_s>: waits for a detached step's status
  local r=$1 s=$2 end st; end=$(( $(date +%s) + $3 )); SEQ+=("$r:wait-$s")
  while :; do
    st=$(run_fg ssh_l "$r" 60 "$HS status $s" 2>/dev/null | tail -1)
    case "$st" in "rc "*) log "step $s ${st}"; [ "$st" = "rc 0" ] && return 0; STEP_FAIL=$s; return 1 ;; esac
    [ "$(date +%s)" -ge "$end" ] && { log "step $s still ${st:-unknown} after $3 s"; STEP_FAIL=$s; return 1; }
    nap "$POLL_S"
  done
}
rwaitfile() {   # rwait_file <role> <step> <remote file> <timeout_s>: the file of a running detached step
  local r=$1 s=$2 f=$3 end st; end=$(( $(date +%s) + $4 )); SEQ+=("$r:file-${f##*/}")
  while :; do
    st=$(run_fg ssh_l "$r" 60 "test -e $f && echo present || $HS status $s" 2>/dev/null | tail -1)
    case "$st" in
      present) log "step $s: ${f##*/} present"; return 0 ;;
      "rc "*) log "step $s ended ($st) before ${f##*/}"; STEP_FAIL=$s; return 1 ;;
    esac
    [ "$(date +%s)" -ge "$end" ] && { log "step $s: no ${f##*/} after $4 s"; STEP_FAIL=$s; return 1; }
    nap "$POLL_S"
  done
}
rtouch() {   # rtouch <role> <remote file>: a handshake file of the world side
  log "touch ${2##*/} on $(var "$1" VM): $2"; SEQ+=("$1:touch-${2##*/}")
  run_fg ssh_l "$1" 60 "touch $2 && echo touched" 2>/dev/null | grep -q touched
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
ipof() {   # ipof <role> <var>: the internal IP, read from gcloud now (never configured: D5 may move the hosts)
  local ip; ip=$(vmip "$1"); [ -n "$ip" ] || fail 5 "no internal IP of $(var "$1" VM) from gcloud"
  IPS="${IPS:-} $1=$ip"; printf -v "$2" '%s' "$ip"
}

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
}
MCAST_DONE=0
offer_checks() {   # after an S-CORE side start (someipd offers 0x4df1 at 192.168.98.1:30511): route, then the unit
  local w=$1
  if [ "$MCAST_DONE" = 0 ]; then
    rstep guest mcast_route "$T_STEP" bash "$ENTRY_GUEST_OFFER_CHECK" route "$(od mcast_route)"; MCAST_DONE=1
  fi
  rstep guest "unit_$w" "$T_UNIT" bash "$ENTRY_GUEST_OFFER_CHECK" unit "$(od "unit_$w")"
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
  rwait guest "capture_$w" "$T_CAPTURE_END" || { fetch_all; fail 5 "the display capture of $w did not end well"; }
}
world_run() {   # world_run <label> <scenario> <setting> <recorded 0|1>: one run with its own S-CORE side
  local w=$1 sc=$2 se=$3 rec=$4 o; o=$(od "world_$w")
  [ "$rec" = 1 ] && rstart sim "rec_$w" "$SIM_PY" "$ENTRY_SIM_RECORD" --out "$(od "rec_$w")"
  rstart sim "world_$w" "$SENV" bash "$ENTRY_SIM_RUN" "$o" "$sc" "$se"
  rwaitfile sim "world_$w" "$o/simulator/ready.json" "$T_READY" || { fetch_all; fail 5 "the world side of $w is not ready"; }
  # the S-CORE side after ready.json (the hero stands), with the camera calibration file of this session
  rstep score "score_start_$w" "$T_SCORE_START" env "DA_CAMERA_CALIBRATION_DIR=$CAMCAL_DIR" bash "$ENTRY_SCORE_START" \
    "$(od "score_$w")" "$CARLA_HOST"
  if [ "$HAS_GUEST" = 1 ] && [ "$rec" = 1 ]; then offer_checks "$w"; window_open "$w"; fi
  rtouch sim "$o/go" || { STEP_FAIL="world_$w"; fetch_all; fail 5 "no go file for $w"; }
  rwaitfile sim "world_$w" "$o/simulator/run_end.json" "$T_RUN" || { fetch_all; fail 5 "the run $w did not end"; }
  # the S-CORE side stops while the world still ticks (launch-manager/README.md), then the world is released
  rstep score "score_stop_$w" "$T_SCORE_START" bash "$ENTRY_SCORE_STOP" "$(od "score_$w")"
  rtouch sim "$o/release" || log "WARNING no release file for $w: the world side ends at its own hold limit"
  rwait sim "world_$w" "$T_RELEASE" || { fetch_all; fail 5 "the world side of $w did not end well"; }
  if [ "$rec" = 1 ]; then rwait sim "rec_$w" "$T_REC_END" || { fetch_all; fail 5 "the recorder of $w did not end well"; }; fi
  if [ "$HAS_GUEST" = 1 ] && [ "$rec" = 1 ]; then window_close "$w"; fi
}
make_h() {   # on this host: the capture from the simulator host, make-h, both files onto the S-CORE host
  local d=$IN/camcal src="da-kit/$SID/out/calibrate/camcal/simulator" vm f rc loc got
  vm=$(var sim VM); mkdir -p "$d/capture"; SEQ+=("lead:make_h")
  log "step make_h on this host: the camera capture from $vm, then camera_calibration.py make-h"
  run_fg scp_r sim 300 "$vm:$src/camera_capture.json" "$vm:$src/calibration_frame.png" "$d/capture/" 2>&1 | one >> "$LOG"
  [ -s "$d/capture/camera_capture.json" ] && [ -s "$d/capture/calibration_frame.png" ] \
    || { STEP_FAIL=make_h; fetch_all; fail 5 "make_h: the camera capture did not arrive"; }
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
    [ "$rc" = 0 ] && [ -s "$d/h/$f" ] || { STEP_FAIL=make_h; fetch_all; fail 5 "make_h: no $f (see camcal/make_h.log)"; }
  done
  loc=$(cd "$d/h" && sha256sum H.yaml homography_C_matrix.yaml)
  CAMCAL_SHA=$(echo "$loc" | awk '{printf "%s=%s ", $2, $1}')
  run_fg ssh_l score 60 "mkdir -p da-kit/$SID/camera_calibration" > /dev/null 2>&1
  local up=("$d/h/H.yaml" "$d/h/homography_C_matrix.yaml")
  [ -f "$d/h/camera_calibration_record.json" ] && up+=("$d/h/camera_calibration_record.json")
  run_fg scp_r score 120 "${up[@]}" "$(var score VM):da-kit/$SID/camera_calibration/" 2>&1 | one >> "$LOG"
  got=$(run_fg ssh_l score 60 "cd da-kit/$SID/camera_calibration && sha256sum H.yaml homography_C_matrix.yaml" 2>/dev/null)
  [ "$(echo "$got" | awk 'NF==2' | sort)" = "$(echo "$loc" | sort)" ] \
    || { STEP_FAIL=make_h; fetch_all; fail 4 "make_h: the files on $(var score VM) differ from this host's"; }
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
    rstep score score_start "$T_SCORE_START" bash "$ENTRY_SCORE_START" "$(od score)" none
    offer_checks inject
    window_open inject
    rstep score inject "$T_INJECT" bash "$ENTRY_SCORE_INJECT" "$(od inject)"
    window_close inject
    rstep score score_stop "$T_SCORE_START" bash "$ENTRY_SCORE_STOP" "$(od score)"
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
    rwait sim rec_warmup "$T_REC_END" || { fetch_all; fail 5 "the warm-up's recorder did not end well: no recorded run"; }
    # ASM-DRIVING-005 and the camera capture, without candidate or adapter; then the calibration file, which the
    # S-CORE side copies into the candidate's working directory before its identity record
    rstep sim calibrate "$T_CALIBRATE" "$SENV" bash "$ENTRY_SIM_CALIBRATE" "$(od calibrate)"
    make_h
    [ "$P10_2_CALIB_STEER" = 1 ] && world_run calib_steer ASM-DRIVING-006 "$P10_2_SETTING" 0
    for n in $(seq 1 "$P10_2_RUNS"); do world_run "run$n" "$P10_2_SCENARIO" "$P10_2_SETTING" 1; done
    ;;
esac
log "SEQUENCE ${SEQ[*]}"
fetch_all || fail 5 "evidence fetch incomplete"
log "session steps done; the files are in $IN"
FINAL_RC=0
exit 0
