// Pure core of the DE4SDV IVI frame relay: the command line.
//
// The defaults name the broker's publication of the feasibility run of
// 2026-10-28 (design data): instance1:com.android.sdv.someip.SomeIpBroker/
// default, unit de4sdv-score-aebs-signal-frame. Phase 10 sets the mapping,
// so an option can follow it without a new build. The relay's own subject
// for initComms, which its ACL names, defaults to de4sdv.ivi_frame_relay,
// bundle IviFrameRelay, instance default (the relay's reading, not a value
// of the model). A name longer than the C API holds
// is refused, so the relay never subscribes to a truncated name.
//
// No option sets the loopback server (127.0.0.1:4731), the subscriber flag
// (ASDVGATEWAY_SUBSCRIBER_OPTIONS_FLAG_NONE), the timing of the
// subscription, or the discard rule. Its margin is fixed at 20 ms, the bound
// of ASM-MW-030, and its copy window at 40 frames: an option that names a
// margin or a bound stops the relay at start. The start log line repeats
// every value.

#ifndef DE4SDV_IVI_FRAME_RELAY_OPTIONS_HPP
#define DE4SDV_IVI_FRAME_RELAY_OPTIONS_HPP

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

#include "de4sdv_ivi_frame_relay/event_log.hpp"
#include "de4sdv_ivi_frame_relay/gateway_client.hpp"
#include "de4sdv_ivi_frame_relay/relay_core.hpp"

namespace de4sdv::ivi_frame_relay {

// The loopback server: 127.0.0.1:4731 of the IVI VM, so a leftover forward
// of the frame assembler's 4721 cannot stand in for the relay.
constexpr std::uint32_t kListenAddress = 0x7F000001;
constexpr std::uint16_t kListenPort = 4731;

// The largest names of the C API, without the NUL.
constexpr std::size_t kMaxVmNameChars = 31;
constexpr std::size_t kMaxPackageNameChars = 127;
constexpr std::size_t kMaxBundleNameChars = 47;
constexpr std::size_t kMaxInstanceNameChars = 47;
constexpr std::size_t kMaxUnitNameChars = 127;

struct RelayOptions {
  RelayConfig relay;
  SubjectIdentity subject{"de4sdv.ivi_frame_relay", "IviFrameRelay", "default"};
  PublicationName publication{"instance1", "com.android.sdv.someip", "SomeIpBroker",
                              "de4sdv-score-aebs-signal-frame"};
  std::int64_t status_period_ns{10 * kNanosecondsPerSecond};
  // name=value of the system properties that the relay sets, in this order,
  // once its loopback server listens (Android only): the ingress reads its
  // frame server from two of them and starts on a third one, so it starts
  // only after the relay listens, also after a restart of the relay.
  std::vector<std::string> announce_properties;
  std::int64_t client_write_timeout_ns{500 * kNanosecondsPerMillisecond};
};

struct ParsedOptions {
  std::optional<RelayOptions> options;
  bool help{false};
  std::string error;
};

// arguments excludes the program name.
ParsedOptions ParseOptions(const std::vector<std::string>& arguments);
std::string Usage();
// The start log line: every option value, the fixed values and the pid.
LogRecord StartRecord(const RelayOptions& options, const char* policy_name, std::int64_t pid);
// Splits the value of --announce-property; false when it is not name=value.
bool SplitProperty(const std::string& text, std::string* name, std::string* value);

}  // namespace de4sdv::ivi_frame_relay

#endif  // DE4SDV_IVI_FRAME_RELAY_OPTIONS_HPP
