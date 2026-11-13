// LOCAL SYNTAX MOCK - NOT S-CORE.
#pragma once
#include <string>
namespace score::mw::com::runtime {
struct RuntimeConfiguration {
  RuntimeConfiguration() = default;
  explicit RuntimeConfiguration(const std::string& /*path*/) {}
};
void InitializeRuntime(const RuntimeConfiguration&);
}  // namespace score::mw::com::runtime
