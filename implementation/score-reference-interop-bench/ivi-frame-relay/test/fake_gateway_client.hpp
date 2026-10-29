// The fake gateway client and the test helpers of the relay's tests.
//
// FakeGatewayClient stands in for the AOSP adapter: it keeps a scripted
// publication (available or destroyed, with a new id after each restore),
// returns the queued slots on reads, and sends PublicationDestroyed and
// Disconnected to the worker like the library's callbacks. It is thread-safe,
// so the shell tests can drive it from the test thread while the worker
// thread calls it. It fails the test when a subscribe comes while a
// subscription is active, because the relay holds one at a time.

#ifndef DE4SDV_IVI_FRAME_RELAY_TEST_FAKE_GATEWAY_CLIENT_HPP
#define DE4SDV_IVI_FRAME_RELAY_TEST_FAKE_GATEWAY_CLIENT_HPP

#include <gtest/gtest.h>

#include <algorithm>
#include <condition_variable>
#include <cstdint>
#include <cstring>
#include <deque>
#include <mutex>
#include <string>
#include <vector>

#include "de4sdv_ivi_frame_relay/event_log.hpp"
#include "de4sdv_ivi_frame_relay/gateway_client.hpp"
#include "de4sdv_ivi_frame_relay/gateway_worker.hpp"

namespace de4sdv::ivi_frame_relay::test {

using Bytes = std::vector<std::uint8_t>;

constexpr std::int64_t kMs = 1'000'000;
constexpr std::int64_t kSecond = 1'000'000'000;
// A realtime clock of 2026-10-28 and an unrelated monotonic clock.
constexpr Clock kStartClock{5'000 * kSecond, 1'793'116'443'934'013'818};
constexpr std::uint32_t kSlotBytes = 4101;  // the slot of the feasibility run

class ManualClock final : public ClockSource {
 public:
  explicit ManualClock(Clock start = kStartClock) : now_{start} {}
  Clock Now() override {
    const std::lock_guard<std::mutex> lock{mutex_};
    return now_;
  }
  void Advance(std::int64_t ns) {
    const std::lock_guard<std::mutex> lock{mutex_};
    now_.monotonic_ns += ns;
    now_.realtime_ns += ns;
  }
  // Steps the realtime clock only.
  void StepRealtime(std::int64_t ns) {
    const std::lock_guard<std::mutex> lock{mutex_};
    now_.realtime_ns += ns;
  }
  void AdvanceTo(std::int64_t monotonic_ns) {
    const std::lock_guard<std::mutex> lock{mutex_};
    if (monotonic_ns > now_.monotonic_ns) {
      const std::int64_t delta = monotonic_ns - now_.monotonic_ns;
      now_.monotonic_ns += delta;
      now_.realtime_ns += delta;
    }
  }

 private:
  std::mutex mutex_;
  Clock now_;
};

class CollectingSink final : public WorkerEventSink {
 public:
  void Post(WorkerEvent&& event) override { events.push_back(std::move(event)); }
  std::vector<WorkerEvent> Take() {
    std::vector<WorkerEvent> taken;
    taken.swap(events);
    return taken;
  }
  std::vector<WorkerEvent> events;
};

// The broker's wrapper, built as the broker builds it: the outer varint, tag
// 0x0A, the inner varint, the payload, and zeros up to the slot size.
inline void PutVarint(Bytes& out, std::uint64_t value) {
  while (value >= 0x80U) {
    out.push_back(static_cast<std::uint8_t>((value & 0x7FU) | 0x80U));
    value >>= 7U;
  }
  out.push_back(static_cast<std::uint8_t>(value));
}

inline std::size_t VarintSize(std::uint64_t value) {
  std::size_t size = 1;
  while (value >= 0x80U) {
    value >>= 7U;
    ++size;
  }
  return size;
}

inline Bytes WrapLikeBroker(const Bytes& payload, std::size_t slot_bytes = kSlotBytes) {
  Bytes slot;
  const std::size_t message = 1 + VarintSize(payload.size()) + payload.size();
  PutVarint(slot, message);
  slot.push_back(0x0A);
  PutVarint(slot, payload.size());
  slot.insert(slot.end(), payload.begin(), payload.end());
  if (slot.size() < slot_bytes) {
    slot.resize(slot_bytes, 0U);
  }
  return slot;
}

// A VisualizationFrame with schema 1.1, sequence (3) and frame_timestamp_ns
// (4), and filler in source_identity (6) up to about size bytes.
inline Bytes VisualizationFrame(std::uint64_t sequence, std::int64_t timestamp_ns, std::size_t filler = 8) {
  Bytes frame{0x08, 0x01, 0x10, 0x01};
  frame.push_back(0x18);
  PutVarint(frame, sequence);
  frame.push_back(0x20);
  PutVarint(frame, static_cast<std::uint64_t>(timestamp_ns));
  frame.push_back(0x32);
  PutVarint(frame, filler);
  for (std::size_t index = 0; index < filler; ++index) {
    frame.push_back(static_cast<std::uint8_t>('a' + index % 26U));
  }
  return frame;
}

// The 4-byte little-endian length prefix and the frame: the SOME/IP payload.
inline Bytes Prefixed(const Bytes& frame) {
  const auto length = static_cast<std::uint32_t>(frame.size());
  Bytes payload{static_cast<std::uint8_t>(length & 0xFFU), static_cast<std::uint8_t>((length >> 8U) & 0xFFU),
                static_cast<std::uint8_t>((length >> 16U) & 0xFFU), static_cast<std::uint8_t>(length >> 24U)};
  for (const std::uint8_t byte : frame) {  // a loop: GCC 11 warns falsely on insert() here
    payload.push_back(byte);
  }
  return payload;
}

inline Bytes FramePayload(std::uint64_t sequence, std::int64_t timestamp_ns, std::size_t filler = 8) {
  return Prefixed(VisualizationFrame(sequence, timestamp_ns, filler));
}

inline Bytes FrameSlot(std::uint64_t sequence, std::int64_t timestamp_ns, std::size_t filler = 8) {
  return WrapLikeBroker(FramePayload(sequence, timestamp_ns, filler));
}

class FakeGatewayClient final : public GatewayClient {
 public:
  explicit FakeGatewayClient(ManualClock* clock = nullptr) : clock_{clock} {}

  // Scripting, from any thread.
  void FailCreates(int count, GatewayResult result) {
    const std::lock_guard<std::mutex> lock{mutex_};
    create_failures_ = count;
    create_failure_ = std::move(result);
  }
  void FailSubscribes(int count, GatewayResult result) {
    const std::lock_guard<std::mutex> lock{mutex_};
    subscribe_failures_ = count;
    subscribe_failure_ = std::move(result);
  }
  void SetMetadata(std::uint32_t message_size_bytes, std::uint32_t message_count) {
    const std::lock_guard<std::mutex> lock{mutex_};
    message_size_bytes_ = message_size_bytes;
    message_count_ = message_count;
  }
  void SetCallLatency(std::int64_t ns) {
    const std::lock_guard<std::mutex> lock{mutex_};
    latency_ns_ = ns;
  }
  // The next reads return these slots, as many as fit, and notify.
  void QueueSlot(Bytes slot) {
    GatewayNotificationSink* sink = nullptr;
    GatewayNotification notification;
    {
      const std::lock_guard<std::mutex> lock{mutex_};
      reads_.push_back(QueuedRead{ReadOutcome::kMessages, {}, std::move(slot)});
      sink = subscribed_ ? sink_ : nullptr;
      notification.kind = GatewayNotificationKind::kDataAvailable;
      notification.subscription_generation = subscription_generation_;
      notification.publication_id = publication_id_;
      notification.raw_type = 1;
    }
    if (sink != nullptr) {
      sink->Notify(notification);
    }
  }
  void QueueDataLoss() {
    const std::lock_guard<std::mutex> lock{mutex_};
    reads_.push_back(QueuedRead{ReadOutcome::kDataLoss, GatewayResult{kGatewayDataLoss, "queue overflow"}, {}});
  }
  void QueueReadFailure(GatewayResult status) {
    const std::lock_guard<std::mutex> lock{mutex_};
    reads_.push_back(QueuedRead{ReadOutcome::kFailed, std::move(status), {}});
  }
  // someipd restarts: the broker destroys its publication.
  void DestroyPublication() {
    GatewayNotificationSink* sink = nullptr;
    GatewayNotification notification;
    {
      const std::lock_guard<std::mutex> lock{mutex_};
      publication_available_ = false;
      sink = subscribed_ ? sink_ : nullptr;
      notification.kind = GatewayNotificationKind::kPublicationDestroyed;
      notification.subscription_generation = subscription_generation_;
      notification.publication_id = publication_id_;
      notification.raw_type = 2;
    }
    if (sink != nullptr) {
      sink->Notify(notification);
    }
  }
  // The broker publishes again, with a new id.
  void RestorePublication() {
    const std::lock_guard<std::mutex> lock{mutex_};
    publication_available_ = true;
  }
  void Disconnect() {
    GatewayNotificationSink* sink = nullptr;
    GatewayNotification notification;
    {
      const std::lock_guard<std::mutex> lock{mutex_};
      sink = sink_;
      notification.kind = GatewayNotificationKind::kDisconnected;
      notification.client_generation = client_generation_;
      notification.raw_type = 3;
    }
    if (sink != nullptr) {
      sink->Notify(notification);
    }
  }
  // Sends a notification as it is, for late ones of old generations.
  void Send(const GatewayNotification& notification) {
    GatewayNotificationSink* sink = nullptr;
    {
      const std::lock_guard<std::mutex> lock{mutex_};
      sink = sink_;
    }
    if (sink != nullptr) {
      sink->Notify(notification);
    }
  }
  // Create blocks until ReleaseCreate.
  void BlockCreate() {
    const std::lock_guard<std::mutex> lock{mutex_};
    create_blocked_ = true;
  }
  void ReleaseCreate() {
    {
      const std::lock_guard<std::mutex> lock{mutex_};
      create_blocked_ = false;
    }
    released_.notify_all();
  }

  // Observation, from any thread.
  std::vector<std::string> calls() const {
    const std::lock_guard<std::mutex> lock{mutex_};
    return calls_;
  }
  std::size_t count(const std::string& name) const {
    const std::lock_guard<std::mutex> lock{mutex_};
    return static_cast<std::size_t>(std::count(calls_.begin(), calls_.end(), name));
  }
  bool subscribed() const {
    const std::lock_guard<std::mutex> lock{mutex_};
    return subscribed_;
  }
  bool has_client() const {
    const std::lock_guard<std::mutex> lock{mutex_};
    return has_client_;
  }
  bool create_waiting() const {
    const std::lock_guard<std::mutex> lock{mutex_};
    return create_waiting_;
  }
  std::int32_t publication_id() const {
    const std::lock_guard<std::mutex> lock{mutex_};
    return publication_id_;
  }
  std::uint64_t subscription_generation() const {
    const std::lock_guard<std::mutex> lock{mutex_};
    return subscription_generation_;
  }
  std::uint64_t client_generation() const {
    const std::lock_guard<std::mutex> lock{mutex_};
    return client_generation_;
  }
  std::uint64_t last_flags() const {
    const std::lock_guard<std::mutex> lock{mutex_};
    return last_flags_;
  }
  SubjectIdentity last_subject() const {
    const std::lock_guard<std::mutex> lock{mutex_};
    return last_subject_;
  }
  PublicationName last_publication() const {
    const std::lock_guard<std::mutex> lock{mutex_};
    return last_publication_;
  }
  std::size_t last_read_capacity() const {
    const std::lock_guard<std::mutex> lock{mutex_};
    return last_read_capacity_;
  }

  // GatewayClient, from the worker.
  GatewayResult Create(std::uint64_t client_generation, const SubjectIdentity& subject,
                       GatewayNotificationSink& sink) override {
    std::unique_lock<std::mutex> lock{mutex_};
    calls_.emplace_back("create");
    create_waiting_ = create_blocked_;
    released_.wait(lock, [this] { return !create_blocked_; });
    create_waiting_ = false;
    Spend();
    last_subject_ = subject;
    if (create_failures_ > 0) {
      --create_failures_;
      return create_failure_;
    }
    has_client_ = true;
    client_generation_ = client_generation;
    sink_ = &sink;
    return GatewayResult{};
  }
  GatewayResult Destroy() override {
    const std::lock_guard<std::mutex> lock{mutex_};
    calls_.emplace_back("destroy");
    Spend();
    has_client_ = false;
    subscribed_ = false;
    return GatewayResult{};
  }
  GatewayResult Subscribe(std::uint64_t subscription_generation, const PublicationName& publication,
                          PublicationMetadata* metadata) override {
    const std::lock_guard<std::mutex> lock{mutex_};
    calls_.emplace_back("subscribe");
    EXPECT_TRUE(has_client_) << "subscribe without a client";
    EXPECT_FALSE(subscribed_) << "a second subscription while one is active";
    Spend();
    last_publication_ = publication;
    last_flags_ = kSubscriberFlagNone;  // the interface has no other flag
    if (subscribe_failures_ > 0) {
      --subscribe_failures_;
      return subscribe_failure_;
    }
    if (!publication_available_) {
      return GatewayResult{5, "No publication service unit found"};
    }
    if (publication_id_ == 0 || !publication_kept_) {
      publication_id_ = ++publications_;
      publication_kept_ = true;
    }
    subscribed_ = true;
    subscription_generation_ = subscription_generation;
    metadata->publication_id = publication_id_;
    metadata->message_size_bytes = message_size_bytes_;
    metadata->message_count = message_count_;
    metadata->subscriber_flags = kSubscriberFlagNone;
    return GatewayResult{};
  }
  GatewayResult Unsubscribe(std::int32_t publication_id) override {
    const std::lock_guard<std::mutex> lock{mutex_};
    calls_.emplace_back("unsubscribe:" + std::to_string(publication_id));
    Spend();
    subscribed_ = false;
    if (!publication_available_) {
      publication_kept_ = false;  // a restored publication has a new id
    }
    return GatewayResult{};
  }
  ReadResult Read(std::int32_t publication_id, std::uint8_t* buffer, std::size_t capacity) override {
    const std::lock_guard<std::mutex> lock{mutex_};
    calls_.emplace_back("read");
    Spend();
    last_read_capacity_ = capacity;
    ReadResult result;
    if (!subscribed_ || publication_id != publication_id_ || reads_.empty()) {
      result.outcome = ReadOutcome::kNoMessage;
      result.status = GatewayResult{kGatewayUnavailable, ""};
      return result;
    }
    if (reads_.front().outcome != ReadOutcome::kMessages) {
      result.outcome = reads_.front().outcome;
      result.status = reads_.front().status;
      reads_.pop_front();
      return result;
    }
    const std::size_t fits = message_size_bytes_ == 0U ? 0U : capacity / message_size_bytes_;
    while (!reads_.empty() && reads_.front().outcome == ReadOutcome::kMessages && result.count < fits) {
      Bytes& slot = reads_.front().slot;
      slot.resize(message_size_bytes_, 0U);
      std::memcpy(buffer + static_cast<std::size_t>(result.count) * message_size_bytes_, slot.data(), slot.size());
      ++result.count;
      reads_.pop_front();
    }
    result.outcome = ReadOutcome::kMessages;
    return result;
  }

 private:
  struct QueuedRead {
    ReadOutcome outcome;
    GatewayResult status;
    Bytes slot;
  };

  void Spend() {
    if (clock_ != nullptr && latency_ns_ > 0) {
      clock_->Advance(latency_ns_);
    }
  }

  ManualClock* clock_;
  mutable std::mutex mutex_;
  std::condition_variable released_;
  std::vector<std::string> calls_;
  GatewayNotificationSink* sink_{nullptr};
  bool has_client_{false};
  bool subscribed_{false};
  bool publication_available_{true};
  bool publication_kept_{false};
  bool create_blocked_{false};
  bool create_waiting_{false};
  int create_failures_{0};
  GatewayResult create_failure_;
  int subscribe_failures_{0};
  GatewayResult subscribe_failure_;
  std::uint32_t message_size_bytes_{kSlotBytes};
  std::uint32_t message_count_{16};
  std::int64_t latency_ns_{0};
  std::int32_t publication_id_{0};
  std::int32_t publications_{1};
  std::uint64_t client_generation_{0};
  std::uint64_t subscription_generation_{0};
  std::uint64_t last_flags_{0};
  SubjectIdentity last_subject_;
  PublicationName last_publication_;
  std::size_t last_read_capacity_{0};
  std::deque<QueuedRead> reads_;
};

}  // namespace de4sdv::ivi_frame_relay::test

#endif  // DE4SDV_IVI_FRAME_RELAY_TEST_FAKE_GATEWAY_CLIENT_HPP
