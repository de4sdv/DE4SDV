#!/bin/sh
# Apply a signed package, gate on the zone actually working, roll back if it does not.
#
# Why this exists: the orchestrator reports `up` when the containers start, not when the
# vehicle works. A package whose zone dies on a missing file converges "successfully" and
# leaves a vehicle that looks up and publishes nothing. That is precisely the failure an
# update has to survive, so the gate lives here, next to the update.
#
# Exit codes: 0 accepted, 2 rolled back, 3 unhealthy even after rollback.
#
# Usage:
#   update_with_rollback.sh <candidate-pkg-dir> <fallback-pkg-dir> [zone] [signal-id]

set -eu

CANDIDATE=${1:?candidate package directory}
FALLBACK=${2:?fallback package directory}
ZONE=${3:-vx-zone-rl-payload}
SIGNAL=${4:-281}
TIMEOUT=${HEALTH_TIMEOUT:-15}

: "${VXEDGE_ENDPOINT:=unix:///run/user/$(id -u)/vxedge.sock}"
export VXEDGE_ENDPOINT

apply() {
    # Exactly one run exists per host, and `down` refuses a workspace that is not the
    # active one — so tear down both sides before bringing either up.
    for pkg in "$CANDIDATE" "$FALLBACK"; do
        vxedge experiment down --chdir "$pkg" >/dev/null 2>&1 || true
    done
    vxedge experiment up --chdir "$1" >/dev/null 2>&1 || return 1
}

# The zone must publish its OWN status frame. A container that is up but silent is the
# failure mode this gate exists for, and a frame bridged in from another zone is not
# evidence — hence the id filter, not "any frame on the bus".
health() {
    waited=0
    while [ "$waited" -lt "$TIMEOUT" ]; do
        if podman exec "$ZONE" sh -c "timeout 2 candump -n 1 vcan0,${SIGNAL}:7FF" 2>/dev/null \
            | grep -q "${SIGNAL}"; then
            return 0
        fi
        waited=$((waited + 2))
    done
    return 1
}

echo "[update] candidate: $CANDIDATE"
apply "$CANDIDATE" || echo "[update] converge reported a failure"

if health; then
    echo "[update] health gate passed on the candidate: update accepted"
    exit 0
fi

echo "[update] health gate FAILED: no ${SIGNAL} from ${ZONE} within ${TIMEOUT}s"
echo "[update] rolling back to $FALLBACK"
apply "$FALLBACK" || echo "[update] rollback converge reported a failure"

if health; then
    echo "[update] rolled back: ${ZONE} is publishing again"
    exit 2
fi

echo "[update] still unhealthy after rollback" >&2
exit 3
