// LOCAL SYNTAX MOCK - NOT S-CORE. Just enough of the S-CORE Communication
// v0.6.0 surface for `g++ -fsyntax-only` to parse state_publisher_main.cpp on a
// machine without S-CORE. It proves nothing about the real API; it only catches
// typos, capture errors and type mismatches inside my own file.
#pragma once

#include <cstddef>
#include <cstdint>
#include <memory>
#include <string>
#include <utility>

namespace score::mw::com {

struct Error {
  std::string message;
  std::string Message() const { return message; }
};

class VoidResult {
 public:
  bool has_value() const { return true; }
  const struct Error& error() const { return error_; }

 private:
  struct Error error_{};
};

template <typename T>
class Result {
 public:
  Result() = default;
  explicit Result(T value) : value_(std::move(value)), ok_(true) {}
  bool has_value() const { return ok_; }
  T& value() & { return value_; }
  T&& value() && { return std::move(value_); }
  const Error& error() const { return error_; }

 private:
  T value_{};
  Error error_{};
  bool ok_ = false;
};

class InstanceSpecifier {
 public:
  InstanceSpecifier() = default;
  static Result<InstanceSpecifier> Create(const std::string& /*text*/) {
    return Result<InstanceSpecifier>{InstanceSpecifier{}};
  }
};

class SkeletonBase {};
class ProxyBase {};

// One event of a skeleton: typed samples, allocate/send.
template <typename SampleType>
class SkeletonEvent {
 public:
  template <typename Owner>
  SkeletonEvent(Owner& /*owner*/, const char* /*name*/) {}
  Result<std::shared_ptr<SampleType>> Allocate() {
    return Result<std::shared_ptr<SampleType>>{std::make_shared<SampleType>()};
  }
  VoidResult Send(std::shared_ptr<SampleType> /*slot*/) { return VoidResult{}; }
};

// One event of a proxy.
template <typename SampleType>
class ProxyEvent {
 public:
  template <typename Owner>
  ProxyEvent(Owner& /*owner*/, const char* /*name*/) {}
};

template <typename SampleType>
class SamplePtr {
 public:
  SampleType& operator*() const { return *value_; }

 private:
  std::shared_ptr<SampleType> value_{};
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
  static Result<AsSkeleton> Create(InstanceSpecifier /*specifier*/) {
    return Result<AsSkeleton>{AsSkeleton{}};
  }
  VoidResult OfferService() { return VoidResult{}; }
  void StopOfferService() {}
};

template <template <typename> class InterfaceTrait>
class AsProxy : public InterfaceTrait<ProxyTrait> {
 public:
  using HandleType = int;
  using FindServiceHandle = int;

  static Result<AsProxy> Create(HandleType /*handle*/) { return Result<AsProxy>{AsProxy{}}; }
  VoidResult Subscribe(std::size_t /*max_sample_count*/) { return VoidResult{}; }
  template <typename Fn>
  VoidResult GetNewSamples(Fn&& /*fn*/, std::size_t /*max_num_samples*/) {
    return VoidResult{};
  }
  template <typename Handler>
  static FindServiceHandle StartFindService(Handler&& /*handler*/, InstanceSpecifier /*specifier*/) {
    return 0;
  }

 private:
  AsProxy() = default;
};

}  // namespace score::mw::com
