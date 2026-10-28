// Pure core of the DE4SDV minimal SOME/IP receiver: the SOME/IP header and
// the SOME/IP-SD messages that the receiver reads and writes.
//
// The receiver reads OfferService, StopOffer, SubscribeEventgroupAck and
// SubscribeEventgroupNack entries. It writes SubscribeEventgroup and
// StopSubscribeEventgroup entries with one IPv4 endpoint option (TCP). All
// other entries and options are decoded far enough to skip them. Every
// length field is checked against the datagram; a message that fails a
// check is rejected as a whole. No socket call is made here.

#ifndef DE4SDV_SOMEIP_RECEIVER_SOMEIP_WIRE_HPP
#define DE4SDV_SOMEIP_RECEIVER_SOMEIP_WIRE_HPP

#include <cstddef>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace de4sdv::someip_receiver {

constexpr std::size_t kHeaderBytes = 16;
// The length field counts the bytes after itself: 8 header bytes plus the payload.
constexpr std::uint32_t kLengthFieldHeaderPart = 8;
constexpr std::uint16_t kSdServiceId = 0xFFFF;
constexpr std::uint16_t kSdMethodId = 0x8100;
constexpr std::uint16_t kSdPort = 30490;
constexpr std::uint8_t kProtocolVersion = 0x01;
constexpr std::uint8_t kSdInterfaceVersion = 0x01;
constexpr std::uint8_t kMessageTypeNotification = 0x02;
constexpr std::uint8_t kReturnCodeOk = 0x00;
constexpr std::uint8_t kSdFlagReboot = 0x80;
constexpr std::uint8_t kSdFlagUnicast = 0x40;
constexpr std::uint8_t kL4ProtocolTcp = 0x06;
constexpr std::uint8_t kL4ProtocolUdp = 0x11;
constexpr std::size_t kSdEntryBytes = 16;
constexpr std::uint32_t kMaxTtl = 0xFFFFFF;

struct Header {
  std::uint16_t service_id{0};
  std::uint16_t method_id{0};
  std::uint32_t length{0};
  std::uint16_t client_id{0};
  std::uint16_t session_id{0};
  std::uint8_t protocol_version{0};
  std::uint8_t interface_version{0};
  std::uint8_t message_type{0};
  std::uint8_t return_code{0};
};

// Reads the 16 header bytes. Fails when fewer than 16 bytes are given.
std::optional<Header> ParseHeader(const std::uint8_t* data, std::size_t size);

// A magic cookie message (service 0xFFFF, method 0x0000 or 0x8000) carries no data.
bool IsMagicCookie(const Header& header) noexcept;

// An IPv4 endpoint option. The address is in host byte order.
struct Ipv4Endpoint {
  std::uint32_t address{0};
  std::uint16_t port{0};
  std::uint8_t protocol{0};

  bool operator==(const Ipv4Endpoint& other) const noexcept {
    return address == other.address && port == other.port && protocol == other.protocol;
  }
};

enum class SdEntryType : std::uint8_t {
  kFindService = 0x00,
  kOfferService = 0x01,  // StopOffer when the TTL is 0
  kSubscribeEventgroup = 0x06,  // StopSubscribeEventgroup when the TTL is 0
  kSubscribeEventgroupAck = 0x07,  // Nack when the TTL is 0
};

struct SdEntry {
  std::uint8_t type{0};
  std::uint16_t service_id{0};
  std::uint16_t instance_id{0};
  std::uint8_t major_version{0};
  std::uint32_t ttl{0};
  std::uint32_t minor_version{0};  // service entries only
  std::uint16_t eventgroup_id{0};  // eventgroup entries only
  std::uint8_t counter{0};         // eventgroup entries only
  // The IPv4 endpoint options that the entry references, in option order.
  std::vector<Ipv4Endpoint> endpoints;
};

struct SdMessage {
  std::uint16_t session_id{0};
  bool reboot{false};
  bool unicast{false};
  std::vector<SdEntry> entries;
};

enum class SdParseError : std::uint8_t {
  kNone,
  kTooShort,
  kNotServiceDiscovery,  // other service, method, message type or protocol version
  kLengthMismatch,       // the SOME/IP length field disagrees with the datagram
  kBadEntriesLength,
  kBadOptionsLength,
  kBadOption,
  kBadOptionReference,
};

const char* ToText(SdParseError error) noexcept;

struct SdParseResult {
  std::optional<SdMessage> message;
  SdParseError error{SdParseError::kNone};
};

SdParseResult ParseSdMessage(const std::uint8_t* data, std::size_t size);

// One SubscribeEventgroup entry with one IPv4 endpoint option, in its own
// SOME/IP-SD message (client ID 0, interface version 1, unicast flag set).
// A TTL of 0 makes it a StopSubscribeEventgroup.
struct SubscribeRequest {
  std::uint16_t session_id{1};
  bool reboot{true};
  std::uint16_t service_id{0};
  std::uint16_t instance_id{0};
  std::uint8_t major_version{0};
  std::uint32_t ttl{0};
  std::uint16_t eventgroup_id{0};
  Ipv4Endpoint endpoint;
};

std::vector<std::uint8_t> EncodeSubscribeEventgroup(const SubscribeRequest& request);

// Text form a.b.c.d of a host-order IPv4 address, and its parse.
std::string Ipv4ToText(std::uint32_t address);
std::optional<std::uint32_t> ParseIpv4(const std::string& text);

}  // namespace de4sdv::someip_receiver

#endif  // DE4SDV_SOMEIP_RECEIVER_SOMEIP_WIRE_HPP
