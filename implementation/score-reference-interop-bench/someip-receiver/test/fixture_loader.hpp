// Loads the golden fixtures of test/fixtures/: one hex string per file, made
// from retained captures and from the protobuf runtime (see
// test/fixtures/README.md). DE4SDV_FIXTURE_DIR comes from CMakeLists.txt.

#ifndef DE4SDV_SOMEIP_RECEIVER_TEST_FIXTURE_LOADER_HPP
#define DE4SDV_SOMEIP_RECEIVER_TEST_FIXTURE_LOADER_HPP

#include <cctype>
#include <cstdint>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#ifndef DE4SDV_FIXTURE_DIR
#error "DE4SDV_FIXTURE_DIR must name the fixture directory"
#endif

namespace de4sdv::someip_receiver::test {

using Bytes = std::vector<std::uint8_t>;

inline Bytes FromHex(const std::string& text) {
  Bytes bytes;
  int high = -1;
  for (const char c : text) {
    if (std::isspace(static_cast<unsigned char>(c)) != 0) {
      continue;
    }
    int value = 0;
    if (c >= '0' && c <= '9') {
      value = c - '0';
    } else if (c >= 'a' && c <= 'f') {
      value = c - 'a' + 10;
    } else if (c >= 'A' && c <= 'F') {
      value = c - 'A' + 10;
    } else {
      throw std::runtime_error("not a hex digit in a fixture");
    }
    if (high < 0) {
      high = value;
    } else {
      bytes.push_back(static_cast<std::uint8_t>((high << 4) | value));
      high = -1;
    }
  }
  if (high >= 0) {
    throw std::runtime_error("odd number of hex digits in a fixture");
  }
  return bytes;
}

inline Bytes LoadHexFixture(const std::string& name) {
  const std::string path = std::string{DE4SDV_FIXTURE_DIR} + "/" + name + ".hex";
  std::ifstream file{path};
  if (!file) {
    throw std::runtime_error("fixture missing: " + path);
  }
  std::stringstream text;
  text << file.rdbuf();
  return FromHex(text.str());
}

}  // namespace de4sdv::someip_receiver::test

#endif  // DE4SDV_SOMEIP_RECEIVER_TEST_FIXTURE_LOADER_HPP
