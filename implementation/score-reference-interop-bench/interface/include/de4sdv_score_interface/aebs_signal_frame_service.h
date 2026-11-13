// DE4SDV mw::com service interface of the AEBS signal frame (INC-MW-011,
// phase-8 port aebsSignalFrameOut of the AutowareToSCORE adapter).
//
// One service with one event and no method or field. The event type is the
// S-CORE SOME/IP gateway's own pre-serialized container, so gatewayd's null
// serializer copies exactly `size` bytes into the SOME/IP payload: the frame
// passes through unread and unchanged (REQ-MW-015). A sample holds one
// length-prefixed frame of the INC-AEBS-010 frame stream, prefix included, of
// at most 2048 bytes: the gateway slot of the reused ingress.
//
// This header is DE4SDV-owned. It compiles only inside the throwaway checkout
// of the S-CORE SOME/IP gateway that the bench builds; no S-CORE file is
// copied into the DE4SDV repository.

#ifndef DE4SDV_SCORE_INTERFACE_AEBS_SIGNAL_FRAME_SERVICE_H
#define DE4SDV_SCORE_INTERFACE_AEBS_SIGNAL_FRAME_SERVICE_H

#include <cstddef>

#include "score/mw/com/types.h"
#include "score/serializer/pre_serialized_data.h"

namespace de4sdv::score_interface {

// The mw::com configuration and the gateway configuration name this
// instance specifier.
constexpr const char* kAebsSignalFrameInstanceSpecifier = "de4sdv/aebs_signal_frame";

constexpr std::size_t kAebsSignalFrameSampleBytes = 2048;

using AebsSignalFrameSample = score::someip_gateway::serializer::PreSerializedData<kAebsSignalFrameSampleBytes>;

template <typename Trait>
class AebsSignalFrameInterface : public Trait::Base {
 public:
  using Trait::Base::Base;

  typename Trait::template Event<AebsSignalFrameSample> aebs_signal_frame_{*this, "aebs_signal_frame"};
};

using AebsSignalFrameSkeleton = score::mw::com::AsSkeleton<AebsSignalFrameInterface>;
using AebsSignalFrameProxy = score::mw::com::AsProxy<AebsSignalFrameInterface>;

}  // namespace de4sdv::score_interface

#endif  // DE4SDV_SCORE_INTERFACE_AEBS_SIGNAL_FRAME_SERVICE_H
