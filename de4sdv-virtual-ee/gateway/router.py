#!/usr/bin/env python3
"""DE4SDV zonal CAN gateway.

Sits between two vehicle buses that are physically separate (each lives in its
own zone's network namespace, connected only by the slices) and applies a
per-frame allow-list in each direction.

The policy is the point of the exercise, not the forwarding:

* **status crosses, commands do not.** A zone publishes what it observes; no
  zone can actuate another zone's hardware. `0x181` (headlamp status) is
  forwarded front->rear, `0x280` (wiper command) is refused rear->front.

Every decision is counted, so "denied" is a number rather than a claim, and the
dropped frames are visible in the stats rather than silently disappearing.

Echo guard: if a transport ever re-injects a frame the gateway just forwarded,
the identical (id, payload) arriving within ECHO_WINDOW_S is dropped instead of
ping-ponging. The DE4SDV bridge does not echo (a SocketCAN socket does not see
its own frames), but a router peer that re-injected would turn the path into a
broadcast storm, so the guard stays.
"""

from __future__ import annotations

import argparse
import signal
import sys
import threading
import time
from collections import Counter

import can

ECHO_WINDOW_S = 0.05

# direction -> allowed CAN ids
POLICY: dict[str, set[int]] = {
    # headlamp status, plus the diagnostic request a tester on the front segment
    # sends to the rear zone's ECU through the gateway
    "front->rear": {0x181, 0x7E0},
    # wiper status, plus that ECU's diagnostic response on its way back
    "rear->front": {0x281, 0x7E8},
}
# deliberately absent: 0x180 headlamp command, 0x280 wiper command.
# Diagnostics are allowed to cross because a tester reaches a zonal ECU through the
# gateway; actuator commands are not, because a zone must not drive another's load.

stop = threading.Event()
stats: Counter = Counter()
lock = threading.Lock()


def bump(key: str, n: int = 1) -> None:
    with lock:
        stats[key] += n


def forwarded_recently(seen: dict[tuple[int, bytes], float], key: tuple[int, bytes]) -> bool:
    now = time.monotonic()
    for k, ts in list(seen.items()):
        if now - ts > ECHO_WINDOW_S:
            del seen[k]
    return key in seen


def pump(src_name: str, dst_name: str, src_bus: can.BusABC, dst_bus: can.BusABC, direction: str) -> None:
    allowed = POLICY[direction]
    seen: dict[tuple[int, bytes], float] = {}
    while not stop.is_set():
        frame = src_bus.recv(timeout=0.1)
        if frame is None:
            continue
        key = (frame.arbitration_id, bytes(frame.data))
        if forwarded_recently(seen, key):
            bump(f"{direction}.echo_dropped")
            continue
        if frame.arbitration_id not in allowed:
            bump(f"{direction}.denied.0x{frame.arbitration_id:03X}")
            continue
        dst_bus.send(
            can.Message(arbitration_id=frame.arbitration_id, data=frame.data, is_extended_id=frame.is_extended_id)
        )
        seen[key] = time.monotonic()
        bump(f"{direction}.forwarded.0x{frame.arbitration_id:03X}")


def report(signum=None, _frame=None) -> None:
    with lock:
        snapshot = dict(stats)
    print("gateway stats:")
    for k in sorted(snapshot):
        print(f"  {k:38s} {snapshot[k]}")
    print(f"  policy front->rear: {sorted(hex(i) for i in POLICY['front->rear'])}")
    print(f"  policy rear->front: {sorted(hex(i) for i in POLICY['rear->front'])}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--front", default="vcan-front")
    ap.add_argument("--rear", default="vcan-rear")
    args = ap.parse_args()

    front = can.Bus(interface="socketcan", channel=args.front)
    rear = can.Bus(interface="socketcan", channel=args.rear)

    threads = [
        threading.Thread(target=pump, args=("front", "rear", front, rear, "front->rear"), daemon=True),
        threading.Thread(target=pump, args=("rear", "front", rear, front, "rear->front"), daemon=True),
    ]
    for t in threads:
        t.start()

    def shutdown(signum, frame):
        stop.set()
        report()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    while not stop.is_set():
        time.sleep(1)
    for t in threads:
        t.join(timeout=2)
    front.shutdown()
    rear.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
