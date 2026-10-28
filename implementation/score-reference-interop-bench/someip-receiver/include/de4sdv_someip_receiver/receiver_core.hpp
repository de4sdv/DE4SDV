// Pure core of the DE4SDV minimal SOME/IP receiver: one object that holds
// the subscription, the SOME/IP-over-TCP reassembly, the payload checks, the
// subscription phase and the discard policy, and decides for every frame
// whether it goes to the loopback client of the HMI ingress.
//
// Subscription phase (receiverSubscriptionPhaseDiscardRule): a phase holds
// while the receiver is subscribed at someipd and the ingress is its only
// loopback client. It starts when the second of the two conditions starts to
// hold, at the receiver's CLOCK_REALTIME, and ends when one of them ends. The
// acknowledgement of a renewal changes nothing. A second client is refused
// and starts no phase. Outside a phase every frame is read and dropped.
//
// Clock controls for ASM-MW-030: the core reads CLOCK_REALTIME minus
// CLOCK_MONOTONIC at every event, and the shell gives it an event at least
// every 100 ms. A slew moves both clocks alike, so this difference changes
// only when the realtime clock is stepped or across a suspend. A change of
// 1 ms or more between two readings is a clock step: it is logged, and the
// phase it falls in is marked. The start, each phase start and each status
// record log the difference. Every served frame logs its receipt time minus
// its frame_timestamp_ns (only the first five of a phase without
// --log-frames), and the phase end and the status records log the minimum
// and maximum of that value in the phase. The minimum bounds the host-guest
// offset from one side only: a negative minimum shows a guest clock that is
// behind the host clock by at least that much; a guest clock ahead looks
// like latency.
//
// Start of the HMI ingress: the ingress is a oneshot service. It exits when
// its connect fails or its stream closes, and init does not start a service
// again while it runs or before init has reaped it. So the core sets the
// start property of the ingress to 0 and then 1 once the loopback server
// listens. When this start of the receiver follows the end of an old
// receiver, its old ingress may still run or not be reaped yet, and that
// trigger does nothing. So, until the first client of this receiver process
// connects, the core repeats the trigger every 1 s, at most 10 times, and
// logs ingress_trigger_gave_up 1 s after the last try. After the first
// client, the core never triggers the ingress again in this process: an
// ingress that exits by itself or is stopped on purpose stays down. Each
// try gives one log line.
//
// The I/O shell feeds the core the socket events and implements its ports.
// Each notification of the frame event ends in exactly one outcome:
// delivered, or dropped with one reason. So frames_received equals
// frames_delivered plus the sum of the drops. The receiver holds no queue.

#ifndef DE4SDV_SOMEIP_RECEIVER_RECEIVER_CORE_HPP
#define DE4SDV_SOMEIP_RECEIVER_RECEIVER_CORE_HPP

#include <array>
#include <cstddef>
#include <cstdint>
#include <string>

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
  // One "frame" log line per served frame of the event. Every dropped frame
  // gives its line anyway, with its reason; without this flag only the first
  // five served frames of a phase give one.
  bool log_frames{false};
  // The system property that starts the HMI ingress; empty: no trigger.
  std::string ingress_start_property;
};

constexpr std::int64_t kClockStepThresholdNs = 1'000'000;
constexpr std::uint64_t kFirstFramesLoggedPerPhase = 5;
constexpr std::int64_t kIngressRetriggerPeriodNs = 1'000'000'000;
// A malformed SD datagram of the server gives at most one log line per second.
constexpr std::int64_t kMalformedLogPeriodNs = 1'000'000'000;
constexpr std::uint64_t kIngressRetriggerLimit = 10;

// The loopback client of the HMI ingress, implemented by the shell.
class FrameSink {
 public:
  virtual ~FrameSink() = default;
  // Writes the whole payload; false when the write failed and the shell
  // closed the client.
  virtual bool Forward(const std::uint8_t* payload, std::size_t size) = 0;
};

// Sets a system property, implemented by the shell: on Android with
// __system_property_set; elsewhere it only logs the property.
class PropertySetter {
 public:
  virtual ~PropertySetter() = default;
  virtual bool SetProperty(const Clock& now, const std::string& name, const std::string& value) = 0;
};

enum class DropReason : std::uint8_t {
  kMalformedNotification,  // wrong message type, return code or versions
  kPayloadTooLarge,
  kLengthPrefixMismatch,
  kFrameUnreadable,
  kNotSubscribed,  // outside a phase: no subscription
  kNoClient,       // outside a phase: subscribed, but no client
  kFieldNotPositive,
  kOlderThanPhase,
  kCopyInPhase,
  kClientWriteFailed,
};

constexpr std::size_t kDropReasonCount = 10;

const char* ToText(DropReason reason) noexcept;

struct ReceiverCounters {
  std::uint64_t sd_datagrams{0};
  std::uint64_t sd_datagrams_from_other_senders{0};  // counted, not parsed, not logged
  std::uint64_t sd_malformed{0};
  std::uint64_t stream_messages{0};
  std::uint64_t magic_cookies{0};
  std::uint64_t other_messages{0};  // not the frame event: neither a frame nor a drop
  std::uint64_t stream_framing_errors{0};
  std::uint64_t frames_received{0};
  std::uint64_t frames_delivered{0};
  std::array<std::uint64_t, kDropReasonCount> drops{};
  std::uint64_t clients_accepted{0};
  std::uint64_t clients_refused{0};
  std::uint64_t clients_lost{0};
  std::uint64_t phases_started{0};
  std::uint64_t phases_ended{0};
  std::uint64_t clock_steps{0};
  std::uint64_t ingress_triggers{0};

  std::uint64_t frames_dropped() const noexcept;
};

class ReceiverCore final : private SubscriptionTransport, private SubscriptionListener {
 public:
  ReceiverCore(const ReceiverConfig& config, SubscriptionTransport& transport, FrameSink& sink,
               FrameDiscardPolicy& policy, EventLog& log, PropertySetter* properties = nullptr);

  void OnTick(const Clock& now);
  // The loopback server listens: the first trigger of the ingress.
  void OnListening(const Clock& now);
  // Reads the offset of the two clocks; every event calls it, and the shell
  // calls it once at start.
  void ObserveClock(const Clock& now);
  void OnSdDatagram(const Clock& now, std::uint32_t source_address, bool multicast, const std::uint8_t* data,
                    std::size_t size);
  void OnTcpConnected(const Clock& now, const Ipv4Endpoint& local);
  void OnTcpConnectFailed(const Clock& now, int error_number);
  void OnTcpData(const Clock& now, const std::uint8_t* data, std::size_t size);
  void OnTcpClosed(const Clock& now);
  // A loopback client connected. false: another client is connected, so the
  // shell closes the new one; it is not served and starts no phase.
  bool OnClientAccepted(const Clock& now);
  void OnClientDisconnected(const Clock& now);
  void Stop(const Clock& now);

  std::int64_t NextDeadline() const noexcept;
  bool subscribed() const noexcept { return machine_.subscribed(); }
  bool client_connected() const noexcept { return client_connected_; }
  bool in_phase() const noexcept { return in_phase_; }
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
  // Starts or ends the phase when the two conditions change; cause names the change.
  void UpdatePhase(const Clock& now, const std::string& cause);
  bool IngressTriggerDue() const noexcept;
  void TriggerIngress(const Clock& now, const char* reason);

  ReceiverConfig config_;
  SubscriptionTransport& transport_;
  FrameSink& sink_;
  FrameDiscardPolicy& policy_;
  EventLog& log_;
  PropertySetter* properties_;
  SubscriptionMachine machine_;
  SomeipStreamReassembler reassembler_;
  bool client_connected_{false};
  bool in_phase_{false};
  std::int64_t phase_start_realtime_ns_{0};
  std::uint64_t phase_clock_steps_{0};
  std::uint64_t phase_served_{0};
  std::int64_t phase_receipt_min_ns_{0};
  std::int64_t phase_receipt_max_ns_{0};
  bool clock_seen_{false};
  std::int64_t clock_offset_ns_{0};
  bool malformed_logged_{false};
  std::int64_t malformed_logged_ns_{0};
  std::uint64_t malformed_suppressed_{0};
  bool listening_{false};
  bool first_client_seen_{false};
  bool ingress_trigger_gave_up_{false};
  std::int64_t next_ingress_trigger_ns_{0};
  std::uint64_t ingress_retriggers_{0};
  ReceiverCounters counters_{};
};

}  // namespace de4sdv::someip_receiver

#endif  // DE4SDV_SOMEIP_RECEIVER_RECEIVER_CORE_HPP
