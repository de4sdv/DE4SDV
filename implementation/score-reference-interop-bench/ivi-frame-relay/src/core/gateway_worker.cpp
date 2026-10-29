#include "de4sdv_ivi_frame_relay/gateway_worker.hpp"

#include <algorithm>
#include <utility>

namespace de4sdv::ivi_frame_relay {

namespace {

// The read buffer holds at most kMaxReadSlots slots and 4 MiB.
constexpr std::size_t kMaxReadBufferBytes = std::size_t{4} << 20U;

std::size_t SlotsFor(const PublicationMetadata& publication) {
  const std::size_t by_count = std::clamp<std::size_t>(publication.message_count, 1U, kMaxReadSlots);
  const std::size_t by_bytes = std::max<std::size_t>(1U, kMaxReadBufferBytes / publication.message_size_bytes);
  return std::min(by_count, by_bytes);
}

}  // namespace

const char* ToText(WorkerEventKind kind) noexcept {
  switch (kind) {
    case WorkerEventKind::kClientCreate:
      return "client_create";
    case WorkerEventKind::kClientDestroyed:
      return "client_destroyed";
    case WorkerEventKind::kSubscribed:
      return "subscribed";
    case WorkerEventKind::kSubscribeFailed:
      return "subscribe_failed";
    case WorkerEventKind::kSubscriptionEnded:
      return "subscription_ended";
    case WorkerEventKind::kUnsubscribed:
      return "unsubscribed";
    case WorkerEventKind::kMessage:
      return "message";
    case WorkerEventKind::kDataLoss:
      return "data_loss";
    case WorkerEventKind::kReadFailed:
      return "read_failed";
    case WorkerEventKind::kNotification:
      return "notification";
  }
  return "unknown";
}

void GatewayCallMonitor::Begin(const char* name, std::int64_t now_ns) {
  const std::lock_guard<std::mutex> lock{mutex_};
  in_call_ = true;
  current_.number += 1U;
  current_.name = name;
  current_.since_ns = now_ns;
  current_.end_ns = 0;
  current_stalled_ = false;
}

void GatewayCallMonitor::End(std::int64_t now_ns) {
  const std::lock_guard<std::mutex> lock{mutex_};
  in_call_ = false;
  current_.end_ns = now_ns;
  if (current_stalled_) {
    returned_ = current_;
    current_stalled_ = false;
  }
}

std::optional<GatewayCallMonitor::Call> GatewayCallMonitor::Current() const {
  const std::lock_guard<std::mutex> lock{mutex_};
  if (!in_call_) {
    return std::nullopt;
  }
  return current_;
}

std::optional<GatewayCallMonitor::Call> GatewayCallMonitor::TakeNewStall(std::int64_t now_ns,
                                                                         std::int64_t threshold_ns) {
  const std::lock_guard<std::mutex> lock{mutex_};
  if (!in_call_ || current_stalled_ || now_ns - current_.since_ns < threshold_ns) {
    return std::nullopt;
  }
  current_stalled_ = true;
  return current_;
}

std::optional<GatewayCallMonitor::Call> GatewayCallMonitor::TakeReturnedStall() {
  const std::lock_guard<std::mutex> lock{mutex_};
  std::optional<Call> returned = returned_;
  returned_.reset();
  return returned;
}

GatewayWorker::GatewayWorker(WorkerConfig config, GatewayClient& client, WorkerEventSink& sink, ClockSource& clock,
                             GatewayCallMonitor* monitor, WorkerWaker* waker)
    : config_{std::move(config)}, client_{client}, sink_{sink}, clock_{clock}, monitor_{monitor}, waker_{waker} {}

void GatewayWorker::Notify(const GatewayNotification& notification) noexcept {
  {
    const std::lock_guard<std::mutex> lock{inbox_mutex_};
    if (notification.kind == GatewayNotificationKind::kDataAvailable) {
      data_available_ = true;  // coalesced: the next read takes every slot
    } else if (inbox_.size() < kInboxCapacity) {
      inbox_.push_back(notification);
    } else {
      ++inbox_dropped_;
    }
  }
  if (waker_ != nullptr) {
    waker_->Wake();
  }
}

void GatewayWorker::RequestStop() noexcept {
  stop_requested_.store(true);
  if (waker_ != nullptr) {
    waker_->Wake();
  }
}

template <typename Function>
auto GatewayWorker::Call(const char* name, Function&& function) {
  if (monitor_ != nullptr) {
    monitor_->Begin(name, clock_.Now().monotonic_ns);
  }
  auto result = function();
  if (monitor_ != nullptr) {
    monitor_->End(clock_.Now().monotonic_ns);
  }
  return result;
}

void GatewayWorker::Start() {
  const Clock now = clock_.Now();
  schedule_ = RetrySchedule{now.monotonic_ns};
  next_client_attempt_ns_ = now.monotonic_ns;
  next_subscribe_attempt_ns_ = now.monotonic_ns;
}

void GatewayWorker::PostNotification(const GatewayNotification& notification, const Clock& now, const char* note) {
  WorkerEvent event;
  event.kind = WorkerEventKind::kNotification;
  event.at = now;
  event.notification = notification.kind;
  event.raw_type = notification.raw_type;
  event.publication.publication_id = notification.publication_id;
  event.note = note;
  sink_.Post(std::move(event));
}

void GatewayWorker::EndSubscription(SubscriptionEnd end, bool unsubscribe, const Clock& now) {
  subscribed_ = false;
  schedule_.OnEnded(end, messages_in_subscription_, now.monotonic_ns);
  if (end == SubscriptionEnd::kDisconnected) {
    schedule_.OnClientLost(now.monotonic_ns);
  }
  next_subscribe_attempt_ns_ = schedule_.FirstAttemptNs(now.monotonic_ns);
  WorkerEvent event;
  event.kind = WorkerEventKind::kSubscriptionEnded;
  event.at = now;
  event.end = end;
  event.subscription = subscriptions_;
  event.publication = publication_;
  event.messages = messages_in_subscription_;
  event.consecutive_silent = schedule_.consecutive_silent();
  if (end == SubscriptionEnd::kPublicationDestroyed || end == SubscriptionEnd::kSilenceTimeout) {
    event.next_attempt_ns = next_subscribe_attempt_ns_;
    event.rule = schedule_.SubscribeRule(next_subscribe_attempt_ns_);
  }
  sink_.Post(std::move(event));
  if (unsubscribe) {
    const std::int32_t publication_id = publication_.publication_id;
    GatewayResult result = Call("unsubscribe", [&] { return client_.Unsubscribe(publication_id); });
    WorkerEvent done;
    done.kind = WorkerEventKind::kUnsubscribed;
    done.at = clock_.Now();
    done.status = std::move(result);
    done.subscription = subscriptions_;
    done.publication = publication_;
    sink_.Post(std::move(done));
  }
}

void GatewayWorker::DestroyClient(const char* cause) {
  GatewayResult result = Call("destroy_client", [&] { return client_.Destroy(); });
  has_client_ = false;
  WorkerEvent event;
  event.kind = WorkerEventKind::kClientDestroyed;
  event.at = clock_.Now();
  event.status = std::move(result);
  event.note = cause;
  sink_.Post(std::move(event));
}

void GatewayWorker::HandleNotification(const GatewayNotification& notification, const Clock& now) {
  switch (notification.kind) {
    case GatewayNotificationKind::kDisconnected:
      if (!has_client_ || notification.client_generation != client_generation_) {
        PostNotification(notification, now, "ignored_not_the_current_client");
        return;
      }
      if (subscribed_) {
        EndSubscription(SubscriptionEnd::kDisconnected, false, now);
      } else {
        schedule_.OnClientLost(now.monotonic_ns);
      }
      DestroyClient("disconnected");
      next_client_attempt_ns_ = clock_.Now().monotonic_ns;
      return;
    case GatewayNotificationKind::kPublicationDestroyed:
      if (!subscribed_ || notification.subscription_generation != subscription_generation_) {
        PostNotification(notification, now, "ignored_not_the_current_subscription");
        return;
      }
      EndSubscription(SubscriptionEnd::kPublicationDestroyed, true, now);
      return;
    case GatewayNotificationKind::kOtherClientNotification:
    case GatewayNotificationKind::kOtherSubscriptionNotification:
      PostNotification(notification, now, "not_acted_on");
      return;
    case GatewayNotificationKind::kDataAvailable:
      return;  // never queued
  }
}

std::int64_t GatewayWorker::Step() {
  Clock now = clock_.Now();
  std::deque<GatewayNotification> inbox;
  bool data_available = false;
  std::uint64_t dropped = 0;
  {
    const std::lock_guard<std::mutex> lock{inbox_mutex_};
    inbox.swap(inbox_);
    data_available = data_available_;
    data_available_ = false;
    dropped = inbox_dropped_;
    inbox_dropped_ = 0;
  }
  if (dropped > 0U) {
    WorkerEvent event;
    event.kind = WorkerEventKind::kNotification;
    event.at = now;
    event.messages = dropped;
    event.note = "inbox_full_notifications_dropped";
    sink_.Post(std::move(event));
  }
  for (const GatewayNotification& notification : inbox) {
    HandleNotification(notification, now);
    now = clock_.Now();
  }
  if (stop_requested_.load()) {
    return now.monotonic_ns;
  }
  if (!has_client_) {
    return StepClient(now);
  }
  if (!subscribed_) {
    return StepSubscribe(now);
  }
  return StepRead(now, data_available);
}

std::int64_t GatewayWorker::StepClient(const Clock& now) {
  if (now.monotonic_ns < next_client_attempt_ns_) {
    return next_client_attempt_ns_;
  }
  const std::uint64_t attempt = ++client_attempts_;
  const std::uint64_t generation = ++client_generation_;
  GatewayResult result = Call("create_client", [&] { return client_.Create(generation, config_.subject, *this); });
  const Clock after = clock_.Now();
  WorkerEvent event;
  event.kind = WorkerEventKind::kClientCreate;
  event.at = after;
  event.attempt = attempt;
  if (result.ok()) {
    has_client_ = true;
    next_subscribe_attempt_ns_ = std::max(next_subscribe_attempt_ns_, schedule_.FirstAttemptNs(after.monotonic_ns));
    event.status = std::move(result);
    sink_.Post(std::move(event));
    return next_subscribe_attempt_ns_;
  }
  next_client_attempt_ns_ = schedule_.NextClientAttemptNs(now.monotonic_ns, after.monotonic_ns);
  event.status = std::move(result);
  event.next_attempt_ns = next_client_attempt_ns_;
  sink_.Post(std::move(event));
  return next_client_attempt_ns_;
}

std::int64_t GatewayWorker::StepSubscribe(const Clock& now) {
  if (now.monotonic_ns < next_subscribe_attempt_ns_) {
    return next_subscribe_attempt_ns_;
  }
  const std::uint64_t attempt = ++subscribe_attempts_;
  const std::uint64_t generation = ++subscription_generation_;
  const char* rule = schedule_.SubscribeRule(now.monotonic_ns);
  PublicationMetadata metadata;
  GatewayResult result =
      Call("subscribe", [&] { return client_.Subscribe(generation, config_.publication, &metadata); });
  const Clock after = clock_.Now();
  const bool metadata_valid = metadata.message_size_bytes > 0U && metadata.message_size_bytes <= kMaxSlotBytes;
  if (result.ok() && metadata_valid) {
    subscribed_ = true;
    publication_ = metadata;
    ++subscriptions_;
    messages_in_subscription_ = 0;
    last_message_ns_ = after.monotonic_ns;
    next_read_ns_ = after.monotonic_ns;
    last_read_data_loss_ = false;
    slots_ = SlotsFor(metadata);
    buffer_.assign(slots_ * metadata.message_size_bytes, 0U);
    schedule_.OnSubscribed();
    WorkerEvent event;
    event.kind = WorkerEventKind::kSubscribed;
    event.at = after;
    event.attempt = attempt;
    event.subscription = subscriptions_;
    event.publication = metadata;
    event.rule = rule;
    sink_.Post(std::move(event));
    return after.monotonic_ns;
  }
  WorkerEvent event;
  event.kind = WorkerEventKind::kSubscribeFailed;
  event.at = after;
  event.attempt = attempt;
  event.rule = rule;
  event.publication = metadata;
  if (result.ok()) {
    // Subscribed, but with a message size that the relay does not read: end it.
    event.status = GatewayResult{result.code, "metadata refused: message_size_bytes " +
                                                  std::to_string(metadata.message_size_bytes)};
    event.note = "metadata_refused";
    const std::int32_t publication_id = metadata.publication_id;
    (void)Call("unsubscribe", [&] { return client_.Unsubscribe(publication_id); });
  } else {
    event.status = std::move(result);
  }
  next_subscribe_attempt_ns_ = schedule_.NextAttemptNs(now.monotonic_ns, clock_.Now().monotonic_ns);
  event.next_attempt_ns = next_subscribe_attempt_ns_;
  sink_.Post(std::move(event));
  return next_subscribe_attempt_ns_;
}

std::int64_t GatewayWorker::StepRead(const Clock& now, bool data_available) {
  Clock current = now;
  if (data_available || now.monotonic_ns >= next_read_ns_) {
    ++reads_;
    const std::int32_t publication_id = publication_.publication_id;
    ReadResult read = Call("read", [&] { return client_.Read(publication_id, buffer_.data(), buffer_.size()); });
    current = clock_.Now();
    const bool data_loss = read.outcome == ReadOutcome::kDataLoss;
    if (read.outcome == ReadOutcome::kMessages && read.count > 0U) {
      const std::size_t count = std::min<std::size_t>(read.count, slots_);
      const std::size_t size = publication_.message_size_bytes;
      for (std::size_t index = 0; index < count; ++index) {
        WorkerEvent event;
        event.kind = WorkerEventKind::kMessage;
        event.at = current;
        event.subscription = subscriptions_;
        event.publication = publication_;
        const auto first = buffer_.begin() + static_cast<std::ptrdiff_t>(index * size);
        event.slot.assign(first, first + static_cast<std::ptrdiff_t>(size));
        sink_.Post(std::move(event));
      }
      messages_in_subscription_ += count;
      last_message_ns_ = current.monotonic_ns;
      next_read_ns_ = current.monotonic_ns;  // more may be queued
    } else if (data_loss) {
      WorkerEvent event;
      event.kind = WorkerEventKind::kDataLoss;
      event.at = current;
      event.subscription = subscriptions_;
      event.publication = publication_;
      event.status = std::move(read.status);
      sink_.Post(std::move(event));
      // Read on at once after one DATA_LOSS; after a second in a row, wait.
      next_read_ns_ = last_read_data_loss_ ? current.monotonic_ns + kReadPollPeriodNs : current.monotonic_ns;
    } else if (read.outcome == ReadOutcome::kFailed) {
      WorkerEvent event;
      event.kind = WorkerEventKind::kReadFailed;
      event.at = current;
      event.subscription = subscriptions_;
      event.publication = publication_;
      event.status = std::move(read.status);
      sink_.Post(std::move(event));
      next_read_ns_ = current.monotonic_ns + kReadPollPeriodNs;
    } else {
      next_read_ns_ = current.monotonic_ns + kReadPollPeriodNs;
    }
    last_read_data_loss_ = data_loss;
  }
  if (current.monotonic_ns - last_message_ns_ >= kSilenceTimeoutNs) {
    EndSubscription(SubscriptionEnd::kSilenceTimeout, true, current);
    return next_subscribe_attempt_ns_;
  }
  return std::min(next_read_ns_, last_message_ns_ + kSilenceTimeoutNs);
}

void GatewayWorker::Finish() {
  const Clock now = clock_.Now();
  if (subscribed_) {
    EndSubscription(SubscriptionEnd::kRelayStop, true, now);
  }
  if (has_client_) {
    DestroyClient("relay_stop");
  }
}

}  // namespace de4sdv::ivi_frame_relay
