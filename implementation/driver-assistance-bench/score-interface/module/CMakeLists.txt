# DE4SDV S-CORE interface for VisionPilot (INC-DRIVING-002, not part of upstream VisionPilot).
# Built only with -DENABLE_SCORE_INTERFACE=ON. The S-CORE build of the bench is Bazel (brief item B2); this file lets
# upstream's CMake build compile the portable part of the module.
#
#   DE4SDV_DA_INTERFACES_INCLUDE_DIR  the bench's interfaces/include (de4sdv/driver_assistance/payloads.h), used in
#                                     place, never copied
#   DE4SDV_SCORE_BINDINGS             a library or target that defines MakeLolaPorts and MakeCarlaClient
#                                     (seams.hpp): src/lola_bindings.cpp and src/carla_client.cpp need mw::com and the
#                                     CARLA 1.0 client, which only the Bazel build provides
cmake_minimum_required(VERSION 3.22.1)

set(DE4SDV_DA_INTERFACES_INCLUDE_DIR "" CACHE PATH "DE4SDV driver-assistance bench interfaces/include")
set(DE4SDV_SCORE_BINDINGS "" CACHE STRING "library defining MakeLolaPorts and MakeCarlaClient")
if(NOT EXISTS "${DE4SDV_DA_INTERFACES_INCLUDE_DIR}/de4sdv/driver_assistance/payloads.h")
    message(FATAL_ERROR "ENABLE_SCORE_INTERFACE needs DE4SDV_DA_INTERFACES_INCLUDE_DIR with "
                        "de4sdv/driver_assistance/payloads.h")
endif()
if(NOT DE4SDV_SCORE_BINDINGS)
    message(FATAL_ERROR "ENABLE_SCORE_INTERFACE needs DE4SDV_SCORE_BINDINGS")
endif()

find_package(OpenCV REQUIRED COMPONENTS core)

add_library(de4sdv_score_interface
        src/adapters.cpp
        src/core.cpp
        src/score_interface.cpp
        src/settings.cpp
        src/stop_signal.cpp
)

target_include_directories(de4sdv_score_interface
        PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        ${DE4SDV_DA_INTERFACES_INCLUDE_DIR}
)

target_link_libraries(de4sdv_score_interface
        PUBLIC
        common
        camera_interface
        vehicle_interface
        opencv_core
        ${DE4SDV_SCORE_BINDINGS}
)

target_compile_features(de4sdv_score_interface PUBLIC cxx_std_17)
