# DE4SDV throwaway spike (INC-MW-011 gateway feasibility), never merged.
# The guest-side vsomeip 3.7.6 client. Build against an installed vsomeip at
# commit 4187431d2815bd351845a09d01aa85b2a3163cab (tag 3.7.6):
#   cmake -S client -B build -DCMAKE_PREFIX_PATH=<vsomeip-3.7.6 prefix>
cmake_minimum_required(VERSION 3.16)
project(de4sdv_spike_frame_client CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(vsomeip3 REQUIRED)
find_package(Threads REQUIRED)

if(NOT vsomeip3_VERSION VERSION_EQUAL "3.7.6")
  message(FATAL_ERROR "the spike pins vsomeip 3.7.6, found ${vsomeip3_VERSION}")
endif()

add_executable(frame_client frame_client.cpp)
target_compile_options(frame_client PRIVATE -Wall -Wextra)
target_link_libraries(frame_client PRIVATE vsomeip3 Threads::Threads)
