// DE4SDV closed-loop driving bench (INC-DRIVING-001, slice 10b): the agent's end of the route
// channel (ICD section 9, MAP-DRIVING-ROUTE). The route provider sends one RouteAnnouncement datagram
// to 127.0.0.1:47110 every 500 ms of simulation time; this listener keeps the newest valid one for
// conditionInputs (REQ-DRIVING-025 judges its age and corridor).
#pragma once

#include <atomic>
#include <cstdint>
#include <mutex>
#include <string>
#include <thread>

#include "de4sdv/driving/payloads.h"

namespace de4sdv::driving::agent {

inline constexpr int kRouteUdpPort = 47110;

struct RouteState {
  bool has_announcement = false;
  RouteAnnouncement newest{};       // byte for byte as received
  std::int64_t received_mono_ns = 0;
  std::uint64_t received = 0;       // valid datagrams
  std::uint64_t rejected = 0;       // wrong size or interface version
};

class RouteListener {
 public:
  RouteListener() = default;
  ~RouteListener();
  RouteListener(const RouteListener&) = delete;
  RouteListener& operator=(const RouteListener&) = delete;

  // Binds a UDP socket on host:port (port 0: an ephemeral port, see port()) and starts the thread.
  bool Start(const std::string& host, int port, std::string* error);
  // Ends the thread within 100 ms; idempotent.
  void Stop();
  int port() const { return port_; }
  RouteState Newest() const;

 private:
  void Loop();
  int fd_ = -1;
  int port_ = 0;
  std::thread thread_;
  std::atomic<bool> running_{false};
  mutable std::mutex mutex_;
  RouteState state_;
};

}  // namespace de4sdv::driving::agent
