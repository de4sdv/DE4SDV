"""Golden bytes: the S-CORE side's encoder against the guest's SOME/IP type definition.

A tiny C++ program, compiled against interfaces/include/de4sdv/driver_assistance/payloads.h,
prints EncodeWarningRequestSomeip for several vectors: these are the bytes the candidate puts into
its mw::com event and gatewayd copies unread onto SOME/IP. The guest's broker reads them by
interop/someip_type_definition.textproto. This test decodes them by that file
(scripts/decode_warning_payload.py) and requires the expected field values: big-endian, no length
field, no 4-byte prefix, nothing left over.

The expected values are computed here independently of payloads.h: the milliseconds with Python's
decimal module from the decimal text of the issue time (each vector is a whole number of
milliseconds, so no rounding rule is involved), the bytes with struct.pack(">II", ...).
"""

from __future__ import annotations

import importlib.util
import shutil
import struct
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
INCLUDE = ROOT.parent / "interfaces" / "include"
TYPE_DEFINITION = ROOT / "interop" / "someip_type_definition.textproto"
DECODER = ROOT / "scripts" / "decode_warning_payload.py"

# (requested, issue time as the decimal text the C++ program parses with strtod)
VECTORS = [
    (True, "12.35"),
    (False, "0.05"),
    (True, "0"),
    (False, "3600.5"),
    (True, "86399.95"),
    (True, "4294967.295"),  # the largest issue time that fits: 0xFFFFFFFF ms
]


def _decoder():
    spec = importlib.util.spec_from_file_location("decode_warning_payload", DECODER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look the module up by name
    spec.loader.exec_module(module)
    return module


def _expected(requested: bool, text: str) -> tuple[dict[str, int], bytes]:
    ms = Decimal(text) * 1000
    assert ms == ms.to_integral_value(), f"{text} s is not a whole number of milliseconds"
    values = {"requested": int(requested), "issue_time_sim_ms": int(ms)}
    return values, struct.pack(">II", values["requested"], values["issue_time_sim_ms"])


@pytest.fixture(scope="module")
def encoded(tmp_path_factory) -> list[bytes]:
    compiler = shutil.which("g++")
    if compiler is None:
        pytest.skip("g++ is not installed")
    binary = tmp_path_factory.mktemp("golden") / "golden_warning_bytes"
    subprocess.run(
        [compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-pedantic", f"-I{INCLUDE}",
         str(HERE / "golden_warning_bytes.cpp"), "-o", str(binary)],
        check=True,
    )
    args = [arg for requested, text in VECTORS for arg in ("1" if requested else "0", text)]
    result = subprocess.run([str(binary), *args], capture_output=True, text=True, check=True)
    lines = result.stdout.split()
    assert len(lines) == len(VECTORS), result.stdout
    return [bytes.fromhex(line) for line in lines]


def test_encoder_writes_the_independently_computed_bytes(encoded: list[bytes]) -> None:
    for (requested, text), wire in zip(VECTORS, encoded):
        _, expected = _expected(requested, text)
        assert wire == expected, f"{requested}, {text}: {wire.hex()} != {expected.hex()}"
    # One vector spelled out: requested 1, 12350 ms = 0x303E.
    assert encoded[0] == bytes.fromhex("000000010000303e")


def test_guest_type_definition_decodes_the_encoder_output(encoded: list[bytes]) -> None:
    decoder = _decoder()
    definition = decoder.load_type_definition(TYPE_DEFINITION)
    assert definition.length_field_size == "ZERO"
    for (requested, text), wire in zip(VECTORS, encoded):
        values, _ = _expected(requested, text)
        assert decoder.decode(wire, definition) == values


def test_guest_type_definition_rejects_a_prefixed_payload(encoded: list[bytes]) -> None:
    """The 4-byte little-endian length a publisher library may put in front of the struct."""
    decoder = _decoder()
    definition = decoder.load_type_definition(TYPE_DEFINITION)
    for wire in encoded:
        prefixed = struct.pack("<I", len(wire)) + wire
        with pytest.raises(decoder.DecodeError, match="trailing"):
            decoder.decode(prefixed, definition)
        with pytest.raises(decoder.DecodeError, match="short"):
            decoder.decode(wire[:-1], definition)


def test_decoder_reads_the_struct_big_endian() -> None:
    decoder = _decoder()
    definition = decoder.load_type_definition(TYPE_DEFINITION)
    # A little-endian writer would put 1 at the first byte.
    assert decoder.decode(bytes.fromhex("0000000100000032"), definition) == {
        "requested": 1, "issue_time_sim_ms": 50}
    assert decoder.decode(bytes.fromhex("0100000032000000"), definition) == {
        "requested": 0x01000000, "issue_time_sim_ms": 0x32000000}
    assert decoder.out_of_range({"requested": 0x01000000, "issue_time_sim_ms": 0}) == ["requested"]
    assert decoder.out_of_range({"requested": 1, "issue_time_sim_ms": 0}) == []


def test_decoder_cli_prints_the_fields() -> None:
    result = subprocess.run(
        ["python3", str(DECODER), "--hex", "00000001 0000303e"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["requested 1", "issue_time_sim_ms 12350",
                                          "# consumed 8 of 8 bytes"]
    bad = subprocess.run(
        ["python3", str(DECODER), "--hex", "08000000000000010000303e"], capture_output=True, text=True)
    assert bad.returncode == 1
    assert "trailing" in bad.stderr
