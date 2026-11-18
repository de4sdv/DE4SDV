// The check macros of the actuation adapter's g++ tests (no test framework).
#pragma once

#include <cmath>
#include <cstdio>

namespace de4sdv::driver_assistance::actuation::test {

inline int g_failures = 0;
inline int g_checks = 0;

inline void Check(bool condition, const char* expression, const char* file, int line) {
  ++g_checks;
  if (!condition) {
    ++g_failures;
    std::printf("FAIL %s:%d: %s\n", file, line, expression);
  }
}

// Exact comparison of doubles, printed with all digits on failure.
inline void CheckEq(double actual, double expected, const char* expression, const char* file,
                    int line) {
  ++g_checks;
  if (!(actual == expected)) {
    ++g_failures;
    std::printf("FAIL %s:%d: %s (actual %.17g, expected %.17g)\n", file, line, expression, actual,
                expected);
  }
}

// Ends a test binary: prints the counts and returns the exit status.
inline int Finish(const char* name) {
  if (g_failures != 0) {
    std::printf("%s: %d of %d checks failed\n", name, g_failures, g_checks);
    return 1;
  }
  std::printf("%s: all passed (%d checks)\n", name, g_checks);
  return 0;
}

}  // namespace de4sdv::driver_assistance::actuation::test

#define CHECK(condition) \
  ::de4sdv::driver_assistance::actuation::test::Check((condition), #condition, __FILE__, __LINE__)
#define CHECK_EQ_D(actual, expected)                                                       \
  ::de4sdv::driver_assistance::actuation::test::CheckEq((actual), (expected),              \
                                                        #actual " == " #expected, __FILE__, \
                                                        __LINE__)
