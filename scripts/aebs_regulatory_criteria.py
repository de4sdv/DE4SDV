"""Fail-closed evaluation of bounded AEBS regulatory measurements.

This module evaluates selected quantified criteria from one controlled source
baseline. It never produces a compliance, homologation, certification, or type-
approval conclusion.
"""

from __future__ import annotations

import math
from bisect import bisect_left
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).resolve().parents[1]
_CRITERIA_PATH = (
    _ROOT / "methodologies/sysmod-sysmlv2/pilots/aebs-regulatory-criteria.yaml"
)
_MEASUREMENT_KEYS = {
    "scenario_family",
    "vehicle_category",
    "load_condition",
    "subject_speed_kmh",
    "target_speed_kmh",
    "warning_time_s",
    "braking_start_time_s",
    "minimum_braking_demand_mps2",
    "impact_speed_kmh",
    "successful_repetitions",
    "failed_repetitions",
    "conditions",
}


def _criteria() -> dict[str, Any]:
    value = yaml.safe_load(_CRITERIA_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise TypeError("regulatory criteria must be a mapping")
    return dict(value)


def _finite_number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _nonnegative_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def maximum_impact_speed_kmh(
    scenario_family: str,
    vehicle_category: str,
    load_condition: str,
    subject_speed_kmh: float,
) -> float:
    """Return the next-higher-row threshold for one controlled source table."""

    speed = _finite_number("subject_speed_kmh", subject_speed_kmh)
    criteria = _criteria()
    try:
        table = criteria["families"][scenario_family]["impact_speed_tables_kmh"][
            vehicle_category
        ][load_condition]
    except (KeyError, TypeError) as error:
        raise ValueError("unknown family, vehicle category, or load condition") from error
    if not isinstance(table, Mapping):
        raise TypeError("impact-speed table must be a mapping")
    rows = sorted((_finite_number("table speed", key), value) for key, value in table.items())
    listed_speeds = [row[0] for row in rows]
    index = bisect_left(listed_speeds, speed)
    if index >= len(rows) or speed < listed_speeds[0]:
        raise ValueError("subject speed is outside the controlled criterion table")
    return _finite_number("maximum impact speed", rows[index][1])


def evaluate_regulatory_measurement(measurement: object) -> dict[str, object]:
    """Evaluate numeric thresholds separately from prescribed evidence fitness."""

    if not isinstance(measurement, Mapping):
        raise TypeError("measurement must be a mapping")
    actual_keys = set(measurement)
    if actual_keys != _MEASUREMENT_KEYS:
        raise ValueError(
            "measurement keys must match the closed contract; "
            f"missing={sorted(_MEASUREMENT_KEYS - actual_keys)}, "
            f"unknown={sorted(actual_keys - _MEASUREMENT_KEYS)}"
        )

    family = measurement["scenario_family"]
    category = measurement["vehicle_category"]
    load = measurement["load_condition"]
    if not all(isinstance(value, str) for value in (family, category, load)):
        raise TypeError("family, vehicle category, and load condition must be strings")

    criteria = _criteria()
    try:
        family_criteria = criteria["families"][family]
    except (KeyError, TypeError) as error:
        raise ValueError("unknown scenario family") from error
    target_range = family_criteria["target_speed_kmh"]
    target_speed = _finite_number("target_speed_kmh", measurement["target_speed_kmh"])
    warning_time = _finite_number("warning_time_s", measurement["warning_time_s"])
    braking_time = _finite_number(
        "braking_start_time_s", measurement["braking_start_time_s"]
    )
    braking_demand = _finite_number(
        "minimum_braking_demand_mps2",
        measurement["minimum_braking_demand_mps2"],
    )
    impact_speed = _finite_number("impact_speed_kmh", measurement["impact_speed_kmh"])
    if min(warning_time, braking_time, impact_speed) < 0.0:
        raise ValueError("times and impact speed must be non-negative")

    maximum_impact = maximum_impact_speed_kmh(
        family,
        category,
        load,
        measurement["subject_speed_kmh"],
    )
    common = criteria["common"]
    failed_thresholds: list[str] = []
    if not (
        _finite_number("target minimum", target_range["minimum"])
        <= target_speed
        <= _finite_number("target maximum", target_range["maximum"])
    ):
        failed_thresholds.append("target_speed_kmh")
    if warning_time > braking_time:
        failed_thresholds.append("warning_not_later_than_braking")
    if braking_demand > _finite_number(
        "minimum braking demand", common["minimum_braking_demand_mps2"]
    ):
        failed_thresholds.append("minimum_braking_demand_mps2")
    if impact_speed > maximum_impact:
        failed_thresholds.append("maximum_impact_speed_kmh")
    threshold_result = "fail" if failed_thresholds else "pass"

    conditions = measurement["conditions"]
    if not isinstance(conditions, Mapping):
        raise TypeError("conditions must be a mapping")
    required_conditions = tuple(criteria["required_conditions"])
    if set(conditions) != set(required_conditions):
        raise ValueError("conditions keys must match the controlled condition set")
    if not all(isinstance(conditions[name], bool) for name in required_conditions):
        raise TypeError("all condition values must be boolean")
    unestablished = [name for name in required_conditions if conditions[name] is not True]

    successful = _nonnegative_int(
        "successful_repetitions", measurement["successful_repetitions"]
    )
    failed = _nonnegative_int("failed_repetitions", measurement["failed_repetitions"])
    if successful < int(common["required_successful_repetitions"]):
        unestablished.append("successful_repetitions")
    if failed > int(common["permitted_failed_repetitions_for_selected_setup"]):
        unestablished.append("failed_repetitions")

    evidence_fitness = "inconclusive" if unestablished else "fit"
    criterion_result = threshold_result if evidence_fitness == "fit" else "inconclusive"
    return {
        "threshold_result": threshold_result,
        "evidence_fitness": evidence_fitness,
        "criterion_result": criterion_result,
        "failed_thresholds": failed_thresholds,
        "unestablished_conditions": unestablished,
        "maximum_impact_speed_kmh": maximum_impact,
        "source_id": criteria["source_id"],
        "source_original_sha256": criteria["source_original_sha256"],
        "compliance_conclusion": "withheld",
    }
