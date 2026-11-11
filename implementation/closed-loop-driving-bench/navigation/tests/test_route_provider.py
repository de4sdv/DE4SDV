"""The route provider: datagram layout, cadence, fault knobs, logs.

The datagram layout is checked against the C++ ``payloads.h`` through the
layout probe built into ``raster_cli --layout``, so the Python packer and the
S-CORE contract cannot drift apart silently.
"""

from __future__ import annotations

import hashlib
import json
import socket
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest

import route_provider

ROOT = Path(__file__).resolve().parent.parent


def _route_file(path: Path, count: int = 11, name: str = "Town10HD_Opt") -> Path:
    rows = [[2.0 * index, 0.0, 0.0, 1] for index in range(count)]
    path.write_text(
        json.dumps(
            {"map": name, "waypoints": rows, "destination": [rows[-1][0], 0.0]},
            separators=(",", ":"),
        )
        + "\n",
        encoding="ascii",
    )
    return path


# ------------------------------------------------------------------ layout


def test_datagram_is_272_bytes_with_the_payloads_h_offsets(raster_cli):
    probe = subprocess.run([str(raster_cli), "--layout"], capture_output=True,
                           text=True, check=True)
    layout = json.loads(probe.stdout)
    assert layout["size"] == route_provider.ANNOUNCEMENT_BYTES == 272
    assert layout["version"] == 0
    assert layout["corridorPoints"] == 4
    assert layout["issueTime"] == 8
    assert layout["routeFile"] == 16
    assert layout["routeSha256"] == 208
    assert layout["routeFileBytes"] == 192
    assert layout["routeSha256Bytes"] == 64
    assert layout["kInterfaceVersion"] == route_provider.INTERFACE_VERSION
    assert route_provider.ANNOUNCEMENT.format == "<IId192s64s"


def test_announcement_round_trip(tmp_path):
    route = _route_file(tmp_path / "route.json", count=7)
    import hashlib

    digest = hashlib.sha256(route.read_bytes()).hexdigest()
    datagram = route_provider.build_announcement(
        corridor_points=7,
        issue_time=12.3,
        route_file=str(route),
        route_sha256=digest,
    )
    decoded = route_provider.parse_announcement(datagram)
    assert decoded["version"] == route_provider.INTERFACE_VERSION
    assert decoded["corridorPoints"] == 7
    assert decoded["issueTime"] == 12.3
    assert decoded["routeFile"] == str(route.resolve())
    assert decoded["routeSha256"] == digest
    # The struct is little-endian: version 1 is 01 00 00 00.
    assert datagram[:4] == route_provider.INTERFACE_VERSION.to_bytes(4, "little")
    assert struct.unpack("<d", datagram[8:16])[0] == 12.3


def test_long_paths_are_truncated_and_nul_terminated():
    long_path = "/" + "a" * 400
    datagram = route_provider.build_announcement(
        corridor_points=1,
        issue_time=0.0,
        route_file=long_path,
        route_sha256="b" * 64,
    )
    raw = datagram[16:208]
    assert len(raw) == 192
    assert raw.endswith(b"\x00")
    assert b"\x00" not in raw.rstrip(b"\x00")
    with pytest.raises(ValueError):
        route_provider.build_announcement(
            corridor_points=1, issue_time=0.0, route_file="/x",
            route_sha256="short",
        )


# ------------------------------------------------------------------ cadence


def test_announces_every_500_ms_of_simulation_time(tmp_path):
    route = _route_file(tmp_path / "route.json")
    provider = route_provider.RouteProvider(route, sock=_NullSocket())
    provider.open()
    route_provider.run_fake_clock(provider, frames=51)  # 0.0 .. 5.0 s
    provider.close()
    # 0.0, 0.5, 1.0, ... 5.0 -> 11 announcements
    assert provider.announcements == 11
    assert provider.ticks == 51


def test_announcement_carries_the_tick_time(tmp_path):
    route = _route_file(tmp_path / "route.json")
    sock = _RecordingSocket()
    provider = route_provider.RouteProvider(route, sock=sock)
    provider.open()
    route_provider.run_fake_clock(provider, frames=6)  # 0.0 .. 0.5 s
    provider.close()
    decoded = [route_provider.parse_announcement(item) for item in sock.sent]
    assert [item["issueTime"] for item in decoded] == pytest.approx([0.0, 0.5])
    assert all(item["corridorPoints"] == 11 for item in decoded)
    assert decoded[0]["version"] == route_provider.INTERFACE_VERSION


def test_stale_knob_stops_announcing(tmp_path):
    route = _route_file(tmp_path / "route.json")
    log_path = tmp_path / "route_provider.jsonl"
    sock = _RecordingSocket()
    provider = route_provider.RouteProvider(
        route,
        sock=sock,
        log=route_provider.RunLog(log_path),
        stale_after_s=1.0,
    )
    provider.open()
    route_provider.run_fake_clock(provider, frames=31)  # 0.0 .. 3.0 s
    provider.close()
    # Last announcement at 0.5 s; at 1.0 s the route goes stale.
    decoded = [route_provider.parse_announcement(item) for item in sock.sent]
    assert [item["issueTime"] for item in decoded] == pytest.approx([0.0, 0.5])
    records = [json.loads(line) for line in log_path.read_text().splitlines()]
    events = [record["event"] for record in records]
    assert events.count("fault.stale") == 1
    assert events[-1] == "stop"


def test_empty_knob_announces_zero_corridor_points(tmp_path):
    route = _route_file(tmp_path / "route.json")
    sock = _RecordingSocket()
    provider = route_provider.RouteProvider(
        route, sock=sock, empty_after_s=1.0
    )
    provider.open()
    route_provider.run_fake_clock(provider, frames=21)  # 0.0 .. 2.0 s
    provider.close()
    decoded = [route_provider.parse_announcement(item) for item in sock.sent]
    assert [item["issueTime"] for item in decoded] == pytest.approx(
        [0.0, 0.5, 1.0, 1.5, 2.0]
    )
    assert [item["corridorPoints"] for item in decoded] == [11, 11, 0, 0, 0]
    # The identity is unchanged: the file is untouched, only the count is 0.
    assert len({item["routeSha256"] for item in decoded}) == 1


def test_log_records_follow_icd_section_6(tmp_path):
    route = _route_file(tmp_path / "route.json")
    log_path = tmp_path / "score" / "route_provider.jsonl"
    provider = route_provider.RouteProvider(
        route, sock=_NullSocket(), log=route_provider.RunLog(log_path)
    )
    provider.open()
    route_provider.run_fake_clock(provider, frames=11)
    provider.close()
    records = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert [record["event"] for record in records] == [
        "start", "config", "out.route_announcement", "out.route_announcement",
        "out.route_announcement", "stop"
    ]
    for index, record in enumerate(records):
        assert set(record) == {
            "t_mono_ns", "t_real_ns", "host", "component", "event", "seq", "data"
        }
        assert record["seq"] == index + 1
        assert record["host"] == "score"
        assert record["component"] == "routeProvider"
        assert record["t_mono_ns"] > 0 and record["t_real_ns"] > 0
    announcement = records[2]["data"]
    assert announcement["routeFile"] == str(route.resolve())
    assert announcement["corridorPoints"] == 11
    assert announcement["bytes"] == 272
    assert len(announcement["routeSha256"]) == 64


# ------------------------------------------------------------- CARLA clock


def test_the_evaluators_read_the_provider_log(tmp_path):
    """The record is the evaluators' contract (case-evaluators/OBSERVABLES.md row 025,
    VC-DRIVING-025): event out.route_announcement, issueTime marked as simulation time
    (ICD C9). Read through runio, the evaluators' own reader, not a re-implementation."""
    import sys
    evaluators = Path(__file__).resolve().parents[2] / "case-evaluators"
    sys.path.insert(0, str(evaluators))
    try:
        import runio
    finally:
        sys.path.remove(str(evaluators))
    route = _route_file(tmp_path / "route.json")
    run_dir = tmp_path / "run"
    provider = route_provider.RouteProvider(
        route, sock=_NullSocket(), log=route_provider.RunLog(run_dir / "score" / "route_provider.jsonl"),
        empty_after_s=1.0,
    )
    provider.open()
    route_provider.run_fake_clock(provider, frames=21, start_frame=5000)  # 500.0 .. 502.0 s
    provider.close()
    (run_dir / "run_record.json").write_text(json.dumps({     # runio opens a run by its record
        "contractIdentity": "de4sdv.driving.icd.v2", "scenario": "degradedInputOrPlan",
        "runRole": "fault", "campaignId": "route-provider-tests",
        "scenarioVariant": {"fault": "route_empty"}}))
    anns = runio.Run(run_dir).route_announcements()
    assert [a["issue_s"] for a in anns] == pytest.approx([500.0, 500.5, 501.0, 501.5, 502.0])
    assert [a["corridor"] for a in anns] == [11, 11, 0, 0, 0]
    assert {a["sha"] for a in anns} == {hashlib.sha256(route.read_bytes()).hexdigest()}


def test_carla_clock_follows_world_ticks(tmp_path):
    """--carla-host mode: simulation time is frame * 0.1 s, from world ticks."""
    import carla

    route = _route_file(tmp_path / "route.json")
    sock = _RecordingSocket()
    provider = route_provider.RouteProvider(
        route,
        sock=sock,
        log=route_provider.RunLog(tmp_path / "log.jsonl"),
    )
    provider.open()
    result: dict[str, Any] = {}

    def _drive() -> None:
        try:
            route_provider.run_carla_clock(
                provider, host="127.0.0.1", port=2000, timeout=1.0,
                frames=11, poll_s=0.005,
            )
        except Exception as error:  # pragma: no cover
            result["error"] = error

    worker = threading.Thread(target=_drive, daemon=True)
    worker.start()
    deadline = time.time() + 5.0
    while carla.Client.last is None and time.time() < deadline:
        time.sleep(0.005)
    world = carla.Client.last.world
    # Wait for the provider's on_tick registration: a tick that lands before it
    # would never reach the provider and the first announcement would move.
    while not world.has_tick_callbacks() and time.time() < deadline:
        time.sleep(0.005)
    while world.get_snapshot().frame < 11 and time.time() < deadline:
        world.tick()
        time.sleep(0.005)
    worker.join(timeout=5.0)
    provider.close()
    assert "error" not in result
    decoded = [route_provider.parse_announcement(item) for item in sock.sent]
    # Frames 1..11 are 0.1 .. 1.1 s: the first tick announces at once, then
    # every 0.5 s.  Every announcement carries the newest tick's time.
    ticks = [round(item["issueTime"], 6) for item in decoded]
    assert ticks == [0.1, 0.6, 1.1]
    assert all(item["corridorPoints"] == 11 for item in decoded)
    assert provider.ticks == 11
    records = [json.loads(line) for line in
               (tmp_path / "log.jsonl").read_text().splitlines()]
    config = [record for record in records if record["event"] == "config"]
    assert any(item["data"].get("clock") == "carla world ticks" for item in config)


# ---------------------------------------------------------------- end to end


def _bind_receiver() -> tuple[socket.socket, int]:
    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver.bind(("127.0.0.1", 0))
    receiver.settimeout(5.0)
    return receiver, receiver.getsockname()[1]


def test_end_to_end_udp_process(tmp_path):
    route = _route_file(tmp_path / "route.json")
    receiver, port = _bind_receiver()
    log_path = tmp_path / "run" / "score" / "route_provider.jsonl"
    process = subprocess.Popen(
        [
            sys.executable, str(ROOT / "route_provider.py"),
            "--route", str(route),
            "--run-dir", str(tmp_path / "run"),
            "--udp-port", str(port),
            "--fake-clock", "--frames", "26", "--start-frame", "0",
        ],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    received = []
    try:
        while len(received) < 6:
            data, _ = receiver.recvfrom(4096)
            received.append(data)
    except socket.timeout:  # pragma: no cover
        pass
    finally:
        process.wait(timeout=10)
        receiver.close()
    assert process.returncode == 0, process.stderr.read()
    assert len(received) == 6
    assert all(len(item) == route_provider.ANNOUNCEMENT_BYTES for item in received)
    decoded = [route_provider.parse_announcement(item) for item in received]
    assert [item["issueTime"] for item in decoded] == pytest.approx(
        [0.0, 0.5, 1.0, 1.5, 2.0, 2.5]
    )
    assert log_path.is_file()
    records = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert sum(record["event"] == "out.route_announcement" for record in records) == 6


def test_missing_route_file_fails_before_sending(tmp_path):
    code = route_provider.main([
        "--route", str(tmp_path / "absent.json"),
        "--fake-clock", "--frames", "3",
        "--log", str(tmp_path / "log.jsonl"),
    ])
    assert code == 2
    records = [json.loads(line) for line in
               (tmp_path / "log.jsonl").read_text().splitlines()]
    assert records[0]["event"] == "error"


# ---------------------------------------------- validity consumed by the C++ side


@pytest.mark.parametrize("issue,now,corridor_points,cause,stale,empty", [
    (0.0, 0.9, 11, 0, False, False),
    (0.0, 1.0, 11, 0, False, False),   # exactly 1 s is not "more than 1 s"
    (0.0, 1.1, 11, 6, True, False),
    (0.0, 5.0, 0, 7, True, True),      # empty reported first
    (0.0, 0.2, 0, 7, False, True),
])
def test_cpp_validity_matches_req_025(issue, now, corridor_points, cause, stale,
                                      empty, tmp_path, raster_cli, cli_runner,
                                      native_library):
    """The C++ RouteValidity decides REQ-DRIVING-025 the same way."""
    import synthetic

    navigation_map = synthetic.MAPS["straight"]()
    import nav_map_json

    map_path = tmp_path / "map.json"
    nav_map_json.dump_map(map_path, navigation_map)
    route_path = synthetic.write_route(tmp_path / "route.json", "straight")
    summary = cli_runner(
        raster_cli,
        "--map", str(map_path),
        "--route", str(route_path),
        "--pose", "0", "0", "0",
        "--announce-issue", repr(issue),
        "--now", repr(now),
        "--announce-corridor-points", str(corridor_points),
    )
    validity = summary["validity"]
    # The route file always has a corridor; "no corridor" is the announcement
    # saying corridorPoints = 0, which is what --announce-corridor-points does.
    assert validity["corridor_present"] is True
    assert validity["corridor_declared"] == (corridor_points > 0)
    assert validity["stale"] is stale
    assert validity["empty"] is empty
    assert validity["cause"] == cause
    assert summary["no_announcement"]["stale"] is True
    assert summary["no_announcement"]["age_infinite"] is True


class _NullSocket:
    def sendto(self, data, target):
        return len(data)


class _RecordingSocket(_NullSocket):
    def __init__(self):
        self.sent = []

    def sendto(self, data, target):
        self.sent.append(bytes(data))
        return len(data)
