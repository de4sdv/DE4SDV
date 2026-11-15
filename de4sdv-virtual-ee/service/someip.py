"""A minimal SOME/IP codec — the subset this testbed needs, and no more.

SOME/IP is the service protocol a zonal E/E spine carries: 16-byte header, then
the payload. This module implements the wire format and nothing else, so that
the backbone increment measures a service plane rather than an integration.

What is implemented:

    Message ID    service id (2) + method/event id (2)
    Length        bytes after this field: 8 + payload length
    Request ID    client id (2) + session id (2)
    Version       protocol 1, interface version supplied by the caller
    Message type  REQUEST, REQUEST_NO_RETURN, NOTIFICATION, RESPONSE, ERROR
    Return code   0x00 OK, plus a parser that preserves anything else

What is deliberately not implemented: service discovery (SOME/IP-SD), TCP
transport, E2E protection, segmentation for payloads over the UDP MTU, and
session handling. Endpoints are static, which is the trade the increment's scope
records.

The small codec keeps the experiment's supported wire fields inspectable. It is
not a full middleware stack, and its source licence says nothing about the
licences of other components included in a container image.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

HEADER = struct.Struct("!HHIHHBBBB")
HEADER_LEN = HEADER.size  # 16
PROTOCOL_VERSION = 0x01

REQUEST = 0x00
REQUEST_NO_RETURN = 0x01
NOTIFICATION = 0x02
RESPONSE = 0x80
ERROR = 0x81

RETURN_OK = 0x00

TYPES = {
    REQUEST: "REQUEST",
    REQUEST_NO_RETURN: "REQUEST_NO_RETURN",
    NOTIFICATION: "NOTIFICATION",
    RESPONSE: "RESPONSE",
    ERROR: "ERROR",
}


class SomeIpError(ValueError):
    """A datagram that is not valid for this subset."""


@dataclass(frozen=True)
class Header:
    service_id: int
    method_id: int
    length: int
    client_id: int
    session_id: int
    protocol_version: int
    interface_version: int
    message_type: int
    return_code: int

    @property
    def message_id(self) -> int:
        return (self.service_id << 16) | self.method_id


def encode(
    service_id: int,
    method_id: int,
    client_id: int,
    session_id: int,
    message_type: int,
    payload: bytes = b"",
    interface_version: int = 0x01,
    return_code: int = RETURN_OK,
) -> bytes:
    """Build one datagram. The length field counts from the request id."""
    if message_type not in TYPES:
        raise SomeIpError(f"unknown message type 0x{message_type:02x}")
    for name, value, limit in (
        ("service_id", service_id, 0xFFFF),
        ("method_id", method_id, 0xFFFF),
        ("client_id", client_id, 0xFFFF),
        ("session_id", session_id, 0xFFFF),
    ):
        if not 0 <= value <= limit:
            raise SomeIpError(f"{name} {value} does not fit in 16 bits")
    length = 8 + len(payload)
    return HEADER.pack(
        service_id,
        method_id,
        length,
        client_id,
        session_id,
        PROTOCOL_VERSION,
        interface_version,
        message_type,
        return_code,
    ) + payload


def decode(datagram: bytes) -> tuple[Header, bytes]:
    """Parse one datagram, refusing anything this subset cannot represent."""
    if len(datagram) < HEADER_LEN:
        raise SomeIpError(f"short datagram: {len(datagram)} bytes")
    fields = HEADER.unpack_from(datagram)
    header = Header(*fields)
    if header.protocol_version != PROTOCOL_VERSION:
        raise SomeIpError(f"unsupported protocol version {header.protocol_version}")
    if header.message_type not in TYPES:
        raise SomeIpError(f"unknown message type 0x{header.message_type:02x}")
    # The length field is authoritative: a datagram that disagrees with it is a
    # truncated or padded message, and guessing which would corrupt a measurement.
    expected = HEADER_LEN + header.length - 8
    if header.length < 8 or expected != len(datagram):
        raise SomeIpError(f"length {header.length} disagrees with {len(datagram)} bytes")
    return header, datagram[HEADER_LEN:]


def request(service: int, method: int, client: int, session: int, payload: bytes = b"") -> bytes:
    return encode(service, method, client, session, REQUEST, payload)


def response(service: int, method: int, client: int, session: int, payload: bytes = b"") -> bytes:
    return encode(service, method, client, session, RESPONSE, payload)


def notification(service: int, event: int, client: int, session: int, payload: bytes = b"") -> bytes:
    return encode(service, event, client, session, NOTIFICATION, payload)


def error(service: int, method: int, client: int, session: int, code: int = 0x01) -> bytes:
    return encode(service, method, client, session, ERROR, b"", return_code=code)


def describe(datagram: bytes) -> str:
    """One line for a log or a capture read-back."""
    header, payload = decode(datagram)
    return (
        f"{TYPES[header.message_type]} service=0x{header.service_id:04x} "
        f"method=0x{header.method_id:04x} client=0x{header.client_id:04x} "
        f"session={header.session_id} len={len(payload)}"
    )
