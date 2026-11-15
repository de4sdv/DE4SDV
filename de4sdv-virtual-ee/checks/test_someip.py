#!/usr/bin/env python3
"""Tests for the SOME/IP subset — the wire format is the contract.

Run: python3 checks/test_someip.py
"""

from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "service"))

import someip  # noqa: E402


class HeaderTests(unittest.TestCase):
    def test_request_roundtrip(self):
        payload = struct.pack("!I", 7)
        datagram = someip.request(0x1234, 0x0001, 0x0002, 7, payload)
        header, decoded = someip.decode(datagram)
        self.assertEqual(header.service_id, 0x1234)
        self.assertEqual(header.method_id, 0x0001)
        self.assertEqual(header.client_id, 0x0002)
        self.assertEqual(header.session_id, 7)
        self.assertEqual(header.message_type, someip.REQUEST)
        self.assertEqual(header.protocol_version, someip.PROTOCOL_VERSION)
        self.assertEqual(decoded, payload)

    def test_message_id_is_service_and_method(self):
        header, _ = someip.decode(someip.request(0x1234, 0x8001, 1, 1))
        self.assertEqual(header.message_id, 0x12348001)

    def test_length_counts_from_request_id(self):
        for size in (0, 1, 4, 12, 100):
            datagram = someip.request(1, 2, 3, 4, b"\x00" * size)
            header, _ = someip.decode(datagram)
            self.assertEqual(header.length, 8 + size)
            self.assertEqual(len(datagram), 16 + size)

    def test_header_is_sixteen_bytes(self):
        self.assertEqual(someip.HEADER_LEN, 16)
        self.assertEqual(len(someip.request(0, 0, 0, 0)), 16)

    def test_response_and_notification_types(self):
        self.assertEqual(someip.decode(someip.response(1, 2, 3, 4))[0].message_type, someip.RESPONSE)
        self.assertEqual(someip.decode(someip.notification(1, 2, 3, 4))[0].message_type, someip.NOTIFICATION)
        self.assertEqual(someip.decode(someip.error(1, 2, 3, 4))[0].message_type, someip.ERROR)

    def test_error_carries_return_code(self):
        header, _ = someip.decode(someip.error(1, 2, 3, 4, code=0x22))
        self.assertEqual(header.return_code, 0x22)


class RefusalTests(unittest.TestCase):
    def test_short_datagram(self):
        with self.assertRaises(someip.SomeIpError):
            someip.decode(b"\x00" * 15)

    def test_wrong_protocol_version(self):
        datagram = bytearray(someip.request(1, 2, 3, 4))
        datagram[12] = 0x02
        with self.assertRaises(someip.SomeIpError):
            someip.decode(bytes(datagram))

    def test_unknown_message_type(self):
        datagram = bytearray(someip.request(1, 2, 3, 4))
        datagram[14] = 0x7F
        with self.assertRaises(someip.SomeIpError):
            someip.decode(bytes(datagram))

    def test_length_disagrees_with_datagram(self):
        datagram = bytearray(someip.request(1, 2, 3, 4, b"\x00" * 4))
        struct.pack_into("!I", datagram, 4, 8 + 4 + 1)  # claim one byte more than present
        with self.assertRaises(someip.SomeIpError):
            someip.decode(bytes(datagram))

    def test_length_below_minimum(self):
        datagram = bytearray(someip.request(1, 2, 3, 4))
        struct.pack_into("!I", datagram, 4, 7)
        with self.assertRaises(someip.SomeIpError):
            someip.decode(bytes(datagram))

    def test_field_wider_than_16_bits(self):
        with self.assertRaises(someip.SomeIpError):
            someip.request(0x10000, 0, 0, 0)
        with self.assertRaises(someip.SomeIpError):
            someip.request(0, 0, 0, -1)

    def test_unknown_type_on_encode(self):
        with self.assertRaises(someip.SomeIpError):
            someip.encode(1, 2, 3, 4, 0x55)


class DescribeTests(unittest.TestCase):
    def test_describe_reads_back(self):
        text = someip.describe(someip.request(0x1234, 0x0001, 0x0002, 9, b"abcd"))
        self.assertIn("REQUEST", text)
        self.assertIn("service=0x1234", text)
        self.assertIn("session=9", text)
        self.assertIn("len=4", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
