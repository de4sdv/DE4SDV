#!/usr/bin/env python3
"""Offline tests for the zone ECU plant model and the frame layout.

No bus, no broker, no VM: the plant is a pure function of the commands it
receives, so the acknowledgement logic can be proved before any of the
expensive parts exist.

Run:  python de4sdv-virtual-ee/env/test_zone_ecu.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import cantools

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "zones"))

from zone_ecu import HeadlampPlant, WiperPlant  # noqa: E402

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"PASS  {name}")
    else:
        failures.append(f"{name} {detail}".strip())
        print(f"FAIL  {name} {detail}")


def test_headlamp() -> None:
    plant = HeadlampPlant()
    check("headlamp starts dark", plant.status()["Headlamp_Low_On"] == 0)

    plant.apply({"Headlamp_Low_Req": 1, "Headlamp_High_Req": 0, "Headlamp_Cmd_Seq": 7})
    s = plant.status()
    check("headlamp accepts low beam", s["Headlamp_Low_On"] == 1)
    check("headlamp acknowledges the sequence number", s["Headlamp_Seq_Ack"] == 7)

    plant.apply({"Headlamp_Low_Req": 0, "Headlamp_High_Req": 1, "Headlamp_Cmd_Seq": 8})
    s = plant.status()
    check("headlamp switches to high beam", (s["Headlamp_Low_On"], s["Headlamp_High_On"]) == (0, 1))
    check("headlamp ack advances", s["Headlamp_Seq_Ack"] == 8)


def test_wiper() -> None:
    plant = WiperPlant(step_pct_per_s=400.0)
    plant.apply({"Wiper_Mode_Req": 1, "Wiper_Interval_ms": 0, "Wiper_Cmd_Seq": 3})
    s = plant.status()
    check("wiper accepts SLOW", s["Wiper_Mode_State"] == 1)
    check("wiper acks immediately", s["Wiper_Seq_Ack"] == 3)
    check("wiper does not claim arrival before moving", s["Wiper_Position_Reached"] == 0)

    # drive a full sweep at 400 %/s in 100 ms steps: park->100->park in ~0.5 s
    for _ in range(40):
        plant.advance(0.1)
    s = plant.status()
    check("wiper reaches the commanded position", s["Wiper_Position_Reached"] == 1)
    check("wiper position stays inside 0..100", 0 <= s["Wiper_Position_pct"] <= 100, f"got {s}")

    plant.apply({"Wiper_Mode_Req": 0, "Wiper_Interval_ms": 0, "Wiper_Cmd_Seq": 4})
    for _ in range(30):
        plant.advance(0.1)
    s = plant.status()
    check("wiper parks on OFF", s["Wiper_Position_pct"] == 0)
    check("wiper acks OFF", (s["Wiper_Mode_State"], s["Wiper_Seq_Ack"]) == (0, 4))


def test_frames_roundtrip() -> None:
    db = cantools.database.Database()
    for name in ("headlamp.dbc", "wiper.dbc"):
        db.add_dbc_file(str(ROOT / "dbc" / name))

    headlamp = db.get_message_by_name("DE4SDV_Headlamp_Status")
    payload = headlamp.encode(
        {"Headlamp_Low_On": 1, "Headlamp_High_On": 0, "Headlamp_Fault": 0, "Headlamp_Seq_Ack": 42}
    )
    decoded = headlamp.decode(payload, decode_choices=True)
    check("headlamp status frame round-trips", decoded["Headlamp_Seq_Ack"] == 42 and decoded["Headlamp_Low_On"] == 1)

    wiper = db.get_message_by_name("DE4SDV_Wiper_Cmd")
    payload = wiper.encode({"Wiper_Mode_Req": "MEDIUM", "Wiper_Interval_ms": 400, "Wiper_Cmd_Seq": 9})
    decoded = wiper.decode(payload, decode_choices=True)
    check(
        "wiper command decodes its VAL_ label",
        decoded["Wiper_Mode_Req"] == "MEDIUM" and decoded["Wiper_Interval_ms"] == 400,
        f"got {decoded}",
    )


def main() -> int:
    test_headlamp()
    test_wiper()
    test_frames_roundtrip()
    if failures:
        print(f"\nFAILED ({len(failures)})")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nPASS  plant model and frame layout behave as specified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
