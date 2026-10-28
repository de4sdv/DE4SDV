"""Evaluator of the soak of the one-process adapter (brittleness check of the design).

baselibs' aborts_upon_exception turns every throw in the adapter process into
an abort, also a throw that a linked library would catch itself on its normal
path. The soak runs the adapter nominally for the planned time, with someipd
and gatewayd, the vehicle-speed provider at 10 Hz, the synthetic frame source
and an independent observer. It passes only when all of these hold:

- The adapter got ready, ran the planned time, left no core, and stopped
  with 0 on SIGTERM by the second LoLa rule.
- Every bench process was alive at every liveness check, and at each check
  the adapter was the only client of the frame stream: the frame assembler
  gives its stream to its newest client.
- gatewayd logged its subscription of the frame event, someipd logged its
  subscription of gatewayd's bridged event, and gatewayd logged no failure
  of its local service instance. One kind of line is a start-up race, not a
  failure: until someipd's subscription takes effect, gatewayd drops each
  frame for lack of a subscriber ("No client subscribed for event"), the
  discard of an unsubscribed event. The runner counts these lines when
  someipd has subscribed and SUBSCRIPTION_SETTLE_S has passed; those are
  the pre-subscription drops. Every later line of that kind, and every other
  failure line, fails the soak.
- ``ros2 node info`` of the adapter node, in the same ROS 2 environment,
  shows exactly the endpoints of a member run: the VelocityReport
  publication and the /parameter_events subscription of rclcpp's time
  source; no parameter services and no /rosout.
- Speed path: each VelocityReport that the observer received pairs with one
  provider sample, in order. Its value is the float32 of the sample's value
  divided by 3.6, and the sample was sent after the adapter subscribed and
  less than half the value repeat time before the receipt. No sample pairs
  twice, and no provider sample between the first and the last paired one
  is missing. The observer received no more VelocityReports than the adapter
  published, and at least MIN_OBSERVED_RATIO of them. Each one has the
  adapter's fixed fields.
- Frame path: the adapter sent frames, with no allocation failure, no send
  failure, no frame without an offer, no oversized frame and no loss of the
  frame stream. The frames it forwarded are, in number and in bytes, the
  first frames of the frame source.

In the nominal soak gatewayd releases each frame sample at once, so one
frame without a free sample slot fails the soak, although the adapter's own
rule handles it (drop and count, GAP-MW-037).

If a library throws on its normal path, the soak fails and the report names
the first named frame below the override: a finding against the one-process
design, not a bench fault.
"""

from __future__ import annotations

import bisect
import json
import math
import re
import struct
from typing import Any, Callable

from de4sdv_score_bench.abort_matrix import BLOCKED, ERROR, FAIL, MISSING, PASS, json_lines, parse_adapter_log
from de4sdv_score_bench.backtrace import (
    check_abort_top_frames,
    first_named_frame_below_override,
    frame_text,
    read_located_frames,
)
from de4sdv_score_bench.node_info import check_member_endpoints

ADAPTER_EXECUTABLE = "de4sdv_score_adapter"
MIN_OBSERVED_RATIO = 0.95
FRAME_PREFIX_BYTES = 4
FLOAT32_MAX = 3.4028234663852886e38

_RUN_KEYS = {
    "planned_duration_s",
    "adapter_ready_monotonic_ns",
    "stop_request_monotonic_ns",
    "early_exit_returncode",
    "stop_returncode",
    "adapter_core_files",
    "provider_values_kmh",
    "gateway",
    "gatewayd_subscribed",
    "liveness_period_s",
    "liveness_checks",
    "adapter_pid",
    "someipd_subscribed",
    "gatewayd_drops_before_subscription",
}
# The fields of a result besides outcome and reasons; each stays None until the evaluation reads it.
_RESULT_FIELDS = (
    "soak_s", "published", "observed_messages", "speed_pairing", "provider_samples_sent", "frames_sent",
    "frames_forwarded", "frame_bytes_read", "frame_source_frames", "frames_allocate_failed",
    "frame_connection_losses", "liveness_checks", "frame_stream_clients", "gatewayd_failures",
    "pre_subscription_drops", "adapter_endpoints", "mw_log_fallback", "rss_kib_first", "rss_kib_last",
    "abort_caller",
)
_GATEWAYD_FAILURE = re.compile(r"\[gatewayd\][^\n]*Failed to[^\n]*")
# gatewayd's drop of a frame while no client (someipd) subscribed its event.
_GATEWAYD_NO_SUBSCRIBER = re.compile(
    r"\[gatewayd\] LocalServiceInstance - Failed to allocate event payload for event \d+: "
    r"No client subscribed for event"
)
# The time after someipd's subscription line within which a drop still
# counts as one before the subscription took effect.
SUBSCRIPTION_SETTLE_S = 1.0
_HEX = re.compile(r"^[0-9a-f]+$")
_FRAME_COUNTERS_ZERO = (
    "frames_allocate_failed",
    "frames_send_failed",
    "frames_not_offered",
    "frames_dropped_oversize",
    "frame_connection_losses",
)


def count_no_subscriber_drops(gatewayd_log_text: str) -> int:
    """The lines with which gatewayd dropped a frame because no client subscribed its event."""
    return len(_GATEWAYD_NO_SUBSCRIBER.findall(gatewayd_log_text))


def float32_bits(value: float) -> str:
    """Big-endian hex of the float32 bit pattern of value."""
    return struct.pack(">f", value).hex()


def _double_from_bits(bits: str) -> float:
    return struct.unpack(">d", bytes.fromhex(bits))[0]


def _is_int(value: Any) -> bool:
    return type(value) is int


def _shape_errors(run: Any) -> list[str]:
    if not isinstance(run, dict) or set(run) != _RUN_KEYS:
        return ["the run record does not have the closed key set"]
    errors = []
    for key in ("planned_duration_s", "liveness_period_s"):
        if not _is_int(run[key]) or run[key] <= 0:
            errors.append(f"{key} is not a positive integer")
    for key in ("adapter_ready_monotonic_ns", "stop_request_monotonic_ns", "early_exit_returncode",
                "stop_returncode"):
        if run[key] is not None and not _is_int(run[key]):
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
    if type(run["gateway"]) is not bool:
        errors.append("gateway is not a boolean")
    for key in ("gatewayd_subscribed", "someipd_subscribed"):
        if run[key] is not None and type(run[key]) is not bool:
            errors.append(f"{key} is not a boolean")
    drops = run["gatewayd_drops_before_subscription"]
    if drops is not None and (not _is_int(drops) or drops < 0):
        errors.append("gatewayd_drops_before_subscription is not a count")
    checks = run["liveness_checks"]
    if not isinstance(checks, list) or not all(
        isinstance(check, dict)
        and set(check) == {"monotonic_ns", "alive", "frame_stream_client_pids"}
        and _is_int(check["monotonic_ns"])
        and isinstance(check["alive"], dict)
        and all(isinstance(name, str) and type(alive) is bool for name, alive in check["alive"].items())
        and (check["frame_stream_client_pids"] is None
             or (isinstance(check["frame_stream_client_pids"], list)
                 and all(_is_int(pid) for pid in check["frame_stream_client_pids"])))
        for check in checks
    ):
        errors.append("liveness_checks is not a list of checks")
    if run["adapter_pid"] is not None and not _is_int(run["adapter_pid"]):
        errors.append("adapter_pid is not an integer")
    return errors


def _last(events: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    matching = [event for event in events if event["event"] == name]
    return matching[-1] if matching else None


def _publishable(value: float) -> bool:
    return math.isfinite(value) and abs(value / 3.6) <= FLOAT32_MAX


def _hex_bits(value: Any, digits: int) -> bool:
    return isinstance(value, str) and len(value) == digits and _HEX.match(value) is not None


def _records(text: str, key: str, source: str,
             valid: Callable[[dict[str, Any]], bool]) -> tuple[list[dict[str, Any]], list[str]]:
    """The JSON records of text that hold key, in order, and an error for each of them that is not valid."""
    records, errors = [], []
    for record in json_lines(text):
        if key not in record:
            continue
        if valid(record):
            records.append(record)
        else:
            errors.append(f"{source} record is malformed: {json.dumps(record)[:120]}")
    return records, errors


def _provider_samples(text: str) -> tuple[list[tuple[int, str, int]], list[str]]:
    """(seq, expected observed bits, send time) of each sample the provider sent and the adapter may publish."""
    records, errors = _records(text, "seq", "a provider", lambda record: (
        _is_int(record.get("seq")) and _hex_bits(record.get("bits"), 16)
        and _is_int(record.get("monotonic_ns")) and isinstance(record.get("send"), str)))
    samples = []
    for record in records:
        value = _double_from_bits(record["bits"])
        if record["send"] == "ok" and _publishable(value):
            samples.append((record["seq"], float32_bits(value / 3.6), record["monotonic_ns"]))
    return samples, errors


def _observed_messages(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    return _records(text, "longitudinal_velocity_bits", "an observer", lambda record: (
        _hex_bits(record.get("longitudinal_velocity_bits"), 8) and _is_int(record.get("receipt_monotonic_ns"))))


def _repeat_window_ns(provider: list[tuple[int, str, int]]) -> int | None:
    """Half the shortest time after which the provider sends the same value again; None when no value repeats."""
    last_sent: dict[str, int] = {}
    shortest = None
    for _seq, bits, sent_ns in provider:
        if bits in last_sent:
            gap = sent_ns - last_sent[bits]
            shortest = gap if shortest is None else min(shortest, gap)
        last_sent[bits] = sent_ns
    return None if shortest is None else shortest // 2


def pair_speed_messages(
    provider: list[tuple[int, str, int]], observed: list[dict[str, Any]], subscribed_ns: int
) -> dict[str, Any]:
    """Pairs each observed VelocityReport, in order, with one provider sample.

    For each message the candidates are the provider samples after the last
    paired one, sent at or before its receipt and within the repeat window;
    the latest candidate with the expected value pairs. A message without a
    candidate stays unpaired: a duplicate, a message out of order, or a
    value that no provider sample explains.
    """
    send_times = [sent_ns for _seq, _bits, sent_ns in provider]
    window_ns = _repeat_window_ns(provider)
    next_index = 0
    pairs: list[tuple[int, int]] = []
    unpaired = 0
    for position, message in enumerate(observed):
        receipt_ns = message["receipt_monotonic_ns"]
        candidate = bisect.bisect_right(send_times, receipt_ns) - 1
        found = None
        while candidate >= next_index:
            if window_ns is not None and receipt_ns - send_times[candidate] > window_ns:
                break
            if provider[candidate][1] == message["longitudinal_velocity_bits"]:
                found = candidate
                break
            candidate -= 1
        if found is None:
            unpaired += 1
            continue
        pairs.append((position, found))
        next_index = found + 1
    gaps = sum(later - earlier - 1 for (_p1, earlier), (_p2, later) in zip(pairs, pairs[1:]))
    latencies = sorted(
        (observed[position]["receipt_monotonic_ns"] - provider[index][2]) / 1e6 for position, index in pairs
    )
    return {
        "paired": len(pairs),
        "unpaired": unpaired,
        "missing_between_paired": gaps,
        "sent_before_subscription": sum(1 for _position, index in pairs if provider[index][2] < subscribed_ns),
        "first_paired_seq": provider[pairs[0][1]][0] if pairs else None,
        "last_paired_seq": provider[pairs[-1][1]][0] if pairs else None,
        "pairing_window_ms": None if window_ns is None else window_ns / 1e6,
        "latency_ms": None
        if not latencies
        else {
            "min": round(latencies[0], 3),
            "p50": round(latencies[len(latencies) // 2], 3),
            "p99": round(latencies[min(len(latencies) - 1, int(len(latencies) * 0.99))], 3),
            "max": round(latencies[-1], 3),
        },
    }


def _frame_source(text: str) -> tuple[list[int], list[str]]:
    records, errors = _records(text, "seq", "a frame source", lambda record: (
        _is_int(record.get("seq")) and _is_int(record.get("size")) and record["size"] >= 0))
    return [record["size"] for record in records], errors


def evaluate_soak(
    run: Any,
    *,
    adapter_log_text: str,
    provider_log_text: str,
    observer_log_text: str,
    frame_source_log_text: str,
    gatewayd_log_text: str,
    node_info_text: str | None,
    backtrace_text: str | None,
    mappings_text: str | None,
) -> dict[str, Any]:
    result: dict[str, Any] = {"outcome": PASS, "reasons": [], **dict.fromkeys(_RESULT_FIELDS)}
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
    result["mw_log_fallback"] = "Fallback to console logging" in adapter_log_text
    if backtrace_text and mappings_text:
        frames = read_located_frames(backtrace_text, mappings_text)
        check = check_abort_top_frames(frames, ADAPTER_EXECUTABLE)
        named = first_named_frame_below_override(frames, check)
        if named is not None:
            result["abort_caller"] = frame_text(named)

    if run["adapter_ready_monotonic_ns"] is None:
        fail(BLOCKED, "the adapter never logged ready")
    if run["early_exit_returncode"] is not None:
        fail(FAIL, f"the adapter ended during the soak with {run['early_exit_returncode']}")
    if run["adapter_core_files"]:
        fail(FAIL, f"the adapter left a core: {', '.join(run['adapter_core_files'])}")
    if result["outcome"] != PASS:
        return result

    if run["stop_request_monotonic_ns"] is None:
        fail(MISSING, "the run record has no stop request time")
    else:
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

    checks = run["liveness_checks"]
    result["liveness_checks"] = len(checks)
    expected_checks = run["planned_duration_s"] // run["liveness_period_s"]
    if len(checks) < expected_checks:
        fail(MISSING, f"{len(checks)} liveness checks, fewer than the {expected_checks} of the planned time")
    dead = sorted({name for check in checks for name, alive in check["alive"].items() if not alive})
    if dead:
        fail(FAIL, f"not alive at a liveness check: {', '.join(dead)}")
    unread = sum(1 for check in checks if check["frame_stream_client_pids"] is None)
    other_clients = [check["frame_stream_client_pids"] for check in checks
                     if check["frame_stream_client_pids"] is not None
                     and check["frame_stream_client_pids"] != [run["adapter_pid"]]]
    result["frame_stream_clients"] = {"checks": len(checks), "unread": unread, "other": len(other_clients)}
    if unread:
        fail(MISSING, f"the clients of the frame stream could not be read at {unread} liveness checks")
    if other_clients:
        fail(FAIL, f"the adapter was not the only client of the frame stream at {len(other_clients)} liveness "
                   f"checks, for example {other_clients[0]}")

    if run["gateway"]:
        failures = _GATEWAYD_FAILURE.findall(gatewayd_log_text)
        others = [line for line in failures if not _GATEWAYD_NO_SUBSCRIBER.search(line)]
        drops = len(failures) - len(others)
        before = run["gatewayd_drops_before_subscription"]
        later_drops = drops - before if before is not None else 0
        result["pre_subscription_drops"] = min(drops, before) if before is not None else None
        result["gatewayd_failures"] = len(others) + max(0, later_drops)
        if run["gatewayd_subscribed"] is not True:
            fail(FAIL, "gatewayd logged no local service instance of the frame event")
        if run["someipd_subscribed"] is not True:
            fail(FAIL, "someipd logged no subscription of gatewayd's bridged frame event")
        if others:
            fail(FAIL, f"gatewayd logged {len(others)} failures, the first: {others[0].strip()[:160]}")
        if before is None:
            if drops:
                fail(MISSING, f"gatewayd dropped {drops} frames for lack of a subscriber, and the run record has no "
                              "count of the drops before the subscription")
        elif later_drops > 0:
            fail(FAIL, f"gatewayd dropped {later_drops} frames for lack of a subscriber after someipd had subscribed")
        elif later_drops < 0:
            fail(ERROR, f"gatewayd's log holds {drops} drops, fewer than the {before} counted at the subscription")

    if node_info_text is None:
        fail(MISSING, "no ros2 node info of the adapter node")
    else:
        endpoints = check_member_endpoints(node_info_text)
        result["adapter_endpoints"] = endpoints["endpoints"]
        if not endpoints["passed"]:
            fail(FAIL, "the adapter node's ROS 2 endpoints are not those of a member run: "
                       + "; ".join(endpoints["reasons"]))

    final = _last(events, "final_status")
    statuses = [event for event in events if event["event"] in ("status", "final_status")]
    if statuses:
        result["rss_kib_first"] = statuses[0].get("rss_kib")
        result["rss_kib_last"] = statuses[-1].get("rss_kib")
    if final is None:
        fail(MISSING, "the adapter logged no final status")
        return result

    # Speed path.
    published = final.get("speed_samples_published")
    result["published"] = published
    provider, provider_errors = _provider_samples(provider_log_text)
    observed, observer_errors = _observed_messages(observer_log_text)
    for errors_of_source in (provider_errors, observer_errors):
        if errors_of_source:
            fail(ERROR, f"{len(errors_of_source)} malformed records; the first: {errors_of_source[0]}")
    result["provider_samples_sent"] = len(provider)
    result["observed_messages"] = len(observed)
    subscribed = next((event for event in events if event["event"] == "speed_proxy_subscribed"), None)
    if not _is_int(published) or published <= 0:
        fail(MISSING, "the adapter published no VelocityReport")
    elif subscribed is None or not _is_int(subscribed.get("monotonic_ns")):
        fail(FAIL, "the adapter logged no subscription of the speed event")
    else:
        pairing = pair_speed_messages(provider, observed, subscribed["monotonic_ns"])
        result["speed_pairing"] = pairing
        if not observed:
            fail(FAIL, f"the observer received none of {published} published VelocityReports")
        if pairing["unpaired"]:
            fail(FAIL, f"{pairing['unpaired']} observed VelocityReports pair with no provider sample in order "
                       "(a duplicate, a reordered message or an unexplained value)")
        if pairing["missing_between_paired"]:
            fail(FAIL, f"{pairing['missing_between_paired']} provider samples are missing between the first and "
                       "the last paired one")
        if pairing["sent_before_subscription"]:
            fail(FAIL, f"{pairing['sent_before_subscription']} observed VelocityReports carry a sample sent before "
                       "the adapter subscribed (a stored sample, first LoLa rule)")
        if len(observed) > published:
            fail(FAIL, f"the observer received {len(observed)} VelocityReports, more than the {published} published")
        if len(observed) < MIN_OBSERVED_RATIO * published:
            fail(FAIL, f"the observer received {len(observed)} of {published} published VelocityReports")
        if published > len(provider):
            fail(FAIL, f"the adapter published {published} VelocityReports from {len(provider)} provider samples")
    off_contract = sum(
        1
        for message in observed
        if message.get("lateral_velocity") != 0.0 or message.get("heading_rate") != 0.0
        or message.get("frame_id") != "base_link"
    )
    if off_contract:
        fail(FAIL, f"{off_contract} VelocityReports differ from the fixed fields of the adapter")
    for key in ("speed_samples_withheld_non_finite", "speed_samples_withheld_out_of_range"):
        if final.get(key):
            fail(FAIL, f"{key} is {final.get(key)} although the provider sent finite values only")

    # Frame path.
    for key in ("frames_sent", "frames_forwarded", "frame_bytes_read", "frames_allocate_failed",
                "frame_connection_losses"):
        result[key] = final.get(key)
    counters = ("frames_sent", "frames_forwarded", "frame_bytes_read", "frame_partial_frames_discarded",
                *_FRAME_COUNTERS_ZERO)
    missing = [key for key in counters if not _is_int(final.get(key))]
    sizes, source_errors = _frame_source(frame_source_log_text)
    if source_errors:
        fail(ERROR, f"{len(source_errors)} malformed records; the first: {source_errors[0]}")
    result["frame_source_frames"] = len(sizes)
    if missing:
        fail(MISSING, f"the final status has no frame counter {', '.join(missing)}")
        return result
    if final["frames_sent"] <= 0:
        fail(FAIL, "the adapter sent no frame")
    for key in _FRAME_COUNTERS_ZERO:
        if final[key]:
            fail(FAIL, f"{key} is {final[key]} in the nominal soak")
    if final["frames_forwarded"] != final["frames_sent"]:
        fail(FAIL, f"the adapter forwarded {final['frames_forwarded']} frames but sent {final['frames_sent']}")
    forwarded = final["frames_forwarded"]
    if forwarded > len(sizes):
        fail(FAIL, f"the adapter forwarded {forwarded} frames, more than the {len(sizes)} of the frame source")
    else:
        expected_bytes = sum(FRAME_PREFIX_BYTES + size for size in sizes[:forwarded])
        next_frame = FRAME_PREFIX_BYTES + sizes[forwarded] if forwarded < len(sizes) else 0
        if not expected_bytes <= final["frame_bytes_read"] <= expected_bytes + max(0, next_frame - 1):
            fail(FAIL, f"the adapter read {final['frame_bytes_read']} bytes; the first {forwarded} frames of the "
                       f"source hold {expected_bytes}")
    if final["frame_partial_frames_discarded"] > 1:
        fail(FAIL, f"{final['frame_partial_frames_discarded']} partial frames were discarded")
    return result
