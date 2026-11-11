#!/usr/bin/env python3
"""DE4SDV INC-DRIVING-001 slice 10b, S1: independent decoder for the
operational-state SOME/IP struct.

    tests/decode_vectors.py [vector-dir]      # default: tests/vectors

This decoder is written from Interface Control Document v2 section 3 (the
43-field table and the encoding rules), not from publisher_core.cpp:

  * field order and types come from the ICD's markdown table, parsed at run time,
    so a change of the contract changes the decoder;
  * u32 is 4-byte big-endian; f32 is IEEE-754 binary32 big-endian;
  * str is a 4-byte big-endian byte count covering BOM + bytes + NUL, then
    EF BB BF, the UTF-8 bytes, 00 (an empty string is 4 + 4 = 8 bytes);
  * f32[] is a 4-byte big-endian length in bytes, then the elements.

It reads the *.bin frames written by tests/dump_vectors.cpp and the intent
values in expect.jsonl (written from the payload inputs, not from the bytes),
asserts every field of every vector, reports the message sizes, and writes
expected.json: the fully decoded 43-field object of every vector, for
cross-checking another decoder.

Exit code 0 means every check passed.
"""

import json
import math
import pathlib
import re
import struct
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent                                   # state-publisher/
ICD = ROOT.parent / "interfaces" / "ICD.md"
VECTOR_DIR = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "vectors"

BOM = b"\xef\xbb\xbf"
MAX_FRAME = 2048            # PreSerializedData<2048>
MAX_MESSAGE = MAX_FRAME - 4  # ICD section 2: the struct starts at byte 4

checks = 0
failures = 0


def check(condition, message):
    global checks, failures
    checks += 1
    if not condition:
        failures += 1
        print(f"FAIL {message}")


# --------------------------------------------------------------- the contract
def parse_icd_table():
    """The 43 rows of ICD v2 section 3, in table order."""
    text = ICD.read_text(encoding="utf-8")
    start = text.index("| # | Field | Type | Meaning |")
    rows = []
    for line in text[start:].splitlines()[2:]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 4 or not cells[0].isdigit():
            continue
        rows.append((int(cells[0]), cells[1], cells[2]))
    return rows


FIELDS = parse_icd_table()
FIELD_TYPES = {number: kind for number, _, kind in FIELDS}
FIELD_NAMES = [name for _, name, _ in FIELDS]


def default_for(kind):
    return 0 if kind in ("u32", "f32") else "" if kind == "str" else []


DEFAULTS = {name: default_for(kind) for _, name, kind in FIELDS}


# ------------------------------------------------------------------ decoding
class DecodeError(Exception):
    pass


def decode_struct(buf):
    """Decode one DrivingOperationalState exactly as ICD v2 section 3 states."""
    if len(buf) > MAX_MESSAGE:
        raise DecodeError(f"message {len(buf)} bytes exceeds the {MAX_MESSAGE}-byte budget")
    out = {}
    pos = 0

    def take(count, what):
        nonlocal pos
        if pos + count > len(buf):
            raise DecodeError(f"{what}: need {count} bytes at {pos}, message is {len(buf)}")
        chunk = buf[pos : pos + count]
        pos += count
        return chunk

    for number, name, kind in FIELDS:
        if kind == "u32":
            out[name] = int.from_bytes(take(4, f"{number} {name}"), "big")
        elif kind == "f32":
            out[name] = struct.unpack(">f", take(4, f"{number} {name}"))[0]
        elif kind == "str":
            length = int.from_bytes(take(4, f"{number} {name} length"), "big")
            if length < 4:
                raise DecodeError(f"{number} {name}: string length {length} < BOM + NUL")
            body = take(length, f"{number} {name} body")
            if body[:3] != BOM:
                raise DecodeError(f"{number} {name}: no UTF-8 BOM")
            if body[-1] != 0:
                raise DecodeError(f"{number} {name}: no terminating NUL")
            raw = body[3:-1]
            if b"\x00" in raw:
                raise DecodeError(f"{number} {name}: NUL inside the string bytes")
            try:
                out[name] = raw.decode("utf-8")
            except UnicodeDecodeError as error:
                raise DecodeError(f"{number} {name}: not UTF-8: {error}") from error
        elif kind == "f32[]":
            length = int.from_bytes(take(4, f"{number} {name} length"), "big")
            if length % 4 != 0:
                raise DecodeError(f"{number} {name}: array length {length} is not a multiple of 4")
            count = length // 4
            out[name] = list(struct.unpack(f">{count}f", take(length, f"{number} {name} body")))
        else:
            raise DecodeError(f"{number} {name}: unknown ICD type {kind!r}")

    if pos != len(buf):
        raise DecodeError(f"{len(buf) - pos} trailing bytes after field 43")
    return out


def f32_bits(value):
    return struct.unpack(">I", struct.pack(">f", value))[0]


def expected_float(expected):
    """Intent value -> predicate on the decoded f32 (exact for finite values)."""
    if isinstance(expected, str):
        if expected == "NaN":
            return math.isnan, "NaN"
        if expected == "Infinity":
            return lambda v: math.isinf(v) and v > 0, "+Infinity"
        if expected == "-Infinity":
            return lambda v: math.isinf(v) and v < 0, "-Infinity"
        if expected == "-0":
            return lambda v: v == 0.0 and math.copysign(1.0, v) < 0, "-0.0"
        raise ValueError(f"bad float token {expected!r}")
    bits = f32_bits(float(expected))
    return lambda v: f32_bits(v) == bits, expected


def compare(name, kind, actual, expected, label):
    if kind == "f32":
        predicate, shown = expected_float(expected)
        check(predicate(actual), f"{label}: {name} = {actual!r}, expected {shown!r}")
    elif kind == "f32[]":
        check(len(actual) == len(expected), f"{label}: {name} has {len(actual)} elements, expected {len(expected)}")
        for index, (got, want) in enumerate(zip(actual, expected)):
            predicate, shown = expected_float(want)
            check(predicate(got), f"{label}: {name}[{index}] = {got!r}, expected {shown!r}")
    else:
        check(actual == expected, f"{label}: {name} = {actual!r}, expected {expected!r}")


# ---------------------------------------------------------------- the vectors
def read_vectors():
    intent_path = VECTOR_DIR / "expect.jsonl"
    intents = {}
    for line in intent_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        intents[entry["name"]] = entry["intent"]
    return intents


def load(name):
    raw = (VECTOR_DIR / f"{name}.bin").read_bytes()
    label = name
    check(len(raw) >= 4, f"{label}: frame shorter than the length prefix")
    if len(raw) < 4:
        return None, None, label
    prefix = int.from_bytes(raw[0:2], "little")
    check(raw[2:4] == b"\x00\x00", f"{label}: bytes 2-3 of the prefix are not zero")
    check(prefix == len(raw) - 4, f"{label}: prefix {prefix}, frame carries {len(raw) - 4}")
    check(len(raw) <= MAX_FRAME, f"{label}: frame {len(raw)} bytes exceeds PreSerializedData<2048>")
    try:
        fields = decode_struct(raw[4:])
    except DecodeError as error:
        check(False, f"{label}: {error}")
        return None, None, label
    check(True, label)
    return fields, raw, label


def verify(name, fields, intent):
    expected = dict(DEFAULTS)
    expected.update(intent)
    for field_number, field_name, kind in FIELDS:
        compare(field_name, kind, fields[field_name], expected[field_name], name)
    checks_done = len(FIELDS)
    return checks_done


def check_defaults(fields, label, exempt):
    """Every field outside `exempt` stays at its ICD type default."""
    for _, name, kind in FIELDS:
        if name in exempt:
            continue
        compare(name, kind, fields[name], default_for(kind), label + " (defaults)")


# ------------------------------------------------------------------ the tests
def test_contract_shape():
    check(len(FIELDS) == 43, f"ICD table has {len(FIELDS)} rows, expected 43")
    check([number for number, _, _ in FIELDS] == list(range(1, 44)), "ICD field numbers are not 1..43")
    kinds = {kind for _, _, kind in FIELDS}
    check(kinds == {"u32", "f32", "str", "f32[]"}, f"unexpected ICD field kinds {kinds}")
    for number, name, kind in FIELDS:
        if number in (1,):
            check(name == "schema_major", f"field 1 is {name}")
        if number == 43:
            check(name == "refusal_reason" and kind == "str", f"field 43 is {name} {kind}")


def test_priming_health(fields):
    label = "health_priming"
    check(fields["schema_major"] == 2, f"{label}: schema_major {fields['schema_major']}")
    check(fields["schema_minor"] == 0, f"{label}: schema_minor {fields['schema_minor']}")
    check(fields["kind"] == 3, f"{label}: kind {fields['kind']}")
    check(fields["sequence"] == 1, f"{label}: sequence {fields['sequence']}")
    check(fields["producer"] == "statePublisher", f"{label}: producer {fields['producer']!r}")
    check((fields["publish_real_s"], fields["publish_real_ns"]) == (1762700000, 0), f"{label}: real time")
    check((fields["publish_mono_s"], fields["publish_mono_ns"]) == (1000, 0), f"{label}: mono time")
    check(fields["mode"] == 0 and fields["cause"] == 0, f"{label}: mode/cause")
    check(fields["mode_source"] == "", f"{label}: mode_source {fields['mode_source']!r}")
    check(fields["plan_reference"] == "" and fields["run_record"] == "", f"{label}: plan strings")
    check(fields["plan_acceleration"] == [], f"{label}: plan_acceleration not empty")


def test_full_plan(fields):
    label = "plan_full"
    check(fields["schema_major"] == 2, f"{label}: schema_major")
    check(fields["kind"] == 1 and fields["sequence"] == 1, f"{label}: kind/sequence")
    check(fields["plan_frame_index"] == 7, f"{label}: frame index")
    check(fields["plan_capture_ms"] == 700, f"{label}: capture ms {fields['plan_capture_ms']}")
    check((fields["plan_production_mono_s"], fields["plan_production_mono_ns"]) == (1000, 700000000),
          f"{label}: production time")
    check(fields["plan_reference"] == "0123456789abcdef/7", f"{label}: reference")
    check(fields["run_record"] == "0123456789abcdef", f"{label}: run record")
    check(fields["plan_producer"] == "drivingAgent/inferPlan", f"{label}: plan producer")
    check(fields["plan_sample_count"] == 64, f"{label}: sample count")
    check(abs(fields["plan_horizon_s"] - 6.4) < 1e-6, f"{label}: horizon {fields['plan_horizon_s']}")
    expected_acceleration = [0.25 * i - 4.0 for i in range(64)]
    check([f32_bits(v) for v in fields["plan_acceleration"]] ==
          [f32_bits(v) for v in expected_acceleration], f"{label}: acceleration values")
    check([f32_bits(v) for v in fields["plan_curvature"]] ==
          [f32_bits(0.5 * i) for i in range(64)], f"{label}: curvature values")
    check([f32_bits(v) for v in fields["plan_x"]] ==
          [f32_bits(0.75 * i) for i in range(64)], f"{label}: x values")
    check([f32_bits(v) for v in fields["plan_y"]] ==
          [f32_bits(-0.125 * i) for i in range(64)], f"{label}: y values")
    check_defaults(fields, label, {
        "schema_major", "schema_minor", "kind", "sequence", "producer",
        "publish_real_s", "publish_real_ns", "publish_mono_s", "publish_mono_ns",
        "plan_frame_index", "plan_capture_ms", "plan_production_mono_s",
        "plan_production_mono_ns", "plan_reference", "run_record", "plan_producer",
        "plan_sample_count", "plan_horizon_s", "plan_acceleration", "plan_curvature",
        "plan_x", "plan_y",
    })


def test_short_and_empty_plan(short, empty):
    check(len(short["plan_acceleration"]) == 3, f"plan_short: {len(short['plan_acceleration'])} samples")
    check([f32_bits(v) for v in short["plan_acceleration"]] ==
          [f32_bits(v) for v in (-4.0, -3.75, -3.5)], "plan_short: acceleration values")
    check(short["plan_sample_count"] == 3, f"plan_short: sample count {short['plan_sample_count']}")
    check(short["plan_reference"] == "" and short["run_record"] == "", "plan_short: empty strings")

    check(empty["plan_sample_count"] == 0, f"plan_empty: sample count {empty['plan_sample_count']}")
    for name in ("plan_acceleration", "plan_curvature", "plan_x", "plan_y"):
        check(empty[name] == [], f"plan_empty: {name} is not empty")
    check(empty["plan_capture_ms"] == 0, f"plan_empty: capture ms {empty['plan_capture_ms']}")
    check(empty["run_record"] == "0123456789abcdef", "plan_empty: run record lost")


def test_unicode(fields):
    label = "plan_unicode"
    check(fields["run_record"] == "运行记录-甲", f"{label}: run_record {fields['run_record']!r}")
    check(fields["plan_reference"] == "运行记录-甲/9", f"{label}: reference {fields['plan_reference']!r}")
    check(fields["plan_producer"] == "驾驶智能体/inferPlan", f"{label}: producer {fields['plan_producer']!r}")
    # 6 characters, 16 UTF-8 bytes: the length covers BOM + bytes + NUL.
    check(len(fields["run_record"].encode("utf-8")) == 16, f"{label}: run_record byte length")
    check(len(fields["run_record"]) == 6, f"{label}: run_record character count")


def test_max_strings(fields):
    check(len(fields["plan_reference"]) == 63, f"plan_max_strings: reference length {len(fields['plan_reference'])}")
    check(len(fields["run_record"]) == 63, f"plan_max_strings: run record length {len(fields['run_record'])}")


def test_vehicle_state(fields):
    label = "vehicle_state"
    check(fields["kind"] == 2 and fields["sequence"] == 1, f"{label}: kind/sequence")
    check(f32_bits(fields["speed_kmh"]) == f32_bits(36.5), f"{label}: speed")
    check(f32_bits(fields["longitudinal_acceleration"]) == f32_bits(-0.5), f"{label}: longitudinal")
    check(f32_bits(fields["lateral_acceleration"]) == f32_bits(0.25), f"{label}: lateral")
    check(f32_bits(fields["yaw_rate_dps"]) == f32_bits(1.75), f"{label}: yaw rate")
    check(fields["sample_capture_ms"] == 12300, f"{label}: capture ms {fields['sample_capture_ms']}")
    check((fields["sample_receipt_mono_s"], fields["sample_receipt_mono_ns"]) == (1234, 500000000),
          f"{label}: receipt time")
    check(fields["publish_mono_s"] == 1234, f"{label}: publish mono")
    check_defaults(fields, label, {
        "schema_major", "schema_minor", "kind", "sequence", "producer",
        "publish_real_s", "publish_real_ns", "publish_mono_s", "publish_mono_ns",
        "speed_kmh", "longitudinal_acceleration", "lateral_acceleration", "yaw_rate_dps",
        "sample_capture_ms", "sample_receipt_mono_s", "sample_receipt_mono_ns",
    })


def test_vehicle_state_specials(fields):
    label = "vehicle_state_specials"
    check(math.isnan(fields["speed_kmh"]), f"{label}: speed {fields['speed_kmh']!r}")
    check(math.isinf(fields["longitudinal_acceleration"]) and fields["longitudinal_acceleration"] > 0,
          f"{label}: longitudinal {fields['longitudinal_acceleration']!r}")
    check(math.isinf(fields["lateral_acceleration"]) and fields["lateral_acceleration"] < 0,
          f"{label}: lateral {fields['lateral_acceleration']!r}")
    check(fields["yaw_rate_dps"] == 0.0 and math.copysign(1.0, fields["yaw_rate_dps"]) < 0,
          f"{label}: yaw rate is not negative zero")


def test_stop_health(stop, standstill, actuation):
    check(stop["kind"] == 3 and stop["sequence"] == 2, f"health_stop_supervise: sequence {stop['sequence']}")
    check(stop["mode"] == 2, f"health_stop_supervise: mode {stop['mode']}")
    check(stop["cause"] == 8, f"health_stop_supervise: cause {stop['cause']}")
    check(stop["mode_source"] == "superviseLoop", f"health_stop_supervise: source {stop['mode_source']!r}")
    check((stop["cause_since_mono_s"], stop["cause_since_mono_ns"]) == (1000, 420000000),
          "health_stop_supervise: cause_since is not the decision time")
    check((stop["publish_mono_s"], stop["publish_mono_ns"]) == (1000, 430000000),
          "health_stop_supervise: publish time")

    check(standstill["mode"] == 3, f"health_standstill: mode {standstill['mode']}")
    check(standstill["cause"] == 8, f"health_standstill: cause {standstill['cause']} (not latched)")
    check((standstill["cause_since_mono_s"], standstill["cause_since_mono_ns"]) == (1000, 420000000),
          "health_standstill: cause_since moved")
    check(standstill["sequence"] == 3, f"health_standstill: sequence {standstill['sequence']}")

    check(actuation["mode"] == 2 and actuation["cause"] == 10, "health_stop_actuation: mode/cause")
    check(actuation["mode_source"] == "actuationAdapter", "health_stop_actuation: source")
    check((actuation["cause_since_mono_s"], actuation["cause_since_mono_ns"]) == (2000, 20000000),
          "health_stop_actuation: cause_since is not the adapter's stopSinceMono")
    check((actuation["publish_mono_s"], actuation["publish_mono_ns"]) == (2000, 50000000),
          "health_stop_actuation: publish time")


def test_refusal(fields):
    label = "health_refusal"
    check(fields["mode"] == 4, f"{label}: mode {fields['mode']}")
    check(fields["cause"] == 11, f"{label}: cause {fields['cause']}")
    check(fields["checkpoint_expected_sha256"] == "a" * 64, f"{label}: expected sha")
    check(fields["checkpoint_actual_sha256"] == "b" * 64, f"{label}: actual sha")
    check(fields["refusal_reason"] == "mismatch", f"{label}: reason {fields['refusal_reason']!r}")
    check((fields["cause_since_mono_s"], fields["cause_since_mono_ns"]) == (0, 700000000),
          f"{label}: cause_since")


def test_health_capture_fields(fields):
    label = "health_capture_fields"
    check(fields["last_plan_frame_index"] == 7, f"{label}: last_plan_frame_index {fields['last_plan_frame_index']}")
    check(fields["last_plan_capture_ms"] == 700, f"{label}: last_plan_capture_ms {fields['last_plan_capture_ms']}")
    check(fields["step_capture_ms"] == 1500, f"{label}: step_capture_ms {fields['step_capture_ms']}")
    check((fields["last_plan_production_mono_s"], fields["last_plan_production_mono_ns"]) == (1000, 700000000),
          f"{label}: last_plan_production")
    check(fields["dropped_samples"] == 1, f"{label}: dropped_samples {fields['dropped_samples']}")


def test_time_carry(fields):
    check((fields["publish_mono_s"], fields["publish_mono_ns"]) == (6, 0),
          f"health_time_carry: (s, ns) = ({fields['publish_mono_s']}, {fields['publish_mono_ns']})")
    check((fields["publish_real_s"], fields["publish_real_ns"]) == (6, 0),
          "health_time_carry: real time")


def lcg_values(seed, count):
    values = []
    state = seed
    for _ in range(count):
        state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
        value = state >> 12
        if state & 0x80000000:
            value -= 1 << 20
        values.append(struct.unpack(">f", struct.pack(">f", value / 1024.0))[0])
    return values


def test_property_random(fields, raw):
    """The 4 x 64 pseudo-random f32 values round-trip bit-exactly."""
    label = "plan_random"
    seed = 0x12345678
    expected = {"plan_acceleration": [], "plan_curvature": [], "plan_x": [], "plan_y": []}
    state = seed
    for _ in range(64):
        for name in expected:            # four draws per index, in field order
            state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
            value = state >> 12
            if state & 0x80000000:
                value -= 1 << 20
            expected[name].append(struct.unpack(">f", struct.pack(">f", value / 1024.0))[0])

    bit_pairs = 0
    for name, values in expected.items():
        got = fields[name]
        check(len(got) == 64, f"{label}: {name} has {len(got)} values")
        for index, (actual, want) in enumerate(zip(got, values)):
            check(f32_bits(actual) == f32_bits(want),
                  f"{label}: {name}[{index}] {actual!r} != {want!r}")
            bit_pairs += 1
    check(bit_pairs == 256, f"{label}: {bit_pairs} value pairs")

    # And each decoded value re-encodes to the bytes that are actually on the
    # wire (bit identity, not a tolerance).
    message = raw[4:]
    # Field offsets: 1-4 are 16 bytes; 5 is a string; 6-13 are 32 bytes; 14, 15,
    # 16 are strings; 17 and 18 are 4 bytes each; then the four arrays.
    pos = 16
    pos += 4 + int.from_bytes(message[pos : pos + 4], "big")   # field 5
    pos += 32                                                  # fields 6-13
    for _ in range(3):                                         # fields 14-16
        length = int.from_bytes(message[pos : pos + 4], "big")
        pos += 4 + length
    pos += 8                                                   # fields 17-18
    for name in expected:
        length = int.from_bytes(message[pos : pos + 4], "big")
        check(length == 256, f"{label}: {name} byte length {length}")
        chunks = [message[pos + 4 + 4 * i : pos + 8 + 4 * i] for i in range(64)]
        check([struct.pack(">f", v) for v in fields[name]] == chunks,
              f"{label}: {name} bytes do not re-encode")
        pos += 4 + length


def sanitized(fields):
    """JSON-safe view: non-finite and signed zero as tokens."""
    out = {}
    for _, name, kind in FIELDS:
        value = fields[name]
        if kind == "f32":
            if math.isnan(value):
                out[name] = "NaN"
            elif math.isinf(value):
                out[name] = "Infinity" if value > 0 else "-Infinity"
            elif value == 0.0 and math.copysign(1.0, value) < 0:
                out[name] = "-0"
            else:
                out[name] = value
        elif kind == "f32[]":
            values = []
            for element in value:
                if math.isnan(element):
                    values.append("NaN")
                elif math.isinf(element):
                    values.append("Infinity" if element > 0 else "-Infinity")
                elif element == 0.0 and math.copysign(1.0, element) < 0:
                    values.append("-0")
                else:
                    values.append(element)
            out[name] = values
        else:
            out[name] = value
    return out


def main():
    test_contract_shape()
    if not VECTOR_DIR.is_dir():
        print(f"FAIL no vector directory {VECTOR_DIR}")
        return 1

    intents = read_vectors()
    required = {
        "health_priming", "plan_full", "plan_random", "plan_short", "plan_empty",
        "plan_unicode", "plan_max_strings", "vehicle_state", "vehicle_state_specials",
        "health_stop_supervise", "health_standstill", "health_stop_actuation",
        "health_refusal", "health_capture_fields", "plan_sequence_2", "health_time_carry",
    }
    check(required.issubset(intents), f"missing vectors: {sorted(required - set(intents))}")

    decoded = {}
    sizes = {}
    raw_by_name = {}
    for name in sorted(intents):
        fields, raw, label = load(name)
        if fields is None:
            continue
        decoded[name] = fields
        raw_by_name[name] = raw
        sizes[name] = (len(raw) - 4, len(raw))
        verify(name, fields, intents[name])

    if failures == 0:
        test_priming_health(decoded["health_priming"])
        test_full_plan(decoded["plan_full"])
        test_short_and_empty_plan(decoded["plan_short"], decoded["plan_empty"])
        test_unicode(decoded["plan_unicode"])
        test_max_strings(decoded["plan_max_strings"])
        test_vehicle_state(decoded["vehicle_state"])
        test_vehicle_state_specials(decoded["vehicle_state_specials"])
        test_stop_health(decoded["health_stop_supervise"], decoded["health_standstill"],
                         decoded["health_stop_actuation"])
        test_refusal(decoded["health_refusal"])
        test_health_capture_fields(decoded["health_capture_fields"])
        test_time_carry(decoded["health_time_carry"])
        test_property_random(decoded["plan_random"], raw_by_name["plan_random"])

    print("message sizes (message bytes / frame bytes):")
    for name in sorted(sizes):
        message, frame = sizes[name]
        print(f"  {name:26s} {message:5d} / {frame:5d}")
    if sizes:
        largest = max(sizes.values())
        print(f"  largest: {largest[0]} bytes (budget {MAX_MESSAGE})")
        check(largest[0] < MAX_MESSAGE, f"a vector reaches the {MAX_MESSAGE}-byte budget")
        check(sizes["plan_max_strings"][0] < MAX_MESSAGE,
              "the worst-case plan does not fit PreSerializedData<2048>")

    # expected.json: the fully decoded fields of every vector, for cross-checking
    # another decoder. Written only after the checks above have run.
    document = {
        "contract": "de4sdv.driving.icd.v2",
        "source": "decoded from tests/vectors/*.bin by tests/decode_vectors.py",
        "max_message_bytes": MAX_MESSAGE,
        "encoding": "someip struct, field order, big-endian; str = 4-byte BOM+bytes+NUL length; f32[] = 4-byte byte length",
        "field_order": FIELD_NAMES,
        "field_types": {name: kind for _, name, kind in FIELDS},
        "value_tokens": {"NaN": "not-a-number", "Infinity": "+inf", "-Infinity": "-inf", "-0": "negative zero"},
        "vectors": [
            {
                "name": name,
                "file": f"{name}.bin",
                "message_bytes": sizes[name][0],
                "frame_bytes": sizes[name][1],
                "fields": sanitized(decoded[name]),
            }
            for name in sorted(decoded)
        ],
    }
    (VECTOR_DIR / "expected.json").write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n",
                                              encoding="utf-8")

    print(f"{'PASS' if failures == 0 else 'FAIL'}: {checks} checks, {failures} failures")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
