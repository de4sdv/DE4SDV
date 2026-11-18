// Fakes for the two seams of the DE4SDV S-CORE interface (mw::com and the CARLA 1.0 client). Test code only.
#pragma once

#include <array>
#include <cstdint>
#include <cstring>
#include <deque>
#include <string>
#include <vector>

#include "de4sdv/score_interface/seams.hpp"

namespace fakes {

namespace da = de4sdv::driver_assistance;
namespace si = de4sdv::score_interface;

struct CommandSink : si::DrivingCommandSink {
  std::vector<da::DrivingCommandEventPayload> sent;
  bool fail_next = false;
  bool Send(const da::DrivingCommandEventPayload& p) override {
    if (fail_next) {
      fail_next = false;
      return false;
    }
    sent.push_back(p);
    return true;
  }
};

struct WarningSink : si::WarningRequestSink {
  std::vector<std::array<std::uint8_t, 8>> sent;
  std::vector<std::size_t> sizes;
  bool Send(const std::uint8_t* bytes, std::size_t size) override {
    sizes.push_back(size);
    std::array<std::uint8_t, 8> b{};
    std::memcpy(b.data(), bytes, size < 8 ? size : 8);
    sent.push_back(b);
    return true;
  }
};

struct RecordSource : si::CandidateRecordSource {
  std::deque<da::CandidateRecordEventPayload> pending;
  int polls = 0;
  bool TakeNewest(da::CandidateRecordEventPayload* out) override {
    ++polls;
    if (pending.empty()) return false;
    *out = pending.back();
    pending.clear();
    return true;
  }
};

// A synthetic record: well-formed, no real hash.
inline da::CandidateRecordEventPayload GoodRecord() {
  da::CandidateRecordEventPayload r{};
  std::memset(r.recordSha256, 'a', 64);
  std::memset(r.upstreamRevision, '0', 40);
  r.diffBytes = 1234u;
  std::strcpy(r.recordPath, "/run/score/candidate_record.json");
  return r;
}

struct SimulatorClient : si::SimulatorClient {
  ImageHandler handler;
  bool attached = false;
  bool started = false;
  bool stopped = false;
  bool has_velocity = false;
  si::EgoVelocity velocity{};
  bool Attach(std::string*) override {
    attached = true;
    return true;
  }
  bool Start(ImageHandler h, std::string*) override {
    handler = std::move(h);
    started = true;
    return true;
  }
  bool NewestEgoVelocity(si::EgoVelocity* out) override {
    if (!has_velocity) return false;
    *out = velocity;
    return true;
  }
  void Stop() override { stopped = true; }
  // Delivers one BGRA image whose pixel (x, y) is (b, g, r, a) = (x, y, frame & 0xff, 255).
  void Deliver(std::uint64_t frame, double sim_time_s, int width, int height) {
    std::vector<std::uint8_t> px(static_cast<std::size_t>(width) * height * 4);
    for (int y = 0; y < height; ++y)
      for (int x = 0; x < width; ++x) {
        std::uint8_t* p = &px[(static_cast<std::size_t>(y) * width + x) * 4];
        p[0] = static_cast<std::uint8_t>(x);
        p[1] = static_cast<std::uint8_t>(y);
        p[2] = static_cast<std::uint8_t>(frame & 0xffu);
        p[3] = 255;
      }
    si::CameraImageView v;
    v.frame = frame;
    v.sim_time_s = sim_time_s;
    v.width = width;
    v.height = height;
    v.row_bytes = static_cast<std::size_t>(width) * 4;
    v.bgra = px.data();
    handler(v);
  }
};

}  // namespace fakes
