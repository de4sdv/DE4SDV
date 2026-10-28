#include "de4sdv_someip_receiver/subscription.hpp"

#include <algorithm>
#include <string>

namespace de4sdv::someip_receiver {

namespace {

bool IsConnected(SubscriptionState state) noexcept {
  return state == SubscriptionState::kSubscribing || state == SubscriptionState::kSubscribed;
}

std::uint8_t TypeOf(SdEntryType type) noexcept { return static_cast<std::uint8_t>(type); }

std::string EndpointText(const Ipv4Endpoint& endpoint) {
  return Ipv4ToText(endpoint.address) + ":" + std::to_string(endpoint.port);
}

}  // namespace

const char* ToText(SubscriptionState state) noexcept {
  switch (state) {
    case SubscriptionState::kIdle:
      return "idle";
    case SubscriptionState::kConnecting:
      return "connecting";
    case SubscriptionState::kSubscribing:
      return "subscribing";
    case SubscriptionState::kSubscribed:
      return "subscribed";
    case SubscriptionState::kStopped:
      return "stopped";
  }
  return "unknown";
}

const char* ToText(SubscriptionLoss loss) noexcept {
  switch (loss) {
    case SubscriptionLoss::kTtlExpired:
      return "ttl_expired";
    case SubscriptionLoss::kNack:
      return "nack";
    case SubscriptionLoss::kTcpClosed:
      return "tcp_closed";
    case SubscriptionLoss::kStopOffer:
      return "stop_offer";
    case SubscriptionLoss::kServerReboot:
      return "server_reboot";
    case SubscriptionLoss::kStreamFramingLost:
      return "stream_framing_lost";
    case SubscriptionLoss::kStopped:
      return "stopped";
  }
  return "unknown";
}

bool SubscriptionMachine::SessionTracker::Observe(std::uint16_t session, bool reboot_flag) noexcept {
  // A sender rebooted when its reboot flag is set again after it was clear,
  // or when the flag stays set and the session ID did not grow.
  const bool rebooted = seen && reboot_flag && (!reboot || session <= session_id);
  seen = true;
  session_id = session;
  reboot = reboot_flag;
  return rebooted;
}

SubscriptionMachine::SubscriptionMachine(const SubscriptionConfig& config, SubscriptionTransport& transport,
                                         SubscriptionListener& listener, EventLog& log)
    : config_{config}, transport_{transport}, listener_{listener}, log_{log} {}

bool SubscriptionMachine::Matches(const SdEntry& entry) const noexcept {
  return entry.service_id == config_.service_id && entry.instance_id == config_.instance_id &&
         entry.major_version == config_.major_version;
}

Ipv4Endpoint SubscriptionMachine::ConnectTarget() const noexcept {
  if (has_offer_) {
    return offer_endpoint_;
  }
  return Ipv4Endpoint{config_.server_address, config_.reliable_port, kL4ProtocolTcp};
}

void SubscriptionMachine::StartConnect(const Clock& now, const char* trigger) {
  tcp_remote_ = ConnectTarget();
  state_ = SubscriptionState::kConnecting;
  connecting_since_ns_ = now.monotonic_ns;
  ++counters_.tcp_connect_attempts;
  log_.Log(now, LogRecord{"tcp_connecting"}.Text("server", EndpointText(tcp_remote_)).Text("trigger", trigger));
  transport_.ConnectTcp(tcp_remote_);
}

void SubscriptionMachine::EnterIdle(const Clock& now, std::int64_t retry_delay_ns) {
  transport_.CloseTcp();
  state_ = SubscriptionState::kIdle;
  next_connect_ns_ = now.monotonic_ns + retry_delay_ns;
}

void SubscriptionMachine::EndConnection(const Clock& now, SubscriptionLoss loss, std::int64_t retry_delay_ns) {
  const bool was_subscribed = state_ == SubscriptionState::kSubscribed;
  log_.Log(now, LogRecord{"connection_ended"}.Text("reason", ToText(loss)).Text("state", ToText(state_)));
  EnterIdle(now, retry_delay_ns);
  if (was_subscribed) {
    listener_.OnSubscriptionLost(now, loss);
  }
}

bool SubscriptionMachine::SendSubscribe(const Clock& now, std::uint32_t ttl) {
  SubscribeRequest request;
  request.session_id = session_id_;
  request.reboot = reboot_flag_;
  request.service_id = config_.service_id;
  request.instance_id = config_.instance_id;
  request.major_version = config_.major_version;
  request.ttl = ttl;
  request.eventgroup_id = config_.eventgroup_id;
  request.endpoint = tcp_local_;
  if (!transport_.SendSd(EncodeSubscribeEventgroup(request), config_.server_address, config_.sd_port)) {
    ++counters_.subscribe_send_failures;
    log_.Log(now, LogRecord{"sd_send_failed"}.Unsigned("session", request.session_id).Unsigned("ttl", ttl));
    return false;
  }
  if (ttl == 0U) {
    ++counters_.stop_subscribes_sent;
  } else {
    ++counters_.subscribes_sent;
  }
  if (state_ != SubscriptionState::kSubscribed || ttl == 0U) {
    log_.Log(now, LogRecord{ttl == 0U ? "stop_subscribe_sent" : "subscribe_sent"}
                      .Unsigned("session", request.session_id)
                      .Bool("reboot_flag", request.reboot)
                      .Unsigned("ttl", ttl)
                      .Text("endpoint", EndpointText(tcp_local_)));
  }
  // The session ID wraps from 0xFFFF to 1; the reboot flag stays set until the first wrap.
  if (session_id_ == 0xFFFFU) {
    session_id_ = 1;
    reboot_flag_ = false;
  } else {
    ++session_id_;
  }
  return true;
}

void SubscriptionMachine::OnTick(const Clock& now) {
  const std::int64_t t = now.monotonic_ns;
  if (has_offer_ && t >= offer_expiry_ns_) {
    has_offer_ = false;
    log_.Log(now, LogRecord{"offer_expired"});
  }
  switch (state_) {
    case SubscriptionState::kIdle:
      if (t >= next_connect_ns_) {
        StartConnect(now, has_offer_ ? "offer" : "unicast_fallback");
      }
      break;
    case SubscriptionState::kConnecting:
      if (t >= connecting_since_ns_ + config_.connect_timeout_ns) {
        ++counters_.tcp_connect_failures;
        log_.Log(now, LogRecord{"tcp_connect_failed"}.Text("reason", "timeout"));
        EnterIdle(now, config_.connect_retry_period_ns);
      }
      break;
    case SubscriptionState::kSubscribed:
      if (t >= ack_expiry_ns_) {
        ++counters_.ttl_expiries;
        state_ = SubscriptionState::kSubscribing;
        subscribing_since_ns_ = t;
        next_subscribe_ns_ = t;
        log_.Log(now, LogRecord{"subscription_expired"});
        listener_.OnSubscriptionLost(now, SubscriptionLoss::kTtlExpired);
        OnTick(now);  // subscribe again in the same tick
      } else if (t >= next_renew_ns_) {
        SendSubscribe(now, config_.ttl_s);
        next_renew_ns_ = t + config_.renew_period_ns;
      }
      break;
    case SubscriptionState::kSubscribing:
      if (t >= subscribing_since_ns_ + config_.subscribe_timeout_ns) {
        ++counters_.subscribe_timeouts;
        log_.Log(now, LogRecord{"subscribe_timeout"});
        EnterIdle(now, config_.connect_retry_period_ns);
      } else if (t >= next_subscribe_ns_) {
        SendSubscribe(now, config_.ttl_s);
        next_subscribe_ns_ = t + config_.renew_period_ns;
      }
      break;
    case SubscriptionState::kStopped:
      break;
  }
}

void SubscriptionMachine::OnSdMessage(const Clock& now, const SdMessage& message, std::uint32_t source_address,
                                      bool multicast) {
  if (state_ == SubscriptionState::kStopped) {
    return;
  }
  if (source_address != config_.server_address) {
    ++counters_.sd_messages_from_other_senders;
    return;
  }
  SessionTracker& tracker = multicast ? multicast_sessions_ : unicast_sessions_;
  if (tracker.Observe(message.session_id, message.reboot)) {
    ++counters_.server_reboots_detected;
    // An Ack in the same message shows that the restarted server accepted
    // the current connection; any other message ends a connection that may
    // belong to the server's previous run.
    const bool carries_our_ack =
        std::any_of(message.entries.begin(), message.entries.end(), [this](const SdEntry& entry) {
          return entry.type == TypeOf(SdEntryType::kSubscribeEventgroupAck) && entry.ttl > 0U && Matches(entry) &&
                 entry.eventgroup_id == config_.eventgroup_id;
        });
    log_.Log(now, LogRecord{"server_reboot_detected"}
                      .Bool("multicast", multicast)
                      .Unsigned("session", message.session_id)
                      .Bool("connection_kept", carries_our_ack));
    if (!carries_our_ack && (IsConnected(state_) || state_ == SubscriptionState::kConnecting)) {
      EndConnection(now, SubscriptionLoss::kServerReboot, config_.connect_retry_period_ns);
    }
  }
  for (const SdEntry& entry : message.entries) {
    if (entry.type == TypeOf(SdEntryType::kOfferService) && Matches(entry)) {
      HandleOffer(now, entry, multicast, message.session_id);
    } else if (entry.type == TypeOf(SdEntryType::kSubscribeEventgroupAck) && Matches(entry) &&
               entry.eventgroup_id == config_.eventgroup_id) {
      HandleAck(now, entry, message.session_id);
    } else {
      ++counters_.sd_entries_ignored;
    }
  }
}

void SubscriptionMachine::HandleOffer(const Clock& now, const SdEntry& entry, bool multicast, std::uint16_t session) {
  if (entry.ttl == 0U) {
    ++counters_.stop_offers;
    has_offer_ = false;
    log_.Log(now, LogRecord{"stop_offer"}.Unsigned("session", session).Bool("multicast", multicast));
    if (IsConnected(state_) || state_ == SubscriptionState::kConnecting) {
      EndConnection(now, SubscriptionLoss::kStopOffer, config_.connect_retry_period_ns);
    }
    return;
  }
  ++counters_.offers;
  Ipv4Endpoint endpoint{config_.server_address, config_.reliable_port, kL4ProtocolTcp};
  for (const Ipv4Endpoint& option : entry.endpoints) {
    if (option.protocol == kL4ProtocolTcp && option.address == config_.server_address) {
      endpoint = option;
      break;
    }
  }
  const bool new_offer = !has_offer_ || !(endpoint == offer_endpoint_);
  has_offer_ = true;
  offer_endpoint_ = endpoint;
  offer_expiry_ns_ = now.monotonic_ns + static_cast<std::int64_t>(entry.ttl) * kNanosecondsPerSecond;
  if (new_offer) {
    log_.Log(now, LogRecord{"offer"}
                      .Text("endpoint", EndpointText(endpoint))
                      .Unsigned("ttl", entry.ttl)
                      .Unsigned("session", session)
                      .Bool("multicast", multicast));
  }
  if (state_ == SubscriptionState::kIdle) {
    StartConnect(now, "offer");
  }
}

void SubscriptionMachine::HandleAck(const Clock& now, const SdEntry& entry, std::uint16_t session) {
  if (!IsConnected(state_)) {
    ++counters_.acks_unexpected;
    return;
  }
  if (entry.ttl == 0U) {
    ++counters_.nacks;
    log_.Log(now, LogRecord{"nack"}.Unsigned("session", session));
    EndConnection(now, SubscriptionLoss::kNack, config_.connect_retry_period_ns);
    return;
  }
  ++counters_.acks;
  ack_expiry_ns_ = now.monotonic_ns + static_cast<std::int64_t>(entry.ttl) * kNanosecondsPerSecond;
  if (state_ == SubscriptionState::kSubscribing) {
    state_ = SubscriptionState::kSubscribed;
    next_renew_ns_ = now.monotonic_ns + config_.renew_period_ns;
    ++counters_.subscription_phases;
    log_.Log(now, LogRecord{"subscribed"}
                      .Unsigned("session", session)
                      .Unsigned("ttl", entry.ttl)
                      .Text("endpoint", EndpointText(tcp_local_)));
    listener_.OnSubscribed(now);
  }
}

void SubscriptionMachine::OnTcpConnected(const Clock& now, const Ipv4Endpoint& local) {
  if (state_ != SubscriptionState::kConnecting) {
    return;
  }
  ++counters_.tcp_connects;
  tcp_local_ = Ipv4Endpoint{local.address, local.port, kL4ProtocolTcp};
  state_ = SubscriptionState::kSubscribing;
  subscribing_since_ns_ = now.monotonic_ns;
  next_subscribe_ns_ = now.monotonic_ns + config_.subscribe_delay_ns;
  log_.Log(now, LogRecord{"tcp_connected"}
                    .Text("local", EndpointText(tcp_local_))
                    .Text("server", EndpointText(tcp_remote_)));
}

void SubscriptionMachine::OnTcpConnectFailed(const Clock& now, int error_number) {
  if (state_ != SubscriptionState::kConnecting) {
    return;
  }
  ++counters_.tcp_connect_failures;
  log_.Log(now, LogRecord{"tcp_connect_failed"}.Signed("errno", error_number));
  EnterIdle(now, config_.connect_retry_period_ns);
}

void SubscriptionMachine::OnTcpClosed(const Clock& now) {
  if (!IsConnected(state_)) {
    return;
  }
  ++counters_.tcp_closed_by_peer;
  EndConnection(now, SubscriptionLoss::kTcpClosed, config_.connect_retry_period_ns);
}

void SubscriptionMachine::OnStreamFramingLost(const Clock& now) {
  if (!IsConnected(state_)) {
    return;
  }
  EndConnection(now, SubscriptionLoss::kStreamFramingLost, config_.connect_retry_period_ns);
}

void SubscriptionMachine::Stop(const Clock& now) {
  if (state_ == SubscriptionState::kStopped) {
    return;
  }
  const bool was_subscribed = state_ == SubscriptionState::kSubscribed;
  if (IsConnected(state_)) {
    SendSubscribe(now, 0);
  }
  transport_.CloseTcp();
  state_ = SubscriptionState::kStopped;
  has_offer_ = false;
  if (was_subscribed) {
    listener_.OnSubscriptionLost(now, SubscriptionLoss::kStopped);
  }
}

std::int64_t SubscriptionMachine::NextDeadline() const noexcept {
  std::int64_t deadline = kNoDeadline;
  switch (state_) {
    case SubscriptionState::kIdle:
      deadline = next_connect_ns_;
      break;
    case SubscriptionState::kConnecting:
      deadline = connecting_since_ns_ + config_.connect_timeout_ns;
      break;
    case SubscriptionState::kSubscribing:
      deadline = std::min(next_subscribe_ns_, subscribing_since_ns_ + config_.subscribe_timeout_ns);
      break;
    case SubscriptionState::kSubscribed:
      deadline = std::min(next_renew_ns_, ack_expiry_ns_);
      break;
    case SubscriptionState::kStopped:
      return kNoDeadline;
  }
  if (has_offer_) {
    deadline = std::min(deadline, offer_expiry_ns_);
  }
  return deadline;
}

}  // namespace de4sdv::someip_receiver
