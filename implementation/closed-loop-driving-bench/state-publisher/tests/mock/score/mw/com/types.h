// LOCAL SYNTAX MOCK - NOT S-CORE. Just enough of the S-CORE Communication
// v0.6.0 surface for `g++ -fsyntax-only` to parse state_publisher_main.cpp on a
// machine without S-CORE. Revised to the DECLARED v0.6.0 API (c5efd74f), so the
// local check fails where the real headers would:
//   * HandleType and FindServiceHandle have no default constructor
//     (impl/handle_type.h:52, impl/find_service_handle.h:44);
//   * StartFindService returns Result<FindServiceHandle> and takes
//     FindServiceHandler<HandleType> = callback<void(ServiceHandleContainer<HandleType>,
//     FindServiceHandle)> (impl/proxy_base.h:105, impl/find_service_handler.h);
//   * Subscribe / GetNewSamples are members of the proxy EVENT
//     (impl/proxy_event_base.h:82, impl/proxy_event.h:125), and the receiver is
//     called with an rvalue SamplePtr<T> (impl/tracing/proxy_event_tracing.h:82);
//   * SamplePtr<T>::operator* yields const T& (impl/plumbing/sample_ptr.h:44,162).
// It still proves nothing about the real API; a compile against the real S-CORE
// headers and the Bazel build on the build VM do.
#pragma once

#include <cstddef>
#include <cstdint>
#include <functional>
#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <vector>

namespace score::mw::com {

struct Error {
  std::string message;
  std::string_view Message() const { return message; }
};

template <typename T>
class Result {
 public:
  Result() = default;
  explicit Result(T value) : value_(std::move(value)) {}
  bool has_value() const { return value_.has_value(); }
  T& value() & { return *value_; }
  const T& value() const& { return *value_; }
  T&& value() && { return std::move(*value_); }
  const Error& error() const { return error_; }

 private:
  std::optional<T> value_{};
  Error error_{};
};

template <>
class Result<void> {
 public:
  bool has_value() const { return true; }
  const Error& error() const { return error_; }

 private:
  Error error_{};
};

class InstanceSpecifier {
 public:
  InstanceSpecifier() = default;
  static Result<InstanceSpecifier> Create(std::string&& /*text*/) {
    return Result<InstanceSpecifier>{InstanceSpecifier{}};
  }
};

class HandleType {
 public:
  HandleType() = delete;
  explicit HandleType(int id) : id_(id) {}

 private:
  int id_;
};

class FindServiceHandle {
 public:
  FindServiceHandle() = delete;
  explicit FindServiceHandle(std::size_t uid) : uid_(uid) {}

 private:
  std::size_t uid_;
};

template <typename T>
using ServiceHandleContainer = std::vector<T>;
template <typename T>
using FindServiceHandler = std::function<void(ServiceHandleContainer<T>, FindServiceHandle)>;

template <typename SampleType>
class SamplePtr {
 public:
  SamplePtr() = default;
  SamplePtr(SamplePtr&&) noexcept = default;
  SamplePtr(const SamplePtr&) = delete;
  const SampleType& operator*() const { return *value_; }
  const SampleType* operator->() const { return value_.get(); }

 private:
  std::unique_ptr<SampleType> value_{};
};

template <typename SampleType>
class SampleAllocateePtr {
 public:
  SampleAllocateePtr() : value_(std::make_unique<SampleType>()) {}
  SampleType& operator*() const { return *value_; }
  SampleType* operator->() const { return value_.get(); }

 private:
  std::unique_ptr<SampleType> value_;
};

class SkeletonBase {};
class ProxyBase {
 public:
  using HandleType = ::score::mw::com::HandleType;
  static Result<ServiceHandleContainer<HandleType>> FindService(InstanceSpecifier) { return {}; }
  static Result<FindServiceHandle> StartFindService(FindServiceHandler<HandleType> /*handler*/,
                                                    InstanceSpecifier /*specifier*/) {
    return Result<FindServiceHandle>{};
  }
  static Result<void> StopFindService(const FindServiceHandle /*handle*/) { return {}; }
};

// One event of a skeleton: typed samples, allocate/send.
template <typename SampleType>
class SkeletonEvent {
 public:
  template <typename Owner>
  SkeletonEvent(Owner& /*owner*/, const char* /*name*/) {}
  Result<SampleAllocateePtr<SampleType>> Allocate() {
    return Result<SampleAllocateePtr<SampleType>>{SampleAllocateePtr<SampleType>{}};
  }
  Result<void> Send(SampleAllocateePtr<SampleType> /*slot*/) { return {}; }
};

// One event of a proxy: Subscribe and GetNewSamples live here, not on the proxy.
template <typename SampleType>
class ProxyEvent {
 public:
  template <typename Owner>
  ProxyEvent(Owner& /*owner*/, const char* /*name*/) {}
  Result<void> Subscribe(const std::size_t /*max_sample_count*/) { return {}; }
  template <typename F>
  Result<std::size_t> GetNewSamples(F&& receiver, std::size_t /*max_num_samples*/) {
    static_assert(std::is_invocable_v<F&, SamplePtr<SampleType>&&>,
                  "the receiver must accept an rvalue SamplePtr<SampleType>");
    if (false) receiver(SamplePtr<SampleType>{});
    return Result<std::size_t>{0};
  }
};

struct SkeletonTrait {
  using Base = SkeletonBase;
  template <typename T>
  using Event = SkeletonEvent<T>;
};

struct ProxyTrait {
  using Base = ProxyBase;
  template <typename T>
  using Event = ProxyEvent<T>;
};

template <template <typename> class InterfaceTrait>
class AsSkeleton : public InterfaceTrait<SkeletonTrait> {
 public:
  static Result<AsSkeleton> Create(const InstanceSpecifier& /*specifier*/) {
    return Result<AsSkeleton>{AsSkeleton{}};
  }
  Result<void> OfferService() { return {}; }
  void StopOfferService() {}
};

template <template <typename> class InterfaceTrait>
class AsProxy : public InterfaceTrait<ProxyTrait> {
 public:
  static Result<AsProxy> Create(const HandleType& /*handle*/) { return Result<AsProxy>{AsProxy{}}; }
  AsProxy(AsProxy&&) noexcept = default;
  AsProxy& operator=(AsProxy&&) noexcept = default;
  AsProxy(const AsProxy&) = delete;
  AsProxy& operator=(const AsProxy&) = delete;

 private:
  AsProxy() = default;
};

}  // namespace score::mw::com
