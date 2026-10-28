#include "de4sdv_someip_receiver/receiver_core.hpp"

#include <string>

namespace de4sdv::someip_receiver {

namespace {

// The reassembler keeps every message up to this size, so that an oversize
// notification of the frame event is counted as a frame and dropped by the
// core, not skipped unseen.
constexpr std::size_t kStreamMessageLimitBytes = 65536;

}  // namespace

const char* ToText(DropReason reason) noexcept {
  switch (reason) {
    case DropReason::kMalformedNotification:
      return "malformed_notification";
    case DropReason::kPayloadTooLarge:
      return "payload_too_large";
    case DropReason::kLengthPrefixMismatch:
      return "length_prefix_mismatch";
    case DropReason::kFrameUnreadable:
      return "frame_unreadable";
    case DropReason::kNotSubscribed:
      return "not_subscribed";
    case DropReason::kNoClient:
      return "no_client";
    case DropReason::kSequenceNotIncreasing:
      return "sequence_not_increasing";
    case DropReason::kOlderThanPhase:
      return "older_than_phase";
    case DropReason::kClientWriteFailed:
      return "client_write_failed";
  }
  return "unknown";
}

std::uint64_t ReceiverCounters::frames_dropped() const noexcept {
  std::uint64_t total = 0;
  for (const std::uint64_t count : drops) {
    total += count;
  }
  return total;
}

ReceiverCore::ReceiverCore(const ReceiverConfig& config, SubscriptionTransport& transport, FrameSink& sink,
                           FrameDiscardPolicy& policy, EventLog& log)
    : config_{config},
      transport_{transport},
      sink_{sink},
      policy_{policy},
      log_{log},
      machine_{config_.subscription, *this, *this, log},
      reassembler_{kStreamMessageLimitBytes} {}

void ReceiverCore::ConnectTcp(const Ipv4Endpoint& server) {
  reassembler_.Reset();
  transport_.ConnectTcp(server);
}

void ReceiverCore::CloseTcp() {
  reassembler_.Reset();
  transport_.CloseTcp();
}

bool ReceiverCore::SendSd(const std::vector<std::uint8_t>& datagram, std::uint32_t address, std::uint16_t port) {
  return transport_.SendSd(datagram, address, port);
}

void ReceiverCore::StartPhase(const Clock& now, PhaseCause cause) {
  policy_.OnPhaseStart(cause, now.realtime_ns);
  if (cause == PhaseCause::kSubscriptionAcknowledged) {
    ++counters_.phases_by_subscription;
  } else {
    ++counters_.phases_by_client;
  }
  log_.Log(now, LogRecord{"phase_start"}
                    .Text("cause", ToText(cause))
                    .Signed("phase_start_realtime_ns", now.realtime_ns)
                    .Bool("subscribed", machine_.subscribed())
                    .Bool("client_connected", client_connected_));
}

void ReceiverCore::OnSubscribed(const Clock& now) { StartPhase(now, PhaseCause::kSubscriptionAcknowledged); }

void ReceiverCore::OnSubscriptionLost(const Clock& now, SubscriptionLoss loss) {
  log_.Log(now, LogRecord{"subscription_lost"}.Text("reason", ToText(loss)));
}

void ReceiverCore::OnTick(const Clock& now) { machine_.OnTick(now); }

void ReceiverCore::OnSdDatagram(const Clock& now, std::uint32_t source_address, bool multicast,
                                const std::uint8_t* data, std::size_t size) {
  ++counters_.sd_datagrams;
  const SdParseResult result = ParseSdMessage(data, size);
  if (!result.message.has_value()) {
    ++counters_.sd_malformed;
    log_.Log(now, LogRecord{"sd_malformed"}
                      .Text("reason", ToText(result.error))
                      .Text("source", Ipv4ToText(source_address))
                      .Unsigned("bytes", size));
    return;
  }
  machine_.OnSdMessage(now, *result.message, source_address, multicast);
}

void ReceiverCore::OnTcpConnected(const Clock& now, const Ipv4Endpoint& local) {
  reassembler_.Reset();
  machine_.OnTcpConnected(now, local);
}

void ReceiverCore::OnTcpConnectFailed(const Clock& now, int error_number) {
  machine_.OnTcpConnectFailed(now, error_number);
}

void ReceiverCore::OnTcpData(const Clock& now, const std::uint8_t* data, std::size_t size) {
  const bool framing_kept = reassembler_.Feed(
      data, size, [this, &now](const Header& header, const std::uint8_t* payload, std::size_t payload_size) {
        OnMessage(now, header, payload, payload_size);
      });
  if (!framing_kept) {
    ++counters_.stream_framing_errors;
    log_.Log(now, LogRecord{"stream_framing_lost"});
    machine_.OnStreamFramingLost(now);
  }
}

void ReceiverCore::OnTcpClosed(const Clock& now) {
  reassembler_.Reset();
  machine_.OnTcpClosed(now);
}

void ReceiverCore::OnClientConnected(const Clock& now) {
  client_connected_ = true;
  ++counters_.clients_connected;
  log_.Log(now, LogRecord{"client_connected"});
  StartPhase(now, PhaseCause::kClientConnected);
}

void ReceiverCore::OnClientDisconnected(const Clock& now) {
  if (!client_connected_) {
    return;
  }
  client_connected_ = false;
  ++counters_.clients_lost;
  log_.Log(now, LogRecord{"client_lost"});
}

void ReceiverCore::Stop(const Clock& now) { machine_.Stop(now); }

void ReceiverCore::LogFrame(const Clock& now, const char* verdict, const Header& header, std::size_t size,
                            const FrameFields* fields) {
  if (!config_.log_frames) {
    return;
  }
  LogRecord record{"frame"};
  record.Text("verdict", verdict).Unsigned("someip_session", header.session_id).Unsigned("payload_bytes", size);
  if (fields != nullptr) {
    record.Unsigned("sequence", fields->sequence).Signed("frame_timestamp_ns", fields->frame_timestamp_ns);
  }
  log_.Log(now, record);
}

void ReceiverCore::Drop(const Clock& now, DropReason reason, const Header& header, std::size_t size,
                        const FrameFields* fields) {
  ++counters_.drops.at(static_cast<std::size_t>(reason));
  LogFrame(now, ToText(reason), header, size, fields);
}

void ReceiverCore::OnMessage(const Clock& now, const Header& header, const std::uint8_t* payload, std::size_t size) {
  ++counters_.stream_messages;
  if (IsMagicCookie(header)) {
    ++counters_.magic_cookies;
    return;
  }
  if (header.service_id != config_.subscription.service_id || header.method_id != config_.event_id) {
    ++counters_.other_messages;
    return;
  }
  ++counters_.frames_received;
  if (header.message_type != kMessageTypeNotification || header.return_code != kReturnCodeOk ||
      header.protocol_version != kProtocolVersion || header.interface_version != config_.subscription.major_version) {
    Drop(now, DropReason::kMalformedNotification, header, size, nullptr);
    return;
  }
  if (size > config_.max_payload_bytes) {
    Drop(now, DropReason::kPayloadTooLarge, header, size, nullptr);
    return;
  }
  if (CheckLengthPrefix(payload, size) != PayloadCheck::kOk) {
    Drop(now, DropReason::kLengthPrefixMismatch, header, size, nullptr);
    return;
  }
  const FrameReadResult read = ReadFrameFields(payload + kLengthPrefixBytes, size - kLengthPrefixBytes);
  if (!read.fields.has_value()) {
    Drop(now, DropReason::kFrameUnreadable, header, size, nullptr);
    return;
  }
  const FrameFields& fields = *read.fields;
  if (!machine_.subscribed()) {
    Drop(now, DropReason::kNotSubscribed, header, size, &fields);
    return;
  }
  if (!client_connected_) {
    Drop(now, DropReason::kNoClient, header, size, &fields);
    return;
  }
  const FrameVerdict verdict = policy_.Admit(fields);
  if (verdict == FrameVerdict::kDropSequenceNotIncreasing) {
    Drop(now, DropReason::kSequenceNotIncreasing, header, size, &fields);
    return;
  }
  if (verdict == FrameVerdict::kDropOlderThanPhase) {
    Drop(now, DropReason::kOlderThanPhase, header, size, &fields);
    return;
  }
  if (!sink_.Forward(payload, size)) {
    Drop(now, DropReason::kClientWriteFailed, header, size, &fields);
    OnClientDisconnected(now);
    return;
  }
  ++counters_.frames_delivered;
  LogFrame(now, "delivered", header, size, &fields);
}

LogRecord ReceiverCore::Status(const char* event) const {
  const SubscriptionCounters& s = machine_.counters();
  const ReceiverCounters& c = counters_;
  LogRecord record{event};
  record.Text("subscription_state", ToText(machine_.state()))
      .Bool("client_connected", client_connected_)
      .Bool("offer_known", machine_.has_offer())
      .Unsigned("frames_received", c.frames_received)
      .Unsigned("frames_delivered", c.frames_delivered)
      .Unsigned("frames_dropped", c.frames_dropped());
  for (std::size_t index = 0; index < kDropReasonCount; ++index) {
    const std::string key = std::string{"drop_"} + ToText(static_cast<DropReason>(index));
    record.Unsigned(key.c_str(), c.drops[index]);
  }
  record.Unsigned("stream_messages", c.stream_messages)
      .Unsigned("other_messages", c.other_messages)
      .Unsigned("magic_cookies", c.magic_cookies)
      .Unsigned("stream_framing_errors", c.stream_framing_errors)
      .Unsigned("sd_datagrams", c.sd_datagrams)
      .Unsigned("sd_malformed", c.sd_malformed)
      .Unsigned("clients_connected", c.clients_connected)
      .Unsigned("clients_lost", c.clients_lost)
      .Unsigned("phases_by_subscription", c.phases_by_subscription)
      .Unsigned("phases_by_client", c.phases_by_client)
      .Unsigned("offers", s.offers)
      .Unsigned("stop_offers", s.stop_offers)
      .Unsigned("sd_messages_from_other_senders", s.sd_messages_from_other_senders)
      .Unsigned("sd_entries_ignored", s.sd_entries_ignored)
      .Unsigned("server_reboots_detected", s.server_reboots_detected)
      .Unsigned("tcp_connect_attempts", s.tcp_connect_attempts)
      .Unsigned("tcp_connects", s.tcp_connects)
      .Unsigned("tcp_connect_failures", s.tcp_connect_failures)
      .Unsigned("tcp_closed_by_peer", s.tcp_closed_by_peer)
      .Unsigned("subscribes_sent", s.subscribes_sent)
      .Unsigned("subscribe_send_failures", s.subscribe_send_failures)
      .Unsigned("stop_subscribes_sent", s.stop_subscribes_sent)
      .Unsigned("acks", s.acks)
      .Unsigned("acks_unexpected", s.acks_unexpected)
      .Unsigned("nacks", s.nacks)
      .Unsigned("subscription_phases", s.subscription_phases)
      .Unsigned("ttl_expiries", s.ttl_expiries)
      .Unsigned("subscribe_timeouts", s.subscribe_timeouts);
  return record;
}

}  // namespace de4sdv::someip_receiver
