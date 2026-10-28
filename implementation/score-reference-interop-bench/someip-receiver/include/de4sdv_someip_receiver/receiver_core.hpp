// Pure core of the DE4SDV minimal SOME/IP receiver: one object that holds
// the subscription, the SOME/IP-over-TCP reassembly, the payload checks and
// the discard policy, and decides for every frame whether it goes to the
// loopback client of the HMI ingress.
//
// The I/O shell feeds it the socket events and implements its ports. Each
// notification of the frame event ends in exactly one outcome: delivered,
// or dropped with one reason. So frames_received equals frames_delivered
// plus the sum of the drops. The receiver holds no queue: a frame that
// finds no client, or no subscription, is dropped at once.

#ifndef DE4SDV_SOMEIP_RECEIVER_RECEIVER_CORE_HPP
#define DE4SDV_SOMEIP_RECEIVER_RECEIVER_CORE_HPP

#include <array>
#include <cstddef>
#include <cstdint>

#include "de4sdv_someip_receiver/discard_policy.hpp"
#include "de4sdv_someip_receiver/event_log.hpp"
#include "de4sdv_someip_receiver/someip_stream.hpp"
#include "de4sdv_someip_receiver/subscription.hpp"

namespace de4sdv::someip_receiver {

struct ReceiverConfig {
  SubscriptionConfig subscription;
  std::uint16_t event_id{0x8001};
  // The largest payload: the 4-byte prefix and a frame of up to 2044 bytes
  // in the 2048-byte sample of the S-CORE frame event.
  std::size_t max_payload_bytes{2048};
  // One "frame" log line per notification of the frame event.
  bool log_frames{false};
};

// The loopback client of the HMI ingress, implemented by the shell.
class FrameSink {
 public:
  virtual ~FrameSink() = default;
  // Writes the whole payload; false when the write failed and the shell
  // closed the client.
  virtual bool Forward(const std::uint8_t* payload, std::size_t size) = 0;
};

enum class DropReason : std::uint8_t {
  kMalformedNotification,  // wrong message type, return code or versions
  kPayloadTooLarge,
  kLengthPrefixMismatch,
  kFrameUnreadable,
  kNotSubscribed,
  kNoClient,
  kSequenceNotIncreasing,
  kOlderThanPhase,
  kClientWriteFailed,
};

constexpr std::size_t kDropReasonCount = 9;

const char* ToText(DropReason reason) noexcept;

struct ReceiverCounters {
  std::uint64_t sd_datagrams{0};
  std::uint64_t sd_malformed{0};
  std::uint64_t stream_messages{0};
  std::uint64_t magic_cookies{0};
  std::uint64_t other_messages{0};  // not the frame event: neither a frame nor a drop
  std::uint64_t stream_framing_errors{0};
  std::uint64_t frames_received{0};
  std::uint64_t frames_delivered{0};
  std::array<std::uint64_t, kDropReasonCount> drops{};
  std::uint64_t clients_connected{0};
  std::uint64_t clients_lost{0};
  std::uint64_t phases_by_subscription{0};
  std::uint64_t phases_by_client{0};

  std::uint64_t frames_dropped() const noexcept;
};

class ReceiverCore final : private SubscriptionTransport, private SubscriptionListener {
 public:
  ReceiverCore(const ReceiverConfig& config, SubscriptionTransport& transport, FrameSink& sink,
               FrameDiscardPolicy& policy, EventLog& log);

  void OnTick(const Clock& now);
  void OnSdDatagram(const Clock& now, std::uint32_t source_address, bool multicast, const std::uint8_t* data,
                    std::size_t size);
  void OnTcpConnected(const Clock& now, const Ipv4Endpoint& local);
  void OnTcpConnectFailed(const Clock& now, int error_number);
  void OnTcpData(const Clock& now, const std::uint8_t* data, std::size_t size);
  void OnTcpClosed(const Clock& now);
  void OnClientConnected(const Clock& now);
  void OnClientDisconnected(const Clock& now);
  void Stop(const Clock& now);

  std::int64_t NextDeadline() const noexcept { return machine_.NextDeadline(); }
  bool subscribed() const noexcept { return machine_.subscribed(); }
  bool client_connected() const noexcept { return client_connected_; }
  const ReceiverCounters& counters() const noexcept { return counters_; }
  const SubscriptionMachine& subscription() const noexcept { return machine_; }
  // A status line with every counter.
  LogRecord Status(const char* event) const;

 private:
  // SubscriptionTransport: forwards to the shell and keeps the reassembly
  // in step with the TCP connection.
  void ConnectTcp(const Ipv4Endpoint& server) override;
  void CloseTcp() override;
  bool SendSd(const std::vector<std::uint8_t>& datagram, std::uint32_t address, std::uint16_t port) override;
  // SubscriptionListener: subscription phases.
  void OnSubscribed(const Clock& now) override;
  void OnSubscriptionLost(const Clock& now, SubscriptionLoss loss) override;

  void OnMessage(const Clock& now, const Header& header, const std::uint8_t* payload, std::size_t size);
  void Drop(const Clock& now, DropReason reason, const Header& header, std::size_t size, const FrameFields* fields);
  void LogFrame(const Clock& now, const char* verdict, const Header& header, std::size_t size,
                const FrameFields* fields);
  void StartPhase(const Clock& now, PhaseCause cause);

  ReceiverConfig config_;
  SubscriptionTransport& transport_;
  FrameSink& sink_;
  FrameDiscardPolicy& policy_;
  EventLog& log_;
  SubscriptionMachine machine_;
  SomeipStreamReassembler reassembler_;
  bool client_connected_{false};
  ReceiverCounters counters_{};
};

}  // namespace de4sdv::someip_receiver

#endif  // DE4SDV_SOMEIP_RECEIVER_RECEIVER_CORE_HPP
