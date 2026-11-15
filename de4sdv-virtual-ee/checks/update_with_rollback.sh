#!/bin/sh
# Apply a signed package, gate on the zone actually working, roll back if it does not.
#
# Why this exists: the orchestrator reports `up` when the containers start, not when the
# vehicle works. A package whose zone dies on a missing file converges "successfully" and
# leaves a vehicle that looks up and publishes nothing. That is precisely the failure an
# update has to survive, so the gate lives here, next to the update.
#
# A package counts as applied only when `experiment up` succeeded AND the zone that then
# answers is the container that `up` created: a different id from the one before the
# apply, running, from the image digest the package deploys on that zone. A failed `up`
# is never accepted, whatever an older same-named container still publishes, and the
# same holds for the rollback. The identity and probe logic is in update_health.py.
#
# Exit codes: 0 accepted, 2 candidate refused and rolled back, 3 the rollback failed too.
#
# Usage:
#   update_with_rollback.sh <candidate-pkg-dir> <fallback-pkg-dir> [zone] [signal-id]
# Environment: HEALTH_TIMEOUT (s; default in update_health.py, longer than the zone's
#   60 s broker wait), UP_TIMEOUT (s, default 180), VXEDGE_ENDPOINT, UPDATE_PYTHON.

set -eu

CANDIDATE=${1:?candidate package directory}
FALLBACK=${2:?fallback package directory}
ZONE=${3:-vx-zone-rl-payload}
SIGNAL=${4:-281}
UP_TIMEOUT=${UP_TIMEOUT:-180}
HERE=$(cd "$(dirname "$0")" && pwd)

: "${VXEDGE_ENDPOINT:=unix:///run/user/$(id -u)/vxedge.sock}"
export VXEDGE_ENDPOINT

health_py() { "${UPDATE_PYTHON:-python3}" "$HERE/update_health.py" "$@"; }

# apply <pkg>: 0 only if `experiment up` succeeded AND the zone publishes its OWN status
# frame from the container this up created. A frame bridged in from another zone is not
# evidence (id filter), and neither is a container that existed before the apply.
apply() {
    previous=$(health_py container-id "$ZONE")
    # Exactly one run exists per host, and `down` refuses a workspace that is not the
    # active one — so tear down both sides before bringing either up.
    for pkg in "$CANDIDATE" "$FALLBACK"; do
        vxedge experiment down --chdir "$pkg" >/dev/null 2>&1 || true
    done
    if ! out=$(timeout "$UP_TIMEOUT" vxedge experiment up --chdir "$1" 2>&1); then
        echo "[update] experiment up FAILED for $1: $(printf '%s' "$out" | tail -n 3 | tr '\n' ' ')"
        return 1
    fi
    if receipt=$(health_py gate --package "$1" --container "$ZONE" --previous-id "$previous" \
            --signal "$SIGNAL" ${HEALTH_TIMEOUT:+--timeout "$HEALTH_TIMEOUT"}); then
        echo "[update] health: $receipt"
        return 0
    fi
    echo "[update] health gate FAILED: $receipt"
    return 1
}

echo "[update] candidate: $CANDIDATE"
if apply "$CANDIDATE"; then
    echo "[update] candidate deployed and healthy: update accepted"
    exit 0
fi

echo "[update] candidate refused; rolling back to $FALLBACK"
if apply "$FALLBACK"; then
    echo "[update] rolled back: ${ZONE} is publishing again from the fallback"
    exit 2
fi

echo "[update] ROLLBACK FAILED: the fallback did not deploy healthy" >&2
exit 3
