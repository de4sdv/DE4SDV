#!/usr/bin/env python3
"""DE4SDV zone ECU plant model.

This is the part of a zonal ECU that has no upstream equivalent: the reference
actuators in the SDV simulation decode a private CMD/ACK/NACK byte protocol and
the wiper never answers at all. Here the frame layout is the DBC in ``dbc/`` and
every ECU acknowledges the command sequence number on the bus.

What it models
--------------
* **headlamp** — stateless. Accepts ``Headlamp_Low_Req`` / ``Headlamp_High_Req``,
  reports the resulting lamp state and the acknowledged sequence number.
* **wiper** — a sweeping blade. Accepts a mode, drives ``Wiper_Position_pct``
  through a full park-to-park sweep, and raises ``Wiper_Position_Reached`` once
  the first complete sweep for the accepted command has finished. That boolean
  is the acknowledgement the reference demo does not implement.

It is a plant, not an ECU implementation: no diagnostics, no fault injection, no
timing guarantees. The zone's real-time honesty is the report's job, not this
file's.
"""

from __future__ import annotations

import argparse
import math
import sys
import time

import can
import cantools

COMMAND_SUFFIX = "_Cmd"
STATUS_SUFFIX = "_Status"


class HeadlampPlant:
    def __init__(self) -> None:
        self.low = False
        self.high = False
        self.ack = 0

    def apply(self, decoded: dict) -> bool:
        seq = decoded["Headlamp_Cmd_Seq"]
        low = bool(decoded["Headlamp_Low_Req"])
        high = bool(decoded["Headlamp_High_Req"])
        changed = (low, high) != (self.low, self.high) or seq != self.ack
        self.low, self.high, self.ack = low, high, seq
        return changed

    def status(self) -> dict:
        return {
            "Headlamp_Low_On": int(self.low),
            "Headlamp_High_On": int(self.high),
            "Headlamp_Fault": 0,
            "Headlamp_Seq_Ack": self.ack,
        }


class WiperPlant:
    """Sweep model: park -> 100% -> park, one step per status period."""

    def __init__(self, step_pct_per_s: float = 200.0) -> None:
        self.mode = 0
        self.ack = 0
        self.position = 0.0
        self.step = step_pct_per_s
        self.direction = 1
        self.sweep_pending = False
        self.reached = True
        self.visited_full = False

    def apply(self, decoded: dict) -> bool:
        seq = decoded["Wiper_Cmd_Seq"]
        mode = int(decoded["Wiper_Mode_Req"])
        changed = mode != self.mode or seq != self.ack
        if changed:
            self.mode, self.ack = mode, seq
            self.reached = False
            self.visited_full = False
            self.sweep_pending = mode != 0
            if mode == 0:
                self.reached = True  # parking: nothing to acknowledge beyond OFF
        return changed

    def advance(self, dt: float) -> None:
        if self.mode == 0:
            self.position = max(0.0, self.position - self.step * dt)
            if self.position == 0.0:
                self.direction = 1
            return
        # triangular sweep: park -> full -> park, direction flips at the stops
        self.position += self.direction * self.step * dt
        if self.position >= 100.0:
            self.position = 100.0
            self.direction = -1
            self.visited_full = True
        elif self.position <= 0.0:
            self.position = 0.0
            self.direction = 1
            if self.visited_full and self.sweep_pending:
                self.reached = True
                self.sweep_pending = False

    def status(self) -> dict:
        return {
            "Wiper_Mode_State": self.mode,
            "Wiper_Position_pct": int(round(min(100.0, max(0.0, self.position)))),
            "Wiper_Position_Reached": int(self.reached),
            "Wiper_Error": 0,
            "Wiper_Seq_Ack": self.ack,
        }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ecu", required=True, choices=["headlamp", "wiper"])
    ap.add_argument("--dbc", required=True)
    ap.add_argument("--channel", default="vcan0")
    ap.add_argument("--period", type=float, default=0.1, help="status period in seconds")
    args = ap.parse_args()

    db = cantools.database.load_file(args.dbc)
    cmd = next(m for m in db.messages if m.name.endswith(COMMAND_SUFFIX))
    status = next(m for m in db.messages if m.name.endswith(STATUS_SUFFIX))

    plant = HeadlampPlant() if args.ecu == "headlamp" else WiperPlant()
    bus = can.Bus(interface="socketcan", channel=args.channel)

    print(
        f"[ecu] {args.ecu} on {args.channel}: cmd=0x{cmd.frame_id:X} status=0x{status.frame_id:X}",
        flush=True,
    )

    next_status = time.monotonic()
    last_status = time.monotonic()
    try:
        while True:
            now = time.monotonic()
            timeout = max(0.0, next_status - now)
            frame = bus.recv(timeout=timeout)

            if frame is not None and frame.arbitration_id == cmd.frame_id:
                try:
                    decoded = cmd.decode(frame.data, decode_choices=True)
                except Exception as exc:  # noqa: BLE001 - a bad frame must not kill the zone
                    print(f"[ecu] undecodable command frame: {exc}", file=sys.stderr, flush=True)
                else:
                    if plant.apply(decoded):
                        print(f"[ecu] accepted cmd {decoded}", flush=True)

            now = time.monotonic()
            if isinstance(plant, WiperPlant):
                plant.advance(now - last_status)
            last_status = now

            if now >= next_status:
                payload = status.encode(plant.status(), scaling=True, choices=True)
                bus.send(can.Message(arbitration_id=status.frame_id, data=payload, is_extended_id=False))
                next_status = now + args.period
    except KeyboardInterrupt:
        pass
    finally:
        bus.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
