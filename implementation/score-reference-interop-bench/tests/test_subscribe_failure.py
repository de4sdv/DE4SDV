"""Tests of the evaluator of a refused speed subscription of the adapter.

A refused handler or subscription must neither stay silent nor last: the
adapter logs the refused step, cleans up by the second LoLa rule, and ends
with exit code 5.
"""

from pathlib import Path
import json
import sys

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))

from de4sdv_score_bench.subscribe_failure import evaluate_subscribe_failure  # noqa: E402


def _log(*events: dict) -> str:
    lines = ["a console line that is not JSON"]
    for number, event in enumerate(events):
        lines.append(json.dumps({"monotonic_ns": number, "realtime_ns": number, **event}))
    return "\n".join(lines) + "\n"


GOOD_LOG = _log(
    {"event": "start"},
    {"event": "speed_subscribe_failed", "step": "subscribe_failed", "reason": "Subscribe: binding failure",
     "exit_code": 5},
    {"event": "speed_path_stopped", "result": "proxy_destroyed"},
    {"event": "final_status"},
    {"event": "exit", "code": 5},
)


def _record(**changes) -> dict:
    record = {"provider_sample_slots": 4, "adapter_max_samples": 5, "returncode": 5, "ended_by_itself": True,
              "core": False}
    record.update(changes)
    return record


def test_a_refused_subscription_that_ends_with_code_5_passes():
    result = evaluate_subscribe_failure(_record(), GOOD_LOG)
    assert result["outcome"] == "passBoundedVerification", result["reasons"]


def test_an_adapter_that_runs_on_fails():
    result = evaluate_subscribe_failure(_record(ended_by_itself=False, returncode=0), GOOD_LOG + _log({"event": "ready"}))
    assert result["outcome"] == "failObservedBehavior"
    assert any("did not end by itself" in reason for reason in result["reasons"])


def test_another_exit_code_fails():
    assert evaluate_subscribe_failure(_record(returncode=-6), GOOD_LOG)["outcome"] == "failObservedBehavior"


def test_a_silent_end_fails():
    log = _log({"event": "start"}, {"event": "speed_path_stopped", "result": "proxy_destroyed"},
               {"event": "exit", "code": 5})
    assert evaluate_subscribe_failure(_record(), log)["outcome"] == "failObservedBehavior"


def test_another_refused_step_fails():
    log = GOOD_LOG.replace('"step": "subscribe_failed"', '"step": "state_handler_failed"')
    assert evaluate_subscribe_failure(_record(), log)["outcome"] == "failObservedBehavior"


def test_a_core_fails():
    assert evaluate_subscribe_failure(_record(core=True), GOOD_LOG)["outcome"] == "failObservedBehavior"


def test_a_malformed_record_is_error_evidence():
    assert evaluate_subscribe_failure({"returncode": 5}, GOOD_LOG)["outcome"] == "errorEvidence"
