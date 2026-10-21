#!/usr/bin/env python3
"""Stand-in for tcpdump in the local dry run only (tcpdump cannot drop privileges
inside an unprivileged user namespace). AF_PACKET capture to a classic
nanosecond pcap, Ethernet link type, packet-buffered."""

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
interface, path = sys.argv[1], sys.argv[2]
sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))
sock.bind((interface, 0))
sock.settimeout(0.1)
out = open(path, "wb")
out.write(struct.pack("<IHHiIII", 0xA1B23C4D, 2, 4, 0, 0, 262144, 1))
out.flush()
print(f"listening on {interface}", flush=True)
while not STOP:
    try:
        frame = sock.recv(262144)
    except socket.timeout:
        continue
    now = time.time_ns()
    out.write(struct.pack("<IIII", now // 1_000_000_000, now % 1_000_000_000, len(frame), len(frame)) + frame)
    out.flush()
out.close()
