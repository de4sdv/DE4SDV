#include "de4sdv_someip_receiver/someip_wire.hpp"

#include <cstdio>
#include <utility>

namespace de4sdv::someip_receiver {

namespace {

constexpr std::size_t kSdFixedBytes = 8;  // flags, reserved, entries length
constexpr std::size_t kOptionHeaderBytes = 3;  // length (2) and type (1)
constexpr std::uint16_t kIpv4EndpointOptionLength = 9;
constexpr std::uint8_t kIpv4EndpointOptionType = 0x04;

std::uint16_t Read16(const std::uint8_t* data) noexcept {
  return static_cast<std::uint16_t>((static_cast<unsigned>(data[0]) << 8U) | data[1]);
}

std::uint32_t Read24(const std::uint8_t* data) noexcept {
  return (static_cast<std::uint32_t>(data[0]) << 16U) | (static_cast<std::uint32_t>(data[1]) << 8U) | data[2];
}

std::uint32_t Read32(const std::uint8_t* data) noexcept {
  return (static_cast<std::uint32_t>(data[0]) << 24U) | (static_cast<std::uint32_t>(data[1]) << 16U) |
         (static_cast<std::uint32_t>(data[2]) << 8U) | data[3];
}

void Put16(std::vector<std::uint8_t>& out, std::uint16_t value) {
  out.push_back(static_cast<std::uint8_t>(value >> 8U));
  out.push_back(static_cast<std::uint8_t>(value & 0xFFU));
}

void Put24(std::vector<std::uint8_t>& out, std::uint32_t value) {
  out.push_back(static_cast<std::uint8_t>((value >> 16U) & 0xFFU));
  out.push_back(static_cast<std::uint8_t>((value >> 8U) & 0xFFU));
  out.push_back(static_cast<std::uint8_t>(value & 0xFFU));
}

void Put32(std::vector<std::uint8_t>& out, std::uint32_t value) {
  out.push_back(static_cast<std::uint8_t>(value >> 24U));
  out.push_back(static_cast<std::uint8_t>((value >> 16U) & 0xFFU));
  out.push_back(static_cast<std::uint8_t>((value >> 8U) & 0xFFU));
  out.push_back(static_cast<std::uint8_t>(value & 0xFFU));
}

// One option of the options array; endpoint is set for an IPv4 endpoint option only.
struct Option {
  std::optional<Ipv4Endpoint> endpoint;
};

SdParseResult Failure(SdParseError error) {
  SdParseResult result;
  result.error = error;
  return result;
}

bool AppendEndpoints(const std::vector<Option>& options, unsigned first, unsigned count,
                     std::vector<Ipv4Endpoint>& endpoints) {
  if (count == 0U) {
    return true;
  }
  if (first + count > options.size()) {
    return false;
  }
  for (unsigned index = first; index < first + count; ++index) {
    if (options[index].endpoint.has_value()) {
      endpoints.push_back(*options[index].endpoint);
    }
  }
  return true;
}

}  // namespace

std::optional<Header> ParseHeader(const std::uint8_t* data, std::size_t size) {
  if (data == nullptr || size < kHeaderBytes) {
    return std::nullopt;
  }
  Header header;
  header.service_id = Read16(data);
  header.method_id = Read16(data + 2);
  header.length = Read32(data + 4);
  header.client_id = Read16(data + 8);
  header.session_id = Read16(data + 10);
  header.protocol_version = data[12];
  header.interface_version = data[13];
  header.message_type = data[14];
  header.return_code = data[15];
  return header;
}

bool IsMagicCookie(const Header& header) noexcept {
  return header.service_id == 0xFFFF && (header.method_id == 0x0000 || header.method_id == 0x8000);
}

const char* ToText(SdParseError error) noexcept {
  switch (error) {
    case SdParseError::kNone:
      return "none";
    case SdParseError::kTooShort:
      return "too_short";
    case SdParseError::kNotServiceDiscovery:
      return "not_service_discovery";
    case SdParseError::kLengthMismatch:
      return "length_mismatch";
    case SdParseError::kBadEntriesLength:
      return "bad_entries_length";
    case SdParseError::kBadOptionsLength:
      return "bad_options_length";
    case SdParseError::kBadOption:
      return "bad_option";
    case SdParseError::kBadOptionReference:
      return "bad_option_reference";
  }
  return "unknown";
}

SdParseResult ParseSdMessage(const std::uint8_t* data, std::size_t size) {
  const auto header = ParseHeader(data, size);
  if (!header.has_value()) {
    return Failure(SdParseError::kTooShort);
  }
  if (header->service_id != kSdServiceId || header->method_id != kSdMethodId ||
      header->protocol_version != kProtocolVersion || header->message_type != kMessageTypeNotification) {
    return Failure(SdParseError::kNotServiceDiscovery);
  }
  if (static_cast<std::uint64_t>(header->length) + kLengthFieldHeaderPart != size) {
    return Failure(SdParseError::kLengthMismatch);
  }
  const std::uint8_t* sd = data + kHeaderBytes;
  const std::size_t sd_size = size - kHeaderBytes;
  if (sd_size < kSdFixedBytes) {
    return Failure(SdParseError::kTooShort);
  }
  SdMessage message;
  message.session_id = header->session_id;
  message.reboot = (sd[0] & kSdFlagReboot) != 0U;
  message.unicast = (sd[0] & kSdFlagUnicast) != 0U;

  const std::uint32_t entries_length = Read32(sd + 4);
  if (entries_length % kSdEntryBytes != 0U ||
      static_cast<std::uint64_t>(entries_length) + kSdFixedBytes + 4U > sd_size) {
    return Failure(SdParseError::kBadEntriesLength);
  }
  const std::uint8_t* entries = sd + kSdFixedBytes;
  const std::uint8_t* options_field = entries + entries_length;
  const std::size_t after_entries = sd_size - kSdFixedBytes - entries_length;
  const std::uint32_t options_length = Read32(options_field);
  if (static_cast<std::uint64_t>(options_length) + 4U != after_entries) {
    return Failure(SdParseError::kBadOptionsLength);
  }

  std::vector<Option> options;
  const std::uint8_t* option = options_field + 4;
  std::size_t remaining = options_length;
  while (remaining > 0U) {
    if (remaining < kOptionHeaderBytes) {
      return Failure(SdParseError::kBadOptionsLength);
    }
    const std::uint16_t length = Read16(option);
    const std::uint8_t type = option[2];
    if (kOptionHeaderBytes + static_cast<std::size_t>(length) > remaining) {
      return Failure(SdParseError::kBadOptionsLength);
    }
    Option parsed;
    if (type == kIpv4EndpointOptionType) {
      if (length != kIpv4EndpointOptionLength) {
        return Failure(SdParseError::kBadOption);
      }
      // reserved, address (4), reserved, L4 protocol, port (2)
      parsed.endpoint = Ipv4Endpoint{Read32(option + 4), Read16(option + 10), option[9]};
    }
    options.push_back(parsed);
    option += kOptionHeaderBytes + length;
    remaining -= kOptionHeaderBytes + length;
  }

  for (std::size_t offset = 0; offset < entries_length; offset += kSdEntryBytes) {
    const std::uint8_t* raw = entries + offset;
    SdEntry entry;
    entry.type = raw[0];
    const unsigned first_index = raw[1];
    const unsigned second_index = raw[2];
    const unsigned first_count = raw[3] >> 4U;
    const unsigned second_count = raw[3] & 0x0FU;
    entry.service_id = Read16(raw + 4);
    entry.instance_id = Read16(raw + 6);
    entry.major_version = raw[8];
    entry.ttl = Read24(raw + 9);
    if (entry.type == static_cast<std::uint8_t>(SdEntryType::kSubscribeEventgroup) ||
        entry.type == static_cast<std::uint8_t>(SdEntryType::kSubscribeEventgroupAck)) {
      entry.counter = static_cast<std::uint8_t>(raw[13] & 0x0FU);
      entry.eventgroup_id = Read16(raw + 14);
    } else {
      entry.minor_version = Read32(raw + 12);
    }
    if (!AppendEndpoints(options, first_index, first_count, entry.endpoints) ||
        !AppendEndpoints(options, second_index, second_count, entry.endpoints)) {
      return Failure(SdParseError::kBadOptionReference);
    }
    message.entries.push_back(std::move(entry));
  }
  SdParseResult result;
  result.message = std::move(message);
  return result;
}

std::vector<std::uint8_t> EncodeSubscribeEventgroup(const SubscribeRequest& request) {
  constexpr std::uint32_t kEntriesLength = 16;
  constexpr std::uint32_t kOptionsLength = 12;
  constexpr std::uint32_t kSdPayload = 4 + 4 + kEntriesLength + 4 + kOptionsLength;
  std::vector<std::uint8_t> out;
  out.reserve(kHeaderBytes + kSdPayload);
  Put16(out, kSdServiceId);
  Put16(out, kSdMethodId);
  Put32(out, kLengthFieldHeaderPart + kSdPayload);
  Put16(out, 0x0000);  // client ID of SOME/IP-SD
  Put16(out, request.session_id);
  out.push_back(kProtocolVersion);
  out.push_back(kSdInterfaceVersion);
  out.push_back(kMessageTypeNotification);
  out.push_back(kReturnCodeOk);
  out.push_back(static_cast<std::uint8_t>((request.reboot ? kSdFlagReboot : 0U) | kSdFlagUnicast));
  Put24(out, 0);
  Put32(out, kEntriesLength);
  out.push_back(static_cast<std::uint8_t>(SdEntryType::kSubscribeEventgroup));
  out.push_back(0x00);  // index of the first option run
  out.push_back(0x00);  // index of the second option run
  out.push_back(0x10);  // one option in the first run, none in the second
  Put16(out, request.service_id);
  Put16(out, request.instance_id);
  out.push_back(request.major_version);
  Put24(out, request.ttl & kMaxTtl);
  out.push_back(0x00);  // reserved
  out.push_back(0x00);  // initial data requested flag, reserved, counter
  Put16(out, request.eventgroup_id);
  Put32(out, kOptionsLength);
  Put16(out, kIpv4EndpointOptionLength);
  out.push_back(kIpv4EndpointOptionType);
  out.push_back(0x00);
  Put32(out, request.endpoint.address);
  out.push_back(0x00);
  out.push_back(request.endpoint.protocol);
  Put16(out, request.endpoint.port);
  return out;
}

std::string Ipv4ToText(std::uint32_t address) {
  char text[16];
  std::snprintf(text, sizeof(text), "%u.%u.%u.%u", (address >> 24U) & 0xFFU, (address >> 16U) & 0xFFU,
                (address >> 8U) & 0xFFU, address & 0xFFU);
  return text;
}

std::optional<std::uint32_t> ParseIpv4(const std::string& text) {
  std::uint32_t address = 0;
  unsigned parts = 0;
  unsigned value = 0;
  unsigned digits = 0;
  for (std::size_t i = 0; i <= text.size(); ++i) {
    if (i == text.size() || text[i] == '.') {
      if (digits == 0U || value > 255U || parts == 4U) {
        return std::nullopt;
      }
      address = (address << 8U) | value;
      ++parts;
      value = 0;
      digits = 0;
      continue;
    }
    const char c = text[i];
    if (c < '0' || c > '9' || digits == 3U) {
      return std::nullopt;
    }
    value = value * 10U + static_cast<unsigned>(c - '0');
    ++digits;
  }
  if (parts != 4U) {
    return std::nullopt;
  }
  return address;
}

}  // namespace de4sdv::someip_receiver
