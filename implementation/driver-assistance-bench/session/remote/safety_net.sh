#!/bin/bash
# The power-off safety net of a session host, should the lead host lose the session (session/README.md).
#
#   safety_net.sh arm <minutes>                    the S-CORE and simulator hosts: a transient system timer that
#                                                  runs systemctl poweroff after <minutes> (not shutdown -h +N,
#                                                  whose last 5 minutes write /run/nologin and lock out a login)
#   safety_net.sh arm <minutes> <guest stop cmd>   the guest host: a transient system timer that runs
#                                                  `safety_net.sh fire <cmd>` after <minutes>
#   safety_net.sh fire <guest stop cmd>            the guests' stop first, then the power-off, and only when no
#                                                  crosvm is left; otherwise it leaves the host running and says so
# Both arm forms list their timer (systemctl list-timers) and print "safety-net-<minutes>" only when it is listed. The guest host is never powered off with guests running
# (lead answer B13.3 of 2026-11-18): a bare shutdown -h there could break the guests' disks.
# Runs as the bench user; uses sudo for the timer and the power-off. The fire's log is <kit>/safety_net.log.
set -uo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
KIT=$(cd -- "$HERE/../../.." && pwd)
ACTION=${1:?arm|fire}; shift
crosvm() { local n; n=$(pgrep -c -x crosvm 2>/dev/null); echo "${n:-0}"; }
case "$ACTION" in
  arm)
    MIN=${1:?minutes}; STOP=${2:-}
    UNIT="da-safety-net-$(basename "$KIT")"
    if [ -z "$STOP" ]; then
      sudo systemd-run --quiet --unit="$UNIT" --on-active="${MIN}min" /bin/systemctl poweroff > /dev/null 2>&1 || exit 1
    else
      sudo systemd-run --quiet --unit="$UNIT" --on-active="${MIN}min" --uid="$(id -u)" --gid="$(id -g)" \
        --setenv=HOME="$HOME" --setenv=PATH="$PATH" /bin/bash "$HERE/safety_net.sh" fire "$STOP" > /dev/null 2>&1 \
        || exit 1
    fi
    TIMER=$(systemctl list-timers --all --no-legend "$UNIT.timer" 2>/dev/null | grep -F "$UNIT.timer")
    [ -n "$TIMER" ] || { echo "no timer $UNIT.timer listed after the arm"; exit 1; }
    echo "timer: $TIMER"
    echo "safety-net-$MIN"
    ;;
  fire)
    STOP=${1:?guest stop command}
    exec >> "$KIT/safety_net.log" 2>&1
    echo "$(date -u +%FT%TZ) safety net fired: the guests' stop first: $STOP"
    bash -c "$STOP"; echo "$(date -u +%FT%TZ) stop rc=$?"
    N=$(crosvm)
    if [ "$N" != 0 ]; then
      echo "$(date -u +%FT%TZ) $N crosvm process(es) left: NOT powering off (guests running); stop them by hand"
      exit 1
    fi
    echo "$(date -u +%FT%TZ) no crosvm left: powering off"
    sudo shutdown -h now
    ;;
  *) echo "usage: safety_net.sh arm <minutes> [guest stop cmd] | fire <guest stop cmd>" >&2; exit 2 ;;
esac
