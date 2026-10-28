// Unit tests of the structured log events of the pure receiver core: one
// JSON object per line, with both clocks first.

#include <gtest/gtest.h>

#include <cstdint>
#include <string>

#include "de4sdv_someip_receiver/event_log.hpp"

namespace {

using de4sdv::someip_receiver::Clock;
using de4sdv::someip_receiver::JsonQuote;
using de4sdv::someip_receiver::LogRecord;

TEST(EventLog, LineHoldsClocksEventAndFieldsInOrder) {
  LogRecord record{"phase_start"};
  record.Text("cause", "client_connected").Signed("phase_start_realtime_ns", -5).Unsigned("count", 7).Bool("ok", true);
  EXPECT_EQ(record.ToJson(Clock{11, 22}),
            "{\"monotonic_ns\":11,\"realtime_ns\":22,\"event\":\"phase_start\",\"cause\":\"client_connected\","
            "\"phase_start_realtime_ns\":-5,\"count\":7,\"ok\":true}");
}

TEST(EventLog, EventWithoutFields) {
  EXPECT_EQ(LogRecord{"exit"}.ToJson(Clock{1, 2}), "{\"monotonic_ns\":1,\"realtime_ns\":2,\"event\":\"exit\"}");
}

TEST(EventLog, TextIsEscaped) {
  EXPECT_EQ(JsonQuote("a\"b\\c\nd\te"), "\"a\\\"b\\\\c\\nd\\u0009e\"");
  EXPECT_EQ(JsonQuote(std::string{"x\x01y"}), "\"x\\u0001y\"");
}

TEST(EventLog, LargestUnsignedValueIsWrittenExactly) {
  LogRecord record{"status"};
  record.Unsigned("sequence", UINT64_MAX);
  EXPECT_EQ(record.fields(), "\"sequence\":18446744073709551615");
}

}  // namespace
