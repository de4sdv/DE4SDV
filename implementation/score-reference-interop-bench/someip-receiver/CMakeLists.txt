cmake_minimum_required(VERSION 3.16)
project(de4sdv_someip_receiver CXX)

# The DE4SDV minimal SOME/IP receiver of the AAOS SDV guest (INC-MW-011):
# portable C++17 on POSIX sockets, without Boost and without vsomeip.
#
# - de4sdv_someip_receiver_core: the pure core (SOME/IP-SD messages, the
#   subscription state machine, SOME/IP-over-TCP reassembly, the payload
#   checks, the discard policy). It makes no socket call; gtest suites
#   cover it with golden fixtures from retained captures.
# - de4sdv_someip_receiver: the thin POSIX shell (sockets, poll loop,
#   signals, JSON log lines). Android.bp builds the same sources for AOSP.
#
# The tests need GTest (Ubuntu: libgtest-dev). Build the receiver only with
# -DDE4SDV_BUILD_TESTS=OFF.

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE RelWithDebInfo)
endif()

set(DE4SDV_WARNINGS -Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Werror)

add_library(de4sdv_someip_receiver_core STATIC
  src/core/discard_policy.cpp
  src/core/event_log.cpp
  src/core/frame_fields.cpp
  src/core/options.cpp
  src/core/receiver_core.cpp
  src/core/someip_stream.cpp
  src/core/someip_wire.cpp
  src/core/subscription.cpp
)
target_include_directories(de4sdv_someip_receiver_core PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)
target_compile_options(de4sdv_someip_receiver_core PRIVATE ${DE4SDV_WARNINGS})

add_executable(de4sdv_someip_receiver src/receiver_main.cpp)
target_compile_options(de4sdv_someip_receiver PRIVATE ${DE4SDV_WARNINGS})
target_link_libraries(de4sdv_someip_receiver PRIVATE de4sdv_someip_receiver_core)
install(TARGETS de4sdv_someip_receiver RUNTIME DESTINATION bin)

option(DE4SDV_BUILD_TESTS "Build the gtest suites of the pure core" ON)
if(DE4SDV_BUILD_TESTS)
  find_package(GTest REQUIRED)
  enable_testing()
  add_executable(de4sdv_someip_receiver_tests
    test/test_discard_policy.cpp
    test/test_event_log.cpp
    test/test_frame_fields.cpp
    test/test_options.cpp
    test/test_receiver_core.cpp
    test/test_someip_stream.cpp
    test/test_someip_wire.cpp
    test/test_subscription.cpp
  )
  target_compile_definitions(de4sdv_someip_receiver_tests PRIVATE
    DE4SDV_FIXTURE_DIR="${CMAKE_CURRENT_SOURCE_DIR}/test/fixtures")
  target_compile_options(de4sdv_someip_receiver_tests PRIVATE ${DE4SDV_WARNINGS})
  target_link_libraries(de4sdv_someip_receiver_tests PRIVATE de4sdv_someip_receiver_core GTest::gtest_main)
  add_test(NAME de4sdv_someip_receiver_tests COMMAND de4sdv_someip_receiver_tests)
endif()
