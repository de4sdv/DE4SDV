"""Evaluator of the refused speed subscription of the one-process adapter.

When mw::com refuses the state handler, the receive handler or the
subscription of the speed proxy, the adapter does not retry in the process
and does not run on silently. It logs the refused step, cleans up by the
second LoLa rule (the proxy is not subscribed, so it is destroyed) and ends
with exit code 5, so the Launch Manager sees the failure.

The check makes the provider offer fewer sample slots than the adapter asks
for, so LoLa refuses the subscription. It passes when the adapter ended by
itself with exit code 5, logged the refused step, stopped its speed path by
rule 2, never logged ready, and left no core.
"""

from __future__ import annotations

from typing import Any

from de4sdv_score_bench.abort_matrix import ERROR, FAIL, PASS, parse_adapter_log

EXIT_SPEED_SUBSCRIBE_FAILED = 5

_RECORD_KEYS = {"provider_sample_slots", "adapter_max_samples", "returncode", "ended_by_itself", "core"}


def evaluate_subscribe_failure(record: Any, adapter_log_text: str) -> dict[str, Any]:
    if not isinstance(record, dict) or set(record) != _RECORD_KEYS:
        return {"outcome": ERROR, "reasons": ["the record does not have the closed key set"]}
    reasons = []
    events = parse_adapter_log(adapter_log_text)
    names = [event["event"] for event in events]
    if not record["ended_by_itself"]:
        reasons.append("the adapter did not end by itself")
    if record["returncode"] != EXIT_SPEED_SUBSCRIBE_FAILED:
        reasons.append(f"the adapter ended with {record['returncode']}, not {EXIT_SPEED_SUBSCRIBE_FAILED}")
    refused = [event for event in events if event["event"] == "speed_subscribe_failed"]
    if not refused:
        reasons.append("the adapter logged no refused subscription")
    elif refused[0].get("step") != "subscribe_failed":
        reasons.append(f"the refused step is {refused[0].get('step')}, not subscribe_failed")
    stopped = [event for event in events if event["event"] == "speed_path_stopped"]
    if not stopped or stopped[-1].get("result") != "proxy_destroyed":
        reasons.append("the speed path did not stop by the second LoLa rule")
    exits = [event for event in events if event["event"] == "exit"]
    if not exits or exits[-1].get("code") != EXIT_SPEED_SUBSCRIBE_FAILED:
        reasons.append("the adapter logged no exit with code 5")
    if "ready" in names:
        reasons.append("the adapter logged ready")
    if record["core"]:
        reasons.append("the adapter left a core")
    return {"outcome": FAIL if reasons else PASS, "reasons": reasons}
