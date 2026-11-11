// DE4SDV closed-loop driving bench (INC-DRIVING-001, slice 10b): the navigation prefetch.
//
// conditionInputs needs the step's navigation raster (map_context, route_mask) drawn at the step's
// REF pose. The pose arrives with the world tick, about 40 ms before the last of the six camera
// images, but the chain only starts when the step is complete. Rendering on the chain (~2.4 ms)
// therefore lengthened every step of the 100 ms planning period (REQ-DRIVING-013). The prefetcher
// renders it on its own thread as soon as the snapshot arrives; the step takes the finished result.
// It changes when the raster is drawn, never what is drawn: same pose, same route, same renderer.
//
// Header-only and generic so that its threading is tested without the rasterizer. `Result` must
// have a `std::string route_event` (a route change the render raised, "" when none): the events of
// results that are never taken are carried to the next take, so no route change goes unlogged.
#pragma once

#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <deque>
#include <functional>
#include <map>
#include <mutex>
#include <string>
#include <thread>
#include <utility>
#include <vector>

#include "frame_store.h"

namespace de4sdv::driving::agent {

struct PrefetchStats {
  std::uint64_t submitted = 0;       // requests accepted
  std::uint64_t refusedUnarmed = 0;  // requests before Arm(true) or after Stop()
  std::uint64_t droppedQueue = 0;    // requests dropped from a full queue (the oldest first)
  std::uint64_t rendered = 0;        // renders completed
  std::uint64_t hits = 0;            // takes that got their frame's result
  std::uint64_t notSubmitted = 0;    // takes of a frame never requested (or already dropped)
  std::uint64_t timedOut = 0;        // takes that waited max_wait in vain
  std::uint64_t discarded = 0;       // results and queued requests of frames older than a take
};

enum class TakeOutcome { kHit, kNotSubmitted, kTimedOut };

// Whether the step may use a prefetched render: only if it is what a render on the chain would draw.
enum class UseDecision { kUse, kRenderFailed, kPoseChanged, kRouteChanged };

inline bool SamePose(const Pose& p, const Pose& q) {
  return p.x == q.x && p.y == q.y && p.z == q.z && p.roll == q.roll && p.pitch == q.pitch && p.yaw == q.yaw;
}

// render_ok: the prefetch's render succeeded; drawn_at / step_pose: the pose it was drawn at and the
// step's; drawn_route / route_now: the route identity it was drawn with and the newest one now.
inline UseDecision DecideUse(bool render_ok, const Pose& drawn_at, const Pose& step_pose, const std::string& drawn_route,
                             const std::string& route_now) {
  if (!render_ok) return UseDecision::kRenderFailed;
  if (!SamePose(drawn_at, step_pose)) return UseDecision::kPoseChanged;
  if (drawn_route != route_now) return UseDecision::kRouteChanged;
  return UseDecision::kUse;
}

template <typename Result>
class NavPrefetch {
 public:
  using RenderFn = std::function<void(std::uint64_t frame, const Pose& pose, std::int64_t arrivalMonoNs, Result* out)>;

  explicit NavPrefetch(std::size_t queue_capacity = 4, std::size_t keep_results = 8)
      : capacity_(queue_capacity == 0 ? 1 : queue_capacity), keep_(keep_results == 0 ? 1 : keep_results) {}
  NavPrefetch(const NavPrefetch&) = delete;
  NavPrefetch& operator=(const NavPrefetch&) = delete;
  ~NavPrefetch() { Stop(); }

  void Start(RenderFn render) {
    std::lock_guard<std::mutex> lock(mu_);
    if (worker_.joinable()) return;
    render_ = std::move(render);
    stop_ = false;
    worker_ = std::thread([this] { Run(); });
  }

  // Requests are refused until armed: the agent arms once the navigation input and the REF origin exist.
  void Arm(bool on) {
    std::lock_guard<std::mutex> lock(mu_);
    armed_ = on;
  }

  void Stop() {
    {
      std::lock_guard<std::mutex> lock(mu_);
      stop_ = true;
      armed_ = false;
    }
    cv_.notify_all();
    if (worker_.joinable() && worker_.get_id() != std::this_thread::get_id()) worker_.join();
  }

  // From the snapshot sink (LibCarla's tick thread): enqueue and return. Beyond the capacity the oldest
  // request is dropped; its step falls back to rendering on the chain.
  bool Submit(std::uint64_t frame, const Pose& pose, std::int64_t arrivalMonoNs) {
    {
      std::lock_guard<std::mutex> lock(mu_);
      if (!armed_ || stop_ || !worker_.joinable()) {
        ++stats_.refusedUnarmed;
        return false;
      }
      if (queue_.size() >= capacity_) {
        queue_.pop_front();
        ++stats_.droppedQueue;
      }
      queue_.push_back(Request{frame, pose, arrivalMonoNs});
      ++stats_.submitted;
    }
    cv_.notify_all();
    return true;
  }

  // The step's take. Results and queued requests of older frames are discarded (those frames are
  // never planned); their route events go to `carried`, oldest first. A result for `frame` is moved
  // into *out (kHit). A frame queued or being rendered is waited for, at most max_wait_ns
  // (kTimedOut when it does not finish). A frame never requested is kNotSubmitted at once.
  TakeOutcome Take(std::uint64_t frame, std::int64_t max_wait_ns, Result* out, std::vector<std::string>* carried,
                   double* waited_ms = nullptr) {
    const auto t0 = std::chrono::steady_clock::now();
    std::unique_lock<std::mutex> lock(mu_);
    DiscardOlderLocked(frame);
    auto it = results_.find(frame);
    if (it == results_.end()) {
      const bool pending = InFlightOrQueuedLocked(frame);
      if (!pending) {
        ++stats_.notSubmitted;
        DrainCarriedLocked(carried);
        if (waited_ms) *waited_ms = 0.0;
        return TakeOutcome::kNotSubmitted;
      }
      const auto done = [&] { return stop_ || results_.count(frame) != 0 || !InFlightOrQueuedLocked(frame); };
#if defined(__SANITIZE_THREAD__)
      // GCC 11's ThreadSanitizer does not intercept pthread_cond_clockwait, which wait_for uses, and
      // reports every timed wait as a double lock with races under the same mutex (a three-line
      // control shows it). Its build waits on a system_clock deadline (pthread_cond_timedwait).
      cv_.wait_until(lock, std::chrono::system_clock::now() + std::chrono::nanoseconds(max_wait_ns), done);
#else
      cv_.wait_for(lock, std::chrono::nanoseconds(max_wait_ns), done);  // monotonic
#endif
      it = results_.find(frame);
    }
    DrainCarriedLocked(carried);
    if (waited_ms) {
      *waited_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
    }
    if (it == results_.end()) {
      ++stats_.timedOut;
      return TakeOutcome::kTimedOut;
    }
    *out = std::move(it->second);
    results_.erase(it);
    ++stats_.hits;
    return TakeOutcome::kHit;
  }

  PrefetchStats Stats() const {
    std::lock_guard<std::mutex> lock(mu_);
    return stats_;
  }

 private:
  struct Request {
    std::uint64_t frame;
    Pose pose;
    std::int64_t arrival;
  };

  void Run() {
    std::unique_lock<std::mutex> lock(mu_);
    for (;;) {
      cv_.wait(lock, [&] { return stop_ || !queue_.empty(); });
      if (stop_) return;
      const Request req = queue_.front();
      queue_.pop_front();
      in_flight_ = true;
      in_flight_frame_ = req.frame;
      lock.unlock();
      Result r;
      render_(req.frame, req.pose, req.arrival, &r);
      lock.lock();
      in_flight_ = false;
      ++stats_.rendered;
      if (req.frame < taken_through_) {
        // Taken past while it rendered: never planned. Keep its route event.
        if (!r.route_event.empty()) carried_.push_back(r.route_event);
        ++stats_.discarded;
      } else {
        results_[req.frame] = std::move(r);
        while (results_.size() > keep_) {
          auto oldest = results_.begin();
          if (!oldest->second.route_event.empty()) carried_.push_back(oldest->second.route_event);
          results_.erase(oldest);
          ++stats_.discarded;
        }
      }
      cv_.notify_all();
    }
  }

  bool InFlightOrQueuedLocked(std::uint64_t frame) const {
    if (in_flight_ && in_flight_frame_ == frame) return true;
    for (const Request& r : queue_) {
      if (r.frame == frame) return true;
    }
    return false;
  }

  void DiscardOlderLocked(std::uint64_t frame) {
    if (frame > taken_through_) taken_through_ = frame;
    for (auto it = results_.begin(); it != results_.end() && it->first < frame;) {
      if (!it->second.route_event.empty()) carried_.push_back(it->second.route_event);
      it = results_.erase(it);
      ++stats_.discarded;
    }
    for (auto it = queue_.begin(); it != queue_.end();) {
      if (it->frame < frame) {
        it = queue_.erase(it);
        ++stats_.discarded;
      } else {
        ++it;
      }
    }
  }

  void DrainCarriedLocked(std::vector<std::string>* carried) {
    if (carried != nullptr) {
      for (auto& e : carried_) carried->push_back(std::move(e));
    }
    carried_.clear();
  }

  const std::size_t capacity_;
  const std::size_t keep_;
  mutable std::mutex mu_;
  std::condition_variable cv_;
  std::thread worker_;
  RenderFn render_;
  bool armed_ = false;
  bool stop_ = false;
  bool in_flight_ = false;
  std::uint64_t in_flight_frame_ = 0;
  std::uint64_t taken_through_ = 0;
  std::deque<Request> queue_;
  std::map<std::uint64_t, Result> results_;
  std::vector<std::string> carried_;
  PrefetchStats stats_;
};

}  // namespace de4sdv::driving::agent
