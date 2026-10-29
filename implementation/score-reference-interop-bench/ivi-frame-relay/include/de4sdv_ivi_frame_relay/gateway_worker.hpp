// The gateway worker of the DE4SDV IVI frame relay: it runs the gateway
// client (create, subscribe, read, unsubscribe, destroy) on a thread of its
// own (iviFrameRelay of the phase-8 model, owner decision of 2026-10-29).
// The loopback server and the ingress connection run on the main thread and
// do not depend on this one: the worker hands every result to the main
// thread as a WorkerEvent, and the main thread never calls the client.
//
// Its own waits are bounded: the thread of the shell waits for a
// notification, a stop request or the next deadline, and while the worker
// holds a subscription it reads at least every 20 ms. A call into the library can still block (the feasibility runs
// saw initComms block while the SD agent of the IVI VM could not start). A
// blocked call cannot be cancelled, so the worker marks each call in a
// GatewayCallMonitor, and the main thread reports a call that runs longer
// than 10 s.
//
// Step() is the logic of one turn, with the clock as an input, so the tests
// drive it with a fake client and a manual clock. The thread of the shell
// calls Step(), then waits until its deadline or until the WorkerWaker wakes
// it.
//
// What it does, by the rules of retry_schedule.hpp:
// - it creates the client and subscribes by name with
//   ASDVGATEWAY_SUBSCRIBER_OPTIONS_FLAG_NONE, one subscription at a time;
// - while subscribed it reads every slot and hands it on unparsed; a
//   DATA_LOSS status is a gap (GAP-MW-037), not the end of a phase, and its
//   buffer is not used. The relay's reading, not a value of the model: a
//   DATA_LOSS also counts as a sign of life for the 3 s timer, because an
//   overflow shows that messages came, and the next read follows at once;
// - on PublicationDestroyed of the current subscription it ends the
//   subscription, unsubscribes and subscribes again;
// - the library allows one client per process (libsdvgatewayclient.h:
//   473-475). So the worker calls ASDVGateway_Client_new once with success
//   and never deletes and re-creates the client. Only a Client_new that
//   itself failed is tried again, with a bounded wait. On Disconnected of
//   the current client, and when initComms fails, the worker ends the
//   subscription, hands on kClientLost and makes no further call: the main
//   thread ends the process with its own code, and init starts the relay
//   again as a new process;
// - a notification of an old subscription changes nothing;
// - when no message comes for 3 s it ends the subscription, unsubscribes
//   and subscribes again;
// - at stop it unsubscribes and deletes the client.
// A failed attempt is handed on with its status code and text.

#ifndef DE4SDV_IVI_FRAME_RELAY_GATEWAY_WORKER_HPP
#define DE4SDV_IVI_FRAME_RELAY_GATEWAY_WORKER_HPP

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <mutex>
#include <optional>
#include <vector>

#include "de4sdv_ivi_frame_relay/event_log.hpp"
#include "de4sdv_ivi_frame_relay/gateway_client.hpp"
#include "de4sdv_ivi_frame_relay/retry_schedule.hpp"

namespace de4sdv::ivi_frame_relay {

// The relay's reading, not a value of the model.
constexpr std::int64_t kReadPollPeriodNs = 20 * kNanosecondsPerMillisecond;
constexpr std::int64_t kGatewayCallStallNs = 10 * kNanosecondsPerSecond;
constexpr std::size_t kMaxReadSlots = 64;
// A publication whose message size is 0 or above this is refused.
constexpr std::uint32_t kMaxSlotBytes = 1U << 20U;
constexpr std::size_t kInboxCapacity = 64;

class ClockSource {
 public:
  virtual ~ClockSource() = default;
  virtual Clock Now() = 0;
};

enum class WorkerEventKind : std::uint8_t {
  kClientCreate,       // an attempt of Client_new or of initComms (note), ok or failed
  kClientLost,         // the client is lost for this process (note: the stage)
  kClientDestroyed,
  kSubscribed,         // a subscription succeeded
  kSubscribeFailed,
  kSubscriptionEnded,
  kUnsubscribed,
  kMessage,            // one slot, unparsed
  kDataLoss,
  kReadFailed,
  kNotification,       // a notification that the worker did not act on
};

const char* ToText(WorkerEventKind kind) noexcept;

struct WorkerEvent {
  WorkerEventKind kind{WorkerEventKind::kNotification};
  Clock at;  // when the worker saw it: for a call, at its return
  GatewayResult status;
  std::uint64_t attempt{0};       // the number of the attempt in the process
  std::uint64_t subscription{0};  // the number of the subscription in the process
  PublicationMetadata publication;
  SubscriptionEnd end{SubscriptionEnd::kRelayStop};
  std::uint64_t messages{0};            // kSubscriptionEnded: the messages of the subscription
  std::uint64_t consecutive_silent{0};  // kSubscriptionEnded: subscriptions in a row without a message
  std::int64_t next_attempt_ns{0};      // CLOCK_MONOTONIC of the next attempt; 0 when none is planned
  const char* rule{""};                 // the retry rule of the attempt or of the next one
  const char* note{""};
  GatewayNotificationKind notification{GatewayNotificationKind::kDataAvailable};
  std::int32_t raw_type{0};
  std::vector<std::uint8_t> slot;  // kMessage
};

// Wakes the thread that runs the worker: a notification came or a stop was
// requested. It must return at once.
class WorkerWaker {
 public:
  virtual ~WorkerWaker() = default;
  virtual void Wake() noexcept = 0;
};

// Takes the worker's events in order; the shell's mailbox to the main thread.
class WorkerEventSink {
 public:
  virtual ~WorkerEventSink() = default;
  virtual void Post(WorkerEvent&& event) = 0;
};

// The gateway call in progress, shared by the worker and the main thread.
class GatewayCallMonitor {
 public:
  struct Call {
    std::uint64_t number{0};
    const char* name{""};
    std::int64_t since_ns{0};  // CLOCK_MONOTONIC
    std::int64_t end_ns{0};    // 0 while it runs
  };

  void Begin(const char* name, std::int64_t now_ns);
  void End(std::int64_t now_ns);
  // The call in progress, if any.
  std::optional<Call> Current() const;
  // The call in progress if it has run for at least threshold_ns; once per call.
  std::optional<Call> TakeNewStall(std::int64_t now_ns, std::int64_t threshold_ns);
  // A call taken by TakeNewStall that has returned since; once.
  std::optional<Call> TakeReturnedStall();

 private:
  mutable std::mutex mutex_;
  bool in_call_{false};
  Call current_;
  bool current_stalled_{false};
  std::optional<Call> returned_;
};

struct WorkerConfig {
  SubjectIdentity subject;
  PublicationName publication;
};

class GatewayWorker final : public GatewayNotificationSink {
 public:
  GatewayWorker(WorkerConfig config, GatewayClient& client, WorkerEventSink& sink, ClockSource& clock,
                GatewayCallMonitor* monitor = nullptr, WorkerWaker* waker = nullptr);

  // GatewayNotificationSink: on the library's threads.
  void Notify(const GatewayNotification& notification) noexcept override;

  // Takes the start of the schedule from the clock.
  void Start();
  // One turn: the notifications, then at most one attempt or one read.
  // Returns the CLOCK_MONOTONIC time when the next turn is due.
  std::int64_t Step();
  // At stop: ends the subscription, unsubscribes, deletes the client.
  void Finish();
  void RequestStop() noexcept;
  bool stop_requested() const noexcept { return stop_requested_.load(); }

  bool has_client() const noexcept { return has_client_; }
  bool client_lost() const noexcept { return client_lost_; }
  bool subscribed() const noexcept { return subscribed_; }
  const PublicationMetadata& publication() const noexcept { return publication_; }
  const RetrySchedule& schedule() const noexcept { return schedule_; }
  std::uint64_t client_attempts() const noexcept { return client_attempts_; }
  std::uint64_t subscribe_attempts() const noexcept { return subscribe_attempts_; }
  std::uint64_t subscriptions() const noexcept { return subscriptions_; }
  std::uint64_t reads() const noexcept { return reads_; }
  std::int64_t next_subscribe_attempt_ns() const noexcept { return next_subscribe_attempt_ns_; }
  std::int64_t next_client_attempt_ns() const noexcept { return next_client_attempt_ns_; }

 private:
  template <typename Function>
  auto Call(const char* name, Function&& function);

  void HandleNotification(const GatewayNotification& notification, const Clock& now);
  void PostNotification(const GatewayNotification& notification, const Clock& now, const char* note);
  void EndSubscription(SubscriptionEnd end, bool unsubscribe, const Clock& now);
  void DestroyClient(const char* cause);
  void LoseClient(const Clock& now, const char* stage, GatewayResult status, std::int32_t raw_type);
  std::int64_t StepClient(const Clock& now);
  std::int64_t StepSubscribe(const Clock& now);
  std::int64_t StepRead(const Clock& now, bool data_available);

  WorkerConfig config_;
  GatewayClient& client_;
  WorkerEventSink& sink_;
  ClockSource& clock_;
  GatewayCallMonitor* monitor_;
  WorkerWaker* waker_;
  RetrySchedule schedule_{0};

  std::mutex inbox_mutex_;
  std::deque<GatewayNotification> inbox_;
  bool data_available_{false};
  std::uint64_t inbox_dropped_{0};
  std::atomic<bool> stop_requested_{false};

  bool client_created_{false};  // Client_new succeeded: the one client of the process
  bool has_client_{false};      // and initComms too
  bool client_lost_{false};
  bool subscribed_{false};
  std::uint64_t client_generation_{0};
  std::uint64_t subscription_generation_{0};
  std::uint64_t client_attempts_{0};
  std::uint64_t subscribe_attempts_{0};
  std::uint64_t subscriptions_{0};
  std::uint64_t reads_{0};
  std::int64_t next_client_attempt_ns_{0};
  std::int64_t next_subscribe_attempt_ns_{0};
  std::int64_t next_read_ns_{0};
  std::int64_t last_message_ns_{0};
  bool last_read_data_loss_{false};
  std::uint64_t messages_in_subscription_{0};
  PublicationMetadata publication_;
  std::size_t slots_{0};
  std::vector<std::uint8_t> buffer_;
};

}  // namespace de4sdv::ivi_frame_relay

#endif  // DE4SDV_IVI_FRAME_RELAY_GATEWAY_WORKER_HPP
