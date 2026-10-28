"""Tests of the gdb backtrace reader of the REQ-MW-018 abort matrix.

The matrix accepts an abort only when the core's crashing thread shows the
signal delivery, then ``abort``, then ``__cxa_allocate_exception`` of the
adapter executable (baselibs' override), then the expected thrower.
"""

from pathlib import Path
import sys

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))

from de4sdv_score_bench.backtrace import (  # noqa: E402
    Frame,
    check_abort_top_frames,
    parse_gdb_backtrace,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _frames(name: str) -> list[Frame]:
    return parse_gdb_backtrace((FIXTURES / name).read_text(encoding="utf-8"))


def test_parses_frames_with_and_without_addresses_and_libraries():
    frames = _frames("gdb_bt_libstdcxx_x86_64.txt")
    assert [frame.index for frame in frames] == list(range(10))
    assert frames[0].function == "__pthread_kill_implementation"
    assert frames[0].library is None
    assert frames[5].function == "__cxa_allocate_exception"
    assert frames[5].library is None
    assert frames[6].function == "std::__throw_out_of_range_fmt"
    assert frames[6].library == "/lib/x86_64-linux-gnu/libstdc++.so.6"


def test_a_repeated_frame_zero_is_read_once():
    frames = _frames("gdb_bt_libstdcxx_x86_64.txt")
    assert sum(1 for frame in frames if frame.index == 0) == 1


def test_unknown_function_is_kept_as_question_marks():
    frames = _frames("gdb_bt_fastdds_shm_aarch64.txt")
    assert frames[5].function == "??"
    assert frames[5].library == "/opt/ros/humble/lib/libfastrtps.so.2.6"


def test_function_name_keeps_namespaces_and_drops_the_argument_list():
    frames = _frames("gdb_bt_fastdds_shm_aarch64.txt")
    assert frames[9].function == "eprosima::fastdds::rtps::SharedMemTransport::CreateInputChannelResource"


def test_accepts_glibc_frames_with_debug_symbols():
    check = check_abort_top_frames(_frames("gdb_bt_libstdcxx_x86_64.txt"))
    assert check.passed, check.reasons
    assert check.override_frame.library is None
    assert check.caller_frame.function == "std::__throw_out_of_range_fmt"


def test_accepts_stripped_glibc_frames():
    check = check_abort_top_frames(_frames("gdb_bt_stripped_libc_rclcpp.txt"))
    assert check.passed, check.reasons
    assert check.caller_frame.library == "/opt/ros/humble/lib/librclcpp.so"


def test_rejects_an_abort_through_std_terminate():
    check = check_abort_top_frames(_frames("gdb_bt_libstdcxx_own_allocation.txt"))
    assert not check.passed
    assert any("__cxa_allocate_exception" in reason for reason in check.reasons)


def test_rejects_the_allocation_function_of_libstdcxx_itself():
    frames = [
        Frame(0, "raise", "/lib/x86_64-linux-gnu/libc.so.6"),
        Frame(1, "abort", "/lib/x86_64-linux-gnu/libc.so.6"),
        Frame(2, "__cxa_allocate_exception", "/lib/x86_64-linux-gnu/libstdc++.so.6"),
        Frame(3, "std::__throw_out_of_range_fmt", "/lib/x86_64-linux-gnu/libstdc++.so.6"),
    ]
    check = check_abort_top_frames(frames)
    assert not check.passed
    assert any("executable" in reason for reason in check.reasons)


def test_rejects_a_frame_other_than_signal_delivery_above_abort():
    frames = [
        Frame(0, "raise", None),
        Frame(1, "some_handler", None),
        Frame(2, "abort", None),
        Frame(3, "__cxa_allocate_exception", None),
        Frame(4, "caller", None),
    ]
    check = check_abort_top_frames(frames)
    assert not check.passed


def test_rejects_an_empty_backtrace():
    check = check_abort_top_frames([])
    assert not check.passed
    assert check.caller_frame is None


def test_rejects_a_backtrace_that_ends_at_the_override():
    frames = [Frame(0, "abort", None), Frame(1, "__cxa_allocate_exception", None)]
    check = check_abort_top_frames(frames)
    assert not check.passed
    assert any("caller" in reason for reason in check.reasons)


def test_accepts_unnamed_libc_frames_of_the_signal_delivery():
    frames = [
        Frame(0, "??", "/lib/x86_64-linux-gnu/libc.so.6"),
        Frame(1, "raise", "/lib/x86_64-linux-gnu/libc.so.6"),
        Frame(2, "abort", "/lib/x86_64-linux-gnu/libc.so.6"),
        Frame(3, "__cxa_allocate_exception", None),
        Frame(4, "std::__throw_out_of_range_fmt", "/lib/x86_64-linux-gnu/libstdc++.so.6"),
    ]
    assert check_abort_top_frames(frames).passed


def test_rejects_an_unnamed_frame_outside_libc_above_abort():
    frames = [
        Frame(0, "??", "/opt/ros/humble/lib/librclcpp.so"),
        Frame(1, "abort", "/lib/x86_64-linux-gnu/libc.so.6"),
        Frame(2, "__cxa_allocate_exception", None),
        Frame(3, "caller", None),
    ]
    assert not check_abort_top_frames(frames).passed
