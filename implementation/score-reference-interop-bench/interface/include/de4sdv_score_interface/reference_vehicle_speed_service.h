// DE4SDV mw::com service interface of the reference vehicle speed
// (INC-MW-011, phase-8 port referenceSpeedIn of the AutowareToSCORE adapter).
//
// One service with one event and no method or field. The event carries the
// payload DE4SDVReferenceVehicleSpeedPayload of INC-MW-008: speed_kmh, the
// identity mapping of COVESA VSS Vehicle.Speed in km/h. The sample type is
// trivially copyable, as the LoLa binding of mw::com needs. The structure
// follows the typed service interfaces of the S-CORE SOME/IP gateway's own
// tests (an Interface<Trait> template with AsSkeleton and AsProxy).
//
// This header is DE4SDV-owned. It compiles only inside the throwaway checkout
// of the S-CORE SOME/IP gateway that the bench builds; no S-CORE file is
// copied into the DE4SDV repository.

#ifndef DE4SDV_SCORE_INTERFACE_REFERENCE_VEHICLE_SPEED_SERVICE_H
#define DE4SDV_SCORE_INTERFACE_REFERENCE_VEHICLE_SPEED_SERVICE_H

#include <type_traits>

#include "score/mw/com/types.h"

namespace de4sdv::score_interface {

// The mw::com configuration names this instance specifier.
constexpr const char* kReferenceVehicleSpeedInstanceSpecifier = "de4sdv/reference_vehicle_speed";

struct ReferenceVehicleSpeedSample {
  double speed_kmh;
};
static_assert(std::is_trivially_copyable_v<ReferenceVehicleSpeedSample>,
              "LoLa event samples must be trivially copyable");

template <typename Trait>
class ReferenceVehicleSpeedInterface : public Trait::Base {
 public:
  using Trait::Base::Base;

  typename Trait::template Event<ReferenceVehicleSpeedSample> vehicle_speed_{*this, "vehicle_speed"};
};

using ReferenceVehicleSpeedSkeleton = score::mw::com::AsSkeleton<ReferenceVehicleSpeedInterface>;
using ReferenceVehicleSpeedProxy = score::mw::com::AsProxy<ReferenceVehicleSpeedInterface>;

}  // namespace de4sdv::score_interface

#endif  // DE4SDV_SCORE_INTERFACE_REFERENCE_VEHICLE_SPEED_SERVICE_H
