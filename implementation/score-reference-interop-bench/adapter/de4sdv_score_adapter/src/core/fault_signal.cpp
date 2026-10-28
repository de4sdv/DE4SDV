#include "de4sdv_score_adapter/fault_signal.hpp"

#include <csignal>
#include <initializer_list>

namespace de4sdv::score_adapter {

const char* ToText(FaultVariant variant) noexcept {
  switch (variant) {
    case FaultVariant::kRclcpp:
      return "rclcpp_internal";
    case FaultVariant::kAdapterCode:
      return "adapter_code";
    case FaultVariant::kLibstdcxx:
      return "libstdcxx";
    case FaultVariant::kNone:
    default:
      return "none";
  }
}

int SignalFor(FaultVariant variant) noexcept {
  return variant == FaultVariant::kNone ? 0 : SIGRTMIN + static_cast<int>(variant);
}

FaultVariant VariantForSignal(int signal) noexcept {
  for (const FaultVariant variant : {FaultVariant::kRclcpp, FaultVariant::kAdapterCode, FaultVariant::kLibstdcxx}) {
    if (signal == SignalFor(variant)) {
      return variant;
    }
  }
  return FaultVariant::kNone;
}

void FaultRequest::Store(int signal) noexcept { signal_.store(signal, std::memory_order_release); }

FaultVariant FaultRequest::Take() noexcept {
  return VariantForSignal(signal_.exchange(0, std::memory_order_acq_rel));
}

}  // namespace de4sdv::score_adapter
