"""Evaluator of the soak of the one-process adapter (brittleness check of the design).

baselibs' aborts_upon_exception turns every throw in the adapter process into
an abort, also a throw that a linked library would catch itself on its normal
path. The soak runs the adapter nominally for the planned time and passes when
the adapter stayed up, stopped cleanly on SIGTERM (second LoLa rule), left no
core, and its output stayed plausible: the observer received the published
VelocityReports, and each received longitudinal velocity is the float32 of a
provider value divided by 3.6. If a library throws on its normal path, the
soak fails and the report names the thrower: a finding against the
one-process design, not a bench fault.
"""

from __future__ import annotations

import json
import math
import struct
from typing import Any

from de4sdv_score_bench.abort_matrix import BLOCKED, ERROR, FAIL, MISSING, PASS, parse_adapter_log
from de4sdv_score_bench.backtrace import check_abort_top_frames, parse_gdb_backtrace

MIN_OBSERVED_RATIO = 0.95

_RUN_KEYS = {
    "planned_duration_s",
    "adapter_ready_monotonic_ns",
    "stop_request_monotonic_ns",
    "early_exit_returncode",
    "stop_returncode",
    "adapter_core_files",
    "provider_values_kmh",
}


def float32_bits(value: float) -> str:
    """Big-endian hex of the IEEE-754 single pattern of value."""
    return struct.pack(">f", value).hex()


def _json_lines(text: str) -> list[dict[str, Any]]:
    records = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            records.append(value)
    return records


def _shape_errors(run: Any) -> list[str]:
    if not isinstance(run, dict) or set(run) != _RUN_KEYS:
        return ["the run record does not have the closed key set"]
    errors = []
    if type(run["planned_duration_s"]) is not int or run["planned_duration_s"] <= 0:
        errors.append("planned_duration_s is not a positive integer")
    for key in ("adapter_ready_monotonic_ns", "stop_request_monotonic_ns", "early_exit_returncode",
                "stop_returncode"):
        if run[key] is not None and type(run[key]) is not int:
            errors.append(f"{key} is not an integer")
    if not isinstance(run["adapter_core_files"], list) or not all(
        isinstance(name, str) for name in run["adapter_core_files"]
    ):
        errors.append("adapter_core_files is not a list of names")
    values = run["provider_values_kmh"]
    if not isinstance(values, list) or not values or not all(
        type(value) in (int, float) and math.isfinite(value) for value in values
    ):
        errors.append("provider_values_kmh is not a list of finite numbers")
    return errors


def _last(events: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    matching = [event for event in events if event["event"] == name]
    return matching[-1] if matching else None


def evaluate_soak(
    run: Any,
    *,
    adapter_log_text: str,
    provider_log_text: str,
    observer_log_text: str,
    backtrace_text: str | None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "outcome": PASS,
        "reasons": [],
        "soak_s": None,
        "published": None,
        "observed_messages": None,
        "unexplained_values": None,
        "provider_samples_sent": None,
        "frames_sent": None,
        "frames_allocate_failed": None,
        "frame_connection_losses": None,
        "rss_kib_first": None,
        "rss_kib_last": None,
        "abort_caller": None,
    }
    errors = _shape_errors(run)
    if errors:
        result["outcome"] = ERROR
        result["reasons"] = errors
        return result

    def fail(outcome: str, reason: str) -> None:
        # The first failure sets the outcome; later reasons are kept for the report.
        if result["outcome"] == PASS:
            result["outcome"] = outcome
        result["reasons"].append(reason)

    events = parse_adapter_log(adapter_log_text)
    if backtrace_text:
        frames = parse_gdb_backtrace(backtrace_text)
        check = check_abort_top_frames(frames)
        if check.caller_frame is not None:
            caller = check.caller_frame
            below = frames[frames.index(caller) :]
            named = next((frame for frame in below if frame.function != "??"), caller)
            library = caller.library or "the adapter executable"
            result["abort_caller"] = f"{named.function} in {library}"

    if run["adapter_ready_monotonic_ns"] is None:
        fail(BLOCKED, "the adapter never logged ready")
    if run["early_exit_returncode"] is not None:
        fail(FAIL, f"the adapter ended during the soak with {run['early_exit_returncode']}")
    if run["adapter_core_files"]:
        fail(FAIL, f"the adapter left a core: {', '.join(run['adapter_core_files'])}")
    if result["outcome"] != PASS:
        return result

    soak_ns = run["stop_request_monotonic_ns"] - run["adapter_ready_monotonic_ns"]
    result["soak_s"] = soak_ns // 1_000_000_000
    if soak_ns < run["planned_duration_s"] * 1_000_000_000:
        fail(MISSING, f"the soak ran {result['soak_s']} s, less than the planned {run['planned_duration_s']} s")
    if run["stop_returncode"] != 0:
        fail(FAIL, f"the adapter did not stop cleanly on SIGTERM: {run['stop_returncode']}")
    stopped = _last(events, "speed_path_stopped")
    if stopped is None or stopped.get("result") != "proxy_destroyed":
        fail(FAIL, "the speed path did not stop by the second LoLa rule")
    if _last(events, "exit") is None:
        fail(FAIL, "the adapter logged no exit")

    final = _last(events, "final_status")
    statuses = [event for event in events if event["event"] in ("status", "final_status")]
    if statuses:
        result["rss_kib_first"] = statuses[0].get("rss_kib")
        result["rss_kib_last"] = statuses[-1].get("rss_kib")
    if final is None:
        fail(MISSING, "the adapter logged no final status")
        return result
    published = final.get("speed_samples_published")
    result["published"] = published
    result["frames_sent"] = final.get("frames_sent")
    result["frames_allocate_failed"] = final.get("frames_allocate_failed")
    result["frame_connection_losses"] = final.get("frame_connection_losses")

    provider_samples = [record for record in _json_lines(provider_log_text) if "seq" in record]
    result["provider_samples_sent"] = sum(1 for record in provider_samples if record.get("send") == "ok")
    expected_bits = {float32_bits(value / 3.6) for value in run["provider_values_kmh"]}
    observed = [record for record in _json_lines(observer_log_text) if "longitudinal_velocity_bits" in record]
    result["observed_messages"] = len(observed)
    result["unexplained_values"] = sum(
        1 for record in observed if record["longitudinal_velocity_bits"] not in expected_bits
    )
    if type(published) is not int or published <= 0:
        fail(MISSING, "the adapter published no VelocityReport")
        return result
    if result["unexplained_values"]:
        fail(FAIL, f"{result['unexplained_values']} observed values match no provider value")
    if len(observed) < MIN_OBSERVED_RATIO * published:
        fail(FAIL, f"the observer received {len(observed)} of {published} published VelocityReports")
    for key in ("speed_samples_withheld_non_finite", "speed_samples_withheld_out_of_range"):
        if final.get(key):
            fail(FAIL, f"{key} is {final.get(key)} although the provider sent finite values only")
    return result
