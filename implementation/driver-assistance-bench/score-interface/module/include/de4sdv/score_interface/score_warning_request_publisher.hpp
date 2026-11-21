// DE4SDV S-CORE interface for VisionPilot (INC-DRIVING-002, not part of upstream VisionPilot).
//
// SCOREWarningRequestPublisher of the model: the one hand-off of the plan's warnings added in the loop after
// vision_pilot.cpp:174 (MAP-DRIVING-DA-PLANNED-WARNINGS in, MAP-DRIVING-DA-WARNING-REQUEST out). One event per plan:
// requested is true when the plan's warnings hold FCW or AEB (planning.cpp:113-121), issueTime is the capture time
// of the pass. The planner is not changed.
#pragma once

#include <vector>

#include <common/types.hpp>

#include "de4sdv/score_interface/core.hpp"

namespace de4sdv::score_interface {

bool HoldsForwardCollisionWarningOrEmergencyBraking(const std::vector<Warning>& warnings);

class ScoreWarningRequestPublisher {
 public:
  explicit ScoreWarningRequestPublisher(WarningRequestWriter* writer);
  void Publish(const Plan& plan);

 private:
  WarningRequestWriter* writer_;
};

}  // namespace de4sdv::score_interface
