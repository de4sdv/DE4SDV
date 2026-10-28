// Unit tests of the SOME/IP header and the SOME/IP-SD messages of the pure
// receiver core. The golden fixtures are real datagrams of someipd (vsomeip
// 3.6.1) and of a vsomeip 3.7.6 client from retained captures; the encoder
// must write the same bytes as that client for the same request.

#include <gtest/gtest.h>

#include <cstdint>
#include <vector>

#include "de4sdv_someip_receiver/someip_wire.hpp"
#include "fixture_loader.hpp"

namespace {

using de4sdv::someip_receiver::EncodeSubscribeEventgroup;
using de4sdv::someip_receiver::Ipv4Endpoint;
using de4sdv::someip_receiver::Ipv4ToText;
using de4sdv::someip_receiver::kL4ProtocolTcp;
using de4sdv::someip_receiver::ParseHeader;
using de4sdv::someip_receiver::ParseIpv4;
using de4sdv::someip_receiver::ParseSdMessage;
using de4sdv::someip_receiver::SdEntryType;
using de4sdv::someip_receiver::SdParseError;
using de4sdv::someip_receiver::SubscribeRequest;
using de4sdv::someip_receiver::test::Bytes;
using de4sdv::someip_receiver::test::LoadHexFixture;

constexpr std::uint32_t kHost = 0x0AFA0001;   // 10.250.0.1
constexpr std::uint32_t kGuest = 0x0AFA0002;  // 10.250.0.2

std::uint8_t Type(SdEntryType type) { return static_cast<std::uint8_t>(type); }

TEST(SomeipHeader, ReadsTheSixteenHeaderBytes) {
  const Bytes offer = LoadHexFixture("sd_offer_multicast");
  const auto header = ParseHeader(offer.data(), offer.size());
  ASSERT_TRUE(header.has_value());
  EXPECT_EQ(header->service_id, 0xFFFF);
  EXPECT_EQ(header->method_id, 0x8100);
  EXPECT_EQ(header->length, 48U);
  EXPECT_EQ(header->client_id, 0x0000);
  EXPECT_EQ(header->session_id, 1);
  EXPECT_EQ(header->protocol_version, 1);
  EXPECT_EQ(header->interface_version, 1);
  EXPECT_EQ(header->message_type, 0x02);
  EXPECT_EQ(header->return_code, 0x00);
  EXPECT_FALSE(ParseHeader(offer.data(), 15).has_value());
}

TEST(SomeipSd, OfferOfSomeipdCarriesTheTcpEndpointOfTheEvent) {
  const Bytes offer = LoadHexFixture("sd_offer_multicast");
  const auto result = ParseSdMessage(offer.data(), offer.size());
  ASSERT_EQ(result.error, SdParseError::kNone);
  ASSERT_TRUE(result.message.has_value());
  const auto& message = *result.message;
  EXPECT_EQ(message.session_id, 1);
  EXPECT_TRUE(message.reboot);
  EXPECT_TRUE(message.unicast);
  ASSERT_EQ(message.entries.size(), 1U);
  const auto& entry = message.entries[0];
  EXPECT_EQ(entry.type, Type(SdEntryType::kOfferService));
  EXPECT_EQ(entry.service_id, 0x4DEE);
  EXPECT_EQ(entry.instance_id, 0x0001);
  EXPECT_EQ(entry.major_version, 1);
  EXPECT_EQ(entry.ttl, 3U);
  EXPECT_EQ(entry.minor_version, 0U);
  ASSERT_EQ(entry.endpoints.size(), 1U);
  EXPECT_EQ(entry.endpoints[0], (Ipv4Endpoint{kHost, 30509, kL4ProtocolTcp}));
}

TEST(SomeipSd, StopOfferHasTtlZero) {
  const Bytes stop = LoadHexFixture("sd_stop_offer");
  const auto result = ParseSdMessage(stop.data(), stop.size());
  ASSERT_TRUE(result.message.has_value());
  EXPECT_EQ(result.message->session_id, 0x15);
  ASSERT_EQ(result.message->entries.size(), 1U);
  EXPECT_EQ(result.message->entries[0].type, Type(SdEntryType::kOfferService));
  EXPECT_EQ(result.message->entries[0].ttl, 0U);
}

TEST(SomeipSd, AckAndNackDifferInTheTtlOnly) {
  const Bytes ack = LoadHexFixture("sd_subscribe_ack");
  const Bytes nack = LoadHexFixture("sd_subscribe_nack_offer_pending");
  const auto ack_result = ParseSdMessage(ack.data(), ack.size());
  const auto nack_result = ParseSdMessage(nack.data(), nack.size());
  ASSERT_TRUE(ack_result.message.has_value());
  ASSERT_TRUE(nack_result.message.has_value());
  const auto& ack_entry = ack_result.message->entries.at(0);
  const auto& nack_entry = nack_result.message->entries.at(0);
  EXPECT_EQ(ack_entry.type, Type(SdEntryType::kSubscribeEventgroupAck));
  EXPECT_EQ(nack_entry.type, Type(SdEntryType::kSubscribeEventgroupAck));
  EXPECT_EQ(ack_entry.ttl, 3U);
  EXPECT_EQ(nack_entry.ttl, 0U);
  for (const auto* entry : {&ack_entry, &nack_entry}) {
    EXPECT_EQ(entry->service_id, 0x4DEE);
    EXPECT_EQ(entry->instance_id, 0x0001);
    EXPECT_EQ(entry->major_version, 1);
    EXPECT_EQ(entry->eventgroup_id, 0x0001);
    EXPECT_TRUE(entry->endpoints.empty());
  }
}

TEST(SomeipSd, FindServiceOfAnotherClientIsDecoded) {
  const Bytes find = LoadHexFixture("sd_find_service_from_vsomeip_client");
  const auto result = ParseSdMessage(find.data(), find.size());
  ASSERT_TRUE(result.message.has_value());
  const auto& entry = result.message->entries.at(0);
  EXPECT_EQ(entry.type, Type(SdEntryType::kFindService));
  EXPECT_EQ(entry.ttl, 0xFFFFFFU);
  EXPECT_EQ(entry.minor_version, 0xFFFFFFFFU);
}

TEST(SomeipSd, TwoEntriesMayReferenceTheSameOption) {
  const Bytes both = LoadHexFixture("sd_stop_subscribe_and_subscribe_from_vsomeip_client");
  const auto result = ParseSdMessage(both.data(), both.size());
  ASSERT_EQ(result.error, SdParseError::kNone);
  ASSERT_TRUE(result.message.has_value());
  ASSERT_EQ(result.message->entries.size(), 2U);
  EXPECT_EQ(result.message->entries[0].ttl, 0U);
  EXPECT_EQ(result.message->entries[1].ttl, 3U);
  for (const auto& entry : result.message->entries) {
    EXPECT_EQ(entry.type, Type(SdEntryType::kSubscribeEventgroup));
    ASSERT_EQ(entry.endpoints.size(), 1U);
    EXPECT_EQ(entry.endpoints[0].address, kGuest);
    EXPECT_EQ(entry.endpoints[0].protocol, kL4ProtocolTcp);
  }
}

TEST(SomeipSd, SubscribeIsByteIdenticalToTheVsomeipClient) {
  // The vsomeip 3.7.6 client subscribed from 10.250.0.2:35005 (TCP) with session 1.
  SubscribeRequest request;
  request.session_id = 1;
  request.reboot = true;
  request.service_id = 0x4DEE;
  request.instance_id = 0x0001;
  request.major_version = 1;
  request.ttl = 3;
  request.eventgroup_id = 0x0001;
  request.endpoint = Ipv4Endpoint{kGuest, 35005, kL4ProtocolTcp};
  EXPECT_EQ(EncodeSubscribeEventgroup(request), LoadHexFixture("sd_subscribe_from_vsomeip_client"));
}

TEST(SomeipSd, StopSubscribeIsByteIdenticalToTheVsomeipClient) {
  SubscribeRequest request;
  request.session_id = 9;
  request.reboot = true;
  request.service_id = 0x4DEE;
  request.instance_id = 0x0001;
  request.major_version = 1;
  request.ttl = 0;
  request.eventgroup_id = 0x0001;
  request.endpoint = Ipv4Endpoint{kGuest, 35005, kL4ProtocolTcp};
  EXPECT_EQ(EncodeSubscribeEventgroup(request), LoadHexFixture("sd_stop_subscribe_from_vsomeip_client"));
}

TEST(SomeipSd, EncodedSubscribeParsesBack) {
  SubscribeRequest request;
  request.session_id = 0xFFFF;
  request.reboot = false;
  request.service_id = 0x1234;
  request.instance_id = 0x0002;
  request.major_version = 3;
  request.ttl = 0xFFFFFF;
  request.eventgroup_id = 0x00AB;
  request.endpoint = Ipv4Endpoint{0xC0A86205, 41000, kL4ProtocolTcp};
  const Bytes bytes = EncodeSubscribeEventgroup(request);
  const auto result = ParseSdMessage(bytes.data(), bytes.size());
  ASSERT_TRUE(result.message.has_value());
  EXPECT_EQ(result.message->session_id, 0xFFFF);
  EXPECT_FALSE(result.message->reboot);
  EXPECT_TRUE(result.message->unicast);
  const auto& entry = result.message->entries.at(0);
  EXPECT_EQ(entry.type, Type(SdEntryType::kSubscribeEventgroup));
  EXPECT_EQ(entry.service_id, 0x1234);
  EXPECT_EQ(entry.instance_id, 0x0002);
  EXPECT_EQ(entry.major_version, 3);
  EXPECT_EQ(entry.ttl, 0xFFFFFFU);
  EXPECT_EQ(entry.eventgroup_id, 0x00AB);
  ASSERT_EQ(entry.endpoints.size(), 1U);
  EXPECT_EQ(entry.endpoints[0], request.endpoint);
}

TEST(SomeipSd, TruncatedDatagramIsRejected) {
  Bytes offer = LoadHexFixture("sd_offer_multicast");
  offer.pop_back();
  EXPECT_EQ(ParseSdMessage(offer.data(), offer.size()).error, SdParseError::kLengthMismatch);
  EXPECT_EQ(ParseSdMessage(offer.data(), 10).error, SdParseError::kTooShort);
}

TEST(SomeipSd, OtherServiceIsNotServiceDiscovery) {
  Bytes offer = LoadHexFixture("sd_offer_multicast");
  offer[0] = 0x4D;
  EXPECT_EQ(ParseSdMessage(offer.data(), offer.size()).error, SdParseError::kNotServiceDiscovery);
  Bytes wrong_type = LoadHexFixture("sd_offer_multicast");
  wrong_type[14] = 0x00;  // REQUEST, not NOTIFICATION
  EXPECT_EQ(ParseSdMessage(wrong_type.data(), wrong_type.size()).error, SdParseError::kNotServiceDiscovery);
}

TEST(SomeipSd, EntriesLengthMustBeAMultipleOfSixteenAndFit) {
  Bytes offer = LoadHexFixture("sd_offer_multicast");
  offer[23] = 0x11;  // entries length 17
  EXPECT_EQ(ParseSdMessage(offer.data(), offer.size()).error, SdParseError::kBadEntriesLength);
  Bytes overrun = LoadHexFixture("sd_offer_multicast");
  overrun[23] = 0x40;  // entries length 64, more than the message holds
  EXPECT_EQ(ParseSdMessage(overrun.data(), overrun.size()).error, SdParseError::kBadEntriesLength);
}

TEST(SomeipSd, OptionsLengthMustFit) {
  Bytes offer = LoadHexFixture("sd_offer_multicast");
  offer[43] = 0x0D;  // options length 13, one byte more than present
  EXPECT_EQ(ParseSdMessage(offer.data(), offer.size()).error, SdParseError::kBadOptionsLength);
}

TEST(SomeipSd, Ipv4EndpointOptionMustHaveLengthNine) {
  Bytes offer = LoadHexFixture("sd_offer_multicast");
  offer[45] = 0x08;  // option length 8 for an IPv4 endpoint option
  EXPECT_EQ(ParseSdMessage(offer.data(), offer.size()).error, SdParseError::kBadOption);
}

TEST(SomeipSd, OptionReferenceOutsideTheOptionsIsRejected) {
  Bytes offer = LoadHexFixture("sd_offer_multicast");
  offer[25] = 0x01;  // first option index 1, but only option 0 exists
  EXPECT_EQ(ParseSdMessage(offer.data(), offer.size()).error, SdParseError::kBadOptionReference);
}

TEST(SomeipSd, UnknownOptionsAreSkippedButCounted) {
  // The offer with its endpoint option replaced by a configuration option (type 0x01).
  Bytes offer = LoadHexFixture("sd_offer_multicast");
  offer[46] = 0x01;
  const auto result = ParseSdMessage(offer.data(), offer.size());
  ASSERT_EQ(result.error, SdParseError::kNone);
  EXPECT_TRUE(result.message->entries.at(0).endpoints.empty());
}

TEST(Ipv4Text, ParsesAndPrintsDottedQuads) {
  EXPECT_EQ(Ipv4ToText(kHost), "10.250.0.1");
  EXPECT_EQ(ParseIpv4("192.168.98.1"), std::optional<std::uint32_t>{0xC0A86201});
  EXPECT_FALSE(ParseIpv4("192.168.98").has_value());
  EXPECT_FALSE(ParseIpv4("192.168.98.256").has_value());
  EXPECT_FALSE(ParseIpv4("a.b.c.d").has_value());
  EXPECT_FALSE(ParseIpv4("1.2.3.4 ").has_value());
}

}  // namespace
