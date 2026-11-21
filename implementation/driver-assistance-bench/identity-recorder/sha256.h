// DE4SDV driver-assistance bench (INC-DRIVING-002): SHA-256 (FIPS 180-4) for the identity recorder, with no
// dependency. MAP-DRIVING-DA-CANDIDATE-RECORD asks for each SHA-256 in hexadecimal.
#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <string>

namespace de4sdv::driver_assistance::identity {

class Sha256 {
 public:
  Sha256();
  void Update(const void* data, std::size_t size);
  void Update(const std::string& data) { Update(data.data(), data.size()); }
  // The digest as 64 lowercase hex digits. The object is spent afterwards.
  std::string HexDigest();

 private:
  void Block(const std::uint8_t* block);

  std::array<std::uint32_t, 8> state_;
  std::array<std::uint8_t, 64> buffer_{};
  std::size_t buffered_ = 0;
  std::uint64_t total_bytes_ = 0;
};

// The hex digest of a whole string.
std::string Sha256Hex(const std::string& data);

// True for exactly `digits` lowercase hex digits.
bool IsLowerHex(const std::string& text, std::size_t digits);

}  // namespace de4sdv::driver_assistance::identity
