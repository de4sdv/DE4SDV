// Unit tests of the fault signals of the REQ-MW-018 abort matrix. Each throw
// of the matrix has its own real-time signal, so the matrix runs the adapter
// with the start configuration of a member run; the handler stores the
// request and the main thread takes it once.

#include <gtest/gtest.h>

#include <csignal>
#include <set>
#include <string>

#include "de4sdv_score_adapter/fault_signal.hpp"

namespace {

using de4sdv::score_adapter::FaultRequest;
using de4sdv::score_adapter::FaultVariant;
using de4sdv::score_adapter::SignalFor;
using de4sdv::score_adapter::VariantForSignal;

constexpr FaultVariant kVariants[] = {FaultVariant::kRclcpp, FaultVariant::kAdapterCode, FaultVariant::kLibstdcxx};

TEST(FaultSignal, EachVariantHasItsOwnRealTimeSignal) {
  std::set<int> signals;
  for (const FaultVariant variant : kVariants) {
    const int signal = SignalFor(variant);
    EXPECT_GT(signal, SIGRTMIN);
    EXPECT_LE(signal, SIGRTMAX);
    signals.insert(signal);
    EXPECT_EQ(VariantForSignal(signal), variant);
  }
  EXPECT_EQ(signals.size(), 3U);
  EXPECT_EQ(SignalFor(FaultVariant::kNone), 0);
}

TEST(FaultSignal, OtherSignalsSelectNothing) {
  EXPECT_EQ(VariantForSignal(SIGTERM), FaultVariant::kNone);
  EXPECT_EQ(VariantForSignal(SIGRTMIN), FaultVariant::kNone);
  EXPECT_EQ(VariantForSignal(0), FaultVariant::kNone);
}

TEST(FaultSignal, VariantNamesAreThoseOfTheMatrix) {
  EXPECT_EQ(std::string{de4sdv::score_adapter::ToText(FaultVariant::kRclcpp)}, "rclcpp_internal");
  EXPECT_EQ(std::string{de4sdv::score_adapter::ToText(FaultVariant::kAdapterCode)}, "adapter_code");
  EXPECT_EQ(std::string{de4sdv::score_adapter::ToText(FaultVariant::kLibstdcxx)}, "libstdcxx");
}

TEST(FaultSignal, ARequestIsTakenOnce) {
  FaultRequest request;
  EXPECT_EQ(request.Take(), FaultVariant::kNone);
  request.Store(SignalFor(FaultVariant::kLibstdcxx));
  EXPECT_EQ(request.Take(), FaultVariant::kLibstdcxx);
  EXPECT_EQ(request.Take(), FaultVariant::kNone);
  request.Store(SIGTERM);
  EXPECT_EQ(request.Take(), FaultVariant::kNone);
}

}  // namespace
