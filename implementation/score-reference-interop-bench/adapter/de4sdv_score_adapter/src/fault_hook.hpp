// Fault hook of the AutowareToSCORE adapter for the REQ-MW-018 abort matrix
// (rehearsal of VC-MW-019). The matrix selects a throw by a real-time signal
// (fault_signal.hpp), so it runs the adapter with the start configuration of
// a member run and the same binary. Each function below throws one exception
// inside a try/catch and returns the text of the caught exception:
//   ThrowInsideRclcpp    - rclcpp::Node::get_parameter of an undeclared
//                          parameter: ParameterNotDeclaredException, thrown
//                          inside librclcpp.so;
//   ThrowInAdapterCode   - a throw in adapter code;
//   ThrowInsideLibstdcxx - a throw inside the shared libstdc++
//                          (std::vector::at).
// With baselibs' aborts_upon_exception linked, each ends the process with
// SIGABRT at the allocation of the exception, before the catch. Without it,
// the catch handles the exception and the process survives, so the test
// discriminates.

#ifndef DE4SDV_SCORE_ADAPTER_FAULT_HOOK_HPP
#define DE4SDV_SCORE_ADAPTER_FAULT_HOOK_HPP

#include <string>

#include "rclcpp/rclcpp.hpp"

namespace de4sdv::score_adapter::fault_hook {

// A name that the adapter never declares.
constexpr const char* kUndeclaredParameter = "de4sdv_undeclared_parameter";

std::string ThrowInsideRclcpp(rclcpp::Node& node);
std::string ThrowInAdapterCode();
std::string ThrowInsideLibstdcxx();

}  // namespace de4sdv::score_adapter::fault_hook

#endif  // DE4SDV_SCORE_ADAPTER_FAULT_HOOK_HPP
