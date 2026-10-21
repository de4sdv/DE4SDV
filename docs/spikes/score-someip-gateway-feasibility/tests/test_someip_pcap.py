"""Local tests of the spike's capture reader (stdlib unittest; no network)."""

import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import someip_pcap  # noqa: E402

HOST, GUEST = bytes([10, 250, 0, 1]), bytes([10, 250, 0, 2])


def ip_packet(src, dst, proto, body):
    header = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(body), 0, 0, 64, proto, 0, src, dst)
    return b"\x00" * 12 + b"\x08\x00" + header + body


def tcp(src, dst, sport, dport, seq, flags, payload):
    body = struct.pack("!HHIIBBHHH", sport, dport, seq, 0, 5 << 4, flags, 65535, 0, 0) + payload
    return ip_packet(src, dst, 6, body)


def udp(src, dst, sport, dport, payload):
    return ip_packet(src, dst, 17, struct.pack("!HHHH", sport, dport, 8 + len(payload), 0) + payload)


def someip(service, method, msg_type, payload, session=1):
    return struct.pack("!HHIHHBBBB", service, method, 8 + len(payload), 0, session, 1, 1, msg_type, 0) + payload


def write_pcap(path, frames):
    with open(path, "wb") as out:
        out.write(struct.pack("<IHHiIII", 0xA1B23C4D, 2, 4, 0, 0, 262144, 1))
        for i, frame in enumerate(frames):
            out.write(struct.pack("<IIII", 1000 + i, 0, len(frame), len(frame)) + frame)


class CaptureReaderTest(unittest.TestCase):
    def test_tcp_stream_with_split_and_retransmitted_segments(self):
        a = someip(0x4DEE, 0x8001, 0x02, b"A" * 2048)
        b = someip(0x4DEE, 0x8001, 0x02, b"B" * 20, session=2)
        stream = a + b
        isn = 1000
        frames = [
            tcp(HOST, GUEST, 30509, 40000, isn - 1, 0x02, b""),  # SYN
            tcp(HOST, GUEST, 30509, 40000, isn, 0x18, stream[:1000]),
            tcp(HOST, GUEST, 30509, 40000, isn + 1000, 0x18, stream[1000:1500]),
            tcp(HOST, GUEST, 30509, 40000, isn + 1000, 0x18, stream[1000:1500]),  # retransmission
            tcp(HOST, GUEST, 30509, 40000, isn + 1500, 0x18, stream[1500:]),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.pcap"
            write_pcap(path, frames)
            result = someip_pcap.analyse(path)
        messages = [m for m in result["messages"] if m.transport == "tcp"]
        self.assertEqual([len(m.payload) for m in messages], [2048, 20])
        self.assertEqual(messages[0].payload, b"A" * 2048)
        self.assertEqual(result["streams"][0]["gaps"], [])
        self.assertEqual(result["streams"][0]["trailing_bytes"], 0)

    def test_gap_stops_reassembly(self):
        stream = someip(0x4DEE, 0x8001, 0x02, b"C" * 100)
        frames = [tcp(HOST, GUEST, 30509, 40000, 5000, 0x18, stream[:50]),
                  tcp(HOST, GUEST, 30509, 40000, 5070, 0x18, stream[70:])]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.pcap"
            write_pcap(path, frames)
            result = someip_pcap.analyse(path)
        self.assertEqual(result["streams"][0]["gaps"], [50])
        self.assertEqual([m for m in result["messages"] if m.transport == "tcp"], [])

    def test_sd_offer_and_stop_offer(self):
        def sd(ttl):
            entry = struct.pack("!BBBBHHB", 0x01, 0, 0, 0x10, 0x4DEE, 1, 1) + ttl.to_bytes(3, "big") + b"\x00" * 4
            body = struct.pack("!B3xI", 0xC0, len(entry)) + entry + struct.pack("!I", 0)
            return someip(0xFFFF, 0x8100, 0x02, body)
        frames = [udp(HOST, bytes([224, 244, 224, 245]), 30490, 30490, sd(3)),
                  udp(HOST, bytes([224, 244, 224, 245]), 30490, 30490, sd(0))]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.pcap"
            write_pcap(path, frames)
            result = someip_pcap.analyse(path)
        self.assertEqual([(e["type"], e["ttl"], e["stop"]) for e in result["sd"]],
                         [("OfferService", 3, False), ("OfferService", 0, True)])


if __name__ == "__main__":
    unittest.main()
