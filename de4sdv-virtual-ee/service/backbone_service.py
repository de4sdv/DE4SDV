#!/usr/bin/env python3
"""The backbone service endpoint — one role per container, chosen by env.

The provider serves one method and publishes one event. The client calls the
method on a period and subscribes to the event. Both write one JSON object per
line to stdout, which is what the measurement script reads; the container's log
is the measurement record.

Wire format is [`someip.py`](someip.py) — header and payload, nothing else.

Environment:

    SOMEIP_ROLE              provider | client (unset: the service does not run)
    SOMEIP_PORT              provider 30490, client 30510
    SOMEIP_PROVIDER          client only: host:port of the provider
    SOMEIP_PEERS             provider only: comma-separated host:port subscribers
    SOMEIP_PERIOD_MS         event period (default 100)
    SOMEIP_CALL_PERIOD_MS    client method period (default 500)
    SOMEIP_SERVICE_ID        default 0x1234
    SOMEIP_METHOD_ID         default 0x0001
    SOMEIP_EVENT_ID          default 0x8001
    SOMEIP_DEADLINE_MS       recorded with each event so the reader can judge it

The event payload carries the send timestamp as an application field
(`seq` + `t_send_ns`). It is not part of SOME/IP: a real service would carry
whatever its interface defines. It exists so one-way latency can be measured on
a single clock domain, and the report says so.
"""

from __future__ import annotations

import json
import os
import select
import signal
import socket
import struct
import sys
import time

import someip

PAYLOAD = struct.Struct("!IQ")  # seq, t_send_ns


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    return int(raw, 0) if raw else default


def log(**fields) -> None:
    fields.setdefault("t", time.time_ns())
    print(json.dumps(fields, separators=(",", ":")), flush=True)


def hostports(raw: str) -> list[tuple[str, int]]:
    out = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        host, _, port = item.rpartition(":")
        out.append((host or "127.0.0.1", int(port)))
    return out


class Provider:
    def __init__(self) -> None:
        self.service = env_int("SOMEIP_SERVICE_ID", 0x1234)
        self.method = env_int("SOMEIP_METHOD_ID", 0x0001)
        self.event = env_int("SOMEIP_EVENT_ID", 0x8001)
        self.period = env_int("SOMEIP_PERIOD_MS", 100) / 1000.0
        self.deadline_ms = env_int("SOMEIP_DEADLINE_MS", 50)
        self.port = env_int("SOMEIP_PORT", 30490)
        self.peers = hostports(os.environ.get("SOMEIP_PEERS", ""))
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((os.environ.get("SOMEIP_BIND", "0.0.0.0"), self.port))
        self.seq = 0
        self.stop = False
        self.served = 0
        self.bad = 0

    def run(self) -> int:
        log(kind="provider_up", port=self.port, peers=[f"{h}:{p}" for h, p in self.peers],
            period_ms=int(self.period * 1000), deadline_ms=self.deadline_ms)
        next_event = time.monotonic()
        while not self.stop:
            wait = max(0.0, next_event - time.monotonic())
            ready, _, _ = select.select([self.sock], [], [], min(wait, 0.05))
            if ready:
                self._serve()
            if time.monotonic() >= next_event:
                self._publish()
                next_event += self.period
                if next_event < time.monotonic():  # never let a stall queue a burst
                    next_event = time.monotonic() + self.period
        log(kind="provider_down", events=self.seq, served=self.served, malformed=self.bad)
        return 0

    def _serve(self) -> None:
        try:
            datagram, peer = self.sock.recvfrom(2048)
        except OSError:
            return
        try:
            header, payload = someip.decode(datagram)
        except someip.SomeIpError:
            self.bad += 1
            return
        if header.service_id != self.service or header.method_id != self.method:
            self.bad += 1
            return
        if header.message_type != someip.REQUEST:
            self.bad += 1
            return
        self.served += 1
        reply = someip.response(
            self.service, self.method, header.client_id, header.session_id,
            struct.pack("!I", self.served),
        )
        self.sock.sendto(reply, peer)
        log(kind="method_served", session=header.session_id, client=header.client_id)

    def _publish(self) -> None:
        self.seq += 1
        now = time.time_ns()
        payload = PAYLOAD.pack(self.seq, now)
        for host, port in self.peers:
            self.sock.sendto(
                someip.notification(self.service, self.event, 0, self.seq, payload),
                (host, port),
            )
        log(kind="event_sent", seq=self.seq, t_send_ns=now, peers=len(self.peers))


class Client:
    def __init__(self) -> None:
        self.service = env_int("SOMEIP_SERVICE_ID", 0x1234)
        self.method = env_int("SOMEIP_METHOD_ID", 0x0001)
        self.event = env_int("SOMEIP_EVENT_ID", 0x8001)
        self.call_period = env_int("SOMEIP_CALL_PERIOD_MS", 500) / 1000.0
        self.deadline_ms = env_int("SOMEIP_DEADLINE_MS", 50)
        self.port = env_int("SOMEIP_PORT", 30510)
        peers = hostports(os.environ.get("SOMEIP_PROVIDER", ""))
        if not peers:
            raise SystemExit("SOMEIP_PROVIDER is required for the client role")
        self.provider = peers[0]
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((os.environ.get("SOMEIP_BIND", "0.0.0.0"), self.port))
        self.session = 0
        self.answered = 0
        self.pending: dict[int, int] = {}
        self.stop = False

    def run(self) -> int:
        log(kind="client_up", port=self.port, provider=f"{self.provider[0]}:{self.provider[1]}",
            call_period_ms=int(self.call_period * 1000), deadline_ms=self.deadline_ms)
        next_call = time.monotonic()
        while not self.stop:
            wait = max(0.0, next_call - time.monotonic())
            ready, _, _ = select.select([self.sock], [], [], min(wait, 0.01))
            if ready:
                self._receive()
            if time.monotonic() >= next_call:
                self._call()
                next_call += self.call_period
                if next_call < time.monotonic():
                    next_call = time.monotonic() + self.call_period
        log(kind="client_down", calls=self.session, answered=self.answered)
        return 0

    def _call(self) -> None:
        self.session += 1
        self.pending[self.session] = time.time_ns()
        datagram = someip.request(
            self.service, self.method, 0x0001, self.session, struct.pack("!I", self.session)
        )
        self.sock.sendto(datagram, self.provider)

    def _receive(self) -> None:
        try:
            datagram, _peer = self.sock.recvfrom(2048)
        except OSError:
            return
        try:
            header, payload = someip.decode(datagram)
        except someip.SomeIpError:
            return
        if header.service_id != self.service:
            return
        if header.message_type == someip.RESPONSE and header.method_id == self.method:
            sent = self.pending.pop(header.session_id, None)
            if sent is not None:
                self.answered += 1
                log(kind="method_rtt", session=header.session_id, rtt_ns=time.time_ns() - sent)
        elif header.message_type == someip.NOTIFICATION and header.method_id == self.event:
            if len(payload) == PAYLOAD.size:
                seq, t_send = PAYLOAD.unpack(payload)
                log(kind="event_recv", seq=seq, t_send_ns=t_send, t_recv_ns=time.time_ns())


def main() -> int:
    role = os.environ.get("SOMEIP_ROLE", "").strip().lower()
    if not role:
        print("SOMEIP_ROLE is unset; nothing to run", file=sys.stderr)
        return 0
    if role not in {"provider", "client"}:
        print(f"unknown SOMEIP_ROLE {role!r}", file=sys.stderr)
        return 2
    service = Provider() if role == "provider" else Client()

    def stop(_signum, _frame):
        service.stop = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    return service.run()


if __name__ == "__main__":
    sys.exit(main())
