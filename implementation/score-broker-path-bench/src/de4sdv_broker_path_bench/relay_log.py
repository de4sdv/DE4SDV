"""The IVI frame relay's event lines in a logcat capture.

The bench saves logcat with ``adb logcat -v epoch -v usec``. A relay line is
one JSON object per event, written with the relay's liblog tag (the run
settings name that tag; its real value is the relay lane's init-service name,
given in the README). Each line carries the process id, so a relay restart (a
new process, phases numbered from 1 again) is told apart by keying every phase
by (pid, phase).

The evaluators read the relay's phase records as the start and end of each
subscription phase. For VC-MW-020 the judged start is the later of the phase
start and the loopback accept in the guest capture (#448); VC-MW-015 takes the
phase windows from this log alone (a known limit). They also read the
clock_step and data_loss events. A phase end that the layer caused while the
ingress stayed connected is a delivery failure of the layer.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
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
    """The relay's JSON events, each with the logcat time and the pid added."""
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
            event["pid"] = line.pid
            events.append(event)
    return events


@dataclass(frozen=True)
class Phase:
    """One subscription phase of the relay (relaySubscriptionPhaseDiscardRule).

    Keyed by (pid, phase): the relay numbers phases from 1 in each process, so
    the pid tells a restart apart. ``layer_caused`` is true when the layer
    ended the phase while the ingress stayed connected (a delivery failure of
    the layer); the relay logs it on the phase_end event.
    """

    pid: int
    number: int
    start_realtime_ns: int
    start_cause: str
    end_realtime_ns: int | None
    end_cause: str | None
    layer_caused_end: bool | None
    client_connected_at_end: bool | None
    clock_steps_in_phase: int | None

    @property
    def key(self) -> tuple[int, int]:
        return (self.pid, self.number)


def phases(events: list[dict]) -> tuple[list[Phase], list[str]]:
    """The phases of the relay, keyed by (pid, phase), and the record problems."""
    problems: list[str] = []
    started: dict[tuple[int, int], dict] = {}
    result: list[Phase] = []
    for event in events:
        kind = event.get("event")
        if kind == "phase_start":
            number = event.get("phase")
            start = event.get("phase_start_realtime_ns")
            pid = event.get("pid")
            if not isinstance(number, int) or not isinstance(start, int) or not isinstance(pid, int):
                problems.append(f"phase_start without a phase number, start time or pid: {event}")
                continue
            if (pid, number) in started:
                problems.append(f"phase (pid {pid}, {number}) started twice")
            started[(pid, number)] = event
        elif kind == "phase_end":
            number = event.get("phase")
            pid = event.get("pid")
            begin = started.pop((pid, number), None) if isinstance(number, int) and isinstance(pid, int) else None
            if begin is None:
                problems.append(f"phase_end without its phase_start: {event}")
                continue
            if event.get("phase_start_realtime_ns") not in (None, begin["phase_start_realtime_ns"]):
                problems.append(f"phase (pid {pid}, {number}) ends with another start time than it began with")
            end = event.get("realtime_ns")
            result.append(Phase(pid, number, begin["phase_start_realtime_ns"], str(begin.get("cause", "")),
                                end if isinstance(end, int) else None, str(event.get("cause", "")),
                                event.get("layer_caused"), event.get("client_connected"),
                                event.get("clock_steps_in_phase")))
    for (pid, number), begin in started.items():
        result.append(Phase(pid, number, begin["phase_start_realtime_ns"], str(begin.get("cause", "")),
                            None, None, None, None, None))
    result.sort(key=lambda phase: phase.start_realtime_ns)
    return result, problems


def first_phase_key(events: list[dict]) -> tuple[int, int] | None:
    """The (pid, phase) of the first phase_start in log order, or None when there is none.

    Log order, not the earliest realtime: a clock step can move realtime back
    past a later phase start (review R46).
    """
    for event in events:
        if event.get("event") == "phase_start" and isinstance(event.get("pid"), int) \
                and isinstance(event.get("phase"), int):
            return (event["pid"], event["phase"])
    return None


def clock_steps(events: list[dict]) -> list[dict]:
    return [event for event in events if event.get("event") == "clock_step"]


def data_loss_events(events: list[dict]) -> list[dict]:
    return [event for event in events if event.get("event") == "data_loss"]


def phase_at(all_phases: list[Phase], realtime_ns: int) -> Phase | None:
    """The phase that holds at ``realtime_ns`` (IVI VM clock), if any."""
    for phase in all_phases:
        if phase.start_realtime_ns <= realtime_ns and (phase.end_realtime_ns is None
                                                       or realtime_ns < phase.end_realtime_ns):
            return phase
    return None


def clock_step_in(events: list[dict], start_ns: int, end_ns: int | None) -> bool:
    """Whether a clock_step fell inside a phase window (voids the run, ASM-MW-030)."""
    for step in clock_steps(events):
        when = step.get("realtime_ns")
        if isinstance(when, int) and when >= start_ns and (end_ns is None or when <= end_ns):
            return True
        if step.get("in_phase") is True and end_ns is None:
            return True
    return False


def new_phase_starts(before: list[dict], after: list[dict]) -> list[dict]:
    """The phase_start events of ``after`` whose (pid, phase) key ``before`` does not hold.

    set_ivi_clock.sh setup restarts the ingress after the clock setting; a new
    phase_start must follow (#448 condition 2, review R37). The relay's own
    (pid, phase) keys decide what is new, so no clock reading is needed.
    """
    seen = {(event.get("pid"), event.get("phase")) for event in before if event.get("event") == "phase_start"}
    return [event for event in after if event.get("event") == "phase_start"
            and (event.get("pid"), event.get("phase")) not in seen]


def main(argv: list[str] | None = None) -> int:
    """``new-phase-start --tag T --before F --after F``: print the new phase_start events; exit 1 when none."""
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(prog="python3 -m de4sdv_broker_path_bench.relay_log")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("new-phase-start", help="the phase_start events that appeared between two logcat dumps")
    p.add_argument("--tag", required=True)
    p.add_argument("--before", required=True)
    p.add_argument("--after", required=True)
    arguments = parser.parse_args(argv)

    def events(path: str) -> list[dict]:
        file = Path(path)
        return relay_events(file.read_text(errors="replace").splitlines(), arguments.tag) if file.exists() else []

    new = new_phase_starts(events(arguments.before), events(arguments.after))
    for event in new:
        print(json.dumps(event, separators=(",", ":")))
    return 0 if new else 1


if __name__ == "__main__":
    raise SystemExit(main())
