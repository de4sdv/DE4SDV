"""Evaluator of the REQ-MW-018 abort matrix (rehearsal of VC-MW-019).

Each variant throws one exception inside a try/catch while the adapter runs:

- ``rclcpp_internal``: ``ros2 param set`` of an undeclared parameter; rclcpp
  throws ParameterNotDeclaredException and catches it in its parameter
  service. The fault hook is off.
- ``adapter_code``: the env-gated fault hook throws in adapter code.
- ``libstdcxx``: the env-gated fault hook calls ``std::vector::at`` out of
  range, so the shared libstdc++ throws.

The adapter of record passes a variant only if it ends with SIGABRT after the
trigger, and the core shows abort, then the executable's
``__cxa_allocate_exception``, then the expected thrower. The control build,
the same sources without the override, passes a variant if it survives the
same trigger, handles the exception and then stops cleanly on SIGTERM. Both
together show that the matrix discriminates.

Outcomes use the evidence outcome vocabulary of the middleware verification
model: passBoundedVerification, failObservedBehavior,
inconclusiveMissingEvidence, blockedTargetRuntime, errorEvidence.
"""

from __future__ import annotations

import json
import signal
from typing import Any, Callable

from de4sdv_score_bench.backtrace import ABORT_FUNCTIONS, Frame, check_abort_top_frames, parse_gdb_backtrace

PASS = "passBoundedVerification"
FAIL = "failObservedBehavior"
MISSING = "inconclusiveMissingEvidence"
BLOCKED = "blockedTargetRuntime"
ERROR = "errorEvidence"

VARIANTS = ("rclcpp_internal", "adapter_code", "libstdcxx")
HOOK_VARIANTS = ("adapter_code", "libstdcxx")
ROLES = ("adapter", "control")

_EXPECTED_THROWER: dict[str, tuple[str, Callable[[Frame], bool]]] = {
    "rclcpp_internal": (
        "librclcpp.so",
        lambda frame: frame.library is not None and frame.library.endswith("/librclcpp.so"),
    ),
    "adapter_code": (
        "ThrowInAdapterCode in the adapter executable",
        lambda frame: frame.library is None and "ThrowInAdapterCode" in frame.function,
    ),
    "libstdcxx": (
        "std::__throw_out_of_range_fmt in libstdc++.so",
        lambda frame: frame.library is not None
        and "libstdc++.so" in frame.library
        and "__throw_out_of_range_fmt" in frame.function,
    ),
}

_RECORD_KEYS = {
    "role",
    "variant",
    "fault_hook_environment",
    "ready_before_trigger",
    "trigger",
    "process",
    "core_file",
    "core_bytes",
}
_TRIGGER_KEYS = {"argv", "start_monotonic_ns", "end_monotonic_ns", "returncode", "timed_out", "output"}
_PROCESS_KEYS = {"returncode", "exit_monotonic_ns", "alive_at_check", "stop_returncode"}

RCLCPP_REJECTION_TEXT = "Setting parameter failed"


def parse_adapter_log(text: str) -> list[dict[str, Any]]:
    """The adapter's JSON event lines in order; other console lines are skipped."""
    events: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and isinstance(value.get("event"), str):
            events.append(value)
    return events


def _is_int(value: Any) -> bool:
    return type(value) is int


def _is_optional_int(value: Any) -> bool:
    return value is None or type(value) is int


def _shape_errors(record: Any) -> list[str]:
    if not isinstance(record, dict) or set(record) != _RECORD_KEYS:
        return ["the record does not have the closed key set"]
    errors: list[str] = []
    if record["role"] not in ROLES:
        errors.append("unknown role")
    if record["variant"] not in VARIANTS:
        errors.append("unknown variant")
    if type(record["ready_before_trigger"]) is not bool:
        errors.append("ready_before_trigger is not a boolean")
    if not isinstance(record["fault_hook_environment"], str):
        errors.append("fault_hook_environment is not a string")
    trigger = record["trigger"]
    if not isinstance(trigger, dict) or set(trigger) != _TRIGGER_KEYS:
        errors.append("trigger does not have the closed key set")
    else:
        if not isinstance(trigger["argv"], list) or not all(isinstance(item, str) for item in trigger["argv"]):
            errors.append("trigger argv is not a list of strings")
        if not _is_int(trigger["start_monotonic_ns"]) or not _is_int(trigger["end_monotonic_ns"]):
            errors.append("trigger times are not integers")
        if not _is_optional_int(trigger["returncode"]):
            errors.append("trigger returncode is not an integer")
        if type(trigger["timed_out"]) is not bool or not isinstance(trigger["output"], str):
            errors.append("trigger timed_out or output has the wrong type")
    process = record["process"]
    if not isinstance(process, dict) or set(process) != _PROCESS_KEYS:
        errors.append("process does not have the closed key set")
    else:
        for key in ("returncode", "exit_monotonic_ns", "stop_returncode"):
            if not _is_optional_int(process[key]):
                errors.append(f"process {key} is not an integer")
        if type(process["alive_at_check"]) is not bool:
            errors.append("process alive_at_check is not a boolean")
    if record["core_file"] is not None and not isinstance(record["core_file"], str):
        errors.append("core_file is not a string")
    if not _is_optional_int(record["core_bytes"]):
        errors.append("core_bytes is not an integer")
    return errors


def _signal_name(returncode: int | None) -> str | None:
    if returncode is None or returncode >= 0:
        return None
    try:
        return signal.Signals(-returncode).name
    except ValueError:
        return f"signal {-returncode}"


def _describe_end(returncode: int | None) -> str:
    if returncode is None:
        return "no end"
    if returncode >= 0:
        return f"exit code {returncode}"
    return str(_signal_name(returncode))


def _events_for(events: list[dict[str, Any]], name: str, variant: str) -> list[dict[str, Any]]:
    return [event for event in events if event["event"] == name and event.get("variant") == variant]


def _frame_text(frame: Frame) -> str:
    # glibc with debug symbols names abort __GI_abort; the report uses one name.
    function = "abort" if frame.function in ABORT_FUNCTIONS else frame.function
    return function if frame.library is None else f"{function} from {frame.library}"


def evaluate_variant(record: Any, backtrace_text: str | None, adapter_log_text: str) -> dict[str, Any]:
    """Outcome of one variant for the adapter of record or the control build."""
    errors = _shape_errors(record)
    if errors:
        return {
            "role": record.get("role") if isinstance(record, dict) else None,
            "variant": record.get("variant") if isinstance(record, dict) else None,
            "outcome": ERROR,
            "reasons": errors,
            "signal": None,
            "top_frames": [],
            "caller": None,
            "first_named_frame": None,
        }
    role = record["role"]
    variant = record["variant"]
    process = record["process"]
    trigger = record["trigger"]
    events = parse_adapter_log(adapter_log_text)
    result: dict[str, Any] = {
        "role": role,
        "variant": variant,
        "outcome": PASS,
        "reasons": [],
        "signal": _signal_name(process["returncode"]),
        "top_frames": [],
        "caller": None,
        "first_named_frame": None,
    }

    def finish(outcome: str, reason: str) -> dict[str, Any]:
        result["outcome"] = outcome
        result["reasons"].append(reason)
        return result

    if not record["ready_before_trigger"]:
        return finish(BLOCKED, "the adapter did not log ready before the trigger")

    ended = process["returncode"] is not None and not process["alive_at_check"]
    if role == "control":
        if ended:
            return finish(FAIL, f"the control build did not survive: {_describe_end(process['returncode'])}")
        if variant in HOOK_VARIANTS:
            if not _events_for(events, "fault_hook_caught", variant):
                return finish(MISSING, "the control build logged no caught exception")
        elif RCLCPP_REJECTION_TEXT not in trigger["output"]:
            return finish(MISSING, "the parameter service gave no failure answer to the undeclared parameter")
        if process["stop_returncode"] != 0:
            return finish(FAIL, f"the control build did not stop cleanly on SIGTERM: {process['stop_returncode']}")
        return result

    if not ended:
        return finish(FAIL, "the adapter survived the exception")
    if process["returncode"] != -signal.SIGABRT:
        return finish(FAIL, f"the adapter ended with {_describe_end(process['returncode'])}, not SIGABRT")
    if process["exit_monotonic_ns"] is not None and process["exit_monotonic_ns"] < trigger["start_monotonic_ns"]:
        return finish(FAIL, "the adapter aborted before the trigger: a throw on its normal path")
    if variant in HOOK_VARIANTS:
        if not _events_for(events, "fault_hook_trigger", variant):
            return finish(MISSING, "the adapter logged no fault hook trigger for this variant")
        if _events_for(events, "fault_hook_caught", variant):
            return finish(FAIL, "the adapter caught the exception instead of aborting")
    if record["core_file"] is None or not backtrace_text:
        return finish(MISSING, "no core or backtrace of the abort")
    frames = parse_gdb_backtrace(backtrace_text)
    check = check_abort_top_frames(frames)
    start = frames.index(check.abort_frame) if check.abort_frame in frames else 0
    result["top_frames"] = [_frame_text(frame) for frame in frames[start : start + 4]]
    if check.caller_frame is not None:
        result["caller"] = _frame_text(check.caller_frame)
        # A library without symbols for its internal functions shows "??";
        # the first named frame below the thrower locates it for the report.
        below = frames[frames.index(check.caller_frame) :]
        named = next((frame for frame in below if frame.function != "??"), None)
        result["first_named_frame"] = _frame_text(named) if named is not None else None
    if not check.passed:
        result["outcome"] = FAIL
        result["reasons"].extend(check.reasons)
        return result
    expected, matches = _EXPECTED_THROWER[variant]
    if not matches(check.caller_frame):
        return finish(FAIL, f"the thrower below the override is {result['caller']}, expected {expected}")
    return result


def summarize_matrix(results: list[dict[str, Any]]) -> dict[str, Any]:
    """The abort gate: all three variants of the adapter of record pass."""
    adapter = {result["variant"]: result for result in results if result["role"] == "adapter"}
    control = {result["variant"]: result for result in results if result["role"] == "control"}
    passed = [variant for variant in VARIANTS if adapter.get(variant, {}).get("outcome") == PASS]
    discriminating = [
        variant
        for variant in VARIANTS
        if adapter.get(variant, {}).get("outcome") == PASS and control.get(variant, {}).get("outcome") == PASS
    ]
    return {
        "adapter_sigabrt_at_override": f"{len(passed)}/{len(VARIANTS)}",
        "control_survived": f"{sum(1 for v in VARIANTS if control.get(v, {}).get('outcome') == PASS)}/{len(VARIANTS)}",
        "discriminates": len(discriminating) == len(VARIANTS),
        "gate": "pass" if len(passed) == len(VARIANTS) else "fail",
        "variants": {
            variant: {
                "adapter": adapter.get(variant, {}).get("outcome", "not run"),
                "control": control.get(variant, {}).get("outcome", "not run"),
            }
            for variant in VARIANTS
        },
    }
