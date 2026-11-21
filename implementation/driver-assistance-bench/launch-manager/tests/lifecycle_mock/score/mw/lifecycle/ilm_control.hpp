// Test-only declarations, not S-CORE code: the public API of score/mw/lifecycle/ilm_control.hpp at
// eclipse-score/lifecycle v0.10.0 (2afae116, score/launch_manager/src/lm_control/src/ilm_control.hpp,
// run_target_activation_source.hpp and fixed_string.hpp) and of score::Result as the bench's control client uses
// them, for a syntax check on the host. The real headers come from //score/launch_manager:control_cc and
// @score_baselibs//score/result in the S-CORE Bazel build.
#pragma once

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <memory>
#include <string_view>

namespace score {

namespace result {
class Error {
 public:
  std::string_view Message() const noexcept;
};
}  // namespace result

template <typename T>
class Result {
 public:
  bool has_value() const noexcept;
  T& value() & noexcept;
  T&& value() && noexcept;
  const result::Error& error() const noexcept;
};

template <>
class Result<void> {
 public:
  bool has_value() const noexcept;
  const result::Error& error() const noexcept;
};

namespace cpp {
class stop_token {};
}  // namespace cpp

}  // namespace score

namespace score::mw::lifecycle {

template <std::size_t MaxLength>
class FixedString {
 public:
  FixedString() noexcept;
  explicit FixedString(std::string_view s) noexcept;  // constexpr at v0.10.0; declared only here
  std::string_view as_string_view() const noexcept;
  const char* data() const noexcept;
};

inline constexpr std::size_t kMaxRunTargetNameLength = 128U;
using RunTargetName = FixedString<kMaxRunTargetNameLength>;

enum class RunTargetActivationSource : std::uint8_t {
  kInitialActivation = 0,
  kStateManagerRequest = 1,
  kRecoveryAction = 2
};

class ILmControl {
 public:
  using ActivationCallback =
      std::function<void(RunTargetActivationSource activationSource, RunTargetName activatedRunTarget)>;
  static score::Result<std::unique_ptr<ILmControl>> Create(std::string_view instance_specifier);
  virtual score::Result<void> wait_for_connection(
      std::chrono::milliseconds timeout = std::chrono::milliseconds(500),
      const score::cpp::stop_token& stop_token = score::cpp::stop_token{}) = 0;
  virtual ~ILmControl() noexcept = default;
  ILmControl(const ILmControl&) = delete;
  ILmControl& operator=(const ILmControl&) = delete;
  ILmControl(ILmControl&&) = delete;
  ILmControl& operator=(ILmControl&&) = delete;
  virtual score::Result<void> activate_run_target(RunTargetName runTargetName, bool force = false) = 0;
  virtual score::Result<void> register_run_target_activation_callback(ActivationCallback callback) = 0;
  virtual score::Result<RunTargetName> get_active_run_target() = 0;

 protected:
  ILmControl() = default;
};

}  // namespace score::mw::lifecycle
