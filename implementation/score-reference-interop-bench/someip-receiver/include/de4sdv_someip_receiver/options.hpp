// Pure core of the DE4SDV minimal SOME/IP receiver: the command line.
//
// The server address and the clock-offset bound have no default: the bench
// that starts the receiver states both. The defaults of the other options
// are the identifiers of the gateway spike (service 0x4dee, instance 1,
// event 0x8001 on TCP 30509, eventgroup 1, SD on UDP 30490 with group
// 224.244.224.245) and the loopback port 4731 of the HMI ingress. The
// receiver listens on a loopback address only. The start log line repeats
// every value.

#ifndef DE4SDV_SOMEIP_RECEIVER_OPTIONS_HPP
#define DE4SDV_SOMEIP_RECEIVER_OPTIONS_HPP

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

#include "de4sdv_someip_receiver/event_log.hpp"
#include "de4sdv_someip_receiver/receiver_core.hpp"

namespace de4sdv::someip_receiver {

struct ReceiverOptions {
  ReceiverConfig receiver;
  std::uint32_t listen_address{0x7F000001};  // 127.0.0.1
  std::uint16_t listen_port{4731};
  bool join_multicast{true};
  std::uint32_t multicast_group{0xE0F4E0F5};  // 224.244.224.245
  std::uint32_t multicast_interface{0};       // 0.0.0.0: the kernel picks the interface by route
  std::int64_t clock_offset_bound_ns{0};
  std::int64_t status_period_ns{10 * kNanosecondsPerSecond};
  std::int64_t client_write_timeout_ns{500 * kNanosecondsPerMillisecond};
};

struct ParsedOptions {
  std::optional<ReceiverOptions> options;
  bool help{false};
  std::string error;
};

// arguments excludes the program name.
ParsedOptions ParseOptions(const std::vector<std::string>& arguments);
std::string Usage();
// The start log line: every option value, the policy name and the pid.
LogRecord StartRecord(const ReceiverOptions& options, const char* policy_name, std::int64_t pid);

}  // namespace de4sdv::someip_receiver

#endif  // DE4SDV_SOMEIP_RECEIVER_OPTIONS_HPP
