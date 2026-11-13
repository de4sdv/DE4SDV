// LOCAL SYNTAX MOCK - NOT S-CORE. Same layout as inc_someip_gateway d9eac670
// score/serializer/pre_serialized_data.h (sha256 1ec7b4c9...a1b2f8): `size`
// first, then the bytes aligned to std::max_align_t. gatewayd's null serializer
// reads exactly this layout (null_serializer.cpp:65-70).
#pragma once
#include <cstddef>
namespace score::someip_gateway::serializer {
template <std::size_t MaxMessageSize>
struct PreSerializedData {
  static constexpr std::size_t kMaxMessageSize = MaxMessageSize;
  std::size_t size{};
  alignas(std::max_align_t) std::byte data[MaxMessageSize];
};
}  // namespace score::someip_gateway::serializer
