"""ROS-independent nominal AEBS coordination decisions."""

from __future__ import annotations

import math


EGO_FRONT_OFFSET_M = 3.74


def classify_override_source(
    value: bool | None,
    source_nanoseconds: int | None,
    diagnostic_nanoseconds: int,
    max_age_s: float,
) -> str:
    """Classify one typed override source against the authorizing diagnostic stamp."""

    if value is not None and type(value) is not bool:
        raise TypeError("override value must be boolean or None")
    if source_nanoseconds is not None and (
        isinstance(source_nanoseconds, bool) or not isinstance(source_nanoseconds, int)
    ):
        raise TypeError("source_nanoseconds must be an integer or None")
    if isinstance(diagnostic_nanoseconds, bool) or not isinstance(diagnostic_nanoseconds, int):
        raise TypeError("diagnostic_nanoseconds must be an integer")
    maximum = float(max_age_s)
    if not math.isfinite(maximum) or maximum <= 0.0:
        raise ValueError("max_age_s must be finite and positive")
    if value is None or source_nanoseconds is None:
        return "inconclusive_missing_source"
    if source_nanoseconds <= 0 or diagnostic_nanoseconds <= 0:
        return "error_malformed_source"
    age_ns = diagnostic_nanoseconds - source_nanoseconds
    if age_ns < 0:
        return "error_future_source"
    if age_ns > round(maximum * 1_000_000_000):
        return "degraded_stale_source"
    return "conscious_override" if value else "control_clear"


class InterventionLatch:
    """Latch native intervention until fresh standstill, independent of diagnostic retention."""

    def __init__(self, stop_speed_mps: float, stop_hold_s: float, odometry_max_age_s: float) -> None:
        values = (float(stop_speed_mps), float(stop_hold_s), float(odometry_max_age_s))
        if any(not math.isfinite(value) or value <= 0.0 for value in values):
            raise ValueError("release thresholds must be finite and positive")
        self.stop_speed_mps, self.stop_hold_s, self.odometry_max_age_s = values
        self.active = False
        self.armed = True
        self.state = "armed"
        self._stopped_since_s: float | None = None
        self._last_stop_sample_s: float | None = None

    def observe_diagnostic(self, intervention: bool, override_fresh_and_clear: bool) -> None:
        if self.state == "released_verified_stop":
            return
        if intervention and self.armed and override_fresh_and_clear:
            self.active = True
            self.armed = False
            self.state = "braking_latched"
            self._stopped_since_s = None

    def observe_motion(self, speed_mps: float, sample_age_s: float, now_s: float) -> None:
        speed, age, now = float(speed_mps), float(sample_age_s), float(now_s)
        if any(not math.isfinite(value) for value in (speed, age, now)) or age < 0.0:
            raise ValueError("motion evidence must be finite and sample age non-negative")
        if not self.active:
            return
        if age > self.odometry_max_age_s or abs(speed) > self.stop_speed_mps:
            self._stopped_since_s = None
            self._last_stop_sample_s = None
            return
        if self._last_stop_sample_s is not None and now - self._last_stop_sample_s > self.odometry_max_age_s:
            self._stopped_since_s = now
        if self._stopped_since_s is None:
            self._stopped_since_s = now
        self._last_stop_sample_s = now
        if now - self._stopped_since_s >= self.stop_hold_s:
            self.active = False
            self.state = "released_verified_stop"


def bumper_gap_m(point_distance_m: float, ego_front_offset_m: float = EGO_FRONT_OFFSET_M) -> float:
    """Convert a base-link point distance to non-negative front-bumper separation."""

    distance = float(point_distance_m)
    offset = float(ego_front_offset_m)
    if not math.isfinite(distance) or not math.isfinite(offset) or distance < 0.0 or offset < 0.0:
        raise ValueError("distances must be finite and non-negative")
    return max(0.0, distance - offset)


def warning_requested(
    point_distance_m: float,
    rss_distance_m: float,
    warning_margin_m: float,
    *,
    ego_front_offset_m: float = EGO_FRONT_OFFSET_M,
) -> bool:
    """Apply coordinator warning margin in the same bumper-gap frame as native RSS."""

    rss = float(rss_distance_m)
    margin = float(warning_margin_m)
    if not math.isfinite(rss) or not math.isfinite(margin) or rss < 0.0 or margin < 0.0:
        raise ValueError("RSS distance and warning margin must be finite and non-negative")
    return bumper_gap_m(point_distance_m, ego_front_offset_m) <= rss + margin


def next_warning_state(
    current: bool,
    latch_state: str,
    point_distance_m: float,
    rss_distance_m: float,
    warning_margin_m: float,
) -> bool:
    """Latch a risk warning independently of any driver-override disposition."""

    if type(current) is not bool:
        raise TypeError("current warning state must be boolean")
    if latch_state not in {"armed", "braking_latched", "released_verified_stop"}:
        raise ValueError("unknown intervention latch state")
    return current or (
        latch_state == "armed"
        and warning_requested(point_distance_m, rss_distance_m, warning_margin_m)
    )
