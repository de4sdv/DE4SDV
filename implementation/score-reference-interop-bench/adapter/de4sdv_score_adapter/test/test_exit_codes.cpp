// Unit test of the exit codes of the adapter process (INC-MW-011): each
// failure has its own code, none is 0, and none is above 125, so none looks
// like the end by a signal. The README lists them for the Launch Manager.

#include <gtest/gtest.h>

#include <set>

#include "de4sdv_score_adapter/exit_codes.hpp"

namespace {

namespace exit_code = de4sdv::score_adapter::exit_code;

TEST(ExitCodes, AreDistinctNonZeroAndBelowTheSignalRange) {
  const std::set<int> codes{exit_code::kConfigurationError, exit_code::kStillSubscribed,
                            exit_code::kFrameOfferFailed, exit_code::kSpeedSubscribeFailed};
  EXPECT_EQ(codes.size(), 4U);
  for (const int code : codes) {
    EXPECT_GT(code, 0);
    EXPECT_LE(code, 125);
  }
}

TEST(ExitCodes, ARefusedSpeedSubscriptionHasItsOwnCode) {
  EXPECT_EQ(exit_code::kSpeedSubscribeFailed, 5);
}

}  // namespace
