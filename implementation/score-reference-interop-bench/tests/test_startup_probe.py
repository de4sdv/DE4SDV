"""Tests of the startup probe evaluator of the one-process adapter.

Each case states what it expects: the adapter runs, the adapter of record
aborts at the override, or (a control of the setup) the adapter does not
start. A control passes only when the host also ran out of participants for
the other ROS 2 processes, so the control shows the limit it is about.
"""

from pathlib import Path
import sys

import pytest

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))

from de4sdv_score_bench.startup_probe import evaluate_case, summarize_probe  # noqa: E402


def _record(**changes) -> dict:
    record = {
        "case": "cyclonedds_bench_environment_after_11_participants",
        "binary": "de4sdv_score_adapter",
        "expected": "runs",
        "ros_environment": {"RMW_IMPLEMENTATION": "rmw_cyclonedds_cpp"},
        "peers_before": 11,
        "peers_after": 0,
        "peers_ready": 11,
        "peer_velocity_reports": 290,
        "ready": True,
        "survived_hold": True,
        "end_returncode": None,
        "stop_returncode": 0,
        "core": False,
        "override_check_passed": None,
        "first_named_frame_below_override": None,
        "required_log_text": None,
        "required_log_text_found": None,
    }
    record.update(changes)
    return record


def _aborted(**changes) -> dict:
    record = _record(expected="aborts_at_override", peers_before=0, peers_ready=0, peer_velocity_reports=None,
                     ready=False, survived_hold=False, end_returncode=-6, stop_returncode=None, core=True,
                     override_check_passed=True)
    record.update(changes)
    return record


def test_an_adapter_that_runs_with_all_participants_is_as_expected():
    evaluation = evaluate_case(_record())
    assert evaluation["as_expected"], evaluation["reasons"]
    assert evaluation["observed"] == "runs"


def test_a_running_case_needs_every_other_participant_ready():
    evaluation = evaluate_case(_record(peers_ready=10))
    assert not evaluation["as_expected"]


def test_a_running_case_needs_the_counting_participant_to_receive_velocity_reports():
    assert not evaluate_case(_record(peer_velocity_reports=0))["as_expected"]


def test_an_abort_at_the_override_is_as_expected_only_with_the_checked_top_frames():
    assert evaluate_case(_aborted())["as_expected"]
    evaluation = evaluate_case(_aborted(override_check_passed=False))
    assert not evaluation["as_expected"]
    assert evaluation["observed"] == "does_not_start"


def test_a_control_build_that_aborts_where_it_should_run_is_not_as_expected():
    record = _aborted(expected="runs", binary="de4sdv_score_adapter_no_abort_control")
    assert not evaluate_case(record)["as_expected"]


def test_the_default_configuration_control_is_as_expected_when_participants_ran_out():
    record = _record(case="cyclonedds_default_configuration_after_11_participants", expected="does_not_start",
                     peers_ready=10, peer_velocity_reports=None, ready=False, survived_hold=False,
                     end_returncode=-6, stop_returncode=None, core=True, override_check_passed=True)
    evaluation = evaluate_case(record)
    assert evaluation["as_expected"], evaluation["reasons"]


def test_the_control_does_not_count_when_every_other_participant_started():
    record = _record(case="cyclonedds_default_configuration_after_11_participants", expected="does_not_start",
                     peers_ready=11, ready=False, survived_hold=False, end_returncode=-6, stop_returncode=None)
    assert not evaluate_case(record)["as_expected"]


def test_the_control_fails_when_the_adapter_runs():
    assert not evaluate_case(_record(expected="does_not_start", peers_ready=10))["as_expected"]


def test_the_localhost_only_control_needs_the_error_text_of_the_setup():
    record = _record(case="cyclonedds_bench_environment_with_ros_localhost_only", expected="does_not_start",
                     peers_before=0, peers_ready=0, peer_velocity_reports=None, ready=False, survived_hold=False,
                     end_returncode=-6, stop_returncode=None, core=True, override_check_passed=True,
                     required_log_text="the same interface may not be selected twice", required_log_text_found=True)
    assert evaluate_case(record)["as_expected"]
    record["required_log_text_found"] = False
    evaluation = evaluate_case(record)
    assert not evaluation["as_expected"]
    assert any("lacks" in reason for reason in evaluation["reasons"])


def test_a_log_text_without_its_result_is_malformed():
    record = _record(required_log_text="x")
    assert not evaluate_case(record)["as_expected"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda record: record.pop("ready"),
        lambda record: record.update(expected="maybe"),
        lambda record: record.update(peers_ready=-1),
        lambda record: record.update(core="no"),
    ],
)
def test_malformed_case_records_are_not_as_expected(mutation):
    record = _record()
    mutation(record)
    assert not evaluate_case(record)["as_expected"]


def test_the_probe_passes_only_when_every_case_is_as_expected():
    good = evaluate_case(_record())
    bad = evaluate_case(_record(peers_ready=3))
    assert summarize_probe([good, good])["gate"] == "pass"
    assert summarize_probe([good, bad])["gate"] == "fail"
    assert summarize_probe([])["gate"] == "fail"
