// Tests of payloads.h: layout, check value and SOME/IP bytes.
// Build: g++ -std=c++17 -Wall -Wextra -Werror -I../include payloads_test.cpp
#include "de4sdv/driver_assistance/payloads.h"

#include <cstdio>
#include <cstring>
#include <limits>

namespace da = de4sdv::driver_assistance;

static int failures = 0;
#define EXPECT(cond)                                              \
  do {                                                            \
    if (!(cond)) {                                                \
      std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
      ++failures;                                                 \
    }                                                             \
  } while (0)

int main() {
  // The standard check value of CRC-32 (IEEE 802.3, zlib).
  const char* nine = "123456789";
  EXPECT(da::Crc32(reinterpret_cast<const std::uint8_t*>(nine), 9) ==
         0xCBF43926u);
  EXPECT(da::Crc32(nullptr, 0) == 0x00000000u);

  // The check value of one command, computed independently with Python:
  // zlib.crc32(struct.pack('<ffdI', -5.0, 1.5, 12.35, 7)) == 0x8bb2a1e4
  da::DrivingCommandEventPayload c{-5.0f, 1.5f, 12.35, 7u, 0u};
  EXPECT(da::DrivingCommandCheckValue(c) == 0x8bb2a1e4u);
  // The check value does not cover itself.
  c.checkValue = 0xFFFFFFFFu;
  EXPECT(da::DrivingCommandCheckValue(c) == 0x8bb2a1e4u);
  // Each covered field changes it.
  da::DrivingCommandEventPayload d = c;
  d.sequenceCount = 8u;
  EXPECT(da::DrivingCommandCheckValue(d) != 0x8bb2a1e4u);
  d = c;
  d.issueTime = 12.4;
  EXPECT(da::DrivingCommandCheckValue(d) != 0x8bb2a1e4u);
  d = c;
  d.steeringAngle = -1.5f;
  EXPECT(da::DrivingCommandCheckValue(d) != 0x8bb2a1e4u);
  d = c;
  d.acceleration = -4.99f;
  EXPECT(da::DrivingCommandCheckValue(d) != 0x8bb2a1e4u);

  // SOME/IP bytes: big-endian, requested then milliseconds.
  std::uint8_t out[8];
  EXPECT(da::EncodeWarningRequestSomeip({true, 12.35}, out));
  const std::uint8_t want[8] = {0, 0, 0, 1, 0x00, 0x00, 0x30, 0x3E};
  EXPECT(std::memcmp(out, want, 8) == 0);  // 12350 ms = 0x303E
  EXPECT(da::EncodeWarningRequestSomeip({false, 0.05}, out));
  const std::uint8_t want2[8] = {0, 0, 0, 0, 0, 0, 0, 50};
  EXPECT(std::memcmp(out, want2, 8) == 0);
  // Not carried: negative, not finite, beyond 32 bits of milliseconds.
  std::uint8_t keep[8] = {9, 9, 9, 9, 9, 9, 9, 9};
  EXPECT(!da::EncodeWarningRequestSomeip({true, -0.001}, keep));
  EXPECT(!da::EncodeWarningRequestSomeip({true, std::numeric_limits<double>::infinity()}, keep));
  EXPECT(!da::EncodeWarningRequestSomeip({true, 4294967.296}, keep));
  EXPECT(keep[0] == 9 && keep[7] == 9);

  if (failures == 0) std::printf("payloads_test: all passed\n");
  return failures == 0 ? 0 : 1;
}
