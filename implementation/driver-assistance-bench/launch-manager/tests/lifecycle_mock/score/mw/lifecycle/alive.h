// Test-only declarations, not S-CORE code: the public API of score/mw/lifecycle/alive.h at eclipse-score/lifecycle
// v0.10.0 (2afae116, score/launch_manager/src/alive/src/alive.h), as the bench's bindings use it, for a syntax
// check on the host. The real header comes from //score/launch_manager:alive_cc in the S-CORE Bazel build.
#pragma once

#include <cstdint>
#include <memory>
#include <string_view>

namespace score::mw::lifecycle {

class AliveImpl;

class Alive final {
 public:
  explicit Alive(const std::string_view& instance) noexcept(false);
  Alive(const Alive&) = delete;
  Alive(Alive&&) noexcept;
  Alive& operator=(const Alive&) = delete;
  Alive& operator=(Alive&&) noexcept;
  ~Alive() noexcept;
  void ReportAlive() const noexcept;
  void ReportFailure() const noexcept;

 private:
  std::unique_ptr<AliveImpl> aliveImplPtr;
};

}  // namespace score::mw::lifecycle
