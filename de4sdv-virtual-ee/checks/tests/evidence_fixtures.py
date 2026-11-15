"""Synthetic demo archives for the evidence tests.

A *good* archive is built from first principles of the demo's wire contract,
not from the evaluator's own constants: the headlamp command 0x180 and status
0x181 belong to the front zone, the wiper command 0x280 and status 0x281 to the
rear zone, both status frames are routed to the other zone, and one UDS
DiagnosticSessionControl(extended) crosses from front to rear and back as ISO-TP
single frames. Each test then breaks exactly one property.
"""

from __future__ import annotations

import json
from pathlib import Path

# The committed driver (checks/run_demo.sh) alternates eight values per arm.
HEADLAMP_VALUES = [True, False] * 4
WIPER_VALUES = ["FAST", "OFF"] * 4

POSITIVE_UDS_TEXT = (
    "<class 'udsoncan.client.Client'>\n"
    "5003003201f4 \n"
    " <PositiveResponse: [DiagnosticSessionControl] - 5 data bytes at 0x755941e99490>\n"
)
# Verbatim from the review probe: a negative response whose object address
# happens to contain the hex digits 5003.
NEGATIVE_UDS_TEXT = (
    "<class 'udsoncan.client.Client'>\n"
    "7f1022\n"
    " <NegativeResponse: [DiagnosticSessionControl] ConditionsNotCorrect at 0x7215003c8320>\n"
)

UDS_REQUEST = "02 10 03 00 00 00 00 00"
UDS_POSITIVE = "06 50 03 00 32 01 F4 CC"


def line(ts: float, iface: str, arb: int, payload: str) -> str:
    return f" ({ts:.6f})  {iface}  {arb:03X}   [8]  {payload}"


def byte_payload(b0: int, rest: str = "00 00 00 00 00 00 00") -> str:
    return f"{b0:02X} {rest}"


def default_commands(start: float = 1794704073.0) -> list[dict]:
    recs = []
    t = start
    for value in HEADLAMP_VALUES:
        recs.append(
            {"path": "Vehicle.Body.Lights.Beam.Low.IsOn", "value": value, "t0": t, "t5": t + 0.07,
             "ok": True, "polls": 20, "poll_s": 0.002, "arm": "headlamp", "on": "true", "off": "false"}
        )
        t += 1.5
    for value in WIPER_VALUES:
        recs.append(
            {"path": "Vehicle.Body.Windshield.Front.Wiping.Mode", "value": value, "t0": t, "t5": t + 0.07,
             "ok": True, "polls": 20, "poll_s": 0.002, "arm": "wiper", "on": "FAST", "off": "OFF"}
        )
        t += 1.5
    return recs


def captures_for(commands: list[dict], uds_at: float | None, *, route_status: bool = True,
                 drop_command_frame_at: int | None = None, drop_status_frame_at: int | None = None,
                 uds_response: str = UDS_POSITIVE) -> dict[str, list[str]]:
    """Bus traffic that a working vehicle produces for these commands."""
    fl: list[tuple[float, str]] = []
    rl: list[tuple[float, str]] = []
    gwf: list[tuple[float, str]] = []
    gwr: list[tuple[float, str]] = []

    def put(bus, ts, iface, arb, payload):
        bus.append((ts, line(ts, iface, arb, payload)))

    first = min((c["t0"] for c in commands if isinstance(c.get("t0"), (int, float))), default=1794704070.0)
    last = max((c["t0"] for c in commands if isinstance(c.get("t0"), (int, float))), default=first)
    end = max(last, uds_at or last) + 2.0
    state = {"headlamp": 0x00, "wiper": 0x00}
    events = sorted(
        [(c["t0"], i, c) for i, c in enumerate(commands) if isinstance(c.get("t0"), (int, float))],
        key=lambda e: e[0],
    )
    # periodic status, 100 ms, from each owning zone, routed to the other zone
    t = first - 1.0
    k = 0
    while t < end:
        for _t0, i, c in events:
            if c["t0"] + 0.006 <= t:
                state[c["arm"]] = 0x01 if str(c["value"]).lower() == "true" else (0x03 if c["value"] == "FAST" else 0x00)
        hp = byte_payload(state["headlamp"])
        wp = byte_payload(state["wiper"])
        put(fl, t, "vcan0", 0x181, hp)
        put(gwf, t + 0.0002, "vcan-front", 0x181, hp)
        put(rl, t + 0.003, "vcan0", 0x281, wp)
        put(gwr, t + 0.0032, "vcan-rear", 0x281, wp)
        if route_status:
            put(gwr, t + 0.0004, "vcan-rear", 0x181, hp)
            put(rl, t + 0.0008, "vcan0", 0x181, hp)
            put(gwf, t + 0.0034, "vcan-front", 0x281, wp)
            put(fl, t + 0.0038, "vcan0", 0x281, wp)
        t = round(t + 0.1, 6)
        k += 1
    for t0, i, c in events:
        b = 0x01 if str(c["value"]).lower() == "true" else (0x03 if c["value"] == "FAST" else 0x00)
        if c["arm"] == "headlamp":
            own, gw, own_if, gw_if, cmd, st = fl, gwf, "vcan0", "vcan-front", 0x180, 0x181
        else:
            own, gw, own_if, gw_if, cmd, st = rl, gwr, "vcan0", "vcan-rear", 0x280, 0x281
        if drop_command_frame_at != i:
            put(own, t0 + 0.003, own_if, cmd, byte_payload(b))
            put(gw, t0 + 0.0031, gw_if, cmd, byte_payload(b))
        if drop_status_frame_at != i:
            put(own, t0 + 0.0055, own_if, st, byte_payload(b, "00 00 00 00 00 00 01"))
    if uds_at is not None:
        put(fl, uds_at, "vcan0", 0x7E0, UDS_REQUEST)
        put(gwf, uds_at + 0.0004, "vcan-front", 0x7E0, UDS_REQUEST)
        put(gwr, uds_at + 0.0006, "vcan-rear", 0x7E0, UDS_REQUEST)
        put(rl, uds_at + 0.0008, "vcan0", 0x7E0, UDS_REQUEST)
        put(rl, uds_at + 0.0020, "vcan0", 0x7E8, uds_response)
        put(gwr, uds_at + 0.0022, "vcan-rear", 0x7E8, uds_response)
        put(gwf, uds_at + 0.0024, "vcan-front", 0x7E8, uds_response)
        put(fl, uds_at + 0.0027, "vcan0", 0x7E8, uds_response)
    return {name: [ln for _ts, ln in sorted(bus)] for name, bus in
            (("fl", fl), ("rl", rl), ("gwf", gwf), ("gwr", gwr))}


CAPTURE_FILES = {
    "fl": "candump-front-left.log",
    "rl": "candump-rear-left.log",
    "gwf": "candump-gw-front.log",
    "gwr": "candump-gw-rear.log",
}


def write_archive(out: Path, commands: list[dict] | None = None, *, uds_text: str = POSITIVE_UDS_TEXT,
                  **capture_kw) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    commands = default_commands() if commands is None else commands
    uds_at = max(c["t0"] for c in commands if isinstance(c.get("t0"), (int, float))) + 1.2 if commands else 1794704090.0
    caps = captures_for(commands, uds_at, **capture_kw)
    for key, name in CAPTURE_FILES.items():
        (out / name).write_text("\n".join(caps[key]) + "\n")
    (out / "commands.jsonl").write_text("".join(json.dumps(c) + "\n" for c in commands))
    (out / "uds.txt").write_text(uds_text)
    return out


def evaluator_args(archive: Path, out: Path, scenario: str | None = None) -> list[str]:
    args = [
        "--fl", str(archive / CAPTURE_FILES["fl"]),
        "--rl", str(archive / CAPTURE_FILES["rl"]),
        "--gw-front", str(archive / CAPTURE_FILES["gwf"]),
        "--gw-rear", str(archive / CAPTURE_FILES["gwr"]),
        "--commands", str(archive / "commands.jsonl"),
        "--uds", str(archive / "uds.txt"),
        "--out", str(out),
    ]
    if scenario is not None:
        args += ["--scenario", scenario]
    return args
