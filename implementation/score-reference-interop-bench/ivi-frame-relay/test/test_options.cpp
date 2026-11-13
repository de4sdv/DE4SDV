// Unit tests of the command line of the relay: the defaults, the names that
// the C API holds, the refused margin options, and the start log line that
// repeats the configuration and the fixed values.

#include <gtest/gtest.h>

#include <string>
#include <vector>

#include "de4sdv_ivi_frame_relay/options.hpp"

namespace {

using de4sdv::ivi_frame_relay::kListenAddress;
using de4sdv::ivi_frame_relay::kListenPort;
using de4sdv::ivi_frame_relay::kNanosecondsPerSecond;
using de4sdv::ivi_frame_relay::ParseOptions;
using de4sdv::ivi_frame_relay::SplitProperty;
using de4sdv::ivi_frame_relay::StartRecord;
using de4sdv::ivi_frame_relay::Usage;

using Args = std::vector<std::string>;

TEST(Options, DefaultsNameThePublicationOfTheFeasibilityRunAndTheRelaysSubject) {
  const auto parsed = ParseOptions({});
  ASSERT_TRUE(parsed.options.has_value()) << parsed.error;
  const auto& o = *parsed.options;
  EXPECT_EQ(o.publication.vm, "instance1");
  EXPECT_EQ(o.publication.package, "com.android.sdv.someip");
  EXPECT_EQ(o.publication.bundle, "SomeIpBroker");
  EXPECT_EQ(o.publication.unit, "de4sdv-score-aebs-signal-frame");
  EXPECT_EQ(o.subject.package, "de4sdv.ivi_frame_relay");
  EXPECT_EQ(o.subject.bundle, "IviFrameRelay");
  EXPECT_EQ(o.subject.instance, "default");
  EXPECT_EQ(o.status_period_ns, 10 * kNanosecondsPerSecond);
  EXPECT_FALSE(o.relay.log_frames);
  EXPECT_TRUE(o.relay.ingress_start_property.empty());
  EXPECT_TRUE(o.announce_properties.empty());
  EXPECT_EQ(kListenAddress, 0x7F000001U);
  EXPECT_EQ(kListenPort, 4731);
}

TEST(Options, EveryValueCanBeSet) {
  const auto parsed = ParseOptions({"--publication-vm", "instance3", "--publication-package", "com.example.broker",
                                    "--publication-bundle", "Broker", "--publication-unit", "frames",
                                    "--subject-package", "org.example.relay", "--subject-bundle", "Relay",
                                    "--subject-instance", "one", "--status-period-s", "5", "--log-frames",
                                    "--announce-property", "de4sdv.aebs.frame_server.host=127.0.0.1",
                                    "--ingress-start-property", "de4sdv.aebs.ingress.start"});
  ASSERT_TRUE(parsed.options.has_value()) << parsed.error;
  const auto& o = *parsed.options;
  EXPECT_EQ(o.publication.vm, "instance3");
  EXPECT_EQ(o.publication.package, "com.example.broker");
  EXPECT_EQ(o.publication.bundle, "Broker");
  EXPECT_EQ(o.publication.unit, "frames");
  EXPECT_EQ(o.subject.package, "org.example.relay");
  EXPECT_EQ(o.subject.bundle, "Relay");
  EXPECT_EQ(o.subject.instance, "one");
  EXPECT_EQ(o.status_period_ns, 5 * kNanosecondsPerSecond);
  EXPECT_TRUE(o.relay.log_frames);
  EXPECT_EQ(o.announce_properties, (Args{"de4sdv.aebs.frame_server.host=127.0.0.1"}));
  EXPECT_EQ(o.relay.ingress_start_property, "de4sdv.aebs.ingress.start");
}

TEST(Options, ANameThatTheCApiCannotHoldIsRefused) {
  EXPECT_TRUE(ParseOptions({"--publication-vm", std::string(31, 'v')}).options.has_value());
  EXPECT_FALSE(ParseOptions({"--publication-vm", std::string(32, 'v')}).options.has_value());
  EXPECT_FALSE(ParseOptions({"--publication-bundle", std::string(48, 'b')}).options.has_value());
  EXPECT_FALSE(ParseOptions({"--subject-instance", std::string(48, 'i')}).options.has_value());
  EXPECT_FALSE(ParseOptions({"--publication-unit", std::string(128, 'u')}).options.has_value());
  EXPECT_FALSE(ParseOptions({"--subject-package", ""}).options.has_value());
  EXPECT_FALSE(ParseOptions({"--subject-package", "with space"}).options.has_value());
}

TEST(Options, AnOptionThatNamesAMarginOrABoundStopsTheRelay) {
  for (const char* option : {"--phase-start-margin-ms", "--margin", "--clock-bound-ms", "--margin-ns"}) {
    const auto parsed = ParseOptions({option, "5"});
    EXPECT_FALSE(parsed.options.has_value()) << option;
    EXPECT_NE(parsed.error.find("fixed at 20 ms"), std::string::npos) << parsed.error;
  }
  // Also after valid options.
  EXPECT_FALSE(ParseOptions({"--log-frames", "--margin-ms", "0"}).options.has_value());
}

TEST(Options, InvalidValuesAndUnknownOptionsAreRefused) {
  EXPECT_FALSE(ParseOptions({"--status-period-s", "0"}).options.has_value());
  EXPECT_FALSE(ParseOptions({"--status-period-s", "3601"}).options.has_value());
  EXPECT_FALSE(ParseOptions({"--status-period-s", "1x"}).options.has_value());
  EXPECT_FALSE(ParseOptions({"--status-period-s"}).options.has_value());
  EXPECT_FALSE(ParseOptions({"--announce-property", "noequals"}).options.has_value());
  EXPECT_FALSE(ParseOptions({"--ingress-start-property", "a=b"}).options.has_value());
  EXPECT_FALSE(ParseOptions({"--listen-port", "4721"}).options.has_value());
  EXPECT_FALSE(ParseOptions({"--fetch-last-message"}).options.has_value());
  EXPECT_FALSE(ParseOptions({"--server-address", "192.168.98.1"}).options.has_value());
}

TEST(Options, HelpNamesTheFixedValues) {
  EXPECT_TRUE(ParseOptions({"--help"}).help);
  const std::string usage = Usage();
  EXPECT_NE(usage.find("127.0.0.1:4731"), std::string::npos);
  EXPECT_NE(usage.find("ASDVGATEWAY_SUBSCRIBER_OPTIONS_FLAG_NONE"), std::string::npos);
  EXPECT_NE(usage.find("fixed at 20 ms"), std::string::npos);
}

TEST(Options, SplitPropertyNeedsAName) {
  std::string name;
  std::string value;
  EXPECT_TRUE(SplitProperty("a.b=c=d", &name, &value));
  EXPECT_EQ(name, "a.b");
  EXPECT_EQ(value, "c=d");
  EXPECT_FALSE(SplitProperty("=x", &name, &value));
}

TEST(Options, StartRecordRepeatsTheConfigurationAndTheFixedValues) {
  const auto parsed = ParseOptions({"--ingress-start-property", "de4sdv.aebs.ingress.start"});
  ASSERT_TRUE(parsed.options.has_value());
  const auto record = StartRecord(*parsed.options, "relay_subscription_phase_discard_rule", 4242);
  const std::string& fields = record.fields();
  for (const char* expected :
       {"\"pid\":4242", "\"publication_unit\":\"de4sdv-score-aebs-signal-frame\"",
        "\"subject_package\":\"de4sdv.ivi_frame_relay\"", "\"subscriber_flags\":0",
        "\"subscriber_flag\":\"ASDVGATEWAY_SUBSCRIBER_OPTIONS_FLAG_NONE\"", "\"listen\":\"127.0.0.1:4731\"",
        "\"max_payload_bytes\":2048", "\"discard_policy\":\"relay_subscription_phase_discard_rule\"",
        "\"phase_start_margin_ns\":20000000", "\"copy_memory_frames\":40", "\"silence_timeout_ns\":3000000000",
        "\"destroyed_retry_period_ns\":100000000", "\"destroyed_fast_window_ns\":5000000000",
        "\"retry_period_ns\":1000000000", "\"silent_subscriptions_before_back_off\":3",
        "\"silent_back_off_ns\":5000000000", "\"start_diagnostic_ns\":30000000000",
        "\"slow_retry_period_ns\":10000000000", "\"ingress_start_property\":\"de4sdv.aebs.ingress.start\"",
        "\"ingress_retrigger_limit\":10"}) {
    EXPECT_NE(fields.find(expected), std::string::npos) << expected;
  }
}

}  // namespace
