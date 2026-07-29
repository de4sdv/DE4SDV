"""Pure source-stamp profiles for the typed INC-AEBS-009D fixture."""

from __future__ import annotations

from .override_matrix import OverrideScenario

_STALE_OFFSET_NS = 300_000_000
_FUTURE_OFFSET_NS = 100_000_000


def override_publication(
    scenario: OverrideScenario, now_nanoseconds: int
) -> tuple[bool, int] | None:
    """Return the BoolStamped value/stamp pair, or no publication for missing."""

    if not isinstance(scenario, OverrideScenario):
        raise TypeError("scenario must be OverrideScenario")
    if isinstance(now_nanoseconds, bool) or not isinstance(now_nanoseconds, int):
        raise TypeError("now_nanoseconds must be an integer")
    if now_nanoseconds < _STALE_OFFSET_NS:
        raise ValueError("now_nanoseconds is too small for the stale profile")
    if scenario is OverrideScenario.MISSING:
        return None
    if scenario is OverrideScenario.MALFORMED:
        return True, 0
    if scenario is OverrideScenario.STALE:
        return True, now_nanoseconds - _STALE_OFFSET_NS
    if scenario is OverrideScenario.FUTURE_STAMPED:
        return True, now_nanoseconds + _FUTURE_OFFSET_NS
    return scenario is OverrideScenario.FRESH_TRUE_CONSCIOUS, now_nanoseconds
