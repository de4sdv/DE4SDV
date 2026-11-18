# DE4SDV driver-assistance bench (INC-DRIVING-002): helpers of the S-CORE host's entry scripts
# (start_score_side.sh, stop_score_side.sh, ../../score-build/scripts/p10_1_check.sh and
# ../../ivi-warning/scripts/inject_warning_requests.sh). Sourced, never run.
#
# Settings, all overridable from the environment:
#   DA_STAGE        the staged tree the Launch Manager configuration names (default /tmp/de4sdv-da-bench)
#   DA_B2_BUNDLE    the S-CORE build's bundle (default /opt/da-b2/bundle, score-build/README.md)
#   DA_SUDO         how to become root (default "sudo -n"; empty when the caller is root, and in the dry-run tests)
#   DA_PYTHON       python3 for the staging helper
# shellcheck shell=bash

export LC_ALL=C   # numbers with a decimal point, whatever the host's locale
: "${DA_STAGE:=/tmp/de4sdv-da-bench}"
: "${DA_B2_BUNDLE:=/opt/da-b2/bundle}"
: "${DA_PYTHON:=python3}"
if [ -z "${DA_SUDO+x}" ]; then
  if [ "$(id -u)" = 0 ]; then DA_SUDO=""; else DA_SUDO="sudo -n"; fi
fi
SCORE_SIDE_STATE=$DA_STAGE/state/score_side.env
COMPONENTS_FULL="identity_recorder someipd gatewayd vision_pilot actuation_adapter"
COMPONENTS_PATH="identity_recorder someipd gatewayd"

ss_log() { echo "[$(date -u +%FT%T.%3NZ)] $*"; }

# A process runs (whoever owns it): ps sees it, and it is no zombie.
ss_alive() { [ -n "${1:-}" ] && ps -o stat= -p "$1" 2>/dev/null | grep -qv '^Z'; }

# The pids of a staged binary's processes: the first word of the command line is $DA_STAGE/bin/<name> (or the
# second, after an interpreter, for the stub components of the dry-run tests).
ss_pids_of() {
  local name=$1
  ps -eo pid=,stat=,args= 2>/dev/null | awk -v want="$DA_STAGE/bin/$name" '
    $2 !~ /^Z/ { if ($3 == want || ($3 ~ /(^|\/)(ba)?sh$|(^|\/)python3?$/ && $4 == want)) print $1 }'
}

# The process's start in seconds since boot (field 22 of /proc/<pid>/stat, in clock ticks).
ss_start_s() {
  local pid=$1 ticks hz
  hz=$(getconf CLK_TCK)
  ticks=$(awk '{ sub(/^.*\) /, ""); print $20 }' "/proc/$pid/stat" 2>/dev/null) || return 1
  [ -n "$ticks" ] || return 1
  awk -v t="$ticks" -v h="$hz" 'BEGIN { printf "%.3f\n", t / h }'
}

# A value of the state file.
ss_state() { sed -n "s/^$1=//p" "$SCORE_SIDE_STATE" 2>/dev/null | tail -1; }

# The host's two clocks and its synchronization, for the 0.1 s path share (brief R9).
ss_clock_record() {
  echo "real_ns $(date +%s%N)"
  echo "boot_s $(cut -d' ' -f1 /proc/uptime)"
  echo "mono_s $(awk '{print $1}' /proc/uptime)"
  if command -v chronyc > /dev/null 2>&1; then chronyc tracking 2>&1 | sed 's/^/chrony /'; fi
  if command -v timedatectl > /dev/null 2>&1; then timedatectl show 2>&1 | sed 's/^/timedatectl /'; fi
}

# The newest record of an event in a run log (run_log.h format: one JSON object per line).
ss_last_event() {
  local file=$1 event=$2
  [ -r "$file" ] || return 1
  grep -F "\"event\":\"$event\"" "$file" 2>/dev/null | tail -1
}
