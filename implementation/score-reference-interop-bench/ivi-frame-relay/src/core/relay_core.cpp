#include "de4sdv_ivi_frame_relay/relay_core.hpp"

#include <algorithm>
#include <limits>
#include <optional>
#include <string>

#include "de4sdv_ivi_frame_relay/broker_wrapper.hpp"

namespace de4sdv::ivi_frame_relay {

namespace {

constexpr const char* kSubscriberFlagName = "ASDVGATEWAY_SUBSCRIBER_OPTIONS_FLAG_NONE";

// a - b, or nothing when it does not fit in 64 bits: a frame may carry any
// frame_timestamp_ns, also INT64_MIN.
std::optional<std::int64_t> Difference(std::int64_t a, std::int64_t b) noexcept {
  std::int64_t result = 0;
  if (__builtin_sub_overflow(a, b, &result)) {
    return std::nullopt;
  }
  return result;
}

DropReason WrapperDrop(WrapperCheck check) noexcept {
  switch (check) {
    case WrapperCheck::kOuterVarintInvalid:
      return DropReason::kWrapperOuterVarintInvalid;
    case WrapperCheck::kOuterLengthExceedsSlot:
      return DropReason::kWrapperOuterLengthExceedsSlot;
    case WrapperCheck::kFieldMissing:
      return DropReason::kWrapperFieldMissing;
    case WrapperCheck::kTagNotBytesField1:
      return DropReason::kWrapperTagNotBytesField1;
    case WrapperCheck::kInnerVarintInvalid:
      return DropReason::kWrapperInnerVarintInvalid;
    case WrapperCheck::kFieldExceedsMessage:
      return DropReason::kWrapperFieldExceedsMessage;
    case WrapperCheck::kBytesAfterField:
      return DropReason::kWrapperBytesAfterField;
    case WrapperCheck::kFillNotZero:
    case WrapperCheck::kOk:
      break;
  }
  return DropReason::kWrapperFillNotZero;
}

}  // namespace

const char* ToText(DropReason reason) noexcept {
  switch (reason) {
    case DropReason::kWrapperOuterVarintInvalid:
      return ToText(WrapperCheck::kOuterVarintInvalid);
    case DropReason::kWrapperOuterLengthExceedsSlot:
      return ToText(WrapperCheck::kOuterLengthExceedsSlot);
    case DropReason::kWrapperFieldMissing:
      return ToText(WrapperCheck::kFieldMissing);
    case DropReason::kWrapperTagNotBytesField1:
      return ToText(WrapperCheck::kTagNotBytesField1);
    case DropReason::kWrapperInnerVarintInvalid:
      return ToText(WrapperCheck::kInnerVarintInvalid);
    case DropReason::kWrapperFieldExceedsMessage:
      return ToText(WrapperCheck::kFieldExceedsMessage);
    case DropReason::kWrapperBytesAfterField:
      return ToText(WrapperCheck::kBytesAfterField);
    case DropReason::kWrapperFillNotZero:
      return ToText(WrapperCheck::kFillNotZero);
    case DropReason::kPayloadTooLarge:
      return "payload_too_large";
    case DropReason::kPayloadTooShort:
      return "payload_too_short";
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
    case DropReason::kRelayStop:
      return "relay_stop";
  }
  return "unknown";
}

std::uint64_t RelayCounters::frames_dropped() const noexcept {
  std::uint64_t total = 0;
  for (const std::uint64_t count : drops) {
    total += count;
  }
  return total;
}

RelayCore::RelayCore(const RelayConfig& config, FrameSink& sink, FrameDiscardPolicy& policy, EventLog& log,
                     PropertySetter* properties, GatewayCallMonitor* monitor)
    : config_{config}, sink_{sink}, policy_{policy}, log_{log}, properties_{properties}, monitor_{monitor} {}

void RelayCore::OnStart(const Clock& now) {
  ObserveClock(now);
  started_ = true;
  start_ = now;
}

void RelayCore::ObserveClock(const Clock& now) {
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

void RelayCore::LogStatus(LogRecord& record, const GatewayResult& status) const {
  record.Signed("status_code", status.code).Text("status_name", GatewayStatusName(status.code)).Text("status_text",
                                                                                                    status.text);
}

void RelayCore::UpdatePhase(const Clock& now, const char* cause, bool layer_caused) {
  const bool holds = subscribed_ && client_connected_;
  if (holds && !in_phase_) {
    in_phase_ = true;
    // The second of the two conditions to start sets the phase start.
    phase_start_realtime_ns_ = std::max(subscribed_since_realtime_ns_, client_since_realtime_ns_);
    phase_clock_steps_ = 0;
    phase_served_ = 0;
    phase_receipt_known_ = false;
    ++counters_.phases_started;
    policy_.OnPhaseStart(phase_start_realtime_ns_);
    log_.Log(now, LogRecord{"phase_start"}
                      .Text("cause", cause)
                      .Unsigned("phase", counters_.phases_started)
                      .Signed("phase_start_realtime_ns", phase_start_realtime_ns_)
                      .Unsigned("subscription", subscription_)
                      .Signed("publication_id", publication_id_)
                      .Signed("realtime_minus_monotonic_ns", now.realtime_ns - now.monotonic_ns));
  } else if (!holds && in_phase_) {
    in_phase_ = false;
    ++counters_.phases_ended;
    if (layer_caused) {
      ++counters_.phases_ended_by_layer;
    }
    policy_.OnPhaseEnd();
    LogRecord record{"phase_end"};
    record.Text("cause", cause)
        .Bool("layer_caused", layer_caused)
        .Bool("client_connected", client_connected_)
        .Unsigned("phase", counters_.phases_started)
        .Signed("phase_start_realtime_ns", phase_start_realtime_ns_)
        .Unsigned("subscription", subscription_)
        .Unsigned("frames_served", phase_served_)
        .Unsigned("clock_steps_in_phase", phase_clock_steps_);
    if (phase_receipt_known_) {
      record.Signed("receipt_minus_frame_min_ns", phase_receipt_min_ns_)
          .Signed("receipt_minus_frame_max_ns", phase_receipt_max_ns_);
    }
    log_.Log(now, record);
  }
}

void RelayCore::OnListening(const Clock& now) {
  ObserveClock(now);
  listening_ = true;
  TriggerIngress(now, "listening");
}

bool RelayCore::IngressTriggerDue() const noexcept {
  return listening_ && !first_client_seen_ && !ingress_trigger_gave_up_ && properties_ != nullptr &&
         !config_.ingress_start_property.empty();
}

void RelayCore::TriggerIngress(const Clock& now, const char* reason) {
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

void RelayCore::CheckStartDiagnostic(const Clock& now) {
  if (!started_ || start_diagnostic_done_ || ever_subscribed_ ||
      now.monotonic_ns - start_.monotonic_ns < kStartDiagnosticNs) {
    return;
  }
  start_diagnostic_done_ = true;
  LogRecord record{"subscription_start_diagnostic"};
  record.Text("likely_fault", client_ever_created_ ? "acl_or_mapping" : "gateway_client")
      .Text("detail", client_ever_created_
                          ? "no subscription within 30 s of the start; a subject without an ACL gets the reply of "
                            "a missing publication"
                          : "no gateway client within 30 s of the start")
      .Signed("since_start_ns", now.monotonic_ns - start_.monotonic_ns)
      .Unsigned("client_create_attempts", counters_.client_create_attempts)
      .Unsigned("client_create_failures", counters_.client_create_failures)
      .Unsigned("subscribe_attempts", counters_.subscribe_attempts)
      .Unsigned("subscribe_failures", counters_.subscribe_failures)
      .Text("last_failure_stage", last_failure_stage_);
  LogStatus(record, last_failure_);
  if (monitor_ != nullptr) {
    const auto call = monitor_->Current();
    record.Text("gateway_call_in_progress", call.has_value() ? call->name : "")
        .Signed("gateway_call_running_ns", call.has_value() ? now.monotonic_ns - call->since_ns : 0);
  }
  record.Signed("retry_period_ns", kSlowRetryPeriodNs);
  log_.Log(now, record);
}

void RelayCore::CheckGatewayCalls(const Clock& now) {
  if (monitor_ == nullptr) {
    return;
  }
  if (const auto stalled = monitor_->TakeNewStall(now.monotonic_ns, config_.gateway_call_stall_ns)) {
    ++counters_.gateway_calls_stalled;
    log_.Log(now, LogRecord{"gateway_call_stalled"}
                      .Text("call", stalled->name)
                      .Unsigned("call_number", stalled->number)
                      .Signed("running_ns", now.monotonic_ns - stalled->since_ns)
                      .Bool("subscribed", subscribed_)
                      .Bool("client_connected", client_connected_)
                      .Bool("in_phase", in_phase_));
  }
  if (const auto returned = monitor_->TakeReturnedStall()) {
    log_.Log(now, LogRecord{"gateway_call_returned"}
                      .Text("call", returned->name)
                      .Unsigned("call_number", returned->number)
                      .Signed("ran_ns", returned->end_ns - returned->since_ns));
  }
}

void RelayCore::OnTick(const Clock& now) {
  ObserveClock(now);
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
  CheckStartDiagnostic(now);
  CheckGatewayCalls(now);
}

std::int64_t RelayCore::NextDeadline() const noexcept {
  std::int64_t deadline = std::numeric_limits<std::int64_t>::max();
  if (IngressTriggerDue()) {
    deadline = std::min(deadline, next_ingress_trigger_ns_);
  }
  if (started_ && !start_diagnostic_done_ && !ever_subscribed_) {
    deadline = std::min(deadline, start_.monotonic_ns + kStartDiagnosticNs);
  }
  return deadline;
}

namespace {

LogRecord& Peer(LogRecord& record, const PeerIdentity& peer) {
  return record.Unsigned("peer_port", peer.port)
      .Signed("peer_pid", peer.pid_known ? peer.pid : -1)
      .Signed("peer_uid", peer.uid_known ? peer.uid : -1)
      .Text("peer_source", peer.source);
}

}  // namespace

bool RelayCore::OnClientAccepted(const Clock& now, const PeerIdentity& peer) {
  ObserveClock(now);
  if (client_connected_) {
    ++counters_.clients_refused;
    LogRecord record{"client_refused"};
    record.Text("reason", "a client is connected");
    log_.Log(now, Peer(record, peer));
    return false;
  }
  client_connected_ = true;
  client_since_realtime_ns_ = now.realtime_ns;
  first_client_seen_ = true;  // from now on, no ingress trigger in this process
  ++counters_.clients_accepted;
  LogRecord record{"client_connected"};
  record.Bool("subscribed", subscribed_);
  log_.Log(now, Peer(record, peer));
  UpdatePhase(now, "client_connected", false);
  return true;
}

void RelayCore::RearmIngressTrigger(const Clock& now) {
  if (!listening_) {
    return;
  }
  first_client_seen_ = false;
  ingress_trigger_gave_up_ = false;
  ingress_retriggers_ = 0;
  TriggerIngress(now, "relay_closed_the_client");
}

void RelayCore::LoseClient(const WorkerEvent& event, const char* reason, const char* cause) {
  if (!client_connected_) {
    return;
  }
  client_connected_ = false;
  ++counters_.clients_lost;
  log_.Log(event.at, LogRecord{"client_lost"}.Text("reason", reason));
  UpdatePhase(event.at, cause, false);
}

void RelayCore::OnClientDisconnected(const Clock& now) {
  ObserveClock(now);
  if (!client_connected_) {
    return;
  }
  client_connected_ = false;
  ++counters_.clients_lost;
  log_.Log(now, LogRecord{"client_lost"});
  UpdatePhase(now, "client_lost", false);
}

void RelayCore::Stop(const Clock& now) {
  ObserveClock(now);
  listening_ = false;
  if (in_phase_) {
    // The relay stops: its subscription ends with it.
    subscribed_ = false;
    UpdatePhase(now, "relay_stop", false);
  }
}

void RelayCore::OnWorkerEvent(const WorkerEvent& event) {
  ObserveClock(event.at);
  switch (event.kind) {
    case WorkerEventKind::kClientCreate: {
      ++counters_.client_create_attempts;
      LogRecord record{"gateway_client_create"};
      record.Bool("ok", event.status.ok()).Unsigned("attempt", event.attempt);
      LogStatus(record, event.status);
      if (event.status.ok()) {
        has_client_ = true;
        client_ever_created_ = true;
      } else {
        ++counters_.client_create_failures;
        last_failure_ = event.status;
        last_failure_stage_ = "create_client";
        record.Signed("next_attempt_in_ns", event.next_attempt_ns - event.at.monotonic_ns);
      }
      log_.Log(event.at, record);
      return;
    }
    case WorkerEventKind::kClientDestroyed: {
      has_client_ = false;
      ++counters_.clients_destroyed;
      LogRecord record{"gateway_client_destroyed"};
      record.Text("cause", event.note).Bool("ok", event.status.ok());
      LogStatus(record, event.status);
      log_.Log(event.at, record);
      return;
    }
    case WorkerEventKind::kSubscribed:
      ++counters_.subscribe_attempts;
      ++counters_.subscriptions;
      ever_subscribed_ = true;
      subscribed_ = true;
      subscribed_since_realtime_ns_ = event.at.realtime_ns;
      subscription_ = event.subscription;
      publication_id_ = event.publication.publication_id;
      log_.Log(event.at, LogRecord{"subscribed"}
                             .Unsigned("attempt", event.attempt)
                             .Unsigned("subscription", event.subscription)
                             .Signed("publication_id", event.publication.publication_id)
                             .Unsigned("message_size_bytes", event.publication.message_size_bytes)
                             .Unsigned("message_count", event.publication.message_count)
                             .Unsigned("subscriber_flags", event.publication.subscriber_flags)
                             .Text("subscriber_flag", kSubscriberFlagName)
                             .Text("rule", event.rule)
                             .Bool("client_connected", client_connected_));
      UpdatePhase(event.at, "subscribed", false);
      return;
    case WorkerEventKind::kSubscribeFailed: {
      ++counters_.subscribe_attempts;
      ++counters_.subscribe_failures;
      last_failure_ = event.status;
      last_failure_stage_ = "subscribe";
      LogRecord record{"subscribe_failed"};
      record.Unsigned("attempt", event.attempt).Unsigned("failures", counters_.subscribe_failures);
      LogStatus(record, event.status);
      record.Text("rule", event.rule)
          .Signed("next_attempt_in_ns", event.next_attempt_ns - event.at.monotonic_ns)
          .Text("note", event.note);
      log_.Log(event.at, record);
      return;
    }
    case WorkerEventKind::kSubscriptionEnded: {
      switch (event.end) {
        case SubscriptionEnd::kPublicationDestroyed:
          ++counters_.ended_publication_destroyed;
          break;
        case SubscriptionEnd::kDisconnected:
          ++counters_.ended_disconnected;
          break;
        case SubscriptionEnd::kSilenceTimeout:
          ++counters_.ended_silence_timeout;
          break;
        case SubscriptionEnd::kRelayStop:
          break;
      }
      const bool layer_caused = EndedByLayer(event.end) && client_connected_ && in_phase_;
      LogRecord record{"subscription_ended"};
      record.Text("cause", ToText(event.end))
          .Unsigned("subscription", event.subscription)
          .Signed("publication_id", event.publication.publication_id)
          .Unsigned("messages", event.messages)
          .Unsigned("consecutive_silent_subscriptions", event.consecutive_silent)
          .Bool("layer_caused_phase_end", layer_caused);
      if (event.next_attempt_ns != 0) {
        record.Signed("next_attempt_in_ns", event.next_attempt_ns - event.at.monotonic_ns).Text("rule", event.rule);
      }
      log_.Log(event.at, record);
      if (!subscribed_ || event.subscription != subscription_) {
        return;
      }
      subscribed_ = false;
      UpdatePhase(event.at, ToText(event.end), layer_caused);
      return;
    }
    case WorkerEventKind::kUnsubscribed: {
      if (!event.status.ok()) {
        ++counters_.unsubscribe_failures;
      }
      LogRecord record{"unsubscribed"};
      record.Bool("ok", event.status.ok())
          .Unsigned("subscription", event.subscription)
          .Signed("publication_id", event.publication.publication_id);
      LogStatus(record, event.status);
      log_.Log(event.at, record);
      return;
    }
    case WorkerEventKind::kMessage:
      OnMessage(event);
      return;
    case WorkerEventKind::kDataLoss: {
      ++counters_.data_loss_reads;
      LogRecord record{"data_loss"};
      record.Unsigned("subscription", event.subscription)
          .Signed("publication_id", event.publication.publication_id)
          .Bool("in_phase", in_phase_)
          .Unsigned("data_loss_reads", counters_.data_loss_reads)
          .Text("counts_as", "gap");
      LogStatus(record, event.status);
      log_.Log(event.at, record);
      return;
    }
    case WorkerEventKind::kReadFailed: {
      ++counters_.read_failures;
      if (read_failure_logged_ && event.at.monotonic_ns - read_failure_logged_ns_ < kRepeatedLogPeriodNs) {
        ++read_failures_suppressed_;
        return;
      }
      LogRecord record{"read_failed"};
      record.Unsigned("subscription", event.subscription)
          .Signed("publication_id", event.publication.publication_id)
          .Unsigned("suppressed", read_failures_suppressed_);
      LogStatus(record, event.status);
      log_.Log(event.at, record);
      read_failure_logged_ = true;
      read_failure_logged_ns_ = event.at.monotonic_ns;
      read_failures_suppressed_ = 0;
      return;
    }
    case WorkerEventKind::kNotification:
      ++counters_.notifications_not_acted_on;
      log_.Log(event.at, LogRecord{"gateway_notification"}
                             .Text("kind", ToText(event.notification))
                             .Signed("raw_type", event.raw_type)
                             .Signed("publication_id", event.publication.publication_id)
                             .Unsigned("count", event.messages)
                             .Text("note", event.note));
      return;
  }
}

void RelayCore::LogFrame(const WorkerEvent& event, const char* verdict, std::size_t payload_bytes,
                         const FrameFields* fields, const WrapperParse* wrapper) {
  LogRecord record{"frame"};
  record.Text("verdict", verdict)
      .Unsigned("subscription", event.subscription)
      .Unsigned("slot_bytes", event.slot.size())
      .Unsigned("payload_bytes", payload_bytes);
  if (wrapper != nullptr && wrapper->message_known) {
    record.Unsigned("message_bytes", wrapper->message_bytes);
  }
  if (wrapper != nullptr && wrapper->check == WrapperCheck::kFillNotZero) {
    record.Unsigned("fill_offset", wrapper->fill_offset).Unsigned("fill_value", wrapper->fill_value);
  }
  if (fields != nullptr) {
    record.Unsigned("sequence", fields->sequence).Signed("frame_timestamp_ns", fields->frame_timestamp_ns);
    if (const auto receipt_minus_frame = Difference(event.at.realtime_ns, fields->frame_timestamp_ns)) {
      record.Signed("receipt_minus_frame_ns", *receipt_minus_frame);
    }
  }
  log_.Log(event.at, record);
}

void RelayCore::Drop(const WorkerEvent& event, DropReason reason, std::size_t payload_bytes,
                     const FrameFields* fields, const WrapperParse* wrapper) {
  ++counters_.drops.at(static_cast<std::size_t>(reason));
  // Every drop is logged with its reason, at most at the message rate;
  // --log-frames adds only the line of each served frame.
  LogFrame(event, ToText(reason), payload_bytes, fields, wrapper);
}

void RelayCore::OnMessage(const WorkerEvent& event) {
  ++counters_.messages_read;
  const WrapperParse wrapper = ParseBrokerWrapper(event.slot.data(), event.slot.size());
  if (wrapper.check != WrapperCheck::kOk) {
    Drop(event, WrapperDrop(wrapper.check), 0, nullptr, &wrapper);
    return;
  }
  const std::uint8_t* payload = event.slot.data() + wrapper.payload_offset;
  const std::size_t size = wrapper.payload_bytes;
  if (size > kMaxPayloadBytes) {
    Drop(event, DropReason::kPayloadTooLarge, size, nullptr);
    return;
  }
  switch (CheckLengthPrefix(payload, size)) {
    case PayloadCheck::kOk:
      break;
    case PayloadCheck::kTooShort:
      Drop(event, DropReason::kPayloadTooShort, size, nullptr);
      return;
    case PayloadCheck::kLengthPrefixMismatch:
      Drop(event, DropReason::kLengthPrefixMismatch, size, nullptr);
      return;
  }
  const FrameReadResult read = ReadFrameFields(payload + kLengthPrefixBytes, size - kLengthPrefixBytes);
  if (!read.fields.has_value()) {
    Drop(event, DropReason::kFrameUnreadable, size, nullptr);
    return;
  }
  const FrameFields& fields = *read.fields;
  if (!in_phase_) {  // outside a phase: read every frame and drop it
    Drop(event, subscribed_ ? DropReason::kNoClient : DropReason::kNotSubscribed, size, &fields);
    return;
  }
  switch (policy_.Admit(fields)) {
    case FrameVerdict::kDeliver:
      break;
    case FrameVerdict::kDropFieldNotPositive:
      Drop(event, DropReason::kFieldNotPositive, size, &fields);
      return;
    case FrameVerdict::kDropOlderThanPhase:
      Drop(event, DropReason::kOlderThanPhase, size, &fields);
      return;
    case FrameVerdict::kDropCopyInPhase:
      Drop(event, DropReason::kCopyInPhase, size, &fields);
      return;
  }
  switch (sink_.Forward(payload, size)) {
    case ForwardResult::kWritten:
      break;
    case ForwardResult::kFailed:
      Drop(event, DropReason::kClientWriteFailed, size, &fields);
      LoseClient(event, "write failed", "client_write_failed");
      RearmIngressTrigger(event.at);
      return;
    case ForwardResult::kStopped:
      Drop(event, DropReason::kRelayStop, size, &fields);
      LoseClient(event, "relay stop", "relay_stop");
      return;
  }
  ++counters_.frames_delivered;
  if (const auto receipt_minus_frame = Difference(event.at.realtime_ns, fields.frame_timestamp_ns)) {
    if (!phase_receipt_known_ || *receipt_minus_frame < phase_receipt_min_ns_) {
      phase_receipt_min_ns_ = *receipt_minus_frame;
    }
    if (!phase_receipt_known_ || *receipt_minus_frame > phase_receipt_max_ns_) {
      phase_receipt_max_ns_ = *receipt_minus_frame;
    }
    phase_receipt_known_ = true;
  }
  ++phase_served_;
  if (config_.log_frames || phase_served_ <= kFirstFramesLoggedPerPhase) {
    LogFrame(event, "delivered", size, &fields);
  }
}

LogRecord RelayCore::Status(const char* event) const {
  const RelayCounters& c = counters_;
  LogRecord record{event};
  record.Bool("has_client", has_client_)
      .Bool("subscribed", subscribed_)
      .Unsigned("subscription", subscribed_ ? subscription_ : 0)
      .Bool("client_connected", client_connected_)
      .Bool("in_phase", in_phase_)
      .Signed("phase_start_realtime_ns", in_phase_ ? phase_start_realtime_ns_ : 0)
      .Signed("realtime_minus_monotonic_ns", clock_offset_ns_)
      .Unsigned("clock_steps", c.clock_steps);
  if (in_phase_) {
    record.Unsigned("frames_served_in_phase", phase_served_).Unsigned("clock_steps_in_phase", phase_clock_steps_);
    if (phase_receipt_known_) {
      record.Signed("receipt_minus_frame_min_ns", phase_receipt_min_ns_)
          .Signed("receipt_minus_frame_max_ns", phase_receipt_max_ns_);
    }
  }
  record.Unsigned("messages_read", c.messages_read)
      .Unsigned("frames_delivered", c.frames_delivered)
      .Unsigned("frames_dropped", c.frames_dropped());
  for (std::size_t index = 0; index < kDropReasonCount; ++index) {
    const std::string key = std::string{"drop_"} + ToText(static_cast<DropReason>(index));
    record.Unsigned(key.c_str(), c.drops[index]);
  }
  record.Unsigned("data_loss_reads", c.data_loss_reads)
      .Unsigned("read_failures", c.read_failures)
      .Unsigned("clients_accepted", c.clients_accepted)
      .Unsigned("clients_refused", c.clients_refused)
      .Unsigned("clients_lost", c.clients_lost)
      .Unsigned("ingress_triggers", c.ingress_triggers)
      .Unsigned("phases_started", c.phases_started)
      .Unsigned("phases_ended", c.phases_ended)
      .Unsigned("phases_ended_by_layer", c.phases_ended_by_layer)
      .Unsigned("client_create_attempts", c.client_create_attempts)
      .Unsigned("client_create_failures", c.client_create_failures)
      .Unsigned("clients_destroyed", c.clients_destroyed)
      .Unsigned("subscribe_attempts", c.subscribe_attempts)
      .Unsigned("subscribe_failures", c.subscribe_failures)
      .Unsigned("subscriptions", c.subscriptions)
      .Unsigned("ended_publication_destroyed", c.ended_publication_destroyed)
      .Unsigned("ended_disconnected", c.ended_disconnected)
      .Unsigned("ended_silence_timeout", c.ended_silence_timeout)
      .Unsigned("unsubscribe_failures", c.unsubscribe_failures)
      .Unsigned("notifications_not_acted_on", c.notifications_not_acted_on)
      .Unsigned("gateway_calls_stalled", c.gateway_calls_stalled);
  return record;
}

}  // namespace de4sdv::ivi_frame_relay
