#include "de4sdv_someip_receiver/receiver_core.hpp"

#include <algorithm>
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
    case DropReason::kFieldNotPositive:
      return "field_not_positive";
    case DropReason::kOlderThanPhase:
      return "older_than_phase";
    case DropReason::kCopyInPhase:
      return "copy_in_phase";
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
                           FrameDiscardPolicy& policy, EventLog& log, PropertySetter* properties)
    : config_{config},
      transport_{transport},
      sink_{sink},
      policy_{policy},
      log_{log},
      properties_{properties},
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

void ReceiverCore::ObserveClock(const Clock& now) {
  const std::int64_t offset = now.realtime_ns - now.monotonic_ns;
  if (clock_seen_) {
    const std::int64_t step = offset - clock_offset_ns_;
    if (step >= kClockStepThresholdNs || step <= -kClockStepThresholdNs) {
      ++counters_.clock_steps;
      if (in_phase_) {
        ++phase_clock_steps_;
      }
      log_.Log(now, LogRecord{"clock_step"}
                        .Signed("step_ns", step)
                        .Signed("realtime_minus_monotonic_ns", offset)
                        .Bool("in_phase", in_phase_));
    }
  }
  clock_seen_ = true;
  clock_offset_ns_ = offset;
}

void ReceiverCore::UpdatePhase(const Clock& now, const std::string& cause) {
  const bool holds = machine_.subscribed() && client_connected_;
  if (holds && !in_phase_) {
    in_phase_ = true;
    phase_start_realtime_ns_ = now.realtime_ns;
    phase_clock_steps_ = 0;
    phase_served_ = 0;
    ++counters_.phases_started;
    policy_.OnPhaseStart(now.realtime_ns);
    log_.Log(now, LogRecord{"phase_start"}
                      .Text("cause", cause)
                      .Signed("phase_start_realtime_ns", now.realtime_ns)
                      .Unsigned("phase", counters_.phases_started)
                      .Signed("realtime_minus_monotonic_ns", now.realtime_ns - now.monotonic_ns));
  } else if (!holds && in_phase_) {
    in_phase_ = false;
    ++counters_.phases_ended;
    policy_.OnPhaseEnd();
    LogRecord record{"phase_end"};
    record.Text("cause", cause)
        .Signed("phase_start_realtime_ns", phase_start_realtime_ns_)
        .Unsigned("phase", counters_.phases_started)
        .Unsigned("frames_served", phase_served_)
        .Unsigned("clock_steps_in_phase", phase_clock_steps_);
    if (phase_served_ > 0U) {
      record.Signed("receipt_minus_frame_min_ns", phase_receipt_min_ns_)
          .Signed("receipt_minus_frame_max_ns", phase_receipt_max_ns_);
    }
    log_.Log(now, record);
  }
}

void ReceiverCore::OnSubscribed(const Clock& now) { UpdatePhase(now, "subscription_acknowledged"); }

void ReceiverCore::OnSubscriptionLost(const Clock& now, SubscriptionLoss loss) {
  log_.Log(now, LogRecord{"subscription_lost"}.Text("reason", ToText(loss)));
  UpdatePhase(now, std::string{"subscription_lost:"} + ToText(loss));
}

void ReceiverCore::OnTick(const Clock& now) {
  ObserveClock(now);
  machine_.OnTick(now);
  if (IngressTriggerDue() && now.monotonic_ns >= next_ingress_trigger_ns_) {
    if (ingress_retriggers_ < kIngressRetriggerLimit) {
      ++ingress_retriggers_;
      TriggerIngress(now, "no_first_client");
    } else {
      ingress_trigger_gave_up_ = true;
      log_.Log(now, LogRecord{"ingress_trigger_gave_up"}
                        .Text("property", config_.ingress_start_property)
                        .Unsigned("tries", 1 + ingress_retriggers_)
                        .Signed("period_ns", kIngressRetriggerPeriodNs));
    }
  }
}

void ReceiverCore::OnListening(const Clock& now) {
  ObserveClock(now);
  listening_ = true;
  TriggerIngress(now, "listening");
}

bool ReceiverCore::IngressTriggerDue() const noexcept {
  return listening_ && !first_client_seen_ && !ingress_trigger_gave_up_ && properties_ != nullptr &&
         !config_.ingress_start_property.empty();
}

void ReceiverCore::TriggerIngress(const Clock& now, const char* reason) {
  next_ingress_trigger_ns_ = now.monotonic_ns + kIngressRetriggerPeriodNs;
  if (properties_ == nullptr || config_.ingress_start_property.empty()) {
    return;
  }
  // 0 and then 1: init sees a change to 1, also when the property was 1.
  const bool reset = properties_->SetProperty(now, config_.ingress_start_property, "0");
  const bool start = properties_->SetProperty(now, config_.ingress_start_property, "1");
  ++counters_.ingress_triggers;
  log_.Log(now, LogRecord{"ingress_trigger"}
                    .Text("reason", reason)
                    .Text("property", config_.ingress_start_property)
                    .Bool("ok", reset && start)
                    .Unsigned("try", 1 + ingress_retriggers_)
                    .Unsigned("repeats_left", kIngressRetriggerLimit - ingress_retriggers_));
}

std::int64_t ReceiverCore::NextDeadline() const noexcept {
  const std::int64_t deadline = machine_.NextDeadline();
  return IngressTriggerDue() ? std::min(deadline, next_ingress_trigger_ns_) : deadline;
}

void ReceiverCore::OnSdDatagram(const Clock& now, std::uint32_t source_address, bool multicast,
                                const std::uint8_t* data, std::size_t size) {
  ObserveClock(now);
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
  ObserveClock(now);
  reassembler_.Reset();
  machine_.OnTcpConnected(now, local);
}

void ReceiverCore::OnTcpConnectFailed(const Clock& now, int error_number) {
  ObserveClock(now);
  machine_.OnTcpConnectFailed(now, error_number);
}

void ReceiverCore::OnTcpData(const Clock& now, const std::uint8_t* data, std::size_t size) {
  ObserveClock(now);
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
  ObserveClock(now);
  reassembler_.Reset();
  machine_.OnTcpClosed(now);
}

bool ReceiverCore::OnClientAccepted(const Clock& now) {
  ObserveClock(now);
  if (client_connected_) {
    ++counters_.clients_refused;
    log_.Log(now, LogRecord{"client_refused"}.Text("reason", "a client is connected"));
    return false;
  }
  client_connected_ = true;
  first_client_seen_ = true;  // from now on, no ingress trigger in this process
  ++counters_.clients_accepted;
  log_.Log(now, LogRecord{"client_connected"});
  UpdatePhase(now, "client_connected");
  return true;
}

void ReceiverCore::OnClientDisconnected(const Clock& now) {
  ObserveClock(now);
  if (!client_connected_) {
    return;
  }
  client_connected_ = false;
  ++counters_.clients_lost;
  log_.Log(now, LogRecord{"client_lost"});
  UpdatePhase(now, "client_lost");
}

void ReceiverCore::Stop(const Clock& now) {
  ObserveClock(now);
  listening_ = false;
  machine_.Stop(now);
}

void ReceiverCore::LogFrame(const Clock& now, const char* verdict, const Header& header, std::size_t size,
                            const FrameFields* fields) {
  LogRecord record{"frame"};
  record.Text("verdict", verdict).Unsigned("someip_session", header.session_id).Unsigned("payload_bytes", size);
  if (fields != nullptr) {
    record.Unsigned("sequence", fields->sequence)
        .Signed("frame_timestamp_ns", fields->frame_timestamp_ns)
        .Signed("receipt_minus_frame_ns", now.realtime_ns - fields->frame_timestamp_ns);
  }
  log_.Log(now, record);
}

void ReceiverCore::Drop(const Clock& now, DropReason reason, const Header& header, std::size_t size,
                        const FrameFields* fields) {
  ++counters_.drops.at(static_cast<std::size_t>(reason));
  if (config_.log_frames) {
    LogFrame(now, ToText(reason), header, size, fields);
  }
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
  if (!in_phase_) {  // outside a phase: read every frame and drop it
    Drop(now, machine_.subscribed() ? DropReason::kNoClient : DropReason::kNotSubscribed, header, size, &fields);
    return;
  }
  switch (policy_.Admit(fields)) {
    case FrameVerdict::kDeliver:
      break;
    case FrameVerdict::kDropFieldNotPositive:
      Drop(now, DropReason::kFieldNotPositive, header, size, &fields);
      return;
    case FrameVerdict::kDropOlderThanPhase:
      Drop(now, DropReason::kOlderThanPhase, header, size, &fields);
      return;
    case FrameVerdict::kDropCopyInPhase:
      Drop(now, DropReason::kCopyInPhase, header, size, &fields);
      return;
  }
  if (!sink_.Forward(payload, size)) {
    Drop(now, DropReason::kClientWriteFailed, header, size, &fields);
    OnClientDisconnected(now);
    return;
  }
  ++counters_.frames_delivered;
  const std::int64_t receipt_minus_frame = now.realtime_ns - fields.frame_timestamp_ns;
  if (phase_served_ == 0U || receipt_minus_frame < phase_receipt_min_ns_) {
    phase_receipt_min_ns_ = receipt_minus_frame;
  }
  if (phase_served_ == 0U || receipt_minus_frame > phase_receipt_max_ns_) {
    phase_receipt_max_ns_ = receipt_minus_frame;
  }
  ++phase_served_;
  if (config_.log_frames || phase_served_ <= kFirstFramesLoggedPerPhase) {
    LogFrame(now, "delivered", header, size, &fields);
  }
}

LogRecord ReceiverCore::Status(const char* event) const {
  const SubscriptionCounters& s = machine_.counters();
  const ReceiverCounters& c = counters_;
  LogRecord record{event};
  record.Text("subscription_state", ToText(machine_.state()))
      .Bool("client_connected", client_connected_)
      .Bool("in_phase", in_phase_)
      .Signed("phase_start_realtime_ns", in_phase_ ? phase_start_realtime_ns_ : 0)
      .Signed("realtime_minus_monotonic_ns", clock_offset_ns_)
      .Unsigned("clock_steps", counters_.clock_steps);
  if (in_phase_) {
    record.Unsigned("frames_served_in_phase", phase_served_).Unsigned("clock_steps_in_phase", phase_clock_steps_);
    if (phase_served_ > 0U) {
      record.Signed("receipt_minus_frame_min_ns", phase_receipt_min_ns_)
          .Signed("receipt_minus_frame_max_ns", phase_receipt_max_ns_);
    }
  }
  record.Bool("offer_known", machine_.has_offer())
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
      .Unsigned("clients_accepted", c.clients_accepted)
      .Unsigned("clients_refused", c.clients_refused)
      .Unsigned("clients_lost", c.clients_lost)
      .Unsigned("ingress_triggers", c.ingress_triggers)
      .Unsigned("phases_started", c.phases_started)
      .Unsigned("phases_ended", c.phases_ended)
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
