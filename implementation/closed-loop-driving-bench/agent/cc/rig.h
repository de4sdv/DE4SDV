// DE4SDV closed-loop driving bench (INC-DRIVING-001, slice 10b): the driving agent's camera rig
// size, shared by the frame store and the decision logic. The index order is the rig's:
// front, front_left, front_right, rear_left, rear, rear_right.
#pragma once

#include <cstddef>

namespace de4sdv::driving::agent {

inline constexpr std::size_t kCameraCount = 6;

}  // namespace de4sdv::driving::agent
