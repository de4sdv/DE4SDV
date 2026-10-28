"""Tests of the REQ-MW-018 abort-matrix evaluator (VC-MW-019 rehearsal).

Three exceptions, each inside a try/catch: one in adapter code, one that
rclcpp throws and catches itself, one inside the shared libstdc++. The adapter
of record must end with SIGABRT and a core whose top frames are abort and the
executable's __cxa_allocate_exception, with the expected thrower below. The
same adapter built without the override must survive all three, so the
matrix discriminates.
"""

from pathlib import Path
import copy
import json
import sys

import pytest

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))

from de4sdv_score_bench.abort_matrix import (  # noqa: E402
    evaluate_variant,
    parse_adapter_log,
    summarize_matrix,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"

BT_LIBSTDCXX = (FIXTURES / "gdb_bt_libstdcxx_x86_64.txt").read_text(encoding="utf-8")
BT_RCLCPP = (FIXTURES / "gdb_bt_stripped_libc_rclcpp.txt").read_text(encoding="utf-8")
BT_ADAPTER = """#0  0x00007f12a5e969fc in pthread_kill () from /lib/x86_64-linux-gnu/libc.so.6
#1  0x00007f12a5e42476 in raise () from /lib/x86_64-linux-gnu/libc.so.6
#2  0x00007f12a5e287f3 in abort () from /lib/x86_64-linux-gnu/libc.so.6
#3  0x0000561b0b6d26a9 in __cxa_allocate_exception ()
#4  0x0000561b0b6e0a10 in de4sdv::score_adapter::fault_hook::ThrowInAdapterCode[abi:cxx11]() ()
#5  0x0000561b0b6d9c11 in (anonymous namespace)::OnFaultHookParameter(std::vector<rclcpp::Parameter, std::allocator<rclcpp::Parameter> > const&) ()
"""
BT_FASTDDS = (FIXTURES / "gdb_bt_fastdds_shm_aarch64.txt").read_text(encoding="utf-8")


def _log(*events: dict) -> str:
    lines = ["[INFO] [rclcpp]: a console line that is not JSON"]
    for number, event in enumerate(events):
        lines.append(json.dumps({"monotonic_ns": 1000 + number, "realtime_ns": 5000 + number, **event}))
    return "\n".join(lines) + "\n"


def _adapter_record(variant: str) -> dict:
    return {
        "role": "adapter",
        "variant": variant,
        "fault_hook_environment": "unset" if variant == "rclcpp_internal" else "1",
        "ready_before_trigger": True,
        "trigger": {
            "argv": ["ros2", "param", "set", "--no-daemon", "/de4sdv_score_adapter", "p", "v"],
            "start_monotonic_ns": 2000,
            "end_monotonic_ns": 9000,
            "returncode": 1,
            "timed_out": False,
            "output": "",
        },
        "process": {"returncode": -6, "exit_monotonic_ns": 3000, "alive_at_check": False, "stop_returncode": None},
        "core_file": "core.de4sdv_score_ad.4711",
        "core_bytes": 1000,
    }


def _hook_log(variant: str, caught: bool) -> str:
    events = [{"event": "start", "fault_hook_enabled": True}, {"event": "ready"},
              {"event": "fault_hook_trigger", "variant": variant}]
    if caught:
        events.append({"event": "fault_hook_caught", "variant": variant, "what": "x"})
    return _log(*events)


def _control_record(variant: str) -> dict:
    record = _adapter_record(variant)
    record["role"] = "control"
    record["process"] = {"returncode": None, "exit_monotonic_ns": None, "alive_at_check": True, "stop_returncode": 0}
    record["core_file"] = None
    record["core_bytes"] = None
    if variant == "rclcpp_internal":
        record["trigger"]["output"] = "Setting parameter failed: parameter 'p' cannot be set because it was not declared"
        record["trigger"]["returncode"] = 0
    return record


def test_adapter_libstdcxx_variant_passes_with_the_expected_top_frames():
    result = evaluate_variant(_adapter_record("libstdcxx"), BT_LIBSTDCXX, _hook_log("libstdcxx", caught=False))
    assert result["outcome"] == "passBoundedVerification", result["reasons"]
    assert result["signal"] == "SIGABRT"
    assert result["top_frames"][:2] == ["abort", "__cxa_allocate_exception"]
    assert result["caller"] == "std::__throw_out_of_range_fmt from /lib/x86_64-linux-gnu/libstdc++.so.6"


def test_adapter_rclcpp_variant_passes_when_librclcpp_threw():
    log = _log({"event": "start", "fault_hook_enabled": False}, {"event": "ready"})
    result = evaluate_variant(_adapter_record("rclcpp_internal"), BT_RCLCPP, log)
    assert result["outcome"] == "passBoundedVerification", result["reasons"]


def test_adapter_code_variant_passes_when_the_hook_threw():
    result = evaluate_variant(_adapter_record("adapter_code"), BT_ADAPTER, _hook_log("adapter_code", caught=False))
    assert result["outcome"] == "passBoundedVerification", result["reasons"]


def test_a_survived_exception_fails():
    record = _adapter_record("adapter_code")
    record["process"] = {"returncode": None, "exit_monotonic_ns": None, "alive_at_check": True, "stop_returncode": 0}
    record["core_file"] = None
    result = evaluate_variant(record, None, _hook_log("adapter_code", caught=True))
    assert result["outcome"] == "failObservedBehavior"
    assert any("survived" in reason for reason in result["reasons"])


def test_a_caught_log_line_fails_even_with_an_abort():
    result = evaluate_variant(_adapter_record("adapter_code"), BT_ADAPTER, _hook_log("adapter_code", caught=True))
    assert result["outcome"] == "failObservedBehavior"


def test_an_exit_without_sigabrt_fails():
    record = _adapter_record("libstdcxx")
    record["process"]["returncode"] = -11
    result = evaluate_variant(record, BT_LIBSTDCXX, _hook_log("libstdcxx", caught=False))
    assert result["outcome"] == "failObservedBehavior"
    assert result["signal"] == "SIGSEGV"


def test_an_abort_with_the_wrong_thrower_fails():
    result = evaluate_variant(_adapter_record("libstdcxx"), BT_ADAPTER, _hook_log("libstdcxx", caught=False))
    assert result["outcome"] == "failObservedBehavior"
    assert any("thrower" in reason for reason in result["reasons"])


def test_an_abort_before_the_trigger_fails_as_a_normal_path_throw():
    record = _adapter_record("rclcpp_internal")
    record["process"]["exit_monotonic_ns"] = 1500
    log = _log({"event": "start"}, {"event": "ready"})
    result = evaluate_variant(record, BT_FASTDDS, log)
    assert result["outcome"] == "failObservedBehavior"
    assert any("before the trigger" in reason for reason in result["reasons"])


def test_an_adapter_that_never_got_ready_blocks_the_variant():
    record = _adapter_record("adapter_code")
    record["ready_before_trigger"] = False
    result = evaluate_variant(record, BT_FASTDDS, _log({"event": "start"}))
    assert result["outcome"] == "blockedTargetRuntime"


def test_a_missing_core_is_missing_evidence():
    record = _adapter_record("libstdcxx")
    record["core_file"] = None
    record["core_bytes"] = None
    result = evaluate_variant(record, None, _hook_log("libstdcxx", caught=False))
    assert result["outcome"] == "inconclusiveMissingEvidence"


def test_control_passes_when_it_survives_and_catches():
    result = evaluate_variant(_control_record("libstdcxx"), None, _hook_log("libstdcxx", caught=True))
    assert result["outcome"] == "passBoundedVerification", result["reasons"]


def test_control_rclcpp_variant_needs_the_failure_answer_of_the_parameter_service():
    log = _log({"event": "start"}, {"event": "ready"})
    assert evaluate_variant(_control_record("rclcpp_internal"), None, log)["outcome"] == "passBoundedVerification"
    record = _control_record("rclcpp_internal")
    record["trigger"]["output"] = ""
    assert evaluate_variant(record, None, log)["outcome"] == "inconclusiveMissingEvidence"


def test_control_that_aborts_fails():
    record = _control_record("adapter_code")
    record["process"] = {"returncode": -6, "exit_monotonic_ns": 3000, "alive_at_check": False, "stop_returncode": None}
    result = evaluate_variant(record, BT_ADAPTER, _hook_log("adapter_code", caught=False))
    assert result["outcome"] == "failObservedBehavior"


def test_control_must_stop_cleanly_on_sigterm():
    record = _control_record("adapter_code")
    record["process"]["stop_returncode"] = 3
    result = evaluate_variant(record, None, _hook_log("adapter_code", caught=True))
    assert result["outcome"] == "failObservedBehavior"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda r: r.pop("variant"),
        lambda r: r.update(variant="unknown"),
        lambda r: r.update(role="observer"),
        lambda r: r.update(ready_before_trigger="true"),
        lambda r: r["process"].update(returncode="-6"),
        lambda r: r["trigger"].update(start_monotonic_ns=True),
        lambda r: r.update(extra_key=1),
    ],
)
def test_malformed_records_are_error_evidence(mutation):
    record = copy.deepcopy(_adapter_record("libstdcxx"))
    mutation(record)
    result = evaluate_variant(record, BT_LIBSTDCXX, _hook_log("libstdcxx", caught=False))
    assert result["outcome"] == "errorEvidence"


def test_parse_adapter_log_keeps_json_events_in_order():
    events = parse_adapter_log(_log({"event": "start"}, {"event": "ready"}) + "{not json}\n[]\n")
    assert [event["event"] for event in events] == ["start", "ready"]


def test_summary_counts_three_of_three_and_discrimination():
    results = []
    for variant, bt, log in [
        ("rclcpp_internal", BT_RCLCPP, _log({"event": "ready"})),
        ("adapter_code", BT_ADAPTER, _hook_log("adapter_code", caught=False)),
        ("libstdcxx", BT_LIBSTDCXX, _hook_log("libstdcxx", caught=False)),
    ]:
        results.append(evaluate_variant(_adapter_record(variant), bt, log))
        control_log = log if variant == "rclcpp_internal" else _hook_log(variant, caught=True)
        results.append(evaluate_variant(_control_record(variant), None, control_log))
    summary = summarize_matrix(results)
    assert summary["adapter_sigabrt_at_override"] == "3/3"
    assert summary["discriminates"] is True
    assert summary["gate"] == "pass"


def test_summary_fails_the_gate_with_two_of_three():
    results = [
        evaluate_variant(_adapter_record("adapter_code"), BT_ADAPTER, _hook_log("adapter_code", caught=False)),
        evaluate_variant(_adapter_record("libstdcxx"), BT_LIBSTDCXX, _hook_log("libstdcxx", caught=False)),
    ]
    summary = summarize_matrix(results)
    assert summary["adapter_sigabrt_at_override"] == "2/3"
    assert summary["gate"] == "fail"
