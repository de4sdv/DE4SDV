"""The IVI frame relay's event lines in a logcat capture.

The bench saves logcat with ``adb logcat -v epoch -v usec``. A relay line is
one JSON object per event, written with the relay's liblog tag; the run
settings name that tag. The evaluators read the relay's phase records as
supporting data and check them against the independent captures.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Iterable, Iterator

_EPOCH_LINE = re.compile(
    r"^\s*(?P<sec>\d+)\.(?P<frac>\d+)\s+(?:(?P<uid>[A-Za-z_][\w.]*|\d+)\s+)?(?P<pid>\d+)\s+(?P<tid>\d+)\s+"
    r"(?P<level>[VDIWEFS])\s+(?P<tag>.+?)\s*:\s?(?P<msg>.*)$"
)


@dataclass(frozen=True)
class LogcatLine:
    ts_ns: int
    pid: int
    tid: int
    level: str
    tag: str
    message: str


def parse_logcat(lines: Iterable[str]) -> Iterator[LogcatLine]:
    for raw in lines:
        match = _EPOCH_LINE.match(raw.rstrip("\n"))
        if match is None:
            continue
        frac = match["frac"]
        ts_ns = int(match["sec"]) * 1_000_000_000 + int(frac.ljust(9, "0")[:9])
        yield LogcatLine(ts_ns, int(match["pid"]), int(match["tid"]), match["level"], match["tag"].strip(),
                         match["msg"])


def relay_events(lines: Iterable[str], tag: str) -> list[dict]:
    """The relay's JSON events, each with the logcat time added as ``logcat_ns``."""
    events = []
    for line in parse_logcat(lines):
        if line.tag != tag or not line.message.startswith("{"):
            continue
        try:
            event = json.loads(line.message)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and isinstance(event.get("event"), str):
            event["logcat_ns"] = line.ts_ns
            events.append(event)
    return events


@dataclass(frozen=True)
class Phase:
    """One subscription phase of the relay (relaySubscriptionPhaseDiscardRule)."""

    number: int
    start_realtime_ns: int
    start_cause: str
    end_realtime_ns: int | None
    end_cause: str | None
    clock_steps_in_phase: int | None


def phases(events: list[dict]) -> tuple[list[Phase], list[str]]:
    """The phases of the relay, and the inconsistencies of its records."""
    problems: list[str] = []
    started: dict[int, dict] = {}
    result: list[Phase] = []
    for event in events:
        kind = event.get("event")
        if kind == "phase_start":
            number = event.get("phase")
            start = event.get("phase_start_realtime_ns")
            if not isinstance(number, int) or not isinstance(start, int):
                problems.append(f"phase_start without phase number or start time: {event}")
                continue
            if number in started:
                problems.append(f"phase {number} started twice")
            started[number] = event
        elif kind == "phase_end":
            number = event.get("phase")
            begin = started.pop(number, None) if isinstance(number, int) else None
            if begin is None:
                problems.append(f"phase_end without its phase_start: {event}")
                continue
            if event.get("phase_start_realtime_ns") not in (None, begin["phase_start_realtime_ns"]):
                problems.append(f"phase {number} ends with another start time than it began with")
            end = event.get("realtime_ns")
            result.append(Phase(number, begin["phase_start_realtime_ns"], str(begin.get("cause", "")),
                                end if isinstance(end, int) else None, str(event.get("cause", "")),
                                event.get("clock_steps_in_phase")))
    for number, begin in started.items():
        result.append(Phase(number, begin["phase_start_realtime_ns"], str(begin.get("cause", "")), None, None, None))
    result.sort(key=lambda phase: phase.start_realtime_ns)
    return result, problems


def clock_steps(events: list[dict]) -> list[dict]:
    return [event for event in events if event.get("event") == "clock_step"]


def phase_at(all_phases: list[Phase], realtime_ns: int) -> Phase | None:
    """The phase that holds at ``realtime_ns`` (IVI VM clock), if any."""
    for phase in all_phases:
        if phase.start_realtime_ns <= realtime_ns and (phase.end_realtime_ns is None
                                                       or realtime_ns < phase.end_realtime_ns):
            return phase
    return None
