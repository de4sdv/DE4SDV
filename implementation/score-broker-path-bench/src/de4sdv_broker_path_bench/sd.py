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

import re
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
    src_port: int    # the UDP source port of the SD datagram (review R43: a stack ignores an offer not from 30490)
    dst_port: int
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
            found.append(SdEntry(item.ts_ns, item.src, item.dst, item.sport, item.dport, entry["kind"],
                                 entry["service"], entry["instance"], entry["major"], entry["ttl"],
                                 entry["eventgroup"], entry["endpoints"]))
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
    result = {"offer_time_ns": None, "offer_src": None, "offer_src_port": None, "offer_endpoints": [],
              "providers_after": [], "subscribes_after": 0,
              "host_offers": sum(1 for e in entries if e.kind == "offer" and e.src == host and e.service == service)}
    if offer is None:
        return result
    after = [e for e in entries if e.kind == "subscribe" and e.service == service and e.instance == instance
             and e.ttl > 0 and e.src == core and e.ts_ns > offer.ts_ns]
    result.update(offer_time_ns=offer.ts_ns, offer_src=offer.src, offer_src_port=offer.src_port,
                  offer_endpoints=offer.endpoints,
                  providers_after=sorted({e.dst for e in after}), subscribes_after=len(after))
    return result


# ------------------------------------------------------------ R43: the core stack's own record of the offer
#
# A SOME/IP stack drops an SD message from a source port other than the SD port
# before its SD module reads it, so an offer that is ignored there shows
# nothing about the no-redirect property (review R43). The SDV Core VM's logcat
# says which happened. The default lines are vsomeip 3.1.37.1's, from the
# COVESA 3.1.37.1 tag:
# - service_discovery_impl.cpp, process_offerservice_serviceentry: a secure
#   service whose offered port is not a secure port gives
#   "process_offerservice_serviceentry: Ignoring offer of [4dee.0001]"; an
#   offer the acceptance handler refuses gives "Do not accept offer from
#   <addr>:<port> reliable=<r>". Either line means the SD module read the
#   offer and refused it: the stack processed the offer.
# - routing_manager_impl.cpp, on_message: "Ignored SD message from unknown port
#   (<port>)" or "Ignored SD message from unknown address." means the message
#   never reached the SD module: the stack ignored it.
# The 3.1.37.1 service discovery logs no line of its own when it accepts an
# offer, so an accepted offer gives "unknown" here (a redirect then shows in
# the SD capture, which fails the case). The image's copy
# may carry other lines or another log level; S1 confirms them on the live
# SDV Core VM, and the patterns are settings (send_sd_offer.sh).

#: (name, regex) of the lines that show the SD module processed the offer.
#: ``{service}``, ``{instance}`` and ``{provider}`` are filled in.
DEFAULT_PROCESSED_PATTERNS = (
    ("secure_service_rejected", r"Ignoring offer of \[{service}\.{instance}\]"),
    ("acceptance_rejected", r"Do not accept offer from {provider}:\d+"),
)
#: (name, regex) of the lines that show the message was dropped before the SD module.
DEFAULT_IGNORED_PATTERNS = (
    ("unknown_port", r"Ignored SD message from unknown port \(\d+\)"),
    ("unknown_address", r"Ignored SD message from unknown address"),
)
PATTERN_SOURCE = ("vsomeip 3.1.37.1 (COVESA tag: service_discovery_impl.cpp, routing_manager_impl.cpp); "
                  "S1 confirms the image's lines")

_EPOCH = re.compile(r"^\s*(\d+(?:\.\d+)?)\s")


def _fill(pattern: str, service: int, instance: int, provider: str | None) -> re.Pattern:
    return re.compile(pattern.format(service=f"{service:04x}", instance=f"{instance:04x}",
                                     provider=re.escape(provider) if provider else r"\S+"))


def core_offer_record(logcat_text: str, *, since_epoch_s: float, provider: str | None = None,
                      service: int = FRAME_SERVICE, instance: int = FRAME_INSTANCE,
                      processed_patterns=None, ignored_patterns=None) -> dict:
    """sd_core_processed.json: whether the SDV Core VM's stack processed or ignored the spoofed offer.

    ``logcat_text`` is the core's logcat with ``-v epoch`` timestamps, taken
    around the offer; only lines at or after ``since_epoch_s`` (the core clock
    just before the send) count. A line that names the frame service (a
    processed pattern) takes precedence over an "ignored" line, which names no
    service and can come from another sender. No matching line gives status
    "unknown" (processed None), which keeps VC-MW-016 inconclusive.
    """
    processed_patterns = list(DEFAULT_PROCESSED_PATTERNS if processed_patterns is None else processed_patterns)
    ignored_patterns = list(DEFAULT_IGNORED_PATTERNS if ignored_patterns is None else ignored_patterns)
    compiled_processed = [(name, _fill(rx, service, instance, provider)) for name, rx in processed_patterns]
    compiled_ignored = [(name, _fill(rx, service, instance, provider)) for name, rx in ignored_patterns]
    processed_hits, ignored_hits, in_window = [], [], 0
    for line in logcat_text.splitlines():
        match = _EPOCH.match(line)
        if match is None or float(match.group(1)) < since_epoch_s:
            continue
        in_window += 1
        for name, regex in compiled_processed:
            if regex.search(line):
                processed_hits.append((name, line.strip()))
                break
        else:
            for name, regex in compiled_ignored:
                if regex.search(line):
                    ignored_hits.append((name, line.strip()))
                    break
    record = {"processed": None, "status": "unknown", "result": "no_matching_line", "matched_line": None,
              "also_seen": [], "since_epoch_s": since_epoch_s, "lines_in_window": in_window,
              "service": f"{service:04x}.{instance:04x}", "provider": provider,
              "patterns": {"processed": [list(item) for item in processed_patterns],
                           "ignored": [list(item) for item in ignored_patterns]},
              "pattern_source": PATTERN_SOURCE if processed_patterns == list(DEFAULT_PROCESSED_PATTERNS)
              and ignored_patterns == list(DEFAULT_IGNORED_PATTERNS) else "settings (S1 confirms the image's lines)"}
    if processed_hits:
        name, line = processed_hits[0]
        record.update(processed=True, status="processed", result=name, matched_line=line)
        record["also_seen"] = [hit[1] for hit in processed_hits[1:] + ignored_hits]
    elif ignored_hits:
        name, line = ignored_hits[0]
        record.update(processed=False, status="ignored", result=name, matched_line=line)
        record["also_seen"] = [hit[1] for hit in ignored_hits[1:]]
    return record
