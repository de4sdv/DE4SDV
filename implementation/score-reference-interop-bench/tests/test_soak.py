"""Tests of the soak evaluator of the one-process adapter (brittleness check of the design).

The adapter runs nominally for the planned time: the vehicle-speed provider
sends finite samples over mw::com, an independent ROS 2 observer receives the
VelocityReports, frames flow from the synthetic frame source into the frame
event. Any throw on a normal path of a linked library aborts the adapter
(REQ-MW-018), so a clean soak shows that no such throw happened in that time.
"""

from pathlib import Path
import copy
import json
import struct
import sys

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))

from de4sdv_score_bench.soak import evaluate_soak, float32_bits  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SECOND = 1_000_000_000


def _adapter_log(published: int, *, include_exit: bool = True, allocate_failed: int = 0) -> str:
    events = [
        {"event": "start", "fault_hook_enabled": False},
        {"event": "ros_node_ready", "rmw": "rmw_cyclonedds_cpp"},
        {"event": "ready"},
        {"event": "status", "speed_samples_published": published // 2, "rss_kib": 20000, "frames_sent": 10,
         "frames_allocate_failed": 0, "frame_connection_losses": 0, "speed_samples_withheld_non_finite": 0,
         "speed_samples_withheld_out_of_range": 0},
        {"event": "stop_requested"},
        {"event": "speed_path_stopped", "result": "proxy_destroyed"},
        {"event": "final_status", "speed_samples_published": published, "rss_kib": 21000, "frames_sent": 20,
         "frames_allocate_failed": allocate_failed, "frame_connection_losses": 0,
         "speed_samples_withheld_non_finite": 0, "speed_samples_withheld_out_of_range": 0},
    ]
    if include_exit:
        events.append({"event": "exit", "code": 0})
    lines = []
    for number, event in enumerate(events):
        lines.append(json.dumps({"monotonic_ns": (number + 1) * SECOND, "realtime_ns": 0, **event}))
    return "\n".join(lines) + "\n"


def _provider_log(values: list[float], count: int) -> str:
    lines = [json.dumps({"event": "offered", "pid": 1, "monotonic_ns": 0})]
    for seq in range(1, count + 1):
        value = values[(seq - 1) % len(values)]
        lines.append(json.dumps({"seq": seq, "speed_kmh": value, "bits": "0", "monotonic_ns": seq,
                                 "realtime_ns": seq, "send": "ok"}))
    return "\n".join(lines) + "\n"


def _observer_log(values: list[float], count: int) -> str:
    lines = []
    for seq in range(count):
        mps = values[seq % len(values)] / 3.6
        lines.append(json.dumps({"receipt_monotonic_ns": seq, "stamp_ns": seq,
                                 "longitudinal_velocity_bits": float32_bits(mps),
                                 "lateral_velocity": 0.0, "heading_rate": 0.0, "frame_id": "base_link"}))
    return "\n".join(lines) + "\n"


VALUES = [36.0, 72.0, 50.0, 0.0]


def _run(planned_s: int = 1800) -> dict:
    return {
        "planned_duration_s": planned_s,
        "adapter_ready_monotonic_ns": 3 * SECOND,
        "stop_request_monotonic_ns": 3 * SECOND + planned_s * SECOND,
        "early_exit_returncode": None,
        "stop_returncode": 0,
        "adapter_core_files": [],
        "provider_values_kmh": VALUES,
    }


def _evaluate(run: dict, published: int = 1000, observed: int = 1000, **log_options) -> dict:
    return evaluate_soak(
        run,
        adapter_log_text=_adapter_log(published, **log_options),
        provider_log_text=_provider_log(VALUES, 1010),
        observer_log_text=_observer_log(VALUES, observed),
        backtrace_text=None,
    )


def test_float32_bits_is_the_ieee_single_pattern():
    assert float32_bits(10.0) == "41200000"
    assert float32_bits(20.0) == struct.pack(">f", 20.0).hex()


def test_a_clean_soak_passes():
    result = _evaluate(_run())
    assert result["outcome"] == "passBoundedVerification", result["reasons"]
    assert result["soak_s"] >= 1800
    assert result["observed_messages"] == 1000


def test_a_shorter_soak_than_planned_is_inconclusive():
    run = _run()
    run["stop_request_monotonic_ns"] = run["adapter_ready_monotonic_ns"] + 60 * SECOND
    assert _evaluate(run)["outcome"] == "inconclusiveMissingEvidence"


def test_an_early_exit_fails_and_reports_the_thrower():
    run = _run()
    run["early_exit_returncode"] = -6
    run["stop_returncode"] = None
    run["adapter_core_files"] = ["core.de4sdv_score_ad.77"]
    result = evaluate_soak(
        run,
        adapter_log_text=_adapter_log(10, include_exit=False),
        provider_log_text=_provider_log(VALUES, 20),
        observer_log_text=_observer_log(VALUES, 10),
        backtrace_text=(FIXTURES / "gdb_bt_fastdds_shm_aarch64.txt").read_text(encoding="utf-8"),
    )
    assert result["outcome"] == "failObservedBehavior"
    assert "libfastrtps" in result["abort_caller"]


def test_a_core_without_an_early_exit_still_fails():
    run = _run()
    run["adapter_core_files"] = ["core.de4sdv_score_ad.78"]
    assert _evaluate(run)["outcome"] == "failObservedBehavior"


def test_an_unclean_stop_fails():
    run = _run()
    run["stop_returncode"] = 3
    assert _evaluate(run)["outcome"] == "failObservedBehavior"


def test_a_missing_exit_event_fails():
    assert _evaluate(_run(), include_exit=False)["outcome"] == "failObservedBehavior"


def test_an_adapter_that_never_got_ready_blocks_the_soak():
    run = _run()
    run["adapter_ready_monotonic_ns"] = None
    assert _evaluate(run)["outcome"] == "blockedTargetRuntime"


def test_a_value_that_no_provider_sample_explains_fails():
    run = _run()
    bad = json.dumps({"receipt_monotonic_ns": 1, "stamp_ns": 1, "longitudinal_velocity_bits": float32_bits(99.0),
                      "lateral_velocity": 0.0, "heading_rate": 0.0, "frame_id": "base_link"})
    result = evaluate_soak(
        run,
        adapter_log_text=_adapter_log(1001),
        provider_log_text=_provider_log(VALUES, 1010),
        observer_log_text=_observer_log(VALUES, 1000) + bad + "\n",
        backtrace_text=None,
    )
    assert result["outcome"] == "failObservedBehavior"
    assert result["unexplained_values"] == 1


def test_too_few_observed_messages_fail():
    assert _evaluate(_run(), published=1000, observed=500)["outcome"] == "failObservedBehavior"


def test_no_published_sample_is_missing_evidence():
    assert _evaluate(_run(), published=0, observed=0)["outcome"] == "inconclusiveMissingEvidence"


def test_frame_allocation_failures_are_reported_but_do_not_fail_the_soak():
    result = _evaluate(_run(), allocate_failed=3)
    assert result["outcome"] == "passBoundedVerification"
    assert result["frames_allocate_failed"] == 3


def test_malformed_run_record_is_error_evidence():
    run = copy.deepcopy(_run())
    run["planned_duration_s"] = "1800"
    assert _evaluate(run)["outcome"] == "errorEvidence"
    run = copy.deepcopy(_run())
    run["unexpected"] = True
    assert _evaluate(run)["outcome"] == "errorEvidence"
