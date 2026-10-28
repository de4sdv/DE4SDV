// Pure core of the DE4SDV minimal SOME/IP receiver: the subscription to the
// frame eventgroup of someipd on the Linux host.
//
// The state machine connects TCP to the reliable endpoint of the service,
// then sends SubscribeEventgroup with an IPv4 endpoint option that names
// the local end of that TCP connection, as someipd expects. It renews the
// subscription before its TTL ends and treats a TTL that ends without an
// Ack as a lost subscription.
//
// It listens for offers of the configured server, but it does not need
// one: without an offer it tries the configured server and reliable port
// every connect_retry_period (the unicast fallback, for a guest that
// receives no multicast). A valid offer starts a connection at once. A
// StopOffer, a Nack, a closed TCP connection or a detected reboot of the
// server ends the connection; the machine then starts again.
//
// SD messages of other senders are ignored. All times are CLOCK_MONOTONIC
// nanoseconds; the realtime clock is only passed through to the listener.

#ifndef DE4SDV_SOMEIP_RECEIVER_SUBSCRIPTION_HPP
#define DE4SDV_SOMEIP_RECEIVER_SUBSCRIPTION_HPP

#include <cstdint>
#include <vector>

#include "de4sdv_someip_receiver/event_log.hpp"
#include "de4sdv_someip_receiver/someip_wire.hpp"

namespace de4sdv::someip_receiver {

constexpr std::int64_t kNanosecondsPerMillisecond = 1'000'000;
constexpr std::int64_t kNanosecondsPerSecond = 1'000'000'000;
constexpr std::int64_t kNoDeadline = INT64_MAX;

struct SubscriptionConfig {
  std::uint32_t server_address{0};
  std::uint16_t sd_port{kSdPort};
  std::uint16_t reliable_port{30509};
  std::uint16_t service_id{0x4DEE};
  std::uint16_t instance_id{0x0001};
  std::uint8_t major_version{1};
  std::uint16_t eventgroup_id{0x0001};
  std::uint32_t ttl_s{3};
  std::int64_t renew_period_ns{1000 * kNanosecondsPerMillisecond};
  std::int64_t subscribe_delay_ns{20 * kNanosecondsPerMillisecond};
  std::int64_t subscribe_timeout_ns{6000 * kNanosecondsPerMillisecond};
  std::int64_t connect_timeout_ns{2000 * kNanosecondsPerMillisecond};
  std::int64_t connect_retry_period_ns{500 * kNanosecondsPerMillisecond};
};

// Implemented by the I/O shell.
class SubscriptionTransport {
 public:
  virtual ~SubscriptionTransport() = default;
  // Starts a non-blocking TCP connection; the shell answers with
  // OnTcpConnected() or OnTcpConnectFailed().
  virtual void ConnectTcp(const Ipv4Endpoint& server) = 0;
  // Closes the TCP connection, or the connection attempt; idempotent.
  virtual void CloseTcp() = 0;
  // Sends one datagram from the SD socket; false when the send failed.
  virtual bool SendSd(const std::vector<std::uint8_t>& datagram, std::uint32_t address, std::uint16_t port) = 0;
};

enum class SubscriptionState : std::uint8_t {
  kIdle,
  kConnecting,
  kSubscribing,  // TCP connected, no Ack yet
  kSubscribed,
  kStopped,
};

const char* ToText(SubscriptionState state) noexcept;

enum class SubscriptionLoss : std::uint8_t {
  kTtlExpired,
  kNack,
  kTcpClosed,
  kStopOffer,
  kServerReboot,
  kStreamFramingLost,
  kStopped,
};

const char* ToText(SubscriptionLoss loss) noexcept;

class SubscriptionListener {
 public:
  virtual ~SubscriptionListener() = default;
  // The machine entered kSubscribed from another state: a subscription phase starts.
  virtual void OnSubscribed(const Clock& now) = 0;
  // The machine left kSubscribed.
  virtual void OnSubscriptionLost(const Clock& now, SubscriptionLoss loss) = 0;
};

struct SubscriptionCounters {
  std::uint64_t offers{0};
  std::uint64_t stop_offers{0};
  std::uint64_t sd_messages_from_other_senders{0};
  std::uint64_t sd_entries_ignored{0};
  std::uint64_t server_reboots_detected{0};
  std::uint64_t tcp_connect_attempts{0};
  std::uint64_t tcp_connects{0};
  std::uint64_t tcp_connect_failures{0};
  std::uint64_t tcp_closed_by_peer{0};
  std::uint64_t subscribes_sent{0};
  std::uint64_t subscribe_send_failures{0};
  std::uint64_t stop_subscribes_sent{0};
  std::uint64_t acks{0};
  std::uint64_t acks_unexpected{0};
  std::uint64_t nacks{0};
  std::uint64_t subscription_phases{0};
  std::uint64_t ttl_expiries{0};
  std::uint64_t subscribe_timeouts{0};
};

class SubscriptionMachine {
 public:
  SubscriptionMachine(const SubscriptionConfig& config, SubscriptionTransport& transport,
                      SubscriptionListener& listener, EventLog& log);

  void OnTick(const Clock& now);
  // A parsed SD message from source_address; multicast when it was sent to the group.
  void OnSdMessage(const Clock& now, const SdMessage& message, std::uint32_t source_address, bool multicast);
  void OnTcpConnected(const Clock& now, const Ipv4Endpoint& local);
  void OnTcpConnectFailed(const Clock& now, int error_number);
  void OnTcpClosed(const Clock& now);
  void OnStreamFramingLost(const Clock& now);
  // Sends StopSubscribeEventgroup when subscribing or subscribed, closes TCP, and stops.
  void Stop(const Clock& now);

  // The next CLOCK_MONOTONIC time at which OnTick() has work; kNoDeadline when none.
  std::int64_t NextDeadline() const noexcept;

  SubscriptionState state() const noexcept { return state_; }
  bool subscribed() const noexcept { return state_ == SubscriptionState::kSubscribed; }
  bool has_offer() const noexcept { return has_offer_; }
  const SubscriptionCounters& counters() const noexcept { return counters_; }
  std::uint16_t next_session_id() const noexcept { return session_id_; }
  bool reboot_flag() const noexcept { return reboot_flag_; }

 private:
  // The session ID and reboot flag of the last SD message per channel of the server.
  struct SessionTracker {
    bool seen{false};
    std::uint16_t session_id{0};
    bool reboot{false};
    // True when this message shows a reboot of the sender.
    bool Observe(std::uint16_t session, bool reboot_flag) noexcept;
  };

  bool Matches(const SdEntry& entry) const noexcept;
  void StartConnect(const Clock& now, const char* trigger);
  void EnterIdle(const Clock& now, std::int64_t retry_delay_ns);
  void EndConnection(const Clock& now, SubscriptionLoss loss, std::int64_t retry_delay_ns);
  bool SendSubscribe(const Clock& now, std::uint32_t ttl);
  void HandleOffer(const Clock& now, const SdEntry& entry, bool multicast, std::uint16_t session);
  void HandleAck(const Clock& now, const SdEntry& entry, std::uint16_t session);
  Ipv4Endpoint ConnectTarget() const noexcept;

  SubscriptionConfig config_;
  SubscriptionTransport& transport_;
  SubscriptionListener& listener_;
  EventLog& log_;

  SubscriptionState state_{SubscriptionState::kIdle};
  std::int64_t next_connect_ns_{0};
  std::int64_t connecting_since_ns_{0};
  std::int64_t subscribing_since_ns_{0};
  std::int64_t next_subscribe_ns_{0};
  std::int64_t ack_expiry_ns_{0};
  std::int64_t next_renew_ns_{0};
  Ipv4Endpoint tcp_local_{};
  Ipv4Endpoint tcp_remote_{};

  bool has_offer_{false};
  Ipv4Endpoint offer_endpoint_{};
  std::int64_t offer_expiry_ns_{0};

  std::uint16_t session_id_{1};
  bool reboot_flag_{true};
  SessionTracker multicast_sessions_{};
  SessionTracker unicast_sessions_{};
  SubscriptionCounters counters_{};
};

}  // namespace de4sdv::someip_receiver

#endif  // DE4SDV_SOMEIP_RECEIVER_SUBSCRIPTION_HPP
