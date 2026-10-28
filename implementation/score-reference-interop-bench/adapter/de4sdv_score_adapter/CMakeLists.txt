cmake_minimum_required(VERSION 3.16)
project(de4sdv_score_adapter CXX)

# The DE4SDV AutowareToSCORE adapter of INC-MW-011 (one process, REQ-MW-018).
#
# The pure core (speed translation, frame splitter, LoLa rules) builds and
# tests without S-CORE and ROS 2. The adapter executable needs rclcpp,
# autoware_vehicle_msgs and the facade SDK that the Bazel build of the S-CORE
# SOME/IP gateway workspace produces (scripts/ci_stage_facade_sdk.sh):
#   <sdk>/include/de4sdv_score_facade/score_facade.h
#   <sdk>/lib/libde4sdv_score_facade.a            facade, mw::com, baselibs
#   <sdk>/lib/libde4sdv_aborts_upon_exception.a   baselibs' abort override
#   <sdk>/link_inputs.txt                         further link inputs, in order
# The final link uses this compiler and the shared libstdc++, so the process
# holds one C++ runtime. The abort override goes first on the link line as a
# whole archive, and the executable exports __cxa_allocate_exception, so a
# throw inside librclcpp.so or libstdc++.so binds to it as well.

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(ament_cmake REQUIRED)

set(DE4SDV_WARNINGS -Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion)

add_library(de4sdv_score_adapter_core STATIC
  src/core/frame_path_controller.cpp
  src/core/frame_splitter.cpp
  src/core/speed_path_controller.cpp
  src/core/speed_translation.cpp
)
target_include_directories(de4sdv_score_adapter_core PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)
target_compile_options(de4sdv_score_adapter_core PRIVATE ${DE4SDV_WARNINGS})
set_target_properties(de4sdv_score_adapter_core PROPERTIES POSITION_INDEPENDENT_CODE ON)
find_package(Threads REQUIRED)
target_link_libraries(de4sdv_score_adapter_core PUBLIC Threads::Threads)

option(DE4SDV_BUILD_ADAPTER "Build the adapter executable (needs rclcpp, autoware_vehicle_msgs and the facade SDK)" ON)
option(DE4SDV_BUILD_DISCRIMINATION_CONTROL
  "Also build de4sdv_score_adapter_no_abort_control: the same adapter without the abort override, used only to show that the abort matrix discriminates" OFF)
set(DE4SDV_SCORE_FACADE_DIR "" CACHE PATH "Facade SDK directory from scripts/ci_stage_facade_sdk.sh")

if(DE4SDV_BUILD_ADAPTER)
  find_package(rclcpp REQUIRED)
  find_package(autoware_vehicle_msgs REQUIRED)

  set(_facade_archive "${DE4SDV_SCORE_FACADE_DIR}/lib/libde4sdv_score_facade.a")
  set(_abort_archive "${DE4SDV_SCORE_FACADE_DIR}/lib/libde4sdv_aborts_upon_exception.a")
  set(_link_inputs_file "${DE4SDV_SCORE_FACADE_DIR}/link_inputs.txt")
  foreach(_required IN ITEMS "${_facade_archive}" "${_abort_archive}" "${_link_inputs_file}"
                             "${DE4SDV_SCORE_FACADE_DIR}/include/de4sdv_score_facade/score_facade.h")
    if(NOT EXISTS "${_required}")
      message(FATAL_ERROR "de4sdv_score_adapter: ${_required} is missing; set DE4SDV_SCORE_FACADE_DIR to the facade SDK "
                          "(scripts/ci_stage_facade_sdk.sh), or build the core only with -DDE4SDV_BUILD_ADAPTER=OFF")
    endif()
  endforeach()
  file(STRINGS "${_link_inputs_file}" DE4SDV_FACADE_LINK_INPUTS)

  set(_adapter_sources
    src/adapter_main.cpp
    src/facade_ports.cpp
    src/fault_hook.cpp
  )

  function(de4sdv_add_adapter target with_abort_override)
    add_executable(${target} ${_adapter_sources})
    target_include_directories(${target} PRIVATE "${DE4SDV_SCORE_FACADE_DIR}/include" src)
    target_compile_options(${target} PRIVATE ${DE4SDV_WARNINGS})
    if(with_abort_override)
      target_link_libraries(${target}
        "-Wl,--whole-archive" "${_abort_archive}" "-Wl,--no-whole-archive")
      target_link_options(${target} PRIVATE "LINKER:--export-dynamic-symbol=__cxa_allocate_exception")
    endif()
    target_link_libraries(${target}
      de4sdv_score_adapter_core
      "${_facade_archive}"
      ${DE4SDV_FACADE_LINK_INPUTS})
    ament_target_dependencies(${target} rclcpp autoware_vehicle_msgs)
    install(TARGETS ${target} DESTINATION lib/${PROJECT_NAME})
  endfunction()

  de4sdv_add_adapter(de4sdv_score_adapter TRUE)
  if(DE4SDV_BUILD_DISCRIMINATION_CONTROL)
    de4sdv_add_adapter(de4sdv_score_adapter_no_abort_control FALSE)
  endif()
endif()

if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)
  foreach(_test IN ITEMS
      test_frame_path_controller
      test_frame_splitter
      test_speed_path_controller
      test_speed_translation)
    ament_add_gtest(${_test} test/${_test}.cpp)
    target_link_libraries(${_test} de4sdv_score_adapter_core)
  endforeach()
endif()

ament_package()
