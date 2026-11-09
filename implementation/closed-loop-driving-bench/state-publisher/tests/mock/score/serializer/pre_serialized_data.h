// LOCAL SYNTAX MOCK - NOT S-CORE.
#pragma once
#include <cstddef>
#include <cstdint>
namespace score::someip_gateway::serializer {
template <std::size_t N>
struct PreSerializedData {
  std::uint8_t data[N];
  std::size_t size;
};
}  // namespace score::someip_gateway::serializer
