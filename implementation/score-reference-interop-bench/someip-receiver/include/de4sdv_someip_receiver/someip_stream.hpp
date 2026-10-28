// Pure core of the DE4SDV minimal SOME/IP receiver: SOME/IP over TCP.
//
// someipd sends the notifications of the frame event as one TCP byte
// stream. TCP keeps no message boundaries, so the reassembler reads the
// 16-byte header of each message and its length field, and hands on each
// message once it is complete, however the stream was cut into reads.
//
// A payload larger than max_payload_bytes, up to kSkipLimitBytes, is
// skipped byte for byte and counted; the messages after it stay intact. A
// length field below 8 or a payload above kSkipLimitBytes means that the
// framing of the stream is lost: Feed() returns false and hands on nothing
// more until Reset(). The caller then closes the connection, because a
// SOME/IP stream without magic cookies cannot find its framing again.

#ifndef DE4SDV_SOMEIP_RECEIVER_SOMEIP_STREAM_HPP
#define DE4SDV_SOMEIP_RECEIVER_SOMEIP_STREAM_HPP

#include <array>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <vector>

#include "de4sdv_someip_receiver/someip_wire.hpp"

namespace de4sdv::someip_receiver {

class SomeipStreamReassembler {
 public:
  static constexpr std::size_t kSkipLimitBytes = 1U << 20U;

  // The payload pointer is valid only during the call.
  using MessageHandler = std::function<void(const Header& header, const std::uint8_t* payload, std::size_t size)>;

  struct Stats {
    std::uint64_t bytes_read{0};
    std::uint64_t messages{0};
    std::uint64_t messages_oversize_skipped{0};
    std::uint64_t partial_messages_discarded{0};
    std::uint64_t framing_errors{0};
  };

  explicit SomeipStreamReassembler(std::size_t max_payload_bytes);

  // Returns false once the framing is lost.
  bool Feed(const std::uint8_t* data, std::size_t size, const MessageHandler& on_message);

  // Forgets a partly read message and a lost framing (new connection).
  void Reset() noexcept;

  bool framing_lost() const noexcept { return state_ == State::kLost; }
  bool HasPartialMessage() const noexcept;
  const Stats& stats() const noexcept { return stats_; }

 private:
  enum class State { kHeader, kPayload, kSkip, kLost };

  void StartMessage(const MessageHandler& on_message);

  std::size_t max_payload_bytes_;
  State state_{State::kHeader};
  std::array<std::uint8_t, kHeaderBytes> header_bytes_{};
  std::size_t header_filled_{0};
  Header header_{};
  std::vector<std::uint8_t> payload_;
  std::size_t payload_expected_{0};
  std::uint64_t skip_remaining_{0};
  Stats stats_{};
};

}  // namespace de4sdv::someip_receiver

#endif  // DE4SDV_SOMEIP_RECEIVER_SOMEIP_STREAM_HPP
