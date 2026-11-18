#!/usr/bin/env bash
# The detached launcher of B12 on the guest host (de4sdv-aaos-build), in the operator's proven
# pattern of 2026-11-18 (guest-prep-20261118/upload/scripts/launch.sh: setsid nohup, no systemd
# unit; launch_two_vms.sh up ran twice that way). A dropped SSH connection cannot end the run.
#
#   b12_launch.sh start <dir>/da-b12-<sha>.tar.gz
#       sha256sum -c <tar>.sha256; the commit id inside the tar must start with <sha>; extract into
#       a fresh ~/da-b12-<sha> (~/da-b12-<sha>-r<B12_RERUN> for a rerun; an existing directory is
#       refused); the extracted copy of this launcher must equal the one running; then start
#       `build_guests_incremental.sh all` detached and return at once.
#   b12_launch.sh status     the run's pid, whether it lives, its result line and the last lines
#   b12_launch.sh abort      SIGTERM to the run (only the pid this launcher started); the script
#                            stops the guests on its way out
#
# On any failure once this run began to boot the guests, the detached run stops them (again: `all`
# already did, unless KEEP_GUESTS_ON_FAILURE=1); guests this run never booted are left alone. It packs its logs and identity into <run dir>/b12-records.tgz with a
# .sha256 beside it, to be copied back. Its last line is
#   B12 RESULT: PASSED|FAILED rc=<n>; guests: stopped|not booted by this run|NOT STOPPED ...;
#               crosvm left: <n>; selinux: ...; IVI_PERMISSIVE=<0|1>; records: <tgz> sha256 <digest>
# Stop the host only after a result line with "crosvm left: 0".
#
# Environment passed through to the run: GUESTS (default fresh), IVI_PERMISSIVE (default 0: the IVI
# stays Enforcing), KEEP_GUESTS_ON_FAILURE (default 0), B12_RERUN (a rerun number, default none).
# It never starts or stops a VM, never calls gcloud and never deletes anything.
set -euo pipefail

: "${AB:=$HOME/aaos-build}"
: "${B12_STATE:=$HOME/b12-launch}"   # what this launcher started: last-run, the pid
SELF="$(readlink -f -- "${BASH_SOURCE[0]}")"
REL_SCRIPT=implementation/driver-assistance-bench/guest-build/build_guests_incremental.sh
REL_SELF=implementation/driver-assistance-bench/guest-build/b12_launch.sh

ts() { date -u +%FT%T.%3NZ; }
log() { printf '%s [b12-launch] %s\n' "$(ts)" "$*"; }
die() { log "ERROR: $*"; exit 1; }

start() { # <tar.gz>
  local tar sha dest run_dir commit
  tar="$(readlink -f -- "${1:?usage: b12_launch.sh start <dir>/da-b12-<sha>.tar.gz}")"
  [ -f "$tar" ] || die "no tar at $1"
  case "$(basename "$tar")" in
    da-b12-*.tar.gz) sha="$(basename "$tar" .tar.gz)"; sha="${sha#da-b12-}" ;;
    *) die "the tar must be named da-b12-<sha>.tar.gz" ;;
  esac
  printf '%s' "$sha" | grep -qE '^[0-9a-f]{8,40}$' || die "'$sha' is not a commit id"
  [ -f "$tar.sha256" ] || die "no $tar.sha256 beside the tar"
  ( cd "$(dirname "$tar")" && sha256sum --strict -c "$(basename "$tar").sha256" ) || die "the tar's sha256 does not match $tar.sha256"
  if command -v git >/dev/null 2>&1; then
    commit="$(gzip -dc "$tar" | git get-tar-commit-id 2>/dev/null || true)"
    [ -n "$commit" ] || die "the tar carries no commit id (make it with git archive from the commit)"
    case "$commit" in "$sha"*) log "the tar is commit $commit" ;; *) die "the tar is commit $commit, not $sha" ;; esac
  fi
  dest="$HOME/da-b12-$sha${B12_RERUN:+-r$B12_RERUN}"
  [ ! -e "$dest" ] || die "$dest exists: extract into a fresh directory (set B12_RERUN=<n> for a rerun)"
  mkdir "$dest"
  tar -xzf "$tar" -C "$dest" || die "the extraction into $dest failed"
  [ -x "$dest/$REL_SCRIPT" ] || die "no $REL_SCRIPT in the tar"
  cmp -s "$SELF" "$dest/$REL_SELF" || die "this launcher differs from the one in the tar ($dest/$REL_SELF)"
  log "extracted into $dest"

  run_dir="$AB/b12-$(date -u +%Y%m%d)-$sha${B12_RERUN:+-r$B12_RERUN}"
  [ ! -e "$run_dir" ] || die "$run_dir exists: set B12_RERUN=<n> for a rerun"
  mkdir -p "$run_dir" "$B12_STATE"
  local next=$(( ${B12_RERUN:-1} + 1 ))
  local rerun
  rerun="IVI_PERMISSIVE=1 B12_RERUN=$next bash $(printf '%q' "$SELF") start $(printf '%q' "$tar")"
  # Detached: own session (setsid), HUP ignored (nohup), no terminal, every descriptor redirected.
  env B12_DIR="$run_dir" GUESTS="${GUESTS:-fresh}" IVI_PERMISSIVE="${IVI_PERMISSIVE:-0}" \
    KEEP_GUESTS_ON_FAILURE="${KEEP_GUESTS_ON_FAILURE:-0}" B12_RERUN_CMD="$rerun" \
    setsid nohup bash "$dest/$REL_SELF" _run "$dest" "$run_dir" < /dev/null > "$run_dir/b12-all.out" 2>&1 &
  local pid=$!
  printf '%s\n' "$pid" > "$run_dir/b12-run.pid"
  printf 'run_dir=%s\npid=%s\ndest=%s\ntar=%s\n' "$run_dir" "$pid" "$dest" "$tar" > "$B12_STATE/last-run"
  log "launched pid $pid (IVI_PERMISSIVE=${IVI_PERMISSIVE:-0}, GUESTS=${GUESTS:-fresh}); output $run_dir/b12-all.out"
  log "poll with: bash $(printf '%q' "$SELF") status"
}

# The detached body: the run, the stop on failure, the records, the result line.
_run() { # <dest> <run dir>
  local dest="$1" run_dir="$2" script="$1/$REL_SCRIPT" child rc=0 stopped=stopped
  trap '[ -n "${child:-}" ] && kill -TERM "$child" 2>/dev/null || true' TERM
  log "B12 run from $dest, records in $run_dir, IVI_PERMISSIVE=${IVI_PERMISSIVE:-0}"
  bash "$script" all & child=$!
  wait "$child" || rc=$?
  while kill -0 "$child" 2>/dev/null; do rc=0; wait "$child" || rc=$?; done
  child=
  if [ "$rc" != 0 ] && [ ! -f "$run_dir/work/guests-booted-by-this-run" ]; then
    stopped="not booted by this run"
  elif [ "$rc" != 0 ]; then
    if [ "${KEEP_GUESTS_ON_FAILURE:-0}" = 1 ]; then
      stopped="NOT STOPPED (KEEP_GUESTS_ON_FAILURE=1): run 'bash $script stop' before the host stop"
    else
      log "the run failed (rc $rc): stopping the guests"
      bash "$script" stop || stopped="NOT STOPPED: the guest stop failed; do not stop the host"
    fi
  fi
  local summary="$run_dir/identity/b12-summary.txt" selinux records="$run_dir/b12-records.tgz" records_sha=none
  selinux="$(grep -o 'SELinux core [A-Za-z]*, IVI [A-Za-z]*' "$summary" 2>/dev/null | tail -1 || true)"
  if tar -czf "$records" -C "$run_dir" --exclude=b12-records.tgz logs identity b12-all.out 2>/dev/null \
      || tar -czf "$records" -C "$run_dir" --exclude=b12-records.tgz . ; then
    ( cd "$run_dir" && sha256sum b12-records.tgz > b12-records.tgz.sha256 )
    records_sha="$(cut -d' ' -f1 "$run_dir/b12-records.tgz.sha256")"
  fi
  local verdict=FAILED crosvm; [ "$rc" = 0 ] && verdict=PASSED
  crosvm="$(pgrep -c -x crosvm 2>/dev/null || true)"
  log "B12 RESULT: $verdict rc=$rc; guests: $stopped; crosvm left: ${crosvm:-0}; selinux: ${selinux:-not read}; IVI_PERMISSIVE=${IVI_PERMISSIVE:-0}; records: $records sha256 $records_sha"
  return "$rc"
}

status() {
  [ -f "$B12_STATE/last-run" ] || die "no run started by this launcher ($B12_STATE/last-run)"
  local run_dir pid
  run_dir="$(sed -n 's/^run_dir=//p' "$B12_STATE/last-run")"; pid="$(sed -n 's/^pid=//p' "$B12_STATE/last-run")"
  if kill -0 "$pid" 2>/dev/null; then log "pid $pid running ($run_dir)"; else log "pid $pid ended ($run_dir)"; fi
  grep -E 'B12 RESULT:' "$run_dir/b12-all.out" 2>/dev/null | tail -1 || true
  tail -n 8 "$run_dir/b12-all.out" 2>/dev/null || true
}

abort() {
  [ -f "$B12_STATE/last-run" ] || die "no run started by this launcher"
  local pid; pid="$(sed -n 's/^pid=//p' "$B12_STATE/last-run")"
  kill -0 "$pid" 2>/dev/null || die "pid $pid is not running"
  kill -TERM "$pid"
  log "SIGTERM sent to pid $pid; the run stops the guests and writes its result line (poll with status)"
}

case "${1:-}" in
  start) shift; start "$@" ;;
  _run) shift; _run "$@" ;;
  status) status ;;
  abort) abort ;;
  *) echo "usage: $0 {start <dir>/da-b12-<sha>.tar.gz|status|abort}" >&2; exit 2 ;;
esac
