#!/usr/bin/env python3
"""Stand-in for frame_publisher in the local dry run of the tooling only.

Same CLI, same frame layout, same logs as the C++ publisher; sends each frame
by UDP to 127.0.0.1:40000 (the fake gatewayd) instead of mw::com.
"""

import argparse
import os
import signal
import socket
import struct
import sys
import time

STOP = False


def on_signal(*_):
    global STOP
    STOP = True


def splitmix(state):
    state = (state + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    z = state
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    return state, z ^ (z >> 31)


def frame_size(seq):
    rest = seq % 10
    if rest == 1:
        return 2048
    if rest == 2:
        return 20
    if rest == 3:
        return 1500
    if rest == 4:
        return 1501
    _, value = splitmix((seq * 7919) & 0xFFFFFFFFFFFFFFFF)
    return 20 + value % (2048 - 20 + 1)


def build_frame(seq, t_ns):
    total = frame_size(seq)
    out = bytearray(struct.pack(">IQQ", total - 4, seq, t_ns))
    state = seq ^ 0xDE45D7A1C0FFEE
    while len(out) < total:
        state, value = splitmix(state)
        out += value.to_bytes(8, "little")[: total - len(out)]
    return bytes(out)


def main():
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    p = argparse.ArgumentParser()
    p.add_argument("--service_instance_manifest", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--tag", default="publisher")
    p.add_argument("--frames", type=int, default=0)
    p.add_argument("--period-ms", type=int, default=50)
    p.add_argument("--start-seq", type=int, default=1)
    p.add_argument("--pause-at", default="")
    p.add_argument("--go-file", default="")
    p.add_argument("--linger-s", type=int, default=0)
    a = p.parse_args()
    pause_at = {int(x) for x in a.pause_at.split(",") if x}
    events = open(os.path.join(a.out, f"{a.tag}_events.log"), "a")
    frames = open(os.path.join(a.out, f"{a.tag}_frames.bin"), "ab")

    def event(text):
        events.write(f"{time.monotonic_ns()} {text}\n")
        events.flush()
        print(text, flush=True)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    event(f"START pid={os.getpid()} start_seq={a.start_seq}")
    event("OFFERED")
    open(os.path.join(a.out, f"{a.tag}.offered"), "w").close()
    if a.go_file:
        while not STOP and not os.path.exists(a.go_file):
            time.sleep(0.01)
        event("GO")
    seq, attempted = a.start_seq, 0
    nxt = time.monotonic()
    while not STOP and (a.frames == 0 or attempted < a.frames):
        t_ns = time.monotonic_ns()
        data = build_frame(seq, t_ns)
        sock.sendto(data, ("127.0.0.1", 40000))
        frames.write(struct.pack("<QQI", seq, t_ns, len(data)) + data)
        frames.flush()
        event(f"SENT seq={seq} len={len(data)}")
        attempted += 1
        if seq in pause_at:
            event(f"PAUSED seq={seq}")
            open(os.path.join(a.out, f"{a.tag}.paused-{seq}"), "w").close()
            while not STOP and not os.path.exists(os.path.join(a.out, f"resume-{seq}")):
                time.sleep(0.01)
            event(f"RESUMED seq={seq}")
            nxt = time.monotonic()
        seq += 1
        nxt += a.period_ms / 1000
        while not STOP and time.monotonic() < nxt:
            time.sleep(0.005)
    event(f"DONE attempted={attempted}")
    open(os.path.join(a.out, f"{a.tag}.done"), "w").close()
    end = time.monotonic() + a.linger_s
    while not STOP and time.monotonic() < end:
        time.sleep(0.05)
    event("STOP_OFFER")
    event("EXIT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
