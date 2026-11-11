"""The ICD v2 section 3 field table, as data.

Hand-copied from `interfaces/ICD.md` v2, section 3 (43 rows: name, type, meaning)
and from the AOSP SOME/IP type-definition page for the type vocabulary. It is
the single source that the other artifacts are held to:

  * `contract/de4sdv_driving_operational_state.proto`  -- names, numbers, types
  * `interop/someip_type_definition.textproto`         -- SomeIpType per field
  * `codec/someip_struct.py`                           -- the wire codec
  * `scripts/gen_someip_vsidl.py`                      -- the mapping's blocks

Nothing here is derived from the C++ publisher: this module is the independent
reading of the ICD that the S-CORE side's encoder is checked against.

Type vocabulary, exactly as ICD section 3 uses it:
    u32     UINT32, 4 bytes, big-endian
    f32     FLOAT32, 4 bytes, big-endian IEEE-754 binary32
    str     AUTOSAR UTF-8 string: u32 length (BOM + bytes + NUL), BOM EF BB BF,
            bytes, 0x00
    f32[]   dynamic array: u32 length IN BYTES, then the FLOAT32 elements
"""

from __future__ import annotations

from typing import Dict, List, NamedTuple, Sequence, Tuple

U32 = "u32"
F32 = "f32"
STR = "str"
F32_ARRAY = "f32[]"


class Field(NamedTuple):
    number: int
    name: str
    kind: str


# ICD v2 section 3, rows 1-43, in table order. The order is the wire order
# (a SOME/IP struct has no field tags; position is identity).
FIELDS: Tuple[Field, ...] = (
    Field(1, "schema_major", U32),
    Field(2, "schema_minor", U32),
    Field(3, "kind", U32),
    Field(4, "sequence", U32),
    Field(5, "producer", STR),
    Field(6, "publish_real_s", U32),
    Field(7, "publish_real_ns", U32),
    Field(8, "publish_mono_s", U32),
    Field(9, "publish_mono_ns", U32),
    Field(10, "plan_frame_index", U32),
    Field(11, "plan_capture_ms", U32),
    Field(12, "plan_production_mono_s", U32),
    Field(13, "plan_production_mono_ns", U32),
    Field(14, "plan_reference", STR),
    Field(15, "run_record", STR),
    Field(16, "plan_producer", STR),
    Field(17, "plan_sample_count", U32),
    Field(18, "plan_horizon_s", F32),
    Field(19, "plan_acceleration", F32_ARRAY),
    Field(20, "plan_curvature", F32_ARRAY),
    Field(21, "plan_x", F32_ARRAY),
    Field(22, "plan_y", F32_ARRAY),
    Field(23, "speed_kmh", F32),
    Field(24, "longitudinal_acceleration", F32),
    Field(25, "lateral_acceleration", F32),
    Field(26, "yaw_rate_dps", F32),
    Field(27, "sample_capture_ms", U32),
    Field(28, "sample_receipt_mono_s", U32),
    Field(29, "sample_receipt_mono_ns", U32),
    Field(30, "mode", U32),
    Field(31, "cause", U32),
    Field(32, "mode_source", STR),
    Field(33, "cause_since_mono_s", U32),
    Field(34, "cause_since_mono_ns", U32),
    Field(35, "last_plan_frame_index", U32),
    Field(36, "last_plan_capture_ms", U32),
    Field(37, "step_capture_ms", U32),
    Field(38, "last_plan_production_mono_s", U32),
    Field(39, "last_plan_production_mono_ns", U32),
    Field(40, "dropped_samples", U32),
    Field(41, "checkpoint_expected_sha256", STR),
    Field(42, "checkpoint_actual_sha256", STR),
    Field(43, "refusal_reason", STR),
)

BY_NAME: Dict[str, Field] = {field.name: field for field in FIELDS}
NAMES: Tuple[str, ...] = tuple(field.name for field in FIELDS)

SCHEMA_MAJOR = 2
SCHEMA_MINOR = 0

KIND_PLAN = 1
KIND_VEHICLE_STATE = 2
KIND_HEALTH = 3
KIND_NAMES = {0: "KIND_UNSPECIFIED", 1: "PLAN", 2: "VEHICLE_STATE", 3: "HEALTH"}

# `de4sdv::driving::Mode` / `Cause` (interfaces/include/de4sdv/driving/payloads.h).
# Names only: the wire carries the number (ICD rows 30-31), and the screen labels
# it. Nothing on the path maps one to the other.
MODE_NAMES = {
    0: "kStarting",
    1: "kDriving",
    2: "kStopResponse",
    3: "kStandstill",
    4: "kRefused",
}
CAUSE_NAMES = {
    0: "kNone",
    1: "kCameraMissing",
    2: "kCameraInvalid",
    3: "kCameraStale",
    4: "kMotionInvalid",
    5: "kMotionStale",
    6: "kRouteStale",
    7: "kRouteEmpty",
    8: "kPlanStale",
    9: "kPlanInvalid",
    10: "kCommandTimeout",
    11: "kCheckpointRefused",
    12: "kRunEnd",
}

# Which fields belong to which kind (ICD section 3 "Meaning"). Every event
# encodes all 43 fields; the fields outside the kind's group are zero, empty
# strings or empty arrays. Used by the sample builders and by the tests that
# check an encoder does not leak a value across kinds.
COMMON_FIELDS: Tuple[str, ...] = (
    "schema_major",
    "schema_minor",
    "kind",
    "sequence",
    "producer",
    "publish_real_s",
    "publish_real_ns",
    "publish_mono_s",
    "publish_mono_ns",
)
KIND_FIELDS: Dict[int, Tuple[str, ...]] = {
    KIND_PLAN: (
        "plan_frame_index",
        "plan_capture_ms",
        "plan_production_mono_s",
        "plan_production_mono_ns",
        "plan_reference",
        "run_record",
        "plan_producer",
        "plan_sample_count",
        "plan_horizon_s",
        "plan_acceleration",
        "plan_curvature",
        "plan_x",
        "plan_y",
    ),
    KIND_VEHICLE_STATE: (
        "speed_kmh",
        "longitudinal_acceleration",
        "lateral_acceleration",
        "yaw_rate_dps",
        "sample_capture_ms",
        "sample_receipt_mono_s",
        "sample_receipt_mono_ns",
    ),
    KIND_HEALTH: (
        "mode",
        "cause",
        "mode_source",
        "cause_since_mono_s",
        "cause_since_mono_ns",
        "last_plan_frame_index",
        "last_plan_capture_ms",
        "step_capture_ms",
        "last_plan_production_mono_s",
        "last_plan_production_mono_ns",
        "dropped_samples",
        "checkpoint_expected_sha256",
        "checkpoint_actual_sha256",
        "refusal_reason",
    ),
}

SOMEIP_PRIMITIVE = {U32: "UINT32", F32: "FLOAT32"}
SOMEIP_STRING_ENCODING = "UTF_8"
SOMEIP_STRING_LENGTH_FIELD = "FOUR"
SOMEIP_ARRAY_LENGTH_FIELD = "FOUR"
SOMEIP_ARRAY_ELEMENT = {F32_ARRAY: "FLOAT32"}


def default(name: str):
    """The value a field has when its kind does not use it (ICD section 3)."""
    kind = BY_NAME[name].kind
    if kind == U32:
        return 0
    if kind == F32:
        return 0.0
    if kind == STR:
        return ""
    if kind == F32_ARRAY:
        return []
    raise KeyError(kind)


def defaults() -> Dict[str, object]:
    return {name: default(name) for name in NAMES}


def expected_kinds() -> Dict[str, str]:
    return {field.name: field.kind for field in FIELDS}


def field_numbers() -> List[int]:
    return [field.number for field in FIELDS]


def grouped_fields(kind: int) -> Sequence[str]:
    return COMMON_FIELDS + KIND_FIELDS[kind]
