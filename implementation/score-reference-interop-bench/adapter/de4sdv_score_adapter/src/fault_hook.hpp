// Fault hook of the AutowareToSCORE adapter for the REQ-MW-018 abort matrix
// (VC-MW-019). It is off by default. Only DE4SDV_ADAPTER_FAULT_HOOK=1 in the
// environment enables it, and the adapter logs the setting at start. When it
// is on, the adapter declares the string parameter de4sdv_fault_hook; setting
// it throws an exception inside a try/catch:
//   adapter_code  - a throw in adapter code;
//   libstdcxx     - a throw inside the shared libstdc++ (std::vector::at).
// With baselibs' aborts_upon_exception linked, both end the process with
// SIGABRT at the allocation of the exception, before the catch. Without it,
// the catch handles them and the process survives, so the test
// discriminates. The third variant of the matrix needs no hook: rclcpp
// throws and catches ParameterNotDeclaredException when an undeclared
// parameter is set.

#ifndef DE4SDV_SCORE_ADAPTER_FAULT_HOOK_HPP
#define DE4SDV_SCORE_ADAPTER_FAULT_HOOK_HPP

#include <string>

namespace de4sdv::score_adapter::fault_hook {

constexpr const char* kEnvironmentVariable = "DE4SDV_ADAPTER_FAULT_HOOK";
constexpr const char* kParameterName = "de4sdv_fault_hook";

// True only when the environment variable is exactly "1".
bool EnabledByEnvironment() noexcept;
// The raw value for the start log: "unset" or the value.
std::string EnvironmentSetting();

// Each returns the text of the caught exception; with the abort override the
// process ends before it returns.
std::string ThrowInAdapterCode();
std::string ThrowInsideLibstdcxx();

}  // namespace de4sdv::score_adapter::fault_hook

#endif  // DE4SDV_SCORE_ADAPTER_FAULT_HOOK_HPP
