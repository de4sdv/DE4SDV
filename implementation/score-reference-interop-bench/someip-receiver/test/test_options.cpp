// Unit tests of the command line of the receiver: required values, ranges,
// and the start log line that repeats the configuration.

#include <gtest/gtest.h>

#include <string>
#include <vector>

#include "de4sdv_someip_receiver/options.hpp"

namespace {

using de4sdv::someip_receiver::kNanosecondsPerMillisecond;
using de4sdv::someip_receiver::ParseOptions;
using de4sdv::someip_receiver::StartRecord;

using Args = std::vector<std::string>;

Args Minimal() { return {"--server-address", "10.250.0.1"}; }

Args With(Args args, const Args& more) {
  args.insert(args.end(), more.begin(), more.end());
  return args;
}

TEST(Options, DefaultsAreTheSpikeIdentifiersAndTheIngressPort) {
  const auto parsed = ParseOptions(Minimal());
  ASSERT_TRUE(parsed.options.has_value()) << parsed.error;
  const auto& options = *parsed.options;
  EXPECT_EQ(options.receiver.subscription.server_address, 0x0AFA0001U);
  EXPECT_EQ(options.receiver.subscription.service_id, 0x4DEE);
  EXPECT_EQ(options.receiver.subscription.instance_id, 0x0001);
  EXPECT_EQ(options.receiver.subscription.major_version, 1);
  EXPECT_EQ(options.receiver.subscription.eventgroup_id, 0x0001);
  EXPECT_EQ(options.receiver.event_id, 0x8001);
  EXPECT_EQ(options.receiver.subscription.reliable_port, 30509);
  EXPECT_EQ(options.receiver.subscription.sd_port, 30490);
  EXPECT_EQ(options.receiver.subscription.ttl_s, 3U);
  EXPECT_EQ(options.receiver.max_payload_bytes, 2048U);
  EXPECT_EQ(options.listen_address, 0x7F000001U);
  EXPECT_EQ(options.listen_port, 4731);
  EXPECT_TRUE(options.join_multicast);
  EXPECT_EQ(options.multicast_group, 0xE0F4E0F5U);
  EXPECT_TRUE(options.announce_property.empty());
}

TEST(Options, ServerAddressIsRequired) {
  EXPECT_FALSE(ParseOptions({}).options.has_value());
  EXPECT_FALSE(ParseOptions({"--listen-port", "4731"}).options.has_value());
}

TEST(Options, TheDiscardRuleHasNoOption) {
  EXPECT_FALSE(ParseOptions(With(Minimal(), {"--clock-offset-bound-ms", "0"})).options.has_value());
}

TEST(Options, AnnouncePropertyIsNameEqualsValue) {
  const auto parsed = ParseOptions(With(Minimal(), {"--announce-property", "de4sdv.aebs.frame_server.host=127.0.0.1"}));
  ASSERT_TRUE(parsed.options.has_value()) << parsed.error;
  EXPECT_EQ(parsed.options->announce_property, "de4sdv.aebs.frame_server.host=127.0.0.1");
  EXPECT_FALSE(ParseOptions(With(Minimal(), {"--announce-property", "=127.0.0.1"})).options.has_value());
  EXPECT_FALSE(ParseOptions(With(Minimal(), {"--announce-property", "no-value"})).options.has_value());
}

TEST(Options, AllValuesAreRead) {
  const auto parsed = ParseOptions(With(Minimal(), {"--service", "0x1234", "--instance", "2", "--major-version", "3",
                                                     "--eventgroup", "0x10", "--event", "0x8002", "--reliable-port",
                                                     "40000", "--sd-port", "30491", "--multicast-group",
                                                     "224.0.0.251", "--multicast-interface", "192.168.98.7",
                                                     "--ttl-s", "5", "--renew-period-ms", "2000",
                                                     "--subscribe-delay-ms", "5", "--subscribe-timeout-ms", "9000",
                                                     "--connect-timeout-ms", "1500", "--connect-retry-ms", "250",
                                                     "--listen-address", "127.0.0.2", "--listen-port", "4800",
                                                     "--max-payload-bytes", "1024", "--status-period-s", "2",
                                                     "--log-frames"}));
  ASSERT_TRUE(parsed.options.has_value()) << parsed.error;
  const auto& o = *parsed.options;
  EXPECT_EQ(o.receiver.subscription.service_id, 0x1234);
  EXPECT_EQ(o.receiver.subscription.instance_id, 2);
  EXPECT_EQ(o.receiver.subscription.major_version, 3);
  EXPECT_EQ(o.receiver.subscription.eventgroup_id, 0x10);
  EXPECT_EQ(o.receiver.event_id, 0x8002);
  EXPECT_EQ(o.receiver.subscription.reliable_port, 40000);
  EXPECT_EQ(o.receiver.subscription.sd_port, 30491);
  EXPECT_EQ(o.multicast_group, 0xE00000FBU);
  EXPECT_EQ(o.multicast_interface, 0xC0A86207U);
  EXPECT_EQ(o.receiver.subscription.ttl_s, 5U);
  EXPECT_EQ(o.receiver.subscription.renew_period_ns, 2000 * kNanosecondsPerMillisecond);
  EXPECT_EQ(o.receiver.subscription.subscribe_delay_ns, 5 * kNanosecondsPerMillisecond);
  EXPECT_EQ(o.receiver.subscription.subscribe_timeout_ns, 9000 * kNanosecondsPerMillisecond);
  EXPECT_EQ(o.receiver.subscription.connect_timeout_ns, 1500 * kNanosecondsPerMillisecond);
  EXPECT_EQ(o.receiver.subscription.connect_retry_period_ns, 250 * kNanosecondsPerMillisecond);
  EXPECT_EQ(o.listen_address, 0x7F000002U);
  EXPECT_EQ(o.listen_port, 4800);
  EXPECT_EQ(o.receiver.max_payload_bytes, 1024U);
  EXPECT_EQ(o.status_period_ns, 2 * 1'000'000'000LL);
  EXPECT_TRUE(o.receiver.log_frames);
}

TEST(Options, NoMulticastSelectsTheUnicastFallbackOnly) {
  const auto parsed = ParseOptions(With(Minimal(), {"--no-multicast"}));
  ASSERT_TRUE(parsed.options.has_value());
  EXPECT_FALSE(parsed.options->join_multicast);
}

TEST(Options, InvalidValuesAreRejected) {
  for (const Args& bad : {Args{"--listen-address", "0.0.0.0"}, Args{"--listen-address", "192.168.98.2"},
                          Args{"--listen-port", "0"}, Args{"--listen-port", "65536"}, Args{"--service", "0x10000"},
                          Args{"--major-version", "256"}, Args{"--ttl-s", "0"}, Args{"--ttl-s", "16777216"},
                          Args{"--renew-period-ms", "3000"},
                          Args{"--max-payload-bytes", "3"}, Args{"--multicast-group", "10.0.0.1"},
                          Args{"--server-address", "10.250.0"}, Args{"--status-period-s", "0"},
                          Args{"--unknown-option"}, Args{"--event"}}) {
    const auto parsed = ParseOptions(With(Minimal(), bad));
    EXPECT_FALSE(parsed.options.has_value()) << bad.front();
    EXPECT_FALSE(parsed.error.empty()) << bad.front();
  }
}

TEST(Options, HelpIsNotAnError) {
  const auto parsed = ParseOptions({"--help"});
  EXPECT_TRUE(parsed.help);
  EXPECT_FALSE(parsed.options.has_value());
}

TEST(Options, StartRecordRepeatsTheConfiguration) {
  const auto parsed = ParseOptions(With(Minimal(), {"--log-frames"}));
  ASSERT_TRUE(parsed.options.has_value());
  const auto record = StartRecord(*parsed.options, "receiver_subscription_phase_discard_rule", 4242);
  EXPECT_EQ(record.event(), "start");
  for (const char* expected :
       {"\"pid\":4242", "\"server_address\":\"10.250.0.1\"", "\"service_id\":19950", "\"event_id\":32769",
        "\"eventgroup_id\":1", "\"reliable_port\":30509", "\"sd_port\":30490",
        "\"multicast_group\":\"224.244.224.245\"", "\"join_multicast\":true", "\"listen\":\"127.0.0.1:4731\"",
        "\"phase_start_margin_ns\":20000000", "\"copy_memory_frames\":40",
        "\"discard_policy\":\"receiver_subscription_phase_discard_rule\"",
        "\"subscription_ttl_s\":3", "\"renew_period_ns\":1000000000", "\"max_payload_bytes\":2048",
        "\"log_frames\":true"}) {
    EXPECT_NE(record.fields().find(expected), std::string::npos) << expected;
  }
  // The line keys monotonic_ns, realtime_ns and event belong to the line itself.
  for (const char* reserved : {"\"event\":", "\"monotonic_ns\":", "\"realtime_ns\":"}) {
    EXPECT_EQ(record.fields().find(reserved), std::string::npos) << reserved;
  }
}

}  // namespace
