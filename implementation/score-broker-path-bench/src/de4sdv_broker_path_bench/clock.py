"""The offset between the Linux host clock and the IVI VM clock (ASM-MW-030).

Method: a two-way NTP exchange between the IVI VM and the chrony of the host.
The IVI VM captures the exchange with tcpdump, on its own clock. So the four
times come from raw artifacts, not from the output of a client:

- t1: the guest capture time of the request (IVI VM clock);
- t2, t3: the receive and transmit timestamps that chrony writes into the
  response (host clock);
- t4: the guest capture time of the response (IVI VM clock).

offset = guest - host = ((t1 - t2) + (t4 - t3)) / 2, and the uncertainty is
half of the round trip, ((t4 - t1) - (t3 - t2)) / 2: each one-way delay lies
between 0 and the round trip. The request carries a marker in its transmit
timestamp, and chrony copies it into the originate timestamp of its
response, so request and response pair without doubt.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from .pcap import Capture, datagrams

NTP_PORT = 123
#: Seconds between the NTP era 0 epoch (1900) and the Unix epoch.
_NTP_TO_UNIX_S = 2_208_988_800
#: The bound of ASM-MW-030: less than 20 ms.
CLOCK_BOUND_NS = 20_000_000


def ntp_to_unix_ns(raw: bytes) -> int:
    seconds, fraction = struct.unpack(">II", raw)
    return (seconds - _NTP_TO_UNIX_S) * 1_000_000_000 + (fraction * 1_000_000_000 >> 32)


@dataclass(frozen=True)
class NtpExchange:
    marker: bytes
    t1_ns: int
    t2_ns: int
    t3_ns: int
    t4_ns: int

    @property
    def offset_ns(self) -> float:
        return ((self.t1_ns - self.t2_ns) + (self.t4_ns - self.t3_ns)) / 2

    @property
    def round_trip_ns(self) -> int:
        return (self.t4_ns - self.t1_ns) - (self.t3_ns - self.t2_ns)

    @property
    def uncertainty_ns(self) -> float:
        return self.round_trip_ns / 2


def exchanges(capture: Capture, server: str | None = None) -> tuple[list[NtpExchange], list[str]]:
    """The complete exchanges of a guest capture, and the problems found."""
    problems: list[str] = []
    requests: dict[bytes, int] = {}
    found: list[NtpExchange] = []
    for item in datagrams(capture):
        if item.protocol != "udp" or len(item.payload) < 48:
            continue
        mode = item.payload[0] & 0x07
        if mode == 3 and item.dport == NTP_PORT and (server is None or item.dst == server):
            marker = item.payload[40:48]
            if marker in requests:
                problems.append(f"request marker {marker.hex()} sent twice")
            requests[marker] = item.ts_ns
        elif mode == 4 and item.sport == NTP_PORT and (server is None or item.src == server):
            marker = item.payload[24:32]
            t1 = requests.pop(marker, None)
            if t1 is None:
                problems.append(f"response without its request (originate {marker.hex()})")
                continue
            exchange = NtpExchange(marker, t1, ntp_to_unix_ns(item.payload[32:40]),
                                   ntp_to_unix_ns(item.payload[40:48]), item.ts_ns)
            if exchange.round_trip_ns < 0 or exchange.t3_ns < exchange.t2_ns:
                problems.append(f"exchange {marker.hex()} has impossible times")
                continue
            found.append(exchange)
    for marker in requests:
        problems.append(f"request {marker.hex()} got no response")
    return found, problems


@dataclass(frozen=True)
class OffsetMeasurement:
    """The best exchange of a measurement: the one with the smallest round trip."""

    offset_ns: float
    uncertainty_ns: float
    exchanges: int
    measured_at_ns: int  # guest capture time of the best exchange's response

    @property
    def bound_term_ns(self) -> float:
        """The size of the offset plus its uncertainty, which ASM-MW-030 bounds."""
        return abs(self.offset_ns) + self.uncertainty_ns

    def holds(self, bound_ns: int = CLOCK_BOUND_NS) -> bool:
        return self.bound_term_ns < bound_ns

    def as_dict(self) -> dict[str, float | int | bool]:
        return {"offset_ns": self.offset_ns, "uncertainty_ns": self.uncertainty_ns, "exchanges": self.exchanges,
                "measured_at_ns": self.measured_at_ns, "bound_term_ns": self.bound_term_ns,
                "holds_20ms_bound": self.holds()}


def best(found: list[NtpExchange]) -> OffsetMeasurement | None:
    if not found:
        return None
    winner = min(found, key=lambda exchange: (exchange.round_trip_ns, exchange.t4_ns))
    return OffsetMeasurement(winner.offset_ns, winner.uncertainty_ns, len(found), winner.t4_ns)


def drift_ppm(first: OffsetMeasurement, second: OffsetMeasurement) -> float:
    """The rate at which the offset changes, in parts per million of elapsed time."""
    elapsed = second.measured_at_ns - first.measured_at_ns
    if elapsed <= 0:
        raise ValueError("the second measurement must come after the first")
    return (second.offset_ns - first.offset_ns) / elapsed * 1_000_000


def session_seconds(after_setting: OffsetMeasurement, drift: float, bound_ns: int = CLOCK_BOUND_NS,
                    reserve_ns: int = 2_000_000) -> float:
    """How long a session may last after a clock setting before the bound is at risk.

    The offset grows by ``drift`` ppm; ``reserve_ns`` is kept back for the
    uncertainty of the end measurement. Without drift there is no limit from
    this side.
    """
    room = bound_ns - after_setting.bound_term_ns - reserve_ns
    if room <= 0:
        return 0.0
    if drift == 0:
        return float("inf")
    return room / (abs(drift) * 1_000)  # ns of room / (ns of drift per second)

# The bench sets and slews the IVI VM clock with a standard SNTP client
# (toybox sntp, or ntpd), not with any DE4SDV code. This module only reads the
# exchange that the guest captured, so it never builds a request packet.
