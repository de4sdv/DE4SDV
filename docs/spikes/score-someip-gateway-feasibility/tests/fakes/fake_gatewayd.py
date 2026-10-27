#!/usr/bin/env python3
"""Stand-in for gatewayd in the local dry run of the tooling only: relays UDP 40000 -> 40001.

With an mw::com binding manifest (*_mwcom.json, PR #375) it first sends its configuration
(a CONFIG datagram) to the fake someipd and logs the mw::com connection line."""

import signal
import socket
import sys
import time

STOP = False


def on_signal(*_):
    global STOP
    STOP = True


signal.signal(signal.SIGTERM, on_signal)
signal.signal(signal.SIGINT, on_signal)
tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
if any(arg.endswith("_mwcom.json") for arg in sys.argv[1:]):
    tx.sendto(b"CONFIG", ("127.0.0.1", 40001))
    print("[gatewayd] Connected to someipd over the mw::com IPC binding", flush=True)
else:
    print("[gatewayd] IPC connection to someipd established", flush=True)
time.sleep(0.3)
print("[gatewayd] LocalServiceInstance created for instance specifier: de4sdv/aebs_signal_frame", flush=True)
rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
rx.bind(("127.0.0.1", 40000))
rx.settimeout(0.1)
while not STOP:
    try:
        data = rx.recv(65535)
    except socket.timeout:
        continue
    tx.sendto(data, ("127.0.0.1", 40001))
print("Shutting down gateway...", flush=True)
sys.exit(0)
