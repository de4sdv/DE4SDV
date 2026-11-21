// Prints the SOME/IP bytes of the warning request that payloads.h writes, one hex line per
// vector, for tests/test_warning_golden_bytes.py.
// Usage: golden_warning_bytes <requested 0|1> <issue time s> [<requested> <issue time> ...]
#include "de4sdv/driver_assistance/payloads.h"

#include <cstdint>
#include <cstdio>
#include <cstdlib>

namespace da = de4sdv::driver_assistance;

int main(int argc, char** argv) {
  if (argc < 3 || argc % 2 == 0) {
    std::fprintf(stderr, "usage: %s <requested 0|1> <issue time s> ...\n", argv[0]);
    return 2;
  }
  for (int i = 1; i + 1 < argc; i += 2) {
    const da::WarningRequest request{std::atoi(argv[i]) != 0, std::strtod(argv[i + 1], nullptr)};
    std::uint8_t out[da::kWarningRequestSomeipSize];
    if (!da::EncodeWarningRequestSomeip(request, out)) {
      std::printf("refused\n");
      continue;
    }
    for (std::size_t k = 0; k < da::kWarningRequestSomeipSize; ++k) std::printf("%02x", out[k]);
    std::printf("\n");
  }
  return 0;
}
