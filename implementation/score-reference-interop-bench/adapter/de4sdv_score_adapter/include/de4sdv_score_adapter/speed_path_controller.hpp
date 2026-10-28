// Pure core of the AutowareToSCORE adapter: the speed path controller, with
// the first and second LoLa rules of the phase-8 realization (INC-MW-011).
//
// Rule 1, stored samples (GAP-MW-039, REQ-MW-013): a new LoLa subscription
// returns the samples that the provider sent before it. The controller
// counts every time the subscription leaves kSubscribed (an epoch). In the
// first subscription and in each later epoch, the first stable read in
// kSubscribed is read and discarded. Every next read is discarded too while
// the reads return max_samples samples, because a full read can mean that
// more stored samples wait. The first stable read with fewer samples ends
// the discard. A read publishes only if the subscription was kSubscribed
// before and after it and no leave happened during it; other reads are
// dropped. A read never starts outside kSubscribed. The cost, as the model
// states: a sample that arrives just before or during a discard read is
// lost.
//
// LoLa itself delivers at most max_samples new samples in one read: the
// newest ones. When more new samples wait, LoLa skips the older ones for
// good. So a burst of more than max_samples samples between two reads loses
// its oldest samples, and the adapter cannot count them.
//
// Rule 2, shutdown (GAP-MW-041): Shutdown() stops the reads, unsets the
// receive handler, calls Unsubscribe(), waits for kNotSubscribed and only
// then unsets the state handler and destroys the proxy. A proxy that stays
// subscribed is never destroyed.
//
// Threads: OnSubscriptionStateChanged() runs in the LoLa state handler,
// under the binding's own lock, and calls no port function. ReadAvailable()
// runs in one reader thread. Shutdown() may run in another thread; it waits
// for a read in progress.

#ifndef DE4SDV_SCORE_ADAPTER_SPEED_PATH_CONTROLLER_HPP
#define DE4SDV_SCORE_ADAPTER_SPEED_PATH_CONTROLLER_HPP

#include <atomic>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <mutex>
#include <vector>

#include "de4sdv_score_adapter/ports.hpp"
#include "de4sdv_score_adapter/speed_translation.hpp"

namespace de4sdv::score_adapter {

enum class SubscribeResult {
  kSubscribed,            // both handlers set and the subscription accepted
  kStateHandlerFailed,    // mw::com refused the subscription state handler
  kReceiveHandlerFailed,  // mw::com refused the receive handler
  kSubscribeFailed,       // mw::com refused Subscribe(), for example no free subscriber or slot
  kShutDown,              // Shutdown() ran before
};

const char* ToText(SubscribeResult result) noexcept;

enum class ShutdownResult {
  kNoProxy,          // nothing was subscribed
  kProxyDestroyed,   // rule 2 completed
  kStillSubscribed,  // Unsubscribe() did not reach kNotSubscribed in time; proxy kept
};

struct SpeedPathCounters {
  std::uint64_t state_changes{0};
  std::uint64_t subscription_leaves{0};
  std::uint64_t reads{0};
  std::uint64_t discard_reads{0};
  std::uint64_t read_errors{0};
  std::uint64_t samples_read{0};
  std::uint64_t samples_discarded_stored{0};
  std::uint64_t samples_dropped_unstable{0};
  std::uint64_t samples_published{0};
  std::uint64_t samples_withheld_non_finite{0};
  std::uint64_t samples_withheld_out_of_range{0};
};

// Optional observer of what the controller drops, for the adapter's log.
// Called in the reader thread, after the read.
class SpeedPathEvents {
 public:
  virtual ~SpeedPathEvents() = default;
  virtual void OnSampleWithheld(double speed_kmh, TranslationOutcome outcome) = 0;
  virtual void OnStoredSamplesDiscarded(std::size_t count) = 0;
  virtual void OnUnstableReadDropped(std::size_t count) = 0;
};

class SpeedPathController {
 public:
  SpeedPathController(SpeedEventPort& event, VelocityPublisherPort& publisher, std::size_t max_samples,
                      SpeedPathEvents* events = nullptr);

  // For a created proxy: sets the state handler, then the receive handler,
  // then subscribes the speed event with max_samples, so the controller sees
  // every state change. It stops at the first step that mw::com refuses.
  // After any call, Shutdown() cleans up by rule 2.
  SubscribeResult Subscribe();

  // LoLa state handler context: lock-free, no port call.
  void OnSubscriptionStateChanged(SubscriptionState new_state) noexcept;

  // Reader thread: reads until no further sample is waiting.
  void ReadAvailable();

  ShutdownResult Shutdown(std::chrono::milliseconds unsubscribe_timeout);

  SpeedPathCounters counters() const noexcept;

 private:
  // Returns true when the read returned max_samples_ samples, so more may wait.
  bool ReadOnce();
  void PublishOrWithhold(double speed_kmh);

  SpeedEventPort& event_;
  VelocityPublisherPort& publisher_;
  const std::size_t max_samples_;
  SpeedPathEvents* events_;

  std::mutex read_mutex_;
  bool proxy_present_{false};
  bool shut_down_{false};
  // The last epoch whose discard has ended (rule 1).
  std::uint64_t discarded_epoch_{0};
  std::vector<double> buffer_;

  std::atomic<std::uint64_t> leave_epoch_{1};
  std::atomic<std::uint64_t> state_changes_{0};
  std::atomic<std::uint64_t> reads_{0};
  std::atomic<std::uint64_t> discard_reads_{0};
  std::atomic<std::uint64_t> read_errors_{0};
  std::atomic<std::uint64_t> samples_read_{0};
  std::atomic<std::uint64_t> samples_discarded_stored_{0};
  std::atomic<std::uint64_t> samples_dropped_unstable_{0};
  std::atomic<std::uint64_t> samples_published_{0};
  std::atomic<std::uint64_t> samples_withheld_non_finite_{0};
  std::atomic<std::uint64_t> samples_withheld_out_of_range_{0};
};

}  // namespace de4sdv::score_adapter

#endif  // DE4SDV_SCORE_ADAPTER_SPEED_PATH_CONTROLLER_HPP
