cmake_minimum_required(VERSION 3.16)
project(de4sdv_ivi_frame_relay CXX)

# The DE4SDV IVI frame relay of the AAOS SDV guest (INC-MW-011, ADR 0025):
# portable C++17 on POSIX, with the SDV Gateway client behind a narrow
# interface (include/de4sdv_ivi_frame_relay/gateway_client.hpp).
#
# - de4sdv_ivi_frame_relay_core: the pure core (the strict parse of the
#   broker's wrapper, the payload checks, the discard policy, the retry
#   schedule, the gateway worker, the relay core, the options). It makes no
#   socket call and no call into the gateway library.
# - de4sdv_ivi_frame_relay_shell: the POSIX shell (the loopback server, the
#   mailbox, the worker thread, the poll loop).
# - The AOSP adapter to libsdvgatewayclient and the main
#   (src/aosp/) build only in an AOSP tree, with Android.bp. This file
#   does not build them, so it builds no relay executable: the gtest suites
#   run the core and the shell with the fake client of test/.
#
# The tests need GTest (Ubuntu: libgtest-dev).

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE RelWithDebInfo)
endif()

set(DE4SDV_WARNINGS -Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Werror)
find_package(Threads REQUIRED)

add_library(de4sdv_ivi_frame_relay_core STATIC
  src/core/broker_wrapper.cpp
  src/core/discard_policy.cpp
  src/core/event_log.cpp
  src/core/frame_fields.cpp
  src/core/gateway_client.cpp
  src/core/gateway_worker.cpp
  src/core/options.cpp
  src/core/relay_core.cpp
  src/core/retry_schedule.cpp
)
target_include_directories(de4sdv_ivi_frame_relay_core PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)
target_compile_options(de4sdv_ivi_frame_relay_core PRIVATE ${DE4SDV_WARNINGS})
target_link_libraries(de4sdv_ivi_frame_relay_core PUBLIC Threads::Threads)

add_library(de4sdv_ivi_frame_relay_shell STATIC src/shell/peer_identity.cpp src/shell/relay_shell.cpp)
target_include_directories(de4sdv_ivi_frame_relay_shell PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/src>
)
target_compile_options(de4sdv_ivi_frame_relay_shell PRIVATE ${DE4SDV_WARNINGS})
target_link_libraries(de4sdv_ivi_frame_relay_shell PUBLIC de4sdv_ivi_frame_relay_core)

find_package(GTest REQUIRED)
enable_testing()
add_executable(de4sdv_ivi_frame_relay_tests
  test/test_broker_wrapper.cpp
  test/test_discard_policy.cpp
  test/test_event_log.cpp
  test/test_frame_fields.cpp
  test/test_gateway_worker.cpp
  test/test_options.cpp
  test/test_peer_identity.cpp
  test/test_relay_core.cpp
  test/test_relay_shell.cpp
  test/test_retry_schedule.cpp
)
target_compile_definitions(de4sdv_ivi_frame_relay_tests PRIVATE
  DE4SDV_FIXTURE_DIR="${CMAKE_CURRENT_SOURCE_DIR}/test/fixtures")
target_compile_options(de4sdv_ivi_frame_relay_tests PRIVATE ${DE4SDV_WARNINGS})
target_link_libraries(de4sdv_ivi_frame_relay_tests PRIVATE de4sdv_ivi_frame_relay_shell GTest::gtest_main)
add_test(NAME de4sdv_ivi_frame_relay_tests COMMAND de4sdv_ivi_frame_relay_tests)
