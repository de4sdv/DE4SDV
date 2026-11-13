#!/usr/bin/env python3
"""The route provider of the closed-loop driving bench (ICD section 9).

It reads the scenario's route file once, at the start of the run, and publishes
a ``RouteAnnouncement`` to ``127.0.0.1:47110`` every 500 ms of **simulation
time**, so the input activity can judge the route's age (REQ-DRIVING-025).  The
route content does not change during a run; what the announcement carries is the
route's identity (file path, SHA-256), its corridor size, and the simulation
time of the newest world tick the provider has seen.

Datagram layout -- byte for byte ``de4sdv::driving::RouteAnnouncement`` in
``interfaces/include/de4sdv/driving/payloads.h``, little-endian, no padding::

    offset  size  field
    0       4     version          uint32   kInterfaceVersion = 2
    4       4     corridorPoints   uint32   route waypoints, 0 means "no corridor"
    8       8     issueTime        double   simulation seconds of the newest tick
    16      192   routeFile        char[192] absolute path, NUL-terminated
    208     64    routeSha256      char[64]  hex SHA-256 of that file
    total   272 bytes

``struct.pack("<IId192s64s")`` produces exactly this; ``tests/test_route_provider.py``
checks the offsets and sizes against the C++ ``payloads.h`` (through the layout
probe in ``tests/raster_cli.cpp``).

Simulation time is the frame index times 100 ms, exact (ICD section 1: never
the simulator's float timestamp).  Two clock sources:

* ``--carla-host`` -- a CARLA client on the S-CORE host subscribes to
  ``world.on_tick`` and stamps each announcement with ``frame * 0.1`` s.
  It does not tick the world: the world-side pacer owns the step.
* ``--fake-clock`` -- a local loop stepping 0.1 s at a time, for tests.

Fault knobs (fault injection of SC-DRIVING-003):

* ``--stale-after-s S``  -- stop announcing once S s of simulation time have
  passed since the first tick; the last announcement then ages out;
* ``--empty-after-s S``  -- announce ``corridorPoints = 0`` from S s on
  (the route file is untouched; the announcement says "no route corridor").

Logs: one JSONL file per run, ``<run_dir>/score/route_provider.jsonl``, in the
format of ICD section 6 (``run_log.h``).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import socket
import struct
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Iterable

INTERFACE_VERSION = 2  # ICD v2
STEP_SECONDS = 0.1
ANNOUNCE_PERIOD_S = 0.5
DEFAULT_UDP_HOST = "127.0.0.1"
DEFAULT_UDP_PORT = 47110
ROUTE_FILE_BYTES = 192
ROUTE_SHA_BYTES = 64

# "<" = little-endian, standard sizes, no padding -- the payloads.h layout.
ANNOUNCEMENT = struct.Struct("<IId192s64s")
ANNOUNCEMENT_BYTES = ANNOUNCEMENT.size  # 272

COMPONENT = "routeProvider"
HOST = "score"
DEFAULT_LOG_NAME = "route_provider.jsonl"


def _c_string(value: str, capacity: int) -> bytes:
    """Fixed-capacity C string: NUL-terminated, truncated on a byte boundary."""
    encoded = value.encode("utf-8")
    if len(encoded) >= capacity:
        encoded = encoded[: capacity - 1]
    return encoded + b"\x00" * (capacity - len(encoded))


def hex_string_64(value: str) -> bytes:
    """The 64-byte SHA-256 field: exactly 64 hex characters, no NUL."""
    encoded = value.encode("ascii")
    if len(encoded) != ROUTE_SHA_BYTES:
        raise ValueError(
            f"route SHA-256 must be {ROUTE_SHA_BYTES} hex characters, got "
            f"{len(encoded)}"
        )
    return encoded


def build_announcement(
    *,
    corridor_points: int,
    issue_time: float,
    route_file: str,
    route_sha256: str,
    version: int = INTERFACE_VERSION,
) -> bytes:
    """One RouteAnnouncement datagram."""
    if corridor_points < 0:
        raise ValueError("corridorPoints must not be negative")
    return ANNOUNCEMENT.pack(
        int(version),
        int(corridor_points),
        float(issue_time),
        _c_string(str(Path(route_file).resolve()) if route_file else "",
                  ROUTE_FILE_BYTES),
        hex_string_64(route_sha256),
    )


def parse_announcement(datagram: bytes) -> dict[str, Any]:
    """Inverse of build_announcement (used by the tests and the input side)."""
    if len(datagram) != ANNOUNCEMENT_BYTES:
        raise ValueError(f"expected {ANNOUNCEMENT_BYTES} bytes, got {len(datagram)}")
    version, corridor_points, issue_time, route_file, route_sha = ANNOUNCEMENT.unpack(
        datagram
    )
    return {
        "version": int(version),
        "corridorPoints": int(corridor_points),
        "issueTime": float(issue_time),
        "routeFile": route_file.split(b"\x00", 1)[0].decode("utf-8"),
        "routeSha256": route_sha.split(b"\x00", 1)[0].decode("ascii"),
    }


# ----------------------------------------------------------------------- logs


class RunLog:
    """ICD section 6 JSONL writer (same field order as run_log.h)."""

    def __init__(self, path: str | Path | None, *, host: str = HOST,
                 component: str = COMPONENT) -> None:
        self._host = host
        self._component = component
        self._sequence = 0
        # The CARLA clock delivers ticks from the client's thread.
        self._lock = threading.Lock()
        self._file = None
        if path is not None:
            target = Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            self._file = target.open("a", encoding="utf-8")

    @property
    def path(self) -> str | None:
        return None if self._file is None else str(self._file.name)

    def write(self, event: str, data: dict[str, Any] | None = None) -> int:
        with self._lock:
            self._sequence += 1
            record = {
                "t_mono_ns": time.monotonic_ns(),
                "t_real_ns": time.time_ns(),
                "host": self._host,
                "component": self._component,
                "event": event,
                "seq": self._sequence,
                "data": data or {},
            }
            if self._file is not None:
                self._file.write(json.dumps(record, separators=(",", ":")) + "\n")
                self._file.flush()
            return self._sequence

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None


# ------------------------------------------------------------------- provider


class RouteProvider:
    """Announces one route file every 500 ms of simulation time."""

    def __init__(
        self,
        route_file: str | Path,
        *,
        log: RunLog | None = None,
        sock: socket.socket | None = None,
        target: tuple[str, int] = (DEFAULT_UDP_HOST, DEFAULT_UDP_PORT),
        version: int = INTERFACE_VERSION,
        period_s: float = ANNOUNCE_PERIOD_S,
        stale_after_s: float | None = None,
        empty_after_s: float | None = None,
    ) -> None:
        self.route_file = Path(route_file).resolve()
        self._log = log or RunLog(None)
        self._socket = sock
        self._closes_socket = sock is None
        self.target = target
        self.version = int(version)
        self.period_s = float(period_s)
        if self.period_s <= 0.0:
            raise ValueError("the announcement period must be positive")
        self.stale_after_s = stale_after_s
        self.empty_after_s = empty_after_s
        self.corridor_points = self._read_route()
        self._start_time: float | None = None
        self._next_due: float | None = None
        self.announcements = 0
        self.ticks = 0
        self._stale_reported = False
        self._empty_reported = False
        self._stopped = False

    # ------------------------------------------------------------- route file
    def _read_route(self) -> int:
        data = self.route_file.read_bytes()
        payload = json.loads(data)
        if not isinstance(payload, dict) or "waypoints" not in payload:
            raise ValueError(f"{self.route_file}: not an ICD section 9 route file")
        waypoints = payload["waypoints"]
        if not isinstance(waypoints, list):
            raise ValueError(f"{self.route_file}: waypoints must be a list")
        self.route_sha256 = hashlib.sha256(data).hexdigest()
        self.map_name = str(payload.get("map", ""))
        return len(waypoints)

    # ------------------------------------------------------------------- API
    @property
    def log(self) -> RunLog:
        return self._log

    def open(self) -> None:
        if self._socket is None:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._log.write(
            "start",
            {
                "routeFile": str(self.route_file),
                "routeSha256": self.route_sha256,
                "map": self.map_name,
                "corridorPoints": self.corridor_points,
                "udpTarget": f"{self.target[0]}:{self.target[1]}",
                "periodSeconds": self.period_s,
                "bytes": ANNOUNCEMENT_BYTES,
            },
        )
        self.log.write(
            "config",
            {
                "interfaceVersion": self.version,
                "stepSeconds": STEP_SECONDS,
                "staleAfterSeconds": self.stale_after_s,
                "emptyAfterSeconds": self.empty_after_s,
                "clock": "simulation time = frame index * 0.1 s",
            },
        )

    def on_simulation_time(self, simulation_s: float) -> None:
        """One observation of the simulation clock (a world tick)."""
        if self._stopped:
            return
        self.ticks += 1
        now = float(simulation_s)
        if self._start_time is None:
            # Announce at once: the route exists from the first step, so the
            # input activity never has to wait for the first period.
            self._start_time = now
            self._next_due = now
        elapsed = now - self._start_time
        if self.stale_after_s is not None and elapsed >= self.stale_after_s:
            if not self._stale_reported:
                self._stale_reported = True
                self._log.write(
                    "fault.stale",
                    {
                        "sinceSimulation": now,
                        "elapsed": elapsed,
                        "announcements": self.announcements,
                    },
                )
            return
        empty = (
            self.empty_after_s is not None and elapsed >= self.empty_after_s
        )
        if empty and not self._empty_reported:
            self._empty_reported = True
            self._log.write(
                "fault.empty",
                {"sinceSimulation": now, "elapsed": elapsed},
            )
        while self._next_due is not None and now + 1e-9 >= self._next_due:
            # issueTime is the newest world tick, as payloads.h defines it.
            self._announce(now, empty)
            self._next_due += self.period_s

    def _announce(self, issue_time: float, empty: bool) -> None:
        corridor_points = 0 if empty else self.corridor_points
        datagram = build_announcement(
            corridor_points=corridor_points,
            issue_time=issue_time,
            route_file=str(self.route_file),
            route_sha256=self.route_sha256,
            version=self.version,
        )
        if self._socket is not None:
            try:
                self._socket.sendto(datagram, self.target)
            except OSError as error:
                self._log.write("error", {"send": str(error)})
                return
        self.announcements += 1
        # The evaluators' record (case-evaluators/OBSERVABLES.md row 025): event
        # out.route_announcement, issueTime marked as simulation time (ICD C9).
        self._log.write(
            "out.route_announcement",
            {
                "version": self.version,
                "corridorPoints": corridor_points,
                "issueTime": float(issue_time),
                "routeFile": str(self.route_file),
                "routeSha256": self.route_sha256,
                "bytes": len(datagram),
                "faultEmpty": empty,
                "clocks": {"issueTime": "simulation"},
            },
        )

    def close(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        self._log.write(
            "stop",
            {"announcements": self.announcements, "ticks": self.ticks},
        )
        self._log.close()
        if self._closes_socket and self._socket is not None:
            self._socket.close()
            self._socket = None


# ------------------------------------------------------------------ clock loops


def run_fake_clock(
    provider: RouteProvider,
    *,
    frames: int,
    step_s: float = STEP_SECONDS,
    start_frame: int = 0,
    sleep_s: float = 0.0,
    on_step: Callable[[int, float], None] | None = None,
) -> int:
    """Step a synthetic simulation clock; returns the last frame index."""
    frame = int(start_frame)
    for _ in range(int(frames)):
        simulation_s = frame * float(step_s)
        provider.on_simulation_time(simulation_s)
        if on_step is not None:
            on_step(frame, simulation_s)
        frame += 1
        if sleep_s > 0.0:
            time.sleep(sleep_s)
    return frame - 1


def run_carla_clock(
    provider: RouteProvider,
    *,
    host: str,
    port: int,
    timeout: float,
    frames: int | None = None,
    poll_s: float = 1.0,
) -> None:
    """Follow CARLA world ticks; returns on SIGINT/SIGTERM or after `frames`."""
    import carla  # noqa: WPS433 (bench only)

    client = carla.Client(host, int(port))
    client.set_timeout(float(timeout))
    world = client.get_world()
    settings = world.get_settings()
    provider.log.write(
        "config",
        {
            "clock": "carla world ticks",
            "carlaHost": host,
            "carlaPort": int(port),
            "synchronousMode": bool(settings.synchronous_mode),
            "fixedDeltaSeconds": float(settings.fixed_delta_seconds or 0.0),
        },
    )

    stop = {"requested": False}

    def _stop(_signum, _frame):
        stop["requested"] = True

    try:
        signal.signal(signal.SIGINT, _stop)
        signal.signal(signal.SIGTERM, _stop)
    except ValueError:
        # Not the main thread (embedded use): the caller owns the signals.
        pass

    def _on_tick(snapshot) -> None:
        # Simulation time is the frame index times 100 ms, exact (ICD 1).
        provider.on_simulation_time(int(snapshot.frame) * STEP_SECONDS)

    world.on_tick(_on_tick)
    while not stop["requested"]:
        if frames is not None and provider.ticks >= int(frames):
            break
        time.sleep(float(poll_s))


# ----------------------------------------------------------------------- main


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Announce a route file to the input activity every 500 ms "
        "of simulation time (ICD section 9)"
    )
    parser.add_argument("--route", required=True, help="route JSON path")
    parser.add_argument(
        "--log",
        default=None,
        help="JSONL log path; default <run-dir>/score/route_provider.jsonl",
    )
    parser.add_argument(
        "--run-dir",
        default=None,
        help="run directory (ICD section 7); the log goes to score/",
    )
    parser.add_argument("--udp-host", default=DEFAULT_UDP_HOST)
    parser.add_argument("--udp-port", type=int, default=DEFAULT_UDP_PORT)
    parser.add_argument("--version", type=int, default=INTERFACE_VERSION)
    parser.add_argument(
        "--period-s", type=float, default=ANNOUNCE_PERIOD_S,
        help="announcement period in simulation seconds",
    )
    parser.add_argument(
        "--stale-after-s",
        type=float,
        default=None,
        help="stop announcing after S s of simulation time (route goes stale)",
    )
    parser.add_argument(
        "--empty-after-s",
        type=float,
        default=None,
        help="announce corridorPoints = 0 from S s of simulation time on",
    )
    clock = parser.add_mutually_exclusive_group(required=True)
    clock.add_argument("--fake-clock", action="store_true")
    clock.add_argument("--carla-host", default=None, help="CARLA RPC host")
    parser.add_argument("--carla-port", type=int, default=2000)
    parser.add_argument("--carla-timeout", type=float, default=10.0)
    parser.add_argument(
        "--frames",
        type=int,
        default=None,
        help="stop after N simulation frames (tests, short bench runs)",
    )
    parser.add_argument("--start-frame", type=int, default=0)
    parser.add_argument("--step-s", type=float, default=STEP_SECONDS)
    parser.add_argument(
        "--fake-sleep-s",
        type=float,
        default=0.0,
        help="wall-clock sleep per fake tick (0: as fast as possible)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    log_path = args.log
    if log_path is None and args.run_dir is not None:
        log_path = str(Path(args.run_dir) / "score" / DEFAULT_LOG_NAME)
    log = RunLog(log_path)
    try:
        provider = RouteProvider(
            args.route,
            log=log,
            target=(args.udp_host, int(args.udp_port)),
            version=args.version,
            period_s=args.period_s,
            stale_after_s=args.stale_after_s,
            empty_after_s=args.empty_after_s,
        )
    except Exception as error:
        log.write("error", {"startup": str(error)})
        log.close()
        print(f"error: {error}", file=sys.stderr)
        return 2

    provider.open()
    try:
        if args.fake_clock:
            if args.frames is None:
                print("error: --fake-clock needs --frames", file=sys.stderr)
                return 2
            run_fake_clock(
                provider,
                frames=args.frames,
                step_s=args.step_s,
                start_frame=args.start_frame,
                sleep_s=args.fake_sleep_s,
            )
        else:
            run_carla_clock(
                provider,
                host=args.carla_host,
                port=args.carla_port,
                timeout=args.carla_timeout,
                frames=args.frames,
            )
    except Exception as error:  # pragma: no cover - bench only
        log.write("error", {"run": str(error)})
        print(f"error: {error}", file=sys.stderr)
        return 3
    finally:
        provider.close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
