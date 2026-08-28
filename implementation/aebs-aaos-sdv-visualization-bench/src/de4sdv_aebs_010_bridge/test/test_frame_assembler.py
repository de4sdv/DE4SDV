"""Unit and contract tests for the pure 010 bridge core (no ROS required)."""

from __future__ import annotations

import pytest

from de4sdv_aebs_010_bridge.frame_assembler import (
    FrameAssembler,
    FrameError,
    FrameValidator,
    PresentationWatchdog,
    SourceObservation,
    HEALTH_HEALTHY,
    HEALTH_INVALID,
    HEALTH_RESTORED,
    HEALTH_STALE,
    HEALTH_UNAVAILABLE,
)

RSS_TOPIC = "/control/autonomous_emergency_braking/debug/rss_distance"
CLOUD_TOPIC = "/control/autonomous_emergency_braking/debug/obstacle_pointcloud"
DIAG_TOPIC = "/diagnostics"
WARN_TOPIC = "/de4sdv/aebs_009b/warning_request"
BRAKE_TOPIC = "/de4sdv/aebs_009b/emergency_braking_request"
STATE_TOPIC = "/de4sdv/aebs_009b/coordination_state"


def make_assembler() -> FrameAssembler:
    return FrameAssembler("de4sdv_aebs_010_bridge@vmB")


def valid_source_frame() -> dict:
    assembler = make_assembler()
    assembler.observe_rss_distance(
        SourceObservation(RSS_TOPIC, {"source_timestamp_ns": 1_000_000_000}, 1_000_000_100),
        12.5,
    )
    assembler.observe_obstacle_projection(
        SourceObservation(CLOUD_TOPIC, {"source_timestamp_ns": 1_000_000_000}, 1_000_000_100),
        10.0, 0.02,
    )
    assembler.observe_native_intervention(
        SourceObservation(DIAG_TOPIC, {"source_timestamp_ns": 1_000_000_000}, 1_000_000_100),
        "autonomous_emergency_braking: aeb_emergency_stop", "OK", "no intervention",
    )
    assembler.observe_warning_request(
        SourceObservation(WARN_TOPIC, {"source_timestamp_ns": 1_000_000_000}, 1_000_000_100),
        False,
    )
    assembler.observe_braking_request(
        SourceObservation(BRAKE_TOPIC, {"source_timestamp_ns": 1_000_000_000}, 1_000_000_100),
        False,
    )
    assembler.observe_lifecycle_state(
        SourceObservation(STATE_TOPIC, {"source_timestamp_ns": 1_000_000_000}, 1_000_000_100),
        "armed",
    )
    return assembler.assemble(1_000_000_200)


# ---------------------------------------------------------------------------
# Provenance contract (REQ-AEBS-S2-002/003/004)
# ---------------------------------------------------------------------------


def test_native_rss_carries_native_autoware_provenance() -> None:
    frame = valid_source_frame()
    assert frame["rss_distance"]["source_kind"] == "nativeAutowareAEB"
    assert frame["rss_distance"]["units"] == "m"


def test_projected_target_values_are_display_derived_not_native() -> None:
    frame = valid_source_frame()
    assert frame["target_range"]["source_kind"] == "displayDerived"
    assert frame["target_bearing"]["source_kind"] == "displayDerived"


def test_warning_braking_lifecycle_are_de4sdv_derived() -> None:
    frame = valid_source_frame()
    for name in ("de4sdv_warning_request", "de4sdv_braking_request", "de4sdv_lifecycle_state"):
        assert frame[name]["source_kind"] == "de4sdvAebsCoordinator"


def test_coordinator_object_distance_never_becomes_native_field() -> None:
    # The frame has no native field that could carry coordinator-derived
    # object distance; only the native RSS field exists with native provenance.
    frame = valid_source_frame()
    native_fields = [k for k, v in frame.items()
                     if isinstance(v, dict) and v.get("source_kind") == "nativeAutowareAEB"]
    assert set(native_fields) <= {"rss_distance", "native_intervention"}


def test_source_timestamps_preserved_per_field() -> None:
    frame = valid_source_frame()
    assert frame["rss_distance"]["source_timestamp_ns"] == 1_000_000_000
    assert frame["de4sdv_warning_request"]["source_timestamp_ns"] == 1_000_000_000


# ---------------------------------------------------------------------------
# Frame assembly and monotonic sequencing
# ---------------------------------------------------------------------------


def test_sequence_increases_monotonically() -> None:
    assembler = make_assembler()
    frame1 = assembler.assemble(1_000)
    frame2 = assembler.assemble(2_000)
    assert frame2["sequence"] == frame1["sequence"] + 1


def test_schema_version_is_recorded() -> None:
    frame = valid_source_frame()
    assert frame["schema_major"] == 1
    assert frame["schema_minor"] == 0


# ---------------------------------------------------------------------------
# Sink-side validation (REQ-AEBS-S2-008)
# ---------------------------------------------------------------------------


@pytest.fixture()
def validator() -> FrameValidator:
    return FrameValidator(max_frame_age_ns=100_000_000, stale_timeout_ns=1_000_000_000)


def test_valid_frame_accepted(validator: FrameValidator) -> None:
    accepted, reason = validator.validate(valid_source_frame(), last_accepted_sequence=0, now_ns=1_000_000_300)
    assert accepted, reason


def test_unsupported_schema_rejected(validator: FrameValidator) -> None:
    frame = valid_source_frame()
    frame["schema_major"] = 99
    accepted, reason = validator.validate(frame, last_accepted_sequence=0, now_ns=1_000_000_300)
    assert not accepted and "schema" in reason


def test_non_monotonic_sequence_rejected(validator: FrameValidator) -> None:
    accepted, reason = validator.validate(valid_source_frame(), last_accepted_sequence=5, now_ns=1_000_000_300)
    assert not accepted and "sequence" in reason


def test_missing_field_rejected(validator: FrameValidator) -> None:
    frame = valid_source_frame()
    del frame["rss_distance"]
    accepted, reason = validator.validate(frame, last_accepted_sequence=0, now_ns=1_000_000_300)
    assert not accepted and "rss_distance" in reason


def test_unknown_field_rejected(validator: FrameValidator) -> None:
    frame = valid_source_frame()
    frame["unexpected"] = 1
    accepted, _ = validator.validate(frame, last_accepted_sequence=0, now_ns=1_000_000_300)
    assert not accepted


def test_nan_value_rejected(validator: FrameValidator) -> None:
    frame = valid_source_frame()
    frame["rss_distance"]["value"] = float("nan")
    accepted, reason = validator.validate(frame, last_accepted_sequence=0, now_ns=1_000_000_300)
    assert not accepted and "finite" in reason


def test_negative_value_rejected(validator: FrameValidator) -> None:
    frame = valid_source_frame()
    frame["rss_distance"]["value"] = -1.0
    accepted, reason = validator.validate(frame, last_accepted_sequence=0, now_ns=1_000_000_300)
    assert not accepted and "negative" in reason


def test_stale_timestamp_rejected(validator: FrameValidator) -> None:
    frame = valid_source_frame()
    frame["frame_timestamp_ns"] = 1_000_000_200 - 2_000_000_000
    accepted, reason = validator.validate(frame, last_accepted_sequence=0, now_ns=1_000_000_300)
    assert not accepted and "older" in reason


def test_future_timestamp_rejected(validator: FrameValidator) -> None:
    frame = valid_source_frame()
    frame["frame_timestamp_ns"] = 1_000_000_300 + 500_000_000
    accepted, reason = validator.validate(frame, last_accepted_sequence=0, now_ns=1_000_000_300)
    assert not accepted and "future" in reason


# ---------------------------------------------------------------------------
# Presentation watchdog (REQ-AEBS-S2-006..009)
# ---------------------------------------------------------------------------


class Dispositions:
    def __init__(self) -> None:
        self.seen: list[str] = []

    def __call__(self, disposition: str) -> None:
        self.seen.append(disposition)


def make_watchdog(now_ns: int = 1_000_000_000) -> tuple[PresentationWatchdog, Dispositions]:
    seen = Dispositions()
    watchdog = PresentationWatchdog(
        stale_timeout_ns=1_000_000_000,          # 1.0 s planning target
        restore_consecutive_frames=3,            # planning target
        restored_hold_ns=2_000_000_000,          # 2 s transient RESTORED
        now_ns=now_ns,
        on_disposition=seen,
    )
    return watchdog, seen


def test_initial_disposition_unavailable() -> None:
    watchdog, _ = make_watchdog()
    assert watchdog.disposition == HEALTH_UNAVAILABLE


def test_first_valid_frames_do_not_skip_unavailable() -> None:
    watchdog, seen = make_watchdog()
    watchdog.mark_valid(1_000_000_000)
    watchdog.mark_valid(1_100_000_000)
    assert watchdog.disposition == HEALTH_UNAVAILABLE  # 2 of 3 frames
    watchdog.mark_valid(1_200_000_000)                 # 3rd -> healthy
    assert HEALTH_HEALTHY in seen.seen
    assert watchdog.disposition == HEALTH_HEALTHY


def test_stale_after_timeout() -> None:
    watchdog, seen = make_watchdog()
    # Three consecutive valid frames make the presentation healthy first.
    watchdog.mark_valid(900_000_000)
    watchdog.mark_valid(950_000_000)
    watchdog.mark_valid(1_000_000_000)
    assert watchdog.disposition == HEALTH_HEALTHY
    watchdog.tick(1_500_000_000)
    watchdog.tick(2_100_000_000)  # > 1 s after last valid
    assert HEALTH_STALE in seen.seen
    assert watchdog.disposition == HEALTH_STALE


def test_restored_after_consecutive_valid_frames() -> None:
    watchdog, seen = make_watchdog()
    watchdog.mark_valid(900_000_000)
    watchdog.mark_valid(950_000_000)
    watchdog.mark_valid(1_000_000_000)    # healthy
    watchdog.tick(2_100_000_000)          # stale
    watchdog.mark_valid(2_200_000_000)    # 1
    watchdog.mark_valid(2_300_000_000)    # 2
    watchdog.mark_valid(2_400_000_000)    # 3 -> restored
    assert HEALTH_RESTORED in seen.seen
    assert watchdog.disposition == HEALTH_RESTORED


def test_restored_transitions_to_healthy_after_hold() -> None:
    watchdog, seen = make_watchdog()
    watchdog.mark_valid(900_000_000)
    watchdog.mark_valid(950_000_000)
    watchdog.mark_valid(1_000_000_000)    # healthy
    watchdog.tick(2_100_000_000)          # stale
    watchdog.mark_valid(2_200_000_000)
    watchdog.mark_valid(2_300_000_000)
    watchdog.mark_valid(2_400_000_000)    # restored; hold until 4.4 s
    assert watchdog.disposition == HEALTH_RESTORED
    watchdog.tick(4_400_000_000)          # hold expires
    assert watchdog.disposition == HEALTH_HEALTHY


def test_invalid_disposition_on_rejection() -> None:
    watchdog, seen = make_watchdog()
    watchdog.mark_valid(900_000_000)
    watchdog.mark_valid(950_000_000)
    watchdog.mark_valid(1_000_000_000)
    watchdog.mark_invalid(1_100_000_000)
    assert HEALTH_INVALID in seen.seen
    assert watchdog.disposition == HEALTH_INVALID


# ---------------------------------------------------------------------------
# Assembler input hygiene
# ---------------------------------------------------------------------------


def test_unsupported_topic_rejected() -> None:
    assembler = make_assembler()
    with pytest.raises(FrameError):
        assembler.observe_rss_distance(
            SourceObservation("/some/other/topic", {"source_timestamp_ns": 1}, 1), 1.0
        )


def test_nonfinite_rss_rejected() -> None:
    assembler = make_assembler()
    with pytest.raises(FrameError):
        assembler.observe_rss_distance(
            SourceObservation(RSS_TOPIC, {"source_timestamp_ns": 1}, 1), float("inf")
        )


def test_unknown_lifecycle_state_rejected() -> None:
    assembler = make_assembler()
    with pytest.raises(FrameError):
        assembler.observe_lifecycle_state(
            SourceObservation(STATE_TOPIC, {"source_timestamp_ns": 1}, 1), "bogus"
        )


def test_exact_native_intervention_tuple_required() -> None:
    assembler = make_assembler()
    assembler.observe_native_intervention(
        SourceObservation(DIAG_TOPIC, {"source_timestamp_ns": 1}, 1),
        "autonomous_emergency_braking: aeb_emergency_stop", "ERROR", "[AEB]: Emergency Brake",
    )
    assert assembler.state.native_intervention["value"] is True
    assembler2 = make_assembler()
    assembler2.observe_native_intervention(
        SourceObservation(DIAG_TOPIC, {"source_timestamp_ns": 1}, 1),
        "autonomous_emergency_braking: aeb_emergency_stop", "ERROR", "different message",
    )
    assert assembler2.state.native_intervention["value"] is False
