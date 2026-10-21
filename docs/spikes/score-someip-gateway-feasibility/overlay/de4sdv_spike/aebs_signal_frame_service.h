// DE4SDV throwaway spike (INC-MW-011 gateway feasibility), never merged.
//
// The mw::com service interface of the opaque AEBS signal frame. The event
// type is the gateway's own pre-serialized container
// (score/serializer/pre_serialized_data.h at inc_someip_gateway 951fbc09), so
// gatewayd's null serializer copies exactly `size` bytes into the SOME/IP
// payload: the frame passes through unread and unchanged. Modeled on
// tests/benchmarks/echo_service.h of the same commit.

#ifndef DE4SDV_SPIKE_AEBS_SIGNAL_FRAME_SERVICE_H
#define DE4SDV_SPIKE_AEBS_SIGNAL_FRAME_SERVICE_H

#include <cstddef>

#include "score/mw/com/types.h"
#include "score/serializer/pre_serialized_data.h"

namespace de4sdv_spike {

// One length-prefixed frame of at most 2048 bytes, the gateway slot of the
// reused INC-AEBS-010 ingress.
constexpr std::size_t kMaxFrameBytes = 2048;

using AebsSignalFrameSample = score::someip_gateway::serializer::PreSerializedData<kMaxFrameBytes>;

template <typename Trait>
class AebsSignalFrameInterface : public Trait::Base {
   public:
    using Trait::Base::Base;

    typename Trait::template Event<AebsSignalFrameSample> aebs_signal_frame_{*this,
                                                                            "aebs_signal_frame"};
};

using AebsSignalFrameSkeleton = score::mw::com::AsSkeleton<AebsSignalFrameInterface>;
using AebsSignalFrameProxy = score::mw::com::AsProxy<AebsSignalFrameInterface>;

}  // namespace de4sdv_spike

#endif  // DE4SDV_SPIKE_AEBS_SIGNAL_FRAME_SERVICE_H
