// Pure core of the AutowareToSCORE adapter: the fault signals of the
// REQ-MW-018 abort matrix (rehearsal of VC-MW-019).
//
// The matrix runs the adapter with the start configuration of a member run,
// and selects each throw by a real-time signal: SIGRTMIN+1 for a throw inside
// librclcpp.so, SIGRTMIN+2 for a throw in adapter code, SIGRTMIN+3 for a
// throw inside the shared libstdc++. The signal handler only stores the
// request; the main thread takes it and runs the throw inside a try/catch.
// With baselibs' abort override the process aborts at the allocation of the
// exception, before the catch; without it, the catch handles the exception.
// Only a process of the same user, or root, can send these signals to the
// adapter, and such a process can end the adapter anyway.

#ifndef DE4SDV_SCORE_ADAPTER_FAULT_SIGNAL_HPP
#define DE4SDV_SCORE_ADAPTER_FAULT_SIGNAL_HPP

#include <atomic>

namespace de4sdv::score_adapter {

enum class FaultVariant : int {
  kNone = 0,
  kRclcpp = 1,       // rclcpp throws ParameterNotDeclaredException in librclcpp.so
  kAdapterCode = 2,  // a throw in adapter code
  kLibstdcxx = 3,    // std::vector::at throws in the shared libstdc++
};

// The name of the variant in the adapter log and in the matrix records.
const char* ToText(FaultVariant variant) noexcept;
// SIGRTMIN plus the variant's number; 0 for kNone.
int SignalFor(FaultVariant variant) noexcept;
// The variant of a fault signal; kNone for any other signal.
FaultVariant VariantForSignal(int signal) noexcept;

// The request slot between the signal handler and the main thread.
class FaultRequest {
 public:
  // Async-signal-safe: one lock-free atomic store.
  void Store(int signal) noexcept;
  // The requested variant, once; kNone when nothing is requested.
  FaultVariant Take() noexcept;

 private:
  std::atomic<int> signal_{0};
  static_assert(std::atomic<int>::is_always_lock_free, "the signal handler needs a lock-free store");
};

}  // namespace de4sdv::score_adapter

#endif  // DE4SDV_SCORE_ADAPTER_FAULT_SIGNAL_HPP
