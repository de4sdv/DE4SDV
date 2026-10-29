"""SOME/IP service discovery in a host capture (VC-MW-016: the spoofed offer).

The bench captures UDP 30490 on the host bridge (host-cvd-ebr.pcap). The
capture is promiscuous, so it also holds the unicast SD messages that the
bridge forwards between the two VMs. This module reads the SD entries of
that capture and answers two questions of #448 VC-MW-016: when did a sender
other than the host offer the frame service (the spoofed offer from the IVI
VM), and to which provider does the SDV Core VM's stack subscribe after it.
In SOME/IP-SD a subscriber sends its SubscribeEventgroup to the SD endpoint
of the provider it chose, so the destination of that message names the
provider.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

from .pcap import Capture, datagrams

SD_PORT = 30490
SD_SERVICE, SD_METHOD = 0xFFFF, 0x8100
#: The frame service of the HMI path (the overlay's stack configuration and mapping).
FRAME_SERVICE, FRAME_INSTANCE, FRAME_EVENTGROUP = 0x4DEE, 0x0001, 0x0001
HOST_ADDR, CORE_ADDR = "192.168.98.1", "192.168.98.3"

_KINDS = {0x00: "find", 0x01: "offer", 0x06: "subscribe", 0x07: "subscribe_ack"}
_PROTOCOLS = {0x06: "tcp", 0x11: "udp"}


@dataclass(frozen=True)
class SdEntry:
    ts_ns: int
    src: str
    dst: str
    kind: str
    service: int
    instance: int
    major: int
    ttl: int
    eventgroup: int | None
    endpoints: list = field(default_factory=list)  # (address, protocol, port) of the entry's options


def _options(raw: bytes) -> list[tuple[int, bytes]]:
    found, index = [], 0
    while index + 3 <= len(raw):
        length, kind = struct.unpack(">HB", raw[index:index + 3])
        body = raw[index + 3:index + 3 + length]
        if len(body) != length:
            break
        found.append((kind, body))
        index += 3 + length
    return found


def _endpoint(kind: int, body: bytes) -> tuple[str, str, int] | None:
    if kind != 0x04 or len(body) != 9:  # IPv4 Endpoint: reserved, address, reserved, protocol, port
        return None
    address = ".".join(str(byte) for byte in body[1:5])
    return address, _PROTOCOLS.get(body[6], str(body[6])), struct.unpack(">H", body[7:9])[0]


def parse_sd(payload: bytes) -> list[dict] | None:
    """The entries of one SOME/IP-SD message, or None when the bytes are not one."""
    if len(payload) < 16 + 12:
        return None
    service, method, length = struct.unpack(">HHI", payload[:8])
    if (service, method) != (SD_SERVICE, SD_METHOD) or length < 8 + 12 or 8 + length > len(payload):
        return None
    body = payload[16:8 + length]
    entries_length = struct.unpack(">I", body[4:8])[0]
    if 8 + entries_length + 4 > len(body) or entries_length % 16:
        return None
    entries_raw = body[8:8 + entries_length]
    options_length = struct.unpack(">I", body[8 + entries_length:12 + entries_length])[0]
    options_raw = body[12 + entries_length:12 + entries_length + options_length]
    if len(options_raw) != options_length:
        return None
    options = _options(options_raw)
    entries = []
    for offset in range(0, entries_length, 16):
        raw = entries_raw[offset:offset + 16]
        kind, first, second, counts, svc, inst, major = struct.unpack(">BBBBHHB", raw[:9])
        ttl = int.from_bytes(raw[9:12], "big")
        eventgroup = struct.unpack(">H", raw[14:16])[0] if kind in (0x06, 0x07) else None
        endpoints = []
        for start, count in ((first, counts >> 4), (second, counts & 0x0F)):
            for option in options[start:start + count]:
                endpoint = _endpoint(*option)
                if endpoint:
                    endpoints.append(endpoint)
        entries.append({"kind": _KINDS.get(kind, f"type_{kind:#x}"), "service": svc, "instance": inst,
                        "major": major, "ttl": ttl, "eventgroup": eventgroup, "endpoints": endpoints})
    return entries


def sd_entries(capture: Capture) -> list[SdEntry]:
    """Every SD entry of a capture, in capture order."""
    found = []
    for item in datagrams(capture):
        if item.protocol != "udp" or SD_PORT not in (item.sport, item.dport):
            continue
        entries = parse_sd(item.payload)
        for entry in entries or ():
            found.append(SdEntry(item.ts_ns, item.src, item.dst, entry["kind"], entry["service"], entry["instance"],
                                 entry["major"], entry["ttl"], entry["eventgroup"], entry["endpoints"]))
    return found


def offer_and_provider(entries: list[SdEntry], *, service: int = FRAME_SERVICE, instance: int = FRAME_INSTANCE,
                       host: str = HOST_ADDR, core: str = CORE_ADDR) -> dict:
    """The first offer of the frame service from a sender other than the host, and the providers after it.

    ``providers_after`` lists the destinations of the SDV Core VM's
    SubscribeEventgroup entries of the frame service (TTL above 0) after that
    offer. ``offer_time_ns`` is None when the capture holds no such offer.
    """
    offer = next((e for e in entries if e.kind == "offer" and e.service == service and e.instance == instance
                  and e.ttl > 0 and e.src != host), None)
    result = {"offer_time_ns": None, "offer_src": None, "offer_endpoints": [], "providers_after": [],
              "subscribes_after": 0, "host_offers": sum(1 for e in entries if e.kind == "offer" and e.src == host
                                                         and e.service == service)}
    if offer is None:
        return result
    after = [e for e in entries if e.kind == "subscribe" and e.service == service and e.instance == instance
             and e.ttl > 0 and e.src == core and e.ts_ns > offer.ts_ns]
    result.update(offer_time_ns=offer.ts_ns, offer_src=offer.src, offer_endpoints=offer.endpoints,
                  providers_after=sorted({e.dst for e in after}), subscribes_after=len(after))
    return result
