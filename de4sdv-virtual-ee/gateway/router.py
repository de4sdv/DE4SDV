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

No echo guard. A frame the gateway forwards cannot come back to it as a new
frame: a SocketCAN socket does not receive its own transmissions
(`CAN_RAW_RECV_OWN_MSGS` is off), the DE4SDV bridge does not echo either, and
the two allow-lists are disjoint, so even a re-injected frame would be refused
by the opposite direction rather than loop. Identical frames repeated by a
sender (an ISO-TP consecutive frame after its sequence number wraps, a status
that did not change) are legitimate traffic and are all forwarded. If a
transport that echoes is ever added, loop prevention belongs on that transport's
receive path, not in a content filter here.
"""

from __future__ import annotations

import argparse
import errno
import signal
import sys
import threading
import time
from collections import Counter

import can

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

# A full transmit queue is back-pressure: the frame is lost, as on a busy bus, and
# counted; the direction keeps forwarding. python-can's SocketCAN backend reports
# it as CanOperationError with ENOBUFS or EAGAIN, or with no errno when the send
# timed out ("Transmit buffer full"). Any other send error ends the pump.
TRANSIENT_SEND_ERRORS = {errno.ENOBUFS, errno.EAGAIN, None}

stop = threading.Event()
stats: Counter = Counter()
lock = threading.Lock()
died: dict[str, str] = {}  # direction -> why its pump stopped


def bump(key: str, n: int = 1) -> None:
    with lock:
        stats[key] += n


def pump(src_name: str, dst_name: str, src_bus: can.BusABC, dst_bus: can.BusABC, direction: str) -> None:
    """Forward one direction until stopped. A pump that cannot go on records why
    and stops the gateway: half a gateway must not look like a running one."""
    try:
        forward(src_bus, dst_bus, direction)
    except Exception as exc:
        code = getattr(exc, "error_code", None)
        name = errno.errorcode.get(code, "") if isinstance(code, int) else ""
        with lock:
            died[direction] = " ".join(part for part in (type(exc).__name__, name, str(exc)) if part)
        stop.set()
        raise


def forward(src_bus: can.BusABC, dst_bus: can.BusABC, direction: str) -> None:
    allowed = POLICY[direction]
    while not stop.is_set():
        frame = src_bus.recv(timeout=0.1)
        if frame is None:
            continue
        if frame.arbitration_id not in allowed:
            bump(f"{direction}.denied.0x{frame.arbitration_id:03X}")
            continue
        try:
            dst_bus.send(
                can.Message(arbitration_id=frame.arbitration_id, data=frame.data, is_extended_id=frame.is_extended_id)
            )
        except can.CanOperationError as exc:
            if exc.error_code not in TRANSIENT_SEND_ERRORS:
                raise
            reason = errno.errorcode[exc.error_code] if exc.error_code else "buffer_full"
            bump(f"{direction}.send_error.{reason}")
            continue
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

    while not stop.wait(1):
        pass
    for t in threads:
        t.join(timeout=2)
    front.shutdown()
    rear.shutdown()
    if died:
        for direction, why in sorted(died.items()):
            print(f"gateway: {direction} pump died: {why}", file=sys.stderr, flush=True)
        report()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
