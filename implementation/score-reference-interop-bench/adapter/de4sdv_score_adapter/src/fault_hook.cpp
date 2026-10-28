#include "fault_hook.hpp"

#include <cstdlib>
#include <stdexcept>
#include <vector>

namespace de4sdv::score_adapter::fault_hook {

bool EnabledByEnvironment() noexcept {
  const char* value = std::getenv(kEnvironmentVariable);
  return value != nullptr && value[0] == '1' && value[1] == '\0';
}

std::string EnvironmentSetting() {
  const char* value = std::getenv(kEnvironmentVariable);
  return value == nullptr ? std::string{"unset"} : std::string{value};
}

// noinline keeps each hook a frame of its own in the backtrace of the core.
__attribute__((noinline)) std::string ThrowInAdapterCode() {
  try {
    throw std::runtime_error("DE4SDV fault hook: exception thrown in adapter code");
  } catch (const std::runtime_error& error) {
    return error.what();
  }
}

__attribute__((noinline)) std::string ThrowInsideLibstdcxx() {
  try {
    std::vector<int> empty;
    volatile std::size_t index = 1;
    // std::vector::at calls std::__throw_out_of_range_fmt in the shared
    // libstdc++, which allocates the exception there.
    return std::to_string(empty.at(index));
  } catch (const std::out_of_range& error) {
    return error.what();
  }
}

}  // namespace de4sdv::score_adapter::fault_hook
