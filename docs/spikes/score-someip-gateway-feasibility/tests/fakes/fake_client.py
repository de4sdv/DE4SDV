#!/usr/bin/env python3
"""Stand-in for frame_client in the local dry run of the tooling only."""

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


signal.signal(signal.SIGTERM, on_signal)
signal.signal(signal.SIGINT, on_signal)
p = argparse.ArgumentParser()
p.add_argument("--out", required=True)
p.add_argument("--control-dir", default="")
a = p.parse_args()
events = open(os.path.join(a.out, "client_events.log"), "a")
payloads = open(os.path.join(a.out, "client_payloads.bin"), "ab")


def event(text):
    events.write(f"{time.monotonic_ns()} {text}\n")
    events.flush()
    print(text, flush=True)


def take(name):
    path = os.path.join(a.control_dir, name)
    if a.control_dir and os.path.exists(path):
        os.rename(path, path + ".done")
        return True
    return False


assert not os.listdir("/tmp"), "the guest must see a private /tmp"
event(f"START pid={os.getpid()}")
sock, buf, count, subscribed = None, b"", 0, True
while not STOP:
    if take("unsubscribe"):
        subscribed = False
        if sock:
            sock.close()
            sock = None
        event("UNSUBSCRIBE_CALLED")
    if take("resubscribe"):
        subscribed = True
        event("SUBSCRIBE_CALLED reason=control")
    if subscribed and sock is None:
        try:
            sock = socket.create_connection(("10.250.0.1", 30509), timeout=0.5)
            sock.settimeout(0.05)
            buf = b""
            event("AVAILABLE value=1 service=0x4dee instance=0x1")
            event("SUBSCRIPTION_STATUS status=0x0")
        except OSError:
            time.sleep(0.1)
            continue
    if take("probe") and sock:
        req = struct.pack("!HHIHHBBBB", 0x4DEE, 0x0001, 8 + 5, 0x0201, 1, 1, 1, 0x00, 0) + b"PROBE"
        sock.sendall(req)
        event("PROBE_SENT method=0x1")
    if sock is None:
        time.sleep(0.05)
        continue
    try:
        chunk = sock.recv(65535)
        if not chunk:
            sock.close()
            sock = None
            event("AVAILABLE value=0 service=0x4dee instance=0x1")
            continue
        buf += chunk
    except socket.timeout:
        pass
    while len(buf) >= 16:
        length = struct.unpack("!I", buf[4:8])[0]
        if len(buf) < 8 + length:
            break
        msg, buf = buf[:8 + length], buf[8 + length:]
        payload = msg[16:]
        count += 1
        recv = time.monotonic_ns()
        payloads.write(struct.pack("<QI", recv, len(payload)) + payload)
        payloads.flush()
        seq = struct.unpack(">Q", payload[4:12])[0] if len(payload) >= 12 else 0
        event(f"MSG n={count} len={len(payload)} seq={seq}")
event(f"EXIT received={count}")
sys.exit(0)
