"""Runtime tests for the SOME/IP backbone service at the session boundary (R5).

Both roles run their real code against real loopback UDP sockets. The boundary is
reached by running the roles past it (65 535 sessions), not by seeding a counter,
so the tests hold whatever the service calls its counters. A 16-bit session id is
reached after about 1.8 h of provider events and 9.1 h of client calls at the
default periods; here it takes a second or two.

SOME/IP session handling: the session id is a 16-bit counter that starts at 1,
and wraps from 0xFFFF to 0x0001; 0x0000 means "no session handling" and is not
used by a role that counts sessions.

Run:  python -m pytest de4sdv-virtual-ee/checks/tests/test_runtime_someip.py
"""

from __future__ import annotations

import json
import socket
import struct
import sys
import time
from pathlib import Path

import pytest

SERVICE = Path(__file__).resolve().parents[2] / "service"
sys.path.insert(0, str(SERVICE))

import backbone_service  # noqa: E402
import someip  # noqa: E402

SESSION_LIMIT = 0xFFFF  # SOME/IP session id is 16 bits
PAST_THE_BOUNDARY = SESSION_LIMIT + 3


@pytest.fixture
def receiver():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
    sock.bind(("127.0.0.1", 0))
    sock.setblocking(False)
    yield sock
    sock.close()


def drain(sock: socket.socket, into: list) -> None:
    while True:
        try:
            datagram = sock.recv(2048)
        except BlockingIOError:
            return
        into.append(someip.decode(datagram))


def test_provider_publishes_past_the_session_limit_and_keeps_the_app_sequence(
    monkeypatch, receiver, capsys
):
    monkeypatch.setenv("SOMEIP_BIND", "127.0.0.1")
    monkeypatch.setenv("SOMEIP_PORT", "0")
    monkeypatch.setenv("SOMEIP_PEERS", f"127.0.0.1:{receiver.getsockname()[1]}")
    provider = backbone_service.Provider()
    received: list = []
    try:
        for n in range(PAST_THE_BOUNDARY):
            try:
                provider._publish()
            except someip.SomeIpError as exc:
                pytest.fail(f"provider crashed on event {n + 1}: {exc}")
            if n % 64 == 0:
                drain(receiver, received)
        drain(receiver, received)
    finally:
        provider.sock.close()
        capsys.readouterr()

    assert len(received) == PAST_THE_BOUNDARY
    sessions = [header.session_id for header, _ in received]
    seqs = [backbone_service.PAYLOAD.unpack(payload)[0] for _, payload in received]
    assert seqs == list(range(1, PAST_THE_BOUNDARY + 1)), "the app sequence must not wrap"
    assert sessions[:SESSION_LIMIT] == list(range(1, SESSION_LIMIT + 1))
    assert sessions[SESSION_LIMIT:] == [1, 2, 3], "the session id wraps to 1, never 0"


def make_client(monkeypatch, provider_sock: socket.socket, timeout_ms: int | None = None):
    monkeypatch.setenv("SOMEIP_BIND", "127.0.0.1")
    monkeypatch.setenv("SOMEIP_PORT", "0")
    monkeypatch.setenv("SOMEIP_PROVIDER", f"127.0.0.1:{provider_sock.getsockname()[1]}")
    if timeout_ms is not None:
        monkeypatch.setenv("SOMEIP_CALL_TIMEOUT_MS", str(timeout_ms))
    return backbone_service.Client()


def calls(client, provider_sock: socket.socket, n: int) -> list:
    """Make n calls; return the requests as the provider received them."""
    requests: list = []
    for i in range(n):
        try:
            client._call()
        except someip.SomeIpError as exc:
            pytest.fail(f"client crashed on call {i + 1}: {exc}")
        if i % 64 == 0:
            drain(provider_sock, requests)
    drain(provider_sock, requests)
    return requests


def test_client_calls_past_the_session_limit_and_keeps_the_call_number(
    monkeypatch, receiver, capsys
):
    client = make_client(monkeypatch, receiver)
    try:
        requests = calls(client, receiver, PAST_THE_BOUNDARY)
    finally:
        client.sock.close()
        capsys.readouterr()

    assert len(requests) == PAST_THE_BOUNDARY
    sessions = [header.session_id for header, _ in requests]
    numbers = [struct.unpack("!I", payload)[0] for _, payload in requests]
    assert numbers == list(range(1, PAST_THE_BOUNDARY + 1)), "the call number must not wrap"
    assert sessions[:SESSION_LIMIT] == list(range(1, SESSION_LIMIT + 1))
    assert sessions[SESSION_LIMIT:] == [1, 2, 3], "the session id wraps to 1, never 0"


def records(text: str) -> list[dict]:
    return [json.loads(line) for line in text.splitlines() if line.startswith("{")]


def reply(provider_sock: socket.socket, client, session: int) -> None:
    datagram = someip.response(client.service, client.method, 0x0001, session, b"\x00\x00\x00\x01")
    provider_sock.sendto(datagram, client.sock.getsockname())
    client.sock.settimeout(1.0)
    client._receive()


def test_unanswered_calls_expire_and_a_late_reply_is_not_an_answer(monkeypatch, receiver, capsys):
    client = make_client(monkeypatch, receiver, timeout_ms=50)
    try:
        calls(client, receiver, 3)
        time.sleep(0.1)  # all three are now older than the 50 ms timeout
        calls(client, receiver, 1)
        pending_after = len(client.pending)
        reply(receiver, client, 1)  # the provider answers call 1, too late
    finally:
        client.sock.close()
    log = records(capsys.readouterr().out)

    timeouts = [r for r in log if r["kind"] == "method_timeout"]
    assert [r["session"] for r in timeouts] == [1, 2, 3]
    assert pending_after == 1, "only the call still inside its timeout stays pending"
    assert not [r for r in log if r["kind"] == "method_rtt"], "a late reply is not an RTT"
    assert client.answered == 0


def test_reused_session_retires_the_old_call_and_the_reply_belongs_to_the_new_one(
    monkeypatch, receiver, capsys
):
    # A timeout far longer than the run: every call is still pending when its
    # session id comes round again, the case expiry alone cannot prevent.
    client = make_client(monkeypatch, receiver, timeout_ms=600_000)
    try:
        calls(client, receiver, SESSION_LIMIT + 1)  # call 65 536 reuses session 1
        pending_after = len(client.pending)
        reply(receiver, client, 1)
    finally:
        client.sock.close()
    log = records(capsys.readouterr().out)

    retired = [r for r in log if r["kind"] == "method_timeout"]
    assert [(r["session"], r["call"]) for r in retired] == [(1, 1)], "the old call 1 is retired, and says so"
    assert pending_after == SESSION_LIMIT, "one pending call per session id, never more"
    rtts = [r for r in log if r["kind"] == "method_rtt"]
    assert [(r["session"], r["call"]) for r in rtts] == [(1, SESSION_LIMIT + 1)]
