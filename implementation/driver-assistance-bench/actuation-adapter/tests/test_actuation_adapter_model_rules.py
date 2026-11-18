"""The core's constants are the ones MAP-DRIVING-DA-COMMAND's transformationRule states.

The test reads the rule from the model file at test time (no copy of model text is kept) and the
constants from actuation_core.h, so a change of either side fails here. The model is the authority:
textual-notation-of-model/packages/features/driving/driver_assistance_physical_software_realization.sysml.
"""

from __future__ import annotations

import re
from pathlib import Path

ADAPTER = Path(__file__).resolve().parents[1]
ROOT = ADAPTER.parents[2]
PSR = (ROOT / "textual-notation-of-model" / "packages" / "features" / "driving"
       / "driver_assistance_physical_software_realization.sysml")
CORE_H = ADAPTER / "actuation_core.h"


def transformation_rule() -> str:
    text = PSR.read_text(encoding="utf-8")
    start = text.index("item <'MAP-DRIVING-DA-COMMAND'>")
    match = re.search(r'attribute :>> transformationRule = "([^"]*)";', text[start:])
    assert match, "MAP-DRIVING-DA-COMMAND has no transformationRule"
    return match.group(1)


def adapter_part_def() -> str:
    text = PSR.read_text(encoding="utf-8")
    start = text.index("part def DrivingCommandActuationAdapter")
    end = text.index("part def ", start + 10)
    return text[start:end]


def constant(name: str) -> float:
    match = re.search(rf"inline constexpr double {name} = ([0-9.]+);", CORE_H.read_text(encoding="utf-8"))
    assert match, name
    return float(match.group(1))


def test_delay_bound() -> None:
    rule = transformation_rule()
    match = re.search(r"issue time is older than the newest world time by more than ([0-9.]+) s of "
                      r"simulation time", rule)
    assert match, rule
    assert constant("kMaxCommandAgeMs") == float(match.group(1)) * 1000.0


def test_speed_rule() -> None:
    match = re.search(r"speed = max\(0, v \+ ([0-9.]+) \* acceleration\) with v the speed of the ego "
                      r"vehicle in the newest world snapshot", transformation_rule())
    assert match
    assert constant("kSpeedHorizonS") == float(match.group(1))


def test_jerk_and_steer_speed() -> None:
    rule = transformation_rule()
    jerk = re.search(r"acceleration unchanged and jerk = ([0-9]+(?:\.[0-9]+)?)", rule)
    steer_speed = re.search(r"steerSpeed stays at its default of ([0-9]+(?:\.[0-9]+)?)", rule)
    assert jerk and steer_speed
    assert constant("kJerk") == float(jerk.group(1))
    assert constant("kSteerSpeed") == float(steer_speed.group(1))


def test_steer_rule_and_sign() -> None:
    rule = transformation_rule()
    assert "steer = -steeringAngle * pi / 180 in rad" in rule
    assert "whose steer is positive to the right" in rule
    source = (ADAPTER / "actuation_core.cpp").read_text(encoding="utf-8")
    assert "control.steer = -static_cast<double>(command.steeringAngle) * kPi / 180.0;" in source


def test_rejection_rule_and_reasons() -> None:
    rule = " ".join(transformation_rule().split())
    # The rule as the adapter counting decision of 2026-11-18 amended it (actuation_core.h).
    assert ("The adapter checks the check value, then the sequence count, then the issue time, against the "
            "reference count, the highest sequence count among the commands received earlier in the run whose "
            "check value holds, 0 at the start of the run") in rule
    assert ("it rejects a command whose check value fails, whose sequence count is not one more than the "
            "reference count, or whose issue time is older than the newest world time by more than 0.1 s of "
            "simulation time, and applies nothing in its place") in rule
    assert ("the count of a command whose check value holds and whose count is greater than the reference "
            "count becomes the reference count, whether the command is accepted or not") in rule
    assert "last accepted" not in rule
    part = " ".join(re.sub(r"\s*\n\s*\*\s?", " ", adapter_part_def()).split())
    assert ("checks each command against a reference count: the highest sequence count among the commands "
            "received earlier in the run whose check value holds") in part
    assert "The reference count is 0 at the start of each run" in part
    assert "The adapter checks the check value first, then the sequence count, then the issue time." in part
    assert "rejected (a corruption) and leaves the reference count unchanged" in part
    assert "rejected (a repetition) and leaves the reference count unchanged" in part
    assert "rejected (a loss is detected), and its count becomes the reference count" in part
    assert "rejected (a delay); in both cases its count becomes the reference count" in part
    assert ("A command that arrives before the adapter has a world snapshot, or whose issue time is not a finite "
            "number, counts as older than the limit and is rejected as a delay.") in part
    assert "It has no stop response of its own." in part
    assert "The autopilot of the ego vehicle stays off." in part
