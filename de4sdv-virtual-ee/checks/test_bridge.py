#!/usr/bin/env python3
"""Framing tests for the DE4SDV CAN-over-UDP bridge.

The socket loops cannot be unit-tested without an interface; the framing is where
a malformed datagram could corrupt a bus, so that is what is pinned here.

Run:  python de4sdv-virtual-ee/checks/test_bridge.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "transport"))

from bridge import (  # noqa: E402
    CAN_EFF_FLAG,
    HEADER,
    FramingError,
    decode_frame,
    encode_frame,
)

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"PASS  {name}")
    else:
        failures.append(f"{name} {detail}".strip())
        print(f"FAIL  {name} {detail}")


def expect_error(name: str, fn, *args) -> None:
    try:
        fn(*args)
    except FramingError:
        print(f"PASS  {name}")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"{name}: wrong exception {type(exc).__name__}")
        print(f"FAIL  {name}: wrong exception {type(exc).__name__}: {exc}")
    else:
        failures.append(f"{name}: accepted an invalid frame")
        print(f"FAIL  {name}: accepted an invalid frame")


def main() -> int:
    check("framing is fixed size", HEADER.size == 17, f"got {HEADER.size}")

    payload = bytes([0x02, 0x10, 0x03, 0, 0, 0, 0, 0])
    wire = encode_frame(0x7E0, payload)
    check("standard frame round-trips", decode_frame(wire) == (0x7E0, payload, False))

    extended = encode_frame(0x18DAF110, bytes([0x50, 0x03]), extended=True)
    check(
        "extended frame round-trips and keeps its flag",
        decode_frame(extended) == (0x18DAF110, bytes([0x50, 0x03]), True),
    )

    check("dlc 0 is legal", decode_frame(encode_frame(0x100, b""))[1] == b"")

    # a short payload must not leak padding into the bus
    check(
        "padding is stripped by dlc",
        decode_frame(encode_frame(0x100, b"\xaa"))[1] == b"\xaa",
    )

    expect_error("rejects oversize dlc", encode_frame, 0x100, b"\x00" * 9)
    expect_error("rejects out-of-range id", encode_frame, 0x20000000, b"\x00")
    expect_error("rejects a short datagram", decode_frame, b"D4E1\x00")
    expect_error("rejects a foreign datagram", decode_frame, b"XXXX" + bytes(13))

    # the extended flag must not leak into the id the caller sees
    wire_id = int.from_bytes(extended[4:8], "big")
    check("extended flag sits in bit 31", wire_id & CAN_EFF_FLAG != 0)

    if failures:
        print(f"\nFAILED ({len(failures)})")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nPASS  framing behaves as specified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
