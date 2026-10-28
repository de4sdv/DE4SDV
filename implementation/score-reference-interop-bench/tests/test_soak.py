"""Tests of the soak evaluator of the one-process adapter (brittleness check of the design).

The adapter runs nominally for the planned time: the vehicle-speed provider
sends finite samples over mw::com at 10 Hz, an independent ROS 2 observer
receives the VelocityReports, frames flow from the synthetic frame source
into the frame event that gatewayd subscribes. Any throw on a normal path of
a linked library aborts the adapter (REQ-MW-018), so a clean soak shows that
no such throw happened in that time. The data must pair one to one and in
order: no duplicate, no reorder, no gap, no stored sample, no frame lost.
"""

from pathlib import Path
import copy
import json
import struct
import sys

import pytest

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))

from de4sdv_score_bench.soak import evaluate_soak, float32_bits, pair_speed_messages  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SECOND = 1_000_000_000
PERIOD = 100_000_000
T0 = 1_000 * SECOND
VALUES = [0.0, 10.0, 36.0, 50.0, 72.0, 100.0, 130.0, 20.5]
SENT = 6040  # provider samples
SUBSCRIBED_AFTER = 25  # the adapter subscribed after this sample
FIRST_PUBLISHED = 26
LAST_PUBLISHED = 6035
FRAME_SIZES = (16, 200, 800, 1100, 2044, 64, 512)
FRAMES_SENT = 6000
PLANNED_S = 600
ADAPTER_PID = 4242


def _send_ns(seq: int) -> int:
    return T0 + seq * PERIOD


def _value(seq: int) -> float:
    return VALUES[(seq - 1) % len(VALUES)]


def _double_bits(value: float) -> str:
    return struct.pack(">d", value).hex()


def _frame_size(seq: int) -> int:
    return FRAME_SIZES[seq % len(FRAME_SIZES)]


def _frame_bytes(count: int) -> int:
    return sum(4 + _frame_size(seq) for seq in range(1, count + 1))


def _final_status(**changes) -> dict:
    status = {
        "event": "final_status", "speed_samples_published": LAST_PUBLISHED - FIRST_PUBLISHED + 1, "rss_kib": 14700,
        "frames_sent": FRAMES_SENT, "frames_forwarded": FRAMES_SENT, "frame_bytes_read": _frame_bytes(FRAMES_SENT),
        "frame_partial_frames_discarded": 0, "frames_allocate_failed": 0, "frames_send_failed": 0,
        "frames_not_offered": 0, "frames_dropped_oversize": 0, "frame_connection_losses": 0,
        "speed_samples_withheld_non_finite": 0, "speed_samples_withheld_out_of_range": 0,
    }
    status.update(changes)
    return status


def _adapter_log(*, final: dict | None = None, include_exit: bool = True, subscribed: bool = True) -> str:
    events = [
        (T0, {"event": "start", "fault_signals": {"rclcpp_internal": 35, "adapter_code": 36, "libstdcxx": 37}}),
        (T0 + 1, {"event": "ros_node_ready", "rmw": "rmw_cyclonedds_cpp"}),
    ]
    if subscribed:
        events.append((_send_ns(SUBSCRIBED_AFTER) + PERIOD // 2, {"event": "speed_proxy_subscribed"}))
    events += [
        (_send_ns(SUBSCRIBED_AFTER) + PERIOD // 2 + 1, {"event": "ready"}),
        (_send_ns(600), {"event": "status", "rss_kib": 14200}),
        (_send_ns(LAST_PUBLISHED) + PERIOD // 2, {"event": "stop_requested"}),
        (_send_ns(LAST_PUBLISHED) + PERIOD // 2 + 1, {"event": "speed_path_stopped", "result": "proxy_destroyed"}),
        (_send_ns(LAST_PUBLISHED) + PERIOD // 2 + 2, final or _final_status()),
    ]
    if include_exit:
        events.append((_send_ns(LAST_PUBLISHED) + PERIOD // 2 + 3, {"event": "exit", "code": 0}))
    lines = ["mw::log initialization error: an example console line that is not JSON"]
    for monotonic_ns, event in events:
        lines.append(json.dumps({"monotonic_ns": monotonic_ns, "realtime_ns": 0, **event}, separators=(",", ":")))
    return "\n".join(lines) + "\n"


def _provider_log() -> str:
    lines = [json.dumps({"event": "offered", "pid": 1, "monotonic_ns": T0})]
    for seq in range(1, SENT + 1):
        lines.append(json.dumps({"seq": seq, "speed_kmh": _value(seq), "bits": _double_bits(_value(seq)),
                                 "monotonic_ns": _send_ns(seq), "realtime_ns": seq, "send": "ok"}))
    return "\n".join(lines) + "\n"


def _message(seq: int, latency_ns: int = 1_000_000, **changes) -> dict:
    message = {"receipt_monotonic_ns": _send_ns(seq) + latency_ns, "stamp_ns": 0,
               "longitudinal_velocity_bits": float32_bits(_value(seq) / 3.6), "lateral_velocity": 0.0,
               "heading_rate": 0.0, "frame_id": "base_link"}
    message.update(changes)
    return message


def _observer_lines(seqs) -> list[str]:
    return [json.dumps(_message(seq)) for seq in seqs]


def _observer_log(lines: list[str] | None = None) -> str:
    lines = _observer_lines(range(FIRST_PUBLISHED, LAST_PUBLISHED + 1)) if lines is None else lines
    return "\n".join(lines) + ("\n" if lines else "")


def _frame_source_log() -> str:
    lines = [json.dumps({"event": "client_connected", "monotonic_ns": T0})]
    for seq in range(1, FRAMES_SENT + 3):
        lines.append(json.dumps({"seq": seq, "size": _frame_size(seq), "monotonic_ns": T0 + seq, "sha256": "0"}))
    return "\n".join(lines) + "\n"


GATEWAYD_LOG = ("[gatewayd] Connected to someipd over the mw::com IPC binding\n"
                "[gatewayd] LocalServiceInstance created for instance specifier: de4sdv/aebs_signal_frame\n")
NODE_INFO = (FIXTURES / "ros2_node_info_member_run.txt").read_text(encoding="utf-8")
NODE_INFO_WITH_SERVICES = (FIXTURES / "ros2_node_info_parameter_services.txt").read_text(encoding="utf-8")


def _run(planned_s: int = PLANNED_S) -> dict:
    ready = _send_ns(SUBSCRIBED_AFTER) + PERIOD // 2 + 1
    return {
        "planned_duration_s": planned_s,
        "adapter_ready_monotonic_ns": ready,
        "stop_request_monotonic_ns": ready + planned_s * SECOND + 1,
        "early_exit_returncode": None,
        "stop_returncode": 0,
        "adapter_core_files": [],
        "provider_values_kmh": VALUES,
        "gateway": True,
        "gatewayd_subscribed": True,
        "liveness_period_s": 10,
        "liveness_checks": [
            {"monotonic_ns": ready + (number + 1) * 10 * SECOND,
             "alive": {"someipd": True, "gatewayd": True, "frame_source": True, "observer": True, "provider": True,
                       "adapter": True},
             "frame_stream_client_pids": [ADAPTER_PID]}
            for number in range(planned_s // 10)
        ],
        "adapter_pid": ADAPTER_PID,
    }


def _evaluate(run: dict | None = None, *, adapter_log: str | None = None, observer_log: str | None = None,
              gatewayd_log: str = GATEWAYD_LOG, provider_log: str | None = None, backtrace: str | None = None,
              mappings: str | None = None, node_info: str | None = NODE_INFO) -> dict:
    return evaluate_soak(
        _run() if run is None else run,
        adapter_log_text=_adapter_log() if adapter_log is None else adapter_log,
        provider_log_text=_provider_log() if provider_log is None else provider_log,
        observer_log_text=_observer_log() if observer_log is None else observer_log,
        frame_source_log_text=_frame_source_log(),
        gatewayd_log_text=gatewayd_log,
        node_info_text=node_info,
        backtrace_text=backtrace,
        mappings_text=mappings,
    )


def test_float32_bits_is_the_single_precision_pattern():
    assert float32_bits(10.0) == "41200000"
    assert float32_bits(20.0) == struct.pack(">f", 20.0).hex()


def test_a_clean_soak_passes():
    result = _evaluate()
    assert result["outcome"] == "passBoundedVerification", result["reasons"]
    assert result["soak_s"] >= PLANNED_S
    assert result["observed_messages"] == LAST_PUBLISHED - FIRST_PUBLISHED + 1
    pairing = result["speed_pairing"]
    assert pairing["paired"] == result["observed_messages"]
    assert pairing["first_paired_seq"] == FIRST_PUBLISHED and pairing["last_paired_seq"] == LAST_PUBLISHED
    assert pairing["unpaired"] == pairing["missing_between_paired"] == pairing["sent_before_subscription"] == 0
    assert pairing["latency_ms"]["max"] == 1.0
    assert pairing["pairing_window_ms"] == 400.0
    assert result["adapter_endpoints"]["Service Servers"] == {}


# The bad records that the independent assurance probe built against the
# earlier evaluator; each one must fail now.

def test_duplicated_observer_lines_fail():
    lines = _observer_lines(range(FIRST_PUBLISHED, LAST_PUBLISHED + 1))
    result = _evaluate(observer_log=_observer_log(lines + lines))
    assert result["outcome"] == "failObservedBehavior"
    assert result["speed_pairing"]["unpaired"] == len(lines)


def test_observer_lines_in_reverse_order_fail():
    lines = _observer_lines(range(FIRST_PUBLISHED, LAST_PUBLISHED + 1))
    result = _evaluate(observer_log=_observer_log(list(reversed(lines))))
    assert result["outcome"] == "failObservedBehavior"
    assert result["speed_pairing"]["unpaired"] == len(lines) - 1


def test_one_stored_value_repeated_fails():
    first = json.dumps(_message(FIRST_PUBLISHED))
    result = _evaluate(observer_log=_observer_log([first] * (LAST_PUBLISHED - FIRST_PUBLISHED + 1)))
    assert result["outcome"] == "failObservedBehavior"


def test_an_empty_observer_log_fails():
    result = _evaluate(observer_log="")
    assert result["outcome"] == "failObservedBehavior"


def test_no_frame_sent_with_allocation_failures_and_stream_losses_fails():
    final = _final_status(frames_sent=0, frames_allocate_failed=500, frame_connection_losses=7)
    result = _evaluate(adapter_log=_adapter_log(final=final))
    assert result["outcome"] == "failObservedBehavior"
    assert any("sent no frame" in reason for reason in result["reasons"])
    assert any("frames_allocate_failed is 500" in reason for reason in result["reasons"])
    assert any("frame_connection_losses is 7" in reason for reason in result["reasons"])


def test_an_adapter_core_fails():
    run = _run()
    run["adapter_core_files"] = ["core.de4sdv_score_ad.1"]
    assert _evaluate(run)["outcome"] == "failObservedBehavior"


def test_an_early_exit_fails_and_names_the_first_named_frame_below_the_override():
    run = _run()
    run["early_exit_returncode"] = -6
    run["stop_returncode"] = None
    run["adapter_core_files"] = ["core.de4sdv_score_ad.77"]
    result = _evaluate(run, adapter_log=_adapter_log(include_exit=False),
                       backtrace=(FIXTURES / "gdb_bt_fastdds_shm_aarch64.txt").read_text(encoding="utf-8"),
                       mappings=(FIXTURES / "gdb_mappings_fastdds_aarch64.txt").read_text(encoding="utf-8"))
    assert result["outcome"] == "failObservedBehavior"
    assert "SharedMemTransport::CreateInputChannelResource in /opt/ros/humble/lib/libfastrtps" in result["abort_caller"]


def test_a_shorter_soak_than_planned_is_inconclusive():
    run = _run()
    run["stop_request_monotonic_ns"] = run["adapter_ready_monotonic_ns"] + 60 * SECOND
    assert _evaluate(run)["outcome"] == "inconclusiveMissingEvidence"


def test_a_run_record_without_a_stop_request_time_is_inconclusive_and_raises_nothing():
    run = _run()
    run["stop_request_monotonic_ns"] = None
    result = _evaluate(run)
    assert result["outcome"] == "inconclusiveMissingEvidence"
    assert any("stop request" in reason for reason in result["reasons"])


def test_an_empty_run_record_is_error_evidence():
    assert _evaluate({})["outcome"] == "errorEvidence"


# Further conditions of a pass.

def test_a_process_that_died_at_a_liveness_check_fails():
    run = _run()
    run["liveness_checks"][30]["alive"]["gatewayd"] = False
    result = _evaluate(run)
    assert result["outcome"] == "failObservedBehavior"
    assert any("gatewayd" in reason for reason in result["reasons"])


def test_a_second_client_of_the_frame_stream_fails():
    run = _run()
    run["liveness_checks"][7]["frame_stream_client_pids"] = [ADAPTER_PID, 999]
    result = _evaluate(run)
    assert result["outcome"] == "failObservedBehavior"
    assert result["frame_stream_clients"]["other"] == 1


def test_frame_stream_clients_that_could_not_be_read_are_inconclusive():
    run = _run()
    run["liveness_checks"][3]["frame_stream_client_pids"] = None
    assert _evaluate(run)["outcome"] == "inconclusiveMissingEvidence"


def test_too_few_liveness_checks_are_inconclusive():
    run = _run()
    run["liveness_checks"] = run["liveness_checks"][:10]
    assert _evaluate(run)["outcome"] == "inconclusiveMissingEvidence"


def test_a_gatewayd_subscription_failure_fails_even_with_the_created_line():
    log = GATEWAYD_LOG + "[gatewayd] LocalServiceInstance - Failed to subscribe event 0: binding failure\n"
    result = _evaluate(gatewayd_log=log)
    assert result["outcome"] == "failObservedBehavior"
    assert result["gatewayd_failures"] == 1


def test_a_gatewayd_without_its_local_service_instance_fails():
    run = _run()
    run["gatewayd_subscribed"] = False
    assert _evaluate(run)["outcome"] == "failObservedBehavior"


def test_parameter_services_on_the_adapter_node_fail_the_soak():
    result = _evaluate(node_info=NODE_INFO_WITH_SERVICES)
    assert result["outcome"] == "failObservedBehavior"
    assert any("member run" in reason for reason in result["reasons"])


def test_a_soak_without_the_node_info_is_inconclusive():
    assert _evaluate(node_info=None)["outcome"] == "inconclusiveMissingEvidence"


def test_a_published_stored_sample_fails():
    lines = _observer_lines(range(SUBSCRIBED_AFTER, LAST_PUBLISHED + 1))
    final = _final_status(speed_samples_published=len(lines))
    result = _evaluate(adapter_log=_adapter_log(final=final), observer_log=_observer_log(lines))
    assert result["outcome"] == "failObservedBehavior"
    assert result["speed_pairing"]["sent_before_subscription"] == 1


def test_a_missing_sample_between_two_paired_ones_fails():
    lines = _observer_lines([seq for seq in range(FIRST_PUBLISHED, LAST_PUBLISHED + 1) if seq != 3000])
    result = _evaluate(observer_log=_observer_log(lines))
    assert result["outcome"] == "failObservedBehavior"
    assert result["speed_pairing"]["missing_between_paired"] == 1


def test_more_observed_than_published_fails():
    final = _final_status(speed_samples_published=100)
    result = _evaluate(adapter_log=_adapter_log(final=final))
    assert result["outcome"] == "failObservedBehavior"
    assert any("more than the 100 published" in reason for reason in result["reasons"])


def test_a_value_that_no_provider_sample_explains_fails():
    lines = _observer_lines(range(FIRST_PUBLISHED, LAST_PUBLISHED + 1))
    lines[100] = json.dumps(_message(FIRST_PUBLISHED + 100, longitudinal_velocity_bits=float32_bits(99.0)))
    result = _evaluate(observer_log=_observer_log(lines))
    assert result["outcome"] == "failObservedBehavior"
    assert result["speed_pairing"]["unpaired"] == 1


def test_a_message_that_pairs_only_beyond_the_repeat_window_fails():
    # Received 900 ms after its sample: the same value came again 800 ms
    # after it, so the pairing would not be unique.
    lines = _observer_lines(range(FIRST_PUBLISHED, LAST_PUBLISHED + 1))
    lines[200] = json.dumps(_message(FIRST_PUBLISHED + 200, latency_ns=900_000_000))
    result = _evaluate(observer_log=_observer_log(lines))
    assert result["outcome"] == "failObservedBehavior"


def test_a_message_off_the_fixed_fields_fails():
    lines = _observer_lines(range(FIRST_PUBLISHED, LAST_PUBLISHED + 1))
    lines[5] = json.dumps(_message(FIRST_PUBLISHED + 5, frame_id="map"))
    assert _evaluate(observer_log=_observer_log(lines))["outcome"] == "failObservedBehavior"


def test_too_few_observed_messages_fail():
    lines = _observer_lines(range(FIRST_PUBLISHED, FIRST_PUBLISHED + 1000))
    assert _evaluate(observer_log=_observer_log(lines))["outcome"] == "failObservedBehavior"


def test_no_published_sample_is_missing_evidence():
    final = _final_status(speed_samples_published=0)
    result = _evaluate(adapter_log=_adapter_log(final=final), observer_log="")
    assert result["outcome"] == "inconclusiveMissingEvidence"


def test_an_adapter_that_never_subscribed_fails():
    assert _evaluate(adapter_log=_adapter_log(subscribed=False))["outcome"] == "failObservedBehavior"


def test_an_adapter_that_never_got_ready_blocks_the_soak():
    run = _run()
    run["adapter_ready_monotonic_ns"] = None
    assert _evaluate(run)["outcome"] == "blockedTargetRuntime"


def test_an_unclean_stop_fails():
    run = _run()
    run["stop_returncode"] = 3
    assert _evaluate(run)["outcome"] == "failObservedBehavior"


def test_a_missing_exit_event_fails():
    assert _evaluate(adapter_log=_adapter_log(include_exit=False))["outcome"] == "failObservedBehavior"


def test_one_frame_allocation_failure_fails_the_nominal_soak():
    final = _final_status(frames_allocate_failed=1)
    result = _evaluate(adapter_log=_adapter_log(final=final))
    assert result["outcome"] == "failObservedBehavior"
    assert result["frames_allocate_failed"] == 1


def test_frame_bytes_that_are_not_the_first_frames_of_the_source_fail():
    final = _final_status(frame_bytes_read=_frame_bytes(FRAMES_SENT) - 1)
    assert _evaluate(adapter_log=_adapter_log(final=final))["outcome"] == "failObservedBehavior"


def test_a_partly_read_frame_at_the_stop_passes():
    final = _final_status(frame_bytes_read=_frame_bytes(FRAMES_SENT) + 3, frame_partial_frames_discarded=1)
    result = _evaluate(adapter_log=_adapter_log(final=final))
    assert result["outcome"] == "passBoundedVerification", result["reasons"]


def test_forwarded_frames_that_were_not_all_sent_fail():
    final = _final_status(frames_sent=FRAMES_SENT - 1)
    assert _evaluate(adapter_log=_adapter_log(final=final))["outcome"] == "failObservedBehavior"


def test_a_final_status_without_the_forwarded_count_is_inconclusive():
    final = _final_status()
    del final["frames_forwarded"]
    assert _evaluate(adapter_log=_adapter_log(final=final))["outcome"] == "inconclusiveMissingEvidence"


def test_a_malformed_provider_record_is_error_evidence():
    provider = _provider_log() + json.dumps({"seq": "7", "bits": "zz", "monotonic_ns": 1, "send": "ok"}) + "\n"
    assert _evaluate(provider_log=provider)["outcome"] == "errorEvidence"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda run: run.update(planned_duration_s="600"),
        lambda run: run.update(unexpected=True),
        lambda run: run.update(gateway="yes"),
        lambda run: run["liveness_checks"].append({"monotonic_ns": 1}),
        lambda run: run["liveness_checks"][0].update(frame_stream_client_pids=["4242"]),
        lambda run: run.update(adapter_pid="4242"),
    ],
)
def test_malformed_run_records_are_error_evidence(mutation):
    run = copy.deepcopy(_run())
    mutation(run)
    assert _evaluate(run)["outcome"] == "errorEvidence"


def test_the_pairing_takes_the_latest_matching_sample_in_order():
    provider = [(1, "aa", 100), (2, "bb", 200), (3, "aa", 300), (4, "bb", 400)]
    observed = [{"receipt_monotonic_ns": 310, "longitudinal_velocity_bits": "aa"},
                {"receipt_monotonic_ns": 410, "longitudinal_velocity_bits": "bb"}]
    pairing = pair_speed_messages(provider, observed, subscribed_ns=250)
    assert pairing["first_paired_seq"] == 3 and pairing["last_paired_seq"] == 4
    assert pairing["unpaired"] == 0 and pairing["missing_between_paired"] == 0
