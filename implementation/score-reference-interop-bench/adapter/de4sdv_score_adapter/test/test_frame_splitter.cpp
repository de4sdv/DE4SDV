// Unit tests of the frame splitter of the pure adapter core. The INC-AEBS-010
// frame assembler serves a stream of frames, each behind a 4-byte
// little-endian length prefix. The adapter reads the prefix only to delimit
// the frames and forwards prefix plus frame unchanged as one mw::com sample
// of at most 2048 bytes. A larger frame is dropped and counted, never
// truncated (REQ-MW-015).

#include <gtest/gtest.h>

#include <algorithm>
#include <atomic>
#include <cstdint>
#include <thread>
#include <vector>

#include "de4sdv_score_adapter/frame_splitter.hpp"

namespace {

using de4sdv::score_adapter::FrameSplitter;
using Bytes = std::vector<std::uint8_t>;

constexpr std::size_t kMaxSampleBytes = 2048;

Bytes Frame(std::size_t payload_size, std::uint8_t seed) {
  Bytes frame(4 + payload_size);
  const auto length = static_cast<std::uint32_t>(payload_size);
  frame[0] = static_cast<std::uint8_t>(length & 0xFFU);
  frame[1] = static_cast<std::uint8_t>((length >> 8U) & 0xFFU);
  frame[2] = static_cast<std::uint8_t>((length >> 16U) & 0xFFU);
  frame[3] = static_cast<std::uint8_t>((length >> 24U) & 0xFFU);
  for (std::size_t i = 0; i < payload_size; ++i) {
    frame[4 + i] = static_cast<std::uint8_t>(seed + i * 7U);
  }
  return frame;
}

struct Collector {
  std::vector<Bytes> samples;
  FrameSplitter::FrameHandler Handler() {
    return [this](const std::uint8_t* data, std::size_t size) { samples.emplace_back(data, data + size); };
  }
};

Bytes Concat(const std::vector<Bytes>& parts) {
  Bytes out;
  for (const auto& part : parts) {
    out.insert(out.end(), part.begin(), part.end());
  }
  return out;
}

TEST(FrameSplitter, CompleteFrameIsForwardedWithItsPrefixUnchanged) {
  FrameSplitter splitter{kMaxSampleBytes};
  Collector collector;
  const Bytes frame = Frame(5, 0x10);
  splitter.Feed(frame.data(), frame.size(), collector.Handler());
  ASSERT_EQ(collector.samples.size(), 1U);
  EXPECT_EQ(collector.samples[0], frame);
  EXPECT_EQ(splitter.stats().frames_forwarded, 1U);
}

TEST(FrameSplitter, PrefixIsLittleEndian) {
  FrameSplitter splitter{kMaxSampleBytes};
  Collector collector;
  const Bytes stream{0x03, 0x00, 0x00, 0x00, 0xAA, 0xBB, 0xCC, 0x01, 0x00, 0x00, 0x00, 0xDD};
  splitter.Feed(stream.data(), stream.size(), collector.Handler());
  ASSERT_EQ(collector.samples.size(), 2U);
  EXPECT_EQ(collector.samples[0], (Bytes{0x03, 0x00, 0x00, 0x00, 0xAA, 0xBB, 0xCC}));
  EXPECT_EQ(collector.samples[1], (Bytes{0x01, 0x00, 0x00, 0x00, 0xDD}));
}

TEST(FrameSplitter, FrameSplitAcrossReadsIsForwardedOnceAndWhole) {
  FrameSplitter splitter{kMaxSampleBytes};
  Collector collector;
  const Bytes frame = Frame(300, 0x21);
  for (const std::uint8_t byte : frame) {
    splitter.Feed(&byte, 1, collector.Handler());
  }
  ASSERT_EQ(collector.samples.size(), 1U);
  EXPECT_EQ(collector.samples[0], frame);
}

TEST(FrameSplitter, SeveralFramesInOneReadKeepTheirOrder) {
  FrameSplitter splitter{kMaxSampleBytes};
  Collector collector;
  const Bytes first = Frame(1, 1);
  const Bytes second = Frame(1000, 2);
  const Bytes third = Frame(64, 3);
  const Bytes stream = Concat({first, second, third});
  splitter.Feed(stream.data(), stream.size(), collector.Handler());
  ASSERT_EQ(collector.samples.size(), 3U);
  EXPECT_EQ(collector.samples[0], first);
  EXPECT_EQ(collector.samples[1], second);
  EXPECT_EQ(collector.samples[2], third);
}

TEST(FrameSplitter, FrameThatFillsTheSampleExactlyIsForwarded) {
  FrameSplitter splitter{kMaxSampleBytes};
  Collector collector;
  const Bytes frame = Frame(kMaxSampleBytes - 4, 0x33);
  splitter.Feed(frame.data(), frame.size(), collector.Handler());
  ASSERT_EQ(collector.samples.size(), 1U);
  EXPECT_EQ(collector.samples[0].size(), kMaxSampleBytes);
  EXPECT_EQ(collector.samples[0], frame);
}

TEST(FrameSplitter, OversizeFrameIsDroppedAndCountedAndTheNextFrameStillArrives) {
  FrameSplitter splitter{kMaxSampleBytes};
  Collector collector;
  const Bytes oversize = Frame(kMaxSampleBytes - 3, 0x44);
  const Bytes next = Frame(10, 0x55);
  const Bytes stream = Concat({oversize, next});
  splitter.Feed(stream.data(), stream.size(), collector.Handler());
  ASSERT_EQ(collector.samples.size(), 1U);
  EXPECT_EQ(collector.samples[0], next);
  EXPECT_EQ(splitter.stats().frames_dropped_oversize, 1U);
  EXPECT_EQ(splitter.stats().frames_forwarded, 1U);
}

TEST(FrameSplitter, OversizeFrameSpreadOverManyReadsDoesNotShiftTheFraming) {
  FrameSplitter splitter{kMaxSampleBytes};
  Collector collector;
  const Bytes oversize = Frame(100000, 0x66);
  const Bytes next = Frame(20, 0x77);
  const Bytes stream = Concat({oversize, next});
  std::size_t offset = 0;
  while (offset < stream.size()) {
    const std::size_t chunk = std::min<std::size_t>(997, stream.size() - offset);
    splitter.Feed(stream.data() + offset, chunk, collector.Handler());
    offset += chunk;
  }
  ASSERT_EQ(collector.samples.size(), 1U);
  EXPECT_EQ(collector.samples[0], next);
  EXPECT_EQ(splitter.stats().frames_dropped_oversize, 1U);
}

TEST(FrameSplitter, ZeroLengthFrameIsForwardedAsItsPrefix) {
  FrameSplitter splitter{kMaxSampleBytes};
  Collector collector;
  const Bytes frame = Frame(0, 0);
  splitter.Feed(frame.data(), frame.size(), collector.Handler());
  ASSERT_EQ(collector.samples.size(), 1U);
  EXPECT_EQ(collector.samples[0], (Bytes{0x00, 0x00, 0x00, 0x00}));
}

TEST(FrameSplitter, ResetDiscardsAPartialFrameSoNoTornFrameIsForwarded) {
  FrameSplitter splitter{kMaxSampleBytes};
  Collector collector;
  const Bytes torn = Frame(50, 0x88);
  splitter.Feed(torn.data(), 20, collector.Handler());
  EXPECT_TRUE(splitter.HasPartialFrame());
  splitter.Reset();
  EXPECT_FALSE(splitter.HasPartialFrame());
  const Bytes fresh = Frame(8, 0x99);
  splitter.Feed(fresh.data(), fresh.size(), collector.Handler());
  ASSERT_EQ(collector.samples.size(), 1U);
  EXPECT_EQ(collector.samples[0], fresh);
  EXPECT_EQ(splitter.stats().partial_frames_discarded, 1U);
}

TEST(FrameSplitter, ResetInsideAnOversizeFrameRestartsAtAPrefix) {
  FrameSplitter splitter{kMaxSampleBytes};
  Collector collector;
  const Bytes oversize = Frame(5000, 0x12);
  splitter.Feed(oversize.data(), 3000, collector.Handler());
  splitter.Reset();
  const Bytes fresh = Frame(3, 0x13);
  splitter.Feed(fresh.data(), fresh.size(), collector.Handler());
  ASSERT_EQ(collector.samples.size(), 1U);
  EXPECT_EQ(collector.samples[0], fresh);
}

TEST(FrameSplitter, ResetBetweenFramesDiscardsNothing) {
  FrameSplitter splitter{kMaxSampleBytes};
  Collector collector;
  const Bytes frame = Frame(4, 0x01);
  splitter.Feed(frame.data(), frame.size(), collector.Handler());
  splitter.Reset();
  EXPECT_EQ(splitter.stats().partial_frames_discarded, 0U);
}

TEST(FrameSplitter, CountsTheBytesItReads) {
  FrameSplitter splitter{kMaxSampleBytes};
  Collector collector;
  const Bytes stream = Concat({Frame(10, 1), Frame(kMaxSampleBytes, 2), Frame(1, 3)});
  splitter.Feed(stream.data(), stream.size(), collector.Handler());
  EXPECT_EQ(splitter.stats().bytes_read, stream.size());
  EXPECT_EQ(collector.samples.size(), 2U);
}

TEST(FrameSplitter, StatsMayBeReadWhileTheIngestThreadFeeds) {
  // The adapter logs the counters from its main thread while the frame
  // ingest thread feeds the splitter; the counters are atomics, so this is
  // free of data races (a ThreadSanitizer build of this test reports none).
  FrameSplitter splitter{kMaxSampleBytes};
  const Bytes frame = Frame(100, 0x05);
  std::atomic<bool> done{false};
  std::uint64_t last_seen = 0;
  std::thread reader{[&] {
    while (!done.load()) {
      const FrameSplitter::Stats snapshot = splitter.stats();
      EXPECT_GE(snapshot.frames_forwarded, last_seen);
      last_seen = snapshot.frames_forwarded;
    }
  }};
  std::uint64_t forwarded = 0;
  for (int i = 0; i < 20000; ++i) {
    splitter.Feed(frame.data(), frame.size(), [&forwarded](const std::uint8_t*, std::size_t) { ++forwarded; });
  }
  done.store(true);
  reader.join();
  EXPECT_EQ(splitter.stats().frames_forwarded, forwarded);
  EXPECT_EQ(splitter.stats().bytes_read, 20000U * frame.size());
}

}  // namespace
