// Unit tests of the SHA-256 (sha256.h). With --vectors it prints "<input hex> <digest>" lines, which
// test_identity_recorder_units.py compares with Python's hashlib (no digest is written into this file).
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "check.h"
#include "sha256.h"

namespace id = de4sdv::driver_assistance::identity;

namespace {

std::vector<std::string> Inputs() {
  std::vector<std::string> inputs = {"", "abc", "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"};
  for (const std::size_t n : {55u, 56u, 57u, 63u, 64u, 65u, 119u, 120u, 127u, 128u, 129u, 1000u}) {
    std::string s;
    for (std::size_t i = 0; i < n; ++i) s += static_cast<char>((i * 31u + 7u) & 0xFFu);
    inputs.push_back(s);
  }
  return inputs;
}

std::string Hex(const std::string& s) {
  static const char* const kHex = "0123456789abcdef";
  std::string out;
  for (const unsigned char c : s) {
    out += kHex[c >> 4];
    out += kHex[c & 0xF];
  }
  return out.empty() ? "-" : out;
}

void TestStreamingEqualsOneShot() {
  for (const std::string& input : Inputs()) {
    for (const std::size_t chunk : {1u, 3u, 63u, 64u, 65u}) {
      id::Sha256 h;
      for (std::size_t i = 0; i < input.size(); i += chunk) h.Update(input.substr(i, chunk));
      CHECK(h.HexDigest() == id::Sha256Hex(input));
    }
  }
}

void TestHexShape() {
  for (const std::string& input : Inputs()) CHECK(id::IsLowerHex(id::Sha256Hex(input), 64));
  CHECK(id::Sha256Hex("a") != id::Sha256Hex("b"));
  CHECK(id::IsLowerHex("0123456789abcdef", 16));
  CHECK(!id::IsLowerHex("0123456789ABCDEF", 16));
  CHECK(!id::IsLowerHex("0123456789abcdeg", 16));
  CHECK(!id::IsLowerHex("0123", 16));
}

}  // namespace

int main(int argc, char** argv) {
  if (argc == 2 && std::strcmp(argv[1], "--vectors") == 0) {
    for (const std::string& input : Inputs()) std::printf("%s %s\n", Hex(input).c_str(), id::Sha256Hex(input).c_str());
    std::string million(1000000, 'a');
    id::Sha256 h;
    for (std::size_t i = 0; i < million.size(); i += 4096) h.Update(million.substr(i, 4096));
    std::printf("million-a %s\n", h.HexDigest().c_str());
    return 0;
  }
  TestStreamingEqualsOneShot();
  TestHexShape();
  return de4sdv::driver_assistance::actuation::test::Finish("sha256_test");
}
