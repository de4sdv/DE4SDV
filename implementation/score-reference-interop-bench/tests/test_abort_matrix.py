"""Tests of the REQ-MW-018 abort-matrix evaluator (VC-MW-019 rehearsal).

The adapter runs with the start configuration of a member run; a real-time
signal selects one of three throws, each inside a try/catch: one inside
librclcpp.so, one in adapter code, one inside the shared libstdc++. The
adapter of record must end with SIGABRT and a core whose top frames are
abort and __cxa_allocate_exception at an address in the executable, with the
expected thrower below, located by its address too. The same adapter built
without the override must survive all three, so the matrix discriminates;
the gate needs both, and exactly one result per role and variant.
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
MAPS_LIBSTDCXX = (FIXTURES / "gdb_mappings_libstdcxx_x86_64.txt").read_text(encoding="utf-8")
BT_RCLCPP = (FIXTURES / "gdb_bt_stripped_libc_rclcpp.txt").read_text(encoding="utf-8")
MAPS_ROS = (FIXTURES / "gdb_mappings_x86_64_ros.txt").read_text(encoding="utf-8")
BT_ADAPTER = """#0  0x00007f12a5e969fc in pthread_kill () from /lib/x86_64-linux-gnu/libc.so.6
#1  0x00007f12a5e42476 in raise () from /lib/x86_64-linux-gnu/libc.so.6
#2  0x00007f12a5e287f3 in abort () from /lib/x86_64-linux-gnu/libc.so.6
#3  0x0000561b0b6d26a9 in __cxa_allocate_exception ()
#4  0x0000561b0b6e0a10 in de4sdv::score_adapter::fault_hook::ThrowInAdapterCode[abi:cxx11]() ()
#5  0x0000561b0b6d9c11 in (anonymous namespace)::OnFaultHookParameter(std::vector<rclcpp::Parameter, std::allocator<rclcpp::Parameter> > const&) ()
"""
BT_FASTDDS = (FIXTURES / "gdb_bt_fastdds_shm_aarch64.txt").read_text(encoding="utf-8")
MAPS_FASTDDS = (FIXTURES / "gdb_mappings_fastdds_aarch64.txt").read_text(encoding="utf-8")
MAPS = {BT_LIBSTDCXX: MAPS_LIBSTDCXX, BT_RCLCPP: MAPS_ROS, BT_ADAPTER: MAPS_ROS, BT_FASTDDS: MAPS_FASTDDS}


def _evaluate(record: dict, backtrace: str | None, log: str) -> dict:
    return evaluate_variant(record, backtrace, log, MAPS.get(backtrace) if backtrace else None)


def _log(*events: dict) -> str:
    lines = ["[INFO] [rclcpp]: a console line that is not JSON"]
    for number, event in enumerate(events):
        lines.append(json.dumps({"monotonic_ns": 1000 + number, "realtime_ns": 5000 + number, **event}))
    return "\n".join(lines) + "\n"


SIGNALS = {"rclcpp_internal": 35, "adapter_code": 36, "libstdcxx": 37}


def _adapter_record(variant: str) -> dict:
    return {
        "role": "adapter",
        "variant": variant,
        "ready_before_trigger": True,
        "trigger": {"signal": SIGNALS[variant], "sent_monotonic_ns": 2000},
        "process": {"returncode": -6, "exit_monotonic_ns": 3000, "alive_at_check": False, "stop_returncode": None},
        "core_file": "core.de4sdv_score_ad.4711",
        "core_bytes": 1000,
    }


def _hook_log(variant: str, caught: bool) -> str:
    events = [{"event": "start", "fault_signals": SIGNALS}, {"event": "ready"},
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
    return record


def test_adapter_libstdcxx_variant_passes_with_the_expected_top_frames():
    result = _evaluate(_adapter_record("libstdcxx"), BT_LIBSTDCXX, _hook_log("libstdcxx", caught=False))
    assert result["outcome"] == "passBoundedVerification", result["reasons"]
    assert result["signal"] == "SIGABRT"
    assert result["top_frames"][:2] == [
        "abort in /usr/lib/x86_64-linux-gnu/libc.so.6",
        "__cxa_allocate_exception in /home/runner/install/de4sdv_score_adapter/lib/de4sdv_score_adapter/"
        "de4sdv_score_adapter",
    ]
    assert result["caller"] == "std::__throw_out_of_range_fmt in /usr/lib/x86_64-linux-gnu/libstdc++.so.6.0.30"


def test_adapter_rclcpp_variant_passes_when_librclcpp_threw():
    log = _hook_log("rclcpp_internal", caught=False)
    result = _evaluate(_adapter_record("rclcpp_internal"), BT_RCLCPP, log)
    assert result["outcome"] == "passBoundedVerification", result["reasons"]


def test_adapter_code_variant_passes_when_the_hook_threw():
    result = _evaluate(_adapter_record("adapter_code"), BT_ADAPTER, _hook_log("adapter_code", caught=False))
    assert result["outcome"] == "passBoundedVerification", result["reasons"]


def test_a_survived_exception_fails():
    record = _adapter_record("adapter_code")
    record["process"] = {"returncode": None, "exit_monotonic_ns": None, "alive_at_check": True, "stop_returncode": 0}
    record["core_file"] = None
    result = _evaluate(record, None, _hook_log("adapter_code", caught=True))
    assert result["outcome"] == "failObservedBehavior"
    assert any("survived" in reason for reason in result["reasons"])


def test_a_caught_log_line_fails_even_with_an_abort():
    result = _evaluate(_adapter_record("adapter_code"), BT_ADAPTER, _hook_log("adapter_code", caught=True))
    assert result["outcome"] == "failObservedBehavior"


def test_an_exit_without_sigabrt_fails():
    record = _adapter_record("libstdcxx")
    record["process"]["returncode"] = -11
    result = _evaluate(record, BT_LIBSTDCXX, _hook_log("libstdcxx", caught=False))
    assert result["outcome"] == "failObservedBehavior"
    assert result["signal"] == "SIGSEGV"


def test_an_abort_with_the_wrong_thrower_fails():
    result = _evaluate(_adapter_record("libstdcxx"), BT_ADAPTER, _hook_log("libstdcxx", caught=False))
    assert result["outcome"] == "failObservedBehavior"
    assert any("thrower" in reason for reason in result["reasons"])


def test_an_abort_before_the_trigger_fails_as_a_normal_path_throw():
    record = _adapter_record("rclcpp_internal")
    record["process"]["exit_monotonic_ns"] = 1500
    log = _hook_log("rclcpp_internal", caught=False)
    result = _evaluate(record, BT_FASTDDS, log)
    assert result["outcome"] == "failObservedBehavior"
    assert any("before the trigger" in reason for reason in result["reasons"])


def test_an_adapter_that_never_got_ready_blocks_the_variant():
    record = _adapter_record("adapter_code")
    record["ready_before_trigger"] = False
    result = _evaluate(record, BT_FASTDDS, _log({"event": "start", "fault_signals": SIGNALS}))
    assert result["outcome"] == "blockedTargetRuntime"


def test_a_missing_core_is_missing_evidence():
    record = _adapter_record("libstdcxx")
    record["core_file"] = None
    record["core_bytes"] = None
    result = _evaluate(record, None, _hook_log("libstdcxx", caught=False))
    assert result["outcome"] == "inconclusiveMissingEvidence"


def test_control_passes_when_it_survives_and_catches():
    result = _evaluate(_control_record("libstdcxx"), None, _hook_log("libstdcxx", caught=True))
    assert result["outcome"] == "passBoundedVerification", result["reasons"]


def test_control_rclcpp_variant_needs_the_caught_exception():
    caught = _hook_log("rclcpp_internal", caught=True)
    assert _evaluate(_control_record("rclcpp_internal"), None, caught)["outcome"] == "passBoundedVerification"
    silent = _hook_log("rclcpp_internal", caught=False)
    assert _evaluate(_control_record("rclcpp_internal"), None, silent)["outcome"] == "inconclusiveMissingEvidence"


def test_a_trigger_signal_that_the_adapter_did_not_log_is_error_evidence():
    record = _adapter_record("libstdcxx")
    record["trigger"]["signal"] = SIGNALS["adapter_code"]
    result = _evaluate(record, BT_LIBSTDCXX, _hook_log("libstdcxx", caught=False))
    assert result["outcome"] == "errorEvidence"


def test_no_signal_sent_is_error_evidence():
    record = _adapter_record("libstdcxx")
    record["trigger"] = {"signal": None, "sent_monotonic_ns": None}
    result = _evaluate(record, BT_LIBSTDCXX, _hook_log("libstdcxx", caught=False))
    assert result["outcome"] == "errorEvidence"


def test_control_that_aborts_fails():
    record = _control_record("adapter_code")
    record["process"] = {"returncode": -6, "exit_monotonic_ns": 3000, "alive_at_check": False, "stop_returncode": None}
    result = _evaluate(record, BT_ADAPTER, _hook_log("adapter_code", caught=False))
    assert result["outcome"] == "failObservedBehavior"


def test_control_must_stop_cleanly_on_sigterm():
    record = _control_record("adapter_code")
    record["process"]["stop_returncode"] = 3
    result = _evaluate(record, None, _hook_log("adapter_code", caught=True))
    assert result["outcome"] == "failObservedBehavior"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda r: r.pop("variant"),
        lambda r: r.update(variant="unknown"),
        lambda r: r.update(role="observer"),
        lambda r: r.update(ready_before_trigger="true"),
        lambda r: r["process"].update(returncode="-6"),
        lambda r: r["trigger"].update(sent_monotonic_ns=True),
        lambda r: r["trigger"].update(extra=1),
        lambda r: r.update(extra_key=1),
    ],
)
def test_malformed_records_are_error_evidence(mutation):
    record = copy.deepcopy(_adapter_record("libstdcxx"))
    mutation(record)
    result = _evaluate(record, BT_LIBSTDCXX, _hook_log("libstdcxx", caught=False))
    assert result["outcome"] == "errorEvidence"


def test_parse_adapter_log_keeps_json_events_in_order():
    events = parse_adapter_log(_log({"event": "start"}, {"event": "ready"}) + "{not json}\n[]\n")
    assert [event["event"] for event in events] == ["start", "ready"]


def test_summary_counts_three_of_three_and_discrimination():
    summary = summarize_matrix(_full_matrix())
    assert summary["adapter_sigabrt_at_override"] == "3/3"
    assert summary["control_survived"] == "3/3"
    assert summary["discriminates"] is True
    assert summary["gate"] == "pass"
    assert summary["gate_problems"] == []


def test_summary_fails_the_gate_with_two_of_three():
    results = [
        _evaluate(_adapter_record("adapter_code"), BT_ADAPTER, _hook_log("adapter_code", caught=False)),
        _evaluate(_adapter_record("libstdcxx"), BT_LIBSTDCXX, _hook_log("libstdcxx", caught=False)),
    ]
    summary = summarize_matrix(results)
    assert summary["adapter_sigabrt_at_override"] == "2/3"
    assert summary["gate"] == "fail"


def test_a_core_without_address_mappings_is_missing_evidence():
    result = evaluate_variant(_adapter_record("libstdcxx"), BT_LIBSTDCXX, _hook_log("libstdcxx", caught=False), None)
    assert result["outcome"] == "inconclusiveMissingEvidence"
    assert any("mappings" in reason for reason in result["reasons"])


def test_a_libstdcxx_thrower_with_debug_information_still_passes():
    backtrace = BT_LIBSTDCXX.replace(
        "#6  0x00007f8d3e8a1c3e in std::__throw_out_of_range_fmt(char const*, ...) () from "
        "/lib/x86_64-linux-gnu/libstdc++.so.6",
        "#6  0x00007f8d3e8a1c3e in std::__throw_out_of_range_fmt (__fmt=0x1) at "
        "../../../../../src/libstdc++-v3/src/c++11/functexcept.cc:84")
    result = evaluate_variant(_adapter_record("libstdcxx"), backtrace, _hook_log("libstdcxx", caught=False),
                              MAPS_LIBSTDCXX)
    assert result["outcome"] == "passBoundedVerification", result["reasons"]


def test_an_allocation_frame_of_libstdcxx_with_debug_information_fails():
    backtrace = BT_LIBSTDCXX.replace(
        "#5  0x000055d4c1a2b6a9 in __cxa_allocate_exception ()",
        "#5  0x00007f8d3e8a0123 in __cxa_allocate_exception (thrown_size=16) at "
        "../../../../src/libstdc++-v3/libsupc++/eh_alloc.cc:284")
    result = evaluate_variant(_adapter_record("libstdcxx"), backtrace, _hook_log("libstdcxx", caught=False),
                              MAPS_LIBSTDCXX)
    assert result["outcome"] == "failObservedBehavior"


def _full_matrix() -> list[dict]:
    results = []
    for variant, bt in [("rclcpp_internal", BT_RCLCPP), ("adapter_code", BT_ADAPTER), ("libstdcxx", BT_LIBSTDCXX)]:
        results.append(_evaluate(_adapter_record(variant), bt, _hook_log(variant, caught=False)))
        results.append(_evaluate(_control_record(variant), None, _hook_log(variant, caught=True)))
    return results


def test_the_gate_fails_when_the_control_build_aborts_too():
    results = [result for result in _full_matrix() if result["role"] == "adapter"]
    for variant in ("rclcpp_internal", "adapter_code", "libstdcxx"):
        record = _control_record(variant)
        record["process"] = {"returncode": -6, "exit_monotonic_ns": 3000, "alive_at_check": False,
                             "stop_returncode": None}
        results.append(_evaluate(record, None, _hook_log(variant, caught=False)))
    summary = summarize_matrix(results)
    assert summary["adapter_sigabrt_at_override"] == "3/3"
    assert summary["control_survived"] == "0/3"
    assert summary["discriminates"] is False
    assert summary["gate"] == "fail"


def test_the_gate_fails_without_the_control_build():
    summary = summarize_matrix([result for result in _full_matrix() if result["role"] == "adapter"])
    assert summary["gate"] == "fail"
    assert any("no result for control" in problem for problem in summary["gate_problems"])


def test_a_later_pass_never_hides_a_failure_of_the_same_variant():
    results = _full_matrix()
    failed = dict(results[0], outcome="failObservedBehavior")
    summary = summarize_matrix([failed] + results)
    assert summary["gate"] == "fail"
    assert summary["variants"]["rclcpp_internal"]["adapter"] == "more than one result"


def test_a_result_of_an_unknown_role_fails_the_gate():
    summary = summarize_matrix(_full_matrix() + [{"role": "observer", "variant": "libstdcxx",
                                                  "outcome": "passBoundedVerification"}])
    assert summary["gate"] == "fail"


def test_reports_the_first_named_frame_below_an_unnamed_thrower():
    backtrace = """#0  0x00007f93dba969bc in pthread_kill () from /lib/x86_64-linux-gnu/libc.so.6
#1  0x00007f93dba42476 in raise () from /lib/x86_64-linux-gnu/libc.so.6
#2  0x00007f93dba287f3 in abort () from /lib/x86_64-linux-gnu/libc.so.6
#3  0x00005623d55ff819 in __cxa_allocate_exception ()
#4  0x00007f93dc2e7b38 in ?? () from /opt/ros/humble/lib/librclcpp.so
#5  0x00007f93dc3b89bd in ?? () from /opt/ros/humble/lib/librclcpp.so
#6  0x00007f93dc3109fa in rclcpp::Executor::execute_service(std::shared_ptr<rclcpp::ServiceBase>) () from /opt/ros/humble/lib/librclcpp.so
"""
    mappings = """Mapped address spaces:

          Start Addr           End Addr       Size     Offset objfile
      0x5623d5500000     0x5623d5700000   0x200000        0x0 /bench/bin/de4sdv_score_adapter
      0x7f93dba00000     0x7f93dbbb0000   0x1b0000        0x0 /usr/lib/x86_64-linux-gnu/libc.so.6
      0x7f93dc200000     0x7f93dc400000   0x200000        0x0 /opt/ros/humble/lib/librclcpp.so
"""
    log = _hook_log("rclcpp_internal", caught=False)
    result = evaluate_variant(_adapter_record("rclcpp_internal"), backtrace, log, mappings)
    assert result["outcome"] == "passBoundedVerification", result["reasons"]
    assert result["caller"] == "?? in /opt/ros/humble/lib/librclcpp.so"
    assert result["first_named_frame"] == "rclcpp::Executor::execute_service in /opt/ros/humble/lib/librclcpp.so"
