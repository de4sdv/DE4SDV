#!/usr/bin/env python3
"""Central-app side of a conformance measurement.

Runs inside the central node's network namespace (the only place that can reach
the databroker) and reports two stamps as JSON on stdout:

    t0  immediately before the actuator_target write
    t5  the first poll that observed the new value at the broker

Everything between them (provider receive, CAN transmit, ECU processing, ACK
frame, provider publish) is measured from the bus capture on the host side. The
split is deliberate: this process must not pretend to know when the frame hit
the wire.

Poll interval is reported alongside the numbers because it bounds the t5
resolution; a 2 ms poll cannot resolve sub-millisecond latencies.
"""

from __future__ import annotations

import json
import sys
import time

from kuksa_client.grpc import Datapoint, VSSClient

HOST, PORT = "10.100.0.50", 55555
POLL_S = 0.002

LITERALS = {"true": True, "false": False}


def coerce(raw: str):
    if raw.lower() in LITERALS:
        return LITERALS[raw.lower()]
    if raw.lstrip("-").isdigit():
        return int(raw)
    return raw


def main() -> int:
    path, raw = sys.argv[1], sys.argv[2]
    timeout = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
    value = coerce(raw)

    with VSSClient(HOST, PORT) as client:
        t0 = time.time()
        client.set_target_values({path: Datapoint(value)})
        t5 = None
        polls = 0
        while time.time() - t0 < timeout:
            polls += 1
            seen = client.get_current_values([path])[path].value
            if seen == value:
                t5 = time.time()
                break
            time.sleep(POLL_S)

    print(
        json.dumps(
            {
                "path": path,
                "value": value,
                "t0": t0,
                "t5": t5,
                "ok": t5 is not None,
                "polls": polls,
                "poll_s": POLL_S,
            }
        )
    )
    return 0 if t5 is not None else 1


if __name__ == "__main__":
    sys.exit(main())
