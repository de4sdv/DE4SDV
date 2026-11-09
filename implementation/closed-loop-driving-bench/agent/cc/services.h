// DE4SDV closed-loop driving bench: the four mw::com services drivingAgent offers (ICD v2 section 2).
// The event name of each service is the last segment of its instance specifier; the proxies in
// statePublisher and actuationAdapter declare the same interfaces.
#pragma once

#include "score/mw/com/types.h"

#include "de4sdv/driving/payloads.h"

namespace de4sdv::driving::agent {

template <typename Trait>
struct EgoMotionSampleInterface : public Trait::Base {
  using Trait::Base::Base;
  typename Trait::template Event<EgoMotionSamplePayload> ego_motion_sample{*this, "ego_motion_sample"};
};

template <typename Trait>
struct PlanInterface : public Trait::Base {
  using Trait::Base::Base;
  typename Trait::template Event<DrivingPlanPayload> plan{*this, "plan"};
};

template <typename Trait>
struct ModeInterface : public Trait::Base {
  using Trait::Base::Base;
  typename Trait::template Event<DrivingModePayload> mode{*this, "mode"};
};

template <typename Trait>
struct CommandInterface : public Trait::Base {
  using Trait::Base::Base;
  typename Trait::template Event<VehicleMotionCommandPayload> command{*this, "command"};
};

using EgoMotionSampleSkeleton = score::mw::com::AsSkeleton<EgoMotionSampleInterface>;
using PlanSkeleton = score::mw::com::AsSkeleton<PlanInterface>;
using ModeSkeleton = score::mw::com::AsSkeleton<ModeInterface>;
using CommandSkeleton = score::mw::com::AsSkeleton<CommandInterface>;

using EgoMotionSampleProxy = score::mw::com::AsProxy<EgoMotionSampleInterface>;
using PlanProxy = score::mw::com::AsProxy<PlanInterface>;
using ModeProxy = score::mw::com::AsProxy<ModeInterface>;
using CommandProxy = score::mw::com::AsProxy<CommandInterface>;

inline constexpr const char* kEgoMotionSampleSpecifier = "de4sdv/driving/ego_motion_sample";
inline constexpr const char* kPlanSpecifier = "de4sdv/driving/plan";
inline constexpr const char* kModeSpecifier = "de4sdv/driving/mode";
inline constexpr const char* kCommandSpecifier = "de4sdv/driving/command";

}  // namespace de4sdv::driving::agent
