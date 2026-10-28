"""Tests of the gdb backtrace reader of the REQ-MW-018 abort matrix.

The matrix accepts an abort only when the core's crashing thread shows the
signal delivery, then ``abort``, then ``__cxa_allocate_exception`` at an
address inside the adapter executable (baselibs' override), then the
expected thrower. Each frame is located by its address in the core's
mappings, not by the text form of gdb's line.
"""

from pathlib import Path
import sys

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))

from de4sdv_score_bench.backtrace import (  # noqa: E402
    Frame,
    check_abort_top_frames,
    first_named_frame_below_override,
    frame_text,
    lies_in,
    locate_frames,
    object_name,
    parse_gdb_backtrace,
    parse_gdb_mappings,
    read_located_frames,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"
EXECUTABLE = "de4sdv_score_adapter"
LIBC = "/usr/lib/x86_64-linux-gnu/libc.so.6"
LIBSTDCXX = "/usr/lib/x86_64-linux-gnu/libstdc++.so.6.0.30"
ADAPTER = "/bench/bin/de4sdv_score_adapter"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _located(bt_name: str, mappings_name: str) -> list[Frame]:
    return read_located_frames(_fixture(bt_name), _fixture(mappings_name))


def _frame(index: int, function: str, objfile: str | None, library: str | None = None, source: str | None = None,
           pc: int | None = 0x1000) -> Frame:
    return Frame(index=index, function=function, library=library, pc=pc, objfile=objfile, source=source)


def test_parses_frames_with_and_without_addresses_and_libraries():
    frames = parse_gdb_backtrace(_fixture("gdb_bt_libstdcxx_x86_64.txt"))
    assert [frame.index for frame in frames] == list(range(10))
    assert frames[0].function == "__pthread_kill_implementation"
    assert frames[0].pc is None
    assert frames[5].function == "__cxa_allocate_exception"
    assert frames[5].pc == 0x000055D4C1A2B6A9
    assert frames[6].function == "std::__throw_out_of_range_fmt"
    assert frames[6].library == "/lib/x86_64-linux-gnu/libstdc++.so.6"
    assert frames[7].source == "/home/runner/work/src/fault_hook.cpp"


def test_an_inlined_frame_takes_the_address_of_the_frame_above_it():
    text = """#3  0x000055cce0cd4819 in __cxa_allocate_exception ()
#5  0x000055cce0ced4c8 in std::vector<int, std::allocator<int> >::_M_range_check (__n=<optimized out>) at /usr/include/c++/12/bits/stl_vector.h:1150
#6  std::vector<int, std::allocator<int> >::at (__n=<optimized out>) at /usr/include/c++/12/bits/stl_vector.h:1175
#7  de4sdv::score_adapter::fault_hook::ThrowInsideLibstdcxx[abi:cxx11]() () at /ws/src/fault_hook.cpp:34
"""
    frames = parse_gdb_backtrace(text)
    assert [frame.pc for frame in frames[1:]] == [0x000055CCE0CED4C8] * 3
    assert frames[2].function == "std::vector<int, std::allocator<int> >::at"


def test_a_repeated_frame_zero_is_read_once():
    frames = parse_gdb_backtrace(_fixture("gdb_bt_libstdcxx_x86_64.txt"))
    assert sum(1 for frame in frames if frame.index == 0) == 1


def test_unknown_function_is_kept_as_question_marks():
    frames = parse_gdb_backtrace(_fixture("gdb_bt_fastdds_shm_aarch64.txt"))
    assert frames[5].function == "??"
    assert frames[5].library == "/opt/ros/humble/lib/libfastrtps.so.2.6"


def test_function_name_keeps_namespaces_and_drops_the_argument_list():
    frames = parse_gdb_backtrace(_fixture("gdb_bt_fastdds_shm_aarch64.txt"))
    assert frames[9].function == "eprosima::fastdds::rtps::SharedMemTransport::CreateInputChannelResource"


def test_reads_the_mappings_of_info_proc_mappings_with_and_without_permissions():
    mappings = parse_gdb_mappings(_fixture("gdb_mappings_libstdcxx_x86_64.txt"))
    assert len(mappings) == 7
    assert mappings[0].start == 0x55D4C1A00000 and mappings[0].end == 0x55D4C1A20000
    assert mappings[4].objfile == LIBSTDCXX
    newer_gdb = "      0x55d4c1a00000     0x55d4c1a20000    0x20000        0x0  r--p   /bench/bin/de4sdv_score_adapter\n"
    assert parse_gdb_mappings(newer_gdb)[0].objfile == "/bench/bin/de4sdv_score_adapter"


def test_locates_each_frame_by_its_address():
    frames = _located("gdb_bt_libstdcxx_x86_64.txt", "gdb_mappings_libstdcxx_x86_64.txt")
    assert frames[0].objfile is None  # no address in the text
    assert lies_in(frames[4], "libc.so")
    assert lies_in(frames[5], EXECUTABLE)
    assert frames[6].objfile == LIBSTDCXX
    assert lies_in(frames[9], "librclcpp.so")


def test_object_names_compare_a_link_with_its_target():
    assert object_name("/lib/x86_64-linux-gnu/libstdc++.so.6") == object_name(LIBSTDCXX) == "libstdc++.so"
    assert object_name("/opt/ros/humble/lib/libfastrtps.so.2.6") == "libfastrtps.so"
    assert object_name(ADAPTER) == EXECUTABLE


def test_accepts_glibc_frames_with_debug_symbols():
    frames = _located("gdb_bt_libstdcxx_x86_64.txt", "gdb_mappings_libstdcxx_x86_64.txt")
    check = check_abort_top_frames(frames, EXECUTABLE)
    assert check.passed, check.reasons
    assert check.caller_frame.function == "std::__throw_out_of_range_fmt"
    assert frame_text(check.caller_frame) == f"std::__throw_out_of_range_fmt in {LIBSTDCXX}"


def test_accepts_stripped_glibc_frames():
    frames = _located("gdb_bt_stripped_libc_rclcpp.txt", "gdb_mappings_x86_64_ros.txt")
    check = check_abort_top_frames(frames, EXECUTABLE)
    assert check.passed, check.reasons
    assert lies_in(check.caller_frame, "librclcpp.so")


def test_the_override_must_lie_in_the_named_executable():
    frames = _located("gdb_bt_stripped_libc_rclcpp.txt", "gdb_mappings_x86_64_ros.txt")
    check = check_abort_top_frames(frames, "de4sdv_score_adapter_no_abort_control")
    assert not check.passed
    assert any("not in the executable" in reason for reason in check.reasons)


def test_rejects_an_abort_through_std_terminate():
    frames = _located("gdb_bt_libstdcxx_own_allocation.txt", "gdb_mappings_x86_64_ros.txt")
    check = check_abort_top_frames(frames, EXECUTABLE)
    assert not check.passed
    assert any("__cxa_allocate_exception" in reason for reason in check.reasons)


def test_rejects_the_allocation_function_of_libstdcxx_with_debug_information():
    # gdb prints "at <file>:<line>" and no "from" for a libstdc++ with debug
    # information; only the address shows that the frame is libstdc++'s.
    text = _fixture("gdb_bt_libstdcxx_x86_64.txt").replace(
        "#5  0x000055d4c1a2b6a9 in __cxa_allocate_exception ()",
        "#5  0x00007f8d3e8a0123 in __cxa_allocate_exception (thrown_size=16) at "
        "../../../../src/libstdc++-v3/libsupc++/eh_alloc.cc:284")
    frames = read_located_frames(text, _fixture("gdb_mappings_libstdcxx_x86_64.txt"))
    check = check_abort_top_frames(frames, EXECUTABLE)
    assert not check.passed
    assert any(f"lies in {LIBSTDCXX}" in reason for reason in check.reasons)


def test_accepts_a_libstdcxx_thrower_with_debug_information():
    text = _fixture("gdb_bt_libstdcxx_x86_64.txt").replace(
        "#6  0x00007f8d3e8a1c3e in std::__throw_out_of_range_fmt(char const*, ...) () from "
        "/lib/x86_64-linux-gnu/libstdc++.so.6",
        "#6  0x00007f8d3e8a1c3e in std::__throw_out_of_range_fmt (__fmt=0x1) at "
        "../../../../../src/libstdc++-v3/src/c++11/functexcept.cc:84")
    frames = read_located_frames(text, _fixture("gdb_mappings_libstdcxx_x86_64.txt"))
    check = check_abort_top_frames(frames, EXECUTABLE)
    assert check.passed, check.reasons
    assert check.caller_frame.library is None
    assert check.caller_frame.objfile == LIBSTDCXX


def test_rejects_a_library_name_that_the_address_does_not_confirm():
    text = _fixture("gdb_bt_libstdcxx_x86_64.txt").replace(
        "#5  0x000055d4c1a2b6a9 in __cxa_allocate_exception ()",
        "#5  0x000055d4c1a2b6a9 in __cxa_allocate_exception () from /lib/x86_64-linux-gnu/libstdc++.so.6")
    frames = read_located_frames(text, _fixture("gdb_mappings_libstdcxx_x86_64.txt"))
    check = check_abort_top_frames(frames, EXECUTABLE)
    assert not check.passed
    assert any("gdb names /lib/x86_64-linux-gnu/libstdc++.so.6" in reason for reason in check.reasons)


def test_rejects_an_allocation_frame_from_the_libstdcxx_source_even_inside_the_executable():
    text = _fixture("gdb_bt_libstdcxx_x86_64.txt").replace(
        "#5  0x000055d4c1a2b6a9 in __cxa_allocate_exception ()",
        "#5  0x000055d4c1a2b6a9 in __cxa_allocate_exception (thrown_size=16) at "
        "../../../../src/libstdc++-v3/libsupc++/eh_alloc.cc:284")
    frames = read_located_frames(text, _fixture("gdb_mappings_libstdcxx_x86_64.txt"))
    check = check_abort_top_frames(frames, EXECUTABLE)
    assert not check.passed
    assert any("libstdc++ source" in reason for reason in check.reasons)


def test_an_override_frame_without_a_mapping_is_rejected():
    frames = locate_frames(parse_gdb_backtrace(_fixture("gdb_bt_stripped_libc_rclcpp.txt")), [])
    check = check_abort_top_frames(frames, EXECUTABLE)
    assert not check.passed
    assert any("no mapped file" in reason for reason in check.reasons)


def test_rejects_a_frame_other_than_signal_delivery_above_abort():
    frames = [
        _frame(0, "raise", LIBC),
        _frame(1, "some_handler", ADAPTER),
        _frame(2, "abort", LIBC),
        _frame(3, "__cxa_allocate_exception", ADAPTER),
        _frame(4, "caller", ADAPTER),
    ]
    assert not check_abort_top_frames(frames, EXECUTABLE).passed


def test_rejects_an_empty_backtrace():
    check = check_abort_top_frames([], EXECUTABLE)
    assert not check.passed
    assert check.caller_frame is None


def test_rejects_a_backtrace_that_ends_at_the_override():
    frames = [_frame(0, "abort", LIBC), _frame(1, "__cxa_allocate_exception", ADAPTER)]
    check = check_abort_top_frames(frames, EXECUTABLE)
    assert not check.passed
    assert any("caller" in reason for reason in check.reasons)


def test_accepts_unnamed_libc_frames_of_the_signal_delivery():
    frames = [
        _frame(0, "??", LIBC),
        _frame(1, "raise", LIBC),
        _frame(2, "abort", LIBC),
        _frame(3, "__cxa_allocate_exception", ADAPTER),
        _frame(4, "std::__throw_out_of_range_fmt", LIBSTDCXX),
    ]
    assert check_abort_top_frames(frames, EXECUTABLE).passed


def test_rejects_an_unnamed_frame_outside_libc_above_abort():
    frames = [
        _frame(0, "??", "/opt/ros/humble/lib/librclcpp.so"),
        _frame(1, "abort", LIBC),
        _frame(2, "__cxa_allocate_exception", ADAPTER),
        _frame(3, "caller", ADAPTER),
    ]
    assert not check_abort_top_frames(frames, EXECUTABLE).passed


def test_the_first_named_frame_below_the_override_skips_unnamed_frames():
    frames = _located("gdb_bt_fastdds_shm_aarch64.txt", "gdb_mappings_fastdds_aarch64.txt")
    check = check_abort_top_frames(frames, EXECUTABLE)
    assert check.passed, check.reasons
    named = first_named_frame_below_override(frames, check)
    assert named.function == "eprosima::fastdds::rtps::SharedMemTransport::CreateInputChannelResource"
    assert frame_text(named).endswith("in /opt/ros/humble/lib/libfastrtps.so.2.6.10")
