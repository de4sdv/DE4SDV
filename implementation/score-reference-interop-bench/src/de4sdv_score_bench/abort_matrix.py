"""Evaluator of the REQ-MW-018 abort matrix (rehearsal of VC-MW-019).

The adapter runs with the start configuration of a member run. A real-time
signal selects one throw inside a try/catch of the adapter's fault hook:

- ``rclcpp_internal``: rclcpp::Node::get_parameter of an undeclared
  parameter; ParameterNotDeclaredException is thrown inside librclcpp.so.
- ``adapter_code``: a throw in adapter code.
- ``libstdcxx``: ``std::vector::at`` out of range, so the shared libstdc++
  throws.

The adapter of record passes a variant only if it ends with SIGABRT after the
trigger, and the core shows abort, then ``__cxa_allocate_exception`` at an
address inside the executable, then the expected thrower, located by its
address too. The control build, the same sources without the override,
passes a variant if it survives the same trigger, handles the exception and
then stops cleanly on SIGTERM. The gate passes only when the adapter passes
all three variants and the control build passes all three, so the matrix
discriminates, and only with exactly one result per role and variant.

Outcomes use the evidence outcome vocabulary of the middleware verification
model: passBoundedVerification, failObservedBehavior,
inconclusiveMissingEvidence, blockedTargetRuntime, errorEvidence.
"""

from __future__ import annotations

import json
import signal
from typing import Any, Callable

from de4sdv_score_bench.backtrace import (
    Frame,
    check_abort_top_frames,
    first_named_frame_below_override,
    frame_text,
    lies_in,
    read_located_frames,
)

PASS = "passBoundedVerification"
FAIL = "failObservedBehavior"
MISSING = "inconclusiveMissingEvidence"
BLOCKED = "blockedTargetRuntime"
ERROR = "errorEvidence"

VARIANTS = ("rclcpp_internal", "adapter_code", "libstdcxx")
ROLES = ("adapter", "control")
EXECUTABLES = {"adapter": "de4sdv_score_adapter", "control": "de4sdv_score_adapter_no_abort_control"}

_EXPECTED_THROWER: dict[str, tuple[str, Callable[[Frame], bool]]] = {
    "rclcpp_internal": ("code in librclcpp.so", lambda frame: lies_in(frame, "librclcpp.so")),
    "adapter_code": (
        "ThrowInAdapterCode in the adapter executable",
        lambda frame: lies_in(frame, EXECUTABLES["adapter"]) and "ThrowInAdapterCode" in frame.function,
    ),
    "libstdcxx": (
        "std::__throw_out_of_range_fmt in libstdc++.so",
        lambda frame: lies_in(frame, "libstdc++.so") and "__throw_out_of_range_fmt" in frame.function,
    ),
}

_RECORD_KEYS = {
    "role",
    "variant",
    "ready_before_trigger",
    "trigger",
    "process",
    "core_file",
    "core_bytes",
}
_TRIGGER_KEYS = {"signal", "sent_monotonic_ns"}
_PROCESS_KEYS = {"returncode", "exit_monotonic_ns", "alive_at_check", "stop_returncode"}


def json_lines(text: str) -> list[dict[str, Any]]:
    """The JSON objects of text, one per line, in order; other lines are skipped."""
    records: list[dict[str, Any]] = []
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


def parse_adapter_log(text: str) -> list[dict[str, Any]]:
    """The adapter's JSON event lines in order; other console lines are skipped."""
    return [record for record in json_lines(text) if isinstance(record.get("event"), str)]


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
    trigger = record["trigger"]
    if not isinstance(trigger, dict) or set(trigger) != _TRIGGER_KEYS:
        errors.append("trigger does not have the closed key set")
    else:
        if not _is_optional_int(trigger["signal"]):
            errors.append("trigger signal is not an integer")
        if not _is_optional_int(trigger["sent_monotonic_ns"]):
            errors.append("trigger time is not an integer")
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


def evaluate_variant(
    record: Any, backtrace_text: str | None, adapter_log_text: str, mappings_text: str | None = None
) -> dict[str, Any]:
    """Outcome of one variant for the adapter of record or the control build.

    backtrace_text is gdb's ``bt`` of the core and mappings_text gdb's ``info
    proc mappings`` of the same core.
    """
    known = record if isinstance(record, dict) else {}
    result: dict[str, Any] = {"role": known.get("role"), "variant": known.get("variant"), "outcome": PASS,
                              "reasons": [], "signal": None, "top_frames": [], "caller": None,
                              "first_named_frame": None}
    errors = _shape_errors(record)
    if errors:
        return dict(result, outcome=ERROR, reasons=errors)
    role, variant, process, trigger = record["role"], record["variant"], record["process"], record["trigger"]
    result["signal"] = _signal_name(process["returncode"])
    events = parse_adapter_log(adapter_log_text)

    def finish(outcome: str, reason: str) -> dict[str, Any]:
        result["outcome"] = outcome
        result["reasons"].append(reason)
        return result

    if not record["ready_before_trigger"]:
        return finish(BLOCKED, "the adapter did not log ready before the trigger")
    start = next((event for event in events if event["event"] == "start"), None)
    signals = start.get("fault_signals") if start is not None else None
    if not isinstance(signals, dict) or trigger["signal"] is None or signals.get(variant) != trigger["signal"]:
        return finish(ERROR, "the trigger signal is not the one that the adapter logged for this variant")

    ended = process["returncode"] is not None and not process["alive_at_check"]
    if role == "control":
        if ended:
            return finish(FAIL, f"the control build did not survive: {_describe_end(process['returncode'])}")
        if not _events_for(events, "fault_hook_caught", variant):
            return finish(MISSING, "the control build logged no caught exception")
        if process["stop_returncode"] != 0:
            return finish(FAIL, f"the control build did not stop cleanly on SIGTERM: {process['stop_returncode']}")
        return result

    if not ended:
        return finish(FAIL, "the adapter survived the exception")
    if process["returncode"] != -signal.SIGABRT:
        return finish(FAIL, f"the adapter ended with {_describe_end(process['returncode'])}, not SIGABRT")
    sent = trigger["sent_monotonic_ns"]
    if process["exit_monotonic_ns"] is not None and (sent is None or process["exit_monotonic_ns"] < sent):
        return finish(FAIL, "the adapter aborted before the trigger: a throw on its normal path")
    if not _events_for(events, "fault_hook_trigger", variant):
        return finish(MISSING, "the adapter logged no fault hook trigger for this variant")
    if _events_for(events, "fault_hook_caught", variant):
        return finish(FAIL, "the adapter caught the exception instead of aborting")
    if record["core_file"] is None or not backtrace_text:
        return finish(MISSING, "no core or backtrace of the abort")
    if not mappings_text:
        return finish(MISSING, "no address mappings of the core, so no frame can be located")
    frames = read_located_frames(backtrace_text, mappings_text)
    check = check_abort_top_frames(frames, EXECUTABLES[role])
    start = frames.index(check.abort_frame) if check.abort_frame in frames else 0
    result["top_frames"] = [frame_text(frame) for frame in frames[start : start + 4]]
    if check.caller_frame is not None:
        result["caller"] = frame_text(check.caller_frame)
        # A library without symbols for its internal functions shows "??";
        # the first named frame below the thrower locates it for the report.
        named = first_named_frame_below_override(frames, check)
        result["first_named_frame"] = frame_text(named) if named is not None else None
    if not check.passed:
        result["outcome"] = FAIL
        result["reasons"].extend(check.reasons)
        return result
    expected, matches = _EXPECTED_THROWER[variant]
    if not matches(check.caller_frame):
        return finish(FAIL, f"the thrower below the override is {result['caller']}, expected {expected}")
    return result


def summarize_matrix(results: list[dict[str, Any]]) -> dict[str, Any]:
    """The abort gate: the adapter of record passes 3 of 3 and the control build passes 3 of 3.

    A missing, repeated or unknown row fails the gate, so a later pass can
    never hide an earlier failure of the same role and variant.
    """
    rows: dict[tuple[str, str], list[dict[str, Any]]] = {}
    problems: list[str] = []
    for result in results:
        key = (result.get("role"), result.get("variant"))
        if key[0] not in ROLES or key[1] not in VARIANTS:
            problems.append(f"a result of unknown role or variant: {key[0]} {key[1]}")
            continue
        rows.setdefault(key, []).append(result)
    for (role, variant), found in sorted(rows.items()):
        if len(found) > 1:
            problems.append(f"{len(found)} results for {role} {variant}")

    def outcome(role: str, variant: str) -> str:
        found = rows.get((role, variant), [])
        if not found:
            return "not run"
        if len(found) > 1:
            return "more than one result"
        return found[0].get("outcome", "no outcome")

    for role in ROLES:
        for variant in VARIANTS:
            if (role, variant) not in rows:
                problems.append(f"no result for {role} {variant}")
    adapter_passed = [variant for variant in VARIANTS if outcome("adapter", variant) == PASS]
    control_passed = [variant for variant in VARIANTS if outcome("control", variant) == PASS]
    discriminates = len(adapter_passed) == len(VARIANTS) and len(control_passed) == len(VARIANTS)
    return {
        "adapter_sigabrt_at_override": f"{len(adapter_passed)}/{len(VARIANTS)}",
        "control_survived": f"{len(control_passed)}/{len(VARIANTS)}",
        "discriminates": discriminates,
        "gate": "pass" if discriminates and not problems else "fail",
        "gate_problems": problems,
        "variants": {
            variant: {"adapter": outcome("adapter", variant), "control": outcome("control", variant)}
            for variant in VARIANTS
        },
    }
