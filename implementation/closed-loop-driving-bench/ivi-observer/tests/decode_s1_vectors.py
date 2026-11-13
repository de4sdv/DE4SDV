#!/usr/bin/env python3
"""Decode the S-CORE publisher's wire vectors with the independent ICD codec.

The publisher's tests write the frames they serialize; this script decodes them
with `codec/someip_struct.py` -- the separate implementation written from
ICD v2 section 3 -- and compares every field. Two independent encoders agreeing
on 43 fields of three kinds is the only local evidence that the S-CORE side and
the SDV Core mapping speak the same struct.

    python3 tests/decode_s1_vectors.py                       # default path
    python3 tests/decode_s1_vectors.py --vectors DIR

Accepted vector forms (first match wins, per file):

  * JSON: {"vectors": [{"name": ..., "hex"|"struct_hex": ..., "fields": {...}}, ...]}
          or a bare list of those objects
  * JSONL / text: one vector per line, either `VECTOR <name> <hex>` (the
    publisher's own dumper format) or `<name> <hex>`, optionally followed by
    `<name>.json` in the same directory holding the expected field values.

A frame may carry the publisher's mw::com envelope (ICD section 2: two-byte
little-endian length at byte 0, the struct from byte 4). The script recognises it
by the length agreeing with the buffer and decodes the struct after it; it says
which form it saw, because "the struct starts at 0" is itself a finding.

Exit: 0 all decoded vectors agree; 1 a disagreement or undecodable vector;
2 no vectors (nothing to check -- reported, not counted as a pass).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from codec import icd_table as table  # noqa: E402
from codec import someip_struct as codec  # noqa: E402

DEFAULT_VECTORS = (
    ROOT.parent / "state-publisher" / "tests" / "vectors"
)

FLOAT_TOLERANCE = 1e-6


def load_expected(directory: pathlib.Path) -> dict[str, dict]:
    """expected.json: {"vectors": [{name, file, message_bytes, fields{43}}]}."""
    path = directory / "expected.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return {entry.get("name"): entry for entry in payload.get("vectors", [])}


def load_vectors(directory: pathlib.Path) -> list[dict]:
    vectors: list[dict] = []
    expected_index = load_expected(directory)

    # The publisher's own form: one .bin per vector, the whole frame with its
    # mw::com envelope, and expected.json holding the values it meant to write.
    for path in sorted(directory.glob("*.bin")):
        entry = expected_index.get(path.stem, {})
        vectors.append({
            "name": path.stem,
            "raw": path.read_bytes(),
            "expected": entry.get("fields"),
            "message_bytes": entry.get("message_bytes"),
            "source": path.name,
        })

    for path in sorted(directory.rglob("*")):
        if path.suffix == ".bin":
            continue
        if not path.is_file():
            continue
        if path.suffix == ".json":
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            entries = payload.get("vectors") if isinstance(payload, dict) else payload
            if not isinstance(entries, list):
                continue
            for entry in entries:
                raw = entry.get("hex") or entry.get("struct_hex") or entry.get("bytes")
                if not isinstance(raw, str):
                    continue
                vectors.append({
                    "name": entry.get("name") or entry.get("id") or path.stem,
                    "raw": bytes.fromhex(raw.replace(" ", "")),
                    "expected": entry.get("fields") or entry.get("expected"),
                    "source": path.name,
                })
            continue
        if path.suffix in (".jsonl", ".txt", ".log", ".hex"):
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                match = re.match(r"^\s*(?:VECTOR\s+)?(\S+)\s+([0-9a-fA-F]{16,})\s*$", line)
                if not match:
                    continue
                name, raw = match.group(1), bytes.fromhex(match.group(2))
                sidecar = path.with_name(f"{name}.json")
                expected = None
                if sidecar.is_file():
                    try:
                        expected = json.loads(sidecar.read_text(encoding="utf-8"))
                    except json.JSONDecodeError:
                        expected = None
                vectors.append({"name": name, "raw": raw, "expected": expected,
                                "source": path.name})
    return vectors


def strip_envelope(raw: bytes) -> tuple[bytes, str]:
    """Return (struct bytes, how the frame was framed)."""
    if len(raw) >= 4 and int.from_bytes(raw[0:2], "little") == len(raw) - 4:
        return raw[4:], "mw::com envelope (2-byte little-endian length at 0, struct at 4)"
    return raw, "struct only (no envelope)"


def decode_vector(raw: bytes) -> tuple[dict, str, str]:
    body, framing = strip_envelope(raw)
    try:
        state, consumed = codec.decode_with_trailer(body, allow_zero_fill=True)
        trailer = "none" if consumed == len(body) else f"{len(body) - consumed} zero bytes"
        return state, framing, trailer
    except codec.DecodeError as error:
        raise SystemExit(
            f"  cannot decode as an ICD section 3 struct: {error}\n"
            f"  first bytes: {body[:16].hex(' ')}\n"
            f"  (a protobuf frame starting 08 01 is the old option-A encoding, "
            f"not this contract's)"
        )


def compare(name: str, expected: dict, actual: dict) -> list[str]:
    problems: list[str] = []
    unknown = set(expected) - set(table.NAMES)
    if unknown:
        problems.append(f"{name}: the vector names fields that are not in the ICD: {sorted(unknown)}")
    for field in table.FIELDS:
        if field.name not in expected:
            continue
        want = expected[field.name]
        got = actual[field.name]
        if field.kind == table.F32_ARRAY:
            want_list = [float(value) for value in want]
            if len(want_list) != len(got):
                problems.append(f"{name}.{field.name}: {len(got)} values, vector has {len(want_list)}")
                continue
            for index, (a, b) in enumerate(zip(want_list, got)):
                if abs(a - b) > FLOAT_TOLERANCE * max(1.0, abs(a)):
                    problems.append(f"{name}.{field.name}[{index}]: {b} != {a}")
                    break
        elif field.kind == table.F32:
            if abs(float(want) - got) > FLOAT_TOLERANCE * max(1.0, abs(float(want))):
                problems.append(f"{name}.{field.name}: {got} != {want}")
        else:
            if want != got:
                problems.append(f"{name}.{field.name}: {got!r} != {want!r}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="decode the S-CORE wire vectors")
    parser.add_argument("--vectors", default=str(DEFAULT_VECTORS))
    parser.add_argument("--dump", action="store_true", help="print every decoded field")
    args = parser.parse_args(argv)

    directory = pathlib.Path(args.vectors)
    if not directory.is_dir():
        print(f"NOT CHECKED: no vector directory at {directory}")
        print("The publisher's vectors are produced by another workstream; until they")
        print("exist there is no cross-implementation check, and this script does not")
        print("stand in for one. The codec's own round trip and the protobuf agreement")
        print("in tests/test_contract_and_encoding.py are what have been run.")
        return 2

    vectors = load_vectors(directory)
    if not vectors:
        print(f"NOT CHECKED: {directory} exists but holds no vector this script recognises")
        return 2

    failures = 0
    field_comparisons = 0
    print(f"{len(vectors)} vector(s) from {directory}")
    for vector in vectors:
        name = vector["name"]
        raw = vector["raw"]
        if vector.get("message_bytes") is not None:
            body, _ = strip_envelope(raw)
            if len(body) != vector["message_bytes"]:
                print(f"FAIL {name}: {len(body)} struct bytes, expected.json says "
                      f"{vector['message_bytes']}")
                failures += 1
        try:
            state, framing, trailer = decode_vector(raw)
        except SystemExit as error:
            print(f"FAIL {name} ({vector['source']}, {len(raw)} bytes)")
            print(str(error))
            failures += 1
            continue
        if state["schema_major"] != table.SCHEMA_MAJOR:
            print(f"FAIL {name}: schema_major {state['schema_major']} != {table.SCHEMA_MAJOR}")
            failures += 1
        kind_name = table.KIND_NAMES.get(state["kind"], f"kind {state['kind']}")
        print(f"ok   {name:24s} {len(raw):5d} B  {kind_name:13s} seq {state['sequence']:<4d} "
              f"{framing.split(' (')[0]}, trailer {trailer}")
        if args.dump:
            for field in table.FIELDS:
                print(f"       {field.name:32s} {state[field.name]!r}")
        if vector["expected"]:
            field_comparisons += sum(1 for name_ in table.NAMES if name_ in vector["expected"])
            problems = compare(name, vector["expected"], state)
            for problem in problems:
                print(f"     FIELD {problem}")
            failures += len(problems)
        else:
            print("     (no expected values in the vector: decoded, nothing to compare)")

    if failures:
        print(f"VECTOR CHECK FAILED: {failures} disagreement(s)")
        return 1
    compared = sum(1 for vector in vectors if vector["expected"])
    print(f"VECTOR CHECK PASSED: {len(vectors)} vector(s) decoded, {compared} compared, "
          f"{field_comparisons} field comparisons")
    if compared < len(vectors):
        print(f"NOTE: {len(vectors) - compared} vector(s) carried no expected values, so only "
              f"decoding was checked for them")
    return 0


if __name__ == "__main__":
    sys.exit(main())
