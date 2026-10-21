#!/usr/bin/env python3
"""Stand-in for someipd in the local dry run of the tooling only.

Offers 0x4dee.0x0001 by SD multicast, accepts the guest's TCP connection on
10.250.0.1:30509 and frames each relayed frame as a SOME/IP notification.
"""

import select
import signal
import socket
import struct
import sys
import time

STOP = False


def on_signal(*_):
    global STOP
    STOP = True


def sd_offer(ttl):
    entry = struct.pack("!BBBBHHB", 0x01, 0, 0, 0x10, 0x4DEE, 0x0001, 1) + ttl.to_bytes(3, "big") + struct.pack("!I", 0)
    sd = struct.pack("!B3xI", 0xC0, len(entry)) + entry + struct.pack("!I", 0)
    header = struct.pack("!HHIHHBBBB", 0xFFFF, 0x8100, 8 + len(sd), 0, 1, 1, 1, 0x02, 0)
    return header + sd


signal.signal(signal.SIGTERM, on_signal)
signal.signal(signal.SIGINT, on_signal)
print("OFFER(0100): [4dee.0001:1.0] (true)", flush=True)
rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
rx.bind(("127.0.0.1", 40001))
listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
listener.bind(("10.250.0.1", 30509))
listener.listen(1)
sd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sd.bind(("10.250.0.1", 30490))
sd.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton("10.250.0.1"))
client = None
session = 0
next_offer = 0.0
while not STOP:
    now = time.monotonic()
    if now >= next_offer:
        sd.sendto(sd_offer(3), ("224.244.224.245", 30490))
        next_offer = now + 1.0
    readable, _, _ = select.select([rx, listener] + ([client] if client else []), [], [], 0.1)
    for sock in readable:
        if sock is listener:
            client, _ = listener.accept()
        elif sock is rx:
            data = rx.recv(65535)
            if client:
                session = (session % 0xFFFF) + 1
                message = struct.pack("!HHIHHBBBB", 0x4DEE, 0x8001, 8 + len(data), 0, session, 1, 1, 0x02, 0) + data
                try:
                    client.sendall(message)
                except OSError:
                    client = None
        else:
            try:
                if not sock.recv(65535):
                    client = None
            except OSError:
                client = None
sd.sendto(sd_offer(0), ("224.244.224.245", 30490))
print("[someipd] Shutting down SOME/IP daemon...", flush=True)
sys.exit(0)
